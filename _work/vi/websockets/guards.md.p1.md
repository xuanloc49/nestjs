### Guard

Không có khác biệt căn bản nào giữa guard của WebSocket và [guard của ứng dụng HTTP thông thường](/guards). Khác biệt duy nhất là thay vì throw `HttpException`, bạn nên throw `WsException`. Nếu một guard trả về `false`, Nest throw một `WsException` với message `'Forbidden resource'`.

> info **Hint** Class `WsException` được cung cấp từ package `@nestjs/websockets`.

#### Gắn guard

Ví dụ sau dùng một guard cấp method. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng guard cấp gateway (tức là gắn `@UseGuards()` cho class gateway). Global guard được đăng ký bằng `app.useGlobalGuards()` hoặc token `APP_GUARD` cũng áp dụng cho gateway.

[[CODE:1]]
