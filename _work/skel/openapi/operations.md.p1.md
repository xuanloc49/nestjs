### Operations

In OpenAPI terms, paths are the endpoints (resources) that your API exposes, such as `/users` or `/reports/summary`. Operations are the HTTP methods used to manipulate these paths, such as `GET`, `POST`, or `DELETE`.

#### Tags

To attach a controller to a specific tag, use the `@ApiTags(...tags)` decorator:

[[CODE:1]]

OpenAPI 3.2 extends the Tag Object so that tags can be organized into a hierarchy and annotated with a hint about how they should be presented. To declare these relationships, define the tags up front with `DocumentBuilder` and pass the `parent` and `kind` options to `addTag()`:

[[CODE:2]]

The `parent` option references another tag by name. The `kind` option is a free-form, machine-readable string that hints at how the tag should be used, commonly `nav`, `badge`, or `audience`. The same options object also accepts a `summary`, another OpenAPI 3.2 Tag Object field.

> warning **Warning** The `parent` and `kind` fields belong to the OpenAPI 3.2 Tag Object. You must call `setOpenAPIVersion('3.2.0')`. Otherwise, the generated document still declares `openapi: 3.0.0`, and strict validators reject these fields. Hierarchy fields can only be defined through `DocumentBuilder.addTag()`. The `@ApiTags()` decorator ignores them and logs a warning.

#### Headers

To define custom headers that are expected as part of the request, use `@ApiHeader()`:

[[CODE:3]]

#### Responses

To define a custom HTTP response, use the `@ApiResponse()` decorator:

[[CODE:4]]

Nest provides a set of shorthand **API response** decorators built on top of `@ApiResponse()`, one for each common status code. They include:

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

To specify a return model for a request, create a class and annotate all of its properties with the `@ApiProperty()` decorator:

[[CODE:6]]

You can then use the `Cat` model with the `type` property of the response decorator:

[[CODE:7]]

Open the browser and verify the generated `Cat` model:

<figure><img src="/assets/swagger-response-type.png" /></figure>

Instead of defining responses for each endpoint or controller individually, you can define a global response for all endpoints using the `DocumentBuilder` class. This is useful for responses that every endpoint in your application can return (e.g., errors like `401 Unauthorized` or `500 Internal Server Error`).

[[CODE:8]]

#### File upload

To document file upload for a specific method, use the `@ApiBody()` decorator together with `@ApiConsumes()`. Here's a full example using the [file upload](/http/file-upload) technique:

[[CODE:9]]

Where `FileUploadDto` is defined as follows:

[[CODE:10]]

To handle multiple file uploads, define `FilesUploadDto` as follows:

[[CODE:11]]

#### Extensions

To add an extension to an operation, use the `@ApiExtension()` decorator. The extension name must be prefixed with `x-` (otherwise, the decorator throws an error).

[[CODE:12]]

#### Advanced: Generic `ApiResponse`

With [raw definitions](/openapi/types-and-parameters#raw-definitions), you can define a generic schema for Swagger UI. Assume you have the following DTO:

[[CODE:13]]

We skip decorating `results`, because we'll provide a raw definition for it later. Now, define another DTO, for example `CatDto`, as follows:

[[CODE:14]]

With this in place, you can define a `PaginatedDto<CatDto>` response:

[[CODE:15]]

In this example, the response combines `PaginatedDto` (through `allOf`) with a `results` property of type `Array<CatDto>`.

- `getSchemaPath()` returns the OpenAPI schema path of a given model within the OpenAPI document.
- `allOf` is an OAS 3 keyword that covers various inheritance-related use cases.

Lastly, because no controller references `PaginatedDto` directly, the `SwaggerModule` can't generate a corresponding model definition yet. In this case, you must add it as an [extra model](/openapi/types-and-parameters#extra-models). For example, use the `@ApiExtraModels()` decorator at the controller level:

[[CODE:16]]

If you run Swagger now, the generated `swagger.json` for this endpoint defines the following response:

[[CODE:17]]

To make it reusable, create a custom decorator for `PaginatedDto`:

[[CODE:18]]

> info **Hint** The `Type<any>` interface and the `applyDecorators()` function are imported from the `@nestjs/common` package.

To ensure that the `SwaggerModule` generates a definition for the model, the decorator registers it as an extra model with `ApiExtraModels()`, just as we did earlier for `PaginatedDto` in the controller.

With this in place, you can use the custom `@ApiPaginatedResponse()` decorator on your endpoint:

[[CODE:19]]

For client generation tools, this approach makes it ambiguous how `PaginatedDto<TModel>` should be generated for the client. The following snippet is an example of a client generator result for the `GET /` endpoint above:

[[CODE:20]]

The **return type** here is ambiguous. To work around this issue, add a `title` property to the `schema` in `ApiPaginatedResponse`:

[[CODE:21]]

The client generator's result now becomes:

[[CODE:22]]
