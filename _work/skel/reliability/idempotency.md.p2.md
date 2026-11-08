#### Encrypt stored receipts

The stored response is the whole receipt: the payment provider's receipt id, the amount, and the card's last four digits. They sit in `idempotency_keys` in plain text, in every backup and every dump of the database, so encrypt the records at rest.

The encryption keys are secrets that the app should read when it starts, not when `app.module.ts` is imported, so switch to `forRootAsync()`. The store stays as it is, a provider of `AppModule` that registers itself, and the factory returns the options:

[[CODE:21]]

Generate a key with `openssl rand -base64 32`, and store it in your secret manager as `IDEMPOTENCY_KEYS`. With encryption on, the `response` column holds a sealed envelope, `v1.<keyId>.<iv>.<ciphertext>.<tag>`, instead of the receipt:

- Records are encrypted with AES-256-GCM, with a random IV for each record.
- The fingerprint stays in plain text. The store has to compare it, and it's a hash anyway.
- The record key is authenticated along with the data, so a record copied under another user's key fails to open instead of replaying there.
- While encryption is on, plain-text records are rejected, so nobody with write access to the table can plant a response.
- A string key must be at least 32 characters, and it's expanded with HKDF-SHA256. That's fine for a random secret like the one above, but it isn't a password hash, so don't use a password that a person chose. A shorter key, or one with spaces around it (`IDEMPOTENCY_KEYS=new, old` splits into a second key that starts with a space), stops the app at startup, with an error that names it.

Turn encryption on before the endpoint stores its first record. It changes the record format both ways: a plain-text record stored before the switch, like a sealed record after encryption is turned off, fails to open until it expires, and its replays get the 500 described below.

To rotate the key without breaking replays:

1. Generate a new key and deploy `IDEMPOTENCY_KEYS=old-key,new-key`. Instances still seal records with the old key, but they can open records sealed with the new one.
2. Once every instance runs that configuration, deploy `IDEMPOTENCY_KEYS=new-key,old-key`. New records are sealed with the new key, and old records still open. During the rolling deploy, instances that haven't restarted yet can already open the new records, thanks to the first step.
3. When `ttl` has passed (48 hours, see [Tune TTLs and failure handling](/reliability/idempotency#tune-ttls-and-failure-handling)), every record sealed with the old key has expired. Deploy `IDEMPOTENCY_KEYS=new-key`.

If you remove a key too early, replays of records sealed with it **fail closed**. The client gets a 500 `IDEMPOTENCY_RECORD_UNREADABLE` error, the failure is logged, and the handler doesn't run again: the record proves that the card was already charged, so running the handler could charge it twice. The error stops when the record expires.

#### Pay through GraphQL

The store's website pays through a GraphQL mutation. Register `GraphQLModule` in `AppModule`:

[[CODE:22]]

Then add the mutation to the orders resolver, next to its queries. In GraphQL, the key can come from the `Idempotency-Key` header, as with REST, or from an argument. An argument puts the key in the schema, where code generators and reviewers can see it. It also suits GraphQL clients, which usually set headers once per connection rather than per operation. `@Idempotent()` reads a mutation's `idempotencyKey` argument when it has one, and the header otherwise, so the resolver only has to declare the argument:

[[CODE:23]]

`PayOrderDto` is the class the REST endpoint uses, with `@InputType()` and `@Field()` added, and `PaymentReceipt` is an `@ObjectType()` with the receipt's fields. The resolver uses the same `AuthGuard`, which reads the request from the GraphQL context. The module's `scope` receives that same request, so keys are per user here too. The argument is a non-null `String`, so GraphQL validation already rejects an operation without it:

[[CODE:24]]

A retry with the same variables returns the stored `payOrder` result, with the same types the resolver returned, so a `Date` field replays as a `Date`. The record key gets the field's path appended, as in `usr_alice:<key>:payOrder`, because one operation can contain several mutations. Each field is stored and replayed on its own, and aliases are part of the path, so a retry must send the same document.

A rejection is an error on that field, not an HTTP status. The response is still a 200, because other fields in the same operation may have succeeded, and the status and the retry delay are in `extensions` (`locations` omitted):

[[CODE:25]]

For the same reason, GraphQL replays don't set the `Idempotent-Replayed` header.

#### Deduplicate order.paid events

After a payment, `OrdersService` emits an `order.paid` event, and the shipping service arranges a courier. In practice, events are delivered at least once. A publisher that retries after a timeout, or a broker (RabbitMQ, Kafka, NATS JetStream) that redelivers an unacknowledged message, can deliver the same event twice, and the customer gets two parcels.

Deduplicating events needs an id that's the same for every delivery of an event, so it's derived from the data rather than generated on each send. An order is paid once, so `OrdersService` uses `order-paid:` followed by the order id. Mark the [event handler](/microservices/basics#event-based) with `@Idempotent()`, and point `keyFrom` at that id:

[[CODE:26]]

By default, microservice handlers read the key from the payload's `idempotencyKey` property, then from a transport header named by the `header` option. Here, `keyFrom` reads `eventId` instead, and `required: true` rejects events that don't have one.

The shipping service is a separate application, with its own database and its own `IdempotencyModule`, and it registers the same store class:

[[CODE:27]]

[[CODE:28]]

A few details differ from the API:

- There's no `scope`, because event ids are unique across the whole system.
- `ttl` is 7 days, because a message can come back from a dead-letter queue long after it was first handled.
- Records belong to a handler: the record key ends with the handler's class and method, as in `order-paid%3Aord_1001:ShippingController.onOrderPaid`. Nest runs every handler registered for an event, so a second handler for `order.paid`, one that emails the tracking number, say, keeps its own records and still handles every event once.

A duplicate event is handled in one of two ways:

- If the first delivery has completed, the duplicate is skipped. The stored result is "replayed", and since events have no reply, nothing happens.
- If the first delivery is still running, the duplicate is rejected with `IDEMPOTENCY_KEY_IN_USE`, and Nest logs the error. With a transport that acknowledges messages, such as RabbitMQ or Kafka, don't acknowledge that delivery as processed. Let the transport redeliver it later, when it'll be skipped.

Either way, the courier is booked once. Retries of the HTTP payment don't produce duplicate events in the first place, because a replayed request never reaches `OrdersService`.

#### Tune TTLs and failure handling

The defaults are a starting point. This is the API's final configuration:

[[CODE:29]]

Every duration takes milliseconds, or a string such as `'45s'`, `'48h'` or `'7d'`. A value that doesn't parse stops the app at startup, with an error that names the option.

- **`ttl`** (default: `'24h'`) is how long a completed result can be replayed. It must be longer than the longest time a client keeps retrying. The app queues payments made offline for up to a day, so it's 48 hours here. After `ttl`, the key is forgotten, and a retry runs the handler again. In this app, that ends in a 409 "already paid" error rather than a second charge, but the customer doesn't get the receipt.
- **`lockTtl`** (default: `'60s'`) is how long an in-flight lock survives after the instance running the handler crashes. While the handler runs, the interceptor renews the lock every `lockTtl / 3`, here every 15 seconds, so a charge that takes longer than 45 seconds still keeps it, and a retry gets a 409. Once renewals stop, the lock expires and a retry takes over the key. A shorter `lockTtl` frees keys sooner after a crash, but renews more often. If the store can't be reached to renew a lock, the interceptor logs a warning that the lock was lost.
- **`retryAfter`** (default: `'1s'`) is the value of the `Retry-After` header on a 409, in whole seconds. Card charges usually take a second or two, so the API asks clients to wait 2 seconds rather than check back after one.

`@Idempotent()` accepts `required`, `ttl`, `lockTtl`, `retryAfter`, `keyFrom`, `scope`, `fingerprint` and `storeIf`, which override the module's options for that handler. `fingerprint` selects what a retry must repeat, for example the body without a client timestamp; the method and the URL always count. The decorator also works on a controller or resolver class, where it covers the handlers that change state: GET routes and GraphQL queries are skipped unless they have their own `@Idempotent()`. A handler's own `@Idempotent()` is merged with the class's options, so a class-level `required: true` still applies to a handler that only sets `lockTtl`.

A `scope` function runs for every kind of handler, and what it receives depends on the handler: the request for HTTP and GraphQL, but the message payload for a microservice handler. In an app that serves both from one `IdempotencyModule`, pass `scope` an object instead, with one function per context under the `http`, `graphql` and `rpc` keys. Each function is typed for what its context passes in, and a context without one isn't scoped.

Not every outcome is stored. By default, anything below 500 is:

| Outcome                                                                     | Default                                                     | Why                                                        |
| --------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------- |
| 2xx                                                                         | Stored and replayed                                         | The payment succeeded                                      |
| 4xx `HttpException` (validation 400, declined 402, 404, 409 already paid)   | Stored, and thrown again on every replay                    | It's deterministic: the same request gets the same answer  |
| Another error with a 4xx `status` (`AuthorizationError`, 403)               | Stored as Nest's exception for that status, and replayed    | Its package turns it into that status                      |
| 5xx or an unknown error (payment provider 503, database down)                        | Not stored. The key is released, so a retry runs again      | Most failures happen before the side effect                |
| `StreamableFile`, streams, `@Res()` without `passthrough`                   | Not stored. The key is released, and a warning is logged    | They can't be replayed                                     |

A replayed error is rebuilt as a plain `HttpException` with the stored status and body, and it passes through your exception filters again. A filter that checks `instanceof` against a custom exception class sees the base class on a replay.

The `storeIf` option changes the rule. It receives the status and, when the handler threw, the error. For example, `storeIf: () => true` stores 5xx errors too, as Stripe does. That matters for the one gap the default leaves: a 5xx that happens **after** the side effect. If the payment provider charges the card and then `markPaid()` fails, the key is released, and the retry charges again. There are three ways to close the gap:

- Pass the payment provider a key derived from the user's id and the idempotency key. Most payment providers accept an idempotency key of their own, so the provider deduplicates the charge too. The idempotency key alone isn't enough, because two users can send the same one.
- Store 5xx errors for this handler with `storeIf`, and have the app start a new attempt after a 5xx. To store only the failure that follows a charge, throw a dedicated exception there and check for it: `storeIf: (status, error) => status < 500 || error instanceof ChargeCapturedError`.
- Write the payment and the event in one transaction, with a [transactional outbox](/reliability/outbox#prerequisites).

#### Try it

Start the shipping service, and the API with `DATABASE_URL` (migrations applied), `IDEMPOTENCY_KEYS` and the payment provider's sandbox configured. The sandbox takes about half a second to answer. The outputs below are trimmed to the relevant headers.

A payment without a key is refused:

[[CODE:30]]

The first call with a key charges the card:

[[CODE:31]]

A retry with the same key gets the same receipt, down to `paidAt`, and the payment provider isn't called:

[[CODE:32]]

The same key with a different card is a client bug:

[[CODE:33]]

Finally, send two requests with a new key at the same time, for the other order. One is charged, and the other gets a 409 with `Retry-After: 2` while the payment provider is still working:

[[CODE:34]]

> info **Hint** `--json` needs curl 7.82 or later, and `%header` in `-w` needs curl 7.84 or later.

#### Testing

In end-to-end tests, keep the app's real configuration, but override the `DrizzleIdempotencyStore` provider with a plain `InMemoryIdempotencyStore`. A plain instance doesn't register itself, so the module falls back to its in-memory store, and since Nest never creates `DrizzleIdempotencyStore`, nothing queries the database (a node-postgres pool connects on the first query, so `DrizzleModule` opens no connection either). The encryption key still comes from `IDEMPOTENCY_KEYS`, so set it in the test environment, for example with `test.env` in `vitest.config.mts`.

Mock the payment provider with a small delay, so that two requests sent together overlap:

[[CODE:35]]

Once the app is initialized, `app.get(IdempotencyStorage).source` returns the store in use, here the in-memory one. Its `peek(key)` method returns the raw record under a record key such as `usr_alice:key-1` (`state`, `fingerprint` and `response`), for assertions such as "the declined payment was stored". Test your own store separately, with the contract suite from [Store keys in PostgreSQL](/reliability/idempotency#store-keys-in-postgresql), against a real server. To keep the Drizzle store in end-to-end tests instead, replace the database that `DrizzleModule` registered, with `overrideProvider(getDrizzleToken()).useValue(db)` (`getDrizzleToken` comes from `@nestjs/drizzle`), where `db` is a Drizzle database on PGlite migrated with your migrations. The example project tests encryption, GraphQL, events and tuning that way.

See [End-to-end testing](/fundamentals/testing#end-to-end-testing) for more about the testing setup.

#### Production checklist

- Register a shared store (your database, or Redis), even for a single instance: in-memory records are lost on every restart or deploy, and a retry after one runs the handler again. Run the contract suite against it with `concurrent` on. In production, the app refuses to start without one, unless `allowInMemoryStorage` is set. With Redis, configure `maxmemory-policy noeviction`. A record evicted early is a double charge waiting to happen, and since every idempotency record has a TTL, the `volatile-*` policies would evict them too.
- Set `required: true` on every endpoint that moves money or creates something a customer would notice twice.
- Set `scope` for every client-facing endpoint. Without it, one user's key can replay another user's response. The module logs a warning when a signed-in user calls a handler that has none.
- Keep the idempotency interceptor outside your other global interceptors. Global interceptors run in the order they were registered, and the `APP_INTERCEPTOR` providers of `AppModule` register before those of the modules it imports, so they run outside it and see every replay. The module warns about them at startup. It refuses to start when one of them is `ClassSerializerInterceptor`, because a replay would hand it a plain object and send the fields that `@Exclude()` hides. Register such interceptors with `app.useGlobalInterceptors()` in `main.ts`, or in a module imported after `IdempotencyModule`.
- With a database store, create its table through your migrations, size the connection pool for its statements, keep the instances' clocks in sync, and call `prune()` on a schedule.
- Keep `ttl` above the client's retry window. `lockTtl` only needs to cover a crash, since the lock is renewed while the handler runs.
- Watch the events. `IdempotencyEvents` is injectable, and its `events$` stream reports every replay, every rejection with its `code`, and every lost lock. The same events are published on the `nestjs:idempotency:replayed`, `nestjs:idempotency:rejected` and `nestjs:idempotency:lock-lost` diagnostics channels for tracing tools. Alert on `lock-lost`: it means the attempt's outcome isn't in the store, because renewals failed (the store was unreachable, or the event loop was blocked for longer than `lockTtl`) or because the store failed when the result was written, and a retry may run the handler again.
- Turn on `encryption` when responses contain personal or payment data, before the endpoint stores its first record. Keep the keys in a secret manager, rotate them in the three steps above, and never remove a key before `ttl` has passed.
- Pass the payment provider a key derived from the user's id and the idempotency key, to cover a failure after the charge.
- When several services share one Redis, give each one its own key prefix (the `idem:` in the store) or its own database. Record keys are only unique within one service: two services can each have a handler class with the same name, and a client could send one key to both.
- Keep the state check in the service, ideally as a conditional database update. An idempotency key deduplicates retries of one attempt, but two taps that create two keys are two attempts.
- Let browsers send the header. For cross-origin clients, add `Idempotency-Key` to the CORS `allowedHeaders`, and `Idempotent-Replayed` and `Retry-After` to `exposedHeaders`.
- Keep idempotent responses small. The whole response body is stored, and the package has no size limit yet.

#### The store contract

The tutorial wrote the store with Drizzle, with TypeORM, and for Redis. This section sums up what any `IdempotencyStore` must do, for writing one with another ORM. The package README's "Implementing a store" has every method in detail.

**Registration.** The store is an ordinary singleton provider that calls `registerSource(this)` on the injectable `IdempotencyStorage` in its constructor. The registry checks the shape at once, refuses a second registration unless it passes `replace: true`, and locks when `IdempotencyModule` initializes, logging the store in use. With nothing registered, the module uses `InMemoryIdempotencyStore`, which one instance can't share with another, and which loses its records on restart. With `NODE_ENV=production`, startup fails instead, unless you set `allowInMemoryStorage: true`, which accepts losing the records on every restart or deploy.

**The methods.** All four are atomic: each one decides who holds a key, and a read followed by a separate write lets two requests both run the handler, which is the double charge the package exists to prevent. None takes your transaction: an idempotency record is written on its own, never as part of your business transaction.

| Method | What it does | How it stays atomic |
| --- | --- | --- |
| `acquire(key, owner, fingerprint, lockTtl)` | Takes the lock on a free or expired key, or returns the record it found | One insert that takes over an expired row in the same statement, so of many concurrent callers exactly one wins; the others read the winner's record |
| `complete(key, owner, response, ttl)` | Turns the owner's live lock into a completed record | A compare-and-set: the owner and expiry checks are in the `WHERE` of the statement that writes |
| `release(key, owner)` | Deletes the owner's live lock, so a retry can run the handler | A compare-and-set, as `complete()` |
| `extend(key, owner, lockTtl)` | Renews the owner's live lock | A compare-and-set, as `complete()` |

**With Prisma.** The Drizzle and TypeORM stores are the model, with the same table:

- **`acquire()`** is one `INSERT ... ON CONFLICT (key_hash) DO UPDATE ... WHERE expires_at <= now RETURNING`. Prisma's `upsert()` has no condition on the update, so use `$queryRaw`. When no row comes back, read the record, as the other stores do.
- **`complete()`, `release()` and `extend()`** put the owner and the expiry in the `WHERE` and count the rows: `updateMany()` or `deleteMany()` with `keyHash`, `owner` and a `gt: now` filter on `expiresAt` in `where`, and `count === 1`. Not `update()` after a `findUnique()`: it reads first.
- **The response column** is `json` rather than `jsonb`, in any ORM: `jsonb` rejects a `\u0000` inside a string, and a response body can contain one.

**Test it** with the suite from `@nestjs/idempotency/testing`, as the Drizzle, TypeORM and Redis stores do. `idempotencyStoreContract()` returns cases for any test runner. `concurrent: true` races 16 callers for each key; run it against PostgreSQL with a connection pool, where the calls really overlap. `advanceTime` moves the store's clock for the expiry cases, and without it they wait in real time.
