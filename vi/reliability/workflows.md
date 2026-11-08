### Durable workflow

`@nestjs/workflows` chạy các quy trình kéo dài nhiều ngày, như xử lý giao một đơn hàng, dưới dạng một method `async` duy nhất, với các bước được lưu trong database của bạn và tồn tại qua các lần restart.

Có những quy trình nghiệp vụ kéo dài nhiều ngày và trải qua nhiều hệ thống. Trong một cửa hàng online bán thức ăn và đồ dùng cho mèo, xử lý giao một đơn hàng nghĩa là:

1. Trừ tiền thẻ của khách hàng qua payment provider.
2. Giữ chỗ các sản phẩm trong kho.
3. Chờ tối đa 3 ngày để nhận webhook `shipment.delivered` từ đơn vị vận chuyển.
4. Nếu webhook không bao giờ tới, hoặc đơn vị vận chuyển trả kiện hàng về, hãy hoàn tiền và giải phóng hàng trong kho. Nếu không, chờ 7 ngày rồi nhờ khách hàng viết đánh giá.

Quy trình phải tồn tại qua các lần deploy và crash, chỉ trừ tiền đúng một lần, hoàn tác công việc của nó khi thất bại, và cho bộ phận hỗ trợ biết mỗi đơn hàng đang ở đâu. Với `@nestjs/workflows`, bạn viết nó thành một method `async` trên một class injectable. Mỗi side effect chạy trong một **step** được ghi journal. Sau một lần restart, method chạy lại từ đầu, và các step đã hoàn tất trả về kết quả đã ghi lại thay vì chạy hai lần. Các lần chờ (wait) và ngủ (sleep) sẽ đỗ instance lại trong database của chính bạn, nơi bất kỳ process nào trên bất kỳ host nào cũng có thể nhận nó khi tới hạn. Không có workflow server nào phải vận hành.

#### Workflow, queue hay saga? <a id="workflows-queues-or-sagas"></a>

Nest đã có hai công cụ cho những việc diễn ra sau, và mỗi công cụ vẫn là lựa chọn đúng cho việc của nó:

- **[BullMQ](/application/queues#bullmq-installation)** chạy từng đơn vị công việc nền một, như gửi email hay chuyển mã video, với giới hạn đồng thời, giới hạn tần suất, độ ưu tiên, và job trì hoãn hoặc lặp lại. Một quy trình chỉ có một hành động trì hoãn ("hủy đơn hàng nếu chưa được thanh toán trong vòng một giờ") chỉ là một delayed job cộng với một cột trạng thái.
- **[CQRS saga](/recipes/cqrs#sagas)** biến event thành command trong phạm vi một process. Chúng hợp với các phản ứng mà việc mất trạng thái đang xử lý khi restart là chấp nhận được. Khi không chấp nhận được, chính các event đó có thể khởi động và gửi signal cho workflow: xem [Với CQRS](/reliability/workflows#with-cqrs).
- **Workflow** hợp với một quy trình có nhiều bước, chờ hàng giờ hoặc hàng ngày cho timer hoặc event bên ngoài, phải tồn tại qua các lần restart và deploy, và phải hoàn tác các bước đã hoàn tất khi nó thất bại hoặc bị hủy. Chúng có giới hạn đồng thời, giới hạn tần suất, độ ưu tiên và lịch chạy riêng, và một step vẫn có thể giao việc nặng cho một BullMQ queue.

Một workflow instance là một dòng trong database của ứng dụng, nên việc khởi động nó có thể là một phần của transaction lưu đơn hàng: truyền transaction cho `start()` qua tùy chọn `transaction`. Đơn hàng và việc xử lý giao hàng của nó cùng commit hoặc không commit gì cả. Một job queue ghi qua kết nối riêng của nó (Redis, hoặc pool PostgreSQL riêng của BullMQ), nên lưu một đơn hàng và đưa job của nó vào hàng đợi là hai thao tác ghi, và một lần crash ở giữa sẽ làm mất một trong hai. Signal cũng vậy: một webhook có thể cập nhật đơn hàng và đánh thức workflow của nó trong một transaction.

Bài hướng dẫn bên dưới cho thấy queue và saga không làm được tới đâu: code tiếp tục chạy sau một lần chờ bền vững ([Ngủ một tuần, rồi nhờ đánh giá](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review)), một event chạy đua với một hạn chót ([Chờ webhook giao hàng](/reliability/workflows#wait-for-the-delivery-webhook)), và việc bù trừ (compensation) tồn tại qua một lần crash ([Cho bộ phận chăm sóc khách hàng hủy đơn](/reliability/workflows#let-customer-support-cancel-an-order)).

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài dependency cần thiết:

```bash
$ npm i --save @nestjs/workflows
```

Bài hướng dẫn giữ các workflow trong PostgreSQL, với store riêng của package, và dùng Drizzle, được đăng ký qua [`@nestjs/drizzle`](/data/drizzle). [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database) cũng trình bày store với TypeORM, và store MySQL của package. Các test trên trang này dùng [PGlite](https://pglite.dev), nên không cần server.

Đơn hàng nằm trong bảng riêng của ứng dụng ví dụ, `orders`. Bài hướng dẫn dùng các bản thay thế trong bộ nhớ cho SDK của payment provider (`PaymentProviderClient`), bảng kho (`InventoryService`) và nhà cung cấp mail (`MailService`). Giống như các hệ thống thật, chúng khử trùng lặp request theo idempotency key. Đơn hàng có cấu trúc như sau:

```typescript
@@filename(orders/order)
export interface OrderItem {
  productId: string;
  quantity: number;
  /** Unit price in cents. */
  price: number;
}

/** How the carrier ships it. Express orders are fulfilled first. */
export type Shipping = 'standard' | 'express';

export type OrderStatus = 'placed' | 'delivered' | 'returned' | 'cancelled';

export interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  shipping: Shipping;
  /** In cents. */
  total: number;
  status: OrderStatus;
}

export class PlaceOrderDto {
  userId: string;
  items: OrderItem[];
  /** Default 'standard'. */
  shipping?: Shipping;
}

export interface FulfilmentResult {
  chargeId: string;
  trackingNumber: string;
}
```

##### Đăng ký module <a id="register-the-module"></a>

Import `WorkflowsModule` một lần, trong root module, cạnh [`DrizzleModule`](/data/drizzle), module đăng ký Drizzle database mà `@InjectDrizzle()` inject. Các class workflow là provider bình thường, nên chúng nằm trong `providers` cạnh các service mà chúng inject. Đây là module hoàn chỉnh: các workflow và controller mà nó liệt kê được viết ở các phần tiếp theo, và provider đầu tiên là store PostgreSQL của package, được giải thích trong [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database).

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule, getDrizzleToken } from '@nestjs/drizzle';
import { WorkflowsModule, WorkflowStorage } from '@nestjs/workflows';
import { fromDrizzle, PostgresWorkflowStore } from '@nestjs/workflows/postgres';
import { drizzle } from 'drizzle-orm/node-postgres';
import type { Database } from './database/drizzle.js';
import * as schema from './database/schema.js';
import { InventoryService } from './inventory/inventory.service.js';
import { InvoiceBatchWorkflow } from './invoices/invoice-batch.workflow.js';
import { InvoicesController } from './invoices/invoices.controller.js';
import { InvoicesService } from './invoices/invoices.service.js';
import { MailService } from './mail/mail.service.js';
import { OrderFulfilmentWorkflow } from './orders/order-fulfilment.workflow.js';
import { OrdersController } from './orders/orders.controller.js';
import { OrdersService } from './orders/orders.service.js';
import { PaymentProviderClient } from './payments/payment-provider.client.js';
import { PaymentsService } from './payments/payments.service.js';
import { CarrierWebhookController } from './shipping/carrier-webhook.controller.js';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      // Drizzle on PostgreSQL: a pg pool on DATABASE_URL, closed after the worker handed its instances back
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema }),
    }),
    WorkflowsModule.forRoot({
      worker: {
        concurrency: 10, // instances this process executes at once
        leaseDuration: '30s', // how long a crashed process keeps its instances
        shutdownTimeout: '10s', // how long a deploy waits for running steps
      },
    }),
  ],
  controllers: [OrdersController, CarrierWebhookController, InvoicesController],
  providers: [
    {
      // Instances and journals in your database, in a schema of their own (nest_workflows)
      provide: PostgresWorkflowStore,
      inject: [getDrizzleToken(), WorkflowStorage],
      useFactory: (db: Database, workflowStorage: WorkflowStorage) =>
        new PostgresWorkflowStore({ executor: fromDrizzle(db) }, workflowStorage),
    },
    OrdersService,
    PaymentProviderClient,
    PaymentsService,
    InventoryService,
    MailService,
    InvoicesService,
    OrderFulfilmentWorkflow,
    InvoiceBatchWorkflow,
  ],
})
export class AppModule {}
```

> info **Gợi ý** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để thiếu `DATABASE_URL` sẽ dừng ứng dụng ngay lúc khởi động, và đọc nó từ `ConfigService` trong factory.

Mọi tùy chọn đều không bắt buộc: `WorkflowsModule.forRoot()` dùng được ngay. Để đọc chúng từ `ConfigService`, hãy dùng `forRootAsync()` với một factory, hoặc với một class `useClass` implement `WorkflowsOptionsFactory` và method `createWorkflowsOptions()` của nó.

`worker` chạy bên trong process của ứng dụng. Nó poll các instance tới hạn mỗi giây, và một lời gọi `start()` hoặc `signal()` ở local sẽ đánh thức nó ngay lập tức. Nó claim các instance tới hạn dưới một lease và gia hạn lease mỗi một phần ba `leaseDuration`. Nếu process chết, các instance của nó có thể được claim lại khi lease hết hạn. Đặt `worker: false` cho các process chỉ nên khởi động, gửi signal và xem workflow, chẳng hạn các pod API. Một step mặc định có 3 lần thử, với backoff bắt đầu từ 1 giây và nhân đôi tới 5 phút. Một tùy chọn `retry` ở đây sẽ thay đổi mặc định đó.

Trong `main.ts`, hãy bật shutdown hook. Khi nhận `SIGTERM`, worker ngừng claim, abort `signal` của các step đang chạy, chờ tối đa `shutdownTimeout`, và trả các instance mà nó đã dừng về lại store. Khi đó một process khác sẽ nhận chúng ngay thay vì chờ hết lease.

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // On SIGTERM, stop claiming work and hand running instances back.
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

##### Giữ workflow trong database của bạn <a id="keep-workflows-in-your-database"></a>

Các workflow instance, journal của chúng, các signal mà chúng chờ và các signal đã được gửi đều nằm trong một **store**. Cho tới khi bạn đăng ký một store, module giữ chúng trong bộ nhớ: ổn cho lần chạy đầu tiên, nhưng một lần restart sẽ mất mọi đơn hàng đang chạy, và hai process không dùng chung chúng.

> warning **Cảnh báo** Với `NODE_ENV=production` và không có store nào được đăng ký, việc khởi động sẽ thất bại, trừ khi bạn đặt `allowInMemoryStorage: true`.

Trên PostgreSQL, hãy đăng ký store của package, `PostgresWorkflowStore` từ `@nestjs/workflows/postgres`. Nó chạy SQL qua database client mà ứng dụng của bạn đã có, nên có thể tham gia vào transaction của bạn. Nó là một provider bình thường, đăng ký một lần, trong root module, cạnh `WorkflowsModule`: cả hai đều có phạm vi toàn ứng dụng. Trong `AppModule` ở trên, nó là provider đầu tiên: một factory inject Drizzle database và registry `WorkflowStorage`, nơi store tự đăng ký.

`fromDrizzle(db)` là **executor** của store: nó chạy các câu lệnh của store qua Drizzle database của bạn, dù dùng driver nào, như `pg` hay PGlite. `fromPg(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` và `fromKysely(db)` làm điều tương tự cho một pool node-postgres, TypeORM, Prisma và Kysely. Lúc khởi động, module log ra `WorkflowStorage: PostgresWorkflowStore`.

**Schema.** Không cần tạo gì cho workflow: không bảng, entity hay Prisma model nào. Store giữ các bảng của nó trong một schema riêng, `nest_workflows` (tùy chọn `schema` cho phép đặt tên khác), và tự tạo cũng như migrate nó. Trên MySQL, vốn không có schema, chúng là các bảng trong database của kết nối, với tên schema làm tiền tố: `nest_workflows_instances` và các bảng tương tự.

| Bảng | Chứa gì |
| --- | --- |
| `nest_workflows.instances` | Mỗi workflow instance: input, trạng thái, output hoặc lỗi, thời điểm tới hạn, và lease của nó |
| `nest_workflows.journal` | Các step, sleep, wait và compensation đã ghi lại của mỗi instance, kèm kết quả |
| `nest_workflows.waits` | Các signal mà một instance đang tạm dừng chờ |
| `nest_workflows.signals` | Các signal đã được gửi, cho tới khi `purge()` xóa những signal không còn instance nào nhận được |
| `nest_workflows.schedules` | Các lịch chạy, kèm spec, trạng thái và lần chạy tiếp theo |
| `nest_workflows.rate_limits` | Các cửa sổ rate-limit, theo workflow và key |
| `nest_workflows.migrations` | Các phiên bản schema của store đã được áp dụng |

Chúng thuộc về store: migration của bạn không tạo chúng, và các bảng của bạn không thể trùng tên với chúng.

**Migration.** Package đi kèm schema dưới dạng các migration có phiên bản, và store tự áp dụng chúng. Với tùy chọn `migrate`, nó áp dụng những migration mà schema chưa có lúc khởi động, trước khi worker chạy, trong một transaction giữ một advisory lock: trong nhiều process khởi động cùng lúc, một process migrate, và các process khác thấy không còn gì để làm. `migrate` mặc định là `true`, trừ khi `NODE_ENV=production`. Vì vậy trong development và test, store tạo schema ở lần khởi động đầu tiên, và migration của bạn chỉ tạo các bảng của riêng bạn, ở đây là `orders`.

Trong production, hãy áp dụng migration trước khi phiên bản mới của ứng dụng khởi động, giống như cách bạn áp dụng migration của mình, để không process nào thay đổi schema trong lúc boot: giữa một lần rolling deploy, việc đó sẽ khóa các bảng đang bận, và một database user có quyền tối thiểu cũng không thể làm điều đó. Command line của package làm việc này từ bước deploy của bạn, cạnh `npx drizzle-kit migrate`. Nó đọc database từ `DATABASE_URL`, hoặc từ `--url`, và cần cài `pg`:

```bash
$ npx @nestjs/workflows status
Schema "nest_workflows" is at version 0; this version of @nestjs/workflows needs version 1.
$ npx @nestjs/workflows migrate
Migrated schema "nest_workflows" to version 1 (applied 1).
```

`status` thoát với mã 1 khi schema còn chậm phiên bản, nên nó có thể dùng làm bước kiểm tra trong CI. Để áp dụng migration bằng công cụ migration của riêng bạn, hãy lấy SQL của chúng từ `npx @nestjs/workflows sql`, hoặc từ `PostgresWorkflowStore.migrationSql()` trong code: các câu lệnh của mọi migration, mỗi đoạn một câu, kèm phần ghi chép phiên bản. Chạy chúng trong một transaction, như migrator của TypeORM và Drizzle làm. Với TypeORM, đó là một migration của riêng bạn, cạnh các migration mà nó sinh ra cho entity của bạn:

```typescript
@@filename(typeorm/migrations/1790801342207-WorkflowStore)
import { PostgresWorkflowStore } from '@nestjs/workflows/postgres';
import type { MigrationInterface, QueryRunner } from 'typeorm';

export class WorkflowStore1790801342207 implements MigrationInterface {
  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(PostgresWorkflowStore.migrationSql());
  }

  async down(): Promise<void> {
    throw new Error('The workflow store has no down migrations.');
  }
}
```

Với drizzle-kit, hãy tạo một custom migration, và điền SQL vào file nó tạo ra, với một dòng `--> statement-breakpoint` giữa các câu lệnh: khi đó migrator của Drizzle sẽ chạy từng câu một, điều mà PGlite yêu cầu. Trong code, `migrationSql()` với `statementBreakpoints: true` trả về kết quả tương tự.

```bash
$ npx drizzle-kit generate --custom --name=workflows
$ npx @nestjs/workflows sql --statement-breakpoints > drizzle/20261103120000_workflows/migration.sql
```

Trên MySQL, `MySqlWorkflowStore.migrationStatements()` trả về các câu lệnh, mỗi chuỗi một câu, và một migration TypeORM chạy chúng mỗi lời gọi một câu:

```typescript
@@filename(typeorm/mysql-migrations/1790801342207-WorkflowStore)
for (const statement of MySqlWorkflowStore.migrationStatements()) {
  await queryRunner.query(statement);
}
```

Khi tắt `migrate`, một store có schema chậm phiên bản sẽ làm việc khởi động thất bại với một `WorkflowSchemaError` nêu ra ba cách này, và làm mọi lời gọi thất bại theo cùng cách cho tới khi schema được cập nhật, điều mà nó tự nhận ra mà không cần restart. Migration chỉ thêm bảng, cột và index, nên trong một lần rolling deploy, phiên bản trước của ứng dụng vẫn tiếp tục chạy trên schema đã migrate. Không có down migration.

**Transaction.** `start()` và `signal()` nhận transaction của bạn qua tùy chọn `transaction`: với Drizzle, đó là `tx` mà `db.transaction()` truyền cho callback của nó, như [Khởi động nó cùng đơn hàng](/reliability/workflows#start-it-with-the-order) trình bày. Store chạy các câu lệnh của nó trên transaction đó, nên chúng commit hoặc rollback cùng các thao tác ghi của bạn. Nó từ chối chính database, vì các câu lệnh trên đó sẽ tự commit riêng, bằng một `TypeError` cho biết cần truyền gì. Với các executor khác, hãy truyền một client node-postgres sau `BEGIN` (không phải pool), `EntityManager` của TypeORM từ `dataSource.transaction()`, interactive transaction client của Prisma, hoặc một Kysely transaction.

**Isolation.** Store dựa vào READ COMMITTED, isolation level mặc định của PostgreSQL: các câu lệnh của nó chạy đua với nhau, và dưới một level chặt hơn chúng sẽ thất bại với lỗi serialization. Lúc khởi động, nó kiểm tra `default_transaction_isolation` của database, và thất bại nếu nó chặt hơn. Một `signal()` trong transaction của bạn cũng cần một transaction READ COMMITTED, nếu không các lần đánh thức của nó có thể bỏ lỡ những wait được commit sau snapshot của transaction: nếu không thỏa điều kiện, nó bị từ chối bằng một `TypeError`.

**Với TypeORM.** `TypeOrmModule` thay thế `DrizzleModule` trong `AppModule`, và store chạy trên `DataSource` mà nó cung cấp, qua `fromTypeOrm()`:

```typescript
@@filename(typeorm/app.module)
{
  // Instances and journals in your database, in a schema of their own (nest_workflows)
  provide: PostgresWorkflowStore,
  inject: [DataSource, WorkflowStorage],
  useFactory: (dataSource: DataSource, workflowStorage: WorkflowStorage) =>
    new PostgresWorkflowStore({ executor: fromTypeOrm(dataSource) }, workflowStorage),
},
```

Ở chỗ bài hướng dẫn truyền `tx` của Drizzle cho `start()` và `signal()`, hãy truyền `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó. Store từ chối `dataSource.manager`, vì các thao tác ghi trên đó sẽ tự commit riêng. Đây là `place()` của order service, từ [Khởi động nó cùng đơn hàng](/reliability/workflows#start-it-with-the-order), với TypeORM:

```typescript
@@filename(typeorm/orders.service)
return this.dataSource.transaction(async (manager) => {
  await manager.insert(OrderEntity, order);
  // Same transaction: the fulfilment exists if and only if the order does.
  const fulfilment = await this.workflowClient.start(OrderFulfilmentWorkflow, order, {
    id: fulfilmentId(order.id),
    transaction: manager,
  });
  return { ...order, fulfilment };
});
```

> info **Gợi ý** Với Prisma, hãy truyền client cho `fromPrisma()`, và truyền làm `transaction` chính transaction client mà `prisma.$transaction()` đưa cho callback của nó. Các transaction riêng của store chờ kết nối tối đa 10 giây và chạy tối đa một phút, lâu hơn mặc định của Prisma: tham số thứ hai của `fromPrisma()` thay đổi điều đó, với `maxWait` và `timeout`. Nếu ứng dụng của bạn gửi signal theo từng đợt dồn dập, hãy cho các transaction riêng của ứng dụng một `maxWait` dài hơn nữa, vì các signal xếp hàng chờ nhau.

**Với MySQL.** Package cũng có một store cho MySQL 8.4 LTS và 9.x, `MySqlWorkflowStore` từ `@nestjs/workflows/mysql`, với các executor cùng tên. MariaDB hiện chưa được hỗ trợ: store từ chối nó lúc khởi động. Provider giống nhau, chỉ khác class store và executor của MySQL. Đây là `AppModule` với Drizzle trên một pool mysql2, trong đó `mode: 'default'` là thiết lập của Drizzle cho schema trên MySQL:

```typescript
@@filename(mysql/app.module)
import { fromDrizzle, MySqlWorkflowStore } from '@nestjs/workflows/mysql';
import { drizzle } from 'drizzle-orm/mysql2';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      // Drizzle on MySQL: a mysql2 pool on DATABASE_URL (mysql://...), whose path names the database
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema, mode: 'default' as const }),
    }),
    // ...
  ],
  providers: [
    {
      // Instances and journals in your database, in tables of their own (nest_workflows_*)
      provide: MySqlWorkflowStore,
      inject: [getDrizzleToken(), WorkflowStorage],
      useFactory: (db: Database, workflowStorage: WorkflowStorage) =>
        new MySqlWorkflowStore({ executor: fromDrizzle(db) }, workflowStorage),
    },
    // ...
  ],
})
export class AppModule {}
```

`fromMysql2(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` và `fromKysely(db)` làm điều tương tự cho một pool mysql2, TypeORM, Prisma (qua `@prisma/adapter-mariadb`) và Kysely. `start()` và `signal()` nhận cùng các transaction object như trên PostgreSQL, và với mysql2, là một connection sau `beginTransaction()`. Những điểm khác so với PostgreSQL:

- **Các bảng.** MySQL không có schema bên trong một database, nên store giữ các bảng của nó trong database của kết nối, database mà phần path của URL chỉ định, và tùy chọn `schema` là tiền tố trong tên của chúng: `nest_workflows_instances`, `nest_workflows_signals` và các bảng tương tự, cạnh `nest_workflows_migrations` và `nest_workflows_locks`, nơi chứa các phiên bản và các lock của nó.
- **Key có giới hạn.** Id, tên và key là các cột có index với độ dài giới hạn. Một instance id, một tên workflow hoặc signal, `key` và `id` của một signal, và một key concurrency hoặc rate-limit chứa được 255 ký tự, một schedule id là 230, và một tên step, sleep hoặc wait là 512. `start()` và `signal()` từ chối một giá trị dài hơn bằng `RangeError` trước khi ghi bất cứ thứ gì. Key vẫn được so sánh chính xác, như trên PostgreSQL.
- **Transaction của bạn.** `start()` và `signal()` với tùy chọn `transaction` hoạt động ở REPEATABLE READ, mặc định của MySQL, và ở READ COMMITTED: việc đánh thức đọc các wait bằng một locking read, cách đọc này cũng thấy những wait được commit sau snapshot của transaction của bạn. Tránh SERIALIZABLE, nơi MySQL biến các lần đọc thường thành locking read: một `start()` trong transaction như vậy sẽ giữ lại mọi signal cho tới khi transaction kết thúc.
- **Deadlock.** MySQL phá một deadlock bằng cách rollback một trong các transaction, với lỗi 1213 (`ER_LOCK_DEADLOCK`). Store tự chạy lại các transaction riêng của nó. Trong transaction của bạn, việc rollback cũng đã lấy đi các thao tác ghi của bạn, nên lỗi tới được code của bạn: hãy chạy lại transaction. Một transaction ghi một đơn hàng rồi gửi signal, trong khi một transaction khác gửi signal rồi ghi cùng đơn hàng đó, sẽ bị deadlock theo cách đó.
- **Migration.** MySQL tự commit từng câu lệnh DDL, nên các migration không thể chạy trong một transaction. Store và `npx @nestjs/workflows migrate` áp dụng chúng từng câu lệnh một, dưới một lock (`GET_LOCK()`), nên các process khởi động cùng lúc vẫn chỉ migrate một lần, và một lần chạy bị dừng giữa chừng sẽ tiếp tục từ chỗ nó đã dừng. Command line nhận một URL `mysql://` và khi đó cần `mysql2`, còn `npx @nestjs/workflows sql --dialect mysql` in ra SQL. Với công cụ của riêng bạn, hãy áp dụng các câu lệnh theo thứ tự, mỗi câu một lần, mỗi lời gọi một câu, như migration TypeORM ở trên làm: với drizzle-kit, vốn có migrator MySQL gửi mỗi breakpoint một câu lệnh, hãy thêm `--statement-breakpoints`.

Với một database khác, hãy tự viết store: [Hợp đồng của store](/reliability/workflows#the-store-contract) cho biết nó phải làm gì.

#### Viết workflow <a id="write-the-workflow"></a>

Mọi side effect đều cần một idempotency key. Một step chạy **ít nhất một lần**: nếu process chết sau khi payment provider đã trừ tiền thẻ nhưng trước khi kết quả tới được journal, step sẽ chạy lại. Engine giao cho mỗi step một `idempotencyKey` giữ nguyên qua các lần thử và các process (`<instance id>:<step name>`). Hãy truyền nó cho hệ thống bạn gọi, và tác động sẽ chỉ xảy ra một lần:

```typescript
@@filename(payments/payments.service)
import { Injectable } from '@nestjs/common';
import { NonRetryableStepError } from '@nestjs/workflows';
import type { Order } from '../orders/order.js';
import { PaymentProviderClient } from './payment-provider.client.js';

export interface Charge {
  chargeId: string;
  amount: number;
}

@Injectable()
export class PaymentsService {
  constructor(private readonly paymentProviderClient: PaymentProviderClient) {}

  async charge(order: Order, idempotencyKey: string): Promise<Charge> {
    // The payment provider answers a repeated Idempotency-Key with the first response,
    // so a retried step never charges the card twice.
    const charge = await this.paymentProviderClient.createCharge(
      { amount: order.total, currency: 'USD', reference: order.id },
      { idempotencyKey },
    );
    if (charge.status === 'declined') {
      // Retrying won't help. Fail the step now.
      throw new NonRetryableStepError(`The payment provider declined the card for order ${order.id}.`);
    }
    return { chargeId: charge.id, amount: charge.amount };
  }

  async refund(chargeId: string, idempotencyKey: string): Promise<void> {
    await this.paymentProviderClient.createRefund({ chargeId }, { idempotencyKey });
  }
}
```

`InventoryService.reserve()` theo cùng ý tưởng mà không cần API bên ngoài: nó dùng key làm primary key của lần giữ chỗ, nên một lần retry sẽ tìm thấy lần giữ chỗ nó đã tạo. Nó throw `NonRetryableStepError` khi một sản phẩm hết hàng. `MailService` truyền key cho nhà cung cấp mail làm message id.

Giờ đến workflow. Gắn `@Workflow()` cho một class, đặt tên cho nó, và implement `run()`:

```typescript
@@filename(orders/order-fulfilment.workflow)
import { Workflow, type WorkflowContext, type WorkflowRunner } from '@nestjs/workflows';
import { InventoryService } from '../inventory/inventory.service.js';
import { MailService } from '../mail/mail.service.js';
import { PaymentsService } from '../payments/payments.service.js';
import { shipmentDelivered } from '../shipping/carrier-event.js';
import type { FulfilmentResult, Order } from './order.js';

/** One fulfilment per order: the order id is the workflow instance id. */
export const fulfilmentId = (orderId: string) => `order-${orderId}`;

@Workflow('order-fulfilment')
export class OrderFulfilmentWorkflow implements WorkflowRunner<Order, FulfilmentResult> {
  constructor(
    private readonly paymentsService: PaymentsService,
    private readonly inventoryService: InventoryService,
    private readonly mailService: MailService,
  ) {}

  async run(ctx: WorkflowContext, order: Order): Promise<FulfilmentResult> {
    const charge = await ctx.step(
      'charge-payment',
      ({ idempotencyKey }) => this.paymentsService.charge(order, idempotencyKey),
      {
        retry: { attempts: 5, backoff: { delay: '2s' } },
        compensate: (charge, { idempotencyKey }) => this.paymentsService.refund(charge.chargeId, idempotencyKey),
      },
    );

    await ctx.step(
      'reserve-stock',
      ({ idempotencyKey }) => this.inventoryService.reserve(order.items, idempotencyKey),
      { compensate: ({ reservationId }) => this.inventoryService.release(reservationId) },
    );

    // ...the delivery wait and the review request continue here
  }
}
```

`ctx.step()` chạy hàm một lần và ghi kết quả của nó vào journal. Mỗi khi instance chạy lại (sau một wait, một sleep hoặc một lần crash), `run()` bắt đầu từ đầu và `charge-payment` trả về lần trừ tiền đã ghi journal mà không gọi payment provider. Kết quả phải serialize được sang JSON, và chúng trả về ở dạng JSON, kể cả ở lần chạy đầu tiên: một `Date` là một chuỗi. Return type nói rõ điều đó (`Journaled<Charge>`), nên TypeScript sẽ báo lỗi code coi một giá trị đã ghi journal như một object sống.

- **`retry`**: `attempts` tính cả lần thử đầu tiên, và `backoff` đặt thời gian chờ trước mỗi lần retry: một `delay`, một hệ số tăng `factor`, một mức trần `maxDelay` và `jitter` tùy chọn. Một con số là cách viết tắt cho số lần thử, và `false` nghĩa là chỉ thử một lần. Một lần thử thất bại sẽ đỗ instance lại cho tới khi hết thời gian backoff, nên một lần retry cũng tồn tại qua một lần restart. Một `NonRetryableStepError`, chẳng hạn thẻ bị từ chối, làm step thất bại ngay lập tức.
- **`compensate`**: được đăng ký khi step hoàn tất. Nếu sau đó workflow thất bại hoặc bị hủy, các compensation của các step đã hoàn tất sẽ chạy theo thứ tự ngược lại. Mỗi compensation được ghi journal và retry như một step, với idempotency key riêng. Nếu `reserve-stock` thất bại vì một sản phẩm hết hàng, tiền sẽ được hoàn lại. [Ngủ một tuần, rồi nhờ đánh giá](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review) cho thấy cách chấm dứt điều này khi đơn hàng đã được giao.

Các step cũng có thể chạy song song. Để giữ chỗ từng sản phẩm riêng, hãy khởi động mỗi sản phẩm một step và chờ chúng cùng nhau. Mỗi step có tên riêng, chứa index của sản phẩm, và vì vậy có idempotency key và compensation riêng:

```typescript
@@filename(orders/order-fulfilment.workflow)
// One step per item, all at once: each reserves its item under its own key, and
// releases it if the order is undone.
await Promise.all(
  order.items.map((item, i) =>
    ctx.step(
      `reserve-item-${i}`,
      ({ idempotencyKey }) => this.inventoryService.reserve([item], idempotencyKey),
      { compensate: ({ reservationId }) => this.inventoryService.release(reservationId) },
    ),
  ),
);
```

Nếu một sản phẩm hết hàng, step của nó thất bại, các step khác vẫn hoàn tất, và compensation của những step đã hoàn tất sẽ chạy: các lần giữ chỗ được giải phóng, rồi tiền được hoàn lại. Compensation chạy theo thứ tự ngược với các lời gọi `ctx.step()`, bất kể step nào xong trước. Phần còn lại của bài hướng dẫn giữ nguyên step `reserve-stock` duy nhất.

Class là một singleton được dùng chung bởi mọi đơn hàng đang chạy, và constructor injection hoạt động như thường. Hãy giữ trạng thái theo từng đơn hàng trong các biến cục bộ, không bao giờ đặt trên `this`.
#### Khởi động workflow <a id="start-the-workflow"></a>

##### Khởi động nó cùng đơn hàng <a id="start-it-with-the-order"></a>

Một đơn hàng và việc xử lý giao hàng của nó đi liền với nhau: một đơn hàng không có gì xử lý cũng tệ như một quy trình giao hàng trừ tiền cho một đơn hàng chưa bao giờ được lưu. Vì vậy `OrdersService` lưu đơn hàng và khởi động workflow trong một Drizzle transaction. `WorkflowClient` khởi động các instance; hãy truyền cho nó `tx` của transaction:

```typescript
@@filename(orders/orders.service)
import { randomUUID } from 'node:crypto';
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { WorkflowClient } from '@nestjs/workflows';
import { eq } from 'drizzle-orm';
import type { Database } from '../database/drizzle.js';
import { orders } from '../database/schema.js';
import { fulfilmentId, OrderFulfilmentWorkflow } from './order-fulfilment.workflow.js';
import type { Order, PlaceOrderDto } from './order.js';

@Injectable()
export class OrdersService {
  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly workflowClient: WorkflowClient,
  ) {}

  async place(dto: PlaceOrderDto) {
    const total = dto.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const order: Order = {
      id: randomUUID().slice(0, 8),
      userId: dto.userId,
      items: dto.items,
      shipping: dto.shipping ?? 'standard',
      total,
      status: 'placed',
    };

    return this.db.transaction(async (tx) => {
      await tx.insert(orders).values(order);
      // Same transaction: the fulfilment exists if and only if the order does.
      const fulfilment = await this.workflowClient.start(OrderFulfilmentWorkflow, order, {
        id: fulfilmentId(order.id),
        transaction: tx,
      });
      return { ...order, fulfilment };
    });
  }

  async findOne(id: string): Promise<Order> {
    const [order] = await this.db.select().from(orders).where(eq(orders.id, id));
    if (!order) {
      throw new NotFoundException(`Order ${id} not found.`);
    }
    return order;
  }

  // ...markDelivered() is added in the next section
}
```

Với `transaction`, store tạo instance qua transaction mà ORM của bạn đã đưa cho callback, nên nó commit cùng đơn hàng, hoặc rollback cùng đơn hàng nếu có gì đó phía sau trong callback thất bại. Worker chỉ thấy các instance đã commit: nó nhận instance này ở lần poll tiếp theo sau khi commit. Hãy truyền transaction, không phải database, thứ mà store sẽ từ chối: `start()` không có tùy chọn này sẽ ghi một cách độc lập, chính là việc dual write mà tùy chọn này loại bỏ. Với TypeORM, hãy truyền `EntityManager` của transaction, và với Prisma, là transaction client, như [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database) trình bày.

Instance id lấy từ id đơn hàng, điều này khiến `start()` trở nên idempotent. Khởi động cùng id với cùng input sẽ trả về instance đã có với `created: false`, còn một input khác sẽ throw `WorkflowIdConflictError`. Một job đối soát có thể gọi lại nó cho một đơn hàng mà không trừ tiền hai lần.

##### Báo cáo trạng thái <a id="report-its-status"></a>

Controller đặt đơn hàng và báo cáo việc xử lý giao hàng đang ở đâu:

```typescript
@@filename(orders/orders.controller)
import { Body, Controller, Get, NotFoundException, Param, Post } from '@nestjs/common';
import { WorkflowClient } from '@nestjs/workflows';
import { fulfilmentId } from './order-fulfilment.workflow.js';
import { PlaceOrderDto } from './order.js';
import { OrdersService } from './orders.service.js';

@Controller('orders')
export class OrdersController {
  constructor(
    private readonly ordersService: OrdersService,
    private readonly workflowClient: WorkflowClient,
  ) {}

  @Post()
  place(@Body() dto: PlaceOrderDto) {
    return this.ordersService.place(dto);
  }

  @Get(':id/fulfilment')
  async fulfilment(@Param('id') id: string) {
    const instance = await this.workflowClient.getStatus(fulfilmentId(id), { journal: true });
    if (!instance) {
      throw new NotFoundException(`Order ${id} not found.`);
    }
    return {
      status: instance.status,
      stage: instance.customStatus,
      waitingFor: instance.waits.map((wait) => wait.signal),
      wakeAt: instance.wakeAt === null ? null : new Date(instance.wakeAt).toISOString(),
      steps: Object.fromEntries(instance.journal.map((entry) => [entry.name, entry.status])),
      error: instance.error?.message ?? null,
    };
  }

  // ...cancel() is added for customer support, below
}
```

`getStatus()` trả về instance: `status`, `wakeAt`, các signal mà nó `waits`, `error` hoặc `output` của nó, và, với tùy chọn `journal`, mọi step. Các trạng thái là `pending`, `running`, `suspended`, `compensating`, `completed`, `failed`, `cancelled` và `compensation_failed`; [Ý nghĩa của từng trạng thái](/reliability/workflows#what-each-status-means) cho biết mỗi trạng thái nghĩa là gì và cần làm gì với nó. Endpoint map instance sang một view nhỏ. Đừng trả instance thô cho khách hàng, vì nó chứa input và chi tiết lease.

`stage` đến từ workflow. `ctx.setStatus()` đặt **custom status** của instance, một giá trị JSON tối đa 16 KiB mà `getStatus()` và `list()` trả về dưới tên `customStatus`: ở đây, là một từ mô tả đơn hàng đang ở đâu. Hãy đặt nó trong `run()` khi đơn hàng tiến triển, và đặt thành `delivered` khi đơn vị vận chuyển đã giao hàng (trong [Ngủ một tuần, rồi nhờ đánh giá](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review)):

```typescript
@@filename(orders/order-fulfilment.workflow)
const charge = await ctx.step(
  'charge-payment',
  // ...the charge, as above
);
ctx.setStatus('paid');

await ctx.step(
  'reserve-stock',
  // ...the reservation, as above
);
ctx.setStatus('awaiting-delivery');
```

Status không được ghi journal. Mỗi lần thực thi đều replay `run()`, và cùng với nó là các lời gọi `setStatus()`, nên mỗi lần thực thi lại đặt status trên đường nó đi qua, và một status được đặt trong vòng lặp không làm journal phình ra. Workflow không bao giờ đọc lại nó, nên không có quyết định nào của workflow phụ thuộc vào nó. Nó được ghi cùng lần ghi tiếp theo của instance: khi step tiếp theo bắt đầu, khi instance đỗ lại, hoặc khi nó kết thúc. Vì vậy endpoint hiển thị `paid` trong khi `reserve-stock` chờ retry, và `awaiting-delivery` khi instance đỗ lại chờ đơn vị vận chuyển. Một status mà workflow không còn thay đổi sẽ được giữ nguyên, chẳng hạn `awaiting-delivery` trên một đơn hàng đã bị hủy: `status` cho biết điều gì đã xảy ra. Một giá trị không phải JSON, hoặc chiếm hơn 16 KiB dưới dạng JSON, sẽ làm instance thất bại với một `TypeError`, còn `undefined` sẽ xóa status. Mỗi thay đổi được ghi sẽ được phát ra dưới dạng event `custom-status`.

#### Chờ signal và timer <a id="wait-for-signals-and-timers"></a>

##### Chờ webhook giao hàng <a id="wait-for-the-delivery-webhook"></a>

Tiếp theo, workflow chờ đơn vị vận chuyển. Webhook và workflow dùng chung một signal: một tên và type của payload, định nghĩa một lần, để không bên nào gõ sai tên hay gửi sai cấu trúc:

```typescript
@@filename(shipping/carrier-event)
import { WorkflowSignal } from '@nestjs/workflows';

/** The body the carrier POSTs to our webhook. */
export interface CarrierEvent {
  type: 'shipment.in_transit' | 'shipment.delivered' | 'shipment.returned';
  /** The store's order id. */
  reference: string;
  trackingNumber: string;
  occurredAt: string;
}

/** Sent by the webhook, awaited by the fulfilment workflow. The order id is its key. */
export const shipmentDelivered = new WorkflowSignal<CarrierEvent>('shipment.delivered');
```

Thêm đoạn này vào `run()`, sau `reserve-stock`:

```typescript
@@filename(orders/order-fulfilment.workflow)
const delivery = await ctx.waitForSignal('await-delivery', shipmentDelivered, {
  key: order.id,
  timeout: '3d',
});
if (!delivery) {
  ctx.fail(`Order ${order.id} was not delivered within 3 days.`);
}
```

`waitForSignal()` ghi lại lần chờ và đỗ instance lại: trạng thái của nó chuyển thành `suspended` và `wakeAt` là hạn chót. Không có bộ nhớ, timer hay worker nào bị giữ trong 3 ngày đó. Nó resolve với payload của signal, có type `CarrierEvent`, hoặc với `null` khi hết thời gian timeout. Khi đó `ctx.fail()` làm instance thất bại, và các compensation chạy theo thứ tự ngược: hàng trong kho được giải phóng, rồi tiền được hoàn lại. Tùy chọn `match` lọc thêm các signal theo payload, chẳng hạn `match: (event) => event.trackingNumber !== ''`; nó chạy lại ở mỗi lần replay, nên phải là một pure function của payload.

Webhook đánh dấu đơn hàng đã được giao và gửi signal. Cả hai diễn ra trong một method mới `OrdersService.markDelivered()`, trong một transaction, nên trạng thái đơn hàng và signal cùng commit. Hãy thêm nó, cùng với import của signal:

```typescript
@@filename(orders/orders.service)
import { shipmentDelivered, type CarrierEvent } from '../shipping/carrier-event.js';

async markDelivered(event: CarrierEvent): Promise<void> {
  await this.db.transaction(async (tx) => {
    const updated = await tx
      .update(orders)
      .set({ status: 'delivered' })
      .where(eq(orders.id, event.reference))
      .returning({ id: orders.id });
    if (updated.length === 0) {
      throw new NotFoundException(`Order ${event.reference} not found.`);
    }
    // The order's new status and the signal commit together.
    await this.workflowClient.signal(shipmentDelivered, event, { key: event.reference, transaction: tx });
  });
}
```

Controller xác minh callback và chuyển nó đi:

```typescript
@@filename(shipping/carrier-webhook.controller)
import { Body, Controller, HttpCode, Post } from '@nestjs/common';
import { OrdersService } from '../orders/orders.service.js';
import type { CarrierEvent } from './carrier-event.js';

@Controller('webhooks/carrier')
export class CarrierWebhookController {
  constructor(private readonly ordersService: OrdersService) {}

  @Post()
  @HttpCode(200)
  async handle(@Body() event: CarrierEvent) {
    // Verify the carrier's signature header before trusting the body.
    if (event.type === 'shipment.delivered') {
      await this.ordersService.markDelivered(event);
    }
    return { received: true };
  }
}
```

`signal()` lưu signal với một `key` dùng để liên kết và đánh thức các instance đang chờ signal và key đó. Key được so khớp chính xác, nên id đơn hàng giúp việc giao hàng của đơn này không đánh thức đơn khác, và một lần chờ không có key chỉ nhận các signal được gửi không kèm key. Signal là bền vững. Một webhook tới trước khi workflow chạm tới lần chờ vẫn được tính, và mỗi signal được tiêu thụ tối đa một lần cho mỗi instance, nên các lần retry của đơn vị vận chuyển là vô hại. Tuy vậy mỗi lần retry vẫn lưu một signal, trừ khi bạn truyền một `id`, chẳng hạn mã vận đơn: một signal có cùng tên và `id` chỉ được lưu một lần, và một lần lặp lại sẽ trả về `signalId` của signal đầu tiên với `created: false`. Một lần giao hàng được ghi nhận sau hạn chót sẽ thua timeout, kể cả khi không có worker nào đang chạy lúc hạn chót trôi qua.

Controller chỉ trả lời `200` sau khi transaction đã commit. Một lần giao hàng cho đơn hàng mà store không biết sẽ rollback với `404`, không để lại signal nào, và nếu database lỗi, đơn vị vận chuyển nhận một lỗi và gửi lại webhook. Các signal được gửi trong một transaction xếp hàng chờ nhau cho tới khi transaction kết thúc, nên hãy giữ các transaction như vậy ngắn gọn. Trên PostgreSQL, transaction phải dùng isolation mặc định READ COMMITTED; store từ chối một level chặt hơn, vì nó có thể bỏ lỡ một lần chờ được đăng ký trong lúc transaction chạy. Trên MySQL, REPEATABLE READ mặc định cũng dùng được.

##### Chờ thứ nào tới trước <a id="wait-for-whichever-comes-first"></a>

Đơn vị vận chuyển không phải lúc nào cũng giao được hàng. Khi không giao được, họ mang kiện hàng về kho và báo `shipment.returned`. Khai báo signal thứ hai, cạnh signal đầu tiên:

```typescript
@@filename(shipping/carrier-event)
/** Sent by the webhook when the carrier brings the parcel back to the warehouse. The order id is its key. */
export const shipmentReturned = new WorkflowSignal<CarrierEvent>('shipment.returned');
```

Webhook gửi nó giống như gửi việc giao hàng. Một method mới `OrdersService.markReturned()` đặt trạng thái đơn hàng thành `returned` và gửi signal, trong một transaction, giống `markDelivered()`:

```typescript
@@filename(shipping/carrier-webhook.controller)
if (event.type === 'shipment.returned') {
  await this.ordersService.markReturned(event);
}
```

Giờ workflow chờ việc giao hàng, việc trả hàng hoặc 3 ngày, thứ nào tới trước. Thay lời gọi `waitForSignal()` bằng `ctx.waitForAny()`:

```typescript
@@filename(orders/order-fulfilment.workflow)
const outcome = await ctx.waitForAny('await-delivery', {
  delivered: ctx.signalWait(shipmentDelivered, { key: order.id }),
  returned: ctx.signalWait(shipmentReturned, { key: order.id }),
  timedOut: ctx.timer('3d'),
});
if (outcome.key === 'returned') {
  ctx.fail(`The carrier returned order ${order.id} to the warehouse.`);
}
if (outcome.key === 'timedOut') {
  ctx.fail(`Order ${order.id} was not delivered within 3 days.`);
}
const delivery = outcome.value;
```

`ctx.signalWait()` và `ctx.timer()` chỉ mô tả một điều kiện, và `waitForAny()` chờ chúng cùng nhau. Nó đỗ instance lại một lần, với mọi signal mà nó chờ và hạn chót sớm nhất, và resolve với `key` của điều kiện xảy ra trước cùng `value` của nó: payload của một signal, hoặc `null` cho một timer. Kiểm tra `key` sẽ thu hẹp type của `value`, nên sau hai lần kiểm tra `delivery` là một `CarrierEvent`. Một kiện hàng bị trả về làm instance thất bại, và các compensation giải phóng hàng trong kho, vốn đã quay về kho, và hoàn tiền. `waitingFor` của endpoint trạng thái liệt kê cả hai signal trong khi instance chờ.

Kết quả được ghi journal thành một entry dưới tên của lần chờ, nên mọi lần thực thi sau đều nhận cùng bên thắng. Khi nhiều điều kiện cùng sẵn sàng một lúc, signal được ghi nhận trước sẽ thắng, bất kể nó khớp với điều kiện nào. Một signal được gửi sau hạn chót của một timer không được tính, giống như `timeout` của `waitForSignal()`, và timer được tính từ lúc lần chờ được chạm tới lần đầu. Chỉ signal thắng mới được lấy: một lần trả hàng được báo sau việc giao hàng sẽ ở lại cho một lần chờ sau của cùng instance. Để chờ tất cả trong nhiều signal, hãy await nhiều lời gọi `waitForSignal()` với `Promise.all()`: mỗi lời gọi được ghi journal riêng, và instance đỗ lại một lần cho tất cả. Một child workflow cũng có thể là một điều kiện, như [Khởi động child workflow](/reliability/workflows#start-child-workflows) trình bày.

##### Ngủ một tuần, rồi nhờ đánh giá <a id="sleep-for-a-week-then-ask-for-a-review"></a>

Kết thúc `run()` bằng điểm không thể quay lại, một timer bền vững và step cuối cùng:

```typescript
@@filename(orders/order-fulfilment.workflow)
// Point of no return: the parcel arrived, so nothing from here on refunds
// the charge or releases the stock, not a failure and not a cancel.
ctx.commit('delivered');
ctx.setStatus('delivered');

await ctx.sleep('before-review-request', '7d');
await ctx.step('send-review-request', ({ idempotencyKey }) =>
  this.mailService.sendReviewRequest(order, idempotencyKey),
);

return { chargeId: charge.chargeId, trackingNumber: delivery.trackingNumber };
```

`ctx.sleep()` lưu một thời điểm đánh thức và đỗ instance lại, giống như lần chờ. Sau 7 ngày, bất kỳ worker nào cũng sẽ tiếp tục nó: không bao giờ sớm hơn, và thường trong vòng một khoảng poll tính từ hạn chót. Khi tiếp tục, `run()` replay từ đầu: `charge-payment` và `await-delivery` trả về các giá trị đã ghi journal, nên `charge` và `delivery` vẫn nằm trong phạm vi một tuần sau đó. Một delayed job không thể cho bạn sự tiếp nối này. Để ngủ tới một thời điểm cụ thể, hãy truyền một object có `until`, là một `Date` hoặc epoch tính bằng mili giây, được tính từ các giá trị đã ghi journal như `ctx.now()`.

`ctx.commit()` đánh dấu điểm không thể quay lại. Khi kiện hàng đã được giao, hoàn tiền sẽ là sai, bất kể điều gì xảy ra tiếp theo. `commit()` loại bỏ các compensation đã đăng ký cho tới thời điểm đó. Nếu sau đó email đánh giá thất bại vĩnh viễn, instance kết thúc ở trạng thái `failed` với lỗi của step, và không có gì được hoàn tiền hay giải phóng. Một lần hủy sau điểm này cũng không hoàn tác gì cả. Chỉ các step sau `commit()` mới đăng ký các compensation còn có thể chạy. Điểm commit được ghi journal dưới tên của nó, nên nó replay như một step, và endpoint trạng thái liệt kê nó là `delivered`.

##### Timeout cho toàn bộ workflow <a id="time-out-the-whole-workflow"></a>

`timeout` của một lần chờ giới hạn một lần chờ, và `timeout` của một step giới hạn một lần thử. Để giới hạn toàn bộ một instance, hãy cho workflow một run timeout:

```typescript
@Workflow('order-fulfilment', { timeout: '30d' })
```

Hạn chót là thời điểm instance bắt đầu cộng với timeout, được lưu cùng instance dưới dạng `deadline` của nó, nên nó giữ nguyên qua các lần restart và deploy, và một instance đang đỗ sẽ thức dậy vì nó kể cả khi lần sleep hoặc wait của nó sẽ kết thúc muộn hơn. Khi hạn chót trôi qua, instance dừng ở lời gọi `ctx` tiếp theo (một step đang chạy sẽ hoàn tất trước), các compensation của nó chạy, và nó kết thúc ở trạng thái `failed` với một `WorkflowTimeoutError`. Compensation không bị giới hạn bởi hạn chót. Ở đây lần chờ bỏ cuộc sau 3 ngày và lần sleep mất 7 ngày, nên 30 ngày là một tấm lưới an toàn. `start()` cũng nhận tùy chọn `timeout`, ghi đè giá trị của decorator cho instance đó.

#### Hủy và vận hành workflow <a id="cancel-and-operate-workflows"></a>

##### Cho bộ phận chăm sóc khách hàng hủy đơn <a id="let-customer-support-cancel-an-order"></a>

Thêm một route `cancel()` vào `OrdersController`, và thêm `ConflictException` cùng `HttpCode` vào import từ `@nestjs/common`. `OrdersService.markCancelled()` đặt trạng thái của đơn hàng:

```typescript
@@filename(orders/orders.controller)
// Customer support only: protect it with your staff guard.
@Post(':id/cancel')
@HttpCode(202)
async cancel(@Param('id') id: string, @Body('reason') reason: string) {
  const order = await this.ordersService.findOne(id);
  if (order.status === 'delivered') {
    throw new ConflictException(`Order ${id} was delivered. Start a return instead.`);
  }
  // accepted is false if the fulfilment already ended or was already cancelled.
  const { accepted } = await this.workflowClient.cancel(fulfilmentId(id), reason);
  if (accepted) {
    await this.ordersService.markCancelled(id);
  }
  return { accepted };
}
```

`cancel()` đặt một cờ. Một instance đang đỗ sẽ thức dậy ngay lập tức. Một instance đang chạy sẽ để step hiện tại hoàn tất và dừng ở lời gọi `ctx` tiếp theo. (Một instance đang chạy ở process khác sẽ nhận ra cờ này ở lần gia hạn lease tiếp theo, trong vòng một phần ba `leaseDuration`.) Dù theo cách nào, các compensation của các step đã hoàn tất cũng chạy theo thứ tự ngược, và instance kết thúc ở trạng thái `cancelled` với lý do làm error message. `cancel()` trả về instance kèm cờ `accepted`. Cờ này là `false` khi instance đã hoàn tất hoặc thất bại, khi nó đang bù trừ cho một lần thất bại, hoặc khi đã có yêu cầu cancel hoặc terminate trước đó. Lần cancel thứ hai không thay đổi gì, và lý do đầu tiên được giữ lại.

Khi đơn vị vận chuyển đã báo việc giao hàng, route trả lời `409`, vì bộ phận hỗ trợ nên khởi tạo một lần trả hàng thay vào đó. Workflow không dựa vào bước kiểm tra đó. Một lần hủy tới nó sau `ctx.commit('delivered')` sẽ dừng việc nhờ đánh giá và không hoàn tiền gì cả. Một lần hủy mà nó thấy trước khi đã tiêu thụ event giao hàng vẫn hoàn tiền, vì nó chưa chạm tới điểm không thể quay lại.

##### Ý nghĩa của từng trạng thái <a id="what-each-status-means"></a>

`status` của một instance cho biết nó đang làm gì, và liệu nó có cần bạn can thiệp không:

| Trạng thái | Ý nghĩa | Cần làm gì |
| --- | --- | --- |
| `pending` | Đã khởi động, và chưa được worker nào claim. Một instance cứ ở `pending` là đang chờ một slot concurrency hoặc chỗ trống trong một cửa sổ rate-limit, hoặc thuộc một phiên bản mà không worker nào đang chạy đăng ký | Không cần gì khi một giới hạn đang giữ nó. Nếu không, hãy deploy một worker với phiên bản đó, hoặc xóa instance |
| `running` | Một worker đang giữ lease và thực thi nó | Không cần gì. `cancel()` dừng nó ở lời gọi `ctx` tiếp theo, và `terminate()` thì dừng mà không bù trừ |
| `suspended` | Đang đỗ ở một lần sleep, wait hoặc backoff của retry, cho tới `wakeAt` hoặc một signal | Không cần gì. Một signal hoặc `cancel()` sẽ đánh thức nó |
| `compensating` | Đang hoàn tác các step đã hoàn tất sau một lần thất bại hoặc hủy | Không cần gì: nó sẽ kết thúc ở `failed`, `cancelled` hoặc `compensation_failed`. `terminate()` dừng việc hoàn tác |
| `completed` | Đã xong, với kết quả của `run()` làm `output` | Không cần gì, cho tới khi chính sách lưu trữ dọn dẹp nó |
| `cancelled` | Đã bị hủy, sau khi các compensation chạy, hoặc bị terminate mà không chạy chúng (`error.name` là `WorkflowTerminatedError`). `error.message` là lý do | Không cần gì, cho tới khi chính sách lưu trữ dọn dẹp nó |
| `failed` | Một step đã bỏ cuộc, `ctx.fail()` được gọi, run timeout đã trôi qua hoặc journal chạm giới hạn, và sau đó các compensation đã chạy. Hoặc một lỗi định nghĩa, chẳng hạn một lần deploy làm hỏng replay, đã làm nó thất bại mà không bù trừ | Nếu không có compensation nào chạy, hãy sửa nguyên nhân và retry nó. Nếu không thì nó đã xong: các step đã hoàn tất của nó đã được hoàn tác |
| `compensation_failed` | Một lần hoàn tác đã bỏ cuộc giữa chừng. `error` là lỗi gốc, với lỗi riêng của compensation nằm ở `error.compensation` | Sửa nguyên nhân, chẳng hạn một API kho bị down, và retry nó. Hoặc tự hoàn tất việc hoàn tác bằng tay và xóa instance |

##### Retry, xóa hoặc terminate <a id="retry-delete-or-terminate"></a>

`WorkflowClient` có các hành động cho cột cuối cùng của bảng. Hãy gọi chúng từ một route chỉ dành cho nhân viên hoặc một script:

```typescript
await this.workflowClient.retry(fulfilmentId(orderId));
await this.workflowClient.delete(fulfilmentId(orderId));
await this.workflowClient.terminate(fulfilmentId(orderId), 'Refunded by hand after a chargeback.');
```

- **`retry()`** chạy lại một instance `failed` từ journal của nó: các step đã hoàn tất trả về kết quả của chúng, step đã bỏ cuộc được trả lại số lần thử, và các lần sleep và wait mà instance bỏ dở sẽ bắt đầu lại. Một lần deploy làm hỏng replay sẽ được retry khi code đã sửa chạy. Nó từ chối một instance mà các compensation đã chạy, vì tiếp tục sẽ xây dựng trên công việc đã bị hoàn tác: hãy khởi động một instance mới thay vào đó. Một instance đã quá run timeout cần một timeout mới, qua tùy chọn `timeout` (tính từ bây giờ), hoặc `false` để không có timeout. Một instance `compensation_failed` sẽ chạy lại các compensation chưa hoàn tất, mỗi cái được trả lại số lần thử, và kết thúc như lẽ ra nó đã kết thúc: `failed` hoặc `cancelled`.
- **`delete()`** xóa một instance đã kết thúc cùng journal của nó. Một instance chưa kết thúc cần tùy chọn `force`, và bị xóa mà không chạy các compensation của nó: hãy dùng nó cho một instance mà không worker nào còn chạy được nữa, chẳng hạn một instance thuộc phiên bản bạn không còn deploy.
- **`cancel()`**, như ở trên, dừng một instance vẫn đang chạy, và chạy các compensation của nó.
- **`terminate()`** dừng một instance mà không chạy các compensation của nó, cho một instance mà việc hoàn tác không được phép hoặc không thể chạy, chẳng hạn một đơn hàng mà bộ phận hỗ trợ đã hoàn tiền bằng tay. Một instance đang đỗ dừng ngay lập tức, một instance đang chạy dừng ở lời gọi `ctx` tiếp theo, và một instance đang bù trừ dừng sau compensation mà nó đang chạy. Nó kết thúc ở trạng thái `cancelled`, với một `WorkflowTerminatedError` có message là lý do (`Terminated.` nếu không có lý do). Nó cũng được chấp nhận sau một lần `cancel()`, và thay thế lần cancel đó, còn một lần `cancel()` sau nó sẽ bị từ chối. Các child của nó nhận `parentClose` của chúng, như với mọi lần kết thúc khác.

`retry()` và `delete()` throw một `WorkflowStateError`, có `status` là `409`, với một trạng thái mà chúng không có ý nghĩa, và khi một thay đổi khác trên instance chạy đua với chúng. Một lần retry được ghi journal thành `$retry:1`, `$retry:2` và cứ thế, kèm trạng thái và lỗi mà nó đã retry, và cả hai hành động đều được phát ra, dưới dạng `workflow-retried` và `workflow-deleted`.

##### Dọn dẹp các instance đã kết thúc <a id="purge-finished-instances"></a>

Các instance đã kết thúc vẫn ở lại, cùng journal của chúng, cho tới khi bạn dọn dẹp chúng. `purge()` xóa những instance đã kết thúc lâu hơn tùy chọn `olderThan` của nó, từng batch một, cùng các signal không còn instance nào nhận được. Một instance chỉ nhận các signal được gửi sau khi nó bắt đầu, nên khi mọi instance chưa kết thúc đều bắt đầu sau một signal, và signal đó cũ hơn `olderThan`, nó sẽ bị xóa; signal mới nhất luôn được giữ lại. Các instance `compensation_failed` chờ một người xử lý, nên chúng chỉ bị dọn dẹp khi bạn liệt kê chúng trong tùy chọn `status`. Hãy chạy nó mỗi đêm, trên một instance của ứng dụng, với `@Cron()` từ `@nestjs/schedule` và `@OnOneInstance()` từ [`@nestjs/locks`](/reliability/locks):

```typescript
@Injectable()
export class WorkflowRetentionJob {
  constructor(private readonly workflowClient: WorkflowClient) {}

  @Cron('30 3 * * *')
  @OnOneInstance({ key: 'workflows:purge' })
  async purge() {
    return this.workflowClient.purge({ olderThan: '30d' });
  }
}
```

`purge()` resolve với số `instances` và `signals` mà nó đã xóa, và số cửa sổ rate-limit đã kết thúc (`rateLimits`). `id` của một signal giúp khử trùng lặp chừng nào signal còn được lưu, nên hãy giữ `olderThan` dài hơn khoảng thời gian gửi lại của mọi bên gửi, chẳng hạn các lần retry webhook của đơn vị vận chuyển.
#### Giới hạn, child và công việc theo batch <a id="limits-children-and-batch-work"></a>

##### Giới hạn số lượng chạy cùng lúc <a id="limit-how-many-run-at-once"></a>

Một worker chạy mọi instance tới hạn mà nó còn chỗ. Có ba tùy chọn quyết định cái gì được chạy, và theo thứ tự nào, trên mọi worker: một giới hạn concurrency, một rate limit và một độ ưu tiên. Quy trình giao hàng đặt hai tùy chọn đầu trong `@Workflow()`:

```typescript
@@filename(orders/order-fulfilment.workflow)
@Workflow('order-fulfilment', {
  // One execution per customer at a time, so two of their orders never charge their card at once.
  concurrency: { limit: 1, key: (order: Order) => order.userId },
  // Each execution sends the payment provider one request at most: a charge, or a refund.
  rateLimit: { max: 10, duration: '1s' },
})
```

**Concurrency.** `concurrency` giới hạn số instance chạy cùng lúc: một `limit` cho cả workflow, hoặc một `limit` theo từng key với một hàm `key`, ở đây là id khách hàng. Một mảng nhận mỗi loại một cái. Một instance chỉ giữ slot trong khi một lần thực thi đang chạy nó, kể cả compensation, chứ không giữ khi nó đang sleep hay wait: một giới hạn bảo vệ những gì các step gọi tới, và một đơn hàng đỗ lại nhiều ngày không cản trở ai cả. Một process bị crash sẽ giải phóng slot của nó khi lease hết hạn. Các instance vượt quá giới hạn vẫn ở trạng thái tới hạn và chờ slot, instance quá hạn lâu nhất được ưu tiên, và một key đã đầy sẽ bị bỏ qua, nên một khách hàng bận rộn không bao giờ cản trở đơn hàng của khách hàng khác. Key được tính từ input khi instance khởi động, và tùy chọn `concurrencyKey` của `start()` cho phép đặt key khác, với workflow có giới hạn theo key.

**Rate limit.** `rateLimit` giới hạn số lần thực thi bắt đầu trong mỗi cửa sổ: `max` mỗi `duration` cho cả workflow, hoặc theo từng key với một hàm `key`, có thể ghi đè bằng tùy chọn `rateLimitKey` của `start()`. Mọi lần thực thi đều được tính, lần đầu tiên và mỗi lần tiếp tục sau một sleep, một signal, backoff của một lần retry hay một lần cancel, vì mỗi lần đều có thể gọi tới thứ mà giới hạn bảo vệ. Quy trình giao hàng gửi tối đa một request tới payment provider mỗi lần thực thi, nên điều này giới hạn số request của nó, và cả những lần thực thi không gửi request nào. Một cửa sổ mở ra với lần thực thi đầu tiên sau khi cửa sổ trước kết thúc, và cho phép `max` lần thực thi cho tới khi nó đóng lại, nên hai cửa sổ liền kề có thể cho phép gấp đôi `max` trong một `duration`. Chẳng hạn payment provider cho phép 20 request mỗi giây: hãy cho phép 10.

**Độ ưu tiên.** Tùy chọn `priority` của `start()` quyết định cái gì được claim trước: độ ưu tiên thấp nhất, rồi đến instance quá hạn lâu nhất. Đó là một số nguyên từ 1 tới 2.097.151, và các instance khởi động không có độ ưu tiên sẽ đi trước mọi instance có độ ưu tiên. Đơn hàng hỏa tốc đi trước:

```typescript
@@filename(orders/orders.service)
const fulfilment = await this.workflowClient.start(OrderFulfilmentWorkflow, order, {
  id: fulfilmentId(order.id),
  transaction: tx,
  // Lower runs first: express orders before standard ones.
  priority: order.shipping === 'express' ? 1 : 2,
});
```

Vì các instance không có độ ưu tiên đi trước, nên khi đơn hàng đã có độ ưu tiên, các công việc khác cần có độ ưu tiên để đi sau chúng: lịch chạy của batch hóa đơn cho nó giá trị 10, trong [Chạy workflow theo lịch](/reliability/workflows#run-workflows-on-a-schedule). Một instance giữ độ ưu tiên của nó cho mọi lần thực thi, và các child kế thừa độ ưu tiên của cha. Độ ưu tiên là tuyệt đối: một dòng đơn hàng hỏa tốc liên tục sẽ giữ chân các đơn tiêu chuẩn. `@StartOn()` nhận cùng tùy chọn này, như [Với CQRS](/reliability/workflows#with-cqrs) trình bày.

Các giới hạn lấy từ phiên bản cao nhất được đăng ký của workflow và áp dụng cho mọi phiên bản của nó, và mỗi process áp dụng các giới hạn của code mà nó chạy, nên hãy deploy thay đổi về giới hạn ở mọi nơi. Các lần claim không bao giờ cho phép nhiều hơn mức giới hạn cho phép, nhưng có thể cho phép ít hơn trong chốc lát: các worker poll cùng lúc có thể mất vài lần poll để lấp đầy một cửa sổ ngắn, và khi có cả concurrency key lẫn rate-limit key, một ứng viên bị một loại key bỏ qua sẽ chờ lần claim tiếp theo. Các lần claim cũng sắp xếp các instance tới hạn theo độ ưu tiên, điều mà index trên `wake_at` không làm được: rẻ khi có ít instance tới hạn, nhưng đáng kể khi tồn đọng nhiều. `drain()` dừng lại khi không còn gì có thể bắt đầu.

##### Khởi động child workflow <a id="start-child-workflows"></a>

Việc vận chuyển phát triển thêm: đặt lịch lấy hàng với đơn vị vận chuyển, hủy nó nếu đơn hàng bị hoàn tác, rồi chờ việc giao hàng hoặc trả hàng. Đó là một quy trình riêng, có step, retry và trạng thái riêng, nên hãy cho nó một workflow riêng, và chạy nó như một **child** của quy trình giao hàng:

```typescript
@@filename(shipping/shipment.workflow)
import { Workflow, type WorkflowContext, type WorkflowRunner } from '@nestjs/workflows';
import type { Order } from '../orders/order.js';
import { shipmentDelivered, shipmentReturned, type CarrierEvent } from './carrier-event.js';
import { CarrierClient } from './carrier.client.js';

/** Books the carrier's pickup, and waits for the delivery: a child of the order's fulfilment. */
@Workflow('shipment')
export class ShipmentWorkflow implements WorkflowRunner<Order, CarrierEvent> {
  constructor(private readonly carrierClient: CarrierClient) {}

  async run(ctx: WorkflowContext, order: Order): Promise<CarrierEvent> {
    await ctx.step(
      'book-pickup',
      ({ idempotencyKey }) => this.carrierClient.bookPickup(order, idempotencyKey),
      { compensate: ({ pickupId }) => this.carrierClient.cancelPickup(pickupId) },
    );

    const outcome = await ctx.waitForAny('await-delivery', {
      delivered: ctx.signalWait(shipmentDelivered, { key: order.id }),
      returned: ctx.signalWait(shipmentReturned, { key: order.id }),
      timedOut: ctx.timer('3d'),
    });
    if (outcome.key === 'returned') {
      ctx.fail(`The carrier returned order ${order.id} to the warehouse.`);
    }
    if (outcome.key === 'timedOut') {
      ctx.fail(`Order ${order.id} was not delivered within 3 days.`);
    }
    return outcome.value;
  }
}
```

`CarrierClient` là bản thay thế cho API đặt lịch của đơn vị vận chuyển, giống như payment provider, nó trả lời một idempotency key lặp lại bằng lần đặt lịch đầu tiên. Trong quy trình giao hàng, child thay thế cho lần chờ:

```typescript
@@filename(orders/order-fulfilment.workflow)
// Starts the shipment, and waits for it to end: its delivery, or a ChildWorkflowFailedError.
const delivery = await ctx.executeChild(ShipmentWorkflow, order);
```

Đăng ký `ShipmentWorkflow` và `CarrierClient` làm provider, cạnh quy trình giao hàng. Webhook của đơn vị vận chuyển không thay đổi: nó gửi signal với id đơn hàng, và giờ shipment là instance đang chờ nó.

- **`ctx.executeChild()`** khởi động child và chờ nó kết thúc. Cả hai đều được ghi journal, dưới dạng `$child:<id>` và `$result:<id>`, nên một lần replay nhận lại cùng child thay vì khởi động một child khác, và quy trình giao hàng đỗ lại trong lúc đó. `ctx.startChild()` chỉ khởi động nó, và trả về một handle: `result()` của handle chờ child, và handle là một điều kiện của `waitForAny()`, để cho child chạy đua với một timer hoặc một signal.
- **Id.** Id của một child mặc định gồm id của cha, tên workflow và số thứ tự child của workflow đó trong lần chạy này, chẳng hạn `order-71e1973d/shipment#1`. Hãy cho các child được khởi động từ các nhánh song song một tùy chọn `id` suy ra từ dữ liệu của bạn, để một lần replay, vốn có thể chạm tới chúng theo thứ tự khác, tìm thấy đúng từng child.
- **Thất bại.** Nếu child thất bại, bị hủy hoặc bị terminate, `executeChild()` throw một `ChildWorkflowFailedError`, với `status` của nó và lỗi của nó làm `cause`. Nếu không bắt, nó làm quy trình giao hàng thất bại như mọi lỗi khác: một kiện hàng bị trả về làm shipment thất bại, compensation của shipment hủy lịch lấy hàng, rồi đến quy trình giao hàng, với các compensation hoàn tiền và giải phóng hàng trong kho. Hãy bắt nó để thử cách khác, chẳng hạn một đơn vị vận chuyển khác.
- **`parentClose`** quyết định điều gì xảy ra với một child vẫn đang chạy khi cha của nó kết thúc hoặc bắt đầu bù trừ: `'cancel'`, mặc định, sẽ hủy nó, và các compensation của nó chạy; `'terminate'` dừng nó mà không chạy compensation; `'abandon'` để nó tiếp tục chạy. Khi bộ phận hỗ trợ hủy đơn hàng, shipment bị hủy cùng nó, và lịch lấy hàng bị hủy cùng shipment.
- Một child kế thừa độ ưu tiên của cha, trừ khi `startChild()` nhận một độ ưu tiên riêng, và nhận các tùy chọn `concurrencyKey` và `rateLimitKey` như `start()`. `getStatus()` với tùy chọn `children` liệt kê các child của một instance, mỗi child kèm `parentId`, và `list()` phân trang chúng theo `parentId`.

##### Step chạy lâu <a id="long-running-steps"></a>

Một step có thể chạy hàng giờ. Trong khi nó chạy, worker liên tục gia hạn lease ở chế độ nền. Với công việc batch dài, hãy lưu checkpoint tiến độ để một lần crash không khởi động lại công việc từ đầu. Ở đây, một batch hàng tháng render hóa đơn từng trang một:

```typescript
@@filename(invoices/invoice-batch.workflow)
import { Workflow, type WorkflowContext, type WorkflowRunner, type WorkflowStepContext } from '@nestjs/workflows';
import { InvoicesService } from './invoices.service.js';

interface Checkpoint {
  cursor: number | null;
  rendered: number;
}

@Workflow('invoice-batch')
export class InvoiceBatchWorkflow implements WorkflowRunner<{ month: string }, { rendered: number }> {
  constructor(private readonly invoicesService: InvoicesService) {}

  async run(ctx: WorkflowContext, { month }: { month: string }) {
    return ctx.step(
      'render-invoices',
      async ({ progress, heartbeat, signal }: WorkflowStepContext<Checkpoint>) => {
        // After a crash, the next attempt starts from the last checkpoint.
        let { cursor, rendered } = progress ?? { cursor: 0, rendered: 0 };
        while (cursor !== null) {
          const page = await this.invoicesService.renderPage(month, cursor, signal);
          cursor = page.nextCursor;
          rendered += page.rendered;
          await heartbeat({ cursor, rendered });
        }
        return { rendered };
      },
      { heartbeatTimeout: '2m' },
    );
  }
}
```

- `heartbeat(progress)` ghi checkpoint vào journal. Nếu lần thử chết, lần tiếp theo nhận nó dưới dạng `progress`. Khai báo type của tham số là `WorkflowStepContext<Checkpoint>` sẽ gán type cho cả hai. Trang đang được xử lý dở sẽ được render lại, nên `renderPage()` phải ghi đè thay vì nối thêm.
- `heartbeatTimeout` làm thất bại một lần thử ngừng gọi `heartbeat()`, chẳng hạn một lần thử bị kẹt ở một socket treo, trong khi process vẫn còn sống. Tùy chọn `timeout` giới hạn tổng thời lượng của lần thử.
- `signal` bị abort khi shutdown, khi mất lease và khi gặp các timeout đó. Hãy truyền nó cho các thao tác I/O của bạn.

Một lịch chạy, bên dưới, khởi động batch mỗi tháng. Khi công việc nên chạy trên các process riêng, chẳng hạn một nhóm renderer PDF, hãy giao nó cho một queue [BullMQ](/application/queues) từ một step, và chờ job báo lại bằng một signal. Job id là `idempotencyKey` của step, nên một step được retry sẽ không đưa job vào hàng đợi hai lần:

```typescript
await ctx.step('enqueue-render', async ({ idempotencyKey }) => {
  await this.invoicesQueue.add('render', { month }, { jobId: idempotencyKey });
});
const rendered = await ctx.waitForSignal('await-render', invoicesRendered, { key: month, timeout: '6h' });
```

Processor của queue báo lại khi job đã xong:

```typescript
await this.workflowClient.signal(invoicesRendered, result, { key: job.data.month, id: job.id });
```

`id` giúp signal chỉ được lưu một lần khi BullMQ chạy lại job, và một job xong trước khi workflow chạm tới lần chờ vẫn được tính, vì signal là bền vững.

##### Chạy workflow theo lịch <a id="run-workflows-on-a-schedule"></a>

Hóa đơn đến hạn vào ngày 1 hàng tháng. Thay vì một cron job khởi động batch, hãy khai báo một lịch chạy trên workflow:

```typescript
@@filename(invoices/invoice-batch.workflow)
import { Workflow, type WorkflowContext, type WorkflowRunner, type WorkflowStepContext } from '@nestjs/workflows';

/** The month before the one `at` falls in, in UTC ('2026-09' in October 2026): 02:00 on the 1st in New York is the 1st in UTC too. */
const lastMonth = (at: number) => new Date(new Date(at).setUTCDate(0)).toISOString().slice(0, 7);

@Workflow('invoice-batch', {
  schedules: [
    {
      id: 'monthly-invoices',
      // At 02:00 on the 1st of every month, in the store's time zone: last month's invoices.
      cron: '0 2 1 * *',
      tz: 'America/New_York',
      // A deploy or an outage at 02:00 delays the batch instead of skipping a month.
      missed: 'once',
      // After the orders (express 1, standard 2): without a priority, it would go before them.
      priority: 10,
      input: ({ at }) => ({ month: lastMonth(at) }),
    },
  ],
})
export class InvoiceBatchWorkflow implements WorkflowRunner<{ month: string }, { rendered: number }> {
  // ...as before
}
```

Mọi worker có code khai báo lịch chạy này đều khởi động các lần chạy của nó, và mỗi lần chạy khởi động đúng một instance, bất kể có bao nhiêu worker: id của nó là id của lịch chạy và thời điểm của lần chạy, chẳng hạn `monthly-invoices@2026-10-01T06:00:00.000Z`. Hàm `input` nhận lần chạy, gồm `id` của lịch chạy và thời điểm `at` của nó, và instance cũng nhận điều này, dưới dạng `ctx.schedule`, giá trị này là `null` với một instance được khởi động theo cách khác.

- **Khi nào.** `cron` nhận 5 trường, hoặc 6 trường với giây đứng đầu, `every` là một khoảng cố định, và `rrule` là một recurrence rule theo RFC 5545. Thời điểm là giờ đồng hồ trong `tz`, mặc định là UTC, nên batch bắt đầu lúc 02:00 ở New York cả trước lẫn sau khi đổi giờ. Khi lùi giờ, một giờ địa phương xuất hiện hai lần chỉ chạy một lần, ở lần đầu tiên, nên một lịch chạy hàng giờ sẽ bỏ qua lượt thứ hai của giờ bị lặp. Khi tiến giờ, một thời điểm không tồn tại vẫn chạy, muộn đúng bằng khoảng giờ bị nhảy: 02:30 chạy lúc 03:30. `every` không nhận `tz`: nó lặp lại một khoảng cố định bất kể múi giờ. `startAt`, `endAt` và `limit` giới hạn một lịch chạy.
- **`missed`** cho biết điều gì xảy ra với các lần chạy mà không worker nào hoạt động để khởi động, trong lúc deploy hoặc gặp sự cố. `'skip'`, mặc định, chỉ khởi động một lần chạy nếu có worker tìm thấy nó trong vòng một phút kể từ thời điểm của nó; `'once'` khởi động lần gần nhất trong số đó; `'all'` khởi động từng lần, tối đa 100 lần gần nhất, và cần `overlap: 'allow'`. Các lần chạy mà nó bỏ qua được báo cáo trong một event `schedule-skipped`.
- **`overlap`** cho biết một lần chạy làm gì khi một instance mà lịch chạy đã khởi động vẫn chưa kết thúc: `'skip'`, mặc định, bỏ qua nó, kèm một event `schedule-skipped`; `'allow'` vẫn khởi động nó; `'cancel-previous'` hủy instance đang chạy; `'buffer-one'` khởi động nó khi instance đang chạy kết thúc.

Một lịch chạy được khai báo thuộc về code, kể cả trong khi một lần rolling deploy chạy song song code cũ và code mới. Mỗi process lưu các lịch chạy mà workflow của nó khai báo khi nó khởi động, và xác nhận chúng mỗi phút trong khi worker của nó chạy. Một process để nguyên một lịch chạy trong khi một process khác xác nhận nó, nếu code của chính nó không khai báo lịch đó hoặc một phiên bản mới hơn của workflow khai báo nó khác đi. Khi không có process nào xác nhận lịch chạy trong năm phút, một process sẽ xóa lịch chạy mà code của nó không khai báo, dù nó có chạy workflow của lịch đó hay không, và thay một khai báo khác bằng khai báo của chính nó. Vì vậy một pod cũ restart giữa lúc rollout sẽ không động tới các lịch chạy mà code mới thêm vào hoặc một phiên bản mới thay đổi, một lịch chạy bị một lần deploy loại bỏ sẽ biến mất khoảng năm phút sau khi process cuối cùng của code cũ dừng, kể cả khi lần deploy xóa workflow của nó, và một lần rollback sẽ mang khai báo cũ trở lại.

Các process của code khác trên cùng database, chẳng hạn worker của các workflow khác, cũng xóa một lịch chạy khi không có worker nào có code khai báo nó chạy trong năm phút, chẳng hạn khi các worker đó bị scale về không. Process tiếp theo có code khai báo nó sẽ lưu lại nó khi khởi động, và lịch chạy bắt đầu lại: từ lần chạy tiếp theo, không bị tạm dừng, với số lần chạy được đếm lại từ không.

`WorkflowClient.schedules`, cũng có thể inject dưới tên `WorkflowSchedules`, xử lý lịch chạy lúc runtime. `trigger('monthly-invoices')` khởi động một lần chạy ngay bây giờ, bất kể `overlap` nói gì và kể cả khi lịch chạy đang tạm dừng, với thời điểm hiện tại làm `at`. `pause()` dừng các lần chạy cho tới `resume()`, lệnh này bắt đầu lại từ lần chạy đầu tiên sau thời điểm hiện tại. `preview()` trả về các lần chạy tiếp theo, tính bằng epoch mili giây, còn `get()` và `list()` đọc các lịch chạy. Một lịch chạy không có trong code, chẳng hạn mỗi khách hàng một lịch, được lưu bằng `upsert()`, và `remove()` xóa nó, để các instance mà nó đã khởi động tiếp tục chạy:

```typescript
await this.workflowClient.schedules.upsert(`reorder-reminder-${user.id}`, {
  workflow: ReorderReminderWorkflow,
  // Every 4 weeks, on Saturdays at 09:00 in the customer's time zone
  rrule: 'FREQ=WEEKLY;INTERVAL=4;BYDAY=SA;BYHOUR=9;BYMINUTE=0',
  tz: user.timeZone,
  input: { userId: user.id },
});
```

`upsert()` và `remove()` từ chối một lịch chạy đã khai báo, vốn được thay đổi trong code.

##### Chờ kết quả <a id="wait-for-a-result"></a>

Phần lớn bên gọi khởi động một workflow rồi đi tiếp. Một số cần kết quả của nó: một kế toán viên muốn hóa đơn của một tháng ngay bây giờ, trước khi lịch chạy render chúng, gọi một route render chúng và trả lời bằng số lượng. `startAndWait()` khởi động instance và chờ nó kết thúc:

```typescript
@@filename(invoices/invoices.controller)
import { Controller, HttpCode, Param, Post, Res } from '@nestjs/common';
import { WorkflowClient, WorkflowResultTimeoutError } from '@nestjs/workflows';
import type { Response } from 'express';
import { InvoiceBatchWorkflow } from './invoice-batch.workflow.js';

@Controller('invoices')
export class InvoicesController {
  constructor(private readonly workflowClient: WorkflowClient) {}

  // Accounting only: protect it with your staff guard.
  @Post(':month')
  @HttpCode(200)
  async render(@Param('month') month: string, @Res({ passthrough: true }) response: Response) {
    try {
      // One batch per month: calling again, while it runs or after it ended, waits for the same one.
      return await this.workflowClient.startAndWait(InvoiceBatchWorkflow, { month }, { id: `invoices-${month}` }, { timeout: '30s' });
    } catch (error) {
      if (!(error instanceof WorkflowResultTimeoutError)) {
        throw error;
      }
      // The batch keeps running: answer now, and let the accountant call again later.
      response.status(202);
      return { rendering: true };
    }
  }
}
```

- `startAndWait()` là `start()`, rồi `result()`, lệnh này chờ một instance kết thúc và resolve với output của nó. Với một id đã có instance, nó chờ instance đó, nên kế toán viên gọi lại route, trong khi batch đang chạy hoặc sau khi nó đã kết thúc, sẽ nhận cùng batch. Các tùy chọn của lần chờ là tham số thứ tư: `timeout` của tham số thứ ba vẫn là run timeout của instance.
- Quá `timeout` của lần chờ, tính theo giờ thực chứ không theo đồng hồ của module, nó reject với `WorkflowResultTimeoutError`, và instance vẫn tiếp tục chạy: route trả lời `202`. Tùy chọn `signal` dừng lần chờ khi nó bị abort, chẳng hạn khi bên gọi bỏ đi.
- Khi shutdown, một lần chờ kéo dài trong khi worker hoàn tất các step đang chạy, tối đa `shutdownTimeout`, nên một instance kết thúc trong lúc đó vẫn trả về kết quả của nó. Sau đó lần chờ reject với một `Error`, trước khi Nest đóng HTTP server, và route trả lời ngay lập tức, ở đây là với `500`, thay vì giữ chân quá trình shutdown cho tới `timeout` của lần chờ.
- Một instance đã thất bại, bị hủy hoặc bị terminate sẽ reject với một `WorkflowFailedError`, có `status` cho biết nó kết thúc thế nào và `cause` là lỗi của nó. Ở đây, đó là `500`.
- `result()` chờ một instance theo id của nó, chẳng hạn instance mà `trigger()` đã khởi động, bất kể process nào chạy nó. `startAndWait()` từ chối tùy chọn `transaction`, vì instance chỉ tồn tại khi transaction của bạn commit: hãy gọi `start()` trong transaction, và `result()` sau khi commit.

#### Deploy thay đổi một cách an toàn <a id="deploy-changes-safely"></a>

Journal được đánh key theo tên, nên tên của step, sleep và wait là một hợp đồng với mọi instance vẫn đang chạy. Tên cũng là một phần của idempotency key.

Giả sử bạn đổi tên `charge-payment` thành `charge-card` và deploy. Một đơn hàng đang chờ đơn vị vận chuyển sẽ tiếp tục, không tìm thấy entry `charge-card` nào trong journal, và sẽ trừ tiền thẻ lần nữa, với một key mà payment provider chưa từng thấy. Trước khi step mới đầu tiên của một lần thực thi chạy, engine kiểm tra rằng code đã chạm tới mọi step trong journal. Ở đây thì không, nên instance thất bại mà không trừ tiền:

```text
Instance "order-6d0f8c06" of workflow "order-fulfilment@1" does not match its journal:
"charge-payment", "reserve-stock", "await-delivery" were recorded by an earlier run but not
reached before the new step "charge-card". A deployed change renamed, removed or reordered steps.
Ship such changes as a new version (@Workflow(name, { version })) and keep the old class
registered until its instances finish.
```

Các compensation của nó cũng không chạy, vì chúng được định nghĩa bởi code không còn khớp nữa. Instance được để lại cho một người xử lý. Bước kiểm tra này không thấy được một step giữ nguyên tên nhưng phần thân giờ làm điều gì đó khác.

Một số thay đổi không cần phiên bản mới:

- thay đổi phần thân của một step mà không thay đổi ý nghĩa của nó,
- thêm step sau step, sleep hoặc wait cuối cùng mà bất kỳ instance đang chạy nào đã chạm tới,
- thay đổi tùy chọn retry và timeout.

Mọi thay đổi khác phải được ship dưới dạng một phiên bản mới. Chẳng hạn bộ phận marketing muốn một email xác nhận đơn hàng ngay sau khi thanh toán. Chèn một step trước `reserve-stock` sẽ thay đổi những gì một lần replay thấy, nên hãy copy class và tăng phiên bản của nó:

```typescript
@@filename(orders/order-fulfilment-v2.workflow)
@Workflow('order-fulfilment', {
  version: 2,
  // The limits of the highest registered version apply to every version: keep them.
  concurrency: { limit: 1, key: (order: Order) => order.userId },
  rateLimit: { max: 10, duration: '1s' },
})
export class OrderFulfilmentWorkflowV2 implements WorkflowRunner<Order, FulfilmentResult> {
  // ...same constructor as version 1

  async run(ctx: WorkflowContext, order: Order): Promise<FulfilmentResult> {
    const charge = await ctx.step(
      'charge-payment',
      // ...unchanged
    );
    ctx.setStatus('paid');

    await ctx.step('send-order-confirmation', ({ idempotencyKey }) =>
      this.mailService.sendOrderConfirmation(order, idempotencyKey),
    );

    // ...the rest is unchanged from version 1
  }
}
```

Đăng ký cả hai class. Một instance giữ phiên bản mà nó đã bắt đầu, và một worker chỉ claim các phiên bản mà nó đã đăng ký, nên pod cũ và mới có thể chạy song song trong một lần rolling deploy. Các instance mới bắt đầu trên phiên bản cao nhất được đăng ký, kể cả khi controller vẫn truyền `OrderFulfilmentWorkflow`, vì class chỉ dùng để xác định tên workflow. Để cố định một phiên bản, hãy thêm `version: 1` vào các tùy chọn của `start()`. Gỡ phiên bản 1 khi `list()` với tên workflow, `version: 1` và các trạng thái chưa kết thúc (`pending`, `running`, `suspended` và `compensating`) trả về rỗng.

##### Quy tắc cho code workflow <a id="rules-for-workflow-code"></a>

`run()` thực thi lại từ đầu mỗi khi một instance tiếp tục. Code nằm giữa các step chạy ở mọi lần thực thi, nên nó phải đưa ra cùng các quyết định mỗi lần:

- Đặt mọi thứ chạm tới hoặc đọc từ thế giới bên ngoài vào một step: lời gọi HTTP, đọc và ghi database, feature flag.
- Bên ngoài step, hãy dùng `ctx.now()`, `ctx.random()` và `ctx.uuid()` thay cho `Date.now()`, `Math.random()` và `randomUUID()`. Chúng được ghi journal.
- Trong `run()`, chỉ `await` các thao tác của `ctx` và các phép tính thuần. Không bao giờ chờ một timer thật.
- Tên step, sleep và wait phải là duy nhất trong một lần chạy. Trong một vòng lặp, hãy thêm index vào tên, chẳng hạn `remind-1` và `remind-2`. Hãy cho các child được khởi động từ các nhánh song song một `id` riêng.
- Đừng gọi các method của `ctx` bên trong hàm của một step. Hàm đó chạy một lần và các lần replay chỉ thấy kết quả của nó, nên engine sẽ làm instance thất bại khi một step gọi `ctx`. Hãy throw một `NonRetryableStepError` từ step thay vì gọi `ctx.fail()` ở đó.
- Nếu bạn bắt lỗi trong `run()`, hãy throw lại những gì bạn không xử lý. `isWorkflowInterrupt()` nhận diện luồng điều khiển của engine. Engine không phụ thuộc vào nó: sau một interrupt bị nuốt mất thì không step nào chạy, `commit()` throw lại, và một lần cancel vẫn hủy. Nhưng các khối `finally` chạy ở mỗi lần tạm dừng, nên hãy giữ side effect ngoài chúng.
- `Promise.all()` trên các step thì ổn, và một step trong cùng `Promise.all()` với một sleep hoặc wait sẽ bắt đầu sau nó. `Promise.race()` và `Promise.any()` không an toàn khi replay.
- Input, kết quả step và payload của signal phải serialize được sang JSON. Một `Date` trả về dưới dạng chuỗi, ở lần chạy đầu tiên và ở mọi lần replay, và các type `Journaled` của kết quả và payload nói rõ điều đó.
- Không giữ trạng thái theo từng lần chạy trên `this`: một instance của class phục vụ mọi đơn hàng.

#### Chạy thử và test <a id="try-it-and-test-it"></a>

##### Chạy thử <a id="try-it"></a>

Tạo database, áp dụng migration của bạn, và khởi động ứng dụng với `DATABASE_URL` trỏ tới database:

```bash
$ npm run start:dev
...
[Nest] 33662  - 09/30/2026, 1:28:30 PM     LOG [WorkflowsModule] WorkflowStorage: PostgresWorkflowStore
[Nest] 33662  - 09/30/2026, 1:28:30 PM     LOG [WorkflowsModule] PostgresWorkflowStore: migrated schema "nest_workflows" to version 1.
[Nest] 33662  - 09/30/2026, 1:28:30 PM     LOG [NestApplication] Nest application successfully started +8ms
```

Log nêu tên store đang dùng, không phải store trong bộ nhớ mặc định, và cho biết store đã tạo schema của nó: migration của bạn đã tạo `orders`, còn store tạo các bảng riêng của nó. Đặt một đơn hàng, rồi hỏi xem nó đang ở đâu:

```bash
$ curl -X POST http://localhost:3000/orders -H "Content-Type: application/json" \
    -d '{"userId": "u_42", "items": [{"productId": "salmon-kibble-2kg", "quantity": 1, "price": 2499}]}'
{"id":"f7e1e1eb","userId":"u_42","items":[{"productId":"salmon-kibble-2kg","quantity":1,"price":2499}],"shipping":"standard","total":2499,"status":"placed","fulfilment":{"id":"order-f7e1e1eb","workflow":"order-fulfilment","version":1,"created":true,"status":"pending"}}

$ curl http://localhost:3000/orders/f7e1e1eb/fulfilment
{"status":"suspended","stage":"awaiting-delivery","waitingFor":["shipment.delivered","shipment.returned"],"wakeAt":"2026-10-03T11:28:42.251Z","steps":{"charge-payment":"completed","reserve-stock":"completed","await-delivery":"pending"},"error":null}
```

Đơn hàng và quy trình giao hàng của nó đã được commit cùng nhau, worker đã nhận instance, thẻ đã bị trừ tiền, hạt cho mèo đã được giữ chỗ, và instance đang đỗ cho tới khi đơn vị vận chuyển báo việc giao hàng hoặc trả hàng, hoặc hạn chót 3 ngày trong `wakeAt` trôi qua.

Giờ hãy đóng vai đơn vị vận chuyển và báo việc giao hàng:

```bash
$ curl -X POST http://localhost:3000/webhooks/carrier -H "Content-Type: application/json" \
    -d '{"type": "shipment.delivered", "reference": "f7e1e1eb", "trackingNumber": "TRK123456789", "occurredAt": "2026-09-30T14:05:00Z"}'
{"received":true}

$ curl http://localhost:3000/orders/f7e1e1eb/fulfilment
{"status":"suspended","stage":"delivered","waitingFor":[],"wakeAt":"2026-10-07T11:28:58.885Z","steps":{"charge-payment":"completed","reserve-stock":"completed","await-delivery":"completed","delivered":"completed","before-review-request":"pending"},"error":null}
```

Instance đã vượt qua điểm không thể quay lại và đang ngủ cho tới khi việc nhờ đánh giá tới hạn sau 7 ngày. Bộ phận hỗ trợ không còn có thể hủy đơn hàng, và một lần giao hàng cho đơn hàng mà store không biết sẽ bị từ chối:

```bash
$ curl -X POST http://localhost:3000/orders/f7e1e1eb/cancel -H "Content-Type: application/json" -d '{"reason": "Changed my mind."}'
{"message":"Order f7e1e1eb was delivered. Start a return instead.","error":"Conflict","statusCode":409}

$ curl -X POST http://localhost:3000/webhooks/carrier -H "Content-Type: application/json" \
    -d '{"type": "shipment.delivered", "reference": "nope", "trackingNumber": "TRK1", "occurredAt": "2026-09-30T14:05:00Z"}'
{"message":"Order nope not found.","error":"Not Found","statusCode":404}
```

Đặt một đơn hàng thứ hai (ở đây nó có id `58b424f5`) và hủy nó trong khi nó đang chờ đơn vị vận chuyển:

```bash
$ curl -X POST http://localhost:3000/orders/58b424f5/cancel -H "Content-Type: application/json" \
    -d '{"reason": "Customer ordered the wrong size."}'
{"accepted":true}

$ curl http://localhost:3000/orders/58b424f5/fulfilment
{"status":"cancelled","stage":"awaiting-delivery","waitingFor":[],"wakeAt":null,"steps":{"charge-payment":"completed","reserve-stock":"completed","await-delivery":"cancelled","$compensate:reserve-stock":"completed","$compensate:charge-payment":"completed"},"error":"Customer ordered the wrong size."}
```

Journal hiển thị cả hai compensation: hàng trong kho được giải phóng trước, rồi tiền được hoàn lại. Lần chờ chưa bao giờ hoàn tất, nên nó được đánh dấu `cancelled`, và stage vẫn ở chỗ workflow đặt lần cuối.

Các instance là các dòng trong database của bạn, trong schema của store, cạnh các đơn hàng:

```bash
$ psql "$DATABASE_URL" -c "SELECT o.id, o.status, w.status AS fulfilment, w.runs FROM orders o JOIN nest_workflows.instances w ON w.id = 'order-' || o.id ORDER BY w.created_at"
    id    |  status   | fulfilment | runs
----------+-----------+------------+------
 f7e1e1eb | delivered | suspended  |    2
 58b424f5 | cancelled | cancelled  |    2
(2 rows)
```

Cuối cùng, restart ứng dụng và hỏi lại đơn hàng đầu tiên. Trạng thái của nó không thay đổi, và store không tìm thấy gì để migrate. Khởi động một process thứ hai trên một port khác với cùng database, và hai process sẽ chia sẻ công việc: mỗi instance chạy trên một trong hai tại một thời điểm. Để thấy timeout 3 ngày mà không phải chờ 3 ngày, hãy dùng một test clock, như các test bên dưới làm.

##### Test với đồng hồ thủ công <a id="test-with-a-manual-clock"></a>

Có hai thứ giúp test workflow nhanh và tất định:

- Mọi timestamp mà engine dùng (hạn chót, thời điểm retry, thời hạn lease và `ctx.now()`) đều đến từ `clock` của module. Một `ManualWorkflowClock` chỉ dịch chuyển khi bạn gọi `advance()`.
- Khi worker bị tắt, không có gì chạy ở chế độ nền. `WorkflowWorker.drain()` chạy mọi instance tới hạn cho tới khi không còn instance nào có thể bắt đầu, và khởi động các lần chạy của những lịch chạy mà đồng hồ đã vượt qua. Đồng hồ bắt đầu vào ngày 1 tháng 1 năm 2026 lúc 00:00 UTC, nên một test dịch nó đi nhiều ngày cũng sẽ khởi động lần chạy đầu tiên của batch hóa đơn, lúc 07:00 UTC.

Chạy các test trên PGlite, với các migration thật của bạn. Override database mà `DrizzleModule` đăng ký (`getDrizzleToken()` trả về token của nó) bằng một database trên PGlite: workflow store sẽ theo đó, vì factory của nó inject database này, và tạo schema của nó ở đó khi ứng dụng khởi động. Override `WORKFLOWS_MODULE_OPTIONS` với một `ManualWorkflowClock` và một worker bị tắt. Dùng chung database và các bản thay thế cho API bên ngoài giữa các ứng dụng, vì chúng tồn tại lâu hơn một process:

```typescript
@@filename(test/support)
import { fileURLToPath } from 'node:url';
import { PGlite } from '@electric-sql/pglite';
import { Test } from '@nestjs/testing';
import { ManualWorkflowClock, WORKFLOWS_MODULE_OPTIONS, WorkflowClient, WorkflowWorker } from '@nestjs/workflows';
import { drizzle } from 'drizzle-orm/pglite';
import { migrate } from 'drizzle-orm/pglite/migrator';
// ...AppModule, getDrizzleToken and the stand-in services

/**
 * PostgreSQL in-process (PGlite), with the app's migrations applied: the orders
 * table. The workflow store creates its own tables when the application starts.
 */
export async function createDatabase() {
  const client = new PGlite();
  const db = drizzle({ client });
  await migrate(db, { migrationsFolder: fileURLToPath(new URL('../drizzle', import.meta.url)) });
  return { db, close: () => client.close() };
}

/** Your database and the external APIs. They outlive a process, so every "process" in a test shares them. */
export async function createWorld() {
  const database = await createDatabase();
  return {
    db: database.db,
    paymentProvider: new PaymentProviderClient(),
    inventory: new InventoryService(),
    mail: new MailService(),
    invoices: new InvoicesService(database.db as unknown as Database),
    close: database.close,
  };
}

export type World = Awaited<ReturnType<typeof createWorld>>;

export async function bootApp(clock: ManualWorkflowClock, world: World) {
  const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
    .overrideProvider(getDrizzleToken())
    .useValue(world.db)
    .overrideProvider(WORKFLOWS_MODULE_OPTIONS)
    .useValue({ clock, worker: { enabled: false, shutdownTimeout: 50 } })
    .overrideProvider(PaymentProviderClient)
    .useValue(world.paymentProvider)
    .overrideProvider(InventoryService)
    .useValue(world.inventory)
    .overrideProvider(MailService)
    .useValue(world.mail)
    .overrideProvider(InvoicesService)
    .useValue(world.invoices)
    .compile();
  const app = moduleRef.createNestApplication({ logger: false });
  await app.listen(0, '127.0.0.1');
  return {
    app,
    url: await app.getUrl(),
    orders: app.get(OrdersService),
    workflows: app.get(WorkflowClient),
    worker: app.get(WorkflowWorker),
    close: () => app.close(),
  };
}

export type App = Awaited<ReturnType<typeof bootApp>>;
```

Với đồng hồ thủ công, timeout 3 ngày chỉ là một lời gọi `advance()`:

```typescript
@@filename(test/order-fulfilment.spec)
describe('order fulfilment', () => {
  let clock: ManualWorkflowClock;
  let world: World;
  let node: App;

  beforeEach(async () => {
    clock = new ManualWorkflowClock();
    world = await createWorld();
    node = await bootApp(clock, world);
  });

  afterEach(async () => {
    await node.close();
    await world.close();
  });

  // ...

  it('refunds and releases the stock when the carrier never confirms delivery', async () => {
    const order = await node.orders.place({ userId: 'u_42', items: [{ productId: KIBBLE, quantity: 1, price: 2499 }] });
    await node.worker.drain(); // charge, reserve, then park for up to 3 days

    clock.advance('3d');
    await node.worker.drain(); // the wait times out and the compensations run

    const fulfilment = await node.workflows.getStatus(fulfilmentId(order.id), { journal: true });
    expect(fulfilment).toMatchObject({
      status: 'failed',
      error: { message: `Order ${order.id} was not delivered within 3 days.` },
    });
    // Compensations run in reverse: release the stock, then refund.
    expect(fulfilment!.journal.filter((entry) => entry.kind === 'compensation').map((entry) => entry.name)).toEqual([
      '$compensate:reserve-stock',
      '$compensate:charge-payment',
    ]);
    expect(world.paymentProvider.refunds).toHaveLength(1);
    expect(world.inventory.stock.get(KIBBLE)).toBe(25);
  });

  // ...

  it('saves the order and starts its fulfilment together, or neither', async () => {
    // The transaction fails after start(): say, the next statement hits a constraint.
    const original = node.workflows.start.bind(node.workflows);
    vi.spyOn(node.workflows, 'start').mockImplementationOnce(async (...args) => {
      await original(...args); // the instance is created in the transaction...
      throw new Error('insert or update on table "order_lines" violates foreign key constraint');
    });
    await expect(place()).rejects.toThrow('violates foreign key constraint');

    // ...and rolled back with it: no order, no fulfilment for the worker to charge.
    expect(await world.db.select().from(orders)).toEqual([]);
    expect(await node.workflows.list()).toEqual([]);
    expect(await node.worker.drain()).toBe(0);
    expect(world.paymentProvider.requests).toBe(0);
  });
});
```

##### Test khả năng phục hồi sau crash <a id="test-crash-recovery"></a>

`createWorld()` tạo một database mới cho mỗi test. An toàn khi crash cần hai ứng dụng trên cùng database. Đóng một ứng dụng trong khi một step đang treo sẽ mô phỏng một lần crash: shutdown timeout hết hạn, và lease của process đã chết vẫn ở trong database cho tới khi hết hạn. Ứng dụng thứ hai tiếp quản sau đó:

```typescript
@@filename(test/crash-recovery.spec)
it('survives a crash in the middle of an order', async () => {
  const first = await bootApp(clock, world);
  const order = await first.orders.place({ userId: 'u_42', items: [{ productId: KIBBLE, quantity: 1, price: 2499 }] });

  // The process dies while reserving stock, after the payment provider charged the card.
  const reserve = vi.spyOn(world.inventory, 'reserve').mockImplementationOnce(() => new Promise<never>(() => {}));
  void first.worker.drain();
  await vi.waitFor(() => expect(reserve).toHaveBeenCalled());
  await first.close();

  // Another process on the same database takes over once the dead one's lease expires.
  const second = await bootApp(clock, world);
  clock.advance('31s');
  await second.worker.drain();

  expect(await second.workflows.getStatus(fulfilmentId(order.id))).toMatchObject({
    status: 'suspended',
    waits: [
      { signal: 'shipment.delivered', key: order.id },
      { signal: 'shipment.returned', key: order.id },
    ],
  });
  expect(world.paymentProvider.charges).toHaveLength(1); // journaled: not charged again
  expect(reserve.mock.calls.map(([, key]) => key)).toEqual([
    `order-${order.id}:reserve-stock`, // the attempt that died
    `order-${order.id}:reserve-stock`, // the retry, with the same key
  ]);
  await second.close();
});
```

Cùng cách thiết lập này bao phủ một lần crash giữa chừng các compensation: process tiếp theo replay journal để dựng lại danh sách compensation, bỏ qua những cái đã làm, và tiếp tục với phần còn lại. PGlite chỉ có một kết nối, nên nó không thể cho thấy hai worker chạy đua giành cùng một instance; các test store của bài hướng dẫn chạy các tình huống race của hợp đồng trên một PostgreSQL server, cùng với ba ứng dụng chia nhau 30 đơn hàng.

Để cho một test store riêng mà không cần override provider, hãy gọi `registerSource()` trên `moduleRef.get(WorkflowStorage)` trước `init()`, với `replace: true`: không có nó, lần đăng ký thứ hai sẽ throw. Tùy chọn `clock` nhận bất kỳ `WorkflowClock` nào, một object có `now()` trả về epoch mili giây, nên một test có thể điều khiển engine bằng một đồng hồ mà nó đã có sẵn.
#### Với CQRS <a id="with-cqrs"></a>

Nếu ứng dụng của bạn theo [recipe CQRS](/recipes/cqrs), command handler sẽ publish event, còn event handler và saga phản ứng với chúng. Chúng phản ứng trong bộ nhớ: một event được publish ngay trước khi process dừng sẽ không bao giờ tới được chúng, và một saga đang chờ event thứ hai sẽ quên event đầu tiên khi restart. Entry point `@nestjs/workflows/cqrs` cho phép chính các event khởi động và gửi signal cho workflow, một cách bền vững, trong khi code của bạn vẫn tiếp tục thực thi command và publish event. Nó hoạt động với `@nestjs/cqrs` 11 trở lên, được đăng ký bằng `CqrsModule.forRoot()` như trong recipe.

##### Map event sang workflow <a id="map-events-to-workflows"></a>

Ở đây quy trình giao hàng bắt đầu khi đơn hàng được đặt và thức dậy khi đơn vị vận chuyển báo việc giao hàng, như trước, nhưng các lời gọi workflow client đã biến mất khỏi code ứng dụng. Import `WorkflowsCqrsModule` cạnh `CqrsModule` và `WorkflowsModule`:

```typescript
@@filename(app.module)
import { CqrsModule } from '@nestjs/cqrs';
import { WorkflowsModule, WorkflowStorage } from '@nestjs/workflows';
import { WorkflowsCqrsModule } from '@nestjs/workflows/cqrs';

@Module({
  imports: [
    // ...DrizzleModule, as before
    CqrsModule.forRoot(),
    WorkflowsModule.forRoot(),
    WorkflowsCqrsModule, // mapped events start and signal workflows
  ],
  controllers: [OrdersController, CarrierWebhookController],
  providers: [
    // ...the store and the services, as before
    PlaceOrderHandler,
    MarkDeliveredHandler,
    ChargePaymentHandler,
    OrderFulfilmentWorkflow,
  ],
})
export class AppModule {}
```

Sau đó map các event trên class workflow. `@StartOn()` khởi động workflow khi một event được publish, và `@SignalOn()` gửi một trong các signal của nó:

```typescript
@@filename(orders/order-fulfilment.workflow)
import { SignalOn, StartOn } from '@nestjs/workflows/cqrs';
import { OrderDeliveredEvent } from './order-delivered.event.js';
import { OrderPlacedEvent } from './order-placed.event.js';

@Workflow('order-fulfilment')
@StartOn(OrderPlacedEvent, {
  id: (event) => fulfilmentId(event.order.id),
  input: (event) => event.order,
  // Lower runs first: express orders before standard ones.
  priority: (event) => (event.order.shipping === 'express' ? 1 : 2),
})
@SignalOn(OrderDeliveredEvent, {
  signal: shipmentDelivered,
  key: (event) => event.delivery.reference,
  id: (event) => event.delivery.trackingNumber,
  payload: (event) => event.delivery,
})
export class OrderFulfilmentWorkflow implements WorkflowRunner<Order, FulfilmentResult> {
  // ...the constructor, which now injects CommandBus too, and run()
}
```

`id` của `@StartOn()` là bắt buộc. Nó suy ra instance id từ business key, như `start()` làm, nên một event được publish hai lần sẽ tìm thấy instance mà lần đầu đã khởi động. Nó cũng nhận `priority`, `concurrencyKey` và `rateLimitKey` của `start()`, mỗi cái dưới dạng một giá trị hoặc một hàm nhận event: ở đây, đơn hàng hỏa tốc đi trước, như trước. `id` của `@SignalOn()` không bắt buộc, và trở thành `id` của signal: một event giao hàng được publish lại, chẳng hạn do webhook của đơn vị vận chuyển được retry, sẽ không lưu signal thứ hai. `input` mặc định là chính event, và `payload` của signal cũng vậy. TypeScript kiểm tra input so với `run()` và payload so với type của signal. Các event là những class thuần, như `OrderPlacedEvent` với tham số constructor `readonly order: Order`.

Command handler lưu đơn hàng và publish event trong một transaction:

```typescript
@@filename(orders/place-order.handler)
import { randomUUID } from 'node:crypto';
import { CommandHandler, EventBus, type ICommandHandler } from '@nestjs/cqrs';
import { InjectDrizzle } from '@nestjs/drizzle';
import type { Database } from '../database/drizzle.js';
import { orders } from '../database/schema.js';
import type { Order } from './order.js';
import { OrderPlacedEvent } from './order-placed.event.js';
import { PlaceOrderCommand } from './place-order.command.js';

@CommandHandler(PlaceOrderCommand)
export class PlaceOrderHandler implements ICommandHandler<PlaceOrderCommand> {
  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly eventBus: EventBus,
  ) {}

  async execute({ dto }: PlaceOrderCommand): Promise<Order> {
    const total = dto.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const order: Order = {
      id: randomUUID().slice(0, 8),
      userId: dto.userId,
      items: dto.items,
      shipping: dto.shipping ?? 'standard',
      total,
      status: 'placed',
    };

    return this.db.transaction(async (tx) => {
      await tx.insert(orders).values(order);
      // The transaction rides along as the dispatcher context: the fulfilment
      // this event starts commits with the order, or rolls back with it.
      await this.eventBus.publish(new OrderPlacedEvent(order), { transaction: tx });
      return order;
    });
  }
}
```

Tham số thứ hai của `publish()` và `publishAll()` là dispatcher context của CQRS. `WorkflowsCqrsModule` đọc thuộc tính `transaction` của nó và truyền cho `start()` và `signal()`, nên instance được tạo qua transaction của bạn, y như với tùy chọn `transaction`. Với TypeORM, dispatcher context mang `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó, dưới cùng thuộc tính `transaction`. `publish()` resolve khi các workflow đã được khởi động và gửi signal, và chỉ khi đó event mới tới được event handler và saga của bạn. Các event không được workflow nào map sẽ đi thẳng qua, không thay đổi. Các controller thực thi command: `POST /orders` thực thi `PlaceOrderCommand`, và webhook của đơn vị vận chuyển thực thi `MarkDeliveredCommand`, có `MarkDeliveredHandler` làm điều tương tự cho việc giao hàng: nó cập nhật trạng thái đơn hàng và publish `OrderDeliveredEvent` trong một transaction, nên trạng thái và signal cùng commit.

Module bọc bất kỳ publisher nào mà event bus đang có, nên một publisher bạn đặt bằng tùy chọn `eventPublisher` của `CqrsModule.forRoot()` (chẳng hạn một message broker) vẫn nhận mọi event, sau các workflow. Thay thế `EventBus.publisher` sau khi khởi động sẽ bỏ qua các workflow, nên việc khởi động sẽ thất bại nếu có gì đó làm vậy. Nó cũng thất bại khi một workflow map event nhưng `WorkflowsCqrsModule` không được import, khi một class map cùng một event hai lần, hoặc khi `@StartOn()` đưa key cho một workflow không có giới hạn theo key. Khi hai phiên bản của một workflow được đăng ký, `@StartOn()` của phiên bản cao nhất quyết định cái gì được khởi động, và một signal tới được các instance đang chờ của mọi phiên bản, được gửi một lần, nên các khai báo `@SignalOn()` của chúng phải thống nhất về payload và `id`: `publish()` sẽ reject khi chúng không thống nhất.

Các mapping nằm trên class workflow, nên mọi process publish các event đã được map đều đăng ký chúng, kể cả một process không chạy workflow nào, chẳng hạn một API chỉ đặt đơn hàng. Hãy đăng ký các class và store ở đó như thường lệ, và truyền `worker: false` cho `WorkflowsModule.forRoot()`: process này khởi động và gửi signal cho workflow, còn các process worker thực thi chúng. Một process import `WorkflowsCqrsModule` nhưng không đăng ký workflow nào map event sẽ không khởi động và không gửi signal gì cả, và log một cảnh báo lúc khởi động nói rõ điều đó.

##### Thực thi command từ step <a id="execute-commands-from-steps"></a>

Một step có thể thực thi command. Hãy truyền idempotency key của step kèm theo command, và để handler chuyển nó cho hệ thống mà nó gọi:

```typescript
@@filename(orders/order-fulfilment.workflow)
const charge = await ctx.step(
  'charge-payment',
  ({ idempotencyKey }) => this.commandBus.execute(new ChargePaymentCommand(order, idempotencyKey)),
  {
    retry: { attempts: 5, backoff: { delay: '2s' } },
    compensate: (charge, { idempotencyKey }) => this.paymentsService.refund(charge.chargeId, idempotencyKey),
  },
);
```

`ChargePaymentHandler` gọi `PaymentsService.charge()` với key, nên một step được retry không bao giờ trừ tiền hai lần, và kết quả của command được ghi journal như kết quả của mọi step. Một step cũng có thể publish event và gửi signal. Nó chạy ít nhất một lần, nên một event được publish từ một step có thể được publish lại. Một lần khởi động đã được map sẽ tìm thấy instance của nó, và một `start()` không có `id` trong một step cũng vậy: nó nhận một id suy ra từ `idempotencyKey` của step, tên workflow và vị trí của nó trong số các lần khởi động workflow đó của step, và một lần lặp lại sẽ trả về instance như lúc được khởi động lần đầu, kể cả input. Một signal được gửi từ bên trong một step, trực tiếp hoặc qua một event đã được map, chỉ được lưu một lần: không có `id` riêng, nó nhận một id suy ra từ `idempotencyKey` của step và vị trí của nó trong số các signal cùng tên và key của step. Hãy gửi chúng theo một thứ tự cố định. Một step gửi đồng thời nhiều signal cùng tên và key nên cho mỗi signal một `id` riêng.

##### Mỗi cách publish đảm bảo điều gì <a id="what-each-way-of-publishing-guarantees"></a>

Mức đảm bảo phụ thuộc vào cách, và thời điểm, event được publish:

| Event được publish thế nào | Việc khởi động hoặc gửi signal cho workflow | Nếu process chết hoặc một thao tác ghi thất bại |
| --- | --- | --- |
| Trong transaction của bạn, với transaction trong dispatcher context | Commit cùng các thao tác ghi của bạn, hoặc không commit gì cả | Không có gì bị làm dở dang. Một lần khởi động hoặc gửi signal thất bại sẽ reject `publish()`, và transaction của bạn rollback |
| Các event của một aggregate, từ `commit()` với transaction trong dispatcher context (`@nestjs/cqrs` 12.1 trở lên), hoặc với `publishAll()` trong transaction của bạn, như bên dưới | Commit cùng các thao tác ghi của bạn, hoặc không commit gì cả | Như trên: một lần khởi động hoặc gửi signal thất bại sẽ reject `commit()` hoặc `publishAll()`, và transaction của bạn rollback |
| Sau khi transaction của bạn commit | Được ghi trước khi `publish()` resolve | Một lần crash giữa lúc commit và lúc publish sẽ làm mất nó. Hãy publish lại từ một job đối soát: `id` của lần khởi động giúp việc đó an toàn, và id của signal cũng vậy, nếu `@SignalOn()` có đặt |
| Từ `commit()` không có transaction, của một aggregate được merge với `EventPublisher` | Được ghi bên ngoài transaction của bạn, ở chế độ nền trừ khi bạn await `commit()` (12.1 trở lên) | Mất khi crash nếu không có gì chờ nó, và bị bỏ lại khi transaction của bạn rollback. Các lỗi được đưa tới `UnhandledExceptionBus` và log, và module log một cảnh báo mỗi event class một lần |
| Từ `commit()` không có transaction, của một aggregate `@Publishable()` | Được ghi bên ngoài transaction của bạn, ở chế độ nền trừ khi bạn await `commit()` (12.1 trở lên) | Mất khi crash nếu không có gì chờ nó, và bị bỏ lại khi transaction của bạn rollback. Nếu không await, một lỗi là một unhandled promise rejection, mặc định sẽ làm dừng Node.js. Không có gì phân biệt nó với một `publish()` thông thường, nên không có cảnh báo |
| Từ một step của workflow | Một lần, bất kể step chạy bao nhiêu lần | Một step được retry không khởi động gì mới, và không lưu signal thứ hai |

Một aggregate được merge bằng `EventPublisher.mergeObjectContext()` hoặc `mergeClassContext()`, hoặc được gắn `@Publishable()`, publish các event của nó từ `commit()`. Với `@nestjs/cqrs` 12.1 trở lên, `commit()` nhận một dispatcher context, giống như `publish()`, và trả về những gì event bus trả về. Hãy truyền cho nó transaction của bạn và await nó trong transaction của command handler: khi đó các event của aggregate sẽ khởi động và gửi signal cho workflow trong transaction đó, và `commit()` reject khi một lần khởi động hoặc gửi signal thất bại, làm transaction rollback:

```typescript
await order.commit({ transaction: tx });
```

`commit()` xóa các event của aggregate khi nó giao chúng đi, trước khi các workflow được ghi, nên sau một lần thất bại, hãy chạy lại command với một aggregate vừa được load lại.

Không có dispatcher context, `commit()` publish bên ngoài transaction của bạn: các workflow vẫn khởi động, nhưng một lần rollback sẽ bỏ lại chúng, và một lần crash trước khi chúng được ghi sẽ làm mất chúng. Đừng để nó publish các event khởi động hoặc gửi signal cho workflow. Với `@nestjs/cqrs` 12.0 trở về trước, `commit()` không nhận context và không trả về gì để chờ, nên hãy tự publish các event của aggregate, trong transaction của command handler, rồi xóa chúng:

```typescript
await this.eventBus.publishAll(order.getUncommittedEvents(), { transaction: tx });
order.uncommit();
```

Module sẽ báo cho bạn khi một event đã được map tới từ `commit()` của một aggregate đã merge mà không có transaction: ở lần đầu tiên, nó log một cảnh báo nêu tên event class. Các event của một aggregate `@Publishable()` tới mà không có dispatcher context nào, giống như một lời gọi `publish()` thông thường, nên chúng không nhận cảnh báo.

Event handler và saga của bạn vẫn nhận mọi event, trong bộ nhớ, sau các workflow. Bên trong một transaction, chúng chạy trước khi transaction commit, như chúng vẫn luôn làm, nên chúng có thể phản ứng với một event mà sau đó transaction của nó lại rollback. Một saga biến một event thành một command có thể giữ nguyên là saga. Một saga ghi nhớ event, chẳng hạn một saga chờ thanh toán sau khi đặt đơn và bỏ cuộc sau một giờ, thực chất là một workflow trá hình: hãy khởi động workflow từ event đầu tiên, map các event còn lại sang signal, và để `waitForSignal()` với một `timeout` lo việc chờ đợi, một cách bền vững.

#### Chuẩn bị cho production <a id="prepare-for-production"></a>

##### Giữ journal ngắn gọn <a id="keep-journals-short"></a>

Mỗi lần thực thi đều load toàn bộ journal của instance và replay `run()` từ đầu. Một quy trình có số step cố định sẽ giữ journal nhỏ, nhưng một vòng lặp có một step hoặc một sleep mỗi vòng sẽ thêm entry chừng nào nó còn chạy, và mỗi lần thực thi lại chậm hơn. Module cảnh báo khi một journal đạt 1.000 entry hoặc 1 MB: mỗi instance một lần, khi nó vượt ngưỡng, trong log và dưới dạng event `journal-large`. Khi nó chứa 10.000 entry hoặc 10 MB, instance thất bại trước khi ghi thêm entry nào: các compensation của nó chạy, chúng vẫn có thể ghi entry của mình, và nó kết thúc ở trạng thái `failed` với một `WorkflowJournalLimitError`. Tùy chọn `journal` của module thay đổi cả hai ngưỡng. Hãy định cỡ chúng theo workflow thông thường dài nhất của bạn với dư địa thoải mái, và đặt một giới hạn thành `Infinity` để tắt nó:

```typescript
WorkflowsModule.forRoot({
  journal: { warnEntries: 500, maxEntries: 5_000 },
});
```

Một quy trình kéo dài mãi mãi, chẳng hạn một gói đăng ký cát vệ sinh hàng tháng, sẽ tiếp tục trong một instance mới thay vào đó. Sau một năm giao hàng, step cuối cùng của nó khởi động instance cho năm tiếp theo, và instance hiện tại hoàn tất:

```typescript
async run(ctx: WorkflowContext, subscription: Subscription) {
  for (let month = 1; month <= 12; month++) {
    await ctx.step(`ship-${month}`, ({ idempotencyKey }) => this.subscriptionsService.ship(subscription, idempotencyKey));
    await ctx.sleep(`wait-${month}`, '30d');
  }

  const next = { ...subscription, year: subscription.year + 1 };
  return ctx.step('continue', async () => {
    const { id } = await this.workflowClient.start(LitterSubscriptionWorkflow, next, {
      id: `subscription-${subscription.id}-${next.year}`,
    });
    return id;
  });
}
```

Step khởi động instance tiếp theo một lần: một step được retry sẽ tìm thấy instance mà nó đã khởi động. Instance mới có journal mới và id riêng, nên năm đã kết thúc vẫn đọc được cho tới khi chính sách lưu trữ dọn dẹp nó. Tiếp tục dưới cùng id sẽ đòi hỏi mọi store phải thay thế journal tại chỗ, dưới lease của worker; một id mới không đòi hỏi gì mới từ store. Khi mỗi vòng độc lập với nhau, một lịch chạy còn đơn giản hơn: nó khởi động mỗi lần chạy một instance, mỗi instance có journal riêng, như [Chạy workflow theo lịch](/reliability/workflows#run-workflows-on-a-schedule) trình bày.

##### Mã hóa những gì workflow lưu trữ <a id="encrypt-what-workflows-store"></a>

Store giữ những gì workflow của bạn xử lý: đơn hàng, các lần trừ tiền, việc giao hàng. Để những thứ đó không đọc được với bất kỳ ai đọc database hoặc các bản backup của nó, hãy cho module một **payload codec**. `AesGcmPayloadCodec` mã hóa bằng AES-256-GCM, với các khóa từ secret manager của bạn. Tạo nó trong factory của module, factory này chạy lúc khởi động:

```typescript
@@filename(app.module)
import { AesGcmPayloadCodec, WorkflowsModule, WorkflowStorage } from '@nestjs/workflows';

WorkflowsModule.forRootAsync({
  useFactory: () => ({
    worker: {
      // ...as before
    },
    // Encrypts what the store keeps. The key comes from your secret manager, through the environment.
    codec: new AesGcmPayloadCodec({
      keys: { '2026-09': process.env.WORKFLOWS_KEY_2026_09! },
      current: '2026-09',
    }),
  }),
}),
```

Một khóa là 32 byte ngẫu nhiên ở dạng base64 (`openssl rand -base64 32`), dưới một id do bạn chọn. Một khóa bị thiếu (một biến môi trường chưa đặt), không phải base64 hoặc không đủ 32 byte sẽ làm việc khởi động thất bại, kèm một lỗi nêu tên nó.

- **Những gì nó mã hóa**: mọi thứ chứa dữ liệu của bạn. Input và output, kết quả step và checkpoint, payload của signal, custom status, lý do hủy, input của lịch chạy, và message cùng stack của lỗi. Mỗi payload được mã hóa dưới một khóa được suy ra riêng cho nó, với vị trí lưu trữ của nó làm dữ liệu xác thực, nên một payload bị thay đổi, hoặc bị chuyển sang instance hay field khác, sẽ không giải mã được thay vì bị đọc. Các payload từ 1 KiB trở lên được nén trước. Nếu payload trộn lẫn secret với dữ liệu do kẻ tấn công chọn, và kẻ tấn công có thể thấy kích thước được lưu, hãy tắt việc nén bằng `compress: false`.
- **Những gì vẫn đọc được**, vì store cần so khớp, lọc, sắp xếp hoặc đếm dựa trên chúng: id, tên và phiên bản workflow, trạng thái, tên và key của signal, key concurrency và rate-limit, độ ưu tiên, liên kết tới cha và lịch chạy, tên entry của journal, và mọi thời điểm. Lỗi giữ nguyên tên của chúng, chẳng hạn `StepFailedError`. Vì vậy hãy chọn id và key không nói lên điều gì nhạy cảm: `order-71e1973d`, chứ không phải một địa chỉ email. Ở đây concurrency key là id khách hàng, đọc được trong `concurrency_key`.
- **Dạng lưu trữ**: `$wf1:aes-256-gcm:2026-09.` theo sau là ciphertext, một chuỗi trong cùng các cột JSON, nên store không cần thay đổi gì.

**Xoay vòng khóa.** Thêm một khóa, và đặt nó làm `current`. Một payload được giải mã bằng khóa đã mã hóa nó, và mọi thứ được ghi từ đó trở đi dùng khóa hiện tại. Không có gì được mã hóa lại hàng loạt: payload được ghi lại khi các instance tiến triển, và payload cũ biến mất theo các lần dọn dẹp. Vì vậy hãy giữ một khóa trong danh sách chừng nào mọi thứ nó đã mã hóa vẫn có thể được đọc: các instance chưa kết thúc, các signal chưa bị dọn dẹp, và các lịch chạy được lưu dưới khóa đó. Input của một lịch chạy được khai báo sẽ được lưu lại dưới khóa hiện tại lúc khởi động và mỗi phút, nhưng input của một lịch chạy được upsert thì chỉ được lưu lại ở lần `upsert()` tiếp theo: `pause()` và `resume()` giữ nguyên nó như đã lưu.

```typescript
codec: new AesGcmPayloadCodec({
  keys: {
    '2027-03': process.env.WORKFLOWS_KEY_2027_03!,
    '2026-09': process.env.WORKFLOWS_KEY_2026_09!,
  },
  current: '2027-03',
}),
```

Một instance có payload cần một khóa không có trong danh sách sẽ không đọc được: `getStatus()` throw một lỗi nêu tên khóa, `list()` hiển thị instance mà không có payload, và các worker để yên nó cho tới khi khóa quay lại, rồi mới chạy nó.

Thêm một codec không làm hỏng instance nào đang chạy: các payload được lưu trước đó được đọc nguyên trạng, và các thao tác ghi mới được mã hóa. Đó cũng là giới hạn của việc bảo vệ. Ai đó có quyền ghi vào database có thể thay một payload đã mã hóa bằng một payload thuần, và khiến nó được đọc: codec bảo vệ những gì nó đã mã hóa khỏi việc bị đọc và bị sửa, chứ không bảo vệ database khỏi những người có quyền ghi vào nó.

Một codec của riêng bạn implement `WorkflowPayloadCodec`: một `id`, được lưu cùng mỗi payload, và `encode()` cùng `decode()`, nhận giá trị và vị trí lưu trữ của nó. Truyền class của nó cho `codec` để Nest tạo nó, với các dependency từ các global module, chẳng hạn một KMS client. Để thay một codec, hãy liệt kê codec mới trước và codec cũ sau nó: codec đầu tiên mã hóa, và mỗi payload được giải mã bằng codec có id mà nó mang.

##### Checklist cho production <a id="production-checklist"></a>

- Truyền `idempotencyKey` cho mọi side effect, kể cả compensation. Step chạy ít nhất một lần.
- Cho signal một `id` khi bên gửi của nó có thể chạy hai lần, chẳng hạn một webhook được bên gửi retry hoặc một message consumer. Signal được gửi từ một step tự động có id.
- Gọi `enableShutdownHooks()`, và giữ `shutdownTimeout` dưới grace period của platform (mặc định 30 giây trên Kubernetes).
- Chọn `leaseDuration` một cách có cân nhắc. Đó là khoảng thời gian các instance của một process bị crash phải chờ trước khi process khác tiếp quản, và một process có event loop bị treo lâu hơn mức đó sẽ mất các instance của nó. Việc hết hạn lease so sánh các timestamp do các host khác nhau ghi, nên hãy giữ đồng hồ của chúng được đồng bộ (NTP) và `leaseDuration` lớn hơn hẳn mọi độ lệch giữa chúng.
- Đăng ký một store trên database của bạn: `PostgresWorkflowStore`, `MySqlWorkflowStore`, hoặc một store của riêng bạn. Trong bộ nhớ, hoặc trong một file trên ổ đĩa của container, trạng thái chết theo instance: store trong bộ nhớ mặc định mất mọi đơn hàng đang chạy khi restart, và việc khởi động sẽ từ chối nó trong production. Chạy contract suite trên store của riêng bạn trong CI, trên database của nó, với `concurrent: true`.
- Áp dụng migration của store trước khi một phiên bản mới khởi động, bằng `npx @nestjs/workflows migrate` hoặc công cụ migration của bạn, và kiểm tra chúng trong CI bằng `npx @nestjs/workflows status`. Với `NODE_ENV=production`, store không migrate lúc khởi động: một schema chậm phiên bản sẽ làm việc khởi động thất bại.
- Chạy bao nhiêu worker tùy thích, trên bao nhiêu host tùy thích. Định cỡ connection pool cho chúng: mỗi instance đang chạy gia hạn lease và ghi journal qua pool, và mỗi lần poll giữ một kết nối cho lần claim của nó.
- Khởi động workflow trong transaction ghi các dòng nghiệp vụ của chúng (`transaction: tx`, hoặc `EntityManager` với TypeORM), để một lần crash giữa hai bước không thể để lại một đơn hàng không có gì xử lý. Hãy truyền transaction, không bao giờ truyền root database. Với CQRS, hãy publish các event bên trong transaction đó, với transaction trong dispatcher context.
- Giữ các transaction gửi signal ngắn gọn: signal và các lần tạm dừng đăng ký wait xếp hàng phía sau chúng. Trên PostgreSQL, giữ chúng ở READ COMMITTED, và isolation mặc định của database cũng vậy: store từ chối một level chặt hơn. Trên MySQL, giữ chúng ở REPEATABLE READ hoặc READ COMMITTED, và chạy lại một transaction khi nó thất bại do deadlock (lỗi 1213).
- Xác minh chữ ký của webhook, và chỉ trả về `2xx` sau khi transaction chứa signal đã commit.
- Cảnh báo khi có instance cần người xử lý. `compensation_failed` nghĩa là một lần hoàn tác đã bỏ cuộc giữa chừng, và một instance `failed` với `WorkflowNonDeterminismError` nghĩa là một lần deploy đã làm hỏng replay. `WorkflowClient.list()` tìm ra chúng, và [Ý nghĩa của từng trạng thái](/reliability/workflows#what-each-status-means) cho biết cần làm gì với từng cái: `retry()` khi đã sửa nguyên nhân, hoặc `delete()`. Cho log và metric, hãy subscribe `WorkflowEvents.events$`, hoặc các diagnostics channel `nestjs:workflows:*` mà các công cụ tracing đọc được mà không cần Nest; [Event](/reliability/workflows#events) map chúng lên một trace.
- Đánh dấu điểm không thể quay lại bằng `ctx.commit()`. Trước nó, mọi lần thất bại và hủy đều hoàn tác các step đã hoàn tất.
- Dọn dẹp các instance đã kết thúc mỗi đêm bằng `purge()`, trên một instance của ứng dụng, như [Dọn dẹp các instance đã kết thúc](/reliability/workflows#purge-finished-instances) trình bày. Giữ `olderThan` của nó dài hơn khoảng thời gian gửi lại của mọi bên gửi: `id` của một signal chỉ khử trùng lặp chừng nào signal còn được lưu.
- Giữ journal ngắn gọn: giới hạn các vòng lặp, và tiếp tục một vòng lặp không bao giờ kết thúc trong một instance mới ([Giữ journal ngắn gọn](/reliability/workflows#keep-journals-short)). Cho một quy trình phải bỏ cuộc ở một thời điểm nào đó một run timeout ([Timeout cho toàn bộ workflow](/reliability/workflows#time-out-the-whole-workflow)).
- Định cỡ giới hạn concurrency và rate theo những gì các step gọi tới, và deploy thay đổi về chúng tới mọi process: mỗi process áp dụng các giới hạn của code mà nó chạy. Khi một số instance đã có độ ưu tiên, hãy cho các instance còn lại độ ưu tiên nữa, vì các instance không có độ ưu tiên sẽ đi trước.
- Deploy một lịch chạy được khai báo tới mọi process đăng ký workflow của nó: chỉ các worker có code khai báo nó mới khởi động các lần chạy của nó. Một lịch chạy bị một lần deploy loại bỏ, hoặc bị xóa workflow, vẫn tiếp tục khởi động trên các process của code cũ, và biến mất khoảng năm phút sau khi process cuối cùng trong số đó dừng. Đặt `missed` cho những công việc không được bỏ qua khi không có worker nào hoạt động vào thời điểm của nó. Nếu các process của code khác dùng chung database, đừng để một lịch chạy không có worker nào có code khai báo nó trong năm phút: chúng sẽ xóa nó, và nó bắt đầu lại khi có một worker như vậy khởi động.
- Mã hóa những gì store lưu giữ bằng một codec, với các khóa từ secret manager của bạn ([Mã hóa những gì workflow lưu trữ](/reliability/workflows#encrypt-what-workflows-store)). Giữ một khóa cũ trong danh sách chừng nào mọi thứ nó đã mã hóa còn có thể được đọc, và chọn id và key không nói lên điều gì nhạy cảm: chúng vẫn đọc được.
#### Tham khảo <a id="reference"></a>

##### Tùy chọn của module <a id="module-options"></a>

`WorkflowsModule.forRoot()` nhận các tùy chọn sau; `forRootAsync()` nhận chúng từ `useFactory`, `useClass` hoặc `useExisting` (một class implement `WorkflowsOptionsFactory`). Token của các tùy chọn là `WORKFLOWS_MODULE_OPTIONS`. Store không phải là một tùy chọn: hãy đăng ký nó với `WorkflowStorage`, như trong [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database).

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `worker.enabled` | `true` | Chạy vòng lặp polling. `worker: false` là cách viết tắt cho `enabled: false`: process khởi động, gửi signal và xem workflow, còn `WorkflowWorker.drain()` chạy các instance tới hạn khi được gọi |
| `worker.id` | `hostname:pid:random` | Tên của worker, hiển thị dưới dạng `leaseOwner` của instance |
| `worker.concurrency` | `10` | Số instance mà process này thực thi cùng lúc |
| `worker.pollInterval` | `'1s'` | Tần suất tìm các instance tới hạn. Một lời gọi `start()` hoặc `signal()` ở local sẽ đánh thức vòng lặp ngay lập tức |
| `worker.leaseDuration` | `'30s'` | Thời gian một lần claim còn hiệu lực nếu không gia hạn, tức là khoảng thời gian một process bị crash còn giữ các instance của nó |
| `worker.heartbeatInterval` | Một phần ba `leaseDuration` | Tần suất một instance đang chạy gia hạn lease |
| `worker.shutdownTimeout` | `'10s'` | Thời gian quá trình shutdown chờ các lần thực thi đang chạy trước khi trả chúng lại |
| `retry` | 3 lần thử, `'1s'` nhân đôi tới `'5m'`, không có jitter | Mặc định cho mọi step. Xem các field retry bên dưới |
| `journal.warnEntries`, `journal.warnBytes` | `1000`, `1000000` | Khi chạm một trong hai, log một cảnh báo và phát ra `journal-large`, mỗi instance một lần ([Giữ journal ngắn gọn](/reliability/workflows#keep-journals-short)) |
| `journal.maxEntries`, `journal.maxBytes` | `10000`, `10000000` | Khi chạm một trong hai, làm instance thất bại với `WorkflowJournalLimitError` trước khi nó ghi thêm entry. `Infinity` tắt việc kiểm tra |
| `clock` | Đồng hồ hệ thống | Một `WorkflowClock`. Các test truyền một `ManualWorkflowClock` ([Test với đồng hồ thủ công](/reliability/workflows#test-with-a-manual-clock)) |
| `allowInMemoryStorage` | `false` | Với `NODE_ENV=production` và không có store được đăng ký, việc khởi động sẽ thất bại; `true` vẫn chạy trên store trong bộ nhớ |
| `codec` | Không có | Một `WorkflowPayloadCodec`, class của nó, hoặc một danh sách: codec đầu tiên mã hóa, và mỗi codec giải mã các payload mà nó đã mã hóa ([Mã hóa những gì workflow lưu trữ](/reliability/workflows#encrypt-what-workflows-store)) |
| `isGlobal` | `true` | Đăng ký module ở phạm vi global. Đặt ở cấp ngoài cùng của `forRoot()` và `forRootAsync()` |

Một tùy chọn `retry` (của module, `retry` hoặc `compensateRetry` của một step) là một số lần thử, `false` cho một lần thử duy nhất, hoặc một object với các field sau. `retry` của một step được merge lên trên của module theo từng field.

| Field | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `attempts` | `3` | Tổng số lần thử, tính cả lần đầu |
| `backoff.delay` | `'1s'` | Thời gian chờ trước lần retry đầu tiên |
| `backoff.factor` | `2` | Mức tăng sau mỗi lần retry; `1` giữ thời gian chờ không đổi |
| `backoff.maxDelay` | `'5m'` | Mức trần cho một lần chờ |
| `backoff.jitter` | `'none'` | `'full'` (từ không tới toàn bộ thời gian chờ), `'equal'` (từ một nửa tới toàn bộ) hoặc `'none'` |
| `retryIf` | Mọi lỗi | `(error, attempt) => boolean`: `false` làm step thất bại ngay lập tức |

`backoff` cũng có thể là một hàm, `(attempt, error) => duration`. Một `NonRetryableStepError` không bao giờ được retry.

##### Store PostgreSQL <a id="postgresql-store"></a>

`new PostgresWorkflowStore(options, workflowStorage)`, từ `@nestjs/workflows/postgres`, nhận các tùy chọn sau:

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `executor` | Bắt buộc | Cách store tiếp cận database: `fromDrizzle(db)`, `fromTypeOrm(dataSource)`, `fromPg(pool)`, `fromPrisma(prisma, options)` hoặc `fromKysely(db)` |
| `schema` | `'nest_workflows'` | Schema chứa các bảng của nó, được migration đầu tiên tạo ra. Chữ cái, chữ số và dấu gạch dưới, không bắt đầu bằng chữ số, tối đa 63 ký tự |
| `migrate` | `true`, trừ khi `NODE_ENV=production` | Áp dụng các migration còn chờ khi ứng dụng khởi động. Với `false`, việc khởi động thất bại với `WorkflowSchemaError` khi schema còn chậm phiên bản |

Mỗi executor nhận database client của bạn, và loại transaction object riêng của nó, thứ mà `start()` và `signal()` sau đó nhận làm `transaction`:

| Executor | Nhận | Transaction object |
| --- | --- | --- |
| `fromDrizzle(db)` | Một Drizzle PostgreSQL database, với bất kỳ driver nào | `tx` mà `db.transaction()` đưa cho callback của nó |
| `fromTypeOrm(dataSource)` | Một `DataSource` có type `postgres`, hoặc `manager` của nó | `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó, hoặc một `QueryRunner` sau `startTransaction()` |
| `fromPg(pool)` | Một `Pool` của node-postgres, hoặc một `Client` đã kết nối | Một client, chẳng hạn từ `pool.connect()`, sau `BEGIN` |
| `fromPrisma(prisma, options)` | Một Prisma client trên PostgreSQL, qua một driver adapter như `@prisma/adapter-pg` hoặc engine của Prisma. `maxWait` (mặc định `'10s'`) và `timeout` (mặc định `'1m'`) giới hạn các transaction riêng của store | Transaction client mà `prisma.$transaction()` đưa cho callback của nó |
| `fromKysely(db)` | Một instance `Kysely` với dialect PostgreSQL. Các câu lệnh của store bỏ qua plugin của nó | Transaction mà `db.transaction().execute()` đưa cho callback của nó, hoặc một controlled transaction |

Method `migrate()` của store áp dụng ngay các migration còn chờ, bất kể tùy chọn `migrate` nói gì, và resolve với các phiên bản mà nó đã áp dụng. `PostgresWorkflowStore.migrationSql()` trả về SQL của chúng, kèm phần ghi chép phiên bản. Các tùy chọn của nó là `schema`, phiên bản bắt đầu `from` (mặc định `0`, một database mới) và phiên bản đích `to` (mặc định: phiên bản mà package cần), và `statementBreakpoints`, tách các câu lệnh bằng các dòng `--> statement-breakpoint` của drizzle-kit. Từ phiên bản 0, nó bắt đầu bằng `CREATE SCHEMA IF NOT EXISTS`, câu này cần quyền CREATE trên database: hãy bỏ nó đi nếu ai đó đã tạo schema cho bạn. `PostgresWorkflowStore.schemaVersion` là phiên bản mà package cần. Phiên bản riêng của một schema là phiên bản cao nhất trong bảng `migrations` của nó.

##### Store MySQL <a id="mysql-store"></a>

`new MySqlWorkflowStore(options, workflowStorage)`, từ `@nestjs/workflows/mysql`, chạy trên MySQL 8.4 LTS và 9.x, và nhận các tùy chọn sau:

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `executor` | Bắt buộc | Cách store tiếp cận database: `fromDrizzle(db)`, `fromTypeOrm(dataSource)`, `fromMysql2(pool)`, `fromPrisma(prisma, options)` hoặc `fromKysely(db)`, từ `@nestjs/workflows/mysql` |
| `schema` | `'nest_workflows'` | Phần đầu trong tên các bảng của nó (`nest_workflows_instances`...), trong database của kết nối. Chữ thường, chữ số và dấu gạch dưới, không bắt đầu bằng chữ số, tối đa 40 ký tự |
| `migrate` | `true`, trừ khi `NODE_ENV=production` | Áp dụng các migration còn chờ khi ứng dụng khởi động, từng câu lệnh một. Với `false`, việc khởi động thất bại với `WorkflowSchemaError` khi các bảng còn chậm phiên bản |

| Executor | Nhận | Transaction object |
| --- | --- | --- |
| `fromDrizzle(db)` | Một Drizzle MySQL database (`drizzle-orm/mysql2`) | `tx` mà `db.transaction()` đưa cho callback của nó |
| `fromTypeOrm(dataSource)` | Một `DataSource` có type `mysql`, hoặc `manager` của nó | `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó, hoặc một `QueryRunner` sau `startTransaction()` |
| `fromMysql2(pool)` | Một pool mysql2, hoặc một connection | Một connection, chẳng hạn từ `pool.getConnection()`, sau `beginTransaction()` |
| `fromPrisma(prisma, options)` | Một Prisma client trên MySQL, qua `@prisma/adapter-mariadb`. `maxWait` (mặc định `'10s'`) và `timeout` (mặc định `'1m'`) giới hạn các transaction riêng của store, kể cả `migrate()`: hãy tăng `timeout` cho nó, hoặc migrate từ command line | Transaction client mà `prisma.$transaction()` đưa cho callback của nó |
| `fromKysely(db)` | Một instance `Kysely` với `MysqlDialect`. Các câu lệnh của store bỏ qua plugin của nó | Transaction mà `db.transaction().execute()` đưa cho callback của nó, hoặc một controlled transaction |

Lúc khởi động, store kiểm tra server và kết nối: phải là MySQL, không phải MariaDB; `sql_mode` phải strict (`STRICT_TRANS_TABLES`, mặc định của MySQL), nếu không MySQL sẽ cắt bớt một giá trị quá dài so với cột của nó; và phải có một database, nơi đặt các bảng của nó. Nó đếm số dòng mà một câu update khớp, nên hãy giữ cờ `FOUND_ROWS` của mysql2, vốn được bật mặc định (adapter của Prisma gọi nó là `foundRows`), và để SQL mode `NO_BACKSLASH_ESCAPES` ở trạng thái tắt.

Id, tên và key của nó là các cột có index với độ dài giới hạn, tính theo ký tự:

| Key | Tối đa |
| --- | --- |
| Một instance id, kể cả của một child (mặc định là `<parent id>/<workflow>#<n>`) và của một instance do lịch chạy khởi động (`<schedule id>@<time>`) | 255 |
| Một schedule id | 230 |
| Tên của một workflow, tên, `key` và `id` của một signal, một concurrency key, một rate-limit key | 255 |
| Tên của một entry trong journal: của một step, sleep hoặc wait, và những tên mà engine thêm vào, như `$compensate:<step>` và `$child:<child id>` | 512 |

Một giá trị dài hơn sẽ thất bại với một `RangeError` nêu tên nó, trước mọi câu SQL. `migrate()` và `MySqlWorkflowStore.schemaVersion` giống như của store PostgreSQL. `MySqlWorkflowStore.migrationSql()` nhận cùng các tùy chọn và trả về các câu lệnh cần áp dụng theo thứ tự, mỗi câu một lần, còn `MySqlWorkflowStore.migrationStatements()` nhận `schema`, `from` và `to` và trả về chúng mỗi chuỗi một câu, cho một công cụ chạy mỗi lời gọi một câu lệnh. Phiên bản riêng của một schema là phiên bản cao nhất được áp dụng trong bảng `<schema>_migrations` của nó.

##### Command line

`npx @nestjs/workflows` áp dụng migration của cả hai store từ một bước deploy hoặc kiểm tra chúng trong CI. Nó nhận `--url` (mặc định `DATABASE_URL`) và `--schema` (mặc định `nest_workflows`). URL quyết định store: `postgres://` hoặc `postgresql://` cho PostgreSQL, cần cài `pg`, và `mysql://` cho MySQL, cần `mysql2`.

| Lệnh | Làm gì |
| --- | --- |
| `migrate` | Áp dụng các migration còn chờ, như `migrate: true` làm lúc khởi động |
| `status` | In ra phiên bản của schema và phiên bản mà package cần, và thoát với mã 1 khi schema còn chậm phiên bản |
| `sql` | In ra SQL của `migrationSql()`, từ `--from` tới `--to`, không cần database: của PostgreSQL, hoặc của MySQL với `--dialect mysql`. `--statement-breakpoints` tách các câu lệnh cho drizzle-kit |

##### Hợp đồng của store <a id="the-store-contract"></a>

`PostgresWorkflowStore` và `MySqlWorkflowStore` implement interface `WorkflowStore`. Với một database khác, hãy implement nó trong một provider của riêng bạn. JSDoc của từng method trên `WorkflowStore` cho biết method đó phải làm gì, và mỗi quy tắc ngăn chặn tình huống race nào.

**Đăng ký.** Store là một singleton provider bình thường gọi `registerSource(this)` trên `WorkflowStorage` (có thể inject) trong constructor của nó. Registry kiểm tra cấu trúc ngay lập tức, từ chối lần đăng ký thứ hai trừ khi truyền `replace: true`, và bị khóa khi `WorkflowsModule` khởi tạo, đồng thời log ra store đang dùng. Một provider request-scoped, một provider trong lazy-loaded module, hoặc một lifecycle hook sẽ đăng ký quá muộn, và throw. Không có gì được đăng ký, module dùng `InMemoryWorkflowStore`: một lần restart sẽ mất mọi instance đang chạy, và hai process không dùng chung chúng. Nó cũng không thể tham gia vào transaction của bạn, nên `start()` và `signal()` với `transaction` sẽ ghi ngay lập tức, và nó log một cảnh báo ở lần đầu tiên. Với `NODE_ENV=production`, việc khởi động sẽ thất bại thay vào đó, kèm một lỗi nêu tên các store của package và interface cần implement, trừ khi bạn đặt `allowInMemoryStorage: true` trong tùy chọn của module.

**Tính nguyên tử.** Worker, signal, cancel, retry, purge và lịch chạy chạy đua với nhau qua store. `claim()` không bao giờ được cho hai worker cùng giữ lease một instance, `write()` chỉ được ghi khi lease của worker còn hiệu lực, và `signal()` không được lọt qua một instance đang tạm dừng. Vì vậy mọi method thay đổi trạng thái đều là một câu lệnh có điều kiện, hoặc một transaction với lock đúng, không bao giờ là một lần đọc theo sau là một lần ghi. Có hai method không bắt buộc: `createInTransaction()` và `signalInTransaction()`, được `start()` và `signal()` gọi với transaction object của bạn, nguyên vẹn. Chúng phải ghi qua nó, và từ chối root handle, vì các thao tác ghi trên đó sẽ tự commit riêng. Trên PostgreSQL, `signalInTransaction()` còn từ chối một transaction không phải READ COMMITTED, vì việc đánh thức của nó có thể bỏ lỡ những wait được commit sau snapshot của nó.

**Hãy test nó** bằng suite từ `@nestjs/workflows/testing`. `workflowStoreContract()` trả về hợp đồng dưới dạng các test case, kể cả các tình huống race, dùng được với mọi test runner. Các test của bài hướng dẫn chạy nó trên `PostgresWorkflowStore` qua Drizzle, và trên `MySqlWorkflowStore` với MySQL, giống như bạn sẽ làm với store của mình, với một hàm trả về store trên các bảng đã được làm trống:

```typescript
@@filename(test/drizzle-workflow.store.spec)
// The concurrency cases run too; with one connection, PGlite runs them one statement at a time.
const cases = workflowStoreContract(() => freshStore(db), { concurrent: true, transaction: (work) => db.transaction(work) });
for (const c of cases) {
  it(c.name, c.run);
}
```

Với `concurrent: true`, suite cho các lần claim (kể cả dưới giới hạn), signal, lần tạm dừng, thao tác ghi cuối cùng của child, cancel và terminate, retry, purge và lần claim lịch chạy chạy đua với nhau: ví dụ 60 signal với 60 lần tạm dừng. Hãy chạy nó trên một database server có connection pool nữa, nơi một store thiếu lock đúng sẽ thất bại. Với `transaction`, một hàm mở một transaction của bạn, các case của hai method không bắt buộc cũng sẽ chạy. Các test riêng của package chạy suite trên một store Drizzle được viết tay, làm bằng chứng rằng một store được viết theo interface sẽ vượt qua nó.

Các package xây trên engine, chẳng hạn một job queue, lấy các phần không phụ thuộc vào lưu trữ của nó (đồng hồ, retry, payload codec, giới hạn, vòng lặp worker có lease và lịch chạy) từ `@nestjs/workflows/core`; ứng dụng không cần dùng nó.

##### Tùy chọn của các lời gọi <a id="call-options"></a>

| Lời gọi | Tùy chọn | Được giải thích trong |
| --- | --- | --- |
| `@Workflow(name, options)` | `version` (mặc định `1`), `timeout` (một run timeout; mặc định không có), `concurrency` (`limit`, và một hàm `key` cho giới hạn theo key; mỗi loại một cái trong một mảng), `rateLimit` (`max`, `duration`, và một hàm `key`; mỗi loại một cái trong một mảng), `schedules` (xem tùy chọn lịch chạy bên dưới) | [Deploy thay đổi một cách an toàn](/reliability/workflows#deploy-changes-safely), [Timeout cho toàn bộ workflow](/reliability/workflows#time-out-the-whole-workflow), [Giới hạn số lượng chạy cùng lúc](/reliability/workflows#limit-how-many-run-at-once), [Chạy workflow theo lịch](/reliability/workflows#run-workflows-on-a-schedule) |
| `ctx.step(name, fn, options)` | `retry`, `timeout`, `heartbeatTimeout`, `compensate`, `compensateRetry` | [Viết workflow](/reliability/workflows#write-the-workflow), [Step chạy lâu](/reliability/workflows#long-running-steps) |
| `ctx.waitForSignal(name, signal, options)` | `key`, `timeout` (resolve `null` khi hết hạn), `match` (một bộ lọc thuần trên payload) | [Chờ webhook giao hàng](/reliability/workflows#wait-for-the-delivery-webhook) |
| `ctx.sleep(name, duration)` | Một khoảng thời gian, hoặc một object có `until` (một `Date` hoặc epoch mili giây) | [Ngủ một tuần, rồi nhờ đánh giá](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review) |
| `ctx.waitForAny(name, conditions)` | Một object chứa các điều kiện: `ctx.signalWait(signal, options)` (`key`, `match`), `ctx.timer(duration)` (một khoảng thời gian, hoặc một object có `until`), hoặc handle của một child. Resolve với `key` và `value` của bên thắng | [Chờ thứ nào tới trước](/reliability/workflows#wait-for-whichever-comes-first) |
| `ctx.startChild(workflow, input, options)`, `ctx.executeChild(workflow, input, options)` | `id` (mặc định gồm id của cha, tên workflow và một số đếm, như `order-71e1973d/shipment#1`), `version`, `timeout`, `parentClose` (`'cancel'`, `'terminate'` hoặc `'abandon'`; mặc định `'cancel'`), `priority` (mặc định là của cha), `concurrencyKey`, `rateLimitKey` | [Khởi động child workflow](/reliability/workflows#start-child-workflows) |
| `ctx.setStatus(status)` | Một giá trị JSON tối đa 16 KiB, hoặc `undefined` để xóa nó | [Báo cáo trạng thái](/reliability/workflows#report-its-status) |
| `ctx.schedule` | Không phải lời gọi: `id` của lịch chạy và thời điểm `at` của lần chạy đã khởi động instance, hoặc `null` | [Chạy workflow theo lịch](/reliability/workflows#run-workflows-on-a-schedule) |
| `WorkflowClient.start(workflow, input, options)` | `id` (mặc định là một UUID ngẫu nhiên, hoặc bên trong một step là một id suy ra từ step), `version` (mặc định là phiên bản cao nhất được đăng ký), `timeout` (mặc định là của decorator), `transaction`, `priority` (1 tới 2.097.151, nhỏ hơn đi trước; mặc định không có, tức đi trước tất cả), `concurrencyKey`, `rateLimitKey` (thay cho các key mà giới hạn tính ra) | [Khởi động nó cùng đơn hàng](/reliability/workflows#start-it-with-the-order), [Giới hạn số lượng chạy cùng lúc](/reliability/workflows#limit-how-many-run-at-once) |
| `WorkflowClient.signal(signal, payload, options)` | `key`, `id` (lưu một signal cùng tên và id chỉ một lần; bên trong một step thì suy ra từ step), `transaction` | [Chờ webhook giao hàng](/reliability/workflows#wait-for-the-delivery-webhook), [Với CQRS](/reliability/workflows#with-cqrs) |
| `WorkflowClient.startAndWait(workflow, input, options, wait)` | Các tùy chọn của `start()`, trừ `transaction`, và các tùy chọn của `result()` làm `wait` | [Chờ kết quả](/reliability/workflows#wait-for-a-result) |
| `WorkflowClient.result(id, options)` | `timeout` (theo giờ thực; mặc định không có), `signal` (dừng chờ khi bị abort) | [Chờ kết quả](/reliability/workflows#wait-for-a-result) |
| `WorkflowClient.getStatus(id, options)` | `journal`, `children` | [Báo cáo trạng thái](/reliability/workflows#report-its-status), [Khởi động child workflow](/reliability/workflows#start-child-workflows) |
| `WorkflowClient.cancel(id, reason)`, `terminate(id, reason)` | Không có | [Cho bộ phận chăm sóc khách hàng hủy đơn](/reliability/workflows#let-customer-support-cancel-an-order), [Retry, xóa hoặc terminate](/reliability/workflows#retry-delete-or-terminate) |
| `WorkflowClient.list(filter)` | `status` (một hoặc một danh sách), `workflow`, `version`, `parentId`, `scheduleId`, `limit` (mặc định `100`), `offset` | [Deploy thay đổi một cách an toàn](/reliability/workflows#deploy-changes-safely) |
| `WorkflowClient.retry(id, options)` | `timeout` (một run timeout mới tính từ bây giờ, hoặc `false` để không có; mặc định là của instance) | [Retry, xóa hoặc terminate](/reliability/workflows#retry-delete-or-terminate) |
| `WorkflowClient.delete(id, options)` | `force` (xóa cả instance chưa kết thúc; mặc định `false`) | [Retry, xóa hoặc terminate](/reliability/workflows#retry-delete-or-terminate) |
| `WorkflowClient.purge(options)` | `olderThan` (bắt buộc), `status` (mặc định `completed`, `failed` và `cancelled`), `batchSize` (mặc định `500`) | [Dọn dẹp các instance đã kết thúc](/reliability/workflows#purge-finished-instances) |
| `WorkflowClient.schedules`, hoặc `WorkflowSchedules` có thể inject | `upsert(id, options)` (các tùy chọn lịch chạy, kèm `workflow`, và tùy chọn `version` cùng một `input` JSON), `get(id)`, `list(filter)` (`workflow`, `limit`, `offset`), `remove(id)`, `pause(id)` và `resume(id)` (cả hai không mã hóa lại input đã lưu), `trigger(id)` (trong một process đăng ký workflow, trừ khi lịch chạy cố định một `version`), và `preview(schedule, options)` (id hoặc thời điểm của một lịch chạy; `from`, và `count`, mặc định `10`) | [Chạy workflow theo lịch](/reliability/workflows#run-workflows-on-a-schedule) |
| `@StartOn(event, options)` | `id` (bắt buộc), `input` (mặc định là event), `priority`, `concurrencyKey`, `rateLimitKey` (như của `start()`: một giá trị, hoặc một hàm nhận event, trong đó `undefined` giữ nguyên mặc định) | [Với CQRS](/reliability/workflows#with-cqrs) |
| `@SignalOn(event, options)` | `signal`, `key`, `id`, `payload` (mặc định là event) | [Với CQRS](/reliability/workflows#with-cqrs) |
| `EventBus.publish(event, context)`, `publishAll(events, context)`, `commit(context)` của một aggregate (`@nestjs/cqrs` 12.1 trở lên) | `transaction`, được đọc từ dispatcher context khi `WorkflowsCqrsModule` đã được import | [Với CQRS](/reliability/workflows#with-cqrs) |

Hàm của một step nhận `idempotencyKey`, `attempt`, `signal`, `progress` và `heartbeat()`; một compensation nhận những thứ tương tự, cộng với lý do workflow đang bị hoàn tác.

Một lịch chạy, được khai báo trong `@Workflow()` hoặc được lưu bằng `upsert()`, nhận các tùy chọn sau:

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `id` | Bắt buộc trong `@Workflow()` | Duy nhất trong toàn ứng dụng: chữ cái, chữ số, `.`, `:`, `_` và `-`. `upsert()` nhận nó làm tham số đầu tiên |
| `cron`, `every`, `rrule` | Bắt buộc một trong ba | Một biểu thức cron 5 trường, hoặc 6 trường với giây đứng đầu; một khoảng thời gian tối thiểu một giây, tính từ `startAt`; hoặc một recurrence rule theo RFC 5545 |
| `tz` | `'UTC'` | Múi giờ IANA của `cron` và `rrule`. Không dùng với `every` |
| `startAt`, `endAt` | Không có | Không có lần chạy nào trước `startAt`, hoặc sau `endAt` |
| `limit` | Không có | Số lần chạy mà nó khởi động trước khi kết thúc |
| `missed` | `'skip'` | Các lần chạy mà không worker nào hoạt động để khởi động: `'skip'`, `'once'` hoặc `'all'` |
| `overlap` | `'skip'` | Một lần chạy tới hạn trong khi một instance mà nó đã khởi động vẫn chưa kết thúc: `'skip'`, `'allow'`, `'cancel-previous'` hoặc `'buffer-one'` |
| `priority` | Không có | Độ ưu tiên của các instance mà nó khởi động |
| `input` | Không có | Input của các instance: một giá trị JSON, hoặc trong `@Workflow()` là một hàm nhận lần chạy |

##### Event <a id="events"></a>

`WorkflowEvents.events$` phát ra mỗi event, và publish nó trên diagnostics channel `nestjs:workflows:<type>`, ví dụ `nestjs:workflows:step-failed`. Mọi payload đều có `type`, `id` (instance), `workflow`, `version` và `at` (thời gian của engine, tính bằng mili giây).

| Event | Các field khác | Khi nào |
| --- | --- | --- |
| `workflow-started` | Không có | Lần thực thi đầu tiên của một instance bắt đầu |
| `workflow-resumed` | `run` | Một lần thực thi sau đó bắt đầu: sau một wait, một sleep, một retry hoặc một lần crash |
| `workflow-suspended` | `wakeAt`, `waits` | Một lần thực thi đã đỗ instance lại |
| `step-completed` | `step`, `attempt`, `durationMs` | Một lần thử step thành công |
| `step-failed` | `step`, `attempt`, `error`, `retryAt` | Một lần thử step thất bại; `retryAt` là `null` khi step đã bỏ cuộc |
| `signal-received` | `wait`, `signal`, `signalId` | Một lần chờ đã nhận một signal |
| `signal-timed-out` | `wait`, `signal` | Hạn chót của một lần chờ đã qua mà không có signal nào khớp |
| `workflow-compensating` | `error` | Instance thất bại hoặc bị hủy, và bắt đầu hoàn tác |
| `step-compensated` | `step`, `attempt` | Compensation của một step đã hoàn tất |
| `workflow-completed` | `output` | Instance đã hoàn tất |
| `workflow-failed` | `error` | Instance đã thất bại, sau khi các compensation của nó chạy |
| `workflow-cancelled` | `error` | Instance đã bị hủy, sau khi các compensation của nó chạy; `error.message` là lý do |
| `workflow-compensation-failed` | `error` | Một compensation đã bỏ cuộc giữa chừng. Cần người xử lý |
| `journal-large` | `entries`, `bytes` | Journal đã chạm `journal.warnEntries` hoặc `journal.warnBytes`; mỗi instance một lần |
| `workflow-retried` | `from`, `error` | `retry()` đã mở lại một instance `failed` hoặc `compensation_failed`; `error` là lỗi mà nó đã có |
| `workflow-deleted` | `status` | `delete()` đã xóa một instance; `status` là trạng thái mà nó đã có |
| `custom-status` | `status` | Một thao tác ghi đã thay đổi custom status của instance |
| `child-started` | `child`, `childWorkflow`, `childVersion` | Instance đã khởi động một child |
| `schedule-skipped` | `reason` (`'missed'` hoặc `'overlap'`), `from`, `to` | Một lịch chạy đã bỏ qua các lần chạy. `id` của nó là id của lịch chạy |

Một instance map lên một trace, bất kể process nào chạy nó trong suốt nhiều ngày hay nhiều tuần, nên hãy đánh key cho trace theo `id` của instance. Instance là root span, từ `workflow-started` tới event cuối cùng của nó (`workflow-completed`, `workflow-failed`, `workflow-cancelled` hoặc `workflow-compensation-failed`). Mỗi lần thực thi là một child span, từ `workflow-started` hoặc `workflow-resumed` tới `workflow-suspended` hoặc event cuối cùng. Mỗi lần thử step là một span bên trong nó, kết thúc ở `step-completed`, có `durationMs` cho biết thời điểm bắt đầu, hoặc ở `step-failed`. Các event khác là event trên span của lần thực thi. Các công cụ tracing subscribe vào các diagnostics channel, nên việc này không cần code nào trong ứng dụng của bạn.

##### Lỗi <a id="errors"></a>

Các lỗi của package kế thừa `WorkflowError`, trừ hai lỗi là luồng điều khiển hoặc là để bạn throw. Những lỗi xuất hiện trên một instance thất bại được ghi theo tên, trong `error` của nó.

| Lỗi | HTTP status | Xảy ra khi |
| --- | --- | --- |
| `WorkflowIdConflictError` | `409` | `start()` với một id đã tồn tại, nhưng khác workflow hoặc input, `signal()` với một `id` đã được dùng cho cùng signal với key khác, hoặc `startChild()` với một id mà workflow, cha hoặc input khác đang dùng |
| `WorkflowNotFoundError` | `404` | `cancel()`, `terminate()`, `retry()`, `delete()` hoặc `result()` với một id không tồn tại, một method lịch chạy với schedule id không tồn tại, hoặc `start()` hay `trigger()` của lịch chạy với một workflow mà ứng dụng này không resolve được |
| `WorkflowStateError` | `409` | `retry()` một instance không ở trạng thái `failed` hoặc `compensation_failed`, hoặc đã chạy compensation; `delete()` một instance chưa kết thúc mà không có `force`; một trong hai chạy đua với một thay đổi khác trên instance; `upsert()` hoặc `remove()` một lịch chạy đã khai báo |
| `NonRetryableStepError` | Không có | Bạn throw nó từ một step để làm step thất bại mà không retry |
| `StepFailedError` | Không có | Bên trong `run()`, một step đã bỏ cuộc; `step`, `attempts`, và tên cùng message của lỗi gốc làm `cause` |
| `StepTimeoutError` | Không có | Một lần thử step chạy quá `timeout` hoặc `heartbeatTimeout` của nó. Sẽ được retry |
| `WorkflowFailedError` | Không có | `ctx.fail()` đã làm instance thất bại. Cũng là lỗi mà `result()` và `startAndWait()` reject với một instance kết thúc mà không hoàn tất, kèm `instanceId`, `status` và lỗi của nó làm `cause` |
| `ChildWorkflowFailedError` | Không có | Một child đã thất bại, bị hủy hoặc bị terminate: đây là lỗi mà `ctx.executeChild()` và `result()` của một child throw ở phía cha, kèm `workflow`, `instanceId`, `status` và lỗi của child làm `cause`. Kế thừa `WorkflowFailedError` |
| `WorkflowResultTimeoutError` | Không có | `result()` hoặc `startAndWait()` đã chờ quá `timeout` của nó, kèm `instanceId` và `timeoutMs`. Instance vẫn tiếp tục chạy |
| `WorkflowDefinitionError` | Không có | Một tên được dùng hai lần trong một lần chạy, hoặc một lời gọi `ctx` bên trong một step. Instance thất bại mà không bù trừ |
| `WorkflowNonDeterminismError` | Không có | Một lần deploy đã đổi tên, xóa hoặc sắp xếp lại các step mà các instance đang chạy đã ghi journal. Kế thừa `WorkflowDefinitionError`. [Deploy thay đổi một cách an toàn](/reliability/workflows#deploy-changes-safely) |
| `WorkflowInterrupt` | Không có | Luồng điều khiển của engine (một lần tạm dừng, một lần cancel). Hãy throw lại nó; `isWorkflowInterrupt()` nhận diện nó |
| `WorkflowTimeoutError` | Không có | Chỉ xuất hiện theo tên, trên một instance đã chạy quá run timeout: nó đã bù trừ và thất bại |
| `WorkflowCancelledError` | Không có | Chỉ xuất hiện theo tên, trên một instance đã bị hủy: message của nó là lý do |
| `WorkflowTerminatedError` | Không có | Chỉ xuất hiện theo tên, trên một instance đã bị terminate, kết thúc ở trạng thái `cancelled`: message của nó là lý do |
| `WorkflowDeletedError` | Không có | Chỉ xuất hiện theo tên, làm cause của `ChildWorkflowFailedError` ở phía cha, khi `delete()` với `force` đã xóa child trước khi nó kết thúc |
| `WorkflowJournalLimitError` | Không có | Chỉ xuất hiện theo tên, trên một instance có journal đã chạm `journal.maxEntries` hoặc `journal.maxBytes`: nó đã bù trừ và thất bại |
| `WorkflowSchemaError` | Không có | Schema của `PostgresWorkflowStore` hoặc `MySqlWorkflowStore` chậm hơn các migration của package trong khi `migrate` bị tắt, hoặc việc áp dụng chúng thất bại (`cause`; trên MySQL, message nêu tên câu lệnh mà lần chạy tiếp theo sẽ tiếp tục từ đó): việc khởi động và mọi lời gọi đều thất bại cho tới khi được sửa. Kèm theo `schema`, `version` của nó và `requiredVersion`. Từ `@nestjs/workflows/postgres` và `@nestjs/workflows/mysql` |

`MySqlWorkflowStore` cũng từ chối một id, tên hoặc key dài hơn cột của nó bằng một `RangeError`, trước mọi câu SQL ([Store MySQL](/reliability/workflows#mysql-store)). Một deadlock trong transaction của bạn tới bạn dưới dạng lỗi 1213 của MySQL, lỗi mà store không retry, vì nó đã rollback cả các thao tác ghi của bạn.
