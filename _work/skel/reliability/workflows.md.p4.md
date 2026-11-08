#### With CQRS

If your application follows the [CQRS recipe](/recipes/cqrs), command handlers publish events, and event handlers and sagas react to them. They react in memory: an event published just before the process stops never reaches them, and a saga that waits for a second event forgets the first one on a restart. The `@nestjs/workflows/cqrs` entry point lets the events themselves start and signal workflows, durably, while your code keeps executing commands and publishing events. It works with `@nestjs/cqrs` 11 and later, registered with `CqrsModule.forRoot()` as in the recipe.

##### Map events to workflows

Here the fulfilment starts when the order is placed and wakes when the carrier reports the delivery, as before, but the workflow client calls are gone from the application code. Import `WorkflowsCqrsModule` next to `CqrsModule` and `WorkflowsModule`:

[[CODE:51]]

Then map the events on the workflow class. `@StartOn()` starts the workflow when an event is published, and `@SignalOn()` sends one of its signals:

[[CODE:52]]

`@StartOn()`'s `id` is required. It derives the instance id from the business key, as `start()` does, so an event published twice finds the instance the first one started. It also takes `start()`'s `priority`, `concurrencyKey` and `rateLimitKey`, each as a value or a function of the event: here, express orders go first, as before. `@SignalOn()`'s `id` is optional, and becomes the signal's `id`: a delivery event published again, say for the carrier's retried webhook, stores no second signal. `input` defaults to the event itself, and a signal's `payload` too. TypeScript checks the input against `run()` and the payload against the signal's type. The events are plain classes, such as `OrderPlacedEvent` with a `readonly order: Order` constructor parameter.

The command handler saves the order and publishes the event in one transaction:

[[CODE:53]]

The second argument of `publish()` and `publishAll()` is CQRS's dispatcher context. `WorkflowsCqrsModule` reads its `transaction` property and passes it to `start()` and `signal()`, so the instance is created through your transaction, exactly as with the `transaction` option. With TypeORM, the dispatcher context carries the `EntityManager` that `dataSource.transaction()` hands its callback, under the same `transaction` property. `publish()` resolves once the workflows are started and signalled, and only then does the event reach your event handlers and sagas. Events that no workflow maps go straight through, unchanged. The controllers execute the commands: `POST /orders` executes `PlaceOrderCommand`, and the carrier's webhook executes `MarkDeliveredCommand`, whose `MarkDeliveredHandler` does the same for the delivery: it updates the order's status and publishes `OrderDeliveredEvent` in one transaction, so the status and the signal commit together.

The module wraps whatever publisher the event bus has, so a publisher you set with `CqrsModule.forRoot()`'s `eventPublisher` option (a message broker, for example) still receives every event, after the workflows. Replacing `EventBus.publisher` after startup would bypass the workflows, so startup fails if something does. It also fails when a workflow maps events but `WorkflowsCqrsModule` isn't imported, when one class maps the same event twice, or when `@StartOn()` gives a key to a workflow without a limit per key. When two versions of a workflow are registered, the highest version's `@StartOn()` decides what starts, and a signal reaches the waiting instances of every version, sent once, so their `@SignalOn()` declarations must agree on its payload and `id`: `publish()` rejects when they don't.

The mappings live on the workflow classes, so every process that publishes mapped events registers them, including one that runs no workflows, such as an API that only places orders. Register the classes and the store there as usual, and pass `worker: false` to `WorkflowsModule.forRoot()`: the process starts and signals the workflows, and the worker processes execute them. A process that imports `WorkflowsCqrsModule` but registers no workflow that maps an event starts and signals nothing, and logs a warning at startup saying so.

##### Execute commands from steps

A step can execute commands. Pass the step's idempotency key along with the command, and have the handler hand it to the system it calls:

[[CODE:54]]

`ChargePaymentHandler` calls `PaymentsService.charge()` with the key, so a retried step never charges twice, and the command's result is journaled like any step's. A step can publish events and send signals too. It runs at least once, so an event published from a step may be published again. A mapped start finds its instance, and so does a `start()` without an `id` in a step: it gets an id derived from the step's `idempotencyKey`, the workflow's name and its place among the step's starts of that workflow, and a repeat returns the instance as first started, input included. A signal sent from inside a step, directly or through a mapped event, is stored once: without an `id` of its own, it gets one derived from the step's `idempotencyKey` and its place among the step's signals with the same name and key. Send those in a fixed order. A step that sends several with one name and key concurrently should give each its own `id`.

##### What each way of publishing guarantees

The guarantee depends on how, and when, the event is published:

| How the event is published | The workflow's start or signal | If the process dies or a write fails |
| --- | --- | --- |
| In your transaction, with the transaction in the dispatcher context | Commits with your writes, or not at all | Nothing is half done. A failed start or signal rejects `publish()`, and your transaction rolls back |
| An aggregate's events, from `commit()` with the transaction in the dispatcher context (`@nestjs/cqrs` 12.1 or later), or with `publishAll()` in your transaction, as shown below | Commits with your writes, or not at all | As above: a failed start or signal rejects `commit()` or `publishAll()`, and your transaction rolls back |
| After your transaction commits | Written before `publish()` resolves | A crash between your commit and the publish loses it. Publish again from a reconciliation job: the start's `id` makes that safe, and so does a signal's, if `@SignalOn()` sets one |
| From `commit()` without a transaction, of an aggregate merged with `EventPublisher` | Written outside your transaction, in the background unless you await `commit()` (12.1 or later) | Lost on a crash while nothing waits for it, and left behind when your transaction rolls back. Failures go to the `UnhandledExceptionBus` and the log, and the module logs a warning once per event class |
| From `commit()` without a transaction, of a `@Publishable()` aggregate | Written outside your transaction, in the background unless you await `commit()` (12.1 or later) | Lost on a crash while nothing waits for it, and left behind when your transaction rolls back. Unawaited, a failure is an unhandled promise rejection, which stops Node.js by default. Nothing tells it apart from a plain `publish()`, so there's no warning |
| From a workflow step | Once, however often the step runs | A retried step starts nothing new, and stores no second signal |

An aggregate merged with `EventPublisher.mergeObjectContext()` or `mergeClassContext()`, or decorated with `@Publishable()`, publishes its events from `commit()`. With `@nestjs/cqrs` 12.1 or later, `commit()` takes a dispatcher context, as `publish()` does, and returns what the event bus returns. Pass it your transaction and await it in the command handler's transaction: the aggregate's events then start and signal workflows in that transaction, and `commit()` rejects when a start or signal fails, which rolls the transaction back:

[[CODE:55]]

`commit()` clears the aggregate's events when it hands them over, before the workflows are written, so after a failure, run the command again with a freshly loaded aggregate.

Without a dispatcher context, `commit()` publishes outside your transaction: the workflows still start, but a rollback leaves them behind, and a crash before they're written loses them. Don't let it publish events that start or signal workflows. With `@nestjs/cqrs` 12.0 or earlier, `commit()` takes no context and returns nothing to wait for, so publish the aggregate's events yourself, in the command handler's transaction, and then clear them:

[[CODE:56]]

The module tells you when a mapped event arrives from a merged aggregate's `commit()` without a transaction: the first time, it logs a warning naming the event class. A `@Publishable()` aggregate's events arrive without any dispatcher context, like an ordinary `publish()` call, so they get no warning.

Your event handlers and sagas still receive every event, in memory, after the workflows. Inside a transaction they run before it commits, as they always did, so they can react to an event whose transaction then rolls back. A saga that turns one event into one command can stay a saga. A saga that remembers events, such as one that waits for the payment after the order and gives up after an hour, is a workflow in disguise: start the workflow from the first event, map the others to signals, and let `waitForSignal()` with a `timeout` do the waiting, durably.

#### Prepare for production

##### Keep journals short

Every execution loads the instance's whole journal and replays `run()` from the top. A process with a fixed number of steps keeps its journal small, but a loop with a step or a sleep per round adds entries for as long as it runs, and each execution gets slower. The module warns when a journal reaches 1,000 entries or 1 MB: once per instance, when it crosses the line, in the log and as a `journal-large` event. Once it holds 10,000 entries or 10 MB, the instance fails before it records another one: its compensations run, which may still record theirs, and it ends as `failed` with a `WorkflowJournalLimitError`. The module's `journal` option moves both lines. Size them to your longest regular workflow with room to spare, and set a limit to `Infinity` to turn it off:

[[CODE:57]]

A process that goes on for good, such as a monthly litter subscription, continues in a new instance instead. After a year of deliveries, its last step starts the next year's instance, and the current one completes:

[[CODE:58]]

The step starts the next instance once: a retried step finds the instance it started. The new instance has a fresh journal and its own id, so the finished year stays readable until retention purges it. Continuing under the same id would need every store to replace a journal in place, under the worker's lease; a new id needs nothing new from the store. When each round stands on its own, a schedule is simpler still: it starts an instance per occurrence, each with a journal of its own, as [Run workflows on a schedule](/reliability/workflows#run-workflows-on-a-schedule) shows.

##### Encrypt what workflows store

The store keeps what your workflows handle: orders, charges, deliveries. To keep that unreadable to whoever reads the database or its backups, give the module a **payload codec**. `AesGcmPayloadCodec` encrypts with AES-256-GCM, under keys from your secret manager. Create it in the module's factory, which runs at startup:

[[CODE:59]]

A key is 32 random bytes in base64 (`openssl rand -base64 32`), under an id of your choice. A key that is missing (an unset environment variable), isn't base64 or isn't 32 bytes fails the startup, with an error that names it.

- **What it encrypts**: everything that holds your data. Inputs and outputs, step results and checkpoints, signal payloads, custom statuses, cancel reasons, schedules' inputs, and the messages and stacks of errors. Each payload is encrypted under a key derived for it, with where it's stored as authenticated data, so a payload that was changed, or moved to another instance or field, fails to decrypt instead of being read. Payloads of 1 KiB or more are compressed first. If payloads mix secrets with data an attacker chooses, and attackers can see stored sizes, turn that off with `compress: false`.
- **What stays readable**, because the store matches, filters, orders or counts on it: ids, workflow names and versions, statuses, signal names and keys, concurrency and rate-limit keys, priorities, links to parents and schedules, journal entry names, and all times. Errors keep their names, such as `StepFailedError`. So pick ids and keys that say nothing sensitive: `order-71e1973d`, not an email address. Here the concurrency key is the customer's id, readable in `concurrency_key`.
- **Stored form**: `$wf1:aes-256-gcm:2026-09.` followed by the ciphertext, a string in the same JSON columns, so the store needs no change.

**Rotating keys.** Add a key, and make it `current`. A payload decrypts with the key that encrypted it, and everything written from then on uses the current one. Nothing is re-encrypted in bulk: payloads are rewritten as instances progress, and old ones go with purges. So keep a key listed while anything it encrypted may still be read: unfinished instances, signals not purged yet, and schedules saved under it. A declared schedule's input is saved again under the current key at startup and every minute, but an upserted one's only by its next `upsert()`: `pause()` and `resume()` keep it as stored.

[[CODE:60]]

An instance whose payloads need a key that isn't listed can't be read: `getStatus()` throws an error that names the key, `list()` shows the instance without its payloads, and workers leave it alone until the key is back, then run it.

Adding a codec breaks no running instance: payloads stored before it are read as they are, and new writes are encrypted. That is also where the protection ends. Someone who can write to the database can replace an encrypted payload with a plain one, and have it read: the codec protects what it encoded against reading and tampering, not the database against its writers.

A codec of your own implements `WorkflowPayloadCodec`: an `id`, stored with each payload, and `encode()` and `decode()`, which receive the value and where it's stored. Pass its class to `codec` to have Nest create it, with its dependencies from global modules, such as a KMS client. To replace a codec, list the new one first and the old one after it: the first one encodes, and each payload is decoded by the codec whose id it carries.

##### Production checklist

- Pass the `idempotencyKey` to every side effect, including compensations. Steps run at least once.
- Give signals an `id` when their sender can run twice, such as a webhook the sender retries or a message consumer. Signals sent from a step get one automatically.
- Call `enableShutdownHooks()`, and keep `shutdownTimeout` below your platform's grace period (30 seconds by default on Kubernetes).
- Choose `leaseDuration` deliberately. It's how long a crashed process's instances wait before another process takes over, and a process whose event loop stalls for longer loses its instances. Lease expiry compares timestamps written by different hosts, so keep their clocks in sync (NTP) and `leaseDuration` well above any skew between them.
- Register a store on your database: `PostgresWorkflowStore`, `MySqlWorkflowStore`, or one of your own. In memory, or in a file on the container's disk, state dies with the instance: the in-memory default loses every running order on restart, and startup refuses it in production. Run the contract suite against a store of your own in CI, on its database, with `concurrent: true`.
- Apply the store's migrations before a new version starts, with `npx @nestjs/workflows migrate` or your migration tool, and check them in CI with `npx @nestjs/workflows status`. With `NODE_ENV=production`, the store doesn't migrate at startup: a schema that's behind fails it instead.
- Run as many workers as you like, on as many hosts. Size the connection pool for them: each running instance renews its lease and writes its journal through the pool, and each poll holds a connection for its claim.
- Start workflows in the transaction that writes their business rows (`transaction: tx`, or the `EntityManager` with TypeORM), so a crash between the two can't leave an order that nothing fulfils. Pass the transaction, never the root database. With CQRS, publish the events inside that transaction, with the transaction in the dispatcher context.
- Keep transactions that send signals short: signals and the suspensions that register waits queue behind them. On PostgreSQL, keep them READ COMMITTED, and the database's default isolation too: the store refuses a stricter one. On MySQL, keep them REPEATABLE READ or READ COMMITTED, and run a transaction again when it fails with a deadlock (error 1213).
- Verify webhook signatures, and return `2xx` only after the transaction with the signal has committed.
- Alert on instances that need a person. `compensation_failed` means an undo gave up halfway, and a `failed` instance with `WorkflowNonDeterminismError` means a deploy broke replay. `WorkflowClient.list()` finds them, and [What each status means](/reliability/workflows#what-each-status-means) says what to do with each: `retry()` once the cause is fixed, or `delete()`. For logs and metrics, subscribe to `WorkflowEvents.events$`, or to the `nestjs:workflows:*` diagnostics channels that tracing tools read without Nest; [Events](/reliability/workflows#events) maps them onto a trace.
- Mark your point of no return with `ctx.commit()`. Before it, every failure and cancel undoes the completed steps.
- Purge finished instances every night with `purge()`, on one instance of the application, as [Purge finished instances](/reliability/workflows#purge-finished-instances) shows. Keep its `olderThan` longer than any sender's redelivery window: a signal's `id` deduplicates only as long as the signal is stored.
- Keep journals short: bound loops, and continue one that never ends in a new instance ([Keep journals short](/reliability/workflows#keep-journals-short)). Give a process that must give up at some point a run timeout ([Time out the whole workflow](/reliability/workflows#time-out-the-whole-workflow)).
- Size concurrency and rate limits to what the steps call, and deploy a change to them to every process: each applies the limits of the code it runs. Once some instances have a priority, give the rest one too, since instances without one go first.
- Deploy a declared schedule to every process that registers its workflow: only workers whose code declares it start its occurrences. A schedule that a deploy drops, or whose workflow it removes, keeps starting on the processes of the old code, and goes about five minutes after the last of them stopped. Set `missed` for work that mustn't be skipped when no worker is up at its time. If processes of other code share the database, don't leave a schedule without a worker whose code declares it for five minutes: they delete it, and it starts over once one starts.
- Encrypt what the store keeps with a codec, with keys from your secret manager ([Encrypt what workflows store](/reliability/workflows#encrypt-what-workflows-store)). Keep an old key listed while anything it encrypted may be read, and pick ids and keys that say nothing sensitive: they stay readable.
