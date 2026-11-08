### Serverless

Serverless computing là một mô hình thực thi điện toán đám mây, trong đó nhà cung cấp cloud cấp phát tài nguyên máy theo nhu cầu, quản lý server thay cho khách hàng. Khi một ứng dụng không được dùng, không có tài nguyên tính toán nào được cấp cho nó. Giá được tính dựa trên lượng tài nguyên thực tế mà ứng dụng tiêu thụ ([nguồn](https://en.wikipedia.org/wiki/Serverless_computing)).

Với một **kiến trúc serverless**, bạn tập trung vào từng hàm riêng lẻ trong code ứng dụng. Các dịch vụ như AWS Lambda, Google Cloud Functions và Microsoft Azure Functions quản lý phần cứng vật lý, hệ điều hành máy ảo và phần mềm web server.

> info **Gợi ý** Chương này không bàn về ưu nhược điểm của serverless function, cũng không đi sâu vào chi tiết của bất kỳ nhà cung cấp cloud nào.

#### Cold start

Cold start là lần đầu tiên code của bạn chạy sau một khoảng thời gian. Tùy nhà cung cấp cloud, nó có thể gồm nhiều thao tác, từ tải code và bootstrap runtime tới chạy code của bạn.
Quá trình này thêm **độ trễ đáng kể**, tùy thuộc vào nhiều yếu tố như ngôn ngữ và số lượng package mà ứng dụng cần.

Một số yếu tố nằm ngoài tầm kiểm soát của bạn, nhưng vẫn còn nhiều điều bạn có thể làm ở phía mình để giữ cold start ngắn nhất có thể.

Dù Nest là một framework đầy đủ được thiết kế cho các ứng dụng doanh nghiệp phức tạp, nó cũng **phù hợp với các ứng dụng "đơn giản" hơn nhiều** (hoặc script). Ví dụ, với tính năng [ứng dụng standalone](/standalone-applications), bạn có thể dùng hệ thống DI của Nest trong các worker đơn giản, CRON job, CLI hoặc serverless function.

#### Benchmark <a id="benchmarks"></a>

Để hiểu rõ hơn chi phí của việc dùng Nest hoặc các library phổ biến khác (như `express`) trong serverless function, hãy so sánh lượng thời gian mà runtime Node.js cần để chạy các script sau:

```typescript
// #1 Express
import express from 'express';

async function bootstrap() {
  const app = express();
  app.get('/', (req, res) => res.send('Hello world!'));
  await new Promise<void>((resolve) => app.listen(3000, resolve));
}
await bootstrap();

// #2 Nest (with @nestjs/platform-express)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, { logger: ['error'] });
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();

// #3 Nest as a Standalone application (no HTTP server)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';
import { AppService } from './app.service.js';

async function bootstrap() {
  const app = await NestFactory.createApplicationContext(AppModule, {
    logger: ['error'],
  });
  console.log(app.get(AppService).getHello());
}
await bootstrap();

// #4 Raw Node.js script
async function bootstrap() {
  console.log('Hello world!');
}
await bootstrap();
```

Với tất cả các script này, chúng tôi dùng trình biên dịch `tsc` (TypeScript), nên code không được bundle (không dùng `webpack`).

|                                      |                   |
| ------------------------------------ | ----------------- |
| Express                              | 0.0079s (7.9ms)   |
| Nest với `@nestjs/platform-express`  | 0.1974s (197.4ms) |
| Nest (ứng dụng standalone)           | 0.1117s (111.7ms) |
| Script Node.js thuần                 | 0.0071s (7.1ms)   |

> info **Lưu ý** Máy: MacBook Pro Mid 2014, 2.5 GHz Quad-Core Intel Core i7, 16 GB 1600 MHz DDR3, SSD.

Giờ hãy lặp lại mọi benchmark, lần này dùng `webpack` để bundle ứng dụng thành một file JavaScript thực thi duy nhất (nếu bạn đã cài [Nest CLI](/cli/overview), hãy chạy `nest build --webpack`).
Thay vì cấu hình `webpack` mặc định đi kèm Nest CLI, chúng ta sẽ bundle mọi dependency (`node_modules`) lại với nhau, như sau:

```javascript
module.exports = (options, webpack) => {
  const lazyImports = [
    '@nestjs/microservices/microservices-module',
    '@nestjs/websockets/socket-module',
  ];

  return {
    ...options,
    externals: [],
    plugins: [
      ...options.plugins,
      new webpack.IgnorePlugin({
        checkResource(resource) {
          if (lazyImports.includes(resource)) {
            try {
              require.resolve(resource);
            } catch (err) {
              return true;
            }
          }
          return false;
        },
      }),
    ],
  };
};
```

> info **Gợi ý** Để Nest CLI dùng cấu hình này, hãy tạo một file `webpack.config.js` ở thư mục gốc của project.

Với cấu hình này, chúng tôi có được kết quả sau:

|                                      |                  |
| ------------------------------------ | ---------------- |
| Express                              | 0.0068s (6.8ms)  |
| Nest với `@nestjs/platform-express`  | 0.0815s (81.5ms) |
| Nest (ứng dụng standalone)           | 0.0319s (31.9ms) |
| Script Node.js thuần                 | 0.0066s (6.6ms)  |

> info **Lưu ý** Máy: MacBook Pro Mid 2014, 2.5 GHz Quad-Core Intel Core i7, 16 GB 1600 MHz DDR3, SSD.

> info **Gợi ý** Bạn có thể tối ưu thêm nữa bằng các kỹ thuật minify và tối ưu code bổ sung (ví dụ dùng các plugin của `webpack`).

Cách bạn biên dịch code (và có bundle nó hay không) ảnh hưởng đáng kể tới tổng thời gian khởi động. Với `webpack`, bạn có thể giảm thời gian bootstrap của một ứng dụng Nest standalone (một project starter có một module, controller và service) xuống trung bình ~32ms, và xuống ~81.5ms với một ứng dụng NestJS HTTP thông thường dựa trên Express.

Với một ứng dụng Nest phức tạp hơn, ví dụ một ứng dụng có 10 resource được sinh bằng schematic `$ nest g resource` (10 module, 10 controller, 10 service, 20 class DTO, và 50 HTTP endpoint, cộng `AppModule`), tổng thời gian khởi động trên cùng máy mất khoảng 0.1298s (129.8ms). Dù sao thì chạy một ứng dụng nguyên khối như một serverless function cũng hiếm khi hợp lý, nên hãy coi benchmark này là ví dụ cho thấy thời gian bootstrap có thể tăng thế nào khi ứng dụng lớn lên.

#### Tối ưu lúc runtime <a id="runtime-optimizations"></a>

Cho tới giờ, chúng ta đã bàn về tối ưu lúc biên dịch. Những tối ưu này không liên quan tới cách bạn định nghĩa provider và load các Nest module trong ứng dụng, thứ đóng vai trò thiết yếu khi ứng dụng lớn lên.

Ví dụ, hãy tưởng tượng một kết nối database được định nghĩa là một [async provider](/fundamentals/async-providers). Async provider được thiết kế để trì hoãn việc khởi động ứng dụng cho tới khi một hoặc nhiều tác vụ bất đồng bộ hoàn tất.
Nếu serverless function của bạn trung bình cần 2 giây để kết nối tới database lúc bootstrap, endpoint của bạn cần thêm ít nhất hai giây để gửi response khi cold start, vì nó phải chờ tới khi kết nối được thiết lập.

Trong một **môi trường serverless**, nơi thời gian bootstrap là quan trọng, bạn cấu trúc các provider hơi khác một chút.
Ví dụ, nếu bạn dùng Redis để cache chỉ trong một số tình huống, có lẽ bạn không nên định nghĩa kết nối Redis là một async provider: nó sẽ làm chậm quá trình bootstrap kể cả với những lần gọi function không cần đến nó.

Bạn cũng có thể lazy load toàn bộ module bằng class `LazyModuleLoader`, như mô tả trong chương [lazy-loading module](/fundamentals/lazy-loading-modules). Caching cũng là một ví dụ tốt ở đây.
Hãy tưởng tượng ứng dụng của bạn có một `CacheModule` kết nối tới Redis và export một `CacheService` để tương tác với Redis. Nếu không phải lần gọi function nào cũng cần nó,
bạn có thể load nó một cách lazy, khi cần. Bằng cách này, mọi lần gọi không cần cache sẽ có thời gian khởi động nhanh hơn khi cold start.

```typescript
if (request.method === RequestMethod[RequestMethod.GET]) {
  const { CacheModule } = await import('./cache.module.js');
  const moduleRef = await this.lazyModuleLoader.load(() => CacheModule);

  const { CacheService } = await import('./cache.service.js');
  const cacheService = moduleRef.get(CacheService);

  return cacheService.get(ENDPOINT_KEY);
}
```

Một ví dụ khác là một webhook hoặc worker thực hiện các thao tác khác nhau tùy vào các điều kiện cụ thể (ví dụ argument đầu vào).
Trong trường hợp này, bạn có thể thêm một điều kiện bên trong route handler để lazy load module phù hợp cho lần gọi function cụ thể, và cũng lazy load mọi module khác.

```typescript
if (workerType === WorkerType.A) {
  const { WorkerAModule } = await import('./worker-a.module.js');
  const moduleRef = await this.lazyModuleLoader.load(() => WorkerAModule);
  // ...
} else if (workerType === WorkerType.B) {
  const { WorkerBModule } = await import('./worker-b.module.js');
  const moduleRef = await this.lazyModuleLoader.load(() => WorkerBModule);
  // ...
}
```

#### Ví dụ tích hợp <a id="example-integration"></a>

File entry của ứng dụng (thường là `main.ts`) nên trông thế nào **phụ thuộc vào nhiều yếu tố**, nên **không có một template duy nhất** dùng được cho mọi tình huống.
Ví dụ, file khởi tạo cần thiết để chạy serverless function thay đổi theo nhà cung cấp cloud (AWS, Azure, GCP, v.v.).
Ngoài ra, code ứng dụng của bạn trông khác nhau tùy vào việc bạn muốn chạy một ứng dụng HTTP điển hình với nhiều route/endpoint hay chỉ cung cấp một route duy nhất (hoặc thực thi một phần code cụ thể).
Ví dụ, với cách tiếp cận mỗi endpoint một function, bạn có thể dùng `NestFactory.createApplicationContext()` thay vì khởi động HTTP server, thiết lập middleware, v.v.

Để minh họa, chúng ta sẽ tích hợp Nest (dùng `@nestjs/platform-express`, và do đó khởi động toàn bộ HTTP router đầy đủ chức năng)
với framework [Serverless](https://www.serverless.com/) (trong trường hợp này, nhắm tới AWS Lambda). Như đã nói, code của bạn sẽ khác nhau tùy vào nhà cung cấp cloud bạn chọn, cùng nhiều yếu tố khác.

Trước tiên, hãy cài các package cần thiết:

```bash
$ npm i @codegenie/serverless-express
$ npm i -D @types/aws-lambda serverless-offline
```

> info **Gợi ý** Để tăng tốc chu kỳ phát triển, chúng ta cài plugin `serverless-offline`, plugin này giả lập AWS Lambda và API Gateway ở local.

Khi đã cài đặt xong, hãy tạo file `serverless.yml` để cấu hình framework Serverless:

```yaml
service: serverless-example

plugins:
  - serverless-offline

provider:
  name: aws
  runtime: nodejs22.x

functions:
  main:
    handler: dist/main.handler
    events:
      - http:
          method: ANY
          path: /
      - http:
          method: ANY
          path: '{proxy+}'
```

> info **Gợi ý** Để tìm hiểu thêm về framework Serverless, hãy truy cập [tài liệu chính thức](https://www.serverless.com/framework/docs/).

Khi đã có file này, hãy mở file `main.ts` và cập nhật code bootstrap với boilerplate cần thiết:

```typescript
import { NestFactory } from '@nestjs/core';
import { configure } from '@codegenie/serverless-express';
import type { Callback, Context, Handler } from 'aws-lambda';
import { AppModule } from './app.module.js';

let server: Handler;

async function bootstrap(): Promise<Handler> {
  const app = await NestFactory.create(AppModule);
  await app.init();

  const expressApp = app.getHttpAdapter().getInstance();
  return configure({ app: expressApp });
}

export const handler: Handler = async (
  event: any,
  context: Context,
  callback: Callback,
) => {
  server = server ?? (await bootstrap());
  return server(event, context, callback);
};
```

> info **Gợi ý** Để tạo nhiều serverless function dùng chung các module, chúng tôi khuyên dùng [monorepo mode của CLI](/cli/monorepo#monorepo-mode).

> warning **Cảnh báo** Nếu bạn dùng package `@nestjs/swagger`, việc phục vụ Swagger UI từ một serverless function cần thêm một bước. Phía sau API Gateway, `originalUrl` của request có thể thiếu dấu gạch chéo ở cuối mà Swagger UI kỳ vọng, gây ra một vòng lặp redirect vô tận. Hãy đăng ký một middleware khôi phục nó **trước** khi gọi `SwaggerModule.setup()`:
>
> ```typescript
> app.use((req, res, next) => {
>   if (req.originalUrl === '/swagger') {
>     req.originalUrl = '/swagger/';
>   }
>   next();
> });
> ```

Tiếp theo, hãy đảm bảo tùy chọn `esModuleInterop` được bật trong file `tsconfig.json` để package `@codegenie/serverless-express` load đúng (các project được sinh bằng `nest new` bật nó mặc định).

```json
{
  "compilerOptions": {
    ...
    "esModuleInterop": true
  }
}
```

Giờ hãy build ứng dụng (bằng `nest build` hoặc `tsc`) và dùng CLI `serverless` để khởi động Lambda function ở local:

```bash
$ npm run build
$ npx serverless offline
```

Khi ứng dụng đang chạy, hãy mở trình duyệt và truy cập `http://localhost:3000/dev/[ANY_ROUTE]`, trong đó `[ANY_ROUTE]` là bất kỳ endpoint nào được đăng ký trong ứng dụng.

Các phần ở trên cho thấy việc bundle ứng dụng bằng `webpack` có thể ảnh hưởng đáng kể tới tổng thời gian bootstrap.
Để nó hoạt động với ví dụ này, bundle phải đưa ra hàm `handler` được export. Bắt đầu từ `@nestjs/cli` v12.0.8, cấu hình `webpack` mặc định làm việc này bằng cách đặt `output.library.type` thành `commonjs2`, miễn là `webpack.config.js` của bạn giữ `...options.output` khi nó override `output`.
Với các phiên bản CLI cũ hơn, hoặc với một cấu hình không kế thừa `options.output`, hãy thêm vài thiết lập nữa vào file `webpack.config.js`. Cụ thể, hãy đặt thuộc tính `output.libraryTarget` thành `commonjs2`.

```javascript
return {
  ...options,
  externals: [],
  output: {
    ...options.output,
    libraryTarget: 'commonjs2',
  },
  // ... the rest of the configuration
};
```

Khi đã có cấu hình này, hãy chạy `$ nest build --webpack` để biên dịch code của function (rồi `$ npx serverless offline` để test nó).

Chúng tôi cũng khuyên (nhưng **không bắt buộc**, vì nó làm chậm quá trình build) cài package `terser-webpack-plugin` và override cấu hình của nó để giữ nguyên tên class khi minify bản build production. Nếu không, `class-validator` có thể hoạt động sai trong ứng dụng của bạn.

```javascript
const TerserPlugin = require('terser-webpack-plugin');

return {
  ...options,
  externals: [],
  optimization: {
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          keep_classnames: true,
        },
      }),
    ],
  },
  output: {
    ...options.output,
    libraryTarget: 'commonjs2',
  },
  // ... the rest of the configuration
};
```

#### Dùng tính năng ứng dụng standalone <a id="using-standalone-application-feature"></a>

Ngoài ra, nếu bạn muốn giữ function gọn nhẹ và không cần tính năng nào liên quan tới HTTP (routing, cũng như guard, interceptor, pipe, v.v.),
hãy dùng `NestFactory.createApplicationContext()` (như đã đề cập trước đó) thay vì chạy toàn bộ HTTP server (và `express` bên dưới):

```typescript
@@filename(main)
import { HttpStatus } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import type { Callback, Context, Handler } from 'aws-lambda';
import { AppModule } from './app.module.js';
import { AppService } from './app.service.js';

export const handler: Handler = async (
  event: any,
  context: Context,
  callback: Callback,
) => {
  const appContext = await NestFactory.createApplicationContext(AppModule);
  const appService = appContext.get(AppService);

  return {
    body: appService.getHello(),
    statusCode: HttpStatus.OK,
  };
};
```

> info **Gợi ý** `NestFactory.createApplicationContext()` không bọc các method của controller bằng enhancer (guard, interceptor, v.v.). Nếu bạn cần enhancer, hãy dùng method `NestFactory.create()`.

Bạn cũng có thể truyền object `event` cho một provider, như một `EventsService`, provider này xử lý nó và trả về một giá trị tương ứng (tùy vào input và logic nghiệp vụ của bạn).

```typescript
export const handler: Handler = async (
  event: any,
  context: Context,
  callback: Callback,
) => {
  const appContext = await NestFactory.createApplicationContext(AppModule);
  const eventsService = appContext.get(EventsService);
  return eventsService.process(event);
};
```
