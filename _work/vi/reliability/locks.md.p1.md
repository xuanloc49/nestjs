### Distributed lock

`@nestjs/locks` chạy một scheduled job, hoặc bất kỳ đoạn code nào khác, trên một instance tại một thời điểm, với các lease mà mọi instance của ứng dụng kiểm tra trong một store dùng chung.

Một cửa hàng online bán thức ăn và đồ dùng cho mèo chạy hai scheduled job bằng `@nestjs/schedule`. Mỗi đêm lúc 02:00, một job export gửi hóa đơn trong ngày tới hệ thống kế toán, và cứ năm phút một lần, một job đối soát yêu cầu kho kiểm đếm toàn bộ hàng và ghi kết quả vào bảng sản phẩm. Cả hai đều chạy ổn trên một instance. Trong production, API đơn hàng chạy trên ba instance, và `@nestjs/schedule` kích hoạt mọi `@Cron()` trên từng instance:

- Hệ thống kế toán ghi nhận mỗi hóa đơn ba lần.
- Kho bị yêu cầu ba lần kiểm đếm toàn bộ mỗi năm phút. Một lần kiểm đếm toàn bộ phân trang qua cả danh mục, và vào cuối tháng nó mất hơn năm phút, nên tick tiếp theo bắt đầu một lần kiểm đếm thứ hai song song với lần đầu, rồi lần thứ ba.

Những cách sửa thông thường đều có lỗ hổng. Một instance `RUN_JOBS=true` chạy ổn cho tới khi một lần rolling deploy có hai instance như vậy trong một phút, hoặc instance chạy job lại chính là instance bị chết. Một key `SET NX` trong Redis ở đầu job chạy ổn cho tới khi bên giữ nó bị dừng lâu hơn TTL của key, do một lần garbage collection stop-the-world hoặc phía sau một network partition: một instance khác lấy key, và khi instance đầu tiên tỉnh lại, nó chạy nốt lần chạy của mình trong khi tin rằng mình vẫn giữ key. Lại hai bên cùng ghi, và không bên nào biết. `waitForCompletion: true` trên `@Cron()` ngăn một job chồng lấn chính nó, nhưng chỉ trên một instance.

`@nestjs/locks` biến một job thành thứ mà một instance nắm giữ: một **lease** mà bên giữ liên tục gia hạn khi nó còn sống, được kiểm tra trong một store mà mọi instance dùng chung. Hai decorator đặt nó lên một scheduled job, `@OnOneInstance()` và `@WithoutOverlapping()`, theo tinh thần của `onOneServer()` và `withoutOverlapping()` trong Laravel. Bên dưới chúng là một distributed lock mà bạn cũng có thể tự lấy, với hai thứ mà một lock cần có để đáng tin: một `AbortSignal` bị abort khi lease bị mất, và một **fencing token** tăng dần với mỗi lần một key được lấy, để một thao tác ghi từ một bên giữ đã bị dừng quá thời hạn lease có thể bị từ chối. Một leader election cũng chính là lease đó, được giữ chừng nào leader còn sống.

Trong bài hướng dẫn này, bạn sẽ thêm nó vào cửa hàng, trên PostgreSQL với Drizzle:

- Chứng minh các lần chạy trùng lặp bằng một test, trên ba instance của ứng dụng.
- Giữ các lock trong một bảng của database ứng dụng.
- Chạy mỗi job trên một instance, với việc chuyển giao khi instance đó chết.
- Giữ một lần kiểm đếm kho dài không chồng lấn chính nó.
- Fence các thao tác ghi kho, để một instance bị dừng không thể ghi đè lên một lần kiểm đếm mới hơn.
- Chạy export thủ công từ một admin endpoint, không bao giờ chạy song song với lần chạy theo lịch.
- Giữ các lock trong Redis thay vào đó.
- Giữ luồng cảnh báo của kho trên một instance, bằng một leader election.

#### Cài đặt

Để bắt đầu, hãy cài dependency cần thiết:

[[CODE:1]]

#### Nhìn thấy vấn đề

Đây là ứng dụng trước bài hướng dẫn. Job export hàng đêm lấy mọi đơn hàng đã đặt chưa có hóa đơn, upload batch đó, và đánh dấu các đơn hàng bằng batch id:

[[CODE:2]]

Hệ thống kế toán ghi nhận mọi batch mà nó nhận được, nên một batch được upload hai lần sẽ bị ghi nhận hai lần. Job đối soát yêu cầu kho cung cấp số lượng và ghi chúng lại:

[[CODE:3]]

Các biểu thức cron lấy từ môi trường, với lịch thật làm mặc định, để các test và phần [Chạy thử](/reliability/locks#try-it) có thể tăng tốc hoặc tắt chúng. `AccountingClient` và `WarehouseClient` là bản thay thế cho hai hệ thống bên ngoài; mỗi cái đếm những gì nó được yêu cầu làm. Database là của ứng dụng, được đăng ký bằng `DrizzleModule` trong `app.module.ts` và inject bằng `@InjectDrizzle()`.

> info **Hint** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để thiếu một biến sẽ dừng ứng dụng ngay lúc khởi động thay vì ở request đầu tiên, và đọc các giá trị từ `ConfigService`.

Trước khi thay đổi bất cứ điều gì, hãy chứng minh vấn đề. Test khởi động ba instance của ứng dụng trong một process, trên một database (PostgreSQL in-process bằng [PGlite](https://pglite.dev), hoặc một PostgreSQL server nếu có cấu hình), và kích hoạt các lịch chạy trên từng instance qua registry riêng của `@nestjs/schedule`, giống như khi tới 02:00:

[[CODE:4]]

Ba batch, mỗi batch có cùng ba đơn hàng, và ba lần kiểm đếm toàn bộ. Bảng `orders` sau đó trông vẫn ổn, mọi đơn hàng đều có batch id, đó là lý do chuyện này không bị phát hiện cho tới khi bộ phận kế toán gọi điện.

#### Giữ lock trong database của bạn

`@nestjs/locks` hoạt động ngay khi bạn import `LocksModule`, trên một store trong bộ nhớ. Store đó chỉ loại trừ các bên gọi trong một process: ba instance sẽ mỗi cái có store riêng, cả ba sẽ cùng lấy được "cái" lock đó, và không có gì thay đổi. Các lock cần một store mà mọi instance dùng chung, và package không đi kèm store nào. Nó định nghĩa hợp đồng, interface `LockStore`, và bạn implement nó trong một provider của ứng dụng bằng database mà ứng dụng đã có.

Phần này trình bày store đó hai lần: đầu tiên với Drizzle trên PostgreSQL, được đăng ký qua [`@nestjs/drizzle`](/data/drizzle) với driver `pg`, là lộ trình của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối phần, cùng store đó cho một ứng dụng dùng TypeORM làm ORM. Hãy chọn một trong hai, hoặc giữ các lock trong Redis với [store trên Redis](/reliability/locks#the-store-on-redis). Với Drizzle, một lock là một dòng cho mỗi key:

[[CODE:5]]

drizzle-kit viết migration:

[[CODE:6]]

[[CODE:7]]

Hợp đồng có ba method, và mỗi method nhận lock key và một `owner` trước tiên: một id ngẫu nhiên mà package sinh ra cho mỗi lần lấy lock. Các khoảng thời gian được truyền vào dưới dạng số mili giây nguyên.

- `acquire(key, owner, ttl)` lấy key nếu không có lock nào còn hiệu lực đang giữ nó, và trả về fencing token của lock, hoặc báo rằng key đã bị chiếm. Nó phải nguyên tử: trong bất kỳ số bên gọi đồng thời nào, chỉ đúng một bên được thắng.
- `renew(key, owner, ttl)` là heartbeat. Nó dời thời hạn thành `ttl` tính từ bây giờ, nếu `owner` vẫn đang giữ một lock còn hiệu lực trên key. Package gọi nó mỗi `ttl / 3` trong khi một lock đang được giữ.
- `release(key, owner)` trả lại lock, nếu `owner` vẫn đang giữ nó.

Điều kiện "nếu `owner` vẫn đang giữ nó" phải được kiểm tra trong cùng câu lệnh thực hiện việc ghi: nếu kiểm tra bằng một lần đọc riêng trước đó, một lần tiếp quản có thể chen vào giữa. Và store đo `ttl` bằng đồng hồ của chính nó, để mọi instance thống nhất về thời điểm một lock hết hạn bất kể đồng hồ của chúng nói gì. Với Drizzle, đó là một câu insert có điều kiện và hai câu update có điều kiện:

[[CODE:8]]

Vài điều về store này:

- **`acquire()` là một câu lệnh duy nhất.** Câu insert thắng một key chưa có dòng nào; `ON CONFLICT DO UPDATE` với `WHERE` của nó tiếp quản một key đã được giải phóng hoặc đã hết hạn, và PostgreSQL kiểm tra lại `WHERE` đó trên dòng sau khi đã lock nó. Trong nhiều bên gọi chạy đua giành cùng một key, một bên nhận lại một dòng và các bên còn lại không nhận được gì. Một câu `SELECT` theo sau là một câu `INSERT` sẽ để nhiều bên lọt vào.
- **Fencing token đến từ một sequence**, được lấy bên trong câu lệnh, sau khi lock dòng. Một sequence không bao giờ quay ngược, nên mỗi lần lấy một key sẽ nhận token lớn hơn lần trước, xuyên qua các lần giải phóng và hết hạn. Nó có những khoảng trống, vì một bên gọi thua cuộc vẫn đã tiêu thụ một giá trị; điều đó không quan trọng. `greatest()` biến token riêng của dòng thành mức sàn cho token tiếp theo: nếu sequence có lúc quay ngược (khôi phục từ backup, failover sang một replica bị chậm), một key vẫn không thể nhận một token mà nó đã từng có. [Fence các thao tác ghi](/reliability/locks#fence-the-writes) cho thấy token dùng để làm gì.
- **`release()` giữ lại dòng** và xóa owner, để lần lấy tiếp theo luôn đi theo nhánh update. Nếu xóa dòng, một câu insert đã lấy token từ sớm có thể thắng key sau khi một bên giữ sau đó đã giải phóng nó, và phát ra một token nhỏ hơn.
- **`clock_timestamp()`**, chứ không phải `now()`: `now()` là thời điểm bắt đầu transaction, chính là thứ mà thời hạn của lock không được phụ thuộc vào.
- Tại sao dùng bảng mà không dùng `pg_advisory_lock()`: một advisory lock gắn với một session, nên bên giữ phải giữ một kết nối lấy ra từ pool trong suốt critical section, sẽ mất lock mà không biết khi nào nếu kết nối đó bị ngắt, không thể gia hạn nó, và không có thời hạn cho một bên giữ bị dừng cũng như không có fencing token. Một dòng dữ liệu có tất cả những thứ đó, qua bất kỳ pool nào.

Package đi kèm hợp đồng dưới dạng một test suite, để bạn có thể kiểm chứng store trước khi tin dùng nó. `lockStoreContract()` trả về các case dùng được với mọi test runner, và `concurrent: true` thêm vào các tình huống race:

[[CODE:9]]

Ví dụ chạy cùng suite đó trên một PostgreSQL server với pool 20 kết nối và 32 bên gọi chạy đua, nơi các câu lệnh thực sự chồng lấn. Hãy chạy nó theo cách đó trong CI, trên phiên bản PostgreSQL mà bạn chạy trong production.

Giờ hãy đăng ký module và store, cạnh `DrizzleModule` của ứng dụng. Store là một provider thuần; constructor của nó tự đăng ký, nên không có gì phải cấu hình:

[[CODE:10]]

`LocksModule.forRoot()` nhận một `ttl` (mặc định là `'30s'`: thời gian một lock tồn tại nếu không được gia hạn, tức là bao lâu sau một lần crash thì một instance khác tiếp quản), một `storeTimeout` (mặc định là `'10s'`: thời gian chờ mỗi lời gọi store trước khi nó thất bại, để một store ngừng trả lời không thể làm treo một job, một request hay quá trình shutdown), một `clock` cho test, và `allowInMemoryStorage`. `forRootAsync()` nhận cùng các tùy chọn từ một factory. Module là global, nên `Locks`, `LocksContext` và `LocksStorage` có sẵn ở mọi nơi. Khi khởi tạo, nó log ra store đang dùng:

[[CODE:11]]

Không có gì được đăng ký, dòng log sẽ nêu tên `InMemoryLockStore` và ý nghĩa của nó. Với `NODE_ENV=production` và không có gì được đăng ký, ứng dụng không khởi động, vì trong bộ nhớ thì mọi instance sẽ cùng lấy được một lock và chạy cùng một job:

[[CODE:12]]

**Với TypeORM.** Cùng store đó cho một ứng dụng dùng TypeORM làm ORM, trên cùng bảng và sequence. Drizzle vẫn là lộ trình của bài hướng dẫn: hãy dùng store này thay cho store ở trên, chứ không phải dùng song song. Bảng là một entity, và mọi cột đều khai báo type của nó, để TypeORM CLI, vốn load entity mà không có decorator metadata, thấy cùng schema với ứng dụng:

[[CODE:13]]

TypeORM CLI và `TypeOrmModule` dùng chung một bộ tùy chọn, trong một file data source:

[[CODE:14]]

Tạo migration từ entity, trên một database đã áp dụng các migration trước đó của bạn. CLI cần một TypeScript loader cho file data source; ở đây dùng `tsx`:

[[CODE:15]]

TypeORM không có entity cho sequence, nên migration nó tạo ra chỉ tạo bảng. Hãy tự thêm sequence vào đó, trước bảng, và drop nó trong `down()`:

[[CODE:16]]

`migrations` trong data source liệt kê nó. Áp dụng nó, và kiểm tra rằng entity và database khớp nhau. Bước kiểm tra không so sánh sequence, nên sequence bạn thêm vào không bị tính là thay đổi:

[[CODE:17]]

Giờ đến store, theo cùng các quy tắc với bản Drizzle:

[[CODE:18]]

- **`acquire()` là câu lệnh duy nhất được viết bằng SQL**, qua `dataSource.query()`. `orUpdate()` của insert query builder viết ra một `ON CONFLICT DO UPDATE`, với `WHERE` trong tùy chọn `overwriteCondition` của nó, nhưng nó đặt mọi cột từ `EXCLUDED`: token sẽ là token mà câu insert đã lấy trước khi dòng bị lock, thứ mà một bên giữ key sau đó có thể đã vượt qua. SQL lấy token trong `SET`, sau khi lock dòng, như store Drizzle làm.
- **`renew()` và `release()`** là update query builder với owner và thời hạn trong `WHERE`, và đọc `affected`. Không bao giờ dùng `save()`, và không gọi `findOneBy()` trước: một lần đọc trước khi ghi sẽ để một lần tiếp quản chen vào giữa.
- **Token được chuyển đổi bằng `Number()`.** `pg` trả về cột `bigint` dưới dạng chuỗi, và package từ chối một token dạng chuỗi.
- **Hãy dùng nó** thay cho store Drizzle: `TypeOrmModule.forRoot(dataSourceOptions)` trong `AppModule`, và `TypeOrmLockStore` trong providers của nó thay cho `DrizzleLockStore`. Nó inject `DataSource` mà `TypeOrmModule` cung cấp, và dòng log lúc khởi động sẽ nêu tên `TypeOrmLockStore`.

Contract suite chạy trên nó mà không cần thay đổi, kể cả các case về concurrency. TypeORM kết nối qua `pg`, nên suite cần một PostgreSQL server và sẽ bị bỏ qua nếu không có. Thêm ba case nữa kiểm tra rằng token của một key vẫn tiếp tục tăng sau khi sequence quay ngược, rằng entity và migration khớp nhau (đúng những gì `migration:generate --check` kiểm tra), và rằng store tự đăng ký khi được cung cấp trong một module:

[[CODE:19]]

> info **Hint** Dùng Prisma? [Hợp đồng của store](/reliability/locks#the-store-contract), sau phần hướng dẫn, liệt kê những gì store phải đảm bảo và cách Prisma diễn đạt các method nguyên tử. Hãy test store của bạn với cùng các case đó.

#### Chạy mỗi job trên một instance

Thêm `@OnOneInstance()` vào cả hai job, cạnh `@Cron()`:

[[CODE:20]]

[[CODE:21]]

[[CODE:22]]

Đó là toàn bộ thay đổi. Những gì nó làm:

- **Instance đầu tiên có scheduler kích hoạt job sẽ lấy lease của job**, một lock được đặt tên theo key với hậu tố `:owner`, và liên tục gia hạn nó mỗi `ttl / 3` chừng nào nó còn sống. Nó chạy tick này và mọi tick sau đó.
- **Trên các instance khác, tick bị bỏ qua**: lời gọi resolve mà không chạy method, một dòng debug cho biết lý do, và `LocksEvents.jobSkips$` báo cáo điều đó ([Event](/reliability/locks#events)). Không có gì được xếp hàng chờ; lịch chạy của job chính là lịch chạy.
- **Khi owner chết**, nó ngừng gia hạn, lease hết hạn sau `ttl` (30 giây), và instance đầu tiên có tick tới sau thời điểm đó sẽ tiếp quản job. Khi owner shutdown một cách bình thường, nó hoàn tất các lần chạy đang dở, trả lại lease, và tick tiếp theo ở bất kỳ đâu sẽ lấy nó.
- **Các decorator bọc method.** `@nestjs/schedule` không bị patch, và nó không biết chúng ở đó: explorer của nó tìm thấy metadata `@Cron()` trên wrapper, theo bất kỳ thứ tự decorator nào, và gọi wrapper, wrapper này hỏi `LocksModule` xem lời gọi này có được chạy không. Job `@Interval()` và `@Timeout()` hoạt động theo cách tương tự, và việc tự gọi method cũng vậy.
- **Key** mặc định là `ClassName.methodName`. Hãy đặt nó cho một job không bao giờ được chạy hai lần: đổi tên class hoặc method sẽ thay đổi giá trị mặc định, và trong một lần rolling deploy, instance cũ và mới sẽ mỗi bên chạy job một lần. Hai job có cùng key mặc định sẽ thất bại lúc khởi động, và một job có key trùng với lease của job khác (`<key>:owner`) hoặc key của một election cũng vậy: chúng sẽ âm thầm loại trừ lẫn nhau.

Quyền sở hữu được giữ ổn định một cách có chủ ý. Một cuộc đua cho mỗi tick sẽ đơn giản hơn, nhưng một tick không phải là một khoảnh khắc: đồng hồ của các instance lệch nhau hàng chục mili giây, nên một lock theo tick sẽ phải tồn tại lâu hơn lần chạy một khoảng bằng độ lệch, và một job nhanh sẽ cần một bản ghi "đã chạy lúc" để ngăn một instance bị trễ chạy lại tick đó. Một lease được giữ giữa các tick không có những vấn đề đó, đổi lại một instance sẽ chạy mọi tick của một job, điều mà một scheduled job hiếm khi bận tâm.

Còn một tick không ai chạy thì sao? Trong khi owner bị down, tối đa `ttl` các tick sẽ bị bỏ qua, và job export hàng đêm có thể rơi đúng vào ba mươi giây đó. **Các tick bị lỡ không được chạy bù**: không có gì ghi lại lần cuối một job đã chạy. Hãy viết job làm mọi thứ đã tới hạn thay vì chỉ làm của "hôm qua". Job export lấy mọi đơn hàng chưa có hóa đơn, nên một đêm nó không chạy sẽ được bù vào đêm tiếp theo; job đối soát ghi số lượng hiện tại, nên một tick bị lỡ chỉ làm dữ liệu cũ đi năm phút. Một job mà mỗi tick làm một việc riêng biệt sẽ giữ bản ghi đó trong bảng riêng của nó.

Test từ [Nhìn thấy vấn đề](/reliability/locks#see-the-problem), với các job mới và store, giờ ghi nhận mỗi hóa đơn một lần, và test làm một instance ngừng gia hạn (đồng hồ của nó đứng yên, như thể process đã chết) cho thấy việc chuyển giao:

[[CODE:23]]

[[CODE:24]]

`ManualLockClock` là đồng hồ của package dành cho test: nó chỉ dịch chuyển khi được yêu cầu. Một instance dùng nó không bao giờ gia hạn, nên database, với đồng hồ riêng của nó, sẽ cho các lock của instance đó hết hạn sau `ttl`.

#### Đừng để một lần chạy dài chồng lấn chính nó

`@OnOneInstance()` đặt job đối soát lên một instance. Nó không ngăn instance đó bắt đầu lần kiểm đếm tiếp theo trong khi lần trước vẫn đang chạy, và một `@Cron()` thông thường cũng không. Vào cuối tháng, lần kiểm đếm mất hơn năm phút, nên kho nhận lần kiểm đếm toàn bộ thứ hai, rồi thứ ba. Hãy thêm `@WithoutOverlapping()`:

[[CODE:25]]

Giờ một lần chạy lấy thêm một lock thứ hai, được đặt tên theo cùng key (hai decorator trên một method dùng chung key này), giữ nó suốt lần chạy, gia hạn nó, và giải phóng nó khi lần chạy kết thúc. Một tick thấy lock đang bị giữ sẽ bị bỏ qua, trên instance này hay bất kỳ instance nào khác: các tick trong lúc một lần kiểm đếm dài bị bỏ đi, và tick đầu tiên sau nó sẽ chạy. Nếu lần chạy crash, lock hết hạn sau `ttl` và tick tiếp theo sẽ chạy. `@WithoutOverlapping()` đứng riêng, không có `@OnOneInstance()`, nghĩa là "bất kỳ instance nào, mỗi lúc một lần chạy".

Test điều khiển hai instance trên một `ManualLockClock`, giữ một lần kiểm đếm chưa kết thúc, và tua đồng hồ qua ba tick:

[[CODE:26]]

`clock.advance('5m')` kích hoạt mọi lần gia hạn tới hạn trên đường đi, theo thứ tự, và chờ từng lần tới được store, nên mười lăm phút của một lần chạy dài chỉ mất một khoảnh khắc, với các lock của lần chạy được gia hạn suốt thời gian đó.

#### Fence các thao tác ghi

Một lease không thể ngăn một bên giữ đang bị dừng. Lấy job đối soát trên instance A làm ví dụ: nó đọc số lượng từ kho (hạt cá hồi: 12), rồi A bị treo, do một lần garbage collection stop-the-world, swap, di chuyển VM, hay một debugger. Nó ngừng gia hạn. Ba mươi giây sau database cho các lock của nó hết hạn, và B tiếp quản job ở tick tiếp theo của nó: nó đọc số lượng mới hơn (đã bán và giao ba bao kể từ đó: hạt cá hồi: 9) và ghi chúng. Rồi A tỉnh lại và chạy nốt lần chạy của mình, với số lượng nó đã đọc trước khi bị dừng. Hạt cá hồi quay về 12, và cửa hàng bán ba bao mà nó không có.

Signal của A bị abort ở lần gia hạn tiếp theo, khi database từ chối nó, nhưng một thao tác ghi đã đang trên đường đi vẫn sẽ được thực hiện. Hãy lưu ý lease hứa hẹn và không hứa hẹn điều gì. Một bên giữ tự đếm hạn chót của mình, `ttl` tính từ thời điểm nó gửi lần gia hạn cuối cùng mà store đã xác nhận, tức là trước khi store xử lý nó: một bên giữ đang chạy sẽ bỏ cuộc không muộn hơn thời điểm hết hạn của store, nên signal của nó bị abort trước khi bất kỳ instance nào khác có thể lấy key. Khoảng hở chỉ tồn tại với một bên giữ không chạy (bị dừng, bị stop, event loop bị block): từ thời điểm hết hạn của store cho tới khi nó chạy trở lại, nó vẫn tin rằng mình giữ lock. Thứ ngăn thao tác ghi của nó là **fencing token**: mỗi lần lấy một key đều nhận một token lớn hơn mọi token mà key đó từng có, và tài nguyên được ghi giữ token cao nhất mà nó đã thấy và từ chối token thấp hơn. Token của A thấp hơn của B, nên thao tác ghi muộn của A không cập nhật gì cả.

Bảng sản phẩm có thêm một cột cho việc này:

[[CODE:27]]

[[CODE:28]]

[[CODE:29]]

Repository chỉ ghi một số lượng nếu chưa có lần chạy nào với token lớn hơn đã ghi sản phẩm đó, và ghi lại token mà nó dùng để ghi, trong cùng câu lệnh:

[[CODE:30]]

Job lấy token, và signal, từ `LocksContext`. `@nestjs/schedule` gọi method mà không có tham số, nên context mang chúng, qua `AsyncLocalStorage`, tới mọi service mà job gọi:

[[CODE:31]]

Token là của run lock, một token mới và cao hơn cho mỗi lần chạy. Signal bị abort khi lock của lần chạy hoặc lease của instance bị mất, và reason của nó là một `LockLostError` cho biết việc mất lock được phát hiện thế nào: store đã từ chối một lần gia hạn, hoặc `ttl` đã trôi qua mà không có lần gia hạn nào tới được store. Hãy truyền signal cho những gì job gọi tới, `fetch`, database driver, một HTTP client; một job bỏ qua nó sẽ tiếp tục chạy, như trong bất kỳ process nào. Không có gì bị kill.

Test tái hiện việc bị dừng trên PostgreSQL. Instance A chạy trên một `ManualLockClock`, nên nó ngừng gia hạn; warehouse client giữ lần kiểm đếm của A chưa kết thúc sau khi A đã đọc nó; hàng trên kệ thay đổi; B tiếp quản 1.2 giây sau (`ttl` của test là một giây) và ghi hạt cá hồi: 9. Rồi lần kiểm đếm của A tiếp tục:

[[CODE:32]]

Với job của phần trước, thao tác ghi cũ được thực hiện và hạt cá hồi quay về 12. Với token, database từ chối nó, và job log ra rằng nó đã bỏ qua ba thao tác ghi cũ. Còn một lần chạy tới được lần gia hạn tiếp theo trước khi ghi sẽ dừng lại ở signal, với một `LockLostError`, và không ghi gì cả. Package log một cảnh báo cho mỗi lock bị mất và phát ra một event `lock-lost`, vì một lock bị mất nghĩa là một instance khác có thể đang ở trong cùng critical section ngay lúc này: chỉ có token giữ hai bên tách biệt.
