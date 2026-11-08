### Logger

Nest comes with a built-in logger that is used during application bootstrapping and in several other circumstances, such as displaying caught exceptions (i.e., system logging). This functionality is provided by the `Logger` class in the `@nestjs/common` package. You can fully control the behavior of the logging system, including any of the following:

- disable logging entirely
- specify the level of detail (e.g., display errors, warnings, debug information, etc.)
- configure the formatting of log messages (raw, JSON, colorized, etc.)
- override the timestamp in the default logger (e.g., use the ISO 8601 standard as the date format)
- completely override the default logger
- customize the default logger by extending it
- use dependency injection to simplify composing and testing your application

You can also use the built-in logger, or create your own custom implementation, to log your own application-level events and messages.

The built-in logger is not only a development convenience. Combined with [JSON output](#json-logging), [structured logging params](#structured-logging-params), and the trace id that [NestJS Observe](#correlating-logs-with-requests) attaches to every line written during a request, it covers what most production applications need from a logger: one machine-readable record per line on stdout, queryable fields, log levels, and a way to tie each line back to the request that wrote it. Container platforms and log aggregators (CloudWatch, Cloud Logging, Datadog, Loki, Elasticsearch, and so on) ingest that output as-is, with no extra dependency in your application. The [Logging in production](#logging-in-production) section below shows the full setup.

Reach for a dedicated library such as [Pino](https://github.com/pinojs/pino) or [Winston](https://github.com/winstonjs/winston) when you need something the built-in logger deliberately leaves out: writing to files or other transports from inside the process, field redaction, or the last bit of throughput on very log-heavy services. See [Use external logger](#use-external-logger).

#### Basic customization

To disable logging, set the `logger` property to `false` in the (optional) Nest application options object, passed as the second argument to the `NestFactory.create()` method.

[[CODE:1]]

To enable specific log levels, set the `logger` property to an array of strings specifying the log levels to display, as follows:

[[CODE:2]]

Values in the array can be any combination of `'log'`, `'fatal'`, `'error'`, `'warn'`, `'debug'`, and `'verbose'`.

> info **Hint** Log levels cascade from the most severe level in the array: every level at least as severe as that one is enabled too. `['log']` therefore also enables `'warn'`, `'error'`, and `'fatal'`. Less severe levels are enabled only if they are listed, so `['debug', 'error']` enables `'debug'`, `'error'`, and `'fatal'`, but not `'log'` or `'warn'`.

To enable a level and everything more severe than it, build the array with `filterLogLevels()` instead of listing the levels by hand. It takes a string, which makes it a good fit for an environment variable:

[[CODE:3]]

Besides `'>=warn'`, it accepts `'>warn'` (more severe than `warn` only), a comma-separated list such as `'log,error'`, or a single level. An empty or unrecognized string returns all levels, and an unknown level after `>` or `>=` throws.

To change the levels after the application has been created (for example, once your configuration has loaded), pass an array of levels to `app.useLogger()`. Nest hands it to the current logger's `setLogLevels()` method:

[[CODE:4]]

To disable colorized output, pass a `ConsoleLogger` instance with the `colors` property set to `false` as the value of the `logger` property:

[[CODE:5]]

Colors are also off by default when the `NO_COLOR` environment variable is set to any non-empty value.

To configure a prefix for each log message, pass a `ConsoleLogger` instance with the `prefix` property set:

[[CODE:6]]

The following table lists all available options:

| Option            | Description                                                                                                                                                                                                                                                                                                                                          | Default                                        |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `logLevels`       | Enabled log levels.                                                                                                                                                                                                                                                                                                                                  | `['log', 'fatal', 'error', 'warn', 'debug', 'verbose']` |
| `timestamp`       | If enabled, will print timestamp (time difference) between current and previous log message. Note: This option is not used when `json` is enabled.                                                                                                                                                                                                   | `false`                                        |
| `prefix`          | A prefix to be used for each log message. Note: This option is not used when `json` is enabled.                                                                                                                                                                                                                                                      | `Nest`                                         |
| `json`            | If enabled, will print the log message in JSON format.                                                                                                                                                                                                                                                                                               | `false`                                        |
| `colors`          | If enabled, will print the log message in color.                                                                                                                                                                                                                                                                                                     | `true` (`false` if `json` is enabled or `NO_COLOR` is set) |
| `context`         | The context of the logger.                                                                                                                                                                                                                                                                                                                           | `undefined`                                    |
| `forceConsole`    | If enabled, will use `console.log`/`console.error` instead of `process.stdout.write`/`process.stderr.write`. Useful in test environments, such as Jest, that buffer console calls.                                                                                                                                                                     | `false`                                        |
| `compact`         | If enabled, will print the log message in a single line, even if it is an object with multiple properties. If set to a number, the most n inner elements are united on a single line as long as all properties fit into breakLength. Short array elements are also grouped together.                                                                 | `false` (`true` if `json` is enabled)          |
| `maxArrayLength`  | Specifies the maximum number of Array, TypedArray, Map, Set, WeakMap, and WeakSet elements to include when formatting. Set to null or Infinity to show all elements. Set to 0 or negative to show no elements. Ignored when `json` is enabled, colors are disabled, and `compact` is set to true as it produces a parseable JSON output.             | `100`                                          |
| `maxStringLength` | Specifies the maximum number of characters to include when formatting. Set to null or Infinity to show all elements. Set to 0 or negative to show no characters. Ignored when `json` is enabled, colors are disabled, and `compact` is set to true as it produces a parseable JSON output.                                                           | `10000`                                        |
| `sorted`          | If enabled, will sort keys while formatting objects. Can also be a custom sorting function. Ignored when `json` is enabled, colors are disabled, and `compact` is set to true as it produces a parseable JSON output.                                                                                                                                | `false`                                        |
| `depth`           | Specifies the number of times to recurse while formatting object. This is useful for inspecting large objects. To recurse up to the maximum call stack size pass Infinity or null. Ignored when `json` is enabled, colors are disabled, and `compact` is set to true as it produces a parseable JSON output.                                         | `5`                                            |
| `showHidden`      | If true, object's non-enumerable symbols and properties are included in the formatted result. WeakMap and WeakSet entries are also included as well as user defined prototype properties                                                                                                                                                             | `false`                                        |
| `breakLength`     | The length at which input values are split across multiple lines. Set to Infinity to format the input as a single line (in combination with "compact" set to true). Ignored when `json` is enabled, colors are disabled, and `compact` is set to true as it produces a parseable JSON output.                                                       | `Infinity` when `compact` is enabled, or when colors are off and `compact` isn't explicitly `false`; `80` otherwise |

#### JSON logging

JSON logging is essential for application observability and for integration with log management systems. To enable it, create a `ConsoleLogger` instance with its `json` property set to `true`, and pass it as the value of the `logger` property when creating the application instance:

[[CODE:7]]

This configuration outputs logs in a structured JSON format, which makes it easier to integrate with external systems such as log aggregators and cloud platforms. For example, platforms like **AWS ECS** (Elastic Container Service) natively support JSON logs, enabling features like:

- **Log filtering**: narrow down logs based on fields like log level, timestamp, or custom metadata.
- **Search and analysis**: use query tools to analyze and track trends in your application's behavior.

If you're using [NestJS Mau](https://mau.nestjs.com), JSON logging also lets you view logs in a well-organized, structured format, which is especially useful for debugging and performance monitoring.

> info **Note** When `json` is set to `true`, the `ConsoleLogger` defaults `colors` to `false` and `compact` to `true`. With those two values, each entry is serialized with `JSON.stringify()`, so the output is valid JSON, free of formatting artifacts. For development, you can explicitly set `colors` to `true` (or `compact` to `false`). Entries are then rendered with Node's `util.inspect()`, which is easier to read during local debugging but is no longer strict JSON.

When JSON logging is enabled, the log output looks like this (on a single line):

[[CODE:8]]

Each entry has the following fields:

- `level`: the log level.
- `pid`: the process id.
- `timestamp`: when the entry was written, in milliseconds since the Unix epoch. The `timestamp` and `prefix` options, and a [custom timestamp format](#extend-built-in-logger), apply to text output only.
- `message`: the message, as passed to the logger.
- `context`: the logger context, when there is one.
- `stack`: the stack trace passed to `error()`, when there is one.
- `params`: the [structured logging params](#structured-logging-params), when any were passed.

As in text mode, `error` entries are written to stderr and all other levels to stdout.

#### Structured logging params

Log messages often need to carry metadata: a user id, a request duration, a correlation id. Starting with NestJS v12, plain objects passed **after** the first message argument are treated as structured params and attached to the same log entry instead of being emitted as separate log records.

[[CODE:9]]

In text mode, the params are appended inline to the same formatted line:

[[CODE:10]]

When several plain objects are passed, they are merged into a single set of params:

[[CODE:11]]

[[CODE:12]]

In JSON mode, params are nested under a `params` key by default:

[[CODE:13]]

To spread them into the root of the JSON object instead (which some log aggregators prefer), enable `flattenParams`:

[[CODE:14]]

[[CODE:15]]

The relevant `ConsoleLogger` options are:

| Option             | Description                                                                                                   | Default |
| ------------------ | ------------------------------------------------------------------------------------------------------------- | ------- |
| `structuredParams` | If enabled, plain objects logged after the message are attached to the same entry as params.                  | `true`  |
| `flattenParams`    | If enabled, params are spread into the root of the JSON record instead of nested under `params`. A param whose key the record already uses (such as `message` or `level`) is dropped. JSON mode only; requires `structuredParams`. | `false` |

> info **Hint** Only **plain objects** are treated as params. Arrays, strings, numbers, class instances, and `null` are still logged as separate messages (a string passed as the *last* argument is still treated as the context), and a plain object passed as the *first* argument is still treated as the message itself. Set `structuredParams: false` to restore the pre-v12 behavior.

#### Logging in production

Put together, JSON output and structured params give you production-grade logs from the built-in logger alone:

[[CODE:16]]

[[CODE:17]]

With [NestJS Observe](#correlating-logs-with-requests) installed, each line written during a request also carries that request's trace id, without changing a single log call:

[[CODE:18]]

That single line is filterable by level and context, queryable by `orderId`, and joinable to every other line from the same request, which is the job most teams install a third-party logger to do. Write logs to stdout like this and let the platform (Docker, Kubernetes, ECS, Cloud Run, and so on) collect and ship them. That keeps rotation, buffering, and delivery out of your application process.

> info **Hint** Set `flattenParams: true` if your aggregator indexes top-level fields only, so `orderId` becomes a root-level field instead of `params.orderId`.

#### Using the logger for application logging

You can combine several of the techniques above to provide consistent behavior and formatting across both Nest system logging and your own application event/message logging.

A good practice is to instantiate the `Logger` class from `@nestjs/common` in each of your services, supplying the service name as the `context` argument of the `Logger` constructor:

[[CODE:19]]

In the default logger implementation, `context` is printed in square brackets, like `NestFactory` in the example below:

[[CODE:20]]

If a message is expensive to build, pass a function that returns it instead. In the default text format, the built-in `ConsoleLogger` calls the function only when the level is enabled, so a disabled `debug` line costs nothing:

[[CODE:21]]

If you supply a custom logger via `app.useLogger()`, Nest uses it internally, and calls made through `Logger` instances are delegated to it. Your code remains implementation agnostic, and you can substitute the default logger with your own by calling `app.useLogger()`.

For example, if you follow the steps in the <a href="application/logger#dependency-injection">Dependency injection</a> section below and call `app.useLogger(app.get(MyLogger))`, subsequent calls to `this.logger.log()` from `MyService` result in calls to the `log()` method of the `MyLogger` instance.

This is suitable for most cases. If you need more customization (like adding and calling custom methods), see the <a href="application/logger#injecting-a-custom-logger">Injecting a custom logger</a> section.

#### Logs with timestamps

To print a timestamp difference for every logged message, pass the optional `timestamp: true` setting when creating the logger instance:

[[CODE:22]]

This will produce output in the following format:

[[CODE:23]]

Note the `+5ms` at the end of the line. It is the time elapsed since the previous line written by any `ConsoleLogger` in the process, not only by this logger.

#### Custom implementation

You can provide a custom logger implementation for Nest to use for system logging by setting the `logger` property to an object that fulfills the `LoggerService` interface. For example, you can tell Nest to use the global JavaScript `console` object (which implements the `LoggerService` interface), as follows:

[[CODE:24]]

To implement your own custom logger, implement each of the methods of the `LoggerService` interface, as shown below:

[[CODE:25]]

You can then supply an instance of `MyLogger` via the `logger` property of the Nest application options object:

[[CODE:26]]

This technique, while simple, doesn't use dependency injection for the `MyLogger` class. This can pose challenges, particularly for testing, and limits the reusability of `MyLogger`. For a better solution, see the <a href="application/logger#dependency-injection">Dependency injection</a> section below.

#### Extend built-in logger

Rather than writing a logger from scratch, you may be able to meet your needs by extending the built-in `ConsoleLogger` class and overriding selected behavior of the default implementation:

[[CODE:27]]

The same approach changes the timestamp format. For example, to print ISO 8601 timestamps instead of the locale-formatted date, override the protected `getTimestamp()` method:

[[CODE:28]]

[[CODE:29]]

This applies to text output only. With [JSON logging](#json-logging), the `timestamp` field is always milliseconds since the Unix epoch.

You can use such an extended logger in your feature modules as described in the <a href="application/logger#using-the-logger-for-application-logging">Using the logger for application logging</a> section above.

You can tell Nest to use your extended logger for system logging by passing an instance of it via the `logger` property of the application options object (as shown in the <a href="application/logger#custom-implementation">Custom implementation</a> section above), or by using the technique shown in the <a href="application/logger#dependency-injection">Dependency injection</a> section below. If you do so, call `super`, as shown in the sample code above, to delegate the log method call to the parent (built-in) class so that Nest can rely on the built-in features it expects.

<app-banner-courses></app-banner-courses>
