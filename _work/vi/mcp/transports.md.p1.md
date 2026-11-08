### Transport

Server được phục vụ qua hai transport: Streamable HTTP, từ chính ứng dụng Nest bạn đang có, cho các assistant kết nối qua mạng, và stdio, từ một standalone application context, cho một assistant khởi chạy server như một process cục bộ. Cả hai đều phục vụ cùng các tool, resource và prompt.

#### HTTP endpoint

Endpoint là một controller mà module thêm vào, tại `path` (mặc định `'mcp'`): global prefix, versioning, middleware, CORS và HTTP guard áp dụng cho nó như với mọi route, nên với `app.setGlobalPrefix('api')` nó sẽ nằm ở `/api/mcp`, còn `app.setGlobalPrefix('api', {{ '{' }} exclude: ['mcp'] {{ '}' }})` giữ nó ở `/mcp`. `endpointVersion` đặt phiên bản của nó khi bật versioning (`VERSION_NEUTRAL` giữ nó ở `/mcp` bất chấp `defaultVersion`), còn `decorators` áp dụng các class decorator cho nó, chẳng hạn `[Public()]` để miễn nó khỏi một global authentication guard, hoặc `[UseGuards(ApiKeyGuard)]`.

Một server chỉ có các agent của riêng bạn gọi tới, thay vì người dùng qua một assistant, có thể không cần OAuth. Thay vào đó, một guard trên route của endpoint sẽ kiểm tra một API key, thứ mà các client kết nối tới server từ xa cho phép bạn gửi dưới dạng request header:

[[CODE:1]]

[[CODE:2]]

Một request không có key sẽ nhận 403 trước khi bất kỳ MCP message nào được đọc.

Nó phục vụ mọi request theo kiểu stateless: mỗi request có một server instance riêng, và không có gì được giữ lại giữa các request. Nhiều instance của ứng dụng đứng sau một load balancer không cần session affinity và không dùng chung gì cả. Client của bản revision giao thức 2026-07-28 và của các bản 2025 đều được phục vụ trên cùng endpoint; `http: {{ '{' }} legacy: 'reject' {{ '}' }}` khiến nó chỉ phục vụ 2026-07-28.

Một request 2026-07-28 được trả lời bằng một JSON body, hoặc bằng một stream server-sent event khi method gửi gì đó trước kết quả của nó, chẳng hạn các thông báo tiến độ. `http: {{ '{' }} responseMode: 'json' {{ '}' }}` không bao giờ stream, và bỏ các thông báo tiến độ; `'sse'` thì luôn stream.

Có vài thiết lập quan trọng trong production:

- **Các trang từ site khác.** Endpoint kiểm tra header `Origin`: một request từ một trang web trên site khác, được tạo bởi trình duyệt của người dùng, sẽ nhận 403. Một request không có header `Origin` sẽ được cho qua, nên assistant, CLI và các hosted connector, vốn không phải trình duyệt và không gửi header này, không bị ảnh hưởng. Mặc định, chỉ các trang trên `localhost`, `127.0.0.1` và `[::1]` được cho qua. Để phục vụ một client chạy trên trình duyệt, hãy liệt kê hostname của nó, `http: {{ '{' }} allowedOrigins: ['support.catstore.example'] {{ '}' }}` (danh sách này thay thế mặc định), hoặc tắt việc kiểm tra bằng `allowedOrigins: false`.
- **DNS rebinding.** Một server bind vào `localhost` cũng có thể bị truy cập bởi một trang có domain riêng resolve về `127.0.0.1`: các request của nó ghi domain đó làm `Host`. Hãy liệt kê các host mà server trả lời, `http: {{ '{' }} allowedHosts: ['localhost', '127.0.0.1', '[::1]'] {{ '}' }}`, và các request có header `Host` khác sẽ nhận 403. Header `Host` không được kiểm tra trừ khi bạn đặt `allowedHosts`.
- **Kích thước body.** Argument của tool tới trong body của request, thứ mà body parser của platform đọc trước: giới hạn mặc định của Express là 100 KB. Hãy tăng nó bằng `app.useBodyParser('json', {{ '{' }} limit: '4mb' {{ '}' }})`.
- **CORS.** Một client chạy trên trình duyệt ở origin khác cần được liệt kê ở cả hai nơi: trong `allowedOrigins`, theo hostname, và trong cấu hình CORS của bạn, cấu hình này cũng cho phép các request header `Authorization`, `Content-Type`, `Mcp-Protocol-Version`, `Mcp-Method` và `Mcp-Name` và expose `WWW-Authenticate`: `app.enableCors({{ '{' }} origin: ['https://support.catstore.example'], exposedHeaders: ['WWW-Authenticate'] {{ '}' }})`.

Cho một dashboard hỗ trợ tại `https://support.catstore.example` gọi server từ trình duyệt, với argument của tool lớn hơn mức Express cho phép mặc định:

[[CODE:3]]

[[CODE:4]]

#### Qua stdio

Một assistant trên máy của người dùng (Claude Desktop, Claude Code, một IDE) có thể khởi chạy server như một process cục bộ, và giao tiếp với nó qua stdin và stdout. Hãy phục vụ cùng module đó từ một standalone application context:

[[CODE:5]]

stdout mang giao thức, mà logger mặc định của Nest lại ghi vào đó: `McpStdioLogger` ghi mọi level ra stderr, nơi client hiển thị như log của server. `listen()` resolve khi client đóng stdin, và khi đó `app.close()` cho phép process thoát. Qua stdio, đặc tả lấy credential từ môi trường, không phải từ OAuth, nên `scopes` không được kiểm tra ở đó; guard vẫn chạy. Hãy đặt `path: false` trong một ứng dụng chỉ phục vụ stdio.

Client khởi động process từ một lệnh. Các assistant trên desktop và IDE nhận nó trong một cấu hình như thế này, ở đây kèm một biến môi trường cho server:

[[CODE:6]]

Process thuộc về một người dùng, trên máy của họ, chừng nào client còn chạy nó. Ở đó không có OAuth: những gì server cần, chẳng hạn một API key, đến từ môi trường mà client truyền vào, và các provider của bạn đọc nó từ `process.env`. Client của cả hai thời kỳ giao thức đều được phục vụ; `stdio: {{ '{' }} legacy: 'reject' {{ '}' }}` từ chối một kết nối mở đầu bằng handshake 2025.

Một bản build có thể phục vụ cả hai transport: `main.ts` khởi động ứng dụng HTTP, còn các client khởi chạy server sẽ chạy `stdio.ts`.

#### NestJS Observe

Khi có [NestJS Observe](https://observe.nestjs.com) (`@nestjs/observe`) trong ứng dụng, mỗi lời gọi MCP sẽ mang tên operation của nó, `tools/call find-order` hoặc `resources/read orders://{{ '{' }}orderId{{ '}' }}`, thay vì tất cả đều là `POST /mcp`. Không có gì phải cấu hình.

#### Checklist cho production

- `auth` được cấu hình trên một server có thể truy cập từ mạng, với `resource` là URL công khai của nó.
- `allowedHosts` trên một server bind vào `localhost`.
- Các client chạy trên trình duyệt gọi tới server, nếu có, được liệt kê trong `allowedOrigins` và trong các CORS origin của bạn: mặc định, chỉ các trang trên localhost mới được cho qua.
- Giới hạn của body parser lớn hơn argument lớn nhất của các tool.
- Mô tả tool và các đoạn text `.describe()` được viết cho model đọc: đó là tất cả những gì nó biết về tool của bạn.
- `annotations.readOnlyHint` trên các tool không thay đổi gì, để client không hỏi người dùng trước mỗi lời gọi.
- `McpStdioLogger` trong entry point stdio: bất cứ thứ gì khác ghi ra stdout đều làm hỏng giao thức.
