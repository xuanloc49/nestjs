### Idempotency key

`@nestjs/idempotency` giúp route, GraphQL mutation và message handler an toàn khi retry: mỗi `Idempotency-Key` chỉ chạy handler một lần, và các lần retry nhận lại kết quả của nó.

Một khách hàng của cửa hàng online bán thức ăn và đồ dùng cho mèo thanh toán hạt cá hồi và cát vệ sinh trong ứng dụng di động của cửa hàng, trên điện thoại khi đang đi tàu. Ứng dụng gửi `POST /orders/ord_1001/pay`. Server trừ tiền thẻ qua payment provider, nhưng response không bao giờ tới được điện thoại. Ứng dụng không thể phân biệt request bị mất với response bị mất, nên nó retry. Không có cơ chế bảo vệ, lần retry sẽ hỏng theo một trong hai cách:

- Nó tới sau khi request đầu tiên đã xong. Đơn hàng đã ở trạng thái `paid`, nên khách hàng nhận lỗi cho một lần thanh toán đã thành công.
- Nó tới trong khi request đầu tiên vẫn đang chờ payment provider. Cả hai request đều vượt qua bước kiểm tra "đơn hàng có còn pending không?", và thẻ bị trừ tiền hai lần.

Một **idempotency key** giải quyết cả hai. Client sinh một key duy nhất cho mỗi lần thử thanh toán và gửi nó trong header `Idempotency-Key` ở mọi lần retry. Server chạy handler một lần cho mỗi key, lưu kết quả, và trả lời mọi lần retry bằng kết quả đó. `@nestjs/idempotency` hiện thực điều này cho HTTP route, GraphQL mutation và microservice handler chỉ với một decorator, `@Idempotent()`. Hành vi HTTP của nó tuân theo [bản nháp header Idempotency-Key](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) của IETF.

Trong bài hướng dẫn này, bạn sẽ làm endpoint thanh toán trở nên idempotent, hướng dẫn ứng dụng di động retry an toàn, chuyển key sang PostgreSQL (hoặc Redis), mã hóa các biên lai được lưu, bảo vệ GraphQL mutation, và khử trùng lặp các event `order.paid` mà service vận chuyển tiêu thụ.

#### Yêu cầu trước

Bài hướng dẫn này bắt đầu từ API đơn hàng của cửa hàng, vốn đã có:

- Một `OrdersModule` với `OrdersService` và `OrdersController`. Một `Order` có `id`, `userId`, `items`, `total` tính bằng cent, và `status` là `'pending'`, `'paid'`, `'shipped'` hoặc `'refunded'`.
- Một `PaymentProviderClient` bọc SDK của payment provider. Nó throw một `HttpException` 402 khi thẻ bị từ chối, và một `ServiceUnavailableException` (503) khi provider bị down.
- Một `AuthGuard` validate bearer token và đặt `req.user` (xem [Xác thực](/security/authentication#issue-tokens-to-the-mobile-app)), cùng một parameter decorator `@CurrentUser()` để đọc nó.
- Một `ValidationPipe` global, và một TCP client cho service vận chuyển, được đăng ký dưới tên `SHIPPING_SERVICE`.
- Dữ liệu của nó nằm trong PostgreSQL, qua Drizzle, với database được đăng ký bằng `@nestjs/drizzle` (xem [Drizzle](/data/drizzle)). Dùng TypeORM? [Lưu key trong PostgreSQL](/reliability/idempotency#store-keys-in-postgresql) có phần store cho TypeORM ở cuối.

Đây là method mà chúng ta cần bảo vệ:

[[CODE:1]]

Riêng bước kiểm tra status không thể ngăn việc trừ tiền hai lần: hai request tới cùng lúc đều thấy `pending` trước khi một trong hai tới được `markPaid()`.

Cài đặt package:

[[CODE:2]]

#### Làm endpoint thanh toán trở nên idempotent

Đăng ký `IdempotencyModule` một lần, trong root module:

[[CODE:3]]

Module này là global. Nó đăng ký một interceptor cho toàn ứng dụng, interceptor này không làm gì với các handler không được đánh dấu `@Idempotent()`, nên không route nào khác bị thay đổi hành vi.

`scope` cho key của mỗi người dùng một namespace riêng. Không có nó, mọi client dùng chung một namespace, và một key mà người dùng này chọn có thể replay biên lai của người dùng khác. Có nó, Alice và Bob đều có thể gửi `Idempotency-Key: 1` mà không bao giờ thấy kết quả của nhau. Vì guard chạy trước interceptor, `req.user` đã được đặt khi `scope` chạy, và một request chưa xác thực bị từ chối trước khi nó có thể dùng mất một key. Nếu một người dùng đã đăng nhập gọi một handler `@Idempotent()` không có `scope`, module sẽ log một cảnh báo, một lần cho mỗi handler. Ở những nơi cố ý dùng chung một namespace, chẳng hạn một webhook dùng event id của provider làm key, hãy đặt `scope: false`.

Giờ hãy đánh dấu handler:

[[CODE:4]]

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

#### Gửi key từ ứng dụng di động

Server chỉ có thể khử trùng lặp những gì client gửi một cách nhất quán. Ứng dụng tuân theo hai quy tắc:

- Nó tạo key khi khách hàng bấm **Pay**, chứ không phải mỗi request một lần. Mọi lần retry của lần thanh toán đó đều gửi cùng key, kể cả sau khi ứng dụng bị kill và khởi động lại, nên key được lưu cùng lần thanh toán đang chờ.
- Nó chỉ tạo key mới khi khách hàng đưa ra một quyết định mới, chẳng hạn chọn thẻ khác sau khi bị từ chối. Gửi một key cũ với body khác sẽ nhận 422.

[[CODE:5]]

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

#### Lưu key trong PostgreSQL

Store trong bộ nhớ không đủ cho production. Các record của nó biến mất mỗi khi process dừng, ở mỗi lần deploy hoặc thay container, nên một lần retry tới sau đó sẽ chạy lại việc thanh toán. Và khi API chạy trên nhiều instance, một lần retry rơi vào instance khác sẽ không tìm thấy record, và hai instance có thể cùng lấy được lock. Các record cần một store dùng chung có thể "tạo nếu chưa tồn tại" một cách nguyên tử.

`@nestjs/idempotency` không đi kèm store nào. Nó định nghĩa hợp đồng, interface `IdempotencyStore`, và bạn implement nó trong một provider của ứng dụng, bằng database hoặc Redis client mà ứng dụng đã có. Interface có bốn method. Mỗi method nhận record key và một owner trước tiên, và các khoảng thời gian được truyền vào dưới dạng số mili giây nguyên:

- `acquire(key, owner, fingerprint, lockTtl)` tạo lock, hoặc trả về record đã tồn tại: đang xử lý, hoặc đã hoàn tất kèm response. Nó phải nguyên tử: trong bất kỳ số lời gọi đồng thời nào cho một key còn trống, chỉ đúng một lời gọi được thắng.
- `complete(key, owner, response, ttl)` biến lock thành một record đã hoàn tất, nếu `owner` vẫn đang giữ nó.
- `release(key, owner)` xóa lock, nếu `owner` vẫn đang giữ nó, để một lần retry có thể chạy lại handler.
- `extend(key, owner, lockTtl)` đặt lại thời hạn của lock thành `lockTtl` tính từ bây giờ, nếu `owner` vẫn đang giữ nó. Interceptor gọi nó mỗi `lockTtl / 3` trong khi handler chạy và kết quả của nó đang được lưu.

`owner` là một id ngẫu nhiên cho mỗi lần thử, gọi là fencing token. Nếu một lần thử ngừng gia hạn lock (chẳng hạn instance của nó bị crash) và một lần retry tiếp quản sau `lockTtl`, các lời gọi `extend()`, `complete()` hay `release()` của lần thử cũ sẽ không làm gì cả, thay vì ghi đè lên record của lần retry. Vì vậy điều kiện "nếu `owner` vẫn đang giữ nó" phải được kiểm tra trong cùng thao tác nguyên tử thực hiện việc ghi: nếu kiểm tra bằng một lần đọc riêng trước đó, một lần tiếp quản có thể chen vào giữa.

Phần này trình bày store đó hai lần: đầu tiên với Drizzle, là lộ trình của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối phần, cùng store đó cho một ứng dụng dùng TypeORM làm ORM. Hãy chọn một trong hai.

Store giữ dữ liệu trong PostgreSQL, với Drizzle, nên các record có một bảng trong Drizzle schema:

[[CODE:6]]

Primary key là một hash SHA-256 của record key, vì record key (một scope, key của client và, với GraphQL, đường dẫn của field) có thể dài hơn mức PostgreSQL cho phép trong một entry của index. Response dùng `json` thay vì `jsonb`, vì `jsonb` từ chối `\u0000` bên trong một chuỗi, và body của response có thể chứa ký tự đó. Tạo migration bằng drizzle-kit, và áp dụng nó bằng `npx drizzle-kit migrate` như thường lệ:

[[CODE:7]]

[[CODE:8]]

Store implement mỗi method bằng query builder của Drizzle. Nó inject database bằng `@InjectDrizzle()` từ `@nestjs/drizzle`, và constructor đăng ký store với `IdempotencyStorage`, một registry mà `IdempotencyModule` export:

[[CODE:9]]

Database được gán type `NodePgDatabase`, và các test bên dưới ép kiểu database PGlite của chúng về type này, vì store chỉ dùng phần query builder mà cả hai driver đều có. Mỗi method là một câu lệnh duy nhất mà PostgreSQL chạy một cách nguyên tử, không cần transaction:

- `acquire()` insert lock, hoặc tiếp quản một dòng đã hết hạn, bằng một câu `INSERT ... ON CONFLICT DO UPDATE ... WHERE expires_at <= now`. Khi nhiều bên gọi tranh nhau một key, PostgreSQL để một bên ghi và kiểm tra lại `WHERE` cho các bên còn lại dựa trên dòng của bên thắng, nên chúng không nhận lại dòng nào và đọc lock của bên thắng thay vào đó. Nếu dòng đó biến mất ở giữa (bị giải phóng, hoặc hết hạn), `acquire()` sẽ chạy lại một vòng nữa.
- `complete()`, `extend()` và `release()` kiểm tra owner, và việc lock chưa hết hạn, trong `WHERE` của câu lệnh ghi. Chúng đếm số dòng mà `returning()` trả về, cách này hoạt động giống nhau trên mọi driver của Drizzle.
- Các dòng đã hết hạn bị bỏ qua ngay lập tức, và request tiếp theo với cùng key sẽ dùng lại dòng đó. Để xóa phần còn lại, hãy gọi `prune()` từ một scheduled job, ví dụ với `@Interval()` từ `@nestjs/schedule`. Nó kiểm tra lại thời hạn ngay trong câu `DELETE`, nên một dòng mà một lần retry đã tiếp quản trong lúc đó sẽ được giữ lại.

Thời điểm hết hạn lấy từ đồng hồ của mỗi instance (`Date.now()`), nên hãy giữ các đồng hồ được đồng bộ, như NTP làm. Mỗi request idempotent thêm một hoặc hai câu lệnh vào connection pool, cộng một câu `UPDATE` mỗi `lockTtl / 3` trong khi handler của nó chạy.

Store là một provider bình thường. Đăng ký database bằng `DrizzleModule` (xem [Drizzle](/data/drizzle)), và thêm store vào providers của `AppModule`:

[[CODE:10]]

> info **Hint** Ứng dụng đọc `DATABASE_URL`, và khi biên lai được mã hóa thì cả `IDEMPOTENCY_KEYS`, từ `process.env`. Một ứng dụng thực tế load môi trường của nó qua `@nestjs/config`, với một validation schema dừng việc khởi động khi thiếu biến, và inject `ConfigService` vào các factory này thay vào đó.

Lúc khởi động, module log ra store mà nó dùng, `IdempotencyStorage: DrizzleIdempotencyStore`, và sau đó nó ngừng nhận đăng ký:

- Một ứng dụng chỉ có một store. Lời gọi `registerSource()` thứ hai sẽ throw, nêu tên cả hai class.
- Hãy đăng ký từ constructor của một singleton provider. Registry bị khóa khi `IdempotencyModule` khởi tạo, nên một store đăng ký muộn hơn (từ một lifecycle hook, theo từng request, hoặc trong một lazy-loaded module) sẽ throw thay vì bị âm thầm bỏ qua.
- Không có store nào được đăng ký, module giữ record trong bộ nhớ. Trong production (`NODE_ENV=production`), nó từ chối khởi động theo cách đó, trừ khi bạn đặt `allowInMemoryStorage: true`, tức chấp nhận rằng mỗi lần restart hoặc deploy đều quên sạch các record.

Mọi store đều được test bằng cùng một contract suite, được `@nestjs/idempotency/testing` export dưới dạng các test case thuần dùng được với mọi test runner. Nó bao gồm từng method, việc kiểm tra owner, thời hạn, và, với `concurrent`, các tình huống race mà một store kiểu đọc-rồi-ghi sẽ làm sai. Project ví dụ chạy nó trên store này với PGlite, và với PostgreSQL qua một `pg` pool, nơi 32 bên gọi tranh nhau mỗi key trên tối đa 16 kết nối:

[[CODE:11]]

**Với TypeORM.** Cùng store đó cho một ứng dụng dùng TypeORM làm ORM, trên cùng bảng. Drizzle vẫn là lộ trình của bài hướng dẫn: hãy dùng store này thay cho store ở trên, chứ không phải dùng song song. Bảng là một entity, và mọi cột đều khai báo type của nó, để TypeORM CLI, vốn load entity mà không có decorator metadata, thấy cùng schema với ứng dụng:

[[CODE:12]]

TypeORM trả về cột `bigint` dưới dạng chuỗi, nên một transformer đọc lại `expiresAt` thành số. Cột response được gán type `object` thay vì `IdempotencyStoredPayload`, vì body kiểu `unknown` của payload không khớp với các type insert của TypeORM; store sẽ ép kiểu nó khi đọc một record. TypeORM CLI và `TypeOrmModule` dùng chung một bộ tùy chọn, trong một file data source:

[[CODE:13]]

Tạo migration từ entity, áp dụng nó, và kiểm tra rằng entity và database khớp nhau. CLI cần một TypeScript loader cho file data source; ở đây dùng `tsx`:

[[CODE:14]]

Migration mà nó tạo ra, `1790321611502-Idempotency.ts`, chính là các câu lệnh `CREATE TABLE` và `CREATE INDEX` của migration Drizzle, và `migrations` trong data source liệt kê nó. Giờ đến store, theo cùng các quy tắc với bản Drizzle:

[[CODE:15]]

- **`acquire()`** là cùng câu `INSERT ... ON CONFLICT DO UPDATE ... WHERE expires_at <= now`, thông qua insert query builder: `orUpdate()` liệt kê các cột mà một lần tiếp quản ghi đè, tùy chọn `overwriteCondition` của nó chính là `WHERE`, và `returning()` chỉ trả về một dòng cho bên gọi đã ghi.
- **`complete()`, `extend()` và `release()`** là `update()` và `delete()` trên entity manager, với owner và `MoreThan(now)` trong điều kiện của chúng, và chúng đọc `affected`. Không bao giờ dùng `save()`: nó đọc dòng trước, nên một lần tiếp quản có thể chen vào giữa.
- **`prune()`** dựng subquery chọn các dòng đã hết hạn bằng một select query builder, và đặt SQL của nó vào `WHERE` của câu `DELETE`, cạnh điều kiện kiểm tra thời hạn.

Store inject `DataSource` mà `TypeOrmModule` cung cấp. Đăng ký module với các tùy chọn của data source thay cho `DrizzleModule`, và store thay cho `DrizzleIdempotencyStore`:

[[CODE:16]]

Contract suite chạy trên nó mà không cần thay đổi. TypeORM kết nối qua `pg`, nên suite cần một PostgreSQL server và sẽ bị bỏ qua nếu không có. Thêm một case nữa kiểm tra rằng entity và migration khớp nhau, đúng những gì `migration:generate --check` kiểm tra:

[[CODE:17]]

`startPostgres()` là một test helper tạo một database dùng một lần trên PostgreSQL server, hoặc bỏ qua suite nếu không có server. Ví dụ này cũng chạy hai instance của `AppModule` bản TypeORM trên một database, một instance đang trừ tiền trong khi instance kia trả lời 409.

> info **Hint** Dùng Prisma? [Hợp đồng của store](/reliability/idempotency#the-store-contract), sau phần hướng dẫn, cho thấy Prisma diễn đạt các câu lệnh này thế nào. Hãy kiểm tra store của bạn bằng cùng suite đó.

#### Lưu key trong Redis

Nếu API của bạn đã chạy Redis, nó có thể giữ các record ở đó thay vì trong PostgreSQL. Redis rất hợp với store này: một record là một hash nhỏ mà Redis tự cho hết hạn, nên không cần job dọn dẹp, và một key nóng, chẳng hạn một client retry một lần thanh toán mỗi giây, chỉ tốn một vòng truy cập bộ nhớ thay vì một row lock trong database chính. Cái giá là phải vận hành, bảo vệ và backup thêm một store thứ hai, và Redis phải được cấu hình để không bao giờ evict các record (xem checklist cho production).

Mỗi method là một Lua script, được Redis chạy một cách nguyên tử:

[[CODE:18]]

Mỗi record là một hash tại `idem:<scope>:<key>`, với các field `state`, `fp` (fingerprint), `owner` và `resp` (response đã lưu dưới dạng JSON). Hash tự hết hạn: `lockTtl` sau lần gia hạn cuối khi đang xử lý, và sau `ttl` khi đã hoàn tất, nên không cần job dọn dẹp. Mỗi script chỉ chạm tới một key, nên store cũng hoạt động với Redis Cluster. Redis chạy một script một cách nguyên tử, nhưng nó không hoàn tác các thao tác ghi của script khi một lệnh phía sau thất bại. Chẳng hạn `PEXPIRE` từ chối giá trị lẻ của mili giây, và nếu thất bại sau `HSET`, nó sẽ để lại một lock không bao giờ hết hạn. Đó là lý do interceptor truyền cho store số mili giây nguyên.

Nest inject Redis client, và constructor đăng ký store, giống như với store PostgreSQL. Một ứng dụng chỉ có một store, nên `RedisIdempotencyStore` thay thế store kia trong `AppModule`:

[[CODE:19]]

`RedisModule` đại diện cho Redis module của ứng dụng: một global module cung cấp một ioredis client dưới token `REDIS`, ví dụ với `useFactory: () => new Redis(process.env.REDIS_URL!)`, và đóng nó bằng `quit()` trong `onApplicationShutdown()`, sau khi package đã xử lý xong các request đang chạy. `RedisClient` không yêu cầu gì ngoài `eval()`, thứ mà một instance `Redis` của ioredis có sẵn. Lúc khởi động, dòng log ghi `IdempotencyStorage: RedisIdempotencyStore`, và các quy tắc của registry từ store PostgreSQL vẫn áp dụng: một store, đăng ký từ constructor.

Project ví dụ cũng chạy contract suite trên store này:

[[CODE:20]]

> info **Hint** Project ví dụ của bài hướng dẫn này không có Redis server, nên các test của nó chạy store trên một bản giả in-process implement cùng bốn script bằng JavaScript. Như vậy bao phủ được logic của store và cách nó đọc reply, nhưng không bao phủ bản thân phần Lua. Hãy chạy contract suite trên một Redis thật, ví dụ trong một container, trước khi tin dùng store. Không có `advanceTime`, suite sẽ chờ hết hạn thật, mất khoảng mười giây.

Các bước còn lại hiển thị `DrizzleIdempotencyStore` trong phần khai báo module. Với Redis, hãy đăng ký `RedisIdempotencyStore` thay vào đó: mã hóa, service vận chuyển và các tùy chọn tinh chỉnh hoạt động y như vậy, và khi bật mã hóa, field `resp` chứa envelope đã được niêm phong thay cho cột `response`.
