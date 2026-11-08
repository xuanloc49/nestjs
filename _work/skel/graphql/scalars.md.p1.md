### Scalars

A GraphQL object type has a name and fields, but at some point those fields have to resolve to some concrete data. Scalar types provide that data: they represent the leaves of the query (see [scalar types](https://graphql.org/learn/schema/#scalar-types) in the GraphQL documentation). GraphQL includes the following built-in scalar types: `Int`, `Float`, `String`, `Boolean`, and `ID`. In addition to these, you may need to support custom atomic data types (e.g., `Date`).

#### Code first

The code first approach ships with five scalars, three of which are aliases for the existing GraphQL types:

- `ID` (alias for `GraphQLID`): a unique identifier, often used to refetch an object or as the key for a cache
- `Int` (alias for `GraphQLInt`): a signed 32-bit integer
- `Float` (alias for `GraphQLFloat`): a signed double-precision floating-point value
- `GraphQLISODateTime`: a date-time string in UTC (used by default to represent the `Date` type)
- `GraphQLTimestamp`: a signed integer that represents a date and time as the number of milliseconds since the start of the Unix epoch

By default, `GraphQLISODateTime` (e.g., `2019-12-03T09:54:33Z`) represents the `Date` type. To use `GraphQLTimestamp` instead, set the `dateScalarMode` property of the `buildSchemaOptions` object to `'timestamp'`:

[[CODE:1]]

Likewise, `GraphQLFloat` represents the `number` type by default. To use `GraphQLInt` instead, set the `numberScalarMode` property of the `buildSchemaOptions` object to `'integer'`:

[[CODE:2]]

You can also create custom scalars.

#### Override a default scalar

To create a custom implementation of the `Date` scalar, create a new class:

[[CODE:3]]

With this in place, register `DateScalar` as a provider:

[[CODE:4]]

Now you can use the `Date` type in your classes:

[[CODE:5]]

#### Import a custom scalar

To use a custom scalar, import it and register it as a resolver. For demonstration purposes, we'll use the `graphql-type-json` package, which defines a `JSON` GraphQL scalar type.

Start by installing the package:

[[CODE:6]]

Once the package is installed, pass a custom resolver to the `forRoot()` method:

[[CODE:7]]

Now you can use the `JSON` type in your classes:

[[CODE:8]]

For a suite of ready-made scalars, see the [graphql-scalars](https://www.npmjs.com/package/graphql-scalars) package.

#### Create a custom scalar

To define a custom scalar, create a new `GraphQLScalarType` instance. The following example creates a custom `UUID` scalar:

[[CODE:9]]

Then pass a custom resolver to the `forRoot()` method:

[[CODE:10]]

Now you can use the `UUID` type in your classes:

[[CODE:11]]

#### Schema first

To define a custom scalar (see [custom scalars](https://www.apollographql.com/docs/graphql-tools/scalars.html) in the GraphQL Tools documentation), create a type definition and a dedicated resolver. As in the official documentation, we'll use the `graphql-type-json` package, which defines a `JSON` GraphQL scalar type.

Start by installing the package:

[[CODE:12]]

Once the package is installed, pass a custom resolver to the `forRoot()` method:

[[CODE:13]]

Now we can use the `JSON` scalar in our type definitions:

[[CODE:14]]

Another way to define a scalar type is to create a class. Suppose you want to add a `Date` type to your schema:

[[CODE:15]]

With this in place, register `DateScalar` as a provider:

[[CODE:16]]

Now you can use the `Date` scalar in your type definitions:

[[CODE:17]]

By default, the generated TypeScript definition for every custom scalar is `any`, which isn't type-safe. You can configure how Nest generates typings for your custom scalars when you specify how to generate types:

[[CODE:18]]

> info **Hint** Alternatively, you can use a type reference, for example, `DateTime: Date`. In this case, `GraphQLDefinitionsFactory` uses the `name` property of the specified type (`Date.name`) to generate the TypeScript definitions. For custom (non-built-in) types, you must also add an import statement.

Now, given the following GraphQL custom scalar types:

[[CODE:19]]

Nest generates the following TypeScript definitions in `src/graphql.ts`:

[[CODE:20]]

Here, the `customScalarTypeMapping` property maps each custom scalar to the TypeScript type to declare for it. The `additionalHeader` property adds any imports these type definitions require. Lastly, setting `defaultScalarType` to `'unknown'` aliases any custom scalar not listed in `customScalarTypeMapping` to `unknown` instead of `any`, which [TypeScript recommends](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-0.html#new-unknown-top-type) since version 3.0 for added type safety.

> info **Hint** The example imports `_BigNumber` from `bignumber.js` under an alias to avoid [circular type references](https://github.com/Microsoft/TypeScript/issues/12525#issuecomment-263166239).
