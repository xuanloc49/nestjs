### Migration

An MCP server built with the community package `@rekog/mcp-nest` moves to `@nestjs/mcp` with mostly mechanical changes: the decorators keep their names, and tools, resources and prompts stay methods of your classes. This page maps both of its APIs, the `McpModule.forRoot()` one of its 1.x releases and the `McpStrategy` one of 2.x, to `@nestjs/mcp`.

#### Packages

`@nestjs/mcp` is built on version 2 of the MCP TypeScript SDK, `@modelcontextprotocol/server`. Replace the packages:

[[CODE:1]]

From 2.x, also uninstall `@modelcontextprotocol/core` and `@modelcontextprotocol/node`, `@rekog/mcp-nest-auth` if you used its authorization server, and `@nestjs/microservices` if nothing else in the application uses it. Types you imported from `@modelcontextprotocol/sdk`, such as `CallToolResult`, come from `@modelcontextprotocol/server`.

#### The module

From 1.x, `McpModule.forRoot()` stays, with fewer options:

[[CODE:2]]

| `@rekog/mcp-nest` 1.x | `@nestjs/mcp` |
| --- | --- |
| `name`, `version` | The same |
| `transport` | Streamable HTTP is served unless `path: false`; stdio is served by `McpStdioServer` (see [Transports](/mcp/transports#over-stdio)) |
| `mcpEndpoint`, `apiPrefix` | `path`, under the application's global prefix |
| `guards` | `decorators: [UseGuards(...)]` |
| `streamableHttp` | Nothing to set: every request is served on its own, and `http.responseMode` shapes the answers to 2026-07-28 requests |
| `forRootAsync()` | `forRootAsync()`, with `path`, `decorators` and `imports` at its top level |
| `forFeature()` | One MCP server per application |

From 2.x, the strategy and its bootstrap code go away. `McpModule.forRoot()` takes the strategy's `name` and `version`, and the endpoint is a route of the application, served by `app.listen()`:

[[CODE:3]]

`@McpController()` classes become ordinary `@Injectable()` providers, listed in a module's `providers` instead of its `controllers`, and the `MCP_STRATEGY` provider goes. A stdio server that `NestFactory.createMicroservice()` started is served from an application context with `McpStdioServer` instead, as [Transports](/mcp/transports#over-stdio) shows.

#### Tools, resources and prompts

The decorators keep their names and most of their options. The method's arguments change:

[[CODE:4]]

| `@rekog/mcp-nest` | `@nestjs/mcp` |
| --- | --- |
| `parameters` | `inputSchema` on a tool, `argsSchema` on a prompt |
| `outputSchema`, `annotations` | The same |
| `(args, context, request)` in 1.x, `@Payload()` and `@Ctx()` in 2.x | `(input, ctx)`: the request is `ctx.request`, the verified token `ctx.authInfo` |
| `context.reportProgress({{ '{' }} progress, total {{ '}' }})` | `ctx.reportProgress(progress, total)` |
| `context.mcpServer.server.elicitInput()` | Return `inputRequired()`: see [asking the user](/mcp/primitives#the-call-context) |
| A resource's `({{ '{' }} uri {{ '}' }})` | `ctx.uri`. A resource template's method receives its variables as the input |
| `{{ '{' }} content {{ '}' }}`, `{{ '{' }} contents {{ '}' }}` and `{{ '{' }} messages {{ '}' }}` results | Returned as they are, or return the value itself and let the module build the result |
| `@Injectable({{ '{' }} scope: Scope.REQUEST {{ '}' }})` | A singleton provider: read what belongs to the call from `ctx` |
| `McpRegistryService.registerTool()`, `strategy.registerTool()` | Not supported: declare tools with decorators |

A resource template, for example:

[[CODE:5]]

A request-scoped provider fails at startup with `@nestjs/mcp`: every request is served by the same singleton instances, and what differs between calls, the request, the token and the client, is in `ctx`.

#### Guards and errors

Guards, interceptors, pipes and filters keep working, with `McpExecutionContext.create(context)` in place of `context.switchToRpc().getContext<McpContext>()`. The context's type is `'mcp'`, not `'rpc'`.

A tool's errors still reach the model as tool results. An `HttpException` carries its message to the client, where 2.x needed an `RpcException`; any other error is answered with `Internal server error`.

[[CODE:6]]

#### Authorization

`@nestjs/mcp` is a resource server, as the MCP spec asks of a server: the tokens come from an identity provider, and the module verifies them (see [Authorization](/mcp/primitives#authorization)).

| `@rekog/mcp-nest` | `@nestjs/mcp` |
| --- | --- |
| `McpAuthModule`, the built-in authorization server | An identity provider (Auth0, Keycloak, Entra ID, WorkOS, your own) that issues the tokens, and `auth` pointing at it |
| `McpAuthJwtGuard` in `guards` | `auth.verifier` |
| `@ToolScopes(['orders:write'])` | `scopes: ['orders:write']` on the decorator. Scoped tools stay listed to every client |
| `@ToolRoles(['admin'])` | A guard, or a `@Can()` policy with `@nestjs/authorization` |
| `@PublicTool()`, `allowUnauthenticatedAccess` | Not supported: with `auth`, every request needs a token |
| `ctx.getUser()` in 2.x | `ctx.authInfo`, or `@CurrentUser()` with `@nestjs/authentication` |

#### What's not there

- **The HTTP+SSE transport** of the 2024-11-05 protocol revision isn't served. Clients connect over Streamable HTTP, the transport current clients use.
- **Sessions** aren't kept: every HTTP request is served on its own, which is what lets the server run on many instances. A 2025 client can't be asked for input mid-call over HTTP; the call ends with a tool error.
- **Registering tools at runtime**, **several MCP servers in one application** and **request-scoped providers** aren't supported in this version.
