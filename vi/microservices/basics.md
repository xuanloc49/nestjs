### Tổng quan

Ngoài các kiến trúc ứng dụng truyền thống (đôi khi gọi là nguyên khối), Nest hỗ trợ sẵn phong cách phát triển theo kiến trúc microservice. Phần lớn các khái niệm được bàn ở những phần khác trong tài liệu này, như dependency injection, decorator, exception filter, pipe, guard và interceptor, đều áp dụng tương tự cho microservice. Ở bất cứ đâu có thể, Nest trừu tượng hóa các chi tiết hiện thực để cùng các thành phần có thể chạy trên các nền tảng dựa trên HTTP, WebSocket và microservice. Phần này nói về những khía cạnh của Nest dành riêng cho microservice.

Trong Nest, về cơ bản một microservice là một ứng dụng dùng một lớp **transport** khác HTTP.

<figure><img class="illustrative-image" src="/assets/Microservices_1.png" /></figure>

Nest hỗ trợ sẵn một số phần hiện thực lớp transport, gọi là **transporter**, chịu trách nhiệm truyền message giữa các instance microservice khác nhau. Phần lớn transporter hỗ trợ sẵn cả hai kiểu message **request-response** và **event-based**. Nest trừu tượng hóa chi tiết hiện thực của từng transporter phía sau một interface chuẩn cho cả hai kiểu. Điều này cho phép bạn chuyển từ lớp transport này sang lớp transport khác (ví dụ để tận dụng các tính năng về độ tin cậy hay hiệu năng của một lớp transport cụ thể) mà không cần thay đổi code ứng dụng.

#### Cài đặt <a id="installation"></a>

Để bắt đầu xây dựng microservice, trước tiên hãy cài package cần thiết:

```bash
$ npm i --save @nestjs/microservices
```

#### Bắt đầu <a id="getting-started"></a>

Để khởi tạo một microservice, hãy dùng method `createMicroservice()` của class `NestFactory`:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    {
      transport: Transport.TCP,
    },
  );
  await app.listen();
}
await bootstrap();
@@switch
import { NestFactory } from '@nestjs/core';
import { Transport } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.createMicroservice(AppModule, {
    transport: Transport.TCP,
  });
  await app.listen();
}
await bootstrap();
```

> info **Gợi ý** Microservice mặc định dùng lớp transport **TCP**.

Tham số thứ hai của method `createMicroservice()` là một object `options` gồm hai thành phần:

<table>
  <tr>
    <td><code>transport</code></td>
    <td>Chỉ định transporter (ví dụ <code>Transport.NATS</code>)</td>
  </tr>
  <tr>
    <td><code>options</code></td>
    <td>Một options object riêng của transporter, quyết định hành vi của transporter</td>
  </tr>
</table>
<p>
  Object <code>options</code> phụ thuộc vào transporter được chọn. Transporter <strong>TCP</strong> cung cấp
  các thuộc tính được mô tả bên dưới. Với các transporter khác (ví dụ Redis hoặc MQTT), hãy xem chương tương ứng để biết mô tả các tùy chọn có sẵn.
</p>
<table>
  <tr>
    <td><code>host</code></td>
    <td>Hostname của kết nối</td>
  </tr>
  <tr>
    <td><code>port</code></td>
    <td>Port của kết nối</td>
  </tr>
  <tr>
    <td><code>retryAttempts</code></td>
    <td>Số lần server thử lắng nghe lại sau khi nó bị đóng bất ngờ (mặc định: <code>0</code>)</td>
  </tr>
  <tr>
    <td><code>retryDelay</code></td>
    <td>Độ trễ giữa các lần thử đó (ms) (mặc định: <code>0</code>)</td>
  </tr>
  <tr>
    <td><code>serializer</code></td>
    <td><a href="https://github.com/nestjs/nest/blob/master/packages/microservices/interfaces/serializer.interface.ts" target="_blank">Serializer</a> tùy chỉnh cho message gửi đi</td>
  </tr>
  <tr>
    <td><code>deserializer</code></td>
    <td><a href="https://github.com/nestjs/nest/blob/master/packages/microservices/interfaces/deserializer.interface.ts" target="_blank">Deserializer</a> tùy chỉnh cho message đi vào</td>
  </tr>
  <tr>
    <td><code>socketClass</code></td>
    <td>Một Socket tùy chỉnh kế thừa <code>TcpSocket</code> (mặc định: <code>JsonSocket</code>)</td>
  </tr>
  <tr>
    <td><code>tlsOptions</code></td>
    <td>Các tùy chọn để cấu hình giao thức TLS (xem <a href="/microservices/basics#tls-support">Hỗ trợ TLS</a>)</td>
  </tr>
  <tr>
    <td><code>maxBufferSize</code></td>
    <td>Kích thước tối đa của buffer cho message đi vào, tính bằng ký tự (mặc định: <code>(512 * 1024 * 1024) / 4</code>)</td>
  </tr>
  <tr>
    <td><code>incompleteMessageTimeout</code></td>
    <td>Thời gian (ms) mà một peer được phép im lặng giữa chừng một packet trước khi kết nối bị ngắt. Đặt thành <code>0</code> để tắt (mặc định: <code>30000</code>)</td>
  </tr>
  <tr>
    <td><code>maxSendBufferSize</code></td>
    <td>Số byte response tối đa có thể được xếp hàng cho một peer không đọc chúng trước khi kết nối bị ngắt. Đặt thành <code>0</code> để tắt (mặc định: 128MB)</td>
  </tr>
</table>

#### Message pattern và event pattern <a id="message-and-event-patterns"></a>

Microservice nhận diện cả message lẫn event theo **pattern**. Một pattern là một giá trị thuần, ví dụ một object literal hoặc một chuỗi. Pattern được tự động serialize và gửi qua mạng cùng phần dữ liệu của message. Bằng cách này, bên gửi và bên tiêu thụ message có thể phối hợp xem request nào được handler nào tiêu thụ.

#### Request-response

Kiểu message request-response hữu ích khi bạn cần **trao đổi** message giữa các service. Nó đảm bảo service thực sự đã nhận được message, mà không cần bạn tự hiện thực một giao thức acknowledgment. Tuy nhiên, request-response không phải lúc nào cũng phù hợp nhất. Ví dụ, các nền tảng streaming dùng persistence dựa trên log, như [Kafka](https://docs.confluent.io/3.0.0/streams/) hay [NATS JetStream](https://docs.nats.io/nats-concepts/jetstream), được tối ưu cho một tập thách thức khác, gần với mô hình event messaging hơn (xem [event-based messaging](/microservices/basics#event-based) để biết thêm chi tiết).

Để bật kiểu message request-response, Nest tạo hai kênh logic: một để truyền dữ liệu và một để chờ các response đi tới. Với một số transport bên dưới, như [NATS](https://nats.io/), việc hỗ trợ hai kênh này có sẵn. Với các transport khác, Nest bù lại bằng cách tự tạo các kênh riêng, điều này có thể gây thêm chi phí. Nếu bạn không cần kiểu message request-response, hãy cân nhắc dùng cách event-based thay vào đó.

Để tạo một message handler theo mô hình request-response, hãy dùng decorator `@MessagePattern()`, được import từ package `@nestjs/microservices`. Chỉ dùng decorator này bên trong các class [controller](/controllers), vì chúng là các entry point của ứng dụng. Runtime của Nest bỏ qua nó trong provider.

```typescript
@@filename(math.controller)
import { Controller } from '@nestjs/common';
import { MessagePattern } from '@nestjs/microservices';

@Controller()
export class MathController {
  @MessagePattern({ cmd: 'sum' })
  accumulate(data: number[]): number {
    return (data || []).reduce((a, b) => a + b);
  }
}
@@switch
import { Controller } from '@nestjs/common';
import { MessagePattern } from '@nestjs/microservices';

@Controller()
export class MathController {
  @MessagePattern({ cmd: 'sum' })
  accumulate(data) {
    return (data || []).reduce((a, b) => a + b);
  }
}
```

Trong đoạn code ở trên, **message handler** `accumulate()` lắng nghe các message khớp với message pattern `{{ '{' }} cmd: 'sum' {{ '}' }}`. Message handler nhận một tham số duy nhất, `data` được truyền từ client. Trong trường hợp này, data là một mảng số cần được cộng dồn.

#### Response bất đồng bộ <a id="asynchronous-responses"></a>

Message handler có thể phản hồi đồng bộ hoặc **bất đồng bộ**, nên các method `async` đều được hỗ trợ.

```typescript
@@filename()
@MessagePattern({ cmd: 'sum' })
async accumulate(data: number[]): Promise<number> {
  return (data || []).reduce((a, b) => a + b);
}
@@switch
@MessagePattern({ cmd: 'sum' })
async accumulate(data) {
  return (data || []).reduce((a, b) => a + b);
}
```

Một message handler cũng có thể trả về một `Observable`, khi đó các giá trị kết quả được phát ra cho tới khi stream hoàn tất.

```typescript
@@filename()
@MessagePattern({ cmd: 'sum' })
accumulate(data: number[]): Observable<number> {
  return from([1, 2, 3]);
}
@@switch
@MessagePattern({ cmd: 'sum' })
accumulate(data) {
  return from([1, 2, 3]);
}
```

Trong ví dụ ở trên, message handler phản hồi **ba lần**, mỗi phần tử trong mảng một lần.

#### Event-based

Dù cách request-response hoạt động tốt cho việc trao đổi message giữa các service, nó lại kém phù hợp với event-based messaging, khi bạn muốn publish **event** mà không chờ response. Trong những trường hợp như vậy, chi phí duy trì hai kênh cho request-response là không cần thiết.

Ví dụ, nếu bạn muốn thông báo cho một service khác rằng một điều kiện cụ thể đã xảy ra ở phần này của hệ thống, hãy dùng kiểu message event-based.

Để tạo một event handler, hãy dùng decorator `@EventPattern()`, được import từ package `@nestjs/microservices`.

```typescript
@@filename()
@EventPattern('user_created')
async handleUserCreated(data: Record<string, unknown>) {
  // business logic
}
@@switch
@EventPattern('user_created')
async handleUserCreated(data) {
  // business logic
}
```

> info **Gợi ý** Bạn có thể đăng ký nhiều event handler cho **một** event pattern, và Nest kích hoạt tất cả chúng song song.

**Event handler** `handleUserCreated()` lắng nghe event `'user_created'`. Event handler nhận một tham số duy nhất, `data` được truyền từ client (trong trường hợp này là một event payload được gửi qua mạng).

<app-banner-enterprise></app-banner-enterprise>

#### Chi tiết bổ sung của request <a id="additional-request-details"></a>

Trong các tình huống nâng cao hơn, bạn có thể cần thêm chi tiết về request đi vào. Chẳng hạn, khi dùng NATS với wildcard subscription, bạn có thể muốn lấy subject gốc mà producer đã gửi message tới. Tương tự, với Kafka, bạn có thể cần truy cập các header của message. Để làm vậy, hãy dùng các decorator có sẵn như bên dưới:

```typescript
@@filename()
@MessagePattern('time.us.*')
getDate(@Payload() data: number[], @Ctx() context: NatsContext) {
  console.log(`Subject: ${context.getSubject()}`); // e.g. "time.us.east"
  return new Date().toLocaleTimeString(...);
}
@@switch
@Bind(Payload(), Ctx())
@MessagePattern('time.us.*')
getDate(data, context) {
  console.log(`Subject: ${context.getSubject()}`); // e.g. "time.us.east"
  return new Date().toLocaleTimeString(...);
}
```

> info **Gợi ý** `@Payload()`, `@Ctx()` và `NatsContext` được import từ `@nestjs/microservices`.

> info **Gợi ý** Bạn cũng có thể truyền một property key cho decorator `@Payload()` để lấy một thuộc tính cụ thể từ payload object đi vào, ví dụ `@Payload('id')`. Để validate payload theo một schema, xem [pipe của microservice](/microservices/pipes).

#### Client (class producer) <a id="client-producer-class"></a>

Một ứng dụng Nest phía client có thể trao đổi message với, hoặc publish event tới, một microservice Nest bằng class `ClientProxy`. Class này cung cấp một số method để giao tiếp với một microservice từ xa, như `send()` (cho messaging request-response) và `emit()` (cho messaging hướng event). Bạn có thể lấy một instance của class này theo các cách sau.

Một cách là import `ClientsModule`, module này cung cấp static method `register()`. Method này nhận một mảng object đại diện cho các transporter của microservice. Mỗi object phải có thuộc tính `name`, và có thể có thuộc tính `transport` (nếu bỏ qua, Nest dùng `Transport.TCP`) và thuộc tính `options`.

Thuộc tính `name` đóng vai trò một **injection token**, bạn có thể dùng nó để inject một instance `ClientProxy` ở bất cứ đâu cần. Giá trị của nó có thể là bất kỳ chuỗi hoặc JavaScript symbol nào, như mô tả trong [provider token không dựa trên class](/fundamentals/custom-providers#non-class-based-provider-tokens).

Thuộc tính `options` là một object có cùng các thuộc tính mà chúng ta đã thấy trong method `createMicroservice()` trước đó.

```typescript
@Module({
  imports: [
    ClientsModule.register([
      { name: 'MATH_SERVICE', transport: Transport.TCP },
    ]),
  ],
})
```

Ngoài ra, hãy dùng method `registerAsync()` nếu bạn cần cung cấp cấu hình hoặc thực hiện các xử lý bất đồng bộ khác trong lúc thiết lập.

```typescript
@Module({
  imports: [
    ClientsModule.registerAsync([
      {
        imports: [ConfigModule],
        name: 'MATH_SERVICE',
        useFactory: async (configService: ConfigService) => ({
          transport: Transport.TCP,
          options: {
            host: configService.get('HOST'),
            port: configService.get('PORT'),
          },
        }),
        inject: [ConfigService],
      },
    ]),
  ],
})
```

Khi module đã được import, hãy dùng decorator `@Inject()` để inject instance `ClientProxy` được cấu hình cho transporter `'MATH_SERVICE'`.

```typescript
constructor(
  @Inject('MATH_SERVICE') private client: ClientProxy,
) {}
```

> info **Gợi ý** Các class `ClientsModule` và `ClientProxy` được import từ package `@nestjs/microservices`.

Đôi khi, bạn có thể cần lấy cấu hình transporter từ một service khác (như `ConfigService`) thay vì hardcode nó trong ứng dụng client. Để làm vậy, hãy đăng ký một [custom provider](/fundamentals/custom-providers) bằng class `ClientProxyFactory`. Class này cung cấp static method `create()` nhận một options object của transporter và trả về một instance `ClientProxy` đã được tùy chỉnh.

```typescript
@Module({
  providers: [
    {
      provide: 'MATH_SERVICE',
      useFactory: (configService: ConfigService) => {
        const mathSvcOptions = configService.getMathSvcOptions();
        return ClientProxyFactory.create(mathSvcOptions);
      },
      inject: [ConfigService],
    }
  ]
  ...
})
```

> info **Gợi ý** Class `ClientProxyFactory` được import từ package `@nestjs/microservices`.

Một lựa chọn khác là dùng property decorator `@Client()`.

```typescript
@Client({ transport: Transport.TCP })
client: ClientProxy;
```

> info **Gợi ý** Decorator `@Client()` được import từ package `@nestjs/microservices`.

Decorator `@Client()` không phải là kỹ thuật được ưu tiên, vì một client được tạo theo cách này khó test hơn và khó dùng chung hơn.

`ClientProxy` là **lazy**. Nó không khởi tạo kết nối ngay lập tức. Thay vào đó, kết nối được thiết lập trước lời gọi microservice đầu tiên và được tái sử dụng cho mỗi lời gọi tiếp theo. Nếu bạn muốn trì hoãn quá trình bootstrap ứng dụng cho tới khi kết nối được thiết lập, hãy tự khởi tạo kết nối bằng method `connect()` của object `ClientProxy` bên trong lifecycle hook `onApplicationBootstrap()`.

```typescript
@@filename()
async onApplicationBootstrap() {
  await this.client.connect();
}
```

Nếu không tạo được kết nối, method `connect()` sẽ reject với object lỗi tương ứng.

#### Gửi message <a id="sending-messages"></a>

`ClientProxy` cung cấp method `send()`, method này gọi microservice và trả về một `Observable` chứa response của nó.

```typescript
@@filename()
accumulate(): Observable<number> {
  const pattern = { cmd: 'sum' };
  const payload = [1, 2, 3];
  return this.client.send<number>(pattern, payload);
}
@@switch
accumulate() {
  const pattern = { cmd: 'sum' };
  const payload = [1, 2, 3];
  return this.client.send(pattern, payload);
}
```

Method `send()` nhận hai tham số, `pattern` và `payload`. `pattern` phải khớp với một pattern được định nghĩa trong decorator `@MessagePattern()`. `payload` là message cần truyền tới microservice từ xa. Method này trả về một **cold `Observable`**, nghĩa là bạn phải subscribe nó một cách tường minh trước khi message được gửi đi.

#### Publish event <a id="publishing-events"></a>

Để gửi một event, hãy dùng method `emit()` của object `ClientProxy`. Method này publish một event tới message broker.

```typescript
@@filename()
async publish() {
  this.client.emit<number>('user_created', new UserCreatedEvent());
}
@@switch
async publish() {
  this.client.emit('user_created', new UserCreatedEvent());
}
```

Method `emit()` nhận hai tham số, `pattern` và `payload`. `pattern` phải khớp với một pattern được định nghĩa trong decorator `@EventPattern()`, còn `payload` là dữ liệu event cần truyền tới microservice từ xa. Method này trả về một **hot `Observable`** (ngược với cold `Observable` mà `send()` trả về), nghĩa là proxy sẽ cố gửi event ngay lập tức, dù bạn có subscribe observable hay không.

<app-banner-observe></app-banner-observe>

#### Request-scoping

Nếu bạn đến từ một nền tảng ngôn ngữ lập trình khác, có thể bạn sẽ ngạc nhiên rằng trong Nest, phần lớn mọi thứ được dùng chung giữa các request đi vào. Điều này bao gồm connection pool của database, các singleton service có trạng thái global, và nhiều thứ khác. Node.js không theo mô hình stateless đa luồng request/response, trong đó mỗi request được xử lý bởi một thread riêng. Vì vậy, việc dùng singleton instance là **an toàn** cho ứng dụng của bạn.

Tuy nhiên, có những trường hợp đặc biệt mà vòng đời theo request cho handler có thể là điều mong muốn, như cache theo từng request trong ứng dụng GraphQL, theo dõi request, hoặc multi-tenancy. Tìm hiểu cách kiểm soát scope trong chương [injection scope](/fundamentals/injection-scopes).

Các handler và provider request-scoped có thể inject `RequestContext` bằng decorator `@Inject()` kết hợp với token `CONTEXT`:

```typescript
import { Injectable, Scope, Inject } from '@nestjs/common';
import { CONTEXT, type RequestContext } from '@nestjs/microservices';

@Injectable({ scope: Scope.REQUEST })
export class CatsService {
  constructor(@Inject(CONTEXT) private ctx: RequestContext) {}
}
```

Điều này cho phép truy cập object `RequestContext`, có cấu trúc như sau:

```typescript
export interface RequestContext<TData = any, TContext extends BaseRpcContext = any> {
  pattern: string | Record<string, any>;
  data: TData;
  context?: TContext;
  getData(): TData;
  getPattern(): string | Record<string, any>;
  getContext(): TContext;
}
```

Thuộc tính `data` là payload của message do producer gửi. Thuộc tính `pattern` là pattern được dùng để xác định handler cho message đi vào. Thuộc tính `context` chứa context object riêng của transporter (ví dụ `NatsContext`), chính là object mà decorator `@Ctx()` inject.

#### Cập nhật trạng thái instance <a id="instance-status-updates"></a>

Để nhận cập nhật real-time về kết nối và trạng thái của instance driver bên dưới, hãy subscribe stream `status`. Stream này cung cấp các cập nhật trạng thái riêng của driver được chọn. Chẳng hạn, với transporter TCP (mặc định), stream `status` phát ra các event `connected` và `disconnected`.

```typescript
this.client.status.subscribe((status: TcpStatus) => {
  console.log(status);
});
```

> info **Gợi ý** Type `TcpStatus` được import từ package `@nestjs/microservices`.

Tương tự, bạn có thể subscribe stream `status` của server để nhận thông báo về trạng thái của server.

```typescript
const server = app.connectMicroservice<MicroserviceOptions>(...);
server.status.subscribe((status: TcpStatus) => {
  console.log(status);
});
```

#### Lắng nghe các event nội bộ <a id="listening-to-internal-events"></a>

Trong một số trường hợp, bạn có thể muốn lắng nghe các event nội bộ do microservice phát ra. Ví dụ, bạn có thể lắng nghe event `error` để kích hoạt thêm các thao tác khi có lỗi xảy ra. Để làm vậy, hãy dùng method `on()`:

```typescript
this.client.on('error', (err) => {
  console.error(err);
});
```

Tương tự, bạn có thể lắng nghe các event nội bộ của server:

```typescript
server.on<TcpEvents>('error', (err) => {
  console.error(err);
});
```

> info **Gợi ý** Type `TcpEvents` được import từ package `@nestjs/microservices`.

Với transporter TCP, bắt đầu từ NestJS v12.1.1, các listener được đăng ký bằng method `on()` của client vẫn được giữ cho tới khi bạn gọi `close()`, nên chúng cũng được gắn vào socket mới mà client mở ở lời gọi `send()` hoặc `emit()` tiếp theo sau khi kết nối đã bị đóng. Các lần đăng ký không được khử trùng lặp, nên hãy đăng ký mỗi listener một lần thay vì đăng ký lại từ callback của nó hoặc sau mỗi lần kết nối lại.

#### Truy cập driver bên dưới <a id="underlying-driver-access"></a>

Với các use case nâng cao hơn, bạn có thể cần truy cập instance driver bên dưới, ví dụ để tự đóng kết nối hoặc dùng các method riêng của driver. Tuy nhiên, trong hầu hết các trường hợp, bạn **không cần** truy cập trực tiếp driver.

Để làm vậy, hãy dùng method `unwrap()`, method này trả về instance driver bên dưới. Generic type parameter chỉ định type của instance driver mà bạn mong đợi.

```typescript
const netSocket = this.client.unwrap<Socket>();
```

Ở đây, `Socket` là một type được import từ module `net`.

Tương tự, bạn có thể truy cập instance driver bên dưới của server:

```typescript
const netServer = server.unwrap<Server>();
```

#### Xử lý timeout <a id="handling-timeouts"></a>

Trong các hệ thống phân tán, đôi khi microservice bị down hoặc không khả dụng. Để tránh phải chờ vô hạn, hãy áp dụng một timeout cho các lời gọi microservice bằng operator `timeout` của [RxJS](https://rxjs.dev). Nếu microservice không phản hồi trong khoảng thời gian chỉ định, một lỗi sẽ được throw, bạn có thể bắt và xử lý nó cho phù hợp.

Áp dụng operator `timeout` bên trong pipe:

```typescript
@@filename()
this.client
  .send<TResult, TInput>(pattern, data)
  .pipe(timeout(5000));
@@switch
this.client
  .send(pattern, data)
  .pipe(timeout(5000));
```

> info **Gợi ý** Operator `timeout` được import từ package `rxjs/operators`.

Nếu microservice không phản hồi trong vòng 5 giây, `Observable` sẽ báo lỗi với một `TimeoutError`.

#### Trace một request xuyên qua các service <a id="tracing-a-request-across-services"></a>

Timeout cho bạn biết một lời gọi đã không quay về kịp. Chúng không cho bạn biết thời gian đã đi *đâu*, và trong một hệ thống năm service giao tiếp qua TCP, NATS và Kafka, đó mới là câu hỏi quan trọng. Một request ở gateway mất 3 giây có thể đã tiêu 2.9 giây trong đó ở một service phía sau mà không ai nghi ngờ, trong khi log riêng của từng service đều cho thấy mọi thứ có vẻ ổn.

Cách sửa thông thường là tự truyền một correlation ID qua mọi transport, rồi ghép các dòng thời gian lại với nhau sau đó. [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') làm việc ghép nối đó cho bạn. Hãy instrument mỗi service bằng SDK `@nestjs/observe` và chuyển tiếp trace ID trên bất kỳ kênh nào mà transport đã có (một Kafka header, một NATS header, hoặc một field trong TCP payload), và dashboard sẽ dựng lại một waterfall trải dài qua mọi service đã tham gia:

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/service-flow.webp" alt="Liên kết trace giữa các service" /></figure>

Từ đó, timeout không còn là một điều bí ẩn. Bạn có thể thấy `send()` của gateway đang chờ, consumer nhận message (và message đã chờ bao lâu trước đó), query bên trong handler đã chạy lâu, và lỗi mà cuối cùng nó throw, kèm các dòng mã nguồn, tất cả trên cùng một trục thời gian. Message handler và event handler được instrument tự động, nên các handler `@MessagePattern()` và `@EventPattern()` hiện ra dưới dạng operation mà không cần tự nối span nào.

Chuyển tiếp trace ID là phần duy nhất cần code ứng dụng, vì chỉ bạn mới biết transport của mình còn để trống kênh nào. Xem [Distributed tracing](/observability/distributed-tracing) để biết pattern cho từng transport, và chương [Observability](/observability/overview) để bắt đầu thiết lập.

#### Hỗ trợ TLS <a id="tls-support"></a>

Khi giao tiếp bên ngoài một mạng riêng, hãy mã hóa lưu lượng. Transporter TCP hỗ trợ sẵn TLS, dựa trên module [TLS](https://nodejs.org/api/tls.html) của Node, cho phép bạn mã hóa giao tiếp giữa các microservice và client của chúng.

Để bật TLS cho một TCP server, bạn cần cả private key lẫn certificate ở định dạng PEM. Thêm chúng vào tùy chọn của server bằng thuộc tính `tlsOptions`:

```typescript
import * as fs from 'node:fs';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';

async function bootstrap() {
  const key = fs.readFileSync('<pathToKeyFile>', 'utf8').toString();
  const cert = fs.readFileSync('<pathToCertFile>', 'utf8').toString();

  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    {
      transport: Transport.TCP,
      options: {
        tlsOptions: {
          key,
          cert,
        },
      },
    },
  );

  await app.listen();
}
await bootstrap();
```

Để một client giao tiếp an toàn qua TLS, hãy định nghĩa cả object `tlsOptions`, lần này với CA certificate, tức certificate của tổ chức đã ký certificate của server. Điều này đảm bảo client tin tưởng certificate của server và có thể thiết lập một kết nối an toàn.

```typescript
import * as fs from 'node:fs';
import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'MATH_SERVICE',
        transport: Transport.TCP,
        options: {
          tlsOptions: {
            ca: [fs.readFileSync('<pathToCaFile>', 'utf-8').toString()],
          },
        },
      },
    ]),
  ],
})
export class AppModule {}
```

Thuộc tính `ca` nhận một mảng, nên bạn có thể liệt kê nhiều CA nếu cách thiết lập của bạn có nhiều tổ chức tin cậy.

Khi mọi thứ đã được thiết lập, hãy inject `ClientProxy` như thường lệ bằng decorator `@Inject()`. Khi đó giao tiếp giữa các microservice của bạn được mã hóa, với module TLS của Node lo các chi tiết mã hóa.

Để biết thêm thông tin, hãy tham khảo [tài liệu TLS](https://nodejs.org/api/tls.html) của Node.

#### Cấu hình động <a id="dynamic-configuration"></a>

Các tùy chọn transport của một microservice được truyền cho `createMicroservice()`, trước khi bất kỳ provider nào (như `ConfigService` từ package `@nestjs/config`) có thể được inject. Để cấu hình microservice bằng các provider được inject, hãy truyền `AsyncMicroserviceOptions` thay vào đó: Nest resolve các provider được liệt kê trong `inject` và truyền chúng cho hàm `useFactory`, hàm này trả về các tùy chọn transport.

```typescript
import { NestFactory } from '@nestjs/core';
import { ConfigService } from '@nestjs/config';
import { AsyncMicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<AsyncMicroserviceOptions>(
    AppModule,
    {
      useFactory: (configService: ConfigService) => ({
        transport: Transport.TCP,
        options: {
          host: configService.get<string>('HOST'),
          port: configService.get<number>('PORT'),
        },
      }),
      inject: [ConfigService],
    },
  );

  await app.listen();
}
await bootstrap();
```
