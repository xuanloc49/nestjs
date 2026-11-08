### Type và parameter

`SwaggerModule` tìm mọi decorator `@Body()`, `@Query()`, `@Param()` và `@Headers()` trong các route handler để sinh tài liệu API. Nó cũng dùng reflection để tạo các định nghĩa model tương ứng. Xét đoạn code sau:

[[CODE:1]]

> info **Hint** Để đặt định nghĩa body một cách tường minh, hãy dùng decorator `@ApiBody()` (được import từ package `@nestjs/swagger`).

Dựa trên `CreateCatDto`, Swagger UI hiển thị định nghĩa model sau:

<figure><img src="/assets/swagger-dto.png" /></figure>

Định nghĩa trống trơn, dù class có khai báo vài thuộc tính. Để các thuộc tính của class hiện ra với `SwaggerModule`, hãy chú thích chúng bằng decorator `@ApiProperty()` hoặc dùng [CLI plugin](/openapi/cli-plugin), plugin này làm việc đó tự động:

[[CODE:2]]

> info **Hint** Thay vì tự chú thích từng thuộc tính, hãy cân nhắc dùng [Swagger plugin](/openapi/cli-plugin), plugin này thêm các chú thích này cho bạn.

Mở trình duyệt và kiểm tra model `CreateCatDto` được sinh ra:

<figure><img src="/assets/swagger-dto2.png" /></figure>

Decorator `@ApiProperty()` cũng cho phép bạn đặt nhiều thuộc tính của [Schema Object](https://swagger.io/specification/#schemaObject):

[[CODE:3]]

> info **Hint** Thay vì gõ tường minh `{{"@ApiProperty({ required: false })"}}`, bạn có thể dùng decorator viết tắt `@ApiPropertyOptional()`.

Để đặt type của thuộc tính một cách tường minh, hãy dùng key `type`:

[[CODE:4]]

#### Mảng

Khi thuộc tính là một mảng, bạn phải tự chỉ ra kiểu mảng, như bên dưới:

[[CODE:5]]

> info **Hint** Hãy cân nhắc dùng [Swagger plugin](/openapi/cli-plugin), plugin này tự động phát hiện mảng.

Hoặc truyền type làm phần tử đầu tiên của một mảng (như ở trên) hoặc đặt thuộc tính `isArray` thành `true`.

<app-banner-enterprise></app-banner-enterprise>

#### Phụ thuộc vòng tròn

Khi bạn có phụ thuộc vòng tròn giữa các class, hãy dùng một lazy function để cung cấp thông tin type cho `SwaggerModule`:

[[CODE:6]]

> info **Hint** Hãy cân nhắc dùng [Swagger plugin](/openapi/cli-plugin), plugin này tự động phát hiện phụ thuộc vòng tròn.

#### Generic và interface

TypeScript không lưu metadata về generic hay interface, nên khi bạn dùng chúng trong DTO, `SwaggerModule` có thể không sinh được định nghĩa model đúng lúc runtime. Chẳng hạn, module Swagger không thể đọc đúng đoạn code sau:

[[CODE:7]]

Để vượt qua hạn chế này, hãy đặt type một cách tường minh:

[[CODE:8]]

#### Enum

Để xác định một `enum`, hãy đặt thuộc tính `enum` của `@ApiProperty()` thành một mảng giá trị:

[[CODE:9]]

Ngoài ra, hãy định nghĩa một enum TypeScript thực sự như sau:

[[CODE:10]]

Sau đó bạn có thể dùng trực tiếp enum với parameter decorator `@Query()`, kết hợp với decorator `@ApiQuery()`:

[[CODE:11]]

<figure><img src="/assets/enum_query.gif" /></figure>

Khi `isArray` được đặt thành `true`, các giá trị của `enum` có thể được chọn trong một ô **chọn nhiều**:

<figure><img src="/assets/enum_query_array.gif" /></figure>

#### Schema của enum

Mặc định, thuộc tính `enum` thêm một định nghĩa [enum](https://swagger.io/docs/specification/data-models/enums/) thô vào `parameter`:

[[CODE:12]]

Đặc tả này dùng được trong hầu hết các trường hợp. Tuy nhiên, nếu bạn dùng một công cụ nhận đặc tả làm **input** và sinh code **phía client**, code được sinh ra có thể chứa các `enums` bị trùng lặp. Xét đoạn code sau:

[[CODE:13]]

> info **Hint** Đoạn code ở trên được sinh ra bằng một công cụ tên [NSwag](https://github.com/RicoSuter/NSwag).

Kết quả chứa hai `enums` giống hệt nhau. Để giải quyết vấn đề này, hãy truyền một `enumName` cùng với thuộc tính `enum` trong decorator:

[[CODE:14]]

Thuộc tính `enumName` khiến `@nestjs/swagger` biến `CatBreed` thành một `schema` riêng, giúp enum `CatBreed` có thể tái sử dụng. Đặc tả trông như sau:

[[CODE:15]]

> info **Hint** Các decorator `@ApiQuery()` và `@ApiParam()` cũng nhận `enumName` bên cạnh `enum`.

#### Ví dụ giá trị của thuộc tính

Để đặt một ví dụ duy nhất cho một thuộc tính, hãy dùng key `example`:

[[CODE:16]]

Để cung cấp nhiều ví dụ, hãy dùng key `examples` và truyền một object có cấu trúc như thế này:

[[CODE:17]]

#### Định nghĩa thô

Trong một số trường hợp, như mảng hoặc ma trận lồng sâu, bạn có thể cần tự định nghĩa type:

[[CODE:18]]

Bạn cũng có thể chỉ định schema object thô:

[[CODE:19]]

Để tự định nghĩa nội dung input/output trong các class controller, hãy dùng thuộc tính `schema`:

[[CODE:20]]

#### Model bổ sung

Để định nghĩa các model bổ sung mà controller không tham chiếu trực tiếp nhưng module Swagger cần đọc, hãy dùng decorator `@ApiExtraModels()`:

[[CODE:21]]

> info **Hint** Bạn chỉ cần dùng `@ApiExtraModels()` một lần cho một class model cụ thể.

Ngoài ra, hãy truyền một options object có thuộc tính `extraModels` cho method `SwaggerModule.createDocument()`:

[[CODE:22]]

Để lấy một tham chiếu (`$ref`) tới model, hãy dùng hàm `getSchemaPath(ExtraModel)`:

[[CODE:23]]

#### oneOf, anyOf, allOf

Để kết hợp các schema, hãy dùng các từ khóa `oneOf`, `anyOf` hoặc `allOf` (xem [oneOf, anyOf, allOf, not](https://swagger.io/docs/specification/data-models/oneof-anyof-allof-not/) trong tài liệu Swagger):

[[CODE:24]]

Để định nghĩa một mảng đa hình (tức là một mảng có các phần tử thuộc nhiều schema), hãy dùng một định nghĩa thô (xem ở trên) để tự định nghĩa type:

[[CODE:25]]

> info **Hint** Hàm `getSchemaPath()` được import từ `@nestjs/swagger`.

Cả `Cat` và `Dog` đều phải được định nghĩa là model bổ sung bằng decorator `@ApiExtraModels()` (ở cấp class).

#### Tên và mô tả của schema

Tên của schema được sinh ra dựa trên tên của class model gốc (ví dụ, model `CreateCatDto` sinh ra schema `CreateCatDto`). Để đổi tên schema, hãy dùng decorator `@ApiSchema()`:

[[CODE:26]]

Model ở trên được chuyển thành schema `CreateCatRequest`.

Mặc định, schema được sinh ra không có mô tả. Để thêm mô tả, hãy dùng thuộc tính `description`:

[[CODE:27]]

Khi đó mô tả được đưa vào schema:

[[CODE:28]]
