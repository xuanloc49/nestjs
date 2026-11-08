#### Mã hóa biên lai được lưu

Response được lưu là toàn bộ biên lai: id biên lai của payment provider, số tiền, và bốn số cuối của thẻ. Chúng nằm trong `idempotency_keys` ở dạng văn bản thuần, trong mọi bản backup và mọi bản dump của database, nên hãy mã hóa các record khi lưu trữ.

Các khóa mã hóa là secret mà ứng dụng nên đọc khi nó khởi động, chứ không phải khi `app.module.ts` được import, nên hãy chuyển sang `forRootAsync()`. Store vẫn giữ nguyên, là một provider của `AppModule` tự đăng ký, và factory trả về các tùy chọn:

[[CODE:21]]

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

#### Thanh toán qua GraphQL

Website của cửa hàng thanh toán qua một GraphQL mutation. Đăng ký `GraphQLModule` trong `AppModule`:

[[CODE:22]]

Sau đó thêm mutation vào resolver đơn hàng, cạnh các query của nó. Trong GraphQL, key có thể đến từ header `Idempotency-Key`, như với REST, hoặc từ một argument. Một argument đặt key vào schema, nơi các code generator và người review có thể thấy nó. Nó cũng hợp với các GraphQL client, vốn thường đặt header một lần cho mỗi kết nối thay vì cho mỗi operation. `@Idempotent()` đọc argument `idempotencyKey` của mutation khi có, và đọc header trong trường hợp ngược lại, nên resolver chỉ cần khai báo argument:

[[CODE:23]]

`PayOrderDto` là class mà endpoint REST dùng, được thêm `@InputType()` và `@Field()`, còn `PaymentReceipt` là một `@ObjectType()` với các field của biên lai. Resolver dùng cùng `AuthGuard`, guard này đọc request từ GraphQL context. `scope` của module nhận cùng request đó, nên ở đây key cũng theo từng người dùng. Argument là một `String` non-null, nên GraphQL validation đã từ chối sẵn một operation không có nó:

[[CODE:24]]

Một lần retry với cùng variables trả về kết quả `payOrder` đã lưu, với cùng các type mà resolver đã trả về, nên một field `Date` được replay thành `Date`. Record key được nối thêm đường dẫn của field, như `usr_alice:<key>:payOrder`, vì một operation có thể chứa nhiều mutation. Mỗi field được lưu và replay riêng, và alias là một phần của đường dẫn, nên một lần retry phải gửi cùng document.

Một lần từ chối là một lỗi trên field đó, không phải một HTTP status. Response vẫn là 200, vì các field khác trong cùng operation có thể đã thành công, còn status và thời gian chờ retry nằm trong `extensions` (đã bỏ `locations`):

[[CODE:25]]

Cũng vì lý do đó, các lần replay GraphQL không đặt header `Idempotent-Replayed`.

#### Khử trùng lặp event order.paid

Sau một lần thanh toán, `OrdersService` phát ra event `order.paid`, và service vận chuyển sắp xếp người giao hàng. Trong thực tế, event được gửi ít nhất một lần (at least once). Một publisher retry sau khi timeout, hoặc một broker (RabbitMQ, Kafka, NATS JetStream) gửi lại một message chưa được ack, có thể gửi cùng một event hai lần, và khách hàng nhận được hai kiện hàng.

Khử trùng lặp event cần một id giống nhau cho mọi lần gửi của một event, nên nó được suy ra từ dữ liệu chứ không phải sinh mới ở mỗi lần gửi. Một đơn hàng chỉ được thanh toán một lần, nên `OrdersService` dùng `order-paid:` theo sau là id đơn hàng. Đánh dấu [event handler](/microservices/basics#event-based) bằng `@Idempotent()`, và trỏ `keyFrom` tới id đó:

[[CODE:26]]

Mặc định, microservice handler đọc key từ thuộc tính `idempotencyKey` của payload, sau đó từ một header của transport có tên do tùy chọn `header` chỉ định. Ở đây, `keyFrom` đọc `eventId` thay vào đó, và `required: true` từ chối các event không có nó.

Service vận chuyển là một ứng dụng riêng, có database riêng và `IdempotencyModule` riêng, và nó đăng ký cùng class store:

[[CODE:27]]

[[CODE:28]]

Có vài chi tiết khác so với API:

- Không có `scope`, vì event id là duy nhất trong toàn bộ hệ thống.
- `ttl` là 7 ngày, vì một message có thể quay lại từ dead-letter queue rất lâu sau lần xử lý đầu tiên.
- Record thuộc về một handler: record key kết thúc bằng class và method của handler, như `order-paid%3Aord_1001:ShippingController.onOrderPaid`. Nest chạy mọi handler được đăng ký cho một event, nên một handler thứ hai cho `order.paid`, chẳng hạn một handler gửi email mã vận đơn, sẽ giữ record riêng và vẫn xử lý mỗi event một lần.

Một event trùng lặp được xử lý theo một trong hai cách:

- Nếu lần gửi đầu tiên đã hoàn tất, bản trùng lặp bị bỏ qua. Kết quả đã lưu được "replay", và vì event không có reply, không có gì xảy ra.
- Nếu lần gửi đầu tiên vẫn đang chạy, bản trùng lặp bị từ chối với `IDEMPOTENCY_KEY_IN_USE`, và Nest log lỗi đó. Với một transport có ack message, như RabbitMQ hoặc Kafka, đừng ack lần gửi đó là đã xử lý. Hãy để transport gửi lại nó sau, khi đó nó sẽ bị bỏ qua.

Dù theo cách nào, người giao hàng cũng chỉ được đặt một lần. Ngay từ đầu, các lần retry thanh toán HTTP không tạo ra event trùng lặp, vì một request được replay không bao giờ tới được `OrdersService`.

#### Tinh chỉnh TTL và cách xử lý thất bại

Các giá trị mặc định là điểm khởi đầu. Đây là cấu hình cuối cùng của API:

[[CODE:29]]

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

#### Chạy thử

Khởi động service vận chuyển, và API với `DATABASE_URL` (đã áp dụng migration), `IDEMPOTENCY_KEYS` và sandbox của payment provider đã được cấu hình. Sandbox mất khoảng nửa giây để trả lời. Các output bên dưới đã được lược bớt, chỉ giữ các header liên quan.

Một lần thanh toán không có key bị từ chối:

[[CODE:30]]

Lời gọi đầu tiên có key sẽ trừ tiền thẻ:

[[CODE:31]]

Một lần retry với cùng key nhận cùng biên lai, tới cả `paidAt`, và payment provider không được gọi:

[[CODE:32]]

Cùng key với một thẻ khác là một bug phía client:

[[CODE:33]]

Cuối cùng, gửi đồng thời hai request với một key mới, cho đơn hàng còn lại. Một request được trừ tiền, và request kia nhận 409 kèm `Retry-After: 2` trong khi payment provider vẫn đang xử lý:

[[CODE:34]]

> info **Hint** `--json` cần curl 7.82 trở lên, và `%header` trong `-w` cần curl 7.84 trở lên.

#### Testing

Trong các test end-to-end, hãy giữ cấu hình thật của ứng dụng, nhưng override provider `DrizzleIdempotencyStore` bằng một `InMemoryIdempotencyStore` thuần. Một instance thuần không tự đăng ký, nên module fallback về store trong bộ nhớ của nó, và vì Nest không bao giờ tạo `DrizzleIdempotencyStore`, không có gì truy vấn database (một pool node-postgres chỉ kết nối ở query đầu tiên, nên `DrizzleModule` cũng không mở kết nối nào). Khóa mã hóa vẫn lấy từ `IDEMPOTENCY_KEYS`, nên hãy đặt nó trong môi trường test, ví dụ với `test.env` trong `vitest.config.mts`.

Mock payment provider với một độ trễ nhỏ, để hai request gửi cùng lúc chồng lấn lên nhau:

[[CODE:35]]

Khi ứng dụng đã khởi tạo, `app.get(IdempotencyStorage).source` trả về store đang dùng, ở đây là store trong bộ nhớ. Method `peek(key)` của nó trả về record thô dưới một record key như `usr_alice:key-1` (`state`, `fingerprint` và `response`), để assert những điều như "lần thanh toán bị từ chối đã được lưu". Hãy test store của riêng bạn một cách độc lập, bằng contract suite từ [Lưu key trong PostgreSQL](/reliability/idempotency#store-keys-in-postgresql), với một server thật. Để giữ store Drizzle trong các test end-to-end, hãy thay database mà `DrizzleModule` đã đăng ký, bằng `overrideProvider(getDrizzleToken()).useValue(db)` (`getDrizzleToken` đến từ `@nestjs/drizzle`), trong đó `db` là một Drizzle database trên PGlite đã được migrate bằng các migration của bạn. Project ví dụ test mã hóa, GraphQL, event và phần tinh chỉnh theo cách đó.

Xem [End-to-end testing](/fundamentals/testing#end-to-end-testing) để biết thêm về cách thiết lập testing.

#### Checklist cho production

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

#### Hợp đồng của store

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
