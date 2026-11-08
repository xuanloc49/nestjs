### Mongo

Nest supports two methods for integrating with the [MongoDB](https://www.mongodb.com/) database. You can either use the [TypeORM](https://github.com/typeorm/typeorm) module described in the [TypeORM chapter](/data/typeorm), which has a connector for MongoDB, or use [Mongoose](https://mongoosejs.com), the most popular MongoDB object modeling tool. This chapter describes the latter, using the dedicated `@nestjs/mongoose` package.

Start by installing the required dependencies:

[[CODE:1]]

Once the installation process is complete, import the `MongooseModule` into the root `AppModule`:

[[CODE:2]]

The `forRoot()` method accepts the same configuration object as `mongoose.connect()` from the Mongoose package, as described in the [Mongoose connections guide](https://mongoosejs.com/docs/connections.html).

#### Model injection

With Mongoose, everything is derived from a [Schema](https://mongoosejs.com/docs/guide.html). Each schema maps to a MongoDB collection and defines the shape of the documents within that collection. Schemas are used to define [Models](https://mongoosejs.com/docs/models.html). Models are responsible for creating and reading documents from the underlying MongoDB database.

You can create schemas with NestJS decorators, or manually with Mongoose itself. Using decorators to create schemas greatly reduces boilerplate and improves overall code readability.

Let's define the `CatSchema`:

[[CODE:3]]

> info **Hint** You can also generate a raw schema definition using the `DefinitionsFactory` class (from the `@nestjs/mongoose` package). This allows you to manually modify the schema definition generated from the metadata you provided, which is useful for edge cases where it may be hard to represent everything with decorators.

The `@Schema()` decorator marks a class as a schema definition. It maps the `Cat` class to a MongoDB collection of the same name, but with an additional "s" at the end, so the final collection name is `cats`. This decorator accepts a single optional argument, a schema options object. Think of it as the object you would normally pass as the second argument of the `mongoose.Schema` class constructor (e.g., `new mongoose.Schema(_, options)`). To learn more about the available schema options, see the [Mongoose schema options](https://mongoosejs.com/docs/guide.html#options) documentation.

The `@Prop()` decorator defines a property in the document. For example, the schema definition above defines three properties: `name`, `age`, and `breed`. The [schema types](https://mongoosejs.com/docs/schematypes.html) for these properties are automatically inferred thanks to TypeScript metadata (and reflection) capabilities. However, in more complex scenarios in which types cannot be implicitly reflected (for example, arrays or nested object structures), you must indicate the types explicitly, as follows:

[[CODE:4]]

Alternatively, the `@Prop()` decorator accepts an options object argument (read more about the [available schema type options](https://mongoosejs.com/docs/schematypes.html#schematype-options)). With it, you can indicate whether a property is required, specify a default value, or mark it as immutable. For example:

[[CODE:5]]

To specify a relation to another model (for populating later), use the `@Prop()` decorator as well. For example, if `Cat` has an `Owner` that is stored in a different collection called `owners`, the property should have `type` and `ref` options:

[[CODE:6]]

If there are multiple owners, your property configuration should look as follows:

[[CODE:7]]

If you don't intend to always populate a reference to another collection, consider using `mongoose.Types.ObjectId` as the type instead:

[[CODE:8]]

Then, when you need to selectively populate it later, use a repository function that specifies the correct type:

[[CODE:9]]

> info **Hint** If there is no foreign document to populate, the type could be `Owner | null`, depending on your [Mongoose configuration](https://mongoosejs.com/docs/populate.html#doc-not-found). Alternatively, it might throw an error, in which case the type is `Owner`.

Finally, you can also pass a **raw** schema definition to the decorator. This is useful when, for example, a property represents a nested object that is not defined as a class. For this, use the `raw()` function from the `@nestjs/mongoose` package, as follows:

[[CODE:10]]

Alternatively, if you prefer **not using decorators**, you can define a schema manually. For example:

[[CODE:11]]

The `cat.schema` file resides in a `schemas` folder in the `cats` directory, where the `CatsModule` is also defined. While you can store schema files wherever you prefer, we recommend storing them near their related **domain** objects, in the appropriate module directory.

Let's look at the `CatsModule`:

[[CODE:12]]

The `MongooseModule` provides the `forFeature()` method to configure the module, including defining which models should be registered in the current scope. To use the models in another module as well, add `MongooseModule` to the `exports` array of `CatsModule` and import `CatsModule` in the other module.

Once you've registered the schema, you can inject a `Cat` model into the `CatsService` using the `@InjectModel()` decorator:

[[CODE:13]]

#### Connection

At times, you may need to access the native [Mongoose Connection](https://mongoosejs.com/docs/api.html#Connection) object, for example, to make native API calls on it. Inject the Mongoose connection with the `@InjectConnection()` decorator as follows:

[[CODE:14]]

#### Sessions

To start a session with Mongoose, inject the database connection using `@InjectConnection()` rather than calling `mongoose.startSession()` directly. This integrates with the Nest dependency injection system and ensures the session is started on the connection that Nest manages.

Here's an example of how to start a session:

[[CODE:15]]

In this example, `@InjectConnection()` injects the Mongoose connection into the service. You can then call `connection.startSession()` to begin a new session and use it to manage database transactions, ensuring atomic operations across multiple queries. After starting the transaction, remember to commit or abort it based on your logic, and end the session when you're done.

#### Multiple databases

Some projects require multiple database connections, which this module also supports. To work with multiple connections, first create the connections. In this case, naming the connections is **mandatory**.

[[CODE:16]]

> warning **Notice** Don't create multiple connections without a name or with the same name, otherwise they will override each other.

With this setup, you have to tell the `MongooseModule.forFeature()` method which connection to use:

[[CODE:17]]

You can also inject the `Connection` object for a given connection:

[[CODE:18]]

To inject a given `Connection` into a custom provider (for example, a factory provider), use the `getConnectionToken()` function, passing the name of the connection as an argument:

[[CODE:19]]

To inject a model from a named connection, pass the connection name as the second argument to the `@InjectModel()` decorator:

[[CODE:20]]

#### Hooks (middleware)

Middleware (also called pre and post hooks) are functions that are passed control during the execution of asynchronous functions. Middleware is specified at the schema level and is useful for writing plugins (see the [Mongoose middleware documentation](https://mongoosejs.com/docs/middleware.html)). Calling `pre()` or `post()` after compiling a model does not work in Mongoose. To register a hook **before** model registration, use the `forFeatureAsync()` method of the `MongooseModule` along with a factory provider (i.e., `useFactory`). With this technique, you can access a schema object, then use its `pre()` or `post()` method to register a hook on that schema. For example:

[[CODE:21]]

Like other [factory providers](/fundamentals/custom-providers#factory-providers-usefactory), the factory function can be `async` and can inject dependencies through `inject`.

[[CODE:22]]

#### Plugins

To register a [plugin](https://mongoosejs.com/docs/plugins.html) for a given schema, use the `forFeatureAsync()` method:

[[CODE:23]]

To register a plugin for all schemas at once, call the `.plugin()` method of the `Connection` object. You must access the connection before models are created; to do this, use the `connectionFactory` option:

[[CODE:24]]

#### Discriminators

[Discriminators](https://mongoosejs.com/docs/discriminators.html) are a schema inheritance mechanism. They enable you to have multiple models with overlapping schemas on top of the same underlying MongoDB collection.

Suppose you want to track different types of events in a single collection. Every event has a timestamp.

[[CODE:25]]

> info **Hint** Mongoose tells discriminator models apart by the "discriminator key", which is `__t` by default. Mongoose adds a String path called `__t` to your schemas and uses it to track which discriminator a document is an instance of.
> You may also use the `discriminatorKey` option to define the path for discrimination.

`SignUpEvent` and `ClickedLinkEvent` instances will be stored in the same collection as generic events.

Now, let's define the `ClickedLinkEvent` class, as follows:

[[CODE:26]]

And `SignUpEvent` class:

[[CODE:27]]

With this in place, use the `discriminators` option to register discriminators for a given schema. It works with both `MongooseModule.forFeature()` and `MongooseModule.forFeatureAsync()`:

[[CODE:28]]

#### Testing

When unit testing an application, you usually want to avoid any database connection, which keeps test suites simpler to set up and faster to execute. However, your classes might depend on models that are pulled from the connection instance. To resolve these classes, create mock models.

To make this easier, the `@nestjs/mongoose` package exposes a `getModelToken()` function that returns a prepared [injection token](/fundamentals/custom-providers#di-fundamentals) based on a model name. Using this token, you can provide a mock implementation using any of the standard [custom provider](/fundamentals/custom-providers) techniques, including `useClass`, `useValue`, and `useFactory`. For example:

[[CODE:29]]

In this example, a hardcoded `catModel` (object instance) is provided whenever any consumer injects a `Model<Cat>` using the `@InjectModel()` decorator.

<app-banner-courses></app-banner-courses>

#### Async configuration

When you need to pass module options asynchronously instead of statically, use the `forRootAsync()` method. As with most dynamic modules, Nest provides several techniques for async configuration.

One technique is to use a factory function:

[[CODE:30]]

Like other [factory providers](/fundamentals/custom-providers#factory-providers-usefactory), the factory function can be `async` and can inject dependencies through `inject`.

[[CODE:31]]

Alternatively, you can configure the `MongooseModule` using a class instead of a factory, as shown below:

[[CODE:32]]

The construction above instantiates `MongooseConfigService` inside `MongooseModule`, using it to create the required options object. In this example, the `MongooseConfigService` has to implement the `MongooseOptionsFactory` interface, as shown below. The `MongooseModule` calls the `createMongooseOptions()` method on the instantiated object of the supplied class.

[[CODE:33]]

To reuse an existing options provider instead of creating a private copy inside the `MongooseModule`, use the `useExisting` syntax. The provider must implement the `MongooseOptionsFactory` interface:

[[CODE:34]]

#### Connection events

You can listen to Mongoose [connection events](https://mongoosejs.com/docs/connections.html#connection-events) using the `onConnectionCreate` configuration option. Nest calls this function with each connection as soon as the connection is created, before it opens, so you can register listeners for the `connected`, `open`, `disconnected`, `reconnected`, and `disconnecting` events, as demonstrated below:

[[CODE:35]]

This code snippet establishes a connection to a MongoDB database at `mongodb://localhost/test`. The `onConnectionCreate` option sets up event listeners for monitoring the connection's status:

- `connected`: Triggered when the connection is successfully established.
- `open`: Fires when the connection is fully opened and ready for operations.
- `disconnected`: Called when the connection is lost.
- `reconnected`: Invoked when the connection is re-established after being disconnected.
- `disconnecting`: Occurs when the connection is in the process of closing.

You can also use the `onConnectionCreate` property in async configurations created with `MongooseModule.forRootAsync()`:

[[CODE:36]]

#### Subdocuments

To nest subdocuments within a parent document, define your schemas as follows:

[[CODE:37]]

And then reference the subdocument in the parent schema:

[[CODE:38]]

To include multiple subdocuments, use an array of subdocuments. Make sure to override the type of the property accordingly:

[[CODE:39]]

#### Virtuals

In Mongoose, a **virtual** is a property that exists on a document but is not persisted to MongoDB. Instead, it is computed dynamically whenever it's accessed. Virtuals are typically used for derived or computed values, like combining fields (e.g., creating a `fullName` property by concatenating `firstName` and `lastName`), or for creating properties that rely on existing data in the document.

[[CODE:40]]

> info **Hint** The `@Virtual()` decorator is imported from the `@nestjs/mongoose` package.

In this example, the `fullName` virtual is derived from `firstName` and `lastName`. Even though it behaves like a normal property when accessed, it's never saved to the MongoDB document.

#### Example

A working example is available in the [nestjs/nest repository](https://github.com/nestjs/nest/tree/master/sample/06-mongoose).
