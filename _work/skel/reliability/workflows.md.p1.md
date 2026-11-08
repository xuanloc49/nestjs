### Durable workflows

`@nestjs/workflows` runs processes that take days, such as fulfilling an order, as one `async` method whose steps are kept in your database and survive restarts.

Some business processes take days and span several systems. In an online store for cat food and supplies, fulfilling an order means:

1. Charge the customer's card with the payment provider.
2. Reserve the items in the warehouse.
3. Wait up to 3 days for the carrier's `shipment.delivered` webhook.
4. If it never arrives, or the carrier brings the parcel back, refund the charge and release the stock. Otherwise, wait 7 days and ask the customer for a review.

The process must survive deploys and crashes, charge exactly once, undo its work when it fails, and tell support where every order stands. With `@nestjs/workflows` you write it as one `async` method on an injectable class. Each side effect runs in a journaled **step**. After a restart, the method runs again from the top, and completed steps return their recorded results instead of running twice. Waits and sleeps park the instance in your own database, where any process on any host can pick it up when it's due. There is no workflow server to run.

#### Workflows, queues or sagas?

Nest already has two tools for work that happens later, and each stays the right choice for its job:

- **[BullMQ](/application/queues#bullmq-installation)** runs one unit of background work at a time, such as sending an email or transcoding a video, with concurrency limits, rate limits, priorities, and delayed or repeatable jobs. A process with a single delayed action ("cancel the order if it isn't paid within an hour") is a delayed job plus a status column.
- **[CQRS sagas](/recipes/cqrs#sagas)** turn events into commands inside one process. They fit reactions where losing in-flight state on a restart is acceptable. Where it isn't, the same events can start and signal workflows: see [With CQRS](/reliability/workflows#with-cqrs).
- **Workflows** fit a process with several steps that waits hours or days for timers or outside events, must survive restarts and deploys, and must undo its completed steps when it fails or is cancelled. They have concurrency limits, rate limits, priorities and schedules of their own, and a step can still hand heavy work to a BullMQ queue.

A workflow instance is a row in your application's database, so starting one can be part of the transaction that saves the order: pass the transaction to `start()` as its `transaction` option. The order and its fulfilment commit together or not at all. A job queue writes through its own connection (Redis, or BullMQ's own PostgreSQL pool), so saving an order and enqueueing its job are two writes, and a crash between them loses one. The same goes for signals: a webhook can update the order and wake its workflow in one transaction.

The tutorial below shows where queues and sagas run out: code that continues after a durable wait ([Sleep for a week, then ask for a review](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review)), an event racing a deadline ([Wait for the delivery webhook](/reliability/workflows#wait-for-the-delivery-webhook)), and compensation that survives a crash ([Let customer support cancel an order](/reliability/workflows#let-customer-support-cancel-an-order)).

#### Installation

To get started, install the required dependency:

[[CODE:1]]

The tutorial keeps its workflows in PostgreSQL, with the package's own store, and uses Drizzle, registered through [`@nestjs/drizzle`](/data/drizzle). [Keep workflows in your database](/reliability/workflows#keep-workflows-in-your-database) shows the store with TypeORM too, and the package's MySQL store. The tests on this page use [PGlite](https://pglite.dev), so they need no server.

Orders live in the example application's own table, `orders`. The tutorial uses in-memory stand-ins for the payment provider's SDK (`PaymentProviderClient`), the stock table (`InventoryService`) and the mail provider (`MailService`). Like the real systems, they deduplicate requests by idempotency key. Orders have this shape:

[[CODE:2]]

##### Register the module

Import `WorkflowsModule` once, in the root module, next to [`DrizzleModule`](/data/drizzle), which registers the Drizzle database that `@InjectDrizzle()` injects. Workflow classes are ordinary providers, so they go in `providers` next to the services they inject. This is the finished module: the workflows and the controllers it lists are written in the following sections, and the first provider is the package's PostgreSQL store, which [Keep workflows in your database](/reliability/workflows#keep-workflows-in-your-database) explains.

[[CODE:3]]

> info **Hint** The tutorial reads `process.env` directly, to stay short. In an application, load the environment through [`@nestjs/config`](/application/configuration) with a validation schema, so a missing `DATABASE_URL` stops the application at startup, and read it from `ConfigService` in the factory.

Every option is optional: `WorkflowsModule.forRoot()` works as is. To read them from `ConfigService`, use `forRootAsync()` with a factory, or with a `useClass` class that implements `WorkflowsOptionsFactory` and its `createWorkflowsOptions()` method.

The `worker` runs inside your application process. It polls for due instances every second, and a local `start()` or `signal()` wakes it immediately. It claims due instances under a lease and renews the lease every third of `leaseDuration`. If the process dies, its instances are claimable again once the lease expires. Set `worker: false` on processes that should only start, signal and inspect workflows, such as API pods. A step gets 3 attempts by default, with a backoff that starts at 1 second and doubles up to 5 minutes. A `retry` option here changes that default.

In `main.ts`, enable shutdown hooks. On `SIGTERM` the worker stops claiming, aborts the `signal` of running steps, waits up to `shutdownTimeout`, and hands the instances it stopped back to the store. Another process then picks them up at once instead of waiting for the lease.

[[CODE:4]]

##### Keep workflows in your database

Workflow instances, their journals, the signals they wait for and the signals sent live in a **store**. Until you register one, the module keeps them in memory: fine for a first run, but a restart loses every running order, and two processes don't share them.

> warning **Warning** With `NODE_ENV=production` and no store registered, startup fails, unless you set `allowInMemoryStorage: true`.

On PostgreSQL, register the package's store, `PostgresWorkflowStore` from `@nestjs/workflows/postgres`. It runs its SQL through the database client your application already has, so it can join your transactions. It's an ordinary provider, registered once, in the root module, next to `WorkflowsModule`: both are application-wide. In `AppModule` above, it's the first provider: a factory that injects the Drizzle database and the `WorkflowStorage` registry, which the store registers itself with.

`fromDrizzle(db)` is the store's **executor**: it runs the store's statements through your Drizzle database, whichever driver it uses, such as `pg` or PGlite. `fromPg(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` and `fromKysely(db)` do the same for a node-postgres pool, TypeORM, Prisma and Kysely. At startup, the module logs `WorkflowStorage: PostgresWorkflowStore`.

**The schema.** There's nothing to create for workflows: no tables, entities or Prisma models. The store keeps its tables in a schema of its own, `nest_workflows` (the `schema` option names another), and creates and migrates it itself. On MySQL, which has no schemas, they're tables of the connection's database, with the schema's name as their prefix: `nest_workflows_instances` and so on.

| Table | What it holds |
| --- | --- |
| `nest_workflows.instances` | Each workflow instance: its input, status, output or error, when it's due, and its lease |
| `nest_workflows.journal` | Each instance's recorded steps, sleeps, waits and compensations, with their results |
| `nest_workflows.waits` | The signals a suspended instance waits for |
| `nest_workflows.signals` | The signals sent, until `purge()` deletes the ones no instance can take any more |
| `nest_workflows.schedules` | The schedules, with their spec, state and next run |
| `nest_workflows.rate_limits` | The rate-limit windows, per workflow and key |
| `nest_workflows.migrations` | The versions of the store's schema applied |

They belong to the store: your migrations don't create them, and your own tables can't collide with them.

**Migrations.** The package ships the schema as versioned migrations, and the store applies them itself. With the `migrate` option, it applies the ones the schema hasn't had yet at startup, before the worker runs, in one transaction that holds an advisory lock: of several processes that start together, one migrates, and the others find nothing left to do. `migrate` defaults to `true`, except with `NODE_ENV=production`. So in development and in tests, the store creates its schema on the first start, and your migrations only create your own tables, here `orders`.

In production, apply the migrations before the new version of your application starts, as you apply your own, so that no process changes the schema while it boots: in the middle of a rolling deploy, that would lock busy tables, and a least-privilege database user can't do it anyway. The package's command line does it from your deploy step, next to `npx drizzle-kit migrate`. It reads the database from `DATABASE_URL`, or from `--url`, and needs `pg` installed:

[[CODE:5]]

`status` exits with 1 while the schema is behind, which makes it a check for CI. To apply the migrations with your own migration tool instead, take their SQL from `npx @nestjs/workflows sql`, or from `PostgresWorkflowStore.migrationSql()` in code: the statements of every migration, one per paragraph, with the bookkeeping that records the version. Run them in one transaction, as TypeORM's and Drizzle's migrators do. With TypeORM, that's a migration of your own, next to the ones it generates for your entities:

[[CODE:6]]

With drizzle-kit, create a custom migration, and fill the file it creates with the SQL, a `--> statement-breakpoint` line between the statements: Drizzle's migrator then runs them one at a time, which PGlite requires. In code, `migrationSql()` with `statementBreakpoints: true` returns the same.

[[CODE:7]]

On MySQL, `MySqlWorkflowStore.migrationStatements()` returns the statements one per string, and a TypeORM migration runs them one per call:

[[CODE:8]]

With `migrate` off, a store whose schema is behind fails the startup with a `WorkflowSchemaError` that names these three ways, and fails every call the same way until the schema catches up, which it notices without a restart. Migrations only ever add tables, columns and indexes, so during a rolling deploy, the previous version of your application keeps running on the migrated schema. There are no down migrations.

**Transactions.** `start()` and `signal()` take your transaction as their `transaction` option: with Drizzle, the `tx` that `db.transaction()` hands its callback, as [Start it with the order](/reliability/workflows#start-it-with-the-order) shows. The store runs its statements on that transaction, so they commit or roll back with your writes. It refuses the database itself, whose statements would commit on their own, with a `TypeError` that says what to pass. With the other executors, pass a node-postgres client after `BEGIN` (not the pool), TypeORM's `EntityManager` from `dataSource.transaction()`, Prisma's interactive transaction client, or a Kysely transaction.

**Isolation.** The store relies on READ COMMITTED, PostgreSQL's default isolation level: its statements race each other, and under a stricter level they would fail with serialization errors. At startup, it checks the database's `default_transaction_isolation`, and fails if it's stricter. A `signal()` in your transaction needs a READ COMMITTED transaction too, or its wake-ups could miss waits committed after the transaction's snapshot: it's refused with a `TypeError` otherwise.

**With TypeORM.** `TypeOrmModule` takes the place of `DrizzleModule` in `AppModule`, and the store runs on the `DataSource` it provides, through `fromTypeOrm()`:

[[CODE:9]]

Where the tutorial passes Drizzle's `tx` to `start()` and `signal()`, pass the `EntityManager` that `dataSource.transaction()` hands its callback. The store refuses `dataSource.manager`, whose writes would commit on their own. This is the order service's `place()`, from [Start it with the order](/reliability/workflows#start-it-with-the-order), with TypeORM:

[[CODE:10]]

> info **Hint** With Prisma, pass the client to `fromPrisma()`, and as `transaction`, the transaction client that `prisma.$transaction()` hands its callback. The store's own transactions wait up to 10 seconds for a connection and run for up to a minute, longer than Prisma's defaults: the second argument of `fromPrisma()` changes that, with `maxWait` and `timeout`. If your application signals in bursts, give its own transactions a longer `maxWait` too, since signals queue behind each other.

**With MySQL.** The package has a store for MySQL 8.4 LTS and 9.x too, `MySqlWorkflowStore` from `@nestjs/workflows/mysql`, with executors of the same names. MariaDB isn't supported yet: the store refuses it at startup. The provider is the same, with the MySQL store's class and executor. This is `AppModule` with Drizzle on a mysql2 pool, where `mode: 'default'` is Drizzle's setting for a schema on MySQL:

[[CODE:11]]

`fromMysql2(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` and `fromKysely(db)` do the same for a mysql2 pool, TypeORM, Prisma (through `@prisma/adapter-mariadb`) and Kysely. `start()` and `signal()` take the same transaction objects as on PostgreSQL, and with mysql2, a connection after `beginTransaction()`. What differs from PostgreSQL:

- **The tables.** MySQL has no schemas inside a database, so the store keeps its tables in the connection's database, the one the URL's path names, and the `schema` option is the prefix of their names: `nest_workflows_instances`, `nest_workflows_signals` and so on, next to `nest_workflows_migrations` and `nest_workflows_locks`, which hold its versions and its locks.
- **Bounded keys.** Ids, names and keys are indexed columns of limited length. An instance id, a workflow or signal name, a signal's `key` and `id`, and a concurrency or rate-limit key hold 255 characters, a schedule id 230, and a step, sleep or wait name 512. `start()` and `signal()` reject a longer one with a `RangeError` before anything is written. Keys still compare exactly, as on PostgreSQL.
- **Your transactions.** `start()` and `signal()` with the `transaction` option work at REPEATABLE READ, MySQL's default, and at READ COMMITTED: the wake-up reads the waits with a locking read, which also sees those committed after your transaction's snapshot. Avoid SERIALIZABLE, where MySQL turns plain reads into locking ones: a `start()` in such a transaction would hold every signal up until the transaction ends.
- **Deadlocks.** MySQL breaks a deadlock by rolling back one of the transactions, with error 1213 (`ER_LOCK_DEADLOCK`). The store runs its own transactions again. In yours, the rollback also took your writes, so the error reaches your code: run the transaction again. A transaction that writes an order and then signals, while another one signals and then writes the same order, deadlocks that way.
- **Migrations.** MySQL commits each DDL statement on its own, so the migrations can't run in one transaction. The store and `npx @nestjs/workflows migrate` apply them one statement at a time, under a lock (`GET_LOCK()`), so processes that start together still migrate once, and a run that stopped halfway resumes where it stopped. The command line takes a `mysql://` URL and then needs `mysql2`, and `npx @nestjs/workflows sql --dialect mysql` prints the SQL. With your own tool, apply the statements in order, each once, one per call, as the TypeORM migration above does: for drizzle-kit, whose MySQL migrator sends one statement per breakpoint, add `--statement-breakpoints`.

For another database, write a store of your own: [The store contract](/reliability/workflows#the-store-contract) says what it must do.

#### Write the workflow

Every side effect needs an idempotency key. A step runs **at least once**: if the process dies after the payment provider charged the card but before the result reached the journal, the step runs again. The engine hands each step an `idempotencyKey` that stays the same across attempts and processes (`<instance id>:<step name>`). Pass it to the system you call, and the effect happens once:

[[CODE:12]]

`InventoryService.reserve()` follows the same idea without an external API: it uses the key as the reservation's primary key, so a retry finds the reservation it already made. It throws `NonRetryableStepError` when a product is out of stock. `MailService` passes the key to the mail provider as the message id.

Now the workflow. Decorate a class with `@Workflow()`, give it a name, and implement `run()`:

[[CODE:13]]

`ctx.step()` runs the function once and writes its result to the journal. Whenever the instance runs again (after a wait, a sleep or a crash), `run()` starts from the top and `charge-payment` returns the journaled charge without calling the payment provider. Results must be JSON-serializable, and they come back in their JSON form, on the first run too: a `Date` is a string. The return type says so (`Journaled<Charge>`), so TypeScript flags code that treats a journaled value as a live object.

- **`retry`**: `attempts` counts the first attempt too, and `backoff` sets the wait before each retry: a `delay`, a growth `factor`, a `maxDelay` cap and optional `jitter`. A number is shorthand for the attempts, and `false` means a single attempt. A failed attempt parks the instance until the backoff has elapsed, so a retry survives a restart too. A `NonRetryableStepError`, such as a declined card, fails the step at once.
- **`compensate`**: registered when the step completes. If the workflow later fails or is cancelled, the compensations of completed steps run in reverse order. Each is journaled and retried like a step, with its own idempotency key. If `reserve-stock` fails because an item is out of stock, the charge is refunded. [Sleep for a week, then ask for a review](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review) shows how to end this once the order is delivered.

Steps can also run in parallel. To reserve each item on its own, start one step per item and wait for them together. Each step has its own name, with the item's index in it, and so its own idempotency key and compensation:

[[CODE:14]]

If one item is out of stock, its step fails, the others finish, and the compensations of the ones that completed run: the reservations are released, then the charge is refunded. Compensations run in the reverse order of the `ctx.step()` calls, whichever step finished first. The rest of the tutorial keeps the single `reserve-stock` step.

The class is a singleton shared by every running order, and constructor injection works as usual. Keep per-order state in local variables, never on `this`.
