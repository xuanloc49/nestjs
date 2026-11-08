### HTTPS

Để tạo một ứng dụng dùng giao thức HTTPS, hãy đặt thuộc tính `httpsOptions` trong options object được truyền cho method `NestFactory.create()`:

[[CODE:1]]

Nếu bạn dùng `FastifyAdapter`, hãy tạo ứng dụng như sau:

[[CODE:2]]

#### Nhiều server chạy đồng thời

Recipe sau cho thấy cách tạo một ứng dụng Nest lắng nghe đồng thời trên nhiều port (ví dụ trên một port HTTP và một port HTTPS):

[[CODE:3]]

Vì chúng ta tự tạo các server bằng `http.createServer()` và `https.createServer()`, Nest không đóng chúng khi bạn gọi `app.close()` hoặc khi process nhận tín hiệu kết thúc. Bạn cần tự đóng chúng, ví dụ bằng một provider implement hook `OnApplicationShutdown`:

[[CODE:4]]

> info **Hint** `ExpressAdapter` được import từ package `@nestjs/platform-express`. Các module `http` và `https` có sẵn trong Node.js.

> warning **Warning** Recipe này không hoạt động với [GraphQL subscription](/graphql/subscriptions).
