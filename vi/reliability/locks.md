### Distributed lock

`@nestjs/locks` chạy một scheduled job, hoặc bất kỳ đoạn code nào khác, trên một instance tại một thời điểm, với các lease mà mọi instance của ứng dụng kiểm tra trong một store dùng chung.

Một cửa hàng online bán thức ăn và đồ dùng cho mèo chạy hai scheduled job bằng `@nestjs/schedule`. Mỗi đêm lúc 02:00, một job export gửi hóa đơn trong ngày tới hệ thống kế toán, và cứ năm phút một lần, một job đối soát yêu cầu kho kiểm đếm toàn bộ hàng và ghi kết quả vào bảng sản phẩm. Cả hai đều chạy ổn trên một instance. Trong production, API đơn hàng chạy trên ba instance, và `@nestjs/schedule` kích hoạt mọi `@Cron()` trên từng instance:

- Hệ thống kế toán ghi nhận mỗi hóa đơn ba lần.
- Kho bị yêu cầu ba lần kiểm đếm toàn bộ mỗi năm phút. Một lần kiểm đếm toàn bộ phân trang qua cả danh mục, và vào cuối tháng nó mất hơn năm phút, nên tick tiếp theo bắt đầu một lần kiểm đếm thứ hai song song với lần đầu, rồi lần thứ ba.

Những cách sửa thông thường đều có lỗ hổng. Một instance `RUN_JOBS=true` chạy ổn cho tới khi một lần rolling deploy có hai instance như vậy trong một phút, hoặc instance chạy job lại chính là instance bị chết. Một key `SET NX` trong Redis ở đầu job chạy ổn cho tới khi bên giữ nó bị dừng lâu hơn TTL của key, do một lần garbage collection stop-the-world hoặc phía sau một network partition: một instance khác lấy key, và khi instance đầu tiên tỉnh lại, nó chạy nốt lần chạy của mình trong khi tin rằng mình vẫn giữ key. Lại hai bên cùng ghi, và không bên nào biết. `waitForCompletion: true` trên `@Cron()` ngăn một job chồng lấn chính nó, nhưng chỉ trên một instance.

`@nestjs/locks` biến một job thành thứ mà một instance nắm giữ: một **lease** mà bên giữ liên tục gia hạn khi nó còn sống, được kiểm tra trong một store mà mọi instance dùng chung. Hai decorator đặt nó lên một scheduled job, `@OnOneInstance()` và `@WithoutOverlapping()`, theo tinh thần của `onOneServer()` và `withoutOverlapping()` trong Laravel. Bên dưới chúng là một distributed lock mà bạn cũng có thể tự lấy, với hai thứ mà một lock cần có để đáng tin: một `AbortSignal` bị abort khi lease bị mất, và một **fencing token** tăng dần với mỗi lần một key được lấy, để một thao tác ghi từ một bên giữ đã bị dừng quá thời hạn lease có thể bị từ chối. Một leader election cũng chính là lease đó, được giữ chừng nào leader còn sống.

Trong bài hướng dẫn này, bạn sẽ thêm nó vào cửa hàng, trên PostgreSQL với Drizzle:

- Chứng minh các lần chạy trùng lặp bằng một test, trên ba instance của ứng dụng.
- Giữ các lock trong một bảng của database ứng dụng.
- Chạy mỗi job trên một instance, với việc chuyển giao khi instance đó chết.
- Giữ một lần kiểm đếm kho dài không chồng lấn chính nó.
- Fence các thao tác ghi kho, để một instance bị dừng không thể ghi đè lên một lần kiểm đếm mới hơn.
- Chạy export thủ công từ một admin endpoint, không bao giờ chạy song song với lần chạy theo lịch.
- Giữ các lock trong Redis thay vào đó.
- Giữ luồng cảnh báo của kho trên một instance, bằng một leader election.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài dependency cần thiết:

```bash
$ npm i --save @nestjs/locks
```

#### Nhìn thấy vấn đề <a id="see-the-problem"></a>

Đây là ứng dụng trước bài hướng dẫn. Job export hàng đêm lấy mọi đơn hàng đã đặt chưa có hóa đơn, upload batch đó, và đánh dấu các đơn hàng bằng batch id:

```typescript
@@filename(invoices/invoice-export.job.step-1)
import { Injectable, Logger } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { Cron } from '@nestjs/schedule';
import { and, eq, inArray, isNull } from 'drizzle-orm';
import type { Database } from '../database/drizzle.js';
import { orders } from '../database/schema.js';
import { AccountingClient } from './accounting.client.js';

@Injectable()
export class InvoiceExportJob {
  private readonly logger = new Logger(InvoiceExportJob.name);

  constructor(
    @InjectDrizzle() private readonly db: Database,
    private readonly accountingClient: AccountingClient,
  ) {}

  @Cron(process.env.INVOICE_EXPORT_CRON ?? '0 2 * * *', { name: 'invoice-export', timeZone: 'Europe/Warsaw' })
  async exportInvoices() {
    // Every placed order without an invoice, not "yesterday's orders": a night
    // the export didn't run is caught up the next night.
    const pending = await this.db
      .select()
      .from(orders)
      .where(and(eq(orders.status, 'placed'), isNull(orders.invoicedAt)))
      .orderBy(orders.placedAt);
    if (pending.length === 0) {
      return;
    }

    const batch = await this.accountingClient.uploadInvoices(
      pending.map((order) => ({
        orderId: order.id,
        userId: order.userId,
        total: order.total,
        placedAt: order.placedAt.toISOString(),
      })),
    );
    await this.db
      .update(orders)
      .set({ invoicedAt: new Date(), invoiceBatch: batch.batchId })
      .where(inArray(orders.id, pending.map((order) => order.id)));
    this.logger.log(`Exported ${pending.length} invoices in batch ${batch.batchId}`);
  }
}
```

Hệ thống kế toán ghi nhận mọi batch mà nó nhận được, nên một batch được upload hai lần sẽ bị ghi nhận hai lần. Job đối soát yêu cầu kho cung cấp số lượng và ghi chúng lại:

```typescript
@@filename(inventory/stock-reconciliation.job.step-1)
import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { StockRepository } from './stock.repository.step-1.js';
import { WarehouseClient } from './warehouse.client.js';

@Injectable()
export class StockReconciliationJob {
  private readonly logger = new Logger(StockReconciliationJob.name);

  constructor(
    private readonly warehouseClient: WarehouseClient,
    private readonly stockRepository: StockRepository,
  ) {}

  @Cron(process.env.STOCK_RECONCILIATION_CRON ?? CronExpression.EVERY_5_MINUTES, { name: 'stock-reconciliation' })
  async reconcileStock() {
    const counts = await this.warehouseClient.stockCounts();
    const written = await this.stockRepository.writeStock(counts);
    this.logger.log(`Reconciled stock for ${written} products`);
  }
}
```

Các biểu thức cron lấy từ môi trường, với lịch thật làm mặc định, để các test và phần [Chạy thử](/reliability/locks#try-it) có thể tăng tốc hoặc tắt chúng. `AccountingClient` và `WarehouseClient` là bản thay thế cho hai hệ thống bên ngoài; mỗi cái đếm những gì nó được yêu cầu làm. Database là của ứng dụng, được đăng ký bằng `DrizzleModule` trong `app.module.ts` và inject bằng `@InjectDrizzle()`.

> info **Gợi ý** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để thiếu một biến sẽ dừng ứng dụng ngay lúc khởi động thay vì ở request đầu tiên, và đọc các giá trị từ `ConfigService`.

Trước khi thay đổi bất cứ điều gì, hãy chứng minh vấn đề. Test khởi động ba instance của ứng dụng trong một process, trên một database (PostgreSQL in-process bằng [PGlite](https://pglite.dev), hoặc một PostgreSQL server nếu có cấu hình), và kích hoạt các lịch chạy trên từng instance qua registry riêng của `@nestjs/schedule`, giống như khi tới 02:00:

```typescript
@@filename(test/step-1.duplicate-runs.e2e-spec)
describe.each(targets)('three instances with plain @Cron() jobs, on %s', (_, target) => {
  let database: TestDatabase;
  let accounting: FakeAccounting;
  let warehouse: FakeWarehouse;
  let instances: TestingModule[];
  let logger: CapturingLogger;

  beforeEach(async (context) => {
    if (!target) {
      return context.skip();
    }
    database = await openDatabase(target, 'locks_step_1');
    accounting = new FakeAccounting();
    warehouse = new FakeWarehouse();
    logger = new CapturingLogger();
    instances = [];
    for (let i = 0; i < 3; i++) {
      instances.push(await startInstance({ database, module: StepOneApp, accounting, warehouse, logger }));
    }
  });
  afterEach(async () => {
    for (const app of instances ?? []) {
      await app.close();
    }
    await database?.close();
  });

  /**
   * 02:00: every instance's scheduler fires the job, through @nestjs/schedule's own
   * callback (which doesn't wait for the job to finish).
   */
  const tick = (name: string) =>
    Promise.all(instances.map((app) => app.get(SchedulerRegistry).getCronJob(name).fireOnTick()));

  it('records every invoice three times', async () => {
    await tick('invoice-export');
    await until(() => logger.matching('Exported 3 invoices').length === 3);
    const orders = ['ord_1001', 'ord_1002', 'ord_1004'];
    expect(booked(accounting)).toEqual([orders, orders, orders]);
    // The orders point at whichever batch wrote last; the accounting system has all three.
    const rows = await database.query<{ invoice_batch: string }>(
      "SELECT DISTINCT invoice_batch FROM orders WHERE status = 'placed'",
    );
    expect(rows).toHaveLength(1);
  });

  it('asks the warehouse for three full counts every five minutes', async () => {
    await tick('stock-reconciliation');
    await until(() => logger.matching('Reconciled stock').length === 3);
    expect(warehouse.counts).toBe(3);
  });
});
```

Ba batch, mỗi batch có cùng ba đơn hàng, và ba lần kiểm đếm toàn bộ. Bảng `orders` sau đó trông vẫn ổn, mọi đơn hàng đều có batch id, đó là lý do chuyện này không bị phát hiện cho tới khi bộ phận kế toán gọi điện.

#### Giữ lock trong database của bạn <a id="keep-locks-in-your-database"></a>

`@nestjs/locks` hoạt động ngay khi bạn import `LocksModule`, trên một store trong bộ nhớ. Store đó chỉ loại trừ các bên gọi trong một process: ba instance sẽ mỗi cái có store riêng, cả ba sẽ cùng lấy được "cái" lock đó, và không có gì thay đổi. Các lock cần một store mà mọi instance dùng chung, và package không đi kèm store nào. Nó định nghĩa hợp đồng, interface `LockStore`, và bạn implement nó trong một provider của ứng dụng bằng database mà ứng dụng đã có.

Phần này trình bày store đó hai lần: đầu tiên với Drizzle trên PostgreSQL, được đăng ký qua [`@nestjs/drizzle`](/data/drizzle) với driver `pg`, là lộ trình của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối phần, cùng store đó cho một ứng dụng dùng TypeORM làm ORM. Hãy chọn một trong hai, hoặc giữ các lock trong Redis với [store trên Redis](/reliability/locks#the-store-on-redis). Với Drizzle, một lock là một dòng cho mỗi key:

```typescript
@@filename(database/schema)
// The locks, read and written by DrizzleLockStore: one row per lock key.

export const locks = pgTable('locks', {
  key: text('key').primaryKey(),
  /** The holder's id; null once released. */
  owner: text('owner'),
  fencingToken: bigint('fencing_token', { mode: 'number' }).notNull(),
  /** On the database's clock: every instance agrees on it. */
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
});

/** Fencing tokens for every key: a sequence never goes back, so they only grow. */
export const locksFencingTokenSeq = pgSequence('locks_fencing_token_seq');
```

drizzle-kit viết migration:

```bash
$ npx drizzle-kit generate --name=locks
$ npx drizzle-kit migrate
```

```sql
@@filename(drizzle/0002_locks.sql)
CREATE SEQUENCE "public"."locks_fencing_token_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1;--> statement-breakpoint
CREATE TABLE "locks" (
	"key" text PRIMARY KEY NOT NULL,
	"owner" text,
	"fencing_token" bigint NOT NULL,
	"expires_at" timestamp with time zone NOT NULL
);
```

Hợp đồng có ba method, và mỗi method nhận lock key và một `owner` trước tiên: một id ngẫu nhiên mà package sinh ra cho mỗi lần lấy lock. Các khoảng thời gian được truyền vào dưới dạng số mili giây nguyên.

- `acquire(key, owner, ttl)` lấy key nếu không có lock nào còn hiệu lực đang giữ nó, và trả về fencing token của lock, hoặc báo rằng key đã bị chiếm. Nó phải nguyên tử: trong bất kỳ số bên gọi đồng thời nào, chỉ đúng một bên được thắng.
- `renew(key, owner, ttl)` là heartbeat. Nó dời thời hạn thành `ttl` tính từ bây giờ, nếu `owner` vẫn đang giữ một lock còn hiệu lực trên key. Package gọi nó mỗi `ttl / 3` trong khi một lock đang được giữ.
- `release(key, owner)` trả lại lock, nếu `owner` vẫn đang giữ nó.

Điều kiện "nếu `owner` vẫn đang giữ nó" phải được kiểm tra trong cùng câu lệnh thực hiện việc ghi: nếu kiểm tra bằng một lần đọc riêng trước đó, một lần tiếp quản có thể chen vào giữa. Và store đo `ttl` bằng đồng hồ của chính nó, để mọi instance thống nhất về thời điểm một lock hết hạn bất kể đồng hồ của chúng nói gì. Với Drizzle, đó là một câu insert có điều kiện và hai câu update có điều kiện:

```typescript
@@filename(database/drizzle-lock.store)
import { Injectable } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { LocksStorage, type LockAcquireResult, type LockStore } from '@nestjs/locks';
import { and, eq, gt, sql } from 'drizzle-orm';
import type { Database } from './drizzle.js';
import { locks } from './schema.js';

/** `ttl` from now, on the database's clock. */
const expiresIn = (ttl: number) => sql`clock_timestamp() + ${ttl} * interval '1 millisecond'`;

/** The lock on `key`, if `owner` still holds it: the compare-and-set of renew() and release(). */
const heldBy = (key: string, owner: string) =>
  and(eq(locks.key, key), eq(locks.owner, owner), gt(locks.expiresAt, sql`clock_timestamp()`));

@Injectable()
export class DrizzleLockStore implements LockStore {
  constructor(
    @InjectDrizzle() private readonly db: Database,
    storage: LocksStorage,
  ) {
    storage.registerSource(this);
  }

  async acquire(key: string, owner: string, ttl: number): Promise<LockAcquireResult> {
    // One statement: insert the lock, or take over a released or expired one. Of any number
    // of concurrent callers, one inserts or updates the row; the others find it held.
    const [row] = await this.db
      .insert(locks)
      .values({ key, owner, fencingToken: sql`nextval('locks_fencing_token_seq')`, expiresAt: expiresIn(ttl) })
      .onConflictDoUpdate({
        target: locks.key,
        // nextval() here runs after the row is locked: a later holder always gets a
        // greater token than the one before it. The row's own token is the floor, so a
        // sequence that went back (a restore, a failover) can't hand a key an old token.
        set: {
          owner,
          fencingToken: sql`greatest(nextval('locks_fencing_token_seq'), ${locks.fencingToken} + 1)`,
          expiresAt: expiresIn(ttl),
        },
        setWhere: sql`${locks.owner} is null or ${locks.expiresAt} <= clock_timestamp()`,
      })
      .returning({ fencingToken: locks.fencingToken });
    return row ? { acquired: true, fencingToken: row.fencingToken } : { acquired: false };
  }

  async renew(key: string, owner: string, ttl: number): Promise<boolean> {
    const rows = await this.db
      .update(locks)
      .set({ expiresAt: expiresIn(ttl) })
      .where(heldBy(key, owner))
      .returning({ key: locks.key });
    return rows.length === 1;
  }

  async release(key: string, owner: string): Promise<boolean> {
    // Keep the row, so the next acquire() always takes the update path above, whose token is
    // drawn after the row is locked.
    const rows = await this.db
      .update(locks)
      .set({ owner: null })
      .where(heldBy(key, owner))
      .returning({ key: locks.key });
    return rows.length === 1;
  }
}
```

Vài điều về store này:

- **`acquire()` là một câu lệnh duy nhất.** Câu insert thắng một key chưa có dòng nào; `ON CONFLICT DO UPDATE` với `WHERE` của nó tiếp quản một key đã được giải phóng hoặc đã hết hạn, và PostgreSQL kiểm tra lại `WHERE` đó trên dòng sau khi đã lock nó. Trong nhiều bên gọi chạy đua giành cùng một key, một bên nhận lại một dòng và các bên còn lại không nhận được gì. Một câu `SELECT` theo sau là một câu `INSERT` sẽ để nhiều bên lọt vào.
- **Fencing token đến từ một sequence**, được lấy bên trong câu lệnh, sau khi lock dòng. Một sequence không bao giờ quay ngược, nên mỗi lần lấy một key sẽ nhận token lớn hơn lần trước, xuyên qua các lần giải phóng và hết hạn. Nó có những khoảng trống, vì một bên gọi thua cuộc vẫn đã tiêu thụ một giá trị; điều đó không quan trọng. `greatest()` biến token riêng của dòng thành mức sàn cho token tiếp theo: nếu sequence có lúc quay ngược (khôi phục từ backup, failover sang một replica bị chậm), một key vẫn không thể nhận một token mà nó đã từng có. [Fence các thao tác ghi](/reliability/locks#fence-the-writes) cho thấy token dùng để làm gì.
- **`release()` giữ lại dòng** và xóa owner, để lần lấy tiếp theo luôn đi theo nhánh update. Nếu xóa dòng, một câu insert đã lấy token từ sớm có thể thắng key sau khi một bên giữ sau đó đã giải phóng nó, và phát ra một token nhỏ hơn.
- **`clock_timestamp()`**, chứ không phải `now()`: `now()` là thời điểm bắt đầu transaction, chính là thứ mà thời hạn của lock không được phụ thuộc vào.
- Tại sao dùng bảng mà không dùng `pg_advisory_lock()`: một advisory lock gắn với một session, nên bên giữ phải giữ một kết nối lấy ra từ pool trong suốt critical section, sẽ mất lock mà không biết khi nào nếu kết nối đó bị ngắt, không thể gia hạn nó, và không có thời hạn cho một bên giữ bị dừng cũng như không có fencing token. Một dòng dữ liệu có tất cả những thứ đó, qua bất kỳ pool nào.

Package đi kèm hợp đồng dưới dạng một test suite, để bạn có thể kiểm chứng store trước khi tin dùng nó. `lockStoreContract()` trả về các case dùng được với mọi test runner, và `concurrent: true` thêm vào các tình huống race:

```typescript
@@filename(test/step-2.drizzle-lock-store.e2e-spec)
describe('DrizzleLockStore on PGlite, the LockStore contract', () => {
  const client = new PGlite();
  const db = drizzlePglite({ client }) as unknown as Database;
  beforeAll(() => migratePglite(db as never, { migrationsFolder }));
  afterAll(() => client.close());

  // The concurrency cases run too; with one connection, PGlite runs them one statement at a time.
  const cases = lockStoreContract(() => new DrizzleLockStore(db, new LocksStorage()), { concurrent: true });
  for (const c of cases) {
    it(c.name, c.run);
  }
});
```

Ví dụ chạy cùng suite đó trên một PostgreSQL server với pool 20 kết nối và 32 bên gọi chạy đua, nơi các câu lệnh thực sự chồng lấn. Hãy chạy nó theo cách đó trong CI, trên phiên bản PostgreSQL mà bạn chạy trong production.

Giờ hãy đăng ký module và store, cạnh `DrizzleModule` của ứng dụng. Store là một provider thuần; constructor của nó tự đăng ký, nên không có gì phải cấu hình:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule } from '@nestjs/drizzle';
import { LocksModule } from '@nestjs/locks';
import { ScheduleModule } from '@nestjs/schedule';
import { drizzle } from 'drizzle-orm/node-postgres';
import { DrizzleLockStore } from './database/drizzle-lock.store.js';
import * as schema from './database/schema.js';
import { InventoryModule } from './inventory/inventory.module.js';
import { InvoicesModule } from './invoices/invoices.module.js';

@Module({
  imports: [
    // A pg pool on DATABASE_URL, closed in onApplicationShutdown(), after running jobs
    // finished and handed their locks back. The jobs and the store inject it with @InjectDrizzle().
    DrizzleModule.forRootAsync({
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema }),
    }),
    ScheduleModule.forRoot(),
    LocksModule.forRoot(),
    InvoicesModule,
    InventoryModule,
  ],
  providers: [DrizzleLockStore],
})
export class AppModule {}
```

`LocksModule.forRoot()` nhận một `ttl` (mặc định là `'30s'`: thời gian một lock tồn tại nếu không được gia hạn, tức là bao lâu sau một lần crash thì một instance khác tiếp quản), một `storeTimeout` (mặc định là `'10s'`: thời gian chờ mỗi lời gọi store trước khi nó thất bại, để một store ngừng trả lời không thể làm treo một job, một request hay quá trình shutdown), một `clock` cho test, và `allowInMemoryStorage`. `forRootAsync()` nhận cùng các tùy chọn từ một factory. Module là global, nên `Locks`, `LocksContext` và `LocksStorage` có sẵn ở mọi nơi. Khi khởi tạo, nó log ra store đang dùng:

```bash
[Nest] 1270  - 09/24/2026, 9:44:02 AM     LOG [LocksModule] LocksStorage: DrizzleLockStore
```

Không có gì được đăng ký, dòng log sẽ nêu tên `InMemoryLockStore` và ý nghĩa của nó. Với `NODE_ENV=production` và không có gì được đăng ký, ứng dụng không khởi động, vì trong bộ nhớ thì mọi instance sẽ cùng lấy được một lock và chạy cùng một job:

```bash
Error: LocksStorage: no LockStore is registered, and NODE_ENV is "production": in memory, a lock only excludes callers in this process, so every instance of the app would take the same lock and run the same job. Implement LockStore in a provider that injects LocksStorage and calls `storage.registerSource(this)` in its constructor, or set `allowInMemoryStorage: true` in the LocksModule options to run in memory anyway (one instance).
```

**Với TypeORM.** Cùng store đó cho một ứng dụng dùng TypeORM làm ORM, trên cùng bảng và sequence. Drizzle vẫn là lộ trình của bài hướng dẫn: hãy dùng store này thay cho store ở trên, chứ không phải dùng song song. Bảng là một entity, và mọi cột đều khai báo type của nó, để TypeORM CLI, vốn load entity mà không có decorator metadata, thấy cùng schema với ứng dụng:

```typescript
@@filename(typeorm/lock.entity)
import { Column, Entity, PrimaryColumn } from 'typeorm';

// The locks table, read and written by TypeOrmLockStore: the same table as the Drizzle
// schema in src/database/schema.ts. Every column states its type, so the entity loads the
// same with or without emitted decorator metadata (the TypeORM CLI runs it through tsx,
// which emits none).

@Entity('locks')
export class LockEntity {
  @PrimaryColumn({ type: 'text' })
  key: string;

  /** The holder's id; null once released. */
  @Column({ type: 'text', nullable: true })
  owner: string | null;

  /** Drawn from locks_fencing_token_seq, which the migration creates. `pg` returns a bigint as a string. */
  @Column({ type: 'bigint', name: 'fencing_token' })
  fencingToken: string;

  /** On the database's clock: every instance agrees on it. */
  @Column({ type: 'timestamptz', name: 'expires_at' })
  expiresAt: Date;
}
```

TypeORM CLI và `TypeOrmModule` dùng chung một bộ tùy chọn, trong một file data source:

```typescript
@@filename(typeorm/data-source)
import { DataSource, type DataSourceOptions } from 'typeorm';
import { LockEntity } from './lock.entity.js';
import { Locks1790321710846 } from './migrations/1790321710846-Locks.js';

/** What the application's TypeOrmModule and the TypeORM CLI share. */
export const dataSourceOptions = {
  type: 'postgres',
  url: process.env.DATABASE_URL,
  entities: [LockEntity],
  migrations: [Locks1790321710846],
} satisfies DataSourceOptions;

// The TypeORM CLI's data source: `migration:generate` compares the entities with this database.
export default new DataSource(dataSourceOptions);
```

Tạo migration từ entity, trên một database đã áp dụng các migration trước đó của bạn. CLI cần một TypeScript loader cho file data source; ở đây dùng `tsx`:

```bash
$ npx tsx ./node_modules/typeorm/cli.js migration:generate src/typeorm/migrations/Locks -d src/typeorm/data-source.ts --pretty
Migration /store/src/typeorm/migrations/1790321710846-Locks.ts has been generated successfully.
```

TypeORM không có entity cho sequence, nên migration nó tạo ra chỉ tạo bảng. Hãy tự thêm sequence vào đó, trước bảng, và drop nó trong `down()`:

```typescript
@@filename(typeorm/migrations/1790321710846-Locks)
import { MigrationInterface, QueryRunner } from "typeorm";

export class Locks1790321710846 implements MigrationInterface {
    name = 'Locks1790321710846'

    public async up(queryRunner: QueryRunner): Promise<void> {
        // Added by hand: TypeORM has no entity for a sequence, so the CLI doesn't generate it.
        await queryRunner.query(`
            CREATE SEQUENCE "locks_fencing_token_seq"
        `);
        await queryRunner.query(`
            CREATE TABLE "locks" (
                "key" text NOT NULL,
                "owner" text,
                "fencing_token" bigint NOT NULL,
                "expires_at" TIMESTAMP WITH TIME ZONE NOT NULL,
                CONSTRAINT "PK_c6e1e10d298aec42ba087dd57e5" PRIMARY KEY ("key")
            )
        `);
    }

    public async down(queryRunner: QueryRunner): Promise<void> {
        await queryRunner.query(`
            DROP TABLE "locks"
        `);
        await queryRunner.query(`
            DROP SEQUENCE "locks_fencing_token_seq"
        `);
    }

}
```

`migrations` trong data source liệt kê nó. Áp dụng nó, và kiểm tra rằng entity và database khớp nhau. Bước kiểm tra không so sánh sequence, nên sequence bạn thêm vào không bị tính là thay đổi:

```bash
$ npx tsx ./node_modules/typeorm/cli.js migration:run -d src/typeorm/data-source.ts
$ npx tsx ./node_modules/typeorm/cli.js migration:generate src/typeorm/migrations/Check -d src/typeorm/data-source.ts --check
No changes in database schema were found
```

Giờ đến store, theo cùng các quy tắc với bản Drizzle:

```typescript
@@filename(typeorm/typeorm-lock.store)
import { Injectable } from '@nestjs/common';
import { LocksStorage, type LockAcquireResult, type LockStore } from '@nestjs/locks';
import { DataSource } from 'typeorm';
import { LockEntity } from './lock.entity.js';

/** `ttl` from now, on the database's clock. */
const EXPIRES_IN = "clock_timestamp() + :ttl * interval '1 millisecond'";

/** The lock on `key`, if `owner` still holds it: the compare-and-set of renew() and release(). */
const HELD_BY = 'key = :key AND owner = :owner AND expires_at > clock_timestamp()';

@Injectable()
export class TypeOrmLockStore implements LockStore {
  constructor(
    private readonly dataSource: DataSource,
    storage: LocksStorage,
  ) {
    storage.registerSource(this);
  }

  async acquire(key: string, owner: string, ttl: number): Promise<LockAcquireResult> {
    // One statement: insert the lock, or take over a released or expired one. It is SQL
    // because the takeover draws its token from the locked row, which orUpdate() can't
    // express: it sets each column from EXCLUDED, whose nextval() ran before the row lock.
    const rows: { fencing_token: string }[] = await this.dataSource.query(
      `INSERT INTO locks (key, owner, fencing_token, expires_at)
       VALUES ($1, $2, nextval('locks_fencing_token_seq'), clock_timestamp() + $3 * interval '1 millisecond')
       ON CONFLICT (key) DO UPDATE SET
         owner = EXCLUDED.owner,
         fencing_token = greatest(nextval('locks_fencing_token_seq'), locks.fencing_token + 1),
         expires_at = clock_timestamp() + $3 * interval '1 millisecond'
       WHERE locks.owner IS NULL OR locks.expires_at <= clock_timestamp()
       RETURNING fencing_token`,
      [key, owner, ttl],
    );
    const [row] = rows;
    // `pg` returns a bigint as a string; the package takes the token as a number.
    return row ? { acquired: true, fencingToken: Number(row.fencing_token) } : { acquired: false };
  }

  async renew(key: string, owner: string, ttl: number): Promise<boolean> {
    const { affected } = await this.dataSource
      .createQueryBuilder()
      .update(LockEntity)
      .set({ expiresAt: () => EXPIRES_IN })
      .where(HELD_BY, { key, owner, ttl })
      .execute();
    return affected === 1;
  }

  async release(key: string, owner: string): Promise<boolean> {
    // Keep the row, so the next acquire() always takes the update path above, whose token is
    // drawn after the row is locked.
    const { affected } = await this.dataSource
      .createQueryBuilder()
      .update(LockEntity)
      .set({ owner: null })
      .where(HELD_BY, { key, owner })
      .execute();
    return affected === 1;
  }
}
```

- **`acquire()` là câu lệnh duy nhất được viết bằng SQL**, qua `dataSource.query()`. `orUpdate()` của insert query builder viết ra một `ON CONFLICT DO UPDATE`, với `WHERE` trong tùy chọn `overwriteCondition` của nó, nhưng nó đặt mọi cột từ `EXCLUDED`: token sẽ là token mà câu insert đã lấy trước khi dòng bị lock, thứ mà một bên giữ key sau đó có thể đã vượt qua. SQL lấy token trong `SET`, sau khi lock dòng, như store Drizzle làm.
- **`renew()` và `release()`** là update query builder với owner và thời hạn trong `WHERE`, và đọc `affected`. Không bao giờ dùng `save()`, và không gọi `findOneBy()` trước: một lần đọc trước khi ghi sẽ để một lần tiếp quản chen vào giữa.
- **Token được chuyển đổi bằng `Number()`.** `pg` trả về cột `bigint` dưới dạng chuỗi, và package từ chối một token dạng chuỗi.
- **Hãy dùng nó** thay cho store Drizzle: `TypeOrmModule.forRoot(dataSourceOptions)` trong `AppModule`, và `TypeOrmLockStore` trong providers của nó thay cho `DrizzleLockStore`. Nó inject `DataSource` mà `TypeOrmModule` cung cấp, và dòng log lúc khởi động sẽ nêu tên `TypeOrmLockStore`.

Contract suite chạy trên nó mà không cần thay đổi, kể cả các case về concurrency. TypeORM kết nối qua `pg`, nên suite cần một PostgreSQL server và sẽ bị bỏ qua nếu không có. Thêm ba case nữa kiểm tra rằng token của một key vẫn tiếp tục tăng sau khi sequence quay ngược, rằng entity và migration khớp nhau (đúng những gì `migration:generate --check` kiểm tra), và rằng store tự đăng ký khi được cung cấp trong một module:

```typescript
@@filename(test/typeorm-lock.store.e2e-spec)
/**
 * TypeOrmLockStore against the package's contract suite (`@nestjs/locks/testing`), on
 * PostgreSQL (the server in SQL_TEST_PG_URL, else a throwaway local cluster; see
 * test-support/postgres.ts), with the migration the TypeORM CLI generated. A pool, so the
 * concurrency cases race for real. Skipped, with the reason, without a server.
 */
import { Logger } from '@nestjs/common';
import { LocksModule, LocksStorage } from '@nestjs/locks';
import { lockStoreContract } from '@nestjs/locks/testing';
import { Test } from '@nestjs/testing';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';
import { startPostgres } from '../../../test-support/postgres.js';
import { dataSourceOptions } from '../src/typeorm/data-source.js';
import { TypeOrmLockStore } from '../src/typeorm/typeorm-lock.store.js';

const { postgres, reason } = await startPostgres();
afterAll(() => postgres?.stop());

describe.skipIf(!postgres)(`TypeOrmLockStore on PostgreSQL${postgres ? '' : ` (skipped: ${reason})`}`, () => {
  let dataSource: DataSource;
  let url: string;

  beforeAll(async () => {
    url = await postgres!.createDatabase('locks_typeorm_store');
    dataSource = await new DataSource({ ...dataSourceOptions, url, poolSize: 20 }).initialize();
    await dataSource.runMigrations();
  });
  afterAll(() => dataSource?.destroy());

  describe('the LockStore contract', () => {
    // The expiry cases wait in real time: the store reads the database's clock.
    const cases = lockStoreContract(() => new TypeOrmLockStore(dataSource, new LocksStorage()), { concurrent: { callers: 32 } });
    for (const c of cases) {
      it(c.name, c.run);
    }
  });

  it("keeps a key's tokens growing after the sequence went back (a restore, a failover to a lagging replica)", async () => {
    const store = new TypeOrmLockStore(dataSource, new LocksStorage());
    const key = `reset-${Date.now()}`;
    await dataSource.query("SELECT setval('locks_fencing_token_seq', 1000)");
    const before = await store.acquire(key, 'a', 5_000);
    expect(before.acquired).toBe(true);
    expect(await store.release(key, 'a')).toBe(true);
    await dataSource.query('ALTER SEQUENCE locks_fencing_token_seq RESTART WITH 1');
    const after = await store.acquire(key, 'b', 5_000);
    expect(after.acquired).toBe(true);
    expect((after as { fencingToken: number }).fencingToken).toBeGreaterThan((before as { fencingToken: number }).fencingToken);
  });

  it('has a migration that matches the entity (what `migration:generate --check` checks)', async () => {
    const { upQueries } = await dataSource.driver.createSchemaBuilder().log();
    expect(upQueries.map((query) => query.query)).toEqual([]);
  });

  it('registers itself when provided in a module', async () => {
    const log = vi.spyOn(Logger.prototype, 'log').mockImplementation(() => {});
    const app = await Test.createTestingModule({
      imports: [TypeOrmModule.forRoot({ ...dataSourceOptions, url }), LocksModule.forRoot()],
      providers: [TypeOrmLockStore],
    }).compile();
    await app.init();
    try {
      expect(app.get(LocksStorage).source).toBe(app.get(TypeOrmLockStore));
      expect(log).toHaveBeenCalledWith('LocksStorage: TypeOrmLockStore');
    } finally {
      log.mockRestore();
      await app.close();
    }
  });
});
```

> info **Gợi ý** Dùng Prisma? [Hợp đồng của store](/reliability/locks#the-store-contract), sau phần hướng dẫn, liệt kê những gì store phải đảm bảo và cách Prisma diễn đạt các method nguyên tử. Hãy test store của bạn với cùng các case đó.

#### Chạy mỗi job trên một instance <a id="run-each-job-on-one-instance"></a>

Thêm `@OnOneInstance()` vào cả hai job, cạnh `@Cron()`:

```typescript
@@filename(invoices/invoice-export.job.step-3)
import { OnOneInstance } from '@nestjs/locks';
import { Cron } from '@nestjs/schedule';
```

```typescript
@@filename(invoices/invoice-export.job.step-3)
@Cron(process.env.INVOICE_EXPORT_CRON ?? '0 2 * * *', { name: 'invoice-export', timeZone: 'Europe/Warsaw' })
@OnOneInstance({ key: 'invoices:nightly-export' })
async exportInvoices() {
```

```typescript
@@filename(inventory/stock-reconciliation.job.step-3)
@Cron(process.env.STOCK_RECONCILIATION_CRON ?? CronExpression.EVERY_5_MINUTES, { name: 'stock-reconciliation' })
@OnOneInstance({ key: 'inventory:stock-reconciliation' })
async reconcileStock() {
```

Đó là toàn bộ thay đổi. Những gì nó làm:

- **Instance đầu tiên có scheduler kích hoạt job sẽ lấy lease của job**, một lock được đặt tên theo key với hậu tố `:owner`, và liên tục gia hạn nó mỗi `ttl / 3` chừng nào nó còn sống. Nó chạy tick này và mọi tick sau đó.
- **Trên các instance khác, tick bị bỏ qua**: lời gọi resolve mà không chạy method, một dòng debug cho biết lý do, và `LocksEvents.jobSkips$` báo cáo điều đó ([Event](/reliability/locks#events)). Không có gì được xếp hàng chờ; lịch chạy của job chính là lịch chạy.
- **Khi owner chết**, nó ngừng gia hạn, lease hết hạn sau `ttl` (30 giây), và instance đầu tiên có tick tới sau thời điểm đó sẽ tiếp quản job. Khi owner shutdown một cách bình thường, nó hoàn tất các lần chạy đang dở, trả lại lease, và tick tiếp theo ở bất kỳ đâu sẽ lấy nó.
- **Các decorator bọc method.** `@nestjs/schedule` không bị patch, và nó không biết chúng ở đó: explorer của nó tìm thấy metadata `@Cron()` trên wrapper, theo bất kỳ thứ tự decorator nào, và gọi wrapper, wrapper này hỏi `LocksModule` xem lời gọi này có được chạy không. Job `@Interval()` và `@Timeout()` hoạt động theo cách tương tự, và việc tự gọi method cũng vậy.
- **Key** mặc định là `ClassName.methodName`. Hãy đặt nó cho một job không bao giờ được chạy hai lần: đổi tên class hoặc method sẽ thay đổi giá trị mặc định, và trong một lần rolling deploy, instance cũ và mới sẽ mỗi bên chạy job một lần. Hai job có cùng key mặc định sẽ thất bại lúc khởi động, và một job có key trùng với lease của job khác (`<key>:owner`) hoặc key của một election cũng vậy: chúng sẽ âm thầm loại trừ lẫn nhau.

Quyền sở hữu được giữ ổn định một cách có chủ ý. Một cuộc đua cho mỗi tick sẽ đơn giản hơn, nhưng một tick không phải là một khoảnh khắc: đồng hồ của các instance lệch nhau hàng chục mili giây, nên một lock theo tick sẽ phải tồn tại lâu hơn lần chạy một khoảng bằng độ lệch, và một job nhanh sẽ cần một bản ghi "đã chạy lúc" để ngăn một instance bị trễ chạy lại tick đó. Một lease được giữ giữa các tick không có những vấn đề đó, đổi lại một instance sẽ chạy mọi tick của một job, điều mà một scheduled job hiếm khi bận tâm.

Còn một tick không ai chạy thì sao? Trong khi owner bị down, tối đa `ttl` các tick sẽ bị bỏ qua, và job export hàng đêm có thể rơi đúng vào ba mươi giây đó. **Các tick bị lỡ không được chạy bù**: không có gì ghi lại lần cuối một job đã chạy. Hãy viết job làm mọi thứ đã tới hạn thay vì chỉ làm của "hôm qua". Job export lấy mọi đơn hàng chưa có hóa đơn, nên một đêm nó không chạy sẽ được bù vào đêm tiếp theo; job đối soát ghi số lượng hiện tại, nên một tick bị lỡ chỉ làm dữ liệu cũ đi năm phút. Một job mà mỗi tick làm một việc riêng biệt sẽ giữ bản ghi đó trong bảng riêng của nó.

Test từ [Nhìn thấy vấn đề](/reliability/locks#see-the-problem), với các job mới và store, giờ ghi nhận mỗi hóa đơn một lần, và test làm một instance ngừng gia hạn (đồng hồ của nó đứng yên, như thể process đã chết) cho thấy việc chuyển giao:

```typescript
@@filename(test/step-3.one-instance.e2e-spec)
it('records every invoice once, and counts the stock once per tick', async () => {
  const apps = [await start(), await start(), await start()];
  await tick(apps, 'export');
  expect(booked(accounting)).toEqual([['ord_1001', 'ord_1002', 'ord_1004']]);
  await tick(apps, 'reconcile');
  await tick(apps, 'reconcile');
  expect(warehouse.counts).toBe(2);
  expect(logger.matching(/runs on this instance \(lease "inventory:stock-reconciliation:owner"/)).toHaveLength(1);
  expect(logger.matching('Skipped StockReconciliationJob.reconcileStock: it runs on another instance')).toHaveLength(4);
});
```

```typescript
@@filename(test/step-3.one-instance.e2e-spec)
it('moves the job to another instance when its owner dies, after ttl', async () => {
  // A's clock stands still: it stops renewing, as if its process died.
  const crashed = await start({ clock: new ManualLockClock(), ttl: '1s' });
  const survivor = await start({ ttl: '1s' });
  await tick([crashed, survivor], 'export');
  expect(booked(accounting)).toHaveLength(1);

  await database.query("INSERT INTO orders (id, user_id, items, total, status, placed_at) VALUES ('ord_1005', 'usr_dave', '[]', 999, 'placed', now())");
  expect(await survivor.get(InvoiceExportJob).exportInvoices()).toBeUndefined(); // the lease is still A's
  await sleep(1_200); // the database's clock passes A's lease
  await survivor.get(InvoiceExportJob).exportInvoices();
  expect(booked(accounting)).toEqual([['ord_1001', 'ord_1002', 'ord_1004'], ['ord_1005']]);
});
```

`ManualLockClock` là đồng hồ của package dành cho test: nó chỉ dịch chuyển khi được yêu cầu. Một instance dùng nó không bao giờ gia hạn, nên database, với đồng hồ riêng của nó, sẽ cho các lock của instance đó hết hạn sau `ttl`.

#### Đừng để một lần chạy dài chồng lấn chính nó <a id="dont-let-a-long-run-overlap-itself"></a>

`@OnOneInstance()` đặt job đối soát lên một instance. Nó không ngăn instance đó bắt đầu lần kiểm đếm tiếp theo trong khi lần trước vẫn đang chạy, và một `@Cron()` thông thường cũng không. Vào cuối tháng, lần kiểm đếm mất hơn năm phút, nên kho nhận lần kiểm đếm toàn bộ thứ hai, rồi thứ ba. Hãy thêm `@WithoutOverlapping()`:

```typescript
@@filename(inventory/stock-reconciliation.job.step-4)
@Cron(process.env.STOCK_RECONCILIATION_CRON ?? CronExpression.EVERY_5_MINUTES, { name: 'stock-reconciliation' })
@OnOneInstance({ key: 'inventory:stock-reconciliation' })
@WithoutOverlapping()
async reconcileStock() {
```

Giờ một lần chạy lấy thêm một lock thứ hai, được đặt tên theo cùng key (hai decorator trên một method dùng chung key này), giữ nó suốt lần chạy, gia hạn nó, và giải phóng nó khi lần chạy kết thúc. Một tick thấy lock đang bị giữ sẽ bị bỏ qua, trên instance này hay bất kỳ instance nào khác: các tick trong lúc một lần kiểm đếm dài bị bỏ đi, và tick đầu tiên sau nó sẽ chạy. Nếu lần chạy crash, lock hết hạn sau `ttl` và tick tiếp theo sẽ chạy. `@WithoutOverlapping()` đứng riêng, không có `@OnOneInstance()`, nghĩa là "bất kỳ instance nào, mỗi lúc một lần chạy".

Test điều khiển hai instance trên một `ManualLockClock`, giữ một lần kiểm đếm chưa kết thúc, và tua đồng hồ qua ba tick:

```typescript
@@filename(test/step-4.without-overlapping.e2e-spec)
it('with @WithoutOverlapping(), every tick during the run is skipped, then the next one runs', async () => {
  const [owner, other] = [await start(StepFourJob), await start(StepFourJob)];
  const slow = warehouse.pauseNext();
  const first = owner!.reconcileStock();
  await until(() => warehouse.counts === 1);
  for (let tick = 0; tick < 3; tick++) {
    await clock.advance('5m'); // the run goes on, its locks renewed
    await Promise.all([owner!.reconcileStock(), other!.reconcileStock()]);
  }
  expect(warehouse.counts).toBe(1);
  expect(logger.matching('Skipped StockReconciliationJob.reconcileStock: a run is still in progress')).toHaveLength(3);
  expect(logger.matching('Skipped StockReconciliationJob.reconcileStock: it runs on another instance')).toHaveLength(3);
  slow.resume();
  await first;
  await clock.advance('5m');
  await Promise.all([owner!.reconcileStock(), other!.reconcileStock()]);
  expect(warehouse.counts).toBe(2);
});
```

`clock.advance('5m')` kích hoạt mọi lần gia hạn tới hạn trên đường đi, theo thứ tự, và chờ từng lần tới được store, nên mười lăm phút của một lần chạy dài chỉ mất một khoảnh khắc, với các lock của lần chạy được gia hạn suốt thời gian đó.

#### Fence các thao tác ghi <a id="fence-the-writes"></a>

Một lease không thể ngăn một bên giữ đang bị dừng. Lấy job đối soát trên instance A làm ví dụ: nó đọc số lượng từ kho (hạt cá hồi: 12), rồi A bị treo, do một lần garbage collection stop-the-world, swap, di chuyển VM, hay một debugger. Nó ngừng gia hạn. Ba mươi giây sau database cho các lock của nó hết hạn, và B tiếp quản job ở tick tiếp theo của nó: nó đọc số lượng mới hơn (đã bán và giao ba bao kể từ đó: hạt cá hồi: 9) và ghi chúng. Rồi A tỉnh lại và chạy nốt lần chạy của mình, với số lượng nó đã đọc trước khi bị dừng. Hạt cá hồi quay về 12, và cửa hàng bán ba bao mà nó không có.

Signal của A bị abort ở lần gia hạn tiếp theo, khi database từ chối nó, nhưng một thao tác ghi đã đang trên đường đi vẫn sẽ được thực hiện. Hãy lưu ý lease hứa hẹn và không hứa hẹn điều gì. Một bên giữ tự đếm hạn chót của mình, `ttl` tính từ thời điểm nó gửi lần gia hạn cuối cùng mà store đã xác nhận, tức là trước khi store xử lý nó: một bên giữ đang chạy sẽ bỏ cuộc không muộn hơn thời điểm hết hạn của store, nên signal của nó bị abort trước khi bất kỳ instance nào khác có thể lấy key. Khoảng hở chỉ tồn tại với một bên giữ không chạy (bị dừng, bị stop, event loop bị block): từ thời điểm hết hạn của store cho tới khi nó chạy trở lại, nó vẫn tin rằng mình giữ lock. Thứ ngăn thao tác ghi của nó là **fencing token**: mỗi lần lấy một key đều nhận một token lớn hơn mọi token mà key đó từng có, và tài nguyên được ghi giữ token cao nhất mà nó đã thấy và từ chối token thấp hơn. Token của A thấp hơn của B, nên thao tác ghi muộn của A không cập nhật gì cả.

Bảng sản phẩm có thêm một cột cho việc này:

```typescript
@@filename(database/schema)
export const products = pgTable('products', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  /** In cents. */
  price: integer('price').notNull(),
  inStock: integer('in_stock').notNull(),
  /** The fencing token of the stock reconciliation run that last wrote `inStock`. */
  stockFencingToken: bigint('stock_fencing_token', { mode: 'number' }).notNull().default(0),
});
```

```bash
$ npx drizzle-kit generate --name=stock_fencing_token
$ npx drizzle-kit migrate
```

```sql
@@filename(drizzle/0003_stock_fencing_token.sql)
ALTER TABLE "products" ADD COLUMN "stock_fencing_token" bigint DEFAULT 0 NOT NULL;
```

Repository chỉ ghi một số lượng nếu chưa có lần chạy nào với token lớn hơn đã ghi sản phẩm đó, và ghi lại token mà nó dùng để ghi, trong cùng câu lệnh:

```typescript
@@filename(inventory/stock.repository)
import { Injectable } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { and, eq, lte } from 'drizzle-orm';
import type { Database } from '../database/drizzle.js';
import { products } from '../database/schema.js';
import type { StockCount } from './warehouse.client.js';

@Injectable()
export class StockRepository {
  constructor(@InjectDrizzle() private readonly db: Database) {}

  /**
   * Writes the counts a reconciliation run read, fenced by the run's token: a product that a
   * newer run (a greater token) already wrote is left alone.
   */
  async writeStock(counts: StockCount[], fencingToken: number): Promise<{ written: number; stale: number }> {
    let written = 0;
    for (const { productId, count } of counts) {
      const rows = await this.db
        .update(products)
        .set({ inStock: count, stockFencingToken: fencingToken })
        .where(and(eq(products.id, productId), lte(products.stockFencingToken, fencingToken)))
        .returning({ id: products.id });
      written += rows.length;
    }
    return { written, stale: counts.length - written };
  }
}
```

Job lấy token, và signal, từ `LocksContext`. `@nestjs/schedule` gọi method mà không có tham số, nên context mang chúng, qua `AsyncLocalStorage`, tới mọi service mà job gọi:

```typescript
@@filename(inventory/stock-reconciliation.job)
import { Injectable, Logger } from '@nestjs/common';
import { LocksContext, OnOneInstance, WithoutOverlapping } from '@nestjs/locks';
import { Cron, CronExpression } from '@nestjs/schedule';
import { StockRepository } from './stock.repository.js';
import { WarehouseClient } from './warehouse.client.js';

@Injectable()
export class StockReconciliationJob {
  private readonly logger = new Logger(StockReconciliationJob.name);

  constructor(
    private readonly warehouseClient: WarehouseClient,
    private readonly stockRepository: StockRepository,
    private readonly locksContext: LocksContext,
  ) {}

  @Cron(process.env.STOCK_RECONCILIATION_CRON ?? CronExpression.EVERY_5_MINUTES, { name: 'stock-reconciliation' })
  @OnOneInstance({ key: 'inventory:stock-reconciliation' })
  @WithoutOverlapping()
  async reconcileStock() {
    const { fencingToken, signal } = this.locksContext;
    // Aborts the count if this run loses its lock...
    const counts = await this.warehouseClient.stockCounts({ signal });
    // ...and the token stops a write that slips through anyway.
    const { written, stale } = await this.stockRepository.writeStock(counts, fencingToken!);
    if (stale > 0) {
      this.logger.warn(`Skipped ${stale} stale stock writes: a newer run (token > ${fencingToken}) wrote those products`);
    }
    this.logger.log(`Reconciled stock for ${written} products (fencing token ${fencingToken})`);
  }
}
```

Token là của run lock, một token mới và cao hơn cho mỗi lần chạy. Signal bị abort khi lock của lần chạy hoặc lease của instance bị mất, và reason của nó là một `LockLostError` cho biết việc mất lock được phát hiện thế nào: store đã từ chối một lần gia hạn, hoặc `ttl` đã trôi qua mà không có lần gia hạn nào tới được store. Hãy truyền signal cho những gì job gọi tới, `fetch`, database driver, một HTTP client; một job bỏ qua nó sẽ tiếp tục chạy, như trong bất kỳ process nào. Không có gì bị kill.

Test tái hiện việc bị dừng trên PostgreSQL. Instance A chạy trên một `ManualLockClock`, nên nó ngừng gia hạn; warehouse client giữ lần kiểm đếm của A chưa kết thúc sau khi A đã đọc nó; hàng trên kệ thay đổi; B tiếp quản 1.2 giây sau (`ttl` của test là một giây) và ghi hạt cá hồi: 9. Rồi lần kiểm đếm của A tiếp tục:

```typescript
@@filename(test/step-5.fencing.e2e-spec)
it('without fencing, the paused instance overwrites the fresh count with its stale one', async () => {
  const { stale, resume } = await pauseAWhileBTakesOver(UnfencedJob);
  resume(); // A wakes up and writes what it read before the pause
  expect(await stale).toBeUndefined();
  expect(await kibble()).toBe(12); // three bags the store doesn't have
});

it("with the run's fencing token, the database refuses the stale write", async () => {
  const { stale, resume } = await pauseAWhileBTakesOver(StockReconciliationJob);
  resume(); // A wakes up before it noticed it lost its locks, and writes
  expect(await stale).toBeUndefined();
  expect(await kibble()).toBe(9);
  expect(logger.matching(/WARN Skipped 3 stale stock writes: a newer run \(token > \d+\) wrote those products/)).toHaveLength(1);
  const tokens = await database.query<{ stock_fencing_token: string }>('SELECT DISTINCT stock_fencing_token FROM products');
  expect(tokens).toHaveLength(1); // every product carries B's token
});

it('a run that notices it lost its lock stops at its signal, before writing', async () => {
  const { stale, resume } = await pauseAWhileBTakesOver(StockReconciliationJob);
  await clockA.advance('1s'); // A's clock moves: its next renewal is refused
  expect(await stale).toBeInstanceOf(LockLostError);
  resume();
  expect(await kibble()).toBe(9);
  expect(logger.matching(/WARN Lost the lock "inventory:stock-reconciliation(:owner)?"/).length).toBeGreaterThan(0);
});
```

Với job của phần trước, thao tác ghi cũ được thực hiện và hạt cá hồi quay về 12. Với token, database từ chối nó, và job log ra rằng nó đã bỏ qua ba thao tác ghi cũ. Còn một lần chạy tới được lần gia hạn tiếp theo trước khi ghi sẽ dừng lại ở signal, với một `LockLostError`, và không ghi gì cả. Package log một cảnh báo cho mỗi lock bị mất và phát ra một event `lock-lost`, vì một lock bị mất nghĩa là một instance khác có thể đang ở trong cùng critical section ngay lúc này: chỉ có token giữ hai bên tách biệt.
#### Chạy export thủ công <a id="run-the-export-by-hand"></a>

Thỉnh thoảng bộ phận kế toán yêu cầu export trước 02:00. Một admin endpoint chạy nó, và nó không bao giờ được chạy song song với lần chạy theo lịch, trên bất kỳ instance nào. Lần chạy theo lịch giữ lock được đặt tên theo key của nó; endpoint lấy cùng lock đó bằng `Locks.withLock()`, chờ tối đa hai giây cho một lần chạy sắp kết thúc:

```typescript
@@filename(invoices/invoice-exports.controller)
import { ConflictException, Controller, HttpCode, Post, UseGuards } from '@nestjs/common';
import { LockNotAcquiredError, Locks } from '@nestjs/locks';
import { AdminGuard } from '../admin/admin.guard.js';
import { INVOICE_EXPORT_LOCK, InvoiceExportJob } from './invoice-export.job.js';

@Controller('admin/invoice-exports')
@UseGuards(AdminGuard)
export class InvoiceExportsController {
  constructor(
    private readonly locks: Locks,
    private readonly invoiceExportJob: InvoiceExportJob,
  ) {}

  /** Runs the export now, unless a run (scheduled or not) holds its lock. */
  @Post()
  @HttpCode(200)
  async exportNow() {
    try {
      return await this.locks.withLock(INVOICE_EXPORT_LOCK, () => this.invoiceExportJob.export(), { wait: '2s' });
    } catch (error) {
      if (error instanceof LockNotAcquiredError) {
        throw new ConflictException('An invoice export is already running. Try again when it has finished.');
      }
      throw error;
    }
  }
}
```

Job export key dưới dạng hằng số, cũng có thêm `@WithoutOverlapping()`, và tách phần công việc ra khỏi method theo lịch để endpoint có thể gọi nó và trả về kết quả:

```typescript
@@filename(invoices/invoice-export.job)
/** The export's lock: held by a run, scheduled or started by hand. */
export const INVOICE_EXPORT_LOCK = 'invoices:nightly-export';

export interface InvoiceExportResult {
  exported: number;
  batchId?: string;
}
```

```typescript
@@filename(invoices/invoice-export.job)
@Cron(process.env.INVOICE_EXPORT_CRON ?? '0 2 * * *', { name: 'invoice-export', timeZone: 'Europe/Warsaw' })
@OnOneInstance({ key: INVOICE_EXPORT_LOCK })
@WithoutOverlapping()
async exportInvoices() {
  await this.export();
}

/** Call it under the INVOICE_EXPORT_LOCK lock. */
async export(): Promise<InvoiceExportResult> {
```

`withLock(key, fn, options)` chạy `fn` dưới lock và giải phóng lock dù `fn` resolve hay throw. `wait` là khoảng thời gian tiếp tục thử, kèm backoff, trước khi bỏ cuộc với một `LockNotAcquiredError`; mặc định là chỉ thử một lần. `acquire(key, options)` cũng vậy nhưng không có callback: nó resolve một `Lock`, hoặc `null` khi key đã bị chiếm, và bạn tự giải phóng nó, hoặc dùng `await using`. Một `Lock` có `fencingToken` và `signal`, và bên trong `withLock()` thì `LocksContext` cũng có, y như trong một job.

Cả hai cũng nhận một `signal` riêng, chẳng hạn signal của request, để dừng việc chờ. Nó cũng dừng việc chờ store: một lời gọi vẫn đang chờ câu trả lời của store sẽ reject với reason của signal, `fn` không chạy, và một lock mà store cấp sau đó sẽ được trả lại cho store. `wait` không cắt ngang một lời gọi store đang trên đường đi; `storeTimeout` của module mới làm việc đó, nên một lời gọi mất tối đa `wait` cộng `storeTimeout`. Một store không trả lời trong vòng `storeTimeout` sẽ làm lời gọi thất bại với một `LockStoreTimeoutError`.

Cả `LockNotAcquiredError` lẫn `LockStoreTimeoutError` đều không mang HTTP status: tranh chấp lock và một store bị treo không phải lỗi của bên gọi, nên handler tự quyết định. Ở đây một lock đã bị chiếm là `409`, còn mọi thứ khác được throw lại. Trong khi export đang chạy thủ công, tick theo lịch trên bất kỳ instance nào sẽ thấy lock đang bị giữ và bỏ qua.

> info **Gợi ý** `AdminGuard` chỉ là placeholder. Hãy bảo vệ route bằng [phân quyền](/security/authorization) thật của ứng dụng.

#### Store trên Redis <a id="the-store-on-redis"></a>

Store là một hợp đồng, nên nó có thể nằm ở bất cứ đâu mà các instance của bạn đã cùng truy cập. Nếu đó là Redis, mỗi method là một Lua script, được Redis chạy một cách nguyên tử:

```typescript
@@filename(redis/redis-lock.store)
import { Inject, Injectable } from '@nestjs/common';
import { LocksStorage, type LockAcquireResult, type LockStore } from '@nestjs/locks';
import { REDIS } from './redis.module.js';

/** The one ioredis method this store needs. */
export interface RedisEval {
  eval(script: string, numKeys: number, ...args: (string | number)[]): Promise<unknown>;
}

// Takes the lock if nobody holds it, expiring on Redis's clock, and draws a fencing token
// from a counter that never goes back. Returns the token, or 0.
const ACQUIRE = `
if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2]) then
  return redis.call('INCR', KEYS[2])
end
return 0
`;

// Renews the lock, if it is still ours.
const RENEW = `
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('PEXPIRE', KEYS[1], ARGV[2])
end
return 0
`;

// Deletes the lock, if it is still ours.
const RELEASE = `
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
`;

/** Where the fencing counter lives; no lock key can be named like it. */
const FENCING_COUNTER = 'locks:fencing-token';

@Injectable()
export class RedisLockStore implements LockStore {
  constructor(
    @Inject(REDIS) private readonly redis: RedisEval,
    storage: LocksStorage,
  ) {
    storage.registerSource(this);
  }

  async acquire(key: string, owner: string, ttl: number): Promise<LockAcquireResult> {
    const token = Number(await this.redis.eval(ACQUIRE, 2, this.key(key), FENCING_COUNTER, owner, ttl));
    return token > 0 ? { acquired: true, fencingToken: token } : { acquired: false };
  }

  async renew(key: string, owner: string, ttl: number): Promise<boolean> {
    return (await this.redis.eval(RENEW, 1, this.key(key), owner, ttl)) === 1;
  }

  async release(key: string, owner: string): Promise<boolean> {
    return (await this.redis.eval(RELEASE, 1, this.key(key), owner)) === 1;
  }

  private key(key: string) {
    return `locks:key:${key}`;
  }
}
```

`SET NX PX` chỉ lấy key nếu nó còn trống, hết hạn theo đồng hồ của Redis tính bằng mili giây, và `INCR` trong cùng script lấy token từ một bộ đếm dùng chung cho mọi key. Fencing chỉ bền vững ngang với bộ đếm đó. Nó không bao giờ hết hạn, và không bao giờ được quay ngược: hãy cho Redis cơ chế persistence (AOF, hoặc RDB với khoảng thời gian ngắn) và `maxmemory-policy noeviction`, vì một bộ đếm bắt đầu lại từ 1 (một lần restart không có persistence, một lệnh `FLUSHALL`) sẽ phát ra những token mà các bên giữ đã có, và một lock bị evict do thiếu bộ nhớ là một lock bị mất. Một lần failover sang một replica bất đồng bộ cũng có thể làm mất những lần ghi cuối cùng: một lock được lấy ngay trước đó, đó là trường hợp bên giữ bị dừng mà token bao phủ, nhưng cũng có thể là những lần tăng cuối cùng của bộ đếm, sau đó bên giữ tiếp theo có thể lấy một token mà bên trước đã có, và token không còn phân biệt được chúng nữa. Ở những nơi fencing phải giữ vững qua một lần failover, hãy giữ các lock trong database, nơi sequence nằm trong cùng WAL với các dòng dữ liệu, hoặc replicate Redis một cách đồng bộ.

Trên Redis Cluster, `ACQUIRE` như đang viết sẽ thất bại với lỗi `CROSSSLOT`: một cluster chỉ chạy script khi mọi key của nó hash vào cùng một slot, mà key của lock và bộ đếm thì không. Hãy đặt tên cả hai dưới một hash tag, `{{ '{' }}locks{{ '}' }}:key:<key>` và `{{ '{' }}locks{{ '}' }}:fencing-token`: khi đó cluster chỉ hash phần `locks`, nên bộ đếm và mọi lock dùng chung một slot, trên một shard. Một bộ đếm dưới tên mới, hoặc trên một cluster mới, sẽ bắt đầu lại từ 1, chính là lần khởi động lại mà nó không bao giờ được phép có. Trước lần acquire đầu tiên trên nó, hãy dừng các instance đang dùng key cũ và đặt bộ đếm mới bằng giá trị của bộ đếm cũ (`SET {{ '{' }}locks{{ '}' }}:fencing-token <value>`), để token tiếp theo lớn hơn mọi token đã được phát ra.

`redis.module` cung cấp client dưới token `REDIS`; ví dụ dùng một client tối giản có signature `eval()` giống ioredis, để không phụ thuộc vào gì, còn trong ứng dụng của bạn thì đó là `new Redis(process.env.REDIS_URL)`:

```typescript
@@filename(redis/redis.module)
import { Global, Inject, Module, type OnApplicationShutdown } from '@nestjs/common';
import { RedisClient } from './redis.client.js';

export const REDIS = Symbol('REDIS');

@Global()
@Module({
  providers: [
    {
      provide: REDIS,
      // With ioredis: new Redis(process.env.REDIS_URL)
      useFactory: () => new RedisClient(process.env.REDIS_URL ?? 'redis://127.0.0.1:6379'),
    },
  ],
  exports: [REDIS],
})
export class RedisModule implements OnApplicationShutdown {
  constructor(@Inject(REDIS) private readonly redis: RedisClient) {}

  // After onModuleDestroy(), where running jobs finish and hand their locks back.
  async onApplicationShutdown() {
    await this.redis.quit();
  }
}
```

Thay provider trong application module, và không có gì khác thay đổi:

```typescript
@@filename(app.module.step-7)
@Module({
  imports: [
    DrizzleModule.forRootAsync({
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema }),
    }),
    RedisModule,
    ScheduleModule.forRoot(),
    LocksModule.forRoot(),
    InvoicesModule,
    InventoryModule,
  ],
  providers: [RedisLockStore],
})
export class AppModule {}
```

Ví dụ chạy contract suite trên một `redis-server` thật, với tám kết nối để các lời gọi chồng lấn, rồi chạy ba instance của ứng dụng trên đó:

```typescript
@@filename(test/step-7.redis-lock-store.e2e-spec)
describe('the LockStore contract', () => {
  // Several connections, so calls really overlap; expiry is Redis's own clock (real time).
  const pool = Array.from({ length: 8 }, () => new RedisLockStore(connect(), new LocksStorage()));
  let next = 0;
  const cases = lockStoreContract(() => pool[next++ % pool.length]!, { concurrent: true });
  for (const c of cases) {
    it(c.name, c.run);
  }
});
```

Hãy đóng Redis client trong `onApplicationShutdown()`, như module làm; `@nestjs/drizzle` đóng database pool trong cùng giai đoạn đó. Nest chạy từng giai đoạn shutdown cho toàn bộ ứng dụng trước khi sang giai đoạn tiếp theo: package trả lại các lease trong `onModuleDestroy()` và giải phóng mọi lock khác còn đang giữ trong `beforeApplicationShutdown()`, nên tới lúc `onApplicationShutdown()` của bất kỳ module nào chạy, không có gì của package còn cần tới kết nối, bất kể thứ tự import. Một tick hoặc một election vẫn đang chờ store khi quá trình shutdown bắt đầu sẽ ngừng chờ: tick bị bỏ qua, và một lock mà store cấp sau đó sẽ được trả lại cho store, nên một store bị treo không làm chậm lần deploy.

#### Giữ luồng dữ liệu của kho trên một instance <a id="hold-the-warehouse-feed-on-one-instance"></a>

Kho đẩy các cảnh báo sắp hết hàng qua một luồng dữ liệu (feed) chỉ cho phép một kết nối cho mỗi cửa hàng. Đó không phải là một scheduled job; đó là một kết nối mà một instance nên giữ chừng nào nó còn sống, và một instance khác nên tiếp quản khi nó bị down. Đó là một leader election, và nó chính là lease giống như quyền sở hữu một job, được giữ một cách có chủ đích:

```typescript
@@filename(inventory/warehouse-feed)
import { Injectable, Logger } from '@nestjs/common';
import { LeaderElection, type Lock, type OnLeadershipAcquired, type OnLeadershipLost } from '@nestjs/locks';
import { WarehouseClient } from './warehouse.client.js';

/**
 * The warehouse's alert feed allows one connection per shop, so one instance of the app
 * holds it: the leader. When the leader goes down, another instance connects within the
 * lease's `ttl`.
 */
@Injectable()
@LeaderElection('inventory:warehouse-feed')
export class WarehouseFeed implements OnLeadershipAcquired, OnLeadershipLost {
  private readonly logger = new Logger(WarehouseFeed.name);

  constructor(private readonly warehouseClient: WarehouseClient) {}

  onLeadershipAcquired(lock: Lock) {
    this.logger.log(`Connected to the warehouse feed (fencing token ${lock.fencingToken})`);
    // The connection ends with the leadership: `lock.signal` aborts when the lease is lost
    // or this instance steps down.
    this.warehouseClient.subscribe(
      (alert) => this.logger.warn(`Low stock: ${alert.count} left of ${alert.productId}`),
      { signal: lock.signal },
    );
  }

  onLeadershipLost() {
    this.logger.log('Disconnected from the warehouse feed');
  }
}
```

```typescript
@@filename(inventory/inventory.module)
import { Module } from '@nestjs/common';
import { StockReconciliationJob } from './stock-reconciliation.job.js';
import { StockRepository } from './stock.repository.js';
import { WarehouseClient } from './warehouse.client.js';
import { WarehouseFeed } from './warehouse-feed.js';

@Module({
  providers: [StockReconciliationJob, StockRepository, WarehouseClient, WarehouseFeed],
})
export class InventoryModule {}
```

`@LeaderElection(key)` đặt trên một singleton provider. Từ `onApplicationBootstrap`, mọi instance đều cố lấy lease trên key, và tiếp tục thử mỗi `ttl / 3`; instance đang giữ nó sẽ gia hạn nó. `onLeadershipAcquired(lock)` chạy khi instance này trở thành leader, với `signal` và `fencingToken` của lease; `onLeadershipLost(lock)` chạy khi nó thôi làm leader, vì lease bị mất hoặc vì nó tự rút lui, lúc shutdown hoặc sau khi `onLeadershipAcquired()` throw. Tùy chọn `ttl` đặt ttl của lease; mặc định là 30 giây của module, nên một leader bị crash sẽ được thay thế trong vòng nửa phút, và một leader shutdown bình thường sẽ được thay thế ở lần thử tiếp theo của các instance khác.

Test khởi động ba instance và cho thấy một kết nối, một lần chuyển giao khi shutdown, và điểm mù của leader bị dừng:

```typescript
@@filename(test/step-8.leader-election.e2e-spec)
await until(() => connected().length === 2, 10_000); // the lease expired in the database
warehouse.notify({ productId: 'salmon-kibble-2kg', count: 2 });
// Both receive it: the paused leader hasn't noticed yet. Anything it writes on the feed's
// behalf needs its fencing token, which is lower than the new leader's.
expect(logger.matching('WARN Low stock: 2 left of salmon-kibble-2kg')).toHaveLength(2);
// The old leader wakes up: its renewal is refused, and it learns it lost the lease.
await clock.advance('3s');
expect(leading.get(crashed)).toBe(false);
expect(disconnected()).toHaveLength(1);
```

Một leader bị dừng vẫn được kết nối cho tới khi lần gia hạn tiếp theo của nó thất bại, và nhận những gì feed gửi tới trong khoảng đó. Đó là cùng điểm mù như trong [Fence các thao tác ghi](/reliability/locks#fence-the-writes), với cùng câu trả lời: những gì leader làm thay cho cả nhóm phải mang theo token của lease.

#### Chạy thử <a id="try-it"></a>

Tạo database và áp dụng migration:

```bash
$ psql postgres://localhost:5432/postgres -c 'CREATE DATABASE store'
$ DATABASE_URL=postgres://localhost:5432/store npx drizzle-kit migrate
```

Khởi động ba instance trên các port 3001, 3002 và 3003, với `ADMIN_TOKEN=s3cret` và job đối soát kho mỗi mười giây thay vì năm phút, để có gì đó mà theo dõi: `STOCK_RECONCILIATION_CRON='*/10 * * * * *'`. Mỗi instance log ra lock store mà nó đã đăng ký. Instance khởi động đầu tiên làm leader cho feed của kho, và lấy job đối soát ở tick đầu tiên, trước khi hai instance còn lại khởi động xong:

```bash
[Nest] 48817  - 09/25/2026, 8:59:26 AM     LOG [LocksModule] LocksStorage: DrizzleLockStore
[Nest] 48817  - 09/25/2026, 8:59:26 AM     LOG [NestApplication] Nest application successfully started +9ms
[Nest] 48817  - 09/25/2026, 8:59:26 AM     LOG [Locks] Leading "inventory:warehouse-feed" (fencing token 1)
[Nest] 48817  - 09/25/2026, 8:59:26 AM     LOG [WarehouseFeed] Connected to the warehouse feed (fencing token 1)
[Nest] 48817  - 09/25/2026, 8:59:30 AM     LOG [Locks] StockReconciliationJob.reconcileStock runs on this instance (lease "inventory:stock-reconciliation:owner", fencing token 2)
[Nest] 48817  - 09/25/2026, 8:59:30 AM     LOG [WarehouseClient] Counted 3 products
[Nest] 48817  - 09/25/2026, 8:59:30 AM     LOG [StockReconciliationJob] Reconciled stock for 3 products (fencing token 3)
[Nest] 48817  - 09/25/2026, 8:59:40 AM     LOG [WarehouseClient] Counted 3 products
[Nest] 48817  - 09/25/2026, 8:59:40 AM     LOG [StockReconciliationJob] Reconciled stock for 3 products (fencing token 9)
```

Hai instance còn lại bỏ qua mọi tick, ở mức debug:

```bash
[Nest] 48849  - 09/25/2026, 8:59:40 AM   DEBUG [Locks] Skipped StockReconciliationJob.reconcileStock: it runs on another instance
[Nest] 48849  - 09/25/2026, 8:59:50 AM   DEBUG [Locks] Skipped StockReconciliationJob.reconcileStock: it runs on another instance
```

Bảng lock hiển thị lease, run lock (đã được giải phóng, nên owner của nó là null, và token của nó tăng sau mỗi lần chạy) và lease của feed. Mọi lock hết hạn ba mươi giây sau lần gia hạn cuối cùng, theo đồng hồ của database:

```bash
$ psql postgres://localhost:5432/store -c "SELECT key, owner, fencing_token, expires_at - clock_timestamp() AS expires_in FROM locks ORDER BY key"
                 key                  |                owner                 | fencing_token |   expires_in
--------------------------------------+--------------------------------------+---------------+-----------------
 inventory:stock-reconciliation       |                                      |             9 | 00:00:26.026727
 inventory:stock-reconciliation:owner | 1feff401-d3c9-41b1-a559-d7b458e2905f |             2 | 00:00:26.054034
 inventory:warehouse-feed             | a4980740-ae27-4d95-af0b-0935d65fffb9 |             1 | 00:00:22.784351
(3 rows)
```

Các fencing token có những khoảng trống: một lần lấy lock bị từ chối vẫn đã tiêu thụ một giá trị từ sequence. Chạy export thủ công. Không có admin token, guard trả lời `403`; sau đó gửi đồng thời hai request, tới hai instance khác nhau:

```bash
$ curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:3002/admin/invoice-exports
403
$ for port in 3002 3003; do (curl -s -X POST localhost:$port/admin/invoice-exports -H 'x-admin-token: s3cret'; echo) & done; wait
{"exported":3,"batchId":"acc_447817af"}
{"exported":0}
```

Một request đã lấy lock và export ba đơn hàng đang chờ. Request kia chờ nó, lấy lock khi nó được giải phóng, và không còn gì để export. Một request chờ quá hai giây sẽ nhận `409`. Instance đã chạy export log ra batch:

```bash
[Nest] 48849  - 09/25/2026, 8:59:44 AM     LOG [AccountingClient] Booked batch acc_447817af: ord_1001, ord_1002, ord_1004
[Nest] 48849  - 09/25/2026, 8:59:44 AM     LOG [InvoiceExportJob] Exported 3 invoices in batch acc_447817af
```

Giờ hãy kill instance đầu tiên, instance đang chạy job đối soát và làm leader cho feed, mà không cho nó cơ hội dọn dẹp:

```bash
$ kill -9 48817
```

Một lúc không có gì xảy ra: hai instance còn lại tiếp tục bỏ qua, vì các lease vẫn còn trong bảng. Ba mươi giây sau lần gia hạn cuối cùng, từng lease hết hạn. Lease của feed hết hạn trước, vì nó được gia hạn theo lịch riêng, và tick tiếp theo tiếp quản job:

```bash
[Nest] 48849  - 09/25/2026, 9:00:11 AM     LOG [Locks] Leading "inventory:warehouse-feed" (fencing token 28)
[Nest] 48849  - 09/25/2026, 9:00:11 AM     LOG [WarehouseFeed] Connected to the warehouse feed (fencing token 28)
[Nest] 48849  - 09/25/2026, 9:00:20 AM     LOG [Locks] StockReconciliationJob.reconcileStock runs on this instance (lease "inventory:stock-reconciliation:owner", fencing token 32)
[Nest] 48849  - 09/25/2026, 9:00:20 AM     LOG [WarehouseClient] Counted 3 products
[Nest] 48849  - 09/25/2026, 9:00:20 AM     LOG [StockReconciliationJob] Reconciled stock for 3 products (fencing token 34)
```

Lần này hãy dừng owner mới bằng `Ctrl+C`. Các shutdown hook của nó trả lại cả hai lease (`main.ts` gọi `app.enableShutdownHooks()`):

```bash
[Nest] 48849  - 09/25/2026, 9:00:35 AM     LOG [Locks] Stepped down from "inventory:warehouse-feed"
[Nest] 48849  - 09/25/2026, 9:00:35 AM     LOG [WarehouseFeed] Disconnected from the warehouse feed
```

Instance cuối cùng lấy job ở tick tiếp theo, và lấy feed ở lần tranh cử tiếp theo, chỉ vài giây sau thay vì ba mươi giây:

```bash
[Nest] 48859  - 09/25/2026, 9:00:40 AM     LOG [Locks] StockReconciliationJob.reconcileStock runs on this instance (lease "inventory:stock-reconciliation:owner", fencing token 41)
[Nest] 48859  - 09/25/2026, 9:00:40 AM     LOG [WarehouseClient] Counted 3 products
[Nest] 48859  - 09/25/2026, 9:00:40 AM     LOG [StockReconciliationJob] Reconciled stock for 3 products (fencing token 43)
[Nest] 48859  - 09/25/2026, 9:00:41 AM     LOG [Locks] Leading "inventory:warehouse-feed" (fencing token 45)
[Nest] 48859  - 09/25/2026, 9:00:41 AM     LOG [WarehouseFeed] Connected to the warehouse feed (fencing token 45)
```

Cuối cùng dừng instance cuối cùng bằng `Ctrl+C`. Nó rút lui khỏi feed trước khi tắt:

```bash
[Nest] 48859  - 09/25/2026, 9:00:50 AM     LOG [Locks] Stepped down from "inventory:warehouse-feed"
[Nest] 48859  - 09/25/2026, 9:00:50 AM     LOG [WarehouseFeed] Disconnected from the warehouse feed
```

#### Testing

Một ứng dụng import `LocksModule` mà không đăng ký store nào sẽ chạy trên store trong bộ nhớ, nên một test end-to-end với một instance không cần gì cả: mọi tick đều chạy, một lần. Để loại store Drizzle ra khỏi một test, hãy override provider của nó bằng một `InMemoryLockStore` thuần; một instance thuần không tự đăng ký, nên mặc định trong bộ nhớ được áp dụng.

Để test đúng mục đích của package, hãy chạy nhiều instance trong một process. Một instance là một ứng dụng Nest; các instance của một ứng dụng dùng chung một store. Helper của ví dụ khởi động một instance trên database dùng chung, với các bản giả và tùy chọn `LocksModule` của test:

```typescript
@@filename(test/helpers)
export async function startInstance(options: InstanceOptions): Promise<TestingModule> {
  if (options.database.url) {
    process.env.DATABASE_URL = options.database.url;
  }
  let builder = Test.createTestingModule({ imports: [options.module] })
    .overrideProvider(AccountingClient)
    .useValue(options.accounting)
    .overrideProvider(WarehouseClient)
    .useValue(options.warehouse);
  if (options.database.pglite) {
    builder = builder.overrideProvider(getDrizzleToken()).useValue(options.database.pglite);
  }
  if (options.locks) {
    builder = builder.overrideProvider(LOCKS_MODULE_OPTIONS).useValue(options.locks);
  }
  const app = await builder.compile();
  app.useLogger(options.logger);
  options.onCompiled?.(app);
  await app.init();
  return app;
}
```

- **Dùng chung database.** Trên PGlite, mọi instance nhận cùng một Drizzle database bằng cách override database mà `DrizzleModule` đăng ký (`getDrizzleToken()`), với các migration thật đã được áp dụng; `DrizzleLockStore` inject nó bằng `@InjectDrizzle()`, nên các instance dùng chung bảng lock giống như trong production. Với một PostgreSQL server, mỗi instance mở pool riêng từ URL của database. Không có database, hãy dùng chung một `InMemoryLockStore` giữa các instance bằng cách đăng ký nó trong từng instance với `LocksStorage.registerSource()` và tùy chọn `replace` của nó trước `init()`.
- **Tự kích hoạt các job.** Gọi method (`await job.exportInvoices()`) trên từng instance, hoặc đi qua `@nestjs/schedule` với `schedulerRegistry.getCronJob(name).fireOnTick()`. Cả hai đều tới được wrapper. Trỏ các lịch chạy thật tới một ngày không bao giờ tới: `vitest.config.mts` của ví dụ đặt hai biến cron thành ngày 29 tháng 2 lúc 3 giờ sáng.
- **Kiểm soát thời gian.** Override `LOCKS_MODULE_OPTIONS` với một `ManualLockClock`, và mọi lần gia hạn, hạn chót và `wait` trong instance đó chỉ dịch chuyển khi test tua đồng hồ: `await clock.advance('5m')` kích hoạt những gì tới hạn trên đường đi, theo thứ tự, và chờ từng lần gia hạn tới được store. Một instance mà bạn không tua đồng hồ chính là một process bị dừng. Với PGlite hoặc một server, đồng hồ của store là thời gian thực, nên một `ttl` ngắn (`'1s'`) và một `sleep` sẽ làm các lock của instance bị dừng hết hạn; với store trong bộ nhớ, hãy cho nó cùng `ManualLockClock` và thời hạn sẽ dịch chuyển theo đồng hồ đó.
- **Assert trên log** hoặc trên `LocksEvents`: instance nào chạy một job, mọi tick bị bỏ qua (`jobSkips$`), mọi lock bị mất và mọi thay đổi leader (`events$`). Các event cũng được publish trên các diagnostics channel `nestjs:locks:job-skipped`, `nestjs:locks:lock-lost`, `nestjs:locks:leadership-acquired` và `nestjs:locks:leadership-lost`.
- **Test store của bạn** bằng contract suite, như các store Drizzle, TypeORM và Redis đã làm, trên server mà bạn chạy trong production.

Xem [End-to-end testing](/fundamentals/testing#end-to-end-testing) để biết thêm về cách thiết lập testing.

#### Checklist cho production <a id="production-checklist"></a>

- Đăng ký một store dùng chung, trên database của bạn hoặc Redis, và chạy contract suite trên nó với `concurrent` được bật, trong CI, trên phiên bản mà bạn chạy trong production. Trong production, ứng dụng từ chối khởi động nếu không có store, trừ khi đặt `allowInMemoryStorage`, vốn chỉ đúng cho một instance duy nhất.
- Đặt `key` cho mọi job không bao giờ được chạy hai lần, để một lần đổi tên hoặc một minifier không thể thay đổi nó trong một lần rolling deploy.
- Chọn một `ttl` lớn hơn hẳn thời gian round trip tới store và thời gian event loop bị treo lâu nhất mà bạn chấp nhận, và đủ ngắn để một lần crash không bỏ qua quá nhiều tick. Các lần gia hạn được gửi đi mỗi `ttl / 3`; 30 giây phù hợp với hầu hết các job. Run lock của một job dài được gia hạn với cùng nhịp độ, nên `ttl` của nó không cần bao phủ cả lần chạy.
- Để `storeTimeout` lớn hơn hẳn câu trả lời chậm nhất khi store vẫn khỏe mạnh: một lời gọi store chạy quá mức đó sẽ thất bại, nên tick không chạy và `acquire()` reject với `LockStoreTimeoutError`. Mặc định, 10 giây, cũng giới hạn thời gian một store bị treo (một pool cạn kiệt, một lần failover, một Redis client xếp hàng lệnh khi đang offline) làm chậm một job, một request hay một lần gia hạn.
- Viết job làm những gì đã tới hạn, chứ không phải những gì tick đó nhắm tới. Các tick bị lỡ không được chạy bù: một owner bị crash làm mất tối đa `ttl` các tick, và các tick trong lúc một lần chạy dài bị bỏ qua.
- Truyền `LocksContext.signal` cho những gì job gọi tới, và fence các thao tác ghi không thể hoàn tác bằng `LocksContext.fencingToken`, trong cùng câu lệnh ghi. Cảnh báo khi có `lock-lost` từ `LocksEvents` hoặc diagnostics channel: nó nghĩa là các lần gia hạn đã thất bại lâu hơn `ttl`, vì không kết nối được tới store hoặc event loop bị block, và một instance khác có thể đang chạy cùng critical section.
- Gọi `app.enableShutdownHooks()`, để một lần deploy chuyển giao các lease ngay lập tức thay vì để chúng tự hết hạn. Đóng Redis client trong `onApplicationShutdown()`, giai đoạn mà `@nestjs/drizzle` đóng database pool: package trả lại các lease trong `onModuleDestroy()` và giải phóng mọi lock khác trong `beforeApplicationShutdown()`, những giai đoạn mà Nest hoàn tất trước cho toàn bộ ứng dụng. Một lease có job bắt đầu chưa tới một giây trước khi shutdown sẽ được giữ cho hết giây đó thay vì được trả lại, để các instance kích hoạt cùng tick sẽ bỏ qua nó thay vì chạy nó lần thứ hai.
- Với store Redis, hãy cho Redis cơ chế persistence và `maxmemory-policy noeviction`. Bộ đếm fencing không bao giờ được quay ngược, và một lock không bao giờ được bị evict.
- Với store database, hãy tạo bảng và sequence qua migration, và định cỡ connection pool cho mỗi lock đang giữ một câu lệnh ngắn mỗi lần gia hạn, cộng thêm mỗi instance một câu cho mỗi tick.
- Dù sao vẫn nên giữ đồng hồ của các instance được đồng bộ bằng NTP. Thời hạn được đo trên đồng hồ của store, nhưng một bên giữ tự đếm hạn chót của mình, và `@nestjs/schedule` kích hoạt theo đồng hồ của instance.
- Mức log: các tick bị bỏ qua được log ở mức `debug`. Hãy giữ mức đó một thời gian sau khi rollout, để thấy các job ổn định trên một instance. Để theo dõi lâu dài, hãy đếm `LocksEvents.jobSkips$` theo `job` và `reason` thay vì parse log.

#### Hợp đồng của store <a id="the-store-contract"></a>

Bài hướng dẫn đã viết store bằng Drizzle, TypeORM và Redis. Phần này tóm tắt những gì bất kỳ `LockStore` nào cũng phải làm, để bạn viết store với một database hoặc ORM khác. [Interface `LockStore`](https://github.com/nestjs/locks/blob/master/lib/interfaces/lock-store.interface.ts) mô tả toàn bộ hợp đồng và các tình huống race mà mỗi quy tắc ngăn chặn.

**Đăng ký.** Store là một singleton provider bình thường gọi `registerSource(this)` trên `LocksStorage` (có thể inject) trong constructor của nó. Registry kiểm tra cấu trúc ngay lập tức, từ chối lần đăng ký thứ hai trừ khi truyền `replace: true`, và bị khóa khi `LocksModule` khởi tạo, đồng thời log ra store đang dùng. Không có gì được đăng ký, module dùng `InMemoryLockStore`, store chỉ loại trừ các bên gọi trong một process. Với `NODE_ENV=production`, việc khởi động sẽ thất bại thay vào đó, trừ khi bạn đặt `allowInMemoryStorage: true`.

**Các method.** Cả ba đều nguyên tử: mỗi method quyết định ai giữ một key, và một lần đọc theo sau là một lần ghi riêng sẽ để hai bên gọi cùng vào critical section, chính là lần chạy trùng lặp mà package sinh ra để ngăn chặn.

| Method | Làm gì | Giữ tính nguyên tử bằng cách nào |
| --- | --- | --- |
| `acquire(key, owner, ttl)` | Lấy key nếu không có lock nào còn hiệu lực đang giữ nó (không có, đã giải phóng, hoặc đã hết hạn), với một fencing token lớn hơn mọi token mà key từng có | Một câu insert tiếp quản một dòng đã giải phóng hoặc đã hết hạn trong cùng câu lệnh, kiểm tra lại thời hạn trong thao tác ghi, nên trong nhiều bên gọi đồng thời chỉ đúng một bên thắng; token được lấy sau bước kiểm tra |
| `renew(key, owner, ttl)` | Dời thời hạn của lock còn hiệu lực của owner thành `ttl` tính từ bây giờ | Một compare-and-set: owner và thời hạn nằm trong `WHERE` của câu lệnh ghi |
| `release(key, owner)` | Giải phóng lock còn hiệu lực của owner (xóa nó, hoặc đánh dấu là đã giải phóng), để bên gọi tiếp theo lấy được ngay. Không bao giờ reset token của key | Một compare-and-set, như `renew()` |

**Những điều khác mà store phải làm đúng**, tất cả đều được suite kiểm tra: một lock đã hết hạn coi như không tồn tại, với mọi method, dù nó đã bị xóa hay chưa (`expires_at > now` trong mọi điều kiện, hoặc để server tự cho nó hết hạn); `ttl` được đo trên đồng hồ của store, tính bằng mili giây, và có thể dài hàng tuần (vượt quá số nguyên 32-bit: `bigint`, `PEXPIRE`); key là chuỗi dài tối đa 500 ký tự, bất kỳ ký tự Unicode nào, được phân biệt chính xác; token là các số nguyên dương an toàn được trả về dưới dạng number. PostgreSQL trả về cột `bigint` dưới dạng chuỗi trừ khi ORM chuyển đổi nó; package từ chối một token như vậy ngay lập tức, kèm một message nêu cách sửa, thay vì để fencing âm thầm bị hỏng.

**Với Prisma.** Store Drizzle là mẫu để làm theo, với cùng bảng và sequence; [Giữ lock trong database của bạn](/reliability/locks#keep-locks-in-your-database) cũng trình bày nó với TypeORM. `acquire()` là một câu `INSERT ... ON CONFLICT (key) DO UPDATE ... WHERE owner IS NULL OR expires_at <= clock_timestamp() RETURNING fencing_token`, với token được lấy trong `SET`, sau khi lock dòng. `upsert()` của Prisma không có điều kiện cho phần update, nên hãy dùng `$queryRaw`. `renew()` và `release()` đặt owner và thời hạn trong `WHERE` của `updateMany()` và kiểm tra `count === 1`. Không dùng `update()` sau `findUnique()`: nó đọc trước.

**Hãy test nó** bằng suite từ `@nestjs/locks/testing`. `lockStoreContract()` trả về các case dùng được với mọi test runner. `concurrent: true` cho 16 bên gọi tranh nhau mỗi key, và tùy chọn `callers` của nó tăng con số đó; hãy chạy nó trên một server có connection pool, nơi các lời gọi thực sự chồng lấn. `advanceTime` dịch đồng hồ của store cho các case về thời hạn; không có nó thì chúng chờ theo thời gian thực, tổng cộng khoảng hai mươi lăm giây, trên các lock có `ttl` (mặc định 2.5 giây, được kiểm tra là vẫn đang bị giữ ở giữa chừng và đã trống sau khi quá hạn một phần sáu: hãy tăng nó cho một store có round trip chậm).
#### Tham khảo <a id="reference"></a>

##### Tùy chọn của module <a id="module-options"></a>

`LocksModule.forRoot()` nhận các tùy chọn sau; `forRootAsync()` nhận chúng từ `useFactory`, `useClass` hoặc `useExisting` (một class implement `LocksOptionsFactory`). Store không phải là một tùy chọn: hãy đăng ký nó với `LocksStorage`, như trong [Giữ lock trong database của bạn](/reliability/locks#keep-locks-in-your-database).

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `ttl` | `'30s'` | Thời gian một lock tồn tại nếu không được gia hạn, tức là bao lâu sau một lần crash thì một instance khác tiếp quản. Mặc định cho mọi lock, lease và election. Một khoảng thời gian: số mili giây, hoặc một chuỗi như `'15s'` hay `'2m'` |
| `storeTimeout` | `'10s'` | Thời gian chờ mỗi lời gọi store (`acquire()`, `renew()`, `release()`). Quá mức đó, lời gọi thất bại với `LockStoreTimeoutError`: `acquire()` reject, một tick không chạy, một lần gia hạn được thử lại ở nhịp tiếp theo, và một lock mà store cấp sau đó sẽ được trả lại cho store |
| `clock` | Đồng hồ hệ thống | Một `LockClock`. Các test truyền một `ManualLockClock` ([Testing](/reliability/locks#testing)) |
| `allowInMemoryStorage` | `false` | Với `NODE_ENV=production` và không có store được đăng ký, việc khởi động sẽ thất bại; `true` vẫn chạy trên store trong bộ nhớ (một instance) |
| `isGlobal` | `true` | Đăng ký module ở phạm vi global. Đặt ở cấp ngoài cùng của `forRoot()` và `forRootAsync()` |

##### Decorator và method <a id="decorators-and-methods"></a>

| API | Tùy chọn | Ghi chú |
| --- | --- | --- |
| `@OnOneInstance()` | `key`, `ttl` | Chạy job trên instance đang giữ lease `<key>:owner`; các instance khác bỏ qua tick. [Chạy mỗi job trên một instance](/reliability/locks#run-each-job-on-one-instance) |
| `@WithoutOverlapping()` | `key`, `ttl` | Bỏ qua một tick trong khi một lần chạy đang giữ lock `<key>`, trên bất kỳ instance nào. [Đừng để một lần chạy dài chồng lấn chính nó](/reliability/locks#dont-let-a-long-run-overlap-itself) |
| `@LeaderElection(key)` | `ttl` | Đặt trên một singleton provider implement `OnLeadershipAcquired`, `OnLeadershipLost` hoặc cả hai. [Giữ luồng dữ liệu của kho trên một instance](/reliability/locks#hold-the-warehouse-feed-on-one-instance) |
| `Locks.acquire(key, options)` | `ttl`, `wait`, `signal` | Resolve một `Lock`, hoặc `null` khi key vẫn bị chiếm. [Chạy export thủ công](/reliability/locks#run-the-export-by-hand) |
| `Locks.withLock(key, fn, options)` | `ttl`, `wait`, `signal` | Chạy `fn(lock)` dưới lock và giải phóng nó; reject với `LockNotAcquiredError` khi key vẫn bị chiếm |

- `key` mặc định là `ClassName.methodName`, và hai decorator job trên một method dùng chung nó. `ttl` mặc định là của module.
- `wait` mặc định là `0` (thử một lần); một khoảng chờ dài hơn sẽ retry kèm backoff. `signal` dừng việc chờ, kể cả với một lời gọi store đang chạy. Cả `wait` lẫn `ttl` đều không giới hạn một lời gọi store: `storeTimeout` của module mới làm việc đó.
- Một `Lock` có `key`, `owner`, `fencingToken`, `signal`, `held`, `release()` và `[Symbol.asyncDispose]`, nên `await using` sẽ giải phóng nó.
- `LocksContext` có `lock`, `fencingToken` và `signal` bên trong một job, một callback `withLock()`, hoặc `run(lock, fn)`; bên ngoài, chúng là `undefined`. [Fence các thao tác ghi](/reliability/locks#fence-the-writes)

##### Event <a id="events"></a>

`LocksEvents.events$` phát ra mỗi event, và publish nó trên channel `node:diagnostics_channel` tương ứng. Mọi payload đều có `type`, `key` và `fencingToken`.

| Event | Channel | Các field khác | Khi nào |
| --- | --- | --- | --- |
| `lock-lost` | `nestjs:locks:lock-lost` | `detectedBy`: `'renewal'` hoặc `'deadline'` | Một bên giữ đã mất lock mà nó đang dùng. Hãy đặt cảnh báo cho nó |
| `leadership-acquired` | `nestjs:locks:leadership-acquired` | Không có | Instance này đã trở thành leader của `key` |
| `leadership-lost` | `nestjs:locks:leadership-lost` | `reason`: `'lost'` hoặc `'released'` | Instance này thôi làm leader: lease bị mất, hoặc nó tự rút lui |

`LocksEvents.jobSkips$` phát ra một event `job-skipped` cho mỗi lời gọi tới một job `@OnOneInstance()` hoặc `@WithoutOverlapping()` đã resolve mà không chạy trước `onApplicationShutdown()`, và publish nó trên `nestjs:locks:job-skipped`. Nó tách biệt với `events$`: mọi instance trừ owner đều bỏ qua từng tick, nên các event này dùng để đếm, không phải để cảnh báo. Payload có `type`, `job` (`ClassName.methodName`), `key` (key của job, không phải lease `<key>:owner` của nó) và `reason`:

| `reason` | Khi nào |
| --- | --- |
| `ownership-unavailable` | Lease `<key>:owner` không được cấp: một instance khác đang giữ nó, hoặc store cấp nó quá muộn để dùng |
| `run-lock-unavailable` | Run lock `<key>` không được cấp: một lần chạy đang diễn ra, hoặc store cấp nó quá muộn để dùng |
| `shutdown` | Ứng dụng đang shutdown |

```typescript
@@filename(metrics/job-skip-metrics)
@Injectable()
export class JobSkipMetrics implements OnModuleInit {
  constructor(private readonly events: LocksEvents) {}

  onModuleInit() {
    // skippedTicks: a counter from your metrics library
    this.events.jobSkips$.subscribe(({ job, reason }) => skippedTicks.add(1, { job, reason }));
  }
}
```

Các event là những gì instance này đã thấy, theo cách nó thấy: chúng không ghi lại lần chạy cuối cùng của một job, và không đếm các tick mà scheduler chưa bao giờ kích hoạt. Một lỗi của store không phải là một lần bỏ qua: lời gọi reject, như trước đây.

> warning **Cảnh báo** Một subscriber của `events$`, `jobSkips$` hoặc một channel `nestjs:locks:*` không được throw: rxjs và Node sẽ throw lại lỗi của nó dưới dạng `uncaughtException`. Một subscriber cho việc bỏ qua chạy ở mọi tick, nên một bug trong đó sẽ lộ ra chỉ trong vòng một tick.

##### Lỗi <a id="errors"></a>

Không lỗi nào mang HTTP status: tranh chấp lock không phải lỗi của bên gọi, nên handler tự chọn response ([Chạy export thủ công](/reliability/locks#run-the-export-by-hand) trả lời `409`).

| Lỗi | Thuộc tính | Xảy ra khi |
| --- | --- | --- |
| `LocksError` | Không có | Class cơ sở của ba lỗi bên dưới |
| `LockNotAcquiredError` | `key`, `waitMs` | `withLock()` không lấy được lock trong khoảng `wait` |
| `LockLostError` | `key`, `fencingToken`, `detectedBy` | Reason mà `signal` của một lock bị mất dùng khi abort: store đã từ chối một lần gia hạn (`'renewal'`), hoặc `ttl` đã trôi qua mà không có lần gia hạn nào được xác nhận (`'deadline'`) |
| `LockStoreTimeoutError` | `key`, `method`, `timeoutMs` | Một lời gọi store (`method`: `'acquire'`, `'renew'` hoặc `'release'`) không trả lời trong vòng `storeTimeout` |
