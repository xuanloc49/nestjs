### Tham khảo lệnh CLI

#### nest new

Tạo một project Nest mới (standard mode), hoặc với `--minimal` là một [project một file](/cli/usages#one-file-projects).

[[CODE:1]]

##### Mô tả

Tạo và khởi tạo một project Nest mới. Lệnh sẽ hỏi mọi thông tin mà bạn không truyền qua tùy chọn: tên project, package manager, hệ thống module (ESM hay CommonJS), và có thiết lập [NestJS Observe](/observability/overview) hay không.

> info **Hint** Trong môi trường không tương tác, như CI, hãy truyền tên project và `--package-manager`. Khi đó hệ thống module mặc định là ESM, và Observe chỉ được thiết lập nếu bạn truyền `--observe`.

> info **Hint** Chọn **ESM** sẽ dựng khung một project ưu tiên ESM dùng Vitest để test. Chọn **CommonJS** sẽ dựng khung theo bố cục truyền thống, dùng Jest. Cả hai biến thể đều dùng oxlint để lint.

Lệnh này:

- Tạo một thư mục với `<name>` được cho
- Điền vào thư mục các file cấu hình
- Tạo các thư mục con cho mã nguồn (`/src`) và end-to-end test (`/test`)
- Điền vào các thư mục con các file mặc định cho các thành phần của ứng dụng và test
- Nếu Observe đã được thiết lập, đề nghị liên kết project với nó khi các dependency đã được cài (chỉ trong terminal tương tác). Đồng ý sẽ chạy `npx @nestjs/observe link`, lệnh này ghi app key và secret vào `.env` - xem [Liên kết từ terminal](/observability/sdk#linking-from-the-terminal)

##### Tham số

| Tham số  | Mô tả                       |
| -------- | --------------------------- |
| `<name>` | Tên của project mới         |

##### Tùy chọn

| Tùy chọn                              | Mô tả                                                                                                                                                                                                                                                         |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--directory [directory]`             | Thư mục đích.                                                                                                                                                                                                                                                 |
| `--dry-run`                           | Báo cáo những thay đổi sẽ được thực hiện, mà không thay đổi filesystem.<br/> Alias: `-d`                                                                                                                                                                      |
| `--skip-git`                          | Bỏ qua việc khởi tạo git repository.<br/> Alias: `-g`                                                                                                                                                                                                         |
| `--skip-install`                      | Bỏ qua việc cài package.<br/> Alias: `-s`                                                                                                                                                                                                                     |
| `--skip-tests`                        | Bỏ qua việc sinh file test cho project mới.<br/> Alias: `-t`                                                                                                                                                                                                  |
| `--package-manager [package-manager]` | Package manager cần dùng: `npm`, `yarn`, `pnpm` hoặc `bun`. Package manager phải được cài ở phạm vi global.<br/> Alias: `-p`                                                                                                                                   |
| `--language [language]`               | Ngôn ngữ lập trình: `TS` (mặc định) hoặc `JS`. Giá trị không phân biệt hoa thường, và `typescript` / `javascript` cũng được chấp nhận.<br/> Alias: `-l`                                                                                                        |
| `--collection [collectionName]`       | Collection schematic cần dùng. Truyền tên package của một package npm đã cài có chứa schematic.<br/> Alias: `-c`                                                                                                                                              |
| `--strict`                            | Bật chế độ `strict` của TypeScript (với `strictPropertyInitialization` bị tắt) trong `tsconfig.json` được sinh ra. Được bật mặc định, và không có cờ nào để tắt nó: để không dùng, hãy đặt `"strict": false` trong `tsconfig.json` sau khi sinh project. |
| `--format`                            | Format các file được sinh ra bằng Prettier.                                                                                                                                                                                                                   |
| `--observe` / `--no-observe`          | Thiết lập SDK `@nestjs/observe`, hoặc bỏ qua nó, mà không bị hỏi. Bỏ cả hai để được hỏi trong terminal tương tác (câu hỏi mặc định là có). Không có terminal, Observe không được thiết lập.                                                                   |
| `--minimal`                           | Sinh một ứng dụng có code nằm trong một file, `src/main.ts`. Xem [Project một file](/cli/usages#one-file-projects). Chỉ TypeScript và ESM.                                                                                                                     |

##### Project một file

`nest new <name> --minimal` sinh ra một ứng dụng Nest thật sự mà không có bố cục xung quanh, cho một project nhỏ hoặc một phiên bản đầu tiên:

[[CODE:2]]

[[CODE:3]]

Chạy nó bằng `npm run start:dev`. Nó đi qua CLI, như mọi project Nest khác, vì trình biên dịch TypeScript phải phát ra decorator metadata thì việc inject theo type mới hoạt động. Dưới một công cụ không phát ra metadata này, như `tsx`, `appService` ở trên sẽ là `undefined`.

Không có `nest-cli.json`, vì các giá trị mặc định của CLI đã mô tả sẵn bố cục này, và không có test, linter, formatter hay README. Hãy thêm bất kỳ thứ nào trong số đó khi bạn cần.

`nest generate` hoạt động ở đây giống như ở mọi nơi khác. Khi không có file `*.module.ts` nào để đăng ký, nó dùng module trong `src/main.ts`:

[[CODE:4]]

Lệnh này ghi ra `src/users/` và thêm `UsersModule` vào imports trong `src/main.ts`. File spec bị bỏ qua chừng nào `package.json` chưa liệt kê `@nestjs/testing`: hãy cài nó, hoặc truyền `--spec`, để có chúng. Khi `src/main.ts` trở nên dài, hãy chuyển module sang `src/app.module.ts` và export nó, và `nest generate` sẽ đăng ký mọi thứ ở đó thay vào đó.

Các tùy chọn khác của `nest new` vẫn áp dụng, với những khác biệt sau:

- `--language js` bị từ chối. JavaScript cần Babel và file entry riêng để chạy decorator, nên project sẽ không còn là một file.
- Project luôn là ESM, và bạn không bị hỏi về hệ thống module. Với CommonJS, hãy sinh một project tiêu chuẩn.
- `--observe` nối SDK vào `src/main.ts`. Sau đó `npx @nestjs/observe link` ghi cặp key, như thường lệ. Không có `--observe`, việc thêm SDK sau này cần [ba chỗ sửa trong phần bắt đầu nhanh của nó](https://observe.nestjs.com/documentation/sdk#quick-start), vì `link` tìm root module trong một file mà `main.ts` import.
- `--skip-tests` không có gì để bỏ qua.

#### nest generate

Sinh và/hoặc sửa file dựa trên một schematic.

[[CODE:5]]

##### Tham số

| Tham số       | Mô tả                                                                                                    |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| `<schematic>` | `schematic` hoặc `collection:schematic` cần sinh. Xem bảng bên dưới để biết các schematic có sẵn.        |
| `<name>`      | Tên của thành phần được sinh ra. Nếu bỏ qua, schematic sẽ hỏi nó.                                        |

##### Schematic

| Tên           | Alias | Mô tả                                                                                                                  |
| ------------- | ----- | ---------------------------------------------------------------------------------------------------------------------- |
| `app`         |       | Sinh một ứng dụng mới trong một monorepo (chuyển một cấu trúc standard mode sang monorepo).                            |
| `library`     | `lib` | Sinh một library mới trong một monorepo (chuyển một cấu trúc standard mode sang monorepo).                             |
| `class`       | `cl`  | Sinh một class mới.                                                                                                    |
| `controller`  | `co`  | Sinh một khai báo controller.                                                                                          |
| `decorator`   | `d`   | Sinh một custom decorator. Từ v12, decorator được sinh ra dùng dạng `Reflector.createDecorator()`.                     |
| `filter`      | `f`   | Sinh một khai báo filter.                                                                                              |
| `gateway`     | `ga`  | Sinh một khai báo gateway.                                                                                             |
| `guard`       | `gu`  | Sinh một khai báo guard.                                                                                               |
| `interface`   | `itf` | Sinh một interface.                                                                                                    |
| `interceptor` | `itc` | Sinh một khai báo interceptor.                                                                                         |
| `middleware`  | `mi`  | Sinh một khai báo middleware.                                                                                          |
| `module`      | `mo`  | Sinh một khai báo module.                                                                                              |
| `pipe`        | `pi`  | Sinh một khai báo pipe.                                                                                                |
| `provider`    | `pr`  | Sinh một khai báo provider.                                                                                            |
| `resolver`    | `r`   | Sinh một khai báo resolver.                                                                                            |
| `resource`    | `res` | Sinh một CRUD resource mới (chỉ TypeScript). Xem [CRUD (resource) generator](/recipes/crud-generator).                 |
| `service`     | `s`   | Sinh một khai báo service.                                                                                             |

##### Tùy chọn

| Tùy chọn                        | Mô tả                                                                                                           |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `--dry-run`                     | Báo cáo những thay đổi sẽ được thực hiện, mà không thay đổi filesystem.<br/> Alias: `-d`                        |
| `--project [project]`           | Project mà thành phần sẽ được thêm vào.<br/> Alias: `-p`                                                        |
| `--flat`                        | Không sinh thư mục cho thành phần.                                                                              |
| `--no-flat`                     | Sinh một thư mục cho thành phần.                                                                                |
| `--collection [collectionName]` | Collection schematic cần dùng. Truyền tên package của một package npm đã cài có chứa schematic.<br/> Alias: `-c` |
| `--spec`                        | Sinh file spec (mặc định, trừ khi `package.json` không liệt kê `@nestjs/testing`).                              |
| `--no-spec`                     | Bỏ qua việc sinh file spec.                                                                                     |
| `--spec-file-suffix [suffix]`   | Dùng một hậu tố tùy chỉnh cho file spec.                                                                        |
| `--skip-import`                 | Bỏ qua việc import thành phần được sinh ra vào module gần nhất của nó.                                          |
| `--format`                      | Format các file được sinh ra bằng Prettier.                                                                     |
| `--type <type>`                 | (chỉ `resource`) Lớp transport: `rest`, `graphql-code-first`, `graphql-schema-first`, `microservice` hoặc `ws`. |
| `--crud [value]`                | (chỉ `resource`) Có sinh các entry point CRUD hay không (`true` hoặc `false`).                                  |

#### nest build

Biên dịch một ứng dụng hoặc workspace vào một thư mục output.

Lệnh `build` cũng chịu trách nhiệm:

- ánh xạ đường dẫn (nếu bạn dùng path alias) qua `tsconfig-paths`
- chú thích DTO bằng các decorator OpenAPI (nếu CLI plugin của `@nestjs/swagger` được bật)
- chú thích DTO bằng các decorator GraphQL (nếu CLI plugin của `@nestjs/graphql` được bật)

[[CODE:6]]

##### Tham số

| Tham số     | Mô tả                                                                                        |
| ----------- | -------------------------------------------------------------------------------------------- |
| `[name...]` | Tên của project cần build. Truyền nhiều tên để build nhiều project. Nếu bỏ qua, project mặc định sẽ được build. |

##### Tùy chọn

| Tùy chọn                | Mô tả                                                                                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--path [path]`         | Đường dẫn tới file `tsconfig`. <br/>Alias `-p`                                                                                                                                             |
| `--config [path]`       | Đường dẫn tới file cấu hình `nest-cli`. <br/>Alias `-c`                                                                                                                                    |
| `--watch`               | Chạy ở watch mode (live-reload).<br /> Với trình biên dịch `tsc`, bạn có thể gõ `rs` để restart ứng dụng (khi tùy chọn `manualRestart` được đặt thành `true`). <br/>Alias `-w`            |
| `--builder [name]`      | Builder dùng để biên dịch (`tsc`, `swc` hoặc `rspack`). <br/>Alias `-b`                                                                                                                    |
| `--webpack`             | Cờ cũ đã deprecated cho việc biên dịch dựa trên webpack. Hãy dùng `--builder rspack` hoặc một builder tường minh khác thay vào đó.                                                        |
| `--webpackPath [path]`  | Đường dẫn cũ đã deprecated tới một file cấu hình webpack. Hãy dùng cấu hình mà builder bạn chọn hỗ trợ thay vào đó.                                                                       |
| `--rspackPath [path]`   | Đường dẫn tới một file cấu hình Rspack.                                                                                                                                                    |
| `--tsc`                 | Buộc dùng `tsc` để biên dịch.                                                                                                                                                              |
| `--watchAssets`         | Theo dõi các file không phải TS (asset như file `.graphql`). Xem [Asset](/cli/monorepo#assets) để biết thêm chi tiết.                                                                      |
| `--type-check`          | Bật type checking (khi dùng SWC).                                                                                                                                                          |
| `--no-type-check`       | Tắt type checking (khi dùng SWC).                                                                                                                                                          |
| `--emit-declarations`   | Phát ra file khai báo (`.d.ts`) khi dùng SWC builder.                                                                                                                                      |
| `--all`                 | Build mọi project trong một monorepo.                                                                                                                                                      |
| `--parallel [concurrency]` | Build các project song song (dùng cùng `--all`). Truyền một số nguyên dương để giới hạn mức đồng thời, hoặc bỏ giá trị để không giới hạn.                                               |
| `--silent`              | Ẩn các log thông tin của trình biên dịch.                                                                                                                                                  |
| `--preserveWatchOutput` | Giữ output cũ trên console ở watch mode thay vì xóa màn hình. (chỉ watch mode của `tsc`)                                                                                                   |

#### nest start

Biên dịch và chạy một ứng dụng (hoặc project mặc định trong một workspace).

[[CODE:7]]

##### Tham số

| Tham số  | Mô tả                                                                |
| -------- | -------------------------------------------------------------------- |
| `[name]` | Tên của project cần chạy. Nếu bỏ qua, project mặc định sẽ chạy.      |

##### Tùy chọn

| Tùy chọn                | Mô tả                                                                                                                              |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `--path [path]`         | Đường dẫn tới file `tsconfig`. <br/>Alias `-p`                                                                                     |
| `--config [path]`       | Đường dẫn tới file cấu hình `nest-cli`. <br/>Alias `-c`                                                                            |
| `--watch`               | Chạy ở watch mode (live-reload). <br/>Alias `-w`                                                                                   |
| `--builder [name]`      | Builder dùng để biên dịch (`tsc`, `swc` hoặc `rspack`). <br/>Alias `-b`                                                          |
| `--preserveWatchOutput` | Giữ output cũ trên console ở watch mode thay vì xóa màn hình. (chỉ watch mode của `tsc`)                                           |
| `--watchAssets`         | Chạy ở watch mode (live-reload), theo dõi các file không phải TS (asset). Xem [Asset](/cli/monorepo#assets) để biết thêm chi tiết. |
| `--debug [hostport]`    | Chạy ở debug mode (với cờ `--inspect`). <br/>Alias `-d`                                                                            |
| `--webpack`             | Cờ cũ đã deprecated cho việc biên dịch dựa trên webpack. Hãy dùng `--builder rspack` hoặc một builder tường minh khác thay vào đó. |
| `--webpackPath [path]`  | Đường dẫn cũ đã deprecated tới một file cấu hình webpack. Hãy dùng cấu hình mà builder bạn chọn hỗ trợ thay vào đó.                |
| `--rspackPath [path]`   | Đường dẫn tới một file cấu hình Rspack.                                                                                            |
| `--tsc`                 | Buộc dùng `tsc` để biên dịch.                                                                                                      |
| `--type-check`          | Bật type checking (khi dùng SWC).                                                                                                  |
| `--no-type-check`       | Tắt type checking (khi dùng SWC).                                                                                                  |
| `--emit-declarations`   | Phát ra file khai báo (`.d.ts`) khi dùng SWC builder.                                                                              |
| `--silent`              | Ẩn các log thông tin của trình biên dịch.                                                                                          |
| `--sourceRoot [sourceRoot]` | Thư mục gốc của mã nguồn (ghi đè thiết lập `sourceRoot` trong `nest-cli.json`).                                                |
| `--entryFile [entryFile]` | File entry cần chạy (ghi đè thiết lập `entryFile` trong `nest-cli.json`).                                                        |
| `--exec [binary]`       | Binary cần chạy (mặc định: `node`). <br/>Alias `-e`                                                                                |
| `--no-shell`            | Không spawn child process bên trong một shell (xem tài liệu `child_process.spawn()` của Node.js).                                  |
| `--env-file [path]`     | Load biến môi trường từ một file, tương đối so với thư mục hiện tại, và đưa chúng vào `process.env` cho ứng dụng. Lặp lại tùy chọn để load nhiều file. Một file không tồn tại sẽ bị bỏ qua, kèm một thông báo. |
| `-- [key=value]`        | Các tham số dòng lệnh mà ứng dụng có thể đọc từ `process.argv`.                                                                    |
