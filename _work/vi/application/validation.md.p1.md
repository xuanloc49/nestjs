### Validation

Hãy validate mọi dữ liệu mà ứng dụng web nhận được trước khi xử lý. Nest cung cấp vài pipe tự động validate request gửi đến:

- `ValidationPipe` validate các class được decorate bằng các quy tắc của [class-validator](https://github.com/typestack/class-validator).
- `StandardSchemaValidationPipe` validate các schema viết bằng [Zod](https://zod.dev/), [Valibot](https://valibot.dev/), [ArkType](https://arktype.io/), hoặc bất kỳ library nào tương thích [Standard Schema](https://standardschema.dev/).
- `ParseIntPipe`, `ParseBoolPipe`, `ParseArrayPipe` và `ParseUUIDPipe` validate và chuyển đổi từng giá trị riêng lẻ.

#### Tổng quan

Chương [Pipes](/pipes) giải thích cách pipe hoạt động và cách bind chúng vào tham số, route handler, controller, hoặc toàn bộ ứng dụng. Chương này tiếp nối từ đó và trình bày cách dùng hai pipe validation trong thực tế.

Hai pipe khác nhau ở chỗ các quy tắc validation nằm ở đâu:

- Với `ValidationPipe`, quy tắc là các decorator trên một **class DTO**, và class này cũng là type TypeScript của tham số. Cách này tích hợp với các tiện ích [mapped type](#mapped-types) và với Swagger CLI plugin.
- Với `StandardSchemaValidationPipe`, quy tắc là một **schema object**, và type TypeScript của tham số được suy ra từ schema. Schema được kết hợp bằng các method của library tương ứng, không cần đến class hay reflection metadata.

Bạn có thể đăng ký cả hai pipe cùng lúc. `ValidationPipe` chỉ validate các tham số có type là class, còn `StandardSchemaValidationPipe` chỉ validate các tham số có khai báo schema, nên bạn có thể chuyển dần sang schema trong một ứng dụng hiện có.

#### Dùng ValidationPipe có sẵn

Để bắt đầu, trước tiên hãy cài các dependency cần thiết.

[[CODE:1]]

> info **Hint** `ValidationPipe` được export từ package `@nestjs/common`.

Vì pipe này dùng các library [`class-validator`](https://github.com/typestack/class-validator) và [`class-transformer`](https://github.com/typestack/class-transformer), nó hỗ trợ rất nhiều tùy chọn. Hãy truyền chúng trong một configuration object vào constructor của pipe. Các tùy chọn riêng của pipe là:

[[CODE:2]]

Ngoài ra, mọi tùy chọn của `class-validator` (kế thừa từ interface `ValidatorOptions`) cũng dùng được:

<table>
  <tr>
    <th>Tùy chọn</th>
    <th>Type</th>
    <th>Mô tả</th>
  </tr>
  <tr>
    <td><code>enableDebugMessages</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ in thêm các thông báo cảnh báo ra console khi có gì đó không ổn.</td>
  </tr>
  <tr>
    <td><code>skipUndefinedProperties</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ bỏ qua validation cho mọi thuộc tính có giá trị undefined trong object đang validate.</td>
  </tr>
  <tr>
    <td><code>skipNullProperties</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ bỏ qua validation cho mọi thuộc tính có giá trị null trong object đang validate.</td>
  </tr>
  <tr>
    <td><code>skipMissingProperties</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ bỏ qua validation cho mọi thuộc tính có giá trị null hoặc undefined trong object đang validate.</td>
  </tr>
  <tr>
    <td><code>whitelist</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validator sẽ loại khỏi object đã validate (object trả về) mọi thuộc tính không dùng decorator validation nào.</td>
  </tr>
  <tr>
    <td><code>forbidNonWhitelisted</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, thay vì loại bỏ các thuộc tính không nằm trong whitelist, validator sẽ throw exception.</td>
  </tr>
  <tr>
    <td><code>forbidUnknownValues</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, mọi nỗ lực validate object không xác định sẽ thất bại ngay lập tức.</td>
  </tr>
  <tr>
    <td><code>disableErrorMessages</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, lỗi validation sẽ không được trả về cho client.</td>
  </tr>
  <tr>
    <td><code>errorHttpStatusCode</code></td>
    <td><code>number</code></td>
    <td>Thiết lập này cho phép bạn chỉ định loại exception sẽ được dùng khi có lỗi. Mặc định nó throw <code>BadRequestException</code>.</td>
  </tr>
  <tr>
    <td><code>exceptionFactory</code></td>
    <td><code>Function</code></td>
    <td>Nhận một mảng lỗi validation và trả về một exception object để throw.</td>
  </tr>
  <tr>
    <td><code>groups</code></td>
    <td><code>string[]</code></td>
    <td>Các group được dùng trong quá trình validate object.</td>
  </tr>
  <tr>
    <td><code>always</code></td>
    <td><code>boolean</code></td>
    <td>Đặt giá trị mặc định cho tùy chọn <code>always</code> của decorator. Giá trị mặc định có thể bị ghi đè trong tùy chọn của decorator.</td>
  </tr>

  <tr>
    <td><code>strictGroups</code></td>
    <td><code>boolean</code></td>
    <td>Nếu <code>groups</code> không được truyền hoặc rỗng, bỏ qua các decorator có ít nhất một group.</td>
  </tr>
  <tr>
    <td><code>dismissDefaultMessages</code></td>
    <td><code>boolean</code></td>
    <td>Nếu đặt là true, validation sẽ không dùng các thông báo mặc định. Thông báo lỗi sẽ luôn là <code>undefined</code>        nếu
      không được đặt tường minh.</td>
  </tr>
  <tr>
    <td><code>validationError.target</code></td>
    <td><code>boolean</code></td>
    <td>Cho biết target có được đưa vào <code>ValidationError</code> hay không.</td>
  </tr>
  <tr>
    <td><code>validationError.value</code></td>
    <td><code>boolean</code></td>
    <td>Cho biết giá trị đã validate có được đưa vào <code>ValidationError</code> hay không.</td>
  </tr>
  <tr>
    <td><code>stopAtFirstError</code></td>
    <td><code>boolean</code></td>
    <td>Khi đặt là true, việc validate một thuộc tính sẽ dừng lại sau khi gặp lỗi đầu tiên. Mặc định là false.</td>
  </tr>
  <tr>
    <td><code>errorFormat</code></td>
    <td><code>'list' | 'grouped'</code></td>
    <td>Chỉ định định dạng của các thông báo lỗi validation. <code>'list'</code> (mặc định) trả về một mảng các chuỗi thông báo lỗi. <code>'grouped'</code> trả về một object với key là đường dẫn thuộc tính và value là mảng các thông báo lỗi nguyên bản, giữ nguyên các thông báo validation tùy chỉnh mà không thêm prefix đường dẫn của cha vào trước.</td>
  </tr>
</table>

> info **Notice** Xem thêm thông tin về package `class-validator` trong [repository](https://github.com/typestack/class-validator) của nó.

#### Tự động validation

Hãy bắt đầu bằng việc bind `ValidationPipe` ở cấp ứng dụng, để mọi endpoint đều được bảo vệ khỏi việc nhận dữ liệu không hợp lệ.

[[CODE:3]]

Để test pipe, hãy tạo một endpoint cơ bản:

[[CODE:4]]

> info **Hint** TypeScript không emit metadata cho **generic hay interface**, nên `ValidationPipe` không thể validate các DTO khai báo bằng chúng. Hãy dùng class cụ thể cho DTO.

> info **Hint** Đừng import DTO bằng type-only import, vì type-only import bị xóa lúc runtime. Hãy viết `import {{ '{' }} CreateUserDto {{ '}' }}` thay vì `import type {{ '{' }} CreateUserDto {{ '}' }}`.

Tiếp theo, thêm các quy tắc validation vào `CreateUserDto` bằng các decorator do package `class-validator` cung cấp (xem [danh sách đầy đủ](https://github.com/typestack/class-validator#validation-decorators)). Khi đó mọi route dùng `CreateUserDto` đều áp dụng các quy tắc này.

[[CODE:5]]

Với các quy tắc này, một request có body chứa thuộc tính `email` không hợp lệ sẽ nhận response `400 Bad Request` với body như sau:

[[CODE:6]]

`ValidationPipe` cũng validate các phần khác của request. Ví dụ, để chỉ chấp nhận giá trị số cho path parameter `:id`, hãy dùng cách khai báo sau:

[[CODE:7]]

Giống như DTO, `FindOneParams` là một class định nghĩa quy tắc validation bằng `class-validator`:

[[CODE:8]]

#### Tắt lỗi chi tiết

Thông báo lỗi giải thích request bị sai ở đâu, nhưng một số môi trường production không muốn để lộ chúng ra. Để tắt lỗi chi tiết, truyền một options object vào `ValidationPipe`:

[[CODE:9]]

Kết quả là body của response không còn chứa thông báo lỗi chi tiết.

#### Loại bỏ thuộc tính

`ValidationPipe` cũng có thể lọc bỏ những thuộc tính mà route handler không nên nhận. Khi bạn khai báo **whitelist** các thuộc tính được chấp nhận, mọi thuộc tính không có trong whitelist sẽ bị loại khỏi object kết quả. Ví dụ, nếu handler mong đợi `email` và `password`, nhưng request có thêm thuộc tính `age`, thì `age` sẽ bị loại khỏi DTO kết quả. Để bật hành vi này, đặt `whitelist` thành `true`.

[[CODE:10]]

Khi bật tùy chọn này, các thuộc tính không có decorator nào trong class validation sẽ bị loại bỏ.

Cách khác là bạn có thể từ chối các request chứa thuộc tính không nằm trong whitelist bằng một response lỗi. Để làm vậy, đặt thêm `forbidNonWhitelisted` thành `true` bên cạnh `whitelist`.

<app-banner-courses></app-banner-courses>

#### Chuyển đổi payload object

Payload đến qua mạng dưới dạng object JavaScript thuần. `ValidationPipe` có thể chuyển chúng thành instance của class DTO tương ứng. Để bật tự động chuyển đổi, đặt `transform` thành `true`. Bạn có thể làm việc này ở cấp method:

[[CODE:11]]

Để bật hành vi này ở cấp global, đặt tùy chọn trên một global pipe:

[[CODE:12]]

Khi bật tự động chuyển đổi, `ValidationPipe` cũng chuyển đổi các type primitive. Trong ví dụ sau, method `findOne()` nhận path parameter `id` làm tham số:

[[CODE:13]]

Path parameter và query parameter luôn đến dưới dạng chuỗi. Vì signature của method khai báo `id` là `number`, `ValidationPipe` sẽ chuyển định danh dạng chuỗi thành số.

#### Chuyển đổi tường minh

Phần trước đã cho thấy `ValidationPipe` ngầm chuyển đổi query parameter và path parameter dựa trên type được khai báo. Việc chuyển đổi đó yêu cầu bật tự động chuyển đổi.

Khi tắt tự động chuyển đổi, bạn có thể chuyển đổi giá trị một cách tường minh bằng `ParseIntPipe` hoặc `ParseBoolPipe`. Không có `ParseStringPipe`, vì path parameter và query parameter vốn đã là chuỗi.

[[CODE:14]]

> info **Hint** `ParseIntPipe` và `ParseBoolPipe` được export từ package `@nestjs/common`.

#### Mapped type

Các tính năng như **CRUD** (Create/Read/Update/Delete) thường cần vài biến thể của một type gốc. Nest cung cấp các hàm tiện ích thực hiện các phép chuyển đổi type này.

> warning **Warning** Nếu ứng dụng của bạn dùng package `@nestjs/swagger`, xem [chương này](/openapi/mapped-types) để biết thêm về mapped type. Tương tự, nếu bạn dùng package `@nestjs/graphql`, xem [chương này](/graphql/mapped-types). Cả hai package đều dựa nhiều vào type metadata, nên chúng export phiên bản riêng của các tiện ích này. Import chúng từ `@nestjs/mapped-types` thay vì từ `@nestjs/swagger` hoặc `@nestjs/graphql` có thể gây ra các tác dụng phụ không được ghi chép.

Các type validation đầu vào (DTO) thường có biến thể **create** và **update** của cùng một type: biến thể **create** yêu cầu mọi trường, còn biến thể **update** cho chúng là tùy chọn. Các tiện ích mapped type tạo ra những biến thể như vậy mà không phải lặp lại khai báo thuộc tính hay các decorator validation của chúng. Xét type **create** sau:

[[CODE:15]]

> info **Hint** `PartialType()`, `PickType()`, `OmitType()` và `IntersectionType()` được import từ package `@nestjs/mapped-types`.

Hàm `PartialType()` trả về một type (class) có mọi thuộc tính của type đầu vào được đặt thành tùy chọn:

[[CODE:16]]

Hàm `PickType()` tạo một type từ một tập con các thuộc tính của type đầu vào:

[[CODE:17]]

Hàm `OmitType()` tạo một type có mọi thuộc tính của type đầu vào, **ngoại trừ** những thuộc tính được liệt kê. Tham số thứ hai là một mảng tên thuộc tính:

[[CODE:18]]

Hàm `IntersectionType()` kết hợp các thuộc tính của hai type thành một type (class) mới. Ví dụ, với một type khác như sau:

[[CODE:19]]

Type sau chứa thuộc tính của cả hai:

[[CODE:20]]

Các hàm tiện ích mapped type có thể kết hợp với nhau. Ví dụ, type sau có mọi thuộc tính của `CreateCatDto` trừ `name`, và tất cả đều là tùy chọn:

[[CODE:21]]

#### Parse và validate mảng

TypeScript không emit metadata cho các type generic như mảng, nên `ValidationPipe` không thể validate các phần tử của một tham số mảng. Trong đoạn code sau, các phần tử của `createUserDtos` không được validate:

[[CODE:22]]

Để validate mảng, hãy tạo một class riêng với một thuộc tính bọc mảng đó, hoặc dùng `ParseArrayPipe`:

[[CODE:23]]

`ParseArrayPipe` cũng hữu ích để parse query parameter. Xét method `findByIds()` trả về danh sách người dùng dựa trên các định danh truyền trong query string:

[[CODE:24]]

Cách khai báo này parse và validate query parameter của một request như sau:

[[CODE:25]]

#### Validation dựa trên schema

`StandardSchemaValidationPipe` validate giá trị theo schema thay vì theo class được decorate. Nó chấp nhận bất kỳ schema nào implement đặc tả [Standard Schema](https://standardschema.dev/), bao gồm [Zod](https://zod.dev/), [Valibot](https://valibot.dev/) và [ArkType](https://arktype.io/). Schema là nguồn sự thật duy nhất cho một payload: nó validate giá trị lúc runtime, và type suy ra từ nó chính là type TypeScript của tham số handler. Các ví dụ trong phần này dùng Zod.

[[CODE:26]]

Định nghĩa một schema và suy ra type DTO từ nó:

[[CODE:27]]

Tiếp theo, bind pipe ở cấp ứng dụng:

[[CODE:28]]

Sau đó gắn schema vào một tham số bằng tùy chọn `schema` của decorator tham số:

[[CODE:29]]

Pipe chỉ validate các tham số có khai báo schema và cho mọi giá trị khác đi qua nguyên vẹn, nên bind nó ở cấp global là an toàn. Nếu body của request không khớp với schema, ứng dụng sẽ trả về `400 Bad Request`. Mỗi thông báo được thêm prefix là đường dẫn của thuộc tính không hợp lệ:

[[CODE:30]]

Tùy chọn `schema` được hỗ trợ bởi `@Body()`, `@Query()` và `@Param()`, cũng như `@MessageBody()` trong [gateway](/websockets/gateways) và `@Payload()` trong [microservice](/microservices/basics). Truyền nó làm tham số duy nhất để validate toàn bộ object, hoặc sau tên thuộc tính để validate một giá trị riêng lẻ:

[[CODE:31]]

#### Ép kiểu và chuyển đổi

Path parameter và query parameter luôn đến dưới dạng chuỗi. Các schema ép kiểu, như `z.coerce.number()`, sẽ chuyển đổi chúng trước khi validate:

[[CODE:32]]

Schema cũng có thể áp dụng giá trị mặc định và các phép chuyển đổi. Schema sau mô tả query string của một danh sách có phân trang:

[[CODE:33]]

[[CODE:34]]

Với request `GET /users?page=2&search=%20kamil%20`, handler nhận được `page` là số `2`, `limit` là giá trị mặc định `20`, và `search` là chuỗi đã trim `'kamil'`.

Mặc định, pipe truyền **output** của schema cho handler, nên việc ép kiểu, giá trị mặc định và các phép chuyển đổi đều có hiệu lực. Để validate giá trị nhưng vẫn truyền nguyên vẹn đầu vào gốc, đặt `transform` thành `false`. Khi đó, hãy khai báo type của tham số bằng type đầu vào của schema (`z.input<typeof schema>` trong Zod).

#### Thuộc tính không xác định

Cách schema xử lý các thuộc tính mà nó không khai báo là do chính schema quyết định, không phải pipe. Trong Zod:

- `z.object()` loại bỏ thuộc tính không xác định, giống tùy chọn `whitelist` của `ValidationPipe`.
- `z.strictObject()` từ chối chúng, giống tùy chọn `forbidNonWhitelisted`. Thông báo lỗi là `Unrecognized key: "age"`.
- `z.looseObject()` giữ lại chúng.

#### Tạo schema dẫn xuất

Các tiện ích [mapped type](#mapped-types) tạo ra class DTO mới từ những class đã có. Với schema, chính các method của library phục vụ cùng mục đích:

[[CODE:35]]

Mảng cũng không cần xử lý gì đặc biệt. Bọc schema của phần tử trong `z.array()`, và mọi phần tử đều được validate:

[[CODE:36]]

Thông báo cho một phần tử không hợp lệ sẽ có prefix là chỉ số của nó, ví dụ `1.email: Invalid email address`.

#### Validate custom decorator

Các decorator tham số tạo bằng [`createParamDecorator()`](/custom-decorators) cũng nhận tùy chọn `schema`. Ví dụ, decorator sau lấy định danh tenant từ một header của request:

[[CODE:37]]

[[CODE:38]]

Pipe sẽ bỏ qua custom decorator trừ khi bạn bật tùy chọn `validateCustomDecorators`:

[[CODE:39]]

#### Tùy chọn validation bằng schema

Constructor của `StandardSchemaValidationPipe` nhận các tùy chọn sau:

<table>
  <tr>
    <th>Tùy chọn</th>
    <th>Type</th>
    <th>Mô tả</th>
  </tr>
  <tr>
    <td><code>transform</code></td>
    <td><code>boolean</code></td>
    <td>Nếu là <code>true</code>, handler nhận giá trị do schema tạo ra. Nếu là <code>false</code>, handler nhận đầu vào gốc sau khi validate thành công. Mặc định: <code>true</code>.</td>
  </tr>
  <tr>
    <td><code>validateCustomDecorators</code></td>
    <td><code>boolean</code></td>
    <td>Nếu là <code>true</code>, tham số của các custom decorator tạo bằng <code>createParamDecorator()</code> cũng được validate. Mặc định: <code>false</code>.</td>
  </tr>
  <tr>
    <td><code>validateOptions</code></td>
    <td><code>Record&lt;string, unknown&gt;</code></td>
    <td>Các tùy chọn được chuyển tiếp tới method <code>~standard.validate()</code> của schema, dành cho các library có hỗ trợ.</td>
  </tr>
  <tr>
    <td><code>errorHttpStatusCode</code></td>
    <td><code>number</code></td>
    <td>HTTP status code của exception được throw khi validation thất bại. Mặc định: <code>400</code>.</td>
  </tr>
  <tr>
    <td><code>exceptionFactory</code></td>
    <td><code>Function</code></td>
    <td>Nhận mảng các vấn đề validation và trả về exception cần throw.</td>
  </tr>
</table>

Dùng `exceptionFactory` để thay đổi cấu trúc của response lỗi. Mỗi vấn đề có một `message` và, với giá trị lồng nhau, một `path` gồm các segment là key thuộc tính hoặc object có thuộc tính `key`:

[[CODE:40]]

Với factory này, một request không hợp lệ sẽ nhận response `422 Unprocessable Entity`:

[[CODE:41]]

#### Các library schema khác

Không có gì trong pipe là đặc thù của Zod. Cùng tùy chọn `schema` đó nhận được schema của Valibot:

[[CODE:42]]

Hoặc schema của ArkType:

[[CODE:43]]

Thông báo lỗi do library tạo ra, nên cách diễn đạt sẽ khác nhau giữa các library.

> info **Hint** Cùng các schema đó có thể dùng để mô tả API của bạn trong tài liệu OpenAPI. Xem [Standard Schema (Zod, Valibot)](/openapi/introduction#standard-schema-zod-valibot) trong chương OpenAPI.

Một ví dụ chạy được có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/35-zod-validation).

#### WebSocket và Microservice

Dù chương này dùng các ví dụ với ứng dụng HTTP (ví dụ Express hoặc Fastify), cả `ValidationPipe` và `StandardSchemaValidationPipe` đều hoạt động giống hệt với WebSocket và microservice, bất kể transport là gì. Mặc định, cả hai đều throw một HTTP exception khi validation thất bại. Để báo lỗi theo cách mà transport hiểu được, hãy trả về một `WsException` hoặc `RpcException` từ tùy chọn `exceptionFactory`:

[[CODE:44]]

#### Tìm hiểu thêm

Đọc thêm về custom validator, thông báo lỗi và các decorator có sẵn trong repository [class-validator](https://github.com/typestack/class-validator). Với các library schema, xem tài liệu của [Zod](https://zod.dev/), [Valibot](https://valibot.dev/) và [ArkType](https://arktype.io/), cùng danh sách [các library tương thích Standard Schema](https://standardschema.dev/schema#what-schema-libraries-implement-the-spec).
