### Model-View-Controller

Mặc định, bên dưới Nest dùng library [Express](https://github.com/expressjs/express). Vì vậy, mọi kỹ thuật áp dụng pattern MVC (Model-View-Controller) trong Express cũng áp dụng được cho Nest.

Đầu tiên, scaffold một ứng dụng Nest mới bằng công cụ [CLI](https://github.com/nestjs/nest-cli):

[[CODE:1]]

Để tạo một app MVC, bạn còn cần một [template engine](https://expressjs.com/en/guide/using-template-engines.html) để render các view HTML:

[[CODE:2]]

Ví dụ này dùng engine `hbs` ([Handlebars](https://github.com/pillarjs/hbs#readme)), nhưng bạn có thể dùng bất kỳ engine nào phù hợp với yêu cầu của mình. Sau khi cài xong, cấu hình Express instance bằng đoạn code sau:

[[CODE:3]]

Đoạn code này báo cho Express biết thư mục `public` chứa các static asset, thư mục `views` chứa template, và template engine `hbs` sẽ render output HTML.

> info **Hint** Cùng các lời gọi đó hoạt động với `NodeAdapter`: hãy tạo ứng dụng với `new NodeAdapter()` và type `NestNodeApplication` thay vào đó (xem [Node adapter](/http/performance#node-adapter)). Node adapter hỗ trợ decorator `@Render()`, nhưng không hỗ trợ method `res.render()` dùng trong phần [Render template động](/http/mvc#dynamic-template-rendering) bên dưới.

#### Render template

Giờ hãy tạo thư mục `views` với một template `index.hbs` bên trong. Template này in ra một `message` được truyền từ controller:

[[CODE:4]]

Tiếp theo, mở file `app.controller` và thay nội dung của nó bằng đoạn code sau:

[[CODE:5]]

Đoạn code này chỉ định template cần dùng trong decorator `@Render()`, và giá trị trả về của method route handler được truyền vào template để render. Giá trị trả về là một object có thuộc tính `message`, khớp với placeholder `message` trong template.

Trong khi ứng dụng đang chạy, mở trình duyệt và truy cập `http://localhost:3000`. Bạn sẽ thấy dòng chữ `Hello world!`.

#### Thêm layout

Engine `hbs` hỗ trợ layout: các template bao bọc dùng chung mà từng view được render vào bên trong. Để dùng layout, hãy đặt biến local `layout` bằng method `setLocal()` (wrapper của Nest bọc quanh [app.locals](https://expressjs.com/en/5x/api.html#app.locals) của Express). Sửa đoạn code trước như sau:

[[CODE:6]]

Tiếp theo, tạo thư mục `layouts` bên trong `views` và thêm file `app.hbs` với nội dung sau:

[[CODE:7]]

Sau đó cập nhật file `index.hbs` thành:

[[CODE:8]]

Cấu trúc file kết quả trông như sau:

<div class="file-tree">
  <div class="item">views</div>
  <div class="children">
    <div class="item">layouts</div>
    <div class="children">
      <div class="item">app.hbs</div>
    </div>
    <div class="item">index.hbs</div>
  </div>
</div>

#### Render template động

Nếu logic của ứng dụng cần quyết định động template nào sẽ được render, hãy dùng decorator `@Res()` và cung cấp tên view trong route handler, thay vì trong decorator `@Render()`:

> info **Hint** Khi Nest phát hiện decorator `@Res()`, nó inject object `response` riêng của library, bạn có thể dùng object này để render template một cách động. Xem [tài liệu API của Express](https://expressjs.com/en/api.html) để tìm hiểu thêm về object `response`.

[[CODE:9]]

#### Ví dụ

Một ví dụ chạy được có sẵn trong [sample 15-mvc](https://github.com/nestjs/nest/tree/master/sample/15-mvc).

#### Fastify

Như đã nói trong chương [HTTP adapter](/http/performance), bạn có thể dùng bất kỳ HTTP provider tương thích nào với Nest. Một library như vậy là [Fastify](https://github.com/fastify/fastify). Để tạo một ứng dụng MVC với Fastify, hãy cài các package sau:

[[CODE:10]]

Các bước tiếp theo gần như giống với Express, chỉ có vài khác biệt nhỏ đặc thù của nền tảng. Sau khi cài xong, mở file `main.ts` và cập nhật nội dung của nó:

[[CODE:11]]

API của Fastify có vài điểm khác, nhưng kết quả cuối cùng của các lời gọi method này là như nhau. Một khác biệt đáng chú ý là với Fastify, tên template bạn truyền vào decorator `@Render()` phải bao gồm cả phần mở rộng của file:

[[CODE:12]]

Cách khác là dùng decorator `@Res()` để inject trực tiếp response và chỉ định view bạn muốn render, như bên dưới:

[[CODE:13]]

Trong khi ứng dụng đang chạy, mở trình duyệt và truy cập `http://localhost:3000`. Bạn sẽ thấy dòng chữ `Hello world!`.

#### Ví dụ

Một ví dụ chạy được có sẵn trong [sample 17-mvc-fastify](https://github.com/nestjs/nest/tree/master/sample/17-mvc-fastify).
