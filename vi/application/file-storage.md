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

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài các dependency cần thiết:

```bash
$ npm i --save @nestjs/storage @nestjs/config
```

#### Cấu hình disk <a id="configure-the-disks"></a>

App cần hai disk. `photos` chứa ảnh sản phẩm, ai cũng được xem, nên nó có URL công khai. `private` chứa hóa đơn và các file upload chưa được kiểm tra, và chỉ truy cập được qua signed URL. Giữ file công khai và file private trên các disk riêng (trên production là các bucket riêng) đảm bảo một file không bao giờ vô tình bị công khai.

Bắt đầu với cấu hình, một [file cấu hình tùy chỉnh](/application/configuration#custom-configuration-files) cho `@nestjs/config`. `STORAGE_DRIVER` sẽ chọn local disk hoặc S3 [trên production](/application/file-storage#use-s3-or-r2-in-production); cho đến lúc đó, mọi thứ đều là local:

```typescript
@@filename(config/configuration)
export default () => ({
  appUrl: process.env.APP_URL ?? 'http://localhost:3000',
  storage: {
    // 'local' in development, 's3' in production (AWS S3, Cloudflare R2, MinIO...)
    driver: process.env.STORAGE_DRIVER ?? 'local',
    root: process.env.STORAGE_ROOT ?? 'storage',
    signingKey: process.env.STORAGE_SIGNING_KEY,
    s3: {
      endpoint: process.env.S3_ENDPOINT,
      region: process.env.S3_REGION ?? 'auto',
      photosBucket: process.env.S3_PHOTOS_BUCKET ?? 'store-photos',
      privateBucket: process.env.S3_PRIVATE_BUCKET ?? 'store-private',
      photosUrl: process.env.PHOTOS_CDN_URL,
    },
  },
});
```

Các disk được tạo từ cấu hình đó bởi một hàm factory:

```typescript
@@filename(storage/storage.config)
import { ConfigService } from '@nestjs/config';
import { LocalDisk, type StorageModuleOptions } from '@nestjs/storage';

export function createStorageOptions(config: ConfigService): StorageModuleOptions {
  const appUrl = config.getOrThrow<string>('appUrl');
  const root = config.getOrThrow<string>('storage.root');
  return {
    default: 'private',
    disks: {
      // Product photos: public, served by the app in development
      photos: new LocalDisk({ root: `${root}/photos`, publicUrl: `${appUrl}/photos` }),
      // Invoices and uploads in progress: only reachable through signed URLs
      private: new LocalDisk({
        root: `${root}/private`,
        signedUrls: {
          baseUrl: `${appUrl}/files`,
          keys: [config.getOrThrow<string>('storage.signingKey')],
        },
      }),
    },
  };
}
```

Một `LocalDisk` giữ file trong một thư mục, thư mục này được tạo lúc khởi động. `publicUrl` là nơi file có thể được truy cập công khai: `url(key)` của disk ảnh trả về các URL nằm dưới nó. Ở development, chính app sẽ phục vụ path đó (xem [Upload ảnh sản phẩm](/application/file-storage#upload-product-photos)); trên production, một CDN sẽ làm việc này.

Một thư mục local không thể tạo signed URL theo cách S3 làm, nên disk private tự ký: với `signedUrls`, `signedUrl()` của nó trả về các URL nằm dưới `baseUrl`, được ký bằng HMAC-SHA256, và app sẽ xác minh rồi phục vụ chúng (xem [Phục vụ signed URL trong development](/application/file-storage#serve-signed-urls-in-development)). `keys` nhận một hoặc nhiều key. Key đầu tiên dùng để ký, và tất cả đều dùng để xác minh, nên bạn có thể xoay vòng key bằng cách đặt key mới lên đầu và bỏ key cũ khi các link nó đã ký đều hết hạn. Một key phải có ít nhất 32 ký tự.

Đăng ký module bằng `forRootAsync()`, để factory có thể đọc `ConfigService`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { StorageModule } from '@nestjs/storage';
import configuration from './config/configuration.js';
import { createStorageOptions } from './storage/storage.config.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [configuration] }),
    StorageModule.forRootAsync({
      inject: [ConfigService],
      useFactory: createStorageOptions,
    }),
  ],
})
export class AppModule {}
```

`StorageModule` là global. Service inject một disk theo một trong ba cách:

| Cách inject | Bạn nhận được |
| --- | --- |
| `private readonly files: StorageDisk` | Disk mặc định, ở đây là `private` |
| `@InjectDisk('photos') private readonly photos: StorageDisk` | Disk có tên `photos` |
| `private readonly storage: Storage` | Mọi disk: `storage.disk('photos')`, cho code chọn disk lúc runtime |

Lỗi cấu hình sẽ làm ứng dụng dừng ngay lúc khởi động. Không có `STORAGE_SIGNING_KEY`, `getOrThrow()` sẽ báo thiếu key; với key quá ngắn, lỗi sẽ nói signing key phải có ít nhất 32 ký tự. Điều tương tự áp dụng cho một `default` không trỏ tới disk nào, và cho một class inject tên disk mà không cấu hình nào cung cấp:

```text
PhotosService injects the disk "photos" (@InjectDisk('photos')), but StorageModule has no disk by that name. Configured disks: private.
```

#### Upload ảnh sản phẩm <a id="upload-product-photos"></a>

Ảnh có thể là JPEG, PNG hoặc WebP, tối đa 5 MiB. Các quy tắc này được dùng chung bởi endpoint upload bên dưới và phần [upload từ mobile](/application/file-storage#upload-straight-to-storage-from-the-mobile-app) phía sau:

```typescript
@@filename(products/photo-rules)
/** What a product photo may be, wherever it is uploaded from. */
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_PHOTO_SIZE = 5 * 1024 * 1024; // 5 MiB
/** Every photo gets a new key, so browsers and the CDN may cache it forever. */
export const PHOTO_CACHE_CONTROL = 'public, max-age=31536000, immutable';
```

Endpoint upload dùng `FileInterceptor()` từ `@nestjs/platform-express`, như mọi upload khác. Điểm khác biệt là tùy chọn `storage`: `uploadToDisk()` là một multer storage engine stream file lên disk thay vì vào bộ nhớ hay thư mục tạm:

```typescript
@@filename(products/photos.controller)
import { BadRequestException, Controller, Get, Param, Post, Req, Res, UploadedFile, UseInterceptors } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { InjectDisk, serveFile, StorageDisk, uploadToDisk, type StoredUpload } from '@nestjs/storage';
import type { Request, Response } from 'express';
import { MAX_PHOTO_SIZE, PHOTO_CACHE_CONTROL, PHOTO_TYPES } from './photo-rules.js';
import { PhotosService } from './photos.service.js';

@Controller()
export class PhotosController {
  constructor(
    private readonly photosService: PhotosService,
    @InjectDisk('photos') private readonly photos: StorageDisk,
  ) {}

  @Post('products/:id/photo')
  @UseInterceptors(
    FileInterceptor('photo', {
      storage: uploadToDisk({ disk: 'photos', contentTypes: PHOTO_TYPES, cacheControl: PHOTO_CACHE_CONTROL }),
      limits: { fileSize: MAX_PHOTO_SIZE, files: 1 },
    }),
  )
  upload(@Param('id') id: string, @UploadedFile() file: StoredUpload | undefined) {
    if (!file) {
      throw new BadRequestException('Attach the image as the "photo" field');
    }
    return this.photosService.replace(id, file.key);
  }

  // Development only: in production a CDN serves the photos bucket at `publicUrl`
  @Get('photos/:file')
  serve(@Param('file') file: string, @Req() req: Request, @Res({ passthrough: true }) res: Response) {
    return serveFile(this.photos, file, { req, res, disposition: 'inline' });
  }
}
```

Đến lúc handler chạy, ảnh đã được lưu xong. `uploadToDisk()` đã làm ba việc trên đường đi:

- **Nó kiểm tra file thực sự là gì, chứ không phải client nói nó là gì.** Trình duyệt gửi type mà nó đoán từ tên file, còn một script có thể gửi bất cứ thứ gì, nên một file khai báo là `image/png` hoàn toàn có thể là một trang HTML hoặc một file SVG có chứa script. Engine đọc những byte đầu tiên của stream, nhận diện type từ chữ ký của chúng (có sẵn JPEG, PNG, GIF, WebP, AVIF, HEIC và PDF; [các định dạng khác](/application/file-storage#accept-csv-and-other-text-formats) cần một detector của riêng bạn), và từ chối mọi thứ không nằm trong `contentTypes` bằng lỗi `415` trước khi ghi bất kỳ byte nào. Content type được lưu là type đã nhận diện, không bao giờ là type của client.
- **Nó áp dụng giới hạn kích thước mà không để lại file dở dang.** multer ngừng đọc khi tới `limits.fileSize`. Khi đó engine từ chối commit những gì đã nhận: request thất bại với `413 File too large`, không có gì được lưu, và không file nào bị thay thế.
- **Nó chọn key.** Mặc định là một UUID ngẫu nhiên kèm phần mở rộng của type đã nhận diện, như `2f1c0d6e-….png`. Key duy nhất rất quan trọng: một lần upload không bao giờ ghi đè lên file khác, và một ảnh đã cache không bao giờ bị cũ.

`@UploadedFile()` trả về một `StoredUpload`: các trường quen thuộc của multer (`fieldname`, `originalname`, `mimetype`, `size`) cộng thêm `key`, `disk`, `contentType` và `etag`. `mimetype` vẫn là lời khai của client; hãy dùng `contentType`.

> info **Gợi ý** `ParseFilePipe` và các validator của nó chạy sau interceptor, khi file được stream đã được lưu xong, còn `FileTypeValidator` cần file nằm trong bộ nhớ để kiểm tra các byte của nó. Với `uploadToDisk()`, hãy kiểm tra type và kích thước trong engine, như ở trên. Trên Fastify, import `FileInterceptor` từ `@nestjs/platform-fastify/multipart` và đăng ký `@fastify/multipart`; `uploadToDisk()` hoạt động giống nhau với cả hai.

Sản phẩm có cấu trúc như sau, và `ProductsService` của ứng dụng có `findOne(id)`, method này throw `NotFoundException` với id không tồn tại, cùng `setPhoto(id, key)`:

```typescript
@@filename(products/product)
export interface Product {
  id: string;
  name: string;
  /** Price in cents */
  price: number;
  /** Where the photo lives on the `photos` disk */
  photoKey?: string;
}
```

Service ghi nhận ảnh mới, và xóa ảnh cũ:

```typescript
@@filename(products/photos.service)
import { Injectable } from '@nestjs/common';
import { InjectDisk, StorageDisk } from '@nestjs/storage';
import { ProductsService } from './products.service.js';

@Injectable()
export class PhotosService {
  constructor(
    private readonly productsService: ProductsService,
    @InjectDisk('photos') private readonly photos: StorageDisk,
  ) {}

  async replace(productId: string, key: string): Promise<{ id: string; photoUrl: string }> {
    let previous: string | undefined;
    try {
      previous = this.productsService.findOne(productId).photoKey;
      this.productsService.setPhoto(productId, key);
    } catch (error) {
      // The upload is already stored: don't leave it behind for a product that doesn't exist
      await this.photos.delete(key);
      throw error;
    }
    if (previous) {
      await this.photos.delete(previous);
    }
    return { id: productId, photoUrl: this.photos.url(key) };
  }
}
```

Interceptor chạy trước handler, nên file vẫn được lưu kể cả khi hóa ra sản phẩm không tồn tại. Trong trường hợp đó, service sẽ xóa nó, để một id gõ sai không để lại file mồ côi. `url(key)` tạo URL công khai từ `publicUrl` của disk.

Route `GET photos/:file` phục vụ ảnh trong development. `serveFile()` stream một file từ disk làm response, kèm `Content-Type`, `Content-Length`, `ETag`, `Last-Modified`, `Cache-Control` được lưu cùng file (`private` nếu không có, để shared cache không bao giờ giữ lại một file có thể chỉ thuộc về một người dùng), và `X-Content-Type-Options: nosniff`, để trình duyệt không bao giờ tự đoán lại type. `disposition: 'inline'` cho phép trình duyệt hiển thị ảnh; với những type có thể chạy script trong origin của bạn, như HTML hay SVG, `serveFile()` luôn gửi `Content-Disposition: attachment`. Nó trả lời request `Range` bằng `206`, `If-None-Match` bằng `304`, và file không tồn tại bằng `404`.

Đăng ký feature module, và import `ProductsModule` trong `AppModule`:

```typescript
@@filename(products/products.module)
import { Module } from '@nestjs/common';
import { PhotosController } from './photos.controller.js';
import { PhotosService } from './photos.service.js';
import { ProductsService } from './products.service.js';

@Module({
  controllers: [PhotosController],
  providers: [ProductsService, PhotosService],
})
export class ProductsModule {}
```

##### Chấp nhận CSV và các định dạng text khác <a id="accept-csv-and-other-text-formats"></a>

Việc nhận diện có sẵn nhận ra định dạng dựa vào các byte cố định mà file bắt đầu. Một file CSV không có chữ ký như vậy, nên chỉ riêng `contentTypes: ['text/csv']` sẽ từ chối mọi file CSV bằng lỗi `415`. Với định dạng như thế, hãy truyền `detectContentType`: một hàm nhận phần đầu của file và trả về type của nó, hoặc `undefined` khi không nhận ra.

Nhân viên cập nhật giá bằng cách upload một file export từ bảng tính. App nhận ra file này qua dòng tiêu đề của nó:

```typescript
@@filename(products/price-list)
/** The header row of a price list exported from the spreadsheet */
const PRICE_LIST_HEADER = 'sku,price';

/** Recognizes a price list by its first line. It doesn't check the rows. */
export function detectPriceList(bytes: Buffer): string | undefined {
  // Spreadsheet apps often start a UTF-8 export with a byte order mark: TextDecoder drops it
  const text = new TextDecoder().decode(bytes);
  const header = text.split(/\r?\n/, 1)[0];
  return header === PRICE_LIST_HEADER ? 'text/csv; charset=utf-8' : undefined;
}
```

Endpoint upload cho phép `text/csv` và truyền hàm đó vào `uploadToDisk()`. Bảng giá được đưa lên disk private, vì chưa ai kiểm tra các dòng của nó:

```typescript
@@filename(products/price-lists.controller)
@Post('products/price-lists')
@UseInterceptors(
  FileInterceptor('prices', {
    storage: uploadToDisk({
      disk: 'private',
      key: (file) => `price-lists/${randomUUID()}${file.extension}`,
      contentTypes: ['text/csv'],
      detectContentType: detectPriceList,
    }),
    limits: { fileSize: 1024 * 1024, files: 1 },
  }),
)
importPrices(@UploadedFile() file: StoredUpload | undefined) {
  if (!file) {
    throw new BadRequestException('Attach the price list as the "prices" field');
  }
  return this.priceListsService.import(file.key);
}
```

- **Việc nhận diện có sẵn chạy trước.** Hàm chỉ chạy khi file không thuộc định dạng có sẵn nào. Một file PNG bị đổi tên thành `prices.csv` vẫn được nhận diện là PNG, và bị từ chối. Truyền helper `detectContentType()` được export làm tùy chọn không có tác dụng gì, vì đó chính là bước kiểm tra đã chạy rồi.
- **Nó thấy phần đầu của file.** `bytes` chứa 4 KiB đầu tiên, hoặc toàn bộ file khi file nhỏ hơn. Để thay đổi, đặt `contentTypeSampleBytes` thành một số nguyên từ 1 byte tới 64 KiB (yêu cầu có `detectContentType`). Tham số thứ hai có `originalname` và `mimetype`, nhưng đó là lời khai của client, nên hãy quyết định dựa trên các byte.
- **Giá trị nó trả về được kiểm tra với `contentTypes`.** Type được so sánh mà không tính tham số: `text/csv` trong danh sách sẽ cho phép `text/csv; charset=utf-8`. Khi hàm trả về `undefined`, hoặc một type không có trong danh sách, upload sẽ bị từ chối bằng lỗi `415` trước khi ghi bất kỳ byte nào. Không có `contentTypes`, mọi type được trả về đều được chấp nhận, và một file không nhận ra được sẽ lưu dưới dạng `application/octet-stream`.
- **Type được trả về là type mà file được lưu và phục vụ.** Hãy kèm charset với các định dạng text. Nó cũng quyết định phần mở rộng: `file.extension` là `.csv` trong `key()` ở trên, và key mặc định cũng kết thúc bằng nó.
- **Nó có thể là async.** Engine chờ promise trong khi giữ request, nên promise phải settle nhanh. Hãy trả về `undefined` với file không nhận ra thay vì throw: một lỗi sẽ làm upload thất bại như ở bất kỳ chỗ nào khác trong request, nên mọi thứ không phải `HttpException` sẽ thành lỗi `500` thay vì `415`. Trả về bất cứ thứ gì không phải chuỗi hoặc `undefined` cũng vậy.

> warning **Cảnh báo** Hàm này phân loại phần đầu của file. Nó không validate file: một bảng giá có dòng tiêu đề đúng vẫn có thể chứa bất cứ thứ gì phía sau. `PriceListsService.import()` phải đọc toàn bộ file, kiểm tra mọi dòng, và xóa `file.key` khi từ chối bảng giá, như với mọi bước kiểm tra chạy sau interceptor.

#### Giữ hóa đơn ở chế độ private <a id="keep-invoices-private"></a>

Hóa đơn được tạo ra lần đầu tiên khi khách hàng yêu cầu và được lưu trên disk private. Một app thực tế render PDF bằng một library hoặc dịch vụ render; bản thay thế này đủ để theo dõi luồng xử lý:

```typescript
@@filename(invoices/render-invoice)
import type { Order } from '../orders/order.interface.js';

const usd = (cents: number) => (cents / 100).toFixed(2);

/** A stand-in for a real PDF renderer (pdfkit, a headless browser, a rendering service). */
export function renderInvoice(order: Order): Buffer {
  const lines = order.items.map((item) => `% ${item.quantity} x ${item.name}  ${usd(item.price)}`);
  return Buffer.from(
    ['%PDF-1.7', `% Invoice for ${order.id}`, ...lines, `% Total ${usd(order.total)} USD`, '%%EOF', ''].join('\n'),
  );
}
```

Service đọc đơn hàng bằng `OrdersService` của ứng dụng, trong đó đơn hàng `ord_1000` đã thanh toán còn `ord_1001` thì chưa, lưu hóa đơn một lần, và trả về một signed link tới nó:

```typescript
@@filename(invoices/invoices.service)
import { ConflictException, Injectable } from '@nestjs/common';
import { StorageDisk } from '@nestjs/storage';
import { OrdersService } from '../orders/orders.service.js';
import { renderInvoice } from './render-invoice.js';

@Injectable()
export class InvoicesService {
  constructor(
    private readonly ordersService: OrdersService,
    // No name: the default disk, `private`
    private readonly storageDisk: StorageDisk,
  ) {}

  async downloadUrl(orderId: string) {
    const order = this.ordersService.findOne(orderId);
    if (order.status === 'pending') {
      throw new ConflictException(`Order ${orderId} has not been paid yet`);
    }
    const key = `invoices/${order.id}.pdf`;
    if (!(await this.storageDisk.exists(key))) {
      await this.storageDisk.put(key, renderInvoice(order), {
        contentType: 'application/pdf',
        metadata: { orderId: order.id },
      });
    }
    const url = await this.storageDisk.signedUrl(key, {
      expiresIn: '5m',
      filename: `invoice-${order.id}.pdf`,
    });
    return { url };
  }
}
```

`put()` nhận một `Buffer`, một chuỗi, một `Uint8Array`, một Node stream, một web `ReadableStream`, hoặc bất kỳ async iterable byte nào. Trên mọi disk, một thao tác ghi là nguyên tử: bên đọc thấy file cũ hoặc file mới, không bao giờ thấy một nửa, và một thao tác ghi thất bại không để lại gì. `metadata` lưu các giá trị chuỗi của riêng bạn cùng với file; `stat()` và `get()` trả về chúng.

Với `LocalDisk`, một thao tác ghi filesystem thất bại sẽ xóa file tạm và giữ nguyên file đã có. Nếu việc ghi không tiến triển, hoặc kích thước đã lưu khác với số byte đã ghi, `put()` sẽ reject với `StorageError`.

`signedUrl()` trả về một link dùng được mà không cần thông tin xác thực nào khác cho đến khi hết hạn. `expiresIn` là một khoảng thời gian: `'5m'`, `'1h'`, hoặc số mili giây, mặc định là 15 phút và tối đa 7 ngày, giới hạn của S3. `filename` đặt tên mà trình duyệt dùng để lưu file.

Endpoint trả về link thay vì file, để một trang web hoặc app mobile có thể mở trực tiếp:

```typescript
@@filename(orders/orders.controller)
import { Controller, Get, Param } from '@nestjs/common';
import { InvoicesService } from '../invoices/invoices.service.js';

@Controller('orders')
export class OrdersController {
  constructor(private readonly invoicesService: InvoicesService) {}

  @Get(':id/invoice')
  invoice(@Param('id') id: string) {
    return this.invoicesService.downloadUrl(id);
  }
}
```

Đăng ký `OrdersController`, `OrdersService` và `InvoicesService` trong một `OrdersModule`. Trong app thực tế, endpoint còn kiểm tra hóa đơn có thuộc về khách hàng đang đăng nhập hay không, ví dụ bằng một policy từ bài hướng dẫn [phân quyền](/security/authorization). Bản thân link không cần kiểm tra: ai giữ nó đều tải được đúng file đó cho đến khi hết hạn.

#### Phục vụ signed URL trong development <a id="serve-signed-urls-in-development"></a>

Với local disk, signed link trỏ tới chính app, `http://localhost:3000/files?key=…&expires=…&signature=…`, nên app cần một route để xác minh và phục vụ nó:

```typescript
@@filename(files/files.controller)
import { Controller, Get, Req, Res } from '@nestjs/common';
import { serveSignedUrl, StorageDisk } from '@nestjs/storage';
import type { Request, Response } from 'express';

/**
 * Serves the private disk's signed URLs when it is a local disk. With S3, the URLs point at
 * the bucket and this route answers 404.
 */
@Controller('files')
export class FilesController {
  constructor(private readonly storageDisk: StorageDisk) {}

  @Get()
  download(@Req() req: Request, @Res({ passthrough: true }) res: Response) {
    return serveSignedUrl(this.storageDisk, { req, res });
  }
}
```

`serveSignedUrl()` kiểm tra chữ ký, thời hạn và method, rồi trả lời giống như `serveFile()`, với tên file mà link được ký kèm. Chữ ký bao gồm route (`baseUrl`), key, thời hạn và tên file, nên thay đổi bất kỳ thứ nào trong đó sẽ ra `403 Invalid signed URL`, một link đã quá hạn sẽ ra `403 The signed URL has expired`, và một link cấp cho route của một disk sẽ bị route của disk khác từ chối, kể cả khi cả hai dùng chung signing key. Các trình quản lý tải xuống có thể tiếp tục tải một file lớn bằng request `Range`.

Đăng ký controller trong một `FilesModule`, và import nó trong `AppModule` cùng các tính năng khác:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { StorageModule } from '@nestjs/storage';
import configuration from './config/configuration.js';
import { FilesModule } from './files/files.module.js';
import { OrdersModule } from './orders/orders.module.js';
import { ProductsModule } from './products/products.module.js';
import { createStorageOptions } from './storage/storage.config.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [configuration] }),
    StorageModule.forRootAsync({
      inject: [ConfigService],
      useFactory: createStorageOptions,
    }),
    ProductsModule,
    OrdersModule,
    FilesModule,
  ],
})
export class AppModule {}
```

Route vẫn nằm trong app trên production. Ở đó, disk private là một S3 disk với signed URL trỏ tới bucket, nên `serveSignedUrl()` không có gì để phục vụ và trả lời `404`.

#### Upload thẳng lên storage từ app mobile <a id="upload-straight-to-storage-from-the-mobile-app"></a>

Team kho chụp ảnh sản phẩm bằng app mobile. Ảnh có dung lượng lớn, và điện thoại thường dùng kết nối chậm, nên một lần upload qua API sẽ chiếm một kết nối và một request trong suốt thời gian upload. Thay vào đó, app xin API một upload URL, gửi ảnh thẳng lên storage, rồi báo cho API là đã xong:

1. `POST /products/:id/photo/uploads` kèm type và kích thước của ảnh trả về một signed upload URL.
2. App gửi ảnh tới URL đó bằng `PUT`.
3. `PUT /products/:id/photo` kèm key của file upload biến nó thành ảnh của sản phẩm.

File upload được đưa lên disk private, dưới `incoming/`, vì API chưa xem xét nó. Chỉ sau khi kiểm tra xong, API mới copy nó sang disk ảnh:

```typescript
@@filename(products/photos.service)
@Injectable()
export class PhotosService {
  constructor(
    private readonly productsService: ProductsService,
    @InjectDisk('photos') private readonly photos: StorageDisk,
    @InjectDisk('private') private readonly uploads: StorageDisk,
  ) {}

  // ...

  async createUpload(productId: string, contentType: string, size: number) {
    this.productsService.findOne(productId);
    if (!PHOTO_TYPES.includes(contentType)) {
      throw new UnsupportedMediaTypeException(`A photo must be one of: ${PHOTO_TYPES.join(', ')}`);
    }
    if (!Number.isSafeInteger(size) || size < 1 || size > MAX_PHOTO_SIZE) {
      throw new BadRequestException(`size must be between 1 and ${MAX_PHOTO_SIZE} bytes`);
    }
    // Private until checked; the product id in the key ties the upload to this product
    const key = `incoming/${productId}/${randomUUID()}`;
    const upload = await this.uploads.signedUpload(key, { contentType, contentLength: size, expiresIn: '10m' });
    return { key, ...upload };
  }

  async completeUpload(productId: string, key: string) {
    this.productsService.findOne(productId);
    // Only keys this endpoint handed out for this product: never copy an arbitrary private
    // file (an invoice) to the public photos disk.
    const prefix = `incoming/${productId}/`;
    if (typeof key !== 'string' || !key.startsWith(prefix) || !/^[0-9a-f-]{36}$/.test(key.slice(prefix.length))) {
      throw new BadRequestException('Unknown upload');
    }
    const file = await this.uploads.stat(key).catch((error: unknown) => {
      if (error instanceof StorageFileNotFoundError) {
        throw new BadRequestException('Upload the file first');
      }
      throw error;
    });
    if (file.size > MAX_PHOTO_SIZE) {
      await this.uploads.delete(key);
      throw new PayloadTooLargeException('File too large');
    }
    // The client chose the Content-Type: check what the bytes are
    const head = await this.uploads.get(key, { range: { start: 0, end: 15 } });
    const type = detectContentType(await buffer(head.body));
    if (!type || !PHOTO_TYPES.includes(type)) {
      await this.uploads.delete(key);
      throw new UnsupportedMediaTypeException(`A photo must be one of: ${PHOTO_TYPES.join(', ')}`);
    }
    // Stream it from the private disk to the public one
    const photoKey = `${randomUUID()}${EXTENSIONS[type]}`;
    const { body } = await this.uploads.get(key);
    await this.photos.put(photoKey, body, {
      contentType: type,
      contentLength: file.size,
      cacheControl: PHOTO_CACHE_CONTROL,
    });
    await this.uploads.delete(key);
    return this.replace(productId, photoKey);
  }
}
```

`signedUpload()` trả về URL, method (`PUT`), các header mà client phải gửi, và thời điểm URL hết hạn. URL được ký cho đúng content type và kích thước đã khai báo: một `Content-Type` khác, hoặc một body có độ dài khác, sẽ bị storage từ chối (`403`), nên app không thể gửi một video 2 GB trong khi đã khai báo một bức ảnh 2 MB.

Type đã khai báo vẫn là lời khai của client. Vì vậy `completeUpload()` xem file upload là không đáng tin:

- **Key phải là key mà nó đã cấp cho sản phẩm này.** Không có bước kiểm tra này, client có thể gửi `invoices/ord_1000.pdf` và khiến API copy hóa đơn của người khác sang disk ảnh công khai.
- **Kích thước được kiểm tra lại** bằng `stat()`, method này trả về metadata của file mà không kèm body.
- **Các byte được kiểm tra** bằng cách chỉ đọc 16 byte đầu tiên, bằng một lời gọi `get()` có range, rồi truyền chúng vào `detectContentType()`, hàm này nhận diện JPEG, PNG, GIF, WebP, AVIF, HEIC và PDF.

Chỉ sau đó ảnh mới được stream từ disk này sang disk kia: `get()` trả về body dưới dạng Node stream, và `put()` nhận nó, nên file không bao giờ nằm trọn vẹn trong bộ nhớ. Trên S3, đó là một lần tải xuống và một lần tải lên đi qua instance API, điều này ổn với ảnh; với các file rất lớn, bạn nên xử lý chúng ngay tại chỗ, ví dụ bằng một job.

Hai route trong controller chuyển tiếp request:

```typescript
@@filename(products/photos.controller)
// The mobile app asks for an upload URL, sends the photo there, then submits its key
@Post('products/:id/photo/uploads')
createUpload(@Param('id') id: string, @Body() body: { contentType: string; size: number }) {
  return this.photosService.createUpload(id, body.contentType, body.size);
}

@Put('products/:id/photo')
completeUpload(@Param('id') id: string, @Body('key') key: string) {
  return this.photosService.completeUpload(id, key);
}
```

Với local disk, upload URL lại trỏ tới app, nên `FilesController` cũng nhận cả `PUT`. `receiveSignedUpload()` làm đúng những gì S3 làm với presigned URL: nó kiểm tra chữ ký, thời hạn, content type và độ dài, rồi stream body lên disk:

```typescript
@@filename(files/files.controller)
import { Controller, Get, Put, Req, Res } from '@nestjs/common';
import { receiveSignedUpload, serveSignedUrl, StorageDisk } from '@nestjs/storage';
import type { Request, Response } from 'express';

/**
 * Serves the private disk's signed URLs when it is a local disk. With S3, the URLs point at
 * the bucket and this route answers 404.
 */
@Controller('files')
export class FilesController {
  constructor(private readonly storageDisk: StorageDisk) {}

  @Get()
  download(@Req() req: Request, @Res({ passthrough: true }) res: Response) {
    return serveSignedUrl(this.storageDisk, { req, res });
  }

  @Put()
  upload(@Req() req: Request, @Res({ passthrough: true }) res: Response) {
    return receiveSignedUpload(this.storageDisk, { req, res });
  }
}
```

> info **Gợi ý** Trên Fastify, body của file upload phải đến handler mà chưa bị đọc. Mặc định Fastify chỉ parse JSON và plain text, và trả lời các content type khác bằng `415`, nên hãy đăng ký một parser bắt mọi type mà để nguyên body: `app.getHttpAdapter().getInstance().addContentTypeParser('*', (req, payload, done) => done(null))`.

Các file upload không bao giờ được hoàn tất sẽ nằm lại dưới `incoming/`. Trên S3, một lifecycle rule sẽ xóa chúng sau một ngày (xem checklist cho production).

#### Dùng S3 hoặc R2 trên production <a id="use-s3-or-r2-in-production"></a>

Trên production, cả hai disk đều trở thành S3 disk. Local disk không thể phục vụ ở đó: file system của container bị hủy khi task bị thay thế (một đợt deploy, một lần scale-in, một node lỗi), kéo theo cả các file, và các instance khác không đọc được chúng. Chỉ có factory thay đổi; mọi service, controller và signed URL vẫn tiếp tục hoạt động:

```typescript
@@filename(storage/storage.config)
import { ConfigService } from '@nestjs/config';
import { LocalDisk, S3Disk, type StorageModuleOptions } from '@nestjs/storage';

export function createStorageOptions(config: ConfigService): StorageModuleOptions {
  if (config.get('storage.driver') === 's3') {
    const s3 = {
      endpoint: config.get<string>('storage.s3.endpoint'),
      region: config.getOrThrow<string>('storage.s3.region'),
    };
    return {
      default: 'private',
      disks: {
        photos: new S3Disk({
          ...s3,
          bucket: config.getOrThrow<string>('storage.s3.photosBucket'),
          publicUrl: config.getOrThrow<string>('storage.s3.photosUrl'),
        }),
        private: new S3Disk({
          ...s3,
          bucket: config.getOrThrow<string>('storage.s3.privateBucket'),
        }),
      },
    };
  }

  // ... the local disks from before
}
```

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

> info **Gợi ý** Mọi request S3 đều được ký bằng Signature Version 4, implement trên `node:crypto`. Nó được kiểm tra với bộ test AWS Signature Version 4 và các ví dụ trong tài liệu API của Amazon S3, nên không cần cài AWS SDK.

#### Thử ngay <a id="try-it"></a>

Khởi động app với một signing key, trong một thư mục có file `kibble.png`, `scratching-post.jpg` và `notes.txt`:

```bash
$ export STORAGE_SIGNING_KEY=$(openssl rand -hex 32)
$ npm run start
```

Upload một bức ảnh. Sau đó thử một file text khai báo là ảnh, app sẽ từ chối mà không lưu nó:

```bash
$ curl -F photo=@kibble.png localhost:3000/products/salmon-kibble-2kg/photo
{"id":"salmon-kibble-2kg","photoUrl":"http://localhost:3000/photos/b098be38-74b4-427a-8239-0ab3dc3a31d2.png"}

$ curl -F 'photo=@notes.txt;type=image/png' localhost:3000/products/salmon-kibble-2kg/photo
{"message":"File type not allowed. Allowed types: image/jpeg, image/png, image/webp","error":"Unsupported Media Type","statusCode":415}
```

Lấy header của một bức ảnh:

```bash
$ PHOTO=$(curl -s -F photo=@kibble.png localhost:3000/products/salmon-kibble-2kg/photo | jq -r .photoUrl)
$ curl -sI "$PHOTO" | grep -iE '^(content-|cache-control|x-content)'
X-Content-Type-Options: nosniff
Cache-Control: public, max-age=31536000, immutable
Content-Type: image/png
Content-Disposition: inline; filename="fc54756b-b451-41a8-82c9-2b979f99849a.png"
Content-Length: 70
```

Lấy signed link tới một hóa đơn, tải nó về, và thử cùng link đó cho một đơn hàng khác:

```bash
$ curl localhost:3000/orders/ord_1000/invoice
{"url":"http://localhost:3000/files?key=invoices%2Ford_1000.pdf&expires=1790319338&disposition=attachment%3B+filename%3D%22invoice-ord_1000.pdf%22&signature=w1O_KuRThM1epUeyqpsbXNGfECkQ9605tZzNjVFMsy8"}

$ INVOICE=$(curl -s localhost:3000/orders/ord_1000/invoice | jq -r .url)
$ curl -sOJ "$INVOICE"
$ head -c 8 invoice-ord_1000.pdf
%PDF-1.7

$ curl "${INVOICE/ord_1000/ord_1001}"
{"message":"Invalid signed URL","error":"Forbidden","statusCode":403}
```

Cuối cùng, upload một bức ảnh theo cách app mobile làm. Xin một upload URL, gửi file lên đó, và gửi key của nó:

```bash
$ curl -s localhost:3000/products/sisal-scratching-post/photo/uploads --json "{\"contentType\":\"image/jpeg\",\"size\":$(wc -c < scratching-post.jpg)}" | tee upload.json | jq
{
  "key": "incoming/sisal-scratching-post/7fe80da3-4710-4940-a904-4a1756280440",
  "url": "http://localhost:3000/files?key=incoming%2Fsisal-scratching-post%2F7fe80da3-4710-4940-a904-4a1756280440&expires=1790319638&method=PUT&type=image%2Fjpeg&length=2011&signature=vx-LwzqLUUeTQevHKTDjguRTM3c_FWOjCbik1Uo6Ojg",
  "method": "PUT",
  "headers": {
    "content-type": "image/jpeg"
  },
  "expiresAt": "2026-09-25T07:00:38.736Z"
}

$ curl -T scratching-post.jpg -H 'content-type: image/jpeg' "$(jq -r .url upload.json)"
{"key":"incoming/sisal-scratching-post/7fe80da3-4710-4940-a904-4a1756280440","size":2011,"contentType":"image/jpeg","etag":"\"7db-65c4922577c58\""}

$ curl -X PUT localhost:3000/products/sisal-scratching-post/photo --json "$(jq -c '{key}' upload.json)"
{"id":"sisal-scratching-post","photoUrl":"http://localhost:3000/photos/5329e44d-7a45-49a5-96eb-6ea0016da7eb.jpg"}
```

Các file nằm trong `storage/photos` và `storage/private`, dưới dạng file thông thường: `storage/private/invoices/ord_1000.pdf` là hóa đơn. Thư mục `.nest-storage` trong mỗi disk chứa các file tạm trong lúc ghi, và các metadata mà tên file không chứa được.

#### Test <a id="testing"></a>

`InMemoryDisk` giữ file trong bộ nhớ và hoạt động giống các disk khác: cùng quy tắc key, range, liệt kê, metadata và signed URL. Giống như S3, nó có thể chứa cả `a` lẫn `a/b`, điều mà local disk từ chối bằng `StorageKeyConflictError`. Trong một end-to-end test, hãy thay các disk bằng cách ghi đè `STORAGE_MODULE_OPTIONS`, tức các tùy chọn mà factory lẽ ra sẽ trả về:

```typescript
@@filename(test/photos.e2e-spec)
import type { INestApplication } from '@nestjs/common';
import { InMemoryDisk, STORAGE_MODULE_OPTIONS } from '@nestjs/storage';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';

const PNG = Buffer.from('89504e470d0a1a0a0000000d49484452', 'hex');

describe('Product photos', () => {
  let app: INestApplication;
  const photos = new InMemoryDisk({ publicUrl: 'https://photos.example.com' });
  const files = new InMemoryDisk({
    signedUrls: { baseUrl: 'https://api.example.com/files', keys: ['test-signing-key-0123456789abcdef'] },
  });

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(STORAGE_MODULE_OPTIONS)
      .useValue({ default: 'private', disks: { photos, private: files } })
      .compile();
    app = moduleRef.createNestApplication();
    await app.init();
  });

  afterAll(() => app.close());
  beforeEach(() => photos.clear());

  it('stores the photo and returns its public URL', async () => {
    const res = await request(app.getHttpServer())
      .post('/products/salmon-kibble-2kg/photo')
      .attach('photo', PNG, 'photo.png')
      .expect(201);

    const [key] = photos.keys();
    expect(res.body.photoUrl).toBe(`https://photos.example.com/${key}`);
    expect(await photos.getBuffer(key)).toEqual(PNG);
  });

  it('refuses a file that is not an image', async () => {
    await request(app.getHttpServer())
      .post('/products/salmon-kibble-2kg/photo')
      .attach('photo', Buffer.from('<html></html>'), 'photo.png')
      .expect(415);

    expect(photos.keys()).toEqual([]);
  });
});
```

Các tùy chọn ghi đè thay thế kết quả của factory, nên bài test không cần signing key và không đụng tới file system. `keys()` liệt kê những gì một disk đang chứa và `clear()` xóa sạch nó. File upload đi qua multer và `uploadToDisk()` giống như trên production; chỉ có nơi các byte được ghi xuống là khác.

Để test những gì thực sự được ghi xuống file system, hãy dùng một `LocalDisk` trên một thư mục tạm. Với các hành vi đặc thù của S3, như presigned URL hay multipart upload, hãy trỏ một `S3Disk` tới MinIO hoặc một server tương thích S3 khác chạy ở local.
#### Checklist cho production <a id="production-checklist"></a>

- **Giữ file công khai và file private trong các bucket riêng.** Cấp quyền đọc công khai cho bucket ảnh, hoặc đặt một CDN phía trước nó và trỏ `publicUrl` tới CDN. Giữ bucket private hoàn toàn private: hóa đơn và file upload chỉ truy cập được qua signed URL. Không có flag công khai cho từng file, vì các bucket S3 mới đã tắt object ACL, và một flag trên từng file rất dễ đặt sai.
- **Cho các file upload bị bỏ dở hết hạn.** Thêm một lifecycle rule vào bucket private để xóa các object dưới `incoming/` sau một ngày, và một rule để hủy các multipart upload chưa hoàn tất sau một ngày.
- **Cho phép upload trực tiếp từ trình duyệt bằng CORS.** App mobile không cần, nhưng một trang web gửi `PUT` tới presigned URL thì cần: hãy cho phép `PUT` từ origin của site bạn, kèm header `Content-Type`.
- **Chỉ cấp cho app những quyền nó dùng.** Một IAM policy với `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` và `s3:ListBucket` trên hai bucket là đủ. Hãy giữ `s3:ListBucket`: không có nó, S3 trả lời request tới file không tồn tại bằng `403` thay vì `404`, và `exists()` sẽ lỗi thay vì trả về `false`. Với thông tin xác thực ngắn hạn, hãy truyền một hàm `credentials` trả về chúng.
- **Mã hóa dữ liệu lưu trữ.** S3 mặc định mã hóa các object mới; để dùng KMS key của riêng bạn, đặt `serverSideEncryption: 'aws:kms'` và `kmsKeyId` trên disk. R2 luôn mã hóa.
- **Giữ link ngắn hạn.** Năm phút là quá đủ cho một link mà người dùng click ngay. Signed URL không thể thu hồi: nó vẫn hợp lệ cho đến khi hết hạn (hoặc, trên S3, cho đến khi thông tin xác thực đã ký nó hết hạn hoặc mất quyền truy cập), nên ai có được nó nếu bị lộ đều dùng được cho đến lúc đó.
- **Đặt một signing key cho mỗi môi trường** với local disk (development và CI), lấy từ secret, có ít nhất 32 ký tự, và xoay vòng nó bằng cách đặt key mới lên đầu trong `keys`.
- **Đừng dùng local disk trên production.** File ghi vào ổ đĩa của container sẽ biến mất khi task bị thay thế, và các instance khác không đọc được chúng. Hãy dùng S3, R2 hoặc một object store khác (xem [Dùng S3 hoặc R2 trên production](/application/file-storage#use-s3-or-r2-in-production)); local disk dành cho development và test, và module sẽ log cảnh báo lúc khởi động khi phát hiện local disk với `NODE_ENV=production`.
- **Cẩn trọng với mọi key được tạo từ dữ liệu người dùng nhập vào.** Key được validate trên mọi disk (không có `..`, không có đường dẫn tuyệt đối, không có ký tự điều khiển), nên dữ liệu người dùng không thể thoát ra khỏi một disk, nhưng vẫn có thể trỏ tới bất kỳ file nào trên disk đó. Hãy tạo key từ các id do bạn kiểm soát, như các endpoint upload ở trên.

#### Tham khảo <a id="reference"></a>

##### Tùy chọn module <a id="module-options"></a>

`StorageModule.forRoot()` nhận các tùy chọn này, và factory của `forRootAsync()` trả về `default` cùng các instance disk. Class disk, `imports` và `isGlobal` đặt cạnh `useFactory`, `useClass` hoặc `useExisting`. Các tùy chọn được cung cấp dưới dạng `STORAGE_MODULE_OPTIONS`.

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `disks` | không có (bắt buộc) | Các disk theo tên: instance, hoặc class `StorageDisk` để Nest khởi tạo, các class này có thể inject. Xem [Cấu hình disk](/application/file-storage#configure-the-disks). |
| `default` | disk duy nhất | Disk mà `StorageDisk` và `storage.disk()` resolve ra. Bắt buộc khi có nhiều hơn một disk. |
| `imports` | không có | Các module có export mà class disk inject. |
| `isGlobal` | `true` | Đăng ký `Storage`, `StorageDisk` và các disk có tên ở cấp global. |

##### Method của disk <a id="disk-methods"></a>

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

##### Disk <a id="disks"></a>

| Disk | Tùy chọn |
| --- | --- |
| `LocalDisk` | `root` (bắt buộc, được tạo lúc khởi động), `publicUrl`, `signedUrls`. Dành cho development và test. `path(key)` trả về đường dẫn tuyệt đối của một file. |
| `S3Disk` | `bucket` (bắt buộc), `region`, `endpoint`, `forcePathStyle`, `credentials`, `prefix`, `serverSideEncryption`, `kmsKeyId`, `multipart`, `retry`, `timeout`, `batchDelete`, `fetch`, `publicUrl`. Xem [Dùng S3 hoặc R2 trên production](/application/file-storage#use-s3-or-r2-in-production). |
| `InMemoryDisk` | `publicUrl`, `signedUrls`. Dành cho test, với `keys()` và `clear()`. Xem [Test](/application/file-storage#testing). |

`signedUrls` nhận `baseUrl`, route phục vụ các URL, và `keys`, các signing key có ít nhất 32 ký tự. Key đầu tiên dùng để ký, và tất cả dùng để xác minh. Giá trị mặc định của `S3Disk`: `region` lấy từ `AWS_REGION`, rồi `AWS_DEFAULT_REGION`, rồi `us-east-1`; thông tin xác thực từ `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` và `AWS_SESSION_TOKEN`; `multipart` với `partSize` là 8 MiB và `concurrency` là 4; `retry: 3`, với backoff bắt đầu từ 100 ms và nhân đôi tới 20 giây; không có `timeout`; `batchDelete: true`.

##### Helper HTTP <a id="http-helpers"></a>

| Helper | Tùy chọn | Mô tả |
| --- | --- | --- |
| `uploadToDisk(options)` | `disk` (tên hoặc instance, mặc định là disk mặc định), `contentTypes`, `detectContentType`, `contentTypeSampleBytes` (mặc định 4 KiB, từ 1 byte tới 64 KiB, yêu cầu có `detectContentType`), `cacheControl`, `key`, `metadata` | Một storage engine cho `FileInterceptor()`. `key` và `metadata` là các hàm theo file và request. `detectContentType(bytes, file)` trả về type của một file mà việc nhận diện có sẵn không nhận ra, hoặc `undefined`, và có thể trả về promise. Xem [Upload ảnh sản phẩm](/application/file-storage#upload-product-photos) và [Chấp nhận CSV và các định dạng text khác](/application/file-storage#accept-csv-and-other-text-formats). |
| `serveFile(disk, key, options)` | `res` (bắt buộc), `req`, `disposition` (mặc định `attachment`), `filename`, `cacheControl` | Stream một file làm response, hỗ trợ `Range` và `If-None-Match` khi có truyền `req`. |
| `serveSignedUrl(disk, options)` | `req`, `res`, `cacheControl` | Xác minh và phục vụ một signed download URL do app phục vụ. Xem [Phục vụ signed URL trong development](/application/file-storage#serve-signed-urls-in-development). |
| `receiveSignedUpload(disk, options)` | `req`, `res`, `maxSize` | Xác minh một signed upload URL do app phục vụ và stream body của `PUT` lên disk. `maxSize` giới hạn các upload được ký mà không có `contentLength`. |
| `detectContentType(bytes)` | không có | Type của một file dựa trên 16 byte đầu tiên: JPEG, PNG, GIF, WebP, AVIF, HEIC hoặc PDF, nếu không thì `undefined`. Đây chính là bước nhận diện có sẵn mà `uploadToDisk()` chạy, và không liên quan gì tới tùy chọn `detectContentType`. |

##### Lỗi <a id="errors"></a>

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
