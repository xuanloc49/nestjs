### Serialization

Serialization diễn ra trước khi object được trả về trong network response. Đây là nơi thích hợp để định nghĩa các quy tắc chuyển đổi và làm sạch dữ liệu gửi về client. Ví dụ, dữ liệu nhạy cảm như mật khẩu phải luôn bị loại khỏi response, và một số thuộc tính có thể cần chuyển đổi thêm, như chỉ trả về một tập con các thuộc tính của entity. Tự làm các phép chuyển đổi này trong từng handler vừa tốn công vừa dễ sai, và khó đảm bảo mọi trường hợp đều được xử lý.

#### Tổng quan

Nest cung cấp sẵn hai interceptor áp dụng các quy tắc này theo kiểu khai báo:

- `ClassSerializerInterceptor` dùng package [class-transformer](https://github.com/typestack/class-transformer). Nó lấy giá trị do route handler trả về và áp dụng hàm `instanceToPlain()` lên đó, hàm này tuân theo các decorator `class-transformer` khai báo trên class entity hoặc DTO. Phần đầu của chương này trình bày cách tiếp cận này.

- `StandardSchemaSerializerInterceptor` validate và chuyển đổi response bằng một schema viết bằng [Zod](https://zod.dev/), [Valibot](https://valibot.dev/), [ArkType](https://arktype.io/), hoặc bất kỳ library nào tương thích [Standard Schema](https://standardschema.dev/). Xem [Serialization dựa trên schema](#schema-based-serialization).

> info **Hint** Cả hai interceptor đều không serialize response dạng [StreamableFile](/http/file-upload#streaming-files).

#### Loại bỏ thuộc tính

Giả sử bạn muốn loại thuộc tính `password` của entity người dùng khỏi mọi response. Hãy đánh dấu entity như sau:

[[CODE:1]]

Giờ xét một controller có route handler trả về instance của class này:

[[CODE:2]]

> warning **Warning** Handler phải trả về một instance của class. Một object JavaScript thuần, như `{{ '{' }} user: new UserEntity() {{ '}' }}`, sẽ không được serialize đúng. Để serialize object thuần, xem [Chuyển đổi object thuần](#transform-plain-objects).

> info **Hint** `ClassSerializerInterceptor` được import từ `@nestjs/common`.

Khi endpoint này được gọi, client nhận được response sau:

[[CODE:3]]

Interceptor cũng có thể được bind cho toàn ứng dụng (xem [Bind interceptor](/interceptors#binding-interceptors)). Kết hợp interceptor với khai báo class entity giúp đảm bảo **mọi** route handler trả về `UserEntity` đều bỏ đi thuộc tính `password`, áp dụng quy tắc này tại một chỗ duy nhất.

#### Expose thuộc tính

Dùng decorator `@Expose()` để đặt tên alias cho thuộc tính, hoặc để tính giá trị thuộc tính bằng một hàm (tương tự **getter**), như bên dưới.

[[CODE:4]]

#### Transform

Dùng decorator `@Transform()` để chuyển đổi dữ liệu thêm. Ví dụ, cách khai báo sau trả về thuộc tính `name` của `RoleEntity` thay vì toàn bộ object.

[[CODE:5]]

#### Truyền tùy chọn

Để ghi đè hành vi mặc định của các hàm chuyển đổi, hãy truyền tùy chọn vào decorator `@SerializeOptions()`.

[[CODE:6]]

> info **Hint** Decorator `@SerializeOptions()` được import từ `@nestjs/common`.

Các tùy chọn truyền vào `@SerializeOptions()` được chuyển tiếp làm tham số thứ hai của hàm `instanceToPlain()` bên dưới. Trong ví dụ này, mọi thuộc tính bắt đầu bằng prefix `_` đều bị loại bỏ.

#### Chuyển đổi object thuần

Tùy chọn `type` của `@SerializeOptions()` chuyển response thành instance của class được chỉ định trước khi serialize, nên các decorator `class-transformer` của class vẫn được áp dụng kể cả khi handler trả về object thuần. Nhờ đó bạn không cần khởi tạo class hay gọi `plainToInstance()` trong từng handler.

Trong ví dụ dưới đây, cả hai nhánh điều kiện đều trả về object JavaScript thuần, và chúng được chuyển thành instance `UserEntity` với các decorator tương ứng được áp dụng:

[[CODE:7]]

> info **Hint** Khai báo type trả về của handler giúp TypeScript kiểm tra object thuần trả về có khớp với cấu trúc của DTO hoặc entity hay không. Hàm `plainToInstance()` không có kiểm tra type này, nên một object sai cấu trúc có thể lọt qua mà không ai để ý.

> warning **Warning** Response được định hình bởi class `type`, không phải bởi class của giá trị trả về. Một giá trị không phải instance của class `type`, như instance của một entity khác, sẽ được chuyển đổi như một object thuần: các decorator trong class của chính nó, như `@Exclude()`, bị bỏ qua, và các thuộc tính mà class `type` không khai báo sẽ được copy nguyên vẹn. Để chỉ gửi các thuộc tính của class `type`, hãy decorate từng thuộc tính bằng `@Expose()` và thêm `excludeExtraneousValues: true` vào tùy chọn của cùng decorator `@SerializeOptions()` đó.


#### Serialization dựa trên schema

`StandardSchemaSerializerInterceptor` định hình response bằng schema thay vì decorator trên class. Schema mô tả chính xác những gì được đưa ra khỏi API: interceptor cho giá trị do route handler trả về chạy qua schema và gửi output của schema về client. Nó chấp nhận bất kỳ schema nào implement đặc tả [Standard Schema](https://standardschema.dev/). Các ví dụ trong phần này dùng Zod.

Vì `z.object()` loại bỏ các thuộc tính mà schema không khai báo, một response schema cũng đồng thời là một allowlist. Schema sau đảm bảo `password` của người dùng không bao giờ bị gửi đi, kể cả khi service trả về toàn bộ dòng dữ liệu trong database:

[[CODE:8]]

Bind interceptor và chọn schema bằng tùy chọn `schema` của decorator `@SerializeOptions()`:

[[CODE:9]]

Service trả về các bản ghi người dùng có kèm thuộc tính `password`, nhưng client chỉ nhận được các thuộc tính đã khai báo:

[[CODE:10]]

Khi handler trả về một mảng, như `findAll()`, interceptor áp dụng schema cho **từng phần tử**. Hãy truyền schema của một phần tử, không phải schema mảng.

Response là `null`, `undefined`, giá trị primitive và `StreamableFile` được gửi đi nguyên vẹn, cũng như response của các handler không có schema.

#### Chuyển đổi response bằng schema

Các phép chuyển đổi của schema làm được những gì `@Expose()` và `@Transform()` làm cho class. Schema sau thêm một thuộc tính tính toán `fullName` và thay object lồng `role` bằng tên của nó:

[[CODE:11]]

Với một người dùng có role `admin`, client nhận được:

[[CODE:12]]

Cùng schema đó viết bằng Valibot dùng `v.pipe()` và `v.transform()`:

[[CODE:13]]

#### Bind schema serializer

`@SerializeOptions()` có thể decorate cả class controller lẫn route handler. Schema đặt trên class áp dụng cho mọi handler của nó, và schema đặt trên handler sẽ được ưu tiên:

[[CODE:14]]

Để bind interceptor cho toàn ứng dụng, hãy truyền vào nó instance `Reflector`, thứ mà interceptor dùng để đọc metadata của `@SerializeOptions()`:

[[CODE:15]]

Cách khác là đăng ký nó bằng token `APP_INTERCEPTOR`, như mô tả trong [Bind interceptor](/interceptors#binding-interceptors), và Nest sẽ tự inject `Reflector` giúp bạn. Các handler không có schema không bị ảnh hưởng bởi global interceptor.

Constructor của interceptor cũng nhận các tùy chọn mặc định, áp dụng khi cả handler lẫn controller của nó đều không đặt schema:

<table>
  <tr>
    <td><code>schema</code></td>
    <td>Schema mặc định được dùng khi <code>@SerializeOptions()</code> không cung cấp schema.</td>
  </tr>
  <tr>
    <td><code>validateOptions</code></td>
    <td>Các tùy chọn được chuyển tiếp tới method <code>~standard.validate()</code> của schema, dành cho các library có hỗ trợ. Handler có thể ghi đè chúng bằng tùy chọn <code>validateOptions</code> của <code>@SerializeOptions()</code>.</td>
  </tr>
</table>

#### Lỗi serialization

Một response không khớp với schema của nó, như một bản ghi thiếu thuộc tính hoặc sai type, cho thấy có bug ở phía server, không phải lỗi của request. Khi đó, interceptor throw một lỗi liệt kê các vấn đề của schema, và client nhận response `500 Internal Server Error` thay vì dữ liệu được serialize dở dang. Thông báo lỗi, kèm các vấn đề, được exception filter mặc định ghi log.

Một ví dụ chạy được dùng Valibot có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/36-valibot-serializer).

#### Ví dụ

Một ví dụ chạy được của `ClassSerializerInterceptor` có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/21-serializer).

#### WebSocket và Microservice

Dù chương này dùng các ví dụ với ứng dụng HTTP (ví dụ Express hoặc Fastify), cả `ClassSerializerInterceptor` lẫn `StandardSchemaSerializerInterceptor` đều hoạt động giống hệt với WebSocket và microservice, bất kể transport là gì.

#### Tìm hiểu thêm

Đọc thêm về các decorator và tùy chọn có sẵn trong repository [class-transformer](https://github.com/typestack/class-transformer). Với các library schema, xem tài liệu của [Zod](https://zod.dev/), [Valibot](https://valibot.dev/) và [ArkType](https://arktype.io/).
