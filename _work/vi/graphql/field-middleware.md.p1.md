### Field middleware

> warning **Warning** Chương này chỉ áp dụng cho cách tiếp cận code first.

Field middleware cho phép bạn chạy code tùy ý **trước hoặc sau** khi một field được resolve. Bạn có thể dùng field middleware để chuyển đổi kết quả của một field, validate các argument của một field, hoặc kiểm tra role ở cấp field (ví dụ các role cần có để truy cập field mà middleware function đang chạy cho nó).

Bạn có thể gắn nhiều middleware function vào một field. Trong trường hợp này, chúng được gọi tuần tự theo một chuỗi, trong đó mỗi middleware quyết định có gọi middleware tiếp theo hay không. Thứ tự của các hàm trong mảng `middleware` là quan trọng. Hàm đầu tiên là lớp ngoài cùng, nên nó chạy đầu tiên và kết thúc sau cùng (tương tự package `graphql-middleware`). Hàm thứ hai là lớp bên trong tiếp theo, nên nó chạy thứ hai và kết thúc áp chót.

#### Bắt đầu

Hãy bắt đầu bằng việc tạo một middleware đơn giản log giá trị của một field trước khi nó được gửi trả về client:

[[CODE:1]]

> info **Hint** `MiddlewareContext` là một object gồm các tham số giống hệt những gì mà GraphQL resolver function thường nhận (`{{ '{' }} source, args, context, info {{ '}' }}`), còn `NextFn` là một hàm thực thi middleware tiếp theo trong stack (gắn với field này) hoặc field resolver thực sự.

> warning **Warning** Field middleware function không thể inject dependency hay truy cập DI container của Nest. Chúng được thiết kế để gọn nhẹ và không nên thực hiện các thao tác có thể tốn thời gian (như lấy dữ liệu từ database). Nếu bạn cần gọi service bên ngoài hoặc truy vấn một nguồn dữ liệu, hãy làm việc đó trong một guard hoặc interceptor gắn với một root query hoặc mutation handler, và gán kết quả vào object `context`. Sau đó bạn có thể truy cập nó từ bên trong field middleware (qua object `MiddlewareContext`).

Field middleware phải khớp với interface `FieldMiddleware`. Trong ví dụ ở trên, trước tiên chúng ta gọi hàm `next()` (hàm này thực thi field resolver thực sự và trả về giá trị của field), rồi log giá trị đó ra terminal. Giá trị trả về từ middleware function sẽ thay thế giá trị của field (nếu middleware trả về `undefined`, giá trị từ `next()` sẽ được dùng). Vì chúng ta không muốn thay đổi gì, chúng ta trả về giá trị gốc.

Khi đã có middleware này, hãy đăng ký nó trực tiếp trong decorator `@Field()`:

[[CODE:2]]

Giờ, mỗi khi bạn request field `title` của object type `Recipe`, giá trị gốc của field sẽ được log ra console.

> info **Hint** Để tìm hiểu cách hiện thực một hệ thống phân quyền ở cấp field bằng tính năng [extension](/graphql/extensions), xem [dùng custom metadata](/graphql/extensions#using-custom-metadata).

> warning **Warning** Field middleware chỉ có thể được áp dụng cho các class `ObjectType`. Để biết thêm chi tiết, xem [GitHub issue này](https://github.com/nestjs/graphql/issues/2446).

Như đã đề cập ở trên, bạn có thể kiểm soát giá trị của field từ bên trong middleware function. Để minh họa, hãy viết hoa tiêu đề của một công thức (nếu có):

[[CODE:3]]

Trong trường hợp này, mọi tiêu đề đều được tự động viết hoa khi được request.

Tương tự, bạn có thể gắn field middleware vào một custom field resolver (một method được chú thích bằng decorator `@ResolveField()`):

[[CODE:4]]

> warning **Warning** Nếu enhancer được bật ở cấp field resolver (xem [thực thi enhancer ở cấp field resolver](/graphql/other-features#execute-enhancers-at-the-field-resolver-level)), field middleware function sẽ chạy trước mọi interceptor, guard, v.v. **gắn với method** (nhưng sau các enhancer cấp root được đăng ký cho query hoặc mutation handler).

#### Áp dụng middleware bằng decorator

Ngoài ra, hãy áp dụng field middleware bằng decorator `@UseFieldMiddleware()`. Nó dùng được trên cả field lẫn field resolver, và có thể đặt phía trên hoặc phía dưới decorator `@Field()` hay `@ResolveField()`:

[[CODE:5]]

Vì nó là một decorator riêng, bạn có thể kết hợp nó với các decorator khác trong một decorator tổng hợp:

[[CODE:6]]

#### Global field middleware

Ngoài việc gắn middleware trực tiếp vào một field cụ thể, bạn có thể đăng ký một hoặc nhiều middleware function ở phạm vi global. Middleware global được tự động gắn vào mọi field của các object type.

[[CODE:7]]

> info **Hint** Các field middleware function được đăng ký global chạy **trước** các middleware được đăng ký cục bộ. Middleware cục bộ được truyền qua tùy chọn `middleware` của `@Field()` hoặc `@ResolveField()` chạy trước middleware được áp dụng bằng `@UseFieldMiddleware()`, loại này chạy theo thứ tự được chỉ định (khi decorator được xếp chồng, decorator thấp nhất chạy trước, giống như `@UseGuards()`).
