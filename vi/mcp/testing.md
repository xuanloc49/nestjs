### Testing

Tool, resource và prompt là các method của provider, nên logic của chúng được test như mọi provider khác: gọi method. Những gì MCP thêm vào xung quanh, gồm schema, guard, scope và cấu trúc của kết quả, được test qua một MCP client thật, thứ mà `@nestjs/mcp/testing` kết nối tới ứng dụng trong bộ nhớ.

#### Unit test <a id="unit-tests"></a>

Một unit test gọi method với các argument và context mà nó cần:

```typescript
@@filename(orders/orders.tools.spec)
import type { McpContext } from '@nestjs/mcp';
import { OrdersService } from './orders.service';
import { OrdersTools } from './orders.tools';

describe('OrdersTools', () => {
  it('changes the delivery address', async () => {
    const orders = {
      changeAddress: vi
        .fn()
        .mockResolvedValue({
          id: 'ord_123',
          address: '12 Whisker Lane, Leeds',
          status: 'pending',
        }),
    };
    const tools = new OrdersTools(orders as unknown as OrdersService);
    const ctx = { authInfo: { clientId: 'support-desk' } } as McpContext;

    const result = await tools.changeAddress(
      { orderId: 'ord_123', address: '12 Whisker Lane, Leeds' },
      ctx,
    );

    expect(result).toEqual({
      orderId: 'ord_123',
      address: '12 Whisker Lane, Leeds',
      status: 'pending',
    });
    expect(orders.changeAddress).toHaveBeenCalledWith(
      'ord_123',
      '12 Whisker Lane, Leeds',
      'support-desk',
    );
  });
});
```

Một lời gọi trực tiếp bỏ qua mọi thứ mà module thêm vào: argument không được validate, guard và interceptor không chạy, và giá trị trả về không được biến thành kết quả MCP. Client sẽ test những thứ đó.

#### Client trong bộ nhớ <a id="the-in-memory-client"></a>

`connectMcpClient()` kết nối một client của MCP SDK chính thức tới ứng dụng, qua cùng handler với HTTP endpoint: việc kiểm tra token, các schema, và mọi guard, interceptor, pipe và filter. Nó không khởi động HTTP server nào. Client đến từ `@modelcontextprotocol/client`, một dev dependency:

```bash
$ npm i --save-dev @modelcontextprotocol/client
```

API đơn hàng yêu cầu token, nên các test thay verifier của nó bằng một verifier biết vài test token:

```typescript
@@filename(test/test-token.verifier)
import type { McpTokenVerifier } from '@nestjs/mcp';
import type { AuthInfo } from '@modelcontextprotocol/server';

const TOKENS: Record<
  string,
  { clientId: string; scopes: string[]; team?: string }
> = {
  'support-token': {
    clientId: 'support-desk',
    scopes: ['orders:read', 'orders:write'],
    team: 'support',
  },
  'warehouse-token': {
    clientId: 'warehouse',
    scopes: ['orders:read', 'orders:write'],
    team: 'warehouse',
  },
  'reader-token': { clientId: 'reporting', scopes: ['orders:read'] },
};

export class TestTokenVerifier implements McpTokenVerifier {
  async verifyAccessToken(token: string): Promise<AuthInfo | null> {
    const found = TOKENS[token];
    if (!found) {
      return null;
    }
    return {
      token,
      clientId: found.clientId,
      scopes: found.scopes,
      expiresAt: Math.floor(Date.now() / 1000) + 3600,
      resource: new URL('https://api.catstore.example/mcp'),
      extra: { team: found.team },
    };
  }
}
```

Giống như một token thật, một test token cần `expiresAt` trong tương lai và `resource` của server. Các test override class verifier, và kết nối với một token:

```typescript
@@filename(test/orders.e2e-spec)
import { Test, type TestingModule } from '@nestjs/testing';
import type { Client } from '@modelcontextprotocol/client';
import { connectMcpClient } from '@nestjs/mcp/testing';
import { AppModule } from '../src/app.module';
import { IdentityProviderTokenVerifier } from '../src/auth/identity-provider-token.verifier';
import { TestTokenVerifier } from './test-token.verifier';

describe('cat-store MCP server', () => {
  let moduleRef: TestingModule;
  let client: Client;

  beforeAll(async () => {
    moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(IdentityProviderTokenVerifier)
      .useClass(TestTokenVerifier)
      .compile();
    client = await connectMcpClient(moduleRef, { token: 'support-token' });
  });

  afterAll(async () => {
    await client.close();
    await moduleRef.close();
  });

  it('lists the tools', async () => {
    const { tools } = await client.listTools();
    expect(tools.map((tool) => tool.name)).toEqual(
      expect.arrayContaining(['find-order', 'change-address']),
    );
  });

  it('finds an order', async () => {
    const result = await client.callTool({
      name: 'find-order',
      arguments: { orderId: 'ord_123' },
    });
    expect(result.isError).toBeFalsy();
    expect(result.content).toEqual([
      { type: 'text', text: expect.stringContaining('ord_123') },
    ]);
  });
});
```

Client chính là `Client` của SDK: `listTools()`, `callTool()`, `readResource()`, `getPrompt()` và các method còn lại là những gì một assistant gọi.

#### Kết quả và lỗi <a id="results-and-errors"></a>

Những gì sai trong một tool là một kết quả mà model đọc, không phải một exception trong test. `isError` và đoạn text cho biết model đã được báo gì:

```typescript
@@filename(test/orders.e2e-spec)
it('tells the model about arguments the schema refuses', async () => {
  const result = await client.callTool({
    name: 'change-address',
    arguments: { orderId: 'ord_123', address: 'Leeds' },
  });
  expect(result.isError).toBe(true);
  expect(result.content).toEqual([
    { type: 'text', text: expect.stringContaining('Input validation error') },
  ]);
});

it('returns structured content, as the output schema describes it', async () => {
  const result = await client.callTool({
    name: 'change-address',
    arguments: { orderId: 'ord_123', address: '12 Whisker Lane, Leeds' },
  });
  expect(result.structuredContent).toEqual({
    orderId: 'ord_123',
    address: '12 Whisker Lane, Leeds',
    status: 'pending',
  });
});

it('answers a guard refusal with a tool error', async () => {
  const warehouse = await connectMcpClient(moduleRef, {
    token: 'warehouse-token',
  });
  try {
    const result = await warehouse.callTool({
      name: 'change-address',
      arguments: { orderId: 'ord_123', address: '12 Whisker Lane, Leeds' },
    });
    expect(result).toMatchObject({
      isError: true,
      content: [{ type: 'text', text: 'Forbidden resource' }],
    });
  } finally {
    await warehouse.close();
  }
});
```

Resource và prompt thì trả lời bằng lỗi JSON-RPC, thứ mà client sẽ throw:

```typescript
@@filename(test/orders.e2e-spec)
it('reads an order', async () => {
  const { contents } = await client.readResource({ uri: 'orders://ord_123' });
  expect(JSON.parse((contents[0] as { text: string }).text)).toMatchObject({
    id: 'ord_123',
  });
});

it('knows no order that does not exist', async () => {
  await expect(
    client.readResource({ uri: 'orders://ord_404' }),
  ).rejects.toThrow();
});

it('drafts a reply', async () => {
  const { messages } = await client.getPrompt({
    name: 'draft-reply',
    arguments: { orderId: 'ord_123', tone: 'friendly' },
  });
  expect(messages[0].content).toMatchObject({
    type: 'text',
    text: expect.stringContaining('friendly'),
  });
});
```

#### Token và scope <a id="tokens-and-scopes"></a>

Hãy kết nối một client cho mỗi token mà một test cần. Một lời gọi thiếu các scope mà tool của nó khai báo sẽ thất bại trước khi method chạy, với lỗi báo cho một client thật biết cần yêu cầu người dùng cấp thêm quyền. Một client không có token hoàn toàn không thể kết nối:

```typescript
@@filename(test/orders.e2e-spec)
import {
  InsufficientScopeError,
  SdkHttpError,
} from '@modelcontextprotocol/client';

it('asks for orders:write to change an address', async () => {
  const reader = await connectMcpClient(moduleRef, { token: 'reader-token' });
  try {
    const error = await reader
      .callTool({
        name: 'change-address',
        arguments: { orderId: 'ord_123', address: '12 Whisker Lane, Leeds' },
      })
      .catch((e: unknown) => e);
    expect(error).toBeInstanceOf(InsufficientScopeError);
    expect(error).toMatchObject({ requiredScope: 'orders:write' });
  } finally {
    await reader.close();
  }
});

it('refuses a client without a token', async () => {
  await expect(connectMcpClient(moduleRef)).rejects.toBeInstanceOf(
    SdkHttpError,
  );
});
```

#### Header và bản revision giao thức <a id="headers-and-protocol-revisions"></a>

`headers` gửi các request header kèm mọi request, thứ mà guard đọc từ `ctx.request.headers`, ở dạng chữ thường. `era: 'legacy'` kết nối như một client của các bản revision giao thức 2025, để kiểm tra rằng server hoạt động với cả hai:

```typescript
@@filename(test/orders.e2e-spec)
it('serves clients of the 2025 revisions', async () => {
  const legacy = await connectMcpClient(moduleRef, {
    token: 'support-token',
    era: 'legacy',
  });
  try {
    expect(legacy.getProtocolEra()).toBe('legacy');
    expect(
      (
        await legacy.callTool({
          name: 'find-order',
          arguments: { orderId: 'ord_123' },
        })
      ).isError,
    ).toBeFalsy();
  } finally {
    await legacy.close();
  }
});
```

> info **Gợi ý** Client trong bộ nhớ bắt đầu ở chỗ route của endpoint kết thúc: middleware, và các guard được truyền trong `decorators` của module, không chạy, và `ctx.request` là một object thuần `{{ '{' }} method, url, headers {{ '}' }}`. Hãy test những gì xảy ra trên route qua HTTP.

#### Mọi primitive cùng lúc <a id="every-primitive-at-once"></a>

`McpRegistry` chứa những gì module đã tìm thấy lúc khởi động. Một test có thể buộc mọi tool tuân theo các quy tắc của riêng bạn, chẳng hạn một mô tả mà model có thể dùng được:

```typescript
@@filename(test/orders.e2e-spec)
import { McpRegistry } from '@nestjs/mcp';

it('describes every tool for the model', () => {
  for (const tool of moduleRef.get(McpRegistry).tools) {
    expect(
      tool.options.description?.length,
      `${tool.name} needs a description`,
    ).toBeGreaterThan(20);
  }
});
```

Registry được điền khi ứng dụng khởi tạo, việc mà `connectMcpClient()` làm; nếu không dùng nó, hãy gọi `moduleRef.init()` trước.

#### Qua HTTP <a id="over-http"></a>

Bản thân route, gồm global prefix, middleware, CORS và việc kiểm tra `Origin`, được test qua một socket. Khởi động ứng dụng trên một port trống, và gửi request tới nó:

```typescript
@@filename(test/mcp-endpoint.e2e-spec)
import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AppModule } from '../src/app.module';

describe('MCP endpoint', () => {
  let app: INestApplication;
  let url: URL;

  const listTools = (headers: Record<string, string> = {}) =>
    fetch(url, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        accept: 'application/json, text/event-stream',
        ...headers,
      },
      body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' }),
    });

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();
    app = moduleRef.createNestApplication();
    await app.listen(0);
    url = new URL('/mcp', await app.getUrl());
  });

  afterAll(() => app.close());

  it('points a client without a token at the metadata', async () => {
    const response = await listTools();
    expect(response.status).toBe(401);
    expect(response.headers.get('www-authenticate')).toContain(
      'resource_metadata=',
    );
  });

  it('refuses a page from another site', async () => {
    const response = await listTools({ origin: 'https://elsewhere.example' });
    expect(response.status).toBe(403);
  });
});
```

#### Entry point stdio <a id="the-stdio-entry-point"></a>

Để test `stdio.ts` theo cách một client khởi chạy nó, hãy build ứng dụng, và khởi động nó bằng stdio transport của SDK:

```typescript
@@filename(test/stdio.e2e-spec)
import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';

it('serves the tools over stdio', async () => {
  const client = new Client({ name: 'stdio-e2e', version: '1.0.0' });
  await client.connect(
    new StdioClientTransport({
      command: process.execPath,
      args: ['dist/stdio.js'],
    }),
  );
  try {
    const { tools } = await client.listTools();
    expect(tools.map((tool) => tool.name)).toContain('find-order');
  } finally {
    await client.close();
  }
});
```

Đóng client sẽ đóng stdin của process, và ứng dụng shutdown, giống như khi assistant thoát.
