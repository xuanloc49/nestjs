#### Production checklist

- Register a store on your application's database, on a database server: `PostgresOutboxStore`, `MySqlOutboxStore`, or one of your own ([The store contract](/reliability/outbox#the-store-contract)). Never keep the outbox on the instance itself, in memory or in a file database such as SQLite on its disk: a container's filesystem goes away when the task is replaced, and every message that hadn't been published goes with it. The production guard refuses to start without a store; set `allowInMemoryStorage` only for a process whose messages you can afford to lose.
- Apply the store's migrations before a new version starts, with `npx @nestjs/outbox migrate` or your migration tool, and check them in CI with `npx @nestjs/outbox status`. With `NODE_ENV=production`, the store doesn't migrate at startup: a schema that's behind fails it instead.
- On PostgreSQL, keep the database's default isolation level at READ COMMITTED, the default: the store refuses a stricter one at startup.
- Alert on `lagMs` and `deadLetters` from `relay.stats()`, and on `dead-lettered` events, from `OutboxEvents` or the `nestjs:outbox:dead-lettered` diagnostics channel.
- Size `retry` to how long your downstreams can be down. The package default is 20 attempts, about 30 to 60 minutes in total. This tutorial's 10 attempts capped at 1 minute give up after 2 to 4 minutes, and then a key's later messages overtake the dead-lettered one.
- Keep `consumer` names stable. Inbox entries are keyed by them, so a renamed consumer sees every past message as new.
- Prune inboxes. Nothing calls `OutboxInbox.prune()` for you. Run it from a [cron job](/application/task-scheduling#declarative-cron-jobs), for example `inbox.prune('30d')`, with a window longer than any redelivery, requeues included.
- Keep handlers shorter than `publishTimeout`, and pass `ctx.signal` to the calls they make. A slower handler counts as a failed attempt; leases aren't extended.
- Call `app.enableShutdownHooks()`, so deploys drain the relay instead of leaving messages leased. `DrizzleModule` ends the pool after that, in `onApplicationShutdown()`.
- Protect the dead-letter routes. They expose full payloads.
- Version payloads. A message added by the previous release can still be delivered after a deploy.
- Give each ordered stream its own key, and don't share a key between messages for different transports.
- Keep transactions that call `outbox.add()` short. The per-key lock makes transactions adding messages with the same key take turns. Prisma's interactive transactions time out after 5 seconds by default (`transactionOptions` on the client, or per call).
- On MySQL, run a transaction that calls `outbox.add()` again when it fails with a deadlock (error 1213): MySQL rolled all of it back.
- Size the connection pool for both your requests and the relay: each claim holds a connection for one short transaction.
- Run the contract suites with `concurrent: true` in CI against a store of your own, on a pool, against the database engine and major version you run in production.

#### The store contract

`PostgresOutboxStore` and `MySqlOutboxStore` implement the package's two storage interfaces: `OutboxStore` for the messages and dead letters, and `OutboxInboxStore` for the consumers' inboxes. For another database, implement them in a provider of your own. The JSDoc of each method on those interfaces says what it must do, and which race each rule prevents.

**Registration.** The store is an ordinary singleton provider that calls `registerSource()` on the injectable `OutboxStorage` in its constructor, for the contracts it implements, by name: `messages` and `inbox`. A service that only consumes may register an inbox store alone. The registry checks the shape at once (every method is a function), refuses a second registration unless it passes `replace: true`, and locks when `OutboxModule` initializes, logging the store in use. A request-scoped provider, a provider in a lazy-loaded module, or a lifecycle hook registers too late, and throws.

With nothing registered, the outbox runs on its in-memory store, and says so at startup:

[[CODE:41]]

That is more than a lost-on-restart shortcut. An in-memory store can't join your transaction, so it applies `add()` at once, and warns the first time it receives a transaction handle. In this run, the order's transaction added its message and then failed, and the confirmation email went out anyway:

[[CODE:42]]

With `NODE_ENV=production`, the same application doesn't start:

[[CODE:43]]

`allowInMemoryStorage: true` in the module's options is the deliberate way out, for a single instance that may lose its state.

**Atomicity.** Producers, relays and deliveries race each other through the store. `add()` must number a key's messages in the order their transactions commit, `claim()` must never lease a message to two relays or run ahead of an older message of its key, a relay's later writes must apply only while its lease holds, and two deliveries of one message must meet at `recordInbox()`. So every method that changes state is one conditional statement, or one transaction with the right lock, never a read followed by a write. `add()` and `recordInbox()` receive your transaction object untouched: they must write through it, and refuse anything that isn't one, such as the database itself, with `OutboxTransactionRequiredError`.

**Test it** with the suites from `@nestjs/outbox/testing`. `outboxStoreContract()` and `outboxInboxStoreContract()` return the contracts as test cases for any test runner: each case is a `name` and a `run()` function that throws on failure. The tutorial's tests run them against `PostgresOutboxStore` through Drizzle, as you would against yours, with a function that returns the store on emptied tables, a way to open one of your transactions, and `notATransaction`, a handle the store must refuse:

[[CODE:44]]

`concurrent: true` adds the races a naive store fails: producers of a key whose transactions overlap, relays claiming side by side, producers and relays racing, a stale relay's writes racing a takeover, and two deliveries of one message. On PGlite they pass one transaction at a time, so run them against a server with a pool too, where the transactions really overlap, on the database engine and major version you run in production. The tutorial runs both suites through each of its clients: Drizzle on PGlite and on PostgreSQL, TypeORM and Prisma on PostgreSQL, and Drizzle on MySQL, against `MySqlOutboxStore`. The package's own tests run them against stores written by hand with Drizzle, TypeORM and Prisma too, as the proof that a store written against the interfaces passes them.

Other packages' stores can live elsewhere: the idempotency store fits Redis. The outbox's store can't, because its messages must commit with your rows, in your database.

#### Using BullMQ on Postgres instead

BullMQ 6 has a PostgreSQL backend, so it's fair to ask whether its job table could be the outbox. The package's research into BullMQ 6.3.x (from reading its published code, not a live run) says: not today.

- `Queue.add()` always runs on BullMQ's own connection pool, in autocommit mode. The backend interface deliberately exposes no connection or transaction type, so an `add()` can't join the transaction that inserts your order.
- The enqueue itself is one SQL function, `bullmq.add_job(...)`. Calling it on your own transaction would be atomic, but the function is internal, its signature changes with BullMQ's schema migrations, and every transaction that calls it would take Postgres's global NOTIFY lock at commit.
- `@nestjs/bullmq` 12.0.0 can't select the Postgres backend for a single queue. The only way is BullMQ's process-wide `setDefaultBackendFactory()`.

What's needed is an upstream option to run `add()` on a caller-supplied client (so the job commits with the order), plus a backend option in `@nestjs/bullmq`. With both, the job table would be the outbox, and BullMQ's workers would provide the claims, retries and failed set with no relay in between. Until then, use this outbox and publish to BullMQ from an `OutboxTransport` that calls `queue.add(topic, payload)` with the outbox message `id` as the `jobId`, so a republished message is ignored while the job still exists.

#### Example

A working example is available in the [37-outbox sample](https://github.com/nestjs/nest/tree/master/sample/37-outbox): the order API on PostgreSQL with Drizzle, its in-process handlers, the analytics microservice with a database of its own, the dead-letter admin API, and the tests.

#### Reference

##### Module options

`OutboxModule.forRoot()` takes these options. `forRootAsync()` takes `transports` classes, `imports` and `isGlobal` at its top level, and the rest from `useFactory`, `useClass` or `useExisting` (a class implementing `OutboxOptionsFactory`), as in [Register the outbox](/reliability/outbox#register-the-outbox). The options token is `OUTBOX_MODULE_OPTIONS`. The store isn't an option: register it as a provider, as in [Keep messages in your database](/reliability/outbox#keep-messages-in-your-database). Durations are milliseconds, or strings such as `'30s'` and `'1m'`.

| Option | Default | Meaning |
| --- | --- | --- |
| `transports` | None | Named `OutboxTransport` classes or instances. `local`, the `@OnOutboxMessage()` handlers, is built in and reserved |
| `imports` | None | Modules whose exports the transport classes inject |
| `route` | The only destination | `(message) => name`: the one transport a message goes to. Required with handlers and transports, or several transports |
| `relay.enabled` | `true` | `false` in instances that only produce or only consume |
| `relay.pollInterval` | `'1s'` | The wait between polls when idle |
| `relay.batchSize` | `100` | Messages per claim |
| `relay.lease` | `'30s'` | How long a claim is exclusive |
| `relay.concurrency` | `10` | Key groups published in parallel within a batch |
| `relay.publishTimeout` | A third of `lease` | A slower publish counts as a failed attempt, and its `signal` aborts |
| `retry.attempts` | `20` | Total attempts, including the first, before the message is dead-lettered. `retry: 5` means 5 attempts; `retry: false`, a single attempt |
| `retry.backoff` | `'1s'` doubling up to `'5m'`, equal jitter | An object with `delay`, `factor`, `maxDelay` and `jitter` (`'equal'`, `'full'` or `'none'`), or a function `(attempt, error, message) => duration` |
| `retry.retryIf` | Every error | `(error, attempt, message) => boolean`: `false` dead-letters the message at once |
| `allowInMemoryStorage` | `false` | With `NODE_ENV=production` and no registered store, startup fails; `true` runs on the in-memory store anyway |
| `isGlobal` | `true` | Registers the module globally |

##### Stores

`new PostgresOutboxStore(options, outboxStorage)`, from `@nestjs/outbox/postgres`, and `new MySqlOutboxStore(options, outboxStorage)`, from `@nestjs/outbox/mysql`, take these options. Without `outboxStorage`, the store registers nowhere, which suits a script or a test.

| Option | Default | Meaning |
| --- | --- | --- |
| `executor` | Required | How the store reaches the database: one of the executors below, from the same entry point as the store. The other dialect's doesn't compile |
| `schema` | `'nest_outbox'` | On PostgreSQL, the schema of its tables, which its first migration creates: letters, digits and underscores, not starting with a digit, at most 63 characters. On MySQL, the prefix of its tables in the connection's database: lowercase letters, digits and underscores, not starting with a digit, at most 40 characters |
| `migrate` | `true`, except with `NODE_ENV=production` | Apply the pending migrations when the application starts. With `false`, startup fails with an `OutboxSchemaError` while the schema is behind |

Each executor takes your database client, and its own kind of transaction object, which `outbox.add()` and `processInTransaction()` then take:

| Executor | Takes | Transaction object |
| --- | --- | --- |
| `fromDrizzle(db)` | A Drizzle database: on PostgreSQL, whichever its driver; on MySQL, `mysql2` | The `tx` that `db.transaction()` hands its callback |
| `fromTypeOrm(dataSource)` | A `DataSource` of type `postgres` or `mysql` | The `EntityManager` that `dataSource.transaction()` hands its callback, or a `QueryRunner` after `startTransaction()` |
| `fromPrisma(prisma, options)` | A Prisma client, through a driver adapter such as `@prisma/adapter-pg`, or `@prisma/adapter-mariadb` for MySQL. `maxWait` (default `'10s'`) and `timeout` (default `'1m'`) limit the store's own transactions | The transaction client that `prisma.$transaction()` hands its callback |
| `fromKysely(db)` | A `Kysely` instance with a PostgreSQL or MySQL dialect | The transaction that `db.transaction().execute()` hands its callback |
| `fromPg(pool)` | PostgreSQL: a node-postgres `Pool`, or a connected `Client` | A client, such as one from `pool.connect()`, after `BEGIN` |
| `fromMysql2(pool)` | MySQL: a `mysql2/promise` pool, or a connection | A connection, such as one from `pool.getConnection()`, after `beginTransaction()` |

The store's `migrate()` method applies the pending migrations at once, whatever the `migrate` option says, and resolves with the versions it applied. The static `migrationSql()` returns their SQL, with the bookkeeping, and `MySqlOutboxStore.migrationStatements()` returns the same statements, one per string. They take the `schema`, the versions to go `from` (default `0`, a new database) and `to` (default: the one the package needs), and `migrationSql()` takes `statementBreakpoints` too. From version 0 on PostgreSQL, the SQL starts with `CREATE SCHEMA IF NOT EXISTS`, which needs the CREATE privilege on the database: leave it out if someone created the schema for you. The static `schemaVersion` is the version the package needs.

The command line, `npx @nestjs/outbox`, takes `--url` (default `DATABASE_URL`) and `--schema` (default `nest_outbox`). A `mysql://` URL picks `MySqlOutboxStore`'s migrations, and needs `mysql2` installed:

| Command | What it does |
| --- | --- |
| `migrate` | Applies the pending migrations, as `migrate: true` does at startup |
| `status` | Prints the schema's version and the one the package needs, and exits with 1 while the schema is behind |
| `sql` | Prints the SQL of `migrationSql()`, from `--from` to `--to`, without a database: PostgreSQL's, or MySQL's with `--dialect mysql`. `--statement-breakpoints` separates the statements for a drizzle-kit custom migration |

On MySQL, the store needs MySQL 8.4 LTS or 9.x with a strict `sql_mode`, MySQL's default: a lax `sql_mode`, or MariaDB, fails the startup.

##### Messages and handlers

A message passed to `outbox.add(tx, message)` ([Save the order and its messages in one transaction](/reliability/outbox#save-the-order-and-its-messages-in-one-transaction)) has these fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `topic` | Yes | What `route` and the handlers match on |
| `payload` | Yes | Serialized to JSON when `add()` runs |
| `key` | No | The ordering key: messages that share it are published one at a time, in commit order |
| `headers` | No | String headers, passed to transports |
| `id` | No | Your own unique id. The default is a UUIDv7; consumers deduplicate by it |
| `delay` or `availableAt` | No | Publish no earlier than this long from now, or than this point in time. Not both |

- `@OnOutboxMessage(topic, options)` takes `consumer` (required: the name of the handler's inbox) and `inbox` (default `true`; `false` runs every delivery). [Handle order.placed in-process](/reliability/outbox#handle-orderplaced-in-process)
- A handler's context has `message`, `consumer`, `attempt`, `signal` and `processInTransaction(tx, work)`.
- `ClientProxyTransport(token, options)` emits the topic with an envelope of `id`, `topic`, `key`, `headers`, `createdAt` and `payload` (`OutboxEnvelope`). Its `toPacket(message, envelope)` option returns your own `pattern` and `data`. [Publish to the analytics microservice](/reliability/outbox#publish-to-the-analytics-microservice)

##### Services

| Service | Methods |
| --- | --- |
| `Outbox` | `add(tx, messages)`, `notify()` |
| `OutboxRelay` | `stats()`: `pending`, `ready`, `leased`, `deadLetters`, `oldestDueAt`, `lagMs`, `inFlight`. `runOnce()`: `claimed`, `published`, `retried`, `deadLettered`, `released`, `leaseLost`. Also `notify()`, `start()` and `stop()` |
| `OutboxDeadLetters` | `list(query)` (by `topic`, `key`, `limit`, `offset`; newest first), `get(id)`, `requeue(target)`, `purge(target)`. A target is an id, an array of ids, or a filter by `ids`, `topic`, `key`, `failedBefore`, or `all: true`. [Retries and the dead-letter queue](/reliability/outbox#retries-and-the-dead-letter-queue) |
| `OutboxInbox` | `process(consumer, id, work)`, `processInTransaction(tx, consumer, id, work)`, `prune(olderThan)`. Both `process` methods resolve `duplicate`, and `result` when `work` ran |

##### Events

`OutboxEvents.events$` emits each event, and publishes it on its `node:diagnostics_channel` channel. Every payload has `type` and the `message`. [Run several instances](/reliability/outbox#run-several-instances) counts them. Catch errors inside your subscribers: RxJS and `diagnostics_channel` both rethrow a subscriber's error as an uncaught exception.

| Event | Channel | Other fields | When |
| --- | --- | --- | --- |
| `published` | `nestjs:outbox:published` | `transport`, `durationMs` | A transport accepted the message |
| `retry-scheduled` | `nestjs:outbox:retry-scheduled` | `transport`, `error`, `attempt`, `delayMs` | A publish failed and will be retried |
| `dead-lettered` | `nestjs:outbox:dead-lettered` | `transport`, `error`, `attempt`, `reason` | The message moved to the dead letters. Alert on it |
| `lease-lost` | `nestjs:outbox:lease-lost` | None | Another relay took the message over mid-publish, so it may be published twice |

A dead letter's `reason` is `exhausted` (the retries ran out) or `rejected` (a `NonRetryableMessageError`, or `retryIf` returned `false`).

##### Errors

None of them carries an HTTP status. `OutboxError` is the base class of the four that the package throws.

| Error | Raised when |
| --- | --- |
| `OutboxTransactionRequiredError` | `add()` or `processInTransaction()` got no transaction handle, or a store refused a handle that isn't a transaction |
| `OutboxPublishTimeoutError` | A publish outlived `relay.publishTimeout` (`timeoutMs`). Counted as a failed attempt |
| `OutboxNoHandlerError` | No `@OnOutboxMessage()` handler for the topic in this process (`topic`). Retried |
| `OutboxSchemaError` | The store's schema is behind the package's migrations while `migrate` is off, or applying them failed (`cause`): startup and every call fail until it's fixed. With the `schema`, its `version` and the `requiredVersion`. From `@nestjs/outbox/postgres` and `@nestjs/outbox/mysql` |
| `NonRetryableMessageError` | You throw it from a handler or transport to dead-letter the message without retrying |
