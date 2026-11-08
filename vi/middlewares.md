### Middleware

Middleware là một hàm được gọi **trước** route handler. Các hàm middleware có quyền truy cập vào [request](https://expressjs.com/en/4x/api.html#req) object, [response](https://expressjs.com/en/4x/api.html#res) object, và hàm middleware `next()` trong chu trình request-response của ứng dụng. Hàm middleware **kế tiếp** thường được đặt trong một biến tên là `next`.

<figure><img class="illustrative-image" src="/assets/Middlewares_1.png" /></figure>

Mặc định, middleware của Nest tương đương với middleware của [Express](https://expressjs.com/en/guide/using-middleware.html). Tài liệu chính thức của Express mô tả khả năng của middleware như sau:

<blockquote class="external">
  Hàm middleware có thể làm những việc sau:
  <ul>
    <li>thực thi bất kỳ đoạn code nào.</li>
    <li>thay đổi request object và response object.</li>
    <li>kết thúc chu trình request-response.</li>
    <li>gọi hàm middleware kế tiếp trong stack.</li>
    <li>nếu hàm middleware hiện tại không kết thúc chu trình request-response, nó phải gọi <code>next()</code> để
      chuyển quyền điều khiển cho hàm middleware kế tiếp. Nếu không, request sẽ bị treo.</li>
  </ul>
</blockquote>

Bạn có thể implement middleware Nest tùy chỉnh dưới dạng một hàm hoặc một class có decorator `@Injectable()`. Class phải implement interface `NestMiddleware`, còn hàm thì không có yêu cầu gì đặc biệt. Hãy bắt đầu bằng việc implement một class middleware đơn giản.

> warning **Cảnh báo** Express và Fastify xử lý middleware khác nhau và có method signature khác nhau, còn Node adapter dùng signature của Express. Xem chương [HTTP adapter](/http/performance#middleware) để biết chi tiết.

```typescript
@@filename(logger.middleware)
import { Injectable, NestMiddleware } from '@nestjs/common';
import type { Request, Response, NextFunction } from 'express';

@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    console.log('Request...');
    next();
  }
}
@@switch
import { Injectable } from '@nestjs/common';

@Injectable()
export class LoggerMiddleware {
  use(req, res, next) {
    console.log('Request...');
    next();
  }
}
```

#### Dependency injection

Middleware của Nest hỗ trợ đầy đủ dependency injection. Giống như provider và controller, class middleware có thể **inject các dependency** có sẵn trong cùng module. Như thường lệ, dependency được inject qua `constructor`.

#### Áp dụng middleware <a id="applying-middleware"></a>

Middleware không được đăng ký trong decorator `@Module()`. Thay vào đó, bạn thiết lập nó trong method `configure()` của class module. Module có chứa middleware phải implement interface `NestModule`. Hãy thiết lập `LoggerMiddleware` ở cấp `AppModule`.

```typescript
@@filename(app.module)
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';
import { LoggerMiddleware } from './common/middleware/logger.middleware.js';
import { CatsModule } from './cats/cats.module.js';

@Module({
  imports: [CatsModule],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes('cats');
  }
}
@@switch
import { Module } from '@nestjs/common';
import { LoggerMiddleware } from './common/middleware/logger.middleware.js';
import { CatsModule } from './cats/cats.module.js';

@Module({
  imports: [CatsModule],
})
export class AppModule {
  configure(consumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes('cats');
  }
}
```

Trong ví dụ trên, `LoggerMiddleware` được áp dụng cho các route handler `/cats` định nghĩa trong `CatsController`. Để giới hạn middleware cho một request method cụ thể, truyền vào method `forRoutes()` một object chứa `path` của route và `method` của request. Ví dụ dưới đây import enum `RequestMethod` để chỉ định request method mong muốn.

```typescript
@@filename(app.module)
import { Module, NestModule, RequestMethod, MiddlewareConsumer } from '@nestjs/common';
import { LoggerMiddleware } from './common/middleware/logger.middleware.js';
import { CatsModule } from './cats/cats.module.js';

@Module({
  imports: [CatsModule],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes({ path: 'cats', method: RequestMethod.GET });
  }
}
@@switch
import { Module, RequestMethod } from '@nestjs/common';
import { LoggerMiddleware } from './common/middleware/logger.middleware.js';
import { CatsModule } from './cats/cats.module.js';

@Module({
  imports: [CatsModule],
})
export class AppModule {
  configure(consumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes({ path: 'cats', method: RequestMethod.GET });
  }
}
```

> info **Gợi ý** Method `configure()` có thể là bất đồng bộ. Khai báo nó với `async` để `await` một thao tác bất đồng bộ hoàn tất bên trong thân method.

> warning **Cảnh báo** Với Express adapter, Nest mặc định đăng ký các body parser `json` và `urlencoded` (`express.json()` và `express.urlencoded()`). Để tùy chỉnh các parser này thông qua `MiddlewareConsumer`, hãy tắt các parser mặc định bằng cách đặt tùy chọn `bodyParser` thành `false` khi tạo ứng dụng với `NestFactory.create()`.

#### Route wildcard <a id="route-wildcards"></a>

Middleware cũng hỗ trợ route theo pattern. Ví dụ, wildcard có tên (`*splat`) khớp với mọi tổ hợp ký tự trong một route. Trong ví dụ sau, middleware chạy cho mọi route bắt đầu bằng `abcd/`, bất kể phía sau có bao nhiêu ký tự.

```typescript
forRoutes({
  path: 'abcd/*splat',
  method: RequestMethod.ALL,
});
```

> info **Gợi ý** `splat` chỉ là tên của tham số wildcard và không có ý nghĩa đặc biệt gì. Bạn có thể dùng bất kỳ tên nào, ví dụ `*wildcard`.

Route path `'abcd/*splat'` khớp với `abcd/1`, `abcd/123`, `abcd/abc`, v.v. Path dạng chuỗi hiểu dấu gạch ngang (`-`) và dấu chấm (`.`) theo nghĩa đen. Tuy nhiên, `abcd/` không có thêm ký tự nào phía sau thì không khớp. Để khớp cả trường hợp này, hãy bọc wildcard trong dấu ngoặc nhọn để biến nó thành tùy chọn:

```typescript
forRoutes({
  path: 'abcd/{*splat}',
  method: RequestMethod.ALL,
});
```

#### Middleware consumer

`MiddlewareConsumer` là một class helper cung cấp vài method có sẵn để quản lý middleware. Tất cả các method này đều có thể **nối chuỗi** theo [kiểu fluent](https://en.wikipedia.org/wiki/Fluent_interface). Method `forRoutes()` nhận một chuỗi, nhiều chuỗi, một object `RouteInfo`, một class controller, hoặc nhiều class controller. Trong hầu hết trường hợp, bạn sẽ truyền vào một danh sách **controller** phân cách bằng dấu phẩy. Dưới đây là ví dụ với một controller:

```typescript
@@filename(app.module)
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';
import { LoggerMiddleware } from './common/middleware/logger.middleware.js';
import { CatsModule } from './cats/cats.module.js';
import { CatsController } from './cats/cats.controller.js';

@Module({
  imports: [CatsModule],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes(CatsController);
  }
}
@@switch
import { Module } from '@nestjs/common';
import { LoggerMiddleware } from './common/middleware/logger.middleware.js';
import { CatsModule } from './cats/cats.module.js';
import { CatsController } from './cats/cats.controller.js';

@Module({
  imports: [CatsModule],
})
export class AppModule {
  configure(consumer) {
    consumer
      .apply(LoggerMiddleware)
      .forRoutes(CatsController);
  }
}
```

> info **Gợi ý** Method `apply()` nhận một middleware hoặc nhiều tham số để chỉ định <a href="/middleware#multiple-middleware">nhiều middleware</a>.

#### Loại trừ route <a id="excluding-routes"></a>

Để **loại trừ** một số route khỏi việc áp dụng middleware, dùng method `exclude()`. Method này nhận một chuỗi, nhiều chuỗi, hoặc một object `RouteInfo` xác định các route cần loại trừ:

```typescript
consumer
  .apply(LoggerMiddleware)
  .exclude(
    { path: 'cats', method: RequestMethod.GET },
    { path: 'cats', method: RequestMethod.POST },
    'cats/{*splat}',
  )
  .forRoutes(CatsController);
```

Với ví dụ trên, `LoggerMiddleware` được bind vào mọi route định nghĩa trong `CatsController`, **ngoại trừ** những route khớp với ba mục truyền vào method `exclude()`.

> info **Gợi ý** Method `exclude()` hỗ trợ tham số wildcard thông qua package [path-to-regexp](https://github.com/pillarjs/path-to-regexp#parameters).

Các path truyền vào `exclude()` được khai báo không kèm [global prefix](/faq/global-prefix); Nest sẽ tự thêm prefix này, trừ khi route đã được loại khỏi global prefix. Nếu một mục loại trừ khớp với một path đã được loại khỏi global prefix và không có tham số hay wildcard, middleware cũng bị bỏ qua cho path đó (path này được phục vụ không kèm prefix). Việc so khớp này tuân theo chế độ phân biệt hoa thường của router.

```typescript
// main.ts
app.setGlobalPrefix('api', { exclude: ['health', 'health/ready'] });

// app.module.ts
consumer
  .apply(LoggerMiddleware)
  .exclude('health', 'health/*splat')
  .forRoutes('*splat');
```

Ở đây, `health/*splat` cũng bỏ qua middleware cho `/health/ready`. Nó không khớp với chính `/health`, nên `health` cũng được liệt kê.

#### Functional middleware

Class `LoggerMiddleware` mà ta đang dùng rất tối giản: không có member, không có method nào khác, và không có dependency. Middleware như thế này có thể được định nghĩa bằng một hàm thông thường thay vì class. Loại middleware này được gọi là **functional middleware**. Hãy chuyển logger middleware từ class sang hàm để thấy sự khác biệt:

```typescript
@@filename(logger.middleware)
import type { Request, Response, NextFunction } from 'express';

export function logger(req: Request, res: Response, next: NextFunction) {
  console.log('Request...');
  next();
}
@@switch
export function logger(req, res, next) {
  console.log('Request...');
  next();
}
```

Sau đó dùng nó trong `AppModule`:

```typescript
@@filename(app.module)
consumer
  .apply(logger)
  .forRoutes(CatsController);
```

> info **Gợi ý** Hãy cân nhắc dùng **functional middleware** mỗi khi middleware của bạn không cần dependency nào.

#### Nhiều middleware <a id="multiple-middleware"></a>

Để bind nhiều middleware chạy tuần tự, truyền vào method `apply()` một danh sách phân cách bằng dấu phẩy:

```typescript
consumer.apply(cors(), helmet(), logger).forRoutes(CatsController);
```

#### Global middleware

Để bind middleware vào tất cả các route đã đăng ký cùng lúc, dùng method `use()` của instance `INestApplication`:

```typescript
@@filename(main)
const app = await NestFactory.create(AppModule);
app.use(logger);
await app.listen(process.env.PORT ?? 3000);
```

> info **Gợi ý** Global middleware đăng ký bằng `app.use()` không truy cập được DI container, nên ở đó hãy dùng [functional middleware](middleware#functional-middleware). Cách khác là dùng class middleware và bind nó bằng `.forRoutes('*')` bên trong `AppModule` (hoặc bất kỳ module nào khác).

#### Xử lý lỗi <a id="error-handling"></a>

Khi middleware throw exception, [lớp xử lý exception](/exception-filters) của Nest sẽ bắt nó và gửi response phù hợp, giống hệt như với exception throw từ route handler. Cách được khuyên dùng là throw một `HttpException` (hoặc một class con có sẵn như `UnauthorizedException`):

```typescript
@@filename(auth.middleware)
import {
  Injectable,
  NestMiddleware,
  UnauthorizedException,
} from '@nestjs/common';
import type { Request, Response, NextFunction } from 'express';

@Injectable()
export class AuthMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    if (!req.headers.authorization) {
      throw new UnauthorizedException();
    }
    next();
  }
}
@@switch
import { Injectable, UnauthorizedException } from '@nestjs/common';

@Injectable()
export class AuthMiddleware {
  use(req, res, next) {
    if (!req.headers.authorization) {
      throw new UnauthorizedException();
    }
    next();
  }
}
```

Nếu middleware là bất đồng bộ, hãy khai báo `use()` là `async` (hoặc trả về `Promise`) để promise bị reject được chuyển tới lớp xử lý exception:

```typescript
@@filename(auth.middleware)
@Injectable()
export class AuthMiddleware implements NestMiddleware {
  constructor(private readonly authService: AuthService) {}

  async use(req: Request, res: Response, next: NextFunction) {
    const user = await this.authService.verify(req.headers.authorization);
    if (!user) {
      throw new UnauthorizedException();
    }
    req['user'] = user;
    next();
  }
}
```

Bạn cũng có thể truyền lỗi vào `next()`. Cách này hữu ích khi bọc các middleware kiểu Express có sẵn, vốn báo lỗi qua callback:

```typescript
use(req: Request, res: Response, next: NextFunction) {
  if (!req.headers.authorization) {
    return next(new UnauthorizedException());
  }
  next();
}
```

> warning **Cảnh báo** Vì middleware chạy trước khi route handler được chọn, chỉ có các exception filter **global** (đăng ký bằng `app.useGlobalFilters()` hoặc token `APP_FILTER`) mới bắt được exception throw từ middleware. Filter ở cấp method và cấp controller sẽ không được gọi, và việc bind filter vào class middleware bằng `@UseFilters()` là không được hỗ trợ.

> info **Gợi ý** Middleware đăng ký bằng `app.use()` được xử lý bởi nền tảng HTTP bên dưới (Express hoặc Fastify), không phải bởi `MiddlewareModule` của Nest. Hãy ưu tiên throw lỗi (hoặc gọi `next(err)`) từ middleware được bind bằng `MiddlewareConsumer`, để lớp xử lý exception có thể xử lý chúng.
