### Embedding

Một embedding model biến một đoạn text thành một vector, để ứng dụng có thể so sánh các đoạn text theo ý nghĩa của chúng: `AiService` gọi các embedding model được đăng ký theo tên, với timeout, retry và usage event, giống như cách nó gọi language model.

Một khách hàng của cửa hàng tìm kiếm "mèo nhà tôi không chịu ăn", và việc tìm kiếm không ra gì: không sản phẩm nào ghi như vậy, còn sản phẩm họ muốn là một "hỗ trợ kích thích ăn nhẹ nhàng cho mèo kén ăn". Khi so sánh dưới dạng vector, hai đoạn này rất gần nhau. Cửa hàng embed phần mô tả của các sản phẩm một lần, giữ các vector cạnh sản phẩm, và embed mỗi lần tìm kiếm khi nó tới.

Package dừng lại ở các vector. Ứng dụng của bạn lưu chúng, trong PostgreSQL với `pgvector` hoặc trong một vector database, và chia các tài liệu dài thành nhiều đoạn nếu cần.

#### Đăng ký model

Embedding model có registry riêng, `embeddingModels`, cạnh `models`. Các model của cửa hàng đến từ OpenAI, qua package provider của nó:

[[CODE:1]]

[[CODE:2]]

Một embedding model là thứ mà một package provider trả về, như ở trên, hoặc một định nghĩa có nó làm `model` cùng [các thiết lập riêng](/ai/embeddings#embedding-settings). Một chuỗi model id, như `'openai/text-embedding-3-small'`, được gửi qua [AI Gateway](https://vercel.com/docs/ai-gateway), giống như trong `models`.

Các lời gọi không chỉ định model sẽ dùng `default`, và model được đăng ký đầu tiên không bao giờ được chọn thay cho nó. Hai registry không dùng chung tên: `default` ở trên là một model cho `generateText()` và một model khác cho `embed()`. Một ứng dụng chỉ embed sẽ bỏ `models` đi, còn một ứng dụng không có model nào ở cả hai sẽ thất bại lúc khởi động.

#### Gọi một embedding model

`embed()` embed một đoạn text, còn `embedMany()` embed một danh sách:

[[CODE:3]]

`model` chỉ định một trong các `embeddingModels`, mặc định là `default` khi bỏ trống, còn `label` đặt tên cho lời gọi trong [usage event](/ai/embeddings#usage-and-cost) và trong các event của các policy của nó. Một lời gọi cũng có thể nhận một `EmbeddingModel` làm `model`: model đó không có thiết lập riêng, và `model.name` của kết quả là `undefined`. Kết quả có nhiều thứ hơn là các vector:

| Thuộc tính | Là gì |
| --- | --- |
| `embedding`, `embeddings` | Vector của `embed()`, và các vector của `embedMany()`, theo thứ tự của `values` |
| `value`, `values` | Các đoạn text đã được embed |
| `usage` | Số token mà provider báo cáo, cộng dồn trên các request của nó: `tokens` |
| `cost` | Chi phí của lời gọi, với một model có `pricing` |
| `attempts` | Các request tới provider mà lời gọi đã thực hiện, kể cả các lần retry |
| `model` | Model đã trả lời: `name`, `provider` và `modelId` của nó |
| `warnings`, `providerMetadata` | Những gì provider thêm vào các câu trả lời của nó |
| `response`, `responses` | HTTP response của provider cho `embed()`, và mỗi request của `embedMany()` một response |

Một giá trị không phải chuỗi, hoặc một model mà module không cấu hình, sẽ bị từ chối với một `AiConfigurationError` trước khi bất cứ thứ gì được gửi đi.

Để so sánh hai vector trong bộ nhớ, `cosineSimilarity()` từ `ai` nhận chúng và trả về một số từ -1 tới 1. Với hơn vài trăm đoạn text, hãy để database tìm các vector gần nhất, với một index.

#### Thiết lập embedding

Một định nghĩa cho model các thiết lập riêng, còn `embeddingDefaults` áp dụng thiết lập cho mọi lời gọi embedding. Mỗi thiết lập lấy từ lời gọi, nếu không có thì từ định nghĩa của model, nếu không nữa thì từ `embeddingDefaults`:

[[CODE:4]]

| Thiết lập | Đặt ở |
| --- | --- |
| `timeout`, `retry`, `resilience` | Lời gọi, model, `embeddingDefaults` |
| `maxParallelCalls`, `providerOptions`, `headers` | Lời gọi, model, `embeddingDefaults` |
| `pricing` | Model |
| `onEmbeddingUsage` | Lời gọi, và module: cả hai đều được gọi |
| `abortSignal`, `label` | Lời gọi |

`defaults` của module dành cho language model, và không có gì trong đó áp dụng tới một lời gọi embedding: không phải timeout, header hay tùy chọn provider của chúng. `budget` và `fallback` là thiết lập chỉ dành cho language model.

`providerOptions` là các tùy chọn riêng của package provider, được đánh key theo tên provider, còn `headers` là các HTTP header được gửi kèm mỗi request tới provider. Số chiều của một vector là một tùy chọn như vậy, với các model cho phép bạn chọn nó, như `documents` làm ở trên.

#### Batch

`embedMany()` nhận bao nhiêu giá trị tùy bạn có. AI SDK chia chúng thành các request tới provider, mỗi request chứa nhiều giá trị nhất mà provider cho phép, và gửi `maxParallelCalls` request mỗi lần: mặc định là 4, hoặc từng request một với một model không nhận được lời gọi song song. Bất kể request nào trả lời trước, `embeddings` vẫn giữ thứ tự của `values`.

#### Retry, timeout và hủy

Mọi request tới provider đều chạy dưới các policy của [`@nestjs/resilience`](/reliability/resilience), được dựng từ cùng các thiết lập như [của một language model](/ai/models#retries-timeouts-and-fallback): `timeout`, mặc định `'60s'`, và `retry`, mặc định 3 lần thử, retry những gì provider đánh dấu là có thể retry và các timeout, và tôn trọng header `retry-after`.

Chúng áp dụng cho từng request, không phải cho cả lời gọi. `timeout` là thời gian một request được phép mất, nên một lời gọi với 20.000 giá trị có thể chạy bao lâu tùy nó cần, và một request thất bại được retry riêng, không gửi lại các request khác.

Khi một request hết số lần thử, lời gọi reject với [`AiModelError`](/ai/models#when-a-call-fails), có `attempts` là của request đó, và các request vẫn đang chạy sẽ bị abort. `embedMany()` trả về tất cả vector hoặc không vector nào, nên những gì các request đã xong embed được cũng mất theo. Để giữ tiến độ của một công việc lớn, hãy gửi nó theo từng nhóm và lưu từng nhóm, trong một queue job hoặc một step của [workflow](/reliability/workflows):

[[CODE:5]]

Một `abortSignal` được truyền cho lời gọi sẽ hủy các request đang chạy và thời gian backoff của một lần retry, và lời gọi reject với reason của signal. Vì `timeout` chỉ bao phủ một request, đây cũng là cách để đặt hạn chót cho cả lời gọi:

[[CODE:6]]

Bên trong một route có resilience, chẳng hạn route có `@Timeout()` từ `@nestjs/resilience`, lần thử của route cũng dừng các request theo cách tương tự.

Một lời gọi embedding không có fallback model. Vector của các model khác nhau không thể so sánh với nhau, kể cả khi chúng có cùng số chiều, nên một search index được ghi bằng một model không thể đọc bằng model khác.

#### Policy của riêng bạn

`resilience` nhận một policy, hoặc tên một preset của `ResilienceService`, thay cho `retry` và `timeout`, giống như [với một language model](/ai/models#policies-of-your-own). Nó chạy quanh mỗi request tới provider, nên một giới hạn tần suất gọi ra ngoài hoặc một bulkhead sẽ đếm theo request, trên mọi lời gọi dùng chung nó. Cửa hàng giữ các request embedding trong hạn mức của nó tại provider:

[[CODE:7]]

Hãy cho một policy như vậy đủ chỗ để các request của một lời gọi chờ. Một request không tìm thấy token sẽ reject cả lời gọi với `OutboundRateLimitError` khi nó đã chờ `maxWait`, mặc định là 0, và một request gặp bulkhead đầy sẽ reject nó với `BulkheadFullError` trừ khi bulkhead có `maxQueue` để giữ nó.

Các policy publish các event của `@nestjs/resilience` trên các diagnostics channel `nestjs:resilience:<type>`, được đặt tên theo model (`ai:embedding:default retry`), với `label` của lời gọi làm `source` của chúng.

#### Usage và chi phí

Một lời gọi thành công phát ra một usage event, với số token mà các request của nó báo cáo. Với `pricing` của một model, tức giá cho mỗi triệu input token theo một đơn vị tùy bạn chọn, event cũng có một `cost`, cùng đơn vị đó. `onEmbeddingUsage` nhận chúng:

[[CODE:8]]

| Thuộc tính | Là gì |
| --- | --- |
| `operation` | `'embed'` hoặc `'embedMany'` |
| `label` | `label` của lời gọi, để phân biệt các lời gọi |
| `model` | Model đã trả lời: `name`, `provider`, `modelId` |
| `inputCount` | Lời gọi đã embed bao nhiêu giá trị |
| `usage` | Số token mà provider báo cáo: `tokens` |
| `attempts` | Các request tới provider mà lời gọi đã thực hiện, kể cả các lần retry |
| `durationMs` | Lời gọi mất bao lâu, kể cả retry và backoff |
| `cost` | Số token tính theo `pricing.input`; `undefined` khi không có `pricing` |

Một lời gọi cũng có thể nhận `onEmbeddingUsage` riêng, được gọi sau của module. `onUsage` dành cho language model, và không được gọi. Những gì một listener throw sẽ được log, và không bao giờ làm lời gọi thất bại. Event không mang theo đoạn text hay vector nào, nên log nó là an toàn.

Các event không phải là sổ tính tiền: một provider có thể tính tiền cho một request đã timeout, và một lời gọi thất bại không phát ra gì cả, kể cả với những request mà nó đã hoàn tất.

#### Tự gọi AI SDK

Để tự gọi AI SDK, hãy inject model. `@InjectEmbeddingModel('documents')` inject `EmbeddingModel` mà `documents` chỉ tới, còn `@InjectEmbeddingModel()` inject model `default`:

[[CODE:9]]

Một tên mà module không cấu hình sẽ thất bại lúc khởi động, nêu tên class đã yêu cầu nó. Model là `EmbeddingModel` nguyên trạng của provider, nên một lời gọi thực hiện bằng nó không có gì từ những thứ `AiService` bổ sung: không policy hay usage event, và dùng retry riêng của AI SDK (`maxRetries`, mặc định là 2). `AiEmbeddingModels` liệt kê các model đã cấu hình, với `names()`, `has(name)` và `get(name)`.

Với `forRootAsync()`, factory của nó trả về `embeddingModels` giống như trả về `models`, và `@InjectEmbeddingModel()` cần những gì [`@InjectModel()` cần](/ai/overview#async-configuration): một class được load sau khi module được định nghĩa sẽ liệt kê tên của nó trong `embeddingModelNames`, ở cấp ngoài cùng.

> info **Hint** [Testing](/ai/testing#testing-embeddings) mô tả `FakeEmbeddingModel`, một embedding model dùng cho test mà không gọi provider nào.
