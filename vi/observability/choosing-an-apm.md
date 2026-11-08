### Chọn một APM

Không có APM nào là tốt nhất cho mọi ứng dụng NestJS: lựa chọn đúng phụ thuộc vào việc hệ thống của bạn có bao nhiêu phần là Nest, bạn đang vận hành những gì, và bạn cần nhìn thấy gì ngoài bản thân ứng dụng. Chương này đặt cạnh nhau các công cụ mà mọi người hay tìm tới - [NestJS Observe](/observability/overview), OpenTelemetry, Sentry, Datadog, New Relic và Elastic APM - kèm cách thiết lập mỗi công cụ cần trong một ứng dụng Nest, những gì nó thấy được về Nest khi đã cài xong, và khi nào mỗi công cụ là lựa chọn đúng.

#### Câu trả lời ngắn gọn <a id="the-short-answer"></a>

- **NestJS Observe** cho các service NestJS trong hệ thống của bạn, dù đó là toàn bộ backend hay chỉ một phần: trace dùng đúng tên gọi của bạn (`OrdersService.create`, chứ không phải `express.middleware`) mà không phải vận hành gì, được nối thông qua OpenTelemetry với trace của các service viết bằng ngôn ngữ khác.
- **OpenTelemetry** cho các service không phải Nest, hoặc nếu bạn muốn một chuẩn trung lập duy nhất cho mọi service, kể cả các service Nest.
- **Sentry** nếu mối quan tâm chính là lỗi trên cả frontend web hoặc mobile lẫn backend.
- **Datadog hoặc New Relic** nếu bạn muốn một nền tảng duy nhất cho nhiều ngôn ngữ và hạ tầng thực sự, và có người để vận hành nó.
- **Elastic APM** nếu bạn đã chạy Elastic Stack, hoặc dữ liệu phải nằm trên hạ tầng do bạn kiểm soát.

Chúng không loại trừ nhau: NestJS Observe hoạt động độc lập, hoặc song song với OpenTelemetry hay APM nền tảng mà bạn đang có (xem [Dùng nhiều hơn một](#using-more-than-one)).

#### Mọi APM cần gì từ một ứng dụng Nest <a id="what-every-apm-needs-from-a-nest-application"></a>

Phần lớn APM agent hoạt động bằng cách patch các library khi chúng được load: HTTP server, router, database driver. Vì vậy agent phải khởi động trước khi ứng dụng của bạn import bất kỳ thứ nào trong số đó, mà trong một ứng dụng Nest nghĩa là trước `@nestjs/core` và trước `AppModule` của bạn.

Có hai cách để làm được điều đó: một flag preload trên lệnh `node` (`--require` cho CommonJS, `--import` cộng một loader hook cho ES module), hoặc một file instrumentation được import ở dòng đầu tiên của `main.ts`. Khởi động agent từ bên trong một Nest module rất dễ hỏng: tới lúc đó Nest và một số library mà agent patch có thể đã được load, và bất cứ thứ gì load trước sẽ không được ghi lại. Mọi vendor bên dưới đều nói cùng một điều trong tài liệu của họ: hãy khởi động nó đầu tiên.

Định dạng module giờ quan trọng hơn trước. Cho tới Nest 11, `nest new` tạo ra project CommonJS. `nest new` của Nest 12 tạo ra ES module, và với hầu hết agent, ES module nghĩa là cần thêm một flag loader, đôi khi số library được instrument cũng ít hơn. Cả hai dạng lệnh đều được đưa ra bên dưới ở những chỗ vendor có tài liệu hướng dẫn.

#### NestJS Observe

NestJS Observe là nền tảng observability được xây dựng riêng cho Nest, bởi chính team NestJS. Một lệnh, chạy trong project của bạn, sẽ thiết lập nó:

```bash
$ npx @nestjs/observe link
```

Nó in ra một mã để bạn chấp thuận trên dashboard (đăng ký trước nếu cần), sau đó cài `@nestjs/observe`, đăng ký `ObserveModule` trong root module, truyền tùy chọn `instrument` vào `NestFactory.create()`, và ghi API key vào `.env`. Làm thủ công cũng chỉ là ba chỗ sửa đó - xem [Liên kết từ terminal](/observability/sdk#linking-from-the-terminal) và [Bắt đầu nhanh](/observability/sdk#quick-start). Không cần flag preload: Nest giao cho SDK mọi provider mà nó tạo ra thông qua hook `instrument`, nên các class của chính bạn không phụ thuộc vào thứ tự load, và cách thiết lập giống nhau cho cả CommonJS lẫn ES module.

**Những gì nó thấy về Nest:** mọi provider. Mỗi lời gọi method trên controller, service, repository, guard, interceptor hay pipe trong một request, job hay message đều trở thành một span được đặt tên đúng như cách bạn đặt tên, nên `PricingService.quote` có trong trace mà không ai phải thêm nó vào. Queue consumer, handler `@Cron()`, GraphQL resolver và WebSocket gateway được ghi lại đúng bản chất của chúng, và một job BullMQ hoặc Bull dùng chung trace với request đã đưa nó vào queue. Các query qua `pg`, `mysql2`, `mssql` và `mongodb` (tức là TypeORM, Drizzle, MikroORM, Mongoose và các adapter `pg` và SQL Server của Prisma) và các lời gọi HTTP ra ngoài đều hiện ra dưới method đã thực hiện chúng.

**Những chỗ nó hẹp hơn các công cụ khác:** nó chỉ instrument NestJS trên Node.js. Các service viết bằng ngôn ngữ khác dùng chung trace với nó thông qua OpenTelemetry (xem [Dùng nhiều hơn một](#using-more-than-one)), nhưng span của chúng vẫn nằm trong backend OpenTelemetry của bạn, vì Observe không nhận OTLP. Nó chỉ có bản hosted, và không giám sát hạ tầng ngoài runtime của chính mỗi process Node.js. Chi tiết query ở cấp driver bao gồm `pg`, `mysql2`, `mssql` và `mongodb`; client Redis và Kafka hiện ra thành span khi chúng được đăng ký làm Nest provider (cách thiết lập thông thường), và các lời gọi cloud SDK hiện ra dưới dạng các HTTP request mà chúng thực hiện. Nó cần `@nestjs/core` 11.1.4 trở lên và Node.js 20.19 trở lên, với Express hoặc Fastify.

Hãy chọn nó cho các service NestJS của bạn, toàn bộ backend hay một phần, khi câu hỏi bạn cứ phải đặt ra là class nào của chính mình đang chậm. Gói Free không cần thông tin thanh toán, và [bản demo trực tiếp](https://www.observe-demo.nestjs.com/dashboard 'NestJS Observe live demo') hiển thị dashboard trên dữ liệu của một service bận rộn mà không cần đăng ký.

#### OpenTelemetry

[OpenTelemetry](https://opentelemetry.io/ 'OpenTelemetry') là chuẩn trung lập với vendor: bạn instrument một lần và gửi trace, metric và log tới bất kỳ backend nào nhận OTLP - Jaeger, Grafana Tempo, hoặc một trong rất nhiều vendor nhận nó, trong đó có Datadog, New Relic và Elastic. Cách thiết lập nó trong một ứng dụng Nest được trình bày trong [OpenTelemetry → Thiết lập không cần code](/observability/opentelemetry#zero-code-setup).

**Những gì nó thấy về Nest:** HTTP server, router, các lời gọi ra ngoài và rất nhiều driver, thông qua các auto-instrumentation cho Node.js. Instrumentation Nest của nó, `@opentelemetry/instrumentation-nestjs-core`, thêm ba loại span trên NestJS 11 trở về trước - việc tạo ứng dụng, request context được đặt tên `Controller.method`, và route handler - và không có gì cho các provider bên dưới. Bản release hiện tại của nó (0.71.0) hỗ trợ `@nestjs/core` dưới 12, nên trên NestJS 12 nó hoàn toàn không thêm span Nest nào.

Hãy chọn nó cho các service không phải Nest, khi bạn muốn tự chọn (và đổi) backend, hoặc khi dữ liệu phải nằm trên hạ tầng do bạn vận hành. Trong một hệ thống có cả hai, NestJS Observe tham gia vào các trace của nó và có thể export span của các service Nest sang cùng backend đó.

#### Sentry

Sentry trước hết là một công cụ theo dõi lỗi, có sẵn performance tracing. Nó có một SDK chính thức cho Nest:

```typescript
@@filename(instrument)
import * as Sentry from '@sentry/nestjs';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 1.0,
});
```

```typescript
@@filename(main)
// This import comes before everything else
import './instrument';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
```

Sau đó thêm `SentryModule.forRoot()` từ `@sentry/nestjs/setup` vào imports của root module và, nếu bạn chưa có exception filter bắt tất cả, hãy đăng ký `SentryGlobalFilter` làm `APP_FILTER` trước mọi filter khác.

**Những gì nó thấy về Nest:** nhiều hơn bất kỳ agent chung chung nào. SDK của Sentry tạo span cho request pipeline của Nest - middleware, guard, pipe, interceptor, filter và route handler, miễn là chúng có `@Injectable()` - bên cạnh HTTP và các database driver phổ biến. Lớp service của bạn thì bạn vẫn phải tự instrument.

Hãy chọn nó khi lỗi là mối quan tâm chính, đặc biệt là trên cả frontend web hoặc mobile lẫn backend. Sentry cũng có thể tự host.

#### Datadog

Tracer của Datadog, `dd-trace`, gửi trace tới một Datadog Agent mà bạn chạy bên cạnh ứng dụng, agent này sẽ chuyển tiếp chúng đi:

```bash
$ npm i dd-trace
$ DD_SERVICE=orders-api DD_ENV=production node --require dd-trace/init dist/main.js
```

Với ES module trên Node.js 20.6 trở lên, có một cách viết tắt chỉ với một flag:

```bash
$ node --import dd-trace/initialize.mjs dist/main.js
```

**Những gì nó thấy về Nest:** NestJS không nằm trong danh sách web framework mà tracer Node.js của Datadog liệt kê; tài liệu của họ nhắc tới nó như một framework có entry point tùy chỉnh, điều này liên quan tới thứ tự load chứ không phải instrumentation. Bạn có Express hoặc Fastify, các lời gọi ra ngoài, rất nhiều driver, và BullMQ (5.66 trở lên) là một library được hỗ trợ. Một package cộng đồng, `nestjs-ddtrace`, có thể bọc controller và provider của bạn trong các span Datadog.

Hãy chọn nó khi bạn có nhiều ngôn ngữ và hạ tầng thực sự cần theo dõi bên cạnh ứng dụng.

#### New Relic

Agent Node.js của New Relic báo cáo thẳng lên New Relic, không cần chạy collector nào cho APM:

```bash
$ npm i newrelic
$ NEW_RELIC_APP_NAME=orders-api NEW_RELIC_LICENSE_KEY=... node -r newrelic dist/main.js
```

Với ES module, New Relic có tài liệu về một loader đi kèm preload, và file cấu hình `newrelic.js` phải đổi thành `newrelic.cjs`:

```bash
$ node --import newrelic/esm-loader.mjs -r newrelic dist/main.js
```

**Những gì nó thấy về Nest:** `@nestjs/core` nằm trong danh sách module được instrument của New Relic (phiên bản 10 trở lên), nhờ đó các transaction được đặt tên theo route Nest của bạn. Bên dưới đó bạn có Express hoặc Fastify, HTTP ra ngoài, và các driver bao gồm `pg`, `mysql2`, `mongodb`, `ioredis` và Prisma (`@prisma/client` 5 trở lên). BullMQ và Bull không có trong danh sách, và các provider của chính bạn không thành span trừ khi bạn tự thêm. Agent hiện tại cần Node.js 22.16 trở lên.

Hãy chọn nó khi bạn muốn một nền tảng đầy đủ - APM, hạ tầng, log, browser - với Node.js là một trong nhiều ngôn ngữ.

#### Elastic APM

Agent Node.js của Elastic APM gửi trace tới một APM Server rồi vào Elasticsearch, nơi Kibana hiển thị chúng:

```bash
$ npm i elastic-apm-node
$ ELASTIC_APM_SERVICE_NAME=orders-api \
  ELASTIC_APM_SERVER_URL=https://apm.example.com:8200 \
  ELASTIC_APM_SECRET_TOKEN=... \
  node -r elastic-apm-node/start.js dist/main.js
```

Với ES module, chính tài liệu của agent mô tả việc hỗ trợ là chưa hoàn chỉnh và còn thử nghiệm: bạn thêm một loader, vẫn khởi động agent riêng, và chỉ một phần các module (`http`, Express, Fastify, `pg`, `ioredis` và một vài module khác) được instrument:

```bash
$ node -r elastic-apm-node/start.js --experimental-loader=elastic-apm-node/loader.mjs dist/main.js
```

**Những gì nó thấy về Nest:** NestJS không nằm trong danh sách framework được hỗ trợ của agent. Nó instrument server bên dưới, nên các transaction được đặt tên theo route, và nó ghi lại query qua `pg`, `mysql2`, `mongodb` và `ioredis`. Controller, service và repository của bạn không thành span trừ khi bạn thêm chúng bằng API của agent, và BullMQ cùng Bull không có trong danh sách của nó. Tài liệu của chính Elastic giờ cũng gợi ý EDOT, bản phân phối OpenTelemetry của họ cho Node.js, vốn thấy được đại khái những gì [OpenTelemetry](#opentelemetry) thấy.

Hãy chọn nó khi bạn đã chạy Elastic Stack, hoặc khi dữ liệu phải nằm trên hạ tầng do bạn kiểm soát.

#### So sánh song song <a id="side-by-side"></a>

|                                            | NestJS Observe                                             | Sentry                                                          | Datadog                                         | New Relic                                      | Elastic APM                                                       |
| ------------------------------------------ | ---------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------- |
| Thiết lập                                  | `npx @nestjs/observe link`, hoặc một module và một tùy chọn | File instrument được import đầu tiên, module, filter            | `--require dd-trace/init`, cộng một Datadog Agent | `-r newrelic` và một license key              | `-r elastic-apm-node/start.js`, cộng APM Server và Elasticsearch  |
| ES module (mặc định của Nest 12)           | Thiết lập như trên                                         | Xem tài liệu của Sentry                                         | `--import dd-trace/initialize.mjs`              | `--import newrelic/esm-loader.mjs -r newrelic` | Loader thử nghiệm, một phần các module                            |
| Nhận diện bản thân Nest                    | Được xây riêng cho Nest                                    | Span cho pipeline (guard, pipe, interceptor, filter, handler)   | Không có trong danh sách                        | Có `@nestjs/core` 10+ trong danh sách          | Không có trong danh sách                                          |
| Provider của bạn tự động thành span        | Có                                                         | Không                                                           | Package cộng đồng (`nestjs-ddtrace`)            | Không                                          | Không                                                             |
| BullMQ job                                 | Có, liên kết với request đã đưa vào queue                  | Kiểm tra với cách thiết lập của bạn                             | Được hỗ trợ (5.66+)                             | Không có trong danh sách                       | Không có trong danh sách                                          |
| Thứ cần chạy ngoài ứng dụng                | Không có gì                                                | Không có gì (hoặc tự host)                                      | Datadog Agent                                   | Không có gì                                    | APM Server, Elasticsearch, Kibana (hoặc Elastic Cloud)            |
| Tự host được                               | Không                                                      | Có                                                              | Không                                           | Không                                          | Có                                                                |
| Ngôn ngữ                                   | NestJS; các ngôn ngữ khác dùng chung trace qua OpenTelemetry | Nhiều                                                         | Nhiều                                           | Nhiều                                          | Nhiều                                                             |
| Giám sát hạ tầng                           | Không                                                      | Không                                                           | Có                                              | Có                                             | Có                                                                |

Chương này không đưa ra giá: các mô hình tính theo host, theo seat, theo gigabyte và theo event không quy đổi qua lại một cách gọn gàng được, và chúng còn thay đổi. Hãy tính giá theo lưu lượng của chính bạn trên từng công cụ trước khi quyết định. Các gói của NestJS Observe được liệt kê trong [Đăng ký gói](/observability/overview#subscribing).

#### Chọn thế nào <a id="how-to-choose"></a>

- **Đang chạy Elastic, Datadog hoặc New Relic cho các service khác?** Hãy thêm ứng dụng Nest vào đó, và biết rằng bạn sẽ thấy router và driver, chứ không thấy các provider của mình. Nếu như vậy là chưa đủ, NestJS Observe có thể chạy bên cạnh cho lớp ứng dụng.
- **Chủ yếu lo về lỗi, đặc biệt là cả ở frontend?** Sentry.
- **Nhiều ngôn ngữ trên đường đi của request cần dùng chung một trace?** OpenTelemetry cho các service không phải Nest, và NestJS Observe cho các service Nest: với `openTelemetry` và `otlp`, các service Nest tham gia vào cùng trace và export span của chúng, chi tiết tới từng method của provider, sang backend OpenTelemetry của bạn, nơi hiển thị toàn bộ trace. Một APM nền tảng bao phủ mọi service trong một sản phẩm, nhưng chỉ thấy router và driver của các service Nest, không thấy provider của chúng.
- **Dữ liệu phải nằm trên hạ tầng của riêng bạn?** Elastic, Sentry tự host, hoặc OpenTelemetry với một backend do bạn vận hành.
- **Một backend NestJS, hiện chưa có tracing, và chưa ai có được một tuần để thiết lập nó?** Đó chính là trường hợp NestJS Observe được xây dựng để giải quyết: phần thiết lập ở trên là toàn bộ việc cần làm.

#### Dùng nhiều hơn một <a id="using-more-than-one"></a>

- **NestJS Observe song song với OpenTelemetry:** với tùy chọn `openTelemetry` của SDK, một service Nest đọc và gửi W3C `traceparent` và tham gia vào các trace mà những service khác của bạn dùng chung, và với `otlp` nó còn export span của mình - chi tiết tới từng method của provider - sang backend OpenTelemetry của bạn. Xem [Chạy song song với OpenTelemetry](/observability/opentelemetry#running-beside-opentelemetry).
- **NestJS Observe song song với Datadog hoặc New Relic:** giữ nền tảng đó cho hạ tầng và các service khác, bật `openTelemetry`, và trỏ `otlp` tới endpoint OTLP của nền tảng, để các span provider của service Nest cũng nằm trong trace của nó.
- **NestJS Observe song song với Sentry:** giữ Sentry cho frontend và thêm NestJS Observe cho backend Nest.
