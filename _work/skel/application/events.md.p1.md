### Events

The [Event Emitter](https://www.npmjs.com/package/@nestjs/event-emitter) package (`@nestjs/event-emitter`) provides an observer implementation that lets you subscribe to and listen for events that occur in your application. Events are a good way to decouple different parts of your application, since a single event can have multiple listeners that don't depend on each other.

`EventEmitterModule` internally uses the [eventemitter2](https://github.com/EventEmitter2/EventEmitter2) package.

#### Getting started

First, install the required package:

[[CODE:1]]

Once the installation is complete, import the `EventEmitterModule` into the root `AppModule` and call its `forRoot()` static method, as shown below:

[[CODE:2]]

The `.forRoot()` call initializes the event emitter and registers any declarative event listeners that exist within your app. Registration happens in the `onApplicationBootstrap` lifecycle hook, which ensures that all modules have loaded and declared their event listeners. The module is registered as a [global module](/modules#global-modules) by default, so you can inject the event emitter anywhere without importing `EventEmitterModule` again. To change this, set the `global` option to `false`.

To configure the underlying `EventEmitter2` instance, pass a configuration object to the `.forRoot()` method, as follows:

[[CODE:3]]

#### Dispatching events

To dispatch (i.e., fire) an event, first inject `EventEmitter2` through the constructor:

[[CODE:4]]

> info **Hint** Import `EventEmitter2` from the `@nestjs/event-emitter` package.

Then use it in the class as follows:

[[CODE:5]]

#### Listening to events

To declare an event listener, decorate the method that handles the event with the `@OnEvent()` decorator, as follows:

[[CODE:6]]

> info **Hint** If an event listener belongs to a [request-scoped](/fundamentals/injection-scopes) provider, Nest creates a new instance of that provider for every event it handles. The event payload takes the place of the request object, so injecting `REQUEST` in that provider gives you the payload. If the payload you emit is the incoming request object itself (or carries its context ID), set the `inheritRequestContextId` option of `forRoot()` to `true` so that the listener reuses that request's DI sub-tree instead of creating a new one.

The first argument can be a `string` or a `symbol` for a simple event emitter, and a `string | symbol | Array<string | symbol>` for a wildcard emitter.

The optional second argument is a listener options object:

[[CODE:7]]

> info **Hint** To learn more about the `OnOptions` object, see the [`eventemitter2` documentation](https://github.com/EventEmitter2/EventEmitter2#emitteronevent-listener-options-objectboolean).

For example, the following listener runs asynchronously:

[[CODE:8]]

To use namespaces and wildcards, pass the `wildcard` option to the `EventEmitterModule#forRoot()` method. When namespaces and wildcards are enabled, events can be either delimiter-separated strings (`foo.bar`) or arrays (`['foo', 'bar']`). You can configure the delimiter with the `delimiter` option. With namespaces enabled, you can subscribe to events using a wildcard:

[[CODE:9]]

A single wildcard matches exactly one segment. For example, `order.*` matches the events `order.created` and `order.shipped`, but not `order.delayed.out_of_stock`. To listen to such events, use the multi-level wildcard pattern (i.e., `**`), described in the [EventEmitter2 documentation on multi-level wildcards](https://github.com/EventEmitter2/EventEmitter2#multi-level-wildcards).

With this pattern, you can, for example, create an event listener that catches all events:

[[CODE:10]]

> info **Hint** The `EventEmitter2` class provides several useful methods for interacting with events, such as `waitFor()` and `onAny()`. See the [EventEmitter2 documentation](https://github.com/EventEmitter2/EventEmitter2) for details.

#### Listener priority

Pass `priority` in the `@OnEvent()` options to choose the order in which listeners of the same event are called. Nest collects every `@OnEvent` listener, sorts them by priority (highest first), and only then registers them. Listeners that omit `priority` use `0`: a positive priority runs before them, and a negative one after them. `Infinity` and `-Infinity` are allowed, and `NaN` falls back to `0`.

[[CODE:11]]

Listeners with `prependListener: true` stay ahead of the other `@OnEvent` listeners, as they do without a priority. Nest orders each of those two groups by priority on its own, so a prepended listener still runs before an appended one that has a higher priority. Listeners with the same priority keep the order they have without one: discovery order for appended listeners, and reverse discovery order for prepended ones.

Priority orders `@OnEvent` listeners of the same event name among themselves. It leaves listeners added directly on `EventEmitter2` in the position they were added. It also leaves a wildcard listener (`order.*`) and an exact one (`order.created`) in the order [EventEmitter2](https://github.com/EventEmitter2/EventEmitter2) calls them.

Priority only holds for listeners that start their work synchronously when the event is emitted:

- Listeners registered with `async: true`, `nextTick: true`, or `promisify: true` are deferred, so they run after every synchronous listener, whatever their priority. For example, `@OnEvent('order.created', {{ '{' }} priority: 10, async: true {{ '}' }})` still runs after `notifyWarehouse()` above.
- Listeners on [request-scoped](/fundamentals/injection-scopes) or durable providers resolve their instance before their body runs, so their body can start after lower-priority listeners. Priority does not hold for them.

Priority decides the order listeners are called in, not whether the next one runs. In every mode, including a plain `emit()`, a higher-priority listener that throws or rejects still leaves the listeners after it to run. A security check at a higher priority cannot rely on a thrown error to skip a later listener, such as `notifyWarehouse()` above.

#### Preventing event loss

Events emitted before or during the `onApplicationBootstrap` lifecycle hook (for example, from constructors or `onModuleInit()` methods) may be missed, because the listeners might not be registered yet.

To avoid this, use the `waitUntilReady()` method of `EventEmitterReadinessWatcher` (exported from `@nestjs/event-emitter`). It returns a promise that resolves once all listeners have been registered. Call it in the `onApplicationBootstrap` lifecycle hook of your provider before emitting events:

[[CODE:12]]

> info **Note** This is only necessary for events emitted before the `onApplicationBootstrap` lifecycle hook completes.

#### Example

A working example is available in the [event emitter sample](https://github.com/nestjs/nest/tree/master/sample/30-event-emitter).
