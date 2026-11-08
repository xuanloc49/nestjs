### Giới thiệu

Đặc tả [OpenAPI](https://swagger.io/specification/) là một định dạng định nghĩa không phụ thuộc ngôn ngữ dùng để mô tả RESTful API. Nest cung cấp một [module](https://github.com/nestjs/swagger) riêng sinh ra đặc tả như vậy từ các decorator trong code của bạn.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài dependency cần thiết:

```bash
$ npm install --save @nestjs/swagger
```

> warning **Cảnh báo** Nếu bạn dùng Fastify, hãy cài thêm `@fastify/static`:
>
> ```bash
> $ npm install --save @fastify/static
> ```

#### Bootstrap

Khi đã cài đặt xong, hãy mở file `main.ts` và khởi tạo Swagger bằng class `SwaggerModule`:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  const config = new DocumentBuilder()
    .setTitle('Cats example')
    .setDescription('The cats API description')
    .setVersion('1.0')
    .addTag('cats')
    .build();
  const documentFactory = () => SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api', app, documentFactory);

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

> info **Gợi ý** Bọc `SwaggerModule.createDocument()` trong một factory function sẽ trì hoãn việc sinh tài liệu cho tới khi tài liệu được yêu cầu lần đầu, giúp tiết kiệm thời gian khởi tạo. Tài liệu kết quả là một object có thể serialize, tuân theo đặc tả [OpenAPI Document](https://swagger.io/specification/#openapi-document). Thay vì phục vụ nó qua HTTP, bạn cũng có thể lưu nó thành file JSON hoặc YAML và dùng ở nơi khác.

> warning **Cảnh báo** Nếu bạn gọi `createDocument()` ngay lập tức (thay vì trong một factory function, như ở trên), hãy đảm bảo `app.enableVersioning()` chạy trước. Nếu không, các `paths` được sinh ra sẽ thiếu tiền tố phiên bản. Pattern factory không bị ảnh hưởng, vì tài liệu chưa được dựng cho tới khi được yêu cầu lần đầu.

`DocumentBuilder` dựng cấu trúc một tài liệu cơ sở tuân theo OpenAPI Specification. Các method của nó cho phép bạn đặt các thuộc tính như tiêu đề, mô tả và phiên bản. Để tạo một tài liệu đầy đủ (với mọi HTTP route được định nghĩa), hãy dùng method `createDocument()` của class `SwaggerModule`. Nó nhận hai tham số: một instance ứng dụng và cấu hình tài liệu cơ sở được trả về bởi `DocumentBuilder#build()`. Một tham số thứ ba tùy chọn, có type `SwaggerDocumentOptions`, được trình bày trong phần [tùy chọn tài liệu](/openapi/introduction#document-options).

Tiếp theo, gọi method `setup()`. Nó nhận:

1. Đường dẫn để mount Swagger UI
2. Một instance ứng dụng
3. Object tài liệu, hoặc một factory function trả về nó (như ở trên)
4. Một object cấu hình tùy chọn (xem [tùy chọn setup](/openapi/introduction#setup-options))

Giờ hãy chạy lệnh sau để khởi động HTTP server:

```bash
$ npm run start
```

Trong khi ứng dụng đang chạy, hãy mở trình duyệt và truy cập `http://localhost:3000/api`. Bạn sẽ thấy Swagger UI.

<figure><img src="/assets/swagger1.png" /></figure>

`SwaggerModule` tự động phản ánh mọi endpoint của bạn.

> info **Gợi ý** Để sinh và tải về một file Swagger JSON, hãy truy cập `http://localhost:3000/api-json` (giả sử tài liệu Swagger của bạn có tại `http://localhost:3000/api`).
> Bạn cũng có thể đưa nó ra trên một route tùy chọn bằng tùy chọn `jsonDocumentUrl` của method `setup()`:
>
> ```typescript
> SwaggerModule.setup('swagger', app, documentFactory, {
>   jsonDocumentUrl: 'swagger/json',
> });
> ```
>
> Khi đó nó sẽ có tại `http://localhost:3000/swagger/json`.

> info **Gợi ý** Swagger UI hoạt động với [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) mặc định của [security header](/security/helmet) có sẵn của Nest. Nếu bạn thêm script qua `customJs`/`customJsStr`, hoặc phục vụ Swagger UI qua HTTP thường bên ngoài môi trường phát triển cục bộ, hãy xem [Swagger UI và GraphQL IDE](/security/helmet#swagger-ui-and-graphql-ides) để biết các directive cần điều chỉnh.

> warning **Cảnh báo** Khi bạn đăng ký `helmet` trực tiếp với Fastify thay vào đó, [CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) của nó có thể chặn Swagger UI. Để giải quyết xung đột này, hãy cấu hình CSP như bên dưới:
>
> ```typescript
> app.register(helmet, {
>   contentSecurityPolicy: {
>     directives: {
>       defaultSrc: [`'self'`],
>       styleSrc: [`'self'`, `'unsafe-inline'`],
>       imgSrc: [`'self'`, 'data:', 'validator.swagger.io'],
>       scriptSrc: [`'self'`, `https:`, `'unsafe-inline'`],
>     },
>   },
> });
>
> // If you are not going to use CSP at all, you can use this:
> app.register(helmet, {
>   contentSecurityPolicy: false,
> });
> ```

#### Tùy chọn tài liệu <a id="document-options"></a>

Khi tạo một tài liệu, bạn có thể truyền thêm các tùy chọn để tinh chỉnh hành vi của library. Các tùy chọn này có type `SwaggerDocumentOptions`:

```TypeScript
export interface SwaggerDocumentOptions {
  /**
   * List of modules to include in the specification
   */
  include?: Function[];

  /**
   * Additional, extra models that should be inspected and included in the specification
   */
  extraModels?: Function[];

  /**
   * If `true`, swagger will ignore the global prefix set through `setGlobalPrefix()` method
   */
  ignoreGlobalPrefix?: boolean;

  /**
   * If `true`, swagger will also load routes from the modules imported by `include` modules
   */
  deepScanRoutes?: boolean;

  /**
   * Custom operationIdFactory that will be used to generate the `operationId`
   * based on the `controllerKey`, `methodKey`, and version.
   * @default () => controllerKey_methodKey_version
   */
  operationIdFactory?: OperationIdFactory;

  /**
   * Custom linkNameFactory that will be used to generate the name of links
   * in the `links` field of responses
   *
   * @see [Link objects](https://swagger.io/docs/specification/links/)
   *
   * @default () => `${controllerKey}_${methodKey}_from_${fieldKey}`
   */
  linkNameFactory?: (
    controllerKey: string,
    methodKey: string,
    fieldKey: string
  ) => string;

  /*
   * Generate tags automatically based on the controller name.
   * If `false`, you must use the `@ApiTags()` decorator to define tags.
   * Otherwise, the controller name without the suffix `Controller` will be used.
   * @default true
   */
  autoTagControllers?: boolean;

  /**
   * If `true`, swagger will only include routes that are decorated with the `@ApiIncludeEndpoint()` decorator
   * @default false
   */
  onlyIncludeDecoratedEndpoints?: boolean;

  /**
   * If `true`, `default` values that are non-plain objects at runtime
   * (e.g., `new Date()` or class instances) are omitted from the document,
   * so the document doesn't change on every restart.
   * @default false
   */
  excludeDynamicDefaults?: boolean;

  /**
   * If set, `example` and `examples` values on component schemas are
   * truncated once their nested object/array depth exceeds this number.
   * Per-property `@ApiProperty({ exampleMaxDepth })` overrides it.
   * @default undefined
   */
  exampleMaxDepth?: number;

  /**
   * Converts Standard Schema instances passed to route parameter decorators
   * into OpenAPI schemas (see "Standard Schema (Zod, Valibot)" below).
   */
  standardSchemaConverter?: StandardSchemaConverter;
}
```

Ví dụ, để sinh tên operation như `createUser` thay vì `UsersController_createUser`, hãy đặt như sau:

```TypeScript
const options: SwaggerDocumentOptions =  {
  operationIdFactory: (
    controllerKey: string,
    methodKey: string
  ) => methodKey
};
const documentFactory = () => SwaggerModule.createDocument(app, config, options);
```

#### Standard Schema (Zod, Valibot)

Các route parameter decorator của Nest nhận một schema tương thích [Standard Schema](https://standardschema.dev/) qua tùy chọn `schema` của chúng (xem chương [controller](/controllers#request-object)):

```typescript
@@filename(cats.controller)
import { Body, Controller, Post } from '@nestjs/common';
import { z } from 'zod';

const createCatSchema = z.object({
  name: z.string(),
  age: z.number().int().positive(),
  breed: z.string(),
});
type CreateCatDto = z.infer<typeof createCatSchema>;

@Controller('cats')
export class CatsController {
  @Post()
  create(@Body({ schema: createCatSchema }) createCatDto: CreateCatDto) {
    return this.catsService.create(createCatDto);
  }
}
```

Module Swagger nhận các schema này và biến chúng thành request body và parameter trong tài liệu được sinh ra.

##### Các library không cần cấu hình <a id="libraries-that-need-no-configuration"></a>

Nếu library validation của bạn hiện thực phần mở rộng **Standard JSON Schema** (tức là schema của nó có `~standard.jsonSchema`), Nest tự chuyển đổi các schema, và không có gì phải cấu hình. Ví dụ, Zod 4.2 trở lên hiện thực phần mở rộng này. Nest yêu cầu target `openapi-3.0` và dùng biến thể `input` hoặc `output`, tùy vào việc schema mô tả một request hay một response.

##### Cung cấp một converter <a id="supplying-a-converter"></a>

Với các library không có phần mở rộng đó (hoặc khi bạn muốn tự kiểm soát việc chuyển đổi), hãy cung cấp một `standardSchemaConverter` trong `SwaggerDocumentOptions`. Nó nhận schema thô và `schemaType` đang được sinh, và trả về OpenAPI schema đã chuyển đổi:

```typescript
standardSchemaConverter?: (
  schema: unknown,
  options: { schemaType: 'input' | 'output' },
) => { schema: unknown; components?: Record<string, any> } | undefined;
```

Nest gọi converter trước khi thử chuyển đổi gốc. Trả về `undefined` báo cho Nest biết converter không xử lý schema này, nên Nest fallback về việc chuyển đổi gốc mô tả ở trên. Điều này giúp việc hỗ trợ nhiều library từ một converter trở nên an toàn.

Với **Zod**, bạn có thể dùng [zod-openapi](https://github.com/samchungy/zod-openapi):

```bash
$ npm i --save-dev zod-openapi
```

```typescript
@@filename(main)
import { SwaggerDocumentOptions, SwaggerModule } from '@nestjs/swagger';
import { createSchema } from 'zod-openapi';

const documentOptions: SwaggerDocumentOptions = {
  standardSchemaConverter: (schema, { schemaType }) => {
    const converted = createSchema(schema as never, {
      io: schemaType,
      openapiVersion: '3.0.0',
    });
    return { schema: converted.schema, components: converted.components };
  },
};

const documentFactory = () =>
  SwaggerModule.createDocument(app, config, documentOptions);
```

Với **Valibot**, hãy dùng [@valibot/to-json-schema](https://github.com/fabian-hiller/valibot/tree/main/packages/to-json-schema):

```bash
$ npm i --save-dev @valibot/to-json-schema
```

```typescript
@@filename(main)
import { SwaggerDocumentOptions } from '@nestjs/swagger';
import { toJsonSchema } from '@valibot/to-json-schema';

const documentOptions: SwaggerDocumentOptions = {
  standardSchemaConverter: (schema, { schemaType }) => ({
    schema: toJsonSchema(schema as never, {
      target: 'openapi-3.0',
      typeMode: schemaType,
    }),
  }),
};
```

Hai converter khác nhau ở một điểm. `createSchema()` có thể tách các định nghĩa dùng lại được ra ngoài, nên kết quả của nó mang theo một map `components`, bạn truyền nó đi tiếp và Nest merge nó vào các component dùng chung của tài liệu. `toJsonSchema()` trả về một schema duy nhất tự đầy đủ, nên converter cho Valibot bỏ qua `components`.

##### Hỗ trợ nhiều library cùng lúc <a id="supporting-several-libraries-at-once"></a>

Vì converter nhận schema dưới dạng `unknown`, bạn có thể rẽ nhánh theo vendor của schema và hỗ trợ nhiều library trong cùng một ứng dụng. Mọi Standard Schema đều cung cấp vendor của nó tại `~standard.vendor`:

```typescript
@@filename(main)
import { SwaggerDocumentOptions } from '@nestjs/swagger';
import { toJsonSchema } from '@valibot/to-json-schema';
import { createSchema } from 'zod-openapi';

function hasVendor(schema: unknown, vendor: string) {
  return (
    !!schema &&
    typeof schema === 'object' &&
    (schema as { '~standard'?: { vendor?: string } })['~standard']?.vendor ===
      vendor
  );
}

const documentOptions: SwaggerDocumentOptions = {
  standardSchemaConverter: (schema, { schemaType }) => {
    if (hasVendor(schema, 'zod')) {
      const converted = createSchema(schema as never, {
        io: schemaType,
        openapiVersion: '3.0.0',
      });
      return { schema: converted.schema, components: converted.components };
    }

    if (hasVendor(schema, 'valibot')) {
      return {
        schema: toJsonSchema(schema as never, {
          target: 'openapi-3.0',
          typeMode: schemaType,
        }),
      };
    }

    // Not handled here - let Nest fall back to native conversion
    return undefined;
  },
};
```

> warning **Cảnh báo** Luôn thu hẹp theo vendor trước khi gọi một converter riêng của library. Truyền một schema Valibot cho `createSchema()` (hoặc ngược lại) sẽ throw lúc sinh tài liệu thay vì thất bại một cách nhẹ nhàng.

> info **Gợi ý** `schemaType` quan trọng khi schema của bạn thực hiện biến đổi: dạng `input` là những gì client gửi, còn dạng `output` là những gì handler của bạn nhận sau khi parse. Nest yêu cầu biến thể phù hợp với vị trí đang được mô tả, nên hãy truyền thẳng giá trị đó cho converter thay vì hardcode một giá trị.

#### Tùy chọn setup <a id="setup-options"></a>

Bạn có thể cấu hình Swagger UI bằng cách truyền một options object implement interface `SwaggerCustomOptions` làm tham số thứ tư của method `SwaggerModule#setup()`.

```TypeScript
export interface SwaggerCustomOptions {
  /**
   * If `true`, Swagger resources paths will be prefixed by the global prefix set through `setGlobalPrefix()`.
   * Default: `false`.
   * @see https://docs.nestjs.com/faq/global-prefix
   */
  useGlobalPrefix?: boolean;

  /**
   * If `false`, the Swagger UI will not be served. Only API definitions (JSON and YAML)
   * will be accessible (on `/{path}-json` and `/{path}-yaml`). To fully disable both the Swagger UI and API definitions, use `raw: false`.
   * Default: `true`.
   * @deprecated Use `ui` instead.
   */
  swaggerUiEnabled?: boolean;

  /**
   * If `false`, the Swagger UI will not be served. Only API definitions (JSON and YAML)
   * will be accessible (on `/{path}-json` and `/{path}-yaml`). To fully disable both the Swagger UI and API definitions, use `raw: false`.
   * Default: `true`.
   */
  ui?: boolean;

  /**
   * If `true`, raw definitions for all formats will be served.
   * Alternatively, you can pass an array to specify the formats to be served, e.g., `raw: ['json']` to serve only JSON definitions.
   * If set to `false` or an empty array, no definitions (JSON or YAML) will be served.
   * Use this option to control the availability of Swagger-related endpoints.
   * Default: `true`.
   */
  raw?: boolean | Array<'json' | 'yaml'>;

  /**
   * Url point the API definition to load in Swagger UI.
   */
  swaggerUrl?: string;

  /**
   * Path of the JSON API definition to serve.
   * Default: `<path>-json`.
   */
  jsonDocumentUrl?: string;

  /**
   * Path of the YAML API definition to serve.
   * Default: `<path>-yaml`.
   */
  yamlDocumentUrl?: string;

  /**
   * Hook allowing to alter the OpenAPI document before being served.
   * It's called after the document is generated and before it is served as JSON & YAML.
   * The hook can return either a plain `OpenAPIObject` or a `Promise<OpenAPIObject>`.
   */
  patchDocumentOnRequest?: <TRequest = any, TResponse = any>(
    req: TRequest,
    res: TResponse,
    document: OpenAPIObject
  ) => OpenAPIObject | Promise<OpenAPIObject>;

  /**
   * If `true`, the selector of OpenAPI definitions is displayed in the Swagger UI interface.
   * Default: `false`.
   */
  explorer?: boolean;

  /**
   * Additional Swagger UI options
   */
  swaggerOptions?: SwaggerUiOptions;

  /**
   * Custom CSS styles to inject in Swagger UI page.
   */
  customCss?: string;

  /**
   * URL(s) of a custom CSS stylesheet to load in Swagger UI page.
   */
  customCssUrl?: string | string[];

  /**
   * URL(s) of custom JavaScript files to load in Swagger UI page.
   */
  customJs?: string | string[];

  /**
   * Custom JavaScript scripts to load in Swagger UI page.
   */
  customJsStr?: string | string[];

  /**
   * Custom favicon for Swagger UI page.
   */
  customfavIcon?: string;

  /**
   * Custom title for Swagger UI page.
   */
  customSiteTitle?: string;

  /**
   * File system path (ex: ./node_modules/swagger-ui-dist) containing static Swagger UI assets.
   */
  customSwaggerUiPath?: string;

  /**
   * @deprecated This property has no effect.
   */
  validatorUrl?: string;

  /**
   * @deprecated This property has no effect.
   */
  url?: string;

  /**
   * @deprecated This property has no effect.
   */
  urls?: Record<'url' | 'name', string>[];
}
```

> info **Gợi ý** `ui` và `raw` là các tùy chọn độc lập. Tắt Swagger UI (`ui: false`) không tắt các định nghĩa API (JSON/YAML). Ngược lại, tắt các định nghĩa API (`raw: []`) không tắt Swagger UI.
>
> Ví dụ, cấu hình sau tắt Swagger UI nhưng vẫn giữ định nghĩa API dạng JSON:
>
> ```typescript
> const options: SwaggerCustomOptions = {
>   ui: false, // Swagger UI is disabled
>   raw: ['json'], // JSON API definition is still accessible (YAML is disabled)
> };
> SwaggerModule.setup('api', app, documentFactory, options);
> ```
>
> Trong trường hợp này, `http://localhost:3000/api-json` vẫn truy cập được, nhưng `http://localhost:3000/api` (Swagger UI) thì không.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có trong [repository của Nest](https://github.com/nestjs/nest/tree/master/sample/11-swagger).
