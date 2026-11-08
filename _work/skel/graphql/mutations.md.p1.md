### Mutations

Most discussions of GraphQL focus on data fetching, but any complete data platform needs a way to modify server-side data as well. In REST, any request could cause side effects on the server, but best practice is not to modify data in `GET` requests. GraphQL is similar: technically, any query could be implemented to write data. However, as with REST, the convention is to send any operation that causes writes explicitly as a mutation (see [Mutations](https://graphql.org/learn/queries/#mutations) in the GraphQL documentation).

The official [Apollo documentation](https://www.apollographql.com/docs/graphql-tools/generate-schema.html) uses an `upvotePost()` mutation example, which increments a post's `votes` property. To create an equivalent mutation in Nest, use the `@Mutation()` decorator.

#### Code first

Add another method to the `AuthorsResolver` from the [Resolvers](/graphql/resolvers) chapter.

[[CODE:1]]

> info **Hint** All decorators (e.g., `@Resolver`, `@ResolveField`, `@Args`, etc.) are exported from the `@nestjs/graphql` package.

This generates the following part of the GraphQL schema in SDL:

[[CODE:2]]

The `upvotePost()` method takes `postId` (`Int`) as an argument and returns the updated `Post` entity. For the reasons explained in the [Resolvers](/graphql/resolvers) chapter, you have to set the expected type explicitly.

If the mutation needs to take an object as an argument, create an **input type**. An input type is a special kind of object type that can be passed in as an argument (see [Input types](https://graphql.org/learn/schema/#input-types) in the GraphQL documentation). To declare an input type, use the `@InputType()` decorator.

[[CODE:3]]

> info **Hint** The `@InputType()` decorator takes an options object as an argument, so you can, for example, specify the input type's description. Due to the limitations of TypeScript's metadata reflection system, you must either use the `@Field()` decorator to indicate a type, or use the [CLI plugin](/graphql/cli-plugin).

You can then use this type in the resolver class:

[[CODE:4]]

#### Mutation payload query

A mutation payload can expose the root `Query` type, so clients can refetch any data after a mutation in a single round trip. In the code first approach, reference the generated root type by its name:

[[CODE:5]]

Any value works as the `query` value (an empty object is enough), because the root query resolvers don't depend on their parent. In the schema first approach, declare `query: Query!` on the payload type in your SDL.

#### Schema first

Extend the `AuthorsResolver` from the [Resolvers](/graphql/resolvers) chapter.

[[CODE:6]]

This example assumes that the business logic (querying the post and incrementing its `votes` property) lives in the `PostsService`. That logic can be as simple or sophisticated as needed. The point of this example is to show how resolvers interact with other providers.

The last step is to add the mutation to the existing type definitions.

[[CODE:7]]

The `upvotePost(postId: Int!): Post` mutation is now part of the application's GraphQL API.
