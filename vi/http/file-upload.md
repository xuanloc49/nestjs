### Upload và stream file

Chương này trình bày việc xử lý file theo cả hai chiều: nhận file mà client upload lên, và [stream file](#streaming-files) ngược về cho client.

Để xử lý upload file, Nest cung cấp sẵn một module dựa trên package middleware [multer](https://github.com/expressjs/multer) của Express. Multer xử lý dữ liệu gửi lên theo định dạng `multipart/form-data`, định dạng chủ yếu được dùng để upload file bằng một request HTTP `POST`. Module này có thể cấu hình hoàn toàn, nên bạn có thể điều chỉnh hành vi của nó theo yêu cầu của ứng dụng.

> warning **Cảnh báo** Multer không thể xử lý dữ liệu không ở định dạng `multipart/form-data`.

> info **Gợi ý** Nếu ứng dụng của bạn chạy trên `FastifyAdapter`, cùng các interceptor đó có sẵn từ package `@nestjs/platform-fastify`, dựa trên [@fastify/multipart](https://github.com/fastify/fastify-multipart) thay vì Multer, và các decorator cùng pipe mô tả trong chương này hoạt động y như cũ. Chỉ có đường dẫn import là thay đổi - xem phần [Fastify](/http/file-upload#fastify) bên dưới.

> info **Gợi ý** Nếu ứng dụng của bạn chạy trên `NodeAdapter`, hãy import các interceptor và `MulterModule` từ `@nestjs/platform-node` thay vì `@nestjs/platform-express`. Chúng chính là các interceptor dựa trên Multer, nên mọi thứ trong chương này đều áp dụng y như cũ.

Để có type safety, hãy cài các định nghĩa type của Multer:

```shell
$ npm i -D @types/multer
```

Khi đã cài package này, bạn có thể dùng type `Express.Multer.File` (import namespace `Express` bằng `import {{ '{' }} Express {{ '}' }} from 'express'`).

#### Ví dụ cơ bản <a id="basic-example"></a>

Để upload một file, hãy bind interceptor `FileInterceptor()` vào route handler và lấy file từ request bằng decorator `@UploadedFile()`.

```typescript
@@filename()
@Post('upload')
@UseInterceptors(FileInterceptor('file'))
uploadFile(@UploadedFile() file: Express.Multer.File) {
  console.log(file);
}
@@switch
@Post('upload')
@UseInterceptors(FileInterceptor('file'))
@Bind(UploadedFile())
uploadFile(file) {
  console.log(file);
}
```

> info **Gợi ý** Decorator `FileInterceptor()` được export từ package `@nestjs/platform-express`. Decorator `@UploadedFile()` được export từ `@nestjs/common`.

Decorator `FileInterceptor()` nhận hai tham số:

- `fieldName`: tên của trường trong form HTML chứa file
- `options`: một object tùy chọn có type `MulterOptions`. Đây chính là object mà constructor của Multer nhận (xem [các tùy chọn của Multer](https://github.com/expressjs/multer#multeropts)).

> warning **Cảnh báo** `FileInterceptor()` có thể không tương thích với các cloud provider bên thứ ba như Google Firebase hay các dịch vụ khác.

#### Validate file <a id="file-validation"></a>

Thường thì bạn sẽ muốn validate metadata của file gửi đến, như kích thước file hoặc MIME type. Để làm vậy, hãy tạo một [pipe](/pipes) và bind nó vào tham số được decorate bằng `@UploadedFile()`. Ví dụ sau implement một pipe validate kích thước file cơ bản:

```typescript
import { PipeTransform, Injectable, ArgumentMetadata } from '@nestjs/common';

@Injectable()
export class FileSizeValidationPipe implements PipeTransform {
  transform(value: any, metadata: ArgumentMetadata) {
    // "value" is an object containing the file's attributes and metadata
    const oneKb = 1000;
    return value.size < oneKb;
  }
}
```

Dùng nó cùng với `FileInterceptor` như sau:

```typescript
@Post('file')
@UseInterceptors(FileInterceptor('file'))
uploadFileAndValidate(@UploadedFile(
  new FileSizeValidationPipe(),
  // other pipes can be added here
) file: Express.Multer.File, ) {
  return file;
}
```

Với các trường hợp phổ biến, Nest cung cấp sẵn một pipe là `ParseFilePipe`, pipe này cũng chuẩn hóa cách thêm các bước validate file mới:

```typescript
@Post('file')
uploadFileAndPassValidation(
  @Body() body: SampleDto,
  @UploadedFile(
    new ParseFilePipe({
      validators: [
        // ... Set of file validator instances here
      ]
    })
  )
  file: Express.Multer.File,
) {
  return {
    body,
    file: file.buffer.toString(),
  };
}
```

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

```typescript
export abstract class FileValidator<TValidationOptions = Record<string, any>> {
  constructor(protected readonly validationOptions: TValidationOptions) {}

  /**
   * Indicates if this file should be considered valid, according to the options passed in the constructor.
   * @param file the file from the request object
   */
  abstract isValid(file?: any): boolean | Promise<boolean>;

  /**
   * Builds an error message in case the validation fails.
   * @param file the file from the request object
   */
  abstract buildErrorMessage(file: any): string;
}
```

> info **Gợi ý** Method `isValid()` có thể là bất đồng bộ. Để có type safety, hãy khai báo type của tham số `file` là `Express.Multer.File` khi bạn dùng Express (HTTP adapter mặc định).

Một `FileValidator` nhận file object và validate nó theo các tùy chọn truyền vào constructor của nó. Nest cung cấp sẵn hai bản implement:

- `MaxFileSizeValidator` kiểm tra kích thước file có nhỏ hơn giá trị cung cấp hay không, tính bằng byte.
- `FileTypeValidator` kiểm tra MIME type của file có khớp với chuỗi hoặc biểu thức chính quy đã cho hay không. Mặc định, nó xác định MIME type dựa trên [magic number](https://www.ibm.com/support/pages/what-magic-number) trong nội dung file.

Đoạn code sau dùng cả hai validator với `ParseFilePipe`:

```typescript
@UploadedFile(
  new ParseFilePipe({
    validators: [
      new MaxFileSizeValidator({ maxSize: 1000 }),
      new FileTypeValidator({ fileType: 'image/jpeg' }),
    ],
  }),
)
file: Express.Multer.File,
```

> info **Gợi ý** Nếu danh sách validator dài ra, hãy định nghĩa mảng trong một file riêng và import nó dưới dạng một hằng có tên, như `fileValidators`.

Cách khác là kết hợp các validator bằng class `ParseFilePipeBuilder`. Builder tự khởi tạo từng validator giúp bạn, nên bạn chỉ cần truyền tùy chọn của chúng:

```typescript
@UploadedFile(
  new ParseFilePipeBuilder()
    .addFileTypeValidator({
      fileType: 'jpeg',
    })
    .addMaxSizeValidator({
      maxSize: 1000
    })
    .build({
      errorHttpStatusCode: HttpStatus.UNPROCESSABLE_ENTITY
    }),
)
file: Express.Multer.File,
```

> info **Gợi ý** Mặc định file là bắt buộc. Để biến nó thành tùy chọn, hãy truyền `fileIsRequired: false` trong tùy chọn của method `build()` (cạnh `errorHttpStatusCode`).

#### Mảng file <a id="array-of-files"></a>

Để upload một mảng file xác định bởi một tên trường duy nhất, hãy dùng decorator `FilesInterceptor()` (để ý chữ **Files** số nhiều trong tên). Nó nhận ba tham số:

- `fieldName`: như mô tả ở trên
- `maxCount`: số file tối đa được chấp nhận (tùy chọn)
- `options`: một object `MulterOptions` tùy chọn, như mô tả ở trên

Khi dùng `FilesInterceptor()`, hãy lấy file từ `request` bằng decorator `@UploadedFiles()`.

```typescript
@@filename()
@Post('upload')
@UseInterceptors(FilesInterceptor('files'))
uploadFile(@UploadedFiles() files: Array<Express.Multer.File>) {
  console.log(files);
}
@@switch
@Post('upload')
@UseInterceptors(FilesInterceptor('files'))
@Bind(UploadedFiles())
uploadFile(files) {
  console.log(files);
}
```

> info **Gợi ý** Decorator `FilesInterceptor()` được export từ package `@nestjs/platform-express`. Decorator `@UploadedFiles()` được export từ `@nestjs/common`.

#### Validate mảng file <a id="validating-an-array-of-files"></a>

Để validate một mảng file đã upload, hãy truyền một pipe tạo bằng `ParseFilePipeBuilder` vào decorator `@UploadedFiles()`. Các validator đã đăng ký sẽ chạy với từng file trong mảng.

```typescript
@@filename()
@Post('upload')
@UseInterceptors(FilesInterceptor('files', 5))
uploadFiles(
  @UploadedFiles(
    new ParseFilePipeBuilder()
      .addFileTypeValidator({
        fileType: /^image\/(jpeg|png|gif)$/,
      })
      .addMaxSizeValidator({ maxSize: 5242880 })
      .build({
        errorHttpStatusCode: HttpStatus.UNPROCESSABLE_ENTITY,
      }),
  )
  files: Array<Express.Multer.File>,
) {
  console.log(files);
}
```

#### Nhiều file <a id="multiple-files"></a>

Để upload nhiều file dưới các tên trường khác nhau, hãy dùng decorator `FileFieldsInterceptor()`. Nó nhận hai tham số:

- `uploadedFields`: một mảng object, mỗi object có thuộc tính `name` bắt buộc (tên trường) và thuộc tính `maxCount` tùy chọn
- `options`: một object `MulterOptions` tùy chọn, như mô tả ở trên

Khi dùng `FileFieldsInterceptor()`, hãy lấy file từ `request` bằng decorator `@UploadedFiles()`.

```typescript
@@filename()
@Post('upload')
@UseInterceptors(FileFieldsInterceptor([
  { name: 'avatar', maxCount: 1 },
  { name: 'background', maxCount: 1 },
]))
uploadFile(@UploadedFiles() files: { avatar?: Express.Multer.File[], background?: Express.Multer.File[] }) {
  console.log(files);
}
@@switch
@Post('upload')
@Bind(UploadedFiles())
@UseInterceptors(FileFieldsInterceptor([
  { name: 'avatar', maxCount: 1 },
  { name: 'background', maxCount: 1 },
]))
uploadFile(files) {
  console.log(files);
}
```

#### File bất kỳ <a id="any-files"></a>

Để chấp nhận file dưới bất kỳ tên trường nào, hãy dùng decorator `AnyFilesInterceptor()`. Nó nhận một object `options` tùy chọn, như mô tả ở trên.

Khi dùng `AnyFilesInterceptor()`, hãy lấy file từ `request` bằng decorator `@UploadedFiles()`.

```typescript
@@filename()
@Post('upload')
@UseInterceptors(AnyFilesInterceptor())
uploadFile(@UploadedFiles() files: Array<Express.Multer.File>) {
  console.log(files);
}
@@switch
@Post('upload')
@Bind(UploadedFiles())
@UseInterceptors(AnyFilesInterceptor())
uploadFile(files) {
  console.log(files);
}
```

#### Không có file <a id="no-files"></a>

Để chấp nhận `multipart/form-data` mà không cho phép upload file, hãy dùng `NoFilesInterceptor`. Nó đặt các trường multipart làm thuộc tính của request body. Một request có chứa file sẽ bị từ chối với `BadRequestException`.

```typescript
@Post('upload')
@UseInterceptors(NoFilesInterceptor())
handleMultiPartData(@Body() body) {
  console.log(body)
}
```

#### Tùy chọn mặc định <a id="default-options"></a>

Bạn có thể truyền tùy chọn Multer cho từng file interceptor, như mô tả ở trên. Để đặt tùy chọn mặc định thay vào đó, hãy gọi method static `register()` khi import `MulterModule`. Nó nhận mọi [tùy chọn của Multer](https://github.com/expressjs/multer#multeropts).

```typescript
MulterModule.register({
  dest: './upload',
});
```

> info **Gợi ý** Class `MulterModule` được export từ package `@nestjs/platform-express`.

Tùy chọn truyền vào một file interceptor sẽ được ưu tiên hơn các giá trị mặc định này. Kể từ NestJS v12.0.4, hai object `limits` được merge theo từng key, nên một route chỉ đặt `limits.fileSize` vẫn giữ một giá trị mặc định như `limits.files`. Nếu một trong hai là hàm, `limits` của interceptor sẽ thay thế hoàn toàn giá trị mặc định.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Để đặt tùy chọn cho `MulterModule` theo kiểu bất đồng bộ thay vì tĩnh, hãy dùng method `registerAsync()`. Giống như hầu hết dynamic module, nó hỗ trợ vài kỹ thuật cho cấu hình bất đồng bộ.

Một kỹ thuật là dùng hàm factory:

```typescript
MulterModule.registerAsync({
  useFactory: () => ({
    dest: './upload',
  }),
});
```

Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, hàm factory có thể là `async` và có thể inject dependency qua `inject`.

```typescript
MulterModule.registerAsync({
  imports: [ConfigModule],
  useFactory: async (configService: ConfigService) => ({
    dest: configService.get<string>('MULTER_DEST'),
  }),
  inject: [ConfigService],
});
```

Cách khác là cấu hình `MulterModule` bằng một class thay vì factory, như bên dưới:

```typescript
MulterModule.registerAsync({
  useClass: MulterConfigService,
});
```

Cách khai báo trên khởi tạo `MulterConfigService` bên trong `MulterModule` và gọi method `createMulterOptions()` của nó để lấy options object. Để cách này hoạt động, `MulterConfigService` phải implement interface `MulterOptionsFactory`:

```typescript
@Injectable()
class MulterConfigService implements MulterOptionsFactory {
  createMulterOptions(): MulterModuleOptions {
    return {
      dest: './upload',
    };
  }
}
```

Nếu bạn muốn dùng lại một options provider đã có thay vì tạo một bản sao riêng bên trong `MulterModule`, hãy dùng cú pháp `useExisting`.

```typescript
MulterModule.registerAsync({
  imports: [ConfigModule],
  useExisting: ConfigService,
});
```

Bạn cũng có thể truyền `extraProviders` vào method `registerAsync()`. Các provider này được merge với các provider của module.

```typescript
MulterModule.registerAsync({
  imports: [ConfigModule],
  useClass: ConfigService,
  extraProviders: [MyAdditionalProvider],
});
```

Điều này hữu ích khi hàm factory hoặc constructor của class cần thêm dependency.

#### Sử dụng bộ nhớ và storage <a id="memory-usage-and-storage"></a>

Mặc định, Multer dùng storage engine trong bộ nhớ (`memoryStorage()`): mọi file upload đều được đọc hoàn toàn vào bộ nhớ và cung cấp dưới dạng một `Buffer` trên `file.buffer` trước khi route handler chạy. Cách này tiện cho các file nhỏ (avatar hay file CSV để import), nhưng mỗi lần upload đang diễn ra chiếm lượng bộ nhớ bằng đúng kích thước của nó, nên file lớn hoặc nhiều lần upload đồng thời có thể nhanh chóng làm cạn bộ nhớ của process.

> warning **Cảnh báo** Mặc định, Multer không giới hạn kích thước file upload. Khi giữ file trong bộ nhớ, hãy luôn đặt `limits.fileSize`.

##### Giới hạn kích thước file <a id="file-size-limit"></a>

Dùng tùy chọn `limits` để từ chối các file quá lớn. Khi vượt quá một giới hạn, Nest trả lời bằng lỗi `413 File too large` (với `fileSize`) hoặc `400 Bad Request` (với các giới hạn khác, như `files`) và route handler không được gọi.

```typescript
@Post('upload')
@UseInterceptors(
  FileInterceptor('file', {
    limits: { fileSize: 5 * 1024 * 1024 }, // 5 MB
  }),
)
uploadFile(@UploadedFile() file: Express.Multer.File) {
  console.log(file.size);
}
```

> info **Gợi ý** Khác với `MaxFileSizeValidator`, vốn chạy sau khi đã nhận toàn bộ file, `limits.fileSize` khiến Multer ngừng lưu file và từ chối request ngay khi chạm tới giới hạn, nên các file quá cỡ không bao giờ được đưa trọn vẹn vào bộ nhớ hay ổ đĩa. Xem [các giới hạn của Multer](https://github.com/expressjs/multer#limits) để có danh sách tùy chọn đầy đủ.

##### Giới hạn tên trường <a id="field-name-limits"></a>

Các tên trường như `user[address][city]` hoặc `tags[2]` tạo ra object và mảng lồng nhau trong request body. Có hai giới hạn kiểm soát chúng: `fieldNestingDepth`, số cấp lồng nhau (`a[b][c]` có 2 cấp), và `fieldArrayIndexLimit`, chỉ số mảng cao nhất (`tags[2]` dùng chỉ số 2). Một request vượt quá một trong hai sẽ bị từ chối với response `400 Bad Request`. Kể từ NestJS v12.2, chúng có giá trị mặc định lần lượt là 32 và 1000 (Multer để chúng không giới hạn), để một request duy nhất không thể tạo ra một body lồng sâu tùy ý hay một mảng khổng lồ. Đặt một giới hạn thành `Infinity` để bỏ nó.

##### Lưu trên ổ đĩa <a id="disk-storage"></a>

Để giữ mức sử dụng bộ nhớ ổn định bất kể kích thước file, hãy ghi file upload ra ổ đĩa bằng engine `diskStorage()`. Khi đó Multer stream mỗi file xuống ổ đĩa ngay khi dữ liệu đến, và file object cung cấp `destination`, `filename` và `path` thay vì `buffer`.

```typescript
import { extname } from 'node:path';
import { randomUUID } from 'node:crypto';
import { diskStorage } from 'multer';

@Post('upload')
@UseInterceptors(
  FileInterceptor('file', {
    storage: diskStorage({
      destination: './uploads',
      filename: (req, file, cb) => {
        cb(null, `${randomUUID()}${extname(file.originalname)}`);
      },
    }),
    limits: { fileSize: 1024 * 1024 * 1024 }, // 1 GB
  }),
)
uploadFile(@UploadedFile() file: Express.Multer.File) {
  console.log(file.path);
}
```

> info **Gợi ý** Các hàm `diskStorage()` và `memoryStorage()` được export từ package `multer`. Để viết tắt, hãy truyền `dest: './uploads'` để lưu file trên ổ đĩa dưới tên ngẫu nhiên. Nếu bạn truyền một hàm `destination` thay vì một chuỗi, bạn phải tự tạo thư mục.

Để áp dụng cùng storage và giới hạn cho mọi file interceptor trong một module, hãy đặt chúng làm [tùy chọn mặc định](/http/file-upload#default-options) hoặc bằng [cấu hình bất đồng bộ](/http/file-upload#async-configuration).

File lưu trên ổ đĩa không tự động bị xóa sau khi route handler đã chạy. Hãy xóa chúng (ví dụ bằng `unlink()` từ `fs/promises`) sau khi đã xử lý xong, kể cả khi xử lý thất bại. Kể từ NestJS v12.2, nếu một pipe từ chối request (ví dụ vì validation của `ParseFilePipe` thất bại), route handler không chạy, và các file đã lưu sẽ bị xóa sau khi response lỗi đã được gửi đi.

##### Gửi file lên storage bên ngoài <a id="sending-files-to-external-storage"></a>

Để lưu file upload lên S3, Cloudflare R2 hoặc một store bên ngoài khác mà không buffer chúng trong bộ nhớ hay ghi ra file tạm, hãy dùng một storage engine stream từng file tới đích ngay khi dữ liệu đến. Package [`@nestjs/storage`](/application/file-storage) cung cấp một engine như vậy, `uploadToDisk()`, bạn truyền nó làm tùy chọn `storage` của `FileInterceptor()`. Xem [Upload ảnh sản phẩm](/application/file-storage#upload-product-photos). Mọi [storage engine](https://github.com/expressjs/multer/blob/main/StorageEngine.md) khác của Multer cũng hoạt động theo cùng cách.

> info **Gợi ý** Trên `FastifyAdapter`, bạn cũng có thể nhận file dưới dạng stream ngay bên trong route handler bằng `FileStreamInterceptor()`. Xem [Stream upload](/http/file-upload#streaming-uploads).
#### Fastify

Kể từ NestJS v12.1, các ứng dụng chạy trên `FastifyAdapter` (xem [Fastify adapter](/http/performance#fastify-adapter)) có thể xử lý upload file bằng cùng API, dựa trên plugin [@fastify/multipart](https://github.com/fastify/fastify-multipart) thay vì Multer. Các interceptor mô tả trong chương này nhận cùng tham số và tùy chọn, điền request theo cùng cách, và thất bại với cùng các response lỗi, trong khi `@UploadedFile()`, `@UploadedFiles()`, `ParseFilePipe`, `ParseFilePipeBuilder` và các file validator có sẵn hoạt động y như cũ.

Đầu tiên, cài plugin:

```bash
$ npm i @fastify/multipart
```

Không cần đăng ký nó: `FastifyAdapter` tự động đăng ký plugin ngay khi ứng dụng của bạn dùng một trong các upload interceptor (với ứng dụng không dùng, nó hoàn toàn không được đăng ký). Nếu package chưa được cài, ứng dụng sẽ lỗi lúc khởi động với thông báo nêu tên package.

Tiếp theo, import các interceptor từ `@nestjs/platform-fastify/multipart` thay vì `@nestjs/platform-express`. Phần còn lại của controller giữ nguyên, ngoại trừ việc file có type là `UploadedMultipartFile`:

```typescript
import {
  Controller,
  FileTypeValidator,
  MaxFileSizeValidator,
  ParseFilePipe,
  Post,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import {
  FileInterceptor,
  type UploadedMultipartFile,
} from '@nestjs/platform-fastify/multipart';

@Controller('files')
export class FilesController {
  @Post('upload')
  @UseInterceptors(FileInterceptor('file'))
  uploadFile(
    @UploadedFile(
      new ParseFilePipe({
        validators: [
          new MaxFileSizeValidator({ maxSize: 1000 }),
          new FileTypeValidator({ fileType: 'image/png' }),
        ],
      }),
    )
    file: UploadedMultipartFile,
  ) {
    console.log(file);
  }
}
```

> info **Gợi ý** Mọi thứ được export từ `@nestjs/platform-fastify/multipart` cũng được re-export từ gốc package `@nestjs/platform-fastify`. Các interceptor chỉ hoạt động với `FastifyAdapter`: với `ExpressAdapter`, ứng dụng sẽ lỗi lúc khởi động, nên ở đó hãy tiếp tục import chúng từ `@nestjs/platform-express`.

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

```typescript
MultipartModule.register({
  dest: './upload',
});
```

##### Storage

Giống như với Multer, file được giữ trong bộ nhớ (trong `file.buffer`) trừ khi bạn đặt tùy chọn `dest` hoặc `storage`. `dest` ghi mỗi file vào thư mục đã cho dưới một tên ngẫu nhiên, còn hàm `diskStorage()` cho phép bạn chọn thư mục và tên file. Disk storage đặt `destination`, `filename` và `path` trên file thay vì `buffer`.

```typescript
import {
  diskStorage,
  FileInterceptor,
  type UploadedMultipartFile,
} from '@nestjs/platform-fastify/multipart';

@Post('upload')
@UseInterceptors(
  FileInterceptor('file', {
    storage: diskStorage({
      destination: './uploads',
      filename: (req, file, callback) =>
        callback(null, `${Date.now()}-${file.originalname}`),
    }),
  }),
)
uploadFile(@UploadedFile() file: UploadedMultipartFile) {
  console.log(file.path);
}
```

Các storage engine tuân theo hợp đồng storage engine của Multer (`_handleFile()` và `_removeFile()`), nên chính `multer.diskStorage()` của Multer và các storage engine bên thứ ba của Multer có thể được truyền làm `storage` mà không cần thay đổi.

##### Giới hạn <a id="limits"></a>

`@fastify/multipart` áp dụng giá trị mặc định chặt hơn Multer. Trừ khi được cấu hình khác, kích thước file tối đa (`fileSize`) là `bodyLimit` của Fastify (mặc định 1 MiB) và số part tối đa (`parts`) là 1000, trong khi Multer không giới hạn cái nào. File lớn hơn sẽ bị từ chối với response `413 File too large`. Bạn có thể nâng các giới hạn này:

- cho một route, bằng tùy chọn `limits` của interceptor
- cho một module, bằng `MultipartModule.register()` hoặc `registerAsync()`
- cho toàn bộ ứng dụng, bằng tùy chọn `multipart` của `FastifyAdapter`, tùy chọn này truyền tùy chọn cho chính plugin:

```typescript
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter({
    multipart: { limits: { fileSize: 10 * 1024 * 1024 } },
  }),
);
```

Giới hạn đặt trên một route được merge đè lên giới hạn đặt bằng `MultipartModule` theo từng key, và cả hai được merge đè lên giới hạn cho toàn ứng dụng. Ngoại lệ duy nhất là `fieldNameSize`, thứ mà các interceptor không đọc từ tùy chọn plugin - hãy đặt nó trên route hoặc bằng `MultipartModule`.

##### Đăng ký plugin <a id="plugin-registration"></a>

Tùy chọn `multipart` của `FastifyAdapter` điều khiển cách plugin `@fastify/multipart` được đăng ký:

- không đặt (mặc định): adapter đăng ký plugin khi có một upload interceptor được dùng, trừ khi nó đã được đăng ký trước đó
- một options object (`FastifyMultipartOptions`, ví dụ `limits`): adapter đăng ký plugin với các tùy chọn này khi ứng dụng khởi tạo
- `true`: giống như trên, với tùy chọn mặc định của plugin
- `false`: adapter không bao giờ đăng ký plugin, dành cho ứng dụng tự đăng ký nó hoặc parse request multipart bằng library khác (các upload interceptor vẫn yêu cầu `@fastify/multipart`, và ứng dụng sẽ lỗi lúc khởi động nếu nó chưa được đăng ký)

Hãy đặt tùy chọn thành `true` (hoặc truyền một options object) khi một upload interceptor được khởi tạo bên ngoài hệ thống dependency injection, ví dụ `new (FileInterceptor('file'))()` truyền vào `app.useGlobalInterceptors()`, vì cách đó không kích hoạt việc đăng ký tự động. Điều tương tự áp dụng khi upload interceptor chỉ được dùng trong các [module lazy load](/fundamentals/lazy-loading-modules) được load sau khi ứng dụng đã khởi động, vì lúc đó không thể đăng ký plugin nữa.

Nếu bạn thích tự đăng ký plugin, hãy truyền nó vào `app.register()`, trước hoặc sau `app.init()`. Adapter sẽ tiếp quản lần đăng ký này, nên plugin chỉ được đăng ký một lần, và tùy chọn của bạn được ưu tiên hơn những tùy chọn truyền qua tùy chọn `multipart`:

```typescript
import multipart from '@fastify/multipart';

const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter(),
);
await app.register(multipart, { limits: { fileSize: 10 * 1024 * 1024 } });
```

> warning **Cảnh báo** Đăng ký `@fastify/multipart` trực tiếp trên Fastify instance (`app.getHttpAdapter().getInstance().register(multipart)`), hoặc truyền một `import()` động của nó vào `app.register()`, chỉ hoạt động trước `app.init()` (thứ mà `app.listen()` tự gọi giúp bạn). Sau đó, adapter đã đăng ký plugin cho các upload interceptor của bạn, và Fastify sẽ lỗi với `FST_ERR_DEC_ALREADY_PRESENT`. Hãy dùng `app.register(multipart)` hoặc tùy chọn `multipart` thay vào đó, hoặc đặt tùy chọn thành `false` để tự quản lý plugin.

##### Stream upload <a id="streaming-uploads"></a>

Các interceptor mô tả từ đầu đến giờ đều lưu mọi file (trong bộ nhớ hoặc trên ổ đĩa) trước khi route handler chạy. Để xử lý file ngay khi dữ liệu đến, ví dụ để pipe một file upload lớn tới đích cuối cùng của nó, hãy dùng `FileStreamInterceptor()`, interceptor này chỉ có trên Fastify. Nó nhận tên của trường chứa file và một options object tùy chọn (giống như các interceptor khác, ngoại trừ `dest` và `storage`), và đưa cho route handler một file có thuộc tính `stream` thay cho `buffer`:

```typescript
import { randomUUID } from 'node:crypto';
import { createWriteStream } from 'node:fs';
import { join } from 'node:path';
import { pipeline } from 'node:stream/promises';
import {
  FileStreamInterceptor,
  MultipartFileStream,
} from '@nestjs/platform-fastify/multipart';

@Post('upload')
@UseInterceptors(
  FileStreamInterceptor('file', { limits: { fileSize: 1024 * 1024 * 1024 } }),
)
async uploadFile(@UploadedFile() file: MultipartFileStream, @Body() body) {
  const path = join('uploads', randomUUID());
  await pipeline(file.stream, createWriteStream(path));
  return { originalname: file.originalname, path, body };
}
```

Vì file không bao giờ được buffer, có vài quy tắc được áp dụng:

- Các trường text phải đứng trước file trong form. Những trường gửi trước file có sẵn trong `req.body` (`@Body()`), còn các part đứng sau file sẽ không được parse.
- Chỉ một file được chấp nhận, trong trường đã cho. Một file ở bất kỳ trường nào khác sẽ làm request thất bại với response `400 Unexpected file field`.
- Kích thước file không biết trước, nên `MaxFileSizeValidator` không áp dụng được, và bước kiểm tra magic number của `FileTypeValidator` cũng vậy (đặt tùy chọn `skipMagicNumbersValidation` của nó thành `true` để chỉ so sánh mime type do client cung cấp). Giới hạn `fileSize` vẫn được áp dụng: khi vượt quá, stream sẽ báo lỗi với một `PayloadTooLargeException`.
- Bất cứ phần nào route handler chưa đọc sẽ bị bỏ đi trước khi response được gửi, để client có thể upload xong. Khi handler trả về một `StreamableFile` (có thể chính là file upload), phần còn lại của file upload sẽ bị bỏ đi sau khi response đã được gửi. Vì lý do này, một handler trả lời bằng `StreamableFile` của một thứ khác ngoài file upload nên đọc file upload trước - nếu không, một client vẫn đang upload qua một kết nối không keep-alive có thể gặp lỗi `EPIPE` hoặc `ECONNRESET`.

##### Khác biệt so với Multer <a id="differences-from-multer"></a>

Ngoài [giới hạn mặc định](/http/file-upload#limits), các interceptor của Fastify khác với Multer ở những điểm sau:

- Một trường text có đúng `fieldSize` byte được chấp nhận, trong khi Multer từ chối nó.
- Các tên trường có thể gây ô nhiễm prototype (`constructor`, hoặc tên có segment `__proto__`, `constructor` hay `prototype`, như `user[constructor]`) sẽ làm request thất bại với response `400 Invalid field name`. Multer chấp nhận chúng.
- Các trường text gửi kèm header `Content-Type: application/json` sẽ đến ở dạng đã parse, và JSON không hợp lệ sẽ làm request thất bại với response `400` (một tính năng của `@fastify/multipart`). Các dòng header của part bị sai định dạng sẽ bị bỏ qua, trong khi Multer làm request thất bại với response `400`.
- Các hàm `fileFilter` và storage engine nhận request của Fastify thay vì của Express.
- Tùy chọn plugin `attachFieldsToBody` không được hỗ trợ, vì nó đọc hết request body trước khi các interceptor chạy.
- Các tùy chọn `highWaterMark`, `fileHwm`, `defCharset` và `streamHandler` của Multer không được các interceptor hỗ trợ.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được về upload file có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/29-file-upload).

#### Stream file <a id="streaming-files"></a>

Để gửi một file từ route handler, bạn có thể pipe một stream vào response object:

```typescript
@Controller('file')
export class FileController {
  @Get()
  getFile(@Res() res: Response) {
    const file = createReadStream(join(process.cwd(), 'package.json'));
    file.pipe(res);
  }
}
```

Với cách này, handler tự tiếp quản response, nên logic của [interceptor](/interceptors) sau controller sẽ không còn chạy. Thay vào đó, hãy trả về một instance `StreamableFile`, và Nest sẽ pipe nó vào response giúp bạn. Với nội dung không phải file, như các token của một LLM, xem [Stream response](/http/streaming-responses).

> info **Lưu ý** Stream file áp dụng cho **ứng dụng HTTP**. Các ví dụ dưới đây không áp dụng cho ứng dụng GraphQL hay microservice.

##### Class StreamableFile <a id="streamable-file-class"></a>

Một `StreamableFile` chứa nội dung cần gửi. Constructor của nó nhận một stream `Readable` hoặc một `Uint8Array` (kể cả `Buffer`). Ví dụ sau trả về file `package.json` thay vì một response JSON. Cùng cách đó áp dụng được cho hình ảnh, tài liệu, và mọi loại file khác:

```typescript
import { Controller, Get, StreamableFile } from '@nestjs/common';
import { createReadStream } from 'node:fs';
import { join } from 'node:path';

@Controller('file')
export class FileController {
  @Get()
  getFile(): StreamableFile {
    const file = createReadStream(join(process.cwd(), 'package.json'));
    return new StreamableFile(file);
  }
}
```

> info **Gợi ý** Class `StreamableFile` được export từ package `@nestjs/common`.

Cả `ClassSerializerInterceptor` lẫn `StandardSchemaSerializerInterceptor` đều không [serialize](/application/serialization) các response `StreamableFile`.

##### Response header <a id="response-headers"></a>

Mặc định, header `Content-Type` của response là `application/octet-stream`. Để thay đổi nó, và để đặt các header `Content-Disposition` và `Content-Length`, hãy truyền các tùy chọn `type`, `disposition` và `length` vào constructor của `StreamableFile`:

```typescript
@Get()
getFile(): StreamableFile {
  const file = createReadStream(join(process.cwd(), 'package.json'));
  return new StreamableFile(file, {
    type: 'application/json',
    disposition: 'attachment; filename="package.json"',
  });
}
```

Khi nội dung là một `Uint8Array`, `length` mặc định bằng kích thước của nó. Với stream, hãy tự đặt `length` nếu bạn biết trước kích thước.

Các header có giá trị cố định cũng có thể được đặt bằng decorator [`@Header()`](/controllers#response-headers):

```typescript
@Get()
@Header('Content-Type', 'application/json')
@Header('Content-Disposition', 'attachment; filename="package.json"')
getFile(): StreamableFile {
  const file = createReadStream(join(process.cwd(), 'package.json'));
  return new StreamableFile(file);
}
```

Để tính toán header lúc runtime, hãy inject response object với `passthrough` được bật, để Nest vẫn gửi `StreamableFile` được trả về:

```typescript
import type { Response } from 'express';

@Get()
getFile(@Res({ passthrough: true }) res: Response): StreamableFile {
  const file = createReadStream(join(process.cwd(), 'package.json'));
  res.set({
    'Content-Type': 'application/json',
    'Content-Disposition': 'attachment; filename="package.json"',
  });
  return new StreamableFile(file);
}
```

##### Lỗi của stream <a id="stream-errors"></a>

Với Express adapter, nếu stream phát ra lỗi trước khi có dữ liệu nào được gửi, client sẽ nhận response `400 Bad Request`, và lỗi được log. Kể từ NestJS v12.2, body của response không còn chứa message lỗi, vốn có thể chứa đường dẫn của file. Nếu dữ liệu đã được gửi, response sẽ được kết thúc. Để tùy biến hành vi này, hãy truyền một handler vào method `setErrorHandler()`:

```typescript
@Get()
getReport(): StreamableFile {
  const file = createReadStream(join(process.cwd(), 'report.pdf'));
  return new StreamableFile(file).setErrorHandler((err, res) => {
    if (res.headersSent) {
      res.end();
      return;
    }
    res.statusCode = 404;
    res.send('Report not found');
  });
}
```

Method `setErrorLogger()` thay thế hàm log lỗi: những lỗi mà error handler mặc định trả lời, và những lỗi mà response stream phát ra trong lúc file đang được ghi vào nó.

> info **Lưu ý** Error handler và error logger áp dụng cho Express adapter và Node adapter. Với Fastify adapter, lỗi của stream được [lớp xử lý exception](/exception-filters) xử lý, nên mặc định client nhận response `500 Internal Server Error`.

##### Hỗ trợ đa nền tảng <a id="cross-platform-support"></a>

Fastify có thể gửi stream mà không cần `stream.pipe(res)`, nên với Fastify, class `StreamableFile` không thực sự bắt buộc. Tuy nhiên, Nest hỗ trợ `StreamableFile` trên cả hai nền tảng, nên code trả về nó vẫn chạy y như cũ khi bạn chuyển đổi giữa Express và Fastify.
