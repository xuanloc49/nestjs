### Complexity

> warning **Warning** This chapter applies only to the code first approach.

Query complexity lets you define how complex certain fields are, and restrict queries with a **maximum complexity**. The idea is to express the complexity of each field as a number. A common default is to give each field a complexity of `1`. You can also customize how the complexity of a GraphQL query is calculated with complexity estimators. A complexity estimator is a function that calculates the complexity of a field. You can add any number of estimators to the rule, and they run one after another. The first estimator that returns a numeric value determines the complexity of that field.

The `@nestjs/graphql` package integrates with tools like [graphql-query-complexity](https://github.com/slicknode/graphql-query-complexity), which provides a solution based on cost analysis. With this library, you can reject queries that are too costly to execute.

#### Installation

To begin, install the required dependency:

[[CODE:1]]

#### Getting started

Once the installation is complete, define the `ComplexityPlugin` class:

[[CODE:2]]

For demonstration purposes, the maximum allowed complexity is set to `20`. The example above uses two estimators, `fieldExtensionsEstimator` and `simpleEstimator`:

- `fieldExtensionsEstimator`: extracts the complexity value defined for each field of your schema (through the field's `extensions`)
- `simpleEstimator`: returns a fixed complexity for each field (used as the fallback for fields without a defined complexity)

> info **Hint** Remember to add this class to the `providers` array of a module.

#### Field-level complexity

With this plugin in place, you can define the complexity of any field by specifying the `complexity` property in the options object passed to the `@Field()` decorator:

[[CODE:3]]

Alternatively, you can define an estimator function:

[[CODE:4]]

#### Query/Mutation-level complexity

The `@Query()` and `@Mutation()` decorators also accept a `complexity` property in their options object:

[[CODE:5]]
