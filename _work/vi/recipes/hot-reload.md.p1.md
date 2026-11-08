### Hot Reload

**Việc biên dịch TypeScript** ảnh hưởng lớn nhất tới thời gian bootstrap ứng dụng. Với [webpack](https://github.com/webpack/webpack) HMR (Hot-Module Replacement), bạn không cần biên dịch lại toàn bộ project mỗi khi có thay đổi. Điều này giảm đáng kể thời gian khởi tạo ứng dụng và giúp việc phát triển lặp đi lặp lại nhanh hơn nhiều.

> warning **Warning** `webpack` không tự động copy asset (ví dụ các file `graphql`) vào thư mục `dist`. Tương tự, `webpack` không tương thích với các glob path tĩnh (ví dụ thuộc tính `entities` trong `TypeOrmModule`).

> warning **Warning** Từ NestJS v12, webpack builder đã bị **deprecated** và Rspack là bundler mặc định cho monorepo. Recipe này nhắm tới các project CommonJS dựa trên webpack, đó là lý do các ví dụ bên dưới dùng `module.hot` và một lời gọi `bootstrap()` thuần thay vì top-level `await` của ESM được dùng ở những chỗ khác trong tài liệu này. Với project mới, hãy ưu tiên `--builder rspack`.

### Với CLI

Nếu bạn dùng [Nest CLI](/cli/overview), quá trình cấu hình khá đơn giản. CLI bọc `webpack`, cho phép bạn dùng `HotModuleReplacementPlugin`.

#### Cài đặt

Trước tiên, hãy cài các package cần thiết:

[[CODE:1]]

> info **Hint** Nếu bạn dùng **Yarn Berry** (không phải Yarn classic), hãy cài package `webpack-pnp-externals` thay cho `webpack-node-externals`.

#### Cấu hình

Khi đã cài đặt xong, hãy tạo một file `webpack-hmr.config.js` ở thư mục gốc của ứng dụng:

[[CODE:2]]

> info **Hint** Với **Yarn Berry** (không phải Yarn classic), thay vì dùng `nodeExternals` trong thuộc tính cấu hình `externals`, hãy dùng `WebpackPnpExternals` từ package `webpack-pnp-externals`: `WebpackPnpExternals({{ '{' }} exclude: ['webpack/hot/poll?100'] {{ '}' }})`.

Hàm này nhận object gốc chứa cấu hình webpack mặc định làm tham số đầu tiên, và một tham chiếu tới package `webpack` bên dưới mà Nest CLI dùng làm tham số thứ hai. Nó trả về một cấu hình webpack đã được sửa đổi với các plugin `HotModuleReplacementPlugin`, `WatchIgnorePlugin` và `RunScriptWebpackPlugin`.

#### Hot-Module Replacement

Để bật **HMR**, hãy mở file entry của ứng dụng (`main.ts`) và thêm các chỉ dẫn liên quan tới webpack sau:

[[CODE:3]]

> info **Hint** `app.close()` là bất đồng bộ, nhưng webpack không await callback `dispose()`. Cất promise được trả về vào `module.hot.data` cho phép instance ứng dụng tiếp theo await nó trước khi bind lại vào port, điều này (cùng với `forceCloseConnections`) ngăn lỗi `EADDRINUSE` khi reload.

Để đơn giản hóa quá trình chạy, hãy thêm một script vào file `package.json`:

[[CODE:4]]

Sau đó chạy lệnh sau:

[[CODE:5]]

### Không dùng CLI

Nếu bạn không dùng [Nest CLI](/cli/overview), việc cấu hình phức tạp hơn một chút và cần nhiều bước thủ công hơn.

#### Cài đặt

Trước tiên, hãy cài các package cần thiết:

[[CODE:6]]

> info **Hint** Nếu bạn dùng **Yarn Berry** (không phải Yarn classic), hãy cài package `webpack-pnp-externals` thay cho `webpack-node-externals`.

#### Cấu hình

Khi đã cài đặt xong, hãy tạo một file `webpack.config.js` ở thư mục gốc của ứng dụng:

[[CODE:7]]

> info **Hint** Với **Yarn Berry** (không phải Yarn classic), thay vì dùng `nodeExternals` trong thuộc tính cấu hình `externals`, hãy dùng `WebpackPnpExternals` từ package `webpack-pnp-externals`: `WebpackPnpExternals({{ '{' }} exclude: ['webpack/hot/poll?100'] {{ '}' }})`.

Cấu hình này cho webpack biết vài điều thiết yếu về ứng dụng của bạn: vị trí của file entry, thư mục chứa các file **đã biên dịch**, và loader dùng để biên dịch các file mã nguồn. Nhìn chung bạn có thể dùng nguyên file này, kể cả khi chưa hiểu hết mọi tùy chọn.

#### Hot-Module Replacement

Để bật **HMR**, hãy mở file entry của ứng dụng (`main.ts`) và thêm các chỉ dẫn liên quan tới webpack sau:

[[CODE:8]]

> info **Hint** `app.close()` là bất đồng bộ, nhưng webpack không await callback `dispose()`. Cất promise được trả về vào `module.hot.data` cho phép instance ứng dụng tiếp theo await nó trước khi bind lại vào port, điều này (cùng với `forceCloseConnections`) ngăn lỗi `EADDRINUSE` khi reload.

Để đơn giản hóa quá trình chạy, hãy thêm một script vào file `package.json`:

[[CODE:9]]

Sau đó chạy lệnh sau:

[[CODE:10]]

#### Ví dụ

Một ví dụ chạy được có trong [sample webpack](https://github.com/nestjs/nest/tree/master/sample/08-webpack) trên GitHub.
