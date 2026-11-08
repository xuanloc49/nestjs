### Interface

Như nhiều hệ thống type khác, GraphQL hỗ trợ interface. Một **interface** là một type trừu tượng định nghĩa một tập các field mà một type phải có để implement interface đó (xem [interface](https://graphql.org/learn/schema/#interfaces) trong tài liệu GraphQL).

#### Code first

Với cách tiếp cận code first, bạn định nghĩa một GraphQL interface bằng cách tạo một abstract class được chú thích bằng decorator `@InterfaceType()`, được export từ package `@nestjs/graphql`.

```typescript
import { Field, ID, InterfaceType } from '@nestjs/graphql';

@InterfaceType()
export abstract class Character {
  @Field(() => ID)
  id: string;

  @Field()
  name: string;
}
```

> warning **Cảnh báo** Không thể dùng interface của TypeScript để định nghĩa GraphQL interface.

Nó sinh ra phần sau của GraphQL schema bằng SDL:

```graphql
interface Character {
  id: ID!
  name: String!
}
```

Để implement interface `Character`, hãy dùng key `implements`:

```typescript
@ObjectType({
  implements: () => [Character],
})
export class Human implements Character {
  id: string;
  name: string;
}
```

> info **Gợi ý** Decorator `@ObjectType()` được export từ package `@nestjs/graphql`.

Hàm `resolveType()` mặc định do library sinh ra xác định type dựa trên giá trị trả về từ method resolver. Điều này có nghĩa là bạn phải trả về instance của class, chứ không phải object literal JavaScript thuần.

Để cung cấp một hàm `resolveType()` tùy chỉnh, hãy truyền thuộc tính `resolveType` trong options object của decorator `@InterfaceType()`:

```typescript
@InterfaceType({
  resolveType(book) {
    if (book.colors) {
      return ColoringBook;
    }
    return TextBook;
  },
})
export abstract class Book {
  @Field(() => ID)
  id: string;

  @Field()
  title: string;
}
```

#### Interface resolver <a id="interface-resolvers"></a>

Cho tới giờ, interface chỉ cho phép bạn dùng chung định nghĩa field với các object. Để dùng chung cả phần hiện thực field resolver, hãy tạo một interface resolver riêng:

```typescript
import { Args, Info, Parent, ResolveField, Resolver } from '@nestjs/graphql';

@Resolver((type) => Character) // Reminder: Character is an interface
export class CharacterInterfaceResolver {
  @ResolveField(() => [Character])
  friends(
    @Parent() character, // Resolved object that implements Character
    @Info() { parentType }, // Type of the object that implements Character
    @Args('search', { type: () => String }) searchTerm: string,
  ) {
    // Get character's friends
    return [];
  }
}
```

Field resolver `friends` giờ được tự động đăng ký cho mọi object type implement interface `Character`.

> warning **Cảnh báo** Việc này yêu cầu đặt thuộc tính `inheritResolversFromInterfaces` thành `true` trong cấu hình `GraphQLModule`.

#### Schema first

Để định nghĩa một interface theo cách tiếp cận schema first, hãy tạo một GraphQL interface bằng SDL:

```graphql
interface Character {
  id: ID!
  name: String!
}
```

Sau đó, bạn có thể dùng tính năng sinh typing (như trong chương [Bắt đầu nhanh với GraphQL](/graphql/quick-start)) để sinh các định nghĩa TypeScript tương ứng:

```typescript
export interface Character {
  id: string;
  name: string;
}
```

Interface cần thêm một field `__resolveType` trong resolver map để xác định interface resolve ra type nào. Hãy tạo một class `CharactersResolver` và định nghĩa method `__resolveType`, method này trả về tên của type cụ thể:

```typescript
@Resolver('Character')
export class CharactersResolver {
  @ResolveField()
  __resolveType(value) {
    if ('age' in value) {
      return 'Person';
    }
    return null;
  }
}
```

> info **Gợi ý** Mọi decorator đều được export từ package `@nestjs/graphql`.
