### Cấu hình

Ứng dụng thường chạy trên nhiều **môi trường** khác nhau, và mỗi môi trường cần một bộ cấu hình riêng. Ví dụ, môi trường local thường dùng thông tin đăng nhập database chỉ hợp lệ cho instance database local, trong khi môi trường production dùng một bộ thông tin đăng nhập khác. Vì các biến cấu hình thay đổi theo môi trường, cách làm tốt nhất là [lưu biến cấu hình](https://12factor.net/config) trong môi trường.

Biến môi trường định nghĩa từ bên ngoài có thể truy cập bên trong Node.js thông qua biến toàn cục `process.env`. Bạn có thể xử lý nhiều môi trường bằng cách đặt biến môi trường riêng cho từng môi trường. Cách này nhanh chóng trở nên khó quản lý, nhất là trong môi trường development và test, nơi các giá trị này cần dễ mock hoặc thay đổi.

Trong ứng dụng Node.js, người ta thường biểu diễn mỗi môi trường bằng một file `.env` chứa các cặp key-value. Khi đó, chạy app trên một môi trường khác chỉ đơn giản là đổi sang đúng file `.env`.

Một cách hay để áp dụng kỹ thuật này trong Nest là tạo một `ConfigModule` cung cấp `ConfigService`, service này sẽ load file `.env` phù hợp. Bạn có thể tự viết module như vậy, nhưng để tiện, Nest cung cấp sẵn package `@nestjs/config`. Chương này trình bày về package đó.

#### Cài đặt

Để bắt đầu, hãy cài dependency cần thiết:

[[CODE:1]]

> info **Hint** Bên trong, package `@nestjs/config` dùng [dotenv](https://github.com/motdotla/dotenv).

> warning **Note** `@nestjs/config` yêu cầu TypeScript 4.1 trở lên.

#### Bắt đầu

Sau khi cài đặt xong, hãy import `ConfigModule`. Thông thường, bạn import nó vào root module `AppModule` và điều khiển hành vi của nó bằng method static `.forRoot()`. Trong bước này, các cặp key/value của biến môi trường được parse và resolve. Ở phần sau, bạn sẽ thấy vài cách để truy cập class `ConfigService` của `ConfigModule` trong các feature module khác.

[[CODE:2]]

Đoạn code này load và parse file `.env` từ vị trí mặc định (thư mục nơi process được khởi động, thường là thư mục gốc của project), merge các cặp key/value từ file `.env` với các biến môi trường đã gán vào `process.env`, và lưu kết quả vào một cấu trúc private mà bạn truy cập được thông qua `ConfigService`. Method `forRoot()` đăng ký provider `ConfigService`, provider này có method `get()` để đọc các biến cấu hình đã được parse và merge. Vì `@nestjs/config` dựa trên [dotenv](https://github.com/motdotla/dotenv), nó dùng quy tắc của package đó để giải quyết xung đột tên biến môi trường. Khi một key tồn tại cả trong môi trường runtime (ví dụ đặt bằng lệnh export trong shell như `export DATABASE_USER=test`) lẫn trong file `.env`, biến môi trường runtime sẽ được ưu tiên. Để giá trị trong file `.env` được ưu tiên, hãy đặt tùy chọn `override` thành `true`.

Một file `.env` mẫu trông như sau:

[[CODE:3]]

Nếu bạn cần một số biến môi trường có sẵn trước khi `ConfigModule` được load và ứng dụng Nest được bootstrap (ví dụ để truyền cấu hình microservice vào method `NestFactory#createMicroservice()`), hãy dùng tùy chọn `--env-file` của Nest CLI. Tùy chọn này chỉ định đường dẫn tới một file `.env` cần load trước khi ứng dụng khởi động. CLI chuyển file này cho flag `--env-file` của Node.js; xem [tài liệu Node.js](https://nodejs.org/dist/v20.18.1/docs/api/cli.html#--env-fileconfig) để biết chi tiết.

[[CODE:4]]

#### Tùy chỉnh đường dẫn file env

Mặc định, package tìm file `.env` trong thư mục làm việc hiện tại (thường là thư mục gốc của ứng dụng). Để chỉ định đường dẫn khác cho file `.env`, đặt thuộc tính `envFilePath` trong options object (tùy chọn) mà bạn truyền vào `forRoot()`, như sau:

[[CODE:5]]

Bạn cũng có thể chỉ định nhiều đường dẫn cho các file `.env`:

[[CODE:6]]

Nếu một biến có mặt trong nhiều file, file đầu tiên sẽ được ưu tiên.

#### Tắt việc load biến env

Nếu bạn không muốn load file `.env` mà chỉ muốn truy cập biến môi trường từ môi trường runtime (ví dụ đặt bằng lệnh export trong shell như `export DATABASE_USER=test`), hãy đặt thuộc tính `ignoreEnvFile` của options object thành `true`:

[[CODE:7]]

#### Hỗ trợ `.env` gốc của Node.js

Node.js có thể tự load file `.env`, bằng flag `--env-file` (tùy chọn `nest start --env-file` ở trên dựa vào flag này) hoặc bằng method `process.loadEnvFile()`. Để Node.js load file và vẫn dùng `ConfigModule` cho mọi thứ khác, hãy đặt `ignoreEnvFile` thành `true` như trên, để module chỉ đọc `process.env`:

[[CODE:8]]

Vì các biến đã nằm sẵn trong `process.env` khi `forRoot()` chạy, validation, `ConfigService#get()` và các factory `registerAs()` vẫn hoạt động như bình thường. Tuy nhiên, `ConfigModule` xem các biến này là biến định nghĩa trước (predefined), nên chúng chỉ được validate khi `validatePredefined` giữ giá trị mặc định là `true`. Một biến đã được đặt sẵn trong môi trường runtime luôn được ưu tiên hơn file (không có tùy chọn nào tương đương `override`), và với nhiều flag `--env-file`, file cuối cùng sẽ được ưu tiên, ngược lại với `envFilePath`.

`process.loadEnvFile()` phải chạy trước khi `AppModule` được import, vì `forRoot()` đọc `process.env` ngay trong lúc file `app.module` được evaluate. Gọi nó trong thân `main.ts` là quá muộn, nên hãy đặt nó trong một file riêng và import file đó trước tiên:

[[CODE:9]]

Cách khác là vẫn để `ConfigModule` lo việc load file (`envFilePath`, `override`, v.v.) và chỉ thay parser thông qua tùy chọn `parser`. Parser nhận nội dung của từng file dưới dạng `Buffer` và trả về các cặp key/value (mặc định là `dotenv.parse`). Vì `util.parseEnv()` chỉ nhận chuỗi, hãy chuyển buffer sang chuỗi trước:

[[CODE:10]]

> warning **Warning** Parser của Node.js đứng sau các API này không hoàn toàn tương thích với dotenv. Ví dụ, ký tự UTF-8 BOM bị dính vào tên key đầu tiên, một dấu nháy bên trong giá trị có nháy sẽ kết thúc giá trị (`'it's here'` thành `it`), và một giá trị chỉ gồm khoảng trắng sẽ nuốt luôn dòng tiếp theo, khiến biến định nghĩa ở dòng đó bị mất. Hành vi của nó cũng đã thay đổi qua các bản minor của Node.js 20.x và 22.x. Node.js không expand biến, và `parseEnv()` trả về các key đã sắp xếp theo tên, nên đừng kết hợp tùy chọn `parser` với [`expandVariables`](/application/configuration#expandable-variables): một tham chiếu tới biến có tên đứng sau trong thứ tự sắp xếp sẽ được resolve như thể biến đó chưa được đặt.

#### Dùng module ở cấp global

Để dùng `ConfigModule` trong các module khác, bạn cần import nó (như với mọi module Nest). Cách khác là khai báo nó là [global module](/modules#global-modules) bằng cách đặt thuộc tính `isGlobal` của options object thành `true`, như bên dưới. Khi đó, một khi `ConfigModule` đã được load trong root module (ví dụ `AppModule`), bạn không cần import nó trong các module khác nữa.

[[CODE:11]]

#### File cấu hình tùy chỉnh

Với các project phức tạp hơn, bạn có thể dùng các file cấu hình tùy chỉnh trả về configuration object lồng nhau. Cách này cho phép bạn gom các thiết lập cấu hình liên quan theo chức năng (ví dụ các thiết lập liên quan đến database) và lưu chúng trong các file riêng, để quản lý chúng độc lập với nhau.

Một file cấu hình tùy chỉnh export một hàm factory trả về configuration object. Configuration object có thể là bất kỳ object JavaScript thuần nào, lồng nhau tùy ý. Bên trong factory, object `process.env` chứa các cặp key/value biến môi trường đã được resolve đầy đủ (với file `.env` và các biến định nghĩa từ bên ngoài đã được resolve và merge như mô tả trong [Bắt đầu](/application/configuration#getting-started)). Vì bạn kiểm soát configuration object trả về, bạn có thể thêm bất kỳ logic nào cần thiết để ép kiểu giá trị, đặt giá trị mặc định, v.v. Ví dụ:

[[CODE:12]]

Load file này bằng thuộc tính `load` của options object mà bạn truyền vào method `ConfigModule.forRoot()`:

[[CODE:13]]

> info **Hint** Giá trị gán cho thuộc tính `load` là một mảng, nên bạn có thể load nhiều file cấu hình (ví dụ `load: [databaseConfig, authConfig]`).

File cấu hình tùy chỉnh cũng cho phép bạn load cấu hình từ các định dạng khác, như YAML. Đây là ví dụ một cấu hình ở định dạng YAML:

[[CODE:14]]

Để đọc và parse file YAML, bạn có thể dùng package `js-yaml`:

[[CODE:15]]

Sau khi cài package, dùng hàm `load()` của nó để đọc file YAML đã tạo ở trên:

[[CODE:16]]

> warning **Note** Nest CLI không tự động copy các "asset" (file không phải TS) vào thư mục `dist` trong quá trình build. Để đảm bảo các file YAML được copy, hãy khai báo chúng trong object `compilerOptions#assets` của file `nest-cli.json`. Ví dụ, nếu thư mục `config` nằm cùng cấp với thư mục `src`, hãy thêm `compilerOptions#assets` với giá trị `"assets": [{{ '{' }}"include": "../config/*.yaml", "outDir": "./dist/config"{{ '}' }}]`. Xem [Asset](/cli/monorepo#assets) để biết chi tiết.

File cấu hình không được validate tự động, kể cả khi bạn dùng tùy chọn `validationSchema` của `ConfigModule` (tùy chọn này chỉ áp dụng cho biến môi trường). Nếu bạn cần validation hoặc muốn áp dụng các phép chuyển đổi, hãy xử lý chúng trong hàm factory, nơi bạn toàn quyền kiểm soát configuration object.

Ví dụ, để đảm bảo port nằm trong một khoảng nhất định, hãy thêm một bước validation vào hàm factory:

[[CODE:17]]

Giờ thì nếu port nằm ngoài khoảng chỉ định, ứng dụng sẽ throw lỗi trong lúc khởi động.

<app-banner-observe></app-banner-observe>

#### Dùng `ConfigService`

Để truy cập các giá trị cấu hình, trước tiên hãy inject `ConfigService`. Giống như với mọi provider, bạn cần import module chứa nó, tức là `ConfigModule`, vào module sử dụng nó (trừ khi bạn đã đặt thuộc tính `isGlobal` của options object truyền vào `ConfigModule.forRoot()` thành `true`). Import nó vào một feature module như bên dưới:

[[CODE:18]]

Sau đó inject nó qua constructor:

[[CODE:19]]

> info **Hint** Import `ConfigService` từ package `@nestjs/config`.

Rồi dùng nó trong class của bạn:

[[CODE:20]]

Như ở trên, dùng method `configService.get()` để lấy một biến môi trường đơn giản bằng cách truyền tên biến. Bạn có thể truyền một type argument làm gợi ý type cho TypeScript (ví dụ `get<string>(...)`). Method `get()` cũng có thể duyệt vào một configuration object tùy chỉnh lồng nhau (tạo bằng [file cấu hình tùy chỉnh](/application/configuration#custom-configuration-files)), như trong ví dụ thứ hai.

Bạn cũng có thể lấy toàn bộ configuration object tùy chỉnh lồng nhau, dùng một interface làm gợi ý type:

[[CODE:21]]

Method `get()` cũng nhận một tham số thứ hai (tùy chọn) để định nghĩa giá trị mặc định, được trả về khi key không tồn tại:

[[CODE:22]]

Nếu một giá trị là bắt buộc, hãy dùng method `getOrThrow()`. Nó nhận cùng tham số như `get()`, nhưng throw lỗi nếu giá trị resolve ra là `undefined`, và type trả về của nó loại bỏ `undefined`:

[[CODE:23]]

`ConfigService` có hai generic (type argument) tùy chọn. Generic thứ nhất giúp tránh truy cập một thuộc tính cấu hình không tồn tại:

[[CODE:24]]

Với thuộc tính `infer` được đặt thành `true`, method `ConfigService#get` sẽ suy ra type của thuộc tính từ interface. Ví dụ, `port` có type `number`, vì `PORT` có type `number` trong interface `EnvironmentVariables` (khi bật tùy chọn compiler `strictNullChecks`, type sẽ là `number | undefined`).

Với tính năng `infer`, bạn cũng có thể suy ra type của thuộc tính trong configuration object tùy chỉnh lồng nhau, kể cả khi dùng dot notation:

[[CODE:25]]

Generic thứ hai dựa vào generic thứ nhất. Nó đóng vai trò type assertion, loại bỏ type `undefined` mà các method của `ConfigService` có thể trả về khi bật `strictNullChecks`. Ví dụ:

[[CODE:26]]

> info **Hint** Để method `ConfigService#get` bỏ qua các biến trong `process.env` và chỉ lấy giá trị từ các file cấu hình tùy chỉnh (và từ các biến môi trường đã được validate, nếu bạn dùng validation), hãy đặt tùy chọn `skipProcessEnv` thành `true` trong options object truyền vào `ConfigModule.forRoot()`.

#### Namespace cấu hình

`ConfigModule` cho phép bạn định nghĩa và load nhiều file cấu hình tùy chỉnh, như đã thấy trong phần [File cấu hình tùy chỉnh](/application/configuration#custom-configuration-files) ở trên. Bạn có thể quản lý các cây cấu hình phức tạp bằng configuration object lồng nhau, như trong phần đó. Cách khác là trả về một configuration object có "namespace" bằng hàm `registerAs()`, như sau:

[[CODE:27]]

Giống như với file cấu hình tùy chỉnh, bên trong hàm factory `registerAs()`, object `process.env` chứa các cặp key/value biến môi trường đã được resolve đầy đủ (với file `.env` và các biến định nghĩa từ bên ngoài đã được resolve và merge như mô tả trong [Bắt đầu](/application/configuration#getting-started)).

> info **Hint** Hàm `registerAs()` được export từ package `@nestjs/config`.

Load một cấu hình có namespace bằng thuộc tính `load` trong options object của method `forRoot()`, giống như cách bạn load một file cấu hình tùy chỉnh:

[[CODE:28]]

Để lấy giá trị `host` từ namespace `database`, hãy dùng dot notation. Dùng `'database'` làm prefix cho tên thuộc tính. Nó tương ứng với tên của namespace (truyền làm tham số thứ nhất cho hàm `registerAs()`):

[[CODE:29]]

Cách khác là inject trực tiếp namespace `database`, cách này cho bạn type chặt chẽ:

[[CODE:30]]

> info **Hint** Type `ConfigType` được export từ package `@nestjs/config`.

#### Cấu hình có namespace trong module

Để dùng một cấu hình có namespace làm configuration object cho một module khác trong ứng dụng, hãy dùng method `.asProvider()` của configuration object. Method này chuyển cấu hình có namespace thành một định nghĩa provider mà bạn có thể truyền vào method `forRootAsync()` (hoặc tương đương) của module cần cấu hình:

[[CODE:31]]

Để hiểu method `.asProvider()` hoạt động thế nào, hãy xem giá trị trả về của nó:

[[CODE:32]]

Cấu trúc này cho phép bạn cắm các cấu hình có namespace vào module khác mà không phải viết code boilerplate lặp đi lặp lại, giúp ứng dụng của bạn ngăn nắp và mô-đun.

#### Cache biến môi trường

Truy cập `process.env` có thể chậm. Để cải thiện hiệu năng của method `ConfigService#get` với các biến lưu trong `process.env`, hãy đặt thuộc tính `cache` trong options object truyền vào `ConfigModule.forRoot()`:

[[CODE:33]]

#### Đăng ký từng phần

Đến giờ, ta đã xử lý các file cấu hình trong root module (ví dụ `AppModule`) bằng method `forRoot()`. Trong một cấu trúc project phức tạp hơn, có thể bạn có các file cấu hình riêng cho từng tính năng nằm ở nhiều thư mục khác nhau. Thay vì load tất cả các file này trong root module, bạn có thể dùng một tính năng của package `@nestjs/config` gọi là **đăng ký từng phần** (partial registration), chỉ tham chiếu tới các file cấu hình gắn với từng feature module. Dùng method static `forFeature()` bên trong feature module để thực hiện đăng ký từng phần, như sau:

[[CODE:34]]

> warning **Warning** Trong một số trường hợp, có thể bạn cần truy cập các thuộc tính được load qua đăng ký từng phần trong hook `onModuleInit()` thay vì trong constructor. Lý do là method `forFeature()` chạy trong lúc khởi tạo module, và thứ tự khởi tạo module là không xác định. Nếu bạn truy cập trong constructor các giá trị được một module khác load theo cách này, module mà cấu hình phụ thuộc vào có thể chưa được khởi tạo. Method `onModuleInit()` chỉ chạy sau khi mọi module mà nó phụ thuộc vào đã được khởi tạo, nên kỹ thuật này là an toàn.

#### Validate bằng schema

Throw exception ngay lúc ứng dụng khởi động nếu các biến môi trường bắt buộc chưa được cung cấp hoặc không thỏa mãn một số quy tắc validation là cách làm chuẩn. Package `@nestjs/config` hỗ trợ hai cách để làm việc này:

- Một schema tương thích [Standard Schema](https://standardschema.dev/) truyền qua tùy chọn `validationSchema`. Bất kỳ library nào implement đặc tả này đều dùng được, như [Zod](https://zod.dev/), [Valibot](https://valibot.dev/) và [ArkType](https://arktype.io/).
- Một hàm `validate()` tùy chỉnh nhận các biến môi trường làm đầu vào.

Hãy cài library validation bạn chọn. Ví dụ này dùng Zod:

[[CODE:35]]

Giờ hãy định nghĩa một validation schema và truyền nó qua thuộc tính `validationSchema` của options object truyền vào `forRoot()`, như bên dưới:

[[CODE:36]]

Schema này đặt giá trị mặc định cho `NODE_ENV` và `PORT`, được dùng nếu bạn không cung cấp các biến này trong môi trường (file `.env` hoặc môi trường của process). Để bắt buộc một biến, hãy để nó không có giá trị mặc định. Khi đó bước validation sẽ throw exception trong lúc bootstrap nếu biến bị thiếu.

Biến môi trường luôn đến dưới dạng chuỗi, đó là lý do `PORT` dùng `z.coerce.number()`. `ConfigService` trả về các giá trị do schema trả về, nên các phép ép kiểu và chuyển đổi khai báo trong schema sẽ áp dụng cho cấu hình mà ứng dụng của bạn đọc. Các biến mà schema không khai báo vẫn truy cập được thông qua `ConfigService`.

Mặc định, các biến môi trường không xác định (vô số mục không liên quan mà `process.env` luôn chứa, như `PATH` và `HOME`) không gây ra exception validation, và mọi biến không hợp lệ đều được báo cáo chứ không chỉ biến đầu tiên. Mỗi lỗi validation được định dạng theo kiểu `PATH: message`, và các lỗi được nối với nhau bằng dấu xuống dòng.

Bạn có thể chuyển tiếp các tùy chọn riêng của library qua key `validationOptions`. Vì tùy chọn này có type theo đặc tả Standard Schema, các thiết lập riêng của library được đặt dưới `libraryOptions`:

[[CODE:37]]

> info **Hint** Joi vẫn được hỗ trợ, nhưng yêu cầu **Joi v18 trở lên**, phiên bản implement đặc tả Standard Schema. Truyền `Joi.object({{ '{' }} ... &#125;)` vào `validationSchema` như trước, và đặt các thiết lập của Joi như `allowUnknown` và `abortEarly` dưới `validationOptions.libraryOptions`. Với schema Joi, `@nestjs/config` giữ các giá trị mặc định cũ là `allowUnknown: true` và `abortEarly: false`, và merge các tùy chọn bạn truyền vào đè lên chúng. Với project mới, chúng tôi khuyên dùng một library Standard Schema hiện đại như Zod.

> info **Hint** Để tắt validation cho các biến môi trường định nghĩa trước, hãy đặt thuộc tính `validatePredefined` thành `false` trong options object truyền vào `forRoot()`. Biến môi trường định nghĩa trước là các biến của process (biến `process.env`) đã được đặt trước khi module được import. Ví dụ, nếu bạn khởi động ứng dụng bằng `PORT=3000 node main.js`, thì `PORT` là một biến môi trường định nghĩa trước.

#### Hàm validate tùy chỉnh

Cách khác là chỉ định một hàm `validate` **đồng bộ**. Hàm này nhận một object chứa các biến môi trường (từ file `.env` và từ process) và trả về một object chứa các biến môi trường đã được validate, nên bạn có thể chuyển đổi hoặc sửa chúng khi cần. Nếu hàm throw lỗi, ứng dụng sẽ không bootstrap.

Ví dụ này dùng các package `class-transformer` và `class-validator`. Đầu tiên, định nghĩa:

- một class với các ràng buộc validation,
- một hàm validate sử dụng các hàm `plainToInstance` và `validateSync`.

[[CODE:38]]

Khi đã có những thứ này, truyền hàm `validate` làm một tùy chọn cấu hình của `ConfigModule`:

[[CODE:39]]

#### Hàm getter tùy chỉnh

`ConfigService` định nghĩa một method `get()` generic để lấy giá trị cấu hình theo key. Bạn cũng có thể thêm các hàm getter để có phong cách code tự nhiên hơn:

[[CODE:40]]

> info **Hint** Ví dụ này giả định `AUTH_ENABLED` là một chuỗi. Nếu validation schema của bạn chuyển nó thành boolean, `get()` sẽ trả về giá trị đã chuyển đổi, nên hãy trả về trực tiếp `this.configService.get<boolean>('AUTH_ENABLED')` thay vì so sánh nó với `'true'`.

Giờ bạn có thể dùng hàm getter như sau:

[[CODE:41]]

#### Hook báo biến môi trường đã load xong

Nếu cấu hình của một module phụ thuộc vào biến môi trường load từ file `.env`, hãy dùng hook `ConfigModule.envVariablesLoaded` để đảm bảo file đã được load trước khi bạn đọc object `process.env`:

[[CODE:42]]

Cách khai báo này đảm bảo mọi biến cấu hình đã được load khi promise `ConfigModule.envVariablesLoaded` resolve.

#### Cấu hình module có điều kiện

Đôi khi bạn muốn load một module có điều kiện, với điều kiện được chỉ định trong một biến môi trường. Package `@nestjs/config` cung cấp `ConditionalModule` cho mục đích này.

[[CODE:43]]

Module này load `FooModule` trừ khi biến môi trường `USE_FOO` được đặt thành `false` (không phân biệt hoa thường). Nếu biến không được định nghĩa, `FooModule` sẽ được load. Bạn cũng có thể truyền một điều kiện tùy chỉnh: một hàm nhận tham chiếu `process.env` và trả về boolean:

[[CODE:44]]

Khi dùng `ConditionalModule`, hãy đảm bảo `ConfigModule` cũng được load trong ứng dụng, để hook `ConfigModule.envVariablesLoaded` có thể resolve. Nếu hook không resolve trong vòng 5 giây (hoặc trong khoảng timeout, tính bằng mili giây, đặt qua thuộc tính `timeout` của tham số `options` thứ ba của method `registerWhen()`), `ConditionalModule` sẽ throw lỗi và Nest hủy việc khởi động ứng dụng.
