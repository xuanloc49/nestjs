### Testing

Tools, resources and prompts are methods of providers, so their logic is tested like any provider's: call the method. What MCP adds around it, the schemas, guards, scopes and the shape of the results, is tested through a real MCP client, which `@nestjs/mcp/testing` connects to the application in memory.

#### Unit tests

A unit test calls the method with the arguments and the context it needs:

[[CODE:1]]

A direct call skips everything the module adds: the arguments aren't validated, guards and interceptors don't run, and the return value isn't turned into an MCP result. The client tests those.

#### The in-memory client

`connectMcpClient()` connects a client of the official MCP SDK to the application, through the same handler as the HTTP endpoint: the token check, the schemas, and every guard, interceptor, pipe and filter. It starts no HTTP server. The client comes from `@modelcontextprotocol/client`, a dev dependency:

[[CODE:2]]

The order API requires a token, so the tests replace its verifier with one that knows a few test tokens:

[[CODE:3]]

Like a real token, a test token needs an `expiresAt` in the future and the server's `resource`. The tests override the verifier class, and connect with a token:

[[CODE:4]]

The client is the SDK's own `Client`: `listTools()`, `callTool()`, `readResource()`, `getPrompt()` and the rest are what an assistant calls.

#### Results and errors

What goes wrong in a tool is a result the model reads, not an exception in the test. `isError` and the text say what the model was told:

[[CODE:5]]

Resources and prompts answer with JSON-RPC errors instead, which the client throws:

[[CODE:6]]

#### Tokens and scopes

Connect a client for each token a test needs. A call without the scopes its tool declares fails before the method runs, with the error that tells a real client to ask the user for more access. A client without a token can't connect at all:

[[CODE:7]]

#### Headers and protocol revisions

`headers` sends request headers with every request, which guards read from `ctx.request.headers`, in lowercase. `era: 'legacy'` connects as a client of the 2025 protocol revisions, to check that the server works for both:

[[CODE:8]]

> info **Hint** The in-memory client starts where the endpoint's route ends: middleware, and guards given in the module's `decorators`, don't run, and `ctx.request` is a plain `{{ '{' }} method, url, headers {{ '}' }}` object. Test what happens on the route over HTTP.

#### Every primitive at once

`McpRegistry` holds what the module found at startup. A test can hold every tool to rules of your own, such as a description the model can work with:

[[CODE:9]]

The registry is filled when the application initializes, which `connectMcpClient()` does; without it, call `moduleRef.init()` first.

#### Over HTTP

The route itself, the global prefix, middleware, CORS and the `Origin` check, is tested over a socket. Start the application on a free port, and send requests to it:

[[CODE:10]]

#### The stdio entry point

To test `stdio.ts` the way a client launches it, build the application, and start it with the SDK's stdio transport:

[[CODE:11]]

Closing the client closes the process's stdin, and the application shuts down, as it does when the assistant quits.
