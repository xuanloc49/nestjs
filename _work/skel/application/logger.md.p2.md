#### Dependency injection

For more advanced logging functionality, take advantage of dependency injection. For example, you may want to inject a `ConfigService` into your logger to customize it, and in turn inject your custom logger into other controllers and/or providers. To enable dependency injection for your custom logger, create a class that implements `LoggerService` and register that class as a provider in a module. For example, you can:

1. Define a `MyLogger` class that either extends the built-in `ConsoleLogger` or completely overrides it, as shown in the previous sections. Be sure to implement the `LoggerService` interface.
2. Create a `LoggerModule` as shown below, and provide `MyLogger` from that module.

[[CODE:30]]

With this construct, your custom logger is available to any other module. Because your `MyLogger` class is part of a module, it can use dependency injection (for example, to inject a `ConfigService`). One more step is needed for Nest to use this custom logger for system logging (e.g., for bootstrapping and error handling).

Because application instantiation (`NestFactory.create()`) happens outside the context of any module, it doesn't participate in the normal dependency injection phase of initialization. So you must ensure that at least one application module imports the `LoggerModule`, which triggers Nest to instantiate a singleton instance of the `MyLogger` class.

You can then instruct Nest to use the same singleton instance of `MyLogger` with the following construction:

[[CODE:31]]

> info **Note** In the example above, `bufferLogs` is set to `true` so that all logs are held in a buffer until a custom logger (`MyLogger` in this case) is attached. With `autoFlushLogs` enabled (the default), Nest flushes the buffer on its own: an HTTP application (or microservice) flushes it when it starts listening in `app.listen()`, and a standalone [application context](/standalone-applications) flushes it when you call `app.useLogger()`. If initialization fails, Nest flushes it right away. When Nest can't create a provider (for example, because its factory throws), it falls back to the original `ConsoleLogger` to print the buffer and the error. When a lifecycle hook such as `onModuleInit()` rejects, Nest prints the buffer through the logger you attached (or through the original one, if none is attached yet) but doesn't log the error: the call that started initialization, such as `app.listen()`, rejects with it. Set `autoFlushLogs` to `false` to flush the buffer yourself with `app.flushLogs()` (or the static `Logger.flush()`).

Here, the `get()` method of the `NestApplication` instance retrieves the singleton instance of `MyLogger`. This technique is essentially a way to "inject" a logger instance for use by Nest. The `app.get()` call depends on that instance first being instantiated through a module import, as described above.

You can also inject this `MyLogger` provider into your feature classes, ensuring consistent logging behavior across both Nest system logging and application logging. See <a href="application/logger#using-the-logger-for-application-logging">Using the logger for application logging</a> and <a href="application/logger#injecting-a-custom-logger">Injecting a custom logger</a> below for more information.

> warning **Warning** If a provider factory or a lifecycle hook calls `process.exit()` itself (for example, after a failed connection check), or a startup step never settles (such as a connection that keeps retrying), nothing in the buffer is printed, not even when you stop the process with `Ctrl+C`. Throw an error instead, so that initialization fails and Nest flushes the buffer.

When startup logs must always be visible, even if the process exits or stalls, don't buffer them: pass a logger instance as the `logger` option of `NestFactory.create()`, as shown in [Custom implementation](#custom-implementation), so that Nest hands each line to it as soon as it is logged. That instance is created outside the dependency injection system, so it can't inject providers such as `ConfigService`.

#### Injecting a custom logger

To start, extend the built-in logger with code like the following. The `scope` option, supplied as configuration metadata for the `ConsoleLogger` subclass, specifies a [transient](/fundamentals/injection-scopes) scope so that each consumer gets its own logger instance. This is important because each module sets a unique context on its logger via `setContext()` — with a singleton, that call would overwrite the context across the entire app. In this example, we do not extend the individual `ConsoleLogger` methods (like `log()`, `warn()`, etc.), though you may choose to do so.

[[CODE:32]]

Next, create a `LoggerModule` with a construction like this:

[[CODE:33]]

Next, import the `LoggerModule` into your feature module. Because `MyLogger` extends `ConsoleLogger`, you can use its `setContext()` method and start using the context-aware custom logger, like this:

[[CODE:34]]

`MyLogger` inherits the rest of the `ConsoleLogger` API too: `resetContext()` restores the context passed to the constructor, and `isLevelEnabled('debug')` tells you whether a level is currently enabled, so you can skip preparing data for a line that would be discarded.

Finally, instruct Nest to use an instance of the custom logger in your `main.ts` file, as shown below. This example doesn't customize the logger behavior (by overriding `ConsoleLogger` methods like `log()`, `warn()`, etc.), so this step isn't strictly needed here. It **is** needed if you add custom logic to those methods and want Nest to use the same implementation.

[[CODE:35]]

> info **Hint** Alternatively, instead of setting `bufferLogs` to `true`, you could temporarily disable the logger with the `logger: false` option. Be aware that if you pass `logger: false` to `NestFactory.create()`, nothing is logged until you call `useLogger()`, so you may miss important initialization errors. If you don't mind some initial messages being logged with the default logger, omit the `logger: false` option.

#### Correlating logs with requests

Centralizing logs solves storage, not investigation. Once every instance ships to the same place, the hard part becomes reconstructing a *single* request out of thousands of interleaved lines. That is why so much production debugging is really the work of inventing a correlation id, threading it through every log call, and hoping nothing on the path forgot to pass it along.

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') removes that bookkeeping. Turn on `forwardLogs` and every line written through Nest's `Logger` is captured with the trace it was written in already attached:

[[CODE:36]]

You keep calling `this.logger.log()` with an `orderId` param exactly as before: no correlation id to generate, no context object to thread through your service layer. On an execution page, the logs for that one request are then placed on the trace's own clock, each line sitting next to the span that was in flight when it was written, so "the retry warning fired *before* the timeout, not after" is something you can see instead of infer from timestamps across three log streams.

Structured logging params carry through as well, so `orderId` stays a queryable field rather than being flattened into the message text. Log lines are also alertable in their own right, for example: "tell me when `payment declined` appears more than 10 times in 15 minutes".

If you would rather keep log content in your own aggregator, you do not have to forward anything. Even with `forwardLogs` off, the SDK augments `ConsoleLogger` so every line written during a request carries that request's trace id: at the end of the line in the default format (`   Trace ID: <id>`, after the message), and as a `traceId` field with [JSON logging](#json-logging) enabled:

[[CODE:37]]

That id is enough to jump from a line in your existing stack to the full trace in the dashboard. It is on by default and controlled by the `attachTraceIdToLogs` option (see [Trace correlation](/observability/sdk#trace-correlation)). Lines written outside a request (during bootstrap, for example) are left as they are. The augmentation applies to Nest's built-in `ConsoleLogger` only, so if you replace it with an [external logger](#use-external-logger), read the id yourself with `TracerService.currentTraceId()`. See the [SDK reference](/observability/sdk#logs) for forwarding and its redaction settings.

The trace id is not the only thing that lives for the length of a request. The SDK keeps an `AsyncLocalStorage` store for every request, job, and message it instruments, and `TracerService` exposes it through `setAttribute()` and `getAttribute()`. That is the natural place for the user or tenant a request is acting for, readable from anywhere downstream without threading it through every call. See [Request-scoped attributes](/observability/manual-instrumentation#request-scoped-attributes), and the [Async local storage](/recipes/async-local-storage) recipe for how it compares to a store you set up yourself.

#### Use external logger

As [Logging in production](#logging-in-production) shows, the built-in logger already covers structured, centralized logging for most applications. Some requirements still call for a dedicated library such as [Pino](https://github.com/pinojs/pino) or [Winston](https://github.com/winstonjs/winston): multiple in-process transports (files, syslog, HTTP), redaction of sensitive fields, custom serializers, or the lowest possible overhead on services that log at very high volume. As with any standard Node.js application, you can take full advantage of such modules in Nest: implement the `LoggerService` interface as described in [Custom implementation](#custom-implementation), or use a community integration.
