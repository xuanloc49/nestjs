### Pre-request hooks

Pre-request hooks are functions that run before all enhancers (guards, interceptors, and pipes) on every invocation of a pattern handler. They are the microservices equivalent of HTTP middleware: a place to establish per-request context that must be visible to guards and the rest of the pipeline.

> info **Hint** The `PreRequestHook` interface is exported from the `@nestjs/common` package.

Hooks run at the start of the following sequence:

[[CODE:1]]

Exceptions thrown inside a hook are caught by the same wrapper that covers the rest of the pipeline, so your existing [exception filters](/microservices/exception-filters) handle them without extra configuration.

#### Binding hooks

Register hooks on the microservice instance with the `registerPreRequestHook()` method, before the microservice is initialized (i.e., before calling `app.listen()` or `app.init()`). Hooks registered after initialization are ignored, and Nest logs a warning. Multiple calls accumulate hooks in registration order.

Each hook receives an `ExecutionContext` and a `next` function. Calling `next()` advances to the next hook or, when no hooks remain, to the guard → interceptor → pipe → handler pipeline. The hook must return an `Observable`: either the one produced by `next()`, or one that wraps it.

> warning **Warning** If a hook doesn't call `next()`, the handler never runs. This is the same contract as HTTP middleware.

> info **Note** In a [hybrid application](/faq/hybrid-application), `connectMicroservice()` initializes the connected microservice immediately (unless you pass `deferInitialization: true` in its second argument), so hooks registered on the returned instance afterward are not applied.

[[CODE:2]]

#### AsyncLocalStorage propagation

A common use case is initializing `AsyncLocalStorage` before guards run, which makes the store available throughout the entire pipeline:

[[CODE:3]]

Because the hook runs before the guards, `als.getStore()` returns the initialized store in any guard, interceptor, or handler:

[[CODE:4]]

#### Logging and metrics

You can apply RxJS operators to the `Observable` returned by `next()` to observe the full handler lifecycle:

[[CODE:5]]

> info **Hint** Pre-request hooks are global: you can't register them for individual patterns. When no hooks are registered, Nest skips the hook chain entirely, so the feature adds no overhead. Pre-request hooks don't apply to WebSocket gateways.
