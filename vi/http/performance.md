### HTTP adapter

Nest không nói chuyện trực tiếp với HTTP server. Nó đi qua một **HTTP adapter**, với nhiệm vụ chính là chuyển middleware và handler tới các bản implement tương ứng của từng library. Điều này giúp Nest độc lập với framework: controller, provider, guard, pipe và filter của bạn chạy y như cũ trên mỗi adapter dưới đây, và bạn có thể chuyển từ adapter này sang adapter khác.

| Adapter          | Package                    | Xây dựng trên                                                            |
| ---------------- | -------------------------- | ------------------------------------------------------------------------ |
| `ExpressAdapter` | `@nestjs/platform-express` | [Express](https://expressjs.com/) (mặc định)                             |
| `FastifyAdapter` | `@nestjs/platform-fastify` | [Fastify](https://fastify.dev/)                                          |
| `NodeAdapter`    | `@nestjs/platform-node`    | Module [`node:http`](https://nodejs.org/api/http.html) của Node.js       |

> info **Gợi ý** Chỉ có thể implement framework adapter cho một library có cơ chế xử lý pipeline request/response tương tự Express.

#### Chọn adapter <a id="choosing-an-adapter"></a>

Kể từ NestJS v12.3, chúng tôi khuyên dùng `NodeAdapter`. Đây là adapter nhanh nhất trong ba cái (xem [Hiệu năng](/http/performance#performance)), và request cùng response object của nó có sẵn các helper kiểu Express, nên phần lớn middleware Express, và phần lớn code viết cho Express adapter, chạy được với nó mà không cần thay đổi. Nest vẫn dùng Express khi bạn không truyền adapter, nên bạn cần tự chọn dùng nó, như trong phần [Node adapter](/http/performance#node-adapter). Trong NestJS v13, `NodeAdapter` sẽ trở thành mặc định.

Hãy chọn `FastifyAdapter` để dùng plugin của Fastify và các tính năng như [route constraint](/http/performance#route-constraints). Hãy ở lại với `ExpressAdapter` nếu ứng dụng của bạn dựa vào các API của Express mà Node adapter không implement (xem [Tương thích với Express](/http/performance#express-compatibility)), hoặc dựa vào một package chỉ hỗ trợ Express.

#### Hiệu năng <a id="performance"></a>

Trong các benchmark của chúng tôi (`wrk` với 100 kết nối trên Node.js 24, với một route `GET` đơn giản, một route `GET` có tham số, và một route `POST` có body JSON), Nest xử lý được nhiều hơn khoảng 50% request mỗi giây trên `NodeAdapter` so với `ExpressAdapter`, và nhiều hơn khoảng 5% so với `FastifyAdapter`. Để chạy cùng benchmark trên máy của bạn, hãy làm theo các bước trong [nestjs/nest#18063](https://github.com/nestjs/nest/pull/18063#reproducing-the-benchmark).

Hãy nhớ rằng adapter chỉ xử lý một phần nhỏ của mỗi request. Một route query database hoặc gọi tới service khác dành phần lớn thời gian để chờ chúng, nên việc chọn adapter quan trọng nhất với các route nhẹ ở tốc độ request cao.

#### Node adapter

`NodeAdapter` chạy Nest trực tiếp trên module `node:http`, không có framework nào khác ở giữa. Đầu tiên, cài package cần thiết:

```bash
$ npm i --save @nestjs/platform-node
```

Sau đó truyền một instance `NodeAdapter` vào `NestFactory.create()`:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { NestNodeApplication, NodeAdapter } from '@nestjs/platform-node';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create<NestNodeApplication>(
    AppModule,
    new NodeAdapter(),
  );
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Type `NestNodeApplication` cho bạn các method đặc thù nền tảng của object ứng dụng: `useBodyParser()`, `useStaticAssets()`, `setViewEngine()`, `setBaseViewsDir()` và `setLocal()`.

Hãy truyền thêm một instance `NodeAdapter` vào `createNestApplication()` trong các end-to-end test. Không có nó, testing module sẽ tạo một ứng dụng Express, nên test không chạy trên adapter mà ứng dụng của bạn dùng, và sẽ lỗi nếu package `@nestjs/platform-express` chưa được cài:

```typescript
app = moduleRef.createNestApplication<NestNodeApplication>(new NodeAdapter());
```

##### Tương thích với Express <a id="express-compatibility"></a>

Request và response là instance của `NodeRequest` và `NodeResponse` (export từ `@nestjs/platform-node`). Chúng kế thừa `IncomingMessage` và `ServerResponse` của Node, bổ sung các thuộc tính và method kiểu Express mà middleware, exception filter và các handler `@Res()` thường dựa vào, như `req.get()`, `req.is()`, `req.ip`, `req.ips`, `req.hostname`, `res.status()`, `res.send()`, `res.json()`, `res.set()`, `res.type()`, `res.cookie()`, `res.redirect()`, `res.sendFile()` và `res.locals`. Middleware chạy trong một stack kiểu Express và dùng cùng signature `(req, res, next)`.

Các package middleware Express phổ biến, như `helmet`, `compression`, `cookie-parser`, `express-session`, `express-rate-limit`, `csrf-csrf`, `morgan` và `passport` (cùng các guard của `@nestjs/passport`), hoạt động giống như với Express adapter. Khi một chương trong tài liệu này đưa ra hướng dẫn riêng cho Express và Fastify (ví dụ [Nén response](/http/compression) hoặc [Session](/http/session)), hãy làm theo hướng dẫn cho Express.

Node adapter cố ý khác Express ở vài điểm:

- Route được so khớp theo độ cụ thể, giống Fastify, thay vì theo thứ tự đăng ký.
- Path được so khớp có phân biệt hoa thường, cho cả route, middleware lẫn `exclude()`, giống Fastify.
- Một chuỗi trả về từ route handler được gửi dưới dạng `text/plain`, không phải `text/html`.
- `req.path` là path đã decode mà router đã so khớp, nên một middleware kiểm tra nó sẽ thấy cùng path như các route.
- `res.set()` và `res.type()` không thêm `; charset=utf-8` vào header `Content-Type`.
- Adapter không thêm header `ETag`, và một request có điều kiện (`If-None-Match`, `If-Modified-Since`) nhận toàn bộ response thay vì `304 Not Modified`, giống Fastify, kể cả khi handler tự đặt `ETag` hoặc `Last-Modified`. `res.sendFile()` và `useStaticAssets()` vẫn gửi `ETag` và trả lời bằng `304`.
- Một route parameter dài hơn 100 ký tự sẽ không khớp (xem [Tùy chọn của Node adapter](/http/performance#node-adapter-options)).
- Một body JSON có key `__proto__` hoặc `constructor.prototype` sẽ bị từ chối (xem [Body parser](/http/performance#body-parsers)).

Một số API của Express không có sẵn: `res.render()` (hãy dùng decorator [`@Render()`](/http/mvc) thay vào đó), `res.download()`, `res.format()`, `res.attachment()`, `res.contentType()` (hãy dùng `res.type()` thay vào đó), `res.jsonp()`, `res.links()`, `res.location()` (hãy dùng `res.set('Location', url)` thay vào đó), `res.vary()`, `req.accepts()` và các biến thể của nó, `req.fresh` và `req.stale`, `req.host`, `req.range()`, `req.route`, `req.subdomains`, `req.xhr`, việc mount một ứng dụng Express bằng `app.use()`, và các thiết lập của Express, mà thay vào đó adapter nhận [tùy chọn](/http/performance#node-adapter-options) (ví dụ `trustProxy` cho thiết lập `trust proxy`).

##### Tùy chọn của Node adapter <a id="node-adapter-options"></a>

Giống như Fastify, route parameter bị giới hạn ở 100 ký tự. Một request có tham số dài hơn sẽ rơi xuống một route khớp khác, nếu có (ví dụ một route wildcard), và nếu không sẽ nhận response `414 URI Too Long`. Để thay đổi giới hạn, hãy truyền tùy chọn `maxParamLength` vào constructor của `NodeAdapter`:

```typescript
new NodeAdapter({ maxParamLength: 500 });
```

Đằng sau một reverse proxy hoặc load balancer, kết nối đến từ proxy, nên `req.ip` là địa chỉ của proxy, và `req.protocol` là `'http'` khi proxy kết thúc TLS. Để đọc địa chỉ, protocol và host của client từ các header `X-Forwarded-For`, `X-Forwarded-Proto` và `X-Forwarded-Host` mà một proxy tin cậy đặt vào, hãy truyền tùy chọn `trustProxy`. Giống như Fastify, nó nhận `true` để tin mọi proxy, các địa chỉ hoặc subnet của proxy (như `'loopback'` hoặc `'10.0.0.0/8'`, phân cách bằng dấu phẩy hoặc trong một mảng), hoặc một hàm nhận địa chỉ cùng số hop của nó và trả về việc có tin nó hay không:

```typescript
new NodeAdapter({ trustProxy: 'loopback' });
```

Khi đó `req.ip`, `req.ips`, `req.protocol`, `req.secure` và `req.hostname` hoạt động giống như với Express, và [routing theo sub-domain](/controllers#sub-domain-routing) cũng vậy. Khác với thiết lập của Express, tùy chọn này không nhận số hop: giống như Fastify, một số sẽ không tin proxy nào cả, vì nó không thể phân biệt một proxy với một client tự gửi header `X-Forwarded-For` của riêng nó.

> warning **Cảnh báo** Chỉ tin các proxy đứng trước ứng dụng của bạn. Một client có thể truy cập trực tiếp ứng dụng có thể gửi bất kỳ header `X-Forwarded-*` nào.

Mặc định, query string được parse thành các key phẳng, giống như Express và Fastify: `?filter[where][name]=John` cho ra một key `filter[where][name]`. Để parse thành object và mảng lồng nhau, hãy truyền tùy chọn `querystringParser`, giống như với Fastify. Nó được gọi với query string, không kèm dấu `?` ở đầu (và với chuỗi rỗng khi URL không có query string):

```typescript
import qs from 'qs';

new NodeAdapter({ querystringParser: (str) => qs.parse(str) });
```

##### Body parser <a id="body-parsers"></a>

Node adapter có sẵn các body parser `json`, `urlencoded`, `text` và `raw` của riêng nó, nên nó không phụ thuộc vào package `body-parser`. Chúng nhận cùng tùy chọn như các parser tương ứng của `body-parser`, như `limit`, `inflate`, `strict` và `type`. Giống như với Express, Nest mặc định đăng ký parser `json` và `urlencoded`, còn tùy chọn `rawBody` và method `useBodyParser()` hoạt động như mô tả trong [Raw body](/faq/raw-body).

Giống như Fastify, parser `json` từ chối một body cố chèn thuộc tính prototype: một body có key `__proto__` hoặc `constructor.prototype` sẽ nhận response `400 Bad Request`. Để bỏ các key này đi, hoặc giữ lại chúng (hành vi của `body-parser`), hãy đặt các tùy chọn `onProtoPoisoning` và `onConstructorPoisoning` thành `'remove'` hoặc `'ignore'`. Parser `urlencoded` nhận cùng các tùy chọn đó.

```typescript
app.useBodyParser('json', { onProtoPoisoning: 'remove' });
```

##### Static asset và view <a id="static-assets-and-views"></a>

`useStaticAssets()` phục vụ một thư mục bằng package [serve-static](https://www.npmjs.com/package/serve-static). Nó nhận các tùy chọn của package đó, cộng thêm một `prefix`, giống như với Express. `setViewEngine()` nhận tên của một engine, giống như với Express (xem [Model-View-Controller](/http/mvc)), hoặc options object của `@fastify/view`, gồm engine và thư mục `templates`.

##### Các package khác <a id="other-packages"></a>

- **Upload file:** import `FileInterceptor()`, các upload interceptor khác, và `MulterModule` từ `@nestjs/platform-node` thay vì `@nestjs/platform-express`. Chúng chính là các interceptor dựa trên Multer, nên phần còn lại của chương [Upload file](/http/file-upload) áp dụng y như cũ.
- **Phục vụ single-page application:** package `@nestjs/serve-static` (v12.1.1 trở lên) phục vụ file thông qua adapter, nên nó không cần package `express`. Route dự phòng cho các path phía client của nó yêu cầu `@nestjs/platform-node` v12.3.1 trở lên.
- **GraphQL:** dùng driver `@nestjs/apollo` (v14.1.1 trở lên), giống như với Express. Driver `@nestjs/mercurius` yêu cầu Fastify adapter.

#### Fastify adapter

[Fastify](https://github.com/fastify/fastify) là một framework thay thế tốt cho Nest vì nó giải quyết các vấn đề thiết kế theo cách tương tự Express. Nó có hệ sinh thái plugin riêng. Để dùng Fastify, hãy chọn `FastifyAdapter` có sẵn, như bên dưới.

##### Cài đặt <a id="installation"></a>

Đầu tiên, cài package cần thiết:

```bash
$ npm i --save @nestjs/platform-fastify
```

##### Adapter

Khi đã cài nền tảng Fastify, bạn có thể dùng `FastifyAdapter`.

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import {
  FastifyAdapter,
  NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter()
  );
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Mặc định, Fastify chỉ lắng nghe trên interface `localhost` (xem [hướng dẫn bắt đầu của Fastify](https://fastify.dev/docs/latest/Guides/Getting-Started/#your-first-server)). Để chấp nhận kết nối trên các host khác, hãy chỉ định `'0.0.0.0'` trong lời gọi `listen()`:

```typescript
async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter(),
  );
  await app.listen(3000, '0.0.0.0');
}
```

##### Package đặc thù nền tảng <a id="platform-specific-packages"></a>

Khi bạn dùng `FastifyAdapter`, Nest dùng Fastify làm **HTTP provider**. Điều này có nghĩa là các recipe dựa vào Express có thể không hoạt động. Hãy dùng các package tương đương cho Fastify thay vào đó.

##### Redirect response

Fastify xử lý redirect response hơi khác Express. Để redirect với Fastify, hãy đặt status code bằng `status()`, rồi gọi `redirect()` với URL:

```typescript
@Get()
index(@Res() res) {
  res.status(302).redirect('/login');
}
```

##### Tùy chọn của Fastify <a id="fastify-options"></a>

Bạn có thể truyền tùy chọn cho Fastify instance thông qua constructor của `FastifyAdapter`. Ví dụ:

```typescript
new FastifyAdapter({ logger: true });
```

##### Middleware

Các hàm middleware nhận object `req` và `res` thô thay vì các wrapper của Fastify. Đây là cách package `@fastify/middie`, thứ mà Nest dùng bên dưới, hoạt động. Xem [tài liệu middleware của Fastify](https://fastify.dev/docs/latest/Reference/Middleware/) để biết thêm thông tin.

```typescript
@@filename(logger.middleware)
import { Injectable, NestMiddleware } from '@nestjs/common';
import type { FastifyRequest, FastifyReply } from 'fastify';

@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: FastifyRequest['raw'], res: FastifyReply['raw'], next: () => void) {
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

##### Route config

Dùng decorator `@RouteConfig()` để áp dụng tính năng [route config](https://fastify.dev/docs/latest/Reference/Routes/#config) của Fastify.

```typescript
@RouteConfig({ output: 'hello world' })
@Get()
index(@Req() req) {
  return req.routeConfig.output;
}
```

##### Route constraint <a id="route-constraints"></a>

Dùng decorator `@RouteConstraints()` để áp dụng tính năng [route constraint](https://fastify.dev/docs/latest/Reference/Routes/#constraints) của Fastify.

```typescript
@RouteConstraints({ version: '1.2.x' })
newFeature() {
  return 'This works only for version >= 1.2.x';
}
```

> info **Gợi ý** `@RouteConfig()` và `@RouteConstraints()` được import từ `@nestjs/platform-fastify`.

##### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn trong [repository nestjs/nest](https://github.com/nestjs/nest/tree/master/sample/10-fastify).

#### Express adapter

[Express](https://expressjs.com/) được dùng rộng rãi, nổi tiếng, và có một kho middleware tương thích khổng lồ. Nest dùng `ExpressAdapter` từ package `@nestjs/platform-express` khi bạn không truyền adapter nào vào `NestFactory.create()`, nên không cần thiết lập gì. Để truy cập các method đặc thù Express của object ứng dụng, hãy truyền type `NestExpressApplication`:

```typescript
const app = await NestFactory.create<NestExpressApplication>(AppModule);
```

Để giữ ứng dụng của bạn trên Express khi `NodeAdapter` trở thành mặc định, hãy truyền tường minh một instance `ExpressAdapter`:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import {
  ExpressAdapter,
  NestExpressApplication,
} from '@nestjs/platform-express';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(
    AppModule,
    new ExpressAdapter(),
  );
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```
