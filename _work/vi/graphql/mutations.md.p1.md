### Mutation

Phần lớn các cuộc thảo luận về GraphQL tập trung vào việc lấy dữ liệu, nhưng bất kỳ nền tảng dữ liệu hoàn chỉnh nào cũng cần một cách để thay đổi dữ liệu phía server. Trong REST, bất kỳ request nào cũng có thể gây side effect trên server, nhưng best practice là không thay đổi dữ liệu trong request `GET`. GraphQL cũng tương tự: về mặt kỹ thuật, bất kỳ query nào cũng có thể được hiện thực để ghi dữ liệu. Tuy nhiên, như với REST, quy ước là gửi mọi operation gây ra thao tác ghi một cách tường minh dưới dạng mutation (xem [Mutation](https://graphql.org/learn/queries/#mutations) trong tài liệu GraphQL).

[Tài liệu Apollo](https://www.apollographql.com/docs/graphql-tools/generate-schema.html) chính thức dùng ví dụ một mutation `upvotePost()`, tăng thuộc tính `votes` của một bài viết. Để tạo một mutation tương đương trong Nest, hãy dùng decorator `@Mutation()`.

#### Code first

Thêm một method khác vào `AuthorsResolver` từ chương [Resolver](/graphql/resolvers).

[[CODE:1]]

> info **Hint** Mọi decorator (ví dụ `@Resolver`, `@ResolveField`, `@Args`, v.v.) đều được export từ package `@nestjs/graphql`.

Nó sinh ra phần sau của GraphQL schema bằng SDL:

[[CODE:2]]

Method `upvotePost()` nhận `postId` (`Int`) làm argument và trả về entity `Post` đã được cập nhật. Vì những lý do đã giải thích trong chương [Resolver](/graphql/resolvers), bạn phải đặt type mong muốn một cách tường minh.

Nếu mutation cần nhận một object làm argument, hãy tạo một **input type**. Input type là một loại object type đặc biệt có thể được truyền vào làm argument (xem [Input type](https://graphql.org/learn/schema/#input-types) trong tài liệu GraphQL). Để khai báo một input type, hãy dùng decorator `@InputType()`.

[[CODE:3]]

> info **Hint** Decorator `@InputType()` nhận một options object làm tham số, nên bạn có thể, chẳng hạn, chỉ định mô tả cho input type. Do những hạn chế của hệ thống metadata reflection của TypeScript, bạn phải dùng decorator `@Field()` để chỉ ra type, hoặc dùng [CLI plugin](/graphql/cli-plugin).

Sau đó bạn có thể dùng type này trong class resolver:

[[CODE:4]]

#### Query trong payload của mutation

Payload của một mutation có thể đưa ra root type `Query`, để client có thể lấy lại bất kỳ dữ liệu nào sau một mutation chỉ trong một vòng request. Với cách tiếp cận code first, hãy tham chiếu tới root type được sinh ra theo tên của nó:

[[CODE:5]]

Bất kỳ giá trị nào cũng dùng được làm giá trị `query` (một object rỗng là đủ), vì các root query resolver không phụ thuộc vào parent của chúng. Với cách tiếp cận schema first, hãy khai báo `query: Query!` trên payload type trong SDL của bạn.

#### Schema first

Mở rộng `AuthorsResolver` từ chương [Resolver](/graphql/resolvers).

[[CODE:6]]

Ví dụ này giả định rằng logic nghiệp vụ (truy vấn bài viết và tăng thuộc tính `votes` của nó) nằm trong `PostsService`. Logic đó có thể đơn giản hoặc phức tạp tùy nhu cầu. Mục đích của ví dụ này là cho thấy cách resolver tương tác với các provider khác.

Bước cuối cùng là thêm mutation vào các định nghĩa type đã có.

[[CODE:7]]

Mutation `upvotePost(postId: Int!): Post` giờ đã là một phần của GraphQL API của ứng dụng.
