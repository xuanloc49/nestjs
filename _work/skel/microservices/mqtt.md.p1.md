### MQTT

[MQTT](https://mqtt.org/) (Message Queuing Telemetry Transport) is an open source, lightweight messaging protocol optimized for low latency. It provides a scalable and cost-efficient way to connect devices using a **publish/subscribe** model. A communication system built on MQTT consists of the publishing server, a broker, and one or more clients. The protocol is designed for constrained devices and for low-bandwidth, high-latency, or unreliable networks.

#### Installation

To start building MQTT-based microservices, first install the required package:

[[CODE:1]]

#### Overview

To use the MQTT transporter, pass the following options object to the `createMicroservice()` method:

[[CODE:2]]

> info **Hint** The `Transport` enum is imported from the `@nestjs/microservices` package.

#### Options

The `options` object is specific to the chosen transporter. The <strong>MQTT</strong> transporter exposes the [MQTT.js client options](https://github.com/mqttjs/MQTT.js/#mqttclientstreambuilder-options), as well as the `url`, `subscribeOptions` (see [Quality of Service](#quality-of-service-qos)), and `userProperties` (see [record builders](#record-builders)) properties. On the server, the `maxConnectionAttempts` property limits the number of attempts to establish the initial connection (default: `-1`, i.e., unlimited). The limit doesn't apply to reconnections after the server has connected.

#### Client

As with other microservice transporters, you have <a href="/microservices/basics#client-producer-class">several options</a> for creating an MQTT `ClientProxy` instance.

One way to create an instance is to use the `ClientsModule`. Import it and use its `register()` method to pass an options object with the same properties shown above for the `createMicroservice()` method, plus a `name` property to use as the injection token. Read more about the `ClientsModule` in the <a href="/microservices/basics#client-producer-class">client section of the overview</a>.

[[CODE:3]]

You can also create a client with `ClientProxyFactory` or the `@Client()` decorator. Both are described in the <a href="/microservices/basics#client-producer-class">client section of the overview</a>.

#### Context

In more complex scenarios, you may need additional information about the incoming request. With the MQTT transporter, you can access the `MqttContext` object.

[[CODE:4]]

> info **Hint** `@Payload()`, `@Ctx()` and `MqttContext` are imported from the `@nestjs/microservices` package.

To access the original MQTT [packet](https://github.com/mqttjs/mqtt-packet), use the `getPacket()` method of the `MqttContext` object:

[[CODE:5]]

#### Wildcards

A subscription can target an explicit topic, or it can include wildcards. Two wildcards are available: `+` matches a single topic level, and `#` matches multiple topic levels.

[[CODE:6]]

#### Quality of Service (QoS)

By default, subscriptions created with the `@MessagePattern()` and `@EventPattern()` decorators use QoS 0. If you need a higher QoS, set it globally with the `subscribeOptions` block when establishing the connection:

[[CODE:7]]

#### Per-pattern QoS

You can override the subscription QoS for an individual pattern by passing a `qos` property in the extras object, the second argument of the `@MessagePattern()` or `@EventPattern()` decorator. Patterns without their own `qos` use the global `subscribeOptions.qos` value.

[[CODE:8]]

#### Record builders

To configure message options (adjust the QoS level, set the Retain or DUP flags, or add properties to the payload), use the `MqttRecordBuilder` class. For example, the following record sets QoS to `1` with the `setQoS()` method and adds a user property with the `setProperties()` method:

[[CODE:9]]

> info **Hint** The `MqttRecordBuilder` class is exported from the `@nestjs/microservices` package.

On the server side, you can read these options through the `MqttContext`:

[[CODE:10]]

To configure user properties for all requests sent by a client, pass them as options to the `ClientProxyFactory`:

[[CODE:11]]

Starting with NestJS v12.1.3, a message handler can also return a record. Nest sends the record data as the reply and applies the record options (for example, the QoS level and the properties) to the reply message:

[[CODE:12]]

#### Instance status updates

To get real-time updates on the connection and the state of the underlying driver instance, subscribe to the `status` stream. This stream provides status updates specific to the chosen driver. For the MQTT driver, the `status` stream emits `connected`, `disconnected`, `reconnecting`, and `closed` events.

[[CODE:13]]

> info **Hint** The `MqttStatus` type is imported from the `@nestjs/microservices` package.

Similarly, you can subscribe to the server's `status` stream to receive notifications about the server's status.

[[CODE:14]]

#### Listening to MQTT events

In some cases, you might want to listen to internal events emitted by the microservice. For example, you could listen for the `error` event to trigger additional operations when an error occurs. To do this, use the `on()` method, as shown below:

[[CODE:15]]

Similarly, you can listen to the server's internal events:

[[CODE:16]]

> info **Hint** The `MqttEvents` type is imported from the `@nestjs/microservices` package.

Starting with NestJS v12.1.2, listeners registered with the client's `on()` method stay registered until you call `close()`, so they are also attached to the new MQTT client created on the next `send()` or `emit()` call after the previous one closed without reconnecting (for example, when `reconnectPeriod` is `0`). Registrations are not deduplicated, so register each listener once rather than again from its callback or after each reconnect.

#### Underlying driver access

For more advanced use cases, you may need to access the underlying driver instance, for example, to close the connection manually or to use driver-specific methods. In most cases, however, you **shouldn't need** to access the driver directly.

To do so, use the `unwrap()` method, which returns the underlying driver instance. The generic type parameter specifies the type of driver instance you expect.

[[CODE:17]]

Similarly, you can access the server's underlying driver instance:

[[CODE:18]]
