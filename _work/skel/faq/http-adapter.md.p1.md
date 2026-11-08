### HTTP adapter

Occasionally, you may need to access the underlying HTTP server, either from within the Nest application context or from outside of it.

Every native (platform-specific) HTTP server or library instance (e.g., Express or Fastify) is wrapped in an **adapter**. The adapter is registered as a globally available provider, so you can retrieve it from the application context or inject it into other providers.

#### Outside application context strategy

To get a reference to the `HttpAdapter` from outside of the application context, call the `getHttpAdapter()` method:

[[CODE:1]]

#### As injectable

To get a reference to the `HttpAdapterHost` from within the application context, inject it like any other provider (e.g., using constructor injection):

[[CODE:2]]

> info **Hint** The `HttpAdapterHost` is imported from the `@nestjs/core` package.

The `HttpAdapterHost` is **not** an actual `HttpAdapter`. To get the actual `HttpAdapter` instance, read its `httpAdapter` property:

[[CODE:3]]

The `httpAdapter` is the HTTP adapter instance that wraps the underlying framework. It is an instance of `ExpressAdapter`, `FastifyAdapter`, or `NodeAdapter` (all of them extend `AbstractHttpAdapter`).

The adapter object exposes several methods for interacting with the HTTP server. To access the library instance (e.g., the Express instance) directly, call the `getInstance()` method:

[[CODE:4]]

#### Listening event

To run code when the server starts listening for incoming requests, subscribe to the `listen$` stream:

[[CODE:5]]

The `HttpAdapterHost` also exposes a `listening` boolean property that indicates whether the server is currently listening:

[[CODE:6]]
