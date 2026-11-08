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

#### Cài đặt

Để bắt đầu, cài dependency cần thiết:

[[CODE:1]]

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

#### Giữ webhook trong database của bạn

Không cần tạo gì cho webhook, hay cho outbox mà chúng đi qua: không có bảng, entity hay Prisma model nào. Hãy đăng ký hai store của chúng, và mỗi store tự tạo schema riêng, `nest_webhooks` và `nest_outbox`, rồi migrate nó: lúc khởi động trong development và trong test, còn trên production thì bằng `npx @nestjs/webhooks migrate` và `npx @nestjs/outbox migrate`, hoặc bằng `migrationSql()` của chúng trong migration của chính bạn.

Package giữ các endpoint, cùng secret của chúng, các message nó đã dispatch, các lần gửi của chúng và log của mọi lần thử trong một **store**, mà nó đọc thông qua hai hợp đồng, `WebhookEndpointStore` và `WebhookDeliveryStore`. Cho đến khi bạn đăng ký một store, module giữ chúng trong bộ nhớ: ổn cho lần chạy đầu tiên, nhưng một lần khởi động lại sẽ mất mọi lần gửi đang chờ, và hai instance không chia sẻ chúng với nhau.

> warning **Warning** Với `NODE_ENV=production` mà không đăng ký store nào, việc khởi động sẽ thất bại, trừ khi bạn đặt `allowInMemoryStorage: true`.

Trên PostgreSQL, hãy đăng ký store của package, `PostgresWebhookStore` từ `@nestjs/webhooks/postgres`. Outbox cũng cần một store, cho các message mang webhook đã dispatch ra khỏi transaction của bạn và cho inbox loại trùng các webhook nhận vào: `PostgresOutboxStore` từ `@nestjs/outbox/postgres`, như trong [bài hướng dẫn outbox](/reliability/outbox#keep-messages-in-your-database). Cả hai chạy SQL của chúng thông qua database client mà ứng dụng của bạn đã có, và giữ các bảng trong schema riêng. Chúng là các provider thông thường, được đăng ký một lần, trong root module, cạnh `WebhooksModule` và `OutboxModule`: cả bốn đều áp dụng cho toàn ứng dụng. `AppModule` tạo mỗi store bằng một factory inject database Drizzle và registry storage của package tương ứng, nơi store tự đăng ký:

[[CODE:2]]

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

[[CODE:3]]

`status` thoát với mã 1 khi schema còn lạc hậu, khiến nó trở thành một bước kiểm tra cho CI. Để áp dụng migration bằng công cụ migration của riêng bạn, hãy lấy SQL của chúng từ `npx @nestjs/webhooks sql` và `npx @nestjs/outbox sql`, hoặc từ `PostgresWebhookStore.migrationSql()` và `PostgresOutboxStore.migrationSql()` trong code: các câu lệnh của mọi migration, kèm phần ghi nhận version. Hãy chạy mỗi cái trong một transaction, như migrator của TypeORM và Drizzle làm. Với TypeORM, đó là một migration của riêng bạn, cạnh các migration nó sinh ra cho entity của bạn:

[[CODE:4]]

Với drizzle-kit, hãy tạo một custom migration cho mỗi store, và điền vào file mà mỗi cái tạo ra bằng SQL của nó, với một dòng `--> statement-breakpoint` giữa các câu lệnh: khi đó migrator của Drizzle chạy chúng từng câu một, điều mà PGlite yêu cầu. Trong code, `migrationSql()` với `statementBreakpoints: true` trả về đúng như vậy.

[[CODE:5]]

Trên MySQL, `migrationStatements()` của các store trả về các câu lệnh, mỗi câu một chuỗi, và một migration TypeORM chạy chúng mỗi câu một lời gọi:

[[CODE:6]]

Khi tắt `migrate`, một store có schema lạc hậu sẽ làm việc khởi động thất bại với một `WebhookSchemaError` (với store của outbox là `OutboxSchemaError`) nêu ra ba cách xử lý này, và làm mọi lời gọi thất bại theo cùng cách cho đến khi schema được cập nhật, điều mà nó nhận ra mà không cần khởi động lại. Trong một đợt rolling deploy, phiên bản trước của ứng dụng vẫn tiếp tục chạy trên schema mà phiên bản mới đã migrate. Không có down migration.

**Transaction.** Không method nào của webhook store nhận transaction của bạn. `webhooks.dispatch(tx, ...)` thêm message vào outbox trong transaction của bạn, thông qua store của outbox, và `webhook.processInTransaction(tx, ...)` ghi nhận một webhook nhận vào trong inbox của outbox theo cùng cách; bước phân phối sau khi commit, worker và mọi thứ khác chạy trên kết nối riêng của các store. Với Drizzle, `tx` là thứ mà `db.transaction()` truyền cho callback của nó, như các phần sau trình bày. Store của outbox từ chối chính database, vì các câu lệnh của nó sẽ tự commit riêng, với một `OutboxTransactionRequiredError` cho biết cần truyền gì. Với các executor khác, hãy truyền một client node-postgres sau `BEGIN` (không phải pool), `EntityManager` của TypeORM từ `dataSource.transaction()`, interactive transaction client của Prisma, hoặc một transaction của Kysely.

**Isolation.** Các store dựa vào READ COMMITTED, isolation level mặc định của PostgreSQL: các câu lệnh của chúng chạy đua với nhau, và dưới một level chặt hơn chúng sẽ lỗi serialization. Lúc khởi động, mỗi store kiểm tra `default_transaction_isolation` của database, và thất bại nếu nó chặt hơn. Transaction của riêng bạn có thể chạy ở bất kỳ level nào. Tuy nhiên, dưới REPEATABLE READ hoặc SERIALIZABLE, một bản sao của webhook nhận vào mà `processInTransaction()` xử lý trong transaction của bạn, chạy đua với lần commit của bản đầu tiên, sẽ lỗi serialization của PostgreSQL thay vì bị bỏ qua như một bản trùng: bên gửi nhận lỗi, và lần retry của họ sẽ thấy webhook đã được ghi nhận.

**Với TypeORM.** `TypeOrmModule` thay chỗ cho `DrizzleModule` trong `AppModule`, và cả hai store chạy trên `DataSource` mà nó cung cấp, thông qua `fromTypeOrm()`:

[[CODE:7]]

Ở chỗ bài hướng dẫn truyền `tx` của Drizzle vào `dispatch()` và `processInTransaction()`, hãy truyền `EntityManager` mà `dataSource.transaction()` truyền cho callback của nó, và inject `Webhooks<EntityManager>`. Store của outbox từ chối `dataSource.manager`, vì các thao tác ghi của nó sẽ tự commit riêng. Đây là `cancelOrder()` của order service, từ phần [Gửi order.shipped và order.cancelled sau khi commit](/http/webhooks#send-ordershipped-and-ordercancelled-after-the-commit), viết bằng TypeORM:

[[CODE:8]]

Entity của bạn và migration của chúng vẫn giữ nguyên: `migration:generate` chỉ so sánh entity của bạn với database, và không đụng tới schema của các store.

**Với MySQL.** Trên MySQL 8.4 hoặc 9.x, hãy import các store và executor từ `@nestjs/outbox/mysql` và `@nestjs/webhooks/mysql` thay vào đó. Các provider vẫn như vậy, với `MySqlOutboxStore` và `MySqlWebhookStore`, trên một database Drizzle của `drizzle-orm/mysql2`:

[[CODE:9]]

Với các client khác, executor là `fromMysql2(pool)` cho một pool `mysql2/promise`, `fromTypeOrm(dataSource)` cho một `DataSource` có type `mysql`, `fromPrisma(prisma)` cho Prisma thông qua `@prisma/adapter-mariadb`, hoặc `fromKysely(db)` cho `MysqlDialect` của Kysely. Những gì khác với PostgreSQL:

- **Bảng, không phải schema.** MySQL không có schema bên trong database, nên các store giữ bảng của chúng trong database của kết nối, database trong path của URL, cạnh các bảng của bạn, và `schema` trở thành prefix của chúng: `nest_webhooks_endpoints`, `nest_webhooks_deliveries`, v.v., và `nest_outbox_messages` cho outbox. Nó nhận chữ thường, chữ số và dấu gạch dưới, tối đa 40 ký tự.
- **Transaction của bạn.** `dispatch()` và `processInTransaction()` hoạt động ở REPEATABLE READ, mặc định của MySQL, cũng như ở READ COMMITTED: không cần cấu hình gì, và các store không kiểm tra mặc định của database. Khi MySQL phá một deadlock trong transaction của bạn (lỗi 1213), nó rollback toàn bộ transaction, và lỗi của client đến tay code của bạn: hãy chạy lại transaction. Các store tự chạy lại transaction của chính chúng. Với `processInTransaction()`, điều đó có thể xảy ra khi nhiều bản sao của một webhook đến cùng lúc và transaction của bản đầu tiên bị rollback: bên gửi nhận lỗi, và lần retry của họ sẽ đi qua.
- **Key có giới hạn.** Id và tenant là các cột có index: tối đa 255 ký tự, 256 với tenant, các id của chính package và giới hạn của nó cho `tenant` đều nằm trong khoảng đó. Id của một webhook nhận vào nằm trong key của inbox, cũng tối đa 255 ký tự, và bộ xác minh từ chối id dài hơn trên mọi database, với lỗi 401, trước khi handler chạy.
- **Migration không phải một transaction.** MySQL tự commit mỗi câu lệnh DDL, nên `migrate` áp dụng các câu lệnh từng câu một, dưới một lock (`GET_LOCK()`), và một lần chạy thất bại sẽ tiếp tục từ câu lệnh nó đã dừng. Công cụ của riêng bạn cũng phải gửi mỗi câu lệnh một lời gọi, như migration TypeORM trong phần **Migration** ở trên. Command line nhận URL `mysql://`, và `sql --dialect mysql` in ra SQL của MySQL: thêm `--statement-breakpoints` cho custom migration của drizzle-kit, vì migrator MySQL của nó gửi mỗi breakpoint một câu lệnh.
- **Server.** Các store kiểm tra nó lúc khởi động, và từ chối MariaDB, một kết nối không có database, và một `sql_mode` không strict (mặc định của MySQL là strict). Cũng hãy giữ `NO_BACKSLASH_ESCAPES` ngoài thiết lập này.

Với một database khác, hãy tự viết store của riêng bạn: [Hợp đồng của store](/http/webhooks#the-store-contract) cho biết nó phải làm gì.

#### Đăng ký các module

Đăng ký `OutboxModule` và `WebhooksModule` trong root module, cạnh `DrizzleModule`, module đăng ký database Drizzle, với cả hai store trong `providers` của nó. Các feature module được xây dựng trong các phần tiếp theo:

[[CODE:10]]

`WebhooksModule` cần outbox: `dispatch()` là một lời gọi `Outbox.add()`, và bước phân phối biến một message đã commit thành các lần gửi là một outbox handler. Không có `OutboxModule`, việc khởi động sẽ thất bại và báo rõ điều đó. `relay` của outbox chuyển các message đã commit cho bước phân phối, polling mỗi giây, và `OUTBOX_RELAY=off` tắt nó đi. Các tùy chọn còn lại, được resolve khi ứng dụng khởi động:

- `eventTypes`: các loại message mà ứng dụng này gửi. `dispatch()` từ chối mọi loại khác, và một endpoint cố đăng ký nhận một loại khác cũng vậy, kèm danh sách các loại đã biết trong thông báo.
- `retry`: bộ từ vựng dùng chung với outbox, HTTP client và resilience. Mười lần thử, và một backoff bắt đầu từ 5 giây, tăng gấp bốn và giới hạn ở một ngày, có jitter: đúng như đặc tả Standard Webhooks khuyến nghị, "một lịch retry kéo dài nhiều ngày".
- `disableEndpointAfter`: một endpoint thất bại ở mọi lần thử trong năm ngày mà không có lần thành công nào sẽ bị tắt, và chủ sở hữu của nó được thông báo (xem [Retry, log gửi và gửi lại](/http/webhooks#retries-the-delivery-log-and-replay)).
- `delivery`: một lần thử có 15 giây cho DNS, kết nối, TLS, request và response. `allowHttp` và `allowPrivateNetworks` mặc định tắt: chỉ các endpoint `https://` công khai được chấp nhận. `WEBHOOKS_ALLOW_LOCAL=1` bật chúng trong development, nơi receiver của đối tác chạy trên chính máy này. Các địa chỉ metadata của cloud vẫn bị chặn kể cả khi đó.
- `worker`: bộ gửi chạy nền, mỗi process một cái. `WEBHOOKS_WORKER=off` tắt nó ở những instance chỉ phục vụ API.
- `encryption`: secret của endpoint được niêm phong khi lưu trữ, theo cùng kiểu trong cả loạt package: key đầu tiên mã hóa, mọi key đều giải mã. Tùy chọn, lấy từ `WEBHOOKS_ENCRYPTION_KEYS`.

> info **Hint** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để một biến bị thiếu làm ứng dụng dừng ngay lúc khởi động thay vì ở request đầu tiên, và đọc giá trị từ `ConfigService` (`inject: [ConfigService]` trong các factory).

Khoảng thời gian tính bằng mili giây hoặc chuỗi như `'15s'` và `'5d'`. Cả hai module đều là global: `Webhooks`, `WebhookEndpoints`, `WebhookDeliveries`, `WebhooksEvents` và `WebhooksStorage` có thể được inject ở bất cứ đâu. `main.ts` bind validation pipe cho các DTO của API đối tác (xem phần tiếp theo), và bật shutdown hook, để một đợt deploy cho relay và worker hoàn tất công việc đang dở:

[[CODE:11]]

Lúc khởi động, cả hai module log store mà chúng dùng, và ở lần khởi động đầu tiên, các store log những schema mà chúng đã tạo:

[[CODE:12]]
