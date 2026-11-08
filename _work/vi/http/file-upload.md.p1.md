### Upload và stream file

Chương này trình bày việc xử lý file theo cả hai chiều: nhận file mà client upload lên, và [stream file](#streaming-files) ngược về cho client.

Để xử lý upload file, Nest cung cấp sẵn một module dựa trên package middleware [multer](https://github.com/expressjs/multer) của Express. Multer xử lý dữ liệu gửi lên theo định dạng `multipart/form-data`, định dạng chủ yếu được dùng để upload file bằng một request HTTP `POST`. Module này có thể cấu hình hoàn toàn, nên bạn có thể điều chỉnh hành vi của nó theo yêu cầu của ứng dụng.

> warning **Warning** Multer không thể xử lý dữ liệu không ở định dạng `multipart/form-data`.

> info **Hint** Nếu ứng dụng của bạn chạy trên `FastifyAdapter`, cùng các interceptor đó có sẵn từ package `@nestjs/platform-fastify`, dựa trên [@fastify/multipart](https://github.com/fastify/fastify-multipart) thay vì Multer, và các decorator cùng pipe mô tả trong chương này hoạt động y như cũ. Chỉ có đường dẫn import là thay đổi - xem phần [Fastify](/http/file-upload#fastify) bên dưới.

> info **Hint** Nếu ứng dụng của bạn chạy trên `NodeAdapter`, hãy import các interceptor và `MulterModule` từ `@nestjs/platform-node` thay vì `@nestjs/platform-express`. Chúng chính là các interceptor dựa trên Multer, nên mọi thứ trong chương này đều áp dụng y như cũ.

Để có type safety, hãy cài các định nghĩa type của Multer:

[[CODE:1]]

Khi đã cài package này, bạn có thể dùng type `Express.Multer.File` (import namespace `Express` bằng `import {{ '{' }} Express {{ '}' }} from 'express'`).

#### Ví dụ cơ bản

Để upload một file, hãy bind interceptor `FileInterceptor()` vào route handler và lấy file từ request bằng decorator `@UploadedFile()`.

[[CODE:2]]

> info **Hint** Decorator `FileInterceptor()` được export từ package `@nestjs/platform-express`. Decorator `@UploadedFile()` được export từ `@nestjs/common`.

Decorator `FileInterceptor()` nhận hai tham số:

- `fieldName`: tên của trường trong form HTML chứa file
- `options`: một object tùy chọn có type `MulterOptions`. Đây chính là object mà constructor của Multer nhận (xem [các tùy chọn của Multer](https://github.com/expressjs/multer#multeropts)).

> warning **Warning** `FileInterceptor()` có thể không tương thích với các cloud provider bên thứ ba như Google Firebase hay các dịch vụ khác.

#### Validate file

Thường thì bạn sẽ muốn validate metadata của file gửi đến, như kích thước file hoặc MIME type. Để làm vậy, hãy tạo một [pipe](/pipes) và bind nó vào tham số được decorate bằng `@UploadedFile()`. Ví dụ sau implement một pipe validate kích thước file cơ bản:

[[CODE:3]]

Dùng nó cùng với `FileInterceptor` như sau:

[[CODE:4]]

Với các trường hợp phổ biến, Nest cung cấp sẵn một pipe là `ParseFilePipe`, pipe này cũng chuẩn hóa cách thêm các bước validate file mới:

[[CODE:5]]

`ParseFilePipe` yêu cầu một mảng các file validator để thực thi. Interface của validator được mô tả bên dưới. Pipe cũng nhận hai tùy chọn **không bắt buộc**:

<table>
  <tr>
    <td><code>errorHttpStatusCode</code></td>
    <td>HTTP status code sẽ được throw khi <b>bất kỳ</b> validator nào thất bại. Mặc định là <code>400</code> (BAD REQUEST)</td>
  </tr>
  <tr>
    <td><code>exceptionFactory</code></td>
    <td>Một factory nhận message lỗi và trả về một lỗi.</td>
  </tr>
</table>

Các validator mà pipe này dùng hoặc là bản implement có sẵn, hoặc là class con của riêng bạn kế thừa abstract class `FileValidator`:

[[CODE:6]]

> info **Hint** Method `isValid()` có thể là bất đồng bộ. Để có type safety, hãy khai báo type của tham số `file` là `Express.Multer.File` khi bạn dùng Express (HTTP adapter mặc định).

Một `FileValidator` nhận file object và validate nó theo các tùy chọn truyền vào constructor của nó. Nest cung cấp sẵn hai bản implement:

- `MaxFileSizeValidator` kiểm tra kích thước file có nhỏ hơn giá trị cung cấp hay không, tính bằng byte.
- `FileTypeValidator` kiểm tra MIME type của file có khớp với chuỗi hoặc biểu thức chính quy đã cho hay không. Mặc định, nó xác định MIME type dựa trên [magic number](https://www.ibm.com/support/pages/what-magic-number) trong nội dung file.

Đoạn code sau dùng cả hai validator với `ParseFilePipe`:

[[CODE:7]]

> info **Hint** Nếu danh sách validator dài ra, hãy định nghĩa mảng trong một file riêng và import nó dưới dạng một hằng có tên, như `fileValidators`.

Cách khác là kết hợp các validator bằng class `ParseFilePipeBuilder`. Builder tự khởi tạo từng validator giúp bạn, nên bạn chỉ cần truyền tùy chọn của chúng:

[[CODE:8]]

> info **Hint** Mặc định file là bắt buộc. Để biến nó thành tùy chọn, hãy truyền `fileIsRequired: false` trong tùy chọn của method `build()` (cạnh `errorHttpStatusCode`).

#### Mảng file

Để upload một mảng file xác định bởi một tên trường duy nhất, hãy dùng decorator `FilesInterceptor()` (để ý chữ **Files** số nhiều trong tên). Nó nhận ba tham số:

- `fieldName`: như mô tả ở trên
- `maxCount`: số file tối đa được chấp nhận (tùy chọn)
- `options`: một object `MulterOptions` tùy chọn, như mô tả ở trên

Khi dùng `FilesInterceptor()`, hãy lấy file từ `request` bằng decorator `@UploadedFiles()`.

[[CODE:9]]

> info **Hint** Decorator `FilesInterceptor()` được export từ package `@nestjs/platform-express`. Decorator `@UploadedFiles()` được export từ `@nestjs/common`.

#### Validate mảng file

Để validate một mảng file đã upload, hãy truyền một pipe tạo bằng `ParseFilePipeBuilder` vào decorator `@UploadedFiles()`. Các validator đã đăng ký sẽ chạy với từng file trong mảng.

[[CODE:10]]

#### Nhiều file

Để upload nhiều file dưới các tên trường khác nhau, hãy dùng decorator `FileFieldsInterceptor()`. Nó nhận hai tham số:

- `uploadedFields`: một mảng object, mỗi object có thuộc tính `name` bắt buộc (tên trường) và thuộc tính `maxCount` tùy chọn
- `options`: một object `MulterOptions` tùy chọn, như mô tả ở trên

Khi dùng `FileFieldsInterceptor()`, hãy lấy file từ `request` bằng decorator `@UploadedFiles()`.

[[CODE:11]]

#### File bất kỳ

Để chấp nhận file dưới bất kỳ tên trường nào, hãy dùng decorator `AnyFilesInterceptor()`. Nó nhận một object `options` tùy chọn, như mô tả ở trên.

Khi dùng `AnyFilesInterceptor()`, hãy lấy file từ `request` bằng decorator `@UploadedFiles()`.

[[CODE:12]]

#### Không có file

Để chấp nhận `multipart/form-data` mà không cho phép upload file, hãy dùng `NoFilesInterceptor`. Nó đặt các trường multipart làm thuộc tính của request body. Một request có chứa file sẽ bị từ chối với `BadRequestException`.

[[CODE:13]]

#### Tùy chọn mặc định

Bạn có thể truyền tùy chọn Multer cho từng file interceptor, như mô tả ở trên. Để đặt tùy chọn mặc định thay vào đó, hãy gọi method static `register()` khi import `MulterModule`. Nó nhận mọi [tùy chọn của Multer](https://github.com/expressjs/multer#multeropts).

[[CODE:14]]

> info **Hint** Class `MulterModule` được export từ package `@nestjs/platform-express`.

Tùy chọn truyền vào một file interceptor sẽ được ưu tiên hơn các giá trị mặc định này. Kể từ NestJS v12.0.4, hai object `limits` được merge theo từng key, nên một route chỉ đặt `limits.fileSize` vẫn giữ một giá trị mặc định như `limits.files`. Nếu một trong hai là hàm, `limits` của interceptor sẽ thay thế hoàn toàn giá trị mặc định.

#### Cấu hình bất đồng bộ

Để đặt tùy chọn cho `MulterModule` theo kiểu bất đồng bộ thay vì tĩnh, hãy dùng method `registerAsync()`. Giống như hầu hết dynamic module, nó hỗ trợ vài kỹ thuật cho cấu hình bất đồng bộ.

Một kỹ thuật là dùng hàm factory:

[[CODE:15]]

Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, hàm factory có thể là `async` và có thể inject dependency qua `inject`.

[[CODE:16]]

Cách khác là cấu hình `MulterModule` bằng một class thay vì factory, như bên dưới:

[[CODE:17]]

Cách khai báo trên khởi tạo `MulterConfigService` bên trong `MulterModule` và gọi method `createMulterOptions()` của nó để lấy options object. Để cách này hoạt động, `MulterConfigService` phải implement interface `MulterOptionsFactory`:

[[CODE:18]]

Nếu bạn muốn dùng lại một options provider đã có thay vì tạo một bản sao riêng bên trong `MulterModule`, hãy dùng cú pháp `useExisting`.

[[CODE:19]]

Bạn cũng có thể truyền `extraProviders` vào method `registerAsync()`. Các provider này được merge với các provider của module.

[[CODE:20]]

Điều này hữu ích khi hàm factory hoặc constructor của class cần thêm dependency.

#### Sử dụng bộ nhớ và storage

Mặc định, Multer dùng storage engine trong bộ nhớ (`memoryStorage()`): mọi file upload đều được đọc hoàn toàn vào bộ nhớ và cung cấp dưới dạng một `Buffer` trên `file.buffer` trước khi route handler chạy. Cách này tiện cho các file nhỏ (avatar hay file CSV để import), nhưng mỗi lần upload đang diễn ra chiếm lượng bộ nhớ bằng đúng kích thước của nó, nên file lớn hoặc nhiều lần upload đồng thời có thể nhanh chóng làm cạn bộ nhớ của process.

> warning **Warning** Mặc định, Multer không giới hạn kích thước file upload. Khi giữ file trong bộ nhớ, hãy luôn đặt `limits.fileSize`.

##### Giới hạn kích thước file

Dùng tùy chọn `limits` để từ chối các file quá lớn. Khi vượt quá một giới hạn, Nest trả lời bằng lỗi `413 File too large` (với `fileSize`) hoặc `400 Bad Request` (với các giới hạn khác, như `files`) và route handler không được gọi.

[[CODE:21]]

> info **Hint** Khác với `MaxFileSizeValidator`, vốn chạy sau khi đã nhận toàn bộ file, `limits.fileSize` khiến Multer ngừng lưu file và từ chối request ngay khi chạm tới giới hạn, nên các file quá cỡ không bao giờ được đưa trọn vẹn vào bộ nhớ hay ổ đĩa. Xem [các giới hạn của Multer](https://github.com/expressjs/multer#limits) để có danh sách tùy chọn đầy đủ.

##### Giới hạn tên trường

Các tên trường như `user[address][city]` hoặc `tags[2]` tạo ra object và mảng lồng nhau trong request body. Có hai giới hạn kiểm soát chúng: `fieldNestingDepth`, số cấp lồng nhau (`a[b][c]` có 2 cấp), và `fieldArrayIndexLimit`, chỉ số mảng cao nhất (`tags[2]` dùng chỉ số 2). Một request vượt quá một trong hai sẽ bị từ chối với response `400 Bad Request`. Kể từ NestJS v12.2, chúng có giá trị mặc định lần lượt là 32 và 1000 (Multer để chúng không giới hạn), để một request duy nhất không thể tạo ra một body lồng sâu tùy ý hay một mảng khổng lồ. Đặt một giới hạn thành `Infinity` để bỏ nó.

##### Lưu trên ổ đĩa

Để giữ mức sử dụng bộ nhớ ổn định bất kể kích thước file, hãy ghi file upload ra ổ đĩa bằng engine `diskStorage()`. Khi đó Multer stream mỗi file xuống ổ đĩa ngay khi dữ liệu đến, và file object cung cấp `destination`, `filename` và `path` thay vì `buffer`.

[[CODE:22]]

> info **Hint** Các hàm `diskStorage()` và `memoryStorage()` được export từ package `multer`. Để viết tắt, hãy truyền `dest: './uploads'` để lưu file trên ổ đĩa dưới tên ngẫu nhiên. Nếu bạn truyền một hàm `destination` thay vì một chuỗi, bạn phải tự tạo thư mục.

Để áp dụng cùng storage và giới hạn cho mọi file interceptor trong một module, hãy đặt chúng làm [tùy chọn mặc định](/http/file-upload#default-options) hoặc bằng [cấu hình bất đồng bộ](/http/file-upload#async-configuration).

File lưu trên ổ đĩa không tự động bị xóa sau khi route handler đã chạy. Hãy xóa chúng (ví dụ bằng `unlink()` từ `fs/promises`) sau khi đã xử lý xong, kể cả khi xử lý thất bại. Kể từ NestJS v12.2, nếu một pipe từ chối request (ví dụ vì validation của `ParseFilePipe` thất bại), route handler không chạy, và các file đã lưu sẽ bị xóa sau khi response lỗi đã được gửi đi.

##### Gửi file lên storage bên ngoài

Để lưu file upload lên S3, Cloudflare R2 hoặc một store bên ngoài khác mà không buffer chúng trong bộ nhớ hay ghi ra file tạm, hãy dùng một storage engine stream từng file tới đích ngay khi dữ liệu đến. Package [`@nestjs/storage`](/application/file-storage) cung cấp một engine như vậy, `uploadToDisk()`, bạn truyền nó làm tùy chọn `storage` của `FileInterceptor()`. Xem [Upload ảnh sản phẩm](/application/file-storage#upload-product-photos). Mọi [storage engine](https://github.com/expressjs/multer/blob/main/StorageEngine.md) khác của Multer cũng hoạt động theo cùng cách.

> info **Hint** Trên `FastifyAdapter`, bạn cũng có thể nhận file dưới dạng stream ngay bên trong route handler bằng `FileStreamInterceptor()`. Xem [Stream upload](/http/file-upload#streaming-uploads).
