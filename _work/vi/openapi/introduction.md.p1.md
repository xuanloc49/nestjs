### Giới thiệu

Đặc tả [OpenAPI](https://swagger.io/specification/) là một định dạng định nghĩa không phụ thuộc ngôn ngữ dùng để mô tả RESTful API. Nest cung cấp một [module](https://github.com/nestjs/swagger) riêng sinh ra đặc tả như vậy từ các decorator trong code của bạn.

#### Cài đặt

Để bắt đầu, hãy cài dependency cần thiết:

[[CODE:1]]

> warning **Warning** Nếu bạn dùng Fastify, hãy cài thêm `@fastify/static`:
>
> [[CODE:2]]

#### Bootstrap

Khi đã cài đặt xong, hãy mở file `main.ts` và khởi tạo Swagger bằng class `SwaggerModule`:

[[CODE:3]]

> info **Hint** Bọc `SwaggerModule.createDocument()` trong một factory function sẽ trì hoãn việc sinh tài liệu cho tới khi tài liệu được yêu cầu lần đầu, giúp tiết kiệm thời gian khởi tạo. Tài liệu kết quả là một object có thể serialize, tuân theo đặc tả [OpenAPI Document](https://swagger.io/specification/#openapi-document). Thay vì phục vụ nó qua HTTP, bạn cũng có thể lưu nó thành file JSON hoặc YAML và dùng ở nơi khác.

> warning **Warning** Nếu bạn gọi `createDocument()` ngay lập tức (thay vì trong một factory function, như ở trên), hãy đảm bảo `app.enableVersioning()` chạy trước. Nếu không, các `paths` được sinh ra sẽ thiếu tiền tố phiên bản. Pattern factory không bị ảnh hưởng, vì tài liệu chưa được dựng cho tới khi được yêu cầu lần đầu.

`DocumentBuilder` dựng cấu trúc một tài liệu cơ sở tuân theo OpenAPI Specification. Các method của nó cho phép bạn đặt các thuộc tính như tiêu đề, mô tả và phiên bản. Để tạo một tài liệu đầy đủ (với mọi HTTP route được định nghĩa), hãy dùng method `createDocument()` của class `SwaggerModule`. Nó nhận hai tham số: một instance ứng dụng và cấu hình tài liệu cơ sở được trả về bởi `DocumentBuilder#build()`. Một tham số thứ ba tùy chọn, có type `SwaggerDocumentOptions`, được trình bày trong phần [tùy chọn tài liệu](/openapi/introduction#document-options).

Tiếp theo, gọi method `setup()`. Nó nhận:

1. Đường dẫn để mount Swagger UI
2. Một instance ứng dụng
3. Object tài liệu, hoặc một factory function trả về nó (như ở trên)
4. Một object cấu hình tùy chọn (xem [tùy chọn setup](/openapi/introduction#setup-options))

Giờ hãy chạy lệnh sau để khởi động HTTP server:

[[CODE:4]]

Trong khi ứng dụng đang chạy, hãy mở trình duyệt và truy cập `http://localhost:3000/api`. Bạn sẽ thấy Swagger UI.

<figure><img src="/assets/swagger1.png" /></figure>

`SwaggerModule` tự động phản ánh mọi endpoint của bạn.

> info **Hint** Để sinh và tải về một file Swagger JSON, hãy truy cập `http://localhost:3000/api-json` (giả sử tài liệu Swagger của bạn có tại `http://localhost:3000/api`).
> Bạn cũng có thể đưa nó ra trên một route tùy chọn bằng tùy chọn `jsonDocumentUrl` của method `setup()`:
>
> [[CODE:5]]
>
> Khi đó nó sẽ có tại `http://localhost:3000/swagger/json`.

> info **Hint** Swagger UI hoạt động với [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) mặc định của [security header](/security/helmet) có sẵn của Nest. Nếu bạn thêm script qua `customJs`/`customJsStr`, hoặc phục vụ Swagger UI qua HTTP thường bên ngoài môi trường phát triển cục bộ, hãy xem [Swagger UI và GraphQL IDE](/security/helmet#swagger-ui-and-graphql-ides) để biết các directive cần điều chỉnh.

> warning **Warning** Khi bạn đăng ký `helmet` trực tiếp với Fastify thay vào đó, [CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) của nó có thể chặn Swagger UI. Để giải quyết xung đột này, hãy cấu hình CSP như bên dưới:
>
> [[CODE:6]]

#### Tùy chọn tài liệu

Khi tạo một tài liệu, bạn có thể truyền thêm các tùy chọn để tinh chỉnh hành vi của library. Các tùy chọn này có type `SwaggerDocumentOptions`:

[[CODE:7]]

Ví dụ, để sinh tên operation như `createUser` thay vì `UsersController_createUser`, hãy đặt như sau:

[[CODE:8]]

#### Standard Schema (Zod, Valibot)

Các route parameter decorator của Nest nhận một schema tương thích [Standard Schema](https://standardschema.dev/) qua tùy chọn `schema` của chúng (xem chương [controller](/controllers#request-object)):

[[CODE:9]]

Module Swagger nhận các schema này và biến chúng thành request body và parameter trong tài liệu được sinh ra.

##### Các library không cần cấu hình

Nếu library validation của bạn hiện thực phần mở rộng **Standard JSON Schema** (tức là schema của nó có `~standard.jsonSchema`), Nest tự chuyển đổi các schema, và không có gì phải cấu hình. Ví dụ, Zod 4.2 trở lên hiện thực phần mở rộng này. Nest yêu cầu target `openapi-3.0` và dùng biến thể `input` hoặc `output`, tùy vào việc schema mô tả một request hay một response.

##### Cung cấp một converter

Với các library không có phần mở rộng đó (hoặc khi bạn muốn tự kiểm soát việc chuyển đổi), hãy cung cấp một `standardSchemaConverter` trong `SwaggerDocumentOptions`. Nó nhận schema thô và `schemaType` đang được sinh, và trả về OpenAPI schema đã chuyển đổi:

[[CODE:10]]

Nest gọi converter trước khi thử chuyển đổi gốc. Trả về `undefined` báo cho Nest biết converter không xử lý schema này, nên Nest fallback về việc chuyển đổi gốc mô tả ở trên. Điều này giúp việc hỗ trợ nhiều library từ một converter trở nên an toàn.

Với **Zod**, bạn có thể dùng [zod-openapi](https://github.com/samchungy/zod-openapi):

[[CODE:11]]

[[CODE:12]]

Với **Valibot**, hãy dùng [@valibot/to-json-schema](https://github.com/fabian-hiller/valibot/tree/main/packages/to-json-schema):

[[CODE:13]]

[[CODE:14]]

Hai converter khác nhau ở một điểm. `createSchema()` có thể tách các định nghĩa dùng lại được ra ngoài, nên kết quả của nó mang theo một map `components`, bạn truyền nó đi tiếp và Nest merge nó vào các component dùng chung của tài liệu. `toJsonSchema()` trả về một schema duy nhất tự đầy đủ, nên converter cho Valibot bỏ qua `components`.

##### Hỗ trợ nhiều library cùng lúc

Vì converter nhận schema dưới dạng `unknown`, bạn có thể rẽ nhánh theo vendor của schema và hỗ trợ nhiều library trong cùng một ứng dụng. Mọi Standard Schema đều cung cấp vendor của nó tại `~standard.vendor`:

[[CODE:15]]

> warning **Warning** Luôn thu hẹp theo vendor trước khi gọi một converter riêng của library. Truyền một schema Valibot cho `createSchema()` (hoặc ngược lại) sẽ throw lúc sinh tài liệu thay vì thất bại một cách nhẹ nhàng.

> info **Hint** `schemaType` quan trọng khi schema của bạn thực hiện biến đổi: dạng `input` là những gì client gửi, còn dạng `output` là những gì handler của bạn nhận sau khi parse. Nest yêu cầu biến thể phù hợp với vị trí đang được mô tả, nên hãy truyền thẳng giá trị đó cho converter thay vì hardcode một giá trị.

#### Tùy chọn setup

Bạn có thể cấu hình Swagger UI bằng cách truyền một options object implement interface `SwaggerCustomOptions` làm tham số thứ tư của method `SwaggerModule#setup()`.

[[CODE:16]]

> info **Hint** `ui` và `raw` là các tùy chọn độc lập. Tắt Swagger UI (`ui: false`) không tắt các định nghĩa API (JSON/YAML). Ngược lại, tắt các định nghĩa API (`raw: []`) không tắt Swagger UI.
>
> Ví dụ, cấu hình sau tắt Swagger UI nhưng vẫn giữ định nghĩa API dạng JSON:
>
> [[CODE:17]]
>
> Trong trường hợp này, `http://localhost:3000/api-json` vẫn truy cập được, nhưng `http://localhost:3000/api` (Swagger UI) thì không.

#### Ví dụ

Một ví dụ chạy được có trong [repository của Nest](https://github.com/nestjs/nest/tree/master/sample/11-swagger).
