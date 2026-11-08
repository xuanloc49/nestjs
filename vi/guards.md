### Guards

Guard là một class được đánh dấu bằng decorator `@Injectable()` và implement interface `CanActivate`.

<figure><img class="illustrative-image" src="/assets/Guards_1.png" /></figure>

Guard có **một trách nhiệm duy nhất**: quyết định xem một request có được route handler xử lý hay không, dựa trên các điều kiện có tại runtime (như quyền, role, hoặc ACL). Việc này thường được gọi là **phân quyền** (authorization). Trong các ứng dụng Express truyền thống, phân quyền (và người anh em thân thiết của nó là **xác thực**, thứ thường đi cùng với nó) thường được xử lý bằng [middleware](/middleware). Middleware khá phù hợp cho xác thực, vì những việc như validate token và gắn thuộc tính vào object `request` không gắn với một context route cụ thể nào (và metadata của nó).

Tuy nhiên, bản chất của middleware là không biết gì về context: nó không biết handler nào sẽ được thực thi sau khi nó gọi `next()`. Ngược lại, **guard** có quyền truy cập instance `ExecutionContext`, nên nó biết chính xác cái gì sẽ được thực thi tiếp theo. Giống như exception filter, pipe và interceptor, guard cho phép bạn chèn logic xử lý vào đúng điểm cần thiết trong chu trình request/response, và làm điều đó theo kiểu khai báo. Điều này giúp code của bạn giữ được tinh thần DRY.

> info **Gợi ý** Guard được thực thi **sau** tất cả middleware, nhưng **trước** mọi interceptor hay pipe.

#### Guard phân quyền <a id="authorization-guard"></a>

Như đã nói, **phân quyền** là một công dụng phổ biến của guard, vì những route cụ thể chỉ nên được truy cập khi người gọi (thường là một người dùng cụ thể đã được xác thực) có đủ quyền. `AuthGuard` mà ta sắp xây dựng giả định có một người dùng đã được xác thực, và do đó có một token gắn trong header của request. Nó lấy token ra, validate, và dùng thông tin lấy được để quyết định request có được đi tiếp hay không.

```typescript
@@filename(auth.guard)
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Observable } from 'rxjs';

@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(
    context: ExecutionContext,
  ): boolean | Promise<boolean> | Observable<boolean> {
    const request = context.switchToHttp().getRequest();
    return validateRequest(request);
  }
}
@@switch
import { Injectable } from '@nestjs/common';

@Injectable()
export class AuthGuard {
  async canActivate(context) {
    const request = context.switchToHttp().getRequest();
    return validateRequest(request);
  }
}
```

> info **Gợi ý** Để xem ví dụ thực tế về một cơ chế xác thực, xem chương [xác thực](/security/authentication). Để xem một ví dụ phân quyền phức tạp hơn, xem chương [phân quyền](/security/authorization).

Logic bên trong hàm `validateRequest()` có thể đơn giản hoặc phức tạp tùy nhu cầu. Mục đích của ví dụ này là cho thấy guard nằm ở đâu trong chu trình request/response.

Mọi guard đều phải implement method `canActivate()`. Method này trả về một giá trị boolean cho biết request hiện tại có được phép hay không, theo kiểu đồng bộ hoặc bất đồng bộ (qua `Promise` hoặc `Observable`). Nest dùng giá trị trả về để quyết định điều gì xảy ra tiếp theo:

- nếu trả về `true`, request sẽ được xử lý.
- nếu trả về `false`, Nest sẽ từ chối request.

<app-banner-enterprise></app-banner-enterprise>

#### Execution context

Method `canActivate()` nhận một tham số duy nhất là instance `ExecutionContext`. `ExecutionContext` kế thừa `ArgumentsHost`, thứ mà ta đã tìm hiểu trong chương exception filter. Ví dụ ở trên dùng chính các method helper định nghĩa trên `ArgumentsHost` để lấy tham chiếu tới object `Request`. Xem phần **Arguments host** trong chương [exception filter](/exception-filters#arguments-host) để biết thêm về chủ đề này.

Bằng việc kế thừa `ArgumentsHost`, `ExecutionContext` bổ sung thêm vài method helper cung cấp thông tin chi tiết hơn về quá trình thực thi hiện tại. Những thông tin này giúp bạn xây dựng các guard generic hơn, hoạt động được trên nhiều controller, method và execution context khác nhau. Xem chương [execution context](/fundamentals/execution-context) để tìm hiểu thêm về `ExecutionContext`.

#### Xác thực dựa trên role <a id="role-based-authentication"></a>

Hãy xây dựng một guard hữu dụng hơn, chỉ cho phép người dùng có role cụ thể truy cập. Ta sẽ bắt đầu với một template guard cơ bản và phát triển dần trong các phần sau. Hiện tại, nó cho mọi request đi qua:

```typescript
@@filename(roles.guard)
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Observable } from 'rxjs';

@Injectable()
export class RolesGuard implements CanActivate {
  canActivate(
    context: ExecutionContext,
  ): boolean | Promise<boolean> | Observable<boolean> {
    return true;
  }
}
@@switch
import { Injectable } from '@nestjs/common';

@Injectable()
export class RolesGuard {
  canActivate(context) {
    return true;
  }
}
```

#### Bind guard <a id="binding-guards"></a>

Giống như pipe và exception filter, guard có thể ở cấp controller, cấp method hoặc cấp global. Dưới đây, ta thiết lập một guard cấp controller bằng decorator `@UseGuards()`. Decorator này nhận một guard hoặc một danh sách guard phân cách bằng dấu phẩy, nên bạn có thể áp dụng cả một nhóm guard chỉ với một khai báo.

```typescript
@@filename()
@Controller('cats')
@UseGuards(RolesGuard)
export class CatsController {}
```

> info **Gợi ý** Decorator `@UseGuards()` được import từ package `@nestjs/common`.

Ở trên, ta truyền vào class `RolesGuard` (thay vì instance), để framework lo việc khởi tạo và bật được dependency injection. Giống như với pipe và exception filter, bạn cũng có thể truyền một instance tạo tại chỗ:

```typescript
@@filename()
@Controller('cats')
@UseGuards(new RolesGuard())
export class CatsController {}
```

Cách khai báo trên gắn guard vào mọi handler mà controller này khai báo. Để chỉ áp dụng guard cho một method, dùng decorator `@UseGuards()` ở **cấp method**.

Để thiết lập global guard, dùng method `useGlobalGuards()` của instance ứng dụng Nest:

```typescript
@@filename()
const app = await NestFactory.create(AppModule);
app.useGlobalGuards(new RolesGuard());
```

> warning **Chú ý** Trong hybrid application, `useGlobalGuards()` mặc định không thiết lập guard cho các microservice được kết nối (xem [Hybrid application](/faq/hybrid-application) để thay đổi hành vi này). Trong một ứng dụng microservice thông thường (không phải hybrid), `useGlobalGuards()` có mount guard ở cấp global.

Global guard áp dụng cho mọi controller và mọi route handler trong ứng dụng. Tuy nhiên, global guard đăng ký từ bên ngoài mọi module (bằng `useGlobalGuards()` như ví dụ trên) không thể inject dependency, vì việc đăng ký diễn ra bên ngoài context của mọi module. Để giải quyết, hãy đăng ký guard trực tiếp từ bất kỳ module nào bằng cách sau:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';

@Module({
  providers: [
    {
      provide: APP_GUARD,
      useClass: RolesGuard,
    },
  ],
})
export class AppModule {}
```

> info **Gợi ý** Khi dùng cách này để thực hiện dependency injection cho guard, guard sẽ là global bất kể bạn đăng ký nó trong module nào. Chúng tôi khuyên đăng ký nó trong module nơi guard (`RolesGuard` trong ví dụ trên) được định nghĩa. Ngoài ra, `useClass` không phải cách duy nhất để đăng ký custom provider. Xem [Custom provider](/fundamentals/custom-providers) để tìm hiểu thêm.

> info **Gợi ý** Bạn có thể đăng ký token `APP_GUARD` nhiều lần (trong cùng một module hoặc các module khác nhau); mọi guard đã đăng ký đều chạy cho mỗi request, theo thứ tự đăng ký. `APP_GUARD` (cũng như các token `APP_*` khác) là một pseudo-provider mà framework sử dụng trong lúc bootstrap: bạn không thể lấy nó ra sau này bằng `app.get()` hay inject nó ở chỗ khác.

#### Đặt role cho từng handler <a id="setting-roles-per-handler"></a>

`RolesGuard` của chúng ta đã chạy, nhưng chưa thông minh lắm: nó chưa tận dụng tính năng quan trọng nhất của guard, đó là [execution context](/fundamentals/execution-context). Nó chưa biết gì về role, hay role nào được phép cho từng handler. Ví dụ, `CatsController` có thể có các cơ chế phân quyền khác nhau cho các route khác nhau. Một số route chỉ dành cho admin, trong khi số khác mở cho tất cả mọi người. Làm sao để gắn role với route một cách linh hoạt và tái sử dụng được?

Đây là lúc **custom metadata** phát huy tác dụng (xem [Reflection và metadata](/fundamentals/execution-context#reflection-and-metadata)). Nest cho phép bạn gắn **metadata** tùy chỉnh vào route handler, thông qua decorator tạo bằng method static `Reflector.createDecorator()` hoặc qua decorator có sẵn `@SetMetadata()`.

Ví dụ, hãy tạo một decorator `@Roles()` bằng method `Reflector.createDecorator()` để gắn metadata vào handler. `Reflector` được framework cung cấp sẵn và export từ package `@nestjs/core`.

```ts
@@filename(roles.decorator)
import { Reflector } from '@nestjs/core';

export const Roles = Reflector.createDecorator<string[]>();
```

Decorator `Roles` là một hàm nhận một tham số duy nhất có type `string[]`.

Để dùng decorator này, hãy đánh dấu handler bằng nó:

```typescript
@@filename(cats.controller)
@Post()
@Roles(['admin'])
async create(@Body() createCatDto: CreateCatDto) {
  this.catsService.create(createCatDto);
}
@@switch
@Post()
@Roles(['admin'])
@Bind(Body())
async create(createCatDto) {
  this.catsService.create(createCatDto);
}
```

Ở đây ta đã gắn metadata của decorator `Roles` vào method `create()`, cho biết chỉ người dùng có role `admin` mới được phép truy cập route này.

Thay vì dùng method `Reflector.createDecorator()`, bạn cũng có thể dùng decorator có sẵn `@SetMetadata()`. Xem [cách làm ở mức thấp](/fundamentals/execution-context#low-level-approach) để tìm hiểu thêm.

#### Ghép mọi thứ lại <a id="putting-it-all-together"></a>

Giờ hãy kết nối tất cả với `RolesGuard`. Hiện tại, nó trả về `true` trong mọi trường hợp, cho mọi request đi qua. Ta muốn giá trị trả về phụ thuộc vào điều kiện, dựa trên việc so sánh **các role được gán cho người dùng hiện tại** với các role mà route đang xử lý yêu cầu. Để lấy (các) role của route (custom metadata), ta lại dùng class `Reflector` như sau:

```typescript
@@filename(roles.guard)
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Roles } from './roles.decorator.js';

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const roles = this.reflector.get(Roles, context.getHandler());
    if (!roles) {
      return true;
    }
    const request = context.switchToHttp().getRequest();
    const user = request.user;
    return matchRoles(roles, user.roles);
  }
}
@@switch
import { Injectable, Dependencies } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Roles } from './roles.decorator.js';

@Injectable()
@Dependencies(Reflector)
export class RolesGuard {
  constructor(reflector) {
    this.reflector = reflector;
  }

  canActivate(context) {
    const roles = this.reflector.get(Roles, context.getHandler());
    if (!roles) {
      return true;
    }
    const request = context.switchToHttp().getRequest();
    const user = request.user;
    return matchRoles(roles, user.roles);
  }
}
```

> info **Gợi ý** Trong các ứng dụng Node.js, gắn người dùng đã được phân quyền vào object `request` là cách làm phổ biến. Vì vậy, ví dụ trên giả định `request.user` chứa instance người dùng và các role của họ. Trong ứng dụng của bạn, có lẽ bạn sẽ thực hiện việc gắn này trong một **authentication guard** tùy chỉnh (hoặc middleware). Xem chương [xác thực](/security/authentication) để biết thêm về chủ đề này.

> warning **Cảnh báo** Hàm `matchRoles()` không phải do Nest cung cấp. Logic của nó có thể đơn giản hoặc phức tạp tùy theo yêu cầu của ứng dụng; mục đích của ví dụ này là cho thấy guard nằm ở đâu trong chu trình request/response.

Xem phần [Reflection và metadata](/fundamentals/execution-context#reflection-and-metadata) trong chương **Execution context** để biết thêm chi tiết về cách dùng `Reflector` theo từng context.

Khi một người dùng không đủ quyền gọi tới một endpoint, Nest tự động trả về response sau:

```json
{
  "statusCode": 403,
  "message": "Forbidden resource",
  "error": "Forbidden"
}
```

Bên dưới, khi guard trả về `false`, framework sẽ throw một `ForbiddenException`. Để trả về một response lỗi khác, hãy tự throw exception của bạn. Ví dụ:

```typescript
throw new UnauthorizedException();
```

Mọi exception do guard throw ra đều được [lớp xử lý exception](/exception-filters) đảm nhận (global exception filter và mọi exception filter được áp dụng cho context hiện tại).

> info **Gợi ý** Để xem ví dụ thực tế về cách implement phân quyền, xem chương [phân quyền](/security/authorization).
