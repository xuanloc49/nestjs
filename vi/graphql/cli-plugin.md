### CLI Plugin

> warning **Cảnh báo** Chương này chỉ áp dụng cho cách tiếp cận code first.

Hệ thống metadata reflection của TypeScript có một số hạn chế khiến việc, chẳng hạn, xác định một class gồm những thuộc tính nào, hay một thuộc tính là tùy chọn hay bắt buộc, trở nên bất khả thi. Tuy nhiên, một số ràng buộc này có thể được giải quyết lúc biên dịch. Nest cung cấp một plugin cải tiến quá trình biên dịch TypeScript để giảm lượng code boilerplate cần viết.

> info **Gợi ý** Plugin này là **tùy chọn bật thêm (opt-in)**. Nếu muốn, bạn có thể tự khai báo mọi decorator, hoặc chỉ khai báo những decorator cụ thể ở nơi bạn cần.

#### Tổng quan <a id="overview"></a>

GraphQL plugin tự động làm những việc sau:

- chú thích mọi thuộc tính của các class input object, object type và args bằng `@Field`, trừ khi có dùng `@HideField`
- đặt thuộc tính `nullable` tùy vào dấu chấm hỏi (ví dụ `name?: string` sẽ đặt `nullable: true`)
- đặt thuộc tính `type` tùy vào type (mảng cũng được hỗ trợ)
- sinh mô tả cho các thuộc tính dựa trên comment (nếu `introspectComments` được đặt thành `true`)

Tên file của bạn **phải có** một trong các hậu tố sau để được plugin phân tích: `['.input.ts', '.args.ts', '.entity.ts', '.model.ts']` (ví dụ `author.entity.ts`). Nếu bạn dùng một hậu tố khác, hãy điều chỉnh hành vi của plugin bằng tùy chọn `typeFileNameSuffix` (xem bên dưới).

Với những gì chúng ta đã đề cập cho tới giờ, bạn phải lặp lại rất nhiều code để cho package biết type của bạn nên được khai báo thế nào trong GraphQL. Ví dụ, bạn có thể định nghĩa một class `Author` như sau:

```typescript
@@filename(authors/models/author.model)
@ObjectType()
export class Author {
  @Field(type => ID)
  id: number;

  @Field({ nullable: true })
  firstName?: string;

  @Field({ nullable: true })
  lastName?: string;

  @Field(type => [Post])
  posts: Post[];
}
```

Dù đây không phải vấn đề lớn với các project cỡ vừa, nó trở nên dài dòng và khó bảo trì khi bạn có một tập class lớn.

Khi bật GraphQL plugin, định nghĩa class ở trên có thể được khai báo như sau:

```typescript
@@filename(authors/models/author.model)
@ObjectType()
export class Author {
  @Field(type => ID)
  id: number;
  firstName?: string;
  lastName?: string;
  posts: Post[];
}
```

Plugin thêm các decorator phù hợp ngay trong lúc biên dịch dựa trên **cây cú pháp trừu tượng (Abstract Syntax Tree)**, nên bạn không phải rải decorator `@Field` khắp code.

> info **Gợi ý** Plugin tự động sinh mọi thuộc tính GraphQL còn thiếu. Nếu bạn cần ghi đè chúng, hãy đặt chúng một cách tường minh bằng `@Field()`.

#### Đọc comment <a id="comments-introspection"></a>

Khi bật tính năng đọc comment, CLI plugin sinh mô tả cho các field dựa trên comment.

Ví dụ, xét thuộc tính `roles`:

```typescript
/**
 * A list of user's roles
 */
@Field(() => [String], {
  description: `A list of user's roles`
})
roles: string[];
```

Ở đây, bạn phải lặp lại phần mô tả. Khi bật `introspectComments`, CLI plugin lấy các comment này và tự động cung cấp mô tả cho các thuộc tính. Khi đó field ở trên có thể được khai báo như sau:

```typescript
/**
 * A list of user's roles
 */
roles: string[];
```

#### Dùng CLI plugin <a id="using-the-cli-plugin"></a>

Để bật plugin, hãy mở `nest-cli.json` (nếu bạn dùng [Nest CLI](/cli/overview)) và thêm cấu hình `plugins` sau:

```javascript
{
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "plugins": ["@nestjs/graphql"]
  }
}
```

Dùng thuộc tính `options` để tùy chỉnh hành vi của plugin:

```javascript
{
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "plugins": [
      {
        "name": "@nestjs/graphql",
        "options": {
          "typeFileNameSuffix": [".input.ts", ".args.ts"],
          "introspectComments": true
        }
      }
    ]
  }
}

```

Thuộc tính `options` nhận các tùy chọn sau:

```typescript
export interface PluginOptions {
  typeFileNameSuffix?: string | string[];
  introspectComments?: boolean;
  esmCompatible?: boolean;
  debug?: boolean;
}
```

<table>
  <tr>
    <th>Tùy chọn</th>
    <th>Mặc định</th>
    <th>Mô tả</th>
  </tr>
  <tr>
    <td><code>typeFileNameSuffix</code></td>
    <td><code>['.input.ts', '.args.ts', '.entity.ts', '.model.ts']</code></td>
    <td>Hậu tố của các file chứa GraphQL type</td>
  </tr>
  <tr>
    <td><code>introspectComments</code></td>
    <td><code>false</code></td>
    <td>Nếu đặt thành <code>true</code>, plugin sẽ sinh mô tả cho các thuộc tính dựa trên comment</td>
  </tr>
  <tr>
    <td><code>esmCompatible</code></td>
    <td>Suy ra từ định dạng module của từng file</td>
    <td>Nếu đặt thành <code>true</code>, plugin sẽ phát ra code tương thích ESM (không có lời gọi <code>require()</code>, và phần mở rộng của output được nối vào các import tương đối).</td>
  </tr>
  <tr>
    <td><code>debug</code></td>
    <td><code>false</code></td>
    <td>Nếu đặt thành <code>true</code>, plugin sẽ log các message chẩn đoán (ví dụ khi nó tìm thấy một type không được export)</td>
  </tr>
</table>

Nếu bạn không dùng CLI mà có cấu hình `webpack` tùy chỉnh, bạn có thể dùng plugin này kết hợp với `ts-loader`:

```javascript
getCustomTransformers: (program) => ({
  before: [require('@nestjs/graphql/plugin').before({}, program)]
}),
```

#### SWC builder

Với cách thiết lập tiêu chuẩn (không phải monorepo), dùng CLI plugin với SWC builder yêu cầu bật type checking, như mô tả trong [SWC type checking](/recipes/swc#type-checking).

```bash
$ nest start -b swc --type-check
```

Với cách thiết lập monorepo, hãy làm theo hướng dẫn trong [monorepo và CLI plugin](/recipes/swc#monorepo-and-cli-plugins).

```bash
$ npx ts-node src/generate-metadata.ts
# OR npx ts-node apps/{YOUR_APP}/src/generate-metadata.ts
```

Sau đó, load file metadata đã được serialize trong cấu hình `GraphQLModule`, như bên dưới:

```typescript
import metadata from './metadata.js'; // <-- file auto-generated by the "PluginMetadataGenerator"

GraphQLModule.forRoot<...>({
  ..., // other options
  metadata,
}),
```

#### Tích hợp với `ts-jest` (e2e test) <a id="integration-with-ts-jest-e2e-tests"></a>

Khi bạn chạy e2e test với plugin này được bật, bạn có thể gặp vấn đề khi biên dịch schema. Ví dụ, một trong những lỗi phổ biến nhất là:

```json
Object type <name> must define one or more fields.
```

Điều này xảy ra vì cấu hình `jest` không import plugin `@nestjs/graphql/plugin` ở đâu cả.

Để sửa, hãy tạo file sau trong thư mục e2e test của bạn:

```javascript
const transformer = require('@nestjs/graphql/plugin');

module.exports.name = 'nestjs-graphql-transformer';
// you should change the version number anytime you change the configuration below - otherwise, jest will not detect changes
module.exports.version = 1;

module.exports.factory = (cs) => {
  return transformer.before(
    {
      // @nestjs/graphql/plugin options (can be empty)
    },
    cs.program, // "cs.tsCompiler.program" for older versions of Jest (<= v27)
  );
};
```

Khi đã có file này, hãy import AST transformer trong file cấu hình `jest`. Mặc định (trong ứng dụng starter), file cấu hình e2e test nằm trong thư mục `test` và có tên `jest-e2e.json`.

```json
{
  ... // other configuration
  "globals": {
    "ts-jest": {
      "astTransformers": {
        "before": ["<path to the file created above>"]
      }
    }
  }
}
```

Nếu bạn dùng `jest@^29` trở lên, hãy dùng đoạn code bên dưới thay vào đó, vì cách trước đã bị deprecated.

```json
{
  ... // other configuration
  "transform": {
    "^.+\\.(t|j)s$": [
      "ts-jest",
      {
        "astTransformers": {
          "before": ["<path to the file created above>"]
        }
      }
    ]
  }
}
```
