### Testing

Các test cho code gọi model không gọi tới model provider: `FakeModel`, từ `@nestjs/ai/testing`, là một language model trả lời mỗi lời gọi bằng câu trả lời tiếp theo trong danh sách bạn đưa cho nó, và ghi lại mọi lời gọi mà nó nhận được.

Fake model là một `LanguageModel` thật, nên mọi thứ xung quanh nó chạy như trong production: các thiết lập của module, retry, timeout và fallback model, schema, agent function cùng các enhancer của chúng, và streaming. Chỉ có network là bị loại ra.

#### Fake model

Một `FakeModel` nhận các câu trả lời của nó theo thứ tự:

[[CODE:1]]

| Câu trả lời | Model làm gì |
| --- | --- |
| Một chuỗi | Trả lời bằng đoạn text đó |
| `{{ '{' }} text {{ '}' }}` | Tương tự, với các tùy chọn bên dưới |
| `{{ '{' }} toolCalls {{ '}' }}` | Gọi các tool, mỗi tool với `name`, `input` (mặc định `{{ '{' }}{{ '}' }}`) và `id` (mặc định `call-1`, `call-2`, ...) |
| `{{ '{' }} object {{ '}' }}` | Trả lời bằng object dưới dạng JSON, thứ mà `generateObject()` đọc |
| Một `Error` | Thất bại với lỗi đó, như một request tới provider |
| Một hàm nhận lời gọi | Trả lời bằng những gì nó trả về, bất kỳ loại nào ở trên, hoặc một promise của nó |

Một answer object cũng nhận:

| Tùy chọn | Làm gì |
| --- | --- |
| `usage` | Số token mà câu trả lời báo cáo: `inputTokens` và `outputTokens` (mặc định mỗi loại 10), `cachedInputTokens`, `reasoningTokens` |
| `finishReason` | Mặc định `'tool-calls'` khi có lời gọi tool, nếu không thì `'stop'` |
| `delay` | Số mili giây trước khi nó trả lời, hoặc trước khi một stream mở. Việc abort lời gọi, và timeout của nó, sẽ cắt ngang khoảng này |
| `chunkDelay` | Số mili giây giữa các chunk của một stream, stream này gửi đoạn text theo từng chunk cỡ một từ |
| `streamError` | Một lỗi mà stream thất bại với nó sau đoạn text, giống như một kết nối bị đứt |

Nếu được đưa một hàm thay vì một danh sách, `new FakeModel((call) => ...)` trả lời mọi lời gọi bằng hàm đó. `reply(...answers)` thêm câu trả lời vào sau những câu chưa dùng, và `fakeModel(...answers)` là `new FakeModel(answers)`. Một lời gọi mà nó không còn câu trả lời nào sẽ thất bại: `FakeModel: no answer left for call 4. Give it more answers.`

`providerError(status, {{ '{' }} message, retryAfter {{ '}' }})` là lỗi mà một provider `@ai-sdk/*` throw cho một lỗi HTTP: một `APICallError`, có thể retry với 408, 409, 429 và 5xx, kèm header `retry-after` khi đặt `retryAfter` (tính bằng giây).

`calls` liệt kê những gì model đã nhận, và `lastCall` là lời gọi cuối cùng:

| Thuộc tính | Là gì |
| --- | --- |
| `instructions` | System prompt |
| `lastUserMessage` | Đoạn text của user message cuối cùng |
| `toolResults` | Những gì các tool của step trước đã trả về, theo cách model đọc chúng: `toolName`, `toolCallId` và `output`, là message của lỗi với một tool đã thất bại |
| `tools` | Tên các tool mà model được cung cấp |
| `stream` | Lời gọi có được stream không |
| `options` | Mọi thứ mà model được gửi, dưới dạng các call option ở cấp provider của AI SDK: `prompt`, `tools`, `responseFormat`, `maxOutputTokens`, `headers` và các tùy chọn còn lại |

#### Test một service

Đăng ký `AiModule` trong một testing module, với các fake model dưới những tên mà service dùng:

[[CODE:2]]

Một câu trả lời không khớp với schema sẽ test cách service xử lý `AiOutputError`: hãy đưa cho model `'Sure! Here it is.'`, hoặc một object thiếu một field.

#### Retry, timeout và fallback

`providerError()` và `delay` test điều gì xảy ra khi một provider thất bại, hoặc mất quá lâu. Hãy để các lần retry của module không có backoff, và cho các lần thử một timeout ngắn, để test không phải chờ:

[[CODE:3]]

Model nhanh thất bại hai lần, và model mặc định mất lâu hơn 50 mili giây mà mỗi lần thử có, hai lần: tổng cộng bốn lần thử, và lỗi của lần cuối cùng là `cause`.

#### Override model trong end-to-end test

`overrideModels()` đặt các fake model vào chỗ các model của ứng dụng, theo tên, và giữ phần còn lại của định nghĩa của chúng: pricing, fallback model, timeout và retry. Một tên mà module không cấu hình sẽ thất bại khi testing module compile. Các model mà `@InjectModel()` inject cũng được thay thế:

[[CODE:4]]

Các agent function chạy thật, với schema, guard và filter của chúng: lỗi của một function tới model dưới dạng kết quả của tool, thứ mà test đọc trong `toolResults` của lời gọi tiếp theo:

[[CODE:5]]

#### Test agent function

`callTool()` chạy một agent function giống như lời gọi tool của một model, không cần model: các argument được validate theo schema của nó, scope của nó được kiểm tra, rồi đến guard, interceptor, pipe và filter, và method. Nó resolve với những gì model sẽ đọc, và reject với `AiToolError` mà model sẽ đọc về một lỗi:

[[CODE:6]]

`caller` chính là `caller` của một lời gọi: một `request`, như của route, hoặc một `user` và `scopes`. `callTool()` khởi tạo testing module nếu nó chưa được khởi tạo. Một method đồng thời phục vụ MCP client được test như một MCP tool bằng [client trong bộ nhớ](/mcp/testing) của `@nestjs/mcp/testing`, với các lời gọi có context type `'mcp'`.

Một unit test gọi trực tiếp method, với context mà nó cần. Một lời gọi trực tiếp bỏ qua mọi thứ xung quanh method: schema, scope và các enhancer. Việc hoàn tiền của một [durable run](/ai/agents#durable-agent-runs) truyền `idempotencyKey` của lời gọi tiếp cho payment provider:

[[CODE:7]]

#### Test stream

Fake model stream đoạn text của nó theo từng chunk cỡ một từ, nên một stream được đọc giống như từ một provider. Trong một end-to-end test, response của một chat route là một body server-sent event, với các event là các chunk của UI message stream:

[[CODE:8]]

`streamError` test một stream bị đứt sau chunk đầu tiên, `{{ '{' }} text: 'Your order', streamError: providerError(500) {{ '}' }}`: khi đó body kết thúc bằng một chunk `error` ghi `An error occurred.`. Bên ngoài HTTP, hãy đọc trực tiếp stream của `streamText()`, dưới dạng `textStream`, hoặc promise `text` của nó.

#### Test durable run

Một durable run được test với workflow engine chạy ngay trong test, trên store trong bộ nhớ của nó, với một `ManualWorkflowClock` và worker bị tắt: `WorkflowWorker.drain()` chạy các instance tới hạn, cho tới khi không còn instance nào có thể chạy, nên test quyết định khi nào run tiếp tục:

[[CODE:9]]

Các lời gọi model và lời gọi tool mà run đã thực hiện trước khi được phê duyệt sẽ được đọc lại từ journal khi nó tiếp tục: tổng cộng fake model được gọi ba lần. Để test một lần restart, hãy boot một ứng dụng thứ hai trên cùng store, như [Test khả năng phục hồi sau crash](/reliability/workflows#test-crash-recovery) trình bày cho mọi workflow.

#### Test embedding

`FakeEmbeddingModel` là fake model cho [các lời gọi embedding](/ai/embeddings): một `EmbeddingModel` thật, trả lời mỗi request tới provider bằng câu trả lời tiếp theo trong danh sách bạn đưa cho nó, và ghi lại request đó. Nó không tự bịa ra vector nào: một câu trả lời có mỗi giá trị của request một vector.

[[CODE:10]]

Tham số thứ hai cho biết AI SDK chia các giá trị thế nào, giống như model của một provider: ở đây mỗi giá trị là một request riêng, và chúng được gửi từng cái một, để test biết thứ tự của chúng. Nó cũng nhận `provider` và `modelId`. Không có nó, model không có giới hạn, và `embedMany()` chỉ thực hiện một request.

| Câu trả lời | Model làm gì |
| --- | --- |
| `{{ '{' }} embeddings {{ '}' }}` | Trả lời bằng các vector, mỗi giá trị của request một vector |
| Một `Error` | Thất bại với lỗi đó, như một request tới provider |
| Một hàm nhận lời gọi | Trả lời bằng những gì nó trả về, bất kỳ loại nào ở trên, hoặc một promise của nó |

Một answer object cũng nhận:

| Tùy chọn | Làm gì |
| --- | --- |
| `usage` | Số token mà câu trả lời báo cáo: `{{ '{' }} tokens {{ '}' }}`, mặc định 10 cho mỗi giá trị |
| `delay` | Số mili giây trước khi nó trả lời. Việc abort lời gọi, và timeout của nó, sẽ cắt ngang khoảng này |
| `warnings`, `providerMetadata`, `response` | Những gì provider thêm vào các vector của nó |

Nếu được đưa một hàm thay vì một danh sách, `new FakeEmbeddingModel((call) => ...)` trả lời mọi request bằng hàm đó, phù hợp với một test không quan tâm các giá trị được chia thế nào. `reply(...answers)` thêm câu trả lời vào sau những câu chưa dùng, và `fakeEmbeddingModel(...answers)` là `new FakeEmbeddingModel(answers)`. Một request mà nó không còn câu trả lời nào sẽ thất bại: `FakeEmbeddingModel: no answer left for call 3. Give it more answers.`

`calls` liệt kê những gì model đã nhận, mỗi request kèm `values` và `options` của nó, tức các call option ở cấp provider của AI SDK như `abortSignal`, `headers` và `providerOptions`, và `lastCall` là request cuối cùng.

`overrideEmbeddingModels()` làm với embedding model những gì `overrideModels()` làm với language model: nó đặt các fake model vào chỗ các model của ứng dụng, theo tên, và giữ phần còn lại của định nghĩa của chúng, gồm thiết lập và pricing. Một tên mà module không cấu hình sẽ thất bại khi testing module compile. Các model mà `@InjectEmbeddingModel()` inject cũng được thay thế:

[[CODE:11]]

Để thay cả language model trong cùng test, hãy truyền những gì `overrideEmbeddingModels()` trả về cho `overrideModels()`.
