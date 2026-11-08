### Distributed locks

`@nestjs/locks` runs a scheduled job, or any other code, on one instance at a time, with leases that every instance of the application checks in a shared store.

An online store for cat food and supplies runs two scheduled jobs with `@nestjs/schedule`. Every night at 02:00 an export sends the day's invoices to the accounting system, and every five minutes a reconciliation asks the warehouse for a full stock count and writes it to the products table. Both work on one instance. In production the order API runs on three, and `@nestjs/schedule` fires every `@Cron()` on each of them:

- The accounting system records every invoice three times.
- The warehouse is asked for three full counts every five minutes. A full count pages through the whole catalog, and at month end it takes longer than five minutes, so the next tick starts a second count alongside the first, then a third.

The usual fixes have holes. A `RUN_JOBS=true` instance works until a rolling deploy has two of them for a minute, or the job instance is the one that dies. A `SET NX` key in Redis at the top of the job works until its holder pauses for longer than the key's TTL, in a stop-the-world garbage collection or behind a network partition: another instance takes the key, and when the first one wakes up it finishes its run believing it still holds it. Two writers again, and neither knows. `waitForCompletion: true` on `@Cron()` stops a job from overlapping itself, on one instance.

`@nestjs/locks` turns a job into something one instance holds: a **lease** that the holder keeps renewing while it is up, checked in a store every instance shares. Two decorators put it on a scheduled job, `@OnOneInstance()` and `@WithoutOverlapping()`, in the spirit of Laravel's `onOneServer()` and `withoutOverlapping()`. Under them is a distributed lock you can also take yourself, with the two things a lock needs to be trusted: an `AbortSignal` that aborts when the lease is lost, and a **fencing token** that grows with every acquisition of a key, so a write from a holder that paused past its lease can be refused. A leader election is the same lease, held for as long as the leader lives.

In this tutorial, you'll add it to the store, on PostgreSQL with Drizzle:

- Prove the duplicate runs with a test, on three instances of the app.
- Keep the locks in a table of the application's database.
- Run each job on one instance, with a handover when that instance dies.
- Keep a long stock count from overlapping itself.
- Fence the stock writes, so a paused instance can't overwrite a fresher count.
- Run the export by hand from an admin endpoint, never alongside the scheduled run.
- Keep the locks in Redis instead.
- Hold the warehouse's alert feed on one instance, with a leader election.

#### Installation

To get started, install the required dependency:

[[CODE:1]]

#### See the problem

This is the application before the tutorial. The nightly export takes every placed order that has no invoice yet, uploads the batch, and marks the orders with the batch id:

[[CODE:2]]

The accounting system records every batch it receives, so a batch uploaded twice is recorded twice. The reconciliation asks the warehouse for the counts and writes them:

[[CODE:3]]

The cron expressions come from the environment, with the real schedule as the default, so the tests and the [Try it](/reliability/locks#try-it) section can speed them up or turn them off. `AccountingClient` and `WarehouseClient` stand in for the two external systems; each counts what it was asked to do. The database is the application's, registered with `DrizzleModule` in `app.module.ts` and injected with `@InjectDrizzle()`.

> info **Hint** The tutorial reads `process.env` directly, to stay short. In an application, load the environment through [`@nestjs/config`](/application/configuration) with a validation schema, so a missing variable stops the application at startup rather than at the first request, and read the values from `ConfigService`.

Before changing anything, prove the problem. The test starts three instances of the application in one process, on one database (PostgreSQL in-process with [PGlite](https://pglite.dev), or a PostgreSQL server when one is configured), and fires the schedules on each of them through `@nestjs/schedule`'s own registry, the way 02:00 would:

[[CODE:4]]

Three batches, each with the same three orders, and three full counts. The `orders` table looks fine afterwards, every order has a batch id, which is why this goes unnoticed until accounting calls.

#### Keep locks in your database

`@nestjs/locks` works as soon as you import `LocksModule`, on an in-memory store. That store excludes callers in one process only: three instances would each have their own, all three would take "the" lock, and nothing would change. The locks need a store every instance shares, and the package doesn't ship one. It defines the contract, the `LockStore` interface, and you implement it in a provider of your application with the database it already has.

This section shows that store twice: first with Drizzle on PostgreSQL, registered through [`@nestjs/drizzle`](/data/drizzle) with the `pg` driver, which is the tutorial's path, and then, under "With TypeORM" at the end of the section, the same store for an application whose ORM is TypeORM. Take one of the two, or keep the locks in Redis with [the store on Redis](/reliability/locks#the-store-on-redis). With Drizzle, a lock is one row per key:

[[CODE:5]]

drizzle-kit writes the migration:

[[CODE:6]]

[[CODE:7]]

The contract has three methods, and each takes the lock key and an `owner` first: a random id the package draws for each acquisition. Durations arrive in whole milliseconds.

- `acquire(key, owner, ttl)` takes the key if no live lock holds it, and returns the lock's fencing token, or reports that the key is taken. It must be atomic: of any number of concurrent callers, exactly one may win.
- `renew(key, owner, ttl)` is the heartbeat. It moves the expiry to `ttl` from now, if `owner` still holds a live lock on the key. The package calls it every `ttl / 3` while a lock is held.
- `release(key, owner)` gives the lock back, if `owner` still holds it.

"If `owner` still holds it" has to be checked in the same statement that writes: checked in a separate read first, a takeover could slip in between. And the store measures `ttl` with its own clock, so every instance agrees on when a lock expires whatever their clocks say. With Drizzle, that is one conditional insert and two conditional updates:

[[CODE:8]]

A few things about this store:

- **`acquire()` is one statement.** The insert wins a key that has no row; the `ON CONFLICT DO UPDATE` with its `WHERE` takes over a released or expired one, and PostgreSQL re-checks that `WHERE` against the row after it locked it. Of many callers racing for the same key, one gets a row back and the rest get nothing. A `SELECT` followed by an `INSERT` would let several of them in.
- **The fencing token comes from a sequence**, drawn inside the statement, after the row lock. A sequence never goes back, so every acquisition of a key gets a greater token than the one before, across releases and expiries. It has gaps, because a caller that lost the race still consumed a value; that doesn't matter. The `greatest()` makes the row's own token the floor of the next one: if the sequence ever does go back (a restore from a backup, a failover to a replica that lagged), a key still can't get a token it had before. [Fence the writes](/reliability/locks#fence-the-writes) shows what the token is for.
- **`release()` keeps the row** and clears the owner, so the next acquisition always takes the update path. With a delete, an insert that drew its token early could win the key after a later holder had already released it, and hand out a smaller token.
- **`clock_timestamp()`**, not `now()`: `now()` is the transaction's start time, which is what a lock's expiry must not depend on.
- Why a table and not `pg_advisory_lock()`: an advisory lock is bound to a session, so the holder would have to keep one connection checked out of the pool for the whole critical section, would lose the lock without knowing when that connection drops, can't renew it, and gets no expiry for a paused holder and no fencing token. A row has all of that, through any pool.

The package ships the contract as a test suite, so you can prove the store before you rely on it. `lockStoreContract()` returns cases for any test runner, and `concurrent: true` adds the races:

[[CODE:9]]

The example runs the same suite against a PostgreSQL server with a pool of 20 connections and 32 racing callers, where the statements really overlap. Run it that way in CI, on the PostgreSQL version you run in production.

Now register the module and the store, next to the application's `DrizzleModule`. The store is a plain provider; its constructor registers it, so there is nothing to configure:

[[CODE:10]]

`LocksModule.forRoot()` takes a `ttl` (the default is `'30s'`: how long a lock lives without a renewal, so how soon another instance takes over after a crash), a `storeTimeout` (the default is `'10s'`: how long to wait for each store call before it fails, so a store that stops answering can't hang a job, a request or the shutdown), a `clock` for tests, and `allowInMemoryStorage`. `forRootAsync()` takes the same options from a factory. The module is global, so `Locks`, `LocksContext` and `LocksStorage` are available everywhere. When it initializes, it logs the store in use:

[[CODE:11]]

With nothing registered, the line names `InMemoryLockStore` and what that means. With `NODE_ENV=production` and nothing registered, the application doesn't start, because in memory every instance would take the same lock and run the same job:

[[CODE:12]]

**With TypeORM.** The same store for an application whose ORM is TypeORM, on the same table and sequence. Drizzle stays the tutorial's path: take this store instead of the one above, not next to it. The table is an entity, and every column states its type, so that the TypeORM CLI, which loads it without decorator metadata, sees the same schema as the application:

[[CODE:13]]

The TypeORM CLI and `TypeOrmModule` share one set of options, in a data source file:

[[CODE:14]]

Generate the migration from the entity, against a database with your previous migrations applied. The CLI needs a TypeScript loader for the data source file; this uses `tsx`:

[[CODE:15]]

TypeORM has no entity for a sequence, so the migration it writes creates the table alone. Add the sequence to it yourself, before the table, and drop it in `down()`:

[[CODE:16]]

`migrations` in the data source lists it. Apply it, and check that the entity and the database agree. The check doesn't compare sequences, so the one you added doesn't count as a change:

[[CODE:17]]

Now the store, under the same rules as the Drizzle one:

[[CODE:18]]

- **`acquire()` is the one statement written as SQL**, through `dataSource.query()`. The insert query builder's `orUpdate()` writes an `ON CONFLICT DO UPDATE`, with the `WHERE` in its `overwriteCondition` option, but it sets every column from `EXCLUDED`: the token would be the one the insert drew before the row was locked, which a later holder of the key may already have passed. The SQL draws it in the `SET`, after the row lock, as the Drizzle store does.
- **`renew()` and `release()`** are the update query builder with the owner and the expiry in the `WHERE`, and read `affected`. Never `save()`, and no `findOneBy()` first: a read before the write lets a takeover slip in between.
- **The token is converted with `Number()`.** `pg` returns a `bigint` column as a string, and the package refuses a string token.
- **Use it** in place of the Drizzle store: `TypeOrmModule.forRoot(dataSourceOptions)` in `AppModule`, and `TypeOrmLockStore` in its providers instead of `DrizzleLockStore`. It injects the `DataSource` that `TypeOrmModule` provides, and the startup line names `TypeOrmLockStore`.

The contract suite runs on it unchanged, with the concurrency cases. TypeORM connects through `pg`, so the suite needs a PostgreSQL server and is skipped without one. Three more cases check that a key's tokens keep growing after the sequence went back, that the entity and the migration agree (what `migration:generate --check` checks), and that the store registers itself when provided in a module:

[[CODE:19]]

> info **Hint** Using Prisma? [The store contract](/reliability/locks#the-store-contract), after the tutorial, lists what the store must guarantee and how Prisma expresses the atomic methods. Test your store against the same cases.

#### Run each job on one instance

Add `@OnOneInstance()` to both jobs, next to `@Cron()`:

[[CODE:20]]

[[CODE:21]]

[[CODE:22]]

That is the whole change. What it does:

- **The first instance whose scheduler fires the job takes the job's lease**, a lock named after the key with an `:owner` suffix, and keeps renewing it every `ttl / 3` for as long as it is up. It runs this tick and every tick after it.
- **On the other instances, the tick is skipped**: the call resolves without running the method, a debug line says why, and `LocksEvents.jobSkips$` reports it ([Events](/reliability/locks#events)). Nothing is queued; the job's schedule is the schedule.
- **When the owner dies**, it stops renewing, the lease expires `ttl` (30 seconds) later, and the first instance whose tick comes after that takes the job over. When the owner shuts down cleanly, it finishes the runs in progress, hands the lease back, and the next tick anywhere takes it.
- **The decorators wrap the method.** `@nestjs/schedule` isn't patched, and it doesn't know they are there: its explorer finds the `@Cron()` metadata on the wrapper, in either decorator order, and calls the wrapper, which asks `LocksModule` whether this call may run. `@Interval()` and `@Timeout()` jobs work the same way, and so does calling the method yourself.
- **The key** defaults to `ClassName.methodName`. Set it on a job that must never run twice: a renamed class or method changes the default, and during a rolling deploy the old and the new instances would each run the job once. Two jobs with the same default key fail at startup, and so does a job whose key is another job's lease (`<key>:owner`) or an election's key: they would exclude each other silently.

Ownership is sticky on purpose. A race per tick would be simpler, but a tick isn't an instant: the instances' clocks differ by tens of milliseconds, so a per-tick lock would have to outlive the run by the skew, and a fast job would need a "ran at" record to stop a lagging instance from running the tick again. A lease held between ticks has none of that, at the cost of one instance running all of a job's ticks, which a scheduled job rarely minds.

What about a tick that nobody runs? While the owner is down, up to `ttl` of ticks are skipped, and the nightly export can fall on those thirty seconds. **Missed ticks aren't caught up**: nothing records when a job last ran. Write jobs that do everything that is due rather than "yesterday's". The export takes every order without an invoice, so a night it didn't run is caught up the next night; the reconciliation writes the current counts, so a missed tick costs five minutes of staleness. A job whose ticks each do something distinct keeps that record in its own table.

The test from [See the problem](/reliability/locks#see-the-problem), with the new jobs and the store, now records every invoice once, and the test that stops an instance from renewing (its clock stands still, as if the process had died) shows the handover:

[[CODE:23]]

[[CODE:24]]

`ManualLockClock` is the package's clock for tests: it only moves when told to. An instance on it never renews, so the database, on its own clock, expires the instance's locks after `ttl`.

#### Don't let a long run overlap itself

`@OnOneInstance()` puts the reconciliation on one instance. It doesn't stop that instance from starting the next count while the last one is still running, and neither does a plain `@Cron()`. At month end the count takes longer than five minutes, so the warehouse gets a second full count, then a third. Add `@WithoutOverlapping()`:

[[CODE:25]]

A run now takes a second lock, named after the same key (the two decorators on one method share it), holds it for the whole run, renewing it, and releases it when the run ends. A tick that finds the lock held is skipped, on this instance or any other: the ticks during a long count are dropped, and the first tick after it runs. If the run crashes, the lock expires after `ttl` and the next tick runs. `@WithoutOverlapping()` on its own, without `@OnOneInstance()`, means "any instance, one run at a time".

The test drives two instances on one `ManualLockClock`, holds a count open, and advances the clock through three ticks:

[[CODE:26]]

`clock.advance('5m')` fires every renewal that falls due on the way, in order, and waits for each to reach the store, so fifteen minutes of a long run take a moment, with the run's locks renewed the whole time.

#### Fence the writes

A lease can't stop a holder that is paused. Take the reconciliation on instance A: it reads the counts from the warehouse (salmon kibble: 12), and then A stalls, in a stop-the-world garbage collection, a swap, a VM migration, a debugger. It stops renewing. Thirty seconds later the database expires its locks, and B takes the job over at its next tick: it reads fresher counts (three bags were sold and shipped since: salmon kibble: 9) and writes them. Then A wakes up and finishes its run, with the counts it read before the pause. Salmon kibble is back at 12, and the store sells three bags it doesn't have.

A's signal aborts at its next renewal, when the database refuses it, but a write that is already on its way goes through. Note what the lease does and doesn't promise. A holder counts its own deadline, `ttl` from the moment it sent the last renewal the store confirmed, which is before the store processed it: a holder that is running gives up no later than the store's expiry, so its signal aborts before any other instance can take the key. The window exists only for a holder that isn't running (paused, stopped, its event loop blocked): from the store's expiry until it runs again, it still believes it holds the lock. What stops its write is the **fencing token**: every acquisition of a key gets a token greater than every token the key had before, and the resource being written keeps the highest token it has seen and refuses a lower one. A's token is lower than B's, so A's late write updates nothing.

The products table gets a column for it:

[[CODE:27]]

[[CODE:28]]

[[CODE:29]]

The repository writes a count only if no run with a greater token has written that product, and records the token it wrote with, in the same statement:

[[CODE:30]]

The job gets its token, and its signal, from `LocksContext`. `@nestjs/schedule` calls the method without arguments, so the context carries them, through `AsyncLocalStorage`, to every service the job calls:

[[CODE:31]]

The token is the run lock's, a new and higher one for every run. The signal aborts when the run's lock or the instance's lease is lost, and its reason is a `LockLostError` that says how the loss was detected: the store refused a renewal, or `ttl` passed without one reaching the store. Pass the signal to what the job calls, `fetch`, the database driver, an HTTP client; a job that ignores it keeps running, as it would in any process. Nothing is killed.

The test reproduces the pause against PostgreSQL. Instance A runs on a `ManualLockClock`, so it stops renewing; the warehouse client holds A's count open after A read it; the shelves change; B takes over 1.2 seconds later (the test's `ttl` is one second) and writes salmon kibble: 9. Then A's count resumes:

[[CODE:32]]

With the previous section's job, the stale write goes through and salmon kibble is back at 12. With the token, the database refuses it, and the job logs that it skipped three stale writes. And a run that gets to its next renewal before writing stops at the signal, with a `LockLostError`, and writes nothing. The package logs a warning for every lost lock and emits a `lock-lost` event, because a lost lock means another instance may be in the same critical section right now: only the token keeps the two apart.
