#### Reference

##### Module options

`LocksModule.forRoot()` takes these options; `forRootAsync()` takes them from `useFactory`, `useClass` or `useExisting` (a class implementing `LocksOptionsFactory`). The store isn't an option: register it with `LocksStorage`, as in [Keep locks in your database](/reliability/locks#keep-locks-in-your-database).

| Option | Default | Meaning |
| --- | --- | --- |
| `ttl` | `'30s'` | How long a lock lives without a renewal, so how soon another instance takes over after a crash. The default for every lock, lease and election. A duration: milliseconds, or a string such as `'15s'` or `'2m'` |
| `storeTimeout` | `'10s'` | How long to wait for each store call (`acquire()`, `renew()`, `release()`). Past it, the call fails with `LockStoreTimeoutError`: `acquire()` rejects, a tick doesn't run, a renewal is tried again at the next beat, and a lock the store grants after that goes back to it |
| `clock` | The system clock | A `LockClock`. Tests pass a `ManualLockClock` ([Testing](/reliability/locks#testing)) |
| `allowInMemoryStorage` | `false` | With `NODE_ENV=production` and no registered store, startup fails; `true` runs on the in-memory store anyway (one instance) |
| `isGlobal` | `true` | Registers the module globally. Top level of `forRoot()` and `forRootAsync()` |

##### Decorators and methods

| API | Options | Notes |
| --- | --- | --- |
| `@OnOneInstance()` | `key`, `ttl` | Runs the job on the instance holding the `<key>:owner` lease; other instances skip the tick. [Run each job on one instance](/reliability/locks#run-each-job-on-one-instance) |
| `@WithoutOverlapping()` | `key`, `ttl` | Skips a tick while a run holds the `<key>` lock, on any instance. [Don't let a long run overlap itself](/reliability/locks#dont-let-a-long-run-overlap-itself) |
| `@LeaderElection(key)` | `ttl` | On a singleton provider implementing `OnLeadershipAcquired`, `OnLeadershipLost` or both. [Hold the warehouse feed on one instance](/reliability/locks#hold-the-warehouse-feed-on-one-instance) |
| `Locks.acquire(key, options)` | `ttl`, `wait`, `signal` | Resolves a `Lock`, or `null` when the key stayed taken. [Run the export by hand](/reliability/locks#run-the-export-by-hand) |
| `Locks.withLock(key, fn, options)` | `ttl`, `wait`, `signal` | Runs `fn(lock)` under the lock and releases it; rejects with `LockNotAcquiredError` when the key stayed taken |

- `key` defaults to `ClassName.methodName`, and the two job decorators on one method share it. `ttl` defaults to the module's.
- `wait` defaults to `0` (try once); a longer wait retries with backoff. `signal` stops the waiting, also for a store call in flight. Neither `wait` nor `ttl` bounds a store call: the module's `storeTimeout` does.
- A `Lock` has `key`, `owner`, `fencingToken`, `signal`, `held`, `release()` and `[Symbol.asyncDispose]`, so `await using` releases it.
- `LocksContext` has `lock`, `fencingToken` and `signal` inside a job, a `withLock()` callback, or `run(lock, fn)`; outside one, they are `undefined`. [Fence the writes](/reliability/locks#fence-the-writes)

##### Events

`LocksEvents.events$` emits each event, and publishes it on its `node:diagnostics_channel` channel. Every payload has `type`, `key` and `fencingToken`.

| Event | Channel | Other fields | When |
| --- | --- | --- | --- |
| `lock-lost` | `nestjs:locks:lock-lost` | `detectedBy`: `'renewal'` or `'deadline'` | A holder lost a lock it was using. Alert on it |
| `leadership-acquired` | `nestjs:locks:leadership-acquired` | None | This instance became the leader of `key` |
| `leadership-lost` | `nestjs:locks:leadership-lost` | `reason`: `'lost'` or `'released'` | This instance stopped leading: the lease was lost, or it stepped down |

`LocksEvents.jobSkips$` emits a `job-skipped` event for each call to an `@OnOneInstance()` or `@WithoutOverlapping()` job that resolved without running before `onApplicationShutdown()`, and publishes it on `nestjs:locks:job-skipped`. It is apart from `events$`: every instance but the owner skips each tick, so these events are for counting, not alerting. The payload has `type`, `job` (`ClassName.methodName`), `key` (the job's key, not its `<key>:owner` lease) and `reason`:

| `reason` | When |
| --- | --- |
| `ownership-unavailable` | The `<key>:owner` lease wasn't granted: another instance holds it, or the store granted it too late to use |
| `run-lock-unavailable` | The `<key>` run lock wasn't granted: a run is in progress, or the store granted it too late to use |
| `shutdown` | The application is shutting down |

[[CODE:55]]

The events are what this instance saw, as it saw it: they don't record a job's last run, and they don't count ticks the scheduler never fired. A store error isn't a skip: the call rejects, as before.

> warning **Warning** A subscriber to `events$`, `jobSkips$` or a `nestjs:locks:*` channel must not throw: rxjs and Node rethrow its error as an `uncaughtException`. A skip subscriber runs on every tick, so a bug in one shows within a tick.

##### Errors

None of them carries an HTTP status: contention isn't the caller's mistake, so the handler picks the response ([Run the export by hand](/reliability/locks#run-the-export-by-hand) answers `409`).

| Error | Properties | Raised when |
| --- | --- | --- |
| `LocksError` | None | The base class of the three below |
| `LockNotAcquiredError` | `key`, `waitMs` | `withLock()` couldn't take the lock within `wait` |
| `LockLostError` | `key`, `fencingToken`, `detectedBy` | The reason a lost lock's `signal` aborts with: the store refused a renewal (`'renewal'`), or `ttl` passed without a confirmed one (`'deadline'`) |
| `LockStoreTimeoutError` | `key`, `method`, `timeoutMs` | A store call (`method`: `'acquire'`, `'renew'` or `'release'`) didn't answer within `storeTimeout` |
