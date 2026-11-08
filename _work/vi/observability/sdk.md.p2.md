#### Instrument tự động

Mọi thứ trong phần này đều được ghi lại mà không cần dòng code nào của bạn; chỉ cần cài SDK là đủ. Các tùy chọn chỉ để thu hẹp hoặc tắt nó đi.

##### Query database và HTTP gửi ra ngoài

Kể từ `@nestjs/observe` 0.3.0, các query database và request gửi ra ngoài xuất hiện dưới dạng span mà không cần cấu hình gì, lồng bên dưới method đã thực hiện chúng. Một lời gọi repository chậm sẽ cho thấy nó đang chờ _câu lệnh nào_.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/sql.webp" alt="Một query được mở trong waterfall" /></figure>

Database được instrument ở tầng driver thay vì ORM: `pg`, `mysql2`, `mssql` và `mongodb` được phát hiện nếu ứng dụng của bạn đã phụ thuộc vào chúng, điều này bao phủ TypeORM, MikroORM, Drizzle, Mongoose, Knex, Sequelize và các driver adapter của Prisma mà không cần nêu tên cái nào. SQL Server là ngoại lệ: `mssql` là thứ mà TypeORM và SQL Server adapter của Prisma chạy trên đó, nhưng Knex, Sequelize và MikroORM nói chuyện với SQL Server trực tiếp qua `tedious`, thứ chưa được hỗ trợ (cũng như `mssql/msnodesqlv8`). Các ORM đi kèm bản sao driver lồng bên trong riêng (MikroORM và Mongoose làm vậy mỗi khi phiên bản không khớp) cũng được xử lý. Các công việc nội bộ của driver (bắt tay kết nối, xác thực, ping) không được ghi lại. Một span query được gắn nhãn bằng động từ và bảng của nó (`SELECT users`) và mang câu lệnh với **mọi literal bị loại bỏ** - chuỗi, số, danh sách `IN (...)` và comment đều được thay thế trước khi span rời khỏi process, còn các tham số bind thì hoàn toàn không bao giờ được đọc. Các query lặp lại dưới cùng một cha được gộp thành một node duy nhất kèm số lần, nên một lỗi N+1 hiện ra là `SELECT order_items ×47` thay vì 47 dòng.

Các client khác, trong đó có Redis và Kafka, không được instrument ở tầng library. Tuy nhiên, một ứng dụng Nest gần như luôn đăng ký chúng dưới dạng provider - một client `ioredis` từ một factory, một `ClientKafka` từ `ClientsModule` - và SDK ghi lại các lời gọi method của mọi provider: mỗi lời gọi trên client là một span dưới method đã thực hiện nó, và một lời gọi trả về promise, như các lệnh của `ioredis`, được tính giờ cho đến khi promise settle. Một client được tạo và gọi bên ngoài dependency injection sẽ không được ghi lại.

HTTP gửi ra ngoài được đọc từ chính diagnostics channel của Node, nên `fetch`, `undici` và mọi thứ xây dựng trên `node:http` (axios, got, hầu hết các SDK) đều được bao phủ mà không cần patch gì. Span được gắn nhãn `GET api.example.com` và mang URL với các query parameter nhạy cảm được che đi. SDK cũng gửi trace id hiện tại dưới dạng `x-request-id`, giúp [tracing HTTP-to-HTTP](/observability/distributed-tracing#http-to-http) trở nên tự động. Khi bật tùy chọn [`openTelemetry`](/observability/opentelemetry#running-beside-opentelemetry), nó gửi thêm một `traceparent` theo chuẩn W3C: `http.traceContext: false` sẽ không gửi header đó, còn `propagateTraceId` quyết định cả hai header được gửi tới đâu.

[[CODE:12]]

Đặt `outgoing: false` để tắt hết, hoặc `database: false` / `http: false` để tắt riêng từng phần.

> info **Hint** Các span này **không bị tính phí**. Chúng là chi tiết của một span method mà bạn đã gửi, nên chúng không được tính vào Observability Event hay giới hạn tốc độ của bạn. Một request chạy mười query tốn chi phí như trước.

##### Lời gọi model

Kể từ `@nestjs/observe` 0.3.20, một lời gọi `fetch` tới một model provider còn ghi lại trên span gửi ra ngoài những gì lời gọi đã dùng: model, số token đầu vào, đầu ra và đầu vào được cache mà response của provider ghi, và, với stream, thời gian tới event đầu tiên. OpenAI, Azure OpenAI, Anthropic, Google Gemini và Vertex AI, Amazon Bedrock, Mistral, Groq, OpenRouter, Together AI, DeepSeek, xAI, Cohere và Perplexity được nhận diện theo host, nên các SDK chính thức, Vercel AI SDK và LangChain đều được bao phủ mà không cần nêu tên.

- **Được đọc khi response đi qua.** SDK đọc response theo tốc độ mà code của bạn đọc, kể cả stream, và chuyển nó đi nguyên vẹn. Một stream mà code của bạn hủy cũng bị hủy ở phía provider.
- **Prompt và completion không bao giờ được gửi đi.** Chỉ có model và số token rời khỏi process.
- **Chỉ với `fetch`.** Một lời gọi thực hiện qua `node:http` - axios, hoặc client mặc định của AWS SDK cho Bedrock - vẫn giữ span gửi ra ngoài thông thường của nó mà không có model hay token.

Một gateway đứng trước các provider (LiteLLM, Portkey, proxy của riêng bạn) hoặc một model tự host có API tương thích OpenAI được thêm vào theo host, và các lời gọi của nó được gắn tag provider `custom`. `outgoing: {{ '{' }} llm: false {{ '}' }}` ngừng đọc các lời gọi model trong khi vẫn giữ span thông thường của chúng:

[[CODE:13]]

Một [quy tắc production](/observability/production-rules) có thể giới hạn số lời gọi model mà một request được thực hiện.

##### WebSocket gateway

Các message được xử lý bởi `@SubscribeMessage()` được báo cáo dưới dạng request với protocol `ws` và operation id là `GatewayClass:pattern`, trên mọi platform adapter. Khối tùy chọn `ws` nhận cùng các hook `ignore`, `tags`, `setAttributes` và `getUserId` như các transport khác; mỗi hook nhận `{{ '{' }} gateway, pattern, client, data {{ '}' }}`. Việc kết nối và ngắt kết nối không phải là operation và không được báo cáo.

##### Queue

Cả `@nestjs/bullmq` lẫn `@nestjs/bull` bản gốc đều được instrument: mỗi lần chạy processor được báo cáo dưới dạng một job, kèm thời gian chờ trong queue, số thứ tự lần thử và kết quả. Một job được thêm từ bên trong một operation đang được trace sẽ thừa hưởng trace id của operation đó - xem [Distributed tracing](/observability/distributed-tracing#queue-jobs-bullmq-and-bull).

##### Metric runtime và profiling

[[CODE:14]]

`runtimeMetrics` (mặc định `true`) lấy mẫu bộ nhớ, CPU, garbage collection và độ trễ event loop theo chu kỳ (`runtimeMetricsInterval`, mặc định `60000` ms) và cung cấp dữ liệu cho **Profiler**. Chính các mẫu đó còn đóng vai trò heartbeat của ứng dụng: một cảnh báo **Telemetry silence** sẽ kích hoạt khi chúng ngừng đến, cho bạn một cơ chế giám sát uptime nhẹ nhàng mà không cần probe bên ngoài.

#### Lỗi và request thất bại

Một lỗi thoát ra khỏi controller, resolver hoặc job được tự động ghi lại. Các tùy chọn này quyết định những gì đi kèm với nó: mã nguồn quanh frame lỗi, và header cùng body của request đã thất bại.

##### Ngữ cảnh mã nguồn của lỗi

Các lỗi lan ra khỏi controller, resolver, job hoặc span được tự động ghi lại. Khi bật `sourceContext` (mặc định), SDK còn đọc các dòng mã nguồn quanh mỗi stack frame thuộc ứng dụng của một lỗi đã ghi lại và đính kèm chúng. Điều này cho phép dashboard hiển thị đoạn code lỗi cạnh stack trace, kể cả với một lỗi production trên một bản build mà bạn không checkout.

[[CODE:15]]

Đây là tùy chọn của `createObserveModule()`, không phải `forRoot()`. Đặt `sourceContext: false` để tắt, hoặc truyền một object để tinh chỉnh các giá trị mặc định:

| Tùy chọn         | Type      | Mặc định | Mô tả                                                                                                                                                                                                                                                                                                                                                                          |
| ---------------- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `linesOfContext` | `number`  | `5`      | Số dòng được đọc ở mỗi phía của dòng thuộc frame.                                                                                                                                                                                                                                                                                                                              |
| `maxFrames`      | `number`  | `5`      | Số frame thuộc ứng dụng, tính từ đỉnh stack, được đính kèm mã nguồn. Giới hạn kích thước payload với các stack sâu.                                                                                                                                                                                                                                                            |
| `sourceMaps`     | `boolean` | `false`  | Map các frame đã compile ngược lại qua source map trước khi đọc mã nguồn. Chỉ cần thiết nếu process chạy code đã compile _mà không có_ hỗ trợ source map của chính Node (`--enable-source-maps` hoặc `process.setSourceMapsEnabled(true)`); khi đã bật hỗ trợ đó, các frame vốn đã mang vị trí gốc và tùy chọn này là thừa. Tốn một lần parse map cho mỗi file đã compile ở lần chạm đầu tiên, rồi được cache lại. |

> warning **Warning** Bật tùy chọn này sẽ gửi các đoạn mã nguồn của ứng dụng (thường là vài dòng quanh lỗi) lên dashboard, nơi chúng được lưu cùng lỗi. Các frame bên trong `node_modules` và phần nội bộ của Node không bao giờ được đọc, chỉ có mã nguồn của ứng dụng. Hãy tắt nó nếu việc gửi đi bất kỳ đoạn mã nguồn nào là không chấp nhận được với codebase của bạn.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/error-with-source.webp" alt="Thẻ lỗi kèm ngữ cảnh mã nguồn" /></figure>

##### Ghi lại request thất bại và chậm

Khi một HTTP request **thất bại**, SDK ghi lại kèm theo một danh sách nhỏ, cố định các header được phép - `user-agent`, `content-type`, `content-length`, `accept`, `host`, `origin` và `referer`. Không header nào trong số này dùng để xác thực hay định danh người gọi. Nếu bạn đặt `slowerThanMs`, các request chạy ít nhất bằng khoảng đó cũng được ghi lại theo cùng cách, dù có thất bại hay không. Một request bình thường không ghi lại gì. Request body mặc định **tắt**; hãy bật tường minh nếu bạn muốn:

[[CODE:16]]

Mọi thứ được ghi lại đều đi qua [`redaction`](/observability/sdk#logs) trước khi rời khỏi process: các key nhạy cảm (`password`, `token`, `authorization`, ...) được che theo tên bên trong body, và việc chỉ định một header nhạy cảm sẽ ghi lại `[REDACTED]` thay vì giá trị của nó. `capture: false` không ghi lại gì cả. Dữ liệu ghi lại được hiển thị trên trang chi tiết của request dưới dạng thẻ **Request**.

#### Log và liên kết trace

Mỗi lần thực thi đều có một trace id. Các tùy chọn này quyết định các dòng log của bạn liên quan tới nó như thế nào: được chuyển tiếp lên dashboard, hoặc chỉ được gắn id để hệ thống log của riêng bạn có thể link tới trace.

##### Log

[[CODE:17]]

`forwardLogs` (mặc định `false`) gửi các dòng log của ứng dụng (bất cứ thứ gì được ghi qua `Logger` của Nest) lên dashboard, liên kết với trace đang hoạt động khi mỗi dòng được ghi. Trên trang execution, mỗi dòng được đặt lên dòng thời gian của trace, cạnh span đang chạy khi nó được ghi. Việc chuyển tiếp log có sẵn từ gói Pro trở lên.

Chuyển tiếp log đưa chúng lên hạ tầng mà bạn không kiểm soát, nên che giấu dữ liệu được bật mặc định. Cơ chế che giấu đó cũng làm sạch message và stack của mọi lỗi đã ghi lại cùng mọi dữ liệu request đã ghi lại, bất kể `forwardLogs` có bật hay không:

| Trường của `redaction` | Type       | Mặc định       | Mô tả                                                                                                                                                                                                                                                                    |
| ---------------------- | ---------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `enabled`              | `boolean`  | `true`         | Có làm sạch gì hay không.                                                                                                                                                                                                                                                |
| `useDefaultPatterns`   | `boolean`  | `true`         | Áp dụng các pattern có sẵn: bearer token, JWT, AWS key id, PEM private key, secret dạng `key=value`, và số thẻ hợp lệ theo thuật toán Luhn. Chỉ tắt nếu bạn thay thế hoàn toàn chúng bằng `patterns` của riêng mình; không có trường hợp hợp lệ nào cho việc chuyển tiếp log mà không che giấu. |
| `patterns`             | `RegExp[]` | -              | Các pattern bổ sung cần che, cho những secret có dạng mà chỉ codebase của bạn biết (prefix token nội bộ, định danh khách hàng). Luôn được áp dụng như thể là global, nên một lần khớp không bao giờ chỉ giới hạn ở lần xuất hiện đầu tiên trong một dòng.                |
| `keys`                 | `string[]` | -              | Các key bổ sung có giá trị bị che hoàn toàn (trong thuộc tính log, header và body đã ghi lại, và query string của URL), ngoài danh sách có sẵn. So sánh không phân biệt hoa thường và bỏ qua `-`/`_`, nên `apiKey`, `api_key` và `API-KEY` là cùng một mục.             |
| `replacement`          | `string`   | `'[REDACTED]'` | Text thay thế cho mọi thứ khớp.                                                                                                                                                                                                                                          |

> info **Hint** Kể cả khi tắt `forwardLogs`, SDK vẫn bổ sung cho `ConsoleLogger` để mọi dòng được ghi bên trong một lần thực thi đang được trace đều mang trace id của nó (`attachTraceIdToLogs`, xem [Liên kết trace](#trace-correlation)). Điều đó cho phép bạn liên kết hệ thống tổng hợp log của riêng mình với trace trên dashboard mà không cần gửi nội dung log đi đâu cả.

##### Liên kết trace

Đây cũng là các tùy chọn của `createObserveModule()`. Chúng quyết định cách request nhận được trace id và cách id đó xuất hiện trong log của riêng bạn:

[[CODE:18]]

| Tùy chọn              | Type                       | Mặc định                                                      | Mô tả                                                                                                                               |
| --------------------- | -------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `traceIdKey`          | `string`                   | `'traceId'`                                                   | Key dùng để lưu trace id trong request context, để lấy ra sau này thông qua `TracerService`.                                        |
| `traceIdGenerator`    | `(req: unknown) => string` | Dùng lại một `x-request-id` đúng định dạng (header HTTP, hoặc metadata của packet microservice) nếu có, nếu không thì một UUID v7 | Sinh trace id cho mỗi request. Được gọi với request object với HTTP; với các protocol khác, nó nhận transport context. |
| `attachTraceIdToLogs` | `boolean`                  | `true`                                                        | Bổ sung cho `ConsoleLogger` để đưa trace id vào log message, để log có thể được liên kết với trace kể cả khi không có `forwardLogs`. Ở định dạng text mặc định, id nằm ở cuối dòng, sau message (`   Trace ID: <id>`); với [log JSON](/application/logger#json-logging), nó là trường `traceId`. Các dòng được ghi bên ngoài một lần thực thi đang được trace giữ nguyên. |

Vì generator mặc định dùng lại `x-request-id` gửi đến, một chuỗi các HTTP service vốn đã dùng chung một trace mà không cần cấu hình thêm. Các service được instrument bằng OpenTelemetry truyền trace tiếp qua `traceparent` thay vào đó, header mà tùy chọn `openTelemetry` của `forRoot()` đọc và gửi - xem [Chạy cạnh OpenTelemetry](/observability/opentelemetry#running-beside-opentelemetry). Điều tương tự áp dụng cho các transport microservice: TCP và Redis trên `@nestjs/microservices` 12.0.4 trở lên, và NATS, Kafka, RabbitMQ, MQTT 5 và gRPC trên 12.3.3 trở lên. Truyền trace qua các phiên bản cũ hơn và qua GraphQL cần thêm vài dòng code - xem [Distributed tracing](/observability/distributed-tracing).
