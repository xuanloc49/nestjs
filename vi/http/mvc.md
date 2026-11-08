### Model-View-Controller

Mặc định, bên dưới Nest dùng library [Express](https://github.com/expressjs/express). Vì vậy, mọi kỹ thuật áp dụng pattern MVC (Model-View-Controller) trong Express cũng áp dụng được cho Nest.

Đầu tiên, scaffold một ứng dụng Nest mới bằng công cụ [CLI](https://github.com/nestjs/nest-cli):

```bash
$ npm i -g @nestjs/cli
$ nest new project
```

Để tạo một app MVC, bạn còn cần một [template engine](https://expressjs.com/en/guide/using-template-engines.html) để render các view HTML:

```bash
$ npm install --save hbs
```

Ví dụ này dùng engine `hbs` ([Handlebars](https://github.com/pillarjs/hbs#readme)), nhưng bạn có thể dùng bất kỳ engine nào phù hợp với yêu cầu của mình. Sau khi cài xong, cấu hình Express instance bằng đoạn code sau:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import { join } from 'node:path';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(
    AppModule,
  );

  app.useStaticAssets(join(import.meta.dirname, '..', 'public'));
  app.setBaseViewsDir(join(import.meta.dirname, '..', 'views'));
  app.setViewEngine('hbs');

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
@@switch
import { NestFactory } from '@nestjs/core';
import { join } from 'node:path';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(
    AppModule,
  );

  app.useStaticAssets(join(import.meta.dirname, '..', 'public'));
  app.setBaseViewsDir(join(import.meta.dirname, '..', 'views'));
  app.setViewEngine('hbs');

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Đoạn code này báo cho Express biết thư mục `public` chứa các static asset, thư mục `views` chứa template, và template engine `hbs` sẽ render output HTML.

> info **Gợi ý** Cùng các lời gọi đó hoạt động với `NodeAdapter`: hãy tạo ứng dụng với `new NodeAdapter()` và type `NestNodeApplication` thay vào đó (xem [Node adapter](/http/performance#node-adapter)). Node adapter hỗ trợ decorator `@Render()`, nhưng không hỗ trợ method `res.render()` dùng trong phần [Render template động](/http/mvc#dynamic-template-rendering) bên dưới.

#### Render template <a id="template-rendering"></a>

Giờ hãy tạo thư mục `views` với một template `index.hbs` bên trong. Template này in ra một `message` được truyền từ controller:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>App</title>
  </head>
  <body>
    {{ "{{ message }\}" }}
  </body>
</html>
```

Tiếp theo, mở file `app.controller` và thay nội dung của nó bằng đoạn code sau:

```typescript
@@filename(app.controller)
import { Get, Controller, Render } from '@nestjs/common';

@Controller()
export class AppController {
  @Get()
  @Render('index')
  root() {
    return { message: 'Hello world!' };
  }
}
```

Đoạn code này chỉ định template cần dùng trong decorator `@Render()`, và giá trị trả về của method route handler được truyền vào template để render. Giá trị trả về là một object có thuộc tính `message`, khớp với placeholder `message` trong template.

Trong khi ứng dụng đang chạy, mở trình duyệt và truy cập `http://localhost:3000`. Bạn sẽ thấy dòng chữ `Hello world!`.

#### Thêm layout <a id="adding-a-layout"></a>

Engine `hbs` hỗ trợ layout: các template bao bọc dùng chung mà từng view được render vào bên trong. Để dùng layout, hãy đặt biến local `layout` bằng method `setLocal()` (wrapper của Nest bọc quanh [app.locals](https://expressjs.com/en/5x/api.html#app.locals) của Express). Sửa đoạn code trước như sau:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import { join } from 'node:path';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(
    AppModule,
  );

  app.setLocal('layout', 'layouts/app');
  app.useStaticAssets(join(import.meta.dirname, '..', 'public'));
  app.setBaseViewsDir(join(import.meta.dirname, '..', 'views'));
  app.setViewEngine('hbs');

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
@@switch
import { NestFactory } from '@nestjs/core';
import { join } from 'node:path';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(
    AppModule,
  );

  app.setLocal('layout', 'layouts/app');
  app.useStaticAssets(join(import.meta.dirname, '..', 'public'));
  app.setBaseViewsDir(join(import.meta.dirname, '..', 'views'));
  app.setViewEngine('hbs');

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Tiếp theo, tạo thư mục `layouts` bên trong `views` và thêm file `app.hbs` với nội dung sau:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>App</title>
  </head>
  <body>
    {{ '{' }}{{ '{' }}{{ '{' }}body{{ '}' }}{{ '}' }}{{ '}' }}
  </body>
</html>
```

Sau đó cập nhật file `index.hbs` thành:

```html
{{ "{{ message }\}" }}
```

Cấu trúc file kết quả trông như sau:

<div class="file-tree">
  <div class="item">views</div>
  <div class="children">
    <div class="item">layouts</div>
    <div class="children">
      <div class="item">app.hbs</div>
    </div>
    <div class="item">index.hbs</div>
  </div>
</div>

#### Render template động <a id="dynamic-template-rendering"></a>

Nếu logic của ứng dụng cần quyết định động template nào sẽ được render, hãy dùng decorator `@Res()` và cung cấp tên view trong route handler, thay vì trong decorator `@Render()`:

> info **Gợi ý** Khi Nest phát hiện decorator `@Res()`, nó inject object `response` riêng của library, bạn có thể dùng object này để render template một cách động. Xem [tài liệu API của Express](https://expressjs.com/en/api.html) để tìm hiểu thêm về object `response`.

```typescript
@@filename(app.controller)
import { Get, Controller, Res, Render } from '@nestjs/common';
import type { Response } from 'express';
import { AppService } from './app.service.js';

@Controller()
export class AppController {
  constructor(private appService: AppService) {}

  @Get()
  root(@Res() res: Response) {
    return res.render(
      this.appService.getViewName(),
      { message: 'Hello world!' },
    );
  }
}
```

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn trong [sample 15-mvc](https://github.com/nestjs/nest/tree/master/sample/15-mvc).

#### Fastify

Như đã nói trong chương [HTTP adapter](/http/performance), bạn có thể dùng bất kỳ HTTP provider tương thích nào với Nest. Một library như vậy là [Fastify](https://github.com/fastify/fastify). Để tạo một ứng dụng MVC với Fastify, hãy cài các package sau:

```bash
$ npm i --save @fastify/static @fastify/view handlebars
```

Các bước tiếp theo gần như giống với Express, chỉ có vài khác biệt nhỏ đặc thù của nền tảng. Sau khi cài xong, mở file `main.ts` và cập nhật nội dung của nó:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { NestFastifyApplication, FastifyAdapter } from '@nestjs/platform-fastify';
import { AppModule } from './app.module.js';
import { join } from 'node:path';
import Handlebars from 'handlebars';

async function bootstrap() {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter(),
  );
  app.useStaticAssets({
    root: join(import.meta.dirname, '..', 'public'),
    prefix: '/public/',
  });
  app.setViewEngine({
    engine: {
      handlebars: Handlebars,
    },
    templates: join(import.meta.dirname, '..', 'views'),
  });
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
@@switch
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { AppModule } from './app.module.js';
import { join } from 'node:path';
import Handlebars from 'handlebars';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, new FastifyAdapter());
  app.useStaticAssets({
    root: join(import.meta.dirname, '..', 'public'),
    prefix: '/public/',
  });
  app.setViewEngine({
    engine: {
      handlebars: Handlebars,
    },
    templates: join(import.meta.dirname, '..', 'views'),
  });
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

API của Fastify có vài điểm khác, nhưng kết quả cuối cùng của các lời gọi method này là như nhau. Một khác biệt đáng chú ý là với Fastify, tên template bạn truyền vào decorator `@Render()` phải bao gồm cả phần mở rộng của file:

```typescript
@@filename(app.controller)
import { Get, Controller, Render } from '@nestjs/common';

@Controller()
export class AppController {
  @Get()
  @Render('index.hbs')
  root() {
    return { message: 'Hello world!' };
  }
}
```

Cách khác là dùng decorator `@Res()` để inject trực tiếp response và chỉ định view bạn muốn render, như bên dưới:

```typescript
import { Get, Res } from '@nestjs/common';
import type { FastifyReply } from 'fastify';

@Get()
root(@Res() res: FastifyReply) {
  return res.view('index.hbs', { message: 'Hello world!' });
}
```

Trong khi ứng dụng đang chạy, mở trình duyệt và truy cập `http://localhost:3000`. Bạn sẽ thấy dòng chữ `Hello world!`.

#### Ví dụ <a id="example-1"></a>

Một ví dụ chạy được có sẵn trong [sample 17-mvc-fastify](https://github.com/nestjs/nest/tree/master/sample/17-mvc-fastify).
