### Decorator

Mọi decorator OpenAPI đều có tiền tố `Api` để phân biệt với các decorator lõi. Bảng bên dưới liệt kê các decorator được export, cùng với cấp mà mỗi decorator có thể được áp dụng.

|                           |                     |
| ------------------------- | ------------------- |
| `@ApiBasicAuth()`         | Method / Controller |
| `@ApiBearerAuth()`        | Method / Controller |
| `@ApiBody()`              | Method              |
| `@ApiConsumes()`          | Method / Controller |
| `@ApiCookieAuth()`        | Method / Controller |
| `@ApiExcludeController()` | Controller          |
| `@ApiExcludeEndpoint()`   | Method              |
| `@ApiDefaultGetter()`     | Method              |
| `@ApiExtension()`         | Method / Controller |
| `@ApiExtraModels()`       | Method / Controller / Model |
| `@ApiHeader()`            | Method / Controller |
| `@ApiHeaders()`           | Method / Controller |
| `@ApiHideProperty()`      | Model               |
| `@ApiIncludeEndpoint()`   | Method              |
| `@ApiLink()`              | Method              |
| `@ApiOAuth2()`            | Method / Controller |
| `@ApiOperation()`         | Method              |
| `@ApiParam()`             | Method / Controller |
| `@ApiProduces()`          | Method / Controller |
| `@ApiSchema()`            | Model               |
| `@ApiProperty()`          | Model               |
| `@ApiPropertyOptional()`  | Model               |
| `@ApiQuery()`             | Method / Controller |
| `@ApiResponse()`          | Method / Controller |
| `@ApiResponseProperty()`  | Model               |
| `@ApiSecurity()`          | Method / Controller |
| `@ApiTags()`              | Method / Controller |
| `@ApiCallbacks()`         | Method / Controller |
| `@ApiWebhook()`           | Method              |

Các decorator response viết tắt (ví dụ `@ApiOkResponse()` và `@ApiNotFoundResponse()`, được liệt kê trong chương [operation](/openapi/operations#responses)) có thể được áp dụng ở cùng các cấp như `@ApiResponse()`.
