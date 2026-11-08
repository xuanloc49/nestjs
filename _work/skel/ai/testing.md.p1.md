### Testing

Tests of code that calls models don't call a model provider: `FakeModel`, from `@nestjs/ai/testing`, is a language model that answers each call with the next of the answers you give it, and records every call it receives.

The fake model is a real `LanguageModel`, so everything around it runs as in production: the module's settings, retries, timeouts and fallback models, schemas, agent functions and their enhancers, and streaming. Only the network is left out.

#### The fake model

A `FakeModel` takes its answers in order:

[[CODE:1]]

| Answer | What the model does |
| --- | --- |
| A string | Answers with that text |
| `{{ '{' }} text {{ '}' }}` | The same, with the options below |
| `{{ '{' }} toolCalls {{ '}' }}` | Calls tools, each with its `name`, `input` (default `{{ '{' }}{{ '}' }}`) and `id` (default `call-1`, `call-2`, ...) |
| `{{ '{' }} object {{ '}' }}` | Answers with the object as JSON, which `generateObject()` reads |
| An `Error` | Fails with it, as a provider's request does |
| A function of the call | Answers with what it returns, any of the above, or a promise of it |

An answer object also takes:

| Option | What it does |
| --- | --- |
| `usage` | The tokens the answer reports: `inputTokens` and `outputTokens` (10 each by default), `cachedInputTokens`, `reasoningTokens` |
| `finishReason` | Default `'tool-calls'` with tool calls, else `'stop'` |
| `delay` | Milliseconds before it answers, or before a stream opens. The call's abort, and its timeout, cut it short |
| `chunkDelay` | Milliseconds between the chunks of a stream, which sends its text in word-sized chunks |
| `streamError` | An error the stream fails with after its text, as a connection that breaks |

Given a function instead of a list, `new FakeModel((call) => ...)` answers every call with it. `reply(...answers)` adds answers after the ones not used yet, and `fakeModel(...answers)` is `new FakeModel(answers)`. A call it has no answer left for fails: `FakeModel: no answer left for call 4. Give it more answers.`

`providerError(status, {{ '{' }} message, retryAfter {{ '}' }})` is the error an `@ai-sdk/*` provider throws for an HTTP error: an `APICallError`, retryable for 408, 409, 429 and 5xx, with a `retry-after` header when `retryAfter` (in seconds) is set.

`calls` lists what the model received, and `lastCall` is the last one:

| Property | What it is |
| --- | --- |
| `instructions` | The system prompt |
| `lastUserMessage` | The text of the last user message |
| `toolResults` | What the tools of the previous step returned, as the model reads them: `toolName`, `toolCallId` and `output`, which is the error's message for a tool that failed |
| `tools` | The names of the tools the model was offered |
| `stream` | Whether the call was streamed |
| `options` | Everything the model was sent, as the AI SDK's provider-level call options: `prompt`, `tools`, `responseFormat`, `maxOutputTokens`, `headers` and the rest |

#### Testing a service

Register `AiModule` in a testing module, with fake models under the names the service uses:

[[CODE:2]]

An answer that doesn't match the schema tests the service's handling of `AiOutputError`: give the model `'Sure! Here it is.'`, or an object with a field missing.

#### Retries, timeouts and fallback

`providerError()` and `delay` test what happens when a provider fails, or takes too long. Give the module's retries no backoff, and its attempts a short timeout, so the test doesn't wait:

[[CODE:3]]

The fast model fails twice, and the default one takes longer than the 50 milliseconds each attempt has, twice: four attempts in all, and the last one's error is the `cause`.

#### Overriding models in end-to-end tests

`overrideModels()` puts fake models in place of the application's own, by name, and keeps the rest of their definitions: their pricing, fallback models, timeouts and retries. A name the module doesn't configure fails when the testing module compiles. The models `@InjectModel()` injects are replaced too:

[[CODE:4]]

The agent functions run for real, with their schemas, guards and filters: a function's failure reaches the model as the tool's result, which the test reads in the next call's `toolResults`:

[[CODE:5]]

#### Testing agent functions

`callTool()` runs an agent function as a model's tool call does, with no model: the arguments validated by its schema, its scopes checked, then its guards, interceptors, pipes and filters, and the method. It resolves with what the model would read, and rejects with the `AiToolError` the model would read about a failure:

[[CODE:6]]

`caller` is what a call's `caller` is: a `request`, as the route's, or a `user` and `scopes`. `callTool()` initializes the testing module if it isn't yet. A method that serves MCP clients too is tested as an MCP tool with the [in-memory client](/mcp/testing) of `@nestjs/mcp/testing`, whose calls have the context type `'mcp'`.

A unit test calls the method itself, with the context it needs. A direct call skips everything around the method: the schema, the scopes and the enhancers. The refund of a [durable run](/ai/agents#durable-agent-runs) passes its call's `idempotencyKey` on to the payment provider:

[[CODE:7]]

#### Testing streams

The fake model streams its text in word-sized chunks, so a stream reads as it would from a provider. In an end-to-end test, the response of a chat route is a server-sent events body, whose events are the UI message stream's chunks:

[[CODE:8]]

`streamError` tests a stream that breaks after its first chunk, `{{ '{' }} text: 'Your order', streamError: providerError(500) {{ '}' }}`: the body then ends with an `error` chunk that says `An error occurred.`. Outside HTTP, read the stream of `streamText()` itself, as `textStream`, or its `text` promise.

#### Testing durable runs

A durable run is tested with the workflows engine running in the test, on its in-memory store, with a `ManualWorkflowClock` and its worker turned off: `WorkflowWorker.drain()` runs the instances that are due, until none is left that can run, so the test decides when the run moves on:

[[CODE:9]]

The model calls and the tool calls the run made before the approval are read back from the journal when it resumes: the fake model is called three times in all. To test a restart, boot a second application on the same store, as [Test crash recovery](/reliability/workflows#test-crash-recovery) shows for any workflow.

#### Testing embeddings

`FakeEmbeddingModel` is the fake model for [embedding calls](/ai/embeddings): a real `EmbeddingModel`, which answers each provider request with the next of the answers you give it, and records the request. It makes up no vectors: an answer has one for each value of the request.

[[CODE:10]]

The second argument says how the AI SDK splits values, as a provider's model does: here each value is a request of its own, and they are sent one at a time, so the test knows their order. It also takes `provider` and `modelId`. Without it, the model has no limit, and `embedMany()` makes one request.

| Answer | What the model does |
| --- | --- |
| `{{ '{' }} embeddings {{ '}' }}` | Answers with the vectors, one for each value of the request |
| An `Error` | Fails with it, as a provider's request does |
| A function of the call | Answers with what it returns, any of the above, or a promise of it |

An answer object also takes:

| Option | What it does |
| --- | --- |
| `usage` | The tokens the answer reports: `{{ '{' }} tokens {{ '}' }}`, 10 per value by default |
| `delay` | Milliseconds before it answers. The call's abort, and its timeout, cut it short |
| `warnings`, `providerMetadata`, `response` | What the provider adds to its vectors |

Given a function instead of a list, `new FakeEmbeddingModel((call) => ...)` answers every request with it, which suits a test that doesn't care how the values are split. `reply(...answers)` adds answers after the ones not used yet, and `fakeEmbeddingModel(...answers)` is `new FakeEmbeddingModel(answers)`. A request it has no answer left for fails: `FakeEmbeddingModel: no answer left for call 3. Give it more answers.`

`calls` lists what the model received, each with its `values` and its `options`, the AI SDK's provider-level call options such as `abortSignal`, `headers` and `providerOptions`, and `lastCall` is the last one.

`overrideEmbeddingModels()` does for embedding models what `overrideModels()` does for language models: it puts fake models in place of the application's own, by name, and keeps the rest of their definitions, their settings and pricing. A name the module doesn't configure fails when the testing module compiles. The models `@InjectEmbeddingModel()` injects are replaced too:

[[CODE:11]]

To replace language models in the same test, pass what `overrideEmbeddingModels()` returns to `overrideModels()`.
