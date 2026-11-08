#### nest add

Import một library đã được đóng gói dưới dạng **nest library**, chạy install schematic của nó.

[[CODE:8]]

##### Tham số

| Tham số  | Mô tả                              |
| -------- | ---------------------------------- |
| `<name>` | Tên của library cần import.        |

##### Tùy chọn

| Tùy chọn              | Mô tả                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `--dry-run`           | Báo cáo những thay đổi sẽ được thực hiện, mà không thay đổi filesystem.<br/> Alias: `-d` |
| `--skip-install`      | Bỏ qua việc cài package.<br/> Alias: `-s`                                                |
| `--project [project]` | Project mà library sẽ được thêm vào.<br/> Alias: `-p`                                    |

#### nest upgrade

Nâng cấp một project đã có lên major version mới nhất của NestJS.

[[CODE:9]]

##### Mô tả

Khi được chạy từ thư mục gốc của một project NestJS v11, `nest upgrade` cập nhật các dependency lên v12 và áp dụng các phần máy móc của quá trình migration:

- Từ chối chạy trên các bản Node.js không có `require(esm)` (mọi bản cũ hơn v20.19, hoặc v22.x cũ hơn v22.12)
- Nâng mọi package `@nestjs/*` được nhận diện lên major tương thích với v12 (`@nestjs/graphql`, `@nestjs/apollo` và `@nestjs/mercurius` lên v14), và báo cáo mọi package `@nestjs/*` khác mà nó không nhận diện được để bạn tự xem xét
- Nâng TypeScript lên v6 (CLI và schematic của v12 yêu cầu), và nâng `engines.node` trong `package.json` lên `>=20.19.0` nếu nó khai báo một mức thấp hơn
- Chuyển `nest-cli.json` khỏi các tùy chọn đã deprecated `webpack` / `webpackConfigPath` sang `--builder rspack`, cập nhật các script tương ứng trong `package.json`
- Đổi tên tùy chọn `playground` của GraphQL thành `graphiql`, chuyển subscription từ `subscriptions-transport-ws` sang `graphql-ws`, và thay các package tương ứng
- Thay package `nats` cũ bằng `@nats-io/transport-node` / `@nats-io/nats-core` và viết lại các import `nats`
- Chuyển các thiết lập riêng của library trong `@nestjs/config` vào dưới `validationOptions.libraryOptions` và nâng Joi lên v18 (bản release đầu tiên hiện thực Standard Schema)
- Nâng Jest lên v30 (và `@types/jest` / `ts-jest` lên các bản tương ứng) nếu có, và cảnh báo rằng Jest chỉ có thể `require()` các package v12 chỉ có ESM trên Node.js v24.9+
- Tùy chọn cài và nối [`@nestjs/observe`](/observability/overview). Nó sẽ hỏi, trừ khi bạn truyền `--observe` hoặc `--no-observe`
- Kiểm tra `tsconfig.json` và `tsconfig.build.json` để tìm các thiết lập mà TypeScript 6 hoặc các package chỉ có ESM không còn hỗ trợ, như một `moduleResolution` cũ hoặc thiếu `rootDir`
- Quét mã nguồn của bạn và in ra các ghi chú về những hành vi đã thay đổi nhưng không thể migrate tự động, như thứ tự lifecycle hook, signature của pipe được tinh chỉnh, và các tham số log có cấu trúc

Lệnh kết thúc bằng việc cài các dependency đã cập nhật (trừ khi truyền `--skip-install`) và in ra báo cáo về mọi thứ nó đã thay đổi, đã cảnh báo, và để lại cho bạn.

> warning **Warning** `nest upgrade` chỉ nâng dependency `@nestjs/cli` **cục bộ**. Hãy tự cập nhật CLI được cài global bằng `npm i -g @nestjs/cli@latest`, và làm điều đó **trước** khi chạy nâng cấp, vì bản thân lệnh này đi kèm với CLI.

> info **Hint** Lệnh cố ý không migrate project của bạn sang ESM, Vitest hay oxlint. Đó là các mặc định cho project v12 mới được sinh ra, nhưng các project đã có có thể chuyển sang theo lịch riêng của chúng. Xem [hướng dẫn migration](/migration-guide) để có bức tranh đầy đủ.

##### Tùy chọn

| Tùy chọn                        | Mô tả                                                                                                             |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `--dry-run`                     | Báo cáo những thay đổi sẽ được thực hiện, mà không thay đổi filesystem.<br/> Alias: `-d`                          |
| `--skip-install`                | Bỏ qua việc cài package.<br/> Alias: `-s`                                                                         |
| `--observe` / `--no-observe`    | Thiết lập `@nestjs/observe`, hoặc bỏ qua việc thiết lập, mà không bị hỏi. Bỏ cả hai để được hỏi trong terminal tương tác (câu hỏi mặc định là không). Không có terminal, Observe không được thiết lập. |
| `--tag [tag]`                   | Dùng một npm dist-tag (ví dụ `next`) thay cho các khoảng phiên bản mặc định.<br/> Alias: `-t`                     |
| `--collection [collectionName]` | Collection schematic cần dùng. Truyền tên package của một package npm đã cài có chứa schematic.<br/> Alias: `-c`  |

#### nest deploy

Deploy ứng dụng của bạn lên cloud, được vận hành bởi [Mau](https://mau.nestjs.com/).

[[CODE:10]]

##### Mô tả

`nest deploy` là một wrapper mỏng quanh Mau CLI. Nó định vị binary Mau và chuyển tiếp mọi tham số bạn truyền cho `mau deploy`, nên mọi tùy chọn mà Mau hỗ trợ đều dùng được ở đây mà không thay đổi.

Nếu Mau chưa được cài trong project, lệnh sẽ đề nghị thêm `@nestjs/mau` làm dev dependency rồi tiếp tục. Trong một môi trường không tương tác (ví dụ CI), lệnh sẽ thất bại thay vì hỏi, nên hãy cài Mau một cách tường minh trước:

[[CODE:11]]

Khi Mau khởi động, nó nắm quyền điều khiển terminal, nên output và các câu hỏi của nó tới thẳng bạn. Xem [chương Deployment](/deployment#easy-deployment-with-mau) để biết Mau làm gì và cách cấu hình nó.

#### nest info

Hiển thị thông tin về các package Nest đã cài và các thông tin hệ thống hữu ích khác. Ví dụ:

[[CODE:12]]

[[CODE:13]]
