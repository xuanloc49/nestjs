### SWC

[SWC](https://swc.rs/) (Speedy Web Compiler) is an extensible Rust-based platform that can be used for both compilation and bundling. Using SWC with the Nest CLI is a straightforward way to significantly speed up your development process.

> info **Hint** SWC is approximately **20 times faster** than the default TypeScript compiler.

#### Installation

To get started, first install a few packages:

[[CODE:1]]

#### Getting started

Once the installation is complete, you can use the `swc` builder with the Nest CLI, as follows:

[[CODE:2]]

> info **Hint** If your repository is a monorepo, see the [Monorepo](/recipes/swc#monorepo) section.

Instead of passing the `-b` flag, you can set the `compilerOptions.builder` property to `"swc"` in your `nest-cli.json` file:

[[CODE:3]]

To customize the builder's behavior, pass an object containing two attributes, `type` (`"swc"`) and `options`, as follows:

[[CODE:4]]

For example, to make SWC compile `.jsx` and `.tsx` files, use the following configuration:

[[CODE:5]]

To run the application in watch mode, use the following command:

[[CODE:6]]

#### Type checking

Unlike the default TypeScript compiler, SWC doesn't perform any type checking itself. To turn type checking on, use the `--type-check` flag:

[[CODE:7]]

This command instructs the Nest CLI to run `tsc` in `noEmit` mode alongside SWC, which performs type checking asynchronously. Instead of passing the `--type-check` flag, you can also set the `compilerOptions.typeCheck` property to `true` in your `nest-cli.json` file:

[[CODE:8]]

#### CLI Plugins (SWC)

The `--type-check` flag automatically executes **NestJS CLI plugins** and produces a serialized metadata file, which the application can then load at runtime.

#### SWC configuration

The SWC builder is preconfigured to match the requirements of NestJS applications. However, you can customize the configuration by creating a `.swcrc` file in the root directory and adjusting the options as needed:

[[CODE:9]]

> info **Hint** The SWC builder emits the same module format as the TypeScript compiler would: ES modules when your `package.json` file sets `"type": "module"` (the default for new projects), and CommonJS otherwise. A `module` setting in `.swcrc` overrides this.

#### Monorepo

> info **Hint** As of NestJS v12, monorepos use the Rspack builder by default, which already compiles your code with SWC (through Rspack's built-in `swc-loader`). The following setup applies only if you use the deprecated webpack builder.

If your repository is a monorepo, then instead of using the `swc` builder, you have to configure `webpack` to use `swc-loader`.

First, install the required package:

[[CODE:10]]

Once the installation is complete, create a `webpack.config.js` file in the root directory of your application with the following content:

[[CODE:11]]

#### Monorepo and CLI plugins

If you use CLI plugins, `swc-loader` doesn't load them automatically. Instead, you have to create a separate file that loads them manually. To do so, create a `generate-metadata.ts` file next to the `main.ts` file with the following content:

[[CODE:12]]

> info **Hint** This example uses the `@nestjs/swagger` plugin, but you can use any plugin of your choice.

The `generate()` method accepts the following options:

|                    |                                                                                                |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| `watch`            | Whether to watch the project for changes.                                                      |
| `tsconfigPath`     | Path to the `tsconfig.json` file. Relative to the current working directory (`process.cwd()`). |
| `outputDir`        | Path to the directory where the metadata file is saved.                                        |
| `visitors`         | An array of visitors used to generate metadata.                                                |
| `filename`         | The name of the metadata file. Defaults to `metadata.ts`.                                      |
| `printDiagnostics` | Whether to print diagnostics to the console. Defaults to `true`.                               |

Finally, run the `generate-metadata` script in a separate terminal window with the following command:

[[CODE:13]]

#### Common pitfalls

If you use TypeORM, MikroORM, or any other ORM in your application, you may run into circular import issues. SWC doesn't handle **circular imports** well, so use the following workaround:

[[CODE:14]]

> info **Hint** The `Relation` type is exported from the `typeorm` package.

This prevents the property's type from being saved in the property metadata of the transpiled code, which avoids circular dependency issues.

If your ORM does not provide a similar workaround, you can define the wrapper type yourself:

[[CODE:15]]

For all [circular dependency injections](/fundamentals/circular-dependency) in your project, you also need to use the custom wrapper type described above:

[[CODE:16]]

### Jest + SWC

To use SWC with Jest (the default test runner for CommonJS projects), install the following packages:

[[CODE:17]]

Once the installation is complete, update your `package.json` or `jest.config.js` file (depending on your configuration) with the following content:

[[CODE:18]]

Additionally, add the `legacyDecorator` and `decoratorMetadata` `transform` properties to your `.swcrc` file:

[[CODE:19]]

If you use NestJS CLI plugins in your project, you have to run `PluginMetadataGenerator` manually. See the [Monorepo and CLI plugins](/recipes/swc#monorepo-and-cli-plugins) section to learn more.

### Vitest

[Vitest](https://vitest.dev/) is a fast, lightweight test runner designed to work with Vite. New NestJS projects that use ES modules (the default) are already set up with Vitest. This section shows how to configure Vitest to build your test files with SWC.

#### Installation

To get started, first install the required packages:

[[CODE:20]]

#### Configuration

Create a `vitest.config.ts` file in the root directory of your application with the following content:

[[CODE:21]]

This configuration file sets up the Vitest environment, root directory, and SWC plugin. You should also create a separate configuration file for e2e tests (e.g., `vitest.config.e2e.ts`), with an additional `include` field that specifies the glob pattern for the test files:

[[CODE:22]]

Additionally, you can set the `alias` options to support TypeScript paths in your tests:

[[CODE:23]]

### Path aliases

Vitest doesn't automatically resolve TypeScript path aliases such as `src/`, which can lead to dependency resolution errors during testing. To fix this, add the following `resolve.alias` configuration to your `vitest.config.ts` file:

[[CODE:24]]

This ensures that Vitest correctly resolves module imports, preventing errors related to missing dependencies.

#### Update imports in E2E tests

Change any E2E test imports that use `import * as request from 'supertest'` to `import request from 'supertest'`. `supertest` is a CommonJS module that exports a function, and in an ES module setup like Vitest's, a namespace import isn't callable, so you need the default import.

Lastly, update the test scripts in your `package.json` file:

[[CODE:25]]

These scripts run the tests, watch for changes, generate code coverage reports, and start a debugging session. The `test:e2e` script runs the E2E tests with the dedicated configuration file.

> info **Hint** A working example is available in the [nest-vitest repository](https://github.com/TrilonIO/nest-vitest).
