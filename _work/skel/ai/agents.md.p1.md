### Agents

An agent is a model that calls tools in a loop: it reads what each tool returns, then calls more tools or answers, until it has answered or reached its limit of model calls.

Every `AiService` call with [tools](/ai/tools), your agent functions, runs that loop, inside your process: there is nothing else to deploy. This page covers what comes with it: the loop and its limits, conversations, answers streamed to the browser as they are written, and durable runs that survive restarts and wait for a person's approval.

#### The agent loop

A call with tools makes a model call, runs the tools the model asked for, and makes the next model call with their results, until the model answers without asking for a tool. Each model call is a **step**, and the result lists them:

[[CODE:1]]

Each step has its `text`, `toolCalls`, `toolResults` (what each tool returned as `output`, or the `error` the model was told), `finishReason`, `usage`, `cost`, the `model` that answered and the `attempts` it took.

`maxSteps` caps the model calls of one call, 10 by default (`defaults.maxSteps` changes it for every call). When it runs out while the model still asks for tools, `generateText()` resolves with what it has, and its `finishReason` is `'tool-calls'`; `generateObject()` rejects with `AiOutputError`, since it has no object to give. Tools run inside their step: their time doesn't count against the model's `timeout`, and a step whose tools have started is never retried, so no tool runs twice.

`toolChoice` is passed to the model as the AI SDK's: `'auto'`, the default, lets the model choose, and `'none'` offers the tools but lets it call none. `'required'` and `{{ '{' }} type: 'tool', toolName {{ '}' }}` make it call one, which not every model accepts.

An `abortSignal` cancels a call: the model call in flight, the wait before a retry, and the agent functions running, through their context's `signal`. A job that must not take more than two minutes passes `abortSignal: AbortSignal.timeout(120_000)`, and the call rejects with the signal's reason, without a retry or a fallback.

#### Conversations

`messages` takes a whole conversation, as the AI SDK's `ModelMessage` objects, in place of `prompt`. A call's `responseMessages` are the messages it added: the model's answers and tool calls, and the tools' results. Append them to the conversation, and send it with the customer's next message:

[[CODE:2]]

The `instructions` aren't part of the conversation: each call sends its own. A chat in the browser keeps the conversation itself, and sends it with each message: see [Streaming to the browser](/ai/agents#streaming-to-the-browser).

#### Streaming to the browser

The assistant answers as it thinks, so the browser shows the answer as it's written. `streamText()` starts the call and returns its stream at once, and `pipeUIMessageStreamToResponse()` sends it, as server-sent events in the AI SDK's UI message stream protocol, on the response that `@Res()` injects:

[[CODE:3]]

The route works the same on Fastify and on the Node adapter: `pipeUIMessageStreamToResponse()` takes the platform's response, a `FastifyReply` on Fastify, whose headers set before the stream starts, such as CORS headers, are kept. `convertToModelMessages()`, from `ai`, turns the `UIMessage` objects the browser posts into the model messages the call takes.

In the browser, `useChat()` from `@ai-sdk/react`, or the AI SDK's packages for Vue, Svelte and Angular, posts the conversation to the route and builds the answer as it arrives:

[[CODE:4]]

Each message's `parts` hold its text (`type: 'text'`) and the tool calls the model made, as `tool-find-order` parts with their `state`, `input` and `output`. The answer of every model call of the call streams as one message, its tool calls and their results included.

- **Errors.** A call that fails before its first chunk rejects, with nothing sent, so the route's exception filters answer it. Until then, the stream is retried, and falls back to another model, as any call. A failure after it ends the stream with an error chunk that says `An error occurred.`, so that no detail of the server leaks: the `errorText` option says more.
- **Keep-alive.** When 15 seconds pass without a chunk, as while a tool works, a comment line (`: keep-alive`) goes out, so that proxies and load balancers don't close the connection as idle. `useChat()` skips it. The `keepAlive` option sets the interval, or `false` turns it off.
- **A browser that goes away.** When the browser closes the connection, the model call is aborted, and so is the `signal` of the agent functions running.
- **Headers.** The response is `text/event-stream` with `x-accel-buffering: no`, which tells nginx not to buffer it. `status` and `headers` add your own.

[[CODE:5]]

An agent function's `ctx.reportProgress()` reaches the browser as a transient `data-tool-progress` chunk, which `useChat()` hands to its `onData` callback without adding it to the message:

[[CODE:6]]

[[CODE:7]]

The stream has other readers. `pipeTextStreamToResponse(response)` sends the text alone, as `text/plain`; `textStream` iterates it; `toUIMessageStream()` is the UI message stream as a `ReadableStream`, and `toUIMessageStreamResponse()` as a web-standard `Response`. `text`, `usage`, `steps`, `finishReason` and `responseMessages` are promises that settle when the call ends, and `result` has all of them; they reject with the call's error. The call runs once, whatever reads it, and each reader gets the whole stream from its start. `abort()` cancels it. Mistakes in the options, such as an agent function that doesn't exist, throw from `streamText()` at once.

[[CODE:8]]

#### Durable agent runs

A refund request takes a person: the agent looks the order up and asks to refund it, and someone in the support team approves, maybe the next morning, maybe after a deploy. `@nestjs/ai/workflows` runs the agent loop on [`@nestjs/workflows`](/reliability/workflows), with each model call as a step and each tool call as another. A run that a restart interrupts resumes where it was, and what its journal holds is read back, not done again. Install the package:

[[CODE:9]]

Import `AiWorkflowsModule` in the module of your workflows. The application imports `WorkflowsModule`, with a store in your database as [Durable workflows](/reliability/workflows#keep-workflows-in-your-database) describes, and `AiModule`, as usual:

[[CODE:10]]

Run the agent from a workflow of your own, with `AiAgents`:

[[CODE:11]]

Start it as any workflow, with an id from the ticket, which makes starting it again for the same ticket return the run that exists:

[[CODE:12]]

A call of an agent function named in `approve` waits for a person before it runs, for as long as it takes; `approvalTimeout` bounds the wait. `pendingApprovals(runId)` lists the calls waiting, each with its `key`, `toolName` and `input`, and `approve(key)` or `reject(key, {{ '{' }} reason {{ '}' }})` answers one, from wherever the support team works:

[[CODE:13]]

A rejected call doesn't run: the model is told it was rejected, and why, and answers the customer. A call nobody answered within `approvalTimeout` doesn't run either. The first answer for a call counts, and `approve()` and `reject()` take `by`, who answered, which is kept with the answer. While a run waits, its workflow instance is suspended, and holds no process.

What a run needs to resume is stored with it, so its options are data: models by name, agent functions by name or by provider class, which the run stores as names, and the `caller` as the `user` and `scopes` the agent functions need, since there is no request to read after a restart. The agent functions get them as `ctx.user` and `ctx.scopes`; with `@nestjs/authentication`, their providers are [`@Public()`](/ai/tools#with-nestjsauthentication-and-nestjsauthorization), as for any call without a request. A run's model calls use their model's and the module's `timeout`, `retry` and generation settings, and its `maxSteps` and `budget` fall back to the module's `defaults`, as a call's do.

An agent function call runs at least once: a process that dies while it runs makes it again after the restart, with the same `ctx.idempotencyKey`. A function that changes something passes the key on, so the change happens once:

[[CODE:14]]

An agent function's failure is a result the model reads, as in any call, not the failure of its step. A model call keeps its retries, timeouts and fallback models; one that still fails is retried as a step of the workflow, which waits durably between attempts (three attempts by default). After `stepsPerInstance` model calls (10), a run goes on in a child workflow, so that no instance's journal grows long: each resume replays it in full, and it is capped. `maxSteps` (25) caps the model calls of a run.

The run resolves with what `generateText()` resolves with, `text`, `steps`, `toolResults` and the rest, as JSON: it is the workflow's output, which `WorkflowClient`'s `getStatus(runId)` reads too.

The options of `run()`:

| Option | Default | Description |
| --- | --- | --- |
| `model`, `fallback` | `'default'`, the model's | Models, by name |
| `instructions`, `prompt`, `messages` | | As for a call |
| `tools` | | Agent function names and provider classes, stored as names |
| `approve` | `[]` | The agent functions, among `tools`, whose calls wait for a person's approval |
| `approvalTimeout` | until answered | How long a call waits for its approval |
| `caller` | | The `user` and `scopes` the agent functions run as |
| `maxSteps` | `defaults.maxSteps`, else `25` | The model calls of the run |
| `stepsPerInstance` | `10` | The model calls of one workflow instance, before the run goes on in a child |
| `budget` | `defaults.budget` | `maxTokens` and `maxCost`, over the run |
| `label`, `toolChoice`, `maxOutputTokens`, `temperature`, `providerOptions` | | As for a call |
