### Mapped type

Khi xây dựng các tính năng như **CRUD** (Create/Read/Update/Delete), việc dựng các biến thể của một base entity type thường rất hữu ích. Nest cung cấp một số hàm tiện ích thực hiện việc biến đổi type để giúp công việc này thuận tiện hơn.

#### Partial

Khi xây dựng các type dùng để validate input (còn gọi là DTO), việc dựng các biến thể **create** và **update** trên cùng một type thường rất hữu ích. Ví dụ, biến thể **create** có thể yêu cầu mọi field, trong khi biến thể **update** có thể cho mọi field là tùy chọn.

Nest cung cấp hàm tiện ích `PartialType()` để làm việc này dễ hơn và giảm thiểu boilerplate.

Hàm `PartialType()` trả về một type (class) với mọi thuộc tính của type đầu vào được đặt thành tùy chọn. Ví dụ, giả sử bạn có một type **create** như sau:

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

Mặc định, mọi field này đều là bắt buộc. Để tạo một type có cùng các field, nhưng mỗi field đều là tùy chọn, hãy dùng `PartialType()` và truyền tham chiếu class (`CreateCatDto`) làm tham số:

```typescript
export class UpdateCatDto extends PartialType(CreateCatDto) {}
```

> info **Gợi ý** Hàm `PartialType()` được import từ package `@nestjs/swagger`.

#### Pick

Hàm `PickType()` dựng một type (class) mới bằng cách chọn một tập thuộc tính từ một type đầu vào. Ví dụ, giả sử bạn bắt đầu với một type như:

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

Bạn có thể chọn một tập thuộc tính từ class này bằng hàm tiện ích `PickType()`:

```typescript
export class UpdateCatAgeDto extends PickType(CreateCatDto, ['age'] as const) {}
```

> info **Gợi ý** Hàm `PickType()` được import từ package `@nestjs/swagger`.

#### Omit

Hàm `OmitType()` dựng một type bằng cách chọn mọi thuộc tính từ một type đầu vào rồi loại bỏ một tập key cụ thể. Ví dụ, giả sử bạn bắt đầu với một type như:

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

Bạn có thể sinh ra một type dẫn xuất có mọi thuộc tính **trừ** `name`, như bên dưới. Trong cấu trúc này, tham số thứ hai của `OmitType()` là một mảng tên thuộc tính.

```typescript
export class UpdateCatDto extends OmitType(CreateCatDto, ['name'] as const) {}
```

> info **Gợi ý** Hàm `OmitType()` được import từ package `@nestjs/swagger`.

#### Intersection

Hàm `IntersectionType()` kết hợp hai hoặc nhiều type thành một type (class) mới. Ví dụ, giả sử bạn bắt đầu với hai type như:

```typescript
import { ApiProperty } from '@nestjs/swagger';

export class CreateCatDto {
  @ApiProperty()
  name: string;

  @ApiProperty()
  breed: string;
}

export class AdditionalCatInfo {
  @ApiProperty()
  color: string;
}
```

Bạn có thể sinh ra một type mới kết hợp mọi thuộc tính của cả hai type:

```typescript
export class UpdateCatDto extends IntersectionType(
  CreateCatDto,
  AdditionalCatInfo,
) {}
```

> info **Gợi ý** Hàm `IntersectionType()` được import từ package `@nestjs/swagger`.

#### Kết hợp <a id="composition"></a>

Các hàm tiện ích ánh xạ type có thể kết hợp với nhau. Ví dụ, đoạn sau tạo ra một type (class) có mọi thuộc tính của type `CreateCatDto` trừ `name`, với các thuộc tính đó được đặt thành tùy chọn:

```typescript
export class UpdateCatDto extends PartialType(
  OmitType(CreateCatDto, ['name'] as const),
) {}
```
