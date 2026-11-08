### SWC

[SWC](https://swc.rs/) (Speedy Web Compiler) là một nền tảng có thể mở rộng, viết bằng Rust, dùng được cho cả biên dịch lẫn bundling. Dùng SWC với Nest CLI là một cách đơn giản để tăng tốc đáng kể quá trình phát triển.

> info **Gợi ý** SWC nhanh hơn trình biên dịch TypeScript mặc định khoảng **20 lần**.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, trước tiên hãy cài một vài package:

```bash
$ npm i --save-dev @swc/cli @swc/core
```

#### Bắt đầu <a id="getting-started"></a>

Khi đã cài đặt xong, bạn có thể dùng builder `swc` với Nest CLI, như sau:

```bash
$ nest start -b swc
# OR nest start --builder swc
```

> info **Gợi ý** Nếu repository của bạn là monorepo, xem phần [Monorepo](/recipes/swc#monorepo).

Thay vì truyền cờ `-b`, bạn có thể đặt thuộc tính `compilerOptions.builder` thành `"swc"` trong file `nest-cli.json`:

```json
{
  "compilerOptions": {
    "builder": "swc"
  }
}
```

Để tùy chỉnh hành vi của builder, hãy truyền một object chứa hai thuộc tính, `type` (`"swc"`) và `options`, như sau:

```json
{
  "compilerOptions": {
    "builder": {
      "type": "swc",
      "options": {
        "swcrcPath": "infrastructure/.swcrc",
      }
    }
  }
}
```

Ví dụ, để SWC biên dịch các file `.jsx` và `.tsx`, hãy dùng cấu hình sau:

```json
{
  "compilerOptions": {
    "builder": {
      "type": "swc",
      "options": { "extensions": [".ts", ".tsx", ".js", ".jsx"] }
    },
  }
}

```

Để chạy ứng dụng ở watch mode, hãy dùng lệnh sau:

```bash
$ nest start -b swc -w
# OR nest start --builder swc --watch
```

#### Type checking

Khác với trình biên dịch TypeScript mặc định, bản thân SWC không thực hiện type checking. Để bật type checking, hãy dùng cờ `--type-check`:

```bash
$ nest start -b swc --type-check
```

Lệnh này chỉ thị Nest CLI chạy `tsc` ở chế độ `noEmit` song song với SWC, thực hiện type checking một cách bất đồng bộ. Thay vì truyền cờ `--type-check`, bạn cũng có thể đặt thuộc tính `compilerOptions.typeCheck` thành `true` trong file `nest-cli.json`:

```json
{
  "compilerOptions": {
    "builder": "swc",
    "typeCheck": true
  }
}
```

#### CLI plugin (SWC) <a id="cli-plugins-swc"></a>

Cờ `--type-check` tự động thực thi các **CLI plugin của NestJS** và tạo ra một file metadata đã được serialize, file này sau đó ứng dụng có thể load lúc runtime.

#### Cấu hình SWC <a id="swc-configuration"></a>

SWC builder được cấu hình sẵn để đáp ứng yêu cầu của các ứng dụng NestJS. Tuy nhiên, bạn có thể tùy chỉnh cấu hình bằng cách tạo một file `.swcrc` ở thư mục gốc và điều chỉnh các tùy chọn khi cần:

```json
{
  "$schema": "https://swc.rs/schema.json",
  "sourceMaps": true,
  "jsc": {
    "parser": {
      "syntax": "typescript",
      "decorators": true,
      "dynamicImport": true
    },
    "baseUrl": "./"
  },
  "minify": false
}
```

> info **Gợi ý** SWC builder phát ra cùng định dạng module như trình biên dịch TypeScript sẽ làm: ES module khi file `package.json` của bạn đặt `"type": "module"` (mặc định với project mới), và CommonJS trong trường hợp ngược lại. Thiết lập `module` trong `.swcrc` sẽ ghi đè điều này.

#### Monorepo

> info **Gợi ý** Từ NestJS v12, monorepo mặc định dùng Rspack builder, builder này đã biên dịch code của bạn bằng SWC (qua `swc-loader` có sẵn của Rspack). Cách thiết lập sau chỉ áp dụng nếu bạn dùng webpack builder đã bị deprecated.

Nếu repository của bạn là monorepo, thì thay vì dùng builder `swc`, bạn phải cấu hình `webpack` để dùng `swc-loader`.

Trước tiên, hãy cài package cần thiết:

```bash
$ npm i --save-dev swc-loader
```

Khi đã cài đặt xong, hãy tạo một file `webpack.config.js` ở thư mục gốc của ứng dụng với nội dung sau:

```js
const swcDefaultConfig = require('@nestjs/cli/lib/compiler/defaults/swc-defaults').swcDefaultsFactory().swcOptions;

module.exports = {
  module: {
    rules: [
      {
        test: /\.ts$/,
        exclude: /node_modules/,
        use: {
          loader: 'swc-loader',
          options: swcDefaultConfig,
        },
      },
    ],
  },
};
```

#### Monorepo và CLI plugin <a id="monorepo-and-cli-plugins"></a>

Nếu bạn dùng CLI plugin, `swc-loader` không tự động load chúng. Thay vào đó, bạn phải tạo một file riêng để tự load chúng. Để làm vậy, hãy tạo một file `generate-metadata.ts` cạnh file `main.ts` với nội dung sau:

```ts
import { PluginMetadataGenerator } from '@nestjs/cli/lib/compiler/plugins/plugin-metadata-generator.js';
import { ReadonlyVisitor } from '@nestjs/swagger/plugin';

const generator = new PluginMetadataGenerator();
generator.generate({
  visitors: [new ReadonlyVisitor({ introspectComments: true, pathToSource: import.meta.dirname })],
  outputDir: import.meta.dirname,
  watch: true,
  tsconfigPath: 'apps/<name>/tsconfig.app.json',
});
```

> info **Gợi ý** Ví dụ này dùng plugin `@nestjs/swagger`, nhưng bạn có thể dùng bất kỳ plugin nào bạn chọn.

Method `generate()` nhận các tùy chọn sau:

|                    |                                                                                                |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| `watch`            | Có theo dõi thay đổi của project hay không.                                                    |
| `tsconfigPath`     | Đường dẫn tới file `tsconfig.json`. Tương đối so với thư mục làm việc hiện tại (`process.cwd()`). |
| `outputDir`        | Đường dẫn tới thư mục nơi file metadata được lưu.                                              |
| `visitors`         | Một mảng visitor dùng để sinh metadata.                                                        |
| `filename`         | Tên của file metadata. Mặc định là `metadata.ts`.                                              |
| `printDiagnostics` | Có in thông tin chẩn đoán ra console hay không. Mặc định là `true`.                            |

Cuối cùng, hãy chạy script `generate-metadata` trong một cửa sổ terminal riêng bằng lệnh sau:

```bash
$ npx ts-node src/generate-metadata.ts
# OR npx ts-node apps/{YOUR_APP}/src/generate-metadata.ts
```

#### Những lỗi thường gặp <a id="common-pitfalls"></a>

Nếu bạn dùng TypeORM, MikroORM, hoặc bất kỳ ORM nào khác trong ứng dụng, bạn có thể gặp vấn đề circular import. SWC không xử lý tốt **circular import**, nên hãy dùng cách khắc phục sau:

```typescript
@Entity()
export class User {
  @OneToOne(() => Profile, (profile) => profile.user)
  profile: Relation<Profile>; // <--- see "Relation<>" type here instead of just "Profile"
}
```

> info **Gợi ý** Type `Relation` được export từ package `typeorm`.

Điều này ngăn type của thuộc tính bị lưu vào metadata thuộc tính của code đã transpile, tránh được các vấn đề phụ thuộc vòng tròn.

Nếu ORM của bạn không cung cấp cách khắc phục tương tự, bạn có thể tự định nghĩa wrapper type:

```typescript
/**
 * Wrapper type used to circumvent ESM modules circular dependency issue
 * caused by reflection metadata saving the type of the property.
 */
export type WrapperType<T> = T; // WrapperType === Relation
```

Với mọi [circular dependency injection](/fundamentals/circular-dependency) trong project, bạn cũng cần dùng wrapper type tùy chỉnh được mô tả ở trên:

```typescript
@Injectable()
export class UsersService {
  constructor(
    @Inject(forwardRef(() => ProfileService))
    private readonly profileService: WrapperType<ProfileService>,
  ) {}
}
```

### Jest + SWC

Để dùng SWC với Jest (test runner mặc định cho các project CommonJS), hãy cài các package sau:

```bash
$ npm i --save-dev jest @swc/core @swc/jest
```

Khi đã cài đặt xong, hãy cập nhật file `package.json` hoặc `jest.config.js` (tùy cấu hình của bạn) với nội dung sau:

```json
{
  "jest": {
    "transform": {
      "^.+\\.(t|j)s?$": ["@swc/jest"]
    }
  }
}
```

Ngoài ra, hãy thêm các thuộc tính `transform` `legacyDecorator` và `decoratorMetadata` vào file `.swcrc`:

```json
{
  "$schema": "https://swc.rs/schema.json",
  "sourceMaps": true,
  "jsc": {
    "parser": {
      "syntax": "typescript",
      "decorators": true,
      "dynamicImport": true
    },
    "transform": {
      "legacyDecorator": true,
      "decoratorMetadata": true
    },
    "baseUrl": "./"
  },
  "minify": false
}
```

Nếu bạn dùng CLI plugin của NestJS trong project, bạn phải tự chạy `PluginMetadataGenerator`. Xem phần [Monorepo và CLI plugin](/recipes/swc#monorepo-and-cli-plugins) để tìm hiểu thêm.

### Vitest

[Vitest](https://vitest.dev/) là một test runner nhanh, gọn nhẹ, được thiết kế để làm việc với Vite. Các project NestJS mới dùng ES module (mặc định) đã được thiết lập sẵn với Vitest. Phần này cho thấy cách cấu hình Vitest để build các file test bằng SWC.

#### Cài đặt <a id="installation-1"></a>

Để bắt đầu, trước tiên hãy cài các package cần thiết:

```bash
$ npm i --save-dev vitest unplugin-swc @swc/core @vitest/coverage-v8
```

#### Cấu hình <a id="configuration"></a>

Tạo một file `vitest.config.ts` ở thư mục gốc của ứng dụng với nội dung sau:

```ts
import { resolve } from 'node:path';
import swc from 'unplugin-swc';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    root: './',
  },
  plugins: [
    // This is required to build the test files with SWC
    swc.vite({
      // Explicitly set the module type to avoid inheriting this value from a `.swcrc` config file
      module: { type: 'es6' },
    }),
  ],
  resolve: {
    alias: {
      // Ensure Vitest correctly resolves TypeScript path aliases
      'src': resolve(import.meta.dirname, './src'),
    },
  },
});
```

File cấu hình này thiết lập môi trường Vitest, thư mục gốc và plugin SWC. Bạn cũng nên tạo một file cấu hình riêng cho e2e test (ví dụ `vitest.config.e2e.ts`), với thêm một field `include` chỉ định glob pattern cho các file test:

```ts
import swc from 'unplugin-swc';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['**/*.e2e-spec.ts'],
    globals: true,
    root: './',
  },
  plugins: [swc.vite()],
});
```

Ngoài ra, bạn có thể đặt các tùy chọn `alias` để hỗ trợ path của TypeScript trong test:

```ts
import swc from 'unplugin-swc';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['**/*.e2e-spec.ts'],
    globals: true,
    alias: {
      '@src': './src',
      '@test': './test',
    },
    root: './',
  },
  resolve: {
    alias: {
      '@src': './src',
      '@test': './test',
    },
  },
  plugins: [swc.vite()],
});
```

### Path alias <a id="path-aliases"></a>

Vitest không tự động resolve các path alias của TypeScript như `src/`, điều này có thể dẫn tới lỗi resolve dependency khi test. Để sửa, hãy thêm cấu hình `resolve.alias` sau vào file `vitest.config.ts`:

```ts
import { resolve } from 'node:path';

export default defineConfig({
  resolve: {
    alias: {
      'src': resolve(import.meta.dirname, './src'),
    },
  },
});
```

Điều này đảm bảo Vitest resolve đúng các module import, tránh các lỗi liên quan tới dependency bị thiếu.

#### Cập nhật import trong E2E test <a id="update-imports-in-e2e-tests"></a>

Hãy đổi mọi import trong E2E test dùng `import * as request from 'supertest'` thành `import request from 'supertest'`. `supertest` là một module CommonJS export một hàm, và trong một cách thiết lập ES module như của Vitest, một namespace import không thể gọi được, nên bạn cần default import.

Cuối cùng, hãy cập nhật các script test trong file `package.json`:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:cov": "vitest run --coverage",
    "test:debug": "vitest --inspect-brk --no-file-parallelism",
    "test:e2e": "vitest run --config ./vitest.config.e2e.ts"
  }
}
```

Các script này chạy test, theo dõi thay đổi, sinh báo cáo code coverage, và khởi động một phiên debug. Script `test:e2e` chạy E2E test với file cấu hình riêng.

> info **Gợi ý** Một ví dụ chạy được có trong [repository nest-vitest](https://github.com/TrilonIO/nest-vitest).
