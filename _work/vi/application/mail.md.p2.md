#### Gửi bằng ngôn ngữ của khách hàng

Cửa hàng bán hàng bằng tiếng Anh và tiếng Ba Lan. Khách hàng chọn ngôn ngữ khi đăng ký, và bảng `customers` lưu nó trong cột `locale`: `en` hoặc `pl`. Mailer chuyển locale của mỗi lần gửi cho template engine, engine sẽ chọn template tương ứng.

Hãy dịch template: thêm `order-confirmation.pl.html` cạnh template tiếng Anh.

[[CODE:25]]

Với locale `pl`, `FileTemplateEngine` render `order-confirmation.pl.html`, còn với mọi locale khác, hoặc không có locale, nó render `order-confirmation.html`. Một locale có vùng sẽ thử chính nó trước, rồi đến ngôn ngữ của nó: với `pt-BR`, engine tìm `order-confirmation.pt-BR.html`, rồi `order-confirmation.pt.html`. Partial và layout cũng được tìm theo cùng cách, nên layout vẫn dùng chung, còn chữ ký tiếng Ba Lan là một partial riêng:

[[CODE:26]]

Nội dung của một mail là văn xuôi, nên nó được dịch theo từng file: người dịch thấy toàn bộ mail, và viết câu tiếng Ba Lan thay vì điền từng key một. Những gì mail class tính toán vẫn phụ thuộc vào locale: subject, tên file hóa đơn và giá tiền. Chúng lấy từ `@nestjs/i18n`, được trình bày chi tiết trong [chương đa ngôn ngữ](/application/i18n). Hãy thêm một catalog cho mail, mỗi ngôn ngữ một catalog:

[[CODE:27]]

[[CODE:28]]

Đăng ký cấu trúc của các catalog, để key được kiểm tra lúc compile, và đăng ký `I18nModule` cạnh `MailModule`:

[[CODE:29]]

[[CODE:30]]

Hãy thêm cả các catalog vào asset trong `nest-cli.json` (`i18n/**/*.json`), như chương đa ngôn ngữ đã hướng dẫn.

Mail class là một provider, nên nó inject `I18nService` cạnh bộ render hóa đơn. `render()` nhận thêm tham số thứ hai, render context, trong đó `locale` là locale truyền vào `send()`, cũng là locale mà mailer chuyển cho template engine. `to` của nó chứa danh sách người nhận đã parse, và rỗng khi preview được render mà không có người nhận:

[[CODE:31]]

Context không thay đổi: cùng các giá trị đó điền vào template nào cũng được. `Key` là `keyof Translations['mail']['orderConfirmation']`, nên một key viết sai là lỗi compile. Giá tiền được định dạng theo locale: `$25.98` trong tiếng Anh, `25,98 USD` trong tiếng Ba Lan. Tên file hóa đơn lấy từ catalog: `invoice-1001.pdf` hoặc `faktura-1001.pdf`.

> warning **Warning** Hãy truyền locale một cách tường minh. `I18nService` quay về locale của request hiện tại, mà mail thường được gửi bên ngoài request của người nhận: từ một outbox handler, như ở đây, hoặc từ request của người khác, như một admin. Locale của request đó là locale sai.

Outbox handler truyền locale của khách hàng khi gửi:

[[CODE:32]]

Một subject hay tên người nhận tiếng Ba Lan không thể đưa nguyên vẹn vào header của mail: header chỉ dùng ASCII. Mailer encode text không phải ASCII trong header thành encoded-word theo RFC 2047, như `=?UTF-8?Q?Twoje_zam=C3=B3wienie_=231001?=`, và body theo quoted-printable, để mọi server đều chuyển message nguyên vẹn và mail client hiển thị `Twoje zamówienie #1001`.

Preview lấy ngôn ngữ từ query string, nên có thể kiểm tra cả hai phiên bản trên trình duyệt:

[[CODE:33]]

#### Dùng template engine khác

`FileTemplateEngine` implement `MailTemplateEngine`, một abstract class chỉ có một method: `render()` nhận tên template, context và locale, rồi trả về HTML, hoặc một object có `html` và `text`, hoặc một promise của một trong hai. Hãy kế thừa nó để render bằng Handlebars, EJS hay bất cứ thứ gì khác. Một engine cho template Handlebars trong các file `.hbs`:

[[CODE:34]]

Truyền nó làm `templates` thay cho `FileTemplateEngine`: một instance, hoặc chính class, để Nest khởi tạo, nhờ đó nó có thể inject cấu hình hoặc các provider khác. Giống như với transport, class được đặt ở cấp cao nhất của `forRootAsync()`, cạnh `useFactory`, còn factory trả về instance.

Mailer gửi HTML đúng như engine trả về, nên escape là việc của engine: Handlebars escape các giá trị trong ngoặc nhọn đôi, giống như `FileTemplateEngine`. `compat: true` cho các tên bên trong `#each` quay về tra trong context bên ngoài, nên các template trong bài hướng dẫn này render được bằng Handlebars mà không cần sửa. Handlebars không biết gì về thư mục `partials/` và layout: hãy đăng ký partial bằng `Handlebars.registerPartial()`, và tự render layout bao quanh mail. Với [MJML](https://mjml.io), hãy chuyển MJML đã render bằng `mjml2html()` trước khi trả về HTML. Hãy throw `MailTemplateError` cho template bị thiếu hoặc bị hỏng: đây là lỗi vĩnh viễn, nên outbox sẽ chuyển mail vào dead-letter thay vì retry.

#### Tự viết transport

Với một provider mà package không có sẵn transport, hãy kế thừa `MailTransport`. Method `send()` của nó nhận message hoàn chỉnh và resolve khi provider đã chấp nhận message. Một transport cho Mailgun, với endpoint `messages.mime` nhận message dạng MIME, giống cách `SesTransport` gửi tới SES:

[[CODE:35]]

Truyền một instance làm `transport`, giống như với các transport có sẵn. `send(message, options)` nhận:

- **`message`.** Một `MailMessage` đã được validate và đóng băng (frozen): `from`, `to`, `cc`, `bcc`, `replyTo`, `subject`, `html`, `text`, `attachments`, `headers` và `messageId`. `envelope` chứa SMTP envelope, với mỗi người nhận xuất hiện một lần, kể cả Bcc, còn `toMime()` trả về message dạng MIME, không kèm header Bcc. Đây là cùng một object ở mọi lần thử.
- **`signal`.** Abort khi bên gọi hủy việc gửi, như outbox relay khi một handler chạy quá timeout. Hãy dừng request, và reject với `signal.reason`; mailer không retry một lần abort.
- **`idempotencyKey`.** Key của bên gọi, giống nhau ở mọi lần thử và mọi lần gửi lại. Hãy gửi nó tới provider có khả năng loại bỏ request trùng, như `ResendTransport` làm; `Message-ID` vốn đã được suy ra từ nó.
- **`attempt`.** 1 cho lần thử đầu tiên, 2 cho lần retry đầu tiên.

Nó resolve ra `accepted`, các người nhận trong envelope mà provider đã nhận (tất cả nếu bỏ trống), `providerMessageId` và `response`, đây cũng là thứ mà `send()` của mailer resolve ra.

Những gì nó throw sẽ quyết định mailer có retry hay không. Hãy throw một `MailError` có `permanent` cho biết gửi lại cùng message có thể thành công hay không: `MailProviderError` cho lời từ chối của HTTP API, là lỗi vĩnh viễn với status 4xx ngoại trừ 408, 409 và 429 (trừ khi bạn tự truyền `permanent`), `MailConnectionError` và `MailTimeoutError` cho request thất bại hoặc chậm. Mọi lỗi khác đều được tính là tạm thời, trừ khi nó có `permanent: true` hoặc `status` 4xx, nên một lỗi mạng từ `fetch` sẽ được retry. Một lỗi có `retryAfterMs` sẽ khiến mailer chờ ít nhất khoảng đó trước lần thử tiếp theo, tối đa là `maxDelay`.

Một transport giữ kết nối hoặc client thì implement `close()`, method này chạy khi ứng dụng tắt, sau khi các lần gửi đang diễn ra đã xong.

#### Thử ngay

Áp dụng các migration, chúng cũng thêm hai khách hàng và bốn sản phẩm:

[[CODE:36]]

Khởi động ứng dụng với các giá trị mặc định: file transport, và relay đang chạy. Đặt một đơn hàng cho Ada:

[[CODE:37]]

Response trả về trước khi có mail nào được gửi. Một lát sau, handler của relay render mail và file transport ghi nó ra:

[[CODE:38]]

File này chính là message đúng như SMTP sẽ truyền đi. Phần header và phần text của nó:

[[CODE:39]]

Vài điều đáng chú ý:

- `Message-ID` được suy ra từ id của outbox message, không phải ngẫu nhiên. Một lần gửi lại sẽ mang cùng id.
- Phần text được suy ra từ HTML, với link được viết ra đầy đủ.
- Body ở dạng quoted-printable, giúp mọi dòng đủ ngắn cho bất kỳ mail server nào: dấu `=` ở cuối dòng đầu tiên của link nối nó với dòng tiếp theo.

Tiếp theo là HTML, logo và hóa đơn:

[[CODE:40]]

Mở file trong một mail client để xem mail đã render. Để làm việc với template, hãy mở preview trên trình duyệt thay vào đó. Response là HTML của mail, template nằm trong layout, với logo được chèn inline dưới dạng URL `data:` (đã rút gọn ở đây):

[[CODE:41]]

[[CODE:42]]

Tiếp theo, đặt mua một sản phẩm không tồn tại:

[[CODE:43]]

Transaction bị rollback, kéo theo message `order.placed`, và không có mail nào được ghi.

Cuối cùng, hãy xem [ngôn ngữ của khách hàng](/application/mail#send-it-in-the-customers-language) hoạt động. Đặt một đơn hàng cho Zofia, người đã chọn tiếng Ba Lan khi đăng ký:

[[CODE:44]]

[[CODE:45]]

Body lấy từ `order-confirmation.pl.html`. Subject tiếng Ba Lan và tên của Zofia được ghi vào file dưới dạng encoded-word, và hóa đơn của cô ấy là `faktura-1002.pdf`:

[[CODE:46]]

#### Test

Thay transport bằng `InMemoryMailTransport`. Nó giữ lại mọi mail nhận được, và có các helper để tìm và đọc mail:

[[CODE:47]]

- **Mọi thứ đều thật, trừ mạng.** Mail class render template của nó, với catalog và provider hóa đơn, outbox và inbox của nó đều chạy, và message được dựng hoàn chỉnh, kể cả header và file đính kèm. Chỉ có việc gửi đi là bị thay thế.
- **Database là PostgreSQL, chạy ngay trong process.** PGlite (`@electric-sql/pglite`, một dev dependency) chạy các migration thật của bạn, và bài test ghi đè database mà `DrizzleModule` đăng ký (token của nó lấy từ `getDrizzleToken()`) bằng PGlite, nên các repository và outbox store đều dùng nó. Không cần khởi động server nào, và mỗi file test có một database mới.
- **`assertSent()`** trả về mail gần nhất khớp điều kiện, theo người nhận (`to` khớp với to, cc và bcc), `subject`, mail class hoặc `template`, hoặc một predicate. Khi không có gì khớp, nó throw một lỗi liệt kê những gì đã được gửi. `assertNotSent()`, `filter()`, `find()` và `mails` lo phần còn lại. Các helper throw lỗi thông thường, nên chúng chạy được với mọi test runner.
- **`link()`** trả về link đầu tiên trong mail có chứa một chuỗi hoặc khớp một biểu thức chính quy, dưới dạng `URL`. Với tính năng reset mật khẩu hay magic link, đó là toàn bộ bài test: gửi mail, rồi gọi `mail.link('/reset-password').searchParams.get('token')` và đi theo link. Các entity được decode, nên `&amp;` mà việc escape ghi vào query string sẽ trở lại thành `&`.
- **`failNext()`** khiến lần gửi tiếp theo throw, ở đây là một lỗi SMTP vĩnh viễn, để test nhánh xử lý lỗi.
- **`raw`** là message dạng MIME, còn `mailer.render()` render riêng một mail class hoặc một template, dùng cho unit test của template.

#### Checklist cho production

- Cấu hình SPF, DKIM và DMARC cho domain gửi mail. Các HTTP provider ký bằng DKIM khi domain đã được xác minh với họ; với SMTP, hãy ký bằng tùy chọn `dkim` hoặc ký ở relay.
- Giữ STARTTLS là bắt buộc, và bật xác minh chứng chỉ. Với relay dùng CA riêng, hãy truyền `tls.ca` thay vì tắt xác minh.
- Giữ thông tin đăng nhập trong biến môi trường hoặc kho secret. Transport giữ chúng trong các trường private, và thông báo lỗi không bao giờ chứa chúng.
- Gửi mail giao dịch sau khi commit, qua outbox, với `retry: false` trong handler và chính sách retry của outbox được điều chỉnh theo khoảng thời gian provider của bạn có thể bị sập.
- Truyền `idempotencyKey` cho mọi mail gửi từ một handler có thể chạy hai lần.
- Biến các lỗi mail vĩnh viễn thành dead letter, và đặt cảnh báo cho các outbox event `dead-lettered`. Một địa chỉ bị từ chối thường là do gõ sai lúc đăng ký, hoặc hộp thư không còn tồn tại.
- Theo dõi `MailEvents`, hoặc các diagnostics channel `nestjs:mail:sent` và `nestjs:mail:failed`, để phát hiện gửi thất bại và gửi chậm.
- Trên production, hãy gửi qua `SmtpTransport` hoặc transport của một HTTP provider. `FileMailTransport` ghi ra ổ đĩa local, thứ mà container sẽ mất khi khởi động lại hoặc bị thay thế, còn `LogMailTransport` chỉ ghi log: cả hai dành cho development, và `InMemoryMailTransport` dành cho test. Module sẽ cảnh báo lúc khởi động nếu một trong số chúng chạy với `NODE_ENV=production`.
- Giữ message của outbox trong database của ứng dụng, qua `PostgresOutboxStore` hoặc một store đã đăng ký khác, để mail trong hàng đợi được commit cùng đơn hàng và sống sót qua việc khởi động lại. Không có store, outbox sẽ từ chối khởi động với `NODE_ENV=production`, và store cũng vậy khi các migration của nó chưa được áp dụng: hãy áp dụng chúng khi deploy, như [bài hướng dẫn outbox](/reliability/outbox#keep-messages-in-your-database) chỉ dẫn.
- Ship các template sang `dist` bằng asset của CLI, và giữ cache template bật trên production, đây là giá trị mặc định: `cache: false` sẽ đọc lại file cho mỗi mail.
- Đừng đăng ký các route chỉ dành cho development, như preview, trên production.
- Dùng `app.enableShutdownHooks()`, để một đợt deploy chờ các mail đang gửi xong và đóng các kết nối SMTP.
