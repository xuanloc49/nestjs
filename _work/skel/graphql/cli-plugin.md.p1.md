### CLI Plugin

> warning **Warning** This chapter applies only to the code first approach.

TypeScript's metadata reflection system has several limitations that make it impossible to, for instance, determine which properties a class consists of, or whether a given property is optional or required. However, some of these constraints can be addressed at compile time. Nest provides a plugin that enhances the TypeScript compilation process to reduce the amount of boilerplate code required.

> info **Hint** This plugin is **opt-in**. If you prefer, you can declare all decorators manually, or only specific decorators where you need them.

#### Overview

The GraphQL plugin automatically does the following:

- annotate all properties of input object, object type, and args classes with `@Field`, unless `@HideField` is used
- set the `nullable` property depending on the question mark (e.g., `name?: string` sets `nullable: true`)
- set the `type` property depending on the type (arrays are supported as well)
- generate descriptions for properties based on comments (if `introspectComments` is set to `true`)

Your filenames **must have** one of the following suffixes to be analyzed by the plugin: `['.input.ts', '.args.ts', '.entity.ts', '.model.ts']` (e.g., `author.entity.ts`). If you use a different suffix, adjust the plugin's behavior with the `typeFileNameSuffix` option (see below).

With what we've covered so far, you have to duplicate a lot of code to tell the package how your type should be declared in GraphQL. For example, you could define an `Author` class as follows:

[[CODE:1]]

While this isn't a significant issue in medium-sized projects, it becomes verbose and hard to maintain once you have a large set of classes.

With the GraphQL plugin enabled, the class definition above can be declared as follows:

[[CODE:2]]

The plugin adds the appropriate decorators on the fly based on the **Abstract Syntax Tree**, so you don't have to scatter `@Field` decorators throughout the code.

> info **Hint** The plugin automatically generates any missing GraphQL properties. If you need to override them, set them explicitly with `@Field()`.

#### Comments introspection

With the comments introspection feature enabled, the CLI plugin generates descriptions for fields based on comments.

For example, consider a `roles` property:

[[CODE:3]]

Here, you must duplicate the description. With `introspectComments` enabled, the CLI plugin extracts these comments and automatically provides descriptions for properties. The field above can then be declared as follows:

[[CODE:4]]

#### Using the CLI plugin

To enable the plugin, open `nest-cli.json` (if you use the [Nest CLI](/cli/overview)) and add the following `plugins` configuration:

[[CODE:5]]

Use the `options` property to customize the behavior of the plugin:

[[CODE:6]]

The `options` property accepts the following options:

[[CODE:7]]

<table>
  <tr>
    <th>Option</th>
    <th>Default</th>
    <th>Description</th>
  </tr>
  <tr>
    <td><code>typeFileNameSuffix</code></td>
    <td><code>['.input.ts', '.args.ts', '.entity.ts', '.model.ts']</code></td>
    <td>Suffixes of the files that contain GraphQL types</td>
  </tr>
  <tr>
    <td><code>introspectComments</code></td>
    <td><code>false</code></td>
    <td>If set to <code>true</code>, the plugin generates descriptions for properties based on comments</td>
  </tr>
  <tr>
    <td><code>esmCompatible</code></td>
    <td>Inferred from each file's module format</td>
    <td>If set to <code>true</code>, the plugin emits ESM-compatible code (no <code>require()</code> calls, and output extensions appended to relative imports).</td>
  </tr>
  <tr>
    <td><code>debug</code></td>
    <td><code>false</code></td>
    <td>If set to <code>true</code>, the plugin logs diagnostic messages (e.g., when it finds a type that isn't exported)</td>
  </tr>
</table>

If you don't use the CLI and have a custom `webpack` configuration instead, you can use this plugin in combination with `ts-loader`:

[[CODE:8]]

#### SWC builder

For standard (non-monorepo) setups, using CLI plugins with the SWC builder requires type checking to be enabled, as described in [SWC type checking](/recipes/swc#type-checking).

[[CODE:9]]

For monorepo setups, follow the instructions in [monorepo and CLI plugins](/recipes/swc#monorepo-and-cli-plugins).

[[CODE:10]]

Then, load the serialized metadata file in the `GraphQLModule` configuration, as shown below:

[[CODE:11]]

#### Integration with `ts-jest` (e2e tests)

When you run e2e tests with this plugin enabled, you may run into issues compiling the schema. For example, one of the most common errors is:

[[CODE:12]]

This happens because the `jest` configuration doesn't import the `@nestjs/graphql/plugin` plugin anywhere.

To fix this, create the following file in your e2e tests directory:

[[CODE:13]]

With this in place, import the AST transformer in your `jest` configuration file. By default (in the starter application), the e2e test configuration file is located in the `test` folder and is named `jest-e2e.json`.

[[CODE:14]]

If you use `jest@^29` or later, use the snippet below instead, as the previous approach is deprecated.

[[CODE:15]]
