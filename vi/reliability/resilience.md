### Resilience

`@nestjs/resilience` bổ sung retry, timeout, circuit breaker, bulkhead và fallback cho controller, resolver, message handler và gateway, dưới dạng decorator.

Sớm hay muộn, mọi ứng dụng gọi sang một hệ thống khác đều sẽ gặp một hệ thống chậm hoặc bị down. Nếu không có kế hoạch, một dependency chậm sẽ giữ chân các request handler của bạn, client phải chờ tới khi timeout của chính chúng kích hoạt, và các lần retry từ mọi tầng lại dồn thêm tải lên chính service đang chật vật.

`@nestjs/resilience` cung cấp những công cụ quen thuộc dưới dạng decorator: **retry**, **timeout**, **circuit breaker**, **bulkhead** và **fallback**. Chúng áp dụng cho các **entrypoint** của ứng dụng, tức là controller, GraphQL resolver, microservice message handler và WebSocket gateway. Với code bên trong service, các thiết lập tương tự có sẵn dưới dạng policy object. Một global interceptor duy nhất áp dụng các decorator, nên chúng hoạt động giống nhau trên mọi transport, và mỗi lỗi sẽ trở thành lỗi gốc của transport đó. Ví dụ qua HTTP, một timeout trả về `504 Gateway Timeout` và một breaker đang mở trả về `503 Service Unavailable` kèm header `Retry-After`.

Trong bài hướng dẫn này, bạn sẽ gia cố API đơn hàng của một cửa hàng online bán thức ăn và đồ dùng cho mèo. Checkout gọi sang đơn vị vận chuyển để lấy báo giá, và API báo giá của đơn vị vận chuyển thì lúc tốt nhất cũng chậm, thỉnh thoảng còn bị down. Khi kết thúc, một đơn vị vận chuyển chậm chỉ làm checkout mất tối đa khoảng ba giây. Khi đã biết đơn vị vận chuyển đang down, checkout sẽ không chờ nó nữa: khách hàng thấy phí vận chuyển đồng giá thay vì một lỗi, và một background job ngừng gọi đơn vị vận chuyển cho tới khi nó hồi phục.

#### Yêu cầu trước <a id="prerequisites"></a>

Bài hướng dẫn này giả định có một `OrdersModule` export một `OrdersService`. Service cần các method sau: `findOne(id)` (throw `NotFoundException` với id không tồn tại), `findAll()`, `update(id, changes)` và `exportCsv()`. Đơn hàng trông như thế này:

```typescript
@@filename(orders/order)
export interface OrderItem {
  productId: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  total: number;
  status: 'pending' | 'paid' | 'shipped';
}

export function subtotal(order: Order): number {
  return order.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}
```

Cài đặt package:

```bash
$ npm i --save @nestjs/resilience
```

[Retry một POST an toàn](/reliability/resilience#retry-a-post-safely) còn dùng `@nestjs/idempotency` (xem [Idempotency key](/reliability/idempotency)).

#### Đăng ký module <a id="register-the-module"></a>

Import `ResilienceModule` vào root module. Cấu hình giá trị mặc định cho các field và một preset có tên, `carrier`, mô tả cách ứng dụng nên đối xử với đơn vị vận chuyển:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { ResilienceModule } from '@nestjs/resilience';
import { OrdersModule } from './orders/orders.module.js';
import { ShippingModule } from './shipping/shipping.module.js';

@Module({
  imports: [
    ResilienceModule.forRoot({
      defaults: {
        timeout: '5s',
        retry: { attempts: 3, backoff: { delay: '200ms', maxDelay: '2s' } },
      },
      presets: {
        carrier: {
          timeout: '2s',
          retry: { attempts: 2 },
          circuitBreaker: { failureRateThreshold: 50, minimumCalls: 10, openDuration: '30s' },
        },
      },
    }),
    OrdersModule,
    ShippingModule,
  ],
})
export class AppModule {}
```

Hai tùy chọn này làm hai việc khác nhau:

- `defaults` điền giá trị cho các field của bất kỳ stage nào mà một decorator hoặc preset bật lên. Bản thân defaults không bao giờ tự bật một stage. Ở đây, một lần retry đầu tiên chờ một khoảng thời gian ngẫu nhiên từ 0 đến 200 ms (`delay`), sau đó tối đa 400 ms, cứ thế nhân đôi mỗi lần cho tới 2 giây (`maxDelay`). Một `@Timeout()` không tham số nghĩa là 5 giây.
- `presets` chứa các tập stage có tên, thường mỗi dependency một preset. Preset `carrier` cho mỗi lần thử 2 giây, thử tối đa 2 lần, và thêm một circuit breaker. Breaker đó được **dùng chung dưới tên `carrier`** bởi mọi route, handler và service dùng preset này. Đơn vị vận chuyển là một dependency, nên nó có một breaker.

Mọi tùy chọn mang giá trị thời gian đều nhận số mili giây hoặc một chuỗi như `'200ms'`, `'2s'` hay `'30s'`.

Module này là global, nên chỉ cần import một lần, trong root module. Nó đăng ký một interceptor cho toàn ứng dụng, interceptor này không làm gì với các handler không có resilience decorator ngoài việc map lỗi. Nó kiểm tra cấu hình lúc bootstrap: một tên preset không tồn tại, một khoảng thời gian hoặc con số không hợp lệ (chẳng hạn `NaN` của một biến môi trường chưa đặt), một fallback method bị thiếu, hoặc một tên breaker được cấu hình theo hai cách khác nhau sẽ làm ứng dụng khởi động thất bại thay vì để tới request đầu tiên mới lỗi. Dùng `ResilienceModule.forRootAsync()` để dựng các tùy chọn từ cấu hình.

#### Đặt ngân sách thời gian cho route báo giá <a id="put-a-time-budget-on-the-quotes-route"></a>

Bắt đầu với một client cho đơn vị vận chuyển. Mọi method đều nhận một `AbortSignal` và truyền nó cho `fetch()`:

```typescript
@@filename(shipping/carrier.client)
import { Injectable } from '@nestjs/common';
import type { Order } from '../orders/order.js';

export interface ShippingQuote {
  service: string;
  price: number;
  estimatedDays: number;
}

export interface Shipment {
  id: string;
  reference: string;
  trackingNumber: string;
}

export class CarrierError extends Error {
  constructor(readonly status: number) {
    super(`The carrier answered with status ${status}`);
  }
}

@Injectable()
export class CarrierClient {
  private readonly baseUrl = process.env.CARRIER_URL ?? 'https://api.carrier.example.com';

  getQuotes(order: Order, signal: AbortSignal): Promise<ShippingQuote[]> {
    return this.post('/v2/quotes', { reference: order.id, items: order.items }, signal);
  }

  /** The carrier returns the existing shipment when it has seen the reference before. */
  createShipment(order: Order, signal: AbortSignal): Promise<Shipment> {
    return this.post('/v2/shipments', { reference: order.id, items: order.items }, signal);
  }

  private async post<T>(path: string, body: unknown, signal: AbortSignal): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
    if (!response.ok) {
      throw new CarrierError(response.status);
    }
    return (await response.json()) as T;
  }
}
```

Service truyền signal đi tiếp. Nó còn có một bảng giá đồng giá và một method đặt vận chuyển, hai thứ này được circuit breaker và lần retry POST dùng ở bên dưới:

```typescript
@@filename(shipping/shipping.service)
import { Injectable } from '@nestjs/common';
import { OrdersService } from '../orders/orders.service.js';
import { CarrierClient, type Shipment, type ShippingQuote } from './carrier.client.js';

@Injectable()
export class ShippingService {
  constructor(
    private readonly ordersService: OrdersService,
    private readonly carrierClient: CarrierClient,
  ) {}

  async getQuotes(orderId: string, signal: AbortSignal): Promise<ShippingQuote[]> {
    const order = await this.ordersService.findOne(orderId);
    return this.carrierClient.getQuotes(order, signal);
  }

  flatRateQuotes(): ShippingQuote[] {
    return [{ service: 'flat-rate', price: 4.99, estimatedDays: 5 }];
  }

  async createShipment(orderId: string, signal: AbortSignal): Promise<Shipment> {
    const order = await this.ordersService.findOne(orderId);
    return this.carrierClient.createShipment(order, signal);
  }
}
```

Giờ đến route. `@Resilience('carrier')` áp dụng preset, và `@Signal()` inject `AbortSignal` của lần thử hiện tại:

```typescript
@@filename(shipping/shipping.controller)
import { Controller, Get, Query } from '@nestjs/common';
import { Resilience, Signal, Timeout } from '@nestjs/resilience';
import { ShippingService } from './shipping.service.js';

@Controller('shipping')
export class ShippingController {
  constructor(private readonly shippingService: ShippingService) {}

  @Get('quotes')
  @Resilience('carrier')
  @Timeout('1.5s')
  getQuotes(@Query('orderId') orderId: string, @Signal() signal: AbortSignal) {
    return this.shippingService.getQuotes(orderId, signal);
  }
}
```

Đăng ký `CarrierClient` và `ShippingService` làm provider, và `ShippingController` làm controller, của một `ShippingModule` có import `OrdersModule`.

Checkout không thể chờ lâu, nên `@Timeout('1.5s')` cho route này một ngân sách chặt hơn của preset. Các thiết lập được resolve **theo từng stage**: một decorator trên handler sẽ thắng preset ở stage của chính nó, còn preset vẫn cung cấp retry và breaker. Một `@Timeout()` không tham số sẽ lấy 2 giây của preset, và chỉ fallback về `defaults.timeout` khi không có preset hay `@Timeout()` cấp class nào đặt thời lượng.

Khi một lần thử hết thời gian, ba điều xảy ra:

1. Lần thử bị reject với một `ResilienceTimeoutError`.
2. Signal bị abort với chính lỗi đó. `fetch()` reject và đóng kết nối, nên không có gì tiếp tục chờ một câu trả lời mà không ai đọc. Việc hủy là cộng tác (cooperative): code bỏ qua signal sẽ tiếp tục chạy ngầm, và kết quả của nó bị bỏ đi.
3. Vì `GET` là một method an toàn, retry của preset sẽ thực hiện lần thử thứ hai. Chỉ các pipe, interceptor bên trong và handler được chạy lại. Guard và middleware chỉ chạy một lần mỗi request.

Nếu lần thử thứ hai cũng timeout, client nhận được `504`:

```json
{
  "statusCode": 504,
  "error": "Gateway Timeout",
  "message": "The operation timed out",
  "code": "TIMEOUT"
}
```

Timeout áp dụng **cho từng lần thử**, nên một đơn vị vận chuyển bị treo làm route này mất khoảng 3.2 giây: hai lần thử 1.5 giây cộng tối đa 200 ms backoff. Status là 504 thay vì 408 là có chủ ý. Một 408 ngầm khẳng định rằng _client_ đã quá chậm khi gửi request, và một số client cũng như proxy tự động gửi lại khi gặp 408, kể cả với request `POST`.

Lỗi client không phải là thất bại. Một request cho đơn hàng không tồn tại sẽ throw `NotFoundException` trước khi đơn vị vận chuyển được gọi. Nó trả về 404, và không bị retry cũng không được breaker đếm.

> info **Gợi ý** Code không thể nhận signal làm tham số có thể inject `ResilienceContext` và đọc `signal` cùng `attempt` của nó. Nó đọc lần thử hiện tại từ `AsyncLocalStorage`, nên hoạt động trong bất kỳ service nào mà handler gọi tới, trên mọi transport. Một policy object được dùng bên trong lần thử cũng kế thừa signal của nó, nên timeout của route cũng dừng luôn các lần retry của policy đó.

#### Fail fast với circuit breaker <a id="fail-fast-with-a-circuit-breaker"></a>

Breaker của preset ghi lại kết quả của mọi lần thử. Breaker `carrier` sẽ mở khi nó đã thấy ít nhất `minimumCalls` (10) lời gọi, và ít nhất `failureRateThreshold` (50%) trong số đó thất bại. Mặc định nó xét 20 lời gọi gần nhất. Mọi lỗi đều được tính là thất bại, kể cả timeout, trừ lỗi client và các lần bị reject bởi policy khác. Lỗi client là một `HttpException` 4xx, hoặc bất kỳ lỗi nào khác có thuộc tính `status` hoặc `statusCode` mang giá trị 4xx. Điều này bao gồm cả `CarrierError`: khi đơn vị vận chuyển trả về `422` cho một request sai định dạng, nó không bị down, nên breaker bỏ qua lỗi đó và retry không lặp lại nó. Ngoại lệ là `408` hoặc `429` từ đơn vị vận chuyển, vì nó có nghĩa là đơn vị vận chuyển đang từ chối bớt tải, nên nó được tính như một `5xx`. Một `HttpException` mang một trong các status đó vẫn là lỗi client: handler throw nó để trả lời chính bên gọi của mình, và điều đó không nói lên gì về đơn vị vận chuyển. Để thay đổi những gì được tính, hãy truyền một hàm `recordIf` trong tùy chọn của breaker.

Trong khi breaker đang **open**, các lời gọi thất bại ngay lập tức và đơn vị vận chuyển hoàn toàn không được gọi. Client nhận `503` kèm header `Retry-After`: số giây cho tới khi breaker cho phép một lời gọi thăm dò đi qua. Retry bọc bên ngoài breaker, nên một lần bị reject không bao giờ được retry.

Sau `openDuration` (30 giây), breaker chuyển sang **half-open**. Nó cho phép một lời gọi thăm dò đi qua (xem `halfOpenMaxCalls`). Nếu lời gọi thăm dò thành công, breaker đóng lại và bắt đầu lại với một cửa sổ trống. Nếu thất bại, breaker mở thêm 30 giây nữa. Breaker không dùng timer cho việc này. Nó kiểm tra trạng thái ở lời gọi tiếp theo.

Một 503 là đúng, nhưng checkout có thể làm tốt hơn. Hãy thêm một fallback trả về báo giá đồng giá trong khi đã biết đơn vị vận chuyển đang down (import `Fallback` và `CircuitOpenError` từ `@nestjs/resilience`):

```typescript
@@filename(shipping/shipping.controller)
@Get('quotes')
@Resilience('carrier')
@Timeout('1.5s')
@Fallback('flatRateQuotes', {
  handleIf: (error) => error instanceof CircuitOpenError,
})
getQuotes(@Query('orderId') orderId: string, @Signal() signal: AbortSignal) {
  return this.shippingService.getQuotes(orderId, signal);
}

flatRateQuotes() {
  return this.shippingService.flatRateQuotes();
}
```

`@Fallback()` nhận tên một method trên cùng class, hoặc một hàm. TypeScript kiểm tra rằng class có method với tên đó. Fallback được gọi với lỗi và `ExecutionContext`, và bất cứ thứ gì nó trả về sẽ trở thành response. Đó có thể là một giá trị, một `Promise` hoặc một `Observable`. Fallback là stage ngoài cùng, nên nó cũng thấy các lần reject của breaker.

Mặc định, một fallback thay thế mọi lỗi trừ lỗi client. Tùy chọn `handleIf` thu hẹp phạm vi đó. Giá đồng giá làm cửa hàng lỗ tiền với các kiện hàng nặng, như bao cát vệ sinh, nên ở đây chúng là phương án cuối cùng: chúng chỉ được dùng khi breaker báo đơn vị vận chuyển đang down, còn một câu trả lời chậm đơn lẻ vẫn nhận 504.

> info **Gợi ý** Để xem một breaker từ code của bạn, hãy inject `ResilienceService` và gọi `circuitBreaker('carrier')`. Breaker cung cấp `state` và `stats`, và bạn có thể ép nó mở hoặc đóng bằng `trip()` và `reset()`.

#### Giới hạn số lượt export CSV đồng thời bằng bulkhead <a id="cap-concurrent-csv-exports-with-a-bulkhead"></a>

Bộ phận back office tải toàn bộ đơn hàng về dưới dạng file CSV. Việc dựng file đọc mọi đơn hàng và rất nặng cho cả database lẫn CPU. Hai lượt export cùng lúc thì ổn, nhưng hai mươi lượt sẽ làm checkout chậm đi với tất cả mọi người. Một bulkhead giới hạn số lượng chạy cùng lúc:

```typescript
@@filename(orders/orders.controller)
import { Controller, Get, Header } from '@nestjs/common';
import { Bulkhead } from '@nestjs/resilience';
import { OrdersService } from './orders.service.js';

@Controller('orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Get('export')
  @Header('Content-Type', 'text/csv')
  @Bulkhead({ maxConcurrent: 2, maxQueue: 3, queueTimeout: '10s' })
  export() {
    return this.ordersService.exportCsv();
  }
}
```

Hai lượt export chạy cùng lúc. Tối đa ba lượt nữa chờ tới lượt, mỗi lượt chờ tối đa 10 giây. Request thứ sáu nhận `503` ngay lập tức, và một request đang chờ cũng vậy khi hết 10 giây:

```json
{
  "statusCode": 503,
  "error": "Service Unavailable",
  "message": "Server is at capacity",
  "code": "BULKHEAD_FULL"
}
```

503 này không có header `Retry-After`, vì không ai biết khi nào một chỗ trống sẽ xuất hiện. Status là 503 thay vì 429 vì 429 đổ lỗi cho tần suất request của client, còn một bulkhead đầy nghĩa là server đã hết công suất với tất cả mọi người.

Một chỗ vẫn bị chiếm cho tới khi handler hoàn tất, hoặc cho tới khi một timeout trên route bỏ cuộc với lần thử đó. Khi đó, một handler bỏ qua signal của nó sẽ tiếp tục chạy ngầm, nằm ngoài số đếm của bulkhead, thêm một lý do để truyền signal cho mọi lời gọi có nhận nó. Một bulkhead không có tên thuộc về handler của nó, và được đăng ký dưới tên của handler. Để đọc mức tải của nó, hãy inject `ResilienceService` và xem `bulkhead('OrdersController.export')`, có các số đếm `active` và `queued`. Đặt `name` cho bulkhead để dùng chung một nhóm chỗ giữa nhiều handler.

#### Retry một POST an toàn <a id="retry-a-post-safely"></a>

Cho tới giờ, retry chỉ xảy ra với `GET`. Đó là có chủ ý. Trên HTTP, retry chỉ áp dụng cho các method an toàn `GET`, `HEAD` và `OPTIONS`, và trên GraphQL chỉ cho query. Chạy một `POST` hai lần có thể tạo ra hai đơn vận chuyển, và package không thể biết điều đó có vô hại hay không. Vì vậy retry của một preset đơn giản là bị bỏ qua trên `POST`. Một decorator `@Retry()` đặt trực tiếp lên handler `POST` cũng bị bỏ qua, và bootstrap sẽ cảnh báo về điều đó:

```bash
WARN [ResilienceModule] @Retry() on ShippingController.createShipment() is inactive: it only re-runs safe operations (GET, HEAD, OPTIONS, GraphQL queries). If the handler is safe to repeat, use @Retry({ idempotent: true }).
```

Đặt vận chuyển _thì_ an toàn để lặp lại, vì đơn vị vận chuyển khử trùng lặp các đơn vận chuyển theo `reference`, chính là id đơn hàng. Điều đó còn quan trọng vì một lý do khác: một lần đặt bị timeout có thể vẫn đã thành công ở phía đơn vị vận chuyển, nên dù sao thì retry cũng phải an toàn. Đặt `idempotent: true` trên `@Retry()` là cách bạn khẳng định rằng chạy handler hai lần trong một request là ổn:

```typescript
@@filename(shipping/shipping.controller)
import { Body, Controller, Get, Post, Query } from '@nestjs/common';
import { Idempotent } from '@nestjs/idempotency';
import { CircuitOpenError, Fallback, Resilience, Retry, Signal, Timeout } from '@nestjs/resilience';
import { ShippingService } from './shipping.service.js';

@Controller('shipping')
export class ShippingController {
  constructor(private readonly shippingService: ShippingService) {}

  @Get('quotes')
  @Resilience('carrier')
  @Timeout('1.5s')
  @Fallback('flatRateQuotes', {
    handleIf: (error) => error instanceof CircuitOpenError,
  })
  getQuotes(@Query('orderId') orderId: string, @Signal() signal: AbortSignal) {
    return this.shippingService.getQuotes(orderId, signal);
  }

  flatRateQuotes() {
    return this.shippingService.flatRateQuotes();
  }

  @Post('shipments')
  @Idempotent()
  @Resilience('carrier')
  @Retry({ idempotent: true })
  createShipment(@Body('orderId') orderId: string, @Signal() signal: AbortSignal) {
    return this.shippingService.createShipment(orderId, signal);
  }
}
```

Một `@Retry()` ở cấp handler được merge vào retry của preset, theo từng field. Các field bạn đặt sẽ thắng, phần còn lại lấy từ preset, rồi từ `defaults.retry`. Vì vậy route này giữ 2 lần thử của preset và chỉ thêm `idempotent: true`. Timeout 2 giây và breaker của preset vẫn áp dụng. Chỉ một decorator mới có thể nói `idempotent: true`: một preset không thể tuyên bố mọi handler dùng nó đều an toàn để lặp lại.

`idempotent: true` và `@Idempotent()` giải quyết hai vấn đề khác nhau:

- `idempotent: true` cho phép **server** chạy lại handler trong một request.
- `@Idempotent()` khử trùng lặp các lần retry toàn bộ request từ phía **client**. Khi một client lặp lại một request với cùng header `Idempotency-Key`, nó nhận lại response đã lưu và handler không chạy lại.

Đăng ký `IdempotencyModule` **trước** `ResilienceModule`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { IdempotencyModule } from '@nestjs/idempotency';
import { ResilienceModule } from '@nestjs/resilience';
import { OrdersModule } from './orders/orders.module.js';
import { ShippingModule } from './shipping/shipping.module.js';

@Module({
  imports: [
    // Import order matters: the first global interceptor runs outermost.
    IdempotencyModule.forRoot({}),
    ResilienceModule.forRoot({
      defaults: {
        timeout: '5s',
        retry: { attempts: 3, backoff: { delay: '200ms', maxDelay: '2s' } },
      },
      presets: {
        carrier: {
          timeout: '2s',
          retry: { attempts: 2 },
          circuitBreaker: { failureRateThreshold: 50, minimumCalls: 10, openDuration: '30s' },
        },
      },
    }),
    OrdersModule,
    ShippingModule,
  ],
})
export class AppModule {}
```

Cả hai module đều đăng ký một global interceptor, và module nào được import trước sẽ chạy ở ngoài cùng. Với thứ tự này:

- Một lần replay, hoặc một `409` cho một key vẫn đang được xử lý, được trả lời trước khi bất kỳ retry, breaker hay timeout nào chạy. Một lần đặt đã thành công sẽ được replay ngay cả khi breaker đang mở.
- Mọi lần retry của một request diễn ra dưới cùng một key đã được claim.
- Response được lưu là kết quả cuối cùng, sau các lần retry và fallback nếu có.
- Một `503` hoặc `504` là response 5xx, nên key được giải phóng và client có thể thử lại sau với cùng key.

Giải phóng key khi gặp `504` có một vấn đề. Key được giải phóng ngay khi timeout trả lời, nhưng lần chạy bị timeout có thể vẫn đang tiếp diễn, hoặc có thể đã tới được đơn vị vận chuyển, nên một lần retry với cùng key có thể chồng lấn với nó. Đó là lý do side effect phải an toàn để lặp lại ở phía sau, như đơn vị vận chuyển đảm bảo bằng `reference`. Truyền signal đi tiếp, như `createShipment()` làm, sẽ dừng công việc ở local sớm hơn.

#### Dùng cùng các policy bên trong service <a id="use-the-same-policies-inside-services"></a>

Các đơn hàng đang chờ có kèm ước tính phí vận chuyển trong `total`. Cứ 15 phút, một background job lại lấy báo giá mới cho chúng. Job không phải là entrypoint, nên nó dùng một **policy object**, lấy từ `ResilienceService`:

```typescript
@@filename(shipping/repricing.service)
import { Injectable, Logger } from '@nestjs/common';
import { CircuitOpenError, ResilienceService, type ResiliencePolicy } from '@nestjs/resilience';
import { subtotal } from '../orders/order.js';
import { OrdersService } from '../orders/orders.service.js';
import { CarrierClient } from './carrier.client.js';

@Injectable()
export class RepricingService {
  private readonly logger = new Logger(RepricingService.name);
  private readonly resiliencePolicy: ResiliencePolicy;

  constructor(
    resilience: ResilienceService,
    private readonly ordersService: OrdersService,
    private readonly carrierClient: CarrierClient,
  ) {
    this.resiliencePolicy = resilience.preset('carrier');
  }

  /** Refreshes the shipping part of every pending order's total. */
  async repricePendingOrders(): Promise<number> {
    const pending = (await this.ordersService.findAll()).filter((order) => order.status === 'pending');
    let repriced = 0;
    for (const order of pending) {
      try {
        const quotes = await this.resiliencePolicy.execute(
          ({ signal }) => this.carrierClient.getQuotes(order, signal),
          { source: 'RepricingService.repricePendingOrders' },
        );
        const shipping = Math.min(...quotes.map((quote) => quote.price));
        await this.ordersService.update(order.id, { total: subtotal(order) + shipping });
        repriced++;
      } catch (error) {
        if (error instanceof CircuitOpenError) {
          this.logger.warn(`The carrier is unavailable, stopping after ${repriced} of ${pending.length} orders`);
          break;
        }
        this.logger.error(`Could not reprice order ${order.id}`, (error as Error).stack);
      }
    }
    return repriced;
  }
}
```

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

```bash
WARN [ResilienceModule] Resilience decorators on RepricingService.repricePendingOrders() have no effect: RepricingService is not a controller, resolver or gateway. They apply to entrypoints only. Inside services, use a policy object (ResilienceService.preset() or create(), or new RetryPolicy() etc.).
```

Đây là một lựa chọn có chủ ý, vì ba lý do:

- Bọc các method tùy ý của provider sẽ bỏ sót các instance request-scoped và transient, vốn được Nest tạo ra sau bootstrap.
- Các lần retry ẩn sâu bên trong service sẽ nhân lên. Một route thử 3 lần, gọi một service thử 3 lần, gọi một SDK thử 3 lần, sẽ gửi tới 27 request tới một dependency vốn đang chật vật.
- Một policy object hiện rõ ở chỗ gọi, nơi bạn thấy được nó làm gì.

> info **Gợi ý** Một entrypoint không có decorator vẫn map các lỗi resilience. Nếu một service throw `CircuitOpenError` bên trong một route bình thường, client nhận `503` kèm `Retry-After`. Đặt `mapErrors: false` trong tùy chọn của module để tắt hành vi này.

#### Các transport khác <a id="other-transports"></a>

Các decorator tương tự hoạt động trên microservice handler. Service kho hàng lấy báo giá qua TCP khi đóng gói lại một đơn hàng:

```typescript
@@filename(shipping/shipping.handlers)
import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { Resilience, Retry, Signal } from '@nestjs/resilience';
import { ShippingService } from './shipping.service.js';

@Controller()
export class ShippingHandlers {
  constructor(private readonly shippingService: ShippingService) {}

  @MessagePattern('shipping.quotes')
  @Resilience('carrier')
  @Retry({ attempts: 3 })
  getQuotes(@Payload() data: { orderId: string }, @Signal() signal: AbortSignal) {
    return this.shippingService.getQuotes(data.orderId, signal);
  }
}
```

Thêm `ShippingHandlers` vào `controllers` của `ShippingModule`.

Một message không có `GET` hay `POST` để biết nó có an toàn để lặp lại hay không, nên trên các handler message, event và WebSocket, chỉ có `@Retry()` đặt trên chính handler mới bật retry. Retry của preset, hoặc một `@Retry()` cấp class không có `idempotent: true`, sẽ không tự áp dụng ở đó, nên việc tái sử dụng preset `carrier` không thể âm thầm chạy lại một handler có side effect. Ở đây `@Retry()` của handler chủ động bật retry, và `attempts: 3` của nó nâng 2 lần thử của preset lên 3. Chỉ dùng nó trên những handler an toàn để chạy hai lần. Lỗi tới bên gọi dưới dạng `RpcException` với payload có cấu trúc:

```json
{ "status": "error", "code": "CIRCUIT_OPEN", "statusCode": 503, "message": "Service temporarily unavailable", "retryAfter": 30 }
```

Một timeout có `"code": "TIMEOUT"` và `"statusCode": 504`, và không có `retryAfter`. Trong một ứng dụng hybrid, hãy kết nối microservice với `inheritAppConfig: true`, nếu không global interceptor sẽ không tới được các handler của nó (xem [Ứng dụng hybrid](/faq/hybrid-application#sharing-configuration)):

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { Transport, type MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.connectMicroservice<MicroserviceOptions>(
    { transport: Transport.TCP, options: { port: 3001 } },
    { inheritAppConfig: true },
  );
  await app.startAllMicroservices();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

GraphQL resolver hoạt động theo cách tương tự. Nếu ứng dụng của bạn phục vụ GraphQL, hãy thêm một resolver vào providers của `ShippingModule`:

```typescript
@@filename(shipping/shipping.resolver)
import { Args, Field, Float, Int, ObjectType, Query, Resolver } from '@nestjs/graphql';
import { Resilience, Signal, Timeout } from '@nestjs/resilience';
import { ShippingService } from './shipping.service.js';

@ObjectType('ShippingQuote')
export class ShippingQuoteModel {
  @Field() service: string;
  @Field(() => Float) price: number;
  @Field(() => Int) estimatedDays: number;
}

@Resolver(() => ShippingQuoteModel)
export class ShippingResolver {
  constructor(private readonly shippingService: ShippingService) {}

  @Query(() => [ShippingQuoteModel], { nullable: true })
  @Resilience('carrier')
  @Timeout('1.5s')
  shippingQuotes(@Args('orderId') orderId: string, @Signal() signal: AbortSignal) {
    return this.shippingService.getQuotes(orderId, signal);
  }
}
```

Query được retry, còn mutation cần `idempotent: true`, giống như request `POST`. Một lỗi chỉ làm hỏng field của chính nó. Response vẫn có status 200, và lỗi mang code trong `extensions`:

```graphql
{ shippingQuotes(orderId: "1001") { service price } }
```

```json
{
  "errors": [
    {
      "message": "The operation timed out",
      "locations": [{ "line": 1, "column": 3 }],
      "path": ["shippingQuotes"],
      "extensions": { "code": "TIMEOUT", "httpStatus": 504 }
    }
  ],
  "data": { "shippingQuotes": null }
}
```

Một breaker đang mở báo `"code": "CIRCUIT_OPEN"`, `"httpStatus": 503` và `"retryAfter"` tính bằng giây. Package đặt `httpStatus` thay vì `extensions.http` của Apollo, vì Apollo sẽ áp dụng `extensions.http` cho toàn bộ response, dù chỉ có một field bị lỗi.

#### Theo dõi các lần chuyển trạng thái của breaker <a id="observe-breaker-transitions"></a>

Mọi policy đều phát ra các event có type: `retry`, `timeout`, `circuit-open`, `circuit-half-open`, `circuit-closed`, `circuit-rejected`, `bulkhead-rejected`, `rate-limited` và `fallback`. Mỗi event mang tên `policy`, và `source` của nó nếu có: entrypoint (chẳng hạn `ShippingController.getQuotes`) hoặc nhãn được truyền cho `execute()`. Inject `ResilienceEvents` để nhận chúng: `events$` của nó là một RxJS stream chứa mọi event từ các policy của ứng dụng này. Hãy log những event mà ai đó nên thấy:

```typescript
@@filename(resilience.logger)
import { Injectable, Logger, type OnModuleInit } from '@nestjs/common';
import { ResilienceEvents } from '@nestjs/resilience';

@Injectable()
export class ResilienceLogger implements OnModuleInit {
  private readonly logger = new Logger('Resilience');

  constructor(private readonly resilienceEvents: ResilienceEvents) {}

  onModuleInit() {
    this.resilienceEvents.events$.subscribe((event) => {
      switch (event.type) {
        case 'circuit-open':
        case 'circuit-half-open':
        case 'circuit-closed':
          this.logger.warn(`Circuit "${event.policy}" went from ${event.from} to ${event.to}`);
          break;
        case 'bulkhead-rejected':
          this.logger.warn(`${event.source} is at capacity (${event.active} running, ${event.queued} queued)`);
          break;
        case 'fallback':
          this.logger.log(`${event.source} answered with its fallback`);
          break;
      }
    });
  }
}
```

Thêm `ResilienceLogger` vào mảng `providers` của `AppModule`.

Mọi policy cũng publish mỗi event trên một [diagnostics channel](https://nodejs.org/api/diagnostics_channel.html) riêng, chẳng hạn `nestjs:resilience:timeout` hoặc `nestjs:resilience:circuit-open`, kể cả các policy được tạo mà không qua module. Các công cụ metric và tracing có thể subscribe mà không cần phụ thuộc vào package này. `ResilienceTimeoutEvent` là type của các message trên một channel, còn `ResilienceEvent` là union của tất cả:

```typescript
import { subscribe } from 'node:diagnostics_channel';
import type { ResilienceTimeoutEvent } from '@nestjs/resilience';

const timeouts = new Map<string, number>();

subscribe('nestjs:resilience:timeout', (message) => {
  const { policy } = message as ResilienceTimeoutEvent;
  timeouts.set(policy, (timeouts.get(policy) ?? 0) + 1);
});
```

[NestJS Observe](/observability/overview#what-it-offers) đã đọc HTTP ra ngoài từ các diagnostics channel của Node (xem [Database query và HTTP ra ngoài](/observability/sdk#database-queries-and-outbound-http)). Nó chưa subscribe vào các channel `nestjs:resilience`. Khi đã làm được, nó có thể gắn các lần retry và timeout vào span của request, vẽ biểu đồ trạng thái breaker theo tên, và cảnh báo khi bulkhead từ chối request, mà không có code nào ở package này phụ thuộc vào package kia.

#### Chạy thử <a id="try-it"></a>

Khởi động ứng dụng với `CARRIER_URL` trỏ tới một stub đơn vị vận chuyển mà bạn kiểm soát, chẳng hạn một mock server hoặc vài dòng `node:http`. Trong khi đơn vị vận chuyển còn trả lời, checkout nhận báo giá thật:

```bash
$ curl "localhost:3000/shipping/quotes?orderId=1001"
[{"service":"ground","price":6.9,"estimatedDays":4},{"service":"express","price":14.5,"estimatedDays":1}]
```

Giờ hãy làm stub bị treo. Cùng request đó trả về `504` sau khoảng 3 giây, và stub thấy cả hai request của nó bị hủy:

```bash
$ curl "localhost:3000/shipping/quotes?orderId=1001"
{"statusCode":504,"error":"Gateway Timeout","message":"The operation timed out","code":"TIMEOUT"}
```

Tiếp tục gửi. Mỗi request ghi nhận hai lần thử thất bại. Tới request chậm thứ năm, breaker có 10 lời gọi trong cửa sổ và 9 trong số đó thất bại. Breaker mở, lần thử thứ hai của request bị reject, và fallback trả lời. Ứng dụng log ra:

```bash
WARN [Resilience] Circuit "carrier" went from closed to open
LOG [Resilience] ShippingController.getQuotes answered with its fallback
```

Từ giờ, việc đặt vận chuyển thất bại ngay mà không gọi đơn vị vận chuyển:

```bash
$ curl -i -X POST localhost:3000/shipping/shipments \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: 5f1c2a9e-shipment-1001" \
    -d '{"orderId":"1001"}'
HTTP/1.1 503 Service Unavailable
Retry-After: 30

{"statusCode":503,"error":"Service Unavailable","message":"Service temporarily unavailable","code":"CIRCUIT_OPEN"}
```

Trong khi đó, báo giá trả lời ngay lập tức với giá đồng giá:

```bash
$ curl "localhost:3000/shipping/quotes?orderId=1002"
[{"service":"flat-rate","price":4.99,"estimatedDays":5}]
```

Cho stub trả lời trở lại và chờ 30 giây. Request báo giá tiếp theo là lời gọi thăm dò. Nó thành công, nên breaker đóng lại và checkout lại hiển thị báo giá thật:

```bash
WARN [Resilience] Circuit "carrier" went from open to half-open
WARN [Resilience] Circuit "carrier" went from half-open to closed
```

Lặp lại việc đặt vận chuyển với cùng `Idempotency-Key` giờ sẽ tạo đơn vận chuyển và trả về `201`. Lần 503 trước đó đã giải phóng key.

#### Testing

Hành vi resilience rất đáng để test, nhưng không phải bằng cách chờ 30 giây cho một breaker. Hãy thay `CarrierClient` bằng một bản giả, và dùng fake timer của Vitest cho đồng hồ. Chỉ giả lập `setTimeout`, `clearTimeout` và `Date`, để HTTP server và supertest vẫn hoạt động với I/O thật:

```typescript
@@filename(test/shipping.e2e-spec)
import type { INestApplication } from '@nestjs/common';
import { ResilienceService } from '@nestjs/resilience';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppModule } from '../src/app.module.js';
import { CarrierClient } from '../src/shipping/carrier.client.js';

const liveQuotes = [{ service: 'ground', price: 6.9, estimatedDays: 4 }];

/** A carrier call that only ends when its signal aborts. */
const hang = (_order: unknown, signal: AbortSignal) =>
  new Promise((_, reject) => signal.addEventListener('abort', () => reject(signal.reason)));

describe('Shipping quotes', () => {
  let app: INestApplication;
  const carrier = { getQuotes: vi.fn(), createShipment: vi.fn() };

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(CarrierClient)
      .useValue(carrier)
      .compile();
    app = moduleRef.createNestApplication({ logger: false });
    await app.listen(0, '127.0.0.1');
    // Fake only timers and Date: the HTTP server and supertest keep real I/O.
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
  });

  afterEach(async () => {
    vi.useRealTimers();
    vi.resetAllMocks();
    await app.close();
  });

  it('answers 504 and cancels the carrier call when the carrier hangs', async () => {
    carrier.getQuotes.mockImplementation(hang);

    // .then() sends the request now; the clock only moves when we advance it.
    const response = request(app.getHttpServer())
      .get('/shipping/quotes?orderId=1001')
      .then((res) => res);
    await vi.waitFor(() => expect(carrier.getQuotes).toHaveBeenCalled());
    await vi.advanceTimersByTimeAsync(5_000); // two attempts of 1.5 s, plus backoff

    expect((await response).status).toBe(504);
    expect(carrier.getQuotes).toHaveBeenCalledTimes(2);
    const [, signal] = carrier.getQuotes.mock.calls[0];
    expect(signal.aborted).toBe(true);
  });

  it('serves flat rates while the breaker is open, then recovers', async () => {
    carrier.getQuotes.mockResolvedValue(liveQuotes);
    const breaker = app.get(ResilienceService).circuitBreaker('carrier');
    breaker.trip();

    const fallback = await request(app.getHttpServer()).get('/shipping/quotes?orderId=1001');
    expect(fallback.body).toEqual([
      { service: 'flat-rate', price: 4.99, estimatedDays: 5 },
    ]);
    expect(carrier.getQuotes).not.toHaveBeenCalled();

    vi.advanceTimersByTime(30_000); // openDuration: the next call is a probe
    const live = await request(app.getHttpServer()).get('/shipping/quotes?orderId=1001');
    expect(live.body).toEqual(liveQuotes);
    expect(breaker.state).toBe('closed');
  });
});
```

Có vài điểm giúp cách này hoạt động:

- `vi.waitFor()` chờ cho tới khi request thực sự tới được đơn vị vận chuyển. Chỉ khi đó mới có timer để tua tới. Khi bật fake timer, `vi.waitFor()` cũng dịch đồng hồ theo khoảng thời gian polling của nó (50 ms), vẫn nằm gọn trong ngân sách 1.5 giây.
- `vi.advanceTimersByTimeAsync()` kích hoạt các timeout và backoff theo thứ tự, và để các promise ở giữa kịp settle.
- `trip()` mở breaker trực tiếp, nên bạn không phải tạo ra mười lần thất bại để test trạng thái open. Vì breaker so `openDuration` với `Date` ở lời gọi tiếp theo, chỉ cần tua đồng hồ giả về phía trước là đủ để lời gọi đó trở thành lời gọi thăm dò.
- Breaker, bulkhead và giới hạn tần suất gọi ra ngoài thuộc về ứng dụng đã tạo ra chúng, nên mỗi ứng dụng test đều bắt đầu với trạng thái mới.
- Để test với các thiết lập khác, chẳng hạn `openDuration` ngắn hơn, hãy override tùy chọn của module bằng `overrideProvider(RESILIENCE_MODULE_OPTIONS)`.

Xem [End-to-end testing](/fundamentals/testing#end-to-end-testing) để nắm kiến thức testing cơ bản.
#### Checklist cho production <a id="production-checklist"></a>

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

#### Tham khảo <a id="reference"></a>

##### Tùy chọn của module <a id="module-options"></a>

`ResilienceModule.forRoot()` nhận các tùy chọn sau. `forRootAsync()` dựng cùng object đó từ một factory, một class implement `ResilienceOptionsFactory`, hoặc một provider có sẵn.

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `defaults` | `ResilienceDefaults` | không có | Giá trị mặc định cho các field của `retry`, `timeout`, `circuitBreaker` và `bulkhead`. Chúng điền vào các stage mà một decorator hoặc preset bật lên, và không bao giờ tự bật một stage. Xem [Đăng ký module](/reliability/resilience#register-the-module). |
| `presets` | `Record<string, ResiliencePreset>` | không có | Các tập stage có tên: `retry`, `timeout`, `circuitBreaker`, `bulkhead`, `outboundRateLimit` và `fallback`. Breaker, bulkhead và giới hạn tần suất gọi ra ngoài của một preset được dùng chung dưới tên của preset. |
| `mapErrors` | `boolean` | `true` | Chuyển các lỗi resilience do bất kỳ handler nào throw, có hay không có decorator, thành lỗi của transport, như liệt kê trong phần Lỗi bên dưới. |
| `isGlobal` | `boolean` | `true` | Đăng ký module ở phạm vi global. Chỉ đăng ký một lần, trong root module. |

Mọi tùy chọn mang giá trị thời gian đều nhận số mili giây hoặc một chuỗi như `'200ms'`, `'2s'` hay `'15m'`. Injection token của các tùy chọn là `RESILIENCE_MODULE_OPTIONS`.

##### Decorator <a id="decorators"></a>

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

##### Event <a id="events"></a>

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

##### Lỗi <a id="errors"></a>

Mọi lỗi đều kế thừa `ResilienceError`, có một `code` và tên `policy`.

| Lỗi | Code | HTTP | Message gửi tới client | Field |
| --- | --- | --- | --- | --- |
| `ResilienceTimeoutError` | `TIMEOUT` | 504 | The operation timed out | `timeoutMs` |
| `CircuitOpenError` | `CIRCUIT_OPEN` | 503, kèm `Retry-After` | Service temporarily unavailable | `retryAfterMs` |
| `BulkheadFullError` | `BULKHEAD_FULL` | 503 | Server is at capacity | `reason` |
| `OutboundRateLimitError` | `RATE_LIMITED` | 503, kèm `Retry-After` | Rate limit of a dependency exceeded | `retryAfterMs` |

Trên microservice và WebSocket handler, lỗi là một `RpcException` hoặc `WsException` có payload gồm `status`, `code`, `statusCode`, `message` và, với những lần reject biết được giá trị này, `retryAfter` tính bằng giây. Trên GraphQL, lỗi của field có `code`, `httpStatus` và `retryAfter` trong `extensions` (xem [Các transport khác](/reliability/resilience#other-transports)).
