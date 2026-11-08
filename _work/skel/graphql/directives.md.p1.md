### Directives

A directive can be attached to a field or fragment inclusion, and can affect execution of the query in any way the server desires (see [directives](https://graphql.org/learn/queries/#directives) in the GraphQL documentation). The GraphQL specification provides several default directives:

- `@include(if: Boolean)`: include this field in the result only if the argument is `true`
- `@skip(if: Boolean)`: skip this field if the argument is `true`
- `@deprecated(reason: String)`: mark the field as deprecated, with a message

A directive is an identifier preceded by an `@` character, optionally followed by a list of named arguments. Directives can appear after almost any element in the GraphQL query and schema languages.

#### Custom directives

To define what happens when Apollo or Mercurius encounters your directive, create a transformer function. This function uses the `mapSchema` function to iterate through locations in your schema (field definitions, type definitions, etc.) and apply the corresponding transformations.

[[CODE:1]]

Next, apply the `upperDirectiveTransformer` function in the `GraphQLModule#forRoot()` method using the `transformSchema` option:

[[CODE:2]]

Once registered, the `@upper` directive can be used in your schema. How you apply the directive depends on the approach you use (code first or schema first).

#### Code first

In the code first approach, use the `@Directive()` decorator to apply the directive:

[[CODE:3]]

> info **Hint** The `@Directive()` decorator is exported from the `@nestjs/graphql` package.

Directives can be applied to fields, field resolvers, input and object types, as well as queries, mutations, and subscriptions. The following example applies a directive at the query handler level:

[[CODE:4]]

> warning **Warning** Directives applied through the `@Directive()` decorator are not reflected in the generated schema definition file.

Lastly, declare the directives in the `GraphQLModule` configuration:

[[CODE:5]]

> info **Hint** Both `GraphQLDirective` and `DirectiveLocation` are exported from the `graphql` package.

#### Schema first

In the schema first approach, apply directives directly in SDL:

[[CODE:6]]
