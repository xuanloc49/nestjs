#### Checklist cho production

- **Tính ngân sách thời gian từ đầu đến cuối.** Thời gian mỗi lần thử nhân với số lần thử, cộng backoff, phải nằm gọn trong timeout của client và của load balancer. Với route báo giá, con số đó là khoảng 3.2 giây.
- **Chỉ retry những gì an toàn.** Chỉ đặt `idempotent: true` khi lần chạy thứ hai trong cùng một request là vô hại. Kết hợp nó với `@Idempotent()` để xử lý các lần retry từ client.
- **Truyền signal cho mọi lời gọi I/O.** Thiếu nó, công việc đã bị timeout vẫn tiếp tục chạy ngầm, nằm ngoài tầm nhìn của bulkhead đã cho nó vào.
- **Chỉ retry ở một tầng.** Retry ở entrypoint hoặc trong policy của service, không phải cả hai, và tắt retry trong các SDK và HTTP client bên dưới.
- **Tinh chỉnh từng breaker theo dependency của nó.** Đặt `minimumCalls` đủ cao để hai lỗi lúc nửa đêm không làm nó mở, đặt `openDuration` gần với khoảng thời gian dependency thường cần để hồi phục, và dùng `recordIf` để loại bỏ những lỗi không phải sự cố.
- **Cho mỗi breaker một timeout.** Breaker chỉ học từ những lời gọi đã kết thúc. Một lời gọi bị treo sẽ không bao giờ được đếm, và một lời gọi thăm dò bị treo sẽ giữ một breaker half-open tiếp tục từ chối mọi thứ khác.
- **Nhớ rằng trạng thái là theo từng process.** Khi có nhiều instance, mỗi instance có breaker, bulkhead và giới hạn tần suất gọi ra ngoài riêng, và một lần restart sẽ khởi tạo lại chúng. Mỗi breaker tự mở độc lập, giới hạn bulkhead áp dụng theo từng instance, và một giới hạn tần suất gọi ra ngoài cho phép `limit` lời gọi trên mỗi instance.
- **Giữ fallback rẻ và độc lập.** Một fallback không bao giờ được gọi tới chính dependency mà nó thay thế.
- **Cảnh báo khi có chuyển trạng thái.** Một breaker mở ra và bulkhead từ chối request là những tín hiệu cần gọi người trực.
- **Đăng ký một idempotency store.** Không có store, `@Idempotent()` giữ các bản ghi trong bộ nhớ của từng process, mất sạch sau mỗi lần restart hoặc deploy, và môi trường production sẽ từ chối khởi động. Xem [Lưu key trong PostgreSQL](/reliability/idempotency#store-keys-in-postgresql) trong bài hướng dẫn idempotency.
- **Nối các module cho đúng.** Import `ResilienceModule` một lần, trong root module, và `IdempotencyModule` trước nó. Dùng `inheritAppConfig: true` cho ứng dụng hybrid.
- **Tôn trọng Retry-After ở phía client.** Nó cho client biết khi nào thử lại thì có thể thành công.

#### Tham khảo

##### Tùy chọn của module

`ResilienceModule.forRoot()` nhận các tùy chọn sau. `forRootAsync()` dựng cùng object đó từ một factory, một class implement `ResilienceOptionsFactory`, hoặc một provider có sẵn.

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `defaults` | `ResilienceDefaults` | không có | Giá trị mặc định cho các field của `retry`, `timeout`, `circuitBreaker` và `bulkhead`. Chúng điền vào các stage mà một decorator hoặc preset bật lên, và không bao giờ tự bật một stage. Xem [Đăng ký module](/reliability/resilience#register-the-module). |
| `presets` | `Record<string, ResiliencePreset>` | không có | Các tập stage có tên: `retry`, `timeout`, `circuitBreaker`, `bulkhead`, `outboundRateLimit` và `fallback`. Breaker, bulkhead và giới hạn tần suất gọi ra ngoài của một preset được dùng chung dưới tên của preset. |
| `mapErrors` | `boolean` | `true` | Chuyển các lỗi resilience do bất kỳ handler nào throw, có hay không có decorator, thành lỗi của transport, như liệt kê trong phần Lỗi bên dưới. |
| `isGlobal` | `boolean` | `true` | Đăng ký module ở phạm vi global. Chỉ đăng ký một lần, trong root module. |

Mọi tùy chọn mang giá trị thời gian đều nhận số mili giây hoặc một chuỗi như `'200ms'`, `'2s'` hay `'15m'`. Injection token của các tùy chọn là `RESILIENCE_MODULE_OPTIONS`.

##### Decorator

Mỗi decorator dùng được trên handler hoặc trên class, trừ `@Signal()`, là một parameter decorator.

| Decorator | Tùy chọn (mặc định) |
| --- | --- |
| `@Retry(options)` | `attempts` (3, tính cả lần đầu; `Infinity` retry cho tới khi signal bị abort), `backoff`, `retryIf(error, attempt)` (mọi lỗi trừ lỗi client), `idempotent` (xem [Retry một POST an toàn](/reliability/resilience#retry-a-post-safely)). `@Retry(5)` đặt `attempts`, và `@Retry(false)` tắt một retry được kế thừa. |
| `backoff` (của `@Retry()`) | `delay` (`'200ms'`), `factor` (2), `maxDelay` (`'30s'`), `jitter`: `'full'`, `'equal'` hoặc `'none'` (`'full'`, hoặc `'none'` khi `factor` bằng 1). Hoặc một hàm nhận lần thử thất bại cùng lỗi của nó và trả về một khoảng thời gian. |
| `@Timeout(duration)` | Ngân sách cho mỗi lần thử. Không có tham số thì lấy timeout của preset hoặc của class, rồi đến `defaults.timeout`. |
| `@CircuitBreaker(options)` | `name`, `failureRateThreshold` (50, tính theo phần trăm), `minimumCalls` (10), `slidingWindow` (20 lời gọi gần nhất: `type` là `'count'` hoặc `'time'`, kèm `size`), `openDuration` (`'30s'`), `halfOpenMaxCalls` (1), `recordIf(error)` (mọi lỗi trừ lỗi client). Một chuỗi là tên breaker. Xem [Fail fast với circuit breaker](/reliability/resilience#fail-fast-with-a-circuit-breaker). |
| `@Bulkhead(options)` | `name`, `maxConcurrent` (10), `maxQueue` (0), `queueTimeout` (không giới hạn). Một chuỗi là tên bulkhead. Xem [Giới hạn số lượt export CSV đồng thời bằng bulkhead](/reliability/resilience#cap-concurrent-csv-exports-with-a-bulkhead). |
| `@Fallback(method, options)` | Tên một method trên cùng class, hoặc một hàm, được gọi với lỗi và `ExecutionContext`. `handleIf(error)` (mọi lỗi trừ lỗi client). |
| `@Resilience(preset)` | Áp dụng một preset từ `presets`, theo từng stage. |
| `@Signal()` | `AbortSignal` của lần thử hiện tại. |

`outboundRateLimit` của một preset nhận `limit` (số lời gọi mỗi `interval`), `interval` và `maxWait` (0: reject ngay lập tức).

`ResilienceService` cung cấp `preset(name)`, `create(options, name)`, `circuitBreaker(name)`, `bulkhead(name)`, `circuitBreakers()` và `bulkheads()`. Xem [Dùng cùng các policy bên trong service](/reliability/resilience#use-the-same-policies-inside-services).

##### Event

Mọi event được publish trên `ResilienceEvents.events$` và trên diagnostics channel `nestjs:resilience:<type>`. Mỗi payload có `type`, `policy` và, nếu có, `source` (xem [Theo dõi các lần chuyển trạng thái của breaker](/reliability/resilience#observe-breaker-transitions)).

| Type | Type của payload | Các field khác |
| --- | --- | --- |
| `retry` | `ResilienceRetryEvent` | `attempt` (lần thử đã thất bại, đếm từ 1), `delayMs` (thời gian chờ trước lần tiếp theo), `error` |
| `timeout` | `ResilienceTimeoutEvent` | `timeoutMs` |
| `circuit-open` | `ResilienceCircuitOpenEvent` | `from`, `to` |
| `circuit-half-open` | `ResilienceCircuitHalfOpenEvent` | `from`, `to` |
| `circuit-closed` | `ResilienceCircuitClosedEvent` | `from`, `to` |
| `circuit-rejected` | `ResilienceCircuitRejectedEvent` | `retryAfterMs` |
| `bulkhead-rejected` | `ResilienceBulkheadRejectedEvent` | `reason` (`'full'` hoặc `'queue-timeout'`), `active`, `queued` |
| `rate-limited` | `ResilienceRateLimitedEvent` | `retryAfterMs` |
| `fallback` | `ResilienceFallbackEvent` | `error` |

Trạng thái của một breaker (`from` và `to`) là `'closed'`, `'open'` hoặc `'half-open'`. `ResilienceEvent` là union của mọi type payload.

##### Lỗi

Mọi lỗi đều kế thừa `ResilienceError`, có một `code` và tên `policy`.

| Lỗi | Code | HTTP | Message gửi tới client | Field |
| --- | --- | --- | --- | --- |
| `ResilienceTimeoutError` | `TIMEOUT` | 504 | The operation timed out | `timeoutMs` |
| `CircuitOpenError` | `CIRCUIT_OPEN` | 503, kèm `Retry-After` | Service temporarily unavailable | `retryAfterMs` |
| `BulkheadFullError` | `BULKHEAD_FULL` | 503 | Server is at capacity | `reason` |
| `OutboundRateLimitError` | `RATE_LIMITED` | 503, kèm `Retry-After` | Rate limit of a dependency exceeded | `retryAfterMs` |

Trên microservice và WebSocket handler, lỗi là một `RpcException` hoặc `WsException` có payload gồm `status`, `code`, `statusCode`, `message` và, với những lần reject biết được giá trị này, `retryAfter` tính bằng giây. Trên GraphQL, lỗi của field có `code`, `httpStatus` và `retryAfter` trong `extensions` (xem [Các transport khác](/reliability/resilience#other-transports)).
