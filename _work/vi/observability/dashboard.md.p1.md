### Dashboard

Khi một ứng dụng đã được instrument và đang gửi dữ liệu, dashboard của project sẽ tự động có dữ liệu, không cần viết query nào và không cần dựng dashboard nào. Chương này nói về những gì mỗi view hiển thị, các view liên hệ với nhau ra sao, và các tính năng xây trên nền telemetry (đánh giá bản release, status page, cảnh báo, SLO, issue, và việc chuyển giao cho agent) kết hợp với nhau thế nào. Để xem tài liệu tham khảo đầy đủ, hãy đọc [tài liệu NestJS Observe](https://www.observe.nestjs.com/documentation 'NestJS Observe documentation').

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/dashboard.webp" alt="Dashboard của project" /></figure>

> info **Hint** Mọi view mô tả bên dưới đều có thể click thử trong [bản demo trực tiếp](https://www.observe-demo.nestjs.com/dashboard 'NestJS Observe live demo'), nơi dashboard chạy trên một tập dữ liệu được sinh ra từ một service đang bận rộn: lưu lượng request thực tế, trace kèm waterfall, lỗi, job và cảnh báo. Không cần tài khoản và nó chạy hoàn toàn trong trình duyệt của bạn.

#### Các view lồng nhau thế nào

Gần như mọi view telemetry đều thuộc một trong ba cấp, và bạn di chuyển giữa chúng bằng cách click vào:

1. **Analytics** - view dạng danh sách. Mọi route, job, span hay metric mà các ứng dụng của bạn đã báo cáo trong khoảng thời gian được chọn, ở dạng tổng hợp: throughput, độ trễ, tỉ lệ thất bại. Đây là nơi bạn nhận ra có điều gì đó.
2. **Operation** - một route (`GET /orders/:id`), một tên job, một tên span. Vẫn những con số đó theo thời gian, kèm danh sách các execution riêng lẻ đằng sau chúng. Đây là nơi bạn xác nhận hình dạng của một vấn đề: liên tục hay đột biến, ở mọi nơi hay chỉ ở một bản release.
3. **Execution** - một request, một lần chạy job, một lần gọi span. Thời lượng chính xác, status, người dùng, tag, lỗi mà nó gây ra, waterfall của mọi thứ nó đã làm, và các log nó đã ghi. Đây là nơi bạn chẩn đoán.

Số liệu tổng hợp cho bạn biết _rằng_ có gì đó sai và nó quan trọng đến mức nào; một execution đơn lẻ cho bạn biết _tại sao_. Mọi view dùng chung một thanh điều khiển (một khoảng thời gian và một bộ lọc ứng dụng tùy chọn), và mọi thứ trên trang đều tuân theo nó.

#### Các view telemetry

| View        | Hiển thị gì                                                                                                                                                                                                                                                                                                      |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Requests** | Mọi request HTTP, GraphQL, gRPC, microservice và WebSocket gateway, chia theo operation. Trang chi tiết request so sánh lời gọi với baseline của chính route đó ("chậm hơn 95% số lời gọi") và, khi process đang chật vật, cho biết áp lực lên host đã làm operation này chậm đi bao nhiêu.                     |
| **Services** | Thời gian tiêu tốn theo từng **class và method** của NestJS, chia thành thời gian riêng (đã trừ mọi thứ được await) và tổng thời gian. Chỉ các class được instrument mới xuất hiện, nên danh sách ngắn nghĩa là độ phủ thấp, không phải lưu lượng thấp.                                                        |
| **Errors**   | Mọi lỗi chưa được xử lý, gom theo operation, với phần lỗi đặt lên đầu trang: class, message, stack trace và mã nguồn. Công tắc **Group into defects** gộp các lần xảy ra có cùng class và hình dạng stack thành một group có fingerprint, kèm first/last seen và bản release đã đưa nó vào. Xem [Error monitoring](/observability/error-monitoring). |
| **Jobs**     | Công việc chạy nền - queue consumer, các lần chạy cron - với thời gian chờ trong queue, số thứ tự lần thử, và lý do thất bại bên cạnh thời lượng và tỉ lệ thất bại.                                                                                                                                            |
| **Spans**    | Phân tích các custom span mà code của bạn tạo bằng [`TracerService.createSpan()`](/observability/manual-instrumentation), trên mọi route gọi tới chúng - "`OrdersService.recalculate` chậm đến mức nào ở mọi nơi", thay vì "endpoint này chậm đến mức nào". Các span do SDK tự ghi lại thì được xem trong waterfall của từng execution. |
| **Traces**   | Waterfall của một trace id, xuyên suốt mọi service dùng chung nó - xem [Distributed tracing](/observability/distributed-tracing).                                                                                                                                                                              |
| **Users**    | Hoạt động theo từng người dùng khi `getUserId` được cấu hình: tỉ lệ thất bại theo người dùng, các lời gọi được gom thành những hành động họ đã thực hiện, phát lại từng hành động, và đường đi giữa chúng. Công tắc **Group by customer** gộp các danh tính theo domain email.                                   |
| **Custom**   | Counter, gauge và summary được báo cáo qua [`TracerService`](/observability/manual-instrumentation#custom-metrics), gom theo tên metric và label.                                                                                                                                                                         |
| **Releases** | Mỗi `serviceVersion` được so sánh với bản trước nó - tỉ lệ lỗi, độ trễ và throughput đặt cạnh nhau - kèm đánh giá liệu lần deploy đó có làm mọi thứ tệ hơn hay thay đổi những gì code làm hay không. Xem [Bản release và đánh giá](/observability/dashboard#releases-and-their-verdicts). |
| **Logs**     | Mọi thứ mà các service của bạn đã log (khi bật `forwardLogs`), được liên kết với các trace mà chúng chạy trong đó. Trên trang execution, mỗi dòng được đặt trên trục thời gian của trace, cạnh span đang chạy lúc đó.                                                                                            |
| **Profiler** | CPU, bộ nhớ, độ trễ và mức sử dụng event loop, và garbage collection theo từng ứng dụng, với so sánh theo từng instance khi một ứng dụng chạy trên nhiều node. Click vào một đỉnh trên biểu đồ Memory hoặc Event loop delay để xem những operation nào đã chạy tại thời điểm đó, xếp hạng theo độ lệch so với baseline của chúng. |
| **Rules**    | [Production rule](/observability/production-rules): những gì một request hoặc job được phép làm, được kiểm tra trên mọi trace được giữ lại, kèm các trace đã vi phạm từng rule và bản release mà chúng đến từ. Dành cho gói trả phí. |

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/services.webp" alt="View Services" /></figure>

#### Query, lời gọi ra ngoài và request được ghi lại

Trong waterfall của một trace, một database query hoặc một HTTP request gửi ra ngoài là một dòng riêng dưới method đã tạo ra nó: một icon, operation (`SELECT orders`, `POST api.stripe.com`), và câu lệnh hoặc URL bên cạnh, nhìn thấy được mà không cần hover. Mũi tên của dòng đó mở ra toàn bộ câu lệnh được trình bày theo từng mệnh đề, với các placeholder được làm nổi bật và một nút copy. Giá trị không bao giờ xuất hiện, vì agent đã loại bỏ chúng trước khi gửi bất cứ thứ gì. Bảng span bên dưới chỉ liệt kê các method của ứng dụng bạn; các query span của agent bị bỏ qua và thời gian của chúng được tính là thời gian riêng của method gọi, nên bảng vẫn trả lời được câu hỏi "method nào của tôi đã tốn thời gian". Trang **Services** cũng tuân theo quy tắc đó: các driver (`pg`, `mysql2`, `mongodb`, `http`) không được liệt kê như class, và thời gian chờ của một query được tính là thời gian riêng của method đã chạy nó.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/sql.webp" alt="Một query được mở trong waterfall" /></figure>

Khi agent giữ lại input của chính request (vì nó bị lỗi, hoặc chạy quá ngưỡng [`slowerThanMs`](/observability/sdk#capturing-failed-and-slow-requests) mà bạn cấu hình), thẻ **Details** của request có thêm hai dòng thu gọn, *Request headers* và *Request body*. Một request không ghi lại gì sẽ không có các dòng này.

#### Service map

Trang **Activity → Map** của một project cho thấy các ứng dụng, queue và database của nó giao tiếp với nhau ra sao. Ứng dụng và queue được xếp từ trái sang phải theo thứ tự gọi, và các database cùng service bên ngoài mà mỗi cái phụ thuộc vào được treo bên dưới nó. Độ dày của một đường và tốc độ luồng lưu lượng chạy dọc theo nó cho thấy khối lượng. Màu đỏ nhạt đánh dấu tỉ lệ lỗi trên 1%, đỏ đậm là trên 5%, và màu xanh mòng két nghĩa là khỏe mạnh. Hover lên bất kỳ node nào để tách riêng những gì nó chạm tới, và click vào để xem số liệu của nó: với một database, đó là các câu lệnh đã ngốn thời gian; với một ứng dụng, đó là những gì nó gọi và những gì gọi nó, kèm link tới các request của nó.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/map.webp" alt="Service map" /></figure>

Map không cần cấu hình và không thu thập gì mới. Database và host bên ngoài lấy từ [query span và outbound-HTTP span](/observability/sdk#database-queries-and-outbound-http) của agent, queue lấy từ các job mà một ứng dụng xử lý, và các đường nét đứt giữa các ứng dụng lấy từ những execution dùng chung một [trace id](/observability/distributed-tracing). Mỗi ứng dụng có một node database cho mỗi driver, nên hai service cùng dùng Postgres thường hiện thành hai database, vì không có gì trên đường truyền cho biết chúng dùng chung một database. Ngược lại, một host bên ngoài là một node duy nhất dùng chung cho mọi bên gọi, tối đa tám host bận rộn nhất cho mỗi ứng dụng.

Một ứng dụng hoàn toàn không có đường nào gần như luôn là do đang chạy SDK cũ hơn `0.3.0`, phiên bản chưa báo cáo query hay lời gọi ra ngoài.

> info **Hint** Liên kết giữa các ứng dụng được suy ra từ những request gần nhất, chứ không được đếm trên toàn bộ khoảng thời gian. Hãy đọc một đường nét đứt là "cái này gọi cái kia", chứ không phải một tổng số chính xác.

#### Bản release và đánh giá

View **Releases** liệt kê mọi `serviceVersion` mà các ứng dụng của bạn đã báo cáo. Mở một bản ra và nó mở đầu bằng một **verdict** (đánh giá): lần deploy đó có làm mọi thứ tệ hơn không, và có gì hoạt động khác đi kể từ đó không, trong một từ và một câu.

- **Regression** - lỗi server (5xx) tăng qua ranh giới release vượt mức nhiễu.
- **Changed** - lỗi server không tăng, nhưng bản release làm điều gì đó mới: một error group xuất hiện lần đầu trong bản đó, một route bỗng im lặng, hoặc thay đổi trong những gì code gọi tới.
- **Clean** - không có điều nào ở trên. Câu mô tả cho biết những gì đã được so sánh, để một đánh giá clean dựa trên quá ít telemetry không bị hiểu là đáng tin hơn thực tế.
- **Not enough data** - quá ít request ở mỗi bên để đánh giá.

Dưới verdict là bằng chứng mà nó dựa vào: các error group xuất hiện lần đầu trong bản release, các route đã phục vụ đều đặn trước ranh giới và không có gì sau đó (request không bao giờ bị lấy mẫu, nên một route im lặng là thực sự đã dừng), các outbound host, hình dạng query và method mà chỉ một phía của ranh giới gọi tới, và những lưu ý cần đọc trước - span bị lấy mẫu, hoặc một rolling deploy mà số liệu phản ánh sự pha trộn giữa các phiên bản.

Tiếp theo, **What changed in the code** liệt kê các query, lời gọi ra ngoài và method có hành vi thay đổi vượt mức nhiễu: **New** hoặc **Gone**, một câu lệnh được chạy nhiều hơn **44×** mỗi request - một lỗi N+1 mới thường trông y hệt như vậy, rất lâu trước khi nó làm p95 thay đổi - hoặc một method có thời gian riêng **chậm hơn 7.6×**. Một lời gọi mà bản release mới thêm vào, hoặc giờ được gọi thường xuyên hơn, sẽ có tùy chọn **Pin as a rule**, tạo ra một [production rule](/observability/production-rules) chỉ ra bản release tiếp theo vi phạm nó. Không cái nào trong số này thu thập thêm dữ liệu: nó đọc cùng các dòng request và telemetry theo method như phần còn lại của dashboard. Một agent nhận được cùng verdict đó qua [MCP server](/observability/mcp-server) với `get_release_verdict`.

#### Status page

Từ gói Pro trở lên, một ứng dụng có thể có một **status page** công khai: availability và thời gian phản hồi p95 của nó cho mỗi ngày mà gói của bạn lưu giữ, tối đa 90 ngày, tại một địa chỉ bạn có thể đưa cho những người dùng nó. Trên danh sách **Applications**, click vào icon phát sóng ở dòng của ứng dụng, hoặc chọn **Status page** từ menu của nó, rồi bật lên - quyền Write hoặc Admin là đủ. Gỡ nó xuống cũng ở chỗ đó; công khai lại sẽ trả về đúng địa chỉ cũ. **Show response times** được bật mặc định; khi tắt, trang chỉ hiển thị availability.

<figure><img src="https://www.observe.nestjs.com/docs/applications/status-page.webp" alt="Status page" /></figure>

Availability là tỉ lệ request không bị lỗi server (5xx); lỗi client (4xx) không bị tính vào. Một ngày là **Operational** khi đạt từ 99.5% trở lên, hiển thị **Elevated errors** từ 95%, và **Major errors** khi dưới mức đó; một ngày có ít hơn 20 request sẽ hiển thị con số mà không có trạng thái. Trang không bao giờ cho thấy ứng dụng nhận bao nhiêu lưu lượng, và không bao giờ báo một ứng dụng bị down vì điều gì đó do Observe gây ra: một ngày không ghi nhận request nào sẽ nói đúng như vậy, và một ngày mà việc thu thập vượt hạn mức bị tạm dừng sẽ được đánh dấu là ghi nhận một phần và không được tính vào số liệu. Trang tự làm mới mỗi phút và không được các công cụ tìm kiếm index.

#### Chuyển một lỗi cho coding agent

Đọc một trace cho bạn biết chuyện gì đã xảy ra. Bước tiếp theo lúc nào cũng vậy: tìm đoạn code đó và sửa nó. Nút **Copy agent prompt** thực hiện việc chuyển giao này chỉ với một click. Nó copy toàn bộ trang thành một prompt markdown tự đầy đủ, sẵn sàng để dán vào Claude Code, Cursor, hay bất kỳ công cụ nào khác đang mở repository của bạn.

Nút này chỉ xuất hiện ở những nơi có điều cần điều tra: một request hoặc job bị lỗi hoặc chạy chậm hơn 95% các lần tương tự, hoặc một trace có chứa lỗi. Prompt bao gồm phần mô tả nhiệm vụ, context của operation, lỗi kèm stack trace đã rút gọn và các dòng mã nguồn (đường dẫn được viết lại tương đối so với thư mục gốc của project, nên là `src/orders/orders.service.ts:35` thay vì `/var/app/current/dist/orders/orders.service.js:35`), lời gọi đó so với mức trung bình và p95 của operation thế nào, các span hàng đầu theo self time, tối đa 40 dòng log được chọn ưu tiên lỗi trước, và chỉ dẫn kết thúc yêu cầu agent giải thích nguyên nhân gốc từ code và đề xuất bản sửa dưới dạng diff kèm test.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/copy-agent-prompt.webp" alt="Copy agent prompt" /></figure>

Với một agent cần tiếp tục đặt câu hỏi (lần theo một trace vào log của nó, kiểm tra xem một lỗi có còn đang xảy ra không), hãy kết nối nó với [MCP server](/observability/mcp-server) thay vào đó.

#### Cảnh báo

Cảnh báo thông báo cho bạn khi telemetry vượt qua một ngưỡng mà bạn quan tâm, để bạn không phải biết chuyện từ khách hàng. Một rule theo dõi một metric thuộc một trong các nhóm sau:

| Nhóm    | Metric                                          | Phạm vi                                             |
| ------- | ----------------------------------------------- | --------------------------------------------------- |
| Request | Error rate, p95 latency, avg latency, throughput | Một ứng dụng, và tùy chọn một route + method        |
| Job     | Job failure rate, job throughput, p95 queue wait | Một ứng dụng, và tùy chọn một tên job + queue       |
| Absence | Telemetry silence, job silence                  | Một ứng dụng, hoặc một tên job + queue              |
| Logs    | Các dòng log khớp                               | Một pattern, và tùy chọn level + logger context     |
| Errors  | New error groups                                | Một ứng dụng, hoặc toàn bộ project                  |
| Runtime | Event loop delay, CPU usage, memory usage       | Một ứng dụng (lấy mẫu theo từng process)            |
| Custom  | Bất kỳ custom metric nào ứng dụng của bạn báo cáo | Một tên metric, và tùy chọn một label             |
| SLO     | SLO burn rate                                   | Chính SLO đó                                        |
| Production rules | Vi phạm production rule                | Một rule, hoặc mọi rule trong một project hay ứng dụng |

**Error rate** chỉ đếm lỗi server (5xx). Một lỗi 4xx là lỗi của client - một 404 từ crawler, một 401 do session hết hạn, một lần validate thất bại - nên nó không bao giờ kích hoạt rule error rate, dù nó vẫn hiện trên các view Requests và Errors.

Mọi rule chạy theo một trong hai chế độ: **ngưỡng cố định** ("error rate trên 5%"), hoặc **anomaly detection**, kích hoạt khi metric lệch khỏi baseline gần đây của chính nó vượt quá một độ nhạy mà bạn đặt. Chế độ anomaly thường là lựa chọn tốt hơn cho các metric runtime: một ngưỡng CPU cố định phù hợp với service này lại sai với service khác, còn "khác với baseline gần đây của chính nó" thì áp dụng được cho cả hai.

Hai nhóm phụ thuộc trực tiếp vào instrumentation của SDK:

- **Phát hiện vắng mặt.** Rule **Telemetry silence** theo dõi heartbeat runtime mà sampler `runtimeMetrics` của SDK phát ra ngay cả khi ứng dụng đang rảnh, và kích hoạt khi nó im lặng lâu hơn một khoảng dung sai bạn đặt (từ 2 phút đến 7 ngày). Rule **Job silence** làm điều tương tự cho một job có tên cụ thể, ví dụ một cron đã không chạy. Cùng cơ chế này cho bạn cả việc giám sát uptime gọn nhẹ mà không cần probe bên ngoài lẫn giám sát cron. Một phạm vi chưa từng báo cáo gì sẽ không kích hoạt: "chưa tích hợp" không phải là "down".
- **Cảnh báo theo pattern log** đếm các dòng log chứa một chuỗi con trong khoảng thời gian ("báo cho tôi khi `payment declined` xuất hiện hơn 10 lần trong 15 phút"), và yêu cầu bật `forwardLogs`.

Một rule có thể thông báo qua **email**, **Slack** (incoming webhook), một **webhook** chung, một thông báo **trong ứng dụng**, hoặc bằng cách **tạo một issue** được điền sẵn mức độ nghiêm trọng và phạm vi của rule. Rule có thể có lịch tắt tiếng định kỳ cho giờ yên tĩnh, và mọi lần chuyển trạng thái (OK → Firing → Resolved) đều được ghi lại kèm trạng thái gửi theo từng kênh.

<figure><img src="https://www.observe.nestjs.com/docs/alerts/create-alert.webp" alt="Tạo cảnh báo" /></figure>

**Cảnh báo khởi đầu.** Một gói trả phí không bắt đầu trống trơn. Khi gói bắt đầu, và mỗi khi một ứng dụng được thêm vào một project mà gói đó chi trả, mỗi ứng dụng nhận được hai rule gửi email cho chủ tài khoản và hiển thị trong ứng dụng:

- **Unusual error rate** - một rule anomaly trên error rate trong 15 phút. Nó không bao giờ kích hoạt khi baseline quá mỏng để đánh giá, và chờ có 20 request cùng 5 lỗi server nhiều hơn mức bình thường của ứng dụng, nên một request lỗi đơn lẻ không phải là một cảnh báo.
- **Went quiet** - một rule telemetry silence với dung sai 15 phút, được thêm vào khi ứng dụng đã báo cáo liên tục suốt một tuần, để một chiếc laptop ngủ qua đêm không đánh thức ai cả.

Chúng là những rule bình thường: bạn có thể sửa kênh hoặc ngưỡng, tắt đi, hoặc xóa chúng. Trên gói Free, vốn không có alert rule, hai rule này được theo dõi giúp bạn: một ứng dụng chạy liên tục được kiểm tra tỉ lệ lỗi bất thường và việc im lặng, với tối đa một email cảnh báo cho mỗi tài khoản trong 30 ngày.

**Lỗi mới.** Rule *new error groups* kích hoạt khi một lỗi mà Observe chưa từng thấy xuất hiện. Nó chỉ đếm các lỗi chưa được xử lý: một group mà lần xảy ra đầu tiên trả về 5xx, hoặc lỗi ở một entry point không có HTTP status (một RPC handler, một message của gateway). Một lỗi mà code của bạn cố ý throw, chẳng hạn `NotFoundException` hay một lần validate thất bại, vẫn hiện trong view Errors nhưng không được tính là một bug mới. Mọi gói, kể cả Free, cũng có sẵn một **email lỗi mới** mà không cần tạo rule: mỗi project một email liệt kê các lỗi mới, tối đa sáu email mỗi ngày. Mỗi người có thể tự tắt nó trong **Settings → New error emails**.

#### SLO

SLO biến "error rate trên 5%" thành "chúng ta đã cam kết 99.9% và đang tiêu error budget quá nhanh". Chúng là các mục tiêu đặt trên telemetry bạn đã thu thập sẵn, nên không cần instrument thêm gì. Một SLO được xây từ ba khái niệm xếp lớp:

- **SLI (service level indicator)**: tỉ lệ sự kiện tốt trên tổng số sự kiện trong một khoảng thời gian, đo availability (request không có lỗi chưa xử lý), độ trễ (request dưới một ngưỡng bạn đặt), hoặc tỉ lệ job thành công.
- **Objective**: SLI cộng với một phần trăm mục tiêu (90-99.999%) trên một compliance window trượt dài 7, 14, 28 hoặc 30 ngày.
- **Error budget**: bạn còn bao nhiêu dư địa để trượt mục tiêu (`1 − target`), và **burn rate**, tốc độ budget đó đang bị tiêu. Burn rate bằng 1.0 nghĩa là tiêu đúng tiến độ; 14.4 nghĩa là một budget 28 ngày sẽ cạn trong khoảng hai ngày.

Một SLO cũng có thể được khai báo ngay cạnh handler mà nó bao phủ, bằng [`@Objective()`](/observability/sdk#declaring-objectives-in-code), để nó được review và quản lý phiên bản cùng với route. Một cảnh báo burn rate là một alert rule bình thường trỏ vào một SLO thay vì một metric thô. Các điểm khởi đầu điển hình là một rule fast-burn (cửa sổ 1 giờ, 14.4×), một rule slow-burn (6 giờ, 6×), và một rule trickle (3 ngày, 1×). Compliance window không thể dài hơn thời gian gói của bạn lưu giữ telemetry.
