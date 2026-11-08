### Adapter

Module WebSocket không phụ thuộc nền tảng, nên bạn có thể dùng library của riêng mình (hoặc thậm chí một phần hiện thực gốc) bằng cách implement interface `WebSocketAdapter`. Interface này yêu cầu các method được mô tả trong bảng sau:

<table>
  <tr>
    <td><code>create</code></td>
    <td>Tạo một socket server instance dựa trên các tham số được truyền vào</td>
  </tr>
  <tr>
    <td><code>bindClientConnect</code></td>
    <td>Gắn event kết nối của client</td>
  </tr>
  <tr>
    <td><code>bindClientDisconnect</code></td>
    <td>Gắn event ngắt kết nối của client (tùy chọn)</td>
  </tr>
  <tr>
    <td><code>bindMessageHandlers</code></td>
    <td>Gắn message đi vào với message handler tương ứng</td>
  </tr>
  <tr>
    <td><code>close</code></td>
    <td>Kết thúc một server instance</td>
  </tr>
</table>

#### Mở rộng socket.io <a id="extend-socketio"></a>

Package [socket.io](https://github.com/socketio/socket.io) được bọc trong class `IoAdapter`. Bạn có thể kế thừa class này để tăng cường chức năng cơ bản của adapter. Ví dụ, giả sử ứng dụng của bạn phải broadcast event qua nhiều instance của web service đứng sau load balancer. Để hỗ trợ điều này, hãy kế thừa `IoAdapter` và override method duy nhất chịu trách nhiệm khởi tạo các socket.io server mới. Trước tiên, hãy cài các package cần thiết.

> warning **Cảnh báo** Để dùng socket.io với nhiều instance đứng sau load balancer, bạn phải hoặc tắt polling bằng cách đặt `transports: ['websocket']` trong cấu hình socket.io của client, hoặc bật định tuyến dựa trên cookie (sticky session) trong load balancer. Chỉ Redis thôi là chưa đủ. Xem [Enabling sticky session](https://socket.io/docs/v4/using-multiple-nodes/#enabling-sticky-session) trong tài liệu socket.io để biết thêm thông tin.

```bash
$ npm i --save redis socket.io @socket.io/redis-adapter
```

Khi đã cài các package, hãy tạo một class `RedisIoAdapter`.

```typescript
import { IoAdapter } from '@nestjs/platform-socket.io';
import { ServerOptions } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { createClient } from 'redis';

export class RedisIoAdapter extends IoAdapter {
  private adapterConstructor: ReturnType<typeof createAdapter>;

  async connectToRedis(): Promise<void> {
    const pubClient = createClient({ url: `redis://localhost:6379` });
    const subClient = pubClient.duplicate();

    await Promise.all([pubClient.connect(), subClient.connect()]);

    this.adapterConstructor = createAdapter(pubClient, subClient);
  }

  createIOServer(port: number, options?: ServerOptions): any {
    const server = super.createIOServer(port, options);
    server.adapter(this.adapterConstructor);
    return server;
  }
}
```

Sau đó chuyển sang dùng Redis adapter vừa tạo.

```typescript
const app = await NestFactory.create(AppModule);
const redisIoAdapter = new RedisIoAdapter(app);
await redisIoAdapter.connectToRedis();

app.useWebSocketAdapter(redisIoAdapter);
```

#### Library ws <a id="ws-library"></a>

Một adapter khác có sẵn là `WsAdapter`, đóng vai trò proxy giữa framework và library [ws](https://github.com/websockets/ws) nhanh và đã được test kỹ lưỡng. Adapter này tương thích hoàn toàn với WebSocket gốc của trình duyệt và nhanh hơn package socket.io. Tuy nhiên, nó cung cấp sẵn ít tính năng hơn đáng kể, những tính năng mà nhiều ứng dụng cũng không cần tới.

> info **Gợi ý** Library `ws` không hỗ trợ namespace (các kênh giao tiếp được `socket.io` phổ biến), và `WsAdapter` sẽ throw lỗi nếu bạn đặt tùy chọn `namespace`. Để mô phỏng tính năng này, hãy mount nhiều `ws` server trên các path khác nhau (ví dụ `@WebSocketGateway({{ '{' }} path: '/users' {{ '}' }})`).

Để dùng `ws`, trước tiên hãy cài package cần thiết:

```bash
$ npm i --save @nestjs/platform-ws
```

Khi đã cài package, hãy đổi adapter:

```typescript
const app = await NestFactory.create(AppModule);
app.useWebSocketAdapter(new WsAdapter(app));
```

> info **Gợi ý** `WsAdapter` được import từ `@nestjs/platform-ws`.

`WsAdapter` xử lý message theo định dạng `{{ '{' }} event: string, data: any {{ '}' }}`. Để nhận và xử lý message theo định dạng khác, hãy cấu hình một message parser chuyển chúng sang định dạng này.

```typescript
const wsAdapter = new WsAdapter(app, {
  // To handle messages in the [event, data] format
  messageParser: (data) => {
    const [event, payload] = JSON.parse(data.toString());
    return { event, data: payload };
  },
});
```

Ngoài ra, bạn có thể đặt message parser sau khi tạo adapter bằng method `setMessageParser()`.

#### Nâng cao (custom adapter) <a id="advanced-custom-adapter"></a>

Để minh họa, chúng ta sẽ tích hợp thủ công library [ws](https://github.com/websockets/ws). Như đã nói, đã có sẵn một adapter cho library này: class `WsAdapter` được cung cấp từ package `@nestjs/platform-ws`. Một phần hiện thực đơn giản hóa có thể trông như thế này:

```typescript
@@filename(ws-adapter)
import WebSocket, { WebSocketServer } from 'ws';
import { WebSocketAdapter, INestApplicationContext } from '@nestjs/common';
import { MessageMappingProperties } from '@nestjs/websockets';
import { Observable, fromEvent, EMPTY } from 'rxjs';
import { mergeMap, filter } from 'rxjs/operators';

export class WsAdapter implements WebSocketAdapter {
  constructor(private app: INestApplicationContext) {}

  create(port: number, options: any = {}): any {
    return new WebSocketServer({ port, ...options });
  }

  bindClientConnect(server: WebSocketServer, callback: (...args: any[]) => void) {
    server.on('connection', callback);
  }

  bindMessageHandlers(
    client: WebSocket,
    handlers: MessageMappingProperties[],
    process: (data: any) => Observable<any>,
  ) {
    fromEvent(client, 'message')
      .pipe(
        mergeMap(data => this.bindMessageHandler(data, handlers, process)),
        filter(result => result),
      )
      .subscribe(response => client.send(JSON.stringify(response)));
  }

  bindMessageHandler(
    buffer: any,
    handlers: MessageMappingProperties[],
    process: (data: any) => Observable<any>,
  ): Observable<any> {
    const message = JSON.parse(buffer.data);
    const messageHandler = handlers.find(
      handler => handler.message === message.event,
    );
    if (!messageHandler) {
      return EMPTY;
    }
    return process(messageHandler.callback(message.data));
  }

  close(server: WebSocketServer) {
    server.close();
  }
}
```

> info **Gợi ý** Để dùng library [ws](https://github.com/websockets/ws), hãy dùng `WsAdapter` có sẵn thay vì tự tạo adapter.

Sau đó thiết lập custom adapter bằng method `useWebSocketAdapter()`:

```typescript
@@filename(main)
const app = await NestFactory.create(AppModule);
app.useWebSocketAdapter(new WsAdapter(app));
```

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được dùng `WsAdapter` có trong [sample 16-gateways-ws](https://github.com/nestjs/nest/tree/master/sample/16-gateways-ws).
