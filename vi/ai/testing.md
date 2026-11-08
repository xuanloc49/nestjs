### Testing

Các test cho code gọi model không gọi tới model provider: `FakeModel`, từ `@nestjs/ai/testing`, là một language model trả lời mỗi lời gọi bằng câu trả lời tiếp theo trong danh sách bạn đưa cho nó, và ghi lại mọi lời gọi mà nó nhận được.

Fake model là một `LanguageModel` thật, nên mọi thứ xung quanh nó chạy như trong production: các thiết lập của module, retry, timeout và fallback model, schema, agent function cùng các enhancer của chúng, và streaming. Chỉ có network là bị loại ra.

#### Fake model <a id="the-fake-model"></a>

Một `FakeModel` nhận các câu trả lời của nó theo thứ tự:

```typescript
import { FakeModel, providerError } from '@nestjs/ai/testing';

const model = new FakeModel([
  // 1. Text
  'Your order has shipped.',
  // 2. A tool call, and the answer after it, a function of the call
  { toolCalls: [{ name: 'find-order', input: { orderId: 'ord_123' } }] },
  (call) => `The order is ${JSON.stringify(call.toolResults[0].output)}`,
  // 3. An object, for generateObject()
  { object: { category: 'shipping', orderId: 'ord_123', urgent: false } },
  // 4. A provider's error: overloaded
  providerError(529),
]);
```

| Câu trả lời | Model làm gì |
| --- | --- |
| Một chuỗi | Trả lời bằng đoạn text đó |
| `{{ '{' }} text {{ '}' }}` | Tương tự, với các tùy chọn bên dưới |
| `{{ '{' }} toolCalls {{ '}' }}` | Gọi các tool, mỗi tool với `name`, `input` (mặc định `{{ '{' }}{{ '}' }}`) và `id` (mặc định `call-1`, `call-2`, ...) |
| `{{ '{' }} object {{ '}' }}` | Trả lời bằng object dưới dạng JSON, thứ mà `generateObject()` đọc |
| Một `Error` | Thất bại với lỗi đó, như một request tới provider |
| Một hàm nhận lời gọi | Trả lời bằng những gì nó trả về, bất kỳ loại nào ở trên, hoặc một promise của nó |

Một answer object cũng nhận:

| Tùy chọn | Làm gì |
| --- | --- |
| `usage` | Số token mà câu trả lời báo cáo: `inputTokens` và `outputTokens` (mặc định mỗi loại 10), `cachedInputTokens`, `reasoningTokens` |
| `finishReason` | Mặc định `'tool-calls'` khi có lời gọi tool, nếu không thì `'stop'` |
| `delay` | Số mili giây trước khi nó trả lời, hoặc trước khi một stream mở. Việc abort lời gọi, và timeout của nó, sẽ cắt ngang khoảng này |
| `chunkDelay` | Số mili giây giữa các chunk của một stream, stream này gửi đoạn text theo từng chunk cỡ một từ |
| `streamError` | Một lỗi mà stream thất bại với nó sau đoạn text, giống như một kết nối bị đứt |

Nếu được đưa một hàm thay vì một danh sách, `new FakeModel((call) => ...)` trả lời mọi lời gọi bằng hàm đó. `reply(...answers)` thêm câu trả lời vào sau những câu chưa dùng, và `fakeModel(...answers)` là `new FakeModel(answers)`. Một lời gọi mà nó không còn câu trả lời nào sẽ thất bại: `FakeModel: no answer left for call 4. Give it more answers.`

`providerError(status, {{ '{' }} message, retryAfter {{ '}' }})` là lỗi mà một provider `@ai-sdk/*` throw cho một lỗi HTTP: một `APICallError`, có thể retry với 408, 409, 429 và 5xx, kèm header `retry-after` khi đặt `retryAfter` (tính bằng giây).

`calls` liệt kê những gì model đã nhận, và `lastCall` là lời gọi cuối cùng:

| Thuộc tính | Là gì |
| --- | --- |
| `instructions` | System prompt |
| `lastUserMessage` | Đoạn text của user message cuối cùng |
| `toolResults` | Những gì các tool của step trước đã trả về, theo cách model đọc chúng: `toolName`, `toolCallId` và `output`, là message của lỗi với một tool đã thất bại |
| `tools` | Tên các tool mà model được cung cấp |
| `stream` | Lời gọi có được stream không |
| `options` | Mọi thứ mà model được gửi, dưới dạng các call option ở cấp provider của AI SDK: `prompt`, `tools`, `responseFormat`, `maxOutputTokens`, `headers` và các tùy chọn còn lại |

#### Test một service <a id="testing-a-service"></a>

Đăng ký `AiModule` trong một testing module, với các fake model dưới những tên mà service dùng:

```typescript
@@filename(support/triage.service.spec)
import { Test } from '@nestjs/testing';
import { AiModule } from '@nestjs/ai';
import { FakeModel } from '@nestjs/ai/testing';
import { TriageService } from './triage.service';

describe('TriageService', () => {
  it('sorts an email', async () => {
    const fast = new FakeModel([
      { object: { category: 'shipping', orderId: 'ord_123', urgent: true } },
    ]);
    const moduleRef = await Test.createTestingModule({
      imports: [
        AiModule.forRoot({ models: { default: new FakeModel(), fast } }),
      ],
      providers: [TriageService],
    }).compile();

    const triage = await moduleRef
      .get(TriageService)
      .triage('Where is ord_123? It was due on Monday.');

    expect(triage).toEqual({
      category: 'shipping',
      orderId: 'ord_123',
      urgent: true,
    });
    expect(fast.lastCall?.instructions).toContain('support email');
    expect(fast.lastCall?.lastUserMessage).toBe(
      'Where is ord_123? It was due on Monday.',
    );
    expect(fast.lastCall?.options.responseFormat).toMatchObject({
      type: 'json',
    });
  });
});
```

Một câu trả lời không khớp với schema sẽ test cách service xử lý `AiOutputError`: hãy đưa cho model `'Sure! Here it is.'`, hoặc một object thiếu một field.

#### Retry, timeout và fallback <a id="retries-timeouts-and-fallback"></a>

`providerError()` và `delay` test điều gì xảy ra khi một provider thất bại, hoặc mất quá lâu. Hãy để các lần retry của module không có backoff, và cho các lần thử một timeout ngắn, để test không phải chờ:

```typescript
@@filename(support/replies.service.spec)
import { Test } from '@nestjs/testing';
import { AiModelError, AiModule } from '@nestjs/ai';
import { FakeModel, providerError } from '@nestjs/ai/testing';
import { ResilienceTimeoutError } from '@nestjs/resilience';
import { RepliesService } from './replies.service';

async function createReplies(fast: FakeModel, main: FakeModel) {
  const moduleRef = await Test.createTestingModule({
    imports: [
      AiModule.forRoot({
        models: { default: main, fast: { model: fast, fallback: 'default' } },
        defaults: {
          timeout: 50,
          retry: { attempts: 2, backoff: { delay: 0 } },
        },
      }),
    ],
    providers: [RepliesService],
  }).compile();
  return moduleRef.get(RepliesService);
}

describe('RepliesService', () => {
  it('falls back to the default model when the fast one fails', async () => {
    const fast = new FakeModel([providerError(529), providerError(529)]);
    const main = new FakeModel(['Thanks for writing in!']);
    const replies = await createReplies(fast, main);

    await expect(replies.draft('Hello')).resolves.toBe(
      'Thanks for writing in!',
    );
    expect(fast.calls).toHaveLength(2);
  });

  it('gives up when every model fails', async () => {
    const fast = new FakeModel(() => providerError(500));
    const main = new FakeModel(() => ({ text: 'Too late', delay: 1_000 }));
    const replies = await createReplies(fast, main);

    const error = await replies.draft('Hello').catch((error: unknown) => error);

    expect(error).toBeInstanceOf(AiModelError);
    expect((error as AiModelError).attempts).toHaveLength(4);
    expect((error as AiModelError).cause).toBeInstanceOf(
      ResilienceTimeoutError,
    );
  });
});
```

Model nhanh thất bại hai lần, và model mặc định mất lâu hơn 50 mili giây mà mỗi lần thử có, hai lần: tổng cộng bốn lần thử, và lỗi của lần cuối cùng là `cause`.

#### Override model trong end-to-end test <a id="overriding-models-in-end-to-end-tests"></a>

`overrideModels()` đặt các fake model vào chỗ các model của ứng dụng, theo tên, và giữ phần còn lại của định nghĩa của chúng: pricing, fallback model, timeout và retry. Một tên mà module không cấu hình sẽ thất bại khi testing module compile. Các model mà `@InjectModel()` inject cũng được thay thế:

```typescript
@@filename(test/assistant.e2e-spec)
import { Test } from '@nestjs/testing';
import type { INestApplication } from '@nestjs/common';
import { FakeModel, overrideModels } from '@nestjs/ai/testing';
import request from 'supertest';
import { AppModule } from '../src/app.module';

describe('the assistant', () => {
  let app: INestApplication;
  const model = new FakeModel();

  beforeAll(async () => {
    const moduleRef = await overrideModels(
      Test.createTestingModule({ imports: [AppModule] }),
      { default: model },
    ).compile();
    app = await moduleRef.createNestApplication().init();
  });

  afterAll(() => app.close());

  it('looks the order up before it answers', async () => {
    model.reply(
      { toolCalls: [{ name: 'find-order', input: { orderId: 'ord_123' } }] },
      (call) => {
        const order = call.toolResults[0].output as { status: string };
        return `Your order has ${order.status}.`;
      },
    );

    const response = await request(app.getHttpServer())
      .post('/assistant/questions')
      .send({ question: 'Where is ord_123?' })
      .expect(201);

    expect(response.body).toEqual({ answer: 'Your order has shipped.' });
    expect(model.calls.map((call) => call.tools)).toEqual([
      ['find-order'],
      ['find-order'],
    ]);
  });
});
```

Các agent function chạy thật, với schema, guard và filter của chúng: lỗi của một function tới model dưới dạng kết quả của tool, thứ mà test đọc trong `toolResults` của lời gọi tiếp theo:

```typescript
it('tells the model when there is no such order', async () => {
  model.reply(
    { toolCalls: [{ name: 'find-order', input: { orderId: 'ord_999' } }] },
    'I could not find that order.',
  );

  await request(app.getHttpServer())
    .post('/assistant/questions')
    .send({ question: 'Where is ord_999?' })
    .expect(201);

  expect(model.lastCall?.toolResults).toEqual([
    expect.objectContaining({
      toolName: 'find-order',
      output: 'There is no order ord_999',
    }),
  ]);
});
```

#### Test agent function <a id="testing-agent-functions"></a>

`callTool()` chạy một agent function giống như lời gọi tool của một model, không cần model: các argument được validate theo schema của nó, scope của nó được kiểm tra, rồi đến guard, interceptor, pipe và filter, và method. Nó resolve với những gì model sẽ đọc, và reject với `AiToolError` mà model sẽ đọc về một lỗi:

```typescript
@@filename(assistant/assistant.tools.spec)
import { Test, type TestingModule } from '@nestjs/testing';
import { AiModule } from '@nestjs/ai';
import { callTool, FakeModel } from '@nestjs/ai/testing';
import { OrdersModule } from '../orders/orders.module';
import { AssistantModule } from './assistant.module';

describe('change-address', () => {
  let moduleRef: TestingModule;
  const alice = { request: { user: { id: 'cus_alice' } } };
  const bob = { request: { user: { id: 'cus_bob' } } };

  beforeAll(async () => {
    moduleRef = await Test.createTestingModule({
      imports: [
        AiModule.forRoot({
          isGlobal: true,
          models: { default: new FakeModel() },
        }),
        OrdersModule,
        AssistantModule,
      ],
    }).compile();
  });

  afterAll(() => moduleRef.close());

  it("changes the address of the customer's own order", async () => {
    const address = { orderId: 'ord_123', address: '12 Whisker Lane, Leeds' };
    await expect(
      callTool(moduleRef, 'change-address', address, { caller: alice }),
    ).resolves.toEqual({ id: 'ord_123', address: '12 Whisker Lane, Leeds' });
  });

  it("refuses another customer's order", async () => {
    const address = { orderId: 'ord_123', address: '12 Whisker Lane, Leeds' };
    await expect(
      callTool(moduleRef, 'change-address', address, { caller: bob }),
    ).rejects.toThrow('Forbidden resource');
  });

  it('validates the address', async () => {
    const address = { orderId: 'ord_123', address: 'Leeds' };
    await expect(
      callTool(moduleRef, 'change-address', address, { caller: alice }),
    ).rejects.toThrow('Too small');
  });
});
```

`caller` chính là `caller` của một lời gọi: một `request`, như của route, hoặc một `user` và `scopes`. `callTool()` khởi tạo testing module nếu nó chưa được khởi tạo. Một method đồng thời phục vụ MCP client được test như một MCP tool bằng [client trong bộ nhớ](/mcp/testing) của `@nestjs/mcp/testing`, với các lời gọi có context type `'mcp'`.

Một unit test gọi trực tiếp method, với context mà nó cần. Một lời gọi trực tiếp bỏ qua mọi thứ xung quanh method: schema, scope và các enhancer. Việc hoàn tiền của một [durable run](/ai/agents#durable-agent-runs) truyền `idempotencyKey` của lời gọi tiếp cho payment provider:

```typescript
@@filename(refunds/refund.tools.spec)
import type { AgentFunctionContext } from '@nestjs/ai';
import { OrdersService } from '../orders/orders.service';
import { PaymentsService } from '../payments/payments.service';
import { RefundTools } from './refund.tools';

describe('RefundTools', () => {
  const orders = {
    findById: vi.fn().mockResolvedValue({
      id: 'ord_123',
      paymentId: 'pay_123',
      total: 4200,
    }),
  };
  const payments = { refund: vi.fn() };
  const tools = new RefundTools(
    orders as unknown as OrdersService,
    payments as unknown as PaymentsService,
  );
  const ctx = {
    idempotencyKey: 'refund-1:tool-1-call-2',
    signal: new AbortController().signal,
  } as AgentFunctionContext;

  it("refunds the order with the call's idempotency key", async () => {
    await expect(tools.refund({ orderId: 'ord_123' }, ctx)).resolves.toEqual({
      refunded: 'ord_123',
      amount: 4200,
    });
    expect(payments.refund).toHaveBeenCalledWith('pay_123', 4200, {
      idempotencyKey: 'refund-1:tool-1-call-2',
    });
  });

  it("doesn't refund an order that doesn't exist", async () => {
    orders.findById.mockResolvedValueOnce(undefined);
    await expect(tools.refund({ orderId: 'ord_999' }, ctx)).rejects.toThrow(
      'There is no order ord_999',
    );
  });
});
```

#### Test stream <a id="testing-streams"></a>

Fake model stream đoạn text của nó theo từng chunk cỡ một từ, nên một stream được đọc giống như từ một provider. Trong một end-to-end test, response của một chat route là một body server-sent event, với các event là các chunk của UI message stream:

```typescript
it('streams the answer, with the tool call', async () => {
  model.reply(
    { toolCalls: [{ name: 'find-order', input: { orderId: 'ord_123' } }] },
    'Your order has shipped.',
  );

  const response = await request(app.getHttpServer())
    .post('/assistant/chat')
    .send({
      messages: [
        {
          id: 'msg_1',
          role: 'user',
          parts: [{ type: 'text', text: 'Where is ord_123?' }],
        },
      ],
    })
    .expect(200)
    .expect('content-type', 'text/event-stream');

  const chunks = response.text
    .split('\n\n')
    .filter((event) => event.startsWith('data: {'))
    .map((event) => JSON.parse(event.slice('data: '.length)));
  expect(chunks).toContainEqual(
    expect.objectContaining({
      type: 'tool-output-available',
      output: { id: 'ord_123', status: 'shipped', total: 4200 },
    }),
  );
  const text = chunks
    .filter((chunk) => chunk.type === 'text-delta')
    .map((chunk) => chunk.delta)
    .join('');
  expect(text).toBe('Your order has shipped.');
});
```

`streamError` test một stream bị đứt sau chunk đầu tiên, `{{ '{' }} text: 'Your order', streamError: providerError(500) {{ '}' }}`: khi đó body kết thúc bằng một chunk `error` ghi `An error occurred.`. Bên ngoài HTTP, hãy đọc trực tiếp stream của `streamText()`, dưới dạng `textStream`, hoặc promise `text` của nó.

#### Test durable run <a id="testing-durable-runs"></a>

Một durable run được test với workflow engine chạy ngay trong test, trên store trong bộ nhớ của nó, với một `ManualWorkflowClock` và worker bị tắt: `WorkflowWorker.drain()` chạy các instance tới hạn, cho tới khi không còn instance nào có thể chạy, nên test quyết định khi nào run tiếp tục:

```typescript
@@filename(refunds/refund-request.workflow.spec)
import { Test, type TestingModule } from '@nestjs/testing';
import { AiModule } from '@nestjs/ai';
import { FakeModel } from '@nestjs/ai/testing';
import { AiAgents } from '@nestjs/ai/workflows';
import {
  ManualWorkflowClock,
  WorkflowClient,
  WorkflowsModule,
  WorkflowWorker,
} from '@nestjs/workflows';
import { PaymentsService } from '../payments/payments.service';
import { RefundRequest } from './refund-request.workflow';
import { RefundsModule } from './refunds.module';

describe('RefundRequest', () => {
  let moduleRef: TestingModule;
  const payments = { refund: vi.fn() };
  const model = new FakeModel([
    { toolCalls: [{ name: 'find-order', input: { orderId: 'ord_123' } }] },
    { toolCalls: [{ name: 'refund', input: { orderId: 'ord_123' } }] },
    'Your order ord_123 is refunded.',
  ]);

  beforeAll(async () => {
    moduleRef = await Test.createTestingModule({
      imports: [
        WorkflowsModule.forRoot({
          clock: new ManualWorkflowClock(),
          worker: false,
        }),
        AiModule.forRoot({ isGlobal: true, models: { default: model } }),
        RefundsModule,
      ],
    })
      .overrideProvider(PaymentsService)
      .useValue(payments)
      .compile();
    await moduleRef.init();
  });

  afterAll(() => moduleRef.close());

  it('refunds the order once the support team approves', async () => {
    const workflows = moduleRef.get(WorkflowClient);
    const worker = moduleRef.get(WorkflowWorker);
    const agents = moduleRef.get(AiAgents);

    await workflows.start(
      RefundRequest,
      { email: 'Please refund ord_123', customerId: 'cus_alice' },
      { id: 'refund-1' },
    );
    await worker.drain();

    const [pending] = await agents.pendingApprovals('refund-1');
    expect(pending).toMatchObject({
      toolName: 'refund',
      input: { orderId: 'ord_123' },
    });
    expect(payments.refund).not.toHaveBeenCalled();

    await agents.approve(pending.key);
    await worker.drain();

    expect(payments.refund).toHaveBeenCalledTimes(1);
    expect(await workflows.getStatus('refund-1')).toMatchObject({
      status: 'completed',
      output: { text: 'Your order ord_123 is refunded.' },
    });
  });
});
```

Các lời gọi model và lời gọi tool mà run đã thực hiện trước khi được phê duyệt sẽ được đọc lại từ journal khi nó tiếp tục: tổng cộng fake model được gọi ba lần. Để test một lần restart, hãy boot một ứng dụng thứ hai trên cùng store, như [Test khả năng phục hồi sau crash](/reliability/workflows#test-crash-recovery) trình bày cho mọi workflow.

#### Test embedding <a id="testing-embeddings"></a>

`FakeEmbeddingModel` là fake model cho [các lời gọi embedding](/ai/embeddings): một `EmbeddingModel` thật, trả lời mỗi request tới provider bằng câu trả lời tiếp theo trong danh sách bạn đưa cho nó, và ghi lại request đó. Nó không tự bịa ra vector nào: một câu trả lời có mỗi giá trị của request một vector.

```typescript
@@filename(catalog/search.service.spec)
import { Test } from '@nestjs/testing';
import { AiModule } from '@nestjs/ai';
import { FakeEmbeddingModel, providerError } from '@nestjs/ai/testing';
import { ProductsRepository } from './products.repository';
import { SearchService } from './search.service';

describe('SearchService', () => {
  const products = { saveEmbeddings: vi.fn(), findNearest: vi.fn() };

  async function createSearch(model: FakeEmbeddingModel) {
    const moduleRef = await Test.createTestingModule({
      imports: [
        AiModule.forRoot({
          embeddingModels: { default: model },
          embeddingDefaults: {
            retry: { attempts: 2, backoff: { delay: 0 } },
          },
        }),
      ],
      providers: [
        SearchService,
        { provide: ProductsRepository, useValue: products },
      ],
    }).compile();
    return moduleRef.get(SearchService);
  }

  it('finds the products nearest to the search', async () => {
    const model = new FakeEmbeddingModel([{ embeddings: [[0.1, 0.2]] }]);
    const search = await createSearch(model);

    await search.search("my cat won't eat");

    expect(model.lastCall?.values).toEqual(["my cat won't eat"]);
    expect(products.findNearest).toHaveBeenCalledWith([0.1, 0.2], 10);
  });

  it('sends a failed request again, and only that one', async () => {
    const model = new FakeEmbeddingModel(
      [{ embeddings: [[1]] }, providerError(429), { embeddings: [[2]] }],
      { maxEmbeddingsPerCall: 1, supportsParallelCalls: false },
    );
    const search = await createSearch(model);
    const catalog = [
      { id: 'prd_1', description: 'Salmon pate' },
      { id: 'prd_2', description: 'Catnip mouse' },
    ];

    await search.index(catalog);

    expect(model.calls.map((call) => call.values)).toEqual([
      ['Salmon pate'],
      ['Catnip mouse'],
      ['Catnip mouse'],
    ]);
    expect(products.saveEmbeddings).toHaveBeenCalledWith(catalog, [[1], [2]]);
  });
});
```

Tham số thứ hai cho biết AI SDK chia các giá trị thế nào, giống như model của một provider: ở đây mỗi giá trị là một request riêng, và chúng được gửi từng cái một, để test biết thứ tự của chúng. Nó cũng nhận `provider` và `modelId`. Không có nó, model không có giới hạn, và `embedMany()` chỉ thực hiện một request.

| Câu trả lời | Model làm gì |
| --- | --- |
| `{{ '{' }} embeddings {{ '}' }}` | Trả lời bằng các vector, mỗi giá trị của request một vector |
| Một `Error` | Thất bại với lỗi đó, như một request tới provider |
| Một hàm nhận lời gọi | Trả lời bằng những gì nó trả về, bất kỳ loại nào ở trên, hoặc một promise của nó |

Một answer object cũng nhận:

| Tùy chọn | Làm gì |
| --- | --- |
| `usage` | Số token mà câu trả lời báo cáo: `{{ '{' }} tokens {{ '}' }}`, mặc định 10 cho mỗi giá trị |
| `delay` | Số mili giây trước khi nó trả lời. Việc abort lời gọi, và timeout của nó, sẽ cắt ngang khoảng này |
| `warnings`, `providerMetadata`, `response` | Những gì provider thêm vào các vector của nó |

Nếu được đưa một hàm thay vì một danh sách, `new FakeEmbeddingModel((call) => ...)` trả lời mọi request bằng hàm đó, phù hợp với một test không quan tâm các giá trị được chia thế nào. `reply(...answers)` thêm câu trả lời vào sau những câu chưa dùng, và `fakeEmbeddingModel(...answers)` là `new FakeEmbeddingModel(answers)`. Một request mà nó không còn câu trả lời nào sẽ thất bại: `FakeEmbeddingModel: no answer left for call 3. Give it more answers.`

`calls` liệt kê những gì model đã nhận, mỗi request kèm `values` và `options` của nó, tức các call option ở cấp provider của AI SDK như `abortSignal`, `headers` và `providerOptions`, và `lastCall` là request cuối cùng.

`overrideEmbeddingModels()` làm với embedding model những gì `overrideModels()` làm với language model: nó đặt các fake model vào chỗ các model của ứng dụng, theo tên, và giữ phần còn lại của định nghĩa của chúng, gồm thiết lập và pricing. Một tên mà module không cấu hình sẽ thất bại khi testing module compile. Các model mà `@InjectEmbeddingModel()` inject cũng được thay thế:

```typescript
@@filename(test/search.e2e-spec)
import { Test } from '@nestjs/testing';
import {
  FakeEmbeddingModel,
  overrideEmbeddingModels,
} from '@nestjs/ai/testing';
import { AppModule } from '../src/app.module';

const model = new FakeEmbeddingModel(({ values }) => ({
  embeddings: values.map(() => [0.1, 0.2]),
}));

const moduleRef = await overrideEmbeddingModels(
  Test.createTestingModule({ imports: [AppModule] }),
  { default: model },
).compile();
```

Để thay cả language model trong cùng test, hãy truyền những gì `overrideEmbeddingModels()` trả về cho `overrideModels()`.
