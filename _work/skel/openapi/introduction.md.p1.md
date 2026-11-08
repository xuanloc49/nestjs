### Introduction

The [OpenAPI](https://swagger.io/specification/) specification is a language-agnostic definition format for describing RESTful APIs. Nest provides a dedicated [module](https://github.com/nestjs/swagger) that generates such a specification from decorators in your code.

#### Installation

To begin, install the required dependency:

[[CODE:1]]

> warning **Warning** If you use Fastify, also install `@fastify/static`:
>
> [[CODE:2]]

#### Bootstrap

Once the installation is complete, open the `main.ts` file and initialize Swagger using the `SwaggerModule` class:

[[CODE:3]]

> info **Hint** Wrapping `SwaggerModule.createDocument()` in a factory function defers document generation until the document is first requested, which saves initialization time. The resulting document is a serializable object that conforms to the [OpenAPI Document](https://swagger.io/specification/#openapi-document) specification. Instead of serving it over HTTP, you can also save it as a JSON or YAML file and use it elsewhere.

> warning **Warning** If you call `createDocument()` eagerly (rather than in a factory function, as shown above), make sure `app.enableVersioning()` runs first. Otherwise, the generated `paths` are missing the version prefix. The factory pattern is unaffected, because the document isn't built until it is first requested.

`DocumentBuilder` structures a base document that conforms to the OpenAPI Specification. Its methods let you set properties such as the title, description, and version. To create a full document (with all HTTP routes defined), use the `createDocument()` method of the `SwaggerModule` class. It takes two arguments: an application instance and the base document configuration returned by `DocumentBuilder#build()`. An optional third argument, of type `SwaggerDocumentOptions`, is covered in the [document options](/openapi/introduction#document-options) section.

Next, call the `setup()` method. It accepts:

1. The path to mount the Swagger UI on
2. An application instance
3. The document object, or a factory function that returns it (as above)
4. An optional configuration object (see [setup options](/openapi/introduction#setup-options))

Now run the following command to start the HTTP server:

[[CODE:4]]

While the application is running, open your browser and navigate to `http://localhost:3000/api`. You should see the Swagger UI.

<figure><img src="/assets/swagger1.png" /></figure>

The `SwaggerModule` automatically reflects all of your endpoints.

> info **Hint** To generate and download a Swagger JSON file, navigate to `http://localhost:3000/api-json` (assuming that your Swagger documentation is available under `http://localhost:3000/api`).
> You can also expose it on a route of your choice with the `jsonDocumentUrl` option of the `setup()` method:
>
> [[CODE:5]]
>
> This exposes it at `http://localhost:3000/swagger/json`.

> info **Hint** Swagger UI works with the default [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) of Nest's built-in [security headers](/security/helmet). If you add scripts through `customJs`/`customJsStr`, or serve Swagger UI over plain HTTP outside local development, see [Swagger UI and GraphQL IDEs](/security/helmet#swagger-ui-and-graphql-ides) for the directives to adjust.

> warning **Warning** When you register `helmet` directly with Fastify instead, its [CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) can block the Swagger UI. To resolve this conflict, configure the CSP as shown below:
>
> [[CODE:6]]

#### Document options

When creating a document, you can pass extra options to fine-tune the library's behavior. These options are of type `SwaggerDocumentOptions`:

[[CODE:7]]

For example, to generate operation names like `createUser` instead of `UsersController_createUser`, set the following:

[[CODE:8]]

#### Standard Schema (Zod, Valibot)

Nest route parameter decorators accept a [Standard Schema](https://standardschema.dev/) compatible schema through their `schema` option (see the [controllers](/controllers#request-object) chapter):

[[CODE:9]]

The Swagger module picks up these schemas and turns them into request bodies and parameters in the generated document.

##### Libraries that need no configuration

If your validation library implements the **Standard JSON Schema** extension (that is, its schemas expose `~standard.jsonSchema`), Nest converts the schemas itself, and there is nothing to configure. Zod 4.2 and later implements this extension, for example. Nest requests the `openapi-3.0` target and uses the `input` or `output` variant, depending on whether the schema describes a request or a response.

##### Supplying a converter

For libraries that don't expose that extension (or when you want to control the conversion yourself), provide a `standardSchemaConverter` in `SwaggerDocumentOptions`. It receives the raw schema and the `schemaType` being generated, and returns the converted OpenAPI schema:

[[CODE:10]]

Nest calls the converter before trying the native conversion. Returning `undefined` tells Nest that the converter doesn't handle this schema, so Nest falls back to the native conversion described above. This makes it safe to support several libraries from one converter.

For **Zod**, you can use [zod-openapi](https://github.com/samchungy/zod-openapi):

[[CODE:11]]

[[CODE:12]]

For **Valibot**, use [@valibot/to-json-schema](https://github.com/fabian-hiller/valibot/tree/main/packages/to-json-schema):

[[CODE:13]]

[[CODE:14]]

The two converters differ in one respect. `createSchema()` can hoist reusable definitions, so its result carries a `components` map, which you pass through and Nest merges into the document's shared components. `toJsonSchema()` returns a single self-contained schema, so the Valibot converter omits `components`.

##### Supporting several libraries at once

Because the converter receives the schema as `unknown`, you can branch on the schema's vendor and support more than one library in the same application. Every Standard Schema exposes its vendor at `~standard.vendor`:

[[CODE:15]]

> warning **Warning** Always narrow by vendor before calling a library-specific converter. Passing a Valibot schema to `createSchema()` (or the reverse) throws at document generation time instead of failing gracefully.

> info **Hint** `schemaType` matters when your schema performs transformations: the `input` shape is what clients send, and the `output` shape is what your handler receives after parsing. Nest requests the variant that fits the position being documented, so pass the value straight through to your converter instead of hardcoding one.

#### Setup options

You can configure Swagger UI by passing an options object that implements the `SwaggerCustomOptions` interface as the fourth argument of the `SwaggerModule#setup()` method.

[[CODE:16]]

> info **Hint** `ui` and `raw` are independent options. Disabling the Swagger UI (`ui: false`) doesn't disable the API definitions (JSON/YAML). Conversely, disabling the API definitions (`raw: []`) doesn't disable the Swagger UI.
>
> For example, the following configuration disables the Swagger UI but keeps the JSON API definition available:
>
> [[CODE:17]]
>
> In this case, `http://localhost:3000/api-json` is still accessible, but `http://localhost:3000/api` (the Swagger UI) is not.

#### Example

A working example is available in the [Nest repository](https://github.com/nestjs/nest/tree/master/sample/11-swagger).
