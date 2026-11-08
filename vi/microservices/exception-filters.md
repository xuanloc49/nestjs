### Exception filter

Khác biệt duy nhất giữa lớp [exception filter](/exception-filters) của HTTP và lớp tương ứng của microservice là microservice nên throw `RpcException` thay vì `HttpException`.

```typescript
throw new RpcException('Invalid credentials.');
```

> info **Gợi ý** Class `RpcException` được import từ package `@nestjs/microservices`.

Nest xử lý exception được throw và trả về một object `error` với cấu trúc sau:

```json
{
  "status": "error",
  "message": "Invalid credentials."
}
```

Nếu bạn truyền một object cho constructor của `RpcException` thay vì một chuỗi, Nest sẽ trả về nguyên object đó.

> warning **Cảnh báo** Một event handler không có response stream. Một lỗi mà filter throw lại cho một handler `@EventPattern()` sẽ không bao giờ tới được producer, nên hãy xử lý lỗi bên trong filter.

#### Filter <a id="filters"></a>

Exception filter của microservice hoạt động giống exception filter của HTTP, với một khác biệt: method `catch()` phải trả về một `Observable`.

```typescript
@@filename(rpc-exception.filter)
import { Catch, RpcExceptionFilter, ArgumentsHost } from '@nestjs/common';
import { Observable, throwError } from 'rxjs';
import { RpcException } from '@nestjs/microservices';

@Catch(RpcException)
export class ExceptionFilter implements RpcExceptionFilter<RpcException> {
  catch(exception: RpcException, host: ArgumentsHost): Observable<any> {
    return throwError(() => exception.getError());
  }
}
@@switch
import { Catch } from '@nestjs/common';
import { throwError } from 'rxjs';
import { RpcException } from '@nestjs/microservices';

@Catch(RpcException)
export class ExceptionFilter {
  catch(exception, host) {
    return throwError(() => exception.getError());
  }
}
```

> warning **Cảnh báo** Global exception filter được đăng ký trên ứng dụng HTTP chính không áp dụng cho các microservice được kết nối vào một [ứng dụng hybrid](/faq/hybrid-application) trừ khi bạn đặt tùy chọn `inheritAppConfig`. Xem [dùng chung cấu hình](/faq/hybrid-application#sharing-configuration).

Ví dụ sau dùng một filter cấp method được khởi tạo thủ công. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng filter cấp controller (tức là đặt decorator `@UseFilters()` trước class controller).

```typescript
@@filename()
@UseFilters(new ExceptionFilter())
@MessagePattern({ cmd: 'sum' })
accumulate(data: number[]): number {
  return (data || []).reduce((a, b) => a + b);
}
@@switch
@UseFilters(new ExceptionFilter())
@MessagePattern({ cmd: 'sum' })
accumulate(data) {
  return (data || []).reduce((a, b) => a + b);
}
```

#### Kế thừa <a id="inheritance"></a>

Thông thường, bạn sẽ tạo các exception filter tùy chỉnh hoàn toàn theo yêu cầu của ứng dụng. Tuy nhiên, trong một số trường hợp, bạn có thể muốn kế thừa **exception filter lõi** và override hành vi của nó dựa trên một số yếu tố.

Để giao việc xử lý exception cho base filter, hãy kế thừa `BaseRpcExceptionFilter` và gọi method `catch()` được kế thừa.

```typescript
@@filename()
import { Catch, ArgumentsHost } from '@nestjs/common';
import { BaseRpcExceptionFilter } from '@nestjs/microservices';

@Catch()
export class AllExceptionsFilter extends BaseRpcExceptionFilter {
  catch(exception: any, host: ArgumentsHost) {
    return super.catch(exception, host);
  }
}
@@switch
import { Catch } from '@nestjs/common';
import { BaseRpcExceptionFilter } from '@nestjs/microservices';

@Catch()
export class AllExceptionsFilter extends BaseRpcExceptionFilter {
  catch(exception, host) {
    return super.catch(exception, host);
  }
}
```

Phần hiện thực ở trên chỉ là một khung để minh họa cách làm. Phần hiện thực exception filter mở rộng của bạn sẽ bao gồm **logic nghiệp vụ** của riêng bạn (ví dụ xử lý các điều kiện khác nhau).
