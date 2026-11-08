#### Production checklist

- **Budget time end to end.** Time per attempt times the number of attempts, plus backoff, must fit inside your client's timeout and your load balancer's. For the quotes route, that's about 3.2 seconds.
- **Retry only what is safe.** Set `idempotent: true` only when a second run within the same request is harmless. Pair it with `@Idempotent()` to handle client retries.
- **Pass the signal to every I/O call.** Without it, timed-out work keeps running in the background, unseen by the bulkhead that admitted it.
- **Retry at one layer.** Retry at the entrypoint or in the service policy, not both, and turn off retries in SDKs and HTTP clients underneath.
- **Tune each breaker to its dependency.** Make `minimumCalls` high enough that two errors at night don't open it, set `openDuration` close to how long the dependency usually takes to recover, and use `recordIf` to leave out errors that aren't outages.
- **Give every breaker a timeout.** A breaker learns only from calls that finish. A call that hangs is never counted, and a hanging probe keeps a half-open breaker rejecting everything else.
- **Remember that state is per process.** With several instances, each one has its own breakers, bulkheads and outbound rate limits, and a restart starts them fresh. Each breaker opens on its own, bulkhead limits apply per instance, and an outbound rate limit allows `limit` calls per instance.
- **Keep fallbacks cheap and independent.** A fallback must never call the dependency it stands in for.
- **Alert on transitions.** A breaker opening and bulkheads rejecting requests are the signals to page on.
- **Register an idempotency store.** Without one, `@Idempotent()` keeps its records in each process's memory, lost on every restart or deploy, and production refuses to start. See [Store keys in PostgreSQL](/reliability/idempotency#store-keys-in-postgresql) in the idempotency tutorial.
- **Wire the modules correctly.** Import `ResilienceModule` once, in the root module, and `IdempotencyModule` before it. Use `inheritAppConfig: true` for hybrid applications.
- **Honor Retry-After in your clients.** It tells them when trying again can succeed.

#### Reference

##### Module options

`ResilienceModule.forRoot()` takes these options. `forRootAsync()` builds the same object from a factory, a class implementing `ResilienceOptionsFactory`, or an existing provider.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `defaults` | `ResilienceDefaults` | none | Field defaults for `retry`, `timeout`, `circuitBreaker` and `bulkhead`. They fill in stages that a decorator or preset turns on, and never turn a stage on. See [Register the module](/reliability/resilience#register-the-module). |
| `presets` | `Record<string, ResiliencePreset>` | none | Named sets of stages: `retry`, `timeout`, `circuitBreaker`, `bulkhead`, `outboundRateLimit` and `fallback`. A preset's breaker, bulkhead and outbound rate limit are shared under the preset's name. |
| `mapErrors` | `boolean` | `true` | Turns resilience errors thrown by any handler, with or without decorators, into the transport's error, as listed under Errors below. |
| `isGlobal` | `boolean` | `true` | Registers the module globally. Register it once, in the root module. |

Every time-valued option takes milliseconds or a string such as `'200ms'`, `'2s'` or `'15m'`. The options' injection token is `RESILIENCE_MODULE_OPTIONS`.

##### Decorators

Each decorator works on a handler or on a class, except `@Signal()`, which is a parameter decorator.

| Decorator | Options (default) |
| --- | --- |
| `@Retry(options)` | `attempts` (3, including the first; `Infinity` retries until the signal aborts), `backoff`, `retryIf(error, attempt)` (every error except client errors), `idempotent` (see [Retry a POST safely](/reliability/resilience#retry-a-post-safely)). `@Retry(5)` sets `attempts`, and `@Retry(false)` turns off an inherited retry. |
| `backoff` (of `@Retry()`) | `delay` (`'200ms'`), `factor` (2), `maxDelay` (`'30s'`), `jitter`: `'full'`, `'equal'` or `'none'` (`'full'`, or `'none'` when `factor` is 1). Or a function of the failed attempt and its error that returns a duration. |
| `@Timeout(duration)` | Budget per attempt. Without an argument, the preset's or class's timeout, then `defaults.timeout`. |
| `@CircuitBreaker(options)` | `name`, `failureRateThreshold` (50, a percentage), `minimumCalls` (10), `slidingWindow` (the last 20 calls: `type` is `'count'` or `'time'`, with a `size`), `openDuration` (`'30s'`), `halfOpenMaxCalls` (1), `recordIf(error)` (every error except client errors). A string is a breaker name. See [Fail fast with a circuit breaker](/reliability/resilience#fail-fast-with-a-circuit-breaker). |
| `@Bulkhead(options)` | `name`, `maxConcurrent` (10), `maxQueue` (0), `queueTimeout` (no limit). A string is a bulkhead name. See [Cap concurrent CSV exports with a bulkhead](/reliability/resilience#cap-concurrent-csv-exports-with-a-bulkhead). |
| `@Fallback(method, options)` | A method name on the same class, or a function, called with the error and the `ExecutionContext`. `handleIf(error)` (every error except client errors). |
| `@Resilience(preset)` | Applies a preset from `presets`, stage by stage. |
| `@Signal()` | The current attempt's `AbortSignal`. |

A preset's `outboundRateLimit` takes `limit` (calls per `interval`), `interval` and `maxWait` (0: reject right away).

`ResilienceService` provides `preset(name)`, `create(options, name)`, `circuitBreaker(name)`, `bulkhead(name)`, `circuitBreakers()` and `bulkheads()`. See [Use the same policies inside services](/reliability/resilience#use-the-same-policies-inside-services).

##### Events

Every event is published on `ResilienceEvents.events$` and on the diagnostics channel `nestjs:resilience:<type>`. Each payload has `type`, `policy` and, when there is one, `source` (see [Observe breaker transitions](/reliability/resilience#observe-breaker-transitions)).

| Type | Payload type | Other fields |
| --- | --- | --- |
| `retry` | `ResilienceRetryEvent` | `attempt` (the one that failed, 1-based), `delayMs` (the wait before the next one), `error` |
| `timeout` | `ResilienceTimeoutEvent` | `timeoutMs` |
| `circuit-open` | `ResilienceCircuitOpenEvent` | `from`, `to` |
| `circuit-half-open` | `ResilienceCircuitHalfOpenEvent` | `from`, `to` |
| `circuit-closed` | `ResilienceCircuitClosedEvent` | `from`, `to` |
| `circuit-rejected` | `ResilienceCircuitRejectedEvent` | `retryAfterMs` |
| `bulkhead-rejected` | `ResilienceBulkheadRejectedEvent` | `reason` (`'full'` or `'queue-timeout'`), `active`, `queued` |
| `rate-limited` | `ResilienceRateLimitedEvent` | `retryAfterMs` |
| `fallback` | `ResilienceFallbackEvent` | `error` |

A breaker's state (`from` and `to`) is `'closed'`, `'open'` or `'half-open'`. `ResilienceEvent` is the union of all payload types.

##### Errors

All errors extend `ResilienceError`, which has a `code` and the `policy` name.

| Error | Code | HTTP | Message sent to clients | Fields |
| --- | --- | --- | --- | --- |
| `ResilienceTimeoutError` | `TIMEOUT` | 504 | The operation timed out | `timeoutMs` |
| `CircuitOpenError` | `CIRCUIT_OPEN` | 503, with `Retry-After` | Service temporarily unavailable | `retryAfterMs` |
| `BulkheadFullError` | `BULKHEAD_FULL` | 503 | Server is at capacity | `reason` |
| `OutboundRateLimitError` | `RATE_LIMITED` | 503, with `Retry-After` | Rate limit of a dependency exceeded | `retryAfterMs` |

On microservice and WebSocket handlers, the error is an `RpcException` or `WsException` whose payload has `status`, `code`, `statusCode`, `message` and, for rejections that know it, `retryAfter` in seconds. On GraphQL, the field's error has `code`, `httpStatus` and `retryAfter` in `extensions` (see [Other transports](/reliability/resilience#other-transports)).
