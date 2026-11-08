### Testing

Tool, resource và prompt là các method của provider, nên logic của chúng được test như mọi provider khác: gọi method. Những gì MCP thêm vào xung quanh, gồm schema, guard, scope và cấu trúc của kết quả, được test qua một MCP client thật, thứ mà `@nestjs/mcp/testing` kết nối tới ứng dụng trong bộ nhớ.

#### Unit test

Một unit test gọi method với các argument và context mà nó cần:

[[CODE:1]]

Một lời gọi trực tiếp bỏ qua mọi thứ mà module thêm vào: argument không được validate, guard và interceptor không chạy, và giá trị trả về không được biến thành kết quả MCP. Client sẽ test những thứ đó.

#### Client trong bộ nhớ

`connectMcpClient()` kết nối một client của MCP SDK chính thức tới ứng dụng, qua cùng handler với HTTP endpoint: việc kiểm tra token, các schema, và mọi guard, interceptor, pipe và filter. Nó không khởi động HTTP server nào. Client đến từ `@modelcontextprotocol/client`, một dev dependency:

[[CODE:2]]

API đơn hàng yêu cầu token, nên các test thay verifier của nó bằng một verifier biết vài test token:

[[CODE:3]]

Giống như một token thật, một test token cần `expiresAt` trong tương lai và `resource` của server. Các test override class verifier, và kết nối với một token:

[[CODE:4]]

Client chính là `Client` của SDK: `listTools()`, `callTool()`, `readResource()`, `getPrompt()` và các method còn lại là những gì một assistant gọi.

#### Kết quả và lỗi

Những gì sai trong một tool là một kết quả mà model đọc, không phải một exception trong test. `isError` và đoạn text cho biết model đã được báo gì:

[[CODE:5]]

Resource và prompt thì trả lời bằng lỗi JSON-RPC, thứ mà client sẽ throw:

[[CODE:6]]

#### Token và scope

Hãy kết nối một client cho mỗi token mà một test cần. Một lời gọi thiếu các scope mà tool của nó khai báo sẽ thất bại trước khi method chạy, với lỗi báo cho một client thật biết cần yêu cầu người dùng cấp thêm quyền. Một client không có token hoàn toàn không thể kết nối:

[[CODE:7]]

#### Header và bản revision giao thức

`headers` gửi các request header kèm mọi request, thứ mà guard đọc từ `ctx.request.headers`, ở dạng chữ thường. `era: 'legacy'` kết nối như một client của các bản revision giao thức 2025, để kiểm tra rằng server hoạt động với cả hai:

[[CODE:8]]

> info **Hint** Client trong bộ nhớ bắt đầu ở chỗ route của endpoint kết thúc: middleware, và các guard được truyền trong `decorators` của module, không chạy, và `ctx.request` là một object thuần `{{ '{' }} method, url, headers {{ '}' }}`. Hãy test những gì xảy ra trên route qua HTTP.

#### Mọi primitive cùng lúc

`McpRegistry` chứa những gì module đã tìm thấy lúc khởi động. Một test có thể buộc mọi tool tuân theo các quy tắc của riêng bạn, chẳng hạn một mô tả mà model có thể dùng được:

[[CODE:9]]

Registry được điền khi ứng dụng khởi tạo, việc mà `connectMcpClient()` làm; nếu không dùng nó, hãy gọi `moduleRef.init()` trước.

#### Qua HTTP

Bản thân route, gồm global prefix, middleware, CORS và việc kiểm tra `Origin`, được test qua một socket. Khởi động ứng dụng trên một port trống, và gửi request tới nó:

[[CODE:10]]

#### Entry point stdio

Để test `stdio.ts` theo cách một client khởi chạy nó, hãy build ứng dụng, và khởi động nó bằng stdio transport của SDK:

[[CODE:11]]

Đóng client sẽ đóng stdin của process, và ứng dụng shutdown, giống như khi assistant thoát.
