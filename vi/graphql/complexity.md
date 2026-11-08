### Độ phức tạp

> warning **Cảnh báo** Chương này chỉ áp dụng cho cách tiếp cận code first.

Query complexity cho phép bạn định nghĩa mức độ phức tạp của các field nhất định, và giới hạn query bằng một **độ phức tạp tối đa**. Ý tưởng là biểu diễn độ phức tạp của mỗi field bằng một con số. Một mặc định phổ biến là cho mỗi field độ phức tạp `1`. Bạn cũng có thể tùy chỉnh cách tính độ phức tạp của một GraphQL query bằng các complexity estimator. Một complexity estimator là một hàm tính độ phức tạp của một field. Bạn có thể thêm bao nhiêu estimator tùy thích vào rule, và chúng chạy lần lượt. Estimator đầu tiên trả về một giá trị số sẽ quyết định độ phức tạp của field đó.

Package `@nestjs/graphql` tích hợp với các công cụ như [graphql-query-complexity](https://github.com/slicknode/graphql-query-complexity), công cụ cung cấp giải pháp dựa trên phân tích chi phí. Với library này, bạn có thể từ chối các query quá tốn kém để thực thi.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài dependency cần thiết:

```bash
$ npm install --save graphql-query-complexity
```

#### Bắt đầu <a id="getting-started"></a>

Khi đã cài đặt xong, hãy định nghĩa class `ComplexityPlugin`:

```typescript
import { GraphQLSchemaHost } from '@nestjs/graphql';
import { Plugin } from '@nestjs/apollo';
import {
  ApolloServerPlugin,
  BaseContext,
  GraphQLRequestListener,
} from '@apollo/server';
import { GraphQLError } from 'graphql';
import {
  fieldExtensionsEstimator,
  getComplexity,
  simpleEstimator,
} from 'graphql-query-complexity';

@Plugin()
export class ComplexityPlugin implements ApolloServerPlugin {
  constructor(private gqlSchemaHost: GraphQLSchemaHost) {}

  async requestDidStart(): Promise<GraphQLRequestListener<BaseContext>> {
    const maxComplexity = 20;
    const { schema } = this.gqlSchemaHost;

    return {
      async didResolveOperation({ request, document }) {
        const complexity = getComplexity({
          schema,
          operationName: request.operationName,
          query: document,
          variables: request.variables,
          estimators: [
            fieldExtensionsEstimator(),
            simpleEstimator({ defaultComplexity: 1 }),
          ],
        });
        if (complexity > maxComplexity) {
          throw new GraphQLError(
            `Query is too complex: ${complexity}. Maximum allowed complexity: ${maxComplexity}`,
          );
        }
        console.log('Query Complexity:', complexity);
      },
    };
  }
}
```

Để minh họa, độ phức tạp tối đa cho phép được đặt là `20`. Ví dụ ở trên dùng hai estimator, `fieldExtensionsEstimator` và `simpleEstimator`:

- `fieldExtensionsEstimator`: lấy giá trị độ phức tạp được định nghĩa cho mỗi field trong schema của bạn (qua `extensions` của field)
- `simpleEstimator`: trả về một độ phức tạp cố định cho mỗi field (dùng làm fallback cho các field không có độ phức tạp được định nghĩa)

> info **Gợi ý** Nhớ thêm class này vào mảng `providers` của một module.

#### Độ phức tạp ở cấp field <a id="field-level-complexity"></a>

Khi đã có plugin này, bạn có thể định nghĩa độ phức tạp của bất kỳ field nào bằng cách chỉ định thuộc tính `complexity` trong options object được truyền cho decorator `@Field()`:

```typescript
@Field({ complexity: 3 })
title: string;
```

Ngoài ra, bạn có thể định nghĩa một hàm estimator:

```typescript
@Field({ complexity: (options: ComplexityEstimatorArgs) => ... })
title: string;
```

#### Độ phức tạp ở cấp Query/Mutation <a id="querymutation-level-complexity"></a>

Decorator `@Query()` và `@Mutation()` cũng nhận thuộc tính `complexity` trong options object của chúng:

```typescript
@Query(() => [Item], {
  complexity: (options: ComplexityEstimatorArgs) =>
    options.args.count * options.childComplexity,
})
items(@Args('count') count: number) {
  return this.itemsService.getItems({ count });
}
```
