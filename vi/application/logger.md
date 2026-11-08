### Logger

Nest có sẵn một logger được dùng trong lúc bootstrap ứng dụng và trong vài trường hợp khác, như hiển thị các exception đã bắt được (tức là log hệ thống). Chức năng này do class `Logger` trong package `@nestjs/common` cung cấp. Bạn có thể toàn quyền điều khiển hành vi của hệ thống log, bao gồm:

- tắt hoàn toàn việc log
- chỉ định mức độ chi tiết (ví dụ hiển thị lỗi, cảnh báo, thông tin debug, v.v.)
- cấu hình định dạng của log message (raw, JSON, có màu, v.v.)
- ghi đè timestamp trong logger mặc định (ví dụ dùng chuẩn ISO 8601 làm định dạng ngày)
- ghi đè hoàn toàn logger mặc định
- tùy biến logger mặc định bằng cách kế thừa nó
- dùng dependency injection để đơn giản hóa việc kết hợp và test ứng dụng

Bạn cũng có thể dùng logger có sẵn, hoặc tự tạo bản implement riêng, để log các event và message ở cấp ứng dụng của riêng bạn.

Logger có sẵn không chỉ là một tiện ích cho lúc phát triển. Kết hợp với [output JSON](#json-logging), [structured logging params](#structured-logging-params), và trace id mà [NestJS Observe](#correlating-logs-with-requests) gắn vào mọi dòng log được ghi trong một request, nó đáp ứng những gì hầu hết ứng dụng production cần ở một logger: mỗi dòng là một bản ghi máy đọc được trên stdout, các trường có thể truy vấn, các log level, và cách để nối mỗi dòng ngược về request đã ghi ra nó. Các nền tảng container và hệ thống tổng hợp log (CloudWatch, Cloud Logging, Datadog, Loki, Elasticsearch, v.v.) tiếp nhận output đó nguyên trạng, không cần thêm dependency nào trong ứng dụng. Phần [Log trên production](#logging-in-production) bên dưới trình bày cách thiết lập đầy đủ.

Hãy tìm đến một library chuyên dụng như [Pino](https://github.com/pinojs/pino) hoặc [Winston](https://github.com/winstonjs/winston) khi bạn cần thứ mà logger có sẵn cố ý không làm: ghi ra file hoặc các transport khác từ bên trong process, che giấu trường dữ liệu (redaction), hoặc vắt kiệt thông lượng cho những service log cực nhiều. Xem [Dùng logger bên ngoài](#use-external-logger).

#### Tùy biến cơ bản <a id="basic-customization"></a>

Để tắt log, đặt thuộc tính `logger` thành `false` trong object tùy chọn ứng dụng Nest (tùy chọn), truyền làm tham số thứ hai cho method `NestFactory.create()`.

```typescript
const app = await NestFactory.create(AppModule, {
  logger: false,
});
await app.listen(process.env.PORT ?? 3000);
```

Để bật những log level cụ thể, đặt thuộc tính `logger` thành một mảng chuỗi chỉ định các log level cần hiển thị, như sau:

```typescript
const app = await NestFactory.create(AppModule, {
  logger: ['error', 'warn'],
});
await app.listen(process.env.PORT ?? 3000);
```

Các giá trị trong mảng có thể là bất kỳ tổ hợp nào của `'log'`, `'fatal'`, `'error'`, `'warn'`, `'debug'` và `'verbose'`.

> info **Gợi ý** Log level được kích hoạt theo kiểu bậc thang từ level nghiêm trọng nhất trong mảng: mọi level nghiêm trọng ít nhất bằng level đó cũng được bật. Do đó `['log']` cũng bật luôn `'warn'`, `'error'` và `'fatal'`. Các level ít nghiêm trọng hơn chỉ được bật nếu được liệt kê, nên `['debug', 'error']` bật `'debug'`, `'error'` và `'fatal'`, nhưng không bật `'log'` hay `'warn'`.

Để bật một level và mọi level nghiêm trọng hơn nó, hãy tạo mảng bằng `filterLogLevels()` thay vì liệt kê các level bằng tay. Hàm này nhận một chuỗi, nên rất hợp để dùng với biến môi trường:

```typescript
import { filterLogLevels } from '@nestjs/common';

const app = await NestFactory.create(AppModule, {
  logger: filterLogLevels(process.env.LOG_LEVEL ?? '>=warn'), // ['warn', 'error', 'fatal']
});
```

Ngoài `'>=warn'`, nó còn nhận `'>warn'` (chỉ những level nghiêm trọng hơn `warn`), một danh sách phân cách bằng dấu phẩy như `'log,error'`, hoặc một level đơn lẻ. Chuỗi rỗng hoặc không nhận diện được sẽ trả về mọi level, còn một level không xác định đứng sau `>` hoặc `>=` sẽ gây throw.

Để thay đổi các level sau khi ứng dụng đã được tạo (ví dụ khi cấu hình đã load xong), truyền một mảng level vào `app.useLogger()`. Nest sẽ chuyển nó cho method `setLogLevels()` của logger hiện tại:

```typescript
app.useLogger(['error', 'warn']);
```

Để tắt output có màu, truyền một instance `ConsoleLogger` có thuộc tính `colors` đặt thành `false` làm giá trị của thuộc tính `logger`:

```typescript
const app = await NestFactory.create(AppModule, {
  logger: new ConsoleLogger({
    colors: false,
  }),
});
```

Màu cũng bị tắt mặc định khi biến môi trường `NO_COLOR` được đặt thành bất kỳ giá trị không rỗng nào.

Để cấu hình prefix cho mỗi log message, truyền một instance `ConsoleLogger` có đặt thuộc tính `prefix`:

```typescript
const app = await NestFactory.create(AppModule, {
  logger: new ConsoleLogger({
    prefix: 'MyApp', // Default is "Nest"
  }),
});
```

Bảng sau liệt kê mọi tùy chọn có sẵn:

| Tùy chọn          | Mô tả                                                                                                                                                                                                                                                                                                                         | Mặc định                                       |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `logLevels`       | Các log level được bật.                                                                                                                                                                                                                                                                                                       | `['log', 'fatal', 'error', 'warn', 'debug', 'verbose']` |
| `timestamp`       | Nếu bật, sẽ in timestamp (khoảng chênh lệch thời gian) giữa log message hiện tại và log message trước đó. Lưu ý: tùy chọn này không được dùng khi bật `json`.                                                                                                                                                                  | `false`                                        |
| `prefix`          | Prefix dùng cho mỗi log message. Lưu ý: tùy chọn này không được dùng khi bật `json`.                                                                                                                                                                                                                                          | `Nest`                                         |
| `json`            | Nếu bật, sẽ in log message ở định dạng JSON.                                                                                                                                                                                                                                                                                  | `false`                                        |
| `colors`          | Nếu bật, sẽ in log message có màu.                                                                                                                                                                                                                                                                                            | `true` (`false` nếu bật `json` hoặc có đặt `NO_COLOR`) |
| `context`         | Context của logger.                                                                                                                                                                                                                                                                                                           | `undefined`                                    |
| `forceConsole`    | Nếu bật, sẽ dùng `console.log`/`console.error` thay vì `process.stdout.write`/`process.stderr.write`. Hữu ích trong các môi trường test buffer lại các lời gọi console, như Jest.                                                                                                                                                | `false`                                        |
| `compact`         | Nếu bật, sẽ in log message trên một dòng duy nhất, kể cả khi đó là object có nhiều thuộc tính. Nếu đặt là một số, n phần tử trong cùng sẽ được gộp trên một dòng miễn là mọi thuộc tính vừa trong breakLength. Các phần tử mảng ngắn cũng được gom lại với nhau.                                                               | `false` (`true` nếu bật `json`)                |
| `maxArrayLength`  | Chỉ định số phần tử tối đa của Array, TypedArray, Map, Set, WeakMap và WeakSet được đưa vào khi format. Đặt null hoặc Infinity để hiện mọi phần tử. Đặt 0 hoặc số âm để không hiện phần tử nào. Bị bỏ qua khi bật `json`, tắt màu, và `compact` đặt là true, vì khi đó output là JSON parse được.                              | `100`                                          |
| `maxStringLength` | Chỉ định số ký tự tối đa được đưa vào khi format. Đặt null hoặc Infinity để hiện tất cả. Đặt 0 hoặc số âm để không hiện ký tự nào. Bị bỏ qua khi bật `json`, tắt màu, và `compact` đặt là true, vì khi đó output là JSON parse được.                                                                                          | `10000`                                        |
| `sorted`          | Nếu bật, sẽ sắp xếp key khi format object. Cũng có thể là một hàm sắp xếp tùy chỉnh. Bị bỏ qua khi bật `json`, tắt màu, và `compact` đặt là true, vì khi đó output là JSON parse được.                                                                                                                                        | `false`                                        |
| `depth`           | Chỉ định số lần đệ quy khi format object. Hữu ích để xem xét các object lớn. Để đệ quy tới kích thước call stack tối đa, truyền Infinity hoặc null. Bị bỏ qua khi bật `json`, tắt màu, và `compact` đặt là true, vì khi đó output là JSON parse được.                                                                         | `5`                                            |
| `showHidden`      | Nếu là true, các symbol và thuộc tính non-enumerable của object được đưa vào kết quả format. Các mục của WeakMap và WeakSet cũng được đưa vào, cùng với các thuộc tính prototype do người dùng định nghĩa                                                                                                                      | `false`                                        |
| `breakLength`     | Độ dài mà tại đó giá trị đầu vào được tách thành nhiều dòng. Đặt Infinity để format đầu vào thành một dòng duy nhất (kết hợp với "compact" đặt là true). Bị bỏ qua khi bật `json`, tắt màu, và `compact` đặt là true, vì khi đó output là JSON parse được.                                                                    | `Infinity` khi bật `compact`, hoặc khi tắt màu và `compact` không được đặt tường minh là `false`; ngược lại là `80` |

#### Log dạng JSON <a id="json-logging"></a>

Log dạng JSON rất quan trọng cho observability của ứng dụng và cho việc tích hợp với các hệ thống quản lý log. Để bật, hãy tạo một instance `ConsoleLogger` với thuộc tính `json` đặt thành `true`, và truyền nó làm giá trị của thuộc tính `logger` khi tạo instance ứng dụng:

```typescript
const app = await NestFactory.create(AppModule, {
  logger: new ConsoleLogger({
    json: true,
  }),
});
```

Cấu hình này xuất log ở định dạng JSON có cấu trúc, giúp dễ tích hợp với các hệ thống bên ngoài như hệ thống tổng hợp log và các nền tảng cloud. Ví dụ, những nền tảng như **AWS ECS** (Elastic Container Service) hỗ trợ sẵn log JSON, cho phép các tính năng như:

- **Lọc log**: thu hẹp log dựa trên các trường như log level, timestamp, hoặc metadata tùy chỉnh.
- **Tìm kiếm và phân tích**: dùng các công cụ truy vấn để phân tích và theo dõi xu hướng trong hành vi của ứng dụng.

Nếu bạn đang dùng [NestJS Mau](https://mau.nestjs.com), log JSON cũng giúp bạn xem log ở định dạng có cấu trúc, ngăn nắp, đặc biệt hữu ích cho việc debug và theo dõi hiệu năng.

> info **Lưu ý** Khi `json` được đặt thành `true`, `ConsoleLogger` mặc định đặt `colors` thành `false` và `compact` thành `true`. Với hai giá trị này, mỗi mục được serialize bằng `JSON.stringify()`, nên output là JSON hợp lệ, không có ký tự định dạng thừa. Khi phát triển, bạn có thể đặt tường minh `colors` thành `true` (hoặc `compact` thành `false`). Khi đó các mục được render bằng `util.inspect()` của Node, dễ đọc hơn khi debug ở local nhưng không còn là JSON chuẩn.

Khi bật log JSON, output trông như sau (trên một dòng duy nhất):

```json
{
  "level": "log",
  "pid": 19096,
  "timestamp": 1607370779834,
  "message": "Starting Nest application...",
  "context": "NestFactory"
}
```

Mỗi mục có các trường sau:

- `level`: log level.
- `pid`: process id.
- `timestamp`: thời điểm mục được ghi, tính bằng mili giây kể từ Unix epoch. Các tùy chọn `timestamp` và `prefix`, cùng với [định dạng timestamp tùy chỉnh](#extend-built-in-logger), chỉ áp dụng cho output dạng text.
- `message`: message, đúng như được truyền vào logger.
- `context`: context của logger, nếu có.
- `stack`: stack trace truyền vào `error()`, nếu có.
- `params`: các [structured logging params](#structured-logging-params), nếu có truyền.

Giống như ở chế độ text, các mục `error` được ghi ra stderr, còn mọi level khác được ghi ra stdout.

#### Structured logging params

Log message thường cần mang theo metadata: user id, thời gian xử lý request, correlation id. Kể từ NestJS v12, các object thuần truyền **sau** tham số message đầu tiên được xem là structured params và được gắn vào cùng một mục log, thay vì bị xuất ra thành các bản ghi log riêng.

```typescript
const logger = new Logger('UserService');
logger.log('User created', { userId: 1, email: 'foo@bar.com' });
```

Ở chế độ text, params được nối vào ngay trên cùng dòng đã format:

```plaintext
[Nest] 3785  - 02/26/2026, 10:04:41 AM     LOG [UserService] User created { userId: 1, email: 'foo@bar.com' }
```

Khi truyền nhiều object thuần, chúng được merge thành một bộ params duy nhất:

```typescript
logger.log('Request handled', { method: 'GET' }, { path: '/api', duration: 42 });
```

```plaintext
[Nest] 3785  - 02/26/2026, 10:04:41 AM     LOG [UserService] Request handled { method: 'GET', path: '/api', duration: 42 }
```

Ở chế độ JSON, params mặc định được lồng dưới key `params`:

```json
{
  "level": "log",
  "pid": 3785,
  "timestamp": 1772089691769,
  "message": "User created",
  "context": "UserService",
  "params": { "userId": 1, "email": "foo@bar.com" }
}
```

Để trải chúng ra ở gốc của object JSON (một số hệ thống tổng hợp log thích kiểu này hơn), hãy bật `flattenParams`:

```typescript
new ConsoleLogger({ json: true, flattenParams: true });
```

```json
{
  "level": "log",
  "pid": 3785,
  "timestamp": 1772089691769,
  "message": "User created",
  "context": "UserService",
  "userId": 1,
  "email": "foo@bar.com"
}
```

Các tùy chọn liên quan của `ConsoleLogger` là:

| Tùy chọn           | Mô tả                                                                                                         | Mặc định |
| ------------------ | ------------------------------------------------------------------------------------------------------------- | -------- |
| `structuredParams` | Nếu bật, các object thuần được log sau message sẽ được gắn vào cùng mục log dưới dạng params.                 | `true`   |
| `flattenParams`    | Nếu bật, params được trải ra ở gốc của bản ghi JSON thay vì lồng dưới `params`. Param nào có key trùng với key bản ghi đã dùng (như `message` hay `level`) sẽ bị bỏ. Chỉ áp dụng ở chế độ JSON; yêu cầu `structuredParams`. | `false`  |

> info **Gợi ý** Chỉ **object thuần** mới được xem là params. Mảng, chuỗi, số, instance của class và `null` vẫn được log thành các message riêng (một chuỗi truyền làm tham số *cuối cùng* vẫn được xem là context), và một object thuần truyền làm tham số *đầu tiên* vẫn được xem là chính message. Đặt `structuredParams: false` để khôi phục hành vi trước v12.

#### Log trên production <a id="logging-in-production"></a>

Kết hợp lại, output JSON và structured params cho bạn log đạt chuẩn production chỉ với logger có sẵn:

```typescript
// main.ts
const app = await NestFactory.create(AppModule, {
  logger: new ConsoleLogger({
    json: true,
    logLevels: ['log', 'warn', 'error', 'fatal'],
  }),
});
```

```typescript
// orders.service.ts
@Injectable()
export class OrdersService {
  private readonly logger = new Logger(OrdersService.name);

  async capture(order: Order) {
    // ...
    this.logger.log('Payment captured', { orderId: order.id, amount: order.total });
  }
}
```

Khi cài [NestJS Observe](#correlating-logs-with-requests), mỗi dòng được ghi trong một request còn mang thêm trace id của request đó, mà không cần sửa bất kỳ lời gọi log nào:

```json
{"level":"log","pid":66803,"timestamp":1789978166281,"message":"Payment captured","context":"OrdersService","params":{"orderId":"ord_8f2a","amount":4200},"traceId":"0199a3f2-7c1e-7b40-9d2a-5e8f1c3b7a64"}
```

Chỉ một dòng đó đã lọc được theo level và context, truy vấn được theo `orderId`, và nối được với mọi dòng khác của cùng request, đúng là việc mà hầu hết các team cài logger bên thứ ba để làm. Hãy ghi log ra stdout như thế này và để nền tảng (Docker, Kubernetes, ECS, Cloud Run, v.v.) thu thập và chuyển đi. Cách này giữ việc xoay vòng file, buffer và vận chuyển log nằm ngoài process ứng dụng của bạn.

> info **Gợi ý** Đặt `flattenParams: true` nếu hệ thống tổng hợp log của bạn chỉ đánh index các trường ở cấp cao nhất, để `orderId` trở thành trường ở gốc thay vì `params.orderId`.

#### Dùng logger để log ứng dụng <a id="using-the-logger-for-application-logging"></a>

Bạn có thể kết hợp vài kỹ thuật ở trên để có hành vi và định dạng nhất quán giữa log hệ thống của Nest và log event/message của chính ứng dụng.

Một cách làm tốt là khởi tạo class `Logger` từ `@nestjs/common` trong mỗi service, truyền tên service làm tham số `context` cho constructor của `Logger`:

```typescript
import { Logger, Injectable } from '@nestjs/common';

@Injectable()
class MyService {
  private readonly logger = new Logger(MyService.name);

  doSomething() {
    this.logger.log('Doing something...');
  }
}
```

Trong bản implement logger mặc định, `context` được in trong dấu ngoặc vuông, như `NestFactory` trong ví dụ dưới đây:

```bash
[Nest] 19096  - 12/08/2019, 7:12:59 AM     LOG [NestFactory] Starting Nest application...
```

Nếu một message tốn kém để tạo ra, hãy truyền vào một hàm trả về message đó. Ở định dạng text mặc định, `ConsoleLogger` có sẵn chỉ gọi hàm khi level đó được bật, nên một dòng `debug` bị tắt sẽ không tốn gì cả:

```typescript
this.logger.debug(() => `Cache state: ${JSON.stringify(this.cache.dump())}`);
```

Nếu bạn cung cấp một custom logger qua `app.useLogger()`, Nest sẽ dùng nó bên trong, và các lời gọi qua instance `Logger` đều được chuyển cho nó. Code của bạn vẫn không phụ thuộc vào bản implement cụ thể, và bạn có thể thay logger mặc định bằng logger của riêng mình chỉ bằng cách gọi `app.useLogger()`.

Ví dụ, nếu bạn làm theo các bước trong phần <a href="application/logger#dependency-injection">Dependency injection</a> bên dưới và gọi `app.useLogger(app.get(MyLogger))`, các lời gọi `this.logger.log()` sau đó từ `MyService` sẽ dẫn tới việc gọi method `log()` của instance `MyLogger`.

Cách này phù hợp với hầu hết trường hợp. Nếu bạn cần tùy biến nhiều hơn (như thêm và gọi các method tùy chỉnh), xem phần <a href="application/logger#injecting-a-custom-logger">Inject custom logger</a>.

#### Log kèm timestamp <a id="logs-with-timestamps"></a>

Để in khoảng chênh lệch timestamp cho mỗi message được log, truyền thiết lập tùy chọn `timestamp: true` khi tạo instance logger:

```typescript
import { Logger, Injectable } from '@nestjs/common';

@Injectable()
class MyService {
  private readonly logger = new Logger(MyService.name, { timestamp: true });

  doSomething() {
    this.logger.log('Doing something with timestamp here ->');
  }
}
```

Kết quả sẽ có định dạng như sau:

```bash
[Nest] 19096  - 04/19/2024, 7:12:59 AM     LOG [MyService] Doing something with timestamp here -> +5ms
```

Để ý `+5ms` ở cuối dòng. Đó là thời gian trôi qua kể từ dòng trước đó được ghi bởi bất kỳ `ConsoleLogger` nào trong process, không chỉ bởi logger này.

#### Implement tùy chỉnh <a id="custom-implementation"></a>

Bạn có thể cung cấp một bản implement logger tùy chỉnh để Nest dùng cho log hệ thống, bằng cách đặt thuộc tính `logger` thành một object thỏa mãn interface `LoggerService`. Ví dụ, bạn có thể bảo Nest dùng object JavaScript toàn cục `console` (object này implement interface `LoggerService`), như sau:

```typescript
const app = await NestFactory.create(AppModule, {
  logger: console,
});
await app.listen(process.env.PORT ?? 3000);
```

Để implement custom logger của riêng bạn, hãy implement từng method của interface `LoggerService`, như bên dưới:

```typescript
import { LoggerService, LogLevel, Injectable } from '@nestjs/common';

@Injectable()
export class MyLogger implements LoggerService {
  /**
   * Write a 'log' level log.
   */
  log(message: any, ...optionalParams: any[]) {}

  /**
   * Write a 'fatal' level log.
   */
  fatal(message: any, ...optionalParams: any[]) {}

  /**
   * Write an 'error' level log.
   */
  error(message: any, ...optionalParams: any[]) {}

  /**
   * Write a 'warn' level log.
   */
  warn(message: any, ...optionalParams: any[]) {}

  /**
   * Write a 'debug' level log.
   */
  debug?(message: any, ...optionalParams: any[]) {}

  /**
   * Write a 'verbose' level log.
   */
  verbose?(message: any, ...optionalParams: any[]) {}

  /**
   * Set the enabled log levels. Called by `app.useLogger()`
   * when it's given an array of levels.
   */
  setLogLevels?(levels: LogLevel[]) {}
}
```

Sau đó bạn có thể cung cấp một instance `MyLogger` qua thuộc tính `logger` của object tùy chọn ứng dụng Nest:

```typescript
const app = await NestFactory.create(AppModule, {
  logger: new MyLogger(),
});
await app.listen(process.env.PORT ?? 3000);
```

Kỹ thuật này tuy đơn giản nhưng không dùng dependency injection cho class `MyLogger`. Điều này có thể gây khó khăn, đặc biệt là khi test, và hạn chế khả năng tái sử dụng `MyLogger`. Để có giải pháp tốt hơn, xem phần <a href="application/logger#dependency-injection">Dependency injection</a> bên dưới.

#### Kế thừa logger có sẵn <a id="extend-built-in-logger"></a>

Thay vì viết logger từ đầu, có thể bạn chỉ cần kế thừa class `ConsoleLogger` có sẵn và ghi đè một số hành vi được chọn của bản implement mặc định:

```typescript
import { ConsoleLogger } from '@nestjs/common';

export class MyLogger extends ConsoleLogger {
  error(message: any, stack?: string, context?: string) {
    // add your tailored logic here
    super.error(...arguments);
  }
}
```

Cùng cách đó cũng dùng để đổi định dạng timestamp. Ví dụ, để in timestamp theo ISO 8601 thay vì ngày định dạng theo locale, hãy ghi đè method protected `getTimestamp()`:

```typescript
import { ConsoleLogger } from '@nestjs/common';

export class IsoTimestampLogger extends ConsoleLogger {
  protected getTimestamp() {
    return new Date().toISOString();
  }
}
```

```bash
[Nest] 19096  - 2026-09-28T06:46:17.869Z     LOG [NestFactory] Starting Nest application...
```

Điều này chỉ áp dụng cho output dạng text. Với [log JSON](#json-logging), trường `timestamp` luôn là số mili giây kể từ Unix epoch.

Bạn có thể dùng logger kế thừa như vậy trong các feature module như mô tả trong phần <a href="application/logger#using-the-logger-for-application-logging">Dùng logger để log ứng dụng</a> ở trên.

Bạn có thể bảo Nest dùng logger kế thừa của bạn cho log hệ thống bằng cách truyền một instance của nó qua thuộc tính `logger` của object tùy chọn ứng dụng (như trong phần <a href="application/logger#custom-implementation">Implement tùy chỉnh</a> ở trên), hoặc bằng kỹ thuật trong phần <a href="application/logger#dependency-injection">Dependency injection</a> bên dưới. Nếu làm vậy, hãy gọi `super` như trong code mẫu ở trên để chuyển lời gọi method log cho class cha (có sẵn), để Nest có thể dựa vào các tính năng có sẵn mà nó cần.

<app-banner-courses></app-banner-courses>
#### Dependency injection

Để có chức năng log nâng cao hơn, hãy tận dụng dependency injection. Ví dụ, có thể bạn muốn inject một `ConfigService` vào logger để tùy biến nó, rồi lại inject custom logger đó vào các controller và/hoặc provider khác. Để bật dependency injection cho custom logger, hãy tạo một class implement `LoggerService` và đăng ký class đó làm provider trong một module. Ví dụ, bạn có thể:

1. Định nghĩa class `MyLogger` kế thừa `ConsoleLogger` có sẵn hoặc ghi đè hoàn toàn nó, như trong các phần trước. Nhớ implement interface `LoggerService`.
2. Tạo một `LoggerModule` như bên dưới, và cung cấp `MyLogger` từ module đó.

```typescript
import { Module } from '@nestjs/common';
import { MyLogger } from './my-logger.service.js';

@Module({
  providers: [MyLogger],
  exports: [MyLogger],
})
export class LoggerModule {}
```

Với cách khai báo này, custom logger của bạn có sẵn cho mọi module khác. Vì class `MyLogger` là một phần của module, nó có thể dùng dependency injection (ví dụ để inject `ConfigService`). Cần thêm một bước nữa để Nest dùng custom logger này cho log hệ thống (ví dụ trong lúc bootstrap và xử lý lỗi).

Vì việc khởi tạo ứng dụng (`NestFactory.create()`) diễn ra bên ngoài context của mọi module, nó không tham gia vào giai đoạn dependency injection thông thường của quá trình khởi tạo. Vì vậy bạn phải đảm bảo có ít nhất một module của ứng dụng import `LoggerModule`, để Nest khởi tạo một instance singleton của class `MyLogger`.

Sau đó bạn có thể bảo Nest dùng chính instance singleton đó của `MyLogger` bằng cách sau:

```typescript
const app = await NestFactory.create(AppModule, {
  bufferLogs: true,
});
app.useLogger(app.get(MyLogger));
await app.listen(process.env.PORT ?? 3000);
```

> info **Lưu ý** Trong ví dụ trên, `bufferLogs` được đặt thành `true` để mọi log được giữ trong buffer cho đến khi một custom logger (ở đây là `MyLogger`) được gắn vào. Khi bật `autoFlushLogs` (mặc định), Nest tự flush buffer: một ứng dụng HTTP (hoặc microservice) flush khi nó bắt đầu lắng nghe trong `app.listen()`, còn một [application context](/standalone-applications) standalone flush khi bạn gọi `app.useLogger()`. Nếu khởi tạo thất bại, Nest sẽ flush ngay lập tức. Khi Nest không tạo được một provider (ví dụ do factory của nó throw), nó quay về dùng `ConsoleLogger` gốc để in buffer và lỗi. Khi một lifecycle hook như `onModuleInit()` reject, Nest in buffer qua logger bạn đã gắn (hoặc qua logger gốc, nếu chưa gắn cái nào) nhưng không log lỗi: lời gọi đã khởi động quá trình khởi tạo, như `app.listen()`, sẽ reject với lỗi đó. Đặt `autoFlushLogs` thành `false` để tự flush buffer bằng `app.flushLogs()` (hoặc method static `Logger.flush()`).

Ở đây, method `get()` của instance `NestApplication` lấy ra instance singleton của `MyLogger`. Kỹ thuật này về cơ bản là một cách "inject" instance logger để Nest sử dụng. Lời gọi `app.get()` phụ thuộc vào việc instance đó đã được khởi tạo trước thông qua việc import module, như mô tả ở trên.

Bạn cũng có thể inject provider `MyLogger` này vào các class tính năng, đảm bảo hành vi log nhất quán giữa log hệ thống của Nest và log của ứng dụng. Xem <a href="application/logger#using-the-logger-for-application-logging">Dùng logger để log ứng dụng</a> và <a href="application/logger#injecting-a-custom-logger">Inject custom logger</a> bên dưới để biết thêm thông tin.

> warning **Cảnh báo** Nếu một provider factory hoặc lifecycle hook tự gọi `process.exit()` (ví dụ sau khi kiểm tra kết nối thất bại), hoặc một bước khởi động không bao giờ kết thúc (như một kết nối cứ retry mãi), sẽ không có gì trong buffer được in ra, kể cả khi bạn dừng process bằng `Ctrl+C`. Hãy throw lỗi thay vào đó, để quá trình khởi tạo thất bại và Nest flush buffer.

Khi log lúc khởi động cần luôn hiển thị, kể cả khi process thoát hoặc bị treo, đừng buffer chúng: hãy truyền một instance logger vào tùy chọn `logger` của `NestFactory.create()`, như trong [Implement tùy chỉnh](#custom-implementation), để Nest chuyển từng dòng cho nó ngay khi được log. Instance đó được tạo bên ngoài hệ thống dependency injection, nên nó không thể inject các provider như `ConfigService`.

#### Inject custom logger <a id="injecting-a-custom-logger"></a>

Để bắt đầu, hãy kế thừa logger có sẵn bằng code như sau. Tùy chọn `scope`, được cung cấp làm metadata cấu hình cho class con của `ConsoleLogger`, chỉ định scope [transient](/fundamentals/injection-scopes) để mỗi nơi sử dụng có instance logger riêng. Điều này quan trọng vì mỗi module đặt một context riêng cho logger của mình qua `setContext()` — với singleton, lời gọi đó sẽ ghi đè context trên toàn bộ app. Trong ví dụ này, ta không kế thừa các method riêng lẻ của `ConsoleLogger` (như `log()`, `warn()`, v.v.), dù bạn hoàn toàn có thể làm vậy.

```typescript
import { Injectable, Scope, ConsoleLogger } from '@nestjs/common';

@Injectable({ scope: Scope.TRANSIENT })
export class MyLogger extends ConsoleLogger {
  customLog() {
    this.log('Please feed the cat!');
  }
}
```

Tiếp theo, tạo một `LoggerModule` với cách khai báo như sau:

```typescript
import { Module } from '@nestjs/common';
import { MyLogger } from './my-logger.service.js';

@Module({
  providers: [MyLogger],
  exports: [MyLogger],
})
export class LoggerModule {}
```

Tiếp theo, import `LoggerModule` vào feature module của bạn. Vì `MyLogger` kế thừa `ConsoleLogger`, bạn có thể dùng method `setContext()` của nó và bắt đầu dùng custom logger có nhận biết context, như sau:

```typescript
import { Injectable } from '@nestjs/common';
import { MyLogger } from './my-logger.service.js';

@Injectable()
export class CatsService {
  private readonly cats: Cat[] = [];

  constructor(private myLogger: MyLogger) {
    // Due to transient scope, CatsService has its own unique instance of MyLogger,
    // so setting context here will not affect other instances in other services
    this.myLogger.setContext('CatsService');
  }

  findAll(): Cat[] {
    // You can call all the default methods
    this.myLogger.warn('About to return cats!');
    // And your custom methods
    this.myLogger.customLog();
    return this.cats;
  }
}
```

`MyLogger` cũng thừa hưởng phần còn lại của API `ConsoleLogger`: `resetContext()` khôi phục context đã truyền vào constructor, và `isLevelEnabled('debug')` cho biết một level hiện có đang được bật hay không, để bạn có thể bỏ qua việc chuẩn bị dữ liệu cho một dòng log sẽ bị loại bỏ.

Cuối cùng, bảo Nest dùng một instance của custom logger trong file `main.ts`, như bên dưới. Ví dụ này không tùy biến hành vi của logger (bằng cách ghi đè các method của `ConsoleLogger` như `log()`, `warn()`, v.v.), nên ở đây bước này không thực sự cần thiết. Nó **là** cần thiết nếu bạn thêm logic tùy chỉnh vào các method đó và muốn Nest dùng cùng bản implement đó.

```typescript
const app = await NestFactory.create(AppModule, {
  bufferLogs: true,
});
app.useLogger(new MyLogger());
await app.listen(process.env.PORT ?? 3000);
```

> info **Gợi ý** Ngoài ra, thay vì đặt `bufferLogs` thành `true`, bạn có thể tạm thời tắt logger bằng tùy chọn `logger: false`. Lưu ý rằng nếu bạn truyền `logger: false` vào `NestFactory.create()`, sẽ không có gì được log cho đến khi bạn gọi `useLogger()`, nên bạn có thể bỏ lỡ những lỗi khởi tạo quan trọng. Nếu bạn không ngại một số message ban đầu được log bằng logger mặc định, hãy bỏ tùy chọn `logger: false`.

#### Liên kết log với request <a id="correlating-logs-with-requests"></a>

Tập trung log về một chỗ giải quyết được chuyện lưu trữ, chứ chưa giải quyết được chuyện điều tra. Khi mọi instance đều đổ log về cùng một nơi, phần khó lại trở thành việc dựng lại *một* request duy nhất từ hàng nghìn dòng log đan xen nhau. Đó là lý do rất nhiều công sức debug trên production thực chất là tự nghĩ ra một correlation id, truyền nó qua từng lời gọi log, và cầu mong không có chỗ nào trên đường đi quên truyền tiếp.

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') loại bỏ công việc ghi chép đó. Bật `forwardLogs` và mọi dòng log ghi qua `Logger` của Nest sẽ được ghi lại cùng với trace nơi nó được ghi ra:

```typescript
ObserveModule.forRoot({
  serviceId: 'orders-api',
  forwardLogs: true,
});
```

Bạn vẫn gọi `this.logger.log()` với param `orderId` y như trước: không cần sinh correlation id, không cần truyền context object qua tầng service. Trên trang execution, các log của đúng request đó được đặt lên dòng thời gian của chính trace, mỗi dòng nằm cạnh span đang chạy khi nó được ghi, nên chuyện "cảnh báo retry bắn ra *trước* timeout, không phải sau" là thứ bạn nhìn thấy được thay vì phải tự suy luận từ timestamp trên ba luồng log khác nhau.

Structured logging params cũng được giữ nguyên, nên `orderId` vẫn là một trường truy vấn được thay vì bị gộp vào nội dung message. Bản thân các dòng log cũng đặt cảnh báo được, ví dụ: "báo cho tôi khi `payment declined` xuất hiện quá 10 lần trong 15 phút".

Nếu bạn muốn giữ nội dung log trong hệ thống tổng hợp log của riêng mình, bạn không cần chuyển tiếp gì cả. Kể cả khi tắt `forwardLogs`, SDK vẫn bổ sung cho `ConsoleLogger` để mọi dòng ghi trong một request mang theo trace id của request đó: ở cuối dòng với định dạng mặc định (`   Trace ID: <id>`, sau message), và dưới dạng trường `traceId` khi bật [log JSON](#json-logging):

```json
{"level":"log","pid":66803,"timestamp":1789978166281,"message":"Payment captured","context":"OrdersService","traceId":"0199a3f2-7c1e-7b40-9d2a-5e8f1c3b7a64"}
```

Id đó là đủ để nhảy từ một dòng log trong hệ thống hiện tại của bạn tới toàn bộ trace trên dashboard. Tính năng này bật mặc định và được điều khiển bằng tùy chọn `attachTraceIdToLogs` (xem [Liên kết trace](/observability/sdk#trace-correlation)). Các dòng được ghi bên ngoài request (ví dụ trong lúc bootstrap) được giữ nguyên. Việc bổ sung này chỉ áp dụng cho `ConsoleLogger` có sẵn của Nest, nên nếu bạn thay nó bằng một [logger bên ngoài](#use-external-logger), hãy tự đọc id bằng `TracerService.currentTraceId()`. Xem [tài liệu tham khảo SDK](/observability/sdk#logs) về việc chuyển tiếp log và các thiết lập che giấu dữ liệu.

Trace id không phải thứ duy nhất tồn tại suốt một request. SDK duy trì một store `AsyncLocalStorage` cho mọi request, job và message mà nó instrument, và `TracerService` cung cấp store đó qua `setAttribute()` và `getAttribute()`. Đó là nơi tự nhiên để lưu người dùng hay tenant mà một request đang đại diện, đọc được từ bất cứ đâu phía sau mà không cần truyền qua từng lời gọi. Xem [Thuộc tính theo request](/observability/manual-instrumentation#request-scoped-attributes), và recipe [Async local storage](/recipes/async-local-storage) để so sánh với một store do bạn tự thiết lập.

#### Dùng logger bên ngoài <a id="use-external-logger"></a>

Như phần [Log trên production](#logging-in-production) đã cho thấy, logger có sẵn đã đáp ứng được việc log có cấu trúc, tập trung cho hầu hết ứng dụng. Một số yêu cầu vẫn cần đến library chuyên dụng như [Pino](https://github.com/pinojs/pino) hoặc [Winston](https://github.com/winstonjs/winston): nhiều transport bên trong process (file, syslog, HTTP), che giấu các trường nhạy cảm, serializer tùy chỉnh, hoặc overhead thấp nhất có thể cho các service log với khối lượng cực lớn. Giống như với mọi ứng dụng Node.js chuẩn, bạn có thể tận dụng tối đa các module như vậy trong Nest: implement interface `LoggerService` như mô tả trong [Implement tùy chỉnh](#custom-implementation), hoặc dùng một bản tích hợp của cộng đồng.
