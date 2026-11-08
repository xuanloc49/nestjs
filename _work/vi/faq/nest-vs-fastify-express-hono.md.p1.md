### Nest so với Fastify, Express và Hono

Fastify, Express và Hono định tuyến request tới các handler của bạn, và bạn tự chọn hoặc tự viết những gì bao quanh chúng. Nest tổ chức toàn bộ backend, với module, dependency injection, guard, pipe và các package chính chủ, và nó chạy trên nền Express, Fastify hoặc `node:http` của chính Node. Vì vậy Nest không thay thế Fastify hay Express: chúng có thể là thứ mà Nest chạy trên đó. Trang này giúp bạn lựa chọn.

#### Khi nào dùng cái nào

| Bạn đang xây gì | Phù hợp hơn | Tại sao |
| --- | --- | --- |
| Một backend sẽ lớn lên: nhiều module hơn, nhiều developer hơn, một database, background job | Nest | Module, dependency injection, guard và pipe cho nó một cấu trúc thống nhất, và service dễ test |
| Một hệ thống cấp doanh nghiệp, với nhiều team và một codebase tồn tại lâu dài | Nest | Mọi team làm việc trong cùng một cấu trúc, và team lõi có cung cấp [hỗ trợ doanh nghiệp](https://enterprise.nestjs.com) |
| Một API nhỏ có xác thực, validation và một database | Nest hoặc Fastify | `nest new --minimal` bắt đầu từ [một file](/cli/usages#one-file-projects), và các package chính chủ bổ sung phần còn lại. Fastify làm điều tương tự với plugin và ít code quanh mỗi route hơn |
| Microservice qua Kafka, RabbitMQ, NATS hoặc gRPC | Nest | Các [transport](/microservices/basics) là chính chủ và dùng chung một mô hình lập trình |
| Một service sẽ chỉ có vài route, như một proxy hoặc một bên nhận webhook | Fastify hoặc Hono | Không có gì cần tổ chức |
| Một API trên Cloudflare Workers hoặc một edge runtime khác | Hono | Nó được xây trên Web Standards và chạy gốc ở đó. Xem [Cloudflare Workers](/faq/cloudflare-workers) |
| Một frontend Next.js dùng chung type route với API của nó, không cần sinh code | Hono | RPC client của nó suy ra type từ các route. Với Nest, [một package dùng chung](/recipes/nextjs) chứa schema và type thay vào đó |
| Một ứng dụng Express đang chạy tốt | Express, hoặc Nest từng route một | [Migrate từ Express](/recipes/express-migration) chạy cả hai song song |
| Tần suất request cao nhất trên những route gần như không làm gì | Fastify | Nó nhanh hơn Nest vài phần trăm. Xem [Hiệu năng](/faq/nest-vs-fastify-express-hono#performance) |

#### Mỗi cái đi kèm gì

| | Nest | Fastify | Express | Hono |
| --- | --- | --- | --- | --- |
| Module và dependency injection | [Có sẵn](/modules) | Plugin được đóng gói, không có container | Bạn tự thiết kế | Bạn tự thiết kế |
| Validate request | [Pipe có sẵn](/application/validation), với class hoặc bất kỳ library Standard Schema nào | JSON Schema trên mỗi route, có sẵn | Thêm một library | `@hono/zod-validator` hoặc tương tự |
| Xác thực | [`@nestjs/authentication`](/security/authentication) và [guard](/guards) | `@fastify/jwt` và các plugin khác | Passport hoặc middleware tự viết | `hono/jwt` và các middleware khác |
| OpenAPI | [`@nestjs/swagger`](/openapi/introduction) | `@fastify/swagger` | Thêm một library | `@hono/zod-openapi` |
| WebSocket | [Gateway](/websockets/gateways), với Socket.IO hoặc `ws` | `@fastify/websocket` | Thêm một library | Các helper theo runtime như `@hono/node-ws` |
| Background job | [`@nestjs/bullmq`](/application/queues) | Thêm một library | Thêm một library | Thêm một library |
| Transport microservice | [`@nestjs/microservices`](/microservices/basics) | Thêm một library | Thêm một library | Thêm một library |
| Streaming | [Trả về một `Response` hoặc một stream](/http/streaming-responses) | Gửi một stream từ handler | Ghi vào response | `streamSSE` và các helper khác |
| Testing | [`@nestjs/testing`](/fundamentals/testing), có thể thay thế provider | `fastify.inject()` | Thêm Supertest | `app.request()` |
| Type dùng chung với frontend | [Một package dùng chung](/recipes/nextjs) | Thêm một library | Thêm một library | RPC client có sẵn |

#### Một ứng dụng Nest có thể nhỏ tới mức nào

`nest new my-api --minimal` sinh ra một ứng dụng có code nằm trong một file, `src/main.ts`:

[[CODE:1]]

Nó vẫn là cùng ứng dụng đó khi lớn lên. `nest g resource users` thêm một module, và khi `src/main.ts` trở nên dài, bạn chuyển root module sang file riêng. Xem [Project một file](/cli/usages#one-file-projects).

Fastify, Express và Hono bắt đầu với ít dòng code hơn, đây vẫn là một lợi thế chừng nào ứng dụng còn nhỏ. Khi nó lớn lên, việc xác thực nằm ở đâu, các phần của nó dùng chung service thế nào, và test thay dependency ra sao đều trở thành những thứ bạn phải tự thiết kế. Nest quyết định những điều đó ngay từ đầu.

#### Hiệu năng

Số request mỗi giây trên `GET /`, với mỗi server trả lời `Hello world!`, dùng `wrk -t4 -c100` trong 8 giây sau 3 giây khởi động, trên Node.js 24.20. Mỗi con số là trung vị của 3 vòng:

| Server | `GET /` |
| --- | --- |
| Fastify | 57.1k |
| Nest trên Node | 55.6k |
| Hono trên Node | 53.1k |
| Nest trên Fastify | 52.6k |
| Express | 37.0k |
| Nest trên Express | 37.0k |

Như vậy với [`NodeAdapter`](/http/performance#node-adapter), Nest xử lý ít hơn Fastify thuần khoảng 3% request mỗi giây, nhiều hơn Hono trên Node khoảng 5%, và nhiều hơn Express thuần khoảng 50%.

Một vòng riêng trên M1 Pro, với một route parameter và một JSON body:

| Server | `GET /users/:id` | `POST /echo` (JSON) |
| --- | --- | --- |
| Express | 35.6k | 30.1k |
| Fastify | 54.0k | 43.5k |
| Nest trên Express | 34.5k | 28.2k |
| Nest trên Fastify | 48.4k | 40.2k |
| Nest trên Node | 51.0k | 42.4k |

Ở đây Nest trên Node đạt mức chênh 3-6% so với Fastify thuần và vẫn nhanh hơn Express thuần 41-43%.

Để tự chạy các benchmark này, hãy làm theo các bước trong [nestjs/nest#18063](https://github.com/nestjs/nest/pull/18063#reproducing-the-benchmark), nơi cũng có các server cho Hono, Koa, Elysia và AdonisJS. Các máy khác cho ra các khoảng chênh khác, và con số của Hono chỉ bao gồm Node, không bao gồm các runtime khác mà nó chạy được.

Các route này gần như không làm gì. Một route truy vấn database hoặc gọi các service khác tiêu phần lớn thời gian để chờ chúng, nên với hầu hết ứng dụng, những khác biệt này sẽ không quyết định lựa chọn.

#### Chuyển sang Nest sau này

Lựa chọn không nhất thiết là cuối cùng:

- Từ Fastify, Nest chạy trên cùng server thông qua `FastifyAdapter`, và các plugin của bạn vẫn tiếp tục hoạt động. Xem [Migrate từ Fastify](/recipes/fastify-migration).
- Từ Express, các route được chuyển từng cái một với cả hai cùng phục vụ request, hoặc tất cả cùng lúc. Xem [Migrate từ Express](/recipes/express-migration).
