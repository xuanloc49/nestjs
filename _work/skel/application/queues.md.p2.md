#### Bull installation

> info **Note** If you use BullMQ, skip this section and the ones that follow.

To begin using Bull, install the required dependencies.

[[CODE:33]]

Once the installation process is complete, import the `BullModule` into the root `AppModule`.

[[CODE:34]]

The `forRoot()` method registers a `bull` configuration object that all queues registered in the application use (unless specified otherwise). A configuration object consists of the following properties (all optional):

- `limiter: RateLimiter` - Options to control the rate at which the queue's jobs are processed. See [RateLimiter](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) for more information.
- `redis: RedisOpts` - Options to configure the Redis connection. See [RedisOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) for more information.
- `prefix: string` - Prefix for all queue keys.
- `defaultJobOptions: JobOpts` - Options to control the default settings for new jobs. See [JobOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queueadd) for more information.
- `settings: AdvancedSettings` - Advanced queue configuration settings. These should usually not be changed. See [AdvancedSettings](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) for more information.

These options are passed directly to the Bull `Queue` constructor. See the [Queue section of the Bull reference](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) for details.

To register a queue, import the `BullModule.registerQueue()` dynamic module, as follows:

[[CODE:35]]

> info **Hint** Create multiple queues by passing multiple configuration objects (as separate arguments) to the `registerQueue()` method.

The `registerQueue()` method instantiates and/or registers queues. Queues are shared across modules and processes that connect to the same underlying Redis database with the same credentials. Each queue is identified by its `name` property. The queue name serves both as an injection token (for injecting the queue into controllers and providers) and as an argument to decorators that associate consumer classes and listeners with queues.

You can also override some of the preconfigured options for a specific queue, as follows:

[[CODE:36]]

Because jobs are persisted in Redis, each time a named queue is instantiated (e.g., when an app starts or restarts), it attempts to process any old jobs left over from a previous unfinished session.

Each queue can have one or many producers, consumers, and listeners. Consumers retrieve jobs from the queue in a specific order: FIFO (the default), LIFO, or according to priorities. The <a href="application/queues#job-options">job options</a> section explains how to control the processing order.

<app-banner-enterprise></app-banner-enterprise>

#### Named configurations

If your queues connect to multiple Redis instances, you can use a technique called **named configurations**. This feature lets you register several configurations under specified keys, which you can then refer to in the queue options.

For example, assuming you have an additional Redis instance (apart from the default one) used by a few queues in your application, you can register its configuration as follows:

[[CODE:37]]

In the example above, `'alternative-config'` is a configuration key (it can be any string).

You can now point to this configuration in the `registerQueue()` options object:

[[CODE:38]]

#### Producers

Job producers add jobs to queues. Producers are typically application services (Nest [providers](/providers)). To add jobs to a queue, first inject the queue into the service:

[[CODE:39]]

> info **Hint** The `@InjectQueue()` decorator identifies the queue by its name, as provided in the `registerQueue()` method call (e.g., `'audio'`).

Now, add a job by calling the queue's `add()` method, passing a user-defined data object. Job data must be serializable, because jobs are stored in Redis. The shape of the data is arbitrary; use it to represent the semantics of your job.

[[CODE:40]]

#### Named jobs

Jobs can have names. This lets you create specialized <a href="application/queues#consumers">consumers</a> that only process jobs with a given name.

[[CODE:41]]

> warning **Warning** When using named jobs, you must create a processor for each unique name added to a queue, or the queue reports that a processor for the given job is missing. See <a href="application/queues#consumers">consumers</a> for more information on consuming named jobs.

#### Job options

Jobs can have additional options associated with them. Pass an options object after the job data in the `Queue.add()` method. The job options are:

- `priority`: `number` - Optional priority value. Ranges from 1 (highest priority) to MAX_INT (lowest priority). Using priorities has a slight impact on performance, so use them with caution.
- `delay`: `number` - Time (in milliseconds) to wait until this job can be processed. For accurate delays, both server and clients should have their clocks synchronized.
- `attempts`: `number` - The total number of attempts to try the job until it completes.
- `repeat`: `RepeatOpts` - Repeats the job according to a cron specification. See [RepeatOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queueadd).
- `backoff`: `number | BackoffOpts` - Backoff setting for automatic retries if the job fails. See [BackoffOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queueadd).
- `lifo`: `boolean` - If `true`, adds the job to the right end of the queue instead of the left (default `false`).
- `timeout`: `number` - The number of milliseconds after which the job fails with a timeout error.
- `jobId`: `number | string` - Overrides the job ID. By default, the job ID is a unique integer. If you use this option, it's up to you to ensure the ID is unique. A job with an ID that already exists is not added.
- `removeOnComplete`: `boolean | number` - If `true`, removes the job when it successfully completes. A number specifies how many jobs to keep. By default, the job is kept in the completed set.
- `removeOnFail`: `boolean | number` - If `true`, removes the job when it fails after all attempts. A number specifies how many jobs to keep. By default, the job is kept in the failed set.
- `stackTraceLimit`: `number` - Limits the number of stack trace lines recorded for a failed job.

Here are a few examples of customizing jobs with job options.

To delay the start of a job, use the `delay` property.

[[CODE:42]]

To add a job to the right end of the queue (i.e., process it as **LIFO**, Last In First Out), set the `lifo` property to `true`.

[[CODE:43]]

To prioritize a job, use the `priority` property.

[[CODE:44]]

#### Consumers

A consumer is a **class** defining methods that process jobs added to the queue, listen for events on the queue, or both. Declare a consumer class using the `@Processor()` decorator as follows:

[[CODE:45]]

> info **Hint** Consumers must be registered as `providers` so the `@nestjs/bull` package can pick them up.

The decorator's string argument (e.g., `'audio'`) is the name of the queue to associate with the class methods.

Within a consumer class, declare job handlers by decorating handler methods with the `@Process()` decorator.

[[CODE:46]]

The decorated method (e.g., `transcode()`) is called whenever the worker is idle and there are jobs to process in the queue. It receives the `job` object as its only argument. The value it returns is stored in the job object and can be accessed later, for example, in a listener for the `completed` event.

`Job` objects have multiple methods that allow you to interact with their state. For example, the code above uses the `progress()` method to update the job's progress. See the [Job section of the Bull reference](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#job) for the complete `Job` API.

You can designate that a job handler method handles **only** jobs of a certain type (jobs with a specific `name`) by passing that `name` to the `@Process()` decorator, as shown below. A consumer class can have multiple `@Process()` handlers, one for each job type (`name`). When you use named jobs, make sure there is a handler for each name.

[[CODE:47]]

> warning **Warning** When you define multiple consumers for the same queue, the `concurrency` option in `@Process({{ '{' }} concurrency: 1 {{ '}' }})` doesn't take effect. The minimum `concurrency` matches the number of consumers defined. This applies even if the `@Process()` handlers use different names to handle named jobs.

#### Request-scoped consumers

When a consumer is flagged as request-scoped (see [injection scopes](/fundamentals/injection-scopes#provider-scope)), a new instance of the class is created exclusively for each job. The instance is garbage-collected after the job completes.

[[CODE:48]]

Because request-scoped consumer classes are instantiated dynamically and scoped to a single job, you can inject the current job through the constructor using the `JOB_REF` token.

[[CODE:49]]

> info **Hint** The `JOB_REF` token is imported from the `@nestjs/bull` package.

#### Event listeners

Bull emits a set of events when queue and/or job state changes occur. The `@nestjs/bull` package exports a set of decorators that let you subscribe to a core set of standard events.

Event listeners must be declared within a <a href="application/queues#consumers">consumer</a> class (i.e., within a class decorated with the `@Processor()` decorator). To listen for an event, use one of the decorators in the table below to declare a handler for the event. For example, to listen to the event emitted when a job enters the active state in the `audio` queue, use the following construct:

[[CODE:50]]

Because Bull operates in a distributed (multi-node) environment, it defines the concept of event locality. Events may be triggered either entirely within a single process, or on shared queues from different processes. A **local** event is produced when an action or state change is triggered on a queue in the local process. In other words, when your event producers and consumers are local to a single process, all events happening on queues are local.

When a queue is shared across multiple processes, **global** events come into play. For a listener in one process to receive an event notification triggered by another process, it must register for a global event.

Event handlers are invoked whenever their corresponding event is emitted. Each handler is called with the signature shown in the table below, which provides access to information relevant to the event. One key difference between local and global event handler signatures is discussed below the table.

<table>
  <tr>
    <th>Local event listeners</th>
    <th>Global event listeners</th>
    <th>Handler method signature / When fired</th>
  </tr>
  <tr>
    <td><code>@OnQueueError()</code></td><td><code>@OnGlobalQueueError()</code></td><td><code>handler(error: Error)</code> - An error occurred. <code>error</code> contains the triggering error.</td>
  </tr>
  <tr>
    <td><code>@OnQueueWaiting()</code></td><td><code>@OnGlobalQueueWaiting()</code></td><td><code>handler(jobId: number | string)</code> - A job is waiting to be processed as soon as a worker is idle. <code>jobId</code> contains the ID of the job that has entered this state.</td>
  </tr>
  <tr>
    <td><code>@OnQueueActive()</code></td><td><code>@OnGlobalQueueActive()</code></td><td><code>handler(job: Job)</code> - Job <code>job</code> has started.</td>
  </tr>
  <tr>
    <td><code>@OnQueueStalled()</code></td><td><code>@OnGlobalQueueStalled()</code></td><td><code>handler(job: Job)</code> - Job <code>job</code> has been marked as stalled. This is useful for debugging job workers that crash or pause the event loop.</td>
  </tr>
  <tr>
    <td><code>@OnQueueProgress()</code></td><td><code>@OnGlobalQueueProgress()</code></td><td><code>handler(job: Job, progress: number)</code> - Job <code>job</code>'s progress was updated to value <code>progress</code>.</td>
  </tr>
  <tr>
    <td><code>@OnQueueCompleted()</code></td><td><code>@OnGlobalQueueCompleted()</code></td><td><code>handler(job: Job, result: any)</code> - Job <code>job</code> successfully completed with a result <code>result</code>.</td>
  </tr>
  <tr>
    <td><code>@OnQueueFailed()</code></td><td><code>@OnGlobalQueueFailed()</code></td><td><code>handler(job: Job, err: Error)</code> - Job <code>job</code> failed with reason <code>err</code>.</td>
  </tr>
  <tr>
    <td><code>@OnQueuePaused()</code></td><td><code>@OnGlobalQueuePaused()</code></td><td><code>handler()</code> - The queue has been paused.</td>
  </tr>
  <tr>
    <td><code>@OnQueueResumed()</code></td><td><code>@OnGlobalQueueResumed()</code></td><td><code>handler()</code> - The queue has been resumed.</td>
  </tr>
  <tr>
    <td><code>@OnQueueCleaned()</code></td><td><code>@OnGlobalQueueCleaned()</code></td><td><code>handler(jobs: Job[], type: string)</code> - Old jobs have been cleaned from the queue. <code>jobs</code> is an array of cleaned jobs, and <code>type</code> is the type of jobs cleaned.</td>
  </tr>
  <tr>
    <td><code>@OnQueueDrained()</code></td><td><code>@OnGlobalQueueDrained()</code></td><td><code>handler()</code> - Emitted whenever the queue has processed all the waiting jobs (even if some delayed jobs are not yet processed).</td>
  </tr>
  <tr>
    <td><code>@OnQueueRemoved()</code></td><td><code>@OnGlobalQueueRemoved()</code></td><td><code>handler(job: Job)</code> - Job <code>job</code> was successfully removed.</td>
  </tr>
</table>

When listening for global events, the method signatures can differ slightly from their local counterparts. Specifically, any handler that receives a `job` object in the local version receives a `jobId` (`number | string`) in the global version instead. To get a reference to the actual `job` object in such a case, use the `Queue#getJob()` method. This call returns a promise, so declare the handler `async` and await it. For example:

[[CODE:51]]

> info **Hint** To access the `Queue` object (to make a `getJob()` call), you must inject it. The queue must also be registered in the module where you inject it.

In addition to the specific event listener decorators, you can use the generic `@OnQueueEvent()` decorator in combination with either the `BullQueueEvents` or `BullQueueGlobalEvents` enum. See the [Events section of the Bull reference](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#events) to learn more about events.

#### Queue management

Queues have an API for management functions such as pausing and resuming, and retrieving the count of jobs in various states. See the [Queue section of the Bull reference](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) for the full API. Invoke these methods directly on the `Queue` object, as shown in the pause and resume examples below.

Pause a queue with the `pause()` method. A paused queue doesn't process new jobs until it's resumed, but jobs already being processed continue until they finish.

[[CODE:52]]

To resume a paused queue, use the `resume()` method, as follows:

[[CODE:53]]

#### Separate processes

Job handlers can also run in a separate (forked) process (see [Separate processes](https://github.com/OptimalBits/bull#separate-processes) in the Bull documentation). This has several advantages:

- The process is sandboxed, so if it crashes, the worker isn't affected.
- You can run blocking code without affecting the queue (jobs don't stall).
- Better utilization of multi-core CPUs.
- Fewer connections to Redis.

[[CODE:54]]

Because your function runs in a forked process, dependency injection (and the IoC container) isn't available. Your processor function must contain (or create) all instances of the external dependencies it needs.

[[CODE:55]]

#### Async configuration

You may want to pass `bull` options asynchronously instead of statically. In this case, use the `forRootAsync()` method, which provides several ways to handle async configuration.

One approach is to use a factory function:

[[CODE:56]]

The factory behaves like any other [asynchronous provider](/fundamentals/async-providers) (e.g., it can be `async` and can inject dependencies through `inject`).

[[CODE:57]]

Alternatively, you can use the `useClass` syntax:

[[CODE:58]]

The construction above instantiates `BullConfigService` inside `BullModule` and uses it to provide an options object by calling `createSharedConfiguration()`. This means `BullConfigService` has to implement the `SharedBullConfigurationFactory` interface, as shown below:

[[CODE:59]]

To reuse a provider imported from a different module instead of creating `BullConfigService` inside `BullModule`, use the `useExisting` syntax.

[[CODE:60]]

This construction works the same as `useClass` with one critical difference: `BullModule` looks up imported modules to reuse an existing `ConfigService` instead of instantiating a new one.

Likewise, to pass queue options asynchronously, use the `registerQueueAsync()` method. Specify the `name` attribute outside the factory function.

[[CODE:61]]

#### Example

A working example is available in the [26-queues sample](https://github.com/nestjs/nest/tree/master/sample/26-queues).
