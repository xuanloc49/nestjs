### Tool

Một agent function là một method của một provider mà model có thể gọi, với các argument do nó điền, để tra cứu hoặc thay đổi thứ gì đó: model đọc những gì method trả về, rồi gọi thêm function hoặc trả lời. Bạn viết một agent function; model được cung cấp nó dưới dạng một tool.

Assistant của cửa hàng trả lời các câu hỏi về đơn hàng, nên model của nó phải tra cứu được đơn hàng. Trong `@nestjs/ai`, method làm việc đó được gắn `@AgentFunction()`, và nó chạy qua các guard, interceptor, pipe và exception filter của class và method của nó, với tư cách người dùng mà model đang hành động thay. Nó không cần gì ngoài `@nestjs/ai`.

#### Định nghĩa một agent function

`inputSchema` mô tả các argument của function: model được gửi JSON Schema của nó, và mọi lời gọi được validate theo nó trước khi method chạy. Model chọn function theo tên và mô tả của nó, và điền argument dựa trên các đoạn text `.describe()`:

[[CODE:1]]

`@AgentFunction()` nhận bốn tùy chọn, tất cả đều không bắt buộc:

- **`name`**: tên mà các lời gọi dùng để liệt kê function, và tên mà model dùng để gọi nó. Mặc định là tên của method, và phải có từ 1 tới 64 ký tự trong tập `A-Z a-z 0-9 _ -`, đúng những gì model provider chấp nhận làm tên tool.
- **`description`**: function làm gì, dành cho model.
- **`inputSchema`**: các argument của nó, dưới dạng một object schema. Không có nó, function không nhận argument nào.
- **`scopes`**: các scope mà bên gọi phải có: xem [Agent hành động thay cho ai](/ai/tools#who-the-agent-acts-for).

Đăng ký class làm provider, như mọi provider khác:

[[CODE:2]]

`AiModule` tìm các agent function của mọi module trong ứng dụng; tùy chọn `include` riêng của nó giới hạn việc tìm kiếm trong các module mà nó liệt kê.

#### Cho một lời gọi các tool của nó

Một lời gọi liệt kê, trong `tools`, các agent function mà model của nó được dùng, theo tên hoặc theo class provider (mọi agent function của class đó), và cho biết nó hành động thay cho ai bằng `caller`:

[[CODE:3]]

Model được cung cấp các function mà lời gọi liệt kê, dưới dạng tool, và không có function nào khác. Khi nó gọi một function, các argument được validate theo schema của function, method chạy, và những gì nó trả về được gửi lại cho model, model sẽ gọi thêm function hoặc trả lời. Mỗi câu trả lời của model là một lời gọi model, và `maxSteps`, mặc định 10, giới hạn số lời gọi model mà một lời gọi thực hiện: xem [Vòng lặp agent](/ai/agents#the-agent-loop). Các argument bị schema từ chối không bao giờ tới được method, cũng không tới được guard của nó: model được báo điều gì sai, và có thể thử lại.

Các sai sót sẽ thất bại sớm:

- Một lời gọi liệt kê một agent function không tồn tại, hoặc một class không có agent function nào, sẽ bị từ chối trước khi bất cứ thứ gì được gửi: `There is no agent function named "find-orders". Agent functions: find-order, change-address.`
- Một tên mà model provider từ chối sẽ thất bại lúc khởi động, nêu tên method. Hai agent function cùng tên cũng vậy, và một agent function trên một provider request-scoped cũng vậy: hãy truyền những gì một lời gọi cần qua `caller` thay vào đó.
- Một schema không phải Standard Schema có JSON Schema, hoặc không mô tả một object, cũng vậy.

Model đọc những gì method trả về dưới dạng JSON: một `Date` thành chuỗi ISO của nó, và `undefined` thành `null`. Một method đồng thời phục vụ MCP client có thể trả về một `CallToolResult` của MCP: model đọc `structuredContent` của nó, hoặc nếu không có thì các text block của nó, được nối lại. Ảnh, audio và các block khác không tới được model, và một cảnh báo trong log sẽ báo điều đó. Một kết quả có `isError: true` là một lỗi tool, kèm đoạn text của nó.

#### Context của lời gọi

Một agent function được gọi với các argument của nó và một `AgentFunctionContext`, từ `@nestjs/ai`:

| Thuộc tính | Là gì |
| --- | --- |
| `name` | Tên của agent function |
| `request` | HTTP request mà lời gọi chạy trong đó, `caller.request`, với các header của nó và `user` mà phần xác thực của bạn đã đặt lên nó |
| `user`, `scopes` | `caller.user` và `caller.scopes`: lời gọi hành động thay cho ai ở những nơi không có request, như trong một queue job |
| `toolCallId` | Id của model cho lần gọi tool này, để gắn log của function với cuộc hội thoại |
| `idempotencyKey` | Trong một [durable run](/ai/agents#durable-agent-runs), giống nhau cho mọi lần thử của lời gọi này; `undefined` ở những nơi khác |
| `messages` | Cuộc hội thoại mà model đã đọc khi nó gọi function, không có system prompt |
| `signal` | Một `AbortSignal`, bị abort khi lời gọi bị abort: hãy truyền nó tiếp cho `fetch()` và database của bạn |
| `reportProgress(progress, total?, message?)` | Trong một [câu trả lời được stream](/ai/agents#streaming-to-the-browser), gửi tiến độ của lời gọi tới trình duyệt; ở những nơi khác, không làm gì cả |

`change-address` cho phép assistant đổi địa chỉ giao hàng của một đơn hàng. Nó truyền `signal` của lời gọi tiếp cho database, và một guard kiểm tra rằng đơn hàng là của khách hàng đó:

[[CODE:4]]

#### Agent hành động thay cho ai

`caller` cho biết một lời gọi hành động thay cho ai, và các agent function, guard của chúng cùng các package xác thực đọc nó từ context:

- **`request`**: trong một route, HTTP request của Express, Fastify hoặc Node adapter, như `@Req()` inject nó. Các function thấy nó dưới dạng `ctx.request`, với `user` mà phần xác thực của bạn đã đặt lên nó, giống như guard của một route.
- **`user`** và **`scopes`**: ở những nơi không có request, như trong một queue job hoặc một scheduled task, lời gọi hành động thay cho ai và họ được làm gì. Chúng là `ctx.user` và `ctx.scopes`.

Một agent function có `@AgentFunction()` khai báo `scopes` chỉ chạy cho một bên gọi có các scope đó trong `caller.scopes`: nếu không, lời gọi bị từ chối trước khi bất kỳ guard nào chạy, và model đọc được `Forbidden: this tool needs the scope(s) orders:refund`. Một job hàng đêm xem xét các yêu cầu hoàn tiền chưa ai trả lời, với tư cách refund bot của cửa hàng:

[[CODE:5]]

Không có gì mà bên gọi thiếu được tự bịa ra: một lời gọi không có `caller` chạy các agent function của nó mà không có request, không có user và không có scope.

#### Guard, interceptor, pipe và filter

Mọi lời gọi agent function đều chạy qua các enhancer của Nest, được gắn trên class, trên method hoặc ở phạm vi global, như với một route. Type của execution context là `'ai'`, và `AiExecutionContext` đọc lời gọi. Một khách hàng chỉ được thay đổi đơn hàng của chính mình:

[[CODE:6]]

`AiExecutionContext.create(context)` có `getType()`, `getInput()` (các argument, cũng là `switchToRpc().getData()`), `getContext()` (`AgentFunctionContext`), `getName()` và `getRequest()`. Một lời gọi agent function đi qua các bước sau, theo thứ tự:

1. Các argument được validate theo schema của function.
2. `scopes` của function được kiểm tra so với của bên gọi.
3. Các guard chạy, guard global trước, rồi đến interceptor và pipe, như quanh một route handler.
4. Method chạy, với các argument và context.

Pipe thấy các argument dưới dạng `body` của lời gọi, nên một `ValidationPipe` sẽ validate một class DTO mà bạn dùng làm type cho chúng, sau khi schema của function đã validate, và chúng thấy context dưới dạng một tham số `custom`, thứ mà `ValidationPipe` bỏ qua. Các custom parameter decorator được tạo bằng `createParamDecorator()` hoạt động sau các argument và context: `changeAddress(input, ctx, @CurrentUser() user)`.

Interceptor thấy giá trị trả về của method trước model. Interceptor này log mỗi lời gọi, kèm id của lần gọi tool của model:

[[CODE:7]]

Những gì một agent function throw sẽ tới model dưới dạng một lỗi mà nó có thể khắc phục, và báo cho người dùng: lần từ chối của một guard thành `Forbidden resource`, message của một `HttpException` (một `BadRequestException('The address has no postcode')`), và `Internal server error` cho mọi lỗi khác, loại lỗi mà exception handler của Nest sẽ log lại và message của nó không bao giờ tới được model. Một exception filter có thể trả lời thay: những gì nó trả về là kết quả của function.

> warning **Warning** Guard, interceptor và filter global (`APP_GUARD`, `app.useGlobalGuards()`) cũng chạy trên các lời gọi agent function, như trên các lời gọi MCP. Một enhancer viết cho HTTP route có đọc `context.switchToHttp()` nên kiểm tra `context.getType() === 'http'` trước.

#### Phục vụ cả MCP client

API đơn hàng đã có một [MCP server](/mcp/overview), với các client là assistant của bộ phận hỗ trợ, cũng gọi `find-order`. Một method phục vụ cả hai bên dùng: nó mang `@Tool()` từ [`@nestjs/mcp`](/mcp/primitives#tools), cho MCP client, và `@AgentFunction()`, cho các agent của ứng dụng, mỗi decorator có tùy chọn riêng. Không decorator nào đọc decorator kia: một method chỉ có `@Tool()` không phải agent function, và một method chỉ có `@AgentFunction()` không phải MCP tool. Một hằng số schema giúp không phải viết schema hai lần:

[[CODE:8]]

Mỗi bên dùng tìm decorator của riêng mình: `McpModule` phục vụ các method `@Tool()` của các module mà `include` của nó liệt kê, còn `AiModule` tìm các method `@AgentFunction()`:

[[CODE:9]]

MCP client nhận được `find-order`, còn assistant được gọi `find-order` và `change-address`, function không có `@Tool()`.

Hai loại lời gọi có context type riêng: `'mcp'` cho lời gọi của MCP client, được `McpExecutionContext` đọc, và `'ai'` cho lời gọi của agent, được `AiExecutionContext` đọc. Guard, interceptor và filter của một method phục vụ cả hai sẽ thấy cả hai loại, và phân biệt chúng bằng `context.getType()`. `find-order` chỉ cho khách hàng thấy đơn hàng của chính họ qua assistant, còn MCP client của bộ phận hỗ trợ thì thấy mọi đơn hàng:

[[CODE:10]]

Tham số thứ hai của method là một `McpContext` với lời gọi của MCP client, và một `AgentFunctionContext` với lời gọi của agent. Các custom parameter decorator, được tạo bằng `createParamDecorator()`, cũng chạy cho cả hai loại lời gọi, và `ExecutionContext` mà chúng nhận có type của lời gọi mà chúng đang chạy cho.

#### Với `@nestjs/authentication` và `@nestjs/authorization`

[`@nestjs/authentication`](/security/authentication) và [`@nestjs/authorization`](/security/authorization) đọc các lời gọi agent function giống như đọc lời gọi của MCP client: từ các argument của chúng, cùng request mà lời gọi chạy trong đó. Trong một route, global authentication guard xác thực mỗi lời gọi từ request mà nó chạy trong đó (một lần: kết quả của route được tái sử dụng), `@CurrentUser()` và `AuthenticationContext` hoạt động trong agent function, và các policy `@Can()` quyết định từng lời gọi. Một agent function không khai báo `@Can()` nào sẽ bị từ chối, giống như một route, và model đọc được `Forbidden`:

[[CODE:11]]

Trong một job, không có request. `@Can()` tìm `user` của bên gọi trên context, và authentication guard coi lời gọi là ẩn danh, như qua stdio, nên hãy đánh dấu các provider chứa agent function mà job gọi là `@Public()`:

[[CODE:12]]

Một lần từ chối là `UnauthorizedException` hoặc `ForbiddenException` của Nest, như trên một route, và model đọc nó như lỗi của tool: `Unauthorized`, hoặc `Forbidden`.

> info **Hint** Việc này cần `@nestjs/authentication` 0.1.4 và `@nestjs/authorization` 0.1.2 trở lên, những phiên bản đầu tiên biết tới context type `'ai'`.

#### Tool trong các lời gọi AI SDK của riêng bạn

`AiTools` biến agent function thành tool của AI SDK: `select()` nhận cùng danh sách mà `tools` của một lời gọi nhận, và `caller` mà các lời gọi của chúng chạy với tư cách đó, dành cho code tự gọi AI SDK. Các function giữ nguyên schema, scope và enhancer của chúng:

[[CODE:13]]

`stopWhen` và `stepCountIs()` là của AI SDK: ở đây nó chạy vòng lặp riêng của mình, như với mọi lời gọi khác của nó.
