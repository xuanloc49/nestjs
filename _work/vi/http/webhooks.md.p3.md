#### Đảm bảo khi gửi

Webhook gửi đi được giao **ít nhất một lần**; bên nhận loại trùng dựa trên `webhook-id`.

| Tình huống | Kết quả |
| --- | --- |
| Transaction của đơn hàng bị rollback | Message chưa bao giờ tồn tại và không có gì được gửi |
| Transaction của đơn hàng được commit | Một lần gửi cho mỗi endpoint đã đăng ký của tenant, cuối cùng sẽ được giao hoặc thất bại kèm log các lần thử |
| Outbox gửi lại message (một relay bị crash sau bước phân phối) | Bước phân phối là idempotent: một lần gửi cho mỗi message và endpoint |
| Endpoint được tạo sau message, hoặc đang bị tắt | Nó không nhận được message, và việc gửi lại cũng không mang nó trở lại |
| Một worker chết sau khi đã lấy (claim) | Được một worker khác gửi khi lease hết hạn (`worker.lease`, 1 phút) |
| Một worker chết sau khi gửi, trước khi ghi nhận | **Bị gửi hai lần**, với cùng `webhook-id`, khi lease hết hạn |
| Hai worker, cùng một lần gửi | Một lần claim là độc quyền trong suốt lease, và mọi thao tác ghi sau đó đều được rào chắn bởi lease |
| Đối tác trả lời 2xx | Đã giao |
| Đối tác trả lời bất cứ gì khác, hoặc không trả lời | Retry có backoff, tôn trọng `Retry-After`; 429, 502, 503 và 504 điều tiết tốc độ của endpoint |
| Đối tác trả lời 410 Gone | Thất bại (`rejected`), và endpoint bị tắt (`gone`) |
| Mọi lần thử thất bại trong suốt `disableEndpointAfter` | Endpoint bị tắt (`failing`), một lần |
| Đối tác yêu cầu gửi lại | Một vòng mới với cùng `webhook-id`, nên inbox của họ bỏ qua nó |

Các lần gửi **không có thứ tự**. Một worker gửi các lần gửi của một endpoint từng cái một, trễ hạn nhất trước, nhưng một lần thử thất bại phải chờ hết backoff trong khi các message sau vẫn được gửi đi, nhiều worker gửi tới cùng một endpoint cùng lúc, và một lần gửi lại sẽ gửi một message cũ ngay bây giờ. Hai lần cập nhật của cùng một đơn hàng có thể đến tay đối tác theo bất kỳ thứ tự nào. Bên nhận xử lý điều này giống như xử lý bản trùng: `timestamp` trong body là thời điểm message được dispatch (`webhook-timestamp` là thời điểm lần thử này được ký), nên một handler có thể bỏ qua một event cũ hơn state mà nó đang giữ, hoặc xem webhook như một tín hiệu rồi đọc state hiện tại từ API.

Webhook nhận vào chạy handler **một lần cho mỗi webhook id và receiver trong trường hợp thông thường** với inbox mặc định (chạy lại sau khi crash giữa handler và lúc ghi inbox, hoặc khi hai bản sao chạy đua trên hai instance), còn công việc trong `processInTransaction()` của chúng chạy **đúng một lần**.

#### Checklist cho production

- Giữ endpoint và các lần gửi trong database của ứng dụng, trên một database server: đăng ký `PostgresWebhookStore`, hoặc `MySqlWebhookStore`, cùng store của outbox bên cạnh nó ([Giữ webhook trong database của bạn](/http/webhooks#keep-webhooks-in-your-database)). Cơ chế bảo vệ trên production từ chối khởi động trong bộ nhớ; `allowInMemoryStorage` dành cho một process mà bạn chấp nhận được việc mất các lần gửi đang chờ.
- Áp dụng migration của cả hai store trước khi phiên bản mới khởi động, bằng `npx @nestjs/webhooks migrate` và `npx @nestjs/outbox migrate` hoặc công cụ migration của bạn, và kiểm tra chúng trong CI bằng `status`. Với `NODE_ENV=production`, các store không migrate lúc khởi động: một schema lạc hậu sẽ làm việc khởi động thất bại.
- Trên PostgreSQL, giữ isolation mặc định của database ở READ COMMITTED: các store từ chối một level chặt hơn. Trên MySQL, hãy chạy lại một transaction khi MySQL phá deadlock trong nó (lỗi 1213): nó đã rollback, kéo theo các message nó đã dispatch và các webhook nó đã ghi nhận.
- Hãy để `delivery.allowHttp` và `delivery.allowPrivateNetworks` tắt. URL của đối tác là dữ liệu không đáng tin, và transport tự resolve nó rồi cố định địa chỉ đã kiểm tra. Dùng `allowedAddresses` cho một dải địa chỉ private mà bạn thực sự cần gửi tới, và đặt cảnh báo cho các event `destination-blocked`: một khách hàng trỏ webhook vào dịch vụ metadata của bạn là chuyện đáng để mắt tới.
- Chạy worker trên vài instance (`WEBHOOKS_WORKER`), không phải trên mọi pod API: mỗi lần claim là một transaction ngắn, và các lease ngăn chúng gửi cùng một lần gửi hai lần.
- Đặt cảnh báo cho `lagMs` và `failed` từ `deliveries.stats()`, và cho `endpoint-disabled`: hãy báo cho đối tác, qua email, rằng endpoint của họ đã bị tắt và vì sao.
- Đánh version cho payload. Một đối tác giữ handler của họ trong nhiều năm, và `retry()` gửi lại body đúng như lúc được dispatch. Hãy thêm trường vào `data` của một loại event, đừng bao giờ đổi tên hay xóa trường. Với một thay đổi phá vỡ tương thích, hãy thêm một loại mới, `order.shipped.v2` trong `eventTypes`, và dispatch cả hai trong cùng transaction (`dispatch()` nhận một mảng) trong khi các đối tác chuyển đăng ký sang; một endpoint đăng ký `*` sẽ nhận cả hai. Sau đó ngừng dispatch loại cũ. Các lần gửi lại message cũ vẫn mang cấu trúc cũ cho đến khi log được dọn.
- Cung cấp cho đối tác log gửi và tính năng gửi lại. Nó trả lời câu "anh đã gửi chưa?" trước khi họ phải mở ticket.
- Xoay vòng secret có khoảng chồng lấn, đừng bao giờ dùng `overlap: 0` trừ khi secret đã bị lộ, và niêm phong chúng khi lưu trữ bằng `WEBHOOKS_ENCRYPTION_KEYS`. Giữ các key trong một secret manager.
- Dọn log. Chạy `deliveries.prune('30d')` từ một [cron job](/application/task-scheduling#declarative-cron-jobs); không có gì tự lên lịch việc này giúp bạn.
- Với webhook nhận vào, giữ `rawBody: true`, và giữ secret của các receiver trong biến môi trường. Liệt kê cả secret cũ lẫn mới trong khi một provider xoay vòng.
- Giữ handler của provider ngắn gọn và tự thân idempotent (một bước kiểm tra trạng thái bên trong transaction), kể cả khi dùng `processInTransaction()`: inbox bảo vệ khỏi một lần gửi lại, còn bước kiểm tra bảo vệ khỏi một provider gửi hai event khác nhau cho cùng một sự việc.
- Dọn inbox bằng `OutboxInbox.prune()` với một khoảng thời gian dài hơn lịch retry của mọi provider (Stripe retry trong ba ngày, GitHub hoàn toàn không retry). Với GitHub, khoảng thời gian đó cũng là khoảng thời gian một request gửi lại bị bắt được, khi loại trùng dựa trên body ([Các bên gửi khác](/http/webhooks#other-senders)).
- Gọi `app.enableShutdownHooks()`, để một đợt deploy cho các lần thử đang dở hoàn tất và trả lại phần còn lại.
- Với store của riêng bạn, hãy chạy các bộ test hợp đồng với `concurrent: true` trong CI, trên đúng phiên bản database mà bạn chạy trên production.

#### Hợp đồng của store

`PostgresWebhookStore` và `MySqlWebhookStore` implement cả hai hợp đồng của package, `WebhookEndpointStore` và `WebhookDeliveryStore`. Với một database khác, hãy implement chúng trong một provider của riêng bạn. JSDoc của mỗi method trong hai interface nêu quy tắc của nó, và cuộc đua mà nó ngăn chặn.

**Đăng ký.** Store là một singleton provider thông thường, gọi `registerSource()` trên `WebhooksStorage` có thể inject trong constructor của nó, nêu tên các hợp đồng mà nó implement: `endpoints`, `deliveries`, hoặc cả hai từ một class. Registry kiểm tra cấu trúc ngay lập tức, từ chối lần đăng ký thứ hai trừ khi nó truyền `replace: true`, và khóa lại khi `WebhooksModule` khởi tạo, log store đang được dùng. Khi không có gì được đăng ký, module dùng `InMemoryWebhookStore`, store này mất các endpoint và các lần gửi đang chờ khi khởi động lại và không chia sẻ được giữa các instance. Với `NODE_ENV=production`, việc khởi động sẽ thất bại, trừ khi `allowInMemoryStorage: true` chấp nhận điều đó.

**Không có transaction handle.** Khác với `add()` của outbox, không method nào ở đây nhận transaction của bạn: outbox mang message ra khỏi transaction của bạn, còn webhook store chạy trên kết nối riêng của nó.

**Các method.** Những method được đánh dấu nguyên tử là một câu lệnh có điều kiện duy nhất hoặc một transaction có row lock, không bao giờ là đọc rồi ghi; đó là những method mà các bộ test hợp đồng cho chạy đua.

| Method | Nó làm gì | Nguyên tử |
| --- | --- | --- |
| `createEndpoint`, `getEndpoint`, `listEndpoints`, `updateEndpoint`, `deleteEndpoint` | Vòng đời của một endpoint; `list` mới nhất trước, theo tenant | Không |
| `findSubscribedEndpoints(tenant, type)` | Các endpoint đang bật của đúng tenant này đã đăng ký nhận loại event đó (hoặc `*`): query của bước phân phối | Không, nhưng bộ test kiểm tra nó không bao giờ trả về endpoint của tenant khác |
| `addEndpointSecret(id, secret, expireOthersAt, now)` | Việc xoay vòng: secret mới đứng đầu, các secret khác sắp hết hạn | Có: dòng dữ liệu bị khóa, nên hai lần xoay vòng đều được ghi nhận |
| `recordEndpointFailure(id, failure)` | Đặt `failingSince` ở lần thất bại đầu tiên; tắt endpoint khi nó đã thất bại đủ lâu, và báo điều đó một lần | Có: dòng dữ liệu bị khóa |
| `recordEndpointSuccess(id)` | Xóa `failingSince` | Không |
| `createDeliveries(message, deliveries)` | Bước phân phối: message nếu chưa tồn tại, mỗi lần gửi nếu `(messageId, endpointId)` của nó chưa tồn tại | Có: một key duy nhất trên cặp này, như `ON CONFLICT DO NOTHING` của PostgreSQL trên nó |
| `claimDeliveries(request)` | Lease các lần gửi đến hạn, trễ hạn nhất trước, kèm message của chúng | Có: `FOR UPDATE SKIP LOCKED`, rồi đến lease |
| `recordDeliveryAttempt(id, owner, update)` | Kết quả và dòng log của lần thử, nếu `owner` vẫn còn giữ lease | Có: được rào chắn bởi chủ sở hữu lease |
| `releaseDeliveries(ids, owner, nextAttemptAt)` | Trả lại lease, hoãn lại khi được yêu cầu | Có: được rào chắn |
| `getDelivery`, `getMessage`, `listDeliveries`, `listDeliveryAttempts`, `deliveryStats` | Các thao tác đọc; `list` mới nhất trước, theo tenant, endpoint, message, trạng thái và loại | Không |
| `retryDeliveries(filter, now)` | Một vòng mới cho những lần gửi khớp điều kiện mà không đang bị lease | Có: một câu `UPDATE` với lease nằm trong `WHERE` |
| `pruneDeliveries(before)` | Các lần gửi đã kết thúc cũ hơn `before`, log của chúng, và các message không còn lần gửi nào | Không, nhưng không bao giờ xóa một lần gửi đang chờ |

**Test nó** bằng `webhookEndpointStoreContract()` và `webhookDeliveryStoreContract()` từ `@nestjs/webhooks/testing`. Mỗi case nhận một store trên các bảng rỗng từ hàm mà bạn truyền vào. Các test của bài hướng dẫn chạy cả hai bộ test với `PostgresWebhookStore` thông qua Drizzle, giống như bạn sẽ làm với store của mình:

[[CODE:66]]

Với `concurrent: true`, các bộ test cho chạy đua việc xoay vòng và các lần thất bại trên một endpoint, các worker claim song song, các lần phân phối của cùng một message, một worker cũ đối đầu với một lần tiếp quản, và một lần retry đối đầu với một lần claim. Trên PGlite, với một kết nối, chúng qua được vì bị tuần tự hóa: hãy chạy chúng trên cả một server, thông qua một pool có nhiều kết nối, nơi một store thiếu các lock phù hợp sẽ thất bại. Các test của chính package chạy các bộ test với một store Drizzle viết tay, như bằng chứng rằng một store viết theo các interface sẽ qua được chúng.
