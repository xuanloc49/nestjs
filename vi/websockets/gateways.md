### Gateway

Phần lớn các khái niệm được bàn ở những phần khác trong tài liệu này, như dependency injection, decorator, exception filter, pipe, guard và interceptor, đều áp dụng tương tự cho gateway. Ở bất cứ đâu có thể, Nest trừu tượng hóa các chi tiết hiện thực để cùng các thành phần có thể chạy trên các nền tảng dựa trên HTTP, WebSocket và microservice. Phần này nói về những khía cạnh của Nest dành riêng cho WebSocket.

Trong Nest, một gateway là một class được chú thích bằng decorator `@WebSocketGateway()`. Gateway không phụ thuộc nền tảng, nên chúng hoạt động với bất kỳ library WebSocket nào một khi đã có adapter cho library đó. Nest hỗ trợ sẵn hai nền tảng WebSocket: [socket.io](https://github.com/socketio/socket.io) và [ws](https://github.com/websockets/ws). Hãy chọn cái phù hợp nhất với nhu cầu của bạn. Bạn cũng có thể tự xây adapter theo [hướng dẫn về adapter](/websockets/adapter).

<figure><img class="illustrative-image" src="/assets/Gateways_1.png" /></figure>

> info **Gợi ý** Gateway là [provider](/providers): chúng có thể inject dependency qua constructor của class, và các class khác (provider và controller) có thể inject chúng.

#### Cài đặt <a id="installation"></a>

Để bắt đầu xây dựng ứng dụng dựa trên WebSocket, trước tiên hãy cài package cần thiết:

```bash
@@filename()
$ npm i --save @nestjs/websockets @nestjs/platform-socket.io
@@switch
$ npm i --save @nestjs/websockets @nestjs/platform-socket.io
```

#### Tổng quan <a id="overview"></a>

Mặc định, mỗi gateway lắng nghe trên cùng port với **HTTP server**. Để dùng một port khác, hãy truyền nó làm tham số đầu tiên cho decorator, ví dụ `@WebSocketGateway(80)`, trong đó `80` là số port được chọn. Bạn cũng có thể đặt [namespace](https://socket.io/docs/v4/namespaces/) mà gateway dùng:

```typescript
@WebSocketGateway(80, { namespace: 'events' })
```

> warning **Cảnh báo** Gateway không được khởi tạo cho tới khi chúng được tham chiếu trong mảng providers của một module đã có.

Tham số thứ hai của decorator `@WebSocketGateway()` truyền bất kỳ [tùy chọn server](https://socket.io/docs/v4/server-options/) nào được hỗ trợ cho constructor của socket server. Nếu bạn không cần port tùy chỉnh, hãy truyền options object làm tham số duy nhất.

```typescript
@WebSocketGateway(81, { transports: ['websocket'] })
```

Gateway giờ đang lắng nghe, nhưng nó chưa subscribe message đi vào nào. Hãy tạo một handler subscribe các message `events` và phản hồi lại client cùng dữ liệu đó.

```typescript
@@filename(events.gateway)
@SubscribeMessage('events')
handleEvent(@MessageBody() data: string): string {
  return data;
}
@@switch
@Bind(MessageBody())
@SubscribeMessage('events')
handleEvent(data) {
  return data;
}
```

> info **Gợi ý** Các decorator `@SubscribeMessage()` và `@MessageBody()` được import từ package `@nestjs/websockets`.

Khi đã tạo gateway, hãy đăng ký nó trong một module.

```typescript
@@filename(events.module)
import { Module } from '@nestjs/common';
import { EventsGateway } from './events.gateway.js';

@Module({
  providers: [EventsGateway]
})
export class EventsModule {}
```

Bạn cũng có thể truyền một property key cho decorator `@MessageBody()` để lấy thuộc tính đó ra từ body của message đi vào:

```typescript
@@filename(events.gateway)
@SubscribeMessage('events')
handleEvent(@MessageBody('id') id: number): number {
  // id === messageBody.id
  return id;
}
@@switch
@Bind(MessageBody('id'))
@SubscribeMessage('events')
handleEvent(id) {
  // id === messageBody.id
  return id;
}
```

Nếu bạn không muốn dùng decorator, đoạn code sau tương đương về chức năng:

```typescript
@@filename(events.gateway)
@SubscribeMessage('events')
handleEvent(client: Socket, data: string): string {
  return data;
}
@@switch
@SubscribeMessage('events')
handleEvent(client, data) {
  return data;
}
```

Trong ví dụ ở trên, method `handleEvent()` nhận hai tham số. Tham số đầu tiên là một [socket instance](https://socket.io/docs/v4/server-api/#socket) riêng của nền tảng, và tham số thứ hai là dữ liệu nhận được từ client. Cách này không được khuyến khích, vì nó buộc bạn phải mock instance `socket` trong mỗi unit test.

Khi nhận được message `events`, handler gửi một acknowledgment với cùng dữ liệu đã được gửi qua mạng. Bạn cũng có thể emit message bằng API riêng của library, ví dụ method `client.emit()`. Để truy cập socket instance đang kết nối, hãy dùng decorator `@ConnectedSocket()`.

```typescript
@@filename(events.gateway)
@SubscribeMessage('events')
handleEvent(
  @MessageBody() data: string,
  @ConnectedSocket() client: Socket,
): string {
  return data;
}
@@switch
@Bind(MessageBody(), ConnectedSocket())
@SubscribeMessage('events')
handleEvent(data, client) {
  return data;
}
```

> info **Gợi ý** Decorator `@ConnectedSocket()` được import từ package `@nestjs/websockets`.

Tuy nhiên, các message bạn emit trực tiếp qua socket sẽ bỏ qua interceptor, vốn chỉ thấy giá trị trả về của handler. Nếu bạn không muốn phản hồi client, hãy bỏ câu lệnh `return` (hoặc trả về `null` hay `undefined`). Các giá trị falsy khác, như `false` hay `0`, vẫn được gửi đi làm response.

Khi một client emit message như sau, method `handleEvent()` sẽ được thực thi:

```typescript
socket.emit('events', { name: 'Nest' });
```

Để nhận response mà handler ở trên gửi, client phải gắn một acknowledgment callback tương ứng:

```typescript
socket.emit('events', { name: 'Nest' }, (data) => console.log(data));
```

Trả về một giá trị từ message handler sẽ ngầm gửi một acknowledgment, nhưng các tình huống nâng cao thường cần kiểm soát trực tiếp acknowledgment callback.

Parameter decorator `@Ack()` inject hàm callback `ack` trực tiếp vào một message handler. Khi bạn dùng nó, Nest không gửi acknowledgment dựa trên giá trị trả về, nên bạn phải tự gọi `ack()`. Không có decorator này, callback được truyền làm tham số thứ ba của method.

```typescript
@@filename(events.gateway)
@SubscribeMessage('events')
handleEvent(
  @MessageBody() data: string,
  @Ack() ack: (response: { status: string; data: string }) => void,
) {
  ack({ status: 'received', data });
}
@@switch
@Bind(MessageBody(), Ack())
@SubscribeMessage('events')
handleEvent(data, ack) {
  ack({ status: 'received', data });
}
```

#### Nhiều response <a id="multiple-responses"></a>

Acknowledgment chỉ được gửi một lần, và các phần hiện thực WebSocket gốc không hỗ trợ nó. Để vượt qua những hạn chế này, hãy trả về một object có hai thuộc tính: `event`, tên của event được emit, và `data`, payload cần chuyển tới client.

```typescript
@@filename(events.gateway)
@SubscribeMessage('events')
handleEvent(@MessageBody() data: unknown): WsResponse<unknown> {
  const event = 'events';
  return { event, data };
}
@@switch
@Bind(MessageBody())
@SubscribeMessage('events')
handleEvent(data) {
  const event = 'events';
  return { event, data };
}
```

> info **Gợi ý** Interface `WsResponse` được import từ package `@nestjs/websockets`.

> warning **Cảnh báo** Nếu field `data` của bạn dựa vào `ClassSerializerInterceptor`, hãy trả về một class instance implement `WsResponse`, vì interceptor bỏ qua các response là plain object JavaScript.

Để nhận (các) response đi tới, client phải thêm một event listener khác.

```typescript
socket.on('events', (data) => console.log(data));
```

#### Response bất đồng bộ <a id="asynchronous-responses"></a>

Message handler có thể phản hồi đồng bộ hoặc **bất đồng bộ**, nên các method `async` đều được hỗ trợ. Một message handler cũng có thể trả về một `Observable`, khi đó mỗi giá trị được phát ra sẽ được gửi tới client cho tới khi stream hoàn tất.

```typescript
@@filename(events.gateway)
@SubscribeMessage('events')
onEvent(@MessageBody() data: unknown): Observable<WsResponse<number>> {
  const event = 'events';
  const response = [1, 2, 3];

  return from(response).pipe(
    map(data => ({ event, data })),
  );
}
@@switch
@Bind(MessageBody())
@SubscribeMessage('events')
onEvent(data) {
  const event = 'events';
  const response = [1, 2, 3];

  return from(response).pipe(
    map(data => ({ event, data })),
  );
}
```

Trong ví dụ ở trên, message handler phản hồi **3 lần** (mỗi phần tử trong mảng một lần).

#### Lifecycle hook <a id="lifecycle-hooks"></a>

Gateway hỗ trợ ba lifecycle hook. Mỗi hook có một interface tương ứng, được mô tả trong bảng sau:

<table>
  <tr>
    <td>
      <code>OnGatewayInit</code>
    </td>
    <td>
      Yêu cầu method <code>afterInit()</code>, method này nhận server instance riêng của library làm tham số.
    </td>
  </tr>
  <tr>
    <td>
      <code>OnGatewayConnection</code>
    </td>
    <td>
      Yêu cầu method <code>handleConnection()</code>, method này nhận client socket instance riêng của library làm
      tham số đầu tiên.
    </td>
  </tr>
  <tr>
    <td>
      <code>OnGatewayDisconnect</code>
    </td>
    <td>
      Yêu cầu method <code>handleDisconnect()</code>, method này nhận client socket instance riêng của library làm
      tham số đầu tiên.
    </td>
  </tr>
</table>

> info **Gợi ý** Mỗi lifecycle interface đều được cung cấp từ package `@nestjs/websockets`.

> warning **Cảnh báo** Nest không chờ một `handleConnection()` async hoàn tất trước khi xử lý các message của client, nên hook này không phải là một cửa chặn: các message tới trước khi nó ngắt kết nối client vẫn được xử lý. Để kiểm tra từng message, hãy gắn [guard](/websockets/guards) vào các message handler. Để từ chối một client trước khi bất kỳ message nào của nó được xử lý, hãy dùng middleware ở cấp kết nối thay vào đó: `server.use()` của socket.io trong `afterInit()`, hoặc, với `WsAdapter`, một hàm `verifyClient` trong các tùy chọn của `@WebSocketGateway()`.

#### Server và Namespace <a id="server-and-namespace"></a>

Đôi khi, bạn có thể cần truy cập trực tiếp vào server instance gốc, **riêng của nền tảng**. Nest truyền nó làm tham số cho method `afterInit()` (interface `OnGatewayInit`). Ngoài ra, bạn có thể dùng decorator `@WebSocketServer()`.

```typescript
@WebSocketServer()
server: Server;
```

Bạn cũng có thể lấy namespace tương ứng:

```typescript
@WebSocketGateway({ namespace: 'my-namespace' })
export class EventsGateway {
  @WebSocketServer()
  namespace: Namespace;
}
```

Decorator `@WebSocketServer()` inject một server instance dựa trên metadata được lưu bởi decorator `@WebSocketGateway()`. Nếu bạn truyền tùy chọn `namespace` cho `@WebSocketGateway()`, `@WebSocketServer()` sẽ inject một instance `Namespace` thay vì một instance `Server`.

> warning **Chú ý** Decorator `@WebSocketServer()` được import từ package `@nestjs/websockets`.

Nest gán server instance cho thuộc tính này khi nó đã sẵn sàng để dùng.

<app-banner-enterprise></app-banner-enterprise>

#### Gateway request-scoped <a id="request-scoped-gateways"></a>

Bắt đầu từ NestJS v12, gateway hỗ trợ các provider [request-scoped](/fundamentals/injection-scopes). Nest tạo một instance mới của mọi dependency request-scoped cho mỗi socket đang kết nối. Instance đó tồn tại chừng nào kết nối còn tồn tại, nên nó có thể giữ trạng thái theo từng kết nối một cách an toàn.

Inject chính socket bằng token `REQUEST`, giống như cách bạn inject HTTP request vào một HTTP provider request-scoped:

```typescript
@@filename(connection-state.service)
import { Inject, Injectable, Scope } from '@nestjs/common';
import { REQUEST } from '@nestjs/core';
import { Socket } from 'socket.io';

@Injectable({ scope: Scope.REQUEST })
export class ConnectionStateService {
  private sequence = 0;

  constructor(@Inject(REQUEST) private readonly client: Socket) {}

  next() {
    return { clientId: this.client.id, sequence: ++this.sequence };
  }
}
```

Sau đó gateway inject nó như bất kỳ provider nào khác:

```typescript
@@filename(events.gateway)
@WebSocketGateway()
export class EventsGateway {
  constructor(private readonly connectionState: ConnectionStateService) {}

  handleConnection(client: Socket) {
    client.emit('connected', this.connectionState.next());
  }

  @SubscribeMessage('state')
  onState() {
    return { event: 'state', data: this.connectionState.next() };
  }
}
```

Vì scope gắn với kết nối chứ không phải với một message đơn lẻ, bộ đếm `sequence` ở trên tăng dần qua mọi message nhận được trên socket đó, trong khi một client thứ hai có instance độc lập của riêng nó. Nest hủy các instance request-scoped khi socket ngắt kết nối.

> warning **Chú ý** Như với HTTP, các provider request-scoped thêm chi phí khởi tạo cho mỗi kết nối. Hãy dùng scope singleton mặc định trừ khi bạn cần trạng thái theo từng kết nối.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có trong [sample 02-gateways](https://github.com/nestjs/nest/tree/master/sample/02-gateways).
