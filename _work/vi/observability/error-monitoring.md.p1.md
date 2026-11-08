### Error monitoring

Error monitoring có trong mọi gói [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe'), kể cả gói Free, và không cần gì ngoài [SDK](/observability/sdk). Khi ứng dụng của bạn đã được instrument, mọi lỗi lan ra khỏi controller, resolver hay queue consumer đều được ghi lại cùng request mà nó làm hỏng, đoạn code đã throw nó, và trace mà nó chạy trong đó. Trang này nói về những gì được ghi lại, cách các lần xảy ra được gom thành defect, cách bạn được thông báo khi có defect mới, và cách một lỗi trở thành một bản sửa đã được kiểm chứng.

> info **Hint** Để xem trước khi cài đặt bất cứ thứ gì, hãy mở [bản demo trực tiếp](https://www.observe-demo.nestjs.com/dashboard 'NestJS Observe live demo'). Nó hiển thị lỗi của một service đang bận rộn, các defect đã được gom nhóm, và stack trace kèm mã nguồn, không cần đăng ký.

#### Những gì được ghi lại

Các lỗi lan ra khỏi controller, resolver, job hay span được ghi lại tự động, trên HTTP, GraphQL, gRPC và các transport của `@nestjs/microservices`, cũng như với queue consumer và các lần chạy cron. Không có error handler nào cần đăng ký và không cần gọi gì từ [exception filter](/exception-filters) của bạn. Filter vẫn quyết định client thấy gì, còn SDK quan sát lỗi trên đường nó đi tới đó, nên hai thứ hoạt động song song với nhau.

Một lỗi không được lưu thành một dòng log tách rời. Bản thân một lỗi _chính là_ request bị lỗi, nên trang chi tiết của nó là trang của chính request đó với phần lỗi được đặt lên đầu: class của lỗi, message, stack trace và mã nguồn trước, sau đó là context của request, rồi đến waterfall của trace và các log được ghi trong request đó. Khi một HTTP request bị lỗi, SDK cũng ghi lại một danh sách nhỏ các header được cho phép, và tùy chọn cả body của nó (xem [Ghi lại request lỗi và request chậm](/observability/sdk#capturing-failed-and-slow-requests)). Một lần chạy job bị throw được ghi lại là một lần chạy thất bại, kèm lý do thất bại và số thứ tự lần thử, trong view **Jobs**.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/errors.webp" alt="View lỗi" /></figure>

Không phải lỗi nào cũng là bug. Một exception mà code của bạn cố ý throw, chẳng hạn `NotFoundException` hay một lần validate thất bại, vẫn hiện trong view **Errors** vì nó vẫn là một request bị lỗi, nhưng nó không được tính là một defect mới để cảnh báo. Chỉ những lỗi không được xử lý mới được tính: một lỗi mà request của nó trả về 5xx, hoặc một lỗi xảy ra ở một entry point hoàn toàn không có HTTP status, như một RPC handler hay một message của gateway.

#### Ngữ cảnh mã nguồn

Một stack trace từ production thường trỏ tới output đã biên dịch mà bạn không có sẵn trên máy. Khi `sourceContext` được bật (mặc định), SDK đọc các dòng mã nguồn quanh mỗi frame thuộc ứng dụng của một lỗi được ghi lại và gửi chúng kèm theo, nên dashboard hiển thị đoạn code bị lỗi ngay cạnh stack trace:

[[CODE:1]]

Để thấy code TypeScript thay vì JavaScript đã biên dịch, hãy chạy Node với hỗ trợ source map (`--enable-source-maps`, hoặc `process.setSourceMapsEnabled(true)`), hoặc đặt `sourceContext.sourceMaps: true` để SDK tự resolve các frame đã biên dịch. Các frame bên trong `node_modules` và phần nội bộ của Node không bao giờ được đọc. Xem [Ngữ cảnh mã nguồn của lỗi](/observability/sdk#error-source-context) để biết mọi tùy chọn.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/error-with-source.webp" alt="Thẻ lỗi kèm ngữ cảnh mã nguồn" /></figure>

> warning **Warning** Ngữ cảnh mã nguồn gửi một vài dòng mã nguồn của ứng dụng lên dashboard của bạn, được lưu cùng với lỗi. Hãy đặt `sourceContext: false` nếu việc gửi bất kỳ đoạn mã nguồn nào là không chấp nhận được với codebase của bạn.

#### Lỗi đã được xử lý

Một lỗi mà bạn đã catch và xử lý xong sẽ không bao giờ lan ra, nên nó không bao giờ được ghi lại tự động. Khi bạn vẫn muốn thấy nó, hãy báo cáo nó bằng `captureError()` trên `TracerService`:

[[CODE:2]]

Lỗi được gắn vào trace hiện tại kèm các tag tùy chọn được ghi lại cùng nó, và có ngữ cảnh mã nguồn giống như mọi lỗi được ghi lại khác. Xem [Ghi lại lỗi đã xử lý](/observability/manual-instrumentation#capturing-handled-errors).

#### Gom lỗi thành defect

Một đợt tăng vọt 3.140 `TypeError` là một bug, không phải 3.140 bug. Công tắc **Group into defects** trên trang Errors gộp các lần xảy ra có cùng exception class và cùng hình dạng stack đã chuẩn hóa thành một **error group**, được lấy fingerprint ở phía server, bất kể message được diễn đạt thế nào, số dòng đã dịch chuyển ra sao, hay lần deploy nào đã tạo ra nó.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/defects.webp" alt="Lỗi được gom thành defect" /></figure>

Một group mang những thông tin cần cho việc phân loại xử lý, thay vì chi tiết của một lần xảy ra đơn lẻ:

| Trường                   | Cho bạn biết điều gì                                                 |
| ------------------------ | -------------------------------------------------------------------- |
| Class và message mẫu     | Defect đó là gì, lấy từ lần xảy ra đầu tiên                          |
| Status                   | Open, Resolved, hoặc Ignored                                         |
| First seen và last seen  | Nó mới xuất hiện, đang tiếp diễn, hay đã biến mất                    |
| Introduced in            | Bản release mà lần xảy ra đầu tiên chạy trên đó, nếu nó có báo cáo   |
| Occurrences              | Nó xảy ra bao nhiêu lần trong khoảng thời gian được chọn, không phải từ trước đến nay |
| Issue                    | [Issue](/observability/dashboard#issues) mà nó được chuyển thành, nếu có |

**Introduced in** lấy từ `serviceVersion` mà ứng dụng của bạn báo cáo (một semantic version hoặc một commit hash, truyền vào [`forRoot()`](/observability/sdk)). Không có nó, một group không thể biết nó xuất hiện cùng lần deploy nào.

Hai trạng thái đóng được thiết kế bất đối xứng một cách có chủ ý. **Resolved** là một khẳng định về code, nên một group đã resolve sẽ mở lại ngay khi lỗi tái diễn; một bản sửa không có hiệu quả sẽ lộ ra thay vì cứ âm thầm hiện màu xanh. **Ignored** là một quyết định về nhiễu, và sẽ giữ nguyên trạng thái ignored.

#### Nhận thông báo

Mọi gói, kể cả Free, đều có sẵn một **email lỗi mới** mà không cần thiết lập rule nào: mỗi project một email liệt kê những lỗi chưa từng thấy trước đó, tối đa sáu email mỗi ngày. Mỗi thành viên có thể tự tắt nó cho mình trong **Settings → New error emails**. Gói Free cũng theo dõi tỉ lệ lỗi bất thường của mỗi ứng dụng chạy liên tục, với tối đa một email cảnh báo cho mỗi tài khoản trong 30 ngày.

Trên các gói trả phí, [alert rule](/observability/dashboard#alerts) đi xa hơn, bắt đầu với một rule tỉ lệ lỗi bất thường mà mọi ứng dụng đều tự có:

- Rule **new error groups** kích hoạt khi một defect xuất hiện lần đầu tiên, cho một ứng dụng hoặc toàn bộ project. Nó thông báo qua email, Slack, webhook, thông báo trong ứng dụng, hoặc bằng cách mở một issue.
- Rule **error rate** theo dõi tỉ lệ request thất bại với lỗi server (5xx) của một ứng dụng, hoặc của một route và method, so với một ngưỡng cố định hoặc so với baseline gần đây của chính nó bằng anomaly detection.
- Rule **job failure rate** làm điều tương tự cho queue consumer và các lần chạy cron.

Ở các gói cao hơn, một [SLO](/observability/dashboard#slos) về availability (tỉ lệ request hoàn tất mà không có lỗi chưa xử lý) biến chính những lỗi đó thành một error budget với cảnh báo burn rate.

#### Từ lỗi tới bản sửa

Vì mỗi lỗi đã mang sẵn stack trace, các dòng mã nguồn, trace và log, nút **Copy agent prompt** trên trang của nó đóng gói tất cả thành một prompt tự đầy đủ cho một coding agent như Claude Code, Cursor, hay bất kỳ công cụ nào khác đang mở repository của bạn. Một agent kết nối với [MCP server](/observability/mcp-server) có thể tự đi xa hơn: liệt kê các error group kèm bản release đã đưa chúng vào, lấy các lần xảy ra gần đây kèm trace id, cho biết một lỗi đang tăng hay giảm dần, và xem những người dùng nào bị ảnh hưởng.

Để theo dõi công việc, hãy chuyển một error group thành [issue](/observability/dashboard#issues) chỉ với một cú click; chuyển một group đã có issue đang mở sẽ liên kết tới issue đó thay vì mở issue thứ hai. Trước khi resolve, mục **Did a release fix this?** trên issue sẽ trả lời dựa trên dữ liệu production: nó đánh giá một bản release trên chính các request của bản đó, trên các route mà lỗi đã xảy ra, so với tần suất lỗi xảy ra ở đó trước đây. Một agent đặt cùng câu hỏi đó bằng `verify_fix` qua [MCP server](/observability/mcp-server). Khi bạn đánh dấu issue là resolved (có thể ghi tên bản release chứa bản sửa), dashboard sẽ theo dõi operation bị ảnh hưởng so với baseline trước sự cố, và hoặc đóng issue khi bản sửa đã giữ vững, hoặc mở lại nó kèm số liệu cho thấy bản sửa không hiệu quả.

Sau một lần deploy, view **Releases** so sánh từng `serviceVersion` với bản trước nó, bao gồm cả tỉ lệ lỗi, nên một regression hiện ra dưới dạng khác biệt giữa hai phiên bản thay vì một chỗ nhô lên đâu đó trên biểu đồ dài cả tuần. [Đánh giá](/observability/dashboard#releases-and-their-verdicts) của mỗi bản release cũng liệt kê các error group xuất hiện lần đầu trong bản đó.
