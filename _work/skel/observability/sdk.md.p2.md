#### Automatic instrumentation

Everything in this section is recorded without any code of your own; installing the SDK is enough. The options only narrow it or switch it off.

##### Database queries and outbound HTTP

Since `@nestjs/observe` 0.3.0, database queries and outbound requests appear as spans with no configuration, nested under the method that made them. A slow repository call shows _which_ statement it was waiting on.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/sql.webp" alt="A query opened in the waterfall" /></figure>

Databases are instrumented at the driver rather than the ORM: `pg`, `mysql2`, `mssql`, and `mongodb` are detected if your application already depends on them, which covers TypeORM, MikroORM, Drizzle, Mongoose, Knex, Sequelize, and Prisma's driver adapters without naming any of them. SQL Server is the exception: `mssql` is what TypeORM and Prisma's SQL Server adapter run on, but Knex, Sequelize, and MikroORM talk to SQL Server through `tedious` directly, which isn't covered yet (nor is `mssql/msnodesqlv8`). ORMs that ship their own nested copy of a driver (MikroORM and Mongoose do, whenever versions disagree) are handled too. The driver's own housekeeping (connection handshakes, authentication, pings) is not recorded. A query span is labeled with its verb and table (`SELECT users`) and carries the statement with **every literal removed** - strings, numbers, `IN (...)` lists, and comments are replaced before the span leaves the process, and bound parameters are never read at all. Repeated queries under one parent fold into a single node with a count, so an N+1 reads as `SELECT order_items ×47` rather than 47 rows.

Other clients, Redis and Kafka among them, aren't instrumented at the library. A Nest application almost always registers them as providers, though - an `ioredis` client from a factory, a `ClientKafka` from `ClientsModule` - and the SDK records every provider's method calls: each call on the client is a span under the method that made it, and one that returns a promise, as `ioredis` commands do, is timed until it settles. A client created and called outside dependency injection isn't recorded.

Outbound HTTP is read from Node's own diagnostics channels, so `fetch`, `undici`, and everything built on `node:http` (axios, got, most SDKs) are covered with nothing patched. The span is labeled `GET api.example.com` and carries the URL with sensitive query parameters masked. The SDK also sends the current trace id as `x-request-id`, which makes [HTTP-to-HTTP tracing](/observability/distributed-tracing#http-to-http) automatic. With the [`openTelemetry`](/observability/opentelemetry#running-beside-opentelemetry) option on, it sends a W3C `traceparent` as well: `http.traceContext: false` keeps that header off, and `propagateTraceId` decides where both headers go.

[[CODE:12]]

Set `outgoing: false` to switch all of it off, or `database: false` / `http: false` individually.

> info **Hint** These spans are **not billed**. They are detail about a method span you already sent, so they don't count toward your Observability Events or your rate cap. A request that runs ten queries costs the same as before.

##### Model calls

Since `@nestjs/observe` 0.3.20, a `fetch` to a model provider also records what the call used on its outbound span: the model, the input, output, and cached input tokens the provider's response states, and, for a stream, the time to its first event. OpenAI, Azure OpenAI, Anthropic, Google Gemini and Vertex AI, Amazon Bedrock, Mistral, Groq, OpenRouter, Together AI, DeepSeek, xAI, Cohere, and Perplexity are recognized by host, so the official SDKs, the Vercel AI SDK, and LangChain are all covered without being named.

- **Read as the response passes through.** The SDK reads the response at the pace your code does, streams included, and hands it on unchanged. A stream your code cancels is cancelled at the provider too.
- **Prompts and completions are never sent.** Only the model and the token counts leave the process.
- **`fetch` only.** A call made through `node:http` - axios, or the AWS SDK's default client for Bedrock - keeps its ordinary outbound span without the model or tokens.

A gateway in front of the providers (LiteLLM, Portkey, your own proxy) or a self-hosted model with an OpenAI-compatible API is added by host, and its calls are tagged with the provider `custom`. `outgoing: {{ '{' }} llm: false {{ '}' }}` stops reading model calls while keeping their plain spans:

[[CODE:13]]

A [production rule](/observability/production-rules) can bound how many model calls a request makes.

##### WebSocket gateways

Messages handled by `@SubscribeMessage()` are reported as requests with the `ws` protocol and an operation id of `GatewayClass:pattern`, on any platform adapter. The `ws` option block takes the same `ignore`, `tags`, `setAttributes`, and `getUserId` hooks as the other transports; each receives `{{ '{' }} gateway, pattern, client, data {{ '}' }}`. Connections and disconnections are not operations and are not reported.

##### Queues

`@nestjs/bullmq` and the original `@nestjs/bull` are both instrumented: every processor run is reported as a job, with its queue wait, attempt number, and outcome. A job added from inside a traced operation inherits that operation's trace id - see [Distributed tracing](/observability/distributed-tracing#queue-jobs-bullmq-and-bull).

##### Runtime metrics and profiling

[[CODE:14]]

`runtimeMetrics` (default `true`) samples memory, CPU, garbage collection, and event loop latency on an interval (`runtimeMetricsInterval`, default `60000` ms) and feeds the **Profiler**. The same samples double as the application's heartbeat: a **Telemetry silence** alert fires when they stop arriving, which gives you lightweight uptime monitoring without an external probe.

#### Errors and failed requests

An error that escapes a controller, resolver, or job is captured automatically. These options decide what comes with it: the source code around the failing frame, and the headers and body of the request that failed.

##### Error source context

Errors that propagate out of a controller, resolver, job, or span are captured automatically. When `sourceContext` is enabled (the default), the SDK also reads the source lines around each in-app stack frame of a captured error and attaches them. This lets the dashboard show the failing code alongside the stack trace, even for a production failure on a build you don't have checked out.

[[CODE:15]]

This is an option of `createObserveModule()`, not `forRoot()`. Set `sourceContext: false` to disable it, or pass an object to tune the defaults:

| Option           | Type      | Default | Description                                                                                                                                                                                                                                                                                                                                                                     |
| ---------------- | --------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `linesOfContext` | `number`  | `5`     | Lines read on either side of the frame's line.                                                                                                                                                                                                                                                                                                                                  |
| `maxFrames`      | `number`  | `5`     | How many in-app frames, counted from the top of the stack, get source attached. Bounds the payload on deep stacks.                                                                                                                                                                                                                                                             |
| `sourceMaps`     | `boolean` | `false` | Resolves compiled frames back through source maps before reading source. Only needed if the process runs compiled output _without_ Node's own source map support (`--enable-source-maps` or `process.setSourceMapsEnabled(true)`); with that on, frames already carry original positions and this is redundant. Costs a map parse per compiled file on first touch, cached after. |

> warning **Warning** Enabling this ships fragments of your application's source code (usually a few lines around the error) to your dashboard, where they are stored alongside the error. Frames inside `node_modules` and Node internals are never read, only application source. Turn it off if shipping any source is not acceptable for your codebase.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/error-with-source.webp" alt="Error card with source context" /></figure>

##### Capturing failed and slow requests

When an HTTP request **fails**, the SDK records a small, fixed allow-list of its headers alongside it - `user-agent`, `content-type`, `content-length`, `accept`, `host`, `origin` and `referer`. None of these authenticate or identify the caller. If you set `slowerThanMs`, requests that ran at least that long are captured the same way, failed or not. An ordinary request records nothing. Request bodies are **off** by default; turn them on explicitly if you want them:

[[CODE:16]]

Everything captured passes through [`redaction`](/observability/sdk#logs) before it leaves the process: sensitive keys (`password`, `token`, `authorization`, ...) are masked by name inside the body, and naming a sensitive header records `[REDACTED]` instead of its value. `capture: false` records nothing. The capture is shown on the request's detail page as a **Request** card.

#### Logs and trace correlation

Every execution gets a trace id. These options decide how your log lines relate to it: forwarded to the dashboard, or only stamped with the id so your own log stack can link to the trace.

##### Logs

[[CODE:17]]

`forwardLogs` (default `false`) sends your application's log lines (anything written through Nest's `Logger`) to the dashboard, correlated to the trace that was active when each line was written. On an execution page, every line is placed on the trace's clock next to the span that was in flight when it was written. Log forwarding is available on Pro and above.

Forwarding logs moves them onto infrastructure you don't control, so redaction is on by default. The same redaction also scrubs the message and stack of every captured error and any captured request data, whether or not `forwardLogs` is on:

| `redaction` field    | Type       | Default        | Description                                                                                                                                                                                                                                                              |
| -------------------- | ---------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enabled`            | `boolean`  | `true`         | Whether anything is scrubbed at all.                                                                                                                                                                                                                                     |
| `useDefaultPatterns` | `boolean`  | `true`         | Applies the built-in patterns: bearer tokens, JWTs, AWS key ids, PEM private keys, `key=value` secrets, and Luhn-valid card numbers. Disable only if you're replacing them wholesale with your own `patterns`; there's no supported case for forwarding logs unredacted.  |
| `patterns`           | `RegExp[]` | -              | Extra patterns to mask, for secrets shaped in a way only your codebase knows (internal token prefixes, customer identifiers). Always applied as if global, so a match is never limited to the first occurrence in a line.                                                |
| `keys`               | `string[]` | -              | Extra keys whose values are masked outright (in log attributes, captured headers and bodies, and URL query strings), on top of the built-in list. Compared case-insensitively and ignoring `-`/`_`, so `apiKey`, `api_key`, and `API-KEY` are one entry.                                                                               |
| `replacement`        | `string`   | `'[REDACTED]'` | Text substituted for anything matched.                                                                                                                                                                                                                                   |

> info **Hint** Even with `forwardLogs` off, the SDK augments `ConsoleLogger` so every line written inside a traced execution carries its trace id (`attachTraceIdToLogs`, see [Trace correlation](#trace-correlation)). That lets you correlate your own log aggregator with traces in the dashboard without shipping the log content anywhere.

##### Trace correlation

These are also options of `createObserveModule()`. They shape how requests get a trace id and how that id shows up in your own logs:

[[CODE:18]]

| Option                | Type                       | Default                                                       | Description                                                                                                                         |
| --------------------- | -------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `traceIdKey`          | `string`                   | `'traceId'`                                                   | The key used to store the trace id in the request context, for later retrieval through `TracerService`.                            |
| `traceIdGenerator`    | `(req: unknown) => string` | Adopts a well-formed `x-request-id` (HTTP header, or microservice packet metadata) if present, else a UUID v7 | Generates the trace id per request. Called with the request object for HTTP; for other protocols it receives the transport context. |
| `attachTraceIdToLogs` | `boolean`                  | `true`                                                        | Augments `ConsoleLogger` to include the trace id in log messages, so logs can be correlated with traces even without `forwardLogs`. In the default text format the id ends the line, after the message (`   Trace ID: <id>`); with [JSON logging](/application/logger#json-logging) it is a `traceId` field. Lines written outside a traced execution are unchanged. |

Because the default generator adopts an incoming `x-request-id`, a chain of HTTP services already shares one trace with no extra configuration. Services instrumented with OpenTelemetry pass the trace on in `traceparent` instead, which the `openTelemetry` option of `forRoot()` reads and sends - see [Running beside OpenTelemetry](/observability/opentelemetry#running-beside-opentelemetry). The same applies to the microservice transports: TCP and Redis on `@nestjs/microservices` 12.0.4 or later, and NATS, Kafka, RabbitMQ, MQTT 5, and gRPC on 12.3.3 or later. Propagating across earlier versions and GraphQL takes a few lines - see [Distributed tracing](/observability/distributed-tracing).
