### Server-Sent Events

Server-Sent Events (SSE) là một công nghệ server push cho phép client tự động nhận cập nhật từ server qua một kết nối HTTP. Mỗi thông báo được gửi dưới dạng một khối text kết thúc bằng hai dấu xuống dòng (xem [Server-sent events trên MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) để tìm hiểu thêm).

#### Cách dùng

Để bật Server-Sent Events trên một route (route đăng ký bên trong một **class controller**), hãy đánh dấu route handler bằng decorator `@Sse()`.

[[CODE:1]]

> info **Hint** Decorator `@Sse()` và interface `MessageEvent` được import từ package `@nestjs/common`, còn `Observable`, `interval` và `map` được import từ package `rxjs`.

> warning **Warning** Các route Server-Sent Events phải trả về một `Observable` stream (hoặc một `Promise` resolve ra nó, như ví dụ [bên dưới](/http/server-sent-events#client-disconnection)). Để stream từ một async generator, một `ReadableStream`, hoặc một `Response` của web, hãy trả về nó từ một route thông thường: xem [Stream response](/http/streaming-responses).

Trong ví dụ trên, ta định nghĩa một route tên `sse` để lan truyền các cập nhật thời gian thực. Client có thể lắng nghe các event này bằng [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource).

Method `sse()` trả về một `Observable` phát ra nhiều object `MessageEvent` (trong ví dụ này, một `MessageEvent` mới mỗi giây). Mỗi object `MessageEvent` nên tuân theo interface sau để khớp với đặc tả:

[[CODE:2]]

`data` dạng object được serialize thành JSON. Thuộc tính `type` được gửi dưới dạng trường `event` của SSE, còn `comment` được gửi dưới dạng một dòng comment, thứ mà client `EventSource` bỏ qua (hữu ích, chẳng hạn, để làm keep-alive). Nếu bạn không đặt `id`, Nest gán cho mỗi event một ID tăng dần.

Khi đã có những thứ trên, bạn có thể tạo một instance của class `EventSource` trong ứng dụng phía client, truyền route `/sse` (khớp với path truyền vào decorator `@Sse()` ở trên) làm tham số constructor.

Một instance `EventSource` mở một kết nối lâu dài tới HTTP server, server này gửi event theo định dạng `text/event-stream`. Kết nối vẫn mở cho đến khi nó được đóng bằng cách gọi `EventSource.close()`.

Khi kết nối đã mở, các message gửi đến từ server được chuyển tới code của bạn dưới dạng event. Nếu message gửi đến có trường `event`, event được kích hoạt sẽ có tên trùng với giá trị của trường đó. Nếu không có trường `event`, một event `message` chung sẽ được kích hoạt (xem [tài liệu EventSource trên MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)).

[[CODE:3]]

#### Status code và header

Một route `@Sse()` gửi các header được đặt bằng decorator `@Header()`. Kể từ NestJS v12.1.3, nó cũng gửi status code mà handler hoặc một interceptor đặt trên response trước khi stream bắt đầu, và, trên Fastify, cả các header mà chúng đặt (Express vốn đã gửi những header đó). Để đặt chúng trong handler, hãy inject response bằng decorator `@Res()` với tùy chọn `passthrough` được bật:

[[CODE:4]]

> info **Hint** `Res` được import từ package `@nestjs/common`, còn type `Response` từ package `express`. Trên Fastify, hãy dùng type `FastifyReply` từ package `fastify`.

#### Client ngắt kết nối

Khi một client đóng kết nối SSE (ví dụ bằng `eventSource.close()`), Nest tự động unsubscribe khỏi `Observable` được trả về. Việc này dừng event stream và dọn dẹp mọi resource liên quan, kể cả bộ hẹn giờ interval trong ví dụ trên.

Để chạy logic dọn dẹp tùy chỉnh khi một client ngắt kết nối, hãy dùng operator `finalize`:

[[CODE:5]]

> info **Hint** Operator `finalize` (import từ `rxjs`) thực thi callback của nó mỗi khi `Observable` kết thúc: do hoàn tất, do lỗi, hoặc do bị unsubscribe (bao gồm cả khi client ngắt kết nối). Điều này khiến nó là nơi đúng đắn để giải phóng các resource bên ngoài gắn với stream, như database cursor hay file handle.

Một handler `@Sse()` có thể là bất đồng bộ, trả về một `Promise<Observable>` thay vì trực tiếp một `Observable`. Điều này phổ biến khi stream cần một bước thiết lập tốn kém trước khi có thể tạo ra event đầu tiên, như mở một database cursor, lấy một model session, hoặc xin quyền từ một service phía sau.

[[CODE:6]]

Điều này để lại một khoảng trống. Nếu client ngắt kết nối **trong khi promise vẫn đang resolve**, Nest không bao giờ subscribe vào `Observable` được trả về, vì nó không khởi động một producer khi consumer của nó đã rời đi. Đó là hành vi đúng cho stream, nhưng nó có nghĩa là logic dọn dẹp của `Observable` không bao giờ chạy, và bất cứ thứ gì được cấp phát trong bước thiết lập (`session` ở trên) sẽ bị rò rỉ.

Để lấp khoảng trống đó, hãy inject `AbortSignal` của request bằng decorator `@SseSignal()`:

[[CODE:7]]

#### Vòng đời của signal

Signal đại diện cho vòng đời của **response SSE**, không chỉ của kết nối. Nó bị abort một khi stream kết thúc vì bất kỳ lý do nào:

- client đã ngắt kết nối;
- `Observable` đã hoàn tất;
- `Observable` đã gặp lỗi.

Điều này khiến signal trở thành một hook dọn dẹp duy nhất cho toàn bộ request. Thay vì lặp lại logic dọn dẹp ở cả một listener `abort` lẫn hàm dọn dẹp của chính `Observable`, bạn có thể gắn resource vào signal một lần và để chúng được giải phóng ở mọi lối ra:

[[CODE:8]]

Vì signal cũng bị abort khi hoàn tất bình thường, `signal.aborted` chỉ có ý nghĩa như một phép kiểm tra "client có rời đi không?" **trong lúc thiết lập**, trước khi `Observable` được trả về. Tại thời điểm đó, stream chưa thể hoàn tất, nên một signal đã bị abort chắc chắn có nghĩa là client đã ngắt kết nối.

> warning **Notice** Logic dọn dẹp gắn với event `abort` có thể chạy song song với hàm dọn dẹp của `Observable`, nên hãy làm cho nó idempotent.

Bên trong một producer, bạn cũng có thể dùng signal để kết thúc stream khi client rời đi:

[[CODE:9]]

> info **Hint** `@SseSignal()` chỉ có giá trị trên các route `@Sse()`; trên mọi route handler khác, nó resolve ra `undefined`. Nó hoạt động giống nhau trên nền tảng Express và Fastify.

#### Ví dụ

Một ví dụ chạy được có sẵn trong [sample 28-sse](https://github.com/nestjs/nest/tree/master/sample/28-sse).
