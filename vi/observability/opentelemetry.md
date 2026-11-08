### OpenTelemetry

[OpenTelemetry](https://opentelemetry.io/ 'OpenTelemetry') là chuẩn trung lập (không phụ thuộc vendor) cho trace, metric và log. Bạn instrument ứng dụng một lần, gửi dữ liệu tới bất kỳ backend tương thích nào - Jaeger, Grafana Tempo, hoặc một trong rất nhiều vendor chấp nhận giao thức OpenTelemetry (OTLP) - và sau này đổi backend mà không phải động vào code ứng dụng.

Với các service Nest trong hệ thống của bạn, dù đó là toàn bộ backend hay chỉ một phần, bạn không phải chọn giữa nó và [NestJS Observe](/observability/overview): Observe hoạt động độc lập, hoặc chạy song song với OpenTelemetry mà bạn đang có, và các service viết bằng ngôn ngữ khác dùng chung trace với nó thông qua OpenTelemetry. Trang này cho thấy mỗi công cụ ghi lại những gì cho một ứng dụng Nest, cách [chạy cả hai cùng nhau](#running-beside-opentelemetry), và cách [thiết lập OpenTelemetry](#zero-code-setup) trong một ứng dụng.

#### NestJS Observe bổ sung những gì <a id="what-nestjs-observe-adds"></a>

OpenTelemetry instrument một ứng dụng Node.js từ bên ngoài: nó patch HTTP server, router và database driver khi chúng được load. Nó không có cách nào nhìn thấy cấu trúc mà Nest dựng lên ở giữa, nên một trace được thể hiện bằng ngôn ngữ của các library. Một `POST /orders` chậm trong backend OpenTelemetry trông đại khái như thế này trên NestJS 11 (trên NestJS 12, hai span của Nest cũng không có):

```bash
POST /orders                          1,812 ms
  OrdersController.create             1,806 ms
    create                            1,806 ms
      pg.query SELECT customers          11 ms
      POST api.stripe.com             1,747 ms
```

NestJS Observe instrument framework từ bên trong. Nest giao cho nó mọi provider mà Nest tạo ra, thông qua tùy chọn `instrument` của `NestFactory.create()`, nên mọi lời gọi method trên controller, service, repository, guard, interceptor hay pipe đều trở thành một span được đặt tên đúng như cách bạn đặt tên chúng. Cùng request đó trong Observe:

```bash
POST /orders                          1,812 ms
  AuthGuard.canActivate                   3 ms
  OrdersController.create             1,806 ms   self 1 ms
    OrdersService.create              1,805 ms   self 6 ms
      CustomersService.findById          12 ms
        SELECT customers                 11 ms
      PricingService.quote               38 ms
      PaymentsService.charge          1,749 ms
        POST api.stripe.com           1,747 ms
```

Không ai viết span cho `PricingService.quote`, và cũng không ai phải đoán trước rằng nó có thể quan trọng. Vì cây span đầy đủ, Observe có thể tính được thời gian mỗi method tiêu tốn cho riêng nó (self time) thay vì để bạn phỏng đoán. Với OpenTelemetry, muốn có cùng cây span đó nghĩa là phải tự thêm span cho từng method bạn quan tâm - code phải viết ra, phải giữ cập nhật, và chỉ bao phủ được những gì ai đó đã nghi ngờ từ trước (xem [Tự thêm span](#adding-your-own-spans)).

Sự khác biệt còn tiếp tục ra ngoài phạm vi request:

- **Không có gì phải vận hành.** Một pipeline OpenTelemetry gồm một SDK, một exporter, thường là một collector, và một backend để lưu trữ, truy vấn và cảnh báo trên dữ liệu. Observe chỉ là một lệnh, `npx @nestjs/observe link`, lệnh này cài SDK, nối nó vào ứng dụng của bạn, và ghi API key vào `.env`. Không có collector và không có backend nào phải vận hành.
- **Các building block của Nest được ghi lại đúng bản chất của chúng.** Queue consumer, handler `@Cron()`, GraphQL resolver, microservice handler và WebSocket gateway đều được ghi lại thành loại operation riêng, và một job BullMQ hoặc Bull dùng chung trace với request đã đưa nó vào queue.
- **Luôn theo kịp framework.** Observe được team Nest xây dựng và bảo trì song song với chính Nest. Ngược lại, instrumentation Nest của OpenTelemetry hiện chưa hỗ trợ NestJS 12 (xem [Những gì được ghi lại cho Nest](#what-gets-recorded-for-nest)).
- **Không chỉ có trace.** Error monitoring kèm ngữ cảnh mã nguồn, thời gian chờ trong queue và retry, phân tích thời gian theo từng class, profiling runtime, và release đều đi kèm cùng một SDK, trên mọi gói, kể cả gói miễn phí.

OpenTelemetry bao phủ những phần mà Observe cố ý không làm:

- Observe chỉ instrument NestJS trên Node.js. Các service viết bằng ngôn ngữ khác dùng chung trace với nó thông qua OpenTelemetry: với [tùy chọn `openTelemetry`](#running-beside-opentelemetry), một service Nest tham gia vào các W3C trace mà chúng truyền qua header `traceparent`, và với [OTLP export](#exporting-spans-over-otlp) các span của nó sẽ nằm trong backend chứa span của các service kia. Không có tùy chọn này, các service được liên kết với nhau qua header `x-request-id` (xem [Distributed tracing](/observability/distributed-tracing)).
- Observe là một dịch vụ hosted, và nó không nhận OTLP: span từ một OpenTelemetry SDK không xuất hiện trong Observe. Nó có thể export span của chính nó sang backend OpenTelemetry của bạn qua OTLP, song song với những gì nó gửi tới Observe (xem [Export span qua OTLP](#exporting-spans-over-otlp)).
- Instrumentation library của OpenTelemetry ghi lại một client ở bất cứ đâu nó được gọi. Observe instrument database driver và HTTP client theo cách đó, còn các client khác thì theo dạng provider: một Redis hay Kafka client được đăng ký làm provider, như hầu như luôn thấy trong ứng dụng Nest, sẽ có một span cho mỗi lời gọi, nhưng một client được tạo bên ngoài dependency injection sẽ không được ghi lại.

Vì vậy hai công cụ bổ sung cho nhau. OpenTelemetry là nền tảng khi yêu cầu là trung lập với vendor, giữ telemetry trên hạ tầng của riêng bạn, hoặc gom span của mọi service vào một backend. NestJS Observe cho các service Nest của bạn góc nhìn ở cấp framework: độc lập, hoặc [song song với OpenTelemetry](#running-beside-opentelemetry), trong cùng trace với phần còn lại của hệ thống.

Để đọc toàn bộ lập luận, xem [NestJS and OpenTelemetry: why we instrument the framework itself](https://dev.to/nestjs/nestjs-and-opentelemetry-why-we-instrument-the-framework-instead-50i6).

#### Chạy song song với OpenTelemetry <a id="running-beside-opentelemetry"></a>

NestJS Observe có thể bao phủ các service Nest trong một hệ thống mà phần còn lại chạy OpenTelemetry, và nó có thể chạy trong một ứng dụng Nest bên cạnh OpenTelemetry SDK. Với cả hai trường hợp, hãy bật tùy chọn `openTelemetry`:

```typescript
ObserveModule.forRoot({
  // ...
  openTelemetry: true,
});
```

Khi bật tùy chọn này:

- **Một request nằm trong W3C trace giữ nguyên id của trace đó.** Khi một request đến kèm header `traceparent` - từ một service được instrument bằng OpenTelemetry, ở bất kỳ ngôn ngữ nào, hoặc từ một service mesh hay load balancer có trace - Observe báo cáo nó dưới trace id đó, nên nó có cùng id với phần còn lại của trace trong backend OpenTelemetry của bạn. Một header `x-request-id` chỉ được giữ lại khi nó chỉ cùng một trace, đó là những gì một service khác chạy Observe gửi đi. Một header không liên quan, chẳng hạn id mà Envoy và Istio gắn vào mọi request, sẽ nhường chỗ.
- **Các lời gọi ra khỏi service mang trace đi tiếp.** Mỗi lời gọi ra ngoài gửi một `traceparent` bên cạnh `x-request-id`, với span của chính lời gọi đó làm span cha, và truyền tiếp `tracestate` cùng quyết định lấy mẫu của bên gọi, nên các span của service tiếp theo sẽ lồng dưới lời gọi đó. Điều này áp dụng cho `fetch` và `undici` trên mọi phiên bản Node.js được hỗ trợ, và các client xây trên `node:http` trên Node.js 22.12 trở lên.
- **Một OpenTelemetry SDK trong cùng process sẽ quyết định trace.** Observe báo cáo mỗi request dưới trace id của span mà SDK đã mở cho nó, kể cả một request khởi tạo trace, và để SDK lo `traceparent` trên các lời gọi ra ngoài. Khi đó một request có cùng một trace id trên cả hai công cụ, và mỗi lời gọi mang đúng một `traceparent`. SDK vẫn tiếp tục ghi lại span của nó, còn Observe thêm các span ở cấp provider. Nếu SDK truyền B3 thay vì W3C Trace Context, Observe vẫn theo trace của nó như thường, và thêm một `traceparent` trong trace đó bên cạnh các header B3.
- **Queue job và message microservice vẫn nằm trong trace của request trên cả hai công cụ.** Từ `@nestjs/observe` 0.3.23, một job BullMQ hoặc Bull được thêm vào trong lúc xử lý request, và một message gửi qua một client đăng ký bằng `ClientsModule` trên một transport có mang trace id (TCP và Redis trên `@nestjs/microservices` 12.0.4 trở lên; NATS, Kafka, RabbitMQ, MQTT 5 và gRPC trên 12.3.3 trở lên), sẽ mang W3C trace context của request bên cạnh trace id của nó. Một consumer được instrument bằng OpenTelemetry, ở bất kỳ ngôn ngữ nào, sẽ tiếp tục trace từ đó. Trong một service Nest chạy OpenTelemetry SDK, Observe giao context cho SDK, vốn không có instrumentation cho BullMQ hay cho các transport TCP và Redis của Nest: các span của SDK trong job hoặc handler, và `traceparent` trên các lời gọi mà chúng thực hiện, thuộc về trace của request, giống như job và handler trong Observe. Ở những nơi instrumentation có mang trace - add-on [`bullmq-otel`](https://www.npmjs.com/package/bullmq-otel) của chính BullMQ, hoặc instrumentation gRPC của SDK - các span của job hoặc handler sẽ lồng dưới span mà instrumentation đó mở cho chúng (với `bullmq-otel`, từ `@nestjs/observe` 0.3.24).

Trace id được dùng chung. Khi bật [OTLP export](#exporting-spans-over-otlp), các span của service Nest cũng vậy: backend OpenTelemetry của bạn hiển thị toàn bộ trace, còn Observe hiển thị phần của service Nest. Không bật nó, backend hiển thị phần của các service khác trong một trace, còn Observe hiển thị phần của service Nest. Observe ghi W3C trace id dưới dạng UUID, và cả hai dạng đều dùng được trong Observe: `4bf92f3577b34da6a3ce929d0e0e4736` từ Jaeger hoặc Tempo tìm ra cùng trace với `4bf92f35-77b3-4da6-a3ce-929d0e0e4736`.

Không bật tùy chọn này, Observe chỉ đọc và gửi `x-request-id`, và không động tới bất kỳ OpenTelemetry SDK nào trong process. Job và message vẫn nằm trong trace trên Observe: một job BullMQ hoặc Bull được thêm vào trong lúc xử lý request sẽ chạy dưới trace id của request đó, dù worker của nó chạy trong cùng process hay trong một service khác, và một message gửi qua một transport microservice tự mang trace id cũng vậy ([Distributed tracing](/observability/distributed-tracing) cho biết những transport nào làm được, từ phiên bản nào).

> info **Gợi ý** Tùy chọn này hoạt động song song với việc báo cáo lên NestJS Observe. Từ `@nestjs/observe` 0.3.24, nó được bật ngay từ lúc ứng dụng khởi động, nên các request đầu tiên của một instance mới vẫn nằm trong các trace xung quanh nó; trước 0.3.24, nó được bật khi collector chấp nhận batch đầu tiên. Nó vẫn bật trong lúc collector gặp sự cố hoặc bị rate limit, nên một sự cố ở phía Observe không làm đứt các trace chạy qua những service khác của bạn. Nó chỉ tạm dừng, kèm một dòng log, khi collector từ chối credential của ứng dụng hoặc worker của SDK bị down. Các request được xử lý trong khoảng đó được trace như khi tắt tùy chọn. Với `enabled: false`, hoặc khi không có credential, nó không bao giờ được bật.

> warning **Cảnh báo** NestJS Observe và OpenTelemetry SDK đều hook vào database driver. Sự kết hợp này đã được test với `pg`; hãy thử với các driver bạn dùng trong môi trường staging trước khi lên production.

#### Export span qua OTLP <a id="exporting-spans-over-otlp"></a>

Từ `@nestjs/observe` 0.3.23, khi bật tùy chọn `openTelemetry`, Observe cũng có thể export các span mà nó ghi lại sang backend OpenTelemetry của bạn qua OTLP/HTTP - một OpenTelemetry Collector, Jaeger, Grafana Tempo, hoặc bất kỳ vendor nào chấp nhận OTLP. Khi đó phần của service Nest trong một trace, chi tiết tới tận các method của provider, sẽ nằm trong cùng waterfall với các service xung quanh nó. Trỏ tùy chọn `otlp` tới endpoint OTLP/HTTP của backend:

```typescript
ObserveModule.forRoot({
  // ...
  openTelemetry: true,
  otlp: {
    endpoint: 'http://localhost:4318',
  },
});
```

`otlp: true` sẽ đọc endpoint, header, protocol và tên service từ các biến chuẩn `OTEL_EXPORTER_OTLP_*`, `OTEL_SERVICE_NAME` và `OTEL_RESOURCE_ATTRIBUTES`; bản thân các biến này không bao giờ tự bật export. Encoding mặc định là `http/protobuf`, và `protocol: 'http/json'` chuyển sang JSON. gRPC không được hỗ trợ, nên hãy trỏ endpoint tới cổng HTTP của backend, theo quy ước là 4318.

Mỗi request trở thành một server span, nằm dưới span của bên gọi khi nó đến trong một trace, và mỗi queue job trở thành một consumer span. Các span controller, provider và span thủ công bên dưới trở thành internal span, còn database query và lời gọi ra ngoài trở thành client span; span của một lời gọi ra ngoài là span cha của những gì service tiếp theo export. Lỗi được ghi lại dưới dạng status của span và một event `exception`, được che thông tin nhạy cảm giống như khi gửi cho Observe. Một request mà bên gọi đã loại trace của nó khỏi mẫu sẽ không được export.

Export chạy song song với việc báo cáo lên NestJS Observe, không bao giờ thay thế nó, và mọi gói đều có:

- **Gói trả phí** export mọi trace mà SDK ghi lại, bất kể sau đó Observe giữ lại bao nhiêu trong bản sao của nó.
- **Gói Free** export những gì Observe giữ lại. Khi các ứng dụng của bạn gửi 30.000 event trong một ngày UTC, hoặc đã dùng hết hạn mức của tháng, phần lớn waterfall bị tạm dừng, và các request cùng job đằng sau chúng được export mà không kèm các span bên dưới. Lỗi server, job thất bại và bất cứ thứ gì kéo dài hơn 1 giây vẫn giữ trace đầy đủ. Khi không kết nối được tới collector, không thể biết Observe giữ lại những gì, nên export của gói Free sẽ tạm dừng sau vài phút kể từ khi sự cố xảy ra và tiếp tục với batch tiếp theo mà collector chấp nhận.

> info **Gợi ý** Export bắt đầu với batch đầu tiên mà collector chấp nhận, phản hồi của nó cho biết gói của ứng dụng bao gồm những gì, và log sẽ báo khi export được bật. Nó tạm dừng bất cứ khi nào tùy chọn `openTelemetry` tạm dừng. Không có tùy chọn `openTelemetry`, hoặc không có credential, sẽ không có gì được export, và SDK sẽ nói lý do lúc khởi động.

#### Thiết lập không cần code <a id="zero-code-setup"></a>

> info **Gợi ý** Phần lớn tài liệu Node.js của OpenTelemetry giả định ứng dụng đã biên dịch chạy dưới dạng CommonJS. Các ứng dụng được tạo bằng `nest new` trên Nest 12 là ES module, cần thêm một flag loader. Cả hai biến thể đều được trình bày bên dưới. Trên Nest 12, một bản build CommonJS cũng cần flag đó, vì các package `@nestjs/*` là ES module và tự import Express. Không có nó, Express không được instrument và HTTP span được đặt tên mà không có route.

Cách nhanh nhất để lấy trace ra khỏi một ứng dụng Nest là zero-code instrumentation của OpenTelemetry. Cài đặt API và gói auto-instrumentations:

```bash
$ npm i --save @opentelemetry/api @opentelemetry/auto-instrumentations-node
```

Instrumentation phải được load trước Nest và các library mà nó patch, nên nó được đặt trên dòng lệnh `node` thay vì trong `main.ts`. Với bản build CommonJS:

```bash
$ OTEL_SERVICE_NAME=orders-api \
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  node --require @opentelemetry/auto-instrumentations-node/register dist/main.js
```

Với bản build ES module, cần thêm loader hook của OpenTelemetry:

```bash
$ OTEL_SERVICE_NAME=orders-api \
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  node --experimental-loader=@opentelemetry/instrumentation/hook.mjs \
  --import @opentelemetry/auto-instrumentations-node/register dist/main.js
```

Nếu platform tự khởi động process cho bạn và bạn không thể thay đổi lệnh, hãy đặt các flag tương tự vào biến môi trường `NODE_OPTIONS`.

Span được gửi qua OTLP tới endpoint mà bạn cấu hình. Để xem chúng ở local, Jaeger chạy trong một container duy nhất và nhận OTLP trên cổng 4318:

```bash
$ docker run --rm -p 16686:16686 -p 4318:4318 jaegertracing/jaeger
```

Mở `http://localhost:16686`, gửi một request tới ứng dụng của bạn, và trace sẽ xuất hiện dưới tên service mà bạn đã đặt.

#### Cấu hình SDK trong code <a id="configuring-the-sdk-in-code"></a>

Để tự chọn exporter, sampler hoặc các instrumentation, hãy khởi động SDK từ một file của riêng bạn thay vì entry point `register`:

```bash
$ npm i --save @opentelemetry/api @opentelemetry/sdk-node @opentelemetry/auto-instrumentations-node @opentelemetry/exporter-trace-otlp-http
```

```typescript
@@filename(instrumentation)
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';

export const otelSdk = new NodeSDK({
  serviceName: 'orders-api',
  traceExporter: new OTLPTraceExporter(),
  instrumentations: [getNodeAutoInstrumentations()],
});

otelSdk.start();
```

`OTLPTraceExporter` đọc endpoint từ `OTEL_EXPORTER_OTLP_ENDPOINT` và mặc định là `http://localhost:4318`. Load file này trước mọi thứ khác, giống như với entry point zero-code:

```bash
# CommonJS
$ node --require ./dist/instrumentation.js dist/main.js

# ES modules
$ node --experimental-loader=@opentelemetry/instrumentation/hook.mjs \
  --import ./dist/instrumentation.js dist/main.js
```

Trong bản build CommonJS, bạn có thể import file này ngay dòng đầu tiên của `main.ts`, trước `@nestjs/core` và `AppModule` của bạn. Trong bản build ES module, và với Express trên Nest 12, như vậy là chưa đủ, vì loader hook phải được đăng ký trên dòng lệnh.

SDK export span theo batch. Để gửi batch cuối cùng khi ứng dụng dừng, hãy gọi `otelSdk.shutdown()` sau khi Nest đã shutdown xong, ví dụ từ một hook `onApplicationShutdown()` với [shutdown hook](/fundamentals/lifecycle-events#application-shutdown) được bật.

#### Những gì được ghi lại cho Nest <a id="what-gets-recorded-for-nest"></a>

Gói auto-instrumentations ghi lại các HTTP request vào và ra (kể cả `fetch`), Express, và các database driver phổ biến như `pg`, `mysql2`, `mongodb` và Mongoose. Các ORM xây trên những driver đó, như TypeORM, MikroORM và Drizzle, hiện ra thông qua các query mà chúng chạy.

Bản thân Nest được bao phủ bởi `@opentelemetry/instrumentation-nestjs-core`, một phần của gói này. Nó phát ra ba loại span:

| Tên span                        | Type              | Bao phủ gì                                     |
| ------------------------------- | ----------------- | ---------------------------------------------- |
| `Create Nest App`               | `app_creation`    | Lời gọi `NestFactory.create()` lúc khởi động   |
| `<ControllerName>.<memberName>` | `request_context` | Toàn bộ request, theo góc nhìn của Nest        |
| `<memberName>`                  | `handler`         | Method của controller đã xử lý request         |

> warning **Cảnh báo** Tại thời điểm viết bài, `@opentelemetry/instrumentation-nestjs-core` hỗ trợ các phiên bản `@nestjs/core` dưới 12. Trên NestJS 12, ba span ở trên không được ghi lại, và một trace chỉ chứa các span HTTP và database. Hãy kiểm tra các phiên bản được hỗ trợ của package cho bản release mà bạn cài.

Các span dừng lại ở controller. Các provider mà nó gọi - service, repository, và các guard, interceptor, pipe xung quanh nó - không được trace tự động, nên thời gian tiêu tốn trong code của chính bạn hiện ra thành một span không thể chia nhỏ. Trên Fastify adapter, các span ở cấp route đến từ `@fastify/otel`, do team Fastify bảo trì, vốn không nằm trong gói auto-instrumentations.

#### Tự thêm span <a id="adding-your-own-spans"></a>

Để nhìn vào bên trong các provider, hãy tạo span bằng OpenTelemetry API. `startActiveSpan()` biến span mới thành span cha của mọi thứ chạy bên trong callback, kể cả các span database và HTTP:

```typescript
@@filename(pricing.service)
import { Injectable } from '@nestjs/common';
import { SpanStatusCode, trace } from '@opentelemetry/api';

const tracer = trace.getTracer('orders-api');

@Injectable()
export class PricingService {
  async quote(cart: Cart) {
    return tracer.startActiveSpan('PricingService.quote', async (span) => {
      try {
        span.setAttribute('cart.items', cart.items.length);
        return await this.calculate(cart);
      } catch (error) {
        span.recordException(error as Error);
        span.setStatus({ code: SpanStatusCode.ERROR });
        throw error;
      } finally {
        span.end();
      }
    });
  }
}
```

Mọi span bạn khởi tạo đều phải được kết thúc, kể cả khi công việc thất bại, đó là lý do có khối `finally`. Package API có thể import an toàn ngay cả khi không có SDK nào đang chạy: khi đó, các lời gọi không làm gì cả.

Đây chính là phần việc mà NestJS Observe làm giúp bạn: khi đã cài SDK của nó, mọi method của provider đều đã là một span, và API thủ công chỉ cần thiết cho code không phải là method của provider.
