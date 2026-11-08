### Lazy loading module

Mặc định, module được load sớm (eager): ngay khi ứng dụng load, mọi module cũng được load theo, dù có cần dùng ngay hay không. Điều này ổn với hầu hết ứng dụng, nhưng có thể trở thành nút thắt cổ chai với các app và worker chạy trong **môi trường serverless**, nơi độ trễ khởi động ("cold start") là yếu tố then chốt.

Lazy loading có thể giảm thời gian bootstrap bằng cách chỉ load những module cần thiết cho một lần gọi serverless function cụ thể. Bạn cũng có thể load các module khác theo kiểu bất đồng bộ khi serverless function đã "warm", để tăng tốc thời gian bootstrap hơn nữa cho các lần gọi tiếp theo (đăng ký module trì hoãn).

> info **Gợi ý** Nếu bạn quen với framework **[Angular](https://angular.dev/)**, có thể bạn đã từng thấy thuật ngữ "[lazy-loading module](https://angular.dev/guide/ngmodules/lazy-loading#lazy-loading-basics)". Kỹ thuật này trong Nest **khác về mặt chức năng**, nên hãy xem nó như một tính năng hoàn toàn khác, chỉ tình cờ có tên giống nhau.

> warning **Cảnh báo** Các [method lifecycle hook](/fundamentals/lifecycle-events) không được gọi trong các module và service được lazy load.

#### Bắt đầu <a id="getting-started"></a>

Để load module theo nhu cầu, Nest cung cấp class `LazyModuleLoader`, bạn inject nó vào class giống như mọi dependency khác:

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(private lazyModuleLoader: LazyModuleLoader) {}
}
@@switch
@Injectable()
@Dependencies(LazyModuleLoader)
export class CatsService {
  constructor(lazyModuleLoader) {
    this.lazyModuleLoader = lazyModuleLoader;
  }
}
```

> info **Gợi ý** Class `LazyModuleLoader` được import từ package `@nestjs/core`.

Cách khác là lấy tham chiếu tới provider `LazyModuleLoader` từ file bootstrap của ứng dụng (`main.ts`):

```typescript
// "app" represents a Nest application instance
const lazyModuleLoader = app.get(LazyModuleLoader);
```

Khi đã có nó, bạn có thể load bất kỳ module nào bằng cách sau:

```typescript
const { LazyModule } = await import('./lazy.module.js');
const moduleRef = await this.lazyModuleLoader.load(() => LazyModule);
```

> info **Gợi ý** Module được lazy load sẽ được **cache** ở lần gọi method `LazyModuleLoader#load` đầu tiên. Vì vậy, mỗi lần load `LazyModule` tiếp theo sẽ **rất nhanh** và trả về instance đã cache thay vì load lại module.
>
> ```bash
> Load "LazyModule" attempt: 1
> time: 2.379ms
> Load "LazyModule" attempt: 2
> time: 0.294ms
> Load "LazyModule" attempt: 3
> time: 0.303ms
> ```
>
> Ngoài ra, module được lazy load dùng chung module graph với các module được load sớm lúc bootstrap ứng dụng, cũng như với mọi lazy module khác được đăng ký sau đó trong app.

Ở đây, `lazy.module.ts` là một file TypeScript export một **module Nest thông thường** (không cần thay đổi gì thêm).

Method `LazyModuleLoader#load` trả về [module reference](/fundamentals/module-ref) (của `LazyModule`), cho phép bạn duyệt danh sách provider nội bộ và lấy tham chiếu tới bất kỳ provider nào, dùng injection token của nó làm khóa tra cứu.

> info **Gợi ý** Method `load()` nhận một tham số thứ hai (tùy chọn) là options object. Đặt thuộc tính `logger` của nó thành `false` để tắt các log mà Nest sinh ra trong lúc load module.

Ví dụ, giả sử ta có một `LazyModule` với định nghĩa sau:

```typescript
@Module({
  providers: [LazyService],
  exports: [LazyService],
})
export class LazyModule {}
```

> info **Gợi ý** Module được lazy load không thể đăng ký làm **global module**, vì chúng được đăng ký muộn, theo nhu cầu, sau khi tất cả các module đăng ký tĩnh đã được khởi tạo. Tương tự, các **global enhancer** đã đăng ký (guard, interceptor, v.v.) cũng **sẽ không hoạt động** đúng.

Với điều này, ta có thể lấy tham chiếu tới provider `LazyService`:

```typescript
const { LazyModule } = await import('./lazy.module.js');
const moduleRef = await this.lazyModuleLoader.load(() => LazyModule);

const { LazyService } = await import('./lazy.service.js');
const lazyService = moduleRef.get(LazyService);
```

> warning **Cảnh báo** Nếu bạn dùng **webpack**, hãy cập nhật file `tsconfig.json`: đặt `compilerOptions.module` thành `"esnext"` và thêm thuộc tính `compilerOptions.moduleResolution` với giá trị `"node"`:
>
> ```json
> {
>   "compilerOptions": {
>     "module": "esnext",
>     "moduleResolution": "node",
>     ...
>   }
> }
> ```
>
> Khi đã đặt các tùy chọn này, bạn có thể dùng tính năng [code splitting](https://webpack.js.org/guides/code-splitting/) của webpack.

#### Lazy load controller, gateway và resolver <a id="lazy-loading-controllers-gateways-and-resolvers"></a>

Vì controller (hoặc resolver, trong ứng dụng GraphQL) trong Nest đại diện cho tập hợp các route, path hoặc topic (hoặc query và mutation), bạn **không thể lazy load chúng** bằng class `LazyModuleLoader`.

> error **Cảnh báo** Controller, [resolver](/graphql/resolvers) và [gateway](/websockets/gateways) đăng ký bên trong module được lazy load sẽ không hoạt động như mong đợi. Tương tự, bạn không thể đăng ký middleware (bằng cách implement method `configure()` của interface `NestModule` với `MiddlewareConsumer`) theo nhu cầu.

Ví dụ, giả sử bạn đang xây dựng một REST API (ứng dụng HTTP) chạy Fastify bên dưới (dùng package `@nestjs/platform-fastify`). Fastify không cho phép đăng ký route sau khi ứng dụng đã sẵn sàng và đang lắng nghe. Vì vậy, kể cả khi Nest có phân tích các route mapping đăng ký trong controller của module, các route được lazy load vẫn không truy cập được, vì không có cách nào đăng ký chúng lúc runtime.

Tương tự, một số transport strategy do package `@nestjs/microservices` cung cấp (bao gồm Kafka, gRPC và RabbitMQ) phải subscribe vào các topic hoặc channel cụ thể trước khi kết nối được thiết lập. Một khi ứng dụng đã bắt đầu lắng nghe message, framework không thể subscribe thêm topic mới.

Cuối cùng, package `@nestjs/graphql`, khi bật cách tiếp cận code first, sẽ sinh GraphQL schema ngay lúc chạy dựa trên metadata. Việc này yêu cầu mọi class phải được load trước; nếu không, nó không thể tạo ra một schema hợp lệ.

#### Các trường hợp sử dụng phổ biến <a id="common-use-cases"></a>

Lazy loading module thường gặp nhất khi một worker, cron job, lambda hay serverless function khác, hoặc webhook phải kích hoạt các service khác nhau (logic khác nhau) tùy theo tham số đầu vào (route path, ngày, query parameter, v.v.). Lazy loading module ít có ý nghĩa với các ứng dụng monolithic, nơi thời gian khởi động gần như không quan trọng.
