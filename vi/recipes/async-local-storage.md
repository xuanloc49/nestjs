### Async Local Storage

`AsyncLocalStorage` là một [API của Node.js](https://nodejs.org/api/async_context.html#class-asynclocalstorage) (dựa trên API `async_hooks`) cung cấp một cách khác để lan truyền trạng thái cục bộ xuyên suốt ứng dụng mà không cần truyền nó một cách tường minh làm tham số của hàm. Nó tương tự thread-local storage trong các ngôn ngữ khác.

Ý tưởng chính của Async Local Storage là bạn có thể _bọc_ một lời gọi hàm bằng lời gọi `AsyncLocalStorage#run`. Mọi đoạn code được gọi bên trong lời gọi được bọc đều truy cập được cùng một `store`, store này là duy nhất cho mỗi chuỗi lời gọi.

Trong ngữ cảnh NestJS, điều này có nghĩa là nếu bạn tìm được một chỗ trong vòng đời của request để bọc phần code còn lại của request, bạn có thể truy cập và thay đổi trạng thái chỉ hiển thị với request đó. Đây có thể là một lựa chọn thay thế cho các provider REQUEST-scoped, tránh được một số hạn chế của chúng.

Ngoài ra, bạn có thể dùng ALS để lan truyền context chỉ cho một phần của hệ thống (ví dụ object _transaction_) mà không cần truyền nó một cách tường minh qua các service, điều này có thể tăng tính cô lập và đóng gói.

Nếu ứng dụng của bạn được instrument bằng [NestJS Observe](/observability/overview), bạn đã có sẵn một store theo request và không cần tự xây. Xem phần [NestJS Observe](/recipes/async-local-storage#nestjs-observe) bên dưới.

#### Tự hiện thực <a id="custom-implementation"></a>

Framework lõi của NestJS không cung cấp lớp trừu tượng có sẵn cho `AsyncLocalStorage`, nên hãy cùng xem cách tự hiện thực nó cho trường hợp HTTP đơn giản nhất, để hiểu rõ hơn toàn bộ khái niệm:

> info **Gợi ý** Để có giải pháp làm sẵn, hãy xem các phần [`@nestjs/observe`](/recipes/async-local-storage#nestjs-observe) và [`nestjs-cls`](/recipes/async-local-storage#nestjs-cls) bên dưới.

1. Trước tiên, tạo một instance mới của `AsyncLocalStorage` trong một file mã nguồn dùng chung. Vì đang dùng NestJS, hãy biến nó thành một module với một custom provider.

```ts
@@filename(als.module)
@Module({
  providers: [
    {
      provide: AsyncLocalStorage,
      useValue: new AsyncLocalStorage(),
    },
  ],
  exports: [AsyncLocalStorage],
})
export class AlsModule {}
```
> info **Gợi ý** `AsyncLocalStorage` được import từ `node:async_hooks`.

2. Chúng ta chỉ quan tâm tới HTTP, nên hãy dùng một middleware để bọc hàm `next` bằng `AsyncLocalStorage#run`. Vì middleware là thứ đầu tiên mà request đi qua, điều này giúp `store` có sẵn trong mọi enhancer và phần còn lại của hệ thống.

```ts
@@filename(app.module)
@Module({
  imports: [AlsModule],
  providers: [CatsService],
  controllers: [CatsController],
})
export class AppModule implements NestModule {
  constructor(
    // inject the AsyncLocalStorage in the module constructor,
    private readonly als: AsyncLocalStorage
  ) {}

  configure(consumer: MiddlewareConsumer) {
    // bind the middleware,
    consumer
      .apply((req, res, next) => {
        // populate the store with some default values
        // based on the request,
        const store = {
          userId: req.headers['x-user-id'],
        };
        // and pass the "next" function as callback
        // to the "als.run" method together with the store.
        this.als.run(store, () => next());
      })
      .forRoutes('*path');
  }
}
@@switch
@Module({
  imports: [AlsModule],
  providers: [CatsService],
  controllers: [CatsController],
})
@Dependencies(AsyncLocalStorage)
export class AppModule {
  constructor(als) {
    // inject the AsyncLocalStorage in the module constructor,
    this.als = als;
  }

  configure(consumer) {
    // bind the middleware,
    consumer
      .apply((req, res, next) => {
        // populate the store with some default values
        // based on the request,
        const store = {
          userId: req.headers['x-user-id'],
        };
        // and pass the "next" function as callback
        // to the "als.run" method together with the store.
        this.als.run(store, () => next());
      })
      .forRoutes('*path');
  }
}
```

3. Giờ bạn có thể truy cập instance store cục bộ ở bất cứ đâu trong vòng đời của một request.

```ts
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(
    // We can inject the provided ALS instance.
    private readonly als: AsyncLocalStorage,
    private readonly catsRepository: CatsRepository,
  ) {}

  getCatForUser() {
    // The "getStore" method will always return the
    // store instance associated with the given request.
    const userId = this.als.getStore()["userId"] as number;
    return this.catsRepository.getForUser(userId);
  }
}
@@switch
@Injectable()
@Dependencies(AsyncLocalStorage, CatsRepository)
export class CatsService {
  constructor(als, catsRepository) {
    // We can inject the provided ALS instance.
    this.als = als;
    this.catsRepository = catsRepository;
  }

  getCatForUser() {
    // The "getStore" method will always return the
    // store instance associated with the given request.
    const userId = this.als.getStore()["userId"];
    return this.catsRepository.getForUser(userId);
  }
}
```

4. Giờ bạn đã có cách dùng chung trạng thái liên quan tới request mà không cần inject cả object `REQUEST`.

> warning **Cảnh báo** Dù kỹ thuật này hữu ích cho nhiều use case, bản chất nó làm luồng code khó theo dõi hơn (bằng cách tạo ra context ngầm), nên hãy dùng nó một cách có trách nhiệm, và đặc biệt tránh tạo ra các "[God object](https://en.wikipedia.org/wiki/God_object)" theo ngữ cảnh.

### NestJS Observe

Nếu bạn chạy [NestJS Observe](/observability/overview), SDK `@nestjs/observe` đã duy trì sẵn một store `AsyncLocalStorage` cho mọi request, job và message mà nó instrument. Store này mang trace context đi qua call stack của bạn. `TracerService` cung cấp nó, nên trạng thái theo request là thứ bạn đọc và ghi chứ không phải thứ bạn phải thiết lập: không có module nào phải viết, không có middleware nào phải mount, và không có gì phải nối lại cho từng transport.

> info **Gợi ý** Đây chính là `TracerService` được mô tả trong [Instrumentation thủ công](/observability/manual-instrumentation). Phần này chỉ nói về khía cạnh async local storage của nó; span, lỗi đã xử lý và custom metric được mô tả ở đó.

#### Thiết lập <a id="setup"></a>

Không cần thiết lập gì ngoài việc tích hợp SDK tiêu chuẩn được mô tả trong [Observability → SDK](/observability/sdk): cài package, import `ObserveModule.forRoot()`, và truyền `ObserveInstrument` cho `NestFactory.create()`.

```bash
$ npm i @nestjs/observe
```

`ObserveModule` export `TracerService`, nên bạn có thể inject nó ở bất cứ đâu trong ứng dụng:

```ts
@@filename(cats.service)
import { Injectable } from '@nestjs/common';
import { TracerService } from '@nestjs/observe';

@Injectable()
export class CatsService {
  constructor(private readonly tracerService: TracerService) {}
}
```

#### Đọc và ghi store <a id="reading-and-writing-the-store"></a>

`setAttribute(key, value)` ghi vào context store hiện tại, và `getAttribute(key)` đọc lại giá trị từ bất cứ đâu phía sau trên cùng request (một service khác, một guard, hoặc một interceptor) mà không cần truyền nó qua signature của từng hàm:

```ts
@@filename(cats.controller)
@Get()
findAll(@Req() req: Request) {
  this.tracerService.setAttribute('userId', req.headers['x-user-id']);
  return this.catsService.getCatForUser();
}
```

```ts
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(
    private readonly tracerService: TracerService,
    private readonly catsRepository: CatsRepository,
  ) {}

  getCatForUser() {
    const userId = this.tracerService.getAttribute('userId');
    return this.catsRepository.getForUser(userId);
  }
}
```

`getAttribute()` trả về `undefined` với một key chưa từng được đặt. Cả hai method đều throw khi được gọi bên ngoài một context đang được trace, vì không có store nào để đọc hay ghi. Nếu một giá trị có thể được đọc một cách hợp lệ trước khi có request nào, hãy phòng thủ lời gọi cho phù hợp.

#### Gán type cho store <a id="typing-the-store"></a>

Truyền cấu trúc của store làm type argument đầu tiên của `TracerService` để key và value được kiểm tra type, kể cả các path lồng nhau:

```ts
interface RequestStore {
  userId: number;
  flags: { betaCheckout: boolean };
}

@Injectable()
export class CatsService {
  constructor(private readonly tracerService: TracerService<RequestStore>) {}

  enableBeta() {
    this.tracerService.setAttribute('flags.betaCheckout', true);
  }
}
```

#### Ngoài HTTP <a id="beyond-http"></a>

Vì store được tạo bởi phần instrumentation chứ không phải bởi một middleware, nó tồn tại ở bất cứ đâu SDK trace một operation: HTTP và GraphQL request, message gRPC và `@nestjs/microservices`, và công việc nền như BullMQ consumer và các lần chạy cron. Pattern ở trên giống hệt nhau ở tất cả các nơi đó. Đây là khác biệt thực tế so với một phần hiện thực tự viết dựa trên middleware, vốn chỉ bao phủ HTTP.

Store cũng chứa trace ID hiện tại, nên nó đồng thời là correlation key cho log và các service phía sau. `currentTraceId()` trả về nó. Khác với `getAttribute()`, nó trả về `null` bên ngoài một context đang được trace thay vì throw:

```ts
const traceId = this.tracerService.currentTraceId();
```

> info **Gợi ý** `ObserveModule` cũng export instance `AsyncLocalStorage` bên dưới. `setAttribute()` và `getAttribute()` là cách được hỗ trợ để truy cập store; chỉ inject trực tiếp instance nếu bạn cần thứ mà chúng không cung cấp.

### NestJS CLS

Package [nestjs-cls](https://github.com/Papooch/nestjs-cls) cung cấp một số cải tiến về trải nghiệm phát triển so với `AsyncLocalStorage` thuần (`CLS` là viết tắt của _continuation-local storage_). Nó trừu tượng hóa phần hiện thực thành một `ClsModule` cung cấp nhiều cách khởi tạo `store` cho các transport khác nhau (không chỉ HTTP), cùng với hỗ trợ type mạnh.

Sau đó bạn có thể truy cập store bằng một `ClsService` có thể inject, hoặc trừu tượng hóa nó hoàn toàn khỏi logic nghiệp vụ bằng [Proxy Provider](https://www.npmjs.com/package/nestjs-cls#proxy-providers).

> info **Lưu ý** `nestjs-cls` là một package bên thứ ba và không do team lõi NestJS quản lý. Hãy báo cáo mọi vấn đề với library trong [repository nestjs-cls](https://github.com/Papooch/nestjs-cls/issues).

#### Cài đặt <a id="installation"></a>

Ngoài peer dependency vào các package `@nestjs`, nó chỉ dùng các API có sẵn của Node.js. Cài nó như mọi package khác:

```bash
$ npm i nestjs-cls
```

#### Cách dùng <a id="usage"></a>

Bạn có thể hiện thực chức năng tương tự [phần tự hiện thực](/recipes/async-local-storage#custom-implementation) ở trên bằng `nestjs-cls`, như sau:

1. Import `ClsModule` trong root module.

```ts
@@filename(app.module)
@Module({
  imports: [
    // Register the ClsModule,
    ClsModule.forRoot({
      middleware: {
        // automatically mount the
        // ClsMiddleware for all routes
        mount: true,
        // and use the setup method to
        // provide default store values.
        setup: (cls, req) => {
          cls.set('userId', req.headers['x-user-id']);
        },
      },
    }),
  ],
  providers: [CatsService],
  controllers: [CatsController],
})
export class AppModule {}
```

2. Sau đó dùng `ClsService` để truy cập các giá trị trong store.

```ts
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(
    // We can inject the provided ClsService instance,
    private readonly cls: ClsService,
    private readonly catsRepository: CatsRepository,
  ) {}

  getCatForUser() {
    // and use the "get" method to retrieve any stored value.
    const userId = this.cls.get('userId');
    return this.catsRepository.getForUser(userId);
  }
}
@@switch
@Injectable()
@Dependencies(ClsService, CatsRepository)
export class CatsService {
  constructor(cls, catsRepository) {
    // We can inject the provided ClsService instance,
    this.cls = cls;
    this.catsRepository = catsRepository;
  }

  getCatForUser() {
    // and use the "get" method to retrieve any stored value.
    const userId = this.cls.get('userId');
    return this.catsRepository.getForUser(userId);
  }
}
```

3. Để có type mạnh cho các giá trị trong store do `ClsService` quản lý (và gợi ý tự động cho các key dạng chuỗi), hãy dùng type parameter tùy chọn `ClsService<MyClsStore>` khi inject nó.

```ts
export interface MyClsStore extends ClsStore {
  userId: number;
}
```

> info **Gợi ý** Bạn cũng có thể để package tự động sinh một request ID và truy cập nó sau bằng `cls.getId()`, hoặc lấy toàn bộ object request bằng `cls.get(CLS_REQ)`.

#### Testing

Vì `ClsService` chỉ là một provider có thể inject khác, bạn có thể mock nó hoàn toàn trong unit test.

Tuy nhiên, trong một số integration test, bạn có thể vẫn muốn dùng phần hiện thực `ClsService` thật. Trong trường hợp đó, hãy bọc đoạn code cần context bằng một lời gọi `ClsService#run` hoặc `ClsService#runWith`:

```ts
describe('CatsService', () => {
  let service: CatsService
  let cls: ClsService
  const mockCatsRepository = createMock<CatsRepository>()

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      // Set up most of the testing module as we normally would.
      providers: [
        CatsService,
        {
          provide: CatsRepository,
          useValue: mockCatsRepository,
        }
      ],
      imports: [
        // Import the static version of ClsModule which only provides
        // the ClsService, but does not set up the store in any way.
        ClsModule
      ],
    }).compile()

    service = module.get(CatsService)

    // Also retrieve the ClsService for later use.
    cls = module.get(ClsService)
  })

  describe('getCatForUser', () => {
    it('retrieves cat based on user id', async () => {
      const expectedUserId = 42
      mockCatsRepository.getForUser.mockImplementationOnce(
        (id) => ({ userId: id })
      )

      // Wrap the test call in the `runWith` method
      // in which we can pass hand-crafted store values.
      const cat = await cls.runWith(
        { userId: expectedUserId },
        () => service.getCatForUser()
      )

      expect(cat.userId).toEqual(expectedUserId)
    })
  })
})
```

#### Thông tin thêm <a id="more-information"></a>

Hãy truy cập [trang GitHub của nestjs-cls](https://github.com/Papooch/nestjs-cls) để xem đầy đủ tài liệu API và thêm các ví dụ code.
