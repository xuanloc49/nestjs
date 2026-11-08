### Model

Mọi lời gọi model đều chạy dưới một timeout, retry và các fallback model, được dựng từ thiết lập của lời gọi, của model và của module, và báo cáo số token đã dùng cùng chi phí của chúng.

#### Thiết lập của model

Một model trong `forRoot({{ '{' }} models {{ '}' }})` là một `LanguageModel` từ một package provider, hoặc một định nghĩa có `LanguageModel` làm `model` của nó cùng các thiết lập riêng. Các model Claude của cửa hàng có giá của chúng, và model mặc định có một fallback từ một provider khác:

[[CODE:1]]

Mỗi thiết lập lấy từ lời gọi, nếu không có thì từ định nghĩa của model, nếu không nữa thì từ `defaults` của module. Một lời gọi tới `default` ở trên được gửi `maxOutputTokens: 4000`, và một lời gọi tới `fast` hoặc `backup` được gửi `maxOutputTokens: 1000`; một lời gọi đặt `maxOutputTokens: 200` sẽ gửi giá trị đó, bất kể model nào trả lời. `fast` cho mỗi lần thử 15 giây, các model khác 45 giây.

| Thiết lập | Đặt ở |
| --- | --- |
| `timeout`, `retry`, `resilience` | Lời gọi, model, `defaults` |
| `maxOutputTokens`, `temperature`, `providerOptions`, `headers` | Lời gọi, model, `defaults` |
| `maxSteps`, `budget` | Lời gọi, `defaults` |
| `fallback` | Lời gọi, model |
| `pricing` | Model |
| `onUsage` | Lời gọi, và module: cả hai đều được gọi |
| `topP`, `topK`, `seed`, `stopSequences`, `presencePenalty`, `frequencyPenalty`, `toolChoice`, `fallbackIf`, `abortSignal` | Lời gọi |

`providerOptions` là các tùy chọn riêng của package provider, được đánh key theo tên provider, còn `headers` là các HTTP header được gửi kèm mỗi request tới provider.

Trong `models`, một model cũng có thể là một chuỗi model id như `'openai/gpt-5'`, thứ mà AI SDK gửi qua [AI Gateway](https://vercel.com/docs/ai-gateway). Trong một lời gọi, một chuỗi luôn là tên của một trong các model của module. Một lời gọi cũng có thể nhận một `LanguageModel` làm `model`, hoặc trong `fallback` của nó: model đó không có thiết lập riêng, và `model.name` của kết quả là `undefined`.

#### Tự gọi AI SDK

Để tự gọi AI SDK, hãy inject model. `@InjectModel('fast')` inject `LanguageModel` mà `fast` chỉ tới, còn `@InjectModel()` inject model `default`:

[[CODE:2]]

Một tên mà module không cấu hình sẽ thất bại lúc khởi động, nêu tên class đã yêu cầu nó: `SummariesService: @InjectModel('fats') asks for a model AiModule does not configure.` Model là `LanguageModel` nguyên trạng của provider, nên một lời gọi thực hiện bằng nó không có gì từ những thứ `AiService` bổ sung: không timeout, fallback model, ngân sách hay usage event, và dùng retry riêng của AI SDK (`maxRetries`, mặc định là 2) thay cho các policy bên dưới. `AiModels` liệt kê các model đã cấu hình, với `names()`, `has(name)` và `get(name)`.

#### Retry, timeout và fallback

Model provider có lúc thất bại: họ trả về 429 khi bạn gửi quá nhiều, 529 khi bị quá tải, và thỉnh thoảng mất cả phút mới trả lời. Mọi lời gọi model chạy dưới các policy của [`@nestjs/resilience`](/reliability/resilience), được dựng từ ba thiết lập:

- **`timeout`**: một `TimeoutPolicy`, mặc định `'60s'`, cho mỗi lần thử: tính tới khi có toàn bộ câu trả lời với `generateText()` và `generateObject()`, tới chunk đầu tiên với `streamText()`. Thời gian các tool chạy không được tính, vì lúc đó model đã trả lời. `false` sẽ tắt nó.
- **`retry`**: một `RetryPolicy`, với các tùy chọn của nó: `attempts` (mặc định 3, tính cả lần đầu), `backoff` (từ `'1s'`, nhân đôi tới `'30s'`, với full jitter) và `retryIf`. Những gì provider đánh dấu là có thể retry sẽ được retry, gồm các response 408, 409, 429 và 5xx cùng các kết nối thất bại, và timeout cũng vậy. Header `retry-after` được tôn trọng, và một header yêu cầu chờ lâu hơn `backoff.maxDelay` sẽ chuyển sang fallback thay vào đó. `retry: false` tắt retry.
- **`fallback`**: các model được thử, theo thứ tự, khi các lần retry của model đã hết, mỗi model dưới các policy riêng của nó. Một lời gọi tự đặt fallback với `fallback: ['default']`, hoặc không có với `fallback: false`, và `fallbackIf` thu hẹp những lỗi nào sẽ chuyển tiếp.

Một lời gọi có thể thay đổi bất kỳ thiết lập nào trong số đó:

[[CODE:3]]

Chỉ `fallback` của model riêng của lời gọi mới được đi theo: `fallback` của một fallback model thì không, nên một lời gọi cần đi tiếp tới một model thứ ba phải liệt kê cả hai, như ở trên. `APICallError` là lỗi của AI SDK cho một response của provider, từ `ai`. Một số lỗi không bao giờ chuyển tiếp, bất kể `fallbackIf` nói gì: việc abort lời gọi, một câu trả lời không khớp với schema của `generateObject()`, và các lỗi của AI SDK cho một lời gọi mà nó không thể gửi, chẳng hạn một prompt không hợp lệ.

Mỗi lần fallback được log dưới dạng cảnh báo qua `Logger` của Nest, kèm model đã thất bại, model mà lời gọi chuyển sang, và nguyên nhân: class của lỗi, HTTP status và message của nó. Một API key bị thu hồi hay một request bị từ chối không thể ẩn sau một fallback chạy được: `The model "default" failed (APICallError, 401: Invalid API key); falling back to "backup".`

Khi một chunk đã tới được trình duyệt, hoặc các tool của một lời gọi model đã bắt đầu chạy, kết quả của nó được chốt: không timeout, retry hay fallback nào thay thế nó, nên không câu trả lời nào bị gửi hai lần và không tool nào chạy hai lần.

Một `abortSignal` được truyền cho lời gọi sẽ hủy nó ngay lập tức, không retry hay fallback, và lời gọi reject với reason của signal. Bên trong một route có resilience, chẳng hạn route có `@Timeout()` từ `@nestjs/resilience`, lần thử của route cũng dừng các lời gọi model mà nó thực hiện theo cách tương tự.

#### Khi một lời gọi thất bại

Khi mọi lần thử đều thất bại, trên mọi model được thử, lời gọi reject với `AiModelError`. `attempts` của nó liệt kê từng model, lần thử và lỗi (một `ResilienceTimeoutError` cho lần thử hết thời gian), và `cause` của nó là lỗi cuối cùng. Các lỗi của package kế thừa `AiError`:

| Lỗi | Khi nào |
| --- | --- |
| `AiModelError` | Mọi lần thử đều thất bại, trên mọi model được thử: `attempts`, `cause` |
| `AiOutputError` | Câu trả lời của `generateObject()` không phải JSON hoặc không khớp với schema, hoặc model vẫn gọi tool sau `maxSteps`: `text` |
| `AiBudgetExceededError` | Lời gọi đã tiêu hết ngân sách, trước lời gọi model tiếp theo: `usage`, `cost`, `limit` |
| `AiConfigurationError` | Một model, một agent function hoặc một tùy chọn mà package không dùng được: lúc khởi động, hoặc khi lời gọi được thực hiện, trước khi bất cứ thứ gì được gửi |
| `AiToolError` | Những gì model được báo về một lời gọi tool thất bại: `toolName`, tên của agent function |

Một route gọi model sẽ trả lời `AiModelError` bằng 500, như mọi lỗi khác. Một exception filter có thể báo rằng assistant đang không khả dụng thay vào đó:

[[CODE:4]]

#### Policy của riêng bạn

`resilience` nhận một policy, hoặc tên một preset của `ResilienceService`, thay cho `retry` và `timeout`: chẳng hạn một circuit breaker hoặc một bulkhead dùng chung với phần còn lại của ứng dụng. Các fallback model vẫn được thử quanh nó, nên một lời gọi tới một model có breaker đang mở sẽ chuyển sang model tiếp theo:

[[CODE:5]]

Một preset thay thế `retry` và `timeout` của model bằng của chính nó: một preset không có `timeout` sẽ để các lời gọi của model không có timeout, và các lần retry của preset chỉ tôn trọng `retry-after` nếu `backoff` của nó có làm vậy. Một lần reject của policy như vậy (`CircuitOpenError`, `BulkheadFullError`) mà không fallback nào nhận sẽ tới bên gọi nguyên trạng: một lỗi của `@nestjs/resilience`, mà `ResilienceModule` trả lời bằng 503 trên một HTTP route. Chỉ định một preset mà không import `ResilienceModule` sẽ thất bại với một `AiConfigurationError`.

Các policy publish các event của `@nestjs/resilience` trên các diagnostics channel `nestjs:resilience:<type>`: `retry`, `timeout` và `fallback`, được đặt tên theo model (`ai:fast retry`, `ai:fast fallback`), với `label` của lời gọi làm `source` của chúng (`AiService` cho lời gọi không có label). Để log các lần retry của mọi lời gọi model:

[[CODE:6]]

#### Usage, chi phí và ngân sách

Mọi lời gọi model đã trả lời đều phát ra một usage event. Với `pricing` của một model, theo một đơn vị tùy bạn chọn cho mỗi triệu token, nó cũng có một `cost`, cùng đơn vị đó. `onUsage` nhận chúng:

[[CODE:7]]

| Thuộc tính | Là gì |
| --- | --- |
| `label` | `label` của lời gọi, để phân biệt các lời gọi |
| `model` | Model đã trả lời: `name`, `provider`, `modelId` |
| `step`, `attempt` | Bước của lời gọi model trong lời gọi (từ 0), và lần thử của model này cho bước đó (từ 1) |
| `fallback`, `stream` | Có phải một fallback model đã trả lời không, và lời gọi có được stream không |
| `usage` | `inputTokens` (tính cả token lấy từ cache), `outputTokens`, `totalTokens`, `cachedInputTokens`, `reasoningTokens` |
| `cost` | Các input token không đọc từ cache tính theo `input`, các token từ cache theo `cachedInput` (mặc định: `input`), và các output token theo `output`; `undefined` khi không có `pricing` |
| `durationMs`, `finishReason` | Lời gọi model mất bao lâu, và tại sao model dừng |

Một lời gọi cũng có thể nhận `onUsage` riêng, được gọi sau của module. Những gì một listener throw sẽ được log, và không bao giờ làm lời gọi thất bại. Cửa hàng đo số token của assistant theo từng khách hàng:

[[CODE:8]]

Một `budget` giới hạn một lời gọi: `maxTokens` và `maxCost`, trên mọi lời gọi model của nó. Một lời gọi có dùng tool sẽ thực hiện nhiều lời gọi model, và ngân sách được kiểm tra trước mỗi lời gọi: một lời gọi đã tiêu hết ngân sách sẽ reject, trước lời gọi model tiếp theo, với `AiBudgetExceededError`, mang theo những gì đã tiêu (`usage`, `cost`) và `limit`. Việc kiểm tra không thể dừng một lời gọi model giữa chừng, nên lời gọi cuối cùng có thể khiến một lời gọi vượt ngân sách. Một model không có `pricing` được tính là miễn phí. `defaults.budget` áp dụng một ngân sách cho mọi lời gọi:

[[CODE:9]]

> info **Hint** Từ `@nestjs/observe` 0.3.20, [NestJS Observe](/observability/overview) ghi lại model và số token của mọi lời gọi model trên outbound span của nó, như với bất kỳ lời gọi AI SDK nào: xem [Lời gọi model](/observability/sdk#model-calls). Một model được chỉ định bằng gateway id, như `'openai/gpt-5'`, được gọi qua host của AI Gateway, `ai-gateway.vercel.sh`: hãy thêm nó vào `outgoing.llm.hosts` để Observe đọc được cả những lời gọi đó.
