### Agent

Một agent là một model gọi tool trong một vòng lặp: nó đọc những gì mỗi tool trả về, rồi gọi thêm tool hoặc trả lời, cho tới khi nó đã trả lời hoặc chạm giới hạn số lời gọi model.

Mọi lời gọi `AiService` có [tool](/ai/tools), tức các agent function của bạn, đều chạy vòng lặp đó, bên trong process của bạn: không có gì khác phải deploy. Trang này nói về những gì đi kèm: vòng lặp và các giới hạn của nó, hội thoại, câu trả lời được stream tới trình duyệt ngay khi đang viết, và các durable run tồn tại qua các lần restart và chờ một người phê duyệt.

#### Vòng lặp agent <a id="the-agent-loop"></a>

Một lời gọi có tool sẽ thực hiện một lời gọi model, chạy các tool mà model yêu cầu, và thực hiện lời gọi model tiếp theo với kết quả của chúng, cho tới khi model trả lời mà không yêu cầu tool nào. Mỗi lời gọi model là một **step**, và kết quả liệt kê chúng:

```typescript
@@filename(assistant/assistant.service)
import { Injectable, Logger } from '@nestjs/common';
import { AiService } from '@nestjs/ai';

@Injectable()
export class AssistantService {
  private readonly logger = new Logger(AssistantService.name);

  constructor(private readonly ai: AiService) {}

  async answer(question: string, request: unknown) {
    const result = await this.ai.generateText({
      label: 'assistant',
      prompt: question,
      tools: ['find-order', 'change-address'],
      caller: { request },
      maxSteps: 5,
    });
    for (const step of result.steps) {
      const tools = step.toolCalls.map((call) => call.toolName).join(', ');
      this.logger.log(
        `Step ${step.index}: ${tools || 'answered'}, ` +
          `${step.usage.totalTokens} tokens, ${step.attempts} attempt(s)`,
      );
    }
    return result.text;
  }
}
```

Mỗi step có `text`, `toolCalls`, `toolResults` (những gì mỗi tool trả về dưới dạng `output`, hoặc `error` mà model được báo), `finishReason`, `usage`, `cost`, `model` đã trả lời và các `attempts` mà nó đã cần.

`maxSteps` giới hạn số lời gọi model của một lời gọi, mặc định 10 (`defaults.maxSteps` thay đổi nó cho mọi lời gọi). Khi hết số lần này trong khi model vẫn yêu cầu tool, `generateText()` resolve với những gì nó có, và `finishReason` của nó là `'tool-calls'`; `generateObject()` reject với `AiOutputError`, vì nó không có object nào để trả về. Các tool chạy bên trong step của chúng: thời gian của chúng không bị tính vào `timeout` của model, và một step có tool đã bắt đầu chạy sẽ không bao giờ được retry, nên không tool nào chạy hai lần.

`toolChoice` được truyền cho model như của AI SDK: `'auto'`, mặc định, để model tự chọn, còn `'none'` cung cấp tool nhưng để model không gọi cái nào. `'required'` và `{{ '{' }} type: 'tool', toolName {{ '}' }}` buộc nó gọi một tool, điều mà không phải model nào cũng chấp nhận.

Một `abortSignal` hủy một lời gọi: lời gọi model đang chạy, thời gian chờ trước một lần retry, và các agent function đang chạy, qua `signal` trong context của chúng. Một job không được kéo dài quá hai phút sẽ truyền `abortSignal: AbortSignal.timeout(120_000)`, và lời gọi reject với reason của signal, không retry hay fallback.

#### Hội thoại <a id="conversations"></a>

`messages` nhận cả một cuộc hội thoại, dưới dạng các object `ModelMessage` của AI SDK, thay cho `prompt`. `responseMessages` của một lời gọi là các message mà nó đã thêm vào: câu trả lời và các lời gọi tool của model, cùng kết quả của các tool. Hãy nối chúng vào cuộc hội thoại, và gửi nó kèm message tiếp theo của khách hàng:

```typescript
@@filename(assistant/conversations.service)
import { Injectable } from '@nestjs/common';
import { AiService } from '@nestjs/ai';
import type { ModelMessage } from 'ai';

@Injectable()
export class ConversationsService {
  // Keep conversations in your database: this one is lost on a restart.
  private readonly conversations = new Map<string, ModelMessage[]>();

  constructor(private readonly ai: AiService) {}

  async reply(conversationId: string, message: string, request: unknown) {
    const messages: ModelMessage[] = [
      ...(this.conversations.get(conversationId) ?? []),
      { role: 'user', content: message },
    ];
    const { text, responseMessages } = await this.ai.generateText({
      instructions: 'You help customers of the cat store with their orders.',
      messages,
      tools: ['find-order', 'change-address'],
      caller: { request },
    });
    this.conversations.set(conversationId, [...messages, ...responseMessages]);
    return text;
  }
}
```

`instructions` không phải là một phần của cuộc hội thoại: mỗi lời gọi gửi phần instructions của riêng nó. Một cuộc chat trên trình duyệt tự giữ cuộc hội thoại, và gửi nó kèm mỗi message: xem [Stream tới trình duyệt](/ai/agents#streaming-to-the-browser).

#### Stream tới trình duyệt <a id="streaming-to-the-browser"></a>

Assistant trả lời trong lúc nó suy nghĩ, nên trình duyệt hiển thị câu trả lời ngay khi đang được viết. `streamText()` bắt đầu lời gọi và trả về stream của nó ngay lập tức, và `pipeUIMessageStreamToResponse()` gửi nó, dưới dạng server-sent event theo giao thức UI message stream của AI SDK, trên response mà `@Res()` inject:

```typescript
@@filename(assistant/assistant.controller)
import { Body, Controller, Post, Req, Res } from '@nestjs/common';
import { AiService } from '@nestjs/ai';
import { convertToModelMessages, type UIMessage } from 'ai';
import type { Request, Response } from 'express';

@Controller('assistant')
export class AssistantController {
  constructor(private readonly ai: AiService) {}

  @Post('chat')
  async chat(
    @Body() { messages }: { messages: UIMessage[] },
    @Req() request: Request,
    @Res() response: Response,
  ) {
    const answer = this.ai.streamText({
      label: 'assistant',
      instructions:
        'You help customers of the cat store with their orders. ' +
        'Look an order up before you answer about it.',
      messages: await convertToModelMessages(messages),
      tools: ['find-order', 'change-address'],
      caller: { request },
    });
    await answer.pipeUIMessageStreamToResponse(response);
  }
}
```

Route hoạt động giống nhau trên Fastify và Node adapter: `pipeUIMessageStreamToResponse()` nhận response của platform, một `FastifyReply` trên Fastify, các header của nó được đặt trước khi stream bắt đầu, như các header CORS, sẽ được giữ lại. `convertToModelMessages()`, từ `ai`, biến các object `UIMessage` mà trình duyệt post lên thành các model message mà lời gọi nhận.

Trên trình duyệt, `useChat()` từ `@ai-sdk/react`, hoặc các package của AI SDK cho Vue, Svelte và Angular, post cuộc hội thoại lên route và dựng câu trả lời ngay khi nó tới:

```typescript
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';

const { messages, sendMessage, status } = useChat({
  transport: new DefaultChatTransport({ api: '/assistant/chat' }),
});
```

`parts` của mỗi message chứa đoạn text của nó (`type: 'text'`) và các lời gọi tool mà model đã thực hiện, dưới dạng các part `tool-find-order` với `state`, `input` và `output` của chúng. Câu trả lời của mọi lời gọi model trong lời gọi được stream thành một message, bao gồm cả các lời gọi tool và kết quả của chúng.

- **Lỗi.** Một lời gọi thất bại trước chunk đầu tiên sẽ reject, không gửi gì cả, nên các exception filter của route sẽ trả lời nó. Cho tới thời điểm đó, stream được retry, và fallback sang model khác, như mọi lời gọi. Một lỗi xảy ra sau đó sẽ kết thúc stream bằng một error chunk ghi `An error occurred.`, để không chi tiết nào của server bị lộ ra: tùy chọn `errorText` cho phép nói rõ hơn.
- **Keep-alive.** Khi 15 giây trôi qua mà không có chunk nào, chẳng hạn trong lúc một tool đang chạy, một dòng comment (`: keep-alive`) được gửi đi, để proxy và load balancer không đóng kết nối vì cho rằng nó rảnh. `useChat()` bỏ qua dòng này. Tùy chọn `keepAlive` đặt khoảng thời gian, hoặc `false` tắt nó.
- **Trình duyệt rời đi.** Khi trình duyệt đóng kết nối, lời gọi model bị abort, và `signal` của các agent function đang chạy cũng vậy.
- **Header.** Response là `text/event-stream` với `x-accel-buffering: no`, header bảo nginx không buffer nó. `status` và `headers` cho phép thêm header của riêng bạn.

```typescript
await answer.pipeUIMessageStreamToResponse(response, {
  keepAlive: '10s',
  errorText: (error) =>
    error instanceof AiModelError
      ? 'The assistant is unavailable. Try again in a minute.'
      : 'Something went wrong.',
});
```

`ctx.reportProgress()` của một agent function tới trình duyệt dưới dạng một chunk tạm thời `data-tool-progress`, thứ mà `useChat()` chuyển cho callback `onData` của nó mà không thêm vào message:

```typescript
@@filename(catalog/catalog.tools)
@AgentFunction({
  name: 'check-stock',
  description: 'Check the stock of a product in every warehouse',
  inputSchema: z.object({
    sku: z.string().describe('The product SKU, such as SKU-1042'),
  }),
})
async checkStock({ sku }: { sku: string }, ctx: AgentFunctionContext) {
  const warehouses = await this.stock.warehouses();
  const counts: Record<string, number> = {};
  for (const [index, warehouse] of warehouses.entries()) {
    counts[warehouse.name] = await this.stock.count(warehouse.id, sku, {
      signal: ctx.signal,
    });
    await ctx.reportProgress(index + 1, warehouses.length, warehouse.name);
  }
  return counts;
}
```

```typescript
const { messages, sendMessage } = useChat({
  transport: new DefaultChatTransport({ api: '/assistant/chat' }),
  onData: (part) => {
    if (part.type === 'data-tool-progress') {
      // { toolCallId, toolName, progress, total, message }
      console.log(part.data);
    }
  },
});
```

Stream còn có các cách đọc khác. `pipeTextStreamToResponse(response)` chỉ gửi đoạn text, dưới dạng `text/plain`; `textStream` duyệt qua nó; `toUIMessageStream()` là UI message stream dưới dạng một `ReadableStream`, còn `toUIMessageStreamResponse()` là dưới dạng một `Response` chuẩn web. `text`, `usage`, `steps`, `finishReason` và `responseMessages` là các promise settle khi lời gọi kết thúc, và `result` có tất cả chúng; chúng reject với lỗi của lời gọi. Lời gọi chỉ chạy một lần, bất kể cái gì đọc nó, và mỗi cách đọc nhận toàn bộ stream từ đầu. `abort()` hủy nó. Các sai sót trong tùy chọn, chẳng hạn một agent function không tồn tại, sẽ throw ngay từ `streamText()`.

```typescript
@Post('summary')
async summary(
  @Body() { thread }: { thread: string },
  @Res() response: Response,
) {
  const answer = this.ai.streamText({
    model: 'fast',
    instructions: 'Summarize the support thread in three sentences.',
    prompt: thread,
  });
  await answer.pipeTextStreamToResponse(response);
}
```

#### Durable agent run <a id="durable-agent-runs"></a>

Một yêu cầu hoàn tiền cần có người xử lý: agent tra cứu đơn hàng và yêu cầu hoàn tiền, và một người trong bộ phận hỗ trợ phê duyệt, có thể sáng hôm sau, có thể sau một lần deploy. `@nestjs/ai/workflows` chạy vòng lặp agent trên [`@nestjs/workflows`](/reliability/workflows), với mỗi lời gọi model là một step và mỗi lời gọi tool là một step khác. Một run bị một lần restart làm gián đoạn sẽ tiếp tục từ chỗ nó đang dừng, và những gì journal của nó chứa sẽ được đọc lại, không làm lại. Cài package:

```bash
$ npm i --save @nestjs/workflows
```

Import `AiWorkflowsModule` trong module chứa các workflow của bạn. Ứng dụng import `WorkflowsModule`, với một store trong database của bạn như [Durable workflow](/reliability/workflows#keep-workflows-in-your-database) mô tả, và `AiModule`, như thường lệ:

```typescript
@@filename(refunds/refunds.module)
import { Module } from '@nestjs/common';
import { AiWorkflowsModule } from '@nestjs/ai/workflows';
import { OrdersModule } from '../orders/orders.module';
import { PaymentsModule } from '../payments/payments.module';
import { ApprovalsController } from './approvals.controller';
import { RefundRequest } from './refund-request.workflow';
import { RefundTools } from './refund.tools';
import { RefundsService } from './refunds.service';

@Module({
  imports: [AiWorkflowsModule, OrdersModule, PaymentsModule],
  controllers: [ApprovalsController],
  providers: [RefundRequest, RefundTools, RefundsService],
})
export class RefundsModule {}
```

Chạy agent từ một workflow của riêng bạn, bằng `AiAgents`:

```typescript
@@filename(refunds/refund-request.workflow)
import { AiAgents } from '@nestjs/ai/workflows';
import { Workflow, type WorkflowContext } from '@nestjs/workflows';

export interface RefundRequestInput {
  email: string;
  customerId: string;
}

@Workflow('refund-request')
export class RefundRequest {
  constructor(private readonly agents: AiAgents) {}

  run(ctx: WorkflowContext, input: RefundRequestInput) {
    return this.agents.run(ctx, {
      label: 'refund-request',
      instructions:
        'You handle the refund requests of the cat store. Look the order ' +
        'up, and refund it when the customer is right.',
      prompt: input.email,
      tools: ['find-order', 'refund'],
      approve: ['refund'],
      caller: { user: { id: input.customerId } },
    });
  }
}
```

Khởi động nó như mọi workflow, với một id lấy từ ticket, điều này khiến việc khởi động lại cho cùng ticket trả về run đã có:

```typescript
@@filename(refunds/refunds.service)
import { Injectable } from '@nestjs/common';
import { WorkflowClient } from '@nestjs/workflows';
import { RefundRequest } from './refund-request.workflow';

@Injectable()
export class RefundsService {
  constructor(private readonly workflows: WorkflowClient) {}

  async request(ticket: { id: string; body: string; customerId: string }) {
    await this.workflows.start(
      RefundRequest,
      { email: ticket.body, customerId: ticket.customerId },
      { id: `refund-${ticket.id}` },
    );
  }
}
```

Một lời gọi tới agent function có tên trong `approve` sẽ chờ một người trước khi nó chạy, bao lâu cũng được; `approvalTimeout` giới hạn thời gian chờ. `pendingApprovals(runId)` liệt kê các lời gọi đang chờ, mỗi lời gọi kèm `key`, `toolName` và `input`, và `approve(key)` hoặc `reject(key, {{ '{' }} reason {{ '}' }})` trả lời một lời gọi, từ bất cứ đâu bộ phận hỗ trợ làm việc:

```typescript
@@filename(refunds/approvals.controller)
import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { AiAgents } from '@nestjs/ai/workflows';

@Controller('refunds')
export class ApprovalsController {
  constructor(private readonly agents: AiAgents) {}

  @Get(':runId/approvals')
  pending(@Param('runId') runId: string) {
    return this.agents.pendingApprovals(runId);
  }

  @Post('approvals/:key')
  answer(
    @Param('key') key: string,
    @Body() body: { approved: boolean; reason?: string },
  ) {
    return body.approved
      ? this.agents.approve(key)
      : this.agents.reject(key, { reason: body.reason });
  }
}
```

Một lời gọi bị từ chối sẽ không chạy: model được báo rằng nó đã bị từ chối, và lý do, rồi trả lời khách hàng. Một lời gọi không ai trả lời trong `approvalTimeout` cũng không chạy. Câu trả lời đầu tiên cho một lời gọi mới được tính, và `approve()` cùng `reject()` nhận `by`, người đã trả lời, được lưu cùng câu trả lời. Trong khi một run đang chờ, workflow instance của nó bị tạm dừng, và không giữ process nào.

Những gì một run cần để tiếp tục được lưu cùng nó, nên các tùy chọn của nó là dữ liệu: model theo tên, agent function theo tên hoặc theo class provider, được run lưu dưới dạng tên, và `caller` dưới dạng `user` và `scopes` mà các agent function cần, vì sau một lần restart không còn request nào để đọc. Các agent function nhận chúng dưới dạng `ctx.user` và `ctx.scopes`; với `@nestjs/authentication`, provider của chúng là [`@Public()`](/ai/tools#with-nestjsauthentication-and-nestjsauthorization), như với mọi lời gọi không có request. Các lời gọi model của một run dùng `timeout`, `retry` và các thiết lập sinh của model và của module, còn `maxSteps` và `budget` của nó fallback về `defaults` của module, giống như một lời gọi thông thường.

Một lời gọi agent function chạy ít nhất một lần: một process chết trong lúc nó chạy sẽ khiến nó chạy lại sau khi restart, với cùng `ctx.idempotencyKey`. Một function thay đổi dữ liệu sẽ truyền key này đi tiếp, để thay đổi chỉ xảy ra một lần:

```typescript
@@filename(refunds/refund.tools)
import { Injectable, NotFoundException } from '@nestjs/common';
import { AgentFunction, type AgentFunctionContext } from '@nestjs/ai';
import * as z from 'zod';
import { OrdersService } from '../orders/orders.service';
import { PaymentsService } from '../payments/payments.service';

@Injectable()
export class RefundTools {
  constructor(
    private readonly orders: OrdersService,
    private readonly payments: PaymentsService,
  ) {}

  @AgentFunction({
    name: 'refund',
    description: 'Refund an order to the card it was paid with',
    inputSchema: z.object({ orderId: z.string() }),
  })
  async refund({ orderId }: { orderId: string }, ctx: AgentFunctionContext) {
    const order = await this.orders.findById(orderId);
    if (!order) {
      throw new NotFoundException(`There is no order ${orderId}`);
    }
    await this.payments.refund(order.paymentId, order.total, {
      idempotencyKey: ctx.idempotencyKey,
    });
    return { refunded: order.id, amount: order.total };
  }
}
```

Lỗi của một agent function là một kết quả mà model đọc, như trong mọi lời gọi, chứ không phải lỗi của step chứa nó. Một lời gọi model giữ nguyên retry, timeout và fallback model của nó; một lời gọi vẫn thất bại sẽ được retry như một step của workflow, workflow chờ một cách bền vững giữa các lần thử (mặc định ba lần thử). Sau `stepsPerInstance` lời gọi model (10), một run tiếp tục trong một child workflow, để không journal của instance nào phình dài: mỗi lần tiếp tục đều replay toàn bộ journal, và nó có giới hạn. `maxSteps` (25) giới hạn số lời gọi model của một run.

Run resolve với những gì `generateText()` resolve, gồm `text`, `steps`, `toolResults` và các thuộc tính còn lại, dưới dạng JSON: đó là output của workflow, thứ mà `getStatus(runId)` của `WorkflowClient` cũng đọc được.

Các tùy chọn của `run()`:

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `model`, `fallback` | `'default'`, fallback của model | Các model, theo tên |
| `instructions`, `prompt`, `messages` | | Như với một lời gọi |
| `tools` | | Tên agent function và class provider, được lưu dưới dạng tên |
| `approve` | `[]` | Các agent function, trong số `tools`, mà lời gọi của chúng phải chờ một người phê duyệt |
| `approvalTimeout` | cho tới khi có câu trả lời | Một lời gọi chờ phê duyệt trong bao lâu |
| `caller` | | `user` và `scopes` mà các agent function chạy với tư cách đó |
| `maxSteps` | `defaults.maxSteps`, nếu không thì `25` | Số lời gọi model của run |
| `stepsPerInstance` | `10` | Số lời gọi model của một workflow instance, trước khi run tiếp tục trong một child |
| `budget` | `defaults.budget` | `maxTokens` và `maxCost`, trên toàn run |
| `label`, `toolChoice`, `maxOutputTokens`, `temperature`, `providerOptions` | | Như với một lời gọi |
