### Mapped type

> warning **Cảnh báo** Chương này chỉ áp dụng cho cách tiếp cận code first.

Khi xây dựng các tính năng như CRUD (Create/Read/Update/Delete), việc dựng các biến thể của một base entity type thường rất hữu ích. Nest cung cấp một số hàm tiện ích thực hiện việc biến đổi type để giúp công việc này thuận tiện hơn.

#### Partial

Khi xây dựng các type dùng để validate input (còn gọi là Data Transfer Object hay DTO), việc dựng các biến thể **create** và **update** trên cùng một type thường rất hữu ích. Ví dụ, biến thể **create** có thể yêu cầu mọi field, trong khi biến thể **update** có thể cho mọi field là tùy chọn.

Nest cung cấp hàm tiện ích `PartialType()` để làm việc này dễ hơn và giảm thiểu boilerplate.

Hàm `PartialType()` trả về một type (class) với mọi thuộc tính của type đầu vào được đặt thành tùy chọn. Ví dụ, giả sử chúng ta có một type **create** như sau:

```typescript
@InputType()
class CreateUserInput {
  @Field()
  email: string;

  @Field()
  password: string;

  @Field()
  firstName: string;
}
```

Mặc định, mọi field này đều là bắt buộc. Để tạo một type có cùng các field, nhưng mỗi field đều là tùy chọn, hãy dùng `PartialType()` và truyền tham chiếu class (`CreateUserInput`) làm tham số:

```typescript
@InputType()
export class UpdateUserInput extends PartialType(CreateUserInput) {}
```

> info **Gợi ý** Hàm `PartialType()` được import từ package `@nestjs/graphql`.

Hàm `PartialType()` nhận một tham số thứ hai tùy chọn: một tham chiếu tới decorator factory. Hãy dùng nó để thay đổi decorator được áp dụng cho class kết quả (class con). Nếu bạn không chỉ định, class con thực chất dùng cùng decorator với class **cha** (class được tham chiếu ở tham số đầu tiên). Trong ví dụ ở trên, chúng ta kế thừa `CreateUserInput`, class được chú thích bằng decorator `@InputType()`. Vì chúng ta muốn `UpdateUserInput` được đối xử như thể nó cũng được gắn `@InputType()`, chúng ta không cần truyền `InputType` làm tham số thứ hai. Nếu type cha và type con khác nhau (ví dụ type cha được gắn `@ObjectType()`), hãy truyền `InputType` làm tham số thứ hai:

```typescript
@InputType()
export class UpdateUserInput extends PartialType(User, InputType) {}
```

Thay vì một decorator factory, bạn có thể truyền một options object làm tham số thứ hai. Nó nhận thuộc tính `decorator`, `omitDefaultValues` (đặt thành `true` để bỏ các giá trị mặc định kế thừa từ các field của cha), và `skipNullProperties` (mặc định là `true`; đặt thành `false` để chỉ bỏ qua validation với giá trị `undefined`, và vẫn validate `null`).

#### Pick

Hàm `PickType()` dựng một type (class) mới bằng cách chọn một tập thuộc tính từ một type đầu vào. Ví dụ, giả sử chúng ta bắt đầu với một type như:

```typescript
@InputType()
class CreateUserInput {
  @Field()
  email: string;

  @Field()
  password: string;

  @Field()
  firstName: string;
}
```

Bạn có thể chọn một tập thuộc tính từ class này bằng hàm tiện ích `PickType()`:

```typescript
@InputType()
export class UpdateEmailInput extends PickType(CreateUserInput, [
  'email',
] as const) {}
```

> info **Gợi ý** Hàm `PickType()` được import từ package `@nestjs/graphql`.

#### Omit

Hàm `OmitType()` dựng một type bằng cách chọn mọi thuộc tính từ một type đầu vào rồi loại bỏ một tập key cụ thể. Ví dụ, giả sử chúng ta bắt đầu với một type như:

```typescript
@InputType()
class CreateUserInput {
  @Field()
  email: string;

  @Field()
  password: string;

  @Field()
  firstName: string;
}
```

Bạn có thể sinh ra một type dẫn xuất có mọi thuộc tính **trừ** `email`, như bên dưới. Ở đây, tham số thứ hai của `OmitType()` là một mảng tên thuộc tính.

```typescript
@InputType()
export class UpdateUserInput extends OmitType(CreateUserInput, [
  'email',
] as const) {}
```

> info **Gợi ý** Hàm `OmitType()` được import từ package `@nestjs/graphql`.

#### Intersection

Hàm `IntersectionType()` kết hợp hai type thành một type (class) mới. Ví dụ, giả sử chúng ta bắt đầu với hai type như:

```typescript
@InputType()
class CreateUserInput {
  @Field()
  email: string;

  @Field()
  password: string;
}

@ObjectType()
export class AdditionalUserInfo {
  @Field()
  firstName: string;

  @Field()
  lastName: string;
}
```

Bạn có thể sinh ra một type mới kết hợp mọi thuộc tính của cả hai type:

```typescript
@InputType()
export class UpdateUserInput extends IntersectionType(
  CreateUserInput,
  AdditionalUserInfo,
) {}
```

> info **Gợi ý** Hàm `IntersectionType()` được import từ package `@nestjs/graphql`.

#### Kết hợp <a id="composition"></a>

Các hàm tiện ích ánh xạ type có thể kết hợp với nhau. Ví dụ, đoạn sau tạo ra một type (class) có mọi thuộc tính của type `CreateUserInput` trừ `email`, với mỗi thuộc tính được đặt thành tùy chọn:

```typescript
@InputType()
export class UpdateUserInput extends PartialType(
  OmitType(CreateUserInput, ['email'] as const),
) {}
```

#### Tự xây dựng <a id="building-your-own"></a>

Các mapped type có sẵn được xây trên hàm `getFieldsAndDecoratorForType()`, hàm mà bạn có thể dùng để tự viết mapped type của mình. Nó trả về các field của một class được chú thích bằng `@ObjectType()`, `@InputType()`, `@InterfaceType()` hoặc `@ArgsType()` (bao gồm cả các field được kế thừa), cùng với class decorator khớp với loại của nó. Ví dụ, helper sau biến mọi field của một type thành một danh sách tùy chọn, rất tiện cho các input dùng để lọc:

```typescript
import { Type } from '@nestjs/common';
import { Field, getFieldsAndDecoratorForType, InputType } from '@nestjs/graphql';

export function FilterType<T>(classRef: Type<T>) {
  const { fields } = getFieldsAndDecoratorForType(classRef);

  @InputType({ isAbstract: true })
  abstract class FilterInput {}

  for (const field of fields) {
    const type = field.typeFn();
    Field(() => [type], { nullable: true })(FilterInput.prototype, field.name);
  }
  return FilterInput as Type<{ [K in keyof T]?: T[K][] }>;
}

@InputType()
export class RecipeFilter extends FilterType(Recipe) {}
```

> warning **Cảnh báo** Metadata của field được trả về được dùng chung với schema builder. Hãy coi nó là chỉ đọc, và truyền bản sao của các tùy chọn (ví dụ `{{ '{' }} ...field.options {{ '}' }}`) cho `@Field()`. Một class không có decorator GraphQL type sẽ khiến `getFieldsAndDecoratorForType()` throw một `UnableToFindFieldsError`.
