### Durable workflow

`@nestjs/workflows` chạy các quy trình kéo dài nhiều ngày, như xử lý giao một đơn hàng, dưới dạng một method `async` duy nhất, với các bước được lưu trong database của bạn và tồn tại qua các lần restart.

Có những quy trình nghiệp vụ kéo dài nhiều ngày và trải qua nhiều hệ thống. Trong một cửa hàng online bán thức ăn và đồ dùng cho mèo, xử lý giao một đơn hàng nghĩa là:

1. Trừ tiền thẻ của khách hàng qua payment provider.
2. Giữ chỗ các sản phẩm trong kho.
3. Chờ tối đa 3 ngày để nhận webhook `shipment.delivered` từ đơn vị vận chuyển.
4. Nếu webhook không bao giờ tới, hoặc đơn vị vận chuyển trả kiện hàng về, hãy hoàn tiền và giải phóng hàng trong kho. Nếu không, chờ 7 ngày rồi nhờ khách hàng viết đánh giá.

Quy trình phải tồn tại qua các lần deploy và crash, chỉ trừ tiền đúng một lần, hoàn tác công việc của nó khi thất bại, và cho bộ phận hỗ trợ biết mỗi đơn hàng đang ở đâu. Với `@nestjs/workflows`, bạn viết nó thành một method `async` trên một class injectable. Mỗi side effect chạy trong một **step** được ghi journal. Sau một lần restart, method chạy lại từ đầu, và các step đã hoàn tất trả về kết quả đã ghi lại thay vì chạy hai lần. Các lần chờ (wait) và ngủ (sleep) sẽ đỗ instance lại trong database của chính bạn, nơi bất kỳ process nào trên bất kỳ host nào cũng có thể nhận nó khi tới hạn. Không có workflow server nào phải vận hành.

#### Workflow, queue hay saga?

Nest đã có hai công cụ cho những việc diễn ra sau, và mỗi công cụ vẫn là lựa chọn đúng cho việc của nó:

- **[BullMQ](/application/queues#bullmq-installation)** chạy từng đơn vị công việc nền một, như gửi email hay chuyển mã video, với giới hạn đồng thời, giới hạn tần suất, độ ưu tiên, và job trì hoãn hoặc lặp lại. Một quy trình chỉ có một hành động trì hoãn ("hủy đơn hàng nếu chưa được thanh toán trong vòng một giờ") chỉ là một delayed job cộng với một cột trạng thái.
- **[CQRS saga](/recipes/cqrs#sagas)** biến event thành command trong phạm vi một process. Chúng hợp với các phản ứng mà việc mất trạng thái đang xử lý khi restart là chấp nhận được. Khi không chấp nhận được, chính các event đó có thể khởi động và gửi signal cho workflow: xem [Với CQRS](/reliability/workflows#with-cqrs).
- **Workflow** hợp với một quy trình có nhiều bước, chờ hàng giờ hoặc hàng ngày cho timer hoặc event bên ngoài, phải tồn tại qua các lần restart và deploy, và phải hoàn tác các bước đã hoàn tất khi nó thất bại hoặc bị hủy. Chúng có giới hạn đồng thời, giới hạn tần suất, độ ưu tiên và lịch chạy riêng, và một step vẫn có thể giao việc nặng cho một BullMQ queue.

Một workflow instance là một dòng trong database của ứng dụng, nên việc khởi động nó có thể là một phần của transaction lưu đơn hàng: truyền transaction cho `start()` qua tùy chọn `transaction`. Đơn hàng và việc xử lý giao hàng của nó cùng commit hoặc không commit gì cả. Một job queue ghi qua kết nối riêng của nó (Redis, hoặc pool PostgreSQL riêng của BullMQ), nên lưu một đơn hàng và đưa job của nó vào hàng đợi là hai thao tác ghi, và một lần crash ở giữa sẽ làm mất một trong hai. Signal cũng vậy: một webhook có thể cập nhật đơn hàng và đánh thức workflow của nó trong một transaction.

Bài hướng dẫn bên dưới cho thấy queue và saga không làm được tới đâu: code tiếp tục chạy sau một lần chờ bền vững ([Ngủ một tuần, rồi nhờ đánh giá](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review)), một event chạy đua với một hạn chót ([Chờ webhook giao hàng](/reliability/workflows#wait-for-the-delivery-webhook)), và việc bù trừ (compensation) tồn tại qua một lần crash ([Cho bộ phận chăm sóc khách hàng hủy đơn](/reliability/workflows#let-customer-support-cancel-an-order)).

#### Cài đặt

Để bắt đầu, hãy cài dependency cần thiết:

[[CODE:1]]

Bài hướng dẫn giữ các workflow trong PostgreSQL, với store riêng của package, và dùng Drizzle, được đăng ký qua [`@nestjs/drizzle`](/data/drizzle). [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database) cũng trình bày store với TypeORM, và store MySQL của package. Các test trên trang này dùng [PGlite](https://pglite.dev), nên không cần server.

Đơn hàng nằm trong bảng riêng của ứng dụng ví dụ, `orders`. Bài hướng dẫn dùng các bản thay thế trong bộ nhớ cho SDK của payment provider (`PaymentProviderClient`), bảng kho (`InventoryService`) và nhà cung cấp mail (`MailService`). Giống như các hệ thống thật, chúng khử trùng lặp request theo idempotency key. Đơn hàng có cấu trúc như sau:

[[CODE:2]]

##### Đăng ký module

Import `WorkflowsModule` một lần, trong root module, cạnh [`DrizzleModule`](/data/drizzle), module đăng ký Drizzle database mà `@InjectDrizzle()` inject. Các class workflow là provider bình thường, nên chúng nằm trong `providers` cạnh các service mà chúng inject. Đây là module hoàn chỉnh: các workflow và controller mà nó liệt kê được viết ở các phần tiếp theo, và provider đầu tiên là store PostgreSQL của package, được giải thích trong [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database).

[[CODE:3]]

> info **Hint** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để thiếu `DATABASE_URL` sẽ dừng ứng dụng ngay lúc khởi động, và đọc nó từ `ConfigService` trong factory.

Mọi tùy chọn đều không bắt buộc: `WorkflowsModule.forRoot()` dùng được ngay. Để đọc chúng từ `ConfigService`, hãy dùng `forRootAsync()` với một factory, hoặc với một class `useClass` implement `WorkflowsOptionsFactory` và method `createWorkflowsOptions()` của nó.

`worker` chạy bên trong process của ứng dụng. Nó poll các instance tới hạn mỗi giây, và một lời gọi `start()` hoặc `signal()` ở local sẽ đánh thức nó ngay lập tức. Nó claim các instance tới hạn dưới một lease và gia hạn lease mỗi một phần ba `leaseDuration`. Nếu process chết, các instance của nó có thể được claim lại khi lease hết hạn. Đặt `worker: false` cho các process chỉ nên khởi động, gửi signal và xem workflow, chẳng hạn các pod API. Một step mặc định có 3 lần thử, với backoff bắt đầu từ 1 giây và nhân đôi tới 5 phút. Một tùy chọn `retry` ở đây sẽ thay đổi mặc định đó.

Trong `main.ts`, hãy bật shutdown hook. Khi nhận `SIGTERM`, worker ngừng claim, abort `signal` của các step đang chạy, chờ tối đa `shutdownTimeout`, và trả các instance mà nó đã dừng về lại store. Khi đó một process khác sẽ nhận chúng ngay thay vì chờ hết lease.

[[CODE:4]]

##### Giữ workflow trong database của bạn

Các workflow instance, journal của chúng, các signal mà chúng chờ và các signal đã được gửi đều nằm trong một **store**. Cho tới khi bạn đăng ký một store, module giữ chúng trong bộ nhớ: ổn cho lần chạy đầu tiên, nhưng một lần restart sẽ mất mọi đơn hàng đang chạy, và hai process không dùng chung chúng.

> warning **Warning** Với `NODE_ENV=production` và không có store nào được đăng ký, việc khởi động sẽ thất bại, trừ khi bạn đặt `allowInMemoryStorage: true`.

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

[[CODE:5]]

`status` thoát với mã 1 khi schema còn chậm phiên bản, nên nó có thể dùng làm bước kiểm tra trong CI. Để áp dụng migration bằng công cụ migration của riêng bạn, hãy lấy SQL của chúng từ `npx @nestjs/workflows sql`, hoặc từ `PostgresWorkflowStore.migrationSql()` trong code: các câu lệnh của mọi migration, mỗi đoạn một câu, kèm phần ghi chép phiên bản. Chạy chúng trong một transaction, như migrator của TypeORM và Drizzle làm. Với TypeORM, đó là một migration của riêng bạn, cạnh các migration mà nó sinh ra cho entity của bạn:

[[CODE:6]]

Với drizzle-kit, hãy tạo một custom migration, và điền SQL vào file nó tạo ra, với một dòng `--> statement-breakpoint` giữa các câu lệnh: khi đó migrator của Drizzle sẽ chạy từng câu một, điều mà PGlite yêu cầu. Trong code, `migrationSql()` với `statementBreakpoints: true` trả về kết quả tương tự.

[[CODE:7]]

Trên MySQL, `MySqlWorkflowStore.migrationStatements()` trả về các câu lệnh, mỗi chuỗi một câu, và một migration TypeORM chạy chúng mỗi lời gọi một câu:

[[CODE:8]]

Khi tắt `migrate`, một store có schema chậm phiên bản sẽ làm việc khởi động thất bại với một `WorkflowSchemaError` nêu ra ba cách này, và làm mọi lời gọi thất bại theo cùng cách cho tới khi schema được cập nhật, điều mà nó tự nhận ra mà không cần restart. Migration chỉ thêm bảng, cột và index, nên trong một lần rolling deploy, phiên bản trước của ứng dụng vẫn tiếp tục chạy trên schema đã migrate. Không có down migration.

**Transaction.** `start()` và `signal()` nhận transaction của bạn qua tùy chọn `transaction`: với Drizzle, đó là `tx` mà `db.transaction()` truyền cho callback của nó, như [Khởi động nó cùng đơn hàng](/reliability/workflows#start-it-with-the-order) trình bày. Store chạy các câu lệnh của nó trên transaction đó, nên chúng commit hoặc rollback cùng các thao tác ghi của bạn. Nó từ chối chính database, vì các câu lệnh trên đó sẽ tự commit riêng, bằng một `TypeError` cho biết cần truyền gì. Với các executor khác, hãy truyền một client node-postgres sau `BEGIN` (không phải pool), `EntityManager` của TypeORM từ `dataSource.transaction()`, interactive transaction client của Prisma, hoặc một Kysely transaction.

**Isolation.** Store dựa vào READ COMMITTED, isolation level mặc định của PostgreSQL: các câu lệnh của nó chạy đua với nhau, và dưới một level chặt hơn chúng sẽ thất bại với lỗi serialization. Lúc khởi động, nó kiểm tra `default_transaction_isolation` của database, và thất bại nếu nó chặt hơn. Một `signal()` trong transaction của bạn cũng cần một transaction READ COMMITTED, nếu không các lần đánh thức của nó có thể bỏ lỡ những wait được commit sau snapshot của transaction: nếu không thỏa điều kiện, nó bị từ chối bằng một `TypeError`.

**Với TypeORM.** `TypeOrmModule` thay thế `DrizzleModule` trong `AppModule`, và store chạy trên `DataSource` mà nó cung cấp, qua `fromTypeOrm()`:

[[CODE:9]]

Ở chỗ bài hướng dẫn truyền `tx` của Drizzle cho `start()` và `signal()`, hãy truyền `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó. Store từ chối `dataSource.manager`, vì các thao tác ghi trên đó sẽ tự commit riêng. Đây là `place()` của order service, từ [Khởi động nó cùng đơn hàng](/reliability/workflows#start-it-with-the-order), với TypeORM:

[[CODE:10]]

> info **Hint** Với Prisma, hãy truyền client cho `fromPrisma()`, và truyền làm `transaction` chính transaction client mà `prisma.$transaction()` đưa cho callback của nó. Các transaction riêng của store chờ kết nối tối đa 10 giây và chạy tối đa một phút, lâu hơn mặc định của Prisma: tham số thứ hai của `fromPrisma()` thay đổi điều đó, với `maxWait` và `timeout`. Nếu ứng dụng của bạn gửi signal theo từng đợt dồn dập, hãy cho các transaction riêng của ứng dụng một `maxWait` dài hơn nữa, vì các signal xếp hàng chờ nhau.

**Với MySQL.** Package cũng có một store cho MySQL 8.4 LTS và 9.x, `MySqlWorkflowStore` từ `@nestjs/workflows/mysql`, với các executor cùng tên. MariaDB hiện chưa được hỗ trợ: store từ chối nó lúc khởi động. Provider giống nhau, chỉ khác class store và executor của MySQL. Đây là `AppModule` với Drizzle trên một pool mysql2, trong đó `mode: 'default'` là thiết lập của Drizzle cho schema trên MySQL:

[[CODE:11]]

`fromMysql2(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` và `fromKysely(db)` làm điều tương tự cho một pool mysql2, TypeORM, Prisma (qua `@prisma/adapter-mariadb`) và Kysely. `start()` và `signal()` nhận cùng các transaction object như trên PostgreSQL, và với mysql2, là một connection sau `beginTransaction()`. Những điểm khác so với PostgreSQL:

- **Các bảng.** MySQL không có schema bên trong một database, nên store giữ các bảng của nó trong database của kết nối, database mà phần path của URL chỉ định, và tùy chọn `schema` là tiền tố trong tên của chúng: `nest_workflows_instances`, `nest_workflows_signals` và các bảng tương tự, cạnh `nest_workflows_migrations` và `nest_workflows_locks`, nơi chứa các phiên bản và các lock của nó.
- **Key có giới hạn.** Id, tên và key là các cột có index với độ dài giới hạn. Một instance id, một tên workflow hoặc signal, `key` và `id` của một signal, và một key concurrency hoặc rate-limit chứa được 255 ký tự, một schedule id là 230, và một tên step, sleep hoặc wait là 512. `start()` và `signal()` từ chối một giá trị dài hơn bằng `RangeError` trước khi ghi bất cứ thứ gì. Key vẫn được so sánh chính xác, như trên PostgreSQL.
- **Transaction của bạn.** `start()` và `signal()` với tùy chọn `transaction` hoạt động ở REPEATABLE READ, mặc định của MySQL, và ở READ COMMITTED: việc đánh thức đọc các wait bằng một locking read, cách đọc này cũng thấy những wait được commit sau snapshot của transaction của bạn. Tránh SERIALIZABLE, nơi MySQL biến các lần đọc thường thành locking read: một `start()` trong transaction như vậy sẽ giữ lại mọi signal cho tới khi transaction kết thúc.
- **Deadlock.** MySQL phá một deadlock bằng cách rollback một trong các transaction, với lỗi 1213 (`ER_LOCK_DEADLOCK`). Store tự chạy lại các transaction riêng của nó. Trong transaction của bạn, việc rollback cũng đã lấy đi các thao tác ghi của bạn, nên lỗi tới được code của bạn: hãy chạy lại transaction. Một transaction ghi một đơn hàng rồi gửi signal, trong khi một transaction khác gửi signal rồi ghi cùng đơn hàng đó, sẽ bị deadlock theo cách đó.
- **Migration.** MySQL tự commit từng câu lệnh DDL, nên các migration không thể chạy trong một transaction. Store và `npx @nestjs/workflows migrate` áp dụng chúng từng câu lệnh một, dưới một lock (`GET_LOCK()`), nên các process khởi động cùng lúc vẫn chỉ migrate một lần, và một lần chạy bị dừng giữa chừng sẽ tiếp tục từ chỗ nó đã dừng. Command line nhận một URL `mysql://` và khi đó cần `mysql2`, còn `npx @nestjs/workflows sql --dialect mysql` in ra SQL. Với công cụ của riêng bạn, hãy áp dụng các câu lệnh theo thứ tự, mỗi câu một lần, mỗi lời gọi một câu, như migration TypeORM ở trên làm: với drizzle-kit, vốn có migrator MySQL gửi mỗi breakpoint một câu lệnh, hãy thêm `--statement-breakpoints`.

Với một database khác, hãy tự viết store: [Hợp đồng của store](/reliability/workflows#the-store-contract) cho biết nó phải làm gì.

#### Viết workflow

Mọi side effect đều cần một idempotency key. Một step chạy **ít nhất một lần**: nếu process chết sau khi payment provider đã trừ tiền thẻ nhưng trước khi kết quả tới được journal, step sẽ chạy lại. Engine giao cho mỗi step một `idempotencyKey` giữ nguyên qua các lần thử và các process (`<instance id>:<step name>`). Hãy truyền nó cho hệ thống bạn gọi, và tác động sẽ chỉ xảy ra một lần:

[[CODE:12]]

`InventoryService.reserve()` theo cùng ý tưởng mà không cần API bên ngoài: nó dùng key làm primary key của lần giữ chỗ, nên một lần retry sẽ tìm thấy lần giữ chỗ nó đã tạo. Nó throw `NonRetryableStepError` khi một sản phẩm hết hàng. `MailService` truyền key cho nhà cung cấp mail làm message id.

Giờ đến workflow. Gắn `@Workflow()` cho một class, đặt tên cho nó, và implement `run()`:

[[CODE:13]]

`ctx.step()` chạy hàm một lần và ghi kết quả của nó vào journal. Mỗi khi instance chạy lại (sau một wait, một sleep hoặc một lần crash), `run()` bắt đầu từ đầu và `charge-payment` trả về lần trừ tiền đã ghi journal mà không gọi payment provider. Kết quả phải serialize được sang JSON, và chúng trả về ở dạng JSON, kể cả ở lần chạy đầu tiên: một `Date` là một chuỗi. Return type nói rõ điều đó (`Journaled<Charge>`), nên TypeScript sẽ báo lỗi code coi một giá trị đã ghi journal như một object sống.

- **`retry`**: `attempts` tính cả lần thử đầu tiên, và `backoff` đặt thời gian chờ trước mỗi lần retry: một `delay`, một hệ số tăng `factor`, một mức trần `maxDelay` và `jitter` tùy chọn. Một con số là cách viết tắt cho số lần thử, và `false` nghĩa là chỉ thử một lần. Một lần thử thất bại sẽ đỗ instance lại cho tới khi hết thời gian backoff, nên một lần retry cũng tồn tại qua một lần restart. Một `NonRetryableStepError`, chẳng hạn thẻ bị từ chối, làm step thất bại ngay lập tức.
- **`compensate`**: được đăng ký khi step hoàn tất. Nếu sau đó workflow thất bại hoặc bị hủy, các compensation của các step đã hoàn tất sẽ chạy theo thứ tự ngược lại. Mỗi compensation được ghi journal và retry như một step, với idempotency key riêng. Nếu `reserve-stock` thất bại vì một sản phẩm hết hàng, tiền sẽ được hoàn lại. [Ngủ một tuần, rồi nhờ đánh giá](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review) cho thấy cách chấm dứt điều này khi đơn hàng đã được giao.

Các step cũng có thể chạy song song. Để giữ chỗ từng sản phẩm riêng, hãy khởi động mỗi sản phẩm một step và chờ chúng cùng nhau. Mỗi step có tên riêng, chứa index của sản phẩm, và vì vậy có idempotency key và compensation riêng:

[[CODE:14]]

Nếu một sản phẩm hết hàng, step của nó thất bại, các step khác vẫn hoàn tất, và compensation của những step đã hoàn tất sẽ chạy: các lần giữ chỗ được giải phóng, rồi tiền được hoàn lại. Compensation chạy theo thứ tự ngược với các lời gọi `ctx.step()`, bất kể step nào xong trước. Phần còn lại của bài hướng dẫn giữ nguyên step `reserve-stock` duy nhất.

Class là một singleton được dùng chung bởi mọi đơn hàng đang chạy, và constructor injection hoạt động như thường. Hãy giữ trạng thái theo từng đơn hàng trong các biến cục bộ, không bao giờ đặt trên `this`.
