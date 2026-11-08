### Outbox

`@nestjs/outbox` publish event và message một cách tin cậy: mỗi cái được lưu trong cùng database transaction với dữ liệu của bạn, sau đó được relay đi kèm retry.

Khi một khách hàng đặt hàng ở cửa hàng online bán thức ăn và đồ dùng cho mèo, API đơn hàng lưu đơn hàng và thông báo nó bằng event `OrderPlaced`. Có ba thứ phản ứng với event đó: một email xác nhận được gửi đi, hàng trong kho được giữ chỗ, và một service analytics riêng ghi nhận doanh số.

Lưu đơn hàng và publish event là hai thao tác ghi vào hai hệ thống khác nhau, và không có transaction nào bao trùm cả hai:

- **Lưu rồi publish.** Nếu process crash hoặc broker bị down ở giữa hai bước, đơn hàng tồn tại nhưng `OrderPlaced` bị mất. Khách hàng không nhận email, hàng không được giữ chỗ, và analytics đếm thiếu.
- **Publish rồi lưu.** Nếu câu insert thất bại, khách hàng được cảm ơn cho một đơn hàng không tồn tại.
- **Retry việc publish khi lỗi.** Một timeout sau khi đã gửi thành công trông giống một lần thất bại, nên lần retry gửi lại nó và khách hàng nhận hai email.

Đây là vấn đề dual-write. `ClientProxy.emit()`, `EventEmitter2` và `EventBus` của CQRS đều publish từ bộ nhớ, nên tất cả đều gặp vấn đề này.

Một transactional outbox loại bỏ nó bằng cách biến event thành một dòng dữ liệu. `Outbox.add()` insert message vào một bảng outbox trong **cùng database transaction với đơn hàng**, nên cả hai cùng commit hoặc cùng không. Sau đó một relay sẽ publish các message đã commit. Nó retry các lần thất bại kèm backoff và chuyển những message không bao giờ thành công sang một bảng dead-letter. Có retry nghĩa là một consumer có thể thấy một message hai lần, nên mỗi consumer giữ một **inbox** chứa id các message nó đã xử lý và bỏ qua các bản lặp lại.

Trong bài hướng dẫn này, bạn sẽ thêm outbox vào API đơn hàng của cửa hàng, trên PostgreSQL với Drizzle:

- `POST /orders` lưu đơn hàng và các message của nó trong một transaction.
- Hai handler in-process gửi email xác nhận và giữ chỗ hàng trong kho.
- Một microservice analytics riêng, có database riêng, nhận event đơn hàng qua TCP, theo đúng thứ tự cho mỗi đơn hàng.
- Các lần thất bại được retry, và một admin API nhỏ liệt kê, đưa lại vào hàng đợi và xóa các dead letter.
- Nhiều instance của API chia sẻ công việc một cách an toàn.

#### Yêu cầu trước <a id="prerequisites"></a>

- PostgreSQL, với [Drizzle ORM](https://orm.drizzle.team) trên driver `pg`, được đăng ký qua [`@nestjs/drizzle`](/data/drizzle). Các message của outbox được commit cùng các dòng dữ liệu của bạn, nên chúng nằm trong database chứa đơn hàng của bạn, trên một database server tồn tại lâu hơn mọi instance của ứng dụng. Dùng TypeORM, Prisma hoặc MySQL? Hãy theo bài hướng dẫn để biết ứng dụng làm gì: [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database) trình bày store với từng loại.
- `@nestjs/microservices`, cho kết nối TCP tới service analytics trong [Publish tới microservice analytics](/reliability/outbox#publish-to-the-analytics-microservice).

Cài đặt package:

```bash
$ npm i --save @nestjs/outbox
```

Ứng dụng ví dụ, API đơn hàng của cửa hàng online, giữ sản phẩm và đơn hàng trong hai bảng riêng, được các phần sau đọc và ghi. Chúng là dữ liệu của ví dụ, không phải thứ outbox cần: các bảng của outbox thuộc về store của nó, store tự tạo ra chúng, như [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database) trình bày.

`products` là danh mục sản phẩm, và việc giữ chỗ hàng cho một đơn hàng sẽ chuyển số lượng từ `in_stock` sang `reserved`:

| Cột | Type | Ghi chú |
| --- | --- | --- |
| `id` | `text` | Primary key, chẳng hạn `salmon-kibble-2kg` |
| `name` | `text` | Tên hiển thị, chẳng hạn `Salmon kibble, 2 kg` |
| `price` | `integer` | Tính bằng cent |
| `in_stock` | `integer` | Số lượng còn có thể đặt |
| `reserved` | `integer` | Số lượng đang được giữ cho các đơn đã đặt. Mặc định là `0` |

`orders` chứa các đơn hàng mà `POST /orders` lưu:

| Cột | Type | Ghi chú |
| --- | --- | --- |
| `id` | `text` | Primary key |
| `user_id` | `text` | Khách hàng đã đặt đơn |
| `items` | `jsonb` | Các dòng của đơn hàng, dưới dạng mảng JSON: `productId`, `quantity` và đơn giá `price` (tính bằng cent) của mỗi dòng |
| `total` | `integer` | Tính bằng cent |
| `status` | `text` | `placed` hoặc `cancelled` |

Không cột nào trong hai bảng được phép null.

Danh mục có hai sản phẩm: `salmon-kibble-2kg`, giá 2499 cent với 10 sản phẩm trong kho, và `clumping-litter-10l`, giá 1599 cent với một sản phẩm trong kho.

#### Giữ message trong database của bạn <a id="keep-messages-in-your-database"></a>

Không cần tạo gì cho outbox: không bảng, entity hay Prisma model nào. Hãy đăng ký store của nó, và store sẽ tạo schema riêng, `nest_outbox`, và migrate nó: lúc khởi động trong môi trường development và test, còn trong production thì bằng `npx @nestjs/outbox migrate`, hoặc bằng `migrationSql()` trong các migration của bạn.

Outbox giữ message, dead letter và inbox của các consumer trong cùng database với các bảng của bạn, vì chúng phải commit cùng các dòng dữ liệu của bạn. Cho tới khi bạn đăng ký một store cho chúng, outbox giữ chúng trong bộ nhớ: ổn cho lần chạy đầu tiên, nhưng một lần restart sẽ mất mọi message chưa được publish, hai instance không dùng chung chúng, và không có gì tham gia vào transaction của bạn.

> warning **Cảnh báo** Với `NODE_ENV=production` và không có store nào được đăng ký, việc khởi động sẽ thất bại, trừ khi bạn đặt `allowInMemoryStorage: true`.

Trên PostgreSQL, hãy đăng ký store của package, `PostgresOutboxStore` từ `@nestjs/outbox/postgres`. Nó chạy SQL qua database client mà ứng dụng của bạn đã có, nên có thể tham gia vào transaction của bạn, và nó giữ các bảng của mình trong một schema riêng. Nó là một provider bình thường, đăng ký một lần, trong root module, cạnh `OutboxModule`: cả hai đều có phạm vi toàn ứng dụng, và mọi `outbox.add()` ở bất kỳ module nào đều đi qua nó. Root module tạo nó bằng một factory inject Drizzle database và registry `OutboxStorage`, nơi store tự đăng ký:

```typescript
@@filename(app.module)
{
  // Messages and inbox records in your database, in a schema of their own (nest_outbox)
  provide: PostgresOutboxStore,
  inject: [getDrizzleToken(), OutboxStorage],
  useFactory: (db: Database, outboxStorage: OutboxStorage) =>
    new PostgresOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
},
```

`fromDrizzle(db)` là **executor** của store: nó chạy các câu lệnh của store qua Drizzle database của bạn, dù dùng driver nào, như `pg` hay PGlite. `fromPg(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` và `fromKysely(db)` làm điều tương tự cho một pool node-postgres, TypeORM, Prisma và Kysely. Lúc khởi động, module log ra `OutboxStorage: PostgresOutboxStore`.

**Schema.** Store giữ các bảng của nó trong một schema riêng, `nest_outbox` (tùy chọn `schema` cho phép đặt tên khác). Trên MySQL, vốn không có schema, chúng là các bảng trong database của kết nối, với tên schema làm tiền tố: `nest_outbox_messages` và các bảng tương tự.

| Bảng | Chứa gì |
| --- | --- |
| `nest_outbox.messages` | Mỗi message từ lúc `add()` cho tới khi nó được publish hoặc chuyển sang dead-letter, kèm số lần thử và lease của nó |
| `nest_outbox.dead_letters` | Các message đã thất bại, kèm lý do và lỗi của mọi lần thử |
| `nest_outbox.inbox` | Id các message mà mỗi consumer đã xử lý |
| `nest_outbox.migrations` | Các phiên bản schema của store đã được áp dụng |

Chúng thuộc về store: migration của bạn không tạo chúng, schema của ORM không khai báo chúng, và các bảng của bạn không thể trùng tên với chúng. drizzle-kit và Prisma Migrate làm việc trên schema `public` trừ khi được chỉ định khác, còn TypeORM làm việc trên các bảng của entity, nên công cụ của chúng không động tới `nest_outbox`.

**Migration.** Package đi kèm schema dưới dạng các migration có phiên bản, và store tự áp dụng chúng. Với tùy chọn `migrate`, nó áp dụng những migration mà schema chưa có khi ứng dụng khởi động, trước khi relay chạy, trong một transaction giữ một advisory lock: trong nhiều instance khởi động cùng lúc, một instance migrate, và các instance khác thấy không còn gì để làm. `migrate` mặc định là `true`, trừ khi `NODE_ENV=production`. Vì vậy trong development và test, store tạo schema ở lần khởi động đầu tiên, và migration của bạn chỉ tạo các bảng của riêng bạn, ở đây là `products` và `orders`.

Trong production, hãy áp dụng migration trước khi phiên bản mới của ứng dụng khởi động, giống như cách bạn áp dụng migration của mình, để không instance nào thay đổi schema trong lúc boot: giữa một lần rolling deploy, việc đó sẽ khóa các bảng đang bận, và một database user có quyền tối thiểu cũng không thể làm điều đó. Command line của package làm việc này từ bước deploy của bạn, cạnh `npx drizzle-kit migrate`. Nó đọc database từ `DATABASE_URL`, hoặc từ `--url`, và cần cài `pg`:

```bash
$ npx @nestjs/outbox status
Schema "nest_outbox" is at version 0; this version of @nestjs/outbox needs version 1.
$ npx @nestjs/outbox migrate
Migrated schema "nest_outbox" to version 1 (applied 1).
```

`status` thoát với mã 1 khi schema còn chậm phiên bản, nên nó có thể dùng làm bước kiểm tra trong CI. Để áp dụng migration bằng công cụ migration của riêng bạn, hãy lấy SQL của chúng từ `npx @nestjs/outbox sql`, hoặc từ `PostgresOutboxStore.migrationSql()` trong code: các câu lệnh của mọi migration, mỗi đoạn một câu, kèm phần ghi chép phiên bản. Chạy chúng trong một transaction, như migrator của TypeORM và Drizzle làm. Với TypeORM, đó là một migration của riêng bạn, cạnh các migration mà nó sinh ra cho entity của bạn:

```typescript
@@filename(typeorm/migrations/1790801276314-OutboxStore)
import { PostgresOutboxStore } from '@nestjs/outbox/postgres';
import type { MigrationInterface, QueryRunner } from 'typeorm';

export class OutboxStore1790801276314 implements MigrationInterface {
  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(PostgresOutboxStore.migrationSql());
  }

  // The store's migrations only ever add tables, columns and indexes: it has no down migrations.
  async down(): Promise<void> {}
}
```

Với drizzle-kit, hãy tạo một custom migration, và điền SQL vào file nó tạo ra, với một dòng `--> statement-breakpoint` giữa các câu lệnh: khi đó migrator của Drizzle sẽ chạy từng câu một, điều mà PGlite yêu cầu. Trong code, `migrationSql()` với `statementBreakpoints: true` trả về kết quả tương tự.

```bash
$ npx drizzle-kit generate --custom --name=outbox
$ npx @nestjs/outbox sql --statement-breakpoints > drizzle/20261103120000_outbox/migration.sql
```

Trên MySQL, `MySqlOutboxStore.migrationStatements()` trả về các câu lệnh, mỗi chuỗi một câu, và một migration TypeORM chạy chúng mỗi lời gọi một câu:

```typescript
@@filename(typeorm/mysql-migrations/1790801276314-OutboxStore)
for (const statement of MySqlOutboxStore.migrationStatements()) {
  await queryRunner.query(statement);
}
```

Khi tắt `migrate`, một store có schema chậm phiên bản sẽ làm việc khởi động thất bại với một `OutboxSchemaError` nêu ra ba cách này, và làm mọi lời gọi thất bại theo cùng cách cho tới khi schema được cập nhật, điều mà nó tự nhận ra mà không cần restart. Migration chỉ thêm bảng, cột và index, nên trong một lần rolling deploy, phiên bản trước của ứng dụng vẫn tiếp tục chạy trên schema đã migrate. Không có down migration.

**Transaction.** `outbox.add()` nhận transaction của bạn, như [Lưu đơn hàng và message của nó trong một transaction](/reliability/outbox#save-the-order-and-its-messages-in-one-transaction) trình bày, và `processInTransaction()` của handler cũng vậy: với Drizzle, đó là `tx` mà `db.transaction()` truyền cho callback của nó. Store chạy các câu lệnh của nó trên transaction đó, nên chúng commit hoặc rollback cùng các thao tác ghi của bạn. Nó từ chối chính database, vì các câu lệnh trên đó sẽ tự commit riêng, bằng một `OutboxTransactionRequiredError` cho biết cần truyền gì. Với các executor khác, hãy truyền một client node-postgres sau `BEGIN` (không phải pool), `EntityManager` của TypeORM từ `dataSource.transaction()`, interactive transaction client của Prisma, hoặc một Kysely transaction.

**Isolation.** Các transaction riêng của store (claim, chuyển sang dead-letter, đưa lại vào hàng đợi) dựa vào READ COMMITTED, isolation level mặc định của PostgreSQL: lúc khởi động, store kiểm tra `default_transaction_isolation` của database, và thất bại nếu nó chặt hơn. Transaction của bạn có thể chạy ở bất kỳ level nào. `add()` trước tiên lấy một lock theo từng key trên transaction của bạn, nên các transaction thêm message có cùng key sẽ lần lượt chờ nhau, và các message của một key được đánh số theo thứ tự transaction của chúng commit. Dưới REPEATABLE READ hoặc SERIALIZABLE, hai lần gửi của cùng một message chạy đua tới `processInTransaction()` có thể làm lần thứ hai thất bại với lỗi serialization thay vì bỏ qua nó như một bản trùng lặp: handler của nó thất bại, và lần retry của relay sẽ tìm thấy record.

**Với TypeORM.** `TypeOrmModule` thay thế `DrizzleModule` trong root module, và store chạy trên `DataSource` mà nó cung cấp, qua `fromTypeOrm()`:

```typescript
@@filename(typeorm/app.module)
{
  // Messages and inbox records in your database, in a schema of their own (nest_outbox)
  provide: PostgresOutboxStore,
  inject: [DataSource, OutboxStorage],
  useFactory: (dataSource: DataSource, outboxStorage: OutboxStorage) =>
    new PostgresOutboxStore({ executor: fromTypeOrm(dataSource) }, outboxStorage),
},
```

Ở chỗ bài hướng dẫn truyền `tx` của Drizzle cho `outbox.add()`, hãy truyền `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó, và gán type cho outbox theo nó. Store từ chối `dataSource.manager`, vì các thao tác ghi trên đó sẽ tự commit riêng. Đây là order service với TypeORM:

```typescript
@@filename(typeorm/orders.service)
@Injectable()
export class OrdersService {
  constructor(
    private readonly dataSource: DataSource,
    private readonly outbox: Outbox<EntityManager>,
  ) {}

  async placeOrder({ userId, items }: PlaceOrderDto): Promise<Order> {
    if (!items?.length) {
      throw new BadRequestException('An order needs at least one item');
    }

    const order = await this.dataSource.transaction(async (manager) => {
      // ... price the items through manager (an unknown product throws) and build the order
      await manager.insert(OrderEntity, order);

      // The transaction's EntityManager: the message commits or rolls back with the order.
      await this.outbox.add(manager, { topic: 'order.placed', payload: order });
      return order;
    });

    this.outbox.notify(); // publish now instead of at the next poll
    return order;
  }
}
```

**Với Prisma.** Truyền `PrismaService` của bạn cho `fromPrisma()` trong factory, và truyền cho `outbox.add()` transaction client mà `prisma.$transaction()` đưa cho callback của nó. Chỉ dạng interactive đó mới có client để truyền: dạng mảng, `prisma.$transaction([query1, query2])`, không thể chứa một `outbox.add()`. Store từ chối chính client, vì các câu lệnh trên đó sẽ tự commit riêng. Các transaction riêng của store chờ kết nối tối đa 10 giây và chạy tối đa một phút, lâu hơn mặc định của Prisma: tham số thứ hai của `fromPrisma()` thay đổi điều đó, với `maxWait` và `timeout`.

**Với MySQL.** Cho MySQL 8.4 LTS và 9.x, `@nestjs/outbox/mysql` có `MySqlOutboxStore`. Import store và executor của nó từ đó: provider giống nhau, các tùy chọn và tên executor cũng vậy. Đây là API đơn hàng trên MySQL, với Drizzle trên driver `mysql2`:

```typescript
@@filename(mysql/app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule, getDrizzleToken } from '@nestjs/drizzle';
import { OutboxModule, OutboxStorage } from '@nestjs/outbox';
import { fromDrizzle, MySqlOutboxStore } from '@nestjs/outbox/mysql';
import { drizzle } from 'drizzle-orm/mysql2';
import { NotificationsModule } from '../notifications/notifications.module.js';
import type { Database } from './drizzle.js';
import { OrdersService } from './orders.service.js';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      // A mysql2 pool on DATABASE_URL (mysql://...), whose path names the database
      useFactory: () => ({ drizzle, connection: { uri: process.env.DATABASE_URL! } }),
    }),
    OutboxModule.forRoot({ relay: { pollInterval: '1s' } }),
    NotificationsModule,
  ],
  providers: [
    {
      // Messages and inbox records in your database, in tables of their own (nest_outbox_*)
      provide: MySqlOutboxStore,
      inject: [getDrizzleToken(), OutboxStorage],
      useFactory: (db: Database, outboxStorage: OutboxStorage) =>
        new MySqlOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
    },
    OrdersService,
  ],
})
export class AppModule {}
```

`fromMysql2(pool)`, `fromTypeOrm(dataSource)` cho một data source có type `mysql`, `fromPrisma(prisma)` với driver adapter `@prisma/adapter-mariadb` (adapter phục vụ MySQL), và `fromKysely(db)` phục vụ các client khác. Những điểm khác so với PostgreSQL:

- **Bảng, không phải schema.** Một database MySQL không có schema, nên store giữ các bảng của nó trong database của kết nối, database mà phần path của URL chỉ định, và tùy chọn `schema` là tiền tố của chúng: `nest_outbox_messages`, `nest_outbox_dead_letters` và `nest_outbox_inbox`, cạnh `nest_outbox_migrations` và `nest_outbox_locks`. Nó nhận chữ thường, chữ số và dấu gạch dưới, tối đa 40 ký tự. Một kết nối không có database sẽ làm việc khởi động thất bại.
- **Key có giới hạn.** Id, topic, key và tên consumer là các cột có index tối đa 255 ký tự, được so sánh theo từng byte: `order-1` và `Order-1` là hai key khác nhau. Một giá trị dài hơn bị từ chối bằng `RangeError`, trước mọi câu lệnh: bởi `add()`, và bởi inbox trước khi nó chạy một handler.
- **Isolation level của bạn.** Transaction của bạn có thể chạy ở REPEATABLE READ, mặc định của MySQL, hoặc ở READ COMMITTED. Một lần gửi chạy đua với lần khác tới `processInTransaction()` sẽ chờ lần kia, rồi bỏ qua handler như một bản trùng lặp, ở cả hai level.
- **Deadlock tới được transaction của bạn.** `add()` lock một dòng theo từng key trong transaction của bạn, một trong 16.384 dòng mà các key dùng chung, được store tạo ra khi nó khởi động: các producer của hai key dùng chung một dòng sẽ lần lượt chờ nhau, như các producer của cùng một key, điều này hiếm khi làm chậm một producer không liên quan. Khi MySQL phá một deadlock trong transaction của bạn (lỗi 1213), nó rollback toàn bộ transaction, và store không thể chạy lại công việc của bạn: lỗi tới code của bạn dưới dạng lỗi của client, nên hãy chạy lại transaction. Với các dòng đó, vẫn còn hai thứ có thể gây ra deadlock: ba lần gửi của cùng một message chạy đua tới `processInTransaction()` trong khi lần đầu tiên rollback, và các transaction của bạn lấy cùng các lock theo thứ tự khác nhau. Các transaction riêng của store tự retry khi gặp deadlock.
- **Migration không mang tính transaction.** MySQL tự commit từng câu lệnh DDL, nên `migrate` và `npx @nestjs/outbox migrate --url mysql://...` áp dụng từng câu lệnh một dưới một lock, và một lần chạy bị dừng giữa chừng sẽ tiếp tục từ chỗ nó đã dừng. Công cụ của riêng bạn cũng phải gửi mỗi lời gọi một câu lệnh, như migration TypeORM trong phần **Migration** ở trên, và một custom migration của drizzle-kit cần `npx @nestjs/outbox sql --dialect mysql --statement-breakpoints`, vì migrator MySQL của nó gửi mỗi breakpoint một câu lệnh.

#### Đăng ký outbox <a id="register-the-outbox"></a>

Đăng ký `OutboxModule` trong root module, cạnh `DrizzleModule`, module đăng ký Drizzle database, và với store từ [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database). Các feature module mà nó import được xây dựng ở các bước tiếp theo:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule, getDrizzleToken } from '@nestjs/drizzle';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { ClientProxyTransport, OutboxModule, OutboxStorage } from '@nestjs/outbox';
import { fromDrizzle, PostgresOutboxStore } from '@nestjs/outbox/postgres';
import { drizzle } from 'drizzle-orm/node-postgres';
import type { Database } from './database/drizzle.js';
import * as schema from './database/schema.js';
import { InventoryModule } from './inventory/inventory.module.js';
import { NotificationsModule } from './notifications/notifications.module.js';
import { OrdersModule } from './orders/orders.module.js';
import { OutboxAdminModule } from './outbox-admin/outbox-admin.module.js';

export const ANALYTICS_SERVICE = 'ANALYTICS_SERVICE';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      // A pg pool on DATABASE_URL, closed in onApplicationShutdown(), after the relay drained.
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema }),
    }),
    OutboxModule.forRootAsync({
      imports: [
        ClientsModule.registerAsync([
          {
            name: ANALYTICS_SERVICE,
            useFactory: () => ({
              transport: Transport.TCP,
              options: {
                host: process.env.ANALYTICS_HOST ?? '127.0.0.1',
                port: Number(process.env.ANALYTICS_PORT ?? 4001),
              },
            }),
          },
        ]),
      ],
      transports: { analytics: ClientProxyTransport(ANALYTICS_SERVICE) },
      useFactory: () => ({
        // Each message goes to exactly one transport; `local` runs @OnOutboxMessage() handlers.
        route: (message) => (message.topic.startsWith('analytics.') ? 'analytics' : 'local'),
        relay: {
          enabled: process.env.OUTBOX_RELAY !== 'off',
          pollInterval: '1s',
          lease: '30s',
          publishTimeout: '10s',
        },
        retry: {
          attempts: 10,
          backoff: { delay: '1s', maxDelay: '1m' },
        },
      }),
    }),
    OrdersModule,
    NotificationsModule,
    InventoryModule,
    OutboxAdminModule,
  ],
  providers: [
    {
      // Messages and inbox records in your database, in a schema of their own (nest_outbox)
      provide: PostgresOutboxStore,
      inject: [getDrizzleToken(), OutboxStorage],
      useFactory: (db: Database, outboxStorage: OutboxStorage) =>
        new PostgresOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
    },
  ],
})
export class AppModule {}
```

`ClientProxyTransport(ANALYTICS_SERVICE)` là một class mà Nest khởi tạo bên trong `OutboxModule`, nên `transports` nằm cạnh `useFactory`, nơi đặt các class. Factory chạy khi ứng dụng khởi động và trả về phần còn lại của các tùy chọn:

- `transports` và `route`: nơi mỗi message được publish. Transport `local` có sẵn và chạy các handler `@OnOutboxMessage()` trong process này ([Xử lý order.placed in-process](/reliability/outbox#handle-orderplaced-in-process)). `ClientProxyTransport(ANALYTICS_SERVICE)` publish qua TCP client mà `ClientsModule` đăng ký dưới tên đó, đó là lý do module đó nằm trong `imports` ([Publish tới microservice analytics](/reliability/outbox#publish-to-the-analytics-microservice)). `route` chọn đúng một transport cho mỗi message.
- `relay`: bộ publish chạy nền. Nó poll mỗi `pollInterval`, giữ lease những gì nó claim trong `lease`, và bỏ cuộc với một lần publish đơn lẻ sau `publishTimeout`. Đặt `OUTBOX_RELAY=off` sẽ tắt nó trong các instance chỉ phục vụ API ([Chạy nhiều instance](/reliability/outbox#run-several-instances)).
- `retry`: 10 lần thử, với exponential backoff bắt đầu từ 1 giây và giới hạn tối đa 1 phút ([Retry và dead-letter queue](/reliability/outbox#retries-and-the-dead-letter-queue)).

> info **Gợi ý** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để thiếu `DATABASE_URL` sẽ dừng ứng dụng ngay lúc khởi động, và đọc các giá trị từ `ConfigService` trong các factory.

Khoảng thời gian là số mili giây hoặc chuỗi như `'30s'` và `'1m'`. `OutboxModule` là global: `Outbox`, `OutboxStorage`, `OutboxRelay`, `OutboxEvents`, `OutboxDeadLetters` và `OutboxInbox` có thể được inject ở bất cứ đâu trong ứng dụng.

#### Lưu đơn hàng và message của nó trong một transaction <a id="save-the-order-and-its-messages-in-one-transaction"></a>

Đây là model đơn hàng:

```typescript
@@filename(orders/order)
export interface OrderItem {
  productId: string;
  quantity: number;
  /** Unit price in cents, copied from the catalog when the order is placed. */
  price: number;
}

export interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  /** In cents. */
  total: number;
  status: 'placed' | 'cancelled';
}

export class PlaceOrderDto {
  userId: string;
  items: { productId: string; quantity: number }[];
}
```

`OrdersService.placeOrder()` mở một Drizzle transaction, tính giá các sản phẩm, insert đơn hàng và thêm các message, tất cả qua cùng một `tx`:

```typescript
@@filename(orders/orders.service)
import { BadRequestException, Injectable } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { Outbox } from '@nestjs/outbox';
import type { Database, Transaction } from '../database/drizzle.js';
import { orders, products } from '../database/schema.js';
import type { Order, PlaceOrderDto } from './order.js';

@Injectable()
export class OrdersService {
  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly outbox: Outbox<Transaction>,
  ) {}

  async placeOrder({ userId, items }: PlaceOrderDto): Promise<Order> {
    if (!items?.length) {
      throw new BadRequestException('An order needs at least one item');
    }

    const order = await this.db.transaction(async (tx) => {
      // ... price the items through tx (an unknown product throws) and build the order
      await tx.insert(orders).values(order);

      // Drizzle's tx: the messages commit or roll back with the order.
      await this.outbox.add(tx, [
        { topic: 'order.placed', payload: order },
        { topic: 'analytics.order.placed', key: order.id, payload: order },
      ]);
      return order;
    });

    this.outbox.notify(); // publish now instead of at the next poll
    return order;
  }
}
```

`outbox.add()` nhận transaction handle trước tiên, sau đó là message hoặc một mảng message. Với Drizzle, handle là `tx` mà `db.transaction()` truyền cho callback của nó, type của nó được service truyền cho outbox: `Outbox<Transaction>`. Store insert chúng qua `tx` đó, nên các message commit cùng đơn hàng, hoặc rollback cùng nó. Store là bất đồng bộ, nên hãy await `add()` như mọi query khác. Mọi API trong package có tham gia vào transaction của bạn đều nhận handle làm tham số đầu tiên.

Một vài chi tiết:

- **Mỗi đích một message.** Mỗi message đi tới đúng một transport. Cùng một event đi tới các handler in-process và tới service analytics, nên service thêm hai message, `order.placed` và `analytics.order.placed`, trong cùng một transaction.
- **Payload là bản chụp.** `add()` serialize payload ngay lập tức, nên các thay đổi sau đó trên object `order` sẽ không được publish.
- **Id.** Mỗi message có một `id` UUIDv7 có thứ tự theo thời gian. Consumer khử trùng lặp dựa trên nó.
- **`notify()`.** Không có gì được publish bên trong transaction. Sau khi commit, `notify()` đánh thức relay. Không có nó, message sẽ được gửi đi ở lần poll tiếp theo, chậm tối đa `pollInterval`.

Nếu có gì đó throw bên trong transaction, đơn hàng và các message của nó cùng rollback, và relay không bao giờ thấy chúng. Điều đó bao gồm một sản phẩm không tồn tại, một câu insert thất bại, và bất cứ thứ gì thất bại sau `add()`. Phần [Testing](/reliability/outbox#testing) chứng minh điều này bằng cách làm transaction thất bại sau khi các message đã được ghi.

Hãy truyền transaction, không bao giờ truyền database: `outbox.add(this.db, message)` sẽ ghi message một cách độc lập, ở chế độ autocommit, chính xác là việc dual write mà bạn đang loại bỏ. Store từ chối nó bằng `OutboxTransactionRequiredError`, và chính `add()` cũng vậy khi nó không nhận được handle nào.

Đưa service ra qua HTTP:

```typescript
@@filename(orders/orders.controller)
import { Body, Controller, HttpCode, HttpStatus, Param, Post } from '@nestjs/common';
import { PlaceOrderDto } from './order.js';
import { OrdersService } from './orders.service.js';

@Controller('orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Post()
  place(@Body() dto: PlaceOrderDto) {
    return this.ordersService.placeOrder(dto);
  }

  @Post(':id/cancel')
  @HttpCode(HttpStatus.OK)
  cancel(@Param('id') id: string) {
    return this.ordersService.cancelOrder(id);
  }
}
```
#### Xử lý order.placed in-process <a id="handle-orderplaced-in-process"></a>

Email xác nhận là một handler cho `order.placed`. Mailer là bản thay thế cho SDK của nhà cung cấp email của bạn:

```typescript
@@filename(notifications/mailer.service)
import { Injectable, Logger } from '@nestjs/common';
import type { Order } from '../orders/order.js';

/** Stand-in for your email provider's SDK. */
@Injectable()
export class MailerService {
  private readonly logger = new Logger(MailerService.name);

  async sendOrderConfirmation(order: Order): Promise<void> {
    this.logger.log(`Order confirmation for ${order.id} sent to ${order.userId}`);
  }
}
```

```typescript
@@filename(notifications/order-emails.handler)
import { Injectable } from '@nestjs/common';
import { OnOutboxMessage } from '@nestjs/outbox';
import type { Order } from '../orders/order.js';
import { MailerService } from './mailer.service.js';

@Injectable()
export class OrderEmailsHandler {
  constructor(private readonly mailerService: MailerService) {}

  // The consumer's inbox skips messages it has already handled.
  @OnOutboxMessage('order.placed', { consumer: 'order-confirmation-email' })
  async sendConfirmation(order: Order) {
    await this.mailerService.sendOrderConfirmation(order);
  }
}
```

Các handler `@OnOutboxMessage()` được tìm thấy trên các provider, nên hãy đăng ký `MailerService` và `OrderEmailsHandler` làm provider của một `NotificationsModule`. Chúng phải là singleton: một handler trên provider request-scoped sẽ thất bại lúc khởi động. Handler nhận payload, ở đây là đơn hàng, và một context làm tham số thứ hai. `message` của context chứa `id`, `topic`, `key` và `headers` của message.

Mỗi handler có một inbox, được đặt tên bởi `consumer`. Trước khi gọi handler, local transport kiểm tra xem consumer `order-confirmation-email` đã xử lý message id này chưa. Sau khi handler thành công, nó ghi lại id. `consumer` là bắt buộc, và phải giữ ổn định: một tên mới sẽ khiến mọi message cũ trông như mới.

Inbox có một lỗ hổng: nếu process chết sau khi email đã được gửi nhưng trước khi id được ghi lại, email sẽ được gửi lại khi message được gửi lại. Điều đó chấp nhận được với một email. Nhưng không chấp nhận được với việc giữ chỗ hàng, vốn nằm trong cùng database với inbox. Handler giữ chỗ hàng bịt lỗ hổng này bằng cách ghi lại id bên trong transaction của chính nó:

```typescript
@@filename(inventory/stock-reservation.handler)
import { Injectable, Logger } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { NonRetryableMessageError, OnOutboxMessage, type OutboxHandlerContext } from '@nestjs/outbox';
import { and, eq, gte, sql } from 'drizzle-orm';
import type { Database, Transaction } from '../database/drizzle.js';
import { products } from '../database/schema.js';
import type { Order } from '../orders/order.js';

@Injectable()
export class StockReservationHandler {
  private readonly logger = new Logger(StockReservationHandler.name);

  constructor(@InjectDrizzle() private readonly db: Database) {}

  @OnOutboxMessage('order.placed', { consumer: 'stock-reservation' })
  async reserve(order: Order, ctx: OutboxHandlerContext<Transaction>) {
    await this.db.transaction(async (tx) => {
      // Records the message id through tx, then runs the callback only if this consumer
      // hasn't processed it yet. Await it: the record commits with the reservation.
      await ctx.processInTransaction(tx, async () => {
        for (const { productId, quantity } of order.items) {
          const reserved = await tx
            .update(products)
            .set({ inStock: sql`${products.inStock} - ${quantity}`, reserved: sql`${products.reserved} + ${quantity}` })
            .where(and(eq(products.id, productId), gte(products.inStock, quantity)))
            .returning({ id: products.id });
          if (reserved.length === 0) {
            // Retrying won't create stock: dead-letter it now and let a human decide.
            throw new NonRetryableMessageError(`Not enough stock for "${productId}" (order ${order.id})`);
          }
        }
        this.logger.log(`Reserved stock for order ${order.id}`);
      });
    });
  }
}
```

`ctx.processInTransaction(tx, work)` insert inbox record qua transaction của handler, sau đó chỉ gọi `work` nếu consumer này chưa xử lý message. Nếu đã xử lý rồi, nó bỏ qua `work` và trả về một kết quả có cờ `duplicate` là `true`. Record và việc cập nhật kho cùng commit, nên việc giữ chỗ chỉ xảy ra đúng một lần: một lần gửi lại sẽ tìm thấy record và bỏ qua handler, còn nếu `work` throw, cả hai cùng rollback và lần retry bắt đầu lại từ đầu. Hãy await nó bên trong callback của transaction, để record được ghi trước `COMMIT`; việc kiểm tra trùng lặp xảy ra bên trong lời gọi, nên thiếu `await` cũng không làm nó bị bỏ qua. Đăng ký handler trong một `InventoryModule`.

| Handler | Hành vi | Đảm bảo |
| --- | --- | --- |
| Mặc định | Bỏ qua handler nếu inbox của nó đã có id, ghi lại id sau khi handler thành công | Một lần, trừ khi process chết giữa lúc handler xong và lúc ghi record, hoặc một instance khác gửi cùng message vào cùng lúc |
| Gọi `ctx.processInTransaction(tx, work)` | Ghi lại id trong transaction riêng của handler, cùng các thao tác ghi của nó | Đúng một lần với các thao tác ghi vào cùng database |
| `inbox: false` | Mọi lần gửi đều chạy handler | Ít nhất một lần |

Cả hai handler chạy đồng thời cho mỗi message `order.placed`. Nếu một trong hai thất bại, lần publish thất bại và toàn bộ message được retry. Ở lần retry, mỗi handler đã thành công sẽ được inbox của nó bỏ qua.

Relay cho các handler `publishTimeout` (ở đây là 10 giây). Nếu chúng mất lâu hơn, lần thử được tính là thất bại và `signal` của context bị abort: hãy truyền `ctx.signal` cho các lời gọi mà handler thực hiện, chẳng hạn tùy chọn `signal` của `fetch()`, để chúng cũng dừng lại. Một handler bỏ qua nó sẽ tiếp tục chạy, và nếu lần retry tới cùng process trong lúc đó, inbox sẽ chờ nó thay vì chạy handler lần thứ hai.

#### Publish tới microservice analytics <a id="publish-to-the-analytics-microservice"></a>

Phía API đã được nối sẵn. Trong `AppModule`, `ClientProxyTransport(ANALYTICS_SERVICE)` publish qua `ClientProxy` mà `ClientsModule` đã đăng ký dưới tên đó, và `route` gửi mọi topic `analytics.*` tới nó. Transport gọi `client.emit(topic, envelope)`, đúng lời gọi bạn sẽ dùng nếu không có outbox. Envelope có `id`, `topic`, `key`, `headers`, `createdAt` và `payload` của message.

Hủy một đơn hàng tạo ra event analytics thứ hai cho cùng đơn hàng đó. Thêm method `cancelOrder()` vào `OrdersService`, và import `NotFoundException` cùng `ConflictException` từ `@nestjs/common`:

```typescript
@@filename(orders/orders.service)
async cancelOrder(id: string): Promise<Order> {
  const order = await this.db.transaction(async (tx) => {
    const [row] = await tx.select().from(orders).where(eq(orders.id, id)).for('update');
    if (!row) {
      throw new NotFoundException(`Order ${id} not found`);
    }
    if (row.status !== 'placed') {
      throw new ConflictException(`Order ${id} is ${row.status}`);
    }

    await tx.update(orders).set({ status: 'cancelled' }).where(eq(orders.id, id));
    const order: Order = { ...row, status: 'cancelled' };
    await this.outbox.add(tx, { topic: 'analytics.order.cancelled', key: order.id, payload: order });
    return order;
  });

  this.outbox.notify();
  return order;
}
```

Orders controller đã route `POST /orders/:id/cancel` tới nó. Câu `SELECT ... FOR UPDATE` lock dòng của đơn hàng, nên hai lần hủy cùng một đơn hàng sẽ lần lượt chờ nhau, và lần thứ hai thấy `cancelled` và trả lời `409`. Cả hai message analytics đều dùng id đơn hàng làm `key`. Các message có chung key được publish lần lượt từng cái, theo thứ tự transaction của chúng commit. Trong khi `analytics.order.placed` đang được retry, `analytics.order.cancelled` chờ phía sau nó, nên analytics không thấy một lần hủy trước đơn hàng mà nó hủy. Các message có key khác vẫn tiếp tục được gửi. Tuy nhiên một key chỉ chờ trong khoảng thời gian các lần retry kéo dài: khi một message bị chuyển sang dead-letter (xem phần tiếp theo), các message phía sau nó sẽ được gửi đi.

Message `order.placed` cho các handler in-process không có key, là có chủ ý. Một key được dùng chung bởi mọi message mang nó, bất kể topic hay transport. Nếu message email cũng dùng id đơn hàng, một sự cố của dịch vụ mail sẽ giữ lại các event analytics cho đơn hàng đó.

Service analytics là một ứng dụng Nest riêng, và như mọi service khác, nó sở hữu dữ liệu của mình: một database PostgreSQL riêng, với schema và migration riêng. Nó không bao giờ đọc các bảng của API đơn hàng. Nó ghi lại mỗi event đơn hàng vào một bảng riêng, cũng là dữ liệu của ví dụ:

`order_events` có mỗi event đơn hàng một dòng, và doanh thu là tổng của cột `amount`:

| Cột | Type | Ghi chú |
| --- | --- | --- |
| `seq` | `bigint`, generated identity | Primary key, theo thứ tự đến |
| `order_id` | `text` | Có index |
| `event` | `text` | `placed` hoặc `cancelled` |
| `amount` | `integer` | Thay đổi doanh thu, tính bằng cent: tổng tiền đơn hàng khi đặt, và trừ đi số đó khi hủy |
| `recorded_at` | `timestamptz` | Mặc định là `now()` |

Là một ứng dụng riêng, nó có root module riêng, `AppModule`, đăng ký `OutboxModule` và store một lần, giống như API đơn hàng. Service này chỉ tiêu thụ, nên relay được tắt, và store chạy trên database riêng của service. `OutboxInbox` giữ inbox của service ở đó, cạnh `order_events`, nên một event và record ghi nhận nó đã được xử lý sẽ cùng commit. Các bảng chứa message của store vẫn trống, và khi relay tắt, không có gì poll chúng:

```typescript
@@filename(analytics-service/app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule, getDrizzleToken } from '@nestjs/drizzle';
import { OutboxModule, OutboxStorage } from '@nestjs/outbox';
import { fromDrizzle, PostgresOutboxStore } from '@nestjs/outbox/postgres';
import { drizzle } from 'drizzle-orm/node-postgres';
import { AnalyticsController } from './analytics.controller.js';
import type { Database } from './database/drizzle.js';
import * as schema from './database/schema.js';
import { OrderStatsService } from './order-stats.service.js';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      // This service's own database, not the order API's.
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema }),
    }),
    // Consumer only: no relay runs.
    OutboxModule.forRoot({ relay: { enabled: false } }),
  ],
  controllers: [AnalyticsController],
  providers: [
    {
      // This service's inbox, in its own database (the store's tables for messages stay empty)
      provide: PostgresOutboxStore,
      inject: [getDrizzleToken(), OutboxStorage],
      useFactory: (db: Database, outboxStorage: OutboxStorage) =>
        new PostgresOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
    },
    OrderStatsService,
  ],
})
export class AppModule {}
```

`OrderStatsService` ghi lại một event và trả về doanh thu tính tới thời điểm đó. Nó mở một transaction và gọi `inbox.processInTransaction(tx, 'analytics', messageId, work)`: inbox record và dòng `order_events` cùng commit, nên một event được gửi lại không thay đổi gì, kể cả khi service crash giữa chừng:

```typescript
@@filename(analytics-service/order-stats.service)
import { Injectable, Logger } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { OutboxInbox } from '@nestjs/outbox';
import type { Database, Transaction } from './database/drizzle.js';
import { orderEvents } from './database/schema.js';

/** The fields of the order API's `Order` that this service reads. */
export interface OrderSnapshot {
  id: string;
  total: number;
}

export type OrderEvent = 'placed' | 'cancelled';

@Injectable()
export class OrderStatsService {
  private readonly logger = new Logger(OrderStatsService.name);

  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly outboxInbox: OutboxInbox,
  ) {}

  /**
   * Records an order event once per message id. The inbox record and the event commit in
   * one transaction, so a redelivered message changes nothing. `false` for a duplicate.
   */
  async record(messageId: string, event: OrderEvent, order: OrderSnapshot): Promise<boolean> {
    const outcome = await this.db.transaction(async (tx) =>
      // Records the message id through tx, then runs the callback only if it is new here.
      this.outboxInbox.processInTransaction(tx, 'analytics', messageId, async () => {
        const amount = event === 'placed' ? order.total : -order.total;
        await tx.insert(orderEvents).values({ orderId: order.id, event, amount });
        return this.revenue(tx);
      }),
    );
    if (outcome.duplicate) {
      return false;
    }
    this.logger.log(`Order ${order.id} ${event}, revenue is now ${outcome.result}`);
    return true;
  }

  /** Total revenue in cents. */
  async revenue(db: Database | Transaction = this.db): Promise<number> {
    // ... the sum of amount in order_events, read through db
  }

  // ...
}
```

```typescript
@@filename(analytics-service/analytics.controller)
import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import type { OutboxEnvelope } from '@nestjs/outbox';
import { OrderStatsService, type OrderEvent, type OrderSnapshot } from './order-stats.service.js';

@Controller()
export class AnalyticsController {
  private readonly logger = new Logger(AnalyticsController.name);
  /** The last event handled for each key: one order's events run one at a time. */
  private readonly queues = new Map<string, Promise<void>>();

  constructor(private readonly orderStatsService: OrderStatsService) {}

  @EventPattern('analytics.order.placed')
  onPlaced(@Payload() envelope: OutboxEnvelope<OrderSnapshot>) {
    return this.apply('placed', envelope);
  }

  @EventPattern('analytics.order.cancelled')
  onCancelled(@Payload() envelope: OutboxEnvelope<OrderSnapshot>) {
    return this.apply('cancelled', envelope);
  }

  private apply(event: OrderEvent, envelope: OutboxEnvelope<OrderSnapshot>) {
    // Events arrive in the order the relay published them, but handlers are asynchronous:
    // without a queue, a cancellation could commit before the placement it follows.
    return this.inOrder(envelope.key ?? envelope.id, async () => {
      // The envelope id is the outbox message id: stable across redeliveries.
      const recorded = await this.orderStatsService.record(envelope.id, event, envelope.payload);
      if (!recorded) {
        this.logger.warn(`Skipped duplicate ${envelope.topic} ${envelope.id}`);
      }
    });
  }

  private inOrder(key: string, work: () => Promise<void>): Promise<void> {
    const next = (this.queues.get(key) ?? Promise.resolve()).then(work, work);
    this.queues.set(key, next);
    const forget = () => {
      if (this.queues.get(key) === next) {
        this.queues.delete(key);
      }
    };
    next.then(forget, forget);
    return next;
  }
}
```

Các event của một đơn hàng tới theo thứ tự relay đã publish chúng, nhưng các handler là bất đồng bộ: hai handler có thể chạy cùng lúc, và một lần hủy có thể commit trước lần đặt mà nó đi sau. Controller chạy các event của một key lần lượt từng cái, theo thứ tự đến, và các đơn hàng khác nhau thì chạy song song.

```typescript
@@filename(analytics-service/main)
import { NestFactory } from '@nestjs/core';
import { Transport, type MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: { host: '127.0.0.1', port: Number(process.env.PORT ?? 4001) },
  });
  app.enableShutdownHooks();
  await app.listen();
}
await bootstrap();
```

`inbox.processInTransaction()` chính là thứ mà một handler `@OnOutboxMessage()` có được với `ctx.processInTransaction()`: đúng một lần với các thao tác ghi vào database riêng của consumer. Khi side effect của consumer nằm ngoài database của nó, chẳng hạn một email, hãy dùng `inbox.process(consumer, id, work)` thay vào đó: nó bỏ qua `work` nếu consumer đã thấy id này, và ghi lại id sau khi `work` thành công.

> warning **Cảnh báo** Qua TCP, "đã publish" chỉ có nghĩa là các byte đã rời khỏi API đơn hàng. Nếu service analytics crash sau khi nhận một event nhưng trước khi xử lý nó, event sẽ bị mất. Với những event không được phép mất, hãy dùng một transport có broker xác nhận đã nhận: Kafka, RabbitMQ với publisher confirms, hoặc NATS JetStream. `ClientProxyTransport` nhận một tùy chọn `toPacket` để map một message sang record của transport đó, với key và header riêng.

#### Retry và dead-letter queue <a id="retries-and-the-dead-letter-queue"></a>

Khi một lần publish thất bại, vì một handler đã throw, kết nối TCP bị từ chối, hoặc việc publish mất lâu hơn `publishTimeout`, relay sẽ lên lịch lại message:

- Mỗi lần retry chờ lâu hơn: 1 giây, 2 giây, 4 giây và cứ thế, giới hạn ở `maxDelay` (ở đây là 1 phút). Mỗi lần chờ được ngẫu nhiên hóa trong khoảng từ một nửa tới toàn bộ giá trị, để các lần retry không tới cùng một nhịp.
- Mỗi lần thất bại được log dưới dạng cảnh báo, kèm số thứ tự lần thử và thời gian chờ trước lần tiếp theo.
- Sau `retry.attempts` lần thất bại (ở đây là 10), message được chuyển sang bảng dead-letter với lý do `exhausted` và lỗi của mọi lần thử.
- Một `NonRetryableMessageError` bỏ qua các lần retry. Message bị chuyển sang dead-letter ngay lập tức với lý do `rejected`. Mọi lỗi mà hàm tùy chọn `retry.retryIf(error, attempt, message)` trả về `false` cũng vậy. Khi nhiều handler thất bại, message chỉ bị reject nếu tất cả chúng đều throw `NonRetryableMessageError`. Nếu không, nó được retry, các handler đã thành công được bỏ qua, và nó bị reject khi chỉ còn lại các lỗi vĩnh viễn.
- Một topic không có handler `@OnOutboxMessage()` nào sẽ được retry, chứ không bị chuyển sang dead-letter. Trong một lần rolling deploy, relay của một instance cũ có thể thấy một topic mà chỉ phiên bản mới xử lý.
- Một message đã bị chuyển sang dead-letter không còn giữ chân key của nó nữa: các message sau đó với key đó được publish mà không có nó. Hãy định cỡ `retry` sao cho những sự cố bạn lường trước không dùng hết nó.

Handler kho throw `NonRetryableMessageError` khi không đủ hàng. Retry không tạo ra hàng, nên message đi thẳng tới bảng dead-letter, nơi một người có thể quyết định phải làm gì.

`OutboxDeadLetters` liệt kê, xem chi tiết, đưa lại vào hàng đợi và xóa các dead letter. Package không mount route HTTP nào, nên hãy đưa nó ra phía sau guard của riêng bạn. Cùng controller đó phục vụ số liệu thống kê của outbox, từ service `OutboxMetrics` được xây dựng ở phần tiếp theo:

```typescript
@@filename(outbox-admin/outbox-admin.controller)
import {
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
  Query,
  UseGuards,
} from '@nestjs/common';
import { OutboxDeadLetters } from '@nestjs/outbox';
import { AdminGuard } from './admin.guard.js';
import { OutboxMetrics } from './outbox-metrics.service.js';

@Controller('admin/outbox')
@UseGuards(AdminGuard)
export class OutboxAdminController {
  constructor(
    private readonly outboxDeadLetters: OutboxDeadLetters,
    private readonly outboxMetrics: OutboxMetrics,
  ) {}

  @Get('dead-letters')
  list(@Query('topic') topic?: string) {
    return this.outboxDeadLetters.list({ topic });
  }

  @Post('dead-letters/:id/requeue')
  @HttpCode(HttpStatus.OK)
  async requeue(@Param('id') id: string) {
    return { requeued: await this.outboxDeadLetters.requeue(id) };
  }

  @Delete('dead-letters/:id')
  async purge(@Param('id') id: string) {
    return { purged: await this.outboxDeadLetters.purge(id) };
  }

  @Get('stats')
  stats() {
    return this.outboxMetrics.snapshot();
  }
}
```

```typescript
@@filename(outbox-admin/admin.guard)
import { Injectable, type CanActivate, type ExecutionContext } from '@nestjs/common';
import { createHash, timingSafeEqual } from 'node:crypto';

type HttpRequest = { headers: Record<string, string | string[] | undefined> };

/** Placeholder: protect these routes with your application's real authorization. */
@Injectable()
export class AdminGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<HttpRequest>();
    const token = process.env.ADMIN_TOKEN;
    const given = request.headers['x-admin-token'];
    return !!token && typeof given === 'string' && sameSecret(given, token);
  }
}

/** Compares in constant time, so response times don't give the token away. */
function sameSecret(given: string, expected: string): boolean {
  const digest = (value: string) => createHash('sha256').update(value).digest();
  return timingSafeEqual(digest(given), digest(expected));
}
```

> info **Gợi ý** `AdminGuard` chỉ là placeholder. Dead letter chứa toàn bộ payload, kể cả dữ liệu khách hàng, nên hãy bảo vệ các route này bằng [phân quyền](/security/authorization) thật của ứng dụng.

`requeue()` chuyển một dead letter trở lại outbox với số lần retry được làm mới và **cùng id**. Các consumer đã xử lý nó sẽ bỏ qua nó qua inbox của chúng. Vì vậy sau khi nhập thêm hàng, đưa lại đơn hàng hết hàng vào hàng đợi sẽ giữ chỗ hàng mà không gửi email xác nhận lần thứ hai. `requeue()` và `purge()` cũng nhận một mảng id, hoặc một bộ lọc theo `topic`, `key` hoặc `failedBefore`. Chúng từ chối một bộ lọc trống; hãy truyền `all: true` để nhắm tới mọi dead letter.

#### Chạy nhiều instance <a id="run-several-instances"></a>

Mọi instance của API đơn hàng đều chạy relay của nó trên cùng các bảng, trên bất kỳ số lượng host nào. Database quyết định ai nhận được gì:

- **Claim.** Một relay claim một batch message bằng cách ghi một lease lên chúng trong `lease` (30 giây), với một token ngẫu nhiên cho lần claim đó. Các lần claim lần lượt chờ nhau dưới claim lock của store, và `SKIP LOCKED` bỏ qua những dòng mà relay khác đang ghi, nên hai relay không bao giờ nhận cùng một message. Chúng publish các batch của mình song song.
- **Fencing.** Mọi thao tác ghi sau đó cho một message (đã publish, lên lịch lại, chuyển sang dead-letter) đều phải xuất trình lease token, nên một relay bị treo quá thời hạn lease không thể ghi đè lên công việc của relay đã tiếp quản.
- **Thứ tự giữa các instance.** Các message của một key được gửi đi theo thứ tự transaction của chúng commit, bất kể instance nào đã thêm chúng: `add()` khiến các transaction thêm cùng một key lần lượt chờ nhau. Hãy giữ các transaction thêm message có key ở mức ngắn gọn.
- **Giữ chỗ đúng một lần.** Hai lần gửi của cùng một message chạy cùng lúc, trên các instance khác nhau, sẽ gặp nhau ở primary key của inbox: lần thứ hai chờ transaction đầu tiên, rồi bỏ qua handler nếu transaction đó đã commit.
- **Crash.** Nếu một instance chết trong khi giữ lease, các message của nó sẽ được một instance khác publish khi lease hết hạn. Nếu nó chết sau khi publish nhưng trước khi ghi nhận điều đó, message sẽ được publish lần thứ hai, và inbox của các consumer sẽ loại bỏ bản trùng lặp. Không có gì bị mất theo instance, vì không có gì nằm trên nó: các message là các dòng trong database.
- **Ngân sách lease.** Một relay không bao giờ bắt đầu một lần publish khi lease còn lại ít hơn `publishTimeout` (10 giây). Thay vào đó, nó giải phóng phần còn lại của batch. Hãy giữ `publishTimeout` thấp hơn hẳn `lease`.
- **Đồng hồ.** Lease dùng đồng hồ của relay, nên hãy giữ đồng hồ của các host được đồng bộ bằng NTP, sai lệch nằm gọn trong `lease`.
- **Instance chỉ phục vụ API.** Khởi động một instance với `OUTBOX_RELAY=off` để nó tạo message mà không publish. `notify()` chỉ đánh thức relay của instance đã thêm message, nên một instance có relay sẽ nhận các message trong vòng một `pollInterval`.
- **Worker chỉ chạy relay.** Chiều ngược lại cũng được: một worker khởi động bằng `NestFactory.createApplicationContext(AppModule)` và không có HTTP server sẽ publish những gì các instance API thêm vào. Timer poll của relay giữ process đó sống cho tới khi một shutdown hook dừng nó.

Graceful shutdown cần shutdown hook:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // On SIGTERM the relay stops claiming, finishes in-flight publishes and releases its leases.
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Khi nhận `SIGTERM`, relay ngừng claim và chờ các lần publish đang chạy hoàn tất, mỗi lần tối đa `publishTimeout`. Sau đó nó giải phóng lease trên các message đã claim nhưng chưa bắt đầu, để một instance khác có thể nhận chúng ngay thay vì chờ hết lease. Việc này xảy ra trong `onModuleDestroy()`, trước khi `ClientsModule` đóng TCP client trong `onApplicationShutdown()`.

Để theo dõi outbox, hãy subscribe `OutboxEvents` và đọc `relay.stats()`:

```typescript
@@filename(outbox-admin/outbox-metrics.service)
import { Injectable, type OnModuleInit } from '@nestjs/common';
import { OutboxEvents, OutboxRelay } from '@nestjs/outbox';

@Injectable()
export class OutboxMetrics implements OnModuleInit {
  readonly counters = { published: 0, retried: 0, deadLettered: 0, leaseLost: 0 };
  /** Time from add() to a successful publish, for the latest message. */
  lastPublishLagMs = 0;

  constructor(
    private readonly outboxEvents: OutboxEvents,
    private readonly outboxRelay: OutboxRelay,
  ) {}

  onModuleInit() {
    this.outboxEvents.events$.subscribe((event) => {
      switch (event.type) {
        case 'published':
          this.counters.published++;
          this.lastPublishLagMs = Date.now() - event.message.createdAt;
          break;
        case 'retry-scheduled':
          this.counters.retried++;
          break;
        case 'dead-lettered':
          this.counters.deadLettered++;
          break;
        case 'lease-lost':
          this.counters.leaseLost++;
          break;
      }
    });
  }

  async snapshot() {
    // pending, ready, leased, deadLetters, lagMs (how long the longest-waiting message has waited)...
    const stats = await this.outboxRelay.stats();
    return { ...stats, ...this.counters, lastPublishLagMs: this.lastPublishLagMs };
  }
}
```

`relay.stats()` báo cáo `lagMs`, khoảng thời gian message chờ lâu nhất đã chờ. Nó tăng trong khi một hệ thống phía sau bị down, nên đây là con số để đặt cảnh báo, cùng với `deadLetters`. Một message được lên lịch với `delay` không được tính cho tới khi tới hạn. Event `published` mang theo message, nên `Date.now() - message.createdAt` là độ trễ publish từ đầu đến cuối. `OutboxEvents` phát ra bốn event mà câu `switch` đếm. `lease-lost` nghĩa là một relay khác đã tiếp quản một message trong khi relay này đang publish nó, nên message đó có thể tới consumer hai lần. Đăng ký `OutboxAdminController`, `AdminGuard` và `OutboxMetrics` trong một `OutboxAdminModule`.

Mỗi event cũng được publish trên một channel [`node:diagnostics_channel`](https://nodejs.org/api/diagnostics_channel.html), `nestjs:outbox:published` và các channel tương tự. Các library tracing và metric có thể subscribe vào chúng mà không cần code Nest nào, và chúng thấy mọi ứng dụng Nest trong process.

Hãy bắt lỗi bên trong các subscriber của bạn. Cả RxJS và `diagnostics_channel` đều throw lại lỗi của subscriber dưới dạng uncaught exception, làm dừng process. Lúc đó relay đã lưu kết quả của message, nên bản thân message vẫn an toàn.

Ứng dụng ví dụ chạy phần này trên một PostgreSQL server: hai relay chia nhau 20 đơn hàng, ba instance (một trong số đó chỉ phục vụ API) đặt và hủy 12 đơn hàng với mọi message được publish một lần và các event của mỗi đơn hàng đúng thứ tự, một transaction chờ lock của instance khác trên cùng một key, một instance crash khi đang giữ lease, và một lần graceful shutdown.

#### Chạy thử <a id="try-it"></a>

Tạo hai database, `store` cho API đơn hàng và `analytics` cho service analytics, và áp dụng migration riêng của từng service: migration của API đơn hàng tạo các bảng và sản phẩm của nó từ [Yêu cầu trước](/reliability/outbox#prerequisites), còn migration của service analytics tạo `order_events`.

Khởi động service analytics (TCP port 4001) trên `analytics`, và API đơn hàng (port 3000) trên `store`, với `ADMIN_TOKEN=s3cret` trong môi trường của API. Mỗi service log ra store mà nó đã đăng ký, và store tạo schema ở lần khởi động đầu tiên:

```bash
[Nest] 52654  - 09/30/2026, 6:45:43 PM     LOG [OutboxModule] OutboxStorage: PostgresOutboxStore
[Nest] 52654  - 09/30/2026, 6:45:43 PM     LOG [OutboxModule] PostgresOutboxStore: migrated schema "nest_outbox" to version 1.
[Nest] 52743  - 09/30/2026, 6:45:59 PM     LOG [OutboxModule] OutboxStorage: PostgresOutboxStore
[Nest] 52743  - 09/30/2026, 6:46:00 PM     LOG [OutboxModule] PostgresOutboxStore: migrated schema "nest_outbox" to version 1.
```

Đặt một đơn hàng:

```bash
$ curl -X POST localhost:3000/orders \
    -H 'Content-Type: application/json' \
    -d '{"userId":"user-42","items":[{"productId":"salmon-kibble-2kg","quantity":2}]}'
{"id":"07fafff6-9892-4298-aeef-dc2c3d5d6bf5","userId":"user-42","items":[{"productId":"salmon-kibble-2kg","quantity":2,"price":2499}],"total":4998,"status":"placed"}
```

Log của API hiển thị hai handler in-process:

```bash
[Nest] 52743  - 09/30/2026, 6:46:07 PM     LOG [MailerService] Order confirmation for 07fafff6-9892-4298-aeef-dc2c3d5d6bf5 sent to user-42
[Nest] 52743  - 09/30/2026, 6:46:07 PM     LOG [StockReservationHandler] Reserved stock for order 07fafff6-9892-4298-aeef-dc2c3d5d6bf5
```

Và log của service analytics hiển thị TCP consumer:

```bash
[Nest] 52654  - 09/30/2026, 6:46:07 PM     LOG [OrderStatsService] Order 07fafff6-9892-4298-aeef-dc2c3d5d6bf5 placed, revenue is now 4998
```

Một đơn hàng cho sản phẩm không tồn tại sẽ không qua được validation bên trong transaction. Response là `400`, và không có gì tới được outbox:

```bash
$ curl -X POST localhost:3000/orders \
    -H 'Content-Type: application/json' \
    -d '{"userId":"user-42","items":[{"productId":"catnip-mouse","quantity":1}]}'
{"message":"Unknown product \"catnip-mouse\"","error":"Bad Request","statusCode":400}
```

Giờ hãy đặt hai bao cát vệ sinh vón cục (`clumping-litter-10l`), loại chỉ còn một bao trong kho. API chấp nhận đơn hàng, vì hàng được giữ chỗ một cách bất đồng bộ. Email xác nhận được gửi đi, và việc giữ chỗ bị chuyển sang dead-letter ngay ở lần thử đầu tiên:

```bash
$ curl -X POST localhost:3000/orders \
    -H 'Content-Type: application/json' \
    -d '{"userId":"user-7","items":[{"productId":"clumping-litter-10l","quantity":2}]}'
{"id":"bf4b8bb3-fd47-4c03-9650-ee991cce3dbe","userId":"user-7","items":[{"productId":"clumping-litter-10l","quantity":2,"price":1599}],"total":3198,"status":"placed"}
```

```bash
[Nest] 52743  - 09/30/2026, 6:46:15 PM     LOG [MailerService] Order confirmation for bf4b8bb3-fd47-4c03-9650-ee991cce3dbe sent to user-7
[Nest] 52743  - 09/30/2026, 6:46:15 PM    WARN [OutboxRelay] Dead-lettered order.placed 01a0f335-aae8-7027-b795-ca9dab21e44d after 1 attempt(s) (rejected): NonRetryableMessageError: Not enough stock for "clumping-litter-10l" (order bf4b8bb3-fd47-4c03-9650-ee991cce3dbe)
```

Xem dead-letter queue. Không có header `x-admin-token`, guard trả lời `403`:

```bash
$ curl localhost:3000/admin/outbox/dead-letters -H 'x-admin-token: s3cret'
```

```json
[
  {
    "id": "01a0f335-aae8-7027-b795-ca9dab21e44d",
    "topic": "order.placed",
    "payload": {
      "id": "bf4b8bb3-fd47-4c03-9650-ee991cce3dbe",
      "items": [{ "price": 1599, "quantity": 2, "productId": "clumping-litter-10l" }],
      "total": 3198,
      "status": "placed",
      "userId": "user-7"
    },
    "headers": {},
    "key": null,
    "createdAt": 1790786775784,
    "attempts": 1,
    "lastError": "NonRetryableMessageError: Not enough stock for \"clumping-litter-10l\" (order bf4b8bb3-fd47-4c03-9650-ee991cce3dbe)",
    "history": [
      {
        "at": 1790786775809,
        "error": "NonRetryableMessageError: Not enough stock for \"clumping-litter-10l\" (order bf4b8bb3-fd47-4c03-9650-ee991cce3dbe)",
        "attempt": 1,
        "transport": "local"
      }
    ],
    "reason": "rejected",
    "failedAt": 1790786775809
  }
]
```

Payload được lưu dưới dạng `jsonb`, vốn giữ thứ tự key riêng của nó, nên nó trả về với các key theo thứ tự khác so với lúc được thêm vào.

Nhập thêm hàng, rồi đưa message trở lại hàng đợi theo id của nó:

```bash
$ psql postgres://localhost:5432/store -c "UPDATE products SET in_stock = in_stock + 5 WHERE id = 'clumping-litter-10l'"
UPDATE 1
$ curl -X POST localhost:3000/admin/outbox/dead-letters/01a0f335-aae8-7027-b795-ca9dab21e44d/requeue \
    -H 'x-admin-token: s3cret'
{"requeued":1}
```

Việc giữ chỗ thành công. Inbox của handler email đã có message id này, nên không có email thứ hai nào được gửi:

```bash
[Nest] 52743  - 09/30/2026, 6:46:24 PM     LOG [StockReservationHandler] Reserved stock for order bf4b8bb3-fd47-4c03-9650-ee991cce3dbe
```

Cuối cùng, dừng service analytics bằng `Ctrl+C`, rồi đặt một đơn hàng và hủy nó:

```bash
$ curl -X POST localhost:3000/orders \
    -H 'Content-Type: application/json' \
    -d '{"userId":"user-42","items":[{"productId":"salmon-kibble-2kg","quantity":1}]}'
{"id":"908139a7-2bab-4dd8-988a-bdde8c087074","userId":"user-42","items":[{"productId":"salmon-kibble-2kg","quantity":1,"price":2499}],"total":2499,"status":"placed"}
$ curl -X POST localhost:3000/orders/908139a7-2bab-4dd8-988a-bdde8c087074/cancel
{"id":"908139a7-2bab-4dd8-988a-bdde8c087074","userId":"user-42","items":[{"price":2499,"quantity":1,"productId":"salmon-kibble-2kg"}],"total":2499,"status":"cancelled"}
$ curl localhost:3000/admin/outbox/stats -H 'x-admin-token: s3cret'
{"pending":2,"ready":0,"leased":0,"deadLetters":0,"oldestDueAt":1790786821554,"lagMs":3351,"inFlight":0,"published":5,"retried":3,"deadLettered":1,"leaseLost":0,"lastPublishLagMs":62}
```

Cả hai message analytics đều đang chờ. `lagMs` tăng trong suốt thời gian sự cố, và `retried` đếm các lần thử thất bại. `ready` bằng 0: lần đặt đang chờ lần retry tiếp theo, còn lần hủy đã tới hạn nhưng chờ phía sau nó, vì chúng dùng chung key. API log ra mỗi lần thử thất bại:

```bash
[Nest] 52743  - 09/30/2026, 6:47:01 PM    WARN [OutboxRelay] Retrying analytics.order.placed 01a0f336-5db2-72ad-80c8-17c07908dfa1 in 546ms (attempt 1 of 10 failed): Error: connect ECONNREFUSED 127.0.0.1:4001
[Nest] 52743  - 09/30/2026, 6:47:02 PM    WARN [OutboxRelay] Retrying analytics.order.placed 01a0f336-5db2-72ad-80c8-17c07908dfa1 in 1617ms (attempt 2 of 10 failed): Error: connect ECONNREFUSED 127.0.0.1:4001
[Nest] 52743  - 09/30/2026, 6:47:04 PM    WARN [OutboxRelay] Retrying analytics.order.placed 01a0f336-5db2-72ad-80c8-17c07908dfa1 in 2084ms (attempt 3 of 10 failed): Error: connect ECONNREFUSED 127.0.0.1:4001
```

Khởi động lại service analytics. Ở lần retry tiếp theo, relay publish lần đặt, rồi đến lần hủy. Doanh thu tiếp tục từ chỗ cũ, vì nó nằm trong database của service, chứ không nằm trong bộ nhớ:

```bash
[Nest] 53368  - 09/30/2026, 6:47:29 PM     LOG [OrderStatsService] Order 908139a7-2bab-4dd8-988a-bdde8c087074 placed, revenue is now 10695
[Nest] 53368  - 09/30/2026, 6:47:29 PM     LOG [OrderStatsService] Order 908139a7-2bab-4dd8-988a-bdde8c087074 cancelled, revenue is now 8196
```

#### Testing

Trong một test e2e, hãy chạy PostgreSQL in-process bằng [PGlite](https://pglite.dev) với các migration thật của bạn, tắt vòng lặp poll, và tự điều khiển relay. `relay.runOnce()` claim và xử lý một batch, và resolve khi batch xong:

```typescript
@@filename(test/orders.e2e-spec)
import { PGlite } from '@electric-sql/pglite';
import { getDrizzleToken } from '@nestjs/drizzle';
import { Outbox, OutboxRelay } from '@nestjs/outbox';
import { Test, type TestingModule } from '@nestjs/testing';
import { drizzle } from 'drizzle-orm/pglite';
import { migrate } from 'drizzle-orm/pglite/migrator';
import { fileURLToPath } from 'node:url';
import { of } from 'rxjs';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { ANALYTICS_SERVICE, AppModule } from '../src/app.module.js';
import { MailerService } from '../src/notifications/mailer.service.js';
import { OrdersService } from '../src/orders/orders.service.js';

describe('OrdersService (outbox)', () => {
  const client = new PGlite(); // PostgreSQL, in-process
  const db = drizzle({ client });
  const mailer = { sendOrderConfirmation: vi.fn() };
  const analytics = { emit: vi.fn(() => of(undefined)) };
  let moduleRef: TestingModule;
  let orders: OrdersService;
  let relay: OutboxRelay;

  beforeAll(async () => {
    // Your migrations: the order tables. The outbox's store creates its schema in init().
    await migrate(db, { migrationsFolder: fileURLToPath(new URL('../drizzle', import.meta.url)) });
    process.env.OUTBOX_RELAY = 'off'; // no poll loop: the test drives the relay
    moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(getDrizzleToken())
      .useValue(db) // the outbox's store runs on it too
      .overrideProvider(MailerService)
      .useValue(mailer)
      .overrideProvider(ANALYTICS_SERVICE)
      .useValue(analytics)
      .compile();
    await moduleRef.init();
    orders = moduleRef.get(OrdersService);
    relay = moduleRef.get(OutboxRelay);
  });

  afterAll(async () => {
    await moduleRef.close();
    await client.close();
  });

  it('publishes order events only after the order commits', async () => {
    const order = await orders.placeOrder({ userId: 'user-42', items: [{ productId: 'salmon-kibble-2kg', quantity: 1 }] });
    expect(mailer.sendOrderConfirmation).not.toHaveBeenCalled();

    await relay.runOnce(); // claim and publish one batch

    expect(mailer.sendOrderConfirmation).toHaveBeenCalledWith(order);
    expect(analytics.emit).toHaveBeenCalledWith(
      'analytics.order.placed',
      expect.objectContaining({ key: order.id, payload: order }),
    );
    expect(await relay.stats()).toMatchObject({ pending: 0, deadLetters: 0 });
  });

  it('publishes nothing when the transaction rolls back', async () => {
    const outbox = moduleRef.get(Outbox);
    const add = outbox.add.bind(outbox);
    vi.spyOn(outbox, 'add').mockImplementationOnce(async (tx, messages) => {
      await add(tx, messages); // the messages are written...
      throw new Error('Connection terminated unexpectedly'); // ...then the transaction fails
    });

    await expect(
      orders.placeOrder({ userId: 'user-42', items: [{ productId: 'salmon-kibble-2kg', quantity: 1 }] }),
    ).rejects.toThrow('Connection terminated unexpectedly');

    expect(await relay.stats()).toMatchObject({ pending: 0 });
    expect(await relay.runOnce()).toMatchObject({ claimed: 0 });
  });
});
```

- Outbox, store của nó, các migration và việc dispatch in-process đều là thật. Chỉ có mailer và client analytics là bản giả.
- Override database mà `DrizzleModule` đăng ký, có token do `getDrizzleToken()` trả về, bằng database PGlite. Factory của store inject cùng token đó, nên đơn hàng và outbox dùng chung database, giống như chúng dùng chung pool trong production, và store tạo schema của nó ở đó khi module khởi tạo. Module vẫn mở pool `pg` của nó, pool này không bao giờ kết nối.
- Test rollback để `outbox.add()` ghi các message, rồi làm transaction thất bại. Đơn hàng và các message của nó cùng biến mất, và `runOnce()` không tìm thấy gì để claim.
- Với các hành vi phụ thuộc thời gian, như backoff và lease hết hạn, hãy tua `Date.now()` về phía trước bằng `vi.spyOn(Date, 'now')`. Relay lấy thời gian từ đó, cho chính nó và cho store, còn các timer thật vẫn tiếp tục chạy cho socket và HTTP.
- PGlite chỉ có một kết nối, nên nó chạy từng transaction một. Hãy test các tình huống race giữa các instance trên một PostgreSQL server, cùng major version với production, như ví dụ đã làm cho [nhiều instance](/reliability/outbox#run-several-instances).
- Để loại outbox ra khỏi một test, hãy thay store: `overrideProvider(PostgresOutboxStore).useValue(new InMemoryOutboxStore())`. Một instance thuần không tự đăng ký, nên outbox fallback về store trong bộ nhớ của nó, và schema của store không được tạo. Tuy nhiên nó không thể tham gia vào các Drizzle transaction của bạn: một message đã rollback vẫn được publish, và store log một cảnh báo ở lần đầu tiên nó nhận được transaction của bạn.

#### Đảm bảo về việc gửi <a id="delivery-guarantees"></a>

Đảm bảo tổng thể là **ít nhất một lần** (at least once), với inbox của các consumer hấp thụ các bản trùng lặp.

| Tình huống | Kết quả |
| --- | --- |
| Transaction đơn hàng rollback | Message chưa từng tồn tại và không bao giờ được publish |
| Transaction đơn hàng commit | Cuối cùng sẽ được publish, hoặc bị chuyển sang dead-letter kèm lịch sử lỗi |
| Một relay chết sau khi claim | Được một instance khác publish khi lease của nó hết hạn |
| Một relay chết sau khi publish, trước khi ghi nhận | Được publish hai lần. Inbox loại bỏ bản trùng lặp |
| Một lần publish hoặc handler thất bại | Được retry kèm backoff, rồi chuyển sang dead-letter (`exhausted`) |
| Một lần publish hoặc handler chạy quá `publishTimeout` | Được tính là một lần thử thất bại, và `ctx.signal` bị abort. Một handler bỏ qua nó sẽ tiếp tục chạy; một lần retry trong cùng process sẽ chờ nó |
| `NonRetryableMessageError`, hoặc `retryIf` trả về `false` | Bị chuyển sang dead-letter ngay lập tức (`rejected`) |
| Các message dùng chung một `key` | Được publish theo thứ tự chúng được thêm vào. Một message đang retry giữ lại phần còn lại của key |
| Một message bị chuyển sang dead-letter | Key của nó được giải phóng, nên các message sau với key đó vượt lên trước nó |
| Transport TCP, Redis hoặc NATS core | "Đã publish" nghĩa là thao tác ghi đã rời khỏi process. Một consumer crash sau đó sẽ làm mất message |

Thứ tự trong một key là thứ tự mà store đánh số các message, không phải id của chúng: một id lấy từ đồng hồ của instance tạo ra nó, và các đồng hồ có thể lệch nhau. PostgreSQL chạy các transaction đồng thời, nên store khiến các transaction thêm message có cùng key lần lượt chờ nhau, và việc đánh số tuân theo thứ tự commit (xem [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database)).
#### Checklist cho production <a id="production-checklist"></a>

- Đăng ký một store trên database của ứng dụng, trên một database server: `PostgresOutboxStore`, `MySqlOutboxStore`, hoặc một store của riêng bạn ([Hợp đồng của store](/reliability/outbox#the-store-contract)). Không bao giờ giữ outbox trên chính instance, trong bộ nhớ hay trong một database dạng file như SQLite trên ổ đĩa của nó: filesystem của container biến mất khi task bị thay thế, và mọi message chưa được publish cũng biến mất theo. Cơ chế bảo vệ production từ chối khởi động khi không có store; chỉ đặt `allowInMemoryStorage` cho một process mà bạn chấp nhận mất message.
- Áp dụng migration của store trước khi một phiên bản mới khởi động, bằng `npx @nestjs/outbox migrate` hoặc công cụ migration của bạn, và kiểm tra chúng trong CI bằng `npx @nestjs/outbox status`. Với `NODE_ENV=production`, store không migrate lúc khởi động: một schema chậm phiên bản sẽ làm việc khởi động thất bại.
- Trên PostgreSQL, giữ isolation level mặc định của database ở READ COMMITTED, vốn là mặc định: store từ chối một level chặt hơn lúc khởi động.
- Cảnh báo dựa trên `lagMs` và `deadLetters` từ `relay.stats()`, và các event `dead-lettered`, từ `OutboxEvents` hoặc diagnostics channel `nestjs:outbox:dead-lettered`.
- Định cỡ `retry` theo khoảng thời gian các hệ thống phía sau có thể bị down. Mặc định của package là 20 lần thử, tổng cộng khoảng 30 đến 60 phút. 10 lần thử giới hạn ở 1 phút trong bài hướng dẫn này sẽ bỏ cuộc sau 2 đến 4 phút, và sau đó các message tiếp theo của một key sẽ vượt lên trước message đã bị chuyển sang dead-letter.
- Giữ tên `consumer` ổn định. Các entry trong inbox được đánh key theo tên này, nên một consumer bị đổi tên sẽ thấy mọi message cũ như mới.
- Dọn dẹp inbox. Không có gì tự gọi `OutboxInbox.prune()` cho bạn. Hãy chạy nó từ một [cron job](/application/task-scheduling#declarative-cron-jobs), ví dụ `inbox.prune('30d')`, với khoảng thời gian dài hơn mọi lần gửi lại, kể cả các lần requeue.
- Giữ handler ngắn hơn `publishTimeout`, và truyền `ctx.signal` cho các lời gọi mà chúng thực hiện. Một handler chậm hơn được tính là một lần thử thất bại; lease không được gia hạn.
- Gọi `app.enableShutdownHooks()`, để các lần deploy rút cạn relay thay vì để lại các message đang bị giữ lease. `DrizzleModule` đóng pool sau đó, trong `onApplicationShutdown()`.
- Bảo vệ các route dead-letter. Chúng để lộ toàn bộ payload.
- Đánh phiên bản payload. Một message được bản release trước thêm vào vẫn có thể được gửi sau một lần deploy.
- Cho mỗi luồng có thứ tự một key riêng, và đừng dùng chung một key giữa các message cho các transport khác nhau.
- Giữ các transaction gọi `outbox.add()` ở mức ngắn. Lock theo từng key khiến các transaction thêm message có cùng key lần lượt chờ nhau. Interactive transaction của Prisma mặc định timeout sau 5 giây (`transactionOptions` trên client, hoặc theo từng lời gọi).
- Trên MySQL, hãy chạy lại một transaction gọi `outbox.add()` khi nó thất bại do deadlock (lỗi 1213): MySQL đã rollback toàn bộ transaction đó.
- Định cỡ connection pool cho cả request của bạn lẫn relay: mỗi lần claim giữ một kết nối cho một transaction ngắn.
- Chạy các contract suite với `concurrent: true` trong CI trên store của riêng bạn, trên một pool, với database engine và major version mà bạn chạy trong production.

#### Hợp đồng của store <a id="the-store-contract"></a>

`PostgresOutboxStore` và `MySqlOutboxStore` implement hai interface lưu trữ của package: `OutboxStore` cho message và dead letter, và `OutboxInboxStore` cho inbox của các consumer. Với một database khác, hãy implement chúng trong một provider của riêng bạn. JSDoc của từng method trên các interface đó cho biết nó phải làm gì, và mỗi quy tắc ngăn chặn tình huống race nào.

**Đăng ký.** Store là một singleton provider bình thường gọi `registerSource()` trên `OutboxStorage` (có thể inject) trong constructor của nó, cho các hợp đồng mà nó implement, theo tên: `messages` và `inbox`. Một service chỉ tiêu thụ có thể chỉ đăng ký một inbox store. Registry kiểm tra cấu trúc ngay lập tức (mọi method đều là hàm), từ chối lần đăng ký thứ hai trừ khi truyền `replace: true`, và bị khóa khi `OutboxModule` khởi tạo, đồng thời log ra store đang dùng. Một provider request-scoped, một provider trong lazy-loaded module, hoặc một lifecycle hook sẽ đăng ký quá muộn, và throw.

Không có gì được đăng ký, outbox chạy trên store trong bộ nhớ, và nói rõ điều đó lúc khởi động:

```bash
[Nest] 19039  - 09/23/2026, 11:28:45 AM     LOG [OutboxModule] OutboxStorage: InMemoryOutboxStore (the default: state is lost on restart and not shared between instances)
```

Đó không chỉ là một lối tắt mất dữ liệu khi restart. Một store trong bộ nhớ không thể tham gia vào transaction của bạn, nên nó áp dụng `add()` ngay lập tức, và cảnh báo ở lần đầu tiên nhận được một transaction handle. Trong lần chạy này, transaction của đơn hàng đã thêm message rồi thất bại, nhưng email xác nhận vẫn được gửi đi:

```bash
[Nest] 19039  - 09/23/2026, 11:28:45 AM    WARN [OutboxModule] InMemoryOutboxStore.add() received your transaction handle, and can't join it: the write applies at once, so a rolled-back transaction won't undo it. Register a store for your database with OutboxStorage.registerSource(). (Logged once.)
[Nest] 19039  - 09/23/2026, 11:28:46 AM     LOG [MailerService] Order confirmation for 7435d418-5d9a-48a0-b186-6cfd2e34b9f4 sent to user-7
```

Với `NODE_ENV=production`, cùng ứng dụng đó không khởi động:

```bash
Error: OutboxStorage: no store is registered for `messages` (OutboxStore) and `inbox` (OutboxInboxStore), and NODE_ENV is "production": in memory, messages and inbox records would be lost on restart and not shared between instances. Register a store on your database: PostgresOutboxStore (@nestjs/outbox/postgres), MySqlOutboxStore (@nestjs/outbox/mysql), or your own OutboxStore and OutboxInboxStore in a provider that injects OutboxStorage and calls `storage.registerSource({ messages: this, inbox: this })` in its constructor. Or set `allowInMemoryStorage: true` in the OutboxModule options to run in memory anyway.
```

`allowInMemoryStorage: true` trong tùy chọn của module là lối ra có chủ đích, cho một instance duy nhất có thể chấp nhận mất trạng thái.

**Tính nguyên tử.** Producer, relay và các lần gửi chạy đua với nhau qua store. `add()` phải đánh số các message của một key theo thứ tự transaction của chúng commit, `claim()` không bao giờ được cho hai relay cùng giữ lease một message hay chạy trước một message cũ hơn của cùng key, các thao tác ghi sau đó của một relay chỉ được áp dụng khi lease của nó còn hiệu lực, và hai lần gửi của cùng một message phải gặp nhau ở `recordInbox()`. Vì vậy mọi method thay đổi trạng thái đều là một câu lệnh có điều kiện, hoặc một transaction với lock đúng, không bao giờ là một lần đọc theo sau là một lần ghi. `add()` và `recordInbox()` nhận nguyên vẹn transaction object của bạn: chúng phải ghi qua nó, và từ chối mọi thứ không phải transaction, chẳng hạn chính database, bằng `OutboxTransactionRequiredError`.

**Hãy test nó** bằng các suite từ `@nestjs/outbox/testing`. `outboxStoreContract()` và `outboxInboxStoreContract()` trả về các hợp đồng dưới dạng test case dùng được với mọi test runner: mỗi case là một `name` và một hàm `run()` throw khi thất bại. Các test của bài hướng dẫn chạy chúng trên `PostgresOutboxStore` qua Drizzle, giống như bạn sẽ làm với store của mình, với một hàm trả về store trên các bảng đã được làm trống, một cách để mở một transaction của bạn, và `notATransaction`, một handle mà store phải từ chối:

```typescript
@@filename(test/drizzle-outbox.store.e2e-spec)
/** A store on emptied tables, built the way Nest builds it: with the database and a registry. */
async function freshStore(db: Database): Promise<OutboxStoreHarness<Transaction> & { store: PostgresOutboxStore }> {
  await db.execute(sql`TRUNCATE nest_outbox.messages, nest_outbox.dead_letters, nest_outbox.inbox RESTART IDENTITY`);
  return {
    store: new PostgresOutboxStore({ executor: fromDrizzle(db) }, new OutboxStorage()),
    transaction: (work) => db.transaction(work),
    notATransaction: db,
  };
}

describe('PostgresOutboxStore through fromDrizzle on PGlite: the store contract', () => {
  // ...
  // The concurrency cases run too; with one connection, PGlite runs them one transaction at a time.
  for (const c of outboxStoreContract(() => freshStore(db), { concurrent: true })) {
    it(c.name, c.run);
  }
  describe('the inbox contract', () => {
    for (const c of outboxInboxStoreContract(() => freshStore(db), { concurrent: true })) {
      it(c.name, c.run);
    }
  });
});
```

`concurrent: true` thêm vào các tình huống race mà một store ngây thơ sẽ thất bại: các producer của một key có transaction chồng lấn, các relay claim song song, producer và relay chạy đua, các thao tác ghi của một relay đã cũ chạy đua với một lần tiếp quản, và hai lần gửi của cùng một message. Trên PGlite chúng chạy từng transaction một, nên hãy chạy chúng trên một server có pool nữa, nơi các transaction thực sự chồng lấn, với database engine và major version mà bạn chạy trong production. Bài hướng dẫn chạy cả hai suite qua từng client của nó: Drizzle trên PGlite và trên PostgreSQL, TypeORM và Prisma trên PostgreSQL, và Drizzle trên MySQL, với `MySqlOutboxStore`. Các test riêng của package cũng chạy chúng trên các store được viết tay bằng Drizzle, TypeORM và Prisma, làm bằng chứng rằng một store được viết theo các interface sẽ vượt qua chúng.

Store của các package khác có thể nằm ở nơi khác: idempotency store hợp với Redis. Store của outbox thì không thể, vì các message của nó phải commit cùng các dòng dữ liệu của bạn, trong database của bạn.

#### Dùng BullMQ trên Postgres thay thế <a id="using-bullmq-on-postgres-instead"></a>

BullMQ 6 có backend PostgreSQL, nên cũng hợp lý khi hỏi liệu bảng job của nó có thể làm outbox hay không. Kết quả nghiên cứu của package về BullMQ 6.3.x (từ việc đọc code đã publish, không phải chạy thực tế) là: hiện tại thì chưa.

- `Queue.add()` luôn chạy trên connection pool riêng của BullMQ, ở chế độ autocommit. Interface backend cố ý không để lộ type kết nối hay transaction nào, nên một `add()` không thể tham gia vào transaction insert đơn hàng của bạn.
- Bản thân việc đưa vào hàng đợi là một hàm SQL, `bullmq.add_job(...)`. Gọi nó trên transaction của bạn thì sẽ nguyên tử, nhưng hàm này là nội bộ, signature của nó thay đổi theo các schema migration của BullMQ, và mọi transaction gọi nó sẽ lấy global NOTIFY lock của Postgres khi commit.
- `@nestjs/bullmq` 12.0.0 không thể chọn backend Postgres cho một queue riêng lẻ. Cách duy nhất là `setDefaultBackendFactory()` áp dụng cho toàn process của BullMQ.

Thứ cần có là một tùy chọn ở upstream để chạy `add()` trên một client do bên gọi cung cấp (để job commit cùng đơn hàng), cộng với một tùy chọn backend trong `@nestjs/bullmq`. Có cả hai, bảng job sẽ là outbox, và worker của BullMQ sẽ đảm nhận việc claim, retry và tập job thất bại mà không cần relay ở giữa. Cho tới lúc đó, hãy dùng outbox này và publish sang BullMQ từ một `OutboxTransport` gọi `queue.add(topic, payload)` với `id` của outbox message làm `jobId`, để một message được publish lại sẽ bị bỏ qua khi job vẫn còn tồn tại.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có trong [sample 37-outbox](https://github.com/nestjs/nest/tree/master/sample/37-outbox): API đơn hàng trên PostgreSQL với Drizzle, các handler in-process, microservice analytics có database riêng, admin API cho dead-letter, và các test.

#### Tham khảo <a id="reference"></a>

##### Tùy chọn của module <a id="module-options"></a>

`OutboxModule.forRoot()` nhận các tùy chọn sau. `forRootAsync()` nhận các class `transports`, `imports` và `isGlobal` ở cấp ngoài cùng, và phần còn lại từ `useFactory`, `useClass` hoặc `useExisting` (một class implement `OutboxOptionsFactory`), như trong [Đăng ký outbox](/reliability/outbox#register-the-outbox). Token của các tùy chọn là `OUTBOX_MODULE_OPTIONS`. Store không phải là một tùy chọn: hãy đăng ký nó làm provider, như trong [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database). Khoảng thời gian là số mili giây, hoặc chuỗi như `'30s'` và `'1m'`.

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `transports` | Không có | Các class hoặc instance `OutboxTransport` có tên. `local`, tức các handler `@OnOutboxMessage()`, có sẵn và được dành riêng |
| `imports` | Không có | Các module mà export của chúng được các class transport inject |
| `route` | Đích duy nhất | `(message) => name`: transport duy nhất mà một message được gửi tới. Bắt buộc khi có cả handler lẫn transport, hoặc có nhiều transport |
| `relay.enabled` | `true` | `false` ở các instance chỉ tạo hoặc chỉ tiêu thụ message |
| `relay.pollInterval` | `'1s'` | Thời gian chờ giữa các lần poll khi rảnh |
| `relay.batchSize` | `100` | Số message cho mỗi lần claim |
| `relay.lease` | `'30s'` | Thời gian một lần claim có tính độc quyền |
| `relay.concurrency` | `10` | Số nhóm key được publish song song trong một batch |
| `relay.publishTimeout` | Một phần ba `lease` | Một lần publish chậm hơn được tính là một lần thử thất bại, và `signal` của nó bị abort |
| `retry.attempts` | `20` | Tổng số lần thử, tính cả lần đầu, trước khi message bị chuyển sang dead-letter. `retry: 5` nghĩa là 5 lần thử; `retry: false` là một lần thử duy nhất |
| `retry.backoff` | `'1s'` nhân đôi tới `'5m'`, jitter kiểu equal | Một object với `delay`, `factor`, `maxDelay` và `jitter` (`'equal'`, `'full'` hoặc `'none'`), hoặc một hàm `(attempt, error, message) => duration` |
| `retry.retryIf` | Mọi lỗi | `(error, attempt, message) => boolean`: `false` chuyển message sang dead-letter ngay lập tức |
| `allowInMemoryStorage` | `false` | Với `NODE_ENV=production` và không có store được đăng ký, việc khởi động sẽ thất bại; `true` vẫn chạy trên store trong bộ nhớ |
| `isGlobal` | `true` | Đăng ký module ở phạm vi global |

##### Store <a id="stores"></a>

`new PostgresOutboxStore(options, outboxStorage)`, từ `@nestjs/outbox/postgres`, và `new MySqlOutboxStore(options, outboxStorage)`, từ `@nestjs/outbox/mysql`, nhận các tùy chọn sau. Không có `outboxStorage`, store không đăng ký ở đâu cả, phù hợp cho một script hoặc một test.

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `executor` | Bắt buộc | Cách store tiếp cận database: một trong các executor bên dưới, từ cùng entry point với store. Executor của dialect kia sẽ không compile |
| `schema` | `'nest_outbox'` | Trên PostgreSQL, là schema chứa các bảng của nó, được migration đầu tiên tạo ra: chữ cái, chữ số và dấu gạch dưới, không bắt đầu bằng chữ số, tối đa 63 ký tự. Trên MySQL, là tiền tố của các bảng trong database của kết nối: chữ thường, chữ số và dấu gạch dưới, không bắt đầu bằng chữ số, tối đa 40 ký tự |
| `migrate` | `true`, trừ khi `NODE_ENV=production` | Áp dụng các migration còn chờ khi ứng dụng khởi động. Với `false`, việc khởi động thất bại với `OutboxSchemaError` khi schema còn chậm phiên bản |

Mỗi executor nhận database client của bạn, và loại transaction object riêng của nó, thứ mà `outbox.add()` và `processInTransaction()` sau đó sẽ nhận:

| Executor | Nhận | Transaction object |
| --- | --- | --- |
| `fromDrizzle(db)` | Một Drizzle database: trên PostgreSQL, với bất kỳ driver nào; trên MySQL, là `mysql2` | `tx` mà `db.transaction()` đưa cho callback của nó |
| `fromTypeOrm(dataSource)` | Một `DataSource` có type `postgres` hoặc `mysql` | `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó, hoặc một `QueryRunner` sau `startTransaction()` |
| `fromPrisma(prisma, options)` | Một Prisma client, qua một driver adapter như `@prisma/adapter-pg`, hoặc `@prisma/adapter-mariadb` cho MySQL. `maxWait` (mặc định `'10s'`) và `timeout` (mặc định `'1m'`) giới hạn các transaction riêng của store | Transaction client mà `prisma.$transaction()` đưa cho callback của nó |
| `fromKysely(db)` | Một instance `Kysely` với dialect PostgreSQL hoặc MySQL | Transaction mà `db.transaction().execute()` đưa cho callback của nó |
| `fromPg(pool)` | PostgreSQL: một `Pool` của node-postgres, hoặc một `Client` đã kết nối | Một client, chẳng hạn từ `pool.connect()`, sau `BEGIN` |
| `fromMysql2(pool)` | MySQL: một pool `mysql2/promise`, hoặc một connection | Một connection, chẳng hạn từ `pool.getConnection()`, sau `beginTransaction()` |

Method `migrate()` của store áp dụng ngay các migration còn chờ, bất kể tùy chọn `migrate` nói gì, và resolve với các phiên bản mà nó đã áp dụng. Method static `migrationSql()` trả về SQL của chúng, kèm phần ghi chép phiên bản, còn `MySqlOutboxStore.migrationStatements()` trả về cùng các câu lệnh đó, mỗi chuỗi một câu. Chúng nhận `schema`, phiên bản bắt đầu `from` (mặc định `0`, một database mới) và phiên bản đích `to` (mặc định: phiên bản mà package cần), và `migrationSql()` nhận thêm `statementBreakpoints`. Từ phiên bản 0 trên PostgreSQL, SQL bắt đầu bằng `CREATE SCHEMA IF NOT EXISTS`, câu này cần quyền CREATE trên database: hãy bỏ nó đi nếu ai đó đã tạo schema cho bạn. `schemaVersion` static là phiên bản mà package cần.

Command line, `npx @nestjs/outbox`, nhận `--url` (mặc định `DATABASE_URL`) và `--schema` (mặc định `nest_outbox`). Một URL `mysql://` sẽ chọn các migration của `MySqlOutboxStore`, và cần cài `mysql2`:

| Lệnh | Làm gì |
| --- | --- |
| `migrate` | Áp dụng các migration còn chờ, như `migrate: true` làm lúc khởi động |
| `status` | In ra phiên bản của schema và phiên bản mà package cần, và thoát với mã 1 khi schema còn chậm phiên bản |
| `sql` | In ra SQL của `migrationSql()`, từ `--from` tới `--to`, không cần database: của PostgreSQL, hoặc của MySQL với `--dialect mysql`. `--statement-breakpoints` tách các câu lệnh cho một custom migration của drizzle-kit |

Trên MySQL, store cần MySQL 8.4 LTS hoặc 9.x với `sql_mode` strict, mặc định của MySQL: một `sql_mode` lỏng lẻo, hoặc MariaDB, sẽ làm việc khởi động thất bại.

##### Message và handler <a id="messages-and-handlers"></a>

Một message được truyền cho `outbox.add(tx, message)` ([Lưu đơn hàng và message của nó trong một transaction](/reliability/outbox#save-the-order-and-its-messages-in-one-transaction)) có các field sau:

| Field | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `topic` | Có | Thứ mà `route` và các handler dùng để khớp |
| `payload` | Có | Được serialize sang JSON khi `add()` chạy |
| `key` | Không | Key xác định thứ tự: các message dùng chung key được publish lần lượt từng cái, theo thứ tự commit |
| `headers` | Không | Các header dạng chuỗi, được truyền cho transport |
| `id` | Không | Id duy nhất của riêng bạn. Mặc định là một UUIDv7; consumer khử trùng lặp dựa trên nó |
| `delay` hoặc `availableAt` | Không | Không publish sớm hơn khoảng thời gian này tính từ bây giờ, hoặc sớm hơn thời điểm này. Không dùng cả hai |

- `@OnOutboxMessage(topic, options)` nhận `consumer` (bắt buộc: tên inbox của handler) và `inbox` (mặc định `true`; `false` chạy mọi lần gửi). [Xử lý order.placed in-process](/reliability/outbox#handle-orderplaced-in-process)
- Context của một handler có `message`, `consumer`, `attempt`, `signal` và `processInTransaction(tx, work)`.
- `ClientProxyTransport(token, options)` emit topic với một envelope gồm `id`, `topic`, `key`, `headers`, `createdAt` và `payload` (`OutboxEnvelope`). Tùy chọn `toPacket(message, envelope)` của nó trả về `pattern` và `data` của riêng bạn. [Publish tới microservice analytics](/reliability/outbox#publish-to-the-analytics-microservice)

##### Service <a id="services"></a>

| Service | Method |
| --- | --- |
| `Outbox` | `add(tx, messages)`, `notify()` |
| `OutboxRelay` | `stats()`: `pending`, `ready`, `leased`, `deadLetters`, `oldestDueAt`, `lagMs`, `inFlight`. `runOnce()`: `claimed`, `published`, `retried`, `deadLettered`, `released`, `leaseLost`. Ngoài ra còn có `notify()`, `start()` và `stop()` |
| `OutboxDeadLetters` | `list(query)` (theo `topic`, `key`, `limit`, `offset`; mới nhất trước), `get(id)`, `requeue(target)`, `purge(target)`. Một target là một id, một mảng id, hoặc một bộ lọc theo `ids`, `topic`, `key`, `failedBefore`, hoặc `all: true`. [Retry và dead-letter queue](/reliability/outbox#retries-and-the-dead-letter-queue) |
| `OutboxInbox` | `process(consumer, id, work)`, `processInTransaction(tx, consumer, id, work)`, `prune(olderThan)`. Cả hai method `process` đều resolve `duplicate`, và `result` khi `work` đã chạy |

##### Event <a id="events"></a>

`OutboxEvents.events$` phát ra mỗi event, và publish nó trên channel `node:diagnostics_channel` tương ứng. Mọi payload đều có `type` và `message`. [Chạy nhiều instance](/reliability/outbox#run-several-instances) đếm chúng. Hãy bắt lỗi bên trong các subscriber của bạn: cả RxJS và `diagnostics_channel` đều throw lại lỗi của subscriber dưới dạng uncaught exception.

| Event | Channel | Các field khác | Khi nào |
| --- | --- | --- | --- |
| `published` | `nestjs:outbox:published` | `transport`, `durationMs` | Một transport đã chấp nhận message |
| `retry-scheduled` | `nestjs:outbox:retry-scheduled` | `transport`, `error`, `attempt`, `delayMs` | Một lần publish thất bại và sẽ được retry |
| `dead-lettered` | `nestjs:outbox:dead-lettered` | `transport`, `error`, `attempt`, `reason` | Message đã được chuyển sang dead letter. Hãy đặt cảnh báo cho nó |
| `lease-lost` | `nestjs:outbox:lease-lost` | Không có | Một relay khác đã tiếp quản message giữa chừng lúc publish, nên nó có thể được publish hai lần |

`reason` của một dead letter là `exhausted` (đã hết số lần retry) hoặc `rejected` (một `NonRetryableMessageError`, hoặc `retryIf` trả về `false`).

##### Lỗi <a id="errors"></a>

Không lỗi nào mang HTTP status. `OutboxError` là class cơ sở của bốn lỗi mà package throw.

| Lỗi | Xảy ra khi |
| --- | --- |
| `OutboxTransactionRequiredError` | `add()` hoặc `processInTransaction()` không nhận được transaction handle, hoặc một store từ chối một handle không phải transaction |
| `OutboxPublishTimeoutError` | Một lần publish chạy quá `relay.publishTimeout` (`timeoutMs`). Được tính là một lần thử thất bại |
| `OutboxNoHandlerError` | Không có handler `@OnOutboxMessage()` nào cho topic trong process này (`topic`). Sẽ được retry |
| `OutboxSchemaError` | Schema của store chậm hơn các migration của package trong khi `migrate` bị tắt, hoặc việc áp dụng chúng thất bại (`cause`): việc khởi động và mọi lời gọi đều thất bại cho tới khi được sửa. Kèm theo `schema`, `version` của nó và `requiredVersion`. Từ `@nestjs/outbox/postgres` và `@nestjs/outbox/mysql` |
| `NonRetryableMessageError` | Bạn throw nó từ một handler hoặc transport để chuyển message sang dead-letter mà không retry |
