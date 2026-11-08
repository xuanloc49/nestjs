### Interface

Như nhiều hệ thống type khác, GraphQL hỗ trợ interface. Một **interface** là một type trừu tượng định nghĩa một tập các field mà một type phải có để implement interface đó (xem [interface](https://graphql.org/learn/schema/#interfaces) trong tài liệu GraphQL).

#### Code first

Với cách tiếp cận code first, bạn định nghĩa một GraphQL interface bằng cách tạo một abstract class được chú thích bằng decorator `@InterfaceType()`, được export từ package `@nestjs/graphql`.

[[CODE:1]]

> warning **Warning** Không thể dùng interface của TypeScript để định nghĩa GraphQL interface.

Nó sinh ra phần sau của GraphQL schema bằng SDL:

[[CODE:2]]

Để implement interface `Character`, hãy dùng key `implements`:

[[CODE:3]]

> info **Hint** Decorator `@ObjectType()` được export từ package `@nestjs/graphql`.

Hàm `resolveType()` mặc định do library sinh ra xác định type dựa trên giá trị trả về từ method resolver. Điều này có nghĩa là bạn phải trả về instance của class, chứ không phải object literal JavaScript thuần.

Để cung cấp một hàm `resolveType()` tùy chỉnh, hãy truyền thuộc tính `resolveType` trong options object của decorator `@InterfaceType()`:

[[CODE:4]]

#### Interface resolver

Cho tới giờ, interface chỉ cho phép bạn dùng chung định nghĩa field với các object. Để dùng chung cả phần hiện thực field resolver, hãy tạo một interface resolver riêng:

[[CODE:5]]

Field resolver `friends` giờ được tự động đăng ký cho mọi object type implement interface `Character`.

> warning **Warning** Việc này yêu cầu đặt thuộc tính `inheritResolversFromInterfaces` thành `true` trong cấu hình `GraphQLModule`.

#### Schema first

Để định nghĩa một interface theo cách tiếp cận schema first, hãy tạo một GraphQL interface bằng SDL:

[[CODE:6]]

Sau đó, bạn có thể dùng tính năng sinh typing (như trong chương [Bắt đầu nhanh với GraphQL](/graphql/quick-start)) để sinh các định nghĩa TypeScript tương ứng:

[[CODE:7]]

Interface cần thêm một field `__resolveType` trong resolver map để xác định interface resolve ra type nào. Hãy tạo một class `CharactersResolver` và định nghĩa method `__resolveType`, method này trả về tên của type cụ thể:

[[CODE:8]]

> info **Hint** Mọi decorator đều được export từ package `@nestjs/graphql`.
