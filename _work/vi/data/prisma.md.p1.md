### Prisma

[Prisma](https://www.prisma.io) là một ORM [mã nguồn mở](https://github.com/prisma/prisma) cho Node.js và TypeScript. Bạn có thể dùng nó **thay cho** việc viết SQL thuần hoặc các công cụ truy cập database khác, như SQL query builder (ví dụ [knex.js](https://knexjs.org/)) hay các ORM khác (ví dụ [TypeORM](https://typeorm.io/) và [Sequelize](https://sequelize.org/)). Prisma hỗ trợ PostgreSQL, MySQL, SQL Server, SQLite, CockroachDB và MongoDB (xem [các database được hỗ trợ](https://www.prisma.io/docs/orm/reference/supported-databases)). Chương này dùng Prisma ORM 7, phiên bản chạy với các database SQL; các project MongoDB tạm thời vẫn ở Prisma ORM 6.

Dù bạn có thể dùng Prisma với JavaScript thuần, nó đặt TypeScript làm trọng tâm và cung cấp mức độ type safety vượt xa những gì các ORM khác trong hệ sinh thái TypeScript đảm bảo. Xem [so sánh về đảm bảo type safety giữa Prisma và TypeORM](https://www.prisma.io/docs/orm/more/comparisons/prisma-and-typeorm#type-safety) để biết chi tiết.

Prisma không có package riêng cho Nest. Thay vào đó, bạn sinh ra một client type-safe (Prisma Client) từ Prisma schema, bọc nó trong một provider, và inject provider đó ở bất cứ đâu cần truy cập database. Chương này thiết lập tích hợp đó với một database [SQLite](https://sqlite.org/), loại database không cần server, và ghi chú những điểm khác biệt với PostgreSQL, MySQL và SQL Server trong quá trình đi.

> info **Note** Để có cái nhìn tổng quan về cách Prisma hoạt động, hãy làm theo [Quickstart](https://www.prisma.io/docs/getting-started/prisma-orm/quickstart/prisma-postgres) hoặc đọc phần [Introduction](https://www.prisma.io/docs/orm/overview/introduction/what-is-prisma) trong [tài liệu Prisma](https://www.prisma.io/docs). Để thêm Prisma vào một project đã có database, hãy làm theo hướng dẫn [thêm Prisma vào project hiện có](https://www.prisma.io/docs/getting-started/setup-prisma/add-to-existing-project-typescript-postgres). Nếu bạn đang chuyển từ TypeORM, hãy đọc [Migrating from TypeORM to Prisma](https://www.prisma.io/docs/guides/migrate-from-typeorm).

#### Cài đặt

Cài [Prisma CLI](https://www.prisma.io/docs/orm/tools/prisma-cli) và `dotenv` làm development dependency, rồi cài Prisma Client và driver adapter cho database của bạn. Với SQLite, adapter `@prisma/adapter-better-sqlite3` cũng cài luôn driver `better-sqlite3`:

[[CODE:1]]

> warning **Warning** Hãy cài tường minh Prisma ORM 7, như ở trên. Tại thời điểm viết bài, tag `latest` của package `prisma` trên npm trỏ tới một bản pre-release của Prisma 8, đây là một CLI khác không có các lệnh `prisma migrate` và `prisma generate` dùng trong chương này. Hãy giữ `prisma` và `@prisma/client` ở cùng major version.

<details><summary>Mở rộng nếu bạn dùng PostgreSQL, MySQL, SQL Server hoặc Azure SQL</summary>

Cài adapter cho database của bạn thay vì `@prisma/adapter-better-sqlite3`. Mỗi package adapter đều kèm driver database của nó.

- Với PostgreSQL:

[[CODE:2]]

- Với MySQL (và MariaDB):

[[CODE:3]]

- Với SQL Server và Azure SQL:

[[CODE:4]]

</details>

Tiếp theo, tạo thiết lập Prisma ban đầu bằng lệnh `init`. Hãy thêm `npx` trước các lệnh Prisma CLI để chúng chạy phiên bản đã cài trong project của bạn:

[[CODE:5]]

Lệnh này tạo các file sau:

- `prisma/schema.prisma`: Chứa schema database của bạn, bao gồm data source provider và Prisma Client generator
- `prisma7.config.ts`: File cấu hình Prisma, được tạo ở thư mục gốc của project. Nó đặt vị trí của schema và migration, và đọc URL kết nối database từ biến môi trường `DATABASE_URL`. Các bản Prisma ORM trước 7.10 đặt tên file này là `prisma.config.ts`, Prisma vẫn nhận diện được tên này.
- `.env`: Một file [dotenv](https://github.com/motdotla/dotenv) lưu URL kết nối database trong biến môi trường `DATABASE_URL`

Nó cũng thêm `.env` và thư mục client được sinh ra vào file `.gitignore`.

#### Đặt đường dẫn output cho generator

Prisma Client được sinh vào thư mục chỉ định bởi trường `output` của block `generator`, tính tương đối với file schema. Tùy chọn `--output` ở trên đặt client bên trong `src`, để nó được compile cùng với phần còn lại của ứng dụng. Không có tùy chọn này, `prisma init` đặt đường dẫn thành `../generated/prisma`, nằm ngoài `src`. Bạn cũng có thể đặt đường dẫn trực tiếp trong Prisma schema:

[[CODE:6]]

Vì client được sinh ra bị loại khỏi version control, hãy chạy `npx prisma generate` trước khi build ứng dụng ở một bản checkout mới hoặc trong CI.

#### Cấu hình định dạng module

Prisma suy ra định dạng module của client được sinh ra từ file `tsconfig.json`. Một project NestJS dùng ES module (mặc định cho project mới) sẽ nhận được client dạng ES module, nên không cần cấu hình thêm.

Nếu project của bạn dùng CommonJS, hãy đặt `moduleFormat` trong generator thành `cjs`:

[[CODE:7]]

> info **Note** Client ESM được sinh ra dựa vào `import.meta`, thứ không có trong CommonJS. Các bản trước Prisma ORM 7.10 sinh ra ES module mỗi khi `tsconfig.json` đặt `module` là `nodenext`, kể cả trong project CommonJS, nên hãy đặt `moduleFormat` một cách tường minh thay vì dựa vào việc suy luận.

#### Đặt kết nối database

Block `datasource` trong file `schema.prisma` định nghĩa database bạn dùng. Với tùy chọn `--datasource-provider sqlite`, `prisma init` đặt trường `provider` của nó thành `sqlite` (mặc định là `postgresql`):

[[CODE:8]]

Bản thân URL kết nối không nằm trong schema: file cấu hình Prisma đọc nó từ biến môi trường `DATABASE_URL`, biến mà `prisma init` đặt trong `.env`:

[[CODE:9]]

Một database SQLite là một file thông thường, nên thay vì _host_ và _port_, URL kết nối trỏ tới một file local, ở đây là `dev.db` trong thư mục gốc của project. Prisma tạo file này khi bạn chạy migration đầu tiên.

Prisma CLI load `.env` thông qua câu import `dotenv/config` ở đầu file cấu hình Prisma. Tuy nhiên, ứng dụng NestJS của bạn không tự động load `.env`. Hãy cài package `@nestjs/config` và đăng ký [`ConfigModule`](/application/configuration) ở cấp global trong `AppModule`, để `PrismaService` có thể đọc `DATABASE_URL` qua `ConfigService`:

[[CODE:10]]

[[CODE:11]]

<details><summary>Mở rộng nếu bạn dùng PostgreSQL, MySQL, SQL Server hoặc Azure SQL</summary>

Với PostgreSQL, MySQL và SQL Server, URL kết nối trỏ tới _database server_. Hãy truyền provider tương ứng cho `prisma init` (ví dụ `--datasource-provider postgresql`), hoặc đổi trường `provider` của block `datasource`, và đặt `DATABASE_URL` trong `.env`. Xem [tài liệu tham khảo URL kết nối](https://www.prisma.io/docs/orm/reference/connection-urls) để biết định dạng yêu cầu.

**PostgreSQL**

[[CODE:12]]

[[CODE:13]]

Thay các placeholder viết hoa bằng thông tin đăng nhập database của bạn. Nếu không chắc cần điền gì cho placeholder `SCHEMA`, nhiều khả năng đó là giá trị mặc định `public`. Nếu bạn chưa có PostgreSQL server, hãy chạy `npx prisma dev` để khởi động một database Prisma Postgres local trong terminal.

**MySQL**

[[CODE:14]]

[[CODE:15]]

Thay các placeholder viết hoa bằng thông tin đăng nhập database của bạn.

**Microsoft SQL Server / Azure SQL Server**

[[CODE:16]]

[[CODE:17]]

Thay các placeholder viết hoa bằng thông tin đăng nhập database của bạn. Nếu không chắc cần điền gì cho tùy chọn `encrypt`, nhiều khả năng đó là giá trị mặc định `true`.

</details>

#### Model và migration

[Prisma Migrate](https://www.prisma.io/docs/orm/prisma-migrate/getting-started) sinh các file migration SQL từ data model khai báo trong Prisma schema. Các file migration này hoàn toàn có thể tùy chỉnh, nên bạn có thể cấu hình thêm các tính năng của database bên dưới hoặc thêm các lệnh khác (ví dụ để seed dữ liệu).

Chương này dùng hai model. Hãy thêm chúng vào file `schema.prisma`:

[[CODE:18]]

Sau đó sinh migration đầu tiên và chạy nó trên database:

[[CODE:19]]

Lệnh `prisma migrate dev` sinh các file SQL và chạy chúng trực tiếp trên database. Vì database chưa tồn tại, nó cũng tạo luôn file `dev.db`. Các file migration được tạo trong thư mục `prisma`:

[[CODE:20]]

<details><summary>Mở rộng để xem các câu lệnh SQL được sinh ra</summary>

Các bảng sau đã được tạo trong database SQLite của bạn:

[[CODE:21]]

</details>

#### Sinh Prisma Client

Prisma Client là một database client type-safe được _sinh ra_ từ Prisma schema. Cách tiếp cận này cho phép Prisma Client cung cấp các thao tác [CRUD](https://www.prisma.io/docs/orm/prisma-client/queries/crud) được _may đo_ riêng cho các model của bạn. Sinh client cùng các type của nó bằng lệnh `generate`:

[[CODE:22]]

`prisma migrate dev` không tự chạy lệnh này giúp bạn. Mỗi khi thay đổi schema, hãy chạy lại `prisma generate` để giữ client và các type của nó đồng bộ.

File `client.ts` được sinh ra là entry point của client. Nó export class `PrismaClient`, một type cho mỗi model (ví dụ `User` và `Post`), và namespace `Prisma`, chứa các type đầu vào cho query (ví dụ `Prisma.UserCreateInput`). Giống như mọi câu import tương đối khác trong project ESM, hãy import nó với đuôi `.js` (`./generated/prisma/client.js`).

#### PrismaService

Trong một ứng dụng NestJS, bạn cung cấp Prisma Client thông qua một provider. Hãy tạo một class `PrismaService` kế thừa `PrismaClient`, để service có đầy đủ API của Prisma Client, và truyền driver adapter cho database của bạn vào constructor của `PrismaClient`. Prisma ORM 7 yêu cầu có driver adapter (hoặc một URL Prisma Accelerate) để tạo client.

Tạo file `prisma.service.ts` trong thư mục `src/prisma`:

[[CODE:23]]

Constructor đọc `DATABASE_URL` qua `ConfigService` trước khi gọi `super()`. Method `getOrThrow()` throw lỗi nếu biến chưa được đặt, nên việc thiếu URL kết nối sẽ làm ứng dụng dừng ngay lúc khởi động. Các hook `onModuleInit()` và `onModuleDestroy()` quản lý kết nối, như mô tả trong [Vòng đời kết nối](#connection-lifecycle).

> info **Hint** Nếu bạn không dùng `@nestjs/config`, hãy khởi động Node.js với flag `--env-file=.env` và đọc `process.env.DATABASE_URL` trong constructor.

<details><summary>Mở rộng nếu bạn dùng PostgreSQL, MySQL, SQL Server hoặc Azure SQL</summary>

Thay `PrismaBetterSqlite3` bằng class adapter cho database của bạn (`PrismaPg`, `PrismaMariaDb` hoặc `PrismaMssql`), và truyền cho nó các thiết lập kết nối mà driver cần. Mỗi adapter này cũng nhận connection string. Ví dụ, với PostgreSQL:

[[CODE:24]]

</details>

#### Vòng đời kết nối

Prisma Client kết nối một cách lười biếng (lazy), khi nó gửi query đầu tiên. Gọi `$connect()` trong hook `onModuleInit()` sẽ kết nối ngay trong lúc bootstrap ứng dụng, nên một kết nối cấu hình sai sẽ lỗi lúc khởi động thay vì ở request đầu tiên.

Gọi `$disconnect()` trong hook `onModuleDestroy()` sẽ đóng kết nối khi ứng dụng tắt. Nó cũng giải phóng driver adapter, việc này đóng kết nối driver bên dưới (ví dụ nó kết thúc connection pool mà `PrismaPg` tạo ra). Nest gọi `onModuleDestroy()` khi bạn gọi `app.close()`. Để nó cũng được gọi khi process nhận tín hiệu kết thúc, như `SIGTERM`, hãy bật shutdown hook trong file `main.ts`:

[[CODE:25]]

Xem [Tắt ứng dụng](/fundamentals/lifecycle-events#application-shutdown) để tìm hiểu thêm về shutdown hook.

> info **Hint** Prisma ORM 7 không hỗ trợ event `beforeExit` (`$on('beforeExit', ...)`) mà các bản tích hợp Prisma cũ từng dùng để đóng ứng dụng. Hãy dùng các lifecycle hook của Nest như ở trên.

#### PrismaModule

Đăng ký `PrismaService` trong một module riêng và export nó. Tạo file `prisma.module.ts` cạnh service:

[[CODE:26]]

Import `PrismaModule` vào mọi module cần truy cập database. Provider mặc định là singleton, nên mọi module import nó đều dùng chung một instance `PrismaService` và kết nối của nó.

> info **Hint** Nếu hầu hết các module đều cần truy cập database, bạn có thể decorate `PrismaModule` bằng `@Global()` và chỉ import nó một lần, trong root module. Xem [Global module](/modules#global-modules) để biết ưu nhược điểm.

#### Query từ service

Khi đã có `PrismaModule`, hãy inject `PrismaService` vào các provider và query database qua các thuộc tính model của nó, như `this.prisma.user`. `UsersService` sau bọc các query CRUD cho model `User`:

[[CODE:27]]

Service dùng các type được sinh ra cho tham số và giá trị trả về, nên bạn không cần viết interface riêng cho các model. Trong một ứng dụng thực tế, service cũng là nơi đặt logic nghiệp vụ. Ví dụ, một `UsersService` có thể có method `updatePassword()` chịu trách nhiệm cập nhật mật khẩu của người dùng.

Sau đó một controller cung cấp service ra ngoài thông qua các route handler:

[[CODE:28]]

> info **Hint** Các type được sinh ra chỉ tồn tại lúc compile, nên `ValidationPipe` không thể dùng chúng để validate payload của request. Để validate request body, hãy khai báo một class DTO, như mô tả trong [Validation](/application/validation).

Cuối cùng, đăng ký controller và service trong một `UsersModule` có import `PrismaModule`, và import `UsersModule` vào `AppModule`:

[[CODE:29]]

#### Transaction

Prisma Client cung cấp vài cách để chạy query trong một transaction (xem [Transactions and batch queries](https://www.prisma.io/docs/orm/prisma-client/queries/transactions)):

- **Nested write**, tạo hoặc cập nhật một bản ghi cùng với các bản ghi liên quan trong một query duy nhất, tự động chạy trong một transaction.
- **Thao tác tuần tự**: truyền một mảng query vào `$transaction()`. Prisma chạy chúng theo thứ tự, trong một transaction duy nhất, và resolve ra một mảng chứa kết quả của chúng.
- **Interactive transaction**: truyền một hàm async vào `$transaction()`. Prisma commit transaction khi hàm resolve và rollback khi hàm throw.

Các method sau minh họa hai dạng cuối trong `UsersService`:

[[CODE:30]]

Bên trong một interactive transaction, hãy gửi mọi query qua transaction client (`tx`) mà Prisma truyền vào hàm. Các query gửi qua `this.prisma` sẽ chạy bên ngoài transaction. Cả hai dạng của `$transaction()` đều nhận một options object làm tham số thứ hai, với các thuộc tính `maxWait`, `timeout` và `isolationLevel`.

Truyền `tx` qua mọi method tham gia vào transaction sẽ khiến các service bị ràng buộc với nhau. Để khai báo ranh giới transaction bằng decorator, hãy dùng plugin transactional của package [`nestjs-cls`](/recipes/async-local-storage#nestjs-cls) với [Prisma adapter](https://papooch.github.io/nestjs-cls/plugins/available-plugins/transactional/prisma-adapter) của nó (`@nestjs-cls/transactional-adapter-prisma`). Nó giữ transaction client đang hoạt động trong async local storage và cung cấp decorator `@Transactional()` cùng một `TransactionHost` có thể inject.

#### Test

Khi unit test một provider phụ thuộc vào `PrismaService`, thông thường bạn muốn tránh kết nối database. Vì `PrismaService` là một class provider thông thường, bạn có thể thay nó bằng một mock, dùng chính class đó làm injection token cùng bất kỳ kỹ thuật [custom provider](/fundamentals/custom-providers) chuẩn nào, như `useValue`:

[[CODE:31]]

Mock thay thế hoàn toàn `PrismaService`, nên hook `onModuleInit()` của nó không chạy và bài test không bao giờ mở kết nối database. Khi test một module có import `PrismaModule`, hãy thay provider bằng `overrideProvider(PrismaService)`. Xem [Testing](/fundamentals/testing) để biết thêm các tiện ích test.

#### Ví dụ

Các project mẫu chạy được ngay cho [REST](https://github.com/prisma/prisma-examples/tree/b53fad046a6d55f0090ddce9fd17ec3f9b95cab3/orm/nest) và [GraphQL](https://github.com/prisma/prisma-examples/tree/b53fad046a6d55f0090ddce9fd17ec3f9b95cab3/orm/nest-graphql) có sẵn trong repository [`prisma-examples`](https://github.com/prisma/prisma-examples/). Để có thêm tài nguyên, xem [NestJS & Prisma](https://www.prisma.io/nestjs) trên website của Prisma.
