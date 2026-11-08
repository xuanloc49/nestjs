#### Run the export by hand

Accounting sometimes asks for the export before 02:00. An admin endpoint runs it, and it must never run alongside the scheduled run, on any instance. The scheduled run holds the lock named by its key; the endpoint takes the same lock with `Locks.withLock()`, waiting up to two seconds for a run that is about to finish:

[[CODE:33]]

The job exports the key as a constant, gets `@WithoutOverlapping()` too, and splits the work out of the scheduled method so the endpoint can call it and return its result:

[[CODE:34]]

[[CODE:35]]

`withLock(key, fn, options)` runs `fn` under the lock and releases it whether `fn` resolves or throws. `wait` is how long to keep trying, with backoff, before it gives up with a `LockNotAcquiredError`; the default is to try once. `acquire(key, options)` is the same without the callback: it resolves a `Lock`, or `null` when the key was taken, and you release it yourself, or with `await using`. A `Lock` has the `fencingToken` and the `signal`, and inside `withLock()` so does `LocksContext`, exactly as in a job.

Both also take a `signal` of their own, the request's for example, which stops the waiting. It stops the wait for the store too: a call still waiting for the store's answer rejects with the signal's reason, `fn` doesn't run, and a lock the store grants after that goes back to it. `wait` doesn't cut short a store call already on its way; the module's `storeTimeout` does, so a call takes at most `wait` plus `storeTimeout`. A store that doesn't answer within `storeTimeout` fails the call with a `LockStoreTimeoutError`.

Neither `LockNotAcquiredError` nor `LockStoreTimeoutError` carries an HTTP status: contention and a stalled store aren't the caller's mistake, so the handler decides. Here a taken lock is a `409`, and anything else is rethrown. While the export runs by hand, the scheduled tick on any instance finds the lock held and skips.

> info **Hint** `AdminGuard` is a placeholder. Protect the route with your application's real [authorization](/security/authorization).

#### The store on Redis

The store is a contract, so it can live wherever your instances already meet. If that is Redis, each method is one Lua script, which Redis runs atomically:

[[CODE:36]]

`SET NX PX` takes the key only if it is free, expiring on Redis's clock in milliseconds, and the `INCR` in the same script draws the token from one counter for every key. Fencing is only as durable as that counter. It never expires, and it must never go back: give Redis persistence (AOF, or RDB with a short interval) and `maxmemory-policy noeviction`, because a counter that restarts at 1 (a restart without persistence, a `FLUSHALL`) hands out tokens that holders already have, and a lock evicted under memory pressure is a lock lost. A failover to an asynchronous replica can lose the last writes too: a lock taken just before it, which is the paused-holder case the token covers, but also the counter's last increments, after which the next holder may draw a token the previous one already has, and the token no longer tells them apart. Where fencing must hold across a failover, keep the locks in the database, whose sequence is in the same WAL as the rows, or replicate Redis synchronously.

On Redis Cluster, `ACQUIRE` fails with a `CROSSSLOT` error as written: a cluster runs a script only when all its keys hash to the same slot, and the lock's key and the counter don't. Name both under one hash tag, `{{ '{' }}locks{{ '}' }}:key:<key>` and `{{ '{' }}locks{{ '}' }}:fencing-token`: the cluster then hashes only `locks`, so the counter and every lock share one slot, on one shard. A counter under a new name, or on a new cluster, starts again at 1, which is the restart it must never make. Before the first acquire on it, stop the instances that use the old keys and set the new counter to the old one's value (`SET {{ '{' }}locks{{ '}' }}:fencing-token <value>`), so the next token is higher than any already handed out.

The `redis.module` provides the client under the `REDIS` token; the example uses a minimal client with ioredis's `eval()` signature, to stay free of dependencies, and in your application it is `new Redis(process.env.REDIS_URL)`:

[[CODE:37]]

Swap the provider in the application module, and nothing else changes:

[[CODE:38]]

The example runs the contract suite against a real `redis-server`, on eight connections so the calls overlap, and then three instances of the application on it:

[[CODE:39]]

Close the Redis client in `onApplicationShutdown()`, as the module does; `@nestjs/drizzle` closes the database pool in the same phase. Nest runs each shutdown phase for the whole application before the next: the package hands the leases back in `onModuleDestroy()` and releases every other lock still held in `beforeApplicationShutdown()`, so by the time any module's `onApplicationShutdown()` runs, nothing of the package's needs the connection, whatever the import order. A tick or an election still waiting for the store when the shutdown begins stops waiting: the tick is skipped, and a lock the store grants after that goes back to it, so a stalled store doesn't hold up the deploy.

#### Hold the warehouse feed on one instance

The warehouse pushes low-stock alerts over a feed that allows one connection per shop. That isn't a scheduled job; it's a connection one instance should hold for as long as it lives, and another should take over when it goes down. That is a leader election, and it is the same lease as a job's ownership, held on purpose:

[[CODE:40]]

[[CODE:41]]

`@LeaderElection(key)` goes on a singleton provider. From `onApplicationBootstrap`, every instance tries to take the lease on the key, and keeps trying every `ttl / 3`; the one that has it renews it. `onLeadershipAcquired(lock)` runs when this instance becomes the leader, with the lease's `signal` and `fencingToken`; `onLeadershipLost(lock)` when it stops leading, because the lease was lost or because it stepped down, at shutdown or after `onLeadershipAcquired()` threw. The `ttl` option sets the lease's; the default is the module's 30 seconds, so a crashed leader is replaced within half a minute, and a leader that shuts down cleanly is replaced at the others' next try.

The test starts three instances and shows one connection, a handover at shutdown, and the paused leader's blind spot:

[[CODE:42]]

A leader that pauses is still connected until its next renewal fails, and receives what the feed sends in between. That is the same blind spot as in [Fence the writes](/reliability/locks#fence-the-writes), with the same answer: what the leader does on the group's behalf carries the lease's token.

#### Try it

Create the database and apply the migrations:

[[CODE:43]]

Start three instances on ports 3001, 3002 and 3003, with `ADMIN_TOKEN=s3cret` and a stock reconciliation every ten seconds instead of five minutes, so there is something to watch: `STOCK_RECONCILIATION_CRON='*/10 * * * * *'`. Each logs the lock store it registered. The first one up leads the warehouse feed, and takes the reconciliation at the first tick, before the other two are up:

[[CODE:44]]

The other two skip every tick, at debug level:

[[CODE:45]]

The locks table shows the lease, the run lock (released, so its owner is null, and its token grows with every run) and the feed's lease. Every lock expires thirty seconds after its last renewal, on the database's clock:

[[CODE:46]]

The fencing tokens have gaps: a refused acquisition still consumed a value from the sequence. Run the export by hand. Without the admin token the guard answers `403`; then send two requests at once, to two different instances:

[[CODE:47]]

One request took the lock and exported the three pending orders. The other waited for it, took the lock when it was released, and found nothing left. A request that waits more than two seconds gets a `409`. The instance that ran the export logs the batch:

[[CODE:48]]

Now kill the first instance, which runs the reconciliation and leads the feed, without giving it a chance to clean up:

[[CODE:49]]

Nothing happens for a while: the other two keep skipping, because the leases are still in the table. Thirty seconds after its last renewal each one expires. The feed's lease goes first, since it was renewed on its own schedule, and the next tick takes the job over:

[[CODE:50]]

Stop the new owner with `Ctrl+C` instead. Its shutdown hooks hand both leases back (`main.ts` calls `app.enableShutdownHooks()`):

[[CODE:51]]

The last instance takes the job at its next tick, and the feed at its next campaign, seconds later rather than thirty:

[[CODE:52]]

Finally stop the last one with `Ctrl+C`. It steps down from the feed before it goes:

[[CODE:53]]

#### Testing

An application that imports `LocksModule` and registers no store runs on the in-memory store, so an end-to-end test of one instance needs nothing: every tick runs, once. To keep the Drizzle store out of a test, override its provider with a plain `InMemoryLockStore`; a plain instance doesn't register itself, so the in-memory default applies.

To test what the package is for, run several instances in one process. An instance is a Nest application; instances of one application share a store. The example's helper starts one on the shared database, with the fakes and the test's `LocksModule` options:

[[CODE:54]]

- **Share the database.** On PGlite, every instance gets the same Drizzle database by overriding the one `DrizzleModule` registers (`getDrizzleToken()`), with the real migrations applied; `DrizzleLockStore` injects it with `@InjectDrizzle()`, so the instances share the locks table as they share it in production. Against a PostgreSQL server, each instance opens its own pool from the database's URL. Without a database, share one `InMemoryLockStore` between the instances by registering it in each with `LocksStorage.registerSource()` and its `replace` option before `init()`.
- **Fire the jobs yourself.** Call the method (`await job.exportInvoices()`) on each instance, or go through `@nestjs/schedule` with `schedulerRegistry.getCronJob(name).fireOnTick()`. Both reach the wrapper. Point the real schedules at a date that never comes: the example's `vitest.config.mts` sets the two cron variables to February 29th at 3 AM.
- **Control time.** Override `LOCKS_MODULE_OPTIONS` with a `ManualLockClock`, and every renewal, deadline and `wait` in that instance moves only when the test advances the clock: `await clock.advance('5m')` fires what falls due on the way, in order, and waits for each renewal to reach the store. An instance whose clock you don't advance is a paused process. Against PGlite or a server, the store's clock is real time, so a short `ttl` (`'1s'`) and a `sleep` expire a paused instance's locks; with the in-memory store, give it the same `ManualLockClock` and expiries move with it.
- **Assert on the log** or on `LocksEvents`: which instance runs a job, every skipped tick (`jobSkips$`), every lost lock and every leadership change (`events$`). The events are also published on the `nestjs:locks:job-skipped`, `nestjs:locks:lock-lost`, `nestjs:locks:leadership-acquired` and `nestjs:locks:leadership-lost` diagnostics channels.
- **Test your store** with the contract suite, as the Drizzle, TypeORM and Redis stores do, against the server you run in production.

See [End-to-end testing](/fundamentals/testing#end-to-end-testing) for more about the testing setup.

#### Production checklist

- Register a shared store, on your database or Redis, and run the contract suite against it with `concurrent` on, in CI, on the version you run in production. In production the application refuses to start without one, unless `allowInMemoryStorage` is set, which is only right for a single instance.
- Set `key` on every job that must never run twice, so a rename or a minifier can't change it during a rolling deploy.
- Pick a `ttl` well above the store's round trip and the longest event-loop stall you accept, and short enough that a crash doesn't skip too many ticks. Renewals go out every `ttl / 3`; 30 seconds fits most jobs. A long job's run lock is renewed at the same pace, so its `ttl` doesn't need to cover the run.
- Leave `storeTimeout` well above the store's slowest healthy answer: a store call that runs past it fails, so the tick doesn't run and `acquire()` rejects with `LockStoreTimeoutError`. The default, 10 seconds, also bounds how long a stalled store (an exhausted pool, a failover, a Redis client queueing commands while offline) holds up a job, a request or a renewal.
- Write jobs that do what is due, not what the tick was for. Missed ticks aren't caught up: a crashed owner costs up to `ttl` of ticks, and ticks during a long run are skipped.
- Pass `LocksContext.signal` to what a job calls, and fence the writes that can't be undone with `LocksContext.fencingToken`, in the same statement that writes. Alert on `lock-lost` from `LocksEvents` or the diagnostics channel: it means renewals failed for longer than `ttl`, because the store was unreachable or the event loop was blocked, and another instance may be running the same critical section.
- Call `app.enableShutdownHooks()`, so a deploy hands the leases over at once instead of leaving them to expire. Close the Redis client in `onApplicationShutdown()`, the phase in which `@nestjs/drizzle` closes the database pool: the package hands the leases back in `onModuleDestroy()` and releases every other lock in `beforeApplicationShutdown()`, phases Nest completes for the whole application first. A lease whose job started less than a second before the shutdown is kept for the rest of that second rather than handed back, so that instances firing the same tick skip it instead of running it a second time.
- With the Redis store, give Redis persistence and `maxmemory-policy noeviction`. The fencing counter must never go back, and a lock must never be evicted.
- With the database store, create the table and the sequence through your migrations, and size the connection pool for one short statement per renewal per held lock, plus one per tick per instance.
- Keep the instances' clocks synchronized with NTP anyway. Expiry is measured on the store's clock, but a holder counts its own deadline, and `@nestjs/schedule` fires on the instance's clock.
- Log level: the skipped ticks are logged at `debug`. Keep that level on for a while after the rollout, to see the jobs settle on one instance. To watch them for good, count `LocksEvents.jobSkips$` by `job` and `reason` instead of parsing the log.

#### The store contract

The tutorial wrote the store with Drizzle, with TypeORM and with Redis. This section sums up what any `LockStore` must do, for writing one with another database or ORM. The [`LockStore` interface](https://github.com/nestjs/locks/blob/master/lib/interfaces/lock-store.interface.ts) documents the full contract and the races each rule prevents.

**Registration.** The store is an ordinary singleton provider that calls `registerSource(this)` on the injectable `LocksStorage` in its constructor. The registry checks the shape at once, refuses a second registration unless it passes `replace: true`, and locks when `LocksModule` initializes, logging the store in use. With nothing registered, the module uses `InMemoryLockStore`, which excludes callers in one process only. With `NODE_ENV=production`, startup fails instead, unless you set `allowInMemoryStorage: true`.

**The methods.** All three are atomic: each decides who holds a key, and a read followed by a separate write lets two callers into the critical section, which is the duplicate run the package exists to prevent.

| Method | What it does | How it stays atomic |
| --- | --- | --- |
| `acquire(key, owner, ttl)` | Takes the key if no live lock holds it (none, released, or expired), with a fencing token greater than every token the key had before | One insert that takes over a released or expired row in the same statement, re-checking the expiry in the write, so of many concurrent callers exactly one wins; the token is drawn after the check |
| `renew(key, owner, ttl)` | Moves the owner's live lock's expiry to `ttl` from now | A compare-and-set: the owner and the expiry are in the `WHERE` of the statement that writes |
| `release(key, owner)` | Frees the owner's live lock (deletes it, or marks it released), so the next caller takes it at once. Never resets the key's token | A compare-and-set, as `renew()` |

**What else the store must get right**, all of it checked by the suite: an expired lock doesn't exist, for every method, whether or not it has been deleted (`expires_at > now` in every condition, or let the server expire it); `ttl` is measured on the store's clock, in milliseconds, and can be weeks (past a 32-bit integer: `bigint`, `PEXPIRE`); keys are strings of up to 500 characters, any Unicode, kept apart exactly; tokens are positive safe integers returned as numbers. PostgreSQL returns a `bigint` column as a string unless the ORM converts it; the package refuses such a token at once, with a message naming the fix, rather than let fencing break silently.

**With Prisma.** The Drizzle store is the model, with the same table and sequence; [Keep locks in your database](/reliability/locks#keep-locks-in-your-database) also shows it with TypeORM. `acquire()` is one `INSERT ... ON CONFLICT (key) DO UPDATE ... WHERE owner IS NULL OR expires_at <= clock_timestamp() RETURNING fencing_token`, with the token drawn in the `SET`, after the row lock. Prisma's `upsert()` has no condition on the update, so use `$queryRaw`. `renew()` and `release()` put the owner and the expiry in the `WHERE` of `updateMany()` and check `count === 1`. Not `update()` after a `findUnique()`: it reads first.

**Test it** with the suite from `@nestjs/locks/testing`. `lockStoreContract()` returns cases for any test runner. `concurrent: true` races 16 callers for each key, and its `callers` option raises that; run it against a server with a connection pool, where the calls really overlap. `advanceTime` moves the store's clock for the expiry cases; without it they wait in real time, about twenty-five seconds in total, on locks of `ttl` (2.5 seconds by default, checked still held halfway through and free a sixth past it: raise it for a store whose round trips are slow).
