### Các tính năng khác

Trang này nói về các tính năng khác của module Swagger mà bạn có thể thấy hữu ích.

#### Global prefix

Để bỏ qua global prefix được đặt qua `setGlobalPrefix()`, hãy dùng tùy chọn `ignoreGlobalPrefix`:

```typescript
const document = SwaggerModule.createDocument(app, options, {
  ignoreGlobalPrefix: true,
});
```

#### Parameter global <a id="global-parameters"></a>

Để định nghĩa parameter cho mọi route, hãy dùng `DocumentBuilder`:

```typescript
const config = new DocumentBuilder()
  .addGlobalParameters({
    name: 'tenantId',
    in: 'header',
  })
  // other configurations
  .build();
```

#### Response global <a id="global-responses"></a>

Để định nghĩa response global cho mọi route, hãy dùng `DocumentBuilder`. Điều này hữu ích để thiết lập các response nhất quán trên mọi endpoint trong ứng dụng, như các mã lỗi `401 Unauthorized` hay `500 Internal Server Error`.

```typescript
const config = new DocumentBuilder()
  .addGlobalResponse({
    status: 500,
    description: 'Internal server error',
  })
  // other configurations
  .build();
```

#### Nhiều đặc tả <a id="multiple-specifications"></a>

`SwaggerModule` hỗ trợ nhiều đặc tả. Nói cách khác, bạn có thể phục vụ các tài liệu khác nhau, với các UI khác nhau, trên các endpoint khác nhau.

Để hỗ trợ nhiều đặc tả, ứng dụng của bạn phải được viết theo cách tiếp cận module hóa. Method `createDocument()` nhận một tham số thứ ba, `extraOptions`, là một object có thuộc tính `include`. Thuộc tính `include` nhận một mảng module.

Thiết lập hỗ trợ nhiều đặc tả như bên dưới:

```typescript
import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module.js';
import { CatsModule } from './cats/cats.module.js';
import { DogsModule } from './dogs/dogs.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  /**
   * createDocument(application, configurationOptions, extraOptions);
   *
   * createDocument method takes an optional 3rd argument "extraOptions"
   * which is an object with "include" property where you can pass an Array
   * of Modules that you want to include in that Swagger Specification
   * E.g: CatsModule and DogsModule will have two separate Swagger Specifications which
   * will be exposed on two different SwaggerUI with two different endpoints.
   */

  const options = new DocumentBuilder()
    .setTitle('Cats example')
    .setDescription('The cats API description')
    .setVersion('1.0')
    .addTag('cats')
    .build();

  const catDocumentFactory = () =>
    SwaggerModule.createDocument(app, options, {
      include: [CatsModule],
    });
  SwaggerModule.setup('api/cats', app, catDocumentFactory);

  const secondOptions = new DocumentBuilder()
    .setTitle('Dogs example')
    .setDescription('The dogs API description')
    .setVersion('1.0')
    .addTag('dogs')
    .build();

  const dogDocumentFactory = () =>
    SwaggerModule.createDocument(app, secondOptions, {
      include: [DogsModule],
    });
  SwaggerModule.setup('api/dogs', app, dogDocumentFactory);

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Giờ hãy khởi động server bằng lệnh sau:

```bash
$ npm run start
```

Truy cập `http://localhost:3000/api/cats` để xem Swagger UI cho cats:

<figure><img src="/assets/swagger-cats.png" /></figure>

Tương ứng, `http://localhost:3000/api/dogs` sẽ đưa ra Swagger UI cho dogs:

<figure><img src="/assets/swagger-dogs.png" /></figure>

#### Dropdown trên thanh explorer <a id="dropdown-in-the-explorer-bar"></a>

Để liệt kê nhiều đặc tả trong menu dropdown của thanh explorer, hãy đặt `explorer: true` và cấu hình `swaggerOptions.urls` trong `SwaggerCustomOptions`.

> info **Gợi ý** Hãy đảm bảo `swaggerOptions.urls` trỏ tới định dạng JSON của các tài liệu Swagger. Để chỉ định đường dẫn của tài liệu JSON, hãy dùng tùy chọn `jsonDocumentUrl` của `SwaggerCustomOptions`. Để biết thêm các tùy chọn, xem [tùy chọn setup](/openapi/introduction#setup-options).

Đây là cách chọn nhiều đặc tả từ một dropdown trên thanh explorer:

```typescript
import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module.js';
import { CatsModule } from './cats/cats.module.js';
import { DogsModule } from './dogs/dogs.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Main API options
  const options = new DocumentBuilder()
    .setTitle('Multiple Specifications Example')
    .setDescription('Description for multiple specifications')
    .setVersion('1.0')
    .build();

  // Create main API document
  const document = SwaggerModule.createDocument(app, options);

  // Setup main API Swagger UI with dropdown support
  SwaggerModule.setup('api', app, document, {
    explorer: true,
    swaggerOptions: {
      urls: [
        {
          name: '1. API',
          url: 'api/swagger.json',
        },
        {
          name: '2. Cats API',
          url: 'api/cats/swagger.json',
        },
        {
          name: '3. Dogs API',
          url: 'api/dogs/swagger.json',
        },
      ],
    },
    jsonDocumentUrl: '/api/swagger.json',
  });

  // Cats API options
  const catOptions = new DocumentBuilder()
    .setTitle('Cats Example')
    .setDescription('Description for the Cats API')
    .setVersion('1.0')
    .addTag('cats')
    .build();

  // Create Cats API document
  const catDocument = SwaggerModule.createDocument(app, catOptions, {
    include: [CatsModule],
  });

  // Setup Cats API Swagger UI
  SwaggerModule.setup('api/cats', app, catDocument, {
    jsonDocumentUrl: '/api/cats/swagger.json',
  });

  // Dogs API options
  const dogOptions = new DocumentBuilder()
    .setTitle('Dogs Example')
    .setDescription('Description for the Dogs API')
    .setVersion('1.0')
    .addTag('dogs')
    .build();

  // Create Dogs API document
  const dogDocument = SwaggerModule.createDocument(app, dogOptions, {
    include: [DogsModule],
  });

  // Setup Dogs API Swagger UI
  SwaggerModule.setup('api/dogs', app, dogDocument, {
    jsonDocumentUrl: '/api/dogs/swagger.json',
  });

  await app.listen(process.env.PORT ?? 3000);
}

await bootstrap();
```

Ví dụ này thiết lập một API chính cùng với các đặc tả riêng cho cats và dogs, mỗi đặc tả đều truy cập được từ dropdown trên thanh explorer.
