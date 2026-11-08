### HTTP adapter

Đôi khi, bạn có thể cần truy cập HTTP server bên dưới, từ bên trong application context của Nest hoặc từ bên ngoài nó.

Mọi instance HTTP server hoặc library gốc (riêng của nền tảng) (ví dụ Express hay Fastify) đều được bọc trong một **adapter**. Adapter được đăng ký như một provider có sẵn ở phạm vi global, nên bạn có thể lấy nó từ application context hoặc inject nó vào các provider khác.

#### Cách làm bên ngoài application context

Để lấy tham chiếu tới `HttpAdapter` từ bên ngoài application context, hãy gọi method `getHttpAdapter()`:

[[CODE:1]]

#### Dưới dạng injectable

Để lấy tham chiếu tới `HttpAdapterHost` từ bên trong application context, hãy inject nó như mọi provider khác (ví dụ dùng constructor injection):

[[CODE:2]]

> info **Hint** `HttpAdapterHost` được import từ package `@nestjs/core`.

`HttpAdapterHost` **không phải** là một `HttpAdapter` thực sự. Để lấy instance `HttpAdapter` thực sự, hãy đọc thuộc tính `httpAdapter` của nó:

[[CODE:3]]

`httpAdapter` là instance HTTP adapter bọc framework bên dưới. Nó là một instance của `ExpressAdapter`, `FastifyAdapter` hoặc `NodeAdapter` (tất cả đều kế thừa `AbstractHttpAdapter`).

Object adapter cung cấp một số method để tương tác với HTTP server. Để truy cập trực tiếp instance của library (ví dụ instance Express), hãy gọi method `getInstance()`:

[[CODE:4]]

#### Event lắng nghe

Để chạy code khi server bắt đầu lắng nghe các request đi vào, hãy subscribe stream `listen$`:

[[CODE:5]]

`HttpAdapterHost` cũng cung cấp một thuộc tính boolean `listening` cho biết server hiện có đang lắng nghe hay không:

[[CODE:6]]
