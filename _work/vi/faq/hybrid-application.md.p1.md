### Ứng dụng hybrid

Một ứng dụng hybrid lắng nghe request từ hai hoặc nhiều nguồn khác nhau. Nó có thể kết hợp một HTTP server với một microservice listener, hoặc kết hợp nhiều microservice listener khác nhau. Method `createMicroservice()` không hỗ trợ nhiều server, nên trong trường hợp này bạn tự tạo và khởi động từng microservice. Để làm vậy, hãy kết nối các instance `INestMicroservice` vào instance `INestApplication` bằng method `connectMicroservice()`.

[[CODE:1]]

> info **Hint** Method `app.listen(port)` khởi động một HTTP server trên port được chỉ định. Nếu ứng dụng của bạn không xử lý HTTP request, hãy dùng method `app.init()` thay vào đó.

> warning **Notice** Thứ tự của các lời gọi này là quan trọng. Với `await app.startAllMicroservices()` đứng trước (như ở trên), các microservice bắt đầu tiêu thụ message **trước khi** các lifecycle hook của ứng dụng (như `onModuleInit` và `onApplicationBootstrap`) hoàn tất. Hãy gọi `app.listen()` (hoặc `app.init()`) trước `startAllMicroservices()` nếu các handler của bạn không được nhận message cho tới khi mọi module đã khởi tạo xong hoàn toàn.

Để kết nối nhiều instance microservice, hãy gọi `connectMicroservice()` một lần cho mỗi microservice:

[[CODE:2]]

Trong một ứng dụng hybrid có nhiều microservice, bạn có thể gắn `@MessagePattern()` với một transport strategy duy nhất (ví dụ NATS) bằng cách truyền một tham số thứ hai xác định transport. Với các strategy có sẵn, đây là một giá trị của enum `Transport`; với một [custom transporter](/microservices/custom-transport), đó là symbol `transportId` của class server của nó.

[[CODE:3]]

> info **Hint** `@Payload()`, `@Ctx()`, `Transport` và `NatsContext` được import từ `@nestjs/microservices`. `XYZServer.Transport` ở đây đại diện cho symbol `transportId` mà custom transporter cung cấp.

#### Dùng chung cấu hình

Mặc định, các microservice được kết nối không kế thừa các pipe, interceptor, guard và filter global được cấu hình cho ứng dụng chính (dựa trên HTTP). Điều này áp dụng cho cả các enhancer được đăng ký bằng các method `useGlobal*()` lẫn những enhancer được đăng ký làm provider với các token `APP_PIPE`, `APP_INTERCEPTOR`, `APP_GUARD` và `APP_FILTER`.
Để kế thừa cấu hình này, hãy đặt thuộc tính `inheritAppConfig` trong options object được truyền làm tham số thứ hai của `connectMicroservice()`:

[[CODE:4]]

> info **Hint** Một microservice được kết nối đăng ký các message handler của nó ngay khi `connectMicroservice()` được gọi. Khi bạn dùng `inheritAppConfig`, hãy gọi `app.useGlobalPipes()`, `app.useGlobalGuards()` và các method `useGlobal*()` khác **trước** `connectMicroservice()`, nếu không các enhancer mà chúng đăng ký sẽ không áp dụng cho các handler của microservice.
