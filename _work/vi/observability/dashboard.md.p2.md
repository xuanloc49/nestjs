#### Issue

Issue là công cụ theo dõi gọn nhẹ, trong phạm vi project, cho những việc phát sinh từ telemetry, chẳng hạn một lỗi lặp đi lặp lại đáng để sửa hoặc một regression về độ trễ cần điều tra. Bạn có thể tự tạo issue từ bất kỳ trang execution nào, chuyển một error group thành issue, hoặc để một cảnh báo đang kích hoạt tự động mở issue. Một issue liên kết tới request, lỗi, job hoặc trace mà nó bắt nguồn, nên bất kỳ ai mở nó sau này cũng có telemetry ngay trong ngữ cảnh, chứ không chỉ một đoạn mô tả về nó.

Mọi issue liên kết với telemetry đều mở đầu bằng **incident record** của nó: nó nói về cái gì (class của lỗi, route hoặc job, và alert rule đã tạo ra nó), nó bắt đầu và kết thúc khi nào, bản release mà nó xuất hiện cùng, nó ảnh hưởng tới ai - người dùng, và các công ty khách hàng đứng sau domain email của họ - và bản release đã sửa nó, tất cả trên một dòng thời gian. **Copy summary** copy toàn bộ record vào clipboard dưới dạng văn bản thuần, để dùng cho postmortem, bản cập nhật trạng thái, hoặc ghi chú gửi khách hàng.

<figure><img src="https://www.observe.nestjs.com/docs/issues/incident-record.webp" alt="Incident record" /></figure>

Một issue được chuyển từ error group cũng trả lời câu hỏi **Did a release fix this?** Chọn một bản release, và câu trả lời được đánh giá trên chính các request của bản đó, trên các route mà lỗi đã xảy ra, so với tần suất lỗi xảy ra ở đó trước đây: **Fixed**, **Not fixed**, **Too early to tell**, hoặc **Not enough data**. Nó cũng hiển thị các error group xuất hiện lần đầu trong bản release trên cùng các route, vì một bản sửa chỉ làm thay đổi chỗ lỗi được throw sẽ khiến lỗi có fingerprint mới. Các con số lấy từ các dòng request, vốn không bao giờ bị lấy mẫu, nên câu trả lời có ngay khi bản release đã phục vụ đủ nhiều request trên các route đó. Một agent đặt cùng câu hỏi đó bằng `verify_fix`.

Khi bạn đánh dấu một issue là resolved và nó chỉ tới một thứ đo lường được (một operation, phạm vi của một alert rule), dashboard sẽ theo dõi telemetry của operation đó so với baseline trước sự cố và cho bạn biết bản sửa có giữ vững không. Nó chuyển issue sang **Verifying**, rồi hoặc tự đóng issue, hoặc chuyển nó về lại **Open** kèm số liệu cho thấy bản sửa không hiệu quả. Sau 7 ngày mà không có kết luận gì - thường là do quá ít lưu lượng để đánh giá - nó sẽ báo điều đó bằng trạng thái **Unverified**, và bạn tự đóng issue. Nếu bạn ghi tên bản release chứa bản sửa (`serviceVersion` của bạn), quá trình xác minh sẽ chờ cho đến khi bản release đó xuất hiện trong telemetry.

#### Một ví dụ điều tra qua dashboard

Các view được thiết kế để dùng theo thứ tự. Một cuộc điều tra điển hình:

1. Một cảnh báo kích hoạt, hoặc biểu đồ **Requests** cho thấy p95 đang tăng.
2. Sắp xếp danh sách route theo thời lượng hoặc tỉ lệ thất bại để tìm operation nào đã thay đổi.
3. Mở operation đó. Nó liên tục hay đột biến? Nó có bắt đầu từ một lần deploy không? Kiểm tra **Releases**, và verdict của bản release đó.
4. Mở một execution đơn lẻ ở phần đuôi của phân phối, ví dụ một execution mà thẻ baseline ghi là _chậm hơn 95% số lời gọi_.
5. Đọc **waterfall**: span nào chiếm self time?
6. Nếu nó bị lỗi, hãy đọc **thẻ lỗi** - stack trace và các dòng mã nguồn quanh chỗ throw.
7. Kiểm tra **log** của trace đó, hover lên từng dòng để đối chiếu chúng với các span.
8. **Copy agent prompt** và giao toàn bộ cho một coding agent, hoặc mở một **issue** liên kết tới execution đó để người tiếp nhận bắt đầu đúng từ chỗ bạn dừng lại.

Một agent cũng có thể đi theo đúng lộ trình này qua [MCP server](/observability/mcp-server), mỗi bước một tool, khi bạn thích đặt câu hỏi hơn là click qua từng view.
