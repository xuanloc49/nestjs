### Migrating from Fastify

A Fastify application can move to Nest and stay on Fastify: your plugins keep working, and routes move one at a time or all at once.

Nest runs on Fastify through the `FastifyAdapter`, so this isn't a change of server. The router, the plugins, the JSON schemas and the serialization stay the same, including how paths match, how query strings parse and how large a body may be. What you add is the structure around them: modules, dependency injection, and guards and pipes in place of hooks registered route by route.

#### Choose an approach

| Question | One route at a time | All at once |
| --- | --- | --- |
| How does it work? | Nest runs on your Fastify instance, and routes move to it one by one | A new Nest application replaces the Fastify app in one release |
| What gets deployed? | Each moved route, on its own | Everything, once |
| What happens to feature work? | It continues, and new endpoints go into Nest | It waits, or gets written twice, until the switch |
| How do you go back? | Restore one route | Deploy the last Fastify release |
| Which Fastify version? | Fastify 5, so upgrade first | Any, since the Fastify app isn't touched |
| What about existing plugins? | They keep running, for Nest's routes too | You register them again on the Nest application |
| How long are there two styles in the code? | Until the last route moves | Never |

Move one route at a time when the application is large, when several people work on it, or when it can't wait. Move it all at once when it's small enough to review as one change and you can pin what it does with tests. That also suits a [coding agent](/recipes/fastify-migration#give-it-to-a-coding-agent).

#### One route at a time

The Fastify app keeps its routes, plugins and error handler, new endpoints are written in Nest, and existing ones move over when you next change them. Both answer on the same port, so clients don't notice, and every step can be deployed on its own.

##### Requirements

- **Fastify 5.** Nest's `FastifyAdapter` registers plugins that require it, so a Fastify 4 instance fails as soon as Nest starts. Upgrade the app first.
- **TypeScript.** The Nest code on this page is TypeScript. If the Fastify app is written in JavaScript, its files can stay as they are: TypeScript's `allowJs` option compiles them with the rest.

Install Nest next to Fastify:

[[CODE:1]]

##### Run Nest on the Fastify app

Nest normally creates its own Fastify instance. Give it yours instead. Stop the app from listening, and have a function return it. Nest sets the instance's own error and not-found handlers, so two things have to change:

- Move `setErrorHandler()` into a plugin that holds your routes. It keeps handling their errors, and Fastify won't warn about it being overridden.
- Remove `setNotFoundHandler()`. Nest refuses to start with `Not found handler already set`, and it answers unknown routes itself.

[[CODE:2]]

Then pass it to the `FastifyAdapter`, and let Nest listen:

[[CODE:3]]

Both now serve requests from one Fastify instance:

- The Fastify routes answer as they did before, and their errors reach their own error handler.
- Plugins and hooks registered on the root instance apply to Nest's routes too, so `helmet` and the `onRequest` hook above run for them, and `request.jwtVerify()` works inside a Nest guard.
- Hooks registered inside an encapsulated plugin stay inside it, as they always do, so they don't run for Nest's routes.
- Errors in Nest's routes go through its [exception filters](/exception-filters), and a request for a route neither has gets Nest's `404` response.

##### Move a route

Write the route in Nest, and delete it from Fastify in the same change. Fastify's router refuses duplicates, so with both in the code the application stops at startup with `Method 'GET' already declared for route`. A plugin you already use can back a [guard](/guards), and `@RouteSchema()` takes the JSON schema the route already has:

[[CODE:4]]

[[CODE:5]]

Read [Keep what would change without an error](/recipes/fastify-migration#keep-what-would-change-without-an-error) as you go. It applies to every moved route, and the response schema above is there because of it.

##### Finish the migration

When the Fastify routes are gone, register the plugins on the Nest application with `app.register()`, turn the error handler into an [exception filter](/exception-filters), delete the `legacy` folder, and create the application with `new FastifyAdapter()`.

#### All at once

A new Nest application replaces the Fastify app in one release. Until then the Fastify app stays as it is, and it's the reference for what the new application must do. Stay on the `FastifyAdapter` for the migration, even if you plan to change adapters later: that keeps the router, query parsing, body limits and path syntax as they are, so fewer things can change at once.

##### Pin the API with tests

Write tests that know only URLs, so that the same tests run against both applications. Go through every plugin and route, and cover each route's status code, body and important headers, for failures as well as successes. Check that fields a response schema removes stay removed:

[[CODE:6]]

Run them against the Fastify app until they all pass, before writing any Nest code:

[[CODE:7]]

##### Translate the application

Create the Nest application with `nest new` next to the Fastify one, [switch it to the `FastifyAdapter`](/http/performance#fastify-adapter), and move each routes plugin to a controller:

| Fastify | Nest |
| --- | --- |
| `app.register(routes, {{ '{' }} prefix {{ '}' }})` | A [controller](/controllers), `@Controller('api/orders')`, in a [module](/modules) |
| `app.get('/:id', handler)` | `@Get(':id')` on a method |
| `request.params`, `request.query`, `request.body` | `@Param()`, `@Query()`, `@Body()` |
| `schema: {{ '{' }} querystring, body, response {{ '}' }}` | `@RouteSchema()` from `@nestjs/platform-fastify`, with the same JSON schemas |
| `onRequest: app.authenticate` | A [guard](/guards) |
| `preHandler: app.requireRole('admin')` | Metadata on the route, read by a guard |
| A decorator such as `request.jwtVerify()` | The same call on `@Req()`, with the plugin registered |
| `reply.code(201).send(x)` | `return x`, with `@HttpCode()` when the status isn't the default |
| `reply.code(204).send()` | `@HttpCode(204)`, and return nothing |
| `reply.redirect(url, 301)` | `@Redirect(url, 301)` |
| `reply.setCookie()` | `@Res({{ '{' }} passthrough: true {{ '}' }}) reply`, then `reply.setCookie()` and `return` as usual |
| `reply.type('application/json')` | `@Header('content-type', 'application/json')` |
| `reply.send(stream)` | `new StreamableFile(stream, {{ '{' }} type {{ '}' }})` |
| `await request.file()` | The same call on `@Req()`, with `@fastify/multipart` registered |
| `app.register(plugin, options)` | `app.register(plugin, options)` |
| `app.addHook('onRequest', fn)` | `app.getHttpAdapter().getInstance().addHook('onRequest', fn)` |
| `setErrorHandler()` and `setNotFoundHandler()` | One global [exception filter](/exception-filters) |
| A plugin that decorates the instance with a database pool | A [provider](/fundamentals/custom-providers#value-providers-usevalue) |

Route paths stay as they are, since the same router reads them: `search/:term?`, `items/:id(^\\d+$)`, and `assets/*`, with `@Param('*')`.

##### Keep what would change without an error

Two of these expose data without any error at all, so check them first:

| In Fastify | In a Nest application | To keep the old behavior |
| --- | --- | --- |
| A response schema removes every field it doesn't list, so handlers can return whole records | Without the schema, every field is sent, `passwordHash` included | `@RouteSchema({{ '{' }} response {{ '}' }})` on each route that had one |
| A `POST` answers `200`, and `response: {{ '{' }} 200: schema {{ '}' }}` applies | A `POST` answers `201`, so a schema keyed on `200` no longer applies, and the fields come back too | `@HttpCode(200)`, or key the schema on `201` |
| Authentication in `onRequest` runs before validation, so an invalid request with no token gets a `401` | `@RouteSchema({{ '{' }} body {{ '}' }})` validates before any guard, so that request gets a validation error | Validate with a [pipe](/application/validation#schema-based-validation), `@Body({{ '{' }} schema {{ '}' }})`, which runs after guards, on routes where it matters |
| Errors have the shape your handler gives them | `{{ '{' }} statusCode, message, error {{ '}' }}` | A global exception filter |
| A validation error reaches your handler with `err.validation` | It reaches the filter the same way, with `exception.validation` | The same filter |
| An unknown route gets your not-found handler | `NotFoundException`, with Nest's body | The same filter |

The filter must keep your error shape for every error, including the ones Nest and Fastify raise themselves. Body errors such as malformed JSON and a body over the limit arrive as an `HttpException`:

[[CODE:8]]

[[CODE:9]]

##### Switch over

Run the same tests against the Nest application, and fix the application rather than the tests:

[[CODE:10]]

When they pass, deploy it in place of the Fastify app, and keep the last Fastify release deployable until the new one has served real traffic.

#### Give it to a coding agent

Either approach works with a coding agent, and all at once is the better fit when the application is small enough to review in one change. Point the agent at this page and hold it to the tests, so that it can't declare success on code that merely compiles:

[[CODE:11]]
