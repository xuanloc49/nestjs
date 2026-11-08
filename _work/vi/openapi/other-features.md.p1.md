### Các tính năng khác

Trang này nói về các tính năng khác của module Swagger mà bạn có thể thấy hữu ích.

#### Global prefix

Để bỏ qua global prefix được đặt qua `setGlobalPrefix()`, hãy dùng tùy chọn `ignoreGlobalPrefix`:

[[CODE:1]]

#### Parameter global

Để định nghĩa parameter cho mọi route, hãy dùng `DocumentBuilder`:

[[CODE:2]]

#### Response global

Để định nghĩa response global cho mọi route, hãy dùng `DocumentBuilder`. Điều này hữu ích để thiết lập các response nhất quán trên mọi endpoint trong ứng dụng, như các mã lỗi `401 Unauthorized` hay `500 Internal Server Error`.

[[CODE:3]]

#### Nhiều đặc tả

`SwaggerModule` hỗ trợ nhiều đặc tả. Nói cách khác, bạn có thể phục vụ các tài liệu khác nhau, với các UI khác nhau, trên các endpoint khác nhau.

Để hỗ trợ nhiều đặc tả, ứng dụng của bạn phải được viết theo cách tiếp cận module hóa. Method `createDocument()` nhận một tham số thứ ba, `extraOptions`, là một object có thuộc tính `include`. Thuộc tính `include` nhận một mảng module.

Thiết lập hỗ trợ nhiều đặc tả như bên dưới:

[[CODE:4]]

Giờ hãy khởi động server bằng lệnh sau:

[[CODE:5]]

Truy cập `http://localhost:3000/api/cats` để xem Swagger UI cho cats:

<figure><img src="/assets/swagger-cats.png" /></figure>

Tương ứng, `http://localhost:3000/api/dogs` sẽ đưa ra Swagger UI cho dogs:

<figure><img src="/assets/swagger-dogs.png" /></figure>

#### Dropdown trên thanh explorer

Để liệt kê nhiều đặc tả trong menu dropdown của thanh explorer, hãy đặt `explorer: true` và cấu hình `swaggerOptions.urls` trong `SwaggerCustomOptions`.

> info **Hint** Hãy đảm bảo `swaggerOptions.urls` trỏ tới định dạng JSON của các tài liệu Swagger. Để chỉ định đường dẫn của tài liệu JSON, hãy dùng tùy chọn `jsonDocumentUrl` của `SwaggerCustomOptions`. Để biết thêm các tùy chọn, xem [tùy chọn setup](/openapi/introduction#setup-options).

Đây là cách chọn nhiều đặc tả từ một dropdown trên thanh explorer:

[[CODE:6]]

Ví dụ này thiết lập một API chính cùng với các đặc tả riêng cho cats và dogs, mỗi đặc tả đều truy cập được từ dropdown trên thanh explorer.
