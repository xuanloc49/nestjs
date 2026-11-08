### Exception filter

Khác biệt duy nhất giữa lớp [exception filter](/exception-filters) của HTTP và lớp tương ứng của microservice là microservice nên throw `RpcException` thay vì `HttpException`.

[[CODE:1]]

> info **Hint** Class `RpcException` được import từ package `@nestjs/microservices`.

Nest xử lý exception được throw và trả về một object `error` với cấu trúc sau:

[[CODE:2]]

Nếu bạn truyền một object cho constructor của `RpcException` thay vì một chuỗi, Nest sẽ trả về nguyên object đó.

> warning **Warning** Một event handler không có response stream. Một lỗi mà filter throw lại cho một handler `@EventPattern()` sẽ không bao giờ tới được producer, nên hãy xử lý lỗi bên trong filter.

#### Filter

Exception filter của microservice hoạt động giống exception filter của HTTP, với một khác biệt: method `catch()` phải trả về một `Observable`.

[[CODE:3]]

> warning **Warning** Global exception filter được đăng ký trên ứng dụng HTTP chính không áp dụng cho các microservice được kết nối vào một [ứng dụng hybrid](/faq/hybrid-application) trừ khi bạn đặt tùy chọn `inheritAppConfig`. Xem [dùng chung cấu hình](/faq/hybrid-application#sharing-configuration).

Ví dụ sau dùng một filter cấp method được khởi tạo thủ công. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng filter cấp controller (tức là đặt decorator `@UseFilters()` trước class controller).

[[CODE:4]]

#### Kế thừa

Thông thường, bạn sẽ tạo các exception filter tùy chỉnh hoàn toàn theo yêu cầu của ứng dụng. Tuy nhiên, trong một số trường hợp, bạn có thể muốn kế thừa **exception filter lõi** và override hành vi của nó dựa trên một số yếu tố.

Để giao việc xử lý exception cho base filter, hãy kế thừa `BaseRpcExceptionFilter` và gọi method `catch()` được kế thừa.

[[CODE:5]]

Phần hiện thực ở trên chỉ là một khung để minh họa cách làm. Phần hiện thực exception filter mở rộng của bạn sẽ bao gồm **logic nghiệp vụ** của riêng bạn (ví dụ xử lý các điều kiện khác nhau).
