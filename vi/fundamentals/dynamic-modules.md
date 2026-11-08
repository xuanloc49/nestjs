### Dynamic module

[Chương Modules](/modules) trình bày những kiến thức cơ bản về module trong Nest và có giới thiệu ngắn gọn về [dynamic module](/modules#dynamic-modules). Chương này đi sâu hơn vào chủ đề đó: dynamic module là gì, cách xây dựng chúng, và khi nào nên dùng.

#### Giới thiệu <a id="introduction"></a>

Hầu hết ví dụ code trong phần **Overview** của tài liệu dùng module thông thường, hay module tĩnh. Module định nghĩa các nhóm thành phần, như [provider](/providers) và [controller](/controllers), kết hợp với nhau thành một phần mô-đun của ứng dụng. Module cung cấp execution context, hay scope, cho các thành phần này. Ví dụ, provider định nghĩa trong một module sẽ được các thành viên khác của module nhìn thấy mà không cần export. Khi một provider cần được nhìn thấy bên ngoài module, nó phải được export từ module chủ của nó trước, rồi được import vào module sử dụng nó.

Hãy xét một ví dụ quen thuộc. Đầu tiên, `UsersModule` cung cấp và export `UsersService`. `UsersModule` là module **chủ** của `UsersService`.

```typescript
import { Module } from '@nestjs/common';
import { UsersService } from './users.service.js';

@Module({
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}
```

Tiếp theo, `AuthModule` import `UsersModule`, nhờ đó các provider được export của `UsersModule` dùng được bên trong `AuthModule`:

```typescript
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { UsersModule } from '../users/users.module.js';

@Module({
  imports: [UsersModule],
  providers: [AuthService],
  exports: [AuthService],
})
export class AuthModule {}
```

Cách khai báo này cho phép ta inject `UsersService` vào, chẳng hạn, `AuthService` nằm trong `AuthModule`:

```typescript
import { Injectable } from '@nestjs/common';
import { UsersService } from '../users/users.service.js';

@Injectable()
export class AuthService {
  constructor(private readonly usersService: UsersService) {}
  /*
    Implementation that makes use of this.usersService
  */
}
```

Ta gọi đây là binding module **tĩnh**. Mọi thông tin Nest cần để nối các module với nhau đều được khai báo trong module chủ và module sử dụng. Nest cho `UsersService` dùng được bên trong `AuthModule` bằng cách:

1. Khởi tạo `UsersModule`, bao gồm cả việc import bắc cầu các module mà bản thân `UsersModule` sử dụng, và resolve bắc cầu mọi dependency (xem [Custom provider](/fundamentals/custom-providers)).
2. Khởi tạo `AuthModule`, và cho các thành phần trong `AuthModule` dùng được các provider được export của `UsersModule` (như thể chúng được khai báo trong `AuthModule`).
3. Inject một instance của `UsersService` vào `AuthService`.

#### Khi nào cần dynamic module <a id="dynamic-module-use-case"></a>

Với binding module tĩnh, module sử dụng không có cách nào **tác động** tới việc cấu hình các provider của module chủ. Điều này quan trọng với các module đa dụng cần hoạt động khác nhau cho từng nơi sử dụng, giống như một "plugin" cần được cấu hình trước khi dùng.

Ví dụ, hãy xét một module sinh ra định danh công khai (public identifier) cho các entity của bạn. Định danh bắt đầu bằng một prefix theo loại, như `usr_` cho người dùng và `ord_` cho đơn hàng, giúp bạn nhìn qua là biết nó trỏ tới loại entity nào. Logic sinh định danh giống nhau cho mọi entity, chỉ có prefix là khác. Với binding tĩnh, một `IdGeneratorModule` chỉ có thể cung cấp một generator duy nhất, được cấu hình theo một cách cho mọi module import nó. Thay vào đó, điều ta cần là `UsersModule` và `OrdersModule` mỗi bên import module này với prefix riêng của mình.

Đây là lúc **dynamic module** phát huy tác dụng. Dynamic module cung cấp một API để import một module vào module khác và tùy chỉnh thuộc tính cũng như hành vi của module đó ngay tại thời điểm import.

<app-banner-observe></app-banner-observe>

#### Ví dụ dynamic module <a id="dynamic-module-example"></a>

Sẽ dễ hiểu hơn nếu bắt đầu từ cách module trông như thế nào dưới góc nhìn của module sử dụng, rồi đi ngược lại. Một câu import tĩnh không có chỗ nào để truyền prefix:

```typescript
import { Module } from '@nestjs/common';
import { IdGeneratorModule } from '../id-generator/id-generator.module.js';
import { UsersService } from './users.service.js';

@Module({
  imports: [IdGeneratorModule],
  providers: [UsersService],
})
export class UsersModule {}
```

Ngược lại, một câu import động truyền vào một options object. Hãy so sánh mảng `imports` của hai ví dụ:

```typescript
import { Module } from '@nestjs/common';
import { IdGeneratorModule } from '../id-generator/id-generator.module.js';
import { UsersService } from './users.service.js';

@Module({
  imports: [IdGeneratorModule.register({ prefix: 'usr' })],
  providers: [UsersService],
})
export class UsersModule {}
```

Hãy xem các thành phần trong ví dụ động:

1. `IdGeneratorModule` là một class thông thường, nên nó phải có một **method static** tên là `register()`. Method này là static vì nó được gọi trên class, không phải trên một **instance** của class. Method có thể đặt tên bất kỳ, nhưng theo quy ước thường gọi là `register()`, `forRoot()` hoặc `forFeature()` (xem [Hướng dẫn của cộng đồng](#community-guidelines)).
2. Ta tự định nghĩa method `register()`, nên nó có thể nhận bất kỳ tham số nào ta muốn. Thông thường, như ở đây, nó nhận một options object.
3. Giá trị mà `register()` trả về nằm trong mảng `imports`, cạnh các class module, nên nó phải là thứ mà Nest có thể xem như một module.

Thực tế, `register()` trả về một `DynamicModule`. Dynamic module là module được tạo lúc runtime. Nó có đúng các thuộc tính như metadata của một module tĩnh, cộng thêm một thuộc tính là `module`. Đây là một khai báo module tĩnh mẫu để so sánh:

```typescript
@Module({
  imports: [DogsModule],
  controllers: [CatsController],
  providers: [CatsService],
  exports: [CatsService],
})
```

Dynamic module là một object có cùng các thuộc tính đó, cộng thêm thuộc tính `module` trỏ tới chính class module.

> info **Gợi ý** Với dynamic module, mọi thuộc tính của object tùy chọn module đều là tùy chọn, **ngoại trừ** `module`.

Do đó, nhiệm vụ của method static `register()` là trả về một object implement interface `DynamicModule`. Gọi method này sẽ cung cấp một module cho mảng `imports`, giống như việc liệt kê một class module trong trường hợp tĩnh. Điểm khác biệt là các thuộc tính của module được chỉ định bằng code thay vì cố định trong decorator `@Module()`.

Còn hai chi tiết nữa để hoàn thiện bức tranh:

1. Mảng `imports` của decorator `@Module()` không chỉ nhận class module (ví dụ `imports: [UsersModule]`), mà còn nhận các dynamic module do method static trả về (ví dụ `imports: [IdGeneratorModule.register(...)]`).
2. Bản thân một dynamic module cũng có thể import các module khác. Nếu nó phụ thuộc vào provider từ module khác, hãy liệt kê chúng trong thuộc tính `imports` (tùy chọn) của nó, giống hệt như bạn làm trong decorator `@Module()` của một module tĩnh.

Với những điều trên, đây là phiên bản đầu tiên của `IdGeneratorModule` động:

```typescript
import { DynamicModule, Module } from '@nestjs/common';
import { IdGenerator } from './id-generator.js';

@Module({})
export class IdGeneratorModule {
  static register(): DynamicModule {
    return {
      module: IdGeneratorModule,
      providers: [IdGenerator],
      exports: [IdGenerator],
    };
  }
}
```

Gọi `IdGeneratorModule.register()` trả về một object `DynamicModule` có các thuộc tính về cơ bản giống với những thứ mà từ trước đến giờ ta cung cấp dưới dạng metadata qua decorator `@Module()`.

> info **Gợi ý** Import `DynamicModule` từ `@nestjs/common`.

Tuy vậy, module này vẫn chưa cấu hình được. Hãy giải quyết chuyện đó tiếp theo.

#### Cấu hình module <a id="module-configuration"></a>

Module sử dụng truyền các tùy chọn vào `register()`, như đã thấy ở trên. Vấn đề là làm sao đưa chúng tới thành phần cần đến. `IdGeneratorModule` chứa và export một service có thể inject là `IdGenerator`, và chính `IdGenerator` mới cần prefix. Tạm thời, service này hard-code prefix:

```typescript
import { Injectable } from '@nestjs/common';
import { randomUUID } from 'node:crypto';

@Injectable()
export class IdGenerator {
  generate(): string {
    const options = { prefix: 'usr' };
    return `${options.prefix}_${randomUUID()}`;
  }
}
```

Việc còn lại của ta là truyền object `options` từ method `register()` tới `IdGenerator`, và ta sẽ dùng _dependency injection_ để làm việc đó. Đây là điểm mấu chốt: `IdGeneratorModule` cung cấp `IdGenerator`, và `IdGenerator` phụ thuộc vào một object `options` chỉ được cung cấp lúc runtime. Vì vậy, lúc runtime, trước tiên ta bind object `options` vào IoC container của Nest, rồi để Nest inject nó vào `IdGenerator`. Như chương **Custom provider** đã giải thích, provider có thể [là bất kỳ giá trị nào](/fundamentals/custom-providers#non-service-based-providers), không chỉ là service, nên một object `options` thuần cũng dùng được.

Đầu tiên, mô tả các tùy chọn bằng một interface, và định nghĩa một injection token cho chúng. Token định nghĩa dưới dạng hằng (hoặc `Symbol`) trong một file riêng có thể được import ở bất cứ đâu cần:

```typescript
@@filename(id-generator.interfaces)
export interface IdGeneratorModuleOptions {
  prefix: string;
}

export const ID_GENERATOR_OPTIONS = 'ID_GENERATOR_OPTIONS';
```

Tiếp theo, bind options object vào IoC container trong method static `register()`. Ta đang xây dựng một module động, và một trong các thuộc tính của module là danh sách provider, nên ta định nghĩa options object như một provider. Hãy để ý mảng `providers`:

```typescript
import { DynamicModule, Module } from '@nestjs/common';
import { IdGenerator } from './id-generator.js';
import {
  ID_GENERATOR_OPTIONS,
  IdGeneratorModuleOptions,
} from './id-generator.interfaces.js';

@Module({})
export class IdGeneratorModule {
  static register(options: IdGeneratorModuleOptions): DynamicModule {
    return {
      module: IdGeneratorModule,
      providers: [
        {
          provide: ID_GENERATOR_OPTIONS,
          useValue: options,
        },
        IdGenerator,
      ],
      exports: [IdGenerator],
    };
  }
}
```

Giờ hãy inject các tùy chọn vào `IdGenerator`. Provider đăng ký bằng token không phải class được inject bằng decorator `@Inject()`, như mô tả trong [Token provider không dựa trên class](/fundamentals/custom-providers#non-class-based-provider-tokens):

```typescript
import { Inject, Injectable } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import {
  ID_GENERATOR_OPTIONS,
  type IdGeneratorModuleOptions,
} from './id-generator.interfaces.js';

@Injectable()
export class IdGenerator {
  constructor(
    @Inject(ID_GENERATOR_OPTIONS)
    private readonly options: IdGeneratorModuleOptions,
  ) {}

  generate(): string {
    return `${this.options.prefix}_${randomUUID()}`;
  }
}
```

Khi đã có những thứ trên, mỗi module sử dụng sẽ tự cấu hình generator của mình:

```typescript
@Module({
  imports: [IdGeneratorModule.register({ prefix: 'usr' })],
  providers: [UsersService],
})
export class UsersModule {}

@Module({
  imports: [IdGeneratorModule.register({ prefix: 'ord' })],
  providers: [OrdersService],
})
export class OrdersModule {}
```

`UsersService` và `OrdersService` đều inject `IdGenerator`, nhưng mỗi bên nhận một instance riêng, được cấu hình bởi module đã import nó: định danh người dùng bắt đầu bằng `usr_`, còn định danh đơn hàng bắt đầu bằng `ord_`.

Một ví dụ chạy được có sẵn trong [sample dynamic module](https://github.com/nestjs/nest/tree/master/sample/25-dynamic-modules) trên GitHub.

#### Hướng dẫn của cộng đồng <a id="community-guidelines"></a>

Có thể bạn đã thấy các method như `forRoot()`, `register()` và `forFeature()` trong một số package `@nestjs/`, và tự hỏi chúng khác nhau thế nào. Không có quy tắc cứng nào, nhưng các package `@nestjs/` tuân theo những hướng dẫn sau:

- `register()` cấu hình một dynamic module chỉ để module gọi nó sử dụng, giống như `IdGeneratorModule` của chúng ta. Ví dụ, với `@nestjs/http-client`, `HttpClientModule.register({{ '{' }} baseUrl: 'someUrl' {{ '}' }})` cấu hình một HTTP client cho module gọi nó. Một module khác có thể gọi `HttpClientModule.register({{ '{' }} baseUrl: 'somewhere else' {{ '}' }})` để có một client được cấu hình khác. Bạn có thể làm vậy trong bao nhiêu module tùy thích.
- `forRoot()` cấu hình một dynamic module một lần và dùng lại cấu hình đó ở nhiều nơi (có thể nơi sử dụng không hề biết điều này). Đây là lý do một ứng dụng chỉ có một `GraphQLModule.forRoot()`, một `TypeOrmModule.forRoot()`, v.v.
- `forFeature()` dùng cấu hình đã được thiết lập bởi `forRoot()`, nhưng sửa đổi một phần theo nhu cầu của module gọi nó (ví dụ module được truy cập những repository nào, hay logger nên dùng context nào).

Mỗi method này thường có một phiên bản bất đồng bộ tương ứng, `registerAsync()`, `forRootAsync()` và `forFeatureAsync()`, mang cùng ý nghĩa nhưng resolve cấu hình thông qua dependency injection của Nest.

#### Configurable module builder

Tự tay tạo các dynamic module có khả năng cấu hình cao, lại còn cung cấp các method bất đồng bộ (`registerAsync()`, `forRootAsync()`, v.v.) khá phức tạp, nhất là với người mới. Để đơn giản hóa việc này, Nest cung cấp class `ConfigurableModuleBuilder`, giúp dựng một "bản thiết kế" module chỉ với vài dòng code.

Ví dụ, hãy chuyển `IdGeneratorModule` ở trên sang dùng `ConfigurableModuleBuilder`. Interface `IdGeneratorModuleOptions` vẫn được giữ, nhưng builder sẽ tự sinh injection token, nên không cần hằng `ID_GENERATOR_OPTIONS` nữa.

Tạo một file mới cạnh `id-generator.module.ts`, đặt tên là `id-generator.module-definition.ts`, và dùng `ConfigurableModuleBuilder` để dựng định nghĩa `IdGeneratorModule`:

```typescript
@@filename(id-generator.module-definition)
import { ConfigurableModuleBuilder } from '@nestjs/common';
import type { IdGeneratorModuleOptions } from './id-generator.interfaces.js';

export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder<IdGeneratorModuleOptions>().build();
@@switch
import { ConfigurableModuleBuilder } from '@nestjs/common';

export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder().build();
```

Tiếp theo, sửa `id-generator.module.ts` để kế thừa `ConfigurableModuleClass` được sinh ra:

```typescript
import { Module } from '@nestjs/common';
import { IdGenerator } from './id-generator.js';
import { ConfigurableModuleClass } from './id-generator.module-definition.js';

@Module({
  providers: [IdGenerator],
  exports: [IdGenerator],
})
export class IdGeneratorModule extends ConfigurableModuleClass {}
```

Giống như mọi dynamic module khác, metadata do các method được sinh ra trả về sẽ mở rộng metadata trong decorator `@Module()`, nên `IdGenerator` được cung cấp và export cùng với provider tùy chọn được sinh ra.

Cuối cùng, cập nhật `IdGenerator` để inject provider tùy chọn được sinh ra thay vì token `ID_GENERATOR_OPTIONS`:

```typescript
import { Inject, Injectable } from '@nestjs/common';
import { randomUUID } from 'node:crypto';
import type { IdGeneratorModuleOptions } from './id-generator.interfaces.js';
import { MODULE_OPTIONS_TOKEN } from './id-generator.module-definition.js';

@Injectable()
export class IdGenerator {
  constructor(
    @Inject(MODULE_OPTIONS_TOKEN)
    private readonly options: IdGeneratorModuleOptions,
  ) {}

  generate(): string {
    return `${this.options.prefix}_${randomUUID()}`;
  }
}
```

Kế thừa `ConfigurableModuleClass` cho `IdGeneratorModule` không chỉ method `register()` (như bản implement thủ công), mà còn cả `registerAsync()`, cho phép nơi sử dụng cấu hình module theo kiểu bất đồng bộ. Ví dụ, factory sau đọc prefix bằng `ConfigService` từ [`@nestjs/config`](/application/configuration):

```typescript
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { IdGeneratorModule } from '../id-generator/id-generator.module.js';
import { UsersService } from './users.service.js';

@Module({
  imports: [
    IdGeneratorModule.registerAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        prefix: configService.getOrThrow<string>('USER_ID_PREFIX'),
      }),
      inject: [ConfigService],
    }),
  ],
  providers: [UsersService],
})
export class UsersModule {}
```

Method `registerAsync()` nhận một object với các thuộc tính sau:

```typescript
{
  /**
   * Modules whose exported providers the factory, class, or existing
   * provider depends on.
   */
  imports?: ModuleMetadata['imports'];
  /**
   * Function returning options (or a Promise resolving to options) to configure the
   * module.
   */
  useFactory?: (...args: any[]) => Promise<ModuleOptions> | ModuleOptions;
  /**
   * Dependencies that a Factory may inject.
   */
  inject?: FactoryProvider['inject'];
  /**
   * Injection token resolving to a class that will be instantiated as a provider.
   * The class must implement the corresponding interface.
   */
  useClass?: Type<
    ConfigurableModuleOptionsFactory<ModuleOptions, FactoryClassMethodKey>
  >;
  /**
   * Injection token resolving to an existing provider. The provider must implement
   * the corresponding interface.
   */
  useExisting?: Type<
    ConfigurableModuleOptionsFactory<ModuleOptions, FactoryClassMethodKey>
  >;
  /**
   * List of parent module's providers that will be filtered to only provide necessary
   * providers for the 'inject' array.
   */
  provideInjectionTokensFrom?: Provider[];
}
```

Hãy đi qua từng thuộc tính:

- `imports` - các module cần import vào dynamic module, để factory, class hoặc provider có sẵn có thể inject các provider được export của chúng. Ví dụ trên import `ConfigModule` để inject `ConfigService`.
- `useFactory` - một hàm trả về options object. Hàm này có thể đồng bộ hoặc bất đồng bộ. Để inject dependency vào hàm factory, dùng thuộc tính `inject`. Ví dụ trên dùng biến thể này.
- `inject` - một mảng các dependency cần inject vào hàm factory. Thứ tự các dependency phải khớp với thứ tự tham số của hàm factory.
- `useClass` - một class sẽ được khởi tạo làm provider. Class này phải implement interface tương ứng, mặc định nghĩa là cung cấp method `create()` trả về options object. Xem [Class factory tùy chọn tùy chỉnh](#custom-options-factory-class) bên dưới.
- `useExisting` - một biến thể của `useClass`, dùng lại một provider đã có thay vì bảo Nest tạo instance mới của class. Provider này phải implement cùng interface như class dùng với `useClass` (và do đó phải cung cấp method `create()`, trừ khi bạn đổi tên method, như mô tả trong [Class factory tùy chọn tùy chỉnh](#custom-options-factory-class) bên dưới).
- `provideInjectionTokensFrom` - dùng cùng với `useFactory` (hoặc `useExisting`) và `inject`: một danh sách provider mà từ đó Nest chọn ra những cái được liệt kê trong `inject` và đăng ký chúng trong dynamic module. Thuộc tính này hữu ích khi một module truyền tùy chọn của chính nó xuống một module lồng bên trong mà nó cấu hình theo kiểu bất đồng bộ.

Luôn chọn đúng một trong `useFactory`, `useClass` và `useExisting`, vì chúng loại trừ lẫn nhau.

#### Tùy chỉnh tên method <a id="custom-method-key"></a>

Mặc định, `ConfigurableModuleClass` cung cấp method `register()` và phiên bản `registerAsync()` tương ứng. Để dùng tên method khác, hãy dùng method `ConfigurableModuleBuilder#setClassMethodName`. Ví dụ, nếu module của bạn được thiết kế để cấu hình một lần cho toàn ứng dụng, [hướng dẫn của cộng đồng](#community-guidelines) gợi ý dùng `forRoot()`:

```typescript
@@filename(id-generator.module-definition)
export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder<IdGeneratorModuleOptions>()
    .setClassMethodName('forRoot')
    .build();
@@switch
export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder().setClassMethodName('forRoot').build();
```

Cách này bảo `ConfigurableModuleBuilder` sinh ra một class cung cấp `forRoot()` và `forRootAsync()`:

```typescript
@Module({
  imports: [
    IdGeneratorModule.forRoot({ prefix: 'id' }), // <-- note "forRoot" instead of "register"
    // or alternatively:
    // IdGeneratorModule.forRootAsync({
    //   useFactory: () => ({ prefix: 'id' }),
    //   inject: [...any extra dependencies...],
    // }),
  ],
})
export class AppModule {}
```

#### Class factory tùy chọn tùy chỉnh <a id="custom-options-factory-class"></a>

Vì method `registerAsync()` (hoặc `forRootAsync()`, hoặc tên bất kỳ tùy cấu hình) cho phép nơi sử dụng truyền vào một định nghĩa provider resolve ra tùy chọn của module, nơi sử dụng cũng có thể cung cấp một class tạo ra options object:

```typescript
@Module({
  imports: [
    IdGeneratorModule.registerAsync({
      useClass: IdGeneratorConfigService,
    }),
  ],
})
export class UsersModule {}
```

Mặc định, class này phải cung cấp method `create()` trả về tùy chọn của module. Interface `ConfigurableModuleOptionsFactory`, export từ `@nestjs/common`, mô tả hợp đồng này:

```typescript
import { ConfigurableModuleOptionsFactory, Injectable } from '@nestjs/common';
import type { IdGeneratorModuleOptions } from '../id-generator/id-generator.interfaces.js';

@Injectable()
export class IdGeneratorConfigService
  implements ConfigurableModuleOptionsFactory<IdGeneratorModuleOptions, 'create'>
{
  create(): IdGeneratorModuleOptions {
    return { prefix: 'usr' };
  }
}
```

Nếu library của bạn theo một quy ước đặt tên khác, hãy bảo `ConfigurableModuleBuilder` chờ một method khác, ví dụ `createIdGeneratorOptions`, bằng method `ConfigurableModuleBuilder#setFactoryMethodName`:

```typescript
@@filename(id-generator.module-definition)
export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder<IdGeneratorModuleOptions>()
    .setFactoryMethodName('createIdGeneratorOptions')
    .build();
@@switch
export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder()
    .setFactoryMethodName('createIdGeneratorOptions')
    .build();
```

Giờ class `IdGeneratorConfigService` phải cung cấp method `createIdGeneratorOptions()` thay vì `create()`:

```typescript
@Module({
  imports: [
    IdGeneratorModule.registerAsync({
      useClass: IdGeneratorConfigService, // <-- this class must provide the "createIdGeneratorOptions" method
    }),
  ],
})
export class UsersModule {}
```

#### Tùy chọn bổ sung <a id="extra-options"></a>

Trong một số trường hợp, module cần những tùy chọn bổ sung quyết định cách nó hoạt động, nhưng không nên nằm trong provider `MODULE_OPTIONS_TOKEN`, vì chúng không liên quan tới các provider đăng ký bên trong module. Một ví dụ điển hình là flag `isGlobal`: `IdGenerator` không cần biết module chủ của nó có được đăng ký là global module hay không.

Với những tùy chọn như vậy, hãy dùng method `ConfigurableModuleBuilder#setExtras`:

```typescript
export const { ConfigurableModuleClass, MODULE_OPTIONS_TOKEN } =
  new ConfigurableModuleBuilder<IdGeneratorModuleOptions>()
    .setExtras(
      {
        isGlobal: false,
      },
      (definition, extras) => ({
        ...definition,
        global: extras.isGlobal,
      }),
    )
    .build();
```

Tham số đầu tiên truyền vào method `setExtras` là một object chứa giá trị mặc định của các thuộc tính bổ sung. Tham số thứ hai là một hàm nhận định nghĩa module được sinh tự động (với `providers`, `exports`, v.v.) và object `extras` chứa các thuộc tính bổ sung (do nơi sử dụng chỉ định hoặc giá trị mặc định). Hàm này trả về định nghĩa module đã được sửa đổi. Trong ví dụ này, thuộc tính `extras.isGlobal` được gán cho thuộc tính `global` của định nghĩa module, thuộc tính quyết định module có phải global hay không (xem [Dynamic module](/modules#dynamic-modules) trong chương Modules).

Giờ đây, khi import module này, nơi sử dụng có thể truyền thêm flag `isGlobal`. Ví dụ, một ứng dụng dùng một prefix cho mọi định danh có thể đăng ký module một lần, ở cấp global:

```typescript
@Module({
  imports: [
    IdGeneratorModule.register({
      isGlobal: true,
      prefix: 'id',
    }),
  ],
})
export class AppModule {}
```

Tuy nhiên, vì `isGlobal` được khai báo là thuộc tính bổ sung, nó không nằm trong options object do `MODULE_OPTIONS_TOKEN` cung cấp:

```typescript
@Injectable()
export class IdGenerator {
  constructor(
    @Inject(MODULE_OPTIONS_TOKEN)
    private readonly options: IdGeneratorModuleOptions,
  ) {
    // "options" object will not have the "isGlobal" property
    // ...
  }
}
```

#### Mở rộng các method được sinh tự động <a id="extending-auto-generated-methods"></a>

Các method static được sinh tự động (`register()`, `registerAsync()`, v.v.) có thể được mở rộng khi cần, như sau:

```typescript
import { DynamicModule, Module } from '@nestjs/common';
import { IdGenerator } from './id-generator.js';
import {
  ASYNC_OPTIONS_TYPE,
  ConfigurableModuleClass,
  OPTIONS_TYPE,
} from './id-generator.module-definition.js';

@Module({
  providers: [IdGenerator],
  exports: [IdGenerator],
})
export class IdGeneratorModule extends ConfigurableModuleClass {
  static register(options: typeof OPTIONS_TYPE): DynamicModule {
    return {
      // your custom logic here
      ...super.register(options),
    };
  }

  static registerAsync(options: typeof ASYNC_OPTIONS_TYPE): DynamicModule {
    return {
      // your custom logic here
      ...super.registerAsync(options),
    };
  }
}
```

Lưu ý các type `OPTIONS_TYPE` và `ASYNC_OPTIONS_TYPE`, chúng phải được export từ file định nghĩa module:

```typescript
export const {
  ConfigurableModuleClass,
  MODULE_OPTIONS_TOKEN,
  OPTIONS_TYPE,
  ASYNC_OPTIONS_TYPE,
} = new ConfigurableModuleBuilder<IdGeneratorModuleOptions>().build();
```
