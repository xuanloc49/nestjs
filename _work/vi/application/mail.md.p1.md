### Mail

`@nestjs/mail` gửi email từ một ứng dụng Nest: các mail class được render từ template HTML có escape, gửi qua SMTP hoặc một email API, và đọc lại được trong test.

Khi một khách hàng đặt hàng ở cửa hàng online bán thức ăn và đồ dùng cho mèo, họ mong nhận được email xác nhận trong vòng một phút: danh sách sản phẩm, tổng tiền, link tới đơn hàng, và hóa đơn dạng PDF. Gửi email đó cho tử tế cần nhiều hơn một lời gọi tới library SMTP:

- **HTML phải an toàn.** Tên sản phẩm hay tên khách hàng sẽ nằm trong markup. Nếu không escape, một cái tên như `<script>` hay một dấu `&` lạc chỗ sẽ làm vỡ layout, hoặc tệ hơn.
- **Mail phải sống sót qua sự cố.** Mail server có thể greylist, giới hạn tốc độ và sập. Một lần gửi thất bại ngay trong request hoặc sẽ làm thất bại một đơn hàng đã commit, hoặc làm mất email.
- **Test phải thấy được những gì đã gửi.** Một bài test cho "khách hàng nhận được xác nhận kèm link tới đơn hàng" cần mail đã render và các link trong đó, chứ không phải một lời gọi method bị mock.

`@nestjs/mail` đáp ứng những yêu cầu này. Mail class là các provider có thể inject, render subject và body từ dữ liệu có type, nên chúng có thể inject các provider khác của bạn, như repository hay bộ render PDF. Body lấy từ một file template HTML, được render bởi một engine nhỏ có sẵn (escape mọi giá trị nó chèn vào), hoặc bởi Handlebars hay bất kỳ engine nào bạn cắm vào. Transport lo việc gửi kết quả đi: SMTP, viết trên `node:net` và `node:tls`, và Resend, Postmark, SendGrid, Amazon SES qua HTTP API của chúng. Trong test, transport được thay bằng một transport trong bộ nhớ và đọc lại các mail mà nó nhận được. Package không có dependency nào ngoài chính Nest.

Trong bài hướng dẫn này, bạn sẽ thêm email xác nhận đơn hàng vào API đơn hàng của cửa hàng:

- Ở môi trường development, mọi mail được ghi ra file `.eml` thay vì gửi đi.
- Xác nhận đơn hàng là một mail class render một template HTML, nằm trong một layout mà mọi mail dùng chung, đính kèm hóa đơn và logo dạng inline.
- Một route preview hiển thị mail trên trình duyệt mà không gửi đi.
- Mail được gửi sau khi đơn hàng commit, qua outbox, có retry và dead letter.
- Production gửi qua SMTP hoặc Resend, chọn bằng một biến môi trường.

#### Cài đặt

Để bắt đầu, cài dependency cần thiết:

[[CODE:1]]

#### Đăng ký mail module

Đăng ký `MailModule` trong root module, cạnh `DrizzleModule`. Bài hướng dẫn mail cần database cho khách hàng và đơn hàng của họ, cũng như cho các bảng của outbox, nơi mail được [gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits). Ở môi trường development, `FileMailTransport` ghi mỗi mail ra một file trong `var/mail` thay vì gửi đi, còn `FileTemplateEngine` render body của mail từ các file HTML trong `mail/templates`. Các feature module mà nó import được xây dựng trong các phần tiếp theo:

[[CODE:2]]

- `transport`: cách mail rời khỏi ứng dụng. Mọi transport đều kế thừa abstract class `MailTransport`, class này cũng chính là injection token của nó, nên trong test bạn thay nó bằng `overrideProvider(MailTransport)`. `FileMailTransport` dành cho development: mở các file `.eml` trong bất kỳ mail client nào để thấy chính xác những gì sẽ được gửi. Nó ghi ra ổ đĩa local và không gửi tới ai cả, nên [trên production](/application/mail#send-in-production) ứng dụng chuyển sang SMTP hoặc Resend.
- `templates`: render các mail có chỉ định template. `FileTemplateEngine` đọc các file `.html` từ `dir`, và bọc mọi mail trong template `layout`, tức `mail/templates/layout.html`. Một `dir` tương đối được resolve theo thư mục làm việc; nếu tạo từ `import.meta.dirname`, nó trỏ tới chỗ cạnh file `app.module.js` đã compile, bất kể ứng dụng được khởi động từ đâu. Template đã compile được cache lại. Khi tắt `cache`, như ở đây với môi trường không phải production, mỗi mail sẽ đọc lại file, nên template vừa sửa sẽ xuất hiện ngay ở mail tiếp theo mà không cần khởi động lại.
- `from`: người gửi mặc định. Mỗi message có thể ghi đè nó.

Trình biên dịch TypeScript không copy file HTML sang `dist`. Hãy thêm các template vào [asset](/cli/monorepo#assets) trong `nest-cli.json`, để chúng nằm ở `dist/mail/templates`, cạnh file `app.module.js` đã compile:

[[CODE:3]]

Với `watchAssets`, `nest start --watch` sẽ copy template sang `dist` mỗi khi bạn lưu nó.

> info **Hint** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để việc thiếu `DATABASE_URL` hay `SMTP_URL` làm ứng dụng dừng ngay lúc khởi động, và đọc giá trị từ `ConfigService` trong các factory.

`MailModule` là global và cung cấp `Mailer` để gửi mail, cùng `MailEvents` để báo cáo những gì đã gửi và những gì thất bại. Thiếu `transport` hoặc `from` không hợp lệ sẽ làm ứng dụng dừng lúc khởi động, kèm thông báo nêu tên tùy chọn.

#### Viết mail xác nhận đơn hàng

Body của mail là một template HTML. Giá trị được đặt giữa cặp ngoặc nhọn đôi, và một block như `#each` lặp lại phần template của nó cho mỗi phần tử trong danh sách:

[[CODE:4]]

Mọi mail đều được bọc trong layout. Layout đặt mail đã render vào bằng ngoặc nhọn ba quanh `body`, và chèn chữ ký, một partial nằm trong `mail/templates/partials/signature.html`:

[[CODE:5]]

[[CODE:6]]

Một mail class implement `Mailable<TData>`. Method `render()` của nó nhận dữ liệu và trả về subject, tên template và context của template, tức các giá trị mà template đọc:

[[CODE:7]]

Template không chứa logic. Nó có giá trị, các block `#if`, `#unless` và `#each`, partial và comment, nhưng không có helper hay biểu thức: những gì cần code, như định dạng giá hay tạo link, được làm trong mail class, bằng TypeScript, nơi chúng có type và được test. Cú pháp là một tập con của Handlebars (xem [Cú pháp template](/application/mail#template-syntax)), nên các template chuyển được sang [engine khác](/application/mail#use-another-template-engine) mà không cần sửa.

Ngoặc nhọn đôi sẽ escape giá trị. Một sản phẩm tên `Feather wand toy <limited edition>` sẽ trở thành `Feather wand toy &lt;limited edition&gt;`, và tên khách hàng không thể chèn markup vào. Hai quy tắc khiến việc này khó mà làm sai:

- Escape bảo vệ được nội dung phần tử và giá trị thuộc tính có dấu nháy, nên đó là những chỗ duy nhất mà giá trị trong ngoặc nhọn đôi được phép đặt. Một giá trị nằm bên trong thẻ ở bất kỳ chỗ nào khác là lỗi compile: `href=` theo sau trực tiếp là giá trị, hoặc một giá trị đứng giữa các thuộc tính. Escape không bảo vệ được cả hai chỗ đó (nếu không có dấu nháy, một dấu cách trong giá trị sẽ mở ra một thuộc tính mới). Hãy đặt giá trị thuộc tính trong dấu nháy, như link ở trên.
- Ngoặc nhọn ba chèn giá trị nguyên vẹn, dành cho HTML do chính bạn tạo ra. Trong bài hướng dẫn này, chỉ `body` của layout cần đến nó.

Một giá trị bị thiếu sẽ render ra rỗng, giống như Handlebars. Bên trong `#each`, `this` là phần tử hiện tại, `@index`, `@first` và `@last` mô tả vị trí của nó, và một tên mà phần tử không có sẽ được tra trong context của template, nên một dòng có thể hiển thị giá trị từ bên ngoài danh sách. Một template không compile được sẽ làm mail thất bại với một `MailTemplateError` vĩnh viễn, lỗi này nêu tên file và vị trí:

[[CODE:8]]

Không có template dạng text. Mailer tự suy ra phần plain text từ HTML: các đoạn văn, các dòng của bảng, và link dưới dạng `View your order (https://shop.example.com/orders/…)`. Các mail client không hiển thị HTML, và bộ lọc spam, sẽ đọc phần này. Để tự viết nó, hãy thêm `order-confirmation.txt` cạnh file HTML: engine sẽ render nó làm phần text, với cùng cú pháp, không escape.

Đăng ký class làm provider, giống như mọi injectable khác:

[[CODE:9]]

Sau đó gửi nó khi có đơn hàng được đặt. `mailer.send()` nhận mail class và người nhận, còn type của `data` lấy từ `render()` của class:

[[CODE:10]]

Người nhận là một object có `name` và `address`, nên một cái tên có dấu phẩy hoặc dấu nháy vẫn là một display name duy nhất. Một chuỗi cũng dùng được, như `'Ada Lovelace <ada@example.com>'`, nhưng chuỗi phải chứa đúng một địa chỉ: một danh sách phân cách bằng dấu phẩy sẽ gây throw, nên một cái tên do người dùng gõ vào không bao giờ thêm được người nhận. Danh sách người nhận là mảng.

Đặt một đơn hàng và một file sẽ xuất hiện trong `var/mail`. Cách này chạy được, nhưng nó gửi mail từ request, sau khi commit. Phần [Gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits) giải thích vì sao như vậy là chưa đủ, và sửa lại.

**Mail viết inline.** Một mail đủ nhỏ để viết bằng TypeScript thì không cần file template. `render()` trả về `html` thay cho `template` và `context`, tạo bằng tagged template `html`:

[[CODE:11]]

`html` escape mọi giá trị bạn chèn vào, theo cùng quy tắc như template: một giá trị bên trong thẻ phải nằm trong giá trị thuộc tính có dấu nháy, nếu không sẽ throw. Các template `html` lồng nhau và mảng của chúng, như các dòng của bảng, được chèn nguyên vẹn, còn `unsafeHtml()` chèn HTML do chính bạn tạo ra; cái tên đã là lời cảnh báo. `mailer.send()` cũng nhận `html`, cho message gửi không cần mail class.

#### Đính kèm hóa đơn và preview mail

Hóa đơn là một file PDF, được render bởi một provider nhỏ. Nó tự viết PDF bằng tay với một font có sẵn, để ví dụ không cần dependency. Một ứng dụng thực tế sẽ dùng library PDF hoặc một dịch vụ render ở đây. Mail chỉ cần các byte:

[[CODE:12]]

`render()` trả về file đính kèm cùng với template. Hóa đơn là một file đính kèm thông thường. Logo là một hình ảnh inline: `cid` của nó biến nó thành một phần của HTML, HTML tham chiếu tới nó bằng `cid:logo@example.com`. Logo nằm ở đầu mọi mail, nên tham chiếu được đặt trong layout:

[[CODE:13]]

Mail class đính kèm logo và hóa đơn:

[[CODE:14]]

Mọi mail render trong layout này đều phải đính kèm logo theo cùng cách, nếu không phần header sẽ hiện hình ảnh bị hỏng. Template có thêm một dòng sau link, `<p>Your invoice is attached.</p>`.

Nội dung của file đính kèm là `Buffer`, chuỗi hoặc stream, hoặc được đọc từ một `path` local khi mail được gửi. Content type lấy theo tên file, và tên file không phải ASCII sẽ được encode để mọi mail client đều hiển thị được. Mailer sắp xếp các phần theo cách mà mail client mong đợi: logo nằm cạnh HTML, nên một client hiển thị bản text sẽ không liệt kê nó như một file đính kèm.

> warning **Warning** Đừng bao giờ tạo `path` của file đính kèm từ dữ liệu người dùng nhập vào. File ở đường dẫn đó sẽ được đính kèm, bất kể nó là gì. URL bị từ chối chứ không được tải về.

Trong lúc làm template, bạn không muốn phải đặt một đơn hàng cho mỗi thay đổi. `mailer.render()` render một mail class mà không gửi đi. Một route chỉ dành cho development hiển thị kết quả trên trình duyệt. Khi tắt cache template, nó hiển thị template vừa sửa ngay ở lần refresh tiếp theo:

[[CODE:15]]

`render()` trả về `MailMessage` hoàn chỉnh: subject, HTML và phần text suy ra, các file đính kèm, và `toMime()` để lấy message thô. Ở đây người nhận là tùy chọn. `render()` cũng nhận một message viết inline, như một subject, một `template` và `context` của nó, để preview template mà không cần mail class. Chỉ đăng ký controller ở môi trường không phải production:

[[CODE:16]]

#### Gửi sau khi đơn hàng commit

Phần [Viết mail xác nhận đơn hàng](/application/mail#write-the-order-confirmation-mail) gửi mail từ request, sau khi đơn hàng commit. Có ba thứ có thể hỏng ở đó:

- **Một lần crash giữa lúc commit và lúc gửi sẽ làm mất mail.** Một đợt deploy khởi động lại process đúng lúc đó sẽ để lại một đơn hàng đã thanh toán mà không có xác nhận.
- **Mail server gặp sự cố sẽ làm thất bại một request vốn đã thành công.** Đơn hàng đã được lưu, nhưng khách hàng thấy lỗi 500 và có thể đặt hàng lại.
- **Khách hàng phải chờ mail server.** Một phiên trao đổi SMTP mất hàng trăm mili giây, và một server chậm sẽ kéo theo thời gian của request.

Đây là bài toán dual-write trong [bài hướng dẫn outbox](/reliability/outbox), và outbox (`@nestjs/outbox`, được cài và thiết lập trong bài hướng dẫn đó) giải quyết nó. Đơn hàng và một message `order.placed` được commit trong cùng một transaction, và một relay chuyển message cho một handler để gửi mail. Nếu gửi thất bại, relay sẽ retry có backoff, và chuyển những message không bao giờ thành công vào bảng dead-letter. Outbox giữ message của nó trong database PostgreSQL của ứng dụng, cạnh các đơn hàng, thông qua store của nó, `PostgresOutboxStore` từ `@nestjs/outbox/postgres`, trên database mà [`@nestjs/drizzle`](/data/drizzle) đăng ký. Store tự tạo các bảng của nó, trong một schema riêng, khi ứng dụng khởi động; phần [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database) trong bài hướng dẫn outbox trình bày về chúng, và cách áp dụng migration của chúng trên production.

Phần này trình bày transaction đơn hàng hai lần: lần đầu với Drizzle, là hướng chính của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối phần, cùng transaction đó cho ứng dụng dùng ORM là TypeORM. Hãy chọn một trong hai.

Đăng ký `OutboxModule`, và store làm provider của root module: một factory inject database Drizzle và registry `OutboxStorage`, nơi store tự đăng ký. Không có nó, outbox sẽ giữ message trong bộ nhớ, và làm mất chúng khi khởi động lại:

[[CODE:17]]

`OrdersService` thêm message thay vì gửi mail, với `tx` của Drizzle, để message được commit hoặc rollback cùng với đơn hàng:

[[CODE:18]]

Handler gửi mail:

[[CODE:19]]

Đăng ký handler trong `NotificationsModule`, module này import `CustomersModule` để lấy repository:

[[CODE:20]]

Mỗi tùy chọn của lời gọi `send()` có một nhiệm vụ riêng:

- **`idempotencyKey`.** Outbox gửi ít nhất một lần: một relay crash sau khi gửi, trước khi kịp ghi lại, sẽ gửi lại. Key xác định mail xuyên suốt các lần gửi đó. Header `Message-ID` được suy ra từ nó, nên qua SMTP, một bản trùng sẽ mang cùng id, và Gmail cùng các bên nhận khác dùng id đó để loại bỏ bản trùng. `ResendTransport` gửi key dưới dạng `Idempotency-Key` của Resend, và Resend từ chối bản trùng trong vòng 24 giờ. Postmark, SendGrid và SES tự gán `Message-ID` của chúng và không có idempotency key, nên với các dịch vụ này, một lần gửi lại có thể đến tay khách hàng hai lần.
- **`signal`.** Relay sẽ abort nó khi handler chạy lâu hơn `publishTimeout`. Mailer sẽ dừng phiên trao đổi SMTP hoặc HTTP request.
- **`retry: false`.** Mặc định mailer retry các lỗi tạm thời ba lần, có backoff. Ở đây outbox đã retry rồi, trong khoảng thời gian tính bằng phút thay vì giây, nên mailer chỉ thử một lần cho mỗi lần gửi. Retry ở cả hai tầng sẽ nhân số lần lên.

Mọi lỗi mà package throw ra đều kế thừa `MailError`, và flag `permanent` của nó cho biết gửi lại cùng message có thể thành công hay không. Một reply SMTP 4xx (greylisting, hộp thư đầy), một lỗi 429 từ HTTP provider, một timeout hay một kết nối bị ngắt đều là lỗi tạm thời: handler throw lại nó, và outbox sẽ retry. Một reply 5xx, như `550 5.1.1 User unknown`, là lỗi vĩnh viễn: handler throw `NonRetryableMessageError`, và outbox chuyển message vào dead-letter ngay lập tức thay vì thử thêm mười lần nữa.

Khi SMTP từ chối một trong nhiều người nhận, transaction được reset trước khi message được gửi, nên một lỗi luôn có nghĩa là không ai nhận được nó, và việc retry của outbox không thể gửi trùng. Ngoại lệ duy nhất: kết nối bị ngắt sau khi message đã được truyền đi, trước khi server trả lời. Mailer không thể biết server đã giữ lại message hay chưa, nên báo một lỗi tạm thời, và lần retry sẽ gửi lại nó, với cùng `Message-ID`.

**Với TypeORM.** Cùng transaction đơn hàng đó cho một ứng dụng dùng ORM là TypeORM. Drizzle vẫn là hướng chính của bài hướng dẫn: hãy dùng code này thay cho code Drizzle ở trên, không phải dùng song song. Outbox giữ message thông qua cùng store đó, trên data source của TypeORM, như phần [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database) trong bài hướng dẫn outbox trình bày. Ứng dụng ví dụ giữ phiên bản này trong `src/typeorm`, cạnh code Drizzle của bài hướng dẫn, với khách hàng, sản phẩm và đơn hàng là các entity.

`TypeOrmModule` thay chỗ cho `DrizzleModule` trong root module, với các tùy chọn mà TypeORM CLI dùng chung, và factory của store inject `DataSource` của nó, thông qua `fromTypeOrm()`:

[[CODE:21]]

`OrdersService` mở transaction bằng data source, và truyền entity manager của transaction vào `outbox.add()`, cạnh các thao tác ghi của chính nó. Type parameter của outbox là `EntityManager` của TypeORM:

[[CODE:22]]

`OrderEntity` khai báo `number` là một identity column (`generated: 'identity'`), nên `manager.insert()` trả về con số mà database đã gán trong `generatedMaps`. Một entity không thể chỉ định sequence bắt đầu từ đâu, nên migration seed của ví dụ khởi động lại nó từ 1001, cạnh các khách hàng và sản phẩm mà nó insert. Handler và `NotificationsModule` giữ nguyên; `CustomersRepository` đọc khách hàng bằng TypeORM, giống như phần còn lại của ứng dụng.

#### Gửi trên production

Development ghi file ra ổ đĩa local, thứ mà một container sẽ mất khi bị thay thế; production cần một transport thực thụ. Hãy chọn nó theo môi trường, để cùng một bản build chạy được ở mọi nơi:

[[CODE:23]]

Tạo transport trong `forRootAsync()`. Factory chạy lúc khởi động, nên một lỗi gõ trong `MAIL_TRANSPORT` hay việc thiếu `SMTP_URL` sẽ làm ứng dụng dừng ngay tại đó thay vì làm hỏng mail đầu tiên:

[[CODE:24]]

**SMTP.** `SmtpTransport` tự nói chuyện bằng SMTP, trên `node:net` và `node:tls`:

- **Mã hóa.** Trên port 587, nó nâng cấp kết nối bằng STARTTLS, và một server không hỗ trợ STARTTLS sẽ bị từ chối thay vì gửi dạng plaintext. `startTls: 'opportunistic'`, mặc định cho localhost, chỉ nâng cấp khi server hỗ trợ, còn `'never'` giữ plaintext, dành cho relay trên mạng tin cậy. Trên port 465 (`smtps://`), nó dùng TLS ngay từ byte đầu tiên. Chứng chỉ được xác minh theo host name; `tls.ca` thêm một CA riêng. Thông tin đăng nhập không bao giờ được gửi qua kết nối không mã hóa, trừ khi gửi tới localhost.
- **Xác thực.** Nó dùng AUTH PLAIN hoặc LOGIN, tùy server hỗ trợ cái nào, và `authMethod` ép dùng một cái cụ thể. Với Gmail và Microsoft 365, hãy truyền OAuth access token làm `accessToken` trong `auth` để dùng XOAUTH2. OAuth access token sẽ hết hạn, thường là sau một giờ, nên `accessToken` cũng có thể là một hàm trả về token, hoặc một promise của token: nó được gọi cho mỗi kết nối mới, và có thể lấy token mới. `name` đặt tên mà transport dùng để giới thiệu bản thân trong `EHLO`; mặc định là host name của máy nếu đó là tên đầy đủ (fully qualified), nếu không thì là địa chỉ IP.
- **Pooling.** `pool: true` giữ tối đa năm kết nối mở và dùng lại chúng, thay vì một lần bắt tay TCP và TLS cho mỗi mail. Một object sẽ đặt các giới hạn: `maxConnections` (mặc định 5; các lần gửi tiếp theo phải chờ có kết nối rảnh), `maxMessages` (mặc định 100, sau đó kết nối sẽ được thay mới) và `idleTimeout` (mặc định `'30s'`, sau đó kết nối rảnh sẽ bị đóng). Mọi kết nối đều gửi `QUIT` khi ứng dụng tắt.
- **Reply.** Một reply 4xx là `MailSmtpError` tạm thời, reply 5xx là vĩnh viễn. Cả hai đều mang `code` của reply, mã mở rộng (như `5.1.1`) và text của server.

Để ký mail bằng DKIM khi SMTP server của bạn không làm việc đó, hãy thêm `dkim` với domain (`domainName`), selector (`keySelector`) và private key (`privateKey`, dạng PEM hoặc `KeyObject`). Key RSA ký bằng `rsa-sha256`, key Ed25519 ký bằng `ed25519-sha256` (RFC 8463); không phải bên nhận nào cũng đã xác minh được chữ ký Ed25519, và transport chỉ ký bằng một key, nên RSA là lựa chọn an toàn trừ khi bạn biết chắc server của người nhận hỗ trợ. Chữ ký bao gồm From, Reply-To, To, Cc, Subject, Date, Message-ID và các header MIME, cộng thêm các header tùy chỉnh của message; `dkim.headers` thay thế danh sách đó. From luôn được ký, và được liệt kê nhiều hơn số lần nó xuất hiện trong message một lần, nên một From thứ hai được thêm vào phía dưới chữ ký sẽ làm hỏng chữ ký. Các HTTP provider tự ký bằng domain đã xác minh của bạn.

**HTTP provider.** `ResendTransport`, `PostmarkTransport`, `SendGridTransport` và `SesTransport` gọi API của các provider bằng `fetch`, và không cần SDK nào. Tùy chọn `fetch` thay thế hàm toàn cục, để đi qua proxy hoặc để stub API trong test. `SesTransport` ký request bằng AWS Signature Version 4, và nhận các credential provider của AWS SDK, như instance role, làm `credentials`. Trong bốn cái, chỉ Resend hỗ trợ idempotency key. Resend và SendGrid cần ít nhất một người nhận `to`: một mail chỉ có `cc` hoặc `bcc` sẽ thất bại với `MailMessageError` trước khi gửi request.

**Địa chỉ quốc tế hóa.** Một domain có ký tự không phải ASCII (`zoë@kočka.example`) được chuyển sang dạng ASCII (IDNA, `xn--...`) với mọi transport, để không server nào phải hỗ trợ nó. Phần local không phải ASCII, đứng trước `@`, thì không chuyển được: qua SMTP, nó cần extension SMTPUTF8 của server. `SmtpTransport` dùng SMTPUTF8 khi server hỗ trợ, nếu không sẽ thất bại với một `MailConnectionError` vĩnh viễn trước khi gửi bất cứ thứ gì: `The SMTP server ... doesn't support SMTPUTF8, which an address with non-ASCII characters needs`. Các HTTP provider nhận địa chỉ nguyên vẹn, và việc chấp nhận hay không là do provider quyết định.

Hãy dùng `app.enableShutdownHooks()` trong `main.ts`, để một đợt deploy cho relay hoàn tất những mail đang gửi, rồi mới đóng SMTP pool.
