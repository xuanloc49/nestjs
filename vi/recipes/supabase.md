### Supabase

Supabase cho một ứng dụng một database Postgres, chức năng đăng nhập, lưu trữ file và một API mà trình duyệt có thể gọi trực tiếp, bao phủ được rất nhiều thứ mà không cần backend. Những gì nó bỏ ngỏ là các công việc cần một secret, một lần retry hay một đồng hồ: Stripe webhook, scheduled job, queue, một admin API. Nest đảm nhận phần việc đó bên cạnh Supabase, trên cùng database và cho cùng người dùng.

| Ở lại Supabase | Đặt trong Nest |
| --- | --- |
| Đăng ký, đăng nhập và đặt lại mật khẩu | Kiểm tra ai đang gọi, và họ được làm gì |
| Postgres, migration của nó và row level security | Quy tắc nghiệp vụ, và các query trải qua nhiều bảng |
| Đọc và ghi từ trình duyệt mà row level security bao phủ | Mọi thứ cần secret: thanh toán, email, API khác |
| Storage và Realtime | Stripe webhook, scheduled job, queue và một admin API |

Trình duyệt tiếp tục gọi trực tiếp Supabase cho những gì row level security bao phủ, và gọi Nest bằng cùng access token cho phần còn lại.

Nếu tất cả những gì bạn cần là một hai hàm ngắn, [Edge Function](https://supabase.com/docs/guides/functions) có thể là đủ, không cần server nào phải vận hành. Chúng có [giới hạn về thời gian CPU và thời lượng](https://supabase.com/docs/guides/functions/limits) và không có chỗ để chạy worker của một queue, nên Nest phù hợp hơn khi bạn đã có job, queue hoặc nhiều route dùng chung code.

Recipe này xây dựng một ứng dụng như vậy trên Supabase stack chạy local, để bạn có thể chạy từng bước trong lúc đọc. [Module hoàn chỉnh](/recipes/supabase#the-finished-module) cho thấy các phần được nối với nhau thế nào.

#### Tạo các project <a id="create-the-projects"></a>

Stack local cần Docker.

```bash
$ npx @nestjs/cli new my-api
$ cd my-api
$ npx supabase init
$ npx supabase start
```

`npx supabase status -o env` in ra các URL và key của stack. Hãy đặt `API_URL`, `PUBLISHABLE_KEY`, `SECRET_KEY` và `DB_URL` vào `.env`, dưới những tên mà recipe này đọc:

```bash
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

> warning **Cảnh báo** Secret key bỏ qua row level security. Nó chỉ thuộc về server, và không bao giờ được đưa vào bất cứ thứ gì bạn ship cho trình duyệt hay ứng dụng di động.

> info **Gợi ý** Một project được host có cùng các key trong dashboard của nó. Supabase đang [deprecate](https://supabase.com/docs/guides/api/api-keys) các key cũ `anon` và `service_role` trước cuối năm 2026, nên hãy dùng hai key này.

Load `.env` bằng [`@nestjs/config`](/application/configuration):

```bash
$ npm i --save @nestjs/config
```

```typescript
@Module({
  imports: [ConfigModule.forRoot()],
})
export class AppModule {}
```

Giữ nó đứng đầu trong `imports`, vì các module bạn sẽ thêm sau nó đọc `process.env` ngay khi được khai báo. Một module được khai báo trong file khác đọc nó sớm hơn, khi file được import, nên hãy dùng `forRootAsync()` cho những gì bạn đăng ký ở đó.

#### Định nghĩa một bảng <a id="define-a-table"></a>

Schema vẫn nằm trong các migration của Supabase:

```bash
$ npx supabase migration new notes
```

Viết bảng vào file mà lệnh này tạo trong `supabase/migrations`, với một policy chỉ cho phép người dùng truy cập các dòng của chính họ. `auth.uid()` là người dùng sở hữu access token của request:

```sql
create table public.notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  body text not null
);

alter table public.notes enable row level security;

create policy "Users manage their own notes" on public.notes
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
```

Áp dụng nó vào database local:

```bash
$ npx supabase db reset
```

> warning **Cảnh báo** API của Supabase phục vụ các bảng trong schema `public` cho bất kỳ ai có publishable key, và key đó nằm trong code trình duyệt của bạn. Hãy bật row level security trên mọi bảng bạn tạo ở đó, kể cả những bảng chỉ Nest dùng. Khi đã bật mà không có policy nào, key đó không đọc được gì.

#### Xác minh token của Supabase <a id="verify-supabase-tokens"></a>

Supabase Auth ký một access token cho mỗi người dùng đã đăng nhập, và công bố các public key dùng để xác minh nó. [`@nestjs/authentication`](/security/authentication) có thể xác minh token từ một issuer khác, nên Nest không cần secret nào từ Supabase để biết ai đang gọi:

```bash
$ npm i --save @nestjs/authentication
```

```typescript
@@filename(supabase/supabase-auth)
import { Injectable } from '@nestjs/common';
import { AuthenticationRegistry, JwtBearerProvider, type JwtClaims } from '@nestjs/authentication';

export interface SupabaseUser {
  id: string;
  email?: string;
  role?: string;
}

@Injectable()
export class SupabaseAuth extends JwtBearerProvider<SupabaseUser> {
  constructor(registry: AuthenticationRegistry) {
    super({
      jwks: `${process.env.SUPABASE_URL}/auth/v1/.well-known/jwks.json`,
      issuer: `${process.env.SUPABASE_URL}/auth/v1`,
      audience: 'authenticated',
    });
    registry.registerProvider(this);
  }

  validate(claims: JwtClaims) {
    if (!claims.sub) {
      return null;
    }
    const { email, app_metadata } = claims as JwtClaims & {
      email?: string;
      app_metadata?: { role?: string };
    };
    return { id: claims.sub, email, role: app_metadata?.role };
  }
}
```

Role lấy từ `app_metadata`, thứ mà chỉ server của bạn mới thay đổi được. Một người dùng đã đăng nhập có thể tự thay đổi `user_metadata` của mình bằng `supabase.auth.updateUser()`, nên đừng bao giờ dựa vào nó để đưa ra quyết định.

Đăng ký module và provider:

```typescript
@Module({
  imports: [AuthenticationModule.forRoot({})],
  providers: [SupabaseAuth],
})
export class AppModule {}
```

Module đăng ký một global guard, nên giờ mọi route đều trả lời `401 Unauthorized` khi không có token hợp lệ, kể cả token có chữ ký sai, issuer hoặc audience khác, hoặc đã hết hạn. Đánh dấu một route vẫn mở bằng `@Public()`, và đọc người dùng bằng `@CurrentUser()`:

```typescript
@@filename(me/me.controller)
import { Controller, Get } from '@nestjs/common';
import { CurrentUser } from '@nestjs/authentication';
import type { SupabaseUser } from '../supabase/supabase-auth.js';

@Controller('me')
export class MeController {
  @Get()
  me(@CurrentUser() user: SupabaseUser) {
    return user;
  }
}
```

> info **Gợi ý** Một project vẫn dùng JWT secret cũ sẽ ký token bằng nó và không công bố key nào. Hãy truyền `key: process.env.SUPABASE_JWT_SECRET` thay cho `jwks`, cho tới khi bạn [chuyển sang signing key](https://supabase.com/docs/guides/auth/signing-keys).

#### Gọi Nest từ trình duyệt <a id="call-nest-from-the-browser"></a>

Trình duyệt gửi access token mà Supabase đã cấp cho nó. `getSession()` làm mới token khi nó đã hết hạn:

```typescript
const { data: { session } } = await supabase.auth.getSession();

const response = await fetch(`${API_URL}/me`, {
  headers: { Authorization: `Bearer ${session.access_token}` },
});
```

Nếu trình duyệt gọi Nest trên một origin khác, hãy [cho phép origin đó](/security/cors) khi ứng dụng khởi động:

```typescript
@@filename(main)
app.enableCors({ origin: process.env.WEB_ORIGIN });
```

#### Query với tư cách người dùng, hoặc với tư cách server <a id="query-as-the-user-or-as-the-server"></a>

`@supabase/supabase-js` là một client cho REST API của database. Hãy sinh type từ schema của bạn, để một query trên một bảng hoặc cột không tồn tại sẽ không biên dịch được, và chạy lại lệnh này sau mỗi migration:

```bash
$ npm i --save @supabase/supabase-js
$ npx supabase gen types typescript --local > src/supabase/database.types.ts
```

Tạo một client cho server, và mỗi request một client cho người dùng. Một client không giữ kết nối database nào, nên việc này rẻ:

```typescript
@@filename(supabase/supabase.service)
import { Injectable } from '@nestjs/common';
import { createClient } from '@supabase/supabase-js';
import type { Database } from './database.types.js';

const options = { auth: { persistSession: false, autoRefreshToken: false } };

@Injectable()
export class SupabaseService {
  /** Bypasses row level security. Only for what the server does on its own. */
  readonly admin = createClient<Database>(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SECRET_KEY!,
    options,
  );

  /** Queries as the user who sent the token, so row level security applies. */
  forUser(token: string) {
    return createClient<Database>(process.env.SUPABASE_URL!, process.env.SUPABASE_PUBLISHABLE_KEY!, {
      ...options,
      accessToken: async () => token,
    });
  }
}
```

Một decorator nhỏ đọc token mà guard đã xác minh:

```typescript
@@filename(supabase/access-token.decorator)
import { createParamDecorator, type ExecutionContext } from '@nestjs/common';

export const AccessToken = createParamDecorator((_: unknown, context: ExecutionContext) => {
  const { authorization } = context.switchToHttp().getRequest().headers;
  return authorization?.replace(/^Bearer /i, '');
});
```

Hãy ưu tiên `forUser()` trong một route hành động thay cho một người dùng. Các policy của bạn vẫn tiếp tục được áp dụng, nên một query quên bộ lọc vẫn chỉ trả về các dòng của người dùng đó, và một câu insert cho người khác sẽ bị từ chối:

```typescript
@@filename(notes/notes.controller)
import { Body, Controller, Get, Post } from '@nestjs/common';
import { CurrentUser } from '@nestjs/authentication';
import { AccessToken } from '../supabase/access-token.decorator.js';
import type { SupabaseUser } from '../supabase/supabase-auth.js';
import { SupabaseService } from '../supabase/supabase.service.js';

@Controller('notes')
export class NotesController {
  constructor(private readonly supabase: SupabaseService) {}

  @Get()
  async findAll(@AccessToken() token: string) {
    const { data, error } = await this.supabase.forUser(token).from('notes').select('body');
    if (error) {
      throw error;
    }
    return data;
  }

  @Post()
  async create(
    @AccessToken() token: string,
    @CurrentUser() user: SupabaseUser,
    @Body('body') body: string,
  ) {
    const { error } = await this.supabase.forUser(token).from('notes').insert({ user_id: user.id, body });
    if (error) {
      throw error;
    }
  }
}
```

Dùng `admin` cho những gì server tự làm, nơi không có người dùng nào liên quan, như trong một job hoặc một webhook.

#### Query trực tiếp Postgres <a id="query-postgres-directly"></a>

Với transaction và các query mà REST API không diễn đạt được, hãy kết nối tới database bằng [`@nestjs/drizzle`](/data/drizzle) hoặc một [tích hợp database](/data/overview) khác. Các webhook và job bên dưới cũng dùng kết nối này:

```bash
$ npm i --save @nestjs/drizzle drizzle-orm pg
```

```typescript
DrizzleModule.forRoot({ drizzle, connection: process.env.DATABASE_URL! }),
```

Ở local, `DATABASE_URL` là `DB_URL` của stack. Trên một project được host, Nest là một backend chạy liên tục, nên hãy dùng [connection string trực tiếp](https://supabase.com/docs/guides/database/connecting-to-postgres), hoặc shared pooler ở session mode nếu host của bạn chỉ có IPv4. Transaction mode của pooler không hỗ trợ prepared statement, cũng không hỗ trợ `LISTEN` mà backend PostgreSQL của BullMQ dùng.

Các migration của Supabase vẫn là nguồn sự thật, nên Drizzle schema chỉ mô tả các bảng cần query:

```typescript
@@filename(database/schema)
import { pgTable, text, uuid } from 'drizzle-orm/pg-core';

export const notes = pgTable('notes', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').notNull(),
  body: text('body').notNull(),
});
```

> warning **Cảnh báo** Row level security không bảo vệ các query này. Role `postgres` bỏ qua nó, nên một query không có bộ lọc sẽ trả về các dòng của mọi người dùng, và mỗi query phải tự kiểm tra chủ sở hữu.

Để giữ các policy của bạn trên một query trực tiếp, hãy chạy nó trong một transaction với role `authenticated`, kèm các claim mà `auth.uid()` đọc:

```typescript
@@filename(database/row-level-security)
import { Injectable } from '@nestjs/common';
import type { JwtClaims } from '@nestjs/authentication';
import { InjectDrizzle } from '@nestjs/drizzle';
import { sql } from 'drizzle-orm';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';

type Transaction = Parameters<Parameters<NodePgDatabase['transaction']>[0]>[0];

@Injectable()
export class RowLevelSecurity {
  constructor(@InjectDrizzle() private readonly db: NodePgDatabase) {}

  asUser<T>(claims: JwtClaims, work: (tx: Transaction) => Promise<T>): Promise<T> {
    return this.db.transaction(async (tx) => {
      await tx.execute(sql`
        select set_config('request.jwt.claims', ${JSON.stringify(claims)}, true),
               set_config('role', 'authenticated', true)
      `);
      return work(tx);
    });
  }
}
```

Cả hai thiết lập đều kết thúc cùng transaction, nên chúng không bao giờ ảnh hưởng tới query tiếp theo trên kết nối đó. Đây là từng cách đặt cạnh nhau, với `@CurrentSession()` cung cấp cho route các claim đã được xác minh:

```typescript
@@filename(notes/notes.repository)
import { Injectable } from '@nestjs/common';
import type { JwtClaims } from '@nestjs/authentication';
import { InjectDrizzle } from '@nestjs/drizzle';
import { eq } from 'drizzle-orm';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';
import { RowLevelSecurity } from '../database/row-level-security.js';
import { notes } from '../database/schema.js';
import type { SupabaseUser } from '../supabase/supabase-auth.js';

@Injectable()
export class NotesRepository {
  constructor(
    @InjectDrizzle() private readonly db: NodePgDatabase,
    private readonly rls: RowLevelSecurity,
  ) {}

  /** Checks the owner itself. */
  findAll(user: SupabaseUser) {
    return this.db.select({ body: notes.body }).from(notes).where(eq(notes.userId, user.id));
  }

  /** Leaves the owner to the table's policy. */
  findAllAsUser(claims: JwtClaims) {
    return this.rls.asUser(claims, (tx) => tx.select({ body: notes.body }).from(notes));
  }
}
```

#### Bảo vệ một admin API <a id="protect-an-admin-api"></a>

Một admin API là thứ mà trình duyệt không tự làm được, vì nó cần secret key. Hãy giữ role của người dùng trong `app_metadata`, thứ mà `SupabaseAuth` đã đọc, và đặt nó từ server:

```typescript
await supabase.admin.auth.admin.updateUserById(userId, {
  app_metadata: { role: 'admin' },
});
```

Role nằm trong token tiếp theo của người dùng, nên một người đã đăng nhập sẽ có nó khi token của họ được làm mới, mặc định trong vòng một giờ.

Kiểm tra nó bằng [`@nestjs/authorization`](/security/authorization):

```bash
$ npm i --save @nestjs/authorization
```

```typescript
@@filename(admin/admin.policy)
import { Policy } from '@nestjs/authorization';
import type { SupabaseUser } from '../supabase/supabase-auth.js';

@Policy()
export class AdminPolicy {
  manage(user: SupabaseUser | null) {
    return user?.role === 'admin';
  }
}
```

```typescript
@@filename(admin/admin-users.controller)
import { Controller, Get, UseGuards } from '@nestjs/common';
import { AuthorizationGuard, Can } from '@nestjs/authorization';
import { SupabaseService } from '../supabase/supabase.service.js';
import { AdminPolicy } from './admin.policy.js';

@UseGuards(AuthorizationGuard)
@Can(AdminPolicy, 'manage')
@Controller('admin/users')
export class AdminUsersController {
  constructor(private readonly supabase: SupabaseService) {}

  @Get()
  async findAll() {
    const { data, error } = await this.supabase.admin.auth.admin.listUsers();
    if (error) {
      throw error;
    }
    return data.users.map(({ id, email }) => ({ id, email }));
  }
}
```

Đăng ký module bằng `AuthorizationModule.forRoot({{ '{' }} globalGuard: false {{ '}' }})`, và `AdminPolicy` trong `providers`. Global guard của nó được bật mặc định và từ chối mọi route không có `@Can()`, điều này cũng sẽ đóng các route ở trên. Một khách nhận `401`, một người dùng không có role nhận `403`.

#### Nhận Stripe webhook <a id="receive-stripe-webhooks"></a>

[`@nestjs/webhooks`](/http/webhooks) xác minh chữ ký của một webhook và ghi nhớ những event nào nó đã xử lý. Nó giữ trạng thái trong database của bạn, qua `@nestjs/outbox`, trong các schema riêng. API của Supabase không phục vụ các schema đó, nên chúng vẫn là riêng tư:

```bash
$ npm i --save @nestjs/webhooks @nestjs/outbox
```

Chữ ký bao phủ chính xác các byte mà Stripe đã gửi, nên hãy tạo ứng dụng với `rawBody`:

```typescript
@@filename(main)
const app = await NestFactory.create(AppModule, { rawBody: true });
```

Khai báo bên gửi trong `receivers` của module, với signing secret lấy từ dashboard Stripe hoặc từ `stripe listen`. Ứng dụng này chỉ nhận webhook, nên nó không cần background worker nào:

```typescript
OutboxModule.forRoot({ relay: { enabled: false } }),
WebhooksModule.forRoot({
  worker: { enabled: false },
  receivers: {
    stripe: { scheme: 'stripe', secret: process.env.STRIPE_WEBHOOK_SECRET! },
  },
}),
```

Đăng ký hai store trong `providers`. `migrate: true` tạo các schema của chúng lúc khởi động, phù hợp cho development (xem [Deployment](/recipes/supabase#deployment) cho production):

```typescript
{
  provide: PostgresOutboxStore,
  inject: [getDrizzleToken(), OutboxStorage],
  useFactory: (db: NodePgDatabase, storage: OutboxStorage) =>
    new PostgresOutboxStore({ executor: fromDrizzle(db), migrate: true }, storage),
},
{
  provide: PostgresWebhookStore,
  inject: [getDrizzleToken(), WebhooksStorage],
  useFactory: (db: NodePgDatabase, storage: WebhooksStorage) =>
    new PostgresWebhookStore({ executor: fromDrizzle(db), migrate: true }, storage),
},
```

Thêm một bảng cho những gì webhook thay đổi. Chỉ Nest đọc nó, và row level security không có policy giữ nó khỏi trình duyệt. Thêm nó vào một migration mới:

```sql
create table public.subscriptions (
  stripe_customer text primary key,
  active boolean not null,
  expires_at timestamptz
);

alter table public.subscriptions enable row level security;
```

```typescript
@@filename(database/schema)
import { boolean, pgTable, text, timestamp } from 'drizzle-orm/pg-core';

export const subscriptions = pgTable('subscriptions', {
  stripeCustomer: text('stripe_customer').primaryKey(),
  active: boolean('active').notNull(),
  expiresAt: timestamp('expires_at', { withTimezone: true }),
});
```

Route là `@Public()`, vì chữ ký là thứ xác thực nó, và một chữ ký không hợp lệ sẽ nhận `401`. `processInTransaction()` ghi lại id của event trong cùng transaction với thay đổi của bạn, nên một lần gửi lại không thay đổi gì:

```typescript
@@filename(billing/stripe-webhooks.controller)
import { Controller, HttpCode, Post } from '@nestjs/common';
import { Public } from '@nestjs/authentication';
import { InjectDrizzle } from '@nestjs/drizzle';
import { IncomingWebhook, VerifyWebhook } from '@nestjs/webhooks';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';
import { subscriptions } from '../database/schema.js';

interface StripeEvent {
  id: string;
  type: string;
  data: { object: { customer: string; status: string; cancel_at: number | null } };
}

@Public()
@Controller('webhooks/stripe')
export class StripeWebhooksController {
  constructor(@InjectDrizzle() private readonly db: NodePgDatabase) {}

  @Post()
  @HttpCode(200)
  @VerifyWebhook('stripe')
  async receive(@IncomingWebhook() webhook: IncomingWebhook<StripeEvent>) {
    const { type, data } = webhook.payload;
    if (type !== 'customer.subscription.updated') {
      return;
    }
    const { customer, status, cancel_at } = data.object;
    const values = {
      active: status === 'active',
      expiresAt: cancel_at ? new Date(cancel_at * 1000) : null,
    };
    await this.db.transaction(async (tx) =>
      webhook.processInTransaction(tx, async () => {
        await tx
          .insert(subscriptions)
          .values({ stripeCustomer: customer, ...values })
          .onConflictDoUpdate({ target: subscriptions.stripeCustomer, set: values });
      }),
    );
  }
}
```

Để chạy thử, hãy chuyển tiếp event tới ứng dụng bằng [Stripe CLI](https://docs.stripe.com/stripe-cli), công cụ này in ra signing secret để đặt vào `STRIPE_WEBHOOK_SECRET`:

```bash
$ stripe listen --forward-to localhost:3000/webhooks/stripe
$ stripe trigger customer.subscription.updated
```

#### Chạy scheduled job <a id="run-scheduled-jobs"></a>

Có hai cách để chạy một job trong Nest. Cả hai đều hoạt động trên bất kỳ số instance nào, và mỗi lần chạy diễn ra trên một instance:

|  | `@nestjs/schedule` với `@nestjs/locks` | BullMQ |
| --- | --- | --- |
| **Chạy ở đâu** | Trong instance đang giữ lease | Trong một worker nhận job |
| **Nếu một lần chạy thất bại** | Nó chờ tick tiếp theo | Nó retry, kèm backoff |
| **Nếu mọi instance đều down** | Tick bị lỡ | Job chờ trong queue |
| **Thêm gì vào Postgres** | Một bảng | Một schema riêng |
| **Nó làm thêm gì** | Không gì khác | Job được đưa vào queue từ code của bạn, độ ưu tiên và flow |
| **Chọn nó cho** | Một job an toàn khi bỏ qua, vì tick tiếp theo sẽ bù lại | Một job không được mất, hoặc chạy lâu |

Cả hai đều có thể gọi cùng một đoạn code:

```typescript
@@filename(billing/subscriptions.service)
import { Injectable } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import { and, eq, lt } from 'drizzle-orm';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';
import { subscriptions } from '../database/schema.js';

@Injectable()
export class SubscriptionsService {
  constructor(@InjectDrizzle() private readonly db: NodePgDatabase) {}

  /** Catches a subscription whose cancellation event never arrived. */
  async expireOverdue() {
    await this.db
      .update(subscriptions)
      .set({ active: false })
      .where(and(eq(subscriptions.active, true), lt(subscriptions.expiresAt, new Date())));
  }
}
```

> info **Gợi ý** [Supabase Cron](https://supabase.com/docs/guides/cron) lên lịch SQL bên trong Postgres, không có ứng dụng nào tham gia. Nó rất hợp với một job chỉ toàn SQL, như xóa các dòng cũ.

##### Với `@nestjs/schedule` và `@nestjs/locks` <a id="with-nestjsschedule-and-nestjslocks"></a>

[`@nestjs/schedule`](/application/task-scheduling) chạy một job bên trong ứng dụng, cạnh đoạn code mà nó gọi. Đứng riêng, nó chạy job trên mọi instance. [`@nestjs/locks`](/reliability/locks) thêm `@OnOneInstance()`: instance đầu tiên kích hoạt sẽ lấy một lease và chạy mọi tick chừng nào nó còn sống, còn các instance khác bỏ qua chúng. Khi nó dừng, một instance khác tiếp quản, khoảng một giây sau một lần shutdown bình thường và trong vòng 30 giây sau một lần crash:

```bash
$ npm i --save @nestjs/schedule @nestjs/locks
```

```typescript
@@filename(billing/expire-subscriptions.job)
import { Injectable } from '@nestjs/common';
import { OnOneInstance } from '@nestjs/locks';
import { Cron, CronExpression } from '@nestjs/schedule';
import { SubscriptionsService } from './subscriptions.service.js';

@Injectable()
export class ExpireSubscriptionsJob {
  constructor(private readonly subscriptions: SubscriptionsService) {}

  @Cron(CronExpression.EVERY_HOUR)
  @OnOneInstance({ key: 'subscriptions:expire' })
  async run() {
    await this.subscriptions.expireOverdue();
  }
}
```

```typescript
ScheduleModule.forRoot(),
LocksModule.forRoot(),
```

Lease phải nằm ở nơi mà mọi instance dùng chung, và trong production ứng dụng từ chối khởi động nếu chỉ có store trong bộ nhớ mặc định. Hãy giữ nó trong database của bạn, với một bảng trong một migration mới:

```sql
create table public.locks (
  key text primary key,
  owner text,
  fencing_token bigint not null,
  expires_at timestamptz not null
);

alter table public.locks enable row level security;

create sequence public.locks_fencing_token_seq;
```

Sau đó copy bảng Drizzle và `DrizzleLockStore` từ [Giữ lock trong database của bạn](/reliability/locks#keep-locks-in-your-database), và thêm store vào `providers`.

##### Với BullMQ <a id="with-bullmq"></a>

[BullMQ](/application/queues) giữ job trong một queue, kèm retry và backoff. Nó thường chạy trên Redis, và cũng có một backend PostgreSQL, nên trên Supabase nó có thể dùng database bạn đã có:

```bash
$ npm i --save @nestjs/bullmq bullmq
```

```typescript
BullModule.forRoot({
  backendFactory: createPostgresBackend,
  connection: { connectionString: process.env.DATABASE_URL!, migrate: true },
}),
BullModule.registerQueue({ name: 'billing' }),
```

`migrate: true` tạo schema `bullmq` lúc khởi động, schema mà API của Supabase không phục vụ. Migration lấy một advisory lock, nên nhiều instance khởi động cùng lúc chỉ áp dụng nó một lần.

> info **Gợi ý** Để dùng Redis, hãy cài `ioredis` và thay các tùy chọn đó bằng `connection: {{ '{' }} host, port {{ '}' }}`. Không có gì khác thay đổi.

Một job scheduler tạo job ở mỗi tick. Id giúp nó là một lịch chạy duy nhất, bất kể có bao nhiêu instance khai báo nó:

```typescript
@@filename(billing/billing.scheduler)
import { InjectQueue } from '@nestjs/bullmq';
import { Injectable, type OnApplicationBootstrap } from '@nestjs/common';
import type { Queue } from 'bullmq';

@Injectable()
export class BillingScheduler implements OnApplicationBootstrap {
  constructor(@InjectQueue('billing') private readonly billing: Queue) {}

  async onApplicationBootstrap() {
    await this.billing.upsertJobScheduler(
      'expire-subscriptions',
      { pattern: '0 * * * *' },
      {
        name: 'expire-subscriptions',
        opts: { attempts: 3, backoff: { type: 'exponential', delay: 1000 } },
      },
    );
  }
}
```

Processor chạy nó, trên bất kỳ instance nào đang rảnh:

```typescript
@@filename(billing/billing.processor)
import { Processor, WorkerHost } from '@nestjs/bullmq';
import type { Job } from 'bullmq';
import { SubscriptionsService } from './subscriptions.service.js';

@Processor('billing')
export class BillingProcessor extends WorkerHost {
  constructor(private readonly subscriptions: SubscriptionsService) {
    super();
  }

  async process(job: Job) {
    if (job.name === 'expire-subscriptions') {
      await this.subscriptions.expireOverdue();
    }
  }
}
```

Cùng queue đó nhận job từ code của bạn, chẳng hạn một route không nên chờ việc gửi email. Inject nó bằng `@InjectQueue('billing')`, và thêm một case cho job vào processor:

```typescript
await this.billing.add('send-invoice', { customer }, {
  attempts: 3,
  backoff: { type: 'exponential', delay: 1000 },
});
```

#### Cấp quyền upload file <a id="hand-out-file-uploads"></a>

Một trình duyệt có thể upload trực tiếp lên Supabase Storage, dưới các policy trên bảng `storage.objects`. Khi quyết định thuộc về server, như một hạn mức hoặc một gói trả phí, hãy giữ bucket ở chế độ riêng tư và để Nest ký cho từng lần upload. Tạo bucket trong một migration:

```sql
insert into storage.buckets (id, name, public) values ('uploads', 'uploads', false);
```

```typescript
@@filename(uploads/uploads.controller)
import { randomUUID } from 'node:crypto';
import { Controller, Post } from '@nestjs/common';
import { CurrentUser } from '@nestjs/authentication';
import type { SupabaseUser } from '../supabase/supabase-auth.js';
import { SupabaseService } from '../supabase/supabase.service.js';

@Controller('uploads')
export class UploadsController {
  constructor(private readonly supabase: SupabaseService) {}

  @Post()
  async create(@CurrentUser() user: SupabaseUser) {
    const path = `${user.id}/${randomUUID()}`;
    const { data, error } = await this.supabase.admin.storage.from('uploads').createSignedUploadUrl(path);
    if (error) {
      throw error;
    }
    return { path: data.path, token: data.token };
  }
}
```

Sau đó trình duyệt upload thẳng lên Supabase, nên file không bao giờ đi qua ứng dụng của bạn:

```typescript
await supabase.storage.from('uploads').uploadToSignedUrl(path, token, file);
```

Để trả một file về, `createSignedUrl(path, 60)` trên admin client tạo một link hoạt động trong 60 giây.

#### Test với stack local <a id="test-against-the-local-stack"></a>

Một end-to-end test có thể dùng token thật và các policy thật của bạn, vì stack cung cấp cả hai. Hãy đặt nó trong `test/`, và chạy `npx supabase start` cùng `npx supabase db reset` trước khi chạy test:

```typescript
@@filename(notes.e2e-spec)
import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { createClient } from '@supabase/supabase-js';
import { randomUUID } from 'node:crypto';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';
import { SupabaseService } from '../src/supabase/supabase.service.js';

describe('Notes', () => {
  let app: INestApplication;

  const signUp = async () => {
    const client = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_PUBLISHABLE_KEY!, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data, error } = await client.auth.signUp({
      email: `${randomUUID()}@example.test`,
      password: randomUUID(),
    });
    if (error) {
      throw error;
    }
    return { id: data.user!.id, token: data.session!.access_token };
  };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = moduleRef.createNestApplication();
    await app.init();
  });

  afterAll(() => app.close());

  it('shows a user only their own notes', async () => {
    const [alice, bob] = [await signUp(), await signUp()];
    await app.get(SupabaseService).admin.from('notes').insert([
      { user_id: alice.id, body: 'from alice' },
      { user_id: bob.id, body: 'from bob' },
    ]);

    const { body } = await request(app.getHttpServer())
      .get('/notes')
      .set('Authorization', `Bearer ${alice.token}`)
      .expect(200);

    expect(body).toEqual([{ body: 'from alice' }]);
  });
});
```

#### Chuyển một Edge Function sang Nest <a id="move-an-edge-function-to-nest"></a>

Phần lớn một function đều có thành phần tương ứng trực tiếp, và bạn có thể chuyển chúng từng cái một, vì cả hai dùng cùng token và database:

| Trong một Edge Function | Trong Nest |
| --- | --- |
| Đọc header `Authorization` và gọi `supabase.auth.getUser()` | `SupabaseAuth` và `@CurrentUser()` |
| Một client được tạo với header của bên gọi | `SupabaseService.forUser()` |
| Một client được tạo với secret key | `SupabaseService.admin` |
| Tự xác minh chữ ký của Stripe bằng tay | `@VerifyWebhook('stripe')` |
| `pg_cron` gọi function qua HTTP | `@Cron()`, hoặc một job scheduler của BullMQ |
| `supabase secrets set` | Biến môi trường của host |
| `supabase.functions.invoke('name')` trên trình duyệt | `fetch()` kèm access token |

#### Module hoàn chỉnh <a id="the-finished-module"></a>

Đây là mọi thứ ở trên được nối lại với nhau, với cả hai cách chạy job, bạn sẽ giữ một trong hai:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { AuthenticationModule } from '@nestjs/authentication';
import { AuthorizationModule } from '@nestjs/authorization';
import { BullModule } from '@nestjs/bullmq';
import { ConfigModule } from '@nestjs/config';
import { DrizzleModule, getDrizzleToken } from '@nestjs/drizzle';
import { LocksModule } from '@nestjs/locks';
import { OutboxModule, OutboxStorage } from '@nestjs/outbox';
import { PostgresOutboxStore } from '@nestjs/outbox/postgres';
import { ScheduleModule } from '@nestjs/schedule';
import { WebhooksModule, WebhooksStorage } from '@nestjs/webhooks';
import { fromDrizzle, PostgresWebhookStore } from '@nestjs/webhooks/postgres';
import { createPostgresBackend } from 'bullmq';
import { drizzle, type NodePgDatabase } from 'drizzle-orm/node-postgres';
import { AdminUsersController } from './admin/admin-users.controller.js';
import { AdminPolicy } from './admin/admin.policy.js';
import { BillingProcessor } from './billing/billing.processor.js';
import { BillingScheduler } from './billing/billing.scheduler.js';
import { ExpireSubscriptionsJob } from './billing/expire-subscriptions.job.js';
import { StripeWebhooksController } from './billing/stripe-webhooks.controller.js';
import { SubscriptionsService } from './billing/subscriptions.service.js';
import { DrizzleLockStore } from './database/drizzle-lock.store.js';
import { RowLevelSecurity } from './database/row-level-security.js';
import { MeController } from './me/me.controller.js';
import { NotesController } from './notes/notes.controller.js';
import { NotesRepository } from './notes/notes.repository.js';
import { SupabaseAuth } from './supabase/supabase-auth.js';
import { SupabaseService } from './supabase/supabase.service.js';
import { UploadsController } from './uploads/uploads.controller.js';

@Module({
  imports: [
    ConfigModule.forRoot(), // first, as the lines below read process.env
    AuthenticationModule.forRoot({}),
    AuthorizationModule.forRoot({ globalGuard: false }),
    DrizzleModule.forRoot({ drizzle, connection: process.env.DATABASE_URL! }),
    OutboxModule.forRoot({ relay: { enabled: false } }),
    WebhooksModule.forRoot({
      worker: { enabled: false },
      receivers: {
        stripe: { scheme: 'stripe', secret: process.env.STRIPE_WEBHOOK_SECRET! },
      },
    }),
    // Jobs with @nestjs/schedule and @nestjs/locks
    ScheduleModule.forRoot(),
    LocksModule.forRoot(),
    // Jobs with BullMQ
    BullModule.forRoot({
      backendFactory: createPostgresBackend,
      connection: { connectionString: process.env.DATABASE_URL!, migrate: true },
    }),
    BullModule.registerQueue({ name: 'billing' }),
  ],
  controllers: [
    MeController,
    NotesController,
    AdminUsersController,
    StripeWebhooksController,
    UploadsController,
  ],
  providers: [
    SupabaseAuth,
    SupabaseService,
    RowLevelSecurity,
    NotesRepository,
    AdminPolicy,
    SubscriptionsService,
    {
      provide: PostgresOutboxStore,
      inject: [getDrizzleToken(), OutboxStorage],
      useFactory: (db: NodePgDatabase, storage: OutboxStorage) =>
        new PostgresOutboxStore({ executor: fromDrizzle(db), migrate: true }, storage),
    },
    {
      provide: PostgresWebhookStore,
      inject: [getDrizzleToken(), WebhooksStorage],
      useFactory: (db: NodePgDatabase, storage: WebhooksStorage) =>
        new PostgresWebhookStore({ executor: fromDrizzle(db), migrate: true }, storage),
    },
    // Jobs with @nestjs/schedule and @nestjs/locks
    ExpireSubscriptionsJob,
    DrizzleLockStore,
    // Jobs with BullMQ
    BillingScheduler,
    BillingProcessor,
  ],
})
export class AppModule {}
```

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, { rawBody: true });
  app.enableCors({ origin: process.env.WEB_ORIGIN });
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

`enableShutdownHooks()` cho phép một job đang chạy hoàn tất và chuyển lease của nó đi khi một lần deploy dừng một instance.

#### Deployment

Nest được deploy riêng với Supabase, trên bất cứ thứ gì chạy được Node.js (xem [Deployment](/deployment)). Hãy host nó gần region của database, vì mọi query đều phải đi qua khoảng cách đó.

Áp dụng các migration lên project được host:

```bash
$ npx supabase link --project-ref your-project-ref
$ npx supabase db push
```

Đặt cùng các biến môi trường trên host của bạn, với giá trị của project được host và connection string từ [Query trực tiếp Postgres](/recipes/supabase#query-postgres-directly). Mỗi instance mở các kết nối riêng, cho Drizzle và cho BullMQ, nên hãy tính chúng vào [giới hạn kết nối](https://supabase.com/docs/guides/database/connection-management) của project.

Các webhook store không nên thay đổi schema trong lúc một phiên bản mới đang boot, giữa một lần rolling deploy. Hãy bỏ `migrate: true` khỏi hai store đó, và áp dụng migration của chúng như một bước trước khi phiên bản mới khởi động, với `DATABASE_URL` được đặt. Migration của BullMQ có thể giữ nguyên, vì nó chạy trong một transaction dưới một advisory lock:

```bash
$ npx @nestjs/webhooks migrate
$ npx @nestjs/outbox migrate
```
