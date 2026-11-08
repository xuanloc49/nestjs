### Union

Union type tương tự interface, nhưng chúng không chỉ định field chung nào giữa các type (xem [union type](https://graphql.org/learn/schema/#union-types) trong tài liệu GraphQL). Union hữu ích khi cần trả về các kiểu dữ liệu tách biệt nhau từ một field duy nhất.

#### Code first

Để định nghĩa một GraphQL union type, trước tiên hãy định nghĩa các class tạo nên union. Theo [ví dụ union type](https://www.apollographql.com/docs/apollo-server/schema/unions-interfaces/#union-type) trong tài liệu Apollo, chúng ta sẽ tạo hai class. Đầu tiên là `Book`:

```typescript
import { Field, ObjectType } from '@nestjs/graphql';

@ObjectType()
export class Book {
  @Field()
  title: string;
}
```

Và sau đó là `Author`:

```typescript
import { Field, ObjectType } from '@nestjs/graphql';

@ObjectType()
export class Author {
  @Field()
  name: string;
}
```

Khi đã có các class này, hãy đăng ký union `ResultUnion` bằng hàm `createUnionType` được export từ package `@nestjs/graphql`:

```typescript
export const ResultUnion = createUnionType({
  name: 'ResultUnion',
  types: () => [Author, Book] as const,
});
```

> warning **Cảnh báo** Hãy thêm một const assertion (`as const`) vào mảng được trả về bởi thuộc tính `types` của hàm `createUnionType`. Thiếu nó, TypeScript sẽ sinh ra một file khai báo sai lúc biên dịch, và việc dùng union từ một project khác sẽ thất bại với một lỗi.

Giờ bạn có thể tham chiếu tới `ResultUnion` trong một query:

```typescript
@Query(() => [ResultUnion])
search(): Array<typeof ResultUnion> {
  return [new Author(), new Book()];
}
```

Nó sinh ra phần sau của GraphQL schema bằng SDL:

```graphql
type Author {
  name: String!
}

type Book {
  title: String!
}

union ResultUnion = Author | Book

type Query {
  search: [ResultUnion!]!
}
```

Hàm `resolveType()` mặc định do library sinh ra xác định type dựa trên giá trị trả về từ method resolver. Điều này có nghĩa là bạn phải trả về instance của class, chứ không phải object literal JavaScript thuần.

Để cung cấp một hàm `resolveType()` tùy chỉnh, hãy truyền thuộc tính `resolveType` trong options object của hàm `createUnionType()`:

```typescript
export const ResultUnion = createUnionType({
  name: 'ResultUnion',
  types: () => [Author, Book] as const,
  resolveType(value) {
    if (value.name) {
      return Author;
    }
    if (value.title) {
      return Book;
    }
    return null;
  },
});
```

#### Schema first

Để định nghĩa một union theo cách tiếp cận schema first, hãy tạo một GraphQL union bằng SDL:

```graphql
type Author {
  name: String!
}

type Book {
  title: String!
}

union ResultUnion = Author | Book
```

Sau đó, bạn có thể dùng tính năng sinh typing (như trong chương [Bắt đầu nhanh với GraphQL](/graphql/quick-start)) để sinh các định nghĩa TypeScript tương ứng:

```typescript
export class Author {
  name: string;
}

export class Book {
  title: string;
}

export type ResultUnion = Author | Book;
```

Union cần thêm một field `__resolveType` trong resolver map để xác định union resolve ra type nào. Hãy tạo một class `ResultUnionResolver` và định nghĩa method `__resolveType`, method này trả về tên của type cụ thể. Nhớ đăng ký `ResultUnionResolver` làm provider trong một module.

```typescript
@Resolver('ResultUnion')
export class ResultUnionResolver {
  @ResolveField()
  __resolveType(value) {
    if (value.name) {
      return 'Author';
    }
    if (value.title) {
      return 'Book';
    }
    return null;
  }
}
```

> info **Gợi ý** Mọi decorator đều được export từ package `@nestjs/graphql`.

### Enum <a id="enums"></a>

Enumeration type là một loại scalar đặc biệt bị giới hạn trong một tập giá trị được phép cụ thể (xem [enumeration type](https://graphql.org/learn/schema/#enumeration-types) trong tài liệu GraphQL). Chúng cho phép bạn:

- validate rằng mọi argument thuộc type này là một trong các giá trị được phép
- truyền đạt qua hệ thống type rằng một field sẽ luôn là một trong một tập hữu hạn các giá trị

#### Code first

Với cách tiếp cận code first, bạn định nghĩa một GraphQL enum type bằng cách tạo một enum TypeScript:

```typescript
export enum AllowedColor {
  RED,
  GREEN,
  BLUE,
}
```

Khi đã có enum này, hãy đăng ký enum `AllowedColor` bằng hàm `registerEnumType` được export từ package `@nestjs/graphql`:

```typescript
registerEnumType(AllowedColor, {
  name: 'AllowedColor',
});
```

Giờ bạn có thể tham chiếu tới `AllowedColor` trong các type của mình:

```typescript
@Field(type => AllowedColor)
favoriteColor: AllowedColor;
```

Nó sinh ra phần sau của GraphQL schema bằng SDL:

```graphql
enum AllowedColor {
  RED
  GREEN
  BLUE
}
```

Để cung cấp mô tả cho enum, hãy truyền thuộc tính `description` cho hàm `registerEnumType()`:

```typescript
registerEnumType(AllowedColor, {
  name: 'AllowedColor',
  description: 'The supported colors.',
});
```

Để cung cấp mô tả cho các giá trị của enum, hoặc đánh dấu một giá trị là deprecated, hãy truyền thuộc tính `valuesMap`:

```typescript
registerEnumType(AllowedColor, {
  name: 'AllowedColor',
  description: 'The supported colors.',
  valuesMap: {
    RED: {
      description: 'The default color.',
    },
    BLUE: {
      deprecationReason: 'Too blue.',
    },
  },
});
```

Nó sinh ra GraphQL schema sau bằng SDL:

```graphql
"""
The supported colors.
"""
enum AllowedColor {
  """
  The default color.
  """
  RED
  GREEN
  BLUE @deprecated(reason: "Too blue.")
}
```

#### Schema first

Để định nghĩa một enum theo cách tiếp cận schema first, hãy tạo một GraphQL enum bằng SDL:

```graphql
enum AllowedColor {
  RED
  GREEN
  BLUE
}
```

Sau đó bạn có thể dùng tính năng sinh typing (như trong chương [Bắt đầu nhanh với GraphQL](/graphql/quick-start)) để sinh các định nghĩa TypeScript tương ứng:

```typescript
export enum AllowedColor {
  RED = "RED",
  GREEN = "GREEN",
  BLUE = "BLUE"
}
```

Đôi khi một backend dùng một giá trị nội bộ cho enum khác với giá trị được đưa ra trong API công khai. Trong ví dụ này, API chứa `RED`, nhưng resolver dùng `#f00` thay vào đó (xem [giá trị nội bộ](https://www.apollographql.com/docs/apollo-server/schema/scalars-enums/#internal-values) trong tài liệu Apollo). Để làm được điều này, hãy khai báo một resolver object cho enum `AllowedColor`:

```typescript
export const allowedColorResolver: Partial<Record<keyof typeof AllowedColor, any>> = {
  RED: '#f00',
};
```

> info **Gợi ý** Mọi decorator đều được export từ package `@nestjs/graphql`.

Sau đó truyền resolver object này trong thuộc tính `resolvers` của method `GraphQLModule#forRoot()`:

```typescript
GraphQLModule.forRoot({
  resolvers: {
    AllowedColor: allowedColorResolver,
  },
});
```
