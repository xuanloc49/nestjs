### Types and parameters

The `SwaggerModule` searches for all `@Body()`, `@Query()`, `@Param()`, and `@Headers()` decorators in route handlers to generate the API document. It also uses reflection to create the corresponding model definitions. Consider the following code:

[[CODE:1]]

> info **Hint** To set the body definition explicitly, use the `@ApiBody()` decorator (imported from the `@nestjs/swagger` package).

Based on the `CreateCatDto`, Swagger UI shows the following model definition:

<figure><img src="/assets/swagger-dto.png" /></figure>

The definition is empty, even though the class declares a few properties. To make the class properties visible to the `SwaggerModule`, either annotate them with the `@ApiProperty()` decorator or use the [CLI plugin](/openapi/cli-plugin), which does this automatically:

[[CODE:2]]

> info **Hint** Instead of manually annotating each property, consider using the [Swagger plugin](/openapi/cli-plugin), which adds these annotations for you.

Open the browser and verify the generated `CreateCatDto` model:

<figure><img src="/assets/swagger-dto2.png" /></figure>

The `@ApiProperty()` decorator also lets you set various [Schema Object](https://swagger.io/specification/#schemaObject) properties:

[[CODE:3]]

> info **Hint** Instead of explicitly typing `{{"@ApiProperty({ required: false })"}}`, you can use the `@ApiPropertyOptional()` shorthand decorator.

To set the type of the property explicitly, use the `type` key:

[[CODE:4]]

#### Arrays

When the property is an array, you must indicate the array type manually, as shown below:

[[CODE:5]]

> info **Hint** Consider using the [Swagger plugin](/openapi/cli-plugin), which detects arrays automatically.

Either pass the type as the first element of an array (as shown above) or set the `isArray` property to `true`.

<app-banner-enterprise></app-banner-enterprise>

#### Circular dependencies

When you have circular dependencies between classes, use a lazy function to provide the `SwaggerModule` with type information:

[[CODE:6]]

> info **Hint** Consider using the [Swagger plugin](/openapi/cli-plugin), which detects circular dependencies automatically.

#### Generics and interfaces

TypeScript doesn't store metadata about generics or interfaces, so when you use them in your DTOs, the `SwaggerModule` may not be able to generate model definitions correctly at runtime. For instance, the Swagger module can't correctly inspect the following code:

[[CODE:7]]

To overcome this limitation, set the type explicitly:

[[CODE:8]]

#### Enums

To identify an `enum`, set the `enum` property of `@ApiProperty()` to an array of values:

[[CODE:9]]

Alternatively, define an actual TypeScript enum as follows:

[[CODE:10]]

You can then use the enum directly with the `@Query()` parameter decorator, in combination with the `@ApiQuery()` decorator:

[[CODE:11]]

<figure><img src="/assets/enum_query.gif" /></figure>

With `isArray` set to `true`, the `enum` values can be selected in a **multi-select**:

<figure><img src="/assets/enum_query_array.gif" /></figure>

#### Enums schema

By default, the `enum` property adds a raw [enum](https://swagger.io/docs/specification/data-models/enums/) definition to the `parameter`:

[[CODE:12]]

This specification works for most cases. However, if you use a tool that takes the specification as **input** and generates **client-side** code, the generated code may contain duplicated `enums`. Consider the following code snippet:

[[CODE:13]]

> info **Hint** The above snippet is generated using a tool called [NSwag](https://github.com/RicoSuter/NSwag).

The result contains two identical `enums`. To address this issue, pass an `enumName` along with the `enum` property in your decorator:

[[CODE:14]]

The `enumName` property makes `@nestjs/swagger` turn `CatBreed` into its own `schema`, which makes the `CatBreed` enum reusable. The specification looks like the following:

[[CODE:15]]

> info **Hint** The `@ApiQuery()` and `@ApiParam()` decorators also accept `enumName` alongside `enum`.

#### Property value examples

To set a single example for a property, use the `example` key:

[[CODE:16]]

To provide multiple examples, use the `examples` key and pass an object structured like this:

[[CODE:17]]

#### Raw definitions

In certain cases, such as deeply nested arrays or matrices, you may need to define your type manually:

[[CODE:18]]

You can also specify raw object schemas:

[[CODE:19]]

To manually define input/output content in controller classes, use the `schema` property:

[[CODE:20]]

#### Extra models

To define additional models that your controllers don't reference directly but the Swagger module should inspect, use the `@ApiExtraModels()` decorator:

[[CODE:21]]

> info **Hint** You only need to use `@ApiExtraModels()` once for a specific model class.

Alternatively, pass an options object with the `extraModels` property to the `SwaggerModule.createDocument()` method:

[[CODE:22]]

To get a reference (`$ref`) to your model, use the `getSchemaPath(ExtraModel)` function:

[[CODE:23]]

#### oneOf, anyOf, allOf

To combine schemas, use the `oneOf`, `anyOf`, or `allOf` keywords (see [oneOf, anyOf, allOf, not](https://swagger.io/docs/specification/data-models/oneof-anyof-allof-not/) in the Swagger documentation):

[[CODE:24]]

To define a polymorphic array (i.e., an array whose members span multiple schemas), use a raw definition (see above) to define your type by hand:

[[CODE:25]]

> info **Hint** The `getSchemaPath()` function is imported from `@nestjs/swagger`.

Both `Cat` and `Dog` must be defined as extra models with the `@ApiExtraModels()` decorator (at the class level).

#### Schema name and description

The name of the generated schema is based on the name of the original model class (for example, the `CreateCatDto` model generates a `CreateCatDto` schema). To change the schema name, use the `@ApiSchema()` decorator:

[[CODE:26]]

The model above is translated into the `CreateCatRequest` schema.

By default, the generated schema has no description. To add one, use the `description` attribute:

[[CODE:27]]

The description is then included in the schema:

[[CODE:28]]
