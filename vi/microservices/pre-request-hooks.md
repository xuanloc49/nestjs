### Pre-request hook

Pre-request hook là các hàm chạy trước mọi enhancer (guard, interceptor và pipe) ở mỗi lần gọi một pattern handler. Chúng là thứ tương đương với HTTP middleware ở microservice: nơi thiết lập context theo từng request mà guard và phần còn lại của pipeline cần nhìn thấy.

> info **Gợi ý** Interface `PreRequestHook` được export từ package `@nestjs/common`.

Hook chạy ở đầu chuỗi sau:

```
Incoming message
  └─ Pre-request hooks  (registration order)
       └─ Guards
            └─ Interceptors
                 └─ Pipes
                      └─ Handler
```

Các exception được throw bên trong một hook được bắt bởi cùng wrapper bao phủ phần còn lại của pipeline, nên các [exception filter](/microservices/exception-filters) hiện có của bạn sẽ xử lý chúng mà không cần cấu hình thêm.

#### Gắn hook <a id="binding-hooks"></a>

Đăng ký hook trên instance microservice bằng method `registerPreRequestHook()`, trước khi microservice được khởi tạo (tức là trước khi gọi `app.listen()` hoặc `app.init()`). Các hook được đăng ký sau khi khởi tạo sẽ bị bỏ qua, và Nest log một cảnh báo. Nhiều lời gọi sẽ cộng dồn hook theo thứ tự đăng ký.

Mỗi hook nhận một `ExecutionContext` và một hàm `next`. Gọi `next()` sẽ chuyển sang hook tiếp theo hoặc, khi không còn hook nào, sang pipeline guard → interceptor → pipe → handler. Hook phải trả về một `Observable`: hoặc là observable do `next()` tạo ra, hoặc một observable bọc nó.

> warning **Cảnh báo** Nếu một hook không gọi `next()`, handler sẽ không bao giờ chạy. Đây cũng là hợp đồng giống như HTTP middleware.

> info **Lưu ý** Trong một [ứng dụng hybrid](/faq/hybrid-application), `connectMicroservice()` khởi tạo microservice được kết nối ngay lập tức (trừ khi bạn truyền `deferInitialization: true` trong tham số thứ hai của nó), nên các hook được đăng ký trên instance trả về sau đó sẽ không được áp dụng.

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    { transport: Transport.TCP },
  );

  app.registerPreRequestHook((ctx, next) => {
    return next();
  });

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

  app.registerPreRequestHook((ctx, next) => {
    return next();
  });

  await app.listen();
}
await bootstrap();
```

#### Lan truyền AsyncLocalStorage <a id="asynclocalstorage-propagation"></a>

Một use case phổ biến là khởi tạo `AsyncLocalStorage` trước khi guard chạy, giúp store có sẵn trong suốt toàn bộ pipeline:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { Observable } from 'rxjs';
import { AsyncLocalStorage } from 'async_hooks';
import { randomUUID } from 'crypto';
import { AppModule } from './app.module.js';

export const als = new AsyncLocalStorage<{ correlationId: string }>();

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    { transport: Transport.TCP },
  );

  app.registerPreRequestHook((ctx, next) => {
    return new Observable(subscriber => {
      als.run({ correlationId: randomUUID() }, () => {
        next().subscribe(subscriber);
      });
    });
  });

  await app.listen();
}
await bootstrap();
@@switch
import { NestFactory } from '@nestjs/core';
import { Transport } from '@nestjs/microservices';
import { Observable } from 'rxjs';
import { AsyncLocalStorage } from 'async_hooks';
import { randomUUID } from 'crypto';
import { AppModule } from './app.module.js';

export const als = new AsyncLocalStorage();

async function bootstrap() {
  const app = await NestFactory.createMicroservice(AppModule, {
    transport: Transport.TCP,
  });

  app.registerPreRequestHook((ctx, next) => {
    return new Observable(subscriber => {
      als.run({ correlationId: randomUUID() }, () => {
        next().subscribe(subscriber);
      });
    });
  });

  await app.listen();
}
await bootstrap();
```

Vì hook chạy trước guard, `als.getStore()` trả về store đã được khởi tạo trong mọi guard, interceptor hay handler:

```typescript
@@filename(correlation.guard)
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { als } from './main.js';

@Injectable()
export class CorrelationGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const { correlationId } = als.getStore()!;
    return true;
  }
}
@@switch
import { Injectable } from '@nestjs/common';
import { als } from './main.js';

@Injectable()
export class CorrelationGuard {
  canActivate(context) {
    const { correlationId } = als.getStore();
    return true;
  }
}
```

#### Logging và metric <a id="logging-and-metrics"></a>

Bạn có thể áp dụng các operator của RxJS cho `Observable` mà `next()` trả về để theo dõi toàn bộ vòng đời của handler:

```typescript
@@filename(main)
import { tap, catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';

app.registerPreRequestHook((ctx, next) => {
  const handler = ctx.getHandler().name;
  const start = Date.now();

  return next().pipe(
    tap(() => console.log(`[${handler}] completed in ${Date.now() - start}ms`)),
    catchError(err => {
      console.error(`[${handler}] failed:`, err.message);
      return throwError(() => err);
    }),
  );
});
@@switch
import { tap, catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';

app.registerPreRequestHook((ctx, next) => {
  const handler = ctx.getHandler().name;
  const start = Date.now();

  return next().pipe(
    tap(() => console.log(`[${handler}] completed in ${Date.now() - start}ms`)),
    catchError(err => {
      console.error(`[${handler}] failed:`, err.message);
      return throwError(() => err);
    }),
  );
});
```

> info **Gợi ý** Pre-request hook là global: bạn không thể đăng ký chúng cho từng pattern riêng. Khi không có hook nào được đăng ký, Nest bỏ qua hoàn toàn chuỗi hook, nên tính năng này không thêm chi phí nào. Pre-request hook không áp dụng cho WebSocket gateway.
