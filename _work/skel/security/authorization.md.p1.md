### Authorization

`@nestjs/authorization` expresses permissions as **policies**: classes whose methods answer "may this user do this?". A policy is an ordinary provider, so it can inject services, and every check is type-checked against the policy method it calls. Policies work on any data shape, including the plain objects that Prisma, Drizzle and Kysely return.

In this tutorial, you'll add permissions to the API of an online store for cat food and supplies:

- Guests and customers browse published products. Staff also see drafts, and only staff edit the catalog.
- Customers see only their own orders. Staff see all of them.
- Only staff refund orders, only paid ones, and only up to a limit that finance sets per person. Nobody refunds an order that has shipped.
- Admins manage the catalog without restrictions.

Along the way, you'll see where each kind of check belongs (on the route or in the service), when a denial is a 401 and when it's a 403, and how to test policies.

#### Prerequisites

This tutorial continues the [Authentication](/security/authentication) tutorial: the store signs its users in with `@nestjs/authentication`, and this page decides what they may do. Install the package:

[[CODE:1]]

If you're starting fresh, the files below are the sign-in code this page relies on: the Authentication tutorial's application once it [issues tokens to the mobile app](/security/authentication#issue-tokens-to-the-mobile-app), reduced to the mobile app's sign-in, a password for a bearer token. The user is the same plain object, as your ORM would return it:

[[CODE:2]]

Four demo accounts stand in for the users table: two customers (Alice and Bob), a staff member (Sam), and Ada, who is staff and an admin. Their ids are fixed, so the demo orders and the tests can refer to them:

[[CODE:3]]

`UsersRepository` is the Authentication tutorial's, with the two methods this page needs. It seeds the demo accounts at startup, and only `User` objects leave it: the password hashes stay inside.

[[CODE:4]]

[[CODE:5]]

The tokens are the ones the Authentication tutorial issues to its mobile app: short-lived JWT access tokens, described once by the `accessToken` options that the root module passes to `AuthenticationModule` below. The signing secret is the `JWT_SECRET` from the Authentication tutorial's `.env` file, at least 32 bytes:

[[CODE:6]]

> info **Hint** The tutorial reads `process.env` directly, to stay short. In an application, load the environment through [`@nestjs/config`](/application/configuration) with a validation schema, so a missing secret stops the application at startup, and read it from `ConfigService`.

`JwtAuth` verifies the bearer token with the `accessToken` options, and loads the token's user. It registers itself with `AuthenticationRegistry` from its constructor, which is how the guard learns about it:

[[CODE:7]]

`CredentialsService` checks a password against the stored hash, with the package's `PasswordHasher`, and answers `null` for an unknown email and a wrong password alike, in the same time:

[[CODE:8]]

`TokensController` exchanges an email and a password for tokens. Its request body is validated with whatever your application already uses. Every DTO on this page comes twice, as a class with decorators and as a Zod schema, so pick the style you have and skip the other listing:

[[CODE:9]]

[[CODE:10]]

`TokenService.issue()` signs an access token with the same `accessToken` options, and returns it with a refresh token:

[[CODE:11]]

With the Zod schema, the body parameter declares its schema instead of a class:

[[CODE:12]]

> info **Hint** The DTOs are enforced only by a validation pipe: bind `ValidationPipe` globally, as an `APP_PIPE` provider of `AppModule` or with `useGlobalPipes()` in `main.ts`. With the Zod schemas, bind `StandardSchemaValidationPipe` the same way instead. An application uses one or the other. The [validation](/application/validation) page has the options of each.

[[CODE:13]]

Authentication puts the signed-in `User` on `request.user`, and `@CurrentUser()` injects it into a handler. That's all authorization needs from it.

#### Register the authorization module

Import `AuthorizationModule` next to `AuthenticationModule` in the root module. `AuthenticationModule` is registered as in the Authentication tutorial, with the `accessToken` options; `JwtAuth` is a provider of `AuthModule`:

[[CODE:14]]

`forRoot()` registers the module globally. It does three things:

- It provides `AuthorizationService`, which you inject wherever code checks a permission.
- It registers `AuthorizationGuard` as a global guard. The guard enforces the `@Can()` decorator you'll add in the next step, and **denies by default**: a handler runs only when it declares a check, with `@Can()`, with `@Can.Anyone()`, or with `@Public()` from `@nestjs/authentication`, which counts as `@Can.Anyone()`. `POST /auth/token` is `@Public()`, so it keeps working.
- It turns a denial that a service reports into a 401 or a 403, as [Tell guests from forbidden users, and expose permissions](/security/authorization#tell-guests-from-forbidden-users-and-expose-permissions) explains.

A route whose `@Can()` was forgotten is therefore closed, not open. At startup, the module logs every handler it will deny this way, so the list is where a migration starts. The [reference](/security/authorization#what-a-route-declares) has the full rules.

Both packages register a global guard, and **the import order matters**. Nest runs global guards in the order it scans modules, so `AuthenticationModule` has to come first. In the reverse order, the authorization guard would run before anything has set `request.user`, so every `@Can()` check would see a guest, and a signed-in staff member would get a 401 on a staff-only route. `AuthorizationModule` checks the order at startup: it recognizes `AuthenticationGuard` by a marker the guard carries, and when that guard comes second, the app refuses to start, with an error that names both guards and the fix.

> warning **Warning** Other authentication guards, such as a subclass of Passport's `AuthGuard()`, carry no such marker, so the check can only go by their class names. In the wrong order, it logs an error, the app starts, and every `@Can()` check treats signed-in users as guests. Register such a guard with `APP_GUARD`, not with `app.useGlobalGuards()`: Nest runs the guards added that way after every `APP_GUARD`, so they always come after the authorization guard, and the check can't see them.

> info **Hint** The guard reads the user from `request.user`, and from the equivalent places for WebSockets, microservices and GraphQL. With `@nestjs/authentication`, on a WebSocket or a `graphql-ws` socket, it's the user of each message or operation, not the socket's, as the [reference](/security/authorization#reference) explains. If your authentication stores the user elsewhere, pass a `getUser` function to `forRoot()`, or return one from a `forRootAsync()` factory when it needs a provider. If you authenticate with `@UseGuards()` rather than a global guard, pass `globalGuard: false` and list `AuthorizationGuard` after your authentication guard.

#### Write a policy for products

Products are plain objects too, identified by a slug and priced in cents, as in the Authentication tutorial:

[[CODE:15]]

A policy is a class decorated with `@Policy()`. Each method whose first parameter is the user and which returns `boolean` or `Promise<boolean>` is an **ability**. Only a literal `true` allows. Any other value denies, even a truthy one.

[[CODE:16]]

The type of the user parameter is a decision. `User | null` means the ability also runs for guests, who arrive as `null`. Guests can browse the catalog, so every ability here accepts `null`, and `view` and `viewDrafts` give guests a real answer.

`ProductsService` uses the policy in two ways. `can()` resolves to `true` or `false`; here it decides whether the listing includes drafts. `authorize()` throws when the ability denies, so `findOne()` never returns a draft to someone who may not see it.

[[CODE:17]]

Creating and updating products doesn't depend on a particular record, so those checks go on the route. The bodies of those routes are DTOs, as classes or as Zod schemas; an update takes any subset of a new product's fields:

[[CODE:18]]

[[CODE:19]]

`@Can(ProductPolicy, 'create')` makes the guard call `create(user)` before the handler runs:

[[CODE:20]]

With the Zod schemas, the body parameters declare their schema instead of a class:

[[CODE:21]]

Whether a route admits guests is authentication's decision, not the policy's. The read routes use `@Authenticate()` with `optional: true`: a request with a valid token gets its user, and a request without one continues with `null`, which is what `@CurrentUser()` then injects. Without the decorator, guests would get a 401 before any policy ran. With `@Public()` instead, authentication would ignore the token entirely, so Sam would browse as a guest and never see drafts.

The read routes check in the service, so they declare `@Can.Anyone()`: anyone authentication lets through may call them, and `ProductsService` decides what each caller sees. Without it, the guard would deny them.

`@Can()` is type-checked. A misspelled ability doesn't compile:

[[CODE:22]]

The error lists the abilities that work on a route: those whose user parameter accepts `null`, since the guard can't know whether a route has a user. `view` is one of them, but `@Can(ProductPolicy, 'view')` still doesn't compile (`Expected 3 arguments, but got 2`): `view` also takes the product, and the guard has none to pass. Checks that need a record belong in the service, as in `findOne()`. A check that needs only an id from the URL can stay on the route, as [Check a route parameter](/security/authorization#check-a-route-parameter) shows.

Finally, register the policy as a provider of its feature module:

[[CODE:23]]

Add `ProductsModule` to the `imports` of `AppModule`. `@Policy()` also makes the class injectable, and the authorization module discovers every policy provider in the app, wherever it's registered. Alternatively, list policies in the `policies` option of `AuthorizationModule.forRoot()`.

> info **Hint** If a `@Can()` points at a policy nobody registered, the app refuses to start, and the error names the handler.

#### Check orders record by record

An order is the Authentication tutorial's: it belongs to a customer, by `userId`, and moves through a few states:

[[CODE:24]]

Whether Alice may view one of Bob's orders depends on that order, so these abilities take the order as a second argument:

[[CODE:25]]

These abilities take `User`, not `User | null`. Every orders route requires a signed-in user, and an ability that only services call may say so. The compiler then makes callers rule out a missing user before they check.

Four demo orders stand in for the orders table, with fixed ids like the demo accounts: Alice has a paid and a shipped order, Bob a paid one of five bags of salmon kibble (124.95, which matters when [a policy injects a service](/security/authorization#inject-a-service-into-a-policy)) and a pending one:

[[CODE:26]]

`OrdersService` loads the order, then authorizes against it:

[[CODE:27]]

Everything after the policy class is typed from the ability's signature: the ability name, the user and the order. A misspelled ability, a missing order, or an object that isn't an `Order` doesn't compile, and neither does a user that might be `null`:

[[CODE:28]]

The listing doesn't check orders one by one. It asks a question the query can use (may this user see every order?) and filters in the database. Checking each row after loading all of them would fetch too much and break pagination.

Checking in the service rather than in the controller means every caller gets the same rules: a controller, a GraphQL resolver, or a queue worker that processes refund requests.

The controller passes the signed-in user along. The Authentication tutorial's `OrdersService` read it from `AuthenticationContext` instead; here it's a parameter, so the service's signature says whose permissions a check is about, and a queue worker can call it for a given user. Every route checks in the service, so each declares `@Can.Anyone()`:

[[CODE:29]]

[[CODE:30]]

Add `OrdersModule` to the `imports` of `AppModule`. Alice now gets her two orders from `GET /orders`, and a 403 from `GET /orders/:id` for one of Bob's.

> info **Hint** A 403 confirms that the order exists. If that matters, for example when ids are sequential and guessable, check with `can()` and throw a `NotFoundException` instead.

#### Check a route parameter

Some checks need an argument but not a record. Staff look up a customer's orders at `GET /customers/:customerId/orders`, and customers may list their own there too. Whether Alice may call it depends on the id in the URL alone, so there's nothing to load before checking. Add an ability for it to `OrderPolicy`:

[[CODE:31]]

Unlike the other abilities of `OrderPolicy`, this one takes `User | null`, because a route ability must accept a guest. The route checks it with `@Can()`, whose third argument reads the arguments after the user from the call:

[[CODE:32]]

`OrdersService` gets a method that filters by customer, without a check of its own, since the route has it:

[[CODE:33]]

Add the controller to the `controllers` of `OrdersModule`. Alice now gets her orders from `GET /customers/<Alice's id>/orders` and a 403 for Bob's, Sam gets either, and a guest gets a 401.

The function is typed by the ability's own parameters. Leaving it out doesn't compile when the ability takes more than the user, and neither does returning the wrong types:

[[CODE:34]]

It runs in the guard, before any pipe, so it gets the values as the transport delivered them: route params are strings, and nothing is validated yet. A `ParseUUIDPipe` on `customerId` runs after the check, and an id the user may not see gets a 403, not a 400. An error the function throws, such as a `BadRequestException` for a missing param, reaches an HTTP client as it is. On WebSockets and microservices, Nest reports an `HttpException` from any guard, this function included, as an internal error, so throw a `WsException` or an `RpcException` there. A denial event carries what the function read in its `args`.

Pass identifiers and scopes, not records. Loading the order in the guard would load it twice, once for the check and once in the handler, and answer 403 before the handler could answer 404. That's why `GET /orders/:id` checks in the service instead.

A function declared on its own returns an array rather than the tuple the ability's parameters describe, so end it with `as const`. That makes a small helper reusable across routes:

[[CODE:35]]

[[CODE:36]]

On the other transports, read the arguments from their own context: `GqlExecutionContext.create(context).getArgs()` for a GraphQL operation's arguments, `context.switchToWs().getData()` for a WebSocket message, and `context.switchToRpc().getData()` for a microservice message.

#### Let admins through with `before()`

Admins may do anything with the catalog, including deleting products, which nobody else may do. Rather than adding an admin check to every ability, give the policy a `before()` hook:

[[CODE:37]]

`before()` runs ahead of every ability of its policy, for route checks and service checks alike. It receives the user, the ability name, and the ability's arguments. Return `true` to allow, `false` to deny, or nothing to let the ability decide. Guests reach `before()` too, so its user parameter must accept `null`. `before(user: User)` doesn't compile, whether or not the class implements `PolicyBefore<User>`.

Add the route that uses the new ability to `ProductsController`, and import `Delete` and `HttpCode` from `@nestjs/common`:

[[CODE:38]]

Sam now gets a 403 from `DELETE /products/clumping-litter-10l`, and Ada gets a 204.

> warning **Warning** `before()` skips every ability of its policy, including rules that should bind everyone. That's why `OrderPolicy` gets no admin bypass: "nobody refunds a shipped order" has to hold for Ada too. If a policy needs both, check the ability name that `before()` receives, and return nothing for the abilities it must not skip. Implement `PolicyBefore<User, Ability<OrderPolicy>>` and type the name as `Ability<OrderPolicy>`, so a misspelled exclusion doesn't compile.

#### Inject a service into a policy

Finance caps how much each staff member may refund on their own: 100.00 by default, more for some people. The limits live outside the policy, in a service that would read a table or a config service:

[[CODE:39]]

Because a policy is a provider, it injects the service through its constructor. The `refund` ability becomes `async`:

[[CODE:40]]

`authorize()`, `can()` and the guard all await async abilities, so `OrdersService` doesn't change. Register the service next to the policy:

[[CODE:41]]

Since `OrderPolicy` is registered in `OrdersModule`, it can inject that module's providers. A policy listed in the `policies` option of `forRoot()` lives in the authorization module instead, and needs the `imports` option to reach its dependencies.

Bob's paid order comes to 124.95. Sam (limit 100.00) now gets a 403 when he tries to refund it, and Ada (limit 1,000.00) succeeds.

> warning **Warning** Policies must be singletons. A request-scoped or transient policy, or one that depends on a request-scoped provider, throws at startup. Keep per-request state out of policies, and pass what an ability needs as arguments.

#### Tell guests from forbidden users, and expose permissions

A denied request gets a 401 or a 403, depending on who is asking and where:

| Caller         | Route                                                                          | Status                                             | Comes from                             |
| -------------- | ------------------------------------------------------------------------------ | -------------------------------------------------- | -------------------------------------- |
| Guest          | Requires sign-in (the default), such as `POST /products` or `GET /orders`      | 401, with `WWW-Authenticate: Bearer realm="store"` | Authentication, before any policy runs |
| Guest          | Optional authentication, and the policy denies `null`, such as a draft product | 401                                                | Authorization                          |
| Signed-in user | The policy denies, such as Alice on `POST /products` or on one of Bob's orders | 403                                                | Authorization                          |

Authorization never decides whether a route needs a user; that's authentication's job. When a policy denies a guest, the package answers 401 ("sign in and try again") rather than 403 ("never"), because signing in might change the answer.

`authorize()` itself throws an `AuthorizationError`, whose `reason` is `unauthenticated` or `forbidden`, and whose `status` is the matching 401 or 403. It isn't an HTTP exception, because the same service also runs in queue workers and WebSocket gateways. When the error leaves a handler, `AuthorizationModule` turns it into the `UnauthorizedException` or `ForbiddenException` that the guard throws, with the same bodies, so exception filters and clients handle both like any other HTTP error. In WebSocket gateways and microservice handlers, it becomes a `WsException` or an `RpcException`. The 403 body doesn't name the ability.

`can()` never throws on a denial. It resolves to `false` for guests and forbidden users alike, which makes it the tool for shaping responses. Give each order a `canRefund` flag, so the frontend shows the refund button without duplicating the rules:

[[CODE:42]]

The flag comes from the same `refund` ability that `POST /orders/:id/refund` enforces, so the button and the endpoint can't disagree. Sam sees `canRefund: true` on Alice's paid order and `false` on Bob's, which is over his limit. Ada sees `true` on both.

#### Try it

Start the application with the `.env` file that holds the signing secret:

[[CODE:43]]

In another terminal, sign in as Alice, Sam and Ada. `--json` (curl 7.82 or later) sends a `POST` with a JSON body, and the `token` helper uses [jq](https://jqlang.org/) to extract the access token:

[[CODE:44]]

Guests see published products. Staff see the draft too:

[[CODE:45]]

The draft itself is a 401 for a guest and a 403 for a customer. Response headers are trimmed here and below:

[[CODE:46]]

Only staff add products. Authentication stops the guest, and `@Can()` stops Alice:

[[CODE:47]]

Alice sees her own orders and can refund neither. Sam sees every order, with his own `canRefund` flags. Bob's paid order is off limits to Alice:

[[CODE:48]]

Sam refunds Alice's paid order, but not her shipped one, and not Bob's, which is over his limit. Ada can't refund the shipped order either, but Bob's is within her limit:

[[CODE:49]]

Only an admin deletes a product:

[[CODE:50]]
