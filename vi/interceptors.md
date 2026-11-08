### Interceptors

Interceptor là một class được đánh dấu bằng decorator `@Injectable()` và implement interface `NestInterceptor`.

<figure><img class="illustrative-image" src="/assets/Interceptors_1.png" /></figure>

Interceptor cung cấp một loạt khả năng lấy cảm hứng từ kỹ thuật [Aspect Oriented Programming](https://en.wikipedia.org/wiki/Aspect-oriented_programming) (AOP). Với interceptor, bạn có thể:

- gắn thêm logic trước hoặc sau khi method thực thi
- chuyển đổi kết quả trả về từ một hàm
- chuyển đổi exception throw ra từ một hàm
- mở rộng hành vi cơ bản của một hàm
- ghi đè hoàn toàn một hàm tùy theo điều kiện cụ thể (ví dụ cho mục đích cache)

#### Cơ bản <a id="basics"></a>

Mỗi interceptor implement method `intercept()`, method này nhận hai tham số. Tham số đầu tiên là instance `ExecutionContext` (chính xác là cùng object như với [guard](/guards)). `ExecutionContext` kế thừa `ArgumentsHost`, thứ mà ta đã tìm hiểu trong chương exception filter. Ở đó, ta thấy nó là một wrapper bọc quanh các tham số truyền vào handler gốc, và chứa các mảng tham số khác nhau tùy theo loại ứng dụng. Xem chương [exception filter](/exception-filters#arguments-host) để biết thêm về chủ đề này.

#### Execution context

Bằng việc kế thừa `ArgumentsHost`, `ExecutionContext` bổ sung thêm vài method helper cung cấp thông tin chi tiết hơn về quá trình thực thi hiện tại. Những thông tin này giúp bạn xây dựng các interceptor generic hơn, hoạt động được trên nhiều controller, method và execution context khác nhau. Xem chương [execution context](/fundamentals/execution-context) để tìm hiểu thêm về `ExecutionContext`.

#### Call handler

Tham số thứ hai là một `CallHandler`. Interface `CallHandler` cung cấp method `handle()`, bạn dùng nó để gọi method route handler tại một thời điểm nào đó trong interceptor. Nếu bạn không gọi `handle()` trong phần implement method `intercept()`, method route handler sẽ hoàn toàn không được thực thi.

Điều này có nghĩa là method `intercept()` thực chất **bọc** lấy luồng request/response. Nhờ vậy, bạn có thể implement logic tùy chỉnh **cả trước lẫn sau** khi route handler cuối cùng thực thi. Chạy code **trước** handler thì đơn giản: đặt nó trước lời gọi `handle()`. Để xử lý những gì xảy ra sau đó, hãy dùng `Observable` mà `handle()` trả về: bạn có thể áp dụng các operator của [RxJS](https://github.com/ReactiveX/rxjs) lên nó để thao tác thêm với response. Theo thuật ngữ Aspect Oriented Programming, việc gọi route handler (tức là gọi `handle()`) được gọi là [Pointcut](https://en.wikipedia.org/wiki/Pointcut), nghĩa là điểm mà logic bổ sung của ta được chèn vào.

Ví dụ, xét một request `POST /cats` gửi đến. Request này hướng tới handler `create()` định nghĩa trong `CatsController`. Nếu trên đường đi có một interceptor không gọi `handle()`, method `create()` sẽ không được thực thi. Khi `handle()` được gọi và `Observable` mà nó trả về được subscribe (Nest sẽ subscribe stream mà method `intercept()` của bạn trả về), handler `create()` mới được kích hoạt. Khi kết quả của handler chảy qua stream, bạn có thể áp dụng thêm các thao tác lên nó trước khi kết quả cuối cùng được trả về cho bên gọi.

<app-banner-observe></app-banner-observe>

#### Chặn theo aspect <a id="aspect-interception"></a>

Công dụng đầu tiên mà ta xem xét là dùng interceptor để log tương tác của người dùng (ví dụ lưu lại các lời gọi của người dùng, dispatch event bất đồng bộ, hoặc tính timestamp). Ví dụ sau là một `LoggingInterceptor` đơn giản:

```typescript
@@filename(logging.interceptor)
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    console.log('Before...');

    const now = Date.now();
    return next
      .handle()
      .pipe(
        tap(() => console.log(`After... ${Date.now() - now}ms`)),
      );
  }
}
@@switch
import { Injectable } from '@nestjs/common';
import { tap } from 'rxjs/operators';

@Injectable()
export class LoggingInterceptor {
  intercept(context, next) {
    console.log('Before...');

    const now = Date.now();
    return next
      .handle()
      .pipe(
        tap(() => console.log(`After... ${Date.now() - now}ms`)),
      );
  }
}
```

> info **Gợi ý** `NestInterceptor<T, R>` là một interface generic, trong đó `T` là type của các giá trị được emit bởi `Observable<T>` mà `next.handle()` trả về (response stream), và `R` là type của các giá trị được emit bởi `Observable<R>` mà `intercept()` trả về.

> warning **Chú ý** Interceptor, giống như controller, provider, guard, v.v., có thể **inject dependency** thông qua `constructor` của nó.

Vì `handle()` trả về một `Observable` của RxJS, bạn có rất nhiều operator để lựa chọn khi thao tác với stream. Ví dụ trên dùng operator `tap()`, operator này gọi hàm log của ta khi stream emit kết quả của route handler, mà không can thiệp gì khác vào chu trình response. Lưu ý rằng hàm này sẽ không được gọi nếu route handler throw; để chạy logic cả trong trường hợp đó, hãy truyền vào `tap()` một observer object có callback `error`, hoặc dùng operator `finalize()`.

> info **Gợi ý** Tự đo thời gian chạy của handler như trên chỉ là phiên bản tối giản của những gì một APM làm. [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') ghi lại cùng số đo đó cho mọi controller, provider và queue consumer, mà không cần viết hay bind interceptor nào. Nó cũng ghi lại thời gian mà từng thành phần tự tiêu tốn, đã trừ đi mọi thứ nó phải await. Xem chương [Observability](/observability/overview).

#### Bind interceptor <a id="binding-interceptors"></a>

Để thiết lập interceptor, dùng decorator `@UseInterceptors()`. Giống như [pipe](/pipes) và [guard](/guards), interceptor có thể ở cấp controller, cấp method hoặc cấp global.

```typescript
@@filename(cats.controller)
@UseInterceptors(LoggingInterceptor)
export class CatsController {}
```

> info **Gợi ý** Decorator `@UseInterceptors()` được import từ package `@nestjs/common`.

Với cách khai báo trên, mọi route handler định nghĩa trong `CatsController` đều dùng `LoggingInterceptor`. Khi client gọi endpoint `GET /cats`, bạn sẽ thấy kết quả sau trên standard output:

```typescript
Before...
After... 1ms
```

Lưu ý rằng ta truyền vào class `LoggingInterceptor` (thay vì instance), để framework lo việc khởi tạo và bật được dependency injection. Giống như với pipe, guard và exception filter, bạn cũng có thể truyền một instance tạo tại chỗ:

```typescript
@@filename(cats.controller)
@UseInterceptors(new LoggingInterceptor())
export class CatsController {}
```

Cách khai báo trên gắn interceptor vào mọi handler mà controller này khai báo. Để giới hạn interceptor cho một method, áp dụng decorator ở **cấp method**.

Để thiết lập global interceptor, dùng method `useGlobalInterceptors()` của instance ứng dụng Nest:

```typescript
const app = await NestFactory.create(AppModule);
app.useGlobalInterceptors(new LoggingInterceptor());
```

Global interceptor áp dụng cho mọi controller và mọi route handler trong ứng dụng. Tuy nhiên, global interceptor đăng ký từ bên ngoài mọi module (bằng `useGlobalInterceptors()` như ví dụ trên) không thể inject dependency, vì việc đăng ký diễn ra bên ngoài context của mọi module. Để giải quyết, hãy đăng ký interceptor **trực tiếp từ bất kỳ module nào** bằng cách sau:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { APP_INTERCEPTOR } from '@nestjs/core';

@Module({
  providers: [
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggingInterceptor,
    },
  ],
})
export class AppModule {}
```

> info **Gợi ý** Khi dùng cách này để thực hiện dependency injection cho interceptor, interceptor sẽ là global bất kể bạn đăng ký nó trong module nào. Chúng tôi khuyên đăng ký nó trong module nơi interceptor (`LoggingInterceptor` trong ví dụ trên) được định nghĩa. Ngoài ra, `useClass` không phải cách duy nhất để đăng ký custom provider. Xem [Custom provider](/fundamentals/custom-providers) để tìm hiểu thêm.

#### Map response <a id="response-mapping"></a>

Stream mà `handle()` trả về chứa giá trị **được trả về** từ route handler, nên bạn có thể chuyển đổi nó bằng operator `map()` của RxJS.

> warning **Cảnh báo** Map response không hoạt động với cách xử lý response riêng của library, tức là khi route handler inject response object bằng `@Res()` và tự gửi response. Để kết hợp cả hai, hãy bật tùy chọn `passthrough` (xem [Cách dùng riêng của library](/controllers#library-specific-approach)).

Hãy tạo một `TransformInterceptor` sửa mỗi response theo một cách đơn giản để minh họa quá trình này. Nó dùng operator `map()` của RxJS để gán response object vào thuộc tính `data` của một object mới tạo, rồi trả object mới này về cho client.

```typescript
@@filename(transform.interceptor)
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface Response<T> {
  data: T;
}

@Injectable()
export class TransformInterceptor<T> implements NestInterceptor<T, Response<T>> {
  intercept(context: ExecutionContext, next: CallHandler): Observable<Response<T>> {
    return next.handle().pipe(map(data => ({ data })));
  }
}
@@switch
import { Injectable } from '@nestjs/common';
import { map } from 'rxjs/operators';

@Injectable()
export class TransformInterceptor {
  intercept(context, next) {
    return next.handle().pipe(map(data => ({ data })));
  }
}
```

> info **Gợi ý** Method `intercept()` có thể đồng bộ hoặc bất đồng bộ. Khai báo nó là `async` nếu bạn cần await gì đó trước khi trả về stream.

Khi bind interceptor này, một request `GET /cats` có route handler trả về mảng rỗng `[]` sẽ cho ra response sau:

```json
{
  "data": []
}
```

Interceptor rất phù hợp để xây dựng các giải pháp tái sử dụng được cho những yêu cầu trải rộng toàn ứng dụng. Ví dụ, giả sử bạn cần thay mọi giá trị response `null` bằng chuỗi rỗng `''`. Bạn có thể làm việc này chỉ với một dòng code, và bind interceptor ở cấp global để mọi handler đã đăng ký tự động dùng nó.

```typescript
@@filename()
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable()
export class ExcludeNullInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next
      .handle()
      .pipe(map(value => value === null ? '' : value ));
  }
}
@@switch
import { Injectable } from '@nestjs/common';
import { map } from 'rxjs/operators';

@Injectable()
export class ExcludeNullInterceptor {
  intercept(context, next) {
    return next
      .handle()
      .pipe(map(value => value === null ? '' : value ));
  }
}
```

#### Map exception <a id="exception-mapping"></a>

Một công dụng khác là ghi đè các exception được throw bằng operator `catchError()` của RxJS:

```typescript
@@filename(errors.interceptor)
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  BadGatewayException,
  CallHandler,
} from '@nestjs/common';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Injectable()
export class ErrorsInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next
      .handle()
      .pipe(
        catchError(err => throwError(() => new BadGatewayException())),
      );
  }
}
@@switch
import { Injectable, BadGatewayException } from '@nestjs/common';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

@Injectable()
export class ErrorsInterceptor {
  intercept(context, next) {
    return next
      .handle()
      .pipe(
        catchError(err => throwError(() => new BadGatewayException())),
      );
  }
}
```

#### Ghi đè stream <a id="stream-overriding"></a>

Đôi khi bạn có thể muốn bỏ qua hoàn toàn việc gọi handler và trả về một giá trị khác. Ví dụ điển hình là cache để cải thiện thời gian phản hồi. Hãy xem một **cache interceptor** đơn giản trả về response từ cache. Một bản implement thực tế còn cần xét đến các yếu tố như TTL, invalidate cache và kích thước cache, những thứ nằm ngoài phạm vi bài này. Ví dụ cơ bản sau minh họa ý tưởng chính.

```typescript
@@filename(cache.interceptor)
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable, of } from 'rxjs';

@Injectable()
export class CacheInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const isCached = true;
    if (isCached) {
      return of([]);
    }
    return next.handle();
  }
}
@@switch
import { Injectable } from '@nestjs/common';
import { of } from 'rxjs';

@Injectable()
export class CacheInterceptor {
  intercept(context, next) {
    const isCached = true;
    if (isCached) {
      return of([]);
    }
    return next.handle();
  }
}
```

`CacheInterceptor` của chúng ta có biến `isCached` và response `[]` được hard-code. Điểm mấu chốt là nó trả về một stream mới, tạo bằng hàm `of()` của RxJS, nên route handler **hoàn toàn không được gọi**. Khi ai đó gọi một endpoint dùng `CacheInterceptor`, response (một mảng rỗng được hard-code) sẽ được trả về ngay lập tức. Để xây dựng một giải pháp generic, hãy dùng `Reflector` cùng với một custom decorator, như mô tả trong chương [guard](/guards).

#### Thêm các operator khác <a id="more-operators"></a>

Thao tác stream bằng các operator của RxJS mở ra rất nhiều khả năng. Hãy xét một công dụng phổ biến khác: xử lý **timeout** cho các request tới route. Nếu một endpoint không trả về gì trong một khoảng thời gian nhất định, bạn muốn kết thúc request bằng một response lỗi. Cách khai báo sau cho phép làm điều đó:

```typescript
@@filename(timeout.interceptor)
import { Injectable, NestInterceptor, ExecutionContext, CallHandler, RequestTimeoutException } from '@nestjs/common';
import { Observable, throwError, TimeoutError } from 'rxjs';
import { catchError, timeout } from 'rxjs/operators';

@Injectable()
export class TimeoutInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      timeout(5000),
      catchError(err => {
        if (err instanceof TimeoutError) {
          return throwError(() => new RequestTimeoutException());
        }
        return throwError(() => err);
      }),
    );
  }
}
@@switch
import { Injectable, RequestTimeoutException } from '@nestjs/common';
import { throwError, TimeoutError } from 'rxjs';
import { catchError, timeout } from 'rxjs/operators';

@Injectable()
export class TimeoutInterceptor {
  intercept(context, next) {
    return next.handle().pipe(
      timeout(5000),
      catchError(err => {
        if (err instanceof TimeoutError) {
          return throwError(() => new RequestTimeoutException());
        }
        return throwError(() => err);
      }),
    );
  }
}
```

Nếu route handler không emit kết quả trong vòng 5 giây, `timeout()` sẽ làm stream thất bại với một `TimeoutError`, và interceptor map nó thành `RequestTimeoutException`. Việc hủy subscribe khỏi stream của handler không hủy được những công việc mà handler đã bắt đầu (như một query database đang chờ), nên hãy thêm logic tùy chỉnh trước khi throw `RequestTimeoutException` nếu bạn cần giải phóng resource.
