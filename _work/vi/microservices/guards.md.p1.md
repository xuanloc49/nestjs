### Guard

Guard của microservice hoạt động giống như [guard của ứng dụng HTTP thông thường](/guards). Khác biệt duy nhất là chúng nên throw `RpcException` thay vì `HttpException`. Khi một guard trả về `false`, Nest throw một `RpcException` với message `Forbidden resource`.

> info **Hint** Class `RpcException` được cung cấp từ package `@nestjs/microservices`.

#### Gắn guard

Ví dụ sau dùng một guard cấp method. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng guard cấp controller (tức là đặt decorator `@UseGuards()` trước class controller).

[[CODE:1]]

> info **Hint** Global guard được đăng ký trên ứng dụng HTTP chính không áp dụng cho các microservice được kết nối vào một [ứng dụng hybrid](/faq/hybrid-application) trừ khi bạn đặt tùy chọn `inheritAppConfig`. Xem [dùng chung cấu hình](/faq/hybrid-application#sharing-configuration).
