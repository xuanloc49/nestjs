### Execution context

Nest cung cấp vài class tiện ích giúp bạn viết ứng dụng hoạt động được trên nhiều application context khác nhau (ví dụ context dựa trên HTTP server, microservice và WebSocket). Các tiện ích này cung cấp thông tin về execution context hiện tại, giúp bạn xây dựng các [guard](/guards), [filter](/exception-filters) và [interceptor](/interceptors) generic, hoạt động được trên nhiều controller, method và execution context khác nhau.

Chương này trình bày hai class như vậy: `ArgumentsHost` và `ExecutionContext`.

#### Class ArgumentsHost

Class `ArgumentsHost` cung cấp các method để lấy các tham số được truyền vào một handler. Nó cho phép bạn chọn context phù hợp (ví dụ HTTP, RPC (microservice), hoặc WebSocket) để lấy tham số. Framework cung cấp một instance `ArgumentsHost`, thường được tham chiếu bằng tham số `host`, ở những chỗ bạn có thể cần truy cập nó. Ví dụ, method `catch()` của một [exception filter](/exception-filters#arguments-host) được gọi với một instance `ArgumentsHost`.

`ArgumentsHost` đóng vai trò lớp trừu tượng bọc quanh các tham số của handler. Ví dụ, trong ứng dụng HTTP server (khi dùng `@nestjs/platform-express`), object `host` đóng gói mảng `[request, response, next]` của Express, trong đó `request` là request object, `response` là response object, và `next` là hàm điều khiển chu trình request-response của ứng dụng. Ngược lại, với ứng dụng [GraphQL](/graphql/quick-start), object `host` chứa mảng `[root, args, context, info]`.

#### Application context hiện tại

Khi bạn xây dựng các [guard](/guards), [filter](/exception-filters) và [interceptor](/interceptors) generic để chạy trên nhiều application context, bạn cần một cách để xác định loại ứng dụng mà method của bạn đang chạy trong đó. Hãy dùng method `getType()` của `ArgumentsHost` cho việc này. Mặc định nó trả về `'http'`, `'rpc'` hoặc `'ws'`, và các package như `@nestjs/graphql` bổ sung thêm type riêng của chúng:

[[CODE:1]]

> info **Hint** Type `GqlContextType` được import từ package `@nestjs/graphql`.

Khi đã biết loại ứng dụng, bạn có thể viết các thành phần generic hơn, như bên dưới.

#### Tham số của handler

Một cách để lấy mảng tham số được truyền vào handler là dùng method `getArgs()` của object host:

[[CODE:2]]

Bạn có thể lấy riêng một tham số theo chỉ số bằng method `getArgByIndex()`:

[[CODE:3]]

Các ví dụ này lấy request và response object theo chỉ số, cách này thường không được khuyên dùng vì nó gắn chặt ứng dụng với một execution context cụ thể. Thay vào đó, bạn có thể làm code bền vững và dễ tái sử dụng hơn bằng cách dùng một trong các method tiện ích của object `host` để chuyển sang application context phù hợp. Các method tiện ích chuyển context được liệt kê bên dưới.

[[CODE:4]]

Hãy viết lại ví dụ trước bằng method `switchToHttp()`. Lời gọi helper `host.switchToHttp()` trả về một object `HttpArgumentsHost` phù hợp với context ứng dụng HTTP. Object `HttpArgumentsHost` có hai method hữu ích để lấy ra các object mong muốn. Ví dụ này cũng truyền các type của Express làm type argument, để các method trả về object Express có type gốc:

[[CODE:5]]

Tương tự, `WsArgumentsHost` và `RpcArgumentsHost` có các method trả về object phù hợp trong context WebSocket và microservice. Đây là các method của `WsArgumentsHost`:

[[CODE:6]]

Và đây là các method của `RpcArgumentsHost`:

[[CODE:7]]

#### Class ExecutionContext

`ExecutionContext` kế thừa `ArgumentsHost`, cung cấp thêm thông tin chi tiết về quá trình thực thi hiện tại. Giống như `ArgumentsHost`, Nest cung cấp một instance `ExecutionContext` ở những chỗ bạn có thể cần nó, như method `canActivate()` của [guard](/guards#execution-context) và method `intercept()` của [interceptor](/interceptors#execution-context). Nó cung cấp các method sau:

[[CODE:8]]

Method `getHandler()` trả về tham chiếu tới handler sắp được gọi. Method `getClass()` trả về type của class controller chứa handler đó. Ví dụ, trong context HTTP, nếu request đang được xử lý là một request `POST` được bind vào method `create()` của `CatsController`, `getHandler()` sẽ trả về tham chiếu tới method `create()`, còn `getClass()` trả về **class** `CatsController` (không phải instance).

[[CODE:9]]

Việc truy cập được cả class hiện tại lẫn method handler mang lại sự linh hoạt rất lớn. Quan trọng nhất, nó cho phép bạn đọc, từ bên trong guard hoặc interceptor, metadata được đặt bởi các decorator tạo bằng `Reflector#createDecorator` hoặc bởi decorator có sẵn `@SetMetadata()`. Các phần sau sẽ trình bày trường hợp sử dụng này.

<app-banner-enterprise></app-banner-enterprise>

#### Reflection và metadata

Nest cho phép bạn gắn **custom metadata** vào route handler thông qua các decorator tạo bằng method `Reflector#createDecorator`, hoặc bằng decorator có sẵn `@SetMetadata()`. Phần này so sánh hai cách và chỉ ra cách truy cập metadata từ bên trong guard hoặc interceptor.

Để tạo decorator có type chặt chẽ bằng `Reflector#createDecorator`, hãy chỉ định type argument. Ví dụ, hãy tạo một decorator `Roles` nhận một mảng chuỗi làm tham số.

[[CODE:10]]

Decorator `Roles` ở đây là một hàm nhận một tham số duy nhất có type `string[]`.

Để dùng decorator này, hãy đánh dấu handler bằng nó:

[[CODE:11]]

Cách này gắn metadata của decorator `Roles` vào method `create()`, cho biết chỉ người dùng có role `admin` mới được phép truy cập route này.

Để lấy (các) role của route (custom metadata), ta lại dùng class helper `Reflector`. `Reflector` có thể được inject vào class theo cách thông thường:

[[CODE:12]]

> info **Hint** Class `Reflector` được import từ package `@nestjs/core`.

Giờ, để đọc metadata của handler, dùng method `get()`:

[[CODE:13]]

Method `Reflector#get` nhận hai tham số: một tham chiếu decorator và một **context** (target của decorator) để lấy metadata. Trong ví dụ này, **decorator** được chỉ định là `Roles` (xem file `roles.decorator.ts` ở trên). Context được cung cấp bởi lời gọi `context.getHandler()`, giúp lấy metadata của route handler đang được xử lý. Hãy nhớ rằng `getHandler()` trả về **tham chiếu** tới hàm route handler.

Ngoài ra, bạn có thể áp dụng metadata ở cấp controller, để nó áp dụng cho mọi route trong class controller.

[[CODE:14]]

Trong trường hợp này, để lấy metadata của controller, hãy truyền `context.getClass()` làm tham số thứ hai (để cung cấp class controller làm context lấy metadata) thay vì `context.getHandler()`:

[[CODE:15]]

Vì metadata có thể được cung cấp ở nhiều cấp, có thể bạn cần lấy và gộp metadata từ vài context. Class `Reflector` cung cấp hai method tiện ích cho việc này. Chúng lấy **cả** metadata của controller lẫn của method cùng lúc, và kết hợp chúng theo những cách khác nhau.

Xét tình huống sau, trong đó bạn đã cung cấp metadata `Roles` ở cả hai cấp.

[[CODE:16]]

Nếu ý định của bạn là đặt `'user'` làm role mặc định và ghi đè có chọn lọc cho một số method, hãy dùng method `getAllAndOverride()`. Nó trả về giá trị được định nghĩa đầu tiên, kiểm tra các target theo đúng thứ tự bạn truyền vào:

[[CODE:17]]

Một guard có đoạn code này, chạy trong context của method `create()` với metadata ở trên, sẽ cho `roles` chứa `['admin']`.

Để lấy metadata từ cả hai cấp và gộp lại (method này gộp được cả mảng lẫn object), dùng method `getAllAndMerge()`:

[[CODE:18]]

Kết quả là `roles` chứa `['admin', 'user']` (các giá trị được nối theo thứ tự của các target).

Với cả hai method này, bạn truyền tham chiếu decorator (hoặc metadata key) làm tham số thứ nhất, và một mảng các context target của metadata (tức là các lời gọi method `getHandler()` và/hoặc `getClass()`) làm tham số thứ hai.

#### Cách làm ở mức thấp

Như đã nói ở trên, thay vì dùng `Reflector#createDecorator`, bạn có thể dùng decorator có sẵn `@SetMetadata()` để gắn metadata vào handler.

[[CODE:19]]

> info **Hint** Decorator `@SetMetadata()` được import từ package `@nestjs/common`.

Cách khai báo trên gắn metadata `roles` (`roles` là metadata key và `['admin']` là giá trị tương ứng) vào method `create()`. Dù cách này chạy được, dùng trực tiếp `@SetMetadata()` trong route không phải là cách làm tốt. Thay vào đó, hãy tạo decorator của riêng bạn, như bên dưới:

[[CODE:20]]

Cách này gọn gàng và dễ đọc hơn, và giống với cách dùng `Reflector#createDecorator`. Điểm khác biệt là với `@SetMetadata()`, bạn kiểm soát được nhiều hơn metadata key và giá trị, và có thể tạo decorator nhận nhiều hơn một tham số.

Khi đã có custom decorator `@Roles()`, bạn có thể dùng nó để decorate method `create()`.

[[CODE:21]]

Để lấy (các) role của route (custom metadata), ta lại dùng class helper `Reflector`:

[[CODE:22]]

> info **Hint** Class `Reflector` được import từ package `@nestjs/core`.

Giờ, để đọc metadata của handler, dùng method `get()`.

[[CODE:23]]

Ở đây, thay vì tham chiếu decorator, bạn truyền metadata **key** (trong trường hợp này là `'roles'`) làm tham số thứ nhất. Mọi thứ khác giữ nguyên như ví dụ dùng `Reflector#createDecorator`.
