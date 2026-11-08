### Các tính năng khác

Trong thế giới GraphQL, có rất nhiều tranh luận về cách xử lý những vấn đề như **xác thực** hay **side effect** của các operation. Có người xử lý chúng bên trong logic nghiệp vụ, có người dùng higher-order function để bổ sung logic phân quyền cho query và mutation, và có người dùng [schema directive](https://www.apollographql.com/docs/apollo-server/schema/directives/). Không có câu trả lời nào phù hợp cho mọi trường hợp.

Nest giúp giải quyết những vấn đề này bằng các tính năng đa nền tảng của nó, như [guard](/guards) và [interceptor](/interceptors). Mục tiêu là giảm sự dư thừa và cung cấp công cụ giúp bạn tạo ra các ứng dụng có cấu trúc tốt, dễ đọc và nhất quán.

#### Tổng quan

Bạn có thể dùng [guard](/guards), [interceptor](/interceptors), [filter](/exception-filters) và [pipe](/pipes) tiêu chuẩn với GraphQL giống như với bất kỳ ứng dụng RESTful nào. Bạn cũng có thể tự tạo decorator bằng tính năng [custom decorator](/custom-decorators). Xét GraphQL query handler sau:

[[CODE:1]]

GraphQL làm việc với guard và pipe giống như các HTTP REST handler. Điều này có nghĩa là bạn có thể chuyển logic xác thực sang một guard, và thậm chí tái sử dụng cùng class guard giữa REST API và GraphQL API. Interceptor hoạt động theo cùng cách ở cả hai loại ứng dụng:

[[CODE:2]]

#### Execution context

Vì GraphQL nhận một loại dữ liệu khác trong request đi vào, [execution context](/fundamentals/execution-context) mà guard và interceptor nhận được ở GraphQL khác với ở REST. GraphQL resolver có một tập argument riêng: `root`, `args`, `context` và `info`. Vì vậy, guard và interceptor phải chuyển `ExecutionContext` chung thành một `GqlExecutionContext`:

[[CODE:3]]

Object được trả về bởi `GqlExecutionContext.create()` cung cấp một method **get** cho mỗi argument của GraphQL resolver (ví dụ `getArgs()`, `getContext()`, v.v.). Khi đã chuyển đổi context, bạn có thể lấy ra bất kỳ argument GraphQL nào của request hiện tại.

#### Exception filter

Các [exception filter](/exception-filters) tiêu chuẩn của Nest cũng tương thích với ứng dụng GraphQL. Giống như với `ExecutionContext`, ứng dụng GraphQL nên chuyển object `ArgumentsHost` thành một object `GqlArgumentsHost`:

[[CODE:4]]

> info **Hint** Cả `GqlExceptionFilter` và `GqlArgumentsHost` đều được import từ package `@nestjs/graphql`.

Khác với trường hợp REST, bạn không dùng object `response` gốc để tạo response.

#### Custom decorator

Như đã đề cập, tính năng [custom decorator](/custom-decorators) hoạt động đúng như mong đợi với GraphQL resolver:

[[CODE:5]]

Dùng custom decorator `@User()` như sau:

[[CODE:6]]

> info **Hint** Ví dụ ở trên giả định rằng object `user` đã được gán vào context của ứng dụng GraphQL.

#### Thực thi enhancer ở cấp field resolver

Trong GraphQL context, mặc định Nest không chạy **enhancer** (tên gọi chung cho interceptor, guard và filter) ở cấp field (xem [GitHub issue này](https://github.com/nestjs/graphql/issues/320#issuecomment-511193229)): chúng chỉ chạy cho method `@Query()`/`@Mutation()` cấp cao nhất. Để Nest thực thi interceptor, guard hoặc filter cho các method được chú thích bằng `@ResolveField()`, hãy đặt tùy chọn `fieldResolverEnhancers` trong `GqlModuleOptions`. Truyền cho nó một danh sách gồm `'interceptors'`, `'guards'` và/hoặc `'filters'` tùy trường hợp:

[[CODE:7]]

> warning **Warning** Bật enhancer cho field resolver có thể gây vấn đề về hiệu năng khi bạn trả về nhiều bản ghi và field resolver của bạn chạy hàng nghìn lần. Vì lý do này, khi bật `fieldResolverEnhancers`, hãy bỏ qua những enhancer không thực sự cần thiết cho field resolver. Bạn có thể làm điều này với hàm helper sau:

[[CODE:8]]

#### Tạo một custom driver

Nest cung cấp sẵn hai driver chính thức, `@nestjs/apollo` và `@nestjs/mercurius`, cùng với một API để xây dựng các **custom driver** mới. Với một custom driver, bạn có thể tích hợp bất kỳ library GraphQL nào, hoặc mở rộng một tích hợp đã có với các tính năng bổ sung.

Ví dụ, để tích hợp package [`graphql-http`](https://github.com/graphql/graphql-http), bạn có thể tạo class driver sau. Tới lúc `start()` được gọi, Nest đã sinh xong schema và truyền nó trong thuộc tính `schema` của options object:

[[CODE:9]]

Rồi dùng nó như sau:

[[CODE:10]]
