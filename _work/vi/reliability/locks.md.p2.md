#### Chạy export thủ công

Thỉnh thoảng bộ phận kế toán yêu cầu export trước 02:00. Một admin endpoint chạy nó, và nó không bao giờ được chạy song song với lần chạy theo lịch, trên bất kỳ instance nào. Lần chạy theo lịch giữ lock được đặt tên theo key của nó; endpoint lấy cùng lock đó bằng `Locks.withLock()`, chờ tối đa hai giây cho một lần chạy sắp kết thúc:

[[CODE:33]]

Job export key dưới dạng hằng số, cũng có thêm `@WithoutOverlapping()`, và tách phần công việc ra khỏi method theo lịch để endpoint có thể gọi nó và trả về kết quả:

[[CODE:34]]

[[CODE:35]]

`withLock(key, fn, options)` chạy `fn` dưới lock và giải phóng lock dù `fn` resolve hay throw. `wait` là khoảng thời gian tiếp tục thử, kèm backoff, trước khi bỏ cuộc với một `LockNotAcquiredError`; mặc định là chỉ thử một lần. `acquire(key, options)` cũng vậy nhưng không có callback: nó resolve một `Lock`, hoặc `null` khi key đã bị chiếm, và bạn tự giải phóng nó, hoặc dùng `await using`. Một `Lock` có `fencingToken` và `signal`, và bên trong `withLock()` thì `LocksContext` cũng có, y như trong một job.

Cả hai cũng nhận một `signal` riêng, chẳng hạn signal của request, để dừng việc chờ. Nó cũng dừng việc chờ store: một lời gọi vẫn đang chờ câu trả lời của store sẽ reject với reason của signal, `fn` không chạy, và một lock mà store cấp sau đó sẽ được trả lại cho store. `wait` không cắt ngang một lời gọi store đang trên đường đi; `storeTimeout` của module mới làm việc đó, nên một lời gọi mất tối đa `wait` cộng `storeTimeout`. Một store không trả lời trong vòng `storeTimeout` sẽ làm lời gọi thất bại với một `LockStoreTimeoutError`.

Cả `LockNotAcquiredError` lẫn `LockStoreTimeoutError` đều không mang HTTP status: tranh chấp lock và một store bị treo không phải lỗi của bên gọi, nên handler tự quyết định. Ở đây một lock đã bị chiếm là `409`, còn mọi thứ khác được throw lại. Trong khi export đang chạy thủ công, tick theo lịch trên bất kỳ instance nào sẽ thấy lock đang bị giữ và bỏ qua.

> info **Hint** `AdminGuard` chỉ là placeholder. Hãy bảo vệ route bằng [phân quyền](/security/authorization) thật của ứng dụng.

#### Store trên Redis

Store là một hợp đồng, nên nó có thể nằm ở bất cứ đâu mà các instance của bạn đã cùng truy cập. Nếu đó là Redis, mỗi method là một Lua script, được Redis chạy một cách nguyên tử:

[[CODE:36]]

`SET NX PX` chỉ lấy key nếu nó còn trống, hết hạn theo đồng hồ của Redis tính bằng mili giây, và `INCR` trong cùng script lấy token từ một bộ đếm dùng chung cho mọi key. Fencing chỉ bền vững ngang với bộ đếm đó. Nó không bao giờ hết hạn, và không bao giờ được quay ngược: hãy cho Redis cơ chế persistence (AOF, hoặc RDB với khoảng thời gian ngắn) và `maxmemory-policy noeviction`, vì một bộ đếm bắt đầu lại từ 1 (một lần restart không có persistence, một lệnh `FLUSHALL`) sẽ phát ra những token mà các bên giữ đã có, và một lock bị evict do thiếu bộ nhớ là một lock bị mất. Một lần failover sang một replica bất đồng bộ cũng có thể làm mất những lần ghi cuối cùng: một lock được lấy ngay trước đó, đó là trường hợp bên giữ bị dừng mà token bao phủ, nhưng cũng có thể là những lần tăng cuối cùng của bộ đếm, sau đó bên giữ tiếp theo có thể lấy một token mà bên trước đã có, và token không còn phân biệt được chúng nữa. Ở những nơi fencing phải giữ vững qua một lần failover, hãy giữ các lock trong database, nơi sequence nằm trong cùng WAL với các dòng dữ liệu, hoặc replicate Redis một cách đồng bộ.

Trên Redis Cluster, `ACQUIRE` như đang viết sẽ thất bại với lỗi `CROSSSLOT`: một cluster chỉ chạy script khi mọi key của nó hash vào cùng một slot, mà key của lock và bộ đếm thì không. Hãy đặt tên cả hai dưới một hash tag, `{{ '{' }}locks{{ '}' }}:key:<key>` và `{{ '{' }}locks{{ '}' }}:fencing-token`: khi đó cluster chỉ hash phần `locks`, nên bộ đếm và mọi lock dùng chung một slot, trên một shard. Một bộ đếm dưới tên mới, hoặc trên một cluster mới, sẽ bắt đầu lại từ 1, chính là lần khởi động lại mà nó không bao giờ được phép có. Trước lần acquire đầu tiên trên nó, hãy dừng các instance đang dùng key cũ và đặt bộ đếm mới bằng giá trị của bộ đếm cũ (`SET {{ '{' }}locks{{ '}' }}:fencing-token <value>`), để token tiếp theo lớn hơn mọi token đã được phát ra.

`redis.module` cung cấp client dưới token `REDIS`; ví dụ dùng một client tối giản có signature `eval()` giống ioredis, để không phụ thuộc vào gì, còn trong ứng dụng của bạn thì đó là `new Redis(process.env.REDIS_URL)`:

[[CODE:37]]

Thay provider trong application module, và không có gì khác thay đổi:

[[CODE:38]]

Ví dụ chạy contract suite trên một `redis-server` thật, với tám kết nối để các lời gọi chồng lấn, rồi chạy ba instance của ứng dụng trên đó:

[[CODE:39]]

Hãy đóng Redis client trong `onApplicationShutdown()`, như module làm; `@nestjs/drizzle` đóng database pool trong cùng giai đoạn đó. Nest chạy từng giai đoạn shutdown cho toàn bộ ứng dụng trước khi sang giai đoạn tiếp theo: package trả lại các lease trong `onModuleDestroy()` và giải phóng mọi lock khác còn đang giữ trong `beforeApplicationShutdown()`, nên tới lúc `onApplicationShutdown()` của bất kỳ module nào chạy, không có gì của package còn cần tới kết nối, bất kể thứ tự import. Một tick hoặc một election vẫn đang chờ store khi quá trình shutdown bắt đầu sẽ ngừng chờ: tick bị bỏ qua, và một lock mà store cấp sau đó sẽ được trả lại cho store, nên một store bị treo không làm chậm lần deploy.

#### Giữ luồng dữ liệu của kho trên một instance

Kho đẩy các cảnh báo sắp hết hàng qua một luồng dữ liệu (feed) chỉ cho phép một kết nối cho mỗi cửa hàng. Đó không phải là một scheduled job; đó là một kết nối mà một instance nên giữ chừng nào nó còn sống, và một instance khác nên tiếp quản khi nó bị down. Đó là một leader election, và nó chính là lease giống như quyền sở hữu một job, được giữ một cách có chủ đích:

[[CODE:40]]

[[CODE:41]]

`@LeaderElection(key)` đặt trên một singleton provider. Từ `onApplicationBootstrap`, mọi instance đều cố lấy lease trên key, và tiếp tục thử mỗi `ttl / 3`; instance đang giữ nó sẽ gia hạn nó. `onLeadershipAcquired(lock)` chạy khi instance này trở thành leader, với `signal` và `fencingToken` của lease; `onLeadershipLost(lock)` chạy khi nó thôi làm leader, vì lease bị mất hoặc vì nó tự rút lui, lúc shutdown hoặc sau khi `onLeadershipAcquired()` throw. Tùy chọn `ttl` đặt ttl của lease; mặc định là 30 giây của module, nên một leader bị crash sẽ được thay thế trong vòng nửa phút, và một leader shutdown bình thường sẽ được thay thế ở lần thử tiếp theo của các instance khác.

Test khởi động ba instance và cho thấy một kết nối, một lần chuyển giao khi shutdown, và điểm mù của leader bị dừng:

[[CODE:42]]

Một leader bị dừng vẫn được kết nối cho tới khi lần gia hạn tiếp theo của nó thất bại, và nhận những gì feed gửi tới trong khoảng đó. Đó là cùng điểm mù như trong [Fence các thao tác ghi](/reliability/locks#fence-the-writes), với cùng câu trả lời: những gì leader làm thay cho cả nhóm phải mang theo token của lease.

#### Chạy thử

Tạo database và áp dụng migration:

[[CODE:43]]

Khởi động ba instance trên các port 3001, 3002 và 3003, với `ADMIN_TOKEN=s3cret` và job đối soát kho mỗi mười giây thay vì năm phút, để có gì đó mà theo dõi: `STOCK_RECONCILIATION_CRON='*/10 * * * * *'`. Mỗi instance log ra lock store mà nó đã đăng ký. Instance khởi động đầu tiên làm leader cho feed của kho, và lấy job đối soát ở tick đầu tiên, trước khi hai instance còn lại khởi động xong:

[[CODE:44]]

Hai instance còn lại bỏ qua mọi tick, ở mức debug:

[[CODE:45]]

Bảng lock hiển thị lease, run lock (đã được giải phóng, nên owner của nó là null, và token của nó tăng sau mỗi lần chạy) và lease của feed. Mọi lock hết hạn ba mươi giây sau lần gia hạn cuối cùng, theo đồng hồ của database:

[[CODE:46]]

Các fencing token có những khoảng trống: một lần lấy lock bị từ chối vẫn đã tiêu thụ một giá trị từ sequence. Chạy export thủ công. Không có admin token, guard trả lời `403`; sau đó gửi đồng thời hai request, tới hai instance khác nhau:

[[CODE:47]]

Một request đã lấy lock và export ba đơn hàng đang chờ. Request kia chờ nó, lấy lock khi nó được giải phóng, và không còn gì để export. Một request chờ quá hai giây sẽ nhận `409`. Instance đã chạy export log ra batch:

[[CODE:48]]

Giờ hãy kill instance đầu tiên, instance đang chạy job đối soát và làm leader cho feed, mà không cho nó cơ hội dọn dẹp:

[[CODE:49]]

Một lúc không có gì xảy ra: hai instance còn lại tiếp tục bỏ qua, vì các lease vẫn còn trong bảng. Ba mươi giây sau lần gia hạn cuối cùng, từng lease hết hạn. Lease của feed hết hạn trước, vì nó được gia hạn theo lịch riêng, và tick tiếp theo tiếp quản job:

[[CODE:50]]

Lần này hãy dừng owner mới bằng `Ctrl+C`. Các shutdown hook của nó trả lại cả hai lease (`main.ts` gọi `app.enableShutdownHooks()`):

[[CODE:51]]

Instance cuối cùng lấy job ở tick tiếp theo, và lấy feed ở lần tranh cử tiếp theo, chỉ vài giây sau thay vì ba mươi giây:

[[CODE:52]]

Cuối cùng dừng instance cuối cùng bằng `Ctrl+C`. Nó rút lui khỏi feed trước khi tắt:

[[CODE:53]]

#### Testing

Một ứng dụng import `LocksModule` mà không đăng ký store nào sẽ chạy trên store trong bộ nhớ, nên một test end-to-end với một instance không cần gì cả: mọi tick đều chạy, một lần. Để loại store Drizzle ra khỏi một test, hãy override provider của nó bằng một `InMemoryLockStore` thuần; một instance thuần không tự đăng ký, nên mặc định trong bộ nhớ được áp dụng.

Để test đúng mục đích của package, hãy chạy nhiều instance trong một process. Một instance là một ứng dụng Nest; các instance của một ứng dụng dùng chung một store. Helper của ví dụ khởi động một instance trên database dùng chung, với các bản giả và tùy chọn `LocksModule` của test:

[[CODE:54]]

- **Dùng chung database.** Trên PGlite, mọi instance nhận cùng một Drizzle database bằng cách override database mà `DrizzleModule` đăng ký (`getDrizzleToken()`), với các migration thật đã được áp dụng; `DrizzleLockStore` inject nó bằng `@InjectDrizzle()`, nên các instance dùng chung bảng lock giống như trong production. Với một PostgreSQL server, mỗi instance mở pool riêng từ URL của database. Không có database, hãy dùng chung một `InMemoryLockStore` giữa các instance bằng cách đăng ký nó trong từng instance với `LocksStorage.registerSource()` và tùy chọn `replace` của nó trước `init()`.
- **Tự kích hoạt các job.** Gọi method (`await job.exportInvoices()`) trên từng instance, hoặc đi qua `@nestjs/schedule` với `schedulerRegistry.getCronJob(name).fireOnTick()`. Cả hai đều tới được wrapper. Trỏ các lịch chạy thật tới một ngày không bao giờ tới: `vitest.config.mts` của ví dụ đặt hai biến cron thành ngày 29 tháng 2 lúc 3 giờ sáng.
- **Kiểm soát thời gian.** Override `LOCKS_MODULE_OPTIONS` với một `ManualLockClock`, và mọi lần gia hạn, hạn chót và `wait` trong instance đó chỉ dịch chuyển khi test tua đồng hồ: `await clock.advance('5m')` kích hoạt những gì tới hạn trên đường đi, theo thứ tự, và chờ từng lần gia hạn tới được store. Một instance mà bạn không tua đồng hồ chính là một process bị dừng. Với PGlite hoặc một server, đồng hồ của store là thời gian thực, nên một `ttl` ngắn (`'1s'`) và một `sleep` sẽ làm các lock của instance bị dừng hết hạn; với store trong bộ nhớ, hãy cho nó cùng `ManualLockClock` và thời hạn sẽ dịch chuyển theo đồng hồ đó.
- **Assert trên log** hoặc trên `LocksEvents`: instance nào chạy một job, mọi tick bị bỏ qua (`jobSkips$`), mọi lock bị mất và mọi thay đổi leader (`events$`). Các event cũng được publish trên các diagnostics channel `nestjs:locks:job-skipped`, `nestjs:locks:lock-lost`, `nestjs:locks:leadership-acquired` và `nestjs:locks:leadership-lost`.
- **Test store của bạn** bằng contract suite, như các store Drizzle, TypeORM và Redis đã làm, trên server mà bạn chạy trong production.

Xem [End-to-end testing](/fundamentals/testing#end-to-end-testing) để biết thêm về cách thiết lập testing.

#### Checklist cho production

- Đăng ký một store dùng chung, trên database của bạn hoặc Redis, và chạy contract suite trên nó với `concurrent` được bật, trong CI, trên phiên bản mà bạn chạy trong production. Trong production, ứng dụng từ chối khởi động nếu không có store, trừ khi đặt `allowInMemoryStorage`, vốn chỉ đúng cho một instance duy nhất.
- Đặt `key` cho mọi job không bao giờ được chạy hai lần, để một lần đổi tên hoặc một minifier không thể thay đổi nó trong một lần rolling deploy.
- Chọn một `ttl` lớn hơn hẳn thời gian round trip tới store và thời gian event loop bị treo lâu nhất mà bạn chấp nhận, và đủ ngắn để một lần crash không bỏ qua quá nhiều tick. Các lần gia hạn được gửi đi mỗi `ttl / 3`; 30 giây phù hợp với hầu hết các job. Run lock của một job dài được gia hạn với cùng nhịp độ, nên `ttl` của nó không cần bao phủ cả lần chạy.
- Để `storeTimeout` lớn hơn hẳn câu trả lời chậm nhất khi store vẫn khỏe mạnh: một lời gọi store chạy quá mức đó sẽ thất bại, nên tick không chạy và `acquire()` reject với `LockStoreTimeoutError`. Mặc định, 10 giây, cũng giới hạn thời gian một store bị treo (một pool cạn kiệt, một lần failover, một Redis client xếp hàng lệnh khi đang offline) làm chậm một job, một request hay một lần gia hạn.
- Viết job làm những gì đã tới hạn, chứ không phải những gì tick đó nhắm tới. Các tick bị lỡ không được chạy bù: một owner bị crash làm mất tối đa `ttl` các tick, và các tick trong lúc một lần chạy dài bị bỏ qua.
- Truyền `LocksContext.signal` cho những gì job gọi tới, và fence các thao tác ghi không thể hoàn tác bằng `LocksContext.fencingToken`, trong cùng câu lệnh ghi. Cảnh báo khi có `lock-lost` từ `LocksEvents` hoặc diagnostics channel: nó nghĩa là các lần gia hạn đã thất bại lâu hơn `ttl`, vì không kết nối được tới store hoặc event loop bị block, và một instance khác có thể đang chạy cùng critical section.
- Gọi `app.enableShutdownHooks()`, để một lần deploy chuyển giao các lease ngay lập tức thay vì để chúng tự hết hạn. Đóng Redis client trong `onApplicationShutdown()`, giai đoạn mà `@nestjs/drizzle` đóng database pool: package trả lại các lease trong `onModuleDestroy()` và giải phóng mọi lock khác trong `beforeApplicationShutdown()`, những giai đoạn mà Nest hoàn tất trước cho toàn bộ ứng dụng. Một lease có job bắt đầu chưa tới một giây trước khi shutdown sẽ được giữ cho hết giây đó thay vì được trả lại, để các instance kích hoạt cùng tick sẽ bỏ qua nó thay vì chạy nó lần thứ hai.
- Với store Redis, hãy cho Redis cơ chế persistence và `maxmemory-policy noeviction`. Bộ đếm fencing không bao giờ được quay ngược, và một lock không bao giờ được bị evict.
- Với store database, hãy tạo bảng và sequence qua migration, và định cỡ connection pool cho mỗi lock đang giữ một câu lệnh ngắn mỗi lần gia hạn, cộng thêm mỗi instance một câu cho mỗi tick.
- Dù sao vẫn nên giữ đồng hồ của các instance được đồng bộ bằng NTP. Thời hạn được đo trên đồng hồ của store, nhưng một bên giữ tự đếm hạn chót của mình, và `@nestjs/schedule` kích hoạt theo đồng hồ của instance.
- Mức log: các tick bị bỏ qua được log ở mức `debug`. Hãy giữ mức đó một thời gian sau khi rollout, để thấy các job ổn định trên một instance. Để theo dõi lâu dài, hãy đếm `LocksEvents.jobSkips$` theo `job` và `reason` thay vì parse log.

#### Hợp đồng của store

Bài hướng dẫn đã viết store bằng Drizzle, TypeORM và Redis. Phần này tóm tắt những gì bất kỳ `LockStore` nào cũng phải làm, để bạn viết store với một database hoặc ORM khác. [Interface `LockStore`](https://github.com/nestjs/locks/blob/master/lib/interfaces/lock-store.interface.ts) mô tả toàn bộ hợp đồng và các tình huống race mà mỗi quy tắc ngăn chặn.

**Đăng ký.** Store là một singleton provider bình thường gọi `registerSource(this)` trên `LocksStorage` (có thể inject) trong constructor của nó. Registry kiểm tra cấu trúc ngay lập tức, từ chối lần đăng ký thứ hai trừ khi truyền `replace: true`, và bị khóa khi `LocksModule` khởi tạo, đồng thời log ra store đang dùng. Không có gì được đăng ký, module dùng `InMemoryLockStore`, store chỉ loại trừ các bên gọi trong một process. Với `NODE_ENV=production`, việc khởi động sẽ thất bại thay vào đó, trừ khi bạn đặt `allowInMemoryStorage: true`.

**Các method.** Cả ba đều nguyên tử: mỗi method quyết định ai giữ một key, và một lần đọc theo sau là một lần ghi riêng sẽ để hai bên gọi cùng vào critical section, chính là lần chạy trùng lặp mà package sinh ra để ngăn chặn.

| Method | Làm gì | Giữ tính nguyên tử bằng cách nào |
| --- | --- | --- |
| `acquire(key, owner, ttl)` | Lấy key nếu không có lock nào còn hiệu lực đang giữ nó (không có, đã giải phóng, hoặc đã hết hạn), với một fencing token lớn hơn mọi token mà key từng có | Một câu insert tiếp quản một dòng đã giải phóng hoặc đã hết hạn trong cùng câu lệnh, kiểm tra lại thời hạn trong thao tác ghi, nên trong nhiều bên gọi đồng thời chỉ đúng một bên thắng; token được lấy sau bước kiểm tra |
| `renew(key, owner, ttl)` | Dời thời hạn của lock còn hiệu lực của owner thành `ttl` tính từ bây giờ | Một compare-and-set: owner và thời hạn nằm trong `WHERE` của câu lệnh ghi |
| `release(key, owner)` | Giải phóng lock còn hiệu lực của owner (xóa nó, hoặc đánh dấu là đã giải phóng), để bên gọi tiếp theo lấy được ngay. Không bao giờ reset token của key | Một compare-and-set, như `renew()` |

**Những điều khác mà store phải làm đúng**, tất cả đều được suite kiểm tra: một lock đã hết hạn coi như không tồn tại, với mọi method, dù nó đã bị xóa hay chưa (`expires_at > now` trong mọi điều kiện, hoặc để server tự cho nó hết hạn); `ttl` được đo trên đồng hồ của store, tính bằng mili giây, và có thể dài hàng tuần (vượt quá số nguyên 32-bit: `bigint`, `PEXPIRE`); key là chuỗi dài tối đa 500 ký tự, bất kỳ ký tự Unicode nào, được phân biệt chính xác; token là các số nguyên dương an toàn được trả về dưới dạng number. PostgreSQL trả về cột `bigint` dưới dạng chuỗi trừ khi ORM chuyển đổi nó; package từ chối một token như vậy ngay lập tức, kèm một message nêu cách sửa, thay vì để fencing âm thầm bị hỏng.

**Với Prisma.** Store Drizzle là mẫu để làm theo, với cùng bảng và sequence; [Giữ lock trong database của bạn](/reliability/locks#keep-locks-in-your-database) cũng trình bày nó với TypeORM. `acquire()` là một câu `INSERT ... ON CONFLICT (key) DO UPDATE ... WHERE owner IS NULL OR expires_at <= clock_timestamp() RETURNING fencing_token`, với token được lấy trong `SET`, sau khi lock dòng. `upsert()` của Prisma không có điều kiện cho phần update, nên hãy dùng `$queryRaw`. `renew()` và `release()` đặt owner và thời hạn trong `WHERE` của `updateMany()` và kiểm tra `count === 1`. Không dùng `update()` sau `findUnique()`: nó đọc trước.

**Hãy test nó** bằng suite từ `@nestjs/locks/testing`. `lockStoreContract()` trả về các case dùng được với mọi test runner. `concurrent: true` cho 16 bên gọi tranh nhau mỗi key, và tùy chọn `callers` của nó tăng con số đó; hãy chạy nó trên một server có connection pool, nơi các lời gọi thực sự chồng lấn. `advanceTime` dịch đồng hồ của store cho các case về thời hạn; không có nó thì chúng chờ theo thời gian thực, tổng cộng khoảng hai mươi lăm giây, trên các lock có `ttl` (mặc định 2.5 giây, được kiểm tra là vẫn đang bị giữ ở giữa chừng và đã trống sau khi quá hạn một phần sáu: hãy tăng nó cho một store có round trip chậm).
