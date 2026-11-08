### Webhooks

`@nestjs/webhooks` sends signed, retried webhooks to your partners after the transaction commits, and verifies the webhooks you receive on their raw body.

An online store for cat food and supplies sells to cat shelters and resellers that buy in bulk, through its API. Northside Pet Supplies, a reseller, places an order and wants to know when it ships and when it's cancelled, without polling: a webhook to its warehouse system. The store receives webhooks too: the payment provider reports payments, and the carrier reports shipments. Both directions look simple, and both go wrong in the same ways:

- **Sending.** A `fetch()` after the order commits is lost when the process dies in between, and sent for a transaction that then rolls back. A retry sends the same event twice without telling the partner so. Every partner writes its own verifier for a homemade signature. A partner that is down for an hour is hammered, a dead endpoint is never turned off, and nobody can answer "did you send it?". And the URL the partner typed is a server-side request forgery waiting to happen: `https://169.254.169.254/` answers with the cloud credentials.
- **Receiving.** The signature is checked on a body the framework parsed and serialized again (a stray space breaks it, and a tampered body can pass), compared with `===` instead of in constant time, with no timestamp window, and a redelivered event runs the handler twice: an order marked paid twice, or shipped twice.

`@nestjs/webhooks` makes both directions one thing to configure. Outgoing webhooks travel through the [outbox](/reliability/outbox): `webhooks.dispatch()` adds the message in the same transaction as the order, and after the commit a worker fans it out to the partner's endpoints, signs each request the way [Standard Webhooks](https://www.standardwebhooks.com) specifies, retries with backoff for about two days, keeps a log of every attempt, and replays on request. Incoming webhooks are one decorator, `@VerifyWebhook()`, which checks the signature on the raw body and skips redeliveries.

In this tutorial, you'll add webhooks to the store's order API, on PostgreSQL with Drizzle:

- Partners subscribe to `order.shipped` and `order.cancelled` through the API, and see their secret once.
- The API sends the webhooks after the commit, signed, and retries them while a partner is down.
- Partners read their delivery log, and ask for a replay.
- The API receives the payment provider's payment webhooks (Standard Webhooks) and the carrier's shipment webhooks (Stripe's scheme), verified on the raw body and processed exactly once.
- Secrets rotate without a gap, and a URL that points inside the store's network is refused.

#### Installation

To get started, install the required dependency:

[[CODE:1]]

The tutorial runs on PostgreSQL, through [Drizzle ORM](https://orm.drizzle.team) and [`@nestjs/drizzle`](/data/drizzle) with the `pg` driver: the endpoints and the delivery log live in the database the orders live in, on a database server that outlives any instance of the application. Using TypeORM, or MySQL? Follow the tutorial, and see "With TypeORM" and "With MySQL" in [Keep webhooks in your database](/http/webhooks#keep-webhooks-in-your-database) for what changes.

Outgoing webhooks are outbox messages, and incoming ones are deduplicated with the outbox's inbox, so the application runs the outbox too (`@nestjs/outbox`, installed and set up in [the outbox tutorial](/reliability/outbox)).

The example application, the online store's order API, keeps its catalog, the partners that call it, and their orders in three tables of its own, which the later sections read and write. They're the example's data, not something webhooks need: the webhooks' and the outbox's tables belong to their stores, which create them, as [Keep webhooks in your database](/http/webhooks#keep-webhooks-in-your-database) shows.

`products` is the catalog:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `text` | Primary key, such as `salmon-kibble-2kg` |
| `name` | `text` | The display name, such as `Salmon kibble, 2 kg` |
| `price` | `integer` | In cents |

`partners` holds the cat shelters and resellers that buy in bulk over the API, and receive its webhooks:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `text` | Primary key, such as `northside` |
| `name` | `text` | The display name, such as `Northside Pet Supplies` |
| `api_key_hash` | `text` | The SHA-256 of the partner's API key, in hex. Unique |

`orders` holds the partners' orders, whose `status` goes from `placed` to `paid` and `shipped`, or to `cancelled`:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `text` | Primary key |
| `partner_id` | `text` | References `partners.id` |
| `items` | `jsonb` | The order's lines, as a JSON array: each line's `productId`, `quantity` and unit `price` (in cents) |
| `total` | `integer` | In cents |
| `status` | `text` | `placed`, `paid`, `shipped` or `cancelled` |
| `payment_id` | `text` | Nullable: set when the order is paid |
| `tracking_number` | `text` | Nullable: set when the order is shipped |

The other columns aren't nullable.

The catalog has two products, `salmon-kibble-2kg` at 2499 cents and `clumping-litter-10l` at 1599 cents, and the two partners have sample API keys (issue real ones from your partner onboarding):

| Partner | `id` | API key |
| --- | --- | --- |
| Northside Pet Supplies, a reseller | `northside` | `partner_northside_7c1d2e` |
| Riverside Cat Shelter | `riverside` | `partner_riverside_91ab44` |

#### Keep webhooks in your database

There's nothing to create for webhooks, or for the outbox they travel through: no tables, entities or Prisma models. Register their two stores, and each creates its own schema, `nest_webhooks` and `nest_outbox`, and migrates it: at startup in development and in tests, and in production with `npx @nestjs/webhooks migrate` and `npx @nestjs/outbox migrate`, or with their `migrationSql()` in your own migrations.

The package keeps the endpoints, with their secrets, the messages it dispatched, their deliveries and the log of every attempt in a **store**, which it reads through two contracts, `WebhookEndpointStore` and `WebhookDeliveryStore`. Until you register one, the module keeps them in memory: fine for a first run, but a restart loses every pending delivery, and two instances don't share them.

> warning **Warning** With `NODE_ENV=production` and no store registered, startup fails, unless you set `allowInMemoryStorage: true`.

On PostgreSQL, register the package's store, `PostgresWebhookStore` from `@nestjs/webhooks/postgres`. The outbox needs one too, for the messages that carry dispatched webhooks out of your transaction and for the inbox that deduplicates incoming ones: `PostgresOutboxStore` from `@nestjs/outbox/postgres`, as in [the outbox tutorial](/reliability/outbox#keep-messages-in-your-database). Both run their SQL through the database client your application already has, and keep their tables in schemas of their own. They're ordinary providers, registered once, in the root module, next to `WebhooksModule` and `OutboxModule`: all four are application-wide. `AppModule` creates each with a factory that injects the Drizzle database and its package's storage registry, which the store registers itself with:

[[CODE:2]]

`fromDrizzle(db)` is the stores' **executor**: it runs their statements through your Drizzle database, whichever driver it uses, such as `pg` or PGlite. `fromPg(pool)`, `fromTypeOrm(dataSource)`, `fromPrisma(prisma)` and `fromKysely(db)` do the same for a node-postgres pool, TypeORM, Prisma and Kysely. `@nestjs/webhooks/postgres` and `@nestjs/outbox/postgres` both export them, so `AppModule` imports `fromDrizzle` once, for both stores. At startup, each module logs the store it uses.

**The schema.** The webhook store keeps its tables in a schema of its own, `nest_webhooks` (the `schema` option names another). On MySQL, which has no schemas, they're tables of the connection's database, with the schema's name as their prefix: `nest_webhooks_endpoints` and so on.

| Table | What it holds |
| --- | --- |
| `nest_webhooks.endpoints` | The partners' endpoints: URL, event types, tenant, and secrets |
| `nest_webhooks.messages` | What was dispatched, byte for byte |
| `nest_webhooks.deliveries` | One per message and endpoint, with its status, attempts and lease |
| `nest_webhooks.delivery_attempts` | The log: every attempt, with the status code, the response and how long it took |
| `nest_webhooks.migrations` | The versions of the store's schema applied |

The outbox's store keeps its messages, dead letters and inbox in `nest_outbox` (`nest_outbox_messages` and so on, on MySQL), as in [the outbox tutorial](/reliability/outbox#keep-messages-in-your-database). They belong to the stores: your migrations don't create them, and your own tables can't collide with them. A few choices in there matter to the package:

- An endpoint's secrets are a JSON array, newest first: during a rotation, the old secret stays for the overlap, with an expiry. With `encryption` configured (see [Register the modules](/http/webhooks#register-the-modules)), what is stored is sealed.
- A message's `body` is `text`, not `jsonb`. It is the exact JSON that was signed and sent, and `jsonb` would reformat it: a partner storing the request and its signature could no longer verify a replay.
- A delivery is unique per message and endpoint. The fan-out that creates deliveries runs after the commit, inside the outbox, so it can run twice; the unique key makes the second run insert nothing.
- No foreign key from a delivery to its endpoint: a deleted endpoint's log stays. Attempts go with their delivery.
- Times are epoch milliseconds (`bigint`), from the package's clock, never the database's.

**Migrations.** The packages ship their schemas as versioned migrations, and the stores apply them themselves. With the `migrate` option, each applies the ones its schema hasn't had yet at startup, before the relay and the worker run, in one transaction that holds an advisory lock: of several instances that start together, one migrates, and the others find nothing left to do. `migrate` defaults to `true`, except with `NODE_ENV=production`. So in development and in tests, the stores create their schemas on the first start, and your migrations only create your own tables.

In production, apply the migrations before the new version of your application starts, as you apply your own, so that no instance changes a schema while it boots: in the middle of a rolling deploy, that would lock busy tables, and a least-privilege database user can't do it anyway. The packages' command lines do it from your deploy step, next to `npx drizzle-kit migrate`. They read the database from `DATABASE_URL`, or from `--url`, and need `pg` installed:

[[CODE:3]]

`status` exits with 1 while the schema is behind, which makes it a check for CI. To apply the migrations with your own migration tool instead, take their SQL from `npx @nestjs/webhooks sql` and `npx @nestjs/outbox sql`, or from `PostgresWebhookStore.migrationSql()` and `PostgresOutboxStore.migrationSql()` in code: the statements of every migration, with the bookkeeping that records the version. Run each in one transaction, as TypeORM's and Drizzle's migrators do. With TypeORM, that's a migration of your own, next to the ones it generates for your entities:

[[CODE:4]]

With drizzle-kit, create a custom migration per store, and fill the file each creates with its SQL, a `--> statement-breakpoint` line between the statements: Drizzle's migrator then runs them one at a time, which PGlite requires. In code, `migrationSql()` with `statementBreakpoints: true` returns the same.

[[CODE:5]]

On MySQL, the stores' `migrationStatements()` return the statements one per string, and a TypeORM migration runs them one per call:

[[CODE:6]]

With `migrate` off, a store whose schema is behind fails the startup with a `WebhookSchemaError` (the outbox's store, with an `OutboxSchemaError`) that names these three ways, and fails every call the same way until the schema catches up, which it notices without a restart. During a rolling deploy, the previous version of your application keeps running on a schema that the new one migrated. There are no down migrations.

**Transactions.** No method of the webhook store takes your transaction. `webhooks.dispatch(tx, ...)` adds the message to the outbox in your transaction, through the outbox's store, and `webhook.processInTransaction(tx, ...)` records an incoming webhook in the outbox's inbox the same way; the fan-out after the commit, the worker and everything else run on the stores' own connections. With Drizzle, `tx` is what `db.transaction()` hands its callback, as the next sections show. The outbox's store refuses the database itself, whose statements would commit on their own, with an `OutboxTransactionRequiredError` that says what to pass. With the other executors, pass a node-postgres client after `BEGIN` (not the pool), TypeORM's `EntityManager` from `dataSource.transaction()`, Prisma's interactive transaction client, or a Kysely transaction.

**Isolation.** The stores rely on READ COMMITTED, PostgreSQL's default isolation level: their statements race each other, and under a stricter level they would fail with serialization errors. At startup, each checks the database's `default_transaction_isolation`, and fails if it's stricter. Your own transactions may run at any level. Under REPEATABLE READ or SERIALIZABLE, though, a copy of an incoming webhook that `processInTransaction()` handles in your transaction, racing the first one's commit, fails with PostgreSQL's serialization error instead of being skipped as a duplicate: the sender gets an error, and its retry finds the webhook recorded.

**With TypeORM.** `TypeOrmModule` takes the place of `DrizzleModule` in `AppModule`, and both stores run on the `DataSource` it provides, through `fromTypeOrm()`:

[[CODE:7]]

Where the tutorial passes Drizzle's `tx` to `dispatch()` and `processInTransaction()`, pass the `EntityManager` that `dataSource.transaction()` hands its callback, and inject `Webhooks<EntityManager>`. The outbox's store refuses `dataSource.manager`, whose writes would commit on their own. This is the order service's `cancelOrder()`, from [Send order.shipped and order.cancelled after the commit](/http/webhooks#send-ordershipped-and-ordercancelled-after-the-commit), with TypeORM:

[[CODE:8]]

Your entities and their migrations stay as they are: `migration:generate` compares only your entities with the database, and leaves the stores' schemas alone.

**With MySQL.** On MySQL 8.4 or 9.x, import the stores and the executor from `@nestjs/outbox/mysql` and `@nestjs/webhooks/mysql` instead. The providers are the same, with `MySqlOutboxStore` and `MySqlWebhookStore`, on a Drizzle database of `drizzle-orm/mysql2`:

[[CODE:9]]

With the other clients, the executor is `fromMysql2(pool)` for a `mysql2/promise` pool, `fromTypeOrm(dataSource)` for a `DataSource` of type `mysql`, `fromPrisma(prisma)` for Prisma through `@prisma/adapter-mariadb`, or `fromKysely(db)` for Kysely's `MysqlDialect`. What differs from PostgreSQL:

- **Tables, not a schema.** MySQL has no schemas inside a database, so the stores keep their tables in the connection's database, the one in the URL's path, next to yours, and `schema` becomes their prefix: `nest_webhooks_endpoints`, `nest_webhooks_deliveries` and so on, and `nest_outbox_messages` for the outbox. It takes lowercase letters, digits and underscores, at most 40 characters.
- **Your transactions.** `dispatch()` and `processInTransaction()` work at REPEATABLE READ, MySQL's default, as at READ COMMITTED: there's nothing to configure, and the stores don't check the database's default. When MySQL breaks a deadlock in your transaction (error 1213), it rolls the whole transaction back, and the client's error reaches your code: run the transaction again. The stores run their own transactions again themselves. With `processInTransaction()`, that can happen when copies of one webhook arrive at once and the first one's transaction rolls back: the sender gets an error, and its retry goes through.
- **Keys are bounded.** Ids and tenants are indexed columns: at most 255 characters, 256 for a tenant, which the package's own ids and its limit on `tenant` stay within. An incoming webhook's id goes into the inbox's key, of at most 255 characters too, and the verifier refuses a longer id on every database, with a 401, before the handler runs.
- **Migrations aren't one transaction.** MySQL commits each DDL statement on its own, so `migrate` applies the statements one at a time, under a lock (`GET_LOCK()`), and a run that failed resumes at the statement it stopped at. Your own tool must send one statement per call too, as the TypeORM migration in **Migrations** above does. The command lines take a `mysql://` URL, and `sql --dialect mysql` prints MySQL's SQL: add `--statement-breakpoints` for a drizzle-kit custom migration, since its MySQL migrator sends one statement per breakpoint.
- **The server.** The stores check it at startup, and refuse MariaDB, a connection without a database, and a `sql_mode` that isn't strict (MySQL's default is). Keep `NO_BACKSLASH_ESCAPES` out of it too.

For another database, write a store of your own: [The store contract](/http/webhooks#the-store-contract) says what it must do.

#### Register the modules

Register `OutboxModule` and `WebhooksModule` in the root module, next to `DrizzleModule`, which registers the Drizzle database, with both stores in its `providers`. The feature modules are built in the next sections:

[[CODE:10]]

`WebhooksModule` needs the outbox: `dispatch()` is an `Outbox.add()`, and the fan-out that turns a committed message into deliveries is an outbox handler. Without `OutboxModule`, startup fails and says so. The outbox's `relay` hands committed messages to the fan-out, polling every second, and `OUTBOX_RELAY=off` turns it off. The rest of the options, resolved when the application starts:

- `eventTypes`: the message types this application sends. `dispatch()` refuses any other, and so does an endpoint that tries to subscribe to one, with the known types in the message.
- `retry`: the vocabulary shared with the outbox, the HTTP client and resilience. Ten attempts, and a backoff that starts at 5 seconds, grows fourfold and is capped at a day, with jitter: what the Standard Webhooks spec recommends, "a retry schedule spanning multiple days".
- `disableEndpointAfter`: an endpoint that has failed every attempt for five days without a single success is switched off, and its owner is told (see [Retries, the delivery log and replay](/http/webhooks#retries-the-delivery-log-and-replay)).
- `delivery`: one attempt has 15 seconds for DNS, the connection, TLS, the request and the response. `allowHttp` and `allowPrivateNetworks` are off by default: only public `https://` endpoints are accepted. `WEBHOOKS_ALLOW_LOCAL=1` turns them on in development, where the partner's receiver runs on this machine. Cloud metadata addresses stay blocked even then.
- `worker`: the background deliverer, one per process. `WEBHOOKS_WORKER=off` turns it off in instances that only serve the API.
- `encryption`: endpoint secrets sealed at rest, with the family's shape: the first key encrypts, every key decrypts. Optional, from `WEBHOOKS_ENCRYPTION_KEYS`.

> info **Hint** The tutorial reads `process.env` directly, to stay short. In an application, load the environment through [`@nestjs/config`](/application/configuration) with a validation schema, so a missing variable stops the application at startup rather than at the first request, and read the values from `ConfigService` (`inject: [ConfigService]` in the factories).

Durations are milliseconds or strings such as `'15s'` and `'5d'`. Both modules are global: `Webhooks`, `WebhookEndpoints`, `WebhookDeliveries`, `WebhooksEvents` and `WebhooksStorage` can be injected anywhere. `main.ts` binds the validation pipe for the partner API's DTOs (see the next section), and enables the shutdown hooks, so a deploy lets the relay and the worker finish their in-flight work:

[[CODE:11]]

At startup, both modules log the store they use, and on the first start, the stores log the schemas they created:

[[CODE:12]]
