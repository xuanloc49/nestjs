### Validation

Hãy validate mọi dữ liệu mà ứng dụng web nhận được trước khi xử lý. Nest cung cấp vài pipe tự động validate request gửi đến:

- `ValidationPipe` validate các class được decorate bằng các quy tắc của [class-validator](https://github.com/typestack/class-validator).
- `StandardSchemaValidationPipe` validate các schema viết bằng [Zod](https://zod.dev/), [Valibot](https://valibot.dev/), [ArkType](https://arktype.io/), hoặc bất kỳ library nào tương thích [Standard Schema](https://standardschema.dev/).
- `ParseIntPipe`, `ParseBoolPipe`, `ParseArrayPipe` và `ParseUUIDPipe` validate và chuyển đổi từng giá trị riêng lẻ.

#### Tổng quan <a id="overview"></a>

Chương [Pipes](/pipes) giải thích cách pipe hoạt động và cách bind chúng vào tham số, route handler, controller, hoặc toàn bộ ứng dụng. Chương này tiếp nối từ đó và trình bày cách dùng hai pipe validation trong thực tế.

Hai pipe khác nhau ở chỗ các quy tắc validation nằm ở đâu:

- Với `ValidationPipe`, quy tắc là các decorator trên một **class DTO**, và class này cũng là type TypeScript của tham số. Cách này tích hợp với các tiện ích [mapped type](#mapped-types) và với Swagger CLI plugin.
- Với `StandardSchemaValidationPipe`, quy tắc là một **schema object**, và type TypeScript của tham số được suy ra từ schema. Schema được kết hợp bằng các method của library tương ứng, không cần đến class hay reflection metadata.

Bạn có thể đăng ký cả hai pipe cùng lúc. `ValidationPipe` chỉ validate các tham số có type là class, còn `StandardSchemaValidationPipe` chỉ validate các tham số có khai báo schema, nên bạn có thể chuyển dần sang schema trong một ứng dụng hiện có.

#### Dùng ValidationPipe có sẵn <a id="using-the-built-in-validationpipe"></a>

Để bắt đầu, trước tiên hãy cài các dependency cần thiết.

```bash
$ npm i --save class-validator class-transformer
```

> info **Gợi ý** `ValidationPipe` được export từ package `@nestjs/common`.

Vì pipe này dùng các library [`class-validator`](https://github.com/typestack/class-validator) và [`class-transformer`](https://github.com/typestack/class-transformer), nó hỗ trợ rất nhiều tùy chọn. Hãy truyền chúng trong một configuration object vào constructor của pipe. Các tùy chọn riêng của pipe là:

```typescript
export interface ValidationPipeOptions extends ValidatorOptions {
  transform?: boolean;
  disableErrorMessages?: boolean;
  exceptionFactory?: (errors: ValidationError[]) => any;
  errorFormat?: 'list' | 'grouped';
}
```

Ngoài ra, mọi tùy chọn của `class-validator` (kế thừa từ interface `ValidatorOptions`) cũng dùng được:

<table>
  <tr>
    <th>Tùy chọn</th>
    <th>Type</th>
    <th>Mô tả</th>
  </tr>
  <tr>
    <td><code>enableDebugMessages</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ in thêm các thông báo cảnh báo ra console khi có gì đó không ổn.</td>
  </tr>
  <tr>
    <td><code>skipUndefinedProperties</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ bỏ qua validation cho mọi thuộc tính có giá trị undefined trong object đang validate.</td>
  </tr>
  <tr>
    <td><code>skipNullProperties</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ bỏ qua validation cho mọi thuộc tính có giá trị null trong object đang validate.</td>
  </tr>
  <tr>
    <td><code>skipMissingProperties</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ bỏ qua validation cho mọi thuộc tính có giá trị null hoặc undefined trong object đang validate.</td>
  </tr>
  <tr>
    <td><code>whitelist</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ loại khỏi object đã validate (object trả về) mọi thuộc tính không dùng decorator validation nào.</td>
  </tr>
  <tr>
    <td><code>forbidNonWhitelisted</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, thay vì loại bỏ các thuộc tính không nằm trong whitelist, validator sẽ throw exception.</td>
  </tr>
  <tr>
    <td><code>forbidUnknownValues</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, mọi nỗ lực validate object không xác định sẽ thất bại ngay lập tức.</td>
  </tr>
  <tr>
    <td><code>disableErrorMessages</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, lỗi validation sẽ không được trả về cho client.</td>
  </tr>
  <tr>
    <td><code>errorHttpStatusCode</code></td>
    <td><code>number</code></td>
    <td>Thiết lập này cho phép bạn chỉ định loại exception sẽ được dùng khi có lỗi. Mặc định nó throw <code>BadRequestException</code>.</td>
  </tr>
  <tr>
    <td><code>exceptionFactory</code></td>
    <td><code>Function</code></td>
    <td>Nhận một mảng lỗi validation và trả về một exception object để throw.</td>
  </tr>
  <tr>
    <td><code>groups</code></td>
    <td><code>string[]</code></td>
    <td>Các group được dùng trong quá trình validate object.</td>
  </tr>
  <tr>
    <td><code>always</code></td>
    <td><code>boolean</code></td>
    <td>Đặt giá trị mặc định cho tùy chọn <code>always</code> của decorator. Giá trị mặc định có thể bị ghi đè trong tùy chọn của decorator.</td>
  </tr>

  <tr>
    <td><code>strictGroups</code></td>
    <td><code>boolean</code></td>
    <td>Nếu <code>groups</code> không được truyền hoặc rỗng, bỏ qua các decorator có ít nhất một group.</td>
  </tr>
  <tr>
    <td><code>dismissDefaultMessages</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validation sẽ không dùng các thông báo mặc định. Thông báo lỗi sẽ luôn là <code>undefined</code>        nếu
      không được đặt tường minh.</td>
  </tr>
  <tr>
    <td><code>validationError.target</code></td>
    <td><code>boolean</code></td>
    <td>Cho biết target có được đưa vào <code>ValidationError</code> hay không.</td>
  </tr>
  <tr>
    <td><code>validationError.value</code></td>
    <td><code>boolean</code></td>
    <td>Cho biết giá trị đã validate có được đưa vào <code>ValidationError</code> hay không.</td>
  </tr>
  <tr>
    <td><code>stopAtFirstError</code></td>
    <td><code>boolean</code></td>
    <td>Khi đặt là true, việc validate một thuộc tính sẽ dừng lại sau khi gặp lỗi đầu tiên. Mặc định là false.</td>
  </tr>
  <tr>
    <td><code>errorFormat</code></td>
    <td><code>'list' | 'grouped'</code></td>
    <td>Chỉ định định dạng của các thông báo lỗi validation. <code>'list'</code> (mặc định) trả về một mảng các chuỗi thông báo lỗi. <code>'grouped'</code> trả về một object với key là đường dẫn thuộc tính và value là mảng các thông báo lỗi nguyên bản, giữ nguyên các thông báo validation tùy chỉnh mà không thêm prefix đường dẫn của cha vào trước.</td>
  </tr>
</table>

> info **Chú ý** Xem thêm thông tin về package `class-validator` trong [repository](https://github.com/typestack/class-validator) của nó.

#### Tự động validation <a id="auto-validation"></a>

Hãy bắt đầu bằng việc bind `ValidationPipe` ở cấp ứng dụng, để mọi endpoint đều được bảo vệ khỏi việc nhận dữ liệu không hợp lệ.

```typescript
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe());
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Để test pipe, hãy tạo một endpoint cơ bản:

```typescript
@Post()
create(@Body() createUserDto: CreateUserDto) {
  return 'This action adds a new user';
}
```

> info **Gợi ý** TypeScript không emit metadata cho **generic hay interface**, nên `ValidationPipe` không thể validate các DTO khai báo bằng chúng. Hãy dùng class cụ thể cho DTO.

> info **Gợi ý** Đừng import DTO bằng type-only import, vì type-only import bị xóa lúc runtime. Hãy viết `import {{ '{' }} CreateUserDto {{ '}' }}` thay vì `import type {{ '{' }} CreateUserDto {{ '}' }}`.

Tiếp theo, thêm các quy tắc validation vào `CreateUserDto` bằng các decorator do package `class-validator` cung cấp (xem [danh sách đầy đủ](https://github.com/typestack/class-validator#validation-decorators)). Khi đó mọi route dùng `CreateUserDto` đều áp dụng các quy tắc này.

```typescript
import { IsEmail, IsNotEmpty } from 'class-validator';

export class CreateUserDto {
  @IsEmail()
  email: string;

  @IsNotEmpty()
  password: string;
}
```

Với các quy tắc này, một request có body chứa thuộc tính `email` không hợp lệ sẽ nhận response `400 Bad Request` với body như sau:

```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": ["email must be an email"]
}
```

`ValidationPipe` cũng validate các phần khác của request. Ví dụ, để chỉ chấp nhận giá trị số cho path parameter `:id`, hãy dùng cách khai báo sau:

```typescript
@Get(':id')
findOne(@Param() params: FindOneParams) {
  return 'This action returns a user';
}
```

Giống như DTO, `FindOneParams` là một class định nghĩa quy tắc validation bằng `class-validator`:

```typescript
import { IsNumberString } from 'class-validator';

export class FindOneParams {
  @IsNumberString()
  id: string;
}
```

#### Tắt lỗi chi tiết <a id="disable-detailed-errors"></a>

Thông báo lỗi giải thích request bị sai ở đâu, nhưng một số môi trường production không muốn để lộ chúng ra. Để tắt lỗi chi tiết, truyền một options object vào `ValidationPipe`:

```typescript
app.useGlobalPipes(
  new ValidationPipe({
    disableErrorMessages: true,
  }),
);
```

Kết quả là body của response không còn chứa thông báo lỗi chi tiết.

#### Loại bỏ thuộc tính <a id="stripping-properties"></a>

`ValidationPipe` cũng có thể lọc bỏ những thuộc tính mà route handler không nên nhận. Khi bạn khai báo **whitelist** các thuộc tính được chấp nhận, mọi thuộc tính không có trong whitelist sẽ bị loại khỏi object kết quả. Ví dụ, nếu handler mong đợi `email` và `password`, nhưng request có thêm thuộc tính `age`, thì `age` sẽ bị loại khỏi DTO kết quả. Để bật hành vi này, đặt `whitelist` thành `true`.

```typescript
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,
  }),
);
```

Khi bật tùy chọn này, các thuộc tính không có decorator nào trong class validation sẽ bị loại bỏ.

Cách khác là bạn có thể từ chối các request chứa thuộc tính không nằm trong whitelist bằng một response lỗi. Để làm vậy, đặt thêm `forbidNonWhitelisted` thành `true` bên cạnh `whitelist`.

<app-banner-courses></app-banner-courses>

#### Chuyển đổi payload object <a id="transform-payload-objects"></a>

Payload đến qua mạng dưới dạng object JavaScript thuần. `ValidationPipe` có thể chuyển chúng thành instance của class DTO tương ứng. Để bật tự động chuyển đổi, đặt `transform` thành `true`. Bạn có thể làm việc này ở cấp method:

```typescript
@@filename(cats.controller)
@Post()
@UsePipes(new ValidationPipe({ transform: true }))
async create(@Body() createCatDto: CreateCatDto) {
  this.catsService.create(createCatDto);
}
```

Để bật hành vi này ở cấp global, đặt tùy chọn trên một global pipe:

```typescript
app.useGlobalPipes(
  new ValidationPipe({
    transform: true,
  }),
);
```

Khi bật tự động chuyển đổi, `ValidationPipe` cũng chuyển đổi các type primitive. Trong ví dụ sau, method `findOne()` nhận path parameter `id` làm tham số:

```typescript
@Get(':id')
findOne(@Param('id') id: number) {
  console.log(typeof id === 'number'); // true
  return 'This action returns a user';
}
```

Path parameter và query parameter luôn đến dưới dạng chuỗi. Vì signature của method khai báo `id` là `number`, `ValidationPipe` sẽ chuyển định danh dạng chuỗi thành số.

#### Chuyển đổi tường minh <a id="explicit-conversion"></a>

Phần trước đã cho thấy `ValidationPipe` ngầm chuyển đổi query parameter và path parameter dựa trên type được khai báo. Việc chuyển đổi đó yêu cầu bật tự động chuyển đổi.

Khi tắt tự động chuyển đổi, bạn có thể chuyển đổi giá trị một cách tường minh bằng `ParseIntPipe` hoặc `ParseBoolPipe`. Không có `ParseStringPipe`, vì path parameter và query parameter vốn đã là chuỗi.

```typescript
@Get(':id')
findOne(
  @Param('id', ParseIntPipe) id: number,
  @Query('sort', ParseBoolPipe) sort: boolean,
) {
  console.log(typeof id === 'number'); // true
  console.log(typeof sort === 'boolean'); // true
  return 'This action returns a user';
}
```

> info **Gợi ý** `ParseIntPipe` và `ParseBoolPipe` được export từ package `@nestjs/common`.

#### Mapped type <a id="mapped-types"></a>

Các tính năng như **CRUD** (Create/Read/Update/Delete) thường cần vài biến thể của một type gốc. Nest cung cấp các hàm tiện ích thực hiện các phép chuyển đổi type này.

> warning **Cảnh báo** Nếu ứng dụng của bạn dùng package `@nestjs/swagger`, xem [chương này](/openapi/mapped-types) để biết thêm về mapped type. Tương tự, nếu bạn dùng package `@nestjs/graphql`, xem [chương này](/graphql/mapped-types). Cả hai package đều dựa nhiều vào type metadata, nên chúng export phiên bản riêng của các tiện ích này. Import chúng từ `@nestjs/mapped-types` thay vì từ `@nestjs/swagger` hoặc `@nestjs/graphql` có thể gây ra các tác dụng phụ không được ghi chép.

Các type validation đầu vào (DTO) thường có biến thể **create** và **update** của cùng một type: biến thể **create** yêu cầu mọi trường, còn biến thể **update** cho chúng là tùy chọn. Các tiện ích mapped type tạo ra những biến thể như vậy mà không phải lặp lại khai báo thuộc tính hay các decorator validation của chúng. Xét type **create** sau:

```typescript
export class CreateCatDto {
  name: string;
  age: number;
  breed: string;
}
```

> info **Gợi ý** `PartialType()`, `PickType()`, `OmitType()` và `IntersectionType()` được import từ package `@nestjs/mapped-types`.

Hàm `PartialType()` trả về một type (class) có mọi thuộc tính của type đầu vào được đặt thành tùy chọn:

```typescript
export class UpdateCatDto extends PartialType(CreateCatDto) {}
```

Hàm `PickType()` tạo một type từ một tập con các thuộc tính của type đầu vào:

```typescript
export class UpdateCatAgeDto extends PickType(CreateCatDto, ['age'] as const) {}
```

Hàm `OmitType()` tạo một type có mọi thuộc tính của type đầu vào, **ngoại trừ** những thuộc tính được liệt kê. Tham số thứ hai là một mảng tên thuộc tính:

```typescript
export class UpdateCatDto extends OmitType(CreateCatDto, ['name'] as const) {}
```

Hàm `IntersectionType()` kết hợp các thuộc tính của hai type thành một type (class) mới. Ví dụ, với một type khác như sau:

```typescript
export class AdditionalCatInfo {
  color: string;
}
```

Type sau chứa thuộc tính của cả hai:

```typescript
export class UpdateCatDto extends IntersectionType(
  CreateCatDto,
  AdditionalCatInfo,
) {}
```

Các hàm tiện ích mapped type có thể kết hợp với nhau. Ví dụ, type sau có mọi thuộc tính của `CreateCatDto` trừ `name`, và tất cả đều là tùy chọn:

```typescript
export class UpdateCatDto extends PartialType(
  OmitType(CreateCatDto, ['name'] as const),
) {}
```

#### Parse và validate mảng <a id="parsing-and-validating-arrays"></a>

TypeScript không emit metadata cho các type generic như mảng, nên `ValidationPipe` không thể validate các phần tử của một tham số mảng. Trong đoạn code sau, các phần tử của `createUserDtos` không được validate:

```typescript
@Post()
createBulk(@Body() createUserDtos: CreateUserDto[]) {
  return 'This action adds new users';
}
```

Để validate mảng, hãy tạo một class riêng với một thuộc tính bọc mảng đó, hoặc dùng `ParseArrayPipe`:

```typescript
@Post()
createBulk(
  @Body(new ParseArrayPipe({ items: CreateUserDto }))
  createUserDtos: CreateUserDto[],
) {
  return 'This action adds new users';
}
```

`ParseArrayPipe` cũng hữu ích để parse query parameter. Xét method `findByIds()` trả về danh sách người dùng dựa trên các định danh truyền trong query string:

```typescript
@Get()
findByIds(
  @Query('ids', new ParseArrayPipe({ items: Number, separator: ',' }))
  ids: number[],
) {
  return 'This action returns users by ids';
}
```

Cách khai báo này parse và validate query parameter của một request như sau:

```bash
GET /?ids=1,2,3
```

#### Validation dựa trên schema <a id="schema-based-validation"></a>

`StandardSchemaValidationPipe` validate giá trị theo schema thay vì theo class được decorate. Nó chấp nhận bất kỳ schema nào implement đặc tả [Standard Schema](https://standardschema.dev/), bao gồm [Zod](https://zod.dev/), [Valibot](https://valibot.dev/) và [ArkType](https://arktype.io/). Schema là nguồn sự thật duy nhất cho một payload: nó validate giá trị lúc runtime, và type suy ra từ nó chính là type TypeScript của tham số handler. Các ví dụ trong phần này dùng Zod.

```bash
$ npm i --save zod
```

Định nghĩa một schema và suy ra type DTO từ nó:

```typescript
@@filename(create-user.dto)
import { z } from 'zod';

export const createUserSchema = z.object({
  email: z.email(),
  password: z.string().min(8),
  displayName: z.string().max(50).optional(),
});

export type CreateUserDto = z.infer<typeof createUserSchema>;
```

Tiếp theo, bind pipe ở cấp ứng dụng:

```typescript
@@filename(main)
import { StandardSchemaValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new StandardSchemaValidationPipe());
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Sau đó gắn schema vào một tham số bằng tùy chọn `schema` của decorator tham số:

```typescript
@@filename(users.controller)
@Post()
create(@Body({ schema: createUserSchema }) createUserDto: CreateUserDto) {
  return this.usersService.create(createUserDto);
}
```

Pipe chỉ validate các tham số có khai báo schema và cho mọi giá trị khác đi qua nguyên vẹn, nên bind nó ở cấp global là an toàn. Nếu body của request không khớp với schema, ứng dụng sẽ trả về `400 Bad Request`. Mỗi thông báo được thêm prefix là đường dẫn của thuộc tính không hợp lệ:

```json
{
  "statusCode": 400,
  "error": "Bad Request",
  "message": [
    "email: Invalid email address",
    "password: Too small: expected string to have >=8 characters"
  ]
}
```

Tùy chọn `schema` được hỗ trợ bởi `@Body()`, `@Query()` và `@Param()`, cũng như `@MessageBody()` trong [gateway](/websockets/gateways) và `@Payload()` trong [microservice](/microservices/basics). Truyền nó làm tham số duy nhất để validate toàn bộ object, hoặc sau tên thuộc tính để validate một giá trị riêng lẻ:

```typescript
@Post('invitations')
invite(@Body('email', { schema: z.email() }) email: string) {
  return this.usersService.invite(email);
}
```

#### Ép kiểu và chuyển đổi <a id="coercion-and-transformation"></a>

Path parameter và query parameter luôn đến dưới dạng chuỗi. Các schema ép kiểu, như `z.coerce.number()`, sẽ chuyển đổi chúng trước khi validate:

```typescript
@Get(':id')
findOne(@Param('id', { schema: z.coerce.number().int().positive() }) id: number) {
  return this.usersService.findOne(id);
}
```

Schema cũng có thể áp dụng giá trị mặc định và các phép chuyển đổi. Schema sau mô tả query string của một danh sách có phân trang:

```typescript
@@filename(list-users-query.dto)
import { z } from 'zod';

export const listUsersQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  search: z.string().trim().optional(),
});

export type ListUsersQuery = z.infer<typeof listUsersQuerySchema>;
```

```typescript
@Get()
findAll(@Query({ schema: listUsersQuerySchema }) query: ListUsersQuery) {
  return this.usersService.findAll(query);
}
```

Với request `GET /users?page=2&search=%20kamil%20`, handler nhận được `page` là số `2`, `limit` là giá trị mặc định `20`, và `search` là chuỗi đã trim `'kamil'`.

Mặc định, pipe truyền **output** của schema cho handler, nên việc ép kiểu, giá trị mặc định và các phép chuyển đổi đều có hiệu lực. Để validate giá trị nhưng vẫn truyền nguyên vẹn đầu vào gốc, đặt `transform` thành `false`. Khi đó, hãy khai báo type của tham số bằng type đầu vào của schema (`z.input<typeof schema>` trong Zod).

#### Thuộc tính không xác định <a id="unknown-properties"></a>

Cách schema xử lý các thuộc tính mà nó không khai báo là do chính schema quyết định, không phải pipe. Trong Zod:

- `z.object()` loại bỏ thuộc tính không xác định, giống tùy chọn `whitelist` của `ValidationPipe`.
- `z.strictObject()` từ chối chúng, giống tùy chọn `forbidNonWhitelisted`. Thông báo lỗi là `Unrecognized key: "age"`.
- `z.looseObject()` giữ lại chúng.

#### Tạo schema dẫn xuất <a id="deriving-schemas"></a>

Các tiện ích [mapped type](#mapped-types) tạo ra class DTO mới từ những class đã có. Với schema, chính các method của library phục vụ cùng mục đích:

```typescript
@@filename(update-user.dto)
import { z } from 'zod';
import { createUserSchema } from './create-user.dto.js';

// All properties optional, like PartialType()
export const updateUserSchema = createUserSchema.partial();

// Only the listed properties, like PickType()
export const changeEmailSchema = createUserSchema.pick({ email: true });

// Every property except the listed ones, like OmitType()
export const publicProfileSchema = createUserSchema.omit({ password: true });

// Additional properties, like IntersectionType()
export const createAdminSchema = createUserSchema.extend({
  role: z.enum(['admin', 'editor']),
});

export type UpdateUserDto = z.infer<typeof updateUserSchema>;
```

Mảng cũng không cần xử lý gì đặc biệt. Bọc schema của phần tử trong `z.array()`, và mọi phần tử đều được validate:

```typescript
@Post('bulk')
createBulk(
  @Body({ schema: z.array(createUserSchema) }) createUserDtos: CreateUserDto[],
) {
  return this.usersService.createMany(createUserDtos);
}
```

Thông báo cho một phần tử không hợp lệ sẽ có prefix là chỉ số của nó, ví dụ `1.email: Invalid email address`.

#### Validate custom decorator <a id="validating-custom-decorators"></a>

Các decorator tham số tạo bằng [`createParamDecorator()`](/custom-decorators) cũng nhận tùy chọn `schema`. Ví dụ, decorator sau lấy định danh tenant từ một header của request:

```typescript
@@filename(tenant-id.decorator)
import { createParamDecorator, ExecutionContext } from '@nestjs/common';

export const TenantId = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) =>
    ctx.switchToHttp().getRequest().headers['x-tenant-id'],
);
```

```typescript
@Get()
findAll(@TenantId({ schema: z.uuid() }) tenantId: string) {
  return this.projectsService.findAll(tenantId);
}
```

Pipe sẽ bỏ qua custom decorator trừ khi bạn bật tùy chọn `validateCustomDecorators`:

```typescript
app.useGlobalPipes(
  new StandardSchemaValidationPipe({
    validateCustomDecorators: true,
  }),
);
```

#### Tùy chọn validation bằng schema <a id="schema-validation-options"></a>

Constructor của `StandardSchemaValidationPipe` nhận các tùy chọn sau:

<table>
  <tr>
    <th>Tùy chọn</th>
    <th>Type</th>
    <th>Mô tả</th>
  </tr>
  <tr>
    <td><code>transform</code></td>
    <td><code>boolean</code></td>
    <td>Nếu là <code>true</code>, handler nhận giá trị do schema tạo ra. Nếu là <code>false</code>, handler nhận đầu vào gốc sau khi validate thành công. Mặc định: <code>true</code>.</td>
  </tr>
  <tr>
    <td><code>validateCustomDecorators</code></td>
    <td><code>boolean</code></td>
    <td>Nếu là <code>true</code>, tham số của các custom decorator tạo bằng <code>createParamDecorator()</code> cũng được validate. Mặc định: <code>false</code>.</td>
  </tr>
  <tr>
    <td><code>validateOptions</code></td>
    <td><code>Record&lt;string, unknown&gt;</code></td>
    <td>Các tùy chọn được chuyển tiếp tới method <code>~standard.validate()</code> của schema, dành cho các library có hỗ trợ.</td>
  </tr>
  <tr>
    <td><code>errorHttpStatusCode</code></td>
    <td><code>number</code></td>
    <td>HTTP status code của exception được throw khi validation thất bại. Mặc định: <code>400</code>.</td>
  </tr>
  <tr>
    <td><code>exceptionFactory</code></td>
    <td><code>Function</code></td>
    <td>Nhận mảng các vấn đề validation và trả về exception cần throw.</td>
  </tr>
</table>

Dùng `exceptionFactory` để thay đổi cấu trúc của response lỗi. Mỗi vấn đề có một `message` và, với giá trị lồng nhau, một `path` gồm các segment là key thuộc tính hoặc object có thuộc tính `key`:

```typescript
app.useGlobalPipes(
  new StandardSchemaValidationPipe({
    exceptionFactory: (issues) =>
      new UnprocessableEntityException({
        message: 'Validation failed',
        errors: issues.map((issue) => ({
          path: issue.path
            ?.map((segment) => (typeof segment === 'object' ? segment.key : segment))
            .join('.'),
          message: issue.message,
        })),
      }),
  }),
);
```

Với factory này, một request không hợp lệ sẽ nhận response `422 Unprocessable Entity`:

```json
{
  "message": "Validation failed",
  "errors": [
    { "path": "email", "message": "Invalid email address" },
    { "path": "password", "message": "Too small: expected string to have >=8 characters" }
  ]
}
```

#### Các library schema khác <a id="other-schema-libraries"></a>

Không có gì trong pipe là đặc thù của Zod. Cùng tùy chọn `schema` đó nhận được schema của Valibot:

```typescript
import * as v from 'valibot';

export const createUserSchema = v.object({
  email: v.pipe(v.string(), v.email()),
  password: v.pipe(v.string(), v.minLength(8)),
});

export type CreateUserDto = v.InferOutput<typeof createUserSchema>;
```

Hoặc schema của ArkType:

```typescript
import { type } from 'arktype';

export const createUserSchema = type({
  email: 'string.email',
  password: 'string >= 8',
});

export type CreateUserDto = typeof createUserSchema.infer;
```

Thông báo lỗi do library tạo ra, nên cách diễn đạt sẽ khác nhau giữa các library.

> info **Gợi ý** Cùng các schema đó có thể dùng để mô tả API của bạn trong tài liệu OpenAPI. Xem [Standard Schema (Zod, Valibot)](/openapi/introduction#standard-schema-zod-valibot) trong chương OpenAPI.

Một ví dụ chạy được có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/35-zod-validation).

#### WebSocket và Microservice <a id="websockets-and-microservices"></a>

Dù chương này dùng các ví dụ với ứng dụng HTTP (ví dụ Express hoặc Fastify), cả `ValidationPipe` và `StandardSchemaValidationPipe` đều hoạt động giống hệt với WebSocket và microservice, bất kể transport là gì. Mặc định, cả hai đều throw một HTTP exception khi validation thất bại. Để báo lỗi theo cách mà transport hiểu được, hãy trả về một `WsException` hoặc `RpcException` từ tùy chọn `exceptionFactory`:

```typescript
new StandardSchemaValidationPipe({
  exceptionFactory: (issues) =>
    new WsException(issues.map((issue) => issue.message)),
});
```

#### Tìm hiểu thêm <a id="learn-more"></a>

Đọc thêm về custom validator, thông báo lỗi và các decorator có sẵn trong repository [class-validator](https://github.com/typestack/class-validator). Với các library schema, xem tài liệu của [Zod](https://zod.dev/), [Valibot](https://valibot.dev/) và [ArkType](https://arktype.io/), cùng danh sách [các library tương thích Standard Schema](https://standardschema.dev/schema#what-schema-libraries-implement-the-spec).
