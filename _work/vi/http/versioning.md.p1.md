### Versioning

> info **Hint** Chương này chỉ áp dụng cho ứng dụng dựa trên HTTP.

Versioning cho phép bạn chạy **nhiều phiên bản khác nhau** của controller hoặc của từng route trong cùng một ứng dụng. Ứng dụng thay đổi thường xuyên, và bạn thường cần đưa vào những thay đổi phá vỡ tương thích (breaking change) trong khi vẫn phải hỗ trợ phiên bản trước đó.

Nest hỗ trợ bốn kiểu versioning:

<table>
  <tr>
    <td><a href='http/versioning#uri-versioning-type'><code>URI Versioning</code></a></td>
    <td>Version được truyền trong URI của request (mặc định)</td>
  </tr>
  <tr>
    <td><a href='http/versioning#header-versioning-type'><code>Header Versioning</code></a></td>
    <td>Một header tùy chỉnh của request chỉ định version</td>
  </tr>
  <tr>
    <td><a href='http/versioning#media-type-versioning-type'><code>Media Type Versioning</code></a></td>
    <td>Header <code>Accept</code> của request chỉ định version</td>
  </tr>
  <tr>
    <td><a href='http/versioning#custom-versioning-type'><code>Custom Versioning</code></a></td>
    <td>Bất kỳ phần nào của request cũng có thể chỉ định (các) version. Bạn cung cấp một hàm tùy chỉnh để lấy (các) version ra.</td>
  </tr>
</table>

#### Kiểu URI Versioning

URI Versioning dùng version truyền trong URI của request, như `https://example.com/v1/route` và `https://example.com/v2/route`.

> warning **Notice** Với URI Versioning, version được tự động thêm vào URI sau <a href="faq/global-prefix">global path prefix</a> (nếu có) và trước mọi path của controller hay route.

Để bật URI Versioning cho ứng dụng, làm như sau:

[[CODE:1]]

> warning **Notice** Mặc định, version trong URI được tự động thêm prefix `v`. Để đổi prefix, hãy đặt key `prefix` thành giá trị mong muốn, hoặc đặt nó thành `false` để tắt.

> info **Hint** Enum `VersioningType` có sẵn để dùng cho thuộc tính `type` và được import từ package `@nestjs/common`.

#### Kiểu Header Versioning

Header Versioning dùng một header tùy chỉnh do người dùng chỉ định, với giá trị của header cho biết version cần dùng cho request.

Để bật **Header Versioning** cho ứng dụng, làm như sau:

[[CODE:2]]

Thuộc tính `header` là tên của header chứa version của request.

> info **Hint** Enum `VersioningType` có sẵn để dùng cho thuộc tính `type` và được import từ package `@nestjs/common`.

#### Kiểu Media Type Versioning

Media Type Versioning dùng header `Accept` của request để chỉ định version.

Trong header `Accept`, version được tách khỏi media type bằng dấu chấm phẩy (`;`), theo sau là một cặp key-value biểu diễn version cần dùng cho request, như `Accept: application/json;v=2`. Key được xem là prefix của version, nên thuộc tính `key` phải bao gồm cả key lẫn dấu phân cách.

Để bật **Media Type Versioning** cho ứng dụng, làm như sau:

[[CODE:3]]

Thuộc tính `key` là key và dấu phân cách của cặp key-value chứa version. Với `Accept: application/json;v=2`, hãy đặt thuộc tính `key` là `v=`.

> info **Hint** Enum `VersioningType` có sẵn để dùng cho thuộc tính `type` và được import từ package `@nestjs/common`.

#### Kiểu Custom Versioning

Custom Versioning dùng bất kỳ phần nào của request để chỉ định version (hoặc nhiều version). Nest phân tích request gửi đến bằng một hàm `extractor` trả về một chuỗi hoặc một mảng chuỗi.

Nếu bên gửi request cung cấp nhiều version, hàm extractor có thể trả về một mảng chuỗi được sắp xếp từ version cao nhất tới thấp nhất. Các version được so khớp với route theo thứ tự từ cao nhất tới thấp nhất.

Nếu `extractor` trả về chuỗi rỗng hoặc mảng rỗng, không route có version nào được khớp, nên request tới một route như vậy sẽ nhận response status `404`. Các route [`VERSION_NEUTRAL`](/http/versioning#version-neutral) vẫn khớp, cũng như các route không chỉ định version khi không đặt [version mặc định global](/http/versioning#global-default-version).

Ví dụ, nếu một request gửi đến cho biết nó hỗ trợ các version `1`, `2` và `3`, `extractor` **phải** trả về `['3', '2', '1']`. Điều này đảm bảo version route cao nhất có thể được chọn trước.

Nếu các version `['3', '2', '1']` được lấy ra, nhưng chỉ có route cho version `2` và `1`, route khớp với version `2` sẽ được chọn (version `3` bị bỏ qua).

> warning **Notice** Với Express adapter, hãy cho `extractor` trả về một version duy nhất (một chuỗi, hoặc một mảng có một phần tử). Việc chọn version khớp cao nhất từ một mảng nhiều phần tử **không hoạt động ổn định** trên Express do giới hạn thiết kế của adapter. Nếu bạn cần hành vi đó, hãy dùng Fastify adapter, adapter này hỗ trợ cả chọn một version lẫn chọn version khớp cao nhất.

Để bật **Custom Versioning** cho ứng dụng, hãy tạo một hàm `extractor` và truyền nó vào `enableVersioning()`:

[[CODE:4]]

#### Cách dùng

Versioning cho phép bạn đánh version cho controller và từng route, đồng thời cho phép một số resource không tham gia versioning. Cách dùng giống nhau bất kể ứng dụng của bạn dùng kiểu versioning nào.

> warning **Notice** Nếu versioning được bật cho ứng dụng nhưng một controller hoặc route không chỉ định version (và không đặt [version mặc định global](/http/versioning#global-default-version)), controller hoặc route đó hoạt động như một controller/route [`VERSION_NEUTRAL`](/http/versioning#version-neutral). Với URI Versioning, nó chỉ được phục vụ tại path không có version (`/cats`, còn `/v1/cats` nhận response status `404`). Với các kiểu versioning khác, nó được phục vụ bất kể request chứa version nào, hoặc không chứa version. Một request chứa version không có controller hoặc route tương ứng sẽ nhận response status `404`, cũng như một request không có version khi chỉ có các controller hoặc route có version khớp với path của nó.

#### Version của controller

Có thể áp dụng version cho một controller, để đặt version cho mọi route trong controller đó.

Để thêm version cho một controller, làm như sau:

[[CODE:5]]

#### Version của route

Có thể áp dụng version cho một route riêng lẻ. Version này ghi đè mọi version khác có thể ảnh hưởng tới route, như version của controller.

Để thêm version cho một route riêng lẻ, làm như sau:

[[CODE:6]]

#### Nhiều version

Có thể áp dụng nhiều version cho một controller hoặc route. Để dùng nhiều version, hãy đặt version là một mảng:

[[CODE:7]]

#### Version "Neutral"

Một số controller hoặc route hoạt động giống nhau bất kể version. Để đáp ứng điều này, hãy đặt version là symbol `VERSION_NEUTRAL`.

Một request gửi đến sẽ được ánh xạ tới controller hoặc route `VERSION_NEUTRAL` bất kể version được chỉ định, kể cả khi request hoàn toàn không chứa version nào.

> warning **Notice** Với URI Versioning, một resource `VERSION_NEUTRAL` không có version trong URI của nó.

Để thêm một controller hoặc route không phụ thuộc version, làm như sau:

[[CODE:8]]

> warning **Notice** Hãy đăng ký một controller hoặc route version-neutral, hoặc một controller/route không chỉ định version khi không đặt [version mặc định global](/http/versioning#global-default-version), sau mọi controller hoặc route có version dùng chung path với nó: liệt kê nó sau trong mảng `controllers` của module, khai báo nó bên dưới chúng trong cùng controller, hoặc đặt nó trong một module được đăng ký sau module của chúng. Các controller của chính một module được đăng ký trước controller của các module mà nó import, và các module được import theo thứ tự của mảng `imports`. Với Express adapter và bất kỳ kiểu versioning nào khác ngoài URI Versioning, các route dùng chung path được thử theo thứ tự đăng ký, nên một route version-neutral được đăng ký trước cũng sẽ nhận các request dành cho route có version.

#### Version mặc định global

Nếu bạn không muốn chỉ định version cho từng controller hoặc route, hoặc muốn một version cụ thể làm mặc định cho mọi controller hoặc route không chỉ định version, hãy đặt `defaultVersion` như sau:

[[CODE:9]]

#### Versioning cho middleware

[Middleware](/middleware) cũng có thể dùng metadata versioning để nhắm tới một version cụ thể của route. Để làm vậy, đặt thuộc tính `version` trong route object truyền vào method `MiddlewareConsumer.forRoutes()`:

[[CODE:10]]

Với URI Versioning, đoạn code trên chỉ áp dụng `LoggerMiddleware` cho version `'2'` của endpoint `/cats`, vì mỗi version được phục vụ tại path riêng của nó.

> warning **Notice** Với Header, Media Type hoặc Custom Versioning, mọi version của một endpoint dùng chung một path, nên middleware chạy cho request tới mọi version của `/cats`. Để chạy code cho riêng một version với các kiểu versioning này, hãy dùng guard hoặc interceptor trên controller hoặc route handler của version đó.
