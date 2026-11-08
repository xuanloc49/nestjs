### Module reference

Nest cung cấp class `ModuleRef` để duyệt danh sách provider nội bộ và lấy tham chiếu tới bất kỳ provider nào, dùng injection token của nó làm khóa tra cứu. `ModuleRef` cũng cho phép bạn khởi tạo động cả provider tĩnh lẫn provider có scope. Inject `ModuleRef` vào class giống như mọi dependency khác:

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(private moduleRef: ModuleRef) {}
}
@@switch
@Injectable()
@Dependencies(ModuleRef)
export class CatsService {
  constructor(moduleRef) {
    this.moduleRef = moduleRef;
  }
}
```

> info **Gợi ý** Class `ModuleRef` được import từ package `@nestjs/core`.

#### Lấy instance <a id="retrieving-instances"></a>

Instance `ModuleRef` (từ đây gọi là **module reference**) có method `get()`. Mặc định, method này dùng injection token hoặc tên class để trả về một provider, controller hoặc injectable (ví dụ guard hay interceptor) đã được đăng ký và khởi tạo trong *module hiện tại*. Nếu không tìm thấy instance, một exception sẽ được throw.

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService implements OnModuleInit {
  private service: Service;
  constructor(private moduleRef: ModuleRef) {}

  onModuleInit() {
    this.service = this.moduleRef.get(Service);
  }
}
@@switch
@Injectable()
@Dependencies(ModuleRef)
export class CatsService {
  constructor(moduleRef) {
    this.moduleRef = moduleRef;
  }

  onModuleInit() {
    this.service = this.moduleRef.get(Service);
  }
}
```

> warning **Cảnh báo** Bạn không thể lấy provider có scope (transient hoặc request-scoped, kể cả những provider ngầm là request-scoped thông qua dependency của chúng) bằng method `get()`. Thay vào đó, hãy dùng kỹ thuật mô tả trong <a href="/fundamentals/module-ref#resolving-scoped-providers">Resolve provider có scope</a> bên dưới. Tìm hiểu cách điều khiển scope trong chương [injection scope](/fundamentals/injection-scopes).

Để lấy provider từ context toàn cục (ví dụ khi provider được đăng ký ở một module khác), truyền tùy chọn `{{ '{' }} strict: false {{ '}' }}` làm tham số thứ hai cho `get()`.

```typescript
this.moduleRef.get(Service, { strict: false });
```

#### Resolve provider có scope <a id="resolving-scoped-providers"></a>

Để resolve động một provider có scope (transient hoặc request-scoped), dùng method `resolve()`, truyền injection token của provider làm tham số.

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService implements OnModuleInit {
  private transientService: TransientService;
  constructor(private moduleRef: ModuleRef) {}

  async onModuleInit() {
    this.transientService = await this.moduleRef.resolve(TransientService);
  }
}
@@switch
@Injectable()
@Dependencies(ModuleRef)
export class CatsService {
  constructor(moduleRef) {
    this.moduleRef = moduleRef;
  }

  async onModuleInit() {
    this.transientService = await this.moduleRef.resolve(TransientService);
  }
}
```

Method `resolve()` trả về một instance duy nhất của provider từ **DI container sub-tree** riêng của nó. Mỗi sub-tree có một **context identifier** duy nhất, nên nếu bạn gọi method này nhiều lần và so sánh tham chiếu instance, bạn sẽ thấy chúng không bằng nhau.

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService implements OnModuleInit {
  constructor(private moduleRef: ModuleRef) {}

  async onModuleInit() {
    const transientServices = await Promise.all([
      this.moduleRef.resolve(TransientService),
      this.moduleRef.resolve(TransientService),
    ]);
    console.log(transientServices[0] === transientServices[1]); // false
  }
}
@@switch
@Injectable()
@Dependencies(ModuleRef)
export class CatsService {
  constructor(moduleRef) {
    this.moduleRef = moduleRef;
  }

  async onModuleInit() {
    const transientServices = await Promise.all([
      this.moduleRef.resolve(TransientService),
      this.moduleRef.resolve(TransientService),
    ]);
    console.log(transientServices[0] === transientServices[1]); // false
  }
}
```

Để có cùng một instance qua nhiều lần gọi `resolve()`, và đảm bảo chúng dùng chung một DI container sub-tree được sinh ra, hãy truyền một context identifier vào method `resolve()`. Dùng class `ContextIdFactory` để sinh context identifier: method `create()` của nó trả về một định danh duy nhất mới.

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService implements OnModuleInit {
  constructor(private moduleRef: ModuleRef) {}

  async onModuleInit() {
    const contextId = ContextIdFactory.create();
    const transientServices = await Promise.all([
      this.moduleRef.resolve(TransientService, contextId),
      this.moduleRef.resolve(TransientService, contextId),
    ]);
    console.log(transientServices[0] === transientServices[1]); // true
  }
}
@@switch
@Injectable()
@Dependencies(ModuleRef)
export class CatsService {
  constructor(moduleRef) {
    this.moduleRef = moduleRef;
  }

  async onModuleInit() {
    const contextId = ContextIdFactory.create();
    const transientServices = await Promise.all([
      this.moduleRef.resolve(TransientService, contextId),
      this.moduleRef.resolve(TransientService, contextId),
    ]);
    console.log(transientServices[0] === transientServices[1]); // true
  }
}
```

> info **Gợi ý** Class `ContextIdFactory` được import từ package `@nestjs/core`.

#### Đăng ký provider `REQUEST` <a id="registering-request-provider"></a>

Các context identifier sinh thủ công (tạo bằng `ContextIdFactory.create()`) đại diện cho những DI sub-tree trong đó provider `REQUEST` là `undefined`, vì các sub-tree này không được hệ thống dependency injection của Nest khởi tạo và quản lý.

Để đăng ký một object `REQUEST` tùy chỉnh cho một DI sub-tree tạo thủ công, dùng method `ModuleRef#registerRequestByContextId()`:

```typescript
const contextId = ContextIdFactory.create();
this.moduleRef.registerRequestByContextId(/* YOUR_REQUEST_OBJECT */, contextId);
```

#### Lấy sub-tree hiện tại <a id="getting-current-sub-tree"></a>

Đôi khi, bạn có thể muốn resolve một instance của request-scoped provider bên trong một **request context**. Giả sử `CatsService` là request-scoped, và bạn muốn resolve instance `CatsRepository`, cũng là một request-scoped provider. Để dùng chung DI container sub-tree, bạn phải lấy context identifier hiện tại thay vì sinh ra một cái mới (ví dụ bằng hàm `ContextIdFactory.create()` như ở trên). Để lấy context identifier hiện tại, trước tiên hãy inject request object bằng decorator `@Inject()`:

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(
    @Inject(REQUEST) private request: Record<string, unknown>,
  ) {}
}
@@switch
@Injectable()
@Dependencies(REQUEST)
export class CatsService {
  constructor(request) {
    this.request = request;
  }
}
```

> info **Gợi ý** Tìm hiểu thêm về request provider trong phần [Request provider](/fundamentals/injection-scopes#request-provider) của chương injection scope.

Giờ hãy dùng method `getByRequest()` của class `ContextIdFactory` để lấy context identifier gắn với request object, rồi truyền nó vào lời gọi `resolve()`:

```typescript
const contextId = ContextIdFactory.getByRequest(this.request);
const catsRepository = await this.moduleRef.resolve(CatsRepository, contextId);
```

#### Khởi tạo động class tùy chỉnh <a id="instantiating-custom-classes-dynamically"></a>

Để khởi tạo động một class **chưa từng được đăng ký** làm **provider**, dùng method `create()` của module reference:

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService implements OnModuleInit {
  private catsFactory: CatsFactory;
  constructor(private moduleRef: ModuleRef) {}

  async onModuleInit() {
    this.catsFactory = await this.moduleRef.create(CatsFactory);
  }
}
@@switch
@Injectable()
@Dependencies(ModuleRef)
export class CatsService {
  constructor(moduleRef) {
    this.moduleRef = moduleRef;
  }

  async onModuleInit() {
    this.catsFactory = await this.moduleRef.create(CatsFactory);
  }
}
```

Kỹ thuật này cho phép bạn khởi tạo có điều kiện các class khác nhau bên ngoài container của framework.

<app-banner-observe></app-banner-observe>
