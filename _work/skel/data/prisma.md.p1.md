### Prisma

[Prisma](https://www.prisma.io) is an [open-source](https://github.com/prisma/prisma) ORM for Node.js and TypeScript. You can use it as an **alternative** to writing plain SQL or to other database access tools, such as SQL query builders (like [knex.js](https://knexjs.org/)) or other ORMs (like [TypeORM](https://typeorm.io/) and [Sequelize](https://sequelize.org/)). Prisma supports PostgreSQL, MySQL, SQL Server, SQLite, CockroachDB, and MongoDB (see [supported databases](https://www.prisma.io/docs/orm/reference/supported-databases)). This chapter uses Prisma ORM 7, which works with the SQL databases; MongoDB projects stay on Prisma ORM 6 for now.

While you can use Prisma with plain JavaScript, it embraces TypeScript and provides a level of type safety that goes beyond the guarantees of other ORMs in the TypeScript ecosystem. See the [comparison of the type safety guarantees of Prisma and TypeORM](https://www.prisma.io/docs/orm/more/comparisons/prisma-and-typeorm#type-safety) for details.

Prisma has no Nest-specific package. Instead, you generate a type-safe client (Prisma Client) from your Prisma schema, wrap it in a provider, and inject that provider wherever you need database access. This chapter sets up that integration with a [SQLite](https://sqlite.org/) database, which needs no database server, and notes the differences for PostgreSQL, MySQL, and SQL Server along the way.

> info **Note** For an overview of how Prisma works, follow the [Quickstart](https://www.prisma.io/docs/getting-started/prisma-orm/quickstart/prisma-postgres) or read the [Introduction](https://www.prisma.io/docs/orm/overview/introduction/what-is-prisma) in the [Prisma documentation](https://www.prisma.io/docs). To add Prisma to a project that already has a database, follow the guide for [adding Prisma to an existing project](https://www.prisma.io/docs/getting-started/setup-prisma/add-to-existing-project-typescript-postgres). If you are migrating from TypeORM, read [Migrating from TypeORM to Prisma](https://www.prisma.io/docs/guides/migrate-from-typeorm).

#### Installation

Install the [Prisma CLI](https://www.prisma.io/docs/orm/tools/prisma-cli) and `dotenv` as development dependencies, then install Prisma Client and the driver adapter for your database. For SQLite, the `@prisma/adapter-better-sqlite3` adapter also installs the `better-sqlite3` driver:

[[CODE:1]]

> warning **Warning** Install Prisma ORM 7 explicitly, as shown above. At the time of writing, the `latest` tag of the `prisma` package on npm points to a Prisma 8 pre-release, which is a different CLI that doesn't provide the `prisma migrate` and `prisma generate` commands used in this chapter. Keep `prisma` and `@prisma/client` on the same major version.

<details><summary>Expand if you're using PostgreSQL, MySQL, SQL Server, or Azure SQL</summary>

Install the adapter for your database instead of `@prisma/adapter-better-sqlite3`. Each adapter package includes its database driver.

- For PostgreSQL:

[[CODE:2]]

- For MySQL (and MariaDB):

[[CODE:3]]

- For SQL Server and Azure SQL:

[[CODE:4]]

</details>

Next, create the initial Prisma setup with the `init` command. Prefix Prisma CLI commands with `npx` so that they run the version installed in your project:

[[CODE:5]]

This command creates the following files:

- `prisma/schema.prisma`: Contains your database schema, including the data source provider and the Prisma Client generator
- `prisma7.config.ts`: The Prisma configuration file, created in the project root. It sets the location of the schema and migrations, and reads the database connection URL from the `DATABASE_URL` environment variable. Prisma ORM releases before 7.10 name this file `prisma.config.ts`, which Prisma still recognizes.
- `.env`: A [dotenv](https://github.com/motdotla/dotenv) file that stores the database connection URL in the `DATABASE_URL` environment variable

It also adds `.env` and the generated client directory to your `.gitignore` file.

#### Set the generator output path

Prisma Client is generated into the directory set by the `output` field of the `generator` block, relative to the schema file. The `--output` option above places the client inside `src`, so that it's compiled along with the rest of your application. Without the option, `prisma init` sets the path to `../generated/prisma`, which is outside of `src`. You can also set the path directly in your Prisma schema:

[[CODE:6]]

Because the generated client is excluded from version control, run `npx prisma generate` before you build the application in a fresh checkout or in CI.

#### Configure the module format

Prisma infers the module format of the generated client from your `tsconfig.json` file. A NestJS project that uses ES modules (the default for new projects) gets an ES module client, so it needs no extra configuration.

If your project uses CommonJS, set `moduleFormat` in the generator to `cjs`:

[[CODE:7]]

> info **Note** The generated ESM client relies on `import.meta`, which isn't available in CommonJS. Releases before Prisma ORM 7.10 generate an ES module whenever `tsconfig.json` sets `module` to `nodenext`, even in a CommonJS project, so set `moduleFormat` explicitly rather than relying on the inference.

#### Set the database connection

The `datasource` block in your `schema.prisma` file defines which database you use. With the `--datasource-provider sqlite` option, `prisma init` sets its `provider` field to `sqlite` (the default is `postgresql`):

[[CODE:8]]

The connection URL itself isn't part of the schema: the Prisma configuration file reads it from the `DATABASE_URL` environment variable, which `prisma init` sets in `.env`:

[[CODE:9]]

A SQLite database is a plain file, so instead of a _host_ and _port_, the connection URL points to a local file, in this case `dev.db` in the project root. Prisma creates the file when you run the first migration.

The Prisma CLI loads `.env` through the `dotenv/config` import at the top of the Prisma configuration file. Your NestJS application doesn't load `.env` automatically, though. Install the `@nestjs/config` package and register the [`ConfigModule`](/application/configuration) globally in your `AppModule`, so that `PrismaService` can read `DATABASE_URL` through `ConfigService`:

[[CODE:10]]

[[CODE:11]]

<details><summary>Expand if you're using PostgreSQL, MySQL, SQL Server, or Azure SQL</summary>

With PostgreSQL, MySQL, and SQL Server, the connection URL points to the _database server_. Pass the matching provider to `prisma init` (e.g., `--datasource-provider postgresql`), or change the `provider` field of the `datasource` block, and set `DATABASE_URL` in `.env`. See the [connection URL reference](https://www.prisma.io/docs/orm/reference/connection-urls) for the required format.

**PostgreSQL**

[[CODE:12]]

[[CODE:13]]

Replace the uppercase placeholders with your database credentials. If you're unsure what to provide for the `SCHEMA` placeholder, it's most likely the default value `public`. If you don't have a PostgreSQL server yet, run `npx prisma dev` to start a local Prisma Postgres database in your terminal.

**MySQL**

[[CODE:14]]

[[CODE:15]]

Replace the uppercase placeholders with your database credentials.

**Microsoft SQL Server / Azure SQL Server**

[[CODE:16]]

[[CODE:17]]

Replace the uppercase placeholders with your database credentials. If you're unsure what to provide for the `encrypt` option, it's most likely the default value `true`.

</details>

#### Models and migrations

[Prisma Migrate](https://www.prisma.io/docs/orm/prisma-migrate/getting-started) generates SQL migration files from the declarative data model in your Prisma schema. These migration files are fully customizable, so you can configure additional features of the underlying database or include additional commands (e.g., for seeding).

This chapter uses two models. Add them to your `schema.prisma` file:

[[CODE:18]]

Then generate the first migration and run it against the database:

[[CODE:19]]

The `prisma migrate dev` command generates SQL files and runs them against the database directly. Because the database doesn't exist yet, it also creates the `dev.db` file. The migration files are created in the `prisma` directory:

[[CODE:20]]

<details><summary>Expand to view the generated SQL statements</summary>

The following tables were created in your SQLite database:

[[CODE:21]]

</details>

#### Generate Prisma Client

Prisma Client is a type-safe database client that's _generated_ from your Prisma schema. This approach lets Prisma Client expose [CRUD](https://www.prisma.io/docs/orm/prisma-client/queries/crud) operations that are _tailored_ specifically to your models. Generate the client and its types with the `generate` command:

[[CODE:22]]

`prisma migrate dev` doesn't run this command for you. Whenever you change your schema, rerun `prisma generate` to keep the client and its types in sync.

The generated `client.ts` file is the entry point of the client. It exports the `PrismaClient` class, a type for each model (e.g., `User` and `Post`), and the `Prisma` namespace, which contains the input types for queries (e.g., `Prisma.UserCreateInput`). Like any other relative import in an ESM project, import it with a `.js` extension (`./generated/prisma/client.js`).

#### PrismaService

In a NestJS application, you expose Prisma Client through a provider. Create a `PrismaService` class that extends `PrismaClient`, so that the service has the full Prisma Client API, and pass the driver adapter for your database to the `PrismaClient` constructor. Prisma ORM 7 requires a driver adapter (or a Prisma Accelerate URL) to create a client.

Create a `prisma.service.ts` file in the `src/prisma` directory:

[[CODE:23]]

The constructor reads `DATABASE_URL` through `ConfigService` before it calls `super()`. The `getOrThrow()` method throws an error if the variable isn't set, so a missing connection URL stops the application at startup. The `onModuleInit()` and `onModuleDestroy()` hooks manage the connection, as described in [Connection lifecycle](#connection-lifecycle).

> info **Hint** If you don't use `@nestjs/config`, start Node.js with the `--env-file=.env` flag and read `process.env.DATABASE_URL` in the constructor instead.

<details><summary>Expand if you're using PostgreSQL, MySQL, SQL Server, or Azure SQL</summary>

Replace `PrismaBetterSqlite3` with the adapter class for your database (`PrismaPg`, `PrismaMariaDb`, or `PrismaMssql`), and pass it the connection settings its driver expects. Each of these adapters also accepts a connection string. For example, with PostgreSQL:

[[CODE:24]]

</details>

#### Connection lifecycle

Prisma Client connects lazily, when it sends the first query. Calling `$connect()` in the `onModuleInit()` hook connects during application bootstrap instead, so a misconfigured connection fails at startup rather than on the first request.

Calling `$disconnect()` in the `onModuleDestroy()` hook closes the connection when the application shuts down. It also disposes of the driver adapter, which closes the underlying driver connection (for example, it ends the connection pool that `PrismaPg` creates). Nest calls `onModuleDestroy()` when you call `app.close()`. To also call it when the process receives a termination signal, such as `SIGTERM`, enable shutdown hooks in your `main.ts` file:

[[CODE:25]]

See [Application shutdown](/fundamentals/lifecycle-events#application-shutdown) to learn more about shutdown hooks.

> info **Hint** Prisma ORM 7 doesn't support the `beforeExit` event (`$on('beforeExit', ...)`) that older Prisma integrations used to close the application. Use the Nest lifecycle hooks shown above instead.

#### PrismaModule

Register `PrismaService` in a dedicated module that exports it. Create a `prisma.module.ts` file next to the service:

[[CODE:26]]

Import `PrismaModule` into every module that needs database access. Providers are singletons by default, so all importing modules share the same `PrismaService` instance and its connection.

> info **Hint** If most of your modules need database access, you can decorate `PrismaModule` with `@Global()` and import it only once, in your root module. See [Global modules](/modules#global-modules) for the trade-offs.

#### Querying from services

With `PrismaModule` in place, inject `PrismaService` into your providers and query the database through its model properties, such as `this.prisma.user`. The following `UsersService` wraps the CRUD queries for the `User` model:

[[CODE:27]]

The service uses the generated types for its parameters and return values, so you don't need to write separate interfaces for your models. In a real-world application, the service is also the place for your business logic. For example, a `UsersService` could have an `updatePassword()` method responsible for updating a user's password.

A controller then exposes the service through route handlers:

[[CODE:28]]

> info **Hint** The generated types exist only at compile time, so the `ValidationPipe` can't use them to validate request payloads. To validate a request body, declare a DTO class, as described in [Validation](/application/validation).

Finally, register the controller and the service in a `UsersModule` that imports `PrismaModule`, and import `UsersModule` into your `AppModule`:

[[CODE:29]]

#### Transactions

Prisma Client offers several ways to run queries in a transaction (see [Transactions and batch queries](https://www.prisma.io/docs/orm/prisma-client/queries/transactions)):

- **Nested writes**, which create or update a record together with related records in a single query, run in a transaction automatically.
- **Sequential operations**: pass an array of queries to `$transaction()`. Prisma runs them in order, in a single transaction, and resolves to an array with their results.
- **Interactive transactions**: pass an async function to `$transaction()`. Prisma commits the transaction when the function resolves and rolls it back when it throws.

The following methods show the last two forms in the `UsersService`:

[[CODE:30]]

Inside an interactive transaction, send every query through the transaction client (`tx`) that Prisma passes to the function. Queries sent through `this.prisma` run outside the transaction. Both forms of `$transaction()` accept an options object as the second argument, with the `maxWait`, `timeout`, and `isolationLevel` properties.

Passing `tx` through every method that takes part in a transaction couples your services to one another. To declare transaction boundaries with a decorator instead, use the transactional plugin of the [`nestjs-cls`](/recipes/async-local-storage#nestjs-cls) package with its [Prisma adapter](https://papooch.github.io/nestjs-cls/plugins/available-plugins/transactional/prisma-adapter) (`@nestjs-cls/transactional-adapter-prisma`). It keeps the active transaction client in async local storage and provides a `@Transactional()` decorator and an injectable `TransactionHost`.

#### Testing

When you unit test a provider that depends on `PrismaService`, you usually want to avoid a database connection. Because `PrismaService` is a regular class provider, you can replace it with a mock using the class itself as the injection token and any of the standard [custom provider](/fundamentals/custom-providers) techniques, such as `useValue`:

[[CODE:31]]

The mock replaces `PrismaService` entirely, so its `onModuleInit()` hook doesn't run and the test never opens a database connection. When you test a module that imports `PrismaModule`, replace the provider with `overrideProvider(PrismaService)` instead. See [Testing](/fundamentals/testing) for more testing utilities.

#### Example

Ready-to-run example projects for [REST](https://github.com/prisma/prisma-examples/tree/b53fad046a6d55f0090ddce9fd17ec3f9b95cab3/orm/nest) and [GraphQL](https://github.com/prisma/prisma-examples/tree/b53fad046a6d55f0090ddce9fd17ec3f9b95cab3/orm/nest-graphql) are available in the [`prisma-examples`](https://github.com/prisma/prisma-examples/) repository. For more resources, see [NestJS & Prisma](https://www.prisma.io/nestjs) on the Prisma website.
