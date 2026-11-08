### Adapters

The WebSockets module is platform-agnostic, so you can bring your own library (or even a native implementation) by implementing the `WebSocketAdapter` interface. The interface requires the methods described in the following table:

<table>
  <tr>
    <td><code>create</code></td>
    <td>Creates a socket server instance based on the passed arguments</td>
  </tr>
  <tr>
    <td><code>bindClientConnect</code></td>
    <td>Binds the client connection event</td>
  </tr>
  <tr>
    <td><code>bindClientDisconnect</code></td>
    <td>Binds the client disconnection event (optional)</td>
  </tr>
  <tr>
    <td><code>bindMessageHandlers</code></td>
    <td>Binds the incoming message to the corresponding message handler</td>
  </tr>
  <tr>
    <td><code>close</code></td>
    <td>Terminates a server instance</td>
  </tr>
</table>

#### Extend socket.io

The [socket.io](https://github.com/socketio/socket.io) package is wrapped in an `IoAdapter` class. You can extend this class to enhance the adapter's basic functionality. For example, suppose your application must broadcast events across multiple load-balanced instances of your web service. To support this, extend `IoAdapter` and override the single method responsible for instantiating new socket.io servers. First, install the required packages.

> warning **Warning** To use socket.io with multiple load-balanced instances, you must either disable polling by setting `transports: ['websocket']` in your clients' socket.io configuration, or enable cookie-based routing (sticky sessions) in your load balancer. Redis alone is not enough. See [Enabling sticky session](https://socket.io/docs/v4/using-multiple-nodes/#enabling-sticky-session) in the socket.io documentation for more information.

[[CODE:1]]

Once the packages are installed, create a `RedisIoAdapter` class.

[[CODE:2]]

Then switch to your newly created Redis adapter.

[[CODE:3]]

#### Ws library

Another available adapter is `WsAdapter`, which acts as a proxy between the framework and the fast, thoroughly tested [ws](https://github.com/websockets/ws) library. This adapter is fully compatible with native browser WebSockets and is faster than the socket.io package. However, it offers significantly fewer features out of the box, which many applications don't need.

> info **Hint** The `ws` library doesn't support namespaces (communication channels popularized by `socket.io`), and `WsAdapter` throws an error if you set the `namespace` option. To mimic this feature, mount multiple `ws` servers on different paths (e.g., `@WebSocketGateway({{ '{' }} path: '/users' {{ '}' }})`).

To use `ws`, first install the required package:

[[CODE:4]]

Once the package is installed, switch the adapter:

[[CODE:5]]

> info **Hint** The `WsAdapter` is imported from `@nestjs/platform-ws`.

The `WsAdapter` handles messages in the `{{ '{' }} event: string, data: any {{ '}' }}` format. To receive and process messages in a different format, configure a message parser that converts them into this format.

[[CODE:6]]

Alternatively, you can set the message parser after creating the adapter with the `setMessageParser()` method.

#### Advanced (custom adapter)

For demonstration purposes, we'll integrate the [ws](https://github.com/websockets/ws) library manually. As mentioned, an adapter for this library already exists: the `WsAdapter` class exposed from the `@nestjs/platform-ws` package. A simplified implementation could look like this:

[[CODE:7]]

> info **Hint** To use the [ws](https://github.com/websockets/ws) library, use the built-in `WsAdapter` instead of creating your own.

Then set up the custom adapter with the `useWebSocketAdapter()` method:

[[CODE:8]]

#### Example

A working example that uses `WsAdapter` is available in the [16-gateways-ws sample](https://github.com/nestjs/nest/tree/master/sample/16-gateways-ws).
