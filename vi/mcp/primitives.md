### Primitive

Một MCP server đưa ra ba primitive: **tool**, các hành động mà model gọi, **resource**, dữ liệu mà client đọc, và **prompt**, các mẫu mà người dùng chọn. Mỗi primitive là một method của một provider của bạn, kèm một decorator, và chạy qua cùng các guard, interceptor, pipe và exception filter như route của bạn.

#### Tool <a id="tools"></a>

Một tool là một method được gắn `@Tool()`. `inputSchema` mô tả các argument của nó: SDK công bố nó tới client dưới dạng JSON Schema, và validate mọi lời gọi theo nó trước khi method chạy. Các đoạn text trong `.describe()` sẽ tới được model, model đọc chúng để điền argument:

```typescript
@@filename(orders/orders.tools)
import { Injectable, NotFoundException } from '@nestjs/common';
import { Tool, type McpContext } from '@nestjs/mcp';
import * as z from 'zod';
import { OrdersService } from './orders.service';

@Injectable()
export class OrdersTools {
  constructor(private readonly orders: OrdersService) {}

  @Tool({
    name: 'find-order',
    description:
      'Find an order by its id, or the latest orders of a customer by email',
    inputSchema: z.object({
      orderId: z.string().optional().describe('The order id, such as ord_123'),
      email: z.email().optional().describe("The customer's email address"),
    }),
    annotations: { readOnlyHint: true },
  })
  async find({ orderId, email }: { orderId?: string; email?: string }) {
    const orders = orderId
      ? [await this.orders.findById(orderId)]
      : await this.orders.latestFor(email!);
    if (orders.length === 0 || !orders[0]) {
      throw new NotFoundException('No such order');
    }
    return orders;
  }

  @Tool({
    name: 'change-address',
    description:
      'Change the delivery address of an order that has not shipped yet',
    inputSchema: z.object({ orderId: z.string(), address: z.string().min(10) }),
    outputSchema: z.object({
      orderId: z.string(),
      address: z.string(),
      status: z.string(),
    }),
  })
  async changeAddress(
    { orderId, address }: { orderId: string; address: string },
    ctx: McpContext,
  ) {
    const order = await this.orders.changeAddress(
      orderId,
      address,
      ctx.authInfo?.clientId,
    );
    return { orderId: order.id, address: order.address, status: order.status };
  }
}
```

Đăng ký class làm provider, như mọi provider khác:

```typescript
@@filename(orders/orders.module)
@Module({
  providers: [OrdersService, OrdersTools],
})
export class OrdersModule {}
```

Method được gọi với các argument đã được validate và [context](/mcp/primitives#the-call-context) của lời gọi. Những gì nó trả về trở thành kết quả của tool:

| Method trả về | Client nhận được |
| --- | --- |
| Một chuỗi | Một text block |
| Một giá trị khác, có `outputSchema` | Giá trị đó dưới dạng `structuredContent` (được validate theo schema), và dưới dạng một JSON text block |
| Một giá trị khác, không có output schema | Một JSON text block |
| Một `CallToolResult` (`{{ '{' }} content, structuredContent?, isError? {{ '}' }}`) | Nguyên trạng, dùng cho ảnh, audio, resource nhúng và link |
| `undefined` | Một kết quả rỗng |

Tên mặc định là tên của method (`find`); tên tool có từ 1 tới 128 ký tự trong tập `A-Z a-z 0-9 _ - .`, và hai tool cùng tên sẽ thất bại lúc khởi động. `annotations` là gợi ý cho client, chẳng hạn `readOnlyHint: true`, cho phép client chạy tool mà không cần hỏi người dùng trước.

Để trả về thứ gì đó không phải text, chẳng hạn một bức ảnh mà model nên xem, hãy tự trả về một `CallToolResult` (từ `@modelcontextprotocol/server`):

```typescript
@@filename(orders/orders.tools)
@Tool({
  name: 'product-photo',
  description:
    'Show the photo of a product, to compare it with what the customer describes',
  inputSchema: z.object({
    sku: z.string().describe('The product SKU, such as SKU-1042'),
  }),
  annotations: { readOnlyHint: true },
})
async photo({ sku }: { sku: string }): Promise<CallToolResult> {
  const photo = await this.catalog.photo(sku);
  return {
    content: [
      {
        type: 'image',
        data: photo.toString('base64'),
        mimeType: 'image/jpeg',
      },
    ],
  };
}
```

> info **Gợi ý** Model chọn tool dựa trên tên và mô tả của nó, và điền argument dựa trên các đoạn text `.describe()`, nên hãy viết chúng cho model đọc: tool làm gì và khi nào nên dùng, mỗi argument nghĩa là gì, kèm một giá trị ví dụ. Hãy nói rõ khi một tool thay đổi dữ liệu.

#### Resource <a id="resources"></a>

Một resource là dữ liệu mà client đọc, rồi hiển thị cho người dùng hoặc đưa cho model. `@Resource()` phục vụ một URI cố định, `@ResourceTemplate()` phục vụ mọi URI khớp với một template theo [RFC 6570](https://datatracker.ietf.org/doc/html/rfc6570), với các biến của template được truyền cho method:

```typescript
@@filename(orders/orders.tools)
@Resource({
  uri: 'catalog://products',
  description: 'Every product and its stock',
  mimeType: 'application/json',
})
catalog() {
  return this.catalog.all();
}

@ResourceTemplate({
  uriTemplate: 'orders://{orderId}',
  description: 'One order',
  mimeType: 'application/json',
})
async order({ orderId }: { orderId: string }) {
  const order = await this.orders.findById(orderId);
  if (!order) {
    throw new NotFoundException();
  }
  return order;
}
```

Một chuỗi được gửi dưới dạng text với `mimeType` tương ứng, một `Uint8Array` hoặc `Buffer` được gửi dưới dạng binary blob, một `ReadResourceResult` (`{{ '{' }} contents: [...] {{ '}' }}`) được gửi nguyên trạng, và mọi thứ khác dưới dạng JSON. Một `NotFoundException` được trả lời bằng lỗi resource-not-found theo đặc tả.

Resource phù hợp với nội dung mà client load nguyên trạng vào cuộc hội thoại: danh mục sản phẩm, một đơn hàng, chính sách đổi trả. Client quyết định khi nào đọc chúng, thường là khi người dùng đính kèm một resource. Để model tự tra cứu thứ gì đó, kèm argument, hãy cho nó một tool.

#### Prompt <a id="prompts"></a>

Một prompt là một mẫu message mà người dùng chọn trong client. Các argument của nó cũng là một schema, và client hỏi người dùng từng argument:

```typescript
@@filename(orders/orders.tools)
@Prompt({
  name: 'draft-reply',
  description: 'Draft a reply to a customer about an order',
  argsSchema: z.object({
    orderId: z.string().describe('The order the customer wrote about'),
    tone: z.enum(['formal', 'friendly']).describe('How the reply sounds'),
  }),
})
async draftReply({
  orderId,
  tone,
}: {
  orderId: string;
  tone: 'formal' | 'friendly';
}) {
  const order = await this.orders.findById(orderId);
  return `Draft a ${tone} reply to the customer of order ${orderId}. The order: ${JSON.stringify(order)}`;
}
```

Một chuỗi là một user message; một mảng message, hoặc một `GetPromptResult` (`{{ '{' }} messages: [...] {{ '}' }}`), được gửi nguyên trạng.

Một prompt cũng có thể mở đầu cuộc hội thoại bằng nhiều message. Prompt này đính kèm đơn hàng dưới dạng một resource nhúng, rồi đặt câu hỏi:

```typescript
@@filename(orders/orders.tools)
@Prompt({
  name: 'review-complaint',
  description: 'Review a complaint about an order',
  argsSchema: z.object({
    orderId: z.string().describe('The order the complaint is about'),
  }),
})
async reviewComplaint({
  orderId,
}: {
  orderId: string;
}): Promise<PromptMessage[]> {
  const order = await this.orders.findById(orderId);
  return [
    {
      role: 'user',
      content: {
        type: 'resource',
        resource: {
          uri: `orders://${orderId}`,
          mimeType: 'application/json',
          text: JSON.stringify(order),
        },
      },
    },
    {
      role: 'user',
      content: {
        type: 'text',
        text: 'Is the complaint about this order justified? Answer in two sentences.',
      },
    },
  ];
}
```

`PromptMessage` là một type từ `@modelcontextprotocol/server`.

#### Chạy thử <a id="try-it"></a>

Khởi động ứng dụng, và endpoint nằm ở `http://localhost:3000/mcp`. [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) liệt kê và gọi được mọi thứ mà server đưa ra:

```bash
$ npx @modelcontextprotocol/inspector
```

Chọn **Streamable HTTP**, nhập URL, và **Connect**. Các assistant kết nối tới MCP server từ xa cũng nhận cùng URL đó.

#### Context của lời gọi <a id="the-call-context"></a>

Tham số thứ hai của mọi method MCP là một `McpContext`:

| Thuộc tính | Là gì |
| --- | --- |
| `kind`, `name`, `uri` | `'tool'`, `'resource'` hoặc `'prompt'`; tên của tool hoặc prompt, hoặc của resource; URI đang được đọc |
| `authInfo` | Access token đã được xác minh, khi có [phân quyền](/mcp/primitives#authorization): `clientId`, `scopes`, `expiresAt`, `extra` |
| `request` | Request của HTTP platform (Express, Fastify, Node adapter), với các header của nó và mọi thứ mà middleware đã đặt lên nó; với test client trong bộ nhớ, đó là một object thuần `{{ '{' }} method, url, headers {{ '}' }}`; `undefined` khi qua stdio |
| `requestInfo` | `Request` chuẩn web mà SDK đã phục vụ |
| `transport`, `era` | `'http'` hoặc `'stdio'`; `'modern'` (bản revision giao thức 2026-07-28) hoặc `'legacy'` (các bản revision 2025) |
| `signal` | Một `AbortSignal`, bị abort khi client hủy lời gọi hoặc rời đi: hãy truyền nó tiếp cho `fetch()` và database của bạn |
| `reportProgress(progress, total?, message?)` | Gửi một thông báo tiến độ, khi client có yêu cầu |
| `server` | Request context riêng của SDK, cho phần còn lại (`mcpReq.envelope`, `mcpReq.inputResponses`) |

```typescript
@Tool({
  name: 'export-orders',
  description: 'Export a month of orders as CSV',
})
async export(_input: unknown, ctx: McpContext) {
  const pages = await this.orders.pages();
  for (let page = 0; page < pages; page++) {
    ctx.signal.throwIfAborted();
    await this.orders.exportPage(page, { signal: ctx.signal });
    await ctx.reportProgress(page + 1, pages);
  }
  return 'Exported';
}
```

**Hỏi người dùng.** Một tool cần người dùng xác nhận, hoặc thiếu một giá trị, sẽ trả về `inputRequired()` từ `@modelcontextprotocol/server`: client hỏi người dùng, và gọi lại tool với câu trả lời, `acceptedContent()` đọc và validate câu trả lời đó:

```typescript
@Tool({
  name: 'cancel-order',
  description: 'Cancel an order',
  inputSchema: z.object({ orderId: z.string() }),
})
cancel({ orderId }: { orderId: string }, ctx: McpContext) {
  const Confirmation = z.object({ confirm: z.boolean() });
  const answer = acceptedContent(
    ctx.server.mcpReq.inputResponses,
    'confirm',
    Confirmation,
  );
  if (!answer) {
    return inputRequired({
      inputRequests: {
        confirm: inputRequired.elicit({
          message: `Cancel order ${orderId}?`,
          requestedSchema: Confirmation,
        }),
      },
    });
  }
  return answer.confirm ? this.orders.cancel(orderId) : 'Kept the order';
}
```

> warning **Cảnh báo** Qua HTTP, cách này hoạt động với client của bản revision 2026-07-28. Một client của bản revision 2025 được hỏi thông qua một request từ server, việc này cần một session, mà endpoint thì không giữ session nào: lời gọi kết thúc với một lỗi tool. Qua stdio, cả hai đều hoạt động.

#### Guard, interceptor, pipe và filter <a id="guards-interceptors-pipes-and-filters"></a>

Mọi lời gọi đều chạy qua các enhancer của Nest, được gắn trên class, trên method hoặc ở phạm vi global, như với một route. Type của execution context là `'mcp'`, và `McpExecutionContext` đọc lời gọi, giống như `GqlExecutionContext` làm với một GraphQL resolver. Chỉ bộ phận hỗ trợ mới được thay đổi đơn hàng:

```typescript
@@filename(orders/support-team.guard)
import {
  Injectable,
  type CanActivate,
  type ExecutionContext,
} from '@nestjs/common';
import { McpExecutionContext } from '@nestjs/mcp';

@Injectable()
export class SupportTeamGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const mcp = McpExecutionContext.create(context);
    return mcp.getAuthInfo()?.extra?.team === 'support';
  }
}
```

```typescript
@@filename(orders/orders.tools)
@Tool({ name: 'change-address', ... })
@UseGuards(SupportTeamGuard)
async changeAddress(...) {}
```

`McpExecutionContext.create(context)` có `getInput()` (các argument), `getContext()` (`McpContext`), `getKind()`, `getName()`, `getRequest()` và `getAuthInfo()`. Interceptor thấy giá trị trả về của method trước khi nó trở thành kết quả, và có thể đo thời gian, log hoặc biến đổi nó. Pipe thấy input dưới dạng `body` của lời gọi, nên một `ValidationPipe({{ '{' }} transform: true {{ '}' }})` global sẽ validate một class DTO mà bạn dùng làm type cho input, giống như với một route. Các custom parameter decorator được tạo bằng `createParamDecorator()` hoạt động sau input và context, như trên GraphQL resolver: `add(input, ctx, @CurrentUser() user)`.

Interceptor hoạt động theo cùng cách. Interceptor này log thời gian mỗi lời gọi mất, kèm loại và tên của nó:

```typescript
@@filename(orders/call-logging.interceptor)
import {
  Injectable,
  Logger,
  type CallHandler,
  type ExecutionContext,
  type NestInterceptor,
} from '@nestjs/common';
import { McpExecutionContext } from '@nestjs/mcp';
import { tap, type Observable } from 'rxjs';

@Injectable()
export class CallLoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger('MCP');

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const mcp = McpExecutionContext.create(context);
    const started = performance.now();
    return next
      .handle()
      .pipe(
        tap(() =>
          this.logger.log(
            `${mcp.getKind()} ${mcp.getName()} took ${Math.round(performance.now() - started)} ms`,
          ),
        ),
      );
  }
}
```

`@UseInterceptors(CallLoggingInterceptor)` trên class `OrdersTools` sẽ log mọi tool, resource và prompt của class đó.

> warning **Cảnh báo** Guard, interceptor và filter global (`app.useGlobalGuards()`, `APP_GUARD`) cũng chạy trên các lời gọi MCP, như trên GraphQL resolver, và trên HTTP request mang chúng. Một enhancer viết cho HTTP route có đọc `context.switchToHttp().getRequest()` nên kiểm tra `context.getType() === 'http'` trước.

#### Lỗi <a id="errors"></a>

Những gì một tool throw sẽ trở thành một kết quả với `isError: true`, thứ mà model đọc được và có thể khắc phục: message của một `HttpException` (một `BadRequestException('The address has no postcode')`), và `Internal server error` cho mọi lỗi khác, loại lỗi mà exception handler của Nest sẽ log lại và message của nó không bao giờ tới được client. Resource và prompt trả lời bằng lỗi JSON-RPC: một `NotFoundException` thành resource-not-found, một `BadRequestException` thành invalid params, một `HttpException` khác thành internal error mang message và status của nó. Một exception filter có thể trả lời thay: những gì nó trả về là kết quả, và một `ProtocolError` (từ `@modelcontextprotocol/server`) mà nó throw là lỗi JSON-RPC.

```typescript
@Catch(PaymentProviderError)
export class PaymentProviderFilter implements ExceptionFilter {
  catch(exception: PaymentProviderError, host: ArgumentsHost) {
    if (host.getType<McpContextType>() !== 'mcp') {
      throw exception;
    }
    return {
      content: [
        {
          type: 'text',
          text: 'Payments are down; try again in a few minutes.',
        },
      ],
      isError: true,
    };
  }
}
```

#### Phân quyền <a id="authorization"></a>

MCP server của API đơn hàng trả lời các câu hỏi về khách hàng, nên nó yêu cầu một người dùng đã đăng nhập. Trong MCP, server là một **resource server** OAuth 2.1: client lấy một access token từ identity provider của cửa hàng (Auth0, Keycloak, Entra ID, WorkOS, hoặc của riêng bạn), và gửi nó kèm mọi request. Server xác minh token, và không bao giờ phát hành token. Hãy cấu hình `auth`:

```typescript
@@filename(app.module)
McpModule.forRoot({
  name: 'cat-store',
  version: '1.0.0',
  auth: {
    verifier: IdentityProviderTokenVerifier,
    resource: 'https://api.catstore.example/mcp',
    authorizationServers: ['https://auth.catstore.example'],
    scopesSupported: ['orders:read'],
  },
}),
```

- `resource` là URL chuẩn của MCP server. Client yêu cầu identity provider cấp một token cho URL đó, và server chỉ chấp nhận các token được phát hành cho nó (audience của chúng), như đặc tả yêu cầu.
- `authorizationServers` là các issuer có token được chấp nhận. Module phục vụ chúng, cùng `scopesSupported`, dưới dạng [protected resource metadata](https://datatracker.ietf.org/doc/html/rfc9728) (RFC 9728) tại `/.well-known/oauth-protected-resource/mcp`, nơi client tìm hiểu cách đăng nhập.
- Một request không có token hợp lệ nhận 401 kèm một challenge `WWW-Authenticate: Bearer` trỏ tới metadata. Challenge đó là thứ khởi động việc đăng nhập của client.

**Verifier** quyết định token nào là hợp lệ. Nó là một class của bạn có `verifyAccessToken(token)`, trả về `AuthInfo` của token, hoặc `null` để từ chối nó. Nest khởi tạo nó, nên nó có thể inject những gì nó cần. Với JWT access token, `JwtVerifier` từ `@nestjs/authentication` kiểm tra chữ ký theo các khóa của identity provider, issuer, audience và thời hạn:

```typescript
@@filename(auth/identity-provider-token.verifier)
import { Injectable } from '@nestjs/common';
import { JwtVerifier } from '@nestjs/authentication';
import type { McpTokenVerifier } from '@nestjs/mcp';
import type { AuthInfo } from '@modelcontextprotocol/server';

const RESOURCE = 'https://api.catstore.example/mcp';

@Injectable()
export class IdentityProviderTokenVerifier implements McpTokenVerifier {
  private readonly jwt = new JwtVerifier({
    jwks: 'https://auth.catstore.example/.well-known/jwks.json',
    issuer: 'https://auth.catstore.example',
    audience: RESOURCE,
    type: 'at+jwt',
  });

  async verifyAccessToken(token: string): Promise<AuthInfo> {
    // A bad signature, an expired token or another audience throws a JwtError: answered with 401.
    const claims = await this.jwt.verify(token);
    return {
      token,
      clientId: String(claims.client_id ?? claims.sub),
      scopes: typeof claims.scope === 'string' ? claims.scope.split(' ') : [],
      expiresAt: claims.exp,
      resource: new URL(RESOURCE),
      extra: { team: claims.team },
    };
  }
}
```

Một lỗi có `status: 401` (`JwtError`, `UnauthorizedException`) sẽ từ chối token; mọi lỗi khác (không lấy được các khóa) được trả lời bằng 500. Opaque token đi qua introspection endpoint của identity provider thay vào đó, phía sau cùng method này.

Với opaque token, verifier hỏi introspection endpoint ([RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662)) của identity provider thay vào đó:

```typescript
@@filename(auth/introspection-token.verifier)
import { Injectable } from '@nestjs/common';
import type { McpTokenVerifier } from '@nestjs/mcp';
import type { AuthInfo } from '@modelcontextprotocol/server';

const RESOURCE = 'https://api.catstore.example/mcp';

@Injectable()
export class IntrospectionTokenVerifier implements McpTokenVerifier {
  async verifyAccessToken(token: string): Promise<AuthInfo | null> {
    const credentials = btoa(
      `${process.env.INTROSPECTION_CLIENT_ID}:${process.env.INTROSPECTION_CLIENT_SECRET}`,
    );
    const response = await fetch(
      'https://auth.catstore.example/oauth/introspect',
      {
        method: 'POST',
        headers: {
          'content-type': 'application/x-www-form-urlencoded',
          authorization: `Basic ${credentials}`,
        },
        body: new URLSearchParams({ token }),
      },
    );
    if (!response.ok) {
      // No verdict on the token: answered with 500.
      throw new Error(`Token introspection failed with ${response.status}`);
    }
    const claims = (await response.json()) as {
      active: boolean;
      aud?: string | string[];
      client_id: string;
      scope?: string;
      exp: number;
    };
    if (!claims.active || ![claims.aud].flat().includes(RESOURCE)) {
      return null; // Answered with 401.
    }
    return {
      token,
      clientId: claims.client_id,
      scopes: claims.scope ? claims.scope.split(' ') : [],
      expiresAt: claims.exp,
      resource: new URL(RESOURCE),
    };
  }
}
```

Dù bạn viết verifier nào, module kiểm tra hai điều trong những gì nó trả về: `resource` phải là URL `auth.resource`, và `expiresAt` phải được đặt và nằm trong tương lai. Một token không thỏa một trong hai sẽ bị từ chối với 401.

**Scope.** `scopes` trên một tool, một resource hoặc một prompt chỉ ra những gì token phải mang để dùng được nó. Một lời gọi thiếu chúng sẽ được trả lời, trước khi method chạy, bằng 403 với các scope còn thiếu trong challenge, và client yêu cầu người dùng cấp chúng (step-up authorization). `requiredScopes` trong `auth` yêu cầu các scope trên mọi request:

```typescript
@Tool({ name: 'change-address', ..., scopes: ['orders:write'] })
```

Khai báo `scopes` mà không có `auth` sẽ thất bại lúc khởi động, vì không có gì kiểm tra chúng. Token là `ctx.authInfo` trong các method, và `McpExecutionContext.create(context).getAuthInfo()` trong guard, cho những quyết định mà scope không diễn đạt được.

**Với `@nestjs/authentication` và `@nestjs/authorization`.** Các global guard của chúng chạy trên mọi lời gọi MCP. Guard xác thực xác thực lời gọi bằng các provider của bạn, từ HTTP request mà lời gọi tới trong đó: một `JwtBearerProvider` chấp nhận token của identity provider sẽ chấp nhận token của MCP client. Khi đó `@CurrentUser()` và `AuthenticationContext` hoạt động trong tool, và các policy `@Can()` quyết định từng lời gọi:

```typescript
@@filename(orders/orders.tools)
@Tool({
  name: 'refund',
  description: 'Refund an order',
  inputSchema: z.object({ orderId: z.string() }),
})
@Can(OrderPolicy, 'refund')
refund(
  { orderId }: { orderId: string },
  ctx: McpContext,
  @CurrentUser() agent: Agent,
) {
  return this.orders.refund(orderId, agent);
}
```

Hãy miễn route của endpoint khỏi guard xác thực bằng `decorators: [Public()]`, và để `auth` trả lời các request chưa xác thực của nó: challenge riêng của guard không trỏ MCP client tới metadata. Một lần từ chối trên một lời gọi là một lỗi tool, `Unauthorized` hoặc `Forbidden`, và một tool không khai báo `@Can()` nào sẽ bị từ chối, giống như một route. Qua stdio không có request nào, nên một lời gọi là ẩn danh trừ khi một provider của riêng bạn xác thực nó từ môi trường.

> info **Gợi ý** Việc này cần `@nestjs/authentication` 0.1.3 và `@nestjs/authorization` 0.1.1 trở lên, những phiên bản đầu tiên biết tới lời gọi MCP (context type `'mcp'`). Với các phiên bản cũ hơn, global guard không tìm thấy credential nào trên một lời gọi: hãy đánh dấu các provider chứa tool của bạn là `@Public()`.

#### Decorator <a id="decorators"></a>

| Decorator | Tùy chọn | Method được gọi với |
| --- | --- | --- |
| `@Tool()` | `name`, `title`, `description`, `inputSchema`, `outputSchema`, `annotations`, `icons`, `_meta`, `scopes` | Các argument đã được validate, context |
| `@Resource()` | `uri`, `name`, `title`, `description`, `mimeType`, `size`, `annotations`, `icons`, `_meta`, `cacheHint`, `scopes` | `{{ '{' }}{{ '}' }}`, context (`ctx.uri`) |
| `@ResourceTemplate()` | `uriTemplate`, và các tùy chọn tương tự | Các biến của template, context |
| `@Prompt()` | `name`, `title`, `description`, `argsSchema`, `icons`, `_meta`, `scopes` | Các argument đã được validate, context |
