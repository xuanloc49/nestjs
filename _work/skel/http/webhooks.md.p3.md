#### Delivery guarantees

Outgoing webhooks are delivered **at least once**; the receiver deduplicates by `webhook-id`.

| Situation | Outcome |
| --- | --- |
| The order's transaction rolls back | The message never existed and nothing is sent |
| The order's transaction commits | One delivery per subscribed endpoint of the tenant, eventually delivered or failed with its attempt log |
| The outbox redelivers the message (a relay crashed after the fan-out) | The fan-out is idempotent: one delivery per message and endpoint |
| The endpoint was created after the message, or is disabled | It doesn't receive it, and a replay doesn't bring it back |
| A worker dies after claiming | Sent by another worker once the lease expires (`worker.lease`, 1 minute) |
| A worker dies after sending, before recording | **Sent twice**, with the same `webhook-id`, once the lease expires |
| Two workers, same delivery | A claim is exclusive for the lease, and every later write is fenced by it |
| The partner answers 2xx | Delivered |
| It answers anything else, or nothing | Retried with backoff, `Retry-After` honored; 429, 502, 503 and 504 pace the endpoint |
| It answers 410 Gone | Failed (`rejected`), and the endpoint is disabled (`gone`) |
| Every attempt fails for `disableEndpointAfter` | The endpoint is disabled (`failing`), once |
| A partner asks for a replay | A new round with the same `webhook-id`, so its inbox skips it |

Deliveries have **no order**. A worker sends one endpoint's deliveries one at a time, most overdue first, but a failed attempt waits out its backoff while later messages go out, several workers send to the same endpoint at once, and a replay sends an old message now. Two updates of one order can reach the partner in either order. Receivers cope as they do with duplicates: the body's `timestamp` is when the message was dispatched (`webhook-timestamp` is when this attempt was signed), so a handler can ignore an event older than the state it already holds, or treat the webhook as a signal and read the current state from the API.

Incoming webhooks run their handler **once per webhook id and receiver in the common case** with the default inbox (again after a crash between the handler and the inbox write, or when two copies race on two instances), and their `processInTransaction()` work **exactly once**.

#### Production checklist

- Keep the endpoints and the deliveries in your application's database, on a database server: register `PostgresWebhookStore`, or `MySqlWebhookStore`, and the outbox's store next to it ([Keep webhooks in your database](/http/webhooks#keep-webhooks-in-your-database)). The production guard refuses to start in memory; `allowInMemoryStorage` is for a process whose pending deliveries you can afford to lose.
- Apply both stores' migrations before a new version starts, with `npx @nestjs/webhooks migrate` and `npx @nestjs/outbox migrate` or your migration tool, and check them in CI with `status`. With `NODE_ENV=production`, the stores don't migrate at startup: a schema that's behind fails it instead.
- On PostgreSQL, keep the database's default isolation at READ COMMITTED: the stores refuse a stricter one. On MySQL, run a transaction again when MySQL breaks a deadlock in it (error 1213): it rolled back, with the messages it dispatched and the webhooks it recorded.
- Leave `delivery.allowHttp` and `delivery.allowPrivateNetworks` off. A partner's URL is untrusted input, and the transport resolves it itself and pins the address it checked. Use `allowedAddresses` for the one private range you really deliver to, and alert on `destination-blocked` events: a customer pointing a webhook at your metadata service is worth a look.
- Run the worker in a few instances (`WEBHOOKS_WORKER`), not in every API pod: each claim is a short transaction, and the leases keep them from sending the same delivery twice.
- Alert on `lagMs` and `failed` from `deliveries.stats()`, and on `endpoint-disabled`: tell the partner, by email, that their endpoint was switched off and why.
- Version the payloads. A partner keeps its handler for years, and `retry()` re-sends the body as it was dispatched. Add fields to a type's `data`, never rename or remove one. For a breaking change, add a new type, `order.shipped.v2` in `eventTypes`, and dispatch both in the same transaction (`dispatch()` takes an array) while partners move their subscriptions over; an endpoint subscribed to `*` gets both. Then stop dispatching the old type. Replays of older messages still carry the old shape until the log is pruned.
- Give partners the delivery log and the replay. It answers "did you send it?" before they open a ticket.
- Rotate secrets with the overlap, never with `overlap: 0` unless a secret leaked, and seal them at rest with `WEBHOOKS_ENCRYPTION_KEYS`. Keep the keys in a secret manager.
- Prune the log. `deliveries.prune('30d')` from a [cron job](/application/task-scheduling#declarative-cron-jobs); nothing schedules it for you.
- For incoming webhooks, keep `rawBody: true`, and keep the receivers' secrets in the environment. List the old and the new secret while a provider rotates.
- Keep provider handlers short and idempotent in their own right (a status check inside the transaction), even with `processInTransaction()`: the inbox protects against a redelivery, the check against a provider that sends two different events for one fact.
- Prune the inbox with `OutboxInbox.prune()` on a window longer than any provider's retry schedule (Stripe retries for three days, GitHub doesn't retry at all). For GitHub, that window is also how long a replayed request is caught, with the deduplication keyed on the body ([Other senders](/http/webhooks#other-senders)).
- Call `app.enableShutdownHooks()`, so a deploy lets attempts in flight finish and releases the rest.
- For a store of your own, run the contract suites with `concurrent: true` in CI, against the database version you run in production.

#### The store contract

`PostgresWebhookStore` and `MySqlWebhookStore` implement both of the package's contracts, `WebhookEndpointStore` and `WebhookDeliveryStore`. For another database, implement them in a provider of your own. The JSDoc of each method in the two interfaces states its rule, and the race it prevents.

**Registration.** The store is an ordinary singleton provider that calls `registerSource()` on the injectable `WebhooksStorage` in its constructor, naming the contracts it implements: `endpoints`, `deliveries`, or both from one class. The registry checks the shape at once, refuses a second registration unless it passes `replace: true`, and locks when `WebhooksModule` initializes, logging the store in use. With nothing registered, the module uses `InMemoryWebhookStore`, which loses the endpoints and the pending deliveries on restart and can't share them between instances. With `NODE_ENV=production`, startup fails instead, unless `allowInMemoryStorage: true` accepts that.

**No transaction handle.** Unlike the outbox's `add()`, no method here takes your transaction: the outbox carries the message out of your transaction, and the webhook store runs on its own connections.

**The methods.** The ones marked atomic are one conditional statement or one transaction with a row lock, never a read followed by a write; they are the ones the contract suites race.

| Method | What it does | Atomic |
| --- | --- | --- |
| `createEndpoint`, `getEndpoint`, `listEndpoints`, `updateEndpoint`, `deleteEndpoint` | An endpoint's lifecycle; `list` newest first, by tenant | No |
| `findSubscribedEndpoints(tenant, type)` | The enabled endpoints of exactly this tenant subscribed to the type (or `*`): the fan-out's query | No, but the suite checks it never returns another tenant's |
| `addEndpointSecret(id, secret, expireOthersAt, now)` | The rotation: the new secret first, the others expiring | Yes: the row is locked, so two rotations both land |
| `recordEndpointFailure(id, failure)` | Sets `failingSince` on the first failure; disables the endpoint once it has been failing long enough, and says so once | Yes: the row is locked |
| `recordEndpointSuccess(id)` | Clears `failingSince` | No |
| `createDeliveries(message, deliveries)` | The fan-out: the message unless it exists, each delivery unless its `(messageId, endpointId)` exists | Yes: a unique key on the pair, such as PostgreSQL's `ON CONFLICT DO NOTHING` on it |
| `claimDeliveries(request)` | Leases due deliveries, most overdue first, with their message | Yes: `FOR UPDATE SKIP LOCKED`, then the lease |
| `recordDeliveryAttempt(id, owner, update)` | The attempt's outcome and log row, if `owner` still holds the lease | Yes: fenced by the lease owner |
| `releaseDeliveries(ids, owner, nextAttemptAt)` | Gives leases back, postponing when asked | Yes: fenced |
| `getDelivery`, `getMessage`, `listDeliveries`, `listDeliveryAttempts`, `deliveryStats` | Reads; `list` newest first, by tenant, endpoint, message, status and type | No |
| `retryDeliveries(filter, now)` | A new round for the matches that aren't leased | Yes: one `UPDATE` with the lease in its `WHERE` |
| `pruneDeliveries(before)` | Finished deliveries older than `before`, their logs, and the messages left without deliveries | No, but never a pending delivery |

**Test it** with `webhookEndpointStoreContract()` and `webhookDeliveryStoreContract()` from `@nestjs/webhooks/testing`. Each case gets a store on empty tables from the function you pass. The tutorial's tests run both suites against `PostgresWebhookStore` through Drizzle, as you would against yours:

[[CODE:66]]

With `concurrent: true`, the suites race rotations and failures on one endpoint, workers claiming side by side, fan-outs of one message, a stale worker against a takeover, and a retry against a claim. On PGlite, with one connection, they pass serialized: run them on a server too, through a pool of several connections, where a store without the right locks fails them. The package's own tests run the suites against a hand-written Drizzle store, as the proof that a store written against the interfaces passes them.
