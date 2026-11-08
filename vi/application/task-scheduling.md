### Task scheduling

Task scheduling cho phép bạn chạy code bất kỳ (method hoặc hàm) vào một ngày giờ cố định, lặp lại theo chu kỳ, hoặc chạy một lần sau một khoảng trễ nhất định. Trong thế giới Linux, việc này thường được xử lý ở cấp hệ điều hành bằng các công cụ như [cron](https://en.wikipedia.org/wiki/Cron). Với app Node.js, có vài package giả lập chức năng giống cron. Nest cung cấp package `@nestjs/schedule`, tích hợp với package [cron](https://github.com/kelektiv/node-cron) phổ biến của Node.js. Chương này trình bày về package `@nestjs/schedule`.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài các dependency cần thiết.

```bash
$ npm install --save @nestjs/schedule
```

Để kích hoạt việc lập lịch job, import `ScheduleModule` vào root module `AppModule` và gọi method static `forRoot()`, như bên dưới:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';

@Module({
  imports: [
    ScheduleModule.forRoot()
  ],
})
export class AppModule {}
```

Lời gọi `forRoot()` khởi tạo scheduler và đăng ký mọi <a href="application/task-scheduling#declarative-cron-jobs">cron job</a>, <a href="application/task-scheduling#declarative-timeouts">timeout</a> và <a href="application/task-scheduling#declarative-intervals">interval</a> khai báo trong app của bạn. Các job đã lập lịch bắt đầu chạy trong lifecycle hook `onApplicationBootstrap`, đảm bảo mọi module đều đã load và khai báo xong các job của chúng.

> warning **Cảnh báo** Chỉ gọi `forRoot()` trong một module duy nhất. Mỗi lần import thêm sẽ đăng ký lại mọi handler `@Cron()`, `@Interval()` và `@Timeout()` trong app, nên import nó trong ba module sẽ khiến mỗi job chạy ba lần.

#### Cron job khai báo <a id="declarative-cron-jobs"></a>

Cron job lập lịch để một hàm bất kỳ (lời gọi method) tự động chạy. Cron job có thể chạy:

- Một lần, vào một ngày giờ chỉ định.
- Lặp lại. Job lặp lại có thể chạy tại một thời điểm chỉ định trong một chu kỳ chỉ định (ví dụ mỗi giờ một lần, mỗi tuần một lần, mỗi 5 phút một lần).

Khai báo một cron job bằng cách áp dụng decorator `@Cron()` lên method chứa code cần thực thi, như sau:

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';

@Injectable()
export class TasksService {
  private readonly logger = new Logger(TasksService.name);

  @Cron('45 * * * * *')
  handleCron() {
    this.logger.debug('Called when the current second is 45');
  }
}
```

Trong ví dụ này, method `handleCron()` được gọi mỗi khi giây hiện tại là `45`. Nói cách khác, method chạy mỗi phút một lần, vào giây thứ 45.

Decorator `@Cron()` hỗ trợ các [cron pattern](http://crontab.org/) chuẩn sau:

- Dấu sao (ví dụ `*`)
- Khoảng và danh sách (ví dụ `1-3,5`)
- Bước nhảy (ví dụ `*/2`)

Trong ví dụ trên, ta truyền `45 * * * * *` vào decorator. Bảng chú thích sau cho thấy cách hiểu từng vị trí trong chuỗi cron pattern:

<pre class="language-javascript"><code class="language-javascript">
* * * * * *
| | | | | |
| | | | | ngày trong tuần
| | | | tháng
| | | ngày trong tháng
| | giờ
| phút
giây (tùy chọn)
</code></pre>

Một vài cron pattern mẫu:

<table>
  <tbody>
    <tr>
      <td><code>* * * * * *</code></td>
      <td>mỗi giây</td>
    </tr>
    <tr>
      <td><code>45 * * * * *</code></td>
      <td>mỗi phút, vào giây thứ 45</td>
    </tr>
    <tr>
      <td><code>0 10 * * * *</code></td>
      <td>mỗi giờ, vào đầu phút thứ 10</td>
    </tr>
    <tr>
      <td><code>0 */30 9-17 * * *</code></td>
      <td>mỗi 30 phút từ 9 giờ sáng đến 5 giờ chiều</td>
    </tr>
   <tr>
      <td><code>0 30 11 * * 1-5</code></td>
      <td>Thứ Hai đến Thứ Sáu lúc 11:30 sáng</td>
    </tr>
  </tbody>
</table>

Package `@nestjs/schedule` cung cấp enum `CronExpression` chứa các cron pattern thường dùng. Bạn có thể dùng enum này như sau:

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';

@Injectable()
export class TasksService {
  private readonly logger = new Logger(TasksService.name);

  @Cron(CronExpression.EVERY_30_SECONDS)
  handleCron() {
    this.logger.debug('Called every 30 seconds');
  }
}
```

Trong ví dụ này, method `handleCron()` được gọi mỗi `30` giây. Mọi method được đánh dấu bằng `@Cron()` đều tự động được bọc trong một khối `try-catch`, nên nếu có exception xảy ra, nó sẽ được log ra console.

Cách khác là bạn có thể truyền một object `Date` của JavaScript vào decorator `@Cron()`. Khi đó job sẽ chạy đúng một lần, vào ngày chỉ định.

> info **Gợi ý** Dùng phép tính ngày của JavaScript để lập lịch job theo mốc ngày hiện tại. Ví dụ, `@Cron(new Date(Date.now() + 10 * 1000))` lập lịch một job chạy 10 giây sau khi app khởi động.

Bạn cũng có thể truyền thêm tùy chọn làm tham số thứ hai cho decorator `@Cron()`.

<table>
  <tbody>
    <tr>
      <td><code>name</code></td>
      <td>
        Cho phép bạn truy cập và điều khiển một cron job sau khi nó đã được khai báo.
      </td>
    </tr>
    <tr>
      <td><code>timeZone</code></td>
      <td>
        Chỉ định múi giờ cho việc thực thi. Tùy chọn này thay đổi thời gian thực tế theo múi giờ của bạn. Nếu múi giờ không hợp lệ, một lỗi sẽ được throw. Bạn có thể xem mọi múi giờ có sẵn trên trang <a href="http://momentjs.com/timezone/">Moment Timezone</a>.
      </td>
    </tr>
    <tr>
      <td><code>utcOffset</code></td>
      <td>
        Chỉ định độ lệch múi giờ của bạn thay vì dùng tùy chọn <code>timeZone</code>. Đừng kết hợp nó với <code>timeZone</code>.
      </td>
    </tr>
    <tr>
      <td><code>waitForCompletion</code></td>
      <td>
        Nếu là <code>true</code>, sẽ không có instance nào khác của cron job chạy cho đến khi callback <code>onTick</code> hiện tại hoàn tất. Mọi lần thực thi mới được lên lịch trong lúc cron job hiện tại đang chạy sẽ bị bỏ qua hoàn toàn.
      </td>
    </tr>
    <tr>
      <td><code>disabled</code></td>
      <td>
        Nếu là <code>true</code>, job hoàn toàn không được thực thi (mặc định là <code>false</code>).
      </td>
    </tr>
  </tbody>
</table>

```typescript
import { Injectable } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';

@Injectable()
export class NotificationService {
  @Cron('* * 0 * * *', {
    name: 'notifications',
    timeZone: 'Europe/Paris',
  })
  triggerNotifications() {}
}
```

Với <a href="/application/task-scheduling#dynamic-schedule-module-api">API động</a>, bạn có thể truy cập và điều khiển một cron job sau khi nó đã được khai báo, hoặc tạo cron job một cách động (với cron pattern được định nghĩa lúc runtime). Để truy cập một cron job khai báo qua API, bạn phải gắn job với một tên bằng cách truyền thuộc tính `name` trong options object (tham số thứ hai, tùy chọn, của decorator).

#### Interval khai báo <a id="declarative-intervals"></a>

Để khai báo một method cần chạy theo một chu kỳ (lặp lại) chỉ định, hãy đặt decorator `@Interval()` trước định nghĩa method. Truyền giá trị chu kỳ vào decorator dưới dạng số mili giây, như bên dưới:

```typescript
@Interval(10000)
handleInterval() {
  this.logger.debug('Called every 10 seconds');
}
```

> info **Gợi ý** Bên dưới, cơ chế này dùng hàm `setInterval()` của JavaScript. Bạn cũng có thể dùng cron job để lập lịch các job lặp lại.

Để điều khiển interval khai báo từ bên ngoài class khai báo nó thông qua <a href="/application/task-scheduling#dynamic-schedule-module-api">API động</a>, hãy gắn interval với một tên bằng cách sau:

```typescript
@Interval('notifications', 2500)
handleInterval() {}
```

Mọi method được đánh dấu bằng `@Interval()` đều tự động được bọc trong một khối `try-catch`, nên nếu có exception xảy ra, nó sẽ được log ra console.

<a href="application/task-scheduling#dynamic-intervals">API động</a> cũng cho phép **tạo** các interval động, với thuộc tính của interval được định nghĩa lúc runtime, cũng như **liệt kê và xóa** chúng.

<app-banner-enterprise></app-banner-enterprise>

#### Timeout khai báo <a id="declarative-timeouts"></a>

Để khai báo một method cần chạy một lần sau một khoảng timeout chỉ định, hãy đặt decorator `@Timeout()` trước định nghĩa method. Truyền vào decorator khoảng thời gian tính từ lúc ứng dụng khởi động (tính bằng mili giây), như bên dưới:

```typescript
@Timeout(5000)
handleTimeout() {
  this.logger.debug('Called once after 5 seconds');
}
```

> info **Gợi ý** Bên dưới, cơ chế này dùng hàm `setTimeout()` của JavaScript.

Mọi method được đánh dấu bằng `@Timeout()` đều tự động được bọc trong một khối `try-catch`, nên nếu có exception xảy ra, nó sẽ được log ra console.

Để điều khiển timeout khai báo từ bên ngoài class khai báo nó thông qua <a href="/application/task-scheduling#dynamic-schedule-module-api">API động</a>, hãy gắn timeout với một tên bằng cách sau:

```typescript
@Timeout('notifications', 2500)
handleTimeout() {}
```

<a href="application/task-scheduling#dynamic-timeouts">API động</a> cũng cho phép **tạo** các timeout động, với thuộc tính của timeout được định nghĩa lúc runtime, cũng như **liệt kê và xóa** chúng.

#### API động của schedule module <a id="dynamic-schedule-module-api"></a>

Module `@nestjs/schedule` cung cấp một API động để quản lý các <a href="application/task-scheduling#declarative-cron-jobs">cron job</a>, <a href="application/task-scheduling#declarative-timeouts">timeout</a> và <a href="application/task-scheduling#declarative-intervals">interval</a> khai báo. API này cũng cho phép bạn tạo và quản lý các cron job, timeout và interval **động**, với thuộc tính được định nghĩa lúc runtime.

#### Cron job động <a id="dynamic-cron-jobs"></a>

Lấy tham chiếu tới một instance `CronJob` theo tên từ bất cứ đâu trong code bằng API `SchedulerRegistry`. Đầu tiên, inject `SchedulerRegistry` bằng injection qua constructor chuẩn:

```typescript
constructor(private schedulerRegistry: SchedulerRegistry) {}
```

> info **Gợi ý** Import `SchedulerRegistry` từ package `@nestjs/schedule`.

Sau đó dùng nó trong class. Giả sử một cron job được tạo với khai báo sau:

```typescript
@Cron('* * 8 * * *', {
  name: 'notifications',
})
triggerNotifications() {}
```

Truy cập job này như sau:

```typescript
const job = this.schedulerRegistry.getCronJob('notifications');

job.stop();
console.log(job.lastDate());
```

Method `getCronJob()` trả về cron job có tên tương ứng. Object `CronJob` trả về có các method sau:

- `stop()` - dừng một job đang được lập lịch.
- `start()` - khởi động lại một job đã bị dừng.
- `setTime(time: CronTime)` - dừng job, đặt thời gian mới cho nó, rồi khởi động lại.
- `lastDate()` - trả về một `Date` của JavaScript biểu diễn lần thực thi gần nhất của job, hoặc `null` nếu job chưa chạy lần nào.
- `nextDate()` - trả về biểu diễn `DateTime` của thời điểm lần thực thi tiếp theo của job được lên lịch.
- `nextDates(count: number)` - trả về một mảng (kích thước `count`) các biểu diễn `DateTime` cho các thời điểm tiếp theo sẽ kích hoạt job. `count` mặc định là 0, khi đó trả về mảng rỗng.

> info **Gợi ý** Gọi `toJSDate()` trên một object `DateTime` (một type của [Luxon](https://moment.github.io/luxon/)) để chuyển nó thành `Date` tương đương của JavaScript.

**Tạo** một cron job mới một cách động bằng method `SchedulerRegistry#addCronJob`, như sau:

```typescript
addCronJob(name: string, seconds: string) {
  const job = new CronJob(`${seconds} * * * * *`, () => {
    this.logger.warn(`time (${seconds}) for job ${name} to run!`);
  });

  this.schedulerRegistry.addCronJob(name, job);
  job.start();

  this.logger.warn(
    `job ${name} added for each minute at ${seconds} seconds!`,
  );
}
```

Đoạn code này dùng class `CronJob` từ package `cron` để tạo cron job. Constructor của `CronJob` nhận một cron pattern (giống như <a href="application/task-scheduling#declarative-cron-jobs">decorator</a> `@Cron()`) làm tham số thứ nhất, và một callback cần thực thi khi bộ hẹn giờ cron kích hoạt làm tham số thứ hai. Method `SchedulerRegistry#addCronJob` nhận hai tham số: tên của `CronJob`, và chính object `CronJob`.

> warning **Cảnh báo** Nhớ inject `SchedulerRegistry` trước khi truy cập nó. Import `CronJob` từ package `cron`.

**Xóa** một cron job có tên bằng method `SchedulerRegistry#deleteCronJob`, như sau:

```typescript
deleteCron(name: string) {
  this.schedulerRegistry.deleteCronJob(name);
  this.logger.warn(`job ${name} deleted!`);
}
```

**Liệt kê** mọi cron job bằng method `SchedulerRegistry#getCronJobs`, như sau:

```typescript
getCrons() {
  const jobs = this.schedulerRegistry.getCronJobs();
  jobs.forEach((value, key, map) => {
    let next;
    try {
      next = value.nextDate().toJSDate();
    } catch (e) {
      next = 'error: next fire date is in the past!';
    }
    this.logger.log(`job: ${key} -> next: ${next}`);
  });
}
```

Method `getCronJobs()` trả về một `Map`. Đoạn code này duyệt qua map và gọi method `nextDate()` của từng `CronJob`. Trong API của `CronJob`, `nextDate()` sẽ throw exception nếu một job đã chạy xong và không còn thời điểm kích hoạt nào trong tương lai.

#### Interval động <a id="dynamic-intervals"></a>

Lấy tham chiếu tới một interval bằng method `SchedulerRegistry#getInterval`. Như ở trên, inject `SchedulerRegistry` bằng injection qua constructor chuẩn:

```typescript
constructor(private schedulerRegistry: SchedulerRegistry) {}
```

Sau đó dùng nó như sau:

```typescript
const interval = this.schedulerRegistry.getInterval('notifications');
clearInterval(interval);
```

**Tạo** một interval mới một cách động bằng method `SchedulerRegistry#addInterval`, như sau:

```typescript
addInterval(name: string, milliseconds: number) {
  const callback = () => {
    this.logger.warn(`Interval ${name} executing at time (${milliseconds})!`);
  };

  const interval = setInterval(callback, milliseconds);
  this.schedulerRegistry.addInterval(name, interval);
}
```

Đoạn code này tạo một interval JavaScript chuẩn, rồi truyền nó vào method `SchedulerRegistry#addInterval`.
Method đó nhận hai tham số: tên của interval, và chính interval đó.

**Xóa** một interval có tên bằng method `SchedulerRegistry#deleteInterval`, như sau:

```typescript
deleteInterval(name: string) {
  this.schedulerRegistry.deleteInterval(name);
  this.logger.warn(`Interval ${name} deleted!`);
}
```

**Liệt kê** tên của mọi interval bằng method `SchedulerRegistry#getIntervals`, như sau:

```typescript
getIntervals() {
  const intervals = this.schedulerRegistry.getIntervals();
  intervals.forEach(key => this.logger.log(`Interval: ${key}`));
}
```

#### Timeout động <a id="dynamic-timeouts"></a>

Lấy tham chiếu tới một timeout bằng method `SchedulerRegistry#getTimeout`. Như ở trên, inject `SchedulerRegistry` bằng injection qua constructor chuẩn:

```typescript
constructor(private readonly schedulerRegistry: SchedulerRegistry) {}
```

Sau đó dùng nó như sau:

```typescript
const timeout = this.schedulerRegistry.getTimeout('notifications');
clearTimeout(timeout);
```

**Tạo** một timeout mới một cách động bằng method `SchedulerRegistry#addTimeout`, như sau:

```typescript
addTimeout(name: string, milliseconds: number) {
  const callback = () => {
    this.logger.warn(`Timeout ${name} executing after (${milliseconds})!`);
  };

  const timeout = setTimeout(callback, milliseconds);
  this.schedulerRegistry.addTimeout(name, timeout);
}
```

Đoạn code này tạo một timeout JavaScript chuẩn, rồi truyền nó vào method `SchedulerRegistry#addTimeout`.
Method đó nhận hai tham số: tên của timeout, và chính timeout đó.

**Xóa** một timeout có tên bằng method `SchedulerRegistry#deleteTimeout`, như sau:

```typescript
deleteTimeout(name: string) {
  this.schedulerRegistry.deleteTimeout(name);
  this.logger.warn(`Timeout ${name} deleted!`);
}
```

**Liệt kê** tên của mọi timeout bằng method `SchedulerRegistry#getTimeouts`, như sau:

```typescript
getTimeouts() {
  const timeouts = this.schedulerRegistry.getTimeouts();
  timeouts.forEach(key => this.logger.log(`Timeout: ${key}`));
}
```

#### Chạy trên nhiều instance <a id="running-on-several-instances"></a>

Scheduler chạy mọi job trong mọi process của ứng dụng. Với ba instance đứng sau một load balancer, một job lập lịch bằng `@Cron('0 2 * * *')` sẽ chạy ba lần mỗi đêm: ba lần export hóa đơn, ba đợt email nhắc nhở.

Để mỗi lần kích hoạt chỉ chạy job trên một instance, hãy thêm `@OnOneInstance()` từ [`@nestjs/locks`](/reliability/locks) cạnh decorator `@Cron()`, `@Interval()` hoặc `@Timeout()` của nó:

```typescript
import { Injectable } from '@nestjs/common';
import { OnOneInstance } from '@nestjs/locks';
import { Cron } from '@nestjs/schedule';

@Injectable()
export class InvoicesJob {
  @Cron('0 2 * * *')
  @OnOneInstance({ key: 'invoices:nightly-export' })
  async exportInvoices() {
    // ...
  }
}
```

Các instance phối hợp với nhau qua một lock store dùng chung, như database PostgreSQL hoặc Redis của bạn. Instance đầu tiên kích hoạt job sẽ giữ một lease trên job đó và liên tục gia hạn trong khi nó còn chạy, còn các instance khác sẽ bỏ qua lượt kích hoạt của mình thay vì xếp hàng chờ. Nếu instance đang giữ job dừng lại, một instance khác sẽ tiếp quản job ở lượt kích hoạt kế tiếp. Một job có thể chạy lâu hơn chu kỳ của nó thì nên thêm `@WithoutOverlapping()`, decorator này bỏ qua một lượt kích hoạt nếu lần chạy trước vẫn chưa xong. [Distributed lock](/reliability/locks) chỉ cách đăng ký module và store.

#### Biết chắc một cron job đã thực sự chạy <a id="knowing-a-cron-job-actually-ran"></a>

Một job đã lập lịch mà throw lỗi là vấn đề bạn sẽ được biết. Một job đã lập lịch mà âm thầm *không còn được lên lịch nữa* (process bị crash, container bị gỡ khỏi lịch, một đợt deploy đẩy lên biểu thức `@Cron()` bị gõ sai) là vấn đề không ai hay biết cho đến khi bản báo cáo mà nó tạo ra bị thiếu.

Đây chính là kiểu lỗi mà cron monitoring sinh ra để xử lý, và [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') đáp ứng được mà không cần dịch vụ ping bên thứ ba hay một heartbeat URL để job gọi khi kết thúc. Các lần chạy theo lịch được báo cáo dưới dạng **job**, cạnh các queue consumer, mỗi lần đều có thời gian chạy, kết quả và lý do thất bại. Một quy tắc cảnh báo **job silence** sẽ kích hoạt khi một job có tên không báo cáo gì trong khoảng dung sai bạn đặt, từ 2 phút đến 7 ngày: *"báo cho tôi nếu `daily-invoices` không báo cáo gì trong 26 giờ qua"*.

Hai chi tiết giúp tính năng này thực sự hữu ích thay vì gây nhiễu. Một scope chưa từng báo cáo gì sẽ không kích hoạt cảnh báo, nên bạn có thể thêm quy tắc trước khi job được ship mà không bị gọi dậy vì thứ chưa được tích hợp. Và các quy tắc có lịch tắt tiếng định kỳ, nên một job vốn không chạy vào cuối tuần sẽ không đánh thức ai vào sáng thứ Bảy.

Một handler cần tự báo cáo tiến độ có thể inject `TracerService` và ghi lại span hoặc custom metric từ bên trong lần chạy. Metric nói riêng không gắn với trace, nên có thể được báo cáo từ cả cron job lẫn lifecycle hook. Xem [Instrumentation thủ công](/observability/manual-instrumentation) cho phần đó, và chương [Observability](/observability/overview) để thiết lập.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn trong [sample 27-scheduling](https://github.com/nestjs/nest/tree/master/sample/27-scheduling).
