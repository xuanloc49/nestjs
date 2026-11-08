### AI

`@nestjs/ai` đưa language model vào một ứng dụng Nest: các model được đăng ký theo tên và inject vào, các lời gọi có timeout, retry và fallback model, câu trả lời được validate theo một schema, và các method của provider trở thành agent function, thứ mà model gọi dưới dạng tool.

Cửa hàng online bán thức ăn và đồ dùng cho mèo nhận một trăm email hỗ trợ mỗi ngày, và khách hàng của nó thà hỏi website về đơn hàng của họ còn hơn phải viết email. Cả hai đều là việc cho một language model, ngay bên trong API đơn hàng: phân loại một email và soạn bản nháp phản hồi, hoặc trả lời khách hàng trong một cuộc chat bằng những gì API biết về đơn hàng của họ.

Package này xây trên [AI SDK](https://ai-sdk.dev) (`ai`) và các package provider của nó, nên bất kỳ model nào chúng hỗ trợ đều dùng được: Claude, GPT, Gemini, Mistral, hoặc một model đứng sau một gateway. Các lời gọi model chạy trên các policy của [`@nestjs/resilience`](/reliability/resilience). Bạn viết một agent function, tức một method có `@AgentFunction()`, và model được cung cấp nó dưới dạng một tool: mọi lời gọi tới nó đều đi qua các guard, interceptor, pipe và exception filter mà route của bạn dùng, với tư cách người dùng mà model đang hành động thay.

Trong chương này, bạn sẽ cho API đơn hàng của cửa hàng:

- Một bước [phân loại](/ai/overview#structured-output) email hỗ trợ thành một object có type, và một bản nháp phản hồi, với một model nhanh và rẻ.
- [Retry, timeout và một fallback model](/ai/models#retries-timeouts-and-fallback) quanh mọi lời gọi, một [ngân sách](/ai/models#usage-cost-and-budgets) cho mỗi lời gọi, và bản ghi chi phí của từng lời gọi.
- Các [agent function](/ai/tools) mà model gọi với tư cách khách hàng đã đăng nhập, trong đó có `find-order`, thứ mà MCP server của cửa hàng cũng phục vụ: một method, hai bên dùng.
- Một [chat assistant](/ai/agents#streaming-to-the-browser) có câu trả lời được stream tới trình duyệt ngay khi đang viết.
- Một [refund agent](/ai/agents#durable-agent-runs) chờ bộ phận hỗ trợ phê duyệt, dưới dạng một durable workflow.
- [Embedding](/ai/embeddings) cho phần mô tả sản phẩm, để tìm kiếm sản phẩm theo ý nghĩa.
- Các [test](/ai/testing) chạy được mà không cần model provider.

#### Cài đặt <a id="installation"></a>

Cài package, `@nestjs/resilience`, nơi các lời gọi model chạy trên policy của nó, AI SDK, một package provider, và Zod, cho các schema:

```bash
$ npm i --save @nestjs/ai @nestjs/resilience ai @ai-sdk/anthropic zod
```

> info **Gợi ý** Mọi package provider `@ai-sdk/*` đều hoạt động theo cùng cách: `@ai-sdk/openai`, `@ai-sdk/google`, `@ai-sdk/mistral`, `@ai-sdk/amazon-bedrock` và các package khác. Schema có thể đến từ bất kỳ library [Standard Schema](https://standardschema.dev) nào tạo ra được JSON Schema, như với `@nestjs/mcp`: Zod 4.2 trở lên và ArkType dùng được ngay, Valibot qua `toStandardJsonSchema()`. Mỗi major version của `@nestjs/ai` hỗ trợ một major version của AI SDK, với phiên bản này là `ai` 7, và nó cần Node.js 22 trở lên, giống AI SDK.

#### Đăng ký model <a id="register-the-models"></a>

Import `AiModule` trong root module, cùng các model mà ứng dụng dùng, theo tên. Các lời gọi không chỉ định model sẽ dùng `default`:

```typescript
@@filename(app.module)
import { anthropic } from '@ai-sdk/anthropic';
import { Module } from '@nestjs/common';
import { AiModule } from '@nestjs/ai';
import { SupportModule } from './support/support.module';

@Module({
  imports: [
    AiModule.forRoot({
      isGlobal: true,
      models: {
        default: anthropic('claude-opus-5-5'),
        fast: {
          model: anthropic('claude-haiku-5-5'),
          fallback: 'default',
        },
      },
      defaults: { timeout: '30s', retry: { attempts: 3 } },
    }),
    SupportModule,
  ],
})
export class AppModule {}
```

Một model là thứ mà một package provider trả về, chẳng hạn `anthropic('claude-opus-5-5')`, hoặc một định nghĩa có nó làm `model` cùng các thiết lập riêng: `fallback`, các model được thử khi nó thất bại, `pricing`, `timeout`, `retry`, và các thiết lập sinh như `maxOutputTokens`. `defaults` áp dụng cho mọi lời gọi: ở đây, một lần thử được phép mất 30 giây, và mỗi model có ba lần thử. [Model](/ai/models) mô tả mọi thiết lập.

Package provider đọc API key từ môi trường, `ANTHROPIC_API_KEY` với `@ai-sdk/anthropic`. Để truyền nó từ `ConfigService` thay vào đó, hãy tạo provider trong một factory: xem [Cấu hình bất đồng bộ](/ai/overview#async-configuration).

`isGlobal: true` cho phép mọi module của ứng dụng inject `AiService`. Không có nó, module không phải là global: `AiService` chỉ được inject trong module import `AiModule.forRoot()`. Để dùng chung một cấu hình chỉ với một số module, hãy import nó trong một module riêng của bạn có export nó, và import module đó ở nơi gọi model:

```typescript
@@filename(llm/llm.module)
import { anthropic } from '@ai-sdk/anthropic';
import { Module } from '@nestjs/common';
import { AiModule } from '@nestjs/ai';

@Module({
  imports: [
    AiModule.forRoot({ models: { default: anthropic('claude-opus-5-5') } }),
  ],
  exports: [AiModule],
})
export class LlmModule {}
```

#### Gọi một model <a id="calling-a-model"></a>

`AiService` thực hiện các lời gọi. `generateText()` gửi một prompt, kèm `instructions` (system prompt), và resolve với câu trả lời:

```typescript
@@filename(support/replies.service)
import { Injectable } from '@nestjs/common';
import { AiService } from '@nestjs/ai';

@Injectable()
export class RepliesService {
  constructor(private readonly ai: AiService) {}

  async draft(email: string): Promise<string> {
    const { text } = await this.ai.generateText({
      model: 'fast',
      label: 'draft-reply',
      instructions:
        'Draft a short, friendly reply to the customer. ' +
        'Sign it "The Cat Store".',
      prompt: email,
      maxOutputTokens: 400,
    });
    return text;
  }
}
```

`model` chỉ định một trong các model của module, mặc định là `default` khi bỏ trống, còn `label` đặt tên cho lời gọi trong [usage event](/ai/models#usage-cost-and-budgets) và trong các event của các policy của nó. `prompt` là message của người dùng; `messages` nhận cả một cuộc hội thoại thay vào đó, dưới dạng các object `ModelMessage` của AI SDK (xem [Hội thoại](/ai/agents#conversations)). Kết quả có nhiều thứ hơn là đoạn text:

| Thuộc tính | Là gì |
| --- | --- |
| `text` | Câu trả lời: đoạn text của lời gọi model cuối cùng |
| `finishReason` | Tại sao model dừng: `'stop'`, `'length'` khi nó chạm `maxOutputTokens`, hoặc `'tool-calls'` khi nó vẫn yêu cầu tool sau `maxSteps` lời gọi model |
| `usage` | Số token của mọi lời gọi model, cộng dồn: `inputTokens`, `outputTokens`, `totalTokens`, `cachedInputTokens` và `reasoningTokens` |
| `cost` | Chi phí của lời gọi, với các model có `pricing` |
| `steps` | Mỗi lời gọi model một phần tử, với đoạn text, các lời gọi tool, usage, và các lần thử mà nó đã cần |
| `toolCalls`, `toolResults` | Các tool mà model đã gọi, kèm input của chúng, và những gì mỗi tool trả về hoặc lý do nó thất bại |
| `responseMessages` | Các message assistant và tool của lời gọi, để nối vào một cuộc hội thoại |
| `model` | Model đã trả lời: `name`, `provider` và `modelId` của nó |

Một lời gọi chỉ định một model mà module không cấu hình, một agent function không tồn tại, hoặc có cả `prompt` lẫn `messages`, sẽ bị từ chối với một `AiConfigurationError` trước khi bất cứ thứ gì được gửi đi.

#### Structured output

Phân loại một email là việc của `generateObject()`. Model được gửi JSON Schema của schema, và câu trả lời của nó được parse và validate theo schema, nên `object` có type theo schema đó:

```typescript
@@filename(support/triage.service)
import { Injectable } from '@nestjs/common';
import { AiService } from '@nestjs/ai';
import * as z from 'zod';

export const Triage = z.object({
  category: z
    .enum(['shipping', 'billing', 'product', 'other'])
    .describe('What the email is about'),
  orderId: z
    .string()
    .nullable()
    .describe('The order id it mentions, such as ord_123, or null'),
  urgent: z.boolean().describe('Whether the customer needs an answer today'),
});

@Injectable()
export class TriageService {
  constructor(private readonly ai: AiService) {}

  async triage(email: string) {
    const { object } = await this.ai.generateObject({
      model: 'fast',
      label: 'triage',
      schema: Triage,
      instructions:
        'You sort the support email of a store for cat food and supplies.',
      prompt: email,
    });
    return object; // { category, orderId, urgent }
  }
}
```

Model đọc các đoạn text `.describe()`, giống như nó đọc của một agent function: hãy nói rõ mỗi field nghĩa là gì, kèm một giá trị ví dụ. `schemaName` và `schemaDescription` đặt tên và mô tả object, cho các provider có chuyển chúng tới model. Ngoài `object`, kết quả có mọi thứ mà kết quả của `generateText()` có: `usage`, `cost`, `steps` và các thuộc tính còn lại.

Một câu trả lời không phải JSON, hoặc không khớp với schema, sẽ reject với `AiOutputError`, lỗi này mang theo `text` của model. Nó không được retry, và không có fallback model nào được thử: model đã trả lời rồi.

Các transform của schema chạy trên câu trả lời, trong khi model được gửi JSON Schema của phía input. Cửa hàng cũng trích xuất các dòng trong hóa đơn của nhà cung cấp, và muốn ngày đến hạn dưới dạng `Date`; model được yêu cầu trả về một chuỗi ngày ISO:

```typescript
@@filename(suppliers/invoices.service)
import { Injectable } from '@nestjs/common';
import { AiService } from '@nestjs/ai';
import * as z from 'zod';

const Invoice = z.object({
  number: z.string().describe('The invoice number, such as INV-2041'),
  total: z.number().describe('The total, in cents'),
  dueDate: z.iso.date().transform((value) => new Date(`${value}T00:00:00Z`)),
  lines: z.array(
    z.object({
      description: z.string(),
      amount: z.number().describe('In cents'),
    }),
  ),
});

@Injectable()
export class InvoicesService {
  constructor(private readonly ai: AiService) {}

  async extract(email: string) {
    const { object } = await this.ai.generateObject({
      label: 'invoice',
      schema: Invoice,
      schemaName: 'invoice',
      instructions: 'Extract the invoice from the email of a supplier.',
      prompt: email,
    });
    return object; // object.dueDate is a Date
  }
}
```

Cùng lời gọi đó hoạt động trong một queue job, nơi cửa hàng đọc hộp thư của các nhà cung cấp: code gọi model không thay đổi theo nơi nó chạy.

Với [tool](/ai/tools), model có thể tra cứu trước khi trả lời, và object là câu trả lời của lời gọi model cuối cùng. Một model vẫn đang gọi tool sau `maxSteps` lời gọi model thì chưa đưa ra object nào, nên lời gọi cũng reject với `AiOutputError`.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

`forRootAsync()` nhận các tùy chọn từ một factory, một `useClass` hoặc một provider `useExisting`. Ở đây, factory tạo provider với API key từ `ConfigService`:

```typescript
@@filename(app.module)
import { createAnthropic } from '@ai-sdk/anthropic';
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AiModule } from '@nestjs/ai';

@Module({
  imports: [
    ConfigModule.forRoot(),
    AiModule.forRootAsync({
      isGlobal: true,
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => {
        const anthropic = createAnthropic({
          apiKey: config.getOrThrow<string>('ANTHROPIC_API_KEY'),
        });
        return {
          models: {
            default: anthropic('claude-opus-5-5'),
            fast: { model: anthropic('claude-haiku-5-5'), fallback: 'default' },
          },
          defaults: { timeout: '30s' },
        };
      },
    }),
  ],
})
export class AppModule {}
```

Một provider `useClass` implement `AiOptionsFactory`, với `createAiOptions()` trả về các tùy chọn. `isGlobal` vẫn ở cấp ngoài cùng, `modelNames` và `embeddingModelNames` cũng vậy.

`@InjectModel()` (xem [Model](/ai/models#calling-the-ai-sdk-yourself)) cần một provider cho mỗi tên model mà nó inject, và `forRootAsync()` tạo các provider này trước khi factory của nó chạy: cho những tên mà `@InjectModel()` được thấy là yêu cầu khi module được định nghĩa, trong các class mà ứng dụng đã import tới lúc đó. Một class được load muộn hơn, chẳng hạn class của một [lazy-loaded module](/fundamentals/lazy-loading-modules), sẽ liệt kê tên của nó trong `modelNames: ['fast']`. Một tên mà không có gì cấu hình sẽ thất bại lúc khởi động, kèm tên của class đã yêu cầu nó.

#### Một package cho nhiều provider <a id="one-package-for-many-providers"></a>

Mỗi package provider `@ai-sdk/*` là thêm một dependency cần cài và giữ đồng bộ với `ai`. Phần lớn provider và gateway (OpenAI, Groq, Together, Fireworks, DeepSeek, OpenRouter, LiteLLM, Ollama, vLLM và các bên khác) cũng phục vụ OpenAI API, nên chỉ một package, `@ai-sdk/openai-compatible`, có thể tiếp cận tất cả:

```bash
$ npm i --save @ai-sdk/openai-compatible
```

Khi đó các provider trở thành dữ liệu thay vì dependency: hãy giữ base URL, API key và model ID của chúng trong một bảng database hoặc cấu hình của bạn, và dựng các model trong factory của `forRootAsync()`:

```typescript
@@filename(app.module)
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { Module } from '@nestjs/common';
import { AiModule } from '@nestjs/ai';
import { ProvidersModule } from './providers/providers.module';
import { ProvidersService } from './providers/providers.service';

@Module({
  imports: [
    AiModule.forRootAsync({
      isGlobal: true,
      imports: [ProvidersModule],
      inject: [ProvidersService],
      useFactory: async (providers: ProvidersService) => {
        // e.g. rows of { name, baseURL, apiKey, modelId }
        const rows = await providers.findAll();
        const models = Object.fromEntries(
          rows.map((row) => [
            row.name,
            createOpenAICompatible({
              name: row.name,
              baseURL: row.baseURL,
              apiKey: row.apiKey,
            })(row.modelId),
          ]),
        );
        return { models };
      },
    }),
  ],
})
export class AppModule {}
```

Factory chạy một lần, lúc khởi động, nên một dòng mới chỉ có hiệu lực khi ứng dụng restart. Một dòng phải được đặt tên `default`, cho các lời gọi không chỉ định model, và một bảng trống sẽ làm việc khởi động thất bại. Để dùng một dòng mà không cần restart, hãy dựng model khi bạn gọi nó và truyền nó làm `model` của lời gọi, model đó [không có thiết lập riêng](/ai/models#model-settings).

`createOpenAICompatible()` giả định server có ít khả năng nhất. Hãy đặt `supportsStructuredOutputs: true` cho một model chấp nhận JSON schema, nếu không [structured output](/ai/overview#structured-output) sẽ không gửi schema cho nó, và `includeUsage: true` để yêu cầu usage trên các lời gọi stream, thứ mà [ngân sách](/ai/models#usage-cost-and-budgets) dựa vào.

Hãy dùng một package `@ai-sdk/*` riêng khi bạn cần một tính năng mà OpenAI API không cung cấp, chẳng hạn prompt caching của Anthropic hay các thiết lập grounding của Google.

#### Tùy chọn của module <a id="module-options"></a>

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `models` | | Các model, theo tên: một `LanguageModel`, hoặc `{{ '{' }} model, ... {{ '}' }}` với các thiết lập bên dưới. Bắt buộc trừ khi `embeddingModels` có chỉ định một model |
| `models.*.fallback` | | Tên các model được thử, theo thứ tự, khi model này thất bại |
| `models.*.pricing` | | `input`, `output` và `cachedInput`: giá cho mỗi triệu token |
| `models.*.timeout`, `retry`, `resilience` | | Các policy riêng của model, thắng `defaults`, giống như các thiết lập sinh của nó |
| `defaults.timeout` | `'60s'` | Thời gian một lần thử được phép mất; `false` để không giới hạn |
| `defaults.retry` | 3 lần thử, từ `'1s'` | Các tùy chọn của `RetryPolicy`: `attempts`, `backoff` (`delay`, `factor`, `maxDelay`, `jitter`, hoặc một hàm), `retryIf`; `false` để không retry |
| `defaults.resilience` | | Một policy, hoặc tên một preset của `ResilienceService`, thay cho `retry` và `timeout` |
| `defaults.maxSteps` | `10` | Số lời gọi model mà một lời gọi thực hiện trong khi model còn yêu cầu tool, và một durable run (mặc định riêng của nó là `25`) |
| `defaults.budget` | | `maxTokens` và `maxCost`, cho mỗi lời gọi và mỗi durable run |
| `defaults.maxOutputTokens`, `temperature`, `providerOptions`, `headers` | | Được truyền cho model |
| `onUsage` | | Được gọi sau mỗi lời gọi model đã trả lời |
| `embeddingModels` | | Các [embedding model](/ai/embeddings), theo tên: một `EmbeddingModel`, hoặc `{{ '{' }} model, ... {{ '}' }}` với các thiết lập riêng |
| `embeddingDefaults` | | [Thiết lập của các lời gọi embedding](/ai/embeddings#embedding-settings), thứ mà `defaults` không áp dụng tới |
| `onEmbeddingUsage` | | Được gọi sau mỗi lời gọi embedding thành công |
| `include` | mọi module | Các module mà provider của chúng được tìm kiếm agent function |
| `isGlobal` | `false` | Module có phải là global hay không. Ở cấp ngoài cùng của `forRootAsync()` |
| `modelNames` | | Thêm các tên model mà `@InjectModel()` có thể inject, cho các class được load sau khi module được định nghĩa. Ở cấp ngoài cùng của `forRootAsync()` |
| `embeddingModelNames` | | Tương tự cho `@InjectEmbeddingModel()`. Ở cấp ngoài cùng của `forRootAsync()` |

Mọi tùy chọn của `defaults` cũng là tùy chọn của từng lời gọi, và giá trị của lời gọi sẽ thắng. `timeout`, `retry`, `resilience` và các thiết lập sinh cũng là thiết lập trong định nghĩa của một model, và chúng thắng `defaults`.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có [tại đây](https://github.com/nestjs/ai/tree/master/sample).
