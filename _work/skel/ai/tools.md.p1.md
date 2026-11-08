### Tools

An agent function is a method of one of your providers that the model may call, with arguments it fills in, to look something up or to change something: the model reads what the method returns, then calls more functions or answers. You write an agent function; the model is offered it as a tool.

The store's assistant answers questions about orders, so its model must look orders up. In `@nestjs/ai`, the method that does it is decorated with `@AgentFunction()`, and it runs through the guards, interceptors, pipes and exception filters of its class and method, as the user the model acts for. It needs nothing beyond `@nestjs/ai`.

#### Define an agent function

`inputSchema` describes the function's arguments: the model is sent its JSON Schema, and every call is validated against it before the method runs. The model picks a function by its name and description, and fills the arguments in from their `.describe()` texts:

[[CODE:1]]

`@AgentFunction()` takes four options, all of them optional:

- **`name`**: what calls list the function by, and what the model calls it by. It defaults to the method's name, and must be 1 to 64 characters out of `A-Z a-z 0-9 _ -`, which is what model providers accept as a tool name.
- **`description`**: what the function does, for the model.
- **`inputSchema`**: its arguments, as an object schema. Without one, the function takes none.
- **`scopes`**: the scopes the caller must hold: see [Who the agent acts for](/ai/tools#who-the-agent-acts-for).

Register the class as a provider, as any other:

[[CODE:2]]

`AiModule` finds the agent functions of every module of the application; its own `include` option limits the search to the modules it lists.

#### Give a call its tools

A call lists, in `tools`, the agent functions its model may use, by name or by provider class (every agent function of the class), and says who it acts for with `caller`:

[[CODE:3]]

The model is offered the functions the call lists, as tools, and no other. When it calls one, the arguments are validated against the function's schema, the method runs, and what it returns is sent back to the model, which calls more functions or answers. Each of the model's answers is one model call, and `maxSteps`, 10 by default, caps how many a call makes: see [The agent loop](/ai/agents#the-agent-loop). Arguments the schema refuses never reach the method, nor its guards: the model is told what's wrong, and can try again.

Mistakes fail early:

- A call that lists an agent function that doesn't exist, or a class without any, is refused before anything is sent: `There is no agent function named "find-orders". Agent functions: find-order, change-address.`
- A name model providers refuse fails at startup, naming the method. So do two agent functions with one name, and an agent function on a request-scoped provider: pass what a call needs through `caller` instead.
- So does a schema that isn't a Standard Schema with JSON Schema, or doesn't describe an object.

The model reads what the method returns as JSON: a `Date` as its ISO string, and `undefined` as `null`. A method that also serves MCP clients may return an MCP `CallToolResult`: the model reads its `structuredContent`, or else its text blocks, joined. Images, audio and other blocks don't reach the model, and a warning in the log says so. A result with `isError: true` is a tool error, with its text.

#### The call context

An agent function is called with its arguments and an `AgentFunctionContext`, from `@nestjs/ai`:

| Property | What it is |
| --- | --- |
| `name` | The agent function's name |
| `request` | The HTTP request the call runs in, `caller.request`, with its headers and the `user` your authentication set on it |
| `user`, `scopes` | `caller.user` and `caller.scopes`: who the call acts for where there is no request, as in a queue job |
| `toolCallId` | The model's id for this tool call, to tie the function's logs to the conversation |
| `idempotencyKey` | In a [durable run](/ai/agents#durable-agent-runs), the same for every attempt of this call; `undefined` elsewhere |
| `messages` | The conversation the model had read when it called the function, without the system prompt |
| `signal` | An `AbortSignal`, aborted when the call is: pass it on to `fetch()` and your database |
| `reportProgress(progress, total?, message?)` | In a [streamed answer](/ai/agents#streaming-to-the-browser), sends the browser the call's progress; elsewhere, does nothing |

`change-address` lets the assistant change the delivery address of an order. It passes the call's `signal` on to the database, and a guard checks that the order is the customer's:

[[CODE:4]]

#### Who the agent acts for

`caller` says who a call acts for, and the agent functions, their guards and the authentication packages read it from the context:

- **`request`**: in a route, the HTTP request of Express, Fastify or the Node adapter, as `@Req()` injects it. The functions see it as `ctx.request`, with the `user` your authentication set on it, as a route's guards do.
- **`user`** and **`scopes`**: where there is no request, as in a queue job or a scheduled task, who the call acts for and what they may do. They are `ctx.user` and `ctx.scopes`.

An agent function whose `@AgentFunction()` declares `scopes` runs only for a caller that holds them in `caller.scopes`: otherwise, the call is refused before any guard runs, and the model reads `Forbidden: this tool needs the scope(s) orders:refund`. A nightly job reviews the refund requests nobody answered, as the store's refund bot:

[[CODE:5]]

Nothing a caller lacks is made up: a call without `caller` runs its agent functions with no request, no user and no scopes.

#### Guards, interceptors, pipes and filters

Every agent function call runs through Nest's enhancers, bound on the class, on the method or globally, as for a route. Its execution context's type is `'ai'`, and `AiExecutionContext` reads the call. A customer may change their own orders only:

[[CODE:6]]

`AiExecutionContext.create(context)` has `getType()`, `getInput()` (the arguments, also `switchToRpc().getData()`), `getContext()` (the `AgentFunctionContext`), `getName()` and `getRequest()`. An agent function call goes through these, in order:

1. The arguments are validated against the function's schema.
2. The function's `scopes` are checked against the caller's.
3. The guards run, global ones first, then the interceptors and the pipes, as around a route handler.
4. The method runs, with the arguments and the context.

Pipes see the arguments as the call's `body`, so a `ValidationPipe` validates a DTO class you type them with, after the function's schema has, and they see the context as a `custom` parameter, which `ValidationPipe` skips. Custom parameter decorators made with `createParamDecorator()` work after the arguments and the context: `changeAddress(input, ctx, @CurrentUser() user)`.

Interceptors see the method's return value before the model does. This one logs each call, with the id of the model's tool call:

[[CODE:7]]

What an agent function throws reaches the model as an error it can recover from, and tell the user about: a guard's refusal as `Forbidden resource`, the message of an `HttpException` (a `BadRequestException('The address has no postcode')`), and `Internal server error` for any other error, which Nest's exception handler logs and whose message never reaches the model. An exception filter can answer instead: what it returns is the function's result.

> warning **Warning** Global guards, interceptors and filters (`APP_GUARD`, `app.useGlobalGuards()`) run on agent function calls too, as they do on MCP calls. An enhancer written for HTTP routes that reads `context.switchToHttp()` should check `context.getType() === 'http'` first.

#### Serving MCP clients too

The order API already has an [MCP server](/mcp/overview), whose clients, the support team's assistants, call `find-order` too. One method serves both consumers: it carries `@Tool()` from [`@nestjs/mcp`](/mcp/primitives#tools), for MCP clients, and `@AgentFunction()`, for the application's agents, each with options of its own. Neither decorator reads the other's: a method with `@Tool()` alone is no agent function, and one with `@AgentFunction()` alone is no MCP tool. A schema constant saves writing the schema twice:

[[CODE:8]]

Each consumer finds its own decorator: `McpModule` serves the `@Tool()` methods of the modules its `include` lists, and `AiModule` finds the `@AgentFunction()` methods:

[[CODE:9]]

MCP clients get `find-order`, and the assistant may call `find-order` and `change-address`, which has no `@Tool()`.

The two kinds of call have context types of their own: `'mcp'` for an MCP client's call, which `McpExecutionContext` reads, and `'ai'` for an agent's, which `AiExecutionContext` reads. The guards, interceptors and filters of a method that serves both see both, and tell them apart with `context.getType()`. `find-order` shows a customer only their own orders through the assistant, and the support team's MCP clients every order:

[[CODE:10]]

The method's second argument is an `McpContext` for an MCP client's call, and an `AgentFunctionContext` for an agent's. Custom parameter decorators, made with `createParamDecorator()`, run for both kinds of call as well, and the `ExecutionContext` they receive has the type of the call they run for.

#### With `@nestjs/authentication` and `@nestjs/authorization`

[`@nestjs/authentication`](/security/authentication) and [`@nestjs/authorization`](/security/authorization) read agent function calls as they read MCP clients' calls: from their arguments, with the request the call runs in. In a route, the global authentication guard authenticates each call from the request it runs in (once: the route's result is reused), `@CurrentUser()` and `AuthenticationContext` work in agent functions, and `@Can()` policies decide each call. An agent function that declares no `@Can()` is denied, as a route is, and the model reads `Forbidden`:

[[CODE:11]]

In a job, there is no request. `@Can()` finds the caller's `user` on the context, and the authentication guard treats the call as anonymous, as it does over stdio, so mark the providers of the agent functions that jobs call `@Public()`:

[[CODE:12]]

A refusal is Nest's `UnauthorizedException` or `ForbiddenException`, as on a route, and the model reads it as the tool's error: `Unauthorized`, or `Forbidden`.

> info **Hint** This needs `@nestjs/authentication` 0.1.4 and `@nestjs/authorization` 0.1.2 or later, the first versions that know the `'ai'` context type.

#### Tools in your own AI SDK calls

`AiTools` turns agent functions into the AI SDK's tools: `select()` takes the same list a call's `tools` does, and the `caller` their calls run as, for code that calls the AI SDK itself. The functions keep their schemas, scopes and enhancers:

[[CODE:13]]

`stopWhen` and `stepCountIs()` are the AI SDK's: it runs its own loop here, as it does any of its calls.
