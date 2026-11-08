### HTTP client

Most applications call other services over HTTP. The `@nestjs/http-client` package provides a client for this, built on the `fetch` API that ships with Node.js. It adds what `fetch` leaves out: base URLs, default headers, JSON bodies, path and query parameters, typed responses, timeouts, retries, interceptors, and named clients. You configure it as a Nest module and inject it like any other provider.

The package has no dependencies besides `@nestjs/common` and `@nestjs/core`. Every method returns a Promise, so you `await` requests and handle failures with `try`/`catch`. If you prefer Observables, see [Working with RxJS](/application/http-client#working-with-rxjs).

> info **Hint** This package replaces the Axios-based `HttpModule` from `@nestjs/axios`, which this chapter used to describe. `@nestjs/axios` remains available. See [Migrating from @nestjs/axios](/application/http-client#migrating-from-nestjsaxios) to switch.

#### Installation

To get started, install the package:

[[CODE:1]]

#### Getting started

Import `HttpClientModule` into the module that makes the requests, and register a client with the `register()` method:

[[CODE:2]]

Then inject the `HttpClient` class:

[[CODE:3]]

The request goes to `https://api.example.com/v1/cats`. A relative URL is appended to `baseUrl` with exactly one `/` between them, so the `/v1` prefix is kept (unlike `new URL('/cats', base)`, which would drop it). A client without a `baseUrl` requires absolute URLs.

Like other `register()` methods, each call creates a client for the module that imports it. To make a client injectable in every module, set `isGlobal: true`.

#### Named clients

An application usually talks to several upstream services, each with its own base URL, credentials, and timeouts. Give each client a `name`:

[[CODE:4]]

and inject it with the `@InjectHttpClient()` decorator:

[[CODE:5]]

A client registered without a name is the default client, injected as `HttpClient`. The `getHttpClientToken(name)` function returns the injection token of a client, which is useful in tests and custom providers.

#### Application-wide defaults

Settings that every client shares, such as a `user-agent` header, a timeout, a retry policy, or a logging interceptor, go into `HttpClientModule.forRoot()`. Import it once, in the root module. It is always global:

[[CODE:6]]

`forRoot()` doesn't register a client itself, and it doesn't take a `baseUrl`. Each client's own settings win over its defaults, with three exceptions: headers are merged (set a header to `null` in a client to remove a default), retry settings are merged field by field, and the `forRoot()` interceptors run before the client's own.

#### Async configuration

To build a client's options from other providers, such as the `ConfigService` from the [configuration](/application/configuration#getting-started) chapter, use `registerAsync()`:

[[CODE:7]]

The factory can be `async`. It returns the same options as `register()`, typed `HttpClientFactoryOptions`, except for `name`, `isGlobal`, `imports`, and interceptor classes: Nest needs those to build the module, before the factory runs, so they go next to `useFactory`. A factory that returns one of them stops the application at startup.

Instead of a factory, you can pass a class that implements the `HttpClientOptionsFactory` interface. Nest instantiates it inside the client's module and calls its `createHttpClientOptions()` method:

[[CODE:8]]

[[CODE:9]]

To reuse a provider that already exists instead of creating a private copy, pass `useExisting: GithubClientConfig`, with the module that exports it in `imports`. `forRootAsync()` works the same way. Its `useClass` or `useExisting` class implements `HttpClientModuleOptionsFactory`, with a `createHttpClientModuleOptions()` method.

#### Making requests

A client has a method for each HTTP verb: `get()`, `post()`, `put()`, `patch()`, `delete()`, `head()`, and `options()`. Each one takes a URL and an optional options object, and resolves to an `HttpResponse`. The `request()` method takes the verb as the `method` option.

[[CODE:10]]

The options mirror what a Nest controller reads from a request:

- `params` fills the `:name` segments of the path, URI-encoded. A segment without a value throws, even when `params` is omitted, and so does a key that matches no segment, or a value that would move the request to another endpoint (an empty string, `.`, or `..`).
- `query` is an object or a `URLSearchParams` instance, appended to any query already in the URL. Arrays repeat the key (`topic=nest&topic=typescript`), `Date` values become ISO strings, and `null` and `undefined` values are skipped. The first request above goes to `https://api.github.com/orgs/nestjs/repos?type=public&sort=updated&topic=nest&topic=typescript`.
- `json` is serialized with `JSON.stringify()`, and sets the `content-type: application/json` header unless you set one.
- `body` is passed to `fetch` as is: a string, `Buffer`, `FormData`, `URLSearchParams`, `Blob`, a web or Node.js stream, or an async iterable. Pass either `json` or `body`, not both. A `GET` or `HEAD` request with a body throws before anything is sent.
- `headers` is merged over the client's headers. A `null` value removes a header.
- `timeout`, `retry`, `signal`, `throwOnHttpError`, `redirect`, and `dispatcher` override the client's settings for one request, and are covered below.
- `context` is a free-form object that [interceptors](/application/http-client#interceptors) can read.

The type argument, such as `Repo[]`, describes `data`. Nothing checks it at runtime, so validate responses from APIs you don't control. The `responseType` option controls how the body is read:

| `responseType` | `data` |
| --- | --- |
| `'auto'` (default) | Parsed JSON when the `content-type` is JSON (including `+json` types), otherwise a string. `undefined` when the body is empty, for `204` and `205` responses, and for `HEAD` requests. A `304` response throws by default, like any non-2xx; with `throwOnHttpError: false`, its `data` is `undefined`. |
| `'json'` | Parsed JSON, whatever the content type. |
| `'text'` | A string. |
| `'arrayBuffer'` | An `ArrayBuffer`. |
| `'stream'` | A Node.js `Readable`. See [Streaming responses](/application/http-client#streaming-responses). |
| `'response'` | The web `Response`, with its body unread. |

The type of `data` follows `responseType`, so `responseType: 'text'` resolves to `HttpResponse<string>`. A successful response whose body isn't valid JSON, although it was expected to be, rejects with an `HttpParseError`. The response object has the following shape:

[[CODE:11]]

#### Timeouts and cancellation

`fetch` has no timeout of its own, apart from the 5-minute limits of undici, the HTTP client inside Node.js. Set a `timeout` on each client, either in milliseconds or as a duration string such as `'500ms'`, `'5s'`, or `'2m'`. An invalid value fails at startup, with an error that names the option. `0` means no timeout, which is the default.

The timeout applies to **each attempt**, not to the whole call. It covers the attempt's interceptors and reading the response body. For `responseType: 'stream'` and `'response'`, it stops once the headers arrive, so a long download isn't cut off. When it elapses, the attempt fails with an `HttpTimeoutError`, and the request is retried like after any other [transient failure](/application/http-client#retries).

To cancel a request, pass an `AbortSignal` as the `signal` option. It is combined with the timeout. A cancelled request rejects with the signal's `reason`, as `fetch` does, and is never retried, even while it waits between two attempts.

Because of retries, a call can take up to `attempts × timeout`, plus the waits between attempts. To put a limit on the whole call, pass a deadline as the signal:

[[CODE:12]]

The deadline rejects with a `DOMException` named `TimeoutError`, which `toHttpException()` maps to `504 Gateway Timeout`, like an `HttpTimeoutError`. To combine it with another signal, use `AbortSignal.any([signal, AbortSignal.timeout(10_000)])`.

#### Retries

Retries are **on by default**. Without any configuration, a client makes up to 3 attempts for `GET`, `HEAD`, `OPTIONS`, `PUT`, and `DELETE`, the methods that HTTP defines as idempotent. It retries after:

- connection errors, such as a refused or reset connection (including a reset while the body is read),
- per-attempt timeouts,
- `408`, `429`, `500`, `502`, `503`, and `504` responses.

Between attempts, the client waits with exponential backoff and full jitter: a random delay of up to 200 ms after the first attempt, up to 400 ms after the second, and so on, capped at 30 seconds. A `Retry-After` response header, in seconds or as an HTTP date, replaces the backoff. When it asks for more than the cap, the client doesn't wait at all, and returns (or throws) the `429` or `503` response right away. A request whose body is a stream is never retried, because the first attempt consumed it.

The `retry` option takes a number of attempts, `false` for a single attempt, or an object:

[[CODE:13]]

Every field you omit keeps its default. `backoff` can also be a function that receives the number of the attempt that failed and its error, and returns a duration. `jitter` can be `'full'`, `'equal'` (at least half of the computed delay), or `'none'`. `retryIf` is only asked about failures the client would retry anyway, so it can narrow the defaults but not widen them; use `methods` and `statusCodes` for that. It receives the `HttpResponseError` (with its `body`), `HttpTimeoutError`, or `HttpNetworkError` of the attempt that failed.

Retry settings are layered: `forRoot()`, then the client, then the request. Each layer overrides only the fields it sets, and a later layer can turn retries back on after an earlier `false`. `methods` and `statusCodes`, however, **replace** the default lists instead of adding to them.

`POST` and `PATCH` aren't retried, because repeating them could, for example, charge a customer twice. When the upstream API supports idempotency keys, send one and opt in for that request:

[[CODE:14]]

The key identifies the operation, so every attempt sends the same one, and the upstream returns the original result instead of creating a second charge. Setting `methods: ['POST']` on the client instead would also stop `GET` retries, since the list replaces the default one.

> warning **Warning** Retries multiply along a chain of services. If service A calls B, B calls C, and every hop makes 3 attempts, one failing request to C turns into 9 calls to C, which arrive exactly when C is already struggling. Retry at one layer only, usually the service that calls the external dependency, and set `retry: false` on clients that call your own services.

#### Handling errors

A request rejects with one of the following errors, all of which extend the `HttpClientError` class:

| Error | When | Fields |
| --- | --- | --- |
| `HttpResponseError` | The upstream answered with a non-2xx status. | `status`, `statusText`, `headers`, `body` (parsed JSON, otherwise text), `method`, `url` |
| `HttpTimeoutError` | The `timeout` elapsed on the last attempt. | `timeoutMs`, `method`, `url` |
| `HttpNetworkError` | The connection failed: DNS, a refused or reset connection, TLS, or a redirect the client refused (to another origin, or with `redirect: 'error'`). | `cause` (for example, with `cause.code` set to `ECONNREFUSED`), `method`, `url` |
| `HttpParseError` | A successful response isn't valid JSON, although it was expected to be. | `status`, `statusText`, `headers`, `body` (the raw text), `method`, `url` |

A cancelled request rejects with the signal's reason, and errors thrown by interceptors propagate unchanged. A request the client refuses to send, such as one with an invalid `params` value, rejects with a `TypeError`. To receive non-2xx responses as values instead, set `throwOnHttpError: false` on the client or on a request, and check `ok` or `status` yourself.

If one of these errors escapes a route handler, Nest answers `500 Internal Server Error`. For your API's callers, though, a failing upstream is usually a `502 Bad Gateway`, and one that doesn't answer in time is a `504 Gateway Timeout`. The `toHttpException()` function maps the errors accordingly:

| Error | Becomes |
| --- | --- |
| `HttpResponseError` | `502 Bad Gateway`, or the upstream status and body when the status is listed in `forward` |
| `HttpTimeoutError`, or the `TimeoutError` of an `AbortSignal.timeout()` deadline | `504 Gateway Timeout` |
| `HttpNetworkError`, `HttpParseError` | `502 Bad Gateway` |
| Anything else, including an `HttpException` | Returned unchanged, so Nest handles it as usual |

[[CODE:15]]

By default, the upstream body isn't passed on to the caller, since it may describe the upstream's internals. To pass selected statuses through with their body, such as a `422` whose body tells the caller what to fix, use `toHttpException(error, options)` with `forward` set to `[422]`, or to `true` for every status. The original error is kept as the exception's `cause`.

Nest's built-in exception filter [doesn't log](/exception-filters#exceptions-logging) an `HttpException`, so a `502` or `504` would leave no trace. `toHttpException()` therefore logs every failure that it turns into a `5xx`, with the `HttpClient` context:

[[CODE:16]]

Set the `log` option to `false` when something else, such as your own exception filter, already logs upstream failures.

Instead of mapping errors in every service, you can let them leave the handler unchanged and map them in an [exception filter](/exception-filters#binding-filters). This keeps call sites free of `try`/`catch`, and interceptors further out still see the original error:

[[CODE:17]]

An `AbortSignal.timeout()` deadline isn't an `HttpClientError`, so add `DOMException` to `@Catch()` if you use deadlines. `toHttpException()` returns an `HttpException`, so in a microservice or WebSocket handler, convert the errors to an `RpcException` or `WsException` yourself.

> info **Hint** Error messages and objects end up in logs, so the client keeps secrets out of them. A message never includes the response body, and the URL in it has its query values masked, as in `GET https://api.example.com/users?email=***`. The `url`, `headers`, and `body` fields are non-enumerable: your code can read them, but loggers and `JSON.stringify()` leave them out.

#### Interceptors

An interceptor wraps every request a client sends. It receives the request and a `next` function that sends it, and returns the resulting web `Response`. The simplest form is a function:

[[CODE:18]]

The `HttpRequest` object holds the `method`, the `url` (a `URL` instance), the `headers` (a `Headers` instance), the `body`, the `signal`, the `attempt` number, and the request's `context`. You can change it in place, or pass a modified copy to `next()`. Interceptors see the response **before** the status check, so a `4xx` or `5xx` response reaches them too. An interceptor must return what `next()` resolves to, or a `Response` of its own.

When an interceptor needs other providers, write it as a class that implements the `HttpClientInterceptor` interface:

[[CODE:19]]

Pass interceptors in the `interceptors` array of `register()` or `forRoot()`, or next to `useFactory` in the async variants:

[[CODE:20]]

Nest resolves interceptor classes when the application initializes, so an interceptor may even depend on a service that injects the same client. If the class is a provider anywhere in the application, as `GithubAuthInterceptor` is above, that instance is used. Otherwise, Nest creates it inside the client's own module, which sees global providers and the modules you pass in the `imports` option of `register()`. An async factory may also return interceptors in its options, but only functions and instances, such as `apiKeyInterceptor(config.getOrThrow('API_KEY'))`.

Interceptors run in the order they are listed, the first one outermost, and the `forRoot()` interceptors run before the client's own. They run **once per attempt**, so a retry gets a fresh token, and `request.attempt` tells them which attempt it is. When an attempt fails, `next()` rejects with an `HttpNetworkError` or `HttpTimeoutError`, or with the abort reason. This makes an interceptor a good place to log upstream traffic:

[[CODE:21]]

Registered with `HttpClientModule.forRoot()` and `interceptors: [HttpLoggingInterceptor]`, it logs the requests of every client. It logs the path without the query string, which often carries personal data or keys.

> info **Hint** For tracing, you don't need an interceptor. [NestJS Observe](/observability/distributed-tracing#http-to-http) records every outbound `fetch` call as a span, and propagates the trace id to other Nest services.

#### Streaming responses

To pass a large response through without buffering it in memory, set `responseType: 'stream'`. The `data` is a Node.js `Readable`, which you can return from a route handler in a [`StreamableFile`](/http/file-upload#streaming-files):

[[CODE:22]]

The timeout stops once the headers arrive, while cancelling the `signal` still stops the download. A non-2xx response is read and thrown as an `HttpResponseError`, as usual. Don't pass the upstream's `content-length` header on as the `length` option: `fetch` decompresses gzip and brotli bodies, so the stream can be longer than the header says. For the web `ReadableStream`, use `responseType: 'response'` and read `data.body`.

#### Proxies, TLS, and redirects

Node.js's `fetch` runs on undici, whose default dispatcher keeps a pool of keep-alive connections, so the common case needs no configuration. To change the pool size, route through a proxy, or use custom TLS settings (a private CA, or client certificates), pass an undici dispatcher as the `dispatcher` option:

[[CODE:23]]

For a proxy, pass `new ProxyAgent('http://proxy.internal:3128')`. Node.js doesn't expose these classes from a built-in module, so install the `undici` package yourself (`@nestjs/http-client` doesn't depend on it), preferably with the major version that your Node.js release bundles. A Node.js `http.Agent`, which Axios accepts as `httpsAgent`, doesn't work with `fetch`, and fails to compile. To route every client through the proxy from the `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` environment variables instead, start Node.js with `--use-env-proxy` (or set `NODE_USE_ENV_PROXY=1`) on a release that supports it.

The `redirect` option controls how `3xx` responses are handled. A client with a `baseUrl` follows redirects on its own origin only, and fails one to another host with an `HttpNetworkError`, since its headers carry that upstream's credentials (see [Security](/application/http-client#security)). A client without a `baseUrl` lets `fetch` follow redirects anywhere, dropping the `authorization` and `cookie` headers when the origin changes, but not others.

Set `redirect` to `'follow'` to follow redirects anywhere with a `baseUrl` too, for an API that intentionally redirects to another host, to `'error'` to fail on every redirect, or to `'manual'` to receive `3xx` responses as they are. A `3xx` response isn't a success, so combine `'manual'` with `throwOnHttpError: false` to read its `location` header.

#### Security

The client guards against a few common mistakes:

- **A client with a `baseUrl` only sends requests to its origin.** An absolute URL on the same origin, such as a pagination link, works, but one on another host throws before anything is sent. A redirect to another host fails too, before the request is repeated there. The client's headers and interceptors carry that upstream's credentials, and a URL taken from user input or from an upstream response must not receive them. Use a client without a `baseUrl` to call arbitrary hosts, or `redirect: 'follow'` for an API that redirects to another host on purpose.
- **Path parameters are encoded.** Put request values in `params` and `query` instead of building the path with string interpolation. They are URI-encoded, and a `params` value such as `..` throws instead of moving the request to another endpoint.
- **Credentials in URLs are refused.** A `baseUrl` or request URL such as `https://user:pass@example.com` throws. Send credentials in the `authorization` header instead. A header value with a line break throws, without quoting the value in the message.
- **Errors are safe to log**, as described in [Handling errors](/application/http-client#handling-errors).

#### Testing

A stub `fetch` is the easiest way to test code that calls an external API. Pass it to `HttpClientModule.forRoot()`, and every client uses it, while keeping its base URL, headers, retry policy, and interceptors. The stub only has to return a standard `Response`:

[[CODE:24]]

Give every call its own `Response`, as `mockResolvedValueOnce()` does above: a response body can be read only once, so `mockResolvedValue()` would hand an already-read response to a retry. A client that sets its own `fetch` option keeps it, since a client's settings win over the `forRoot()` defaults. A client without one calls `globalThis.fetch` on every request, so `vi.stubGlobal('fetch', stub)` works too.

For an end-to-end test of an application that already calls `forRoot()`, override its options instead. This replaces every `forRoot()` option, except the interceptors passed directly to `forRoot()` or next to `useFactory`, which keep running:

[[CODE:25]]

To keep HTTP out of a test entirely, replace the client itself with `overrideProvider(getHttpClientToken('github'))`. Outside of Nest, for example in a script, create a client with `new HttpClient(options)`.
