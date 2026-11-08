#### Tham khảo

##### Tùy chọn module

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

##### Store PostgreSQL và MySQL

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

##### Service và decorator

- `Webhooks`: `dispatch(tx, message)` nhận một message hoặc một mảng, với `type`, `data`, `tenant` và `id` tùy chọn, và throw một `TypeError` khi gặp loại không xác định, dữ liệu không serialize được thành JSON, hoặc id không hợp lệ. `notify()` chạy relay ngay lập tức.
- `WebhookEndpoints`: `create(input)`, `list(query)`, `get(id, scope)`, `update(id, changes, scope)`, `delete(id, scope)`, `getSecret(id, scope)` và `rotateSecret(id, options)`, trong đó `options` nhận `tenant`, `overlap` và `secret`. `create()` cũng nhận một `secret`, một `whsec_…` đã có được dùng thay cho secret sinh ra. Xem [Cho đối tác đăng ký](/http/webhooks#let-partners-subscribe).
- `WebhookDeliveries`: `list(query)`, `get(id, scope)`, `retry(idOrFilter, scope)`, `stats()` và `prune(olderThan)`. Xem [Retry, log gửi và gửi lại](/http/webhooks#retries-the-delivery-log-and-replay).
- `WebhookWorker`: bộ gửi, được khởi động khi ứng dụng boot trừ khi `worker.enabled` là `false`. `start()`; `stop()`, method này ngừng claim, chờ các lần thử đang dở và trả lại những lần gửi mà nó chưa bắt đầu; `running`; `notify()`, method này poll ngay thay vì chờ lượt tiếp theo; `runOnce()`, method này claim một lô rồi gửi nó, resolve ra số lần đã `claimed`, `delivered`, `retried`, `failed` và `released`, cùng số lần nó bị mất lease (`leaseLost`), và hoạt động cả khi worker đã dừng, như các bài test điều khiển nó; `stats()`, giống như `WebhookDeliveries.stats()`.
- `WEBHOOKS_OUTBOX_TOPIC`: topic outbox mà các message đã dispatch đi qua, `'nestjs.webhooks.message'`, tới handler `@OnOutboxMessage()` của package, tức bước phân phối. Một outbox có `route` chọn giữa nhiều transport sẽ gửi topic này tới `local`.
- `WebhookVerifier`: `verify(receiver, request)` kiểm tra một request không đến qua route HTTP, như một request được lưu trong queue, từ `headers` và `rawBody` của nó.
- `@VerifyWebhook(receiver)` xác minh và loại trùng, trên một method hoặc controller. `@IncomingWebhook()` inject webhook đã xác minh: `receiver`, `id`, `timestamp`, `payload`, `rawBody` và `processInTransaction()`. `@WebhookPayload()` chỉ inject payload, và nhận pipe giống như `@Body()`.

##### Transport

Worker gửi thông qua provider `WebhookTransport`. Transport mặc định, `HttpWebhookTransport`, được dựng từ các tùy chọn `delivery`: một `POST` cho mỗi lần thử qua `node:http` và `node:https`, host được resolve một lần và mọi địa chỉ mà nó resolve ra đều được kiểm tra, socket được cố định vào địa chỉ đã kiểm tra, redirect không bao giờ được đi theo, không dùng proxy từ biến môi trường. Constructor của nó nhận hai tùy chọn mà `delivery` không có:

- `ca`: các certificate authority cần tin cậy ngoài các CA của chính Node, cho các endpoint đứng sau một CA riêng. Chúng được thêm vào trust store của Node, nên các endpoint công khai vẫn xác minh được.
- `lookup`: resolve một host name ra mọi địa chỉ mà nó có, mỗi địa chỉ gồm `address` và `family` (4 hoặc 6), thay cho resolver của hệ thống. Mọi địa chỉ nó trả về vẫn được kiểm tra, và kết nối đi tới địa chỉ đầu tiên.

Để dùng chúng, hãy truyền một instance làm `transport`, với cùng `allowHttp`, `allowPrivateNetworks` và `allowedAddresses` như `delivery`: `delivery` vẫn quyết định những URL nào `WebhookEndpoints` chấp nhận, còn transport quyết định nó kết nối tới đâu.

[[CODE:67]]

Một transport của riêng bạn kế thừa `WebhookTransport` và implement `send(request, options)`, trong đó `options` có `signal` của lần thử và số thứ tự `attempt` của nó. Request mang `url`, các `headers` đã ký và `body`, cùng id của endpoint, lần gửi và message của nó. Hãy resolve với `statusCode`, `headers` và phần đầu `body` của response, bất kể status là gì, và chỉ throw khi không có response; hãy dừng khi `signal` bị abort, sau `delivery.timeout`. `NonRetryableWebhookError` và `WebhookDestinationBlockedError` làm lần gửi thất bại mà không retry; mọi lỗi khác đều được retry. Hãy truyền class làm `transport` ở cấp cao nhất của `forRoot()` hoặc `forRootAsync()`, nơi Nest khởi tạo nó (`imports` cho các module mà nó inject từ đó), hoặc truyền một instance. Nó thay thế cơ chế bảo vệ SSRF bằng bất cứ thứ gì nó tự làm: gửi qua một egress proxy có áp dụng cơ chế bảo vệ, như Smokescreen, là một lý do để tự viết transport; bọc `HttpWebhookTransport` thì vẫn giữ được cơ chế bảo vệ.

Cho test, `InMemoryWebhookTransport` ghi lại thay vì gửi đi, không có mạng hay kiểm tra địa chỉ (xem [Test](/http/webhooks#testing)):

- `sent`: mọi request, cũ nhất trước, dưới dạng `SentWebhook`. `clear()` làm rỗng nó.
- `respondWith(answer)`: cách endpoint trả lời từ giờ trở đi, mặc định là 200. Một status (`503`), một response (`statusCode`, `headers` như `retry-after`, `body`), hoặc một hàm nhận request và số thứ tự lần thử rồi trả về một trong hai, và throw để giả lập không có response.
- `filter(query)` và `single(query)`: các request khớp với `type`, `url` (một chuỗi hoặc `RegExp`), `endpointId` và `messageId`, hoặc một hàm nhận `SentWebhook`. `single()` throw, kèm danh sách những gì đã gửi, trừ khi có đúng một request khớp.

Một `SentWebhook` có `request`, số thứ tự `attempt` trong vòng của nó, `sentAt`, `url`, `type`, `messageId`, `endpointId`, `deliveryId`, `headers` và `body` của request, `data` (`data` của body, đã parse), và `isSignedWith(secret)`, method kiểm tra một chữ ký `v1` với secret của một endpoint.

##### Event

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

##### Lỗi

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
