#### Limits, children and batch work

##### Limit how many run at once

A worker runs every due instance it has room for. Three options decide what runs, and in what order, across every worker: a concurrency limit, a rate limit and a priority. The fulfilment sets the first two in `@Workflow()`:

[[CODE:30]]

**Concurrency.** `concurrency` caps how many instances run at once: a `limit` for the workflow, or a `limit` per key with a `key` function, here the customer's id. An array takes one of each. An instance holds a slot only while an execution runs it, compensations included, not while it sleeps or waits: a limit protects what the steps call, and an order parked for days holds up nobody. A process that crashes frees its slots once its leases expire. Instances past a limit stay due and wait for a slot, most overdue first, and a full key is passed over, so one busy customer never holds back another's order. The key is computed from the input when the instance starts, and `start()`'s `concurrencyKey` option sets another, for a workflow whose limit has a key.

**Rate limits.** `rateLimit` caps how many executions start per window: `max` per `duration` for the workflow, or per key with a `key` function, which `start()`'s `rateLimitKey` option overrides. Every execution counts, the first one and each resumption after a sleep, a signal, a retry's backoff or a cancel, because each can call what the limit protects. The fulfilment sends the payment provider one request per execution at most, so this caps its requests, and the executions that send none too. A window opens with the first execution after the previous one ended, and admits `max` executions until it closes, so two windows back to back can admit twice `max` within one `duration`. Say the payment provider allows 20 requests a second: allow 10.

**Priorities.** `start()`'s `priority` option decides what is claimed first: the lowest priority, then the most overdue. It's an integer from 1 to 2,097,151, and instances started without one go before every prioritized one. Express orders go first:

[[CODE:31]]

Since instances without a priority go first, once orders have one, other work needs one to go after them: the invoice batch's schedule gives it 10, in [Run workflows on a schedule](/reliability/workflows#run-workflows-on-a-schedule). An instance keeps its priority for every execution, and children inherit their parent's. Priorities are strict: a steady stream of express orders holds the standard ones back. `@StartOn()` takes the same option, as [With CQRS](/reliability/workflows#with-cqrs) shows.

Limits come from the highest registered version of the workflow and apply to all its versions, and each process applies the limits of the code it runs, so deploy a change to them everywhere. Claims never admit more than the limits allow, but can admit less for a moment: workers polling at the same time can take a few polls to fill a short window, and with both a concurrency key and a rate-limit key, a candidate that one kind of key passes over waits for the next claim. Claims also sort the due instances by priority, which the index on `wake_at` doesn't give them: cheap while few instances are due, noticeable with a large backlog. `drain()` stops when nothing left can start.

##### Start child workflows

Shipping grows: book the carrier's pickup, cancel it if the order is undone, then wait for the delivery or the return. It's a process of its own, with its own steps, retries and status, so give it a workflow of its own, and run it as a **child** of the fulfilment:

[[CODE:32]]

`CarrierClient` is a stand-in for the carrier's booking API, which, like the payment provider, answers a repeated idempotency key with the first booking. In the fulfilment, the child takes the place of the wait:

[[CODE:33]]

Register `ShipmentWorkflow` and `CarrierClient` as providers, next to the fulfilment. The carrier's webhook doesn't change: it signals the order's id, and the shipment is now the instance waiting for it.

- **`ctx.executeChild()`** starts the child and waits for its end. Both are journaled, as `$child:<id>` and `$result:<id>`, so a replay gets the same child back instead of starting another, and the fulfilment parks in the meantime. `ctx.startChild()` only starts it, and returns a handle: its `result()` waits for the child, and the handle is a condition of `waitForAny()`, to race the child against a timer or a signal.
- **Ids.** A child's id defaults to its parent's id, the workflow's name and a count of that workflow's children in this run, such as `order-71e1973d/shipment#1`. Give children started from parallel branches an `id` option derived from your data, so that a replay, which can reach them in another order, finds each one.
- **Failures.** If the child fails, is cancelled or is terminated, `executeChild()` throws a `ChildWorkflowFailedError`, with its `status` and its error as `cause`. Left uncaught, it fails the fulfilment like any error: a returned parcel fails the shipment, whose compensation cancels its booking, and then the fulfilment, whose compensations refund the charge and release the stock. Catch it to try something else, such as another carrier.
- **`parentClose`** decides what happens to a child that is still running when its parent ends or starts compensating: `'cancel'`, the default, cancels it, and its compensations run; `'terminate'` stops it without them; `'abandon'` leaves it running. When support cancels the order, the shipment is cancelled with it, and the pickup with the shipment.
- A child inherits its parent's priority, unless `startChild()` gets one, and takes `concurrencyKey` and `rateLimitKey` options as `start()` does. `getStatus()` with the `children` option lists an instance's children, each with its `parentId`, and `list()` pages through them by `parentId`.

##### Long-running steps

A step can run for hours. While it runs, the worker keeps renewing the lease in the background. For long batch work, checkpoint progress so a crash doesn't restart the job from zero. Here, a monthly batch renders invoices one page at a time:

[[CODE:34]]

- `heartbeat(progress)` writes the checkpoint to the journal. If the attempt dies, the next one receives it as `progress`. Annotating the parameter as `WorkflowStepContext<Checkpoint>` types both. The page that was in flight is rendered again, so `renderPage()` must overwrite rather than append.
- `heartbeatTimeout` fails an attempt that stops calling `heartbeat()`, such as one stuck on a hung socket, while the process is still alive. A `timeout` option caps the attempt's total duration.
- `signal` is aborted on shutdown, on a lost lease and on those timeouts. Pass it to your I/O.

A schedule, below, starts the batch every month. When the work belongs on processes of its own, such as a pool of PDF renderers, hand it to a [BullMQ](/application/queues) queue from a step, and wait for the job to report back with a signal. The job id is the step's `idempotencyKey`, so a retried step doesn't enqueue it twice:

[[CODE:35]]

The queue's processor reports back when the job is done:

[[CODE:36]]

The `id` stores the signal once when BullMQ runs the job again, and a job that finishes before the workflow reaches the wait still counts, because signals are durable.

##### Run workflows on a schedule

The invoices are due on the 1st of every month. Instead of a cron job that starts the batch, declare a schedule on the workflow:

[[CODE:37]]

Every worker whose code declares the schedule starts its occurrences, and each occurrence starts one instance, however many workers there are: its id is the schedule's id and the occurrence's time, such as `monthly-invoices@2026-10-01T06:00:00.000Z`. The `input` function receives the occurrence, its schedule's `id` and its time `at`, and so does the instance, as `ctx.schedule`, which is `null` for an instance started otherwise.

- **When.** `cron` takes 5 fields, or 6 with the seconds first, `every` a fixed interval, and `rrule` an RFC 5545 recurrence rule. Times are wall-clock times in `tz`, UTC by default, so the batch starts at 02:00 in New York before and after the clocks change. When the clocks go back, a local time that occurs twice runs once, the first time, so an hourly schedule skips the second pass of the repeated hour. When they go forward, a time that doesn't exist still runs, as much later as the clocks jumped: 02:30 runs at 03:30. `every` takes no `tz`: it repeats a fixed interval whatever the time zone. `startAt`, `endAt` and `limit` bound a schedule.
- **`missed`** says what happens to occurrences no worker was up to start, during a deploy or an outage. `'skip'`, the default, starts one only if a worker finds it within a minute of its time; `'once'` starts the latest of them; `'all'` starts each of them, the latest 100 at most, and needs `overlap: 'allow'`. The occurrences it passes over are reported in a `schedule-skipped` event.
- **`overlap`** says what an occurrence does while an instance the schedule started is unfinished: `'skip'`, the default, passes it over, with a `schedule-skipped` event; `'allow'` starts it anyway; `'cancel-previous'` cancels the running one; `'buffer-one'` starts it once the running one ends.

A declared schedule belongs to the code, also while a rolling deploy runs the old and the new code side by side. Each process saves the schedules that its workflows declare when it starts, and confirms them every minute while its worker runs. A process leaves a schedule as it is while another process confirms it, if its own code doesn't declare it or a newer version of the workflow declares it differently. Once no process has confirmed it for five minutes, a process deletes a schedule that its code doesn't declare, whether or not it runs the schedule's workflow, and replaces another declaration with its own. So an old pod that restarts mid-rollout leaves alone the schedules that the new code adds or a new version changes, a schedule that a deploy drops goes about five minutes after the last process of the old code stopped, also when the deploy removes its workflow, and a rollback brings the old declaration back.

Processes of other code on the same database, such as the workers of other workflows, also delete a schedule when no worker whose code declares it has run for five minutes, as while those workers are scaled to zero. The next process whose code declares it saves it again as it starts, and the schedule starts over: from its next occurrence, unpaused, with its runs counted from zero.

`WorkflowClient.schedules`, also injectable as `WorkflowSchedules`, handles schedules at runtime. `trigger('monthly-invoices')` starts an occurrence now, whatever `overlap` says and even while the schedule is paused, with its time as `at`. `pause()` stops the occurrences until `resume()`, which starts again from the first one after now. `preview()` returns the next occurrences, in epoch milliseconds, and `get()` and `list()` read the schedules. A schedule that isn't in the code, such as one per customer, is saved with `upsert()`, and `remove()` deletes it, leaving the instances it started running:

[[CODE:38]]

`upsert()` and `remove()` refuse a declared schedule, which you change in the code.

##### Wait for a result

Most callers start a workflow and move on. Some need its result: an accountant who wants a month's invoices now, before the schedule renders them, calls a route that renders them and answers with the count. `startAndWait()` starts the instance and waits for it to end:

[[CODE:39]]

- `startAndWait()` is `start()`, then `result()`, which waits for an instance to end and resolves with its output. For an id that has an instance already, it waits for that one, so the accountant calling the route again, while the batch runs or after it ended, gets the same batch. The wait's options are the fourth argument: the third one's `timeout` stays the instance's run timeout.
- Past the wait's `timeout`, in wall-clock time rather than the module's clock, it rejects with `WorkflowResultTimeoutError`, and the instance keeps running: the route answers `202`. A `signal` option stops the wait when it's aborted, as when the caller goes away.
- On shutdown, a wait lasts while the worker finishes its running steps, up to `shutdownTimeout`, so an instance that ends meanwhile still answers with its result. Then the wait rejects with an `Error`, before Nest closes the HTTP server, and the route answers at once, here with a `500`, instead of holding up the shutdown until its wait's `timeout`.
- An instance that failed, was cancelled or terminated rejects with a `WorkflowFailedError`, whose `status` says how it ended and whose `cause` is its error. Here, that's a `500`.
- `result()` waits for an instance by its id, such as the one `trigger()` started, whichever process runs it. `startAndWait()` refuses the `transaction` option, since the instance only exists once your transaction commits: call `start()` in the transaction, and `result()` after the commit.

#### Deploy changes safely

The journal is keyed by name, so step, sleep and wait names are a contract with every instance that is still running. The name is also part of the idempotency key.

Suppose you rename `charge-payment` to `charge-card` and deploy. An order that was waiting for the carrier resumes, finds no `charge-card` entry in its journal, and would charge the card again, under a key the payment provider has never seen. Before the first new step of an execution runs, the engine checks that the code reached every step in the journal. Here it didn't, so the instance fails without charging:

[[CODE:40]]

Its compensations don't run either, because they're defined by the code that no longer matches. The instance is left for a person to handle. The check doesn't see a step whose name stayed the same but whose body now does something different.

Some changes don't need a new version:

- changing a step's body without changing what it means,
- adding steps after the last step, sleep or wait that any running instance has reached,
- changing retry options and timeouts.

Anything else ships as a new version. Say marketing wants an order confirmation right after payment. Inserting a step before `reserve-stock` changes what a replay sees, so copy the class and bump its version:

[[CODE:41]]

Register both classes. An instance keeps the version it started on, and a worker only claims versions it has registered, so old and new pods can run side by side during a rolling deploy. New instances start on the highest registered version, even when the controller still passes `OrderFulfilmentWorkflow`, because the class only identifies the workflow's name. To pin one, add `version: 1` to the `start()` options. Remove version 1 once `list()` with the workflow's name, `version: 1` and the unfinished statuses (`pending`, `running`, `suspended` and `compensating`) comes back empty.

##### Rules for workflow code

`run()` executes again from the top every time an instance resumes. Code between steps runs on every execution, so it must make the same decisions each time:

- Put anything that touches or reads the outside world in a step: HTTP calls, database reads and writes, feature flags.
- Outside steps, use `ctx.now()`, `ctx.random()` and `ctx.uuid()` instead of `Date.now()`, `Math.random()` and `randomUUID()`. They're journaled.
- In `run()`, only `await` `ctx` operations and pure computation. Never wait on a real timer.
- Step, sleep and wait names must be unique within a run. In a loop, add the index to the name, such as `remind-1` and `remind-2`. Give children started from parallel branches an `id` of their own.
- Don't call `ctx` methods inside a step's function. The function runs once and replays only see its result, so the engine fails the instance when a step calls `ctx`. Throw a `NonRetryableStepError` from a step instead of calling `ctx.fail()` there.
- If you catch errors in `run()`, rethrow what you don't handle. `isWorkflowInterrupt()` identifies the engine's control flow. The engine doesn't depend on it: after a swallowed interrupt no step runs, `commit()` throws again, and a cancel still cancels. But `finally` blocks run at every suspension, so keep side effects out of them.
- `Promise.all()` over steps is fine, and a step in the same `Promise.all()` as a sleep or wait starts after it. `Promise.race()` and `Promise.any()` are not replay-safe.
- Inputs, step results and signal payloads must be JSON-serializable. A `Date` comes back as a string, on the first run and on every replay, and the `Journaled` types of results and payloads say so.
- Keep no per-run state on `this`: one instance of the class serves every order.

#### Try it and test it

##### Try it

Create the database, apply your migrations, and start the application with `DATABASE_URL` pointing at the database:

[[CODE:42]]

The log names the store in use, not the in-memory default, and says that the store created its schema: your migrations created `orders`, and the store its own tables. Place an order, then ask where it is:

[[CODE:43]]

The order and its fulfilment were committed together, the worker picked the instance up, the card is charged, the kibble is reserved, and the instance is parked until the carrier reports the delivery or the return, or the 3-day deadline in `wakeAt` passes.

Now play the carrier and report the delivery:

[[CODE:44]]

The instance passed its point of no return and is sleeping until the review request is due in 7 days. Support can no longer cancel the order, and a delivery for an order the store doesn't know is refused:

[[CODE:45]]

Place a second order (it gets id `58b424f5` here) and cancel it while it waits for the carrier:

[[CODE:46]]

The journal shows both compensations: the stock was released first, then the charge was refunded. The wait never finished, so it's marked `cancelled`, and the stage stays where the workflow last set it.

The instances are rows in your database, in the store's schema, next to the orders:

[[CODE:47]]

Finally, restart the application and ask for the first order again. Its status hasn't changed, and the store found nothing to migrate. Start a second process on another port against the same database, and the two share the work: each instance runs on one of them at a time. To see the 3-day timeout without waiting 3 days, use a test clock, as the tests below do.

##### Test with a manual clock

Two things make workflow tests fast and deterministic:

- Every timestamp the engine uses (deadlines, retry times, lease expiry and `ctx.now()`) comes from the module's `clock`. A `ManualWorkflowClock` only moves when you call `advance()`.
- With the worker disabled, nothing runs in the background. `WorkflowWorker.drain()` runs every due instance until none is left that can start, and starts the occurrences of schedules that the clock has passed. The clock starts on 1 January 2026 at 00:00 UTC, so a test that moves it by days also starts the invoice batch's first occurrence, at 07:00 UTC.

Run the tests on PGlite, with your real migrations. Override the database `DrizzleModule` registers (`getDrizzleToken()` returns its token) with one on PGlite: the workflow store follows, because its factory injects it, and creates its schema there when the application starts. Override `WORKFLOWS_MODULE_OPTIONS` with a `ManualWorkflowClock` and a disabled worker. Share the database and the stand-ins for the external APIs between applications, because they outlive a process:

[[CODE:48]]

With a manual clock, the 3-day timeout is one `advance()` call:

[[CODE:49]]

##### Test crash recovery

`createWorld()` creates a fresh database per test. Crash safety needs two applications on the same database. Closing an application while a step hangs simulates a crash: the shutdown timeout expires, and the dead process's lease stays in the database until it expires. The second application takes over after that:

[[CODE:50]]

The same setup covers a crash in the middle of the compensations: the next process replays the journal to rebuild the list of compensations, skips the ones already done, and continues with the rest. PGlite is a single connection, so it can't show two workers racing for the same instance; the tutorial's tests of the store run the contract's races on a PostgreSQL server, along with three applications sharing 30 orders.

To give a test its own store without overriding providers, call `registerSource()` on `moduleRef.get(WorkflowStorage)` before `init()`, with `replace: true`: without it, a second registration throws. The `clock` option takes any `WorkflowClock`, an object whose `now()` returns epoch milliseconds, so a test can drive the engine from a clock it already has.
