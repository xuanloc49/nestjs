#### Handle order.placed in-process

The confirmation email is a handler for `order.placed`. The mailer is a stand-in for your email provider's SDK:

[[CODE:14]]

[[CODE:15]]

`@OnOutboxMessage()` handlers are discovered on providers, so register `MailerService` and `OrderEmailsHandler` as providers of a `NotificationsModule`. They must be singletons: a handler on a request-scoped provider fails at startup. The handler gets the payload, here the order, and a context as its second argument. The context's `message` holds the message's `id`, `topic`, `key` and `headers`.

Every handler has an inbox, named by `consumer`. Before calling the handler, the local transport checks whether the `order-confirmation-email` consumer has already processed this message id. After the handler succeeds, it records the id. `consumer` is required, and it must stay stable: a new name makes every past message look new.

The inbox has a gap: if the process dies after the email is sent but before the id is recorded, the email is sent again on redelivery. That's acceptable for an email. It isn't for a stock reservation, which lives in the same database as the inbox. The reservation handler closes the gap by recording the id inside its own transaction:

[[CODE:16]]

`ctx.processInTransaction(tx, work)` inserts the inbox record through the handler's transaction, then calls `work` only if this consumer hasn't processed the message yet. Otherwise it skips `work` and returns a result whose `duplicate` flag is `true`. The record and the stock update commit together, so the reservation happens exactly once: a redelivery finds the record and skips the handler, and if `work` throws, both roll back and the retry starts clean. Await it inside the transaction's callback, so the record is written before `COMMIT`; the duplicate check happens inside the call, so a missing `await` can't make it pass. Register the handler in an `InventoryModule`.

| Handler | Behavior | Guarantee |
| --- | --- | --- |
| Default | Skips the handler if its inbox has the id, records the id after the handler succeeds | Once, unless the process dies between the handler finishing and the record, or another instance delivers the same message at the same time |
| Calls `ctx.processInTransaction(tx, work)` | Records the id in the handler's own transaction, with its writes | Exactly once for writes to the same database |
| `inbox: false` | Every delivery runs the handler | At least once |

Both handlers run concurrently for each `order.placed` message. If one of them fails, the publish fails and the whole message is retried. On the retry, each handler that already succeeded is skipped by its inbox.

The relay gives the handlers `publishTimeout` (10 seconds here). If they take longer, the attempt counts as failed and the context's `signal` aborts: pass `ctx.signal` to the calls a handler makes, such as the `signal` option of `fetch()`, so they stop too. A handler that ignores it keeps running, and if the retry reaches the same process while it does, the inbox waits for it instead of running the handler a second time.

#### Publish to the analytics microservice

The API side is already wired. In `AppModule`, `ClientProxyTransport(ANALYTICS_SERVICE)` publishes through the `ClientProxy` that `ClientsModule` registered under that name, and `route` sends every `analytics.*` topic to it. The transport calls `client.emit(topic, envelope)`, the same call you'd make without an outbox. The envelope has the message's `id`, `topic`, `key`, `headers`, `createdAt` and `payload`.

Cancelling an order produces a second analytics event for the same order. Add a `cancelOrder()` method to `OrdersService`, and import `NotFoundException` and `ConflictException` from `@nestjs/common`:

[[CODE:17]]

The orders controller already routes `POST /orders/:id/cancel` to it. The `SELECT ... FOR UPDATE` locks the order's row, so two cancellations of the same order take turns, and the second one sees `cancelled` and answers `409`. Both analytics messages use the order id as their `key`. Messages that share a key are published one at a time, in the order their transactions committed. While `analytics.order.placed` is being retried, `analytics.order.cancelled` waits behind it, so analytics doesn't see a cancellation before the order it cancels. Messages with other keys keep flowing. A key waits only as long as the retries last, though: once a message is dead-lettered (see the next section), the messages behind it go out.

The `order.placed` message for the in-process handlers has no key, on purpose. A key is shared by every message that carries it, whatever the topic or transport. If the email message used the order id as well, a mail outage would hold back the analytics events for that order.

The analytics service is a separate Nest application, and like any service it owns its data: a PostgreSQL database of its own, with its own schema and migrations. It never reads the order API's tables. It records each order event in a table of its own, again the example's data:

`order_events` has one row per order event, and the revenue is the sum of its `amount` column:

| Column | Type | Notes |
| --- | --- | --- |
| `seq` | `bigint`, generated identity | Primary key, in arrival order |
| `order_id` | `text` | Indexed |
| `event` | `text` | `placed` or `cancelled` |
| `amount` | `integer` | The change to revenue, in cents: the order's total when it's placed, minus it when it's cancelled |
| `recorded_at` | `timestamptz` | Defaults to `now()` |

Being an application of its own, it has its own root module, `AppModule`, which registers `OutboxModule` and the store once, as the order API's does. The service only consumes, so the relay is turned off, and the store runs on the service's own database. `OutboxInbox` keeps the service's inbox there, next to `order_events`, so an event and the record that it was processed commit together. The store's tables for messages stay empty, and with the relay off, nothing polls them:

[[CODE:18]]

`OrderStatsService` records an event and returns the revenue so far. It opens a transaction and calls `inbox.processInTransaction(tx, 'analytics', messageId, work)`: the inbox record and the `order_events` row commit together, so a redelivered event changes nothing, even if the service crashes halfway:

[[CODE:19]]

[[CODE:20]]

The events for an order arrive in the order the relay published them, but the handlers are asynchronous: two of them can run at once, and a cancellation could commit before the placement it follows. The controller runs one key's events one at a time, in arrival order, and different orders in parallel.

[[CODE:21]]

`inbox.processInTransaction()` is what an `@OnOutboxMessage()` handler gets with `ctx.processInTransaction()`: exactly once for writes to the consumer's own database. When a consumer's side effect is outside its database, such as an email, use `inbox.process(consumer, id, work)` instead: it skips `work` if the consumer has seen this id, and records it after `work` succeeds.

> warning **Warning** Over TCP, "published" only means the bytes left the order API. If the analytics service crashes after receiving an event but before processing it, the event is lost. For events you can't lose, use a transport whose broker acknowledges receipt: Kafka, RabbitMQ with publisher confirms, or NATS JetStream. `ClientProxyTransport` accepts a `toPacket` option that maps a message to that transport's record, with its own key and headers.

#### Retries and the dead-letter queue

When a publish fails, because a handler threw, the TCP connection was refused, or the publish took longer than `publishTimeout`, the relay reschedules the message:

- Each retry waits longer: 1 s, 2 s, 4 s and so on, capped at `maxDelay` (1 minute here). Each wait is randomized between half and the full value, so retries don't arrive in lockstep.
- Each failure is logged as a warning, with the attempt number and the wait before the next one.
- After `retry.attempts` failures (10 here), the message moves to the dead-letter table with the reason `exhausted` and the error of every attempt.
- A `NonRetryableMessageError` skips the retries. The message is dead-lettered at once with the reason `rejected`. So is any error for which the optional `retry.retryIf(error, attempt, message)` function returns `false`. When several handlers fail, the message is rejected only if all of them threw `NonRetryableMessageError`. Otherwise it's retried, the handlers that succeeded are skipped, and it's rejected once only the permanent failures remain.
- A topic with no `@OnOutboxMessage()` handler is retried, not dead-lettered. During a rolling deploy, an old instance's relay can see a topic that only the new version handles.
- A dead-lettered message no longer holds back its key: the later messages with that key are published without it. Size `retry` so that the outages you expect don't use it up.

The stock handler throws `NonRetryableMessageError` when there isn't enough stock. Retrying won't create stock, so the message goes straight to the dead-letter table, where a person can decide what to do.

`OutboxDeadLetters` lists, inspects, requeues and purges dead letters. The package doesn't mount any HTTP routes, so expose it behind your own guard. The same controller serves the outbox's stats, from the `OutboxMetrics` service built in the next section:

[[CODE:22]]

[[CODE:23]]

> info **Hint** `AdminGuard` is a placeholder. Dead letters contain full payloads, customer data included, so protect these routes with your application's real [authorization](/security/authorization).

`requeue()` moves a dead letter back to the outbox with a fresh retry budget and **the same id**. Consumers that already processed it skip it through their inbox. So after you restock, requeueing the out-of-stock order reserves the stock without sending a second confirmation email. `requeue()` and `purge()` also accept an array of ids, or a filter by `topic`, `key` or `failedBefore`. They refuse an empty filter; pass `all: true` to target every dead letter.

#### Run several instances

Every instance of the order API runs its relay against the same tables, on any number of hosts. The database decides who gets what:

- **Claims.** A relay claims a batch of messages by writing a lease on them for `lease` (30 s), with a random token for that claim. Claims take turns under the store's claim lock, and `SKIP LOCKED` passes over rows another relay is writing, so two relays never get the same message. They publish their batches in parallel.
- **Fencing.** Every later write for a message (published, rescheduled, dead-lettered) must present the lease token, so a relay that stalled past its lease can't overwrite the work of the relay that took over.
- **Order across instances.** A key's messages go out in the order their transactions committed, whichever instance added them: `add()` makes the transactions adding the same key take turns. Keep transactions that add keyed messages short.
- **Exactly-once reservations.** Two deliveries of the same message that run at the same time, on different instances, meet at the inbox's primary key: the second waits for the first transaction, then skips the handler if it committed.
- **Crashes.** If an instance dies while holding a lease, its messages are published by another instance once the lease expires. If it died after publishing but before recording that, the message is published a second time, and the consumers' inboxes drop the duplicate. Nothing is lost with the instance, because nothing lives on it: the messages are rows in the database.
- **Lease budget.** A relay never starts a publish with less than `publishTimeout` (10 s) of lease left. It releases the rest of the batch instead. Keep `publishTimeout` well below `lease`.
- **Clocks.** Leases use the relay's clock, so keep the hosts' clocks synchronized with NTP, well within `lease`.
- **API-only instances.** Start an instance with `OUTBOX_RELAY=off` to make it produce messages without publishing them. `notify()` wakes only the relay of the instance that added the message, so a relay instance picks the messages up within one `pollInterval`.
- **Relay-only workers.** The reverse also works: a worker started with `NestFactory.createApplicationContext(AppModule)` and no HTTP server publishes what the API instances add. The relay's poll timer keeps that process alive until a shutdown hook stops it.

Graceful shutdown needs shutdown hooks:

[[CODE:24]]

On `SIGTERM`, the relay stops claiming and waits for in-flight publishes to finish, each for at most `publishTimeout`. It then releases the leases on messages it claimed but hasn't started, so another instance can take them at once instead of waiting out the lease. This happens in `onModuleDestroy()`, before `ClientsModule` closes the TCP client in `onApplicationShutdown()`.

To watch the outbox, subscribe to `OutboxEvents` and read `relay.stats()`:

[[CODE:25]]

`relay.stats()` reports `lagMs`, how long the longest-waiting message has waited. It grows while a downstream is down, which makes it the number to alert on, along with `deadLetters`. A message scheduled with `delay` doesn't count until it is due. The `published` event carries the message, so `Date.now() - message.createdAt` is the end-to-end publish lag. `OutboxEvents` emits the four events the `switch` counts. `lease-lost` means another relay took a message over while this one was publishing it, so that message may reach its consumers twice. Register `OutboxAdminController`, `AdminGuard` and `OutboxMetrics` in an `OutboxAdminModule`.

Each event is also published on a [`node:diagnostics_channel`](https://nodejs.org/api/diagnostics_channel.html) channel, `nestjs:outbox:published` and so on. Tracing and metrics libraries can subscribe to those without any Nest code, and they see every Nest application in the process.

Catch errors inside your subscribers. RxJS and `diagnostics_channel` both rethrow a subscriber's error as an uncaught exception, which stops the process. The relay has already saved the message's outcome by then, so the message itself is safe.

The example application runs this section against a PostgreSQL server: two relays sharing 20 orders, three instances (one of them API-only) placing and cancelling 12 orders with every message published once and each order's events in order, a transaction that waits for another instance's lock on the same key, an instance that crashes holding a lease, and a graceful shutdown.

#### Try it

Create the two databases, `store` for the order API and `analytics` for the analytics service, and apply each service's own migrations: the order API's create its tables and products from [Prerequisites](/reliability/outbox#prerequisites), and the analytics service's create `order_events`.

Start the analytics service (TCP port 4001) on `analytics`, and the order API (port 3000) on `store`, with `ADMIN_TOKEN=s3cret` in the API's environment. Each logs the store it registered, and the store creates its schema on the first start:

[[CODE:26]]

Place an order:

[[CODE:27]]

The API's log shows the two in-process handlers:

[[CODE:28]]

And the analytics service's log shows the TCP consumer:

[[CODE:29]]

An order for an unknown product fails validation inside the transaction. The response is a `400`, and nothing reaches the outbox:

[[CODE:30]]

Now order two bags of clumping litter (`clumping-litter-10l`), which has one in stock. The API accepts the order, because stock is reserved asynchronously. The confirmation email goes out, and the reservation is dead-lettered on its first attempt:

[[CODE:31]]

[[CODE:32]]

Inspect the dead-letter queue. Without the `x-admin-token` header, the guard answers `403`:

[[CODE:33]]

[[CODE:34]]

The payload is stored as `jsonb`, which keeps its own key order, so it comes back with its keys in a different order than they were added.

Restock, then requeue the message by its id:

[[CODE:35]]

The reservation goes through. The email handler's inbox already has this message id, so no second email is sent:

[[CODE:36]]

Finally, stop the analytics service with `Ctrl+C`, then place an order and cancel it:

[[CODE:37]]

Both analytics messages are pending. `lagMs` grows while the outage lasts, and `retried` counts the failed attempts. `ready` is 0: the placement is waiting for its next retry, and the cancellation is due but waits behind it, because they share a key. The API logs each failed attempt:

[[CODE:38]]

Start the analytics service again. At its next retry, the relay publishes the placement, then the cancellation. The revenue picks up where it was, because it lives in the service's database, not in its memory:

[[CODE:39]]

#### Testing

In an e2e test, run PostgreSQL in-process with [PGlite](https://pglite.dev) and your real migrations, turn the poll loop off, and drive the relay yourself. `relay.runOnce()` claims and processes one batch, and resolves when the batch is done:

[[CODE:40]]

- The outbox, its store, the migrations and the in-process dispatch are real. Only the mailer and the analytics client are stubbed.
- Override the database `DrizzleModule` registers, whose token `getDrizzleToken()` returns, with the PGlite one. The store's factory injects the same token, so the orders and the outbox share the database, as they share the pool in production, and the store creates its schema there when the module initializes. The module still opens its `pg` pool, which never connects.
- The rollback test lets `outbox.add()` write the messages, then fails the transaction. The order and its messages disappear together, and `runOnce()` finds nothing to claim.
- For behavior that depends on time, such as backoff and lease expiry, move `Date.now()` forward with `vi.spyOn(Date, 'now')`. The relay takes the time from it, for itself and for the store, and real timers keep running for sockets and HTTP.
- PGlite has a single connection, so it runs transactions one at a time. Test races between instances against a PostgreSQL server, the same major version as production, as the example does for [several instances](/reliability/outbox#run-several-instances).
- To keep the outbox out of a test, replace the store: `overrideProvider(PostgresOutboxStore).useValue(new InMemoryOutboxStore())`. A plain instance doesn't register itself, so the outbox falls back to its in-memory store, and the store's schema isn't created. It can't join your Drizzle transactions, though: a rolled-back message is still published, and the store logs a warning the first time it gets your transaction.

#### Delivery guarantees

The overall guarantee is **at least once**, with consumer inboxes absorbing the duplicates.

| Situation | Outcome |
| --- | --- |
| The order transaction rolls back | The message never existed and is never published |
| The order transaction commits | Published eventually, or dead-lettered with its error history |
| A relay dies after claiming | Published by another instance once its lease expires |
| A relay dies after publishing, before recording it | Published twice. Inboxes drop the duplicate |
| A publish or handler fails | Retried with backoff, then dead-lettered (`exhausted`) |
| A publish or handler outlives `publishTimeout` | Counted as a failed attempt, and `ctx.signal` aborts. A handler that ignores it keeps running; a retry in the same process waits for it |
| `NonRetryableMessageError`, or `retryIf` returns `false` | Dead-lettered at once (`rejected`) |
| Messages share a `key` | Published in the order they were added. A retrying message holds back the rest of its key |
| A message is dead-lettered | Its key is unblocked, so later messages with that key overtake it |
| TCP, Redis or core NATS transport | "Published" means the write left the process. A consumer crash after that loses the message |

Order within a key is the order in which the store numbered the messages, not their ids: an id comes from its instance's clock, and clocks differ. PostgreSQL runs transactions concurrently, so the store makes the transactions that add messages with the same key take turns, and the numbering follows commit order (see [Keep messages in your database](/reliability/outbox#keep-messages-in-your-database)).
