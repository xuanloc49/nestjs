### Resilience

`@nestjs/resilience` bổ sung retry, timeout, circuit breaker, bulkhead và fallback cho controller, resolver, message handler và gateway, dưới dạng decorator.

Sớm hay muộn, mọi ứng dụng gọi sang một hệ thống khác đều sẽ gặp một hệ thống chậm hoặc bị down. Nếu không có kế hoạch, một dependency chậm sẽ giữ chân các request handler của bạn, client phải chờ tới khi timeout của chính chúng kích hoạt, và các lần retry từ mọi tầng lại dồn thêm tải lên chính service đang chật vật.

`@nestjs/resilience` cung cấp những công cụ quen thuộc dưới dạng decorator: **retry**, **timeout**, **circuit breaker**, **bulkhead** và **fallback**. Chúng áp dụng cho các **entrypoint** của ứng dụng, tức là controller, GraphQL resolver, microservice message handler và WebSocket gateway. Với code bên trong service, các thiết lập tương tự có sẵn dưới dạng policy object. Một global interceptor duy nhất áp dụng các decorator, nên chúng hoạt động giống nhau trên mọi transport, và mỗi lỗi sẽ trở thành lỗi gốc của transport đó. Ví dụ qua HTTP, một timeout trả về `504 Gateway Timeout` và một breaker đang mở trả về `503 Service Unavailable` kèm header `Retry-After`.

Trong bài hướng dẫn này, bạn sẽ gia cố API đơn hàng của một cửa hàng online bán thức ăn và đồ dùng cho mèo. Checkout gọi sang đơn vị vận chuyển để lấy báo giá, và API báo giá của đơn vị vận chuyển thì lúc tốt nhất cũng chậm, thỉnh thoảng còn bị down. Khi kết thúc, một đơn vị vận chuyển chậm chỉ làm checkout mất tối đa khoảng ba giây. Khi đã biết đơn vị vận chuyển đang down, checkout sẽ không chờ nó nữa: khách hàng thấy phí vận chuyển đồng giá thay vì một lỗi, và một background job ngừng gọi đơn vị vận chuyển cho tới khi nó hồi phục.

#### Yêu cầu trước

Bài hướng dẫn này giả định có một `OrdersModule` export một `OrdersService`. Service cần các method sau: `findOne(id)` (throw `NotFoundException` với id không tồn tại), `findAll()`, `update(id, changes)` và `exportCsv()`. Đơn hàng trông như thế này:

[[CODE:1]]

Cài đặt package:

[[CODE:2]]

[Retry một POST an toàn](/reliability/resilience#retry-a-post-safely) còn dùng `@nestjs/idempotency` (xem [Idempotency key](/reliability/idempotency)).

#### Đăng ký module

Import `ResilienceModule` vào root module. Cấu hình giá trị mặc định cho các field và một preset có tên, `carrier`, mô tả cách ứng dụng nên đối xử với đơn vị vận chuyển:

[[CODE:3]]

Hai tùy chọn này làm hai việc khác nhau:

- `defaults` điền giá trị cho các field của bất kỳ stage nào mà một decorator hoặc preset bật lên. Bản thân defaults không bao giờ tự bật một stage. Ở đây, một lần retry đầu tiên chờ một khoảng thời gian ngẫu nhiên từ 0 đến 200 ms (`delay`), sau đó tối đa 400 ms, cứ thế nhân đôi mỗi lần cho tới 2 giây (`maxDelay`). Một `@Timeout()` không tham số nghĩa là 5 giây.
- `presets` chứa các tập stage có tên, thường mỗi dependency một preset. Preset `carrier` cho mỗi lần thử 2 giây, thử tối đa 2 lần, và thêm một circuit breaker. Breaker đó được **dùng chung dưới tên `carrier`** bởi mọi route, handler và service dùng preset này. Đơn vị vận chuyển là một dependency, nên nó có một breaker.

Mọi tùy chọn mang giá trị thời gian đều nhận số mili giây hoặc một chuỗi như `'200ms'`, `'2s'` hay `'30s'`.

Module này là global, nên chỉ cần import một lần, trong root module. Nó đăng ký một interceptor cho toàn ứng dụng, interceptor này không làm gì với các handler không có resilience decorator ngoài việc map lỗi. Nó kiểm tra cấu hình lúc bootstrap: một tên preset không tồn tại, một khoảng thời gian hoặc con số không hợp lệ (chẳng hạn `NaN` của một biến môi trường chưa đặt), một fallback method bị thiếu, hoặc một tên breaker được cấu hình theo hai cách khác nhau sẽ làm ứng dụng khởi động thất bại thay vì để tới request đầu tiên mới lỗi. Dùng `ResilienceModule.forRootAsync()` để dựng các tùy chọn từ cấu hình.

#### Đặt ngân sách thời gian cho route báo giá

Bắt đầu với một client cho đơn vị vận chuyển. Mọi method đều nhận một `AbortSignal` và truyền nó cho `fetch()`:

[[CODE:4]]

Service truyền signal đi tiếp. Nó còn có một bảng giá đồng giá và một method đặt vận chuyển, hai thứ này được circuit breaker và lần retry POST dùng ở bên dưới:

[[CODE:5]]

Giờ đến route. `@Resilience('carrier')` áp dụng preset, và `@Signal()` inject `AbortSignal` của lần thử hiện tại:

[[CODE:6]]

Đăng ký `CarrierClient` và `ShippingService` làm provider, và `ShippingController` làm controller, của một `ShippingModule` có import `OrdersModule`.

Checkout không thể chờ lâu, nên `@Timeout('1.5s')` cho route này một ngân sách chặt hơn của preset. Các thiết lập được resolve **theo từng stage**: một decorator trên handler sẽ thắng preset ở stage của chính nó, còn preset vẫn cung cấp retry và breaker. Một `@Timeout()` không tham số sẽ lấy 2 giây của preset, và chỉ fallback về `defaults.timeout` khi không có preset hay `@Timeout()` cấp class nào đặt thời lượng.

Khi một lần thử hết thời gian, ba điều xảy ra:

1. Lần thử bị reject với một `ResilienceTimeoutError`.
2. Signal bị abort với chính lỗi đó. `fetch()` reject và đóng kết nối, nên không có gì tiếp tục chờ một câu trả lời mà không ai đọc. Việc hủy là cộng tác (cooperative): code bỏ qua signal sẽ tiếp tục chạy ngầm, và kết quả của nó bị bỏ đi.
3. Vì `GET` là một method an toàn, retry của preset sẽ thực hiện lần thử thứ hai. Chỉ các pipe, interceptor bên trong và handler được chạy lại. Guard và middleware chỉ chạy một lần mỗi request.

Nếu lần thử thứ hai cũng timeout, client nhận được `504`:

[[CODE:7]]

Timeout áp dụng **cho từng lần thử**, nên một đơn vị vận chuyển bị treo làm route này mất khoảng 3.2 giây: hai lần thử 1.5 giây cộng tối đa 200 ms backoff. Status là 504 thay vì 408 là có chủ ý. Một 408 ngầm khẳng định rằng _client_ đã quá chậm khi gửi request, và một số client cũng như proxy tự động gửi lại khi gặp 408, kể cả với request `POST`.

Lỗi client không phải là thất bại. Một request cho đơn hàng không tồn tại sẽ throw `NotFoundException` trước khi đơn vị vận chuyển được gọi. Nó trả về 404, và không bị retry cũng không được breaker đếm.

> info **Hint** Code không thể nhận signal làm tham số có thể inject `ResilienceContext` và đọc `signal` cùng `attempt` của nó. Nó đọc lần thử hiện tại từ `AsyncLocalStorage`, nên hoạt động trong bất kỳ service nào mà handler gọi tới, trên mọi transport. Một policy object được dùng bên trong lần thử cũng kế thừa signal của nó, nên timeout của route cũng dừng luôn các lần retry của policy đó.

#### Fail fast với circuit breaker

Breaker của preset ghi lại kết quả của mọi lần thử. Breaker `carrier` sẽ mở khi nó đã thấy ít nhất `minimumCalls` (10) lời gọi, và ít nhất `failureRateThreshold` (50%) trong số đó thất bại. Mặc định nó xét 20 lời gọi gần nhất. Mọi lỗi đều được tính là thất bại, kể cả timeout, trừ lỗi client và các lần bị reject bởi policy khác. Lỗi client là một `HttpException` 4xx, hoặc bất kỳ lỗi nào khác có thuộc tính `status` hoặc `statusCode` mang giá trị 4xx. Điều này bao gồm cả `CarrierError`: khi đơn vị vận chuyển trả về `422` cho một request sai định dạng, nó không bị down, nên breaker bỏ qua lỗi đó và retry không lặp lại nó. Ngoại lệ là `408` hoặc `429` từ đơn vị vận chuyển, vì nó có nghĩa là đơn vị vận chuyển đang từ chối bớt tải, nên nó được tính như một `5xx`. Một `HttpException` mang một trong các status đó vẫn là lỗi client: handler throw nó để trả lời chính bên gọi của mình, và điều đó không nói lên gì về đơn vị vận chuyển. Để thay đổi những gì được tính, hãy truyền một hàm `recordIf` trong tùy chọn của breaker.

Trong khi breaker đang **open**, các lời gọi thất bại ngay lập tức và đơn vị vận chuyển hoàn toàn không được gọi. Client nhận `503` kèm header `Retry-After`: số giây cho tới khi breaker cho phép một lời gọi thăm dò đi qua. Retry bọc bên ngoài breaker, nên một lần bị reject không bao giờ được retry.

Sau `openDuration` (30 giây), breaker chuyển sang **half-open**. Nó cho phép một lời gọi thăm dò đi qua (xem `halfOpenMaxCalls`). Nếu lời gọi thăm dò thành công, breaker đóng lại và bắt đầu lại với một cửa sổ trống. Nếu thất bại, breaker mở thêm 30 giây nữa. Breaker không dùng timer cho việc này. Nó kiểm tra trạng thái ở lời gọi tiếp theo.

Một 503 là đúng, nhưng checkout có thể làm tốt hơn. Hãy thêm một fallback trả về báo giá đồng giá trong khi đã biết đơn vị vận chuyển đang down (import `Fallback` và `CircuitOpenError` từ `@nestjs/resilience`):

[[CODE:8]]

`@Fallback()` nhận tên một method trên cùng class, hoặc một hàm. TypeScript kiểm tra rằng class có method với tên đó. Fallback được gọi với lỗi và `ExecutionContext`, và bất cứ thứ gì nó trả về sẽ trở thành response. Đó có thể là một giá trị, một `Promise` hoặc một `Observable`. Fallback là stage ngoài cùng, nên nó cũng thấy các lần reject của breaker.

Mặc định, một fallback thay thế mọi lỗi trừ lỗi client. Tùy chọn `handleIf` thu hẹp phạm vi đó. Giá đồng giá làm cửa hàng lỗ tiền với các kiện hàng nặng, như bao cát vệ sinh, nên ở đây chúng là phương án cuối cùng: chúng chỉ được dùng khi breaker báo đơn vị vận chuyển đang down, còn một câu trả lời chậm đơn lẻ vẫn nhận 504.

> info **Hint** Để xem một breaker từ code của bạn, hãy inject `ResilienceService` và gọi `circuitBreaker('carrier')`. Breaker cung cấp `state` và `stats`, và bạn có thể ép nó mở hoặc đóng bằng `trip()` và `reset()`.

#### Giới hạn số lượt export CSV đồng thời bằng bulkhead

Bộ phận back office tải toàn bộ đơn hàng về dưới dạng file CSV. Việc dựng file đọc mọi đơn hàng và rất nặng cho cả database lẫn CPU. Hai lượt export cùng lúc thì ổn, nhưng hai mươi lượt sẽ làm checkout chậm đi với tất cả mọi người. Một bulkhead giới hạn số lượng chạy cùng lúc:

[[CODE:9]]

Hai lượt export chạy cùng lúc. Tối đa ba lượt nữa chờ tới lượt, mỗi lượt chờ tối đa 10 giây. Request thứ sáu nhận `503` ngay lập tức, và một request đang chờ cũng vậy khi hết 10 giây:

[[CODE:10]]

503 này không có header `Retry-After`, vì không ai biết khi nào một chỗ trống sẽ xuất hiện. Status là 503 thay vì 429 vì 429 đổ lỗi cho tần suất request của client, còn một bulkhead đầy nghĩa là server đã hết công suất với tất cả mọi người.

Một chỗ vẫn bị chiếm cho tới khi handler hoàn tất, hoặc cho tới khi một timeout trên route bỏ cuộc với lần thử đó. Khi đó, một handler bỏ qua signal của nó sẽ tiếp tục chạy ngầm, nằm ngoài số đếm của bulkhead, thêm một lý do để truyền signal cho mọi lời gọi có nhận nó. Một bulkhead không có tên thuộc về handler của nó, và được đăng ký dưới tên của handler. Để đọc mức tải của nó, hãy inject `ResilienceService` và xem `bulkhead('OrdersController.export')`, có các số đếm `active` và `queued`. Đặt `name` cho bulkhead để dùng chung một nhóm chỗ giữa nhiều handler.

#### Retry một POST an toàn

Cho tới giờ, retry chỉ xảy ra với `GET`. Đó là có chủ ý. Trên HTTP, retry chỉ áp dụng cho các method an toàn `GET`, `HEAD` và `OPTIONS`, và trên GraphQL chỉ cho query. Chạy một `POST` hai lần có thể tạo ra hai đơn vận chuyển, và package không thể biết điều đó có vô hại hay không. Vì vậy retry của một preset đơn giản là bị bỏ qua trên `POST`. Một decorator `@Retry()` đặt trực tiếp lên handler `POST` cũng bị bỏ qua, và bootstrap sẽ cảnh báo về điều đó:

[[CODE:11]]

Đặt vận chuyển _thì_ an toàn để lặp lại, vì đơn vị vận chuyển khử trùng lặp các đơn vận chuyển theo `reference`, chính là id đơn hàng. Điều đó còn quan trọng vì một lý do khác: một lần đặt bị timeout có thể vẫn đã thành công ở phía đơn vị vận chuyển, nên dù sao thì retry cũng phải an toàn. Đặt `idempotent: true` trên `@Retry()` là cách bạn khẳng định rằng chạy handler hai lần trong một request là ổn:

[[CODE:12]]

Một `@Retry()` ở cấp handler được merge vào retry của preset, theo từng field. Các field bạn đặt sẽ thắng, phần còn lại lấy từ preset, rồi từ `defaults.retry`. Vì vậy route này giữ 2 lần thử của preset và chỉ thêm `idempotent: true`. Timeout 2 giây và breaker của preset vẫn áp dụng. Chỉ một decorator mới có thể nói `idempotent: true`: một preset không thể tuyên bố mọi handler dùng nó đều an toàn để lặp lại.

`idempotent: true` và `@Idempotent()` giải quyết hai vấn đề khác nhau:

- `idempotent: true` cho phép **server** chạy lại handler trong một request.
- `@Idempotent()` khử trùng lặp các lần retry toàn bộ request từ phía **client**. Khi một client lặp lại một request với cùng header `Idempotency-Key`, nó nhận lại response đã lưu và handler không chạy lại.

Đăng ký `IdempotencyModule` **trước** `ResilienceModule`:

[[CODE:13]]

Cả hai module đều đăng ký một global interceptor, và module nào được import trước sẽ chạy ở ngoài cùng. Với thứ tự này:

- Một lần replay, hoặc một `409` cho một key vẫn đang được xử lý, được trả lời trước khi bất kỳ retry, breaker hay timeout nào chạy. Một lần đặt đã thành công sẽ được replay ngay cả khi breaker đang mở.
- Mọi lần retry của một request diễn ra dưới cùng một key đã được claim.
- Response được lưu là kết quả cuối cùng, sau các lần retry và fallback nếu có.
- Một `503` hoặc `504` là response 5xx, nên key được giải phóng và client có thể thử lại sau với cùng key.

Giải phóng key khi gặp `504` có một vấn đề. Key được giải phóng ngay khi timeout trả lời, nhưng lần chạy bị timeout có thể vẫn đang tiếp diễn, hoặc có thể đã tới được đơn vị vận chuyển, nên một lần retry với cùng key có thể chồng lấn với nó. Đó là lý do side effect phải an toàn để lặp lại ở phía sau, như đơn vị vận chuyển đảm bảo bằng `reference`. Truyền signal đi tiếp, như `createShipment()` làm, sẽ dừng công việc ở local sớm hơn.

#### Dùng cùng các policy bên trong service

Các đơn hàng đang chờ có kèm ước tính phí vận chuyển trong `total`. Cứ 15 phút, một background job lại lấy báo giá mới cho chúng. Job không phải là entrypoint, nên nó dùng một **policy object**, lấy từ `ResilienceService`:

[[CODE:14]]

Thêm `RepricingService` vào providers của `ShippingModule`, và gọi `repricePendingOrders()` từ một scheduled job (xem [Task scheduling](/application/task-scheduling#declarative-cron-jobs)).

`resilience.preset('carrier')` trả về preset dưới dạng một policy. Breaker của nó là **cùng một instance** mà các route dùng, nên job và checkout chia sẻ những gì chúng biết về đơn vị vận chuyển theo cả hai chiều:

- Trong khi breaker đang mở, job nhận `CircuitOpenError` ngay lập tức và dừng lại, thay vì tốn một lần timeout cho mỗi đơn hàng.
- Nếu job là bên đầu tiên phát hiện đơn vị vận chuyển bị lỗi, các lần thất bại của nó sẽ mở breaker, và checkout trả về giá đồng giá mà không phải chờ timeout trước.

Có một vài chi tiết khác so với entrypoint:

- `execute()` truyền cho hàm của bạn `signal` và số thứ tự `attempt` của lần thử. Tùy chọn `source` gắn nhãn cho các event mà lời gọi này phát ra.
- Một policy object không có `GET` hay `POST` để xét, nên retry của preset **luôn luôn** được áp dụng. Chỉ bọc những lời gọi an toàn để lặp lại (một lần lấy báo giá là an toàn).
- `@Timeout('1.5s')` của route thuộc về route. Job nhận 2 giây của preset.
- Hãy tạo policy một lần, ví dụ trong constructor, chứ không phải ở mỗi lời gọi. Với các tùy chọn không phải preset, dùng `resilience.create(options, name)`.

Tại sao không đặt `@Retry()` lên `repricePendingOrders()`? Resilience decorator là metadata mà global interceptor đọc, và interceptor chỉ chạy quanh các entrypoint. Trên một method của provider, decorator sẽ không làm gì cả, nên bootstrap sẽ cảnh báo thay vào đó:

[[CODE:15]]

Đây là một lựa chọn có chủ ý, vì ba lý do:

- Bọc các method tùy ý của provider sẽ bỏ sót các instance request-scoped và transient, vốn được Nest tạo ra sau bootstrap.
- Các lần retry ẩn sâu bên trong service sẽ nhân lên. Một route thử 3 lần, gọi một service thử 3 lần, gọi một SDK thử 3 lần, sẽ gửi tới 27 request tới một dependency vốn đang chật vật.
- Một policy object hiện rõ ở chỗ gọi, nơi bạn thấy được nó làm gì.

> info **Hint** Một entrypoint không có decorator vẫn map các lỗi resilience. Nếu một service throw `CircuitOpenError` bên trong một route bình thường, client nhận `503` kèm `Retry-After`. Đặt `mapErrors: false` trong tùy chọn của module để tắt hành vi này.

#### Các transport khác

Các decorator tương tự hoạt động trên microservice handler. Service kho hàng lấy báo giá qua TCP khi đóng gói lại một đơn hàng:

[[CODE:16]]

Thêm `ShippingHandlers` vào `controllers` của `ShippingModule`.

Một message không có `GET` hay `POST` để biết nó có an toàn để lặp lại hay không, nên trên các handler message, event và WebSocket, chỉ có `@Retry()` đặt trên chính handler mới bật retry. Retry của preset, hoặc một `@Retry()` cấp class không có `idempotent: true`, sẽ không tự áp dụng ở đó, nên việc tái sử dụng preset `carrier` không thể âm thầm chạy lại một handler có side effect. Ở đây `@Retry()` của handler chủ động bật retry, và `attempts: 3` của nó nâng 2 lần thử của preset lên 3. Chỉ dùng nó trên những handler an toàn để chạy hai lần. Lỗi tới bên gọi dưới dạng `RpcException` với payload có cấu trúc:

[[CODE:17]]

Một timeout có `"code": "TIMEOUT"` và `"statusCode": 504`, và không có `retryAfter`. Trong một ứng dụng hybrid, hãy kết nối microservice với `inheritAppConfig: true`, nếu không global interceptor sẽ không tới được các handler của nó (xem [Ứng dụng hybrid](/faq/hybrid-application#sharing-configuration)):

[[CODE:18]]

GraphQL resolver hoạt động theo cách tương tự. Nếu ứng dụng của bạn phục vụ GraphQL, hãy thêm một resolver vào providers của `ShippingModule`:

[[CODE:19]]

Query được retry, còn mutation cần `idempotent: true`, giống như request `POST`. Một lỗi chỉ làm hỏng field của chính nó. Response vẫn có status 200, và lỗi mang code trong `extensions`:

[[CODE:20]]

[[CODE:21]]

Một breaker đang mở báo `"code": "CIRCUIT_OPEN"`, `"httpStatus": 503` và `"retryAfter"` tính bằng giây. Package đặt `httpStatus` thay vì `extensions.http` của Apollo, vì Apollo sẽ áp dụng `extensions.http` cho toàn bộ response, dù chỉ có một field bị lỗi.

#### Theo dõi các lần chuyển trạng thái của breaker

Mọi policy đều phát ra các event có type: `retry`, `timeout`, `circuit-open`, `circuit-half-open`, `circuit-closed`, `circuit-rejected`, `bulkhead-rejected`, `rate-limited` và `fallback`. Mỗi event mang tên `policy`, và `source` của nó nếu có: entrypoint (chẳng hạn `ShippingController.getQuotes`) hoặc nhãn được truyền cho `execute()`. Inject `ResilienceEvents` để nhận chúng: `events$` của nó là một RxJS stream chứa mọi event từ các policy của ứng dụng này. Hãy log những event mà ai đó nên thấy:

[[CODE:22]]

Thêm `ResilienceLogger` vào mảng `providers` của `AppModule`.

Mọi policy cũng publish mỗi event trên một [diagnostics channel](https://nodejs.org/api/diagnostics_channel.html) riêng, chẳng hạn `nestjs:resilience:timeout` hoặc `nestjs:resilience:circuit-open`, kể cả các policy được tạo mà không qua module. Các công cụ metric và tracing có thể subscribe mà không cần phụ thuộc vào package này. `ResilienceTimeoutEvent` là type của các message trên một channel, còn `ResilienceEvent` là union của tất cả:

[[CODE:23]]

[NestJS Observe](/observability/overview#what-it-offers) đã đọc HTTP ra ngoài từ các diagnostics channel của Node (xem [Database query và HTTP ra ngoài](/observability/sdk#database-queries-and-outbound-http)). Nó chưa subscribe vào các channel `nestjs:resilience`. Khi đã làm được, nó có thể gắn các lần retry và timeout vào span của request, vẽ biểu đồ trạng thái breaker theo tên, và cảnh báo khi bulkhead từ chối request, mà không có code nào ở package này phụ thuộc vào package kia.

#### Chạy thử

Khởi động ứng dụng với `CARRIER_URL` trỏ tới một stub đơn vị vận chuyển mà bạn kiểm soát, chẳng hạn một mock server hoặc vài dòng `node:http`. Trong khi đơn vị vận chuyển còn trả lời, checkout nhận báo giá thật:

[[CODE:24]]

Giờ hãy làm stub bị treo. Cùng request đó trả về `504` sau khoảng 3 giây, và stub thấy cả hai request của nó bị hủy:

[[CODE:25]]

Tiếp tục gửi. Mỗi request ghi nhận hai lần thử thất bại. Tới request chậm thứ năm, breaker có 10 lời gọi trong cửa sổ và 9 trong số đó thất bại. Breaker mở, lần thử thứ hai của request bị reject, và fallback trả lời. Ứng dụng log ra:

[[CODE:26]]

Từ giờ, việc đặt vận chuyển thất bại ngay mà không gọi đơn vị vận chuyển:

[[CODE:27]]

Trong khi đó, báo giá trả lời ngay lập tức với giá đồng giá:

[[CODE:28]]

Cho stub trả lời trở lại và chờ 30 giây. Request báo giá tiếp theo là lời gọi thăm dò. Nó thành công, nên breaker đóng lại và checkout lại hiển thị báo giá thật:

[[CODE:29]]

Lặp lại việc đặt vận chuyển với cùng `Idempotency-Key` giờ sẽ tạo đơn vận chuyển và trả về `201`. Lần 503 trước đó đã giải phóng key.

#### Testing

Hành vi resilience rất đáng để test, nhưng không phải bằng cách chờ 30 giây cho một breaker. Hãy thay `CarrierClient` bằng một bản giả, và dùng fake timer của Vitest cho đồng hồ. Chỉ giả lập `setTimeout`, `clearTimeout` và `Date`, để HTTP server và supertest vẫn hoạt động với I/O thật:

[[CODE:30]]

Có vài điểm giúp cách này hoạt động:

- `vi.waitFor()` chờ cho tới khi request thực sự tới được đơn vị vận chuyển. Chỉ khi đó mới có timer để tua tới. Khi bật fake timer, `vi.waitFor()` cũng dịch đồng hồ theo khoảng thời gian polling của nó (50 ms), vẫn nằm gọn trong ngân sách 1.5 giây.
- `vi.advanceTimersByTimeAsync()` kích hoạt các timeout và backoff theo thứ tự, và để các promise ở giữa kịp settle.
- `trip()` mở breaker trực tiếp, nên bạn không phải tạo ra mười lần thất bại để test trạng thái open. Vì breaker so `openDuration` với `Date` ở lời gọi tiếp theo, chỉ cần tua đồng hồ giả về phía trước là đủ để lời gọi đó trở thành lời gọi thăm dò.
- Breaker, bulkhead và giới hạn tần suất gọi ra ngoài thuộc về ứng dụng đã tạo ra chúng, nên mỗi ứng dụng test đều bắt đầu với trạng thái mới.
- Để test với các thiết lập khác, chẳng hạn `openDuration` ngắn hơn, hãy override tùy chọn của module bằng `overrideProvider(RESILIENCE_MODULE_OPTIONS)`.

Xem [End-to-end testing](/fundamentals/testing#end-to-end-testing) để nắm kiến thức testing cơ bản.
