### Giới hạn tốc độ

Một kỹ thuật phổ biến để bảo vệ ứng dụng khỏi các cuộc tấn công brute-force là **rate limiting** (giới hạn tốc độ). Để bắt đầu, hãy cài package `@nestjs/throttler`.

```bash
$ npm i --save @nestjs/throttler
```

Sau khi cài xong, cấu hình `ThrottlerModule` như mọi package Nest khác, bằng method `forRoot()` hoặc `forRootAsync()`.

```typescript
@@filename(app.module)
@Module({
  imports: [
    ThrottlerModule.forRoot({
      throttlers: [
        {
          ttl: 60000,
          limit: 10,
        },
      ],
    }),
  ],
})
export class AppModule {}
```

Cách này đặt các tùy chọn global cho những route được bảo vệ trong ứng dụng: `ttl`, thời gian sống tính bằng mili giây, và `limit`, số request tối đa trong khoảng `ttl`.

Khi module đã được import, hãy chọn cách bind `ThrottlerGuard`. Mọi kiểu bind mô tả trong chương [guard](/guards#binding-guards) đều dùng được. Ví dụ, để bind guard ở cấp global, thêm provider này vào bất kỳ module nào:

```typescript
{
  provide: APP_GUARD,
  useClass: ThrottlerGuard
}
```

#### Nhiều định nghĩa throttler <a id="multiple-throttler-definitions"></a>

Đôi khi bạn muốn có nhiều định nghĩa throttling, như không quá 3 lời gọi mỗi giây, 20 lời gọi mỗi 10 giây, và 100 lời gọi mỗi phút. Để làm vậy, hãy định nghĩa chúng trong mảng với các tùy chọn có tên. Sau đó bạn có thể tham chiếu tới các tên này trong decorator `@SkipThrottle()` và `@Throttle()` để thay đổi tùy chọn cho từng route hoặc controller.

```typescript
@@filename(app.module)
@Module({
  imports: [
    ThrottlerModule.forRoot([
      {
        name: 'short',
        ttl: 1000,
        limit: 3,
      },
      {
        name: 'medium',
        ttl: 10000,
        limit: 20
      },
      {
        name: 'long',
        ttl: 60000,
        limit: 100
      }
    ]),
  ],
})
export class AppModule {}
```

#### Tùy biến <a id="customization"></a>

Có thể bạn muốn bind guard cho một controller hoặc ở cấp global, nhưng tắt giới hạn tốc độ cho một hoặc vài endpoint. Khi đó, hãy dùng decorator `@SkipThrottle()` để tắt throttler cho cả một class hoặc một route. Decorator `@SkipThrottle()` cũng nhận một object với key là chuỗi (tên throttler) và value là boolean. Điều này hữu ích khi bạn muốn loại trừ _phần lớn_ một controller, nhưng không phải mọi route, và để cấu hình việc bỏ qua theo từng bộ throttler nếu bạn có nhiều hơn một bộ. Nếu bạn không truyền object, mặc định là `{{ '{' }} default: true {{ '}' }}`.

```typescript
@SkipThrottle()
@Controller('users')
export class UsersController {}
```

Decorator `@SkipThrottle()` có thể bỏ qua một route hoặc một class, hoặc hủy việc bỏ qua cho một route nằm trong một class đã bị bỏ qua.

```typescript
@SkipThrottle()
@Controller('users')
export class UsersController {
  // Rate limiting is applied to this route.
  @SkipThrottle({ default: false })
  dontSkip() {
    return 'List users work with Rate limiting.';
  }
  // This route will skip rate limiting.
  doSkip() {
    return 'List users work without Rate limiting.';
  }
}
```

Decorator `@Throttle()` ghi đè `limit` và `ttl` đã đặt trong root module, để cho các tùy chọn bảo mật chặt hơn hoặc lỏng hơn. Bạn có thể áp dụng nó lên class hoặc method. Kể từ version 5, decorator nhận một object có key là tên các bộ throttler và value là object có key `limit` và `ttl` (và, tùy chọn, `blockDuration`), tương tự như các tùy chọn truyền vào root module. Nếu bạn không đặt tên trong tùy chọn gốc, hãy dùng key `default`:

```typescript
// Override default configuration for Rate limiting and duration.
@Throttle({ default: { limit: 3, ttl: 60000 } })
@Get()
findAll() {
  return "List users works with custom rate limiting.";
}
```

#### Proxy <a id="proxies"></a>

Nếu ứng dụng của bạn chạy đằng sau một proxy server, hãy cấu hình HTTP adapter để tin tưởng proxy. Xem các tùy chọn `trust proxy` của [Express](http://expressjs.com/en/guide/behind-proxies.html), [Fastify](https://www.fastify.io/docs/latest/Reference/Server/#trustproxy) và [Node adapter](/http/performance#node-adapter-options).

Ví dụ sau bật `trust proxy` cho Express adapter:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';
import { NestExpressApplication } from '@nestjs/platform-express';

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  app.set('trust proxy', 'loopback'); // Trust requests from the loopback address
  await app.listen(3000);
}

await bootstrap();
@@switch
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';
import { NestExpressApplication } from '@nestjs/platform-express';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.set('trust proxy', 'loopback'); // Trust requests from the loopback address
  await app.listen(3000);
}

await bootstrap();
```

Với Fastify adapter, hãy truyền tùy chọn `trustProxy`:

```typescript
@@filename(main)
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter({ trustProxy: 'loopback' }), // Trust requests from the loopback address
);
@@switch
const app = await NestFactory.create(
  AppModule,
  new FastifyAdapter({ trustProxy: 'loopback' }), // Trust requests from the loopback address
);
```

> warning **Cảnh báo** Trên Fastify v5.12.1 trở lên, phiên bản mà `@nestjs/platform-fastify` v12 cài, một số truyền vào `trustProxy` (một số hop như `1`) sẽ khiến Fastify không tin tưởng proxy nào cả. Khi đó `request.ip` là địa chỉ của proxy, và throttler đếm mọi client đằng sau proxy như một. Thay vào đó, hãy truyền địa chỉ hoặc dải địa chỉ của proxy, như ví dụ trên.

Với Node adapter, hãy truyền tùy chọn `trustProxy` của nó, tùy chọn này nhận cùng các giá trị như của Fastify (ở đây một số cũng không tin tưởng proxy nào):

```typescript
@@filename(main)
const app = await NestFactory.create<NestNodeApplication>(
  AppModule,
  new NodeAdapter({ trustProxy: 'loopback' }), // Trust requests from the loopback address
);
@@switch
const app = await NestFactory.create(
  AppModule,
  new NodeAdapter({ trustProxy: 'loopback' }), // Trust requests from the loopback address
);
```

Bật `trust proxy` cho phép bạn lấy địa chỉ IP gốc từ header `X-Forwarded-For`. Bạn cũng có thể ghi đè method `getTracker()` để lấy địa chỉ IP từ header này thay vì dựa vào `req.ip`. Ví dụ sau dành cho Express và Node adapter, hai cái này sắp xếp `req.ips` theo cùng cách:

```typescript
@@filename(throttler-behind-proxy.guard)
import { ThrottlerGuard } from '@nestjs/throttler';
import { Injectable } from '@nestjs/common';

@Injectable()
export class ThrottlerBehindProxyGuard extends ThrottlerGuard {
  protected async getTracker(req: Record<string, any>): Promise<string> {
    return req.ips.length ? req.ips[0] : req.ip; // individualize IP extraction to meet your own needs
  }
}
```

> info **Gợi ý** Trên Fastify, `request.ips` được sắp xếp từ địa chỉ gần nhất tới xa nhất, nên mục đầu tiên là địa chỉ của proxy, và guard này sẽ đếm mọi client đằng sau proxy như một. Ở đó hãy giữ tracker mặc định, vốn dùng `request.ip`. Xem API của request object cho [Express](https://expressjs.com/en/api.html#req.ips) và [Fastify](https://www.fastify.io/docs/latest/Reference/Request/).

#### WebSocket <a id="websockets"></a>

Module này hoạt động với WebSocket, nhưng cần kế thừa class `ThrottlerGuard` và ghi đè method `handleRequest()` của nó, như sau:

```typescript
@Injectable()
export class WsThrottlerGuard extends ThrottlerGuard {
  async handleRequest(requestProps: ThrottlerRequest): Promise<boolean> {
    const { context, limit, ttl, throttler, blockDuration, generateKey } =
      requestProps;

    const client = context.switchToWs().getClient();
    const tracker = client._socket.remoteAddress;
    const key = generateKey(context, tracker, throttler.name);
    const { totalHits, timeToExpire, isBlocked, timeToBlockExpire } =
      await this.storageService.increment(
        key,
        ttl,
        limit,
        blockDuration,
        throttler.name,
      );

    // Throw an error when the user reached their limit.
    if (isBlocked) {
      await this.throwThrottlingException(context, {
        limit,
        ttl,
        key,
        tracker,
        totalHits,
        timeToExpire,
        isBlocked,
        timeToBlockExpire,
      });
    }

    return true;
  }
}
```

> info **Gợi ý** Ví dụ trên đọc địa chỉ client từ `client._socket`, cách này hoạt động với package `@nestjs/platform-ws`. Nếu bạn dùng `@nestjs/platform-socket.io`, hãy thay `client._socket` bằng `client.conn`.

Hãy lưu ý những điều sau khi làm việc với WebSocket:

- Đừng đăng ký guard này bằng `APP_GUARD` hay `app.useGlobalGuards()`. Global guard cũng chạy cho các route HTTP, còn guard này chỉ xử lý context WebSocket.
- Khi đạt tới giới hạn, Nest phát ra event `exception`, nên hãy đảm bảo có sẵn listener cho nó.

> info **Gợi ý** Khi bạn cấu hình [nhiều định nghĩa throttler](/security/rate-limiting#multiple-throttler-definitions), `handleRequest()` chạy một lần cho mỗi bộ throttler. Hãy truyền `throttler.name` từ `ThrottlerRequest` khi sinh storage key và khi gọi `storageService.increment()`, như ở trên, để mỗi throttler có tên theo dõi giới hạn riêng của nó.

#### GraphQL

`ThrottlerGuard` cũng hoạt động với request GraphQL. Một lần nữa, hãy kế thừa guard, nhưng lần này ghi đè method `getRequestResponse()`:

```typescript
@Injectable()
export class GqlThrottlerGuard extends ThrottlerGuard {
  getRequestResponse(context: ExecutionContext) {
    const gqlCtx = GqlExecutionContext.create(context);
    const ctx = gqlCtx.getContext();
    return { req: ctx.req, res: ctx.res };
  }
}
```

#### Cấu hình <a id="configuration"></a>

Các tùy chọn sau hợp lệ cho mỗi object trong mảng truyền vào `ThrottlerModule`:

<table>
  <tr>
    <td><code>name</code></td>
    <td>tên dùng nội bộ để theo dõi bộ throttler nào đang được dùng. Mặc định là <code>default</code> nếu không truyền. Với throttler có tên, tên cũng được nối vào các header giới hạn tốc độ của response (ví dụ <code>X-RateLimit-Remaining-long</code>)</td>
  </tr>
  <tr>
    <td><code>ttl</code></td>
    <td>số mili giây mà mỗi request được giữ trong storage</td>
  </tr>
  <tr>
    <td><code>limit</code></td>
    <td>số request tối đa trong khoảng TTL</td>
  </tr>
  <tr>
    <td><code>blockDuration</code></td>
    <td>số mili giây mà request bị chặn khi đã đạt tới giới hạn. Mặc định bằng giá trị <code>ttl</code></td>
  </tr>
  <tr>
    <td><code>ignoreUserAgents</code></td>
    <td>một mảng biểu thức chính quy khớp với các user agent cần bỏ qua khi throttle request</td>
  </tr>
  <tr>
    <td><code>skipIf</code></td>
    <td>một hàm nhận <code>ExecutionContext</code> và trả về <code>boolean</code> để bỏ qua logic của throttler. Giống như <code>@SkipThrottle()</code>, nhưng dựa trên request</td>
  </tr>
  <tr>
    <td><code>getTracker</code></td>
    <td>một hàm ghi đè logic tracker mặc định cho bộ throttler này (xem bảng bên dưới)</td>
  </tr>
  <tr>
    <td><code>generateKey</code></td>
    <td>một hàm ghi đè logic sinh key mặc định cho bộ throttler này (xem bảng bên dưới)</td>
  </tr>
  <tr>
    <td><code>setHeaders</code></td>
    <td>có thêm các header giới hạn tốc độ vào response hay không. Mặc định là <code>true</code></td>
  </tr>
</table>

Để thiết lập storage tùy chỉnh, hoặc áp dụng một số tùy chọn ở trên ở cấp global cho mọi bộ throttler, hãy truyền một options object thay vì mảng. Định nghĩa các bộ throttler trong thuộc tính `throttlers` của nó, và dùng các tùy chọn trong bảng sau:

<table>
  <tr>
    <td><code>storage</code></td>
    <td>một storage service tùy chỉnh để theo dõi việc throttle. Xem <a href="/security/rate-limiting#storages">Storage</a></td>
  </tr>
  <tr>
    <td><code>ignoreUserAgents</code></td>
    <td>một mảng biểu thức chính quy khớp với các user agent cần bỏ qua khi throttle request</td>
  </tr>
  <tr>
    <td><code>skipIf</code></td>
    <td>một hàm nhận <code>ExecutionContext</code> và trả về <code>boolean</code> để bỏ qua logic của throttler. Giống như <code>@SkipThrottle()</code>, nhưng dựa trên request</td>
  </tr>
  <tr>
    <td><code>throttlers</code></td>
    <td>một mảng các bộ throttler, định nghĩa theo bảng ở trên</td>
  </tr>
  <tr>
    <td><code>errorMessage</code></td>
    <td>một <code>string</code>, hoặc một hàm nhận <code>ExecutionContext</code> và <code>ThrottlerLimitDetail</code> rồi trả về <code>string</code>, để ghi đè message lỗi mặc định của throttler</td>
  </tr>
  <tr>
    <td><code>getTracker</code></td>
    <td>một hàm nhận request và <code>ExecutionContext</code> rồi trả về <code>string</code> (hoặc một <code>Promise</code> của nó), ghi đè logic mặc định của method <code>getTracker()</code></td>
  </tr>
  <tr>
    <td><code>generateKey</code></td>
    <td>một hàm nhận <code>ExecutionContext</code>, <code>string</code> tracker và tên throttler dạng <code>string</code>, rồi trả về <code>string</code> dùng làm storage key cho giá trị giới hạn tốc độ. Hàm này ghi đè logic mặc định của method <code>generateKey()</code></td>
  </tr>
  <tr>
    <td><code>setHeaders</code></td>
    <td>có thêm các header giới hạn tốc độ vào response hay không. Mặc định là <code>true</code></td>
  </tr>
  <tr>
    <td><code>ipv6SubnetPrefix</code></td>
    <td>độ dài prefix dùng để gom các địa chỉ IPv6 vào một tracker duy nhất, để một client không thể lách giới hạn bằng cách xoay vòng qua các địa chỉ trong subnet của nó. Chỉ áp dụng cho tracker có sẵn (không áp dụng cho <code>getTracker</code> tùy chỉnh). Mặc định là <code>64</code></td>
  </tr>
</table>

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Có thể bạn muốn load cấu hình giới hạn tốc độ theo kiểu bất đồng bộ. Hãy dùng method `forRootAsync()`, method này hỗ trợ dependency injection và các method `async`.

Một cách là dùng hàm factory:

```typescript
@Module({
  imports: [
    ThrottlerModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => [
        {
          ttl: config.get('THROTTLE_TTL'),
          limit: config.get('THROTTLE_LIMIT'),
        },
      ],
    }),
  ],
})
export class AppModule {}
```

Bạn cũng có thể dùng cú pháp `useClass`:

```typescript
@Module({
  imports: [
    ThrottlerModule.forRootAsync({
      imports: [ConfigModule],
      useClass: ThrottlerConfigService,
    }),
  ],
})
export class AppModule {}
```

Cách này hoạt động miễn là `ThrottlerConfigService` implement interface `ThrottlerOptionsFactory`.

#### Storage <a id="storages"></a>

Storage có sẵn là một cache trong bộ nhớ, theo dõi các request cho đến khi TTL của chúng trôi qua. Bạn có thể truyền storage của riêng mình vào tùy chọn `storage` của `ThrottlerModule`, miễn là class đó implement interface `ThrottlerStorage`.

Với các server phân tán, bạn có thể dùng storage provider của cộng đồng cho [Redis](https://github.com/jmcdo29/nest-lab/tree/main/packages/throttler-storage-redis) để có một nguồn sự thật duy nhất.

> info **Lưu ý** `ThrottlerStorage` có thể được import từ `@nestjs/throttler`.

#### Helper thời gian <a id="time-helpers"></a>

`@nestjs/throttler` export năm hàm helper giúp biểu diễn thời gian dễ đọc hơn so với số mili giây thô: `seconds`, `minutes`, `hours`, `days` và `weeks`. Mỗi hàm trả về số mili giây tương đương. Ví dụ, `seconds(5)` trả về `5000`.

#### Hướng dẫn chuyển đổi <a id="migration-guide"></a>

Khi chuyển sang version 5 trở lên, với hầu hết ứng dụng, chỉ cần bọc các tùy chọn của bạn trong một mảng là đủ.

Nếu bạn dùng storage tùy chỉnh, hãy bọc `ttl` và `limit` trong một mảng và gán nó cho thuộc tính `throttlers` của options object.

Decorator `@SkipThrottle()` giờ nhận một object tùy chọn với key là chuỗi (tên throttler) và value là boolean, mặc định là `{{ '{' }} default: true {{ '}' }}`.

Decorator `@Throttle()` giờ nhận một object có key là chuỗi, tức tên các bộ throttler (một lần nữa, là `'default'` nếu không đặt tên), và value là object có key `limit` và `ttl`.

> warning **Cảnh báo** `ttl` giờ tính bằng **mili giây**. Để giữ `ttl` tính bằng giây cho dễ đọc, hãy dùng helper `seconds` từ package này, helper này nhân giá trị với 1000.

Để biết thêm thông tin, xem [mục changelog 5.0](https://github.com/nestjs/throttler/blob/master/CHANGELOG.md#501).
