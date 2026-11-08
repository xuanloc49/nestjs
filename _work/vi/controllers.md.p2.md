#### Cho controller chạy

Dù `CatsController` đã được định nghĩa đầy đủ, Nest vẫn chưa biết đến nó và sẽ không tạo instance của class này.

Controller luôn phải thuộc về một module, vì vậy ta khai báo mảng `controllers` trong decorator `@Module()`. Vì hiện chưa định nghĩa module nào khác ngoài root module `AppModule`, ta sẽ dùng nó để đăng ký `CatsController`:

[[CODE:29]]

Khi metadata này đã được gắn vào class module thông qua decorator `@Module()`, Nest sẽ biết cần mount những controller nào.

#### Cách dùng riêng của library

Đến giờ, ta đã tìm hiểu cách chuẩn của Nest để thao tác với response. Cách còn lại là dùng [response object](https://expressjs.com/en/api.html#res) riêng của library, được inject bằng decorator `@Res()`. Để thấy rõ sự khác biệt, hãy viết lại `CatsController` như sau:

[[CODE:30]]

Cách này linh hoạt hơn vì cho bạn toàn quyền điều khiển response object (ví dụ: thao tác header và dùng các tính năng riêng của library), nhưng nên dùng một cách thận trọng. Nhìn chung, code sẽ kém rõ ràng hơn và có một số nhược điểm. Nhược điểm chính là code của bạn bị phụ thuộc vào nền tảng, vì mỗi library bên dưới có thể cung cấp API khác nhau trên response object. Nó cũng khiến việc test khó hơn, chẳng hạn bạn phải mock response object.

Ngoài ra, cách này làm mất tương thích với các tính năng của Nest dựa trên cơ chế xử lý response chuẩn, như interceptor và các decorator `@HttpCode()` / `@Header()`. Để khắc phục, hãy bật tùy chọn `passthrough`:

[[CODE:31]]

Bằng cách này, bạn vẫn tương tác được với response object gốc (ví dụ, set cookie hoặc header theo điều kiện cụ thể) trong khi để framework lo phần còn lại.
