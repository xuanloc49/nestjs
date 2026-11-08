### Workspace

Nest có hai chế độ để tổ chức code:

- **standard mode**: phù hợp với các ứng dụng riêng lẻ, tập trung vào một project, có dependency và thiết lập riêng và không cần tối ưu cho việc dùng chung module hay cho các bản build phức tạp. Đây là chế độ mặc định.
- **monorepo mode**: coi các thành phần code là một phần của một **monorepo** gọn nhẹ, và có thể phù hợp hơn cho các team developer và/hoặc các môi trường nhiều project. Nó tự động hóa một phần quá trình build để giúp việc tạo và kết hợp các thành phần dạng module trở nên dễ dàng. Nó khuyến khích tái sử dụng code, giúp integration test dễ hơn, giúp dễ dàng dùng chung các thành phần cho toàn project như lint rule và các chính sách cấu hình khác, và dễ dùng hơn các lựa chọn thay thế như Git submodule. Monorepo mode dùng khái niệm **workspace**, được biểu diễn trong file `nest-cli.json`, để điều phối quan hệ giữa các thành phần của monorepo.

Gần như mọi tính năng của Nest đều độc lập với chế độ tổ chức code của bạn. Ảnh hưởng **duy nhất** của lựa chọn này là cách các project được kết hợp và cách các build artifact được sinh ra. Mọi chức năng khác, từ CLI tới các module lõi và các module bổ sung, đều hoạt động giống nhau ở cả hai chế độ.

Bạn cũng có thể chuyển từ **standard mode** sang **monorepo mode** bất cứ lúc nào, nên bạn có thể hoãn quyết định này cho tới khi lợi ích của cách này hay cách kia trở nên rõ ràng hơn.

#### Standard mode

Khi bạn chạy `nest new`, Nest tạo một **project** mới bằng một schematic có sẵn. Nest làm những việc sau:

1. Tạo một thư mục mới được đặt tên theo tham số `name` mà bạn truyền cho `nest new`.
2. Điền vào thư mục đó các file mặc định của một ứng dụng Nest tối giản. Bạn có thể xem các file này trong repository [typescript-starter](https://github.com/nestjs/typescript-starter).
3. Thêm các file như `nest-cli.json`, `package.json` và `tsconfig.json` để cấu hình các công cụ biên dịch, test và chạy ứng dụng.

Từ đó, bạn có thể sửa các file khởi đầu, thêm các thành phần và dependency mới (ví dụ `npm install`), và phát triển ứng dụng như mô tả trong phần còn lại của tài liệu này.

#### Monorepo mode

Để bật monorepo mode, hãy bắt đầu với một cấu trúc _standard mode_ và thêm **project**. Một project có thể là một **ứng dụng** đầy đủ (bạn thêm vào workspace bằng `nest generate app`) hoặc một **library** (bạn thêm bằng `nest generate library`). Chúng ta sẽ bàn về các loại project này bên dưới. Điểm mấu chốt lúc này là **việc thêm một project** vào một cấu trúc standard mode đã có sẽ **chuyển đổi nó** sang monorepo mode. Hãy xem một ví dụ.

Nếu chúng ta chạy:

```bash
$ nest new my-project
```

chúng ta sẽ có một cấu trúc _standard mode_ với các thư mục và file sau:

<div class="file-tree">
  <div class="item">node_modules</div>
  <div class="item">src</div>
  <div class="children">
    <div class="item">app.controller.ts</div>
    <div class="item">app.module.ts</div>
    <div class="item">app.service.ts</div>
    <div class="item">main.ts</div>
  </div>
  <div class="item">nest-cli.json</div>
  <div class="item">package.json</div>
  <div class="item">tsconfig.json</div>
  <div class="item">lint config</div>
</div>

Chúng ta có thể chuyển nó sang một cấu trúc monorepo mode như sau:

```bash
$ cd my-project
$ nest generate app my-app
```

Tại thời điểm này, `nest` chuyển cấu trúc đã có sang một cấu trúc **monorepo mode**, dẫn tới một vài thay đổi quan trọng. Cấu trúc thư mục giờ trông như thế này:

<div class="file-tree">
  <div class="item">apps</div>
    <div class="children">
      <div class="item">my-app</div>
      <div class="children">
        <div class="item">src</div>
        <div class="children">
          <div class="item">my-app.controller.ts</div>
          <div class="item">my-app.module.ts</div>
          <div class="item">my-app.service.ts</div>
          <div class="item">main.ts</div>
        </div>
        <div class="item">tsconfig.app.json</div>
      </div>
      <div class="item">my-project</div>
      <div class="children">
        <div class="item">src</div>
        <div class="children">
          <div class="item">app.controller.ts</div>
          <div class="item">app.module.ts</div>
          <div class="item">app.service.ts</div>
          <div class="item">main.ts</div>
        </div>
        <div class="item">tsconfig.app.json</div>
      </div>
    </div>
  <div class="item">nest-cli.json</div>
  <div class="item">package.json</div>
  <div class="item">tsconfig.json</div>
  <div class="item">lint config</div>
</div>

Schematic `generate app` đã tổ chức lại code: nó chuyển mỗi project **ứng dụng** vào dưới thư mục `apps` và thêm một file `tsconfig.app.json` riêng cho từng project vào thư mục gốc của project đó. Ứng dụng `my-project` ban đầu của chúng ta đã trở thành **project mặc định** của monorepo, và giờ ngang hàng với `my-app` vừa thêm, dưới thư mục `apps`. Chúng ta sẽ nói về project mặc định bên dưới.

> error **Cảnh báo** Việc chuyển một cấu trúc standard mode sang monorepo chỉ hoạt động với các project tuân theo cấu trúc project Nest chuẩn. Trong quá trình chuyển đổi, schematic chuyển các thư mục `src` và `test` của project vào một thư mục project bên dưới thư mục `apps` ở gốc. Nếu một project không dùng cấu trúc này, việc chuyển đổi sẽ thất bại hoặc cho kết quả không đáng tin cậy.

#### Các project trong workspace <a id="workspace-projects"></a>

Một monorepo dùng khái niệm workspace để quản lý các thành viên của nó. Workspace được tạo thành từ các **project**. Một project là một trong hai loại:

- một **ứng dụng**: một ứng dụng Nest đầy đủ, bao gồm một file `main.ts` để bootstrap nó. Ngoài những khác biệt về biên dịch và build, một project loại ứng dụng trong workspace hoàn toàn giống về mặt chức năng với một ứng dụng trong cấu trúc _standard mode_.
- một **library**: một package các tính năng dùng chung (module, provider, controller, v.v.) mà các project khác có thể dùng. Một library không thể tự chạy và không có file `main.ts`. Xem [Library](/cli/libraries) để biết chi tiết.

Mọi workspace đều có một **project mặc định**, project này nên là loại ứng dụng. Nó được định nghĩa bởi thuộc tính `"root"` ở cấp cao nhất trong file `nest-cli.json`, trỏ tới thư mục gốc của project mặc định (xem [Thuộc tính CLI](/cli/monorepo#cli-properties) bên dưới). Thường thì đây là ứng dụng **standard mode** mà bạn bắt đầu và sau đó chuyển sang monorepo bằng `nest generate app`. Trong trường hợp đó, thuộc tính được điền tự động.

Các lệnh `nest` như `nest build` và `nest start` dùng project mặc định khi bạn không cung cấp tên project.

Ví dụ, trong cấu trúc monorepo ở trên, chạy

```bash
$ nest start
```

sẽ khởi động ứng dụng `my-project`. Để khởi động `my-app`, hãy chạy:

```bash
$ nest start my-app
```

#### Ứng dụng <a id="applications"></a>

Các project loại ứng dụng, gọi không chính thức là "ứng dụng", là các ứng dụng Nest hoàn chỉnh mà bạn có thể chạy và deploy. Bạn sinh một ứng dụng bằng `nest generate app`.

Lệnh này sinh ra khung của một project, bao gồm các thư mục `src` và `test` tiêu chuẩn từ [typescript starter](https://github.com/nestjs/typescript-starter). Khác với standard mode, một project ứng dụng trong monorepo không có file dependency của package (`package.json`) và không có các thành phần cấu hình project khác, như `.prettierrc` hay file cấu hình lint. Thay vào đó, nó dùng các dependency và file cấu hình của toàn monorepo.

Tuy nhiên, schematic có sinh ra một file `tsconfig.app.json` riêng cho project trong thư mục gốc của project. File này đặt các tùy chọn build phù hợp, bao gồm thư mục output của quá trình biên dịch. Nó kế thừa file `tsconfig.json` ở cấp cao nhất (của monorepo), nên bạn có thể quản lý thiết lập global cho toàn monorepo và ghi đè chúng ở cấp project khi cần.

#### Library <a id="libraries"></a>

Các project loại library, hay đơn giản là "library", là các package chứa thành phần Nest phải được kết hợp vào ứng dụng để chạy. Bạn sinh một library bằng `nest generate library`. Quyết định thứ gì thuộc về một library là một quyết định thiết kế kiến trúc. Chúng ta bàn sâu về library trong chương [Library](/cli/libraries).

#### Thuộc tính CLI <a id="cli-properties"></a>

Nest giữ metadata cần thiết để tổ chức, build và deploy cả project standard lẫn monorepo trong file `nest-cli.json`. Nest tự động cập nhật file này khi bạn thêm project, nên bạn thường không phải sửa nó. Tuy nhiên, bạn có thể muốn tự thay đổi một số thiết lập, nên hiểu cấu trúc của file sẽ hữu ích.

Sau các bước ở trên, file `nest-cli.json` trông như thế này:

```javascript
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "apps/my-project/src",
  "compilerOptions": {
    "deleteOutDir": true,
    "builder": "rspack",
    "tsConfigPath": "apps/my-project/tsconfig.app.json"
  },
  "monorepo": true,
  "root": "apps/my-project",
  "projects": {
    "my-app": {
      "type": "application",
      "root": "apps/my-app",
      "entryFile": "main",
      "sourceRoot": "apps/my-app/src",
      "compilerOptions": {
        "tsConfigPath": "apps/my-app/tsconfig.app.json"
      }
    },
    "my-project": {
      "type": "application",
      "root": "apps/my-project",
      "entryFile": "main",
      "sourceRoot": "apps/my-project/src",
      "compilerOptions": {
        "tsConfigPath": "apps/my-project/tsconfig.app.json"
      }
    }
  }
}
```

File được chia thành các phần:

- một phần global với các thuộc tính cấp cao nhất kiểm soát thiết lập cho standard và toàn monorepo
- một thuộc tính cấp cao nhất (`"projects"`) chứa metadata về từng project. Phần này chỉ có trong cấu trúc monorepo mode.

Các thuộc tính cấp cao nhất như sau:

- `"collection"`: trỏ tới collection các schematic dùng để sinh thành phần; nhìn chung bạn không nên thay đổi giá trị này
- `"sourceRoot"`: trỏ tới thư mục gốc chứa mã nguồn của project duy nhất trong cấu trúc standard mode, hoặc của _project mặc định_ trong cấu trúc monorepo mode
- `"compilerOptions"`: một map với key chỉ định tùy chọn của trình biên dịch và value chỉ định thiết lập của tùy chọn; xem chi tiết bên dưới
- `"generateOptions"`: một map với key chỉ định tùy chọn generate global và value chỉ định thiết lập của tùy chọn; xem chi tiết bên dưới
- `"monorepo"`: (chỉ monorepo) luôn là `true` với một cấu trúc monorepo mode
- `"root"`: (chỉ monorepo) trỏ tới thư mục gốc của _project mặc định_

#### Tùy chọn trình biên dịch global <a id="global-compiler-options"></a>

Các thuộc tính này chỉ định trình biên dịch cần dùng, cũng như các tùy chọn ảnh hưởng tới **mọi** bước biên dịch, dù nó chạy như một phần của `nest build` hay `nest start`, và bất kể bạn dùng trình biên dịch nào (`tsc`, `swc` hay Rspack).

| Tên thuộc tính      | Type của giá trị    | Mô tả                                                                                                                                                                                                                                                                     |
| ------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `webpack`           | boolean             | Cờ cũ đã deprecated cho việc biên dịch dựa trên webpack. Hãy dùng `builder` thay vào đó. |
| `tsConfigPath`      | string              | (**chỉ monorepo**) Trỏ tới file chứa thiết lập `tsconfig.json` sẽ được dùng khi `nest build` hoặc `nest start` được gọi mà không có tùy chọn `project` (ví dụ khi project mặc định được build hoặc khởi động).                                                             |
| `webpackConfigPath` | string              | Đường dẫn cũ đã deprecated cho các tùy chọn webpack. Hãy dùng `builder.options.configPath` thay vào đó.                                                                                                                                                                   |
| `deleteOutDir`      | boolean             | Nếu là `true`, trình biên dịch sẽ xóa thư mục output biên dịch trước (như được cấu hình trong `tsconfig.json`; mặc định là `./dist`) mỗi khi nó được gọi.                                                                                                                 |
| `assets`            | array               | Bật việc tự động phân phối các asset không phải TypeScript mỗi khi một bước biên dịch bắt đầu (asset **không** được phân phối ở các lần biên dịch tăng dần trong chế độ `--watch`). Xem bên dưới để biết chi tiết.                                                         |
| `watchAssets`       | boolean             | Nếu là `true`, chạy ở watch mode, theo dõi **mọi** asset không phải TypeScript. (Để kiểm soát chi tiết hơn những asset nào cần theo dõi, xem phần [Asset](/cli/monorepo#assets) bên dưới.)                                                                                 |
| `manualRestart`     | boolean             | Nếu là `true`, bật phím tắt `rs` để tự restart server. Mặc định là `false`.                                                                                                                                                                                               |
| `builder`           | string/object       | Builder mà CLI dùng để biên dịch project (`tsc`, `swc` hoặc `rspack`). Để tùy chỉnh hành vi của builder, hãy truyền một object có hai thuộc tính: `type` (`tsc`, `swc` hoặc `rspack`) và `options`.                                                                       |
| `typeCheck`         | boolean             | Nếu là `true`, bật type checking cho các project chạy bằng SWC (khi `builder` là `swc`). Mặc định là `false`.                                                                                                                                                              |
| `emitDeclarations`  | boolean             | Nếu là `true`, phát ra các file khai báo (`.d.ts`) khi dùng SWC builder. Mặc định là `false`.                                                                                                                                                                             |
| `includeLibraryAssets` | array            | (**chỉ monorepo**) Danh sách tên các project library mà asset của chúng cũng cần được copy khi build ứng dụng này.                                                                                                                                                        |

> warning **Cảnh báo** Ở monorepo mode, `compilerOptions` của một project không được merge với `compilerOptions` cấp cao nhất. Ví dụ, một mảng `assets` ở cấp project sẽ thay thế mảng `assets` cấp cao nhất thay vì cộng thêm vào nó. Để copy cả asset của một library khi build một ứng dụng, hãy liệt kê library đó trong `includeLibraryAssets`.

#### Tùy chọn generate global <a id="global-generate-options"></a>

Các thuộc tính này chỉ định các tùy chọn mặc định cho lệnh `nest generate`.

| Tên thuộc tính | Type của giá trị   | Mô tả                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `spec`        | boolean _hoặc_ object | Nếu giá trị là boolean, `true` bật việc sinh `spec` theo mặc định và `false` tắt nó. Một cờ được truyền trên command line sẽ ghi đè thiết lập này, một thiết lập `generateOptions` riêng của project cũng vậy (xem bên dưới). Nếu giá trị là object, mỗi key là một tên schematic, và giá trị boolean của nó bật hoặc tắt việc sinh spec mặc định cho schematic đó. |
| `flat`        | boolean             | Nếu là `true`, mọi lệnh generate đều sinh ra cấu trúc phẳng.                                                                                                                                                                                                                                                                                                                                                                                  |

Ví dụ sau dùng một giá trị boolean để tắt việc sinh file spec theo mặc định cho mọi project:

```javascript
{
  "generateOptions": {
    "spec": false
  },
  ...
}
```

Ví dụ sau dùng một giá trị boolean để đặt việc sinh file theo cấu trúc phẳng làm mặc định cho mọi project:

```javascript
{
  "generateOptions": {
    "flat": true
  },
  ...
}
```

Trong ví dụ sau, việc sinh file `spec` chỉ bị tắt cho các schematic `service` (ví dụ `nest generate service...`):

```javascript
{
  "generateOptions": {
    "spec": {
      "service": false
    }
  },
  ...
}
```

> warning **Cảnh báo** Khi bạn chỉ định `spec` dưới dạng object, các key schematic không hỗ trợ alias. Ví dụ, nếu bạn đặt `service: false` rồi sinh một service qua alias `s` của nó, file spec vẫn được sinh ra. Để bao phủ cả tên schematic lẫn alias của nó, hãy chỉ định cả hai, như bên dưới.
>
> ```javascript
> {
>   "generateOptions": {
>     "spec": {
>       "service": false,
>       "s": false
>     }
>   },
>   ...
> }
> ```

#### Tùy chọn generate riêng của project <a id="project-specific-generate-options"></a>

Ngoài các tùy chọn generate global, bạn có thể chỉ định các tùy chọn generate riêng của project. Chúng dùng cùng định dạng với các tùy chọn global, nhưng bạn đặt chúng trực tiếp trên từng project.

Tùy chọn generate riêng của project ghi đè tùy chọn generate global.

```javascript
{
  "projects": {
    "cats-project": {
      "generateOptions": {
        "spec": {
          "service": false
        }
      },
      ...
    }
  },
  ...
}
```

> warning **Cảnh báo** Các tùy chọn generate được áp dụng theo thứ tự ưu tiên sau: tùy chọn được truyền trên command line được ưu tiên hơn tùy chọn riêng của project, và tùy chọn riêng của project lại ghi đè tùy chọn global.

#### Trình biên dịch được chỉ định <a id="specified-compiler"></a>

Standard mode và monorepo mode dùng trình biên dịch mặc định khác nhau vì, với các project lớn hơn (thường gặp hơn trong monorepo), Rspack có thể giảm đáng kể thời gian build và tạo ra một file duy nhất bundle mọi thành phần của project lại với nhau. Để sinh ra các file riêng lẻ thay vào đó, hãy đặt builder thành `tsc` hoặc `swc`.

#### Asset <a id="assets"></a>

Quá trình biên dịch TypeScript tự động phân phối output của trình biên dịch (các file `.js` và `.d.ts`) vào thư mục output được chỉ định. Việc phân phối cả các file không phải TypeScript, như file `.graphql`, hình ảnh, file `.html` và các asset khác, cũng có thể rất tiện. Điều này cho phép bạn coi `nest build` (và mọi bước biên dịch ban đầu) như một bước **development build** gọn nhẹ, trong đó bạn sửa các file không phải TypeScript, biên dịch và test lặp đi lặp lại.
Asset phải nằm trong thư mục `src`; nếu không, chúng sẽ không được copy.

Giá trị của key `assets` là một mảng các phần tử chỉ định các file cần phân phối. Các phần tử có thể là chuỗi đơn giản với đặc tả file kiểu `glob`, ví dụ:

```typescript
"assets": ["**/*.graphql"],
"watchAssets": true,
```

Để kiểm soát chi tiết hơn, các phần tử có thể là object với các key sau:

- `"include"`: đặc tả file kiểu `glob` cho các asset cần phân phối
- `"exclude"`: đặc tả file kiểu `glob` cho các asset cần **loại trừ** khỏi danh sách `include`
- `"outDir"`: đường dẫn (tương đối so với thư mục gốc) để phân phối asset tới. Mặc định là thư mục output được cấu hình cho output của trình biên dịch.
- `"watchAssets"`: boolean; nếu là `true`, chạy ở watch mode, theo dõi các asset được chỉ định

Ví dụ:

```typescript
"assets": [
  { "include": "**/*.graphql", "exclude": "**/omitted.graphql", "watchAssets": true },
]
```

> warning **Cảnh báo** Đặt `watchAssets` trong thuộc tính `compilerOptions` cấp cao nhất sẽ ghi đè mọi thiết lập `watchAssets` bên trong thuộc tính `assets`.

#### Thuộc tính của project <a id="project-properties"></a>

Phần này chỉ tồn tại trong cấu trúc monorepo mode. Nhìn chung bạn không nên sửa các thuộc tính này, vì Nest dùng chúng để định vị các project và tùy chọn cấu hình của chúng bên trong monorepo.
