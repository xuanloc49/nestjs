### Other features

In the GraphQL world, there is a lot of debate about handling concerns like **authentication** or the **side effects** of operations. Some handle them inside the business logic, some use higher-order functions to enhance queries and mutations with authorization logic, and others use [schema directives](https://www.apollographql.com/docs/apollo-server/schema/directives/). There is no one-size-fits-all answer.

Nest helps address these concerns with its cross-platform features, such as [guards](/guards) and [interceptors](/interceptors). The goal is to reduce redundancy and provide tooling that helps you create well-structured, readable, and consistent applications.

#### Overview

You can use standard [guards](/guards), [interceptors](/interceptors), [filters](/exception-filters), and [pipes](/pipes) with GraphQL the same way as with any RESTful application. You can also create your own decorators with the [custom decorators](/custom-decorators) feature. Consider the following GraphQL query handler:

[[CODE:1]]

GraphQL works with guards and pipes the same way as HTTP REST handlers do. This means you can move your authentication logic to a guard, and even reuse the same guard class across a REST and a GraphQL API. Interceptors work the same way across both types of applications:

[[CODE:2]]

#### Execution context

Since GraphQL receives a different type of data in the incoming request, the [execution context](/fundamentals/execution-context) that guards and interceptors receive differs between GraphQL and REST. GraphQL resolvers have a distinct set of arguments: `root`, `args`, `context`, and `info`. Therefore, guards and interceptors must transform the generic `ExecutionContext` into a `GqlExecutionContext`:

[[CODE:3]]

The object returned by `GqlExecutionContext.create()` exposes a **get** method for each GraphQL resolver argument (e.g., `getArgs()`, `getContext()`, etc.). Once you've transformed the context, you can pick out any GraphQL argument for the current request.

#### Exception filters

Standard Nest [exception filters](/exception-filters) are compatible with GraphQL applications as well. As with `ExecutionContext`, GraphQL apps should transform the `ArgumentsHost` object into a `GqlArgumentsHost` object:

[[CODE:4]]

> info **Hint** Both `GqlExceptionFilter` and `GqlArgumentsHost` are imported from the `@nestjs/graphql` package.

Unlike in the REST case, you don't use the native `response` object to generate a response.

#### Custom decorators

As mentioned, the [custom decorators](/custom-decorators) feature works as expected with GraphQL resolvers:

[[CODE:5]]

Use the `@User()` custom decorator as follows:

[[CODE:6]]

> info **Hint** The example above assumes that the `user` object is assigned to the context of your GraphQL application.

#### Execute enhancers at the field resolver level

In the GraphQL context, Nest doesn't run **enhancers** (the generic name for interceptors, guards, and filters) at the field level by default (see [this GitHub issue](https://github.com/nestjs/graphql/issues/320#issuecomment-511193229)): they only run for the top-level `@Query()`/`@Mutation()` method. To make Nest execute interceptors, guards, or filters for methods annotated with `@ResolveField()`, set the `fieldResolverEnhancers` option in `GqlModuleOptions`. Pass it a list of `'interceptors'`, `'guards'`, and/or `'filters'` as appropriate:

[[CODE:7]]

> warning **Warning** Enabling enhancers for field resolvers can cause performance issues when you return many records and your field resolver runs thousands of times. For this reason, when you enable `fieldResolverEnhancers`, skip the enhancers that aren't strictly necessary for your field resolvers. You can do this with the following helper function:

[[CODE:8]]

#### Creating a custom driver

Nest provides two official drivers out of the box, `@nestjs/apollo` and `@nestjs/mercurius`, as well as an API for building new **custom drivers**. With a custom driver, you can integrate any GraphQL library, or extend an existing integration with extra features.

For example, to integrate the [`graphql-http`](https://github.com/graphql/graphql-http) package, you could create the following driver class. By the time `start()` is called, Nest has already generated the schema and passed it in the `schema` property of the options object:

[[CODE:9]]

And then use it as follows:

[[CODE:10]]
