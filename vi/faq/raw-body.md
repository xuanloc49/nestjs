### Raw body

Một trong những lý do phổ biến nhất để truy cập raw body của request là xác minh chữ ký webhook. Việc xác minh chữ ký webhook thường cần request body chưa được parse để tính một HMAC hash.

> warning **Cảnh báo** Tính năng này chỉ hoạt động nếu middleware body parser global có sẵn được bật, tức là bạn không được truyền `bodyParser: false` khi tạo ứng dụng.

#### Dùng với Express <a id="use-with-express"></a>

Trước tiên, hãy bật tùy chọn khi tạo ứng dụng Nest Express:

```typescript
import { NestFactory } from '@nestjs/core';
import type { NestExpressApplication } from '@nestjs/platform-express';
import { AppModule } from './app.module.js';

// in the "bootstrap" function
const app = await NestFactory.create<NestExpressApplication>(AppModule, {
  rawBody: true,
});
await app.listen(process.env.PORT ?? 3000);
```

Để truy cập raw body của request trong một controller, hãy gán type cho request bằng interface tiện ích `RawBodyRequest`, interface này cung cấp field `rawBody`:

```typescript
import { Controller, Post, type RawBodyRequest, Req } from '@nestjs/common';
import type { Request } from 'express';

@Controller('cats')
class CatsController {
  @Post()
  create(@Req() req: RawBodyRequest<Request>) {
    const raw = req.rawBody; // returns a `Buffer`.
  }
}
```

#### Đăng ký một parser khác <a id="registering-a-different-parser"></a>

Mặc định, chỉ các parser `json` và `urlencoded` được đăng ký. Để dùng một parser khác, hãy đăng ký nó một cách tường minh.

Ví dụ, để đăng ký một parser `text`:

```typescript
app.useBodyParser('text');
```

> warning **Cảnh báo** Hãy đảm bảo bạn truyền đúng type ứng dụng cho lời gọi `NestFactory.create()`. Với ứng dụng Express, type đúng là `NestExpressApplication`; nếu không, method `useBodyParser()` sẽ không được tìm thấy.

#### Giới hạn kích thước của body parser <a id="body-parser-size-limit"></a>

Nếu ứng dụng của bạn cần parse các body lớn hơn mặc định `100kb` của Express, hãy tăng giới hạn:

```typescript
app.useBodyParser('json', { limit: '10mb' });
```

Method `useBodyParser()` tôn trọng tùy chọn `rawBody` được truyền trong các tùy chọn của ứng dụng.

#### Dùng với Fastify <a id="use-with-fastify"></a>

Trước tiên, hãy bật tùy chọn khi tạo ứng dụng Nest Fastify:

```typescript
import { NestFactory } from '@nestjs/core';
import {
  FastifyAdapter,
  NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { AppModule } from './app.module.js';

// in the "bootstrap" function
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter(),
  {
    rawBody: true,
  },
);
await app.listen(process.env.PORT ?? 3000);
```

Để truy cập raw body của request trong một controller, hãy gán type cho request bằng interface tiện ích `RawBodyRequest`, interface này cung cấp field `rawBody`:

```typescript
import { Controller, Post, type RawBodyRequest, Req } from '@nestjs/common';
import type { FastifyRequest } from 'fastify';

@Controller('cats')
class CatsController {
  @Post()
  create(@Req() req: RawBodyRequest<FastifyRequest>) {
    const raw = req.rawBody; // returns a `Buffer`.
  }
}
```

#### Đăng ký một parser khác <a id="registering-a-different-parser-1"></a>

Mặc định, chỉ các parser `application/json` và `application/x-www-form-urlencoded` được đăng ký. Để dùng một parser khác, hãy đăng ký nó một cách tường minh.

Ví dụ, để đăng ký một parser `text/plain`:

```typescript
app.useBodyParser('text/plain');
```

> warning **Cảnh báo** Hãy đảm bảo bạn truyền đúng type ứng dụng cho lời gọi `NestFactory.create()`. Với ứng dụng Fastify, type đúng là `NestFastifyApplication`; nếu không, method `useBodyParser()` sẽ không được tìm thấy.

#### Giới hạn kích thước của body parser <a id="body-parser-size-limit-1"></a>

Nếu ứng dụng của bạn cần parse các body lớn hơn mặc định 1 MiB của Fastify, hãy tăng giới hạn:

```typescript
const bodyLimit = 10_485_760; // 10MiB
app.useBodyParser('application/json', { bodyLimit });
```

Method `useBodyParser()` tôn trọng tùy chọn `rawBody` được truyền trong các tùy chọn của ứng dụng.
