### Configuration

Applications often run in different **environments**, and each environment needs its own configuration settings. For example, the local environment typically relies on database credentials that are valid only for the local database instance, while the production environment uses a separate set of credentials. Since configuration variables change between environments, best practice is to [store configuration variables](https://12factor.net/config) in the environment.

Externally defined environment variables are visible inside Node.js through the `process.env` global. You could handle multiple environments by setting the environment variables separately in each one. This quickly gets unwieldy, especially in development and testing environments, where these values need to be easy to mock or change.

In Node.js applications, it's common to represent each environment with a `.env` file that holds key-value pairs. Running an app in a different environment is then a matter of swapping in the correct `.env` file.

A good way to apply this technique in Nest is to create a `ConfigModule` that exposes a `ConfigService`, which loads the appropriate `.env` file. You can write such a module yourself, but for convenience, Nest provides the `@nestjs/config` package. This chapter covers that package.

#### Installation

To get started, install the required dependency:

[[CODE:1]]

> info **Hint** The `@nestjs/config` package internally uses [dotenv](https://github.com/motdotla/dotenv).

> warning **Note** `@nestjs/config` requires TypeScript 4.1 or later.

#### Getting started

Once the installation is complete, import the `ConfigModule`. Typically, you import it into the root `AppModule` and control its behavior with the `.forRoot()` static method. During this step, environment variable key/value pairs are parsed and resolved. Later, you'll see several options for accessing the `ConfigService` class of the `ConfigModule` in other feature modules.

[[CODE:2]]

This code loads and parses a `.env` file from the default location (the directory the process is started from, typically the project root), merges the key/value pairs from the `.env` file with the environment variables assigned to `process.env`, and stores the result in a private structure that you can access through the `ConfigService`. The `forRoot()` method registers the `ConfigService` provider, which provides a `get()` method for reading these parsed and merged configuration variables. Since `@nestjs/config` relies on [dotenv](https://github.com/motdotla/dotenv), it uses that package's rules for resolving conflicts in environment variable names. When a key exists both in the runtime environment (e.g., set through a shell export like `export DATABASE_USER=test`) and in a `.env` file, the runtime environment variable takes precedence. To let values from the `.env` file win instead, set the `override` option to `true`.

A sample `.env` file looks like this:

[[CODE:3]]

If you need some environment variables to be available before the `ConfigModule` is loaded and the Nest application is bootstrapped (for example, to pass the microservice configuration to the `NestFactory#createMicroservice()` method), use the `--env-file` option of the Nest CLI. It specifies the path to a `.env` file to load before the application starts. The CLI passes the file to the Node.js `--env-file` flag; see the [Node.js documentation](https://nodejs.org/dist/v20.18.1/docs/api/cli.html#--env-fileconfig) for details.

[[CODE:4]]

#### Custom env file path

By default, the package looks for a `.env` file in the current working directory (typically the root directory of the application). To specify another path for the `.env` file, set the `envFilePath` property of the optional options object you pass to `forRoot()`, as follows:

[[CODE:5]]

You can also specify multiple paths for `.env` files:

[[CODE:6]]

If a variable is found in multiple files, the first one takes precedence.

#### Disable env variables loading

If you don't want to load the `.env` file and only want to access environment variables from the runtime environment (e.g., set through shell exports like `export DATABASE_USER=test`), set the `ignoreEnvFile` property of the options object to `true`:

[[CODE:7]]

#### Native `.env` support

Node.js can load a `.env` file by itself, with the `--env-file` flag (the `nest start --env-file` option shown above relies on it) or with the `process.loadEnvFile()` method. To let Node.js load the file and keep using `ConfigModule` for everything else, set `ignoreEnvFile` to `true` as shown above, so that the module reads only `process.env`:

[[CODE:8]]

Since the variables are already in `process.env` when `forRoot()` runs, validation, `ConfigService#get()`, and `registerAs()` factories work as usual. `ConfigModule` treats these variables as predefined, though, so they're validated only while `validatePredefined` keeps its default value of `true`. A variable that is already set in the runtime environment always wins over the file (there's no equivalent of the `override` option), and with several `--env-file` flags, the last file takes precedence, which is the opposite of `envFilePath`.

`process.loadEnvFile()` must run before `AppModule` is imported, because `forRoot()` reads `process.env` while the `app.module` file is being evaluated. A call in the body of `main.ts` comes too late, so put it in a separate file and import that file first:

[[CODE:9]]

Alternatively, keep `ConfigModule` in charge of loading the files (`envFilePath`, `override`, and so on) and replace only the parser through the `parser` option. The parser receives the contents of each file as a `Buffer` and returns the key/value pairs (the default is `dotenv.parse`). Since `util.parseEnv()` accepts only a string, convert the buffer first:

[[CODE:10]]

> warning **Warning** The Node.js parser behind these APIs isn't fully compatible with dotenv. For example, a UTF-8 BOM ends up in the first key name, a quote inside a quoted value ends the value (`'it's here'` becomes `it`), and a value made only of spaces swallows the next line, so the variable defined there is lost. Its behavior has also changed across Node.js 20.x and 22.x minor releases. Node.js doesn't expand variables, and `parseEnv()` returns the keys sorted by name, so don't combine the `parser` option with [`expandVariables`](/application/configuration#expandable-variables): a reference to a variable whose name sorts later resolves as if that variable weren't set.

#### Use module globally

To use `ConfigModule` in other modules, you need to import it (as with any Nest module). Alternatively, declare it as a [global module](/modules#global-modules) by setting the `isGlobal` property of the options object to `true`, as shown below. In that case, once `ConfigModule` is loaded in the root module (e.g., `AppModule`), you don't need to import it in other modules.

[[CODE:11]]

#### Custom configuration files

For more complex projects, you can use custom configuration files that return nested configuration objects. This lets you group related configuration settings by function (e.g., database-related settings) and store them in individual files, so you can manage them independently.

A custom configuration file exports a factory function that returns a configuration object. The configuration object can be any arbitrarily nested plain JavaScript object. Inside the factory, the `process.env` object contains the fully resolved environment variable key/value pairs (with the `.env` file and externally defined variables resolved and merged as described in [Getting started](/application/configuration#getting-started)). Since you control the returned configuration object, you can add any logic you need to cast values to the appropriate type, set default values, and so on. For example:

[[CODE:12]]

Load this file with the `load` property of the options object you pass to the `ConfigModule.forRoot()` method:

[[CODE:13]]

> info **Hint** The value assigned to the `load` property is an array, so you can load multiple configuration files (e.g., `load: [databaseConfig, authConfig]`).

Custom configuration files also let you load configuration from other formats, such as YAML. Here is an example of a configuration in YAML format:

[[CODE:14]]

To read and parse YAML files, you can use the `js-yaml` package:

[[CODE:15]]

Once the package is installed, use its `load()` function to read the YAML file created above:

[[CODE:16]]

> warning **Note** The Nest CLI doesn't automatically copy your "assets" (non-TS files) to the `dist` folder during the build process. To make sure that your YAML files are copied, specify them in the `compilerOptions#assets` object in the `nest-cli.json` file. As an example, if the `config` folder is at the same level as the `src` folder, add `compilerOptions#assets` with the value `"assets": [{{ '{' }}"include": "../config/*.yaml", "outDir": "./dist/config"{{ '}' }}]`. See [Assets](/cli/monorepo#assets) for details.

Configuration files aren't validated automatically, even if you use the `validationSchema` option of the `ConfigModule` (it only applies to environment variables). If you need validation or want to apply transformations, handle them in the factory function, where you have full control over the configuration object.

For example, to ensure that the port is within a certain range, add a validation step to the factory function:

[[CODE:17]]

Now, if the port is outside the specified range, the application throws an error during startup.

<app-banner-observe></app-banner-observe>

#### Using the `ConfigService`

To access configuration values, first inject `ConfigService`. As with any provider, you need to import its containing module, the `ConfigModule`, into the module that uses it (unless you set the `isGlobal` property of the options object passed to `ConfigModule.forRoot()` to `true`). Import it into a feature module as shown below:

[[CODE:18]]

Then inject it through the constructor:

[[CODE:19]]

> info **Hint** Import `ConfigService` from the `@nestjs/config` package.

Then use it in your class:

[[CODE:20]]

As shown above, use the `configService.get()` method to get a simple environment variable by passing the variable name. You can pass a type argument as a TypeScript type hint (e.g., `get<string>(...)`). The `get()` method can also traverse a nested custom configuration object (created with a [custom configuration file](/application/configuration#custom-configuration-files)), as shown in the second example.

You can also get the whole nested custom configuration object using an interface as the type hint:

[[CODE:21]]

The `get()` method also takes an optional second argument that defines a default value, returned when the key doesn't exist:

[[CODE:22]]

If a value is required, use the `getOrThrow()` method instead. It accepts the same arguments as `get()`, but throws an error if the resolved value is `undefined`, and its return type excludes `undefined`:

[[CODE:23]]

`ConfigService` has two optional generics (type arguments). The first one helps prevent accessing a configuration property that doesn't exist:

[[CODE:24]]

With the `infer` property set to `true`, the `ConfigService#get` method infers the property type from the interface. For example, `port` is typed as `number`, since `PORT` has a `number` type in the `EnvironmentVariables` interface (with the `strictNullChecks` compiler option enabled, the type is `number | undefined`).

With the `infer` feature, you can also infer the type of a nested custom configuration object's property, even when using dot notation:

[[CODE:25]]

The second generic relies on the first one. It acts as a type assertion that removes the `undefined` type that the `ConfigService` methods can return when `strictNullChecks` is enabled. For instance:

[[CODE:26]]

> info **Hint** To make the `ConfigService#get` method ignore `process.env` variables and retrieve values only from custom configuration files (and from validated environment variables, if you use validation), set the `skipProcessEnv` option to `true` in the options object passed to `ConfigModule.forRoot()`.

#### Configuration namespaces

The `ConfigModule` lets you define and load multiple custom configuration files, as shown in [Custom configuration files](/application/configuration#custom-configuration-files) above. You can manage complex configuration hierarchies with nested configuration objects, as shown in that section. Alternatively, you can return a "namespaced" configuration object with the `registerAs()` function, as follows:

[[CODE:27]]

As with custom configuration files, inside your `registerAs()` factory function, the `process.env` object contains the fully resolved environment variable key/value pairs (with the `.env` file and externally defined variables resolved and merged as described in [Getting started](/application/configuration#getting-started)).

> info **Hint** The `registerAs()` function is exported from the `@nestjs/config` package.

Load a namespaced configuration with the `load` property of the `forRoot()` method's options object, in the same way you load a custom configuration file:

[[CODE:28]]

To get the `host` value from the `database` namespace, use dot notation. Use `'database'` as the prefix of the property name. It corresponds to the name of the namespace (passed as the first argument to the `registerAs()` function):

[[CODE:29]]

Alternatively, you can inject the `database` namespace directly, which gives you strong typing:

[[CODE:30]]

> info **Hint** The `ConfigType` type is exported from the `@nestjs/config` package.

#### Namespaced configurations in modules

To use a namespaced configuration as the configuration object of another module in your application, use the `.asProvider()` method of the configuration object. This method converts your namespaced configuration into a provider definition that you can pass to the `forRootAsync()` method (or equivalent) of the module you want to configure:

[[CODE:31]]

To understand how the `.asProvider()` method works, look at its return value:

[[CODE:32]]

This structure lets you plug namespaced configurations into other modules without writing repetitive boilerplate code, which keeps your application organized and modular.

#### Cache environment variables

Accessing `process.env` can be slow. To improve the performance of the `ConfigService#get` method for variables stored in `process.env`, set the `cache` property of the options object passed to `ConfigModule.forRoot()`:

[[CODE:33]]

#### Partial registration

So far, we've processed configuration files in the root module (e.g., `AppModule`) with the `forRoot()` method. In a more complex project structure, you may have feature-specific configuration files located in several different directories. Rather than loading all these files in the root module, you can use a feature of the `@nestjs/config` package called **partial registration**, which references only the configuration files associated with each feature module. Use the `forFeature()` static method within a feature module to perform partial registration, as follows:

[[CODE:34]]

> warning **Warning** In some circumstances, you may need to access properties loaded through partial registration in the `onModuleInit()` hook rather than in a constructor. This is because the `forFeature()` method runs during module initialization, and the order of module initialization is indeterminate. If you access values loaded this way by another module in a constructor, the module that the configuration depends on may not have initialized yet. The `onModuleInit()` method runs only after all the modules it depends on have been initialized, so this technique is safe.

#### Schema validation

It's standard practice to throw an exception during application startup if required environment variables haven't been provided or don't meet certain validation rules. The `@nestjs/config` package supports two ways to do this:

- A [Standard Schema](https://standardschema.dev/)-compatible schema passed through the `validationSchema` option. Any library that implements the specification works, such as [Zod](https://zod.dev/), [Valibot](https://valibot.dev/), and [ArkType](https://arktype.io/).
- A custom `validate()` function that takes the environment variables as input.

Install the validation library of your choice. This example uses Zod:

[[CODE:35]]

Now define a validation schema and pass it through the `validationSchema` property of the options object passed to `forRoot()`, as shown below:

[[CODE:36]]

This schema sets default values for `NODE_ENV` and `PORT`, which are used if you don't provide these variables in the environment (`.env` file or process environment). To require a variable instead, leave it without a default. The validation step then throws an exception during bootstrap if the variable is missing.

Environment variables always arrive as strings, which is why `PORT` uses `z.coerce.number()`. `ConfigService` serves the values returned by the schema, so coercions and transformations declared in the schema apply to the configuration your application reads. Variables that the schema doesn't declare remain available through `ConfigService` as well.

By default, unknown environment variables (the many unrelated entries that `process.env` always carries, such as `PATH` and `HOME`) don't trigger a validation exception, and every failing variable is reported rather than only the first. Each validation error is formatted as `PATH: message`, and the errors are joined by newlines.

You can forward library-specific options through the `validationOptions` key. Because the option is typed against the Standard Schema specification, library-specific settings go under `libraryOptions`:

[[CODE:37]]

> info **Hint** Joi is still supported, but it requires **Joi v18 or later**, which implements the Standard Schema specification. Pass `Joi.object({{ '{' }} ... &#125;)` to `validationSchema` as before, and put Joi settings such as `allowUnknown` and `abortEarly` under `validationOptions.libraryOptions`. For Joi schemas, `@nestjs/config` keeps its historical defaults of `allowUnknown: true` and `abortEarly: false`, and merges the options you pass on top of them. For new projects, we recommend a modern Standard Schema library such as Zod instead.

> info **Hint** To disable validation of predefined environment variables, set the `validatePredefined` property to `false` in the options object passed to `forRoot()`. Predefined environment variables are process variables (`process.env` variables) that were set before the module was imported. For example, if you start your application with `PORT=3000 node main.js`, then `PORT` is a predefined environment variable.

#### Custom validate function

Alternatively, you can specify a **synchronous** `validate` function. It takes an object containing the environment variables (from the `.env` file and the process) and returns an object containing the validated environment variables, so you can convert or modify them if needed. If the function throws an error, the application doesn't bootstrap.

This example uses the `class-transformer` and `class-validator` packages. First, define:

- a class with validation constraints,
- a validate function that makes use of the `plainToInstance` and `validateSync` functions.

[[CODE:38]]

With this in place, pass the `validate` function as a configuration option of the `ConfigModule`:

[[CODE:39]]

#### Custom getter functions

`ConfigService` defines a generic `get()` method that retrieves a configuration value by key. You can also add getter functions for a more natural coding style:

[[CODE:40]]

> info **Hint** This example assumes that `AUTH_ENABLED` is a string. If your validation schema converts it to a boolean, `get()` returns the converted value, so return `this.configService.get<boolean>('AUTH_ENABLED')` directly instead of comparing it with `'true'`.

Now you can use the getter function as follows:

[[CODE:41]]

#### Environment variables loaded hook

If a module configuration depends on environment variables loaded from the `.env` file, use the `ConfigModule.envVariablesLoaded` hook to ensure that the file has been loaded before you read the `process.env` object:

[[CODE:42]]

This construction guarantees that all configuration variables are loaded once the `ConfigModule.envVariablesLoaded` promise resolves.

#### Conditional module configuration

Sometimes you may want to load a module conditionally and specify the condition in an environment variable. The `@nestjs/config` package provides a `ConditionalModule` for this purpose.

[[CODE:43]]

This module loads the `FooModule` unless the `USE_FOO` environment variable is set to `false` (case-insensitive). If the variable isn't defined, `FooModule` is loaded. You can also pass a custom condition: a function that receives the `process.env` reference and returns a boolean:

[[CODE:44]]

When you use the `ConditionalModule`, make sure the `ConfigModule` is also loaded in the application, so that the `ConfigModule.envVariablesLoaded` hook resolves. If the hook doesn't resolve within 5 seconds (or within the timeout, in milliseconds, set through the `timeout` property of the third `options` argument of the `registerWhen()` method), the `ConditionalModule` throws an error and Nest aborts starting the application.
