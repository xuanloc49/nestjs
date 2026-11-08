### Federation

Federation lets you split a monolithic GraphQL server into independent microservices. It consists of two components: a gateway and one or more federated microservices. Each microservice holds part of the schema, and the gateway merges the schemas into a single schema that clients consume.

As described in [Apollo's introduction to federation](https://blog.apollographql.com/apollo-federation-f260cf525d21), federation is designed around these core principles:

- Building a graph should be **declarative.** With federation, you compose a graph declaratively from within your schema instead of writing imperative schema stitching code.
- Code should be separated by **concern**, not by types. Often no single team controls every aspect of an important type like a User or Product, so the definition of these types should be distributed across teams and codebases, rather than centralized.
- The graph should be simple for clients to consume. Together, federated services can form a complete, product-focused graph that accurately reflects how it's being consumed on the client.
- It's just **GraphQL**, using only spec-compliant features of the language. Any language, not just JavaScript, can implement federation.

> info **Hint** Subgraphs built with `ApolloFederationDriver` or `MercuriusFederationDriver` support subscriptions (with the `subscriptions` option for Apollo, or `subscription: true` for Mercurius). The Apollo Gateway (`ApolloGatewayDriver`) does not forward subscriptions to subgraphs, so to expose them through a single federated endpoint, use a router that supports federated subscriptions, such as Apollo Router, or the Mercurius gateway (set `subscription: true` on the gateway and `wsUrl` for each service).

In the following sections, we'll set up a demo application that consists of a gateway and two federated endpoints: a Users service and a Posts service.

#### Federation with Apollo

Start by installing the required dependencies:

[[CODE:1]]

#### Schema first

The Users service provides a simple schema. The `@key` directive tells the Apollo query planner that a particular instance of `User` can be fetched by its `id`. Also note that the schema extends the `Query` type.

[[CODE:2]]

The resolver provides one additional method named `resolveReference()`. The Apollo gateway calls this method whenever a related resource requires a `User` instance. You'll see an example of this in the Posts service later. The method must be annotated with the `@ResolveReference()` decorator.

[[CODE:3]]

Finally, wire everything up by registering the `GraphQLModule` with the `ApolloFederationDriver` driver in the configuration object:

[[CODE:4]]

#### Code first

Start by adding some extra decorators to the `User` entity:

[[CODE:5]]

The resolver provides one additional method named `resolveReference()`. The Apollo gateway calls this method whenever a related resource requires a `User` instance. You'll see an example of this in the Posts service later. The method must be annotated with the `@ResolveReference()` decorator.

[[CODE:6]]

Finally, wire everything up by registering the `GraphQLModule` with the `ApolloFederationDriver` driver in the configuration object:

[[CODE:7]]

Working examples are available for the [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/users-application) and [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/users-application) approaches.

#### Federated example: Posts

The Posts service serves aggregated posts through the `getPosts` query, and also extends the `User` type with a `user.posts` field.

#### Schema first

The Posts service references the `User` type in its schema by marking it with the `extend` keyword. It also declares one additional field on the `User` type (`posts`). Note the `@key` directive, used to match `User` instances, and the `@external` directive, which indicates that the `id` field is managed elsewhere.

[[CODE:8]]

In the following example, the `PostsResolver` provides a `getUser()` method that returns a reference containing `__typename` plus any additional properties your application needs to resolve the reference, in this case `id`. The gateway uses `__typename` to pinpoint the microservice responsible for the `User` type and retrieve the corresponding instance. To resolve the reference, the gateway sends a request to the Users service described above, which executes its `resolveReference()` method.

[[CODE:9]]

Lastly, register the `GraphQLModule`, as in the Users service.

[[CODE:10]]

#### Code first

First, declare a class representing the `User` entity. Although the entity itself lives in another service, this service uses it (and extends its definition). Note the `@extends` and `@external` directives.

[[CODE:11]]

Next, create the resolver for the extension of the `User` entity:

[[CODE:12]]

Then define the `Post` entity class:

[[CODE:13]]

And its resolver:

[[CODE:14]]

Finally, tie everything together in a module. Note the schema build options, which specify that `User` is an orphaned (external) type.

[[CODE:15]]

Working examples are available for the [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/posts-application) and [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/posts-application) approaches.

#### Federated example: Gateway

Start by installing the required dependency:

[[CODE:16]]

The gateway requires a list of endpoints, and it discovers the corresponding schemas automatically. Therefore, the gateway implementation is the same for both the code first and schema first approaches.

[[CODE:17]]

Working examples are available for the [code first](https://github.com/nestjs/nest/tree/master/sample/31-graphql-federation-code-first/gateway) and [schema first](https://github.com/nestjs/nest/tree/master/sample/32-graphql-federation-schema-first/gateway) approaches.

#### Federation with Mercurius

Start by installing the required dependencies:

[[CODE:18]]

> info **Note** The `@apollo/subgraph` package is required to build a subgraph schema (the `buildSubgraphSchema` and `printSubgraphSchema` functions).

#### Schema first

The Users service provides a simple schema. The `@key` directive tells the Mercurius query planner that a particular instance of `User` can be fetched by its `id`. Also note that the schema extends the `Query` type.

[[CODE:19]]

The resolver provides one additional method named `resolveReference()`. The Mercurius gateway calls this method whenever a related resource requires a `User` instance. You'll see an example of this in the Posts service later. The method must be annotated with the `@ResolveReference()` decorator.

[[CODE:20]]

Finally, wire everything up by registering the `GraphQLModule` with the `MercuriusFederationDriver` driver in the configuration object:

[[CODE:21]]

#### Code first

Start by adding some extra decorators to the `User` entity:

[[CODE:22]]

The resolver provides one additional method named `resolveReference()`. The Mercurius gateway calls this method whenever a related resource requires a `User` instance. You'll see an example of this in the Posts service later. The method must be annotated with the `@ResolveReference()` decorator.

[[CODE:23]]

Finally, wire everything up by registering the `GraphQLModule` with the `MercuriusFederationDriver` driver in the configuration object:

[[CODE:24]]

#### Federated example: Posts

The Posts service serves aggregated posts through the `getPosts` query, and also extends the `User` type with a `user.posts` field.

#### Schema first

The Posts service references the `User` type in its schema by marking it with the `extend` keyword. It also declares one additional field on the `User` type (`posts`). Note the `@key` directive, used to match `User` instances, and the `@external` directive, which indicates that the `id` field is managed elsewhere.

[[CODE:25]]

In the following example, the `PostsResolver` provides a `getUser()` method that returns a reference containing `__typename` plus any additional properties your application needs to resolve the reference, in this case `id`. The gateway uses `__typename` to pinpoint the microservice responsible for the `User` type and retrieve the corresponding instance. To resolve the reference, the gateway sends a request to the Users service described above, which executes its `resolveReference()` method.

[[CODE:26]]

Lastly, register the `GraphQLModule`, as in the Users service.

[[CODE:27]]

#### Code first

First, declare a class representing the `User` entity. Although the entity itself lives in another service, this service uses it (and extends its definition). Note the `@extends` and `@external` directives.

[[CODE:28]]

Next, create the resolver for the extension of the `User` entity:

[[CODE:29]]

Then define the `Post` entity class:

[[CODE:30]]

And its resolver:

[[CODE:31]]

Finally, tie everything together in a module. Note the schema build options, which specify that `User` is an orphaned (external) type.

[[CODE:32]]

#### Federated example: Gateway

Start by installing the required dependency:

[[CODE:33]]

The gateway requires a list of endpoints, and it discovers the corresponding schemas automatically. Therefore, the gateway implementation is the same for both the code first and schema first approaches.

[[CODE:34]]

### Federation 2

According to the [Apollo docs](https://www.apollographql.com/docs/federation/federation-2/new-in-federation-2), Federation 2 improves the developer experience of the original Apollo Federation (called Federation 1 in this section) and is backward compatible with most original supergraphs.

> warning **Warning** Mercurius doesn't fully support Federation 2. See Apollo's list of [subgraph libraries that support Federation 2](https://www.apollographql.com/docs/federation/supported-subgraphs#javascript--typescript).

In the following sections, we'll upgrade the previous example to Federation 2.

#### Federated example: Users

In Federation 2, entities have no originating subgraph, so you no longer need to extend `Query`. For more details, see the [entities topic](https://www.apollographql.com/docs/federation/federation-2/new-in-federation-2#entities) in the Apollo Federation 2 docs.

#### Schema first

Remove the `extend` keyword from the schema. To opt in to Federation 2, the schema must also import the federation directives it uses with the `@link` directive:

[[CODE:35]]

#### Code first

To use Federation 2, specify the federation version in the `autoSchemaFile` option. Nest then adds the `@link` directive to the generated schema for you.

[[CODE:36]]

#### Federated example: Posts

For the same reason, you no longer need to extend `User` and `Query`.

#### Schema first

Remove the `extend` keyword and the `@external` directive from the schema, and add the `@link` directive:

[[CODE:37]]

#### Code first

Because the `User` entity is no longer extended, remove the `@extends` and `@external` directives from `User`:

[[CODE:38]]

As in the Users service, configure the `GraphQLModule` to use Federation 2:

[[CODE:39]]

#### Hiding operations from the supergraph

To keep a query, mutation or field out of the public supergraph API while the subgraph still serves it, mark it with Federation 2's `@inaccessible` directive. With the code first approach, use the `@Directive()` decorator:

[[CODE:40]]

The operation stays executable on the subgraph and is listed in its `_service {{ '{' }} sdl {{ '}' }}`, but composition leaves it out of the supergraph schema that clients see.
