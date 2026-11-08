### Provider bất đồng bộ

Đôi khi việc khởi động ứng dụng cần được trì hoãn cho đến khi một hoặc nhiều **tác vụ bất đồng bộ** hoàn tất. Ví dụ, có thể bạn không muốn bắt đầu nhận request cho đến khi kết nối tới database đã được thiết lập. Provider bất đồng bộ cho phép bạn làm điều này.

Để tạo một provider bất đồng bộ, dùng `async/await` với cú pháp `useFactory`. Factory trả về một `Promise`, và hàm factory có thể `await` các tác vụ bất đồng bộ. Nest sẽ chờ promise được resolve rồi mới khởi tạo bất kỳ class nào phụ thuộc vào (inject) provider đó.

[[CODE:1]]

> info **Hint** Tìm hiểu thêm về cú pháp custom provider trong chương [custom provider](/fundamentals/custom-providers).

#### Injection

Provider bất đồng bộ được inject vào các thành phần khác thông qua token của chúng, giống như mọi provider khác. Trong ví dụ trên, bạn sẽ dùng `@Inject('ASYNC_CONNECTION')`.
