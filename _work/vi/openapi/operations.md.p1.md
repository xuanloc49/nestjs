### Operation

Theo thuật ngữ OpenAPI, path là các endpoint (resource) mà API của bạn đưa ra, như `/users` hay `/reports/summary`. Operation là các HTTP method dùng để thao tác trên các path này, như `GET`, `POST` hay `DELETE`.

#### Tag

Để gắn một controller vào một tag cụ thể, hãy dùng decorator `@ApiTags(...tags)`:

[[CODE:1]]

OpenAPI 3.2 mở rộng Tag Object để các tag có thể được tổ chức thành một cây phân cấp và được chú thích kèm gợi ý về cách chúng nên được trình bày. Để khai báo các quan hệ này, hãy định nghĩa trước các tag bằng `DocumentBuilder` và truyền các tùy chọn `parent` và `kind` cho `addTag()`:

[[CODE:2]]

Tùy chọn `parent` tham chiếu tới một tag khác theo tên. Tùy chọn `kind` là một chuỗi tự do, máy đọc được, gợi ý cách tag nên được dùng, thường là `nav`, `badge` hoặc `audience`. Cùng options object đó cũng nhận một `summary`, một field khác của Tag Object trong OpenAPI 3.2.

> warning **Warning** Các field `parent` và `kind` thuộc về Tag Object của OpenAPI 3.2. Bạn phải gọi `setOpenAPIVersion('3.2.0')`. Nếu không, tài liệu được sinh ra vẫn khai báo `openapi: 3.0.0`, và các validator nghiêm ngặt sẽ từ chối các field này. Các field phân cấp chỉ có thể được định nghĩa qua `DocumentBuilder.addTag()`. Decorator `@ApiTags()` bỏ qua chúng và log một cảnh báo.

#### Header

Để định nghĩa các header tùy chỉnh được kỳ vọng là một phần của request, hãy dùng `@ApiHeader()`:

[[CODE:3]]

#### Response

Để định nghĩa một HTTP response tùy chỉnh, hãy dùng decorator `@ApiResponse()`:

[[CODE:4]]

Nest cung cấp một tập decorator **API response** viết tắt được xây trên `@ApiResponse()`, mỗi decorator cho một status code phổ biến. Chúng bao gồm:

- `@ApiOkResponse()`
- `@ApiCreatedResponse()`
- `@ApiAcceptedResponse()`
- `@ApiNoContentResponse()`
- `@ApiMovedPermanentlyResponse()`
- `@ApiFoundResponse()`
- `@ApiBadRequestResponse()`
- `@ApiUnauthorizedResponse()`
- `@ApiNotFoundResponse()`
- `@ApiForbiddenResponse()`
- `@ApiMethodNotAllowedResponse()`
- `@ApiNotAcceptableResponse()`
- `@ApiRequestTimeoutResponse()`
- `@ApiConflictResponse()`
- `@ApiPreconditionFailedResponse()`
- `@ApiTooManyRequestsResponse()`
- `@ApiGoneResponse()`
- `@ApiPayloadTooLargeResponse()`
- `@ApiUnsupportedMediaTypeResponse()`
- `@ApiUnprocessableEntityResponse()`
- `@ApiInternalServerErrorResponse()`
- `@ApiNotImplementedResponse()`
- `@ApiBadGatewayResponse()`
- `@ApiServiceUnavailableResponse()`
- `@ApiGatewayTimeoutResponse()`
- `@ApiDefaultResponse()`

[[CODE:5]]

Để chỉ định model trả về cho một request, hãy tạo một class và chú thích mọi thuộc tính của nó bằng decorator `@ApiProperty()`:

[[CODE:6]]

Sau đó bạn có thể dùng model `Cat` với thuộc tính `type` của decorator response:

[[CODE:7]]

Mở trình duyệt và kiểm tra model `Cat` được sinh ra:

<figure><img src="/assets/swagger-response-type.png" /></figure>

Thay vì định nghĩa response cho từng endpoint hoặc controller riêng lẻ, bạn có thể định nghĩa một response global cho mọi endpoint bằng class `DocumentBuilder`. Điều này hữu ích cho các response mà mọi endpoint trong ứng dụng đều có thể trả về (ví dụ các lỗi như `401 Unauthorized` hay `500 Internal Server Error`).

[[CODE:8]]

#### Upload file

Để mô tả việc upload file cho một method cụ thể, hãy dùng decorator `@ApiBody()` cùng với `@ApiConsumes()`. Đây là một ví dụ đầy đủ dùng kỹ thuật [upload file](/http/file-upload):

[[CODE:9]]

Trong đó `FileUploadDto` được định nghĩa như sau:

[[CODE:10]]

Để xử lý upload nhiều file, hãy định nghĩa `FilesUploadDto` như sau:

[[CODE:11]]

#### Extension

Để thêm một extension cho một operation, hãy dùng decorator `@ApiExtension()`. Tên extension phải có tiền tố `x-` (nếu không, decorator sẽ throw một lỗi).

[[CODE:12]]

#### Nâng cao: `ApiResponse` generic

Với [định nghĩa thô](/openapi/types-and-parameters#raw-definitions), bạn có thể định nghĩa một schema generic cho Swagger UI. Giả sử bạn có DTO sau:

[[CODE:13]]

Chúng ta bỏ qua việc gắn decorator cho `results`, vì sau đó chúng ta sẽ cung cấp một định nghĩa thô cho nó. Giờ hãy định nghĩa một DTO khác, ví dụ `CatDto`, như sau:

[[CODE:14]]

Khi đã có DTO này, bạn có thể định nghĩa một response `PaginatedDto<CatDto>`:

[[CODE:15]]

Trong ví dụ này, response kết hợp `PaginatedDto` (qua `allOf`) với một thuộc tính `results` có type `Array<CatDto>`.

- `getSchemaPath()` trả về đường dẫn OpenAPI schema của một model cho trước trong tài liệu OpenAPI.
- `allOf` là một từ khóa của OAS 3 bao phủ nhiều use case liên quan tới kế thừa.

Cuối cùng, vì không có controller nào tham chiếu trực tiếp tới `PaginatedDto`, `SwaggerModule` chưa thể sinh định nghĩa model tương ứng. Trong trường hợp này, bạn phải thêm nó làm một [model bổ sung](/openapi/types-and-parameters#extra-models). Ví dụ, dùng decorator `@ApiExtraModels()` ở cấp controller:

[[CODE:16]]

Nếu bạn chạy Swagger lúc này, `swagger.json` được sinh ra cho endpoint này sẽ định nghĩa response sau:

[[CODE:17]]

Để có thể tái sử dụng, hãy tạo một custom decorator cho `PaginatedDto`:

[[CODE:18]]

> info **Hint** Interface `Type<any>` và hàm `applyDecorators()` được import từ package `@nestjs/common`.

Để đảm bảo `SwaggerModule` sinh định nghĩa cho model, decorator đăng ký nó làm model bổ sung bằng `ApiExtraModels()`, giống như chúng ta đã làm trước đó cho `PaginatedDto` trong controller.

Khi đã có decorator này, bạn có thể dùng custom decorator `@ApiPaginatedResponse()` trên endpoint:

[[CODE:19]]

Với các công cụ sinh client, cách này khiến việc `PaginatedDto<TModel>` nên được sinh ra thế nào cho client trở nên mơ hồ. Đoạn code sau là ví dụ về kết quả của một công cụ sinh client cho endpoint `GET /` ở trên:

[[CODE:20]]

**Return type** ở đây là mơ hồ. Để khắc phục vấn đề này, hãy thêm thuộc tính `title` vào `schema` trong `ApiPaginatedResponse`:

[[CODE:21]]

Giờ kết quả của công cụ sinh client trở thành:

[[CODE:22]]
