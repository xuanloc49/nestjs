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

#### Tùy biến cơ bản

Để tắt log, đặt thuộc tính `logger` thành `false` trong object tùy chọn ứng dụng Nest (tùy chọn), truyền làm tham số thứ hai cho method `NestFactory.create()`.

[[CODE:1]]

Để bật những log level cụ thể, đặt thuộc tính `logger` thành một mảng chuỗi chỉ định các log level cần hiển thị, như sau:

[[CODE:2]]

Các giá trị trong mảng có thể là bất kỳ tổ hợp nào của `'log'`, `'fatal'`, `'error'`, `'warn'`, `'debug'` và `'verbose'`.

> info **Hint** Log level được kích hoạt theo kiểu bậc thang từ level nghiêm trọng nhất trong mảng: mọi level nghiêm trọng ít nhất bằng level đó cũng được bật. Do đó `['log']` cũng bật luôn `'warn'`, `'error'` và `'fatal'`. Các level ít nghiêm trọng hơn chỉ được bật nếu được liệt kê, nên `['debug', 'error']` bật `'debug'`, `'error'` và `'fatal'`, nhưng không bật `'log'` hay `'warn'`.

Để bật một level và mọi level nghiêm trọng hơn nó, hãy tạo mảng bằng `filterLogLevels()` thay vì liệt kê các level bằng tay. Hàm này nhận một chuỗi, nên rất hợp để dùng với biến môi trường:

[[CODE:3]]

Ngoài `'>=warn'`, nó còn nhận `'>warn'` (chỉ những level nghiêm trọng hơn `warn`), một danh sách phân cách bằng dấu phẩy như `'log,error'`, hoặc một level đơn lẻ. Chuỗi rỗng hoặc không nhận diện được sẽ trả về mọi level, còn một level không xác định đứng sau `>` hoặc `>=` sẽ gây throw.

Để thay đổi các level sau khi ứng dụng đã được tạo (ví dụ khi cấu hình đã load xong), truyền một mảng level vào `app.useLogger()`. Nest sẽ chuyển nó cho method `setLogLevels()` của logger hiện tại:

[[CODE:4]]

Để tắt output có màu, truyền một instance `ConsoleLogger` có thuộc tính `colors` đặt thành `false` làm giá trị của thuộc tính `logger`:

[[CODE:5]]

Màu cũng bị tắt mặc định khi biến môi trường `NO_COLOR` được đặt thành bất kỳ giá trị không rỗng nào.

Để cấu hình prefix cho mỗi log message, truyền một instance `ConsoleLogger` có đặt thuộc tính `prefix`:

[[CODE:6]]

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

#### Log dạng JSON

Log dạng JSON rất quan trọng cho observability của ứng dụng và cho việc tích hợp với các hệ thống quản lý log. Để bật, hãy tạo một instance `ConsoleLogger` với thuộc tính `json` đặt thành `true`, và truyền nó làm giá trị của thuộc tính `logger` khi tạo instance ứng dụng:

[[CODE:7]]

Cấu hình này xuất log ở định dạng JSON có cấu trúc, giúp dễ tích hợp với các hệ thống bên ngoài như hệ thống tổng hợp log và các nền tảng cloud. Ví dụ, những nền tảng như **AWS ECS** (Elastic Container Service) hỗ trợ sẵn log JSON, cho phép các tính năng như:

- **Lọc log**: thu hẹp log dựa trên các trường như log level, timestamp, hoặc metadata tùy chỉnh.
- **Tìm kiếm và phân tích**: dùng các công cụ truy vấn để phân tích và theo dõi xu hướng trong hành vi của ứng dụng.

Nếu bạn đang dùng [NestJS Mau](https://mau.nestjs.com), log JSON cũng giúp bạn xem log ở định dạng có cấu trúc, ngăn nắp, đặc biệt hữu ích cho việc debug và theo dõi hiệu năng.

> info **Note** Khi `json` được đặt thành `true`, `ConsoleLogger` mặc định đặt `colors` thành `false` và `compact` thành `true`. Với hai giá trị này, mỗi mục được serialize bằng `JSON.stringify()`, nên output là JSON hợp lệ, không có ký tự định dạng thừa. Khi phát triển, bạn có thể đặt tường minh `colors` thành `true` (hoặc `compact` thành `false`). Khi đó các mục được render bằng `util.inspect()` của Node, dễ đọc hơn khi debug ở local nhưng không còn là JSON chuẩn.

Khi bật log JSON, output trông như sau (trên một dòng duy nhất):

[[CODE:8]]

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

[[CODE:9]]

Ở chế độ text, params được nối vào ngay trên cùng dòng đã format:

[[CODE:10]]

Khi truyền nhiều object thuần, chúng được merge thành một bộ params duy nhất:

[[CODE:11]]

[[CODE:12]]

Ở chế độ JSON, params mặc định được lồng dưới key `params`:

[[CODE:13]]

Để trải chúng ra ở gốc của object JSON (một số hệ thống tổng hợp log thích kiểu này hơn), hãy bật `flattenParams`:

[[CODE:14]]

[[CODE:15]]

Các tùy chọn liên quan của `ConsoleLogger` là:

| Tùy chọn           | Mô tả                                                                                                         | Mặc định |
| ------------------ | ------------------------------------------------------------------------------------------------------------- | -------- |
| `structuredParams` | Nếu bật, các object thuần được log sau message sẽ được gắn vào cùng mục log dưới dạng params.                 | `true`   |
| `flattenParams`    | Nếu bật, params được trải ra ở gốc của bản ghi JSON thay vì lồng dưới `params`. Param nào có key trùng với key bản ghi đã dùng (như `message` hay `level`) sẽ bị bỏ. Chỉ áp dụng ở chế độ JSON; yêu cầu `structuredParams`. | `false`  |

> info **Hint** Chỉ **object thuần** mới được xem là params. Mảng, chuỗi, số, instance của class và `null` vẫn được log thành các message riêng (một chuỗi truyền làm tham số *cuối cùng* vẫn được xem là context), và một object thuần truyền làm tham số *đầu tiên* vẫn được xem là chính message. Đặt `structuredParams: false` để khôi phục hành vi trước v12.

#### Log trên production

Kết hợp lại, output JSON và structured params cho bạn log đạt chuẩn production chỉ với logger có sẵn:

[[CODE:16]]

[[CODE:17]]

Khi cài [NestJS Observe](#correlating-logs-with-requests), mỗi dòng được ghi trong một request còn mang thêm trace id của request đó, mà không cần sửa bất kỳ lời gọi log nào:

[[CODE:18]]

Chỉ một dòng đó đã lọc được theo level và context, truy vấn được theo `orderId`, và nối được với mọi dòng khác của cùng request, đúng là việc mà hầu hết các team cài logger bên thứ ba để làm. Hãy ghi log ra stdout như thế này và để nền tảng (Docker, Kubernetes, ECS, Cloud Run, v.v.) thu thập và chuyển đi. Cách này giữ việc xoay vòng file, buffer và vận chuyển log nằm ngoài process ứng dụng của bạn.

> info **Hint** Đặt `flattenParams: true` nếu hệ thống tổng hợp log của bạn chỉ đánh index các trường ở cấp cao nhất, để `orderId` trở thành trường ở gốc thay vì `params.orderId`.

#### Dùng logger để log ứng dụng

Bạn có thể kết hợp vài kỹ thuật ở trên để có hành vi và định dạng nhất quán giữa log hệ thống của Nest và log event/message của chính ứng dụng.

Một cách làm tốt là khởi tạo class `Logger` từ `@nestjs/common` trong mỗi service, truyền tên service làm tham số `context` cho constructor của `Logger`:

[[CODE:19]]

Trong bản implement logger mặc định, `context` được in trong dấu ngoặc vuông, như `NestFactory` trong ví dụ dưới đây:

[[CODE:20]]

Nếu một message tốn kém để tạo ra, hãy truyền vào một hàm trả về message đó. Ở định dạng text mặc định, `ConsoleLogger` có sẵn chỉ gọi hàm khi level đó được bật, nên một dòng `debug` bị tắt sẽ không tốn gì cả:

[[CODE:21]]

Nếu bạn cung cấp một custom logger qua `app.useLogger()`, Nest sẽ dùng nó bên trong, và các lời gọi qua instance `Logger` đều được chuyển cho nó. Code của bạn vẫn không phụ thuộc vào bản implement cụ thể, và bạn có thể thay logger mặc định bằng logger của riêng mình chỉ bằng cách gọi `app.useLogger()`.

Ví dụ, nếu bạn làm theo các bước trong phần <a href="application/logger#dependency-injection">Dependency injection</a> bên dưới và gọi `app.useLogger(app.get(MyLogger))`, các lời gọi `this.logger.log()` sau đó từ `MyService` sẽ dẫn tới việc gọi method `log()` của instance `MyLogger`.

Cách này phù hợp với hầu hết trường hợp. Nếu bạn cần tùy biến nhiều hơn (như thêm và gọi các method tùy chỉnh), xem phần <a href="application/logger#injecting-a-custom-logger">Inject custom logger</a>.

#### Log kèm timestamp

Để in khoảng chênh lệch timestamp cho mỗi message được log, truyền thiết lập tùy chọn `timestamp: true` khi tạo instance logger:

[[CODE:22]]

Kết quả sẽ có định dạng như sau:

[[CODE:23]]

Để ý `+5ms` ở cuối dòng. Đó là thời gian trôi qua kể từ dòng trước đó được ghi bởi bất kỳ `ConsoleLogger` nào trong process, không chỉ bởi logger này.

#### Implement tùy chỉnh

Bạn có thể cung cấp một bản implement logger tùy chỉnh để Nest dùng cho log hệ thống, bằng cách đặt thuộc tính `logger` thành một object thỏa mãn interface `LoggerService`. Ví dụ, bạn có thể bảo Nest dùng object JavaScript toàn cục `console` (object này implement interface `LoggerService`), như sau:

[[CODE:24]]

Để implement custom logger của riêng bạn, hãy implement từng method của interface `LoggerService`, như bên dưới:

[[CODE:25]]

Sau đó bạn có thể cung cấp một instance `MyLogger` qua thuộc tính `logger` của object tùy chọn ứng dụng Nest:

[[CODE:26]]

Kỹ thuật này tuy đơn giản nhưng không dùng dependency injection cho class `MyLogger`. Điều này có thể gây khó khăn, đặc biệt là khi test, và hạn chế khả năng tái sử dụng `MyLogger`. Để có giải pháp tốt hơn, xem phần <a href="application/logger#dependency-injection">Dependency injection</a> bên dưới.

#### Kế thừa logger có sẵn

Thay vì viết logger từ đầu, có thể bạn chỉ cần kế thừa class `ConsoleLogger` có sẵn và ghi đè một số hành vi được chọn của bản implement mặc định:

[[CODE:27]]

Cùng cách đó cũng dùng để đổi định dạng timestamp. Ví dụ, để in timestamp theo ISO 8601 thay vì ngày định dạng theo locale, hãy ghi đè method protected `getTimestamp()`:

[[CODE:28]]

[[CODE:29]]

Điều này chỉ áp dụng cho output dạng text. Với [log JSON](#json-logging), trường `timestamp` luôn là số mili giây kể từ Unix epoch.

Bạn có thể dùng logger kế thừa như vậy trong các feature module như mô tả trong phần <a href="application/logger#using-the-logger-for-application-logging">Dùng logger để log ứng dụng</a> ở trên.

Bạn có thể bảo Nest dùng logger kế thừa của bạn cho log hệ thống bằng cách truyền một instance của nó qua thuộc tính `logger` của object tùy chọn ứng dụng (như trong phần <a href="application/logger#custom-implementation">Implement tùy chỉnh</a> ở trên), hoặc bằng kỹ thuật trong phần <a href="application/logger#dependency-injection">Dependency injection</a> bên dưới. Nếu làm vậy, hãy gọi `super` như trong code mẫu ở trên để chuyển lời gọi method log cho class cha (có sẵn), để Nest có thể dựa vào các tính năng có sẵn mà nó cần.

<app-banner-courses></app-banner-courses>
