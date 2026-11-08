### Library

Nhiều ứng dụng cần giải quyết cùng những vấn đề chung, hoặc tái sử dụng một thành phần dạng module trong nhiều ngữ cảnh. Nest cung cấp một vài cách để giải quyết điều này. Mỗi cách hoạt động ở một cấp độ khác nhau và giúp đáp ứng các mục tiêu kiến trúc và tổ chức khác nhau.

Các [module](/modules) của Nest cung cấp một execution context cho phép các thành phần được dùng chung trong một ứng dụng. Bạn cũng có thể đóng gói module bằng [npm](https://npmjs.com) để tạo một library có thể tái sử dụng mà các project khác nhau có thể cài. Đây là một cách hiệu quả để phân phối các library có thể cấu hình, có thể tái sử dụng tới các tổ chức có liên kết lỏng lẻo hoặc không liên quan (ví dụ bằng cách phân phối và cài đặt các library bên thứ ba).

Để dùng chung code trong các nhóm có tổ chức chặt chẽ (ví dụ trong phạm vi một công ty hoặc một project), một cách tiếp cận gọn nhẹ hơn có thể hữu ích. Monorepo ra đời để làm điều đó, và bên trong một monorepo, một **library** cung cấp một cách gọn nhẹ để dùng chung code. Trong một monorepo Nest, library giúp việc lắp ghép các ứng dụng dùng chung thành phần trở nên đơn giản. Điều này cũng khuyến khích bạn tách nhỏ các ứng dụng nguyên khối, và tập trung việc phát triển vào xây dựng và kết hợp các thành phần dạng module.

#### Library của Nest <a id="nest-libraries"></a>

Một library của Nest là một project Nest mà, khác với một ứng dụng, không thể tự chạy. Một library phải được import vào một ứng dụng chứa nó thì code của nó mới được thực thi. Hỗ trợ library có sẵn được mô tả trong phần này chỉ có cho **monorepo** (các project standard mode có thể đạt được chức năng tương tự bằng package npm).

Ví dụ, một tổ chức có thể phát triển một `AuthModule` quản lý việc xác thực bằng cách hiện thực các chính sách của công ty áp dụng cho mọi ứng dụng nội bộ. Thay vì xây dựng module đó riêng cho từng ứng dụng, hoặc đóng gói code bằng npm và yêu cầu mỗi project cài nó, một monorepo có thể định nghĩa module đó như một library. Khi được tổ chức theo cách này, mọi bên dùng library module đều thấy phiên bản mới nhất của `AuthModule` ngay khi nó được commit. Điều này có thể giúp đáng kể trong việc điều phối phát triển và lắp ghép các thành phần, và đơn giản hóa end-to-end testing.

#### Tạo library <a id="creating-libraries"></a>

Bất kỳ chức năng nào phù hợp để tái sử dụng đều là ứng viên cho một library. Quyết định thứ gì nên là library, và thứ gì nên là một phần của ứng dụng, là một quyết định thiết kế kiến trúc. Tạo một library không chỉ là copy code từ một ứng dụng đã có vào nó: code của library phải được tách rời khỏi ứng dụng. Việc này có thể tốn **nhiều** thời gian hơn lúc đầu và buộc bạn đưa ra những quyết định thiết kế mà bạn sẽ không gặp với code gắn kết chặt hơn. Công sức đó được đền đáp khi library cho phép bạn lắp ghép nhiều ứng dụng nhanh hơn.

Để tạo một library, hãy chạy lệnh sau:

```bash
$ nest g library my-library
```

Khi bạn chạy lệnh, schematic `library` hỏi bạn một prefix (còn gọi là alias) cho library:

```bash
What prefix would you like to use for the library (default: @app or 'defaultLibraryPrefix' setting value)?
```

Prefix mặc định là `@app`, trừ khi file `nest-cli.json` của bạn đặt thuộc tính `defaultLibraryPrefix`.

Lệnh này tạo một project mới tên `my-library` trong workspace của bạn. Giống như một project loại ứng dụng, một project loại library được schematic sinh ra trong một thư mục có tên. Các library nằm trong thư mục `libs` ở thư mục gốc của monorepo. Nest tạo thư mục `libs` khi bạn tạo library đầu tiên.

Các file được sinh ra cho một library hơi khác so với các file được sinh ra cho một ứng dụng. Đây là nội dung của thư mục `libs` sau khi chạy lệnh ở trên:

<div class="file-tree">
  <div class="item">libs</div>
  <div class="children">
    <div class="item">my-library</div>
    <div class="children">
      <div class="item">src</div>
      <div class="children">
        <div class="item">index.ts</div>
        <div class="item">my-library.module.ts</div>
        <div class="item">my-library.service.ts</div>
      </div>
      <div class="item">tsconfig.lib.json</div>
    </div>
  </div>
</div>

Giờ file `nest-cli.json` có một entry mới cho library dưới key `"projects"`:

```javascript
...
{
    "my-library": {
      "type": "library",
      "root": "libs/my-library",
      "entryFile": "index",
      "sourceRoot": "libs/my-library/src",
      "compilerOptions": {
        "tsConfigPath": "libs/my-library/tsconfig.lib.json"
      }
}
...
```

Có hai khác biệt trong metadata của `nest-cli.json` giữa library và ứng dụng:

- thuộc tính `"type"` được đặt thành `"library"` thay vì `"application"`
- thuộc tính `"entryFile"` được đặt thành `"index"` thay vì `"main"`

Những khác biệt này cho quá trình build biết cách xử lý library cho phù hợp. Ví dụ, một library export chức năng của nó qua file `index.js`.

Giống như các project loại ứng dụng, mỗi library có file `tsconfig.lib.json` riêng kế thừa file `tsconfig.json` gốc (của toàn monorepo). Bạn có thể sửa file này để cung cấp các tùy chọn trình biên dịch riêng cho library.

Để build library, hãy chạy:

```bash
$ nest build my-library
```

#### Dùng library <a id="using-libraries"></a>

Với các file cấu hình đã được sinh ra, việc dùng library rất đơn giản. Giả sử bạn muốn dùng `MyLibraryService` từ library `my-library` trong ứng dụng `my-project`.

Dùng các module của library giống như dùng bất kỳ module Nest nào khác. Monorepo quản lý đường dẫn để việc import library và sinh bản build diễn ra trong suốt. Để dùng `MyLibraryService`, hãy import module khai báo nó. Sửa `my-project/src/app.module.ts` như sau để import `MyLibraryModule`:

```typescript
import { Module } from '@nestjs/common';
import { AppController } from './app.controller.js';
import { AppService } from './app.service.js';
import { MyLibraryModule } from '@app/my-library';

@Module({
  imports: [MyLibraryModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
```

Câu lệnh `import` ở trên dùng path alias `@app`, chính là `prefix` mà chúng ta đã cung cấp cho lệnh `nest g library`. Nest hiện thực điều này qua path mapping của tsconfig. Khi bạn thêm một library, Nest cập nhật key `"paths"` của file `tsconfig.json` global (của monorepo) như thế này:

```javascript
"paths": {
    "@app/my-library": [
        "./libs/my-library/src"
    ],
    "@app/my-library/*": [
        "./libs/my-library/src/*"
    ]
}
```

Trong một project ESM, entry đầu tiên trỏ tới file entry của library thay vào đó (`./libs/my-library/src/index.ts`).

> warning **Cảnh báo** Path mapping `paths` chỉ được trình biên dịch TypeScript hiểu. Test runner tự resolve module theo cách riêng. Nếu bạn chạy end-to-end test của một ứng dụng bằng Jest, hãy lặp lại mỗi alias trong tùy chọn `moduleNameMapper` của cấu hình Jest e2e của ứng dụng đó, ví dụ: `"moduleNameMapper": {{ '{' }} "^@app/my-library(|/.*)$": "<rootDir>/../../libs/my-library/src/$1" {{ '}' }}`. Nếu không, các import qua alias sẽ thất bại lúc chạy test dù project vẫn biên dịch được.

Kết hợp lại, các tính năng monorepo và library giúp việc đưa module của library vào ứng dụng trở nên đơn giản.

Cùng cơ chế đó cho phép bạn build và deploy các ứng dụng kết hợp nhiều library. Khi bạn đã import `MyLibraryModule`, `nest build` tự động xử lý việc resolve module và bundle ứng dụng, cùng mọi dependency library, để deploy. Trình biên dịch mặc định cho monorepo là **Rspack**, nên output là một file duy nhất bundle toàn bộ JavaScript đã được transpile. Bạn có thể chuyển sang `tsc` như mô tả trong [Tùy chọn trình biên dịch global](/cli/monorepo#global-compiler-options).
