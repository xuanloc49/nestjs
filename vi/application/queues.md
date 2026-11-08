### Queue

Queue là một design pattern giúp bạn giải quyết các bài toán phổ biến về mở rộng quy mô và hiệu năng của ứng dụng. Một vài ví dụ về vấn đề mà queue có thể giúp giải quyết:

- San phẳng các đỉnh tải xử lý. Ví dụ, nếu người dùng có thể khởi tạo các tác vụ tốn tài nguyên vào bất kỳ lúc nào, bạn có thể đưa các tác vụ này vào queue thay vì xử lý chúng một cách đồng bộ. Các worker process sau đó sẽ lấy tác vụ từ queue một cách có kiểm soát. Khi ứng dụng lớn dần, bạn có thể thêm queue consumer để mở rộng khả năng xử lý tác vụ ở back-end.
- Chia nhỏ các tác vụ nguyên khối có thể làm nghẽn event loop của Node.js. Ví dụ, nếu một request của người dùng cần xử lý nặng về CPU như chuyển mã âm thanh, bạn có thể giao tác vụ này cho các process khác, để các process phục vụ người dùng vẫn phản hồi nhanh.
- Cung cấp một kênh giao tiếp tin cậy giữa các service. Ví dụ, bạn có thể đưa tác vụ (job) vào queue ở một process hoặc service và xử lý chúng ở một nơi khác. Bằng cách lắng nghe các status event, bất kỳ process hay service nào cũng có thể được thông báo khi job hoàn tất, gặp lỗi, hoặc có thay đổi trạng thái khác trong vòng đời job. Khi producer hoặc consumer của queue gặp sự cố, trạng thái của chúng vẫn được lưu lại, và việc xử lý tác vụ có thể tự động tiếp tục khi các node khởi động lại.

Nest cung cấp package `@nestjs/bullmq` để tích hợp BullMQ và package `@nestjs/bull` để tích hợp Bull. Cả hai package đều bọc library tương ứng, vốn do cùng một team phát triển. Bull đang ở chế độ bảo trì (team chỉ sửa bug), trong khi BullMQ vẫn được phát triển tích cực và mang đến một bản implement TypeScript hiện đại với bộ tính năng khác. Nếu Bull đáp ứng được yêu cầu của bạn, nó vẫn là một lựa chọn đáng tin cậy, đã được kiểm chứng qua thực chiến.

Cả BullMQ và Bull đều dùng [Redis](https://redis.io/) để lưu dữ liệu job, nên bạn cần một instance Redis đang chạy. Vì dựa trên Redis, kiến trúc queue của bạn có thể hoàn toàn phân tán và không phụ thuộc nền tảng. Ví dụ, bạn có thể chạy một số <a href="application/queues#producers">producer</a>, <a href="application/queues#consumers">consumer</a> và <a href="application/queues#event-listeners">listener</a> của queue trong Nest trên một hoặc nhiều node, và các producer, consumer, listener khác trên các nền tảng Node.js khác ở các node mạng khác.

Chương này trình bày về các package `@nestjs/bullmq` và `@nestjs/bull`. Để có thêm kiến thức nền và chi tiết implement, xem [tài liệu BullMQ](https://docs.bullmq.io/) và [tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md).

#### Cài đặt BullMQ <a id="bullmq-installation"></a>

Để bắt đầu dùng BullMQ, hãy cài các dependency cần thiết.

```bash
$ npm install --save @nestjs/bullmq bullmq
```

Sau khi cài xong, import `BullModule` vào root module `AppModule`.

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';

@Module({
  imports: [
    BullModule.forRoot({
      connection: {
        host: 'localhost',
        port: 6379,
      },
    }),
  ],
})
export class AppModule {}
```

Method `forRoot()` đăng ký một configuration object `bullmq` mà mọi queue đăng ký trong ứng dụng đều dùng (trừ khi có chỉ định khác). Dưới đây là vài thuộc tính cấu hình:

- `connection: ConnectionOptions` - Tùy chọn cấu hình kết nối Redis. Xem [Connections](https://docs.bullmq.io/guide/connections) để biết thêm thông tin.
- `backendFactory: BullMQBackendFactory` - Hàm factory cho các backend có thể thay thế (ví dụ PostgreSQL). Xem [Backend có thể thay thế](/application/queues#pluggable-backends) để biết thêm thông tin.
- `prefix: string` - Prefix cho mọi key của queue (mặc định là `bull`).
- `defaultJobOptions: DefaultJobOptions` - Thiết lập mặc định cho job mới. Xem [DefaultJobOptions](https://docs.bullmq.io/api/interfaces/v6.DefaultJobOptions.html) để biết thêm thông tin. Các thiết lập này không có hiệu lực với job được thêm qua `FlowProducer`; xem [bullmq#1034](https://github.com/taskforcesh/bullmq/issues/1034) để hiểu lý do.
- `settings: AdvancedRepeatOptions` - Thiết lập nâng cao cho job lặp lại. Thường không nên thay đổi. Xem [AdvancedRepeatOptions](https://docs.bullmq.io/api/interfaces/v6.AdvancedRepeatOptions.html) để biết thêm thông tin.
- `extraOptions` - Tùy chọn bổ sung cho việc khởi tạo module. Xem [Đăng ký thủ công](/application/queues#manual-registration).

Mọi tùy chọn đều là tùy chọn. Ngoài `extraOptions`, chúng được truyền thẳng vào constructor `Queue` của BullMQ. Xem [tài liệu API QueueOptions](https://docs.bullmq.io/api/interfaces/v6.QueueOptions.html) để có danh sách đầy đủ.

Để đăng ký một queue, import dynamic module `BullModule.registerQueue()`, như sau:

```typescript
BullModule.registerQueue({
  name: 'audio',
});
```

> info **Gợi ý** Tạo nhiều queue bằng cách truyền nhiều configuration object (dưới dạng các tham số riêng) vào method `registerQueue()`.

Method `registerQueue()` khởi tạo và/hoặc đăng ký queue. Queue được chia sẻ giữa các module và process kết nối tới cùng một database Redis bên dưới với cùng thông tin đăng nhập. Mỗi queue được xác định bằng thuộc tính `name`. Tên queue vừa đóng vai trò injection token (để inject queue vào controller và provider), vừa là tham số cho các decorator gắn class consumer và listener với queue.

Bạn cũng có thể ghi đè một số tùy chọn đã cấu hình sẵn cho một queue cụ thể, như sau:

```typescript
BullModule.registerQueue({
  name: 'audio',
  connection: {
    port: 6380,
  },
});
```

BullMQ cũng hỗ trợ quan hệ cha-con giữa các job. Điều này cho phép tạo ra các flow, trong đó job là các node của những cây có độ sâu tùy ý. Xem [Flows](https://docs.bullmq.io/guide/flows) trong tài liệu BullMQ để tìm hiểu thêm.

Để đăng ký một flow producer, dùng method `registerFlowProducer()`:

```typescript
BullModule.registerFlowProducer({
  name: 'flowProducerName',
});
```

Vì job được lưu trong Redis, mỗi lần một queue có tên được khởi tạo (ví dụ khi app khởi động hoặc khởi động lại), nó sẽ cố xử lý mọi job cũ còn sót lại từ một phiên chưa hoàn tất trước đó.

Mỗi queue có thể có một hoặc nhiều producer, consumer và listener. Consumer lấy job từ queue theo một thứ tự cụ thể: FIFO (mặc định), LIFO, hoặc theo độ ưu tiên. Phần <a href="application/queues#job-options">tùy chọn job</a> giải thích cách điều khiển thứ tự xử lý.

<app-banner-enterprise></app-banner-enterprise>

#### Cấu hình có tên <a id="named-configurations"></a>

Nếu các queue của bạn kết nối tới nhiều instance Redis, bạn có thể dùng một kỹ thuật gọi là **cấu hình có tên** (named configuration). Tính năng này cho phép bạn đăng ký nhiều cấu hình dưới các key chỉ định, rồi tham chiếu tới chúng trong tùy chọn của queue.

Ví dụ, giả sử bạn có thêm một instance Redis (ngoài instance mặc định) được vài queue trong ứng dụng sử dụng, bạn có thể đăng ký cấu hình của nó như sau:

```typescript
BullModule.forRoot('alternative-config', {
  connection: {
    port: 6381,
  },
});
```

Trong ví dụ trên, `'alternative-config'` là một key cấu hình (có thể là chuỗi bất kỳ).

Giờ bạn có thể trỏ tới cấu hình này trong options object của `registerQueue()`:

```typescript
BullModule.registerQueue({
  configKey: 'alternative-config',
  name: 'video',
});
```

#### Backend có thể thay thế (PostgreSQL) <a id="pluggable-backends-postgresql"></a>

BullMQ hỗ trợ các backend lưu trữ có thể thay thế (như PostgreSQL) thông qua các backend factory tùy chỉnh. Bạn có thể cấu hình `backendFactory` ở cấp global trong `BullModule.forRoot()` hoặc cho từng queue trong `BullModule.registerQueue()`.

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { createPostgresBackend } from 'bullmq';

@Module({
  imports: [
    BullModule.forRoot({
      backendFactory: createPostgresBackend,
      connection: {
        host: 'localhost',
        port: 5432,
        user: 'postgres',
        password: 'password',
        database: 'mydb',
        migrate: true,
      },
    }),
  ],
})
export class AppModule {}
```

`migrate: true` tạo các bảng của BullMQ lúc khởi động, trong một schema `bullmq` riêng. Không có tùy chọn này, ứng dụng sẽ lỗi trên một database chưa có các bảng đó.

`backendFactory` đã cấu hình được tự động lan truyền tới mọi thành phần BullMQ bên dưới (`Queue`, `Worker`, `QueueEvents` và `FlowProducer`), bao gồm cả các worker host `@Processor()` và `@QueueEventsListener()`.

#### Producer <a id="producers"></a>

Job producer thêm job vào queue. Producer thường là các service của ứng dụng ([provider](/providers) của Nest). Để thêm job vào queue, trước tiên hãy inject queue vào service:

```typescript
import { Injectable } from '@nestjs/common';
import { Queue } from 'bullmq';
import { InjectQueue } from '@nestjs/bullmq';

@Injectable()
export class AudioService {
  constructor(@InjectQueue('audio') private audioQueue: Queue) {}
}
```

> info **Gợi ý** Decorator `@InjectQueue()` xác định queue theo tên của nó, đúng như tên truyền vào lời gọi method `registerQueue()` (ví dụ `'audio'`).

Giờ hãy thêm một job bằng cách gọi method `add()` của queue, truyền vào tên job và một data object do người dùng định nghĩa. Dữ liệu job phải serialize được, vì job được lưu trong Redis. Cấu trúc dữ liệu là tùy ý; hãy dùng nó để biểu diễn ý nghĩa của job. Tên job giúp <a href="application/queues#consumers">consumer</a> phân biệt các loại job khác nhau.

```typescript
const job = await this.audioQueue.add('transcode', {
  foo: 'bar',
});
```

#### Tùy chọn job <a id="job-options"></a>

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

> info **Gợi ý** BullMQ không còn nhận tùy chọn `repeat` trong `Queue.add()`. Để chạy một job lặp lại (ví dụ theo cron pattern), hãy tạo một job scheduler bằng method `Queue#upsertJobScheduler()`. Xem [Job Schedulers](https://docs.bullmq.io/guide/job-schedulers) trong tài liệu BullMQ.

Đây là vài ví dụ tùy biến job bằng tùy chọn job.

Để trì hoãn việc bắt đầu một job, dùng thuộc tính `delay`.

```typescript
const job = await this.audioQueue.add(
  'transcode',
  {
    foo: 'bar',
  },
  { delay: 3000 }, // 3 seconds delayed
);
```

Để thêm job vào đầu bên phải của queue (tức là xử lý theo kiểu **LIFO**, Last In First Out), đặt thuộc tính `lifo` thành `true`.

```typescript
const job = await this.audioQueue.add(
  'transcode',
  {
    foo: 'bar',
  },
  { lifo: true },
);
```

Để đặt độ ưu tiên cho một job, dùng thuộc tính `priority`.

```typescript
const job = await this.audioQueue.add(
  'transcode',
  {
    foo: 'bar',
  },
  { priority: 2 },
);
```

Để có danh sách tùy chọn đầy đủ, xem tài liệu API [JobsOptions](https://docs.bullmq.io/api/types/v6.JobsOptions.html) và [BaseJobOptions](https://docs.bullmq.io/api/interfaces/v6.BaseJobOptions.html).

#### Consumer <a id="consumers"></a>

Consumer là một **class** định nghĩa các method xử lý job được thêm vào queue, lắng nghe event trên queue, hoặc cả hai. Khai báo class consumer bằng decorator `@Processor()` như sau:

```typescript
import { Processor } from '@nestjs/bullmq';

@Processor('audio')
export class AudioConsumer {}
```

> info **Gợi ý** Consumer phải được đăng ký làm `providers` để package `@nestjs/bullmq` có thể nhận diện chúng.

Tham số chuỗi của decorator (ví dụ `'audio'`) là tên của queue cần gắn với class. Class consumer phải kế thừa `WorkerHost` và implement method `process()` của nó:

```typescript
import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor('audio')
export class AudioConsumer extends WorkerHost {
  async process(job: Job<any, any, string>): Promise<any> {
    let progress = 0;
    for (let i = 0; i < 100; i++) {
      await doSomething(job.data);
      progress += 1;
      await job.updateProgress(progress);
    }
    return {};
  }
}
```

Method `process()` được gọi mỗi khi worker rảnh và có job cần xử lý trong queue. Nó nhận object `job` làm tham số duy nhất. Giá trị nó trả về được lưu trong object job và có thể truy cập sau đó, ví dụ trong listener của event `completed`.

Object `Job` có nhiều method cho phép bạn tương tác với trạng thái của nó. Ví dụ, đoạn code trên dùng method `updateProgress()` để cập nhật tiến độ của job. Xem [tài liệu API Job](https://docs.bullmq.io/api/classes/v6.Job.html) để có danh sách đầy đủ.

Trong Bull, bạn có thể chỉ định một method handler job **chỉ** xử lý job thuộc một loại nhất định (job có `name` cụ thể) bằng cách truyền `name` đó vào decorator `@Process()`, như bên dưới.

> warning **Cảnh báo** Cách này không hoạt động với BullMQ. Hãy đọc tiếp để biết cách làm với BullMQ.

```typescript
@Process('transcode')
async transcode(job: Job<unknown>) { ... }
```

BullMQ không hỗ trợ hành vi này, vì nó gây nhầm lẫn. Thay vào đó, hãy dùng câu lệnh `switch` trên tên job để gọi service hoặc logic khác nhau cho từng loại job:

```typescript
import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor('audio')
export class AudioConsumer extends WorkerHost {
  async process(job: Job<any, any, string>): Promise<any> {
    switch (job.name) {
      case 'transcode': {
        let progress = 0;
        for (let i = 0; i < 100; i++) {
          await doSomething(job.data);
          progress += 1;
          await job.updateProgress(progress);
        }
        return {};
      }
      case 'concatenate': {
        await doSomeLogic2();
        break;
      }
    }
  }
}
```

Điều này được trình bày trong phần [named processor](https://docs.bullmq.io/patterns/named-processor) của tài liệu BullMQ.

#### Consumer request-scoped <a id="request-scoped-consumers"></a>

Khi một consumer được đánh dấu là request-scoped (xem [injection scope](/fundamentals/injection-scopes#provider-scope)), một instance mới của class sẽ được tạo riêng cho mỗi job. Instance này bị garbage collect sau khi job hoàn tất.

```typescript
@Processor({
  name: 'audio',
  scope: Scope.REQUEST,
})
```

Vì các class consumer request-scoped được khởi tạo động và có scope gắn với một job duy nhất, bạn có thể inject job hiện tại qua constructor bằng token `JOB_REF`.

```typescript
constructor(@Inject(JOB_REF) jobRef: Job) {
  console.log(jobRef);
}
```

> info **Gợi ý** Token `JOB_REF` được import từ package `@nestjs/bullmq`.

#### Event listener <a id="event-listeners"></a>

BullMQ phát ra một loạt event khi có thay đổi trạng thái của queue và/hoặc job. Bạn có thể subscribe các event này ở cấp worker bằng decorator `@OnWorkerEvent(event)`, hoặc ở cấp queue bằng một class listener chuyên dụng và decorator `@OnQueueEvent(event)`.

Worker event phải được khai báo bên trong một class <a href="application/queues#consumers">consumer</a> (tức là bên trong class được decorate bằng `@Processor()`). Để lắng nghe một event, dùng decorator `@OnWorkerEvent(event)` với event bạn muốn xử lý. Ví dụ, để lắng nghe event phát ra khi một job chuyển sang trạng thái active trong queue `audio`, dùng cách khai báo sau:

```typescript
import { Processor, WorkerHost, OnWorkerEvent } from '@nestjs/bullmq';
import { Job } from 'bullmq';

@Processor('audio')
export class AudioConsumer extends WorkerHost {
  @OnWorkerEvent('active')
  onActive(job: Job) {
    console.log(
      `Processing job ${job.id} of type ${job.name} with data ${job.data}...`,
    );
  }

  // ...
}
```

Danh sách đầy đủ các worker event và tham số của chúng có sẵn dưới dạng các thuộc tính của interface [WorkerListener](https://docs.bullmq.io/api/interfaces/v6.WorkerListener.html).

Listener của queue event phải dùng decorator `@QueueEventsListener(queue)` và kế thừa class `QueueEventsHost` do `@nestjs/bullmq` cung cấp. Để lắng nghe một event, dùng decorator `@OnQueueEvent(event)` với event bạn muốn xử lý. Ví dụ, để lắng nghe event phát ra khi một job chuyển sang trạng thái active trong queue `audio`, dùng cách khai báo sau:

```typescript
import {
  QueueEventsHost,
  QueueEventsListener,
  OnQueueEvent,
} from '@nestjs/bullmq';

@QueueEventsListener('audio')
export class AudioEventsListener extends QueueEventsHost {
  @OnQueueEvent('active')
  onActive(job: { jobId: string; prev?: string }) {
    console.log(`Processing job ${job.jobId}...`);
  }

  // ...
}
```

> info **Gợi ý** Listener của queue event phải được đăng ký làm `providers` để package `@nestjs/bullmq` có thể nhận diện chúng.

Danh sách đầy đủ các queue event và tham số của chúng có sẵn dưới dạng các thuộc tính của interface [QueueEventsListener](https://docs.bullmq.io/api/interfaces/v6.QueueEventsListener.html).

#### Quản lý queue <a id="queue-management"></a>

Queue có một API cho các chức năng quản lý như tạm dừng và tiếp tục, hay lấy số lượng job ở các trạng thái khác nhau. Xem [tài liệu API Queue](https://docs.bullmq.io/api/classes/v6.Queue.html) để có API đầy đủ. Gọi các method này trực tiếp trên object `Queue`, như trong ví dụ tạm dừng và tiếp tục bên dưới.

Tạm dừng một queue bằng method `pause()`. Queue bị tạm dừng sẽ không xử lý job mới cho đến khi được tiếp tục, nhưng các job đang được xử lý vẫn tiếp tục cho đến khi xong.

```typescript
await audioQueue.pause();
```

Để tiếp tục một queue đã tạm dừng, dùng method `resume()`, như sau:

```typescript
await audioQueue.resume();
```

#### Theo dõi queue trên production <a id="observing-queues-in-production"></a>

Queue gặp sự cố theo những cách mà HTTP endpoint không gặp. Một job không trả status code cho một người dùng đang sốt ruột. Nó lặng lẽ retry ba lần, có backoff, và triệu chứng duy nhất là một việc gì đó phía sau không bao giờ xảy ra. Vì vậy hai câu hỏi quan trọng là *"queue này có theo kịp không?"* và *"job đó có chạy hay không?"*, và log của chính consumer không trả lời được câu nào cả.

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') tự động instrument các queue consumer, giống như cách nó instrument controller: các class `@Processor()` và handler của chúng được nhận diện là job, nên không cần tự nối span bằng tay:

- **Thời gian chờ trong queue được đo riêng với thời gian thực thi.** Một job chạy mất 200 ms nhưng nằm trong queue suốt bốn phút là vấn đề về năng lực xử lý, không phải handler chậm. Hai con số được báo cáo cạnh nhau, nên bạn biết mình đang gặp vấn đề nào.
- **Số lần thử và lý do thất bại được ghi lại cho từng lần chạy.** Bạn thấy một job thành công ở lần thử thứ 3 thay vì chỉ thấy là nó thành công, và đó thường là khác biệt giữa "ổn" và "đang âm thầm xuống cấp".
- **Sự im lặng cũng đặt cảnh báo được.** Một quy tắc *job silence* kích hoạt khi một job có tên không báo cáo gì lâu hơn khoảng dung sai bạn chọn. Đó là cách bạn biết consumer tính tiền hằng đêm đã ngừng chạy ngay đêm nó ngừng, chứ không phải vào cuối tháng.

Job thất bại mang cùng thẻ lỗi như request thất bại: stack trace đã map kèm các dòng mã nguồn, các log được ghi trong lần chạy, và waterfall những gì job đã làm trước khi throw. Xem chương [Observability](/observability/overview) để thiết lập.

#### Process riêng <a id="separate-processes"></a>

Job handler cũng có thể chạy trong một process riêng (fork) (xem [Sandboxed processors](https://docs.bullmq.io/guide/workers/sandboxed-processors) trong tài liệu BullMQ). Cách này có vài ưu điểm:

- Process được cô lập (sandbox), nên nếu nó crash, worker không bị ảnh hưởng.
- Bạn có thể chạy code blocking mà không ảnh hưởng tới queue (job không bị treo).
- Tận dụng CPU đa nhân tốt hơn.
- Ít kết nối tới Redis hơn.

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { join } from 'node:path';

@Module({
  imports: [
    BullModule.registerQueue({
      name: 'audio',
      processors: [join(import.meta.dirname, 'processor.js')],
    }),
  ],
})
export class AppModule {}
```

> warning **Cảnh báo** Vì hàm của bạn chạy trong một process được fork, dependency injection (và IoC container) không có sẵn. Hàm processor phải tự chứa (hoặc tự tạo) mọi instance của các dependency bên ngoài mà nó cần.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Có thể bạn muốn truyền tùy chọn `bullmq` theo kiểu bất đồng bộ thay vì tĩnh. Khi đó, hãy dùng method `forRootAsync()`, method này cung cấp vài cách để xử lý cấu hình bất đồng bộ. Tương tự, để truyền tùy chọn queue theo kiểu bất đồng bộ, dùng method `registerQueueAsync()`.

Một cách là dùng hàm factory:

```typescript
BullModule.forRootAsync({
  useFactory: () => ({
    connection: {
      host: 'localhost',
      port: 6379,
    },
  }),
});
```

Factory này hoạt động như mọi [provider bất đồng bộ](/fundamentals/async-providers) khác (ví dụ nó có thể là `async` và có thể inject dependency qua `inject`).

```typescript
BullModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: async (configService: ConfigService) => ({
    connection: {
      host: configService.get('QUEUE_HOST'),
      port: configService.get('QUEUE_PORT'),
    },
  }),
  inject: [ConfigService],
});
```

Cách khác là dùng cú pháp `useClass`:

```typescript
BullModule.forRootAsync({
  useClass: BullConfigService,
});
```

Cách khai báo trên khởi tạo `BullConfigService` bên trong `BullModule` và dùng nó để cung cấp options object bằng cách gọi `createSharedConfiguration()`. Điều này có nghĩa là `BullConfigService` phải implement interface `SharedBullConfigurationFactory`, như bên dưới:

```typescript
@Injectable()
class BullConfigService implements SharedBullConfigurationFactory {
  createSharedConfiguration(): BullRootModuleOptions {
    return {
      connection: {
        host: 'localhost',
        port: 6379,
      },
    };
  }
}
```

Để dùng lại một provider được import từ module khác thay vì tạo `BullConfigService` bên trong `BullModule`, hãy dùng cú pháp `useExisting`.

```typescript
BullModule.forRootAsync({
  imports: [ConfigModule],
  useExisting: ConfigService,
});
```

Cách khai báo này hoạt động giống `useClass`, với một khác biệt quan trọng: `BullModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã có thay vì khởi tạo cái mới.

Tương tự, để truyền tùy chọn queue theo kiểu bất đồng bộ, dùng method `registerQueueAsync()`. Hãy chỉ định thuộc tính `name` bên ngoài hàm factory.

```typescript
BullModule.registerQueueAsync({
  name: 'audio',
  useFactory: () => ({
    connection: {
      host: 'localhost',
      port: 6379,
    },
  }),
});
```

#### Đăng ký thủ công <a id="manual-registration"></a>

Mặc định, `BullModule` tự động đăng ký các thành phần BullMQ (queue, processor và các service event listener) trong lifecycle hook `onModuleInit`. Trong một số trường hợp, đây không phải hành vi bạn muốn. Để ngăn việc tự động đăng ký, hãy bật `manualRegistration` trong `BullModule`:

```typescript
BullModule.forRoot({
  extraOptions: {
    manualRegistration: true,
  },
});
```

Để tự đăng ký các thành phần này, hãy inject `BullRegistrar` và gọi method `register()` của nó, tốt nhất là trong lifecycle hook `onModuleInit()` hoặc `onApplicationBootstrap()`.

```typescript
import { Injectable, OnModuleInit } from '@nestjs/common';
import { BullRegistrar } from '@nestjs/bullmq';

@Injectable()
export class AudioService implements OnModuleInit {
  constructor(private bullRegistrar: BullRegistrar) {}

  onModuleInit() {
    if (yourConditionHere) {
      this.bullRegistrar.register();
    }
  }
}
```

Cho đến khi bạn gọi `BullRegistrar#register()`, không thành phần BullMQ nào hoạt động, nghĩa là không có job nào được xử lý.
#### Cài đặt Bull <a id="bull-installation"></a>

> info **Lưu ý** Nếu bạn dùng BullMQ, hãy bỏ qua phần này và các phần tiếp theo.

Để bắt đầu dùng Bull, hãy cài các dependency cần thiết.

```bash
$ npm install --save @nestjs/bull bull
```

Sau khi cài xong, import `BullModule` vào root module `AppModule`.

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bull';

@Module({
  imports: [
    BullModule.forRoot({
      redis: {
        host: 'localhost',
        port: 6379,
      },
    }),
  ],
})
export class AppModule {}
```

Method `forRoot()` đăng ký một configuration object `bull` mà mọi queue đăng ký trong ứng dụng đều dùng (trừ khi có chỉ định khác). Một configuration object gồm các thuộc tính sau (tất cả đều là tùy chọn):

- `limiter: RateLimiter` - Tùy chọn điều khiển tốc độ xử lý job của queue. Xem [RateLimiter](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết thêm thông tin.
- `redis: RedisOpts` - Tùy chọn cấu hình kết nối Redis. Xem [RedisOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết thêm thông tin.
- `prefix: string` - Prefix cho mọi key của queue.
- `defaultJobOptions: JobOpts` - Tùy chọn điều khiển thiết lập mặc định cho job mới. Xem [JobOpts](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queueadd) để biết thêm thông tin.
- `settings: AdvancedSettings` - Thiết lập cấu hình queue nâng cao. Thường không nên thay đổi. Xem [AdvancedSettings](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết thêm thông tin.

Các tùy chọn này được truyền thẳng vào constructor `Queue` của Bull. Xem [phần Queue trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để biết chi tiết.

Để đăng ký một queue, import dynamic module `BullModule.registerQueue()`, như sau:

```typescript
BullModule.registerQueue({
  name: 'audio',
});
```

> info **Gợi ý** Tạo nhiều queue bằng cách truyền nhiều configuration object (dưới dạng các tham số riêng) vào method `registerQueue()`.

Method `registerQueue()` khởi tạo và/hoặc đăng ký queue. Queue được chia sẻ giữa các module và process kết nối tới cùng một database Redis bên dưới với cùng thông tin đăng nhập. Mỗi queue được xác định bằng thuộc tính `name`. Tên queue vừa đóng vai trò injection token (để inject queue vào controller và provider), vừa là tham số cho các decorator gắn class consumer và listener với queue.

Bạn cũng có thể ghi đè một số tùy chọn đã cấu hình sẵn cho một queue cụ thể, như sau:

```typescript
BullModule.registerQueue({
  name: 'audio',
  redis: {
    port: 6380,
  },
});
```

Vì job được lưu trong Redis, mỗi lần một queue có tên được khởi tạo (ví dụ khi app khởi động hoặc khởi động lại), nó sẽ cố xử lý mọi job cũ còn sót lại từ một phiên chưa hoàn tất trước đó.

Mỗi queue có thể có một hoặc nhiều producer, consumer và listener. Consumer lấy job từ queue theo một thứ tự cụ thể: FIFO (mặc định), LIFO, hoặc theo độ ưu tiên. Phần <a href="application/queues#job-options">tùy chọn job</a> giải thích cách điều khiển thứ tự xử lý.

<app-banner-enterprise></app-banner-enterprise>

#### Cấu hình có tên <a id="named-configurations-1"></a>

Nếu các queue của bạn kết nối tới nhiều instance Redis, bạn có thể dùng một kỹ thuật gọi là **cấu hình có tên** (named configuration). Tính năng này cho phép bạn đăng ký nhiều cấu hình dưới các key chỉ định, rồi tham chiếu tới chúng trong tùy chọn của queue.

Ví dụ, giả sử bạn có thêm một instance Redis (ngoài instance mặc định) được vài queue trong ứng dụng sử dụng, bạn có thể đăng ký cấu hình của nó như sau:

```typescript
BullModule.forRoot('alternative-config', {
  redis: {
    port: 6381,
  },
});
```

Trong ví dụ trên, `'alternative-config'` là một key cấu hình (có thể là chuỗi bất kỳ).

Giờ bạn có thể trỏ tới cấu hình này trong options object của `registerQueue()`:

```typescript
BullModule.registerQueue({
  configKey: 'alternative-config',
  name: 'video',
});
```

#### Producer <a id="producers-1"></a>

Job producer thêm job vào queue. Producer thường là các service của ứng dụng ([provider](/providers) của Nest). Để thêm job vào queue, trước tiên hãy inject queue vào service:

```typescript
import { Injectable } from '@nestjs/common';
import type { Queue } from 'bull';
import { InjectQueue } from '@nestjs/bull';

@Injectable()
export class AudioService {
  constructor(@InjectQueue('audio') private audioQueue: Queue) {}
}
```

> info **Gợi ý** Decorator `@InjectQueue()` xác định queue theo tên của nó, đúng như tên truyền vào lời gọi method `registerQueue()` (ví dụ `'audio'`).

Giờ hãy thêm một job bằng cách gọi method `add()` của queue, truyền vào một data object do người dùng định nghĩa. Dữ liệu job phải serialize được, vì job được lưu trong Redis. Cấu trúc dữ liệu là tùy ý; hãy dùng nó để biểu diễn ý nghĩa của job.

```typescript
const job = await this.audioQueue.add({
  foo: 'bar',
});
```

#### Job có tên <a id="named-jobs"></a>

Job có thể có tên. Điều này cho phép bạn tạo các <a href="application/queues#consumers">consumer</a> chuyên biệt chỉ xử lý job có tên nhất định.

```typescript
const job = await this.audioQueue.add('transcode', {
  foo: 'bar',
});
```

> warning **Cảnh báo** Khi dùng job có tên, bạn phải tạo một processor cho mỗi tên khác nhau được thêm vào queue, nếu không queue sẽ báo thiếu processor cho job đó. Xem <a href="application/queues#consumers">consumer</a> để biết thêm về cách xử lý job có tên.

#### Tùy chọn job <a id="job-options-1"></a>

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

```typescript
const job = await this.audioQueue.add(
  {
    foo: 'bar',
  },
  { delay: 3000 }, // 3 seconds delayed
);
```

Để thêm job vào đầu bên phải của queue (tức là xử lý theo kiểu **LIFO**, Last In First Out), đặt thuộc tính `lifo` thành `true`.

```typescript
const job = await this.audioQueue.add(
  {
    foo: 'bar',
  },
  { lifo: true },
);
```

Để đặt độ ưu tiên cho một job, dùng thuộc tính `priority`.

```typescript
const job = await this.audioQueue.add(
  {
    foo: 'bar',
  },
  { priority: 2 },
);
```

#### Consumer <a id="consumers-1"></a>

Consumer là một **class** định nghĩa các method xử lý job được thêm vào queue, lắng nghe event trên queue, hoặc cả hai. Khai báo class consumer bằng decorator `@Processor()` như sau:

```typescript
import { Processor } from '@nestjs/bull';

@Processor('audio')
export class AudioConsumer {}
```

> info **Gợi ý** Consumer phải được đăng ký làm `providers` để package `@nestjs/bull` có thể nhận diện chúng.

Tham số chuỗi của decorator (ví dụ `'audio'`) là tên của queue cần gắn với các method của class.

Bên trong class consumer, khai báo job handler bằng cách decorate các method handler với decorator `@Process()`.

```typescript
import { Processor, Process } from '@nestjs/bull';
import type { Job } from 'bull';

@Processor('audio')
export class AudioConsumer {
  @Process()
  async transcode(job: Job<unknown>) {
    let progress = 0;
    for (let i = 0; i < 100; i++) {
      await doSomething(job.data);
      progress += 1;
      await job.progress(progress);
    }
    return {};
  }
}
```

Method được decorate (ví dụ `transcode()`) được gọi mỗi khi worker rảnh và có job cần xử lý trong queue. Nó nhận object `job` làm tham số duy nhất. Giá trị nó trả về được lưu trong object job và có thể truy cập sau đó, ví dụ trong listener của event `completed`.

Object `Job` có nhiều method cho phép bạn tương tác với trạng thái của nó. Ví dụ, đoạn code trên dùng method `progress()` để cập nhật tiến độ của job. Xem [phần Job trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#job) để có API `Job` đầy đủ.

Bạn có thể chỉ định một method handler job **chỉ** xử lý job thuộc một loại nhất định (job có `name` cụ thể) bằng cách truyền `name` đó vào decorator `@Process()`, như bên dưới. Một class consumer có thể có nhiều handler `@Process()`, mỗi handler cho một loại job (`name`). Khi dùng job có tên, hãy đảm bảo có handler cho mỗi tên.

```typescript
@Process('transcode')
async transcode(job: Job<unknown>) { ... }
```

> warning **Cảnh báo** Khi bạn định nghĩa nhiều consumer cho cùng một queue, tùy chọn `concurrency` trong `@Process({{ '{' }} concurrency: 1 {{ '}' }})` không có hiệu lực. `concurrency` tối thiểu sẽ bằng số consumer được định nghĩa. Điều này vẫn đúng kể cả khi các handler `@Process()` dùng tên khác nhau để xử lý job có tên.

#### Consumer request-scoped <a id="request-scoped-consumers-1"></a>

Khi một consumer được đánh dấu là request-scoped (xem [injection scope](/fundamentals/injection-scopes#provider-scope)), một instance mới của class sẽ được tạo riêng cho mỗi job. Instance này bị garbage collect sau khi job hoàn tất.

```typescript
@Processor({
  name: 'audio',
  scope: Scope.REQUEST,
})
```

Vì các class consumer request-scoped được khởi tạo động và có scope gắn với một job duy nhất, bạn có thể inject job hiện tại qua constructor bằng token `JOB_REF`.

```typescript
constructor(@Inject(JOB_REF) jobRef: Job) {
  console.log(jobRef);
}
```

> info **Gợi ý** Token `JOB_REF` được import từ package `@nestjs/bull`.

#### Event listener <a id="event-listeners-1"></a>

Bull phát ra một loạt event khi có thay đổi trạng thái của queue và/hoặc job. Package `@nestjs/bull` export một bộ decorator cho phép bạn subscribe một nhóm event chuẩn cốt lõi.

Event listener phải được khai báo bên trong một class <a href="application/queues#consumers">consumer</a> (tức là bên trong class được decorate bằng `@Processor()`). Để lắng nghe một event, dùng một trong các decorator trong bảng dưới đây để khai báo handler cho event đó. Ví dụ, để lắng nghe event phát ra khi một job chuyển sang trạng thái active trong queue `audio`, dùng cách khai báo sau:

```typescript
import { Processor, Process, OnQueueActive } from '@nestjs/bull';
import type { Job } from 'bull';

@Processor('audio')
export class AudioConsumer {

  @OnQueueActive()
  onActive(job: Job) {
    console.log(
      `Processing job ${job.id} of type ${job.name} with data ${job.data}...`,
    );
  }
  ...
```

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

```typescript
@OnGlobalQueueCompleted()
async onGlobalCompleted(jobId: number, result: any) {
  const job = await this.immediateQueue.getJob(jobId);
  console.log('(Global) on completed: job ', job.id, ' -> result: ', result);
}
```

> info **Gợi ý** Để truy cập object `Queue` (để gọi `getJob()`), bạn phải inject nó. Queue cũng phải được đăng ký trong module nơi bạn inject nó.

Ngoài các decorator event listener cụ thể, bạn có thể dùng decorator generic `@OnQueueEvent()` kết hợp với enum `BullQueueEvents` hoặc `BullQueueGlobalEvents`. Xem [phần Events trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#events) để tìm hiểu thêm về event.

#### Quản lý queue <a id="queue-management-1"></a>

Queue có một API cho các chức năng quản lý như tạm dừng và tiếp tục, hay lấy số lượng job ở các trạng thái khác nhau. Xem [phần Queue trong tài liệu tham khảo Bull](https://github.com/OptimalBits/bull/blob/master/REFERENCE.md#queue) để có API đầy đủ. Gọi các method này trực tiếp trên object `Queue`, như trong ví dụ tạm dừng và tiếp tục bên dưới.

Tạm dừng một queue bằng method `pause()`. Queue bị tạm dừng sẽ không xử lý job mới cho đến khi được tiếp tục, nhưng các job đang được xử lý vẫn tiếp tục cho đến khi xong.

```typescript
await audioQueue.pause();
```

Để tiếp tục một queue đã tạm dừng, dùng method `resume()`, như sau:

```typescript
await audioQueue.resume();
```

#### Process riêng <a id="separate-processes-1"></a>

Job handler cũng có thể chạy trong một process riêng (fork) (xem [Separate processes](https://github.com/OptimalBits/bull#separate-processes) trong tài liệu Bull). Cách này có vài ưu điểm:

- Process được cô lập (sandbox), nên nếu nó crash, worker không bị ảnh hưởng.
- Bạn có thể chạy code blocking mà không ảnh hưởng tới queue (job không bị treo).
- Tận dụng CPU đa nhân tốt hơn.
- Ít kết nối tới Redis hơn.

```ts
@@filename(app.module)
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bull';
import { join } from 'node:path';

@Module({
  imports: [
    BullModule.registerQueue({
      name: 'audio',
      processors: [join(import.meta.dirname, 'processor.js')],
    }),
  ],
})
export class AppModule {}
```

Vì hàm của bạn chạy trong một process được fork, dependency injection (và IoC container) không có sẵn. Hàm processor phải tự chứa (hoặc tự tạo) mọi instance của các dependency bên ngoài mà nó cần.

```ts
@@filename(processor)
import { Job, DoneCallback } from 'bull';

export default function (job: Job, cb: DoneCallback) {
  console.log(`[${process.pid}] ${JSON.stringify(job.data)}`);
  cb(null, 'It works');
}
```

#### Cấu hình bất đồng bộ <a id="async-configuration-1"></a>

Có thể bạn muốn truyền tùy chọn `bull` theo kiểu bất đồng bộ thay vì tĩnh. Khi đó, hãy dùng method `forRootAsync()`, method này cung cấp vài cách để xử lý cấu hình bất đồng bộ.

Một cách là dùng hàm factory:

```typescript
BullModule.forRootAsync({
  useFactory: () => ({
    redis: {
      host: 'localhost',
      port: 6379,
    },
  }),
});
```

Factory này hoạt động như mọi [provider bất đồng bộ](/fundamentals/async-providers) khác (ví dụ nó có thể là `async` và có thể inject dependency qua `inject`).

```typescript
BullModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: async (configService: ConfigService) => ({
    redis: {
      host: configService.get('QUEUE_HOST'),
      port: configService.get('QUEUE_PORT'),
    },
  }),
  inject: [ConfigService],
});
```

Cách khác là dùng cú pháp `useClass`:

```typescript
BullModule.forRootAsync({
  useClass: BullConfigService,
});
```

Cách khai báo trên khởi tạo `BullConfigService` bên trong `BullModule` và dùng nó để cung cấp options object bằng cách gọi `createSharedConfiguration()`. Điều này có nghĩa là `BullConfigService` phải implement interface `SharedBullConfigurationFactory`, như bên dưới:

```typescript
@Injectable()
class BullConfigService implements SharedBullConfigurationFactory {
  createSharedConfiguration(): BullRootModuleOptions {
    return {
      redis: {
        host: 'localhost',
        port: 6379,
      },
    };
  }
}
```

Để dùng lại một provider được import từ module khác thay vì tạo `BullConfigService` bên trong `BullModule`, hãy dùng cú pháp `useExisting`.

```typescript
BullModule.forRootAsync({
  imports: [ConfigModule],
  useExisting: ConfigService,
});
```

Cách khai báo này hoạt động giống `useClass`, với một khác biệt quan trọng: `BullModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã có thay vì khởi tạo cái mới.

Tương tự, để truyền tùy chọn queue theo kiểu bất đồng bộ, dùng method `registerQueueAsync()`. Hãy chỉ định thuộc tính `name` bên ngoài hàm factory.

```typescript
BullModule.registerQueueAsync({
  name: 'audio',
  useFactory: () => ({
    redis: {
      host: 'localhost',
      port: 6379,
    },
  }),
});
```

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn trong [sample 26-queues](https://github.com/nestjs/nest/tree/master/sample/26-queues).
