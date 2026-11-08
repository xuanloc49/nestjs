### Federation

Federation cho phép bạn tách một GraphQL server nguyên khối thành các microservice độc lập. Nó gồm hai thành phần: một gateway và một hoặc nhiều microservice được federate. Mỗi microservice giữ một phần của schema, và gateway gộp các schema thành một schema duy nhất mà client sử dụng.

Như mô tả trong [bài giới thiệu về federation của Apollo](https://blog.apollographql.com/apollo-federation-f260cf525d21), federation được thiết kế xoay quanh các nguyên tắc cốt lõi sau:

- Việc xây dựng một graph nên mang tính **khai báo.** Với federation, bạn kết hợp một graph một cách khai báo ngay từ bên trong schema thay vì viết code ghép schema (schema stitching) theo kiểu mệnh lệnh.
- Code nên được tách theo **mối quan tâm (concern)**, không phải theo type. Thường không có team nào kiểm soát mọi khía cạnh của một type quan trọng như User hay Product, nên định nghĩa của các type này nên được phân tán giữa các team và codebase, thay vì tập trung một chỗ.
- Graph nên đơn giản để client sử dụng. Cùng nhau, các service được federate có thể tạo thành một graph hoàn chỉnh, tập trung vào sản phẩm, phản ánh chính xác cách nó được sử dụng ở phía client.
- Nó chỉ là **GraphQL**, chỉ dùng các tính năng tuân thủ đặc tả của ngôn ngữ. Bất kỳ ngôn ngữ nào, không chỉ JavaScript, đều có thể hiện thực federation.

> info **Hint** Các subgraph được xây bằng `ApolloFederationDriver` hoặc `MercuriusFederationDriver` hỗ trợ subscription (với tùy chọn `subscriptions` cho Apollo, hoặc `subscription: true` cho Mercurius). Apollo Gateway (`ApolloGatewayDriver`) không chuyển tiếp subscription tới các subgraph, nên để đưa chúng ra qua một federated endpoint duy nhất, hãy dùng một router hỗ trợ federated subscription, như Apollo Router, hoặc Mercurius gateway (đặt `subscription: true` trên gateway và `wsUrl` cho mỗi service).

Trong các phần tiếp theo, chúng ta sẽ thiết lập một ứng dụng demo gồm một gateway và hai federated endpoint: service Users và service Posts.

#### Federation với Apollo

Bắt đầu bằng việc cài các dependency cần thiết:

[[CODE:1]]

#### Schema first

Service Users cung cấp một schema đơn giản. Directive `@key` cho Apollo query planner biết rằng một instance cụ thể của `User` có thể được lấy theo `id` của nó. Cũng lưu ý rằng schema mở rộng type `Query`.

[[CODE:2]]

Resolver cung cấp thêm một method tên `resolveReference()`. Apollo gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

[[CODE:3]]

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `ApolloFederationDriver` trong configuration object:

[[CODE:4]]

#### Code first

Bắt đầu bằng việc thêm một số decorator vào entity `User`:

[[CODE:5]]

Resolver cung cấp thêm một method tên `resolveReference()`. Apollo gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

[[CODE:6]]

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `ApolloFederationDriver` trong configuration object:

[[CODE:7]]

Có sẵn các ví dụ chạy được cho cách tiếp cận [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/users-application) và [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/users-application).

#### Ví dụ federation: Posts

Service Posts phục vụ các bài viết được tổng hợp qua query `getPosts`, đồng thời mở rộng type `User` với một field `user.posts`.

#### Schema first

Service Posts tham chiếu tới type `User` trong schema của nó bằng cách đánh dấu nó với từ khóa `extend`. Nó cũng khai báo thêm một field trên type `User` (`posts`). Lưu ý directive `@key`, dùng để khớp các instance `User`, và directive `@external`, cho biết field `id` được quản lý ở nơi khác.

[[CODE:8]]

Trong ví dụ sau, `PostsResolver` cung cấp một method `getUser()` trả về một tham chiếu chứa `__typename` cùng mọi thuộc tính bổ sung mà ứng dụng của bạn cần để resolve tham chiếu, trong trường hợp này là `id`. Gateway dùng `__typename` để xác định chính xác microservice chịu trách nhiệm cho type `User` và lấy instance tương ứng. Để resolve tham chiếu, gateway gửi một request tới service Users mô tả ở trên, service này thực thi method `resolveReference()` của nó.

[[CODE:9]]

Cuối cùng, đăng ký `GraphQLModule`, như trong service Users.

[[CODE:10]]

#### Code first

Đầu tiên, khai báo một class đại diện cho entity `User`. Dù bản thân entity nằm ở một service khác, service này vẫn dùng nó (và mở rộng định nghĩa của nó). Lưu ý các directive `@extends` và `@external`.

[[CODE:11]]

Tiếp theo, tạo resolver cho phần mở rộng của entity `User`:

[[CODE:12]]

Sau đó định nghĩa class entity `Post`:

[[CODE:13]]

Và resolver của nó:

[[CODE:14]]

Cuối cùng, gắn mọi thứ lại với nhau trong một module. Lưu ý các tùy chọn build schema, chỉ định rằng `User` là một orphaned type (type bên ngoài).

[[CODE:15]]

Có sẵn các ví dụ chạy được cho cách tiếp cận [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/posts-application) và [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/posts-application).

#### Ví dụ federation: Gateway

Bắt đầu bằng việc cài dependency cần thiết:

[[CODE:16]]

Gateway cần một danh sách endpoint, và nó tự động khám phá các schema tương ứng. Vì vậy, phần hiện thực gateway giống nhau cho cả cách tiếp cận code first lẫn schema first.

[[CODE:17]]

Có sẵn các ví dụ chạy được cho cách tiếp cận [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/gateway) và [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/gateway).

#### Federation với Mercurius

Bắt đầu bằng việc cài các dependency cần thiết:

[[CODE:18]]

> info **Note** Package `@apollo/subgraph` là bắt buộc để xây dựng một subgraph schema (các hàm `buildSubgraphSchema` và `printSubgraphSchema`).

#### Schema first

Service Users cung cấp một schema đơn giản. Directive `@key` cho Mercurius query planner biết rằng một instance cụ thể của `User` có thể được lấy theo `id` của nó. Cũng lưu ý rằng schema mở rộng type `Query`.

[[CODE:19]]

Resolver cung cấp thêm một method tên `resolveReference()`. Mercurius gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

[[CODE:20]]

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `MercuriusFederationDriver` trong configuration object:

[[CODE:21]]

#### Code first

Bắt đầu bằng việc thêm một số decorator vào entity `User`:

[[CODE:22]]

Resolver cung cấp thêm một method tên `resolveReference()`. Mercurius gateway gọi method này bất cứ khi nào một tài nguyên liên quan cần một instance `User`. Bạn sẽ thấy một ví dụ về điều này trong service Posts ở phần sau. Method phải được chú thích bằng decorator `@ResolveReference()`.

[[CODE:23]]

Cuối cùng, nối mọi thứ lại bằng cách đăng ký `GraphQLModule` với driver `MercuriusFederationDriver` trong configuration object:

[[CODE:24]]

#### Ví dụ federation: Posts

Service Posts phục vụ các bài viết được tổng hợp qua query `getPosts`, đồng thời mở rộng type `User` với một field `user.posts`.

#### Schema first

Service Posts tham chiếu tới type `User` trong schema của nó bằng cách đánh dấu nó với từ khóa `extend`. Nó cũng khai báo thêm một field trên type `User` (`posts`). Lưu ý directive `@key`, dùng để khớp các instance `User`, và directive `@external`, cho biết field `id` được quản lý ở nơi khác.

[[CODE:25]]

Trong ví dụ sau, `PostsResolver` cung cấp một method `getUser()` trả về một tham chiếu chứa `__typename` cùng mọi thuộc tính bổ sung mà ứng dụng của bạn cần để resolve tham chiếu, trong trường hợp này là `id`. Gateway dùng `__typename` để xác định chính xác microservice chịu trách nhiệm cho type `User` và lấy instance tương ứng. Để resolve tham chiếu, gateway gửi một request tới service Users mô tả ở trên, service này thực thi method `resolveReference()` của nó.

[[CODE:26]]

Cuối cùng, đăng ký `GraphQLModule`, như trong service Users.

[[CODE:27]]

#### Code first

Đầu tiên, khai báo một class đại diện cho entity `User`. Dù bản thân entity nằm ở một service khác, service này vẫn dùng nó (và mở rộng định nghĩa của nó). Lưu ý các directive `@extends` và `@external`.

[[CODE:28]]

Tiếp theo, tạo resolver cho phần mở rộng của entity `User`:

[[CODE:29]]

Sau đó định nghĩa class entity `Post`:

[[CODE:30]]

Và resolver của nó:

[[CODE:31]]

Cuối cùng, gắn mọi thứ lại với nhau trong một module. Lưu ý các tùy chọn build schema, chỉ định rằng `User` là một orphaned type (type bên ngoài).

[[CODE:32]]

#### Ví dụ federation: Gateway

Bắt đầu bằng việc cài dependency cần thiết:

[[CODE:33]]

Gateway cần một danh sách endpoint, và nó tự động khám phá các schema tương ứng. Vì vậy, phần hiện thực gateway giống nhau cho cả cách tiếp cận code first lẫn schema first.

[[CODE:34]]

### Federation 2

Theo [tài liệu Apollo](https://www.apollographql.com/docs/federation/federation-2/new-in-federation-2), Federation 2 cải thiện trải nghiệm phát triển so với Apollo Federation ban đầu (trong phần này gọi là Federation 1) và tương thích ngược với hầu hết các supergraph ban đầu.

> warning **Warning** Mercurius chưa hỗ trợ đầy đủ Federation 2. Xem danh sách [các library subgraph hỗ trợ Federation 2](https://www.apollographql.com/docs/federation/supported-subgraphs#javascript--typescript) của Apollo.

Trong các phần tiếp theo, chúng ta sẽ nâng cấp ví dụ trước lên Federation 2.

#### Ví dụ federation: Users

Trong Federation 2, entity không có subgraph gốc, nên bạn không còn cần mở rộng `Query`. Để biết thêm chi tiết, xem [chủ đề entity](https://www.apollographql.com/docs/federation/federation-2/new-in-federation-2#entities) trong tài liệu Apollo Federation 2.

#### Schema first

Bỏ từ khóa `extend` khỏi schema. Để dùng Federation 2, schema cũng phải import các federation directive mà nó dùng bằng directive `@link`:

[[CODE:35]]

#### Code first

Để dùng Federation 2, hãy chỉ định phiên bản federation trong tùy chọn `autoSchemaFile`. Khi đó Nest sẽ thêm directive `@link` vào schema được sinh ra cho bạn.

[[CODE:36]]

#### Ví dụ federation: Posts

Vì cùng lý do đó, bạn không còn cần mở rộng `User` và `Query`.

#### Schema first

Bỏ từ khóa `extend` và directive `@external` khỏi schema, và thêm directive `@link`:

[[CODE:37]]

#### Code first

Vì entity `User` không còn được mở rộng, hãy bỏ các directive `@extends` và `@external` khỏi `User`:

[[CODE:38]]

Như trong service Users, hãy cấu hình `GraphQLModule` để dùng Federation 2:

[[CODE:39]]

#### Ẩn operation khỏi supergraph

Để giữ một query, mutation hoặc field nằm ngoài API công khai của supergraph trong khi subgraph vẫn phục vụ nó, hãy đánh dấu nó bằng directive `@inaccessible` của Federation 2. Với cách tiếp cận code first, hãy dùng decorator `@Directive()`:

[[CODE:40]]

Operation vẫn thực thi được trên subgraph và được liệt kê trong `_service {{ '{' }} sdl {{ '}' }}` của nó, nhưng quá trình composition sẽ loại nó ra khỏi supergraph schema mà client nhìn thấy.
