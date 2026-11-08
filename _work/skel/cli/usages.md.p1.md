### CLI command reference

#### nest new

Creates a new (standard mode) Nest project, or with `--minimal` a [one-file project](/cli/usages#one-file-projects).

[[CODE:1]]

##### Description

Creates and initializes a new Nest project. The command prompts for any information you don't pass as an option: the project name, the package manager, the module system (ESM or CommonJS), and whether to set up [NestJS Observe](/observability/overview).

> info **Hint** In non-interactive environments, such as CI, pass the project name and `--package-manager`. The module system then defaults to ESM, and Observe is set up only if you pass `--observe`.

> info **Hint** Choosing **ESM** scaffolds an ESM-first project that uses Vitest for testing. Choosing **CommonJS** scaffolds the traditional layout, which uses Jest. Both variants use oxlint for linting.

The command:

- Creates a folder with the given `<name>`
- Populates the folder with configuration files
- Creates subfolders for source code (`/src`) and end-to-end tests (`/test`)
- Populates the subfolders with default files for application components and tests
- If Observe was set up, offers to link the project to it once the dependencies are installed (in an interactive terminal only). Accepting runs `npx @nestjs/observe link`, which writes the app key and secret into `.env` - see [Linking from the terminal](/observability/sdk#linking-from-the-terminal)

##### Arguments

| Argument | Description                 |
| -------- | --------------------------- |
| `<name>` | The name of the new project |

##### Options

| Option                                | Description                                                                                                                                                                                                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--directory [directory]`             | Destination directory.                                                                                                                                                                                                                                        |
| `--dry-run`                           | Report the changes that would be made, without changing the filesystem.<br/> Alias: `-d`                                                                                                                                                                      |
| `--skip-git`                          | Skip git repository initialization.<br/> Alias: `-g`                                                                                                                                                                                                          |
| `--skip-install`                      | Skip package installation.<br/> Alias: `-s`                                                                                                                                                                                                                   |
| `--skip-tests`                        | Skip generating test files for the new project.<br/> Alias: `-t`                                                                                                                                                                                              |
| `--package-manager [package-manager]` | Package manager to use: `npm`, `yarn`, `pnpm`, or `bun`. The package manager must be installed globally.<br/> Alias: `-p`                                                                                                                                      |
| `--language [language]`               | Programming language: `TS` (default) or `JS`. The value is case-insensitive, and `typescript` / `javascript` are also accepted.<br/> Alias: `-l`                                                                                                                |
| `--collection [collectionName]`       | Schematics collection to use. Pass the package name of an installed npm package that contains the schematic.<br/> Alias: `-c`                                                                                                                                 |
| `--strict`                            | Enable TypeScript's `strict` mode (with `strictPropertyInitialization` disabled) in the generated `tsconfig.json`. Enabled by default, and there is no flag to disable it: to opt out, set `"strict": false` in `tsconfig.json` after generating the project. |
| `--format`                            | Format generated files using Prettier.                                                                                                                                                                                                                        |
| `--observe` / `--no-observe`          | Set up the `@nestjs/observe` SDK, or skip it, without being prompted. Omit both to be prompted in an interactive terminal (the prompt defaults to yes). Without a terminal, Observe is not set up.                                                            |
| `--minimal`                           | Generate an application whose code is one file, `src/main.ts`. See [One-file projects](/cli/usages#one-file-projects). TypeScript and ESM only.                                                                                                                 |

##### One-file projects

`nest new <name> --minimal` generates a real Nest application without the layout around it, for a small project or a first version:

[[CODE:2]]

[[CODE:3]]

Run it with `npm run start:dev`. It goes through the CLI, like any other Nest project, because the TypeScript compiler has to emit decorator metadata for injection by type to work. Under a tool that doesn't emit it, such as `tsx`, `appService` above is `undefined`.

There's no `nest-cli.json`, because the CLI's defaults already describe this layout, and no tests, linter, formatter, or README. Add any of them when you need them.

`nest generate` works here as it does anywhere else. With no `*.module.ts` file to register things in, it uses the module in `src/main.ts`:

[[CODE:4]]

This writes `src/users/` and adds `UsersModule` to the imports in `src/main.ts`. Spec files are left out while `package.json` doesn't list `@nestjs/testing`: install it, or pass `--spec`, to get them. When `src/main.ts` gets long, move the module to `src/app.module.ts` and export it, and `nest generate` registers things there instead.

The other options to `nest new` apply, with these differences:

- `--language js` is refused. JavaScript needs Babel and its own entry file to run decorators, so the project wouldn't stay one file.
- The project is always ESM, and you aren't prompted for a module system. For CommonJS, generate a standard project.
- `--observe` wires the SDK into `src/main.ts`. `npx @nestjs/observe link` then writes the key pair, as usual. Without `--observe`, adding the SDK later takes the [three edits in its quick start](https://observe.nestjs.com/documentation/sdk#quick-start), because `link` looks for the root module in a file that `main.ts` imports.
- `--skip-tests` has nothing to skip.

#### nest generate

Generates and/or modifies files based on a schematic.

[[CODE:5]]

##### Arguments

| Argument      | Description                                                                                              |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| `<schematic>` | The `schematic` or `collection:schematic` to generate. See the table below for the available schematics. |
| `<name>`      | The name of the generated component. If omitted, the schematic prompts for it.                           |

##### Schematics

| Name          | Alias | Description                                                                                                            |
| ------------- | ----- | ---------------------------------------------------------------------------------------------------------------------- |
| `app`         |       | Generate a new application within a monorepo (converting a standard mode structure to a monorepo).                     |
| `library`     | `lib` | Generate a new library within a monorepo (converting a standard mode structure to a monorepo).                         |
| `class`       | `cl`  | Generate a new class.                                                                                                  |
| `controller`  | `co`  | Generate a controller declaration.                                                                                     |
| `decorator`   | `d`   | Generate a custom decorator. As of v12, the generated decorator uses the `Reflector.createDecorator()` form.           |
| `filter`      | `f`   | Generate a filter declaration.                                                                                         |
| `gateway`     | `ga`  | Generate a gateway declaration.                                                                                        |
| `guard`       | `gu`  | Generate a guard declaration.                                                                                          |
| `interface`   | `itf` | Generate an interface.                                                                                                 |
| `interceptor` | `itc` | Generate an interceptor declaration.                                                                                   |
| `middleware`  | `mi`  | Generate a middleware declaration.                                                                                     |
| `module`      | `mo`  | Generate a module declaration.                                                                                         |
| `pipe`        | `pi`  | Generate a pipe declaration.                                                                                           |
| `provider`    | `pr`  | Generate a provider declaration.                                                                                       |
| `resolver`    | `r`   | Generate a resolver declaration.                                                                                       |
| `resource`    | `res` | Generate a new CRUD resource (TypeScript only). See the [CRUD (resource) generator](/recipes/crud-generator).          |
| `service`     | `s`   | Generate a service declaration.                                                                                        |

##### Options

| Option                          | Description                                                                                                     |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `--dry-run`                     | Report the changes that would be made, without changing the filesystem.<br/> Alias: `-d`                        |
| `--project [project]`           | Project that the element should be added to.<br/> Alias: `-p`                                                   |
| `--flat`                        | Do not generate a folder for the element.                                                                       |
| `--no-flat`                     | Generate a folder for the element.                                                                              |
| `--collection [collectionName]` | Schematics collection to use. Pass the package name of an installed npm package that contains the schematic.<br/> Alias: `-c` |
| `--spec`                        | Generate spec files (default, unless `package.json` doesn't list `@nestjs/testing`).                            |
| `--no-spec`                     | Skip generating spec files.                                                                                     |
| `--spec-file-suffix [suffix]`   | Use a custom suffix for spec files.                                                                             |
| `--skip-import`                 | Skip importing the generated element into its closest module.                                                   |
| `--format`                      | Format generated files using Prettier.                                                                          |
| `--type <type>`                 | (`resource` only) Transport layer: `rest`, `graphql-code-first`, `graphql-schema-first`, `microservice`, or `ws`. |
| `--crud [value]`                | (`resource` only) Whether to generate CRUD entry points (`true` or `false`).                                    |

#### nest build

Compiles an application or workspace into an output folder.

The `build` command is also responsible for:

- mapping paths (if you use path aliases) via `tsconfig-paths`
- annotating DTOs with OpenAPI decorators (if the `@nestjs/swagger` CLI plugin is enabled)
- annotating DTOs with GraphQL decorators (if the `@nestjs/graphql` CLI plugin is enabled)

[[CODE:6]]

##### Arguments

| Argument    | Description                                                                                  |
| ----------- | -------------------------------------------------------------------------------------------- |
| `[name...]` | The name of the project to build. Pass several names to build several projects. If omitted, the default project is built. |

##### Options

| Option                  | Description                                                                                                                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--path [path]`         | Path to `tsconfig` file. <br/>Alias `-p`                                                                                                                                                   |
| `--config [path]`       | Path to `nest-cli` configuration file. <br/>Alias `-c`                                                                                                                                     |
| `--watch`               | Run in watch mode (live-reload).<br /> With the `tsc` compiler, you can type `rs` to restart the application (when the `manualRestart` option is set to `true`). <br/>Alias `-w` |
| `--builder [name]`      | Builder to use for compilation (`tsc`, `swc`, or `rspack`). <br/>Alias `-b`                                                                                                                |
| `--webpack`             | Deprecated legacy flag for webpack-based compilation. Use `--builder rspack` or another explicit builder instead.                                                                         |
| `--webpackPath [path]`  | Deprecated legacy path to a webpack configuration file. Use the configuration supported by your selected builder instead.                                                                 |
| `--rspackPath [path]`   | Path to a Rspack configuration file.                                                                                                                                                      |
| `--tsc`                 | Force the use of `tsc` for compilation.                                                                                                                                                    |
| `--watchAssets`         | Watch non-TS files (assets such as `.graphql` files). See [Assets](/cli/monorepo#assets) for more details.                                                                                 |
| `--type-check`          | Enable type checking (when SWC is used).                                                                                                                                                   |
| `--no-type-check`       | Disable type checking (when SWC is used).                                                                                                                                                  |
| `--emit-declarations`   | Emit declaration files (`.d.ts`) when using the SWC builder.                                                                                                                               |
| `--all`                 | Build all projects in a monorepo.                                                                                                                                                          |
| `--parallel [concurrency]` | Build projects in parallel (use with `--all`). Pass a positive integer to limit concurrency, or omit the value for unlimited concurrency.                                                |
| `--silent`              | Suppress informational compiler logs.                                                                                                                                                      |
| `--preserveWatchOutput` | Keep outdated console output in watch mode instead of clearing the screen. (`tsc` watch mode only)                                                                                         |

#### nest start

Compiles and runs an application (or the default project in a workspace).

[[CODE:7]]

##### Arguments

| Argument | Description                                                          |
| -------- | -------------------------------------------------------------------- |
| `[name]` | The name of the project to run. If omitted, the default project runs. |

##### Options

| Option                  | Description                                                                                                                        |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `--path [path]`         | Path to `tsconfig` file. <br/>Alias `-p`                                                                                           |
| `--config [path]`       | Path to `nest-cli` configuration file. <br/>Alias `-c`                                                                             |
| `--watch`               | Run in watch mode (live-reload). <br/>Alias `-w`                                                                                   |
| `--builder [name]`      | Builder to use for compilation (`tsc`, `swc`, or `rspack`). <br/>Alias `-b`                                                      |
| `--preserveWatchOutput` | Keep outdated console output in watch mode instead of clearing the screen. (`tsc` watch mode only)                                 |
| `--watchAssets`         | Run in watch mode (live-reload), watching non-TS files (assets). See [Assets](/cli/monorepo#assets) for more details.              |
| `--debug [hostport]`    | Run in debug mode (with the `--inspect` flag). <br/>Alias `-d`                                                                     |
| `--webpack`             | Deprecated legacy flag for webpack-based compilation. Use `--builder rspack` or another explicit builder instead.                |
| `--webpackPath [path]`  | Deprecated legacy path to a webpack configuration file. Use the configuration supported by your selected builder instead.          |
| `--rspackPath [path]`   | Path to a Rspack configuration file.                                                                                              |
| `--tsc`                 | Force the use of `tsc` for compilation.                                                                                            |
| `--type-check`          | Enable type checking (when SWC is used).                                                                                           |
| `--no-type-check`       | Disable type checking (when SWC is used).                                                                                          |
| `--emit-declarations`   | Emit declaration files (`.d.ts`) when using the SWC builder.                                                                       |
| `--silent`              | Suppress informational compiler logs.                                                                                              |
| `--sourceRoot [sourceRoot]` | Root of the source code (overrides the `sourceRoot` setting in `nest-cli.json`).                                               |
| `--entryFile [entryFile]` | Entry file to run (overrides the `entryFile` setting in `nest-cli.json`).                                                        |
| `--exec [binary]`       | Binary to run (default: `node`). <br/>Alias `-e`                                                                                   |
| `--no-shell`            | Do not spawn child processes within a shell (see the Node.js `child_process.spawn()` documentation).                               |
| `--env-file [path]`     | Load environment variables from a file, relative to the current directory, and expose them to the application on `process.env`. Repeat the option to load several files. A file that doesn't exist is skipped, with a notice. |
| `-- [key=value]`        | Command-line arguments that the application can read from `process.argv`.                                                          |
