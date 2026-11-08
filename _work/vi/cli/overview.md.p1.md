### Tổng quan

[Nest CLI](https://github.com/nestjs/nest-cli) là một công cụ dòng lệnh giúp bạn khởi tạo, phát triển và bảo trì ứng dụng Nest. Nó dựng khung project, chạy chúng ở chế độ development, và build cũng như bundle chúng cho production. Nó cũng thể hiện các pattern kiến trúc theo best practice để khuyến khích các ứng dụng có cấu trúc tốt.

#### Cài đặt

**Lưu ý**: Hướng dẫn này dùng [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) để cài package, kể cả Nest CLI. Bạn có thể dùng package manager khác nếu muốn. npm cung cấp nhiều cách để kiểm soát cách command line của hệ điều hành resolve binary `nest`. Ở đây, chúng ta cài nó ở phạm vi global với tùy chọn `-g`. Cách này tiện lợi, và là cách mà phần còn lại của tài liệu giả định. Hãy nhớ rằng khi bạn cài **bất kỳ** package npm nào ở phạm vi global, bạn có trách nhiệm đảm bảo mình chạy đúng phiên bản. Điều đó cũng có nghĩa là mọi project của bạn đều chạy **cùng** một phiên bản CLI. Một lựa chọn thay thế hợp lý là chương trình [npx](https://github.com/npm/cli/blob/latest/docs/lib/content/commands/npx.md) có sẵn trong npm CLI (các package manager khác có tính năng tương tự), giúp bạn chạy một **phiên bản được quản lý** của Nest CLI. Để biết thêm thông tin, hãy tham khảo [tài liệu npx](https://github.com/npm/cli/blob/latest/docs/lib/content/commands/npx.md) hoặc team DevOps của bạn.

Cài CLI ở phạm vi global bằng lệnh `npm install -g` (xem **Lưu ý** ở trên để biết chi tiết về việc cài global).

[[CODE:1]]

> info **Hint** Ngoài ra, hãy chạy `npx @nestjs/cli@latest` để dùng CLI mà không cần cài global.

#### Quy trình cơ bản

Khi đã cài CLI, bạn có thể gọi các lệnh của nó từ command line của hệ điều hành qua file thực thi `nest`. Để liệt kê các lệnh có sẵn, hãy chạy:

[[CODE:2]]

Để xem trợ giúp chi tiết về một lệnh, hãy truyền `--help` cho nó. Thay `generate` trong ví dụ bên dưới bằng bất kỳ lệnh nào, như `new` hay `add`:

[[CODE:3]]

Để tạo, build và chạy một project Nest mới ở chế độ development, hãy tới thư mục sẽ chứa project mới và chạy các lệnh sau:

[[CODE:4]]

Lệnh `new` sẽ hỏi bạn chọn một hệ thống module: ESM (mặc định), dùng Vitest để test, hoặc CommonJS, dùng Jest. Cả hai đều dùng oxlint để lint. Xem [`nest new`](/cli/usages#nest-new) để biết các câu hỏi và tùy chọn khác.

Trong trình duyệt, hãy mở [http://localhost:3000](http://localhost:3000) để xem ứng dụng mới đang chạy. Ứng dụng tự động biên dịch lại và reload mỗi khi bạn thay đổi một file mã nguồn.

> info **Hint** Để build nhanh hơn, chúng tôi khuyên dùng [SWC builder](/recipes/swc), nhanh hơn khoảng 10 lần so với trình biên dịch TypeScript mặc định.

> info **Hint** Với một project nhỏ, `nest new my-nest-project --minimal` sinh ra một ứng dụng có code nằm trong một file, bạn có thể mở rộng nó sau. Xem [Project một file](/cli/usages#one-file-projects).

#### Cấu trúc project

Khi bạn chạy `nest new`, Nest tạo một thư mục mới và điền vào đó một ứng dụng boilerplate. Bạn có thể tiếp tục làm việc trong cấu trúc mặc định này và thêm các thành phần mới như mô tả xuyên suốt tài liệu này. Chúng tôi gọi cấu trúc project được `nest new` sinh ra là **standard mode**. Nest cũng hỗ trợ một cấu trúc thay thế để quản lý nhiều project và library, gọi là **monorepo mode**.

Hai chế độ chỉ khác nhau ở cách quá trình **build** hoạt động (monorepo mode đơn giản hóa những phức tạp trong build có thể phát sinh với cấu trúc project kiểu monorepo) và ở hỗ trợ [library](/cli/libraries) có sẵn. Mọi tính năng khác của Nest, và tài liệu này, áp dụng như nhau cho cả hai. Bạn có thể chuyển từ standard mode sang monorepo mode bất cứ lúc nào, nên bạn có thể yên tâm hoãn quyết định này trong khi vẫn đang học Nest.

Bạn có thể dùng chế độ nào cũng được để quản lý nhiều project. Bảng sau tóm tắt các khác biệt:

| Tính năng                                                  | Standard Mode                                                      | Monorepo Mode                                              |
| ---------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------- |
| Nhiều project                                              | Cấu trúc file system riêng biệt                                    | Một cấu trúc file system duy nhất                          |
| `node_modules` & `package.json`                            | Mỗi project một bản                                                | Dùng chung trong toàn monorepo                             |
| Trình biên dịch mặc định                                   | `tsc`                                                              | rspack                                                     |
| Thiết lập trình biên dịch                                  | Chỉ định riêng                                                     | Mặc định của monorepo, có thể ghi đè theo từng project     |
| File cấu hình lint và formatter                            | Chỉ định riêng                                                     | Dùng chung trong toàn monorepo                             |
| Lệnh `nest build` và `nest start`                          | Đích mặc định tự động là project (duy nhất) trong context          | Đích mặc định là **project mặc định** trong monorepo       |
| Library                                                    | Quản lý thủ công, thường qua đóng gói npm                          | Hỗ trợ sẵn, bao gồm quản lý đường dẫn và bundling          |

Xem [Workspace](/cli/monorepo) và [Library](/cli/libraries) để có thêm chi tiết giúp bạn quyết định chế độ nào phù hợp nhất.

<app-banner-courses></app-banner-courses>

#### Cú pháp lệnh CLI

Mọi lệnh `nest` đều theo cùng định dạng:

[[CODE:5]]

Ví dụ:

[[CODE:6]]

Ở đây, `new` là _commandOrAlias_; alias của nó là `n`. `my-nest-project` là _requiredArg_. Nếu bạn không cung cấp _requiredArg_ trên command line, `nest` sẽ hỏi nó. Tùy chọn `--dry-run` có dạng viết tắt `-d`. Vì vậy lệnh sau tương đương với lệnh ở trên:

[[CODE:7]]

Phần lớn lệnh, và một số tùy chọn, có alias. Chạy `nest new --help` để xem chúng.

#### Tổng quan các lệnh

Chạy `nest <command> --help` với bất kỳ lệnh nào sau đây để xem các tùy chọn của nó. Xem [tài liệu tham khảo lệnh CLI](/cli/usages) để có mô tả chi tiết về từng lệnh.

| Lệnh       | Alias | Mô tả                                                                                          |
| ---------- | ----- | ---------------------------------------------------------------------------------------------- |
| `new`      | `n`   | Dựng khung một ứng dụng _standard mode_ mới với mọi file boilerplate mà nó cần để chạy.        |
| `generate` | `g`   | Sinh và/hoặc sửa file dựa trên một schematic.                                                  |
| `build`    |       | Biên dịch một ứng dụng hoặc workspace vào một thư mục output.                                  |
| `start`    |       | Biên dịch và chạy một ứng dụng (hoặc project mặc định trong một workspace).                    |
| `add`      |       | Import một library đã được đóng gói dưới dạng **nest library**, chạy install schematic của nó. |
| `upgrade`  | `update` | Nâng cấp một project đã có lên major version mới nhất của NestJS.                           |
| `deploy`   |       | Deploy ứng dụng của bạn lên cloud, được vận hành bởi [Mau](https://mau.nestjs.com/).            |
| `info`     | `i`   | Hiển thị thông tin về các package Nest đã cài và các thông tin hệ thống hữu ích khác.          |

#### Yêu cầu

Bản thân binary CLI chạy trên **Node.js v20.11 trở lên**, nhưng các schematic phía sau `nest new`, `nest generate` và `nest upgrade` (`@nestjs/schematics`) cần **Node.js v22.22.3+, v24.15+ hoặc v26+**. Việc chạy một ứng dụng Nest có mức yêu cầu thấp hơn (xem [Yêu cầu về Node.js](/migration-guide#nodejs-requirements) trong hướng dẫn migration). Nếu bạn sinh code trên máy dùng để phát triển, hãy dùng bản active LTS mới nhất.

Nest CLI cũng cần một binary Node.js được build với [hỗ trợ quốc tế hóa](https://nodejs.org/api/intl.html) (ICU), như các binary chính thức từ [trang tải Node.js](https://nodejs.org/en/download). Nếu bạn gặp lỗi liên quan tới ICU, hãy kiểm tra xem binary của bạn có đáp ứng yêu cầu này không:

[[CODE:8]]

Nếu lệnh in ra `undefined`, binary Node.js của bạn không có hỗ trợ quốc tế hóa.
