### Webhook

`@nestjs/webhooks` gửi webhook có chữ ký, có retry tới các đối tác của bạn sau khi transaction commit, và xác minh các webhook bạn nhận được dựa trên raw body của chúng.

Một cửa hàng online bán thức ăn và đồ dùng cho mèo bán hàng cho các trại cứu trợ mèo và các đại lý mua số lượng lớn, thông qua API của nó. Northside Pet Supplies, một đại lý, đặt một đơn hàng và muốn biết khi nào đơn được giao và khi nào bị hủy, mà không cần polling: một webhook tới hệ thống kho của họ. Cửa hàng cũng nhận webhook: payment provider báo cáo các khoản thanh toán, và hãng vận chuyển báo cáo các lô hàng. Cả hai chiều trông có vẻ đơn giản, và cả hai đều hỏng theo cùng những cách:

- **Gửi.** Một lời gọi `fetch()` sau khi đơn hàng commit sẽ bị mất nếu process chết ở giữa, và được gửi đi cho một transaction sau đó lại bị rollback. Một lần retry gửi cùng một event hai lần mà không báo cho đối tác biết. Mỗi đối tác tự viết bộ xác minh riêng cho một kiểu chữ ký tự chế. Một đối tác bị sập một giờ sẽ bị dội liên tục, một endpoint đã chết không bao giờ được tắt, và không ai trả lời được câu "anh đã gửi chưa?". Và URL mà đối tác gõ vào là một lỗ hổng server-side request forgery chực chờ: `https://169.254.169.254/` trả lời bằng thông tin xác thực của cloud.
- **Nhận.** Chữ ký được kiểm tra trên một body mà framework đã parse rồi serialize lại (một dấu cách lạc chỗ cũng làm hỏng nó, và một body bị giả mạo có thể lọt qua), so sánh bằng `===` thay vì trong thời gian không đổi, không có khoảng thời gian timestamp nào, và một event được gửi lại sẽ chạy handler hai lần: một đơn hàng bị đánh dấu đã thanh toán hai lần, hoặc đã giao hai lần.

`@nestjs/webhooks` biến cả hai chiều thành một thứ duy nhất để cấu hình. Webhook gửi đi đi qua [outbox](/reliability/outbox): `webhooks.dispatch()` thêm message trong cùng transaction với đơn hàng, và sau khi commit, một worker phân phối nó tới các endpoint của đối tác, ký mỗi request theo cách [Standard Webhooks](https://www.standardwebhooks.com) quy định, retry có backoff trong khoảng hai ngày, giữ log của mọi lần thử, và gửi lại theo yêu cầu. Webhook nhận vào chỉ cần một decorator, `@VerifyWebhook()`, decorator này kiểm tra chữ ký trên raw body và bỏ qua các lần gửi lại.

Trong bài hướng dẫn này, bạn sẽ thêm webhook vào API đơn hàng của cửa hàng, trên PostgreSQL với Drizzle:

- Đối tác đăng ký nhận `order.shipped` và `order.cancelled` qua API, và chỉ thấy secret của họ một lần.
- API gửi webhook sau khi commit, có chữ ký, và retry trong khi đối tác bị sập.
- Đối tác đọc log gửi của họ, và yêu cầu gửi lại.
- API nhận webhook thanh toán của payment provider (Standard Webhooks) và webhook vận chuyển của hãng vận chuyển (kiểu chữ ký của Stripe), được xác minh trên raw body và xử lý đúng một lần.
- Secret được xoay vòng mà không có khoảng hở, và một URL trỏ vào mạng nội bộ của cửa hàng sẽ bị từ chối.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, cài dependency cần thiết:

```bash
$ npm i --save @nestjs/webhooks
```

Bài hướng dẫn chạy trên PostgreSQL, thông qua [Drizzle ORM](https://orm.drizzle.team) và [`@nestjs/drizzle`](/data/drizzle) với driver `pg`: các endpoint và log gửi nằm trong cùng database với đơn hàng, trên một database server sống lâu hơn mọi instance của ứng dụng. Đang dùng TypeORM, hay MySQL? Hãy làm theo bài hướng dẫn, và xem "Với TypeORM" và "Với MySQL" trong phần [Giữ webhook trong database của bạn](/http/webhooks#keep-webhooks-in-your-database) để biết những gì thay đổi.

Webhook gửi đi là các outbox message, còn webhook nhận vào được loại trùng bằng inbox của outbox, nên ứng dụng cũng chạy outbox (`@nestjs/outbox`, được cài và thiết lập trong [bài hướng dẫn outbox](/reliability/outbox)).

Ứng dụng ví dụ, API đơn hàng của cửa hàng online, giữ danh mục sản phẩm, các đối tác gọi nó, và đơn hàng của họ trong ba bảng của riêng nó, các phần sau sẽ đọc và ghi chúng. Chúng là dữ liệu của ví dụ, không phải thứ mà webhook cần: các bảng của webhook và outbox thuộc về store của chúng, store sẽ tự tạo, như phần [Giữ webhook trong database của bạn](/http/webhooks#keep-webhooks-in-your-database) trình bày.

`products` là danh mục sản phẩm:

| Cột | Type | Ghi chú |
| --- | --- | --- |
| `id` | `text` | Khóa chính, như `salmon-kibble-2kg` |
| `name` | `text` | Tên hiển thị, như `Salmon kibble, 2 kg` |
| `price` | `integer` | Tính bằng cent |

`partners` chứa các trại cứu trợ mèo và đại lý mua số lượng lớn qua API, và nhận webhook của nó:

| Cột | Type | Ghi chú |
| --- | --- | --- |
| `id` | `text` | Khóa chính, như `northside` |
| `name` | `text` | Tên hiển thị, như `Northside Pet Supplies` |
| `api_key_hash` | `text` | SHA-256 của API key của đối tác, dạng hex. Duy nhất |

`orders` chứa đơn hàng của các đối tác, với `status` đi từ `placed` sang `paid` rồi `shipped`, hoặc sang `cancelled`:

| Cột | Type | Ghi chú |
| --- | --- | --- |
| `id` | `text` | Khóa chính |
| `partner_id` | `text` | Tham chiếu tới `partners.id` |
| `items` | `jsonb` | Các dòng của đơn hàng, dưới dạng mảng JSON: `productId`, `quantity` và `price` đơn vị (tính bằng cent) của mỗi dòng |
| `total` | `integer` | Tính bằng cent |
| `status` | `text` | `placed`, `paid`, `shipped` hoặc `cancelled` |
| `payment_id` | `text` | Nullable: được đặt khi đơn hàng đã thanh toán |
| `tracking_number` | `text` | Nullable: được đặt khi đơn hàng đã giao |

Các cột khác không nullable.

Danh mục có hai sản phẩm, `salmon-kibble-2kg` giá 2499 cent và `clumping-litter-10l` giá 1599 cent, và hai đối tác có API key mẫu (hãy cấp key thật từ quy trình onboarding đối tác của bạn):

| Đối tác | `id` | API key |
| --- | --- | --- |
| Northside Pet Supplies, một đại lý | `northside` | `partner_northside_7c1d2e` |
| Riverside Cat Shelter | `riverside` | `partner_riverside_91ab44` |

#### Giữ webhook trong database của bạn <a id="keep-webhooks-in-your-database"></a>

Không cần tạo gì cho webhook, hay cho outbox mà chúng đi qua: không có bảng, entity hay Prisma model nào. Hãy đăng ký hai store của chúng, và mỗi store tự tạo schema riêng, `nest_webhooks` và `nest_outbox`, rồi migrate nó: lúc khởi động trong development và trong test, còn trên production thì bằng `npx @nestjs/webhooks migrate` và `npx @nestjs/outbox migrate`, hoặc bằng `migrationSql()` của chúng trong migration của chính bạn.

Package giữ các endpoint, cùng secret của chúng, các message nó đã dispatch, các lần gửi của chúng và log của mọi lần thử trong một **store**, mà nó đọc thông qua hai hợp đồng, `WebhookEndpointStore` và `WebhookDeliveryStore`. Cho đến khi bạn đăng ký một store, module giữ chúng trong bộ nhớ: ổn cho lần chạy đầu tiên, nhưng một lần khởi động lại sẽ mất mọi lần gửi đang chờ, và hai instance không chia sẻ chúng với nhau.

> warning **Cảnh báo** Với `NODE_ENV=production` mà không đăng ký store nào, việc khởi động sẽ thất bại, trừ khi bạn đặt `allowInMemoryStorage: true`.

Trên PostgreSQL, hãy đăng ký store của package, `PostgresWebhookStore` từ `@nestjs/webhooks/postgres`. Outbox cũng cần một store, cho các message mang webhook đã dispatch ra khỏi transaction của bạn và cho inbox loại trùng các webhook nhận vào: `PostgresOutboxStore` từ `@nestjs/outbox/postgres`, như trong [bài hướng dẫn outbox](/reliability/outbox#keep-messages-in-your-database). Cả hai chạy SQL của chúng thông qua database client mà ứng dụng của bạn đã có, và giữ các bảng trong schema riêng. Chúng là các provider thông thường, được đăng ký một lần, trong root module, cạnh `WebhooksModule` và `OutboxModule`: cả bốn đều áp dụng cho toàn ứng dụng. `AppModule` tạo mỗi store bằng một factory inject database Drizzle và registry storage của package tương ứng, nơi store tự đăng ký:

```typescript
@@filename(app.module)
{
  // Outbox messages and the inbox, in your database, in a schema of their own (nest_outbox)
  provide: PostgresOutboxStore,
  inject: [getDrizzleToken(), OutboxStorage],
  useFactory: (db: Database, outboxStorage: OutboxStorage) =>
    new PostgresOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
},
{
  // Endpoints, deliveries and their log, in your database, in a schema of their own (nest_webhooks)
  provide: PostgresWebhookStore,
  inject: [getDrizzleToken(), WebhooksStorage],
  useFactory: (db: Database, webhooksStorage: WebhooksStorage) =>
    new PostgresWebhookStore({ executor: fromDrizzle(db) }, webhooksStorage),
},
```

`fromDrizzle(db)` là **executor** của các store: nó chạy các câu lệnh của chúng thông qua database Drizzle của bạn, bất kể driver nào được dùng, như `pg` hay PGlite. `fromPg(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` và `fromKysely(db)` làm điều tương tự cho một pool node-postgres, TypeORM, Prisma và Kysely. Cả `@nestjs/webhooks/postgres` và `@nestjs/outbox/postgres` đều export chúng, nên `AppModule` chỉ import `fromDrizzle` một lần, cho cả hai store. Lúc khởi động, mỗi module log store mà nó dùng.

**Schema.** Webhook store giữ các bảng trong một schema riêng, `nest_webhooks` (tùy chọn `schema` đặt tên khác). Trên MySQL, vốn không có schema, chúng là các bảng trong database của kết nối, với tên schema làm prefix: `nest_webhooks_endpoints`, v.v.

| Bảng | Chứa gì |
| --- | --- |
| `nest_webhooks.endpoints` | Các endpoint của đối tác: URL, loại event, tenant, và secret |
| `nest_webhooks.messages` | Những gì đã được dispatch, chính xác đến từng byte |
| `nest_webhooks.deliveries` | Một dòng cho mỗi message và endpoint, với trạng thái, số lần thử và lease của nó |
| `nest_webhooks.delivery_attempts` | Log: mọi lần thử, với status code, response và thời gian nó mất |
| `nest_webhooks.migrations` | Các version của schema store đã được áp dụng |

Store của outbox giữ message, dead letter và inbox của nó trong `nest_outbox` (`nest_outbox_messages`, v.v., trên MySQL), như trong [bài hướng dẫn outbox](/reliability/outbox#keep-messages-in-your-database). Chúng thuộc về các store: migration của bạn không tạo chúng, và các bảng của riêng bạn không thể trùng với chúng. Vài lựa chọn trong đó có ý nghĩa với package:

- Secret của một endpoint là một mảng JSON, mới nhất trước: trong lúc xoay vòng, secret cũ được giữ lại trong khoảng chồng lấn, kèm thời hạn. Khi có cấu hình `encryption` (xem [Đăng ký các module](/http/webhooks#register-the-modules)), thứ được lưu là bản đã niêm phong (sealed).
- `body` của message là `text`, không phải `jsonb`. Nó chính là JSON đã được ký và gửi đi, còn `jsonb` sẽ định dạng lại nó: một đối tác lưu request cùng chữ ký sẽ không còn xác minh được một lần gửi lại.
- Một lần gửi là duy nhất theo message và endpoint. Bước phân phối tạo ra các lần gửi chạy sau khi commit, bên trong outbox, nên nó có thể chạy hai lần; key duy nhất khiến lần chạy thứ hai không insert gì cả.
- Không có khóa ngoại từ lần gửi tới endpoint của nó: log của một endpoint đã xóa vẫn được giữ lại. Các lần thử đi theo lần gửi của chúng.
- Thời gian là mili giây epoch (`bigint`), lấy từ đồng hồ của package, không bao giờ từ đồng hồ của database.

**Migration.** Các package cung cấp schema của chúng dưới dạng các migration có version, và các store tự áp dụng chúng. Với tùy chọn `migrate`, mỗi store áp dụng lúc khởi động những migration mà schema của nó chưa có, trước khi relay và worker chạy, trong một transaction giữ advisory lock: trong số nhiều instance khởi động cùng lúc, một instance migrate, còn các instance khác không còn gì để làm. `migrate` mặc định là `true`, trừ khi `NODE_ENV=production`. Vì vậy trong development và trong test, các store tạo schema của chúng ở lần khởi động đầu tiên, và migration của bạn chỉ tạo các bảng của riêng bạn.

Trên production, hãy áp dụng các migration trước khi phiên bản mới của ứng dụng khởi động, như cách bạn áp dụng migration của riêng mình, để không instance nào thay đổi schema trong lúc boot: giữa một đợt rolling deploy, điều đó sẽ khóa các bảng đang bận, và một database user có quyền tối thiểu cũng không làm được. Command line của các package làm việc này từ bước deploy của bạn, cạnh `npx drizzle-kit migrate`. Chúng đọc database từ `DATABASE_URL`, hoặc từ `--url`, và cần cài `pg`:

```bash
$ npx @nestjs/webhooks status
Schema "nest_webhooks" is at version 0; this version of @nestjs/webhooks needs version 1.
$ npx @nestjs/webhooks migrate
Migrated schema "nest_webhooks" to version 1 (applied 1).
$ npx @nestjs/outbox migrate
Migrated schema "nest_outbox" to version 1 (applied 1).
```

`status` thoát với mã 1 khi schema còn lạc hậu, khiến nó trở thành một bước kiểm tra cho CI. Để áp dụng migration bằng công cụ migration của riêng bạn, hãy lấy SQL của chúng từ `npx @nestjs/webhooks sql` và `npx @nestjs/outbox sql`, hoặc từ `PostgresWebhookStore.migrationSql()` và `PostgresOutboxStore.migrationSql()` trong code: các câu lệnh của mọi migration, kèm phần ghi nhận version. Hãy chạy mỗi cái trong một transaction, như migrator của TypeORM và Drizzle làm. Với TypeORM, đó là một migration của riêng bạn, cạnh các migration nó sinh ra cho entity của bạn:

```typescript
@@filename(typeorm/migrations/1790801311590-WebhookStores)
import { PostgresOutboxStore } from '@nestjs/outbox/postgres';
import { PostgresWebhookStore } from '@nestjs/webhooks/postgres';
import type { MigrationInterface, QueryRunner } from 'typeorm';

export class WebhookStores1790801311590 implements MigrationInterface {
  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(PostgresOutboxStore.migrationSql());
    await queryRunner.query(PostgresWebhookStore.migrationSql());
  }

  async down(): Promise<void> {
    throw new Error('The webhook and outbox stores have no down migrations.');
  }
}
```

Với drizzle-kit, hãy tạo một custom migration cho mỗi store, và điền vào file mà mỗi cái tạo ra bằng SQL của nó, với một dòng `--> statement-breakpoint` giữa các câu lệnh: khi đó migrator của Drizzle chạy chúng từng câu một, điều mà PGlite yêu cầu. Trong code, `migrationSql()` với `statementBreakpoints: true` trả về đúng như vậy.

```bash
$ npx drizzle-kit generate --custom --name=outbox
$ npx @nestjs/outbox sql --statement-breakpoints > drizzle/20261103120000_outbox/migration.sql
$ npx drizzle-kit generate --custom --name=webhooks
$ npx @nestjs/webhooks sql --statement-breakpoints > drizzle/20261103120100_webhooks/migration.sql
```

Trên MySQL, `migrationStatements()` của các store trả về các câu lệnh, mỗi câu một chuỗi, và một migration TypeORM chạy chúng mỗi câu một lời gọi:

```typescript
@@filename(typeorm/mysql-migrations/1790801311590-WebhookStores)
for (const statement of [...MySqlOutboxStore.migrationStatements(), ...MySqlWebhookStore.migrationStatements()]) {
  await queryRunner.query(statement);
}
```

Khi tắt `migrate`, một store có schema lạc hậu sẽ làm việc khởi động thất bại với một `WebhookSchemaError` (với store của outbox là `OutboxSchemaError`) nêu ra ba cách xử lý này, và làm mọi lời gọi thất bại theo cùng cách cho đến khi schema được cập nhật, điều mà nó nhận ra mà không cần khởi động lại. Trong một đợt rolling deploy, phiên bản trước của ứng dụng vẫn tiếp tục chạy trên schema mà phiên bản mới đã migrate. Không có down migration.

**Transaction.** Không method nào của webhook store nhận transaction của bạn. `webhooks.dispatch(tx, ...)` thêm message vào outbox trong transaction của bạn, thông qua store của outbox, và `webhook.processInTransaction(tx, ...)` ghi nhận một webhook nhận vào trong inbox của outbox theo cùng cách; bước phân phối sau khi commit, worker và mọi thứ khác chạy trên kết nối riêng của các store. Với Drizzle, `tx` là thứ mà `db.transaction()` truyền cho callback của nó, như các phần sau trình bày. Store của outbox từ chối chính database, vì các câu lệnh của nó sẽ tự commit riêng, với một `OutboxTransactionRequiredError` cho biết cần truyền gì. Với các executor khác, hãy truyền một client node-postgres sau `BEGIN` (không phải pool), `EntityManager` của TypeORM từ `dataSource.transaction()`, interactive transaction client của Prisma, hoặc một transaction của Kysely.

**Isolation.** Các store dựa vào READ COMMITTED, isolation level mặc định của PostgreSQL: các câu lệnh của chúng chạy đua với nhau, và dưới một level chặt hơn chúng sẽ lỗi serialization. Lúc khởi động, mỗi store kiểm tra `default_transaction_isolation` của database, và thất bại nếu nó chặt hơn. Transaction của riêng bạn có thể chạy ở bất kỳ level nào. Tuy nhiên, dưới REPEATABLE READ hoặc SERIALIZABLE, một bản sao của webhook nhận vào mà `processInTransaction()` xử lý trong transaction của bạn, chạy đua với lần commit của bản đầu tiên, sẽ lỗi serialization của PostgreSQL thay vì bị bỏ qua như một bản trùng: bên gửi nhận lỗi, và lần retry của họ sẽ thấy webhook đã được ghi nhận.

**Với TypeORM.** `TypeOrmModule` thay chỗ cho `DrizzleModule` trong `AppModule`, và cả hai store chạy trên `DataSource` mà nó cung cấp, thông qua `fromTypeOrm()`:

```typescript
@@filename(typeorm/app.module)
{
  // Outbox messages and the inbox, in your database, in a schema of their own (nest_outbox)
  provide: PostgresOutboxStore,
  inject: [DataSource, OutboxStorage],
  useFactory: (dataSource: DataSource, outboxStorage: OutboxStorage) =>
    new PostgresOutboxStore({ executor: fromTypeOrm(dataSource) }, outboxStorage),
},
{
  // Endpoints, deliveries and their log, in your database, in a schema of their own (nest_webhooks)
  provide: PostgresWebhookStore,
  inject: [DataSource, WebhooksStorage],
  useFactory: (dataSource: DataSource, webhooksStorage: WebhooksStorage) =>
    new PostgresWebhookStore({ executor: fromTypeOrm(dataSource) }, webhooksStorage),
},
```

Ở chỗ bài hướng dẫn truyền `tx` của Drizzle vào `dispatch()` và `processInTransaction()`, hãy truyền `EntityManager` mà `dataSource.transaction()` truyền cho callback của nó, và inject `Webhooks<EntityManager>`. Store của outbox từ chối `dataSource.manager`, vì các thao tác ghi của nó sẽ tự commit riêng. Đây là `cancelOrder()` của order service, từ phần [Gửi order.shipped và order.cancelled sau khi commit](/http/webhooks#send-ordershipped-and-ordercancelled-after-the-commit), viết bằng TypeORM:

```typescript
@@filename(typeorm/orders.service)
const order = await this.dataSource.transaction(async (manager) => {
  const row = await manager.findOne(OrderEntity, { where: { id, partnerId: partner.id }, lock: { mode: 'pessimistic_write' } });
  if (!row) {
    throw new NotFoundException(`Order ${id} not found`);
  }
  if (row.status === 'shipped' || row.status === 'cancelled') {
    throw new ConflictException(`Order ${id} is ${row.status}`);
  }
  await manager.update(OrderEntity, id, { status: 'cancelled' });

  // The transaction's EntityManager: the webhook is sent only if the cancellation commits.
  const data: OrderCancelled = { orderId: id, reason };
  await this.webhooks.dispatch(manager, { type: 'order.cancelled', tenant: row.partnerId, data });
  return { ...row, status: 'cancelled' as const };
});
```

Entity của bạn và migration của chúng vẫn giữ nguyên: `migration:generate` chỉ so sánh entity của bạn với database, và không đụng tới schema của các store.

**Với MySQL.** Trên MySQL 8.4 hoặc 9.x, hãy import các store và executor từ `@nestjs/outbox/mysql` và `@nestjs/webhooks/mysql` thay vào đó. Các provider vẫn như vậy, với `MySqlOutboxStore` và `MySqlWebhookStore`, trên một database Drizzle của `drizzle-orm/mysql2`:

```typescript
@@filename(mysql/app.module)
import { MySqlOutboxStore } from '@nestjs/outbox/mysql';
import { fromDrizzle, MySqlWebhookStore } from '@nestjs/webhooks/mysql';
import { drizzle } from 'drizzle-orm/mysql2';
// ...
DrizzleModule.forRootAsync({
  // Drizzle on MySQL: a mysql2 pool on DATABASE_URL (mysql://), whose database holds the stores' tables too
  useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL! }),
}),
// ...
{
  // Outbox messages and the inbox, in your database, in tables of their own (nest_outbox_*)
  provide: MySqlOutboxStore,
  inject: [getDrizzleToken(), OutboxStorage],
  useFactory: (db: Database, outboxStorage: OutboxStorage) =>
    new MySqlOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
},
{
  // Endpoints, deliveries and their log, in your database, in tables of their own (nest_webhooks_*)
  provide: MySqlWebhookStore,
  inject: [getDrizzleToken(), WebhooksStorage],
  useFactory: (db: Database, webhooksStorage: WebhooksStorage) =>
    new MySqlWebhookStore({ executor: fromDrizzle(db) }, webhooksStorage),
},
```

Với các client khác, executor là `fromMysql2(pool)` cho một pool `mysql2/promise`, `fromTypeOrm(dataSource)` cho một `DataSource` có type `mysql`, `fromPrisma(prisma)` cho Prisma thông qua `@prisma/adapter-mariadb`, hoặc `fromKysely(db)` cho `MysqlDialect` của Kysely. Những gì khác với PostgreSQL:

- **Bảng, không phải schema.** MySQL không có schema bên trong database, nên các store giữ bảng của chúng trong database của kết nối, database trong path của URL, cạnh các bảng của bạn, và `schema` trở thành prefix của chúng: `nest_webhooks_endpoints`, `nest_webhooks_deliveries`, v.v., và `nest_outbox_messages` cho outbox. Nó nhận chữ thường, chữ số và dấu gạch dưới, tối đa 40 ký tự.
- **Transaction của bạn.** `dispatch()` và `processInTransaction()` hoạt động ở REPEATABLE READ, mặc định của MySQL, cũng như ở READ COMMITTED: không cần cấu hình gì, và các store không kiểm tra mặc định của database. Khi MySQL phá một deadlock trong transaction của bạn (lỗi 1213), nó rollback toàn bộ transaction, và lỗi của client đến tay code của bạn: hãy chạy lại transaction. Các store tự chạy lại transaction của chính chúng. Với `processInTransaction()`, điều đó có thể xảy ra khi nhiều bản sao của một webhook đến cùng lúc và transaction của bản đầu tiên bị rollback: bên gửi nhận lỗi, và lần retry của họ sẽ đi qua.
- **Key có giới hạn.** Id và tenant là các cột có index: tối đa 255 ký tự, 256 với tenant, các id của chính package và giới hạn của nó cho `tenant` đều nằm trong khoảng đó. Id của một webhook nhận vào nằm trong key của inbox, cũng tối đa 255 ký tự, và bộ xác minh từ chối id dài hơn trên mọi database, với lỗi 401, trước khi handler chạy.
- **Migration không phải một transaction.** MySQL tự commit mỗi câu lệnh DDL, nên `migrate` áp dụng các câu lệnh từng câu một, dưới một lock (`GET_LOCK()`), và một lần chạy thất bại sẽ tiếp tục từ câu lệnh nó đã dừng. Công cụ của riêng bạn cũng phải gửi mỗi câu lệnh một lời gọi, như migration TypeORM trong phần **Migration** ở trên. Command line nhận URL `mysql://`, và `sql --dialect mysql` in ra SQL của MySQL: thêm `--statement-breakpoints` cho custom migration của drizzle-kit, vì migrator MySQL của nó gửi mỗi breakpoint một câu lệnh.
- **Server.** Các store kiểm tra nó lúc khởi động, và từ chối MariaDB, một kết nối không có database, và một `sql_mode` không strict (mặc định của MySQL là strict). Cũng hãy giữ `NO_BACKSLASH_ESCAPES` ngoài thiết lập này.

Với một database khác, hãy tự viết store của riêng bạn: [Hợp đồng của store](/http/webhooks#the-store-contract) cho biết nó phải làm gì.

#### Đăng ký các module <a id="register-the-modules"></a>

Đăng ký `OutboxModule` và `WebhooksModule` trong root module, cạnh `DrizzleModule`, module đăng ký database Drizzle, với cả hai store trong `providers` của nó. Các feature module được xây dựng trong các phần tiếp theo:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule, getDrizzleToken } from '@nestjs/drizzle';
import { OutboxModule, OutboxStorage } from '@nestjs/outbox';
import { PostgresOutboxStore } from '@nestjs/outbox/postgres';
import { WebhooksModule, WebhooksStorage } from '@nestjs/webhooks';
import { fromDrizzle, PostgresWebhookStore } from '@nestjs/webhooks/postgres';
import { drizzle } from 'drizzle-orm/node-postgres';
import type { Database } from './database/drizzle.js';
import * as schema from './database/schema.js';
import { OrdersModule } from './orders/orders.module.js';
import { PartnerWebhooksModule } from './partner-webhooks/partner-webhooks.module.js';

@Module({
  imports: [
    // A pg pool on DATABASE_URL, closed in onApplicationShutdown(), after the relay and the
    // worker drained. The services inject it with @InjectDrizzle(), the stores' factories too.
    DrizzleModule.forRootAsync({
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema }),
    }),
    // Outgoing webhooks travel through the outbox: dispatched in the order's transaction,
    // handed to the webhooks worker after the commit.
    OutboxModule.forRootAsync({
      useFactory: () => ({
        relay: { enabled: process.env.OUTBOX_RELAY !== 'off', pollInterval: '1s' },
      }),
    }),
    WebhooksModule.forRootAsync({
      useFactory: () => ({
        // The types partners may subscribe to; dispatch() refuses any other.
        eventTypes: ['order.shipped', 'order.cancelled'],
        // Ten attempts: 5s, 20s, 80s, ... capped at a day, about two days in all.
        retry: { attempts: 10, backoff: { delay: '5s', factor: 4, maxDelay: '1d' } },
        // An endpoint that fails every attempt for five days is switched off.
        disableEndpointAfter: '5d',
        delivery: {
          timeout: '15s',
          // Development only: deliver over http:// and to this machine. Without it, only
          // public https:// endpoints are accepted.
          allowHttp: process.env.WEBHOOKS_ALLOW_LOCAL === '1',
          allowPrivateNetworks: process.env.WEBHOOKS_ALLOW_LOCAL === '1',
        },
        worker: { enabled: process.env.WEBHOOKS_WORKER !== 'off', pollInterval: '1s' },
        // Endpoint secrets at rest: the first key encrypts, every key decrypts.
        encryption: process.env.WEBHOOKS_ENCRYPTION_KEYS
          ? { keys: process.env.WEBHOOKS_ENCRYPTION_KEYS.split(',').map((key) => key.trim()) }
          : undefined,
      }),
    }),
    OrdersModule,
    PartnerWebhooksModule,
  ],
  providers: [
    {
      // Outbox messages and the inbox, in your database, in a schema of their own (nest_outbox)
      provide: PostgresOutboxStore,
      inject: [getDrizzleToken(), OutboxStorage],
      useFactory: (db: Database, outboxStorage: OutboxStorage) =>
        new PostgresOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
    },
    {
      // Endpoints, deliveries and their log, in your database, in a schema of their own (nest_webhooks)
      provide: PostgresWebhookStore,
      inject: [getDrizzleToken(), WebhooksStorage],
      useFactory: (db: Database, webhooksStorage: WebhooksStorage) =>
        new PostgresWebhookStore({ executor: fromDrizzle(db) }, webhooksStorage),
    },
  ],
})
export class AppModule {}
```

`WebhooksModule` cần outbox: `dispatch()` là một lời gọi `Outbox.add()`, và bước phân phối biến một message đã commit thành các lần gửi là một outbox handler. Không có `OutboxModule`, việc khởi động sẽ thất bại và báo rõ điều đó. `relay` của outbox chuyển các message đã commit cho bước phân phối, polling mỗi giây, và `OUTBOX_RELAY=off` tắt nó đi. Các tùy chọn còn lại, được resolve khi ứng dụng khởi động:

- `eventTypes`: các loại message mà ứng dụng này gửi. `dispatch()` từ chối mọi loại khác, và một endpoint cố đăng ký nhận một loại khác cũng vậy, kèm danh sách các loại đã biết trong thông báo.
- `retry`: bộ từ vựng dùng chung với outbox, HTTP client và resilience. Mười lần thử, và một backoff bắt đầu từ 5 giây, tăng gấp bốn và giới hạn ở một ngày, có jitter: đúng như đặc tả Standard Webhooks khuyến nghị, "một lịch retry kéo dài nhiều ngày".
- `disableEndpointAfter`: một endpoint thất bại ở mọi lần thử trong năm ngày mà không có lần thành công nào sẽ bị tắt, và chủ sở hữu của nó được thông báo (xem [Retry, log gửi và gửi lại](/http/webhooks#retries-the-delivery-log-and-replay)).
- `delivery`: một lần thử có 15 giây cho DNS, kết nối, TLS, request và response. `allowHttp` và `allowPrivateNetworks` mặc định tắt: chỉ các endpoint `https://` công khai được chấp nhận. `WEBHOOKS_ALLOW_LOCAL=1` bật chúng trong development, nơi receiver của đối tác chạy trên chính máy này. Các địa chỉ metadata của cloud vẫn bị chặn kể cả khi đó.
- `worker`: bộ gửi chạy nền, mỗi process một cái. `WEBHOOKS_WORKER=off` tắt nó ở những instance chỉ phục vụ API.
- `encryption`: secret của endpoint được niêm phong khi lưu trữ, theo cùng kiểu trong cả loạt package: key đầu tiên mã hóa, mọi key đều giải mã. Tùy chọn, lấy từ `WEBHOOKS_ENCRYPTION_KEYS`.

> info **Gợi ý** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để một biến bị thiếu làm ứng dụng dừng ngay lúc khởi động thay vì ở request đầu tiên, và đọc giá trị từ `ConfigService` (`inject: [ConfigService]` trong các factory).

Khoảng thời gian tính bằng mili giây hoặc chuỗi như `'15s'` và `'5d'`. Cả hai module đều là global: `Webhooks`, `WebhookEndpoints`, `WebhookDeliveries`, `WebhooksEvents` và `WebhooksStorage` có thể được inject ở bất cứ đâu. `main.ts` bind validation pipe cho các DTO của API đối tác (xem phần tiếp theo), và bật shutdown hook, để một đợt deploy cho relay và worker hoàn tất công việc đang dở:

```typescript
@@filename(main)
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // The partner API's DTOs; whitelist: properties without a decorator are dropped.
  app.useGlobalPipes(new ValidationPipe({ whitelist: true }));
  // On SIGTERM the outbox relay and the webhook worker finish what they started.
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Lúc khởi động, cả hai module log store mà chúng dùng, và ở lần khởi động đầu tiên, các store log những schema mà chúng đã tạo:

```bash
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [OutboxModule] OutboxStorage: PostgresOutboxStore
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [WebhooksModule] WebhooksStorage: PostgresWebhookStore
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [OutboxModule] PostgresOutboxStore: migrated schema "nest_outbox" to version 1.
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [WebhooksModule] PostgresWebhookStore: migrated schema "nest_webhooks" to version 1.
```
#### Cho đối tác đăng ký <a id="let-partners-subscribe"></a>

Các trại cứu trợ và đại lý gọi API đối tác bằng một API key: hai đối tác của ví dụ, Northside Pet Supplies (một đại lý) và Riverside Cat Shelter, có các key mẫu trong phần [Cài đặt](/http/webhooks#installation). `PartnerGuard` tra hash của key và đặt đối tác lên request, còn `@CurrentPartner()` đọc nó:

```typescript
@@filename(partners/partner.guard)
import {
  createParamDecorator,
  Injectable,
  UnauthorizedException,
  type CanActivate,
  type ExecutionContext,
} from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { eq } from 'drizzle-orm';
import { createHash } from 'node:crypto';
import type { Database } from '../database/drizzle.js';
import { partners } from '../database/schema.js';

export interface Partner {
  id: string;
  name: string;
}

/** Authenticates a partner by its API key: `Authorization: Bearer <key>`. */
@Injectable()
export class PartnerGuard implements CanActivate {
  constructor(@InjectDrizzle() private readonly db: Database) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<{ headers: Record<string, string>; partner?: Partner }>();
    const key = /^Bearer (\S+)$/.exec(request.headers.authorization ?? '')?.[1];
    if (!key) {
      throw new UnauthorizedException();
    }
    const hash = createHash('sha256').update(key).digest('hex');
    const [partner] = await this.db
      .select({ id: partners.id, name: partners.name })
      .from(partners)
      .where(eq(partners.apiKeyHash, hash));
    if (!partner) {
      throw new UnauthorizedException();
    }
    request.partner = partner;
    return true;
  }
}

/** The partner `PartnerGuard` authenticated. */
export const CurrentPartner = createParamDecorator(
  (_data: unknown, context: ExecutionContext) => context.switchToHttp().getRequest<{ partner: Partner }>().partner,
);
```

Một lần đăng ký gồm một URL, các loại event cần nhận, và một mô tả; một lần cập nhật chỉ gửi những gì thay đổi. Các DTO kiểm tra cấu trúc, và để URL cùng các loại event cho package, vì package biết nó chấp nhận gì. Request body được validate bằng bất cứ công cụ nào ứng dụng đang dùng: mọi DTO trên trang này đều có hai phiên bản, một class với decorator của `class-validator` và một schema Zod, nên hãy chọn kiểu bạn đang dùng và bỏ qua phiên bản còn lại:

```typescript
@@filename(partner-webhooks/webhook-endpoints.dto)
import { IsArray, IsBoolean, IsOptional, IsString } from 'class-validator';

/** Body of `POST /partner/webhook-endpoints`. The package checks the URL and the types themselves. */
export class CreateEndpointDto {
  @IsString()
  url: string;

  /** `order.shipped`, `order.cancelled`, or `*` for both. */
  @IsArray()
  @IsString({ each: true })
  eventTypes: string[];

  @IsOptional()
  @IsString()
  description?: string;
}

/** Body of `PATCH /partner/webhook-endpoints/:id`: only what is sent changes. */
export class UpdateEndpointDto {
  @IsOptional()
  @IsString()
  url?: string;

  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  eventTypes?: string[];

  @IsOptional()
  @IsString()
  description?: string | null;

  @IsOptional()
  @IsBoolean()
  enabled?: boolean;
}
```

Cùng các quy tắc đó dưới dạng schema Zod, với type suy ra từ schema thay cho class. Nest 12.1 validate mọi object [Standard Schema](https://standardschema.dev/), từ Zod, Valibot hay ArkType, thông qua `StandardSchemaValidationPipe`:

```typescript
@@filename(partner-webhooks/webhook-endpoints.schemas)
import { z } from 'zod';

/** Body of `POST /partner/webhook-endpoints`. The package checks the URL and the types themselves. */
export const createEndpointSchema = z.object({
  url: z.string(),
  /** `order.shipped`, `order.cancelled`, or `*` for both. */
  eventTypes: z.array(z.string()),
  description: z.string().optional(),
});
export type CreateEndpointDto = z.infer<typeof createEndpointSchema>;

/** Body of `PATCH /partner/webhook-endpoints/:id`: only what is sent changes. */
export const updateEndpointSchema = z.object({
  url: z.string().optional(),
  eventTypes: z.array(z.string()).optional(),
  description: z.string().nullable().optional(),
  enabled: z.boolean().optional(),
});
export type UpdateEndpointDto = z.infer<typeof updateEndpointSchema>;
```

API đăng ký là một controller bọc quanh `WebhookEndpoints`. Mọi lời gọi đều truyền id của đối tác làm **tenant**: một endpoint được tạo cho tenant đó, được liệt kê cho tenant đó, và id endpoint của một đối tác khác sẽ hoạt động như thể nó không tồn tại:

```typescript
@@filename(partner-webhooks/webhook-endpoints.controller)
import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  NotFoundException,
  Param,
  Patch,
  Post,
  UseGuards,
} from '@nestjs/common';
import { WebhookEndpoints } from '@nestjs/webhooks';
import { CurrentPartner, PartnerGuard, type Partner } from '../partners/partner.guard.js';
import { CreateEndpointDto, UpdateEndpointDto } from './webhook-endpoints.dto.js';

/** A partner's subscriptions. Every call is scoped to the partner: another partner's endpoint is a 404. */
@Controller('partner/webhook-endpoints')
@UseGuards(PartnerGuard)
export class WebhookEndpointsController {
  constructor(private readonly webhookEndpoints: WebhookEndpoints) {}

  /** Returns the endpoint and its secret. The secret is shown this once. */
  @Post()
  create(@CurrentPartner() partner: Partner, @Body() dto: CreateEndpointDto) {
    return this.webhookEndpoints.create({
      url: dto.url,
      eventTypes: dto.eventTypes,
      description: dto.description ?? null,
      tenant: partner.id,
    });
  }

  @Get()
  list(@CurrentPartner() partner: Partner) {
    return this.webhookEndpoints.list({ tenant: partner.id });
  }

  @Get(':id')
  async get(@CurrentPartner() partner: Partner, @Param('id') id: string) {
    const endpoint = await this.webhookEndpoints.get(id, { tenant: partner.id });
    if (!endpoint) {
      throw new NotFoundException(`Webhook endpoint ${id} not found`);
    }
    return endpoint;
  }

  @Patch(':id')
  update(@CurrentPartner() partner: Partner, @Param('id') id: string, @Body() dto: UpdateEndpointDto) {
    return this.webhookEndpoints.update(id, dto, { tenant: partner.id });
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  async delete(@CurrentPartner() partner: Partner, @Param('id') id: string) {
    await this.webhookEndpoints.delete(id, { tenant: partner.id });
  }

  /** A new secret. The old one keeps signing for 24 hours, so the partner can switch without a gap. */
  @Post(':id/rotate-secret')
  @HttpCode(HttpStatus.OK)
  async rotateSecret(@CurrentPartner() partner: Partner, @Param('id') id: string) {
    return { secret: await this.webhookEndpoints.rotateSecret(id, { tenant: partner.id }) };
  }
}
```

Với các schema Zod, tham số body khai báo schema thay vì class:

```typescript
@@filename(partner-webhooks/webhook-endpoints.controller)
import { createEndpointSchema, updateEndpointSchema, type CreateEndpointDto, type UpdateEndpointDto } from './webhook-endpoints.schemas.js';
// ...
@Post()
create(@CurrentPartner() partner: Partner, @Body({ schema: createEndpointSchema }) dto: CreateEndpointDto) {
  // ...
}

@Patch(':id')
update(@CurrentPartner() partner: Partner, @Param('id') id: string, @Body({ schema: updateEndpointSchema }) dto: UpdateEndpointDto) {
  // ...
}
```

> info **Gợi ý** Các DTO chỉ được áp dụng khi có validation pipe: hãy bind `ValidationPipe` ở cấp global, bằng `useGlobalPipes()` trong `main.ts` như phần [Đăng ký các module](/http/webhooks#register-the-modules) làm (`whitelist` bỏ các thuộc tính không có decorator), hoặc dưới dạng provider `APP_PIPE`. Với các schema Zod, hãy bind `StandardSchemaValidationPipe` theo cùng cách: một ứng dụng dùng một trong hai. Trang [validation](/application/validation) có các tùy chọn của mỗi loại.

`create()` trả về endpoint kèm `secret` của nó, một `whsec_…` theo Standard Webhooks gồm 32 byte ngẫu nhiên, được sinh ra tại đây. API này chỉ hiển thị nó đúng một lần này: `list()` và `get()` không bao giờ kèm nó, và một đối tác làm mất nó thì phải xoay vòng. Package giữ secret, được niêm phong khi đặt `encryption`, vì nó dùng secret đó để ký, và `getSecret()` đọc lại secret hiện tại, dành cho một nút "hiện secret" đặt sau một lần đăng nhập mới nếu API của bạn có cung cấp. Các endpoint chuyển từ Svix hoặc một bên gửi Standard Webhooks khác vẫn giữ secret của chúng: một script chuyển đổi truyền `whsec_…` hiện có của đối tác làm `secret` của `create()`, để bộ xác minh của đối tác vẫn hoạt động, và `rotateSecret()` nhận một `secret` được cung cấp theo cùng cách. Package kiểm tra những gì đối tác gửi lên và throw một `InvalidWebhookEndpointError` với status 400: một URL không phải `https://` (hoặc `http://` khi có `allowHttp`), một URL có chứa thông tin đăng nhập, hoặc có host là một địa chỉ bị chặn, như `https://169.254.169.254/latest/meta-data/` hay `https://localhost/`; một loại event không nằm trong `eventTypes`. Lỗi của đối tác được trả về dưới dạng 400, còn id của đối tác khác dưới dạng 404, thông qua một filter:

```typescript
@@filename(partner-webhooks/webhooks-error.filter)
import { Catch, HttpException, type ArgumentsHost } from '@nestjs/common';
import { BaseExceptionFilter } from '@nestjs/core';
import { WebhooksError } from '@nestjs/webhooks';

/**
 * The package's errors carry an HTTP status (400 for an endpoint it refuses, 404 for another
 * partner's endpoint or delivery); this answers with it and the error's message.
 */
@Catch(WebhooksError)
export class WebhooksErrorFilter extends BaseExceptionFilter {
  override catch(error: WebhooksError, host: ArgumentsHost) {
    const status = (error as { status?: number }).status;
    super.catch(status ? new HttpException(error.message, status, { cause: error }) : error, host);
  }
}
```

```typescript
@@filename(partner-webhooks/partner-webhooks.module)
import { Module } from '@nestjs/common';
import { APP_FILTER } from '@nestjs/core';
import { WebhookDeliveriesController } from './webhook-deliveries.controller.js';
import { WebhookEndpointsController } from './webhook-endpoints.controller.js';
import { WebhooksErrorFilter } from './webhooks-error.filter.js';

@Module({
  controllers: [WebhookEndpointsController, WebhookDeliveriesController],
  // Turns the package's errors (a refused URL, another partner's endpoint) into 4xx responses.
  providers: [{ provide: APP_FILTER, useClass: WebhooksErrorFilter }],
})
export class PartnerWebhooksModule {}
```

Controller của log gửi, được thêm vào module này [ở phần sau](/http/webhooks#retries-the-delivery-log-and-replay), cho đối tác nửa còn lại: những gì đã được gửi tới các endpoint của họ.

#### Gửi order.shipped và order.cancelled sau khi commit <a id="send-ordershipped-and-ordercancelled-after-the-commit"></a>

`Webhooks.dispatch()` nhận transaction handle của bạn làm tham số đầu tiên, giống như `Outbox.add()`: với Drizzle, đó là `tx` mà `db.transaction()` truyền cho callback của nó, với type mà service gán cho `Webhooks<Transaction>`. Hủy một đơn hàng sẽ cập nhật nó và dispatch `order.cancelled` trên cùng `tx`; giao nó (do hãng vận chuyển kích hoạt, trong phần [Nhận webhook kiểu Stripe của hãng vận chuyển](/http/webhooks#receive-the-carriers-stripe-like-webhooks)) sẽ cập nhật nó và dispatch `order.shipped`. `tenant` là đối tác đã đặt đơn hàng, nên chỉ các endpoint của đối tác đó mới nhận được nó:

```typescript
@@filename(orders/orders.service)
@Injectable()
export class OrdersService {
  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly webhooks: Webhooks<Transaction>,
  ) {}

  // ...

  /** Cancels an order that hasn't shipped, and tells the partner in the same transaction. */
  async cancelOrder(partner: Partner, id: string, reason: string): Promise<Order> {
    const order = await this.db.transaction(async (tx) => {
      const [row] = await tx
        .select()
        .from(orders)
        .where(and(eq(orders.id, id), eq(orders.partnerId, partner.id)))
        .for('update');
      if (!row) {
        throw new NotFoundException(`Order ${id} not found`);
      }
      if (row.status === 'shipped' || row.status === 'cancelled') {
        throw new ConflictException(`Order ${id} is ${row.status}`);
      }
      await tx.update(orders).set({ status: 'cancelled' }).where(eq(orders.id, id));

      // Drizzle's tx: the webhook is sent only if the cancellation commits, and only to the
      // partner's own endpoints (the tenant).
      const data: OrderCancelled = { orderId: id, reason };
      await this.webhooks.dispatch(tx, { type: 'order.cancelled', tenant: row.partnerId, data });
      return { ...row, status: 'cancelled' as const };
    });

    this.webhooks.notify(); // deliver now instead of at the next poll
    return order;
  }

  // ...

  /** The carrier picked the order up: marks it shipped and tells the partner, in one transaction (the carrier's webhook). */
  async markShipped(tx: Transaction, orderId: string, trackingNumber: string): Promise<Order> {
    const [row] = await tx.select().from(orders).where(eq(orders.id, orderId)).for('update');
    if (!row) {
      throw new NotFoundException(`Order ${orderId} not found`);
    }
    if (row.status !== 'paid') {
      throw new ConflictException(`Order ${orderId} is ${row.status}, not paid`);
    }
    await tx.update(orders).set({ status: 'shipped', trackingNumber }).where(eq(orders.id, orderId));

    const data: OrderShipped = { orderId, trackingNumber };
    await this.webhooks.dispatch(tx, { type: 'order.shipped', tenant: row.partnerId, data });
    return { ...row, status: 'shipped', trackingNumber };
  }
}
```

Không có gì rời khỏi process bên trong transaction. Nếu nó rollback, message chưa bao giờ tồn tại. Nếu nó commit, outbox relay lấy message (`notify()` yêu cầu nó làm việc này ngay thay vì chờ tới lần poll tiếp theo) và chuyển nó cho bước phân phối của package, bước này tạo một lần gửi cho mỗi endpoint đang bật của tenant đã đăng ký nhận loại event đó. Sau đó worker ký và gửi từng lần. Đây là những gì server của Northside nhận được, ở mọi lần thử của lần gửi, với cùng `webhook-id` và chính xác body đã được serialize lúc `dispatch()`:

```http
POST /store/webhooks HTTP/1.1
content-type: application/json
user-agent: NestJS-Webhooks/1.0
webhook-id: msg_01a0f33b898e7341950339801ec3319a
webhook-timestamp: 1790787160
webhook-signature: v1,<base64 HMAC-SHA256 of "msg_01a0f33b898e7341950339801ec3319a.1790787160.{the body}">

{"type":"order.shipped","timestamp":"2026-09-30T16:52:40.462Z","data":{"orderId":"1067d04c-0617-44ac-9a29-67297867329e","trackingNumber":"TRK-4471-0001"}}
```

Chữ ký được tạo bằng secret của endpoint, nên đối tác có thể xác minh nó bằng bất kỳ library Standard Webhooks nào. Hoặc bằng chính package này: receiver của Northside là một ứng dụng Nest riêng, với root module riêng, chỉ để nhận, với `outgoing: false`, và `@VerifyWebhook('store')` trên route của nó. `STORE_WEBHOOK_SECRET` nhận một danh sách phân cách bằng dấu phẩy, vì [việc xoay vòng](/http/webhooks#rotate-secrets) của cửa hàng ký bằng hai secret trong một ngày:

```typescript
@@filename(partner-service/app.module)
import { Module } from '@nestjs/common';
import { OutboxModule } from '@nestjs/outbox';
import { WebhooksModule } from '@nestjs/webhooks';
import { StoreWebhooksController } from './store-webhooks.controller.js';

/**
 * Northside's side: a service that only receives. `outgoing: false` leaves out the
 * endpoints, deliveries and worker. The outbox's inbox deduplicates redeliveries by
 * webhook-id; in memory here, on the partner's own database in production (the outbox's
 * store, as in the outbox tutorial's analytics service).
 */
@Module({
  imports: [
    OutboxModule.forRoot({ relay: { enabled: false } }),
    WebhooksModule.forRootAsync({
      outgoing: false,
      useFactory: () => {
        const secrets = process.env.STORE_WEBHOOK_SECRET;
        if (!secrets) {
          throw new Error('Set STORE_WEBHOOK_SECRET to the secret the store gave this endpoint');
        }
        return {
          receivers: {
            // Every listed secret is tried: keep the old one next to the new one while the store rotates.
            store: { scheme: 'standard', secret: secrets.split(',') },
          },
        };
      },
    }),
  ],
  controllers: [StoreWebhooksController],
})
export class AppModule {}
```

```typescript
@@filename(partner-service/store-webhooks.controller)
import { Controller, HttpCode, HttpStatus, Logger, Post } from '@nestjs/common';
import { IncomingWebhook, VerifyWebhook } from '@nestjs/webhooks';

/** What the store sends: the Standard Webhooks payload, `type`, `timestamp` and `data`. */
export type StoreEvent =
  | { type: 'order.shipped'; timestamp: string; data: { orderId: string; trackingNumber: string } }
  | { type: 'order.cancelled'; timestamp: string; data: { orderId: string; reason: string } };

@Controller('store')
export class StoreWebhooksController {
  private readonly logger = new Logger(StoreWebhooksController.name);

  @Post('webhooks')
  @HttpCode(HttpStatus.NO_CONTENT)
  @VerifyWebhook('store')
  receive(@IncomingWebhook() webhook: IncomingWebhook<StoreEvent>) {
    const event = webhook.payload;
    if (event.type === 'order.shipped') {
      this.logger.log(`Order ${event.data.orderId} shipped, tracking ${event.data.trackingNumber} (${webhook.id})`);
    } else {
      this.logger.log(`Order ${event.data.orderId} cancelled: ${event.data.reason} (${webhook.id})`);
    }
  }
}
```

```typescript
@@filename(partner-service/main)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  // rawBody: the signature is checked on the bytes the store signed, not on a re-serialized body.
  const app = await NestFactory.create(AppModule, { rawBody: true });
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 4100);
}
await bootstrap();
```

`OutboxModule` của đối tác cung cấp inbox mà `@VerifyWebhook()` dùng để loại trùng. Ở đây nó chạy trong bộ nhớ; một đối tác thực tế sẽ đăng ký store của outbox trên database của riêng họ, `PostgresOutboxStore` trên PostgreSQL, như analytics service làm trong [bài hướng dẫn outbox](/reliability/outbox#publish-to-the-analytics-microservice).

#### Retry, log gửi và gửi lại <a id="retries-the-delivery-log-and-replay"></a>

Một response 2xx từ đối tác là thành công. Mọi thứ khác là một lần thử thất bại: 5xx, 4xx, 3xx (redirect không bao giờ được đi theo), timeout, kết nối bị từ chối. Worker retry sau khoảng backoff, tôn trọng header `Retry-After` tính bằng giây hoặc dưới dạng HTTP date (tối đa bằng mức trần của backoff, một ngày; mọi giá trị khác bị bỏ qua), và với lỗi 429, 502, 503 hoặc 504 thì tạm dừng endpoint đó cho đến lúc ấy, năm giây nếu không có header: các lần gửi khác của nó sẽ chờ mà không thử, để một đối tác xin được nghỉ chỉ nhận một lần thăm dò, chứ không phải mỗi lô một lần, trong khi các lần gửi của đối tác khác vẫn tiếp tục. Có ba câu trả lời kết thúc sớm một lần gửi: 410 Gone, câu trả lời này cũng tắt luôn endpoint (`gone`); một đích mà transport từ chối (các bước kiểm tra lúc đăng ký, chạy lại ở mỗi lần gửi, vì DNS có thể thay đổi); và `retry.retryIf` trả lời không. Sau lần thử cuối cùng, lần gửi ở trạng thái `failed` với lý do `exhausted`.

Một endpoint thất bại ở mọi lần thử trong suốt `disableEndpointAfter` sẽ bị tắt với lý do `failing`, và `WebhooksEvents` phát ra `endpoint-disabled`: hãy báo cho đối tác. Một lần thành công bất kỳ lúc nào sẽ reset đồng hồ. Một endpoint bị tắt, dù do worker hay do đối tác (`enabled: false` trong `update()` của đăng ký), sẽ không nhận lần gửi nào cho những gì được dispatch trong lúc nó vẫn bị tắt: bước phân phối bỏ qua nó, và không có gì tạo ra những lần gửi đó sau này. Gửi lại cũng không, vì nó gửi lại những lần gửi đã tồn tại. Những gì tồn tại là các lần gửi đang chờ khi endpoint bị tắt: chúng thất bại với lý do `endpoint-disabled` khi tới lượt, và sau khi bật lại, đối tác có thể yêu cầu gửi lại những lần đó, như những lần gửi thất bại. Bật lại sẽ quên các lần thất bại, và endpoint nhận những gì được dispatch kể từ đó.

Mọi lần thử đều được log: status code, thời gian, 4 KB đầu tiên của body response, lỗi. Đối tác đọc log của riêng họ, và yêu cầu gửi lại một lần gửi, một lần hoặc mọi lần thất bại kể từ khi sự cố bắt đầu. Việc retry hàng loạt nhận một endpoint và thời điểm bắt đầu sự cố, cả hai đều tùy chọn:

```typescript
@@filename(partner-webhooks/webhook-deliveries.dto)
import { IsISO8601, IsOptional, IsString } from 'class-validator';

/** Body of `POST /partner/webhook-deliveries/retry`: every failed delivery since an outage began. */
export class RetryDeliveriesDto {
  /** One endpoint's, or every endpoint's. */
  @IsOptional()
  @IsString()
  endpointId?: string;

  /** Deliveries created at or after this time (ISO 8601): the start of the outage. */
  @IsOptional()
  @IsISO8601()
  since?: string;
}
```

```typescript
@@filename(partner-webhooks/webhook-deliveries.schemas)
import { z } from 'zod';

/** Body of `POST /partner/webhook-deliveries/retry`: every failed delivery since an outage began. */
export const retryDeliveriesSchema = z.object({
  /** One endpoint's, or every endpoint's. */
  endpointId: z.string().optional(),
  /** Deliveries created at or after this time (ISO 8601): the start of the outage. */
  since: z.iso.datetime().optional(),
});
export type RetryDeliveriesDto = z.infer<typeof retryDeliveriesSchema>;
```

```typescript
@@filename(partner-webhooks/webhook-deliveries.controller)
import {
  Body,
  Controller,
  Get,
  HttpCode,
  HttpStatus,
  NotFoundException,
  Param,
  Post,
  Query,
  UseGuards,
} from '@nestjs/common';
import { WebhookDeliveries, type WebhookDeliveryStatus } from '@nestjs/webhooks';
import { CurrentPartner, PartnerGuard, type Partner } from '../partners/partner.guard.js';
import { RetryDeliveriesDto } from './webhook-deliveries.dto.js';

/** A partner's delivery log: what was sent, how each attempt went, and a way to ask for it again. */
@Controller('partner/webhook-deliveries')
@UseGuards(PartnerGuard)
export class WebhookDeliveriesController {
  constructor(private readonly webhookDeliveries: WebhookDeliveries) {}

  /** Newest first. */
  @Get()
  list(
    @CurrentPartner() partner: Partner,
    @Query('endpointId') endpointId?: string,
    @Query('status') status?: WebhookDeliveryStatus,
    @Query('type') type?: string,
  ) {
    return this.webhookDeliveries.list({ tenant: partner.id, endpointId, status, type });
  }

  /** The delivery, the message that was sent, and every attempt: status code, duration, the start of the response. */
  @Get(':id')
  async get(@CurrentPartner() partner: Partner, @Param('id') id: string) {
    const delivery = await this.webhookDeliveries.get(id, { tenant: partner.id });
    if (!delivery) {
      throw new NotFoundException(`Webhook delivery ${id} not found`);
    }
    return delivery;
  }

  /** Sends one delivery again, now, with the same webhook-id: a replay of a lost webhook, or a retry of a failed one. */
  @Post(':id/retry')
  @HttpCode(HttpStatus.OK)
  async retry(@CurrentPartner() partner: Partner, @Param('id') id: string) {
    return { retried: await this.webhookDeliveries.retry(id, { tenant: partner.id }) };
  }

  /** Retries every failed delivery, of one endpoint or all, since an outage began. */
  @Post('retry')
  @HttpCode(HttpStatus.OK)
  async retryFailed(@CurrentPartner() partner: Partner, @Body() dto: RetryDeliveriesDto) {
    const since = dto.since === undefined ? undefined : new Date(dto.since);
    const retried = await this.webhookDeliveries.retry(
      { endpointId: dto.endpointId, status: 'failed', since },
      { tenant: partner.id },
    );
    return { retried };
  }
}
```

Với schema Zod:

```typescript
@@filename(partner-webhooks/webhook-deliveries.controller)
import { retryDeliveriesSchema, type RetryDeliveriesDto } from './webhook-deliveries.schemas.js';
// ...
@Post('retry')
@HttpCode(HttpStatus.OK)
async retryFailed(@CurrentPartner() partner: Partner, @Body({ schema: retryDeliveriesSchema }) dto: RetryDeliveriesDto) {
  // ...
}
```

Một lần retry bắt đầu một vòng mới: `attempts` về 0, gửi ngay lập tức, với cùng `webhook-id` và cùng body. Log của các vòng trước vẫn được giữ lại. Vì id giống nhau, một đối tác có inbox đã lưu nó sẽ trả lời 2xx mà không chạy handler, nên gửi lại cũng an toàn với một webhook đã được giao: Northside có thể yêu cầu gửi lại toàn bộ giờ vừa qua sau khi mất database của họ, và chỉ nhận những gì họ chưa xử lý.

Người vận hành có cùng các khả năng đó thông qua `WebhookDeliveries` mà không cần tenant: `stats()` (số lượng đang chờ, đến hạn, đang lease và thất bại, cùng `lagMs`, thời gian mà lần gửi trễ hạn nhất đã phải chờ, con số cần đặt cảnh báo), `retry()` xuyên các tenant, và `prune('30d')`, thứ không có gì tự gọi giúp bạn. `WebhooksEvents.events$` phát ra `delivered`, `retry-scheduled`, `delivery-failed`, `endpoint-disabled` và `destination-blocked`, mỗi event cũng có trên một channel `node:diagnostics_channel` tên `nestjs:webhooks:<event>`.

#### Nhận webhook của payment provider <a id="receive-the-payment-providers-webhooks"></a>

Payment provider báo cho cửa hàng biết một khoản thanh toán đã thành công bằng một request Standard Webhooks. Xác minh nó cần body đúng như provider đã ký, nên ứng dụng được tạo với `rawBody: true`. Cách này hoạt động trên cả Express lẫn Fastify:

```typescript
@@filename(main)
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  // rawBody: incoming webhooks are verified on the bytes that were signed, not on a re-serialized body.
  const app = await NestFactory.create(AppModule, { rawBody: true });
  // The partner API's DTOs; whitelist: properties without a decorator are dropped.
  app.useGlobalPipes(new ValidationPipe({ whitelist: true }));
  // On SIGTERM the outbox relay and the webhook worker finish what they started.
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Bên gửi được đưa vào `receivers` của module, theo tên mà route sẽ dùng. Secret của payment provider là thứ nó hiển thị trong dashboard:

```typescript
@@filename(app.module)
// The senders whose webhooks this API accepts, by the name @VerifyWebhook() uses.
receivers: {
  // The payment provider follows Standard Webhooks: webhook-id, webhook-timestamp, webhook-signature.
  payments: { scheme: 'standard', secret: process.env.PAYMENTS_WEBHOOK_SECRET! },
  // The carrier copied Stripe's scheme under its own header: Carrier-Signature: t=...,v1=...
  carrier: { scheme: 'stripe', header: 'Carrier-Signature', secret: process.env.CARRIER_WEBHOOK_SECRET! },
},
```

`@VerifyWebhook('payments')` trên route xác minh request trước khi handler chạy, còn `@IncomingWebhook()` cung cấp những gì đã được xác minh: `id` của webhook do bên gửi đặt, `timestamp` đã ký, `payload` được parse từ các byte đã ký, và `processInTransaction()`:

```typescript
@@filename(provider-webhooks/payment-provider-webhooks.controller)
import { Controller, HttpCode, HttpStatus, Logger, Post } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { IncomingWebhook, VerifyWebhook } from '@nestjs/webhooks';
import type { Database } from '../database/drizzle.js';
import { OrdersService } from '../orders/orders.service.js';

/** The payment provider's payload: the Standard Webhooks shape, `type`, `timestamp` and `data`. */
export interface PaymentProviderEvent {
  type: 'payment.succeeded' | 'payment.failed';
  timestamp: string;
  data: { paymentId: string; orderId: string; amount: number };
}

@Controller('webhooks/payments')
export class PaymentProviderWebhooksController {
  private readonly logger = new Logger(PaymentProviderWebhooksController.name);

  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly ordersService: OrdersService,
  ) {}

  @Post()
  @HttpCode(HttpStatus.OK)
  @VerifyWebhook('payments')
  async receive(@IncomingWebhook() webhook: IncomingWebhook<PaymentProviderEvent>) {
    const { type, data } = webhook.payload;
    if (type !== 'payment.succeeded') {
      this.logger.log(`Ignoring ${type} for order ${data.orderId}`);
      return;
    }
    // Exactly once: the webhook's id is recorded in the same transaction as the order's new
    // status, so a redelivery, even one racing this request on another instance, changes nothing.
    const result = await this.db.transaction(async (tx) =>
      webhook.processInTransaction(tx, () => this.ordersService.markPaid(tx, data.orderId, data.paymentId, data.amount)),
    );
    if (!result.duplicate) {
      this.logger.log(`Order ${data.orderId} paid: ${data.paymentId}, ${data.amount} cents`);
    }
  }
}
```

```typescript
@@filename(orders/orders.service)
/** The payment provider confirmed the payment. Runs inside the receiver's transaction. */
async markPaid(tx: Transaction, orderId: string, paymentId: string, amount: number): Promise<Order> {
  const [row] = await tx.select().from(orders).where(eq(orders.id, orderId)).for('update');
  if (!row) {
    throw new NotFoundException(`Order ${orderId} not found`);
  }
  if (row.status !== 'placed') {
    throw new ConflictException(`Order ${orderId} is ${row.status}`);
  }
  if (amount !== row.total) {
    throw new ConflictException(`Payment ${paymentId} is for ${amount}, and order ${orderId} totals ${row.total}`);
  }
  await tx.update(orders).set({ status: 'paid', paymentId }).where(eq(orders.id, orderId));
  return { ...row, status: 'paid', paymentId };
}
```

```typescript
@@filename(provider-webhooks/provider-webhooks.module)
import { Module } from '@nestjs/common';
import { OrdersModule } from '../orders/orders.module.js';
import { CarrierWebhooksController } from './carrier-webhooks.controller.js';
import { PaymentProviderWebhooksController } from './payment-provider-webhooks.controller.js';

/** The webhooks the store receives: the payment provider's payments and the carrier's shipments. */
@Module({
  imports: [OrdersModule],
  controllers: [PaymentProviderWebhooksController, CarrierWebhooksController],
})
export class ProviderWebhooksModule {}
```

Những gì decorator kiểm tra, theo thứ tự: ba header `webhook-` có mặt và đúng định dạng, với `webhook-id` tối đa 255 ký tự, đếm theo code point; một chữ ký `v1,` trong `webhook-signature` khớp với HMAC của `id.timestamp.body` dùng một trong các secret đã cấu hình (so sánh trong thời gian không đổi; có thể liệt kê nhiều secret trong khi payment provider xoay vòng); timestamp đã ký nằm trong khoảng 5 phút so với hiện tại, theo cả hai chiều; body là JSON. Một request không đạt sẽ nhận lỗi 401 với message chung chung. Lý do không bao giờ được gửi cho bên gửi; nó được đưa vào event `verification-failed`, kèm tên receiver. Một body đã ký nhưng không phải JSON sẽ nhận lỗi 400 từ body parser của framework trước khi decorator thấy nó, nên không có event nào được phát ra cho nó. Điều tương tự đúng với một body vượt quá giới hạn kích thước của body parser (mặc định 100 kB trên Express và 1 MiB trên Fastify): nó nhận lỗi 413 trước khi decorator chạy, và không có event nào được phát ra. Nếu payment provider gửi body lớn hơn, hãy nâng giới hạn bằng `useBodyParser()`, như mô tả trong [Raw body](/faq/raw-body#body-parser-size-limit).

Tiếp theo là loại trùng. Payment provider retry cho đến khi nhận được 2xx, nên một timeout xảy ra sau khi handler đã thành công sẽ khiến nó gửi lại cùng `webhook-id`. Receiver giữ một inbox chứa các id nó đã xử lý (inbox của outbox, consumer `webhooks:payments`): một id đã biết sẽ được trả lời bằng 200 rỗng mà không chạy handler, và một id chỉ được ghi nhận sau khi handler thành công, nên một handler đã throw sẽ được chạy lại ở lần retry của payment provider. Hai bản sao đến cùng lúc tại một instance chỉ chạy handler một lần; hai instance nhận chúng đúng cùng một thời điểm có thể cùng chạy, và đoạn tiếp theo là để xử lý trường hợp đó.

`markPaid()` thay đổi state liên quan tới tiền, nên controller tiến thêm một bước với `processInTransaction()`: id của webhook được ghi nhận *thông qua transaction của đơn hàng*, và `markPaid()` chỉ chạy nếu id đó là mới. Bản ghi và trạng thái mới được commit cùng nhau. Một lần gửi lại sau khi crash giữa handler và lúc ghi inbox, hoặc một lần chạy đua với request này trên instance khác, sẽ thấy id và không thay đổi gì; nó resolve với `duplicate` được đặt, thứ mà controller dùng để chỉ log một lần. Và khi `markPaid()` throw, ví dụ một khoản thanh toán sai số tiền, transaction sẽ rollback, kéo theo bản ghi, bên gửi nhận lỗi 409, và lần retry của nó có thêm cơ hội khi đơn hàng đã được sửa.

Để phát triển, một script nhỏ ký request theo cách mà payment provider (và, ở phần tiếp theo, hãng vận chuyển) sẽ làm, bằng `signWebhook()` từ `@nestjs/webhooks/testing`:

```typescript
@@filename(scripts/send-webhook)
/**
 * Sends the signed request the payment provider or the carrier would send, for trying the API by hand:
 *
 *   npx tsx scripts/send-webhook.ts payments payment.succeeded '{"paymentId":"pay_1","orderId":"...","amount":4998}'
 *   npx tsx scripts/send-webhook.ts carrier shipment.shipped '{"orderId":"...","trackingNumber":"TRK-0001"}'
 *
 * Signs with PAYMENTS_WEBHOOK_SECRET or CARRIER_WEBHOOK_SECRET, the secrets the API was
 * started with, and posts to API_URL (default http://localhost:3000). WEBHOOK_ID sends a
 * redelivery with a given id; TAMPER=1 changes a byte of the body after signing it.
 */
import { signWebhook } from '@nestjs/webhooks/testing';
import { randomUUID } from 'node:crypto';

const [sender, type, json = '{}'] = process.argv.slice(2);
if (sender !== 'payments' && sender !== 'carrier') {
  console.error('usage: send-webhook.ts <payments|carrier> <type> <data as JSON>');
  process.exit(2);
}
const data: unknown = JSON.parse(json);
const id = process.env.WEBHOOK_ID;

function secret(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Set ${name}`);
  }
  return value;
}

const signed =
  sender === 'payments'
    ? signWebhook({
        scheme: 'standard',
        secret: secret('PAYMENTS_WEBHOOK_SECRET'),
        id,
        payload: { type, timestamp: new Date().toISOString(), data },
      })
    : signWebhook({
        scheme: 'stripe',
        header: 'Carrier-Signature',
        secret: secret('CARRIER_WEBHOOK_SECRET'),
        payload: { id: id ?? `evt_${randomUUID().replaceAll('-', '')}`, type, data },
      });

const body = process.env.TAMPER ? `${signed.body.slice(0, -1)} }` : signed.body;
const response = await fetch(`${process.env.API_URL ?? 'http://localhost:3000'}/webhooks/${sender}`, {
  method: 'POST',
  headers: signed.headers,
  body,
});
console.log(`${response.status} ${await response.text()}`);
```

#### Nhận webhook kiểu Stripe của hãng vận chuyển <a id="receive-the-carriers-stripe-like-webhooks"></a>

Hãng vận chuyển chép theo kiểu chữ ký của Stripe: một header `Carrier-Signature: t=…,v1=…`, HMAC-SHA256 dạng hex của `t.body` dùng text của secret làm key, và id của event nằm trong payload. Receiver trong [tùy chọn `receivers`](/http/webhooks#receive-the-payment-providers-webhooks) nói rõ điều đó: `scheme: 'stripe'` cùng tên `header`. Webhook của chính Stripe là cùng receiver đó mà không có `header`. Webhook của GitHub, và các bên gửi có kiểu chữ ký riêng, nằm trong phần [Các bên gửi khác](/http/webhooks#other-senders).

Handler mới là phần thú vị. Đánh dấu đơn hàng đã giao và báo cho đối tác diễn ra trong một transaction: trạng thái mới của đơn hàng, message `order.shipped` cho đối tác (qua outbox) và bản ghi inbox của webhook này được commit cùng nhau, hoặc không cái nào cả:

```typescript
@@filename(provider-webhooks/carrier-webhooks.controller)
import { Controller, HttpCode, HttpStatus, Logger, Post } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { IncomingWebhook, VerifyWebhook, Webhooks } from '@nestjs/webhooks';
import type { Database } from '../database/drizzle.js';
import { OrdersService } from '../orders/orders.service.js';

/** The carrier's payload, Stripe-like: the event's `id` is in the body, which is what the signature covers. */
export interface CarrierEvent {
  id: string;
  type: 'shipment.shipped' | 'shipment.delivered';
  data: { orderId: string; trackingNumber: string };
}

@Controller('webhooks/carrier')
export class CarrierWebhooksController {
  private readonly logger = new Logger(CarrierWebhooksController.name);

  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly ordersService: OrdersService,
    private readonly webhooks: Webhooks,
  ) {}

  @Post()
  @HttpCode(HttpStatus.OK)
  @VerifyWebhook('carrier')
  async receive(@IncomingWebhook() webhook: IncomingWebhook<CarrierEvent>) {
    const { type, data } = webhook.payload;
    if (type !== 'shipment.shipped') {
      this.logger.log(`Ignoring ${type} for order ${data.orderId}`);
      return;
    }
    // One transaction: the order's status, the partner's order.shipped webhook (through the
    // outbox) and this webhook's inbox record commit together, or not at all.
    const result = await this.db.transaction(async (tx) =>
      webhook.processInTransaction(tx, () => this.ordersService.markShipped(tx, data.orderId, data.trackingNumber)),
    );
    if (result.duplicate) {
      return;
    }
    this.webhooks.notify(); // deliver order.shipped now instead of at the next poll
    this.logger.log(`Order ${data.orderId} shipped, tracking ${data.trackingNumber}`);
  }
}
```

`markShipped()` là method từ phần [Gửi order.shipped và order.cancelled sau khi commit](/http/webhooks#send-ordershipped-and-ordercancelled-after-the-commit). Id dùng để loại trùng là `id` của event lấy từ payload đã ký, không phải từ header, vì đó là thứ mà kiểu chữ ký của Stripe ký. Một event `shipment.shipped` cho đơn hàng chưa thanh toán sẽ bị từ chối với lỗi 409, và không có gì được ghi nhận: khi hãng vận chuyển retry sau khi khoản thanh toán đã đến, cùng event id đó sẽ được xử lý.

#### Các bên gửi khác <a id="other-senders"></a>

Webhook của GitHub dùng `scheme: 'github'`: `X-Hub-Signature-256`, HMAC-SHA256 dạng hex của body dùng text của secret làm key.

> warning **Cảnh báo** GitHub không ký timestamp hay id. Một request bị bắt được sẽ xác minh được mãi mãi, và việc loại trùng mặc định dựa trên header `X-GitHub-Delivery`, header này không được ký: cùng request đó được gửi lại với một giá trị mới trong header đó sẽ chạy handler lần nữa.

Thay vào đó, hãy loại trùng dựa trên body đã ký, bằng tùy chọn `id` của receiver. Payload được parse từ các byte đã ký, nên một lần gửi lại có cùng id với bản gốc, và inbox sẽ bỏ qua nó:

```typescript
receivers: {
  github: {
    scheme: 'github',
    secret: process.env.GITHUB_WEBHOOK_SECRET!,
    // The signed body, not the unsigned X-GitHub-Delivery header: a replayed request has a known id.
    id: (payload) => createHash('sha256').update(JSON.stringify(payload)).digest('hex'),
  },
},
```

Inbox nhớ một id cho đến khi `OutboxInbox.prune()` xóa nó, nên với GitHub, khoảng thời gian đó cũng chính là khoảng thời gian một lần gửi lại bị bắt được: hãy giữ nó dài. Gửi lại sau khoảng đó, một request vẫn xác minh được và chạy; chỉ chấp nhận webhook của GitHub từ các địa chỉ mà nó công bố (`hooks` trong `https://api.github.com/meta`) sẽ thu hẹp được ai có thể gửi.

Một bên gửi có kiểu chữ ký riêng là một class kế thừa `WebhookSignatureScheme`. Giả sử cửa hàng còn bán qua một sàn thương mại điện tử, sàn này ký URL mà nó post tới, theo sau là body, và đặt id của event trong body:

```typescript
@@filename(provider-webhooks/marketplace.scheme)
import { WebhookSignatureScheme, type WebhookSignatureCheck, type WebhookSignedRequest } from '@nestjs/webhooks';
import { createHmac } from 'node:crypto';

/**
 * The marketplace's scheme: `X-Marketplace-Signature` is the base64 HMAC-SHA256 of the URL it
 * posts to followed by the body, keyed with the secret's text, and the event's id is in the body.
 * A scheme sees the request's headers and raw body, so the URL comes in through the constructor:
 * the one registered in the marketplace's dashboard.
 */
export class MarketplaceScheme extends WebhookSignatureScheme {
  constructor(private readonly url: string) {
    super();
  }

  verify({ headers, rawBody }: WebhookSignedRequest, keys: readonly Buffer[]): WebhookSignatureCheck {
    const signature = headers['x-marketplace-signature'];
    if (signature === undefined) {
      return { valid: false, reason: 'missing-header', detail: 'no x-marketplace-signature header' };
    }
    if (typeof signature !== 'string') {
      return { valid: false, reason: 'malformed-header', detail: 'x-marketplace-signature is repeated' };
    }

    const candidates = [Buffer.from(signature, 'base64')];
    for (const key of keys) {
      const expected = createHmac('sha256', key).update(this.url).update(rawBody).digest();
      // In constant time, never with ===.
      if (WebhookSignatureScheme.matches(expected, candidates)) {
        return { valid: true };
      }
    }
    return { valid: false, reason: 'invalid-signature', detail: 'no signature matches a configured secret' };
  }

  /** The deduplication id: the event's, from the signed body. */
  override idFromPayload(payload: unknown): string | undefined {
    const id = (payload as { eventId?: unknown } | null)?.eventId;
    return typeof id === 'string' ? id : undefined;
  }
}
```

- `verify(request, keys)` nhận `headers` của request (tên viết thường) và `rawBody` của nó, đúng như đã nhận, cùng một key cho mỗi secret đã cấu hình. Nó trả về `valid: true`, kèm `id` của bên gửi khi có header mang id và `timestamp` đã ký tính bằng giây epoch khi kiểu chữ ký có ký timestamp (khi đó `tolerance` của receiver được áp dụng), hoặc `valid: false` kèm `reason` cho event `verification-failed` và một `detail`. Nó chạy đồng bộ, trước khi body được parse thành JSON.
- `WebhookSignatureScheme.matches(expected, candidates)` so sánh trong thời gian không đổi. Đừng bao giờ so sánh chữ ký bằng `===`.
- `idFromPayload(payload, headers)` cung cấp id để loại trùng khi không có header nào mang id, từ body đã parse, như kiểu chữ ký Stripe có sẵn làm với `id` của event. Một id dài hơn 255 ký tự, từ bất kỳ nguồn nào, sẽ bị từ chối với `malformed-header`.
- `key(secret)` chuyển mỗi secret đã cấu hình thành key mà `verify()` nhận được, một lần, lúc khởi động, nơi một secret sai định dạng sẽ làm ứng dụng dừng lại. Mặc định nó lấy text của secret và từ chối secret rỗng hoặc có khoảng trắng bao quanh. Hãy ghi đè nó cho một secret đã được encode, như kiểu chữ ký `standard` làm với `whsec_…`.

Receiver nhận một instance:

```typescript
receivers: {
  marketplace: {
    scheme: new MarketplaceScheme('https://api.store.example.com/webhooks/marketplace'),
    secret: process.env.MARKETPLACE_WEBHOOK_SECRET!,
  },
},
```

#### Xoay vòng secret <a id="rotate-secrets"></a>

Một secret bị lộ, hoặc chính sách của đối tác nói một năm là đủ. `POST /partner/webhook-endpoints/:id/rotate-secret` (xem [Cho đối tác đăng ký](/http/webhooks#let-partners-subscribe)) trả về một secret mới, và secret cũ vẫn tiếp tục ký cạnh nó trong `secretRotationOverlap`, 24 giờ: mỗi lần gửi mang hai chữ ký `v1,`, và một bộ xác minh Standard Webhooks chấp nhận bất kỳ chữ ký nào khớp. Đối tác thêm secret mới vào danh sách, deploy, rồi bỏ secret cũ, theo lịch của riêng họ. Sau khoảng chồng lấn, chỉ secret mới ký. `rotateSecret()` với `overlap: 0` thu hồi secret cũ ngay lập tức, dành cho secret đã bị lộ.

Đặt `WEBHOOKS_ENCRYPTION_KEYS` để niêm phong các secret khi lưu trữ, `openssl rand -base64 32` cho mỗi key, mới nhất trước. Các endpoint tạo trước đó vẫn được đọc (secret của chúng là plaintext) và được niêm phong ở lần xoay vòng tiếp theo.

#### Thử ngay <a id="try-it"></a>

Tạo database, và áp dụng các migration của bạn vào đó, chúng tạo các bảng và dòng dữ liệu của API đơn hàng trong phần [Cài đặt](/http/webhooks#installation):

```bash
$ psql postgres://localhost:5432/postgres -c 'CREATE DATABASE store'
```

Export các secret mà payment provider và hãng vận chuyển dùng chung với cửa hàng (ở đây là bịa ra), cho phép gửi tới máy này, và khởi động API trên port 3000:

```bash
$ export PAYMENTS_WEBHOOK_SECRET=whsec_$(openssl rand -base64 32)
$ export CARRIER_WEBHOOK_SECRET=carrier_test_$(openssl rand -hex 6)
$ export WEBHOOKS_ALLOW_LOCAL=1
```

```bash
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [OutboxModule] OutboxStorage: PostgresOutboxStore
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [WebhooksModule] WebhooksStorage: PostgresWebhookStore
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [OutboxModule] PostgresOutboxStore: migrated schema "nest_outbox" to version 1.
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [WebhooksModule] PostgresWebhookStore: migrated schema "nest_webhooks" to version 1.
[Nest] 55905  - 09/30/2026, 6:52:36 PM     LOG [NestApplication] Nest application successfully started +2ms
```

Các migration của bạn đã tạo các bảng của API đơn hàng, còn các store tạo schema của chúng, nằm cạnh đó. Northside đăng ký, bằng API key của mình, nhận cả hai event tại một receiver mà họ sẽ chạy trên port 4100. Response mang theo secret, đúng một lần này:

```bash
$ curl -s -X POST localhost:3000/partner/webhook-endpoints \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"url":"http://127.0.0.1:4100/store/webhooks","eventTypes":["order.shipped","order.cancelled"],"description":"Warehouse system"}'
{"id":"ep_01a0f33b79e27154b8fd089a10f3e48e","tenant":"northside","url":"http://127.0.0.1:4100/store/webhooks","eventTypes":["order.shipped","order.cancelled"],"description":"Warehouse system","enabled":true,"disabledReason":null,"failingSince":null,"createdAt":1790787156450,"updatedAt":1790787156450,"secret":"whsec_yKaIEKkc0ZpOWofM8Fx1Wc5yxdffKSsP1jolLCynqug="}
$ curl -s localhost:3000/partner/webhook-endpoints -H 'Authorization: Bearer partner_northside_7c1d2e'
[{"id":"ep_01a0f33b79e27154b8fd089a10f3e48e","tenant":"northside","url":"http://127.0.0.1:4100/store/webhooks","eventTypes":["order.shipped","order.cancelled"],"description":"Warehouse system","enabled":true,"disabledReason":null,"failingSince":null,"createdAt":1790787156450,"updatedAt":1790787156450}]
```

> info **Gợi ý** `--json` cần curl 7.82 trở lên.

URL của một dịch vụ metadata cloud bị từ chối trước khi bất cứ thứ gì được lưu, và một loại event mà API không gửi cũng vậy. Riverside Cat Shelter, đối tác còn lại, nhận lỗi 404 với endpoint của Northside:

```bash
$ curl -s -X POST localhost:3000/partner/webhook-endpoints \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"url":"https://169.254.169.254/latest/meta-data/","eventTypes":["*"]}'
{"statusCode":400,"message":"Invalid webhook URL: 169.254.169.254 is link-local (cloud metadata)"}
$ curl -s -X POST localhost:3000/partner/webhook-endpoints \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"url":"https://hooks.northside.example.com/store","eventTypes":["order.paid"]}'
{"statusCode":400,"message":"Unknown message type \"order.paid\". Known: order.shipped, order.cancelled"}
$ curl -s -o /dev/null -w '%{http_code}' localhost:3000/partner/webhook-endpoints/ep_01a0f33b79e27154b8fd089a10f3e48e \
    -H 'Authorization: Bearer partner_riverside_91ab44'
404
```

Khởi động receiver của Northside, `partner-service/main.ts`, trên port 4100, với secret được cấp nằm trong môi trường của nó:

```bash
STORE_WEBHOOK_SECRET=whsec_yKaIEKkc0ZpOWofM8Fx1Wc5yxdffKSsP1jolLCynqug=
```

Giờ hãy đặt một đơn hàng, và để payment provider thanh toán còn hãng vận chuyển giao nó. Script ký các request mà họ sẽ gửi, bằng các secret đã export ở trên:

```bash
$ curl -s -X POST localhost:3000/orders \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"items":[{"productId":"salmon-kibble-2kg","quantity":2}]}'
{"id":"1067d04c-0617-44ac-9a29-67297867329e","partnerId":"northside","items":[{"productId":"salmon-kibble-2kg","quantity":2,"price":2499}],"total":4998,"status":"placed","paymentId":null,"trackingNumber":null}
$ npx tsx scripts/send-webhook.ts payments payment.succeeded \
    '{"paymentId":"pay_8f21c","orderId":"1067d04c-0617-44ac-9a29-67297867329e","amount":4998}'
200
$ npx tsx scripts/send-webhook.ts carrier shipment.shipped \
    '{"orderId":"1067d04c-0617-44ac-9a29-67297867329e","trackingNumber":"TRK-4471-0001"}'
200
$ curl -s localhost:3000/orders/1067d04c-0617-44ac-9a29-67297867329e -H 'Authorization: Bearer partner_northside_7c1d2e'
{"id":"1067d04c-0617-44ac-9a29-67297867329e","partnerId":"northside","items":[{"price":2499,"quantity":2,"productId":"salmon-kibble-2kg"}],"total":4998,"status":"shipped","paymentId":"pay_8f21c","trackingNumber":"TRK-4471-0001"}
```

Log của API cho thấy cả hai webhook đã được xử lý, còn log của Northside cho thấy `order.shipped` đến ngay sau webhook của hãng vận chuyển, kèm `webhook-id` của nó:

```bash
[Nest] 55905  - 09/30/2026, 6:52:39 PM     LOG [PaymentProviderWebhooksController] Order 1067d04c-0617-44ac-9a29-67297867329e paid: pay_8f21c, 4998 cents
[Nest] 55905  - 09/30/2026, 6:52:40 PM     LOG [CarrierWebhooksController] Order 1067d04c-0617-44ac-9a29-67297867329e shipped, tracking TRK-4471-0001
```

```bash
[Nest] 56040  - 09/30/2026, 6:52:40 PM     LOG [StoreWebhooksController] Order 1067d04c-0617-44ac-9a29-67297867329e shipped, tracking TRK-4471-0001 (msg_01a0f33b898e7341950339801ec3319a)
```

Log gửi của Northside có lần gửi đó, và chi tiết của nó có message cùng một lần thử, kèm status code của đối tác và thời gian nó mất:

```bash
$ curl -s localhost:3000/partner/webhook-deliveries -H 'Authorization: Bearer partner_northside_7c1d2e'
[{"id":"dlv_01a0f33b89ac720aa76e2c3da97f3c14","messageId":"msg_01a0f33b898e7341950339801ec3319a","endpointId":"ep_01a0f33b79e27154b8fd089a10f3e48e","tenant":"northside","type":"order.shipped","status":"succeeded","attempts":1,"nextAttemptAt":null,"lastAttemptAt":1790787160533,"lastStatusCode":204,"lastError":null,"failureReason":null,"createdAt":1790787160462,"completedAt":1790787160544}]
$ curl -s localhost:3000/partner/webhook-deliveries/dlv_01a0f33b89ac720aa76e2c3da97f3c14 -H 'Authorization: Bearer partner_northside_7c1d2e'
```

```json
{
  "id": "dlv_01a0f33b89ac720aa76e2c3da97f3c14",
  "messageId": "msg_01a0f33b898e7341950339801ec3319a",
  "endpointId": "ep_01a0f33b79e27154b8fd089a10f3e48e",
  "tenant": "northside",
  "type": "order.shipped",
  "status": "succeeded",
  "attempts": 1,
  "nextAttemptAt": null,
  "lastAttemptAt": 1790787160533,
  "lastStatusCode": 204,
  "lastError": null,
  "failureReason": null,
  "createdAt": 1790787160462,
  "completedAt": 1790787160544,
  "message": {
    "id": "msg_01a0f33b898e7341950339801ec3319a",
    "type": "order.shipped",
    "tenant": "northside",
    "body": "{\"type\":\"order.shipped\",\"timestamp\":\"2026-09-30T16:52:40.462Z\",\"data\":{\"orderId\":\"1067d04c-0617-44ac-9a29-67297867329e\",\"trackingNumber\":\"TRK-4471-0001\"}}",
    "createdAt": 1790787160462
  },
  "history": [
    { "deliveryId": "dlv_01a0f33b89ac720aa76e2c3da97f3c14", "attempt": 1, "at": 1790787160533, "durationMs": 11, "statusCode": 204, "response": "", "error": null }
  ]
}
```

Dừng receiver của Northside bằng `Ctrl+C`, rồi đặt một đơn hàng và hủy nó. Lần gửi không kết nối được, API log thời gian chờ trước lần thử tiếp theo, và log của đối tác cho thấy lần gửi đang chờ kèm lỗi của nó:

```bash
$ curl -s -X POST localhost:3000/orders \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"items":[{"productId":"clumping-litter-10l","quantity":1}]}'
{"id":"d6a36832-6b83-40f6-960b-0c6aa905ae18","partnerId":"northside","items":[{"productId":"clumping-litter-10l","quantity":1,"price":1599}],"total":1599,"status":"placed","paymentId":null,"trackingNumber":null}
$ curl -s -X POST localhost:3000/orders/d6a36832-6b83-40f6-960b-0c6aa905ae18/cancel \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"reason":"out of stock"}'
{"id":"d6a36832-6b83-40f6-960b-0c6aa905ae18","partnerId":"northside","items":[{"price":1599,"quantity":1,"productId":"clumping-litter-10l"}],"total":1599,"status":"cancelled","paymentId":null,"trackingNumber":null}
$ curl -s 'localhost:3000/partner/webhook-deliveries?status=pending' -H 'Authorization: Bearer partner_northside_7c1d2e'
[{"id":"dlv_01a0f33b8f51724da606406a85418fab","messageId":"msg_01a0f33b8f367090b44d3de36eed8f13","endpointId":"ep_01a0f33b79e27154b8fd089a10f3e48e","tenant":"northside","type":"order.cancelled","status":"pending","attempts":1,"nextAttemptAt":1790787164580,"lastAttemptAt":1790787161969,"lastStatusCode":null,"lastError":"Error: connect ECONNREFUSED 127.0.0.1:4100","failureReason":null,"createdAt":1790787161910,"completedAt":null}]
```

```bash
[Nest] 55905  - 09/30/2026, 6:52:42 PM    WARN [WebhookWorker] Retrying webhook delivery dlv_01a0f33b8f51724da606406a85418fab (order.cancelled) in 2609ms (attempt 1 of 10 failed): Error: connect ECONNREFUSED 127.0.0.1:4100
```

Khởi động lại receiver. Lần retry đi qua, và log giữ lại cả hai lần thử:

```bash
[Nest] 56304  - 09/30/2026, 6:52:45 PM     LOG [StoreWebhooksController] Order d6a36832-6b83-40f6-960b-0c6aa905ae18 cancelled: out of stock (msg_01a0f33b8f367090b44d3de36eed8f13)
```

```bash
$ curl -s localhost:3000/partner/webhook-deliveries/dlv_01a0f33b8f51724da606406a85418fab -H 'Authorization: Bearer partner_northside_7c1d2e'
```

```json
{
  "id": "dlv_01a0f33b8f51724da606406a85418fab",
  "type": "order.cancelled",
  "status": "succeeded",
  "attempts": 2,
  "lastStatusCode": 204,
  "history": [
    { "attempt": 1, "at": 1790787161969, "durationMs": 2, "statusCode": null, "response": null, "error": "Error: connect ECONNREFUSED 127.0.0.1:4100" },
    { "attempt": 2, "at": 1790787165060, "durationMs": 11, "statusCode": 204, "response": "", "error": null }
  ]
}
```

Northside yêu cầu gửi lại lần gửi đó. Nó được gửi với cùng `webhook-id`, inbox của receiver nhận ra nó và trả lời 204 mà không chạy handler (không có gì mới trong log của nó), và log gửi cho thấy một vòng mới:

```bash
$ curl -s -X POST localhost:3000/partner/webhook-deliveries/dlv_01a0f33b8f51724da606406a85418fab/retry \
    -H 'Authorization: Bearer partner_northside_7c1d2e'
{"retried":1}
$ curl -s localhost:3000/partner/webhook-deliveries/dlv_01a0f33b8f51724da606406a85418fab -H 'Authorization: Bearer partner_northside_7c1d2e'
```

```json
{
  "status": "succeeded",
  "attempts": 1,
  "history": [
    { "attempt": 1, "at": 1790787161969, "statusCode": null, "error": "Error: connect ECONNREFUSED 127.0.0.1:4100" },
    { "attempt": 2, "at": 1790787165060, "statusCode": 204, "error": null },
    { "attempt": 1, "at": 1790787166185, "statusCode": 204, "error": null }
  ]
}
```

Giờ là phía payment provider. Một lần gửi lại với cùng `webhook-id` (do mất response 200, nên provider đã retry) được trả lời nhưng không được xử lý lại: API chỉ log một khoản thanh toán. Một body bị giả mạo và một secret sai đều bị từ chối, không kèm lý do:

```bash
$ curl -s -X POST localhost:3000/orders \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"items":[{"productId":"salmon-kibble-2kg","quantity":1}]}'
{"id":"d7dbe1ab-c408-4688-9e9e-2925ed2025a3","partnerId":"northside","items":[{"productId":"salmon-kibble-2kg","quantity":1,"price":2499}],"total":2499,"status":"placed","paymentId":null,"trackingNumber":null}
$ WEBHOOK_ID=msg_2c9e4f1a npx tsx scripts/send-webhook.ts payments payment.succeeded \
    '{"paymentId":"pay_9d0a2","orderId":"d7dbe1ab-c408-4688-9e9e-2925ed2025a3","amount":2499}'
200
$ WEBHOOK_ID=msg_2c9e4f1a npx tsx scripts/send-webhook.ts payments payment.succeeded \
    '{"paymentId":"pay_9d0a2","orderId":"d7dbe1ab-c408-4688-9e9e-2925ed2025a3","amount":2499}'
200
$ TAMPER=1 npx tsx scripts/send-webhook.ts payments payment.succeeded \
    '{"paymentId":"pay_9d0a2","orderId":"d7dbe1ab-c408-4688-9e9e-2925ed2025a3","amount":2499}'
401 {"message":"Webhook signature verification failed","error":"Unauthorized","statusCode":401}
$ PAYMENTS_WEBHOOK_SECRET=whsec_$(openssl rand -base64 32) npx tsx scripts/send-webhook.ts payments payment.succeeded \
    '{"paymentId":"pay_9d0a2","orderId":"d7dbe1ab-c408-4688-9e9e-2925ed2025a3","amount":2499}'
401 {"message":"Webhook signature verification failed","error":"Unauthorized","statusCode":401}
```

```bash
[Nest] 55905  - 09/30/2026, 6:52:48 PM     LOG [PaymentProviderWebhooksController] Order d7dbe1ab-c408-4688-9e9e-2925ed2025a3 paid: pay_9d0a2, 2499 cents
```

Cuối cùng, xoay vòng secret của endpoint. Receiver vẫn chạy với secret cũ, và lần gửi tiếp theo vẫn xác minh được: nó mang cả hai chữ ký. Sau đó khởi động lại receiver với secret mới đứng đầu danh sách và secret cũ đứng sau, như cách một đối tác sẽ deploy, rồi đặt và hủy thêm một đơn hàng: lần gửi đó cũng xác minh được:

```bash
$ curl -s -X POST localhost:3000/partner/webhook-endpoints/ep_01a0f33b79e27154b8fd089a10f3e48e/rotate-secret \
    -H 'Authorization: Bearer partner_northside_7c1d2e'
{"secret":"whsec_BUPv/LlKhv9qDH7udP3gsGPquuj4WaopeP8fxyouWOk="}
$ curl -s -X POST localhost:3000/orders/d7dbe1ab-c408-4688-9e9e-2925ed2025a3/cancel \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"reason":"customer changed their mind"}'
{"id":"d7dbe1ab-c408-4688-9e9e-2925ed2025a3","partnerId":"northside","items":[{"price":2499,"quantity":1,"productId":"salmon-kibble-2kg"}],"total":2499,"status":"cancelled","paymentId":"pay_9d0a2","trackingNumber":null}
```

```bash
[Nest] 56304  - 09/30/2026, 6:52:50 PM     LOG [StoreWebhooksController] Order d7dbe1ab-c408-4688-9e9e-2925ed2025a3 cancelled: customer changed their mind (msg_01a0f33bb022712e8e440b7adef8208f)
```

```bash
STORE_WEBHOOK_SECRET=whsec_BUPv/LlKhv9qDH7udP3gsGPquuj4WaopeP8fxyouWOk=,whsec_yKaIEKkc0ZpOWofM8Fx1Wc5yxdffKSsP1jolLCynqug=
```

```bash
$ curl -s -X POST localhost:3000/orders \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"items":[{"productId":"clumping-litter-10l","quantity":2}]}'
{"id":"d203fd6f-7396-489b-9d20-775cd8a6ca4e","partnerId":"northside","items":[{"productId":"clumping-litter-10l","quantity":2,"price":1599}],"total":3198,"status":"placed","paymentId":null,"trackingNumber":null}
$ curl -s -X POST localhost:3000/orders/d203fd6f-7396-489b-9d20-775cd8a6ca4e/cancel \
    -H 'Authorization: Bearer partner_northside_7c1d2e' \
    --json '{"reason":"ordered twice"}'
{"id":"d203fd6f-7396-489b-9d20-775cd8a6ca4e","partnerId":"northside","items":[{"price":1599,"quantity":2,"productId":"clumping-litter-10l"}],"total":3198,"status":"cancelled","paymentId":null,"trackingNumber":null}
```

```bash
[Nest] 56624  - 09/30/2026, 6:52:52 PM     LOG [StoreWebhooksController] Order d203fd6f-7396-489b-9d20-775cd8a6ca4e cancelled: ordered twice (msg_01a0f33bb8ad7249a0fa069361100c49)
```

Các lần gửi là các dòng trong database của bạn, trong schema của store:

```bash
$ psql "$DATABASE_URL" -c "SELECT type, status, attempts, last_status_code FROM nest_webhooks.deliveries ORDER BY created_at"
      type       |  status   | attempts | last_status_code
-----------------+-----------+----------+------------------
 order.shipped   | succeeded |        1 |              204
 order.cancelled | succeeded |        1 |              204
 order.cancelled | succeeded |        1 |              204
 order.cancelled | succeeded |        1 |              204
(4 rows)
```

#### Test <a id="testing"></a>

Trong một e2e test, hãy chạy PostgreSQL ngay trong process bằng [PGlite](https://pglite.dev) với các migration thật của bạn, tắt relay và worker, thay transport bằng transport ghi lại request, và ký request của các provider bằng `signWebhook()`. Ghi đè database mà `DrizzleModule` đăng ký (`getDrizzleToken()` trả về token của nó) bằng một database trên PGlite: các store sẽ theo đó, vì factory của chúng inject nó, và tạo schema của chúng ở đó khi ứng dụng khởi động:

```typescript
@@filename(test/webhooks.e2e-spec)
import { PGlite } from '@electric-sql/pglite';
import type { INestApplication } from '@nestjs/common';
import { getDrizzleToken } from '@nestjs/drizzle';
import { OutboxRelay } from '@nestjs/outbox';
import { Test } from '@nestjs/testing';
import { InMemoryWebhookTransport, WebhookEndpoints, WebhookTransport, WebhookWorker } from '@nestjs/webhooks';
import { signWebhook } from '@nestjs/webhooks/testing';
import { drizzle } from 'drizzle-orm/pglite';
import { migrate } from 'drizzle-orm/pglite/migrator';
import { fileURLToPath } from 'node:url';
import request from 'supertest';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { AppModule } from '../src/app.module.js';
import * as schema from '../src/database/schema.js';
import { OrdersService } from '../src/orders/orders.service.js';

const PAYMENTS_SECRET = `whsec_${Buffer.alloc(32, 1).toString('base64')}`;
const CARRIER_SECRET = 'carrier_test_secret';

describe('Order webhooks', () => {
  const client = new PGlite(); // PostgreSQL, in-process
  const db = drizzle({ client });
  const transport = new InMemoryWebhookTransport(); // records requests instead of sending them
  const partner = { id: 'northside', name: 'Northside Pet Supplies' };
  let app: INestApplication;
  let relay: OutboxRelay;
  let worker: WebhookWorker;
  let endpoint: { id: string; secret: string };

  beforeAll(async () => {
    // The real migrations: the order tables. The stores create their schemas when the app starts.
    await migrate(db, { migrationsFolder: fileURLToPath(new URL('../drizzle', import.meta.url)) });
    process.env.PAYMENTS_WEBHOOK_SECRET = PAYMENTS_SECRET;
    process.env.CARRIER_WEBHOOK_SECRET = CARRIER_SECRET;
    process.env.OUTBOX_RELAY = 'off'; // no poll loops: the test drives the relay and the worker
    process.env.WEBHOOKS_WORKER = 'off';
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(getDrizzleToken())
      .useValue(db) // the stores' factories inject it too
      .overrideProvider(WebhookTransport)
      .useValue(transport)
      .compile();
    app = moduleRef.createNestApplication({ rawBody: true });
    await app.init();
    relay = app.get(OutboxRelay);
    worker = app.get(WebhookWorker);
    endpoint = await app.get(WebhookEndpoints).create({ url: 'https://hooks.northside.example.com/store', eventTypes: ['*'], tenant: partner.id });
  });

  afterAll(async () => {
    await app.close();
    await client.close();
  });

  /** Publishes committed messages (the fan-out), then runs one worker batch. */
  const deliver = async () => {
    await relay.runOnce();
    return worker.runOnce();
  };
  const shipment = (orderId: string, id = 'evt_1') =>
    signWebhook({
      scheme: 'stripe',
      header: 'Carrier-Signature',
      secret: CARRIER_SECRET,
      payload: { id, type: 'shipment.shipped', data: { orderId, trackingNumber: 'TRK-1' } },
    });

  it("sends order.shipped to the partner once the carrier's webhook commits", async () => {
    const order = await app.get(OrdersService).placeOrder(partner, { items: [{ productId: 'salmon-kibble-2kg', quantity: 1 }] });
    const paid = signWebhook({
      scheme: 'standard',
      secret: PAYMENTS_SECRET,
      payload: { type: 'payment.succeeded', data: { paymentId: 'pay_1', orderId: order.id, amount: order.total } },
    });
    await request(app.getHttpServer()).post('/webhooks/payments').set(paid.headers).send(paid.body).expect(200);
    const shipped = shipment(order.id);
    await request(app.getHttpServer()).post('/webhooks/carrier').set(shipped.headers).send(shipped.body).expect(200);
    expect(transport.sent).toEqual([]); // nothing until the outbox relays the commit

    expect(await deliver()).toMatchObject({ delivered: 1 });

    const sent = transport.single({ type: 'order.shipped', endpointId: endpoint.id });
    expect(sent.data).toEqual({ orderId: order.id, trackingNumber: 'TRK-1' });
    expect(sent.isSignedWith(endpoint.secret)).toBe(true);
  });

  it('processes a redelivered shipment webhook once', async () => {
    const [order] = await db.select().from(schema.orders);
    const shipped = shipment(order!.id);
    await request(app.getHttpServer()).post('/webhooks/carrier').set(shipped.headers).send(shipped.body).expect(200, '');
    expect(await deliver()).toMatchObject({ claimed: 0 });
    expect(transport.sent).toHaveLength(1);
  });

  it('refuses a webhook whose body was altered', async () => {
    const shipped = shipment('order-x', 'evt_2');
    await request(app.getHttpServer())
      .post('/webhooks/carrier')
      .set(shipped.headers)
      .send(shipped.body.replace('TRK-1', 'TRK-2'))
      .expect(401);
    expect(await deliver()).toMatchObject({ claimed: 0 });
  });
});
```

- Outbox, cả hai store, các migration, bước phân phối, việc ký và việc xác minh đều là thật. Chỉ có mạng là bị thay thế: `InMemoryWebhookTransport` trả lời 200 và giữ lại mọi request, còn `respondWith(503)` hoặc một hàm giả lập một đối tác đang bị sập, chậm, hoặc khó tính.
- `deliver()` là toàn bộ pipeline sau khi commit: `relay.runOnce()` publish các message đã commit (bước phân phối tạo các lần gửi), `worker.runOnce()` lấy một lô và gửi nó.
- `SentWebhook.isSignedWith(secret)` xác minh chữ ký `v1` bằng secret của một endpoint, còn `data` là `data` của body, nên bài test kiểm tra đúng những gì đối tác lẽ ra sẽ xác minh và đọc.
- `signWebhook()` tạo ra body và header mà payment provider, Stripe hay GitHub sẽ gửi. Dùng lại `id` của nó cho một lần gửi lại, dịch `timestamp` để test khoảng dung sai, đổi một byte của body cho một request bị giả mạo.
- Với các hành vi phụ thuộc thời gian, như backoff, lease và khoảng chồng lấn khi xoay vòng, hãy đẩy `Date.now()` tới trước bằng `vi.spyOn(Date, 'now')`. Worker và các store lấy thời gian từ nó, còn timer thật vẫn tiếp tục chạy cho socket.
- `tutorial.e2e-spec.ts` của ví dụ chạy mọi phần trên trang này qua HTTP thật, trên PGlite và trên một PostgreSQL server: API gửi tới receiver của đối tác qua transport mặc định, với sự cố, việc gửi lại, các lần gửi trùng và việc xoay vòng. `zod.e2e-spec.ts` của nó khởi động cùng app đó với các biến thể Zod của DTO và `StandardSchemaValidationPipe`. Các test store của nó chạy các store thông qua Drizzle trên PGlite, PostgreSQL và MySQL, và thông qua TypeORM trên PostgreSQL: các bộ test hợp đồng, một lần dispatch commit và rollback cùng đơn hàng, và các schema trên production.

Xem [End-to-end test](/fundamentals/testing#end-to-end-testing) để biết thêm về việc thiết lập test.
#### Đảm bảo khi gửi <a id="delivery-guarantees"></a>

Webhook gửi đi được giao **ít nhất một lần**; bên nhận loại trùng dựa trên `webhook-id`.

| Tình huống | Kết quả |
| --- | --- |
| Transaction của đơn hàng bị rollback | Message chưa bao giờ tồn tại và không có gì được gửi |
| Transaction của đơn hàng được commit | Một lần gửi cho mỗi endpoint đã đăng ký của tenant, cuối cùng sẽ được giao hoặc thất bại kèm log các lần thử |
| Outbox gửi lại message (một relay bị crash sau bước phân phối) | Bước phân phối là idempotent: một lần gửi cho mỗi message và endpoint |
| Endpoint được tạo sau message, hoặc đang bị tắt | Nó không nhận được message, và việc gửi lại cũng không mang nó trở lại |
| Một worker chết sau khi đã lấy (claim) | Được một worker khác gửi khi lease hết hạn (`worker.lease`, 1 phút) |
| Một worker chết sau khi gửi, trước khi ghi nhận | **Bị gửi hai lần**, với cùng `webhook-id`, khi lease hết hạn |
| Hai worker, cùng một lần gửi | Một lần claim là độc quyền trong suốt lease, và mọi thao tác ghi sau đó đều được rào chắn bởi lease |
| Đối tác trả lời 2xx | Đã giao |
| Đối tác trả lời bất cứ gì khác, hoặc không trả lời | Retry có backoff, tôn trọng `Retry-After`; 429, 502, 503 và 504 điều tiết tốc độ của endpoint |
| Đối tác trả lời 410 Gone | Thất bại (`rejected`), và endpoint bị tắt (`gone`) |
| Mọi lần thử thất bại trong suốt `disableEndpointAfter` | Endpoint bị tắt (`failing`), một lần |
| Đối tác yêu cầu gửi lại | Một vòng mới với cùng `webhook-id`, nên inbox của họ bỏ qua nó |

Các lần gửi **không có thứ tự**. Một worker gửi các lần gửi của một endpoint từng cái một, trễ hạn nhất trước, nhưng một lần thử thất bại phải chờ hết backoff trong khi các message sau vẫn được gửi đi, nhiều worker gửi tới cùng một endpoint cùng lúc, và một lần gửi lại sẽ gửi một message cũ ngay bây giờ. Hai lần cập nhật của cùng một đơn hàng có thể đến tay đối tác theo bất kỳ thứ tự nào. Bên nhận xử lý điều này giống như xử lý bản trùng: `timestamp` trong body là thời điểm message được dispatch (`webhook-timestamp` là thời điểm lần thử này được ký), nên một handler có thể bỏ qua một event cũ hơn state mà nó đang giữ, hoặc xem webhook như một tín hiệu rồi đọc state hiện tại từ API.

Webhook nhận vào chạy handler **một lần cho mỗi webhook id và receiver trong trường hợp thông thường** với inbox mặc định (chạy lại sau khi crash giữa handler và lúc ghi inbox, hoặc khi hai bản sao chạy đua trên hai instance), còn công việc trong `processInTransaction()` của chúng chạy **đúng một lần**.

#### Checklist cho production <a id="production-checklist"></a>

- Giữ endpoint và các lần gửi trong database của ứng dụng, trên một database server: đăng ký `PostgresWebhookStore`, hoặc `MySqlWebhookStore`, cùng store của outbox bên cạnh nó ([Giữ webhook trong database của bạn](/http/webhooks#keep-webhooks-in-your-database)). Cơ chế bảo vệ trên production từ chối khởi động trong bộ nhớ; `allowInMemoryStorage` dành cho một process mà bạn chấp nhận được việc mất các lần gửi đang chờ.
- Áp dụng migration của cả hai store trước khi phiên bản mới khởi động, bằng `npx @nestjs/webhooks migrate` và `npx @nestjs/outbox migrate` hoặc công cụ migration của bạn, và kiểm tra chúng trong CI bằng `status`. Với `NODE_ENV=production`, các store không migrate lúc khởi động: một schema lạc hậu sẽ làm việc khởi động thất bại.
- Trên PostgreSQL, giữ isolation mặc định của database ở READ COMMITTED: các store từ chối một level chặt hơn. Trên MySQL, hãy chạy lại một transaction khi MySQL phá deadlock trong nó (lỗi 1213): nó đã rollback, kéo theo các message nó đã dispatch và các webhook nó đã ghi nhận.
- Hãy để `delivery.allowHttp` và `delivery.allowPrivateNetworks` tắt. URL của đối tác là dữ liệu không đáng tin, và transport tự resolve nó rồi cố định địa chỉ đã kiểm tra. Dùng `allowedAddresses` cho một dải địa chỉ private mà bạn thực sự cần gửi tới, và đặt cảnh báo cho các event `destination-blocked`: một khách hàng trỏ webhook vào dịch vụ metadata của bạn là chuyện đáng để mắt tới.
- Chạy worker trên vài instance (`WEBHOOKS_WORKER`), không phải trên mọi pod API: mỗi lần claim là một transaction ngắn, và các lease ngăn chúng gửi cùng một lần gửi hai lần.
- Đặt cảnh báo cho `lagMs` và `failed` từ `deliveries.stats()`, và cho `endpoint-disabled`: hãy báo cho đối tác, qua email, rằng endpoint của họ đã bị tắt và vì sao.
- Đánh version cho payload. Một đối tác giữ handler của họ trong nhiều năm, và `retry()` gửi lại body đúng như lúc được dispatch. Hãy thêm trường vào `data` của một loại event, đừng bao giờ đổi tên hay xóa trường. Với một thay đổi phá vỡ tương thích, hãy thêm một loại mới, `order.shipped.v2` trong `eventTypes`, và dispatch cả hai trong cùng transaction (`dispatch()` nhận một mảng) trong khi các đối tác chuyển đăng ký sang; một endpoint đăng ký `*` sẽ nhận cả hai. Sau đó ngừng dispatch loại cũ. Các lần gửi lại message cũ vẫn mang cấu trúc cũ cho đến khi log được dọn.
- Cung cấp cho đối tác log gửi và tính năng gửi lại. Nó trả lời câu "anh đã gửi chưa?" trước khi họ phải mở ticket.
- Xoay vòng secret có khoảng chồng lấn, đừng bao giờ dùng `overlap: 0` trừ khi secret đã bị lộ, và niêm phong chúng khi lưu trữ bằng `WEBHOOKS_ENCRYPTION_KEYS`. Giữ các key trong một secret manager.
- Dọn log. Chạy `deliveries.prune('30d')` từ một [cron job](/application/task-scheduling#declarative-cron-jobs); không có gì tự lên lịch việc này giúp bạn.
- Với webhook nhận vào, giữ `rawBody: true`, và giữ secret của các receiver trong biến môi trường. Liệt kê cả secret cũ lẫn mới trong khi một provider xoay vòng.
- Giữ handler của provider ngắn gọn và tự thân idempotent (một bước kiểm tra trạng thái bên trong transaction), kể cả khi dùng `processInTransaction()`: inbox bảo vệ khỏi một lần gửi lại, còn bước kiểm tra bảo vệ khỏi một provider gửi hai event khác nhau cho cùng một sự việc.
- Dọn inbox bằng `OutboxInbox.prune()` với một khoảng thời gian dài hơn lịch retry của mọi provider (Stripe retry trong ba ngày, GitHub hoàn toàn không retry). Với GitHub, khoảng thời gian đó cũng là khoảng thời gian một request gửi lại bị bắt được, khi loại trùng dựa trên body ([Các bên gửi khác](/http/webhooks#other-senders)).
- Gọi `app.enableShutdownHooks()`, để một đợt deploy cho các lần thử đang dở hoàn tất và trả lại phần còn lại.
- Với store của riêng bạn, hãy chạy các bộ test hợp đồng với `concurrent: true` trong CI, trên đúng phiên bản database mà bạn chạy trên production.

#### Hợp đồng của store <a id="the-store-contract"></a>

`PostgresWebhookStore` và `MySqlWebhookStore` implement cả hai hợp đồng của package, `WebhookEndpointStore` và `WebhookDeliveryStore`. Với một database khác, hãy implement chúng trong một provider của riêng bạn. JSDoc của mỗi method trong hai interface nêu quy tắc của nó, và cuộc đua mà nó ngăn chặn.

**Đăng ký.** Store là một singleton provider thông thường, gọi `registerSource()` trên `WebhooksStorage` có thể inject trong constructor của nó, nêu tên các hợp đồng mà nó implement: `endpoints`, `deliveries`, hoặc cả hai từ một class. Registry kiểm tra cấu trúc ngay lập tức, từ chối lần đăng ký thứ hai trừ khi nó truyền `replace: true`, và khóa lại khi `WebhooksModule` khởi tạo, log store đang được dùng. Khi không có gì được đăng ký, module dùng `InMemoryWebhookStore`, store này mất các endpoint và các lần gửi đang chờ khi khởi động lại và không chia sẻ được giữa các instance. Với `NODE_ENV=production`, việc khởi động sẽ thất bại, trừ khi `allowInMemoryStorage: true` chấp nhận điều đó.

**Không có transaction handle.** Khác với `add()` của outbox, không method nào ở đây nhận transaction của bạn: outbox mang message ra khỏi transaction của bạn, còn webhook store chạy trên kết nối riêng của nó.

**Các method.** Những method được đánh dấu nguyên tử là một câu lệnh có điều kiện duy nhất hoặc một transaction có row lock, không bao giờ là đọc rồi ghi; đó là những method mà các bộ test hợp đồng cho chạy đua.

| Method | Nó làm gì | Nguyên tử |
| --- | --- | --- |
| `createEndpoint`, `getEndpoint`, `listEndpoints`, `updateEndpoint`, `deleteEndpoint` | Vòng đời của một endpoint; `list` mới nhất trước, theo tenant | Không |
| `findSubscribedEndpoints(tenant, type)` | Các endpoint đang bật của đúng tenant này đã đăng ký nhận loại event đó (hoặc `*`): query của bước phân phối | Không, nhưng bộ test kiểm tra nó không bao giờ trả về endpoint của tenant khác |
| `addEndpointSecret(id, secret, expireOthersAt, now)` | Việc xoay vòng: secret mới đứng đầu, các secret khác sắp hết hạn | Có: dòng dữ liệu bị khóa, nên hai lần xoay vòng đều được ghi nhận |
| `recordEndpointFailure(id, failure)` | Đặt `failingSince` ở lần thất bại đầu tiên; tắt endpoint khi nó đã thất bại đủ lâu, và báo điều đó một lần | Có: dòng dữ liệu bị khóa |
| `recordEndpointSuccess(id)` | Xóa `failingSince` | Không |
| `createDeliveries(message, deliveries)` | Bước phân phối: message nếu chưa tồn tại, mỗi lần gửi nếu `(messageId, endpointId)` của nó chưa tồn tại | Có: một key duy nhất trên cặp này, như `ON CONFLICT DO NOTHING` của PostgreSQL trên nó |
| `claimDeliveries(request)` | Lease các lần gửi đến hạn, trễ hạn nhất trước, kèm message của chúng | Có: `FOR UPDATE SKIP LOCKED`, rồi đến lease |
| `recordDeliveryAttempt(id, owner, update)` | Kết quả và dòng log của lần thử, nếu `owner` vẫn còn giữ lease | Có: được rào chắn bởi chủ sở hữu lease |
| `releaseDeliveries(ids, owner, nextAttemptAt)` | Trả lại lease, hoãn lại khi được yêu cầu | Có: được rào chắn |
| `getDelivery`, `getMessage`, `listDeliveries`, `listDeliveryAttempts`, `deliveryStats` | Các thao tác đọc; `list` mới nhất trước, theo tenant, endpoint, message, trạng thái và loại | Không |
| `retryDeliveries(filter, now)` | Một vòng mới cho những lần gửi khớp điều kiện mà không đang bị lease | Có: một câu `UPDATE` với lease nằm trong `WHERE` |
| `pruneDeliveries(before)` | Các lần gửi đã kết thúc cũ hơn `before`, log của chúng, và các message không còn lần gửi nào | Không, nhưng không bao giờ xóa một lần gửi đang chờ |

**Test nó** bằng `webhookEndpointStoreContract()` và `webhookDeliveryStoreContract()` từ `@nestjs/webhooks/testing`. Mỗi case nhận một store trên các bảng rỗng từ hàm mà bạn truyền vào. Các test của bài hướng dẫn chạy cả hai bộ test với `PostgresWebhookStore` thông qua Drizzle, giống như bạn sẽ làm với store của mình:

```typescript
@@filename(test/drizzle-webhook.store.e2e-spec)
/** A store on emptied tables, built the way Nest builds it: with the database and a registry. */
async function freshStore(db: Database) {
  await db.execute(sql.raw(`TRUNCATE ${STORE_TABLES.join(', ')} RESTART IDENTITY`));
  return { store: new PostgresWebhookStore({ executor: fromDrizzle(db) }, new WebhooksStorage()) };
}

// ...

// The concurrency cases run too; with one connection, PGlite runs them one statement at a time.
describe('the endpoint contract', () => {
  for (const c of webhookEndpointStoreContract(() => freshStore(db), { concurrent: true })) {
    it(c.name, c.run);
  }
});
describe('the delivery contract', () => {
  for (const c of webhookDeliveryStoreContract(() => freshStore(db), { concurrent: true })) {
    it(c.name, c.run);
  }
});
```

Với `concurrent: true`, các bộ test cho chạy đua việc xoay vòng và các lần thất bại trên một endpoint, các worker claim song song, các lần phân phối của cùng một message, một worker cũ đối đầu với một lần tiếp quản, và một lần retry đối đầu với một lần claim. Trên PGlite, với một kết nối, chúng qua được vì bị tuần tự hóa: hãy chạy chúng trên cả một server, thông qua một pool có nhiều kết nối, nơi một store thiếu các lock phù hợp sẽ thất bại. Các test của chính package chạy các bộ test với một store Drizzle viết tay, như bằng chứng rằng một store viết theo các interface sẽ qua được chúng.
#### Tham khảo <a id="reference"></a>

##### Tùy chọn module <a id="module-options"></a>

`WebhooksModule.forRoot()` nhận các tùy chọn này. `forRootAsync()` nhận `outgoing`, `transport` (dưới dạng class), `imports` và `isGlobal` ở cấp cao nhất, cạnh `useFactory`, `useClass` hoặc `useExisting`, còn factory trả về phần còn lại. Xem [Đăng ký các module](/http/webhooks#register-the-modules).

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `eventTypes` | mọi loại | Các loại message mà ứng dụng này gửi. `dispatch()` và các endpoint mới chỉ chấp nhận những loại này (endpoint còn chấp nhận `*`). |
| `retry` | 10 lần thử | `attempts` (tính cả lần đầu), `backoff` và `retryIf(error, attempt, delivery)`. Một số sẽ đặt `attempts`, còn `false` nghĩa là chỉ thử một lần. |
| `retry.backoff` | xem mô tả | `delay` (`'5s'`), `factor` (4), `maxDelay` (`'1d'`, cũng là mức trần cho `Retry-After`), `jitter`: `'equal'`, `'full'` hoặc `'none'` (`'equal'`). Hoặc một hàm nhận lần thử, lỗi và lần gửi rồi trả về một khoảng thời gian. |
| `disableEndpointAfter` | `'5d'` | Tắt một endpoint đã thất bại ở mọi lần thử trong khoảng thời gian này mà không có lần thành công nào. `false` thì không bao giờ tắt. |
| `secretRotationOverlap` | `'24h'` | Thời gian một secret đã bị xoay ra vẫn tiếp tục ký cạnh secret mới. |
| `delivery.timeout` | `'15s'` | Một lần thử: DNS, kết nối, TLS, request và response. Ngắn hơn `worker.lease`. |
| `delivery.allowHttp` | `false` | Chấp nhận URL endpoint `http://`. Dành cho development. |
| `delivery.allowPrivateNetworks` | `false` | Gửi tới các dải loopback, private, shared-address và unique-local. Dành cho development. Các địa chỉ link-local và metadata của cloud vẫn bị chặn. |
| `delivery.allowedAddresses` | không có | Các dải CIDR, như `10.20.0.0/16`, vẫn được gửi tới dù lẽ ra bị chặn. |
| `delivery.maxResponseSize` | 4096 | Số byte của body response được đọc và giữ lại trong log. |
| `delivery.userAgent` | `NestJS-Webhooks/1.0` | Header `User-Agent`. |
| `worker.enabled` | `true` | Gửi trong process này. `false` ở những instance chỉ dispatch. |
| `worker.pollInterval` | `'1s'` | Khoảng chờ giữa các lần poll khi rảnh. `notify()` poll ngay lập tức. |
| `worker.batchSize` | 50 | Số lần gửi được claim mỗi lần poll. |
| `worker.concurrency` | 10 | Số endpoint được gửi song song. Các lần gửi của một endpoint đi từng cái một. |
| `worker.lease` | `'1m'` | Thời gian một lần claim là độc quyền. Dài hơn `delivery.timeout`. |
| `encryption` | tắt | Niêm phong secret của endpoint khi lưu trữ. `keys` liệt kê các `Buffer` 32 byte hoặc chuỗi ít nhất 32 ký tự, mới nhất trước: key đầu tiên mã hóa, mọi key đều giải mã. |
| `receivers` | không có | Các bên gửi mà ứng dụng này chấp nhận webhook của họ, theo tên mà `@VerifyWebhook()` dùng (xem bảng tiếp theo). |
| `transport` | `HttpWebhookTransport` | Một class `WebhookTransport` ở cấp cao nhất, hoặc một instance từ factory bất đồng bộ. |
| `allowInMemoryStorage` | `false` | Cho phép ứng dụng production khởi động mà không có store nào được đăng ký. |
| `outgoing` | `true` | Chỉ ở cấp cao nhất. `false` trong service chỉ nhận webhook: không có endpoint, lần gửi, worker hay store. |
| `imports` | không có | Chỉ ở cấp cao nhất. Các module có export mà một class transport inject. |
| `isGlobal` | `true` | Chỉ ở cấp cao nhất. Đăng ký module ở cấp global. |

Khoảng thời gian tính bằng mili giây hoặc chuỗi như `'15s'`, `'24h'` hay `'5d'`. Injection token của các tùy chọn là `WEBHOOKS_MODULE_OPTIONS`.

Mỗi mục của `receivers` nhận các tùy chọn sau (xem [Nhận webhook của payment provider](/http/webhooks#receive-the-payment-providers-webhooks) và [Nhận webhook kiểu Stripe của hãng vận chuyển](/http/webhooks#receive-the-carriers-stripe-like-webhooks)):

| Tùy chọn | Áp dụng cho | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `scheme` | tất cả | bắt buộc | `'standard'`, `'stripe'`, `'github'`, hoặc một instance của class kế thừa `WebhookSignatureScheme` |
| `secret` | tất cả | bắt buộc | Một secret, hoặc một mảng trong lúc bên gửi xoay vòng. Mọi secret đều được thử. |
| `tolerance` | `standard`, `stripe`, tùy chỉnh | `'5m'` | Khoảng cách lớn nhất được chấp nhận giữa timestamp đã ký và hiện tại, theo cả hai chiều |
| `header` | `stripe` | `'stripe-signature'` | Header chữ ký, cho các bên gửi chép theo kiểu chữ ký của Stripe |
| `id` | `stripe`, `github` | `id` của payload; header `X-GitHub-Delivery`, header này không được ký (xem [Các bên gửi khác](/http/webhooks#other-senders)) | Một hàm nhận payload và header rồi trả về id để loại trùng, tối đa 255 ký tự |
| `dedupe` | tất cả | `true` | Bỏ qua một webhook id mà receiver này đã xử lý |
| `consumer` | tất cả | `webhooks:<name>` | Tên consumer của inbox. Hãy giữ nó ổn định. Tối đa 255 ký tự, kể cả giá trị mặc định: tên dài hơn sẽ làm việc khởi động thất bại với một `TypeError` |

##### Store PostgreSQL và MySQL <a id="postgresql-and-mysql-stores"></a>

`new PostgresWebhookStore(options, webhooksStorage)`, từ `@nestjs/webhooks/postgres`, và `new MySqlWebhookStore(options, webhooksStorage)`, từ `@nestjs/webhooks/mysql`, nhận các tùy chọn sau. `PostgresOutboxStore` và `MySqlOutboxStore` của outbox nhận cùng các tùy chọn đó, với `'nest_outbox'` là `schema` mặc định:

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `executor` | Bắt buộc | Cách store tiếp cận database: `fromDrizzle(db)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma, options)`, `fromKysely(db)`, và `fromPg(pool)` trên PostgreSQL hoặc `fromMysql2(pool)` trên MySQL, import từ chính subpath của store: executor của dialect kia sẽ không compile được |
| `schema` | `'nest_webhooks'` | Trên PostgreSQL, là schema chứa các bảng của nó, được migration đầu tiên tạo ra: chữ cái, chữ số và dấu gạch dưới, không bắt đầu bằng chữ số, tối đa 63 ký tự. Trên MySQL, là prefix cho các bảng của nó trong database của kết nối (`nest_webhooks_endpoints`...): chữ thường, chữ số và dấu gạch dưới, không bắt đầu bằng chữ số, tối đa 40 ký tự |
| `migrate` | `true`, trừ khi `NODE_ENV=production` | Áp dụng các migration đang chờ khi ứng dụng khởi động. Với `false`, việc khởi động thất bại với một `WebhookSchemaError` khi schema còn lạc hậu |

Mỗi executor nhận database client của bạn, và loại object transaction riêng của nó, thứ mà `dispatch()` và `processInTransaction()` sau đó sẽ nhận:

| Executor | Nhận | Object transaction |
| --- | --- | --- |
| `fromDrizzle(db)` | Một database Drizzle: trên PostgreSQL, với bất kỳ driver nào; trên MySQL, của `drizzle-orm/mysql2` | `tx` mà `db.transaction()` truyền cho callback của nó |
| `fromTypeOrm(dataSource)` | Một `DataSource` có type `postgres` hoặc `mysql` | `EntityManager` mà `dataSource.transaction()` truyền cho callback của nó, hoặc một `QueryRunner` sau `startTransaction()` |
| `fromPg(pool)` | Một `Pool` của node-postgres, trên PostgreSQL | Một client từ `pool.connect()`, sau `BEGIN` |
| `fromMysql2(pool)` | Một pool `mysql2/promise`, trên MySQL | Một connection từ `pool.getConnection()`, sau `beginTransaction()` |
| `fromPrisma(prisma, options)` | Một Prisma client, thông qua driver adapter như `@prisma/adapter-pg`, hoặc `@prisma/adapter-mariadb` trên MySQL. `maxWait` (mặc định `'10s'`) và `timeout` (mặc định `'1m'`) giới hạn các transaction riêng của store | Transaction client mà `prisma.$transaction()` truyền cho callback của nó |
| `fromKysely(db)` | Một instance `Kysely` với dialect PostgreSQL hoặc MySQL | Transaction mà `db.transaction().execute()` truyền cho callback của nó |

Method `migrate()` của store áp dụng ngay các migration đang chờ, bất kể tùy chọn `migrate` nói gì, và resolve ra các version mà nó đã áp dụng. `PostgresWebhookStore.migrationSql()` và `MySqlWebhookStore.migrationSql()` trả về SQL của chúng, kèm phần ghi nhận version. Tùy chọn của chúng là `schema`, các version đi `from` (mặc định `0`, một database mới) và `to` (mặc định: version mà package cần), và `statementBreakpoints`, tùy chọn đặt `--> statement-breakpoint` của drizzle-kit giữa các câu lệnh. Trên PostgreSQL, từ version 0, SQL bắt đầu bằng `CREATE SCHEMA IF NOT EXISTS`, câu này cần quyền CREATE trên database: hãy bỏ nó đi nếu đã có người tạo schema giúp bạn. `MySqlWebhookStore.migrationStatements()` trả về các câu lệnh của MySQL mỗi câu một chuỗi, để chạy theo thứ tự, mỗi câu một lần. `schemaVersion` là version mà package cần. Version của chính một schema là version cao nhất đã được áp dụng trong bảng `migrations` của nó.

Command line, `npx @nestjs/webhooks`, nhận `--url` (mặc định `DATABASE_URL`), với scheme quyết định store: `postgres://` hoặc `postgresql://` cho schema của `PostgresWebhookStore`, `mysql://` cho các bảng của `MySqlWebhookStore`. Nó cũng nhận `--schema` (mặc định `nest_webhooks`). `npx @nestjs/outbox` làm điều tương tự cho các store của outbox:

| Lệnh | Nó làm gì |
| --- | --- |
| `migrate` | Áp dụng các migration đang chờ, giống như `migrate: true` làm lúc khởi động. Cần cài `pg` hoặc `mysql2` |
| `status` | In ra version của schema và version mà package cần, và thoát với mã 1 khi schema còn lạc hậu |
| `sql` | In ra SQL của `migrationSql()`, từ `--from` tới `--to`, không cần database: SQL của PostgreSQL, hoặc của MySQL với `--dialect mysql`. `--statement-breakpoints` phân cách các câu lệnh cho drizzle-kit |

##### Service và decorator <a id="services-and-decorators"></a>

- `Webhooks`: `dispatch(tx, message)` nhận một message hoặc một mảng, với `type`, `data`, `tenant` và `id` tùy chọn, và throw một `TypeError` khi gặp loại không xác định, dữ liệu không serialize được thành JSON, hoặc id không hợp lệ. `notify()` chạy relay ngay lập tức.
- `WebhookEndpoints`: `create(input)`, `list(query)`, `get(id, scope)`, `update(id, changes, scope)`, `delete(id, scope)`, `getSecret(id, scope)` và `rotateSecret(id, options)`, trong đó `options` nhận `tenant`, `overlap` và `secret`. `create()` cũng nhận một `secret`, một `whsec_…` đã có được dùng thay cho secret sinh ra. Xem [Cho đối tác đăng ký](/http/webhooks#let-partners-subscribe).
- `WebhookDeliveries`: `list(query)`, `get(id, scope)`, `retry(idOrFilter, scope)`, `stats()` và `prune(olderThan)`. Xem [Retry, log gửi và gửi lại](/http/webhooks#retries-the-delivery-log-and-replay).
- `WebhookWorker`: bộ gửi, được khởi động khi ứng dụng boot trừ khi `worker.enabled` là `false`. `start()`; `stop()`, method này ngừng claim, chờ các lần thử đang dở và trả lại những lần gửi mà nó chưa bắt đầu; `running`; `notify()`, method này poll ngay thay vì chờ lượt tiếp theo; `runOnce()`, method này claim một lô rồi gửi nó, resolve ra số lần đã `claimed`, `delivered`, `retried`, `failed` và `released`, cùng số lần nó bị mất lease (`leaseLost`), và hoạt động cả khi worker đã dừng, như các bài test điều khiển nó; `stats()`, giống như `WebhookDeliveries.stats()`.
- `WEBHOOKS_OUTBOX_TOPIC`: topic outbox mà các message đã dispatch đi qua, `'nestjs.webhooks.message'`, tới handler `@OnOutboxMessage()` của package, tức bước phân phối. Một outbox có `route` chọn giữa nhiều transport sẽ gửi topic này tới `local`.
- `WebhookVerifier`: `verify(receiver, request)` kiểm tra một request không đến qua route HTTP, như một request được lưu trong queue, từ `headers` và `rawBody` của nó.
- `@VerifyWebhook(receiver)` xác minh và loại trùng, trên một method hoặc controller. `@IncomingWebhook()` inject webhook đã xác minh: `receiver`, `id`, `timestamp`, `payload`, `rawBody` và `processInTransaction()`. `@WebhookPayload()` chỉ inject payload, và nhận pipe giống như `@Body()`.

##### Transport <a id="transports"></a>

Worker gửi thông qua provider `WebhookTransport`. Transport mặc định, `HttpWebhookTransport`, được dựng từ các tùy chọn `delivery`: một `POST` cho mỗi lần thử qua `node:http` và `node:https`, host được resolve một lần và mọi địa chỉ mà nó resolve ra đều được kiểm tra, socket được cố định vào địa chỉ đã kiểm tra, redirect không bao giờ được đi theo, không dùng proxy từ biến môi trường. Constructor của nó nhận hai tùy chọn mà `delivery` không có:

- `ca`: các certificate authority cần tin cậy ngoài các CA của chính Node, cho các endpoint đứng sau một CA riêng. Chúng được thêm vào trust store của Node, nên các endpoint công khai vẫn xác minh được.
- `lookup`: resolve một host name ra mọi địa chỉ mà nó có, mỗi địa chỉ gồm `address` và `family` (4 hoặc 6), thay cho resolver của hệ thống. Mọi địa chỉ nó trả về vẫn được kiểm tra, và kết nối đi tới địa chỉ đầu tiên.

Để dùng chúng, hãy truyền một instance làm `transport`, với cùng `allowHttp`, `allowPrivateNetworks` và `allowedAddresses` như `delivery`: `delivery` vẫn quyết định những URL nào `WebhookEndpoints` chấp nhận, còn transport quyết định nó kết nối tới đâu.

```typescript
WebhooksModule.forRoot({
  delivery: { allowedAddresses: ['10.20.0.0/16'] },
  transport: new HttpWebhookTransport({
    allowedAddresses: ['10.20.0.0/16'],
    ca: readFileSync('/etc/ssl/partners-ca.pem'),
  }),
}),
```

Một transport của riêng bạn kế thừa `WebhookTransport` và implement `send(request, options)`, trong đó `options` có `signal` của lần thử và số thứ tự `attempt` của nó. Request mang `url`, các `headers` đã ký và `body`, cùng id của endpoint, lần gửi và message của nó. Hãy resolve với `statusCode`, `headers` và phần đầu `body` của response, bất kể status là gì, và chỉ throw khi không có response; hãy dừng khi `signal` bị abort, sau `delivery.timeout`. `NonRetryableWebhookError` và `WebhookDestinationBlockedError` làm lần gửi thất bại mà không retry; mọi lỗi khác đều được retry. Hãy truyền class làm `transport` ở cấp cao nhất của `forRoot()` hoặc `forRootAsync()`, nơi Nest khởi tạo nó (`imports` cho các module mà nó inject từ đó), hoặc truyền một instance. Nó thay thế cơ chế bảo vệ SSRF bằng bất cứ thứ gì nó tự làm: gửi qua một egress proxy có áp dụng cơ chế bảo vệ, như Smokescreen, là một lý do để tự viết transport; bọc `HttpWebhookTransport` thì vẫn giữ được cơ chế bảo vệ.

Cho test, `InMemoryWebhookTransport` ghi lại thay vì gửi đi, không có mạng hay kiểm tra địa chỉ (xem [Test](/http/webhooks#testing)):

- `sent`: mọi request, cũ nhất trước, dưới dạng `SentWebhook`. `clear()` làm rỗng nó.
- `respondWith(answer)`: cách endpoint trả lời từ giờ trở đi, mặc định là 200. Một status (`503`), một response (`statusCode`, `headers` như `retry-after`, `body`), hoặc một hàm nhận request và số thứ tự lần thử rồi trả về một trong hai, và throw để giả lập không có response.
- `filter(query)` và `single(query)`: các request khớp với `type`, `url` (một chuỗi hoặc `RegExp`), `endpointId` và `messageId`, hoặc một hàm nhận `SentWebhook`. `single()` throw, kèm danh sách những gì đã gửi, trừ khi có đúng một request khớp.

Một `SentWebhook` có `request`, số thứ tự `attempt` trong vòng của nó, `sentAt`, `url`, `type`, `messageId`, `endpointId`, `deliveryId`, `headers` và `body` của request, `data` (`data` của body, đã parse), và `isSignedWith(secret)`, method kiểm tra một chữ ký `v1` với secret của một endpoint.

##### Event <a id="events"></a>

`WebhooksEvents.events$` phát ra mọi event, và mỗi event cũng được công bố trên diagnostics channel `nestjs:webhooks:<type>`.

| Loại | Type của payload | Các trường ngoài `type` |
| --- | --- | --- |
| `delivered` | `WebhooksDeliveredEvent` | `delivery`, `statusCode`, `attempt`, `durationMs` |
| `retry-scheduled` | `WebhooksRetryScheduledEvent` | `delivery`, `error`, `statusCode` (`null` khi không có response), `attempt`, `delayMs` |
| `delivery-failed` | `WebhooksDeliveryFailedEvent` | `delivery`, `error`, `statusCode`, `attempt`, `reason` |
| `endpoint-disabled` | `WebhooksEndpointDisabledEvent` | `endpointId`, `tenant`, `reason` (`'failing'` hoặc `'gone'`) |
| `destination-blocked` | `WebhooksDestinationBlockedEvent` | `endpointId`, `tenant`, `reason`, `address` |
| `verification-failed` | `WebhooksVerificationFailedEvent` | `receiver`, `reason` |

`reason` của một lần gửi thất bại là `exhausted`, `rejected` (410 Gone, một đích bị chặn, `NonRetryableWebhookError` hoặc `retryIf`), `endpoint-disabled` hoặc `endpoint-deleted`. `reason` của một lần xác minh thất bại là `missing-header`, `malformed-header` (bao gồm cả webhook id dài hơn 255 ký tự), `invalid-signature`, `timestamp-out-of-tolerance` hoặc `invalid-payload`. `WebhooksEvent` là union của mọi type payload.

##### Lỗi <a id="errors"></a>

Mọi lỗi trừ `NonRetryableWebhookError` đều kế thừa `WebhooksError`. Những lỗi có `status` dành cho exception filter của API đối tác, như trong phần [Cho đối tác đăng ký](/http/webhooks#let-partners-subscribe).

| Lỗi | Status | Throw khi nào |
| --- | --- | --- |
| `InvalidWebhookEndpointError` | 400 | URL, loại event hoặc secret của một endpoint bị từ chối. `field` nêu tên cái nào. |
| `WebhookEndpointNotFoundError` | 404 | Endpoint không tồn tại, hoặc thuộc về tenant khác |
| `WebhookDeliveryNotFoundError` | 404 | Lần gửi không tồn tại, hoặc thuộc về tenant khác |
| `WebhookVerificationError` | 401, hoặc 400 với `invalid-payload` | `WebhookVerifier.verify()` từ chối một request. Nó có `receiver` và `reason`. |
| `WebhookDestinationBlockedError` | không có | URL của endpoint là, hoặc resolve ra, một địa chỉ bị chặn. Lần gửi thất bại mà không retry. |
| `WebhookResponseError` | không có | Endpoint trả lời ngoài khoảng 2xx. Nó có `statusCode`, và `retryAfterMs` từ header `Retry-After`. |
| `WebhookDeliveryTimeoutError` | không có | Không có response trong `delivery.timeout` |
| `NonRetryableWebhookError` | không có | Một transport tùy chỉnh throw nó để làm lần gửi thất bại mà không retry |
| `WebhookSchemaError` | không có | Schema của một store lạc hậu so với các migration của package khi `migrate` bị tắt, hoặc việc áp dụng chúng thất bại (`cause`): việc khởi động và mọi lời gọi đều thất bại cho đến khi được sửa. Nó có `schema`, `version` của nó và `requiredVersion`. Từ `@nestjs/webhooks/postgres` và `@nestjs/webhooks/mysql` |

`@VerifyWebhook()` trả lời một request bị từ chối bằng lỗi 401 (400 với body đã ký nhưng không phải JSON) và một message chung chung, còn lý do được đưa vào event `verification-failed`. Một request có body không được giữ dạng thô sẽ nhận lỗi 415 nếu nó không phải JSON hay form, và lỗi 500 kèm log về việc thiếu `rawBody: true` trong trường hợp còn lại.
