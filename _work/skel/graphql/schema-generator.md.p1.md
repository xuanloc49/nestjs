### Generating SDL

> warning **Warning** This chapter applies only to the code first approach.

To generate a GraphQL SDL schema manually (i.e., without running an application, connecting to the database, hooking up resolvers, etc.), use the `GraphQLSchemaBuilderModule`:

[[CODE:1]]

> info **Hint** The `GraphQLSchemaBuilderModule` and `GraphQLSchemaFactory` are imported from the `@nestjs/graphql` package. The `printSchema` function is imported from the `graphql` package.

#### Usage

The `gqlSchemaFactory.create()` method takes an array of resolver class references. For example:

[[CODE:2]]

It also takes an optional second argument with an array of scalar classes:

[[CODE:3]]

Lastly, you can pass an options object (the same `BuildSchemaOptions` accepted by the `buildSchemaOptions` property of the `GraphQLModule` configuration):

[[CODE:4]]

- `skipCheck`: skip schema validation; boolean, defaults to `false`
- `orphanedTypes`: an array of classes to generate even though they aren't explicitly referenced (i.e., aren't part of the object graph). Normally, a class that is declared but not referenced anywhere in the graph is omitted.

#### Federation

`GraphQLSchemaFactory` builds a plain GraphQL schema: it knows nothing about Apollo Federation. To get the SDL of a code first [federated](/graphql/federation) subgraph (for example, to pass it to `rover subgraph check` or `rover supergraph compose`), print it with `printSubgraphSchema` from `@apollo/subgraph` instead of `printSchema`, so that directives such as `@key`, `@shareable` or `@external` are kept:

[[CODE:5]]

For Federation 2, the printed SDL must also link the federation specification, or it is treated as a Federation 1 subgraph. Prepend the `@link` yourself, importing every federation directive your types use:

[[CODE:6]]

> info **Hint** Entity types that are only referenced through `_entities` (for example, `@extends` stubs resolved with `@ResolveReference()`) aren't reachable from the root types, so pass them in `orphanedTypes`. Otherwise, the schema is generated without them.
