### CLI Plugin

Hệ thống metadata reflection của [TypeScript](https://www.typescriptlang.org/docs/handbook/decorators.html) có một số hạn chế. Chẳng hạn, nó không thể xác định một class gồm những thuộc tính nào, hay một thuộc tính là tùy chọn hay bắt buộc. Tuy nhiên, một số ràng buộc này có thể được giải quyết lúc biên dịch. Nest cung cấp một plugin cải tiến quá trình biên dịch TypeScript để giảm lượng code boilerplate cần viết.

> info **Hint** Plugin này là **tùy chọn bật thêm (opt-in)**. Nếu muốn, bạn có thể tự khai báo mọi decorator, hoặc chỉ khai báo những decorator cụ thể ở nơi bạn cần.

#### Tổng quan

Swagger plugin tự động:

- chú thích mọi thuộc tính của DTO bằng `@ApiProperty()`, trừ khi có dùng `@ApiHideProperty()`
- đặt thuộc tính `required` tùy vào dấu chấm hỏi (ví dụ `name?: string` sẽ đặt `required: false`)
- đặt thuộc tính `type` hoặc `enum` tùy vào type (mảng cũng được hỗ trợ)
- đặt thuộc tính `default` dựa trên giá trị mặc định được gán
- đặt một số quy tắc validation dựa trên các decorator của `class-validator` (nếu `classValidatorShim` được đặt thành `true`)
- thêm một decorator response cho mọi endpoint với status và `type` (response model) phù hợp
- sinh mô tả cho các thuộc tính và endpoint dựa trên comment (nếu `introspectComments` được đặt thành `true`)
- sinh giá trị ví dụ cho các thuộc tính dựa trên comment (nếu `introspectComments` được đặt thành `true`)

Để plugin phân tích một file DTO, tên file của nó **phải có** một trong các hậu tố sau: `['.dto.ts', '.entity.ts']` (ví dụ `create-user.dto.ts`).

Nếu bạn dùng một hậu tố khác, hãy điều chỉnh hành vi của plugin bằng tùy chọn `dtoFileNameSuffix` (xem bên dưới).

Không có plugin, việc cung cấp trải nghiệm tương tác với Swagger UI đồng nghĩa với việc lặp lại rất nhiều code để cho package biết các model/component của bạn nên được khai báo thế nào trong đặc tả. Ví dụ, bạn có thể định nghĩa một class `CreateUserDto` đơn giản như sau:

[[CODE:1]]

Dù đây không phải vấn đề lớn với các project cỡ vừa, nó trở nên dài dòng và khó bảo trì khi bạn có một tập class lớn.

Khi [bật Swagger plugin](/openapi/cli-plugin#using-the-cli-plugin), bạn có thể khai báo class ở trên mà không cần decorator nào:

[[CODE:2]]

> info **Note** Swagger plugin suy ra các chú thích `@ApiProperty()` từ type của TypeScript và các decorator của `class-validator`, những thứ mô tả API của bạn trong tài liệu Swagger UI được sinh ra. Tuy nhiên, validation lúc runtime vẫn do các decorator của `class-validator` đảm nhận, nên bạn phải tiếp tục dùng các validator như `IsEmail()`, `IsNumber()`, v.v.

Nói cách khác, nếu bạn dựa vào các chú thích tự động cho tài liệu và vẫn muốn validation lúc runtime, bạn vẫn cần các decorator của `class-validator`.

> info **Hint** Khi bạn dùng [các tiện ích mapped type](/openapi/mapped-types) (như `PartialType`) trong DTO, hãy import chúng từ `@nestjs/swagger` thay vì `@nestjs/mapped-types` để plugin nhận được schema.

Plugin thêm các decorator phù hợp ngay trong lúc biên dịch, dựa trên **cây cú pháp trừu tượng (Abstract Syntax Tree)**, nên bạn không phải rải decorator `@ApiProperty()` khắp code.

> info **Hint** Plugin sinh mọi thuộc tính Swagger còn thiếu. Để ghi đè một thuộc tính, hãy đặt nó một cách tường minh qua `@ApiProperty()`.

#### Đọc comment

Khi bật tính năng đọc comment, CLI plugin sinh mô tả và giá trị ví dụ cho các thuộc tính dựa trên comment.

Ví dụ, xét thuộc tính `roles`:

[[CODE:3]]

Bạn phải lặp lại cả phần mô tả lẫn giá trị ví dụ. Khi bật `introspectComments`, CLI plugin lấy các comment này và tự động cung cấp mô tả (và ví dụ, nếu có định nghĩa) cho các thuộc tính. Khi đó thuộc tính ở trên có thể được khai báo như sau:

[[CODE:4]]

Các tùy chọn plugin `dtoKeyOfComment` và `controllerKeyOfComment` tùy chỉnh cách plugin gán giá trị comment cho decorator `ApiProperty` và `ApiOperation` tương ứng. Xem ví dụ bên dưới:

[[CODE:5]]

Đoạn này tương đương với:

[[CODE:6]]

> info **Hint** Với model, logic tương tự được áp dụng, nhưng với decorator `ApiProperty` thay vào đó.

Với controller, bạn có thể cung cấp không chỉ summary mà còn description (remarks), tag (như `@deprecated`), và ví dụ response, như thế này:

[[CODE:7]]

Từ `@nestjs/swagger` v12, plugin (khi bật `introspectComments`) cũng nhận các tag `@param`, nên mô tả của route parameter có thể lấy từ cùng doc comment:

[[CODE:8]]

Plugin thêm một `description` vào `@ApiQuery()` mà nó đã sinh cho các parameter `@Query()` tùy chọn, sinh `@ApiQuery({{ '{' }} name, description &#125;)` cho các query parameter bắt buộc có tài liệu, và sinh `@ApiParam({{ '{' }} name, description &#125;)` cho các parameter `@Param()` có tài liệu.

Mô tả được khớp theo **tên biến**, chính là thứ mà `@param` mô tả. Vì vậy `@Query('order_by') orderBy: string` được mô tả là `@param orderBy ...`, không phải `@param order_by ...`. Các decorator `@ApiQuery()` / `@ApiParam()` tường minh luôn được ưu tiên và không bao giờ bị ghi đè.

#### Dùng CLI plugin

Để bật plugin, hãy mở `nest-cli.json` (nếu bạn dùng [Nest CLI](/cli/overview)) và thêm cấu hình `plugins` sau:

[[CODE:9]]

Dùng thuộc tính `options` để tùy chỉnh hành vi của plugin:

[[CODE:10]]

Thuộc tính `options` nhận các tùy chọn sau (cùng một số tùy chọn khác):

[[CODE:11]]

<table>
  <tr>
    <th>Tùy chọn</th>
    <th>Mặc định</th>
    <th>Mô tả</th>
  </tr>
  <tr>
    <td><code>dtoFileNameSuffix</code></td>
    <td><code>['.dto.ts', '.entity.ts']</code></td>
    <td>Hậu tố của các file DTO (Data Transfer Object)</td>
  </tr>
  <tr>
    <td><code>controllerFileNameSuffix</code></td>
    <td><code>['.controller.ts']</code></td>
    <td>Hậu tố của các file controller</td>
  </tr>
  <tr>
    <td><code>classValidatorShim</code></td>
    <td><code>true</code></td>
    <td>Nếu đặt thành <code>true</code>, plugin tái sử dụng các decorator validation của <code>class-validator</code> (ví dụ <code>@Max(10)</code> thêm <code>max: 10</code> vào định nghĩa schema)</td>
  </tr>
  <tr>
    <td><code>classTransformerShim</code></td>
    <td><code>false</code></td>
    <td>Nếu đặt thành <code>true</code>, plugin bỏ qua các thuộc tính được gắn <code>@Exclude()</code> của <code>class-transformer</code>. Nếu đặt thành <code>'exclusive'</code>, nó chỉ mô tả các thuộc tính được gắn <code>@Expose()</code> hoặc <code>@ApiProperty()</code></td>
  </tr>
  <tr>
    <td><code>dtoKeyOfComment</code></td>
    <td><code>'description'</code></td>
    <td>Key thuộc tính dùng để đặt nội dung comment trên <code>ApiProperty</code>.</td>
  </tr>
  <tr>
    <td><code>controllerKeyOfComment</code></td>
    <td><code>'summary'</code></td>
    <td>Key thuộc tính dùng để đặt nội dung comment trên <code>ApiOperation</code>.</td>
  </tr>
  <tr>
    <td><code>introspectComments</code></td>
    <td><code>false</code></td>
    <td>Nếu đặt thành <code>true</code>, plugin sinh mô tả và giá trị ví dụ cho các thuộc tính dựa trên comment</td>
  </tr>
  <tr>
    <td><code>skipAutoHttpCode</code></td>
    <td><code>false</code></td>
    <td>Tắt việc tự động thêm <code>@HttpCode()</code> trong controller</td>
  </tr>
  <tr>
    <td><code>skipDefaultValues</code></td>
    <td><code>false</code></td>
    <td>Nếu đặt thành <code>true</code>, plugin không đặt thuộc tính <code>default</code> từ giá trị khởi tạo của thuộc tính</td>
  </tr>
  <tr>
    <td><code>autoFillEnumName</code></td>
    <td><code>false</code></td>
    <td>Nếu đặt thành <code>true</code>, plugin đặt <code>enumName</code> bằng tên của enum type cho các thuộc tính enum không khai báo nó</td>
  </tr>
  <tr>
    <td><code>esmCompatible</code></td>
    <td>Phát hiện theo từng file</td>
    <td>Làm code được sinh ra tương thích với ESM (<code>&#123; "type": "module" &#125;</code>). Khi bỏ qua, plugin phát hiện xem mỗi file có được phát ra dưới dạng ESM không dựa trên tùy chọn trình biên dịch và <code>package.json</code> của bạn</td>
  </tr>
</table>

Hãy xóa thư mục `/dist` và build lại ứng dụng mỗi khi bạn cập nhật tùy chọn của plugin.

Nếu bạn không dùng CLI mà có cấu hình `webpack` tùy chỉnh, bạn có thể dùng plugin này kết hợp với `ts-loader`:

[[CODE:12]]

#### SWC builder

Với cách thiết lập tiêu chuẩn (không phải monorepo), dùng CLI plugin với SWC builder yêu cầu bật type checking, như mô tả trong [recipe SWC](/recipes/swc#type-checking).

[[CODE:13]]

Với cách thiết lập monorepo, hãy làm theo hướng dẫn [monorepo và CLI plugin](/recipes/swc#monorepo-and-cli-plugins) để tạo một file `generate-metadata.ts`, rồi chạy nó:

[[CODE:14]]

Sau đó load file metadata đã được serialize bằng method `SwaggerModule#loadPluginMetadata()`, như bên dưới:

[[CODE:15]]

#### Tích hợp với `ts-jest` (e2e test)

Để chạy e2e test, `ts-jest` biên dịch các file mã nguồn ngay lập tức, trong bộ nhớ. Điều này có nghĩa là nó không dùng trình biên dịch của Nest CLI, và không áp dụng plugin nào hay thực hiện biến đổi AST nào.

Để bật plugin, hãy tạo file sau trong thư mục e2e test của bạn:

[[CODE:16]]

Khi đã có file này, hãy import AST transformer trong file cấu hình `jest`. Mặc định (trong ứng dụng starter), file cấu hình e2e test nằm trong thư mục `test` và có tên `jest-e2e.json`.

Nếu bạn dùng `jest@<29`, hãy dùng đoạn code bên dưới:

[[CODE:17]]

Nếu bạn dùng `jest@^29`, hãy dùng đoạn code bên dưới thay vào đó, vì cách trước đã bị deprecated:

[[CODE:18]]

#### Xử lý sự cố `jest` (e2e test)

Nếu `jest` có vẻ không nhận các thay đổi cấu hình, có thể Jest đã **cache** kết quả build. Để áp dụng cấu hình mới, hãy xóa thư mục cache của Jest bằng cách chạy lệnh sau trong thư mục project NestJS:

[[CODE:19]]

Nếu việc xóa cache tự động thất bại, hãy tự xóa thư mục cache bằng các lệnh sau:

[[CODE:20]]
