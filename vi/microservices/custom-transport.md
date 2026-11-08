### Custom transporter

Nest cung cấp sẵn nhiều **transporter**, cùng với một API để xây dựng các transport strategy tùy chỉnh.
Transporter cho phép bạn kết nối các thành phần qua mạng bằng một lớp giao tiếp có thể cắm thay và một giao thức message đơn giản ở tầng ứng dụng (xem [bài viết đầy đủ](https://dev.to/nestjs/integrate-nestjs-with-external-services-using-microservice-transporters-part-1-p3)).

> info **Gợi ý** Xây dựng một microservice với Nest không nhất thiết có nghĩa là bạn phải dùng package `@nestjs/microservices`. Ví dụ, nếu bạn muốn giao tiếp với các service bên ngoài (chẳng hạn các microservice khác viết bằng ngôn ngữ khác), bạn có thể không cần mọi tính năng mà library `@nestjs/microservices` cung cấp.
> Nếu bạn không cần các decorator cho phép định nghĩa subscriber theo kiểu khai báo (`@EventPattern` hoặc `@MessagePattern`), việc chạy một [ứng dụng standalone](/standalone-applications) và tự quản lý kết nối cùng các subscription của channel là đủ cho hầu hết các use case, và cho bạn nhiều linh hoạt hơn.

Với một custom transporter, bạn có thể tích hợp bất kỳ hệ thống messaging hay giao thức nào (bao gồm Google Cloud Pub/Sub, Amazon Kinesis và các hệ thống khác), hoặc mở rộng một transporter đã có với các tính năng bổ sung (ví dụ [QoS](https://github.com/mqttjs/MQTT.js/blob/master/README.md#qos) cho MQTT).

> info **Gợi ý** Để hiểu rõ hơn cách các microservice Nest hoạt động và cách bạn có thể mở rộng khả năng của các transporter đã có, chúng tôi khuyên bạn đọc loạt bài [NestJS Microservices in Action](https://dev.to/johnbiundo/series/4724) và [Advanced NestJS Microservices](https://dev.to/nestjs/part-1-introduction-and-setup-1a2l).

#### Tạo một strategy <a id="creating-a-strategy"></a>

Trước tiên, hãy định nghĩa một class đại diện cho custom transporter của chúng ta:

```typescript
import { CustomTransportStrategy, Server } from '@nestjs/microservices';

class GoogleCloudPubSubServer
  extends Server
  implements CustomTransportStrategy
{
  /**
   * Triggered when you run "app.listen()".
   */
  listen(callback: () => void) {
    callback();
  }

  /**
   * Triggered on application shutdown.
   */
  close() {}

  /**
   * You can ignore this method if you don't want transporter users
   * to be able to register event listeners. Most custom implementations
   * will not need this.
   */
  on(event: string, callback: Function) {
    throw new Error('Method not implemented.');
  }

  /**
   * You can ignore this method if you don't want transporter users
   * to be able to retrieve the underlying native server. Most custom implementations
   * will not need this.
   */
  unwrap<T = never>(): T {
    throw new Error('Method not implemented.');
  }
}
```

> warning **Cảnh báo** Chương này không hiện thực một Google Cloud Pub/Sub server đầy đủ tính năng, vì việc đó đòi hỏi đi sâu vào các chi tiết kỹ thuật riêng của transporter.

Trong ví dụ ở trên, chúng ta đã khai báo class `GoogleCloudPubSubServer` và cung cấp các method `listen()` và `close()` mà interface `CustomTransportStrategy` yêu cầu.
Class của chúng ta cũng kế thừa class `Server` từ package `@nestjs/microservices`, class này cung cấp một số method hữu ích, như những method mà runtime của Nest dùng để đăng ký message handler. Ngoài ra, để mở rộng khả năng của một transport strategy đã có, bạn có thể kế thừa class server tương ứng, ví dụ `ServerRedis`.
Theo quy ước, chúng ta thêm hậu tố `"Server"` vào tên class, vì class này chịu trách nhiệm subscribe message và event (và phản hồi chúng, nếu cần).

Khi đã có class này, chúng ta có thể dùng custom strategy thay cho một transporter có sẵn:

```typescript
const app = await NestFactory.createMicroservice<MicroserviceOptions>(
  AppModule,
  {
    strategy: new GoogleCloudPubSubServer(),
  },
);
```

Thay vì truyền options object thông thường của transporter với các thuộc tính `transport` và `options`, chúng ta truyền một thuộc tính duy nhất, `strategy`, với giá trị là một instance của class custom transporter.

Quay lại class `GoogleCloudPubSubServer`. Trong một ứng dụng thực tế, method `listen()` sẽ thiết lập kết nối tới message broker hoặc service bên ngoài và đăng ký subscriber hoặc lắng nghe các channel cụ thể (còn method dọn dẹp `close()` sẽ gỡ các subscription và đóng kết nối).
Vì việc này đòi hỏi hiểu rõ cách các microservice Nest giao tiếp với nhau, chúng tôi khuyên bạn đọc [loạt bài Advanced NestJS Microservices](https://dev.to/nestjs/part-1-introduction-and-setup-1a2l).
Thay vào đó, chương này tập trung vào các khả năng mà class `Server` cung cấp và cách bạn có thể dùng chúng để xây dựng các strategy tùy chỉnh.

Ví dụ, giả sử message handler sau được định nghĩa ở đâu đó trong ứng dụng:

```typescript
@MessagePattern('echo')
echo(@Payload() data: object) {
  return data;
}
```

Runtime của Nest tự động đăng ký message handler này. Với class `Server`, bạn có thể xem những message pattern nào đã được đăng ký, và truy cập cũng như thực thi các method được gán cho chúng.
Để thử điều này, hãy thêm một lời gọi `console.log` bên trong method `listen()`, trước khi hàm `callback` được gọi:

```typescript
listen(callback: () => void) {
  console.log(this.messageHandlers);
  callback();
}
```

Sau khi ứng dụng restart, bạn sẽ thấy log sau trong terminal:

```text
Map(1) {
  'echo' => [AsyncFunction (anonymous)] { isEventHandler: false, extras: {} }
}
```

> info **Gợi ý** Với decorator `@EventPattern`, bạn sẽ thấy cùng output, nhưng thuộc tính `isEventHandler` được đặt thành `true`.

Thuộc tính `messageHandlers` là một `Map` chứa mọi message (và event) handler, được đánh key theo pattern.
Bạn có thể dùng một key (ví dụ `"echo"`) để lấy tham chiếu tới message handler:

```typescript
async listen(callback: () => void) {
  const echoHandler = this.messageHandlers.get('echo');
  console.log(await echoHandler('Hello world!'));
  callback();
}
```

Khi chúng ta thực thi `echoHandler` với một chuỗi tùy ý làm tham số (ở đây là `"Hello world!"`), chúng ta sẽ thấy nó trong console:

```text
Hello world!
```

Điều này có nghĩa là method handler của chúng ta đã được thực thi đúng.

Khi bạn dùng một `CustomTransportStrategy` với [interceptor](/interceptors), các handler được bọc trong các RxJS stream. Điều này có nghĩa là bạn cần subscribe chúng để thực thi logic bên dưới của stream (ví dụ để tiếp tục vào logic của controller sau khi một interceptor đã chạy).

Ví dụ:

```typescript
async listen(callback: () => void) {
  const echoHandler = this.messageHandlers.get('echo');
  const streamOrResult = await echoHandler('Hello World');
  if (isObservable(streamOrResult)) {
    streamOrResult.subscribe();
  }
  callback();
}
```

#### Báo cáo lỗi của event handler <a id="reporting-event-handler-errors"></a>

Một event handler không có response stream, nên một lỗi được throw bên trong nó không có chỗ nào để đi. Thay vào đó Nest sẽ log nó, nhưng chỉ sau khi các exception filter của bạn đã chạy. Nếu một trong các filter của bạn khớp với exception, filter đó là nơi báo cáo duy nhất.

Một số transporter tự await event stream và chuyển lỗi cho client library của chúng, library này sẽ báo cáo nó. `ServerKafka` làm như vậy: `kafkajs` log lần reject, nên một báo cáo thứ hai từ Nest sẽ bị trùng lặp. Trong trường hợp đó, hãy đặt `propagatesEventHandlerErrors` thành `true`:

```typescript
class GoogleCloudPubSubServer
  extends Server
  implements CustomTransportStrategy
{
  /**
   * The client library reports an event handler failure, so Nest must not
   * log it a second time.
   */
  public override readonly propagatesEventHandlerErrors = true;
}
```

Mặc định là `false`, phù hợp với một transporter dùng `handleEvent` được kế thừa. Ở đó không có gì subscribe event stream, nên Nest là thứ duy nhất có thể báo cáo lỗi.

#### Client proxy

Như đã đề cập ở phần đầu, bạn không nhất thiết cần package `@nestjs/microservices` để tạo microservice. Tuy nhiên, nếu bạn dùng nó và cần tích hợp một custom strategy, bạn cũng cần cung cấp một class "client".

> info **Gợi ý** Hiện thực một class client đầy đủ tính năng, tương thích với mọi tính năng của `@nestjs/microservices` (ví dụ streaming), đòi hỏi hiểu rõ các kỹ thuật giao tiếp mà framework dùng. Để tìm hiểu thêm, xem [bài viết về thành phần client cơ bản](https://dev.to/nestjs/part-4-basic-client-component-16f9).

Để giao tiếp với một service bên ngoài và publish message (hoặc emit event), bạn có thể dùng một package SDK riêng của library hoặc hiện thực một class client tùy chỉnh kế thừa `ClientProxy`:

```typescript
import { ClientProxy, ReadPacket, WritePacket } from '@nestjs/microservices';

class GoogleCloudPubSubClient extends ClientProxy {
  async connect(): Promise<any> {}
  async close() {}
  async dispatchEvent(packet: ReadPacket<any>): Promise<any> {}
  publish(
    packet: ReadPacket<any>,
    callback: (packet: WritePacket<any>) => void,
  ): () => void {}
  unwrap<T = never>(): T {
    throw new Error('Method not implemented.');
  }
}
```

> warning **Cảnh báo** Chương này không hiện thực một Google Cloud Pub/Sub client đầy đủ tính năng, vì việc đó đòi hỏi đi sâu vào các chi tiết kỹ thuật riêng của transporter.

Class `ClientProxy` yêu cầu bạn hiện thực các method để thiết lập và đóng kết nối, và để publish message (`publish()`) và event (`dispatchEvent()`).
Nếu bạn không cần hỗ trợ kiểu giao tiếp request-response, bạn có thể để trống method `publish()`. Tương tự, nếu bạn không cần hỗ trợ giao tiếp event-based, hãy để trống method `dispatchEvent()`.

Để quan sát method nào trong số này chạy, và khi nào, hãy thêm vài lời gọi `console.log`:

```typescript
class GoogleCloudPubSubClient extends ClientProxy {
  async connect(): Promise<any> {
    console.log('connect');
  }

  async close() {
    console.log('close');
  }

  async dispatchEvent(packet: ReadPacket<any>): Promise<any> {
    return console.log('event to dispatch: ', packet);
  }

  publish(
    packet: ReadPacket<any>,
    callback: (packet: WritePacket<any>) => void,
  ): () => void {
    console.log('message:', packet);

    // In a real-world application, the "callback" function should be executed
    // with the payload sent back from the responder. Here, we simulate a response
    // (after a 5-second delay) by passing back the same "data" we originally sent.
    //
    // The "isDisposed" flag on the WritePacket signals that no further data is
    // expected. If it's omitted or false, the data is emitted to the Observable.
    setTimeout(() => callback({ 
      response: packet.data,
      isDisposed: true,
    }), 5000);

    return () => console.log('teardown');
  }

  unwrap<T = never>(): T {
    throw new Error('Method not implemented.');
  }
}
```

Khi đã có class này, hãy tạo một instance của class `GoogleCloudPubSubClient` và gọi method `send()` (có thể bạn đã thấy ở các chương trước), subscribe observable stream được trả về:

```typescript
const googlePubSubClient = new GoogleCloudPubSubClient();
googlePubSubClient
  .send('pattern', 'Hello world!')
  .subscribe((response) => console.log(response));
```

Bạn sẽ thấy output sau trong terminal:

```typescript
connect
message: { pattern: 'pattern', data: 'Hello world!' }
Hello world! // <-- after 5 seconds
```

Để kiểm tra xem hàm dọn dẹp (thứ mà method `publish()` của chúng ta trả về) có chạy không, hãy áp dụng operator `timeout` cho stream, đặt là 2 giây để nó throw trước khi `setTimeout` của chúng ta gọi hàm `callback`:

```typescript
const googlePubSubClient = new GoogleCloudPubSubClient();
googlePubSubClient
  .send('pattern', 'Hello world!')
  .pipe(timeout(2000))
  .subscribe({
    next: (response) => console.log(response),
    error: (error) => console.error(error.message),
  });
```

> info **Gợi ý** Operator `timeout` được import từ package `rxjs/operators`.

Khi áp dụng operator `timeout`, output trong terminal của bạn sẽ trông như sau:

```typescript
connect
message: { pattern: 'pattern', data: 'Hello world!' }
teardown // <-- teardown
Timeout has occurred
```

Để dispatch một event (thay vì gửi một message), hãy dùng method `emit()`:

```typescript
googlePubSubClient.emit('event', 'Hello world!');
```

Bạn sẽ thấy nội dung sau trong console:

```typescript
connect
event to dispatch:  { pattern: 'event', data: 'Hello world!' }
```

#### Serialize message <a id="message-serialization"></a>

Để thêm logic tùy chỉnh quanh việc serialize response ở phía client, hãy dùng một class tùy chỉnh kế thừa class `ClientProxy` hoặc một trong các class con của nó. Để thay đổi các response thành công, hãy override method `serializeResponse()`; để thay đổi mọi lỗi đi qua client này, hãy override method `serializeError()`. Để dùng class tùy chỉnh này, hãy truyền chính class đó cho method `ClientsModule.register()` bằng thuộc tính `customClass`. Bên dưới là ví dụ về một `ClientProxy` tùy chỉnh serialize mỗi lỗi thành một `RpcException`.

```typescript
@@filename(error-handling.proxy)
import { ClientTCP, RpcException } from '@nestjs/microservices';

class ErrorHandlingProxy extends ClientTCP {
  serializeError(err: Error) {
    return new RpcException(err);
  }
}
```

Sau đó dùng nó trong `ClientsModule`:

```typescript
@@filename(app.module)
@Module({
  imports: [
    ClientsModule.register([{
      name: 'CustomProxy',
      customClass: ErrorHandlingProxy,
    }]),
  ]
})
export class AppModule {}
```

> info **Gợi ý** Bạn truyền chính class cho `customClass`, không phải một instance của class. Nest tạo instance cho bạn và truyền mọi tùy chọn được cung cấp trong thuộc tính `options` cho `ClientProxy` mới.
