### Drizzle

Thay cho TypeORM, bạn có thể dùng [Drizzle ORM](https://orm.drizzle.team/) với package `@nestjs/drizzle`. Drizzle là một ORM nhẹ, ưu tiên TypeScript. Bạn khai báo bảng bằng các hàm thông thường và viết query bằng một query builder giống SQL (hoặc relational query API cho các thao tác đọc lồng nhau), và Drizzle suy ra type của mọi kết quả từ schema. Không có class entity, decorator hay bước sinh code nào.

Để bắt đầu, hãy cài các dependency cần thiết. Chương này dùng [PostgreSQL](https://www.postgresql.org/) với driver `node-postgres`, nhưng Drizzle hỗ trợ nhiều database khác, bao gồm MySQL, SQLite và Microsoft SQL Server, cũng như các database serverless như Neon, Turso và Cloudflare D1. Các bước trong chương này giống nhau cho mọi database mà Drizzle hỗ trợ: cài driver cho database của bạn, và import `drizzle()` từ [entry point](https://orm.drizzle.team/docs/connect-overview) tương ứng (ví dụ `drizzle-orm/mysql2` hoặc `drizzle-orm/libsql`) thay vì `drizzle-orm/node-postgres`.

[[CODE:1]]

> info **Hint** Chương này dùng Drizzle ORM v1, hiện đang được phát hành dưới tag `rc`. Tài liệu Drizzle được viết cho phiên bản này. `@nestjs/drizzle` cũng hỗ trợ Drizzle v0.35 trở lên. Với v0.x, chỉ có relation và relational query hoạt động khác so với chương này (xem [Upgrading to v1](https://orm.drizzle.team/docs/upgrade-v1)).

#### Schema

Với Drizzle, bạn viết schema database bằng TypeScript. Bạn khai báo mỗi bảng bằng một hàm như `pgTable()` và export nó từ một file schema. Hãy định nghĩa bảng `users`:

[[CODE:2]]

Các helper `$inferSelect` và `$inferInsert` suy ra type của dòng dữ liệu từ định nghĩa bảng, nên không cần một class model riêng phải giữ đồng bộ với schema. Để xem các loại cột có sẵn, xem [Schema declaration](https://orm.drizzle.team/docs/sql-schema-declaration) trong tài liệu Drizzle.

#### Đăng ký database

Sau khi đã cài dependency và định nghĩa schema, import `DrizzleModule` vào root module `AppModule`:

[[CODE:3]]

Tùy chọn `drizzle` nhận hàm `drizzle()` của driver bạn dùng. `DrizzleModule` gọi nó với `connection` và các tùy chọn Drizzle khác một lần cho mỗi instance ứng dụng. Vì vậy, mọi ứng dụng, kể cả mỗi ứng dụng mà e2e test của bạn tạo ra, đều có connection pool riêng, và pool này được đóng khi ứng dụng đó tắt. Vì bạn truyền vào chính hàm đó, mọi driver mà Drizzle hỗ trợ đều hoạt động theo cùng cách, và TypeScript kiểm tra `connection` cùng các tùy chọn khác theo signature `drizzle()` của driver đó.

Method `forRoot()` hỗ trợ các tùy chọn sau:

<table>
  <tr>
    <td><code>drizzle</code></td>
    <td>Hàm <code>drizzle()</code> của driver, ví dụ hàm được export bởi <code>drizzle-orm/node-postgres</code></td>
  </tr>
  <tr>
    <td><code>connection</code></td>
    <td>Một connection string, hoặc các tùy chọn kết nối của driver (ví dụ cấu hình pool của <code>pg</code>)</td>
  </tr>
  <tr>
    <td><code>db</code></td>
    <td>Một instance database do bạn tự tạo, dùng thay cho <code>drizzle</code> và <code>connection</code> (xem bên dưới)</td>
  </tr>
  <tr>
    <td><code>autoCloseConnection</code></td>
    <td>Nếu là <code>true</code>, client của database (<code>db.$client</code>) sẽ được đóng khi ứng dụng tắt (mặc định: <code>true</code>)</td>
  </tr>
</table>

Các tùy chọn khác, như `relations`, `logger` hay `casing`, cũng được truyền vào `drizzle()`.

> info **Hint** Giống như tùy chọn của mọi module khác, tùy chọn của `forRoot()` được evaluate khi file `AppModule` được import, nên `process.env.DATABASE_URL` phải được đặt sẵn tại thời điểm đó (ví dụ bằng cách khởi động Node.js với flag `--env-file=.env`). Để đọc connection string qua `ConfigService`, hãy dùng `forRootAsync()`, được mô tả trong phần "Cấu hình bất đồng bộ" bên dưới.

> info **Hint** Client được đóng khi bạn gọi `app.close()`, hoặc khi process nhận tín hiệu kết thúc nếu đã bật [shutdown hook](/fundamentals/lifecycle-events#application-shutdown). Các client dựa trên pool (ví dụ `node-postgres`, `postgres.js`, `mysql2`) được đóng bằng `end()`, còn các client khác (ví dụ `better-sqlite3`, `libsql`, PGlite) bằng `close()`. Với database tạo bằng hàm [`withReplicas()`](https://orm.drizzle.team/docs/read-replicas) của Drizzle, client của database chính và mọi database replica đều được đóng (với Drizzle v0.44.6 trở lên; các phiên bản trước không để lộ các replica, nên chỉ client của database chính được đóng). Một client đăng ký dưới nhiều tên chỉ được đóng một lần.

Khi module đã được đăng ký, bạn có thể inject database ở bất cứ đâu trong project (không cần import module nào) bằng decorator `@InjectDrizzle()`. Ví dụ:

[[CODE:4]]

Để đăng ký một database do bạn tự tạo, ví dụ database định tuyến thao tác đọc tới replica bằng hàm `withReplicas()` của Drizzle, hãy truyền nó làm `db`. Tạo nó trong một factory `forRootAsync()`, factory này chạy một lần cho mỗi ứng dụng:

[[CODE:5]]

> warning **Warning** Bạn cũng có thể truyền một instance `db` vào `forRoot()`, ví dụ instance được export từ một file `db` mà các script seed của bạn cũng import. Instance như vậy được tạo một lần, khi file của nó được import lần đầu. Mọi ứng dụng tạo từ `AppModule` đều dùng chung nó, và ứng dụng đầu tiên tắt sẽ đóng nó, làm hỏng các e2e test suite tạo ứng dụng mới cho mỗi bài test. Trong trường hợp đó, hãy đặt `autoCloseConnection` thành `false` và tự đóng client.

#### Query

Khác với tích hợp TypeORM, Drizzle không có bước `forFeature()`. Bảng của Drizzle là các object thông thường mà bạn import ở bất cứ đâu cần tạo query, và database được đăng ký ở cấp global, nên mọi provider đều inject được nó. Hãy implement `UsersService`:

[[CODE:6]]

Một query Drizzle chạy khi nó được await (hoặc được trả về từ một hàm `async`), và type kết quả của nó được suy ra từ các cột mà nó select. Tài liệu Drizzle trình bày chi tiết về [select](https://orm.drizzle.team/docs/select), [insert](https://orm.drizzle.team/docs/insert), [update](https://orm.drizzle.team/docs/update) và [delete](https://orm.drizzle.team/docs/delete) dòng dữ liệu.

#### Relation

Relation là liên kết giữa hai hoặc nhiều bảng, dựa trên các trường chung, thường là khóa chính và khóa ngoại. [Relational query](https://orm.drizzle.team/docs/rqb-v2) của Drizzle dùng chúng để lấy dữ liệu lồng nhau, như người dùng cùng với ảnh của họ, mà không cần tự viết join.

Hãy thêm một bảng `photos` có cột `userId` tham chiếu tới bảng `users`:

[[CODE:7]]

Bạn khai báo relation cho toàn bộ schema cùng một lúc, bằng hàm `defineRelations()`. Ví dụ, mỗi người dùng có thể có nhiều ảnh, và mỗi ảnh thuộc về một người dùng:

[[CODE:8]]

Để relational query dùng được các relation, hãy truyền chúng vào `drizzle()` bằng tùy chọn `relations`:

[[CODE:9]]

Type của database giờ phụ thuộc vào các relation, nên hãy khai báo nó một lần và dùng lại ở mọi nơi bạn inject database:

[[CODE:10]]

Khi đã có những thứ trên, API `db.query` có type đầy đủ:

[[CODE:11]]

> info **Hint** Relation chỉ phục vụ relational query. Ràng buộc khóa ngoại đến từ `references()` trong định nghĩa bảng. Để tìm hiểu thêm, xem [Relations](https://orm.drizzle.team/docs/relations-v2) trong tài liệu Drizzle.

#### Transaction trong Drizzle

Một database transaction là một đơn vị công việc mà hệ quản trị database xử lý như một khối thống nhất, độc lập với các transaction khác: hoặc mọi thay đổi của nó đều được áp dụng, hoặc không thay đổi nào cả. Để tìm hiểu thêm, xem [Database transaction](https://en.wikipedia.org/wiki/Database_transaction) trên Wikipedia.

Để bắt đầu một [transaction Drizzle](https://orm.drizzle.team/docs/transactions), gọi method `transaction()` của database đã inject. Callback nhận một object transaction (`tx`) có cùng query API như database:

[[CODE:12]]

Nếu callback throw hoặc gọi `tx.rollback()`, transaction sẽ bị rollback và `transaction()` reject với lỗi đó. Ngược lại, transaction được commit, và `transaction()` resolve với giá trị mà callback trả về. Các query thuộc transaction phải chạy qua `tx`, không phải qua database đã inject.

> info **Hint** Để chạy code từ nhiều provider trong cùng một transaction mà không phải truyền `tx` đi khắp nơi, hãy lan truyền transaction bằng `AsyncLocalStorage`. Package [`nestjs-cls`](/recipes/async-local-storage#nestjs-cls) cung cấp một plugin transactional với [Drizzle adapter](https://papooch.github.io/nestjs-cls/plugins/available-plugins/transactional/drizzle-orm-adapter) làm được việc này.

#### Repository tùy chỉnh

Drizzle không có tầng repository: bạn tạo query từ database đã inject và các định nghĩa bảng. Để giữ các query của một bảng ở một chỗ, và để các class dùng chúng dễ unit test, bạn có thể tự viết một repository dưới dạng provider thông thường:

[[CODE:13]]

Đăng ký `UsersRepository` trong mảng `providers` của `UsersModule`, và inject nó vào `UsersService` thay vì database. Trong unit test, hãy thay nó bằng một [custom provider](/fundamentals/custom-providers) có `useValue` là một object implement các method mà service của bạn gọi, như `findActive()`.

> warning **Warning** Các method của repository query trên database đã inject, không phải trên `tx` của một transaction. Với connection pool, chúng chạy trên một kết nối khác với transaction được bắt đầu ở nơi khác bằng `db.transaction()`, nên chúng không thuộc transaction đó. Để chạy chúng trong một transaction, hãy nhận `tx` làm tham số, hoặc lan truyền transaction bằng `nestjs-cls` như mô tả ở trên.

#### Migration

[Migration](https://orm.drizzle.team/docs/migrations) cập nhật dần schema database để giữ nó đồng bộ với data model của ứng dụng, trong khi vẫn giữ nguyên dữ liệu hiện có. Để sinh và chạy migration, Drizzle cung cấp một CLI chuyên dụng là [Drizzle Kit](https://orm.drizzle.team/docs/kit-overview), CLI này đọc thiết lập từ file `drizzle.config.ts` trong thư mục gốc của project:

[[CODE:14]]

Khi đã có file đó, `npx drizzle-kit generate` tạo các file migration SQL từ những thay đổi trong schema, và `npx drizzle-kit migrate` áp dụng chúng vào database.

Drizzle Kit chạy bên ngoài ứng dụng Nest của bạn, nên migration không thể dùng dependency injection hay các tính năng đặc thù khác của Nest. Drizzle Kit load file `.env` từ thư mục nơi bạn chạy nó, nên `process.env.DATABASE_URL` có sẵn trong `drizzle.config.ts` mà không cần `ConfigModule`. Các biến đã được đặt sẵn trong môi trường sẽ được ưu tiên hơn file.

Để áp dụng các migration đang chờ ngay khi ứng dụng khởi động, hãy tạo database trong một factory `forRootAsync()` và áp dụng chúng ở đó. Factory có thể là `async`, và Nest sẽ không tạo các provider inject database cho đến khi factory resolve:

[[CODE:15]]

> warning **Warning** Khi nhiều instance của ứng dụng khởi động cùng lúc, mỗi instance đều cố áp dụng migration. Với kiểu deploy như vậy, hãy chạy `drizzle-kit migrate` như một bước riêng trong quy trình release.

<app-banner-courses></app-banner-courses>

#### Nhiều database

Một số project cần nhiều kết nối database, và `DrizzleModule` cũng hỗ trợ điều này. Hãy đăng ký mỗi database bằng một lần import `DrizzleModule` riêng. Trong trường hợp này, mọi database trừ một cái phải có tên:

[[CODE:16]]

> warning **Notice** Một database đăng ký không có `name` sẽ có tên là `default`. Đừng đăng ký nhiều database không có tên, hoặc trùng tên: chúng sẽ dùng chung một injection token, và chỉ một trong số chúng được inject.

Các database không nhất thiết phải dùng chung driver: `analytics` hoàn toàn có thể là một file SQLite mở bằng hàm `drizzle()` từ `drizzle-orm/better-sqlite3`. Để inject một database khác database mặc định, hãy truyền tên của nó vào decorator `@InjectDrizzle()`:

[[CODE:17]]

Bạn cũng có thể inject bất kỳ database nào vào một factory provider bằng hàm `getDrizzleToken()`, hàm này trả về injection token của database có tên tương ứng:

[[CODE:18]]

#### Test

Khi unit test một ứng dụng, thông thường bạn muốn tránh kết nối tới database, để các test suite độc lập và chạy nhanh. Tuy nhiên, các class của bạn phụ thuộc vào database được inject bằng `@InjectDrizzle()`. Để giải quyết, hãy thay database bằng một mock, dùng một [custom provider](/fundamentals/custom-providers). Hàm `getDrizzleToken()` trả về injection token của database mặc định (hoặc của database có tên bạn truyền vào):

[[CODE:19]]

Giờ thì Nest inject object `mockDb` ở bất cứ đâu một class yêu cầu database bằng decorator `@InjectDrizzle()`. Query builder của Drizzle có thể nối chuỗi (ví dụ `select().from().where()`), nên một mock phải implement mọi method trong chuỗi mà code của bạn gọi. Với những gì vượt quá các query đơn giản, hãy chuyển các query vào [repository tùy chỉnh](/data/drizzle#custom-repositories) rồi mock chúng, hoặc chạy các bài test này với database thật.

#### Cấu hình bất đồng bộ

Để truyền tùy chọn cho `DrizzleModule` theo kiểu bất đồng bộ thay vì tĩnh, hãy dùng method `forRootAsync()`. Nó hỗ trợ vài cách để cung cấp tùy chọn.

Một cách là dùng hàm factory. Factory hoạt động như mọi [provider bất đồng bộ](/fundamentals/async-providers) khác: nó có thể là `async`, và có thể inject dependency qua `inject`. Nó trả về cùng các tùy chọn như `forRoot()` (trừ `name`), hoặc `drizzle` và `connection`, hoặc một instance `db`:

[[CODE:20]]

Cách khác là dùng cú pháp `useClass`:

[[CODE:21]]

Với cách khai báo này, `DrizzleModule` khởi tạo `DrizzleConfigService`, resolve các dependency của nó từ các module trong `imports`, và gọi method `createDrizzleOptions()` của nó để lấy tùy chọn. Do đó `DrizzleConfigService` phải implement interface `DrizzleOptionsFactory`:

[[CODE:22]]

> info **Hint** `createDrizzleOptions()` nhận tên của database đang được đăng ký (`undefined` với database mặc định), nên một class duy nhất có thể cấu hình nhiều database.

Để dùng lại một provider từ module khác thay vì khởi tạo `DrizzleConfigService` bên trong `DrizzleModule`, hãy dùng cú pháp `useExisting`:

[[CODE:23]]

Cách này hoạt động giống `useClass`, với một khác biệt quan trọng: `DrizzleModule` dùng lại instance `DrizzleConfigService` được export bởi một module đã import (ở đây là `DatabaseConfigModule`) thay vì tạo cái mới.
