### Exception filters

The WebSockets exceptions layer works like the HTTP [exception filter](/exception-filters) layer, with one difference: instead of throwing `HttpException`, throw `WsException`.

[[CODE:1]]

> info **Hint** The `WsException` class is imported from the `@nestjs/websockets` package.

When a handler throws the exception above, Nest catches it and emits an `exception` message to the client with the following structure:

[[CODE:2]]

The `cause` property lets the client associate the error with the message that triggered it. If you pass an object (rather than a string) to the `WsException` constructor, Nest emits that object as is. Any exception that isn't a `WsException` produces the same structure, with `'Internal server error'` as the message. With the `ws` adapter, which has no named events, the client receives a JSON string of the form `{{ '{' }} "event": "exception", "data": ... {{ '}' }}` instead.

#### Filters

WebSocket exception filters behave the same way as HTTP exception filters. The following example uses a manually instantiated method-scoped filter. As with HTTP-based applications, you can also use gateway-scoped filters (i.e., decorate the gateway class with `@UseFilters()`).

[[CODE:3]]

> warning **Warning** Global exception filters (registered with `app.useGlobalFilters()` or the `APP_FILTER` token) don't apply to gateways. Bind WebSocket exception filters at the gateway or method level with `@UseFilters()`.

#### Inheritance

Typically, you'll create fully customized exception filters tailored to your application requirements. However, sometimes you may want to extend the **core exception filter** and override its behavior based on certain factors.

To delegate exception processing to the base filter, extend `BaseWsExceptionFilter` and call the inherited `catch()` method.

[[CODE:4]]

The implementation above is only a shell that demonstrates the approach. A real extended exception filter would add your own **business logic** (e.g., handling various conditions).

The `BaseWsExceptionFilter` constructor accepts an options object. Set `includeCause` to `false` to omit the `cause` property from error messages, or pass a `causeFactory(pattern, data)` function to control its shape.
