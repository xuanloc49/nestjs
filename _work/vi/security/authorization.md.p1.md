### Phân quyền

`@nestjs/authorization` biểu diễn quyền hạn dưới dạng **policy**: các class có method trả lời câu hỏi "người dùng này có được làm việc này không?". Một policy là một provider thông thường, nên nó có thể inject service, và mọi lần kiểm tra đều được kiểm tra type theo method của policy mà nó gọi. Policy làm việc với mọi cấu trúc dữ liệu, kể cả các object thuần mà Prisma, Drizzle và Kysely trả về.

Trong bài hướng dẫn này, bạn sẽ thêm phân quyền vào API của một cửa hàng online bán thức ăn và đồ dùng cho mèo:

- Khách vãng lai và khách hàng xem các sản phẩm đã đăng. Nhân viên còn thấy cả bản nháp, và chỉ nhân viên mới sửa danh mục sản phẩm.
- Khách hàng chỉ thấy đơn hàng của chính họ. Nhân viên thấy tất cả.
- Chỉ nhân viên mới được hoàn tiền đơn hàng, chỉ với đơn đã thanh toán, và chỉ tới mức mà bộ phận tài chính đặt cho từng người. Không ai được hoàn tiền một đơn hàng đã giao.
- Admin quản lý danh mục sản phẩm không giới hạn.

Trong quá trình đó, bạn sẽ thấy mỗi loại kiểm tra nên nằm ở đâu (trên route hay trong service), khi nào một lời từ chối là 401 và khi nào là 403, và cách test policy.

#### Điều kiện tiên quyết

Bài hướng dẫn này tiếp nối bài hướng dẫn [Xác thực](/security/authentication): cửa hàng đăng nhập người dùng bằng `@nestjs/authentication`, còn trang này quyết định họ được làm gì. Cài package:

[[CODE:1]]

Nếu bạn bắt đầu từ đầu, các file dưới đây là phần code đăng nhập mà trang này dựa vào: ứng dụng của bài hướng dẫn Xác thực ở thời điểm nó [cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app), rút gọn còn phần đăng nhập của app mobile, đổi mật khẩu lấy bearer token. Người dùng vẫn là object thuần như vậy, đúng như ORM của bạn trả về:

[[CODE:2]]

Bốn tài khoản demo thay cho bảng người dùng: hai khách hàng (Alice và Bob), một nhân viên (Sam), và Ada, vừa là nhân viên vừa là admin. Id của họ là cố định, để các đơn hàng demo và các bài test có thể tham chiếu tới họ:

[[CODE:3]]

`UsersRepository` là của bài hướng dẫn Xác thực, với hai method mà trang này cần. Nó tạo sẵn các tài khoản demo lúc khởi động, và chỉ có object `User` đi ra khỏi nó: các hash mật khẩu ở lại bên trong.

[[CODE:4]]

[[CODE:5]]

Token là loại mà bài hướng dẫn Xác thực cấp cho app mobile của nó: các JWT access token ngắn hạn, được mô tả một lần bằng tùy chọn `accessToken` mà root module truyền vào `AuthenticationModule` bên dưới. Signing secret là `JWT_SECRET` từ file `.env` của bài hướng dẫn Xác thực, dài ít nhất 32 byte:

[[CODE:6]]

> info **Hint** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để việc thiếu secret làm ứng dụng dừng ngay lúc khởi động, và đọc nó từ `ConfigService`.

`JwtAuth` xác minh bearer token bằng tùy chọn `accessToken`, và load người dùng của token. Nó tự đăng ký với `AuthenticationRegistry` từ constructor, đó là cách guard biết đến nó:

[[CODE:7]]

`CredentialsService` kiểm tra mật khẩu với hash đã lưu, bằng `PasswordHasher` của package, và trả lời `null` cho cả email không tồn tại lẫn mật khẩu sai, trong cùng khoảng thời gian:

[[CODE:8]]

`TokensController` đổi email và mật khẩu lấy token. Request body của nó được validate bằng bất cứ công cụ nào ứng dụng của bạn đang dùng. Mọi DTO trên trang này đều có hai phiên bản, một class có decorator và một schema Zod, nên hãy chọn kiểu bạn đang dùng và bỏ qua phiên bản còn lại:

[[CODE:9]]

[[CODE:10]]

`TokenService.issue()` ký một access token bằng cùng tùy chọn `accessToken`, và trả về nó kèm một refresh token:

[[CODE:11]]

Với schema Zod, tham số body khai báo schema thay vì class:

[[CODE:12]]

> info **Hint** Các DTO chỉ được áp dụng khi có validation pipe: hãy bind `ValidationPipe` ở cấp global, dưới dạng provider `APP_PIPE` của `AppModule` hoặc bằng `useGlobalPipes()` trong `main.ts`. Với các schema Zod, hãy bind `StandardSchemaValidationPipe` theo cùng cách. Một ứng dụng dùng một trong hai. Trang [validation](/application/validation) có các tùy chọn của mỗi loại.

[[CODE:13]]

Phần xác thực đặt `User` đã đăng nhập vào `request.user`, và `@CurrentUser()` inject nó vào handler. Đó là tất cả những gì phân quyền cần từ nó.

#### Đăng ký authorization module

Import `AuthorizationModule` cạnh `AuthenticationModule` trong root module. `AuthenticationModule` được đăng ký giống như trong bài hướng dẫn Xác thực, với tùy chọn `accessToken`; `JwtAuth` là một provider của `AuthModule`:

[[CODE:14]]

`forRoot()` đăng ký module ở cấp global. Nó làm ba việc:

- Nó cung cấp `AuthorizationService`, bạn inject nó ở bất cứ đâu code cần kiểm tra quyền.
- Nó đăng ký `AuthorizationGuard` làm global guard. Guard áp dụng decorator `@Can()` mà bạn sẽ thêm ở bước tiếp theo, và **mặc định từ chối**: một handler chỉ chạy khi nó khai báo một bước kiểm tra, bằng `@Can()`, bằng `@Can.Anyone()`, hoặc bằng `@Public()` từ `@nestjs/authentication`, decorator này được tính như `@Can.Anyone()`. `POST /auth/token` là `@Public()`, nên nó vẫn hoạt động.
- Nó biến một lời từ chối mà service báo cáo thành lỗi 401 hoặc 403, như phần [Phân biệt khách vãng lai với người dùng bị cấm, và cung cấp quyền hạn](/security/authorization#tell-guests-from-forbidden-users-and-expose-permissions) giải thích.

Do đó, một route bị quên `@Can()` sẽ bị đóng, chứ không mở. Lúc khởi động, module log mọi handler mà nó sẽ từ chối theo cách này, nên danh sách đó là nơi bắt đầu một đợt chuyển đổi. Phần [tham khảo](/security/authorization#what-a-route-declares) có các quy tắc đầy đủ.

Cả hai package đều đăng ký global guard, và **thứ tự import rất quan trọng**. Nest chạy global guard theo thứ tự nó quét các module, nên `AuthenticationModule` phải đứng trước. Nếu ngược lại, authorization guard sẽ chạy trước khi có gì đặt `request.user`, nên mọi kiểm tra `@Can()` sẽ thấy một khách vãng lai, và một nhân viên đã đăng nhập sẽ nhận lỗi 401 trên một route chỉ dành cho nhân viên. `AuthorizationModule` kiểm tra thứ tự lúc khởi động: nó nhận ra `AuthenticationGuard` nhờ một dấu hiệu mà guard mang theo, và khi guard đó đứng thứ hai, app sẽ từ chối khởi động, với thông báo lỗi nêu tên cả hai guard và cách sửa.

> warning **Warning** Các authentication guard khác, như một class con của `AuthGuard()` của Passport, không mang dấu hiệu đó, nên việc kiểm tra chỉ có thể dựa vào tên class của chúng. Khi sai thứ tự, nó log một lỗi, app vẫn khởi động, và mọi kiểm tra `@Can()` xem người dùng đã đăng nhập như khách vãng lai. Hãy đăng ký guard như vậy bằng `APP_GUARD`, không phải bằng `app.useGlobalGuards()`: Nest chạy các guard thêm theo cách đó sau mọi `APP_GUARD`, nên chúng luôn đứng sau authorization guard, và bước kiểm tra không thể thấy chúng.

> info **Hint** Guard đọc người dùng từ `request.user`, và từ các vị trí tương đương với WebSocket, microservice và GraphQL. Với `@nestjs/authentication`, trên một WebSocket hoặc socket `graphql-ws`, đó là người dùng của từng message hoặc operation, không phải của socket, như phần [tham khảo](/security/authorization#reference) giải thích. Nếu phần xác thực của bạn lưu người dùng ở chỗ khác, hãy truyền một hàm `getUser` vào `forRoot()`, hoặc trả về nó từ một factory `forRootAsync()` khi nó cần một provider. Nếu bạn xác thực bằng `@UseGuards()` thay vì global guard, hãy truyền `globalGuard: false` và liệt kê `AuthorizationGuard` sau authentication guard của bạn.

#### Viết policy cho sản phẩm

Sản phẩm cũng là object thuần, được định danh bằng slug và có giá tính bằng cent, như trong bài hướng dẫn Xác thực:

[[CODE:15]]

Một policy là một class được decorate bằng `@Policy()`. Mỗi method có tham số đầu tiên là người dùng và trả về `boolean` hoặc `Promise<boolean>` là một **ability**. Chỉ giá trị literal `true` mới cho phép. Mọi giá trị khác đều từ chối, kể cả giá trị truthy.

[[CODE:16]]

Type của tham số người dùng là một quyết định. `User | null` có nghĩa là ability cũng chạy cho khách vãng lai, những người đến dưới dạng `null`. Khách vãng lai có thể xem danh mục sản phẩm, nên mọi ability ở đây đều nhận `null`, và `view` cùng `viewDrafts` đưa ra câu trả lời thực sự cho khách vãng lai.

`ProductsService` dùng policy theo hai cách. `can()` resolve ra `true` hoặc `false`; ở đây nó quyết định danh sách có bao gồm bản nháp hay không. `authorize()` throw khi ability từ chối, nên `findOne()` không bao giờ trả về bản nháp cho người không được phép xem nó.

[[CODE:17]]

Tạo và cập nhật sản phẩm không phụ thuộc vào một bản ghi cụ thể nào, nên các bước kiểm tra đó nằm trên route. Body của các route đó là DTO, dưới dạng class hoặc schema Zod; một lần cập nhật nhận bất kỳ tập con nào của các trường của sản phẩm mới:

[[CODE:18]]

[[CODE:19]]

`@Can(ProductPolicy, 'create')` khiến guard gọi `create(user)` trước khi handler chạy:

[[CODE:20]]

Với các schema Zod, tham số body khai báo schema thay vì class:

[[CODE:21]]

Một route có cho khách vãng lai vào hay không là quyết định của phần xác thực, không phải của policy. Các route đọc dùng `@Authenticate()` với `optional: true`: một request có token hợp lệ sẽ có người dùng của nó, còn một request không có token sẽ tiếp tục với `null`, đó cũng là thứ mà `@CurrentUser()` inject khi đó. Không có decorator này, khách vãng lai sẽ nhận lỗi 401 trước khi bất kỳ policy nào chạy. Nếu dùng `@Public()` thay vào đó, phần xác thực sẽ bỏ qua hoàn toàn token, nên Sam sẽ xem như một khách vãng lai và không bao giờ thấy bản nháp.

Các route đọc kiểm tra trong service, nên chúng khai báo `@Can.Anyone()`: bất kỳ ai mà phần xác thực cho qua đều có thể gọi chúng, và `ProductsService` quyết định mỗi người gọi thấy gì. Không có nó, guard sẽ từ chối chúng.

`@Can()` được kiểm tra type. Một ability viết sai chính tả sẽ không compile được:

[[CODE:22]]

Thông báo lỗi liệt kê các ability dùng được trên một route: những ability có tham số người dùng nhận `null`, vì guard không thể biết một route có người dùng hay không. `view` là một trong số đó, nhưng `@Can(ProductPolicy, 'view')` vẫn không compile được (`Expected 3 arguments, but got 2`): `view` còn nhận thêm sản phẩm, mà guard không có sản phẩm nào để truyền. Các bước kiểm tra cần một bản ghi thuộc về service, như trong `findOne()`. Một bước kiểm tra chỉ cần một id từ URL có thể nằm trên route, như phần [Kiểm tra route parameter](/security/authorization#check-a-route-parameter) chỉ ra.

Cuối cùng, đăng ký policy làm provider của feature module của nó:

[[CODE:23]]

Thêm `ProductsModule` vào `imports` của `AppModule`. `@Policy()` cũng biến class thành injectable, và authorization module phát hiện mọi policy provider trong app, bất kể chúng được đăng ký ở đâu. Cách khác là liệt kê các policy trong tùy chọn `policies` của `AuthorizationModule.forRoot()`.

> info **Hint** Nếu một `@Can()` trỏ tới một policy chưa ai đăng ký, app sẽ từ chối khởi động, và thông báo lỗi nêu tên handler.

#### Kiểm tra đơn hàng theo từng bản ghi

Đơn hàng là loại trong bài hướng dẫn Xác thực: nó thuộc về một khách hàng, qua `userId`, và chuyển qua vài trạng thái:

[[CODE:24]]

Alice có được xem một đơn hàng của Bob hay không phụ thuộc vào đơn hàng đó, nên các ability này nhận đơn hàng làm tham số thứ hai:

[[CODE:25]]

Các ability này nhận `User`, không phải `User | null`. Mọi route đơn hàng đều yêu cầu người dùng đã đăng nhập, và một ability chỉ được service gọi có thể nói rõ điều đó. Khi đó trình biên dịch buộc bên gọi phải loại trừ trường hợp không có người dùng trước khi kiểm tra.

Bốn đơn hàng demo thay cho bảng đơn hàng, với id cố định giống các tài khoản demo: Alice có một đơn đã thanh toán và một đơn đã giao, Bob có một đơn đã thanh toán gồm năm túi hạt cá hồi (124,95, con số này quan trọng khi [một policy inject một service](/security/authorization#inject-a-service-into-a-policy)) và một đơn đang chờ:

[[CODE:26]]

`OrdersService` load đơn hàng, rồi kiểm tra quyền dựa trên nó:

[[CODE:27]]

Mọi thứ sau class policy đều có type lấy từ signature của ability: tên ability, người dùng và đơn hàng. Một ability viết sai, thiếu đơn hàng, hoặc một object không phải `Order` đều không compile được, và một người dùng có thể là `null` cũng vậy:

[[CODE:28]]

Phần liệt kê không kiểm tra từng đơn hàng một. Nó hỏi một câu mà query có thể dùng (người dùng này có được xem mọi đơn hàng không?) rồi lọc ngay trong database. Kiểm tra từng dòng sau khi đã load hết sẽ lấy quá nhiều dữ liệu và làm hỏng việc phân trang.

Kiểm tra trong service thay vì trong controller có nghĩa là mọi bên gọi đều nhận cùng các quy tắc: một controller, một GraphQL resolver, hay một queue worker xử lý yêu cầu hoàn tiền.

Controller truyền người dùng đã đăng nhập xuống. `OrdersService` của bài hướng dẫn Xác thực thì đọc nó từ `AuthenticationContext`; ở đây nó là một tham số, nên signature của service cho biết một bước kiểm tra đang xét quyền của ai, và một queue worker có thể gọi nó cho một người dùng cụ thể. Mọi route đều kiểm tra trong service, nên mỗi route khai báo `@Can.Anyone()`:

[[CODE:29]]

[[CODE:30]]

Thêm `OrdersModule` vào `imports` của `AppModule`. Giờ Alice nhận được hai đơn hàng của cô ấy từ `GET /orders`, và lỗi 403 từ `GET /orders/:id` với một đơn hàng của Bob.

> info **Hint** Lỗi 403 xác nhận rằng đơn hàng có tồn tại. Nếu điều đó quan trọng, ví dụ khi id là số tăng dần và dễ đoán, hãy kiểm tra bằng `can()` và throw `NotFoundException` thay vào đó.

#### Kiểm tra route parameter

Một số bước kiểm tra cần tham số nhưng không cần bản ghi. Nhân viên tra cứu đơn hàng của một khách hàng tại `GET /customers/:customerId/orders`, và khách hàng cũng có thể liệt kê đơn hàng của chính họ ở đó. Alice có được gọi nó hay không chỉ phụ thuộc vào id trong URL, nên không có gì cần load trước khi kiểm tra. Thêm một ability cho nó vào `OrderPolicy`:

[[CODE:31]]

Khác với các ability khác của `OrderPolicy`, ability này nhận `User | null`, vì một route ability phải chấp nhận khách vãng lai. Route kiểm tra nó bằng `@Can()`, với tham số thứ ba đọc các tham số đứng sau người dùng từ lời gọi:

[[CODE:32]]

`OrdersService` có thêm một method lọc theo khách hàng, không có bước kiểm tra riêng, vì route đã có:

[[CODE:33]]

Thêm controller vào `controllers` của `OrdersModule`. Giờ Alice nhận được đơn hàng của cô ấy từ `GET /customers/<Alice's id>/orders` và lỗi 403 với đơn hàng của Bob, Sam nhận được cả hai, còn khách vãng lai nhận lỗi 401.

Hàm được gán type theo chính các tham số của ability. Bỏ nó đi sẽ không compile được khi ability nhận nhiều hơn người dùng, và trả về sai type cũng vậy:

[[CODE:34]]

Nó chạy trong guard, trước mọi pipe, nên nó nhận các giá trị đúng như transport gửi đến: route param là chuỗi, và chưa có gì được validate. Một `ParseUUIDPipe` trên `customerId` chạy sau bước kiểm tra, và một id mà người dùng không được xem sẽ nhận lỗi 403, không phải 400. Một lỗi mà hàm throw ra, như `BadRequestException` khi thiếu param, đến client HTTP nguyên vẹn. Trên WebSocket và microservice, Nest báo một `HttpException` từ bất kỳ guard nào, kể cả hàm này, thành lỗi nội bộ, nên hãy throw `WsException` hoặc `RpcException` ở đó. Một event từ chối mang theo những gì hàm đã đọc trong `args` của nó.

Hãy truyền định danh và phạm vi, không truyền bản ghi. Load đơn hàng trong guard sẽ load nó hai lần, một lần cho bước kiểm tra và một lần trong handler, và trả lời 403 trước khi handler kịp trả lời 404. Đó là lý do `GET /orders/:id` kiểm tra trong service.

Một hàm khai báo riêng sẽ trả về mảng thay vì tuple mà các tham số của ability mô tả, nên hãy kết thúc nó bằng `as const`. Điều đó giúp một helper nhỏ dùng lại được trên nhiều route:

[[CODE:35]]

[[CODE:36]]

Trên các transport khác, hãy đọc tham số từ context riêng của chúng: `GqlExecutionContext.create(context).getArgs()` cho tham số của một operation GraphQL, `context.switchToWs().getData()` cho một message WebSocket, và `context.switchToRpc().getData()` cho một message microservice.

#### Cho admin đi qua bằng `before()`

Admin được làm mọi thứ với danh mục sản phẩm, kể cả xóa sản phẩm, điều mà không ai khác được làm. Thay vì thêm bước kiểm tra admin vào mọi ability, hãy cho policy một hook `before()`:

[[CODE:37]]

`before()` chạy trước mọi ability của policy, cho cả kiểm tra trên route lẫn kiểm tra trong service. Nó nhận người dùng, tên ability, và các tham số của ability. Trả về `true` để cho phép, `false` để từ chối, hoặc không trả về gì để ability tự quyết định. Khách vãng lai cũng đi tới `before()`, nên tham số người dùng của nó phải nhận `null`. `before(user: User)` không compile được, bất kể class có implement `PolicyBefore<User>` hay không.

Thêm route dùng ability mới vào `ProductsController`, và import `Delete` cùng `HttpCode` từ `@nestjs/common`:

[[CODE:38]]

Giờ Sam nhận lỗi 403 từ `DELETE /products/clumping-litter-10l`, còn Ada nhận 204.

> warning **Warning** `before()` bỏ qua mọi ability của policy, kể cả những quy tắc lẽ ra phải ràng buộc tất cả mọi người. Đó là lý do `OrderPolicy` không có đường tắt cho admin: "không ai được hoàn tiền một đơn hàng đã giao" phải đúng cả với Ada. Nếu một policy cần cả hai, hãy kiểm tra tên ability mà `before()` nhận được, và không trả về gì với những ability mà nó không được bỏ qua. Implement `PolicyBefore<User, Ability<OrderPolicy>>` và gán type cho tên là `Ability<OrderPolicy>`, để một tên loại trừ viết sai không compile được.

#### Inject service vào policy

Bộ phận tài chính giới hạn số tiền mà mỗi nhân viên được tự hoàn: mặc định 100,00, cao hơn với một số người. Các giới hạn nằm bên ngoài policy, trong một service đọc từ một bảng hoặc một config service:

[[CODE:39]]

Vì policy là provider, nó inject service qua constructor. Ability `refund` trở thành `async`:

[[CODE:40]]

`authorize()`, `can()` và guard đều await các ability async, nên `OrdersService` không thay đổi. Đăng ký service cạnh policy:

[[CODE:41]]

Vì `OrderPolicy` được đăng ký trong `OrdersModule`, nó có thể inject các provider của module đó. Một policy liệt kê trong tùy chọn `policies` của `forRoot()` thì nằm trong authorization module, và cần tùy chọn `imports` để tiếp cận các dependency của nó.

Đơn hàng đã thanh toán của Bob là 124,95. Giờ Sam (giới hạn 100,00) nhận lỗi 403 khi cố hoàn tiền nó, còn Ada (giới hạn 1.000,00) thì thành công.

> warning **Warning** Policy phải là singleton. Một policy request-scoped hoặc transient, hoặc một policy phụ thuộc vào provider request-scoped, sẽ throw lúc khởi động. Đừng để state theo request trong policy, và hãy truyền những gì ability cần dưới dạng tham số.

#### Phân biệt khách vãng lai với người dùng bị cấm, và cung cấp quyền hạn

Một request bị từ chối sẽ nhận lỗi 401 hoặc 403, tùy theo ai đang hỏi và hỏi ở đâu:

| Người gọi        | Route                                                                                     | Status                                             | Đến từ                                  |
| ---------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------- |
| Khách vãng lai   | Yêu cầu đăng nhập (mặc định), như `POST /products` hoặc `GET /orders`                     | 401, kèm `WWW-Authenticate: Bearer realm="store"`  | Xác thực, trước khi bất kỳ policy nào chạy |
| Khách vãng lai   | Xác thực tùy chọn, và policy từ chối `null`, như một sản phẩm nháp                        | 401                                                | Phân quyền                              |
| Người dùng đã đăng nhập | Policy từ chối, như Alice trên `POST /products` hoặc trên một đơn hàng của Bob    | 403                                                | Phân quyền                              |

Phân quyền không bao giờ quyết định một route có cần người dùng hay không; đó là việc của xác thực. Khi một policy từ chối khách vãng lai, package trả lời 401 ("hãy đăng nhập rồi thử lại") thay vì 403 ("không bao giờ"), vì đăng nhập có thể thay đổi câu trả lời.

Bản thân `authorize()` throw một `AuthorizationError`, có `reason` là `unauthenticated` hoặc `forbidden`, và `status` là 401 hoặc 403 tương ứng. Nó không phải HTTP exception, vì cùng service đó còn chạy trong queue worker và WebSocket gateway. Khi lỗi thoát ra khỏi handler, `AuthorizationModule` biến nó thành `UnauthorizedException` hoặc `ForbiddenException` giống như guard throw, với cùng body, nên exception filter và client xử lý cả hai như mọi lỗi HTTP khác. Trong WebSocket gateway và handler của microservice, nó trở thành `WsException` hoặc `RpcException`. Body của lỗi 403 không nêu tên ability.

`can()` không bao giờ throw khi bị từ chối. Nó resolve ra `false` cho cả khách vãng lai lẫn người dùng bị cấm, khiến nó trở thành công cụ để định hình response. Hãy cho mỗi đơn hàng một flag `canRefund`, để frontend hiển thị nút hoàn tiền mà không phải lặp lại các quy tắc:

[[CODE:42]]

Flag lấy từ cùng ability `refund` mà `POST /orders/:id/refund` áp dụng, nên nút bấm và endpoint không thể bất đồng. Sam thấy `canRefund: true` trên đơn hàng đã thanh toán của Alice và `false` trên đơn của Bob, vốn vượt quá giới hạn của anh ấy. Ada thấy `true` trên cả hai.

#### Thử ngay

Khởi động ứng dụng với file `.env` chứa signing secret:

[[CODE:43]]

Trong một terminal khác, đăng nhập với tư cách Alice, Sam và Ada. `--json` (curl 7.82 trở lên) gửi một `POST` với body JSON, và helper `token` dùng [jq](https://jqlang.org/) để lấy access token ra:

[[CODE:44]]

Khách vãng lai thấy các sản phẩm đã đăng. Nhân viên thấy cả bản nháp:

[[CODE:45]]

Bản thân bản nháp là lỗi 401 với khách vãng lai và 403 với khách hàng. Header của response được rút gọn ở đây và bên dưới:

[[CODE:46]]

Chỉ nhân viên mới thêm sản phẩm. Phần xác thực chặn khách vãng lai, còn `@Can()` chặn Alice:

[[CODE:47]]

Alice thấy đơn hàng của chính cô ấy và không hoàn tiền được đơn nào. Sam thấy mọi đơn hàng, với các flag `canRefund` của riêng anh ấy. Đơn hàng đã thanh toán của Bob nằm ngoài giới hạn của Alice:

[[CODE:48]]

Sam hoàn tiền đơn hàng đã thanh toán của Alice, nhưng không hoàn được đơn đã giao của cô ấy, và cũng không hoàn được đơn của Bob, vốn vượt quá giới hạn của anh ấy. Ada cũng không hoàn tiền được đơn đã giao, nhưng đơn của Bob nằm trong giới hạn của cô ấy:

[[CODE:49]]

Chỉ admin mới xóa được sản phẩm:

[[CODE:50]]
