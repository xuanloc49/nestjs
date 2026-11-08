### Hybrid application

A hybrid application listens for requests from two or more different sources. It can combine an HTTP server with a microservice listener, or combine several different microservice listeners. The `createMicroservice()` method doesn't support multiple servers, so in this case you create and start each microservice manually. To do this, connect `INestMicroservice` instances to the `INestApplication` instance with the `connectMicroservice()` method.

[[CODE:1]]

> info **Hint** The `app.listen(port)` method starts an HTTP server on the specified port. If your application doesn't handle HTTP requests, use the `app.init()` method instead.

> warning **Notice** The order of these calls matters. With `await app.startAllMicroservices()` first (as above), the microservices begin consuming messages **before** the application's lifecycle hooks (such as `onModuleInit` and `onApplicationBootstrap`) have completed. Call `app.listen()` (or `app.init()`) before `startAllMicroservices()` if your handlers must not receive messages until every module has fully initialized.

To connect multiple microservice instances, call `connectMicroservice()` once for each microservice:

[[CODE:2]]

In a hybrid application with multiple microservices, you can bind `@MessagePattern()` to a single transport strategy (for example, NATS) by passing a second argument that identifies the transport. For the built-in strategies, this is a value of the `Transport` enum; for a [custom transporter](/microservices/custom-transport), it is the `transportId` symbol of its server class.

[[CODE:3]]

> info **Hint** `@Payload()`, `@Ctx()`, `Transport` and `NatsContext` are imported from `@nestjs/microservices`. `XYZServer.Transport` here stands for the `transportId` symbol exposed by the custom transporter.

#### Sharing configuration

By default, connected microservices don't inherit the global pipes, interceptors, guards, and filters configured for the main (HTTP-based) application. This applies both to enhancers registered with the `useGlobal*()` methods and to those registered as providers with the `APP_PIPE`, `APP_INTERCEPTOR`, `APP_GUARD`, and `APP_FILTER` tokens.
To inherit this configuration, set the `inheritAppConfig` property in the options object passed as the second argument of `connectMicroservice()`:

[[CODE:4]]

> info **Hint** A connected microservice registers its message handlers as soon as `connectMicroservice()` is called. When you use `inheritAppConfig`, call `app.useGlobalPipes()`, `app.useGlobalGuards()`, and the other `useGlobal*()` methods **before** `connectMicroservice()`, otherwise the enhancers they register won't apply to the microservice's handlers.
