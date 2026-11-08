### Async Local Storage

`AsyncLocalStorage` is a [Node.js API](https://nodejs.org/api/async_context.html#class-asynclocalstorage) (based on the `async_hooks` API) that provides an alternative way of propagating local state through the application without explicitly passing it as a function parameter. It's similar to thread-local storage in other languages.

The main idea of Async Local Storage is that you can _wrap_ a function call with the `AsyncLocalStorage#run` call. All code invoked within the wrapped call gets access to the same `store`, which is unique to each call chain.

In the context of NestJS, this means that if you find a place within the request's lifecycle to wrap the rest of the request's code, you can access and modify state visible only to that request. This can serve as an alternative to REQUEST-scoped providers, avoiding some of their limitations.

Alternatively, you can use ALS to propagate context for only a part of the system (e.g., the _transaction_ object) without passing it around explicitly across services, which can increase isolation and encapsulation.

If your application is instrumented with [NestJS Observe](/observability/overview), you already have a request-scoped store and don't need to build one. See the [NestJS Observe](/recipes/async-local-storage#nestjs-observe) section below.

#### Custom implementation

The NestJS core framework doesn't provide a built-in abstraction for `AsyncLocalStorage`, so let's walk through how to implement it yourself for the simplest HTTP case, to get a better understanding of the whole concept:

> info **Hint** For ready-made solutions, see the [`@nestjs/observe`](/recipes/async-local-storage#nestjs-observe) and [`nestjs-cls`](/recipes/async-local-storage#nestjs-cls) sections below.

1. First, create a new instance of `AsyncLocalStorage` in a shared source file. Since we're using NestJS, let's also turn it into a module with a custom provider.

[[CODE:1]]
> info **Hint** `AsyncLocalStorage` is imported from `node:async_hooks`.

2. We're only concerned with HTTP, so let's use a middleware to wrap the `next` function with `AsyncLocalStorage#run`. Since middleware is the first thing a request hits, this makes the `store` available in all enhancers and the rest of the system.

[[CODE:2]]

3. Now you can access the local store instance anywhere within the lifecycle of a request.

[[CODE:3]]

4. You now have a way to share request-related state without injecting the whole `REQUEST` object.

> warning **Warning** While this technique is useful for many use cases, it inherently obscures the code flow (by creating implicit context), so use it responsibly, and especially avoid creating contextual "[God objects](https://en.wikipedia.org/wiki/God_object)".

### NestJS Observe

If you run [NestJS Observe](/observability/overview), the `@nestjs/observe` SDK already maintains an `AsyncLocalStorage` store for every request, job, and message it instruments. This store carries the trace context through your call stack. `TracerService` exposes it, so request-scoped state is something you read and write rather than something you set up: there's no module to write, no middleware to mount, and nothing to re-wire per transport.

> info **Hint** This is the same `TracerService` documented in [Manual instrumentation](/observability/manual-instrumentation). This section covers only its async local storage side; spans, handled errors, and custom metrics are described there.

#### Setup

No setup is needed beyond the standard SDK integration described in [Observability → SDK](/observability/sdk): install the package, import `ObserveModule.forRoot()`, and pass `ObserveInstrument` to `NestFactory.create()`.

[[CODE:4]]

`ObserveModule` exports `TracerService`, so you can inject it anywhere in your application:

[[CODE:5]]

#### Reading and writing the store

`setAttribute(key, value)` writes to the current context store, and `getAttribute(key)` reads the value back from anywhere downstream on the same request (a different service, a guard, or an interceptor) without threading it through every function signature:

[[CODE:6]]

[[CODE:7]]

`getAttribute()` returns `undefined` for a key that was never set. Both methods throw when called outside a traced context, since there's no store to read from or write to. If a value may legitimately be read before any request exists, guard the call accordingly.

#### Typing the store

Pass the shape of your store as the first type argument of `TracerService` to have keys and values type-checked, including nested paths:

[[CODE:8]]

#### Beyond HTTP

Because the store is created by the instrumentation rather than by a middleware, it exists wherever the SDK traces an operation: HTTP and GraphQL requests, gRPC and `@nestjs/microservices` messages, and background work such as BullMQ consumers and cron runs. The pattern above is identical in all of them. This is the practical difference from a hand-rolled, middleware-based implementation, which only covers HTTP.

The store also holds the current trace ID, so it doubles as the correlation key for logs and downstream services. `currentTraceId()` returns it. Unlike `getAttribute()`, it returns `null` outside a traced context instead of throwing:

[[CODE:9]]

> info **Hint** `ObserveModule` also exports the underlying `AsyncLocalStorage` instance. `setAttribute()` and `getAttribute()` are the supported way to access the store; inject the instance directly only if you need something they don't expose.

### NestJS CLS

The [nestjs-cls](https://github.com/Papooch/nestjs-cls) package provides several developer experience improvements over plain `AsyncLocalStorage` (`CLS` is an abbreviation of _continuation-local storage_). It abstracts the implementation into a `ClsModule` that offers various ways of initializing the `store` for different transports (not only HTTP), as well as strong typing support.

You can then access the store with an injectable `ClsService`, or abstract it away from the business logic entirely by using [Proxy Providers](https://www.npmjs.com/package/nestjs-cls#proxy-providers).

> info **Note** `nestjs-cls` is a third-party package and is not managed by the NestJS core team. Please report any issues with the library in the [nestjs-cls repository](https://github.com/Papooch/nestjs-cls/issues).

#### Installation

Apart from peer dependencies on the `@nestjs` packages, it uses only built-in Node.js APIs. Install it like any other package:

[[CODE:10]]

#### Usage

You can implement functionality similar to the [custom implementation](/recipes/async-local-storage#custom-implementation) above using `nestjs-cls`, as follows:

1. Import the `ClsModule` in the root module.

[[CODE:11]]

2. Then use the `ClsService` to access the store values.

[[CODE:12]]

3. To get strong typing of the store values managed by the `ClsService` (and auto-suggestions for the string keys), use the optional type parameter `ClsService<MyClsStore>` when injecting it.

[[CODE:13]]

> info **Hint** You can also let the package automatically generate a request ID and access it later with `cls.getId()`, or get the whole request object using `cls.get(CLS_REQ)`.

#### Testing

Since the `ClsService` is just another injectable provider, you can mock it out entirely in unit tests.

However, in certain integration tests, you might still want to use the real `ClsService` implementation. In that case, wrap the context-aware piece of code with a call to `ClsService#run` or `ClsService#runWith`:

[[CODE:14]]

#### More information

Visit the [nestjs-cls GitHub page](https://github.com/Papooch/nestjs-cls) for the full API documentation and more code examples.
