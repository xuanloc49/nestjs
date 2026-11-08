#### Reference

##### Module options

`WorkflowsModule.forRoot()` takes these options; `forRootAsync()` takes them from `useFactory`, `useClass` or `useExisting` (a class implementing `WorkflowsOptionsFactory`). The options token is `WORKFLOWS_MODULE_OPTIONS`. The store isn't an option: register it with `WorkflowStorage`, as in [Keep workflows in your database](/reliability/workflows#keep-workflows-in-your-database).

| Option | Default | Meaning |
| --- | --- | --- |
| `worker.enabled` | `true` | Run the polling loop. `worker: false` is shorthand for `enabled: false`: the process starts, signals and inspects workflows, and `WorkflowWorker.drain()` runs due instances on demand |
| `worker.id` | `hostname:pid:random` | The worker's name, shown as the instance's `leaseOwner` |
| `worker.concurrency` | `10` | Instances this process executes at once |
| `worker.pollInterval` | `'1s'` | How often to look for due instances. A local `start()` or `signal()` wakes the loop at once |
| `worker.leaseDuration` | `'30s'` | How long a claim is valid without a renewal, so how long a crashed process keeps its instances |
| `worker.heartbeatInterval` | A third of `leaseDuration` | How often a running instance renews its lease |
| `worker.shutdownTimeout` | `'10s'` | How long shutdown waits for running executions before handing them back |
| `retry` | 3 attempts, `'1s'` doubling up to `'5m'`, no jitter | The default for every step. See the retry fields below |
| `journal.warnEntries`, `journal.warnBytes` | `1000`, `1000000` | At either, log a warning and emit `journal-large`, once per instance ([Keep journals short](/reliability/workflows#keep-journals-short)) |
| `journal.maxEntries`, `journal.maxBytes` | `10000`, `10000000` | At either, fail the instance with a `WorkflowJournalLimitError` before it records another entry. `Infinity` turns a check off |
| `clock` | The system clock | A `WorkflowClock`. Tests pass a `ManualWorkflowClock` ([Test with a manual clock](/reliability/workflows#test-with-a-manual-clock)) |
| `allowInMemoryStorage` | `false` | With `NODE_ENV=production` and no registered store, startup fails; `true` runs on the in-memory store anyway |
| `codec` | None | A `WorkflowPayloadCodec`, its class, or a list of them: the first encodes, and each decodes the payloads it encoded ([Encrypt what workflows store](/reliability/workflows#encrypt-what-workflows-store)) |
| `isGlobal` | `true` | Registers the module globally. Top level of `forRoot()` and `forRootAsync()` |

A `retry` option (the module's, a step's `retry` or its `compensateRetry`) is a number of attempts, `false` for a single attempt, or an object with these fields. A step's `retry` merges over the module's field by field.

| Field | Default | Meaning |
| --- | --- | --- |
| `attempts` | `3` | Total attempts, including the first |
| `backoff.delay` | `'1s'` | The wait before the first retry |
| `backoff.factor` | `2` | Growth per retry; `1` keeps the wait constant |
| `backoff.maxDelay` | `'5m'` | The cap for a single wait |
| `backoff.jitter` | `'none'` | `'full'` (zero to the wait), `'equal'` (half to all of it) or `'none'` |
| `retryIf` | Every error | `(error, attempt) => boolean`: `false` fails the step at once |

`backoff` can also be a function, `(attempt, error) => duration`. A `NonRetryableStepError` never retries.

##### PostgreSQL store

`new PostgresWorkflowStore(options, workflowStorage)`, from `@nestjs/workflows/postgres`, takes these options:

| Option | Default | Meaning |
| --- | --- | --- |
| `executor` | Required | How the store reaches the database: `fromDrizzle(db)`, `fromTypeOrm(dataSource)`, `fromPg(pool)`, `fromPrisma(prisma, options)` or `fromKysely(db)` |
| `schema` | `'nest_workflows'` | The schema of its tables, which its first migration creates. Letters, digits and underscores, not starting with a digit, at most 63 characters |
| `migrate` | `true`, except with `NODE_ENV=production` | Apply the pending migrations when the application starts. With `false`, startup fails with a `WorkflowSchemaError` while the schema is behind |

Each executor takes your database client, and its own kind of transaction object, which `start()` and `signal()` then take as `transaction`:

| Executor | Takes | Transaction object |
| --- | --- | --- |
| `fromDrizzle(db)` | A Drizzle PostgreSQL database, whichever its driver | The `tx` that `db.transaction()` hands its callback |
| `fromTypeOrm(dataSource)` | A `DataSource` of type `postgres`, or its `manager` | The `EntityManager` that `dataSource.transaction()` hands its callback, or a `QueryRunner` after `startTransaction()` |
| `fromPg(pool)` | A node-postgres `Pool`, or a connected `Client` | A client, such as one from `pool.connect()`, after `BEGIN` |
| `fromPrisma(prisma, options)` | A Prisma client on PostgreSQL, through a driver adapter such as `@prisma/adapter-pg` or Prisma's engine. `maxWait` (default `'10s'`) and `timeout` (default `'1m'`) limit the store's own transactions | The transaction client that `prisma.$transaction()` hands its callback |
| `fromKysely(db)` | A `Kysely` instance with a PostgreSQL dialect. The store's statements skip its plugins | The transaction that `db.transaction().execute()` hands its callback, or a controlled transaction |

The store's `migrate()` method applies the pending migrations at once, whatever the `migrate` option says, and resolves with the versions it applied. `PostgresWorkflowStore.migrationSql()` returns their SQL, with the bookkeeping. Its options are the `schema`, the versions to go `from` (default `0`, a new database) and `to` (default: the one the package needs), and `statementBreakpoints`, which separates the statements with drizzle-kit's `--> statement-breakpoint` lines. From version 0, it starts with `CREATE SCHEMA IF NOT EXISTS`, which needs the CREATE privilege on the database: leave it out if someone created the schema for you. `PostgresWorkflowStore.schemaVersion` is the version the package needs. A schema's own version is the highest in its `migrations` table.

##### MySQL store

`new MySqlWorkflowStore(options, workflowStorage)`, from `@nestjs/workflows/mysql`, runs on MySQL 8.4 LTS and 9.x, and takes these options:

| Option | Default | Meaning |
| --- | --- | --- |
| `executor` | Required | How the store reaches the database: `fromDrizzle(db)`, `fromTypeOrm(dataSource)`, `fromMysql2(pool)`, `fromPrisma(prisma, options)` or `fromKysely(db)`, from `@nestjs/workflows/mysql` |
| `schema` | `'nest_workflows'` | The start of its tables' names (`nest_workflows_instances`...), in the connection's database. Lowercase letters, digits and underscores, not starting with a digit, at most 40 characters |
| `migrate` | `true`, except with `NODE_ENV=production` | Apply the pending migrations when the application starts, one statement at a time. With `false`, startup fails with a `WorkflowSchemaError` while the tables are behind |

| Executor | Takes | Transaction object |
| --- | --- | --- |
| `fromDrizzle(db)` | A Drizzle MySQL database (`drizzle-orm/mysql2`) | The `tx` that `db.transaction()` hands its callback |
| `fromTypeOrm(dataSource)` | A `DataSource` of type `mysql`, or its `manager` | The `EntityManager` that `dataSource.transaction()` hands its callback, or a `QueryRunner` after `startTransaction()` |
| `fromMysql2(pool)` | A mysql2 pool, or a connection | A connection, such as one from `pool.getConnection()`, after `beginTransaction()` |
| `fromPrisma(prisma, options)` | A Prisma client on MySQL, through `@prisma/adapter-mariadb`. `maxWait` (default `'10s'`) and `timeout` (default `'1m'`) limit the store's own transactions, `migrate()` included: raise `timeout` for it, or migrate from the command line | The transaction client that `prisma.$transaction()` hands its callback |
| `fromKysely(db)` | A `Kysely` instance with a `MysqlDialect`. The store's statements skip its plugins | The transaction that `db.transaction().execute()` hands its callback, or a controlled transaction |

At startup, the store checks the server and the connection: MySQL, not MariaDB; a strict `sql_mode` (`STRICT_TRANS_TABLES`, MySQL's default), without which MySQL would cut a value too long for its column; and a database, where its tables go. It counts the rows an update matched, so keep mysql2's `FOUND_ROWS` flag, which is on by default (Prisma's adapter calls it `foundRows`), and leave the `NO_BACKSLASH_ESCAPES` SQL mode off.

Its ids, names and keys are indexed columns of bounded length, in characters:

| Key | At most |
| --- | --- |
| An instance id, including a child's (by default `<parent id>/<workflow>#<n>`) and that of an instance a schedule starts (`<schedule id>@<time>`) | 255 |
| A schedule id | 230 |
| A workflow's name, a signal's name, `key` and `id`, a concurrency key, a rate-limit key | 255 |
| A journal entry's name: a step's, a sleep's or a wait's, and those the engine adds, such as `$compensate:<step>` and `$child:<child id>` | 512 |

A longer one fails with a `RangeError` that names it, before any SQL. `migrate()` and `MySqlWorkflowStore.schemaVersion` are the PostgreSQL store's. `MySqlWorkflowStore.migrationSql()` takes the same options and returns the statements to apply in order, each once, and `MySqlWorkflowStore.migrationStatements()` takes the `schema`, `from` and `to` and returns them one per string, for a tool that runs one statement per call. A schema's own version is the highest one applied in its `<schema>_migrations` table.

##### Command line

`npx @nestjs/workflows` applies either store's migrations from a deploy step or checks them in CI. It takes `--url` (default `DATABASE_URL`) and `--schema` (default `nest_workflows`). The URL picks the store: `postgres://` or `postgresql://` for PostgreSQL, which needs `pg` installed, and `mysql://` for MySQL, which needs `mysql2`.

| Command | What it does |
| --- | --- |
| `migrate` | Applies the pending migrations, as `migrate: true` does at startup |
| `status` | Prints the schema's version and the one the package needs, and exits with 1 while the schema is behind |
| `sql` | Prints the SQL of `migrationSql()`, from `--from` to `--to`, without a database: PostgreSQL's, or MySQL's with `--dialect mysql`. `--statement-breakpoints` separates the statements for drizzle-kit |

##### The store contract

`PostgresWorkflowStore` and `MySqlWorkflowStore` implement the `WorkflowStore` interface. For another database, implement it in a provider of your own. The JSDoc of each method on `WorkflowStore` says what the method must do, and which race each rule prevents.

**Registration.** The store is an ordinary singleton provider that calls `registerSource(this)` on the injectable `WorkflowStorage` in its constructor. The registry checks the shape at once, refuses a second registration unless it passes `replace: true`, and locks when `WorkflowsModule` initializes, logging the store in use. A request-scoped provider, a provider in a lazy-loaded module, or a lifecycle hook registers too late, and throws. With nothing registered, the module uses `InMemoryWorkflowStore`: a restart loses every running instance, and two processes don't share them. It can't join your transaction either, so `start()` and `signal()` with `transaction` write at once, and it logs a warning the first time. With `NODE_ENV=production`, startup fails instead, with an error that names the package's stores and the interface to implement, unless you set `allowInMemoryStorage: true` in the module options.

**Atomicity.** Workers, signals, cancels, retries, purges and schedules race each other through the store. `claim()` must never lease one instance to two workers, `write()` must write only while the worker's lease holds, and `signal()` must not slip past an instance that is suspending. So every method that changes state is one conditional statement, or one transaction with the right lock, never a read followed by a write. Two methods are optional: `createInTransaction()` and `signalInTransaction()`, which `start()` and `signal()` call with your transaction object, untouched. They must write through it, and refuse the root handle, whose writes commit on their own. On PostgreSQL, `signalInTransaction()` also refuses a transaction that isn't READ COMMITTED, whose wake-up could miss waits committed after its snapshot.

**Test it** with the suite from `@nestjs/workflows/testing`. `workflowStoreContract()` returns the contract as test cases, races included, for any test runner. The tutorial's tests run it against `PostgresWorkflowStore` through Drizzle, and against `MySqlWorkflowStore` on MySQL, as you would against yours, with a function that returns a store on emptied tables:

[[CODE:61]]

With `concurrent: true`, the suite races claims (under limits too), signals, suspensions, children's final writes, cancels and terminates, retries, purges and schedule claims against each other: 60 signals against 60 suspensions, for example. Run it on a database server with a connection pool too, where a store without the right locks fails it. With `transaction`, a function that opens one of your transactions, the cases of the two optional methods run as well. The package's own tests run the suite against a hand-written Drizzle store, as the proof that a store written against the interface passes it.

Packages built on the engine, such as a job queue, take its storage-agnostic parts (clocks, retries, payload codecs, limits, the leased worker loop and schedules) from `@nestjs/workflows/core`; applications don't need it.

##### Call options

| Call | Options | Explained in |
| --- | --- | --- |
| `@Workflow(name, options)` | `version` (default `1`), `timeout` (a run timeout; default none), `concurrency` (`limit`, and a `key` function for a limit per key; one of each in an array), `rateLimit` (`max`, `duration`, and a `key` function; one of each in an array), `schedules` (see the schedule options below) | [Deploy changes safely](/reliability/workflows#deploy-changes-safely), [Time out the whole workflow](/reliability/workflows#time-out-the-whole-workflow), [Limit how many run at once](/reliability/workflows#limit-how-many-run-at-once), [Run workflows on a schedule](/reliability/workflows#run-workflows-on-a-schedule) |
| `ctx.step(name, fn, options)` | `retry`, `timeout`, `heartbeatTimeout`, `compensate`, `compensateRetry` | [Write the workflow](/reliability/workflows#write-the-workflow), [Long-running steps](/reliability/workflows#long-running-steps) |
| `ctx.waitForSignal(name, signal, options)` | `key`, `timeout` (resolves `null` when it passes), `match` (a pure filter over the payload) | [Wait for the delivery webhook](/reliability/workflows#wait-for-the-delivery-webhook) |
| `ctx.sleep(name, duration)` | A duration, or an object with `until` (a `Date` or epoch milliseconds) | [Sleep for a week, then ask for a review](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review) |
| `ctx.waitForAny(name, conditions)` | An object of conditions: `ctx.signalWait(signal, options)` (`key`, `match`), `ctx.timer(duration)` (a duration, or an object with `until`), or a child's handle. Resolves with the winner's `key` and `value` | [Wait for whichever comes first](/reliability/workflows#wait-for-whichever-comes-first) |
| `ctx.startChild(workflow, input, options)`, `ctx.executeChild(workflow, input, options)` | `id` (default the parent's id, the workflow's name and a count, such as `order-71e1973d/shipment#1`), `version`, `timeout`, `parentClose` (`'cancel'`, `'terminate'` or `'abandon'`; default `'cancel'`), `priority` (default the parent's), `concurrencyKey`, `rateLimitKey` | [Start child workflows](/reliability/workflows#start-child-workflows) |
| `ctx.setStatus(status)` | A JSON value of up to 16 KiB, or `undefined` to clear it | [Report its status](/reliability/workflows#report-its-status) |
| `ctx.schedule` | Not a call: the `id` of the schedule and the time `at` of the occurrence that started the instance, or `null` | [Run workflows on a schedule](/reliability/workflows#run-workflows-on-a-schedule) |
| `WorkflowClient.start(workflow, input, options)` | `id` (default a random UUID, or inside a step one derived from the step), `version` (default the highest registered), `timeout` (default the decorator's), `transaction`, `priority` (1 to 2,097,151, lower first; default none, which goes before all), `concurrencyKey`, `rateLimitKey` (instead of the keys the limits compute) | [Start it with the order](/reliability/workflows#start-it-with-the-order), [Limit how many run at once](/reliability/workflows#limit-how-many-run-at-once) |
| `WorkflowClient.signal(signal, payload, options)` | `key`, `id` (stores a signal with the same name and id once; derived from the step inside a step), `transaction` | [Wait for the delivery webhook](/reliability/workflows#wait-for-the-delivery-webhook), [With CQRS](/reliability/workflows#with-cqrs) |
| `WorkflowClient.startAndWait(workflow, input, options, wait)` | `start()`'s options, but not `transaction`, and `result()`'s as `wait` | [Wait for a result](/reliability/workflows#wait-for-a-result) |
| `WorkflowClient.result(id, options)` | `timeout` (wall-clock; default none), `signal` (stops waiting when aborted) | [Wait for a result](/reliability/workflows#wait-for-a-result) |
| `WorkflowClient.getStatus(id, options)` | `journal`, `children` | [Report its status](/reliability/workflows#report-its-status), [Start child workflows](/reliability/workflows#start-child-workflows) |
| `WorkflowClient.cancel(id, reason)`, `terminate(id, reason)` | None | [Let customer support cancel an order](/reliability/workflows#let-customer-support-cancel-an-order), [Retry, delete or terminate](/reliability/workflows#retry-delete-or-terminate) |
| `WorkflowClient.list(filter)` | `status` (one or a list), `workflow`, `version`, `parentId`, `scheduleId`, `limit` (default `100`), `offset` | [Deploy changes safely](/reliability/workflows#deploy-changes-safely) |
| `WorkflowClient.retry(id, options)` | `timeout` (a new run timeout from now, or `false` for none; default the instance's) | [Retry, delete or terminate](/reliability/workflows#retry-delete-or-terminate) |
| `WorkflowClient.delete(id, options)` | `force` (delete an unfinished instance too; default `false`) | [Retry, delete or terminate](/reliability/workflows#retry-delete-or-terminate) |
| `WorkflowClient.purge(options)` | `olderThan` (required), `status` (default `completed`, `failed` and `cancelled`), `batchSize` (default `500`) | [Purge finished instances](/reliability/workflows#purge-finished-instances) |
| `WorkflowClient.schedules`, or the injectable `WorkflowSchedules` | `upsert(id, options)` (the schedule options, with `workflow`, and optionally `version` and a JSON `input`), `get(id)`, `list(filter)` (`workflow`, `limit`, `offset`), `remove(id)`, `pause(id)` and `resume(id)` (neither re-encrypts the stored input), `trigger(id)` (in a process that registers the workflow, unless the schedule pins a `version`), and `preview(schedule, options)` (a schedule's id or timing; `from`, and `count`, default `10`) | [Run workflows on a schedule](/reliability/workflows#run-workflows-on-a-schedule) |
| `@StartOn(event, options)` | `id` (required), `input` (default the event), `priority`, `concurrencyKey`, `rateLimitKey` (as `start()`'s: a value, or a function of the event, where `undefined` leaves the default) | [With CQRS](/reliability/workflows#with-cqrs) |
| `@SignalOn(event, options)` | `signal`, `key`, `id`, `payload` (default the event) | [With CQRS](/reliability/workflows#with-cqrs) |
| `EventBus.publish(event, context)`, `publishAll(events, context)`, an aggregate's `commit(context)` (`@nestjs/cqrs` 12.1 or later) | `transaction`, read from the dispatcher context once `WorkflowsCqrsModule` is imported | [With CQRS](/reliability/workflows#with-cqrs) |

A step's function receives `idempotencyKey`, `attempt`, `signal`, `progress` and `heartbeat()`; a compensation receives the same, plus the reason the workflow is being undone.

A schedule, declared in `@Workflow()` or saved with `upsert()`, takes these options:

| Option | Default | Meaning |
| --- | --- | --- |
| `id` | Required in `@Workflow()` | Unique across the application: letters, digits, `.`, `:`, `_` and `-`. `upsert()` takes it as its first argument |
| `cron`, `every`, `rrule` | One of the three is required | A cron expression of 5 fields, or 6 with the seconds first; an interval of at least a second, counted from `startAt`; or an RFC 5545 recurrence rule |
| `tz` | `'UTC'` | The IANA time zone of `cron` and `rrule`. Not with `every` |
| `startAt`, `endAt` | None | No occurrence before `startAt`, or after `endAt` |
| `limit` | None | How many occurrences it starts before it ends |
| `missed` | `'skip'` | Occurrences no worker was up to start: `'skip'`, `'once'` or `'all'` |
| `overlap` | `'skip'` | An occurrence due while an instance it started is unfinished: `'skip'`, `'allow'`, `'cancel-previous'` or `'buffer-one'` |
| `priority` | None | The priority of the instances it starts |
| `input` | None | The instances' input: a JSON value, or in `@Workflow()` a function of the occurrence |

##### Events

`WorkflowEvents.events$` emits each event, and publishes it on the `nestjs:workflows:<type>` diagnostics channel, for example `nestjs:workflows:step-failed`. Every payload has `type`, `id` (the instance), `workflow`, `version` and `at` (the engine's time, in milliseconds).

| Event | Other fields | When |
| --- | --- | --- |
| `workflow-started` | None | The first execution of an instance began |
| `workflow-resumed` | `run` | A later execution began: after a wait, a sleep, a retry or a crash |
| `workflow-suspended` | `wakeAt`, `waits` | An execution parked the instance |
| `step-completed` | `step`, `attempt`, `durationMs` | A step attempt succeeded |
| `step-failed` | `step`, `attempt`, `error`, `retryAt` | A step attempt failed; `retryAt` is `null` when the step gave up |
| `signal-received` | `wait`, `signal`, `signalId` | A wait took a signal |
| `signal-timed-out` | `wait`, `signal` | A wait's deadline passed without a matching signal |
| `workflow-compensating` | `error` | The instance failed or was cancelled, and starts undoing |
| `step-compensated` | `step`, `attempt` | A step's compensation completed |
| `workflow-completed` | `output` | The instance completed |
| `workflow-failed` | `error` | The instance failed, after its compensations ran |
| `workflow-cancelled` | `error` | The instance was cancelled, after its compensations ran; `error.message` is the reason |
| `workflow-compensation-failed` | `error` | A compensation gave up halfway. Needs a person |
| `journal-large` | `entries`, `bytes` | The journal reached `journal.warnEntries` or `journal.warnBytes`; once per instance |
| `workflow-retried` | `from`, `error` | `retry()` reopened a `failed` or `compensation_failed` instance; `error` is the one it had |
| `workflow-deleted` | `status` | `delete()` removed an instance; `status` is the one it had |
| `custom-status` | `status` | A write changed the instance's custom status |
| `child-started` | `child`, `childWorkflow`, `childVersion` | The instance started a child |
| `schedule-skipped` | `reason` (`'missed'` or `'overlap'`), `from`, `to` | A schedule passed over occurrences. Its `id` is the schedule's |

An instance maps onto one trace, whichever processes run it over its days or weeks, so key the trace by the instance `id`. The instance is the root span, from `workflow-started` to its final event (`workflow-completed`, `workflow-failed`, `workflow-cancelled` or `workflow-compensation-failed`). Each execution is a child span, from `workflow-started` or `workflow-resumed` to `workflow-suspended` or the final event. Each step attempt is a span inside it that ends at `step-completed`, whose `durationMs` gives its start, or at `step-failed`. The other events are events on the execution's span. Tracing tools subscribe to the diagnostics channels, so this needs no code in your application.

##### Errors

The package's errors extend `WorkflowError`, except the two that are control flow or yours to throw. The ones found on a failed instance are there by name, in its `error`.

| Error | HTTP status | Raised when |
| --- | --- | --- |
| `WorkflowIdConflictError` | `409` | `start()` with an existing id, but a different workflow or input, `signal()` with an `id` already used for the same signal with another key, or `startChild()` with an id that another workflow, parent or input uses |
| `WorkflowNotFoundError` | `404` | `cancel()`, `terminate()`, `retry()`, `delete()` or `result()` of an unknown id, a schedule method with an unknown schedule id, or `start()` or a schedule's `trigger()` of a workflow this application can't resolve |
| `WorkflowStateError` | `409` | `retry()` of an instance that isn't `failed` or `compensation_failed`, or whose compensations ran; `delete()` of an unfinished instance without `force`; either racing another change to the instance; `upsert()` or `remove()` of a declared schedule |
| `NonRetryableStepError` | None | You throw it from a step to fail the step without retrying |
| `StepFailedError` | None | Inside `run()`, a step gave up; `step`, `attempts`, and the original error's name and message as `cause` |
| `StepTimeoutError` | None | A step attempt ran past its `timeout` or `heartbeatTimeout`. Retried |
| `WorkflowFailedError` | None | `ctx.fail()` failed the instance. Also what `result()` and `startAndWait()` reject with for an instance that ended without completing, with its `instanceId`, its `status` and its error as `cause` |
| `ChildWorkflowFailedError` | None | A child failed, was cancelled or was terminated: what `ctx.executeChild()` and a child's `result()` throw in the parent, with the child's `workflow`, `instanceId`, `status` and error as `cause`. Extends `WorkflowFailedError` |
| `WorkflowResultTimeoutError` | None | `result()` or `startAndWait()` waited past its `timeout`, with the `instanceId` and `timeoutMs`. The instance keeps running |
| `WorkflowDefinitionError` | None | A name used twice in one run, or a `ctx` call inside a step. The instance fails without compensation |
| `WorkflowNonDeterminismError` | None | A deploy renamed, removed or reordered steps that running instances journaled. Extends `WorkflowDefinitionError`. [Deploy changes safely](/reliability/workflows#deploy-changes-safely) |
| `WorkflowInterrupt` | None | The engine's control flow (a suspension, a cancel). Rethrow it; `isWorkflowInterrupt()` identifies it |
| `WorkflowTimeoutError` | None | Only by name, on an instance that ran past its run timeout: it compensated and failed |
| `WorkflowCancelledError` | None | Only by name, on a cancelled instance: its message is the reason |
| `WorkflowTerminatedError` | None | Only by name, on a terminated instance, which ends as `cancelled`: its message is the reason |
| `WorkflowDeletedError` | None | Only by name, as the cause of a parent's `ChildWorkflowFailedError`, when `delete()` with `force` removed the child before it ended |
| `WorkflowJournalLimitError` | None | Only by name, on an instance whose journal reached `journal.maxEntries` or `journal.maxBytes`: it compensated and failed |
| `WorkflowSchemaError` | None | The schema of `PostgresWorkflowStore` or `MySqlWorkflowStore` is behind the package's migrations while `migrate` is off, or applying them failed (`cause`; on MySQL, the message names the statement where the next run resumes): startup and every call fail until it's fixed. With the `schema`, its `version` and the `requiredVersion`. From `@nestjs/workflows/postgres` and `@nestjs/workflows/mysql` |

`MySqlWorkflowStore` also rejects an id, name or key longer than its column with a `RangeError`, before any SQL ([MySQL store](/reliability/workflows#mysql-store)). A deadlock in your transaction reaches you as MySQL's error 1213, which the store doesn't retry, since it rolled back your writes too.
