### Directive

Một directive có thể được gắn vào một field hoặc một lần include fragment, và có thể ảnh hưởng tới việc thực thi query theo bất kỳ cách nào server muốn (xem [directive](https://graphql.org/learn/queries/#directives) trong tài liệu GraphQL). Đặc tả GraphQL cung cấp sẵn một số directive mặc định:

- `@include(if: Boolean)`: chỉ đưa field này vào kết quả nếu argument là `true`
- `@skip(if: Boolean)`: bỏ qua field này nếu argument là `true`
- `@deprecated(reason: String)`: đánh dấu field là deprecated, kèm một message

Một directive là một định danh đứng sau ký tự `@`, có thể theo sau là một danh sách argument có tên. Directive có thể xuất hiện sau gần như mọi thành phần trong ngôn ngữ query và schema của GraphQL.

#### Custom directive <a id="custom-directives"></a>

Để định nghĩa điều gì xảy ra khi Apollo hoặc Mercurius gặp directive của bạn, hãy tạo một hàm transformer. Hàm này dùng hàm `mapSchema` để duyệt qua các vị trí trong schema (định nghĩa field, định nghĩa type, v.v.) và áp dụng các biến đổi tương ứng.

```typescript
import { getDirective, MapperKind, mapSchema } from '@graphql-tools/utils';
import { defaultFieldResolver, GraphQLSchema } from 'graphql';

export function upperDirectiveTransformer(
  schema: GraphQLSchema,
  directiveName: string,
) {
  return mapSchema(schema, {
    [MapperKind.OBJECT_FIELD]: (fieldConfig) => {
      const upperDirective = getDirective(
        schema,
        fieldConfig,
        directiveName,
      )?.[0];

      if (upperDirective) {
        const { resolve = defaultFieldResolver } = fieldConfig;

        // Replace the original resolver with a function that *first* calls
        // the original resolver, then converts its result to upper case
        fieldConfig.resolve = async function (source, args, context, info) {
          const result = await resolve(source, args, context, info);
          if (typeof result === 'string') {
            return result.toUpperCase();
          }
          return result;
        };
        return fieldConfig;
      }
    },
  });
}
```

Tiếp theo, áp dụng hàm `upperDirectiveTransformer` trong method `GraphQLModule#forRoot()` bằng tùy chọn `transformSchema`:

```typescript
GraphQLModule.forRoot({
  // ...
  transformSchema: (schema) => upperDirectiveTransformer(schema, 'upper'),
});
```

Khi đã đăng ký, directive `@upper` có thể được dùng trong schema của bạn. Cách bạn áp dụng directive phụ thuộc vào cách tiếp cận bạn dùng (code first hay schema first).

#### Code first

Với cách tiếp cận code first, hãy dùng decorator `@Directive()` để áp dụng directive:

```typescript
@Directive('@upper')
@Field()
title: string;
```

> info **Gợi ý** Decorator `@Directive()` được export từ package `@nestjs/graphql`.

Directive có thể được áp dụng cho field, field resolver, input type và object type, cũng như query, mutation và subscription. Ví dụ sau áp dụng một directive ở cấp query handler:

```typescript
@Directive('@deprecated(reason: "This query will be removed in the next version")')
@Query(() => Author, { name: 'author' })
async getAuthor(@Args({ name: 'id', type: () => Int }) id: number) {
  return this.authorsService.findOneById(id);
}
```

> warning **Cảnh báo** Các directive được áp dụng qua decorator `@Directive()` không được phản ánh trong file định nghĩa schema được sinh ra.

Cuối cùng, khai báo các directive trong cấu hình `GraphQLModule`:

```typescript
GraphQLModule.forRoot({
  // ...,
  transformSchema: schema => upperDirectiveTransformer(schema, 'upper'),
  buildSchemaOptions: {
    directives: [
      new GraphQLDirective({
        name: 'upper',
        locations: [DirectiveLocation.FIELD_DEFINITION],
      }),
    ],
  },
}),
```

> info **Gợi ý** Cả `GraphQLDirective` và `DirectiveLocation` đều được export từ package `graphql`.

#### Schema first

Với cách tiếp cận schema first, hãy áp dụng directive trực tiếp trong SDL:

```graphql
directive @upper on FIELD_DEFINITION

type Post {
  id: Int!
  title: String! @upper
  votes: Int
}
```
