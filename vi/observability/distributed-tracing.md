### Distributed tracing

Một **trace** là tất cả những gì các ứng dụng của bạn đã ghi lại dưới cùng một trace id: request hoặc job đã khởi tạo nó, và mọi span bên dưới. Trong phạm vi một service, việc này diễn ra tự động. SDK sinh ra một trace id khi công việc bắt đầu, và mọi span bên dưới, kể cả những span bạn tự thêm bằng [`TracerService`](/observability/manual-instrumentation), đều kế thừa nó.

Còn giữa các service với nhau thì tùy vào kênh giao tiếp. Lời gọi HTTP và queue job tự mang theo trace id, các transport microservice có sẵn cũng vậy nếu `@nestjs/microservices` đủ mới (12.0.4 cho TCP và Redis, 12.3.3 cho NATS, Kafka, RabbitMQ, MQTT 5 và gRPC). Với các phiên bản cũ hơn, trace id cần được chuyển tiếp thủ công. Một hành động của người dùng chạm tới nhiều service (một API call tỏa ra một service gRPC, hoặc một message gửi sang ứng dụng khác qua một transport microservice) chỉ hiện ra là **một trace** trên dashboard nếu mọi service liên quan đều dùng chung trace id. Nếu không, mỗi service tự tạo trace id riêng qua `traceIdGenerator`, và hành động đó hiện ra thành nhiều trace rời rạc, mỗi service một trace.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/service-flow.webp" alt="Liên kết trace giữa các service" /></figure>

Khi cần chuyển tiếp, đó là việc của code ứng dụng chứ không phải một thiết lập trên dashboard, và pattern lúc nào cũng giống nhau: bên gọi đặt trace id hiện tại của nó lên bất kỳ kênh nào mà giao thức có, và `traceIdGenerator` của bên nhận đọc lại nó. Trang này hướng dẫn cách làm cho từng transport.

#### Đọc trace id hiện tại <a id="reading-the-current-trace-id"></a>

Để chuyển tiếp trace id xuống phía sau, trước tiên một service cần đọc trace id mà nó đang chạy dưới đó. `TracerService.currentTraceId()` trả về giá trị này:

```typescript
@@filename(orders.service)
import { Injectable } from '@nestjs/common';
import { TracerService } from '@nestjs/observe';

@Injectable()
export class OrdersService {
  constructor(private readonly tracerService: TracerService) {}

  async report(orderId: string) {
    const traceId = this.tracerService.currentTraceId();
    // ...forward traceId to the next service
  }
}
```

Nó đọc từ cùng context store với `getAttribute()`/`setAttribute()`, nhưng khác với hai method đó, nó không throw khi ở ngoài một context đang được trace. Thay vào đó nó trả về `null`, nên code chuyển tiếp trace id từ các hook khởi động hoặc các đường code khác không được trace sẽ không cần `try`/`catch`. Nếu code của bạn có thể chạy ngoài một trace, hãy kiểm tra `null` trước khi đặt header.

#### HTTP sang HTTP <a id="http-to-http"></a>

Việc truyền trace qua HTTP diễn ra tự động theo cả hai chiều. Ở chiều vào, `traceIdGenerator` mặc định dùng header `x-request-id` nếu nó đúng định dạng, còn không thì tạo một UUID có thứ tự theo thời gian (v7). Ở chiều ra, SDK thêm trace id hiện tại dưới dạng `x-request-id` vào các request gửi đi chưa có header này, nên một lời gọi từ service được instrument này sang service được instrument khác sẽ rơi vào cùng một trace mà không cần viết code ứng dụng nào.

Việc truyền ở chiều ra bao gồm `fetch` và `undici`, kể cả [HTTP client](/application/http-client), trên mọi phiên bản Node được hỗ trợ, và các client xây trên `node:http` (axios, got, `@nestjs/axios`) trên Node 22.12 trở lên, bản phát hành đầu tiên cho phép thêm header sau khi đối tượng request đã được tạo. Để giới hạn những host nhận header này, hoặc tắt nó đi, xem [`outgoing.http.propagateTraceId`](/observability/sdk#database-queries-and-outbound-http).

Trên phiên bản Node cũ hơn với một client dựa trên axios, hãy đăng ký một request interceptor một lần để tự chuyển tiếp id:

```typescript
@@filename(orders.module)
@Module({
  imports: [HttpModule],
})
export class OrdersModule implements OnModuleInit {
  constructor(
    private readonly httpService: HttpService,
    private readonly tracerService: TracerService,
  ) {}

  onModuleInit() {
    this.httpService.axiosRef.interceptors.request.use((config) => {
      config.headers['x-request-id'] = this.tracerService.currentTraceId();
      return config;
    });
  }
}
```

> info **Gợi ý** Nhiều reverse proxy và load balancer (nginx, Envoy, AWS ALB) có thể đặt `x-request-id` cho mọi request đi vào. Khi đó, trace id trên dashboard của bạn khớp với request id trong access log của proxy. Khi bật tùy chọn [`openTelemetry`](/observability/opentelemetry#running-beside-opentelemetry), một W3C `traceparent` sẽ được ưu tiên hơn một `x-request-id` trỏ tới trace khác.

#### OpenTelemetry và W3C Trace Context <a id="opentelemetry-and-w3c-trace-context"></a>

Các service được instrument bằng OpenTelemetry truyền trace qua header W3C `traceparent` thay vì `x-request-id`. Khi bật tùy chọn `openTelemetry`, SDK đọc `traceparent` ở chiều vào, và trace id mà nó chỉ định trở thành trace id của request. Ở chiều ra, nó gửi `traceparent` bên cạnh `x-request-id`. Nhờ đó một service Nest sẽ tham gia vào các trace mà những service xung quanh dùng chung, bất kể chúng được viết bằng ngôn ngữ nào. Xem [Chạy song song với OpenTelemetry](/observability/opentelemetry#running-beside-opentelemetry).

#### gRPC

gRPC không có header, chỉ có metadata. Trên `@nestjs/microservices` 12.3.3 trở lên, trace id tự đi theo metadata: SDK thêm trace id hiện tại dưới dạng metadata `x-request-id` vào mọi lời gọi thực hiện qua một `ClientGrpc` được đăng ký làm provider (ví dụ với `ClientsModule`), và `traceIdGenerator` mặc định của service gRPC sẽ dùng nó, nên không cần code ứng dụng nào. Metadata bạn tự truyền vào lời gọi sẽ được ưu tiên: một `x-request-id` trong đó là cái mà service sẽ dùng. Khi bật tùy chọn [`openTelemetry`](/observability/opentelemetry#running-beside-opentelemetry), metadata cũng mang theo một W3C `traceparent`, nên một gRPC server được instrument bằng OpenTelemetry, ở bất kỳ ngôn ngữ nào, sẽ tiếp tục trace đó.

Trên các phiên bản cũ hơn, bên gọi gắn trace id dưới dạng metadata, và service gRPC override `traceIdGenerator` để đọc lại nó, vì ở các phiên bản đó generator mặc định không đọc metadata của gRPC:

```typescript
@@filename(caller)
import { Metadata } from '@grpc/grpc-js';

const metadata = new Metadata();
const traceId = this.tracerService.currentTraceId();
if (traceId) {
  metadata.set('x-request-id', traceId);
}
this.heroesService.findOne({ id: 1 }, metadata);
```

```typescript
@@filename(app.module)
import { randomUUID } from 'node:crypto';

// gRPC service - passed to createObserveModule(), not forRoot()
export const { ObserveModule, ObserveInstrument } = createObserveModule({
  traceIdGenerator: (call: any) => {
    const inbound = call.metadata?.get?.('x-request-id')?.[0];
    return typeof inbound === 'string' && inbound.length > 0
      ? inbound
      : randomUUID(); // no id was propagated - this call started its own trace
  },
});
```

Xem chương [gRPC](/microservices/grpc) để biết cách đọc và ghi metadata ở cả hai phía của một lời gọi.

#### TCP, Redis, NATS và các transport microservice khác <a id="tcp-redis-nats-and-other-microservice-transports"></a>

Mọi transport microservice có sẵn đều tự mang theo trace id, khi cả hai service chạy `@nestjs/microservices` đủ mới, cùng với `@nestjs/observe` 0.3.0 trở lên:

| Transport  | Từ `@nestjs/microservices`                 | Trace id được truyền                 |
| ---------- | ------------------------------------------ | ------------------------------------ |
| TCP, Redis | 12.0.4                                     | bên trong packet                     |
| NATS       | 12.3.3                                     | dưới dạng message header             |
| Kafka      | 12.3.3                                     | dưới dạng record header              |
| RabbitMQ   | 12.3.3                                     | trong thuộc tính `headers` của message |
| MQTT       | 12.3.3, qua MQTT 5 (`protocolVersion: 5`)  | dưới dạng user property              |
| gRPC       | 12.3.3                                     | dưới dạng call metadata (xem [gRPC](#grpc)) |

SDK gắn trace id hiện tại, dưới dạng `x-request-id`, vào mọi packet được gửi qua một `ClientProxy` đăng ký làm provider (ví dụ với `ClientsModule`), và `traceIdGenerator` mặc định ở phía nhận sẽ dùng nó, nên không cần code ứng dụng nào. Với các transport mang nó dưới dạng header, một header cùng tên do code của bạn tự đặt, trên record builder hoặc trong tùy chọn `headers` hay `userProperties` của client, sẽ được ưu tiên hơn header của SDK. Vì id ở đó chỉ là một header `x-request-id` bình thường, một service không viết bằng Nest cũng có thể đọc nó, hoặc gửi một header như vậy tới service Nest. Khi bật tùy chọn [`openTelemetry`](/observability/opentelemetry#running-beside-opentelemetry), một W3C `traceparent` cũng được truyền kèm theo cách tương tự, nên một service như vậy nếu được instrument bằng OpenTelemetry, ở bất kỳ ngôn ngữ nào, sẽ tiếp tục trace đó.

Trên `@nestjs/microservices` cũ hơn, và qua MQTT 3.1.1, vốn không có user property, trace id không tự được truyền đi, và mỗi service khởi tạo trace riêng. Nếu bạn không thể nâng cấp, hãy chuyển tiếp id trong một header mà transport có hỗ trợ (`NatsRecordBuilder#setHeaders()`, `RmqRecordBuilder#setOptions({{ '{' }} headers {{ '}' }})`, `headers` của một Kafka message), và override `traceIdGenerator` để đọc lại nó từ context mà transport truyền vào:

```typescript
@@filename(app.module)
import { randomUUID } from 'node:crypto';

// receiving service, over NATS
export const { ObserveModule, ObserveInstrument } = createObserveModule({
  traceIdGenerator: (ctx: any) =>
    ctx.getHeaders?.()?.get('x-request-id') || randomUUID(),
});
```

Generator nhận đối tượng context của transport, nên cùng một đoạn code chạy được cho cả message kiểu request-response (`send()`) lẫn kiểu event (`emit()`). Một custom transport sẽ mang id giống như các transport có sẵn khi client của nó gửi `metadata` của packet đi kèm, và context của nó trả về giá trị đó từ một method `getMetadata()`: generator mặc định sẽ dùng `x-request-id` lấy từ đó.

> warning **Cảnh báo** Cùng một `traceIdGenerator` được gọi cho cả HTTP request lẫn RPC context. Trong một [ứng dụng hybrid](/faq/hybrid-application) phục vụ cả HTTP và một transport microservice, hãy viết generator một cách phòng thủ: kiểm tra `headers` trước, sau đó mới fallback sang context của transport.

#### GraphQL

Không cần cấu hình thêm khi GraphQL server nằm sau lớp HTTP của cùng service. Nó tham gia vào trace mà HTTP agent đã mở cho request đó, bản thân trace này có thể đã được truyền qua `x-request-id` như mô tả ở trên. Chỉ những operation không có HTTP trace bao ngoài, chẳng hạn một subscription qua WebSocket thuần, mới cần xử lý riêng, và hiện tại chưa có hook truyền trace nào có sẵn cho trường hợp đó.

#### Queue job (BullMQ và Bull) <a id="queue-jobs-bullmq-and-bull"></a>

Việc truyền trace qua queue diễn ra tự động. Khi một job được thêm vào từ bên trong một operation đang được trace (một request handler, một RPC handler, một job khác), SDK đóng dấu trace id hiện tại vào option của job, và processor nhận job đó sẽ chạy dưới id này thay vì tự tạo id mới. Request và mọi job mà nó đưa vào queue hiển thị thành một trace, không cần viết code ứng dụng nào:

```typescript
@@filename(orders.controller)
@Post()
async create(@Body() dto: CreateOrderDto) {
  const order = await this.ordersService.create(dto);
  // The job inherits this request's trace id
  await this.ordersQueue.add('send-confirmation', { orderId: order.id });
  return order;
}
```

Cơ chế này hoạt động giống nhau với `@nestjs/bullmq` và `@nestjs/bull`, với `add()` và `addBulk()`, và bất kể worker chạy cùng process với producer hay trong một service riêng: id đi qua Redis cùng với job. Một job được retry giữ nguyên id lúc được đưa vào queue, nên mọi lần thử đều nằm trong cùng một trace.

Có hai trường hợp cố ý khởi tạo trace riêng:

- **Repeatable job và các handler của `@nestjs/schedule`.** Một lịch chạy tồn tại lâu hơn operation đã đăng ký nó, nên mỗi lần kích hoạt là một trace riêng, thay vì là một phần của một trace cứ dài mãi ra gắn với request nào đó đã thiết lập lịch.
- **Job được thêm vào bên ngoài mọi operation đang được trace**, ví dụ từ một bootstrap hook hoặc một script thông thường. Không có trace nào để kế thừa.

> info **Gợi ý** Trace id được lưu dưới job option `observeTraceId`. Để gắn một job vào một trace mà SDK không thấy (ví dụ một job được đưa vào queue bởi một producer không phải Nest), hãy tự đặt option đó khi thêm job.

Khi bật tùy chọn [`openTelemetry`](/observability/opentelemetry#running-beside-opentelemetry), từ `@nestjs/observe` 0.3.23, một job cũng mang theo W3C trace context tại thời điểm nó được thêm vào, dưới job option `observeTraceparent`, và processor sẽ chạy trong context đó. Khi đó một OpenTelemetry SDK trong process chạy job sẽ tiếp tục trace của request: các span của job trong backend OpenTelemetry của bạn, và các service mà job gọi tới, nằm cùng trace với request, giống như job nằm cùng trace trong Observe. Với add-on OpenTelemetry riêng của BullMQ, [`bullmq-otel`](https://www.npmjs.com/package/bullmq-otel), trên queue và worker, processor chạy trong consumer span mà add-on mở ra, một span của cùng trace, và từ `@nestjs/observe` 0.3.24 các span của job sẽ lồng dưới nó.

> warning **Cảnh báo** Việc kế thừa trace cho job yêu cầu `@nestjs/observe` 0.3.0 trở lên trên **cả** service thêm job lẫn service xử lý job. Với producer cũ hơn, job không mang id nào và mỗi lần chạy mở một trace riêng, như trước đây.

#### Một trace trông như thế nào trên dashboard <a id="what-a-trace-looks-like-in-the-dashboard"></a>

Khi các service đã thống nhất một trace id, trang chi tiết trace hiển thị mọi execution đã chạy dưới id đó, xuyên suốt các service, request và job, thành một waterfall: độ sâu lồng nhau là thụt lề, thời lượng là độ dài thanh, và vị trí theo chiều ngang là thời điểm span chạy. Khi đọc nó, hãy lưu ý những điểm sau:

- **Self time** là con số quan trọng. Thời lượng của một span trừ đi phần thời gian của các span con chính là thời gian span đó tiêu tốn trong code của chính nó. Xếp hạng theo tổng thời lượng luôn đưa controller lên đầu (nó chứa mọi thứ); xếp hạng theo self time sẽ làm lộ ra lời gọi repository thực sự ngốn thời gian. Mỗi trang execution đều có một bảng span được sắp xếp theo cách này.
- **Các span con chồng lấn được đánh dấu.** Khi tổng thời lượng các span con lớn hơn thời lượng của chính span cha, chúng đã chạy đồng thời (`Promise.all`, một fan-out song song) và dòng đó sẽ ghi chú điều này.
- **Span bị lỗi được đánh dấu**, và trang execution mở đầu bằng một thẻ lỗi cho span đầu tiên đã throw - class, message, stack trace đã được rút gọn với frame throw được đánh dấu, và các dòng mã nguồn xung quanh khi [`sourceContext`](/observability/sdk#error-source-context) được bật.
- **Log nằm trên trục thời gian của trace.** Khi bật `forwardLogs`, mỗi dòng log được đặt tại độ lệch của nó so với thời điểm bắt đầu trace và được gắn nhãn span đang chạy lúc nó được ghi; hover vào một dòng sẽ đánh dấu thời điểm đó trên waterfall.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/traces.webp" alt="Waterfall của trace" /></figure>

Từ bất kỳ execution nào bị lỗi hoặc chậm bất thường, nút **Copy agent prompt** đóng gói toàn bộ trang (context, lỗi, stack trace kèm mã nguồn, các span hàng đầu theo self time, và log) thành một prompt markdown tự đầy đủ cho coding agent. Xem [Dashboard](/observability/dashboard#handing-a-failure-to-a-coding-agent).
