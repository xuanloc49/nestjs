### Discovery service

`DiscoveryService`, do package `@nestjs/core` cung cấp, cho phép bạn kiểm tra và lấy ra động các provider, controller và metadata của chúng trong một ứng dụng NestJS. Tính năng này đặc biệt hữu ích khi xây dựng plugin, decorator, hoặc các tính năng nâng cao dựa vào introspection lúc runtime, giúp bạn xây dựng các kiến trúc linh hoạt, mô-đun hơn với hành vi tự động và động.

#### Bắt đầu <a id="getting-started"></a>

Trước khi dùng `DiscoveryService`, hãy import `DiscoveryModule` vào module nơi bạn định dùng nó. Việc này giúp service có sẵn để dependency injection:

```typescript
import { Module } from '@nestjs/common';
import { DiscoveryModule } from '@nestjs/core';
import { ExampleService } from './example.service.js';

@Module({
  imports: [DiscoveryModule],
  providers: [ExampleService],
})
export class ExampleModule {}
```

Khi đã thiết lập module, bạn có thể inject `DiscoveryService` vào bất kỳ provider nào cần khả năng khám phá động:

```typescript
@@filename(example.service)
@Injectable()
export class ExampleService {
  constructor(private readonly discoveryService: DiscoveryService) {}
}
@@switch
@Injectable()
@Dependencies(DiscoveryService)
export class ExampleService {
  constructor(discoveryService) {
    this.discoveryService = discoveryService;
  }
}
```

#### Khám phá provider và controller <a id="discovering-providers-and-controllers"></a>

Một khả năng quan trọng của `DiscoveryService` là lấy ra mọi provider đã đăng ký trong ứng dụng, hữu ích để xử lý động các provider dựa trên những điều kiện cụ thể. Đoạn code sau lấy ra mọi provider:

```typescript
const providers = this.discoveryService.getProviders();
console.log(providers);
```

Mỗi object trả về là một `InstanceWrapper`, chứa các thông tin như instance, token và class (`metatype`) của provider. Tương tự, để lấy mọi controller đã đăng ký trong ứng dụng, dùng:

```typescript
const controllers = this.discoveryService.getControllers();
console.log(controllers);
```

Điều này hữu ích khi cần xử lý động các controller, ví dụ để theo dõi analytics hoặc cho các cơ chế đăng ký tự động.

Cả hai method đều nhận một options object tùy chọn. Truyền vào một mảng `include` chứa các class module để giới hạn việc khám phá trong những module đó:

```typescript
const providers = this.discoveryService.getProviders({
  include: [CatsModule],
});
```

#### Lấy metadata <a id="extracting-metadata"></a>

Ngoài việc khám phá provider và controller, `DiscoveryService` còn lấy được metadata gắn trên các thành phần này. Điều này đặc biệt có giá trị khi làm việc với custom decorator lưu metadata lúc runtime.

Ví dụ, xét một custom decorator dùng để gắn tag metadata cụ thể cho provider:

```typescript
import { DiscoveryService } from '@nestjs/core';

export const FeatureFlag = DiscoveryService.createDecorator();
```

Áp dụng decorator này lên một service sẽ lưu metadata để truy vấn sau:

```typescript
import { Injectable } from '@nestjs/common';
import { FeatureFlag } from './custom-metadata.decorator.js';

@Injectable()
@FeatureFlag('experimental')
export class CustomService {}
```

Khi metadata đã được gắn vào provider theo cách này, bạn có thể dùng `DiscoveryService` để lọc provider dựa trên metadata đã gán. Đoạn code sau lấy ra một provider được gắn tag với một giá trị metadata cụ thể:

```typescript
const providers = this.discoveryService.getProviders();

const [provider] = providers.filter(
  (item) =>
    this.discoveryService.getMetadataByDecorator(FeatureFlag, item) ===
    'experimental',
);

console.log(
  'Providers with the "experimental" feature flag metadata:',
  provider,
);
```

Decorator tạo bằng `DiscoveryService.createDecorator()` cũng đăng ký luôn các class mà nó decorate, nên bạn có thể chỉ lấy ra những class đó bằng cách truyền `KEY` của decorator vào tùy chọn `metadataKey`, thay vì tự lọc toàn bộ provider:

```typescript
const providers = this.discoveryService.getProviders({
  metadataKey: FeatureFlag.KEY,
});
```

Cùng một decorator cũng có thể áp dụng lên method. Để đọc metadata ở cấp method, truyền tên method làm tham số thứ ba cho `getMetadataByDecorator()`.

#### Tổng kết <a id="conclusion"></a>

`DiscoveryService` mở ra khả năng introspection lúc runtime trong ứng dụng NestJS. Bằng cách khám phá động các provider, controller và metadata của chúng, nó đóng vai trò viên gạch nền cho các framework mở rộng được, plugin và các tính năng dựa trên tự động hóa, dù bạn cần quét và xử lý provider, lấy metadata để xử lý tiếp, hay xây dựng kiến trúc mô-đun.
