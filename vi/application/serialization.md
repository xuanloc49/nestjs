### Serialization

Serialization diễn ra trước khi object được trả về trong network response. Đây là nơi thích hợp để định nghĩa các quy tắc chuyển đổi và làm sạch dữ liệu gửi về client. Ví dụ, dữ liệu nhạy cảm như mật khẩu phải luôn bị loại khỏi response, và một số thuộc tính có thể cần chuyển đổi thêm, như chỉ trả về một tập con các thuộc tính của entity. Tự làm các phép chuyển đổi này trong từng handler vừa tốn công vừa dễ sai, và khó đảm bảo mọi trường hợp đều được xử lý.

#### Tổng quan <a id="overview"></a>

Nest cung cấp sẵn hai interceptor áp dụng các quy tắc này theo kiểu khai báo:

- `ClassSerializerInterceptor` dùng package [class-transformer](https://github.com/typestack/class-transformer). Nó lấy giá trị do route handler trả về và áp dụng hàm `instanceToPlain()` lên đó, hàm này tuân theo các decorator `class-transformer` khai báo trên class entity hoặc DTO. Phần đầu của chương này trình bày cách tiếp cận này.

- `StandardSchemaSerializerInterceptor` validate và chuyển đổi response bằng một schema viết bằng [Zod](https://zod.dev/), [Valibot](https://valibot.dev/), [ArkType](https://arktype.io/), hoặc bất kỳ library nào tương thích [Standard Schema](https://standardschema.dev/). Xem [Serialization dựa trên schema](#schema-based-serialization).

> info **Gợi ý** Cả hai interceptor đều không serialize response dạng [StreamableFile](/http/file-upload#streaming-files).

#### Loại bỏ thuộc tính <a id="exclude-properties"></a>

Giả sử bạn muốn loại thuộc tính `password` của entity người dùng khỏi mọi response. Hãy đánh dấu entity như sau:

```typescript
import { Exclude } from 'class-transformer';

export class UserEntity {
  id: number;
  firstName: string;
  lastName: string;

  @Exclude()
  password: string;

  constructor(partial: Partial<UserEntity>) {
    Object.assign(this, partial);
  }
}
```

Giờ xét một controller có route handler trả về instance của class này:

```typescript
@UseInterceptors(ClassSerializerInterceptor)
@Get()
findOne(): UserEntity {
  return new UserEntity({
    id: 1,
    firstName: 'John',
    lastName: 'Doe',
    password: 'password',
  });
}
```

> warning **Cảnh báo** Handler phải trả về một instance của class. Một object JavaScript thuần, như `{{ '{' }} user: new UserEntity() {{ '}' }}`, sẽ không được serialize đúng. Để serialize object thuần, xem [Chuyển đổi object thuần](#transform-plain-objects).

> info **Gợi ý** `ClassSerializerInterceptor` được import từ `@nestjs/common`.

Khi endpoint này được gọi, client nhận được response sau:

```json
{
  "id": 1,
  "firstName": "John",
  "lastName": "Doe"
}
```

Interceptor cũng có thể được bind cho toàn ứng dụng (xem [Bind interceptor](/interceptors#binding-interceptors)). Kết hợp interceptor với khai báo class entity giúp đảm bảo **mọi** route handler trả về `UserEntity` đều bỏ đi thuộc tính `password`, áp dụng quy tắc này tại một chỗ duy nhất.

#### Expose thuộc tính <a id="expose-properties"></a>

Dùng decorator `@Expose()` để đặt tên alias cho thuộc tính, hoặc để tính giá trị thuộc tính bằng một hàm (tương tự **getter**), như bên dưới.

```typescript
@Expose()
get fullName(): string {
  return `${this.firstName} ${this.lastName}`;
}
```

#### Transform

Dùng decorator `@Transform()` để chuyển đổi dữ liệu thêm. Ví dụ, cách khai báo sau trả về thuộc tính `name` của `RoleEntity` thay vì toàn bộ object.

```typescript
@Transform(({ value }) => value.name)
role: RoleEntity;
```

#### Truyền tùy chọn <a id="pass-options"></a>

Để ghi đè hành vi mặc định của các hàm chuyển đổi, hãy truyền tùy chọn vào decorator `@SerializeOptions()`.

```typescript
@SerializeOptions({
  excludePrefixes: ['_'],
})
@Get()
findOne(): UserEntity {
  return new UserEntity();
}
```

> info **Gợi ý** Decorator `@SerializeOptions()` được import từ `@nestjs/common`.

Các tùy chọn truyền vào `@SerializeOptions()` được chuyển tiếp làm tham số thứ hai của hàm `instanceToPlain()` bên dưới. Trong ví dụ này, mọi thuộc tính bắt đầu bằng prefix `_` đều bị loại bỏ.

#### Chuyển đổi object thuần <a id="transform-plain-objects"></a>

Tùy chọn `type` của `@SerializeOptions()` chuyển response thành instance của class được chỉ định trước khi serialize, nên các decorator `class-transformer` của class vẫn được áp dụng kể cả khi handler trả về object thuần. Nhờ đó bạn không cần khởi tạo class hay gọi `plainToInstance()` trong từng handler.

Trong ví dụ dưới đây, cả hai nhánh điều kiện đều trả về object JavaScript thuần, và chúng được chuyển thành instance `UserEntity` với các decorator tương ứng được áp dụng:

```typescript
@UseInterceptors(ClassSerializerInterceptor)
@SerializeOptions({ type: UserEntity })
@Get()
findOne(@Query('id', ParseIntPipe) id: number): UserEntity {
  if (id === 1) {
    return {
      id: 1,
      firstName: 'John',
      lastName: 'Doe',
      password: 'password',
    };
  }

  return {
    id: 2,
    firstName: 'Kamil',
    lastName: 'Mysliwiec',
    password: 'password2',
  };
}
```

> info **Gợi ý** Khai báo type trả về của handler giúp TypeScript kiểm tra object thuần trả về có khớp với cấu trúc của DTO hoặc entity hay không. Hàm `plainToInstance()` không có kiểm tra type này, nên một object sai cấu trúc có thể lọt qua mà không ai để ý.

> warning **Cảnh báo** Response được định hình bởi class `type`, không phải bởi class của giá trị trả về. Một giá trị không phải instance của class `type`, như instance của một entity khác, sẽ được chuyển đổi như một object thuần: các decorator trong class của chính nó, như `@Exclude()`, bị bỏ qua, và các thuộc tính mà class `type` không khai báo sẽ được copy nguyên vẹn. Để chỉ gửi các thuộc tính của class `type`, hãy decorate từng thuộc tính bằng `@Expose()` và thêm `excludeExtraneousValues: true` vào tùy chọn của cùng decorator `@SerializeOptions()` đó.


#### Serialization dựa trên schema <a id="schema-based-serialization"></a>

`StandardSchemaSerializerInterceptor` định hình response bằng schema thay vì decorator trên class. Schema mô tả chính xác những gì được đưa ra khỏi API: interceptor cho giá trị do route handler trả về chạy qua schema và gửi output của schema về client. Nó chấp nhận bất kỳ schema nào implement đặc tả [Standard Schema](https://standardschema.dev/). Các ví dụ trong phần này dùng Zod.

Vì `z.object()` loại bỏ các thuộc tính mà schema không khai báo, một response schema cũng đồng thời là một allowlist. Schema sau đảm bảo `password` của người dùng không bao giờ bị gửi đi, kể cả khi service trả về toàn bộ dòng dữ liệu trong database:

```typescript
@@filename(user-response.schema)
import { z } from 'zod';

export const userResponseSchema = z.object({
  id: z.number(),
  firstName: z.string(),
  lastName: z.string(),
});

export type UserResponse = z.infer<typeof userResponseSchema>;
```

Bind interceptor và chọn schema bằng tùy chọn `schema` của decorator `@SerializeOptions()`:

```typescript
@@filename(users.controller)
import {
  Controller,
  Get,
  Param,
  ParseIntPipe,
  SerializeOptions,
  StandardSchemaSerializerInterceptor,
  UseInterceptors,
} from '@nestjs/common';
import { userResponseSchema } from './user-response.schema.js';
import { UsersService } from './users.service.js';

@Controller('users')
@UseInterceptors(StandardSchemaSerializerInterceptor)
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get(':id')
  @SerializeOptions({ schema: userResponseSchema })
  findOne(@Param('id', ParseIntPipe) id: number) {
    return this.usersService.findOne(id);
  }

  @Get()
  @SerializeOptions({ schema: userResponseSchema })
  findAll() {
    return this.usersService.findAll();
  }
}
```

Service trả về các bản ghi người dùng có kèm thuộc tính `password`, nhưng client chỉ nhận được các thuộc tính đã khai báo:

```json
{
  "id": 1,
  "firstName": "John",
  "lastName": "Doe"
}
```

Khi handler trả về một mảng, như `findAll()`, interceptor áp dụng schema cho **từng phần tử**. Hãy truyền schema của một phần tử, không phải schema mảng.

Response là `null`, `undefined`, giá trị primitive và `StreamableFile` được gửi đi nguyên vẹn, cũng như response của các handler không có schema.

#### Chuyển đổi response bằng schema <a id="transforming-responses-with-schemas"></a>

Các phép chuyển đổi của schema làm được những gì `@Expose()` và `@Transform()` làm cho class. Schema sau thêm một thuộc tính tính toán `fullName` và thay object lồng `role` bằng tên của nó:

```typescript
@@filename(user-response.schema)
import { z } from 'zod';

export const userResponseSchema = z
  .object({
    id: z.number(),
    firstName: z.string(),
    lastName: z.string(),
    role: z.object({ id: z.number(), name: z.string() }),
  })
  .transform((user) => ({
    id: user.id,
    fullName: `${user.firstName} ${user.lastName}`,
    role: user.role.name,
  }));
```

Với một người dùng có role `admin`, client nhận được:

```json
{
  "id": 1,
  "fullName": "John Doe",
  "role": "admin"
}
```

Cùng schema đó viết bằng Valibot dùng `v.pipe()` và `v.transform()`:

```typescript
import * as v from 'valibot';

export const userResponseSchema = v.pipe(
  v.object({
    id: v.number(),
    firstName: v.string(),
    lastName: v.string(),
    role: v.object({ id: v.number(), name: v.string() }),
  }),
  v.transform((user) => ({
    id: user.id,
    fullName: `${user.firstName} ${user.lastName}`,
    role: user.role.name,
  })),
);
```

#### Bind schema serializer <a id="binding-the-schema-serializer"></a>

`@SerializeOptions()` có thể decorate cả class controller lẫn route handler. Schema đặt trên class áp dụng cho mọi handler của nó, và schema đặt trên handler sẽ được ưu tiên:

```typescript
@Controller('users')
@UseInterceptors(StandardSchemaSerializerInterceptor)
@SerializeOptions({ schema: userResponseSchema })
export class UsersController {}
```

Để bind interceptor cho toàn ứng dụng, hãy truyền vào nó instance `Reflector`, thứ mà interceptor dùng để đọc metadata của `@SerializeOptions()`:

```typescript
@@filename(main)
const app = await NestFactory.create(AppModule);
app.useGlobalInterceptors(
  new StandardSchemaSerializerInterceptor(app.get(Reflector)),
);
```

Cách khác là đăng ký nó bằng token `APP_INTERCEPTOR`, như mô tả trong [Bind interceptor](/interceptors#binding-interceptors), và Nest sẽ tự inject `Reflector` giúp bạn. Các handler không có schema không bị ảnh hưởng bởi global interceptor.

Constructor của interceptor cũng nhận các tùy chọn mặc định, áp dụng khi cả handler lẫn controller của nó đều không đặt schema:

<table>
  <tr>
    <td><code>schema</code></td>
    <td>Schema mặc định được dùng khi <code>@SerializeOptions()</code> không cung cấp schema.</td>
  </tr>
  <tr>
    <td><code>validateOptions</code></td>
    <td>Các tùy chọn được chuyển tiếp tới method <code>~standard.validate()</code> của schema, dành cho các library có hỗ trợ. Handler có thể ghi đè chúng bằng tùy chọn <code>validateOptions</code> của <code>@SerializeOptions()</code>.</td>
  </tr>
</table>

#### Lỗi serialization <a id="serialization-errors"></a>

Một response không khớp với schema của nó, như một bản ghi thiếu thuộc tính hoặc sai type, cho thấy có bug ở phía server, không phải lỗi của request. Khi đó, interceptor throw một lỗi liệt kê các vấn đề của schema, và client nhận response `500 Internal Server Error` thay vì dữ liệu được serialize dở dang. Thông báo lỗi, kèm các vấn đề, được exception filter mặc định ghi log.

Một ví dụ chạy được dùng Valibot có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/36-valibot-serializer).

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được của `ClassSerializerInterceptor` có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/21-serializer).

#### WebSocket và Microservice <a id="websockets-and-microservices"></a>

Dù chương này dùng các ví dụ với ứng dụng HTTP (ví dụ Express hoặc Fastify), cả `ClassSerializerInterceptor` lẫn `StandardSchemaSerializerInterceptor` đều hoạt động giống hệt với WebSocket và microservice, bất kể transport là gì.

#### Tìm hiểu thêm <a id="learn-more"></a>

Đọc thêm về các decorator và tùy chọn có sẵn trong repository [class-transformer](https://github.com/typestack/class-transformer). Với các library schema, xem tài liệu của [Zod](https://zod.dev/), [Valibot](https://valibot.dev/) và [ArkType](https://arktype.io/).
