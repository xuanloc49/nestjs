### Interceptor

Không có khác biệt nào giữa [interceptor thông thường](/interceptors) và interceptor của WebSocket. Ví dụ sau dùng một interceptor cấp method được khởi tạo thủ công. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng interceptor cấp gateway (tức là gắn `@UseInterceptors()` cho class gateway). Global interceptor được đăng ký bằng `app.useGlobalInterceptors()` hoặc token `APP_INTERCEPTOR` cũng áp dụng cho gateway.

[[CODE:1]]
