#### Checklist cho production

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

#### Hợp đồng của store

`PostgresOutboxStore` và `MySqlOutboxStore` implement hai interface lưu trữ của package: `OutboxStore` cho message và dead letter, và `OutboxInboxStore` cho inbox của các consumer. Với một database khác, hãy implement chúng trong một provider của riêng bạn. JSDoc của từng method trên các interface đó cho biết nó phải làm gì, và mỗi quy tắc ngăn chặn tình huống race nào.

**Đăng ký.** Store là một singleton provider bình thường gọi `registerSource()` trên `OutboxStorage` (có thể inject) trong constructor của nó, cho các hợp đồng mà nó implement, theo tên: `messages` và `inbox`. Một service chỉ tiêu thụ có thể chỉ đăng ký một inbox store. Registry kiểm tra cấu trúc ngay lập tức (mọi method đều là hàm), từ chối lần đăng ký thứ hai trừ khi truyền `replace: true`, và bị khóa khi `OutboxModule` khởi tạo, đồng thời log ra store đang dùng. Một provider request-scoped, một provider trong lazy-loaded module, hoặc một lifecycle hook sẽ đăng ký quá muộn, và throw.

Không có gì được đăng ký, outbox chạy trên store trong bộ nhớ, và nói rõ điều đó lúc khởi động:

[[CODE:41]]

Đó không chỉ là một lối tắt mất dữ liệu khi restart. Một store trong bộ nhớ không thể tham gia vào transaction của bạn, nên nó áp dụng `add()` ngay lập tức, và cảnh báo ở lần đầu tiên nhận được một transaction handle. Trong lần chạy này, transaction của đơn hàng đã thêm message rồi thất bại, nhưng email xác nhận vẫn được gửi đi:

[[CODE:42]]

Với `NODE_ENV=production`, cùng ứng dụng đó không khởi động:

[[CODE:43]]

`allowInMemoryStorage: true` trong tùy chọn của module là lối ra có chủ đích, cho một instance duy nhất có thể chấp nhận mất trạng thái.

**Tính nguyên tử.** Producer, relay và các lần gửi chạy đua với nhau qua store. `add()` phải đánh số các message của một key theo thứ tự transaction của chúng commit, `claim()` không bao giờ được cho hai relay cùng giữ lease một message hay chạy trước một message cũ hơn của cùng key, các thao tác ghi sau đó của một relay chỉ được áp dụng khi lease của nó còn hiệu lực, và hai lần gửi của cùng một message phải gặp nhau ở `recordInbox()`. Vì vậy mọi method thay đổi trạng thái đều là một câu lệnh có điều kiện, hoặc một transaction với lock đúng, không bao giờ là một lần đọc theo sau là một lần ghi. `add()` và `recordInbox()` nhận nguyên vẹn transaction object của bạn: chúng phải ghi qua nó, và từ chối mọi thứ không phải transaction, chẳng hạn chính database, bằng `OutboxTransactionRequiredError`.

**Hãy test nó** bằng các suite từ `@nestjs/outbox/testing`. `outboxStoreContract()` và `outboxInboxStoreContract()` trả về các hợp đồng dưới dạng test case dùng được với mọi test runner: mỗi case là một `name` và một hàm `run()` throw khi thất bại. Các test của bài hướng dẫn chạy chúng trên `PostgresOutboxStore` qua Drizzle, giống như bạn sẽ làm với store của mình, với một hàm trả về store trên các bảng đã được làm trống, một cách để mở một transaction của bạn, và `notATransaction`, một handle mà store phải từ chối:

[[CODE:44]]

`concurrent: true` thêm vào các tình huống race mà một store ngây thơ sẽ thất bại: các producer của một key có transaction chồng lấn, các relay claim song song, producer và relay chạy đua, các thao tác ghi của một relay đã cũ chạy đua với một lần tiếp quản, và hai lần gửi của cùng một message. Trên PGlite chúng chạy từng transaction một, nên hãy chạy chúng trên một server có pool nữa, nơi các transaction thực sự chồng lấn, với database engine và major version mà bạn chạy trong production. Bài hướng dẫn chạy cả hai suite qua từng client của nó: Drizzle trên PGlite và trên PostgreSQL, TypeORM và Prisma trên PostgreSQL, và Drizzle trên MySQL, với `MySqlOutboxStore`. Các test riêng của package cũng chạy chúng trên các store được viết tay bằng Drizzle, TypeORM và Prisma, làm bằng chứng rằng một store được viết theo các interface sẽ vượt qua chúng.

Store của các package khác có thể nằm ở nơi khác: idempotency store hợp với Redis. Store của outbox thì không thể, vì các message của nó phải commit cùng các dòng dữ liệu của bạn, trong database của bạn.

#### Dùng BullMQ trên Postgres thay thế

BullMQ 6 có backend PostgreSQL, nên cũng hợp lý khi hỏi liệu bảng job của nó có thể làm outbox hay không. Kết quả nghiên cứu của package về BullMQ 6.3.x (từ việc đọc code đã publish, không phải chạy thực tế) là: hiện tại thì chưa.

- `Queue.add()` luôn chạy trên connection pool riêng của BullMQ, ở chế độ autocommit. Interface backend cố ý không để lộ type kết nối hay transaction nào, nên một `add()` không thể tham gia vào transaction insert đơn hàng của bạn.
- Bản thân việc đưa vào hàng đợi là một hàm SQL, `bullmq.add_job(...)`. Gọi nó trên transaction của bạn thì sẽ nguyên tử, nhưng hàm này là nội bộ, signature của nó thay đổi theo các schema migration của BullMQ, và mọi transaction gọi nó sẽ lấy global NOTIFY lock của Postgres khi commit.
- `@nestjs/bullmq` 12.0.0 không thể chọn backend Postgres cho một queue riêng lẻ. Cách duy nhất là `setDefaultBackendFactory()` áp dụng cho toàn process của BullMQ.

Thứ cần có là một tùy chọn ở upstream để chạy `add()` trên một client do bên gọi cung cấp (để job commit cùng đơn hàng), cộng với một tùy chọn backend trong `@nestjs/bullmq`. Có cả hai, bảng job sẽ là outbox, và worker của BullMQ sẽ đảm nhận việc claim, retry và tập job thất bại mà không cần relay ở giữa. Cho tới lúc đó, hãy dùng outbox này và publish sang BullMQ từ một `OutboxTransport` gọi `queue.add(topic, payload)` với `id` của outbox message làm `jobId`, để một message được publish lại sẽ bị bỏ qua khi job vẫn còn tồn tại.

#### Ví dụ

Một ví dụ chạy được có trong [sample 37-outbox](https://github.com/nestjs/nest/tree/master/sample/37-outbox): API đơn hàng trên PostgreSQL với Drizzle, các handler in-process, microservice analytics có database riêng, admin API cho dead-letter, và các test.

#### Tham khảo

##### Tùy chọn của module

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

##### Store

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

##### Message và handler

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

##### Service

| Service | Method |
| --- | --- |
| `Outbox` | `add(tx, messages)`, `notify()` |
| `OutboxRelay` | `stats()`: `pending`, `ready`, `leased`, `deadLetters`, `oldestDueAt`, `lagMs`, `inFlight`. `runOnce()`: `claimed`, `published`, `retried`, `deadLettered`, `released`, `leaseLost`. Ngoài ra còn có `notify()`, `start()` và `stop()` |
| `OutboxDeadLetters` | `list(query)` (theo `topic`, `key`, `limit`, `offset`; mới nhất trước), `get(id)`, `requeue(target)`, `purge(target)`. Một target là một id, một mảng id, hoặc một bộ lọc theo `ids`, `topic`, `key`, `failedBefore`, hoặc `all: true`. [Retry và dead-letter queue](/reliability/outbox#retries-and-the-dead-letter-queue) |
| `OutboxInbox` | `process(consumer, id, work)`, `processInTransaction(tx, consumer, id, work)`, `prune(olderThan)`. Cả hai method `process` đều resolve `duplicate`, và `result` khi `work` đã chạy |

##### Event

`OutboxEvents.events$` phát ra mỗi event, và publish nó trên channel `node:diagnostics_channel` tương ứng. Mọi payload đều có `type` và `message`. [Chạy nhiều instance](/reliability/outbox#run-several-instances) đếm chúng. Hãy bắt lỗi bên trong các subscriber của bạn: cả RxJS và `diagnostics_channel` đều throw lại lỗi của subscriber dưới dạng uncaught exception.

| Event | Channel | Các field khác | Khi nào |
| --- | --- | --- | --- |
| `published` | `nestjs:outbox:published` | `transport`, `durationMs` | Một transport đã chấp nhận message |
| `retry-scheduled` | `nestjs:outbox:retry-scheduled` | `transport`, `error`, `attempt`, `delayMs` | Một lần publish thất bại và sẽ được retry |
| `dead-lettered` | `nestjs:outbox:dead-lettered` | `transport`, `error`, `attempt`, `reason` | Message đã được chuyển sang dead letter. Hãy đặt cảnh báo cho nó |
| `lease-lost` | `nestjs:outbox:lease-lost` | Không có | Một relay khác đã tiếp quản message giữa chừng lúc publish, nên nó có thể được publish hai lần |

`reason` của một dead letter là `exhausted` (đã hết số lần retry) hoặc `rejected` (một `NonRetryableMessageError`, hoặc `retryIf` trả về `false`).

##### Lỗi

Không lỗi nào mang HTTP status. `OutboxError` là class cơ sở của bốn lỗi mà package throw.

| Lỗi | Xảy ra khi |
| --- | --- |
| `OutboxTransactionRequiredError` | `add()` hoặc `processInTransaction()` không nhận được transaction handle, hoặc một store từ chối một handle không phải transaction |
| `OutboxPublishTimeoutError` | Một lần publish chạy quá `relay.publishTimeout` (`timeoutMs`). Được tính là một lần thử thất bại |
| `OutboxNoHandlerError` | Không có handler `@OnOutboxMessage()` nào cho topic trong process này (`topic`). Sẽ được retry |
| `OutboxSchemaError` | Schema của store chậm hơn các migration của package trong khi `migrate` bị tắt, hoặc việc áp dụng chúng thất bại (`cause`): việc khởi động và mọi lời gọi đều thất bại cho tới khi được sửa. Kèm theo `schema`, `version` của nó và `requiredVersion`. Từ `@nestjs/outbox/postgres` và `@nestjs/outbox/mysql` |
| `NonRetryableMessageError` | Bạn throw nó từ một handler hoặc transport để chuyển message sang dead-letter mà không retry |
