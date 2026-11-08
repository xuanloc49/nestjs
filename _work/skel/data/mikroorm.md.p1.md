### MikroORM

[MikroORM](https://mikro-orm.io) is a TypeScript ORM for Node.js based on the Data Mapper, Unit of Work, and Identity Map patterns. It supports MongoDB, MySQL, MariaDB, PostgreSQL, SQLite, Microsoft SQL Server, and Oracle. The `@mikro-orm/nestjs` package integrates it with Nest: it registers the ORM and its `EntityManager` as providers, provides repository injection, creates a request context for every HTTP request, and closes the database connection when the application shuts down.

This chapter covers the Nest-specific parts of the integration. See the [MikroORM documentation](https://mikro-orm.io/docs) for complete coverage of the ORM itself.

> info **Note** `@mikro-orm/nestjs` is a third-party package and is not managed by the NestJS core team. Report any issues with the library in the [mikro-orm/nestjs repository](https://github.com/mikro-orm/nestjs).

> info **Hint** This chapter targets MikroORM v7 and `@mikro-orm/nestjs` v7. If you're upgrading from MikroORM v6, see the [MikroORM v6 to v7 upgrading guide](https://mikro-orm.io/docs/upgrading-v6-to-v7).

#### Installation

Install the Nest module together with MikroORM, its decorators package, and the driver for your database. This chapter uses SQLite:

[[CODE:1]]

MikroORM provides a driver package for each supported database, such as `@mikro-orm/postgresql`, `@mikro-orm/mysql`, and `@mikro-orm/mongodb`. See the [MikroORM quick start guide](https://mikro-orm.io/docs/quick-start#installation) for the full list.

> info **Hint** Since MikroORM v7, decorators are no longer exported from `@mikro-orm/core`. Nest projects use legacy (experimental) decorators, so import decorators such as `@Entity()` and `@Property()` from `@mikro-orm/decorators/legacy`. Import `EntityManager`, `EntityRepository`, and `MikroORM` from your driver package (e.g., `@mikro-orm/sqlite`), and other types (e.g., the `EntityRepositoryType` symbol) from `@mikro-orm/core`. The snippets in this chapter include the relevant import statements.

Once the installation is complete, import the `MikroOrmModule` into the root `AppModule`:

[[CODE:2]]

The `forRoot()` method accepts the same configuration object as `MikroORM.init()`. See the [MikroORM configuration documentation](https://mikro-orm.io/docs/configuration) for the complete list of options. The `entities` and `entitiesTs` glob patterns tell MikroORM where to find your entity files: it uses `entitiesTs` when it runs from TypeScript sources and `entities` when it runs from compiled JavaScript (see [folder-based discovery](https://mikro-orm.io/docs/folder-based-discovery)).

> info **Hint** Since MikroORM v7, `ReflectMetadataProvider` is no longer the default metadata provider. Set it explicitly, as shown above, to let MikroORM infer property types from the metadata that TypeScript emits for legacy decorators.

In addition, `forRoot()` supports the following Nest-specific options, all described later in this chapter:

<table>
  <tr>
    <td><code>autoLoadEntities</code></td>
    <td>If <code>true</code>, entities registered through <code>forFeature()</code> are added to the configuration automatically (default: <code>false</code>)</td>
  </tr>
  <tr>
    <td><code>registerRequestContext</code></td>
    <td>If <code>true</code>, registers a middleware that creates a request context for every HTTP request (default: <code>true</code>)</td>
  </tr>
  <tr>
    <td><code>forRoutesPath</code></td>
    <td>The route path that the request context middleware applies to (default: all routes)</td>
  </tr>
  <tr>
    <td><code>scope</code></td>
    <td>The <a href="/fundamentals/injection-scopes">injection scope</a> of the <code>EntityManager</code> provider (default: <code>Scope.DEFAULT</code>)</td>
  </tr>
  <tr>
    <td><code>contextName</code></td>
    <td>The name of the connection, required when you connect to <a href="/data/mikroorm#multiple-databases">multiple databases</a></td>
  </tr>
</table>

Alternatively, you can keep your configuration in a separate `mikro-orm.config.ts` file, which the [MikroORM CLI](https://mikro-orm.io/docs/quick-start#setting-up-the-commandline-tool) uses as well. The `defineConfig()` helper exported by your driver package sets the `driver` option for you:

[[CODE:3]]

Then pass the configuration to `forRoot()`. Since MikroORM v7, `forRoot()` no longer accepts an empty argument list, so you must pass the configuration explicitly:

[[CODE:4]]

Afterward, the `MikroORM` and `EntityManager` objects are available for injection across the entire project, without importing any module elsewhere:

[[CODE:5]]

> info **Note** Import `EntityManager` and `MikroORM` from the `@mikro-orm/<driver>` package, where `<driver>` is `sqlite`, `postgresql`, `mysql`, or whichever driver you use, to get the driver-specific API. If you have `@mikro-orm/sql` installed as a dependency, you can also import the `EntityManager` from there. The generic classes exported by `@mikro-orm/core` are registered as injection tokens as well.

#### Repositories

MikroORM supports the repository design pattern, so each entity has its own repository. See the [MikroORM repositories documentation](https://mikro-orm.io/docs/repositories) for details. To continue the example, define a `Photo` entity:

[[CODE:6]]

> info **Hint** Besides decorators, MikroORM can define entities with the `defineEntity()` helper or the `EntitySchema` class. Learn more in the [MikroORM defining entities guide](https://mikro-orm.io/docs/defining-entities).

To define which repositories are registered in the current scope, use the `forFeature()` method:

[[CODE:7]]

> info **Note** Don't register your base entities via `forFeature()`, as there are no repositories for them. Base entities do, however, need to be part of the ORM configuration (e.g., the `entities` option of `forRoot()`).

Then import the `PhotoModule` into the root `AppModule`:

[[CODE:8]]

You can now inject the `Photo` repository into the `PhotoService` using the `@InjectRepository()` decorator:

[[CODE:9]]

Repositories don't have `persist()` or `flush()` methods, so write operations go through the `EntityManager`, which implements the [Unit of Work](https://mikro-orm.io/docs/unit-of-work) pattern. The repository's `create()` method marks the new entity for persistence, and `em.flush()` writes all pending changes to the database in a single transaction.

#### Using custom repositories

To add your own query methods, extend `EntityRepository` and point the entity to your class through the `repository` option:

[[CODE:10]]

[[CODE:11]]

When you pass the `Author` entity to `forFeature()`, the module also registers the custom repository class itself as a provider. You can therefore inject it by its class, without the `@InjectRepository()` decorator:

[[CODE:12]]

#### Load entities automatically

Manually adding entities to the `entities` array of the configuration can be tedious. In addition, referencing entities from the root module breaks application domain boundaries and leaks implementation details to other parts of the application. Glob paths solve this issue, but they don't work when you bundle your application (e.g., in a [monorepo](/cli/monorepo)): MikroORM looks up the matching files at runtime, and a bundle doesn't contain them as separate files.

As an alternative, you can load entities automatically by setting the `autoLoadEntities` property of the configuration object (passed into the `forRoot()` method) to `true`, as shown below:

[[CODE:13]]

With this option enabled, every entity registered through the `forFeature()` method is automatically added to the `entities` array of the configuration object.

> info **Note** Entities that aren't registered through the `forFeature()` method, but are only referenced from an entity (via a relationship), won't be included by the `autoLoadEntities` setting.

> info **Note** `autoLoadEntities` has no effect on the MikroORM CLI, which still needs a CLI config with the full list of entities. You can use globs there, however, as the CLI doesn't run your bundle.

#### Request context

MikroORM keeps loaded entities in an [identity map](https://mikro-orm.io/docs/identity-map), which must not be shared between concurrent requests. Each request needs its own fork of the `EntityManager`, with a clean identity map. The `MikroOrmModule` handles this for you: it registers a middleware for all routes that runs each HTTP request inside a `RequestContext`. Within that context, the global `EntityManager` that you inject (and every repository that depends on it) transparently delegates to the request's fork.

Outside of a request context, MikroORM refuses to use the global `EntityManager` for operations that depend on the identity map, such as `find()` or `flush()`, and throws a `ValidationError`. The [next section](/data/mikroorm#request-scoped-handlers-in-queues) shows how to create a context for code that doesn't run as part of an HTTP request.

To apply the middleware to a subset of routes only, set the `forRoutesPath` option. To disable it, set `registerRequestContext` to `false`. For example, instead of using the middleware, you can let Nest create an `EntityManager` fork for every request by making the `EntityManager` provider [request-scoped](/fundamentals/injection-scopes):

[[CODE:14]]

> warning **Warning** With `scope: Scope.REQUEST`, every provider that depends on the `EntityManager` (including repositories) becomes request-scoped as well. This affects performance, as described in the [injection scopes chapter](/fundamentals/injection-scopes#performance).

#### Request scoped handlers in queues

Middleware only runs for HTTP requests. Code outside of that flow, such as [queue](/application/queues) consumers and [scheduled tasks](/application/task-scheduling), has no request context, so you need to create one yourself.

For these methods, use the `@CreateRequestContext()` decorator. It forks the `EntityManager` and runs the decorated `async` method inside a new context. The decorator looks up the `EntityManager` through the `orm` property (a `MikroORM` instance) or the `em` property (an `EntityManager`) of the class, so inject one of them under that name:

[[CODE:15]]

> warning **Warning** Place `@CreateRequestContext()` directly above the method, below other method decorators such as `@Cron()`. The decorator replaces the method with a wrapper. Decorators listed above it attach their metadata to that wrapper, but decorators listed below it attach their metadata to the original method, which Nest never sees (in this example, the cron job wouldn't be registered).

> info **Note** As the name suggests, this decorator always creates a new context, as opposed to its alternative `@EnsureRequestContext()`, which creates one only if the method isn't already running inside another context. Before MikroORM v6, `@CreateRequestContext()` was called `@UseRequestContext()`, and before v7, it was exported from `@mikro-orm/core`.

#### Transactions

MikroORM queues all write operations until you call `em.flush()`, which then wraps them in a single transaction. To control the transaction boundaries yourself, for example, to flush several times or to combine the changes with other queries, use the `em.transactional()` method:

[[CODE:16]]

The callback receives a forked `EntityManager` that runs inside the transaction. When the callback completes, MikroORM flushes the fork and commits the transaction. If the callback throws, MikroORM rolls the transaction back and rethrows the error.

Alternatively, use the `@Transactional()` decorator, which wraps the decorated `async` method in `em.transactional()`:

[[CODE:17]]

Like `@CreateRequestContext()`, the decorator finds the `EntityManager` through the `em` or `orm` property of the class, and falls back to the current context if the class has neither. When called inside another transaction, `em.transactional()` starts a nested transaction (a savepoint), while `@Transactional()` joins the existing transaction by default. See the [MikroORM transactions documentation](https://mikro-orm.io/docs/transactions) for propagation options, isolation levels, and locking.

#### Serialization

MikroORM entities have a `toJSON()` method that applies MikroORM's [serialization rules](https://mikro-orm.io/docs/serializing): it omits hidden properties, applies custom property serializers, and serializes populated relations as nested objects and unpopulated relations as their primary keys. When a route handler returns an entity, Nest converts it to JSON, so these rules apply automatically.

> warning **Warning** Don't use [Nest's built-in serializer](/application/serialization) (the `ClassSerializerInterceptor`) with MikroORM entities. It relies on `class-transformer`, which doesn't understand the wrappers that MikroORM uses for relations: it serializes the internal structure of a `Reference`, and traversing a `Collection` leads to infinite recursion (a "Maximum call stack size exceeded" error).

Instead, configure serialization on the entity with MikroORM's options:

[[CODE:18]]

> info **Hint** When entities reference each other, wrap the relation's type in `Rel<T>` (or use `Ref<T>`) from `@mikro-orm/core`, and pass the target entity to the relation decorator, as shown above. Otherwise, TypeScript emits decorator metadata that references the related class directly. In ESM projects, the circular imports between entity files then fail at startup with a `ReferenceError` (e.g., "Cannot access 'Author' before initialization").

To control serialization for a single route handler, convert the entity explicitly with the `serialize()` function, which is exported by your driver package and by `@mikro-orm/core`. It accepts options such as `populate`, `exclude`, `fields`, and `groups`:

[[CODE:19]]

To get a plain object with the default rules applied, call `wrap(entity).toObject()`.

#### Multiple databases

To connect to multiple databases, call `MikroOrmModule.forRoot()` once per database, and give each connection a unique `contextName`. In this setup, set `registerRequestContext` to `false` on every connection, because the default middleware only works with a single, unnamed connection. Instead, import `MikroOrmModule.forMiddleware()` once. Its middleware creates a request context that covers all connections:

[[CODE:20]]

> warning **Notice** If you use `MikroOrmModule.forRootAsync()`, set the `contextName` next to `useFactory`, not inside the options object that the factory returns.

With this setup, pass the context name to the `forFeature()` method and the `@InjectRepository()` decorator:

[[CODE:21]]

To inject the `MikroORM` or `EntityManager` of a specific connection, use the `@InjectMikroORM()` and `@InjectEntityManager()` decorators:

[[CODE:22]]

To inject all registered `MikroORM` instances as an array, use the `@InjectMikroORMs()` decorator.

#### Testing

When unit testing an application, you usually want to avoid a database connection, which keeps test suites independent and fast. However, your classes might depend on repositories and the `EntityManager`. To resolve these classes, provide mock implementations using [custom providers](/fundamentals/custom-providers).

The `@mikro-orm/nestjs` package exposes a `getRepositoryToken()` function that returns a prepared injection token based on a given entity (e.g., `'PhotoRepository'` for the `Photo` entity), allowing you to mock the repository. For a custom repository, use its class as the token:

[[CODE:23]]

Now the `mockedRepository` object is injected wherever a class in this module asks for the `Photo` repository using the `@InjectRepository(Photo)` decorator. For [multiple databases](/data/mikroorm#multiple-databases), pass the context name as the second argument, e.g., `getRepositoryToken(Album, 'albums')`.

#### Async configuration

When you need to pass module options asynchronously instead of statically, use the `forRootAsync()` method. As with most dynamic modules, Nest provides several techniques for async configuration.

One technique is to use a factory function. Like other [factory providers](/fundamentals/custom-providers#factory-providers-usefactory), the factory function can be `async` and can inject dependencies through `inject`:

[[CODE:24]]

> warning **Warning** Set the `driver` option next to `useFactory`, as shown above. The module needs to know the driver before it calls the factory, to register the driver-specific `EntityManager` and `MikroORM` classes as injection tokens. Without it, injecting the `EntityManager` from your driver package fails with a dependency resolution error.

Alternatively, you can configure the `MikroOrmModule` using a class instead of a factory, as shown below:

[[CODE:25]]

The construction above instantiates `MikroOrmConfigService` inside `MikroOrmModule`, using it to create the required options object. In this example, the `MikroOrmConfigService` has to implement the `MikroOrmOptionsFactory` interface, as shown below. The `MikroOrmModule` calls the `createMikroOrmOptions()` method on the instantiated object of the supplied class.

[[CODE:26]]

To reuse an existing options provider instead of creating a private copy inside the `MikroOrmModule`, use the `useExisting` syntax. The provider must implement the `MikroOrmOptionsFactory` interface, and a module listed in `imports` must export it:

[[CODE:27]]

#### Application shutdown

The `MikroOrmModule` closes the ORM and its database connection in the `onApplicationShutdown()` lifecycle hook, which Nest calls when you call `app.close()`. By default, however, Nest doesn't listen for process termination signals such as `SIGTERM`, so the connection isn't closed when the process is terminated. To close it in that case too, enable [shutdown hooks](/fundamentals/lifecycle-events#application-shutdown):

[[CODE:28]]

#### Example

For complete applications that use NestJS with MikroORM, see the [nestjs-realworld-example-app](https://github.com/mikro-orm/nestjs-realworld-example-app) and [nestjs-example-app](https://github.com/mikro-orm/nestjs-example-app) repositories.
