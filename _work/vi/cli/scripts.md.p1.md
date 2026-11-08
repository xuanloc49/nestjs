### Nest CLI và script

Phần này giải thích cách lệnh `nest` tương tác với trình biên dịch và script, để giúp người làm DevOps quản lý môi trường phát triển.

Một ứng dụng Nest là một ứng dụng TypeScript **tiêu chuẩn** phải được biên dịch sang JavaScript trước khi có thể chạy. Có nhiều cách để xử lý bước biên dịch, và developer cũng như team được tự do chọn cách phù hợp nhất với mình. Với suy nghĩ đó, Nest cung cấp sẵn một tập công cụ nhằm:

- Cung cấp một quy trình build/chạy tiêu chuẩn, dùng được từ command line, hoạt động với các giá trị mặc định hợp lý.
- Giữ quy trình build/chạy **mở**, để developer có thể truy cập trực tiếp các công cụ bên dưới và tùy chỉnh chúng bằng các tính năng và tùy chọn gốc của chúng.
- Vẫn là một framework TypeScript/Node.js hoàn toàn tiêu chuẩn, để bất kỳ công cụ bên ngoài nào mà team chọn đều có thể quản lý toàn bộ pipeline biên dịch/deploy/chạy.

Nest đạt được điều này nhờ kết hợp lệnh `nest`, một trình biên dịch TypeScript được cài cục bộ, và các script trong `package.json`. Các phần bên dưới mô tả cách những thành phần này phối hợp với nhau, điều gì xảy ra ở mỗi bước của quy trình build/chạy, và cách tùy chỉnh hành vi đó.

#### Binary nest

Lệnh `nest` là một binary ở cấp hệ điều hành (tức là nó chạy từ command line của hệ điều hành). Nó bao gồm ba lĩnh vực riêng biệt, được mô tả bên dưới. Chúng tôi khuyên bạn chạy các subcommand build (`nest build`) và chạy (`nest start`) qua các script trong `package.json` được sinh ra khi bạn dựng khung một project (xem [typescript starter](https://github.com/nestjs/typescript-starter) nếu bạn muốn bắt đầu bằng cách clone một repository thay vì chạy `nest new`).

#### Build

`nest build` là một wrapper quanh trình biên dịch tiêu chuẩn `tsc` hoặc `swc` (với [project tiêu chuẩn](/cli/overview#project-structure)) hoặc bundler Rspack (với [monorepo](/cli/overview#project-structure)). Ngoài việc xử lý `tsconfig-paths` và chạy các CLI plugin được bật, nó không thêm tính năng hay bước biên dịch nào của riêng mình. Nó tồn tại vì phần lớn developer, đặc biệt khi mới bắt đầu với Nest, không cần điều chỉnh các tùy chọn trình biên dịch (ví dụ trong file `tsconfig.json`), việc có thể khá rắc rối.

Xem tài liệu [nest build](/cli/usages#nest-build) để biết thêm chi tiết.

#### Chạy

`nest start` đảm bảo project đã được build (giống như `nest build`), rồi gọi lệnh `node` theo cách có thể dùng ở mọi nơi để chạy ứng dụng đã biên dịch. Như với việc build, bạn có thể tùy chỉnh quá trình này qua lệnh `nest start` và các tùy chọn của nó, hoặc thay thế nó hoàn toàn. Toàn bộ quá trình là một pipeline build và chạy TypeScript tiêu chuẩn, và bạn có thể quản lý nó như vậy.

Xem tài liệu [nest start](/cli/usages#nest-start) để biết thêm chi tiết.

#### Sinh code

Các lệnh `nest generate` sinh ra thành phần mới, hoặc ứng dụng và library mới trong một workspace. (Để tạo một project mới, hãy dùng `nest new`.)

#### Package script

Chạy các lệnh `nest` ở cấp command line của hệ điều hành yêu cầu binary `nest` được cài ở phạm vi global. Đây là một tính năng tiêu chuẩn của npm, nằm ngoài sự kiểm soát trực tiếp của Nest. Một hệ quả là binary `nest` được cài global **không** được quản lý như một dependency của project trong `package.json`, nên hai developer có thể chạy hai phiên bản khác nhau của nó. Giải pháp tiêu chuẩn là dùng package script, để bạn có thể coi các công cụ dùng trong bước build và chạy là development dependency.

Khi bạn chạy `nest new`, hoặc clone [typescript starter](https://github.com/nestjs/typescript-starter), Nest điền vào các script trong `package.json` của project mới các lệnh như `build` và `start`. Nó cũng cài các công cụ trình biên dịch bên dưới (như `typescript`) dưới dạng **dev dependency**.

Bạn chạy các script build và chạy bằng các lệnh như:

[[CODE:1]]

và

[[CODE:2]]

Các lệnh này dùng script runner của npm để chạy `nest build` hoặc `nest start` với binary `nest` **được cài cục bộ**. Bằng cách dùng các package script có sẵn này, bạn có được việc quản lý dependency đầy đủ cho các lệnh Nest CLI\*. Bằng cách theo cách dùng **được khuyến nghị** này, mọi thành viên trong tổ chức đều chạy cùng một phiên bản của các lệnh.

\*Điều này áp dụng cho các lệnh `build` và `start`. Các lệnh `nest new` và `nest generate` không phải là một phần của pipeline build/chạy, nên chúng hoạt động trong một ngữ cảnh khác và không đi kèm các script có sẵn trong `package.json`.

Chúng tôi khuyên phần lớn developer và team dùng package script để build và chạy các project Nest. Bạn có thể tùy chỉnh hành vi của các script này qua tùy chọn của chúng, và tùy chỉnh các file cấu hình của `tsc`, `swc` hoặc Rspack (ví dụ `tsconfig.json`) khi cần. Bạn cũng được tự do chạy một quy trình build hoàn toàn tùy chỉnh để biên dịch TypeScript (hoặc thậm chí chạy TypeScript trực tiếp bằng `ts-node`).

#### Tương thích ngược

Vì ứng dụng Nest là ứng dụng TypeScript thuần, các phiên bản trước của script build/chạy Nest vẫn tiếp tục hoạt động. Bạn không bắt buộc phải nâng cấp chúng. Bạn có thể chuyển sang dùng các lệnh `nest build` và `nest start` khi đã sẵn sàng, hoặc tiếp tục chạy các script cũ hoặc tùy chỉnh của mình.

#### Migration

Bạn không bắt buộc phải thay đổi gì, nhưng bạn có thể muốn chuyển sang dùng các lệnh CLI thay cho các công cụ như `tsc-watch` hay `ts-node`. Để làm vậy, hãy cài phiên bản mới nhất của `@nestjs/cli` cả ở phạm vi global lẫn cục bộ:

[[CODE:3]]

Sau đó thay các `scripts` được định nghĩa trong `package.json` bằng nội dung sau:

[[CODE:4]]
