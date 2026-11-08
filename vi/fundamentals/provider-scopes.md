### Injection scope

Nếu bạn đến từ một ngôn ngữ lập trình khác, có thể bạn sẽ bất ngờ khi biết rằng trong Nest, gần như mọi thứ đều được chia sẻ giữa các request: connection pool tới database, các singleton service có state toàn cục, v.v. Node.js không theo mô hình request/response đa luồng stateless, trong đó mỗi request được xử lý bởi một thread riêng. Vì vậy, dùng singleton instance là hoàn toàn **an toàn** trong ứng dụng Nest.

Tuy nhiên, có những trường hợp đặc biệt mà vòng đời theo request mới là hành vi mong muốn, ví dụ cache theo từng request trong ứng dụng GraphQL, theo dõi request, và multi-tenancy. Injection scope giúp bạn có được vòng đời provider như mong muốn.

#### Scope của provider <a id="provider-scope"></a>

Một provider có thể có một trong các scope sau:

<table>
  <tr>
    <td><code>DEFAULT</code></td>
    <td>Một instance duy nhất của provider được chia sẻ trong toàn bộ ứng dụng. Vòng đời của instance gắn trực tiếp với vòng đời của ứng dụng. Khi ứng dụng đã bootstrap xong, mọi singleton provider đều đã được khởi tạo. Singleton là scope mặc định.</td>
  </tr>
  <tr>
    <td><code>REQUEST</code></td>
    <td>Một instance mới của provider được tạo riêng cho mỗi <strong>request</strong> gửi đến. Instance này được garbage collect sau khi request đã được xử lý xong.</td>
  </tr>
  <tr>
    <td><code>TRANSIENT</code></td>
    <td>Transient provider không được chia sẻ giữa các nơi sử dụng. Mỗi nơi inject một transient provider sẽ nhận được một instance mới, dành riêng cho nó.</td>
  </tr>
</table>

> info **Gợi ý** Singleton scope là **lựa chọn được khuyên dùng** cho hầu hết trường hợp. Chia sẻ provider giữa các nơi sử dụng và giữa các request nghĩa là instance có thể được cache, và việc khởi tạo chỉ diễn ra một lần, trong lúc ứng dụng khởi động.

#### Cách dùng <a id="usage"></a>

Chỉ định injection scope bằng cách truyền thuộc tính `scope` vào options object của decorator `@Injectable()`:

```typescript
import { Injectable, Scope } from '@nestjs/common';

@Injectable({ scope: Scope.REQUEST })
export class CatsService {}
```

Tương tự, với [custom provider](/fundamentals/custom-providers), đặt thuộc tính `scope` trong dạng khai báo đầy đủ khi đăng ký provider:

```typescript
{
  provide: 'CACHE_MANAGER',
  useClass: CacheManager,
  scope: Scope.TRANSIENT,
}
```

> info **Gợi ý** Import enum `Scope` từ `@nestjs/common`.

Singleton scope là mặc định nên không cần khai báo. Nếu bạn muốn khai báo tường minh một provider có scope singleton, hãy dùng giá trị `Scope.DEFAULT` cho thuộc tính `scope`.

> info **Gợi ý** Kể từ NestJS v12, WebSocket gateway hỗ trợ request-scoped provider. Scope gắn với kết nối socket, không phải với từng message riêng lẻ. Xem [Gateway request-scoped](/websockets/gateways#request-scoped-gateways).

> warning **Chú ý** Một số provider bắt buộc phải hoạt động như singleton và không nên dùng request-scoped provider, như [_Passport strategy_](/recipes/passport#request-scoped-strategies) hay _Cron controller_.

#### Scope của controller <a id="controller-scope"></a>

Controller cũng có thể có scope, áp dụng cho mọi route handler khai báo trong controller đó. Giống như scope của provider, scope của controller khai báo vòng đời của nó. Với controller request-scoped, một instance mới được tạo cho mỗi request gửi đến và được garbage collect khi request đã xử lý xong.

Khai báo scope của controller bằng thuộc tính `scope` của object `ControllerOptions`:

```typescript
@Controller({
  path: 'cats',
  scope: Scope.REQUEST,
})
export class CatsController {}
```

#### Phân cấp scope <a id="scope-hierarchy"></a>

Scope `REQUEST` lan ngược lên theo chuỗi injection. Một controller phụ thuộc vào một request-scoped provider thì bản thân nó cũng trở thành request-scoped.

Xét dependency graph sau: `CatsController <- CatsService <- CatsRepository`. Nếu `CatsService` là request-scoped (còn các thành phần khác là singleton mặc định), `CatsController` sẽ trở thành request-scoped, vì nó phụ thuộc vào service được inject. `CatsRepository`, vốn không phụ thuộc vào `CatsService`, vẫn giữ scope singleton.

Dependency có scope transient không theo pattern đó. Nếu một `DogsService` có scope singleton inject một provider transient `LoggerService`, nó sẽ nhận được một instance mới của provider đó. Tuy nhiên, `DogsService` vẫn giữ scope singleton, nên inject nó ở bất cứ đâu cũng _không_ tạo ra instance mới của `DogsService`. Nếu muốn hành vi đó, hãy đánh dấu tường minh `DogsService` cũng là `TRANSIENT`.

<app-banner-courses></app-banner-courses>

#### Request provider

Trong ứng dụng dựa trên HTTP server (ví dụ dùng `@nestjs/platform-express` hoặc `@nestjs/platform-fastify`), có thể bạn muốn lấy tham chiếu tới request object gốc khi dùng request-scoped provider. Để làm vậy, hãy inject object `REQUEST`.

Provider `REQUEST` vốn dĩ đã là request-scoped, nên bạn không cần chỉ định tường minh scope `REQUEST` khi dùng nó (nếu có chỉ định, nó cũng bị bỏ qua). Mọi provider phụ thuộc vào một request-scoped provider đều tự động mang scope request, và hành vi này không thể thay đổi.

```typescript
import { Injectable, Scope, Inject } from '@nestjs/common';
import { REQUEST } from '@nestjs/core';
import type { Request } from 'express';

@Injectable({ scope: Scope.REQUEST })
export class CatsService {
  constructor(@Inject(REQUEST) private request: Request) {}
}
```

Do khác biệt về nền tảng và giao thức bên dưới, cách truy cập request gửi đến trong ứng dụng microservice hoặc GraphQL hơi khác một chút. Trong ứng dụng [GraphQL](/graphql/quick-start), hãy inject `CONTEXT` thay vì `REQUEST`:

```typescript
import { Injectable, Scope, Inject } from '@nestjs/common';
import { CONTEXT } from '@nestjs/graphql';

@Injectable({ scope: Scope.REQUEST })
export class CatsService {
  constructor(@Inject(CONTEXT) private context) {}
}
```

Sau đó cấu hình giá trị `context` (trong `GraphQLModule`) để chứa `request` như một thuộc tính.

#### Inquirer provider

Để lấy class nơi một provider được tạo ra, ví dụ trong các provider log hoặc metrics, hãy inject token `INQUIRER`:

```typescript
import { Inject, Injectable, Scope } from '@nestjs/common';
import { INQUIRER } from '@nestjs/core';

@Injectable({ scope: Scope.TRANSIENT })
export class HelloService {
  constructor(@Inject(INQUIRER) private parentClass: object) {}

  sayHello(message: string) {
    console.log(`${this.parentClass?.constructor?.name}: ${message}`);
  }
}
```

Sau đó dùng nó như sau:

```typescript
import { Injectable } from '@nestjs/common';
import { HelloService } from './hello.service.js';

@Injectable()
export class AppService {
  constructor(private helloService: HelloService) {}

  getRoot(): string {
    this.helloService.sayHello('My name is getRoot');

    return 'Hello world!';
  }
}
```

Trong ví dụ trên, khi `AppService#getRoot` được gọi, dòng `"AppService: My name is getRoot"` sẽ được in ra console.

#### Hiệu năng <a id="performance"></a>

Request-scoped provider ảnh hưởng tới hiệu năng của ứng dụng. Dù Nest cache càng nhiều metadata càng tốt, nó vẫn phải tạo một instance của class cho mỗi request, làm chậm thời gian phản hồi trung bình và kết quả benchmark tổng thể. Trừ khi một provider bắt buộc phải là request-scoped, chúng tôi rất khuyên bạn dùng singleton scope mặc định.

> info **Gợi ý** Một ứng dụng được thiết kế đúng cách có dùng request-scoped provider không nên thấy độ trễ tăng quá ~5%.

Nhiều provider là request-scoped chỉ để đọc một giá trị thuộc về request hiện tại: người dùng đã xác thực, tenant, hay locale. Với trường hợp đó, một store theo từng request dựa trên `AsyncLocalStorage` giúp mọi provider vẫn là singleton, và hoạt động giống nhau trong HTTP handler, message handler của microservice và queue job. Nếu ứng dụng của bạn dùng [NestJS Observe](/observability/overview), nó đã duy trì sẵn một store như vậy cho mọi request, message và job mà nó instrument: ghi vào store bằng `TracerService.setAttribute()` và đọc ra từ bất cứ đâu phía sau bằng `getAttribute()`, không cần đổi scope và không cần tự duy trì store nào. Xem [Async local storage](/recipes/async-local-storage#nestjs-observe) để biết chi tiết và các phương án khác.

#### Durable provider <a id="durable-providers"></a>

Như đã nói ở phần trước, request-scoped provider có thể làm tăng độ trễ, vì chỉ cần có ít nhất một request-scoped provider (được inject vào instance controller, hoặc sâu hơn, vào một trong các provider của nó) là controller cũng trở thành request-scoped. Khi đó controller phải được tạo lại (khởi tạo) cho từng request riêng lẻ và được garbage collect sau đó. Với, chẳng hạn, 30 nghìn request song song, sẽ có 30 nghìn instance tạm thời của controller (và các request-scoped provider của nó).

Nếu một provider dùng chung mà hầu hết các provider khác phụ thuộc vào (ví dụ kết nối database hoặc logger service) là request-scoped, tất cả các provider đó cũng tự động trở thành request-scoped. Điều này có thể gây khó khăn trong **ứng dụng multi-tenant**, đặc biệt là những ứng dụng có một provider "data source" request-scoped trung tâm, đọc header hoặc token từ request object và dựa vào giá trị đó để lấy kết nối database hoặc schema tương ứng của tenant.

Ví dụ, giả sử ứng dụng của bạn được 10 khách hàng khác nhau sử dụng. Mỗi khách hàng có **data source riêng**, và bạn muốn đảm bảo khách hàng A không bao giờ truy cập được database của khách hàng B. Một cách để làm điều này là khai báo một provider "data source" request-scoped, xác định "khách hàng hiện tại" từ request object và lấy database tương ứng. Cách này biến ứng dụng của bạn thành multi-tenant chỉ trong vài phút. Nhược điểm lớn của nó là phần lớn các thành phần trong ứng dụng có lẽ đều phụ thuộc vào provider "data source", nên chúng ngầm trở thành request-scoped, làm giảm hiệu năng của ứng dụng.

Với chỉ 10 khách hàng, bạn có thể có 10 [DI sub-tree](/fundamentals/module-ref#resolving-scoped-providers) riêng, mỗi khách hàng một cái, thay vì tạo lại từng cây cho mỗi request. Nếu provider của bạn không phụ thuộc vào thuộc tính nào thực sự là duy nhất cho mỗi request (ví dụ UUID của request), mà phụ thuộc vào những thuộc tính cụ thể cho phép gom nhóm (phân loại) request, thì không có lý do gì phải _tạo lại DI sub-tree_ cho mỗi request gửi đến.

Đây là lúc **durable provider** xuất hiện.

Trước khi đánh dấu provider là durable, bạn phải đăng ký một **strategy** cho Nest biết những "thuộc tính chung của request" đó là gì, và cung cấp logic gom nhóm request, tức là gắn chúng với DI sub-tree tương ứng.

```typescript
import {
  HostComponentInfo,
  ContextId,
  ContextIdFactory,
  ContextIdStrategy,
} from '@nestjs/core';
import type { Request } from 'express';

const tenants = new Map<string, ContextId>();

export class AggregateByTenantContextIdStrategy implements ContextIdStrategy {
  attach(contextId: ContextId, request: Request) {
    const tenantId = request.headers['x-tenant-id'] as string;
    let tenantSubTreeId: ContextId;

    if (tenants.has(tenantId)) {
      tenantSubTreeId = tenants.get(tenantId);
    } else {
      tenantSubTreeId = ContextIdFactory.create();
      tenants.set(tenantId, tenantSubTreeId);
    }

    // If tree is not durable, return the original "contextId" object
    return (info: HostComponentInfo) =>
      info.isTreeDurable ? tenantSubTreeId : contextId;
  }
}
```

> info **Gợi ý** Giống như request scope, tính durable lan ngược lên theo chuỗi injection. Nếu A phụ thuộc vào B, và B được đánh dấu `durable`, A cũng ngầm trở thành durable, với điều kiện mọi dependency request-scoped khác của A cũng đều durable (và trừ khi A được khai báo tường minh với `Scope.REQUEST` và `durable: false`).

> warning **Cảnh báo** Strategy này không lý tưởng cho các ứng dụng có số lượng tenant lớn.

Giá trị trả về từ method `attach` cho Nest biết nên dùng context identifier nào cho một host cụ thể. Trong trường hợp này, ta chỉ định rằng `tenantSubTreeId` sẽ được dùng thay cho object `contextId` gốc được sinh tự động khi thành phần host (ví dụ một controller request-scoped) được đánh dấu durable (bạn sẽ thấy cách đánh dấu provider là durable ở bên dưới). Ngoài ra, trong ví dụ trên, **không có payload** nào được đăng ký (payload là provider `REQUEST`/`CONTEXT` đại diện cho "gốc", tức là cha của sub-tree).

Để đăng ký payload cho một durable tree, hãy dùng cách khai báo sau:

```typescript
// The return of `AggregateByTenantContextIdStrategy#attach` method:
return {
  resolve: (info: HostComponentInfo) =>
    info.isTreeDurable ? tenantSubTreeId : contextId,
  payload: { tenantId },
};
```

Giờ đây, mỗi khi bạn inject provider `REQUEST` (hoặc `CONTEXT` với ứng dụng GraphQL) bằng `@Inject(REQUEST)`/`@Inject(CONTEXT)`, object `payload` sẽ được inject (trong trường hợp này gồm một thuộc tính duy nhất là `tenantId`).

Khi đã có strategy này, hãy đăng ký nó ở bất cứ đâu trong code (nó áp dụng ở cấp global), ví dụ trong file `main.ts`:

```typescript
ContextIdFactory.apply(new AggregateByTenantContextIdStrategy());
```

> info **Gợi ý** Class `ContextIdFactory` được import từ package `@nestjs/core`.

Miễn là việc đăng ký diễn ra trước khi có request nào đến ứng dụng, mọi thứ sẽ hoạt động như mong đợi.

Cuối cùng, để biến một provider thông thường thành durable provider, đặt flag `durable` thành `true` và đổi scope của nó thành `Scope.REQUEST`. Nest chỉ đọc flag `durable` trên những provider được khai báo tường minh với `Scope.REQUEST`; một provider chỉ ngầm là request-scoped (thông qua dependency của nó) sẽ suy ra tính durable từ các dependency đó, như mô tả trong phần gợi ý ở trên.

```typescript
import { Injectable, Scope } from '@nestjs/common';

@Injectable({ scope: Scope.REQUEST, durable: true })
export class CatsService {}
```

Tương tự, với [custom provider](/fundamentals/custom-providers), đặt thuộc tính `durable` trong dạng khai báo đầy đủ khi đăng ký provider:

```typescript
{
  provide: 'foobar',
  useFactory: () => { ... },
  scope: Scope.REQUEST,
  durable: true,
}
```
