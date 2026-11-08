### Các lỗi thường gặp

Trong quá trình học và làm việc với NestJS, bạn có thể gặp các lỗi được mô tả trên trang này.

#### Lỗi "Cannot resolve dependency"

> info **Hint** [NestJS Devtools](/devtools/overview#debugging-cannot-resolve-dependency-errors) có thể giúp bạn giải quyết lỗi "Cannot resolve dependency".

Message lỗi phổ biến nhất nói rằng Nest không thể resolve các dependency của một provider. Nó thường trông như thế này:

[[CODE:1]]

Nguyên nhân phổ biến nhất là `<unknown_token>` không có sẵn trong `<module>`: nó không được liệt kê trong mảng `providers` của module cũng không được export bởi một trong các module trong mảng `imports` của nó. Hãy đảm bảo provider đã được đăng ký và tuân theo [cách làm provider tiêu chuẩn của NestJS](/fundamentals/custom-providers#di-fundamentals).

Một lỗi phổ biến khác là đặt một provider vào mảng `imports` của module. Nếu class được gắn `@Injectable()`, Nest phát hiện điều này lúc khởi động và throw một lỗi cho biết class không thể xuất hiện trong mảng "imports"; hãy chuyển nó sang mảng `providers` thay vào đó.

Khi gặp lỗi này, hãy mở module được nêu tên trong message lỗi và xem lại `providers` của nó. Với mỗi provider trong mảng `providers`, hãy đảm bảo module có quyền truy cập mọi dependency của nó. Provider thường bị lặp lại ở một feature module và root module, khiến Nest cố khởi tạo provider hai lần. Trong hầu hết các trường hợp, bạn nên gỡ bản trùng lặp và thêm module chứa `<provider>` vào mảng `imports` của root module thay vào đó.

Cũng hãy đảm bảo bạn không inject một provider vào chính nó: tự inject không được phép trong NestJS. Khi điều này xảy ra, `<unknown_token>` thường bằng `<provider>`.

Nếu dependency ở index được báo cáo resolve ra `undefined` hoặc `Object` lúc runtime, message lỗi sẽ bỏ qua tên token, chỉ tới module **hiện tại**, và liệt kê một tập giải pháp khả dĩ khác:

[[CODE:2]]

Điều này thường có một trong các nguyên nhân sau:

1. **Import file vòng tròn.** Khác với [phụ thuộc vòng tròn](/faq/common-errors#circular-dependency-error) được mô tả bên dưới, các provider không phụ thuộc lẫn nhau trong constructor của chúng; mà là hai file import lẫn nhau. Ví dụ, một file module khai báo một token và import một provider, còn provider lại import hằng số token đó từ file module. Nếu bạn dùng barrel file, hãy đảm bảo các import qua barrel không tạo ra những circular import như vậy.
2. **Inject theo type hoặc interface.** Type và interface không tồn tại lúc runtime, nên Nest không thể dùng chúng làm injection token. Hãy inject tham chiếu class thay vào đó, hoặc dùng một custom token với decorator `@Inject()` (xem [custom provider](/fundamentals/custom-providers)).
3. **Import chỉ type.** Với các provider dựa trên class, hãy import class cụ thể thay vì chỉ import type của nó bằng cú pháp [`import type ...`](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-8.html#type-only-imports-and-export).

<app-banner-observe></app-banner-observe>

Trong một **cách thiết lập monorepo**, bạn có thể thấy cùng lỗi này với provider lõi `ModuleRef` ở vị trí `<unknown_token>`:

[[CODE:3]]

Điều này thường xảy ra khi project của bạn load hai bản sao của package `@nestjs/core`, như thế này:

[[CODE:4]]

Giải pháp:

- Với workspace **Yarn**, hãy dùng [tính năng nohoist](https://classic.yarnpkg.com/blog/2018/02/15/nohoist) để ngăn việc hoist package `@nestjs/core`.
- Với workspace **pnpm**, hãy khai báo `@nestjs/core` làm peer dependency trong module kia, và đặt `"dependenciesMeta": {{ '{' }}"other-module-name": {{ '{' }}"injected": true &#125;&#125;` trong package.json của ứng dụng import module đó. Xem [dependenciesMeta.injected](https://pnpm.io/package_json#dependenciesmetainjected) trong tài liệu pnpm.

#### Lỗi "Circular dependency"

Đôi khi, bạn sẽ thấy khó tránh được [phụ thuộc vòng tròn](/fundamentals/circular-dependency) trong ứng dụng, và bạn sẽ cần giúp Nest resolve chúng. Các lỗi do phụ thuộc vòng tròn gây ra trông như thế này:

[[CODE:5]]

Phụ thuộc vòng tròn có thể phát sinh từ các provider phụ thuộc lẫn nhau, hoặc từ các file TypeScript phụ thuộc lẫn nhau vì hằng số (ví dụ một file module export một hằng số mà một file service import). Trong trường hợp sau, hãy chuyển các hằng số sang một file riêng. Trong trường hợp trước, hãy làm theo hướng dẫn về [phụ thuộc vòng tròn](/fundamentals/circular-dependency) và đảm bảo cả module **lẫn** provider đều được bọc bằng `forwardRef()`.

#### Debug lỗi dependency

Ngoài việc tự kiểm tra các dependency, bạn có thể đặt biến môi trường `NEST_DEBUG` thành bất kỳ chuỗi không rỗng nào để có thêm log trong lúc Nest resolve các dependency của ứng dụng.

<figure><img src="/assets/injector_logs.png" /></figure>

Trong hình ở trên, chuỗi màu vàng là class host của dependency đang được inject, chuỗi màu xanh dương là tên (hoặc injection token) của dependency được inject, và chuỗi màu tím là module mà Nest tìm dependency trong đó. Với output này, bạn thường có thể lần theo quá trình resolve dependency và tìm ra lý do việc inject thất bại.

#### "File change detected" lặp vô tận

Người dùng Windows với TypeScript 4.9 trở lên có thể gặp vấn đề này. Khi bạn chạy ứng dụng ở watch mode (ví dụ `npm run start:dev`), bạn thấy một vòng lặp vô tận các message log sau:

[[CODE:6]]

Khi bạn khởi động ứng dụng ở watch mode bằng Nest CLI, nó chạy trình biên dịch TypeScript ở watch mode (tương đương `tsc --watch`). TypeScript 4.9 đã giới thiệu một [chiến lược mới](https://devblogs.microsoft.com/typescript/announcing-typescript-4-9/#file-watching-now-uses-file-system-events) để phát hiện thay đổi file, đây có lẽ là nguyên nhân của vấn đề này.
Để sửa, hãy thêm thiết lập sau vào file `tsconfig.json`, sau tùy chọn `"compilerOptions"`:

[[CODE:7]]

Thiết lập này bảo TypeScript poll để phát hiện thay đổi file thay vì dùng file system event (mặc định từ 4.9), thứ có thể gây vấn đề trên một số máy.
Để tìm hiểu thêm, xem [tùy chọn `watchFile`](https://www.typescriptlang.org/tsconfig#watch-watchFile) trong tài liệu TypeScript.
