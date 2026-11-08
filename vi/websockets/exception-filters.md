### Exception filter

Lớp xử lý exception của WebSocket hoạt động giống lớp [exception filter](/exception-filters) của HTTP, chỉ khác một điểm: thay vì throw `HttpException`, hãy throw `WsException`.

```typescript
throw new WsException('Invalid credentials.');
```

> info **Gợi ý** Class `WsException` được import từ package `@nestjs/websockets`.

Khi một handler throw exception ở trên, Nest bắt nó và emit một message `exception` tới client với cấu trúc sau:

```typescript
{
  status: 'error',
  message: 'Invalid credentials.',
  cause: {
    pattern: 'events', // pattern of the message that caused the exception
    data: { name: 'Nest' }, // payload of that message
  },
}
```

Thuộc tính `cause` cho phép client liên kết lỗi với message đã gây ra nó. Nếu bạn truyền một object (thay vì một chuỗi) cho constructor của `WsException`, Nest sẽ emit nguyên object đó. Mọi exception không phải `WsException` đều tạo ra cùng cấu trúc, với message là `'Internal server error'`. Với adapter `ws`, vốn không có event có tên, client nhận một chuỗi JSON dạng `{{ '{' }} "event": "exception", "data": ... {{ '}' }}` thay vào đó.

#### Filter <a id="filters"></a>

Exception filter của WebSocket hoạt động giống như exception filter của HTTP. Ví dụ sau dùng một filter cấp method được khởi tạo thủ công. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng filter cấp gateway (tức là gắn `@UseFilters()` cho class gateway).

```typescript
@UseFilters(new WsExceptionFilter())
@SubscribeMessage('events')
onEvent(client, data: any): WsResponse<any> {
  const event = 'events';
  return { event, data };
}
```

> warning **Cảnh báo** Global exception filter (được đăng ký bằng `app.useGlobalFilters()` hoặc token `APP_FILTER`) không áp dụng cho gateway. Hãy gắn exception filter của WebSocket ở cấp gateway hoặc cấp method bằng `@UseFilters()`.

#### Kế thừa <a id="inheritance"></a>

Thông thường, bạn sẽ tạo các exception filter tùy chỉnh hoàn toàn theo yêu cầu của ứng dụng. Tuy nhiên, đôi khi bạn có thể muốn kế thừa **exception filter lõi** và override hành vi của nó dựa trên một số yếu tố.

Để giao việc xử lý exception cho base filter, hãy kế thừa `BaseWsExceptionFilter` và gọi method `catch()` được kế thừa.

```typescript
@@filename()
import { Catch, ArgumentsHost } from '@nestjs/common';
import { BaseWsExceptionFilter } from '@nestjs/websockets';

@Catch()
export class AllExceptionsFilter extends BaseWsExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    super.catch(exception, host);
  }
}
@@switch
import { Catch } from '@nestjs/common';
import { BaseWsExceptionFilter } from '@nestjs/websockets';

@Catch()
export class AllExceptionsFilter extends BaseWsExceptionFilter {
  catch(exception, host) {
    super.catch(exception, host);
  }
}
```

Phần hiện thực ở trên chỉ là một khung để minh họa cách làm. Một exception filter mở rộng thực sự sẽ thêm **logic nghiệp vụ** của riêng bạn (ví dụ xử lý các điều kiện khác nhau).

Constructor của `BaseWsExceptionFilter` nhận một options object. Đặt `includeCause` thành `false` để bỏ thuộc tính `cause` khỏi các error message, hoặc truyền một hàm `causeFactory(pattern, data)` để kiểm soát cấu trúc của nó.
