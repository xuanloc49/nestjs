### Cookie

Một **HTTP cookie** là một mẩu dữ liệu nhỏ mà trình duyệt của người dùng lưu lại. Cookie được thiết kế như một cơ chế tin cậy để website ghi nhớ thông tin có trạng thái. Khi người dùng truy cập lại website, trình duyệt tự động gửi cookie kèm request.

Kể từ NestJS v12.1, Nest hỗ trợ cookie có sẵn. Cùng một API hoạt động trên mọi HTTP adapter (Express, Fastify, hoặc adapter của riêng bạn kế thừa `AbstractHttpAdapter`), và không cần cài thêm package nào:

- các decorator tham số `@Cookies()` và `@SignedCookies()` đọc các cookie được gửi kèm request
- các method `setCookie()` và `clearCookie()` của HTTP adapter ghi các header `Set-Cookie` của response
- tùy chọn ứng dụng `cookies` bật signed cookie, có hỗ trợ xoay vòng secret

Các ứng dụng đang dùng `cookie-parser` hoặc `@fastify/cookie` vẫn tiếp tục chạy mà không cần thay đổi. Xem [Dùng cookie-parser hoặc @fastify/cookie](#using-cookie-parser-or-fastifycookie) để biết hai cách tiếp cận tương tác với nhau như thế nào.

#### Đọc cookie

Dùng decorator `@Cookies()` để lấy cookie từ request gửi đến. Truyền tên cookie để lấy một cookie duy nhất, hoặc bỏ qua để lấy mọi cookie dưới dạng một object có key là tên cookie.

[[CODE:1]]

> info **Hint** Import decorator `@Cookies()` từ package `@nestjs/common`.

Một cookie có tên nhưng không được gửi sẽ resolve ra `undefined`. Nest chỉ parse header `Cookie` khi có tham số yêu cầu cookie, và tối đa một lần cho mỗi request. Giá trị được percent-decode, và khi cùng một tên xuất hiện nhiều lần, lần xuất hiện đầu tiên sẽ thắng (trình duyệt gửi cookie có path cụ thể nhất trước).

Giống như với `@Query()` hay `@Param()`, bạn có thể truyền [pipe](/pipes) sau tên cookie:

[[CODE:2]]

Với cách này, một cookie `cartSize=abc` sẽ dẫn tới response `400 Bad Request`, và một cookie bị thiếu cũng vậy, trừ khi bạn bật tùy chọn `optional` của pipe.

> info **Hint** Pipe nhận các tham số cookie với thuộc tính `type` của `ArgumentMetadata` đặt là `'custom'`. Do đó, một `ValidationPipe` global sẽ bỏ qua chúng trừ khi bạn bật tùy chọn `validateCustomDecorators` của nó.

> warning **Warning** `@Cookies()` không xác minh chữ ký. Các giá trị của nó đến thẳng từ client và có thể đã bị giả mạo, nên hãy đọc mọi giá trị cần tin cậy bằng `@SignedCookies()` thay vào đó (xem [Ký cookie](#signing-cookies)).

#### Đặt và xóa cookie

Cookie được ghi thông qua HTTP adapter, adapter này cung cấp hai method cho việc đó:

- `setCookie(response, name, value, options?)` thêm một header `Set-Cookie` vào response
- `clearCookie(response, name, options?)` thêm một header `Set-Cookie` làm cookie hết hạn ngay lập tức

Cả hai method đều nhận response object gốc làm tham số đầu tiên. Trong một route handler, hãy inject `HttpAdapterHost` (xem [HTTP adapter](/faq/http-adapter)) và lấy response object bằng decorator `@Res()`, có bật tùy chọn `passthrough`:

[[CODE:3]]

> warning **Warning** Để framework lo phần logic xử lý response, hãy đặt tùy chọn `passthrough` thành `true`, như ở trên. Xem phần [cách dùng riêng của library](/controllers#library-specific-approach) trong chương Controllers để biết chi tiết.

Controller không bao giờ cần biết type của response object: `setCookie()` nhận bất cứ thứ gì nền tảng bên dưới cung cấp (một `Response` của Express, một `FastifyReply`, v.v.), giúp code không phụ thuộc nền tảng. Mỗi lời gọi thêm một header `Set-Cookie` riêng, nên mọi cookie được đặt trong lúc xử lý một request đều được gửi đi, trên mọi nền tảng. Vì các method này chỉ cần response object, bạn cũng có thể gọi chúng từ một guard hay interceptor, bằng `context.switchToHttp().getResponse()`.

> info **Hint** `setCookie()` và `clearCookie()` là các member tùy chọn của interface `HttpServer`. `AbstractHttpAdapter` implement chúng một lần, dựa trên method `appendHeader()` của nó, nên mọi adapter kế thừa nó (kể cả `ExpressAdapter` và `FastifyAdapter`) đều hỗ trợ chúng.

Giá trị của cookie phải là chuỗi. Nó luôn được percent-encode bằng `encodeURIComponent()` (và được `@Cookies()` decode lại), nên lưu bất kỳ chuỗi nào cũng an toàn. Hãy tự chuyển đổi các type khác, ví dụ bằng `JSON.stringify()`.

Tham số `options` (interface `CookieSerializeOptions`, export từ `@nestjs/common`) nhận các thuộc tính sau:

| Tùy chọn      | Mô tả                                                                                                                                   | Mặc định  |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `path`        | Thuộc tính `Path`.                                                                                                                      | `'/'`     |
| `domain`      | Thuộc tính `Domain`. Phải là một host name hợp lệ, có thể có dấu chấm ở đầu. Khi bỏ qua, cookie chỉ dành cho host hiện tại.            | không đặt |
| `maxAge`      | Thuộc tính `Max-Age`, tính bằng **giây**. Phải là số nguyên.                                                                            | không đặt |
| `expires`     | Thuộc tính `Expires`, dưới dạng `Date`. Trình duyệt ưu tiên `maxAge` khi cả hai đều được đặt.                                          | không đặt |
| `httpOnly`    | Thuộc tính `HttpOnly`. Ẩn cookie khỏi JavaScript phía client.                                                                           | `false`   |
| `secure`      | Thuộc tính `Secure`. Trình duyệt chỉ gửi cookie qua HTTPS.                                                                              | `false`   |
| `sameSite`    | Thuộc tính `SameSite`: `'strict'`, `'lax'` hoặc `'none'`. `'none'` yêu cầu `secure: true`.                                              | không đặt |
| `partitioned` | Thuộc tính `Partitioned` (CHIPS). Yêu cầu `secure: true`.                                                                               | `false`   |
| `priority`    | Thuộc tính `Priority` (không chuẩn, được Chromium tôn trọng): `'low'`, `'medium'` hoặc `'high'`.                                        | không đặt |
| `signed`      | Ký giá trị bằng secret đầu tiên đã cấu hình. Xem [Ký cookie](#signing-cookies).                                                        | `false`   |

Ngoài `path`, không thuộc tính nào có giá trị mặc định, kể cả `httpOnly`, khớp với hành vi của Express và `@fastify/cookie`. Với cookie mang thông tin xác thực hoặc định danh session, hãy đặt tường minh `httpOnly`, `secure` và `sameSite`.

> warning **Warning** `maxAge` được tính bằng **giây**, như trong RFC 6265 và `@fastify/cookie`. Method `res.cookie()` của Express nhận `maxAge` tính bằng **mili giây**, nên một giá trị mang nguyên từ đó sang sẽ khiến cookie sống lâu gấp 1000 lần. Với một ngày, hãy truyền `60 * 60 * 24`.

`clearCookie()` ghi một cookie rỗng với `Max-Age=0` và một ngày `Expires` trong quá khứ. Trình duyệt chỉ xóa cookie khi `path` và `domain` khớp với lúc nó được đặt, nên hãy truyền cùng các giá trị cho cả hai method. Vì `path` mặc định là `/` ở cả hai, `clearCookie(res, 'theme')` sẽ xóa một cookie đặt bằng `setCookie(res, 'theme', value)`. Các tùy chọn `maxAge`, `expires` và `signed` bị `clearCookie()` bỏ qua.

#### Ký cookie

Một signed cookie mang một chữ ký HMAC bên cạnh giá trị của nó, giúp server phát hiện client có giả mạo nó hay không. Để bật việc ký, hãy truyền một secret qua tùy chọn `cookies` của method `NestFactory.create()`:

[[CODE:4]]

Sau đó, đặt cookie với tùy chọn `signed` và đọc lại bằng decorator `@SignedCookies()`:

[[CODE:5]]

> info **Hint** Import decorator `@SignedCookies()` từ package `@nestjs/common`.

`@SignedCookies('uid')` resolve ra giá trị gốc, chưa ký, khi chữ ký được xác minh. Khi cookie bị thiếu, không được ký, đã bị giả mạo, hoặc được ký bằng một secret không được cấu hình, nó resolve ra `undefined`. Khi gọi không kèm tên, `@SignedCookies()` trả về một object chỉ chứa những cookie có chữ ký được xác minh. Giống như `@Cookies()`, nó nhận pipe sau tên cookie.

Việc ký sẽ báo lỗi rõ ràng khi không có secret nào được cấu hình: `setCookie()` với tùy chọn `signed` sẽ throw lỗi, và việc resolve một tham số `@SignedCookies()` cũng vậy (trừ khi `cookie-parser` cung cấp signed cookie, xem [bên dưới](#using-cookie-parser-or-fastifycookie)), dẫn tới response `500 Internal Server Error` thay vì mọi signed cookie đều âm thầm đọc ra `undefined`. Một secret rỗng (chuỗi rỗng, mảng rỗng, hoặc mảng có một mục rỗng) sẽ throw khi tạo ứng dụng.

> warning **Warning** Một `secret` là `undefined`, ví dụ vì một biến môi trường chưa được đặt, được tính như hoàn toàn không có secret. Ứng dụng vẫn khởi động, và lỗi chỉ lộ ra khi một request đặt hoặc đọc signed cookie. Hãy validate cấu hình lúc khởi động, ví dụ như mô tả trong chương [Cấu hình](/application/configuration#schema-validation).

> warning **Warning** Việc ký bảo vệ tính toàn vẹn của cookie, không bảo vệ tính bí mật của nó: giá trị được lưu dạng plaintext, và client đọc được nó. Đừng lưu dữ liệu nhạy cảm trong signed cookie. Ngoài ra, cũng như với package `cookie-signature`, tên cookie không nằm trong dữ liệu được ký, nên một giá trị ký cho cookie này vẫn xác minh được khi client gửi nó dưới một tên khác.

##### Xoay vòng secret

Để thay một secret mà không làm vô hiệu hóa các cookie đã ký bằng nó, hãy truyền một mảng secret. Nest ký cookie mới bằng secret đầu tiên và xác minh cookie gửi đến với tất cả các secret:

[[CODE:6]]

Để xoay vòng, hãy thêm secret mới vào đầu mảng, và bỏ secret cũ khi mọi cookie ký bằng nó đã hết hạn. Chữ ký được so sánh trong thời gian không đổi, và với mọi secret, nên thời gian phản hồi không để lộ secret nào đã khớp.

##### Định dạng chữ ký

Nest ký cookie theo định dạng của package `cookie-signature`, định dạng mà `cookie-parser` và `express-session` cũng dùng: prefix `s:`, theo sau là giá trị, một dấu chấm, và digest HMAC-SHA256 của giá trị dưới dạng base64, không có padding. Kết quả là:

- các cookie ký bằng cùng secret bởi Express (tùy chọn `signed` của `res.cookie()`), `cookie-parser` hoặc `express-session` vẫn tiếp tục xác minh được sau khi bạn chuyển sang API có sẵn, và `cookie-parser` có thể xác minh cookie do Nest ký
- các giá trị ký bởi `@fastify/cookie`, vốn bỏ prefix `s:`, cũng xác minh được. Chiều ngược lại thì không: method `unsignCookie()` của `@fastify/cookie` không thể xác minh cookie do Nest ký, vì có prefix `s:`

#### Tên và thuộc tính không hợp lệ

`setCookie()` và `clearCookie()` từ chối đầu vào không hợp lệ thay vì escape nó, nên cả tên cookie lẫn thuộc tính đều không thể chèn thêm thuộc tính hay header thông qua các ký tự `;`, CR hoặc LF. Chúng throw một `TypeError` khi:

- tên không phải một token RFC 7230 hợp lệ (ví dụ chứa dấu cách, `;`, `=` hoặc ký tự điều khiển)
- `path` chứa `;`, hoặc một ký tự nằm ngoài ASCII in được
- `domain` không phải một host name hợp lệ (dấu chấm ở đầu được cho phép)
- `maxAge` không phải số nguyên, hoặc `expires` không phải một `Date` hợp lệ
- `sameSite` hoặc `priority` không phải một trong các giá trị được phép
- `sameSite` là `'none'`, hoặc `partitioned` là `true`, trong khi `secure` không phải `true`. Trình duyệt âm thầm bỏ qua những cookie như vậy, nên Nest báo lỗi thay vào đó
- giá trị không phải chuỗi

Nội dung của giá trị không bao giờ bị từ chối: vì nó được percent-encode, một `;`, CR hoặc LF trong giá trị sẽ trở thành `%3B`, `%0D` hoặc `%0A`.

Những lỗi này không phải HTTP exception, nên khi một lỗi được throw từ route handler, client nhận response `500 Internal Server Error`. Nếu tên cookie hoặc thuộc tính đến từ dữ liệu người dùng nhập vào, hãy validate nó trước khi gọi `setCookie()`.

> info **Hint** Nest không áp dụng các quy tắc của prefix tên cookie `__Host-` và `__Secure-`. Nếu bạn dùng chúng, hãy tự đặt các thuộc tính mà chúng yêu cầu: `secure: true` cho cả hai, cộng thêm `path: '/'` và không có `domain` cho `__Host-`.

#### Dùng cookie-parser hoặc @fastify/cookie

Trước khi có hỗ trợ sẵn, việc đọc cookie cần middleware `cookie-parser` (Express) hoặc plugin `@fastify/cookie` (Fastify). Các ứng dụng dùng chúng vẫn tiếp tục chạy, và các decorator có sẵn hợp tác với chúng:

- `@Cookies()` trả về nguyên `req.cookies` mỗi khi một middleware hoặc plugin đã điền nó, và chỉ tự parse header `Cookie` trong trường hợp ngược lại. Vì vậy hành vi của package đó được giữ nguyên. Ví dụ, `cookie-parser` chuyển signed cookie từ `req.cookies` sang `req.signedCookies` khi nó được cung cấp secret, và biến các cookie JSON có prefix `j:` thành object.
- Khi tùy chọn ứng dụng `cookies.secret` được đặt, `@SignedCookies()` luôn xác minh header `Cookie` thô với các secret của Nest, và bỏ qua `req.signedCookies`. Hãy cấu hình cùng secret (hoặc các secret) như middleware của bạn, để các cookie mà nó đã ký vẫn tiếp tục xác minh được.
- Không có tùy chọn `cookies.secret`, `@SignedCookies()` quay về dùng object `req.signedCookies` do `cookie-parser` điền (khi nó được cung cấp secret), và xem các cookie mà nó đánh dấu là không hợp lệ như bị thiếu. `@fastify/cookie` không điền `req.signedCookies`, nên trên Fastify, `@SignedCookies()` yêu cầu tùy chọn `cookies.secret`.

Nest không bao giờ tự gán `req.cookies`. Nếu bạn bỏ `cookie-parser` hoặc `@fastify/cookie`, hãy thay mọi đoạn code đọc `request.cookies` (hoặc gọi `reply.setCookie()`) bằng các decorator và method adapter có sẵn. Tương tự, nếu ứng dụng của bạn tự định nghĩa decorator `@Cookies()` bằng `createParamDecorator()`, bạn có thể thay nó bằng decorator có sẵn. Khi thay các lời gọi `res.cookie()` bằng `setCookie()`, nhớ chuyển `maxAge` từ mili giây sang giây.

##### Express (cookie-parser)

Đầu tiên, cài package [cookie-parser](https://github.com/expressjs/cookie-parser) (và các type của nó, với người dùng TypeScript):

[[CODE:7]]

Sau khi cài xong, áp dụng middleware `cookie-parser` ở cấp global (ví dụ trong file `main.ts`):

[[CODE:8]]

Tham số đầu tiên là một secret tùy chọn (hoặc một mảng secret) dùng để xác minh signed cookie. Middleware parse header `Cookie` và cung cấp các cookie dưới dạng `req.cookies` và, nếu có cung cấp secret, các signed cookie đã xác minh dưới dạng `req.signedCookies` (một signed cookie không qua được bước xác minh có giá trị `false`). Xem [repository cookie-parser](https://github.com/expressjs/cookie-parser) để biết các tùy chọn khác.

Khi đã có những thứ trên, bạn có thể đọc cookie bằng các decorator `@Cookies()` và `@SignedCookies()`, hoặc từ request object:

[[CODE:9]]

Để gắn cookie vào response gửi đi, dùng method `setCookie()` của adapter hoặc method `Response#cookie()`:

[[CODE:10]]

> info **Hint** Import các decorator `@Req()` và `@Res()` từ package `@nestjs/common`, còn `Request` và `Response` từ package `express`.

##### Fastify (@fastify/cookie)

Đầu tiên, cài package cần thiết:

[[CODE:11]]

Sau khi cài xong, đăng ký plugin `@fastify/cookie`:

[[CODE:12]]

Khi đã có những thứ trên, bạn có thể đọc cookie bằng decorator `@Cookies()`, hoặc từ request object:

[[CODE:13]]

Để gắn cookie vào response gửi đi, dùng method `setCookie()` của adapter hoặc method `FastifyReply#setCookie()` (xem [tài liệu @fastify/cookie về việc gửi cookie](https://github.com/fastify/fastify-cookie#sending)):

[[CODE:14]]

> info **Hint** Import các decorator `@Req()` và `@Res()` từ package `@nestjs/common`, còn `FastifyRequest` và `FastifyReply` từ package `fastify`.
