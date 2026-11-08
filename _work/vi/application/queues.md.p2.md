#### Cài đặt Bull

> info **Note** Nếu bạn dùng BullMQ, hãy bỏ qua phần này và các phần tiếp theo.

Để bắt đầu dùng Bull, hãy cài các dependency cần thiết.

[[CODE:33]]

Sau khi cài xong, import `BullModule` vào root module `AppModule`.

[[CODE:34]]

Method `forRoot()` đăng ký một configuration object `bull` mà mọi queue đăng ký trong ứng dụng đều dùng (trừ khi có chỉ định khác). Một configuration object gồm các thuộc tính sau (tất cả đều là tùy chọn):

- `limiter: RateLimiter` - Tùy chọn điều khiển tốc độ xử lý job của queue. Xem [RateLimiter](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết thêm thông tin.
- `redis: RedisOpts` - Tùy chọn cấu hình kết nối Redis. Xem [RedisOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết thêm thông tin.
- `prefix: string` - Prefix cho mọi key của queue.
- `defaultJobOptions: JobOpts` - Tùy chọn điều khiển thiết lập mặc định cho job mới. Xem [JobOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queueadd) để biết thêm thông tin.
- `settings: AdvancedSettings` - Thiết lập cấu hình queue nâng cao. Thường không nên thay đổi. Xem [AdvancedSettings](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết thêm thông tin.

Các tùy chọn này được truyền thẳng vào constructor `Queue` của Bull. Xem [phần Queue trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết chi tiết.

Để đăng ký một queue, import dynamic module `BullModule.registerQueue()`, như sau:

[[CODE:35]]

> info **Hint** Tạo nhiều queue bằng cách truyền nhiều configuration object (dưới dạng các tham số riêng) vào method `registerQueue()`.

Method `registerQueue()` khởi tạo và/hoặc đăng ký queue. Queue được chia sẻ giữa các module và process kết nối tới cùng một database Redis bên dưới với cùng thông tin đăng nhập. Mỗi queue được xác định bằng thuộc tính `name`. Tên queue vừa đóng vai trò injection token (để inject queue vào controller và provider), vừa là tham số cho các decorator gắn class consumer và listener với queue.

Bạn cũng có thể ghi đè một số tùy chọn đã cấu hình sẵn cho một queue cụ thể, như sau:

[[CODE:36]]

Vì job được lưu trong Redis, mỗi lần một queue có tên được khởi tạo (ví dụ khi app khởi động hoặc khởi động lại), nó sẽ cố xử lý mọi job cũ còn sót lại từ một phiên chưa hoàn tất trước đó.

Mỗi queue có thể có một hoặc nhiều producer, consumer và listener. Consumer lấy job từ queue theo một thứ tự cụ thể: FIFO (mặc định), LIFO, hoặc theo độ ưu tiên. Phần <a href="application/queues#job-options">tùy chọn job</a> giải thích cách điều khiển thứ tự xử lý.

<app-banner-enterprise></app-banner-enterprise>

#### Cấu hình có tên

Nếu các queue của bạn kết nối tới nhiều instance Redis, bạn có thể dùng một kỹ thuật gọi là **cấu hình có tên** (named configuration). Tính năng này cho phép bạn đăng ký nhiều cấu hình dưới các key chỉ định, rồi tham chiếu tới chúng trong tùy chọn của queue.

Ví dụ, giả sử bạn có thêm một instance Redis (ngoài instance mặc định) được vài queue trong ứng dụng sử dụng, bạn có thể đăng ký cấu hình của nó như sau:

[[CODE:37]]

Trong ví dụ trên, `'alternative-config'` là một key cấu hình (có thể là chuỗi bất kỳ).

Giờ bạn có thể trỏ tới cấu hình này trong options object của `registerQueue()`:

[[CODE:38]]

#### Producer

Job producer thêm job vào queue. Producer thường là các service của ứng dụng ([provider](/providers) của Nest). Để thêm job vào queue, trước tiên hãy inject queue vào service:

[[CODE:39]]

> info **Hint** Decorator `@InjectQueue()` xác định queue theo tên của nó, đúng như tên truyền vào lời gọi method `registerQueue()` (ví dụ `'audio'`).

Giờ hãy thêm một job bằng cách gọi method `add()` của queue, truyền vào một data object do người dùng định nghĩa. Dữ liệu job phải serialize được, vì job được lưu trong Redis. Cấu trúc dữ liệu là tùy ý; hãy dùng nó để biểu diễn ý nghĩa của job.

[[CODE:40]]

#### Job có tên

Job có thể có tên. Điều này cho phép bạn tạo các <a href="application/queues#consumers">consumer</a> chuyên biệt chỉ xử lý job có tên nhất định.

[[CODE:41]]

> warning **Warning** Khi dùng job có tên, bạn phải tạo một processor cho mỗi tên khác nhau được thêm vào queue, nếu không queue sẽ báo thiếu processor cho job đó. Xem <a href="application/queues#consumers">consumer</a> để biết thêm về cách xử lý job có tên.

#### Tùy chọn job

Job có thể có thêm các tùy chọn đi kèm. Truyền một options object sau dữ liệu job trong method `Queue.add()`. Các tùy chọn job gồm:

- `priority`: `number` - Giá trị độ ưu tiên (tùy chọn). Nằm trong khoảng từ 1 (ưu tiên cao nhất) tới MAX_INT (ưu tiên thấp nhất). Dùng độ ưu tiên có ảnh hưởng nhẹ tới hiệu năng, nên hãy dùng một cách thận trọng.
- `delay`: `number` - Thời gian (tính bằng mili giây) phải chờ trước khi job này có thể được xử lý. Để độ trễ chính xác, cả server lẫn client nên đồng bộ đồng hồ với nhau.
- `attempts`: `number` - Tổng số lần thử chạy job cho đến khi nó hoàn tất.
- `repeat`: `RepeatOpts` - Lặp lại job theo một đặc tả cron. Xem [RepeatOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queueadd).
- `backoff`: `number | BackoffOpts` - Thiết lập backoff cho việc tự động retry khi job thất bại. Xem [BackoffOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queueadd).
- `lifo`: `boolean` - Nếu là `true`, thêm job vào đầu bên phải của queue thay vì bên trái (mặc định `false`).
- `timeout`: `number` - Số mili giây mà sau đó job sẽ thất bại với lỗi timeout.
- `jobId`: `number | string` - Ghi đè ID của job. Mặc định, ID của job là một số nguyên duy nhất. Nếu dùng tùy chọn này, bạn phải tự đảm bảo ID là duy nhất. Một job có ID đã tồn tại sẽ không được thêm vào.
- `removeOnComplete`: `boolean | number` - Nếu là `true`, xóa job khi nó hoàn tất thành công. Một số sẽ chỉ định số lượng job cần giữ lại. Mặc định, job được giữ trong tập completed.
- `removeOnFail`: `boolean | number` - Nếu là `true`, xóa job khi nó thất bại sau mọi lần thử. Một số sẽ chỉ định số lượng job cần giữ lại. Mặc định, job được giữ trong tập failed.
- `stackTraceLimit`: `number` - Giới hạn số dòng stack trace được ghi lại cho một job thất bại.

Đây là vài ví dụ tùy biến job bằng tùy chọn job.

Để trì hoãn việc bắt đầu một job, dùng thuộc tính `delay`.

[[CODE:42]]

Để thêm job vào đầu bên phải của queue (tức là xử lý theo kiểu **LIFO**, Last In First Out), đặt thuộc tính `lifo` thành `true`.

[[CODE:43]]

Để đặt độ ưu tiên cho một job, dùng thuộc tính `priority`.

[[CODE:44]]

#### Consumer

Consumer là một **class** định nghĩa các method xử lý job được thêm vào queue, lắng nghe event trên queue, hoặc cả hai. Khai báo class consumer bằng decorator `@Processor()` như sau:

[[CODE:45]]

> info **Hint** Consumer phải được đăng ký làm `providers` để package `@nestjs/bull` có thể nhận diện chúng.

Tham số chuỗi của decorator (ví dụ `'audio'`) là tên của queue cần gắn với các method của class.

Bên trong class consumer, khai báo job handler bằng cách decorate các method handler với decorator `@Process()`.

[[CODE:46]]

Method được decorate (ví dụ `transcode()`) được gọi mỗi khi worker rảnh và có job cần xử lý trong queue. Nó nhận object `job` làm tham số duy nhất. Giá trị nó trả về được lưu trong object job và có thể truy cập sau đó, ví dụ trong listener của event `completed`.

Object `Job` có nhiều method cho phép bạn tương tác với trạng thái của nó. Ví dụ, đoạn code trên dùng method `progress()` để cập nhật tiến độ của job. Xem [phần Job trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#job) để có API `Job` đầy đủ.

Bạn có thể chỉ định một method handler job **chỉ** xử lý job thuộc một loại nhất định (job có `name` cụ thể) bằng cách truyền `name` đó vào decorator `@Process()`, như bên dưới. Một class consumer có thể có nhiều handler `@Process()`, mỗi handler cho một loại job (`name`). Khi dùng job có tên, hãy đảm bảo có handler cho mỗi tên.

[[CODE:47]]

> warning **Warning** Khi bạn định nghĩa nhiều consumer cho cùng một queue, tùy chọn `concurrency` trong `@Process({{ '{' }} concurrency: 1 {{ '}' }})` không có hiệu lực. `concurrency` tối thiểu sẽ bằng số consumer được định nghĩa. Điều này vẫn đúng kể cả khi các handler `@Process()` dùng tên khác nhau để xử lý job có tên.

#### Consumer request-scoped

Khi một consumer được đánh dấu là request-scoped (xem [injection scope](/fundamentals/injection-scopes#provider-scope)), một instance mới của class sẽ được tạo riêng cho mỗi job. Instance này bị garbage collect sau khi job hoàn tất.

[[CODE:48]]

Vì các class consumer request-scoped được khởi tạo động và có scope gắn với một job duy nhất, bạn có thể inject job hiện tại qua constructor bằng token `JOB_REF`.

[[CODE:49]]

> info **Hint** Token `JOB_REF` được import từ package `@nestjs/bull`.

#### Event listener

Bull phát ra một loạt event khi có thay đổi trạng thái của queue và/hoặc job. Package `@nestjs/bull` export một bộ decorator cho phép bạn subscribe một nhóm event chuẩn cốt lõi.

Event listener phải được khai báo bên trong một class <a href="application/queues#consumers">consumer</a> (tức là bên trong class được decorate bằng `@Processor()`). Để lắng nghe một event, dùng một trong các decorator trong bảng dưới đây để khai báo handler cho event đó. Ví dụ, để lắng nghe event phát ra khi một job chuyển sang trạng thái active trong queue `audio`, dùng cách khai báo sau:

[[CODE:50]]

Vì Bull hoạt động trong môi trường phân tán (nhiều node), nó định nghĩa khái niệm phạm vi của event. Event có thể được kích hoạt hoàn toàn bên trong một process duy nhất, hoặc trên các queue dùng chung từ nhiều process khác nhau. Event **local** được tạo ra khi một hành động hoặc thay đổi trạng thái được kích hoạt trên một queue trong process cục bộ. Nói cách khác, khi producer và consumer event của bạn đều nằm trong một process duy nhất, mọi event xảy ra trên queue đều là local.

Khi một queue được chia sẻ giữa nhiều process, event **global** bắt đầu có vai trò. Để một listener trong một process nhận được thông báo về event do process khác kích hoạt, nó phải đăng ký event global.

Event handler được gọi mỗi khi event tương ứng được phát ra. Mỗi handler được gọi với signature như trong bảng dưới đây, cho phép truy cập thông tin liên quan tới event. Một khác biệt quan trọng giữa signature của handler event local và global được trình bày ngay dưới bảng.

<table>
  <tr>
    <th>Listener event local</th>
    <th>Listener event global</th>
    <th>Signature của method handler / Khi nào được kích hoạt</th>
  </tr>
  <tr>
    <td><code>@OnQueueError()</code></td><td><code>@OnGlobalQueueError()</code></td><td><code>handler(error: Error)</code> - Có lỗi xảy ra. <code>error</code> chứa lỗi gây ra event.</td>
  </tr>
  <tr>
    <td><code>@OnQueueWaiting()</code></td><td><code>@OnGlobalQueueWaiting()</code></td><td><code>handler(jobId: number | string)</code> - Một job đang chờ được xử lý ngay khi có worker rảnh. <code>jobId</code> chứa ID của job vừa chuyển sang trạng thái này.</td>
  </tr>
  <tr>
    <td><code>@OnQueueActive()</code></td><td><code>@OnGlobalQueueActive()</code></td><td><code>handler(job: Job)</code> - Job <code>job</code> đã bắt đầu.</td>
  </tr>
  <tr>
    <td><code>@OnQueueStalled()</code></td><td><code>@OnGlobalQueueStalled()</code></td><td><code>handler(job: Job)</code> - Job <code>job</code> đã bị đánh dấu là stalled. Hữu ích để debug các job worker bị crash hoặc làm treo event loop.</td>
  </tr>
  <tr>
    <td><code>@OnQueueProgress()</code></td><td><code>@OnGlobalQueueProgress()</code></td><td><code>handler(job: Job, progress: number)</code> - Tiến độ của job <code>job</code> đã được cập nhật thành giá trị <code>progress</code>.</td>
  </tr>
  <tr>
    <td><code>@OnQueueCompleted()</code></td><td><code>@OnGlobalQueueCompleted()</code></td><td><code>handler(job: Job, result: any)</code> - Job <code>job</code> đã hoàn tất thành công với kết quả <code>result</code>.</td>
  </tr>
  <tr>
    <td><code>@OnQueueFailed()</code></td><td><code>@OnGlobalQueueFailed()</code></td><td><code>handler(job: Job, err: Error)</code> - Job <code>job</code> thất bại với lý do <code>err</code>.</td>
  </tr>
  <tr>
    <td><code>@OnQueuePaused()</code></td><td><code>@OnGlobalQueuePaused()</code></td><td><code>handler()</code> - Queue đã bị tạm dừng.</td>
  </tr>
  <tr>
    <td><code>@OnQueueResumed()</code></td><td><code>@OnGlobalQueueResumed()</code></td><td><code>handler()</code> - Queue đã được tiếp tục.</td>
  </tr>
  <tr>
    <td><code>@OnQueueCleaned()</code></td><td><code>@OnGlobalQueueCleaned()</code></td><td><code>handler(jobs: Job[], type: string)</code> - Các job cũ đã được dọn khỏi queue. <code>jobs</code> là mảng các job đã được dọn, và <code>type</code> là loại job đã được dọn.</td>
  </tr>
  <tr>
    <td><code>@OnQueueDrained()</code></td><td><code>@OnGlobalQueueDrained()</code></td><td><code>handler()</code> - Phát ra mỗi khi queue đã xử lý hết các job đang chờ (kể cả khi vẫn còn một số job bị trì hoãn chưa được xử lý).</td>
  </tr>
  <tr>
    <td><code>@OnQueueRemoved()</code></td><td><code>@OnGlobalQueueRemoved()</code></td><td><code>handler(job: Job)</code> - Job <code>job</code> đã được xóa thành công.</td>
  </tr>
</table>

Khi lắng nghe event global, signature của method có thể hơi khác so với phiên bản local tương ứng. Cụ thể, handler nào nhận object `job` ở phiên bản local thì sẽ nhận `jobId` (`number | string`) ở phiên bản global. Để lấy tham chiếu tới object `job` thực sự trong trường hợp đó, dùng method `Queue#getJob()`. Lời gọi này trả về một promise, nên hãy khai báo handler là `async` và await nó. Ví dụ:

[[CODE:51]]

> info **Hint** Để truy cập object `Queue` (để gọi `getJob()`), bạn phải inject nó. Queue cũng phải được đăng ký trong module nơi bạn inject nó.

Ngoài các decorator event listener cụ thể, bạn có thể dùng decorator generic `@OnQueueEvent()` kết hợp với enum `BullQueueEvents` hoặc `BullQueueGlobalEvents`. Xem [phần Events trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#events) để tìm hiểu thêm về event.

#### Quản lý queue

Queue có một API cho các chức năng quản lý như tạm dừng và tiếp tục, hay lấy số lượng job ở các trạng thái khác nhau. Xem [phần Queue trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để có API đầy đủ. Gọi các method này trực tiếp trên object `Queue`, như trong ví dụ tạm dừng và tiếp tục bên dưới.

Tạm dừng một queue bằng method `pause()`. Queue bị tạm dừng sẽ không xử lý job mới cho đến khi được tiếp tục, nhưng các job đang được xử lý vẫn tiếp tục cho đến khi xong.

[[CODE:52]]

Để tiếp tục một queue đã tạm dừng, dùng method `resume()`, như sau:

[[CODE:53]]

#### Process riêng

Job handler cũng có thể chạy trong một process riêng (fork) (xem [Separate processes](https://github.com/OptimalBits/bull#separate-processes) trong tài liệu Bull). Cách này có vài ưu điểm:

- Process được cô lập (sandbox), nên nếu nó crash, worker không bị ảnh hưởng.
- Bạn có thể chạy code blocking mà không ảnh hưởng tới queue (job không bị treo).
- Tận dụng CPU đa nhân tốt hơn.
- Ít kết nối tới Redis hơn.

[[CODE:54]]

Vì hàm của bạn chạy trong một process được fork, dependency injection (và IoC container) không có sẵn. Hàm processor phải tự chứa (hoặc tự tạo) mọi instance của các dependency bên ngoài mà nó cần.

[[CODE:55]]

#### Cấu hình bất đồng bộ

Có thể bạn muốn truyền tùy chọn `bull` theo kiểu bất đồng bộ thay vì tĩnh. Khi đó, hãy dùng method `forRootAsync()`, method này cung cấp vài cách để xử lý cấu hình bất đồng bộ.

Một cách là dùng hàm factory:

[[CODE:56]]

Factory này hoạt động như mọi [provider bất đồng bộ](/fundamentals/async-providers) khác (ví dụ nó có thể là `async` và có thể inject dependency qua `inject`).

[[CODE:57]]

Cách khác là dùng cú pháp `useClass`:

[[CODE:58]]

Cách khai báo trên khởi tạo `BullConfigService` bên trong `BullModule` và dùng nó để cung cấp options object bằng cách gọi `createSharedConfiguration()`. Điều này có nghĩa là `BullConfigService` phải implement interface `SharedBullConfigurationFactory`, như bên dưới:

[[CODE:59]]

Để dùng lại một provider được import từ module khác thay vì tạo `BullConfigService` bên trong `BullModule`, hãy dùng cú pháp `useExisting`.

[[CODE:60]]

Cách khai báo này hoạt động giống `useClass`, với một khác biệt quan trọng: `BullModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã có thay vì khởi tạo cái mới.

Tương tự, để truyền tùy chọn queue theo kiểu bất đồng bộ, dùng method `registerQueueAsync()`. Hãy chỉ định thuộc tính `name` bên ngoài hàm factory.

[[CODE:61]]

#### Ví dụ

Một ví dụ chạy được có sẵn trong [sample 26-queues](https://github.com/nestjs/nest/tree/master/sample/26-queues).
