### Testing

Test tự động là một phần thiết yếu của mọi dự án phần mềm nghiêm túc. Tự động hóa giúp bạn dễ dàng chạy lại nhanh từng test hoặc cả test suite trong quá trình phát triển, góp phần đảm bảo các bản release đạt mục tiêu về chất lượng và hiệu năng. Nó tăng coverage, cho developer vòng phản hồi nhanh hơn, và đảm bảo test được chạy ở những thời điểm quan trọng trong vòng đời phát triển, như khi check-in vào source control, tích hợp tính năng, hay release phiên bản.

Có nhiều loại test, bao gồm unit test, end-to-end (e2e) test và integration test. Dù lợi ích là rõ ràng, việc thiết lập chúng có thể khá tốn công. Nest khuyến khích các best practice trong phát triển, bao gồm test hiệu quả, và có sẵn các tính năng sau để giúp developer và team xây dựng và tự động hóa test. Nest:

- tự động scaffold sẵn unit test mặc định cho các thành phần và e2e test cho ứng dụng
- cung cấp tooling mặc định (như một test runner dựng sẵn loader module/ứng dụng tách biệt)
- tích hợp sẵn với [Vitest](https://vitest.dev/) và [Supertest](https://github.com/visionmedia/supertest) nhưng vẫn không phụ thuộc vào công cụ test cụ thể nào
- cho phép dùng hệ thống dependency injection của Nest trong môi trường test, nên bạn có thể mock các thành phần mà không cần thiết lập thêm

Bạn có thể dùng bất kỳ **testing framework** nào bạn thích, vì Nest không ép buộc dùng tooling cụ thể nào. Hãy thay những thành phần bạn cần (như test runner), và bạn vẫn tận dụng được các tiện ích test có sẵn của Nest.

> info **Gợi ý** Project mới tạo dùng Vitest làm mặc định. Các API test mà Nest cung cấp không phụ thuộc vào runner cụ thể nào, nên cùng các pattern đó vẫn chạy được với các công cụ khác.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài package cần thiết:

```bash
$ npm i --save-dev @nestjs/testing
```

#### Unit test <a id="unit-testing"></a>

Ví dụ sau test hai class `CatsController` và `CatsService` bằng [Vitest](https://vitest.dev/). Vitest đóng vai trò test runner, đồng thời cung cấp các hàm assertion và tiện ích test double để mock, spy và stub. Bài test cơ bản này khởi tạo các class thủ công và kiểm tra xem controller và service có thỏa mãn hợp đồng API của chúng không.

```typescript
@@filename(cats.controller.spec)
import { vi } from 'vitest';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

describe('CatsController', () => {
  let catsController: CatsController;
  let catsService: CatsService;

  beforeEach(() => {
    catsService = new CatsService();
    catsController = new CatsController(catsService);
  });

  describe('findAll', () => {
    it('should return an array of cats', async () => {
      const result = ['test'];
      vi.spyOn(catsService, 'findAll').mockImplementation(() => result);

      expect(await catsController.findAll()).toBe(result);
    });
  });
});
@@switch
import { vi } from 'vitest';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

describe('CatsController', () => {
  let catsController;
  let catsService;

  beforeEach(() => {
    catsService = new CatsService();
    catsController = new CatsController(catsService);
  });

  describe('findAll', () => {
    it('should return an array of cats', async () => {
      const result = ['test'];
      vi.spyOn(catsService, 'findAll').mockImplementation(() => result);

      expect(await catsController.findAll()).toBe(result);
    });
  });
});
```

> info **Gợi ý** Hãy đặt file test gần các class mà nó test. File test nên có hậu tố `.spec` hoặc `.test`.

Vì ví dụ trên rất đơn giản, nó không test thứ gì đặc thù của Nest. Nó thậm chí không dùng dependency injection (nó truyền trực tiếp một instance `CatsService` vào `catsController`). Kiểu test này, trong đó bạn tự khởi tạo các class cần test, thường được gọi là **isolated testing**, vì nó độc lập với framework. Các phần sau sẽ giới thiệu những khả năng nâng cao hơn, giúp bạn test các ứng dụng dùng nhiều tính năng của Nest hơn.

#### Tiện ích test <a id="testing-utilities"></a>

Package `@nestjs/testing` cung cấp một bộ tiện ích giúp quá trình test chắc chắn hơn. Hãy viết lại ví dụ trước bằng class `Test` có sẵn:

```typescript
@@filename(cats.controller.spec)
import { vi } from 'vitest';
import { Test } from '@nestjs/testing';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

describe('CatsController', () => {
  let catsController: CatsController;
  let catsService: CatsService;

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({
        controllers: [CatsController],
        providers: [CatsService],
      }).compile();

    catsService = moduleRef.get(CatsService);
    catsController = moduleRef.get(CatsController);
  });

  describe('findAll', () => {
    it('should return an array of cats', async () => {
      const result = ['test'];
      vi.spyOn(catsService, 'findAll').mockImplementation(() => result);

      expect(await catsController.findAll()).toBe(result);
    });
  });
});
@@switch
import { vi } from 'vitest';
import { Test } from '@nestjs/testing';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

describe('CatsController', () => {
  let catsController;
  let catsService;

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({
        controllers: [CatsController],
        providers: [CatsService],
      }).compile();

    catsService = moduleRef.get(CatsService);
    catsController = moduleRef.get(CatsController);
  });

  describe('findAll', () => {
    it('should return an array of cats', async () => {
      const result = ['test'];
      vi.spyOn(catsService, 'findAll').mockImplementation(() => result);

      expect(await catsController.findAll()).toBe(result);
    });
  });
});
```

Class `Test` cung cấp một execution context cho ứng dụng, về cơ bản là giả lập toàn bộ Nest runtime, nhưng cho bạn các hook để quản lý instance của class, bao gồm mock và ghi đè. Method `createTestingModule()` của nó nhận một object metadata module làm tham số (chính là object bạn truyền vào decorator `@Module()`) và trả về một instance `TestingModuleBuilder`, instance này lại cung cấp vài method. Với unit test, method quan trọng là `compile()`. Nó bootstrap một module cùng các dependency của module đó (tương tự cách ứng dụng được bootstrap trong file `main.ts` thông thường bằng `NestFactory.create()`), và trả về một `TestingModule` sẵn sàng để test.

> info **Gợi ý** Method `compile()` là **bất đồng bộ**, nên bạn phải await nó. Khi module đã được compile, bạn có thể lấy bất kỳ instance **tĩnh** nào mà nó khai báo (controller và provider) bằng method `get()`.

`TestingModule` cung cấp cùng API resolve instance như class [module reference](/fundamentals/module-ref), bao gồm khả năng resolve động các provider có scope (transient hoặc request-scoped). Hãy dùng method `resolve()` cho việc này (method `get()` chỉ lấy được instance tĩnh).

```typescript
const moduleRef = await Test.createTestingModule({
  controllers: [CatsController],
  providers: [CatsService],
}).compile();

catsService = await moduleRef.resolve(CatsService);
```

> warning **Cảnh báo** Method `resolve()` trả về một instance duy nhất của provider từ **DI container sub-tree** riêng của nó. Mỗi sub-tree có một context identifier duy nhất. Nếu bạn gọi method này nhiều lần và so sánh tham chiếu instance, bạn sẽ thấy chúng không bằng nhau.

> info **Gợi ý** Tìm hiểu thêm về các tính năng của nó trong chương [module reference](/fundamentals/module-ref).

Thay vì dùng phiên bản production của một provider, bạn có thể ghi đè nó bằng một [custom provider](/fundamentals/custom-providers) cho mục đích test. Ví dụ, bạn có thể mock một database service thay vì kết nối tới database thật. Việc ghi đè được trình bày trong phần [end-to-end test](/fundamentals/testing#end-to-end-testing), nhưng nó cũng dùng được cho unit test.

<app-banner-courses></app-banner-courses>

#### Tự động mock <a id="auto-mocking"></a>

Nest cũng cho phép bạn định nghĩa một mock factory áp dụng cho mọi dependency còn thiếu. Điều này hữu ích khi một class có rất nhiều dependency và việc mock hết chúng sẽ tốn nhiều thời gian và công thiết lập. Để dùng tính năng này, hãy nối method `useMocker()` vào sau `createTestingModule()`, truyền vào một factory cho các mock dependency. Factory nhận một token tùy chọn (bất kỳ token nào hợp lệ cho một provider Nest) và trả về một bản implement mock. Ví dụ dưới đây tạo một mock riêng cho `CatsService` bằng `vi.fn()`.

```typescript
import { vi } from 'vitest';

describe('CatsController', () => {
  let controller: CatsController;

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({
      controllers: [CatsController],
    })
      .useMocker((token) => {
        const results = ['test1', 'test2'];
        if (token === CatsService) {
          return { findAll: vi.fn().mockResolvedValue(results) };
        }
      })
      .compile();

    controller = moduleRef.get(CatsController);
  });
});
```

Bạn có thể lấy các mock này từ container test giống như với custom provider, ví dụ `moduleRef.get(CatsService)`.

> info **Gợi ý** Bạn cũng có thể truyền trực tiếp một helper mock factory tái sử dụng được vào `useMocker()` khi muốn dùng chung test double giữa các test suite.

> info **Gợi ý** Provider `REQUEST` và `INQUIRER` không thể tự động mock, vì chúng đã được định nghĩa sẵn trong context. Tuy nhiên, bạn có thể _ghi đè_ chúng bằng cú pháp custom provider hoặc method `overrideProvider()`.

#### End-to-end test <a id="end-to-end-testing"></a>

Khác với unit test, vốn tập trung vào từng module và class riêng lẻ, end-to-end (e2e) test bao quát sự tương tác giữa các class và module ở mức tổng thể hơn, gần với kiểu tương tác mà người dùng cuối có với hệ thống production. Khi ứng dụng lớn dần, việc test thủ công hành vi end-to-end của từng API endpoint trở nên khó khăn. E2e test tự động giúp đảm bảo hành vi tổng thể của hệ thống là đúng và đáp ứng yêu cầu của dự án. E2e test dùng cấu hình tương tự như phần **unit test**. Ngoài ra, Nest giúp bạn dễ dàng dùng library [Supertest](https://github.com/visionmedia/supertest) để giả lập HTTP request.

```typescript
@@filename(cats.e2e-spec)
import request from 'supertest';
import { Test } from '@nestjs/testing';
import { CatsModule } from '../../src/cats/cats.module.js';
import { CatsService } from '../../src/cats/cats.service.js';
import { INestApplication } from '@nestjs/common';

describe('Cats', () => {
  let app: INestApplication;
  let catsService = { findAll: () => ['test'] };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [CatsModule],
    })
      .overrideProvider(CatsService)
      .useValue(catsService)
      .compile();

    app = moduleRef.createNestApplication();
    await app.init();
  });

  it(`/GET cats`, () => {
    return request(app.getHttpServer())
      .get('/cats')
      .expect(200)
      .expect({
        data: catsService.findAll(),
      });
  });

  afterAll(async () => {
    await app.close();
  });
});
@@switch
import request from 'supertest';
import { Test } from '@nestjs/testing';
import { CatsModule } from '../../src/cats/cats.module.js';
import { CatsService } from '../../src/cats/cats.service.js';

describe('Cats', () => {
  let app;
  let catsService = { findAll: () => ['test'] };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [CatsModule],
    })
      .overrideProvider(CatsService)
      .useValue(catsService)
      .compile();

    app = moduleRef.createNestApplication();
    await app.init();
  });

  it(`/GET cats`, () => {
    return request(app.getHttpServer())
      .get('/cats')
      .expect(200)
      .expect({
        data: catsService.findAll(),
      });
  });

  afterAll(async () => {
    await app.close();
  });
});
```

> info **Gợi ý** Nếu ứng dụng của bạn chạy trên [Node adapter](/http/performance#node-adapter), hãy truyền thêm một instance `NodeAdapter` vào `createNestApplication()`. Không có adapter, testing module sẽ tạo một ứng dụng Express, nên test không chạy trên adapter mà ứng dụng của bạn dùng, và sẽ lỗi nếu package `@nestjs/platform-express` chưa được cài:
>
> ```ts
> app = moduleRef.createNestApplication<NestNodeApplication>(new NodeAdapter());
> ```

> info **Gợi ý** Nếu bạn dùng [Fastify](/http/performance#fastify-adapter) làm HTTP adapter, nó cần cấu hình hơi khác một chút và có sẵn khả năng test riêng:
>
> ```ts
> let app: NestFastifyApplication;
>
> beforeAll(async () => {
>   app = moduleRef.createNestApplication<NestFastifyApplication>(
>     new FastifyAdapter(),
>   );
>
>   await app.init();
>   await app.getHttpAdapter().getInstance().ready();
> });
>
> it(`/GET cats`, () => {
>   return app
>     .inject({
>       method: 'GET',
>       url: '/cats',
>     })
>     .then((result) => {
>       expect(result.statusCode).toEqual(200);
>       expect(result.payload).toEqual(/* expectedPayload */);
>     });
> });
>
> afterAll(async () => {
>   await app.close();
> });
> ```

Ví dụ này dựa trên các khái niệm đã mô tả ở trên. Ngoài method `compile()`, nó dùng method `createNestApplication()` để khởi tạo một môi trường Nest runtime đầy đủ.

Một lưu ý: khi ứng dụng được compile bằng method `compile()`, `HttpAdapterHost#httpAdapter` vẫn còn là undefined, vì chưa có HTTP adapter hay server nào được tạo trong giai đoạn compile. Nếu test của bạn cần `httpAdapter`, hãy dùng method `createNestApplication()` để tạo instance ứng dụng, hoặc refactor project để tránh phụ thuộc này trong lúc dependency graph được khởi tạo.

Hãy cùng phân tích ví dụ.

Bài test lưu tham chiếu tới app đang chạy vào biến `app`, để dùng nó giả lập HTTP request.

HTTP request được giả lập bằng hàm `request()` của Supertest. Để định tuyến các request này tới app Nest đang chạy, bài test truyền cho `request()` một tham chiếu tới HTTP listener nằm bên dưới Nest (listener này có thể do nền tảng Express cung cấp). Do đó mới có cách viết `request(app.getHttpServer())`. Lời gọi `request()` trả về một HTTP server đã được bọc lại, kết nối với app Nest, cung cấp các method để giả lập một HTTP request thật. Ví dụ, `request(...).get('/cats')` khởi tạo một request tới app Nest giống hệt một HTTP request `GET /cats` **thật** gửi đến qua mạng.

Ví dụ cũng cung cấp một bản implement thay thế (test double) của `CatsService` trả về một giá trị hard-code mà bài test có thể kiểm tra. Hãy dùng `overrideProvider()` để cung cấp bản implement thay thế như vậy. Tương tự, Nest cung cấp các method `overrideModule()`, `overrideGuard()`, `overrideInterceptor()`, `overrideFilter()` và `overridePipe()` để lần lượt ghi đè module, guard, interceptor, filter và pipe.

Mỗi method ghi đè (trừ `overrideModule()`) trả về một object có ba method, tương ứng với những gì đã mô tả cho [custom provider](/fundamentals/custom-providers):

- `useClass`: bạn cung cấp một class sẽ được khởi tạo để tạo ra instance ghi đè lên object (provider, guard, v.v.).
- `useValue`: bạn cung cấp một instance ghi đè lên object.
- `useFactory`: bạn cung cấp một object có hàm `factory` trả về instance ghi đè lên object, và một mảng `inject` (tùy chọn) liệt kê các provider cần truyền vào hàm đó.

Còn `overrideModule()` thì trả về một object có method `useModule()`, bạn dùng nó để cung cấp một module ghi đè lên module gốc:

```typescript
const moduleRef = await Test.createTestingModule({
  imports: [AppModule],
})
  .overrideModule(CatsModule)
  .useModule(AlternateCatsModule)
  .compile();
```

Mỗi method này lại trả về instance `TestingModuleBuilder`, nên bạn có thể nối chuỗi chúng với các method khác theo [kiểu fluent](https://en.wikipedia.org/wiki/Fluent_interface). Hãy gọi `compile()` ở cuối chuỗi để Nest khởi tạo và chuẩn bị module.

Có thể bạn cũng muốn cung cấp một logger tùy chỉnh khi chạy test (ví dụ trên CI server). Dùng method `setLogger()` và truyền vào một object thỏa mãn interface `LoggerService` để bảo `TestingModuleBuilder` cách log trong lúc test (mặc định, chỉ log "error" mới được ghi ra console).

Module đã compile có vài method hữu ích, như mô tả trong bảng sau:

<table>
  <tr>
    <td>
      <code>createNestApplication()</code>
    </td>
    <td>
      Tạo và trả về một ứng dụng Nest (instance <code>INestApplication</code>) dựa trên module đã cho.
      Lưu ý rằng bạn phải tự khởi tạo ứng dụng bằng method <code>init()</code>.
    </td>
  </tr>
  <tr>
    <td>
      <code>createNestMicroservice()</code>
    </td>
    <td>
      Tạo và trả về một microservice Nest (instance <code>INestMicroservice</code>) dựa trên module đã cho.
    </td>
  </tr>
  <tr>
    <td>
      <code>get()</code>
    </td>
    <td>
      Lấy một instance tĩnh của controller hoặc provider (bao gồm guard, filter, v.v.) có trong application context. Hoạt động giống method cùng tên của class <a href="/fundamentals/module-ref">module reference</a>.
    </td>
  </tr>
  <tr>
     <td>
      <code>resolve()</code>
    </td>
    <td>
      Lấy một instance có scope (request hoặc transient) được tạo động của controller hoặc provider (bao gồm guard, filter, v.v.) có trong application context. Hoạt động giống method cùng tên của class <a href="/fundamentals/module-ref">module reference</a>.
    </td>
  </tr>
  <tr>
    <td>
      <code>select()</code>
    </td>
    <td>
      Duyệt qua dependency graph của module; có thể dùng để lấy một instance cụ thể từ module được chọn (dùng cùng với strict mode (<code>strict: true</code>) trong method <code>get()</code>).
    </td>
  </tr>
</table>

> info **Gợi ý** Hãy đặt các file e2e test trong thư mục `test`. File test nên có hậu tố `.e2e-spec`.

#### Ghi đè các enhancer đăng ký global <a id="overriding-globally-registered-enhancers"></a>

Nếu bạn có một guard (hoặc pipe, interceptor, filter) đăng ký ở cấp global, bạn cần thêm vài bước để ghi đè enhancer đó. Nhắc lại, việc đăng ký ban đầu trông như sau:

```typescript
providers: [
  {
    provide: APP_GUARD,
    useClass: JwtAuthGuard,
  },
],
```

Cách này đăng ký guard như một provider "multi" thông qua token `APP_*`. Để có thể thay thế `JwtAuthGuard` ở đây, việc đăng ký cần dùng một provider đã có tại vị trí này:

```typescript
providers: [
  {
    provide: APP_GUARD,
    useExisting: JwtAuthGuard,
    // ^^^^^^^^ notice the use of 'useExisting' instead of 'useClass'
  },
  JwtAuthGuard,
],
```

> info **Gợi ý** Đổi `useClass` thành `useExisting` để tham chiếu tới một provider đã đăng ký, thay vì để Nest khởi tạo nó phía sau token.

Giờ thì `JwtAuthGuard` hiện diện với Nest như một provider thông thường, có thể ghi đè khi tạo `TestingModule`:

```typescript
const moduleRef = await Test.createTestingModule({
  imports: [AppModule],
})
  .overrideProvider(JwtAuthGuard)
  .useClass(MockAuthGuard)
  .compile();
```

Giờ mọi test của bạn đều dùng `MockAuthGuard` cho mỗi request.

#### Test các instance request-scoped <a id="testing-request-scoped-instances"></a>

Provider [request-scoped](/fundamentals/injection-scopes) được tạo riêng cho mỗi **request** gửi đến, và instance bị garbage collect sau khi request đã được xử lý xong. Điều này gây khó khăn, vì bạn không thể truy cập vào dependency injection sub-tree được sinh ra riêng cho request đang test.

Như đã thấy ở các phần trên, method `resolve()` lấy ra một class được khởi tạo động. Ngoài ra, như mô tả trong [resolve provider có scope](/fundamentals/module-ref#resolving-scoped-providers), bạn có thể truyền một context identifier duy nhất để kiểm soát vòng đời của một DI container sub-tree. Bạn có thể kết hợp cả hai trong context test.

Chiến lược là sinh trước một context identifier và buộc Nest dùng đúng ID này để tạo sub-tree cho mọi request gửi đến. Bằng cách này, bạn có thể lấy được các instance được tạo cho request đang test.

Để làm vậy, hãy dùng `vi.spyOn()` trên `ContextIdFactory`:

```typescript
const contextId = ContextIdFactory.create();
vi
  .spyOn(ContextIdFactory, 'getByRequest')
  .mockImplementation(() => contextId);
```

Giờ bạn có thể dùng `contextId` để truy cập vào một DI container sub-tree duy nhất được sinh ra cho mọi request tiếp theo.

```typescript
catsService = await moduleRef.resolve(CatsService, contextId);
```
