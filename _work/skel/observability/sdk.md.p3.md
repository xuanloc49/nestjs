#### Shaping what is recorded

These options enrich what the SDK records (who a request was for, what it concerned) and keep out what you don't need.

##### Associating users with telemetry

`getUserId` reads the incoming request and returns whatever identifier your system uses for a person: a user id, an account id, or a tenant-scoped id. Set it once and the **Users** view populates automatically:

[[CODE:19]]

The same option exists on `rpc` (receiving the transport id and the `BaseRpcContext`), `grpc` (receiving the call object), `graphql` (receiving the GraphQL context, for operations with no enclosing HTTP request), and `ws` (receiving the gateway message), each reading the transport's own context instead of an HTTP request. Reporting a user identifier is optional: traffic without one still shows up everywhere except the per-user views. The dashboard treats the identifier as an opaque string and never tries to resolve it into a name or an email, so prefer an opaque internal id over anything personally identifying.

##### Tags and custom attributes

`http`, `rpc`, `grpc`, `graphql`, and `jobs` each accept the same two options for attaching your own data to every request they cover:

| Option          | Applies                                                       | Description                                                                                              |
| --------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `tags`          | The same static `Record<string, string>` to every request     | Sent to Observe. For constants that don't vary per call, e.g., `project`, `env`, `region`.               |
| `setAttributes` | A function of the request/call/job, returning key-value pairs | Kept in your application. For per-call context your code reads later, e.g., a tenant id, a feature flag. |

[[CODE:20]]

`tags` appear as tags on the resulting request or job, and are searchable and visible on its detail page.

`setAttributes` values are **not sent to Observe** and don't appear in the dashboard. As each call starts, they're written to its [request-scoped attributes](/observability/manual-instrumentation#request-scoped-attributes), the same as calling `setAttribute()` for each key yourself, so any code handling that call can read them with `getAttribute()`. The function receives whatever the transport has: the request for `http`, the transport id and `BaseRpcContext` for `rpc`, the call object for `grpc`, the resolve info and GraphQL context for `graphql`, and `{{ '{' }} queueName, name, id {{ '}' }}` for `jobs`.

To see a per-call value in the dashboard, add it as a tag on a span with `TracerService` (see [Manual instrumentation](/observability/manual-instrumentation)):

[[CODE:21]]

> info **Hint** A GraphQL server is usually an HTTP endpoint, so its requests are already subject to the `http` options: `http.ignore` drops a request before the GraphQL layer sees it, and `http.getUserId` supplies the user for queries over HTTP. The `graphql` block tunes what happens _inside_ a request that was let through, per operation rather than per resolver, and `graphql.getUserId` is only consulted for operations that aren't already inside an HTTP trace, such as subscriptions over a WebSocket.

##### Ignoring noisy operations

Every inbound transport block (`http`, `rpc`, `grpc`, `graphql`, and `ws`) has an `ignore` option that skips instrumentation entirely for matching calls, such as a health check endpoint, an internal probe, or anything else not worth a trace:

[[CODE:22]]

`http.ignore` accepts an array of paths, `{{ '{' }} method, path {{ '}' }}` pairs (`path` can be a string or a `RegExp`), and plain `RegExp`s or a single predicate function over the request. `rpc.ignore`, `grpc.ignore`, and `graphql.ignore` are predicates over the transport's own context (the `@nestjs/microservices` transport id and `BaseRpcContext`, the gRPC call object, and the GraphQL resolve info respectively). Matching a GraphQL field name skips the whole operation that field leads, not only that field: an operation is measured end to end, so it is either traced or not.

`ignore` stops telemetry from being generated at all. The dashboard's spend-control drop filters are a different tool: they discard already-generated events at ingestion to reduce billed volume. Use `ignore` when you don't want a trace to exist, and drop filters when you want to tune cost on data the SDK is already producing.

`http` additionally takes `queryParamsObfuscateRegex`, a `RegExp` that masks sensitive query string values before they're sent. It is applied on top of the built-in redaction, which always masks well-known sensitive parameters (`token`, `password`, `code`, `signature`, and so on).

##### Trace sampling and batching

[[CODE:23]]

| Option              | Type                                                                       | Default | Description                                                                                               |
| ------------------- | -------------------------------------------------------------------------- | ------- | --------------------------------------------------------------------------------------------------------- |
| `tracesSampleRate`  | `number \| ((protocol: 'http' \| 'rpc' \| 'grpc' \| 'graphql' \| 'ws', attributes) => boolean)` | `1.0`   | Fraction of traces sent, or a predicate for per-trace decisions. `0` counts as unset and sends everything; pass `() => false` to send none. `1.0` sends everything; `0.1` sends 10%. |
| `maxTracesPerBatch` | `number`                                                                   | `1000`  | Caps how many traces go out per batch, to bound volume on high-traffic applications.                      |
| `flushInterval`     | `number` (ms)                                                              | `5000`  | How often the SDK batches and sends collected traces.                                                     |

Telemetry is buffered in the process and shipped on the flush interval rather than inline with each request. Sampling here decides what the SDK _produces_. The dashboard's per-project spend controls (span sampling, rate caps, drop filters) act on what it has already sent, and you can change them without a redeploy.

#### Declaring objectives in code

`@Objective()` states what a route promises next to the handler that has to keep it, and Observe turns each promise into an [SLO](/observability/dashboard#slos). The objective is written, reviewed, and versioned with the route it covers, in the same change:

[[CODE:24]]

| Option         | What it promises                                                                         |
| -------------- | ---------------------------------------------------------------------------------------- |
| `availability` | This percentage of requests don't fail with an unhandled error - `99.9` for three nines. |
| `latency`      | `{{ '{' }} underMs, target {{ '}' }}`: `target` percent of requests finish in under `underMs` milliseconds. |
| `windowDays`   | The rolling window it's judged over: 7, 14, 28 (the default), or 30 days.                |
| `name`         | What the dashboard calls it, instead of the route and the promise.                       |

Targets run from 90 to 99.999, and a handler can carry up to ten `@Objective()`s; anything outside those bounds is logged and left out when the application starts. Each promise becomes its own SLO, scoped to the application and the route the handler serves, and appears once the route has had traffic. From then on the code owns it: change a target, a window, or a name and deploy, and the same SLO moves. The dashboard marks a declared SLO **in code** and doesn't edit it, and deleting it there doesn't last while the decorator is in place, because the SDK restates each route's objectives hourly. To retire one, remove the decorator, then delete the SLO. SLOs need a plan that has them (Scale or Enterprise); on any other plan, declarations are sent and ignored.

#### Full configuration reference

All options at a glance. Options listed under `createObserveModule()` must be set there; everything else goes to `forRoot()`/`forRootAsync()`.

| Where                   | Option                                | Purpose                                                                   |
| ----------------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `createObserveModule()` | `sourceContext`                       | Attach source lines to error stack frames                                 |
| `createObserveModule()` | `traceIdKey`                          | Context key the trace id is stored under                                  |
| `createObserveModule()` | `traceIdGenerator`                    | How each request obtains its trace id                                     |
| `createObserveModule()` | `attachTraceIdToLogs`                 | Add the trace id to `ConsoleLogger` output                                |
| `createObserveModule()` | `skipInstrumentation`                 | Predicate that excludes provider instances from instrumentation           |
| `forRoot()`             | `appKey`, `appSecret`                 | Project API key pair (or `OBSERVE_APP_KEY`, `OBSERVE_APP_SECRET`)         |
| `forRoot()`             | `endpoint`                            | Collector base URL (or `OBSERVE_ENDPOINT`)                                |
| `forRoot()`             | `enabled`                             | `false` records and sends nothing, for development and CI                 |
| `forRoot()`             | `serviceId`, `serviceVersion`         | Application and release identity (the release is inferred when unset)    |
| `forRoot()`             | `http`, `rpc`, `grpc`, `graphql`      | Per-transport `tags`, `setAttributes`, `getUserId`, `ignore`              |
| `forRoot()`             | `jobs`                                | `tags` and `setAttributes` for queue and scheduled jobs                   |
| `forRoot()`             | `http.queryParamsObfuscateRegex`      | Mask sensitive query string values                                        |
| `forRoot()`             | `http.capture`                        | Headers (and optionally body) recorded for failed and slow requests       |
| `forRoot()`             | `outgoing`                            | Database query and outbound HTTP spans; `outgoing.llm` for model calls   |
| `forRoot()`             | `openTelemetry`                       | W3C `traceparent` in and out, beside an OpenTelemetry SDK                 |
| `forRoot()`             | `otlp`                                | Export spans over OTLP to your OpenTelemetry backend                      |
| `forRoot()`             | `ws`                                  | WebSocket gateway `tags`, `setAttributes`, `getUserId`, `ignore`          |
| `forRoot()`             | `runtimeMetrics`, `runtimeMetricsInterval` | Profiler samples and heartbeat                                       |
| `forRoot()`             | `forwardLogs`, `redaction`            | Logs streaming and scrubbing                                              |
| `forRoot()`             | `tracesSampleRate`                    | Fraction (or predicate) of traces to send                                 |
| `forRoot()`             | `maxTracesPerBatch`, `flushInterval`  | Batching                                                                  |
| `forRoot()`             | `spanCollapse`                        | Collapse repeated sibling spans (default threshold `20`, keep slowest `3`) |
| `forRoot()`             | `shutdownFlushTimeout`                | How long closing the application waits for the final send (default `2000` ms) |
| `forRoot()`             | `debug`                               | SDK diagnostics                                                           |

#### Where to go next

- [Manual instrumentation](/observability/manual-instrumentation) - add your own spans, capture handled errors, attach request-scoped attributes, and report custom metrics.
- [Distributed tracing](/observability/distributed-tracing) - keep one trace across HTTP, gRPC, microservice transports, and GraphQL.
- [Dashboard](/observability/dashboard) - what shows up once the SDK is running, and how the views relate to each other.
