### Migration

Một MCP server được xây bằng package cộng đồng `@rekog/mcp-nest` chuyển sang `@nestjs/mcp` với phần lớn là các thay đổi máy móc: các decorator giữ nguyên tên, còn tool, resource và prompt vẫn là method của các class của bạn. Trang này ánh xạ cả hai API của nó, API `McpModule.forRoot()` của các bản release 1.x và API `McpStrategy` của 2.x, sang `@nestjs/mcp`.

#### Package

`@nestjs/mcp` được xây trên phiên bản 2 của MCP TypeScript SDK, `@modelcontextprotocol/server`. Hãy thay các package:

[[CODE:1]]

Từ 2.x, hãy gỡ thêm `@modelcontextprotocol/core` và `@modelcontextprotocol/node`, `@rekog/mcp-nest-auth` nếu bạn đã dùng authorization server của nó, và `@nestjs/microservices` nếu không có gì khác trong ứng dụng dùng nó. Các type mà bạn đã import từ `@modelcontextprotocol/sdk`, như `CallToolResult`, giờ đến từ `@modelcontextprotocol/server`.

#### Module

Từ 1.x, `McpModule.forRoot()` vẫn giữ nguyên, với ít tùy chọn hơn:

[[CODE:2]]

| `@rekog/mcp-nest` 1.x | `@nestjs/mcp` |
| --- | --- |
| `name`, `version` | Giữ nguyên |
| `transport` | Streamable HTTP được phục vụ trừ khi `path: false`; stdio được phục vụ bởi `McpStdioServer` (xem [Transport](/mcp/transports#over-stdio)) |
| `mcpEndpoint`, `apiPrefix` | `path`, dưới global prefix của ứng dụng |
| `guards` | `decorators: [UseGuards(...)]` |
| `streamableHttp` | Không cần đặt gì: mọi request được phục vụ độc lập, và `http.responseMode` định dạng câu trả lời cho các request 2026-07-28 |
| `forRootAsync()` | `forRootAsync()`, với `path`, `decorators` và `imports` ở cấp ngoài cùng |
| `forFeature()` | Mỗi ứng dụng một MCP server |

Từ 2.x, strategy và code bootstrap của nó biến mất. `McpModule.forRoot()` nhận `name` và `version` của strategy, và endpoint là một route của ứng dụng, được phục vụ bởi `app.listen()`:

[[CODE:3]]

Các class `@McpController()` trở thành provider `@Injectable()` bình thường, được liệt kê trong `providers` của một module thay vì `controllers` của nó, và provider `MCP_STRATEGY` bị bỏ đi. Một stdio server mà `NestFactory.createMicroservice()` đã khởi động giờ được phục vụ từ một application context với `McpStdioServer` thay vào đó, như [Transport](/mcp/transports#over-stdio) trình bày.

#### Tool, resource và prompt

Các decorator giữ nguyên tên và phần lớn tùy chọn của chúng. Các tham số của method thì thay đổi:

[[CODE:4]]

| `@rekog/mcp-nest` | `@nestjs/mcp` |
| --- | --- |
| `parameters` | `inputSchema` trên một tool, `argsSchema` trên một prompt |
| `outputSchema`, `annotations` | Giữ nguyên |
| `(args, context, request)` trong 1.x, `@Payload()` và `@Ctx()` trong 2.x | `(input, ctx)`: request là `ctx.request`, token đã được xác minh là `ctx.authInfo` |
| `context.reportProgress({{ '{' }} progress, total {{ '}' }})` | `ctx.reportProgress(progress, total)` |
| `context.mcpServer.server.elicitInput()` | Trả về `inputRequired()`: xem [hỏi người dùng](/mcp/primitives#the-call-context) |
| `({{ '{' }} uri {{ '}' }})` của một resource | `ctx.uri`. Method của một resource template nhận các biến của nó làm input |
| Các kết quả `{{ '{' }} content {{ '}' }}`, `{{ '{' }} contents {{ '}' }}` và `{{ '{' }} messages {{ '}' }}` | Được trả về nguyên trạng, hoặc trả về chính giá trị và để module dựng kết quả |
| `@Injectable({{ '{' }} scope: Scope.REQUEST {{ '}' }})` | Một singleton provider: đọc những gì thuộc về lời gọi từ `ctx` |
| `McpRegistryService.registerTool()`, `strategy.registerTool()` | Không được hỗ trợ: hãy khai báo tool bằng decorator |

Ví dụ, một resource template:

[[CODE:5]]

Một provider request-scoped sẽ thất bại lúc khởi động với `@nestjs/mcp`: mọi request đều được phục vụ bởi cùng các singleton instance, và những gì khác nhau giữa các lời gọi, gồm request, token và client, nằm trong `ctx`.

#### Guard và lỗi

Guard, interceptor, pipe và filter vẫn tiếp tục hoạt động, với `McpExecutionContext.create(context)` thay cho `context.switchToRpc().getContext<McpContext>()`. Type của context là `'mcp'`, không phải `'rpc'`.

Lỗi của một tool vẫn tới được model dưới dạng kết quả của tool. Một `HttpException` mang message của nó tới client, ở chỗ 2.x cần một `RpcException`; mọi lỗi khác được trả lời bằng `Internal server error`.

[[CODE:6]]

#### Phân quyền

`@nestjs/mcp` là một resource server, như đặc tả MCP yêu cầu ở một server: token đến từ một identity provider, và module xác minh chúng (xem [Phân quyền](/mcp/primitives#authorization)).

| `@rekog/mcp-nest` | `@nestjs/mcp` |
| --- | --- |
| `McpAuthModule`, authorization server có sẵn | Một identity provider (Auth0, Keycloak, Entra ID, WorkOS, hoặc của riêng bạn) phát hành token, và `auth` trỏ tới nó |
| `McpAuthJwtGuard` trong `guards` | `auth.verifier` |
| `@ToolScopes(['orders:write'])` | `scopes: ['orders:write']` trên decorator. Các tool có scope vẫn được liệt kê cho mọi client |
| `@ToolRoles(['admin'])` | Một guard, hoặc một policy `@Can()` với `@nestjs/authorization` |
| `@PublicTool()`, `allowUnauthenticatedAccess` | Không được hỗ trợ: với `auth`, mọi request đều cần token |
| `ctx.getUser()` trong 2.x | `ctx.authInfo`, hoặc `@CurrentUser()` với `@nestjs/authentication` |

#### Những gì không có

- **Transport HTTP+SSE** của bản revision giao thức 2024-11-05 không được phục vụ. Client kết nối qua Streamable HTTP, transport mà các client hiện tại dùng.
- **Session** không được giữ: mọi HTTP request được phục vụ độc lập, đó là điều cho phép server chạy trên nhiều instance. Một client 2025 không thể được hỏi input giữa chừng một lời gọi qua HTTP; lời gọi kết thúc với một lỗi tool.
- **Đăng ký tool lúc runtime**, **nhiều MCP server trong một ứng dụng** và **provider request-scoped** không được hỗ trợ trong phiên bản này.
