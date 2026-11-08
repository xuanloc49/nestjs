### Custom route decorator

Nest được xây dựng quanh một tính năng ngôn ngữ gọi là **decorator**. Decorator đã rất phổ biến trong nhiều ngôn ngữ lập trình nhưng vẫn còn tương đối mới với JavaScript. Để hiểu sâu hơn cách decorator hoạt động, xem [bài viết này](https://medium.com/google-developers/exploring-es7-decorators-76ecb65fb841). Đây là một định nghĩa đơn giản:

<blockquote class="external">
  Decorator ES2016 là một biểu thức trả về một hàm và có thể nhận target, name và property descriptor làm tham số.
  Bạn áp dụng nó bằng cách đặt ký tự <code>@</code> trước decorator và đặt nó ngay trên cùng của thứ
  bạn muốn decorate. Decorator có thể được định nghĩa cho class, method hoặc property.
</blockquote>

#### Param decorator

Nest cung cấp một bộ **param decorator** mà bạn có thể dùng trong HTTP route handler. Bảng sau liệt kê chúng cùng với các object Express (hoặc Fastify) thuần mà chúng đại diện:

<table>
  <tbody>
    <tr>
      <td><code>@Request(), @Req()</code></td>
      <td><code>req</code></td>
    </tr>
    <tr>
      <td><code>@Response(), @Res()</code></td>
      <td><code>res</code></td>
    </tr>
    <tr>
      <td><code>@Next()</code></td>
      <td><code>next</code></td>
    </tr>
    <tr>
      <td><code>@Session()</code></td>
      <td><code>req.session</code></td>
    </tr>
    <tr>
      <td><code>@Param(param?: string)</code></td>
      <td><code>req.params</code> / <code>req.params[param]</code></td>
    </tr>
    <tr>
      <td><code>@Body(param?: string)</code></td>
      <td><code>req.body</code> / <code>req.body[param]</code></td>
    </tr>
    <tr>
      <td><code>@Query(param?: string)</code></td>
      <td><code>req.query</code> / <code>req.query[param]</code></td>
    </tr>
    <tr>
      <td><code>@Headers(param?: string)</code></td>
      <td><code>req.headers</code> / <code>req.headers[param]</code></td>
    </tr>
    <tr>
      <td><code>@Ip()</code></td>
      <td><code>req.ip</code></td>
    </tr>
    <tr>
      <td><code>@HostParam(param?: string)</code></td>
      <td><code>req.hosts</code> / <code>req.hosts[param]</code></td>
    </tr>
  </tbody>
</table>

Bạn cũng có thể tạo **custom decorator** của riêng mình. Để thấy vì sao điều này hữu ích, hãy xét một pattern phổ biến trong các ứng dụng Node.js: các thuộc tính được gắn vào object **request**, rồi được lấy ra thủ công trong từng route handler, với code kiểu như sau:

[[CODE:1]]

Để code dễ đọc và rõ ràng hơn, bạn có thể tạo một decorator `@User()` và dùng lại nó trong tất cả các controller:

[[CODE:2]]

Sau đó bạn có thể dùng nó ở bất cứ đâu cần:

[[CODE:3]]

#### Truyền dữ liệu

Khi hành vi của decorator phụ thuộc vào một điều kiện nào đó, hãy dùng tham số `data` để truyền tham số vào hàm factory của decorator. Một ví dụ là custom decorator lấy một thuộc tính từ request object theo key. Giả sử [lớp xác thực](/security/authentication#read-the-current-user) của bạn validate request và gắn một entity người dùng vào request object. Entity người dùng của một request đã xác thực có thể trông như sau:

[[CODE:4]]

Hãy định nghĩa một decorator nhận tên thuộc tính làm key và trả về giá trị tương ứng nếu có (hoặc `undefined` nếu không có, hoặc nếu object `user` chưa được tạo):

[[CODE:5]]

Sau đó bạn có thể truy cập một thuộc tính cụ thể thông qua decorator `@User()` trong controller:

[[CODE:6]]

Bạn có thể dùng cùng một decorator với các key khác nhau để truy cập các thuộc tính khác nhau. Nếu object `user` lồng sâu hoặc phức tạp, cách này giúp phần implement route handler đơn giản và dễ đọc hơn.

> info **Hint** `createParamDecorator<T>()` là generic, nên bạn có thể ép kiểu an toàn một cách tường minh, ví dụ `createParamDecorator<string>((data, ctx) => ...)`. Cách khác là chỉ định type tham số trong hàm factory, ví dụ `createParamDecorator((data: string, ctx) => ...)`. Nếu bỏ qua cả hai, `data` sẽ có type `any`.

#### Làm việc với pipe

Nest xử lý các custom param decorator giống hệt như các decorator có sẵn (`@Body()`, `@Param()` và `@Query()`). Điều này có nghĩa là pipe cũng chạy cho các tham số được đánh dấu bằng custom decorator (trong ví dụ của chúng ta là tham số `user`). Bạn cũng có thể áp dụng pipe trực tiếp lên custom decorator:

[[CODE:7]]

> info **Hint** Mặc định, `ValidationPipe` không validate các tham số được đánh dấu bằng custom decorator. Đó là lý do ví dụ trên đặt tùy chọn `validateCustomDecorators` thành `true`.

Custom decorator cũng nhận tùy chọn `schema` giống các decorator tham số có sẵn. Truyền vào một schema tương thích [Standard Schema](https://standardschema.dev/), như schema của Zod, và một `StandardSchemaValidationPipe` có bật tùy chọn `validateCustomDecorators` sẽ validate giá trị của decorator theo schema đó:

[[CODE:8]]

Xem [Validate custom decorator](/application/validation#validating-custom-decorators) để biết chi tiết.

#### Kết hợp decorator

Nest cung cấp helper `applyDecorators()` để kết hợp nhiều decorator. Ví dụ, giả sử bạn muốn gộp tất cả các decorator liên quan đến xác thực vào một decorator duy nhất:

[[CODE:9]]

Sau đó bạn có thể dùng custom decorator `@Auth()` này như sau:

[[CODE:10]]

Cách này áp dụng cả bốn decorator chỉ với một khai báo.

> warning **Warning** Decorator `@ApiHideProperty()` của package `@nestjs/swagger` không kết hợp được và không hoạt động đúng với hàm `applyDecorators()`.
