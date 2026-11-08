### Queues

Queues are a design pattern that helps you deal with common application scaling and performance challenges. Some examples of problems that queues can help you solve are:

- Smooth out processing peaks. For example, if users can initiate resource-intensive tasks at arbitrary times, you can add these tasks to a queue instead of performing them synchronously. Worker processes then pull tasks from the queue in a controlled manner. As the application grows, you can add queue consumers to scale up back-end task handling.
- Break up monolithic tasks that may otherwise block the Node.js event loop. For example, if a user request requires CPU-intensive work like audio transcoding, you can delegate this task to other processes, so user-facing processes remain responsive.
- Provide a reliable communication channel across services. For example, you can queue tasks (jobs) in one process or service and consume them in another. By listening for status events, any process or service can be notified of completion, errors, or other state changes in the job lifecycle. When queue producers or consumers fail, their state is preserved, and task handling can resume automatically when nodes restart.

Nest provides the `@nestjs/bullmq` package for BullMQ integration and the `@nestjs/bull` package for Bull integration. Both packages wrap their respective libraries, which are developed by the same team. Bull is in maintenance mode (the team only fixes bugs), while BullMQ is actively developed and offers a modern TypeScript implementation with a different set of features. If Bull meets your requirements, it remains a reliable, battle-tested choice.

Both BullMQ and Bull use [Redis](https://redis.io/) to persist job data, so you need a running Redis instance. Because they are Redis-backed, your queue architecture can be fully distributed and platform-independent. For example, you can run some queue <a href="application/queues#producers">producers</a>, <a href="application/queues#consumers">consumers</a>, and <a href="application/queues#event-listeners">listeners</a> in Nest on one or more nodes, and other producers, consumers, and listeners on other Node.js platforms on other network nodes.

This chapter covers the `@nestjs/bullmq` and `@nestjs/bull` packages. For more background and implementation details, see the [BullMQ documentation](https://docs.bullmq.io/) and the [Bull reference](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md).

#### BullMQ installation

To begin using BullMQ, install the required dependencies.

[[CODE:1]]

Once the installation process is complete, import the `BullModule` into the root `AppModule`.

[[CODE:2]]

The `forRoot()` method registers a `bullmq` configuration object that all queues registered in the application use (unless specified otherwise). The following are a few of the configuration properties:

- `connection: ConnectionOptions` - Options to configure the Redis connection. See [Connections](https://docs.bullmq.io/guide/connections) for more information.
- `backendFactory: BullMQBackendFactory` - Factory function for pluggable backends (e.g., PostgreSQL). See [Pluggable backends](/application/queues#pluggable-backends) for more information.
- `prefix: string` - Prefix for all queue keys (defaults to `bull`).
- `defaultJobOptions: DefaultJobOptions` - Default settings for new jobs. See [DefaultJobOptions](https://docs.bullmq.io/api/interfaces/v6.DefaultJobOptions.html) for more information. These don't take effect for jobs added through a `FlowProducer`; see [bullmq#1034](https://github.com/taskforcesh/bullmq/issues/1034) for an explanation.
- `settings: AdvancedRepeatOptions` - Advanced settings for repeatable jobs. These should usually not be changed. See [AdvancedRepeatOptions](https://docs.bullmq.io/api/interfaces/v6.AdvancedRepeatOptions.html) for more information.
- `extraOptions` - Extra options for module initialization. See [Manual registration](/application/queues#manual-registration).

All options are optional. Apart from `extraOptions`, they are passed directly to the BullMQ `Queue` constructor. See the [QueueOptions API reference](https://docs.bullmq.io/api/interfaces/v6.QueueOptions.html) for the complete list.

To register a queue, import the `BullModule.registerQueue()` dynamic module, as follows:

[[CODE:3]]

> info **Hint** Create multiple queues by passing multiple configuration objects (as separate arguments) to the `registerQueue()` method.

The `registerQueue()` method instantiates and/or registers queues. Queues are shared across modules and processes that connect to the same underlying Redis database with the same credentials. Each queue is identified by its `name` property. The queue name serves both as an injection token (for injecting the queue into controllers and providers) and as an argument to decorators that associate consumer classes and listeners with queues.

You can also override some of the preconfigured options for a specific queue, as follows:

[[CODE:4]]

BullMQ also supports parent-child relationships between jobs. This enables flows, where jobs are the nodes of trees of arbitrary depth. See [Flows](https://docs.bullmq.io/guide/flows) in the BullMQ documentation to learn more.

To register a flow producer, use the `registerFlowProducer()` method:

[[CODE:5]]

Because jobs are persisted in Redis, each time a named queue is instantiated (e.g., when an app starts or restarts), it attempts to process any old jobs left over from a previous unfinished session.

Each queue can have one or many producers, consumers, and listeners. Consumers retrieve jobs from the queue in a specific order: FIFO (the default), LIFO, or according to priorities. The <a href="application/queues#job-options">job options</a> section explains how to control the processing order.

<app-banner-enterprise></app-banner-enterprise>

#### Named configurations

If your queues connect to multiple Redis instances, you can use a technique called **named configurations**. This feature lets you register several configurations under specified keys, which you can then refer to in the queue options.

For example, assuming you have an additional Redis instance (apart from the default one) used by a few queues in your application, you can register its configuration as follows:

[[CODE:6]]

In the example above, `'alternative-config'` is a configuration key (it can be any string).

You can now point to this configuration in the `registerQueue()` options object:

[[CODE:7]]

#### Pluggable backends (PostgreSQL)

BullMQ supports pluggable storage backends (such as PostgreSQL) through custom backend factories. You can configure a `backendFactory` globally in `BullModule.forRoot()` or per-queue in `BullModule.registerQueue()`.

[[CODE:8]]

`migrate: true` creates BullMQ's tables at startup, in a `bullmq` schema of their own. Without it, the application fails on a database that doesn't have them yet.

The configured `backendFactory` is automatically propagated across all underlying BullMQ components (`Queue`, `Worker`, `QueueEvents`, and `FlowProducer`), including `@Processor()` and `@QueueEventsListener()` worker hosts.

#### Producers

Job producers add jobs to queues. Producers are typically application services (Nest [providers](/providers)). To add jobs to a queue, first inject the queue into the service:

[[CODE:9]]

> info **Hint** The `@InjectQueue()` decorator identifies the queue by its name, as provided in the `registerQueue()` method call (e.g., `'audio'`).

Now, add a job by calling the queue's `add()` method, passing a job name and a user-defined data object. Job data must be serializable, because jobs are stored in Redis. The shape of the data is arbitrary; use it to represent the semantics of your job. The name lets a <a href="application/queues#consumers">consumer</a> tell different kinds of jobs apart.

[[CODE:10]]

#### Job options

Jobs can have additional options associated with them. Pass an options object as the third argument of the `Queue.add()` method, after the job data. Some of the job options are:

- `priority`: `number` - Priority value, from 0 to 2,097,151. `0` (the default) means no explicit priority; jobs without a priority are processed before prioritized jobs, and among prioritized jobs, lower numbers are processed first. Using priorities has a slight impact on performance, so use them only when required.
- `delay`: `number` - Time (in milliseconds) to wait until this job can be processed. For accurate delays, workers and producers should have their clocks synchronized.
- `attempts`: `number` - The total number of attempts to try the job until it completes (defaults to 1).
- `backoff`: `number | BackoffOptions` - Backoff setting for automatic retries if the job fails. See [BackoffOptions](https://docs.bullmq.io/api/interfaces/v6.BackoffOptions.html).
- `lifo`: `boolean` - If `true`, adds the job to the right end of the queue instead of the left (default `false`).
- `jobId`: `string` - Overrides the job ID. By default, the job ID is a unique integer. If you use this option, it's up to you to ensure the ID is unique. A job with an ID that already exists is not added.
- `removeOnComplete`: `boolean | number | KeepJobs` - If `true`, removes the job when it successfully completes. A number specifies how many jobs to keep, and a `KeepJobs` object specifies a maximum age and/or count. By default, the job is kept in the completed set.
- `removeOnFail`: `boolean | number | KeepJobs` - If `true`, removes the job when it fails after all attempts. A number or `KeepJobs` object works as for `removeOnComplete`. By default, the job is kept in the failed set.
- `stackTraceLimit`: `number` - Limits the number of stack trace lines recorded for a failed job.

> info **Hint** BullMQ no longer accepts a `repeat` option in `Queue.add()`. To run a job repeatedly (e.g., on a cron pattern), create a job scheduler with the `Queue#upsertJobScheduler()` method. See [Job Schedulers](https://docs.bullmq.io/guide/job-schedulers) in the BullMQ documentation.

Here are a few examples of customizing jobs with job options.

To delay the start of a job, use the `delay` property.

[[CODE:11]]

To add a job to the right end of the queue (i.e., process it as **LIFO**, Last In First Out), set the `lifo` property to `true`.

[[CODE:12]]

To prioritize a job, use the `priority` property.

[[CODE:13]]

For the full list of options, see the [JobsOptions](https://docs.bullmq.io/api/types/v6.JobsOptions.html) and [BaseJobOptions](https://docs.bullmq.io/api/interfaces/v6.BaseJobOptions.html) API references.

#### Consumers

A consumer is a **class** defining methods that process jobs added to the queue, listen for events on the queue, or both. Declare a consumer class using the `@Processor()` decorator as follows:

[[CODE:14]]

> info **Hint** Consumers must be registered as `providers` so the `@nestjs/bullmq` package can pick them up.

The decorator's string argument (e.g., `'audio'`) is the name of the queue to associate with the class. The consumer class must extend `WorkerHost` and implement its `process()` method:

[[CODE:15]]

The `process()` method is called whenever the worker is idle and there are jobs to process in the queue. It receives the `job` object as its only argument. The value it returns is stored in the job object and can be accessed later, for example, in a listener for the `completed` event.

`Job` objects have multiple methods that allow you to interact with their state. For example, the code above uses the `updateProgress()` method to update the job's progress. See the [Job API reference](https://docs.bullmq.io/api/classes/v6.Job.html) for the complete list.

In Bull, you could designate that a job handler method handles **only** jobs of a certain type (jobs with a specific `name`) by passing that `name` to the `@Process()` decorator, as shown below.

> warning **Warning** This doesn't work with BullMQ. Read on for the BullMQ approach.

[[CODE:16]]

BullMQ doesn't support this behavior, because it caused confusion. Instead, use a `switch` statement on the job name to call different services or logic for each kind of job:

[[CODE:17]]

This is covered in the [named processor](https://docs.bullmq.io/patterns/named-processor) section of the BullMQ documentation.

#### Request-scoped consumers

When a consumer is flagged as request-scoped (see [injection scopes](/fundamentals/injection-scopes#provider-scope)), a new instance of the class is created exclusively for each job. The instance is garbage-collected after the job completes.

[[CODE:18]]

Because request-scoped consumer classes are instantiated dynamically and scoped to a single job, you can inject the current job through the constructor using the `JOB_REF` token.

[[CODE:19]]

> info **Hint** The `JOB_REF` token is imported from the `@nestjs/bullmq` package.

#### Event listeners

BullMQ emits a set of events when queue and/or job state changes occur. You can subscribe to these events at the worker level using the `@OnWorkerEvent(event)` decorator, or at the queue level with a dedicated listener class and the `@OnQueueEvent(event)` decorator.

Worker events must be declared within a <a href="application/queues#consumers">consumer</a> class (i.e., within a class decorated with the `@Processor()` decorator). To listen for an event, use the `@OnWorkerEvent(event)` decorator with the event you want to handle. For example, to listen to the event emitted when a job enters the active state in the `audio` queue, use the following construct:

[[CODE:20]]

The complete list of worker events and their arguments is available as the properties of the [WorkerListener](https://docs.bullmq.io/api/interfaces/v6.WorkerListener.html) interface.

Queue event listeners must use the `@QueueEventsListener(queue)` decorator and extend the `QueueEventsHost` class provided by `@nestjs/bullmq`. To listen for an event, use the `@OnQueueEvent(event)` decorator with the event you want to handle. For example, to listen to the event emitted when a job enters the active state in the `audio` queue, use the following construct:

[[CODE:21]]

> info **Hint** Queue event listeners must be registered as `providers` so the `@nestjs/bullmq` package can pick them up.

The complete list of queue events and their arguments is available as the properties of the [QueueEventsListener](https://docs.bullmq.io/api/interfaces/v6.QueueEventsListener.html) interface.

#### Queue management

Queues have an API for management functions such as pausing and resuming, and retrieving the count of jobs in various states. See the [Queue API reference](https://docs.bullmq.io/api/classes/v6.Queue.html) for the full API. Invoke these methods directly on the `Queue` object, as shown in the pause and resume examples below.

Pause a queue with the `pause()` method. A paused queue doesn't process new jobs until it's resumed, but jobs already being processed continue until they finish.

[[CODE:22]]

To resume a paused queue, use the `resume()` method, as follows:

[[CODE:23]]

#### Observing queues in production

Queues fail in ways that HTTP endpoints don't. A job doesn't return a status code to an impatient user. It retries quietly, three times, with backoff, and the only symptom is that something downstream never happened. The two questions that matter are therefore *"is this queue keeping up?"* and *"did that job run at all?"*, and the consumer's own logs can't answer either of them.

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') instruments queue consumers automatically, the same way it instruments controllers: `@Processor()` classes and their handlers are recognized as jobs, so no manual span wiring is needed:

- **Queue wait time is measured separately from execution time.** A job that takes 200 ms to run but sat in the queue for four minutes is a capacity problem, not a slow handler. The two numbers are reported side by side, so you can tell which one you have.
- **Attempts and failure reasons are recorded per run.** You see that a job succeeded on attempt 3 rather than seeing only the success, which is usually the difference between "fine" and "quietly degrading".
- **Silence is alertable.** A *job silence* rule fires when a named job hasn't reported for longer than a tolerance you choose. That's how you find out that the nightly billing consumer stopped running on the night it stops, rather than at the end of the month.

Failed jobs carry the same error card as failed requests: the resolved stack trace with source lines, the logs written during the run, and the waterfall of what the job did before it threw. See the [Observability](/observability/overview) chapter for setup.

#### Separate processes

Job handlers can also run in a separate (forked) process (see [Sandboxed processors](https://docs.bullmq.io/guide/workers/sandboxed-processors) in the BullMQ documentation). This has several advantages:

- The process is sandboxed, so if it crashes, the worker isn't affected.
- You can run blocking code without affecting the queue (jobs don't stall).
- Better utilization of multi-core CPUs.
- Fewer connections to Redis.

[[CODE:24]]

> warning **Warning** Because your function runs in a forked process, dependency injection (and the IoC container) isn't available. Your processor function must contain (or create) all instances of the external dependencies it needs.

#### Async configuration

You may want to pass `bullmq` options asynchronously instead of statically. In this case, use the `forRootAsync()` method, which provides several ways to handle async configuration. Likewise, to pass queue options asynchronously, use the `registerQueueAsync()` method.

One approach is to use a factory function:

[[CODE:25]]

The factory behaves like any other [asynchronous provider](/fundamentals/async-providers) (e.g., it can be `async` and can inject dependencies through `inject`).

[[CODE:26]]

Alternatively, you can use the `useClass` syntax:

[[CODE:27]]

The construction above instantiates `BullConfigService` inside `BullModule` and uses it to provide an options object by calling `createSharedConfiguration()`. This means `BullConfigService` has to implement the `SharedBullConfigurationFactory` interface, as shown below:

[[CODE:28]]

To reuse a provider imported from a different module instead of creating `BullConfigService` inside `BullModule`, use the `useExisting` syntax.

[[CODE:29]]

This construction works the same as `useClass` with one critical difference: `BullModule` looks up imported modules to reuse an existing `ConfigService` instead of instantiating a new one.

Likewise, to pass queue options asynchronously, use the `registerQueueAsync()` method. Specify the `name` attribute outside the factory function.

[[CODE:30]]

#### Manual registration

By default, `BullModule` automatically registers BullMQ components (queues, processors, and event listener services) in the `onModuleInit` lifecycle hook. In some cases, this behavior isn't what you want. To prevent automatic registration, enable `manualRegistration` in `BullModule`:

[[CODE:31]]

To register these components manually, inject `BullRegistrar` and call its `register()` method, ideally within the `onModuleInit()` or `onApplicationBootstrap()` lifecycle hook.

[[CODE:32]]

Until you call `BullRegistrar#register()`, no BullMQ components work, which means no jobs are processed.
