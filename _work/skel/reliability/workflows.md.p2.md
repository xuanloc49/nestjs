#### Start the workflow

##### Start it with the order

An order and its fulfilment belong together: an order that nothing fulfils is as bad as a fulfilment charging for an order that was never saved. So `OrdersService` saves the order and starts the workflow in one Drizzle transaction. `WorkflowClient` starts instances; pass it the transaction's `tx`:

[[CODE:15]]

With `transaction`, the store creates the instance through the transaction your ORM handed the callback, so it commits with the order, or rolls back with it if anything later in the callback fails. The worker only ever sees committed instances: it picks this one up at its next poll after the commit. Pass the transaction, not the database, which the store refuses: `start()` without the option writes on its own, which is the dual write the option removes. With TypeORM, pass the transaction's `EntityManager`, and with Prisma, the transaction client, as [Keep workflows in your database](/reliability/workflows#keep-workflows-in-your-database) shows.

The instance id comes from the order id, which makes `start()` idempotent. Starting the same id with the same input returns the existing instance with `created: false`, and a different input throws `WorkflowIdConflictError`. A reconciliation job can call it again for an order without charging twice.

##### Report its status

The controller places orders and reports where their fulfilment stands:

[[CODE:16]]

`getStatus()` returns the instance: its `status`, `wakeAt`, the signals it `waits` for, its `error` or `output`, and, with the `journal` option, every step. The statuses are `pending`, `running`, `suspended`, `compensating`, `completed`, `failed`, `cancelled` and `compensation_failed`; [What each status means](/reliability/workflows#what-each-status-means) says what each one means and what to do about it. The endpoint maps the instance to a small view. Don't return the raw instance to customers, because it includes the input and lease details.

The `stage` comes from the workflow. `ctx.setStatus()` sets the instance's **custom status**, a JSON value of up to 16 KiB that `getStatus()` and `list()` return as `customStatus`: here, a word for where the order stands. Set it in `run()` as the order moves on, and to `delivered` once the carrier has delivered it (in [Sleep for a week, then ask for a review](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review)):

[[CODE:17]]

The status isn't journaled. Every execution replays `run()`, and with it the `setStatus()` calls, so each execution sets the status again on its way through, and a status set in a loop doesn't grow the journal. The workflow never reads it back, so nothing it decides depends on it. It's written with the instance's next write: when the next step starts, when the instance parks, or when it ends. So the endpoint shows `paid` while `reserve-stock` waits for a retry, and `awaiting-delivery` once the instance parks for the carrier. A status the workflow no longer changes stays, such as `awaiting-delivery` on a cancelled order: `status` tells what happened. A value that isn't JSON, or takes more than 16 KiB as JSON, fails the instance with a `TypeError`, and `undefined` clears the status. Each written change is emitted as a `custom-status` event.

#### Wait for signals and timers

##### Wait for the delivery webhook

Next, the workflow waits for the carrier. The webhook and the workflow share a signal: a name and the type of its payload, defined once, so neither side can misspell the name or send the wrong shape:

[[CODE:18]]

Add this to `run()`, after `reserve-stock`:

[[CODE:19]]

`waitForSignal()` records the wait and parks the instance: its status becomes `suspended` and `wakeAt` is the deadline. No memory, timer or worker is held for those 3 days. It resolves with the signal's payload, typed as a `CarrierEvent`, or with `null` once the timeout passes. `ctx.fail()` then fails the instance, and the compensations run in reverse: the stock is released, then the charge is refunded. A `match` option filters the signals further by payload, such as `match: (event) => event.trackingNumber !== ''`; it runs again on every replay, so it must be a pure function of the payload.

The webhook marks the order as delivered and sends the signal. Both happen in a new `OrdersService.markDelivered()` method, in one transaction, so the order's status and the signal commit together. Add it, and the import of the signal:

[[CODE:20]]

The controller verifies the callback and hands it over:

[[CODE:21]]

`signal()` stores the signal with a correlation `key` and wakes the instances waiting for that signal and key. Keys match exactly, so the order id keeps one order's delivery from waking another, and a wait without a key only takes signals sent without one. Signals are durable. A webhook that arrives before the workflow reaches the wait still counts, and each signal is consumed at most once per instance, so the carrier's retries are harmless. They still store a signal each, unless you pass an `id`, such as the tracking number: a signal with the same name and `id` is stored once, and a repeat returns the first one's `signalId` with `created: false`. A delivery recorded after the deadline loses to the timeout, even if no worker was running when the deadline passed.

The controller answers `200` only after the transaction has committed. A delivery for an order the store doesn't know rolls back with a `404`, leaving no signal behind, and if the database fails, the carrier gets an error and delivers the webhook again. Signals sent in a transaction queue behind each other until it ends, so keep such transactions short. On PostgreSQL, the transaction must use the default READ COMMITTED isolation; the store refuses a stricter one, which could miss a wait registered while it ran. On MySQL, the default REPEATABLE READ works as well.

##### Wait for whichever comes first

The carrier doesn't always deliver. When it can't, it brings the parcel back to the warehouse and reports `shipment.returned`. Declare a second signal, next to the first:

[[CODE:22]]

The webhook sends it as it sends the delivery. A new `OrdersService.markReturned()` sets the order's status to `returned` and sends the signal, in one transaction, like `markDelivered()`:

[[CODE:23]]

The workflow now waits for the delivery, the return or 3 days, whichever comes first. Replace the `waitForSignal()` call with `ctx.waitForAny()`:

[[CODE:24]]

`ctx.signalWait()` and `ctx.timer()` only describe a condition, and `waitForAny()` waits for them together. It parks the instance once, with every signal it waits for and the earliest deadline, and resolves with the `key` of the condition that happened first and its `value`: a signal's payload, or `null` for a timer. Checking `key` narrows `value`, so after the two checks `delivery` is a `CarrierEvent`. A returned parcel fails the instance, and the compensations release the stock, which is back in the warehouse, and refund the charge. The status endpoint's `waitingFor` lists both signals while the instance waits.

The outcome is journaled as one entry under the wait's name, so every later execution gets the same winner. When several conditions are ready at once, the signal recorded first wins, whichever condition it matched. A signal sent after a timer's deadline doesn't count, as with `waitForSignal()`'s `timeout`, and timers count from when the wait is first reached. Only the winning signal is taken: a return reported after the delivery would stay for a later wait of the same instance. To wait for all of several signals instead, await several `waitForSignal()` calls with `Promise.all()`: each is journaled on its own, and the instance parks once for all of them. A child workflow can be a condition too, as [Start child workflows](/reliability/workflows#start-child-workflows) shows.

##### Sleep for a week, then ask for a review

Finish `run()` with the point of no return, a durable timer and the last step:

[[CODE:25]]

`ctx.sleep()` stores a wake-up time and parks the instance, like the wait. After 7 days, any worker resumes it: never early, and usually within a poll interval of the deadline. When it resumes, `run()` replays from the top: `charge-payment` and `await-delivery` return their journaled values, so `charge` and `delivery` are in scope a week later. A delayed job can't give you that continuation. To sleep until a point in time instead, pass an object with `until`, a `Date` or epoch milliseconds, computed from journaled values such as `ctx.now()`.

`ctx.commit()` marks the point of no return. Once the parcel is delivered, refunding the charge would be wrong, whatever happens next. `commit()` discards the compensations registered so far. If the review email then fails for good, the instance ends as `failed` with the step's error, and nothing is refunded or released. A cancel past this point doesn't undo anything either. Only the steps after `commit()` register compensations that can still run. The commit point is journaled under its name, so it replays like a step, and the status endpoint lists it as `delivered`.

##### Time out the whole workflow

A wait's `timeout` bounds one wait, and a step's `timeout` one attempt. To bound a whole instance, give the workflow a run timeout:

[[CODE:26]]

The deadline is the instance's start plus the timeout, stored with the instance as its `deadline`, so it holds across restarts and deploys, and a parked instance wakes for it even when its sleep or wait would end later. Once it passes, the instance stops at its next `ctx` call (a step that is running finishes first), its compensations run, and it ends as `failed` with a `WorkflowTimeoutError`. Compensations aren't bound by the deadline. Here the wait gives up after 3 days and the sleep takes 7, so 30 days is a safety net. `start()` takes a `timeout` option too, which overrides the decorator's for that instance.

#### Cancel and operate workflows

##### Let customer support cancel an order

Add a `cancel()` route to `OrdersController`, and `ConflictException` and `HttpCode` to its `@nestjs/common` import. `OrdersService.markCancelled()` sets the order's status:

[[CODE:27]]

`cancel()` sets a flag. A parked instance wakes at once. A running one lets its current step finish and stops at its next `ctx` call. (A running instance in another process notices the flag on its next lease renewal, within a third of `leaseDuration`.) Either way, the compensations of the completed steps run in reverse, and the instance ends as `cancelled` with the reason as its error message. `cancel()` returns the instance with an `accepted` flag. It's `false` when the instance had already completed or failed, when it is already compensating a failure, or when a cancel or a terminate was already requested. A second cancel changes nothing, and the first reason is kept.

Once the carrier has reported the delivery, the route answers `409`, because support should start a return instead. The workflow doesn't rely on that check. A cancel that reaches it after `ctx.commit('delivered')` stops the review request and refunds nothing. A cancel it sees before it has consumed the delivery event still refunds, because it hasn't reached its point of no return yet.

##### What each status means

An instance's `status` says what it's doing, and whether it needs you:

| Status | What it means | What to do |
| --- | --- | --- |
| `pending` | Started, and not yet claimed by a worker. One that stays `pending` waits for a concurrency slot or room in a rate-limit window, or is of a version no running worker registers | Nothing while a limit holds it. Otherwise, deploy a worker with that version, or delete the instance |
| `running` | A worker holds its lease and executes it | Nothing. `cancel()` stops it at its next `ctx` call, and `terminate()` without compensating |
| `suspended` | Parked on a sleep, a wait or a retry's backoff, until `wakeAt` or a signal | Nothing. A signal or `cancel()` wakes it |
| `compensating` | Undoing its completed steps after a failure or a cancel | Nothing: it ends as `failed`, `cancelled` or `compensation_failed`. `terminate()` stops the undo |
| `completed` | Done, with the result of `run()` as its `output` | Nothing, until retention purges it |
| `cancelled` | Cancelled, after its compensations ran, or terminated without them (`error.name` is `WorkflowTerminatedError`). `error.message` is the reason | Nothing, until retention purges it |
| `failed` | A step gave up, `ctx.fail()` was called, the run timeout passed or the journal hit its limit, and then its compensations ran. Or a definition error, such as a deploy that broke replay, failed it without compensating | If no compensation ran, fix the cause and retry it. Otherwise it's done: its completed steps were undone |
| `compensation_failed` | An undo gave up halfway. `error` is the original failure, with the compensation's own error as `error.compensation` | Fix the cause, such as a warehouse API that was down, and retry it. Or finish the undo by hand and delete the instance |

##### Retry, delete or terminate

`WorkflowClient` has the actions for the table's last column. Call them from a staff-only route or a script:

[[CODE:28]]

- **`retry()`** runs a `failed` instance again from its journal: completed steps return their results, the step that gave up gets its attempts back, and sleeps and waits the instance left behind start over. A deploy that broke replay is retried once the fixed code runs. It refuses an instance whose compensations ran, since resuming would build on undone work: start a new instance instead. An instance past its run timeout needs a new one, as the `timeout` option (counted from now), or `false` for none. A `compensation_failed` instance runs the compensations that didn't complete again, each with its attempts back, and ends as it would have: `failed` or `cancelled`.
- **`delete()`** removes a finished instance with its journal. An unfinished one needs the `force` option, and goes without running its compensations: use it for an instance no worker can run any more, such as one of a version you no longer deploy.
- **`cancel()`**, as above, stops an instance that is still running, and runs its compensations.
- **`terminate()`** stops an instance without running its compensations, for one whose undo mustn't or can't run, such as an order support has already refunded by hand. A parked instance stops at once, a running one at its next `ctx` call, and a compensating one after the compensation it's running. It ends as `cancelled`, with a `WorkflowTerminatedError` whose message is the reason (`Terminated.` without one). It's accepted after a `cancel()` too, which it replaces, and a `cancel()` after it is refused. Its children get their `parentClose`, as for any end.

`retry()` and `delete()` throw a `WorkflowStateError`, whose `status` is `409`, for a status where they make no sense, and when another change to the instance races them. A retry is journaled as `$retry:1`, `$retry:2` and so on, with the status and error it retried, and both actions are emitted, as `workflow-retried` and `workflow-deleted`.

##### Purge finished instances

Finished instances stay, with their journals, until you purge them. `purge()` deletes the ones that finished longer ago than its `olderThan` option, a batch at a time, and the signals no instance can take any more. An instance only takes signals sent after it started, so once every unfinished instance started after a signal, and the signal is older than `olderThan`, it goes; the newest signal always stays. `compensation_failed` instances wait for a person, so they're purged only when you list them in the `status` option. Run it every night, on one instance of your application, with `@Cron()` from `@nestjs/schedule` and `@OnOneInstance()` from [`@nestjs/locks`](/reliability/locks):

[[CODE:29]]

`purge()` resolves with the number of `instances` and `signals` it deleted, and of the rate-limit windows that ended (`rateLimits`). A signal's `id` deduplicates for as long as the signal is stored, so keep `olderThan` longer than any sender's redelivery window, such as your carrier's webhook retries.
