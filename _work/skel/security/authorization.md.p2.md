#### Testing

An end-to-end test boots the whole app, signs in through the real endpoint, and checks the rules over HTTP. As in the Authentication tutorial, scrypt is slow on purpose, so the test overrides `PasswordHasher` with a cheaper one, and the application reads `JWT_SECRET` at bootstrap, so the test configuration provides one:

[[CODE:51]]

[[CODE:52]]

A policy is a plain class, so its rules are easy to unit-test without Nest. Construct the policy yourself and control its dependencies; the demo accounts and orders double as fixtures:

[[CODE:53]]

Calling an ability directly skips `before()`. The hook is just another method, so test it the same way, for example `expect(new ProductPolicy().before(ada)).toBe(true)`. To test the hook and the ability together, go through `AuthorizationService`, and to test the 401/403 mapping too, go through HTTP, as the end-to-end test does.

A service test sits in between: the real policy and `AuthorizationModule`, without HTTP or signing in. Outside a handler, a denial stays an `AuthorizationError`:

[[CODE:54]]

To replace a policy in a bigger test, override it like any provider, for example `.overrideProvider(OrderPolicy).useValue(...)`: every check, on routes and in services, runs against the override.

#### Production checklist

- **Keep authentication ahead of authorization.** With `AuthenticationModule`, the wrong import order stops the app at startup. With another authentication guard, it only logs an error, so have an end-to-end test sign in and call a `@Can()` route. Two registrations always run after the authorization guard, whatever the import order: a request-scoped `APP_GUARD` (the startup check says so) and `app.useGlobalGuards()` (it can't). Register authentication as a singleton `APP_GUARD`.
- **Review every `@Can.Anyone()`.** The guard denies a handler that declares no check, and logs each one at startup, so a forgotten `@Can()` closes a route. `@Can.Anyone()` opens it to everyone authentication lets through: check that its service authorizes, or that the route needs no permission. A check on an id in the URL can go on the route, with `@Can()`'s third argument, where a later edit to the handler can't drop it.
- **Connect microservices with `inheritAppConfig: true`.** In a hybrid app, Nest runs the app's global guards and interceptors on message handlers only when `connectMicroservice()` gets that option. Without it, `@Can()` on a message handler isn't enforced, and a denial from `authorize()` reaches the client as an internal error instead of a 401 or 403.
- **Put record checks in services**, after loading the record, so that controllers, resolvers and queue workers share them.
- **Don't cache responses by URL on routes that check records.** A cache such as Nest's `CacheInterceptor` answers before the handler runs, so it would serve Bob's order to Alice without asking `OrderPolicy`. Cache below the check, or per user.
- **Filter lists in the query** with a question the query can use, like `viewAll`, rather than loading every row and checking each one.
- **Re-check state when you write.** Authorization reads the order before the refund, and two concurrent requests can both see `paid`. Make the write conditional (update the status only where it's still `paid`), and send the payment provider an idempotency key, so a retry never refunds twice.
- **Choose between 403 and 404** for records whose existence is sensitive, such as other customers' orders when IDs are sequential.
- **Keep policies stateless.** They're singletons shared by all requests.
- **Watch the cost of `can()` flags.** Each flag runs the ability once per row, including any async work. Cache slow lookups like refund limits, or load them once per request.
- **Load secrets from configuration.** Read the JWT secret (at least 32 bytes) from a secret manager or `ConfigService`, not from code.
- **Check with `can()` in your own guards and middleware.** They run before any handler, so an `AuthorizationError` thrown there isn't turned into a 401 or a 403. It becomes a 500.
- **Audit denials.** Responses don't say which check refused a caller. Subscribe to `AuthorizationEvents` to log the policy, the ability and the user's ID for every denial. Each event carries the user and the record as the policy saw them, so log the fields you need rather than the whole event.

#### Reference

##### Module options

`AuthorizationModule.forRoot()` takes these options. `forRootAsync()` takes `policies`, `imports`, `globalGuard` and `isGlobal` at the top level, next to `useFactory`, and its factory returns `getUser`.

| Option | Default | Description |
| --- | --- | --- |
| `getUser` | `defaultGetUser` | A function that receives the `ExecutionContext` and returns the current user, or a promise of it. See [Register the authorization module](/security/authorization#register-the-authorization-module). |
| `policies` | none | Policies to register in the authorization module itself. A `@Policy()` provider of any module is found without being listed. |
| `imports` | none | Modules whose exported providers the `policies` inject. |
| `globalGuard` | `true` | Register `AuthorizationGuard` as a global guard. With `false`, apply it with `@UseGuards()` after your authentication guard. |
| `isGlobal` | `true` | Register the module globally. |

`defaultGetUser` reads the user from these places. `null`, `undefined` and `false` all mean a guest.

| Context | Source |
| --- | --- |
| HTTP | `request.user` |
| GraphQL | the user authentication recorded for this operation, else `req.user` on the GraphQL context |
| WebSockets | the user authentication recorded for this message, else `client.user`, then `client.data.user` |
| Microservices | `user` on the transport context, never the message payload |

A WebSocket client is the connection, not the message, and over `graphql-ws` the `req` on the GraphQL context is the socket's upgrade request, which every operation on the socket shares. So `client.user` and `req.user` hold whichever message or operation authenticated last. `@nestjs/authentication` also leaves a function on the client and on `req`, under `Symbol.for('nestjs.authentication.userOf')`, which takes the `ExecutionContext` and answers with the user of that message or operation: `null` for an anonymous one, as every `@Public()` one is, or `undefined` when it has no answer. `defaultGetUser` asks it first. A `@Public()` message or operation is therefore a guest for `@Can()`, even on a socket whose handshake signed in, and a session that a sign-out everywhere revoked no longer counts. A `getUser` of your own that reads `client.user` or `req.user` on these transports sees the socket's last user instead; other authentication packages can leave the same function to be asked.

##### What a route declares

The guard decides by what the handler and its class declare:

| Declaration | The guard |
| --- | --- |
| `@Can()` | Runs every requirement of the class, then of the method. All must pass. |
| `@Can.Anyone()` | Lets through anyone authentication lets through. |
| `@Public()` from `@nestjs/authentication` (0.1.0 or later) | The same as `@Can.Anyone()`. |
| Nothing | Denies: 403 for a user, 401 for a guest. The startup log names the handler. |

On a method, `@Can.Anyone()` or `@Public()` lifts the class's `@Can()`, as `@Public()` lifts the class's authentication. A `@Can()` on the method itself still applies, so a `@Public()` method with a `@Can()` runs the check for a guest. On a class, neither lifts a method's `@Can()`. A method that `@Authenticate()` puts back under authentication inside a `@Public()` class isn't public, and needs a declaration of its own.

Where Nest runs no global guard, nothing is denied: on GraphQL field resolvers unless `fieldResolverEnhancers` includes `'guards'`, and on the message handlers of a hybrid app connected without `inheritAppConfig: true`. With the enhancer, every `@ResolveField()` needs a declaration too. A class-level one covers them.

##### Events

`AuthorizationEvents` exposes every denial on its `events$` observable, and publishes it on a diagnostics channel. `can()` resolving to `false` isn't a denial and emits nothing.

| Event type | Channel | When |
| --- | --- | --- |
| `denied` | `nestjs:authorization:denied` | `@Can()` or `authorize()` refused a caller |

The `AuthorizationDeniedEvent` payload has these fields:

- `type`: `'denied'`.
- `policy` and `ability`: the policy class name and the ability that denied, such as `OrderPolicy` and `refund`. Both are `null` when the guard denied a handler that declares no check.
- `reason`: `'unauthenticated'` for a guest, `'forbidden'` for a signed-in user.
- `user`: the user the policy saw, `null` for a guest.
- `args`: the ability's arguments after the user, such as the record. For `@Can()`, what its third argument read, or empty without one.
- `handler`: the handler `@Can()` guarded, such as `ProductsController.create`. Absent for `authorize()`.

##### Errors

`authorize()` throws an `AuthorizationError` with `reason`, `status`, `policy` and `ability`. The guard's denial of a handler that declares no check carries the same error, with `policy` and `ability` set to `null`. When it leaves a handler, or when `@Can()` denies, the caller gets the transport's own error, whose body never names the policy or the ability. See [Tell guests from forbidden users, and expose permissions](/security/authorization#tell-guests-from-forbidden-users-and-expose-permissions).

| `reason` | `status` | HTTP | GraphQL `extensions.code` | WebSockets and microservices |
| --- | --- | --- | --- | --- |
| `unauthenticated` | 401 | `UnauthorizedException` | `UNAUTHENTICATED` | `WsException` or `RpcException` with `statusCode: 401` |
| `forbidden` | 403 | `ForbiddenException` | `FORBIDDEN` | `WsException` or `RpcException` with `statusCode: 403` |

Over `graphql-ws`, the client gets the error's message, `Unauthorized` or `Forbidden`, without `extensions.code`: the Apollo driver adds the codes in its error formatting, which doesn't run on that transport.

An `AuthorizationError` thrown outside a handler, such as in your own guard or middleware, isn't mapped and becomes a 500.
