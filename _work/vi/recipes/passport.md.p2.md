#### Bật xác thực ở phạm vi global

Nếu phần lớn endpoint của bạn nên được bảo vệ mặc định, bạn có thể đăng ký authentication guard làm một [global guard](/guards#binding-guards). Thay vì dùng decorator `@UseGuards()` trên từng controller, khi đó bạn đánh dấu các route cần công khai.

Trước tiên, đăng ký `JwtAuthGuard` làm global guard bằng cấu trúc sau (trong bất kỳ module nào):

[[CODE:28]]

Khi đã có cấu hình này, Nest sẽ tự động gắn `JwtAuthGuard` vào mọi endpoint.

Tiếp theo, cung cấp một cơ chế để khai báo route là công khai. Để làm vậy, hãy tạo một custom decorator bằng decorator factory function `SetMetadata`.

[[CODE:29]]

File ở trên export hai hằng số: metadata key của chúng ta, tên `IS_PUBLIC_KEY`, và chính decorator mới, tên `Public` (bạn có thể đặt tên nó là `SkipAuth`, `AllowAnon`, hoặc bất cứ tên gì phù hợp với project).

Khi đã có custom decorator `@Public()`, bạn có thể dùng nó để gắn cho bất kỳ method nào, như sau:

[[CODE:30]]

Cuối cùng, `JwtAuthGuard` cần trả về `true` khi tìm thấy metadata `"isPublic"`. Để làm vậy, hãy dùng class `Reflector` (xem [kết hợp tất cả lại](/guards#putting-it-all-together) trong chương Guard).

[[CODE:31]]

#### Strategy request-scoped

API của Passport dựa trên việc đăng ký strategy với instance global của library. Vì vậy, strategy không được thiết kế để có tùy chọn phụ thuộc request hay được khởi tạo động theo từng request (xem [injection scope](/fundamentals/injection-scopes) để tìm hiểu thêm về provider request-scoped). Nếu bạn cấu hình strategy là request-scoped, Nest sẽ không bao giờ khởi tạo nó, vì nó không gắn với route cụ thể nào, và không có cách nào xác định strategy "request-scoped" nào nên chạy cho một request cho trước.

Tuy nhiên, bạn có thể resolve động các provider request-scoped bên trong strategy. Để làm vậy, hãy dùng tính năng [module reference](/fundamentals/module-ref).

Trước tiên, mở file `local.strategy.ts` và inject `ModuleRef` theo cách thông thường:

[[CODE:32]]

> info **Hint** Class `ModuleRef` được import từ package `@nestjs/core`.

Hãy đảm bảo đặt thuộc tính cấu hình `passReqToCallback` thành `true`, như ở trên.

Ở bước tiếp theo, instance request được dùng để lấy định danh context hiện tại, thay vì sinh một định danh mới (xem [lấy sub-tree hiện tại](/fundamentals/module-ref#getting-current-sub-tree) để tìm hiểu thêm về request context).

Giờ, bên trong method `validate()` của class `LocalStrategy`, hãy dùng method `getByRequest()` của class `ContextIdFactory` để tạo một context id dựa trên object request, và truyền nó cho lời gọi `resolve()`:

[[CODE:33]]

Trong ví dụ ở trên, method `resolve()` trả về một cách bất đồng bộ instance request-scoped của provider `AuthService` (giả sử `AuthService` được đánh dấu là provider request-scoped).

#### Tùy chỉnh Passport

Để tùy chỉnh cách các guard gọi Passport, hãy truyền tùy chọn cho method `PassportModule.register()`. Ngoài `defaultStrategy` và `property`, hai tùy chọn mà `@nestjs/passport` tự dùng, các tùy chọn này được truyền cho lời gọi `authenticate()` của Passport, nên các tùy chọn có sẵn phụ thuộc vào strategy đang được hiện thực. Ví dụ:

[[CODE:34]]

Bạn cũng có thể cấu hình một strategy bằng cách truyền một options object cho `super()` trong constructor của nó. Ví dụ, với local strategy:

[[CODE:35]]

Xem [website Passport](http://www.passportjs.org/docs/oauth/) chính thức để biết các tên thuộc tính có sẵn.

#### Strategy có tên

Khi hiện thực một strategy, bạn có thể đặt tên cho nó bằng cách truyền một tham số thứ hai cho hàm `PassportStrategy()`. Nếu không, mỗi strategy dùng tên mặc định của nó (ví dụ `'jwt'` cho JWT strategy):

[[CODE:36]]

Sau đó bạn tham chiếu tới nó bằng một decorator như `@UseGuards(AuthGuard('myjwt'))`.

#### GraphQL

Để dùng một `AuthGuard` với [GraphQL](/graphql/quick-start), hãy kế thừa class `AuthGuard` có sẵn và override method `getRequest()`.

[[CODE:37]]

Để lấy người dùng đang được xác thực trong GraphQL resolver, hãy định nghĩa một decorator `@CurrentUser()`:

[[CODE:38]]

Để dùng decorator trong resolver, hãy đưa nó vào làm tham số của query hoặc mutation:

[[CODE:39]]

Với strategy passport-local, bạn cũng cần thêm các argument của GraphQL context vào body của request để Passport có thể truy cập chúng khi validate. Nếu không, bạn sẽ nhận lỗi `Unauthorized`.

[[CODE:40]]
