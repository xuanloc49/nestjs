#### Checklist cho production

- **Giữ file công khai và file private trong các bucket riêng.** Cấp quyền đọc công khai cho bucket ảnh, hoặc đặt một CDN phía trước nó và trỏ `publicUrl` tới CDN. Giữ bucket private hoàn toàn private: hóa đơn và file upload chỉ truy cập được qua signed URL. Không có flag công khai cho từng file, vì các bucket S3 mới đã tắt object ACL, và một flag trên từng file rất dễ đặt sai.
- **Cho các file upload bị bỏ dở hết hạn.** Thêm một lifecycle rule vào bucket private để xóa các object dưới `incoming/` sau một ngày, và một rule để hủy các multipart upload chưa hoàn tất sau một ngày.
- **Cho phép upload trực tiếp từ trình duyệt bằng CORS.** App mobile không cần, nhưng một trang web gửi `PUT` tới presigned URL thì cần: hãy cho phép `PUT` từ origin của site bạn, kèm header `Content-Type`.
- **Chỉ cấp cho app những quyền nó dùng.** Một IAM policy với `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` và `s3:ListBucket` trên hai bucket là đủ. Hãy giữ `s3:ListBucket`: không có nó, S3 trả lời request tới file không tồn tại bằng `403` thay vì `404`, và `exists()` sẽ lỗi thay vì trả về `false`. Với thông tin xác thực ngắn hạn, hãy truyền một hàm `credentials` trả về chúng.
- **Mã hóa dữ liệu lưu trữ.** S3 mặc định mã hóa các object mới; để dùng KMS key của riêng bạn, đặt `serverSideEncryption: 'aws:kms'` và `kmsKeyId` trên disk. R2 luôn mã hóa.
- **Giữ link ngắn hạn.** Năm phút là quá đủ cho một link mà người dùng click ngay. Signed URL không thể thu hồi: nó vẫn hợp lệ cho đến khi hết hạn (hoặc, trên S3, cho đến khi thông tin xác thực đã ký nó hết hạn hoặc mất quyền truy cập), nên ai có được nó nếu bị lộ đều dùng được cho đến lúc đó.
- **Đặt một signing key cho mỗi môi trường** với local disk (development và CI), lấy từ secret, có ít nhất 32 ký tự, và xoay vòng nó bằng cách đặt key mới lên đầu trong `keys`.
- **Đừng dùng local disk trên production.** File ghi vào ổ đĩa của container sẽ biến mất khi task bị thay thế, và các instance khác không đọc được chúng. Hãy dùng S3, R2 hoặc một object store khác (xem [Dùng S3 hoặc R2 trên production](/application/file-storage#use-s3-or-r2-in-production)); local disk dành cho development và test, và module sẽ log cảnh báo lúc khởi động khi phát hiện local disk với `NODE_ENV=production`.
- **Cẩn trọng với mọi key được tạo từ dữ liệu người dùng nhập vào.** Key được validate trên mọi disk (không có `..`, không có đường dẫn tuyệt đối, không có ký tự điều khiển), nên dữ liệu người dùng không thể thoát ra khỏi một disk, nhưng vẫn có thể trỏ tới bất kỳ file nào trên disk đó. Hãy tạo key từ các id do bạn kiểm soát, như các endpoint upload ở trên.

#### Tham khảo

##### Tùy chọn module

`StorageModule.forRoot()` nhận các tùy chọn này, và factory của `forRootAsync()` trả về `default` cùng các instance disk. Class disk, `imports` và `isGlobal` đặt cạnh `useFactory`, `useClass` hoặc `useExisting`. Các tùy chọn được cung cấp dưới dạng `STORAGE_MODULE_OPTIONS`.

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `disks` | không có (bắt buộc) | Các disk theo tên: instance, hoặc class `StorageDisk` để Nest khởi tạo, các class này có thể inject. Xem [Cấu hình disk](/application/file-storage#configure-the-disks). |
| `default` | disk duy nhất | Disk mà `StorageDisk` và `storage.disk()` resolve ra. Bắt buộc khi có nhiều hơn một disk. |
| `imports` | không có | Các module có export mà class disk inject. |
| `isGlobal` | `true` | Đăng ký `Storage`, `StorageDisk` và các disk có tên ở cấp global. |

##### Method của disk

Mọi disk đều có cùng method, quy tắc key và lỗi. Một key là một đường dẫn tương đối phân cách bằng `/`, tối đa 1024 byte UTF-8, không có segment rỗng, `.` hay `..`, không có dấu gạch chéo ngược hay ký tự điều khiển.

| Method | Mô tả |
| --- | --- |
| `put(key, body, options)` | Ghi file theo kiểu nguyên tử. Tùy chọn: `contentType` (mặc định suy ra từ phần mở rộng), `cacheControl`, `contentDisposition`, `metadata` (các giá trị chuỗi, tổng cộng 2 KB), `contentLength`, `signal`. Resolve ra `key`, `size`, `contentType` và `etag`. |
| `get(key, options)` | Metadata của file và `body` của nó dưới dạng Node stream. `range` nhận `start` và `end` (tính cả byte cuối), hoặc `suffix`. |
| `getBuffer(key)`, `getText(key)` | Toàn bộ file. |
| `stat(key)`, `exists(key)` | Metadata không kèm body, hoặc file có tồn tại hay không. |
| `delete(keys)` | Một key hoặc một mảng. Key không tồn tại sẽ bị bỏ qua. |
| `list(options)`, `listAll(options)` | Một trang gồm `key`, `size`, `lastModified` và `etag` theo thứ tự byte UTF-8, kèm `cursor`. Tùy chọn: `prefix`, `cursor`, `limit` (tối đa 1000, cũng là mặc định). `listAll()` duyệt qua mọi trang. |
| `copy(from, to)`, `move(from, to)` | Trong cùng disk, kèm cả metadata. |
| `url(key)` | URL công khai nằm dưới `publicUrl`. Throw nếu không có giá trị này. |
| `signedUrl(key, options)` | Một link tải về. Tùy chọn: `expiresIn` (mặc định 15 phút, tối đa 7 ngày), `filename`, `disposition`. Xem [Giữ hóa đơn ở chế độ private](/application/file-storage#keep-invoices-private). |
| `signedUpload(key, options)` | `url`, `method` (`PUT`), `headers` và `expiresAt` cho một lần upload trực tiếp. Tùy chọn: `contentType` (bắt buộc), `contentLength`, `expiresIn`. Xem [Upload thẳng lên storage từ app mobile](/application/file-storage#upload-straight-to-storage-from-the-mobile-app). |

##### Disk

| Disk | Tùy chọn |
| --- | --- |
| `LocalDisk` | `root` (bắt buộc, được tạo lúc khởi động), `publicUrl`, `signedUrls`. Dành cho development và test. `path(key)` trả về đường dẫn tuyệt đối của một file. |
| `S3Disk` | `bucket` (bắt buộc), `region`, `endpoint`, `forcePathStyle`, `credentials`, `prefix`, `serverSideEncryption`, `kmsKeyId`, `multipart`, `retry`, `timeout`, `batchDelete`, `fetch`, `publicUrl`. Xem [Dùng S3 hoặc R2 trên production](/application/file-storage#use-s3-or-r2-in-production). |
| `InMemoryDisk` | `publicUrl`, `signedUrls`. Dành cho test, với `keys()` và `clear()`. Xem [Test](/application/file-storage#testing). |

`signedUrls` nhận `baseUrl`, route phục vụ các URL, và `keys`, các signing key có ít nhất 32 ký tự. Key đầu tiên dùng để ký, và tất cả dùng để xác minh. Giá trị mặc định của `S3Disk`: `region` lấy từ `AWS_REGION`, rồi `AWS_DEFAULT_REGION`, rồi `us-east-1`; thông tin xác thực từ `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` và `AWS_SESSION_TOKEN`; `multipart` với `partSize` là 8 MiB và `concurrency` là 4; `retry: 3`, với backoff bắt đầu từ 100 ms và nhân đôi tới 20 giây; không có `timeout`; `batchDelete: true`.

##### Helper HTTP

| Helper | Tùy chọn | Mô tả |
| --- | --- | --- |
| `uploadToDisk(options)` | `disk` (tên hoặc instance, mặc định là disk mặc định), `contentTypes`, `detectContentType`, `contentTypeSampleBytes` (mặc định 4 KiB, từ 1 byte tới 64 KiB, yêu cầu có `detectContentType`), `cacheControl`, `key`, `metadata` | Một storage engine cho `FileInterceptor()`. `key` và `metadata` là các hàm theo file và request. `detectContentType(bytes, file)` trả về type của một file mà việc nhận diện có sẵn không nhận ra, hoặc `undefined`, và có thể trả về promise. Xem [Upload ảnh sản phẩm](/application/file-storage#upload-product-photos) và [Chấp nhận CSV và các định dạng text khác](/application/file-storage#accept-csv-and-other-text-formats). |
| `serveFile(disk, key, options)` | `res` (bắt buộc), `req`, `disposition` (mặc định `attachment`), `filename`, `cacheControl` | Stream một file làm response, hỗ trợ `Range` và `If-None-Match` khi có truyền `req`. |
| `serveSignedUrl(disk, options)` | `req`, `res`, `cacheControl` | Xác minh và phục vụ một signed download URL do app phục vụ. Xem [Phục vụ signed URL trong development](/application/file-storage#serve-signed-urls-in-development). |
| `receiveSignedUpload(disk, options)` | `req`, `res`, `maxSize` | Xác minh một signed upload URL do app phục vụ và stream body của `PUT` lên disk. `maxSize` giới hạn các upload được ký mà không có `contentLength`. |
| `detectContentType(bytes)` | không có | Type của một file dựa trên 16 byte đầu tiên: JPEG, PNG, GIF, WebP, AVIF, HEIC hoặc PDF, nếu không thì `undefined`. Đây chính là bước nhận diện có sẵn mà `uploadToDisk()` chạy, và không liên quan gì tới tùy chọn `detectContentType`. |

##### Lỗi

Mọi lỗi đều kế thừa `StorageError`. Bên ngoài các helper HTTP, chúng không phải là `HttpException`, nên hãy tự map chúng trong code của bạn ở những chỗ chúng có ý nghĩa với API.

| Lỗi | `status` | Khi nào |
| --- | --- | --- |
| `StorageFileNotFoundError` | 404 | `get()`, `stat()`, `copy()` hoặc `move()` với key không tồn tại. Có `key`. |
| `StorageInvalidKeyError` | 400 | Một key vi phạm quy tắc key. Có `reason`. |
| `StorageBodyLengthError` | 400 | Body không khớp với `contentLength`. Có `expected` và `received`. |
| `StorageRangeNotSatisfiableError` | 416 | Một range bắt đầu sau điểm cuối của file. Có `size`. |
| `StorageKeyConflictError` | 409 | Local disk không thể chứa cả `a` lẫn `a/b`. |
| `StorageSignedUrlError` | 403 | Signed URL không qua được bước xác minh. `reason` là `missing`, `invalid`, `expired` hoặc `method`. |
| `StorageServiceError` | không có | Object store từ chối hoặc gặp lỗi. Có `code` (như `AccessDenied` hoặc `SlowDown`), `upstreamStatus`, `requestId` và `operation`. |
