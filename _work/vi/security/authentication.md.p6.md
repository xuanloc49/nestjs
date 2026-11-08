#### Tham khảo

##### Tùy chọn module

`AuthenticationModule.forRoot()` nhận các tùy chọn này, và factory của `forRootAsync()` trả về chúng, ngoại trừ `isGlobal` và `globalGuard`, hai tùy chọn này vẫn nằm ở cấp cao nhất. Thời gian sống tính bằng mili giây, hoặc chuỗi như `'30s'`, `'15m'` và `'14d'`, tối đa 100 năm; giá trị dài hơn sẽ lỗi lúc khởi động. Mọi nhóm tùy chọn có liên quan tới đồng hồ đều nhận thêm `now`, một hàm trả về số mili giây epoch, dùng cho test.

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `isGlobal` | `true` | Đăng ký module ở cấp global. |
| `globalGuard` | `true` | Đăng ký `AuthenticationGuard` làm global guard. Với `false`, các route vẫn mở cho đến khi chúng dùng `@UseGuards(AuthenticationGuard)`. |
| `allowInMemoryStorage` | `false` | Khởi động với `NODE_ENV=production` khi một hợp đồng mà tính năng cần dùng chưa có store. Xem [Giữ session và token trong database của bạn](/security/authentication#keep-sessions-and-tokens-in-your-database). |
| `session.cookieName` | `__Host-sid` | Tên session cookie; là `sid` khi `cookie` không cho phép prefix `__Host-`. |
| `session.absoluteTtl` | `'7d'` | Thời gian sống tối đa của một session, bất kể nó hoạt động nhiều thế nào. |
| `session.idleTtl` | `'1d'` | Thời gian chờ khi không hoạt động, được gia hạn khi có hoạt động. `0` để tắt. |
| `session.touchInterval` | `'1m'` | Tần suất tối đa ghi hoạt động vào store. Phải ngắn hơn `idleTtl`, trừ khi nó là `0`: giá trị dài hơn sẽ lỗi lúc khởi động, vì người dùng đang hoạt động sẽ bị đăng xuất như thể không hoạt động. |
| `session.cookie` | `secure: true`, `sameSite: 'lax'`, `path: '/'` | Các thuộc tính cookie: `secure`, `sameSite`, `path`, `domain`. `HttpOnly` luôn được đặt. |
| `session.trustedOrigins` | không có | Các origin khác mà trang của chúng được phép dùng session cookie để ghi và đăng nhập. |
| `session.metadata` | không có | Một hàm nhận request đăng nhập, kết quả của nó được lưu cùng mỗi session mới. Xem [Cho khách hàng quản lý session](/security/authentication#let-customers-manage-their-sessions). |
| `password.logN` | `17` | Logarit cơ số 2 của chi phí scrypt N, một số nguyên từ 10 tới 22. `r` (mặc định `8`, tối đa 32), `p` (`1`, tối đa 16), `keyLength` (`32`) và `saltLength` (`16`, cả hai từ 16 tới 64) đặt các tham số còn lại. Một lần hash có thể tốn tối đa 1 GiB bộ nhớ (128·N·r byte) và gấp 16 lần khối lượng công việc mặc định (N·r·p), nên với `r` là 8, `logN` dừng ở 20. |
| `accessToken.key` | bắt buộc | Secret HS256 dài ít nhất 32 byte, hoặc một private key cho RS256, ES256 hay EdDSA, dưới dạng text PEM hoặc `KeyObject`. Một JWK hoặc key DER sẽ lỗi lúc khởi động: hãy import nó bằng `createPrivateKey()`. Xem [Cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app). |
| `accessToken.alg` | theo key | Thuật toán ký: HS256 với secret, thuật toán của chính key với private key. |
| `accessToken.issuer`, `audience` | không có | Các claim `iss` và `aud`, được ghi vào và kiểm tra trên mọi token. |
| `accessToken.ttl` | `'15m'` | Thời gian sống của access token. |
| `accessToken.kid`, `type` | không có, `JWT` | Các header `kid` và `typ`. |
| `refreshToken` | bật khi có `accessToken` | `false` chỉ cấp access token, không có refresh token và không cần `RefreshTokenStore`. Xem [Cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app). |
| `refreshToken.ttl` | `'30d'` | Thời gian sống của một refresh token. |
| `refreshToken.absoluteTtl` | `'90d'` | Thời gian sống tối đa của một family refresh token, bất kể nó được xoay vòng bao nhiêu lần. |
| `mfa.encryption` | bắt buộc | `keys`, danh sách các key AES-256-GCM, mới nhất trước, cùng `migratePlaintext` (mặc định `false`); hoặc `false` để lưu secret dạng plaintext. Xem [Thêm xác thực hai lớp](/security/authentication#add-two-factor-authentication). |
| `mfa.issuer` | không có | Cái tên mà app authenticator hiển thị. |
| `mfa.window` | `1` | Số step 30 giây được chấp nhận ở mỗi phía của thời điểm hiện tại, một số nguyên từ 0 tới 10. |
| `mfa.maxAttempts` | `5` | Số mã sai được phép trong mỗi `lockoutWindow` trước khi mọi mã bị từ chối, một số nguyên ít nhất là 1. |
| `mfa.lockoutWindow` | `'15m'` | Khoảng thời gian dùng để đếm số mã sai. |
| `mfa.recoveryCodes` | `10` | Số mã khôi phục mỗi lô, một số nguyên ít nhất là 1. |
| `mfa.pendingTtl` | `'10m'` | Thời gian một session được phép chờ yếu tố thứ hai. |
| `emailVerification.url` | bắt buộc | Trang mà link xác minh mở ra. `ttl` mặc định là `'24h'`. Xem [Xác minh địa chỉ email](/security/authentication#verify-email-addresses). |
| `passwordReset.url` | bắt buộc | Trang mà link đặt lại mật khẩu mở ra. `ttl` mặc định là `'1h'`. Xem [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords). |
| `magicLink.url` | bắt buộc | Trang mà magic link mở ra. `ttl` mặc định là `'15m'`. Xem [Thêm đăng nhập bằng magic link](/security/authentication#add-magic-link-sign-in). |
| `magicLink.bindToBrowser` | `true` | Chỉ chấp nhận link trên trình duyệt đã xin nó. |
| `magicLink.cookie` | `secure: true` | Các thuộc tính của cookie giao dịch `__Host-magic_link_tx`. |
| `oidc.callbackUrl` | bắt buộc | URL callback công khai, với `:provider` thay cho tên provider, hoặc một hàm nhận request và trả về URL đó. Xem [Thêm "Đăng nhập bằng Google"](/security/authentication#add-sign-in-with-google). |
| `oidc.providers` | bắt buộc | Cấu hình provider theo tên, như `google()`, `github()` và `microsoft()` (cái sau nhận thêm id `tenant` của directory), hoặc một hàm nhận tên và trả về cấu hình. Xem [Thêm "Đăng nhập bằng Google"](/security/authentication#add-sign-in-with-google). |
| `oidc.redirectAfterLogin` | `/` | Nơi đến khi lần đăng nhập không có `redirectTo`. |
| `oidc.transactionTtl` | `'10m'` | Thời gian tối đa một lần đăng nhập được phép kéo dài giữa redirect và callback. |
| `oidc.cookie` | `secure: true` | Các thuộc tính của cookie giao dịch `__Host-oidc_tx`. |
| `oidc.discoveryTtl`, `clockTolerance` | `'1h'`, `'30s'` | Thời gian một tài liệu discovery được tin cậy, và độ lệch cho phép với các claim thời gian của ID token. |

Các tính năng `emailVerification`, `passwordReset`, `magicLink` và `oidc` còn cần một handler cùng tên đã đăng ký; có cái này mà thiếu cái kia sẽ lỗi lúc khởi động. Một giá trị nằm ngoài các khoảng ở trên cũng vậy, kể cả `NaN` mà `Number()` tạo ra từ một biến môi trường chưa được đặt.

##### Tùy chọn route

`@Authenticate()` nhận các tùy chọn này, trên class hoặc method:

| Tùy chọn | Mô tả |
| --- | --- |
| `optional` | Cho người gọi ẩn danh đi qua, với người dùng là `null`. Thông tin xác thực sai vẫn nhận lỗi 401. |
| `mfa` | Yêu cầu yếu tố thứ hai đã xác minh: một session đã xác minh, hoặc một JWT có `amr` chứa `mfa`, `otp` hoặc `hwk`. API key không bao giờ thỏa mãn được. Xem [Thêm xác thực hai lớp](/security/authentication#add-two-factor-authentication). |
| `verifiedEmail` | Yêu cầu địa chỉ email đã xác minh, nếu không trả lời 403 với `email_unverified`. Xem [Đọc người dùng hiện tại](/security/authentication#read-the-current-user). |
| `providers` | Chỉ những class provider này, hoặc class con của chúng, mới được xác thực route. |

##### API key

`ApiKeyProvider` nhận các tùy chọn này trong `super()`. Xem [Cấp API key cho đối tác](/security/authentication#issue-api-keys-to-partners).

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `prefix` | bắt buộc | Phần mở đầu của mọi key, như trong `cat_<id>_<secret>`: từ 1 tới 16 chữ cái thường và chữ số, bắt đầu bằng một chữ cái. |
| `realm` | `api` | Realm trong challenge `WWW-Authenticate`. |

Class con của bạn implement `findKey(id)`, method này trả về `hash` đã lưu của key, `user` và `expiresAt` của nó, hoặc `null` với key không tồn tại, đã bị thu hồi, hoặc có chủ sở hữu không còn nữa. `generate()` trả về một key mới dưới dạng `key`, chỉ hiển thị một lần, cùng `id` và `hash` để lưu. Với một request dùng key, session là `keyId` và `expiresAt` của key, với `method` đặt là `api-key`.

##### Event

`AuthenticationEvents` công bố mỗi event trên observable `events$` của nó, và trên diagnostics channel `nestjs:authentication:<type>`, như `nestjs:authentication:sign-in`.

| Loại | Payload | Khi nào |
| --- | --- | --- |
| `sign-in` | `userId`, `sessionId` hoặc `tokenFamilyId`, `method`, `mfa`, `metadata` | `SignInService.signIn()` hoặc `TokenService.issue()` đã đăng nhập một người dùng |
| `sign-out` | `userId`, `sessionId`, `tokenFamilyId` hoặc `everywhere` | Một session, một family refresh token, hoặc tất cả đã kết thúc |
| `mfa-verified` | `userId`, `method` (`totp` hoặc `recovery-code`) | Một mã đã được chấp nhận |
| `mfa-failed` | `userId`, `method`, `failures`, `locked` | Một mã bị từ chối, kể cả trong thời gian bị khóa |
| `mfa-enabled` | `userId`, `replaced` | Một authenticator đã được xác nhận |
| `mfa-disabled` | `userId` | Authenticator và mã khôi phục đã bị xóa |
| `recovery-codes-generated` | `userId`, `count` | Một lô mã khôi phục mới đã thay thế lô cũ |
| `refresh-token-reused` | `userId`, `tokenFamilyId` | Một refresh token đã dùng quay lại, và family của nó đã bị thu hồi |
| `password-reset-requested` | `email`, `userId` (không có với địa chỉ không tồn tại) | Ai đó đã xin link đặt lại mật khẩu |
| `password-reset` | `userId` | Một link đặt lại đã đặt mật khẩu mới |
| `email-verified` | `userId`, `email` | Một link xác minh đã được dùng |
| `magic-link-refused` | `reason` (`not-this-browser`, `unknown`, `expired` hoặc `refused`), `email` | Một magic link không đăng nhập được ai |
| `session-touch-failed` | `userId`, `sessionId`, `error` | `SessionStore.touchSession()` thất bại; request vẫn tiếp tục, và mốc hạn idle của session không thay đổi |

##### Lỗi

`AuthenticationError` là class cha của các lỗi trong package. Nó mang `status`, và tùy chọn `code`, `details` và `challenge` (header `WWW-Authenticate`). Khi được throw từ một handler hoặc bất cứ thứ gì handler gọi, nó trở thành HTTP exception của chính Nest, `UNAUTHENTICATED` của GraphQL, một `WsException` hoặc một `RpcException`. `code` của nó chính là `errorCode` của Nest. Qua HTTP và GraphQL, nó được đặt trên exception, nên một exception filter đọc được `exception.errorCode`, và Nest đưa nó vào body, hoặc vào `extensions.originalError` với GraphQL. Payload ws và rpc mang cùng key `errorCode`. Một lời từ chối có kèm message cũng gửi code dưới dạng `error`, như trước giờ vẫn vậy. `details`, một object thuần, được gửi nguyên vẹn dưới dạng `details`; không gì khác của lỗi (`cause`, stack) đến được client. Ví dụ, `new AuthenticationError('Too many attempts', options)` với `too_many_attempts` làm `code` và `retryAfter: 30` trong `details` sẽ trả lời:

[[CODE:136]]

| Lỗi | Status | `errorCode` | `error` | Khi nào |
| --- | --- | --- | --- | --- |
| `AuthenticationError` | 401 | `code` của nó, nếu có | `code` của nó; nếu không thì là `Unauthorized` khi có message, không có gì khi không có message | Thông tin xác thực sai, hoặc `requireUser()` khi không có người dùng (không message, không code) |
| `JwtError` | 401 | không có | `Unauthorized` | Một token sai định dạng, chữ ký không hợp lệ, đã hết hạn, hoặc thuộc issuer hay audience khác |
| `RefreshTokenError` | 401 | không có | `Unauthorized` | Một refresh token không hợp lệ, đã hết hạn hoặc bị dùng lại; `reason` cho biết trường hợp nào |
| `MagicLinkError` | 401 | `not_this_browser` | `not_this_browser` | Một magic link được mở trên trình duyệt khác với trình duyệt đã xin nó, hoặc sau khi trình duyệt đó đã xin thêm năm link mới hơn |
| `MfaAlreadyEnrolledError` | 409 | không có | `Conflict` | `enroll()` không có `replace: true` cho người dùng đã xác nhận authenticator |

Khi không provider nào nhận ra thông tin xác thực nào, guard trả lời 401 với `missing_credentials`, và không có `error`:

[[CODE:137]]

Điều đó bao gồm request không có thông tin xác thực, session cookie cũ hoặc không tồn tại (được tính như không có, để các route tùy chọn vẫn hoạt động), và thông tin xác thực mà `providers` của route không chấp nhận. Guard và `TokenService.issue()` cũng trả lời 401 với `mfa_required` khi còn thiếu yếu tố thứ hai, và 403 với `email_unverified` trên các route `verifiedEmail`, mỗi trường hợp đều dưới dạng cả `errorCode` lẫn `error`. Các route OIDC trả lời 400 với callback sai hoặc giả mạo, 401 khi câu trả lời của provider không qua được bước xác minh hoặc luồng link không có session đã đăng nhập, 403 khi resolver từ chối tài khoản hoặc luồng link được bắt đầu từ site khác, 404 với tên provider chưa được cấu hình, và 502 khi không liên lạc được với provider hoặc provider bị cấu hình sai, như một endpoint không phải https hay một bộ key không load được. `SignInService.signIn()` và `MagicLinkService.create()` trả lời 403 với request được gửi từ một origin khác.
