### Sinh SDL

> warning **Cảnh báo** Chương này chỉ áp dụng cho cách tiếp cận code first.

Để sinh một GraphQL SDL schema thủ công (tức là không cần chạy ứng dụng, kết nối database, nối các resolver, v.v.), hãy dùng `GraphQLSchemaBuilderModule`:

```typescript
async function generateSchema() {
  const app = await NestFactory.create(GraphQLSchemaBuilderModule);
  await app.init();

  const gqlSchemaFactory = app.get(GraphQLSchemaFactory);
  const schema = await gqlSchemaFactory.create([RecipesResolver]);
  console.log(printSchema(schema));
}
```

> info **Gợi ý** `GraphQLSchemaBuilderModule` và `GraphQLSchemaFactory` được import từ package `@nestjs/graphql`. Hàm `printSchema` được import từ package `graphql`.

#### Cách dùng <a id="usage"></a>

Method `gqlSchemaFactory.create()` nhận một mảng tham chiếu tới các class resolver. Ví dụ:

```typescript
const schema = await gqlSchemaFactory.create([
  RecipesResolver,
  AuthorsResolver,
  PostsResolver,
]);
```

Nó cũng nhận một tham số thứ hai tùy chọn là một mảng các class scalar:

```typescript
const schema = await gqlSchemaFactory.create(
  [RecipesResolver, AuthorsResolver, PostsResolver],
  [DurationScalar, DateScalar],
);
```

Cuối cùng, bạn có thể truyền một options object (chính là `BuildSchemaOptions` mà thuộc tính `buildSchemaOptions` trong cấu hình `GraphQLModule` nhận):

```typescript
const schema = await gqlSchemaFactory.create([RecipesResolver], {
  skipCheck: true,
  orphanedTypes: [],
});
```

- `skipCheck`: bỏ qua việc validate schema; boolean, mặc định là `false`
- `orphanedTypes`: một mảng các class cần được sinh ra dù chúng không được tham chiếu tường minh (tức không phải là một phần của object graph). Thông thường, một class được khai báo nhưng không được tham chiếu ở đâu trong graph sẽ bị bỏ qua.

#### Federation

`GraphQLSchemaFactory` dựng một GraphQL schema thuần: nó không biết gì về Apollo Federation. Để lấy SDL của một subgraph [federated](/graphql/federation) theo code first (ví dụ để truyền cho `rover subgraph check` hoặc `rover supergraph compose`), hãy in nó bằng `printSubgraphSchema` từ `@apollo/subgraph` thay vì `printSchema`, để các directive như `@key`, `@shareable` hay `@external` được giữ lại:

```typescript
import { printSubgraphSchema } from '@apollo/subgraph';

async function generateSchema() {
  const app = await NestFactory.create(GraphQLSchemaBuilderModule);
  await app.init();

  const gqlSchemaFactory = app.get(GraphQLSchemaFactory);
  const schema = await gqlSchemaFactory.create([UsersResolver], {
    orphanedTypes: [User],
  });
  console.log(printSubgraphSchema(schema));
}
```

Với Federation 2, SDL được in ra cũng phải liên kết tới đặc tả federation, nếu không nó sẽ bị coi là một subgraph Federation 1. Hãy tự thêm `@link` vào đầu, import mọi federation directive mà các type của bạn dùng:

```typescript
const sdl = `extend schema @link(url: "https://specs.apollo.dev/federation/v2.14", import: ["@key", "@shareable", "@external"])

${printSubgraphSchema(schema)}`;
```

> info **Gợi ý** Các entity type chỉ được tham chiếu qua `_entities` (ví dụ các stub `@extends` được resolve bằng `@ResolveReference()`) không thể truy cập được từ các root type, nên hãy truyền chúng trong `orphanedTypes`. Nếu không, schema sẽ được sinh ra mà không có chúng.
