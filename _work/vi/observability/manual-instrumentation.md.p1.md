### Instrumentation thủ công

Phần lớn SDK là instrument tự động: bạn cấu hình nó một lần và nó tự quyết định cần ghi lại gì. `TracerService` là nửa thủ công. Hãy inject nó ở bất cứ đâu trong ứng dụng để thêm span bên trong một request đang được trace, gắn ngữ cảnh vào request đó, ghi lại các lỗi mà bạn đã tự xử lý, và báo cáo các metric của riêng bạn.

[[CODE:1]]

`ObserveModule.forRoot()` đăng ký một global module export `TracerService`, nên bạn có thể inject nó ở bất kỳ module nào mà không cần import lại `ObserveModule`. (`forRootAsync()` cũng là global, trừ khi bạn truyền `global: false`.) Mọi method đều đọc trace từ async context hiện hành, nên gọi một method bên ngoài request, job hay một operation được instrument khác sẽ throw: không có trace nào để gắn vào. Điều này là có chủ ý, vì một span bị âm thầm bỏ đi khó nhận ra hơn một lỗi. Các ngoại lệ là `currentTraceId()`, method này trả về `null` thay vào đó, và [custom metric](#custom-metrics), vốn không gắn với trace.

#### Tạo span

`createSpan(name, callback)` chạy callback bên trong một span mới lồng dưới span đang hoạt động, và trả về một promise của giá trị mà callback trả về. Thời gian của span chính là thời gian của callback, nên hãy `await` bất cứ thứ gì bạn muốn đo:

[[CODE:2]]

Span lồng nhau theo call stack: một `createSpan()` bên trong callback của một `createSpan()` khác sẽ trở thành con của nó, tạo ra waterfall trên trang chi tiết của trace. Callback có thể đồng bộ hoặc bất đồng bộ. Các span được instrument tự động (method của controller, provider, lời gọi database) và các span tùy chỉnh của bạn dùng chung một cây, nên một span đặt tên bằng tay xuất hiện đúng vị trí nó đã chạy so với mọi thứ khác.

Tham số `span` là một `TraceSpanDelegate`. Method `addTags(tags)` của nó (hoặc `setTag(key, value)` cho một mục duy nhất) gắn các cặp key-value vào riêng span đó. Giống như tùy chọn `tags` mô tả trong [SDK → Tag và thuộc tính tùy chỉnh](/observability/sdk#tags-and-custom-attributes), chúng có thể tìm kiếm và được hiển thị trên span trong view trace. Điểm khác là phạm vi: tùy chọn kia bao phủ mọi request, còn các tag này chỉ bao phủ một span.

`activeSpan()` resolve ra `TraceSpanDelegate` của span đang hoạt động mà không tạo span mới. Hãy dùng nó để gắn tag cho span bao ngoài từ code không tạo ra span đó:

[[CODE:3]]

Nó reject nếu không có span nào đang hoạt động cho trace hiện tại.

<figure><img src="https://www.observe.nestjs.com/docs/sdk/spans.webp" alt="Span" /></figure>

> info **Hint** View phân tích **Spans** tổng hợp theo tên span, trên mọi route gọi tới chúng. Hãy chọn những cái tên mô tả công việc (`orders.recalculate`, `cache.lookup`) thay vì bên gọi, để dashboard có thể cho bạn biết một thứ gì đó chậm ở mọi nơi hay chỉ chậm khi gọi từ một endpoint.

#### Ghi lại lỗi đã xử lý

Các lỗi lan ra khỏi controller, job hoặc span được ghi lại tự động. `captureError()` dành cho những lỗi không lan ra: bất cứ thứ gì bạn đã bắt và xử lý nhưng vẫn muốn thấy trên dashboard:

[[CODE:4]]

Lỗi được gắn vào trace hiện tại, kèm các tag tùy chọn được ghi lại cùng nó, và được xử lý ngữ cảnh mã nguồn giống như mọi lỗi được ghi lại khác nếu [`sourceContext`](/observability/sdk#error-source-context) được bật.

#### Thuộc tính theo request

`setAttribute(key, value)` và `getAttribute(key)` ghi và đọc context store riêng của trace. Các giá trị của nó tồn tại suốt thời gian của request và đọc được từ bất cứ đâu phía sau, mà không cần truyền chúng qua signature của từng hàm:

[[CODE:5]]

`getAttribute()` trả về `undefined` với một key chưa từng được đặt. Cả hai đều throw khi được gọi bên ngoài một context đang được trace.

Trace id nằm trong cùng store đó, nên `getAttribute(traceIdKey)` lấy ra trace id hiện tại, ví dụ để liên kết với một hệ thống bên ngoài hoặc để [truyền nó sang một service khác](/observability/distributed-tracing). `currentTraceId()` là cách viết tắt cho phép tra cứu đó với một khác biệt có chủ ý: nó trả về `null` bên ngoài một context đang được trace thay vì throw, vì việc chuyển tiếp trace id xuống phía sau hoàn toàn có thể xảy ra khi chưa có trace nào.

Để gán type cho store, hãy truyền cấu trúc của nó làm type argument đầu tiên của `TracerService`. Khi đó key và value được kiểm tra theo cấu trúc đó, kể cả các path lồng nhau:

[[CODE:6]]

> info **Hint** `ObserveModule` cũng export instance `AsyncLocalStorage` chứa trace context. `setAttribute()`/`getAttribute()` là cách được hỗ trợ để tiếp cận nó; chỉ inject trực tiếp store khi bạn cần thứ mà chúng không cung cấp. Nếu bạn đã dùng pattern mô tả trong recipe [Async local storage](/recipes/async-local-storage), store này có thể thay thế store bạn tự viết.

#### Custom metric

Có ba loại metric, mỗi loại được tạo theo tên (hoặc lấy ra, nếu tên đã tồn tại). Chúng báo cáo vào phần **Custom** của dashboard, và bạn có thể đặt cảnh báo cho chúng như mọi metric có sẵn.

Khác với các method ở trên, metric không gắn với trace, nên bạn có thể báo cáo chúng từ bất cứ đâu, kể cả code lúc khởi động và tắt ứng dụng, các hook `onModuleInit()`, và cron job.

| Method    | Dành cho                                                                    | Method báo cáo   |
| --------- | --------------------------------------------------------------------------- | ---------------- |
| `counter` | Các giá trị chỉ tăng - số request đã phục vụ, số đơn đã đặt, số lần retry   | `increment()`    |
| `gauge`   | Các giá trị tăng và giảm - độ sâu queue, số kết nối đang mở, tỉ lệ cache    | `increment()`, `decrement()`, `setValue(value)` |
| `summary` | Các phân phối mà bạn muốn tính quantile - độ trễ, kích thước payload        | `observe(value)` |

[[CODE:7]]

Gọi `counter('orders.placed')` hai lần sẽ trả về cùng một instance, nên bạn không cần giữ tham chiếu trong một field, dù làm vậy sẽ rẻ hơn trên một đường code nóng. Truyền thuộc tính ở một lần gọi sau sẽ cập nhật ngay description và label của metric đã có.

| Thuộc tính     | Áp dụng cho             | Mô tả                                                                                                                                 |
| -------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `description`  | counter, gauge, summary | Hiển thị cạnh metric trên dashboard. Đáng để đặt: một tên metric trơn trọi hiếm khi tự giải thích được cho người đọc sau này.          |
| `labels`       | counter, gauge, summary | Các chiều để phân tách metric, để biểu đồ có thể chia nhỏ thay vì chỉ hiện một đường tổng hợp.                                        |
| `initialValue` | counter, gauge          | Giá trị khởi đầu. Chỉ được áp dụng khi metric vẫn còn ở `0`, để một lần khai báo lúc khởi động lại không ghi đè lên giá trị đã đếm.   |
| `kind`         | gauge                   | `'ratio'` (mặc định) cho các giá trị đứng riêng trong mỗi lần báo cáo, hoặc `'additive'` cho các giá trị được cộng dồn giữa các instance báo cáo. |
| `sampleSize`   | summary                 | Số lần quan sát được giữ lại cho mỗi label để tính quantile, giới hạn bộ nhớ của summary khi có tải.                                  |

<figure><img src="https://www.observe.nestjs.com/docs/sdk/custom-metrics.webp" alt="Custom metric" /></figure>

Một metric đã được khai báo nhưng chưa bao giờ được báo cáo sẽ hiển thị là "unknown" thay vì `0` trên dashboard. Đây là một trạng thái thực sự, không phải dữ liệu bị thiếu: "chúng tôi chưa bao giờ nghe gì từ metric này" và "metric này hiện đang bằng không" là hai sự thật khác nhau, và hiển thị cái sau thay cho cái trước sẽ che giấu một lần deploy bị hỏng.

#### Tóm tắt API

| Method                            | Cần trace | Mô tả                                                               |
| --------------------------------- | :-------: | ------------------------------------------------------------------- |
| `createSpan(name, callback)`      |     ✓     | Chạy `callback` bên trong một span con mới; trả về kết quả của nó   |
| `activeSpan()`                    |     ✓     | Resolve ra `TraceSpanDelegate` của span đang chạy                   |
| `captureError(error, tags?)`      |     ✓     | Ghi lại một lỗi đã xử lý trên trace hiện tại                        |
| `setAttribute(key, value)`        |     ✓     | Ghi vào context store theo request                                  |
| `getAttribute(key)`               |     ✓     | Đọc từ context store theo request                                   |
| `currentTraceId()`                |     ✗     | Trace id đang hoạt động, hoặc `null` khi ở ngoài trace              |
| `counter(name, attributes?)`      |     ✗     | Lấy hoặc tạo một metric tăng đơn điệu                               |
| `gauge(name, attributes?)`        |     ✗     | Lấy hoặc tạo một metric có thể tăng và giảm                         |
| `summary(name, attributes?)`      |     ✗     | Lấy hoặc tạo một metric phân phối có quantile                       |

#### Đọc tiếp

- [Distributed tracing](/observability/distributed-tracing) - dùng `currentTraceId()` để giữ một trace duy nhất xuyên qua ranh giới các service.
- [Dashboard](/observability/dashboard) - nơi span, lỗi đã ghi lại và custom metric hiện lên.
