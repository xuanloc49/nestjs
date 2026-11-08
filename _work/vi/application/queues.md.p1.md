### Queue

Queue là một design pattern giúp bạn giải quyết các bài toán phổ biến về mở rộng quy mô và hiệu năng của ứng dụng. Một vài ví dụ về vấn đề mà queue có thể giúp giải quyết:

- San phẳng các đỉnh tải xử lý. Ví dụ, nếu người dùng có thể khởi tạo các tác vụ tốn tài nguyên vào bất kỳ lúc nào, bạn có thể đưa các tác vụ này vào queue thay vì xử lý chúng một cách đồng bộ. Các worker process sau đó sẽ lấy tác vụ từ queue một cách có kiểm soát. Khi ứng dụng lớn dần, bạn có thể thêm queue consumer để mở rộng khả năng xử lý tác vụ ở back-end.
- Chia nhỏ các tác vụ nguyên khối có thể làm nghẽn event loop của Node.js. Ví dụ, nếu một request của người dùng cần xử lý nặng về CPU như chuyển mã âm thanh, bạn có thể giao tác vụ này cho các process khác, để các process phục vụ người dùng vẫn phản hồi nhanh.
- Cung cấp một kênh giao tiếp tin cậy giữa các service. Ví dụ, bạn có thể đưa tác vụ (job) vào queue ở một process hoặc service và xử lý chúng ở một nơi khác. Bằng cách lắng nghe các status event, bất kỳ process hay service nào cũng có thể được thông báo khi job hoàn tất, gặp lỗi, hoặc có thay đổi trạng thái khác trong vòng đời job. Khi producer hoặc consumer của queue gặp sự cố, trạng thái của chúng vẫn được lưu lại, và việc xử lý tác vụ có thể tự động tiếp tục khi các node khởi động lại.

Nest cung cấp package `@nestjs/bullmq` để tích hợp BullMQ và package `@nestjs/bull` để tích hợp Bull. Cả hai package đều bọc library tương ứng, vốn do cùng một team phát triển. Bull đang ở chế độ bảo trì (team chỉ sửa bug), trong khi BullMQ vẫn được phát triển tích cực và mang đến một bản implement TypeScript hiện đại với bộ tính năng khác. Nếu Bull đáp ứng được yêu cầu của bạn, nó vẫn là một lựa chọn đáng tin cậy, đã được kiểm chứng qua thực chiến.

Cả BullMQ và Bull đều dùng [Redis](https://redis.io/) để lưu dữ liệu job, nên bạn cần một instance Redis đang chạy. Vì dựa trên Redis, kiến trúc queue của bạn có thể hoàn toàn phân tán và không phụ thuộc nền tảng. Ví dụ, bạn có thể chạy một số <a href="application/queues#producers">producer</a>, <a href="application/queues#consumers">consumer</a> và <a href="application/queues#event-listeners">listener</a> của queue trong Nest trên một hoặc nhiều node, và các producer, consumer, listener khác trên các nền tảng Node.js khác ở các node mạng khác.

Chương này trình bày về các package `@nestjs/bullmq` và `@nestjs/bull`. Để có thêm kiến thức nền và chi tiết implement, xem [tài liệu BullMQ](https://docs.bullmq.io/) và [tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md).

#### Cài đặt BullMQ

Để bắt đầu dùng BullMQ, hãy cài các dependency cần thiết.

[[CODE:1]]

Sau khi cài xong, import `BullModule` vào root module `AppModule`.

[[CODE:2]]

Method `forRoot()` đăng ký một configuration object `bullmq` mà mọi queue đăng ký trong ứng dụng đều dùng (trừ khi có chỉ định khác). Dưới đây là vài thuộc tính cấu hình:

- `connection: ConnectionOptions` - Tùy chọn cấu hình kết nối Redis. Xem [Connections](https://docs.bullmq.io/guide/connections) để biết thêm thông tin.
- `backendFactory: BullMQBackendFactory` - Hàm factory cho các backend có thể thay thế (ví dụ PostgreSQL). Xem [Backend có thể thay thế](/application/queues#pluggable-backends) để biết thêm thông tin.
- `prefix: string` - Prefix cho mọi key của queue (mặc định là `bull`).
- `defaultJobOptions: DefaultJobOptions` - Thiết lập mặc định cho job mới. Xem [DefaultJobOptions](https://docs.bullmq.io/api/interfaces/v6.DefaultJobOptions.html) để biết thêm thông tin. Các thiết lập này không có hiệu lực với job được thêm qua `FlowProducer`; xem [bullmq#1034](https://github.com/taskforcesh/bullmq/issues/1034) để hiểu lý do.
- `settings: AdvancedRepeatOptions` - Thiết lập nâng cao cho job lặp lại. Thường không nên thay đổi. Xem [AdvancedRepeatOptions](https://docs.bullmq.io/api/interfaces/v6.AdvancedRepeatOptions.html) để biết thêm thông tin.
- `extraOptions` - Tùy chọn bổ sung cho việc khởi tạo module. Xem [Đăng ký thủ công](/application/queues#manual-registration).

Mọi tùy chọn đều là tùy chọn. Ngoài `extraOptions`, chúng được truyền thẳng vào constructor `Queue` của BullMQ. Xem [tài liệu API QueueOptions](https://docs.bullmq.io/api/interfaces/v6.QueueOptions.html) để có danh sách đầy đủ.

Để đăng ký một queue, import dynamic module `BullModule.registerQueue()`, như sau:

[[CODE:3]]

> info **Hint** Tạo nhiều queue bằng cách truyền nhiều configuration object (dưới dạng các tham số riêng) vào method `registerQueue()`.

Method `registerQueue()` khởi tạo và/hoặc đăng ký queue. Queue được chia sẻ giữa các module và process kết nối tới cùng một database Redis bên dưới với cùng thông tin đăng nhập. Mỗi queue được xác định bằng thuộc tính `name`. Tên queue vừa đóng vai trò injection token (để inject queue vào controller và provider), vừa là tham số cho các decorator gắn class consumer và listener với queue.

Bạn cũng có thể ghi đè một số tùy chọn đã cấu hình sẵn cho một queue cụ thể, như sau:

[[CODE:4]]

BullMQ cũng hỗ trợ quan hệ cha-con giữa các job. Điều này cho phép tạo ra các flow, trong đó job là các node của những cây có độ sâu tùy ý. Xem [Flows](https://docs.bullmq.io/guide/flows) trong tài liệu BullMQ để tìm hiểu thêm.

Để đăng ký một flow producer, dùng method `registerFlowProducer()`:

[[CODE:5]]

Vì job được lưu trong Redis, mỗi lần một queue có tên được khởi tạo (ví dụ khi app khởi động hoặc khởi động lại), nó sẽ cố xử lý mọi job cũ còn sót lại từ một phiên chưa hoàn tất trước đó.

Mỗi queue có thể có một hoặc nhiều producer, consumer và listener. Consumer lấy job từ queue theo một thứ tự cụ thể: FIFO (mặc định), LIFO, hoặc theo độ ưu tiên. Phần <a href="application/queues#job-options">tùy chọn job</a> giải thích cách điều khiển thứ tự xử lý.

<app-banner-enterprise></app-banner-enterprise>

#### Cấu hình có tên

Nếu các queue của bạn kết nối tới nhiều instance Redis, bạn có thể dùng một kỹ thuật gọi là **cấu hình có tên** (named configuration). Tính năng này cho phép bạn đăng ký nhiều cấu hình dưới các key chỉ định, rồi tham chiếu tới chúng trong tùy chọn của queue.

Ví dụ, giả sử bạn có thêm một instance Redis (ngoài instance mặc định) được vài queue trong ứng dụng sử dụng, bạn có thể đăng ký cấu hình của nó như sau:

[[CODE:6]]

Trong ví dụ trên, `'alternative-config'` là một key cấu hình (có thể là chuỗi bất kỳ).

Giờ bạn có thể trỏ tới cấu hình này trong options object của `registerQueue()`:

[[CODE:7]]

#### Backend có thể thay thế (PostgreSQL)

BullMQ hỗ trợ các backend lưu trữ có thể thay thế (như PostgreSQL) thông qua các backend factory tùy chỉnh. Bạn có thể cấu hình `backendFactory` ở cấp global trong `BullModule.forRoot()` hoặc cho từng queue trong `BullModule.registerQueue()`.

[[CODE:8]]

`migrate: true` tạo các bảng của BullMQ lúc khởi động, trong một schema `bullmq` riêng. Không có tùy chọn này, ứng dụng sẽ lỗi trên một database chưa có các bảng đó.

`backendFactory` đã cấu hình được tự động lan truyền tới mọi thành phần BullMQ bên dưới (`Queue`, `Worker`, `QueueEvents` và `FlowProducer`), bao gồm cả các worker host `@Processor()` và `@QueueEventsListener()`.

#### Producer

Job producer thêm job vào queue. Producer thường là các service của ứng dụng ([provider](/providers) của Nest). Để thêm job vào queue, trước tiên hãy inject queue vào service:

[[CODE:9]]

> info **Hint** Decorator `@InjectQueue()` xác định queue theo tên của nó, đúng như tên truyền vào lời gọi method `registerQueue()` (ví dụ `'audio'`).

Giờ hãy thêm một job bằng cách gọi method `add()` của queue, truyền vào tên job và một data object do người dùng định nghĩa. Dữ liệu job phải serialize được, vì job được lưu trong Redis. Cấu trúc dữ liệu là tùy ý; hãy dùng nó để biểu diễn ý nghĩa của job. Tên job giúp <a href="application/queues#consumers">consumer</a> phân biệt các loại job khác nhau.

[[CODE:10]]

#### Tùy chọn job

Job có thể có thêm các tùy chọn đi kèm. Truyền một options object làm tham số thứ ba của method `Queue.add()`, sau dữ liệu job. Một số tùy chọn job:

- `priority`: `number` - Giá trị độ ưu tiên, từ 0 đến 2.097.151. `0` (mặc định) nghĩa là không có độ ưu tiên tường minh; job không có độ ưu tiên được xử lý trước các job có độ ưu tiên, và trong số các job có độ ưu tiên, số nhỏ hơn được xử lý trước. Dùng độ ưu tiên có ảnh hưởng nhẹ tới hiệu năng, nên chỉ dùng khi cần.
- `delay`: `number` - Thời gian (tính bằng mili giây) phải chờ trước khi job này có thể được xử lý. Để độ trễ chính xác, worker và producer nên đồng bộ đồng hồ với nhau.
- `attempts`: `number` - Tổng số lần thử chạy job cho đến khi nó hoàn tất (mặc định là 1).
- `backoff`: `number | BackoffOptions` - Thiết lập backoff cho việc tự động retry khi job thất bại. Xem [BackoffOptions](https://docs.bullmq.io/api/interfaces/v6.BackoffOptions.html).
- `lifo`: `boolean` - Nếu là `true`, thêm job vào đầu bên phải của queue thay vì bên trái (mặc định `false`).
- `jobId`: `string` - Ghi đè ID của job. Mặc định, ID của job là một số nguyên duy nhất. Nếu dùng tùy chọn này, bạn phải tự đảm bảo ID là duy nhất. Một job có ID đã tồn tại sẽ không được thêm vào.
- `removeOnComplete`: `boolean | number | KeepJobs` - Nếu là `true`, xóa job khi nó hoàn tất thành công. Một số sẽ chỉ định số lượng job cần giữ lại, còn một object `KeepJobs` chỉ định tuổi tối đa và/hoặc số lượng. Mặc định, job được giữ trong tập completed.
- `removeOnFail`: `boolean | number | KeepJobs` - Nếu là `true`, xóa job khi nó thất bại sau mọi lần thử. Số hoặc object `KeepJobs` hoạt động giống như với `removeOnComplete`. Mặc định, job được giữ trong tập failed.
- `stackTraceLimit`: `number` - Giới hạn số dòng stack trace được ghi lại cho một job thất bại.

> info **Hint** BullMQ không còn nhận tùy chọn `repeat` trong `Queue.add()`. Để chạy một job lặp lại (ví dụ theo cron pattern), hãy tạo một job scheduler bằng method `Queue#upsertJobScheduler()`. Xem [Job Schedulers](https://docs.bullmq.io/guide/job-schedulers) trong tài liệu BullMQ.

Đây là vài ví dụ tùy biến job bằng tùy chọn job.

Để trì hoãn việc bắt đầu một job, dùng thuộc tính `delay`.

[[CODE:11]]

Để thêm job vào đầu bên phải của queue (tức là xử lý theo kiểu **LIFO**, Last In First Out), đặt thuộc tính `lifo` thành `true`.

[[CODE:12]]

Để đặt độ ưu tiên cho một job, dùng thuộc tính `priority`.

[[CODE:13]]

Để có danh sách tùy chọn đầy đủ, xem tài liệu API [JobsOptions](https://docs.bullmq.io/api/types/v6.JobsOptions.html) và [BaseJobOptions](https://docs.bullmq.io/api/interfaces/v6.BaseJobOptions.html).

#### Consumer

Consumer là một **class** định nghĩa các method xử lý job được thêm vào queue, lắng nghe event trên queue, hoặc cả hai. Khai báo class consumer bằng decorator `@Processor()` như sau:

[[CODE:14]]

> info **Hint** Consumer phải được đăng ký làm `providers` để package `@nestjs/bullmq` có thể nhận diện chúng.

Tham số chuỗi của decorator (ví dụ `'audio'`) là tên của queue cần gắn với class. Class consumer phải kế thừa `WorkerHost` và implement method `process()` của nó:

[[CODE:15]]

Method `process()` được gọi mỗi khi worker rảnh và có job cần xử lý trong queue. Nó nhận object `job` làm tham số duy nhất. Giá trị nó trả về được lưu trong object job và có thể truy cập sau đó, ví dụ trong listener của event `completed`.

Object `Job` có nhiều method cho phép bạn tương tác với trạng thái của nó. Ví dụ, đoạn code trên dùng method `updateProgress()` để cập nhật tiến độ của job. Xem [tài liệu API Job](https://docs.bullmq.io/api/classes/v6.Job.html) để có danh sách đầy đủ.

Trong Bull, bạn có thể chỉ định một method handler job **chỉ** xử lý job thuộc một loại nhất định (job có `name` cụ thể) bằng cách truyền `name` đó vào decorator `@Process()`, như bên dưới.

> warning **Warning** Cách này không hoạt động với BullMQ. Hãy đọc tiếp để biết cách làm với BullMQ.

[[CODE:16]]

BullMQ không hỗ trợ hành vi này, vì nó gây nhầm lẫn. Thay vào đó, hãy dùng câu lệnh `switch` trên tên job để gọi service hoặc logic khác nhau cho từng loại job:

[[CODE:17]]

Điều này được trình bày trong phần [named processor](https://docs.bullmq.io/patterns/named-processor) của tài liệu BullMQ.

#### Consumer request-scoped

Khi một consumer được đánh dấu là request-scoped (xem [injection scope](/fundamentals/injection-scopes#provider-scope)), một instance mới của class sẽ được tạo riêng cho mỗi job. Instance này bị garbage collect sau khi job hoàn tất.

[[CODE:18]]

Vì các class consumer request-scoped được khởi tạo động và có scope gắn với một job duy nhất, bạn có thể inject job hiện tại qua constructor bằng token `JOB_REF`.

[[CODE:19]]

> info **Hint** Token `JOB_REF` được import từ package `@nestjs/bullmq`.

#### Event listener

BullMQ phát ra một loạt event khi có thay đổi trạng thái của queue và/hoặc job. Bạn có thể subscribe các event này ở cấp worker bằng decorator `@OnWorkerEvent(event)`, hoặc ở cấp queue bằng một class listener chuyên dụng và decorator `@OnQueueEvent(event)`.

Worker event phải được khai báo bên trong một class <a href="application/queues#consumers">consumer</a> (tức là bên trong class được decorate bằng `@Processor()`). Để lắng nghe một event, dùng decorator `@OnWorkerEvent(event)` với event bạn muốn xử lý. Ví dụ, để lắng nghe event phát ra khi một job chuyển sang trạng thái active trong queue `audio`, dùng cách khai báo sau:

[[CODE:20]]

Danh sách đầy đủ các worker event và tham số của chúng có sẵn dưới dạng các thuộc tính của interface [WorkerListener](https://docs.bullmq.io/api/interfaces/v6.WorkerListener.html).

Listener của queue event phải dùng decorator `@QueueEventsListener(queue)` và kế thừa class `QueueEventsHost` do `@nestjs/bullmq` cung cấp. Để lắng nghe một event, dùng decorator `@OnQueueEvent(event)` với event bạn muốn xử lý. Ví dụ, để lắng nghe event phát ra khi một job chuyển sang trạng thái active trong queue `audio`, dùng cách khai báo sau:

[[CODE:21]]

> info **Hint** Listener của queue event phải được đăng ký làm `providers` để package `@nestjs/bullmq` có thể nhận diện chúng.

Danh sách đầy đủ các queue event và tham số của chúng có sẵn dưới dạng các thuộc tính của interface [QueueEventsListener](https://docs.bullmq.io/api/interfaces/v6.QueueEventsListener.html).

#### Quản lý queue

Queue có một API cho các chức năng quản lý như tạm dừng và tiếp tục, hay lấy số lượng job ở các trạng thái khác nhau. Xem [tài liệu API Queue](https://docs.bullmq.io/api/classes/v6.Queue.html) để có API đầy đủ. Gọi các method này trực tiếp trên object `Queue`, như trong ví dụ tạm dừng và tiếp tục bên dưới.

Tạm dừng một queue bằng method `pause()`. Queue bị tạm dừng sẽ không xử lý job mới cho đến khi được tiếp tục, nhưng các job đang được xử lý vẫn tiếp tục cho đến khi xong.

[[CODE:22]]

Để tiếp tục một queue đã tạm dừng, dùng method `resume()`, như sau:

[[CODE:23]]

#### Theo dõi queue trên production

Queue gặp sự cố theo những cách mà HTTP endpoint không gặp. Một job không trả status code cho một người dùng đang sốt ruột. Nó lặng lẽ retry ba lần, có backoff, và triệu chứng duy nhất là một việc gì đó phía sau không bao giờ xảy ra. Vì vậy hai câu hỏi quan trọng là *"queue này có theo kịp không?"* và *"job đó có chạy hay không?"*, và log của chính consumer không trả lời được câu nào cả.

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') tự động instrument các queue consumer, giống như cách nó instrument controller: các class `@Processor()` và handler của chúng được nhận diện là job, nên không cần tự nối span bằng tay:

- **Thời gian chờ trong queue được đo riêng với thời gian thực thi.** Một job chạy mất 200 ms nhưng nằm trong queue suốt bốn phút là vấn đề về năng lực xử lý, không phải handler chậm. Hai con số được báo cáo cạnh nhau, nên bạn biết mình đang gặp vấn đề nào.
- **Số lần thử và lý do thất bại được ghi lại cho từng lần chạy.** Bạn thấy một job thành công ở lần thử thứ 3 thay vì chỉ thấy là nó thành công, và đó thường là khác biệt giữa "ổn" và "đang âm thầm xuống cấp".
- **Sự im lặng cũng đặt cảnh báo được.** Một quy tắc *job silence* kích hoạt khi một job có tên không báo cáo gì lâu hơn khoảng dung sai bạn chọn. Đó là cách bạn biết consumer tính tiền hằng đêm đã ngừng chạy ngay đêm nó ngừng, chứ không phải vào cuối tháng.

Job thất bại mang cùng thẻ lỗi như request thất bại: stack trace đã map kèm các dòng mã nguồn, các log được ghi trong lần chạy, và waterfall những gì job đã làm trước khi throw. Xem chương [Observability](/observability/overview) để thiết lập.

#### Process riêng

Job handler cũng có thể chạy trong một process riêng (fork) (xem [Sandboxed processors](https://docs.bullmq.io/guide/workers/sandboxed-processors) trong tài liệu BullMQ). Cách này có vài ưu điểm:

- Process được cô lập (sandbox), nên nếu nó crash, worker không bị ảnh hưởng.
- Bạn có thể chạy code blocking mà không ảnh hưởng tới queue (job không bị treo).
- Tận dụng CPU đa nhân tốt hơn.
- Ít kết nối tới Redis hơn.

[[CODE:24]]

> warning **Warning** Vì hàm của bạn chạy trong một process được fork, dependency injection (và IoC container) không có sẵn. Hàm processor phải tự chứa (hoặc tự tạo) mọi instance của các dependency bên ngoài mà nó cần.

#### Cấu hình bất đồng bộ

Có thể bạn muốn truyền tùy chọn `bullmq` theo kiểu bất đồng bộ thay vì tĩnh. Khi đó, hãy dùng method `forRootAsync()`, method này cung cấp vài cách để xử lý cấu hình bất đồng bộ. Tương tự, để truyền tùy chọn queue theo kiểu bất đồng bộ, dùng method `registerQueueAsync()`.

Một cách là dùng hàm factory:

[[CODE:25]]

Factory này hoạt động như mọi [provider bất đồng bộ](/fundamentals/async-providers) khác (ví dụ nó có thể là `async` và có thể inject dependency qua `inject`).

[[CODE:26]]

Cách khác là dùng cú pháp `useClass`:

[[CODE:27]]

Cách khai báo trên khởi tạo `BullConfigService` bên trong `BullModule` và dùng nó để cung cấp options object bằng cách gọi `createSharedConfiguration()`. Điều này có nghĩa là `BullConfigService` phải implement interface `SharedBullConfigurationFactory`, như bên dưới:

[[CODE:28]]

Để dùng lại một provider được import từ module khác thay vì tạo `BullConfigService` bên trong `BullModule`, hãy dùng cú pháp `useExisting`.

[[CODE:29]]

Cách khai báo này hoạt động giống `useClass`, với một khác biệt quan trọng: `BullModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã có thay vì khởi tạo cái mới.

Tương tự, để truyền tùy chọn queue theo kiểu bất đồng bộ, dùng method `registerQueueAsync()`. Hãy chỉ định thuộc tính `name` bên ngoài hàm factory.

[[CODE:30]]

#### Đăng ký thủ công

Mặc định, `BullModule` tự động đăng ký các thành phần BullMQ (queue, processor và các service event listener) trong lifecycle hook `onModuleInit`. Trong một số trường hợp, đây không phải hành vi bạn muốn. Để ngăn việc tự động đăng ký, hãy bật `manualRegistration` trong `BullModule`:

[[CODE:31]]

Để tự đăng ký các thành phần này, hãy inject `BullRegistrar` và gọi method `register()` của nó, tốt nhất là trong lifecycle hook `onModuleInit()` hoặc `onApplicationBootstrap()`.

[[CODE:32]]

Cho đến khi bạn gọi `BullRegistrar#register()`, không thành phần BullMQ nào hoạt động, nghĩa là không có job nào được xử lý.
