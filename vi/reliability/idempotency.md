### Idempotency key

`@nestjs/idempotency` giúp route, GraphQL mutation và message handler an toàn khi retry: mỗi `Idempotency-Key` chỉ chạy handler một lần, và các lần retry nhận lại kết quả của nó.

Một khách hàng của cửa hàng online bán thức ăn và đồ dùng cho mèo thanh toán hạt cá hồi và cát vệ sinh trong ứng dụng di động của cửa hàng, trên điện thoại khi đang đi tàu. Ứng dụng gửi `POST /orders/ord_1001/pay`. Server trừ tiền thẻ qua payment provider, nhưng response không bao giờ tới được điện thoại. Ứng dụng không thể phân biệt request bị mất với response bị mất, nên nó retry. Không có cơ chế bảo vệ, lần retry sẽ hỏng theo một trong hai cách:

- Nó tới sau khi request đầu tiên đã xong. Đơn hàng đã ở trạng thái `paid`, nên khách hàng nhận lỗi cho một lần thanh toán đã thành công.
- Nó tới trong khi request đầu tiên vẫn đang chờ payment provider. Cả hai request đều vượt qua bước kiểm tra "đơn hàng có còn pending không?", và thẻ bị trừ tiền hai lần.

Một **idempotency key** giải quyết cả hai. Client sinh một key duy nhất cho mỗi lần thử thanh toán và gửi nó trong header `Idempotency-Key` ở mọi lần retry. Server chạy handler một lần cho mỗi key, lưu kết quả, và trả lời mọi lần retry bằng kết quả đó. `@nestjs/idempotency` hiện thực điều này cho HTTP route, GraphQL mutation và microservice handler chỉ với một decorator, `@Idempotent()`. Hành vi HTTP của nó tuân theo [bản nháp header Idempotency-Key](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) của IETF.

Trong bài hướng dẫn này, bạn sẽ làm endpoint thanh toán trở nên idempotent, hướng dẫn ứng dụng di động retry an toàn, chuyển key sang PostgreSQL (hoặc Redis), mã hóa các biên lai được lưu, bảo vệ GraphQL mutation, và khử trùng lặp các event `order.paid` mà service vận chuyển tiêu thụ.

#### Yêu cầu trước <a id="prerequisites"></a>

Bài hướng dẫn này bắt đầu từ API đơn hàng của cửa hàng, vốn đã có:

- Một `OrdersModule` với `OrdersService` và `OrdersController`. Một `Order` có `id`, `userId`, `items`, `total` tính bằng cent, và `status` là `'pending'`, `'paid'`, `'shipped'` hoặc `'refunded'`.
- Một `PaymentProviderClient` bọc SDK của payment provider. Nó throw một `HttpException` 402 khi thẻ bị từ chối, và một `ServiceUnavailableException` (503) khi provider bị down.
- Một `AuthGuard` validate bearer token và đặt `req.user` (xem [Xác thực](/security/authentication#issue-tokens-to-the-mobile-app)), cùng một parameter decorator `@CurrentUser()` để đọc nó.
- Một `ValidationPipe` global, và một TCP client cho service vận chuyển, được đăng ký dưới tên `SHIPPING_SERVICE`.
- Dữ liệu của nó nằm trong PostgreSQL, qua Drizzle, với database được đăng ký bằng `@nestjs/drizzle` (xem [Drizzle](/data/drizzle)). Dùng TypeORM? [Lưu key trong PostgreSQL](/reliability/idempotency#store-keys-in-postgresql) có phần store cho TypeORM ở cuối.

Đây là method mà chúng ta cần bảo vệ:

```typescript
@@filename(orders/orders.service)
async pay(orderId: string, user: User, dto: PayOrderDto): Promise<PaymentReceipt> {
  const order = this.ordersRepository.findOwned(orderId, user.id);
  if (order.status !== 'pending') {
    throw new ConflictException(`Order ${order.id} is already ${order.status}`);
  }
  const charge = await this.paymentProviderClient.charge({
    amount: order.total,
    paymentMethod: dto.paymentMethod,
    reference: order.id,
  });
  this.ordersRepository.markPaid(order.id);
  this.shipping.emit('order.paid', {
    eventId: `order-paid:${order.id}`,
    orderId: order.id,
  });

  return {
    orderId: order.id,
    receiptId: charge.id,
    amount: charge.amount,
    cardLast4: charge.cardLast4,
    paidAt: charge.createdAt,
  };
}
```

Riêng bước kiểm tra status không thể ngăn việc trừ tiền hai lần: hai request tới cùng lúc đều thấy `pending` trước khi một trong hai tới được `markPaid()`.

Cài đặt package:

```bash
$ npm i --save @nestjs/idempotency
```

#### Làm endpoint thanh toán trở nên idempotent <a id="make-the-payment-endpoint-idempotent"></a>

Đăng ký `IdempotencyModule` một lần, trong root module:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { IdempotencyModule } from '@nestjs/idempotency';
import type { User } from './orders/order.js';
import { OrdersModule } from './orders/orders.module.js';

@Module({
  imports: [
    IdempotencyModule.forRoot({
      // Runs after guards, so req.user is set. Keys never collide across users.
      scope: (req: { user?: User }) => req.user?.id,
    }),
    OrdersModule,
  ],
})
export class AppModule {}
```

Module này là global. Nó đăng ký một interceptor cho toàn ứng dụng, interceptor này không làm gì với các handler không được đánh dấu `@Idempotent()`, nên không route nào khác bị thay đổi hành vi.

`scope` cho key của mỗi người dùng một namespace riêng. Không có nó, mọi client dùng chung một namespace, và một key mà người dùng này chọn có thể replay biên lai của người dùng khác. Có nó, Alice và Bob đều có thể gửi `Idempotency-Key: 1` mà không bao giờ thấy kết quả của nhau. Vì guard chạy trước interceptor, `req.user` đã được đặt khi `scope` chạy, và một request chưa xác thực bị từ chối trước khi nó có thể dùng mất một key. Nếu một người dùng đã đăng nhập gọi một handler `@Idempotent()` không có `scope`, module sẽ log một cảnh báo, một lần cho mỗi handler. Ở những nơi cố ý dùng chung một namespace, chẳng hạn một webhook dùng event id của provider làm key, hãy đặt `scope: false`.

Giờ hãy đánh dấu handler:

```typescript
@@filename(orders/orders.controller)
import { Body, Controller, Param, Post, UseGuards } from '@nestjs/common';
import { Idempotent } from '@nestjs/idempotency';
import { AuthGuard } from '../auth/auth.guard.js';
import { CurrentUser } from '../auth/current-user.decorator.js';
import { PayOrderDto } from './dto/pay-order.dto.js';
import type { User } from './order.js';
import { OrdersService } from './orders.service.js';

@Controller('orders')
@UseGuards(AuthGuard)
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Post(':id/pay')
  @Idempotent({ required: true })
  pay(
    @Param('id') id: string,
    @Body() dto: PayOrderDto,
    @CurrentUser() user: User,
  ) {
    return this.ordersService.pay(id, user, dto);
  }
}
```

`required: true` từ chối một request không có key bằng lỗi 400 `IDEMPOTENCY_KEY_REQUIRED`, trước khi handler chạy. Một lần thanh toán không có key thì không thể retry an toàn, nên từ chối nó tốt hơn là trừ tiền thẻ mà không có bảo vệ.

Đây là những gì xảy ra với một request có mang key:

1. Interceptor tính một **fingerprint** của request: một hash SHA-256 của scope, method, URL (bao gồm id đơn hàng) và body, với các key của object được sắp xếp.
2. Nó lấy lock một cách nguyên tử trên **record key** `<scope>:<key>`, ví dụ `usr_alice:5e0f6d0e-…`. Nếu một record đã tồn tại, handler không chạy (xem bảng bên dưới). Trong khi handler chạy, interceptor liên tục gia hạn lock, nên một handler chậm không bao giờ bị một lần retry giành mất lock.
3. Handler chạy. Khi nó xong, lock trở thành một record đã hoàn tất chứa response: status code, body, và các header từ một allowlist ngắn (`Location`, `Content-Type`, `Content-Language`, `Content-Location`, `ETag` và `Last-Modified`) nếu handler hoặc một middleware đã đặt chúng. Chúng mô tả body được lưu, nên một lần retry gửi kèm `Accept-Language` khác vẫn nhận `Content-Language` của body đã lưu. Cookie, header CORS và header rate-limit thuộc về request gốc và không bao giờ được replay.

Mỗi request sau đó với cùng key sẽ nhận một trong các câu trả lời sau:

| Tình huống                             | Response                                                                                |
| -------------------------------------- | --------------------------------------------------------------------------------------- |
| Request đầu tiên vẫn đang chạy         | 409 `IDEMPOTENCY_KEY_IN_USE`, kèm header `Retry-After`                                  |
| Request đầu tiên đã hoàn tất           | Status và body đã lưu, cộng `Idempotent-Replayed: true`. Handler không chạy.            |
| Cùng key, nhưng body hoặc URL khác     | 422 `IDEMPOTENCY_KEY_REUSED`                                                            |

Lỗi cũng có thể được lưu. [Tinh chỉnh TTL và cách xử lý thất bại](/reliability/idempotency#tune-ttls-and-failure-handling) nói về những lỗi nào.

Vì interceptor là global, nó chạy bên ngoài các interceptor của controller và handler của bạn. Body được lưu chính xác là những gì client đã nhận, sau khi serializer và các interceptor khác đã chạy, và một lần replay bỏ qua tất cả chúng. Pipe chạy bên trong nó, nên một lỗi 400 từ `ValidationPipe` được lưu như mọi lỗi client khác. Các global interceptor khác thì lại là chuyện khác, như checklist cho production giải thích.

Cho tới khi bạn [lưu key trong PostgreSQL](/reliability/idempotency#store-keys-in-postgresql), các record nằm trong bộ nhớ, trong `InMemoryIdempotencyStore` mặc định. Như vậy ổn cho một instance duy nhất khi phát triển, nhưng mỗi instance của API có record riêng, và chúng mất khi restart. Khi `NODE_ENV` là `production`, ứng dụng từ chối khởi động theo cách này, kèm một lỗi cho biết cách đăng ký store.

#### Gửi key từ ứng dụng di động <a id="send-keys-from-the-mobile-app"></a>

Server chỉ có thể khử trùng lặp những gì client gửi một cách nhất quán. Ứng dụng tuân theo hai quy tắc:

- Nó tạo key khi khách hàng bấm **Pay**, chứ không phải mỗi request một lần. Mọi lần retry của lần thanh toán đó đều gửi cùng key, kể cả sau khi ứng dụng bị kill và khởi động lại, nên key được lưu cùng lần thanh toán đang chờ.
- Nó chỉ tạo key mới khi khách hàng đưa ra một quyết định mới, chẳng hạn chọn thẻ khác sau khi bị từ chối. Gửi một key cũ với body khác sẽ nhận 422.

```typescript
@@filename(mobile/pay-order)
export interface Receipt {
  orderId: string;
  receiptId: string;
  amount: number;
  cardLast4: string;
  paidAt: string;
}

export interface PendingPayment {
  orderId: string;
  paymentMethod: string;
  idempotencyKey: string;
}

export class PaymentError extends Error {
  constructor(
    readonly status: number,
    readonly body: { code?: string; message?: string },
  ) {
    super(body.message ?? `Payment failed with status ${status}`);
  }
}

// Call when the customer taps "Pay", and save the result with the order
// (for example in AsyncStorage). Retries, even after an app restart, reuse it.
export function startPayment(orderId: string, paymentMethod: string): PendingPayment {
  return { orderId, paymentMethod, idempotencyKey: crypto.randomUUID() };
}

export async function payOrder(
  apiUrl: string,
  token: string,
  payment: PendingPayment,
  maxAttempts = 5,
): Promise<Receipt> {
  for (let attempt = 1; ; attempt++) {
    const backoff = 250 * 2 ** (attempt - 1);
    let res: Response;
    try {
      res = await fetch(`${apiUrl}/orders/${payment.orderId}/pay`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Idempotency-Key': payment.idempotencyKey,
        },
        body: JSON.stringify({ paymentMethod: payment.paymentMethod }),
        signal: AbortSignal.timeout(15_000),
      });
    } catch (err) {
      // No response: the card may or may not have been charged. Same key, try again.
      if (attempt >= maxAttempts) {
        throw err;
      }
      await sleep(backoff);
      continue;
    }
    if (res.ok) {
      return res.json(); // the first result, even if Idempotent-Replayed: true
    }
    const body = await res.json().catch(() => ({})); // a proxy's 502 page isn't JSON
    const retryable =
      res.status >= 500 || // the server released the key
      res.status === 429 ||
      body.code === 'IDEMPOTENCY_KEY_IN_USE'; // the first attempt is still running
    if (!retryable || attempt >= maxAttempts) {
      throw new PaymentError(res.status, body);
    }
    const retryAfter = Number(res.headers.get('Retry-After'));
    await sleep(retryAfter > 0 ? retryAfter * 1000 : backoff);
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
```

`crypto.randomUUID()` có sẵn trong trình duyệt và Node.js. Trong React Native, hãy dùng một library UUID, chẳng hạn `randomUUID()` từ `expo-crypto`.

Đây là những response mà ứng dụng có thể nhận, và ý nghĩa của chúng đối với việc retry:

| Response                                                      | Ý nghĩa                                                                  | Retry với cùng key?                               |
| ------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------- |
| Không có response (lỗi mạng, timeout)                         | Thẻ có thể đã hoặc chưa bị trừ tiền                                      | Có                                                |
| 2xx                                                           | Xong. Nếu có `Idempotent-Replayed: true`, đó là kết quả của lần thử đầu tiên | Không, hiển thị biên lai                      |
| 409 với code `IDEMPOTENCY_KEY_IN_USE`                         | Lần thử đầu tiên vẫn đang chạy                                           | Có, sau `Retry-After` giây                        |
| 5xx                                                           | Lần thử thất bại, và server đã giải phóng key                            | Có, kèm backoff                                   |
| 429                                                           | Bị rate limit trước khi handler chạy                                     | Có, sau `Retry-After` giây                        |
| 422 `IDEMPOTENCY_KEY_REUSED`                                  | Một bug: key bị dùng lại cho một request khác                            | Không                                             |
| Mọi 4xx khác: 400, 402 (bị từ chối), 404, 409 (đã thanh toán) | Kết quả cuối cùng. Mọi lần retry với key này đều nhận cùng câu trả lời   | Không. Hiển thị lỗi; lần thử mới sẽ có key mới    |

Hãy kiểm tra `code`, không chỉ status. Một 409 cũng có thể nghĩa là đơn hàng đã được thanh toán, và trường hợp đó là kết quả cuối cùng.

#### Lưu key trong PostgreSQL <a id="store-keys-in-postgresql"></a>

Store trong bộ nhớ không đủ cho production. Các record của nó biến mất mỗi khi process dừng, ở mỗi lần deploy hoặc thay container, nên một lần retry tới sau đó sẽ chạy lại việc thanh toán. Và khi API chạy trên nhiều instance, một lần retry rơi vào instance khác sẽ không tìm thấy record, và hai instance có thể cùng lấy được lock. Các record cần một store dùng chung có thể "tạo nếu chưa tồn tại" một cách nguyên tử.

`@nestjs/idempotency` không đi kèm store nào. Nó định nghĩa hợp đồng, interface `IdempotencyStore`, và bạn implement nó trong một provider của ứng dụng, bằng database hoặc Redis client mà ứng dụng đã có. Interface có bốn method. Mỗi method nhận record key và một owner trước tiên, và các khoảng thời gian được truyền vào dưới dạng số mili giây nguyên:

- `acquire(key, owner, fingerprint, lockTtl)` tạo lock, hoặc trả về record đã tồn tại: đang xử lý, hoặc đã hoàn tất kèm response. Nó phải nguyên tử: trong bất kỳ số lời gọi đồng thời nào cho một key còn trống, chỉ đúng một lời gọi được thắng.
- `complete(key, owner, response, ttl)` biến lock thành một record đã hoàn tất, nếu `owner` vẫn đang giữ nó.
- `release(key, owner)` xóa lock, nếu `owner` vẫn đang giữ nó, để một lần retry có thể chạy lại handler.
- `extend(key, owner, lockTtl)` đặt lại thời hạn của lock thành `lockTtl` tính từ bây giờ, nếu `owner` vẫn đang giữ nó. Interceptor gọi nó mỗi `lockTtl / 3` trong khi handler chạy và kết quả của nó đang được lưu.

`owner` là một id ngẫu nhiên cho mỗi lần thử, gọi là fencing token. Nếu một lần thử ngừng gia hạn lock (chẳng hạn instance của nó bị crash) và một lần retry tiếp quản sau `lockTtl`, các lời gọi `extend()`, `complete()` hay `release()` của lần thử cũ sẽ không làm gì cả, thay vì ghi đè lên record của lần retry. Vì vậy điều kiện "nếu `owner` vẫn đang giữ nó" phải được kiểm tra trong cùng thao tác nguyên tử thực hiện việc ghi: nếu kiểm tra bằng một lần đọc riêng trước đó, một lần tiếp quản có thể chen vào giữa.

Phần này trình bày store đó hai lần: đầu tiên với Drizzle, là lộ trình của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối phần, cùng store đó cho một ứng dụng dùng TypeORM làm ORM. Hãy chọn một trong hai.

Store giữ dữ liệu trong PostgreSQL, với Drizzle, nên các record có một bảng trong Drizzle schema:

```typescript
@@filename(database/schema)
import type { IdempotencyStoredPayload } from '@nestjs/idempotency';
import { bigint, index, json, pgTable, text } from 'drizzle-orm/pg-core';

/** One row per idempotency record: an in-flight lock, or a completed response. */
export const idempotencyKeys = pgTable(
  'idempotency_keys',
  {
    // SHA-256 of the record key: keys can be longer than an index entry allows.
    keyHash: text('key_hash').primaryKey(),
    key: text('key').notNull(),
    fingerprint: text('fingerprint').notNull(),
    // The attempt holding the lock; null once the record is completed.
    owner: text('owner'),
    // null while in flight. json, not jsonb: jsonb rejects "\u0000" in strings.
    response: json('response').$type<IdempotencyStoredPayload>(),
    // Epoch milliseconds.
    expiresAt: bigint('expires_at', { mode: 'number' }).notNull(),
  },
  (table) => [index('idempotency_keys_expires_at_idx').on(table.expiresAt)],
);
```

Primary key là một hash SHA-256 của record key, vì record key (một scope, key của client và, với GraphQL, đường dẫn của field) có thể dài hơn mức PostgreSQL cho phép trong một entry của index. Response dùng `json` thay vì `jsonb`, vì `jsonb` từ chối `\u0000` bên trong một chuỗi, và body của response có thể chứa ký tự đó. Tạo migration bằng drizzle-kit, và áp dụng nó bằng `npx drizzle-kit migrate` như thường lệ:

```bash
$ npx drizzle-kit generate --name=idempotency
```

```sql
@@filename(drizzle/0000_idempotency.sql)
CREATE TABLE "idempotency_keys" (
	"key_hash" text PRIMARY KEY NOT NULL,
	"key" text NOT NULL,
	"fingerprint" text NOT NULL,
	"owner" text,
	"response" json,
	"expires_at" bigint NOT NULL
);
--> statement-breakpoint
CREATE INDEX "idempotency_keys_expires_at_idx" ON "idempotency_keys" USING btree ("expires_at");
```

Store implement mỗi method bằng query builder của Drizzle. Nó inject database bằng `@InjectDrizzle()` từ `@nestjs/drizzle`, và constructor đăng ký store với `IdempotencyStorage`, một registry mà `IdempotencyModule` export:

```typescript
@@filename(idempotency/drizzle-idempotency.store)
import { Injectable } from '@nestjs/common';
import { InjectDrizzle } from '@nestjs/drizzle';
import {
  IdempotencyStorage,
  type IdempotencyAcquireResult,
  type IdempotencyStore,
  type IdempotencyStoredPayload,
} from '@nestjs/idempotency';
import { and, eq, gt, inArray, lte } from 'drizzle-orm';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';
import { createHash } from 'node:crypto';
import { idempotencyKeys } from '../database/schema.js';

export type Database = NodePgDatabase;

const { keyHash, owner: ownerColumn, expiresAt } = idempotencyKeys;

@Injectable()
export class DrizzleIdempotencyStore implements IdempotencyStore {
  constructor(
    @InjectDrizzle() private readonly db: Database,
    storage: IdempotencyStorage,
  ) {
    storage.registerSource(this);
  }

  async acquire(
    key: string,
    owner: string,
    fingerprint: string,
    lockTtl: number,
  ): Promise<IdempotencyAcquireResult> {
    const hash = hashOf(key);
    // A second round only happens when the row was released or expired
    // between the two statements below.
    for (let attempt = 0; attempt < 5; attempt++) {
      const now = Date.now();
      const lock = { fingerprint, owner, response: null, expiresAt: now + lockTtl };
      // Insert the lock, or take over an expired row. Of many concurrent
      // callers, PostgreSQL lets one write, and re-checks `setWhere` for the
      // others against the winner's row: they get no row back.
      const taken = await this.db
        .insert(idempotencyKeys)
        .values({ keyHash: hash, key, ...lock })
        .onConflictDoUpdate({
          target: keyHash,
          set: lock,
          setWhere: lte(expiresAt, now),
        })
        .returning({ keyHash });
      if (taken.length) {
        return { state: 'acquired' };
      }

      // Someone else holds the key: report their lock or record.
      const [row] = await this.db
        .select()
        .from(idempotencyKeys)
        .where(eq(keyHash, hash));
      if (row && row.expiresAt > now) {
        return row.response === null
          ? { state: 'in-flight', fingerprint: row.fingerprint }
          : { state: 'completed', fingerprint: row.fingerprint, response: row.response };
      }
    }
    throw new Error(`The idempotency record for "${key}" kept changing; try again`);
  }

  async complete(
    key: string,
    owner: string,
    response: IdempotencyStoredPayload,
    ttl: number,
  ): Promise<boolean> {
    const now = Date.now();
    const done = await this.db
      .update(idempotencyKeys)
      .set({ owner: null, response, expiresAt: now + ttl })
      .where(this.ownedBy(key, owner, now))
      .returning({ keyHash });
    return done.length === 1;
  }

  async release(key: string, owner: string): Promise<boolean> {
    const released = await this.db
      .delete(idempotencyKeys)
      .where(this.ownedBy(key, owner, Date.now()))
      .returning({ keyHash });
    return released.length === 1;
  }

  async extend(key: string, owner: string, lockTtl: number): Promise<boolean> {
    const now = Date.now();
    const extended = await this.db
      .update(idempotencyKeys)
      .set({ expiresAt: now + lockTtl })
      .where(this.ownedBy(key, owner, now))
      .returning({ keyHash });
    return extended.length === 1;
  }

  /**
   * Deletes up to `limit` expired rows, for a scheduled job. Expired rows are
   * already ignored, and reused by the next request with the same key.
   */
  async prune(limit = 1000): Promise<number> {
    const now = Date.now();
    const expired = this.db
      .select({ keyHash })
      .from(idempotencyKeys)
      .where(lte(expiresAt, now))
      .limit(limit);
    const deleted = await this.db
      .delete(idempotencyKeys)
      // Checks the expiry again: a row taken over since the subquery read it stays.
      .where(and(inArray(keyHash, expired), lte(expiresAt, now)))
      .returning({ keyHash });
    return deleted.length;
  }

  /** The caller's lock, if it still holds it and it hasn't expired. */
  private ownedBy(key: string, owner: string, now: number) {
    return and(eq(keyHash, hashOf(key)), eq(ownerColumn, owner), gt(expiresAt, now));
  }
}

function hashOf(key: string) {
  return createHash('sha256').update(key).digest('hex');
}
```

Database được gán type `NodePgDatabase`, và các test bên dưới ép kiểu database PGlite của chúng về type này, vì store chỉ dùng phần query builder mà cả hai driver đều có. Mỗi method là một câu lệnh duy nhất mà PostgreSQL chạy một cách nguyên tử, không cần transaction:

- `acquire()` insert lock, hoặc tiếp quản một dòng đã hết hạn, bằng một câu `INSERT ... ON CONFLICT DO UPDATE ... WHERE expires_at <= now`. Khi nhiều bên gọi tranh nhau một key, PostgreSQL để một bên ghi và kiểm tra lại `WHERE` cho các bên còn lại dựa trên dòng của bên thắng, nên chúng không nhận lại dòng nào và đọc lock của bên thắng thay vào đó. Nếu dòng đó biến mất ở giữa (bị giải phóng, hoặc hết hạn), `acquire()` sẽ chạy lại một vòng nữa.
- `complete()`, `extend()` và `release()` kiểm tra owner, và việc lock chưa hết hạn, trong `WHERE` của câu lệnh ghi. Chúng đếm số dòng mà `returning()` trả về, cách này hoạt động giống nhau trên mọi driver của Drizzle.
- Các dòng đã hết hạn bị bỏ qua ngay lập tức, và request tiếp theo với cùng key sẽ dùng lại dòng đó. Để xóa phần còn lại, hãy gọi `prune()` từ một scheduled job, ví dụ với `@Interval()` từ `@nestjs/schedule`. Nó kiểm tra lại thời hạn ngay trong câu `DELETE`, nên một dòng mà một lần retry đã tiếp quản trong lúc đó sẽ được giữ lại.

Thời điểm hết hạn lấy từ đồng hồ của mỗi instance (`Date.now()`), nên hãy giữ các đồng hồ được đồng bộ, như NTP làm. Mỗi request idempotent thêm một hoặc hai câu lệnh vào connection pool, cộng một câu `UPDATE` mỗi `lockTtl / 3` trong khi handler của nó chạy.

Store là một provider bình thường. Đăng ký database bằng `DrizzleModule` (xem [Drizzle](/data/drizzle)), và thêm store vào providers của `AppModule`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule } from '@nestjs/drizzle';
import { IdempotencyModule } from '@nestjs/idempotency';
import { drizzle } from 'drizzle-orm/node-postgres';
import { DrizzleIdempotencyStore } from './idempotency/drizzle-idempotency.store.js';
import type { User } from './orders/order.js';
import { OrdersModule } from './orders/orders.module.js';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL! }),
    }),
    IdempotencyModule.forRoot({
      scope: (req: { user?: User }) => req.user?.id,
    }),
    OrdersModule,
  ],
  // Registers itself with IdempotencyStorage when Nest creates it.
  providers: [DrizzleIdempotencyStore],
})
export class AppModule {}
```

> info **Gợi ý** Ứng dụng đọc `DATABASE_URL`, và khi biên lai được mã hóa thì cả `IDEMPOTENCY_KEYS`, từ `process.env`. Một ứng dụng thực tế load môi trường của nó qua `@nestjs/config`, với một validation schema dừng việc khởi động khi thiếu biến, và inject `ConfigService` vào các factory này thay vào đó.

Lúc khởi động, module log ra store mà nó dùng, `IdempotencyStorage: DrizzleIdempotencyStore`, và sau đó nó ngừng nhận đăng ký:

- Một ứng dụng chỉ có một store. Lời gọi `registerSource()` thứ hai sẽ throw, nêu tên cả hai class.
- Hãy đăng ký từ constructor của một singleton provider. Registry bị khóa khi `IdempotencyModule` khởi tạo, nên một store đăng ký muộn hơn (từ một lifecycle hook, theo từng request, hoặc trong một lazy-loaded module) sẽ throw thay vì bị âm thầm bỏ qua.
- Không có store nào được đăng ký, module giữ record trong bộ nhớ. Trong production (`NODE_ENV=production`), nó từ chối khởi động theo cách đó, trừ khi bạn đặt `allowInMemoryStorage: true`, tức chấp nhận rằng mỗi lần restart hoặc deploy đều quên sạch các record.

Mọi store đều được test bằng cùng một contract suite, được `@nestjs/idempotency/testing` export dưới dạng các test case thuần dùng được với mọi test runner. Nó bao gồm từng method, việc kiểm tra owner, thời hạn, và, với `concurrent`, các tình huống race mà một store kiểu đọc-rồi-ghi sẽ làm sai. Project ví dụ chạy nó trên store này với PGlite, và với PostgreSQL qua một `pg` pool, nơi 32 bên gọi tranh nhau mỗi key trên tối đa 16 kết nối:

```typescript
@@filename(test/step-3.drizzle-store.spec)
import { PGlite } from '@electric-sql/pglite';
import { IdempotencyStorage } from '@nestjs/idempotency';
import { idempotencyStoreContract } from '@nestjs/idempotency/testing';
import { drizzle as drizzlePglite } from 'drizzle-orm/pglite';
import { migrate as migratePglite } from 'drizzle-orm/pglite/migrator';
import { DrizzleIdempotencyStore, type Database } from '../src/idempotency/drizzle-idempotency.store.js';

const migrationsFolder = new URL('../drizzle', import.meta.url).pathname;
// ...
describe('DrizzleIdempotencyStore on PGlite', () => {
  let pglite: PGlite;
  let store: DrizzleIdempotencyStore;

  beforeAll(async () => {
    pglite = new PGlite();
    const db = drizzlePglite({ client: pglite });
    await migratePglite(db, { migrationsFolder }); // npx drizzle-kit migrate
    store = new DrizzleIdempotencyStore(db as unknown as Database, new IdempotencyStorage());
  });
  afterAll(() => pglite.close());

  describe('the IdempotencyStore contract', () => {
    // The store reads Date.now(): fake Date alone, so the driver keeps its timers.
    beforeEach(() => vi.useFakeTimers({ toFake: ['Date'] }));
    afterEach(() => vi.useRealTimers());

    // One store and one table for every case: each case uses keys of its own.
    const cases = idempotencyStoreContract(() => store, {
      advanceTime: (ms) => vi.setSystemTime(Date.now() + ms),
      concurrent: true,
    });
    for (const c of cases) {
      it(c.name, c.run);
    }
  });
  // ...
});
```

**Với TypeORM.** Cùng store đó cho một ứng dụng dùng TypeORM làm ORM, trên cùng bảng. Drizzle vẫn là lộ trình của bài hướng dẫn: hãy dùng store này thay cho store ở trên, chứ không phải dùng song song. Bảng là một entity, và mọi cột đều khai báo type của nó, để TypeORM CLI, vốn load entity mà không có decorator metadata, thấy cùng schema với ứng dụng:

```typescript
@@filename(typeorm/idempotency-key.entity)
import { Column, Entity, Index, PrimaryColumn } from 'typeorm';

// The idempotency_keys table of the Drizzle schema in src/database/schema.ts, as an entity.
// Every column states its type, so the entity loads the same with or without emitted
// decorator metadata (the TypeORM CLI runs it through tsx, which emits none).

/** Reads a `bigint` column as a number: TypeORM returns it as a string. */
const epochMs = {
  to: (value: number) => value,
  from: (value: string) => Number(value),
};

/** One row per idempotency record: an in-flight lock, or a completed response. */
@Entity('idempotency_keys')
@Index('idempotency_keys_expires_at_idx', ['expiresAt'])
export class IdempotencyKeyEntity {
  // SHA-256 of the record key: keys can be longer than an index entry allows.
  @PrimaryColumn({ type: 'text', name: 'key_hash' })
  keyHash: string;

  @Column({ type: 'text' })
  key: string;

  @Column({ type: 'text' })
  fingerprint: string;

  // The attempt holding the lock; null once the record is completed.
  @Column({ type: 'text', nullable: true })
  owner: string | null;

  // null while in flight. json, not jsonb: jsonb rejects "\u0000" in strings. An
  // IdempotencyStoredPayload, typed `object`: its `unknown` body doesn't fit TypeORM's insert types.
  @Column({ type: 'json', nullable: true })
  response: object | null;

  // Epoch milliseconds.
  @Column({ type: 'bigint', name: 'expires_at', transformer: epochMs })
  expiresAt: number;
}
```

TypeORM trả về cột `bigint` dưới dạng chuỗi, nên một transformer đọc lại `expiresAt` thành số. Cột response được gán type `object` thay vì `IdempotencyStoredPayload`, vì body kiểu `unknown` của payload không khớp với các type insert của TypeORM; store sẽ ép kiểu nó khi đọc một record. TypeORM CLI và `TypeOrmModule` dùng chung một bộ tùy chọn, trong một file data source:

```typescript
@@filename(typeorm/data-source)
import { DataSource, type DataSourceOptions } from 'typeorm';
import { IdempotencyKeyEntity } from './idempotency-key.entity.js';
import { Idempotency1790321611502 } from './migrations/1790321611502-Idempotency.js';

/** What the application's TypeOrmModule and the TypeORM CLI share. */
export const dataSourceOptions = {
  type: 'postgres',
  url: process.env.DATABASE_URL,
  entities: [IdempotencyKeyEntity],
  migrations: [Idempotency1790321611502],
} satisfies DataSourceOptions;

// The TypeORM CLI's data source: `migration:generate` compares the entities with this database.
export default new DataSource(dataSourceOptions);
```

Tạo migration từ entity, áp dụng nó, và kiểm tra rằng entity và database khớp nhau. CLI cần một TypeScript loader cho file data source; ở đây dùng `tsx`:

```bash
$ npx tsx ./node_modules/typeorm/cli.js migration:generate src/typeorm/migrations/Idempotency -d src/typeorm/data-source.ts --pretty
Migration /store/src/typeorm/migrations/1790321611502-Idempotency.ts has been generated successfully.
$ npx tsx ./node_modules/typeorm/cli.js migration:run -d src/typeorm/data-source.ts
$ npx tsx ./node_modules/typeorm/cli.js migration:generate src/typeorm/migrations/Check -d src/typeorm/data-source.ts --check
No changes in database schema were found
```

Migration mà nó tạo ra, `1790321611502-Idempotency.ts`, chính là các câu lệnh `CREATE TABLE` và `CREATE INDEX` của migration Drizzle, và `migrations` trong data source liệt kê nó. Giờ đến store, theo cùng các quy tắc với bản Drizzle:

```typescript
@@filename(typeorm/typeorm-idempotency.store)
import { Injectable } from '@nestjs/common';
import {
  IdempotencyStorage,
  type IdempotencyAcquireResult,
  type IdempotencyStore,
  type IdempotencyStoredPayload,
} from '@nestjs/idempotency';
import { createHash } from 'node:crypto';
import { DataSource, MoreThan } from 'typeorm';
import { IdempotencyKeyEntity } from './idempotency-key.entity.js';

/**
 * Keeps idempotency records in PostgreSQL, through TypeORM: the Drizzle
 * store, on the same table. Each method is a single statement, so the
 * guarantees hold with any number of API instances.
 */
@Injectable()
export class TypeOrmIdempotencyStore implements IdempotencyStore {
  constructor(
    private readonly dataSource: DataSource,
    storage: IdempotencyStorage,
  ) {
    storage.registerSource(this);
  }

  async acquire(
    key: string,
    owner: string,
    fingerprint: string,
    lockTtl: number,
  ): Promise<IdempotencyAcquireResult> {
    const hash = hashOf(key);
    // A second round only happens when the row was released or expired
    // between the two statements below.
    for (let attempt = 0; attempt < 5; attempt++) {
      const now = Date.now();
      // Insert the lock, or take over an expired row. Of many concurrent
      // callers, PostgreSQL lets one write, and re-checks the overwrite
      // condition for the others against the winner's row: they get no row back.
      const { raw } = await this.dataSource
        .createQueryBuilder()
        .insert()
        .into(IdempotencyKeyEntity)
        .values({ keyHash: hash, key, fingerprint, owner, response: null, expiresAt: now + lockTtl })
        .orUpdate(['fingerprint', 'owner', 'response', 'expires_at'], ['key_hash'], {
          overwriteCondition: { where: 'idempotency_keys.expires_at <= :now', parameters: { now } },
        })
        .returning(['keyHash'])
        .updateEntity(false)
        .execute();
      if ((raw as unknown[]).length === 1) {
        return { state: 'acquired' };
      }

      // Someone else holds the key: report their lock or record.
      const row = await this.dataSource.manager.findOneBy(IdempotencyKeyEntity, { keyHash: hash });
      if (row && row.expiresAt > now) {
        return row.response === null
          ? { state: 'in-flight', fingerprint: row.fingerprint }
          : { state: 'completed', fingerprint: row.fingerprint, response: row.response as IdempotencyStoredPayload };
      }
    }
    throw new Error(`The idempotency record for "${key}" kept changing; try again`);
  }

  async complete(
    key: string,
    owner: string,
    response: IdempotencyStoredPayload,
    ttl: number,
  ): Promise<boolean> {
    const now = Date.now();
    const { affected } = await this.dataSource.manager.update(IdempotencyKeyEntity, ownedBy(key, owner, now), {
      owner: null,
      response,
      expiresAt: now + ttl,
    });
    return affected === 1;
  }

  async release(key: string, owner: string): Promise<boolean> {
    const { affected } = await this.dataSource.manager.delete(IdempotencyKeyEntity, ownedBy(key, owner, Date.now()));
    return affected === 1;
  }

  async extend(key: string, owner: string, lockTtl: number): Promise<boolean> {
    const now = Date.now();
    const { affected } = await this.dataSource.manager.update(IdempotencyKeyEntity, ownedBy(key, owner, now), {
      expiresAt: now + lockTtl,
    });
    return affected === 1;
  }

  /**
   * Deletes up to `limit` expired rows, for a scheduled job. Expired rows are
   * already ignored, and reused by the next request with the same key.
   */
  async prune(limit = 1000): Promise<number> {
    const expired = this.dataSource.manager
      .createQueryBuilder(IdempotencyKeyEntity, 'expired')
      .select('expired.keyHash')
      .where('expired.expiresAt <= :now')
      .limit(limit);
    const { affected } = await this.dataSource
      .createQueryBuilder()
      .delete()
      .from(IdempotencyKeyEntity)
      .where(`key_hash IN (${expired.getQuery()})`)
      // Checks the expiry again: a row taken over since the subquery read it stays.
      .andWhere('expires_at <= :now', { now: Date.now() })
      .execute();
    return affected ?? 0;
  }
}

/** The caller's lock, if it still holds it and it hasn't expired. */
function ownedBy(key: string, owner: string, now: number) {
  return { keyHash: hashOf(key), owner, expiresAt: MoreThan(now) };
}

function hashOf(key: string) {
  return createHash('sha256').update(key).digest('hex');
}
```

- **`acquire()`** là cùng câu `INSERT ... ON CONFLICT DO UPDATE ... WHERE expires_at <= now`, thông qua insert query builder: `orUpdate()` liệt kê các cột mà một lần tiếp quản ghi đè, tùy chọn `overwriteCondition` của nó chính là `WHERE`, và `returning()` chỉ trả về một dòng cho bên gọi đã ghi.
- **`complete()`, `extend()` và `release()`** là `update()` và `delete()` trên entity manager, với owner và `MoreThan(now)` trong điều kiện của chúng, và chúng đọc `affected`. Không bao giờ dùng `save()`: nó đọc dòng trước, nên một lần tiếp quản có thể chen vào giữa.
- **`prune()`** dựng subquery chọn các dòng đã hết hạn bằng một select query builder, và đặt SQL của nó vào `WHERE` của câu `DELETE`, cạnh điều kiện kiểm tra thời hạn.

Store inject `DataSource` mà `TypeOrmModule` cung cấp. Đăng ký module với các tùy chọn của data source thay cho `DrizzleModule`, và store thay cho `DrizzleIdempotencyStore`:

```typescript
@@filename(typeorm/app.module)
import { Module } from '@nestjs/common';
import { IdempotencyModule } from '@nestjs/idempotency';
import { TypeOrmModule } from '@nestjs/typeorm';
import type { User } from '../orders/order.js';
import { OrdersModule } from '../orders/orders.module.js';
import { dataSourceOptions } from './data-source.js';
import { TypeOrmIdempotencyStore } from './typeorm-idempotency.store.js';

@Module({
  imports: [
    TypeOrmModule.forRootAsync({
      // The entity and migration the CLI uses; migrations run on deploy (`migration:run`).
      useFactory: () => ({ ...dataSourceOptions, url: process.env.DATABASE_URL }),
    }),
    IdempotencyModule.forRoot({
      scope: (req: { user?: User }) => req.user?.id,
    }),
    OrdersModule,
  ],
  // Registers itself with IdempotencyStorage when Nest creates it.
  providers: [TypeOrmIdempotencyStore],
})
export class AppModule {}
```

Contract suite chạy trên nó mà không cần thay đổi. TypeORM kết nối qua `pg`, nên suite cần một PostgreSQL server và sẽ bị bỏ qua nếu không có. Thêm một case nữa kiểm tra rằng entity và migration khớp nhau, đúng những gì `migration:generate --check` kiểm tra:

```typescript
@@filename(test/typeorm-idempotency.store.spec)
import { IdempotencyStorage } from '@nestjs/idempotency';
import { idempotencyStoreContract } from '@nestjs/idempotency/testing';
import { DataSource } from 'typeorm';
import { startPostgres } from '../../../test-support/postgres.js';
import { dataSourceOptions } from '../src/typeorm/data-source.js';
import { TypeOrmIdempotencyStore } from '../src/typeorm/typeorm-idempotency.store.js';
// ...
const { postgres, reason } = await startPostgres();
afterAll(() => postgres?.stop());

describe.skipIf(!postgres)(`TypeOrmIdempotencyStore on PostgreSQL${postgres ? '' : ` (skipped: ${reason})`}`, () => {
  let dataSource: DataSource;
  let url: string;
  let store: TypeOrmIdempotencyStore;

  beforeAll(async () => {
    url = await postgres!.createDatabase('idempotency_typeorm_store');
    dataSource = await new DataSource({ ...dataSourceOptions, url, poolSize: 16 }).initialize();
    await dataSource.runMigrations(); // npx typeorm migration:run
    store = new TypeOrmIdempotencyStore(dataSource, new IdempotencyStorage());
  });
  afterAll(() => dataSource?.destroy());

  describe('the IdempotencyStore contract', () => {
    // The store reads Date.now(): fake Date alone, so the driver keeps its timers.
    beforeEach(() => vi.useFakeTimers({ toFake: ['Date'] }));
    afterEach(() => vi.useRealTimers());

    // One store and one table for every case: each case uses keys of its own.
    // 32 callers per race, on up to 16 connections.
    const cases = idempotencyStoreContract(() => store, {
      advanceTime: (ms) => vi.setSystemTime(Date.now() + ms),
      concurrent: { callers: 32 },
    });
    for (const c of cases) {
      it(c.name, c.run);
    }
  });

  it('has a migration that matches the entity (what `migration:generate --check` checks)', async () => {
    const { upQueries } = await dataSource.driver.createSchemaBuilder().log();
    expect(upQueries.map((query) => query.query)).toEqual([]);
  });
  // ...
});
```

`startPostgres()` là một test helper tạo một database dùng một lần trên PostgreSQL server, hoặc bỏ qua suite nếu không có server. Ví dụ này cũng chạy hai instance của `AppModule` bản TypeORM trên một database, một instance đang trừ tiền trong khi instance kia trả lời 409.

> info **Gợi ý** Dùng Prisma? [Hợp đồng của store](/reliability/idempotency#the-store-contract), sau phần hướng dẫn, cho thấy Prisma diễn đạt các câu lệnh này thế nào. Hãy kiểm tra store của bạn bằng cùng suite đó.

#### Lưu key trong Redis <a id="store-keys-in-redis-instead"></a>

Nếu API của bạn đã chạy Redis, nó có thể giữ các record ở đó thay vì trong PostgreSQL. Redis rất hợp với store này: một record là một hash nhỏ mà Redis tự cho hết hạn, nên không cần job dọn dẹp, và một key nóng, chẳng hạn một client retry một lần thanh toán mỗi giây, chỉ tốn một vòng truy cập bộ nhớ thay vì một row lock trong database chính. Cái giá là phải vận hành, bảo vệ và backup thêm một store thứ hai, và Redis phải được cấu hình để không bao giờ evict các record (xem checklist cho production).

Mỗi method là một Lua script, được Redis chạy một cách nguyên tử:

```typescript
@@filename(idempotency/redis-idempotency.store)
import { Inject, Injectable } from '@nestjs/common';
import {
  IdempotencyStorage,
  type IdempotencyAcquireResult,
  type IdempotencyStore,
  type IdempotencyStoredPayload,
} from '@nestjs/idempotency';
import { REDIS } from '../redis/redis.module.js';

/** The one ioredis method this store needs. */
export interface RedisClient {
  eval(script: string, numKeys: number, ...args: (string | number)[]): Promise<unknown>;
}

// Creates the lock if no record exists. Otherwise returns the record, in the
// same round trip.
const ACQUIRE = `
if redis.call('EXISTS', KEYS[1]) == 0 then
  redis.call('HSET', KEYS[1], 'state', 'in-flight', 'fp', ARGV[1], 'owner', ARGV[2])
  redis.call('PEXPIRE', KEYS[1], ARGV[3])
  return {1}
end
local r = redis.call('HMGET', KEYS[1], 'state', 'fp', 'resp')
return {0, r[1], r[2], r[3]}
`;

// Turns our lock into a completed record, unless another attempt took it over.
const COMPLETE = `
if redis.call('HGET', KEYS[1], 'owner') ~= ARGV[1] then return 0 end
redis.call('HSET', KEYS[1], 'state', 'completed', 'resp', ARGV[2])
redis.call('HDEL', KEYS[1], 'owner')
redis.call('PEXPIRE', KEYS[1], ARGV[3])
return 1
`;

// Deletes the lock, but only if it is still ours.
const RELEASE = `
if redis.call('HGET', KEYS[1], 'owner') == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
`;

// Renews our lock while the handler runs, but only if it is still ours.
const EXTEND = `
if redis.call('HGET', KEYS[1], 'owner') ~= ARGV[1] then return 0 end
redis.call('PEXPIRE', KEYS[1], ARGV[2])
return 1
`;

type AcquireReply =
  | [1]
  | [0, 'in-flight' | 'completed', string, string | null];

@Injectable()
export class RedisIdempotencyStore implements IdempotencyStore {
  constructor(
    @Inject(REDIS) private readonly redis: RedisClient,
    storage: IdempotencyStorage,
  ) {
    storage.registerSource(this);
  }

  async acquire(
    key: string,
    owner: string,
    fingerprint: string,
    lockTtl: number,
  ): Promise<IdempotencyAcquireResult> {
    const reply = (await this.redis.eval(
      ACQUIRE, 1, this.key(key), fingerprint, owner, lockTtl,
    )) as AcquireReply;
    if (reply[0] === 1) {
      return { state: 'acquired' };
    }
    const [, state, storedFingerprint, response] = reply;
    return state === 'completed'
      ? { state, fingerprint: storedFingerprint, response: JSON.parse(response!) }
      : { state, fingerprint: storedFingerprint };
  }

  async complete(
    key: string,
    owner: string,
    response: IdempotencyStoredPayload,
    ttl: number,
  ): Promise<boolean> {
    const done = await this.redis.eval(
      COMPLETE, 1, this.key(key), owner, JSON.stringify(response), ttl,
    );
    return done === 1;
  }

  async release(key: string, owner: string): Promise<boolean> {
    const released = await this.redis.eval(RELEASE, 1, this.key(key), owner);
    return released === 1;
  }

  async extend(key: string, owner: string, lockTtl: number): Promise<boolean> {
    const extended = await this.redis.eval(EXTEND, 1, this.key(key), owner, lockTtl);
    return extended === 1;
  }

  private key(key: string) {
    return `idem:${key}`;
  }
}
```

Mỗi record là một hash tại `idem:<scope>:<key>`, với các field `state`, `fp` (fingerprint), `owner` và `resp` (response đã lưu dưới dạng JSON). Hash tự hết hạn: `lockTtl` sau lần gia hạn cuối khi đang xử lý, và sau `ttl` khi đã hoàn tất, nên không cần job dọn dẹp. Mỗi script chỉ chạm tới một key, nên store cũng hoạt động với Redis Cluster. Redis chạy một script một cách nguyên tử, nhưng nó không hoàn tác các thao tác ghi của script khi một lệnh phía sau thất bại. Chẳng hạn `PEXPIRE` từ chối giá trị lẻ của mili giây, và nếu thất bại sau `HSET`, nó sẽ để lại một lock không bao giờ hết hạn. Đó là lý do interceptor truyền cho store số mili giây nguyên.

Nest inject Redis client, và constructor đăng ký store, giống như với store PostgreSQL. Một ứng dụng chỉ có một store, nên `RedisIdempotencyStore` thay thế store kia trong `AppModule`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { IdempotencyModule } from '@nestjs/idempotency';
import { RedisIdempotencyStore } from './idempotency/redis-idempotency.store.js';
import type { User } from './orders/order.js';
import { OrdersModule } from './orders/orders.module.js';
import { RedisModule } from './redis/redis.module.js';

@Module({
  imports: [
    RedisModule,
    IdempotencyModule.forRoot({
      scope: (req: { user?: User }) => req.user?.id,
    }),
    OrdersModule,
  ],
  providers: [RedisIdempotencyStore],
})
export class AppModule {}
```

`RedisModule` đại diện cho Redis module của ứng dụng: một global module cung cấp một ioredis client dưới token `REDIS`, ví dụ với `useFactory: () => new Redis(process.env.REDIS_URL!)`, và đóng nó bằng `quit()` trong `onApplicationShutdown()`, sau khi package đã xử lý xong các request đang chạy. `RedisClient` không yêu cầu gì ngoài `eval()`, thứ mà một instance `Redis` của ioredis có sẵn. Lúc khởi động, dòng log ghi `IdempotencyStorage: RedisIdempotencyStore`, và các quy tắc của registry từ store PostgreSQL vẫn áp dụng: một store, đăng ký từ constructor.

Project ví dụ cũng chạy contract suite trên store này:

```typescript
@@filename(test/step-4.redis-store.spec)
import { idempotencyStoreContract } from '@nestjs/idempotency/testing';
// ...
describe('RedisIdempotencyStore, the IdempotencyStore contract (on FakeRedis)', () => {
  let redis: FakeRedis;
  const cases = idempotencyStoreContract(
    () => {
      redis = new FakeRedis();
      return new RedisIdempotencyStore(redis, new IdempotencyStorage());
    },
    // Redis expires keys on its own clock: the fake's.
    { advanceTime: (ms) => redis.advance(ms), concurrent: true },
  );
  for (const c of cases) {
    it(c.name, c.run);
  }
});
```

> info **Gợi ý** Project ví dụ của bài hướng dẫn này không có Redis server, nên các test của nó chạy store trên một bản giả in-process implement cùng bốn script bằng JavaScript. Như vậy bao phủ được logic của store và cách nó đọc reply, nhưng không bao phủ bản thân phần Lua. Hãy chạy contract suite trên một Redis thật, ví dụ trong một container, trước khi tin dùng store. Không có `advanceTime`, suite sẽ chờ hết hạn thật, mất khoảng mười giây.

Các bước còn lại hiển thị `DrizzleIdempotencyStore` trong phần khai báo module. Với Redis, hãy đăng ký `RedisIdempotencyStore` thay vào đó: mã hóa, service vận chuyển và các tùy chọn tinh chỉnh hoạt động y như vậy, và khi bật mã hóa, field `resp` chứa envelope đã được niêm phong thay cho cột `response`.
#### Mã hóa biên lai được lưu <a id="encrypt-stored-receipts"></a>

Response được lưu là toàn bộ biên lai: id biên lai của payment provider, số tiền, và bốn số cuối của thẻ. Chúng nằm trong `idempotency_keys` ở dạng văn bản thuần, trong mọi bản backup và mọi bản dump của database, nên hãy mã hóa các record khi lưu trữ.

Các khóa mã hóa là secret mà ứng dụng nên đọc khi nó khởi động, chứ không phải khi `app.module.ts` được import, nên hãy chuyển sang `forRootAsync()`. Store vẫn giữ nguyên, là một provider của `AppModule` tự đăng ký, và factory trả về các tùy chọn:

```typescript
@@filename(app.module)
IdempotencyModule.forRootAsync({
  useFactory: () => ({
    scope: (req: { user?: User }) => req.user?.id,
    encryption: {
      // Newest first: seal with the first key, open with any of them.
      keys: process.env.IDEMPOTENCY_KEYS!.split(','),
    },
  }),
}),
```

Tạo một khóa bằng `openssl rand -base64 32`, và lưu nó trong secret manager dưới tên `IDEMPOTENCY_KEYS`. Khi bật mã hóa, cột `response` chứa một envelope đã niêm phong, `v1.<keyId>.<iv>.<ciphertext>.<tag>`, thay vì biên lai:

- Record được mã hóa bằng AES-256-GCM, với IV ngẫu nhiên cho mỗi record.
- Fingerprint vẫn ở dạng văn bản thuần. Store phải so sánh nó, và dù sao nó cũng là một hash.
- Record key được xác thực cùng với dữ liệu, nên một record bị copy sang key của người dùng khác sẽ không mở được thay vì bị replay ở đó.
- Trong khi bật mã hóa, các record dạng văn bản thuần bị từ chối, nên không ai có quyền ghi vào bảng có thể cài cắm một response.
- Một khóa dạng chuỗi phải có ít nhất 32 ký tự, và nó được mở rộng bằng HKDF-SHA256. Như vậy ổn cho một secret ngẫu nhiên như ở trên, nhưng nó không phải là password hash, nên đừng dùng một mật khẩu do người đặt. Một khóa ngắn hơn, hoặc có khoảng trắng xung quanh (`IDEMPOTENCY_KEYS=new, old` bị tách thành khóa thứ hai bắt đầu bằng khoảng trắng), sẽ dừng ứng dụng lúc khởi động, kèm một lỗi nêu tên nó.

Hãy bật mã hóa trước khi endpoint lưu record đầu tiên. Nó thay đổi định dạng record theo cả hai chiều: một record dạng văn bản thuần được lưu trước khi chuyển, cũng như một record đã niêm phong sau khi tắt mã hóa, sẽ không mở được cho tới khi hết hạn, và các lần replay của nó nhận lỗi 500 mô tả bên dưới.

Để xoay vòng khóa mà không làm hỏng các lần replay:

1. Tạo một khóa mới và deploy `IDEMPOTENCY_KEYS=old-key,new-key`. Các instance vẫn niêm phong record bằng khóa cũ, nhưng có thể mở các record được niêm phong bằng khóa mới.
2. Khi mọi instance đã chạy cấu hình đó, deploy `IDEMPOTENCY_KEYS=new-key,old-key`. Record mới được niêm phong bằng khóa mới, còn record cũ vẫn mở được. Trong quá trình rolling deploy, các instance chưa restart đã có thể mở các record mới, nhờ bước đầu tiên.
3. Khi `ttl` đã trôi qua (48 giờ, xem [Tinh chỉnh TTL và cách xử lý thất bại](/reliability/idempotency#tune-ttls-and-failure-handling)), mọi record được niêm phong bằng khóa cũ đã hết hạn. Deploy `IDEMPOTENCY_KEYS=new-key`.

Nếu bạn gỡ một khóa quá sớm, các lần replay của record được niêm phong bằng khóa đó sẽ **fail closed**. Client nhận lỗi 500 `IDEMPOTENCY_RECORD_UNREADABLE`, lỗi được log lại, và handler không chạy lại: record chứng minh rằng thẻ đã bị trừ tiền, nên chạy handler có thể trừ tiền hai lần. Lỗi sẽ dừng khi record hết hạn.

#### Thanh toán qua GraphQL <a id="pay-through-graphql"></a>

Website của cửa hàng thanh toán qua một GraphQL mutation. Đăng ký `GraphQLModule` trong `AppModule`:

```typescript
@@filename(app.module)
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  autoSchemaFile: true,
}),
```

Sau đó thêm mutation vào resolver đơn hàng, cạnh các query của nó. Trong GraphQL, key có thể đến từ header `Idempotency-Key`, như với REST, hoặc từ một argument. Một argument đặt key vào schema, nơi các code generator và người review có thể thấy nó. Nó cũng hợp với các GraphQL client, vốn thường đặt header một lần cho mỗi kết nối thay vì cho mỗi operation. `@Idempotent()` đọc argument `idempotencyKey` của mutation khi có, và đọc header trong trường hợp ngược lại, nên resolver chỉ cần khai báo argument:

```typescript
@@filename(orders/orders.resolver)
@Mutation(() => PaymentReceipt)
@Idempotent({ required: true })
payOrder(
  @Args('orderId', { type: () => ID }) orderId: string,
  @Args('input') input: PayOrderDto,
  @Args('idempotencyKey') _idempotencyKey: string,
  @CurrentUser() user: User,
) {
  return this.ordersService.pay(orderId, user, input);
}
```

`PayOrderDto` là class mà endpoint REST dùng, được thêm `@InputType()` và `@Field()`, còn `PaymentReceipt` là một `@ObjectType()` với các field của biên lai. Resolver dùng cùng `AuthGuard`, guard này đọc request từ GraphQL context. `scope` của module nhận cùng request đó, nên ở đây key cũng theo từng người dùng. Argument là một `String` non-null, nên GraphQL validation đã từ chối sẵn một operation không có nó:

```graphql
mutation PayOrder($orderId: ID!, $paymentMethod: String!, $key: String!) {
  payOrder(orderId: $orderId, input: { paymentMethod: $paymentMethod }, idempotencyKey: $key) {
    receiptId
    amount
    cardLast4
    paidAt
  }
}
```

Một lần retry với cùng variables trả về kết quả `payOrder` đã lưu, với cùng các type mà resolver đã trả về, nên một field `Date` được replay thành `Date`. Record key được nối thêm đường dẫn của field, như `usr_alice:<key>:payOrder`, vì một operation có thể chứa nhiều mutation. Mỗi field được lưu và replay riêng, và alias là một phần của đường dẫn, nên một lần retry phải gửi cùng document.

Một lần từ chối là một lỗi trên field đó, không phải một HTTP status. Response vẫn là 200, vì các field khác trong cùng operation có thể đã thành công, còn status và thời gian chờ retry nằm trong `extensions` (đã bỏ `locations`):

```json
{
  "errors": [
    {
      "message": "A request with this idempotency key is still being processed.",
      "path": ["payOrder"],
      "extensions": {
        "code": "IDEMPOTENCY_KEY_IN_USE",
        "httpStatus": 409,
        "retryAfter": 2
      }
    }
  ],
  "data": null
}
```

Cũng vì lý do đó, các lần replay GraphQL không đặt header `Idempotent-Replayed`.

#### Khử trùng lặp event order.paid <a id="deduplicate-orderpaid-events"></a>

Sau một lần thanh toán, `OrdersService` phát ra event `order.paid`, và service vận chuyển sắp xếp người giao hàng. Trong thực tế, event được gửi ít nhất một lần (at least once). Một publisher retry sau khi timeout, hoặc một broker (RabbitMQ, Kafka, NATS JetStream) gửi lại một message chưa được ack, có thể gửi cùng một event hai lần, và khách hàng nhận được hai kiện hàng.

Khử trùng lặp event cần một id giống nhau cho mọi lần gửi của một event, nên nó được suy ra từ dữ liệu chứ không phải sinh mới ở mỗi lần gửi. Một đơn hàng chỉ được thanh toán một lần, nên `OrdersService` dùng `order-paid:` theo sau là id đơn hàng. Đánh dấu [event handler](/microservices/basics#event-based) bằng `@Idempotent()`, và trỏ `keyFrom` tới id đó:

```typescript
@@filename(shipping/shipping.controller)
import { Controller } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import { Idempotent } from '@nestjs/idempotency';
import { ShipmentsService } from './shipments.service.js';

export interface OrderPaidEvent {
  eventId: string;
  orderId: string;
}

@Controller()
export class ShippingController {
  constructor(private readonly shipmentsService: ShipmentsService) {}

  @EventPattern('order.paid')
  @Idempotent({ required: true, keyFrom: { payload: 'eventId' } })
  async onOrderPaid(@Payload() event: OrderPaidEvent) {
    await this.shipmentsService.createFor(event.orderId);
  }
}
```

Mặc định, microservice handler đọc key từ thuộc tính `idempotencyKey` của payload, sau đó từ một header của transport có tên do tùy chọn `header` chỉ định. Ở đây, `keyFrom` đọc `eventId` thay vào đó, và `required: true` từ chối các event không có nó.

Service vận chuyển là một ứng dụng riêng, có database riêng và `IdempotencyModule` riêng, và nó đăng ký cùng class store:

```typescript
@@filename(shipping/shipping.module)
import { Module } from '@nestjs/common';
import { DrizzleModule } from '@nestjs/drizzle';
import { IdempotencyModule } from '@nestjs/idempotency';
import { drizzle } from 'drizzle-orm/node-postgres';
import { DrizzleIdempotencyStore } from '../idempotency/drizzle-idempotency.store.js';
import { ShipmentsService } from './shipments.service.js';
import { ShippingController } from './shipping.controller.js';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL! }),
    }),
    IdempotencyModule.forRoot({
      ttl: '7d', // brokers can redeliver long after the first delivery
    }),
  ],
  controllers: [ShippingController],
  providers: [ShipmentsService, DrizzleIdempotencyStore],
})
export class ShippingModule {}
```

```typescript
@@filename(shipping/main)
import { NestFactory } from '@nestjs/core';
import { Transport, type MicroserviceOptions } from '@nestjs/microservices';
import { ShippingModule } from './shipping.module.js';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(ShippingModule, {
    transport: Transport.TCP,
    options: { host: '0.0.0.0', port: 4001 },
  });
  await app.listen();
}
bootstrap();
```

Có vài chi tiết khác so với API:

- Không có `scope`, vì event id là duy nhất trong toàn bộ hệ thống.
- `ttl` là 7 ngày, vì một message có thể quay lại từ dead-letter queue rất lâu sau lần xử lý đầu tiên.
- Record thuộc về một handler: record key kết thúc bằng class và method của handler, như `order-paid%3Aord_1001:ShippingController.onOrderPaid`. Nest chạy mọi handler được đăng ký cho một event, nên một handler thứ hai cho `order.paid`, chẳng hạn một handler gửi email mã vận đơn, sẽ giữ record riêng và vẫn xử lý mỗi event một lần.

Một event trùng lặp được xử lý theo một trong hai cách:

- Nếu lần gửi đầu tiên đã hoàn tất, bản trùng lặp bị bỏ qua. Kết quả đã lưu được "replay", và vì event không có reply, không có gì xảy ra.
- Nếu lần gửi đầu tiên vẫn đang chạy, bản trùng lặp bị từ chối với `IDEMPOTENCY_KEY_IN_USE`, và Nest log lỗi đó. Với một transport có ack message, như RabbitMQ hoặc Kafka, đừng ack lần gửi đó là đã xử lý. Hãy để transport gửi lại nó sau, khi đó nó sẽ bị bỏ qua.

Dù theo cách nào, người giao hàng cũng chỉ được đặt một lần. Ngay từ đầu, các lần retry thanh toán HTTP không tạo ra event trùng lặp, vì một request được replay không bao giờ tới được `OrdersService`.

#### Tinh chỉnh TTL và cách xử lý thất bại <a id="tune-ttls-and-failure-handling"></a>

Các giá trị mặc định là điểm khởi đầu. Đây là cấu hình cuối cùng của API:

```typescript
@@filename(app.module)
IdempotencyModule.forRootAsync({
  useFactory: () => ({
    scope: (req: { user?: User }) => req.user?.id,
    encryption: {
      // Newest first: seal with the first key, open with any of them.
      keys: process.env.IDEMPOTENCY_KEYS!.split(','),
    },
    // Longer than the app keeps retrying a queued payment (24 hours).
    ttl: '48h',
    // A crashed instance blocks a key for at most 45 seconds. While a
    // charge runs, its lock is renewed every 15 seconds.
    lockTtl: '45s',
    // How long a client waits after a 409 before it asks again.
    retryAfter: '2s',
  }),
}),
```

Mọi khoảng thời gian đều nhận số mili giây, hoặc một chuỗi như `'45s'`, `'48h'` hay `'7d'`. Một giá trị không parse được sẽ dừng ứng dụng lúc khởi động, kèm một lỗi nêu tên tùy chọn.

- **`ttl`** (mặc định: `'24h'`) là khoảng thời gian một kết quả đã hoàn tất có thể được replay. Nó phải dài hơn khoảng thời gian dài nhất mà client tiếp tục retry. Ứng dụng xếp hàng các lần thanh toán thực hiện khi offline tới tối đa một ngày, nên ở đây là 48 giờ. Sau `ttl`, key bị quên, và một lần retry sẽ chạy lại handler. Trong ứng dụng này, điều đó kết thúc bằng lỗi 409 "đã thanh toán" thay vì trừ tiền lần hai, nhưng khách hàng không nhận được biên lai.
- **`lockTtl`** (mặc định: `'60s'`) là khoảng thời gian một lock đang xử lý còn tồn tại sau khi instance chạy handler bị crash. Trong khi handler chạy, interceptor gia hạn lock mỗi `lockTtl / 3`, ở đây là mỗi 15 giây, nên một lần trừ tiền mất hơn 45 giây vẫn giữ được lock, và một lần retry nhận 409. Khi việc gia hạn dừng lại, lock hết hạn và một lần retry sẽ tiếp quản key. Một `lockTtl` ngắn hơn giải phóng key sớm hơn sau khi crash, nhưng gia hạn thường xuyên hơn. Nếu không kết nối được tới store để gia hạn lock, interceptor sẽ log một cảnh báo rằng lock đã bị mất.
- **`retryAfter`** (mặc định: `'1s'`) là giá trị của header `Retry-After` trên một 409, tính bằng số giây nguyên. Việc trừ tiền thẻ thường mất một đến hai giây, nên API yêu cầu client chờ 2 giây thay vì quay lại kiểm tra sau một giây.

`@Idempotent()` nhận `required`, `ttl`, `lockTtl`, `retryAfter`, `keyFrom`, `scope`, `fingerprint` và `storeIf`, các tùy chọn này ghi đè tùy chọn của module cho handler đó. `fingerprint` chọn những gì một lần retry phải lặp lại, ví dụ body không kèm timestamp của client; method và URL luôn được tính. Decorator cũng dùng được trên class controller hoặc resolver, khi đó nó bao phủ các handler thay đổi trạng thái: route GET và GraphQL query bị bỏ qua trừ khi chúng có `@Idempotent()` riêng. `@Idempotent()` riêng của một handler được merge với tùy chọn của class, nên một `required: true` cấp class vẫn áp dụng cho handler chỉ đặt `lockTtl`.

Một hàm `scope` chạy cho mọi loại handler, và những gì nó nhận phụ thuộc vào handler: request với HTTP và GraphQL, nhưng là payload của message với microservice handler. Trong một ứng dụng phục vụ cả hai từ một `IdempotencyModule`, hãy truyền cho `scope` một object thay vào đó, với mỗi context một hàm dưới các key `http`, `graphql` và `rpc`. Mỗi hàm được gán type theo những gì context của nó truyền vào, và một context không có hàm sẽ không được scope.

Không phải kết quả nào cũng được lưu. Mặc định, mọi thứ dưới 500 đều được lưu:

| Kết quả                                                                     | Mặc định                                                    | Lý do                                                      |
| --------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------- |
| 2xx                                                                         | Được lưu và replay                                          | Thanh toán đã thành công                                   |
| `HttpException` 4xx (validation 400, bị từ chối 402, 404, 409 đã thanh toán) | Được lưu, và throw lại ở mọi lần replay                    | Nó có tính tất định: cùng request nhận cùng câu trả lời    |
| Lỗi khác có `status` 4xx (`AuthorizationError`, 403)                        | Được lưu dưới dạng exception của Nest cho status đó, và replay | Package của nó chuyển nó thành status đó                |
| 5xx hoặc lỗi không xác định (payment provider 503, database down)           | Không được lưu. Key được giải phóng, nên một lần retry sẽ chạy lại | Phần lớn thất bại xảy ra trước side effect          |
| `StreamableFile`, stream, `@Res()` không có `passthrough`                   | Không được lưu. Key được giải phóng, và một cảnh báo được log | Chúng không thể replay                                   |

Một lỗi được replay được dựng lại thành một `HttpException` thuần với status và body đã lưu, và nó đi qua các exception filter của bạn một lần nữa. Một filter kiểm tra `instanceof` với một exception class tùy chỉnh sẽ thấy class gốc khi replay.

Tùy chọn `storeIf` thay đổi quy tắc này. Nó nhận status và, khi handler đã throw, cả lỗi. Ví dụ, `storeIf: () => true` lưu cả lỗi 5xx, giống như Stripe. Điều đó quan trọng với một lỗ hổng mà mặc định để lại: một lỗi 5xx xảy ra **sau** side effect. Nếu payment provider đã trừ tiền thẻ rồi `markPaid()` thất bại, key được giải phóng, và lần retry sẽ trừ tiền lần nữa. Có ba cách để bịt lỗ hổng này:

- Truyền cho payment provider một key được suy ra từ id người dùng và idempotency key. Phần lớn payment provider nhận idempotency key riêng của họ, nên provider cũng khử trùng lặp việc trừ tiền. Riêng idempotency key là chưa đủ, vì hai người dùng có thể gửi cùng một key.
- Lưu lỗi 5xx cho handler này bằng `storeIf`, và để ứng dụng bắt đầu một lần thử mới sau một lỗi 5xx. Để chỉ lưu lỗi xảy ra sau khi đã trừ tiền, hãy throw một exception riêng ở đó và kiểm tra nó: `storeIf: (status, error) => status < 500 || error instanceof ChargeCapturedError`.
- Ghi việc thanh toán và event trong một transaction, với một [transactional outbox](/reliability/outbox#prerequisites).

#### Chạy thử <a id="try-it"></a>

Khởi động service vận chuyển, và API với `DATABASE_URL` (đã áp dụng migration), `IDEMPOTENCY_KEYS` và sandbox của payment provider đã được cấu hình. Sandbox mất khoảng nửa giây để trả lời. Các output bên dưới đã được lược bớt, chỉ giữ các header liên quan.

Một lần thanh toán không có key bị từ chối:

```bash
$ curl -i localhost:3000/orders/ord_1001/pay \
    -H 'Authorization: Bearer alice-token' \
    --json '{"paymentMethod":"pm_card_visa"}'
HTTP/1.1 400 Bad Request

{"statusCode":400,"error":"Bad Request","code":"IDEMPOTENCY_KEY_REQUIRED","message":"An idempotency key is required for this operation."}
```

Lời gọi đầu tiên có key sẽ trừ tiền thẻ:

```bash
$ KEY=$(uuidgen)
$ curl -i localhost:3000/orders/ord_1001/pay \
    -H 'Authorization: Bearer alice-token' \
    -H "Idempotency-Key: $KEY" \
    --json '{"paymentMethod":"pm_card_visa"}'
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8

{"orderId":"ord_1001","receiptId":"ch_0001","amount":4098,"cardLast4":"4242","paidAt":"2026-09-22T11:09:25.813Z"}
```

Một lần retry với cùng key nhận cùng biên lai, tới cả `paidAt`, và payment provider không được gọi:

```bash
$ curl -i localhost:3000/orders/ord_1001/pay \
    -H 'Authorization: Bearer alice-token' \
    -H "Idempotency-Key: $KEY" \
    --json '{"paymentMethod":"pm_card_visa"}'
HTTP/1.1 201 Created
Idempotent-Replayed: true
Content-Type: application/json; charset=utf-8

{"orderId":"ord_1001","receiptId":"ch_0001","amount":4098,"cardLast4":"4242","paidAt":"2026-09-22T11:09:25.813Z"}
```

Cùng key với một thẻ khác là một bug phía client:

```bash
$ curl -i localhost:3000/orders/ord_1001/pay \
    -H 'Authorization: Bearer alice-token' \
    -H "Idempotency-Key: $KEY" \
    --json '{"paymentMethod":"pm_card_mastercard"}'
HTTP/1.1 422 Unprocessable Entity

{"statusCode":422,"error":"Unprocessable Entity","code":"IDEMPOTENCY_KEY_REUSED","message":"This idempotency key was already used for a different request."}
```

Cuối cùng, gửi đồng thời hai request với một key mới, cho đơn hàng còn lại. Một request được trừ tiền, và request kia nhận 409 kèm `Retry-After: 2` trong khi payment provider vẫn đang xử lý:

```bash
$ KEY=$(uuidgen)
$ for i in 1 2; do
  curl -s -o /dev/null -w '%{http_code} %header{retry-after}\n' \
    localhost:3000/orders/ord_1002/pay \
    -H 'Authorization: Bearer alice-token' \
    -H "Idempotency-Key: $KEY" \
    --json '{"paymentMethod":"pm_card_visa"}' &
done; wait
409 2
201
```

> info **Gợi ý** `--json` cần curl 7.82 trở lên, và `%header` trong `-w` cần curl 7.84 trở lên.

#### Testing

Trong các test end-to-end, hãy giữ cấu hình thật của ứng dụng, nhưng override provider `DrizzleIdempotencyStore` bằng một `InMemoryIdempotencyStore` thuần. Một instance thuần không tự đăng ký, nên module fallback về store trong bộ nhớ của nó, và vì Nest không bao giờ tạo `DrizzleIdempotencyStore`, không có gì truy vấn database (một pool node-postgres chỉ kết nối ở query đầu tiên, nên `DrizzleModule` cũng không mở kết nối nào). Khóa mã hóa vẫn lấy từ `IDEMPOTENCY_KEYS`, nên hãy đặt nó trong môi trường test, ví dụ với `test.env` trong `vitest.config.mts`.

Mock payment provider với một độ trễ nhỏ, để hai request gửi cùng lúc chồng lấn lên nhau:

```typescript
@@filename(test/pay-order.e2e-spec)
import { ValidationPipe, type INestApplication } from '@nestjs/common';
import { InMemoryIdempotencyStore } from '@nestjs/idempotency';
import { Test } from '@nestjs/testing';
import { setTimeout } from 'node:timers/promises';
import { EMPTY } from 'rxjs';
import request from 'supertest';
import type { MockInstance } from 'vitest';
import { AppModule } from '../src/app.module.js';
import { DrizzleIdempotencyStore } from '../src/idempotency/drizzle-idempotency.store.js';
import { SHIPPING_SERVICE } from '../src/orders/orders.service.js';
import { PaymentProviderClient } from '../src/payments/payment-provider.client.js';

describe('POST /orders/:id/pay', () => {
  let app: INestApplication;
  let charge: MockInstance<PaymentProviderClient['charge']>;

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(DrizzleIdempotencyStore)
      .useValue(new InMemoryIdempotencyStore())
      .overrideProvider(SHIPPING_SERVICE)
      .useValue({ emit: () => EMPTY })
      .compile();

    app = moduleRef.createNestApplication();
    app.useGlobalPipes(new ValidationPipe({ whitelist: true }));
    await app.listen(0, '127.0.0.1');

    charge = vi.spyOn(app.get(PaymentProviderClient), 'charge').mockImplementation(async (input) => {
      await setTimeout(100); // slow enough for duplicates to overlap
      return {
        id: 'ch_test',
        amount: input.amount,
        cardLast4: '4242',
        reference: input.reference,
        createdAt: new Date().toISOString(),
      };
    });
  });

  afterEach(() => app.close());

  const pay = (key: string) =>
    request(app.getHttpServer())
      .post('/orders/ord_1001/pay')
      .set('Authorization', 'Bearer alice-token')
      .set('Idempotency-Key', key)
      .send({ paymentMethod: 'pm_card_visa' });

  it('charges once when the app retries', async () => {
    const first = await pay('key-1').expect(201);
    const retry = await pay('key-1').expect(201).expect('Idempotent-Replayed', 'true');

    expect(retry.body).toEqual(first.body);
    expect(charge).toHaveBeenCalledTimes(1);
  });

  it('rejects a duplicate that arrives while the first is in flight', async () => {
    const [a, b] = await Promise.all([pay('key-2'), pay('key-2')]);

    expect([a.status, b.status].sort()).toEqual([201, 409]);
    expect(charge).toHaveBeenCalledTimes(1);
  });
});
```

Khi ứng dụng đã khởi tạo, `app.get(IdempotencyStorage).source` trả về store đang dùng, ở đây là store trong bộ nhớ. Method `peek(key)` của nó trả về record thô dưới một record key như `usr_alice:key-1` (`state`, `fingerprint` và `response`), để assert những điều như "lần thanh toán bị từ chối đã được lưu". Hãy test store của riêng bạn một cách độc lập, bằng contract suite từ [Lưu key trong PostgreSQL](/reliability/idempotency#store-keys-in-postgresql), với một server thật. Để giữ store Drizzle trong các test end-to-end, hãy thay database mà `DrizzleModule` đã đăng ký, bằng `overrideProvider(getDrizzleToken()).useValue(db)` (`getDrizzleToken` đến từ `@nestjs/drizzle`), trong đó `db` là một Drizzle database trên PGlite đã được migrate bằng các migration của bạn. Project ví dụ test mã hóa, GraphQL, event và phần tinh chỉnh theo cách đó.

Xem [End-to-end testing](/fundamentals/testing#end-to-end-testing) để biết thêm về cách thiết lập testing.

#### Checklist cho production <a id="production-checklist"></a>

- Đăng ký một store dùng chung (database của bạn, hoặc Redis), kể cả với một instance duy nhất: record trong bộ nhớ mất sạch ở mỗi lần restart hoặc deploy, và một lần retry sau đó sẽ chạy lại handler. Chạy contract suite trên nó với `concurrent` được bật. Trong production, ứng dụng từ chối khởi động nếu không có store, trừ khi đặt `allowInMemoryStorage`. Với Redis, hãy cấu hình `maxmemory-policy noeviction`. Một record bị evict sớm là một lần trừ tiền hai lần đang chực chờ xảy ra, và vì mọi idempotency record đều có TTL, các policy `volatile-*` cũng sẽ evict chúng.
- Đặt `required: true` trên mọi endpoint chuyển tiền hoặc tạo ra thứ gì đó mà khách hàng sẽ nhận ra nếu bị lặp hai lần.
- Đặt `scope` cho mọi endpoint hướng tới client. Không có nó, key của một người dùng có thể replay response của người dùng khác. Module log một cảnh báo khi một người dùng đã đăng nhập gọi một handler không có scope.
- Giữ idempotency interceptor ở bên ngoài các global interceptor khác. Global interceptor chạy theo thứ tự được đăng ký, và các provider `APP_INTERCEPTOR` của `AppModule` được đăng ký trước các provider của những module mà nó import, nên chúng chạy bên ngoài interceptor này và thấy mọi lần replay. Module cảnh báo về chúng lúc khởi động. Nó từ chối khởi động khi một trong số đó là `ClassSerializerInterceptor`, vì một lần replay sẽ đưa cho nó một plain object và gửi đi các field mà `@Exclude()` che giấu. Hãy đăng ký các interceptor như vậy bằng `app.useGlobalInterceptors()` trong `main.ts`, hoặc trong một module được import sau `IdempotencyModule`.
- Với một database store, tạo bảng của nó qua migration, định cỡ connection pool cho các câu lệnh của nó, giữ đồng hồ của các instance được đồng bộ, và gọi `prune()` theo lịch.
- Giữ `ttl` lớn hơn khoảng thời gian retry của client. `lockTtl` chỉ cần đủ cho trường hợp crash, vì lock được gia hạn trong khi handler chạy.
- Theo dõi các event. `IdempotencyEvents` có thể inject được, và stream `events$` của nó báo cáo mọi lần replay, mọi lần từ chối kèm `code`, và mọi lock bị mất. Các event tương tự được publish trên các diagnostics channel `nestjs:idempotency:replayed`, `nestjs:idempotency:rejected` và `nestjs:idempotency:lock-lost` cho các công cụ tracing. Hãy cảnh báo khi có `lock-lost`: nó nghĩa là kết quả của lần thử không có trong store, vì việc gia hạn thất bại (không kết nối được tới store, hoặc event loop bị block lâu hơn `lockTtl`) hoặc vì store thất bại khi ghi kết quả, và một lần retry có thể chạy lại handler.
- Bật `encryption` khi response chứa dữ liệu cá nhân hoặc dữ liệu thanh toán, trước khi endpoint lưu record đầu tiên. Giữ các khóa trong secret manager, xoay vòng chúng theo ba bước ở trên, và không bao giờ gỡ một khóa trước khi `ttl` trôi qua.
- Truyền cho payment provider một key được suy ra từ id người dùng và idempotency key, để bao phủ trường hợp thất bại sau khi trừ tiền.
- Khi nhiều service dùng chung một Redis, hãy cho mỗi service một tiền tố key riêng (phần `idem:` trong store) hoặc một database riêng. Record key chỉ là duy nhất trong phạm vi một service: hai service có thể đều có một handler class cùng tên, và một client có thể gửi một key tới cả hai.
- Giữ bước kiểm tra trạng thái trong service, lý tưởng nhất là dưới dạng một câu update có điều kiện trên database. Một idempotency key khử trùng lặp các lần retry của một lần thử, nhưng hai lần bấm tạo ra hai key là hai lần thử.
- Cho phép trình duyệt gửi header. Với client khác origin, hãy thêm `Idempotency-Key` vào `allowedHeaders` của CORS, và `Idempotent-Replayed` cùng `Retry-After` vào `exposedHeaders`.
- Giữ response idempotent ở kích thước nhỏ. Toàn bộ body của response được lưu, và package hiện chưa có giới hạn kích thước.

#### Hợp đồng của store <a id="the-store-contract"></a>

Bài hướng dẫn đã viết store bằng Drizzle, bằng TypeORM, và cho Redis. Phần này tóm tắt những gì bất kỳ `IdempotencyStore` nào cũng phải làm, để bạn viết store với một ORM khác. Mục "Implementing a store" trong README của package mô tả chi tiết từng method.

**Đăng ký.** Store là một singleton provider bình thường gọi `registerSource(this)` trên `IdempotencyStorage` (có thể inject) trong constructor của nó. Registry kiểm tra cấu trúc ngay lập tức, từ chối lần đăng ký thứ hai trừ khi truyền `replace: true`, và bị khóa khi `IdempotencyModule` khởi tạo, đồng thời log ra store đang dùng. Không có gì được đăng ký, module dùng `InMemoryIdempotencyStore`, store mà một instance không thể dùng chung với instance khác, và mất record khi restart. Với `NODE_ENV=production`, việc khởi động sẽ thất bại thay vào đó, trừ khi bạn đặt `allowInMemoryStorage: true`, tức chấp nhận mất record ở mỗi lần restart hoặc deploy.

**Các method.** Cả bốn đều nguyên tử: mỗi method quyết định ai giữ một key, và một lần đọc theo sau là một lần ghi riêng sẽ để hai request cùng chạy handler, chính là việc trừ tiền hai lần mà package sinh ra để ngăn chặn. Không method nào nhận transaction của bạn: một idempotency record được ghi độc lập, không bao giờ là một phần của business transaction.

| Method | Làm gì | Giữ tính nguyên tử bằng cách nào |
| --- | --- | --- |
| `acquire(key, owner, fingerprint, lockTtl)` | Lấy lock trên một key còn trống hoặc đã hết hạn, hoặc trả về record mà nó tìm thấy | Một câu insert tiếp quản dòng đã hết hạn ngay trong cùng câu lệnh, nên trong nhiều bên gọi đồng thời chỉ đúng một bên thắng; các bên còn lại đọc record của bên thắng |
| `complete(key, owner, response, ttl)` | Biến lock còn hiệu lực của owner thành một record đã hoàn tất | Một compare-and-set: việc kiểm tra owner và thời hạn nằm trong `WHERE` của câu lệnh ghi |
| `release(key, owner)` | Xóa lock còn hiệu lực của owner, để một lần retry có thể chạy handler | Một compare-and-set, như `complete()` |
| `extend(key, owner, lockTtl)` | Gia hạn lock còn hiệu lực của owner | Một compare-and-set, như `complete()` |

**Với Prisma.** Store Drizzle và TypeORM là mẫu để làm theo, với cùng bảng:

- **`acquire()`** là một câu `INSERT ... ON CONFLICT (key_hash) DO UPDATE ... WHERE expires_at <= now RETURNING`. `upsert()` của Prisma không có điều kiện cho phần update, nên hãy dùng `$queryRaw`. Khi không có dòng nào trả về, hãy đọc record, như các store khác làm.
- **`complete()`, `release()` và `extend()`** đặt owner và thời hạn trong `WHERE` và đếm số dòng: `updateMany()` hoặc `deleteMany()` với `keyHash`, `owner` và bộ lọc `gt: now` trên `expiresAt` trong `where`, và `count === 1`. Không dùng `update()` sau `findUnique()`: nó đọc trước.
- **Cột response** dùng `json` thay vì `jsonb`, với bất kỳ ORM nào: `jsonb` từ chối `\u0000` bên trong một chuỗi, và body của response có thể chứa ký tự đó.

**Hãy test nó** bằng suite từ `@nestjs/idempotency/testing`, như các store Drizzle, TypeORM và Redis đã làm. `idempotencyStoreContract()` trả về các case dùng được với mọi test runner. `concurrent: true` cho 16 bên gọi tranh nhau mỗi key; hãy chạy nó trên PostgreSQL với một connection pool, nơi các lời gọi thực sự chồng lấn. `advanceTime` dịch đồng hồ của store cho các case về thời hạn, và không có nó thì các case này chờ theo thời gian thực.
#### Tham khảo <a id="reference"></a>

##### Tùy chọn của module <a id="module-options"></a>

`IdempotencyModule.forRoot()` nhận các tùy chọn sau. `forRootAsync()` nhận `isGlobal` và `imports` ở cấp ngoài cùng, cạnh `useFactory`, `useClass` hoặc `useExisting`, và factory trả về phần còn lại. Mọi tùy chọn trừ `header`, `replayHeaders`, `encryption`, `allowInMemoryStorage` và `isGlobal` cũng có thể đặt theo từng class hoặc handler trong `@Idempotent()`, khi đó nó được merge theo từng field lên trên tùy chọn của module.

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `required` | `boolean` | `false` | Từ chối các lời gọi không có key với `IDEMPOTENCY_KEY_REQUIRED`. Xem [Làm endpoint thanh toán trở nên idempotent](/reliability/idempotency#make-the-payment-endpoint-idempotent). |
| `scope` | hàm, object hoặc `false` | không có | Namespace của key, chẳng hạn id người dùng. Một object có mỗi context một hàm, dưới `http`, `graphql` và `rpc`. `false` cố ý dùng chung một namespace. |
| `ttl` | `Duration` | `'24h'` | Khoảng thời gian một kết quả đã hoàn tất được replay. Xem [Tinh chỉnh TTL và cách xử lý thất bại](/reliability/idempotency#tune-ttls-and-failure-handling). |
| `lockTtl` | `Duration` | `'60s'` | Khoảng thời gian một lock đang xử lý còn tồn tại sau khi việc gia hạn dừng lại. Lock được gia hạn mỗi `lockTtl / 3`. |
| `retryAfter` | `Duration` | `'1s'` | Thời gian chờ được gửi kèm `IDEMPOTENCY_KEY_IN_USE`, tính bằng số giây nguyên, làm tròn lên. |
| `keyFrom` | source, hoặc mỗi context một source | xem bên dưới | Nơi lấy key: `header`, `arg` (GraphQL), `payload` (microservice) hoặc một hàm nhận `ExecutionContext`. |
| `fingerprint` | `(payload, context) => unknown` | toàn bộ payload | Những gì một lần retry phải lặp lại. Method và URL, field GraphQL hoặc message pattern, và scope luôn được tính. |
| `storeIf` | `(status, error) => boolean` | `status < 500` | Những kết quả nào được lưu và replay. Các kết quả khác giải phóng key. |
| `header` | `string` | `'Idempotency-Key'` | HTTP header, GraphQL cũng đọc header này, và là tên header của transport với microservice. |
| `replayHeaders` | `string[]` | không có | Các response header được replay thêm ngoài `Location`, `Content-Type`, `Content-Language`, `Content-Location`, `ETag` và `Last-Modified`. `Set-Cookie` và các header mà platform ghi cho mọi response sẽ bị từ chối lúc khởi động. |
| `encryption` | một object có `keys` | tắt | Mã hóa AES-256-GCM cho các record được lưu. `keys` liệt kê các `Buffer` 32 byte hoặc chuỗi có ít nhất 32 ký tự, khóa mới nhất đứng đầu. Xem [Mã hóa biên lai được lưu](/reliability/idempotency#encrypt-stored-receipts). |
| `allowInMemoryStorage` | `boolean` | `false` | Cho phép một ứng dụng production khởi động mà không có store được đăng ký. |
| `isGlobal` | `boolean` | `true` | Đăng ký module ở phạm vi global. |

Mọi khoảng thời gian đều nhận số mili giây hoặc một chuỗi như `'45s'`, `'48h'` hay `'7d'`.

Mặc định, key được lấy từ các nguồn sau:

| Context | Nguồn mặc định |
| --- | --- |
| HTTP | Header `Idempotency-Key` (tùy chọn `header`) |
| GraphQL | Argument `idempotencyKey` của mutation, sau đó là header |
| Microservice | Thuộc tính `idempotencyKey` của payload, sau đó là header của transport có tên do `header` chỉ định |

Một key gồm 1 đến 255 ký tự ASCII in được. Một số trong payload được tính theo các chữ số của nó.

##### Event <a id="events"></a>

`IdempotencyEvents.events$` phát ra mọi event, và mỗi event cũng được publish trên một diagnostics channel. Mọi payload đều có `type`, `context` (`'http'`, `'graphql'` hoặc `'rpc'`), `handler` (chẳng hạn `OrdersController.pay`), `key` và, nếu có, `scope`.

| Type | Channel | Type của payload | Các field khác | Khi nào |
| --- | --- | --- | --- | --- |
| `replayed` | `nestjs:idempotency:replayed` | `IdempotencyReplayedEvent` | `status` | Một lần retry nhận kết quả đã lưu, hoặc một event trùng lặp bị bỏ qua |
| `rejected` | `nestjs:idempotency:rejected` | `IdempotencyRejectedEvent` | `code`, `status` | Một lời gọi bị từ chối trước khi handler của nó chạy. Không có `key` với `IDEMPOTENCY_KEY_REQUIRED` và `IDEMPOTENCY_KEY_INVALID`. |
| `lock-lost` | `nestjs:idempotency:lock-lost` | `IdempotencyLockLostEvent` | `phase` (`'extend'`, `'complete'` hoặc `'release'`) | Kết quả của lần thử không có trong store, nên một lần retry có thể chạy lại handler |

`IdempotencyEvent` là union của ba type payload.

##### Lỗi <a id="errors"></a>

Các lần từ chối mang một trong các code sau, có type là `IdempotencyErrorCode`. Qua HTTP, code nằm trong body của response. Trong GraphQL, nó nằm trong `extensions` của lỗi field, kèm `httpStatus` và, với 409, `retryAfter`. Trên microservice, payload của `RpcException` có `status`, `code`, `statusCode`, `message` và, với 409, `retryAfter`.

| Code | Status | Message | Nguyên nhân |
| --- | --- | --- | --- |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | An idempotency key is required for this operation. | Không có key, khi `required: true` |
| `IDEMPOTENCY_KEY_INVALID` | 400 | The idempotency key must be 1 to 255 printable ASCII characters. | Key quá dài, có ký tự khác, hoặc không phải chuỗi hay số |
| `IDEMPOTENCY_KEY_IN_USE` | 409, kèm `Retry-After` | A request with this idempotency key is still being processed. | Lời gọi đầu tiên với key này vẫn đang chạy |
| `IDEMPOTENCY_KEY_REUSED` | 422 | This idempotency key was already used for a different request. | Cùng key nhưng fingerprint khác |
| `IDEMPOTENCY_RECORD_UNREADABLE` | 500 | The stored result for this idempotency key could not be read. | Record đã lưu không giải mã được, chẳng hạn vì khóa của nó đã bị gỡ |
