### Gateways

Most of the concepts discussed elsewhere in this documentation, such as dependency injection, decorators, exception filters, pipes, guards, and interceptors, apply equally to gateways. Wherever possible, Nest abstracts implementation details so that the same components can run across HTTP-based platforms, WebSockets, and microservices. This section covers the aspects of Nest that are specific to WebSockets.

In Nest, a gateway is a class annotated with the `@WebSocketGateway()` decorator. Gateways are platform-agnostic, so they work with any WebSockets library once an adapter exists for it. Nest supports two WebSocket platforms out of the box: [socket.io](https://github.com/socketio/socket.io) and [ws](https://github.com/websockets/ws). Choose the one that best suits your needs. You can also build your own adapter by following the [adapters guide](/websockets/adapter).

<figure><img class="illustrative-image" src="/assets/Gateways_1.png" /></figure>

> info **Hint** Gateways are [providers](/providers): they can inject dependencies through the class constructor, and other classes (providers and controllers) can inject them.

#### Installation

To start building WebSockets-based applications, first install the required package:

[[CODE:1]]

#### Overview

By default, each gateway listens on the same port as the **HTTP server**. To use a different port, pass it as the first argument to the decorator, e.g., `@WebSocketGateway(80)`, where `80` is the chosen port number. You can also set the [namespace](https://socket.io/docs/v4/namespaces/) used by the gateway:

[[CODE:2]]

> warning **Warning** Gateways are not instantiated until they are referenced in the providers array of an existing module.

The second argument of the `@WebSocketGateway()` decorator passes any supported [server option](https://socket.io/docs/v4/server-options/) to the socket server constructor. If you don't need a custom port, pass the options object as the only argument.

[[CODE:3]]

The gateway is now listening, but it doesn't subscribe to any incoming messages yet. Let's create a handler that subscribes to `events` messages and responds to the client with the same data.

[[CODE:4]]

> info **Hint** The `@SubscribeMessage()` and `@MessageBody()` decorators are imported from the `@nestjs/websockets` package.

Once the gateway is created, register it in a module.

[[CODE:5]]

You can also pass a property key to the `@MessageBody()` decorator to extract that property from the incoming message body:

[[CODE:6]]

If you prefer not to use decorators, the following code is functionally equivalent:

[[CODE:7]]

In the example above, the `handleEvent()` method takes two arguments. The first is a platform-specific [socket instance](https://socket.io/docs/v4/server-api/#socket), and the second is the data received from the client. This approach isn't recommended, because it requires mocking the `socket` instance in each unit test.

When the `events` message is received, the handler sends an acknowledgment with the same data that was sent over the network. You can also emit messages with a library-specific API, e.g., the `client.emit()` method. To access the connected socket instance, use the `@ConnectedSocket()` decorator.

[[CODE:8]]

> info **Hint** The `@ConnectedSocket()` decorator is imported from the `@nestjs/websockets` package.

However, messages you emit directly through the socket bypass interceptors, which only see the handler's return value. If you don't want to respond to the client, omit the `return` statement (or return `null` or `undefined`). Other falsy values, such as `false` or `0`, are still sent as a response.

When a client emits the message as follows, the `handleEvent()` method is executed:

[[CODE:9]]

To receive the response sent by the handler above, the client must attach a corresponding acknowledgment callback:

[[CODE:10]]

Returning a value from a message handler implicitly sends an acknowledgment, but advanced scenarios often require direct control over the acknowledgment callback.

The `@Ack()` parameter decorator injects the `ack` callback function directly into a message handler. When you use it, Nest doesn't send an acknowledgment based on the return value, so you must call `ack()` yourself. Without the decorator, the callback is passed as the third argument of the method.

[[CODE:11]]

#### Multiple responses

The acknowledgment is dispatched only once, and native WebSocket implementations don't support it. To work around these limitations, return an object with two properties: `event`, the name of the emitted event, and `data`, the payload to forward to the client.

[[CODE:12]]

> info **Hint** The `WsResponse` interface is imported from the `@nestjs/websockets` package.

> warning **Warning** If your `data` field relies on `ClassSerializerInterceptor`, return a class instance that implements `WsResponse`, because the interceptor ignores plain JavaScript object responses.

To receive the incoming response(s), the client must add another event listener.

[[CODE:13]]

#### Asynchronous responses

Message handlers can respond either synchronously or **asynchronously**, so `async` methods are supported. A message handler can also return an `Observable`, in which case each emitted value is sent to the client until the stream completes.

[[CODE:14]]

In the example above, the message handler responds **3 times** (once for each item in the array).

#### Lifecycle hooks

Gateways support three lifecycle hooks. Each has a corresponding interface, described in the following table:

<table>
  <tr>
    <td>
      <code>OnGatewayInit</code>
    </td>
    <td>
      Requires the <code>afterInit()</code> method, which receives the library-specific server instance as an argument.
    </td>
  </tr>
  <tr>
    <td>
      <code>OnGatewayConnection</code>
    </td>
    <td>
      Requires the <code>handleConnection()</code> method, which receives the library-specific client socket instance as
      its first argument.
    </td>
  </tr>
  <tr>
    <td>
      <code>OnGatewayDisconnect</code>
    </td>
    <td>
      Requires the <code>handleDisconnect()</code> method, which receives the library-specific client socket instance as
      its first argument.
    </td>
  </tr>
</table>

> info **Hint** Each lifecycle interface is exposed from the `@nestjs/websockets` package.

> warning **Warning** Nest doesn't wait for an async `handleConnection()` to finish before it handles the client's messages, so the hook isn't a gate: messages that arrive before it disconnects the client are still handled. To check each message, bind [guards](/websockets/guards) to the message handlers. To reject a client before any of its messages are handled, use connection-level middleware instead: socket.io's `server.use()` in `afterInit()`, or, with `WsAdapter`, a `verifyClient` function in the `@WebSocketGateway()` options.

#### Server and Namespace

Occasionally, you may need direct access to the native, **platform-specific** server instance. Nest passes it as an argument to the `afterInit()` method (`OnGatewayInit` interface). Alternatively, use the `@WebSocketServer()` decorator.

[[CODE:15]]

You can also retrieve the corresponding namespace:

[[CODE:16]]

The `@WebSocketServer()` decorator injects a server instance based on the metadata stored by the `@WebSocketGateway()` decorator. If you pass the `namespace` option to `@WebSocketGateway()`, `@WebSocketServer()` injects a `Namespace` instance instead of a `Server` instance.

> warning **Notice** The `@WebSocketServer()` decorator is imported from the `@nestjs/websockets` package.

Nest assigns the server instance to this property once it's ready to use.

<app-banner-enterprise></app-banner-enterprise>

#### Request-scoped gateways

Starting with NestJS v12, gateways support [request-scoped](/fundamentals/injection-scopes) providers. Nest creates a new instance of every request-scoped dependency per connected socket. That instance lives as long as the connection does, so it can safely hold per-connection state.

Inject the socket itself with the `REQUEST` token, the same way you inject the HTTP request into a request-scoped HTTP provider:

[[CODE:17]]

The gateway then injects it like any other provider:

[[CODE:18]]

Because the scope is tied to the connection rather than to a single message, the `sequence` counter above increments across every message received on that socket, while a second client gets its own independent instance. Nest tears the request-scoped instances down when the socket disconnects.

> warning **Notice** As with HTTP, request-scoped providers add per-connection instantiation overhead. Use the default singleton scope unless you need per-connection state.

#### Example

A working example is available in the [02-gateways sample](https://github.com/nestjs/nest/tree/master/sample/02-gateways).
