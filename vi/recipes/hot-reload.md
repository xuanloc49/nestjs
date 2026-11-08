### Hot Reload

**Việc biên dịch TypeScript** ảnh hưởng lớn nhất tới thời gian bootstrap ứng dụng. Với [webpack](https://github.com/webpack/webpack) HMR (Hot-Module Replacement), bạn không cần biên dịch lại toàn bộ project mỗi khi có thay đổi. Điều này giảm đáng kể thời gian khởi tạo ứng dụng và giúp việc phát triển lặp đi lặp lại nhanh hơn nhiều.

> warning **Cảnh báo** `webpack` không tự động copy asset (ví dụ các file `graphql`) vào thư mục `dist`. Tương tự, `webpack` không tương thích với các glob path tĩnh (ví dụ thuộc tính `entities` trong `TypeOrmModule`).

> warning **Cảnh báo** Từ NestJS v12, webpack builder đã bị **deprecated** và Rspack là bundler mặc định cho monorepo. Recipe này nhắm tới các project CommonJS dựa trên webpack, đó là lý do các ví dụ bên dưới dùng `module.hot` và một lời gọi `bootstrap()` thuần thay vì top-level `await` của ESM được dùng ở những chỗ khác trong tài liệu này. Với project mới, hãy ưu tiên `--builder rspack`.

### Với CLI <a id="with-cli"></a>

Nếu bạn dùng [Nest CLI](/cli/overview), quá trình cấu hình khá đơn giản. CLI bọc `webpack`, cho phép bạn dùng `HotModuleReplacementPlugin`.

#### Cài đặt <a id="installation"></a>

Trước tiên, hãy cài các package cần thiết:

```bash
$ npm i --save-dev webpack-node-externals run-script-webpack-plugin webpack
```

> info **Gợi ý** Nếu bạn dùng **Yarn Berry** (không phải Yarn classic), hãy cài package `webpack-pnp-externals` thay cho `webpack-node-externals`.

#### Cấu hình <a id="configuration"></a>

Khi đã cài đặt xong, hãy tạo một file `webpack-hmr.config.js` ở thư mục gốc của ứng dụng:

```typescript
const nodeExternals = require('webpack-node-externals');
const { RunScriptWebpackPlugin } = require('run-script-webpack-plugin');

module.exports = function (options, webpack) {
  return {
    ...options,
    entry: ['webpack/hot/poll?100', options.entry],
    externals: [
      nodeExternals({
        allowlist: ['webpack/hot/poll?100'],
      }),
    ],
    plugins: [
      ...options.plugins,
      new webpack.HotModuleReplacementPlugin(),
      new webpack.WatchIgnorePlugin({
        paths: [/\.js$/, /\.d\.ts$/],
      }),
      new RunScriptWebpackPlugin({ name: options.output.filename, autoRestart: false }),
    ],
  };
};
```

> info **Gợi ý** Với **Yarn Berry** (không phải Yarn classic), thay vì dùng `nodeExternals` trong thuộc tính cấu hình `externals`, hãy dùng `WebpackPnpExternals` từ package `webpack-pnp-externals`: `WebpackPnpExternals({{ '{' }} exclude: ['webpack/hot/poll?100'] {{ '}' }})`.

Hàm này nhận object gốc chứa cấu hình webpack mặc định làm tham số đầu tiên, và một tham chiếu tới package `webpack` bên dưới mà Nest CLI dùng làm tham số thứ hai. Nó trả về một cấu hình webpack đã được sửa đổi với các plugin `HotModuleReplacementPlugin`, `WatchIgnorePlugin` và `RunScriptWebpackPlugin`.

#### Hot-Module Replacement

Để bật **HMR**, hãy mở file entry của ứng dụng (`main.ts`) và thêm các chỉ dẫn liên quan tới webpack sau:

```typescript
declare const module: any;

async function bootstrap() {
  if (module.hot?.data?.closePromise) {
    // wait for the previous application instance to fully shut down
    await module.hot.data.closePromise;
  }

  const app = await NestFactory.create(AppModule, {
    forceCloseConnections: !!module.hot,
  });
  await app.listen(process.env.PORT ?? 3000);

  if (module.hot) {
    module.hot.accept();
    module.hot.dispose((data: any) => {
      data.closePromise = app.close();
    });
  }
}
bootstrap();
```

> info **Gợi ý** `app.close()` là bất đồng bộ, nhưng webpack không await callback `dispose()`. Cất promise được trả về vào `module.hot.data` cho phép instance ứng dụng tiếp theo await nó trước khi bind lại vào port, điều này (cùng với `forceCloseConnections`) ngăn lỗi `EADDRINUSE` khi reload.

Để đơn giản hóa quá trình chạy, hãy thêm một script vào file `package.json`:

```json
"start:dev": "nest build --webpack --webpackPath webpack-hmr.config.js --watch"
```

Sau đó chạy lệnh sau:

```bash
$ npm run start:dev
```

### Không dùng CLI <a id="without-cli"></a>

Nếu bạn không dùng [Nest CLI](/cli/overview), việc cấu hình phức tạp hơn một chút và cần nhiều bước thủ công hơn.

#### Cài đặt <a id="installation-1"></a>

Trước tiên, hãy cài các package cần thiết:

```bash
$ npm i --save-dev webpack webpack-cli webpack-node-externals ts-loader run-script-webpack-plugin
```

> info **Gợi ý** Nếu bạn dùng **Yarn Berry** (không phải Yarn classic), hãy cài package `webpack-pnp-externals` thay cho `webpack-node-externals`.

#### Cấu hình <a id="configuration-1"></a>

Khi đã cài đặt xong, hãy tạo một file `webpack.config.js` ở thư mục gốc của ứng dụng:

```typescript
const webpack = require('webpack');
const path = require('path');
const nodeExternals = require('webpack-node-externals');
const { RunScriptWebpackPlugin } = require('run-script-webpack-plugin');

module.exports = {
  entry: ['webpack/hot/poll?100', './src/main.ts'],
  target: 'node',
  externals: [
    nodeExternals({
      allowlist: ['webpack/hot/poll?100'],
    }),
  ],
  module: {
    rules: [
      {
        test: /.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  mode: 'development',
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
  },
  plugins: [new webpack.HotModuleReplacementPlugin(), new RunScriptWebpackPlugin({ name: 'server.js', autoRestart: false })],
  output: {
    path: path.join(__dirname, 'dist'),
    filename: 'server.js',
  },
};
```

> info **Gợi ý** Với **Yarn Berry** (không phải Yarn classic), thay vì dùng `nodeExternals` trong thuộc tính cấu hình `externals`, hãy dùng `WebpackPnpExternals` từ package `webpack-pnp-externals`: `WebpackPnpExternals({{ '{' }} exclude: ['webpack/hot/poll?100'] {{ '}' }})`.

Cấu hình này cho webpack biết vài điều thiết yếu về ứng dụng của bạn: vị trí của file entry, thư mục chứa các file **đã biên dịch**, và loader dùng để biên dịch các file mã nguồn. Nhìn chung bạn có thể dùng nguyên file này, kể cả khi chưa hiểu hết mọi tùy chọn.

#### Hot-Module Replacement

Để bật **HMR**, hãy mở file entry của ứng dụng (`main.ts`) và thêm các chỉ dẫn liên quan tới webpack sau:

```typescript
declare const module: any;

async function bootstrap() {
  if (module.hot?.data?.closePromise) {
    // wait for the previous application instance to fully shut down
    await module.hot.data.closePromise;
  }

  const app = await NestFactory.create(AppModule, {
    forceCloseConnections: !!module.hot,
  });
  await app.listen(process.env.PORT ?? 3000);

  if (module.hot) {
    module.hot.accept();
    module.hot.dispose((data: any) => {
      data.closePromise = app.close();
    });
  }
}
bootstrap();
```

> info **Gợi ý** `app.close()` là bất đồng bộ, nhưng webpack không await callback `dispose()`. Cất promise được trả về vào `module.hot.data` cho phép instance ứng dụng tiếp theo await nó trước khi bind lại vào port, điều này (cùng với `forceCloseConnections`) ngăn lỗi `EADDRINUSE` khi reload.

Để đơn giản hóa quá trình chạy, hãy thêm một script vào file `package.json`:

```json
"start:dev": "webpack --config webpack.config.js --watch"
```

Sau đó chạy lệnh sau:

```bash
$ npm run start:dev
```

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có trong [sample webpack](https://github.com/nestjs/nest/tree/master/sample/08-webpack) trên GitHub.
