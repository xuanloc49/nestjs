### Hot Reload

**TypeScript compilation** has the biggest impact on your application's bootstrapping time. With [webpack](https://github.com/webpack/webpack) HMR (Hot-Module Replacement), you don't need to recompile the entire project each time a change occurs. This significantly decreases the time it takes to instantiate your application and makes iterative development much faster.

> warning **Warning** `webpack` doesn't automatically copy your assets (e.g., `graphql` files) to the `dist` folder. Similarly, `webpack` isn't compatible with static glob paths (e.g., the `entities` property in `TypeOrmModule`).

> warning **Warning** As of NestJS v12, the webpack builder is **deprecated** and Rspack is the default bundler for monorepos. This recipe targets webpack-based CommonJS projects, which is why the examples below use `module.hot` and a plain `bootstrap()` call rather than the ESM top-level `await` used elsewhere in these docs. For new projects, prefer `--builder rspack`.

### With CLI

If you use the [Nest CLI](/cli/overview), the configuration process is straightforward. The CLI wraps `webpack`, which lets you use the `HotModuleReplacementPlugin`.

#### Installation

First, install the required packages:

[[CODE:1]]

> info **Hint** If you use **Yarn Berry** (not classic Yarn), install the `webpack-pnp-externals` package instead of `webpack-node-externals`.

#### Configuration

Once the installation is complete, create a `webpack-hmr.config.js` file in the root directory of your application:

[[CODE:2]]

> info **Hint** With **Yarn Berry** (not classic Yarn), instead of using `nodeExternals` in the `externals` configuration property, use `WebpackPnpExternals` from the `webpack-pnp-externals` package: `WebpackPnpExternals({{ '{' }} exclude: ['webpack/hot/poll?100'] {{ '}' }})`.

This function takes the original object containing the default webpack configuration as its first argument, and a reference to the underlying `webpack` package used by the Nest CLI as its second argument. It returns a modified webpack configuration with the `HotModuleReplacementPlugin`, `WatchIgnorePlugin`, and `RunScriptWebpackPlugin` plugins.

#### Hot-Module Replacement

To enable **HMR**, open the application entry file (`main.ts`) and add the following webpack-related instructions:

[[CODE:3]]

> info **Hint** `app.close()` is asynchronous, but webpack does not await the `dispose()` callback. Stashing the returned promise on `module.hot.data` lets the next application instance await it before binding to the port again, which (together with `forceCloseConnections`) prevents `EADDRINUSE` errors on reload.

To simplify the execution process, add a script to your `package.json` file:

[[CODE:4]]

Then run the following command:

[[CODE:5]]

### Without CLI

If you don't use the [Nest CLI](/cli/overview), the configuration is slightly more complex and requires more manual steps.

#### Installation

First, install the required packages:

[[CODE:6]]

> info **Hint** If you use **Yarn Berry** (not classic Yarn), install the `webpack-pnp-externals` package instead of `webpack-node-externals`.

#### Configuration

Once the installation is complete, create a `webpack.config.js` file in the root directory of your application:

[[CODE:7]]

> info **Hint** With **Yarn Berry** (not classic Yarn), instead of using `nodeExternals` in the `externals` configuration property, use `WebpackPnpExternals` from the `webpack-pnp-externals` package: `WebpackPnpExternals({{ '{' }} exclude: ['webpack/hot/poll?100'] {{ '}' }})`.

This configuration tells webpack a few essential things about your application: the location of the entry file, the directory that holds the **compiled** files, and the loader used to compile source files. You can generally use this file as-is, even if you don't fully understand all of the options.

#### Hot-Module Replacement

To enable **HMR**, open the application entry file (`main.ts`) and add the following webpack-related instructions:

[[CODE:8]]

> info **Hint** `app.close()` is asynchronous, but webpack does not await the `dispose()` callback. Stashing the returned promise on `module.hot.data` lets the next application instance await it before binding to the port again, which (together with `forceCloseConnections`) prevents `EADDRINUSE` errors on reload.

To simplify the execution process, add a script to your `package.json` file:

[[CODE:9]]

Then run the following command:

[[CODE:10]]

#### Example

A working example is available in the [webpack sample](https://github.com/nestjs/nest/tree/master/sample/08-webpack) on GitHub.
