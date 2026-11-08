#### Giữ session và token trong database của bạn

Đến giờ, mọi thứ mà package lưu trữ đều nằm trong bộ nhớ: session, refresh token, authenticator và mã khôi phục, cùng các link và lần đăng nhập đang chờ. Chúng sẽ mất khi khởi động lại, và một instance thứ hai của API sẽ không thấy chúng. Package không tự nói chuyện với database của bạn. Nó mô tả những gì nó lưu trữ dưới dạng sáu interface, `SessionStore`, `RefreshTokenStore`, `MfaStore`, `MagicLinkStore`, `OidcStateStore` và `EmailTokenStore`, và ứng dụng của bạn implement chúng bằng cách truy cập database mà nó vốn đã có, rồi đăng ký bản implement đó.

Bước này trình bày bản implement đó hai lần, cho hai ORM mà các bài hướng dẫn trong loạt này dùng: lần đầu với Drizzle, là hướng chính của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối bước, cùng store đó cho ứng dụng dùng ORM là TypeORM. Hãy chọn một trong hai.

Store dùng PostgreSQL với Drizzle, qua [`@nestjs/drizzle`](/data/drizzle), bước này giả định ứng dụng của bạn đã có sẵn nó. `DrizzleModule` mở một pool `pg` từ URL của database và cung cấp database Drizzle, và nó đóng pool khi ứng dụng tắt, sau khi package đã hoàn tất công việc đang dở dang (ví dụ một link đặt lại mật khẩu đang được gửi đi). Thêm URL vào `.env`, và đăng ký module trong `AppModule`:

[[CODE:89]]

[[CODE:90]]

Bắt đầu với các bảng. Chúng là các bảng Drizzle thông thường trong schema của ứng dụng, nằm cạnh các bảng của riêng bạn:

[[CODE:91]]

- Session, token và link được lưu dưới dạng hash SHA-256 của các giá trị trong cookie và email, TOTP secret đến dưới dạng đã mã hóa bằng key của bạn (xem [xác thực hai lớp](/security/authentication#add-two-factor-authentication)), và mã khôi phục đến dưới dạng đã hash bằng scrypt. Không thứ gì trong các bảng này có thể bị dùng lại.
- `revoked` nằm trên từng refresh token thay vì trong một bảng family: một family được tính là đã thu hồi khi bất kỳ token nào của nó bị thu hồi. Điều này bao phủ cả trường hợp một token được lưu sau khi đã thu hồi, bởi một lần refresh bị thua trong cuộc đua.

Sinh migration từ schema, và áp dụng nó:

[[CODE:92]]

Giờ là store. Nó là một provider như mọi provider khác: nó inject database Drizzle, implement sáu interface bằng query builder của Drizzle, và tự đăng ký với `AuthenticationStorage` của package từ constructor của nó:

[[CODE:93]]

Thêm nó vào providers của `AuthModule`, giống như các credential provider và handler. Đăng ký trong constructor là đủ: Nest tạo provider lúc khởi động, trước request đầu tiên.

[[CODE:94]]

Lúc khởi động, sau chuỗi provider và các handler, module log nơi mỗi loại state được lưu:

[[CODE:95]]

- **Một provider hay nhiều provider.** `registerSource()` nhận các interface theo tên, nên một class có thể implement cả sáu, như ở đây, hoặc nhiều class có thể chia nhau: một `RedisSessionStore` đăng ký `sessions`, còn class này đăng ký năm cái còn lại. Một store thứ hai cho cùng một tên sẽ lỗi lúc khởi động, kèm tên cả hai class.
- **Một số method phải là một câu lệnh duy nhất.** Bất cứ thứ gì quyết định một việc chỉ được xảy ra một lần đều là một câu lệnh có điều kiện duy nhất, không bao giờ là đọc rồi ghi. `touchSession()` chỉ cập nhật session còn tồn tại, nên một request chạy đua với việc đăng xuất không thể làm session sống lại. `deleteSession()` resolve ra việc nó có xóa dòng dữ liệu hay không, nên giữa hai lần xoay vòng của cùng một session, hoặc một lần xoay vòng và một lần đăng xuất, chỉ đúng một bên thắng. `markRefreshTokenUsed()`, `claimTotpStep()` và `consumeRecoveryCode()` đếm số dòng đã thay đổi, còn ba method `consume` là một câu `DELETE … RETURNING`. `saveTotp()` giữ time step lớn hơn bằng `greatest()`, nơi duy nhất store phải tự viết SQL. `recordMfaFailure()` insert trước rồi đếm sau, bên ngoài transaction, nên một loạt lần đoán song song không thể cùng thấy một con số thấp. Mỗi method của các interface store đều nêu quy tắc của nó, và cuộc đua mà nó ngăn chặn, trong doc comment.
- **Ghi nhận hoạt động là cố gắng hết sức (best-effort).** Nếu `touchSession()` thất bại (lock timeout, replica chỉ đọc), request và việc đăng xuất vẫn thành công. Session được giữ lại, `lastActiveAt` không thay đổi, và session sẽ chuyển sang trạng thái idle ở mốc hạn cũ trừ khi một request sau đó ghi nhận được hoạt động. Mỗi lần thất bại phát ra event `session-touch-failed`; log chỉ nhận một cảnh báo khi các lỗi bắt đầu, không có gì trong khi chúng tiếp diễn, và một dòng kèm số lần lỗi ở lần touch thành công tiếp theo.
- **Các bảng luôn có giới hạn.** Ai cũng có thể xin magic link hay link đặt lại mật khẩu, nên mỗi lần lưu sẽ xóa những gì đã hết hạn, và khi một bảng vượt quá 100.000 dòng đang chờ, xóa những gì hết hạn sớm nhất. Session và family refresh token đã hết hạn sẽ bị xóa khi có cái mới được ghi.
- **Đặt lại mật khẩu và xác minh email vẫn hoạt động y như cũ.** Link của chúng giờ là các dòng trong `email_tokens`, và các mailer của chúng vẫn gửi chúng qua `@nestjs/mail`.
- **Production từ chối dùng bộ nhớ.** Khi `NODE_ENV` đặt thành `production`, module sẽ không khởi động khi một store mà tính năng đã cấu hình cần dùng chưa được đăng ký, và nêu tên các interface cần implement. Mỗi tính năng chỉ cần các store mà nó dùng: `MfaStore` chỉ khi có `mfa`, và `RefreshTokenStore` chỉ khi có `accessToken` trong lúc refresh token được bật. [Hợp đồng của store](/security/authentication#the-store-contract) liệt kê chúng. Một store mà không tính năng đã cấu hình nào dùng sẽ lỗi ở lần đọc đầu tiên. `allowInMemoryStorage: true` trong tùy chọn module vẫn chạy trong bộ nhớ, nhưng khi đó mỗi lần khởi động lại hay deploy sẽ đăng xuất mọi người và quên các authenticator đã đăng ký, và các instance không chia sẻ gì với nhau.

Nếu người dùng của bạn nằm cùng database, `getSession()` có thể đọc người dùng của mỗi session trong cùng một query và truyền nó tiếp dưới dạng `extra`, thứ mà `validate()` của `SessionAuth` nhận được: một lần đọc mỗi request thay vì hai. Gán type cho nó bằng một key `sessionExtra` cạnh `user` (`users` và `toUser()` đại diện cho bảng của riêng bạn và hàm ánh xạ bỏ đi hash mật khẩu):

[[CODE:96]]

[[CODE:97]]

[[CODE:98]]

`extra` không bao giờ được lưu: `createSession()` không bao giờ nhận nó, một lần xoay vòng bỏ nó đi, và `listUserSessions()` không nên đặt nó. Nó cũng không bị để lộ: `@CurrentSession()`, `request.session` và `AuthenticationContext.session` mang session mà không kèm nó, nên những gì handler cần phải nằm trong người dùng mà `validate()` trả về. Đừng copy người dùng vào dòng session thay vì join: bản sao sẽ bị cũ khi người dùng thay đổi.

Package cung cấp các quy tắc của nó dưới dạng test. `authenticationStoreContract()` từ `@nestjs/authentication/testing` trả về các test case chạy được với mọi test runner, và `concurrent: true` thêm các cuộc đua: refresh song song cùng một token, dùng song song cùng một mã hoặc link, một loạt mã sai, một lần đăng xuất chạy đua với một request, xóa song song cùng một session, và một lần xoay vòng chạy đua với một lần đăng xuất hoặc một lần xoay vòng khác. Hãy chạy chúng trên PGlite và, nơi các lời gọi thực sự chạy đua, trên PostgreSQL:

[[CODE:99]]

`CappedStore` hạ mức trần số dòng đang chờ để `maxPending: 3` kiểm tra được nó. `startPostgres()` là một test helper tạo một database dùng một lần trên PostgreSQL server, hoặc bỏ qua các case PostgreSQL nếu không có server. Một store đọc một dòng rồi ghi ngược lại sẽ qua được các test khác nhưng thất bại ở những test này.

**Với TypeORM.** Cùng store đó cho một ứng dụng dùng ORM là TypeORM, trên cùng tám bảng. Drizzle vẫn là hướng chính của bài hướng dẫn: hãy dùng store này thay cho store ở trên, không phải dùng song song. Các bảng là entity, và mọi cột đều khai báo type của nó, để TypeORM CLI, vốn load chúng mà không có decorator metadata, thấy cùng một schema như ứng dụng:

[[CODE:100]]

TypeORM CLI và `TypeOrmModule` dùng chung một bộ tùy chọn, trong một file data source:

[[CODE:101]]

Sinh migration từ các entity, trên một database đã áp dụng các migration trước đó, áp dụng nó, và kiểm tra entity và database có khớp nhau không. CLI cần một TypeScript loader cho file data source; ở đây dùng `tsx`:

[[CODE:102]]

Migration mà nó viết ra, `1790235914534-Authentication.ts`, gồm các câu lệnh `CREATE TABLE` và `CREATE INDEX` cho tám bảng ở trên, và `migrations` trong data source liệt kê nó. Giờ là store, theo cùng quy tắc như store Drizzle:

[[CODE:103]]

- **Update và delete có điều kiện** đặt điều kiện trong tiêu chí của `update()` và `delete()`, với `LessThan()`, `IsNull()` và `Or()`, và đọc `affected`. Đừng bao giờ dùng `save()`: nó sẽ ghi ngược lại một session mà một lần đăng xuất vừa xóa.
- **`saveTotp()`** giữ time step lớn hơn bằng `GREATEST()` trên dòng bị xung đột, điều mà API upsert không biểu diễn được, nên đây là câu lệnh duy nhất được viết bằng SQL, qua `manager.query()`.
- **Các method `consume`** là delete query builder với `returning('*')`. Nó trả về các dòng thô theo tên cột của database, nên `deleteReturning()` ánh xạ chúng ngược lại thành các thuộc tính entity thông qua entity metadata.
- **`recordMfaFailure()`** là hai câu lệnh trên `dataSource.manager`, mỗi câu được commit riêng, còn `saveRecoveryCodes()` là method duy nhất nằm trong `dataSource.transaction()`.
- **Dùng nó** thay cho store Drizzle: `TypeOrmModule.forRoot(dataSourceOptions)` trong `AppModule` thay cho `DrizzleModule`, và `TypeOrmAuthenticationStore` trong providers của `AuthModule` thay cho `DrizzleAuthenticationStore`. Nó inject `DataSource` mà `TypeOrmModule` cung cấp.

Bộ test hợp đồng chạy trên nó mà không cần sửa gì. TypeORM kết nối qua `pg`, nên bộ test cần một PostgreSQL server và sẽ bị bỏ qua nếu không có. Hai case bổ sung kiểm tra entity và migration có khớp nhau không (thứ mà `migration:generate --check` kiểm tra), và store có đăng ký cho cả sáu hợp đồng khi được cung cấp trong một module hay không:

[[CODE:104]]

> info **Hint** Dùng Prisma? [Hợp đồng của store](/security/authentication#the-store-contract), nằm sau bài hướng dẫn, liệt kê những gì mỗi hợp đồng phải đảm bảo và cách Prisma biểu diễn các method nguyên tử. Hãy test store của bạn với cùng các case đó.

#### Cấp API key cho đối tác

Các trại cứu trợ mèo và cửa hàng thú cưng nhập hàng số lượng lớn từ hệ thống quản lý kho của họ, và một số khách hàng đặt hàng lại bằng script. Một script không thể điền vào form đăng nhập, và một refresh token thay đổi sau mỗi lần dùng không hợp với một job chạy hằng đêm. Thay vào đó, hãy cấp cho họ API key: các secret dài hạn mà khách hàng tạo trong web app và thu hồi khi không cần nữa. Script gửi key của nó dưới dạng bearer token, và hoạt động với tư cách khách hàng đã tạo ra nó.

Package kiểm tra các key, còn database của bạn lưu giữ chúng. Thêm một bảng vào schema:

[[CODE:105]]

Sinh migration cho nó, và áp dụng (output đã được rút gọn):

[[CODE:106]]

Credential provider thứ ba kế thừa `ApiKeyProvider`, và chỉ làm một việc: tìm key theo id của nó.

[[CODE:107]]

Một key có dạng `cat_<id>_<secret>`: prefix, một id công khai gồm 16 ký tự hex, và một secret gồm 256 bit ngẫu nhiên. `findKey()` tra cứu id, còn provider lo phần còn lại. Nó so sánh SHA-256 của toàn bộ key với `hash` đã lưu, trong thời gian không đổi và với cùng khối lượng công việc cho một id không tồn tại, và từ chối key kể từ thời điểm `expiresAt`. Một hàm hash chậm như scrypt của mật khẩu sẽ không thêm được gì ở đây, vì không ai đoán được 256 bit ngẫu nhiên, và nó sẽ làm chậm mọi request. Một key sai, đã hết hạn hoặc bị thu hồi sẽ nhận lỗi 401 với `error="invalid_token"`, giống như một access token không hợp lệ.

`JwtAuth` đọc cùng header `Authorization`. Một JWT luôn chứa hai dấu chấm còn một key thì không có dấu nào, nên `JwtAuth` để các key cho `ApiKeyAuth`, bất kể cái nào chạy trước. Một request không có thông tin xác thực vẫn chỉ nhận một challenge duy nhất, `Bearer realm="store"`, vì cả hai provider dùng chung realm.

Giờ là các endpoint tạo, liệt kê và thu hồi key:

[[CODE:108]]

- `generate()` trả về key, id và hash của nó. Bảng lưu id và hash, nên `create` là lần duy nhất ai đó nhìn thấy key. Một khách hàng làm mất key thì thu hồi nó và tạo key khác.
- Controller chỉ chấp nhận `SessionAuth`, nên key được quản lý từ web app. Dưới `providers`, thông tin xác thực của mọi provider khác đều được tính như không có: một key bị lộ không thể tạo thêm key, hay thu hồi key của chủ sở hữu nó.
- Key hết hạn sau một năm, để một key bị quên không dùng được mãi mãi. Xóa dòng dữ liệu của một key sẽ thu hồi nó kể từ request tiếp theo.

Đăng ký cả hai trong `AuthModule`:

[[CODE:109]]

Một key đăng nhập chủ sở hữu của nó trên mọi route không chỉ định provider, kể cả `POST /orders`. Nó không bao giờ được tính là yếu tố thứ hai: `PATCH /me/email` trả lời nó bằng `mfa_required`, giống như trả lời một session chưa qua bước nhập mã. Để giới hạn một route chỉ cho key, hoặc chặn key khỏi route đó, hãy liệt kê các provider mà route chấp nhận trong `@Authenticate()`. Trong một handler, `@CurrentSession()` chứa `keyId` của key, với `method` đặt là `api-key`, nên một audit log có thể cho biết key nào đã đặt một đơn hàng. Những key chỉ được đọc, hoặc chỉ được đặt hàng, là vấn đề phân quyền, và đó là việc của [`@nestjs/authorization`](/security/authorization).

**Với TypeORM.** Bảng là một entity, nằm cạnh các entity của store:

[[CODE:110]]

Liệt kê nó trong `entities` của data source, và migration của nó, được sinh ra giống như các bảng của store, trong `migrations`. `findKey()` đọc dòng dữ liệu qua repository của entity, bằng `findOneBy()`, còn controller ghi nó bằng `insert()` và `delete()`.

#### Thử ngay

Áp dụng các [migration](/security/authentication#keep-sessions-and-tokens-in-your-database), và khởi động ứng dụng với file `.env` từ các phần trước:

[[CODE:111]]

Trong một terminal khác, hãy đăng ký. Flag `-c` lưu session cookie vào một file, còn `-b` gửi nó kèm các request sau. `--json` (curl 7.82 trở lên) gửi một `POST` với body JSON. Header của response được rút gọn ở đây và bên dưới:

[[CODE:112]]

Session và link xác minh đang chờ giờ là các dòng trong PostgreSQL. Id của session là hash SHA-256 của cookie, còn token của link hoàn toàn không được lưu:

[[CODE:113]]

Email xác minh xuất hiện trong log của ứng dụng (`LogMailTransport` in nội dung text của mỗi email):

[[CODE:114]]

Cookie đăng nhập cho Ada, nhưng địa chỉ của cô ấy chưa được xác minh, nên cô ấy chưa đặt hàng được. Gửi token ngược lại giống như trang xác minh làm, và đơn hàng sẽ được chấp nhận. Không có cookie, API trả lời 401:

[[CODE:115]]

Đăng nhập với tư cách app mobile, và dùng access token. Các lệnh dưới đây dùng [jq](https://jqlang.org/) để lấy token ra:

[[CODE:116]]

Một refresh token chỉ dùng được một lần. Lần thử thứ hai với cùng token đó được xem là bị đánh cắp, và cả family bị thu hồi:

[[CODE:117]]

Bật xác thực hai lớp. Thêm secret vào một app authenticator, và xác nhận bằng mã mà nó hiển thị. Mã chứng minh trình duyệt này có authenticator, nên session được xác minh kể từ đây, dưới một cookie mới (`-c` lưu nó lại):

[[CODE:118]]

> info **Hint** Khi đã cài [oath-toolkit](https://www.nongnu.org/oath-toolkit/), `oathtool --totp -b` theo sau là secret sẽ in mã hiện tại ra terminal.

Đăng nhập lại. Session mới ở trạng thái pending cho đến khi qua được yếu tố thứ hai, và việc xác minh sẽ thay cookie:

[[CODE:119]]

Địa chỉ mới chưa được xác minh, và một email xác minh được gửi tới nó:

[[CODE:120]]

App mobile cũng bị yêu cầu nhập mã:

[[CODE:121]]

Bắt đầu một lần đăng nhập bằng Google. curl hiển thị redirect; mở cùng URL đó trên trình duyệt để hoàn tất, và bạn sẽ đến `/orders`, ở trạng thái đã đăng nhập:

[[CODE:122]]

Xin một magic link cho khách hàng mới tên Grace. Link chỉ dùng được trên trình duyệt đã xin nó, nên hãy giữ cookie mà response đặt. Email xuất hiện trong log của ứng dụng:

[[CODE:123]]

[[CODE:124]]

Gửi token ngược lại giống như trang làm, kèm cookie đó. Grace nhận được một tài khoản, với địa chỉ đã xác minh, và một session:

[[CODE:125]]

Grace điều hành một trại cứu trợ mèo, có hệ thống quản lý kho tự đặt mua cát vệ sinh. Hãy tạo một key cho nó từ session của cô ấy, và đặt hàng bằng key đó. Key không thể tạo key, và khi Grace thu hồi nó, nó ngừng hoạt động:

[[CODE:126]]

Liệt kê các session của Ada, rồi đăng xuất cô ấy khỏi mọi nơi. Cookie cũ của cô ấy ngừng hoạt động:

[[CODE:127]]

Ada quên mật khẩu. Hãy xin link đặt lại mật khẩu cho địa chỉ của cô ấy, và cho một địa chỉ chưa ai đăng ký: cả hai đều nhận cùng response 202 rỗng, và chỉ Ada nhận được email:

[[CODE:128]]

[[CODE:129]]

Chọn mật khẩu mới bằng token, giống như trang đặt lại mật khẩu làm. Ada được đăng nhập lại, đang chờ yếu tố thứ hai (một session pending sống mười phút, `mfa.pendingTtl`, do đó có `Max-Age`), và mật khẩu cũ không còn dùng được nữa:

[[CODE:130]]

Cuối cùng, thử đoán mật khẩu của Grace. Lần thử thứ sáu trong vòng 15 phút bị từ chối trước khi mật khẩu được kiểm tra:

[[CODE:131]]

#### GraphQL và WebSocket

Global guard, `@Public()`, `@CurrentUser()` và `AuthenticationContext` cũng hoạt động trong GraphQL resolver và WebSocket gateway. Guard đọc cookie và header từ request mang chúng.

Trong GraphQL, đó là `req` trên GraphQL context, nên tùy chọn `context` phải là một hàm tạo context cho mỗi request. Một `context` cho dưới dạng object sẽ là một object duy nhất cho mọi request, và app sẽ lỗi lúc khởi động. Nest chỉ chạy global guard và interceptor trên root resolver: để guard cả field resolver, và cung cấp `AuthenticationContext` cho chúng, hãy thêm `fieldResolverEnhancers: ['guards', 'interceptors']`.

[[CODE:132]]

Qua `graphql-ws`, mọi operation trên một socket dùng chung upgrade request đó, và mỗi operation cần người dùng sẽ xác thực lại bằng cookie của nó, nên một lần đăng xuất khỏi mọi nơi sẽ chặn operation tiếp theo. `@CurrentUser()` cho mỗi operation người dùng riêng của nó, và `null` với operation `@Public()`. `req.user`, thứ mà module cũng đặt cho code đọc request, chứa người dùng của operation nào xác thực sau cùng: hãy đọc `@CurrentUser()` thay vào đó.

Nest không chạy guard nào trên `handleConnection()` của gateway, nên hãy xác thực handshake bằng `WsAuthenticator`:

[[CODE:133]]

Nó đóng một kết nối không có ai đăng nhập, với mã 1008, hoặc `disconnect()` của socket.io; để giữ lại khách vãng lai, hãy truyền cho `authenticateConnection()` một tham số thứ ba có tùy chọn `required` là `false`. Với socket.io, nó đọc header của handshake, nên có thể bỏ tham số `request`. Một handshake từ trang của site khác là ẩn danh, giống như một [thao tác ghi cross-origin](/security/authentication#add-sign-up-and-sign-in). Sau đó guard xác thực lại mọi message, nên một session đã bị thu hồi sẽ ngừng hoạt động ngay giữa chừng kết nối. `@CurrentUser()` tính theo từng message, `null` với message `@Public()`. `client.user` chứa người dùng của message xác thực sau cùng, và bị xóa khi một message bị từ chối vì thông tin xác thực của nó.

[`@nestjs/authorization`](/security/authorization) kiểm tra `@Can()` với người dùng của từng message và từng operation, không phải của socket.

#### Test

End-to-end test khởi động `AppModule` thật, với ba thứ được thay đổi. Database là [PGlite](https://pglite.dev), PostgreSQL được biên dịch sang WebAssembly, với các migration thật của bạn được áp dụng, nên test không cần server. Mail được gửi tới một `InMemoryMailTransport`, transport này giữ mỗi email để bài test đọc. Và scrypt cố ý chậm, vài trăm mili giây và 128 MiB bộ nhớ cho mỗi lần hash ở mức chi phí mặc định, nên bài test ghi đè `PasswordHasher` bằng một bản rẻ hơn. Ứng dụng cũng đọc thiết lập lúc bootstrap, nên test cần các giá trị test cho chúng:

[[CODE:134]]

[[CODE:135]]

- `mailbox.assertSent()` tìm email gần nhất gửi tới một địa chỉ, thuộc một mail class, còn `link()` trả về link đầu tiên trong đó có chứa path, dưới dạng `URL`. Đó là toàn bộ luồng cho link xác minh, đặt lại mật khẩu và magic link: gửi, tìm link, đi theo nó.
- Email đặt lại mật khẩu được gửi sau khi có response (xem [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords)), nên bài test chờ nó bằng `vi.waitFor()`. Các email khác được gửi trước khi route trả lời.
- `DrizzleAuthenticationStore` chạy trên PGlite giống như trên PostgreSQL. PGlite chỉ có một kết nối, nên hai request không bao giờ thực sự chạy đua ở đó; các [test hợp đồng](/security/authentication#keep-sessions-and-tokens-in-your-database) của store cũng chạy trên PostgreSQL, nơi chúng thực sự chạy đua.

Để đăng nhập một người dùng test mà không cần đi qua route đăng nhập, `SessionService.create()` trả về một session cookie, còn `TokenService.issue()` trả về một bearer token (cho người dùng không có authenticator). Để test code đọc `AuthenticationContext` mà không cần HTTP, hãy chạy nó với tư cách một người dùng: `run()` nhận một kết quả xác thực (người dùng, và tùy chọn là session) cùng một hàm để chạy.
