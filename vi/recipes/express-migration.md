### Migrate từ Express

Một ứng dụng Express có thể chuyển sang Nest từng route một, với cả hai cùng phục vụ request, hoặc tất cả cùng lúc, trong một lần release. Trang này nói về cả hai cách.

#### Chọn cách tiếp cận <a id="choose-an-approach"></a>

| Câu hỏi | Từng route một | Tất cả cùng lúc |
| --- | --- | --- |
| Nó hoạt động thế nào? | Nest chạy trên ứng dụng Express của bạn, và các route được chuyển sang nó từng cái một | Một ứng dụng Nest mới thay thế ứng dụng Express trong một lần release |
| Cái gì được deploy? | Mỗi route được chuyển, một cách độc lập | Mọi thứ, một lần |
| Việc phát triển tính năng thì sao? | Vẫn tiếp tục, và các endpoint mới được viết trong Nest | Phải chờ, hoặc viết hai lần, cho tới khi chuyển đổi |
| Quay lui thế nào? | Khôi phục một route | Deploy bản release Express cuối cùng |
| Phiên bản Express nào? | Express 5, nên hãy nâng cấp trước | Bất kỳ, vì ứng dụng Express không bị động tới |
| Các middleware hiện có thì sao? | Chúng vẫn chạy, cả cho route của Nest | Chúng được chuyển sang Nest cùng mọi thứ khác |
| Có hai phong cách trong code bao lâu? | Cho tới khi route cuối cùng được chuyển | Không bao giờ |

Hãy chuyển từng route một khi ứng dụng lớn, khi có nhiều người cùng làm, hoặc khi nó không thể chờ. Hãy chuyển tất cả cùng lúc khi nó đủ nhỏ để review như một thay đổi duy nhất và bạn có thể cố định những gì nó làm bằng test. Cách đó cũng phù hợp với một [coding agent](/recipes/express-migration#give-it-to-a-coding-agent), thứ có thể chuyển đổi cả một ứng dụng trong một lần, nhưng không tự biết được những gì phải giữ nguyên.

#### Từng route một <a id="one-route-at-a-time"></a>

Ứng dụng Express giữ các route, middleware và error handler của nó, các endpoint mới được viết trong Nest, và các endpoint hiện có được chuyển sang khi bạn sửa chúng lần tới. Cả hai trả lời trên cùng một port, phía sau cùng các middleware, nên client, session và phần xác thực không nhận ra, và mỗi bước đều có thể được deploy độc lập.

##### Yêu cầu <a id="requirements"></a>

- **Express 5.** Adapter Express của Nest điều khiển một ứng dụng Express 5, và một ứng dụng Express 4 sẽ thất bại ngay khi Nest khởi động. Hãy nâng cấp ứng dụng trước, với [hướng dẫn migration](https://expressjs.com/en/guide/migrating-5.html) của Express và codemod của nó, `npx @expressjs/codemod upgrade`.
- **TypeScript.** Code Nest trên trang này là TypeScript. Nếu ứng dụng Express được viết bằng JavaScript, các file của nó có thể giữ nguyên: tùy chọn `allowJs` của TypeScript biên dịch chúng cùng phần còn lại.

Một ứng dụng CommonJS có thể giữ nguyên CommonJS. Các package của Nest là ESM, thứ mà một ứng dụng CommonJS load được trên các phiên bản Node.js được liệt kê trong [hướng dẫn migration](/migration-guide#esm-packages).

Cài Nest cạnh Express:

```bash
$ npm i --save @nestjs/core @nestjs/common @nestjs/platform-express reflect-metadata rxjs
```

##### Chạy Nest trên ứng dụng Express <a id="run-nest-on-the-express-app"></a>

Nest thường tự tạo ứng dụng Express của riêng nó. Hãy đưa cho nó ứng dụng của bạn thay vào đó. Dừng việc ứng dụng Express tự lắng nghe, và export một hàm dựng nó, để các test có thể tự dựng ứng dụng của chúng:

```typescript
@@filename(legacy/app)
import express from 'express';
import { authenticate } from './auth.js';
import { errorHandler } from './errors.js';
import { ordersRouter } from './orders.router.js';

export function createLegacyApp() {
  const app = express();
  app.use(express.json());
  app.use(authenticate); // sets req.user
  app.use('/orders', ordersRouter);
  app.use(errorHandler);
  // app.listen(3000); <- Nest listens from now on
  return app;
}
```

Sau đó truyền nó cho `ExpressAdapter`, và để Nest lắng nghe:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { ExpressAdapter } from '@nestjs/platform-express';
import { AppModule } from './app.module.js';
import { createLegacyApp } from './legacy/app.js';

async function bootstrap() {
  const app = await NestFactory.create(
    AppModule,
    new ExpressAdapter(createLegacyApp()),
  );
  await app.listen(process.env.PORT ?? 3000);
}

await bootstrap();
```

Express chạy middleware và route theo thứ tự chúng được thêm vào. Mọi thứ mà ứng dụng Express thêm vào đều đứng trước. Nest thêm các route của nó khi ứng dụng khởi động, trong `listen()` hoặc `init()`, và sau đó là một handler trả lời `404` cho các request không khớp route nào. Vì vậy:

- Các route Express trả lời như trước đây.
- Các route của Nest trả lời những request mà route Express không trả lời.
- Các route của Nest thấy những gì middleware Express đặt lên request, như `req.user`, và body mà các parser của nó đã đọc.
- Một request tới route mà cả hai đều không có sẽ nhận response `404` của Nest.

> warning **Cảnh báo** Hãy gỡ bỏ một handler `404` bắt tất cả, như `app.use((req, res) => res.status(404).send())`, khỏi ứng dụng Express. Nó đứng trước các route của Nest, nên nó cũng trả lời request của chúng, và handler của Nest sẽ trả lời các route không tồn tại thay cho nó. Hãy giữ error handler: một error handler của Express chỉ nhận lỗi của các middleware và route được thêm vào trước nó, nên nó vẫn tiếp tục xử lý lỗi của các route Express, trong khi các [exception filter](/exception-filters) của Nest xử lý lỗi của các route Nest.

Phần nào của ứng dụng chạy cho route nào:

| Phần | Route Express | Route Nest |
| --- | --- | --- |
| Middleware được thêm vào ứng dụng Express (body parser, session, xác thực) | Có | Có |
| Error handler của ứng dụng Express | Có | Không |
| Middleware được thêm qua Nest: [`MiddlewareConsumer`](/middleware), `app.use()`, `app.enableCors()` | Không | Có |
| [Guard](/guards), [interceptor](/interceptors), [pipe](/pipes) và [exception filter](/exception-filters) | Không | Có |

Các middleware mà ứng dụng Express đang chạy cũng đứng trước các route của Nest, nên một [guard](/guards) có thể kiểm tra user mà middleware xác thực hiện có đã đặt lên request:

```typescript
@@filename(authenticated.guard)
import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';

@Injectable()
export class AuthenticatedGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    return Boolean(request.user);
  }
}
```

> info **Gợi ý** Với một [global prefix](/faq/global-prefix), handler `404` của Nest chỉ trả lời các path nằm dưới prefix. Một path nằm ngoài nó mà không route Express nào khớp sẽ nhận trang `404` mặc định của Express.

##### Chuyển một route <a id="move-a-route"></a>

Viết các endpoint mới trong Nest. Để chuyển một endpoint hiện có, hãy viết nó thành một route Nest và xóa nó khỏi router Express. Vì các route Express đứng trước, một route Nest có cùng method và path sẽ không trả lời cho tới khi route Express biến mất, nên cả hai có thể cùng có trong code cho tới khi bạn sẵn sàng chuyển:

```typescript
@@filename(orders/orders.controller)
import { Controller, Get, Param, UseGuards } from '@nestjs/common';
import { AuthenticatedGuard } from '../authenticated.guard.js';
import { OrdersService } from './orders.service.js';

@Controller('orders')
@UseGuards(AuthenticatedGuard)
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.ordersService.findOne(id);
  }
}
```

```typescript
@@filename(legacy/orders.router)
import express from 'express';
import { getOrder, listOrders } from './orders.handlers.js';

export const ordersRouter = express.Router();

ordersRouter.get('/', listOrders);
// ordersRouter.get('/:id', getOrder); <- deleted: Nest answers GET /orders/:id
```

`GET /orders` vẫn do Express trả lời, còn `GET /orders/:id` đi qua router Express và tới Nest.

[End-to-end test](/fundamentals/testing#end-to-end-testing) bao phủ cả hai loại route khi ứng dụng test cũng được dựng trên ứng dụng Express. Hãy truyền adapter cho `createNestApplication()`, và cùng một test sẽ kiểm tra một route trước và sau khi nó được chuyển:

```typescript
@@filename(test/orders.e2e-spec)
import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { ExpressAdapter } from '@nestjs/platform-express';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';
import { createLegacyApp } from '../src/legacy/app.js';

describe('Orders', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();
    app = moduleRef.createNestApplication(new ExpressAdapter(createLegacyApp()));
    await app.init();
  });

  it('lists orders (Express)', () => {
    return request(app.getHttpServer()).get('/orders').expect(200);
  });

  it('returns one order (Nest)', () => {
    return request(app.getHttpServer())
      .get('/orders/ord_1001')
      .set('Authorization', 'Bearer test-token')
      .expect(200);
  });

  afterAll(async () => {
    await app.close();
  });
});
```

##### Dùng chung code giữa hai bên <a id="share-code-between-the-two"></a>

Ứng dụng Express đã có những object mà code Nest cần, như một database pool, các repository, hoặc một mailer. Hãy đăng ký chúng làm [value provider](/fundamentals/custom-providers#value-providers-usevalue), để Nest inject cùng các instance mà code Express dùng:

```typescript
@@filename(legacy/legacy.module)
import { Global, Module } from '@nestjs/common';
import { OrdersRepository, ordersRepository } from './orders.repository.js';

@Global()
@Module({
  providers: [{ provide: OrdersRepository, useValue: ordersRepository }],
  exports: [OrdersRepository],
})
export class LegacyModule {}
```

Import `LegacyModule` một lần trong `AppModule`, và bất kỳ provider nào cũng có thể inject `OrdersRepository` theo class của nó.

Chiều ngược lại cũng được. Khi `NestFactory.create()` trả về, `app.get()` trả về bất kỳ provider nào, nên một route vẫn ở lại trong Express có thể gọi logic đã được chuyển vào một service của Nest. Hãy thêm route trước `listen()`, và nó sẽ đứng trước các route của Nest như phần còn lại của ứng dụng Express:

```typescript
@@filename(main)
const legacyApp = createLegacyApp();
const app = await NestFactory.create(AppModule, new ExpressAdapter(legacyApp));
legacyApp.use('/reports', reportsRouter(app.get(ReportsService)));
await app.listen(process.env.PORT ?? 3000);
```

##### Hoàn tất migration <a id="finish-the-migration"></a>

Khi các router Express đã trống, hãy chuyển phần còn lại của ứng dụng Express vào Nest: middleware vào [middleware của Nest](/middleware) hoặc `app.use()`, và error handler vào một [exception filter](/exception-filters). Sau đó xóa thư mục `legacy`, và tạo ứng dụng mà không có tham số adapter:

```typescript
const app = await NestFactory.create(AppModule);
```

#### Tất cả cùng lúc <a id="all-at-once"></a>

Một ứng dụng Nest mới thay thế ứng dụng Express trong một lần release. Cho tới lúc đó ứng dụng Express giữ nguyên, trên phiên bản Express mà nó đang chạy, và nó là tham chiếu cho những gì ứng dụng mới phải làm.

Phần lớn rủi ro không nằm ở việc chuyển đổi, vì một bản chuyển đổi sai thường thất bại rõ ràng. Nó nằm ở những gì thay đổi mà không báo lỗi: một status code, cấu trúc của một error response, cách một query string được parse. Vì vậy migration bắt đầu bằng những test nhận ra được các thay đổi đó.

##### Cố định API bằng test <a id="pin-the-api-with-tests"></a>

Viết các test chỉ biết URL, để cùng các test chạy được trên cả hai ứng dụng. Duyệt qua mọi router và lời gọi `app.use()`, và bao phủ status code, body và các header quan trọng của mỗi route, cho cả trường hợp thất bại lẫn thành công:

```typescript
import assert from 'node:assert/strict';
import { test } from 'node:test';

const BASE = process.env.BASE_URL ?? 'http://localhost:3000';

test('creating an order answers 200', async () => {
  const res = await fetch(`${BASE}/api/orders`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
    body: JSON.stringify({ total: 10 }),
  });
  assert.equal(res.status, 200);
  assert.equal((await res.json()).status, 'pending');
});

test('errors keep their shape', async () => {
  const res = await fetch(`${BASE}/api/orders/nope`, {
    headers: { authorization: `Bearer ${token}` },
  });
  assert.equal(res.status, 404);
  assert.deepEqual(await res.json(), {
    error: { code: 'ORDER_NOT_FOUND', message: 'Order nope not found' },
  });
});
```

Chạy chúng trên ứng dụng Express cho tới khi tất cả đều pass, trước khi viết bất kỳ dòng code Nest nào:

```bash
$ BASE_URL=http://localhost:3000 node --test test/contract.test.mjs
```

##### Chuyển đổi ứng dụng <a id="translate-the-application"></a>

Tạo ứng dụng Nest bằng `nest new` cạnh ứng dụng Express, và chuyển mỗi router thành một controller:

| Express | Nest |
| --- | --- |
| `express.Router()` cho một resource | Một [controller](/controllers) trong một [module](/modules) (`nest generate resource`) |
| `router.get('/:id', handler)` | `@Get(':id')` trên một method |
| `req.params`, `req.query`, `req.body` | `@Param()`, `@Query()`, `@Body()` |
| Tự validate `req.body` bằng tay | Một [schema hoặc một DTO](/application/validation), hoặc giữ nguyên bước kiểm tra nếu test cố định status và message của nó |
| Middleware xác thực đặt `req.user` | Một [guard](/guards) đặt nó, và một [custom decorator](/custom-decorators) đọc nó |
| `requireRole('admin')` | Metadata trên route, được một guard đọc |
| `router.param('id', load)` | Một [pipe](/pipes): `@Param('id', OrderByIdPipe)`. Guard chạy trước pipe, nên việc xác thực vẫn đi trước |
| `res.json(x)` | `return x`, kèm `@HttpCode()` khi status không phải mặc định |
| `res.status(204).end()` | `@HttpCode(204)`, và không trả về gì |
| `res.redirect(301, url)` | `@Redirect(url, 301)` |
| `res.cookie()` | `@Res({{ '{' }} passthrough: true {{ '}' }}) res`, sau đó `res.cookie()` và `return` như thường lệ |
| `res.type()`, `res.attachment()` | `@Header()` |
| `res.write()` | `@Res() res`, sau đó ghi vào nó như trong Express |
| `next(err)` | `throw err`, được một [exception filter](/exception-filters) xử lý |
| Error handler và `404` bắt tất cả | Một exception filter global |
| `app.use(helmet())` | `app.use(helmet())` |
| `app.use(cors(options))` | `app.enableCors(options)` |
| `express.static(dir)` | `app.useStaticAssets(dir, {{ '{' }} prefix {{ '}' }})` |
| `multer(options).single('file')` | `@UseInterceptors(FileInterceptor('file', options))` và `@UploadedFile()` |
| Các module giữ một database pool hoặc một mailer | Ban đầu là [value provider](/fundamentals/custom-providers#value-providers-usevalue), sau đó là service |

Một router có xác thực, kiểm tra role và một parameter handler trở thành:

```typescript
@@filename(orders/orders.controller)
@Controller('api/orders')
@UseGuards(AuthGuard, RoleGuard)
export class OrdersController {
  @Post()
  @HttpCode(200) // Express answered 200, and a client depends on it
  create(@CurrentUser() user: User, @Body() body?: CreateOrderBody) {
    const { total, tags } = body ?? {};
    if (typeof total !== 'number' || total <= 0) {
      throw new ApiError(422, 'INVALID_TOTAL', 'total must be a positive number');
    }
    return createOrder(user.id, total, tags);
  }

  @Get('summary') // Declared before ':orderId', which would match it too
  @Role('admin')
  summary() {
    return { total: orders.size };
  }

  @Get(':orderId')
  findOne(@CurrentUser() user: User, @Param('orderId', OrderByIdPipe) order: Order) {
    if (user.role !== 'admin' && order.userId !== user.id) {
      throw new ApiError(403, 'FORBIDDEN', 'Not your order');
    }
    return order;
  }
}
```

##### Giữ những gì sẽ thay đổi mà không báo lỗi <a id="keep-what-would-change-without-an-error"></a>

Đây là những khác biệt vẫn biên dịch được, khởi động được và trông có vẻ đúng, những thứ mà test của bạn phải bắt được:

| Trong Express | Trong một ứng dụng Nest | Để giữ hành vi cũ |
| --- | --- | --- |
| `res.json()` trả lời `200`, kể cả trên một `POST` | Một handler `POST` trả lời `201` | `@HttpCode(200)` |
| Lỗi có cấu trúc mà handler của bạn đặt cho chúng | `{{ '{' }} statusCode, message, error {{ '}' }}` | Một exception filter global |
| Một route không tồn tại nhận `404` của bạn | `NotFoundException`, với body của Nest | Cùng filter đó |
| JSON sai định dạng tới handler của bạn dưới dạng `entity.parse.failed` | `BadRequestException`, lỗi mà một URL sai định dạng như `/orders/%FF` cũng gây ra | Cùng filter đó |
| Một JSON body lớn hơn 100 kB tới handler của bạn dưới dạng `entity.too.large` | Một `HttpException` với status `413` | Cùng filter đó |
| Một lỗi multer tới handler của bạn dưới dạng `MulterError` | `FileInterceptor` gây ra `PayloadTooLargeException` cho lỗi kích thước, và `400` cho hầu hết các lỗi khác | Cùng filter đó, hoặc tự chạy multer |
| Chỉ các định dạng body mà bạn đã thêm parser mới được đọc | Cả body JSON lẫn URL-encoded đều được đọc | `bodyParser: false` trong `NestFactory.create()`, rồi `app.use(express.json())` |
| `router.use(authenticate)` cũng trả lời cho các path không có route nào bên dưới nó | Một guard chỉ chạy trên các route tồn tại, nên các path đó nhận `404` | Giữ nó dưới dạng middleware, với `consumer.apply(authenticate).forRoutes('api/orders/{{ '{' }}*path{{ '}' }}')`, nếu client có thể nhận ra khác biệt |
| `router.param()` chạy trước middleware riêng của route, nên một bản ghi không tồn tại là `404` với bất kỳ ai | Mọi guard chạy trước mọi pipe, nên `requireRole` trả lời trước, với `403` | Kiểm tra role trong handler, sau pipe, nếu client có thể nhận ra khác biệt |
| Trên Express 4, `?min[total]=10` là `{{ '{' }} min: {{ '{' }} total: '10' {{ '}' }} {{ '}' }}` | Parser của Express 5 cho ra `{{ '{' }} 'min[total]': '10' {{ '}' }}` | `app.set('query parser', 'extended')` |
| Trên Express 4, một request không có body có `req.body` là `{{ '{' }}{{ '}' }}` | `@Body()` là `undefined`, nên destructure nó sẽ throw | `body ?? {{ '{' }}{{ '}' }}` |
| `res.json('1.2.3')` gửi một chuỗi JSON | Trả về một chuỗi sẽ gửi `text/html` | `@Res() res`, rồi `res.json('1.2.3')` |

Đường dẫn route cũng phải thay đổi, nhưng những thay đổi đó thất bại rõ ràng: `/search/:term?` dừng ứng dụng lúc khởi động, và cần đổi thành `search{{ '{' }}/:term{{ '}' }}`. Một wildcard cần có tên, `assets/*path`, và `@Param('path')` trả về các đoạn của nó dưới dạng một mảng. `assets/*path` không khớp với `/assets/` khi không có gì phía sau, nên hãy dùng `assets/{{ '{' }}*path{{ '}' }}` nếu Express 4 đã trả lời path đó.

Đi từ Express 4 lên cũng mang theo những thay đổi nhỏ riêng của Express 5, mà các test so sánh chính xác từng byte sẽ phát hiện: `charset=utf-8` ở chỗ file tĩnh từng ghi `UTF-8`, và một body khác trên các redirect. Không client nào nên phụ thuộc vào những thứ đó, nên hãy chấp nhận chúng thay vì cố định các phiên bản cũ của library Express để tái tạo chúng.

Filter và `main.ts` giữ phần lớn những điều này. Chúng phải giữ cấu trúc lỗi của bạn cho mọi lỗi, kể cả những lỗi mà Nest tự phát sinh, nên hãy kiểm tra xem test của bạn kỳ vọng những lỗi nào. Ví dụ, filter này báo cáo mọi `BadRequestException` là JSON sai định dạng:

```typescript
@@filename(common/api-exception.filter)
@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const http = host.switchToHttp();
    const request = http.getRequest<Request>();
    const response = http.getResponse<Response>();
    const send = (status: number, code: string, message: string) =>
      response.status(status).json({ error: { code, message } });

    if (exception instanceof ApiError) {
      return send(exception.status, exception.code, exception.message);
    }
    if (exception instanceof NotFoundException) {
      return send(404, 'NOT_FOUND', `No route for ${request.method} ${request.path}`);
    }
    if (exception instanceof BadRequestException) {
      return send(400, 'BAD_JSON', 'Malformed JSON');
    }
    if (exception instanceof PayloadTooLargeException) {
      return send(413, 'FILE_TOO_LARGE', 'File too large');
    }
    if (exception instanceof HttpException) {
      return send(exception.getStatus(), 'ERROR', exception.message);
    }
    console.error(exception);
    return send(500, 'INTERNAL', 'Something went wrong');
  }
}
```

```typescript
@@filename(main)
async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  app.set('query parser', 'extended');
  app.use(helmet());
  app.enableCors({ origin: 'https://shop.example.com', credentials: true });
  app.useStaticAssets(join(import.meta.dirname, '..', 'public'), { prefix: '/static' });
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

Khi chúng pass, hãy deploy nó thay cho ứng dụng Express, và giữ bản release Express cuối cùng ở trạng thái có thể deploy cho tới khi bản mới đã phục vụ lưu lượng thật.

#### Giao cho một coding agent <a id="give-it-to-a-coding-agent"></a>

Cách tiếp cận nào cũng làm được với một coding agent, và tất cả cùng lúc là lựa chọn phù hợp hơn khi ứng dụng đủ nhỏ để review trong một thay đổi. Hãy chỉ cho agent trang này và buộc nó tuân theo các test, để nó không thể tuyên bố thành công với code chỉ đơn thuần biên dịch được:

```bash
Migrate this Express application to NestJS all at once, following
https://docs.nestjs.com/recipes/express-migration.md.

1. Before changing anything, write black-box HTTP tests that cover every
   route: status codes, bodies and important headers, failures included.
   Run them against the Express app until they all pass.
2. Build the Nest application next to it, using the page's translation table.
3. Check every row of "Keep what would change without an error".
4. Run the same tests against the Nest application. Don't edit a test to
   make it pass. If behavior has to change, stop and tell me.
```
