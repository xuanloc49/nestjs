#### Định hình những gì được ghi lại

Các tùy chọn này làm phong phú những gì SDK ghi lại (request dành cho ai, liên quan tới cái gì) và loại bỏ những gì bạn không cần.

##### Gắn người dùng với dữ liệu telemetry

`getUserId` đọc request gửi đến và trả về bất kỳ định danh nào mà hệ thống của bạn dùng cho một người: user id, account id, hoặc một id theo phạm vi tenant. Đặt nó một lần và view **Users** sẽ tự động có dữ liệu:

[[CODE:19]]

Cùng tùy chọn đó có trên `rpc` (nhận transport id và `BaseRpcContext`), `grpc` (nhận call object), `graphql` (nhận GraphQL context, cho các operation không nằm trong HTTP request nào), và `ws` (nhận message của gateway), mỗi cái đọc context riêng của transport thay vì một HTTP request. Việc báo cáo định danh người dùng là tùy chọn: traffic không có định danh vẫn hiện ở mọi nơi ngoại trừ các view theo người dùng. Dashboard xem định danh như một chuỗi opaque và không bao giờ cố resolve nó thành tên hay email, nên hãy ưu tiên dùng một id nội bộ opaque thay vì bất cứ thứ gì định danh cá nhân.

##### Tag và thuộc tính tùy chỉnh

`http`, `rpc`, `grpc`, `graphql` và `jobs` đều nhận cùng hai tùy chọn để gắn dữ liệu của riêng bạn vào mọi request mà chúng bao phủ:

| Tùy chọn        | Áp dụng                                                       | Mô tả                                                                                                    |
| --------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `tags`          | Cùng một `Record<string, string>` tĩnh cho mọi request        | Được gửi lên Observe. Dành cho các hằng số không thay đổi theo lời gọi, ví dụ `project`, `env`, `region`. |
| `setAttributes` | Một hàm nhận request/call/job, trả về các cặp key-value       | Giữ lại trong ứng dụng của bạn. Dành cho ngữ cảnh theo lời gọi mà code của bạn đọc sau đó, ví dụ tenant id, feature flag. |

[[CODE:20]]

`tags` xuất hiện dưới dạng tag trên request hoặc job tương ứng, có thể tìm kiếm và hiển thị trên trang chi tiết của nó.

Các giá trị của `setAttributes` **không được gửi lên Observe** và không xuất hiện trên dashboard. Khi mỗi lời gọi bắt đầu, chúng được ghi vào [thuộc tính theo request](/observability/manual-instrumentation#request-scoped-attributes) của lời gọi đó, giống như tự gọi `setAttribute()` cho từng key, nên bất kỳ code nào xử lý lời gọi đó đều có thể đọc chúng bằng `getAttribute()`. Hàm nhận bất cứ thứ gì transport có: request với `http`, transport id và `BaseRpcContext` với `rpc`, call object với `grpc`, resolve info và GraphQL context với `graphql`, và `{{ '{' }} queueName, name, id {{ '}' }}` với `jobs`.

Để thấy một giá trị theo lời gọi trên dashboard, hãy thêm nó làm tag trên một span bằng `TracerService` (xem [Instrumentation thủ công](/observability/manual-instrumentation)):

[[CODE:21]]

> info **Hint** Một GraphQL server thường là một HTTP endpoint, nên request của nó vốn đã chịu tác động của tùy chọn `http`: `http.ignore` bỏ một request trước khi tầng GraphQL thấy nó, còn `http.getUserId` cung cấp người dùng cho các query qua HTTP. Khối `graphql` tinh chỉnh những gì xảy ra _bên trong_ một request đã được cho qua, theo từng operation chứ không phải theo từng resolver, và `graphql.getUserId` chỉ được hỏi đến với những operation chưa nằm trong một HTTP trace, như subscription qua WebSocket.

##### Bỏ qua các operation ồn ào

Mỗi khối transport đầu vào (`http`, `rpc`, `grpc`, `graphql` và `ws`) có một tùy chọn `ignore` bỏ hoàn toàn việc instrument cho những lời gọi khớp điều kiện, như một health check endpoint, một probe nội bộ, hay bất cứ thứ gì không đáng để trace:

[[CODE:22]]

`http.ignore` nhận một mảng path, các cặp `{{ '{' }} method, path {{ '}' }}` (`path` có thể là chuỗi hoặc `RegExp`), và các `RegExp` thông thường, hoặc một predicate duy nhất trên request. `rpc.ignore`, `grpc.ignore` và `graphql.ignore` là các predicate trên context riêng của transport (lần lượt là transport id và `BaseRpcContext` của `@nestjs/microservices`, call object của gRPC, và resolve info của GraphQL). Khớp tên một trường GraphQL sẽ bỏ qua toàn bộ operation mà trường đó dẫn đầu, không chỉ riêng trường đó: một operation được đo từ đầu đến cuối, nên hoặc nó được trace, hoặc không.

`ignore` ngăn dữ liệu telemetry được tạo ra ngay từ đầu. Bộ lọc loại bỏ trong phần kiểm soát chi tiêu của dashboard là một công cụ khác: chúng loại bỏ các event đã được tạo ra ngay lúc tiếp nhận để giảm khối lượng tính phí. Hãy dùng `ignore` khi bạn không muốn một trace tồn tại, và dùng bộ lọc loại bỏ khi bạn muốn tinh chỉnh chi phí trên dữ liệu mà SDK đã đang tạo ra.

`http` còn nhận `queryParamsObfuscateRegex`, một `RegExp` che các giá trị query string nhạy cảm trước khi chúng được gửi đi. Nó được áp dụng thêm bên trên cơ chế che giấu có sẵn, cơ chế này luôn che các tham số nhạy cảm phổ biến (`token`, `password`, `code`, `signature`, v.v.).

##### Lấy mẫu trace và gom lô

[[CODE:23]]

| Tùy chọn            | Type                                                                       | Mặc định | Mô tả                                                                                                     |
| ------------------- | -------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------- |
| `tracesSampleRate`  | `number \| ((protocol: 'http' \| 'rpc' \| 'grpc' \| 'graphql' \| 'ws', attributes) => boolean)` | `1.0`    | Tỉ lệ trace được gửi đi, hoặc một predicate để quyết định theo từng trace. `0` được tính như chưa đặt và sẽ gửi tất cả; truyền `() => false` để không gửi gì. `1.0` gửi tất cả; `0.1` gửi 10%. |
| `maxTracesPerBatch` | `number`                                                                   | `1000`   | Giới hạn số trace gửi đi mỗi lô, để kiểm soát khối lượng với các ứng dụng traffic cao.                    |
| `flushInterval`     | `number` (ms)                                                              | `5000`   | Tần suất SDK gom lô và gửi các trace đã thu thập.                                                         |

Dữ liệu telemetry được buffer trong process và được gửi đi theo chu kỳ flush thay vì gửi ngay cùng mỗi request. Việc lấy mẫu ở đây quyết định những gì SDK _tạo ra_. Phần kiểm soát chi tiêu theo project của dashboard (lấy mẫu span, giới hạn tốc độ, bộ lọc loại bỏ) tác động lên những gì nó đã gửi, và bạn có thể thay đổi chúng mà không cần deploy lại.

#### Khai báo mục tiêu trong code

`@Objective()` nêu ra những gì một route cam kết, ngay cạnh handler phải giữ cam kết đó, và Observe biến mỗi cam kết thành một [SLO](/observability/dashboard#slos). Mục tiêu được viết, review và đánh version cùng với route mà nó bao phủ, trong cùng một lần thay đổi:

[[CODE:24]]

| Tùy chọn       | Nó cam kết điều gì                                                                       |
| -------------- | ---------------------------------------------------------------------------------------- |
| `availability` | Tỉ lệ phần trăm request không thất bại vì lỗi chưa được xử lý - `99.9` cho ba số chín.   |
| `latency`      | `{{ '{' }} underMs, target {{ '}' }}`: `target` phần trăm request hoàn tất trong dưới `underMs` mili giây. |
| `windowDays`   | Khoảng thời gian trượt dùng để đánh giá: 7, 14, 28 (mặc định), hoặc 30 ngày.             |
| `name`         | Tên mà dashboard dùng để gọi nó, thay cho route và cam kết.                              |

Mục tiêu nằm trong khoảng từ 90 tới 99.999, và một handler có thể mang tối đa mười `@Objective()`; bất cứ thứ gì nằm ngoài các giới hạn đó sẽ được log và bị bỏ qua khi ứng dụng khởi động. Mỗi cam kết trở thành một SLO riêng, có phạm vi theo ứng dụng và route mà handler phục vụ, và xuất hiện khi route đã có traffic. Từ đó trở đi, code là chủ của nó: đổi một mục tiêu, một khoảng thời gian hay một cái tên rồi deploy, và cùng SLO đó sẽ thay đổi theo. Dashboard đánh dấu một SLO được khai báo là **in code** và không chỉnh sửa nó, và việc xóa nó ở đó sẽ không có tác dụng lâu dài khi decorator vẫn còn, vì SDK khai báo lại các mục tiêu của mỗi route mỗi giờ. Để bỏ một SLO, hãy xóa decorator, rồi xóa SLO. SLO cần một gói có hỗ trợ (Scale hoặc Enterprise); trên các gói khác, các khai báo được gửi đi nhưng bị bỏ qua.

#### Tham khảo cấu hình đầy đủ

Toàn bộ tùy chọn trong một bảng. Các tùy chọn liệt kê dưới `createObserveModule()` phải được đặt ở đó; mọi thứ khác đặt trong `forRoot()`/`forRootAsync()`.

| Vị trí                  | Tùy chọn                              | Mục đích                                                                  |
| ----------------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `createObserveModule()` | `sourceContext`                       | Đính kèm các dòng mã nguồn vào stack frame của lỗi                        |
| `createObserveModule()` | `traceIdKey`                          | Key trong context dùng để lưu trace id                                    |
| `createObserveModule()` | `traceIdGenerator`                    | Cách mỗi request nhận được trace id                                       |
| `createObserveModule()` | `attachTraceIdToLogs`                 | Thêm trace id vào output của `ConsoleLogger`                              |
| `createObserveModule()` | `skipInstrumentation`                 | Predicate loại các instance provider khỏi việc instrument                 |
| `forRoot()`             | `appKey`, `appSecret`                 | Cặp API key của project (hoặc `OBSERVE_APP_KEY`, `OBSERVE_APP_SECRET`)    |
| `forRoot()`             | `endpoint`                            | URL gốc của collector (hoặc `OBSERVE_ENDPOINT`)                           |
| `forRoot()`             | `enabled`                             | `false` không ghi lại và không gửi gì, dành cho development và CI         |
| `forRoot()`             | `serviceId`, `serviceVersion`         | Định danh ứng dụng và release (release được suy ra khi chưa đặt)          |
| `forRoot()`             | `http`, `rpc`, `grpc`, `graphql`      | `tags`, `setAttributes`, `getUserId`, `ignore` theo từng transport        |
| `forRoot()`             | `jobs`                                | `tags` và `setAttributes` cho queue job và job theo lịch                  |
| `forRoot()`             | `http.queryParamsObfuscateRegex`      | Che các giá trị query string nhạy cảm                                     |
| `forRoot()`             | `http.capture`                        | Header (và tùy chọn là body) được ghi lại với request thất bại và chậm    |
| `forRoot()`             | `outgoing`                            | Span cho query database và HTTP gửi ra ngoài; `outgoing.llm` cho lời gọi model |
| `forRoot()`             | `openTelemetry`                       | `traceparent` W3C vào và ra, cạnh một SDK OpenTelemetry                   |
| `forRoot()`             | `otlp`                                | Export span qua OTLP tới backend OpenTelemetry của bạn                    |
| `forRoot()`             | `ws`                                  | `tags`, `setAttributes`, `getUserId`, `ignore` cho WebSocket gateway      |
| `forRoot()`             | `runtimeMetrics`, `runtimeMetricsInterval` | Mẫu của Profiler và heartbeat                                        |
| `forRoot()`             | `forwardLogs`, `redaction`            | Stream log và làm sạch dữ liệu                                            |
| `forRoot()`             | `tracesSampleRate`                    | Tỉ lệ (hoặc predicate) trace được gửi đi                                  |
| `forRoot()`             | `maxTracesPerBatch`, `flushInterval`  | Gom lô                                                                    |
| `forRoot()`             | `spanCollapse`                        | Gộp các span anh em lặp lại (ngưỡng mặc định `20`, giữ lại `3` cái chậm nhất) |
| `forRoot()`             | `shutdownFlushTimeout`                | Thời gian việc đóng ứng dụng chờ lần gửi cuối cùng (mặc định `2000` ms)   |
| `forRoot()`             | `debug`                               | Chẩn đoán SDK                                                             |

#### Đọc tiếp

- [Instrumentation thủ công](/observability/manual-instrumentation) - thêm span của riêng bạn, ghi lại các lỗi đã xử lý, gắn thuộc tính theo request, và báo cáo custom metric.
- [Distributed tracing](/observability/distributed-tracing) - giữ một trace duy nhất xuyên qua HTTP, gRPC, các transport microservice và GraphQL.
- [Dashboard](/observability/dashboard) - những gì hiện lên khi SDK đã chạy, và các view liên quan tới nhau như thế nào.
