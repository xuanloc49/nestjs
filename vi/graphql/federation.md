### Federation

Federation cho phép bạn tách một GraphQL server nguyên khối thành các microservice độc lập. Nó gồm hai thành phần: một gateway và một hoặc nhiều microservice được federate. Mỗi microservice giữ một phần của schema, và gateway gộp các schema thành một schema duy nhất mà client sử dụng.

Như mô tả trong [bài giới thiệu về federation của Apollo](https://blog.apollographql.com/apollo-federation-f260cf525d21), federation được thiết kế xoay quanh các nguyên tắc cốt lõi sau:

- Việc xây dựng một graph nên mang tính **khai báo.** Với federation, bạn kết hợp một graph một cách khai báo ngay từ bên trong schema thay vì viết code ghép schema (schema stitching) theo kiểu mệnh lệnh.
- Code nên được tách theo **mối quan tâm (concern)**, không phải theo type. Thường không có team nào kiểm soát mọi khía cạnh của một type quan trọng như User hay Product, nên định nghĩa của các type này nên được phân tán giữa các team và codebase, thay vì tập trung một chỗ.
- Graph nên đơn giản để client sử dụng. Cùng nhau, các service được federate có thể tạo thành một graph hoàn chỉnh, tập trung vào sản phẩm, phản ánh chính xác cách nó được sử dụng ở phía client.
- Nó chỉ là **GraphQL**, chỉ dùng các tính năng tuân thủ đặc tả của ngôn ngữ. Bất kỳ ngôn ngữ nào, không chỉ JavaScript, đều có thể hiện thực federation.

> info **Gợi ý** Các subgraph được xây bằng `ApolloFederationDriver` hoặc `MercuriusFederationDriver` hỗ trợ subscription (với tùy chọn `subscriptions` cho Apollo, hoặc `subscription: true` cho Mercurius). Apollo Gateway (`ApolloGatewayDriver`) không chuyển tiếp subscription tới các subgraph, nên để đưa chúng ra qua một federated endpoint duy nhất, hãy dùng một router hỗ trợ federated subscription, như Apollo Router, hoặc Mercurius gateway (đặt `subscription: true` trên gateway và `wsUrl` cho mỗi service).

Trong các phần tiếp theo, chúng ta sẽ thiết lập một ứng dụng demo gồm một gateway và hai federated endpoint: service Users và service Posts.

#### Federation với Apollo <a id="federation-with-apollo"></a>

Bắt đầu bằng việc cài các dependency cần thiết:

```bash
$ npm install --save @apollo/subgraph
```

#### Schema first

Service Users cung cấp một schema đơn giản. Directive `@key` cho Apollo query planner biết rằng một instance cụ thể của `User` có thể được lấy theo `id` của nó. Cũng lưu ý rằng schema mở rộng type `Query`.

```graphql
type User @key(fields: "id") {
  id: ID!
  name: String!
}

extend type Query {
  getUser(id: ID!): User
}
```

Resolver cung cấp thêm một method tên `resolveReference()`. Apollo gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

```typescript
import { Args, Query, Resolver, ResolveReference } from '@nestjs/graphql';
import { UsersService } from './users.service.js';

@Resolver('User')
export class UsersResolver {
  constructor(private usersService: UsersService) {}

  @Query()
  getUser(@Args('id') id: string) {
    return this.usersService.findById(id);
  }

  @ResolveReference()
  resolveReference(reference: { __typename: string; id: string }) {
    return this.usersService.findById(reference.id);
  }
}
```

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `ApolloFederationDriver` trong configuration object:

```typescript
import {
  ApolloFederationDriver,
  ApolloFederationDriverConfig,
} from '@nestjs/apollo';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { UsersResolver } from './users.resolver.js';

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloFederationDriverConfig>({
      driver: ApolloFederationDriver,
      typePaths: ['**/*.graphql'],
    }),
  ],
  providers: [UsersResolver],
})
export class AppModule {}
```

#### Code first

Bắt đầu bằng việc thêm một số decorator vào entity `User`:

```ts
import { Directive, Field, ID, ObjectType } from '@nestjs/graphql';

@ObjectType()
@Directive('@key(fields: "id")')
export class User {
  @Field(() => ID)
  id: number;

  @Field()
  name: string;
}
```

Resolver cung cấp thêm một method tên `resolveReference()`. Apollo gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

```ts
import { Args, Query, Resolver, ResolveReference } from '@nestjs/graphql';
import { User } from './user.entity.js';
import { UsersService } from './users.service.js';

@Resolver(() => User)
export class UsersResolver {
  constructor(private usersService: UsersService) {}

  @Query(() => User)
  getUser(@Args('id') id: number): User {
    return this.usersService.findById(id);
  }

  @ResolveReference()
  resolveReference(reference: { __typename: string; id: number }): User {
    return this.usersService.findById(reference.id);
  }
}
```

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `ApolloFederationDriver` trong configuration object:

```typescript
import {
  ApolloFederationDriver,
  ApolloFederationDriverConfig,
} from '@nestjs/apollo';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { UsersResolver } from './users.resolver.js';
import { UsersService } from './users.service.js'; // Not included in this example

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloFederationDriverConfig>({
      driver: ApolloFederationDriver,
      autoSchemaFile: true,
    }),
  ],
  providers: [UsersResolver, UsersService],
})
export class AppModule {}
```

Có sẵn các ví dụ chạy được cho cách tiếp cận [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/users-application) và [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/users-application).

#### Ví dụ federation: Posts <a id="federated-example-posts"></a>

Service Posts phục vụ các bài viết được tổng hợp qua query `getPosts`, đồng thời mở rộng type `User` với một field `user.posts`.

#### Schema first

Service Posts tham chiếu tới type `User` trong schema của nó bằng cách đánh dấu nó với từ khóa `extend`. Nó cũng khai báo thêm một field trên type `User` (`posts`). Lưu ý directive `@key`, dùng để khớp các instance `User`, và directive `@external`, cho biết field `id` được quản lý ở nơi khác.

```graphql
type Post @key(fields: "id") {
  id: ID!
  title: String!
  body: String!
  user: User
}

extend type User @key(fields: "id") {
  id: ID! @external
  posts: [Post]
}

extend type Query {
  getPosts: [Post]
}
```

Trong ví dụ sau, `PostsResolver` cung cấp một method `getUser()` trả về một tham chiếu chứa `__typename` cùng mọi thuộc tính bổ sung mà ứng dụng của bạn cần để resolve tham chiếu, trong trường hợp này là `id`. Gateway dùng `__typename` để xác định chính xác microservice chịu trách nhiệm cho type `User` và lấy instance tương ứng. Để resolve tham chiếu, gateway gửi một request tới service Users mô tả ở trên, service này thực thi method `resolveReference()` của nó.

```typescript
import { Query, Resolver, Parent, ResolveField } from '@nestjs/graphql';
import { PostsService } from './posts.service.js';
import type { Post } from './posts.interfaces.js';

@Resolver('Post')
export class PostsResolver {
  constructor(private postsService: PostsService) {}

  @Query('getPosts')
  getPosts() {
    return this.postsService.findAll();
  }

  @ResolveField('user')
  getUser(@Parent() post: Post) {
    return { __typename: 'User', id: post.userId };
  }
}
```

Cuối cùng, đăng ký `GraphQLModule`, như trong service Users.

```typescript
import {
  ApolloFederationDriver,
  ApolloFederationDriverConfig,
} from '@nestjs/apollo';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { PostsResolver } from './posts.resolver.js';

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloFederationDriverConfig>({
      driver: ApolloFederationDriver,
      typePaths: ['**/*.graphql'],
    }),
  ],
  providers: [PostsResolver],
})
export class AppModule {}
```

#### Code first

Đầu tiên, khai báo một class đại diện cho entity `User`. Dù bản thân entity nằm ở một service khác, service này vẫn dùng nó (và mở rộng định nghĩa của nó). Lưu ý các directive `@extends` và `@external`.

```ts
import { Directive, ObjectType, Field, ID } from '@nestjs/graphql';
import { Post } from './post.entity.js';

@ObjectType()
@Directive('@extends')
@Directive('@key(fields: "id")')
export class User {
  @Field(() => ID)
  @Directive('@external')
  id: number;

  @Field(() => [Post])
  posts?: Post[];
}
```

Tiếp theo, tạo resolver cho phần mở rộng của entity `User`:

```ts
import { Parent, ResolveField, Resolver } from '@nestjs/graphql';
import { PostsService } from './posts.service.js';
import { Post } from './post.entity.js';
import { User } from './user.entity.js';

@Resolver(() => User)
export class UsersResolver {
  constructor(private readonly postsService: PostsService) {}

  @ResolveField(() => [Post])
  public posts(@Parent() user: User): Post[] {
    return this.postsService.forAuthor(user.id);
  }
}
```

Sau đó định nghĩa class entity `Post`:

```ts
import { Directive, Field, ID, Int, ObjectType } from '@nestjs/graphql';
import { User } from './user.entity.js';

@ObjectType()
@Directive('@key(fields: "id")')
export class Post {
  @Field(() => ID)
  id: number;

  @Field()
  title: string;

  @Field(() => Int)
  authorId: number;

  @Field(() => User)
  user?: User;
}
```

Và resolver của nó:

```ts
import { Query, Args, ResolveField, Resolver, Parent } from '@nestjs/graphql';
import { PostsService } from './posts.service.js';
import { Post } from './post.entity.js';
import { User } from './user.entity.js';

@Resolver(() => Post)
export class PostsResolver {
  constructor(private readonly postsService: PostsService) {}

  @Query(() => Post)
  findPost(@Args('id') id: number): Post {
    return this.postsService.findOne(id);
  }

  @Query(() => [Post])
  getPosts(): Post[] {
    return this.postsService.all();
  }

  @ResolveField(() => User)
  user(@Parent() post: Post): any {
    return { __typename: 'User', id: post.authorId };
  }
}
```

Cuối cùng, gắn mọi thứ lại với nhau trong một module. Lưu ý các tùy chọn build schema, chỉ định rằng `User` là một orphaned type (type bên ngoài).

```ts
import {
  ApolloFederationDriver,
  ApolloFederationDriverConfig,
} from '@nestjs/apollo';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { User } from './user.entity.js';
import { PostsResolver } from './posts.resolver.js';
import { UsersResolver } from './users.resolver.js';
import { PostsService } from './posts.service.js'; // Not included in this example

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloFederationDriverConfig>({
      driver: ApolloFederationDriver,
      autoSchemaFile: true,
      buildSchemaOptions: {
        orphanedTypes: [User],
      },
    }),
  ],
  providers: [PostsResolver, UsersResolver, PostsService],
})
export class AppModule {}
```

Có sẵn các ví dụ chạy được cho cách tiếp cận [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/posts-application) và [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/posts-application).

#### Ví dụ federation: Gateway <a id="federated-example-gateway"></a>

Bắt đầu bằng việc cài dependency cần thiết:

```bash
$ npm install --save @apollo/gateway
```

Gateway cần một danh sách endpoint, và nó tự động khám phá các schema tương ứng. Vì vậy, phần hiện thực gateway giống nhau cho cả cách tiếp cận code first lẫn schema first.

```typescript
import { IntrospectAndCompose } from '@apollo/gateway';
import { ApolloGatewayDriver, ApolloGatewayDriverConfig } from '@nestjs/apollo';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloGatewayDriverConfig>({
      driver: ApolloGatewayDriver,
      server: {
        // ... Apollo Server options
      },
      gateway: {
        supergraphSdl: new IntrospectAndCompose({
          subgraphs: [
            { name: 'users', url: 'http://user-service/graphql' },
            { name: 'posts', url: 'http://post-service/graphql' },
          ],
        }),
      },
    }),
  ],
})
export class AppModule {}
```

Có sẵn các ví dụ chạy được cho cách tiếp cận [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/gateway) và [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/gateway).

#### Federation với Mercurius <a id="federation-with-mercurius"></a>

Bắt đầu bằng việc cài các dependency cần thiết:

```bash
$ npm install --save @apollo/subgraph @nestjs/mercurius
```

> info **Lưu ý** Package `@apollo/subgraph` là bắt buộc để xây dựng một subgraph schema (các hàm `buildSubgraphSchema` và `printSubgraphSchema`).

#### Schema first

Service Users cung cấp một schema đơn giản. Directive `@key` cho Mercurius query planner biết rằng một instance cụ thể của `User` có thể được lấy theo `id` của nó. Cũng lưu ý rằng schema mở rộng type `Query`.

```graphql
type User @key(fields: "id") {
  id: ID!
  name: String!
}

extend type Query {
  getUser(id: ID!): User
}
```

Resolver cung cấp thêm một method tên `resolveReference()`. Mercurius gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

```typescript
import { Args, Query, Resolver, ResolveReference } from '@nestjs/graphql';
import { UsersService } from './users.service.js';

@Resolver('User')
export class UsersResolver {
  constructor(private usersService: UsersService) {}

  @Query()
  getUser(@Args('id') id: string) {
    return this.usersService.findById(id);
  }

  @ResolveReference()
  resolveReference(reference: { __typename: string; id: string }) {
    return this.usersService.findById(reference.id);
  }
}
```

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `MercuriusFederationDriver` trong configuration object:

```typescript
import {
  MercuriusFederationDriver,
  MercuriusFederationDriverConfig,
} from '@nestjs/mercurius';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { UsersResolver } from './users.resolver.js';

@Module({
  imports: [
    GraphQLModule.forRoot<MercuriusFederationDriverConfig>({
      driver: MercuriusFederationDriver,
      typePaths: ['**/*.graphql'],
    }),
  ],
  providers: [UsersResolver],
})
export class AppModule {}
```

#### Code first

Bắt đầu bằng việc thêm một số decorator vào entity `User`:

```ts
import { Directive, Field, ID, ObjectType } from '@nestjs/graphql';

@ObjectType()
@Directive('@key(fields: "id")')
export class User {
  @Field(() => ID)
  id: number;

  @Field()
  name: string;
}
```

Resolver cung cấp thêm một method tên `resolveReference()`. Mercurius gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

```ts
import { Args, Query, Resolver, ResolveReference } from '@nestjs/graphql';
import { User } from './user.entity.js';
import { UsersService } from './users.service.js';

@Resolver(() => User)
export class UsersResolver {
  constructor(private usersService: UsersService) {}

  @Query(() => User)
  getUser(@Args('id') id: number): User {
    return this.usersService.findById(id);
  }

  @ResolveReference()
  resolveReference(reference: { __typename: string; id: number }): User {
    return this.usersService.findById(reference.id);
  }
}
```

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `MercuriusFederationDriver` trong configuration object:

```typescript
import {
  MercuriusFederationDriver,
  MercuriusFederationDriverConfig,
} from '@nestjs/mercurius';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { UsersResolver } from './users.resolver.js';
import { UsersService } from './users.service.js'; // Not included in this example

@Module({
  imports: [
    GraphQLModule.forRoot<MercuriusFederationDriverConfig>({
      driver: MercuriusFederationDriver,
      autoSchemaFile: true,
    }),
  ],
  providers: [UsersResolver, UsersService],
})
export class AppModule {}
```

#### Ví dụ federation: Posts <a id="federated-example-posts-1"></a>

Service Posts phục vụ các bài viết được tổng hợp qua query `getPosts`, đồng thời mở rộng type `User` với một field `user.posts`.

#### Schema first

Service Posts tham chiếu tới type `User` trong schema của nó bằng cách đánh dấu nó với từ khóa `extend`. Nó cũng khai báo thêm một field trên type `User` (`posts`). Lưu ý directive `@key`, dùng để khớp các instance `User`, và directive `@external`, cho biết field `id` được quản lý ở nơi khác.

```graphql
type Post @key(fields: "id") {
  id: ID!
  title: String!
  body: String!
  user: User
}

extend type User @key(fields: "id") {
  id: ID! @external
  posts: [Post]
}

extend type Query {
  getPosts: [Post]
}
```

Trong ví dụ sau, `PostsResolver` cung cấp một method `getUser()` trả về một tham chiếu chứa `__typename` cùng mọi thuộc tính bổ sung mà ứng dụng của bạn cần để resolve tham chiếu, trong trường hợp này là `id`. Gateway dùng `__typename` để xác định chính xác microservice chịu trách nhiệm cho type `User` và lấy instance tương ứng. Để resolve tham chiếu, gateway gửi một request tới service Users mô tả ở trên, service này thực thi method `resolveReference()` của nó.

```typescript
import { Query, Resolver, Parent, ResolveField } from '@nestjs/graphql';
import { PostsService } from './posts.service.js';
import type { Post } from './posts.interfaces.js';

@Resolver('Post')
export class PostsResolver {
  constructor(private postsService: PostsService) {}

  @Query('getPosts')
  getPosts() {
    return this.postsService.findAll();
  }

  @ResolveField('user')
  getUser(@Parent() post: Post) {
    return { __typename: 'User', id: post.userId };
  }
}
```

Cuối cùng, đăng ký `GraphQLModule`, như trong service Users.

```typescript
import {
  MercuriusFederationDriver,
  MercuriusFederationDriverConfig,
} from '@nestjs/mercurius';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { PostsResolver } from './posts.resolver.js';

@Module({
  imports: [
    GraphQLModule.forRoot<MercuriusFederationDriverConfig>({
      driver: MercuriusFederationDriver,
      typePaths: ['**/*.graphql'],
    }),
  ],
  providers: [PostsResolver],
})
export class AppModule {}
```

#### Code first

Đầu tiên, khai báo một class đại diện cho entity `User`. Dù bản thân entity nằm ở một service khác, service này vẫn dùng nó (và mở rộng định nghĩa của nó). Lưu ý các directive `@extends` và `@external`.

```ts
import { Directive, ObjectType, Field, ID } from '@nestjs/graphql';
import { Post } from './post.entity.js';

@ObjectType()
@Directive('@extends')
@Directive('@key(fields: "id")')
export class User {
  @Field(() => ID)
  @Directive('@external')
  id: number;

  @Field(() => [Post])
  posts?: Post[];
}
```

Tiếp theo, tạo resolver cho phần mở rộng của entity `User`:

```ts
import { Parent, ResolveField, Resolver } from '@nestjs/graphql';
import { PostsService } from './posts.service.js';
import { Post } from './post.entity.js';
import { User } from './user.entity.js';

@Resolver(() => User)
export class UsersResolver {
  constructor(private readonly postsService: PostsService) {}

  @ResolveField(() => [Post])
  public posts(@Parent() user: User): Post[] {
    return this.postsService.forAuthor(user.id);
  }
}
```

Sau đó định nghĩa class entity `Post`:

```ts
import { Directive, Field, ID, Int, ObjectType } from '@nestjs/graphql';
import { User } from './user.entity.js';

@ObjectType()
@Directive('@key(fields: "id")')
export class Post {
  @Field(() => ID)
  id: number;

  @Field()
  title: string;

  @Field(() => Int)
  authorId: number;

  @Field(() => User)
  user?: User;
}
```

Và resolver của nó:

```ts
import { Query, Args, ResolveField, Resolver, Parent } from '@nestjs/graphql';
import { PostsService } from './posts.service.js';
import { Post } from './post.entity.js';
import { User } from './user.entity.js';

@Resolver(() => Post)
export class PostsResolver {
  constructor(private readonly postsService: PostsService) {}

  @Query(() => Post)
  findPost(@Args('id') id: number): Post {
    return this.postsService.findOne(id);
  }

  @Query(() => [Post])
  getPosts(): Post[] {
    return this.postsService.all();
  }

  @ResolveField(() => User)
  user(@Parent() post: Post): any {
    return { __typename: 'User', id: post.authorId };
  }
}
```

Cuối cùng, gắn mọi thứ lại với nhau trong một module. Lưu ý các tùy chọn build schema, chỉ định rằng `User` là một orphaned type (type bên ngoài).

```ts
import {
  MercuriusFederationDriver,
  MercuriusFederationDriverConfig,
} from '@nestjs/mercurius';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { User } from './user.entity.js';
import { PostsResolver } from './posts.resolver.js';
import { UsersResolver } from './users.resolver.js';
import { PostsService } from './posts.service.js'; // Not included in this example

@Module({
  imports: [
    GraphQLModule.forRoot<MercuriusFederationDriverConfig>({
      driver: MercuriusFederationDriver,
      autoSchemaFile: true,
      buildSchemaOptions: {
        orphanedTypes: [User],
      },
    }),
  ],
  providers: [PostsResolver, UsersResolver, PostsService],
})
export class AppModule {}
```

#### Ví dụ federation: Gateway <a id="federated-example-gateway-1"></a>

Bắt đầu bằng việc cài dependency cần thiết:

```bash
$ npm install --save @mercuriusjs/gateway
```

Gateway cần một danh sách endpoint, và nó tự động khám phá các schema tương ứng. Vì vậy, phần hiện thực gateway giống nhau cho cả cách tiếp cận code first lẫn schema first.

```typescript
import {
  MercuriusGatewayDriver,
  MercuriusGatewayDriverConfig,
} from '@nestjs/mercurius';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';

@Module({
  imports: [
    GraphQLModule.forRoot<MercuriusGatewayDriverConfig>({
      driver: MercuriusGatewayDriver,
      gateway: {
        services: [
          { name: 'users', url: 'http://user-service/graphql' },
          { name: 'posts', url: 'http://post-service/graphql' },
        ],
      },
    }),
  ],
})
export class AppModule {}
```

### Federation 2

Theo [tài liệu Apollo](https://www.apollographql.com/docs/federation/federation-2/new-in-federation-2), Federation 2 cải thiện trải nghiệm phát triển so với Apollo Federation ban đầu (trong phần này gọi là Federation 1) và tương thích ngược với hầu hết các supergraph ban đầu.

> warning **Cảnh báo** Mercurius chưa hỗ trợ đầy đủ Federation 2. Xem danh sách [các library subgraph hỗ trợ Federation 2](https://www.apollographql.com/docs/federation/supported-subgraphs#javascript--typescript) của Apollo.

Trong các phần tiếp theo, chúng ta sẽ nâng cấp ví dụ trước lên Federation 2.

#### Ví dụ federation: Users <a id="federated-example-users"></a>

Trong Federation 2, entity không có subgraph gốc, nên bạn không còn cần mở rộng `Query`. Để biết thêm chi tiết, xem [chủ đề entity](https://www.apollographql.com/docs/federation/federation-2/new-in-federation-2#entities) trong tài liệu Apollo Federation 2.

#### Schema first

Bỏ từ khóa `extend` khỏi schema. Để dùng Federation 2, schema cũng phải import các federation directive mà nó dùng bằng directive `@link`:

```graphql
extend schema @link(url: "https://specs.apollo.dev/federation/v2.0", import: ["@key"])

type User @key(fields: "id") {
  id: ID!
  name: String!
}

type Query {
  getUser(id: ID!): User
}
```

#### Code first

Để dùng Federation 2, hãy chỉ định phiên bản federation trong tùy chọn `autoSchemaFile`. Khi đó Nest sẽ thêm directive `@link` vào schema được sinh ra cho bạn.

```ts
import {
  ApolloFederationDriver,
  ApolloFederationDriverConfig,
} from '@nestjs/apollo';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { UsersResolver } from './users.resolver.js';
import { UsersService } from './users.service.js'; // Not included in this example

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloFederationDriverConfig>({
      driver: ApolloFederationDriver,
      autoSchemaFile: {
        federation: 2,
      },
    }),
  ],
  providers: [UsersResolver, UsersService],
})
export class AppModule {}
```

#### Ví dụ federation: Posts <a id="federated-example-posts-2"></a>

Vì cùng lý do đó, bạn không còn cần mở rộng `User` và `Query`.

#### Schema first

Bỏ từ khóa `extend` và directive `@external` khỏi schema, và thêm directive `@link`:

```graphql
extend schema @link(url: "https://specs.apollo.dev/federation/v2.0", import: ["@key"])

type Post @key(fields: "id") {
  id: ID!
  title: String!
  body: String!
  user: User
}

type User @key(fields: "id") {
  id: ID!
  posts: [Post]
}

type Query {
  getPosts: [Post]
}
```

#### Code first

Vì entity `User` không còn được mở rộng, hãy bỏ các directive `@extends` và `@external` khỏi `User`:

```ts
import { Directive, ObjectType, Field, ID } from '@nestjs/graphql';
import { Post } from './post.entity.js';

@ObjectType()
@Directive('@key(fields: "id")')
export class User {
  @Field(() => ID)
  id: number;

  @Field(() => [Post])
  posts?: Post[];
}
```

Như trong service Users, hãy cấu hình `GraphQLModule` để dùng Federation 2:

```ts
import {
  ApolloFederationDriver,
  ApolloFederationDriverConfig,
} from '@nestjs/apollo';
import { Module } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { User } from './user.entity.js';
import { PostsResolver } from './posts.resolver.js';
import { UsersResolver } from './users.resolver.js';
import { PostsService } from './posts.service.js'; // Not included in this example

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloFederationDriverConfig>({
      driver: ApolloFederationDriver,
      autoSchemaFile: {
        federation: 2,
      },
      buildSchemaOptions: {
        orphanedTypes: [User],
      },
    }),
  ],
  providers: [PostsResolver, UsersResolver, PostsService],
})
export class AppModule {}
```

#### Ẩn operation khỏi supergraph <a id="hiding-operations-from-the-supergraph"></a>

Để giữ một query, mutation hoặc field nằm ngoài API công khai của supergraph trong khi subgraph vẫn phục vụ nó, hãy đánh dấu nó bằng directive `@inaccessible` của Federation 2. Với cách tiếp cận code first, hãy dùng decorator `@Directive()`:

```typescript
@Query(() => Int)
@Directive('@inaccessible')
internalStats() {
  return this.statsService.count();
}
```

Operation vẫn thực thi được trên subgraph và được liệt kê trong `_service {{ '{' }} sdl {{ '}' }}` của nó, nhưng quá trình composition sẽ loại nó ra khỏi supergraph schema mà client nhìn thấy.
