#### Xử lý order.placed in-process

Email xác nhận là một handler cho `order.placed`. Mailer là bản thay thế cho SDK của nhà cung cấp email của bạn:

[[CODE:14]]

[[CODE:15]]

Các handler `@OnOutboxMessage()` được tìm thấy trên các provider, nên hãy đăng ký `MailerService` và `OrderEmailsHandler` làm provider của một `NotificationsModule`. Chúng phải là singleton: một handler trên provider request-scoped sẽ thất bại lúc khởi động. Handler nhận payload, ở đây là đơn hàng, và một context làm tham số thứ hai. `message` của context chứa `id`, `topic`, `key` và `headers` của message.

Mỗi handler có một inbox, được đặt tên bởi `consumer`. Trước khi gọi handler, local transport kiểm tra xem consumer `order-confirmation-email` đã xử lý message id này chưa. Sau khi handler thành công, nó ghi lại id. `consumer` là bắt buộc, và phải giữ ổn định: một tên mới sẽ khiến mọi message cũ trông như mới.

Inbox có một lỗ hổng: nếu process chết sau khi email đã được gửi nhưng trước khi id được ghi lại, email sẽ được gửi lại khi message được gửi lại. Điều đó chấp nhận được với một email. Nhưng không chấp nhận được với việc giữ chỗ hàng, vốn nằm trong cùng database với inbox. Handler giữ chỗ hàng bịt lỗ hổng này bằng cách ghi lại id bên trong transaction của chính nó:

[[CODE:16]]

`ctx.processInTransaction(tx, work)` insert inbox record qua transaction của handler, sau đó chỉ gọi `work` nếu consumer này chưa xử lý message. Nếu đã xử lý rồi, nó bỏ qua `work` và trả về một kết quả có cờ `duplicate` là `true`. Record và việc cập nhật kho cùng commit, nên việc giữ chỗ chỉ xảy ra đúng một lần: một lần gửi lại sẽ tìm thấy record và bỏ qua handler, còn nếu `work` throw, cả hai cùng rollback và lần retry bắt đầu lại từ đầu. Hãy await nó bên trong callback của transaction, để record được ghi trước `COMMIT`; việc kiểm tra trùng lặp xảy ra bên trong lời gọi, nên thiếu `await` cũng không làm nó bị bỏ qua. Đăng ký handler trong một `InventoryModule`.

| Handler | Hành vi | Đảm bảo |
| --- | --- | --- |
| Mặc định | Bỏ qua handler nếu inbox của nó đã có id, ghi lại id sau khi handler thành công | Một lần, trừ khi process chết giữa lúc handler xong và lúc ghi record, hoặc một instance khác gửi cùng message vào cùng lúc |
| Gọi `ctx.processInTransaction(tx, work)` | Ghi lại id trong transaction riêng của handler, cùng các thao tác ghi của nó | Đúng một lần với các thao tác ghi vào cùng database |
| `inbox: false` | Mọi lần gửi đều chạy handler | Ít nhất một lần |

Cả hai handler chạy đồng thời cho mỗi message `order.placed`. Nếu một trong hai thất bại, lần publish thất bại và toàn bộ message được retry. Ở lần retry, mỗi handler đã thành công sẽ được inbox của nó bỏ qua.

Relay cho các handler `publishTimeout` (ở đây là 10 giây). Nếu chúng mất lâu hơn, lần thử được tính là thất bại và `signal` của context bị abort: hãy truyền `ctx.signal` cho các lời gọi mà handler thực hiện, chẳng hạn tùy chọn `signal` của `fetch()`, để chúng cũng dừng lại. Một handler bỏ qua nó sẽ tiếp tục chạy, và nếu lần retry tới cùng process trong lúc đó, inbox sẽ chờ nó thay vì chạy handler lần thứ hai.

#### Publish tới microservice analytics

Phía API đã được nối sẵn. Trong `AppModule`, `ClientProxyTransport(ANALYTICS_SERVICE)` publish qua `ClientProxy` mà `ClientsModule` đã đăng ký dưới tên đó, và `route` gửi mọi topic `analytics.*` tới nó. Transport gọi `client.emit(topic, envelope)`, đúng lời gọi bạn sẽ dùng nếu không có outbox. Envelope có `id`, `topic`, `key`, `headers`, `createdAt` và `payload` của message.

Hủy một đơn hàng tạo ra event analytics thứ hai cho cùng đơn hàng đó. Thêm method `cancelOrder()` vào `OrdersService`, và import `NotFoundException` cùng `ConflictException` từ `@nestjs/common`:

[[CODE:17]]

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

[[CODE:18]]

`OrderStatsService` ghi lại một event và trả về doanh thu tính tới thời điểm đó. Nó mở một transaction và gọi `inbox.processInTransaction(tx, 'analytics', messageId, work)`: inbox record và dòng `order_events` cùng commit, nên một event được gửi lại không thay đổi gì, kể cả khi service crash giữa chừng:

[[CODE:19]]

[[CODE:20]]

Các event của một đơn hàng tới theo thứ tự relay đã publish chúng, nhưng các handler là bất đồng bộ: hai handler có thể chạy cùng lúc, và một lần hủy có thể commit trước lần đặt mà nó đi sau. Controller chạy các event của một key lần lượt từng cái, theo thứ tự đến, và các đơn hàng khác nhau thì chạy song song.

[[CODE:21]]

`inbox.processInTransaction()` chính là thứ mà một handler `@OnOutboxMessage()` có được với `ctx.processInTransaction()`: đúng một lần với các thao tác ghi vào database riêng của consumer. Khi side effect của consumer nằm ngoài database của nó, chẳng hạn một email, hãy dùng `inbox.process(consumer, id, work)` thay vào đó: nó bỏ qua `work` nếu consumer đã thấy id này, và ghi lại id sau khi `work` thành công.

> warning **Warning** Qua TCP, "đã publish" chỉ có nghĩa là các byte đã rời khỏi API đơn hàng. Nếu service analytics crash sau khi nhận một event nhưng trước khi xử lý nó, event sẽ bị mất. Với những event không được phép mất, hãy dùng một transport có broker xác nhận đã nhận: Kafka, RabbitMQ với publisher confirms, hoặc NATS JetStream. `ClientProxyTransport` nhận một tùy chọn `toPacket` để map một message sang record của transport đó, với key và header riêng.

#### Retry và dead-letter queue

Khi một lần publish thất bại, vì một handler đã throw, kết nối TCP bị từ chối, hoặc việc publish mất lâu hơn `publishTimeout`, relay sẽ lên lịch lại message:

- Mỗi lần retry chờ lâu hơn: 1 giây, 2 giây, 4 giây và cứ thế, giới hạn ở `maxDelay` (ở đây là 1 phút). Mỗi lần chờ được ngẫu nhiên hóa trong khoảng từ một nửa tới toàn bộ giá trị, để các lần retry không tới cùng một nhịp.
- Mỗi lần thất bại được log dưới dạng cảnh báo, kèm số thứ tự lần thử và thời gian chờ trước lần tiếp theo.
- Sau `retry.attempts` lần thất bại (ở đây là 10), message được chuyển sang bảng dead-letter với lý do `exhausted` và lỗi của mọi lần thử.
- Một `NonRetryableMessageError` bỏ qua các lần retry. Message bị chuyển sang dead-letter ngay lập tức với lý do `rejected`. Mọi lỗi mà hàm tùy chọn `retry.retryIf(error, attempt, message)` trả về `false` cũng vậy. Khi nhiều handler thất bại, message chỉ bị reject nếu tất cả chúng đều throw `NonRetryableMessageError`. Nếu không, nó được retry, các handler đã thành công được bỏ qua, và nó bị reject khi chỉ còn lại các lỗi vĩnh viễn.
- Một topic không có handler `@OnOutboxMessage()` nào sẽ được retry, chứ không bị chuyển sang dead-letter. Trong một lần rolling deploy, relay của một instance cũ có thể thấy một topic mà chỉ phiên bản mới xử lý.
- Một message đã bị chuyển sang dead-letter không còn giữ chân key của nó nữa: các message sau đó với key đó được publish mà không có nó. Hãy định cỡ `retry` sao cho những sự cố bạn lường trước không dùng hết nó.

Handler kho throw `NonRetryableMessageError` khi không đủ hàng. Retry không tạo ra hàng, nên message đi thẳng tới bảng dead-letter, nơi một người có thể quyết định phải làm gì.

`OutboxDeadLetters` liệt kê, xem chi tiết, đưa lại vào hàng đợi và xóa các dead letter. Package không mount route HTTP nào, nên hãy đưa nó ra phía sau guard của riêng bạn. Cùng controller đó phục vụ số liệu thống kê của outbox, từ service `OutboxMetrics` được xây dựng ở phần tiếp theo:

[[CODE:22]]

[[CODE:23]]

> info **Hint** `AdminGuard` chỉ là placeholder. Dead letter chứa toàn bộ payload, kể cả dữ liệu khách hàng, nên hãy bảo vệ các route này bằng [phân quyền](/security/authorization) thật của ứng dụng.

`requeue()` chuyển một dead letter trở lại outbox với số lần retry được làm mới và **cùng id**. Các consumer đã xử lý nó sẽ bỏ qua nó qua inbox của chúng. Vì vậy sau khi nhập thêm hàng, đưa lại đơn hàng hết hàng vào hàng đợi sẽ giữ chỗ hàng mà không gửi email xác nhận lần thứ hai. `requeue()` và `purge()` cũng nhận một mảng id, hoặc một bộ lọc theo `topic`, `key` hoặc `failedBefore`. Chúng từ chối một bộ lọc trống; hãy truyền `all: true` để nhắm tới mọi dead letter.

#### Chạy nhiều instance

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

[[CODE:24]]

Khi nhận `SIGTERM`, relay ngừng claim và chờ các lần publish đang chạy hoàn tất, mỗi lần tối đa `publishTimeout`. Sau đó nó giải phóng lease trên các message đã claim nhưng chưa bắt đầu, để một instance khác có thể nhận chúng ngay thay vì chờ hết lease. Việc này xảy ra trong `onModuleDestroy()`, trước khi `ClientsModule` đóng TCP client trong `onApplicationShutdown()`.

Để theo dõi outbox, hãy subscribe `OutboxEvents` và đọc `relay.stats()`:

[[CODE:25]]

`relay.stats()` báo cáo `lagMs`, khoảng thời gian message chờ lâu nhất đã chờ. Nó tăng trong khi một hệ thống phía sau bị down, nên đây là con số để đặt cảnh báo, cùng với `deadLetters`. Một message được lên lịch với `delay` không được tính cho tới khi tới hạn. Event `published` mang theo message, nên `Date.now() - message.createdAt` là độ trễ publish từ đầu đến cuối. `OutboxEvents` phát ra bốn event mà câu `switch` đếm. `lease-lost` nghĩa là một relay khác đã tiếp quản một message trong khi relay này đang publish nó, nên message đó có thể tới consumer hai lần. Đăng ký `OutboxAdminController`, `AdminGuard` và `OutboxMetrics` trong một `OutboxAdminModule`.

Mỗi event cũng được publish trên một channel [`node:diagnostics_channel`](https://nodejs.org/api/diagnostics_channel.html), `nestjs:outbox:published` và các channel tương tự. Các library tracing và metric có thể subscribe vào chúng mà không cần code Nest nào, và chúng thấy mọi ứng dụng Nest trong process.

Hãy bắt lỗi bên trong các subscriber của bạn. Cả RxJS và `diagnostics_channel` đều throw lại lỗi của subscriber dưới dạng uncaught exception, làm dừng process. Lúc đó relay đã lưu kết quả của message, nên bản thân message vẫn an toàn.

Ứng dụng ví dụ chạy phần này trên một PostgreSQL server: hai relay chia nhau 20 đơn hàng, ba instance (một trong số đó chỉ phục vụ API) đặt và hủy 12 đơn hàng với mọi message được publish một lần và các event của mỗi đơn hàng đúng thứ tự, một transaction chờ lock của instance khác trên cùng một key, một instance crash khi đang giữ lease, và một lần graceful shutdown.

#### Chạy thử

Tạo hai database, `store` cho API đơn hàng và `analytics` cho service analytics, và áp dụng migration riêng của từng service: migration của API đơn hàng tạo các bảng và sản phẩm của nó từ [Yêu cầu trước](/reliability/outbox#prerequisites), còn migration của service analytics tạo `order_events`.

Khởi động service analytics (TCP port 4001) trên `analytics`, và API đơn hàng (port 3000) trên `store`, với `ADMIN_TOKEN=s3cret` trong môi trường của API. Mỗi service log ra store mà nó đã đăng ký, và store tạo schema ở lần khởi động đầu tiên:

[[CODE:26]]

Đặt một đơn hàng:

[[CODE:27]]

Log của API hiển thị hai handler in-process:

[[CODE:28]]

Và log của service analytics hiển thị TCP consumer:

[[CODE:29]]

Một đơn hàng cho sản phẩm không tồn tại sẽ không qua được validation bên trong transaction. Response là `400`, và không có gì tới được outbox:

[[CODE:30]]

Giờ hãy đặt hai bao cát vệ sinh vón cục (`clumping-litter-10l`), loại chỉ còn một bao trong kho. API chấp nhận đơn hàng, vì hàng được giữ chỗ một cách bất đồng bộ. Email xác nhận được gửi đi, và việc giữ chỗ bị chuyển sang dead-letter ngay ở lần thử đầu tiên:

[[CODE:31]]

[[CODE:32]]

Xem dead-letter queue. Không có header `x-admin-token`, guard trả lời `403`:

[[CODE:33]]

[[CODE:34]]

Payload được lưu dưới dạng `jsonb`, vốn giữ thứ tự key riêng của nó, nên nó trả về với các key theo thứ tự khác so với lúc được thêm vào.

Nhập thêm hàng, rồi đưa message trở lại hàng đợi theo id của nó:

[[CODE:35]]

Việc giữ chỗ thành công. Inbox của handler email đã có message id này, nên không có email thứ hai nào được gửi:

[[CODE:36]]

Cuối cùng, dừng service analytics bằng `Ctrl+C`, rồi đặt một đơn hàng và hủy nó:

[[CODE:37]]

Cả hai message analytics đều đang chờ. `lagMs` tăng trong suốt thời gian sự cố, và `retried` đếm các lần thử thất bại. `ready` bằng 0: lần đặt đang chờ lần retry tiếp theo, còn lần hủy đã tới hạn nhưng chờ phía sau nó, vì chúng dùng chung key. API log ra mỗi lần thử thất bại:

[[CODE:38]]

Khởi động lại service analytics. Ở lần retry tiếp theo, relay publish lần đặt, rồi đến lần hủy. Doanh thu tiếp tục từ chỗ cũ, vì nó nằm trong database của service, chứ không nằm trong bộ nhớ:

[[CODE:39]]

#### Testing

Trong một test e2e, hãy chạy PostgreSQL in-process bằng [PGlite](https://pglite.dev) với các migration thật của bạn, tắt vòng lặp poll, và tự điều khiển relay. `relay.runOnce()` claim và xử lý một batch, và resolve khi batch xong:

[[CODE:40]]

- Outbox, store của nó, các migration và việc dispatch in-process đều là thật. Chỉ có mailer và client analytics là bản giả.
- Override database mà `DrizzleModule` đăng ký, có token do `getDrizzleToken()` trả về, bằng database PGlite. Factory của store inject cùng token đó, nên đơn hàng và outbox dùng chung database, giống như chúng dùng chung pool trong production, và store tạo schema của nó ở đó khi module khởi tạo. Module vẫn mở pool `pg` của nó, pool này không bao giờ kết nối.
- Test rollback để `outbox.add()` ghi các message, rồi làm transaction thất bại. Đơn hàng và các message của nó cùng biến mất, và `runOnce()` không tìm thấy gì để claim.
- Với các hành vi phụ thuộc thời gian, như backoff và lease hết hạn, hãy tua `Date.now()` về phía trước bằng `vi.spyOn(Date, 'now')`. Relay lấy thời gian từ đó, cho chính nó và cho store, còn các timer thật vẫn tiếp tục chạy cho socket và HTTP.
- PGlite chỉ có một kết nối, nên nó chạy từng transaction một. Hãy test các tình huống race giữa các instance trên một PostgreSQL server, cùng major version với production, như ví dụ đã làm cho [nhiều instance](/reliability/outbox#run-several-instances).
- Để loại outbox ra khỏi một test, hãy thay store: `overrideProvider(PostgresOutboxStore).useValue(new InMemoryOutboxStore())`. Một instance thuần không tự đăng ký, nên outbox fallback về store trong bộ nhớ của nó, và schema của store không được tạo. Tuy nhiên nó không thể tham gia vào các Drizzle transaction của bạn: một message đã rollback vẫn được publish, và store log một cảnh báo ở lần đầu tiên nó nhận được transaction của bạn.

#### Đảm bảo về việc gửi

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
