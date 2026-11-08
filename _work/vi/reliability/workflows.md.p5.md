#### Tham khảo

##### Tùy chọn của module

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

##### Store PostgreSQL

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

##### Store MySQL

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

##### Hợp đồng của store

`PostgresWorkflowStore` và `MySqlWorkflowStore` implement interface `WorkflowStore`. Với một database khác, hãy implement nó trong một provider của riêng bạn. JSDoc của từng method trên `WorkflowStore` cho biết method đó phải làm gì, và mỗi quy tắc ngăn chặn tình huống race nào.

**Đăng ký.** Store là một singleton provider bình thường gọi `registerSource(this)` trên `WorkflowStorage` (có thể inject) trong constructor của nó. Registry kiểm tra cấu trúc ngay lập tức, từ chối lần đăng ký thứ hai trừ khi truyền `replace: true`, và bị khóa khi `WorkflowsModule` khởi tạo, đồng thời log ra store đang dùng. Một provider request-scoped, một provider trong lazy-loaded module, hoặc một lifecycle hook sẽ đăng ký quá muộn, và throw. Không có gì được đăng ký, module dùng `InMemoryWorkflowStore`: một lần restart sẽ mất mọi instance đang chạy, và hai process không dùng chung chúng. Nó cũng không thể tham gia vào transaction của bạn, nên `start()` và `signal()` với `transaction` sẽ ghi ngay lập tức, và nó log một cảnh báo ở lần đầu tiên. Với `NODE_ENV=production`, việc khởi động sẽ thất bại thay vào đó, kèm một lỗi nêu tên các store của package và interface cần implement, trừ khi bạn đặt `allowInMemoryStorage: true` trong tùy chọn của module.

**Tính nguyên tử.** Worker, signal, cancel, retry, purge và lịch chạy chạy đua với nhau qua store. `claim()` không bao giờ được cho hai worker cùng giữ lease một instance, `write()` chỉ được ghi khi lease của worker còn hiệu lực, và `signal()` không được lọt qua một instance đang tạm dừng. Vì vậy mọi method thay đổi trạng thái đều là một câu lệnh có điều kiện, hoặc một transaction với lock đúng, không bao giờ là một lần đọc theo sau là một lần ghi. Có hai method không bắt buộc: `createInTransaction()` và `signalInTransaction()`, được `start()` và `signal()` gọi với transaction object của bạn, nguyên vẹn. Chúng phải ghi qua nó, và từ chối root handle, vì các thao tác ghi trên đó sẽ tự commit riêng. Trên PostgreSQL, `signalInTransaction()` còn từ chối một transaction không phải READ COMMITTED, vì việc đánh thức của nó có thể bỏ lỡ những wait được commit sau snapshot của nó.

**Hãy test nó** bằng suite từ `@nestjs/workflows/testing`. `workflowStoreContract()` trả về hợp đồng dưới dạng các test case, kể cả các tình huống race, dùng được với mọi test runner. Các test của bài hướng dẫn chạy nó trên `PostgresWorkflowStore` qua Drizzle, và trên `MySqlWorkflowStore` với MySQL, giống như bạn sẽ làm với store của mình, với một hàm trả về store trên các bảng đã được làm trống:

[[CODE:61]]

Với `concurrent: true`, suite cho các lần claim (kể cả dưới giới hạn), signal, lần tạm dừng, thao tác ghi cuối cùng của child, cancel và terminate, retry, purge và lần claim lịch chạy chạy đua với nhau: ví dụ 60 signal với 60 lần tạm dừng. Hãy chạy nó trên một database server có connection pool nữa, nơi một store thiếu lock đúng sẽ thất bại. Với `transaction`, một hàm mở một transaction của bạn, các case của hai method không bắt buộc cũng sẽ chạy. Các test riêng của package chạy suite trên một store Drizzle được viết tay, làm bằng chứng rằng một store được viết theo interface sẽ vượt qua nó.

Các package xây trên engine, chẳng hạn một job queue, lấy các phần không phụ thuộc vào lưu trữ của nó (đồng hồ, retry, payload codec, giới hạn, vòng lặp worker có lease và lịch chạy) từ `@nestjs/workflows/core`; ứng dụng không cần dùng nó.

##### Tùy chọn của các lời gọi

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

##### Event

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

##### Lỗi

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
