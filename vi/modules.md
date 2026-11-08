### Modules

Module là một class được đánh dấu bằng decorator `@Module()`. Decorator này cung cấp metadata mà **Nest** dùng để tổ chức và quản lý cấu trúc ứng dụng.

<figure><img class="illustrative-image" src="/assets/Modules_1.png" /></figure>

Mọi ứng dụng Nest đều có ít nhất một module, đó là **root module**. Đây là điểm xuất phát để Nest xây dựng **application graph**, cấu trúc nội bộ mà Nest dùng để resolve mối quan hệ và dependency giữa các module và provider. Một ứng dụng rất nhỏ có thể chỉ có root module, nhưng hầu hết ứng dụng đều có nhiều module, mỗi module đóng gói một nhóm **chức năng** liên quan chặt chẽ với nhau. Module là cách **được khuyên dùng** để tổ chức các thành phần của bạn.

Decorator `@Module()` nhận một object duy nhất với các thuộc tính mô tả module:

|               |                                                                                                                                                                         |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `providers`   | các provider sẽ được Nest injector khởi tạo và có thể được chia sẻ ít nhất trong phạm vi module này                                                                     |
| `controllers` | tập các controller định nghĩa trong module này cần được khởi tạo                                                                                                        |
| `imports`     | danh sách các module được import, export ra các provider mà module này cần                                                                                              |
| `exports`     | tập con của `providers` mà module này cung cấp và cho phép các module khác import nó sử dụng. Bạn có thể dùng chính provider hoặc token của nó (giá trị `provide`)       |

Mặc định, module **đóng gói** các provider của nó: bạn chỉ có thể inject những provider thuộc module hiện tại hoặc được export tường minh từ một module đã import. Các provider được export của một module tạo thành public interface, hay API, của module đó.

#### Feature module <a id="feature-modules"></a>

Trong ví dụ của chúng ta, `CatsController` và `CatsService` liên quan chặt chẽ và phục vụ cùng một domain của ứng dụng, nên gom chúng vào một feature module là hợp lý. Feature module tổ chức code cho một tính năng cụ thể, giúp ranh giới giữa các phần luôn rõ ràng. Điều này càng quan trọng khi ứng dụng hoặc team lớn dần, và nó phù hợp với các nguyên tắc [SOLID](https://en.wikipedia.org/wiki/SOLID).

Tiếp theo, ta sẽ tạo `CatsModule` để gom controller và service lại:

```typescript
@@filename(cats/cats.module)
import { Module } from '@nestjs/common';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

@Module({
  controllers: [CatsController],
  providers: [CatsService],
})
export class CatsModule {}
```

> info **Gợi ý** Để tạo module bằng CLI, chạy `$ nest g module cats`.

Ở trên, ta đã định nghĩa `CatsModule` trong file `cats.module.ts` và chuyển mọi thứ liên quan đến nó vào thư mục `cats`. Bước cuối cùng là import module này vào root module (`AppModule`, định nghĩa trong file `app.module.ts`):

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { CatsModule } from './cats/cats.module.js';

@Module({
  imports: [CatsModule],
})
export class AppModule {}
```

Cấu trúc thư mục lúc này trông như sau:

<div class="file-tree">
  <div class="item">src</div>
  <div class="children">
    <div class="item">cats</div>
    <div class="children">
      <div class="item">dto</div>
      <div class="children">
        <div class="item">create-cat.dto.ts</div>
      </div>
      <div class="item">interfaces</div>
      <div class="children">
        <div class="item">cat.interface.ts</div>
      </div>
      <div class="item">cats.controller.ts</div>
      <div class="item">cats.module.ts</div>
      <div class="item">cats.service.ts</div>
    </div>
    <div class="item">app.module.ts</div>
    <div class="item">main.ts</div>
  </div>
</div>

#### Shared module <a id="shared-modules"></a>

Trong Nest, module mặc định là **singleton**, nên bạn có thể chia sẻ cùng một instance của bất kỳ provider nào giữa nhiều module.

<figure><img class="illustrative-image" src="/assets/Shared_Module_1.png" /></figure>

Mọi module đều tự động là **shared module**: một khi đã được tạo, nó có thể được tái sử dụng bởi bất kỳ module nào khác. Giả sử bạn muốn chia sẻ một instance của `CatsService` cho vài module khác. Để làm vậy, trước tiên hãy **export** provider `CatsService` bằng cách thêm nó vào mảng `exports` của module:

```typescript
@@filename(cats.module)
import { Module } from '@nestjs/common';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

@Module({
  controllers: [CatsController],
  providers: [CatsService],
  exports: [CatsService],
})
export class CatsModule {}
```

Giờ thì mọi module import `CatsModule` đều truy cập được `CatsService`, và dùng chung một instance với tất cả các module khác cũng import nó.

Đăng ký trực tiếp `CatsService` trong từng module cần đến nó cũng chạy được, nhưng khi đó mỗi module sẽ có một instance riêng của service. Nhiều instance làm tăng lượng bộ nhớ sử dụng và có thể gây ra hành vi không mong muốn, chẳng hạn state không nhất quán nếu service giữ state nội bộ.

Đóng gói `CatsService` trong một module như `CatsModule` rồi export nó ra đảm bảo rằng mọi module import `CatsModule` đều dùng lại cùng một instance. Cách này giảm tiêu thụ bộ nhớ và giúp hành vi dễ đoán hơn, vì state và resource dùng chung được quản lý ở một chỗ. Chia sẻ service hiệu quả trong toàn ứng dụng là một trong những lợi ích chính của việc module hóa và dependency injection.

<app-banner-observe></app-banner-observe>

#### Re-export module <a id="module-re-exporting"></a>

Như đã thấy ở trên, module có thể export các provider nội bộ của nó. Module cũng có thể re-export các module mà nó import. Trong ví dụ dưới đây, `CommonModule` vừa được import vào **vừa** được export ra từ `CoreModule`, nhờ đó bất kỳ module nào import `CoreModule` cũng dùng được nó.

```typescript
@Module({
  imports: [CommonModule],
  exports: [CommonModule],
})
export class CoreModule {}
```

#### Dependency injection

Bản thân class module cũng có thể **inject** provider (ví dụ cho mục đích cấu hình):

```typescript
@@filename(cats.module)
import { Module } from '@nestjs/common';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

@Module({
  controllers: [CatsController],
  providers: [CatsService],
})
export class CatsModule {
  constructor(private catsService: CatsService) {}
}
@@switch
import { Module, Dependencies } from '@nestjs/common';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

@Module({
  controllers: [CatsController],
  providers: [CatsService],
})
@Dependencies(CatsService)
export class CatsModule {
  constructor(catsService) {
    this.catsService = catsService;
  }
}
```

Tuy nhiên, chính các class module lại không thể được inject như provider, do vấn đề [circular dependency](/fundamentals/circular-dependency).

#### Global module <a id="global-modules"></a>

Phải import cùng một nhóm module ở khắp nơi có thể trở nên nhàm chán. Trong [Angular](https://angular.dev), `providers` được đăng ký ở scope toàn cục và một khi đã định nghĩa thì dùng được ở mọi nơi. Ngược lại, Nest đóng gói provider bên trong scope của module: bạn không thể dùng provider của một module ở nơi khác nếu chưa import module đóng gói chúng.

Để một nhóm provider có sẵn ở mọi nơi (ví dụ helper hoặc kết nối database), hãy biến module thành **global** bằng decorator `@Global()`:

```typescript
import { Module, Global } from '@nestjs/common';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';

@Global()
@Module({
  controllers: [CatsController],
  providers: [CatsService],
  exports: [CatsService],
})
export class CatsModule {}
```

Decorator `@Global()` biến module thành global scope. Hãy đăng ký global module **chỉ một lần**, thường là trong root module hoặc core module. Trong ví dụ trên, provider `CatsService` có sẵn ở mọi nơi, và các module inject nó không cần thêm `CatsModule` vào mảng `imports`.

> info **Gợi ý** Biến mọi thứ thành global không phải là cách thiết kế được khuyên dùng. Global module giúp giảm boilerplate, nhưng mảng `imports` cho phép API của một module được cung cấp cho các module khác một cách có kiểm soát và tường minh. Điều này giúp cấu trúc ứng dụng dễ bảo trì, chỉ chia sẻ những phần của module mà nơi khác thực sự cần, và tránh việc các phần không liên quan của ứng dụng bị ràng buộc vào nhau một cách không cần thiết.

#### Dynamic module <a id="dynamic-modules"></a>

Dynamic module cho phép bạn tạo những module được cấu hình lúc runtime. Chúng hữu ích khi provider của một module phụ thuộc vào các tùy chọn do module import nó truyền vào. Ví dụ, `FeatureFlagsModule` dưới đây nhận các feature flag của ứng dụng thông qua method static `forRoot()`:

```typescript
@@filename(feature-flags.module)
import { DynamicModule, Module } from '@nestjs/common';
import { FEATURE_FLAGS } from './feature-flags.constants.js';
import { FeatureFlagsService } from './feature-flags.service.js';

@Module({
  providers: [FeatureFlagsService],
  exports: [FeatureFlagsService],
})
export class FeatureFlagsModule {
  static forRoot(flags: Record<string, boolean>): DynamicModule {
    return {
      module: FeatureFlagsModule,
      providers: [{ provide: FEATURE_FLAGS, useValue: flags }],
    };
  }
}
@@switch
import { Module } from '@nestjs/common';
import { FEATURE_FLAGS } from './feature-flags.constants.js';
import { FeatureFlagsService } from './feature-flags.service.js';

@Module({
  providers: [FeatureFlagsService],
  exports: [FeatureFlagsService],
})
export class FeatureFlagsModule {
  static forRoot(flags) {
    return {
      module: FeatureFlagsModule,
      providers: [{ provide: FEATURE_FLAGS, useValue: flags }],
    };
  }
}
```

Injection token `FEATURE_FLAGS` là một hằng số thông thường (`export const FEATURE_FLAGS = 'FEATURE_FLAGS';`), như mô tả trong [Token provider không dựa trên class](/fundamentals/custom-providers#non-class-based-provider-tokens).

> info **Gợi ý** Method `forRoot()` có thể trả về dynamic module theo kiểu đồng bộ hoặc bất đồng bộ (tức là qua một `Promise`).

Các thuộc tính mà `forRoot()` trả về sẽ **mở rộng** (chứ không ghi đè) metadata định nghĩa trong decorator `@Module()`. Vì vậy, module cuối cùng có cả `FeatureFlagsService` được khai báo tĩnh lẫn provider `FEATURE_FLAGS` được đăng ký động. Vì chúng thuộc cùng một module, service có thể inject các flag này:

```typescript
@@filename(feature-flags.service)
import { Inject, Injectable } from '@nestjs/common';
import { FEATURE_FLAGS } from './feature-flags.constants.js';

@Injectable()
export class FeatureFlagsService {
  constructor(
    @Inject(FEATURE_FLAGS) private readonly flags: Record<string, boolean>,
  ) {}

  isEnabled(flag: string): boolean {
    return this.flags[flag] ?? false;
  }
}
@@switch
import { Dependencies, Injectable } from '@nestjs/common';
import { FEATURE_FLAGS } from './feature-flags.constants.js';

@Injectable()
@Dependencies(FEATURE_FLAGS)
export class FeatureFlagsService {
  constructor(flags) {
    this.flags = flags;
  }

  isEnabled(flag) {
    return this.flags[flag] ?? false;
  }
}
```

Module chỉ export `FeatureFlagsService`, nên bản thân các flag vẫn là chi tiết implementation bên trong module.

Import và cấu hình `FeatureFlagsModule` như sau:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { FeatureFlagsModule } from './feature-flags/feature-flags.module.js';

@Module({
  imports: [
    FeatureFlagsModule.forRoot({
      newCheckout: true,
      betaDashboard: false,
    }),
  ],
})
export class AppModule {}
```

Chỉ module nào import `FeatureFlagsModule.forRoot()` mới inject được `FeatureFlagsService`. Gọi `forRoot()` thêm lần nữa trong một module khác sẽ tạo ra instance thứ hai, được cấu hình riêng. Để dùng chung một instance, hãy cấu hình module một lần rồi re-export nó. Để re-export một dynamic module, liệt kê class module trong mảng `exports`, không cần gọi lại `forRoot()`:

```typescript
@@filename(core.module)
import { Module } from '@nestjs/common';
import { FeatureFlagsModule } from '../feature-flags/feature-flags.module.js';

@Module({
  imports: [
    FeatureFlagsModule.forRoot({
      newCheckout: true,
      betaDashboard: false,
    }),
  ],
  exports: [FeatureFlagsModule],
})
export class CoreModule {}
```

Giờ thì mọi module import `CoreModule` đều inject được `FeatureFlagsService`, và tất cả dùng chung một bộ flag.

Cách khác, để đăng ký dynamic module ở global scope, đặt thuộc tính `global` thành `true` trong object mà `forRoot()` trả về. Khi đó `FeatureFlagsService` sẽ inject được ở mọi nơi mà không cần import module nào:

```typescript
return {
  global: true,
  module: FeatureFlagsModule,
  providers: [{ provide: FEATURE_FLAGS, useValue: flags }],
};
```

> warning **Cảnh báo** Như đã nói ở trên, biến mọi thứ thành global **không phải là một quyết định thiết kế tốt**.

Những tùy chọn chỉ biết được lúc runtime, như giá trị đọc từ `ConfigService`, cần đến biến thể bất đồng bộ của `forRoot()`. Chương [Dynamic module](/fundamentals/dynamic-modules) trình bày chi tiết phần này và nhiều hơn nữa.

> info **Gợi ý** Để tìm hiểu cách xây dựng các dynamic module có khả năng tùy biến cao với `ConfigurableModuleBuilder`, xem phần [Configurable module builder](/fundamentals/dynamic-modules#configurable-module-builder).
