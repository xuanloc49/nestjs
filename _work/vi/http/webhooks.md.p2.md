#### Cho đối tác đăng ký

Các trại cứu trợ và đại lý gọi API đối tác bằng một API key: hai đối tác của ví dụ, Northside Pet Supplies (một đại lý) và Riverside Cat Shelter, có các key mẫu trong phần [Cài đặt](/http/webhooks#installation). `PartnerGuard` tra hash của key và đặt đối tác lên request, còn `@CurrentPartner()` đọc nó:

[[CODE:13]]

Một lần đăng ký gồm một URL, các loại event cần nhận, và một mô tả; một lần cập nhật chỉ gửi những gì thay đổi. Các DTO kiểm tra cấu trúc, và để URL cùng các loại event cho package, vì package biết nó chấp nhận gì. Request body được validate bằng bất cứ công cụ nào ứng dụng đang dùng: mọi DTO trên trang này đều có hai phiên bản, một class với decorator của `class-validator` và một schema Zod, nên hãy chọn kiểu bạn đang dùng và bỏ qua phiên bản còn lại:

[[CODE:14]]

Cùng các quy tắc đó dưới dạng schema Zod, với type suy ra từ schema thay cho class. Nest 12.1 validate mọi object [Standard Schema](https://standardschema.dev/), từ Zod, Valibot hay ArkType, thông qua `StandardSchemaValidationPipe`:

[[CODE:15]]

API đăng ký là một controller bọc quanh `WebhookEndpoints`. Mọi lời gọi đều truyền id của đối tác làm **tenant**: một endpoint được tạo cho tenant đó, được liệt kê cho tenant đó, và id endpoint của một đối tác khác sẽ hoạt động như thể nó không tồn tại:

[[CODE:16]]

Với các schema Zod, tham số body khai báo schema thay vì class:

[[CODE:17]]

> info **Hint** Các DTO chỉ được áp dụng khi có validation pipe: hãy bind `ValidationPipe` ở cấp global, bằng `useGlobalPipes()` trong `main.ts` như phần [Đăng ký các module](/http/webhooks#register-the-modules) làm (`whitelist` bỏ các thuộc tính không có decorator), hoặc dưới dạng provider `APP_PIPE`. Với các schema Zod, hãy bind `StandardSchemaValidationPipe` theo cùng cách: một ứng dụng dùng một trong hai. Trang [validation](/application/validation) có các tùy chọn của mỗi loại.

`create()` trả về endpoint kèm `secret` của nó, một `whsec_…` theo Standard Webhooks gồm 32 byte ngẫu nhiên, được sinh ra tại đây. API này chỉ hiển thị nó đúng một lần này: `list()` và `get()` không bao giờ kèm nó, và một đối tác làm mất nó thì phải xoay vòng. Package giữ secret, được niêm phong khi đặt `encryption`, vì nó dùng secret đó để ký, và `getSecret()` đọc lại secret hiện tại, dành cho một nút "hiện secret" đặt sau một lần đăng nhập mới nếu API của bạn có cung cấp. Các endpoint chuyển từ Svix hoặc một bên gửi Standard Webhooks khác vẫn giữ secret của chúng: một script chuyển đổi truyền `whsec_…` hiện có của đối tác làm `secret` của `create()`, để bộ xác minh của đối tác vẫn hoạt động, và `rotateSecret()` nhận một `secret` được cung cấp theo cùng cách. Package kiểm tra những gì đối tác gửi lên và throw một `InvalidWebhookEndpointError` với status 400: một URL không phải `https://` (hoặc `http://` khi có `allowHttp`), một URL có chứa thông tin đăng nhập, hoặc có host là một địa chỉ bị chặn, như `https://169.254.169.254/latest/meta-data/` hay `https://localhost/`; một loại event không nằm trong `eventTypes`. Lỗi của đối tác được trả về dưới dạng 400, còn id của đối tác khác dưới dạng 404, thông qua một filter:

[[CODE:18]]

[[CODE:19]]

Controller của log gửi, được thêm vào module này [ở phần sau](/http/webhooks#retries-the-delivery-log-and-replay), cho đối tác nửa còn lại: những gì đã được gửi tới các endpoint của họ.

#### Gửi order.shipped và order.cancelled sau khi commit

`Webhooks.dispatch()` nhận transaction handle của bạn làm tham số đầu tiên, giống như `Outbox.add()`: với Drizzle, đó là `tx` mà `db.transaction()` truyền cho callback của nó, với type mà service gán cho `Webhooks<Transaction>`. Hủy một đơn hàng sẽ cập nhật nó và dispatch `order.cancelled` trên cùng `tx`; giao nó (do hãng vận chuyển kích hoạt, trong phần [Nhận webhook kiểu Stripe của hãng vận chuyển](/http/webhooks#receive-the-carriers-stripe-like-webhooks)) sẽ cập nhật nó và dispatch `order.shipped`. `tenant` là đối tác đã đặt đơn hàng, nên chỉ các endpoint của đối tác đó mới nhận được nó:

[[CODE:20]]

Không có gì rời khỏi process bên trong transaction. Nếu nó rollback, message chưa bao giờ tồn tại. Nếu nó commit, outbox relay lấy message (`notify()` yêu cầu nó làm việc này ngay thay vì chờ tới lần poll tiếp theo) và chuyển nó cho bước phân phối của package, bước này tạo một lần gửi cho mỗi endpoint đang bật của tenant đã đăng ký nhận loại event đó. Sau đó worker ký và gửi từng lần. Đây là những gì server của Northside nhận được, ở mọi lần thử của lần gửi, với cùng `webhook-id` và chính xác body đã được serialize lúc `dispatch()`:

[[CODE:21]]

Chữ ký được tạo bằng secret của endpoint, nên đối tác có thể xác minh nó bằng bất kỳ library Standard Webhooks nào. Hoặc bằng chính package này: receiver của Northside là một ứng dụng Nest riêng, với root module riêng, chỉ để nhận, với `outgoing: false`, và `@VerifyWebhook('store')` trên route của nó. `STORE_WEBHOOK_SECRET` nhận một danh sách phân cách bằng dấu phẩy, vì [việc xoay vòng](/http/webhooks#rotate-secrets) của cửa hàng ký bằng hai secret trong một ngày:

[[CODE:22]]

[[CODE:23]]

[[CODE:24]]

`OutboxModule` của đối tác cung cấp inbox mà `@VerifyWebhook()` dùng để loại trùng. Ở đây nó chạy trong bộ nhớ; một đối tác thực tế sẽ đăng ký store của outbox trên database của riêng họ, `PostgresOutboxStore` trên PostgreSQL, như analytics service làm trong [bài hướng dẫn outbox](/reliability/outbox#publish-to-the-analytics-microservice).

#### Retry, log gửi và gửi lại

Một response 2xx từ đối tác là thành công. Mọi thứ khác là một lần thử thất bại: 5xx, 4xx, 3xx (redirect không bao giờ được đi theo), timeout, kết nối bị từ chối. Worker retry sau khoảng backoff, tôn trọng header `Retry-After` tính bằng giây hoặc dưới dạng HTTP date (tối đa bằng mức trần của backoff, một ngày; mọi giá trị khác bị bỏ qua), và với lỗi 429, 502, 503 hoặc 504 thì tạm dừng endpoint đó cho đến lúc ấy, năm giây nếu không có header: các lần gửi khác của nó sẽ chờ mà không thử, để một đối tác xin được nghỉ chỉ nhận một lần thăm dò, chứ không phải mỗi lô một lần, trong khi các lần gửi của đối tác khác vẫn tiếp tục. Có ba câu trả lời kết thúc sớm một lần gửi: 410 Gone, câu trả lời này cũng tắt luôn endpoint (`gone`); một đích mà transport từ chối (các bước kiểm tra lúc đăng ký, chạy lại ở mỗi lần gửi, vì DNS có thể thay đổi); và `retry.retryIf` trả lời không. Sau lần thử cuối cùng, lần gửi ở trạng thái `failed` với lý do `exhausted`.

Một endpoint thất bại ở mọi lần thử trong suốt `disableEndpointAfter` sẽ bị tắt với lý do `failing`, và `WebhooksEvents` phát ra `endpoint-disabled`: hãy báo cho đối tác. Một lần thành công bất kỳ lúc nào sẽ reset đồng hồ. Một endpoint bị tắt, dù do worker hay do đối tác (`enabled: false` trong `update()` của đăng ký), sẽ không nhận lần gửi nào cho những gì được dispatch trong lúc nó vẫn bị tắt: bước phân phối bỏ qua nó, và không có gì tạo ra những lần gửi đó sau này. Gửi lại cũng không, vì nó gửi lại những lần gửi đã tồn tại. Những gì tồn tại là các lần gửi đang chờ khi endpoint bị tắt: chúng thất bại với lý do `endpoint-disabled` khi tới lượt, và sau khi bật lại, đối tác có thể yêu cầu gửi lại những lần đó, như những lần gửi thất bại. Bật lại sẽ quên các lần thất bại, và endpoint nhận những gì được dispatch kể từ đó.

Mọi lần thử đều được log: status code, thời gian, 4 KB đầu tiên của body response, lỗi. Đối tác đọc log của riêng họ, và yêu cầu gửi lại một lần gửi, một lần hoặc mọi lần thất bại kể từ khi sự cố bắt đầu. Việc retry hàng loạt nhận một endpoint và thời điểm bắt đầu sự cố, cả hai đều tùy chọn:

[[CODE:25]]

[[CODE:26]]

[[CODE:27]]

Với schema Zod:

[[CODE:28]]

Một lần retry bắt đầu một vòng mới: `attempts` về 0, gửi ngay lập tức, với cùng `webhook-id` và cùng body. Log của các vòng trước vẫn được giữ lại. Vì id giống nhau, một đối tác có inbox đã lưu nó sẽ trả lời 2xx mà không chạy handler, nên gửi lại cũng an toàn với một webhook đã được giao: Northside có thể yêu cầu gửi lại toàn bộ giờ vừa qua sau khi mất database của họ, và chỉ nhận những gì họ chưa xử lý.

Người vận hành có cùng các khả năng đó thông qua `WebhookDeliveries` mà không cần tenant: `stats()` (số lượng đang chờ, đến hạn, đang lease và thất bại, cùng `lagMs`, thời gian mà lần gửi trễ hạn nhất đã phải chờ, con số cần đặt cảnh báo), `retry()` xuyên các tenant, và `prune('30d')`, thứ không có gì tự gọi giúp bạn. `WebhooksEvents.events$` phát ra `delivered`, `retry-scheduled`, `delivery-failed`, `endpoint-disabled` và `destination-blocked`, mỗi event cũng có trên một channel `node:diagnostics_channel` tên `nestjs:webhooks:<event>`.

#### Nhận webhook của payment provider

Payment provider báo cho cửa hàng biết một khoản thanh toán đã thành công bằng một request Standard Webhooks. Xác minh nó cần body đúng như provider đã ký, nên ứng dụng được tạo với `rawBody: true`. Cách này hoạt động trên cả Express lẫn Fastify:

[[CODE:29]]

Bên gửi được đưa vào `receivers` của module, theo tên mà route sẽ dùng. Secret của payment provider là thứ nó hiển thị trong dashboard:

[[CODE:30]]

`@VerifyWebhook('payments')` trên route xác minh request trước khi handler chạy, còn `@IncomingWebhook()` cung cấp những gì đã được xác minh: `id` của webhook do bên gửi đặt, `timestamp` đã ký, `payload` được parse từ các byte đã ký, và `processInTransaction()`:

[[CODE:31]]

[[CODE:32]]

[[CODE:33]]

Những gì decorator kiểm tra, theo thứ tự: ba header `webhook-` có mặt và đúng định dạng, với `webhook-id` tối đa 255 ký tự, đếm theo code point; một chữ ký `v1,` trong `webhook-signature` khớp với HMAC của `id.timestamp.body` dùng một trong các secret đã cấu hình (so sánh trong thời gian không đổi; có thể liệt kê nhiều secret trong khi payment provider xoay vòng); timestamp đã ký nằm trong khoảng 5 phút so với hiện tại, theo cả hai chiều; body là JSON. Một request không đạt sẽ nhận lỗi 401 với message chung chung. Lý do không bao giờ được gửi cho bên gửi; nó được đưa vào event `verification-failed`, kèm tên receiver. Một body đã ký nhưng không phải JSON sẽ nhận lỗi 400 từ body parser của framework trước khi decorator thấy nó, nên không có event nào được phát ra cho nó. Điều tương tự đúng với một body vượt quá giới hạn kích thước của body parser (mặc định 100 kB trên Express và 1 MiB trên Fastify): nó nhận lỗi 413 trước khi decorator chạy, và không có event nào được phát ra. Nếu payment provider gửi body lớn hơn, hãy nâng giới hạn bằng `useBodyParser()`, như mô tả trong [Raw body](/faq/raw-body#body-parser-size-limit).

Tiếp theo là loại trùng. Payment provider retry cho đến khi nhận được 2xx, nên một timeout xảy ra sau khi handler đã thành công sẽ khiến nó gửi lại cùng `webhook-id`. Receiver giữ một inbox chứa các id nó đã xử lý (inbox của outbox, consumer `webhooks:payments`): một id đã biết sẽ được trả lời bằng 200 rỗng mà không chạy handler, và một id chỉ được ghi nhận sau khi handler thành công, nên một handler đã throw sẽ được chạy lại ở lần retry của payment provider. Hai bản sao đến cùng lúc tại một instance chỉ chạy handler một lần; hai instance nhận chúng đúng cùng một thời điểm có thể cùng chạy, và đoạn tiếp theo là để xử lý trường hợp đó.

`markPaid()` thay đổi state liên quan tới tiền, nên controller tiến thêm một bước với `processInTransaction()`: id của webhook được ghi nhận *thông qua transaction của đơn hàng*, và `markPaid()` chỉ chạy nếu id đó là mới. Bản ghi và trạng thái mới được commit cùng nhau. Một lần gửi lại sau khi crash giữa handler và lúc ghi inbox, hoặc một lần chạy đua với request này trên instance khác, sẽ thấy id và không thay đổi gì; nó resolve với `duplicate` được đặt, thứ mà controller dùng để chỉ log một lần. Và khi `markPaid()` throw, ví dụ một khoản thanh toán sai số tiền, transaction sẽ rollback, kéo theo bản ghi, bên gửi nhận lỗi 409, và lần retry của nó có thêm cơ hội khi đơn hàng đã được sửa.

Để phát triển, một script nhỏ ký request theo cách mà payment provider (và, ở phần tiếp theo, hãng vận chuyển) sẽ làm, bằng `signWebhook()` từ `@nestjs/webhooks/testing`:

[[CODE:34]]

#### Nhận webhook kiểu Stripe của hãng vận chuyển

Hãng vận chuyển chép theo kiểu chữ ký của Stripe: một header `Carrier-Signature: t=…,v1=…`, HMAC-SHA256 dạng hex của `t.body` dùng text của secret làm key, và id của event nằm trong payload. Receiver trong [tùy chọn `receivers`](/http/webhooks#receive-the-payment-providers-webhooks) nói rõ điều đó: `scheme: 'stripe'` cùng tên `header`. Webhook của chính Stripe là cùng receiver đó mà không có `header`. Webhook của GitHub, và các bên gửi có kiểu chữ ký riêng, nằm trong phần [Các bên gửi khác](/http/webhooks#other-senders).

Handler mới là phần thú vị. Đánh dấu đơn hàng đã giao và báo cho đối tác diễn ra trong một transaction: trạng thái mới của đơn hàng, message `order.shipped` cho đối tác (qua outbox) và bản ghi inbox của webhook này được commit cùng nhau, hoặc không cái nào cả:

[[CODE:35]]

`markShipped()` là method từ phần [Gửi order.shipped và order.cancelled sau khi commit](/http/webhooks#send-ordershipped-and-ordercancelled-after-the-commit). Id dùng để loại trùng là `id` của event lấy từ payload đã ký, không phải từ header, vì đó là thứ mà kiểu chữ ký của Stripe ký. Một event `shipment.shipped` cho đơn hàng chưa thanh toán sẽ bị từ chối với lỗi 409, và không có gì được ghi nhận: khi hãng vận chuyển retry sau khi khoản thanh toán đã đến, cùng event id đó sẽ được xử lý.

#### Các bên gửi khác

Webhook của GitHub dùng `scheme: 'github'`: `X-Hub-Signature-256`, HMAC-SHA256 dạng hex của body dùng text của secret làm key.

> warning **Warning** GitHub không ký timestamp hay id. Một request bị bắt được sẽ xác minh được mãi mãi, và việc loại trùng mặc định dựa trên header `X-GitHub-Delivery`, header này không được ký: cùng request đó được gửi lại với một giá trị mới trong header đó sẽ chạy handler lần nữa.

Thay vào đó, hãy loại trùng dựa trên body đã ký, bằng tùy chọn `id` của receiver. Payload được parse từ các byte đã ký, nên một lần gửi lại có cùng id với bản gốc, và inbox sẽ bỏ qua nó:

[[CODE:36]]

Inbox nhớ một id cho đến khi `OutboxInbox.prune()` xóa nó, nên với GitHub, khoảng thời gian đó cũng chính là khoảng thời gian một lần gửi lại bị bắt được: hãy giữ nó dài. Gửi lại sau khoảng đó, một request vẫn xác minh được và chạy; chỉ chấp nhận webhook của GitHub từ các địa chỉ mà nó công bố (`hooks` trong `https://api.github.com/meta`) sẽ thu hẹp được ai có thể gửi.

Một bên gửi có kiểu chữ ký riêng là một class kế thừa `WebhookSignatureScheme`. Giả sử cửa hàng còn bán qua một sàn thương mại điện tử, sàn này ký URL mà nó post tới, theo sau là body, và đặt id của event trong body:

[[CODE:37]]

- `verify(request, keys)` nhận `headers` của request (tên viết thường) và `rawBody` của nó, đúng như đã nhận, cùng một key cho mỗi secret đã cấu hình. Nó trả về `valid: true`, kèm `id` của bên gửi khi có header mang id và `timestamp` đã ký tính bằng giây epoch khi kiểu chữ ký có ký timestamp (khi đó `tolerance` của receiver được áp dụng), hoặc `valid: false` kèm `reason` cho event `verification-failed` và một `detail`. Nó chạy đồng bộ, trước khi body được parse thành JSON.
- `WebhookSignatureScheme.matches(expected, candidates)` so sánh trong thời gian không đổi. Đừng bao giờ so sánh chữ ký bằng `===`.
- `idFromPayload(payload, headers)` cung cấp id để loại trùng khi không có header nào mang id, từ body đã parse, như kiểu chữ ký Stripe có sẵn làm với `id` của event. Một id dài hơn 255 ký tự, từ bất kỳ nguồn nào, sẽ bị từ chối với `malformed-header`.
- `key(secret)` chuyển mỗi secret đã cấu hình thành key mà `verify()` nhận được, một lần, lúc khởi động, nơi một secret sai định dạng sẽ làm ứng dụng dừng lại. Mặc định nó lấy text của secret và từ chối secret rỗng hoặc có khoảng trắng bao quanh. Hãy ghi đè nó cho một secret đã được encode, như kiểu chữ ký `standard` làm với `whsec_…`.

Receiver nhận một instance:

[[CODE:38]]

#### Xoay vòng secret

Một secret bị lộ, hoặc chính sách của đối tác nói một năm là đủ. `POST /partner/webhook-endpoints/:id/rotate-secret` (xem [Cho đối tác đăng ký](/http/webhooks#let-partners-subscribe)) trả về một secret mới, và secret cũ vẫn tiếp tục ký cạnh nó trong `secretRotationOverlap`, 24 giờ: mỗi lần gửi mang hai chữ ký `v1,`, và một bộ xác minh Standard Webhooks chấp nhận bất kỳ chữ ký nào khớp. Đối tác thêm secret mới vào danh sách, deploy, rồi bỏ secret cũ, theo lịch của riêng họ. Sau khoảng chồng lấn, chỉ secret mới ký. `rotateSecret()` với `overlap: 0` thu hồi secret cũ ngay lập tức, dành cho secret đã bị lộ.

Đặt `WEBHOOKS_ENCRYPTION_KEYS` để niêm phong các secret khi lưu trữ, `openssl rand -base64 32` cho mỗi key, mới nhất trước. Các endpoint tạo trước đó vẫn được đọc (secret của chúng là plaintext) và được niêm phong ở lần xoay vòng tiếp theo.

#### Thử ngay

Tạo database, và áp dụng các migration của bạn vào đó, chúng tạo các bảng và dòng dữ liệu của API đơn hàng trong phần [Cài đặt](/http/webhooks#installation):

[[CODE:39]]

Export các secret mà payment provider và hãng vận chuyển dùng chung với cửa hàng (ở đây là bịa ra), cho phép gửi tới máy này, và khởi động API trên port 3000:

[[CODE:40]]

[[CODE:41]]

Các migration của bạn đã tạo các bảng của API đơn hàng, còn các store tạo schema của chúng, nằm cạnh đó. Northside đăng ký, bằng API key của mình, nhận cả hai event tại một receiver mà họ sẽ chạy trên port 4100. Response mang theo secret, đúng một lần này:

[[CODE:42]]

> info **Hint** `--json` cần curl 7.82 trở lên.

URL của một dịch vụ metadata cloud bị từ chối trước khi bất cứ thứ gì được lưu, và một loại event mà API không gửi cũng vậy. Riverside Cat Shelter, đối tác còn lại, nhận lỗi 404 với endpoint của Northside:

[[CODE:43]]

Khởi động receiver của Northside, `partner-service/main.ts`, trên port 4100, với secret được cấp nằm trong môi trường của nó:

[[CODE:44]]

Giờ hãy đặt một đơn hàng, và để payment provider thanh toán còn hãng vận chuyển giao nó. Script ký các request mà họ sẽ gửi, bằng các secret đã export ở trên:

[[CODE:45]]

Log của API cho thấy cả hai webhook đã được xử lý, còn log của Northside cho thấy `order.shipped` đến ngay sau webhook của hãng vận chuyển, kèm `webhook-id` của nó:

[[CODE:46]]

[[CODE:47]]

Log gửi của Northside có lần gửi đó, và chi tiết của nó có message cùng một lần thử, kèm status code của đối tác và thời gian nó mất:

[[CODE:48]]

[[CODE:49]]

Dừng receiver của Northside bằng `Ctrl+C`, rồi đặt một đơn hàng và hủy nó. Lần gửi không kết nối được, API log thời gian chờ trước lần thử tiếp theo, và log của đối tác cho thấy lần gửi đang chờ kèm lỗi của nó:

[[CODE:50]]

[[CODE:51]]

Khởi động lại receiver. Lần retry đi qua, và log giữ lại cả hai lần thử:

[[CODE:52]]

[[CODE:53]]

[[CODE:54]]

Northside yêu cầu gửi lại lần gửi đó. Nó được gửi với cùng `webhook-id`, inbox của receiver nhận ra nó và trả lời 204 mà không chạy handler (không có gì mới trong log của nó), và log gửi cho thấy một vòng mới:

[[CODE:55]]

[[CODE:56]]

Giờ là phía payment provider. Một lần gửi lại với cùng `webhook-id` (do mất response 200, nên provider đã retry) được trả lời nhưng không được xử lý lại: API chỉ log một khoản thanh toán. Một body bị giả mạo và một secret sai đều bị từ chối, không kèm lý do:

[[CODE:57]]

[[CODE:58]]

Cuối cùng, xoay vòng secret của endpoint. Receiver vẫn chạy với secret cũ, và lần gửi tiếp theo vẫn xác minh được: nó mang cả hai chữ ký. Sau đó khởi động lại receiver với secret mới đứng đầu danh sách và secret cũ đứng sau, như cách một đối tác sẽ deploy, rồi đặt và hủy thêm một đơn hàng: lần gửi đó cũng xác minh được:

[[CODE:59]]

[[CODE:60]]

[[CODE:61]]

[[CODE:62]]

[[CODE:63]]

Các lần gửi là các dòng trong database của bạn, trong schema của store:

[[CODE:64]]

#### Test

Trong một e2e test, hãy chạy PostgreSQL ngay trong process bằng [PGlite](https://pglite.dev) với các migration thật của bạn, tắt relay và worker, thay transport bằng transport ghi lại request, và ký request của các provider bằng `signWebhook()`. Ghi đè database mà `DrizzleModule` đăng ký (`getDrizzleToken()` trả về token của nó) bằng một database trên PGlite: các store sẽ theo đó, vì factory của chúng inject nó, và tạo schema của chúng ở đó khi ứng dụng khởi động:

[[CODE:65]]

- Outbox, cả hai store, các migration, bước phân phối, việc ký và việc xác minh đều là thật. Chỉ có mạng là bị thay thế: `InMemoryWebhookTransport` trả lời 200 và giữ lại mọi request, còn `respondWith(503)` hoặc một hàm giả lập một đối tác đang bị sập, chậm, hoặc khó tính.
- `deliver()` là toàn bộ pipeline sau khi commit: `relay.runOnce()` publish các message đã commit (bước phân phối tạo các lần gửi), `worker.runOnce()` lấy một lô và gửi nó.
- `SentWebhook.isSignedWith(secret)` xác minh chữ ký `v1` bằng secret của một endpoint, còn `data` là `data` của body, nên bài test kiểm tra đúng những gì đối tác lẽ ra sẽ xác minh và đọc.
- `signWebhook()` tạo ra body và header mà payment provider, Stripe hay GitHub sẽ gửi. Dùng lại `id` của nó cho một lần gửi lại, dịch `timestamp` để test khoảng dung sai, đổi một byte của body cho một request bị giả mạo.
- Với các hành vi phụ thuộc thời gian, như backoff, lease và khoảng chồng lấn khi xoay vòng, hãy đẩy `Date.now()` tới trước bằng `vi.spyOn(Date, 'now')`. Worker và các store lấy thời gian từ nó, còn timer thật vẫn tiếp tục chạy cho socket.
- `tutorial.e2e-spec.ts` của ví dụ chạy mọi phần trên trang này qua HTTP thật, trên PGlite và trên một PostgreSQL server: API gửi tới receiver của đối tác qua transport mặc định, với sự cố, việc gửi lại, các lần gửi trùng và việc xoay vòng. `zod.e2e-spec.ts` của nó khởi động cùng app đó với các biến thể Zod của DTO và `StandardSchemaValidationPipe`. Các test store của nó chạy các store thông qua Drizzle trên PGlite, PostgreSQL và MySQL, và thông qua TypeORM trên PostgreSQL: các bộ test hợp đồng, một lần dispatch commit và rollback cùng đơn hàng, và các schema trên production.

Xem [End-to-end test](/fundamentals/testing#end-to-end-testing) để biết thêm về việc thiết lập test.
