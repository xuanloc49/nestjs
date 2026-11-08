### Exception filters

The only difference between the HTTP [exception filter](/exception-filters) layer and the corresponding microservices layer is that microservices should throw `RpcException` instead of `HttpException`.

[[CODE:1]]

> info **Hint** The `RpcException` class is imported from the `@nestjs/microservices` package.

Nest handles the thrown exception and returns an `error` object with the following structure:

[[CODE:2]]

If you pass an object to the `RpcException` constructor instead of a string, Nest returns that object as is.

> warning **Warning** An event handler has no response stream. An error that a filter rethrows for an `@EventPattern()` handler never reaches the producer, so handle the error inside the filter.

#### Filters

Microservice exception filters behave like HTTP exception filters, with one difference: the `catch()` method must return an `Observable`.

[[CODE:3]]

> warning **Warning** Global exception filters registered on the main HTTP application don't apply to microservices connected to a [hybrid application](/faq/hybrid-application) unless you set the `inheritAppConfig` option. See [sharing configuration](/faq/hybrid-application#sharing-configuration).

The following example uses a manually instantiated method-scoped filter. As with HTTP-based applications, you can also use controller-scoped filters (i.e., prefix the controller class with a `@UseFilters()` decorator).

[[CODE:4]]

#### Inheritance

Typically, you'll create fully customized exception filters tailored to your application's requirements. In some cases, however, you may want to extend the **core exception filter** and override its behavior based on certain factors.

To delegate exception processing to the base filter, extend `BaseRpcExceptionFilter` and call the inherited `catch()` method.

[[CODE:5]]

The above implementation is only a shell that demonstrates the approach. Your implementation of the extended exception filter would include your own **business logic** (e.g., handling various conditions).
