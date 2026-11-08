#### Dependency injection

Để có chức năng log nâng cao hơn, hãy tận dụng dependency injection. Ví dụ, có thể bạn muốn inject một `ConfigService` vào logger để tùy biến nó, rồi lại inject custom logger đó vào các controller và/hoặc provider khác. Để bật dependency injection cho custom logger, hãy tạo một class implement `LoggerService` và đăng ký class đó làm provider trong một module. Ví dụ, bạn có thể:

1. Định nghĩa class `MyLogger` kế thừa `ConsoleLogger` có sẵn hoặc ghi đè hoàn toàn nó, như trong các phần trước. Nhớ implement interface `LoggerService`.
2. Tạo một `LoggerModule` như bên dưới, và cung cấp `MyLogger` từ module đó.

[[CODE:30]]

Với cách khai báo này, custom logger của bạn có sẵn cho mọi module khác. Vì class `MyLogger` là một phần của module, nó có thể dùng dependency injection (ví dụ để inject `ConfigService`). Cần thêm một bước nữa để Nest dùng custom logger này cho log hệ thống (ví dụ trong lúc bootstrap và xử lý lỗi).

Vì việc khởi tạo ứng dụng (`NestFactory.create()`) diễn ra bên ngoài context của mọi module, nó không tham gia vào giai đoạn dependency injection thông thường của quá trình khởi tạo. Vì vậy bạn phải đảm bảo có ít nhất một module của ứng dụng import `LoggerModule`, để Nest khởi tạo một instance singleton của class `MyLogger`.

Sau đó bạn có thể bảo Nest dùng chính instance singleton đó của `MyLogger` bằng cách sau:

[[CODE:31]]

> info **Note** Trong ví dụ trên, `bufferLogs` được đặt thành `true` để mọi log được giữ trong buffer cho đến khi một custom logger (ở đây là `MyLogger`) được gắn vào. Khi bật `autoFlushLogs` (mặc định), Nest tự flush buffer: một ứng dụng HTTP (hoặc microservice) flush khi nó bắt đầu lắng nghe trong `app.listen()`, còn một [application context](/standalone-applications) standalone flush khi bạn gọi `app.useLogger()`. Nếu khởi tạo thất bại, Nest sẽ flush ngay lập tức. Khi Nest không tạo được một provider (ví dụ do factory của nó throw), nó quay về dùng `ConsoleLogger` gốc để in buffer và lỗi. Khi một lifecycle hook như `onModuleInit()` reject, Nest in buffer qua logger bạn đã gắn (hoặc qua logger gốc, nếu chưa gắn cái nào) nhưng không log lỗi: lời gọi đã khởi động quá trình khởi tạo, như `app.listen()`, sẽ reject với lỗi đó. Đặt `autoFlushLogs` thành `false` để tự flush buffer bằng `app.flushLogs()` (hoặc method static `Logger.flush()`).

Ở đây, method `get()` của instance `NestApplication` lấy ra instance singleton của `MyLogger`. Kỹ thuật này về cơ bản là một cách "inject" instance logger để Nest sử dụng. Lời gọi `app.get()` phụ thuộc vào việc instance đó đã được khởi tạo trước thông qua việc import module, như mô tả ở trên.

Bạn cũng có thể inject provider `MyLogger` này vào các class tính năng, đảm bảo hành vi log nhất quán giữa log hệ thống của Nest và log của ứng dụng. Xem <a href="application/logger#using-the-logger-for-application-logging">Dùng logger để log ứng dụng</a> và <a href="application/logger#injecting-a-custom-logger">Inject custom logger</a> bên dưới để biết thêm thông tin.

> warning **Warning** Nếu một provider factory hoặc lifecycle hook tự gọi `process.exit()` (ví dụ sau khi kiểm tra kết nối thất bại), hoặc một bước khởi động không bao giờ kết thúc (như một kết nối cứ retry mãi), sẽ không có gì trong buffer được in ra, kể cả khi bạn dừng process bằng `Ctrl+C`. Hãy throw lỗi thay vào đó, để quá trình khởi tạo thất bại và Nest flush buffer.

Khi log lúc khởi động cần luôn hiển thị, kể cả khi process thoát hoặc bị treo, đừng buffer chúng: hãy truyền một instance logger vào tùy chọn `logger` của `NestFactory.create()`, như trong [Implement tùy chỉnh](#custom-implementation), để Nest chuyển từng dòng cho nó ngay khi được log. Instance đó được tạo bên ngoài hệ thống dependency injection, nên nó không thể inject các provider như `ConfigService`.

#### Inject custom logger

Để bắt đầu, hãy kế thừa logger có sẵn bằng code như sau. Tùy chọn `scope`, được cung cấp làm metadata cấu hình cho class con của `ConsoleLogger`, chỉ định scope [transient](/fundamentals/injection-scopes) để mỗi nơi sử dụng có instance logger riêng. Điều này quan trọng vì mỗi module đặt một context riêng cho logger của mình qua `setContext()` — với singleton, lời gọi đó sẽ ghi đè context trên toàn bộ app. Trong ví dụ này, ta không kế thừa các method riêng lẻ của `ConsoleLogger` (như `log()`, `warn()`, v.v.), dù bạn hoàn toàn có thể làm vậy.

[[CODE:32]]

Tiếp theo, tạo một `LoggerModule` với cách khai báo như sau:

[[CODE:33]]

Tiếp theo, import `LoggerModule` vào feature module của bạn. Vì `MyLogger` kế thừa `ConsoleLogger`, bạn có thể dùng method `setContext()` của nó và bắt đầu dùng custom logger có nhận biết context, như sau:

[[CODE:34]]

`MyLogger` cũng thừa hưởng phần còn lại của API `ConsoleLogger`: `resetContext()` khôi phục context đã truyền vào constructor, và `isLevelEnabled('debug')` cho biết một level hiện có đang được bật hay không, để bạn có thể bỏ qua việc chuẩn bị dữ liệu cho một dòng log sẽ bị loại bỏ.

Cuối cùng, bảo Nest dùng một instance của custom logger trong file `main.ts`, như bên dưới. Ví dụ này không tùy biến hành vi của logger (bằng cách ghi đè các method của `ConsoleLogger` như `log()`, `warn()`, v.v.), nên ở đây bước này không thực sự cần thiết. Nó **là** cần thiết nếu bạn thêm logic tùy chỉnh vào các method đó và muốn Nest dùng cùng bản implement đó.

[[CODE:35]]

> info **Hint** Ngoài ra, thay vì đặt `bufferLogs` thành `true`, bạn có thể tạm thời tắt logger bằng tùy chọn `logger: false`. Lưu ý rằng nếu bạn truyền `logger: false` vào `NestFactory.create()`, sẽ không có gì được log cho đến khi bạn gọi `useLogger()`, nên bạn có thể bỏ lỡ những lỗi khởi tạo quan trọng. Nếu bạn không ngại một số message ban đầu được log bằng logger mặc định, hãy bỏ tùy chọn `logger: false`.

#### Liên kết log với request

Tập trung log về một chỗ giải quyết được chuyện lưu trữ, chứ chưa giải quyết được chuyện điều tra. Khi mọi instance đều đổ log về cùng một nơi, phần khó lại trở thành việc dựng lại *một* request duy nhất từ hàng nghìn dòng log đan xen nhau. Đó là lý do rất nhiều công sức debug trên production thực chất là tự nghĩ ra một correlation id, truyền nó qua từng lời gọi log, và cầu mong không có chỗ nào trên đường đi quên truyền tiếp.

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') loại bỏ công việc ghi chép đó. Bật `forwardLogs` và mọi dòng log ghi qua `Logger` của Nest sẽ được ghi lại cùng với trace nơi nó được ghi ra:

[[CODE:36]]

Bạn vẫn gọi `this.logger.log()` với param `orderId` y như trước: không cần sinh correlation id, không cần truyền context object qua tầng service. Trên trang execution, các log của đúng request đó được đặt lên dòng thời gian của chính trace, mỗi dòng nằm cạnh span đang chạy khi nó được ghi, nên chuyện "cảnh báo retry bắn ra *trước* timeout, không phải sau" là thứ bạn nhìn thấy được thay vì phải tự suy luận từ timestamp trên ba luồng log khác nhau.

Structured logging params cũng được giữ nguyên, nên `orderId` vẫn là một trường truy vấn được thay vì bị gộp vào nội dung message. Bản thân các dòng log cũng đặt cảnh báo được, ví dụ: "báo cho tôi khi `payment declined` xuất hiện quá 10 lần trong 15 phút".

Nếu bạn muốn giữ nội dung log trong hệ thống tổng hợp log của riêng mình, bạn không cần chuyển tiếp gì cả. Kể cả khi tắt `forwardLogs`, SDK vẫn bổ sung cho `ConsoleLogger` để mọi dòng ghi trong một request mang theo trace id của request đó: ở cuối dòng với định dạng mặc định (`   Trace ID: <id>`, sau message), và dưới dạng trường `traceId` khi bật [log JSON](#json-logging):

[[CODE:37]]

Id đó là đủ để nhảy từ một dòng log trong hệ thống hiện tại của bạn tới toàn bộ trace trên dashboard. Tính năng này bật mặc định và được điều khiển bằng tùy chọn `attachTraceIdToLogs` (xem [Liên kết trace](/observability/sdk#trace-correlation)). Các dòng được ghi bên ngoài request (ví dụ trong lúc bootstrap) được giữ nguyên. Việc bổ sung này chỉ áp dụng cho `ConsoleLogger` có sẵn của Nest, nên nếu bạn thay nó bằng một [logger bên ngoài](#use-external-logger), hãy tự đọc id bằng `TracerService.currentTraceId()`. Xem [tài liệu tham khảo SDK](/observability/sdk#logs) về việc chuyển tiếp log và các thiết lập che giấu dữ liệu.

Trace id không phải thứ duy nhất tồn tại suốt một request. SDK duy trì một store `AsyncLocalStorage` cho mọi request, job và message mà nó instrument, và `TracerService` cung cấp store đó qua `setAttribute()` và `getAttribute()`. Đó là nơi tự nhiên để lưu người dùng hay tenant mà một request đang đại diện, đọc được từ bất cứ đâu phía sau mà không cần truyền qua từng lời gọi. Xem [Thuộc tính theo request](/observability/manual-instrumentation#request-scoped-attributes), và recipe [Async local storage](/recipes/async-local-storage) để so sánh với một store do bạn tự thiết lập.

#### Dùng logger bên ngoài

Như phần [Log trên production](#logging-in-production) đã cho thấy, logger có sẵn đã đáp ứng được việc log có cấu trúc, tập trung cho hầu hết ứng dụng. Một số yêu cầu vẫn cần đến library chuyên dụng như [Pino](https://github.com/pinojs/pino) hoặc [Winston](https://github.com/winstonjs/winston): nhiều transport bên trong process (file, syslog, HTTP), che giấu các trường nhạy cảm, serializer tùy chỉnh, hoặc overhead thấp nhất có thể cho các service log với khối lượng cực lớn. Giống như với mọi ứng dụng Node.js chuẩn, bạn có thể tận dụng tối đa các module như vậy trong Nest: implement interface `LoggerService` như mô tả trong [Implement tùy chỉnh](#custom-implementation), hoặc dùng một bản tích hợp của cộng đồng.
