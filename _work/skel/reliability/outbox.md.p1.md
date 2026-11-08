### Outbox

`@nestjs/outbox` publishes events and messages reliably: each one is saved in the same database transaction as your data, then relayed with retries.

When a customer places an order at an online store for cat food and supplies, the order API saves the order and announces it with an `OrderPlaced` event. Three things react to that event: a confirmation email goes out, stock is reserved, and a separate analytics service records the sale.

Saving the order and publishing the event are two writes to two different systems, and no transaction spans both:

- **Save, then publish.** If the process crashes or the broker is down between the two, the order exists but `OrderPlaced` is lost. The customer gets no email, the stock isn't reserved, and analytics undercounts.
- **Publish, then save.** If the insert fails, the customer is thanked for an order that doesn't exist.
- **Retry the publish on error.** A timeout after a successful send looks like a failure, so the retry sends it again and the customer gets two emails.

This is the dual-write problem. `ClientProxy.emit()`, `EventEmitter2` and the CQRS `EventBus` all publish from memory, so they all have it.

A transactional outbox removes it by turning the event into a row. `Outbox.add()` inserts the message into an outbox table in **the same database transaction as the order**, so both commit or neither does. A relay then publishes committed messages. It retries failures with backoff and moves messages that never succeed to a dead-letter table. Retries mean a consumer can see a message twice, so each consumer keeps an **inbox** of the message ids it has processed and skips repeats.

In this tutorial, you'll add the outbox to the store's order API, on PostgreSQL with Drizzle:

- `POST /orders` saves the order and its messages in one transaction.
- Two in-process handlers send the confirmation email and reserve stock.
- A separate analytics microservice, with a database of its own, receives order events over TCP, in order for each order.
- Failures are retried, and a small admin API lists, requeues and purges dead letters.
- Several instances of the API share the work safely.

#### Prerequisites

- PostgreSQL, with [Drizzle ORM](https://orm.drizzle.team) on the `pg` driver, registered through [`@nestjs/drizzle`](/data/drizzle). The outbox's messages commit with your rows, so they live in the database your orders live in, on a database server that outlives any instance of the application. Using TypeORM, Prisma or MySQL? Follow the tutorial for what the application does: [Keep messages in your database](/reliability/outbox#keep-messages-in-your-database) shows the store with each of them.
- `@nestjs/microservices`, for the TCP link to the analytics service in [Publish to the analytics microservice](/reliability/outbox#publish-to-the-analytics-microservice).

Install the package:

[[CODE:1]]

The example application, the online store's order API, keeps its products and orders in two tables of its own, which the later sections read and write. They're the example's data, not something the outbox needs: the outbox's tables belong to its store, which creates them, as [Keep messages in your database](/reliability/outbox#keep-messages-in-your-database) shows.

`products` is the catalog, and reserving stock for an order moves units from its `in_stock` to its `reserved`:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `text` | Primary key, such as `salmon-kibble-2kg` |
| `name` | `text` | The display name, such as `Salmon kibble, 2 kg` |
| `price` | `integer` | In cents |
| `in_stock` | `integer` | The units available to order |
| `reserved` | `integer` | The units held for placed orders. Defaults to `0` |

`orders` holds the orders that `POST /orders` saves:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `text` | Primary key |
| `user_id` | `text` | The customer who placed the order |
| `items` | `jsonb` | The order's lines, as a JSON array: each line's `productId`, `quantity` and unit `price` (in cents) |
| `total` | `integer` | In cents |
| `status` | `text` | `placed` or `cancelled` |

No column in either table is nullable.

The catalog has two products: `salmon-kibble-2kg`, at 2499 cents with 10 in stock, and `clumping-litter-10l`, at 1599 cents with one in stock.

#### Keep messages in your database

There's nothing to create for the outbox: no tables, entities or Prisma models. Register its store, and the store creates its own schema, `nest_outbox`, and migrates it: at startup in development and in tests, and in production with `npx @nestjs/outbox migrate`, or with `migrationSql()` in your own migrations.

The outbox keeps its messages, its dead letters and the consumers' inboxes in the same database as your own tables, because they must commit with your rows. Until you register a store for them, the outbox keeps them in memory: fine for a first run, but a restart loses every message that wasn't published yet, two instances don't share them, and nothing joins your transactions.

> warning **Warning** With `NODE_ENV=production` and no store registered, startup fails, unless you set `allowInMemoryStorage: true`.

On PostgreSQL, register the package's store, `PostgresOutboxStore` from `@nestjs/outbox/postgres`. It runs its SQL through the database client your application already has, so it can join your transactions, and it keeps its tables in a schema of its own. It's an ordinary provider, registered once, in the root module, next to `OutboxModule`: both are application-wide, and every `outbox.add()` in any module goes through it. The root module creates it with a factory that injects the Drizzle database and the `OutboxStorage` registry, which the store registers itself with:

[[CODE:2]]

`fromDrizzle(db)` is the store's **executor**: it runs the store's statements through your Drizzle database, whichever driver it uses, such as `pg` or PGlite. `fromPg(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` and `fromKysely(db)` do the same for a node-postgres pool, TypeORM, Prisma and Kysely. At startup, the module logs `OutboxStorage: PostgresOutboxStore`.

**The schema.** The store keeps its tables in a schema of its own, `nest_outbox` (the `schema` option names another). On MySQL, which has no schemas, they're tables of the connection's database, with the schema's name as their prefix: `nest_outbox_messages` and so on.

| Table | What it holds |
| --- | --- |
| `nest_outbox.messages` | Each message from `add()` until it's published or dead-lettered, with its attempts and lease |
| `nest_outbox.dead_letters` | The messages that failed, with the reason and the error of every attempt |
| `nest_outbox.inbox` | The ids of the messages each consumer has processed |
| `nest_outbox.migrations` | The versions of the store's schema applied |

They belong to the store: your migrations don't create them, your ORM's schema doesn't declare them, and your own tables can't collide with them. drizzle-kit and Prisma Migrate work on the `public` schema unless told otherwise, and TypeORM on its entities' tables, so their tools leave `nest_outbox` alone.

**Migrations.** The package ships the schema as versioned migrations, and the store applies them itself. With the `migrate` option, it applies the ones the schema hasn't had yet when the application starts, before the relay runs, in one transaction that holds an advisory lock: of several instances that start together, one migrates, and the others find nothing left to do. `migrate` defaults to `true`, except with `NODE_ENV=production`. So in development and in tests, the store creates its schema on the first start, and your migrations only create your own tables, here `products` and `orders`.

In production, apply the migrations before the new version of your application starts, as you apply your own, so that no instance changes the schema while it boots: in the middle of a rolling deploy, that would lock busy tables, and a least-privilege database user can't do it anyway. The package's command line does it from your deploy step, next to `npx drizzle-kit migrate`. It reads the database from `DATABASE_URL`, or from `--url`, and needs `pg` installed:

[[CODE:3]]

`status` exits with 1 while the schema is behind, which makes it a check for CI. To apply the migrations with your own migration tool instead, take their SQL from `npx @nestjs/outbox sql`, or from `PostgresOutboxStore.migrationSql()` in code: the statements of every migration, one per paragraph, with the bookkeeping that records the version. Run them in one transaction, as TypeORM's and Drizzle's migrators do. With TypeORM, that's a migration of your own, next to the ones it generates for your entities:

[[CODE:4]]

With drizzle-kit, create a custom migration, and fill the file it creates with the SQL, a `--> statement-breakpoint` line between the statements: Drizzle's migrator then runs them one at a time, which PGlite requires. In code, `migrationSql()` with `statementBreakpoints: true` returns the same.

[[CODE:5]]

On MySQL, `MySqlOutboxStore.migrationStatements()` returns the statements one per string, and a TypeORM migration runs them one per call:

[[CODE:6]]

With `migrate` off, a store whose schema is behind fails the startup with an `OutboxSchemaError` that names these three ways, and fails every call the same way until the schema catches up, which it notices without a restart. Migrations only ever add tables, columns and indexes, so during a rolling deploy, the previous version of your application keeps running on the migrated schema. There are no down migrations.

**Transactions.** `outbox.add()` takes your transaction, as [Save the order and its messages in one transaction](/reliability/outbox#save-the-order-and-its-messages-in-one-transaction) shows, and so does a handler's `processInTransaction()`: with Drizzle, the `tx` that `db.transaction()` hands its callback. The store runs its statements on that transaction, so they commit or roll back with your writes. It refuses the database itself, whose statements would commit on their own, with an `OutboxTransactionRequiredError` that says what to pass. With the other executors, pass a node-postgres client after `BEGIN` (not the pool), TypeORM's `EntityManager` from `dataSource.transaction()`, Prisma's interactive transaction client, or a Kysely transaction.

**Isolation.** The store's own transactions (claims, dead-letter moves, requeues) rely on READ COMMITTED, PostgreSQL's default isolation level: at startup, the store checks the database's `default_transaction_isolation`, and fails if it's stricter. Yours may run at any level. `add()` first takes a lock per key on your transaction, so transactions that add messages with the same key take turns, and a key's messages are numbered in the order their transactions commit. Under REPEATABLE READ or SERIALIZABLE, two deliveries of one message that race to `processInTransaction()` can fail the second with a serialization error instead of skipping it as a duplicate: its handler fails, and the relay's retry finds the record.

**With TypeORM.** `TypeOrmModule` takes the place of `DrizzleModule` in the root module, and the store runs on the `DataSource` it provides, through `fromTypeOrm()`:

[[CODE:7]]

Where the tutorial passes Drizzle's `tx` to `outbox.add()`, pass the `EntityManager` that `dataSource.transaction()` hands its callback, and type the outbox with it. The store refuses `dataSource.manager`, whose writes would commit on their own. This is the order service with TypeORM:

[[CODE:8]]

**With Prisma.** Pass your `PrismaService` to `fromPrisma()` in the factory, and to `outbox.add()` the transaction client that `prisma.$transaction()` hands its callback. Only that interactive form has one to pass: the array form, `prisma.$transaction([query1, query2])`, can't include an `outbox.add()`. The store refuses the client itself, whose statements would commit on their own. Its own transactions wait up to 10 seconds for a connection and run for up to a minute, longer than Prisma's defaults: the second argument of `fromPrisma()` changes that, with `maxWait` and `timeout`.

**With MySQL.** For MySQL 8.4 LTS and 9.x, `@nestjs/outbox/mysql` has `MySqlOutboxStore`. Import the store and its executor from there: the provider is the same, and so are the options and the executors' names. This is the order API on MySQL, with Drizzle on the `mysql2` driver:

[[CODE:9]]

`fromMysql2(pool)`, `fromTypeOrm(dataSource)` for a data source of type `mysql`, `fromPrisma(prisma)` with the `@prisma/adapter-mariadb` driver adapter (the one that serves MySQL), and `fromKysely(db)` serve the other clients. What differs from PostgreSQL:

- **Tables, not a schema.** A MySQL database has no schemas, so the store keeps its tables in the connection's database, the one the URL's path names, and the `schema` option is their prefix: `nest_outbox_messages`, `nest_outbox_dead_letters` and `nest_outbox_inbox`, next to `nest_outbox_migrations` and `nest_outbox_locks`. It takes lowercase letters, digits and underscores, up to 40 characters. A connection without a database fails the startup.
- **Bounded keys.** Ids, topics, keys and consumer names are indexed columns of at most 255 characters, compared byte for byte: `order-1` and `Order-1` are two keys. A longer one is refused with a `RangeError`, before any statement: by `add()`, and by the inbox before it runs a handler.
- **Your isolation level.** Your transactions may run at REPEATABLE READ, MySQL's default, or at READ COMMITTED. A delivery that races another to `processInTransaction()` waits for it, then skips the handler as a duplicate, at either level.
- **Deadlocks reach your transaction.** `add()` locks a row per key in your transaction, one of 16,384 that the keys share, which the store creates when it starts: producers of two keys that share a row take turns, as producers of one key do, which slows an unrelated producer only rarely. When MySQL breaks a deadlock in your transaction (error 1213), it rolls the whole transaction back, and the store can't run your work again: the error reaches your code as your client's error, so run the transaction again. With those rows in place, two things can still cause one: three deliveries of one message that race to `processInTransaction()` while the first rolls back, and transactions of yours that take the same locks in different orders. The store's own transactions retry on deadlock by themselves.
- **Migrations that aren't transactional.** MySQL commits each DDL statement on its own, so `migrate` and `npx @nestjs/outbox migrate --url mysql://...` apply the statements one at a time under a lock, and a run that stopped halfway resumes where it stopped. Your own tool must send one statement per call too, as the TypeORM migration in **Migrations** above does, and a drizzle-kit custom migration takes `npx @nestjs/outbox sql --dialect mysql --statement-breakpoints`, since its MySQL migrator sends one statement per breakpoint.

#### Register the outbox

Register `OutboxModule` in the root module, next to `DrizzleModule`, which registers the Drizzle database, and with the store from [Keep messages in your database](/reliability/outbox#keep-messages-in-your-database). The feature modules it imports are built in the next steps:

[[CODE:10]]

`ClientProxyTransport(ANALYTICS_SERVICE)` is a class that Nest instantiates inside `OutboxModule`, so `transports` sits next to `useFactory`, where classes go. The factory runs when the application starts and returns the rest of the options:

- `transports` and `route`: where each message is published. The `local` transport is built in and runs `@OnOutboxMessage()` handlers in this process ([Handle order.placed in-process](/reliability/outbox#handle-orderplaced-in-process)). `ClientProxyTransport(ANALYTICS_SERVICE)` publishes through the TCP client that `ClientsModule` registers under that name, which is why that module is in `imports` ([Publish to the analytics microservice](/reliability/outbox#publish-to-the-analytics-microservice)). `route` picks exactly one transport per message.
- `relay`: the background publisher. It polls every `pollInterval`, leases what it claims for `lease`, and gives up on a single publish after `publishTimeout`. Setting `OUTBOX_RELAY=off` turns it off in API-only instances ([Run several instances](/reliability/outbox#run-several-instances)).
- `retry`: 10 attempts, with exponential backoff that starts at 1 second and is capped at 1 minute ([Retries and the dead-letter queue](/reliability/outbox#retries-and-the-dead-letter-queue)).

> info **Hint** The tutorial reads `process.env` directly, to stay short. In an application, load the environment through [`@nestjs/config`](/application/configuration) with a validation schema, so a missing `DATABASE_URL` stops the application at startup, and read the values from `ConfigService` in the factories.

Durations are milliseconds or strings such as `'30s'` and `'1m'`. `OutboxModule` is global: `Outbox`, `OutboxStorage`, `OutboxRelay`, `OutboxEvents`, `OutboxDeadLetters` and `OutboxInbox` can be injected anywhere in the application.

#### Save the order and its messages in one transaction

This is the order model:

[[CODE:11]]

`OrdersService.placeOrder()` opens a Drizzle transaction, prices the items, inserts the order and adds the messages, all through the same `tx`:

[[CODE:12]]

`outbox.add()` takes the transaction handle first, then the message or an array of messages. With Drizzle, the handle is the `tx` that `db.transaction()` passes its callback, whose type the service gives the outbox: `Outbox<Transaction>`. The store inserts them through that `tx`, so the messages commit with the order, or roll back with it. The store is asynchronous, so await `add()` like any other query. Every API in the package that joins your transaction takes the handle as its first argument.

A few details:

- **One message per destination.** Each message goes to exactly one transport. The same event goes to the in-process handlers and to the analytics service, so the service adds two messages, `order.placed` and `analytics.order.placed`, in the same transaction.
- **Payloads are snapshots.** `add()` serializes the payload right away, so later changes to the `order` object aren't published.
- **Ids.** Every message gets a time-ordered UUIDv7 `id`. Consumers deduplicate by it.
- **`notify()`.** Nothing is published inside the transaction. After the commit, `notify()` wakes the relay. Without it, the message goes out at the next poll, up to `pollInterval` later.

If anything throws inside the transaction, the order and its messages roll back together, and the relay never sees them. That includes an unknown product, a failed insert, and anything that fails after `add()`. The [Testing](/reliability/outbox#testing) section proves it by failing the transaction after the messages were written.

Pass the transaction, never the database: `outbox.add(this.db, message)` would write the message on its own, in autocommit mode, which is exactly the dual write you're removing. The store refuses it with `OutboxTransactionRequiredError`, and so does `add()` itself when it gets no handle at all.

Expose the service over HTTP:

[[CODE:13]]
