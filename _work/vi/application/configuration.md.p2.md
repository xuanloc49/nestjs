#### Biến có thể expand

Package `@nestjs/config` hỗ trợ expand biến môi trường. Với kỹ thuật này, bạn có thể tạo các biến môi trường lồng nhau, trong đó một biến được tham chiếu bên trong định nghĩa của biến khác. Ví dụ:

[[CODE:45]]

Với cách khai báo này, biến `SUPPORT_EMAIL` được resolve thành `'support@mywebsite.com'`. Cú pháp `${{ '{' }}...{{ '}' }}` kích hoạt việc resolve giá trị của biến `APP_URL` bên trong định nghĩa của `SUPPORT_EMAIL`.

> info **Hint** Với tính năng này, bên trong package `@nestjs/config` dùng [dotenv-expand](https://github.com/motdotla/dotenv-expand).

Bật tính năng expand biến môi trường bằng thuộc tính `expandVariables` của options object truyền vào `ConfigModule.forRoot()`, như bên dưới. Thay vì `true`, bạn cũng có thể truyền một object chứa các tùy chọn cho `dotenv-expand`.

[[CODE:46]]

#### Dùng trong `main.ts`

Dù cấu hình được lưu trong một service, bạn vẫn có thể dùng nó trong file `main.ts`, ví dụ để đọc các biến như port của ứng dụng hoặc host cho CORS.

Để truy cập, dùng method `app.get()` với class service:

[[CODE:47]]

Sau đó bạn có thể dùng nó như bình thường, bằng cách gọi method `get()` với key cấu hình:

[[CODE:48]]
