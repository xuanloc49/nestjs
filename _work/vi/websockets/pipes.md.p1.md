### Pipe

Không có khác biệt căn bản nào giữa [pipe thông thường](/pipes) và pipe của WebSocket. Khác biệt duy nhất là thay vì throw `HttpException`, bạn nên throw `WsException`. Chỉ có `WsException` mới tới được client với message riêng của nó. Mọi exception khác, kể cả `BadRequestException` mà các validation pipe có sẵn throw theo mặc định, đều được báo tới client dưới dạng `'Internal server error'`.

> info **Hint** Class `WsException` được cung cấp từ package `@nestjs/websockets`.

#### Gắn pipe

Ví dụ sau dùng một pipe cấp method được khởi tạo thủ công. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng pipe cấp gateway (tức là gắn `@UsePipes()` cho class gateway). Global pipe được đăng ký bằng `app.useGlobalPipes()` hoặc token `APP_PIPE` cũng áp dụng cho gateway.

[[CODE:1]]

Pipe cấp method, cấp gateway và cấp global chạy cho mọi tham số của message handler. Để chỉ biến đổi hoặc validate payload của message, hãy gắn pipe ở cấp tham số thay vào đó, ví dụ `@MessageBody(new ParseIntPipe())` hoặc `@MessageBody('id', ParseIntPipe)`.

#### Validation dựa trên schema

Giống như các HTTP parameter decorator, `@MessageBody()` nhận một options object có thuộc tính `schema`. Schema có thể đến từ bất kỳ library nào tương thích [Standard Schema](https://standardschema.dev/), như Zod, Valibot hay ArkType. `StandardSchemaValidationPipe` có sẵn sẽ validate payload theo schema đó, và để các tham số không có schema đi qua mà không thay đổi. Xem [Validation dựa trên schema](/application/validation#schema-based-validation) để biết chi tiết.

[[CODE:2]]

Để lấy ra một thuộc tính và validate nó, hãy truyền property key trước: `@MessageBody('id', {{ '{' }} schema: z.number() {{ '}' }})`.
