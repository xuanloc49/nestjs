#### Tham khảo

##### Tùy chọn của module

`LocksModule.forRoot()` nhận các tùy chọn sau; `forRootAsync()` nhận chúng từ `useFactory`, `useClass` hoặc `useExisting` (một class implement `LocksOptionsFactory`). Store không phải là một tùy chọn: hãy đăng ký nó với `LocksStorage`, như trong [Giữ lock trong database của bạn](/reliability/locks#keep-locks-in-your-database).

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `ttl` | `'30s'` | Thời gian một lock tồn tại nếu không được gia hạn, tức là bao lâu sau một lần crash thì một instance khác tiếp quản. Mặc định cho mọi lock, lease và election. Một khoảng thời gian: số mili giây, hoặc một chuỗi như `'15s'` hay `'2m'` |
| `storeTimeout` | `'10s'` | Thời gian chờ mỗi lời gọi store (`acquire()`, `renew()`, `release()`). Quá mức đó, lời gọi thất bại với `LockStoreTimeoutError`: `acquire()` reject, một tick không chạy, một lần gia hạn được thử lại ở nhịp tiếp theo, và một lock mà store cấp sau đó sẽ được trả lại cho store |
| `clock` | Đồng hồ hệ thống | Một `LockClock`. Các test truyền một `ManualLockClock` ([Testing](/reliability/locks#testing)) |
| `allowInMemoryStorage` | `false` | Với `NODE_ENV=production` và không có store được đăng ký, việc khởi động sẽ thất bại; `true` vẫn chạy trên store trong bộ nhớ (một instance) |
| `isGlobal` | `true` | Đăng ký module ở phạm vi global. Đặt ở cấp ngoài cùng của `forRoot()` và `forRootAsync()` |

##### Decorator và method

| API | Tùy chọn | Ghi chú |
| --- | --- | --- |
| `@OnOneInstance()` | `key`, `ttl` | Chạy job trên instance đang giữ lease `<key>:owner`; các instance khác bỏ qua tick. [Chạy mỗi job trên một instance](/reliability/locks#run-each-job-on-one-instance) |
| `@WithoutOverlapping()` | `key`, `ttl` | Bỏ qua một tick trong khi một lần chạy đang giữ lock `<key>`, trên bất kỳ instance nào. [Đừng để một lần chạy dài chồng lấn chính nó](/reliability/locks#dont-let-a-long-run-overlap-itself) |
| `@LeaderElection(key)` | `ttl` | Đặt trên một singleton provider implement `OnLeadershipAcquired`, `OnLeadershipLost` hoặc cả hai. [Giữ luồng dữ liệu của kho trên một instance](/reliability/locks#hold-the-warehouse-feed-on-one-instance) |
| `Locks.acquire(key, options)` | `ttl`, `wait`, `signal` | Resolve một `Lock`, hoặc `null` khi key vẫn bị chiếm. [Chạy export thủ công](/reliability/locks#run-the-export-by-hand) |
| `Locks.withLock(key, fn, options)` | `ttl`, `wait`, `signal` | Chạy `fn(lock)` dưới lock và giải phóng nó; reject với `LockNotAcquiredError` khi key vẫn bị chiếm |

- `key` mặc định là `ClassName.methodName`, và hai decorator job trên một method dùng chung nó. `ttl` mặc định là của module.
- `wait` mặc định là `0` (thử một lần); một khoảng chờ dài hơn sẽ retry kèm backoff. `signal` dừng việc chờ, kể cả với một lời gọi store đang chạy. Cả `wait` lẫn `ttl` đều không giới hạn một lời gọi store: `storeTimeout` của module mới làm việc đó.
- Một `Lock` có `key`, `owner`, `fencingToken`, `signal`, `held`, `release()` và `[Symbol.asyncDispose]`, nên `await using` sẽ giải phóng nó.
- `LocksContext` có `lock`, `fencingToken` và `signal` bên trong một job, một callback `withLock()`, hoặc `run(lock, fn)`; bên ngoài, chúng là `undefined`. [Fence các thao tác ghi](/reliability/locks#fence-the-writes)

##### Event

`LocksEvents.events$` phát ra mỗi event, và publish nó trên channel `node:diagnostics_channel` tương ứng. Mọi payload đều có `type`, `key` và `fencingToken`.

| Event | Channel | Các field khác | Khi nào |
| --- | --- | --- | --- |
| `lock-lost` | `nestjs:locks:lock-lost` | `detectedBy`: `'renewal'` hoặc `'deadline'` | Một bên giữ đã mất lock mà nó đang dùng. Hãy đặt cảnh báo cho nó |
| `leadership-acquired` | `nestjs:locks:leadership-acquired` | Không có | Instance này đã trở thành leader của `key` |
| `leadership-lost` | `nestjs:locks:leadership-lost` | `reason`: `'lost'` hoặc `'released'` | Instance này thôi làm leader: lease bị mất, hoặc nó tự rút lui |

`LocksEvents.jobSkips$` phát ra một event `job-skipped` cho mỗi lời gọi tới một job `@OnOneInstance()` hoặc `@WithoutOverlapping()` đã resolve mà không chạy trước `onApplicationShutdown()`, và publish nó trên `nestjs:locks:job-skipped`. Nó tách biệt với `events$`: mọi instance trừ owner đều bỏ qua từng tick, nên các event này dùng để đếm, không phải để cảnh báo. Payload có `type`, `job` (`ClassName.methodName`), `key` (key của job, không phải lease `<key>:owner` của nó) và `reason`:

| `reason` | Khi nào |
| --- | --- |
| `ownership-unavailable` | Lease `<key>:owner` không được cấp: một instance khác đang giữ nó, hoặc store cấp nó quá muộn để dùng |
| `run-lock-unavailable` | Run lock `<key>` không được cấp: một lần chạy đang diễn ra, hoặc store cấp nó quá muộn để dùng |
| `shutdown` | Ứng dụng đang shutdown |

[[CODE:55]]

Các event là những gì instance này đã thấy, theo cách nó thấy: chúng không ghi lại lần chạy cuối cùng của một job, và không đếm các tick mà scheduler chưa bao giờ kích hoạt. Một lỗi của store không phải là một lần bỏ qua: lời gọi reject, như trước đây.

> warning **Warning** Một subscriber của `events$`, `jobSkips$` hoặc một channel `nestjs:locks:*` không được throw: rxjs và Node sẽ throw lại lỗi của nó dưới dạng `uncaughtException`. Một subscriber cho việc bỏ qua chạy ở mọi tick, nên một bug trong đó sẽ lộ ra chỉ trong vòng một tick.

##### Lỗi

Không lỗi nào mang HTTP status: tranh chấp lock không phải lỗi của bên gọi, nên handler tự chọn response ([Chạy export thủ công](/reliability/locks#run-the-export-by-hand) trả lời `409`).

| Lỗi | Thuộc tính | Xảy ra khi |
| --- | --- | --- |
| `LocksError` | Không có | Class cơ sở của ba lỗi bên dưới |
| `LockNotAcquiredError` | `key`, `waitMs` | `withLock()` không lấy được lock trong khoảng `wait` |
| `LockLostError` | `key`, `fencingToken`, `detectedBy` | Reason mà `signal` của một lock bị mất dùng khi abort: store đã từ chối một lần gia hạn (`'renewal'`), hoặc `ttl` đã trôi qua mà không có lần gia hạn nào được xác nhận (`'deadline'`) |
| `LockStoreTimeoutError` | `key`, `method`, `timeoutMs` | Một lời gọi store (`method`: `'acquire'`, `'renew'` hoặc `'release'`) không trả lời trong vòng `storeTimeout` |
