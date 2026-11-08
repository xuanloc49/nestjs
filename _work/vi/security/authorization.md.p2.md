#### Test

Một end-to-end test khởi động toàn bộ app, đăng nhập qua endpoint thật, và kiểm tra các quy tắc qua HTTP. Giống như trong bài hướng dẫn Xác thực, scrypt cố ý chậm, nên bài test ghi đè `PasswordHasher` bằng một bản rẻ hơn, và ứng dụng đọc `JWT_SECRET` lúc bootstrap, nên cấu hình test cung cấp một giá trị:

[[CODE:51]]

[[CODE:52]]

Một policy là một class thông thường, nên các quy tắc của nó dễ unit test mà không cần Nest. Hãy tự khởi tạo policy và kiểm soát các dependency của nó; các tài khoản và đơn hàng demo kiêm luôn vai trò fixture:

[[CODE:53]]

Gọi trực tiếp một ability sẽ bỏ qua `before()`. Hook chỉ là một method khác, nên hãy test nó theo cùng cách, ví dụ `expect(new ProductPolicy().before(ada)).toBe(true)`. Để test hook cùng với ability, hãy đi qua `AuthorizationService`, và để test cả việc ánh xạ 401/403, hãy đi qua HTTP, như end-to-end test làm.

Một bài test service nằm ở giữa: policy thật và `AuthorizationModule`, không có HTTP hay đăng nhập. Bên ngoài handler, một lời từ chối vẫn là `AuthorizationError`:

[[CODE:54]]

Để thay một policy trong một bài test lớn hơn, hãy ghi đè nó như mọi provider khác, ví dụ `.overrideProvider(OrderPolicy).useValue(...)`: mọi bước kiểm tra, trên route lẫn trong service, đều chạy với bản ghi đè.

#### Checklist cho production

- **Giữ xác thực đứng trước phân quyền.** Với `AuthenticationModule`, thứ tự import sai sẽ làm app dừng lúc khởi động. Với một authentication guard khác, nó chỉ log một lỗi, nên hãy có một end-to-end test đăng nhập và gọi một route `@Can()`. Có hai cách đăng ký luôn chạy sau authorization guard, bất kể thứ tự import: một `APP_GUARD` request-scoped (bước kiểm tra lúc khởi động có báo điều này) và `app.useGlobalGuards()` (bước kiểm tra không thể phát hiện). Hãy đăng ký xác thực như một singleton `APP_GUARD`.
- **Rà soát mọi `@Can.Anyone()`.** Guard từ chối handler không khai báo bước kiểm tra nào, và log từng handler như vậy lúc khởi động, nên một `@Can()` bị quên sẽ đóng route lại. `@Can.Anyone()` mở route cho mọi người mà phần xác thực cho qua: hãy kiểm tra service của nó có kiểm tra quyền không, hoặc route có thực sự không cần quyền gì không. Một bước kiểm tra trên id trong URL có thể đặt trên route, bằng tham số thứ ba của `@Can()`, nơi một lần sửa handler sau này không thể làm rơi mất nó.
- **Kết nối microservice với `inheritAppConfig: true`.** Trong một hybrid app, Nest chỉ chạy global guard và interceptor của app trên message handler khi `connectMicroservice()` nhận tùy chọn đó. Không có nó, `@Can()` trên một message handler sẽ không được áp dụng, và một lời từ chối từ `authorize()` sẽ đến client dưới dạng lỗi nội bộ thay vì 401 hay 403.
- **Đặt các bước kiểm tra bản ghi trong service**, sau khi load bản ghi, để controller, resolver và queue worker dùng chung chúng.
- **Đừng cache response theo URL trên các route kiểm tra bản ghi.** Một cache như `CacheInterceptor` của Nest trả lời trước khi handler chạy, nên nó sẽ phục vụ đơn hàng của Bob cho Alice mà không hỏi `OrderPolicy`. Hãy cache ở bên dưới bước kiểm tra, hoặc cache theo từng người dùng.
- **Lọc danh sách ngay trong query** bằng một câu hỏi mà query có thể dùng, như `viewAll`, thay vì load mọi dòng rồi kiểm tra từng dòng.
- **Kiểm tra lại trạng thái khi ghi.** Phân quyền đọc đơn hàng trước khi hoàn tiền, và hai request đồng thời có thể cùng thấy `paid`. Hãy làm cho thao tác ghi có điều kiện (chỉ cập nhật trạng thái ở chỗ nó vẫn còn là `paid`), và gửi cho payment provider một idempotency key, để một lần retry không bao giờ hoàn tiền hai lần.
- **Chọn giữa 403 và 404** cho những bản ghi mà sự tồn tại của chúng là nhạy cảm, như đơn hàng của khách hàng khác khi id là số tăng dần.
- **Giữ policy stateless.** Chúng là singleton dùng chung cho mọi request.
- **Để ý chi phí của các flag `can()`.** Mỗi flag chạy ability một lần cho mỗi dòng, kể cả mọi công việc async. Hãy cache các phép tra cứu chậm như giới hạn hoàn tiền, hoặc load chúng một lần cho mỗi request.
- **Load secret từ cấu hình.** Hãy đọc JWT secret (ít nhất 32 byte) từ một secret manager hoặc `ConfigService`, không phải từ code.
- **Kiểm tra bằng `can()` trong guard và middleware của riêng bạn.** Chúng chạy trước mọi handler, nên một `AuthorizationError` throw ở đó sẽ không được biến thành 401 hay 403. Nó trở thành lỗi 500.
- **Ghi lại audit các lời từ chối.** Response không cho biết bước kiểm tra nào đã từ chối người gọi. Hãy subscribe `AuthorizationEvents` để log policy, ability và id người dùng cho mọi lời từ chối. Mỗi event mang theo người dùng và bản ghi đúng như policy đã thấy, nên hãy log những trường bạn cần thay vì toàn bộ event.

#### Tham khảo

##### Tùy chọn module

`AuthorizationModule.forRoot()` nhận các tùy chọn này. `forRootAsync()` nhận `policies`, `imports`, `globalGuard` và `isGlobal` ở cấp cao nhất, cạnh `useFactory`, và factory của nó trả về `getUser`.

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `getUser` | `defaultGetUser` | Một hàm nhận `ExecutionContext` và trả về người dùng hiện tại, hoặc một promise của nó. Xem [Đăng ký authorization module](/security/authorization#register-the-authorization-module). |
| `policies` | không có | Các policy được đăng ký trong chính authorization module. Một provider `@Policy()` ở bất kỳ module nào đều được tìm thấy mà không cần liệt kê. |
| `imports` | không có | Các module có provider được export mà `policies` inject. |
| `globalGuard` | `true` | Đăng ký `AuthorizationGuard` làm global guard. Với `false`, hãy áp dụng nó bằng `@UseGuards()` sau authentication guard của bạn. |
| `isGlobal` | `true` | Đăng ký module ở cấp global. |

`defaultGetUser` đọc người dùng từ các vị trí sau. `null`, `undefined` và `false` đều có nghĩa là khách vãng lai.

| Context | Nguồn |
| --- | --- |
| HTTP | `request.user` |
| GraphQL | người dùng mà phần xác thực đã ghi nhận cho operation này, nếu không thì `req.user` trên GraphQL context |
| WebSocket | người dùng mà phần xác thực đã ghi nhận cho message này, nếu không thì `client.user`, rồi `client.data.user` |
| Microservice | `user` trên transport context, không bao giờ lấy từ payload của message |

Một WebSocket client là kết nối, không phải message, và qua `graphql-ws`, `req` trên GraphQL context là upgrade request của socket, thứ mà mọi operation trên socket dùng chung. Vì vậy `client.user` và `req.user` chứa người dùng của message hoặc operation nào xác thực sau cùng. `@nestjs/authentication` cũng để lại một hàm trên client và trên `req`, dưới `Symbol.for('nestjs.authentication.userOf')`, hàm này nhận `ExecutionContext` và trả lời bằng người dùng của message hoặc operation đó: `null` với một message/operation ẩn danh, như mọi cái `@Public()`, hoặc `undefined` khi nó không có câu trả lời. `defaultGetUser` hỏi nó trước. Do đó một message hoặc operation `@Public()` là khách vãng lai đối với `@Can()`, kể cả trên một socket có handshake đã đăng nhập, và một session đã bị thu hồi bởi việc đăng xuất khỏi mọi nơi không còn được tính nữa. Một `getUser` của riêng bạn đọc `client.user` hoặc `req.user` trên các transport này sẽ thấy người dùng sau cùng của socket; các package xác thực khác có thể để lại cùng hàm đó để được hỏi.

##### Những gì một route khai báo

Guard quyết định dựa trên những gì handler và class của nó khai báo:

| Khai báo | Guard |
| --- | --- |
| `@Can()` | Chạy mọi yêu cầu của class, rồi đến của method. Tất cả đều phải đạt. |
| `@Can.Anyone()` | Cho qua bất kỳ ai mà phần xác thực cho qua. |
| `@Public()` từ `@nestjs/authentication` (0.1.0 trở lên) | Giống như `@Can.Anyone()`. |
| Không có gì | Từ chối: 403 với người dùng, 401 với khách vãng lai. Log lúc khởi động nêu tên handler. |

Trên một method, `@Can.Anyone()` hoặc `@Public()` gỡ bỏ `@Can()` của class, giống như `@Public()` gỡ bỏ yêu cầu xác thực của class. Một `@Can()` trên chính method vẫn được áp dụng, nên một method `@Public()` có `@Can()` sẽ chạy bước kiểm tra cho khách vãng lai. Trên một class, không cái nào gỡ bỏ được `@Can()` của method. Một method được `@Authenticate()` đưa trở lại dưới yêu cầu xác thực bên trong một class `@Public()` thì không còn công khai, và cần một khai báo riêng.

Ở những nơi Nest không chạy global guard nào, không có gì bị từ chối: trên GraphQL field resolver trừ khi `fieldResolverEnhancers` bao gồm `'guards'`, và trên message handler của một hybrid app được kết nối mà không có `inheritAppConfig: true`. Với enhancer đó, mọi `@ResolveField()` cũng cần một khai báo. Một khai báo ở cấp class sẽ bao phủ chúng.

##### Event

`AuthorizationEvents` cung cấp mọi lời từ chối trên observable `events$` của nó, và công bố nó trên một diagnostics channel. `can()` resolve ra `false` không phải là lời từ chối và không phát ra gì cả.

| Loại event | Channel | Khi nào |
| --- | --- | --- |
| `denied` | `nestjs:authorization:denied` | `@Can()` hoặc `authorize()` đã từ chối một người gọi |

Payload `AuthorizationDeniedEvent` có các trường sau:

- `type`: `'denied'`.
- `policy` và `ability`: tên class policy và ability đã từ chối, như `OrderPolicy` và `refund`. Cả hai là `null` khi guard từ chối một handler không khai báo bước kiểm tra nào.
- `reason`: `'unauthenticated'` với khách vãng lai, `'forbidden'` với người dùng đã đăng nhập.
- `user`: người dùng mà policy đã thấy, `null` với khách vãng lai.
- `args`: các tham số của ability đứng sau người dùng, như bản ghi. Với `@Can()`, là những gì tham số thứ ba của nó đọc được, hoặc rỗng nếu không có.
- `handler`: handler mà `@Can()` đã bảo vệ, như `ProductsController.create`. Không có với `authorize()`.

##### Lỗi

`authorize()` throw một `AuthorizationError` với `reason`, `status`, `policy` và `ability`. Lời từ chối của guard với một handler không khai báo bước kiểm tra nào mang cùng lỗi đó, với `policy` và `ability` đặt là `null`. Khi nó thoát ra khỏi handler, hoặc khi `@Can()` từ chối, người gọi nhận lỗi riêng của transport, với body không bao giờ nêu tên policy hay ability. Xem [Phân biệt khách vãng lai với người dùng bị cấm, và cung cấp quyền hạn](/security/authorization#tell-guests-from-forbidden-users-and-expose-permissions).

| `reason` | `status` | HTTP | GraphQL `extensions.code` | WebSocket và microservice |
| --- | --- | --- | --- | --- |
| `unauthenticated` | 401 | `UnauthorizedException` | `UNAUTHENTICATED` | `WsException` hoặc `RpcException` với `statusCode: 401` |
| `forbidden` | 403 | `ForbiddenException` | `FORBIDDEN` | `WsException` hoặc `RpcException` với `statusCode: 403` |

Qua `graphql-ws`, client nhận message của lỗi, `Unauthorized` hoặc `Forbidden`, mà không có `extensions.code`: Apollo driver thêm các mã này trong phần định dạng lỗi của nó, phần này không chạy trên transport đó.

Một `AuthorizationError` throw bên ngoài handler, như trong guard hoặc middleware của riêng bạn, sẽ không được ánh xạ và trở thành lỗi 500.
