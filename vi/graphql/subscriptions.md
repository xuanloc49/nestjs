### Subscription

Ngoài việc lấy dữ liệu bằng query và thay đổi dữ liệu bằng mutation, đặc tả GraphQL còn hỗ trợ loại operation thứ ba, gọi là `subscription`. GraphQL subscription đẩy dữ liệu từ server tới những client chọn lắng nghe các message real-time. Giống như query, subscription chỉ định một tập field sẽ được gửi tới client. Tuy nhiên, thay vì trả về ngay một kết quả duy nhất, chúng mở một kênh, và server gửi kết quả tới client mỗi khi một event cụ thể xảy ra.

Một use case phổ biến của subscription là thông báo cho client về các event cụ thể, chẳng hạn khi một object mới được tạo hoặc các field được cập nhật (xem [Subscription](https://www.apollographql.com/docs/react/data/subscriptions) trong tài liệu Apollo).

#### Bật subscription với Apollo driver <a id="enable-subscriptions-with-apollo-driver"></a>

Subscription được truyền qua WebSocket bởi package [graphql-ws](https://github.com/enisdenjo/graphql-ws). `@nestjs/graphql` đã phụ thuộc vào nó, nhưng hãy cài nó trong project của bạn nữa nếu bạn import trực tiếp từ nó (ví dụ type `Context` được dùng trong [Xác thực qua WebSocket](/graphql/subscriptions#authentication-over-websockets)):

```bash
$ npm i --save graphql-ws
```

Sau đó bật transport:

```typescript
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  subscriptions: {
    'graphql-ws': true,
  },
}),
```

> warning **Cảnh báo** Hỗ trợ cho `subscriptions-transport-ws` đã bị **gỡ bỏ** trong `@nestjs/graphql` v14. Package này không còn là dependency, và key `'subscriptions-transport-ws'` không còn được chấp nhận trong options object `subscriptions`. Nếu bạn đang nâng cấp, hãy thay key đó bằng `'graphql-ws'` và cập nhật client sang giao thức mới hơn. Hai giao thức không tương thích với nhau ở tầng truyền tải, nên các client vẫn dùng `subscriptions-transport-ws` sẽ không kết nối được. Signature của callback `onConnect` cũng khác: với `graphql-ws`, nó nhận connection context, và các giá trị context bổ sung thuộc về field `extra` của nó (xem [Xác thực qua WebSocket](/graphql/subscriptions#authentication-over-websockets) bên dưới).

#### Code first

Để tạo một subscription theo cách tiếp cận code first, hãy dùng decorator `@Subscription()` (được export từ package `@nestjs/graphql`) và class `PubSub` từ package `graphql-subscriptions`, class này cung cấp một **API publish/subscribe** đơn giản.

Subscription handler sau **subscribe** một event bằng cách gọi `PubSub#asyncIterableIterator`. Method này nhận một tham số duy nhất, `triggerName`, tương ứng với tên topic của event.

```typescript
const pubSub = new PubSub();

@Resolver(() => Author)
export class AuthorResolver {
  // ...
  @Subscription(() => Comment)
  commentAdded() {
    return pubSub.asyncIterableIterator('commentAdded');
  }
}
```

> info **Gợi ý** Mọi decorator đều được export từ package `@nestjs/graphql`, còn class `PubSub` được export từ package `graphql-subscriptions` (`npm i graphql-subscriptions`).

> warning **Lưu ý** `PubSub` là một class cung cấp API `publish` và `subscribe` đơn giản. Tìm hiểu thêm trong [hướng dẫn thiết lập graphql-subscriptions](https://www.apollographql.com/docs/graphql-subscriptions/setup.html). Tài liệu Apollo cảnh báo rằng [phần hiện thực mặc định](https://github.com/apollographql/graphql-subscriptions#getting-started-with-your-first-subscription) không phù hợp cho production. Các ứng dụng production nên dùng một phần hiện thực `PubSub` dựa trên một store bên ngoài (xem danh sách [các phần hiện thực PubSub](https://github.com/apollographql/graphql-subscriptions#pubsub-implementations)).

Nó sinh ra phần sau của GraphQL schema bằng SDL:

```graphql
type Subscription {
  commentAdded: Comment!
}
```

Theo định nghĩa, subscription trả về một object có một thuộc tính cấp cao nhất duy nhất với key là tên của subscription. Tên này hoặc được kế thừa từ tên của method subscription handler (tức `commentAdded` ở trên), hoặc được cung cấp tường minh qua tùy chọn `name` trong tham số thứ hai của decorator `@Subscription()`, như bên dưới.

```typescript
@Subscription(() => Comment, {
  name: 'commentAdded',
})
subscribeToCommentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

Cấu trúc này tạo ra cùng SDL với đoạn code mẫu trước, nhưng tách tên method khỏi tên subscription.

#### Publish <a id="publishing"></a>

Để publish event, hãy dùng method `PubSub#publish`. Nó thường được gọi bên trong một mutation để kích hoạt việc cập nhật phía client khi một phần của object graph thay đổi. Ví dụ:

```typescript
@@filename(posts/posts.resolver)
@Mutation(() => Comment)
async addComment(
  @Args('postId', { type: () => Int }) postId: number,
  @Args('comment', { type: () => CommentInput }) comment: CommentInput,
) {
  const newComment = this.commentsService.addComment({ id: postId, comment });
  pubSub.publish('commentAdded', { commentAdded: newComment });
  return newComment;
}
```

Method `PubSub#publish` nhận một `triggerName` (một lần nữa, hãy coi nó là tên topic của event) làm tham số đầu tiên, và một event payload làm tham số thứ hai. Như đã nói, theo định nghĩa một subscription trả về một giá trị, và giá trị đó có một cấu trúc. Hãy xem lại SDL được sinh ra cho subscription `commentAdded`:

```graphql
type Subscription {
  commentAdded: Comment!
}
```

Điều này cho chúng ta biết subscription phải trả về một object có thuộc tính cấp cao nhất tên `commentAdded` với giá trị là một object `Comment`. Cấu trúc của event payload được phát ra bởi method `PubSub#publish` phải khớp với cấu trúc của giá trị mà subscription được kỳ vọng trả về. Trong ví dụ ở trên, câu lệnh `pubSub.publish('commentAdded', {{ '{' }} commentAdded: newComment {{ '}' }})` publish một event `commentAdded` với payload có cấu trúc phù hợp. Nếu cấu trúc không khớp, subscription sẽ thất bại khi event được resolve.

#### Lọc subscription <a id="filtering-subscriptions"></a>

Để lọc bỏ các event cụ thể, hãy đặt thuộc tính `filter` thành một hàm lọc. Hàm này hoạt động giống callback được truyền cho method `filter()` của mảng. Nó nhận hai tham số: `payload`, chứa event payload (do bên publish event gửi), và `variables`, chứa mọi argument được truyền kèm request subscription. Nó trả về một boolean quyết định event có được publish tới các client đang lắng nghe hay không.

```typescript
@Subscription(() => Comment, {
  filter: (payload, variables) =>
    payload.commentAdded.title === variables.title,
})
commentAdded(@Args('title') title: string) {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

#### Biến đổi payload của subscription <a id="mutating-subscription-payloads"></a>

Để biến đổi event payload được publish, hãy đặt thuộc tính `resolve` thành một hàm. Hàm này nhận event payload (do bên publish event gửi) và trả về giá trị phù hợp.

```typescript
@Subscription(() => Comment, {
  resolve: value => value,
})
commentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

> warning **Lưu ý** Nếu bạn dùng tùy chọn `resolve`, hãy trả về payload đã được bóc ra (trong ví dụ của chúng ta, trả về trực tiếp object `newComment`, không phải object `{{ '{' }} commentAdded: newComment {{ '}' }}`).

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau.

```typescript
@Subscription(() => Comment, {
  resolve(this: AuthorResolver, value) {
    // "this" refers to an instance of "AuthorResolver"
    return value;
  }
})
commentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

Cấu trúc tương tự cũng dùng được với filter:

```typescript
@Subscription(() => Comment, {
  filter(this: AuthorResolver, payload, variables) {
    // "this" refers to an instance of "AuthorResolver"
    return payload.commentAdded.title === variables.title;
  }
})
commentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

#### Schema first

Để tạo một subscription tương đương trong Nest, hãy dùng decorator `@Subscription()`.

```typescript
const pubSub = new PubSub();

@Resolver('Author')
export class AuthorResolver {
  // ...
  @Subscription()
  commentAdded() {
    return pubSub.asyncIterableIterator('commentAdded');
  }
}
```

Để lọc bỏ các event cụ thể dựa trên context và argument, hãy đặt thuộc tính `filter`.

```typescript
@Subscription('commentAdded', {
  filter: (payload, variables) =>
    payload.commentAdded.title === variables.title,
})
commentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

Để biến đổi payload được publish, hãy dùng một hàm `resolve`.

```typescript
@Subscription('commentAdded', {
  resolve: value => value,
})
commentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau:

```typescript
@Subscription('commentAdded', {
  resolve(this: AuthorResolver, value) {
    // "this" refers to an instance of "AuthorResolver"
    return value;
  }
})
commentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

Cấu trúc tương tự cũng dùng được với filter:

```typescript
@Subscription('commentAdded', {
  filter(this: AuthorResolver, payload, variables) {
    // "this" refers to an instance of "AuthorResolver"
    return payload.commentAdded.title === variables.title;
  }
})
commentAdded() {
  return pubSub.asyncIterableIterator('commentAdded');
}
```

Bước cuối cùng là cập nhật file định nghĩa type.

```graphql
type Author {
  id: Int!
  firstName: String
  lastName: String
  posts: [Post]
}

type Post {
  id: Int!
  title: String
  votes: Int
}

type Query {
  author(id: Int!): Author
}

type Comment {
  id: String
  content: String
}

type Subscription {
  commentAdded(title: String!): Comment
}
```

Với điều này, chúng ta đã tạo một subscription duy nhất `commentAdded(title: String!): Comment`. Một [ví dụ schema first](https://github.com/nestjs/nest/blob/master/sample/12-graphql-schema-first) hoàn chỉnh có sẵn trong repository của NestJS.

#### PubSub

Các ví dụ ở trên khởi tạo một instance `PubSub` cục bộ. Cách được ưu tiên là định nghĩa `PubSub` làm một [provider](/fundamentals/custom-providers) và inject nó qua constructor (bằng decorator `@Inject()`), để cùng một instance được tái sử dụng trong toàn bộ ứng dụng. Ví dụ, định nghĩa một provider như sau, rồi inject `'PUB_SUB'` ở nơi cần.

```typescript
{
  provide: 'PUB_SUB',
  useValue: new PubSub(),
}
```

#### Tùy chỉnh subscription server <a id="customize-subscriptions-server"></a>

Để tùy chỉnh subscription server (ví dụ để thay đổi path của nó, mặc định là path của GraphQL endpoint), hãy truyền một options object cho `graphql-ws` trong thuộc tính `subscriptions`:

```typescript
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  subscriptions: {
    'graphql-ws': {
      path: '/graphql',
    },
  },
});
```

Để tự cấu hình WebSocket server bên dưới (ví dụ để bật `perMessageDeflate`, giới hạn `maxPayload`, hoặc thêm bước kiểm tra `verifyClient`), hãy tạo một `WebSocketServer` của [`ws`](https://github.com/websockets/ws) và truyền nó làm `server`:

```typescript
import { WebSocketServer } from 'ws';

GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  subscriptions: {
    'graphql-ws': {
      server: new WebSocketServer({
        noServer: true,
        path: '/subscriptions',
        maxPayload: 1024 * 1024,
      }),
    },
  },
});
```

- Server phải được tạo với `noServer: true`: Nest điều hướng các HTTP upgrade request tới nó, và sẽ throw nếu không như vậy.
- Nếu server có `path`, nó được ưu tiên hơn `graphql-ws.path` và path của GraphQL endpoint.
- Server được giao cho `graphql-ws`, thư viện này thay thế tùy chọn `handleProtocols` của nó và, khi ứng dụng shutdown, đóng nó lại và gỡ bỏ mọi listener của nó.
- Hãy dùng một server riêng cho mỗi `GraphQLModule`; một instance không thể được dùng chung giữa các module.

> info **Gợi ý** Chỉ phần hiện thực `ws` được hỗ trợ. Các adapter Fastify và uWebSockets của `graphql-ws` không thể cắm vào theo cách này.

#### Xác thực qua WebSocket <a id="authentication-over-websockets"></a>

Để kiểm tra người dùng đã được xác thực hay chưa, hãy dùng callback function `onConnect`, thứ bạn có thể chỉ định trong các tùy chọn `subscriptions`.

Với `graphql-ws`, callback `onConnect` nhận connection context, bao gồm `connectionParams`.

```typescript
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  subscriptions: {
    'graphql-ws': {
      onConnect: (context: Context<any>) => {
        const { connectionParams, extra } = context;
        const authToken = connectionParams.authToken;
        if (!isValid(authToken)) {
          throw new Error('Token is not valid');
        }
        // when using graphql-ws, additional context values should be stored in the extra field
        extra.user = { user: {} };
      },
    },
  },
  context: ({ extra }) => {
    // you can now access your additional context value through the extra field
  },
});
```

#### Bật subscription với Mercurius driver <a id="enable-subscriptions-with-mercurius-driver"></a>

Để bật subscription, hãy đặt thuộc tính `subscription` thành `true`.

```typescript
GraphQLModule.forRoot<MercuriusDriverConfig>({
  driver: MercuriusDriver,
  subscription: true,
}),
```

> info **Gợi ý** Bạn cũng có thể truyền một options object để thiết lập một custom emitter, validate các kết nối đi vào, v.v. Xem tùy chọn `subscription` trong [tùy chọn plugin của Mercurius](https://github.com/mercurius-js/mercurius/blob/master/docs/api/options.md#plugin-options).

#### Code first

Để tạo một subscription theo cách tiếp cận code first, hãy dùng decorator `@Subscription()` (được export từ package `@nestjs/graphql`) và class `PubSub` từ package `mercurius`, class này cung cấp một **API publish/subscribe** đơn giản.

Subscription handler sau **subscribe** một event bằng cách gọi `PubSub#subscribe`. Method này nhận tên topic làm tham số.

```typescript
@Resolver(() => Author)
export class AuthorResolver {
  // ...
  @Subscription(() => Comment)
  commentAdded(@Context('pubsub') pubSub: PubSub) {
    return pubSub.subscribe('commentAdded');
  }
}
```

> info **Gợi ý** Mọi decorator dùng trong ví dụ ở trên đều được export từ package `@nestjs/graphql`, còn class `PubSub` được export từ package `mercurius`.

> warning **Lưu ý** `PubSub` là một class cung cấp API `publish` và `subscribe` đơn giản. Để đăng ký một class `PubSub` tùy chỉnh, xem [Subscriptions with custom PubSub](https://github.com/mercurius-js/mercurius/blob/master/docs/subscriptions.md#subscriptions-with-custom-pubsub) trong tài liệu Mercurius.

Nó sinh ra phần sau của GraphQL schema bằng SDL:

```graphql
type Subscription {
  commentAdded: Comment!
}
```

Theo định nghĩa, subscription trả về một object có một thuộc tính cấp cao nhất duy nhất với key là tên của subscription. Tên này hoặc được kế thừa từ tên của method subscription handler (tức `commentAdded` ở trên), hoặc được cung cấp tường minh qua tùy chọn `name` trong tham số thứ hai của decorator `@Subscription()`, như bên dưới.

```typescript
@Subscription(() => Comment, {
  name: 'commentAdded',
})
subscribeToCommentAdded(@Context('pubsub') pubSub: PubSub) {
  return pubSub.subscribe('commentAdded');
}
```

Cấu trúc này tạo ra cùng SDL với đoạn code mẫu trước, nhưng tách tên method khỏi tên subscription.

#### Publish <a id="publishing-1"></a>

Để publish event, hãy dùng method `PubSub#publish`. Nó thường được gọi bên trong một mutation để kích hoạt việc cập nhật phía client khi một phần của object graph thay đổi. Ví dụ:

```typescript
@@filename(posts/posts.resolver)
@Mutation(() => Comment)
async addComment(
  @Args('postId', { type: () => Int }) postId: number,
  @Args('comment', { type: () => CommentInput }) comment: CommentInput,
  @Context('pubsub') pubSub: PubSub,
) {
  const newComment = this.commentsService.addComment({ id: postId, comment });
  await pubSub.publish({
    topic: 'commentAdded',
    payload: {
      commentAdded: newComment
    }
  });
  return newComment;
}
```

Như đã nói, theo định nghĩa một subscription trả về một giá trị, và giá trị đó có một cấu trúc. Hãy xem lại SDL được sinh ra cho subscription `commentAdded`:

```graphql
type Subscription {
  commentAdded: Comment!
}
```

Điều này cho chúng ta biết subscription phải trả về một object có thuộc tính cấp cao nhất tên `commentAdded` với giá trị là một object `Comment`. Cấu trúc của event payload được phát ra bởi method `PubSub#publish` phải khớp với cấu trúc của giá trị mà subscription được kỳ vọng trả về. Trong ví dụ ở trên, câu lệnh `pubSub.publish({{ '{' }} topic: 'commentAdded', payload: {{ '{' }} commentAdded: newComment {{ '}' }} {{ '}' }})` publish một event `commentAdded` với payload có cấu trúc phù hợp. Nếu cấu trúc không khớp, subscription sẽ thất bại khi event được resolve.

#### Lọc subscription <a id="filtering-subscriptions-1"></a>

Để lọc bỏ các event cụ thể, hãy đặt thuộc tính `filter` thành một hàm lọc. Hàm này hoạt động giống callback được truyền cho method `filter()` của mảng. Nó nhận hai tham số: `payload`, chứa event payload (do bên publish event gửi), và `variables`, chứa mọi argument được truyền kèm request subscription. Nó trả về một boolean quyết định event có được publish tới các client đang lắng nghe hay không.

```typescript
@Subscription(() => Comment, {
  filter: (payload, variables) =>
    payload.commentAdded.title === variables.title,
})
commentAdded(@Args('title') title: string, @Context('pubsub') pubSub: PubSub) {
  return pubSub.subscribe('commentAdded');
}
```

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau.

```typescript
@Subscription(() => Comment, {
  filter(this: AuthorResolver, payload, variables) {
    // "this" refers to an instance of "AuthorResolver"
    return payload.commentAdded.title === variables.title;
  }
})
commentAdded(@Args('title') title: string, @Context('pubsub') pubSub: PubSub) {
  return pubSub.subscribe('commentAdded');
}
```

#### Schema first

Để tạo một subscription tương đương trong Nest, hãy dùng decorator `@Subscription()`.

```typescript
@Resolver('Author')
export class AuthorResolver {
  // ...
  @Subscription()
  commentAdded(@Context('pubsub') pubSub: PubSub) {
    return pubSub.subscribe('commentAdded');
  }
}
```

Để lọc bỏ các event cụ thể dựa trên context và argument, hãy đặt thuộc tính `filter`.

```typescript
@Subscription('commentAdded', {
  filter: (payload, variables) =>
    payload.commentAdded.title === variables.title,
})
commentAdded(@Context('pubsub') pubSub: PubSub) {
  return pubSub.subscribe('commentAdded');
}
```

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau:

```typescript
@Subscription('commentAdded', {
  filter(this: AuthorResolver, payload, variables) {
    // "this" refers to an instance of "AuthorResolver"
    return payload.commentAdded.title === variables.title;
  }
})
commentAdded(@Context('pubsub') pubSub: PubSub) {
  return pubSub.subscribe('commentAdded');
}
```

Bước cuối cùng là cập nhật file định nghĩa type.

```graphql
type Author {
  id: Int!
  firstName: String
  lastName: String
  posts: [Post]
}

type Post {
  id: Int!
  title: String
  votes: Int
}

type Query {
  author(id: Int!): Author
}

type Comment {
  id: String
  content: String
}

type Subscription {
  commentAdded(title: String!): Comment
}
```

Với điều này, chúng ta đã tạo một subscription duy nhất `commentAdded(title: String!): Comment`.

#### PubSub

Các ví dụ ở trên dùng emitter `PubSub` mặc định ([mqemitter](https://github.com/mcollina/mqemitter)). Cho production, cách được ưu tiên là dùng `mqemitter-redis`. Ngoài ra, bạn có thể cung cấp một phần hiện thực `PubSub` tùy chỉnh (xem [Subscription](https://github.com/mercurius-js/mercurius/blob/master/docs/subscriptions.md) trong tài liệu Mercurius).

```typescript
import mqemitterRedis from 'mqemitter-redis';

GraphQLModule.forRoot<MercuriusDriverConfig>({
  driver: MercuriusDriver,
  subscription: {
    emitter: mqemitterRedis({
      port: 6579,
      host: '127.0.0.1',
    }),
  },
});
```

#### Xác thực qua WebSocket <a id="authentication-over-websockets-1"></a>

Để kiểm tra người dùng đã được xác thực hay chưa, hãy dùng callback function `verifyClient`, thứ bạn có thể chỉ định trong các tùy chọn `subscription`.

Callback `verifyClient` nhận object `info` làm tham số đầu tiên, bạn có thể dùng nó để đọc các header của request.

```typescript
GraphQLModule.forRoot<MercuriusDriverConfig>({
  driver: MercuriusDriver,
  subscription: {
    verifyClient: (info, next) => {
      const authorization = info.req.headers?.authorization as string;
      if (!authorization?.startsWith('Bearer ')) {
        return next(false);
      }
      next(true);
    },
  }
}),
```
