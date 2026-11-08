### CLI Plugin

[TypeScript](https://www.typescriptlang.org/docs/handbook/decorators.html)'s metadata reflection system has several limitations. For instance, it can't determine which properties a class consists of, or whether a given property is optional or required. However, some of these constraints can be addressed at compile time. Nest provides a plugin that enhances the TypeScript compilation process to reduce the amount of boilerplate code required.

> info **Hint** This plugin is **opt-in**. If you prefer, you can declare all decorators manually, or only specific decorators where you need them.

#### Overview

The Swagger plugin automatically:

- annotates all DTO properties with `@ApiProperty()`, unless `@ApiHideProperty()` is used
- sets the `required` property depending on the question mark (e.g., `name?: string` sets `required: false`)
- sets the `type` or `enum` property depending on the type (arrays are supported as well)
- sets the `default` property based on the assigned default value
- sets several validation rules based on `class-validator` decorators (if `classValidatorShim` is set to `true`)
- adds a response decorator to every endpoint with a proper status and `type` (response model)
- generates descriptions for properties and endpoints based on comments (if `introspectComments` is set to `true`)
- generates example values for properties based on comments (if `introspectComments` is set to `true`)

For the plugin to analyze a DTO file, its filename **must have** one of the following suffixes: `['.dto.ts', '.entity.ts']` (e.g., `create-user.dto.ts`).

If you use a different suffix, adjust the plugin's behavior with the `dtoFileNameSuffix` option (see below).

Without the plugin, providing an interactive experience with the Swagger UI means duplicating a lot of code to tell the package how your models/components should be declared in the specification. For example, you could define a simple `CreateUserDto` class as follows:

[[CODE:1]]

While not a significant issue in medium-sized projects, this becomes verbose and hard to maintain once you have a large set of classes.

With the [Swagger plugin enabled](/openapi/cli-plugin#using-the-cli-plugin), you can declare the class above without any decorators:

[[CODE:2]]

> info **Note** The Swagger plugin derives the `@ApiProperty()` annotations from the TypeScript types and `class-validator` decorators, which describe your API in the generated Swagger UI documentation. Runtime validation, however, is still handled by the `class-validator` decorators, so you must keep using validators like `IsEmail()`, `IsNumber()`, etc.

In other words, if you rely on automatic annotations for the documentation and still want runtime validation, you still need the `class-validator` decorators.

> info **Hint** When you use [mapped type utilities](/openapi/mapped-types) (like `PartialType`) in DTOs, import them from `@nestjs/swagger` instead of `@nestjs/mapped-types` so that the plugin picks up the schema.

The plugin adds the appropriate decorators on the fly, based on the **Abstract Syntax Tree**, so you don't have to scatter `@ApiProperty()` decorators throughout the code.

> info **Hint** The plugin generates any missing Swagger properties. To override one, set it explicitly via `@ApiProperty()`.

#### Comments introspection

With the comments introspection feature enabled, the CLI plugin generates descriptions and example values for properties based on comments.

For example, consider a `roles` property:

[[CODE:3]]

You must duplicate both the description and the example values. With `introspectComments` enabled, the CLI plugin extracts these comments and provides descriptions (and examples, if defined) for properties automatically. The property above can then be declared as follows:

[[CODE:4]]

The `dtoKeyOfComment` and `controllerKeyOfComment` plugin options customize how the plugin assigns comment values to the `ApiProperty` and `ApiOperation` decorators, respectively. See the example below:

[[CODE:5]]

This is equivalent to the following:

[[CODE:6]]

> info **Hint** For models, the same logic applies, but with the `ApiProperty` decorator instead.

For controllers, you can provide not only a summary but also a description (remarks), tags (such as `@deprecated`), and response examples, like this:

[[CODE:7]]

As of `@nestjs/swagger` v12, the plugin (with `introspectComments` enabled) picks up `@param` tags as well, so route parameter descriptions can come from the same doc comment:

[[CODE:8]]

The plugin adds a `description` to the `@ApiQuery()` it already generates for optional `@Query()` parameters, generates `@ApiQuery({{ '{' }} name, description &#125;)` for documented required query parameters, and generates `@ApiParam({{ '{' }} name, description &#125;)` for documented `@Param()` parameters.

Descriptions are matched by the **variable name**, which is what `@param` documents. So `@Query('order_by') orderBy: string` is documented as `@param orderBy ...`, not `@param order_by ...`. Explicit `@ApiQuery()` / `@ApiParam()` decorators always take precedence and are never overwritten.

#### Using the CLI plugin

To enable the plugin, open `nest-cli.json` (if you use [Nest CLI](/cli/overview)) and add the following `plugins` configuration:

[[CODE:9]]

Use the `options` property to customize the behavior of the plugin:

[[CODE:10]]

The `options` property accepts the following options (among others):

[[CODE:11]]

<table>
  <tr>
    <th>Option</th>
    <th>Default</th>
    <th>Description</th>
  </tr>
  <tr>
    <td><code>dtoFileNameSuffix</code></td>
    <td><code>['.dto.ts', '.entity.ts']</code></td>
    <td>DTO (Data Transfer Object) files suffix</td>
  </tr>
  <tr>
    <td><code>controllerFileNameSuffix</code></td>
    <td><code>['.controller.ts']</code></td>
    <td>Controller files suffix</td>
  </tr>
  <tr>
    <td><code>classValidatorShim</code></td>
    <td><code>true</code></td>
    <td>If set to <code>true</code>, the plugin reuses <code>class-validator</code> validation decorators (e.g., <code>@Max(10)</code> adds <code>max: 10</code> to the schema definition)</td>
  </tr>
  <tr>
    <td><code>classTransformerShim</code></td>
    <td><code>false</code></td>
    <td>If set to <code>true</code>, the plugin skips properties decorated with <code>class-transformer</code>'s <code>@Exclude()</code>. If set to <code>'exclusive'</code>, it documents only properties decorated with <code>@Expose()</code> or <code>@ApiProperty()</code></td>
  </tr>
  <tr>
    <td><code>dtoKeyOfComment</code></td>
    <td><code>'description'</code></td>
    <td>The property key to set the comment text to on <code>ApiProperty</code>.</td>
  </tr>
  <tr>
    <td><code>controllerKeyOfComment</code></td>
    <td><code>'summary'</code></td>
    <td>The property key to set the comment text to on <code>ApiOperation</code>.</td>
  </tr>
  <tr>
    <td><code>introspectComments</code></td>
    <td><code>false</code></td>
    <td>If set to <code>true</code>, the plugin generates descriptions and example values for properties based on comments</td>
  </tr>
  <tr>
    <td><code>skipAutoHttpCode</code></td>
    <td><code>false</code></td>
    <td>Disables the automatic addition of <code>@HttpCode()</code> in controllers</td>
  </tr>
  <tr>
    <td><code>skipDefaultValues</code></td>
    <td><code>false</code></td>
    <td>If set to <code>true</code>, the plugin doesn't set the <code>default</code> property from property initializers</td>
  </tr>
  <tr>
    <td><code>autoFillEnumName</code></td>
    <td><code>false</code></td>
    <td>If set to <code>true</code>, the plugin sets <code>enumName</code> to the name of the enum type for enum properties that don't declare one</td>
  </tr>
  <tr>
    <td><code>esmCompatible</code></td>
    <td>Detected per file</td>
    <td>Makes the generated code compatible with ESM (<code>&#123; "type": "module" &#125;</code>). When omitted, the plugin detects whether each file is emitted as ESM from your compiler options and <code>package.json</code></td>
  </tr>
</table>

Delete the `/dist` folder and rebuild your application whenever you update plugin options.

If you don't use the CLI but have a custom `webpack` configuration instead, you can use this plugin in combination with `ts-loader`:

[[CODE:12]]

#### SWC builder

For standard (non-monorepo) setups, using CLI plugins with the SWC builder requires type checking to be enabled, as described in the [SWC recipe](/recipes/swc#type-checking).

[[CODE:13]]

For monorepo setups, follow the [monorepo and CLI plugins](/recipes/swc#monorepo-and-cli-plugins) instructions to create a `generate-metadata.ts` file, and then run it:

[[CODE:14]]

Then load the serialized metadata file with the `SwaggerModule#loadPluginMetadata()` method, as shown below:

[[CODE:15]]

#### Integration with `ts-jest` (e2e tests)

To run e2e tests, `ts-jest` compiles your source code files on the fly, in memory. This means it doesn't use the Nest CLI compiler, and it doesn't apply any plugins or perform AST transformations.

To enable the plugin, create the following file in your e2e tests directory:

[[CODE:16]]

With this in place, import the AST transformer in your `jest` configuration file. By default (in the starter application), the e2e test configuration file is located in the `test` folder and is named `jest-e2e.json`.

If you use `jest@<29`, use the snippet below:

[[CODE:17]]

If you use `jest@^29`, use the snippet below instead, because the previous approach is deprecated:

[[CODE:18]]

#### Troubleshooting `jest` (e2e tests)

If `jest` doesn't seem to pick up your configuration changes, Jest may have **cached** the build result. To apply the new configuration, clear Jest's cache directory by running the following command in your NestJS project folder:

[[CODE:19]]

If the automatic cache clearance fails, remove the cache folder manually with the following commands:

[[CODE:20]]
