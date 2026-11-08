### Cloudflare Workers

Cloudflare Workers và Nest giải quyết những vấn đề khác nhau, và nhiều hệ thống dùng cả hai. Workers chạy các hàm nhỏ trên mạng lưới của Cloudflare, gần với từng người dùng, không có server nào phải duy trì chạy. Nest tổ chức một backend, thường là một process Node.js chạy lâu dài. Trang này giúp bạn lựa chọn.

#### Khi nào dùng cái nào

| Bạn đang xây gì | Phù hợp hơn | Tại sao |
| --- | --- | --- |
| Logic đứng trước một site hoặc một API: redirect, A/B test, viết lại header, kiểm tra token | Workers | Nó chạy gần mọi người dùng, trước khi request tới được origin của bạn |
| Một API nhỏ với vài route, và lưu lượng tới theo từng đợt đột biến hoặc gần như không có | Workers | Nó không tốn gì khi rảnh, và không có server nào phải vận hành |
| Một backend có nhiều module, hoặc có nhiều developer cùng làm | Nest | Module, dependency injection, guard và pipe cho nó một cấu trúc thống nhất, và service dễ test |
| Một database quan hệ có transaction và connection pool | Nest | Một process chạy lâu dài giữ được pool của nó. Một Worker tiếp cận database qua Hyperdrive hoặc D1 |
| Background job chạy nhiều phút, hoặc queue consumer | Nest | [Queue](/application/queues) và [scheduled job](/application/task-scheduling) chạy trong process của bạn. Workers có Queues, Cron Triggers và Workflows, là những thứ riêng của Cloudflare |
| Công việc nặng về CPU hoặc bộ nhớ, hoặc module Node.js native | Nest | Isolate của một Worker có giới hạn, được liệt kê bên dưới |
| WebSocket với nhiều phòng | Cả hai | Nest có [gateway](/websockets/gateways), còn Workers có Durable Objects |
| Thứ gì đó phải chạy trên cloud khác, hoặc trên server của riêng bạn | Nest | Nó chạy ở bất cứ đâu Node.js chạy được, trong khi các binding của Worker như KV và D1 gắn chặt code với Cloudflare |

Cloudflare [liệt kê các giới hạn của mình](https://developers.cloudflare.com/workers/platform/limits/), những giới hạn có thể thay đổi. Tại thời điểm viết bài, một isolate có 128 MB bộ nhớ và một giây để khởi động, và một request mặc định có 30 giây thời gian CPU, tối đa 5 phút với gói trả phí.

#### Dùng cả hai

Một Worker có thể đứng trước một ứng dụng Nest: nó trả lời những gì nó có thể ở edge, và chuyển phần còn lại đi tiếp. Cookie, header và body đi qua mà không bị thay đổi:

[[CODE:1]]

Khi đó Nest chạy trên bất kỳ host Node.js nào (xem [Deployment](/deployment)), kể cả [Cloudflare Containers](https://developers.cloudflare.com/containers/), dịch vụ chạy một container image cạnh các Workers của bạn.

#### Nest có chạy được trên một Worker không?

Có thể, nhưng Nest không chính thức hỗ trợ điều đó, và hiếm khi nó mang lại cái tốt nhất của cả hai. Workers hiện thực `node:http`, nên Express adapter khởi động được trong `workerd`. Một ứng dụng có một controller và một provider có kích thước khoảng 500 KB sau khi gzip. Những gì có thể xảy ra:

- **Dependency injection cần `@Inject()`.** Workers bundle bằng esbuild, công cụ không phát ra decorator metadata, nên một dependency cần được chỉ rõ token, như `constructor(@Inject(TodosService) todos: TodosService)`.
- **Các package tùy chọn phải được alias.** Nest chỉ load các package như `class-validator` và `@nestjs/microservices` nếu chúng được cài, nhưng bundler vẫn cố resolve chúng.
- **Ứng dụng bootstrap trong mỗi isolate mới**, và thời gian đó bị tính vào giới hạn khởi động. Trạng thái trong bộ nhớ không được dùng chung giữa các isolate.
- **Một số tính năng không có**, như [WebSocket gateway](/websockets/gateways), [shutdown hook](/fundamentals/lifecycle-events) và [transport microservice](/microservices/basics) TCP.

Nếu bạn muốn dùng Workers cho phần lớn backend, một framework được viết riêng cho chúng sẽ phù hợp hơn. Nếu bạn muốn dùng Nest, hãy chạy nó ở nơi nó có một process chạy lâu dài, và đặt một Worker phía trước.
