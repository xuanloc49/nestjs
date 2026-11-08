### Next.js

A Next.js application can use Nest as its backend: one repository, one origin for the browser, and request schemas shared by both applications.

Route handlers and Server Actions are enough for a small backend. As it grows, with background jobs, webhooks, a public API, a mobile client or a team of its own, it needs the structure that Nest gives it: modules, dependency injection, guards, and validation on every route. Next.js keeps rendering, and Nest takes over everything behind it:

| Next.js | Nest |
| --- | --- |
| Pages, layouts and Server Components | The API, and the business rules behind it |
| Forms, and the state of the browser | Validating what the forms send |
| Fetching data to render it | The database, and every other data source |
| | Sign-in, permissions, webhooks, queues, scheduled jobs |
| | Other clients, such as a mobile app |

This page sets up a Nest application next to a Next.js one, and then moves a backend from one to the other:

- Both live in one repository, as npm workspaces.
- The browser calls `/api` on the Next.js origin, and Next.js passes the request on to Nest, so cookies work without CORS.
- Zod schemas in a shared package validate a form in the browser and the same request in Nest.
- The route handlers you already have keep answering, and [move to Nest](/recipes/nextjs#migrate-a-nextjs-backend-to-nest) one at a time.

#### Project layout

[[CODE:1]]

The root `package.json` declares the workspaces:

[[CODE:2]]

Create both applications without installing their packages, then install everything once, from the root:

[[CODE:3]]

`--skip-git` also leaves the Nest application without a `.gitignore`, so add one at the root of the repository:

[[CODE:4]]

The Next.js development server takes port `3000`, so give Nest another one in `apps/api/src/main.ts`, and put its routes under `/api`, the path the browser will call:

[[CODE:5]]

#### Send `/api` to Nest

Next.js [rewrites](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites) pass a request on to another server and return its response, without the browser seeing a redirect. In `apps/web/next.config.ts`, send every `/api` request that the Next.js app doesn't answer itself to Nest:

[[CODE:6]]

The browser talks to one origin, the Next.js one. A cookie that Nest sets, such as a session, is stored for that origin and sent back with every request to it, so it reaches Nest and Next.js alike, and Nest needs no [CORS](/security/cors) configuration.

`fallback` rewrites run after Next.js has checked all of its pages and route handlers, dynamic ones included. So an existing route handler, such as `src/app/api/orders/[id]/route.ts`, keeps answering its requests, and only the rest reach Nest. An `/api` path that neither app has gets Nest's `404` response. An `afterFiles` rewrite would run before dynamic routes, and pass that route handler's requests to Nest.

Set `API_URL` for development in `apps/web/.env.development`:

[[CODE:7]]

> warning **Warning** Next.js reads `rewrites()` when it builds the application, so `API_URL` must also be set for `next build`: a different value when the application starts doesn't change where its rewrites go.

Everything an API does goes through the rewrite untouched: cookies, raw request bodies for [webhook](/http/webhooks) signatures, [server-sent events](/http/server-sent-events) as they're written, and [WebSockets](/websockets/gateways) with the `ws` adapter. Two limits fail badly, with a `500` and no useful error: a request body over 10 MB, and a response that takes more than 30 seconds to start, such as a call to a language model. Raise them with two experimental options of Next.js:

[[CODE:8]]

Nest also sees the Next.js server as the client, so `req.ip` is its address, and anything that limits requests per IP address, such as [`@nestjs/throttler`](/security/rate-limiting), treats all your visitors as one. Next.js doesn't add `X-Forwarded-For` itself, but it passes on the one set by a load balancer in front of it. If you have one, call `app.set('trust proxy', 1)` on the `NestExpressApplication`. Without one, leave it off, or a visitor can claim any address.

#### Share schemas between the apps

Nest validates a request body against any [Standard Schema](https://standardschema.dev/) schema, such as a Zod one (see [Schema-based validation](/application/validation#schema-based-validation)). Put the schemas in a package of their own, `packages/contracts`, and the Next.js app validates its forms with the very schema that Nest checks the request against, and both use the types inferred from it.

[[CODE:9]]

[[CODE:10]]

[[CODE:11]]

The package is compiled, so that both applications import plain JavaScript and its type declarations. Add it to both applications, and build it (`npm run dev -w @acme/contracts` rebuilds it on every change):

[[CODE:12]]

In Nest, bind the `StandardSchemaValidationPipe` and pass the schema to `@Body()`:

[[CODE:13]]

[[CODE:14]]

In Next.js, a form checks its input with the same schema before it sends anything:

[[CODE:15]]

A request that doesn't come from your form, from a script or an older version of the app, is still checked, by Nest:

[[CODE:16]]

To run everything with one command, add `concurrently` to the root, and two scripts to its `package.json`. The shared package has to be built before the applications that import it:

[[CODE:17]]

[[CODE:18]]

#### Sign users in

Sign-in belongs to Nest, since the API is what it protects. [`@nestjs/authentication`](/security/authentication) keeps the session in an `HttpOnly` cookie, and a form signs in by posting to `/api/auth/sign-in` through the rewrite, like any other request from the browser. That chapter builds it, and one setting is specific to running behind Next.js.

The module ignores a session cookie on a `POST` from another origin, and refuses sign-ins from one, to stop cross-site request forgery. Behind a rewrite, Nest's own host is `localhost:3001` while the browser's `Origin` is `http://localhost:3000`. Browsers that send `Sec-Fetch-Site` pass anyway, but a client that sends only `Origin` gets a `403`. So name the Next.js origin as trusted:

[[CODE:19]]

Requests from any other origin are still refused.

#### Call Nest from the Next.js server

Server Components and Server Actions run on the Next.js server, so they call Nest directly, without the rewrite. The browser's cookies don't go with those requests unless you forward them, so put that in one helper:

[[CODE:20]]

[[CODE:21]]

> warning **Warning** A page that fetches without reading cookies may be rendered during `next build`, so Nest has to be reachable from the build, or it fails with `fetch failed`.

#### Migrate a Next.js backend to Nest

Next.js's own [backend guide](https://nextjs.org/docs/app/guides/backend-for-frontend) says that its backend capabilities "are not a full backend replacement". A Next.js backend works well until it has to be one, and past that point a separate backend can be the simpler of the two.

##### Why it can be simpler

It isn't less code. The same four endpoints (list, create, read and cancel an order, for a signed-in user) came to about the same number of lines in route handlers as in a Nest controller and service. What changes is what you have to remember:

| | Route handlers | Nest |
| --- | --- | --- |
| Checking the session | In every handler, four times here. A handler that forgets is public | Once, in a [global guard](/security/authentication). A new route answers `401` until you mark it `@Public()` |
| Validating a body | Each handler parses it and builds its own `400` | `@Body({{ '{' }} schema {{ '}' }})`, and the handler only runs with valid input |
| A missing record | Each handler builds its own `404`, and a helper can't end the request for it | `throw new NotFoundException()` from anywhere, such as a service |
| Testing the logic | Handlers read `cookies()`, which throws `was called outside a request scope`, so a test has to mock `next/headers` | A service is a class: `new OrdersService()`, with no HTTP and no mocks of the framework |
| Finding an endpoint | One file per path, with the path in the folder names | One controller per resource |
| Scheduled jobs | Nothing built in, so a platform has to call a URL | `@Cron()`, in the same process as the rest of the application |
| WebSockets | Won't work where handlers are deployed as lambda functions, says the same guide | [Gateways](/websockets/gateways) |

Here's one of those four endpoints in both. As a route handler:

[[CODE:22]]

The other handlers repeat its first lines. In Nest, the guard has already checked the session, and the service holds the rule, where the other methods can reuse it and a test can reach it:

[[CODE:23]]

[[CODE:24]]

[[CODE:25]]

You can get part of the way with helpers: a `withSession()` wrapper, then one for validation, then one that turns errors into responses. That's a reasonable step, and it's also writing your own guards, pipes and exception filters.

It does cost something. There's a second application to deploy, a rewrite to configure, and a network hop between a Server Component and its data. If your backend is a few handlers with one client and no background work, stay on route handlers.

##### What goes where

Write new endpoints in Nest, and move the existing ones when you next change them. Each piece of a Next.js backend has a place to go:

| In Next.js | In Nest |
| --- | --- |
| A route handler | A [controller](/controllers) method |
| A database query in a Server Component or a Server Action | A [service](/providers) behind an endpoint, called through `api()` |
| `getSession()` at the top of every handler | The global guard of [`@nestjs/authentication`](/security/authentication), and `@CurrentUser()` |
| Checking `request.json()` by hand | `@Body({{ '{' }} schema {{ '}' }})` |
| Role checks inside handlers | [`@nestjs/authorization`](/security/authorization) |
| A webhook route handler that reads `request.text()` | `@VerifyWebhook()` from [`@nestjs/webhooks`](/http/webhooks) |
| A cron route called by the platform | `@Cron()` from [`@nestjs/schedule`](/application/task-scheduling) |
| Work started with `after()`, such as sending email | A [queue](/application/queues), and [`@nestjs/mail`](/application/mail) |

##### Move one route

Write the endpoint in Nest under the same path, and delete the route handler. The URL doesn't change, so neither does any client. Because route handlers come before the rewrite, both can be in the code until you delete the route handler.

Then check what a client can see:

- **The status code.** `NextResponse.json()` answers `200` on a `POST`, and a Nest `POST` answers `201` unless you add `@HttpCode(200)`.
- **The shape of an error**, which is now `{{ '{' }} statusCode, message, error {{ '}' }}`. A [global exception filter](/recipes/express-migration#keep-what-would-change-without-an-error) keeps the old shape if clients depend on it.
- **Dynamic segments.** `[id]` becomes `:id`, and a catch-all `[...path]` becomes `*path`, whose `@Param('path')` is an array of segments.

##### Move queries out of pages

A Server Component or a Server Action that queries the database directly makes a request instead, and the query moves to a Nest service:

[[CODE:26]]

When nothing in `apps/web` imports the database client any more, remove it from the Next.js application, so that a page can't go around the API.

#### Deployment

The two applications deploy separately. Whatever the platform, the order is the same: build `@acme/contracts`, then the applications, with `API_URL` set for `next build`.

Nest runs anywhere Node.js does (see [Deployment](/deployment)). If you deploy the Next.js application on Vercel, set `API_URL` in its environment to Nest's address. Vercel can [deploy Nest](https://vercel.com/docs/frameworks/backend/nestjs) too, as a project of its own. Other clients, such as a mobile app, call Nest's address directly, and need a [CORS](/security/cors) configuration only if they run in a browser on another origin.
