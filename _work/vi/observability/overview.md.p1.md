### Tổng quan

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') là nền tảng observability và giám sát hiệu năng ứng dụng (APM) chính thức, tự động instrument, dành cho các ứng dụng NestJS. Cài SDK, thêm một API key, và ứng dụng của bạn bắt đầu stream request, background job, lỗi, log và trace lên dashboard - không cần tự nối span bằng tay, không cần chạy collector, không cần thiết kế schema, không cần tự dựng dashboard.

> info **Hint** Chương này trình bày cách instrument một ứng dụng NestJS bằng SDK `@nestjs/observe` và những gì instrumentation đó mang lại. Nếu bạn đang tìm chính dashboard, hãy vào [observe.nestjs.com](https://www.observe.nestjs.com/ 'NestJS Observe'), hoặc mở [bản demo trực tiếp](https://www.observe-demo.nestjs.com/dashboard 'Bản demo trực tiếp của NestJS Observe') - toàn bộ dashboard trên dữ liệu của một service bận rộn, không cần đăng ký và không cần cài gì.

#### Khác gì so với một APM Node.js thông thường

Các agent APM Node.js thông thường gắn vào HTTP server và database driver, còn mọi thứ ở giữa thì để như một hộp đen. NestJS Observe được xây dựng quanh chính vòng đời request của Nest - controller, guard, interceptor, pipe, resolver, queue consumer - nên dữ liệu telemetry được thể hiện bằng chính ngôn từ mà bạn dùng khi viết code: `OrdersService.recalculate`, chứ không phải `POST /orders`. Đó cũng là lý do nó có thể hiển thị thời gian theo từng **class và method** của NestJS, không chỉ theo route, và lý do một trace waterfall từ một ứng dụng chưa sửa gì đã đọc giống như một call graph.

SDK gắn vào framework thông qua tùy chọn ứng dụng `instrument` của `NestFactory.create()` (có sẵn từ `@nestjs/core` v11.1.4), nên nó thấy mọi controller, provider, resolver và queue consumer đúng như cách Nest nối chúng - không patch toàn process, và không cần import gì trước phần còn lại của code.

Nó không phải là thứ thay thế OpenTelemetry: Observe bao quát các service Nest trong hệ thống của bạn, dù đó là toàn bộ backend hay chỉ một phần, chạy riêng hay chạy cạnh OpenTelemetry mà bạn đã có, và các service viết bằng ngôn ngữ khác dùng chung trace của nó thông qua OpenTelemetry. Xem [OpenTelemetry](/observability/opentelemetry#running-beside-opentelemetry).

#### Những gì nó cung cấp

Khi SDK đã chạy, mọi gói - kể cả gói miễn phí - đều cho bạn:

- **Giám sát request** cho HTTP, GraphQL, gRPC và các transport của `@nestjs/microservices`: throughput, độ trễ (trung bình và p95), tỉ lệ thất bại theo từng operation, và một trang chi tiết cho từng lần thực thi.
- **Distributed tracing** với một waterfall gồm mọi span mà request đã chạy, xếp hạng self-time để tìm ra thời gian thực sự đi đâu, và liên kết xuyên các service khi trace id được truyền đi (xem [Distributed tracing](/observability/distributed-tracing)).
- **Theo dõi lỗi** với stack trace, các dòng mã nguồn quanh frame lỗi, và việc gom các lần xảy ra thành defect ngay phía server.
- **Job** - queue consumer và các lần chạy cron (ví dụ BullMQ) được đối xử giống như request, cộng thêm thời gian chờ trong queue và số lần retry.
- **Service** - bảng phân tích theo từng class, từng method về thời gian tự thân so với tổng thời gian trong toàn ứng dụng.
- **Runtime profiling** - CPU, bộ nhớ, độ trễ và mức sử dụng event loop, và garbage collection, được lấy mẫu từ bên trong process và so sánh theo từng instance.
- **Release** - mọi request và job đều ghi lại phiên bản đã phục vụ nó, và mỗi release nhận một kết luận: lần deploy có làm mọi thứ tệ đi không, và những query, lời gọi ra ngoài và method nào hoạt động khác đi kể từ đó (xem [Release và kết luận của chúng](/observability/dashboard#releases-and-their-verdicts)).
- **Custom metric** - counter, gauge và summary được báo cáo từ chính code của bạn.
- **Người dùng** - hoạt động theo từng người dùng, được gom thành những hành động họ thực sự đã làm, khi ứng dụng của bạn báo cáo định danh người dùng.
- **Issue** - theo dõi theo phạm vi project cho những việc mà dữ liệu telemetry phát hiện ra, với một bản ghi sự cố, một bước kiểm tra xem release có sửa được lỗi không, và việc xác minh so với mốc trước sự cố khi bạn đóng một issue.
- **Cảnh báo có sẵn** - một email khi xuất hiện một lỗi mà Observe chưa từng thấy, và, với một ứng dụng chạy suốt ngày đêm, khi tỉ lệ lỗi của nó bất thường hoặc nó im lặng.
- **Copy agent prompt** - một cú click biến một request thất bại, một job chậm hay một trace lỗi thành một prompt hoàn chỉnh cho coding agent.

Các gói trả phí có thêm **stream log** (liên kết với trace, mặc định bật che giấu dữ liệu nhạy cảm), **quy tắc cảnh báo** (ngưỡng, phát hiện bất thường, phát hiện vắng mặt, kênh Slack/webhook/email, và một bộ khởi đầu cho mọi ứng dụng), **[quy tắc production](/observability/production-rules)** được kiểm tra trên mọi trace được giữ lại, **[trang trạng thái](/observability/dashboard#status-pages)** công khai, quản lý team kèm audit log, và một **MCP server** để agent tương thích MCP có thể truy vấn dữ liệu telemetry, tự đánh giá các lần deploy của nó, và thiết lập một service mới (xem [MCP server](/observability/mcp-server)). Các gói cao hơn có thêm **SSO** và **SLO** với error budget và cảnh báo burn-rate.

#### Cách tổ chức

NestJS Observe tổ chức dữ liệu telemetry của bạn theo ba lớp:

- Một **team** là một tập hợp người dùng. Mỗi project thuộc về đúng một team, và tư cách thành viên team là cách để cấp cho ai đó quyền truy cập nhiều project cùng lúc. Gói đăng ký được quản lý theo từng team.
- Một **project** là một tập hợp các ứng dụng được ship cùng nhau, thường là một project cho mỗi sản phẩm hoặc môi trường (ví dụ `storefront-production`, `storefront-staging`). Project là phạm vi của cảnh báo, issue, SLO và API key.
- Một **ứng dụng** là một service NestJS duy nhất - một REST API, một worker, một microservice - được instrument bằng SDK và báo cáo vào một project. Một project thường có nhiều hơn một ứng dụng (ví dụ một web API và các queue worker phía sau nó), nên bạn có thể xem chúng như một hệ thống mà vẫn lọc xuống từng ứng dụng.

<figure><img src="https://www.observe.nestjs.com/docs/overview/projects.webp" alt="Tổng quan các project" /></figure>

Mỗi thành viên của project có một trong ba mức truy cập - **Read**, **Write** hoặc **Admin** - quyết định họ có thể xem dữ liệu telemetry, tạo quy tắc cảnh báo, ứng dụng và API key, hay quản lý thành viên và kiểm soát chi tiêu.

#### Đăng ký gói

Đăng ký tại [observe.nestjs.com](https://www.observe.nestjs.com/ 'NestJS Observe'). Gói **Free** không cần thông tin thanh toán và đã bao gồm theo dõi lỗi, distributed tracing và tự động instrument, nên bạn có thể instrument một ứng dụng và xem trace thật trước khi quyết định có cần nhiều hơn không.

Mức sử dụng được tính bằng **Observability Event (OE)** - mỗi request, lần chạy background job, lỗi, dòng log hoặc trace span mà ứng dụng của bạn báo cáo là một event. Các event được cộng dồn chứ không gộp lại: một request chạy qua ba method của bạn, ghi hai dòng log và phát sinh một lỗi là bảy event. Các span query database và HTTP gửi ra ngoài của chính agent không được tính, vì chúng là chi tiết của một span method vốn đã được tính. Gói của bạn đặt ra một lượng event bao gồm sẵn mỗi tháng, một khoảng thời gian lưu trữ, và những tính năng được mở khóa:

| Gói        | Event bao gồm / tháng   | Lưu trữ    | Log & cảnh báo | SSO & SLO |
| ---------- | ----------------------: | ---------- | -------------- | --------- |
| Free       |                    300k | 3 ngày     | ✗              | ✗         |
| Pro        |                     25M | 30 ngày    | ✓              | ✗         |
| Scale      |                    200M | 90 ngày    | ✓              | ✓         |
| Enterprise |             Thương lượng | Thương lượng | ✓            | ✓         |

Gói Free vẫn tiếp tục ghi lại request, job và lỗi khi đã vượt quá lượng bao gồm, và hy sinh dần mức chi tiết theo từng giai đoạn:

- **Một ngày bị điều tiết.** Khi ứng dụng của bạn gửi 30.000 event trong một ngày UTC (một phần mười lượng của tháng), hầu hết trace waterfall sẽ tạm dừng cho đến 00:00 UTC, để một ngày ồn ào không tiêu hết cả tháng. Các span bị giữ lại không được tính vào lượng bao gồm.
- **Giảm tiếp nhận, khi vượt quá 300k event.** Các biểu đồ vẫn cập nhật trực tiếp, nhưng hầu hết trace đến mà không kèm span của chúng.
- **Từ chối, ở mức 600k event.** Khi gấp đôi lượng bao gồm, collector trả lời dữ liệu telemetry mới bằng mã `429` cho đến kỳ tiếp theo. Dữ liệu bị bỏ, không được xếp hàng.

Trong khi một ngày bị điều tiết hoặc việc tiếp nhận bị giảm, lỗi server, job thất bại và mọi thứ chậm hơn 1 giây vẫn giữ đầy đủ trace. Pro và Scale cho phép vượt mức thay vì dừng hẳn, tính phí theo mỗi triệu event bổ sung, nên một tháng bận rộn không có nghĩa là mất dữ liệu telemetry.

Với các gói lưu trữ dữ liệu lâu hơn 7 ngày, cây span của một lần thực thi vừa nhanh vừa thành công (dưới 1 giây, không có 5xx, không có job thất bại) bị xóa sau 7 ngày; các lần thực thi chậm và thất bại giữ waterfall của chúng suốt khoảng thời gian lưu trữ. Bản thân các lần thực thi, cùng mọi percentile, tỉ lệ lỗi và SLO, được giữ trong suốt khoảng thời gian đó. Thanh toán theo năm được giảm giá so với giá theo tháng. Để biết giá hiện tại, số lượng ghế và mức phí vượt mức, xem [trang bảng giá](https://www.observe.nestjs.com/ 'NestJS Observe').

Để nâng cấp, mở **Billing → Manage subscription** của team sở hữu các project của bạn. Cũng ở khu vực đó, trang **Usage** theo dõi Observability Event của bạn so với lượng bao gồm, phân theo project, và cho phép bạn đặt **thông báo hạn mức** (tối đa năm ngưỡng, ví dụ 50%, 80%, 100%) để nhận email khi mức sử dụng vượt qua một ngưỡng.

> info **Hint** Khối lượng tiếp nhận có thể kiểm soát mà không cần deploy lại, thông qua **kiểm soát chi tiêu** theo từng project: lấy mẫu span nhất quán theo trace, giới hạn tốc độ mỗi phút, và các bộ lọc loại bỏ cho traffic vốn ồn ào như `/health*`. Việc lấy mẫu luôn giữ lại lỗi server và trace chậm. Giới hạn tốc độ là mức trần cho khối lượng vượt kiểm soát: một lô bị từ chối vì vượt giới hạn sẽ mất trọn vẹn, kể cả lỗi. Bạn cũng có thể ngăn dữ liệu telemetry được tạo ra ngay từ phía SDK - xem [Bỏ qua các operation ồn ào](/observability/sdk#ignoring-noisy-operations).

Trên Pro và Scale, **Billing → Spend controls** còn giới hạn chi phí vượt mức. **Spike protection** (mặc định bật trên Pro, và trong tháng đầu tiên trên Scale) tạm dừng việc vượt mức khi mức sử dụng tăng vọt và khoản vượt mức của tháng này, với tốc độ hôm nay, sẽ lên tới $50 trở lên. Một **ngân sách vượt mức hằng tháng** tạm dừng việc vượt mức khi khoản vượt mức của tháng đạt tới số tiền bạn đặt; ngân sách $0 sẽ không thu thập gì vượt quá lượng event bao gồm. Trong khi việc vượt mức bị tạm dừng, lỗi server, job thất bại, cùng các metric runtime và custom metric vẫn tiếp tục được gửi, không tính phí; mọi thứ khác vượt quá lượng bao gồm sẽ bị bỏ, không tính phí, cho đến ngày 1, hoặc cho đến khi bạn tiếp tục, đổi ngân sách hoặc nâng cấp. SDK 0.3.13 trở lên chuyển sang chỉ gửi những gì được giữ lại trong thời gian tạm dừng.

#### Project đầu tiên

Cách nhanh nhất để có project đầu tiên bắt đầu từ terminal. Chạy `npx @nestjs/observe link` trong thư mục project và xác nhận mã mà nó in ra tại [observe.nestjs.com/link](https://www.observe.nestjs.com/link 'Liên kết project với NestJS Observe'), đăng ký trước nếu bạn chưa có tài khoản. Việc xác nhận sẽ tạo project và ứng dụng nếu bạn chưa có, và cấp một API key, lệnh sẽ ghi key đó vào `.env` của project. Nếu ứng dụng chưa dùng [SDK](/observability/sdk), lệnh cũng cài và nối nó vào - xem [Liên kết từ terminal](/observability/sdk#linking-from-the-terminal). Một project được tạo bằng `nest new` có kèm Observe sẽ đề nghị bước này ngay sau khi cài đặt.

Nếu bắt đầu từ dashboard, một tài khoản mới sẽ được đề nghị một **hướng dẫn thiết lập** ngắn đi qua các trang thật - nó làm nổi bật *Create Project*, rồi đưa bạn vào project mới để thêm một ứng dụng và một API key, và kết thúc ở banner chờ event đầu tiên của bạn. Cùng các bước đó làm bằng tay:

1. **Tạo một project** và đặt tên cho nó.
2. **Thêm một ứng dụng** vào đó. Một ứng dụng không cần gì ngoài một cái tên - các route nó phục vụ, các job nó xử lý và các metric nó báo cáo đều được phát hiện từ dữ liệu telemetry mà SDK gửi lên.
3. **Tạo một API key** từ trang **API Keys** của project. Mỗi key có một tên (một cho phát triển local, một cho CI, một cho production) và một ngày hết hạn tùy chọn. Cặp key (`appKey` và `appSecret`) chỉ được hiển thị một lần, lúc tạo, nên hãy copy nó vào kho secret của bạn ngay lập tức. Key có phạm vi theo project: mọi ứng dụng có dữ liệu telemetry cần đổ về project đó đều dùng cùng một key.
4. **Instrument ứng dụng** bằng cách làm theo chương [SDK](/observability/sdk). Dữ liệu telemetry bắt đầu xuất hiện chỉ trong chốc lát sau khi ứng dụng của bạn nhận traffic.

> info **Hint** Nếu bạn thiết lập bằng một coding agent, hãy dùng nút **Copy setup prompt** trong hộp thoại hiển thị secret của một key mới. Nó gộp lệnh cài đặt, ba chỗ sửa code và thông tin xác thực thành một prompt duy nhất. Một agent kết nối với [MCP server](/observability/mcp-server#setting-up-a-service) có thể tự tạo ứng dụng và key.

<figure><img src="https://www.observe.nestjs.com/docs/applications/api-keys.webp" alt="API key" /></figure>

> warning **Warning** Hãy xử lý `appKey` và `appSecret` như mọi thông tin xác thực khác: đọc chúng từ biến môi trường hoặc secret manager, đừng bao giờ commit chúng vào source control. Bạn có thể thu hồi một key từ cùng trang đó bất cứ lúc nào; các ứng dụng vẫn đang dùng nó sẽ không gửi được dữ liệu telemetry nữa.

#### Overhead hiệu năng

SDK thêm rất ít chi phí cho một request: khoảng một phần mười mili giây vào độ trễ trung vị của một endpoint điển hình, và vài micro giây CPU cho mỗi lời gọi được trace. Span được ghi lại trên chính thread phục vụ request; cứ mỗi `flushInterval`, thread đó serialize lô dữ liệu, và một worker thread nén rồi gửi nó đi. Được đo vào tháng 10 năm 2026 so với cùng một ứng dụng Nest 12 không có SDK, trên Express, Node 24 và một Apple M1 Pro:

| Endpoint có                                  | 1 lời gọi được trace | 9 lời gọi được trace | 102 lời gọi được trace |
| -------------------------------------------- | -------------------- | -------------------- | ---------------------- |
| Độ trễ trung vị tăng thêm ở 150 request/s    | +0,10 ms             | +0,09 ms             | +0,45 ms               |
| CPU tăng thêm mỗi request, process bận hoàn toàn | +9 µs            | +29 µs               | +115 µs                |
| CPU tăng thêm ở 150 request/s                | +3,5% một core       | +4% một core         | +10% một core          |

Chín lời gọi là một guard, một interceptor, một pipe, một controller, một service và hai repository; 102 lời gọi là một service gọi một provider khác trong vòng lặp. Theo kinh nghiệm, chi phí CPU vào khoảng 8 µs mỗi request cộng thêm 1-2,5 µs cho mỗi lời gọi được trace, và khi tải nhẹ, một request mất 10 ms sẽ chậm đi khoảng 1%. Bộ nhớ tăng khoảng 11 MB lúc khởi động và 32-64 MB khi có tải, và một process đang rảnh dành 0,3-0,6% của một core cho SDK, gần như toàn bộ là trên worker thread.

Để so sánh, lượng throughput mà các agent Node.js khác mất đi trong các benchmark của bên thứ ba trên những endpoint gần như rỗng tương đương 45 µs mỗi request với Sentry, 130 µs với Datadog và 200 µs với New Relic ([NodeSource](https://benchmark.nodesource.com/ 'Các benchmark Node.js của NodeSource')), và 31-77 µs với OpenTelemetry ([Platformatic](https://blog.platformatic.dev/the-hidden-cost-of-context 'The hidden cost of context')). Tính theo cùng cách, SDK thêm 7 µs trên endpoint một lời gọi và 20 µs trên endpoint chín lời gọi. Máy móc, và những gì mỗi agent ghi lại, đều khác nhau, nên hãy xem đây là một xu hướng chứ không phải một bảng xếp hạng.

> info **Hint** Benchmark và kết quả đầy đủ của nó nằm trong [repository SDK](https://github.com/nestjs/observe/blob/master/bench/README.md 'Benchmark SDK của NestJS Observe'). Chạy `npm run bench` trong một bản clone để tái hiện chúng trên phần cứng của bạn trong khoảng 8 phút.

#### Đọc tiếp

- [SDK](/observability/sdk) - cài đặt, phần bắt đầu nhanh ba dòng, và mọi tùy chọn cấu hình.
- [Instrumentation thủ công](/observability/manual-instrumentation) - custom span, lỗi đã xử lý, thuộc tính theo request, và custom metric.
- [Distributed tracing](/observability/distributed-tracing) - truyền trace id qua HTTP, gRPC, các transport microservice và GraphQL.
- [Theo dõi lỗi](/observability/error-monitoring) - những gì được ghi lại, ngữ cảnh mã nguồn, gom lỗi thành defect, và đi từ một lỗi tới một bản fix đã được xác minh.
- [Dashboard](/observability/dashboard) - mỗi view hiển thị gì khi dữ liệu telemetry đã chảy về, và cảnh báo, SLO và issue được xây dựng trên đó như thế nào.
- [Quy tắc production](/observability/production-rules) - ghi rõ một request hoặc job được phép làm gì, được kiểm tra trên mọi trace được giữ lại.
- [MCP server](/observability/mcp-server) - truy vấn dữ liệu telemetry từ Claude Code, Cursor, VS Code hoặc agent của riêng bạn.
