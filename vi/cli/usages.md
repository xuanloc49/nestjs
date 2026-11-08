### Tham khảo lệnh CLI

#### nest new

Tạo một project Nest mới (standard mode), hoặc với `--minimal` là một [project một file](/cli/usages#one-file-projects).

```bash
$ nest new <name> [options]
$ nest n <name> [options]
```

##### Mô tả <a id="description"></a>

Tạo và khởi tạo một project Nest mới. Lệnh sẽ hỏi mọi thông tin mà bạn không truyền qua tùy chọn: tên project, package manager, hệ thống module (ESM hay CommonJS), và có thiết lập [NestJS Observe](/observability/overview) hay không.

> info **Gợi ý** Trong môi trường không tương tác, như CI, hãy truyền tên project và `--package-manager`. Khi đó hệ thống module mặc định là ESM, và Observe chỉ được thiết lập nếu bạn truyền `--observe`.

> info **Gợi ý** Chọn **ESM** sẽ dựng khung một project ưu tiên ESM dùng Vitest để test. Chọn **CommonJS** sẽ dựng khung theo bố cục truyền thống, dùng Jest. Cả hai biến thể đều dùng oxlint để lint.

Lệnh này:

- Tạo một thư mục với `<name>` được cho
- Điền vào thư mục các file cấu hình
- Tạo các thư mục con cho mã nguồn (`/src`) và end-to-end test (`/test`)
- Điền vào các thư mục con các file mặc định cho các thành phần của ứng dụng và test
- Nếu Observe đã được thiết lập, đề nghị liên kết project với nó khi các dependency đã được cài (chỉ trong terminal tương tác). Đồng ý sẽ chạy `npx @nestjs/observe link`, lệnh này ghi app key và secret vào `.env` - xem [Liên kết từ terminal](/observability/sdk#linking-from-the-terminal)

##### Tham số <a id="arguments"></a>

| Tham số  | Mô tả                       |
| -------- | --------------------------- |
| `<name>` | Tên của project mới         |

##### Tùy chọn <a id="options"></a>

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

##### Project một file <a id="one-file-projects"></a>

`nest new <name> --minimal` sinh ra một ứng dụng Nest thật sự mà không có bố cục xung quanh, cho một project nhỏ hoặc một phiên bản đầu tiên:

```bash
src/main.ts      # a service, a controller, a module and the bootstrap call
package.json     # build, start, start:dev and start:prod scripts
tsconfig.json
.gitignore
AGENTS.md
```

```typescript
import { Controller, Get, Injectable, Module } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';

@Injectable()
class AppService {
  getHello(): string {
    return 'Hello World!';
  }
}

@Controller()
class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  getHello(): string {
    return this.appService.getHello();
  }
}

@Module({
  controllers: [AppController],
  providers: [AppService],
})
class AppModule {}

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Chạy nó bằng `npm run start:dev`. Nó đi qua CLI, như mọi project Nest khác, vì trình biên dịch TypeScript phải phát ra decorator metadata thì việc inject theo type mới hoạt động. Dưới một công cụ không phát ra metadata này, như `tsx`, `appService` ở trên sẽ là `undefined`.

Không có `nest-cli.json`, vì các giá trị mặc định của CLI đã mô tả sẵn bố cục này, và không có test, linter, formatter hay README. Hãy thêm bất kỳ thứ nào trong số đó khi bạn cần.

`nest generate` hoạt động ở đây giống như ở mọi nơi khác. Khi không có file `*.module.ts` nào để đăng ký, nó dùng module trong `src/main.ts`:

```bash
$ nest g resource users
```

Lệnh này ghi ra `src/users/` và thêm `UsersModule` vào imports trong `src/main.ts`. File spec bị bỏ qua chừng nào `package.json` chưa liệt kê `@nestjs/testing`: hãy cài nó, hoặc truyền `--spec`, để có chúng. Khi `src/main.ts` trở nên dài, hãy chuyển module sang `src/app.module.ts` và export nó, và `nest generate` sẽ đăng ký mọi thứ ở đó thay vào đó.

Các tùy chọn khác của `nest new` vẫn áp dụng, với những khác biệt sau:

- `--language js` bị từ chối. JavaScript cần Babel và file entry riêng để chạy decorator, nên project sẽ không còn là một file.
- Project luôn là ESM, và bạn không bị hỏi về hệ thống module. Với CommonJS, hãy sinh một project tiêu chuẩn.
- `--observe` nối SDK vào `src/main.ts`. Sau đó `npx @nestjs/observe link` ghi cặp key, như thường lệ. Không có `--observe`, việc thêm SDK sau này cần [ba chỗ sửa trong phần bắt đầu nhanh của nó](https://observe.nestjs.com/documentation/sdk#quick-start), vì `link` tìm root module trong một file mà `main.ts` import.
- `--skip-tests` không có gì để bỏ qua.

#### nest generate

Sinh và/hoặc sửa file dựa trên một schematic.

```bash
$ nest generate <schematic> <name> [options]
$ nest g <schematic> <name> [options]
```

##### Tham số <a id="arguments-1"></a>

| Tham số       | Mô tả                                                                                                    |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| `<schematic>` | `schematic` hoặc `collection:schematic` cần sinh. Xem bảng bên dưới để biết các schematic có sẵn.        |
| `<name>`      | Tên của thành phần được sinh ra. Nếu bỏ qua, schematic sẽ hỏi nó.                                        |

##### Schematic <a id="schematics"></a>

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

##### Tùy chọn <a id="options-1"></a>

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

```bash
$ nest build [name...] [options]
```

##### Tham số <a id="arguments-2"></a>

| Tham số     | Mô tả                                                                                        |
| ----------- | -------------------------------------------------------------------------------------------- |
| `[name...]` | Tên của project cần build. Truyền nhiều tên để build nhiều project. Nếu bỏ qua, project mặc định sẽ được build. |

##### Tùy chọn <a id="options-2"></a>

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

```bash
$ nest start [name] [options]
```

##### Tham số <a id="arguments-3"></a>

| Tham số  | Mô tả                                                                |
| -------- | -------------------------------------------------------------------- |
| `[name]` | Tên của project cần chạy. Nếu bỏ qua, project mặc định sẽ chạy.      |

##### Tùy chọn <a id="options-3"></a>

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
#### nest add

Import một library đã được đóng gói dưới dạng **nest library**, chạy install schematic của nó.

```bash
$ nest add <name> [options]
```

##### Tham số <a id="arguments-4"></a>

| Tham số  | Mô tả                              |
| -------- | ---------------------------------- |
| `<name>` | Tên của library cần import.        |

##### Tùy chọn <a id="options-4"></a>

| Tùy chọn              | Mô tả                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `--dry-run`           | Báo cáo những thay đổi sẽ được thực hiện, mà không thay đổi filesystem.<br/> Alias: `-d` |
| `--skip-install`      | Bỏ qua việc cài package.<br/> Alias: `-s`                                                |
| `--project [project]` | Project mà library sẽ được thêm vào.<br/> Alias: `-p`                                    |

#### nest upgrade

Nâng cấp một project đã có lên major version mới nhất của NestJS.

```bash
$ nest upgrade [options]
$ nest update [options]
```

##### Mô tả <a id="description-1"></a>

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

> warning **Cảnh báo** `nest upgrade` chỉ nâng dependency `@nestjs/cli` **cục bộ**. Hãy tự cập nhật CLI được cài global bằng `npm i -g @nestjs/cli@latest`, và làm điều đó **trước** khi chạy nâng cấp, vì bản thân lệnh này đi kèm với CLI.

> info **Gợi ý** Lệnh cố ý không migrate project của bạn sang ESM, Vitest hay oxlint. Đó là các mặc định cho project v12 mới được sinh ra, nhưng các project đã có có thể chuyển sang theo lịch riêng của chúng. Xem [hướng dẫn migration](/migration-guide) để có bức tranh đầy đủ.

##### Tùy chọn <a id="options-5"></a>

| Tùy chọn                        | Mô tả                                                                                                             |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `--dry-run`                     | Báo cáo những thay đổi sẽ được thực hiện, mà không thay đổi filesystem.<br/> Alias: `-d`                          |
| `--skip-install`                | Bỏ qua việc cài package.<br/> Alias: `-s`                                                                         |
| `--observe` / `--no-observe`    | Thiết lập `@nestjs/observe`, hoặc bỏ qua việc thiết lập, mà không bị hỏi. Bỏ cả hai để được hỏi trong terminal tương tác (câu hỏi mặc định là không). Không có terminal, Observe không được thiết lập. |
| `--tag [tag]`                   | Dùng một npm dist-tag (ví dụ `next`) thay cho các khoảng phiên bản mặc định.<br/> Alias: `-t`                     |
| `--collection [collectionName]` | Collection schematic cần dùng. Truyền tên package của một package npm đã cài có chứa schematic.<br/> Alias: `-c`  |

#### nest deploy

Deploy ứng dụng của bạn lên cloud, được vận hành bởi [Mau](https://mau.nestjs.com/).

```bash
$ nest deploy [mau-options]
```

##### Mô tả <a id="description-2"></a>

`nest deploy` là một wrapper mỏng quanh Mau CLI. Nó định vị binary Mau và chuyển tiếp mọi tham số bạn truyền cho `mau deploy`, nên mọi tùy chọn mà Mau hỗ trợ đều dùng được ở đây mà không thay đổi.

Nếu Mau chưa được cài trong project, lệnh sẽ đề nghị thêm `@nestjs/mau` làm dev dependency rồi tiếp tục. Trong một môi trường không tương tác (ví dụ CI), lệnh sẽ thất bại thay vì hỏi, nên hãy cài Mau một cách tường minh trước:

```bash
$ npm install --save-dev @nestjs/mau
```

Khi Mau khởi động, nó nắm quyền điều khiển terminal, nên output và các câu hỏi của nó tới thẳng bạn. Xem [chương Deployment](/deployment#easy-deployment-with-mau) để biết Mau làm gì và cách cấu hình nó.

#### nest info

Hiển thị thông tin về các package Nest đã cài và các thông tin hệ thống hữu ích khác. Ví dụ:

```bash
$ nest info
```

```bash
 _   _             _      ___  _____  _____  _     _____
| \ | |           | |    |_  |/  ___|/  __ \| |   |_   _|
|  \| |  ___  ___ | |_     | |\ `--. | /  \/| |     | |
| . ` | / _ \/ __|| __|    | | `--. \| |    | |     | |
| |\  ||  __/\__ \| |_ /\__/ //\__/ /| \__/\| |_____| |_
\_| \_/ \___||___/ \__|\____/ \____/  \____/\_____/\___/

[System Information]
OS Version     : macOS Sequoia 24.6.0
NodeJS Version : v22.12.0
NPM Version    : 10.9.0

[Nest CLI]
Nest CLI Version : 12.0.3

[Nest Platform Information]
platform-express version : 12.0.4
schematics version       : 12.0.4
testing version          : 12.0.4
common version           : 12.0.4
core version             : 12.0.4
cli version              : 12.0.3
```
