### Migrate từ Fastify

Một ứng dụng Fastify có thể chuyển sang Nest mà vẫn chạy trên Fastify: các plugin của bạn vẫn hoạt động, và các route được chuyển từng cái một hoặc tất cả cùng lúc.

Nest chạy trên Fastify qua `FastifyAdapter`, nên đây không phải là đổi server. Router, các plugin, JSON schema và việc serialize vẫn giữ nguyên, kể cả cách path được so khớp, cách query string được parse và kích thước tối đa của body. Những gì bạn thêm vào là cấu trúc xung quanh chúng: module, dependency injection, và guard cùng pipe thay cho các hook được đăng ký theo từng route.

#### Chọn cách tiếp cận <a id="choose-an-approach"></a>

| Câu hỏi | Từng route một | Tất cả cùng lúc |
| --- | --- | --- |
| Nó hoạt động thế nào? | Nest chạy trên instance Fastify của bạn, và các route được chuyển sang nó từng cái một | Một ứng dụng Nest mới thay thế ứng dụng Fastify trong một lần release |
| Cái gì được deploy? | Mỗi route được chuyển, một cách độc lập | Mọi thứ, một lần |
| Việc phát triển tính năng thì sao? | Vẫn tiếp tục, và các endpoint mới được viết trong Nest | Phải chờ, hoặc viết hai lần, cho tới khi chuyển đổi |
| Quay lui thế nào? | Khôi phục một route | Deploy bản release Fastify cuối cùng |
| Phiên bản Fastify nào? | Fastify 5, nên hãy nâng cấp trước | Bất kỳ, vì ứng dụng Fastify không bị động tới |
| Các plugin hiện có thì sao? | Chúng vẫn chạy, cả cho route của Nest | Bạn đăng ký lại chúng trên ứng dụng Nest |
| Có hai phong cách trong code bao lâu? | Cho tới khi route cuối cùng được chuyển | Không bao giờ |

Hãy chuyển từng route một khi ứng dụng lớn, khi có nhiều người cùng làm, hoặc khi nó không thể chờ. Hãy chuyển tất cả cùng lúc khi nó đủ nhỏ để review như một thay đổi duy nhất và bạn có thể cố định những gì nó làm bằng test. Cách đó cũng phù hợp với một [coding agent](/recipes/fastify-migration#give-it-to-a-coding-agent).

#### Từng route một <a id="one-route-at-a-time"></a>

Ứng dụng Fastify giữ các route, plugin và error handler của nó, các endpoint mới được viết trong Nest, và các endpoint hiện có được chuyển sang khi bạn sửa chúng lần tới. Cả hai trả lời trên cùng một port, nên client không nhận ra, và mỗi bước đều có thể được deploy độc lập.

##### Yêu cầu <a id="requirements"></a>

- **Fastify 5.** `FastifyAdapter` của Nest đăng ký các plugin yêu cầu phiên bản này, nên một instance Fastify 4 sẽ thất bại ngay khi Nest khởi động. Hãy nâng cấp ứng dụng trước.
- **TypeScript.** Code Nest trên trang này là TypeScript. Nếu ứng dụng Fastify được viết bằng JavaScript, các file của nó có thể giữ nguyên: tùy chọn `allowJs` của TypeScript biên dịch chúng cùng phần còn lại.

Cài Nest cạnh Fastify:

```bash
$ npm i --save @nestjs/core @nestjs/common @nestjs/platform-fastify reflect-metadata rxjs
```

##### Chạy Nest trên ứng dụng Fastify <a id="run-nest-on-the-fastify-app"></a>

Nest thường tự tạo instance Fastify của riêng nó. Hãy đưa cho nó instance của bạn thay vào đó. Dừng việc ứng dụng tự lắng nghe, và để một hàm trả về nó. Nest đặt error handler và not-found handler riêng của instance, nên có hai điều phải thay đổi:

- Chuyển `setErrorHandler()` vào một plugin chứa các route của bạn. Nó vẫn tiếp tục xử lý lỗi của chúng, và Fastify sẽ không cảnh báo về việc nó bị ghi đè.
- Gỡ bỏ `setNotFoundHandler()`. Nest từ chối khởi động với `Not found handler already set`, và nó tự trả lời các route không tồn tại.

```typescript
@@filename(legacy/app)
export async function buildLegacyApp() {
  const app = Fastify();
  await app.register(helmet);
  await app.register(auth); // decorates the instance and the request
  app.addHook('onRequest', async (request, reply) => {
    reply.header('x-request-id', request.headers['x-request-id'] ?? 'generated');
  });
  await app.register(async (legacy) => {
    legacy.setErrorHandler(errorHandler);
    await legacy.register(ordersRoutes, { prefix: '/api/orders' });
    await legacy.register(miscRoutes, { prefix: '/api' });
  });
  // await app.listen({ port: 3000 }); <- Nest listens from now on
  return app;
}
```

Sau đó truyền nó cho `FastifyAdapter`, và để Nest lắng nghe:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, type NestFastifyApplication } from '@nestjs/platform-fastify';
import { AppModule } from './app.module.js';
import { buildLegacyApp } from './legacy/app.js';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter(await buildLegacyApp()),
  );
  await app.listen(process.env.PORT ?? 3000);
}

await bootstrap();
```

Giờ cả hai cùng phục vụ request từ một instance Fastify:

- Các route Fastify trả lời như trước đây, và lỗi của chúng tới error handler riêng của chúng.
- Các plugin và hook được đăng ký trên root instance cũng áp dụng cho route của Nest, nên `helmet` và hook `onRequest` ở trên chạy cho chúng, và `request.jwtVerify()` hoạt động bên trong một guard của Nest.
- Các hook được đăng ký bên trong một plugin được đóng gói vẫn ở trong đó, như mọi khi, nên chúng không chạy cho route của Nest.
- Lỗi trong route của Nest đi qua các [exception filter](/exception-filters) của nó, và một request tới route mà cả hai đều không có sẽ nhận response `404` của Nest.

##### Chuyển một route <a id="move-a-route"></a>

Viết route trong Nest, và xóa nó khỏi Fastify trong cùng thay đổi. Router của Fastify từ chối trùng lặp, nên khi cả hai cùng có trong code, ứng dụng sẽ dừng lúc khởi động với `Method 'GET' already declared for route`. Một plugin bạn đang dùng có thể làm nền cho một [guard](/guards), và `@RouteSchema()` nhận JSON schema mà route đã có:

```typescript
@@filename(authenticated.guard)
@Injectable()
export class AuthenticatedGuard implements CanActivate {
  constructor(private readonly users: UsersRepository) {}

  async canActivate(context: ExecutionContext) {
    const request = context.switchToHttp().getRequest();
    try {
      const { sub } = await request.jwtVerify();
      request.user = await this.users.find(sub);
      return true;
    } catch {
      throw new UnauthorizedException();
    }
  }
}
```

```typescript
@@filename(me.controller)
@Controller('api')
export class MeController {
  @Get('me')
  @UseGuards(AuthenticatedGuard)
  @RouteSchema({
    response: {
      200: {
        type: 'object',
        properties: { id: { type: 'string' }, email: { type: 'string' } },
      },
    },
  })
  me(@Req() request: { user: User }) {
    return request.user;
  }
}
```

Hãy đọc [Giữ những gì sẽ thay đổi mà không báo lỗi](/recipes/fastify-migration#keep-what-would-change-without-an-error) trong lúc làm. Nó áp dụng cho mọi route được chuyển, và response schema ở trên có mặt chính là vì nó.

##### Hoàn tất migration <a id="finish-the-migration"></a>

Khi các route Fastify đã hết, hãy đăng ký các plugin trên ứng dụng Nest bằng `app.register()`, biến error handler thành một [exception filter](/exception-filters), xóa thư mục `legacy`, và tạo ứng dụng bằng `new FastifyAdapter()`.

#### Tất cả cùng lúc <a id="all-at-once"></a>

Một ứng dụng Nest mới thay thế ứng dụng Fastify trong một lần release. Cho tới lúc đó ứng dụng Fastify giữ nguyên, và nó là tham chiếu cho những gì ứng dụng mới phải làm. Hãy giữ `FastifyAdapter` trong suốt quá trình migration, kể cả khi bạn định đổi adapter sau này: điều đó giữ nguyên router, việc parse query, giới hạn body và cú pháp path, nên ít thứ có thể thay đổi cùng lúc hơn.

##### Cố định API bằng test <a id="pin-the-api-with-tests"></a>

Viết các test chỉ biết URL, để cùng các test chạy được trên cả hai ứng dụng. Duyệt qua mọi plugin và route, và bao phủ status code, body và các header quan trọng của mỗi route, cho cả trường hợp thất bại lẫn thành công. Kiểm tra rằng các field mà một response schema loại bỏ vẫn bị loại bỏ:

```typescript
import assert from 'node:assert/strict';
import { test } from 'node:test';

const BASE = process.env.BASE_URL ?? 'http://localhost:3000';

test('the response schema hides internal fields', async () => {
  const res = await fetch(`${BASE}/api/me`, {
    headers: { authorization: `Bearer ${token}` },
  });
  assert.deepEqual(await res.json(), { id: 'u2', email: 'bob@example.com' });
});

test('authentication comes before validation', async () => {
  const res = await fetch(`${BASE}/api/orders`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ total: -1 }),
  });
  assert.equal(res.status, 401);
});
```

Chạy chúng trên ứng dụng Fastify cho tới khi tất cả đều pass, trước khi viết bất kỳ dòng code Nest nào:

```bash
$ BASE_URL=http://localhost:3000 node --test test/contract.test.mjs
```

##### Chuyển đổi ứng dụng <a id="translate-the-application"></a>

Tạo ứng dụng Nest bằng `nest new` cạnh ứng dụng Fastify, [chuyển nó sang `FastifyAdapter`](/http/performance#fastify-adapter), và chuyển mỗi plugin chứa route thành một controller:

| Fastify | Nest |
| --- | --- |
| `app.register(routes, {{ '{' }} prefix {{ '}' }})` | Một [controller](/controllers), `@Controller('api/orders')`, trong một [module](/modules) |
| `app.get('/:id', handler)` | `@Get(':id')` trên một method |
| `request.params`, `request.query`, `request.body` | `@Param()`, `@Query()`, `@Body()` |
| `schema: {{ '{' }} querystring, body, response {{ '}' }}` | `@RouteSchema()` từ `@nestjs/platform-fastify`, với cùng các JSON schema |
| `onRequest: app.authenticate` | Một [guard](/guards) |
| `preHandler: app.requireRole('admin')` | Metadata trên route, được một guard đọc |
| Một decorator như `request.jwtVerify()` | Cùng lời gọi đó trên `@Req()`, với plugin đã được đăng ký |
| `reply.code(201).send(x)` | `return x`, kèm `@HttpCode()` khi status không phải mặc định |
| `reply.code(204).send()` | `@HttpCode(204)`, và không trả về gì |
| `reply.redirect(url, 301)` | `@Redirect(url, 301)` |
| `reply.setCookie()` | `@Res({{ '{' }} passthrough: true {{ '}' }}) reply`, sau đó `reply.setCookie()` và `return` như thường lệ |
| `reply.type('application/json')` | `@Header('content-type', 'application/json')` |
| `reply.send(stream)` | `new StreamableFile(stream, {{ '{' }} type {{ '}' }})` |
| `await request.file()` | Cùng lời gọi đó trên `@Req()`, với `@fastify/multipart` đã được đăng ký |
| `app.register(plugin, options)` | `app.register(plugin, options)` |
| `app.addHook('onRequest', fn)` | `app.getHttpAdapter().getInstance().addHook('onRequest', fn)` |
| `setErrorHandler()` và `setNotFoundHandler()` | Một [exception filter](/exception-filters) global |
| Một plugin decorate instance bằng một database pool | Một [provider](/fundamentals/custom-providers#value-providers-usevalue) |

Đường dẫn route giữ nguyên, vì cùng một router đọc chúng: `search/:term?`, `items/:id(^\\d+$)`, và `assets/*`, với `@Param('*')`.

##### Giữ những gì sẽ thay đổi mà không báo lỗi <a id="keep-what-would-change-without-an-error"></a>

Hai điểm trong số này làm lộ dữ liệu mà không có lỗi nào cả, nên hãy kiểm tra chúng trước:

| Trong Fastify | Trong một ứng dụng Nest | Để giữ hành vi cũ |
| --- | --- | --- |
| Một response schema loại bỏ mọi field mà nó không liệt kê, nên handler có thể trả về toàn bộ bản ghi | Không có schema, mọi field đều được gửi đi, kể cả `passwordHash` | `@RouteSchema({{ '{' }} response {{ '}' }})` trên mỗi route từng có schema |
| Một `POST` trả lời `200`, và `response: {{ '{' }} 200: schema {{ '}' }}` được áp dụng | Một `POST` trả lời `201`, nên một schema đánh key theo `200` không còn được áp dụng, và các field cũng được trả về | `@HttpCode(200)`, hoặc đánh key schema theo `201` |
| Việc xác thực trong `onRequest` chạy trước validation, nên một request không hợp lệ và không có token sẽ nhận `401` | `@RouteSchema({{ '{' }} body {{ '}' }})` validate trước mọi guard, nên request đó nhận lỗi validation | Validate bằng một [pipe](/application/validation#schema-based-validation), `@Body({{ '{' }} schema {{ '}' }})`, pipe này chạy sau guard, trên những route mà điều này quan trọng |
| Lỗi có cấu trúc mà handler của bạn đặt cho chúng | `{{ '{' }} statusCode, message, error {{ '}' }}` | Một exception filter global |
| Một lỗi validation tới handler của bạn với `err.validation` | Nó tới filter theo cùng cách, với `exception.validation` | Cùng filter đó |
| Một route không tồn tại nhận not-found handler của bạn | `NotFoundException`, với body của Nest | Cùng filter đó |

Filter phải giữ cấu trúc lỗi của bạn cho mọi lỗi, kể cả những lỗi mà Nest và Fastify tự phát sinh. Các lỗi về body như JSON sai định dạng hay body vượt giới hạn tới dưới dạng một `HttpException`:

```typescript
@@filename(common/api-exception.filter)
@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  catch(exception: any, host: ArgumentsHost) {
    const http = host.switchToHttp();
    const request = http.getRequest<FastifyRequest>();
    const reply = http.getResponse<FastifyReply>();
    const send = (status: number, code: string, message: string) =>
      reply.code(status).send({ error: { code, message } });

    if (exception instanceof ApiError) {
      return send(exception.status, exception.code, exception.message);
    }
    if (exception instanceof NotFoundException) {
      return send(404, 'NOT_FOUND', `No route for ${request.method} ${request.url}`);
    }
    if (exception?.validation) {
      return send(422, 'INVALID_INPUT', exception.message);
    }
    const status =
      exception instanceof HttpException ? exception.getStatus() : exception?.statusCode;
    if (status === 400) {
      return send(400, 'BAD_REQUEST', 'Malformed request');
    }
    if (status && status < 500) {
      return send(status, exception.code ?? 'ERROR', exception.message);
    }
    return send(500, 'INTERNAL', 'Something went wrong');
  }
}
```

```typescript
@@filename(main)
async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter(),
  );
  await app.register(helmet);
  await app.register(cors, { origin: 'https://shop.example.com', credentials: true });
  await app.register(cookie);
  await app.register(multipart, { limits: { fileSize: 1024 * 1024 } });
  await app.register(fastifyStatic, {
    root: join(import.meta.dirname, '..', 'public'),
    prefix: '/static/',
  });
  await app.register(jwt, { secret: process.env.JWT_SECRET });
  app.getHttpAdapter().getInstance().addHook('onRequest', async (request: FastifyRequest, reply: FastifyReply) => {
    reply.header('x-request-id', request.headers['x-request-id'] ?? 'generated');
  });
  app.useGlobalFilters(new ApiExceptionFilter());
  await app.listen(process.env.PORT ?? 3000);
}

await bootstrap();
```

##### Chuyển đổi <a id="switch-over"></a>

Chạy cùng các test trên ứng dụng Nest, và sửa ứng dụng chứ không sửa test:

```bash
$ BASE_URL=http://localhost:3001 node --test test/contract.test.mjs
```

Khi chúng pass, hãy deploy nó thay cho ứng dụng Fastify, và giữ bản release Fastify cuối cùng ở trạng thái có thể deploy cho tới khi bản mới đã phục vụ lưu lượng thật.

#### Giao cho một coding agent <a id="give-it-to-a-coding-agent"></a>

Cách tiếp cận nào cũng làm được với một coding agent, và tất cả cùng lúc là lựa chọn phù hợp hơn khi ứng dụng đủ nhỏ để review trong một thay đổi. Hãy chỉ cho agent trang này và buộc nó tuân theo các test, để nó không thể tuyên bố thành công với code chỉ đơn thuần biên dịch được:

```bash
Migrate this Fastify application to NestJS all at once, on the FastifyAdapter,
following https://docs.nestjs.com/recipes/fastify-migration.md.

1. Before changing anything, write black-box HTTP tests that cover every
   route: status codes, bodies and important headers, failures included.
   Assert that fields a response schema removes stay removed.
   Run them against the Fastify app until they all pass.
2. Build the Nest application next to it, using the page's translation table.
3. Check every row of "Keep what would change without an error".
4. Run the same tests against the Nest application. Don't edit a test to
   make it pass. If behavior has to change, stop and tell me.
```
