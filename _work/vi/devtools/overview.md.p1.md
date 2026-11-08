### Tổng quan

> info **Hint** Chương này nói về việc tích hợp Nest Devtools với framework Nest. Nếu bạn đang tìm ứng dụng Devtools, hãy truy cập website [Devtools](https://devtools.nestjs.com).

Nest Devtools cho bạn một góc nhìn tương tác, luôn cập nhật về phần bên trong ứng dụng: module, provider, controller, cùng các route và event kết nối chúng với nhau. Thay vì tự ghép bức tranh đó từ các import và chữ ký constructor, bạn có một đồ thị trực tiếp để tìm kiếm, lọc và click qua lại. Chương này hướng dẫn bạn kết nối ứng dụng local với Devtools lần đầu tiên.

Bắt đầu mất chưa tới năm phút. Mở file `main.ts` và đặt thuộc tính `snapshot` thành `true` trong object tùy chọn của ứng dụng:

[[CODE:1]]

Điều này bảo Nest thu thập metadata mà Devtools cần để dựng lại và trực quan hóa đồ thị dependency của ứng dụng.

Tiếp theo, cài package tích hợp Devtools:

[[CODE:2]]

Khi đã cài package, mở `app.module.ts` và import `DevtoolsModule`:

[[CODE:3]]

> info **Note** Ở đây chúng ta kiểm tra `NODE_ENV` vì `DevtoolsModule` không bao giờ nên chạy trên production.

Flag `http` quyết định `DevtoolsModule` có khởi động introspection server hay không. Khi tắt flag, module không expose gì cả, đây chính là lớp bảo vệ bạn cần nếu cấu hình này vô tình lọt qua review. Chi phí lúc runtime không đáng kể: khi bật `snapshot`, Nest chỉ thu thập metadata của đồ thị một lần, lúc ứng dụng bootstrap, nên việc xử lý request thông thường của ứng dụng không bị ảnh hưởng.

Khi đã import `DevtoolsModule` và ứng dụng đang chạy (`npm run start:dev`), hãy mở [Devtools](https://devtools.nestjs.com) để xem đồ thị đã được introspect.

<figure><img src="/assets/devtools/modules-graph.png" /></figure>

> info **Hint** Mọi module đều kết nối với `InternalCoreModule`, một global module mà Nest luôn import vào root module. Vì nó được đăng ký global, Nest vẽ một cạnh nối giữa nó và mọi module khác trong ứng dụng. Để màn hình gọn hơn, hãy tick checkbox **Hide global modules** ở sidebar.

Bên dưới, `DevtoolsModule` khởi động một HTTP server nhẹ (mặc định ở port 8000) mà dashboard dùng để introspect ứng dụng của bạn theo thời gian thực. Không cần cấu hình thêm gì. Nếu port 8000 đã bị chiếm, hãy truyền port khác qua tùy chọn `port` của `DevtoolsModule.register()`.

Để xác nhận mọi thứ đã được kết nối đúng, hãy chuyển chế độ xem đồ thị sang "Classes". Bạn sẽ thấy thứ gì đó như thế này:

<figure><img src="/assets/devtools/classes-graph.png" /></figure>

Click vào node bất kỳ để mở một popup với nút **"Focus"** để tách riêng node đó trên đồ thị, hoặc dùng thanh tìm kiếm ở sidebar để nhảy tới một node cụ thể.

> info **Hint** Click **Inspect** sẽ đưa bạn tới trang `/debug` với node đó được chọn sẵn, rất tiện khi cần đào sâu vào một provider hay controller cụ thể.

<figure><img src="/assets/devtools/node-popup.png" /></figure>

> info **Hint** Cần một ảnh chụp cho tài liệu hoặc pull request? Click **Export as PNG** ở góc dưới bên phải của đồ thị.

Các control ở sidebar cho phép bạn thu hẹp độ gần của các cạnh, giúp bạn zoom vào một nhánh cụ thể của ứng dụng:

<figure><img src="/assets/devtools/subtree-view.png" /></figure>

Đây là một cách tuyệt vời để onboard **thành viên mới** bằng cách cho họ thấy chính xác các phần của ứng dụng khớp với nhau thế nào. Nó cũng hữu ích không kém khi bạn tách một module (ví dụ `TasksModule`) cùng mọi dependency của nó trước khi chia một ứng dụng lớn thành các service nhỏ hơn.

Mọi thứ trong Graph Explorer luôn đồng bộ với ứng dụng đang chạy: chỉ cần refresh, mọi thay đổi bạn đã làm với module hay provider đều được phản ánh ngay lập tức. Không có bước build hay tài liệu riêng nào cần cập nhật; đồ thị **chính là** tài liệu.

Xem **Graph Explorer** hoạt động:

<figure>
  <iframe
    width="1000"
    height="565"
    src="https://www.youtube.com/embed/bW8V-ssfnvM"
    title="YouTube video player"
    frameBorder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowFullScreen
  ></iframe>
</figure>

#### Debug lỗi "Cannot resolve dependency"

> info **Note** Có từ `@nestjs/core` 9.3.10 trở lên.

Nếu bạn đã làm việc với Nest một thời gian, có lẽ bạn đã gặp lỗi **"Cannot resolve dependency"**. Đây thường là lỗi đầu tiên mà một thành viên mới trong team gặp phải, và trên một ứng dụng lớn, nó có thể khó lần ra: stack trace cho bạn biết cái gì bị thiếu, nhưng không cho biết tại sao, hay chỗ nào trong một chuỗi provider lồng nhau sâu đã bị đứt. Devtools biến việc này từ một trò đoán mò thành một lần chẩn đoán nhanh và trực quan.

Bắt đầu bằng cách cập nhật lời gọi `bootstrap()` trong `main.ts`:

[[CODE:4]]

> info **Hint** `PartialGraphHost` được export từ `@nestjs/core`, còn `writeFileSync` từ `node:fs`.

Bạn cũng cần đặt `abortOnError` thành `false`:

[[CODE:5]]

Từ giờ, mỗi khi ứng dụng bootstrap thất bại với lỗi **"Cannot resolve dependency"**, nó sẽ ghi một file `graph.json` (một đồ thị một phần) vào thư mục gốc của project. Hãy kéo thả file này vào Devtools (chuyển từ chế độ "Interactive" sang "Preview" trước) để thấy chính xác chỗ nào đã hỏng:

<figure><img src="/assets/devtools/drag-and-drop.png" /></figure>

Sau khi upload, bạn sẽ thấy đồ thị cùng một hộp thoại tóm tắt những gì đã xảy ra:

<figure><img src="/assets/devtools/partial-graph-modules-view.png" /></figure>

`TasksModule` được highlight là module cần kiểm tra, và hộp thoại gợi ý cho bạn cách sửa.

Chuyển sang chế độ xem "Classes" sẽ cho thấy toàn bộ câu chuyện:

<figure><img src="/assets/devtools/partial-graph-classes-view.png" /></figure>

Đồ thị cho thấy rõ: `DiagnosticsService`, thứ mà `TasksService` phụ thuộc vào, không có sẵn trong context của `TasksModule`. Cách sửa là import `DiagnosticsModule` vào `TasksModule`.

Thứ lẽ ra là một quá trình chậm chạp, tự lần theo các import qua nhiều file và hy vọng không bỏ sót file nào, giờ chỉ còn vài cú click. Đây là một thay đổi nhỏ trong quy trình làm việc, nhưng lợi ích cộng dồn nhanh trên một codebase có hàng chục module.

#### Routes explorer

Trang **Routes explorer** hiển thị mọi entrypoint mà ứng dụng của bạn đăng ký:

<figure><img src="/assets/devtools/routes.png" /></figure>

> info **Hint** Trang này không chỉ giới hạn ở HTTP route. Nó còn bao gồm WebSocket, gRPC, GraphQL resolver, và nhiều thứ khác.

Các entrypoint được nhóm theo controller chứa chúng, và bạn có thể dùng thanh tìm kiếm để nhảy tới entrypoint cần tìm.

Click vào entrypoint bất kỳ để thấy **một flow graph** của toàn bộ đường thực thi: mọi guard, interceptor và pipe được gắn với route đó. Đây là cách nhanh nhất để hiểu một request đi qua ứng dụng thế nào, hoặc để tìm ra tại sao một guard, interceptor hay pipe cụ thể không chạy khi bạn mong đợi.

Chế độ xem này phát huy tác dụng nhất với những ứng dụng phát triển tự phát, nơi cùng một guard có thể được áp dụng ở cấp controller ở chỗ này và theo từng route ở chỗ khác. Thay vì đọc qua các decorator rải rác khắp codebase, bạn có được thứ tự thực thi thực tế, đã được resolve, cho route đó.

#### Playground

Để chạy code trên ứng dụng của bạn mà không cần deploy lại, hãy mở trang **Playground**:

<figure><img src="/assets/devtools/sandbox.png" /></figure>

Playground cho phép bạn test và debug endpoint **theo thời gian thực**, nên bạn có thể truy vết vấn đề mà không cần tới một HTTP client riêng. Bạn có thể bỏ qua hoàn toàn lớp xác thực, không cần thêm bước đăng nhập hay một tài khoản test riêng. Với các ứng dụng hướng sự kiện, bạn có thể kích hoạt event trực tiếp từ Playground để thấy chính xác ứng dụng phản hồi thế nào.

Mọi thứ code của bạn log ra đều được stream tới console của Playground, nên bạn luôn biết chuyện gì đang diễn ra bên dưới.

Chạy code **ngay lập tức** và thấy kết quả tức thì, không cần build lại và không cần restart server.

> info **Hint** Các request của Playground được xác thực bằng một sandbox session token. `DevtoolsModule` sinh một token mới mỗi lần ứng dụng khởi động và in nó ra console (`Sandbox session token: ...`). Hãy cung cấp token này cho Devtools để chạy code trong Playground.

<figure><img src="/assets/devtools/sandbox-table.png" /></figure>

> info **Hint** Dùng `console.table()` (hoặc `table()`) để in đẹp một mảng object.

Xem **Playground** hoạt động:

<figure>
  <iframe
    width="1000"
    height="565"
    src="https://www.youtube.com/embed/liSxEN_VXKM"
    title="YouTube video player"
    frameBorder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowFullScreen
  ></iframe>
</figure>

#### Phân tích hiệu năng bootstrap

Để tìm ra điều gì đang làm chậm quá trình khởi động ứng dụng, hãy mở trang **Bootstrap performance**. Nó liệt kê mọi class node (controller, provider, enhancer, và nhiều thứ khác) cùng thời gian khởi tạo của chúng:

<figure><img src="/assets/devtools/bootstrap-performance.png" /></figure>

Đây là cách nhanh nhất để phát hiện những phần chậm nhất trong quá trình bootstrap. Điều này quan trọng nhất khi thời gian khởi động nằm trên critical path, như trong môi trường serverless nơi từng mili giây đều đáng kể.

Bootstrap chậm thường có vài nguyên nhân phổ biến: công việc đồng bộ nặng bên trong constructor, một provider await một lời gọi ra bên ngoài chậm trong `onModuleInit`, hoặc một module khởi tạo nhiều dependency hơn hẳn mức nó cần. Khi được sắp xếp theo thời gian khởi tạo, trang này khiến những điểm bất thường đó lộ rõ ngay, mà không cần rải các lời gọi `console.time()` khắp codebase.

#### Audit

Devtools tự động phân tích đồ thị đã serialize và đưa ra các lỗi, cảnh báo và gợi ý đáng để bạn chú ý. Bạn sẽ thấy chúng ở trang **Audit**:

<figure><img src="/assets/devtools/audit.png" /></figure>

> info **Hint** Ảnh chụp màn hình ở trên chỉ cho thấy một vài ví dụ trong số các audit rule có sẵn.

Hãy coi nó như một linter cho kiến trúc ứng dụng: một cách nhanh để bắt vấn đề trước khi vấn đề bắt được bạn. Một số rule có sẵn đánh dấu những vấn đề mà nếu không bạn sẽ phát hiện ra theo cách khó khăn: một controller chứa nhiều route hơn hẳn các controller khác, một module kéo vào số lượng dependency lớn bất thường, một provider tên `SomethingGuard` nhưng chưa bao giờ được đăng ký làm guard, hoặc một request-scoped provider rất nên chuyển thành [durable provider](/fundamentals/injection-scopes#durable-providers). Bộ test của bạn sẽ không bắt được những thứ này, nhưng chúng chính là loại vấn đề khiến codebase chậm dần theo thời gian.

#### Xem trước file tĩnh

Để lưu một đồ thị đã serialize ra file, hãy dùng code sau:

[[CODE:6]]

> info **Hint** `SerializedGraph` được export từ `@nestjs/core`.

Sau đó kéo thả (hoặc upload) file:

<figure><img src="/assets/devtools/drag-and-drop.png" /></figure>

Cách này hữu ích khi bạn muốn chia sẻ một đồ thị với đồng nghiệp, đính kèm nó vào một bug report, hoặc phân tích offline mà không cần chạy ứng dụng.
