### Model Context Protocol (MCP)

`@nestjs/mcp` biến một ứng dụng Nest thành một Model Context Protocol (MCP) server, với các tool, resource và prompt chính là các method của provider của bạn.

Cửa hàng online bán thức ăn và đồ dùng cho mèo trả lời rất nhiều email: "đơn hàng của tôi đâu rồi?", "tôi có thể đổi địa chỉ giao hàng không?", "hạt cá hồi đã có hàng lại chưa?". Bộ phận hỗ trợ làm việc với một AI assistant (Claude, ChatGPT, một agent trong hệ thống help desk của họ), và assistant chỉ có thể trả lời khi nó thấy được những gì API đơn hàng thấy.

[Model Context Protocol](https://modelcontextprotocol.io) (MCP) là cách một assistant tiếp cận một ứng dụng. Ứng dụng chạy một **MCP server**, và đưa ra ba loại thứ cho assistant, tức **MCP client**:

- **Tool**, các hành động mà model gọi kèm argument: tra cứu một đơn hàng, đổi địa chỉ của nó.
- **Resource**, dữ liệu mà client đọc theo URI: danh mục sản phẩm, một đơn hàng.
- **Prompt**, các mẫu mà người dùng chọn: "soạn phản hồi về đơn hàng này".

`@nestjs/mcp` biến các method của provider thành tool, resource và prompt, mỗi loại một decorator. Chúng chạy qua các guard, interceptor, pipe và exception filter mà route của bạn dùng, và server được phục vụ từ chính ứng dụng Nest bạn đang có: qua Streamable HTTP cho các assistant từ xa, và qua stdio cho một assistant khởi chạy nó như một process cục bộ.

Trong bài hướng dẫn này, bạn sẽ cho API đơn hàng của cửa hàng một MCP server:

- Các [tool](/mcp/primitives) để tìm một đơn hàng và đổi địa chỉ giao hàng của nó, với schema mà model nhìn thấy và server validate.
- Danh mục sản phẩm dưới dạng một [resource](/mcp/primitives#resources), và mỗi đơn hàng dưới dạng một resource template.
- Một [prompt](/mcp/primitives#prompts) để soạn phản hồi.
- Một [guard](/mcp/primitives#guards-interceptors-pipes-and-filters) chỉ cho phép bộ phận hỗ trợ thay đổi đơn hàng, và một interceptor log mỗi lời gọi.
- [OAuth 2.1](/mcp/primitives#authorization) trên HTTP endpoint, với identity provider của cửa hàng, và một scope cho việc thay đổi đơn hàng.
- Cùng server đó qua [stdio](/mcp/transports#over-stdio), và các [test](/mcp/testing) gọi nó trong bộ nhớ.

#### Cài đặt

Cài package, MCP TypeScript SDK mà nó xây dựng trên đó, và Zod, cho các schema:

[[CODE:1]]

> info **Hint** Các schema có thể đến từ bất kỳ library [Standard Schema](https://standardschema.dev) nào tạo ra được JSON Schema: Zod 4.2 trở lên và ArkType dùng được ngay, Valibot qua `toStandardJsonSchema()` từ `@valibot/to-json-schema`, và một tài liệu JSON Schema bạn đã có qua `fromJsonSchema()` từ `@modelcontextprotocol/server`. Schema Zod 3 bị từ chối lúc khởi động: SDK không thể biến chúng thành JSON Schema.

#### Đăng ký module

Import `McpModule` trong root module. `name` và `version` định danh server với client; `instructions` cho model biết cách dùng nó:

[[CODE:2]]

Module tìm tool, resource và prompt trên mọi provider của ứng dụng, lúc khởi động. `include: [OrdersModule]` giới hạn việc tìm kiếm trong các module bạn liệt kê.

Khởi động ứng dụng như thường lệ:

[[CODE:3]]

MCP endpoint được phục vụ tại `http://localhost:3000/mcp`, cạnh các route riêng của ứng dụng. Cùng module đó cũng có thể được phục vụ qua stdio, cho một assistant khởi chạy ứng dụng như một process cục bộ: xem [Transport](/mcp/transports).

#### Một lời gọi được phục vụ thế nào

Khi ứng dụng khởi động, module duyệt qua các provider của nó để tìm các method được gắn `@Tool()`, `@Resource()`, `@ResourceTemplate()` và `@Prompt()`. Nó biến mỗi schema thành JSON Schema một lần, và thất bại ngay lúc khởi động với những gì lẽ ra chỉ hỏng về sau: hai tool cùng tên, một tên tool nằm ngoài quy tắc đặt tên của MCP, một provider request-scoped, `scopes` mà không có `auth`.

Sau đó mỗi HTTP request tới endpoint được phục vụ độc lập. Module dựng một MCP server cho nó từ những gì đã tìm được lúc khởi động, [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk) lo phần giao thức, và một lời gọi đi qua các bước sau:

1. Với `auth`, access token được xác minh, và các scope của lời gọi được kiểm tra.
2. SDK validate các argument theo schema. Những argument bị nó từ chối không bao giờ tới được method của bạn: model được báo điều gì sai, và có thể thử lại.
3. Các guard của bạn chạy, rồi đến interceptor và pipe, như quanh một route handler.
4. Method chạy, với các argument và context của lời gọi.
5. Những gì nó trả về trở thành kết quả MCP. Những gì nó throw đi qua các exception filter của bạn, và trở thành một lỗi mà client hiểu được.

Không có gì được giữ lại giữa các request, nên server chạy trên bao nhiêu instance tùy thích, sau bất kỳ load balancer nào. Qua stdio, một server phục vụ kết nối chừng nào process còn sống.

#### Cấu hình bất đồng bộ

`forRootAsync()` nhận các tùy chọn từ một factory, một `useClass` hoặc một provider `useExisting`. `path`, `endpointVersion`, `decorators` và `imports` vẫn ở cấp ngoài cùng, vì các route của module đã được biết khi nó được định nghĩa; một verifier từ factory là một instance:

[[CODE:4]]

#### Tùy chọn của module

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `name`, `version` | | Bắt buộc. Danh tính của server, được gửi tới client |
| `title`, `description`, `websiteUrl`, `icons` | | Thêm thông tin về danh tính, để client hiển thị |
| `instructions` | | Model nên dùng server thế nào |
| `include` | mọi module | Các module mà provider của chúng được tìm kiếm tool, resource và prompt |
| `path` | `'mcp'` | Route của HTTP endpoint. `false` để không có. Ở cấp ngoài cùng của `forRootAsync()` |
| `endpointVersion` | | Phiên bản của endpoint, khi bật versioning. Ở cấp ngoài cùng của `forRootAsync()` |
| `decorators` | `[]` | Các class decorator được áp dụng cho controller của endpoint. Ở cấp ngoài cùng của `forRootAsync()` |
| `imports` | `[]` | Các module mà export của chúng được một class `verifier` inject. Ở cấp ngoài cùng của `forRootAsync()` |
| `http.legacy` | `'stateless'` | `'reject'` chỉ phục vụ bản revision 2026-07-28 |
| `http.responseMode` | `'auto'` | `'json'` hoặc `'sse'` cố định dạng response của các request 2026-07-28 |
| `http.allowedOrigins` | `localhost`, `127.0.0.1`, `[::1]` | Các hostname mà header `Origin` của request được phép chỉ tới; request không có header này sẽ được cho qua. Một danh sách sẽ thay thế mặc định, `false` tắt việc kiểm tra |
| `http.allowedHosts` | không kiểm tra | Các hostname mà header `Host` phải chỉ tới |
| `http.maxRequestBodySize` | 4 MiB | Cho các body mà platform chưa parse |
| `auth.verifier` | | Một class hoặc một instance có `verifyAccessToken(token)` |
| `auth.resource` | | URL chuẩn của server, và là audience của các token của nó |
| `auth.authorizationServers` | | Các issuer có token được chấp nhận |
| `auth.scopesSupported`, `auth.requiredScopes` | | Các scope được công bố, và các scope mà mọi request đều cần |
| `auth.resourceName`, `auth.resourceDocumentation` | | Thêm metadata về protected resource |
| `stdio.legacy` | `'serve'` | `'reject'` từ chối các kết nối mở đầu bằng handshake 2025 |

#### Ví dụ

Một ví dụ chạy được có [tại đây](https://github.com/nestjs/mcp/tree/master/sample).
