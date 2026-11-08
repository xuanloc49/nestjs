### Type và parameter

`SwaggerModule` tìm mọi decorator `@Body()`, `@Query()`, `@Param()` và `@Headers()` trong các route handler để sinh tài liệu API. Nó cũng dùng reflection để tạo các định nghĩa model tương ứng. Xét đoạn code sau:

```typescript
@Post()
async create(@Body() createCatDto: CreateCatDto) {
  this.catsService.create(createCatDto);
}
```

> info **Gợi ý** Để đặt định nghĩa body một cách tường minh, hãy dùng decorator `@ApiBody()` (được import từ package `@nestjs/swagger`).

Dựa trên `CreateCatDto`, Swagger UI hiển thị định nghĩa model sau:

<figure><img src="/assets/swagger-dto.png" /></figure>

Định nghĩa trống trơn, dù class có khai báo vài thuộc tính. Để các thuộc tính của class hiện ra với `SwaggerModule`, hãy chú thích chúng bằng decorator `@ApiProperty()` hoặc dùng [CLI plugin](/openapi/cli-plugin), plugin này làm việc đó tự động:

```typescript
import { ApiProperty } from '@nestjs/swagger';

export class CreateCatDto {
  @ApiProperty()
  name: string;

  @ApiProperty()
  age: number;

  @ApiProperty()
  breed: string;
}
```

> info **Gợi ý** Thay vì tự chú thích từng thuộc tính, hãy cân nhắc dùng [Swagger plugin](/openapi/cli-plugin), plugin này thêm các chú thích này cho bạn.

Mở trình duyệt và kiểm tra model `CreateCatDto` được sinh ra:

<figure><img src="/assets/swagger-dto2.png" /></figure>

Decorator `@ApiProperty()` cũng cho phép bạn đặt nhiều thuộc tính của [Schema Object](https://swagger.io/specification/#schemaObject):

```typescript
@ApiProperty({
  description: 'The age of a cat',
  minimum: 1,
  default: 1,
})
age: number;
```

> info **Gợi ý** Thay vì gõ tường minh `{{"@ApiProperty({ required: false })"}}`, bạn có thể dùng decorator viết tắt `@ApiPropertyOptional()`.

Để đặt type của thuộc tính một cách tường minh, hãy dùng key `type`:

```typescript
@ApiProperty({
  type: Number,
})
age: number;
```

#### Mảng <a id="arrays"></a>

Khi thuộc tính là một mảng, bạn phải tự chỉ ra kiểu mảng, như bên dưới:

```typescript
@ApiProperty({ type: [String] })
names: string[];
```

> info **Gợi ý** Hãy cân nhắc dùng [Swagger plugin](/openapi/cli-plugin), plugin này tự động phát hiện mảng.

Hoặc truyền type làm phần tử đầu tiên của một mảng (như ở trên) hoặc đặt thuộc tính `isArray` thành `true`.

<app-banner-enterprise></app-banner-enterprise>

#### Phụ thuộc vòng tròn <a id="circular-dependencies"></a>

Khi bạn có phụ thuộc vòng tròn giữa các class, hãy dùng một lazy function để cung cấp thông tin type cho `SwaggerModule`:

```typescript
@ApiProperty({ type: () => Node })
node: Node;
```

> info **Gợi ý** Hãy cân nhắc dùng [Swagger plugin](/openapi/cli-plugin), plugin này tự động phát hiện phụ thuộc vòng tròn.

#### Generic và interface <a id="generics-and-interfaces"></a>

TypeScript không lưu metadata về generic hay interface, nên khi bạn dùng chúng trong DTO, `SwaggerModule` có thể không sinh được định nghĩa model đúng lúc runtime. Chẳng hạn, module Swagger không thể đọc đúng đoạn code sau:

```typescript
createBulk(@Body() usersDto: CreateUserDto[])
```

Để vượt qua hạn chế này, hãy đặt type một cách tường minh:

```typescript
@ApiBody({ type: [CreateUserDto] })
createBulk(@Body() usersDto: CreateUserDto[])
```

#### Enum <a id="enums"></a>

Để xác định một `enum`, hãy đặt thuộc tính `enum` của `@ApiProperty()` thành một mảng giá trị:

```typescript
@ApiProperty({ enum: ['Admin', 'Moderator', 'User']})
role: UserRole;
```

Ngoài ra, hãy định nghĩa một enum TypeScript thực sự như sau:

```typescript
export enum UserRole {
  Admin = 'Admin',
  Moderator = 'Moderator',
  User = 'User',
}
```

Sau đó bạn có thể dùng trực tiếp enum với parameter decorator `@Query()`, kết hợp với decorator `@ApiQuery()`:

```typescript
@ApiQuery({ name: 'role', enum: UserRole })
async filterByRole(@Query('role') role: UserRole = UserRole.User) {}
```

<figure><img src="/assets/enum_query.gif" /></figure>

Khi `isArray` được đặt thành `true`, các giá trị của `enum` có thể được chọn trong một ô **chọn nhiều**:

<figure><img src="/assets/enum_query_array.gif" /></figure>

#### Schema của enum <a id="enums-schema"></a>

Mặc định, thuộc tính `enum` thêm một định nghĩa [enum](https://swagger.io/docs/specification/data-models/enums/) thô vào `parameter`:

```yaml
- breed:
    type: 'string'
    enum:
      - Persian
      - Tabby
      - Siamese
```

Đặc tả này dùng được trong hầu hết các trường hợp. Tuy nhiên, nếu bạn dùng một công cụ nhận đặc tả làm **input** và sinh code **phía client**, code được sinh ra có thể chứa các `enums` bị trùng lặp. Xét đoạn code sau:

```typescript
// generated client-side code
export class CatDetail {
  breed: CatDetailEnum;
}

export class CatInformation {
  breed: CatInformationEnum;
}

export enum CatDetailEnum {
  Persian = 'Persian',
  Tabby = 'Tabby',
  Siamese = 'Siamese',
}

export enum CatInformationEnum {
  Persian = 'Persian',
  Tabby = 'Tabby',
  Siamese = 'Siamese',
}
```

> info **Gợi ý** Đoạn code ở trên được sinh ra bằng một công cụ tên [NSwag](https://github.com/RicoSuter/NSwag).

Kết quả chứa hai `enums` giống hệt nhau. Để giải quyết vấn đề này, hãy truyền một `enumName` cùng với thuộc tính `enum` trong decorator:

```typescript
export class CatDetail {
  @ApiProperty({ enum: CatBreed, enumName: 'CatBreed' })
  breed: CatBreed;
}
```

Thuộc tính `enumName` khiến `@nestjs/swagger` biến `CatBreed` thành một `schema` riêng, giúp enum `CatBreed` có thể tái sử dụng. Đặc tả trông như sau:

```yaml
CatDetail:
  type: 'object'
  properties:
    ...
    - breed:
        schema:
          $ref: '#/components/schemas/CatBreed'
CatBreed:
  type: string
  enum:
    - Persian
    - Tabby
    - Siamese
```

> info **Gợi ý** Các decorator `@ApiQuery()` và `@ApiParam()` cũng nhận `enumName` bên cạnh `enum`.

#### Ví dụ giá trị của thuộc tính <a id="property-value-examples"></a>

Để đặt một ví dụ duy nhất cho một thuộc tính, hãy dùng key `example`:

```typescript
@ApiProperty({
  example: 'persian',
})
breed: string;
```

Để cung cấp nhiều ví dụ, hãy dùng key `examples` và truyền một object có cấu trúc như thế này:

```typescript
@ApiProperty({
  examples: {
    Persian: { value: 'persian' },
    Tabby: { value: 'tabby' },
    Siamese: { value: 'siamese' },
    'Scottish Fold': { value: 'scottish_fold' },
  },
})
breed: string;
```

#### Định nghĩa thô <a id="raw-definitions"></a>

Trong một số trường hợp, như mảng hoặc ma trận lồng sâu, bạn có thể cần tự định nghĩa type:

```typescript
@ApiProperty({
  type: 'array',
  items: {
    type: 'array',
    items: {
      type: 'number',
    },
  },
})
coords: number[][];
```

Bạn cũng có thể chỉ định schema object thô:

```typescript
@ApiProperty({
  type: 'object',
  properties: {
    name: {
      type: 'string',
      example: 'Error'
    },
    status: {
      type: 'number',
      example: 400
    }
  },
  required: ['name', 'status']
})
rawDefinition: Record<string, any>;
```

Để tự định nghĩa nội dung input/output trong các class controller, hãy dùng thuộc tính `schema`:

```typescript
@ApiBody({
  schema: {
    type: 'array',
    items: {
      type: 'array',
      items: {
        type: 'number',
      },
    },
  },
})
async create(@Body() coords: number[][]) {}
```

#### Model bổ sung <a id="extra-models"></a>

Để định nghĩa các model bổ sung mà controller không tham chiếu trực tiếp nhưng module Swagger cần đọc, hãy dùng decorator `@ApiExtraModels()`:

```typescript
@ApiExtraModels(ExtraModel)
export class CreateCatDto {}
```

> info **Gợi ý** Bạn chỉ cần dùng `@ApiExtraModels()` một lần cho một class model cụ thể.

Ngoài ra, hãy truyền một options object có thuộc tính `extraModels` cho method `SwaggerModule.createDocument()`:

```typescript
const documentFactory = () =>
  SwaggerModule.createDocument(app, options, {
    extraModels: [ExtraModel],
  });
```

Để lấy một tham chiếu (`$ref`) tới model, hãy dùng hàm `getSchemaPath(ExtraModel)`:

```typescript
'application/vnd.api+json': {
   schema: { $ref: getSchemaPath(ExtraModel) },
},
```

#### oneOf, anyOf, allOf

Để kết hợp các schema, hãy dùng các từ khóa `oneOf`, `anyOf` hoặc `allOf` (xem [oneOf, anyOf, allOf, not](https://swagger.io/docs/specification/data-models/oneof-anyof-allof-not/) trong tài liệu Swagger):

```typescript
@ApiProperty({
  oneOf: [
    { $ref: getSchemaPath(Cat) },
    { $ref: getSchemaPath(Dog) },
  ],
})
pet: Cat | Dog;
```

Để định nghĩa một mảng đa hình (tức là một mảng có các phần tử thuộc nhiều schema), hãy dùng một định nghĩa thô (xem ở trên) để tự định nghĩa type:

```typescript
type Pet = Cat | Dog;

@ApiProperty({
  type: 'array',
  items: {
    oneOf: [
      { $ref: getSchemaPath(Cat) },
      { $ref: getSchemaPath(Dog) },
    ],
  },
})
pets: Pet[];
```

> info **Gợi ý** Hàm `getSchemaPath()` được import từ `@nestjs/swagger`.

Cả `Cat` và `Dog` đều phải được định nghĩa là model bổ sung bằng decorator `@ApiExtraModels()` (ở cấp class).

#### Tên và mô tả của schema <a id="schema-name-and-description"></a>

Tên của schema được sinh ra dựa trên tên của class model gốc (ví dụ, model `CreateCatDto` sinh ra schema `CreateCatDto`). Để đổi tên schema, hãy dùng decorator `@ApiSchema()`:

```typescript
@ApiSchema({ name: 'CreateCatRequest' })
class CreateCatDto {}
```

Model ở trên được chuyển thành schema `CreateCatRequest`.

Mặc định, schema được sinh ra không có mô tả. Để thêm mô tả, hãy dùng thuộc tính `description`:

```typescript
@ApiSchema({ description: 'Description of the CreateCatDto schema' })
class CreateCatDto {}
```

Khi đó mô tả được đưa vào schema:

```yaml
schemas:
  CreateCatDto:
    type: object
    description: Description of the CreateCatDto schema
```
