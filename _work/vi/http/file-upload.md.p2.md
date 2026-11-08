#### Fastify

Kể từ NestJS v12.1, các ứng dụng chạy trên `FastifyAdapter` (xem [Fastify adapter](/http/performance#fastify-adapter)) có thể xử lý upload file bằng cùng API, dựa trên plugin [@fastify/multipart](https://github.com/fastify/fastify-multipart) thay vì Multer. Các interceptor mô tả trong chương này nhận cùng tham số và tùy chọn, điền request theo cùng cách, và thất bại với cùng các response lỗi, trong khi `@UploadedFile()`, `@UploadedFiles()`, `ParseFilePipe`, `ParseFilePipeBuilder` và các file validator có sẵn hoạt động y như cũ.

Đầu tiên, cài plugin:

[[CODE:23]]

Không cần đăng ký nó: `FastifyAdapter` tự động đăng ký plugin ngay khi ứng dụng của bạn dùng một trong các upload interceptor (với ứng dụng không dùng, nó hoàn toàn không được đăng ký). Nếu package chưa được cài, ứng dụng sẽ lỗi lúc khởi động với thông báo nêu tên package.

Tiếp theo, import các interceptor từ `@nestjs/platform-fastify/multipart` thay vì `@nestjs/platform-express`. Phần còn lại của controller giữ nguyên, ngoại trừ việc file có type là `UploadedMultipartFile`:

[[CODE:24]]

> info **Hint** Mọi thứ được export từ `@nestjs/platform-fastify/multipart` cũng được re-export từ gốc package `@nestjs/platform-fastify`. Các interceptor chỉ hoạt động với `FastifyAdapter`: với `ExpressAdapter`, ứng dụng sẽ lỗi lúc khởi động, nên ở đó hãy tiếp tục import chúng từ `@nestjs/platform-express`.

Bảng dưới đây ánh xạ API của Express sang API tương ứng của Fastify:

| `@nestjs/platform-express`                                                                                            | `@nestjs/platform-fastify/multipart`                                                           |
| --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `FileInterceptor()`, `FilesInterceptor()`, `FileFieldsInterceptor()`, `AnyFilesInterceptor()`, `NoFilesInterceptor()` | Cùng tên, tham số và tùy chọn                                                                  |
| `MulterOptions`                                                                                                       | `MultipartOptions`                                                                             |
| `MulterModule`, `MulterOptionsFactory`, `createMulterOptions()`                                                       | `MultipartModule`, `MultipartOptionsFactory`, `createMultipartOptions()`                       |
| `Express.Multer.File`                                                                                                 | `UploadedMultipartFile`                                                                        |
| `memoryStorage()` và `diskStorage()` từ package `multer`                                                              | `memoryStorage()` và `diskStorage()`                                                           |
| -                                                                                                                     | `FileStreamInterceptor()` (xem [Stream upload](/http/file-upload#streaming-uploads))           |

Các tùy chọn của interceptor chính là những tùy chọn mà Multer nhận: `dest`, `storage`, `limits` (một object, hoặc một hàm nhận request và trả về object), `fileFilter`, `preservePath` và `defParamCharset`. File upload được cung cấp dưới dạng `req.file` hoặc `req.files`, còn các trường text dưới dạng `req.body`, y hệt như với Multer. `UploadedMultipartFile` có cùng cấu trúc với `Express.Multer.File`, nên bạn không cần package `@types/multer`.

`MultipartModule` đặt tùy chọn mặc định cho các upload interceptor của module import nó, giống hệt `MulterModule`. Method `registerAsync()` của nó nhận `useFactory` (cùng `imports` và `inject`), `useClass` và `useExisting`.

[[CODE:25]]

##### Storage

Giống như với Multer, file được giữ trong bộ nhớ (trong `file.buffer`) trừ khi bạn đặt tùy chọn `dest` hoặc `storage`. `dest` ghi mỗi file vào thư mục đã cho dưới một tên ngẫu nhiên, còn hàm `diskStorage()` cho phép bạn chọn thư mục và tên file. Disk storage đặt `destination`, `filename` và `path` trên file thay vì `buffer`.

[[CODE:26]]

Các storage engine tuân theo hợp đồng storage engine của Multer (`_handleFile()` và `_removeFile()`), nên chính `multer.diskStorage()` của Multer và các storage engine bên thứ ba của Multer có thể được truyền làm `storage` mà không cần thay đổi.

##### Giới hạn

`@fastify/multipart` áp dụng giá trị mặc định chặt hơn Multer. Trừ khi được cấu hình khác, kích thước file tối đa (`fileSize`) là `bodyLimit` của Fastify (mặc định 1 MiB) và số part tối đa (`parts`) là 1000, trong khi Multer không giới hạn cái nào. File lớn hơn sẽ bị từ chối với response `413 File too large`. Bạn có thể nâng các giới hạn này:

- cho một route, bằng tùy chọn `limits` của interceptor
- cho một module, bằng `MultipartModule.register()` hoặc `registerAsync()`
- cho toàn bộ ứng dụng, bằng tùy chọn `multipart` của `FastifyAdapter`, tùy chọn này truyền tùy chọn cho chính plugin:

[[CODE:27]]

Giới hạn đặt trên một route được merge đè lên giới hạn đặt bằng `MultipartModule` theo từng key, và cả hai được merge đè lên giới hạn cho toàn ứng dụng. Ngoại lệ duy nhất là `fieldNameSize`, thứ mà các interceptor không đọc từ tùy chọn plugin - hãy đặt nó trên route hoặc bằng `MultipartModule`.

##### Đăng ký plugin

Tùy chọn `multipart` của `FastifyAdapter` điều khiển cách plugin `@fastify/multipart` được đăng ký:

- không đặt (mặc định): adapter đăng ký plugin khi có một upload interceptor được dùng, trừ khi nó đã được đăng ký trước đó
- một options object (`FastifyMultipartOptions`, ví dụ `limits`): adapter đăng ký plugin với các tùy chọn này khi ứng dụng khởi tạo
- `true`: giống như trên, với tùy chọn mặc định của plugin
- `false`: adapter không bao giờ đăng ký plugin, dành cho ứng dụng tự đăng ký nó hoặc parse request multipart bằng library khác (các upload interceptor vẫn yêu cầu `@fastify/multipart`, và ứng dụng sẽ lỗi lúc khởi động nếu nó chưa được đăng ký)

Hãy đặt tùy chọn thành `true` (hoặc truyền một options object) khi một upload interceptor được khởi tạo bên ngoài hệ thống dependency injection, ví dụ `new (FileInterceptor('file'))()` truyền vào `app.useGlobalInterceptors()`, vì cách đó không kích hoạt việc đăng ký tự động. Điều tương tự áp dụng khi upload interceptor chỉ được dùng trong các [module lazy load](/fundamentals/lazy-loading-modules) được load sau khi ứng dụng đã khởi động, vì lúc đó không thể đăng ký plugin nữa.

Nếu bạn thích tự đăng ký plugin, hãy truyền nó vào `app.register()`, trước hoặc sau `app.init()`. Adapter sẽ tiếp quản lần đăng ký này, nên plugin chỉ được đăng ký một lần, và tùy chọn của bạn được ưu tiên hơn những tùy chọn truyền qua tùy chọn `multipart`:

[[CODE:28]]

> warning **Warning** Đăng ký `@fastify/multipart` trực tiếp trên Fastify instance (`app.getHttpAdapter().getInstance().register(multipart)`), hoặc truyền một `import()` động của nó vào `app.register()`, chỉ hoạt động trước `app.init()` (thứ mà `app.listen()` tự gọi giúp bạn). Sau đó, adapter đã đăng ký plugin cho các upload interceptor của bạn, và Fastify sẽ lỗi với `FST_ERR_DEC_ALREADY_PRESENT`. Hãy dùng `app.register(multipart)` hoặc tùy chọn `multipart` thay vào đó, hoặc đặt tùy chọn thành `false` để tự quản lý plugin.

##### Stream upload

Các interceptor mô tả từ đầu đến giờ đều lưu mọi file (trong bộ nhớ hoặc trên ổ đĩa) trước khi route handler chạy. Để xử lý file ngay khi dữ liệu đến, ví dụ để pipe một file upload lớn tới đích cuối cùng của nó, hãy dùng `FileStreamInterceptor()`, interceptor này chỉ có trên Fastify. Nó nhận tên của trường chứa file và một options object tùy chọn (giống như các interceptor khác, ngoại trừ `dest` và `storage`), và đưa cho route handler một file có thuộc tính `stream` thay cho `buffer`:

[[CODE:29]]

Vì file không bao giờ được buffer, có vài quy tắc được áp dụng:

- Các trường text phải đứng trước file trong form. Những trường gửi trước file có sẵn trong `req.body` (`@Body()`), còn các part đứng sau file sẽ không được parse.
- Chỉ một file được chấp nhận, trong trường đã cho. Một file ở bất kỳ trường nào khác sẽ làm request thất bại với response `400 Unexpected file field`.
- Kích thước file không biết trước, nên `MaxFileSizeValidator` không áp dụng được, và bước kiểm tra magic number của `FileTypeValidator` cũng vậy (đặt tùy chọn `skipMagicNumbersValidation` của nó thành `true` để chỉ so sánh mime type do client cung cấp). Giới hạn `fileSize` vẫn được áp dụng: khi vượt quá, stream sẽ báo lỗi với một `PayloadTooLargeException`.
- Bất cứ phần nào route handler chưa đọc sẽ bị bỏ đi trước khi response được gửi, để client có thể upload xong. Khi handler trả về một `StreamableFile` (có thể chính là file upload), phần còn lại của file upload sẽ bị bỏ đi sau khi response đã được gửi. Vì lý do này, một handler trả lời bằng `StreamableFile` của một thứ khác ngoài file upload nên đọc file upload trước - nếu không, một client vẫn đang upload qua một kết nối không keep-alive có thể gặp lỗi `EPIPE` hoặc `ECONNRESET`.

##### Khác biệt so với Multer

Ngoài [giới hạn mặc định](/http/file-upload#limits), các interceptor của Fastify khác với Multer ở những điểm sau:

- Một trường text có đúng `fieldSize` byte được chấp nhận, trong khi Multer từ chối nó.
- Các tên trường có thể gây ô nhiễm prototype (`constructor`, hoặc tên có segment `__proto__`, `constructor` hay `prototype`, như `user[constructor]`) sẽ làm request thất bại với response `400 Invalid field name`. Multer chấp nhận chúng.
- Các trường text gửi kèm header `Content-Type: application/json` sẽ đến ở dạng đã parse, và JSON không hợp lệ sẽ làm request thất bại với response `400` (một tính năng của `@fastify/multipart`). Các dòng header của part bị sai định dạng sẽ bị bỏ qua, trong khi Multer làm request thất bại với response `400`.
- Các hàm `fileFilter` và storage engine nhận request của Fastify thay vì của Express.
- Tùy chọn plugin `attachFieldsToBody` không được hỗ trợ, vì nó đọc hết request body trước khi các interceptor chạy.
- Các tùy chọn `highWaterMark`, `fileHwm`, `defCharset` và `streamHandler` của Multer không được các interceptor hỗ trợ.

#### Ví dụ

Một ví dụ chạy được về upload file có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/29-file-upload).

#### Stream file

Để gửi một file từ route handler, bạn có thể pipe một stream vào response object:

[[CODE:30]]

Với cách này, handler tự tiếp quản response, nên logic của [interceptor](/interceptors) sau controller sẽ không còn chạy. Thay vào đó, hãy trả về một instance `StreamableFile`, và Nest sẽ pipe nó vào response giúp bạn. Với nội dung không phải file, như các token của một LLM, xem [Stream response](/http/streaming-responses).

> info **Note** Stream file áp dụng cho **ứng dụng HTTP**. Các ví dụ dưới đây không áp dụng cho ứng dụng GraphQL hay microservice.

##### Class StreamableFile

Một `StreamableFile` chứa nội dung cần gửi. Constructor của nó nhận một stream `Readable` hoặc một `Uint8Array` (kể cả `Buffer`). Ví dụ sau trả về file `package.json` thay vì một response JSON. Cùng cách đó áp dụng được cho hình ảnh, tài liệu, và mọi loại file khác:

[[CODE:31]]

> info **Hint** Class `StreamableFile` được export từ package `@nestjs/common`.

Cả `ClassSerializerInterceptor` lẫn `StandardSchemaSerializerInterceptor` đều không [serialize](/application/serialization) các response `StreamableFile`.

##### Response header

Mặc định, header `Content-Type` của response là `application/octet-stream`. Để thay đổi nó, và để đặt các header `Content-Disposition` và `Content-Length`, hãy truyền các tùy chọn `type`, `disposition` và `length` vào constructor của `StreamableFile`:

[[CODE:32]]

Khi nội dung là một `Uint8Array`, `length` mặc định bằng kích thước của nó. Với stream, hãy tự đặt `length` nếu bạn biết trước kích thước.

Các header có giá trị cố định cũng có thể được đặt bằng decorator [`@Header()`](/controllers#response-headers):

[[CODE:33]]

Để tính toán header lúc runtime, hãy inject response object với `passthrough` được bật, để Nest vẫn gửi `StreamableFile` được trả về:

[[CODE:34]]

##### Lỗi của stream

Với Express adapter, nếu stream phát ra lỗi trước khi có dữ liệu nào được gửi, client sẽ nhận response `400 Bad Request`, và lỗi được log. Kể từ NestJS v12.2, body của response không còn chứa message lỗi, vốn có thể chứa đường dẫn của file. Nếu dữ liệu đã được gửi, response sẽ được kết thúc. Để tùy biến hành vi này, hãy truyền một handler vào method `setErrorHandler()`:

[[CODE:35]]

Method `setErrorLogger()` thay thế hàm log lỗi: những lỗi mà error handler mặc định trả lời, và những lỗi mà response stream phát ra trong lúc file đang được ghi vào nó.

> info **Note** Error handler và error logger áp dụng cho Express adapter và Node adapter. Với Fastify adapter, lỗi của stream được [lớp xử lý exception](/exception-filters) xử lý, nên mặc định client nhận response `500 Internal Server Error`.

##### Hỗ trợ đa nền tảng

Fastify có thể gửi stream mà không cần `stream.pipe(res)`, nên với Fastify, class `StreamableFile` không thực sự bắt buộc. Tuy nhiên, Nest hỗ trợ `StreamableFile` trên cả hai nền tảng, nên code trả về nó vẫn chạy y như cũ khi bạn chuyển đổi giữa Express và Fastify.
