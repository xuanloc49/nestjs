## Khai thác sức mạnh của TypeScript & GraphQL

[GraphQL](https://graphql.org/) là một ngôn ngữ truy vấn cho API và là một runtime để đáp ứng các truy vấn đó bằng dữ liệu bạn đang có. Nó giải quyết nhiều vấn đề thường gặp ở REST API. Để có thêm bối cảnh, hãy xem [bài so sánh GraphQL và REST](https://www.apollographql.com/blog/graphql-vs-rest) này. Kết hợp với [TypeScript](https://www.typescriptlang.org/), GraphQL cho bạn type safety tốt hơn cho các truy vấn và type xuyên suốt từ đầu đến cuối.

Chương này giả định bạn đã hiểu cơ bản về GraphQL và tập trung vào cách làm việc với module `@nestjs/graphql` có sẵn. `GraphQLModule` có thể được cấu hình để dùng [Apollo](https://www.apollographql.com/) Server (với driver `@nestjs/apollo`) hoặc [Mercurius](https://github.com/mercurius-js/mercurius) (với driver `@nestjs/mercurius`). Nest cung cấp tích hợp chính thức cho cả hai package (xem thêm phần [tích hợp bên thứ ba](/graphql/quick-start#third-party-integrations) bên dưới).

Bạn cũng có thể tự xây driver của riêng mình (xem [Tạo một custom driver](/graphql/other-features#creating-a-custom-driver)).

#### Cài đặt

Bắt đầu bằng việc cài các package cần thiết:

[[CODE:1]]

> warning **Warning** `@nestjs/apollo` v14 yêu cầu **Apollo Server v5** (package `@apollo/server`). Nếu bạn đang nâng cấp từ một phiên bản Apollo Server cũ hơn, hãy xem [hướng dẫn migration của Apollo Server](https://www.apollographql.com/docs/apollo-server/migration/).

#### Tổng quan

Nest cung cấp hai cách để xây dựng ứng dụng GraphQL: **code first** và **schema first**. Hãy chọn cách phù hợp nhất với bạn. Phần lớn các chương trong phần GraphQL này được chia làm hai phần: một cho cách tiếp cận **code first** và một cho cách tiếp cận **schema first**.

Với cách tiếp cận **code first**, bạn dùng decorator và các class TypeScript để sinh ra GraphQL schema tương ứng. Cách này phù hợp nếu bạn muốn chỉ làm việc với TypeScript và tránh phải chuyển qua lại giữa các cú pháp ngôn ngữ.

Với cách tiếp cận **schema first**, nguồn sự thật (source of truth) là một tập các file GraphQL SDL (Schema Definition Language). SDL là cách không phụ thuộc ngôn ngữ để chia sẻ file schema giữa các nền tảng. Nest sinh ra các định nghĩa TypeScript (dưới dạng class hoặc interface) từ GraphQL schema, nên bạn không phải viết code boilerplate dư thừa.

<app-banner-courses-graphql-cf></app-banner-courses-graphql-cf>

#### Bắt đầu với GraphQL & TypeScript

> info **Hint** Các chương tiếp theo dùng package `@nestjs/apollo`. Để dùng Mercurius thay vào đó, xem [Tích hợp Mercurius](/graphql/quick-start#mercurius-integration).

Khi đã cài các package, hãy import `GraphQLModule` và cấu hình nó bằng static method `forRoot()`.

[[CODE:2]]

> info **Hint** Với tích hợp Mercurius, hãy dùng `MercuriusDriver` và `MercuriusDriverConfig` thay vào đó. Cả hai đều được export từ package `@nestjs/mercurius`.

Method `forRoot()` nhận một options object, object này được truyền thẳng cho instance của driver bên dưới (xem các thiết lập có sẵn cho [Apollo](https://www.apollographql.com/docs/apollo-server/api/apollo-server) và [Mercurius](https://github.com/mercurius-js/mercurius/blob/master/docs/api/options.md#plugin-options)). Ví dụ, để tắt GraphQL IDE, hãy truyền các tùy chọn sau:

[[CODE:3]]

> warning **Warning** IDE `graphql-playground` đã bị gỡ bỏ trong `@nestjs/graphql` v14. Tùy chọn `playground` chỉ còn lại như một **alias boolean đã deprecated cho GraphiQL**: `playground: false` tắt landing page và `playground: true` bật GraphiQL. Hãy dùng `graphiql` trong code mới.

Với Apollo driver, các tùy chọn này được chuyển tiếp cho constructor của `ApolloServer`.

#### Truy cập object request và response

Tùy chọn `context` là một factory dựng GraphQL execution context cho mỗi request. Hãy dùng nó để đưa các object request và response bên dưới tới resolver của bạn:

[[CODE:4]]

Sau đó bạn có thể đọc chúng trong một resolver bằng decorator `@Context()`:

[[CODE:5]]

> info **Hint** Guard, interceptor và các enhancer khác chạy trong GraphQL context có thể truy cập cùng object đó qua `GqlExecutionContext.create(context).getContext()` (xem [Các tính năng khác](/graphql/other-features)).

#### GraphQL IDE

[GraphiQL](https://github.com/graphql/graphiql) là GraphQL IDE mặc định, dạng đồ họa, tương tác và chạy ngay trong trình duyệt. Nó được phục vụ trên cùng URL với chính GraphQL server, nên bạn cần một GraphQL server cơ bản đã được cấu hình và đang chạy để truy cập nó. Để thử ngay, hãy cài và build [ứng dụng mẫu code first](https://github.com/nestjs/nest/tree/master/sample/23-graphql-code-first). Nếu bạn đang làm theo các đoạn code mẫu này, GraphiQL sẽ có sẵn khi bạn đã hoàn tất các bước trong [chương Resolver](/graphql/resolvers).

Khi ứng dụng đang chạy, hãy mở trình duyệt và truy cập `http://localhost:3000/graphql` (host và port có thể khác tùy cấu hình của bạn). Bạn sẽ thấy GraphiQL, như hình bên dưới.

<figure>
  <img src="/assets/playground.png" alt="" />
</figure>

> info **Note** Tích hợp `@nestjs/mercurius` cũng dùng [GraphiQL](https://github.com/graphql/graphiql).

##### Bật và tắt GraphiQL

Từ `@nestjs/graphql` v14, GraphiQL là GraphQL IDE có sẵn duy nhất; `graphql-playground` cũ đã bị gỡ bỏ. Với Apollo driver, GraphiQL được bật tự động bất cứ khi nào `NODE_ENV` không phải `production`. Trong development, nó hoạt động mà không cần cấu hình gì; trong production, landing page bị tắt mặc định.

Để kiểm soát nó một cách tường minh, hãy dùng tùy chọn `graphiql`:

[[CODE:6]]

[[CODE:7]]

> warning **Warning** Tùy chọn `playground` vẫn tồn tại, nhưng chỉ như một **alias boolean đã deprecated** của `graphiql`. Nếu cả hai đều được đặt, `graphiql` được ưu tiên. Hãy chuyển `playground: false` thành `graphiql: false` và `playground: true` thành `graphiql: true`.

##### Cấu hình GraphiQL

Để bật GraphiQL và cấu hình nó cùng lúc, hãy truyền một object thay vì một boolean:

[[CODE:8]]

Các tùy chọn có sẵn là:

<table>
  <tr>
    <td><code>url</code></td>
    <td>Endpoint mà IDE gửi operation tới. Mặc định là tùy chọn <code>path</code> của driver, nên chỉ đặt nó khi IDE cần nhắm tới một URL khác với URL mà nó được phục vụ.</td>
  </tr>
  <tr>
    <td><code>headers</code></td>
    <td>Các header được áp dụng cho mọi request, ví dụ một header <code>authorization</code> được cấu hình sẵn trong lúc phát triển. Nếu headers editor được bật và người dùng đặt cùng header đó, giá trị của người dùng được ưu tiên.</td>
  </tr>
  <tr>
    <td><code>shouldPersistHeaders</code></td>
    <td>Nội dung của headers editor có được lưu vào storage của trình duyệt hay không. Mặc định: <code>true</code>.</td>
  </tr>
  <tr>
    <td><code>isHeadersEditorEnabled</code></td>
    <td>Headers editor có được hiển thị trong phần công cụ của editor hay không. Đặt thành <code>false</code> để ngăn người dùng sửa header. Mặc định: <code>true</code>.</td>
  </tr>
  <tr>
    <td><code>inputValueDeprecation</code></td>
    <td>Nếu là <code>true</code>, tài liệu schema bao gồm các input field và giá trị argument đã deprecated, và introspection trả về chúng. Mặc định: <code>false</code>.</td>
  </tr>
</table>

> info **Hint** Vì GraphiQL được bật mặc định bên ngoài production, một cách thiết lập phổ biến là giữ nguyên mặc định và chỉ đặt `graphiql: false` cho các môi trường không phải production nhưng có thể truy cập công khai, nơi IDE không nên bị lộ ra.

##### Subscription trong IDE

Nếu ứng dụng của bạn dùng [subscription](/graphql/subscriptions), hãy dùng `graphql-ws`. Hỗ trợ cho `subscriptions-transport-ws` đã bị **gỡ bỏ**: nó không còn được chấp nhận làm key của `subscriptions`, và package này cũng không còn là dependency.

[[CODE:9]]

Khi đó GraphiQL có thể thực thi trực tiếp các subscription operation với server của bạn.

#### Code first

Với cách tiếp cận **code first**, bạn dùng decorator và các class TypeScript để sinh ra GraphQL schema tương ứng.

Để dùng cách tiếp cận code first, hãy bắt đầu bằng việc thêm thuộc tính `autoSchemaFile` vào options object:

[[CODE:10]]

Giá trị của thuộc tính `autoSchemaFile` là đường dẫn nơi schema được sinh tự động sẽ được ghi ra. Ngoài ra, schema có thể được sinh ngay trong bộ nhớ. Để làm vậy, hãy đặt thuộc tính `autoSchemaFile` thành `true`:

[[CODE:11]]

Mặc định, các type trong schema được sinh ra xuất hiện theo thứ tự chúng được định nghĩa trong các module được bao gồm. Để sắp xếp schema theo thứ tự từ điển, hãy đặt thuộc tính `sortSchema` thành `true`:

[[CODE:12]]

#### Ví dụ

Một [ví dụ code first](https://github.com/nestjs/nest/tree/master/sample/23-graphql-code-first) chạy được hoàn chỉnh có sẵn trong repository của NestJS.

#### Schema first

Để dùng cách tiếp cận schema first, hãy bắt đầu bằng việc thêm thuộc tính `typePaths` vào options object. Thuộc tính `typePaths` cho `GraphQLModule` biết nơi tìm các file định nghĩa schema GraphQL SDL mà bạn sẽ viết. Các file này được gộp lại trong bộ nhớ, nên bạn có thể chia schema thành nhiều file và đặt chúng cạnh resolver của chúng.

[[CODE:13]]

Thông thường bạn cũng sẽ cần các định nghĩa TypeScript (class và interface) tương ứng với các type GraphQL SDL. Viết chúng bằng tay vừa dư thừa vừa tẻ nhạt, và khiến bạn không có một nguồn sự thật duy nhất: mỗi thay đổi trong SDL buộc bạn phải cập nhật cả các định nghĩa TypeScript. Để giải quyết điều này, package `@nestjs/graphql` có thể **tự động sinh** các định nghĩa TypeScript từ cây cú pháp trừu tượng ([AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree)). Để bật tính năng này, hãy thêm thuộc tính `definitions` khi cấu hình `GraphQLModule`.

[[CODE:14]]

Thuộc tính `path` của object `definitions` chỉ định nơi lưu output TypeScript được sinh ra. Mặc định, mọi type TypeScript được sinh ra đều là interface. Để sinh class thay vào đó, hãy đặt thuộc tính `outputAs` thành `'class'`.

[[CODE:15]]

Cách này sinh các định nghĩa TypeScript mỗi khi ứng dụng khởi động. Ngoài ra, bạn có thể viết một script sinh chúng khi cần. Ví dụ, tạo script `generate-typings.ts` sau:

[[CODE:16]]

Giờ bạn có thể chạy script này khi cần:

[[CODE:17]]

> info **Hint** Bạn có thể biên dịch script trước (ví dụ bằng `tsc`) và dùng `node` để chạy nó.

Để bật watch mode cho script (sinh lại typing mỗi khi một file `.graphql` thay đổi), hãy truyền tùy chọn `watch` cho method `generate()`.

[[CODE:18]]

Để sinh thêm một field `__typename` cho mọi object type, hãy bật tùy chọn `emitTypenameField`:

[[CODE:19]]

Để sinh các resolver (query, mutation, subscription) dưới dạng field thuần không có argument, hãy bật tùy chọn `skipResolverArgs`:

[[CODE:20]]

Để sinh enum dưới dạng union type của TypeScript thay vì enum TypeScript thông thường, hãy đặt tùy chọn `enumsAsTypes` thành `true`:

[[CODE:21]]

#### Apollo Sandbox

Để dùng [Apollo Sandbox](https://www.apollographql.com/blog/announcement/platform/apollo-sandbox-an-open-graphql-ide-for-local-development/) thay cho GraphiQL làm GraphQL IDE khi phát triển ở local, hãy dùng cấu hình sau:

[[CODE:22]]

#### Ví dụ

Một [ví dụ schema first](https://github.com/nestjs/nest/tree/master/sample/12-graphql-schema-first) chạy được hoàn chỉnh có sẵn trong repository của NestJS.

#### Truy cập schema được sinh ra

Trong một số tình huống, bạn có thể muốn có một tham chiếu tới schema object được sinh ra. Ví dụ, trong các test end-to-end, khi đó bạn có thể chạy query trực tiếp bằng package `graphql`, không cần HTTP listener nào.

Bạn có thể truy cập schema được sinh ra (ở cả cách tiếp cận code first lẫn schema first) bằng class `GraphQLSchemaHost`:

[[CODE:23]]

> info **Hint** Bạn phải gọi getter `GraphQLSchemaHost#schema` sau khi ứng dụng đã được khởi tạo (sau khi hook `onModuleInit` đã được kích hoạt bởi method `app.listen()` hoặc `app.init()`).

#### Cấu hình bất đồng bộ

Khi bạn cần truyền tùy chọn cho module một cách bất đồng bộ thay vì tĩnh, hãy dùng method `forRootAsync()`. Như với hầu hết các dynamic module, Nest cung cấp nhiều kỹ thuật cho cấu hình bất đồng bộ.

Một kỹ thuật là dùng một factory function:

[[CODE:24]]

Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, factory function có thể là async và có thể inject dependency qua `inject`.

[[CODE:25]]

Ngoài ra, bạn có thể cấu hình `GraphQLModule` bằng một class thay vì một factory, như bên dưới:

[[CODE:26]]

Cấu trúc ở trên khởi tạo `GqlConfigService` bên trong `GraphQLModule` và dùng nó để tạo options object. `GqlConfigService` phải implement interface `GqlOptionsFactory`, như bên dưới. `GraphQLModule` gọi method `createGqlOptions()` trên object được khởi tạo từ class được cung cấp.

[[CODE:27]]

Để tái sử dụng một options provider đã có thay vì tạo một bản sao riêng bên trong `GraphQLModule`, hãy dùng cú pháp `useExisting`.

[[CODE:28]]

#### Tích hợp Mercurius

Thay vì Apollo, người dùng [Fastify](/http/performance#fastify-adapter) có thể dùng driver `@nestjs/mercurius`.

[[CODE:29]]

> info **Hint** Khi ứng dụng đang chạy, hãy mở trình duyệt và truy cập `http://localhost:3000/graphiql` để xem [GraphiQL IDE](https://github.com/graphql/graphiql).

Method `forRoot()` nhận một options object, object này được truyền thẳng cho instance của driver bên dưới. Xem [tùy chọn plugin của Mercurius](https://github.com/mercurius-js/mercurius/blob/master/docs/api/options.md#plugin-options) để biết các thiết lập có sẵn.

#### Nhiều endpoint

Module `@nestjs/graphql` cũng có thể phục vụ nhiều endpoint cùng lúc, và bạn quyết định module nào được bao gồm trong endpoint nào. Mặc định, `GraphQLModule` tìm resolver trong toàn bộ ứng dụng. Để giới hạn việc quét này trong một tập con các module, hãy dùng thuộc tính `include`.

[[CODE:30]]

Với cách tiếp cận **code first**, tùy chọn `include` chỉ quyết định những module nào được quét để tìm resolver. Các type được gắn `@ObjectType()`, `@InputType()`, `@InterfaceType()`, `@ArgsType()`, hoặc được đăng ký qua `registerEnumType()` / `createUnionType()` vẫn có mặt trong mọi schema được sinh ra. Để giới hạn một type vào một module cụ thể, hãy dùng tùy chọn `registerIn`:

[[CODE:31]]

Khi một schema được dựng với `include: [CatsModule]`, chỉ những type được gán cho `CatsModule` mới trở thành một phần của nó, còn các type được gán cho module khác bị loại ra. Các type không có `registerIn` giữ hành vi mặc định và có mặt trong mọi schema tham chiếu tới chúng.

Tùy chọn `registerIn` có sẵn trên `@InputType()`, `@InterfaceType()` và `@ArgsType()`, cũng như `registerEnumType()` và `createUnionType()`:

[[CODE:32]]

> info **Hint** Bạn có thể truyền chính class module hoặc một factory function trả về nó. Hãy ưu tiên dạng factory (`() => CatsModule`) bất cứ khi nào type và module tham chiếu lẫn nhau: nó trì hoãn việc resolve module và tránh các lỗi do circular import gây ra.

#### Tích hợp bên thứ ba

- [GraphQL Yoga](https://github.com/dotansimha/graphql-yoga)

#### Ví dụ

Một [ví dụ Mercurius](https://github.com/nestjs/nest/tree/master/sample/33-graphql-mercurius) chạy được có sẵn trong repository của NestJS.
