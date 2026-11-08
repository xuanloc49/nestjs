#### Reference

##### Module options

`WebhooksModule.forRoot()` takes these options. `forRootAsync()` takes `outgoing`, `transport` (as a class), `imports` and `isGlobal` at the top level, next to `useFactory`, `useClass` or `useExisting`, and the factory returns the rest. See [Register the modules](/http/webhooks#register-the-modules).

| Option | Default | Description |
| --- | --- | --- |
| `eventTypes` | any type | The message types this application sends. `dispatch()` and new endpoints accept only these (endpoints also accept `*`). |
| `retry` | 10 attempts | `attempts` (including the first), `backoff` and `retryIf(error, attempt, delivery)`. A number sets `attempts`, and `false` means a single attempt. |
| `retry.backoff` | see description | `delay` (`'5s'`), `factor` (4), `maxDelay` (`'1d'`, also the cap for `Retry-After`), `jitter`: `'equal'`, `'full'` or `'none'` (`'equal'`). Or a function of the attempt, the error and the delivery that returns a duration. |
| `disableEndpointAfter` | `'5d'` | Disables an endpoint that has failed every attempt for this long without a success. `false` never disables one. |
| `secretRotationOverlap` | `'24h'` | How long a rotated-out secret keeps signing next to the new one. |
| `delivery.timeout` | `'15s'` | One attempt: DNS, connection, TLS, request and response. Shorter than `worker.lease`. |
| `delivery.allowHttp` | `false` | Accepts `http://` endpoint URLs. For development. |
| `delivery.allowPrivateNetworks` | `false` | Delivers to loopback, private, shared-address and unique-local ranges. For development. Link-local and cloud metadata addresses stay blocked. |
| `delivery.allowedAddresses` | none | CIDR ranges, such as `10.20.0.0/16`, delivered to although they'd be blocked. |
| `delivery.maxResponseSize` | 4096 | Bytes of the response body read and kept in the log. |
| `delivery.userAgent` | `NestJS-Webhooks/1.0` | The `User-Agent` header. |
| `worker.enabled` | `true` | Delivers in this process. `false` in instances that only dispatch. |
| `worker.pollInterval` | `'1s'` | The wait between polls when idle. `notify()` polls at once. |
| `worker.batchSize` | 50 | Deliveries claimed per poll. |
| `worker.concurrency` | 10 | Endpoints delivered to in parallel. One endpoint's deliveries go one at a time. |
| `worker.lease` | `'1m'` | How long a claim is exclusive. Longer than `delivery.timeout`. |
| `encryption` | off | Seals endpoint secrets at rest. `keys` lists 32-byte `Buffer`s or strings of at least 32 characters, newest first: the first key encrypts, every key decrypts. |
| `receivers` | none | The senders whose webhooks this application accepts, by the name `@VerifyWebhook()` uses (see the next table). |
| `transport` | `HttpWebhookTransport` | A `WebhookTransport` class at the top level, or an instance from the async factory. |
| `allowInMemoryStorage` | `false` | Lets a production application start without registered stores. |
| `outgoing` | `true` | Top level only. `false` in a service that only receives webhooks: no endpoints, deliveries, worker or stores. |
| `imports` | none | Top level only. Modules whose exports a transport class injects. |
| `isGlobal` | `true` | Top level only. Registers the module globally. |

Durations are milliseconds or strings such as `'15s'`, `'24h'` or `'5d'`. The options' injection token is `WEBHOOKS_MODULE_OPTIONS`.

Each entry of `receivers` takes these options (see [Receive the payment provider's webhooks](/http/webhooks#receive-the-payment-providers-webhooks) and [Receive the carrier's Stripe-like webhooks](/http/webhooks#receive-the-carriers-stripe-like-webhooks)):

| Option | Applies to | Default | Description |
| --- | --- | --- | --- |
| `scheme` | all | required | `'standard'`, `'stripe'`, `'github'`, or an instance of a class extending `WebhookSignatureScheme` |
| `secret` | all | required | One secret, or an array while the sender rotates. Every one is tried. |
| `tolerance` | `standard`, `stripe`, custom | `'5m'` | The largest accepted distance between the signed timestamp and now, in either direction |
| `header` | `stripe` | `'stripe-signature'` | The signature header, for senders that copied Stripe's scheme |
| `id` | `stripe`, `github` | the payload's `id`; the `X-GitHub-Delivery` header, which isn't signed (see [Other senders](/http/webhooks#other-senders)) | A function of the payload and the headers that returns the deduplication id, of at most 255 characters |
| `dedupe` | all | `true` | Skips a webhook id this receiver already processed |
| `consumer` | all | `webhooks:<name>` | The inbox consumer name. Keep it stable. At most 255 characters, the default included: a longer one fails the startup with a `TypeError` |

##### PostgreSQL and MySQL stores

`new PostgresWebhookStore(options, webhooksStorage)`, from `@nestjs/webhooks/postgres`, and `new MySqlWebhookStore(options, webhooksStorage)`, from `@nestjs/webhooks/mysql`, take these options. The outbox's `PostgresOutboxStore` and `MySqlOutboxStore` take the same, with `'nest_outbox'` as the default `schema`:

| Option | Default | Meaning |
| --- | --- | --- |
| `executor` | Required | How the store reaches the database: `fromDrizzle(db)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma, options)`, `fromKysely(db)`, and `fromPg(pool)` on PostgreSQL or `fromMysql2(pool)` on MySQL, imported from the store's own subpath: the other dialect's executor doesn't compile |
| `schema` | `'nest_webhooks'` | On PostgreSQL, the schema of its tables, which its first migration creates: letters, digits and underscores, not starting with a digit, at most 63 characters. On MySQL, the prefix of its tables in the connection's database (`nest_webhooks_endpoints`...): lowercase letters, digits and underscores, not starting with a digit, at most 40 characters |
| `migrate` | `true`, except with `NODE_ENV=production` | Apply the pending migrations when the application starts. With `false`, startup fails with a `WebhookSchemaError` while the schema is behind |

Each executor takes your database client, and its own kind of transaction object, which `dispatch()` and `processInTransaction()` then take:

| Executor | Takes | Transaction object |
| --- | --- | --- |
| `fromDrizzle(db)` | A Drizzle database: on PostgreSQL, whichever its driver; on MySQL, `drizzle-orm/mysql2`'s | The `tx` that `db.transaction()` hands its callback |
| `fromTypeOrm(dataSource)` | A `DataSource` of type `postgres` or `mysql` | The `EntityManager` that `dataSource.transaction()` hands its callback, or a `QueryRunner` after `startTransaction()` |
| `fromPg(pool)` | A node-postgres `Pool`, on PostgreSQL | A client from `pool.connect()`, after `BEGIN` |
| `fromMysql2(pool)` | A `mysql2/promise` pool, on MySQL | A connection from `pool.getConnection()`, after `beginTransaction()` |
| `fromPrisma(prisma, options)` | A Prisma client, through a driver adapter such as `@prisma/adapter-pg`, or `@prisma/adapter-mariadb` on MySQL. `maxWait` (default `'10s'`) and `timeout` (default `'1m'`) limit the stores' own transactions | The transaction client that `prisma.$transaction()` hands its callback |
| `fromKysely(db)` | A `Kysely` instance with a PostgreSQL or MySQL dialect | The transaction that `db.transaction().execute()` hands its callback |

The store's `migrate()` method applies the pending migrations at once, whatever the `migrate` option says, and resolves with the versions it applied. `PostgresWebhookStore.migrationSql()` and `MySqlWebhookStore.migrationSql()` return their SQL, with the bookkeeping. Their options are the `schema`, the versions to go `from` (default `0`, a new database) and `to` (default: the one the package needs), and `statementBreakpoints`, which puts drizzle-kit's `--> statement-breakpoint` between the statements. On PostgreSQL, from version 0, the SQL starts with `CREATE SCHEMA IF NOT EXISTS`, which needs the CREATE privilege on the database: leave it out if someone created the schema for you. `MySqlWebhookStore.migrationStatements()` returns MySQL's statements one per string, to run in order, each once. `schemaVersion` is the version the package needs. A schema's own version is the highest applied in its `migrations` table.

The command line, `npx @nestjs/webhooks`, takes `--url` (default `DATABASE_URL`), whose scheme picks the store: `postgres://` or `postgresql://` for `PostgresWebhookStore`'s schema, `mysql://` for `MySqlWebhookStore`'s tables. It takes `--schema` too (default `nest_webhooks`). `npx @nestjs/outbox` does the same for the outbox's stores:

| Command | What it does |
| --- | --- |
| `migrate` | Applies the pending migrations, as `migrate: true` does at startup. Needs `pg` or `mysql2` installed |
| `status` | Prints the schema's version and the one the package needs, and exits with 1 while the schema is behind |
| `sql` | Prints the SQL of `migrationSql()`, from `--from` to `--to`, without a database: PostgreSQL's, or MySQL's with `--dialect mysql`. `--statement-breakpoints` separates the statements for drizzle-kit |

##### Services and decorators

- `Webhooks`: `dispatch(tx, message)` takes one message or an array, with `type`, `data`, `tenant` and an optional `id`, and throws a `TypeError` for an unknown type, data that isn't JSON-serializable or an invalid id. `notify()` runs the relay now.
- `WebhookEndpoints`: `create(input)`, `list(query)`, `get(id, scope)`, `update(id, changes, scope)`, `delete(id, scope)`, `getSecret(id, scope)` and `rotateSecret(id, options)`, where `options` takes `tenant`, `overlap` and `secret`. `create()` takes a `secret` too, an existing `whsec_…` used instead of a generated one. See [Let partners subscribe](/http/webhooks#let-partners-subscribe).
- `WebhookDeliveries`: `list(query)`, `get(id, scope)`, `retry(idOrFilter, scope)`, `stats()` and `prune(olderThan)`. See [Retries, the delivery log and replay](/http/webhooks#retries-the-delivery-log-and-replay).
- `WebhookWorker`: the deliverer, started when the application boots unless `worker.enabled` is `false`. `start()`; `stop()`, which stops claiming, waits for the attempts in flight and releases the deliveries it hasn't started; `running`; `notify()`, which polls now instead of at the next tick; `runOnce()`, which claims one batch and delivers it, resolving to how many it `claimed`, `delivered`, `retried`, `failed` and `released`, and on how many it lost the lease (`leaseLost`), and which works with the worker stopped, as the tests drive it; `stats()`, the same as `WebhookDeliveries.stats()`.
- `WEBHOOKS_OUTBOX_TOPIC`: the outbox topic that dispatched messages travel on, `'nestjs.webhooks.message'`, to the package's `@OnOutboxMessage()` handler, the fan-out. An outbox whose `route` picks among several transports sends this topic to `local`.
- `WebhookVerifier`: `verify(receiver, request)` checks a request that didn't arrive on an HTTP route, such as one stored in a queue, from its `headers` and `rawBody`.
- `@VerifyWebhook(receiver)` verifies and deduplicates, on a method or a controller. `@IncomingWebhook()` injects the verified webhook: `receiver`, `id`, `timestamp`, `payload`, `rawBody` and `processInTransaction()`. `@WebhookPayload()` injects the payload alone, and takes pipes like `@Body()`.

##### Transports

The worker sends through the `WebhookTransport` provider. The default, `HttpWebhookTransport`, is built from the `delivery` options: one `POST` per attempt over `node:http` and `node:https`, the host resolved once and every address it resolves to checked, the socket pinned to the checked address, redirects never followed, no proxy from the environment. Its constructor takes two options that `delivery` doesn't:

- `ca`: certificate authorities to trust besides Node's own, for endpoints behind a private CA. They are added to Node's trust store, so public endpoints keep verifying.
- `lookup`: resolves a host name to every address it has, each an `address` and its `family` (4 or 6), in place of the system resolver. Every address it returns is still checked, and the connection goes to the first.

To use them, pass an instance as `transport`, with the same `allowHttp`, `allowPrivateNetworks` and `allowedAddresses` as `delivery`: `delivery` still decides which URLs `WebhookEndpoints` accepts, and the transport what it connects to.

[[CODE:67]]

A transport of your own extends `WebhookTransport` and implements `send(request, options)`, where `options` has the attempt's `signal` and its `attempt` number. The request carries the `url`, the signed `headers` and the `body`, and the ids of its endpoint, delivery and message. Resolve with the response's `statusCode`, `headers` and the start of its `body`, whatever the status, and throw only when there is no response; stop when `signal` aborts, after `delivery.timeout`. `NonRetryableWebhookError` and `WebhookDestinationBlockedError` fail the delivery without a retry; any other error is retried. Pass the class as `transport` at the top level of `forRoot()` or `forRootAsync()`, where Nest instantiates it (`imports` for the modules it injects from), or an instance. It replaces the SSRF guard with whatever it does itself: sending through an egress proxy that enforces one, such as Smokescreen, is a reason to write one; wrapping `HttpWebhookTransport` keeps the guard.

For tests, `InMemoryWebhookTransport` records instead of sending, without network or address checks (see [Testing](/http/webhooks#testing)):

- `sent`: every request, oldest first, as `SentWebhook`s. `clear()` empties it.
- `respondWith(answer)`: how the endpoint answers from now on, 200 until then. A status (`503`), a response (`statusCode`, `headers` such as `retry-after`, `body`), or a function of the request and the attempt number that returns either and throws to simulate no response.
- `filter(query)` and `single(query)`: the requests matching `type`, `url` (a string or a `RegExp`), `endpointId` and `messageId`, or a function of the `SentWebhook`. `single()` throws, listing what was sent, unless exactly one matches.

A `SentWebhook` has the `request`, the `attempt` number within its round, `sentAt`, the request's `url`, `type`, `messageId`, `endpointId`, `deliveryId`, `headers` and `body`, `data` (the body's `data`, parsed), and `isSignedWith(secret)`, which checks a `v1` signature against an endpoint's secret.

##### Events

`WebhooksEvents.events$` emits every event, and each is also published on the diagnostics channel `nestjs:webhooks:<type>`.

| Type | Payload type | Fields besides `type` |
| --- | --- | --- |
| `delivered` | `WebhooksDeliveredEvent` | `delivery`, `statusCode`, `attempt`, `durationMs` |
| `retry-scheduled` | `WebhooksRetryScheduledEvent` | `delivery`, `error`, `statusCode` (`null` without a response), `attempt`, `delayMs` |
| `delivery-failed` | `WebhooksDeliveryFailedEvent` | `delivery`, `error`, `statusCode`, `attempt`, `reason` |
| `endpoint-disabled` | `WebhooksEndpointDisabledEvent` | `endpointId`, `tenant`, `reason` (`'failing'` or `'gone'`) |
| `destination-blocked` | `WebhooksDestinationBlockedEvent` | `endpointId`, `tenant`, `reason`, `address` |
| `verification-failed` | `WebhooksVerificationFailedEvent` | `receiver`, `reason` |

A failed delivery's `reason` is `exhausted`, `rejected` (410 Gone, a blocked destination, `NonRetryableWebhookError` or `retryIf`), `endpoint-disabled` or `endpoint-deleted`. A verification failure's `reason` is `missing-header`, `malformed-header` (a webhook id longer than 255 characters too), `invalid-signature`, `timestamp-out-of-tolerance` or `invalid-payload`. `WebhooksEvent` is the union of all payload types.

##### Errors

Every error except `NonRetryableWebhookError` extends `WebhooksError`. The ones with a `status` are meant for the partner API's exception filter, as in [Let partners subscribe](/http/webhooks#let-partners-subscribe).

| Error | Status | Thrown when |
| --- | --- | --- |
| `InvalidWebhookEndpointError` | 400 | An endpoint's URL, event types or secret are refused. `field` names which one. |
| `WebhookEndpointNotFoundError` | 404 | The endpoint doesn't exist, or belongs to another tenant |
| `WebhookDeliveryNotFoundError` | 404 | The delivery doesn't exist, or belongs to another tenant |
| `WebhookVerificationError` | 401, or 400 for `invalid-payload` | `WebhookVerifier.verify()` refuses a request. It has the `receiver` and the `reason`. |
| `WebhookDestinationBlockedError` | none | The endpoint's URL is, or resolves to, a blocked address. The delivery fails without a retry. |
| `WebhookResponseError` | none | The endpoint answered outside 2xx. It has the `statusCode`, and `retryAfterMs` from a `Retry-After` header. |
| `WebhookDeliveryTimeoutError` | none | No response within `delivery.timeout` |
| `NonRetryableWebhookError` | none | A custom transport throws it to fail a delivery without a retry |
| `WebhookSchemaError` | none | A store's schema is behind the package's migrations while `migrate` is off, or applying them failed (`cause`): startup and every call fail until it's fixed. It has the `schema`, its `version` and the `requiredVersion`. From `@nestjs/webhooks/postgres` and `@nestjs/webhooks/mysql` |

`@VerifyWebhook()` answers a refused request with a 401 (a 400 for a signed body that isn't JSON) and a generic message, and the reason goes to the `verification-failed` event. A request whose body wasn't kept raw gets a 415 if it isn't JSON or a form, and a 500 that logs the missing `rawBody: true` otherwise.
