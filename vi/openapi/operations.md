### Operation

Theo thuật ngữ OpenAPI, path là các endpoint (resource) mà API của bạn đưa ra, như `/users` hay `/reports/summary`. Operation là các HTTP method dùng để thao tác trên các path này, như `GET`, `POST` hay `DELETE`.

#### Tag <a id="tags"></a>

Để gắn một controller vào một tag cụ thể, hãy dùng decorator `@ApiTags(...tags)`:

```typescript
@ApiTags('cats')
@Controller('cats')
export class CatsController {}
```

OpenAPI 3.2 mở rộng Tag Object để các tag có thể được tổ chức thành một cây phân cấp và được chú thích kèm gợi ý về cách chúng nên được trình bày. Để khai báo các quan hệ này, hãy định nghĩa trước các tag bằng `DocumentBuilder` và truyền các tùy chọn `parent` và `kind` cho `addTag()`:

```typescript
const config = new DocumentBuilder()
  .setOpenAPIVersion('3.2.0')
  .addTag('Animals', 'Everything about animals', undefined, { kind: 'nav' })
  .addTag('Cats', 'Cat operations', undefined, { parent: 'Animals' })
  .addTag('Dogs', 'Dog operations', undefined, { parent: 'Animals' })
  .build();
```

Tùy chọn `parent` tham chiếu tới một tag khác theo tên. Tùy chọn `kind` là một chuỗi tự do, máy đọc được, gợi ý cách tag nên được dùng, thường là `nav`, `badge` hoặc `audience`. Cùng options object đó cũng nhận một `summary`, một field khác của Tag Object trong OpenAPI 3.2.

> warning **Cảnh báo** Các field `parent` và `kind` thuộc về Tag Object của OpenAPI 3.2. Bạn phải gọi `setOpenAPIVersion('3.2.0')`. Nếu không, tài liệu được sinh ra vẫn khai báo `openapi: 3.0.0`, và các validator nghiêm ngặt sẽ từ chối các field này. Các field phân cấp chỉ có thể được định nghĩa qua `DocumentBuilder.addTag()`. Decorator `@ApiTags()` bỏ qua chúng và log một cảnh báo.

#### Header <a id="headers"></a>

Để định nghĩa các header tùy chỉnh được kỳ vọng là một phần của request, hãy dùng `@ApiHeader()`:

```typescript
@ApiHeader({
  name: 'X-MyHeader',
  description: 'Custom header',
})
@Controller('cats')
export class CatsController {}
```

#### Response <a id="responses"></a>

Để định nghĩa một HTTP response tùy chỉnh, hãy dùng decorator `@ApiResponse()`:

```typescript
@Post()
@ApiResponse({ status: 201, description: 'The record has been successfully created.'})
@ApiResponse({ status: 403, description: 'Forbidden.'})
async create(@Body() createCatDto: CreateCatDto) {
  this.catsService.create(createCatDto);
}
```

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

```typescript
@Post()
@ApiCreatedResponse({ description: 'The record has been successfully created.'})
@ApiForbiddenResponse({ description: 'Forbidden.'})
async create(@Body() createCatDto: CreateCatDto) {
  this.catsService.create(createCatDto);
}
```

Để chỉ định model trả về cho một request, hãy tạo một class và chú thích mọi thuộc tính của nó bằng decorator `@ApiProperty()`:

```typescript
export class Cat {
  @ApiProperty()
  id: number;

  @ApiProperty()
  name: string;

  @ApiProperty()
  age: number;

  @ApiProperty()
  breed: string;
}
```

Sau đó bạn có thể dùng model `Cat` với thuộc tính `type` của decorator response:

```typescript
@ApiTags('cats')
@Controller('cats')
export class CatsController {
  @Post()
  @ApiCreatedResponse({
    description: 'The record has been successfully created.',
    type: Cat,
  })
  async create(@Body() createCatDto: CreateCatDto): Promise<Cat> {
    return this.catsService.create(createCatDto);
  }
}
```

Mở trình duyệt và kiểm tra model `Cat` được sinh ra:

<figure><img src="/assets/swagger-response-type.png" /></figure>

Thay vì định nghĩa response cho từng endpoint hoặc controller riêng lẻ, bạn có thể định nghĩa một response global cho mọi endpoint bằng class `DocumentBuilder`. Điều này hữu ích cho các response mà mọi endpoint trong ứng dụng đều có thể trả về (ví dụ các lỗi như `401 Unauthorized` hay `500 Internal Server Error`).

```typescript
const config = new DocumentBuilder()
  .addGlobalResponse({
    status: 500,
    description: 'Internal server error',
  })
  // other configurations
  .build();
```

#### Upload file <a id="file-upload"></a>

Để mô tả việc upload file cho một method cụ thể, hãy dùng decorator `@ApiBody()` cùng với `@ApiConsumes()`. Đây là một ví dụ đầy đủ dùng kỹ thuật [upload file](/http/file-upload):

```typescript
@UseInterceptors(FileInterceptor('file'))
@ApiConsumes('multipart/form-data')
@ApiBody({
  description: 'List of cats',
  type: FileUploadDto,
})
uploadFile(@UploadedFile() file: Express.Multer.File) {}
```

Trong đó `FileUploadDto` được định nghĩa như sau:

```typescript
class FileUploadDto {
  @ApiProperty({ type: 'string', format: 'binary' })
  file: any;
}
```

Để xử lý upload nhiều file, hãy định nghĩa `FilesUploadDto` như sau:

```typescript
class FilesUploadDto {
  @ApiProperty({ type: 'array', items: { type: 'string', format: 'binary' } })
  files: any[];
}
```

#### Extension <a id="extensions"></a>

Để thêm một extension cho một operation, hãy dùng decorator `@ApiExtension()`. Tên extension phải có tiền tố `x-` (nếu không, decorator sẽ throw một lỗi).

```typescript
@ApiExtension('x-foo', { hello: 'world' })
```

#### Nâng cao: `ApiResponse` generic <a id="advanced-generic-apiresponse"></a>

Với [định nghĩa thô](/openapi/types-and-parameters#raw-definitions), bạn có thể định nghĩa một schema generic cho Swagger UI. Giả sử bạn có DTO sau:

```ts
export class PaginatedDto<TData> {
  @ApiProperty()
  total: number;

  @ApiProperty()
  limit: number;

  @ApiProperty()
  offset: number;

  results: TData[];
}
```

Chúng ta bỏ qua việc gắn decorator cho `results`, vì sau đó chúng ta sẽ cung cấp một định nghĩa thô cho nó. Giờ hãy định nghĩa một DTO khác, ví dụ `CatDto`, như sau:

```ts
export class CatDto {
  @ApiProperty()
  name: string;

  @ApiProperty()
  age: number;

  @ApiProperty()
  breed: string;
}
```

Khi đã có DTO này, bạn có thể định nghĩa một response `PaginatedDto<CatDto>`:

```ts
@ApiOkResponse({
  schema: {
    allOf: [
      { $ref: getSchemaPath(PaginatedDto) },
      {
        properties: {
          results: {
            type: 'array',
            items: { $ref: getSchemaPath(CatDto) },
          },
        },
      },
    ],
  },
})
async findAll(): Promise<PaginatedDto<CatDto>> {}
```

Trong ví dụ này, response kết hợp `PaginatedDto` (qua `allOf`) với một thuộc tính `results` có type `Array<CatDto>`.

- `getSchemaPath()` trả về đường dẫn OpenAPI schema của một model cho trước trong tài liệu OpenAPI.
- `allOf` là một từ khóa của OAS 3 bao phủ nhiều use case liên quan tới kế thừa.

Cuối cùng, vì không có controller nào tham chiếu trực tiếp tới `PaginatedDto`, `SwaggerModule` chưa thể sinh định nghĩa model tương ứng. Trong trường hợp này, bạn phải thêm nó làm một [model bổ sung](/openapi/types-and-parameters#extra-models). Ví dụ, dùng decorator `@ApiExtraModels()` ở cấp controller:

```ts
@Controller('cats')
@ApiExtraModels(PaginatedDto)
export class CatsController {}
```

Nếu bạn chạy Swagger lúc này, `swagger.json` được sinh ra cho endpoint này sẽ định nghĩa response sau:

```json
"responses": {
  "200": {
    "description": "",
    "content": {
      "application/json": {
        "schema": {
          "allOf": [
            {
              "$ref": "#/components/schemas/PaginatedDto"
            },
            {
              "properties": {
                "results": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/CatDto"
                  }
                }
              }
            }
          ]
        }
      }
    }
  }
}
```

Để có thể tái sử dụng, hãy tạo một custom decorator cho `PaginatedDto`:

```ts
export const ApiPaginatedResponse = <TModel extends Type<any>>(
  model: TModel,
) => {
  return applyDecorators(
    ApiExtraModels(PaginatedDto, model),
    ApiOkResponse({
      schema: {
        allOf: [
          { $ref: getSchemaPath(PaginatedDto) },
          {
            properties: {
              results: {
                type: 'array',
                items: { $ref: getSchemaPath(model) },
              },
            },
          },
        ],
      },
    }),
  );
};
```

> info **Gợi ý** Interface `Type<any>` và hàm `applyDecorators()` được import từ package `@nestjs/common`.

Để đảm bảo `SwaggerModule` sinh định nghĩa cho model, decorator đăng ký nó làm model bổ sung bằng `ApiExtraModels()`, giống như chúng ta đã làm trước đó cho `PaginatedDto` trong controller.

Khi đã có decorator này, bạn có thể dùng custom decorator `@ApiPaginatedResponse()` trên endpoint:

```ts
@ApiPaginatedResponse(CatDto)
async findAll(): Promise<PaginatedDto<CatDto>> {}
```

Với các công cụ sinh client, cách này khiến việc `PaginatedDto<TModel>` nên được sinh ra thế nào cho client trở nên mơ hồ. Đoạn code sau là ví dụ về kết quả của một công cụ sinh client cho endpoint `GET /` ở trên:

```typescript
// Angular
findAll(): Observable<{ total: number, limit: number, offset: number, results: CatDto[] }>
```

**Return type** ở đây là mơ hồ. Để khắc phục vấn đề này, hãy thêm thuộc tính `title` vào `schema` trong `ApiPaginatedResponse`:

```typescript
export const ApiPaginatedResponse = <TModel extends Type<any>>(
  model: TModel,
) => {
  return applyDecorators(
    ApiOkResponse({
      schema: {
        title: `PaginatedResponseOf${model.name}`,
        allOf: [
          // ...
        ],
      },
    }),
  );
};
```

Giờ kết quả của công cụ sinh client trở thành:

```ts
// Angular
findAll(): Observable<PaginatedResponseOfCatDto>
```
