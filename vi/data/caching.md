### Caching

Caching là một **kỹ thuật** đơn giản mà hiệu quả để cải thiện hiệu năng của ứng dụng. Cache đóng vai trò một tầng lưu trữ tạm thời giúp truy cập nhanh những dữ liệu hay dùng, để bạn không phải lấy hoặc tính toán lại cùng một thông tin nhiều lần. Kết quả là thời gian phản hồi nhanh hơn và hiệu quả tổng thể tốt hơn.

#### Cài đặt <a id="installation"></a>

Để bắt đầu với caching trong Nest, hãy cài package `@nestjs/cache-manager` cùng với package `cache-manager`:

```bash
$ npm install @nestjs/cache-manager cache-manager
```

Mặc định, mọi thứ được lưu trong bộ nhớ. Vì bên dưới `cache-manager` dùng [Keyv](https://keyv.org/docs/), bạn có thể chuyển sang một giải pháp lưu trữ khác, như Redis, bằng cách cài package tương ứng. Xem phần [Dùng cache store khác](/data/caching#using-alternative-cache-stores) bên dưới.

#### Cache trong bộ nhớ <a id="in-memory-cache"></a>

Để bật caching trong ứng dụng, hãy import `CacheModule` và cấu hình nó bằng method `register()`:

```typescript
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';
import { AppController } from './app.controller.js';

@Module({
  imports: [CacheModule.register()],
  controllers: [AppController],
})
export class AppModule {}
```

Thiết lập này khởi tạo caching trong bộ nhớ với các thiết lập mặc định, để bạn có thể bắt đầu cache dữ liệu ngay lập tức.

#### Tương tác với cache store <a id="interacting-with-the-cache-store"></a>

Để tương tác với instance cache manager, hãy inject nó vào class bằng token `CACHE_MANAGER`, như sau:

```typescript
constructor(@Inject(CACHE_MANAGER) private cacheManager: Cache) {}
```

> info **Gợi ý** Class `Cache` và token `CACHE_MANAGER` đều được import từ package `@nestjs/cache-manager`.

Dùng method `get()` của instance `Cache` (từ package `cache-manager`) để lấy các mục từ cache. Nếu mục không tồn tại trong cache, `get()` trả về `undefined` (`cache-manager` v6 thì trả về `null`). Hãy xem cả hai đều là cache miss khi chuyển đổi phiên bản.

```typescript
const value = await this.cacheManager.get('key');
```

Để thêm một mục vào cache, dùng method `set()`:

```typescript
await this.cacheManager.set('key', 'value');
```

> warning **Lưu ý** Store trong bộ nhớ mặc định giữ tham chiếu tới giá trị thay vì một bản sao: `get()` trả về chính object đã được truyền vào `set()`, nên thay đổi object đó sau này cũng sẽ thay đổi mục trong cache. Hãy xem các giá trị trong cache là chỉ đọc, hoặc copy giá trị trước khi thay đổi. Các store Keyv trong phần [Dùng cache store khác](/data/caching#using-alternative-cache-stores) thì serialize giá trị thành JSON, nên instance của class sẽ trở lại dưới dạng object thuần và object `Date` sẽ trở lại dưới dạng chuỗi.

Bạn có thể chỉ định TTL (thời gian hết hạn tính bằng mili giây) cho một key cụ thể, như sau:

```typescript
await this.cacheManager.set('key', 'value', 1000);
```

Ở đây, mục trong cache sẽ hết hạn sau một giây.

Để lưu một mục không bao giờ hết hạn, truyền TTL là `0`:

```typescript
await this.cacheManager.set('key', 'value', 0);
```

Để xóa một mục khỏi cache, dùng method `del()`:

```typescript
await this.cacheManager.del('key');
```

Để xóa toàn bộ cache, dùng method `clear()`:

```typescript
await this.cacheManager.clear();
```

#### Tự động cache response <a id="auto-caching-responses"></a>

> warning **Cảnh báo** Trong ứng dụng [GraphQL](/graphql/quick-start), interceptor được thực thi riêng cho mỗi field resolver. Vì vậy, `CacheModule` (vốn dùng interceptor để cache response) không hoạt động đúng ở đó.

Để tự động cache response, hãy bind `CacheInterceptor` ở nơi bạn muốn cache dữ liệu:

```typescript
@Controller()
@UseInterceptors(CacheInterceptor)
export class AppController {
  @Get()
  findAll(): string[] {
    return [];
  }
}
```

> warning **Cảnh báo** Mặc định, chỉ các endpoint `GET` mới được cache (một `@CacheKey()` tường minh trên route handler sẽ bỏ qua bước kiểm tra này). Ngoài ra, các route HTTP inject response object gốc (`@Res()`) không thể dùng `CacheInterceptor`. Xem [map response](/interceptors#response-mapping) để biết thêm chi tiết.

Để giảm boilerplate, bạn có thể bind `CacheInterceptor` cho mọi endpoint ở cấp global:

```typescript
import { Module } from '@nestjs/common';
import { CacheModule, CacheInterceptor } from '@nestjs/cache-manager';
import { AppController } from './app.controller.js';
import { APP_INTERCEPTOR } from '@nestjs/core';

@Module({
  imports: [CacheModule.register()],
  controllers: [AppController],
  providers: [
    {
      provide: APP_INTERCEPTOR,
      useClass: CacheInterceptor,
    },
  ],
})
export class AppModule {}
```

#### Time-to-live (TTL)

Mặc định, `ttl` không được đặt, nên các mục trong cache không bao giờ hết hạn (giống như đặt nó thành `0`). Để chỉ định một [TTL](https://en.wikipedia.org/wiki/Time_to_live) tùy chỉnh, truyền tùy chọn `ttl` vào method `register()`:

```typescript
CacheModule.register({
  ttl: 5000, // milliseconds
});
```

#### Dùng module ở cấp global <a id="use-module-globally"></a>

Để dùng `CacheModule` trong các module khác, bạn cần import nó (như với mọi module Nest). Cách khác là khai báo nó là [global module](/modules#global-modules) bằng cách đặt thuộc tính `isGlobal` của options object thành `true`, như bên dưới. Khi đó, một khi `CacheModule` đã được load trong root module (ví dụ `AppModule`), bạn không cần import nó trong các module khác nữa.

```typescript
CacheModule.register({
  isGlobal: true,
});
```

#### Ghi đè cache global <a id="global-cache-overrides"></a>

Khi `CacheInterceptor` được bind ở cấp global, các mục cache được lưu dưới một key sinh tự động từ URL của request. Bạn có thể ghi đè một số thiết lập cache (`@CacheKey()` và `@CacheTTL()`) cho từng method để tùy biến chiến lược cache cho từng method của controller. Điều này đặc biệt có ý nghĩa khi dùng [các cache store khác nhau](/data/caching#using-alternative-cache-stores).

Bạn cũng có thể áp dụng decorator `@CacheTTL()` lên controller để đặt TTL cho mọi route của nó. Khi có cả thiết lập TTL ở cấp controller lẫn cấp method, thiết lập ở cấp method được ưu tiên.

```typescript
@Controller()
@CacheTTL(5000)
export class AppController {
  @CacheKey('custom_key')
  @CacheTTL(2000)
  findAll(): string[] {
    return [];
  }
}
```

> info **Gợi ý** Các decorator `@CacheKey()` và `@CacheTTL()` được import từ package `@nestjs/cache-manager`.

Bạn có thể dùng decorator `@CacheKey()` có hoặc không có decorator `@CacheTTL()` đi kèm, và ngược lại, để chỉ ghi đè key hoặc chỉ ghi đè TTL. Các thiết lập không bị ghi đè bằng decorator sẽ dùng giá trị mặc định đăng ký với module (xem [Time-to-live (TTL)](/data/caching#time-to-live-ttl)).

#### WebSocket và Microservice <a id="websockets-and-microservices"></a>

Bạn cũng có thể áp dụng `CacheInterceptor` cho WebSocket subscriber và microservice pattern (bất kể transport nào được dùng).

```typescript
@@filename()
@CacheKey('events')
@UseInterceptors(CacheInterceptor)
@SubscribeMessage('events')
handleEvent(client: Client, data: string[]): string[] {
  return [];
}
@@switch
@CacheKey('events')
@UseInterceptors(CacheInterceptor)
@SubscribeMessage('events')
handleEvent(client, data) {
  return [];
}
```

Trong các context này, decorator `@CacheKey()` là bắt buộc: nó chỉ định key dùng để lưu và lấy dữ liệu trong cache. Không có nó, response sẽ không được cache. Ngoài ra, hãy nhớ rằng bạn **không nên cache mọi thứ**. Đừng bao giờ cache những action thực hiện thao tác nghiệp vụ thay vì chỉ truy vấn dữ liệu.

Bạn cũng có thể chỉ định thời gian hết hạn cache (TTL) bằng decorator `@CacheTTL()`, decorator này ghi đè TTL mặc định:

```typescript
@@filename()
@CacheKey('events')
@CacheTTL(1000)
@UseInterceptors(CacheInterceptor)
@SubscribeMessage('events')
handleEvent(client: Client, data: string[]): string[] {
  return [];
}
@@switch
@CacheKey('events')
@CacheTTL(1000)
@UseInterceptors(CacheInterceptor)
@SubscribeMessage('events')
handleEvent(client, data) {
  return [];
}
```

> info **Gợi ý** Trong ứng dụng HTTP, decorator `@CacheTTL()` hoạt động dù có hay không có decorator `@CacheKey()` đi kèm. Trong context WebSocket và microservice, nó không có tác dụng nếu thiếu `@CacheKey()`, vì không có key thì không có gì được cache.

#### Điều chỉnh cách theo dõi <a id="adjust-tracking"></a>

Mặc định, Nest dùng URL của request (trong app HTTP) hoặc cache key đặt qua decorator `@CacheKey()` (trong app WebSocket và microservice) để gắn các bản ghi cache với endpoint của bạn. Đôi khi bạn có thể muốn theo dõi bản ghi dựa trên các yếu tố khác, ví dụ HTTP header (như `Authorization` để nhận diện đúng các endpoint `profile`).

Để làm vậy, hãy tạo một class con của `CacheInterceptor` và ghi đè method `trackBy()`:

```typescript
@Injectable()
class HttpCacheInterceptor extends CacheInterceptor {
  trackBy(context: ExecutionContext): string | undefined {
    return 'key';
  }
}
```

#### Dùng cache store khác <a id="using-alternative-cache-stores"></a>

Để chuyển sang một cache store khác, trước tiên hãy cài package tương ứng. Ví dụ, để dùng Redis, hãy cài package `@keyv/redis`. Ví dụ bên dưới cũng dùng store trong bộ nhớ từ package `cacheable`:

```bash
$ npm install @keyv/redis cacheable
```

Khi đã có những thứ trên, bạn có thể đăng ký `CacheModule` với nhiều store, như bên dưới:

```typescript
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';
import { AppController } from './app.controller.js';
import { createKeyv } from '@keyv/redis';
import { Keyv } from 'keyv';
import { KeyvCacheableMemory } from 'cacheable';

@Module({
  imports: [
    CacheModule.registerAsync({
      useFactory: async () => {
        const redisStore = createKeyv('redis://localhost:6379');
        redisStore.on('error', (err) => console.error('Redis error:', err));

        return {
          stores: [
            new Keyv({
              store: new KeyvCacheableMemory({ ttl: 60000, lruSize: 5000 }),
            }),
            redisStore,
          ],
        };
      },
    }),
  ],
  controllers: [AppController],
})
export class AppModule {}
```

Ví dụ này đăng ký hai store: `CacheableMemory` và một Redis store. `CacheableMemory` là một store trong bộ nhớ tạo bằng storage adapter `KeyvCacheableMemory`, còn Redis store được tạo bằng helper `createKeyv()` từ `@keyv/redis`. Mảng `stores` chỉ định các store bạn muốn dùng. Store đầu tiên trong mảng là store mặc định, các store còn lại là store dự phòng.

> warning **Cảnh báo** Luôn gắn một listener `'error'` cho Redis store, như ở trên. Khi kết nối Redis bị ngắt, store phát ra event `'error'`, và Keyv sẽ throw nếu không có ai lắng nghe event đó, điều này có thể làm crash ứng dụng.

Xem [tài liệu Keyv](https://keyv.org/docs/) để biết thêm thông tin về các store có sẵn.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Có thể bạn muốn truyền tùy chọn module theo kiểu bất đồng bộ thay vì tĩnh lúc compile. Khi đó, hãy dùng method `registerAsync()`, method này cung cấp vài cách để xử lý cấu hình bất đồng bộ.

Một cách là dùng hàm factory:

```typescript
CacheModule.registerAsync({
  useFactory: () => ({
    ttl: 5000,
  }),
});
```

Factory hoạt động giống mọi factory module bất đồng bộ khác: nó có thể là `async` và có thể inject dependency qua `inject`.

```typescript
CacheModule.registerAsync({
  imports: [ConfigModule],
  useFactory: async (configService: ConfigService) => ({
    ttl: configService.get('CACHE_TTL'),
  }),
  inject: [ConfigService],
});
```

Cách khác là dùng cú pháp `useClass`:

```typescript
CacheModule.registerAsync({
  useClass: CacheConfigService,
});
```

Cách khai báo này khởi tạo `CacheConfigService` bên trong `CacheModule` và dùng nó để lấy options object. `CacheConfigService` phải implement interface `CacheOptionsFactory` để cung cấp các tùy chọn cấu hình:

```typescript
@Injectable()
class CacheConfigService implements CacheOptionsFactory {
  createCacheOptions(): CacheModuleOptions {
    return {
      ttl: 5000,
    };
  }
}
```

Để dùng một configuration provider đã có được import từ module khác, hãy dùng cú pháp `useExisting`:

```typescript
CacheModule.registerAsync({
  imports: [ConfigModule],
  useExisting: ConfigService,
});
```

Cách này hoạt động giống `useClass`, với một khác biệt quan trọng: `CacheModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã được tạo thay vì tự khởi tạo cái mới.

> info **Gợi ý** `CacheModule#register`, `CacheModule#registerAsync` và `CacheOptionsFactory` nhận một generic (type argument) tùy chọn để thu hẹp các tùy chọn cấu hình riêng của store, giúp chúng type-safe.

Bạn cũng có thể truyền `extraProviders` vào method `registerAsync()`. Các provider này được merge với các provider của module:

```typescript
CacheModule.registerAsync({
  imports: [ConfigModule],
  useClass: ConfigService,
  extraProviders: [MyAdditionalProvider],
});
```

Điều này hữu ích khi bạn muốn cung cấp thêm dependency cho hàm factory hoặc constructor của class.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn trong [sample cache](https://github.com/nestjs/nest/tree/master/sample/20-cache).
