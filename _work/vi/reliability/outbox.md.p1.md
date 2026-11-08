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

#### Yêu cầu trước

- PostgreSQL, với [Drizzle ORM](https://orm.drizzle.team) trên driver `pg`, được đăng ký qua [`@nestjs/drizzle`](/data/drizzle). Các message của outbox được commit cùng các dòng dữ liệu của bạn, nên chúng nằm trong database chứa đơn hàng của bạn, trên một database server tồn tại lâu hơn mọi instance của ứng dụng. Dùng TypeORM, Prisma hoặc MySQL? Hãy theo bài hướng dẫn để biết ứng dụng làm gì: [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database) trình bày store với từng loại.
- `@nestjs/microservices`, cho kết nối TCP tới service analytics trong [Publish tới microservice analytics](/reliability/outbox#publish-to-the-analytics-microservice).

Cài đặt package:

[[CODE:1]]

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

#### Giữ message trong database của bạn

Không cần tạo gì cho outbox: không bảng, entity hay Prisma model nào. Hãy đăng ký store của nó, và store sẽ tạo schema riêng, `nest_outbox`, và migrate nó: lúc khởi động trong môi trường development và test, còn trong production thì bằng `npx @nestjs/outbox migrate`, hoặc bằng `migrationSql()` trong các migration của bạn.

Outbox giữ message, dead letter và inbox của các consumer trong cùng database với các bảng của bạn, vì chúng phải commit cùng các dòng dữ liệu của bạn. Cho tới khi bạn đăng ký một store cho chúng, outbox giữ chúng trong bộ nhớ: ổn cho lần chạy đầu tiên, nhưng một lần restart sẽ mất mọi message chưa được publish, hai instance không dùng chung chúng, và không có gì tham gia vào transaction của bạn.

> warning **Warning** Với `NODE_ENV=production` và không có store nào được đăng ký, việc khởi động sẽ thất bại, trừ khi bạn đặt `allowInMemoryStorage: true`.

Trên PostgreSQL, hãy đăng ký store của package, `PostgresOutboxStore` từ `@nestjs/outbox/postgres`. Nó chạy SQL qua database client mà ứng dụng của bạn đã có, nên có thể tham gia vào transaction của bạn, và nó giữ các bảng của mình trong một schema riêng. Nó là một provider bình thường, đăng ký một lần, trong root module, cạnh `OutboxModule`: cả hai đều có phạm vi toàn ứng dụng, và mọi `outbox.add()` ở bất kỳ module nào đều đi qua nó. Root module tạo nó bằng một factory inject Drizzle database và registry `OutboxStorage`, nơi store tự đăng ký:

[[CODE:2]]

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

[[CODE:3]]

`status` thoát với mã 1 khi schema còn chậm phiên bản, nên nó có thể dùng làm bước kiểm tra trong CI. Để áp dụng migration bằng công cụ migration của riêng bạn, hãy lấy SQL của chúng từ `npx @nestjs/outbox sql`, hoặc từ `PostgresOutboxStore.migrationSql()` trong code: các câu lệnh của mọi migration, mỗi đoạn một câu, kèm phần ghi chép phiên bản. Chạy chúng trong một transaction, như migrator của TypeORM và Drizzle làm. Với TypeORM, đó là một migration của riêng bạn, cạnh các migration mà nó sinh ra cho entity của bạn:

[[CODE:4]]

Với drizzle-kit, hãy tạo một custom migration, và điền SQL vào file nó tạo ra, với một dòng `--> statement-breakpoint` giữa các câu lệnh: khi đó migrator của Drizzle sẽ chạy từng câu một, điều mà PGlite yêu cầu. Trong code, `migrationSql()` với `statementBreakpoints: true` trả về kết quả tương tự.

[[CODE:5]]

Trên MySQL, `MySqlOutboxStore.migrationStatements()` trả về các câu lệnh, mỗi chuỗi một câu, và một migration TypeORM chạy chúng mỗi lời gọi một câu:

[[CODE:6]]

Khi tắt `migrate`, một store có schema chậm phiên bản sẽ làm việc khởi động thất bại với một `OutboxSchemaError` nêu ra ba cách này, và làm mọi lời gọi thất bại theo cùng cách cho tới khi schema được cập nhật, điều mà nó tự nhận ra mà không cần restart. Migration chỉ thêm bảng, cột và index, nên trong một lần rolling deploy, phiên bản trước của ứng dụng vẫn tiếp tục chạy trên schema đã migrate. Không có down migration.

**Transaction.** `outbox.add()` nhận transaction của bạn, như [Lưu đơn hàng và message của nó trong một transaction](/reliability/outbox#save-the-order-and-its-messages-in-one-transaction) trình bày, và `processInTransaction()` của handler cũng vậy: với Drizzle, đó là `tx` mà `db.transaction()` truyền cho callback của nó. Store chạy các câu lệnh của nó trên transaction đó, nên chúng commit hoặc rollback cùng các thao tác ghi của bạn. Nó từ chối chính database, vì các câu lệnh trên đó sẽ tự commit riêng, bằng một `OutboxTransactionRequiredError` cho biết cần truyền gì. Với các executor khác, hãy truyền một client node-postgres sau `BEGIN` (không phải pool), `EntityManager` của TypeORM từ `dataSource.transaction()`, interactive transaction client của Prisma, hoặc một Kysely transaction.

**Isolation.** Các transaction riêng của store (claim, chuyển sang dead-letter, đưa lại vào hàng đợi) dựa vào READ COMMITTED, isolation level mặc định của PostgreSQL: lúc khởi động, store kiểm tra `default_transaction_isolation` của database, và thất bại nếu nó chặt hơn. Transaction của bạn có thể chạy ở bất kỳ level nào. `add()` trước tiên lấy một lock theo từng key trên transaction của bạn, nên các transaction thêm message có cùng key sẽ lần lượt chờ nhau, và các message của một key được đánh số theo thứ tự transaction của chúng commit. Dưới REPEATABLE READ hoặc SERIALIZABLE, hai lần gửi của cùng một message chạy đua tới `processInTransaction()` có thể làm lần thứ hai thất bại với lỗi serialization thay vì bỏ qua nó như một bản trùng lặp: handler của nó thất bại, và lần retry của relay sẽ tìm thấy record.

**Với TypeORM.** `TypeOrmModule` thay thế `DrizzleModule` trong root module, và store chạy trên `DataSource` mà nó cung cấp, qua `fromTypeOrm()`:

[[CODE:7]]

Ở chỗ bài hướng dẫn truyền `tx` của Drizzle cho `outbox.add()`, hãy truyền `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó, và gán type cho outbox theo nó. Store từ chối `dataSource.manager`, vì các thao tác ghi trên đó sẽ tự commit riêng. Đây là order service với TypeORM:

[[CODE:8]]

**Với Prisma.** Truyền `PrismaService` của bạn cho `fromPrisma()` trong factory, và truyền cho `outbox.add()` transaction client mà `prisma.$transaction()` đưa cho callback của nó. Chỉ dạng interactive đó mới có client để truyền: dạng mảng, `prisma.$transaction([query1, query2])`, không thể chứa một `outbox.add()`. Store từ chối chính client, vì các câu lệnh trên đó sẽ tự commit riêng. Các transaction riêng của store chờ kết nối tối đa 10 giây và chạy tối đa một phút, lâu hơn mặc định của Prisma: tham số thứ hai của `fromPrisma()` thay đổi điều đó, với `maxWait` và `timeout`.

**Với MySQL.** Cho MySQL 8.4 LTS và 9.x, `@nestjs/outbox/mysql` có `MySqlOutboxStore`. Import store và executor của nó từ đó: provider giống nhau, các tùy chọn và tên executor cũng vậy. Đây là API đơn hàng trên MySQL, với Drizzle trên driver `mysql2`:

[[CODE:9]]

`fromMysql2(pool)`, `fromTypeOrm(dataSource)` cho một data source có type `mysql`, `fromPrisma(prisma)` với driver adapter `@prisma/adapter-mariadb` (adapter phục vụ MySQL), và `fromKysely(db)` phục vụ các client khác. Những điểm khác so với PostgreSQL:

- **Bảng, không phải schema.** Một database MySQL không có schema, nên store giữ các bảng của nó trong database của kết nối, database mà phần path của URL chỉ định, và tùy chọn `schema` là tiền tố của chúng: `nest_outbox_messages`, `nest_outbox_dead_letters` và `nest_outbox_inbox`, cạnh `nest_outbox_migrations` và `nest_outbox_locks`. Nó nhận chữ thường, chữ số và dấu gạch dưới, tối đa 40 ký tự. Một kết nối không có database sẽ làm việc khởi động thất bại.
- **Key có giới hạn.** Id, topic, key và tên consumer là các cột có index tối đa 255 ký tự, được so sánh theo từng byte: `order-1` và `Order-1` là hai key khác nhau. Một giá trị dài hơn bị từ chối bằng `RangeError`, trước mọi câu lệnh: bởi `add()`, và bởi inbox trước khi nó chạy một handler.
- **Isolation level của bạn.** Transaction của bạn có thể chạy ở REPEATABLE READ, mặc định của MySQL, hoặc ở READ COMMITTED. Một lần gửi chạy đua với lần khác tới `processInTransaction()` sẽ chờ lần kia, rồi bỏ qua handler như một bản trùng lặp, ở cả hai level.
- **Deadlock tới được transaction của bạn.** `add()` lock một dòng theo từng key trong transaction của bạn, một trong 16.384 dòng mà các key dùng chung, được store tạo ra khi nó khởi động: các producer của hai key dùng chung một dòng sẽ lần lượt chờ nhau, như các producer của cùng một key, điều này hiếm khi làm chậm một producer không liên quan. Khi MySQL phá một deadlock trong transaction của bạn (lỗi 1213), nó rollback toàn bộ transaction, và store không thể chạy lại công việc của bạn: lỗi tới code của bạn dưới dạng lỗi của client, nên hãy chạy lại transaction. Với các dòng đó, vẫn còn hai thứ có thể gây ra deadlock: ba lần gửi của cùng một message chạy đua tới `processInTransaction()` trong khi lần đầu tiên rollback, và các transaction của bạn lấy cùng các lock theo thứ tự khác nhau. Các transaction riêng của store tự retry khi gặp deadlock.
- **Migration không mang tính transaction.** MySQL tự commit từng câu lệnh DDL, nên `migrate` và `npx @nestjs/outbox migrate --url mysql://...` áp dụng từng câu lệnh một dưới một lock, và một lần chạy bị dừng giữa chừng sẽ tiếp tục từ chỗ nó đã dừng. Công cụ của riêng bạn cũng phải gửi mỗi lời gọi một câu lệnh, như migration TypeORM trong phần **Migration** ở trên, và một custom migration của drizzle-kit cần `npx @nestjs/outbox sql --dialect mysql --statement-breakpoints`, vì migrator MySQL của nó gửi mỗi breakpoint một câu lệnh.

#### Đăng ký outbox

Đăng ký `OutboxModule` trong root module, cạnh `DrizzleModule`, module đăng ký Drizzle database, và với store từ [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database). Các feature module mà nó import được xây dựng ở các bước tiếp theo:

[[CODE:10]]

`ClientProxyTransport(ANALYTICS_SERVICE)` là một class mà Nest khởi tạo bên trong `OutboxModule`, nên `transports` nằm cạnh `useFactory`, nơi đặt các class. Factory chạy khi ứng dụng khởi động và trả về phần còn lại của các tùy chọn:

- `transports` và `route`: nơi mỗi message được publish. Transport `local` có sẵn và chạy các handler `@OnOutboxMessage()` trong process này ([Xử lý order.placed in-process](/reliability/outbox#handle-orderplaced-in-process)). `ClientProxyTransport(ANALYTICS_SERVICE)` publish qua TCP client mà `ClientsModule` đăng ký dưới tên đó, đó là lý do module đó nằm trong `imports` ([Publish tới microservice analytics](/reliability/outbox#publish-to-the-analytics-microservice)). `route` chọn đúng một transport cho mỗi message.
- `relay`: bộ publish chạy nền. Nó poll mỗi `pollInterval`, giữ lease những gì nó claim trong `lease`, và bỏ cuộc với một lần publish đơn lẻ sau `publishTimeout`. Đặt `OUTBOX_RELAY=off` sẽ tắt nó trong các instance chỉ phục vụ API ([Chạy nhiều instance](/reliability/outbox#run-several-instances)).
- `retry`: 10 lần thử, với exponential backoff bắt đầu từ 1 giây và giới hạn tối đa 1 phút ([Retry và dead-letter queue](/reliability/outbox#retries-and-the-dead-letter-queue)).

> info **Hint** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để thiếu `DATABASE_URL` sẽ dừng ứng dụng ngay lúc khởi động, và đọc các giá trị từ `ConfigService` trong các factory.

Khoảng thời gian là số mili giây hoặc chuỗi như `'30s'` và `'1m'`. `OutboxModule` là global: `Outbox`, `OutboxStorage`, `OutboxRelay`, `OutboxEvents`, `OutboxDeadLetters` và `OutboxInbox` có thể được inject ở bất cứ đâu trong ứng dụng.

#### Lưu đơn hàng và message của nó trong một transaction

Đây là model đơn hàng:

[[CODE:11]]

`OrdersService.placeOrder()` mở một Drizzle transaction, tính giá các sản phẩm, insert đơn hàng và thêm các message, tất cả qua cùng một `tx`:

[[CODE:12]]

`outbox.add()` nhận transaction handle trước tiên, sau đó là message hoặc một mảng message. Với Drizzle, handle là `tx` mà `db.transaction()` truyền cho callback của nó, type của nó được service truyền cho outbox: `Outbox<Transaction>`. Store insert chúng qua `tx` đó, nên các message commit cùng đơn hàng, hoặc rollback cùng nó. Store là bất đồng bộ, nên hãy await `add()` như mọi query khác. Mọi API trong package có tham gia vào transaction của bạn đều nhận handle làm tham số đầu tiên.

Một vài chi tiết:

- **Mỗi đích một message.** Mỗi message đi tới đúng một transport. Cùng một event đi tới các handler in-process và tới service analytics, nên service thêm hai message, `order.placed` và `analytics.order.placed`, trong cùng một transaction.
- **Payload là bản chụp.** `add()` serialize payload ngay lập tức, nên các thay đổi sau đó trên object `order` sẽ không được publish.
- **Id.** Mỗi message có một `id` UUIDv7 có thứ tự theo thời gian. Consumer khử trùng lặp dựa trên nó.
- **`notify()`.** Không có gì được publish bên trong transaction. Sau khi commit, `notify()` đánh thức relay. Không có nó, message sẽ được gửi đi ở lần poll tiếp theo, chậm tối đa `pollInterval`.

Nếu có gì đó throw bên trong transaction, đơn hàng và các message của nó cùng rollback, và relay không bao giờ thấy chúng. Điều đó bao gồm một sản phẩm không tồn tại, một câu insert thất bại, và bất cứ thứ gì thất bại sau `add()`. Phần [Testing](/reliability/outbox#testing) chứng minh điều này bằng cách làm transaction thất bại sau khi các message đã được ghi.

Hãy truyền transaction, không bao giờ truyền database: `outbox.add(this.db, message)` sẽ ghi message một cách độc lập, ở chế độ autocommit, chính xác là việc dual write mà bạn đang loại bỏ. Store từ chối nó bằng `OutboxTransactionRequiredError`, và chính `add()` cũng vậy khi nó không nhận được handle nào.

Đưa service ra qua HTTP:

[[CODE:13]]
