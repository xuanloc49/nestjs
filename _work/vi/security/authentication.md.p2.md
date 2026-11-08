#### Đọc người dùng hiện tại

`@CurrentUser()` inject người dùng mà `validate()` đã load:

[[CODE:36]]

`@CurrentUser('id')` inject một thuộc tính duy nhất. `@CurrentSession()` inject thứ mà provider xem là session: ở đây là bản ghi session đã lưu.

> info **Hint** Tùy chọn: hãy cho package biết type người dùng của bạn một lần, và các type của nó sẽ đi theo. Mở rộng interface `AuthenticationTypes` của `@nestjs/authentication` trong một khối `declare module`, với `user: User` (bài hướng dẫn đặt nó trong `src/auth/auth-types.ts`). Từ đó trở đi `@CurrentUser('key')` chỉ nhận các key của `User` và có type trả về đúng thuộc tính đó, `AuthenticationContext.user` và `.session` cũng có type tương ứng. Một key `sessionExtra` gán type cho `SessionRecord.extra`, thứ mà session store đọc kèm theo mỗi session (được export dưới tên `SessionExtra`, là `unknown` nếu không có key này). Nó không gán type cho chính tham số: một parameter decorator không quyết định được annotation, nên `user: User` vẫn phải đặt trên tham số. Và đây là một type người dùng duy nhất cho toàn ứng dụng, nên một ứng dụng có hai loại chủ thể thì vẫn giữ các annotation. Cùng interface đó nhận `refreshTokens: false` cho một ứng dụng [tắt refresh token](/security/authentication#issue-tokens-to-the-mobile-app).

[[CODE:37]]

Controller không phải là code duy nhất cần người dùng. Đơn hàng thuộc về khách hàng đã đặt chúng, và `OrdersService` đọc khách hàng đó từ `AuthenticationContext`, nên controller không cần truyền người dùng xuống:

[[CODE:38]]

[[CODE:39]]

[[CODE:40]]

`@Authenticate()` với `verifiedEmail: true` chỉ cho khách hàng đã xác minh địa chỉ đặt hàng. Bất kỳ ai khác đã đăng nhập sẽ nhận lỗi 403 có `error` là `email_unverified`, báo cho web app biết cần yêu cầu khách hàng mở [link xác minh](/security/authentication#verify-email-addresses), hoặc gửi lại link. Đây là 403 chứ không phải 401: đăng nhập lại cũng không giúp gì. `GET /orders` không có yêu cầu này. Mặc định guard đọc `emailVerified` từ người dùng mà `validate()` đã load; `EmailVerificationHandler` của bạn có thể ghi đè `isVerified(user)` nếu type người dùng của bạn lưu thông tin này theo cách khác.

[[CODE:41]]

Thêm `OrdersModule` vào `imports` của `AppModule`:

[[CODE:42]]

`AuthenticationContext` là một singleton. Nó đọc người dùng của request hiện tại từ một `AsyncLocalStorage` mà module mở ra bao quanh mỗi handler, nên nó cho kết quả đúng ở mọi thứ mà handler gọi hoặc await, bất kể có bao nhiêu request chạy cùng lúc. `requireUser()` trả về người dùng, hoặc throw một `AuthenticationError`, thứ mà module trả lời bằng lỗi 401 trên mọi transport. Bên ngoài request, trong một queue consumer hay cron job, `AuthenticationContext` là rỗng, và method `run()` của nó chạy một hàm với tư cách một người dùng cụ thể. Nó cũng rỗng trong middleware, guard và exception filter, vì chúng chạy bên ngoài handler.

#### Cấp token cho app mobile

App mobile của cửa hàng xác thực bằng bearer token thay vì cookie. Nó gửi một JWT access token ngắn hạn trong header `Authorization`, và gia hạn nó bằng một refresh token dài hạn.

Thêm một signing secret vào `.env`. Nó phải dài ít nhất 32 byte. Không có nó, ứng dụng sẽ từ chối khởi động, kèm thông báo nêu tên tùy chọn: `accessToken.key` is required.

[[CODE:43]]

Ứng dụng vừa cấp vừa xác minh access token, nên hãy mô tả chúng một lần, bằng tùy chọn `accessToken`. Key dùng để ký chúng, còn issuer, audience và thời gian sống được đưa vào mọi token và được kiểm tra ở mọi request:

[[CODE:44]]

Với một secret làm key, token được ký bằng HS256. Credential provider thứ hai xác minh chúng. `JwtBearerProvider` đọc header `Authorization`, kiểm tra chữ ký với key `accessToken`, cùng `exp`, `iss` và `aud`, rồi truyền các claim đã xác minh cho `validate()` của bạn:

[[CODE:45]]

> info **Hint** HS256 với một secret dùng chung phù hợp với API vừa cấp vừa xác minh token của chính nó. Nếu các service khác cũng xác minh chúng, hãy dùng một private key ES256 làm key `accessToken`: khi đó `JwtAuth` xác minh bằng nửa public của nó, và các service kia cũng vậy. Để chấp nhận token từ một issuer khác, hãy truyền cho `super()` URL `jwks` của nó, URL này phải là https (http thường chỉ được phép trên localhost), hoặc `key` public của nó, cùng `issuer` và `audience`: cả hai đều bắt buộc, vì một identity provider ký token của mọi client bằng cùng các key. Với token không có audience, hãy truyền `audience: false` và kiểm tra claim định danh client của bạn trong `validate()`. Thêm `clockTolerance: '30s'` để bù đồng hồ của issuer khác. Key là text PEM hoặc một `KeyObject`; để import một JWK, dùng `createPublicKey()` từ `node:crypto`, truyền JWK làm `key` và `'jwk'` làm `format`. Một `key` hoặc `jwks` rỗng, như một biến môi trường chưa đặt, sẽ lỗi lúc khởi động thay vì quay về dùng tùy chọn `accessToken`. Một service chỉ xác minh token có thể bỏ hẳn `accessToken` và truyền cho `super()` thứ nó dùng để xác minh: `key` dùng chung, hoặc `jwks` cùng `issuer` và `audience`.

Cung cấp nó trong `AuthModule`:

[[CODE:46]]

Với mỗi request, guard hỏi các provider theo `order` tăng dần, và provider đầu tiên trả về người dùng sẽ thắng. `SessionAuth` đăng ký với order mặc định là `0`, còn `JwtAuth` yêu cầu `1`, nên một request có session cookie sẽ được `SessionAuth` đăng nhập, còn một request có bearer token, vốn không có cookie, nhận `null` từ `SessionAuth` và được `JwtAuth` xử lý. Thứ tự được chỉ định lúc đăng ký thay vì phụ thuộc vào thứ tự Nest tạo các provider: thứ tự đó đi theo module graph, và thay đổi khi một provider chuyển sang module khác hoặc có thêm một câu import. Hai provider yêu cầu cùng một order sẽ lỗi lúc khởi động, kèm tên cả hai. Một request không có cái nào sẽ nhận lỗi 401 với `errorCode` là `missing_credentials`; header `WWW-Authenticate` của nó liệt kê những gì các provider chấp nhận: `Bearer realm="store"`. Một token không qua được bước xác minh sẽ nhận lỗi 401 nêu rõ lý do, như RFC 6750 mô tả, ví dụ `error="invalid_token", error_description="token expired"`. Điều đó báo cho app mobile biết cần refresh.

Giờ là các endpoint cấp token:

[[CODE:47]]

`TokenService.issue()` ký một access token với tùy chọn `accessToken`, khởi tạo một refresh token, và trả về cả hai, kèm `expiresIn`, thời gian sống của access token tính bằng giây. Refresh token là opaque (không đọc được nội dung), và được lưu dưới dạng hash. Mỗi token chỉ dùng được một lần: `refresh()` dùng hết nó và trả về token kế tiếp, cùng một access token mới. Các token kế tiếp của một lần đăng nhập tạo thành một family. Nếu một token đã dùng quay lại, nghĩa là có hai bên cùng giữ nó, một kẻ trộm và app, nên service sẽ thu hồi cả family và cả hai đều phải đăng nhập lại. Một refresh token không tồn tại, đã hết hạn hoặc bị dùng lại sẽ throw `RefreshTokenError`, một `AuthenticationError`, thứ mà module trả lời bằng lỗi 401, nên `refresh` không cần tự xử lý lỗi.

Claim `amr` ghi lại cách người dùng đã đăng nhập, và [xác thực hai lớp](/security/authentication#add-two-factor-authentication) dựa vào nó. `issue()` lưu các `claims` cùng family refresh token, và `refresh()` đưa chúng vào mọi access token mà nó tạo ra, nên các token đã refresh mô tả cùng một lần đăng nhập. Đừng đưa những thông tin có thể thay đổi, như role, vào `claims`: chúng sẽ nằm trong token suốt thời gian family còn sống. Thay vào đó, `validate()` load người dùng hiện tại ở mọi request.

Một service ký access token ngắn hạn và để client đăng nhập lại có thể tắt refresh token. Khi `refreshToken` đặt thành `false`, `issue()` chỉ trả về `accessToken` và `expiresIn`, và không lưu gì cả, nên ứng dụng không cần `RefreshTokenStore`. Response của token endpoint không có refresh token: client đăng nhập lại khi access token hết hạn. `refresh()` và `revoke()` sẽ throw, báo rằng refresh token đã bị tắt, còn `revokeAll()` không làm gì cả. Yếu tố thứ hai và claim `amr` vẫn hoạt động như trước. Hãy khai báo cả `refreshTokens: false` trên `AuthenticationTypes`, để `issue()` có type trả về là `AccessTokenResult` thay vì `TokenPair`:

[[CODE:48]]

[[CODE:49]]

Tùy chọn mới là thứ quyết định hành vi lúc chạy; phần khai báo chỉ để báo cho trình biên dịch. Một ứng dụng đặt tùy chọn mà không khai báo sẽ không nhận refresh token lúc runtime nhưng type vẫn là chuỗi, và `refresh()` sẽ throw khi gặp nó. Đặt `refreshToken` thành `false` mà không có `accessToken` sẽ không thay đổi gì, và log một cảnh báo lúc khởi động.

Đăng ký controller:

[[CODE:50]]

#### Thêm xác thực hai lớp

Khách hàng có thể bảo vệ tài khoản bằng một app authenticator (mật khẩu dùng một lần theo thời gian, hay TOTP). Cấu hình `mfa` trong `AppModule`:

[[CODE:51]]

Server phải đọc lại được TOTP secret để kiểm tra mã, nên khác với mật khẩu, nó không thể bị hash. `MfaService` mã hóa mỗi secret bằng AES-256-GCM trước khi đưa vào lưu trữ, gắn với người dùng của nó, và chỉ giải mã khi cần xác minh mã. Ai có bản sao database nhưng không có key sẽ không tạo được mã. Key là bắt buộc: cấu hình `mfa` mà không có `encryption` sẽ throw lúc khởi động. (`encryption: false` cố ý lưu dạng plaintext, dành cho test.) Một secret ngắn hơn 128 bit sẽ không bao giờ xác minh được: `enroll()` tạo secret 160 bit, nhưng secret import từ hệ thống khác có thể ngắn hơn, và người dùng của chúng phải đăng ký lại.

Thêm key vào `.env`. Một key dạng chuỗi phải có ít nhất 32 ký tự dữ liệu ngẫu nhiên:

[[CODE:52]]

> info **Hint** Để xoay vòng key, hãy đặt key mới lên đầu trong `keys` và giữ key cũ phía sau. Key đầu tiên dùng để mã hóa, mọi key được liệt kê đều dùng để giải mã, và secret sẽ được mã hóa lại bằng key mới khi chúng được dùng. Hãy bỏ key cũ khi không còn gì dùng nó. Key không cần tên: mỗi secret đã mã hóa ghi lại một id suy ra từ key của nó.

Xác thực hai lớp bị tắt trừ khi `mfa` được cấu hình. Không có nó, `MfaService.isEnrolled()` trả lời `false` mà không đọc store, nên đăng nhập không bao giờ hỏi mã, và mọi method khác của `MfaService` đều throw `MFA is not configured` trước khi đụng tới lưu trữ. Bỏ `mfa` khỏi tùy chọn sẽ tắt xác thực hai lớp cho mọi khách hàng, kể cả những người đã đăng ký authenticator.

Các endpoint MFA đăng ký authenticator, xác nhận nó, và hoàn tất một lần đăng nhập:

[[CODE:53]]

- `enroll()` lưu một secret mới, chưa xác nhận, và trả về nó cùng một URI `otpauth://` mà web app hiển thị dưới dạng mã QR. Khi một authenticator đã được xác nhận, `enroll()` từ chối ghi đè nó và throw `MfaAlreadyEnrolledError`, thứ mà module trả lời bằng lỗi 409, `Authenticator already enrolled`. Ghi đè nó sẽ tắt xác thực hai lớp cho đến khi authenticator mới được xác nhận.
- `replace` xử lý trường hợp đổi điện thoại mới. `enroll()` với `replace: true` chuẩn bị sẵn một secret thứ hai, và authenticator hiện tại vẫn hoạt động cho đến khi `confirm()` nhận được mã từ authenticator mới. `@Authenticate()` với `mfa: true` khiến route yêu cầu yếu tố thứ hai đã xác minh, nên chỉ một mật khẩu bị đánh cắp không thể tráo authenticator của người khác vào.
- `SignInService.confirmMfa()` kích hoạt authenticator khi nó tạo ra một mã hợp lệ, nên một secret bị gõ sai không thể khóa ai bên ngoài. Mã đó cũng chứng minh trình duyệt này có authenticator, nên session trở thành đã xác minh, dưới một cookie mới: khách hàng có thể dùng ngay các route yêu cầu yếu tố thứ hai, mà không cần đăng nhập lại. Một lần xác nhận gửi bằng bearer token, vốn không có session, chỉ kích hoạt authenticator. Mười mã khôi phục mà route trả về chỉ được hiển thị đúng một lần này, và được lưu dưới một hash chậm có salt là id của khách hàng, nên một bản sao database không làm lộ chúng.
- Khi một authenticator đã được xác nhận, `SignInService.signIn()` tạo session ở trạng thái **pending** cho người dùng đó. Một session pending không đăng nhập ở đâu cả: các route cần người dùng sẽ trả lời 401 với `"errorCode": "mfa_required"`, báo cho web app biết cần hỏi mã. Đó là lý do `verify` là `@Public()`. `completeMfa()` đọc session từ cookie của trình duyệt này, kiểm tra một mã hoặc mã khôi phục, rồi xoay session sang một id mới với `mfa: 'verified'`, đặt cookie mới. Một session pending hết hạn sau 10 phút (`mfa.pendingTtl`), không phải sau 14 ngày của `session.absoluteTtl`: một cookie pending chỉ là một nửa thông tin xác thực. Xác minh mã xong thì session có đầy đủ thời gian sống.
- `completeMfa()` chỉ làm việc với session cookie. Một request có bearer token mà không có cookie sẽ nhận lỗi 401.
- Mã được chấp nhận trong khoảng 30 giây trước và sau thời điểm hiện tại, và mỗi mã chỉ dùng được một lần. Sau 5 lần nhập sai mã trong 15 phút, tài khoản sẽ từ chối mọi mã, kể cả mã đúng, cho đến khi hết khoảng thời gian đó. Mỗi lần thử được đếm trước khi kiểm tra, nên gửi các lần đoán song song không lách được giới hạn.

Một yếu tố thứ hai đã xác minh cũng có thể được yêu cầu cho từng route riêng lẻ, gọi là step-up authentication. Cửa hàng yêu cầu nó khi đổi địa chỉ email, vì đó là cách một tài khoản được khôi phục. Địa chỉ mới được gửi trong `EmailDto` của phần [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords). Thêm route, với `@Authenticate()`:

[[CODE:54]]

Với schema Zod:

[[CODE:55]]

Mọi route vốn đã yêu cầu người dùng đăng nhập; `@Authenticate()` điều chỉnh cách yêu cầu. Với `mfa: true`, một cookie session chỉ qua được khi đã được xác minh. Một khách hàng chưa đăng ký authenticator không thể qua được, nên web app sẽ yêu cầu họ đăng ký trước.

Địa chỉ mới chưa được xác minh, nên route gửi một link xác minh tới nó, và khách hàng không thể đặt hàng cho đến khi dùng link. Các link đã gửi tới địa chỉ cũ ngừng hoạt động: chúng chỉ xác minh đúng địa chỉ mà chúng được gửi tới.

App mobile không được trở thành cách lách yếu tố thứ hai, và nó không thể: giống như `signIn()`, `TokenService.issue()` không cấp token cho khách hàng đã xác nhận authenticator nếu không có mã. Nó trả lời 401 với `"errorCode": "mfa_required"`, báo cho app biết cần hỏi mã. Khi đó app gửi lại mật khẩu, kèm mã. Thêm mã vào body:

[[CODE:56]]

[[CODE:57]]

Và truyền nó tiếp làm `secondFactor`:

[[CODE:58]]

[[CODE:59]]

Một request không có mã sẽ không bị tính là một lần thử thất bại, nên app có thể tìm hiểu xem nó có cần mã hay không. Một mã đã xác minh sẽ thêm `mfa` vào claim `amr`. `JwtBearerProvider` xem một token có `amr` chứa `mfa`, `otp` hoặc `hwk` là đã xác minh, nên nó qua được các route `mfa: true`. Các token đã refresh mang cùng `amr` như lần đăng nhập đã khởi tạo family của chúng, nên một app mobile đã đăng nhập bằng mã sẽ giữ trạng thái đã xác minh cho đến khi refresh token của nó hết hạn hoặc bị thu hồi. `issue()` không bao giờ nhận ba giá trị đó từ `claims` của chính bạn: nó bỏ chúng đi, kèm một cảnh báo trong log, và chỉ thêm `mfa` khi đã xác minh được mã, nên một ứng dụng không thể vô tình tạo ra một token đã xác minh.

Đăng ký controller:

[[CODE:60]]

##### Tắt xác thực hai lớp

`MfaService.disable()` xóa authenticator và các mã khôi phục của khách hàng, rồi phát ra `mfa-disabled`. Thêm một route vào `MfaController`, với `SessionService` và `TokenService` được inject vào constructor:

[[CODE:61]]

- `@Authenticate()` với `mfa: true` là mức tối thiểu: không có nó, chỉ một mật khẩu bị đánh cắp đã có thể tắt yếu tố thứ hai. Một API key không bao giờ qua được nó. Tuy vậy, nó không chứng minh khách hàng đang ngồi trước bàn phím ngay lúc này: một session giữ trạng thái đã xác minh suốt thời gian sống của nó. Vì vậy route còn yêu cầu thêm một mã. `verifyTotp()` resolve ra `false` với mã sai, được tính vào cùng cơ chế khóa như khi đăng nhập, và mỗi mã chỉ dùng được một lần.
- `disable()` xóa mọi mã khôi phục cùng với authenticator, và bỏ một bản thay thế đã chuẩn bị bằng `replace` mà chưa bao giờ được xác nhận. Đăng ký lại sẽ bắt đầu từ đầu, với một lô mã khôi phục mới.
- `disable()` không đụng tới session và token. Các session đã xác minh khác của khách hàng vẫn sẽ qua được các route `mfa: true`, và các family refresh token của họ cũng vậy, vì `amr` của chúng giữ `mfa` qua mỗi lần refresh. Route kết thúc chúng, chỉ giữ lại session của trình duyệt này. Các access token đã cấp vẫn còn hiệu lực cho đến khi hết hạn. Nếu gửi bằng bearer token, request không có session id nào để giữ lại: mọi session đều kết thúc, và `TokenService.revokeAll()` cũng đăng xuất client đó.
- Một session vẫn đang chờ yếu tố thứ hai không thể hoàn tất, vì không còn authenticator nào để kiểm tra mã. `revokeAll()` kết thúc nó cùng với các session khác.
- Một khách hàng chưa bao giờ xác nhận việc đăng ký thì không có session đã xác minh nào, nên route này từ chối họ. Để hủy một lần đăng ký như vậy, hãy gọi `disable()` từ một route không có yêu cầu đó khi `isEnrolled()` là `false`, hoặc gọi lại `enroll()`.
