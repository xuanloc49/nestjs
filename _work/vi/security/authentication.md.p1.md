### Xác thực

`@nestjs/authentication` đăng nhập người dùng và cho phần còn lại của ứng dụng biết họ là ai. Nó đăng ký một global guard, cung cấp decorator và một context có thể inject để đọc người dùng hiện tại, và có sẵn những thành phần mà mọi luồng đăng nhập đều cần: session phía server, hash mật khẩu, link xác minh email và đặt lại mật khẩu, xác thực hai lớp TOTP, magic link, OpenID Connect, access token và refresh token, và API key. Tất cả đều xây dựng trên các thành phần có sẵn của Node.js, và giữ state trong database của bạn thông qua một store mà bạn viết theo các interface đã được mô tả, kèm bộ test của package để kiểm tra nó. Bạn chỉ viết những gì mà riêng ứng dụng của bạn biết: cách load một người dùng, route nào là công khai, và các endpoint của luồng đăng nhập.

Trong bài hướng dẫn này, bạn sẽ thêm tính năng đăng nhập vào API của một cửa hàng online bán thức ăn và đồ dùng cho mèo. Khi hoàn thành, nó sẽ:

- Cho khách hàng đăng nhập bằng mật khẩu, bằng Google, hoặc bằng link gửi qua email, và giữ trạng thái đăng nhập cho web app bằng session cookie.
- Xác minh địa chỉ email của khách hàng, và cho họ đặt lại mật khẩu khi quên.
- Cấp cho app mobile các bearer token ngắn hạn và refresh token có xoay vòng.
- Cung cấp xác thực hai lớp bằng app authenticator, và yêu cầu nó khi đổi địa chỉ email của tài khoản.
- Cho khách hàng xem họ đang đăng nhập ở đâu, và đăng xuất khỏi mọi nơi.
- Giới hạn tốc độ đoán mật khẩu của bất kỳ ai.
- Giữ session, token và các link đang chờ trong PostgreSQL, qua Drizzle (hoặc TypeORM).
- Cho hệ thống của đối tác và script của khách hàng gọi API bằng các key mà khách hàng tự tạo và thu hồi.

Đây là các endpoint bạn sẽ xây dựng, cùng phần hướng dẫn thêm từng endpoint:

| Endpoint | Phần |
| --- | --- |
| `POST /auth/sign-up`, `POST /auth/sign-in` | [Thêm đăng ký và đăng nhập](/security/authentication#add-sign-up-and-sign-in) |
| `POST /auth/email/verify`, `POST /auth/email/verification` | [Xác minh địa chỉ email](/security/authentication#verify-email-addresses) |
| `POST /auth/password/forgot`, `POST /auth/password/reset` | [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords) |
| `GET /me`, `GET /orders`, `POST /orders` | [Đọc người dùng hiện tại](/security/authentication#read-the-current-user) |
| `POST /auth/token`, `POST /auth/token/refresh` | [Cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app) |
| `POST /auth/mfa/enroll`, `POST /auth/mfa/replace`, `POST /auth/mfa/confirm`, `POST /auth/mfa/verify`, `PATCH /me/email` | [Thêm xác thực hai lớp](/security/authentication#add-two-factor-authentication) |
| `GET /auth/oidc/google/login`, `GET /auth/oidc/google/callback` | [Thêm "Đăng nhập bằng Google"](/security/authentication#add-sign-in-with-google) |
| `POST /auth/magic-link`, `POST /auth/magic-link/consume` | [Thêm đăng nhập bằng magic link](/security/authentication#add-magic-link-sign-in) |
| `GET /auth/sessions`, `DELETE /auth/sessions/:id`, `POST /auth/sign-out`, `POST /auth/sign-out-everywhere`, `POST /auth/token/revoke` | [Cho khách hàng quản lý session](/security/authentication#let-customers-manage-their-sessions) |
| `POST /auth/api-keys`, `GET /auth/api-keys`, `DELETE /auth/api-keys/:id` | [Cấp API key cho đối tác](/security/authentication#issue-api-keys-to-partners) |

#### Cài đặt

Cài package:

[[CODE:1]]

Request body được validate bằng bất cứ công cụ nào ứng dụng của bạn đang dùng. Mọi DTO trên trang này đều có hai phiên bản, một class có decorator và một schema Zod, nên hãy chọn kiểu bạn đang dùng và bỏ qua phiên bản còn lại.

Bài hướng dẫn giữ người dùng trong bộ nhớ, đằng sau một class `UsersRepository`. Hãy thay phần thân các method của nó bằng Prisma, Drizzle, TypeORM, hoặc bất cứ thứ gì ứng dụng của bạn dùng; phần code còn lại chỉ thấy các object `User` thuần. State xác thực (session, token, authenticator, các link đang chờ) được chuyển sang PostgreSQL trong phần [Giữ session và token trong database của bạn](/security/authentication#keep-sessions-and-tokens-in-your-database).

Bắt đầu từ phần xác minh email, ứng dụng đọc thiết lập và secret từ biến môi trường. Hãy giữ chúng trong một file `.env` khi phát triển, và khởi động ứng dụng với file đó:

[[CODE:2]]

#### Đăng ký authentication module

Package không bao giờ đọc bảng người dùng của bạn. Nó hỏi code của bạn để lấy người dùng theo id, và code của bạn quyết định người dùng là gì. Đây là người dùng của cửa hàng. `emailVerified` ghi nhận khách hàng đã chứng minh họ sở hữu địa chỉ email hay chưa; việc xác minh email sẽ đặt giá trị này, và việc đặt hàng, đăng nhập bằng Google và magic link đều phụ thuộc vào nó:

[[CODE:3]]

Repository giữ kín các hash mật khẩu. Mọi thứ nó trả về đều là `User` không có hash, nên một người dùng có thể được trả về từ route hoặc ghi vào log mà không làm lộ hash:

[[CODE:4]]

[[CODE:5]]

Tiếp theo là một **credential provider**. Một provider xem xét request gửi đến và trả về người dùng mà request đó chứng minh, hoặc `null` khi request không mang thông tin xác thực nào nó hiểu được. `SessionCookieProvider` đọc session cookie, load session, rồi truyền nó cho method `validate()` của bạn, method này load người dùng:

[[CODE:6]]

Provider là các class `@Injectable()` thông thường, nên chúng inject được bất cứ thứ gì cần, và chúng tự đăng ký: constructor truyền `this` cho `AuthenticationRegistry`, danh sách provider của package, nơi guard tham khảo. Class cha nhận `SessionService` qua injection qua property, đó là lý do constructor chỉ liệt kê `UsersRepository` và registry. Vì `validate()` chạy ở mọi request đã xác thực, một người dùng bị xóa sẽ mất quyền truy cập ngay lập tức, chứ không phải khi session hết hạn. Khi người dùng nằm cùng database với session, store có thể đọc người dùng trong cùng một query và truyền nó cho `validate()` dưới dạng `session.extra`, nên một request chỉ tốn một lần đọc thay vì hai; phần [Giữ session và token trong database của bạn](/security/authentication#keep-sessions-and-tokens-in-your-database) chỉ cách làm.

Hãy cung cấp nó trong một module của riêng bạn. `AuthModule` sẽ chứa mọi thứ bài hướng dẫn này thêm vào dưới `src/auth`:

[[CODE:7]]

Giờ hãy đăng ký `AuthenticationModule` trong root module, cạnh `AuthModule`:

[[CODE:8]]

`forRoot()` chỉ nhận giá trị: thời gian sống, secret, client id, các trang mà email của bạn link tới. Không có class nào nằm trong tùy chọn. Các credential provider, các handler mà các phần sau thêm vào, và [database store](/security/authentication#keep-sessions-and-tokens-in-your-database) đều là provider trong module của riêng bạn, và mỗi cái tự đăng ký từ constructor của nó, nên nó nằm cạnh những gì nó inject, còn tùy chọn của module vẫn chỉ là dữ liệu thuần. Thời gian sống tính bằng mili giây, hoặc chuỗi như `'15m'` và `'14d'`, tối đa 100 năm. `@nestjs/jwt` thì tính bằng giây, nên một thời gian sống dạng số dưới một phút sẽ log cảnh báo lúc khởi động: `3600` ở đây là 3,6 giây, không phải một giờ.

Lúc khởi động, khi constructor của mọi provider đã chạy xong, registry sẽ khóa lại và log chuỗi provider mà nó sẽ thử:

[[CODE:9]]

Module cũng đăng ký một global guard. Từ giờ trở đi, **mọi route đều yêu cầu người dùng đã đăng nhập** và trả lời `401 Unauthorized` với bất kỳ ai khác. Nếu ứng dụng của bạn đã có những route cần để công khai, như health check hay danh mục sản phẩm, hãy đánh dấu chúng bằng `@Public()`, decorator được giới thiệu ở phần tiếp theo.

> info **Hint** Session được lưu trong bộ nhớ cho đến khi một provider đăng ký store, và khi `NODE_ENV` được đặt thành `production`, module sẽ từ chối khởi động theo cách đó. Một [phần sau](/security/authentication#keep-sessions-and-tokens-in-your-database) chuyển chúng sang database của bạn.

#### Thêm đăng ký và đăng nhập

Đầu tiên hãy validate request body. Đăng ký áp dụng độ dài mật khẩu tối thiểu; đăng nhập thì không, để mật khẩu được đặt theo quy tắc cũ vẫn dùng được:

[[CODE:10]]

Cùng các quy tắc đó dưới dạng schema Zod, với type suy ra từ schema thay cho class. Nest 12.1 validate mọi object [Standard Schema](https://standardschema.dev/), từ Zod, Valibot hay ArkType, thông qua `StandardSchemaValidationPipe`:

[[CODE:11]]

`PasswordHasher` hash mật khẩu bằng scrypt (`crypto.scrypt`, chạy trên threadpool của libuv, nên không làm nghẽn event loop), mặc định dùng các tham số mà OWASP khuyến nghị. Một service bọc hai thứ mà controller cần:

[[CODE:12]]

- `verify()` khi không có hash đã lưu sẽ kiểm tra mật khẩu với một hash giả. Email không tồn tại và mật khẩu sai tốn cùng thời gian và cho cùng câu trả lời, nên không cái nào để lộ email nào có tài khoản.
- Mật khẩu được hash bằng scrypt từ `node:crypto`, với các tham số OWASP khuyến nghị (N=2^17, r=8, p=1: khoảng 128 MiB bộ nhớ cho mỗi lần hash), trên thread pool của libuv. Đó là một hàm memory-hard, điều mà bcrypt không phải, và nó không cần dependency native nào. Mỗi hash ghi lại các tham số đã dùng để tạo ra nó (`$scrypt$ln=17,r=8,p=1$...`). Khi bạn tăng chi phí bằng tùy chọn `password`, `needsRehash()` cho biết những hash đã lưu nào cần nâng cấp, và thời điểm duy nhất bạn làm được việc đó là khi người dùng đăng nhập. Cho đến lúc đó, `verify()` bù thêm cho việc kiểm tra một hash cũ, rẻ hơn, cho bằng khối lượng công việc của các tham số mới, để nó vẫn tốn thời gian bằng một email không tồn tại. Giảm chi phí thì không che giấu được theo cách đó: một hash tạo với tham số tốn kém hơn sẽ mất nhiều thời gian kiểm tra hơn cho đến khi được nâng cấp. Chi phí có mức trần là 1 GiB bộ nhớ và gấp 16 lần khối lượng công việc mặc định cho mỗi lần hash, nên với `r` là 8, `logN` dừng ở 20. Tham số vượt quá mức đó sẽ lỗi lúc khởi động, và một hash đã lưu tạo với chúng sẽ không bao giờ xác minh được.
- `register()` để địa chỉ ở trạng thái chưa xác minh. Gõ một email vào form đăng ký không chứng minh được bạn sở hữu nó.

Controller biến một mật khẩu đã xác minh thành một session:

[[CODE:13]]

`@Public()` trên class bỏ qua xác thực cho cả hai route. `SignInService.signIn()` là nơi duy nhất một yếu tố xác thực thứ nhất trở thành session: bước này gọi nó sau khi kiểm tra mật khẩu, và các bước Google và magic link cũng đi qua nó. Nó tạo session và tự đặt session cookie lên response, trên cả Express lẫn Fastify, nên controller không cần `@Req()` hay `@Res()`:

- Cookie `__Host-sid` chứa một token ngẫu nhiên 256 bit và có các thuộc tính `HttpOnly`, `Secure` và `SameSite=Lax`. Prefix `__Host-` báo cho trình duyệt chỉ chấp nhận cookie này từ chính host này, nên một trang trên subdomain khác không thể cài session cookie của riêng nó. Chỉ hash SHA-256 của token được lưu, nên một session store bị lộ không thể bị dùng lại làm cookie.
- Nó xóa session mà trình duyệt này có trước đó, giúp phòng chống session fixation.
- Nó từ chối, với lỗi 403, một lần đăng nhập được gửi từ trang của một website khác. Nếu không, trang đó có thể đăng nhập trình duyệt của khách hàng vào một tài khoản do kẻ tấn công chọn (login CSRF).
- `method` được ghi lại trong audit trail, như phần [quản lý session](/security/authentication#let-customers-manage-their-sessions) có đề cập.
- `mfaRequired` giữ là `false` cho đến khi bạn [thêm yếu tố xác thực thứ hai](/security/authentication#add-two-factor-authentication).

Với các schema Zod, tham số body khai báo schema thay vì class:

[[CODE:14]]

Đăng ký controller trong `AuthModule`:

[[CODE:15]]

> info **Hint** Các DTO chỉ được áp dụng khi có validation pipe: hãy bind `ValidationPipe` ở cấp global, dưới dạng provider `APP_PIPE` của `AppModule` hoặc bằng `useGlobalPipes()` trong `main.ts`. Với các schema Zod, hãy bind `StandardSchemaValidationPipe` theo cùng cách: một ứng dụng dùng một trong hai. Trang [validation](/application/validation) có các tùy chọn của mỗi loại.

> info **Hint** Chrome, Firefox và curl xem `http://localhost` là một origin an toàn và chấp nhận cookie `Secure` và `__Host-` từ nó, nên bạn không cần HTTPS khi phát triển. Trên một host khác qua HTTP thường, như một địa chỉ mạng LAN, hãy đặt `cookie.secure` thành `false` trong tùy chọn `session` ở đó; khi đó cookie sẽ có tên là `sid`.

Session cookie cũng được bảo vệ khỏi cross-site request forgery. Bên cạnh `SameSite=Lax`, module bỏ qua cookie trên các request `POST`, `PUT`, `PATCH` và `DELETE`, cũng như các WebSocket handshake, đến từ một origin khác, dựa trên các header `Sec-Fetch-Site`, `Origin` và `Host`, nên những request đó là ẩn danh. Các client không gửi cả `Sec-Fetch-Site` lẫn `Origin`, như curl và app mobile của bạn, không bị ảnh hưởng. Nếu web app của bạn chạy trên một origin khác với API, hãy liệt kê nó trong `session.trustedOrigins`.

Trên Nest 12.1 trở lên, hãy gọi thêm `app.enableCsrfProtection()` trong `main.ts`. Nó đưa ra cùng quyết định đó cho mọi route, với lỗi 403, kể cả các route công khai chưa có session nào để bảo vệ. Hãy truyền cho nó cùng `trustedOrigins` như trong tùy chọn `session`.

#### Xác minh địa chỉ email

Ai cũng có thể gõ bất kỳ địa chỉ nào vào form đăng ký. Cho đến khi khách hàng chứng minh địa chỉ đó là của họ, bằng cách mở một link gửi tới nó, cửa hàng xem nó là chưa xác minh: cửa hàng sẽ không nhận đơn hàng có hóa đơn gửi tới đó, và không cho tài khoản Google hay magic link vào tài khoản đó, như các phần sau sẽ trình bày. Package tạo và kiểm tra các link. Ứng dụng của bạn gửi chúng đi, bằng library mail bạn chọn; cửa hàng dùng `@nestjs/mail`:

[[CODE:16]]

Từ bước này trở đi, ứng dụng đọc thiết lập từ biến môi trường. Hãy thêm URL công khai của ứng dụng vào `.env`. Các link trong email trỏ tới các trang của web app ở đó:

[[CODE:17]]

> info **Hint** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để một biến bị thiếu hoặc sai định dạng làm ứng dụng dừng ngay lúc khởi động thay vì ở request đầu tiên, và đọc giá trị từ `ConfigService`.

Đăng ký `MailModule` trong `AppModule`. Giờ cả hai module đều đọc biến môi trường, nên `AuthenticationModule` chuyển sang dùng `forRootAsync()`: factory của nó chạy lúc bootstrap, trong khi tham số của `forRoot()` được evaluate khi file được import, điều này vẫn ổn khi mọi giá trị đều là literal. Với `@nestjs/config`, hãy thêm `inject: [ConfigService]` và đọc giá trị từ service được inject. Ở development, `LogMailTransport` in mỗi email ra log của ứng dụng, để bạn có thể đi theo các link; đặt `SMTP_URL` để gửi email thật. `FileTemplateEngine` render body của email từ các file HTML trong `src/mail/templates`, mỗi email một file:

[[CODE:18]]

Trình biên dịch TypeScript không copy file HTML sang `dist`: hãy thêm các template vào asset trong `nest-cli.json`, như bài hướng dẫn [Mail](/application/mail#register-the-mail-module) chỉ dẫn; bài đó cũng trình bày cú pháp template.

Email xác minh là một template. Link được đặt giữa cặp ngoặc nhọn đôi, thứ sẽ escape nó:

[[CODE:19]]

Một mail class render email từ template, với link làm context, và một `EmailVerificationHandler` kết nối package với nó: `send()` gửi đi một link, còn `markVerified()` ghi nhận một địa chỉ đã xác minh vào bảng người dùng của bạn. Giống như credential provider, handler tự đăng ký, dưới tên của tính năng mà nó phục vụ:

[[CODE:20]]

`markVerified()` chỉ đánh dấu đúng địa chỉ mà link được gửi tới. Nếu khách hàng đã đổi địa chỉ kể từ đó, link sẽ không xác minh gì cả. Repository chỉ cập nhật dòng dữ liệu khi địa chỉ vẫn khớp, trong SQL đó là một câu update có điều kiện (`UPDATE users SET email_verified = true WHERE id = $1 AND email = $2`):

[[CODE:21]]

Một tính năng có hai nửa: handler của nó, và tùy chọn của nó. Hãy cung cấp handler trong `AuthModule`, và cấu hình trang mà các link mở ra. Có nửa này mà thiếu nửa kia sẽ lỗi lúc khởi động, kèm thông báo nêu tên phần bị thiếu:

[[CODE:22]]

[[CODE:23]]

Gửi link khi khách hàng đăng ký:

[[CODE:24]]

Sau đó thêm các endpoint. Link mở một trang của web app, trang này POST token từ URL của nó ngược lại cho API: các trình quét email và trình xem trước link đi theo link trong email bằng request GET, và sẽ dùng hết token trước khi khách hàng kịp click.

[[CODE:25]]

- `EmailVerificationService.send()` lưu hash SHA-256 của một token ngẫu nhiên 256 bit, cùng id của khách hàng và địa chỉ, rồi truyền link cho handler của bạn. Bản thân token chỉ tồn tại trong email.
- Một link chỉ dùng được một lần, trong 24 giờ (`emailVerification.ttl`), và chỉ cho đúng địa chỉ mà nó được gửi tới. `verify()` trả về `null` với token không tồn tại, đã dùng hoặc đã hết hạn, và với địa chỉ đã thay đổi kể từ đó, và route sẽ trả lời 400.
- `resend` không phải `@Public()`: chỉ khách hàng đã đăng nhập mới xin được link mới, và chỉ tới địa chỉ của chính họ, nên route không để lộ gì về các tài khoản khác.

Đăng ký controller:

[[CODE:26]]

Package cũng có thể yêu cầu địa chỉ đã xác minh trên một route: `@Authenticate()` với `verifiedEmail: true` sẽ trả lời 403 cho khách hàng đã đăng nhập nhưng chưa xác minh địa chỉ. Phần [Đọc người dùng hiện tại](/security/authentication#read-the-current-user) dùng nó cho việc đặt hàng.

> info **Hint** `LogMailTransport` log nội dung text của mỗi email ở level `debug`, kể cả link, nên đừng bao giờ dùng nó ở nơi log được gửi đi. Trên production, hãy đặt `SMTP_URL`, hoặc truyền một transport khác, như `ResendTransport`. Bài hướng dẫn [Mail](/application/mail) trình bày các tùy chọn.

#### Đặt lại mật khẩu đã quên

Một khách hàng quên mật khẩu sẽ xin một link, và chọn mật khẩu mới trên trang mà link mở ra. Email gửi link là một template khác:

[[CODE:27]]

Package sở hữu các token; một `PasswordResetHandler` tìm tài khoản, gửi email, và lưu hash của mật khẩu mới:

[[CODE:28]]

`findUser()` trả về id của tài khoản, địa chỉ đã lưu và hash mật khẩu đã lưu của nó, hoặc `null` với tài khoản không có mật khẩu. Link được gửi tới địa chỉ đã lưu đó, không bao giờ tới địa chỉ được gõ vào form: nếu không, một phép tra cứu bỏ qua dấu hoặc dấu chấm, như collation mặc định của MySQL làm, sẽ gửi link của một khách hàng cho bất kỳ ai gõ một địa chỉ trông giống. Một link chỉ dùng được khi địa chỉ và hash không thay đổi, nên một lần đổi mật khẩu, qua bất kỳ route nào, sẽ vô hiệu hóa các link đã gửi trước đó. Bỏ trống địa chỉ hoặc hash là lỗi, package sẽ log lỗi đó thay vì gửi link.

Bật tính năng đặt lại mật khẩu cạnh xác minh email, handler trong `AuthModule` và trang trong tùy chọn:

[[CODE:29]]

[[CODE:30]]

Một endpoint nhận địa chỉ, endpoint kia nhận token và mật khẩu mới, mật khẩu này tuân theo quy tắc của bước đăng ký:

[[CODE:31]]

[[CODE:32]]

[[CODE:33]]

- `request()` trả về trước khi tra cứu địa chỉ. Việc tìm tài khoản, lưu token và gửi email diễn ra sau khi response được gửi đi, nên một request cho địa chỉ chưa ai đăng ký nhận được cùng mã 202, trong cùng khoảng thời gian, như request của một khách hàng thật: route không thể cho ai biết ai có tài khoản. Đó là lý do `forgot` không `await` gì cả. Một lỗi xảy ra sau khi response đã gửi, như mail server bị sập, sẽ được log.
- Một link chỉ dùng được một lần, trong một giờ (`passwordReset.ttl`), và chỉ khi tài khoản vẫn còn địa chỉ và mật khẩu như lúc link được gửi.
- `reset()` lưu hash của mật khẩu mới, vô hiệu hóa các link đặt lại khác của khách hàng, và kết thúc mọi session của tài khoản, cùng mọi refresh token khi ứng dụng [cấp chúng](/security/authentication#issue-tokens-to-the-mobile-app), nên bất kỳ ai biết mật khẩu cũ đều bị đăng xuất khỏi mọi nơi. [API key](/security/authentication#issue-api-keys-to-partners) nằm trong bảng của riêng bạn và vẫn còn hiệu lực: để cắt cả chúng, hãy thu hồi chúng khi có event `password-reset`. Một mật khẩu mà `PasswordHasher` từ chối, rỗng hoặc vượt quá 4 KiB, sẽ nhận `null` mà không làm tốn link, nên khách hàng có thể thử lại. Với `signIn: true`, sau đó nó đăng nhập khách hàng trên trình duyệt này thông qua `SignInService`, nên một khách hàng có [xác thực hai lớp](/security/authentication#add-two-factor-authentication) vẫn phải nhập mã.
- Link cũng chứng minh luôn địa chỉ, nên `reset()` đánh dấu nó là đã xác minh, thông qua `markVerified()` của bạn. Điều đó cũng cứu được một tài khoản mà người khác đã đăng ký bằng địa chỉ của khách hàng: việc đặt lại sẽ thay mật khẩu của người lạ và đăng xuất họ.

Với các schema Zod:

[[CODE:34]]

Đăng ký controller:

[[CODE:35]]
