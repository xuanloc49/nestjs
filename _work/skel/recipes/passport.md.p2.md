#### Enable authentication globally

If most of your endpoints should be protected by default, you can register the authentication guard as a [global guard](/guards#binding-guards). Instead of using the `@UseGuards()` decorator on each controller, you then flag the routes that should be public.

First, register the `JwtAuthGuard` as a global guard using the following construction (in any module):

[[CODE:28]]

With this in place, Nest will automatically bind `JwtAuthGuard` to all endpoints.

Next, provide a mechanism for declaring routes as public. For this, create a custom decorator using the `SetMetadata` decorator factory function.

[[CODE:29]]

The file above exports two constants: our metadata key, named `IS_PUBLIC_KEY`, and the new decorator itself, named `Public` (you can name it `SkipAuth`, `AllowAnon`, or whatever fits your project).

With the custom `@Public()` decorator in place, you can use it to decorate any method, as follows:

[[CODE:30]]

Lastly, the `JwtAuthGuard` needs to return `true` when the `"isPublic"` metadata is found. For this, use the `Reflector` class (see [putting it all together](/guards#putting-it-all-together) in the Guards chapter).

[[CODE:31]]

#### Request-scoped strategies

The Passport API is based on registering strategies with the global instance of the library. Therefore, strategies are not designed to have request-dependent options or to be dynamically instantiated per request (see [injection scopes](/fundamentals/injection-scopes) to learn more about request-scoped providers). If you configure your strategy to be request-scoped, Nest never instantiates it, since it's not tied to any specific route, and there is no way to determine which "request-scoped" strategies should run for a given request.

However, you can dynamically resolve request-scoped providers within the strategy. For this, use the [module reference](/fundamentals/module-ref) feature.

First, open the `local.strategy.ts` file and inject the `ModuleRef` in the usual way:

[[CODE:32]]

> info **Hint** The `ModuleRef` class is imported from the `@nestjs/core` package.

Be sure to set the `passReqToCallback` configuration property to `true`, as shown above.

In the next step, the request instance is used to obtain the current context identifier, instead of generating a new one (see [getting the current sub-tree](/fundamentals/module-ref#getting-current-sub-tree) to learn more about the request context).

Now, inside the `validate()` method of the `LocalStrategy` class, use the `getByRequest()` method of the `ContextIdFactory` class to create a context id based on the request object, and pass this to the `resolve()` call:

[[CODE:33]]

In the example above, the `resolve()` method asynchronously returns the request-scoped instance of the `AuthService` provider (assuming that `AuthService` is marked as a request-scoped provider).

#### Customize Passport

To customize how the guards call Passport, pass options to the `PassportModule.register()` method. Apart from `defaultStrategy` and `property`, which `@nestjs/passport` uses itself, these options are passed to Passport's `authenticate()` call, so the available options depend on the strategy being implemented. For example:

[[CODE:34]]

You can also configure a strategy by passing an options object to `super()` in its constructor. For example, for the local strategy:

[[CODE:35]]

See the official [Passport website](http://www.passportjs.org/docs/oauth/) for the available property names.

#### Named strategies

When implementing a strategy, you can name it by passing a second argument to the `PassportStrategy()` function. Otherwise, each strategy uses its default name (e.g., `'jwt'` for the JWT strategy):

[[CODE:36]]

You then refer to it with a decorator like `@UseGuards(AuthGuard('myjwt'))`.

#### GraphQL

To use an `AuthGuard` with [GraphQL](/graphql/quick-start), extend the built-in `AuthGuard` class and override the `getRequest()` method.

[[CODE:37]]

To get the currently authenticated user in your GraphQL resolver, define a `@CurrentUser()` decorator:

[[CODE:38]]

To use the decorator in your resolver, include it as a parameter of your query or mutation:

[[CODE:39]]

For the passport-local strategy, you also need to add the GraphQL context's arguments to the request body so that Passport can access them for validation. Otherwise, you'll get an `Unauthorized` error.

[[CODE:40]]
