### Directive

Một directive có thể được gắn vào một field hoặc một lần include fragment, và có thể ảnh hưởng tới việc thực thi query theo bất kỳ cách nào server muốn (xem [directive](https://graphql.org/learn/queries/#directives) trong tài liệu GraphQL). Đặc tả GraphQL cung cấp sẵn một số directive mặc định:

- `@include(if: Boolean)`: chỉ đưa field này vào kết quả nếu argument là `true`
- `@skip(if: Boolean)`: bỏ qua field này nếu argument là `true`
- `@deprecated(reason: String)`: đánh dấu field là deprecated, kèm một message

Một directive là một định danh đứng sau ký tự `@`, có thể theo sau là một danh sách argument có tên. Directive có thể xuất hiện sau gần như mọi thành phần trong ngôn ngữ query và schema của GraphQL.

#### Custom directive

Để định nghĩa điều gì xảy ra khi Apollo hoặc Mercurius gặp directive của bạn, hãy tạo một hàm transformer. Hàm này dùng hàm `mapSchema` để duyệt qua các vị trí trong schema (định nghĩa field, định nghĩa type, v.v.) và áp dụng các biến đổi tương ứng.

[[CODE:1]]

Tiếp theo, áp dụng hàm `upperDirectiveTransformer` trong method `GraphQLModule#forRoot()` bằng tùy chọn `transformSchema`:

[[CODE:2]]

Khi đã đăng ký, directive `@upper` có thể được dùng trong schema của bạn. Cách bạn áp dụng directive phụ thuộc vào cách tiếp cận bạn dùng (code first hay schema first).

#### Code first

Với cách tiếp cận code first, hãy dùng decorator `@Directive()` để áp dụng directive:

[[CODE:3]]

> info **Hint** Decorator `@Directive()` được export từ package `@nestjs/graphql`.

Directive có thể được áp dụng cho field, field resolver, input type và object type, cũng như query, mutation và subscription. Ví dụ sau áp dụng một directive ở cấp query handler:

[[CODE:4]]

> warning **Warning** Các directive được áp dụng qua decorator `@Directive()` không được phản ánh trong file định nghĩa schema được sinh ra.

Cuối cùng, khai báo các directive trong cấu hình `GraphQLModule`:

[[CODE:5]]

> info **Hint** Cả `GraphQLDirective` và `DirectiveLocation` đều được export từ package `graphql`.

#### Schema first

Với cách tiếp cận schema first, hãy áp dụng directive trực tiếp trong SDL:

[[CODE:6]]
