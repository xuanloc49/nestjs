### MCP server

NestJS Observe cung cấp một [MCP](https://modelcontextprotocol.io/) server, nhờ đó một client tương thích MCP (Claude Code, Claude Desktop, Cursor, VS Code, hoặc một agent bạn tự viết) có thể truy vấn trực tiếp các project của bạn, thay vì bạn phải copy dữ liệu từ dashboard vào prompt. Có sẵn các regression và những gì mỗi bản release đã thay đổi, các operation chậm, error group, trace, job, cảnh báo và production rule: cùng dữ liệu mà dashboard hiển thị, giới hạn đúng trong phạm vi những gì bạn được xem. Có hai tool được làm riêng cho một agent đang làm việc trên code của bạn: một context pack để đọc trước khi sửa, và một release verdict để đọc sau khi deploy.

MCP server có trong mọi gói trả phí (Pro trở lên). Nó đi theo gói đang chi trả cho từng project: một thành viên dùng tài khoản Free được mời vào các project của một team trả phí có thể dùng nó trên những project đó.

> info **Hint** MCP là một trong hai cách đưa telemetry tới agent. Nút **Copy agent prompt** (xem [Dashboard](/observability/dashboard#handing-a-failure-to-a-coding-agent)) đóng gói một trang thành văn bản để dán một lần. MCP dành cho một agent cần tiếp tục đặt câu hỏi (lần theo một trace, kiểm tra xem lỗi có còn đang xảy ra không) mà không cần bạn chuyển tiếp từng câu trả lời.

Endpoint giao tiếp bằng Streamable HTTP tại `POST https://observe-api.nestjs.com/mcp`. Nó là stateless: không có session nào cần mở, không có gì cần giữ kết nối, và không cần thiết lập gì ngoài chính request.

#### Kết nối một client

Chỉ cần đưa cho client URL, không cần gì khác. Lần đầu tiên client gọi, server sẽ trả lời rằng nó cần credential và chỉ chỗ lấy. Một client hỗ trợ đăng nhập OAuth của MCP - Claude Code, Claude Desktop và claude.ai, Cursor, và VS Code đều hỗ trợ - sẽ mở trình duyệt của bạn tới dashboard, bạn chấp thuận kết nối ở đó, và client tiếp tục làm việc, không cần copy, dán hay lưu token nào vào file.

**Claude Code**

[[CODE:1]]

Sau đó chạy `/mcp` bên trong Claude Code, chọn `observe`, và xác thực; trình duyệt của bạn sẽ mở trang chấp thuận.

**Claude Desktop và claude.ai**: trong **Settings → Connectors**, thêm một custom connector với URL là `https://observe-api.nestjs.com/mcp`. Kết nối nó sẽ mở trang chấp thuận.

**Cursor**: thêm URL vào `~/.cursor/mcp.json` (cho mọi project) hoặc `.cursor/mcp.json` (cho một project), và đăng nhập khi Cursor báo server cần đăng nhập:

[[CODE:2]]

**VS Code (Copilot agent mode)**: trong `.vscode/mcp.json` cho một workspace, hoặc file `mcp.json` cấp user cho mọi workspace. VS Code sẽ yêu cầu bạn đăng nhập khi server khởi động lần đầu:

[[CODE:3]]

Trang chấp thuận hiển thị tên của client (do chính client tự khai báo, nên chỉ chấp thuận kết nối mà bạn vừa tự khởi tạo), địa chỉ mà trình duyệt của bạn sẽ quay về, và tài khoản bạn đang đăng nhập. Một yêu cầu có hiệu lực trong 10 phút. Chấp thuận sẽ tạo một personal MCP token đặt theo tên client, chẳng hạn "Cursor (connected with OAuth)", và giao trực tiếp cho client; nó hoạt động với tư cách của bạn, với đúng quyền trên project của bạn, và tồn tại cho tới khi bạn thu hồi nó trong **MCP tokens**. Không có cơ chế refresh: một client có token bị thu hồi sẽ nhận `401` và yêu cầu bạn chấp thuận lại.

#### Kết nối bằng token

Với những thứ không thể mở trình duyệt - CI, một script, một agent bạn tự viết, một client không hỗ trợ đăng nhập OAuth của MCP - hãy tự tạo một token và gửi nó trong header `Authorization: Bearer <token>`.

##### Lấy token

Personal MCP token được tạo trên dashboard trong mục **MCP tokens**.

- Click **Create token**, đặt tên cho nó, và tùy chọn đặt thời hạn. Một token không có thời hạn sẽ không bao giờ hết hạn, vì các MCP client không có cơ chế refresh.
- Secret (`omcp_...`) chỉ được hiển thị **một lần**, trong response khi tạo nó. Hãy copy ngay; chỉ hash của nó được lưu lại, nên không thể lấy lại nó lần nữa. Nếu bạn làm mất, hãy thu hồi token và tạo một token khác.
- Token hoạt động **với tư cách người dùng đã tạo ra nó**, với đúng quyền trên project của người đó. Không có gì để giới hạn phạm vi: nếu bạn thấy được trên dashboard, token đọc được nó qua MCP, còn nếu bạn không thấy, token cũng không thấy.

Thu hồi một token từ cùng trang đó sẽ chặn nó ngay lập tức. Bản thân việc quản lý token được cố ý chỉ làm trên dashboard: một MCP token không thể tạo hay thu hồi MCP token, nên một credential bị lộ không thể tự kéo dài tuổi thọ của nó.

##### Cấu hình client bằng token

Bất kỳ client nào giao tiếp bằng Streamable HTTP đều kết nối được với URL và một header đó. Các client chỉ khác nhau ở vị trí file cấu hình và tên các key của nó.

**Claude Code**

[[CODE:4]]

**Claude Desktop, và các client dùng `mcpServers` khác**

[[CODE:5]]

**Cursor** dùng cùng cấu trúc `mcpServers` trong `~/.cursor/mcp.json` (cho mọi project) hoặc `.cursor/mcp.json` (cho một project), và expand `${{ '{' }}env:...{{ '}' }}` bên trong `url` và `headers`, đây là cách để giữ token ngoài một file mà bạn có thể commit:

[[CODE:6]]

**VS Code (Copilot agent mode)** dùng `servers` thay vì `mcpServers`, cần một `type` tường minh, và có thể hỏi token một lần rồi lưu nó ở dạng mã hóa. Trong `.vscode/mcp.json` cho một workspace, hoặc file `mcp.json` cấp user cho mọi workspace:

[[CODE:7]]

**Agent của riêng bạn.** Với TypeScript SDK chính thức, endpoint là một `StreamableHTTPClientTransport` và token được đặt trong `requestInit.headers`:

[[CODE:8]]

Trước khi debug cấu hình của một client, hãy xác nhận rằng endpoint và token hoạt động. Lệnh này liệt kê các tool mà server công bố:

[[CODE:9]]

Nếu bạn nhận lại danh sách tool, credential là hợp lệ và bất cứ thứ gì vẫn còn lỗi là ở phía client. **401** nghĩa là token bị thiếu, hết hạn, đã bị thu hồi, hoặc header sai định dạng. **405** nghĩa là client đã gửi `GET` hoặc `DELETE`; mọi MCP request tới endpoint này đều phải là `POST`.

#### Một ví dụ điều tra

Các tool được thiết kế xoay quanh việc điều tra chứ không theo endpoint, nên mỗi câu trả lời đều mang theo key mà câu hỏi tiếp theo cần. Giả sử vừa có một lần deploy và có vẻ có gì đó không ổn:

1. **"Có gì bị regression sau lần deploy vừa rồi?"** - `find_regressions` so sánh tỉ lệ lỗi server (5xx) và độ trễ ở hai phía của mỗi ranh giới release (các giá trị `serviceVersion` của bạn) và chỉ ra bản release đã làm mọi thứ tệ hơn, cùng các operation mà nó làm suy giảm.
2. **"Cho tôi xem operation đó."** - `get_operation_details` trả về tóm tắt độ trễ và lỗi của route cùng các request riêng lẻ gần đây, mỗi request kèm một `traceId`.
3. **"Request đó thực sự đã làm gì?"** - `get_trace` resolve trace id thành waterfall: mọi execution dưới nó, xuyên suốt các service, kèm cây span.
4. **"Code đã nói gì khi chuyện đó xảy ra?"** - `get_trace_logs` trả về mọi dòng log được ghi dưới cùng trace id, theo thứ tự.

Lỗi và background job cũng theo cấu trúc tương tự: `list_error_groups` → `get_error_details` → `get_trace`, và `list_jobs` → `get_job_details` → `get_trace`. Trong mọi trường hợp, hãy bắt đầu với `list_projects`, vì gần như mọi tool chẩn đoán đều nhận một `projectId`.

#### Trước khi sửa code, và sau khi deploy

Một agent làm việc trên chính code có hai thời điểm đáng để đặt câu hỏi:

- **Trước khi sửa**, `get_context_pack` trả về một bản tóm tắt về project vừa với context của agent: các hot path và độ trễ của chúng, các dependency hay chập chờn, SLO, và các [production rule](/observability/production-rules) mà code phải tuân theo. `get_method_impact` cho biết một method quan trọng đến mức nào - nó chạy thường xuyên ra sao, thời gian riêng, tỉ lệ lỗi, và những ứng dụng nào chạy nó - trước khi nó bị thay đổi.
- **Sau khi deploy**, `get_release_verdict` cho biết bản release đã thay đổi gì trong cách code hoạt động và liệu nó có gây regression không. Khi bản release nhằm sửa một lỗi, `verify_fix` cho biết lỗi có ngừng xảy ra trên chính các request của bản release đó không - bằng chứng để dẫn ra trước khi gọi `resolve_issue`. Sau đó `create_production_rule` pin lại những gì thay đổi đó phải tiếp tục làm.

Server nêu rõ thứ tự này trong các chỉ dẫn nó gửi khi một client kết nối, nên một agent đã kết nối sẽ tự tìm tới các tool này mà không cần được bảo.

#### Các tool có sẵn

Gần như mọi tool đều chỉ đọc; những tool ghi dữ liệu được liệt kê trong [Thiết lập một service](/observability/mcp-server#setting-up-a-service). Phần lớn tool chẩn đoán dùng chung một phạm vi: một `projectId` bắt buộc, một `applicationId` tùy chọn để thu hẹp về một service, và một khoảng thời gian nhìn lại `timeInterval` tùy chọn (`1h`, `3h`, `12h`, `1d`, `3d`, `7d`, `30d`), mặc định là `1d`.

| Tool                     | Trả lời câu hỏi gì                                                                                                                                |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `list_projects`          | Mọi project mà bạn là thành viên, kèm số team và số ứng dụng. Bắt đầu từ đây để lấy project id.                                                   |
| `get_project`            | Một project theo id, bao gồm mức quyền của bạn và trạng thái subscription.                                                                        |
| `search`                 | Tìm kiếm toàn văn trên các project, ứng dụng, alert rule, SLO và issue của bạn.                                                                   |
| `get_context_pack`       | Bản tóm tắt một project để load trước khi sửa code của nó, khoảng 2.500 token: các route và job bận rộn nhất, các method có thời gian riêng lớn nhất, các lời gọi ra ngoài và câu lệnh bị lỗi hoặc chậm, SLO, các route đã im lặng, và các production rule kèm mức độ giữ vững của từng rule trong ngày qua. Trả về dạng JSON và thêm một lần dạng markdown cho `AGENTS.md` hoặc `CLAUDE.md`. |
| `get_method_impact`      | Mức độ quan trọng của một method trước khi bạn thay đổi nó: số lời gọi mỗi phút, thời gian riêng mỗi lời gọi, tỉ lệ lỗi, ngày qua so với phần còn lại của tuần, và các ứng dụng chạy nó. Nó nhận một method, một outbound `METHOD host`, hoặc một câu lệnh như `pg SELECT orders`. |
| `find_regressions`       | Các bản release đã làm mọi thứ tệ hơn: tỉ lệ lỗi server (5xx) và độ trễ trước và sau mỗi ranh giới release, kèm các operation cụ thể mà mỗi bản làm suy giảm. |
| `get_release_verdict`    | Verdict của một bản release: nó đã thay đổi gì trong cách code hoạt động (các outbound host và câu lệnh mới thêm, các lời gọi được thực hiện nhiều hơn hoặc ít hơn, error group mới, các route đã im lặng) và liệu nó có gây regression không. |
| `diff_release`           | Các hình dạng câu lệnh, lời gọi ra ngoài và method NestJS có số lời gọi mỗi request hoặc thời gian riêng mỗi lời gọi thay đổi qua một ranh giới release: một lỗi N+1 mới, một lời gọi bên ngoài được thêm hoặc bỏ đi, một method mà code của nó chậm đi. |
| `verify_fix`             | Một bản release có sửa được một error group hay không, đánh giá trên chính các request của bản đó trên các route mà lỗi đã xảy ra: fixed, not fixed, too early to tell, hoặc not enough data. Số liệu lấy từ các dòng request, vốn không bao giờ bị lấy mẫu, và nó không ghi gì cả. |
| `list_slow_operations`   | Các HTTP operation chậm nhất trong khoảng thời gian, xếp hạng theo p95, kèm khối lượng bên cạnh, để công sức được dồn vào những gì vừa chậm _vừa_ được gọi nhiều. |
| `get_operation_details`  | Một route: tóm tắt độ trễ và lỗi cùng các request riêng lẻ gần đây, mỗi request kèm thời lượng, status và `traceId`.                               |
| `get_trace`              | Một `traceId` được resolve thành mọi execution đã chạy dưới nó - xuyên suốt các service, request và job - mỗi execution kèm cây span của nó.       |
| `get_trace_logs`         | Mọi dòng log được ghi dưới một `traceId`, theo thứ tự.                                                                                            |
| `list_error_groups`      | Các lỗi được gom theo fingerprint, xếp hạng theo số lần xảy ra, kèm class, message và stack trace mẫu, first/last seen, và bản release đã đưa lỗi vào. |
| `get_error_details`      | Các lần xảy ra gần đây của một class lỗi: message, status, người dùng và `traceId` của từng lần, cùng một bản tóm tắt.                            |
| `get_error_trend`        | Lỗi đang tăng hay giảm dần trong khoảng thời gian, đã được phân loại sẵn thành một chiều hướng.                                                    |
| `get_affected_users`     | Phạm vi ảnh hưởng của một class lỗi: những người dùng cuối nào gặp phải và bao nhiêu lần.                                                          |
| `list_jobs`              | Hiệu năng của background job trong khoảng thời gian, theo tên job và queue: khối lượng, thời lượng và số lần thất bại.                            |
| `get_job_details`        | Một tên job trên một queue: tóm tắt thời lượng và thời gian chờ cùng các lần chạy riêng lẻ gần đây, mỗi lần kèm status và `traceId`.              |
| `list_classes`, `get_class_methods` | Thời gian tiêu tốn theo từng class NestJS, như trên view **Services** (thời gian riêng, tổng thời gian, số lời gọi, lỗi), sau đó là method nào của một class nóng là method nóng. |
| `get_service_map`        | Ai gọi ai trong project: các ứng dụng, các queue mà chúng xử lý, các database mà chúng truy vấn, và các host bên ngoài mà chúng gọi, mỗi cái kèm số lời gọi, lỗi và thời lượng trung bình. |
| `list_issues`, `get_issue` | Các issue trên các project của bạn, và một issue cùng comment và hoạt động của nó.                                                              |
| `get_incident_record`    | Bản ghi mà một issue để lại: nó nói về cái gì, bắt đầu khi nào, bản release nó xuất hiện cùng, nó ảnh hưởng tới ai, bản release đã sửa nó, và quá trình xác minh diễn ra thế nào, trên một dòng thời gian. |
| `list_slos`              | Các SLO của một project kèm trạng thái hiện tại và mức tiêu error budget.                                                                          |
| `list_rule_violations`   | Các [production rule](/observability/production-rules) của một project, mức độ giữ vững của từng rule trong khoảng thời gian, và các trace đã vi phạm chúng. |
| `list_alert_rules`, `list_alert_events` | Các alert rule trên mọi project bạn xem được, và lịch sử kích hoạt của chúng.                                                       |

Ngoài việc thiết lập một service, resolve một issue và pin một production rule, không có gì có thể được tạo hay thay đổi qua MCP, kể cả alert rule, trạng thái error group và các production rule đã có. Những thứ đó vẫn ở trên dashboard. Kết quả của tool cũng bỏ qua các chuỗi dữ liệu biểu đồ chia theo bucket thời gian mà các endpoint của dashboard trả về, vì hàng trăm giá trị bucket tốn context mà lại nói được ít hơn bản tóm tắt rút ra từ chúng.

#### Thiết lập một service

Đây là những tool ghi dữ liệu. Mỗi tool đi qua cùng service với nút tương ứng trên dashboard, nên vai trò của bạn trong project và giới hạn của gói áp dụng y hệt như ở đó, và một lần bị từ chối sẽ được trả về làm câu trả lời của tool. Không có gì có thể bị xóa, đổi tên hay thu hồi qua MCP.

| Tool                 | Làm gì |
| -------------------- | ------------ |
| `list_applications`  | Các ứng dụng của một project. Hãy kiểm tra nó trước khi tạo một bản trùng lặp. |
| `create_project`     | Tạo một project, trong một team đã có (truyền id của team) hoặc một team mới đặt theo tên project. |
| `create_application` | Đăng ký một service NestJS trong một project. Tên không thể đổi qua MCP và nên khớp với `serviceId` bạn truyền cho SDK. |
| `create_api_key`     | Cấp cặp key mà SDK dùng để xác thực. Secret chỉ được trả về một lần; một client đúng mực sẽ ghi nó vào file biến môi trường đã được git-ignore của bạn và không lặp lại nó. |
| `resolve_issue`      | Đánh dấu một issue là resolved sau khi bản sửa được ship, việc này bắt đầu quá trình xác minh so với baseline trước sự cố. |
| `create_production_rule` | Pin một [production rule](/observability/production-rules) lên một operation: mỗi request hoặc job được phép gọi gì, và bao nhiêu lần. Nó cần quyền Write và gói trả phí; việc sửa và xóa rule vẫn thực hiện trên dashboard. |

Với các tool này, một agent có thể đưa một repository từ trạng thái "chưa instrument" sang "đang báo cáo" chỉ trong một yêu cầu: *"Thiết lập NestJS Observe cho service này"* trở thành `list_projects` → `create_application` → `create_api_key`, tiếp theo là bước cài đặt và ba chỗ sửa code từ [hướng dẫn SDK](/observability/sdk).
