### Bảo vệ CSRF

Cross-site request forgery (CSRF hoặc XSRF) là một kiểu tấn công trong đó một site độc hại khiến trình duyệt của người dùng gửi tới ứng dụng của bạn những request không mong muốn, có làm thay đổi state. Vì trình duyệt gắn cookie của người dùng vào các request đó, ứng dụng xem chúng như thể người dùng cố ý gửi.

Kể từ NestJS v12.1, Nest có sẵn cơ chế bảo vệ CSRF. Nó hoạt động giống nhau trên Express và Fastify, và không cần thêm package, cookie, session, hay thay đổi gì trong code phía client.

#### Cách hoạt động

Các trình duyệt hiện đại cho server biết mỗi request đến từ đâu. Chúng gửi header [`Sec-Fetch-Site`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-Fetch-Site) (một phần của Fetch Metadata), có giá trị `same-origin` khi một trang của chính bạn tạo ra request, và `same-site` hoặc `cross-site` khi một site khác tạo ra. Chúng cũng gửi header `Origin` kèm các request cross-origin. Cơ chế bảo vệ có sẵn từ chối các request làm thay đổi state mà trình duyệt báo là cross-origin, theo thuật toán của [`CrossOriginProtection`](https://pkg.go.dev/net/http#CrossOriginProtection) trong Go 1.25.

Chi tiết hơn, mỗi request được kiểm tra như sau:

1. Request `GET`, `HEAD` và `OPTIONS` luôn được cho phép.
2. Nếu request có header `Sec-Fetch-Site`, các giá trị `same-origin` và `none` (một lần điều hướng do người dùng khởi động, như mở một bookmark) được cho phép. Mọi giá trị khác, kể cả `same-site`, đều bị từ chối.
3. Nếu request không có cả header `Sec-Fetch-Site` lẫn `Origin`, nó được cho phép, vì nó không đến từ trình duyệt.
4. Ngược lại, host của header `Origin` phải khớp với header `Host` của request (`:authority` trên HTTP/2). Phép so sánh không phân biệt hoa thường và bỏ qua port mặc định của scheme, nên `https://example.com` khớp với `example.com:443`. Header `X-Forwarded-Host` bị bỏ qua.

Một request lẽ ra bị từ chối vẫn được cho phép khi nó khớp với một [route được loại trừ](/security/csrf#excluding-routes), hoặc khi `Origin` của nó nằm trong danh sách [origin tin cậy](/security/csrf#trusted-origins).

#### Bắt đầu

Để bật cơ chế bảo vệ, gọi method `enableCsrfProtection()` trên object ứng dụng Nest:

[[CODE:1]]

Bước kiểm tra chạy cho mọi request, kể cả request tới các route không tồn tại, trước middleware của Nest, việc parse body, guard, interceptor và route handler. Các quy tắc sau được áp dụng:

- Gọi `enableCsrfProtection()` trước `app.init()` hoặc `app.listen()`. Gọi nó sau đó, hoặc gọi hai lần, sẽ throw lỗi.
- Các tùy chọn được validate ngay khi bạn gọi method, nên một cấu hình sai sẽ lỗi lúc khởi động. Ví dụ, một tùy chọn viết sai sẽ throw `Invalid CSRF protection options: unknown option "trustedOrigin" (expected "trustedOrigins", "exclude").`
- Bước kiểm tra được đăng ký dưới dạng một middleware ở cấp framework (Express) hoặc hook `onRequest` (Fastify) tại thời điểm bạn gọi method. Middleware đăng ký bằng `app.use()` trước lời gọi đó sẽ chạy trước, nên hãy gọi `enableCsrfProtection()` ngay sau `NestFactory.create()`.
- `app.useSecurityHeaders()` (xem [Security header](/security/helmet)) dùng chung request hook. Bạn có thể gọi hai method theo bất kỳ thứ tự nào: các header luôn được ghi trước khi bước kiểm tra CSRF chạy, nên các request bị từ chối cũng mang chúng.
- `setGlobalPrefix()` và `enableVersioning()` có thể được gọi trước hoặc sau `enableCsrfProtection()`, vì các mục loại trừ được resolve khi ứng dụng khởi tạo.

#### Request bị từ chối

Một request bị từ chối trở thành `ForbiddenException`, đi qua các global [exception filter](/exception-filters) của bạn như mọi exception khác. Không có filter tùy chỉnh, client nhận được response `403` như sau:

[[CODE:2]]

Khi request không có header `Sec-Fetch-Site` và `Origin` của nó không khớp với `Host`, message là `Cross-origin request detected, and/or browser is out of date: Sec-Fetch-Site is missing, and Origin does not match Host`.

Vì bước kiểm tra chạy trước routing, các filter, guard và interceptor ở cấp controller không chạy với các request bị từ chối.

#### Tùy chọn

Method `enableCsrfProtection()` nhận một options object tùy chọn:

[[CODE:3]]

| Tùy chọn         | Type                                                      | Mô tả                                                                                        |
| ---------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `trustedOrigins` | `string[]`                                                | Các origin được phép gửi request cross-origin làm thay đổi state. Mặc định là không có.      |
| `exclude`        | một mảng path và object `RouteInfo`, hoặc một hàm         | Các request được bỏ qua bước kiểm tra. Chỉ được xét với những request lẽ ra bị từ chối.     |

Mọi tùy chọn khác đều bị từ chối khi gọi method.

#### Origin tin cậy

Một frontend được phục vụ từ origin khác, như một trang admin trên subdomain anh em, sẽ gửi request cross-origin. Trình duyệt báo chúng là `same-site` hoặc `cross-site`, nên chúng bị từ chối trừ khi bạn liệt kê origin của frontend trong `trustedOrigins`:

[[CODE:4]]

Mỗi mục phải là một origin đã serialize theo dạng `scheme://host[:port]`:

- Không được có path (kể cả một dấu `/` ở cuối), query string, fragment, thông tin đăng nhập và wildcard. Hãy liệt kê từng origin riêng biệt.
- Các mục được chuẩn hóa theo cách trình duyệt serialize header `Origin`: chữ thường, không có port mặc định. `https://Example.com:443` trở thành `https://example.com`.
- Một request được miễn khi header `Origin` của nó bằng chính xác một trong các mục.

Một mục không hợp lệ sẽ throw lúc khởi động, ví dụ `Invalid trusted origin "https://example.com/": expected "scheme://host[:port]", without a path, query string or fragment.`

> warning **Warning** Các origin được [CORS](/security/cors) cho phép không tự động được tin cậy. Nếu một frontend cross-origin gửi request làm thay đổi state kèm thông tin xác thực, hãy liệt kê cả origin của nó trong `trustedOrigins`.

#### Loại trừ route

Các request server-to-server thường không mang cả `Sec-Fetch-Site` lẫn `Origin`, nên chúng qua được bước kiểm tra mà không cần cấu hình gì. Hãy loại trừ một route khi nó phải chấp nhận request có origin lạ, ví dụ từ một bên gửi webhook có đặt header `Origin`, hoặc từ một identity provider gửi người dùng quay lại ứng dụng của bạn bằng một form `POST` cross-site (SAML, hoặc response mode `form_post` của OAuth).

Các mục loại trừ được khai báo giống như của `MiddlewareConsumer.exclude()` (xem [Middleware](/middleware)): dưới dạng một path, khớp với mọi request method, hoặc một object `RouteInfo` có `path`, `method`, và `version` tùy chọn. Path được khai báo không kèm global prefix:

[[CODE:5]]

Các mục loại trừ được resolve khi ứng dụng khởi tạo:

- [Global prefix](/faq/global-prefix) được thêm vào, trừ khi route đã được loại khỏi nó. Nếu một mục loại trừ khớp với một path đã được loại khỏi prefix và không có tham số hay wildcard, nó cũng áp dụng cho path đó (path này được phục vụ không kèm prefix). Việc so khớp này luôn phân biệt hoa thường. Ví dụ, với `webhooks/stripe` được loại khỏi prefix, `webhooks/*path` loại trừ cả `/api/webhooks/github` lẫn `/webhooks/stripe`.
- Với [URI versioning](/http/versioning), segment version của thuộc tính `version` được thêm vào. Version mặc định không được áp dụng, nên hãy đặt `version` trên mục loại trừ của một route có version.
- Route parameter và wildcard hoạt động như trong route path, ví dụ `webhooks/:provider` hoặc `webhooks/*path`.

Khác với `MiddlewareConsumer.exclude()`, việc so khớp là chính xác, vì một phép so khớp lỏng lẻo có thể để một request đến được một route không được loại trừ:

- Việc so khớp phân biệt hoa thường, và một dấu gạch chéo ở cuối không khớp. Query string bị bỏ qua.
- Các request path không chuẩn tắc không bao giờ khớp: path chứa `//`, các segment `.` hoặc `..`, `;`, `#`, `\`, hoặc `.`, `/`, `\` được percent-encode. Những request như vậy đi qua bước kiểm tra như mọi request khác, nên cơ chế bảo vệ fail closed (thất bại theo hướng an toàn).
- Trên Fastify, các mục loại trừ được so khớp với URL trước khi `rewriteUrl` chạy, giống như với `MiddlewareConsumer.exclude()`.

Nếu ứng dụng Fastify của bạn bật các tùy chọn router `ignoreTrailingSlash` hoặc `caseSensitive: false`, các biến thể của một path được loại trừ vẫn đến được route nhưng không được loại trừ, nên chúng bị từ chối. Nếu client cần các biến thể như vậy, hãy liệt kê chúng một cách tường minh. Vì dấu gạch chéo ở cuối bị bỏ khỏi path loại trừ, hãy dùng một nhóm tùy chọn để khớp nó:

[[CODE:6]]

Thay vì một danh sách, `exclude` cũng nhận một predicate nhận request object của nền tảng (một `Request` của Express hoặc `FastifyRequest`) và trả về `true` để bỏ qua bước kiểm tra. Nó chỉ được gọi với những request lẽ ra bị từ chối.

> warning **Warning** Một predicate nhận request thô, nên không quy tắc so khớp nào ở trên áp dụng cho nó. Ví dụ, một predicate kiểm tra `request.url` có bắt đầu bằng `/public/` hay không cũng sẽ bỏ qua bước kiểm tra cho `/public/../account`, path mà router hoặc proxy có thể resolve thành `/account`. Hãy ưu tiên dùng danh sách route khi có thể.

#### Giới hạn

- Cơ chế bảo vệ này không phải một scheme dựa trên token. Nó dựa vào header `Sec-Fetch-Site` của trình duyệt, header mà trình duyệt chỉ gửi tới các origin an toàn (HTTPS hoặc `localhost`), hoặc vào header `Origin`.
- Request `GET`, `HEAD` và `OPTIONS` không bao giờ được kiểm tra, nên các handler cho những method này không được làm thay đổi state.
- Cơ chế dự phòng `Origin`/`Host` không biết scheme. Với những trình duyệt không gửi `Sec-Fetch-Site`, một request từ `http://example.com` tới `https://example.com` được cho phép (fail open), giống như trong Go. [HSTS](/security/helmet#default-headers), thứ mà `app.useSecurityHeaders()` gửi mặc định, giúp giảm thiểu điều này.
- `X-Forwarded-Host` bị bỏ qua. Đằng sau một proxy viết lại header `Host`, những trình duyệt không gửi `Sec-Fetch-Site` sẽ rơi vào cơ chế dự phòng và nhận lỗi `403`. Hãy cấu hình proxy giữ nguyên `Host`, hoặc thêm origin công khai của bạn vào `trustedOrigins`.
- Một response `403` không mang header CORS khi CORS được đăng ký sau cơ chế bảo vệ, đó là trường hợp khi dùng tùy chọn `cors` của `NestFactory.create()`.
- Middleware đăng ký bằng `app.use()` trước `enableCsrfProtection()` chạy trước bước kiểm tra, và những request mà middleware đó trả lời sẽ không được kiểm tra.
- Request WebSocket upgrade không được kiểm tra. Nếu [gateway](/websockets/gateways) của bạn xác thực kết nối bằng cookie, hãy tự validate header `Origin` của handshake.

#### Khi nào bạn cần cách tiếp cận dựa trên token

CSRF lạm dụng thông tin xác thực mà trình duyệt tự động gắn vào request, nên các client không phải trình duyệt, như app mobile, công cụ CLI và các server khác, không cần bảo vệ CSRF. Request của chúng không mang cả `Sec-Fetch-Site` lẫn `Origin`, và được cho phép.

Mọi trình duyệt evergreen đều đã gửi `Sec-Fetch-Site` từ năm 2023. Các trình duyệt rất cũ không gửi cả hai header trông giống như client không phải trình duyệt, nên request của chúng cũng được cho phép. Nếu bạn buộc phải bảo vệ người dùng của những trình duyệt như vậy, hãy thêm một scheme dựa trên token, như mô tả bên dưới.

#### Bảo vệ dựa trên token

Các scheme dựa trên token lưu một secret trong cookie hoặc session, và yêu cầu client gửi một token khớp với nó kèm mỗi request làm thay đổi state. Chúng cần thay đổi code phía client và một package phụ thuộc vào nền tảng bên dưới.

##### Express

Cài package [csrf-csrf](https://github.com/Psifi-Solutions/csrf-csrf):

[[CODE:7]]

Sau đó đăng ký middleware của nó làm global middleware. Hàm `doubleCsrf()` yêu cầu các tùy chọn `getSecret` và `getSessionIdentifier`; các tùy chọn khác có giá trị mặc định:

[[CODE:8]]

> warning **Warning** Như ghi chú trong [tài liệu csrf-csrf](https://github.com/Psifi-Solutions/csrf-csrf?tab=readme-ov-file#getting-started), middleware này yêu cầu session middleware hoặc `cookie-parser` phải được khởi tạo trước. `doubleCsrf()` cũng trả về một hàm sinh ra các token mà route của bạn trao cho client. Vui lòng tham khảo tài liệu để biết thêm chi tiết.

##### Fastify

Cài package [@fastify/csrf-protection](https://github.com/fastify/csrf-protection):

[[CODE:9]]

Sau đó đăng ký nó như một Fastify plugin:

[[CODE:10]]

> warning **Warning** Như giải thích trong [tài liệu @fastify/csrf-protection](https://github.com/fastify/csrf-protection#usage), plugin này yêu cầu một storage plugin (`@fastify/cookie`, `@fastify/session` hoặc `@fastify/secure-session`) phải được đăng ký trước.
