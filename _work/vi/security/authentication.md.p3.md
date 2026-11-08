#### Thêm "Đăng nhập bằng Google"

Trong Google Cloud console, tạo một OAuth client ID loại **Web application**, và thêm redirect URI được phép sau (cùng URI production, khi bạn deploy):

[[CODE:62]]

Thêm thông tin xác thực của client vào `.env`, cạnh `APP_URL`:

[[CODE:63]]

Lần đầu tiên ai đó đăng nhập bằng Google, ứng dụng của bạn phải quyết định tài khoản Google đó thuộc về tài khoản local nào. Hãy lưu liên kết dưới dạng một cặp (provider, subject), trong đó subject là id ổn định mà Google gán cho tài khoản. Email có thể thay đổi; subject thì không. Thêm một bảng identity vào repository:

[[CODE:64]]

Package hỏi một `OidcAccountResolver` để đưa ra quyết định đó:

[[CODE:65]]

Liên kết theo email đòi hỏi cả hai bên đều đã xác minh địa chỉ:

- **Google phải đã xác minh nó** (`profile.emailVerified`). Nếu không, bất kỳ ai cũng có thể tạo một tài khoản Google bằng địa chỉ của khách hàng và chiếm tài khoản của họ ở cửa hàng. Trả về `null` sẽ từ chối việc đăng nhập với lỗi 403.
- **Tài khoản ở cửa hàng cũng phải đã xác minh nó** (`existing.emailVerified`). Nếu không, ai đó có thể đăng ký trước bằng địa chỉ của khách hàng với mật khẩu do họ chọn, và vẫn giữ quyền truy cập khi khách hàng đăng nhập bằng Google. Đây gọi là account pre-hijacking. Một tài khoản tạo bằng mật khẩu sẽ ở trạng thái chưa xác minh cho đến khi chủ sở hữu mở [link xác minh](/security/authentication#verify-email-addresses), hoặc [đặt lại mật khẩu](/security/authentication#reset-forgotten-passwords). Cho đến lúc đó, nó nhận lỗi 403 yêu cầu khách hàng đăng nhập bằng mật khẩu rồi kết nối Google từ tài khoản của họ.

Kết nối Google vào một tài khoản mà khách hàng đang đăng nhập thì không cần khớp email gì cả. Package gọi đây là luồng link: nút "Kết nối Google" của web app trỏ tới `GET /auth/oidc/google/login?link=true`. Package chỉ bắt đầu luồng này với một session đã đăng nhập đầy đủ, và không bắt đầu từ trang của site khác (trường hợp đó nhận lỗi 403): một lần link sẽ gắn bất kỳ tài khoản Google nào đang đăng nhập trên trình duyệt này. Ở callback, nó kiểm tra chính session đó vẫn còn sống, rồi gọi `resolveUser()` với `linkTo` là người dùng đang đăng nhập. Resolver liên kết tài khoản Google với họ, trừ khi nó đã thuộc về một khách hàng khác. Session vẫn giữ nguyên, và trình duyệt được redirect tới `redirectTo`.

Bật OpenID Connect bằng preset `google()` và URL mà Google gửi trình duyệt quay về. `:provider` đại diện cho tên của provider, nên một route callback phục vụ được mọi provider bạn thêm vào:

[[CODE:66]]

Các route là của bạn, nên chúng nằm cùng các route khác, dưới prefix, version và giới hạn tốc độ của bạn. `OidcService.start()` tạo redirect tới Google còn `finish()` xử lý callback; một controller cung cấp hai cái này ra ngoài:

[[CODE:67]]

- `GET /auth/oidc/google/login?redirectTo=/orders` redirect trình duyệt tới Google. Nút "Đăng nhập bằng Google" của web app là một link thông thường tới đây. `start()` dùng authorization code flow với PKCE, một `state` và một `nonce`. Giao dịch đăng nhập được lưu phía server dưới `state`, còn trình duyệt nhận một secret có hash SHA-256 chính là `state`, trong một cookie `HttpOnly` tên `__Host-oidc_tx`, có hiệu lực 10 phút.
- `GET /auth/oidc/google/callback` là nơi Google gửi trình duyệt quay về. `finish()` kiểm tra `state` trong query có phải là hash của secret trong cookie của trình duyệt hay không (nên không ai có thể hoàn tất một lần đăng nhập mà họ không bắt đầu trên trình duyệt này, kể cả với một URL callback đọc được từ log hay lịch sử trình duyệt), đổi code lấy token, xác minh chữ ký của ID token với các key mà Google công bố, và kiểm tra issuer, audience, thời hạn và nonce của nó. Nếu không liên lạc được với Google, hoặc Google trả về một endpoint không phải https, câu trả lời là 502, không phải 401. Sau đó nó gọi `resolveUser()`, đăng nhập người dùng thông qua `SignInService` (nên khách hàng có authenticator sẽ nhận một session pending), và trả về redirect tới `redirectTo`, hoặc tới `/`. Chỉ đường dẫn tương đối mới được chấp nhận làm `redirectTo`, nên luồng đăng nhập không thể bị biến thành open redirect.
- Cả hai đều đọc request và đặt cookie thông qua HTTP adapter của Nest, và trả về thứ mà `@Redirect()` mong đợi, nên controller chạy được trên cả Express lẫn Fastify, không cần `@Req()` hay `@Res()`.

Đăng ký controller và resolver trong `AuthModule`:

[[CODE:68]]

Preset `github()` hoạt động theo cùng cách. `microsoft()` nhận thêm tenant id của directory làm tùy chọn `tenant`, cạnh `clientId` và `clientSecret`: một GUID lấy từ trang Overview của Microsoft Entra admin center, như `process.env.ENTRA_TENANT_ID`. Một domain, hoặc các giá trị multi-tenant `common`, `organizations` và `consumers`, sẽ lỗi lúc khởi động: với những giá trị đó, Microsoft công bố một issuer khác với issuer được yêu cầu, và mọi lần đăng nhập sẽ thất bại. Hãy thêm chúng cạnh `google` trong `providers`, và đăng ký URL callback với từng provider, thay `google` bằng tên của nó.

Một ứng dụng phục vụ dưới nhiều domain, như mỗi khách hàng một domain, không thể chỉ định một URL callback duy nhất: một lần đăng nhập bắt đầu trên domain nào thì phải quay về domain đó. Thay vào đó, hãy truyền một hàm nhận request làm `callbackUrl`. `start()` gọi nó khi bắt đầu đăng nhập, và `finish()` gọi lại nó ở callback, nên nó phải trả về cùng một URL cho cả hai. Hãy so sánh host với danh sách domain của riêng bạn thay vì tin vào header, và đăng ký mọi URL mà hàm có thể trả về với từng provider:

[[CODE:69]]

Hàm này cũng có thể là `async`, để tra cứu domain trong database. Bất cứ thứ gì nó throw ra đều là câu trả lời cho lần đăng nhập, như lỗi 404 ở trên cho một domain mà ứng dụng không phục vụ, và một URL không phải tuyệt đối sẽ làm lần đăng nhập thất bại với lỗi nêu tên hàm. Cookie `__Host-oidc_tx` thuộc về domain đã đặt nó, nên một lần đăng nhập kết thúc trên domain nơi nó bắt đầu. Nếu hàm lỡ trả về một URL khác ở callback, provider sẽ từ chối code, và callback nhận lỗi 401. Đằng sau một proxy viết lại host, hãy đọc header mà nó chuyển tiếp, như `X-Forwarded-Host`, và chỉ từ proxy mà bạn tin tưởng.

Một số ứng dụng chỉ biết được các provider của mình lúc runtime. Một ứng dụng bán cho doanh nghiệp có thể cấp cho mỗi khách hàng một OIDC client riêng, hoặc cho họ mang identity provider của riêng mình, được thiết lập từ trang admin và lưu trong database. Thay vào đó, hãy truyền một hàm nhận tên provider làm `providers`. `start()` gọi nó khi bắt đầu đăng nhập, và `finish()` gọi lại nó ở callback. Hãy trả về cấu hình của provider, hoặc `undefined` với tên mà bạn không phục vụ, trường hợp này nhận lỗi 404:

[[CODE:70]]

Cấu hình được tra lại ở callback thay vì lưu cùng lần đăng nhập, nên một secret bạn xoay vòng trong database sẽ được dùng ngay từ lần gọi tiếp theo, kể cả với một lần đăng nhập đang diễn ra. Mỗi cấu hình mà hàm trả về đều được kiểm tra giống như dạng object được kiểm tra lúc khởi động: một cấu hình không có `clientId`, hoặc không có `clientSecret` trừ khi `tokenEndpointAuthMethod` của nó là `'none'`, sẽ làm lần đăng nhập thất bại với lỗi nêu tên hàm. Hàm chạy ở mỗi lần đăng nhập và callback, nên hãy cache việc tra cứu nếu nó chậm. Package cache tài liệu discovery và key của mỗi provider theo issuer, nên các khách hàng đăng nhập qua cùng một provider sẽ dùng chung chúng.

Identity được liên kết theo (provider, subject), và provider là cái tên, nên mỗi tên phải đại diện cho một client của một provider. Hãy đưa khách hàng vào trong tên, như `acme` ở trên, thay vì dùng một tên, như `okta`, cho provider của mọi khách hàng: provider của hai khách hàng có thể cấp ra cùng một subject. Khi khách hàng mang identity provider của riêng họ, còn hai điều nữa thay đổi:

- **Provider của họ bảo đảm cho bất kỳ địa chỉ nào nó muốn.** Nó có thể đánh dấu bất kỳ địa chỉ nào là đã xác minh, kể cả địa chỉ của người dùng thuộc khách hàng khác. Resolver ở trên liên kết tài khoản theo email đã xác minh. Với provider do khách hàng của bạn kiểm soát, chỉ liên kết theo email với các tài khoản của chính khách hàng đó, hoặc không liên kết theo email gì cả.
- **Issuer là dữ liệu người dùng nhập vào.** Package tải tài liệu discovery, key và token từ các URL mà cấu hình chỉ định, và không có gì ngăn những request đó đi vào mạng nội bộ của bạn. Hãy kiểm tra issuer mà khách hàng nhập vào với danh sách provider bạn hỗ trợ trước khi lưu nó.

#### Thêm đăng nhập bằng magic link

Một magic link đăng nhập khách hàng từ hộp thư của họ, không cần mật khẩu. Package tạo và kiểm tra các link; việc gửi chúng đi là việc của bạn, thông qua một `MagicLinkHandler`. Cửa hàng gửi chúng qua email giống như link xác minh, với template và mail class riêng:

[[CODE:71]]

[[CODE:72]]

Bật magic link: handler trong `AuthModule`, và URL mà các link trỏ tới trong tùy chọn:

[[CODE:73]]

[[CODE:74]]

`MagicLinkService.create()` tạo một token ngẫu nhiên 256 bit, có hiệu lực 15 phút và chỉ dùng được một lần, rồi truyền link cho handler của bạn. Nó lưu hash SHA-256 của token kết hợp với một secret mà chỉ cookie giao dịch của trình duyệt này giữ (xem bên dưới), nên một link đọc được từ log, hoặc bị chuyển tiếp, sẽ không tìm thấy gì, kể cả với một cookie giả mạo. Với `bindToBrowser: false`, nó chỉ lưu hash của riêng token. Token được thêm vào URL dưới dạng query parameter `token`, và code của bạn không bao giờ nhìn thấy nó theo cách nào khác.

Hãy trỏ link tới một trang của web app, không phải tới API. Trang đó đọc token từ URL của nó và POST ngược lại. Các trình quét email và trình xem trước link đi theo link trong email bằng request GET, và sẽ dùng hết token trước khi khách hàng kịp click. Trang phải nằm cùng site với API: việc xin link sẽ đặt một cookie mà trình duyệt gửi kèm token.

[[CODE:75]]

- Route xin link trả lời 202 bất kể địa chỉ có tài khoản hay không, và tài khoản chỉ được tạo khi link được dùng. Một request gửi từ trang của site khác sẽ nhận lỗi 403, giống như đăng nhập: nếu không, trang đó có thể đặt cookie giao dịch của trình duyệt này cho một link tới địa chỉ của tác giả trang, rồi lừa khách hàng mở nó (login CSRF).
- `consume()` hủy token, gọi `resolveUser()`, và đăng nhập người dùng thông qua `SignInService`, thứ đặt cookie, nên xác thực hai lớp vẫn được áp dụng. `resolveUser()` trả về tài khoản cùng `email` đã lưu của nó, và link chỉ đăng nhập tài khoản nếu đó đúng là địa chỉ mà link được gửi tới, so sánh sau khi trim, chuyển chữ thường và chuẩn hóa Unicode NFC. Một phép tra cứu bỏ qua dấu hoặc dấu chấm, như collation mặc định của MySQL làm, không thể trao tài khoản của khách hàng này cho một hộp thư khác: thay vào đó `consume()` trả về `null`.
- Một link chỉ dùng được trên trình duyệt đã xin nó. `create()` đặt một cookie giao dịch, `__Host-magic_link_tx`, và `consume()` từ chối token nếu không có cookie này, trước khi tra cứu bất cứ thứ gì: nó throw một `MagicLinkError`, và module trả lời bằng lỗi 401 có `error` là `not_this_browser` cùng thông báo yêu cầu khách hàng mở link mới nhất trên trình duyệt mà họ đã xin link, hoặc xin link mới ở đây. Nếu không, bất kỳ ai cũng có thể xin một link cho địa chỉ của chính họ rồi lừa khách hàng mở nó, khiến trình duyệt của khách hàng đăng nhập vào tài khoản của kẻ tấn công (login CSRF). Link bị từ chối vẫn có hiệu lực trên trình duyệt đã xin nó, và câu trả lời không để lộ gì về token, vì một token bịa ra cũng nhận cùng câu trả lời. Cookie giữ năm link gần nhất mà trình duyệt đã xin, nên một khách hàng bấm "Gửi lại" rồi mở email đầu tiên vẫn đăng nhập được; một link cũ hơn năm link đó cũng nhận lỗi 401 tương tự. Vì vậy một khách hàng xin link trên laptop rồi mở email trên điện thoại sẽ được bảo mở nó trên laptop, hoặc xin link mới trên điện thoại, link đó khi ấy sẽ dùng được trên điện thoại; một ứng dụng muốn bản thân link dùng được trên điện thoại thì đặt `bindToBrowser: false` trong tùy chọn `magicLink`. Link không tồn tại, đã dùng hoặc đã hết hạn, và các địa chỉ bị handler từ chối, đều nhận cùng một câu trả lời chung từ controller: `consume()` trả về `null` cho tất cả, và chỉ có event `magic-link-refused` cho biết đó là trường hợp nào.
- Việc dùng link chứng minh luôn địa chỉ, nên tài khoản tạo bằng link là đã xác minh. Một tài khoản tạo bằng mật khẩu thì khác khi địa chỉ của nó chưa được xác minh: link chứng minh ai đang sở hữu địa chỉ lúc này, chứ không chứng minh ai đã chọn mật khẩu, nên handler từ chối nó với lỗi 403 thay vì trao một tài khoản đã bị pre-hijack cho chủ sở hữu. Khi chủ sở hữu đã dùng [link xác minh](/security/authentication#verify-email-addresses), hoặc [đặt lại mật khẩu](/security/authentication#reset-forgotten-passwords), magic link cũng dùng được cho tài khoản đó.
- `redirectTo` chỉ được giữ qua vòng đi về nếu nó là một đường dẫn tương đối, như `/orders`.

Với schema Zod:

[[CODE:76]]

Đăng ký controller:

[[CODE:77]]

#### Cho khách hàng quản lý session

Session nằm trên server, nên khách hàng có thể xem họ đang đăng nhập ở đâu và kết thúc bất kỳ session nào trong số đó. Để phân biệt các session, hãy ghi lại trình duyệt mà mỗi session thuộc về. `session.metadata` chạy mỗi khi khách hàng đăng nhập, bằng mật khẩu, bằng Google hay bằng magic link, và những gì nó trả về được lưu cùng session mới:

[[CODE:78]]

Sau đó liệt kê các session, và kết thúc chúng:

[[CODE:79]]

- Session id là hash SHA-256 của token trong cookie. Hiển thị chúng cho chủ sở hữu là an toàn, vì không thể suy ra cookie từ id. `revoke()` nhận cả người dùng lẫn id, và chỉ kết thúc session thuộc về người dùng đó, nên một id lấy từ URL không thể kết thúc session của khách hàng khác.
- `sign-out` là `@Public()`, giống như `verify` trong [xác thực hai lớp](/security/authentication#add-two-factor-authentication), nên một khách hàng chưa bao giờ hoàn tất yếu tố thứ hai vẫn đăng xuất được. `signOut()` kết thúc session trong cookie của trình duyệt này và xóa cookie. Nó trả về `false` khi không có session nào, và route trả lời 401: một bearer token ở đây không đăng xuất gì cả.
- `signOutEverywhere()` kết thúc mọi session và, khi ứng dụng có cấp, mọi refresh token của người dùng, rồi xóa cookie của trình duyệt này. Các access token đã cấp vẫn còn hiệu lực cho đến khi hết hạn, đó là lý do chúng chỉ sống 15 phút.

App mobile đăng xuất khỏi một thiết bị bằng cách thu hồi refresh token của nó. Thêm một route vào `TokensController`. `TokenService.revoke()` kết thúc family của token: chính token đó, các token trước và các token kế tiếp của nó:

[[CODE:80]]

Đăng ký controller. Đây là module hoàn chỉnh, với mọi credential provider và handler của bài hướng dẫn:

[[CODE:81]]

Hãy xoay vòng session mỗi khi quyền hạn thay đổi, ví dụ sau khi đổi mật khẩu hoặc khi một khách hàng trở thành nhân viên: `SignInService.rotateSession()` cấp cho session của trình duyệt này một id mới, và đặt cookie mới; `completeMfa()` vốn đã làm việc này. Nó resolve ra `null`, và không đặt cookie, khi trình duyệt không có session hoặc đã mất session trong lúc đó: do đăng xuất khỏi mọi nơi, đặt lại mật khẩu, hoặc một request khác đã xoay vòng nó trước.

#### Giới hạn tốc độ đăng nhập

`@nestjs/authentication` không giới hạn tốc độ request. Đó là việc của `@nestjs/throttler`, một package riêng:

[[CODE:82]]

Chỉ giới hạn theo địa chỉ IP là quá thô cho việc đăng nhập. Các khách hàng đằng sau cùng một địa chỉ mạng dùng chung nó, nên giới hạn không thể đủ thấp để ngăn một client đoán mật khẩu của một tài khoản. Hãy dùng hai [định nghĩa throttler](/security/rate-limiting#multiple-throttler-definitions); mỗi request được tính vào cả hai. `default` đếm theo địa chỉ IP, trên mọi route. `account` đếm theo email và địa chỉ IP, ở bất cứ đâu request body chỉ định một tài khoản:

[[CODE:83]]

Đăng ký `ThrottlerModule` với cả hai định nghĩa, và `ThrottlerGuard` làm global guard:

[[CODE:84]]

Guard chạy trước validation, nên `accountEmail()` kiểm tra `email` có phải là chuỗi hay không. `normalizeIp()` gom các địa chỉ IPv6 theo prefix `/64` của chúng, giống như tracker của chính throttler làm, nên một client không thể có bộ đếm mới cho mỗi địa chỉ trong subnet của nó.

Guard được đăng ký trong root module, nên nó chạy trước authentication guard. Global guard chạy theo thứ tự module, và root module đứng đầu. Điều đó có nghĩa là các bearer token đoán mò cũng bị tính vào giới hạn, thay vì chỉ bị từ chối với lỗi 401.

Cuối cùng, siết chặt giới hạn trên các route kiểm tra mật khẩu hoặc gửi email. Mỗi `@Throttle()` đếm theo route, và đặt cả hai giới hạn: theo địa chỉ IP, và theo tài khoản:

[[CODE:85]]

[[CODE:86]]

[[CODE:87]]

[[CODE:88]]

`Throttle`, `SkipThrottle`, `minutes` và `hours` được import từ `@nestjs/throttler`. Giới hạn theo địa chỉ IP là chuyện cân nhắc, vì văn phòng và nhà mạng di động đặt nhiều khách hàng sau một địa chỉ. Giới hạn `account` áp dụng cho mọi route có `email` trong request body, ở mức 5 request mỗi 15 phút trừ khi route tự đặt giới hạn riêng; `@SkipThrottle({{ '{' }} account: true {{ '}' }})` loại một route ra.

- `forgot` đếm theo địa chỉ, bất kể địa chỉ IP, nên không ai có thể làm đầy hộp thư của khách hàng bằng link đặt lại mật khẩu, dù từ một hay nhiều địa chỉ IP. Ai đó dùng hết giới hạn này chỉ làm chậm request của chính khách hàng: các link họ gây ra đều được gửi tới khách hàng, và link nào cũng dùng được.
- Request xin magic link giữ email và địa chỉ IP đi cùng nhau. Một link chỉ dùng được trên trình duyệt đã xin nó, nên chỉ giới hạn theo địa chỉ sẽ cho phép bất kỳ ai dùng hết lượt link của khách hàng từ trình duyệt của chính họ, và ngăn khách hàng đăng nhập.
- Đăng ký mỗi lần dùng một địa chỉ mới, nên nó bỏ qua giới hạn `account` và để giới hạn theo địa chỉ IP làm việc. Nếu không, một khách hàng có mật khẩu không đạt quy tắc đăng ký vài lần sẽ bị từ chối.

Các mã xác thực hai lớp không cần throttle riêng: package khóa các mã của một tài khoản sau 5 lần sai, từ bất kỳ địa chỉ IP, route hay transport nào. `POST /auth/password/reset` cũng vậy: một token đoán mò chỉ tốn một lần tra cứu, và có tới 2^256 token.

> info **Hint** Đằng sau một load balancer hoặc reverse proxy, mọi request dường như đều đến từ proxy. Hãy bật `trust proxy`, như mô tả trong phần [Proxy](/security/rate-limiting#proxies) của throttler, để tracker thấy được địa chỉ của client.
