#### Tham khảo

##### Tùy chọn của module

`IdempotencyModule.forRoot()` nhận các tùy chọn sau. `forRootAsync()` nhận `isGlobal` và `imports` ở cấp ngoài cùng, cạnh `useFactory`, `useClass` hoặc `useExisting`, và factory trả về phần còn lại. Mọi tùy chọn trừ `header`, `replayHeaders`, `encryption`, `allowInMemoryStorage` và `isGlobal` cũng có thể đặt theo từng class hoặc handler trong `@Idempotent()`, khi đó nó được merge theo từng field lên trên tùy chọn của module.

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `required` | `boolean` | `false` | Từ chối các lời gọi không có key với `IDEMPOTENCY_KEY_REQUIRED`. Xem [Làm endpoint thanh toán trở nên idempotent](/reliability/idempotency#make-the-payment-endpoint-idempotent). |
| `scope` | hàm, object hoặc `false` | không có | Namespace của key, chẳng hạn id người dùng. Một object có mỗi context một hàm, dưới `http`, `graphql` và `rpc`. `false` cố ý dùng chung một namespace. |
| `ttl` | `Duration` | `'24h'` | Khoảng thời gian một kết quả đã hoàn tất được replay. Xem [Tinh chỉnh TTL và cách xử lý thất bại](/reliability/idempotency#tune-ttls-and-failure-handling). |
| `lockTtl` | `Duration` | `'60s'` | Khoảng thời gian một lock đang xử lý còn tồn tại sau khi việc gia hạn dừng lại. Lock được gia hạn mỗi `lockTtl / 3`. |
| `retryAfter` | `Duration` | `'1s'` | Thời gian chờ được gửi kèm `IDEMPOTENCY_KEY_IN_USE`, tính bằng số giây nguyên, làm tròn lên. |
| `keyFrom` | source, hoặc mỗi context một source | xem bên dưới | Nơi lấy key: `header`, `arg` (GraphQL), `payload` (microservice) hoặc một hàm nhận `ExecutionContext`. |
| `fingerprint` | `(payload, context) => unknown` | toàn bộ payload | Những gì một lần retry phải lặp lại. Method và URL, field GraphQL hoặc message pattern, và scope luôn được tính. |
| `storeIf` | `(status, error) => boolean` | `status < 500` | Những kết quả nào được lưu và replay. Các kết quả khác giải phóng key. |
| `header` | `string` | `'Idempotency-Key'` | HTTP header, GraphQL cũng đọc header này, và là tên header của transport với microservice. |
| `replayHeaders` | `string[]` | không có | Các response header được replay thêm ngoài `Location`, `Content-Type`, `Content-Language`, `Content-Location`, `ETag` và `Last-Modified`. `Set-Cookie` và các header mà platform ghi cho mọi response sẽ bị từ chối lúc khởi động. |
| `encryption` | một object có `keys` | tắt | Mã hóa AES-256-GCM cho các record được lưu. `keys` liệt kê các `Buffer` 32 byte hoặc chuỗi có ít nhất 32 ký tự, khóa mới nhất đứng đầu. Xem [Mã hóa biên lai được lưu](/reliability/idempotency#encrypt-stored-receipts). |
| `allowInMemoryStorage` | `boolean` | `false` | Cho phép một ứng dụng production khởi động mà không có store được đăng ký. |
| `isGlobal` | `boolean` | `true` | Đăng ký module ở phạm vi global. |

Mọi khoảng thời gian đều nhận số mili giây hoặc một chuỗi như `'45s'`, `'48h'` hay `'7d'`.

Mặc định, key được lấy từ các nguồn sau:

| Context | Nguồn mặc định |
| --- | --- |
| HTTP | Header `Idempotency-Key` (tùy chọn `header`) |
| GraphQL | Argument `idempotencyKey` của mutation, sau đó là header |
| Microservice | Thuộc tính `idempotencyKey` của payload, sau đó là header của transport có tên do `header` chỉ định |

Một key gồm 1 đến 255 ký tự ASCII in được. Một số trong payload được tính theo các chữ số của nó.

##### Event

`IdempotencyEvents.events$` phát ra mọi event, và mỗi event cũng được publish trên một diagnostics channel. Mọi payload đều có `type`, `context` (`'http'`, `'graphql'` hoặc `'rpc'`), `handler` (chẳng hạn `OrdersController.pay`), `key` và, nếu có, `scope`.

| Type | Channel | Type của payload | Các field khác | Khi nào |
| --- | --- | --- | --- | --- |
| `replayed` | `nestjs:idempotency:replayed` | `IdempotencyReplayedEvent` | `status` | Một lần retry nhận kết quả đã lưu, hoặc một event trùng lặp bị bỏ qua |
| `rejected` | `nestjs:idempotency:rejected` | `IdempotencyRejectedEvent` | `code`, `status` | Một lời gọi bị từ chối trước khi handler của nó chạy. Không có `key` với `IDEMPOTENCY_KEY_REQUIRED` và `IDEMPOTENCY_KEY_INVALID`. |
| `lock-lost` | `nestjs:idempotency:lock-lost` | `IdempotencyLockLostEvent` | `phase` (`'extend'`, `'complete'` hoặc `'release'`) | Kết quả của lần thử không có trong store, nên một lần retry có thể chạy lại handler |

`IdempotencyEvent` là union của ba type payload.

##### Lỗi

Các lần từ chối mang một trong các code sau, có type là `IdempotencyErrorCode`. Qua HTTP, code nằm trong body của response. Trong GraphQL, nó nằm trong `extensions` của lỗi field, kèm `httpStatus` và, với 409, `retryAfter`. Trên microservice, payload của `RpcException` có `status`, `code`, `statusCode`, `message` và, với 409, `retryAfter`.

| Code | Status | Message | Nguyên nhân |
| --- | --- | --- | --- |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | An idempotency key is required for this operation. | Không có key, khi `required: true` |
| `IDEMPOTENCY_KEY_INVALID` | 400 | The idempotency key must be 1 to 255 printable ASCII characters. | Key quá dài, có ký tự khác, hoặc không phải chuỗi hay số |
| `IDEMPOTENCY_KEY_IN_USE` | 409, kèm `Retry-After` | A request with this idempotency key is still being processed. | Lời gọi đầu tiên với key này vẫn đang chạy |
| `IDEMPOTENCY_KEY_REUSED` | 422 | This idempotency key was already used for a different request. | Cùng key nhưng fingerprint khác |
| `IDEMPOTENCY_RECORD_UNREADABLE` | 500 | The stored result for this idempotency key could not be read. | Record đã lưu không giải mã được, chẳng hạn vì khóa của nó đã bị gỡ |
