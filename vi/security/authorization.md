### Phân quyền

`@nestjs/authorization` biểu diễn quyền hạn dưới dạng **policy**: các class có method trả lời câu hỏi "người dùng này có được làm việc này không?". Một policy là một provider thông thường, nên nó có thể inject service, và mọi lần kiểm tra đều được kiểm tra type theo method của policy mà nó gọi. Policy làm việc với mọi cấu trúc dữ liệu, kể cả các object thuần mà Prisma, Drizzle và Kysely trả về.

Trong bài hướng dẫn này, bạn sẽ thêm phân quyền vào API của một cửa hàng online bán thức ăn và đồ dùng cho mèo:

- Khách vãng lai và khách hàng xem các sản phẩm đã đăng. Nhân viên còn thấy cả bản nháp, và chỉ nhân viên mới sửa danh mục sản phẩm.
- Khách hàng chỉ thấy đơn hàng của chính họ. Nhân viên thấy tất cả.
- Chỉ nhân viên mới được hoàn tiền đơn hàng, chỉ với đơn đã thanh toán, và chỉ tới mức mà bộ phận tài chính đặt cho từng người. Không ai được hoàn tiền một đơn hàng đã giao.
- Admin quản lý danh mục sản phẩm không giới hạn.

Trong quá trình đó, bạn sẽ thấy mỗi loại kiểm tra nên nằm ở đâu (trên route hay trong service), khi nào một lời từ chối là 401 và khi nào là 403, và cách test policy.

#### Điều kiện tiên quyết <a id="prerequisites"></a>

Bài hướng dẫn này tiếp nối bài hướng dẫn [Xác thực](/security/authentication): cửa hàng đăng nhập người dùng bằng `@nestjs/authentication`, còn trang này quyết định họ được làm gì. Cài package:

```bash
$ npm i --save @nestjs/authorization
```

Nếu bạn bắt đầu từ đầu, các file dưới đây là phần code đăng nhập mà trang này dựa vào: ứng dụng của bài hướng dẫn Xác thực ở thời điểm nó [cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app), rút gọn còn phần đăng nhập của app mobile, đổi mật khẩu lấy bearer token. Người dùng vẫn là object thuần như vậy, đúng như ORM của bạn trả về:

```typescript
@@filename(src/users/user)
export type Role = 'customer' | 'staff' | 'admin';

export interface User {
  id: string;
  email: string;
  /** Whether the owner proved the address to us, e.g. by using a magic link. */
  emailVerified: boolean;
  roles: Role[];
}
```

Bốn tài khoản demo thay cho bảng người dùng: hai khách hàng (Alice và Bob), một nhân viên (Sam), và Ada, vừa là nhân viên vừa là admin. Id của họ là cố định, để các đơn hàng demo và các bài test có thể tham chiếu tới họ:

```typescript
@@filename(src/users/demo-users)
import type { User } from './user.js';

/**
 * The demo accounts. They all sign in with the password "catnip4all", and the
 * seeded orders refer to their ids.
 */
export const alice: User = {
  id: '1f794c55-472e-42b9-8913-4114964ed6fb',
  email: 'alice@example.com',
  emailVerified: true,
  roles: ['customer'],
};

export const bob: User = {
  id: 'fc27b5c1-62b5-494e-9924-28a66d387fd1',
  email: 'bob@example.com',
  emailVerified: true,
  roles: ['customer'],
};

export const sam: User = {
  id: '208a223b-3503-4255-83e7-22d290e331c3',
  email: 'sam@example.com',
  emailVerified: true,
  roles: ['staff'],
};

export const ada: User = {
  id: 'ae34ca97-f82b-49ab-b332-8808f3b0e240',
  email: 'ada@example.com',
  emailVerified: true,
  roles: ['staff', 'admin'],
};

export const demoUsers = [alice, bob, sam, ada];
```

`UsersRepository` là của bài hướng dẫn Xác thực, với hai method mà trang này cần. Nó tạo sẵn các tài khoản demo lúc khởi động, và chỉ có object `User` đi ra khỏi nó: các hash mật khẩu ở lại bên trong.

```typescript
@@filename(src/users/users.repository)
import { Injectable, type OnModuleInit } from '@nestjs/common';
import { PasswordHasher } from '@nestjs/authentication';
import { demoUsers } from './demo-users.js';
import type { User } from './user.js';

interface UserRow extends User {
  passwordHash: string | null;
}

/**
 * In-memory stand-in for your data layer (Prisma, Drizzle, TypeORM, ...).
 * Only `User` objects leave this class: password hashes stay inside.
 */
@Injectable()
export class UsersRepository implements OnModuleInit {
  private readonly rows = new Map<string, UserRow>();

  constructor(private readonly passwordHasher: PasswordHasher) {}

  async onModuleInit() {
    // Seeds the demo accounts, all with the password "catnip4all".
    const passwordHash = await this.passwordHasher.hash('catnip4all');
    for (const user of demoUsers) {
      this.rows.set(user.id, { ...user, passwordHash });
    }
  }

  async findById(id: string): Promise<User | null> {
    const row = this.rows.get(id);
    return row ? toUser(row) : null;
  }

  /** For password sign-in only. */
  async findCredentials(email: string): Promise<{ user: User; passwordHash: string | null } | null> {
    const row = this.findRow(email);
    return row ? { user: toUser(row), passwordHash: row.passwordHash } : null;
  }

  private findRow(email: string) {
    const normalized = normalize(email);
    return [...this.rows.values()].find((row) => row.email === normalized);
  }
}

const normalize = (email: string) => email.trim().toLowerCase();
const toUser = ({ id, email, emailVerified, roles }: UserRow): User => ({ id, email, emailVerified, roles: [...roles] });
```

```typescript
@@filename(src/users/users.module)
import { Module } from '@nestjs/common';
import { UsersRepository } from './users.repository.js';

@Module({
  providers: [UsersRepository],
  exports: [UsersRepository],
})
export class UsersModule {}
```

Token là loại mà bài hướng dẫn Xác thực cấp cho app mobile của nó: các JWT access token ngắn hạn, được mô tả một lần bằng tùy chọn `accessToken` mà root module truyền vào `AuthenticationModule` bên dưới. Signing secret là `JWT_SECRET` từ file `.env` của bài hướng dẫn Xác thực, dài ít nhất 32 byte:

```bash
# Generate with: openssl rand -base64 32
JWT_SECRET=
```

> info **Gợi ý** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để việc thiếu secret làm ứng dụng dừng ngay lúc khởi động, và đọc nó từ `ConfigService`.

`JwtAuth` xác minh bearer token bằng tùy chọn `accessToken`, và load người dùng của token. Nó tự đăng ký với `AuthenticationRegistry` từ constructor, đó là cách guard biết đến nó:

```typescript
@@filename(src/auth/jwt-auth.provider)
import { Injectable } from '@nestjs/common';
import { AuthenticationRegistry, JwtBearerProvider, type JwtClaims } from '@nestjs/authentication';
import type { User } from '../users/user.js';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class JwtAuth extends JwtBearerProvider<User> {
  constructor(
    private readonly usersRepository: UsersRepository,
    registry: AuthenticationRegistry,
  ) {
    // The key, issuer and audience come from the `accessToken` options.
    super({ realm: 'store' });
    // Adds this provider to the chain the guard runs for every request.
    registry.registerProvider(this);
  }

  // Called after the signature and claims checked out.
  // Returning null (the user was deleted) rejects the token.
  validate({ sub }: JwtClaims) {
    return sub ? this.usersRepository.findById(sub) : null;
  }
}
```

`CredentialsService` kiểm tra mật khẩu với hash đã lưu, bằng `PasswordHasher` của package, và trả lời `null` cho cả email không tồn tại lẫn mật khẩu sai, trong cùng khoảng thời gian:

```typescript
@@filename(src/auth/credentials.service)
import { Injectable } from '@nestjs/common';
import { PasswordHasher } from '@nestjs/authentication';
import type { User } from '../users/user.js';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class CredentialsService {
  constructor(
    private readonly usersRepository: UsersRepository,
    private readonly passwordHasher: PasswordHasher,
  ) {}

  /** The user, or `null` when the email or the password is wrong. */
  async verify(email: string, password: string): Promise<User | null> {
    const found = await this.usersRepository.findCredentials(email);
    // With no account (or no password), verify() checks a dummy hash, so the
    // response time does not reveal which emails are registered.
    const valid = await this.passwordHasher.verify(password, found?.passwordHash);
    if (!valid || !found?.passwordHash) {
      return null;
    }
    return found.user;
  }
}
```

`TokensController` đổi email và mật khẩu lấy token. Request body của nó được validate bằng bất cứ công cụ nào ứng dụng của bạn đang dùng. Mọi DTO trên trang này đều có hai phiên bản, một class có decorator và một schema Zod, nên hãy chọn kiểu bạn đang dùng và bỏ qua phiên bản còn lại:

```typescript
@@filename(src/auth/auth.dto)
import { IsEmail, IsString } from 'class-validator';

export class SignInDto {
  @IsEmail()
  email: string;

  @IsString()
  password: string;
}
```

```typescript
@@filename(src/auth/auth.schemas)
import { z } from 'zod';

export const signInSchema = z.object({
  email: z.email(),
  password: z.string(),
});
export type SignInDto = z.infer<typeof signInSchema>;
```

`TokenService.issue()` ký một access token bằng cùng tùy chọn `accessToken`, và trả về nó kèm một refresh token:

```typescript
@@filename(src/auth/tokens.controller)
import { Body, Controller, HttpCode, Post, UnauthorizedException } from '@nestjs/common';
import { Public, TokenService } from '@nestjs/authentication';
import { SignInDto } from './auth.dto.js';
import { CredentialsService } from './credentials.service.js';

@Public()
@Controller('auth/token')
export class TokensController {
  constructor(
    private readonly credentialsService: CredentialsService,
    private readonly tokenService: TokenService,
  ) {}

  @Post()
  @HttpCode(200)
  async issue(@Body() body: SignInDto) {
    const user = await this.credentialsService.verify(body.email, body.password);
    if (!user) {
      throw new UnauthorizedException('Invalid email or password');
    }
    return this.tokenService.issue(user.id, {
      method: 'password',
      // `amr` goes into this access token and into every refreshed one.
      claims: { amr: ['pwd'] },
    });
  }
}
```

Với schema Zod, tham số body khai báo schema thay vì class:

```typescript
@@filename(src/auth/tokens.controller)
import { signInSchema, type SignInDto } from './auth.schemas.js';
// ...
@Post()
@HttpCode(200)
async issue(@Body({ schema: signInSchema }) body: SignInDto) {
  // ...
}
```

> info **Gợi ý** Các DTO chỉ được áp dụng khi có validation pipe: hãy bind `ValidationPipe` ở cấp global, dưới dạng provider `APP_PIPE` của `AppModule` hoặc bằng `useGlobalPipes()` trong `main.ts`. Với các schema Zod, hãy bind `StandardSchemaValidationPipe` theo cùng cách. Một ứng dụng dùng một trong hai. Trang [validation](/application/validation) có các tùy chọn của mỗi loại.

```typescript
@@filename(src/auth/auth.module)
import { Module } from '@nestjs/common';
import { UsersModule } from '../users/users.module.js';
import { CredentialsService } from './credentials.service.js';
import { JwtAuth } from './jwt-auth.provider.js';
import { TokensController } from './tokens.controller.js';

@Module({
  imports: [UsersModule],
  controllers: [TokensController],
  providers: [JwtAuth, CredentialsService],
})
export class AuthModule {}
```

Phần xác thực đặt `User` đã đăng nhập vào `request.user`, và `@CurrentUser()` inject nó vào handler. Đó là tất cả những gì phân quyền cần từ nó.

#### Đăng ký authorization module <a id="register-the-authorization-module"></a>

Import `AuthorizationModule` cạnh `AuthenticationModule` trong root module. `AuthenticationModule` được đăng ký giống như trong bài hướng dẫn Xác thực, với tùy chọn `accessToken`; `JwtAuth` là một provider của `AuthModule`:

```typescript
@@filename(src/app.module)
import { Module } from '@nestjs/common';
import { AuthenticationModule } from '@nestjs/authentication';
import { AuthorizationModule } from '@nestjs/authorization';
import { AuthModule } from './auth/auth.module.js';

@Module({
  imports: [
    // Authentication first: its guard sets request.user, which authorization reads.
    AuthenticationModule.forRootAsync({
      useFactory: () => ({
        accessToken: {
          key: process.env.JWT_SECRET!,
          issuer: 'https://api.example.com',
          audience: 'mobile-app',
          ttl: '15m',
        },
      }),
    }),
    AuthorizationModule.forRoot(),
    AuthModule,
  ],
})
export class AppModule {}
```

`forRoot()` đăng ký module ở cấp global. Nó làm ba việc:

- Nó cung cấp `AuthorizationService`, bạn inject nó ở bất cứ đâu code cần kiểm tra quyền.
- Nó đăng ký `AuthorizationGuard` làm global guard. Guard áp dụng decorator `@Can()` mà bạn sẽ thêm ở bước tiếp theo, và **mặc định từ chối**: một handler chỉ chạy khi nó khai báo một bước kiểm tra, bằng `@Can()`, bằng `@Can.Anyone()`, hoặc bằng `@Public()` từ `@nestjs/authentication`, decorator này được tính như `@Can.Anyone()`. `POST /auth/token` là `@Public()`, nên nó vẫn hoạt động.
- Nó biến một lời từ chối mà service báo cáo thành lỗi 401 hoặc 403, như phần [Phân biệt khách vãng lai với người dùng bị cấm, và cung cấp quyền hạn](/security/authorization#tell-guests-from-forbidden-users-and-expose-permissions) giải thích.

Do đó, một route bị quên `@Can()` sẽ bị đóng, chứ không mở. Lúc khởi động, module log mọi handler mà nó sẽ từ chối theo cách này, nên danh sách đó là nơi bắt đầu một đợt chuyển đổi. Phần [tham khảo](/security/authorization#what-a-route-declares) có các quy tắc đầy đủ.

Cả hai package đều đăng ký global guard, và **thứ tự import rất quan trọng**. Nest chạy global guard theo thứ tự nó quét các module, nên `AuthenticationModule` phải đứng trước. Nếu ngược lại, authorization guard sẽ chạy trước khi có gì đặt `request.user`, nên mọi kiểm tra `@Can()` sẽ thấy một khách vãng lai, và một nhân viên đã đăng nhập sẽ nhận lỗi 401 trên một route chỉ dành cho nhân viên. `AuthorizationModule` kiểm tra thứ tự lúc khởi động: nó nhận ra `AuthenticationGuard` nhờ một dấu hiệu mà guard mang theo, và khi guard đó đứng thứ hai, app sẽ từ chối khởi động, với thông báo lỗi nêu tên cả hai guard và cách sửa.

> warning **Cảnh báo** Các authentication guard khác, như một class con của `AuthGuard()` của Passport, không mang dấu hiệu đó, nên việc kiểm tra chỉ có thể dựa vào tên class của chúng. Khi sai thứ tự, nó log một lỗi, app vẫn khởi động, và mọi kiểm tra `@Can()` xem người dùng đã đăng nhập như khách vãng lai. Hãy đăng ký guard như vậy bằng `APP_GUARD`, không phải bằng `app.useGlobalGuards()`: Nest chạy các guard thêm theo cách đó sau mọi `APP_GUARD`, nên chúng luôn đứng sau authorization guard, và bước kiểm tra không thể thấy chúng.

> info **Gợi ý** Guard đọc người dùng từ `request.user`, và từ các vị trí tương đương với WebSocket, microservice và GraphQL. Với `@nestjs/authentication`, trên một WebSocket hoặc socket `graphql-ws`, đó là người dùng của từng message hoặc operation, không phải của socket, như phần [tham khảo](/security/authorization#reference) giải thích. Nếu phần xác thực của bạn lưu người dùng ở chỗ khác, hãy truyền một hàm `getUser` vào `forRoot()`, hoặc trả về nó từ một factory `forRootAsync()` khi nó cần một provider. Nếu bạn xác thực bằng `@UseGuards()` thay vì global guard, hãy truyền `globalGuard: false` và liệt kê `AuthorizationGuard` sau authentication guard của bạn.

#### Viết policy cho sản phẩm <a id="write-a-policy-for-products"></a>

Sản phẩm cũng là object thuần, được định danh bằng slug và có giá tính bằng cent, như trong bài hướng dẫn Xác thực:

```typescript
@@filename(src/products/product)
export interface Product {
  /** A slug, such as `salmon-kibble-2kg`. */
  id: string;
  name: string;
  /** In cents. */
  price: number;
  published: boolean;
}

export type ProductInput = Omit<Product, 'id'>;
```

Một policy là một class được decorate bằng `@Policy()`. Mỗi method có tham số đầu tiên là người dùng và trả về `boolean` hoặc `Promise<boolean>` là một **ability**. Chỉ giá trị literal `true` mới cho phép. Mọi giá trị khác đều từ chối, kể cả giá trị truthy.

```typescript
@@filename(src/products/product.policy)
import { Policy } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import type { Product } from './product.js';

const isStaff = (user: User | null) => !!user?.roles.includes('staff');

@Policy()
export class ProductPolicy {
  // `null` is a guest. Everyone sees published products; staff also see drafts.
  view(user: User | null, product: Product) {
    return product.published || isStaff(user);
  }

  viewDrafts(user: User | null) {
    return isStaff(user);
  }

  create(user: User | null) {
    return isStaff(user);
  }

  update(user: User | null) {
    return isStaff(user);
  }
}
```

Type của tham số người dùng là một quyết định. `User | null` có nghĩa là ability cũng chạy cho khách vãng lai, những người đến dưới dạng `null`. Khách vãng lai có thể xem danh mục sản phẩm, nên mọi ability ở đây đều nhận `null`, và `view` cùng `viewDrafts` đưa ra câu trả lời thực sự cho khách vãng lai.

`ProductsService` dùng policy theo hai cách. `can()` resolve ra `true` hoặc `false`; ở đây nó quyết định danh sách có bao gồm bản nháp hay không. `authorize()` throw khi ability từ chối, nên `findOne()` không bao giờ trả về bản nháp cho người không được phép xem nó.

```typescript
@@filename(src/products/products.service)
import { Injectable, NotFoundException } from '@nestjs/common';
import { AuthorizationService } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import type { Product, ProductInput } from './product.js';
import { ProductPolicy } from './product.policy.js';

@Injectable()
export class ProductsService {
  // Stands in for your products table.
  private readonly products: Product[] = [
    { id: 'salmon-kibble-2kg', name: 'Salmon kibble, 2 kg', price: 2499, published: true },
    { id: 'clumping-litter-10l', name: 'Clumping litter, 10 l', price: 1599, published: true },
    { id: 'heated-cat-bed', name: 'Heated cat bed', price: 5499, published: false },
  ];

  constructor(private readonly authorizationService: AuthorizationService) {}

  async findAll(user: User | null) {
    const withDrafts = await this.authorizationService.can(ProductPolicy, 'viewDrafts', user);
    return withDrafts ? this.products : this.products.filter((product) => product.published);
  }

  async findOne(user: User | null, id: string) {
    const product = this.find(id);
    await this.authorizationService.authorize(ProductPolicy, 'view', user, product);
    return product;
  }

  create(input: ProductInput) {
    const product = { ...input, id: slug(input.name) };
    this.products.push(product);
    return product;
  }

  update(id: string, changes: Partial<ProductInput>) {
    return Object.assign(this.find(id), changes);
  }

  remove(id: string) {
    this.products.splice(this.products.indexOf(this.find(id)), 1);
  }

  private find(id: string) {
    const product = this.products.find((product) => product.id === id);
    if (!product) {
      throw new NotFoundException();
    }
    return product;
  }
}

/** `Sisal scratching post` → `sisal-scratching-post`. */
const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
```

Tạo và cập nhật sản phẩm không phụ thuộc vào một bản ghi cụ thể nào, nên các bước kiểm tra đó nằm trên route. Body của các route đó là DTO, dưới dạng class hoặc schema Zod; một lần cập nhật nhận bất kỳ tập con nào của các trường của sản phẩm mới:

```typescript
@@filename(src/products/products.dto)
import { PartialType } from '@nestjs/mapped-types';
import { IsBoolean, IsPositive, IsString, MinLength } from 'class-validator';

export class CreateProductDto {
  @IsString()
  @MinLength(1)
  name: string;

  @IsPositive()
  price: number;

  @IsBoolean()
  published: boolean;
}

/** Any subset of the fields above. */
export class UpdateProductDto extends PartialType(CreateProductDto) {}
```

```typescript
@@filename(src/products/products.schemas)
import { z } from 'zod';

export const createProductSchema = z.object({
  name: z.string().min(1),
  price: z.number().positive(),
  published: z.boolean(),
});
export type CreateProductDto = z.infer<typeof createProductSchema>;

/** Any subset of the fields above. */
export const updateProductSchema = createProductSchema.partial();
export type UpdateProductDto = z.infer<typeof updateProductSchema>;
```

`@Can(ProductPolicy, 'create')` khiến guard gọi `create(user)` trước khi handler chạy:

```typescript
@@filename(src/products/products.controller)
import { Body, Controller, Get, Param, Patch, Post } from '@nestjs/common';
import { Authenticate, CurrentUser } from '@nestjs/authentication';
import { Can } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import { ProductPolicy } from './product.policy.js';
import { CreateProductDto, UpdateProductDto } from './products.dto.js';
import { ProductsService } from './products.service.js';

@Controller('products')
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Get()
  @Authenticate({ optional: true })
  @Can.Anyone()
  findAll(@CurrentUser() user: User | null) {
    return this.productsService.findAll(user);
  }

  @Get(':id')
  @Authenticate({ optional: true })
  @Can.Anyone()
  findOne(@CurrentUser() user: User | null, @Param('id') id: string) {
    return this.productsService.findOne(user, id);
  }

  @Post()
  @Can(ProductPolicy, 'create')
  create(@Body() input: CreateProductDto) {
    return this.productsService.create(input);
  }

  @Patch(':id')
  @Can(ProductPolicy, 'update')
  update(@Param('id') id: string, @Body() changes: UpdateProductDto) {
    return this.productsService.update(id, changes);
  }
}
```

Với các schema Zod, tham số body khai báo schema thay vì class:

```typescript
@@filename(src/products/products.controller)
import { createProductSchema, updateProductSchema, type CreateProductDto, type UpdateProductDto } from './products.schemas.js';
// ...
@Post()
@Can(ProductPolicy, 'create')
create(@Body({ schema: createProductSchema }) input: CreateProductDto) {
  return this.productsService.create(input);
}

@Patch(':id')
@Can(ProductPolicy, 'update')
update(@Param('id') id: string, @Body({ schema: updateProductSchema }) changes: UpdateProductDto) {
  return this.productsService.update(id, changes);
}
```

Một route có cho khách vãng lai vào hay không là quyết định của phần xác thực, không phải của policy. Các route đọc dùng `@Authenticate()` với `optional: true`: một request có token hợp lệ sẽ có người dùng của nó, còn một request không có token sẽ tiếp tục với `null`, đó cũng là thứ mà `@CurrentUser()` inject khi đó. Không có decorator này, khách vãng lai sẽ nhận lỗi 401 trước khi bất kỳ policy nào chạy. Nếu dùng `@Public()` thay vào đó, phần xác thực sẽ bỏ qua hoàn toàn token, nên Sam sẽ xem như một khách vãng lai và không bao giờ thấy bản nháp.

Các route đọc kiểm tra trong service, nên chúng khai báo `@Can.Anyone()`: bất kỳ ai mà phần xác thực cho qua đều có thể gọi chúng, và `ProductsService` quyết định mỗi người gọi thấy gì. Không có nó, guard sẽ từ chối chúng.

`@Can()` được kiểm tra type. Một ability viết sai chính tả sẽ không compile được:

```typescript
@Post()
@Can(ProductPolicy, 'craete')
// error TS2345: Argument of type '"craete"' is not assignable to parameter of type '"create" | "update" | "view" | "viewDrafts"'.
create(@Body() input: CreateProductDto) {}
```

Thông báo lỗi liệt kê các ability dùng được trên một route: những ability có tham số người dùng nhận `null`, vì guard không thể biết một route có người dùng hay không. `view` là một trong số đó, nhưng `@Can(ProductPolicy, 'view')` vẫn không compile được (`Expected 3 arguments, but got 2`): `view` còn nhận thêm sản phẩm, mà guard không có sản phẩm nào để truyền. Các bước kiểm tra cần một bản ghi thuộc về service, như trong `findOne()`. Một bước kiểm tra chỉ cần một id từ URL có thể nằm trên route, như phần [Kiểm tra route parameter](/security/authorization#check-a-route-parameter) chỉ ra.

Cuối cùng, đăng ký policy làm provider của feature module của nó:

```typescript
@@filename(src/products/products.module)
import { Module } from '@nestjs/common';
import { ProductPolicy } from './product.policy.js';
import { ProductsController } from './products.controller.js';
import { ProductsService } from './products.service.js';

@Module({
  controllers: [ProductsController],
  providers: [ProductsService, ProductPolicy],
})
export class ProductsModule {}
```

Thêm `ProductsModule` vào `imports` của `AppModule`. `@Policy()` cũng biến class thành injectable, và authorization module phát hiện mọi policy provider trong app, bất kể chúng được đăng ký ở đâu. Cách khác là liệt kê các policy trong tùy chọn `policies` của `AuthorizationModule.forRoot()`.

> info **Gợi ý** Nếu một `@Can()` trỏ tới một policy chưa ai đăng ký, app sẽ từ chối khởi động, và thông báo lỗi nêu tên handler.

#### Kiểm tra đơn hàng theo từng bản ghi <a id="check-orders-record-by-record"></a>

Đơn hàng là loại trong bài hướng dẫn Xác thực: nó thuộc về một khách hàng, qua `userId`, và chuyển qua vài trạng thái:

```typescript
@@filename(src/orders/order)
export interface OrderItem {
  productId: string;
  quantity: number;
}

export interface Order {
  id: string;
  userId: string;
  items: OrderItem[];
  /** In cents. */
  total: number;
  status: 'pending' | 'paid' | 'shipped' | 'refunded';
}
```

Alice có được xem một đơn hàng của Bob hay không phụ thuộc vào đơn hàng đó, nên các ability này nhận đơn hàng làm tham số thứ hai:

```typescript
@@filename(src/orders/order.policy)
import { Policy } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import type { Order } from './order.js';

@Policy()
export class OrderPolicy {
  viewAll(user: User) {
    return user.roles.includes('staff');
  }

  // Customers see their own orders; staff see everyone's.
  view(user: User, order: Order) {
    return order.userId === user.id || user.roles.includes('staff');
  }

  // Staff refund paid orders. Pending, shipped and refunded orders
  // can't be refunded by anyone.
  refund(user: User, order: Order) {
    return user.roles.includes('staff') && order.status === 'paid';
  }
}
```

Các ability này nhận `User`, không phải `User | null`. Mọi route đơn hàng đều yêu cầu người dùng đã đăng nhập, và một ability chỉ được service gọi có thể nói rõ điều đó. Khi đó trình biên dịch buộc bên gọi phải loại trừ trường hợp không có người dùng trước khi kiểm tra.

Bốn đơn hàng demo thay cho bảng đơn hàng, với id cố định giống các tài khoản demo: Alice có một đơn đã thanh toán và một đơn đã giao, Bob có một đơn đã thanh toán gồm năm túi hạt cá hồi (124,95, con số này quan trọng khi [một policy inject một service](/security/authorization#inject-a-service-into-a-policy)) và một đơn đang chờ:

```typescript
@@filename(src/orders/demo-orders)
import { alice, bob } from '../users/demo-users.js';
import type { Order } from './order.js';

/** The demo orders: Alice has a paid and a shipped one, Bob a paid and a pending one. */
export const alicePaid: Order = {
  id: 'b69f25e7-db50-4abe-86d3-2ef2bd148009',
  userId: alice.id,
  items: [{ productId: 'salmon-kibble-2kg', quantity: 1 }],
  total: 2499,
  status: 'paid',
};

export const aliceShipped: Order = {
  id: 'd626a0c1-4122-4f83-ab7a-b009c26f35c7',
  userId: alice.id,
  items: [{ productId: 'clumping-litter-10l', quantity: 1 }],
  total: 1599,
  status: 'shipped',
};

export const bobPaid: Order = {
  id: '0ea8343b-879d-4b83-884b-6d5bb02f802f',
  userId: bob.id,
  items: [{ productId: 'salmon-kibble-2kg', quantity: 5 }],
  total: 12495,
  status: 'paid',
};

export const bobPending: Order = {
  id: '7e7023d3-cb2a-48d2-8c4e-20c07e6b8c06',
  userId: bob.id,
  items: [{ productId: 'clumping-litter-10l', quantity: 1 }],
  total: 1599,
  status: 'pending',
};

export const demoOrders = [alicePaid, aliceShipped, bobPaid, bobPending];
```

`OrdersService` load đơn hàng, rồi kiểm tra quyền dựa trên nó:

```typescript
@@filename(src/orders/orders.service)
import { Injectable, NotFoundException } from '@nestjs/common';
import { AuthorizationService } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import { demoOrders } from './demo-orders.js';
import type { Order } from './order.js';
import { OrderPolicy } from './order.policy.js';

@Injectable()
export class OrdersService {
  // Stands in for your orders table: copies, since a refund changes an order's status.
  private readonly orders: Order[] = demoOrders.map((order) => ({ ...order }));

  constructor(private readonly authorizationService: AuthorizationService) {}

  async findAll(user: User) {
    // Filter lists in the query; policies check one record at a time.
    return (await this.authorizationService.can(OrderPolicy, 'viewAll', user))
      ? this.orders
      : this.orders.filter((order) => order.userId === user.id);
  }

  async findOne(user: User, id: string) {
    const order = this.find(id);
    await this.authorizationService.authorize(OrderPolicy, 'view', user, order);
    return order;
  }

  async refund(user: User, id: string) {
    const order = this.find(id);
    await this.authorizationService.authorize(OrderPolicy, 'refund', user, order);
    // Refund the payment through the payment provider here, then record it.
    order.status = 'refunded';
    return order;
  }

  private find(id: string) {
    const order = this.orders.find((order) => order.id === id);
    if (!order) {
      throw new NotFoundException();
    }
    return order;
  }
}
```

Mọi thứ sau class policy đều có type lấy từ signature của ability: tên ability, người dùng và đơn hàng. Một ability viết sai, thiếu đơn hàng, hoặc một object không phải `Order` đều không compile được, và một người dùng có thể là `null` cũng vậy:

```typescript
async show(user: User | null, order: Order) {
  await this.authorizationService.authorize(OrderPolicy, 'view', user, order);
  // error TS2345: Argument of type 'User | null' is not assignable to parameter of type 'User'.
}
```

Phần liệt kê không kiểm tra từng đơn hàng một. Nó hỏi một câu mà query có thể dùng (người dùng này có được xem mọi đơn hàng không?) rồi lọc ngay trong database. Kiểm tra từng dòng sau khi đã load hết sẽ lấy quá nhiều dữ liệu và làm hỏng việc phân trang.

Kiểm tra trong service thay vì trong controller có nghĩa là mọi bên gọi đều nhận cùng các quy tắc: một controller, một GraphQL resolver, hay một queue worker xử lý yêu cầu hoàn tiền.

Controller truyền người dùng đã đăng nhập xuống. `OrdersService` của bài hướng dẫn Xác thực thì đọc nó từ `AuthenticationContext`; ở đây nó là một tham số, nên signature của service cho biết một bước kiểm tra đang xét quyền của ai, và một queue worker có thể gọi nó cho một người dùng cụ thể. Mọi route đều kiểm tra trong service, nên mỗi route khai báo `@Can.Anyone()`:

```typescript
@@filename(src/orders/orders.controller)
import { Controller, Get, HttpCode, Param, Post } from '@nestjs/common';
import { CurrentUser } from '@nestjs/authentication';
import { Can } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import { OrdersService } from './orders.service.js';

@Controller('orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Get()
  @Can.Anyone()
  findAll(@CurrentUser() user: User) {
    return this.ordersService.findAll(user);
  }

  @Get(':id')
  @Can.Anyone()
  findOne(@CurrentUser() user: User, @Param('id') id: string) {
    return this.ordersService.findOne(user, id);
  }

  @Post(':id/refund')
  @HttpCode(200)
  @Can.Anyone()
  refund(@CurrentUser() user: User, @Param('id') id: string) {
    return this.ordersService.refund(user, id);
  }
}
```

```typescript
@@filename(src/orders/orders.module)
import { Module } from '@nestjs/common';
import { OrderPolicy } from './order.policy.js';
import { OrdersController } from './orders.controller.js';
import { OrdersService } from './orders.service.js';

@Module({
  controllers: [OrdersController],
  providers: [OrdersService, OrderPolicy],
})
export class OrdersModule {}
```

Thêm `OrdersModule` vào `imports` của `AppModule`. Giờ Alice nhận được hai đơn hàng của cô ấy từ `GET /orders`, và lỗi 403 từ `GET /orders/:id` với một đơn hàng của Bob.

> info **Gợi ý** Lỗi 403 xác nhận rằng đơn hàng có tồn tại. Nếu điều đó quan trọng, ví dụ khi id là số tăng dần và dễ đoán, hãy kiểm tra bằng `can()` và throw `NotFoundException` thay vào đó.

#### Kiểm tra route parameter <a id="check-a-route-parameter"></a>

Một số bước kiểm tra cần tham số nhưng không cần bản ghi. Nhân viên tra cứu đơn hàng của một khách hàng tại `GET /customers/:customerId/orders`, và khách hàng cũng có thể liệt kê đơn hàng của chính họ ở đó. Alice có được gọi nó hay không chỉ phụ thuộc vào id trong URL, nên không có gì cần load trước khi kiểm tra. Thêm một ability cho nó vào `OrderPolicy`:

```typescript
@@filename(src/orders/order.policy)
// Customers list their own orders; staff list anyone's. A guest is denied.
viewOrdersOf(user: User | null, customerId: string) {
  return !!user && (user.id === customerId || user.roles.includes('staff'));
}
```

Khác với các ability khác của `OrderPolicy`, ability này nhận `User | null`, vì một route ability phải chấp nhận khách vãng lai. Route kiểm tra nó bằng `@Can()`, với tham số thứ ba đọc các tham số đứng sau người dùng từ lời gọi:

```typescript
@@filename(src/orders/customer-orders.controller)
import { Controller, Get, Param } from '@nestjs/common';
import { Can } from '@nestjs/authorization';
import { OrderPolicy } from './order.policy.js';
import { OrdersService } from './orders.service.js';

@Controller('customers/:customerId/orders')
export class CustomerOrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Get()
  @Can(OrderPolicy, 'viewOrdersOf', (context) => [context.switchToHttp().getRequest().params.customerId])
  findAll(@Param('customerId') customerId: string) {
    return this.ordersService.findByCustomer(customerId);
  }
}
```

`OrdersService` có thêm một method lọc theo khách hàng, không có bước kiểm tra riêng, vì route đã có:

```typescript
@@filename(src/orders/orders.service)
findByCustomer(customerId: string) {
  return this.orders.filter((order) => order.userId === customerId);
}
```

Thêm controller vào `controllers` của `OrdersModule`. Giờ Alice nhận được đơn hàng của cô ấy từ `GET /customers/<Alice's id>/orders` và lỗi 403 với đơn hàng của Bob, Sam nhận được cả hai, còn khách vãng lai nhận lỗi 401.

Hàm được gán type theo chính các tham số của ability. Bỏ nó đi sẽ không compile được khi ability nhận nhiều hơn người dùng, và trả về sai type cũng vậy:

```typescript
@Get()
@Can(OrderPolicy, 'viewOrdersOf')
// error TS2554: Expected 3 arguments, but got 2.
findAll() {}

@Get()
@Can(OrderPolicy, 'viewOrdersOf', () => [42])
// error TS2322: Type 'number' is not assignable to type 'string'.
findAll() {}
```

Nó chạy trong guard, trước mọi pipe, nên nó nhận các giá trị đúng như transport gửi đến: route param là chuỗi, và chưa có gì được validate. Một `ParseUUIDPipe` trên `customerId` chạy sau bước kiểm tra, và một id mà người dùng không được xem sẽ nhận lỗi 403, không phải 400. Một lỗi mà hàm throw ra, như `BadRequestException` khi thiếu param, đến client HTTP nguyên vẹn. Trên WebSocket và microservice, Nest báo một `HttpException` từ bất kỳ guard nào, kể cả hàm này, thành lỗi nội bộ, nên hãy throw `WsException` hoặc `RpcException` ở đó. Một event từ chối mang theo những gì hàm đã đọc trong `args` của nó.

Hãy truyền định danh và phạm vi, không truyền bản ghi. Load đơn hàng trong guard sẽ load nó hai lần, một lần cho bước kiểm tra và một lần trong handler, và trả lời 403 trước khi handler kịp trả lời 404. Đó là lý do `GET /orders/:id` kiểm tra trong service.

Một hàm khai báo riêng sẽ trả về mảng thay vì tuple mà các tham số của ability mô tả, nên hãy kết thúc nó bằng `as const`. Điều đó giúp một helper nhỏ dùng lại được trên nhiều route:

```typescript
@@filename(src/common/param)
import type { ExecutionContext } from '@nestjs/common';

/** Reads one route param for `@Can()`. */
export const param = (name: string) => (context: ExecutionContext) =>
  [context.switchToHttp().getRequest().params[name] as string] as const;
```

```typescript
@Can(OrderPolicy, 'viewOrdersOf', param('customerId'))
```

Trên các transport khác, hãy đọc tham số từ context riêng của chúng: `GqlExecutionContext.create(context).getArgs()` cho tham số của một operation GraphQL, `context.switchToWs().getData()` cho một message WebSocket, và `context.switchToRpc().getData()` cho một message microservice.

#### Cho admin đi qua bằng `before()` <a id="let-admins-through-with-before"></a>

Admin được làm mọi thứ với danh mục sản phẩm, kể cả xóa sản phẩm, điều mà không ai khác được làm. Thay vì thêm bước kiểm tra admin vào mọi ability, hãy cho policy một hook `before()`:

```typescript
@@filename(src/products/product.policy)
import { Policy, type PolicyBefore } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import type { Product } from './product.js';

const isStaff = (user: User | null) => !!user?.roles.includes('staff');

@Policy()
export class ProductPolicy implements PolicyBefore<User> {
  // Admins pass every check below, including abilities added later.
  before(user: User | null) {
    if (user?.roles.includes('admin')) {
      return true;
    }
  }

  // `null` is a guest. Everyone sees published products; staff also see drafts.
  view(user: User | null, product: Product) {
    return product.published || isStaff(user);
  }

  viewDrafts(user: User | null) {
    return isStaff(user);
  }

  create(user: User | null) {
    return isStaff(user);
  }

  update(user: User | null) {
    return isStaff(user);
  }

  // Nobody but admins, who get through in before().
  delete(_user: User | null) {
    return false;
  }
}
```

`before()` chạy trước mọi ability của policy, cho cả kiểm tra trên route lẫn kiểm tra trong service. Nó nhận người dùng, tên ability, và các tham số của ability. Trả về `true` để cho phép, `false` để từ chối, hoặc không trả về gì để ability tự quyết định. Khách vãng lai cũng đi tới `before()`, nên tham số người dùng của nó phải nhận `null`. `before(user: User)` không compile được, bất kể class có implement `PolicyBefore<User>` hay không.

Thêm route dùng ability mới vào `ProductsController`, và import `Delete` cùng `HttpCode` từ `@nestjs/common`:

```typescript
@@filename(src/products/products.controller)
@Delete(':id')
@HttpCode(204)
@Can(ProductPolicy, 'delete')
remove(@Param('id') id: string) {
  this.productsService.remove(id);
}
```

Giờ Sam nhận lỗi 403 từ `DELETE /products/clumping-litter-10l`, còn Ada nhận 204.

> warning **Cảnh báo** `before()` bỏ qua mọi ability của policy, kể cả những quy tắc lẽ ra phải ràng buộc tất cả mọi người. Đó là lý do `OrderPolicy` không có đường tắt cho admin: "không ai được hoàn tiền một đơn hàng đã giao" phải đúng cả với Ada. Nếu một policy cần cả hai, hãy kiểm tra tên ability mà `before()` nhận được, và không trả về gì với những ability mà nó không được bỏ qua. Implement `PolicyBefore<User, Ability<OrderPolicy>>` và gán type cho tên là `Ability<OrderPolicy>`, để một tên loại trừ viết sai không compile được.

#### Inject service vào policy <a id="inject-a-service-into-a-policy"></a>

Bộ phận tài chính giới hạn số tiền mà mỗi nhân viên được tự hoàn: mặc định 100,00, cao hơn với một số người. Các giới hạn nằm bên ngoài policy, trong một service đọc từ một bảng hoặc một config service:

```typescript
@@filename(src/orders/refund-limits.service)
import { Injectable } from '@nestjs/common';
import { ada } from '../users/demo-users.js';
import type { User } from '../users/user.js';

@Injectable()
export class RefundLimitsService {
  // Per-person limits set by finance, in cents, by user id. Stands in for a table or a config service.
  private readonly limits = new Map<string, number>([[ada.id, 100_000]]);

  async maxRefundFor(user: User): Promise<number> {
    return this.limits.get(user.id) ?? 10_000;
  }
}
```

Vì policy là provider, nó inject service qua constructor. Ability `refund` trở thành `async`:

```typescript
@@filename(src/orders/order.policy)
import { Policy } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import type { Order } from './order.js';
import { RefundLimitsService } from './refund-limits.service.js';

@Policy()
export class OrderPolicy {
  constructor(private readonly refundLimitsService: RefundLimitsService) {}

  viewAll(user: User) {
    return user.roles.includes('staff');
  }

  // Customers see their own orders; staff see everyone's.
  view(user: User, order: Order) {
    return order.userId === user.id || user.roles.includes('staff');
  }

  // Customers list their own orders; staff list anyone's. A guest is denied.
  viewOrdersOf(user: User | null, customerId: string) {
    return !!user && (user.id === customerId || user.roles.includes('staff'));
  }

  // Staff refund paid orders up to their limit. Pending, shipped and
  // refunded orders can't be refunded by anyone.
  async refund(user: User, order: Order) {
    if (!user.roles.includes('staff') || order.status !== 'paid') {
      return false;
    }
    return order.total <= (await this.refundLimitsService.maxRefundFor(user));
  }
}
```

`authorize()`, `can()` và guard đều await các ability async, nên `OrdersService` không thay đổi. Đăng ký service cạnh policy:

```typescript
@@filename(src/orders/orders.module)
import { Module } from '@nestjs/common';
import { CustomerOrdersController } from './customer-orders.controller.js';
import { OrderPolicy } from './order.policy.js';
import { OrdersController } from './orders.controller.js';
import { OrdersService } from './orders.service.js';
import { RefundLimitsService } from './refund-limits.service.js';

@Module({
  controllers: [OrdersController, CustomerOrdersController],
  providers: [OrdersService, OrderPolicy, RefundLimitsService],
})
export class OrdersModule {}
```

Vì `OrderPolicy` được đăng ký trong `OrdersModule`, nó có thể inject các provider của module đó. Một policy liệt kê trong tùy chọn `policies` của `forRoot()` thì nằm trong authorization module, và cần tùy chọn `imports` để tiếp cận các dependency của nó.

Đơn hàng đã thanh toán của Bob là 124,95. Giờ Sam (giới hạn 100,00) nhận lỗi 403 khi cố hoàn tiền nó, còn Ada (giới hạn 1.000,00) thì thành công.

> warning **Cảnh báo** Policy phải là singleton. Một policy request-scoped hoặc transient, hoặc một policy phụ thuộc vào provider request-scoped, sẽ throw lúc khởi động. Đừng để state theo request trong policy, và hãy truyền những gì ability cần dưới dạng tham số.

#### Phân biệt khách vãng lai với người dùng bị cấm, và cung cấp quyền hạn <a id="tell-guests-from-forbidden-users-and-expose-permissions"></a>

Một request bị từ chối sẽ nhận lỗi 401 hoặc 403, tùy theo ai đang hỏi và hỏi ở đâu:

| Người gọi        | Route                                                                                     | Status                                             | Đến từ                                  |
| ---------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------- |
| Khách vãng lai   | Yêu cầu đăng nhập (mặc định), như `POST /products` hoặc `GET /orders`                     | 401, kèm `WWW-Authenticate: Bearer realm="store"`  | Xác thực, trước khi bất kỳ policy nào chạy |
| Khách vãng lai   | Xác thực tùy chọn, và policy từ chối `null`, như một sản phẩm nháp                        | 401                                                | Phân quyền                              |
| Người dùng đã đăng nhập | Policy từ chối, như Alice trên `POST /products` hoặc trên một đơn hàng của Bob    | 403                                                | Phân quyền                              |

Phân quyền không bao giờ quyết định một route có cần người dùng hay không; đó là việc của xác thực. Khi một policy từ chối khách vãng lai, package trả lời 401 ("hãy đăng nhập rồi thử lại") thay vì 403 ("không bao giờ"), vì đăng nhập có thể thay đổi câu trả lời.

Bản thân `authorize()` throw một `AuthorizationError`, có `reason` là `unauthenticated` hoặc `forbidden`, và `status` là 401 hoặc 403 tương ứng. Nó không phải HTTP exception, vì cùng service đó còn chạy trong queue worker và WebSocket gateway. Khi lỗi thoát ra khỏi handler, `AuthorizationModule` biến nó thành `UnauthorizedException` hoặc `ForbiddenException` giống như guard throw, với cùng body, nên exception filter và client xử lý cả hai như mọi lỗi HTTP khác. Trong WebSocket gateway và handler của microservice, nó trở thành `WsException` hoặc `RpcException`. Body của lỗi 403 không nêu tên ability.

`can()` không bao giờ throw khi bị từ chối. Nó resolve ra `false` cho cả khách vãng lai lẫn người dùng bị cấm, khiến nó trở thành công cụ để định hình response. Hãy cho mỗi đơn hàng một flag `canRefund`, để frontend hiển thị nút hoàn tiền mà không phải lặp lại các quy tắc:

```typescript
@@filename(src/orders/orders.service)
import { Injectable, NotFoundException } from '@nestjs/common';
import { AuthorizationService } from '@nestjs/authorization';
import type { User } from '../users/user.js';
import { demoOrders } from './demo-orders.js';
import type { Order } from './order.js';
import { OrderPolicy } from './order.policy.js';

export type OrderView = Order & { canRefund: boolean };

@Injectable()
export class OrdersService {
  // Stands in for your orders table: copies, since a refund changes an order's status.
  private readonly orders: Order[] = demoOrders.map((order) => ({ ...order }));

  constructor(private readonly authorizationService: AuthorizationService) {}

  async findAll(user: User): Promise<OrderView[]> {
    // Filter lists in the query; policies check one record at a time.
    const orders = (await this.authorizationService.can(OrderPolicy, 'viewAll', user))
      ? this.orders
      : this.orders.filter((order) => order.userId === user.id);
    return Promise.all(orders.map((order) => this.toView(user, order)));
  }

  async findOne(user: User, id: string): Promise<OrderView> {
    const order = this.find(id);
    await this.authorizationService.authorize(OrderPolicy, 'view', user, order);
    return this.toView(user, order);
  }

  async refund(user: User, id: string): Promise<OrderView> {
    const order = this.find(id);
    await this.authorizationService.authorize(OrderPolicy, 'refund', user, order);
    // Refund the payment through the payment provider here, then record it.
    order.status = 'refunded';
    return this.toView(user, order);
  }

  private async toView(user: User, order: Order): Promise<OrderView> {
    return { ...order, canRefund: await this.authorizationService.can(OrderPolicy, 'refund', user, order) };
  }

  private find(id: string) {
    const order = this.orders.find((order) => order.id === id);
    if (!order) {
      throw new NotFoundException();
    }
    return order;
  }
}
```

Flag lấy từ cùng ability `refund` mà `POST /orders/:id/refund` áp dụng, nên nút bấm và endpoint không thể bất đồng. Sam thấy `canRefund: true` trên đơn hàng đã thanh toán của Alice và `false` trên đơn của Bob, vốn vượt quá giới hạn của anh ấy. Ada thấy `true` trên cả hai.

#### Thử ngay <a id="try-it"></a>

Khởi động ứng dụng với file `.env` chứa signing secret:

```bash
$ npm run start:dev -- --env-file .env
```

Trong một terminal khác, đăng nhập với tư cách Alice, Sam và Ada. `--json` (curl 7.82 trở lên) gửi một `POST` với body JSON, và helper `token` dùng [jq](https://jqlang.org/) để lấy access token ra:

```bash
$ token() { curl -s localhost:3000/auth/token --json "{\"email\":\"$1@example.com\",\"password\":\"catnip4all\"}" | jq -r .accessToken; }
$ ALICE=$(token alice) SAM=$(token sam) ADA=$(token ada)
```

Khách vãng lai thấy các sản phẩm đã đăng. Nhân viên thấy cả bản nháp:

```bash
$ curl localhost:3000/products
[{"id":"salmon-kibble-2kg","name":"Salmon kibble, 2 kg","price":2499,"published":true},{"id":"clumping-litter-10l","name":"Clumping litter, 10 l","price":1599,"published":true}]

$ curl -s localhost:3000/products -H "Authorization: Bearer $SAM" | jq -c '.[] | {id, published}'
{"id":"salmon-kibble-2kg","published":true}
{"id":"clumping-litter-10l","published":true}
{"id":"heated-cat-bed","published":false}
```

Bản thân bản nháp là lỗi 401 với khách vãng lai và 403 với khách hàng. Header của response được rút gọn ở đây và bên dưới:

```bash
$ curl -i localhost:3000/products/heated-cat-bed
HTTP/1.1 401 Unauthorized
{"message":"Unauthorized","statusCode":401}

$ curl -i localhost:3000/products/heated-cat-bed -H "Authorization: Bearer $ALICE"
HTTP/1.1 403 Forbidden
{"message":"Forbidden","statusCode":403}
```

Chỉ nhân viên mới thêm sản phẩm. Phần xác thực chặn khách vãng lai, còn `@Can()` chặn Alice:

```bash
$ curl -i localhost:3000/products --json '{"name":"Sisal scratching post","price":3999,"published":false}'
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="store"
{"message":"Unauthorized","statusCode":401}

$ curl -i localhost:3000/products -H "Authorization: Bearer $ALICE" --json '{"name":"Sisal scratching post","price":3999,"published":false}'
HTTP/1.1 403 Forbidden
{"message":"Forbidden","statusCode":403}

$ curl localhost:3000/products -H "Authorization: Bearer $SAM" --json '{"name":"Sisal scratching post","price":3999,"published":false}'
{"name":"Sisal scratching post","price":3999,"published":false,"id":"sisal-scratching-post"}
```

Alice thấy đơn hàng của chính cô ấy và không hoàn tiền được đơn nào. Sam thấy mọi đơn hàng, với các flag `canRefund` của riêng anh ấy. Đơn hàng đã thanh toán của Bob nằm ngoài giới hạn của Alice:

```bash
$ curl -s localhost:3000/orders -H "Authorization: Bearer $ALICE" | jq -c '.[] | {id, status, canRefund}'
{"id":"b69f25e7-db50-4abe-86d3-2ef2bd148009","status":"paid","canRefund":false}
{"id":"d626a0c1-4122-4f83-ab7a-b009c26f35c7","status":"shipped","canRefund":false}

$ curl -s localhost:3000/orders -H "Authorization: Bearer $SAM" | jq -c '.[] | {id, status, total, canRefund}'
{"id":"b69f25e7-db50-4abe-86d3-2ef2bd148009","status":"paid","total":2499,"canRefund":true}
{"id":"d626a0c1-4122-4f83-ab7a-b009c26f35c7","status":"shipped","total":1599,"canRefund":false}
{"id":"0ea8343b-879d-4b83-884b-6d5bb02f802f","status":"paid","total":12495,"canRefund":false}
{"id":"7e7023d3-cb2a-48d2-8c4e-20c07e6b8c06","status":"pending","total":1599,"canRefund":false}

$ curl -i localhost:3000/orders/0ea8343b-879d-4b83-884b-6d5bb02f802f -H "Authorization: Bearer $ALICE"
HTTP/1.1 403 Forbidden
{"message":"Forbidden","statusCode":403}
```

Sam hoàn tiền đơn hàng đã thanh toán của Alice, nhưng không hoàn được đơn đã giao của cô ấy, và cũng không hoàn được đơn của Bob, vốn vượt quá giới hạn của anh ấy. Ada cũng không hoàn tiền được đơn đã giao, nhưng đơn của Bob nằm trong giới hạn của cô ấy:

```bash
$ curl -s -X POST localhost:3000/orders/b69f25e7-db50-4abe-86d3-2ef2bd148009/refund -H "Authorization: Bearer $SAM" | jq -c '{id, status, canRefund}'
{"id":"b69f25e7-db50-4abe-86d3-2ef2bd148009","status":"refunded","canRefund":false}

$ curl -i -X POST localhost:3000/orders/d626a0c1-4122-4f83-ab7a-b009c26f35c7/refund -H "Authorization: Bearer $SAM"
HTTP/1.1 403 Forbidden
{"message":"Forbidden","statusCode":403}

$ curl -i -X POST localhost:3000/orders/0ea8343b-879d-4b83-884b-6d5bb02f802f/refund -H "Authorization: Bearer $SAM"
HTTP/1.1 403 Forbidden
{"message":"Forbidden","statusCode":403}

$ curl -i -X POST localhost:3000/orders/d626a0c1-4122-4f83-ab7a-b009c26f35c7/refund -H "Authorization: Bearer $ADA"
HTTP/1.1 403 Forbidden
{"message":"Forbidden","statusCode":403}

$ curl -s -X POST localhost:3000/orders/0ea8343b-879d-4b83-884b-6d5bb02f802f/refund -H "Authorization: Bearer $ADA" | jq -c '{id, status, canRefund}'
{"id":"0ea8343b-879d-4b83-884b-6d5bb02f802f","status":"refunded","canRefund":false}
```

Chỉ admin mới xóa được sản phẩm:

```bash
$ curl -i -X DELETE localhost:3000/products/clumping-litter-10l -H "Authorization: Bearer $SAM"
HTTP/1.1 403 Forbidden
{"message":"Forbidden","statusCode":403}

$ curl -i -X DELETE localhost:3000/products/clumping-litter-10l -H "Authorization: Bearer $ADA"
HTTP/1.1 204 No Content
```
#### Test <a id="testing"></a>

Một end-to-end test khởi động toàn bộ app, đăng nhập qua endpoint thật, và kiểm tra các quy tắc qua HTTP. Giống như trong bài hướng dẫn Xác thực, scrypt cố ý chậm, nên bài test ghi đè `PasswordHasher` bằng một bản rẻ hơn, và ứng dụng đọc `JWT_SECRET` lúc bootstrap, nên cấu hình test cung cấp một giá trị:

```typescript
@@filename(vitest.config)
export default defineConfig({
  // ...
  test: {
    // ...
    env: {
      JWT_SECRET: 'test-only-jwt-secret-of-at-least-32-bytes',
    },
  },
});
```

```typescript
@@filename(test/orders.e2e-spec)
import type { INestApplication } from '@nestjs/common';
import { PasswordHasher } from '@nestjs/authentication';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';
import { alicePaid, aliceShipped, bobPaid } from '../src/orders/demo-orders.js';

describe('Orders (e2e)', () => {
  let app: INestApplication;

  const signIn = async (email: string) => {
    const { body } = await request(app.getHttpServer())
      .post('/auth/token')
      .send({ email, password: 'catnip4all' })
      .expect(200);
    return `Bearer ${body.accessToken}`;
  };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      // scrypt is slow on purpose; the tests don't need it to be.
      .overrideProvider(PasswordHasher)
      .useValue(new PasswordHasher({ logN: 11 }))
      .compile();
    app = moduleRef.createNestApplication();
    await app.listen(0, '127.0.0.1');
  });

  afterAll(() => app.close());

  it('asks guests to sign in', async () => {
    await request(app.getHttpServer()).get('/orders').expect(401);
  });

  it('shows customers only their own orders', async () => {
    const alice = await signIn('alice@example.com');
    const { body } = await request(app.getHttpServer())
      .get('/orders')
      .set('Authorization', alice)
      .expect(200);
    expect(body.map((order: { id: string }) => order.id)).toEqual([alicePaid.id, aliceShipped.id]);

    await request(app.getHttpServer()).get(`/orders/${bobPaid.id}`).set('Authorization', alice).expect(403);
  });

  it('lets staff refund a paid order once, within their limit', async () => {
    const sam = await signIn('sam@example.com');
    const refund = (id: string) =>
      request(app.getHttpServer()).post(`/orders/${id}/refund`).set('Authorization', sam);

    await refund(alicePaid.id).expect(200);
    await refund(alicePaid.id).expect(403); // already refunded
    await refund(aliceShipped.id).expect(403); // shipped
    await refund(bobPaid.id).expect(403); // over Sam's limit
  });
});
```

Một policy là một class thông thường, nên các quy tắc của nó dễ unit test mà không cần Nest. Hãy tự khởi tạo policy và kiểm soát các dependency của nó; các tài khoản và đơn hàng demo kiêm luôn vai trò fixture:

```typescript
@@filename(src/orders/order.policy.spec)
import { vi } from 'vitest';
import { alice, sam } from '../users/demo-users.js';
import { alicePaid, bobPaid } from './demo-orders.js';
import { OrderPolicy } from './order.policy.js';
import { RefundLimitsService } from './refund-limits.service.js';

describe('OrderPolicy', () => {
  // No Nest here: a policy is a class, so construct it yourself.
  const refundLimits = new RefundLimitsService();
  const policy = new OrderPolicy(refundLimits);

  it('shows customers only their own orders', () => {
    expect(policy.view(alice, alicePaid)).toBe(true);
    expect(policy.view(alice, bobPaid)).toBe(false);
    expect(policy.view(sam, bobPaid)).toBe(true);
  });

  it('lets staff refund paid orders up to their limit', async () => {
    vi.spyOn(refundLimits, 'maxRefundFor').mockResolvedValue(5000);

    expect(await policy.refund(sam, { ...alicePaid, total: 5000 })).toBe(true);
    expect(await policy.refund(sam, { ...alicePaid, total: 5001 })).toBe(false);
    expect(await policy.refund(alice, alicePaid)).toBe(false);
  });

  it('refuses refunds on orders that are not paid', async () => {
    for (const status of ['pending', 'shipped', 'refunded'] as const) {
      expect(await policy.refund(sam, { ...alicePaid, status })).toBe(false);
    }
  });
});
```

Gọi trực tiếp một ability sẽ bỏ qua `before()`. Hook chỉ là một method khác, nên hãy test nó theo cùng cách, ví dụ `expect(new ProductPolicy().before(ada)).toBe(true)`. Để test hook cùng với ability, hãy đi qua `AuthorizationService`, và để test cả việc ánh xạ 401/403, hãy đi qua HTTP, như end-to-end test làm.

Một bài test service nằm ở giữa: policy thật và `AuthorizationModule`, không có HTTP hay đăng nhập. Bên ngoài handler, một lời từ chối vẫn là `AuthorizationError`:

```typescript
@@filename(src/orders/orders.service.spec)
import { Test } from '@nestjs/testing';
import { AuthorizationError, AuthorizationModule } from '@nestjs/authorization';
import { alice, sam } from '../users/demo-users.js';
import { alicePaid, bobPaid } from './demo-orders.js';
import { OrderPolicy } from './order.policy.js';
import { OrdersService } from './orders.service.js';
import { RefundLimitsService } from './refund-limits.service.js';

describe('OrdersService', () => {
  let orders: OrdersService;

  beforeEach(async () => {
    // The real policy and module, no HTTP and no sign-in.
    const moduleRef = await Test.createTestingModule({
      imports: [AuthorizationModule.forRoot()],
      providers: [OrdersService, OrderPolicy, RefundLimitsService],
    }).compile();
    orders = moduleRef.get(OrdersService);
  });

  it("keeps Bob's order from Alice", async () => {
    await expect(orders.findOne(alice, bobPaid.id)).rejects.toThrow(AuthorizationError);
  });

  it('refunds within the limit only', async () => {
    await expect(orders.refund(sam, bobPaid.id)).rejects.toMatchObject({ reason: 'forbidden', ability: 'refund' });
    expect((await orders.refund(sam, alicePaid.id)).status).toBe('refunded');
  });
});
```

Để thay một policy trong một bài test lớn hơn, hãy ghi đè nó như mọi provider khác, ví dụ `.overrideProvider(OrderPolicy).useValue(...)`: mọi bước kiểm tra, trên route lẫn trong service, đều chạy với bản ghi đè.

#### Checklist cho production <a id="production-checklist"></a>

- **Giữ xác thực đứng trước phân quyền.** Với `AuthenticationModule`, thứ tự import sai sẽ làm app dừng lúc khởi động. Với một authentication guard khác, nó chỉ log một lỗi, nên hãy có một end-to-end test đăng nhập và gọi một route `@Can()`. Có hai cách đăng ký luôn chạy sau authorization guard, bất kể thứ tự import: một `APP_GUARD` request-scoped (bước kiểm tra lúc khởi động có báo điều này) và `app.useGlobalGuards()` (bước kiểm tra không thể phát hiện). Hãy đăng ký xác thực như một singleton `APP_GUARD`.
- **Rà soát mọi `@Can.Anyone()`.** Guard từ chối handler không khai báo bước kiểm tra nào, và log từng handler như vậy lúc khởi động, nên một `@Can()` bị quên sẽ đóng route lại. `@Can.Anyone()` mở route cho mọi người mà phần xác thực cho qua: hãy kiểm tra service của nó có kiểm tra quyền không, hoặc route có thực sự không cần quyền gì không. Một bước kiểm tra trên id trong URL có thể đặt trên route, bằng tham số thứ ba của `@Can()`, nơi một lần sửa handler sau này không thể làm rơi mất nó.
- **Kết nối microservice với `inheritAppConfig: true`.** Trong một hybrid app, Nest chỉ chạy global guard và interceptor của app trên message handler khi `connectMicroservice()` nhận tùy chọn đó. Không có nó, `@Can()` trên một message handler sẽ không được áp dụng, và một lời từ chối từ `authorize()` sẽ đến client dưới dạng lỗi nội bộ thay vì 401 hay 403.
- **Đặt các bước kiểm tra bản ghi trong service**, sau khi load bản ghi, để controller, resolver và queue worker dùng chung chúng.
- **Đừng cache response theo URL trên các route kiểm tra bản ghi.** Một cache như `CacheInterceptor` của Nest trả lời trước khi handler chạy, nên nó sẽ phục vụ đơn hàng của Bob cho Alice mà không hỏi `OrderPolicy`. Hãy cache ở bên dưới bước kiểm tra, hoặc cache theo từng người dùng.
- **Lọc danh sách ngay trong query** bằng một câu hỏi mà query có thể dùng, như `viewAll`, thay vì load mọi dòng rồi kiểm tra từng dòng.
- **Kiểm tra lại trạng thái khi ghi.** Phân quyền đọc đơn hàng trước khi hoàn tiền, và hai request đồng thời có thể cùng thấy `paid`. Hãy làm cho thao tác ghi có điều kiện (chỉ cập nhật trạng thái ở chỗ nó vẫn còn là `paid`), và gửi cho payment provider một idempotency key, để một lần retry không bao giờ hoàn tiền hai lần.
- **Chọn giữa 403 và 404** cho những bản ghi mà sự tồn tại của chúng là nhạy cảm, như đơn hàng của khách hàng khác khi id là số tăng dần.
- **Giữ policy stateless.** Chúng là singleton dùng chung cho mọi request.
- **Để ý chi phí của các flag `can()`.** Mỗi flag chạy ability một lần cho mỗi dòng, kể cả mọi công việc async. Hãy cache các phép tra cứu chậm như giới hạn hoàn tiền, hoặc load chúng một lần cho mỗi request.
- **Load secret từ cấu hình.** Hãy đọc JWT secret (ít nhất 32 byte) từ một secret manager hoặc `ConfigService`, không phải từ code.
- **Kiểm tra bằng `can()` trong guard và middleware của riêng bạn.** Chúng chạy trước mọi handler, nên một `AuthorizationError` throw ở đó sẽ không được biến thành 401 hay 403. Nó trở thành lỗi 500.
- **Ghi lại audit các lời từ chối.** Response không cho biết bước kiểm tra nào đã từ chối người gọi. Hãy subscribe `AuthorizationEvents` để log policy, ability và id người dùng cho mọi lời từ chối. Mỗi event mang theo người dùng và bản ghi đúng như policy đã thấy, nên hãy log những trường bạn cần thay vì toàn bộ event.

#### Tham khảo <a id="reference"></a>

##### Tùy chọn module <a id="module-options"></a>

`AuthorizationModule.forRoot()` nhận các tùy chọn này. `forRootAsync()` nhận `policies`, `imports`, `globalGuard` và `isGlobal` ở cấp cao nhất, cạnh `useFactory`, và factory của nó trả về `getUser`.

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `getUser` | `defaultGetUser` | Một hàm nhận `ExecutionContext` và trả về người dùng hiện tại, hoặc một promise của nó. Xem [Đăng ký authorization module](/security/authorization#register-the-authorization-module). |
| `policies` | không có | Các policy được đăng ký trong chính authorization module. Một provider `@Policy()` ở bất kỳ module nào đều được tìm thấy mà không cần liệt kê. |
| `imports` | không có | Các module có provider được export mà `policies` inject. |
| `globalGuard` | `true` | Đăng ký `AuthorizationGuard` làm global guard. Với `false`, hãy áp dụng nó bằng `@UseGuards()` sau authentication guard của bạn. |
| `isGlobal` | `true` | Đăng ký module ở cấp global. |

`defaultGetUser` đọc người dùng từ các vị trí sau. `null`, `undefined` và `false` đều có nghĩa là khách vãng lai.

| Context | Nguồn |
| --- | --- |
| HTTP | `request.user` |
| GraphQL | người dùng mà phần xác thực đã ghi nhận cho operation này, nếu không thì `req.user` trên GraphQL context |
| WebSocket | người dùng mà phần xác thực đã ghi nhận cho message này, nếu không thì `client.user`, rồi `client.data.user` |
| Microservice | `user` trên transport context, không bao giờ lấy từ payload của message |

Một WebSocket client là kết nối, không phải message, và qua `graphql-ws`, `req` trên GraphQL context là upgrade request của socket, thứ mà mọi operation trên socket dùng chung. Vì vậy `client.user` và `req.user` chứa người dùng của message hoặc operation nào xác thực sau cùng. `@nestjs/authentication` cũng để lại một hàm trên client và trên `req`, dưới `Symbol.for('nestjs.authentication.userOf')`, hàm này nhận `ExecutionContext` và trả lời bằng người dùng của message hoặc operation đó: `null` với một message/operation ẩn danh, như mọi cái `@Public()`, hoặc `undefined` khi nó không có câu trả lời. `defaultGetUser` hỏi nó trước. Do đó một message hoặc operation `@Public()` là khách vãng lai đối với `@Can()`, kể cả trên một socket có handshake đã đăng nhập, và một session đã bị thu hồi bởi việc đăng xuất khỏi mọi nơi không còn được tính nữa. Một `getUser` của riêng bạn đọc `client.user` hoặc `req.user` trên các transport này sẽ thấy người dùng sau cùng của socket; các package xác thực khác có thể để lại cùng hàm đó để được hỏi.

##### Những gì một route khai báo <a id="what-a-route-declares"></a>

Guard quyết định dựa trên những gì handler và class của nó khai báo:

| Khai báo | Guard |
| --- | --- |
| `@Can()` | Chạy mọi yêu cầu của class, rồi đến của method. Tất cả đều phải đạt. |
| `@Can.Anyone()` | Cho qua bất kỳ ai mà phần xác thực cho qua. |
| `@Public()` từ `@nestjs/authentication` (0.1.0 trở lên) | Giống như `@Can.Anyone()`. |
| Không có gì | Từ chối: 403 với người dùng, 401 với khách vãng lai. Log lúc khởi động nêu tên handler. |

Trên một method, `@Can.Anyone()` hoặc `@Public()` gỡ bỏ `@Can()` của class, giống như `@Public()` gỡ bỏ yêu cầu xác thực của class. Một `@Can()` trên chính method vẫn được áp dụng, nên một method `@Public()` có `@Can()` sẽ chạy bước kiểm tra cho khách vãng lai. Trên một class, không cái nào gỡ bỏ được `@Can()` của method. Một method được `@Authenticate()` đưa trở lại dưới yêu cầu xác thực bên trong một class `@Public()` thì không còn công khai, và cần một khai báo riêng.

Ở những nơi Nest không chạy global guard nào, không có gì bị từ chối: trên GraphQL field resolver trừ khi `fieldResolverEnhancers` bao gồm `'guards'`, và trên message handler của một hybrid app được kết nối mà không có `inheritAppConfig: true`. Với enhancer đó, mọi `@ResolveField()` cũng cần một khai báo. Một khai báo ở cấp class sẽ bao phủ chúng.

##### Event <a id="events"></a>

`AuthorizationEvents` cung cấp mọi lời từ chối trên observable `events$` của nó, và công bố nó trên một diagnostics channel. `can()` resolve ra `false` không phải là lời từ chối và không phát ra gì cả.

| Loại event | Channel | Khi nào |
| --- | --- | --- |
| `denied` | `nestjs:authorization:denied` | `@Can()` hoặc `authorize()` đã từ chối một người gọi |

Payload `AuthorizationDeniedEvent` có các trường sau:

- `type`: `'denied'`.
- `policy` và `ability`: tên class policy và ability đã từ chối, như `OrderPolicy` và `refund`. Cả hai là `null` khi guard từ chối một handler không khai báo bước kiểm tra nào.
- `reason`: `'unauthenticated'` với khách vãng lai, `'forbidden'` với người dùng đã đăng nhập.
- `user`: người dùng mà policy đã thấy, `null` với khách vãng lai.
- `args`: các tham số của ability đứng sau người dùng, như bản ghi. Với `@Can()`, là những gì tham số thứ ba của nó đọc được, hoặc rỗng nếu không có.
- `handler`: handler mà `@Can()` đã bảo vệ, như `ProductsController.create`. Không có với `authorize()`.

##### Lỗi <a id="errors"></a>

`authorize()` throw một `AuthorizationError` với `reason`, `status`, `policy` và `ability`. Lời từ chối của guard với một handler không khai báo bước kiểm tra nào mang cùng lỗi đó, với `policy` và `ability` đặt là `null`. Khi nó thoát ra khỏi handler, hoặc khi `@Can()` từ chối, người gọi nhận lỗi riêng của transport, với body không bao giờ nêu tên policy hay ability. Xem [Phân biệt khách vãng lai với người dùng bị cấm, và cung cấp quyền hạn](/security/authorization#tell-guests-from-forbidden-users-and-expose-permissions).

| `reason` | `status` | HTTP | GraphQL `extensions.code` | WebSocket và microservice |
| --- | --- | --- | --- | --- |
| `unauthenticated` | 401 | `UnauthorizedException` | `UNAUTHENTICATED` | `WsException` hoặc `RpcException` với `statusCode: 401` |
| `forbidden` | 403 | `ForbiddenException` | `FORBIDDEN` | `WsException` hoặc `RpcException` với `statusCode: 403` |

Qua `graphql-ws`, client nhận message của lỗi, `Unauthorized` hoặc `Forbidden`, mà không có `extensions.code`: Apollo driver thêm các mã này trong phần định dạng lỗi của nó, phần này không chạy trên transport đó.

Một `AuthorizationError` throw bên ngoài handler, như trong guard hoặc middleware của riêng bạn, sẽ không được ánh xạ và trở thành lỗi 500.
