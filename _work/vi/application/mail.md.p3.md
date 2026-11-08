#### Tham khảo

##### Tùy chọn module

`MailModule.forRoot()` nhận các tùy chọn này, và factory của `forRootAsync()` trả về chúng. Khi dùng `useClass` hoặc `useExisting` thay cho `useFactory`, class đó implement `MailOptionsFactory`, với `createMailOptions()` trả về các tùy chọn. `transport`, `templates`, `imports` và `isGlobal` cũng đặt cạnh `useFactory`, `useClass` hoặc `useExisting` trong `forRootAsync()`. Các tùy chọn đã resolve được cung cấp dưới token `MAIL_MODULE_OPTIONS`.

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `transport` | instance hoặc class `MailTransport` | không có (bắt buộc) | Cách mail rời khỏi ứng dụng. Class sẽ được Nest khởi tạo, nên nó có thể inject cấu hình. Xem [Gửi trên production](/application/mail#send-in-production). |
| `templates` | instance hoặc class `MailTemplateEngine` | không có | Render các mail có chỉ định `template`: `FileTemplateEngine`, hoặc [engine của riêng bạn](/application/mail#use-another-template-engine). Class sẽ được Nest khởi tạo. Không có tùy chọn này, một mail có template sẽ thất bại với `MailTemplateError`. |
| `from` | địa chỉ | không có | Người gửi mặc định. Một message không có người gửi sẽ thất bại với `MailMessageError`. |
| `replyTo` | địa chỉ hoặc mảng | không có | Reply-To mặc định. |
| `headers` | `Record<string, string>` | không có | Được thêm vào mọi message. Header riêng của message sẽ được ưu tiên. |
| `retry` | số, `false` hoặc tùy chọn retry | 3 lần thử | Số lần thử cho mỗi lần gửi, với backoff bắt đầu từ `1s` và nhân đôi tới `30s`, full jitter. `false` chỉ thử một lần. Xem [Gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits). |
| `imports` | module | không có | Các module có export mà class transport hoặc template engine inject. |
| `isGlobal` | `boolean` | `true` | Đăng ký `Mailer`, `MailEvents`, `MailTransport` và `MailTemplateEngine` ở cấp global. |

Các tùy chọn retry gồm `attempts` (tổng số lần, tính cả lần đầu), `backoff` (một object có `delay`, `factor`, `maxDelay` và `jitter`, hoặc một hàm theo số lần thử) và `retryIf` (chỉ có thể thu hẹp những lỗi tạm thời nào được retry). Khi một HTTP provider trả lời kèm header `Retry-After`, thường là với lỗi 429 hoặc 503, lỗi sẽ giữ nó trong `retryAfterMs`, và mailer chờ ít nhất khoảng đó trước lần thử tiếp theo, tối đa là `maxDelay` (`30s` khi dùng hàm backoff). `signal` vẫn kết thúc được việc chờ. Reply của SMTP không có `Retry-After`, và một outbox handler với `retry: false` sẽ để việc chờ cho backoff của outbox.

##### Template engine

`FileTemplateEngine` nhận:

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `dir` | `string` | không có (bắt buộc) | Thư mục chứa template, với partial nằm trong thư mục con `partials/`. Đường dẫn tương đối được resolve theo thư mục làm việc. |
| `layout` | `string` | không có | Một template bọc HTML của mọi mail, đặt nó vào bằng ngoặc nhọn ba quanh `body`. Phiên bản `.txt`, nếu có, sẽ bọc phần text. |
| `cache` | `boolean` | `true` | Giữ các template đã compile, và danh sách file nào tồn tại, trong bộ nhớ. `false` sẽ đọc file cho mỗi mail, để thấy được thay đổi khi đang phát triển. |

`template: 'order-confirmation'` với locale `pt-BR` sẽ render file đầu tiên tồn tại trong số `order-confirmation.pt-BR.html`, `order-confirmation.pt.html` và `order-confirmation.html`, và file đầu tiên cùng tên với đuôi `.txt` làm phần text, nếu có. Tên template gồm chữ cái, chữ số, `-` và `_`, nằm trong các thư mục phân cách bằng `/`. Các tên khác, và các locale không phải language tag, sẽ thất bại với `MailTemplateError`, nên không cái nào có thể trỏ tới file nằm ngoài `dir`.

##### Cú pháp template

Cú pháp là một tập con của Handlebars:

<table>
  <tr>
    <th>Cú pháp</th>
    <th>Render ra</th>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }} customer.name {{ '}' }}{{ '}' }}</code></td>
    <td>Giá trị, đã escape HTML. Đường dẫn dùng dấu chấm, và <code>items.0</code> là phần tử đầu tiên của mảng. Giá trị bị thiếu sẽ render ra rỗng. Trong template <code>.txt</code>, giá trị được giữ nguyên.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}{{ '{' }} body {{ '}' }}{{ '}' }}{{ '}' }}</code></td>
    <td>Giá trị nguyên vẹn, dành cho HTML do chính bạn tạo ra. HTML tạo bằng tag <code>html</code> cũng được chèn nguyên vẹn khi nằm giữa ngoặc nhọn đôi.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#if paid{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}else{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/if{{ '}' }}{{ '}' }}</code></td>
    <td>Phần đầu tiên khi giá trị là truthy, ngược lại là phần <code>else</code> (tùy chọn). <code>false</code>, <code>0</code>, chuỗi rỗng, danh sách rỗng và giá trị bị thiếu đều là falsy. <code>{{ '{' }}{{ '{' }}else if pending{{ '}' }}{{ '}' }}</code> nối thêm một điều kiện khác.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#unless paid{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/unless{{ '}' }}{{ '}' }}</code></td>
    <td>Ngược lại với <code>#if</code>, với phần <code>else</code> tùy chọn.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#each items{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}else{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/each{{ '}' }}{{ '}' }}</code></td>
    <td>Phần đầu tiên lặp lại một lần cho mỗi phần tử của danh sách, hoặc mỗi giá trị của object; phần <code>else</code> dành cho danh sách rỗng hoặc bị thiếu.</td>
  </tr>
  <tr>
    <td><code>this, &#64;index, &#64;first, &#64;last, &#64;key</code></td>
    <td>Bên trong <code>#each</code>: phần tử hiện tại, vị trí của nó tính từ 0, nó có phải phần tử đầu tiên hay cuối cùng không, và key của object. Một tên mà phần tử không có sẽ được tra trong các context bên ngoài.</td>
  </tr>
  <tr>
    <td><code>../number, &#64;root.shop</code></td>
    <td>Context bên ngoài <code>#each</code> hiện tại, và context của template.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}> signature{{ '}' }}{{ '}' }}</code></td>
    <td>Partial <code>partials/signature.html</code> (<code>.txt</code> trong template text), theo locale của mail, với context tại chỗ nó được chèn.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}! note {{ '}' }}{{ '}' }}, {{ '{' }}{{ '{' }}!-- note --{{ '}' }}{{ '}' }}</code></td>
    <td>Comment, bị loại khỏi output. Dạng thứ hai có thể chứa ngoặc nhọn đôi.</td>
  </tr>
  <tr>
    <td><code>\{{ '{' }}{{ '{' }}</code></td>
    <td>Ngoặc nhọn đôi theo nghĩa đen.</td>
  </tr>
</table>

Không có helper và không có biểu thức. Giá trị được đọc từ các thuộc tính riêng của context, không bao giờ từ prototype, và hàm không được gọi. Bất cứ thứ gì khác nằm giữa ngoặc nhọn đôi, một block không bao giờ được đóng, và một giá trị trong ngoặc nhọn đôi nằm bên trong thẻ nhưng ngoài giá trị thuộc tính có dấu nháy, đều thất bại với `MailTemplateError`, lỗi này có `file`, `line` và `column`.

##### Tùy chọn gửi

`mailer.send(MailClass, options)` và `mailer.send(message)` nhận:

| Tùy chọn | Mô tả |
| --- | --- |
| `to`, `cc`, `bcc` | Một địa chỉ hoặc một mảng. Một địa chỉ là chuỗi chứa đúng một địa chỉ, hoặc một object có `name` và `address`. `bcc` chỉ đi vào SMTP envelope. |
| `data` | Dữ liệu của mail class, có type lấy từ `render()` của nó. |
| `locale` | Được truyền vào `render()` trong render context, và vào template engine, engine sẽ chọn template theo nó. Xem [Gửi bằng ngôn ngữ của khách hàng](/application/mail#send-it-in-the-customers-language). |
| `from`, `replyTo` | Ghi đè giá trị mặc định của module. |
| `subject`, `html`, `text` | Nội dung, dành cho message viết inline. `text` được suy ra từ `html` khi bỏ trống. |
| `template`, `context` | Template dùng để render body, và các giá trị nó đọc, thay cho `html` và `text`. `render()` của mail class trả về chúng theo cùng cách. |
| `attachments` | Mỗi file có `filename`, `content` (một `Buffer`, chuỗi hoặc stream) hoặc một `path` local, cùng `contentType` và `cid` tùy chọn. Xem [Đính kèm hóa đơn và preview mail](/application/mail#attach-the-invoice-and-preview-the-mail). |
| `headers` | Các header tùy chỉnh, như `List-Unsubscribe`. |
| `retry` | Ghi đè `retry` của module cho lần gửi này. |
| `signal` | Một `AbortSignal` dừng việc gửi và mọi khoảng chờ giữa các lần thử. |
| `idempotencyKey` | Xác định mail xuyên suốt các lần gửi lại. `Message-ID` được suy ra từ nó. |

`mailer.render(MailClass, options)` và `mailer.render(message)` nhận các tùy chọn tương tự nhưng không có các tùy chọn gửi, và resolve ra `MailMessage`, object này ghi lại `template` và `locale` của nó. `send()` resolve ra `messageId`, `providerMessageId` (khi provider có), `accepted` (các người nhận trong envelope đã được chấp nhận), `response` (reply SMTP cuối cùng) và `attempts`.

##### Transport

| Transport | Tùy chọn | Idempotency key |
| --- | --- | --- |
| `SmtpTransport` | `url` hoặc `host`, `port`, `secure`, `startTls` (`required`, `opportunistic` hoặc `never`; mặc định `required`, `opportunistic` với localhost), `auth` (`user` kèm `pass` hoặc `accessToken`), `authMethod` (`PLAIN`, `LOGIN` hoặc `XOAUTH2`), `name`, `tls`, `pool`, `timeouts`, `dkim` (`domainName`, `keySelector`, `privateKey`, `headers`) | chỉ có `Message-ID` được suy ra |
| `ResendTransport` | `apiKey`, `baseUrl`, `timeout`, `fetch` | `Idempotency-Key`, 24 giờ |
| `PostmarkTransport` | `serverToken`, `messageStream` (mặc định `outbound`), `baseUrl`, `timeout`, `fetch` | không có |
| `SendGridTransport` | `apiKey`, `baseUrl`, `timeout`, `fetch` | không có |
| `SesTransport` | `region`, `credentials`, `configurationSetName`, `endpoint`, `timeout`, `fetch` | không có |
| `FileMailTransport` | `directory`, `log` | chỉ dành cho development |
| `LogMailTransport` | `body`, `logger` | chỉ dành cho development |
| `InMemoryMailTransport` | không có | chỉ dành cho test, xem [Test](/application/mail#testing) |

`InMemoryMailTransport.mails` liệt kê mọi mail đã nhận, cũ nhất trước, dưới dạng `SentMail`, cũng là thứ mà `filter()`, `find()` và `assertSent()` trả về. Một `SentMail` có `messageId`, `from`, `to`, `cc`, `bcc`, `subject`, `html`, `text`, `attachments`, `headers`, `mail` (mail class), `template` và `locale` của message, cộng thêm `sentAt` (thời điểm transport nhận được), `raw` (mã nguồn MIME), `links` (mọi link, từ HTML, rồi đến các link chỉ có trong phần text), `link()`, `attachment()` và `message`, chính là `MailMessage`. `clear()` xóa sạch tất cả.

Với `pool: true`, `SmtpTransport` giữ tối đa 5 kết nối, gửi tối đa 100 message trên mỗi kết nối, và đóng một kết nối sau 30 giây không hoạt động; truyền một object có `maxConnections`, `maxMessages` và `idleTimeout` làm `pool` sẽ thay đổi các giới hạn đó. Timeout mặc định của nó là `30s` để kết nối, `30s` cho lời chào, `1m` cho mỗi lệnh và `5m` cho phần dữ liệu. HTTP provider timeout sau `30s` cho mỗi request.

##### Event

`MailEvents.events$` phát ra một event cho mỗi lần gửi, sau các lần retry của nó. Mỗi event cũng được publish trên một channel `node:diagnostics_channel`.

| Loại event | Channel | Khi nào | Payload |
| --- | --- | --- | --- |
| `sent` | `nestjs:mail:sent` | Transport đã chấp nhận message. | `messageId`, `mail`, `recipients`, `subject`, `transport`, `attempts`, `durationMs`, `providerMessageId` |
| `failed` | `nestjs:mail:failed` | Việc gửi thất bại sau các lần retry, hoặc `signal` của nó abort trước lần thử đầu tiên (`attempts` là 0). | Các trường tương tự nhưng không có `providerMessageId`, cộng thêm `error` và `permanent` |

Một message không qua được validation sẽ throw trước khi có event nào.

##### Lỗi

Mọi lỗi đều kế thừa `MailError`, class này có `permanent` (gửi lại cùng message có chắc chắn không thành công hay không) và `code` (mã reply SMTP hoặc HTTP status của provider). Mailer chỉ retry những lỗi không phải vĩnh viễn. Xem [Gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits).

| Lỗi | Khi nào | Vĩnh viễn |
| --- | --- | --- |
| `MailMessageError` | Message không hợp lệ, trước khi gửi bất cứ thứ gì. `field` nêu tên trường, `status` là 400. | Có |
| `MailConnectionError` | DNS, kết nối bị từ chối hoặc reset, TLS hoặc chứng chỉ. `cause` chứa lỗi socket. | Không, trừ các vấn đề cấu hình như server không hỗ trợ STARTTLS khi nó là bắt buộc |
| `MailTimeoutError` | Một giai đoạn chạy quá timeout của nó. Có `phase` và `timeoutMs`. | Không |
| `MailSmtpError` | Một reply lỗi của SMTP. Có `code`, `enhancedCode`, `command` và `response`. | Với reply 5xx |
| `MailRecipientsRejectedError` | Server từ chối một hoặc nhiều người nhận, và không có gì được gửi. `rejected` liệt kê họ. Kế thừa `MailSmtpError`. | Khi có bất kỳ lời từ chối nào là 5xx |
| `MailTemplateError` | Một template bị thiếu hoặc không compile được, hoặc một mail chỉ định template mà không có template engine. Có `template`, và `file`, `line`, `column` khi lỗi nằm trong một file. | Có |
| `MailProviderError` | Một HTTP provider từ chối request. Có `code` (HTTP status), `provider`, `providerCode`, và `retryAfterMs` khi response có `Retry-After` hợp lệ. | Với 4xx ngoại trừ 408, 409 và 429 |
