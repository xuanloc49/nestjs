### Production rules

Một production rule quy định những gì một request hoặc job được phép làm, chẳng hạn nó chạy bao nhiêu query hay gọi model bao nhiêu lần, và NestJS Observe kiểm tra mọi trace được giữ lại theo rule đó.

Có những bug không bao giờ throw. Một lần retry trừ tiền thẻ hai lần, một relation mới load từng dòng cho mỗi sản phẩm, một agent loop gọi model bốn mươi lần - mọi request đều trả về `200`, mọi test đều pass, và dashboard vẫn xanh cho tới khi hóa đơn, độ trễ, hoặc một khách hàng lên tiếng.

Một **production rule** ghi lại những gì một request hoặc job được phép làm - "checkout trừ tiền qua payment provider đúng một lần", "danh sách sản phẩm chạy tối đa ba query", "không request nào gọi LLM quá năm lần" - và mọi trace được giữ lại đều được kiểm tra theo rule ngay khi nó tới. Trace vi phạm rule, và bản release mà nó đến từ, hiện ra trước mắt bạn ngay khi chuyện xảy ra. Khi thay đổi do một coding agent viết, một rule là cách review rẻ nhất: một câu mô tả những gì production phải tiếp tục làm, được kiểm tra trên mỗi lần deploy mà không cần ai đọc lại diff.

Rule không cần instrument thêm gì: chúng đọc các span mà [SDK](/observability/sdk) đã ghi lại sẵn - các method của bạn, các span database query và outbound HTTP của agent, và các lời gọi LLM. Chúng có trong mọi gói trả phí, tối đa 25 rule mỗi project, trong mục **Activity → Rules** của dashboard. Thành viên có quyền **Write** hoặc **Admin** có thể tạo và sửa chúng; thành viên **Read** thì xem được. Nếu một gói hết hạn, các rule của nó vẫn được giữ nhưng không còn được kiểm tra, và việc kiểm tra sẽ tiếp tục khi project quay lại gói trả phí.

#### Những rule đáng viết

| Điều phải đảm bảo               | Rule                                                                 | Vi phạm thường có nghĩa là                                            |
| ------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Một lần thanh toán chỉ trừ tiền một lần | `POST /checkout/:orderId/pay` calls `POST api.stripe.com` exactly once | Một lần retry hoặc một handler bị lặp đã trừ tiền hai lần, hoặc một lần refactor khiến việc trừ tiền không còn diễn ra |
| Danh sách sản phẩm không bị N+1 | `GET /products` runs `pg SELECT products` at most 3 times            | Một relation giờ bị load một lần cho mỗi dòng                         |
| Một endpoint vẫn rẻ khi chạy    | Every request makes LLM calls at most 5 times                        | Một tool hoặc agent loop cứ liên tục gọi model                        |
| Thay đổi của admin được audit   | `PATCH /admin/users/:id` calls `AuditLogService.record` at least once | Một đường code mới bỏ qua việc ghi audit                              |
| Một job gửi một bản digest      | The `send-digest` job calls `POST api.postmarkapp.com` exactly once  | Một job được retry sau khi thất bại một phần, gửi mail cho mọi người hai lần |

Những rule tốt nhất đến từ một thay đổi bạn vừa làm: nó phải tiếp tục làm gì? Một rule được viết khi bạn còn nhớ câu trả lời sẽ tiếp tục buộc production tuân theo nó rất lâu sau khi diff đã bị lãng quên.

#### Một rule nói gì

Một rule đọc lên như một câu, và form trên dashboard hiển thị câu đó ngay khi bạn viết:

- **Operation**: một route và method (`POST /checkout/:orderId/pay`), một job theo tên, hoặc mọi request hay mọi job. Một route chưa từng được phục vụ cũng không sao: rule sẽ ở trạng thái **Unchecked** cho tới khi có một trace được giữ lại của route đó.
- **Những gì nó đếm** trong mỗi execution:
  - **Lời gọi tới một class hoặc method**: một method của provider như `PaymentsService.charge`, hoặc một câu lệnh của driver như `pg SELECT orders`, đặt tên theo cách view **Services** đặt tên chúng.
  - **Lời gọi HTTP ra ngoài tới một host**: `api.stripe.com`, tùy chọn kèm một method. Một host được đặt tên mà không có port sẽ khớp với host đó trên mọi port.
  - **Lời gọi LLM**: mọi lời gọi model, hoặc chỉ của một provider (OpenAI, Anthropic, Azure OpenAI và các provider khác, hoặc một gateway mà bạn đã cấu hình).
- **Giới hạn**: đúng bằng, tối đa, hoặc tối thiểu một số lần cho mỗi execution.

Giới hạn trên (đúng bằng, tối đa) áp dụng cho mọi execution, kể cả những execution bị lỗi. Giới hạn dưới (đúng bằng, tối thiểu) chỉ áp dụng cho những execution thành công - không có lỗi, status dưới `400` - vì một request bị lỗi giữa chừng chưa có cơ hội thực hiện các lời gọi của nó.

Chỉ những span do SDK tự ghi lại mới được đếm; các span bạn tự mở bằng [`TracerService`](/observability/manual-instrumentation) thì không bao giờ được đếm. Khi một method thực hiện hơn 20 lời gọi giống hệt nhau, SDK giữ lại vài lời gọi chậm nhất và gộp phần còn lại vào một span duy nhất (xem `spanCollapse` trong [tài liệu tham khảo cấu hình](/observability/sdk#full-configuration-reference)). Rule đếm các lời gọi bị gộp theo số lượng thật của chúng, nên một lỗi N+1 năm mươi query sẽ được tính là năm mươi.

<figure><img src="https://www.observe.nestjs.com/docs/rules/rules.webp" alt="Production rule" /></figure>

#### Viết rule ngay tại chỗ có bằng chứng

Bạn có thể viết một rule từ đầu trong **Activity → Rules**, nhưng có hai lối tắt giúp tạo rule từ chính telemetry gợi ý ra nó:

- **Pin as a rule**, trên trang **Releases**. Mỗi query, lời gọi ra ngoài hoặc method mà một bản release mới thêm vào, hoặc giờ được gọi thường xuyên hơn, sẽ mở form với lời gọi đó và một giới hạn khởi đầu lấy từ số liệu của bản release. Route được để cho bạn chọn, vì số liệu của bản release là trung bình trên mọi request.
- **Guard with a rule**, trong waterfall của một trace. Một loạt lời gọi mà SDK đã gộp vào một span - hình dạng của một lỗi N+1 - sẽ mở form đã điền sẵn route hoặc job của chính trace đó, lời gọi, và giới hạn tối đa 3.

Không cái nào lưu lại gì cho tới khi bạn nhấn **Create**.

#### Kiểm tra trên các trace được giữ lại

Rule được trace worker kiểm tra trên các trace mà nó giữ lại, kể từ thời điểm rule được lưu - không bao giờ trên các trace trước đó. Các chỉnh sửa và việc bật tắt có hiệu lực trong khoảng 30 giây. Điều đó có ý nghĩa gì với các con số:

- **Một vi phạm là chắc chắn.** Đó là một execution đã thực sự xảy ra, và trace của nó chỉ cách một click.
- **Một rule được giữ vững là bằng chứng, không phải chứng minh.** Khi [spend control](/observability/overview#subscribing) lấy mẫu span, lỗi server và các trace chậm hơn một giây luôn được giữ lại, phần còn lại được giữ theo tỉ lệ keep rate, nên các trace được kiểm tra nghiêng về phía các trace chậm và bị lỗi.
- **Số đếm là số trace được kiểm tra, không phải số request.** Một tỉ lệ trên số trace được kiểm tra không phải là tỉ lệ trên số request.
- **Một khoảng thời gian bị thưa dữ liệu sẽ được báo rõ.** Vào một ngày có ít trace được giữ lại hơn bình thường, rule chỉ được kiểm tra trên những trace đó, và trang của rule sẽ hiện cảnh báo phía trên các con số.

Mỗi rule hiển thị trạng thái của nó cho khoảng thời gian bạn chọn (24 giờ qua hoặc 7 ngày qua):

| Status    | Ý nghĩa                                                           |
| --------- | ----------------------------------------------------------------- |
| Violated  | Có ít nhất một trace được kiểm tra đã vi phạm rule trong khoảng thời gian đó |
| Holding   | Đã được kiểm tra, và chưa bao giờ bị vi phạm                      |
| Unchecked | Không có trace nào được giữ lại của operation đó, nên rule chưa được đánh giá |
| Disabled  | Đã tắt; các số đếm là từ trước đó                                 |

Trang riêng của một rule liệt kê các trace mới nhất đã vi phạm nó, mỗi trace mở ra waterfall của nó, cùng số lần kiểm tra và vi phạm theo từng bản release, kèm thời điểm mỗi phiên bản bắt đầu và ngừng vi phạm - bản release nào làm hỏng rule thường là câu hỏi đầu tiên.

<figure><img src="https://www.observe.nestjs.com/docs/rules/rule.webp" alt="Trang của một production rule" /></figure>

#### Cảnh báo cho một rule

Bật **Alert me when this rule breaks** khi bạn tạo một rule, và một cảnh báo sẽ được tạo cùng với nó: nhiều hơn 0 vi phạm trong một giờ, mức độ High, thông báo trong ứng dụng và qua email. Nó kích hoạt ở trace vi phạm đầu tiên và resolve một giờ sau trace vi phạm cuối cùng, một lần cho mỗi đợt thay vì một lần cho mỗi request. Bất kỳ [alert rule](/observability/dashboard#alerts) nào cũng có thể theo dõi metric **Production rule violations**, cho một rule hoặc cho mọi rule trong một project hay ứng dụng.

#### Từ một coding agent

Qua [MCP server](/observability/mcp-server), trên mọi gói trả phí, `create_production_rule` cho phép agent vừa ship một thay đổi pin lại những gì production phải tiếp tục làm khi nó vẫn còn nhớ, và `list_rule_violations` đọc cùng báo cáo mà dashboard hiển thị. Việc sửa và xóa rule vẫn thực hiện trên dashboard.

Agent không cần được báo là có rule. Các chỉ dẫn mà server gửi khi một client kết nối nêu tên `create_production_rule` là thao tác ghi nên dùng sau khi ship một thay đổi, `get_context_pack` liệt kê các rule của project và mỗi rule đã giữ vững ra sao trong ngày qua, và khi một bản release thêm một lời gọi ra ngoài hoặc một câu lệnh, hoặc gọi chúng thường xuyên hơn, `get_release_verdict` sẽ kết thúc bằng một dòng cho biết điều gì đáng để pin.

> info **Hint** Một rule chỉ đọc các trace mà SDK đã gửi sẵn. Cả dashboard lẫn agent đều không thể dùng rule để mở rộng phạm vi những gì SDK ghi lại.
