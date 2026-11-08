### Idempotency keys

`@nestjs/idempotency` makes routes, GraphQL mutations and message handlers safe to retry: each `Idempotency-Key` runs the handler once, and retries get its result.

A customer of an online store for cat food and supplies pays for salmon kibble and cat litter in the store's mobile app, on a phone on a train. The app sends `POST /orders/ord_1001/pay`. The server charges the card through the payment provider, but the response never reaches the phone. The app can't tell a lost request from a lost response, so it retries. Without protection, the retry goes wrong in one of two ways:

- It arrives after the first request finished. The order is already `paid`, so the customer gets an error for a payment that went through.
- It arrives while the first request is still waiting for the payment provider. Both requests pass the "is the order still pending?" check, and the card is charged twice.

An **idempotency key** fixes both. The client generates a unique key for each payment attempt and sends it in the `Idempotency-Key` header with every retry. The server runs the handler once per key, stores the result, and answers every retry with that result. `@nestjs/idempotency` implements this for HTTP routes, GraphQL mutations and microservice handlers with one decorator, `@Idempotent()`. Its HTTP behavior follows the IETF [Idempotency-Key header draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/).

In this tutorial, you'll make the payment endpoint idempotent, teach the mobile app to retry safely, move the keys to PostgreSQL (or to Redis), encrypt the stored receipts, protect the GraphQL mutation, and deduplicate the `order.paid` events that the shipping service consumes.

#### Prerequisites

This tutorial starts from the store's order API, which already has:

- An `OrdersModule` with an `OrdersService` and an `OrdersController`. An `Order` has an `id`, a `userId`, `items`, a `total` in cents, and a `status` of `'pending'`, `'paid'`, `'shipped'` or `'refunded'`.
- A `PaymentProviderClient` that wraps the payment provider's SDK. It throws a 402 `HttpException` when a card is declined, and a `ServiceUnavailableException` (503) when the provider is down.
- An `AuthGuard` that validates the bearer token and sets `req.user` (see [Authentication](/security/authentication#issue-tokens-to-the-mobile-app)), plus a `@CurrentUser()` parameter decorator that reads it.
- A global `ValidationPipe`, and a TCP client for the shipping service, registered as `SHIPPING_SERVICE`.
- Its data in PostgreSQL, through Drizzle, with the database registered by `@nestjs/drizzle` (see [Drizzle](/data/drizzle)). Using TypeORM? [Store keys in PostgreSQL](/reliability/idempotency#store-keys-in-postgresql) ends with the store for TypeORM.

This is the method we need to protect:

[[CODE:1]]

The status check can't stop a double charge on its own: two requests that arrive together both see `pending` before either one reaches `markPaid()`.

Install the package:

[[CODE:2]]

#### Make the payment endpoint idempotent

Register `IdempotencyModule` once, in the root module:

[[CODE:3]]

The module is global. It registers one app-wide interceptor, which does nothing for handlers that aren't marked with `@Idempotent()`, so no other route changes behavior.

`scope` gives every user's keys their own namespace. Without it, all clients share one namespace, and a key that one user picks could replay another user's receipt. With it, Alice and Bob can both send `Idempotency-Key: 1` without ever seeing each other's results. Because guards run before interceptors, `req.user` is already set when `scope` runs, and an unauthenticated request is rejected before it can use up a key. If a signed-in user calls an `@Idempotent()` handler that has no `scope`, the module logs a warning, once for each handler. Where one shared namespace is deliberate, such as a webhook keyed by the provider's event ids, set `scope: false`.

Now mark the handler:

[[CODE:4]]

`required: true` rejects a request without a key with a 400 `IDEMPOTENCY_KEY_REQUIRED` error, before the handler runs. A payment without a key can't be retried safely, so it's better to refuse it than to charge the card unprotected.

Here's what happens to a request that carries a key:

1. The interceptor computes a **fingerprint** of the request: a SHA-256 hash of the scope, the method, the URL (which includes the order id) and the body, with object keys sorted.
2. It atomically takes a lock on the **record key** `<scope>:<key>`, for example `usr_alice:5e0f6d0e-…`. If a record already exists, the handler doesn't run (see the table below). While the handler runs, the interceptor keeps renewing the lock, so a slow handler never loses it to a retry.
3. The handler runs. When it finishes, the lock becomes a completed record that holds the response: the status code, the body, and the headers from a short allowlist (`Location`, `Content-Type`, `Content-Language`, `Content-Location`, `ETag` and `Last-Modified`) if the handler or a middleware set them. They describe the stored body, so a retry sent with another `Accept-Language` still gets the stored body's `Content-Language`. Cookies, CORS and rate-limit headers belong to the original request and are never replayed.

Every later request with the same key gets one of these answers:

| Situation                              | Response                                                                                |
| -------------------------------------- | --------------------------------------------------------------------------------------- |
| The first request is still running     | 409 `IDEMPOTENCY_KEY_IN_USE`, with a `Retry-After` header                               |
| The first request completed            | The stored status and body, plus `Idempotent-Replayed: true`. The handler doesn't run.  |
| Same key, but a different body or URL  | 422 `IDEMPOTENCY_KEY_REUSED`                                                            |

Errors can be stored too. [Tune TTLs and failure handling](/reliability/idempotency#tune-ttls-and-failure-handling) covers which ones.

Because the interceptor is global, it runs outside the interceptors of your controllers and handlers. The stored body is exactly what the client received, after serializers and other interceptors ran, and a replay skips all of them. Pipes run inside it, so a `ValidationPipe` 400 is stored like any other client error. Other global interceptors are a different matter, as the production checklist explains.

Until you [store keys in PostgreSQL](/reliability/idempotency#store-keys-in-postgresql), records live in memory, in the default `InMemoryIdempotencyStore`. That's fine for a single instance in development, but every instance of the API has its own records, and they're lost on restart. When `NODE_ENV` is `production`, the app refuses to start this way, with an error that says how to register a store.

#### Send keys from the mobile app

The server can only deduplicate what the client sends consistently. The app follows two rules:

- It creates the key when the customer taps **Pay**, not once per request. Every retry of that payment sends the same key, even after the app is killed and restarted, so the key is saved with the pending payment.
- It creates a new key only for a new decision by the customer, such as choosing another card after a decline. Sending an old key with a different body is a 422.

[[CODE:5]]

`crypto.randomUUID()` is available in browsers and Node.js. In React Native, use a UUID library, such as `randomUUID()` from `expo-crypto`.

These are the responses the app can get, and what they mean for a retry:

| Response                                                      | Meaning                                                                  | Retry with the same key?                          |
| ------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------- |
| No response (network error, timeout)                          | The card may or may not have been charged                                | Yes                                               |
| 2xx                                                           | Done. With `Idempotent-Replayed: true`, it's the first attempt's result  | No, show the receipt                              |
| 409 with the code `IDEMPOTENCY_KEY_IN_USE`                    | The first attempt is still running                                       | Yes, after `Retry-After` seconds                  |
| 5xx                                                           | The attempt failed, and the server released the key                      | Yes, with backoff                                 |
| 429                                                           | Rate limited before the handler ran                                      | Yes, after `Retry-After` seconds                  |
| 422 `IDEMPOTENCY_KEY_REUSED`                                  | A bug: the key was reused for a different request                        | No                                                |
| Any other 4xx: 400, 402 (declined), 404, 409 (already paid)   | Final. Every retry with this key gets the same answer                    | No. Show the error; a new attempt gets a new key  |

Check `code`, not just the status. A 409 can also mean that the order is already paid, and that one is final.

#### Store keys in PostgreSQL

The in-memory store isn't enough in production. Its records vanish whenever the process stops, on every deploy or replaced container, so a retry that arrives afterwards runs the payment again. And once the API runs on more than one instance, a retry that lands on another instance wouldn't find the record, and two instances could both take the lock. The records need a shared store that can "create unless it exists" atomically.

`@nestjs/idempotency` doesn't ship one. It defines the contract, the `IdempotencyStore` interface, and you implement it in a provider of your app, with the database or the Redis client it already has. The interface has four methods. Each one takes the record key and an owner first, and durations arrive in whole milliseconds:

- `acquire(key, owner, fingerprint, lockTtl)` creates the lock, or returns the existing record: in flight, or completed with its response. It must be atomic: of any number of concurrent calls for a free key, exactly one may win.
- `complete(key, owner, response, ttl)` turns the lock into a completed record, if `owner` still holds it.
- `release(key, owner)` deletes the lock, if `owner` still holds it, so a retry can run the handler again.
- `extend(key, owner, lockTtl)` resets the lock's expiry to `lockTtl` from now, if `owner` still holds it. The interceptor calls it every `lockTtl / 3` while the handler runs and its result is being stored.

`owner` is a random id for each attempt, known as a fencing token. If an attempt stops renewing its lock (its instance crashed, say) and a retry takes over after `lockTtl`, the old attempt's `extend()`, `complete()` or `release()` does nothing, instead of overwriting the retry's record. So "if `owner` still holds it" has to be checked in the same atomic operation that writes: checked in a separate read first, a takeover could slip in between.

This section shows that store twice: first with Drizzle, which is the tutorial's path, and then, under "With TypeORM" at the end of the section, the same store for an application whose ORM is TypeORM. Take one of the two.

The store keeps its data in PostgreSQL, with Drizzle, so the records get a table in its Drizzle schema:

[[CODE:6]]

The primary key is a SHA-256 hash of the record key, because record keys (a scope, the client's key and, for GraphQL, the field's path) can be longer than PostgreSQL allows in an index entry. The response is `json` rather than `jsonb`, because `jsonb` rejects a `\u0000` inside a string, and a response body can contain one. Generate the migration with drizzle-kit, and apply it with `npx drizzle-kit migrate` as usual:

[[CODE:7]]

[[CODE:8]]

The store implements each method with Drizzle's query builder. It injects the database with `@InjectDrizzle()` from `@nestjs/drizzle`, and the constructor registers the store with `IdempotencyStorage`, a registry that `IdempotencyModule` exports:

[[CODE:9]]

The database is typed as `NodePgDatabase`, and the tests below cast their PGlite database to it, since the store only uses the query builder both drivers share. Each method is a single statement that PostgreSQL runs atomically, without a transaction:

- `acquire()` inserts the lock, or takes over an expired row, with one `INSERT ... ON CONFLICT DO UPDATE ... WHERE expires_at <= now`. When several callers race for a key, PostgreSQL lets one of them write and checks the `WHERE` again for the others against the winner's row, so they get no row back and read the winner's lock instead. If that row disappears in between (released, or expired), `acquire()` goes round again.
- `complete()`, `extend()` and `release()` check the owner, and that the lock hasn't expired, in the `WHERE` of the statement that writes. They count the rows that `returning()` gives back, which works the same on every Drizzle driver.
- Expired rows are ignored at once, and the next request with the same key reuses its row. To delete the rest, call `prune()` from a scheduled job, for example with `@Interval()` from `@nestjs/schedule`. It checks the expiry again in the `DELETE` itself, so a row that a retry took over in the meantime stays.

Expiry times come from each instance's clock (`Date.now()`), so keep the clocks in sync, as NTP does. Every idempotent request adds one or two statements to the connection pool, plus an `UPDATE` every `lockTtl / 3` while its handler runs.

The store is an ordinary provider. Register the database with `DrizzleModule` (see [Drizzle](/data/drizzle)), and add the store to the providers of `AppModule`:

[[CODE:10]]

> info **Hint** The app reads `DATABASE_URL`, and, once receipts are encrypted, `IDEMPOTENCY_KEYS`, from `process.env`. An application loads its environment through `@nestjs/config`, with a validation schema that stops startup when a variable is missing, and injects `ConfigService` into these factories instead.

At startup, the module logs the store it uses, `IdempotencyStorage: DrizzleIdempotencyStore`, and then it stops taking registrations:

- An app has one store. A second `registerSource()` call throws, naming both classes.
- Register from the constructor of a singleton provider. The registry locks when `IdempotencyModule` initializes, so a store that registers later (from a lifecycle hook, per request, or in a lazy-loaded module) throws instead of being silently ignored.
- Without a registered store, the module keeps records in memory. In production (`NODE_ENV=production`), it refuses to start that way, unless you set `allowInMemoryStorage: true`, which accepts that every restart or deploy forgets the records.

Every store is tested with the same contract suite, which `@nestjs/idempotency/testing` exports as plain test cases for any test runner. It covers each method, the owner checks, expiry, and, with `concurrent`, the races that a store that reads and then writes gets wrong. The example project runs it against this store on PGlite, and on PostgreSQL through a `pg` pool, where 32 callers race for each key on up to 16 connections:

[[CODE:11]]

**With TypeORM.** The same store for an application whose ORM is TypeORM, on the same table. Drizzle stays the tutorial's path: take this store instead of the one above, not next to it. The table is an entity, and every column states its type, so that the TypeORM CLI, which loads it without decorator metadata, sees the same schema as the application:

[[CODE:12]]

TypeORM returns a `bigint` column as a string, so a transformer reads `expiresAt` back as a number. The response column is typed `object` rather than `IdempotencyStoredPayload`, because the payload's `unknown` body doesn't fit TypeORM's insert types; the store casts it when it reads a record. The TypeORM CLI and `TypeOrmModule` share one set of options, in a data source file:

[[CODE:13]]

Generate the migration from the entity, apply it, and check that the entity and the database agree. The CLI needs a TypeScript loader for the data source file; this uses `tsx`:

[[CODE:14]]

The migration it wrote, `1790321611502-Idempotency.ts`, is the `CREATE TABLE` and `CREATE INDEX` statements of the Drizzle migration, and `migrations` in the data source lists it. Now the store, under the same rules as the Drizzle one:

[[CODE:15]]

- **`acquire()`** is the same `INSERT ... ON CONFLICT DO UPDATE ... WHERE expires_at <= now`, through the insert query builder: `orUpdate()` lists the columns a takeover overwrites, its `overwriteCondition` option is the `WHERE`, and `returning()` gives back a row only to the caller that wrote.
- **`complete()`, `extend()` and `release()`** are `update()` and `delete()` on the entity manager, with the owner and `MoreThan(now)` in their criteria, and they read `affected`. Never `save()`: it reads the row first, so a takeover could slip in between.
- **`prune()`** builds the subquery that picks the expired rows with a select query builder, and puts its SQL in the `WHERE` of the `DELETE`, next to the expiry check.

The store injects the `DataSource` that `TypeOrmModule` provides. Register the module with the data source's options in place of `DrizzleModule`, and the store in place of `DrizzleIdempotencyStore`:

[[CODE:16]]

The contract suite runs on it unchanged. TypeORM connects through `pg`, so the suite needs a PostgreSQL server and is skipped without one. One more case checks that the entity and the migration agree, which is what `migration:generate --check` checks:

[[CODE:17]]

`startPostgres()` is a test helper that creates a throwaway database on a PostgreSQL server, or skips the suite without one. The example also runs two instances of the TypeORM `AppModule` on one database, one charging while the other answers 409.

> info **Hint** Using Prisma? [The store contract](/reliability/idempotency#the-store-contract), after the tutorial, shows how Prisma expresses these statements. Check your store with the same suite.

#### Store keys in Redis instead

If your API already runs Redis, it can keep the records there instead of in PostgreSQL. Redis suits this store well: a record is a small hash that Redis expires on its own, so there's no pruning job, and a hot key, such as a client retrying one payment every second, costs a round trip to memory instead of a row lock in the primary database. The price is a second store to run, protect and back up, and Redis has to be configured never to evict the records (see the production checklist).

Each method is one Lua script, which Redis runs atomically:

[[CODE:18]]

Each record is a hash at `idem:<scope>:<key>`, with the fields `state`, `fp` (the fingerprint), `owner` and `resp` (the stored response as JSON). The hash expires on its own: `lockTtl` after the last renewal while it's in flight, and after `ttl` once it's completed, so no cleanup job is needed. Each script touches a single key, so the store also works with Redis Cluster. Redis runs a script atomically, but it doesn't undo the script's writes when a later command fails. `PEXPIRE`, for one, rejects a fraction of a millisecond, and failing after the `HSET`, it would leave a lock that never expires. That's why the interceptor hands the store whole milliseconds.

Nest injects the Redis client, and the constructor registers the store, as in the PostgreSQL store. An app has one store, so `RedisIdempotencyStore` takes the place of the other one in `AppModule`:

[[CODE:19]]

`RedisModule` stands for your app's Redis module: a global module that provides an ioredis client under the `REDIS` token, for example with `useFactory: () => new Redis(process.env.REDIS_URL!)`, and closes it with `quit()` in its `onApplicationShutdown()`, after the package has finished the requests in flight. `RedisClient` asks for nothing but `eval()`, which an ioredis `Redis` instance provides as is. At startup, the log line reads `IdempotencyStorage: RedisIdempotencyStore`, and the registry's rules from the PostgreSQL store apply: one store, registered from a constructor.

The example project runs the contract suite against this store too:

[[CODE:20]]

> info **Hint** This tutorial's example project has no Redis server, so its tests run the store against an in-process fake that implements the same four scripts in JavaScript. That covers the store's logic and the way it reads replies, but not the Lua itself. Run the contract suite against a real Redis, for example in a container, before you rely on the store. Without `advanceTime`, the suite waits for real expiry, which takes about ten seconds.

The remaining steps show `DrizzleIdempotencyStore` in their module listings. With Redis, register `RedisIdempotencyStore` in its place: encryption, the shipping service and the tuning options work the same, and with encryption on, the `resp` field holds the sealed envelope instead of the `response` column.
