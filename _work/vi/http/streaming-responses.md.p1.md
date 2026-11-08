### Stream response

Một route handler có thể trả về một `Response` chuẩn web, một `ReadableStream`, hoặc một async iterable như async generator. Nest gửi nó đi ngay khi dữ liệu được tạo ra, có backpressure, và dừng nó khi client rời đi. Nó hoạt động giống nhau trên Express adapter, Fastify adapter và Node adapter.

Hãy dùng nó cho những câu trả lời mất thời gian để tạo ra hoặc quá lớn để giữ trong bộ nhớ: các token của một LLM, một request được proxy tới API khác, một bản export lớn.

> info **Hint** Tính năng này cần `@nestjs/core` 12.4.0 trở lên. Trên các phiên bản cũ hơn, hầu hết các giá trị này được trả lời bằng một object JSON rỗng và status 200.

#### Trả về một stream

Cách ngắn nhất để stream là một async generator. Mỗi giá trị nó yield ra được gửi đi ngay khi client nhận được:

[[CODE:1]]

Nếu bạn đã có sẵn một `Response`, hãy trả về nó. `toTextStreamResponse()` của AI SDK trả về một response như vậy, `fetch()` cũng resolve ra một response như vậy, và một promise hay một `Observable` của nó cũng dùng được. Để dừng lời gọi model khi client rời đi, xem [Client ngắt kết nối](/http/streaming-responses#client-disconnection):

[[CODE:2]]

Một `ReadableStream` cho bạn nhiều quyền kiểm soát nhất, vì nó biết ngay lập tức khi client đã rời đi (xem [Client ngắt kết nối](/http/streaming-responses#client-disconnection)):

[[CODE:3]]

> info **Hint** `Response` và `ReadableStream` là các global của Node.js, nên không cần import gì cả.

Bất kỳ object nào khác có method `Symbol.asyncIterator` cũng được tính, trong đó có `Readable` của Node.js. Mảng, `Set` và các sync iterable khác vẫn được serialize thành JSON. Một thenable cũng có method đó, như một query của Mongoose, vẫn được await như bình thường.

#### Những gì một stream có thể yield

Mỗi chunk được gửi theo type của nó:

| Chunk                                       | Được gửi dưới dạng                           | `Content-Type` mặc định     |
| ------------------------------------------- | -------------------------------------------- | --------------------------- |
| Chuỗi                                       | Text UTF-8                                   | `text/plain; charset=utf-8` |
| `Uint8Array`, `Buffer`, dữ liệu binary khác | Nguyên các byte                              | `application/octet-stream`  |
| Mọi thứ khác                                | Một dòng JSON ([NDJSON](https://ndjson.org)) | `application/x-ndjson`      |

Chunk đầu tiên quyết định `Content-Type` mặc định. Hãy đặt giá trị của riêng bạn bằng `@Header()`, giá trị này được ưu tiên:

[[CODE:4]]

Một chunk `undefined` không gửi gì cả, còn một chunk mà `JSON.stringify()` từ chối, như một `BigInt`, sẽ làm stream thất bại.

#### Status và header

Với generator hoặc `ReadableStream`, `@HttpCode()` và `@Header()` được áp dụng như trên mọi route khác. Điều đó bao gồm status mặc định của `POST`, là 201: hãy thêm `@HttpCode(200)` nếu client của bạn mong đợi 200.

Một `Response` là toàn bộ câu trả lời, nên status và header của nó được ưu tiên hơn những gì đã được đặt trước đó, bởi `@HttpCode()`, `@Header()`, một guard, hay một middleware. Các header mà nó không đặt vẫn được giữ nguyên, như header CORS, và các giá trị `Set-Cookie` của nó được thêm vào những giá trị đã có. Một `Response` không có `Content-Type` được gửi dưới dạng `application/octet-stream`, trừ khi một `@Header()` hoặc middleware đã đặt giá trị khác. Một `Response` luôn có status, là 200 trừ khi bạn đặt giá trị khác, nên `@HttpCode()` không có tác dụng với nó.

[[CODE:5]]

Một `Response` có body là `null`, như một response 204 hoặc thứ mà `Response.redirect()` tạo ra, được gửi đi với status và header mà không có body.

`fetch()` decode body của response mà nó trả về, nhưng vẫn giữ nguyên các header `Content-Encoding` và `Content-Length`, cùng các header mô tả kết nối của nó, như `Keep-Alive`. Nest bỏ các header này khỏi một `Response` đến từ `fetch()`, để bạn có thể trả về nó nguyên vẹn. Một `Response` mà bạn tạo từ nó, như với `new Response(upstream.body, upstream)`, được gửi đi với các header bạn đã đưa cho nó, nên hãy tự bỏ những header đó đi.

#### Lỗi

Header phải chờ chunk đầu tiên, vì không exception filter nào có thể trả lời một khi header đã được gửi đi. Vì vậy một lỗi xảy ra trước chunk đầu tiên giống như mọi lỗi khác trong route handler: nó đi qua các [exception filter](/exception-filters), và client nhận được một response lỗi đúng chuẩn.

[[CODE:6]]

Để gửi header trước khi chunk đầu tiên sẵn sàng, ví dụ để client biết kết nối đã mở, hãy yield một chuỗi rỗng trước. Từ đó trở đi, lỗi không còn đến được các exception filter nữa.

Một khi header đã được gửi, lỗi sẽ được log, và kết nối bị đóng đột ngột thay vì được kết thúc, để một câu trả lời bị cắt ngang không bị nhầm là câu trả lời hoàn chỉnh: `fetch()` reject trong lúc đọc body, và `curl` báo lỗi. Nếu client của bạn cần biết chuyện gì đã sai, hãy đưa thông tin đó vào nội dung bạn stream, và tự bắt lỗi trong generator.

Một body đã được đọc rồi (ví dụ bằng `await response.text()`) hoặc đang bị khóa thì không thể gửi được, nên nó thất bại với lỗi 500 thay vì không gửi gì. Một async generator thì không phân biệt được: một generator đã chạy tới cuối sẽ đơn giản là không gửi gì cả.

#### Client ngắt kết nối

Khi client rời đi, kể cả trước chunk đầu tiên, Nest dừng stream, để một lời gọi LLM có trả phí không tiếp tục chạy cho không ai cả:

- một `ReadableStream`, hoặc body của một `Response`, sẽ bị hủy, việc này gọi ngay `cancel()` của nó;
- một `Readable` của Node.js sẽ bị destroy;
- `return()` của một async generator sẽ được gọi, việc này chạy các khối `finally` của nó.

[[CODE:7]]

> warning **Warning** JavaScript xếp hàng `return()` cho đến lần `yield` tiếp theo của một async generator, nên một generator đang chờ trong một `await` chỉ dừng lại khi `await` đó settle. Nếu một upstream có thể im lặng trong thời gian dài, hãy dùng `ReadableStream`, vì `cancel()` của nó chạy ngay lập tức.

Dừng một stream không phải lúc nào cũng dừng được thứ cung cấp dữ liệu cho nó. Chẳng hạn, hủy `Response` của `toTextStreamResponse()` trong AI SDK vẫn để lời gọi model chạy tới cuối, và tính tiền tới cuối, trừ khi `abortSignal` của nó bị abort. Để dừng lời gọi khi client rời đi, hãy abort nó từ `cancel()`:

[[CODE:8]]

Hãy kiểm tra điều này với mọi `Response` mà một library đưa cho bạn.

#### Client chậm

Chunk tiếp theo chỉ được đọc khi client có thể nhận, nên một client đọc chậm sẽ làm chậm bên tạo dữ liệu thay vì làm đầy bộ nhớ của server. Một async generator đơn giản là dừng ở `yield`, còn `pull()` của một `ReadableStream` sẽ không được gọi.

Một thứ gì đó nằm giữa Nest và client vẫn có thể giữ chunk lại. Middleware [nén response](/http/compression) và các proxy như nginx buffer response: với nginx, hãy đặt header `X-Accel-Buffering: no`.

#### Request HEAD

Một request `HEAD` không đọc stream: một generator thậm chí không khởi động, còn một `ReadableStream` sẽ bị hủy. Status và header được gửi như thường lệ, nhưng vì chunk đầu tiên không bao giờ được đọc, một route dựa vào `Content-Type` mặc định sẽ trả lời `application/octet-stream`. Hãy đặt nó bằng `@Header()` nếu điều đó quan trọng.

#### Interceptor

Một [interceptor](/interceptors) thấy stream như một giá trị duy nhất, giá trị này đến với nó trước khi việc stream bắt đầu. Vì vậy `finalize()` và `timeout()` của nó đã xong trước khi stream kết thúc, và interceptor không thấy các chunk.

Một stream không thể được gửi đi như một phần của thứ khác. Nếu một interceptor bọc hoặc serialize nó, như một interceptor global đặt mọi kết quả dưới key `data`, Nest sẽ gửi nguyên stream của handler, còn các route khác vẫn giữ wrapper của chúng. Một interceptor vẫn có thể:

- chuyển tiếp nó, như với `tap()`;
- thay nó bằng một stream khác, ví dụ một stream đọc stream đầu tiên và thay đổi từng chunk;
- đọc nó và trả về một giá trị của riêng mình, khi đó Nest sẽ gửi giá trị này thay vào đó.

Cả `ClassSerializerInterceptor` lẫn `StandardSchemaSerializerInterceptor` đều không [serialize](/application/serialization) các giá trị này.

#### Handler dùng @Res()

Một handler inject response bằng `@Res()` sẽ tự gửi response, nên Nest bỏ qua những gì nó trả về, và một generator không bao giờ khởi động. Với tùy chọn `passthrough` của `@Res()`, stream được trả về sẽ được gửi như thường lệ.

#### Chọn cách stream

- **Một stream**, như mô tả ở đây, cho bất cứ thứ gì được tạo ra theo thời gian, ở bất kỳ định dạng nào, đọc bằng `fetch()`.
- [**`@Sse()`**](/http/server-sent-events) cho các event gửi tới một `EventSource` từ một `Observable`, kèm event id và khả năng kết nối lại mà chúng cho phép.
- [**`StreamableFile`**](/http/file-upload#streaming-files) cho file, kèm `Content-Disposition` và `Content-Length` của chúng.
