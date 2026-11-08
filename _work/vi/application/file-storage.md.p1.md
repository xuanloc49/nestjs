### Lưu trữ file

`@nestjs/storage` lưu file trên các disk có tên (một thư mục local, S3 hoặc một store tương thích S3 như R2) phía sau một API duy nhất, kèm URL công khai và URL có chữ ký (signed URL).

Một cửa hàng online bán thức ăn và đồ dùng cho mèo lưu ba loại file. Ảnh sản phẩm do nhân viên tải lên và hiển thị cho mọi người. Hóa đơn là các file PDF mà chỉ khách hàng đã thanh toán mới được tải về. Còn team kho chụp ảnh sản phẩm bằng app mobile của cửa hàng, app này tải lên những bức ảnh dung lượng lớn mà không nên phải đi qua API đơn hàng.

Ở môi trường development, mọi thứ này nên chạy được với một thư mục trên laptop. Trên production, file được đưa lên S3 hoặc Cloudflare R2, vì API chạy trên nhiều instance và không instance nào có ổ đĩa tồn tại lâu dài. Code lưu và phục vụ file nên giống nhau ở cả hai nơi.

`@nestjs/storage` đặt cho mỗi nơi lưu file một cái tên, gọi là **disk**, và một API cho tất cả: `put()`, `get()`, `list()`, `delete()`, URL công khai và signed URL. Nó có sẵn một local disk, một S3 disk chạy được với AWS S3 và các store tương thích S3 (Cloudflare R2, MinIO, Backblaze B2), và một in-memory disk cho test. Nó nói chuyện với S3 qua `fetch`, không cần AWS SDK, và chỉ phụ thuộc vào `@nestjs/common` và `@nestjs/core`.

Nó không parse upload. multer trên Express và `@nestjs/platform-fastify/multipart` trên Fastify vẫn làm việc đó, với `FileInterceptor()` như thường lệ. Package này là nơi file được đưa đến cuối cùng: nó cung cấp một storage engine stream mỗi file upload thẳng lên một disk.

Trong bài hướng dẫn này, bạn sẽ:

- cấu hình một disk công khai cho ảnh và một disk private cho mọi thứ khác,
- stream ảnh upload lên disk ảnh, với type và kích thước được kiểm tra trước khi ghi bất cứ thứ gì,
- lưu hóa đơn ở chế độ private và cấp link tải về hết hạn sau năm phút,
- cho app mobile upload ảnh thẳng lên storage, bằng một signed upload URL,
- chuyển từ local disk sang S3 hoặc R2 chỉ bằng cấu hình,
- test tất cả với in-memory disk.

#### Cài đặt

Để bắt đầu, hãy cài các dependency cần thiết:

[[CODE:1]]

#### Cấu hình disk

App cần hai disk. `photos` chứa ảnh sản phẩm, ai cũng được xem, nên nó có URL công khai. `private` chứa hóa đơn và các file upload chưa được kiểm tra, và chỉ truy cập được qua signed URL. Giữ file công khai và file private trên các disk riêng (trên production là các bucket riêng) đảm bảo một file không bao giờ vô tình bị công khai.

Bắt đầu với cấu hình, một [file cấu hình tùy chỉnh](/application/configuration#custom-configuration-files) cho `@nestjs/config`. `STORAGE_DRIVER` sẽ chọn local disk hoặc S3 [trên production](/application/file-storage#use-s3-or-r2-in-production); cho đến lúc đó, mọi thứ đều là local:

[[CODE:2]]

Các disk được tạo từ cấu hình đó bởi một hàm factory:

[[CODE:3]]

Một `LocalDisk` giữ file trong một thư mục, thư mục này được tạo lúc khởi động. `publicUrl` là nơi file có thể được truy cập công khai: `url(key)` của disk ảnh trả về các URL nằm dưới nó. Ở development, chính app sẽ phục vụ path đó (xem [Upload ảnh sản phẩm](/application/file-storage#upload-product-photos)); trên production, một CDN sẽ làm việc này.

Một thư mục local không thể tạo signed URL theo cách S3 làm, nên disk private tự ký: với `signedUrls`, `signedUrl()` của nó trả về các URL nằm dưới `baseUrl`, được ký bằng HMAC-SHA256, và app sẽ xác minh rồi phục vụ chúng (xem [Phục vụ signed URL trong development](/application/file-storage#serve-signed-urls-in-development)). `keys` nhận một hoặc nhiều key. Key đầu tiên dùng để ký, và tất cả đều dùng để xác minh, nên bạn có thể xoay vòng key bằng cách đặt key mới lên đầu và bỏ key cũ khi các link nó đã ký đều hết hạn. Một key phải có ít nhất 32 ký tự.

Đăng ký module bằng `forRootAsync()`, để factory có thể đọc `ConfigService`:

[[CODE:4]]

`StorageModule` là global. Service inject một disk theo một trong ba cách:

| Cách inject | Bạn nhận được |
| --- | --- |
| `private readonly files: StorageDisk` | Disk mặc định, ở đây là `private` |
| `@InjectDisk('photos') private readonly photos: StorageDisk` | Disk có tên `photos` |
| `private readonly storage: Storage` | Mọi disk: `storage.disk('photos')`, cho code chọn disk lúc runtime |

Lỗi cấu hình sẽ làm ứng dụng dừng ngay lúc khởi động. Không có `STORAGE_SIGNING_KEY`, `getOrThrow()` sẽ báo thiếu key; với key quá ngắn, lỗi sẽ nói signing key phải có ít nhất 32 ký tự. Điều tương tự áp dụng cho một `default` không trỏ tới disk nào, và cho một class inject tên disk mà không cấu hình nào cung cấp:

[[CODE:5]]

#### Upload ảnh sản phẩm

Ảnh có thể là JPEG, PNG hoặc WebP, tối đa 5 MiB. Các quy tắc này được dùng chung bởi endpoint upload bên dưới và phần [upload từ mobile](/application/file-storage#upload-straight-to-storage-from-the-mobile-app) phía sau:

[[CODE:6]]

Endpoint upload dùng `FileInterceptor()` từ `@nestjs/platform-express`, như mọi upload khác. Điểm khác biệt là tùy chọn `storage`: `uploadToDisk()` là một multer storage engine stream file lên disk thay vì vào bộ nhớ hay thư mục tạm:

[[CODE:7]]

Đến lúc handler chạy, ảnh đã được lưu xong. `uploadToDisk()` đã làm ba việc trên đường đi:

- **Nó kiểm tra file thực sự là gì, chứ không phải client nói nó là gì.** Trình duyệt gửi type mà nó đoán từ tên file, còn một script có thể gửi bất cứ thứ gì, nên một file khai báo là `image/png` hoàn toàn có thể là một trang HTML hoặc một file SVG có chứa script. Engine đọc những byte đầu tiên của stream, nhận diện type từ chữ ký của chúng (có sẵn JPEG, PNG, GIF, WebP, AVIF, HEIC và PDF; [các định dạng khác](/application/file-storage#accept-csv-and-other-text-formats) cần một detector của riêng bạn), và từ chối mọi thứ không nằm trong `contentTypes` bằng lỗi `415` trước khi ghi bất kỳ byte nào. Content type được lưu là type đã nhận diện, không bao giờ là type của client.
- **Nó áp dụng giới hạn kích thước mà không để lại file dở dang.** multer ngừng đọc khi tới `limits.fileSize`. Khi đó engine từ chối commit những gì đã nhận: request thất bại với `413 File too large`, không có gì được lưu, và không file nào bị thay thế.
- **Nó chọn key.** Mặc định là một UUID ngẫu nhiên kèm phần mở rộng của type đã nhận diện, như `2f1c0d6e-….png`. Key duy nhất rất quan trọng: một lần upload không bao giờ ghi đè lên file khác, và một ảnh đã cache không bao giờ bị cũ.

`@UploadedFile()` trả về một `StoredUpload`: các trường quen thuộc của multer (`fieldname`, `originalname`, `mimetype`, `size`) cộng thêm `key`, `disk`, `contentType` và `etag`. `mimetype` vẫn là lời khai của client; hãy dùng `contentType`.

> info **Hint** `ParseFilePipe` và các validator của nó chạy sau interceptor, khi file được stream đã được lưu xong, còn `FileTypeValidator` cần file nằm trong bộ nhớ để kiểm tra các byte của nó. Với `uploadToDisk()`, hãy kiểm tra type và kích thước trong engine, như ở trên. Trên Fastify, import `FileInterceptor` từ `@nestjs/platform-fastify/multipart` và đăng ký `@fastify/multipart`; `uploadToDisk()` hoạt động giống nhau với cả hai.

Sản phẩm có cấu trúc như sau, và `ProductsService` của ứng dụng có `findOne(id)`, method này throw `NotFoundException` với id không tồn tại, cùng `setPhoto(id, key)`:

[[CODE:8]]

Service ghi nhận ảnh mới, và xóa ảnh cũ:

[[CODE:9]]

Interceptor chạy trước handler, nên file vẫn được lưu kể cả khi hóa ra sản phẩm không tồn tại. Trong trường hợp đó, service sẽ xóa nó, để một id gõ sai không để lại file mồ côi. `url(key)` tạo URL công khai từ `publicUrl` của disk.

Route `GET photos/:file` phục vụ ảnh trong development. `serveFile()` stream một file từ disk làm response, kèm `Content-Type`, `Content-Length`, `ETag`, `Last-Modified`, `Cache-Control` được lưu cùng file (`private` nếu không có, để shared cache không bao giờ giữ lại một file có thể chỉ thuộc về một người dùng), và `X-Content-Type-Options: nosniff`, để trình duyệt không bao giờ tự đoán lại type. `disposition: 'inline'` cho phép trình duyệt hiển thị ảnh; với những type có thể chạy script trong origin của bạn, như HTML hay SVG, `serveFile()` luôn gửi `Content-Disposition: attachment`. Nó trả lời request `Range` bằng `206`, `If-None-Match` bằng `304`, và file không tồn tại bằng `404`.

Đăng ký feature module, và import `ProductsModule` trong `AppModule`:

[[CODE:10]]

##### Chấp nhận CSV và các định dạng text khác

Việc nhận diện có sẵn nhận ra định dạng dựa vào các byte cố định mà file bắt đầu. Một file CSV không có chữ ký như vậy, nên chỉ riêng `contentTypes: ['text/csv']` sẽ từ chối mọi file CSV bằng lỗi `415`. Với định dạng như thế, hãy truyền `detectContentType`: một hàm nhận phần đầu của file và trả về type của nó, hoặc `undefined` khi không nhận ra.

Nhân viên cập nhật giá bằng cách upload một file export từ bảng tính. App nhận ra file này qua dòng tiêu đề của nó:

[[CODE:11]]

Endpoint upload cho phép `text/csv` và truyền hàm đó vào `uploadToDisk()`. Bảng giá được đưa lên disk private, vì chưa ai kiểm tra các dòng của nó:

[[CODE:12]]

- **Việc nhận diện có sẵn chạy trước.** Hàm chỉ chạy khi file không thuộc định dạng có sẵn nào. Một file PNG bị đổi tên thành `prices.csv` vẫn được nhận diện là PNG, và bị từ chối. Truyền helper `detectContentType()` được export làm tùy chọn không có tác dụng gì, vì đó chính là bước kiểm tra đã chạy rồi.
- **Nó thấy phần đầu của file.** `bytes` chứa 4 KiB đầu tiên, hoặc toàn bộ file khi file nhỏ hơn. Để thay đổi, đặt `contentTypeSampleBytes` thành một số nguyên từ 1 byte tới 64 KiB (yêu cầu có `detectContentType`). Tham số thứ hai có `originalname` và `mimetype`, nhưng đó là lời khai của client, nên hãy quyết định dựa trên các byte.
- **Giá trị nó trả về được kiểm tra với `contentTypes`.** Type được so sánh mà không tính tham số: `text/csv` trong danh sách sẽ cho phép `text/csv; charset=utf-8`. Khi hàm trả về `undefined`, hoặc một type không có trong danh sách, upload sẽ bị từ chối bằng lỗi `415` trước khi ghi bất kỳ byte nào. Không có `contentTypes`, mọi type được trả về đều được chấp nhận, và một file không nhận ra được sẽ lưu dưới dạng `application/octet-stream`.
- **Type được trả về là type mà file được lưu và phục vụ.** Hãy kèm charset với các định dạng text. Nó cũng quyết định phần mở rộng: `file.extension` là `.csv` trong `key()` ở trên, và key mặc định cũng kết thúc bằng nó.
- **Nó có thể là async.** Engine chờ promise trong khi giữ request, nên promise phải settle nhanh. Hãy trả về `undefined` với file không nhận ra thay vì throw: một lỗi sẽ làm upload thất bại như ở bất kỳ chỗ nào khác trong request, nên mọi thứ không phải `HttpException` sẽ thành lỗi `500` thay vì `415`. Trả về bất cứ thứ gì không phải chuỗi hoặc `undefined` cũng vậy.

> warning **Warning** Hàm này phân loại phần đầu của file. Nó không validate file: một bảng giá có dòng tiêu đề đúng vẫn có thể chứa bất cứ thứ gì phía sau. `PriceListsService.import()` phải đọc toàn bộ file, kiểm tra mọi dòng, và xóa `file.key` khi từ chối bảng giá, như với mọi bước kiểm tra chạy sau interceptor.

#### Giữ hóa đơn ở chế độ private

Hóa đơn được tạo ra lần đầu tiên khi khách hàng yêu cầu và được lưu trên disk private. Một app thực tế render PDF bằng một library hoặc dịch vụ render; bản thay thế này đủ để theo dõi luồng xử lý:

[[CODE:13]]

Service đọc đơn hàng bằng `OrdersService` của ứng dụng, trong đó đơn hàng `ord_1000` đã thanh toán còn `ord_1001` thì chưa, lưu hóa đơn một lần, và trả về một signed link tới nó:

[[CODE:14]]

`put()` nhận một `Buffer`, một chuỗi, một `Uint8Array`, một Node stream, một web `ReadableStream`, hoặc bất kỳ async iterable byte nào. Trên mọi disk, một thao tác ghi là nguyên tử: bên đọc thấy file cũ hoặc file mới, không bao giờ thấy một nửa, và một thao tác ghi thất bại không để lại gì. `metadata` lưu các giá trị chuỗi của riêng bạn cùng với file; `stat()` và `get()` trả về chúng.

Với `LocalDisk`, một thao tác ghi filesystem thất bại sẽ xóa file tạm và giữ nguyên file đã có. Nếu việc ghi không tiến triển, hoặc kích thước đã lưu khác với số byte đã ghi, `put()` sẽ reject với `StorageError`.

`signedUrl()` trả về một link dùng được mà không cần thông tin xác thực nào khác cho đến khi hết hạn. `expiresIn` là một khoảng thời gian: `'5m'`, `'1h'`, hoặc số mili giây, mặc định là 15 phút và tối đa 7 ngày, giới hạn của S3. `filename` đặt tên mà trình duyệt dùng để lưu file.

Endpoint trả về link thay vì file, để một trang web hoặc app mobile có thể mở trực tiếp:

[[CODE:15]]

Đăng ký `OrdersController`, `OrdersService` và `InvoicesService` trong một `OrdersModule`. Trong app thực tế, endpoint còn kiểm tra hóa đơn có thuộc về khách hàng đang đăng nhập hay không, ví dụ bằng một policy từ bài hướng dẫn [phân quyền](/security/authorization). Bản thân link không cần kiểm tra: ai giữ nó đều tải được đúng file đó cho đến khi hết hạn.

#### Phục vụ signed URL trong development

Với local disk, signed link trỏ tới chính app, `http://localhost:3000/files?key=…&expires=…&signature=…`, nên app cần một route để xác minh và phục vụ nó:

[[CODE:16]]

`serveSignedUrl()` kiểm tra chữ ký, thời hạn và method, rồi trả lời giống như `serveFile()`, với tên file mà link được ký kèm. Chữ ký bao gồm route (`baseUrl`), key, thời hạn và tên file, nên thay đổi bất kỳ thứ nào trong đó sẽ ra `403 Invalid signed URL`, một link đã quá hạn sẽ ra `403 The signed URL has expired`, và một link cấp cho route của một disk sẽ bị route của disk khác từ chối, kể cả khi cả hai dùng chung signing key. Các trình quản lý tải xuống có thể tiếp tục tải một file lớn bằng request `Range`.

Đăng ký controller trong một `FilesModule`, và import nó trong `AppModule` cùng các tính năng khác:

[[CODE:17]]

Route vẫn nằm trong app trên production. Ở đó, disk private là một S3 disk với signed URL trỏ tới bucket, nên `serveSignedUrl()` không có gì để phục vụ và trả lời `404`.

#### Upload thẳng lên storage từ app mobile

Team kho chụp ảnh sản phẩm bằng app mobile. Ảnh có dung lượng lớn, và điện thoại thường dùng kết nối chậm, nên một lần upload qua API sẽ chiếm một kết nối và một request trong suốt thời gian upload. Thay vào đó, app xin API một upload URL, gửi ảnh thẳng lên storage, rồi báo cho API là đã xong:

1. `POST /products/:id/photo/uploads` kèm type và kích thước của ảnh trả về một signed upload URL.
2. App gửi ảnh tới URL đó bằng `PUT`.
3. `PUT /products/:id/photo` kèm key của file upload biến nó thành ảnh của sản phẩm.

File upload được đưa lên disk private, dưới `incoming/`, vì API chưa xem xét nó. Chỉ sau khi kiểm tra xong, API mới copy nó sang disk ảnh:

[[CODE:18]]

`signedUpload()` trả về URL, method (`PUT`), các header mà client phải gửi, và thời điểm URL hết hạn. URL được ký cho đúng content type và kích thước đã khai báo: một `Content-Type` khác, hoặc một body có độ dài khác, sẽ bị storage từ chối (`403`), nên app không thể gửi một video 2 GB trong khi đã khai báo một bức ảnh 2 MB.

Type đã khai báo vẫn là lời khai của client. Vì vậy `completeUpload()` xem file upload là không đáng tin:

- **Key phải là key mà nó đã cấp cho sản phẩm này.** Không có bước kiểm tra này, client có thể gửi `invoices/ord_1000.pdf` và khiến API copy hóa đơn của người khác sang disk ảnh công khai.
- **Kích thước được kiểm tra lại** bằng `stat()`, method này trả về metadata của file mà không kèm body.
- **Các byte được kiểm tra** bằng cách chỉ đọc 16 byte đầu tiên, bằng một lời gọi `get()` có range, rồi truyền chúng vào `detectContentType()`, hàm này nhận diện JPEG, PNG, GIF, WebP, AVIF, HEIC và PDF.

Chỉ sau đó ảnh mới được stream từ disk này sang disk kia: `get()` trả về body dưới dạng Node stream, và `put()` nhận nó, nên file không bao giờ nằm trọn vẹn trong bộ nhớ. Trên S3, đó là một lần tải xuống và một lần tải lên đi qua instance API, điều này ổn với ảnh; với các file rất lớn, bạn nên xử lý chúng ngay tại chỗ, ví dụ bằng một job.

Hai route trong controller chuyển tiếp request:

[[CODE:19]]

Với local disk, upload URL lại trỏ tới app, nên `FilesController` cũng nhận cả `PUT`. `receiveSignedUpload()` làm đúng những gì S3 làm với presigned URL: nó kiểm tra chữ ký, thời hạn, content type và độ dài, rồi stream body lên disk:

[[CODE:20]]

> info **Hint** Trên Fastify, body của file upload phải đến handler mà chưa bị đọc. Mặc định Fastify chỉ parse JSON và plain text, và trả lời các content type khác bằng `415`, nên hãy đăng ký một parser bắt mọi type mà để nguyên body: `app.getHttpAdapter().getInstance().addContentTypeParser('*', (req, payload, done) => done(null))`.

Các file upload không bao giờ được hoàn tất sẽ nằm lại dưới `incoming/`. Trên S3, một lifecycle rule sẽ xóa chúng sau một ngày (xem checklist cho production).

#### Dùng S3 hoặc R2 trên production

Trên production, cả hai disk đều trở thành S3 disk. Local disk không thể phục vụ ở đó: file system của container bị hủy khi task bị thay thế (một đợt deploy, một lần scale-in, một node lỗi), kéo theo cả các file, và các instance khác không đọc được chúng. Chỉ có factory thay đổi; mọi service, controller và signed URL vẫn tiếp tục hoạt động:

[[CODE:21]]

`S3Disk` đọc thông tin xác thực từ các biến chuẩn `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` và `AWS_SESSION_TOKEN`, trừ khi bạn truyền `credentials`, là một object hoặc một hàm trả về chúng (được gọi trước mỗi request, dành cho thông tin xác thực được xoay vòng). Không có thông tin xác thực, app sẽ không khởi động. Cùng một class dùng được cho nhiều dịch vụ:

| Dịch vụ | Thiết lập |
| --- | --- |
| AWS S3 | `region`, như `eu-central-1`. Không có `endpoint` |
| Cloudflare R2 | `endpoint: 'https://<account id>.r2.cloudflarestorage.com'`, `region: 'auto'` |
| MinIO | `endpoint: 'http://minio:9000'`, `forcePathStyle: true` |
| Backblaze B2 | `endpoint: 'https://s3.<region>.backblazeb2.com'`, `region` |
| Google Cloud Storage | `endpoint: 'https://storage.googleapis.com'`, HMAC key làm thông tin xác thực, `batchDelete: false` |

Với S3, `signedUrl()` và `signedUpload()` trả về presigned URL, được ký bằng thông tin xác thực, và bucket tự xác minh chúng: route `/files` của app không tham gia. `url()` trả về các URL nằm dưới `publicUrl`, thường là một CDN hoặc domain public bucket của R2 đặt trước bucket ảnh.

Upload cũng được stream lên S3. Một file tối đa 8 MiB được tải lên trong một request; file dài hơn, hoặc một stream không biết trước độ dài, được tải lên dưới dạng multipart upload, bốn phần 8 MiB mỗi lần, và bị hủy nếu có bất kỳ lỗi nào, nên một lần upload thất bại không bao giờ trở thành file. Các request thất bại do lỗi mạng, timeout, bị giới hạn tốc độ (`429`, `SlowDown`) hoặc lỗi `5xx` sẽ được retry có backoff, tổng cộng tối đa 3 lần thử. `multipart`, `retry` và `timeout` tinh chỉnh việc này cho từng disk.

> info **Hint** Mọi request S3 đều được ký bằng Signature Version 4, implement trên `node:crypto`. Nó được kiểm tra với bộ test AWS Signature Version 4 và các ví dụ trong tài liệu API của Amazon S3, nên không cần cài AWS SDK.

#### Thử ngay

Khởi động app với một signing key, trong một thư mục có file `kibble.png`, `scratching-post.jpg` và `notes.txt`:

[[CODE:22]]

Upload một bức ảnh. Sau đó thử một file text khai báo là ảnh, app sẽ từ chối mà không lưu nó:

[[CODE:23]]

Lấy header của một bức ảnh:

[[CODE:24]]

Lấy signed link tới một hóa đơn, tải nó về, và thử cùng link đó cho một đơn hàng khác:

[[CODE:25]]

Cuối cùng, upload một bức ảnh theo cách app mobile làm. Xin một upload URL, gửi file lên đó, và gửi key của nó:

[[CODE:26]]

Các file nằm trong `storage/photos` và `storage/private`, dưới dạng file thông thường: `storage/private/invoices/ord_1000.pdf` là hóa đơn. Thư mục `.nest-storage` trong mỗi disk chứa các file tạm trong lúc ghi, và các metadata mà tên file không chứa được.

#### Test

`InMemoryDisk` giữ file trong bộ nhớ và hoạt động giống các disk khác: cùng quy tắc key, range, liệt kê, metadata và signed URL. Giống như S3, nó có thể chứa cả `a` lẫn `a/b`, điều mà local disk từ chối bằng `StorageKeyConflictError`. Trong một end-to-end test, hãy thay các disk bằng cách ghi đè `STORAGE_MODULE_OPTIONS`, tức các tùy chọn mà factory lẽ ra sẽ trả về:

[[CODE:27]]

Các tùy chọn ghi đè thay thế kết quả của factory, nên bài test không cần signing key và không đụng tới file system. `keys()` liệt kê những gì một disk đang chứa và `clear()` xóa sạch nó. File upload đi qua multer và `uploadToDisk()` giống như trên production; chỉ có nơi các byte được ghi xuống là khác.

Để test những gì thực sự được ghi xuống file system, hãy dùng một `LocalDisk` trên một thư mục tạm. Với các hành vi đặc thù của S3, như presigned URL hay multipart upload, hãy trỏ một `S3Disk` tới MinIO hoặc một server tương thích S3 khác chạy ở local.
