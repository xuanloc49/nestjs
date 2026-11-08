### Hướng dẫn migration

Bài này hướng dẫn bạn migrate từ NestJS phiên bản 11 lên phiên bản 12. Phiên bản 12 tập trung vào các package ESM, các thiết lập mặc định mới của CLI, hỗ trợ đầy đủ cho validation và serialization dựa trên [Standard Schema](https://standardschema.dev/), và hỗ trợ [observability](/observability/overview) có sẵn.

#### Nâng cấp package <a id="upgrading-packages"></a>

Hãy bắt đầu bằng việc nâng cấp chính Nest CLI, vì lệnh upgrade dùng bên dưới đi kèm với nó:

```bash
$ npm i -g @nestjs/cli@latest @nestjs/schematics@latest
```

Nếu project của bạn giữ CLI dưới dạng dev dependency local, hãy cập nhật nó ở đó nữa, cùng với TypeScript. `@nestjs/schematics` v12 yêu cầu TypeScript 6 làm peer dependency, nên npm sẽ từ chối cài nó cạnh TypeScript 5:

```bash
$ npm i -D @nestjs/cli@latest @nestjs/schematics@latest typescript@^6
```

Nếu npm vẫn báo xung đột peer dependency, nhiều khả năng lockfile của bạn đang ghim một bản `ts-jest` hoặc `typescript-eslint` cũ không chấp nhận TypeScript 6. Cả hai đều đi kèm các project được sinh bởi CLI v11. Hãy chạy `npm update ts-jest typescript-eslint` để chuyển chúng lên các bản mới hơn trong range hiện tại, rồi chạy lại lệnh ở trên.

Khi đã có CLI mới nhất, hãy chạy `nest upgrade` từ thư mục gốc của project:

```bash
$ nest upgrade
```

Lệnh này chuyển mọi package `@nestjs/*` mà nó nhận ra lên major tương thích v12 cùng một lúc, để framework, các platform adapter và các package đi kèm luôn đồng bộ, rồi cài đặt chúng. Nó cũng nâng TypeScript lên v6 và áp dụng những phần mang tính cơ học của quá trình migration được mô tả trong hướng dẫn này (các tùy chọn webpack trong `nest-cli.json`, các thay đổi về `playground` và transport subscription của GraphQL, việc đổi package NATS, và các tùy chọn validation của `@nestjs/config`). Cuối cùng, nó in ra một báo cáo về mọi thứ đã thay đổi, cùng ghi chú về những thay đổi hành vi mà nó không thể migrate giúp bạn. Để xem báo cáo đó mà không đụng vào file nào, hãy chạy lệnh với `--dry-run` trước. Xem [nest upgrade](/cli/usages#nest-upgrade) để biết danh sách đầy đủ các bước và tùy chọn.

> info **Gợi ý** `nest upgrade` thay thế cho cách làm thủ công bằng [npm-check-updates (ncu)](https://npmjs.com/package/npm-check-updates) từng được khuyên dùng ở đây. Bạn vẫn có thể tự nâng cấp package nếu muốn; điều quan trọng là mọi package Nest phải lên cùng một major cùng lúc. Lệnh này chỉ nâng dependency CLI bên trong project, đó là lý do bạn cần nâng cấp binary global trước.

#### Yêu cầu về Node.js <a id="nodejs-requirements"></a>

Yêu cầu về Node.js khác nhau tùy vào việc bạn đang **chạy** một ứng dụng hay **sinh** code bằng CLI:

| Bạn đang làm gì | Node.js tối thiểu |
| --- | --- |
| Chạy một ứng dụng Nest 12 | **v20.19+**, hoặc **v22.12+** trên dòng 22.x |
| `nest new`, `nest generate`, `nest upgrade` (`@nestjs/schematics`) | **v22.22.3+**, **v24.15+**, hoặc **v26+** |

Bản thân `@nestjs/core` vẫn khai báo `>= 20`, nhưng các package v12 chỉ có ESM, và việc dùng chúng từ một ứng dụng CommonJS dựa vào `require(esm)`, tính năng chỉ được bật mà không cần flag từ Node.js 20.19 và 22.12 trở đi. Dòng 21.x chưa bao giờ có nó và không được hỗ trợ. `nest upgrade` kiểm tra đúng điều này và từ chối chạy trên bản cũ hơn.

AWS Lambda tắt `require(esm)` mặc định trên các runtime Node.js 20, 22 và 24, kể cả khi bản Node.js upstream tương ứng có bật nó. Để chạy một ứng dụng Nest 12 dạng CommonJS trên các runtime Lambda này, hãy bật nó qua biến môi trường `NODE_OPTIONS` của function:

```text
NODE_OPTIONS=--experimental-require-module
```

Nếu `NODE_OPTIONS` đã chứa các flag khác, hãy nối flag này vào giá trị hiện có. Xem [tài liệu AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/lambda-nodejs.html#nodejs-experimental) để biết chi tiết và các giới hạn hỗ trợ của tính năng thử nghiệm.

Các schematic của CLI có mức tối thiểu cao hơn: `@nestjs/schematics` yêu cầu **Node.js v22.22.3+, v24.15+, hoặc v26+**, kế thừa từ Angular devkit mà nó được xây trên đó. Vì vậy việc scaffold và nâng cấp cần một runtime mới hơn so với việc chạy framework. Các dòng 23.x và 25.x, cũng như các bản 22.x và 24.x cũ hơn, đều bị loại trừ.

> info **Gợi ý** Cách đơn giản nhất để thỏa mọi yêu cầu là chạy bản active LTS mới nhất. Chỉ chọn mức tối thiểu nếu bạn có lý do cụ thể để ở lại đó. Nếu vậy, hãy nhớ rằng Node.js 20.19 đủ để chạy ứng dụng, nhưng không đủ để dùng các generator của CLI.

#### Package ESM <a id="esm-packages"></a>

Mọi package lõi của Nest giờ đều được phát hành dưới dạng ESM. Với hầu hết ứng dụng hiện có, việc này ít gây xáo trộn hơn nhiều so với vài năm trước, vì các bản Node.js hiện đại hỗ trợ `require(esm)`.

> info **Gợi ý** Việc migrate **ứng dụng của chính bạn** sang ESM là hoàn toàn tùy chọn và **không** phải là một phần của việc nâng cấp lên v12. Vì các package ESM của Nest có thể được dùng từ CommonJS thông qua `require(esm)`, một ứng dụng CommonJS có thể nâng cấp lên v12 và giữ nguyên CommonJS bao lâu tùy bạn; `nest upgrade` cố ý không đụng tới module format của bạn. Có chuyển hay không là tùy sở thích. Nếu bạn quyết định chuyển, hai phần cuối của hướng dẫn này, [Chuyển project sang ESM](#switching-your-project-to-esm) và [Chuyển code của bạn sang ESM](#moving-your-own-code-to-esm), sẽ hướng dẫn bạn.

Trên thực tế, điều này có nghĩa là:

- Nhiều ứng dụng CommonJS hiện có vẫn tiếp tục chạy mà không cần viết lại toàn bộ
- Hãy xem lại các script bootstrap tự viết, build tooling và test runner nếu chúng có giả định về các package chỉ dùng CommonJS
- Nếu bạn duy trì cấu hình bundler hoặc runtime riêng, hãy đảm bảo nó khớp với module format mà project của bạn thực sự dùng

Với project mới, CLI giờ cho phép bạn chọn giữa cấu trúc project CommonJS và ESM.

#### Mặc định cho project mới <a id="new-project-defaults"></a>

`nest new` giờ hỏi bạn muốn sinh project CommonJS hay ESM.

- Project ESM dùng Vitest mặc định (project CommonJS dùng Jest)
- Mọi project được sinh ra đều dùng oxlint mặc định

Điều này chỉ thay đổi những gì CLI scaffold cho bạn. Các project hiện có có thể giữ tooling hiện tại và migrate theo lịch của riêng mình.

#### Bộ công cụ testing <a id="testing-stack"></a>

Các tiện ích testing của Nest vẫn giữ nguyên. Thay đổi chính là bộ công cụ mặc định được dùng bởi các project ESM được sinh ra và bởi chính các repository và sample của framework: Vitest giờ là lựa chọn mặc định chính cho các workflow ESM.

Nếu ứng dụng của bạn đã dùng một test runner khác, bạn không cần migrate ngay. `@nestjs/testing` vẫn không phụ thuộc vào test runner cụ thể nào.

> warning **Cảnh báo** Nếu bạn ở lại với Jest, lưu ý rằng nó chỉ load được các package v12 chỉ-ESM trên Node.js v24.9 trở lên (các phiên bản cũ hơn thất bại với `ERR_REQUIRE_ASYNC_MODULE`). Hãy chạy bộ test trên Node.js v24.9+, hoặc cân nhắc migrate sang Vitest. `nest upgrade` nâng Jest lên v30 và cảnh báo về điều này.

Khi bạn quyết định migrate:

- Cập nhật các script `test`, `test:watch`, `test:cov` và `test:e2e`
- Xem lại các global riêng của runner và thay bằng các thứ tương đương của Vitest khi cần
- Kiểm tra các import `supertest` trong test E2E nếu thiết lập Vitest của bạn mong đợi default import

#### Mặc định về linting <a id="linting-defaults"></a>

Các project mới được sinh ra dùng oxlint mặc định. Bạn chỉ cần migrate nếu muốn repository của mình khớp với cấu trúc scaffold mới của CLI.

#### Schema trong route decorator <a id="route-decorator-schemas"></a>

Nest thêm một tùy chọn `schema` mới cho các route parameter decorator như `@Body()`, `@Query()`, `@Param()` và `@RawBody()`. Metadata schema được thiết kế cho các library tương thích [Standard Schema](https://standardschema.dev/) như Zod, Valibot và ArkType.

Ví dụ:

```typescript
@Post()
create(@Body({ schema: createUserSchema }) body: CreateUserDto) {
  return this.usersService.create(body);
}

@Get(':id')
findOne(@Param('id', { schema: z.coerce.number().int().positive() }) id: number) {
  return this.usersService.findOne(id);
}
```

Tự bản thân decorator chỉ gắn metadata schema. Để validate dựa trên nó, hãy đăng ký `StandardSchemaValidationPipe` có sẵn:

```typescript
app.useGlobalPipes(new StandardSchemaValidationPipe());
```

Đây là một lựa chọn theo hướng schema-first thay cho cách truyền thống dùng `ValidationPipe` cùng `class-validator`. Cùng các schema đó cũng có thể được dùng để sinh OpenAPI (xem [Standard Schema (Zod, Valibot)](/openapi/introduction#standard-schema-zod-valibot)).

Cách tiếp cận dựa trên decorator hiện có vẫn được hỗ trợ đầy đủ, và không có kế hoạch gỡ bỏ nó. Tùy chọn `schema` là một lựa chọn bổ sung cho các team thích các library schema-first như Zod.

#### Serialization với Standard Schema <a id="standard-schema-serialization"></a>

Nest cũng giới thiệu `StandardSchemaSerializerInterceptor`, interceptor này validate và biến đổi response gửi đi bằng cùng hệ sinh thái Standard Schema.

```typescript
@UseInterceptors(StandardSchemaSerializerInterceptor)
@SerializeOptions({ schema: userResponseSchema })
@Get(':id')
findOne(@Param('id') id: string) {
  return this.usersService.findOne(id);
}
```

Hãy dùng nó khi bạn muốn một schema, thay vì các decorator của `class-transformer`, quyết định hình dạng của response.

#### Cấu hình GraphQL IDE <a id="graphql-ide-configuration"></a>

GraphiQL giờ là GraphQL IDE mặc định. Nếu cần tùy biến nó, hãy truyền một object tùy chọn `graphiql` thay vì đặt `graphiql: true`.

```typescript
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  graphiql: {
    url: '/graphql',
    headers: {
      authorization: 'Bearer <token>',
    },
    shouldPersistHeaders: true,
    isHeadersEditorEnabled: true,
  },
});
```

Cách này tùy biến endpoint của IDE và hành vi của editor trong khi vẫn giữ GraphiQL được bật.

#### Transport cho GraphQL subscription <a id="graphql-subscriptions-transport"></a>

Bản `@nestjs/graphql` mới nhất gỡ bỏ hỗ trợ cho `subscriptions-transport-ws`. Hãy dùng `graphql-ws` cho GraphQL subscription thay thế.

```typescript
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  subscriptions: {
    'graphql-ws': true,
  },
});
```

Nếu ứng dụng của bạn vẫn phụ thuộc vào `subscriptions-transport-ws`, hãy lên kế hoạch migrate nó như một phần của việc nâng cấp package GraphQL.

#### NATS v3

Package microservices giờ nhắm tới NATS v3, phiên bản có một thay đổi breaking về dependency. Nếu bạn dùng NATS transport, hãy thay package `nats` cũ bằng `@nats-io/transport-node`:

```bash
$ npm uninstall nats
$ npm install @nats-io/transport-node
```

Nếu ứng dụng của bạn import trực tiếp các helper của NATS, hãy cài thêm `@nats-io/nats-core` và cập nhật các import đó. NATS v3 cũng đã bỏ các helper `StringCodec` và `JSONCodec`. Ví dụ, helper `headers()` giờ đến từ `@nats-io/nats-core`:

```typescript
import * as nats from '@nats-io/nats-core';
import { NatsRecordBuilder } from '@nestjs/microservices';

const headers = nats.headers();
headers.set('x-version', '1.0.0');

const record = new NatsRecordBuilder(payload).setHeaders(headers).build();
return this.client.send('record-builder-duplex', record);
```

Cũng hãy xem lại các serializer hoặc deserializer tự viết. Nest giờ serialize các packet NATS thành chuỗi JSON, và các NATS deserializer tự viết nhận toàn bộ object message của NATS thay vì một `Uint8Array` thô. Trên thực tế, các deserializer tự viết nên đọc payload bằng `msg.json()` thay vì tự decode byte.

#### Thứ tự gọi lifecycle hook <a id="lifecycle-hook-ordering"></a>

Các lifecycle hook giờ được gọi theo cấp trong cây phân cấp component. Điều này có thể thay đổi thứ tự thực thi của các hook như `onModuleInit`, `onApplicationBootstrap` và các shutdown hook khi nhiều provider hoặc module phụ thuộc lẫn nhau.

Nếu ứng dụng của bạn dựa vào một thứ tự hook cụ thể giữa các provider liên quan, hãy xem lại luồng đó trong quá trình nâng cấp và cập nhật mọi giả định trong logic khởi tạo, logic dọn dẹp, hoặc trong test.

#### `@Optional()` không còn được kế thừa bởi constructor khai báo lại <a id="optional-is-no-longer-inherited-by-a-redeclared-constructor"></a>

Nest giờ đọc các đánh dấu optional của tham số constructor từ chính class khai báo constructor đó. Một subclass tự khai báo constructor của riêng nó sẽ không còn kế thừa các đánh dấu từ constructor của class cha, nên Nest throw `UnknownDependenciesException` ở những chỗ mà v11 resolve tham số đó thành `undefined`.

Đây là thay đổi có chủ đích: một dependency thực sự bị thiếu trước đây sẽ âm thầm resolve thành `undefined`. Hãy khai báo lại đánh dấu trong constructor của subclass:

```typescript
@Injectable()
class Child extends Base {
  constructor(@Optional() options?: Options) {
    super(options);
  }
}
```

Từ NestJS v12.1, một subclass không có constructor riêng vẫn giữ các đánh dấu optional từ constructor của class cha, như ở v11. Các phiên bản 12.0.x cũng bỏ chúng trong trường hợp này.

#### class-validator và class-transformer <a id="class-validator-and-class-transformer"></a>

Workflow dựa trên decorator hiện có vẫn hoạt động trong v12. `ValidationPipe` và `ClassSerializerInterceptor` vẫn được hỗ trợ và vẫn phù hợp với các project dùng DTO dạng class.

Phiên bản 12 mở rộng các tùy chọn có sẵn chứ không thay thế các tùy chọn hiện có:

- Dùng `ValidationPipe` khi DTO của bạn dạng class và dựa vào decorator
- Dùng `StandardSchemaValidationPipe` khi library validation của bạn đã cung cấp sẵn schema tương thích Standard Schema
- Dùng `ClassSerializerInterceptor` khi việc định hình response của bạn dựa trên `class-transformer`
- Dùng `StandardSchemaSerializerInterceptor` khi hình dạng response nên được suy ra từ một schema

#### Config module

`@nestjs/config` chuyển từ validation riêng cho Joi sang [Standard Schema](https://standardschema.dev/). Tùy chọn `validationSchema` giờ chấp nhận bất kỳ schema nào tương thích Standard Schema, như Zod, Valibot hoặc ArkType.

```typescript
import { z } from 'zod';

ConfigModule.forRoot({
  validationSchema: z.object({
    NODE_ENV: z
      .enum(['development', 'production', 'test', 'provision'])
      .default('development'),
    PORT: z.coerce.number().default(3000),
  }),
});
```

Vì validation không còn gắn với một library duy nhất, chúng tôi giờ khuyên dùng một library Standard Schema hiện đại như Zod cho project mới, và [chương Configuration](/application/configuration#schema-validation) đã được viết lại xoay quanh nó.

Các schema Joi hiện có vẫn hoạt động, với hai lưu ý:

- Bạn phải nâng cấp lên **Joi v18 trở lên**, phiên bản hiện thực đặc tả Standard Schema
- Các thiết lập riêng của library trước đây được truyền trực tiếp dưới `validationOptions` giờ chuyển vào `validationOptions.libraryOptions`

```typescript
// Before
validationOptions: {
  allowUnknown: false,
  abortEarly: true,
},

// After
validationOptions: {
  libraryOptions: {
    allowUnknown: false,
    abortEarly: true,
  },
},
```

Với schema Joi, `@nestjs/config` giữ các giá trị mặc định cũ là `allowUnknown: true` và `abortEarly: false`, và merge bất cứ thứ gì bạn truyền vào lên trên chúng.

#### Terminus module

API health indicator cũ, đã bị deprecate từ phiên bản 11, nay đã bị gỡ bỏ. Nếu các health indicator tự viết của bạn vẫn kế thừa `HealthIndicator` hoặc throw `HealthCheckError`, hãy migrate chúng sang `HealthIndicatorService`.

**Cách làm trước đây**

Trước phiên bản 12, một health indicator tự viết có thể báo trạng thái không khỏe bằng cách throw một `HealthCheckError`:

```typescript
@Injectable()
export class DogHealthIndicator extends HealthIndicator {
  constructor(private readonly dogService: DogService) {
    super();
  }

  async isHealthy(key: string) {
    const badboys = await this.dogService.getBadboys();
    const isHealthy = badboys.length === 0;
    const result = this.getStatus(key, isHealthy, { badboys: badboys.length });

    if (!isHealthy) {
      throw new HealthCheckError('Dog check failed', result);
    }

    return result;
  }
}
```

**Cách làm mới (NestJS Terminus v12)**

Ở phiên bản 12, health indicator trả về kết quả trong cả hai trường hợp. Throw không còn là cách để báo trạng thái không khỏe. Indicator hoặc trả về `up()` / `down()` một cách tường minh, hoặc giao thao tác cho `attempt()`, hàm này đánh dấu indicator là `'down'` khi thao tác throw:

```typescript
@Injectable()
export class DogHealthIndicator {
  constructor(
    private readonly dogService: DogService,
    // Inject the `HealthIndicatorService` provided by the `TerminusModule`
    private readonly healthIndicatorService: HealthIndicatorService,
  ) {}

  async isHealthy(key: string) {
    const indicator = this.healthIndicatorService.check(key);
    const badboys = await this.dogService.getBadboys();

    if (badboys.length > 0) {
      // Mark the indicator as "down" and add additional info to the response
      return indicator.down({ badboys: badboys.length });
    }

    // Mark the health indicator as "up"
    return indicator.up();
  }
}
```

Nếu indicator chỉ cần biết một thao tác có thành công hay không (ví dụ dog service có truy cập được không), `attempt()` là cách viết ngắn hơn:

```typescript
isHealthy(key: string) {
  return this.healthIndicatorService
    .check(key)
    .attempt(() => this.dogService.ping())
    .withTimeout(1000);
}
```

Tùy chọn `timeout` của các indicator có sẵn cho database, microservice và gRPC (ví dụ `db.pingCheck('database', {{ '{' }} timeout: 1500 {{ '}' }})`) đã bị deprecate. Hãy nối `.withTimeout(1500)` vào attempt được trả về thay thế. Xem [chương Terminus](/reliability/terminus#timeouts-and-caching) để biết chi tiết.

#### Ngừng khuyến khích webpack trong workflow CLI <a id="webpack-deprecation-in-cli-workflows"></a>

Bản v12 cũng đánh dấu việc chuyển hướng khỏi các workflow CLI xoay quanh webpack. Rspack giờ là bundler mặc định cho monorepo, và các flag CLI `--webpack` / `--webpackPath` (cùng các thuộc tính tương ứng `webpack` / `webpackConfigPath` trong `nest-cli.json`) đã bị deprecate, thay vào đó là `--builder rspack`. Nếu việc sinh project hoặc thiết lập build của bạn dựa vào webpack, hãy lên kế hoạch migrate dần theo thời gian.

CLI cũng thêm `bun` vào danh sách package manager được hỗ trợ, và schematic `decorator` giờ sinh decorator theo dạng `Reflector.createDecorator()`. Schematic `angular` đã bị gỡ bỏ.

#### Lệnh và flag CLI mới <a id="new-cli-commands-and-flags"></a>

CLI có thêm lệnh `deploy`, chuyển tiếp tới [Mau](https://mau.nestjs.com/), và cài `@nestjs/mau` làm dev dependency ở lần dùng đầu tiên:

```bash
$ nest deploy
```

`nest build` và `nest start` cũng có thêm một số tùy chọn mới:

- `--rspackPath [path]`: đường dẫn tới file cấu hình Rspack, tương đương với `--webpackPath` đã bị deprecate
- `--emit-declarations`: phát ra file `.d.ts` khi dùng SWC builder (cũng có dưới dạng `emitDeclarations` trong `nest-cli.json`)
- `--no-type-check`: tắt tường minh việc kiểm tra type của SWC
- `--silent`: ẩn các log thông tin của trình biên dịch

`nest build` cũng hỗ trợ `--parallel [concurrency]`, giúp build các project trong monorepo song song khi kết hợp với `--all`. Ngoài ra, `nest-cli.json` có thêm thuộc tính `includeLibraryAssets` để copy asset của library vào bản build của ứng dụng.

#### Chẩn đoán xung đột route <a id="route-conflict-diagnostics"></a>

Nest đăng ký route theo thứ tự khai báo. Trên các adapter phụ thuộc thứ tự như Express, điều này có nghĩa `@Get(':id')` có thể âm thầm che mất một `@Get('me')` được khai báo sau nó. v12 thêm hai tùy chọn **opt-in** vào `NestApplicationOptions` để xử lý việc này:

```typescript
const app = await NestFactory.create(AppModule, {
  routeConflictPolicy: { duplicate: 'error', shadow: 'warn' },
  routeResolutionStrategy: 'specificity',
});
```

Cả hai mặc định giữ hành vi cũ, nên các ứng dụng hiện có không bị ảnh hưởng trừ khi bạn đặt chúng. Xem [chương Controller](/controllers#route-conflicts-and-resolution-order) để có mô tả đầy đủ.

#### Mã lỗi máy đọc được <a id="machine-readable-error-codes"></a>

`HttpExceptionOptions` chấp nhận một thuộc tính mới `errorCode`. Nó được serialize vào response body, để client có thể rẽ nhánh theo một định danh ổn định thay vì phải parse chuỗi message:

```typescript
throw new BadRequestException('Password is too weak', {
  errorCode: 'WEAK_PASSWORD',
});
```

Xem [Mã lỗi máy đọc được](/exception-filters#machine-readable-error-codes) trong chương Exception filter.

#### Structured logging params

`ConsoleLogger` giờ coi các plain object được truyền sau message là structured params gắn vào cùng một log entry, thay vì ghi chúng ra thành các bản ghi riêng:

```typescript
logger.log('User created', { userId: 1, email: 'foo@bar.com' });
```

Ở JSON mode, chúng được lồng dưới key `params`, hoặc được trải vào object gốc nếu bạn bật `flattenParams`. Hành vi này được bật mặc định trong v12; đặt `structuredParams: false` để khôi phục hành vi cũ. Xem [Structured logging params](/application/logger#structured-logging-params) trong chương Logger.

#### Hỗ trợ observability có sẵn <a id="native-observability-support"></a>

Phiên bản 12 bổ sung hỗ trợ observability đầy đủ thông qua SDK chính thức [`@nestjs/observe`](/observability/overview). Thay vì gắn một APM agent Node.js chung chung vào HTTP server, SDK cắm trực tiếp vào vòng đời request của chính Nest thông qua tùy chọn ứng dụng `instrument`. Nhờ vậy, request, job, lỗi và trace được báo cáo theo đúng các controller, provider, resolver và queue consumer của bạn.

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { createObserveModule } from '@nestjs/observe';

export const { ObserveModule, ObserveInstrument } = createObserveModule();

@Module({
  imports: [ObserveModule.forRoot({ serviceId: 'cats-app' })],
})
export class AppModule {}
```

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule, ObserveInstrument } from './app.module.js';

const app = await NestFactory.create(AppModule, {
  instrument: ObserveInstrument,
});
```

Ở đây không có gì phải migrate: đây là một khả năng mới, opt-in. Xem [chương Observability](/observability/overview) để biết auto-instrumentation bao phủ những gì, và [SDK reference](/observability/sdk) để biết các tùy chọn cấu hình.

#### Các thay đổi đáng chú ý khác trong bản phát hành <a id="other-notable-release-changes"></a>

Tùy vào những package Nest bạn dùng, bạn có thể cũng muốn xem lại các thay đổi sau:

- **Chữ ký transform của pipe** đã được tinh chỉnh để type safety chặt chẽ hơn, và `ArgumentMetadata` giờ nhận một tham số generic. Các pipe tự viết có chữ ký viết tay có thể cần điều chỉnh type.
- **Định dạng lỗi của `ValidationPipe`**: tùy chọn mới `errorFormat` (`'list'` hoặc `'grouped'`) quyết định hình dạng của response lỗi validation.
- **gRPC exception filter**: `GrpcExceptionFilter`, cùng một nhóm exception theo từng status, ánh xạ lỗi sang đúng gRPC status code thay vì `UNKNOWN`. Xem [chương gRPC](/microservices/grpc#exception-handling).
- **Pattern Kafka dạng regex**: `@MessagePattern()` và `@EventPattern()` giờ chấp nhận một `RegExp` trên Kafka transport. Xem [chương Kafka](/microservices/kafka#regular-expression-patterns).
- **WebSocket gateway dạng request-scoped**: gateway giờ hỗ trợ request-scoped provider, với socket có thể inject qua token `REQUEST`. Xem [chương Gateway](/websockets/gateways#request-scoped-gateways).
- **Lý do ngắt kết nối WebSocket**: `handleDisconnect` giờ có thể nhận lý do của việc ngắt kết nối.
- **Pre-request hook cho microservice**: một hook mới chạy trước khi message handler được gọi.
- **Graceful shutdown cho Express**: Express adapter giờ chờ xử lý xong các request đang dở khi shutdown.
- **Ánh xạ lỗi của HTTP adapter** đã được làm lại trên core, Express adapter và Fastify adapter.

Nếu bạn phụ thuộc vào một trong các phần này, hãy kiểm tra hành vi tương ứng bằng bộ test sau khi nâng cấp.

#### Chuyển project sang ESM <a id="switching-your-project-to-esm"></a>

> warning **Tùy chọn** Phần này và phần tiếp theo **không** phải là một phần của việc nâng cấp lên v12, đó là lý do chúng nằm cuối cùng. Một ứng dụng CommonJS chạy trên v12 mà không cần thay đổi gì: `nest upgrade` không đụng tới module format của bạn, và không có gì trong framework bắt bạn phải chuyển. Chỉ đọc tiếp nếu bạn *muốn* chuyển project sang ESM, theo lịch nào phù hợp với bạn.

Việc chuyển đổi thực sự diễn ra trong `package.json`, không phải trong `tsconfig.json`. Hãy thêm field `type` với giá trị `module`:

```json
{
  "name": "my-app",
  "type": "module"
}
```

Chỉ một field đó là đủ để bảo Node.js (và, thông qua `"module": "nodenext"`, cả TypeScript) coi output `.js` của bạn là ESM.

Bạn có cần thay đổi `tsconfig.json` hay không tùy vào project của bạn cũ tới mức nào:

- **Project được sinh bằng CLI v11 gần đây** (`@nestjs/schematics` 11.0.6 trở lên) đã dùng sẵn `"module": "nodenext"` và `"moduleResolution": "nodenext"`. Không cần thay đổi gì trong `tsconfig.json`; thêm `"type": "module"` là đủ.
- **Project được sinh bằng các bản cũ hơn** (v10, hoặc đầu v11) thường vẫn có `"module": "commonjs"` và không có mục `moduleResolution`. Hãy cập nhật cả hai trước khi thêm `"type": "module"`:

```json
{
  "compilerOptions": {
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "resolvePackageJsonExports": true,
    "target": "ES2023"
  }
}
```

Để tham khảo, đây là bộ `compilerOptions` đầy đủ được dùng bởi project ESM mà `nest new` sinh ra:

```json
{
  "compilerOptions": {
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "resolvePackageJsonExports": true,
    "esModuleInterop": true,
    "isolatedModules": true,
    "declaration": true,
    "removeComments": true,
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true,
    "allowSyntheticDefaultImports": true,
    "target": "ES2023",
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": ".",
    "incremental": true,
    "skipLibCheck": true,
    "strict": true,
    "strictPropertyInitialization": false,
    "types": ["vitest/globals", "node"]
  }
}
```

> info **Gợi ý** `nest-cli.json` và `tsconfig.build.json` giống hệt nhau ở cả biến thể project CommonJS và ESM, nên không file nào cần thay đổi. Mục `types` ở trên chỉ khác vì project ESM mặc định dùng Vitest; một project CommonJS dùng Jest sẽ dùng `["node", "jest"]` thay thế.

> warning **Cảnh báo** `"module": "nodenext"` suy ra module format của từng file từ `package.json` gần nhất. Do đó, thêm `"type": "module"` sẽ thay đổi cách **mọi** file `.ts` trong project được emit, và TypeScript bắt đầu báo lỗi thiếu extension trong import như mô tả bên dưới. Hãy chuẩn bị sửa chúng trong cùng một lượt thay vì sửa dần.

#### Chuyển code của bạn sang ESM <a id="moving-your-own-code-to-esm"></a>

Khi đã có cấu hình, hai thứ trong code của bạn thường cần chú ý nhất là các import tương đối và các global chỉ có trong CommonJS.

Import tương đối phải có extension của file:

```typescript
// Before
import { AppModule } from './app.module';

// After
import { AppModule } from './app.module.js';
```

Extension là `.js` dù file nguồn là `.ts`, vì specifier tham chiếu tới file được emit ra.

`__dirname` và `__filename` không tồn tại trong ESM. Hãy dùng `import.meta.dirname` thay thế (hoặc `import.meta.url` cùng `fileURLToPath` trên các phiên bản Node.js cũ hơn):

```typescript
// Before
protoPath: join(__dirname, 'hero/hero.proto'),

// After
protoPath: join(import.meta.dirname, 'hero/hero.proto'),
```

Tương tự, `require()` không có sẵn. Nếu cần nó để tương tác, hãy tạo nó một cách tường minh bằng `createRequire(import.meta.url)` từ `node:module`.

> info **Gợi ý** Nhiều code mẫu trong tài liệu này dùng các quy ước ESM ở trên. Nếu project của bạn vẫn dùng CommonJS, hãy bỏ các extension `.js`, giữ `__dirname`, và gọi `bootstrap()` không có `await`.
