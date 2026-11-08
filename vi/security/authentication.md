### Xác thực

`@nestjs/authentication` đăng nhập người dùng và cho phần còn lại của ứng dụng biết họ là ai. Nó đăng ký một global guard, cung cấp decorator và một context có thể inject để đọc người dùng hiện tại, và có sẵn những thành phần mà mọi luồng đăng nhập đều cần: session phía server, hash mật khẩu, link xác minh email và đặt lại mật khẩu, xác thực hai lớp TOTP, magic link, OpenID Connect, access token và refresh token, và API key. Tất cả đều xây dựng trên các thành phần có sẵn của Node.js, và giữ state trong database của bạn thông qua một store mà bạn viết theo các interface đã được mô tả, kèm bộ test của package để kiểm tra nó. Bạn chỉ viết những gì mà riêng ứng dụng của bạn biết: cách load một người dùng, route nào là công khai, và các endpoint của luồng đăng nhập.

Trong bài hướng dẫn này, bạn sẽ thêm tính năng đăng nhập vào API của một cửa hàng online bán thức ăn và đồ dùng cho mèo. Khi hoàn thành, nó sẽ:

- Cho khách hàng đăng nhập bằng mật khẩu, bằng Google, hoặc bằng link gửi qua email, và giữ trạng thái đăng nhập cho web app bằng session cookie.
- Xác minh địa chỉ email của khách hàng, và cho họ đặt lại mật khẩu khi quên.
- Cấp cho app mobile các bearer token ngắn hạn và refresh token có xoay vòng.
- Cung cấp xác thực hai lớp bằng app authenticator, và yêu cầu nó khi đổi địa chỉ email của tài khoản.
- Cho khách hàng xem họ đang đăng nhập ở đâu, và đăng xuất khỏi mọi nơi.
- Giới hạn tốc độ đoán mật khẩu của bất kỳ ai.
- Giữ session, token và các link đang chờ trong PostgreSQL, qua Drizzle (hoặc TypeORM).
- Cho hệ thống của đối tác và script của khách hàng gọi API bằng các key mà khách hàng tự tạo và thu hồi.

Đây là các endpoint bạn sẽ xây dựng, cùng phần hướng dẫn thêm từng endpoint:

| Endpoint | Phần |
| --- | --- |
| `POST /auth/sign-up`, `POST /auth/sign-in` | [Thêm đăng ký và đăng nhập](/security/authentication#add-sign-up-and-sign-in) |
| `POST /auth/email/verify`, `POST /auth/email/verification` | [Xác minh địa chỉ email](/security/authentication#verify-email-addresses) |
| `POST /auth/password/forgot`, `POST /auth/password/reset` | [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords) |
| `GET /me`, `GET /orders`, `POST /orders` | [Đọc người dùng hiện tại](/security/authentication#read-the-current-user) |
| `POST /auth/token`, `POST /auth/token/refresh` | [Cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app) |
| `POST /auth/mfa/enroll`, `POST /auth/mfa/replace`, `POST /auth/mfa/confirm`, `POST /auth/mfa/verify`, `PATCH /me/email` | [Thêm xác thực hai lớp](/security/authentication#add-two-factor-authentication) |
| `GET /auth/oidc/google/login`, `GET /auth/oidc/google/callback` | [Thêm "Đăng nhập bằng Google"](/security/authentication#add-sign-in-with-google) |
| `POST /auth/magic-link`, `POST /auth/magic-link/consume` | [Thêm đăng nhập bằng magic link](/security/authentication#add-magic-link-sign-in) |
| `GET /auth/sessions`, `DELETE /auth/sessions/:id`, `POST /auth/sign-out`, `POST /auth/sign-out-everywhere`, `POST /auth/token/revoke` | [Cho khách hàng quản lý session](/security/authentication#let-customers-manage-their-sessions) |
| `POST /auth/api-keys`, `GET /auth/api-keys`, `DELETE /auth/api-keys/:id` | [Cấp API key cho đối tác](/security/authentication#issue-api-keys-to-partners) |

#### Cài đặt <a id="installation"></a>

Cài package:

```bash
$ npm i --save @nestjs/authentication
```

Request body được validate bằng bất cứ công cụ nào ứng dụng của bạn đang dùng. Mọi DTO trên trang này đều có hai phiên bản, một class có decorator và một schema Zod, nên hãy chọn kiểu bạn đang dùng và bỏ qua phiên bản còn lại.

Bài hướng dẫn giữ người dùng trong bộ nhớ, đằng sau một class `UsersRepository`. Hãy thay phần thân các method của nó bằng Prisma, Drizzle, TypeORM, hoặc bất cứ thứ gì ứng dụng của bạn dùng; phần code còn lại chỉ thấy các object `User` thuần. State xác thực (session, token, authenticator, các link đang chờ) được chuyển sang PostgreSQL trong phần [Giữ session và token trong database của bạn](/security/authentication#keep-sessions-and-tokens-in-your-database).

Bắt đầu từ phần xác minh email, ứng dụng đọc thiết lập và secret từ biến môi trường. Hãy giữ chúng trong một file `.env` khi phát triển, và khởi động ứng dụng với file đó:

```bash
$ npm run start:dev -- --env-file .env
```

#### Đăng ký authentication module <a id="register-the-authentication-module"></a>

Package không bao giờ đọc bảng người dùng của bạn. Nó hỏi code của bạn để lấy người dùng theo id, và code của bạn quyết định người dùng là gì. Đây là người dùng của cửa hàng. `emailVerified` ghi nhận khách hàng đã chứng minh họ sở hữu địa chỉ email hay chưa; việc xác minh email sẽ đặt giá trị này, và việc đặt hàng, đăng nhập bằng Google và magic link đều phụ thuộc vào nó:

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

Repository giữ kín các hash mật khẩu. Mọi thứ nó trả về đều là `User` không có hash, nên một người dùng có thể được trả về từ route hoặc ghi vào log mà không làm lộ hash:

```typescript
@@filename(src/users/users.repository)
import { randomUUID } from 'node:crypto';
import { Injectable } from '@nestjs/common';
import type { User } from './user.js';

interface UserRow extends User {
  passwordHash: string | null;
}

/**
 * In-memory stand-in for your data layer (Prisma, Drizzle, TypeORM, ...).
 * Only `User` objects leave this class: password hashes stay inside.
 */
@Injectable()
export class UsersRepository {
  private readonly rows = new Map<string, UserRow>();

  async create(
    email: string,
    { passwordHash = null, emailVerified = false }: { passwordHash?: string | null; emailVerified?: boolean } = {},
  ): Promise<User> {
    const row: UserRow = { id: randomUUID(), email: normalize(email), emailVerified, roles: ['customer'], passwordHash };
    this.rows.set(row.id, row);
    return toUser(row);
  }

  async findById(id: string): Promise<User | null> {
    const row = this.rows.get(id);
    return row ? toUser(row) : null;
  }

  async findByEmail(email: string): Promise<User | null> {
    const row = this.findRow(email);
    return row ? toUser(row) : null;
  }

  /** For password sign-in only. */
  async findCredentials(email: string): Promise<{ user: User; passwordHash: string | null } | null> {
    const row = this.findRow(email);
    return row ? { user: toUser(row), passwordHash: row.passwordHash } : null;
  }

  async updatePasswordHash(id: string, passwordHash: string): Promise<void> {
    const row = this.rows.get(id);
    if (row) {
      row.passwordHash = passwordHash;
    }
  }

  async updateEmail(id: string, email: string): Promise<User | null> {
    const row = this.rows.get(id);
    if (!row) {
      return null;
    }
    row.email = normalize(email);
    row.emailVerified = false; // nobody has proven the new address yet
    return toUser(row);
  }

  private findRow(email: string) {
    const normalized = normalize(email);
    return [...this.rows.values()].find((row) => row.email === normalized);
  }
}

// As the package passes addresses to handlers: an accent typed as two code points matches the stored one.
const normalize = (email: string) => email.trim().normalize('NFC').toLowerCase();
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

Tiếp theo là một **credential provider**. Một provider xem xét request gửi đến và trả về người dùng mà request đó chứng minh, hoặc `null` khi request không mang thông tin xác thực nào nó hiểu được. `SessionCookieProvider` đọc session cookie, load session, rồi truyền nó cho method `validate()` của bạn, method này load người dùng:

```typescript
@@filename(src/auth/session-auth.provider)
import { Injectable } from '@nestjs/common';
import { AuthenticationRegistry, SessionCookieProvider, type SessionRecord } from '@nestjs/authentication';
import type { User } from '../users/user.js';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class SessionAuth extends SessionCookieProvider<User> {
  constructor(
    private readonly usersRepository: UsersRepository,
    registry: AuthenticationRegistry,
  ) {
    super();
    // Adds this provider to the chain the guard runs for every request.
    registry.registerProvider(this);
  }

  // Called for every request with a live session cookie.
  // Returning null (the user was deleted) ends the session.
  validate(session: SessionRecord) {
    return this.usersRepository.findById(session.userId);
  }
}
```

Provider là các class `@Injectable()` thông thường, nên chúng inject được bất cứ thứ gì cần, và chúng tự đăng ký: constructor truyền `this` cho `AuthenticationRegistry`, danh sách provider của package, nơi guard tham khảo. Class cha nhận `SessionService` qua injection qua property, đó là lý do constructor chỉ liệt kê `UsersRepository` và registry. Vì `validate()` chạy ở mọi request đã xác thực, một người dùng bị xóa sẽ mất quyền truy cập ngay lập tức, chứ không phải khi session hết hạn. Khi người dùng nằm cùng database với session, store có thể đọc người dùng trong cùng một query và truyền nó cho `validate()` dưới dạng `session.extra`, nên một request chỉ tốn một lần đọc thay vì hai; phần [Giữ session và token trong database của bạn](/security/authentication#keep-sessions-and-tokens-in-your-database) chỉ cách làm.

Hãy cung cấp nó trong một module của riêng bạn. `AuthModule` sẽ chứa mọi thứ bài hướng dẫn này thêm vào dưới `src/auth`:

```typescript
@@filename(src/auth/auth.module)
import { Module } from '@nestjs/common';
import { UsersModule } from '../users/users.module.js';
import { SessionAuth } from './session-auth.provider.js';

@Module({
  imports: [UsersModule],
  providers: [SessionAuth],
})
export class AuthModule {}
```

Giờ hãy đăng ký `AuthenticationModule` trong root module, cạnh `AuthModule`:

```typescript
@@filename(src/app.module)
import { Module } from '@nestjs/common';
import { AuthenticationModule } from '@nestjs/authentication';
import { AuthModule } from './auth/auth.module.js';
import { UsersModule } from './users/users.module.js';

@Module({
  imports: [
    AuthenticationModule.forRoot({
      session: {
        absoluteTtl: '14d', // signed out after 14 days, however active
        idleTtl: '3d', // or after 3 days without a request
      },
    }),
    UsersModule,
    AuthModule,
  ],
})
export class AppModule {}
```

`forRoot()` chỉ nhận giá trị: thời gian sống, secret, client id, các trang mà email của bạn link tới. Không có class nào nằm trong tùy chọn. Các credential provider, các handler mà các phần sau thêm vào, và [database store](/security/authentication#keep-sessions-and-tokens-in-your-database) đều là provider trong module của riêng bạn, và mỗi cái tự đăng ký từ constructor của nó, nên nó nằm cạnh những gì nó inject, còn tùy chọn của module vẫn chỉ là dữ liệu thuần. Thời gian sống tính bằng mili giây, hoặc chuỗi như `'15m'` và `'14d'`, tối đa 100 năm. `@nestjs/jwt` thì tính bằng giây, nên một thời gian sống dạng số dưới một phút sẽ log cảnh báo lúc khởi động: `3600` ở đây là 3,6 giây, không phải một giờ.

Lúc khởi động, khi constructor của mọi provider đã chạy xong, registry sẽ khóa lại và log chuỗi provider mà nó sẽ thử:

```bash
LOG [AuthenticationModule] AuthenticationRegistry: providers SessionAuth
```

Module cũng đăng ký một global guard. Từ giờ trở đi, **mọi route đều yêu cầu người dùng đã đăng nhập** và trả lời `401 Unauthorized` với bất kỳ ai khác. Nếu ứng dụng của bạn đã có những route cần để công khai, như health check hay danh mục sản phẩm, hãy đánh dấu chúng bằng `@Public()`, decorator được giới thiệu ở phần tiếp theo.

> info **Gợi ý** Session được lưu trong bộ nhớ cho đến khi một provider đăng ký store, và khi `NODE_ENV` được đặt thành `production`, module sẽ từ chối khởi động theo cách đó. Một [phần sau](/security/authentication#keep-sessions-and-tokens-in-your-database) chuyển chúng sang database của bạn.

#### Thêm đăng ký và đăng nhập <a id="add-sign-up-and-sign-in"></a>

Đầu tiên hãy validate request body. Đăng ký áp dụng độ dài mật khẩu tối thiểu; đăng nhập thì không, để mật khẩu được đặt theo quy tắc cũ vẫn dùng được:

```typescript
@@filename(src/auth/auth.dto)
import { IsEmail, IsString, MaxLength, MinLength } from 'class-validator';

export class SignUpDto {
  @IsEmail()
  email: string;

  @IsString()
  @MinLength(12)
  @MaxLength(128)
  password: string;
}

export class SignInDto {
  @IsEmail()
  email: string;

  @IsString()
  password: string;
}
```

Cùng các quy tắc đó dưới dạng schema Zod, với type suy ra từ schema thay cho class. Nest 12.1 validate mọi object [Standard Schema](https://standardschema.dev/), từ Zod, Valibot hay ArkType, thông qua `StandardSchemaValidationPipe`:

```typescript
@@filename(src/auth/auth.schemas)
import { z } from 'zod';

export const signUpSchema = z.object({
  email: z.email(),
  password: z.string().min(12).max(128),
});
export type SignUpDto = z.infer<typeof signUpSchema>;

export const signInSchema = z.object({
  email: z.email(),
  password: z.string(),
});
export type SignInDto = z.infer<typeof signInSchema>;
```

`PasswordHasher` hash mật khẩu bằng scrypt (`crypto.scrypt`, chạy trên threadpool của libuv, nên không làm nghẽn event loop), mặc định dùng các tham số mà OWASP khuyến nghị. Một service bọc hai thứ mà controller cần:

```typescript
@@filename(src/auth/credentials.service)
import { ConflictException, Injectable } from '@nestjs/common';
import { PasswordHasher } from '@nestjs/authentication';
import type { User } from '../users/user.js';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class CredentialsService {
  constructor(
    private readonly usersRepository: UsersRepository,
    private readonly passwordHasher: PasswordHasher,
  ) {}

  async register(email: string, password: string): Promise<User> {
    if (await this.usersRepository.findByEmail(email)) {
      throw new ConflictException('Email already registered');
    }
    // The address is unverified: anyone can type any email into a sign-up form.
    return this.usersRepository.create(email, { passwordHash: await this.passwordHasher.hash(password) });
  }

  /** The user, or `null` when the email or the password is wrong. */
  async verify(email: string, password: string): Promise<User | null> {
    const found = await this.usersRepository.findCredentials(email);
    // With no account (or no password), verify() checks a dummy hash, so the
    // response time does not reveal which emails are registered.
    const valid = await this.passwordHasher.verify(password, found?.passwordHash);
    if (!valid || !found?.passwordHash) {
      return null;
    }
    // The cost settings changed since this hash was stored: upgrade it now,
    // while we have the plaintext.
    if (this.passwordHasher.needsRehash(found.passwordHash)) {
      await this.usersRepository.updatePasswordHash(found.user.id, await this.passwordHasher.hash(password));
    }
    return found.user;
  }
}
```

- `verify()` khi không có hash đã lưu sẽ kiểm tra mật khẩu với một hash giả. Email không tồn tại và mật khẩu sai tốn cùng thời gian và cho cùng câu trả lời, nên không cái nào để lộ email nào có tài khoản.
- Mật khẩu được hash bằng scrypt từ `node:crypto`, với các tham số OWASP khuyến nghị (N=2^17, r=8, p=1: khoảng 128 MiB bộ nhớ cho mỗi lần hash), trên thread pool của libuv. Đó là một hàm memory-hard, điều mà bcrypt không phải, và nó không cần dependency native nào. Mỗi hash ghi lại các tham số đã dùng để tạo ra nó (`$scrypt$ln=17,r=8,p=1$...`). Khi bạn tăng chi phí bằng tùy chọn `password`, `needsRehash()` cho biết những hash đã lưu nào cần nâng cấp, và thời điểm duy nhất bạn làm được việc đó là khi người dùng đăng nhập. Cho đến lúc đó, `verify()` bù thêm cho việc kiểm tra một hash cũ, rẻ hơn, cho bằng khối lượng công việc của các tham số mới, để nó vẫn tốn thời gian bằng một email không tồn tại. Giảm chi phí thì không che giấu được theo cách đó: một hash tạo với tham số tốn kém hơn sẽ mất nhiều thời gian kiểm tra hơn cho đến khi được nâng cấp. Chi phí có mức trần là 1 GiB bộ nhớ và gấp 16 lần khối lượng công việc mặc định cho mỗi lần hash, nên với `r` là 8, `logN` dừng ở 20. Tham số vượt quá mức đó sẽ lỗi lúc khởi động, và một hash đã lưu tạo với chúng sẽ không bao giờ xác minh được.
- `register()` để địa chỉ ở trạng thái chưa xác minh. Gõ một email vào form đăng ký không chứng minh được bạn sở hữu nó.

Controller biến một mật khẩu đã xác minh thành một session:

```typescript
@@filename(src/auth/auth.controller)
import { Body, Controller, HttpCode, Post, UnauthorizedException } from '@nestjs/common';
import { Public, SignInService } from '@nestjs/authentication';
import { SignInDto, SignUpDto } from './auth.dto.js';
import { CredentialsService } from './credentials.service.js';

@Public()
@Controller('auth')
export class AuthController {
  constructor(
    private readonly credentialsService: CredentialsService,
    private readonly signInService: SignInService,
  ) {}

  @Post('sign-up')
  async signUp(@Body() body: SignUpDto) {
    const user = await this.credentialsService.register(body.email, body.password);
    await this.signInService.signIn(user.id, { method: 'password' });
    return user;
  }

  @Post('sign-in')
  @HttpCode(200)
  async signIn(@Body() body: SignInDto) {
    const user = await this.credentialsService.verify(body.email, body.password);
    if (!user) {
      throw new UnauthorizedException('Invalid email or password');
    }
    const { session } = await this.signInService.signIn(user.id, { method: 'password' });
    return { mfaRequired: session.mfa === 'pending' };
  }
}
```

`@Public()` trên class bỏ qua xác thực cho cả hai route. `SignInService.signIn()` là nơi duy nhất một yếu tố xác thực thứ nhất trở thành session: bước này gọi nó sau khi kiểm tra mật khẩu, và các bước Google và magic link cũng đi qua nó. Nó tạo session và tự đặt session cookie lên response, trên cả Express lẫn Fastify, nên controller không cần `@Req()` hay `@Res()`:

- Cookie `__Host-sid` chứa một token ngẫu nhiên 256 bit và có các thuộc tính `HttpOnly`, `Secure` và `SameSite=Lax`. Prefix `__Host-` báo cho trình duyệt chỉ chấp nhận cookie này từ chính host này, nên một trang trên subdomain khác không thể cài session cookie của riêng nó. Chỉ hash SHA-256 của token được lưu, nên một session store bị lộ không thể bị dùng lại làm cookie.
- Nó xóa session mà trình duyệt này có trước đó, giúp phòng chống session fixation.
- Nó từ chối, với lỗi 403, một lần đăng nhập được gửi từ trang của một website khác. Nếu không, trang đó có thể đăng nhập trình duyệt của khách hàng vào một tài khoản do kẻ tấn công chọn (login CSRF).
- `method` được ghi lại trong audit trail, như phần [quản lý session](/security/authentication#let-customers-manage-their-sessions) có đề cập.
- `mfaRequired` giữ là `false` cho đến khi bạn [thêm yếu tố xác thực thứ hai](/security/authentication#add-two-factor-authentication).

Với các schema Zod, tham số body khai báo schema thay vì class:

```typescript
@@filename(src/auth/auth.controller)
import { signInSchema, signUpSchema, type SignInDto, type SignUpDto } from './auth.schemas.js';
// ...
@Post('sign-up')
async signUp(@Body({ schema: signUpSchema }) body: SignUpDto) {
  // ...
}

@Post('sign-in')
@HttpCode(200)
async signIn(@Body({ schema: signInSchema }) body: SignInDto) {
  // ...
}
```

Đăng ký controller trong `AuthModule`:

```typescript
@@filename(src/auth/auth.module)
import { Module } from '@nestjs/common';
import { UsersModule } from '../users/users.module.js';
import { AuthController } from './auth.controller.js';
import { CredentialsService } from './credentials.service.js';
import { SessionAuth } from './session-auth.provider.js';

@Module({
  imports: [UsersModule],
  controllers: [AuthController],
  providers: [SessionAuth, CredentialsService],
})
export class AuthModule {}
```

> info **Gợi ý** Các DTO chỉ được áp dụng khi có validation pipe: hãy bind `ValidationPipe` ở cấp global, dưới dạng provider `APP_PIPE` của `AppModule` hoặc bằng `useGlobalPipes()` trong `main.ts`. Với các schema Zod, hãy bind `StandardSchemaValidationPipe` theo cùng cách: một ứng dụng dùng một trong hai. Trang [validation](/application/validation) có các tùy chọn của mỗi loại.

> info **Gợi ý** Chrome, Firefox và curl xem `http://localhost` là một origin an toàn và chấp nhận cookie `Secure` và `__Host-` từ nó, nên bạn không cần HTTPS khi phát triển. Trên một host khác qua HTTP thường, như một địa chỉ mạng LAN, hãy đặt `cookie.secure` thành `false` trong tùy chọn `session` ở đó; khi đó cookie sẽ có tên là `sid`.

Session cookie cũng được bảo vệ khỏi cross-site request forgery. Bên cạnh `SameSite=Lax`, module bỏ qua cookie trên các request `POST`, `PUT`, `PATCH` và `DELETE`, cũng như các WebSocket handshake, đến từ một origin khác, dựa trên các header `Sec-Fetch-Site`, `Origin` và `Host`, nên những request đó là ẩn danh. Các client không gửi cả `Sec-Fetch-Site` lẫn `Origin`, như curl và app mobile của bạn, không bị ảnh hưởng. Nếu web app của bạn chạy trên một origin khác với API, hãy liệt kê nó trong `session.trustedOrigins`.

Trên Nest 12.1 trở lên, hãy gọi thêm `app.enableCsrfProtection()` trong `main.ts`. Nó đưa ra cùng quyết định đó cho mọi route, với lỗi 403, kể cả các route công khai chưa có session nào để bảo vệ. Hãy truyền cho nó cùng `trustedOrigins` như trong tùy chọn `session`.

#### Xác minh địa chỉ email <a id="verify-email-addresses"></a>

Ai cũng có thể gõ bất kỳ địa chỉ nào vào form đăng ký. Cho đến khi khách hàng chứng minh địa chỉ đó là của họ, bằng cách mở một link gửi tới nó, cửa hàng xem nó là chưa xác minh: cửa hàng sẽ không nhận đơn hàng có hóa đơn gửi tới đó, và không cho tài khoản Google hay magic link vào tài khoản đó, như các phần sau sẽ trình bày. Package tạo và kiểm tra các link. Ứng dụng của bạn gửi chúng đi, bằng library mail bạn chọn; cửa hàng dùng `@nestjs/mail`:

```bash
$ npm i --save @nestjs/mail
```

Từ bước này trở đi, ứng dụng đọc thiết lập từ biến môi trường. Hãy thêm URL công khai của ứng dụng vào `.env`. Các link trong email trỏ tới các trang của web app ở đó:

```bash
APP_URL=http://localhost:3000
```

> info **Gợi ý** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để một biến bị thiếu hoặc sai định dạng làm ứng dụng dừng ngay lúc khởi động thay vì ở request đầu tiên, và đọc giá trị từ `ConfigService`.

Đăng ký `MailModule` trong `AppModule`. Giờ cả hai module đều đọc biến môi trường, nên `AuthenticationModule` chuyển sang dùng `forRootAsync()`: factory của nó chạy lúc bootstrap, trong khi tham số của `forRoot()` được evaluate khi file được import, điều này vẫn ổn khi mọi giá trị đều là literal. Với `@nestjs/config`, hãy thêm `inject: [ConfigService]` và đọc giá trị từ service được inject. Ở development, `LogMailTransport` in mỗi email ra log của ứng dụng, để bạn có thể đi theo các link; đặt `SMTP_URL` để gửi email thật. `FileTemplateEngine` render body của email từ các file HTML trong `src/mail/templates`, mỗi email một file:

```typescript
@@filename(src/app.module)
import { FileTemplateEngine, LogMailTransport, MailModule, SmtpTransport } from '@nestjs/mail';
// ...
import { join } from 'node:path';
// ...

@Module({
  imports: [
    MailModule.forRootAsync({
      useFactory: () => ({
        // Your provider in production. In development, each email (links
        // included) is printed to the log.
        transport: process.env.SMTP_URL ? new SmtpTransport({ url: process.env.SMTP_URL }) : new LogMailTransport(),
        // The emails' HTML: the templates in mail/templates, next to this file
        templates: new FileTemplateEngine({ dir: join(import.meta.dirname, 'mail/templates') }),
        from: 'Accounts <accounts@example.com>',
      }),
    }),
    AuthenticationModule.forRootAsync({
      // ...
```

Trình biên dịch TypeScript không copy file HTML sang `dist`: hãy thêm các template vào asset trong `nest-cli.json`, như bài hướng dẫn [Mail](/application/mail#register-the-mail-module) chỉ dẫn; bài đó cũng trình bày cú pháp template.

Email xác minh là một template. Link được đặt giữa cặp ngoặc nhọn đôi, thứ sẽ escape nó:

```html
@@filename(src/mail/templates/verify-email.html)
<p>Confirm the email address of your store account:</p>
<p><a href="{{ '{' }}{{ '{' }} url {{ '}' }}{{ '}' }}">Confirm my address</a></p>
<p>If you didn't create an account, ignore this email.</p>
```

Một mail class render email từ template, với link làm context, và một `EmailVerificationHandler` kết nối package với nó: `send()` gửi đi một link, còn `markVerified()` ghi nhận một địa chỉ đã xác minh vào bảng người dùng của bạn. Giống như credential provider, handler tự đăng ký, dưới tên của tính năng mà nó phục vụ:

```typescript
@@filename(src/auth/email-verification.mailer)
import { Injectable } from '@nestjs/common';
import { AuthenticationRegistry, EmailVerificationHandler, type EmailVerificationLink } from '@nestjs/authentication';
import { Mailer, type Mailable } from '@nestjs/mail';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class VerifyEmailMail implements Mailable<EmailVerificationLink> {
  render({ url }: EmailVerificationLink) {
    return {
      subject: 'Confirm your email address',
      template: 'verify-email',
      context: { url },
    };
  }
}

@Injectable()
export class EmailVerificationMailer extends EmailVerificationHandler {
  constructor(
    private readonly usersRepository: UsersRepository,
    private readonly mailer: Mailer,
    registry: AuthenticationRegistry,
  ) {
    super();
    registry.registerHandler('emailVerification', this);
  }

  async send(link: EmailVerificationLink) {
    await this.mailer.send(VerifyEmailMail, { to: link.email, data: link });
  }

  // Runs when the link is used. It verifies nothing if the address changed since.
  markVerified(userId: string, email: string) {
    return this.usersRepository.markEmailVerified(userId, email);
  }
}
```

`markVerified()` chỉ đánh dấu đúng địa chỉ mà link được gửi tới. Nếu khách hàng đã đổi địa chỉ kể từ đó, link sẽ không xác minh gì cả. Repository chỉ cập nhật dòng dữ liệu khi địa chỉ vẫn khớp, trong SQL đó là một câu update có điều kiện (`UPDATE users SET email_verified = true WHERE id = $1 AND email = $2`):

```typescript
@@filename(src/users/users.repository)
/** Only if `email` is still the user's address: a link sent to an old one verifies nothing. */
async markEmailVerified(id: string, email: string): Promise<boolean> {
  const row = this.rows.get(id);
  if (!row || row.email !== normalize(email)) {
    return false;
  }
  row.emailVerified = true;
  return true;
}
```

Một tính năng có hai nửa: handler của nó, và tùy chọn của nó. Hãy cung cấp handler trong `AuthModule`, và cấu hình trang mà các link mở ra. Có nửa này mà thiếu nửa kia sẽ lỗi lúc khởi động, kèm thông báo nêu tên phần bị thiếu:

```typescript
@@filename(src/auth/auth.module)
providers: [
  SessionAuth,
  CredentialsService,
  EmailVerificationMailer,
],
```

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    session: {
      // ...
    },
    emailVerification: { url: `${process.env.APP_URL}/verify-email` },
  }),
}),
```

Gửi link khi khách hàng đăng ký:

```typescript
@@filename(src/auth/auth.controller)
import { EmailVerificationService, Public, SignInService } from '@nestjs/authentication';
// ...
constructor(
  private readonly credentialsService: CredentialsService,
  private readonly signInService: SignInService,
  private readonly emailVerificationService: EmailVerificationService,
) {}

@Post('sign-up')
async signUp(@Body() body: SignUpDto) {
  const user = await this.credentialsService.register(body.email, body.password);
  await this.signInService.signIn(user.id, { method: 'password' });
  // The link in this email proves the customer owns the address.
  await this.emailVerificationService.send(user);
  return user;
}
```

Sau đó thêm các endpoint. Link mở một trang của web app, trang này POST token từ URL của nó ngược lại cho API: các trình quét email và trình xem trước link đi theo link trong email bằng request GET, và sẽ dùng hết token trước khi khách hàng kịp click.

```typescript
@@filename(src/auth/email-verification.controller)
import { BadRequestException, Body, ConflictException, Controller, HttpCode, Post } from '@nestjs/common';
import { CurrentUser, EmailVerificationService, Public } from '@nestjs/authentication';
import type { User } from '../users/user.js';

@Controller('auth/email')
export class EmailVerificationController {
  constructor(private readonly emailVerificationService: EmailVerificationService) {}

  // Called by the page the link opens, which POSTs the token from its URL.
  @Public()
  @Post('verify')
  @HttpCode(200)
  async verify(@Body('token') token: string) {
    const verified = await this.emailVerificationService.verify(token);
    if (!verified) {
      throw new BadRequestException('Invalid or expired link');
    }
    return { email: verified.email, emailVerified: true };
  }

  // "Send the link again", to the signed-in customer's current address.
  @Post('verification')
  @HttpCode(202)
  async resend(@CurrentUser() user: User) {
    if (user.emailVerified) {
      throw new ConflictException('Email address already verified');
    }
    await this.emailVerificationService.send(user);
  }
}
```

- `EmailVerificationService.send()` lưu hash SHA-256 của một token ngẫu nhiên 256 bit, cùng id của khách hàng và địa chỉ, rồi truyền link cho handler của bạn. Bản thân token chỉ tồn tại trong email.
- Một link chỉ dùng được một lần, trong 24 giờ (`emailVerification.ttl`), và chỉ cho đúng địa chỉ mà nó được gửi tới. `verify()` trả về `null` với token không tồn tại, đã dùng hoặc đã hết hạn, và với địa chỉ đã thay đổi kể từ đó, và route sẽ trả lời 400.
- `resend` không phải `@Public()`: chỉ khách hàng đã đăng nhập mới xin được link mới, và chỉ tới địa chỉ của chính họ, nên route không để lộ gì về các tài khoản khác.

Đăng ký controller:

```typescript
@@filename(src/auth/auth.module)
controllers: [
  AuthController,
  EmailVerificationController,
],
```

Package cũng có thể yêu cầu địa chỉ đã xác minh trên một route: `@Authenticate()` với `verifiedEmail: true` sẽ trả lời 403 cho khách hàng đã đăng nhập nhưng chưa xác minh địa chỉ. Phần [Đọc người dùng hiện tại](/security/authentication#read-the-current-user) dùng nó cho việc đặt hàng.

> info **Gợi ý** `LogMailTransport` log nội dung text của mỗi email ở level `debug`, kể cả link, nên đừng bao giờ dùng nó ở nơi log được gửi đi. Trên production, hãy đặt `SMTP_URL`, hoặc truyền một transport khác, như `ResendTransport`. Bài hướng dẫn [Mail](/application/mail) trình bày các tùy chọn.

#### Đặt lại mật khẩu đã quên <a id="reset-forgotten-passwords"></a>

Một khách hàng quên mật khẩu sẽ xin một link, và chọn mật khẩu mới trên trang mà link mở ra. Email gửi link là một template khác:

```html
@@filename(src/mail/templates/password-reset.html)
<p>Someone asked to reset the password of your store account.</p>
<p><a href="{{ '{' }}{{ '{' }} url {{ '}' }}{{ '}' }}">Choose a new password</a></p>
<p>The link works once, for an hour. If it wasn't you, ignore this email: your password stays as it is.</p>
```

Package sở hữu các token; một `PasswordResetHandler` tìm tài khoản, gửi email, và lưu hash của mật khẩu mới:

```typescript
@@filename(src/auth/password-reset.mailer)
import { Injectable } from '@nestjs/common';
import { AuthenticationRegistry, PasswordResetHandler, type PasswordResetLink } from '@nestjs/authentication';
import { Mailer, type Mailable } from '@nestjs/mail';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class PasswordResetMail implements Mailable<PasswordResetLink> {
  render({ url }: PasswordResetLink) {
    return {
      subject: 'Reset your password',
      template: 'password-reset',
      context: { url },
    };
  }
}

@Injectable()
export class PasswordResetMailer extends PasswordResetHandler {
  constructor(
    private readonly usersRepository: UsersRepository,
    private readonly mailer: Mailer,
    registry: AuthenticationRegistry,
  ) {
    super();
    registry.registerHandler('passwordReset', this);
  }

  // The link goes to the address the account has stored, and works only while
  // the account keeps that address and this hash: any change invalidates it.
  async findUser(email: string) {
    const found = await this.usersRepository.findCredentials(email);
    return found && { id: found.user.id, email: found.user.email, passwordHash: found.passwordHash };
  }

  async send(link: PasswordResetLink) {
    await this.mailer.send(PasswordResetMail, { to: link.email, data: link });
  }

  updatePassword(userId: string, passwordHash: string) {
    return this.usersRepository.updatePasswordHash(userId, passwordHash);
  }
}
```

`findUser()` trả về id của tài khoản, địa chỉ đã lưu và hash mật khẩu đã lưu của nó, hoặc `null` với tài khoản không có mật khẩu. Link được gửi tới địa chỉ đã lưu đó, không bao giờ tới địa chỉ được gõ vào form: nếu không, một phép tra cứu bỏ qua dấu hoặc dấu chấm, như collation mặc định của MySQL làm, sẽ gửi link của một khách hàng cho bất kỳ ai gõ một địa chỉ trông giống. Một link chỉ dùng được khi địa chỉ và hash không thay đổi, nên một lần đổi mật khẩu, qua bất kỳ route nào, sẽ vô hiệu hóa các link đã gửi trước đó. Bỏ trống địa chỉ hoặc hash là lỗi, package sẽ log lỗi đó thay vì gửi link.

Bật tính năng đặt lại mật khẩu cạnh xác minh email, handler trong `AuthModule` và trang trong tùy chọn:

```typescript
@@filename(src/auth/auth.module)
providers: [
  SessionAuth,
  CredentialsService,
  EmailVerificationMailer,
  PasswordResetMailer,
],
```

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    // ...
    emailVerification: { url: `${process.env.APP_URL}/verify-email` },
    passwordReset: { url: `${process.env.APP_URL}/reset-password` },
  }),
}),
```

Một endpoint nhận địa chỉ, endpoint kia nhận token và mật khẩu mới, mật khẩu này tuân theo quy tắc của bước đăng ký:

```typescript
@@filename(src/auth/auth.dto)
// ...

export class EmailDto {
  @IsEmail()
  email: string;
}

/** The token from the reset link, and the new password, under the sign-up rules. */
export class ResetPasswordDto {
  @IsString()
  token: string;

  @IsString()
  @MinLength(12)
  @MaxLength(128)
  password: string;
}
```

```typescript
@@filename(src/auth/auth.schemas)
export const emailSchema = z.object({
  email: z.email(),
});
export type EmailDto = z.infer<typeof emailSchema>;

/** The token from the reset link, and the new password, under the sign-up rules. */
export const resetPasswordSchema = z.object({
  token: z.string(),
  password: z.string().min(12).max(128),
});
export type ResetPasswordDto = z.infer<typeof resetPasswordSchema>;
```

```typescript
@@filename(src/auth/password-reset.controller)
import { BadRequestException, Body, Controller, HttpCode, Post } from '@nestjs/common';
import { PasswordResetService, Public } from '@nestjs/authentication';
import { EmailDto, ResetPasswordDto } from './auth.dto.js';

@Public()
@Controller('auth/password')
export class PasswordResetController {
  constructor(private readonly passwordResetService: PasswordResetService) {}

  // The same answer, as fast, whether or not the address has an account:
  // request() returns before it looks the address up.
  @Post('forgot')
  @HttpCode(202)
  forgot(@Body() body: EmailDto) {
    this.passwordResetService.request(body.email);
  }

  // Called by the page the link opens, with the token from its URL and the new password.
  @Post('reset')
  @HttpCode(200)
  async reset(@Body() body: ResetPasswordDto) {
    const result = await this.passwordResetService.reset(body.token, body.password, { signIn: true });
    if (!result) {
      throw new BadRequestException('Invalid or expired link');
    }
    return { mfaRequired: result.signedIn?.session.mfa === 'pending' };
  }
}
```

- `request()` trả về trước khi tra cứu địa chỉ. Việc tìm tài khoản, lưu token và gửi email diễn ra sau khi response được gửi đi, nên một request cho địa chỉ chưa ai đăng ký nhận được cùng mã 202, trong cùng khoảng thời gian, như request của một khách hàng thật: route không thể cho ai biết ai có tài khoản. Đó là lý do `forgot` không `await` gì cả. Một lỗi xảy ra sau khi response đã gửi, như mail server bị sập, sẽ được log.
- Một link chỉ dùng được một lần, trong một giờ (`passwordReset.ttl`), và chỉ khi tài khoản vẫn còn địa chỉ và mật khẩu như lúc link được gửi.
- `reset()` lưu hash của mật khẩu mới, vô hiệu hóa các link đặt lại khác của khách hàng, và kết thúc mọi session của tài khoản, cùng mọi refresh token khi ứng dụng [cấp chúng](/security/authentication#issue-tokens-to-the-mobile-app), nên bất kỳ ai biết mật khẩu cũ đều bị đăng xuất khỏi mọi nơi. [API key](/security/authentication#issue-api-keys-to-partners) nằm trong bảng của riêng bạn và vẫn còn hiệu lực: để cắt cả chúng, hãy thu hồi chúng khi có event `password-reset`. Một mật khẩu mà `PasswordHasher` từ chối, rỗng hoặc vượt quá 4 KiB, sẽ nhận `null` mà không làm tốn link, nên khách hàng có thể thử lại. Với `signIn: true`, sau đó nó đăng nhập khách hàng trên trình duyệt này thông qua `SignInService`, nên một khách hàng có [xác thực hai lớp](/security/authentication#add-two-factor-authentication) vẫn phải nhập mã.
- Link cũng chứng minh luôn địa chỉ, nên `reset()` đánh dấu nó là đã xác minh, thông qua `markVerified()` của bạn. Điều đó cũng cứu được một tài khoản mà người khác đã đăng ký bằng địa chỉ của khách hàng: việc đặt lại sẽ thay mật khẩu của người lạ và đăng xuất họ.

Với các schema Zod:

```typescript
@@filename(src/auth/password-reset.controller)
import { emailSchema, resetPasswordSchema, type EmailDto, type ResetPasswordDto } from './auth.schemas.js';
// ...
@Post('forgot')
@HttpCode(202)
forgot(@Body({ schema: emailSchema }) body: EmailDto) {
  this.passwordResetService.request(body.email);
}

@Post('reset')
@HttpCode(200)
async reset(@Body({ schema: resetPasswordSchema }) body: ResetPasswordDto) {
  // ...
}
```

Đăng ký controller:

```typescript
@@filename(src/auth/auth.module)
controllers: [
  AuthController,
  EmailVerificationController,
  PasswordResetController,
],
```
#### Đọc người dùng hiện tại <a id="read-the-current-user"></a>

`@CurrentUser()` inject người dùng mà `validate()` đã load:

```typescript
@@filename(src/users/me.controller)
import { Controller, Get } from '@nestjs/common';
import { CurrentUser } from '@nestjs/authentication';
import type { User } from './user.js';

@Controller('me')
export class MeController {
  @Get()
  me(@CurrentUser() user: User) {
    return user;
  }
}
```

`@CurrentUser('id')` inject một thuộc tính duy nhất. `@CurrentSession()` inject thứ mà provider xem là session: ở đây là bản ghi session đã lưu.

> info **Gợi ý** Tùy chọn: hãy cho package biết type người dùng của bạn một lần, và các type của nó sẽ đi theo. Mở rộng interface `AuthenticationTypes` của `@nestjs/authentication` trong một khối `declare module`, với `user: User` (bài hướng dẫn đặt nó trong `src/auth/auth-types.ts`). Từ đó trở đi `@CurrentUser('key')` chỉ nhận các key của `User` và có type trả về đúng thuộc tính đó, `AuthenticationContext.user` và `.session` cũng có type tương ứng. Một key `sessionExtra` gán type cho `SessionRecord.extra`, thứ mà session store đọc kèm theo mỗi session (được export dưới tên `SessionExtra`, là `unknown` nếu không có key này). Nó không gán type cho chính tham số: một parameter decorator không quyết định được annotation, nên `user: User` vẫn phải đặt trên tham số. Và đây là một type người dùng duy nhất cho toàn ứng dụng, nên một ứng dụng có hai loại chủ thể thì vẫn giữ các annotation. Cùng interface đó nhận `refreshTokens: false` cho một ứng dụng [tắt refresh token](/security/authentication#issue-tokens-to-the-mobile-app).

```typescript
@@filename(src/users/users.module)
@Module({
  controllers: [MeController],
  providers: [UsersRepository],
  exports: [UsersRepository],
})
export class UsersModule {}
```

Controller không phải là code duy nhất cần người dùng. Đơn hàng thuộc về khách hàng đã đặt chúng, và `OrdersService` đọc khách hàng đó từ `AuthenticationContext`, nên controller không cần truyền người dùng xuống:

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

```typescript
@@filename(src/orders/orders.service)
import { randomUUID } from 'node:crypto';
import { BadRequestException, Injectable } from '@nestjs/common';
import { AuthenticationContext } from '@nestjs/authentication';
import type { Order, OrderItem } from './order.js';

// Stand-in for the products table: product id → price in cents.
const PRICES = new Map([
  ['salmon-kibble-2kg', 2499],
  ['clumping-litter-10l', 1599],
]);

@Injectable()
export class OrdersService {
  private readonly orders: Order[] = [];

  constructor(private readonly authenticationContext: AuthenticationContext) {}

  findMine(): Order[] {
    const { id } = this.authenticationContext.requireUser();
    return this.orders.filter((order) => order.userId === id);
  }

  place(items: OrderItem[]): Order {
    const { id: userId } = this.authenticationContext.requireUser();
    const total = items.reduce((sum, item) => sum + this.price(item.productId) * item.quantity, 0);
    const order: Order = { id: randomUUID(), userId, items, total, status: 'pending' };
    this.orders.push(order);
    return order;
  }

  private price(productId: string): number {
    const price = PRICES.get(productId);
    if (price === undefined) {
      throw new BadRequestException(`Unknown product ${productId}`);
    }
    return price;
  }
}
```

```typescript
@@filename(src/orders/orders.controller)
import { Body, Controller, Get, Post } from '@nestjs/common';
import { Authenticate } from '@nestjs/authentication';
import type { OrderItem } from './order.js';
import { OrdersService } from './orders.service.js';

@Controller('orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Get()
  findMine() {
    return this.ordersService.findMine();
  }

  // Receipts and shipping updates go to the customer's email address,
  // so it must be one they proved.
  @Authenticate({ verifiedEmail: true })
  @Post()
  place(@Body('items') items: OrderItem[]) {
    return this.ordersService.place(items);
  }
}
```

`@Authenticate()` với `verifiedEmail: true` chỉ cho khách hàng đã xác minh địa chỉ đặt hàng. Bất kỳ ai khác đã đăng nhập sẽ nhận lỗi 403 có `error` là `email_unverified`, báo cho web app biết cần yêu cầu khách hàng mở [link xác minh](/security/authentication#verify-email-addresses), hoặc gửi lại link. Đây là 403 chứ không phải 401: đăng nhập lại cũng không giúp gì. `GET /orders` không có yêu cầu này. Mặc định guard đọc `emailVerified` từ người dùng mà `validate()` đã load; `EmailVerificationHandler` của bạn có thể ghi đè `isVerified(user)` nếu type người dùng của bạn lưu thông tin này theo cách khác.

```typescript
@@filename(src/orders/orders.module)
import { Module } from '@nestjs/common';
import { OrdersController } from './orders.controller.js';
import { OrdersService } from './orders.service.js';

@Module({
  controllers: [OrdersController],
  providers: [OrdersService],
})
export class OrdersModule {}
```

Thêm `OrdersModule` vào `imports` của `AppModule`:

```typescript
@@filename(src/app.module)
UsersModule,
AuthModule,
OrdersModule,
```

`AuthenticationContext` là một singleton. Nó đọc người dùng của request hiện tại từ một `AsyncLocalStorage` mà module mở ra bao quanh mỗi handler, nên nó cho kết quả đúng ở mọi thứ mà handler gọi hoặc await, bất kể có bao nhiêu request chạy cùng lúc. `requireUser()` trả về người dùng, hoặc throw một `AuthenticationError`, thứ mà module trả lời bằng lỗi 401 trên mọi transport. Bên ngoài request, trong một queue consumer hay cron job, `AuthenticationContext` là rỗng, và method `run()` của nó chạy một hàm với tư cách một người dùng cụ thể. Nó cũng rỗng trong middleware, guard và exception filter, vì chúng chạy bên ngoài handler.

#### Cấp token cho app mobile <a id="issue-tokens-to-the-mobile-app"></a>

App mobile của cửa hàng xác thực bằng bearer token thay vì cookie. Nó gửi một JWT access token ngắn hạn trong header `Authorization`, và gia hạn nó bằng một refresh token dài hạn.

Thêm một signing secret vào `.env`. Nó phải dài ít nhất 32 byte. Không có nó, ứng dụng sẽ từ chối khởi động, kèm thông báo nêu tên tùy chọn: `accessToken.key` is required.

```bash
# Generate with: openssl rand -base64 32
JWT_SECRET=
```

Ứng dụng vừa cấp vừa xác minh access token, nên hãy mô tả chúng một lần, bằng tùy chọn `accessToken`. Key dùng để ký chúng, còn issuer, audience và thời gian sống được đưa vào mọi token và được kiểm tra ở mọi request:

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    session: {
      // ...
    },
    accessToken: {
      key: process.env.JWT_SECRET!,
      issuer: 'https://api.example.com',
      audience: 'mobile-app',
      ttl: '15m',
    },
  }),
}),
```

Với một secret làm key, token được ký bằng HS256. Credential provider thứ hai xác minh chúng. `JwtBearerProvider` đọc header `Authorization`, kiểm tra chữ ký với key `accessToken`, cùng `exp`, `iss` và `aud`, rồi truyền các claim đã xác minh cho `validate()` của bạn:

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
    // Second in the chain, after SessionAuth (order 0).
    registry.registerProvider(this, { order: 1 });
  }

  // Called after the signature and claims checked out.
  // Returning null (the user was deleted) rejects the token.
  validate({ sub }: JwtClaims) {
    return sub ? this.usersRepository.findById(sub) : null;
  }
}
```

> info **Gợi ý** HS256 với một secret dùng chung phù hợp với API vừa cấp vừa xác minh token của chính nó. Nếu các service khác cũng xác minh chúng, hãy dùng một private key ES256 làm key `accessToken`: khi đó `JwtAuth` xác minh bằng nửa public của nó, và các service kia cũng vậy. Để chấp nhận token từ một issuer khác, hãy truyền cho `super()` URL `jwks` của nó, URL này phải là https (http thường chỉ được phép trên localhost), hoặc `key` public của nó, cùng `issuer` và `audience`: cả hai đều bắt buộc, vì một identity provider ký token của mọi client bằng cùng các key. Với token không có audience, hãy truyền `audience: false` và kiểm tra claim định danh client của bạn trong `validate()`. Thêm `clockTolerance: '30s'` để bù đồng hồ của issuer khác. Key là text PEM hoặc một `KeyObject`; để import một JWK, dùng `createPublicKey()` từ `node:crypto`, truyền JWK làm `key` và `'jwk'` làm `format`. Một `key` hoặc `jwks` rỗng, như một biến môi trường chưa đặt, sẽ lỗi lúc khởi động thay vì quay về dùng tùy chọn `accessToken`. Một service chỉ xác minh token có thể bỏ hẳn `accessToken` và truyền cho `super()` thứ nó dùng để xác minh: `key` dùng chung, hoặc `jwks` cùng `issuer` và `audience`.

Cung cấp nó trong `AuthModule`:

```typescript
@@filename(src/auth/auth.module)
providers: [
  SessionAuth,
  JwtAuth,
  CredentialsService,
],
```

Với mỗi request, guard hỏi các provider theo `order` tăng dần, và provider đầu tiên trả về người dùng sẽ thắng. `SessionAuth` đăng ký với order mặc định là `0`, còn `JwtAuth` yêu cầu `1`, nên một request có session cookie sẽ được `SessionAuth` đăng nhập, còn một request có bearer token, vốn không có cookie, nhận `null` từ `SessionAuth` và được `JwtAuth` xử lý. Thứ tự được chỉ định lúc đăng ký thay vì phụ thuộc vào thứ tự Nest tạo các provider: thứ tự đó đi theo module graph, và thay đổi khi một provider chuyển sang module khác hoặc có thêm một câu import. Hai provider yêu cầu cùng một order sẽ lỗi lúc khởi động, kèm tên cả hai. Một request không có cái nào sẽ nhận lỗi 401 với `errorCode` là `missing_credentials`; header `WWW-Authenticate` của nó liệt kê những gì các provider chấp nhận: `Bearer realm="store"`. Một token không qua được bước xác minh sẽ nhận lỗi 401 nêu rõ lý do, như RFC 6750 mô tả, ví dụ `error="invalid_token", error_description="token expired"`. Điều đó báo cho app mobile biết cần refresh.

Giờ là các endpoint cấp token:

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

  // An unknown, expired or reused refresh token gets a 401.
  @Post('refresh')
  @HttpCode(200)
  refresh(@Body('refreshToken') refreshToken: string) {
    return this.tokenService.refresh(refreshToken);
  }
}
```

`TokenService.issue()` ký một access token với tùy chọn `accessToken`, khởi tạo một refresh token, và trả về cả hai, kèm `expiresIn`, thời gian sống của access token tính bằng giây. Refresh token là opaque (không đọc được nội dung), và được lưu dưới dạng hash. Mỗi token chỉ dùng được một lần: `refresh()` dùng hết nó và trả về token kế tiếp, cùng một access token mới. Các token kế tiếp của một lần đăng nhập tạo thành một family. Nếu một token đã dùng quay lại, nghĩa là có hai bên cùng giữ nó, một kẻ trộm và app, nên service sẽ thu hồi cả family và cả hai đều phải đăng nhập lại. Một refresh token không tồn tại, đã hết hạn hoặc bị dùng lại sẽ throw `RefreshTokenError`, một `AuthenticationError`, thứ mà module trả lời bằng lỗi 401, nên `refresh` không cần tự xử lý lỗi.

Claim `amr` ghi lại cách người dùng đã đăng nhập, và [xác thực hai lớp](/security/authentication#add-two-factor-authentication) dựa vào nó. `issue()` lưu các `claims` cùng family refresh token, và `refresh()` đưa chúng vào mọi access token mà nó tạo ra, nên các token đã refresh mô tả cùng một lần đăng nhập. Đừng đưa những thông tin có thể thay đổi, như role, vào `claims`: chúng sẽ nằm trong token suốt thời gian family còn sống. Thay vào đó, `validate()` load người dùng hiện tại ở mọi request.

Một service ký access token ngắn hạn và để client đăng nhập lại có thể tắt refresh token. Khi `refreshToken` đặt thành `false`, `issue()` chỉ trả về `accessToken` và `expiresIn`, và không lưu gì cả, nên ứng dụng không cần `RefreshTokenStore`. Response của token endpoint không có refresh token: client đăng nhập lại khi access token hết hạn. `refresh()` và `revoke()` sẽ throw, báo rằng refresh token đã bị tắt, còn `revokeAll()` không làm gì cả. Yếu tố thứ hai và claim `amr` vẫn hoạt động như trước. Hãy khai báo cả `refreshTokens: false` trên `AuthenticationTypes`, để `issue()` có type trả về là `AccessTokenResult` thay vì `TokenPair`:

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    accessToken: {
      key: process.env.JWT_SECRET!,
      // ...
    },
    refreshToken: false,
  }),
}),
```

```typescript
@@filename(src/auth/auth-types)
declare module '@nestjs/authentication' {
  interface AuthenticationTypes {
    // ...
    refreshTokens: false;
  }
}
```

Tùy chọn mới là thứ quyết định hành vi lúc chạy; phần khai báo chỉ để báo cho trình biên dịch. Một ứng dụng đặt tùy chọn mà không khai báo sẽ không nhận refresh token lúc runtime nhưng type vẫn là chuỗi, và `refresh()` sẽ throw khi gặp nó. Đặt `refreshToken` thành `false` mà không có `accessToken` sẽ không thay đổi gì, và log một cảnh báo lúc khởi động.

Đăng ký controller:

```typescript
@@filename(src/auth/auth.module)
controllers: [
  AuthController,
  EmailVerificationController,
  PasswordResetController,
  TokensController,
],
```

#### Thêm xác thực hai lớp <a id="add-two-factor-authentication"></a>

Khách hàng có thể bảo vệ tài khoản bằng một app authenticator (mật khẩu dùng một lần theo thời gian, hay TOTP). Cấu hình `mfa` trong `AppModule`:

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    // ...
    mfa: {
      issuer: 'example.com',
      encryption: { keys: [process.env.TOTP_ENCRYPTION_KEY!] },
    },
  }),
}),
```

Server phải đọc lại được TOTP secret để kiểm tra mã, nên khác với mật khẩu, nó không thể bị hash. `MfaService` mã hóa mỗi secret bằng AES-256-GCM trước khi đưa vào lưu trữ, gắn với người dùng của nó, và chỉ giải mã khi cần xác minh mã. Ai có bản sao database nhưng không có key sẽ không tạo được mã. Key là bắt buộc: cấu hình `mfa` mà không có `encryption` sẽ throw lúc khởi động. (`encryption: false` cố ý lưu dạng plaintext, dành cho test.) Một secret ngắn hơn 128 bit sẽ không bao giờ xác minh được: `enroll()` tạo secret 160 bit, nhưng secret import từ hệ thống khác có thể ngắn hơn, và người dùng của chúng phải đăng ký lại.

Thêm key vào `.env`. Một key dạng chuỗi phải có ít nhất 32 ký tự dữ liệu ngẫu nhiên:

```bash
# Generate with: openssl rand -base64 32
TOTP_ENCRYPTION_KEY=
```

> info **Gợi ý** Để xoay vòng key, hãy đặt key mới lên đầu trong `keys` và giữ key cũ phía sau. Key đầu tiên dùng để mã hóa, mọi key được liệt kê đều dùng để giải mã, và secret sẽ được mã hóa lại bằng key mới khi chúng được dùng. Hãy bỏ key cũ khi không còn gì dùng nó. Key không cần tên: mỗi secret đã mã hóa ghi lại một id suy ra từ key của nó.

Xác thực hai lớp bị tắt trừ khi `mfa` được cấu hình. Không có nó, `MfaService.isEnrolled()` trả lời `false` mà không đọc store, nên đăng nhập không bao giờ hỏi mã, và mọi method khác của `MfaService` đều throw `MFA is not configured` trước khi đụng tới lưu trữ. Bỏ `mfa` khỏi tùy chọn sẽ tắt xác thực hai lớp cho mọi khách hàng, kể cả những người đã đăng ký authenticator.

Các endpoint MFA đăng ký authenticator, xác nhận nó, và hoàn tất một lần đăng nhập:

```typescript
@@filename(src/auth/mfa.controller)
import { Body, Controller, HttpCode, Post, UnauthorizedException } from '@nestjs/common';
import { Authenticate, CurrentUser, MfaService, Public, SignInService } from '@nestjs/authentication';
import type { User } from '../users/user.js';

@Controller('auth/mfa')
export class MfaController {
  constructor(
    private readonly mfaService: MfaService,
    private readonly signInService: SignInService,
  ) {}

  // Returns the otpauth:// URI for the web app to show as a QR code,
  // and the secret for people who type it in instead.
  @Post('enroll')
  enroll(@CurrentUser() user: User) {
    return this.mfaService.enroll(user.id, user.email);
  }

  // A new phone. The current authenticator keeps working until /confirm
  // receives a code from the new one.
  @Authenticate({ mfa: true })
  @Post('replace')
  replace(@CurrentUser() user: User) {
    return this.mfaService.enroll(user.id, user.email, { replace: true });
  }

  // The first code proves the authenticator works, and that this browser has
  // it: the session passes the second factor from here on, under a new cookie.
  // Recovery codes are shown once.
  @Post('confirm')
  @HttpCode(200)
  async confirm(@CurrentUser('id') userId: string, @Body('code') code: string) {
    if (!(await this.signInService.confirmMfa(userId, code))) {
      throw new UnauthorizedException('Invalid code');
    }
    return { recoveryCodes: await this.mfaService.generateRecoveryCodes(userId) };
  }

  // Second step of signing in. A pending session counts as signed in
  // nowhere, so the route is public: completeMfa() reads the session cookie.
  @Public()
  @Post('verify')
  @HttpCode(200)
  async verify(@Body('code') code: string | undefined, @Body('recoveryCode') recoveryCode: string | undefined) {
    const issued = await this.signInService.completeMfa({ code, recoveryCode });
    if (!issued) {
      throw new UnauthorizedException('Invalid code');
    }
    return { mfa: issued.session.mfa };
  }
}
```

- `enroll()` lưu một secret mới, chưa xác nhận, và trả về nó cùng một URI `otpauth://` mà web app hiển thị dưới dạng mã QR. Khi một authenticator đã được xác nhận, `enroll()` từ chối ghi đè nó và throw `MfaAlreadyEnrolledError`, thứ mà module trả lời bằng lỗi 409, `Authenticator already enrolled`. Ghi đè nó sẽ tắt xác thực hai lớp cho đến khi authenticator mới được xác nhận.
- `replace` xử lý trường hợp đổi điện thoại mới. `enroll()` với `replace: true` chuẩn bị sẵn một secret thứ hai, và authenticator hiện tại vẫn hoạt động cho đến khi `confirm()` nhận được mã từ authenticator mới. `@Authenticate()` với `mfa: true` khiến route yêu cầu yếu tố thứ hai đã xác minh, nên chỉ một mật khẩu bị đánh cắp không thể tráo authenticator của người khác vào.
- `SignInService.confirmMfa()` kích hoạt authenticator khi nó tạo ra một mã hợp lệ, nên một secret bị gõ sai không thể khóa ai bên ngoài. Mã đó cũng chứng minh trình duyệt này có authenticator, nên session trở thành đã xác minh, dưới một cookie mới: khách hàng có thể dùng ngay các route yêu cầu yếu tố thứ hai, mà không cần đăng nhập lại. Một lần xác nhận gửi bằng bearer token, vốn không có session, chỉ kích hoạt authenticator. Mười mã khôi phục mà route trả về chỉ được hiển thị đúng một lần này, và được lưu dưới một hash chậm có salt là id của khách hàng, nên một bản sao database không làm lộ chúng.
- Khi một authenticator đã được xác nhận, `SignInService.signIn()` tạo session ở trạng thái **pending** cho người dùng đó. Một session pending không đăng nhập ở đâu cả: các route cần người dùng sẽ trả lời 401 với `"errorCode": "mfa_required"`, báo cho web app biết cần hỏi mã. Đó là lý do `verify` là `@Public()`. `completeMfa()` đọc session từ cookie của trình duyệt này, kiểm tra một mã hoặc mã khôi phục, rồi xoay session sang một id mới với `mfa: 'verified'`, đặt cookie mới. Một session pending hết hạn sau 10 phút (`mfa.pendingTtl`), không phải sau 14 ngày của `session.absoluteTtl`: một cookie pending chỉ là một nửa thông tin xác thực. Xác minh mã xong thì session có đầy đủ thời gian sống.
- `completeMfa()` chỉ làm việc với session cookie. Một request có bearer token mà không có cookie sẽ nhận lỗi 401.
- Mã được chấp nhận trong khoảng 30 giây trước và sau thời điểm hiện tại, và mỗi mã chỉ dùng được một lần. Sau 5 lần nhập sai mã trong 15 phút, tài khoản sẽ từ chối mọi mã, kể cả mã đúng, cho đến khi hết khoảng thời gian đó. Mỗi lần thử được đếm trước khi kiểm tra, nên gửi các lần đoán song song không lách được giới hạn.

Một yếu tố thứ hai đã xác minh cũng có thể được yêu cầu cho từng route riêng lẻ, gọi là step-up authentication. Cửa hàng yêu cầu nó khi đổi địa chỉ email, vì đó là cách một tài khoản được khôi phục. Địa chỉ mới được gửi trong `EmailDto` của phần [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords). Thêm route, với `@Authenticate()`:

```typescript
@@filename(src/users/me.controller)
import { Body, ConflictException, Controller, Get, Patch } from '@nestjs/common';
import { Authenticate, CurrentUser, EmailVerificationService } from '@nestjs/authentication';
import { EmailDto } from '../auth/auth.dto.js';
import type { User } from './user.js';
import { UsersRepository } from './users.repository.js';

@Controller('me')
export class MeController {
  constructor(
    private readonly usersRepository: UsersRepository,
    private readonly emailVerificationService: EmailVerificationService,
  ) {}

  @Get()
  me(@CurrentUser() user: User) {
    return user;
  }

  // The email address is how an account is recovered: changing it needs a
  // session (or token) that passed the second factor.
  @Authenticate({ mfa: true })
  @Patch('email')
  async changeEmail(@CurrentUser('id') userId: string, @Body() body: EmailDto) {
    if (await this.usersRepository.findByEmail(body.email)) {
      throw new ConflictException('Email already registered');
    }
    const user = await this.usersRepository.updateEmail(userId, body.email);
    if (user) {
      // The new address is unverified until the customer uses this link.
      await this.emailVerificationService.send(user);
    }
    return user;
  }
}
```

Với schema Zod:

```typescript
@@filename(src/users/me.controller)
import { emailSchema, type EmailDto } from '../auth/auth.schemas.js';
// ...
@Authenticate({ mfa: true })
@Patch('email')
async changeEmail(@CurrentUser('id') userId: string, @Body({ schema: emailSchema }) body: EmailDto) {
  // ...
}
```

Mọi route vốn đã yêu cầu người dùng đăng nhập; `@Authenticate()` điều chỉnh cách yêu cầu. Với `mfa: true`, một cookie session chỉ qua được khi đã được xác minh. Một khách hàng chưa đăng ký authenticator không thể qua được, nên web app sẽ yêu cầu họ đăng ký trước.

Địa chỉ mới chưa được xác minh, nên route gửi một link xác minh tới nó, và khách hàng không thể đặt hàng cho đến khi dùng link. Các link đã gửi tới địa chỉ cũ ngừng hoạt động: chúng chỉ xác minh đúng địa chỉ mà chúng được gửi tới.

App mobile không được trở thành cách lách yếu tố thứ hai, và nó không thể: giống như `signIn()`, `TokenService.issue()` không cấp token cho khách hàng đã xác nhận authenticator nếu không có mã. Nó trả lời 401 với `"errorCode": "mfa_required"`, báo cho app biết cần hỏi mã. Khi đó app gửi lại mật khẩu, kèm mã. Thêm mã vào body:

```typescript
@@filename(src/auth/auth.dto)
import { IsEmail, IsOptional, IsString, MaxLength, MinLength } from 'class-validator';

// ...

/** The mobile app's sign-in: a password, and a code once the customer has an authenticator. */
export class TokenRequestDto extends SignInDto {
  @IsOptional()
  @IsString()
  code?: string;

  @IsOptional()
  @IsString()
  recoveryCode?: string;
}
```

```typescript
@@filename(src/auth/auth.schemas)
/** The mobile app's sign-in: a password, and a code once the customer has an authenticator. */
export const tokenRequestSchema = signInSchema.extend({
  code: z.string().optional(),
  recoveryCode: z.string().optional(),
});
export type TokenRequestDto = z.infer<typeof tokenRequestSchema>;
```

Và truyền nó tiếp làm `secondFactor`:

```typescript
@@filename(src/auth/tokens.controller)
@Post()
@HttpCode(200)
async issue(@Body() body: TokenRequestDto) {
  const user = await this.credentialsService.verify(body.email, body.password);
  if (!user) {
    throw new UnauthorizedException('Invalid email or password');
  }
  return this.tokenService.issue(user.id, {
    method: 'password',
    // `amr` goes into this access token and into every refreshed one.
    claims: { amr: ['pwd'] },
    // Checked only for customers with an authenticator.
    secondFactor: { code: body.code, recoveryCode: body.recoveryCode },
  });
}
```

```typescript
@@filename(src/auth/tokens.controller)
import { tokenRequestSchema, type TokenRequestDto } from './auth.schemas.js';
// ...
@Post()
@HttpCode(200)
async issue(@Body({ schema: tokenRequestSchema }) body: TokenRequestDto) {
  // ...
}
```

Một request không có mã sẽ không bị tính là một lần thử thất bại, nên app có thể tìm hiểu xem nó có cần mã hay không. Một mã đã xác minh sẽ thêm `mfa` vào claim `amr`. `JwtBearerProvider` xem một token có `amr` chứa `mfa`, `otp` hoặc `hwk` là đã xác minh, nên nó qua được các route `mfa: true`. Các token đã refresh mang cùng `amr` như lần đăng nhập đã khởi tạo family của chúng, nên một app mobile đã đăng nhập bằng mã sẽ giữ trạng thái đã xác minh cho đến khi refresh token của nó hết hạn hoặc bị thu hồi. `issue()` không bao giờ nhận ba giá trị đó từ `claims` của chính bạn: nó bỏ chúng đi, kèm một cảnh báo trong log, và chỉ thêm `mfa` khi đã xác minh được mã, nên một ứng dụng không thể vô tình tạo ra một token đã xác minh.

Đăng ký controller:

```typescript
@@filename(src/auth/auth.module)
controllers: [
  // ...
  TokensController,
  MfaController,
],
```

##### Tắt xác thực hai lớp <a id="turn-off-two-factor-authentication"></a>

`MfaService.disable()` xóa authenticator và các mã khôi phục của khách hàng, rồi phát ra `mfa-disabled`. Thêm một route vào `MfaController`, với `SessionService` và `TokenService` được inject vào constructor:

```typescript
@@filename(src/auth/mfa.controller)
// Takes a verified session and a fresh code: a session left signed in on a
// shared computer isn't enough.
@Authenticate({ mfa: true })
@Post('disable')
@HttpCode(204)
async disable(
  @CurrentUser('id') userId: string,
  @CurrentSession() current: SessionRecord,
  @Body('code') code: string,
) {
  if (!(await this.mfaService.verifyTotp(userId, code))) {
    throw new UnauthorizedException('Invalid code');
  }
  await this.mfaService.disable(userId);
  // The other sessions and refresh tokens passed the second factor, and still would.
  await this.sessionService.revokeAll(userId, { except: current.id });
  await this.tokenService.revokeAll(userId);
}
```

- `@Authenticate()` với `mfa: true` là mức tối thiểu: không có nó, chỉ một mật khẩu bị đánh cắp đã có thể tắt yếu tố thứ hai. Một API key không bao giờ qua được nó. Tuy vậy, nó không chứng minh khách hàng đang ngồi trước bàn phím ngay lúc này: một session giữ trạng thái đã xác minh suốt thời gian sống của nó. Vì vậy route còn yêu cầu thêm một mã. `verifyTotp()` resolve ra `false` với mã sai, được tính vào cùng cơ chế khóa như khi đăng nhập, và mỗi mã chỉ dùng được một lần.
- `disable()` xóa mọi mã khôi phục cùng với authenticator, và bỏ một bản thay thế đã chuẩn bị bằng `replace` mà chưa bao giờ được xác nhận. Đăng ký lại sẽ bắt đầu từ đầu, với một lô mã khôi phục mới.
- `disable()` không đụng tới session và token. Các session đã xác minh khác của khách hàng vẫn sẽ qua được các route `mfa: true`, và các family refresh token của họ cũng vậy, vì `amr` của chúng giữ `mfa` qua mỗi lần refresh. Route kết thúc chúng, chỉ giữ lại session của trình duyệt này. Các access token đã cấp vẫn còn hiệu lực cho đến khi hết hạn. Nếu gửi bằng bearer token, request không có session id nào để giữ lại: mọi session đều kết thúc, và `TokenService.revokeAll()` cũng đăng xuất client đó.
- Một session vẫn đang chờ yếu tố thứ hai không thể hoàn tất, vì không còn authenticator nào để kiểm tra mã. `revokeAll()` kết thúc nó cùng với các session khác.
- Một khách hàng chưa bao giờ xác nhận việc đăng ký thì không có session đã xác minh nào, nên route này từ chối họ. Để hủy một lần đăng ký như vậy, hãy gọi `disable()` từ một route không có yêu cầu đó khi `isEnrolled()` là `false`, hoặc gọi lại `enroll()`.
#### Thêm "Đăng nhập bằng Google" <a id="add-sign-in-with-google"></a>

Trong Google Cloud console, tạo một OAuth client ID loại **Web application**, và thêm redirect URI được phép sau (cùng URI production, khi bạn deploy):

```bash
http://localhost:3000/auth/oidc/google/callback
```

Thêm thông tin xác thực của client vào `.env`, cạnh `APP_URL`:

```bash
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Lần đầu tiên ai đó đăng nhập bằng Google, ứng dụng của bạn phải quyết định tài khoản Google đó thuộc về tài khoản local nào. Hãy lưu liên kết dưới dạng một cặp (provider, subject), trong đó subject là id ổn định mà Google gán cho tài khoản. Email có thể thay đổi; subject thì không. Thêm một bảng identity vào repository:

```typescript
@@filename(src/users/users.repository)
@Injectable()
export class UsersRepository {
  private readonly rows = new Map<string, UserRow>();
  /** `provider:subject` → user id, e.g. `google:1098...` */
  private readonly identities = new Map<string, string>();

  // ...

  async findByIdentity(provider: string, subject: string): Promise<User | null> {
    const id = this.identities.get(`${provider}:${subject}`);
    return id ? this.findById(id) : null;
  }

  async linkIdentity(id: string, provider: string, subject: string): Promise<User | null> {
    this.identities.set(`${provider}:${subject}`, id);
    return this.findById(id);
  }
```

Package hỏi một `OidcAccountResolver` để đưa ra quyết định đó:

```typescript
@@filename(src/auth/account-linker)
import { ConflictException, ForbiddenException, Injectable } from '@nestjs/common';
import {
  AuthenticationRegistry,
  OidcAccountResolver,
  type OAuthTokens,
  type OidcProfile,
  type OidcResolveContext,
} from '@nestjs/authentication';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class AccountLinker extends OidcAccountResolver {
  constructor(
    private readonly usersRepository: UsersRepository,
    registry: AuthenticationRegistry,
  ) {
    super();
    registry.registerHandler('oidc', this);
  }

  async resolveUser(profile: OidcProfile, _tokens: OAuthTokens, { linkTo }: OidcResolveContext) {
    const linked = await this.usersRepository.findByIdentity(profile.provider, profile.subject);

    // "Connect Google" from the account page: link to the signed-in customer.
    if (linkTo) {
      if (linked && linked.id !== linkTo.id) {
        throw new ConflictException('This Google account belongs to another customer');
      }
      return this.usersRepository.linkIdentity(linkTo.id, profile.provider, profile.subject);
    }

    // A returning Google account: sign in the user it is linked to.
    if (linked) {
      return linked;
    }

    // First visit. Trust only an address Google verified, or anyone could
    // claim any account.
    if (!profile.email || !profile.emailVerified) {
      return null; // 403
    }
    const existing = await this.usersRepository.findByEmail(profile.email);
    if (!existing) {
      const user = await this.usersRepository.create(profile.email, { emailVerified: true });
      return this.usersRepository.linkIdentity(user.id, profile.provider, profile.subject);
    }
    // Link by email only if the account's owner proved the address to us too.
    // Otherwise whoever signed up with it, with a password of their choosing,
    // would share the account with the customer.
    if (!existing.emailVerified) {
      throw new ForbiddenException('Sign in with your password, then connect Google from your account');
    }
    return this.usersRepository.linkIdentity(existing.id, profile.provider, profile.subject);
  }
}
```

Liên kết theo email đòi hỏi cả hai bên đều đã xác minh địa chỉ:

- **Google phải đã xác minh nó** (`profile.emailVerified`). Nếu không, bất kỳ ai cũng có thể tạo một tài khoản Google bằng địa chỉ của khách hàng và chiếm tài khoản của họ ở cửa hàng. Trả về `null` sẽ từ chối việc đăng nhập với lỗi 403.
- **Tài khoản ở cửa hàng cũng phải đã xác minh nó** (`existing.emailVerified`). Nếu không, ai đó có thể đăng ký trước bằng địa chỉ của khách hàng với mật khẩu do họ chọn, và vẫn giữ quyền truy cập khi khách hàng đăng nhập bằng Google. Đây gọi là account pre-hijacking. Một tài khoản tạo bằng mật khẩu sẽ ở trạng thái chưa xác minh cho đến khi chủ sở hữu mở [link xác minh](/security/authentication#verify-email-addresses), hoặc [đặt lại mật khẩu](/security/authentication#reset-forgotten-passwords). Cho đến lúc đó, nó nhận lỗi 403 yêu cầu khách hàng đăng nhập bằng mật khẩu rồi kết nối Google từ tài khoản của họ.

Kết nối Google vào một tài khoản mà khách hàng đang đăng nhập thì không cần khớp email gì cả. Package gọi đây là luồng link: nút "Kết nối Google" của web app trỏ tới `GET /auth/oidc/google/login?link=true`. Package chỉ bắt đầu luồng này với một session đã đăng nhập đầy đủ, và không bắt đầu từ trang của site khác (trường hợp đó nhận lỗi 403): một lần link sẽ gắn bất kỳ tài khoản Google nào đang đăng nhập trên trình duyệt này. Ở callback, nó kiểm tra chính session đó vẫn còn sống, rồi gọi `resolveUser()` với `linkTo` là người dùng đang đăng nhập. Resolver liên kết tài khoản Google với họ, trừ khi nó đã thuộc về một khách hàng khác. Session vẫn giữ nguyên, và trình duyệt được redirect tới `redirectTo`.

Bật OpenID Connect bằng preset `google()` và URL mà Google gửi trình duyệt quay về. `:provider` đại diện cho tên của provider, nên một route callback phục vụ được mọi provider bạn thêm vào:

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    // ...
    oidc: {
      // The callback route of OidcController, registered with Google.
      callbackUrl: `${process.env.APP_URL}/auth/oidc/:provider/callback`,
      providers: {
        google: google({
          clientId: process.env.GOOGLE_CLIENT_ID!,
          clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
        }),
      },
    },
  }),
}),
```

Các route là của bạn, nên chúng nằm cùng các route khác, dưới prefix, version và giới hạn tốc độ của bạn. `OidcService.start()` tạo redirect tới Google còn `finish()` xử lý callback; một controller cung cấp hai cái này ra ngoài:

```typescript
@@filename(src/auth/oidc.controller)
import { Controller, Get, Param, Query, Redirect } from '@nestjs/common';
import { OidcService, Public } from '@nestjs/authentication';

@Public()
@Controller('auth/oidc')
export class OidcController {
  constructor(private readonly oidcService: OidcService) {}

  // "Sign in with Google" links here. With ?link=true, "Connect Google"
  // links the Google account to the signed-in customer instead.
  @Get(':provider/login')
  @Redirect()
  login(@Param('provider') provider: string, @Query('redirectTo') redirectTo?: string, @Query('link') link?: string) {
    return this.oidcService.start(provider, { redirectTo, link: link === 'true' });
  }

  // Where Google sends the browser back.
  @Get(':provider/callback')
  @Redirect()
  callback(@Param('provider') provider: string, @Query() query: Record<string, string>) {
    return this.oidcService.finish(provider, query);
  }
}
```

- `GET /auth/oidc/google/login?redirectTo=/orders` redirect trình duyệt tới Google. Nút "Đăng nhập bằng Google" của web app là một link thông thường tới đây. `start()` dùng authorization code flow với PKCE, một `state` và một `nonce`. Giao dịch đăng nhập được lưu phía server dưới `state`, còn trình duyệt nhận một secret có hash SHA-256 chính là `state`, trong một cookie `HttpOnly` tên `__Host-oidc_tx`, có hiệu lực 10 phút.
- `GET /auth/oidc/google/callback` là nơi Google gửi trình duyệt quay về. `finish()` kiểm tra `state` trong query có phải là hash của secret trong cookie của trình duyệt hay không (nên không ai có thể hoàn tất một lần đăng nhập mà họ không bắt đầu trên trình duyệt này, kể cả với một URL callback đọc được từ log hay lịch sử trình duyệt), đổi code lấy token, xác minh chữ ký của ID token với các key mà Google công bố, và kiểm tra issuer, audience, thời hạn và nonce của nó. Nếu không liên lạc được với Google, hoặc Google trả về một endpoint không phải https, câu trả lời là 502, không phải 401. Sau đó nó gọi `resolveUser()`, đăng nhập người dùng thông qua `SignInService` (nên khách hàng có authenticator sẽ nhận một session pending), và trả về redirect tới `redirectTo`, hoặc tới `/`. Chỉ đường dẫn tương đối mới được chấp nhận làm `redirectTo`, nên luồng đăng nhập không thể bị biến thành open redirect.
- Cả hai đều đọc request và đặt cookie thông qua HTTP adapter của Nest, và trả về thứ mà `@Redirect()` mong đợi, nên controller chạy được trên cả Express lẫn Fastify, không cần `@Req()` hay `@Res()`.

Đăng ký controller và resolver trong `AuthModule`:

```typescript
@@filename(src/auth/auth.module)
controllers: [
  // ...
  MfaController,
  OidcController,
],
providers: [
  // ...
  PasswordResetMailer,
  AccountLinker,
],
```

Preset `github()` hoạt động theo cùng cách. `microsoft()` nhận thêm tenant id của directory làm tùy chọn `tenant`, cạnh `clientId` và `clientSecret`: một GUID lấy từ trang Overview của Microsoft Entra admin center, như `process.env.ENTRA_TENANT_ID`. Một domain, hoặc các giá trị multi-tenant `common`, `organizations` và `consumers`, sẽ lỗi lúc khởi động: với những giá trị đó, Microsoft công bố một issuer khác với issuer được yêu cầu, và mọi lần đăng nhập sẽ thất bại. Hãy thêm chúng cạnh `google` trong `providers`, và đăng ký URL callback với từng provider, thay `google` bằng tên của nó.

Một ứng dụng phục vụ dưới nhiều domain, như mỗi khách hàng một domain, không thể chỉ định một URL callback duy nhất: một lần đăng nhập bắt đầu trên domain nào thì phải quay về domain đó. Thay vào đó, hãy truyền một hàm nhận request làm `callbackUrl`. `start()` gọi nó khi bắt đầu đăng nhập, và `finish()` gọi lại nó ở callback, nên nó phải trả về cùng một URL cho cả hai. Hãy so sánh host với danh sách domain của riêng bạn thay vì tin vào header, và đăng ký mọi URL mà hàm có thể trả về với từng provider:

```typescript
@@filename(src/app.module)
oidc: {
  callbackUrl: ({ headers }) => {
    const host = CUSTOMER_DOMAINS.find((domain) => domain === headers.host);
    if (!host) {
      throw new NotFoundException();
    }
    return `https://${host}/auth/oidc/:provider/callback`;
  },
  providers: {
    // ...
  },
},
```

Hàm này cũng có thể là `async`, để tra cứu domain trong database. Bất cứ thứ gì nó throw ra đều là câu trả lời cho lần đăng nhập, như lỗi 404 ở trên cho một domain mà ứng dụng không phục vụ, và một URL không phải tuyệt đối sẽ làm lần đăng nhập thất bại với lỗi nêu tên hàm. Cookie `__Host-oidc_tx` thuộc về domain đã đặt nó, nên một lần đăng nhập kết thúc trên domain nơi nó bắt đầu. Nếu hàm lỡ trả về một URL khác ở callback, provider sẽ từ chối code, và callback nhận lỗi 401. Đằng sau một proxy viết lại host, hãy đọc header mà nó chuyển tiếp, như `X-Forwarded-Host`, và chỉ từ proxy mà bạn tin tưởng.

Một số ứng dụng chỉ biết được các provider của mình lúc runtime. Một ứng dụng bán cho doanh nghiệp có thể cấp cho mỗi khách hàng một OIDC client riêng, hoặc cho họ mang identity provider của riêng mình, được thiết lập từ trang admin và lưu trong database. Thay vào đó, hãy truyền một hàm nhận tên provider làm `providers`. `start()` gọi nó khi bắt đầu đăng nhập, và `finish()` gọi lại nó ở callback. Hãy trả về cấu hình của provider, hoặc `undefined` với tên mà bạn không phục vụ, trường hợp này nhận lỗi 404:

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  imports: [TenantsModule],
  inject: [TenantsRepository],
  useFactory: (tenantsRepository: TenantsRepository) => ({
    // ...
    oidc: {
      callbackUrl: `${process.env.APP_URL}/auth/oidc/:provider/callback`,
      // GET /auth/oidc/acme/login signs in through Acme's own client.
      providers: async (name) => {
        const tenant = await tenantsRepository.findByKey(name);
        return tenant ? { issuer: tenant.issuer, clientId: tenant.clientId, clientSecret: tenant.clientSecret } : undefined;
      },
    },
  }),
}),
```

Cấu hình được tra lại ở callback thay vì lưu cùng lần đăng nhập, nên một secret bạn xoay vòng trong database sẽ được dùng ngay từ lần gọi tiếp theo, kể cả với một lần đăng nhập đang diễn ra. Mỗi cấu hình mà hàm trả về đều được kiểm tra giống như dạng object được kiểm tra lúc khởi động: một cấu hình không có `clientId`, hoặc không có `clientSecret` trừ khi `tokenEndpointAuthMethod` của nó là `'none'`, sẽ làm lần đăng nhập thất bại với lỗi nêu tên hàm. Hàm chạy ở mỗi lần đăng nhập và callback, nên hãy cache việc tra cứu nếu nó chậm. Package cache tài liệu discovery và key của mỗi provider theo issuer, nên các khách hàng đăng nhập qua cùng một provider sẽ dùng chung chúng.

Identity được liên kết theo (provider, subject), và provider là cái tên, nên mỗi tên phải đại diện cho một client của một provider. Hãy đưa khách hàng vào trong tên, như `acme` ở trên, thay vì dùng một tên, như `okta`, cho provider của mọi khách hàng: provider của hai khách hàng có thể cấp ra cùng một subject. Khi khách hàng mang identity provider của riêng họ, còn hai điều nữa thay đổi:

- **Provider của họ bảo đảm cho bất kỳ địa chỉ nào nó muốn.** Nó có thể đánh dấu bất kỳ địa chỉ nào là đã xác minh, kể cả địa chỉ của người dùng thuộc khách hàng khác. Resolver ở trên liên kết tài khoản theo email đã xác minh. Với provider do khách hàng của bạn kiểm soát, chỉ liên kết theo email với các tài khoản của chính khách hàng đó, hoặc không liên kết theo email gì cả.
- **Issuer là dữ liệu người dùng nhập vào.** Package tải tài liệu discovery, key và token từ các URL mà cấu hình chỉ định, và không có gì ngăn những request đó đi vào mạng nội bộ của bạn. Hãy kiểm tra issuer mà khách hàng nhập vào với danh sách provider bạn hỗ trợ trước khi lưu nó.

#### Thêm đăng nhập bằng magic link <a id="add-magic-link-sign-in"></a>

Một magic link đăng nhập khách hàng từ hộp thư của họ, không cần mật khẩu. Package tạo và kiểm tra các link; việc gửi chúng đi là việc của bạn, thông qua một `MagicLinkHandler`. Cửa hàng gửi chúng qua email giống như link xác minh, với template và mail class riêng:

```html
@@filename(src/mail/templates/magic-link.html)
<p><a href="{{ '{' }}{{ '{' }} url {{ '}' }}{{ '}' }}">Sign in to the store</a></p>
<p>The link works once, for 15 minutes. If you didn't ask for it, ignore this email.</p>
```

```typescript
@@filename(src/auth/magic-link.mailer)
import { ForbiddenException, Injectable } from '@nestjs/common';
import { AuthenticationRegistry, MagicLinkHandler, type MagicLink } from '@nestjs/authentication';
import { Mailer, type Mailable } from '@nestjs/mail';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class MagicLinkMail implements Mailable<MagicLink> {
  render({ url }: MagicLink) {
    return {
      subject: 'Your sign-in link',
      template: 'magic-link',
      context: { url },
    };
  }
}

@Injectable()
export class MagicLinkMailer extends MagicLinkHandler {
  constructor(
    private readonly usersRepository: UsersRepository,
    private readonly mailer: Mailer,
    registry: AuthenticationRegistry,
  ) {
    super();
    registry.registerHandler('magicLink', this);
  }

  async send(link: MagicLink) {
    await this.mailer.send(MagicLinkMail, { to: link.email, data: link });
  }

  // Runs when the link is used, which proves the address. The account returned
  // carries its stored `email`, and signs in only if the link went to that address.
  async resolveUser(email: string) {
    const user = await this.usersRepository.findByEmail(email);
    if (!user) {
      // Passwordless sign-up. Return null instead to refuse unknown addresses.
      return this.usersRepository.create(email, { emailVerified: true });
    }
    // A password account whose address nobody confirmed: whoever chose that
    // password may not own the address. Resetting the password proves both.
    if (!user.emailVerified) {
      throw new ForbiddenException('Sign in with your password, or reset it');
    }
    return user;
  }
}
```

Bật magic link: handler trong `AuthModule`, và URL mà các link trỏ tới trong tùy chọn:

```typescript
@@filename(src/auth/auth.module)
providers: [
  // ...
  AccountLinker,
  MagicLinkMailer,
],
```

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    // ...
    magicLink: { url: `${process.env.APP_URL}/sign-in/magic` },
  }),
}),
```

`MagicLinkService.create()` tạo một token ngẫu nhiên 256 bit, có hiệu lực 15 phút và chỉ dùng được một lần, rồi truyền link cho handler của bạn. Nó lưu hash SHA-256 của token kết hợp với một secret mà chỉ cookie giao dịch của trình duyệt này giữ (xem bên dưới), nên một link đọc được từ log, hoặc bị chuyển tiếp, sẽ không tìm thấy gì, kể cả với một cookie giả mạo. Với `bindToBrowser: false`, nó chỉ lưu hash của riêng token. Token được thêm vào URL dưới dạng query parameter `token`, và code của bạn không bao giờ nhìn thấy nó theo cách nào khác.

Hãy trỏ link tới một trang của web app, không phải tới API. Trang đó đọc token từ URL của nó và POST ngược lại. Các trình quét email và trình xem trước link đi theo link trong email bằng request GET, và sẽ dùng hết token trước khi khách hàng kịp click. Trang phải nằm cùng site với API: việc xin link sẽ đặt một cookie mà trình duyệt gửi kèm token.

```typescript
@@filename(src/auth/magic-link.controller)
import { Body, Controller, HttpCode, Post, UnauthorizedException } from '@nestjs/common';
import { MagicLinkService, Public } from '@nestjs/authentication';
import { EmailDto } from './auth.dto.js';

@Public()
@Controller('auth/magic-link')
export class MagicLinkController {
  constructor(private readonly magicLinkService: MagicLinkService) {}

  @Post()
  @HttpCode(202)
  async request(@Body() body: EmailDto, @Body('redirectTo') redirectTo?: string) {
    await this.magicLinkService.create(body.email, { redirectTo });
  }

  // Called by the page the link opens, which POSTs the token from its URL.
  @Post('consume')
  @HttpCode(200)
  async consume(@Body('token') token: string) {
    // A link opened in another browser throws MagicLinkError, which the module
    // answers: a 401 telling the customer to open it where they asked for it.
    const result = await this.magicLinkService.consume(token);
    if (!result) {
      throw new UnauthorizedException('Invalid or expired link');
    }
    return { redirectTo: result.redirectTo ?? '/', mfaRequired: result.session.mfa === 'pending' };
  }
}
```

- Route xin link trả lời 202 bất kể địa chỉ có tài khoản hay không, và tài khoản chỉ được tạo khi link được dùng. Một request gửi từ trang của site khác sẽ nhận lỗi 403, giống như đăng nhập: nếu không, trang đó có thể đặt cookie giao dịch của trình duyệt này cho một link tới địa chỉ của tác giả trang, rồi lừa khách hàng mở nó (login CSRF).
- `consume()` hủy token, gọi `resolveUser()`, và đăng nhập người dùng thông qua `SignInService`, thứ đặt cookie, nên xác thực hai lớp vẫn được áp dụng. `resolveUser()` trả về tài khoản cùng `email` đã lưu của nó, và link chỉ đăng nhập tài khoản nếu đó đúng là địa chỉ mà link được gửi tới, so sánh sau khi trim, chuyển chữ thường và chuẩn hóa Unicode NFC. Một phép tra cứu bỏ qua dấu hoặc dấu chấm, như collation mặc định của MySQL làm, không thể trao tài khoản của khách hàng này cho một hộp thư khác: thay vào đó `consume()` trả về `null`.
- Một link chỉ dùng được trên trình duyệt đã xin nó. `create()` đặt một cookie giao dịch, `__Host-magic_link_tx`, và `consume()` từ chối token nếu không có cookie này, trước khi tra cứu bất cứ thứ gì: nó throw một `MagicLinkError`, và module trả lời bằng lỗi 401 có `error` là `not_this_browser` cùng thông báo yêu cầu khách hàng mở link mới nhất trên trình duyệt mà họ đã xin link, hoặc xin link mới ở đây. Nếu không, bất kỳ ai cũng có thể xin một link cho địa chỉ của chính họ rồi lừa khách hàng mở nó, khiến trình duyệt của khách hàng đăng nhập vào tài khoản của kẻ tấn công (login CSRF). Link bị từ chối vẫn có hiệu lực trên trình duyệt đã xin nó, và câu trả lời không để lộ gì về token, vì một token bịa ra cũng nhận cùng câu trả lời. Cookie giữ năm link gần nhất mà trình duyệt đã xin, nên một khách hàng bấm "Gửi lại" rồi mở email đầu tiên vẫn đăng nhập được; một link cũ hơn năm link đó cũng nhận lỗi 401 tương tự. Vì vậy một khách hàng xin link trên laptop rồi mở email trên điện thoại sẽ được bảo mở nó trên laptop, hoặc xin link mới trên điện thoại, link đó khi ấy sẽ dùng được trên điện thoại; một ứng dụng muốn bản thân link dùng được trên điện thoại thì đặt `bindToBrowser: false` trong tùy chọn `magicLink`. Link không tồn tại, đã dùng hoặc đã hết hạn, và các địa chỉ bị handler từ chối, đều nhận cùng một câu trả lời chung từ controller: `consume()` trả về `null` cho tất cả, và chỉ có event `magic-link-refused` cho biết đó là trường hợp nào.
- Việc dùng link chứng minh luôn địa chỉ, nên tài khoản tạo bằng link là đã xác minh. Một tài khoản tạo bằng mật khẩu thì khác khi địa chỉ của nó chưa được xác minh: link chứng minh ai đang sở hữu địa chỉ lúc này, chứ không chứng minh ai đã chọn mật khẩu, nên handler từ chối nó với lỗi 403 thay vì trao một tài khoản đã bị pre-hijack cho chủ sở hữu. Khi chủ sở hữu đã dùng [link xác minh](/security/authentication#verify-email-addresses), hoặc [đặt lại mật khẩu](/security/authentication#reset-forgotten-passwords), magic link cũng dùng được cho tài khoản đó.
- `redirectTo` chỉ được giữ qua vòng đi về nếu nó là một đường dẫn tương đối, như `/orders`.

Với schema Zod:

```typescript
@@filename(src/auth/magic-link.controller)
import { emailSchema, type EmailDto } from './auth.schemas.js';
// ...
@Post()
@HttpCode(202)
async request(@Body({ schema: emailSchema }) body: EmailDto, @Body('redirectTo') redirectTo?: string) {
  // ...
}
```

Đăng ký controller:

```typescript
@@filename(src/auth/auth.module)
controllers: [
  // ...
  OidcController,
  MagicLinkController,
],
```

#### Cho khách hàng quản lý session <a id="let-customers-manage-their-sessions"></a>

Session nằm trên server, nên khách hàng có thể xem họ đang đăng nhập ở đâu và kết thúc bất kỳ session nào trong số đó. Để phân biệt các session, hãy ghi lại trình duyệt mà mỗi session thuộc về. `session.metadata` chạy mỗi khi khách hàng đăng nhập, bằng mật khẩu, bằng Google hay bằng magic link, và những gì nó trả về được lưu cùng session mới:

```typescript
@@filename(src/app.module)
AuthenticationModule.forRootAsync({
  useFactory: () => ({
    session: {
      absoluteTtl: '14d', // signed out after 14 days, however active
      idleTtl: '3d', // or after 3 days without a request
      // Stored with every new session, whichever way the customer signed in.
      metadata: (request) => ({ userAgent: request.headers['user-agent'] }),
    },
    // ...
  }),
}),
```

Sau đó liệt kê các session, và kết thúc chúng:

```typescript
@@filename(src/auth/sessions.controller)
import { Controller, Delete, Get, HttpCode, NotFoundException, Param, Post, UnauthorizedException } from '@nestjs/common';
import {
  CurrentSession,
  CurrentUser,
  Public,
  SessionService,
  SignInService,
  type SessionRecord,
} from '@nestjs/authentication';

@Controller('auth')
export class SessionsController {
  constructor(
    private readonly sessionService: SessionService,
    private readonly signInService: SignInService,
  ) {}

  @Get('sessions')
  async list(@CurrentUser('id') userId: string, @CurrentSession() current: SessionRecord) {
    const sessions = await this.sessionService.list(userId);
    return sessions.map(({ id, createdAt, lastActiveAt, metadata }) => ({
      id,
      createdAt,
      lastActiveAt,
      userAgent: metadata?.userAgent ?? null,
      current: id === current.id,
    }));
  }

  // revoke() only ends a session of this user: another customer's id is a 404.
  @Delete('sessions/:id')
  @HttpCode(204)
  async revoke(@CurrentUser('id') userId: string, @Param('id') id: string) {
    if (!(await this.sessionService.revoke(id, { userId }))) {
      throw new NotFoundException();
    }
  }

  // Public, so that a session still waiting for its second factor can sign
  // out too. signOut() ends the session in this browser's cookie.
  @Public()
  @Post('sign-out')
  @HttpCode(204)
  async signOut() {
    if (!(await this.signInService.signOut())) {
      throw new UnauthorizedException(); // no session cookie, e.g. a bearer token
    }
  }

  @Post('sign-out-everywhere')
  @HttpCode(204)
  async signOutEverywhere(@CurrentUser('id') userId: string) {
    await this.signInService.signOutEverywhere(userId);
  }
}
```

- Session id là hash SHA-256 của token trong cookie. Hiển thị chúng cho chủ sở hữu là an toàn, vì không thể suy ra cookie từ id. `revoke()` nhận cả người dùng lẫn id, và chỉ kết thúc session thuộc về người dùng đó, nên một id lấy từ URL không thể kết thúc session của khách hàng khác.
- `sign-out` là `@Public()`, giống như `verify` trong [xác thực hai lớp](/security/authentication#add-two-factor-authentication), nên một khách hàng chưa bao giờ hoàn tất yếu tố thứ hai vẫn đăng xuất được. `signOut()` kết thúc session trong cookie của trình duyệt này và xóa cookie. Nó trả về `false` khi không có session nào, và route trả lời 401: một bearer token ở đây không đăng xuất gì cả.
- `signOutEverywhere()` kết thúc mọi session và, khi ứng dụng có cấp, mọi refresh token của người dùng, rồi xóa cookie của trình duyệt này. Các access token đã cấp vẫn còn hiệu lực cho đến khi hết hạn, đó là lý do chúng chỉ sống 15 phút.

App mobile đăng xuất khỏi một thiết bị bằng cách thu hồi refresh token của nó. Thêm một route vào `TokensController`. `TokenService.revoke()` kết thúc family của token: chính token đó, các token trước và các token kế tiếp của nó:

```typescript
@@filename(src/auth/tokens.controller)
// Signs the mobile app out on this device. Unknown tokens get the same
// answer, as in RFC 7009.
@Post('revoke')
@HttpCode(204)
async revoke(@Body('refreshToken') refreshToken: string) {
  await this.tokenService.revoke(refreshToken);
}
```

Đăng ký controller. Đây là module hoàn chỉnh, với mọi credential provider và handler của bài hướng dẫn:

```typescript
@@filename(src/auth/auth.module)
import { Module } from '@nestjs/common';
import { UsersModule } from '../users/users.module.js';
import { AccountLinker } from './account-linker.js';
import { AuthController } from './auth.controller.js';
import { CredentialsService } from './credentials.service.js';
import { EmailVerificationController } from './email-verification.controller.js';
import { EmailVerificationMailer } from './email-verification.mailer.js';
import { JwtAuth } from './jwt-auth.provider.js';
import { MagicLinkController } from './magic-link.controller.js';
import { MagicLinkMailer } from './magic-link.mailer.js';
import { MfaController } from './mfa.controller.js';
import { OidcController } from './oidc.controller.js';
import { PasswordResetController } from './password-reset.controller.js';
import { PasswordResetMailer } from './password-reset.mailer.js';
import { SessionAuth } from './session-auth.provider.js';
import { SessionsController } from './sessions.controller.js';
import { TokensController } from './tokens.controller.js';

@Module({
  imports: [UsersModule],
  controllers: [
    AuthController,
    EmailVerificationController,
    PasswordResetController,
    TokensController,
    MfaController,
    OidcController,
    MagicLinkController,
    SessionsController,
  ],
  providers: [
    SessionAuth,
    JwtAuth,
    CredentialsService,
    EmailVerificationMailer,
    PasswordResetMailer,
    AccountLinker,
    MagicLinkMailer,
  ],
})
export class AuthModule {}
```

Hãy xoay vòng session mỗi khi quyền hạn thay đổi, ví dụ sau khi đổi mật khẩu hoặc khi một khách hàng trở thành nhân viên: `SignInService.rotateSession()` cấp cho session của trình duyệt này một id mới, và đặt cookie mới; `completeMfa()` vốn đã làm việc này. Nó resolve ra `null`, và không đặt cookie, khi trình duyệt không có session hoặc đã mất session trong lúc đó: do đăng xuất khỏi mọi nơi, đặt lại mật khẩu, hoặc một request khác đã xoay vòng nó trước.

#### Giới hạn tốc độ đăng nhập <a id="rate-limit-sign-in"></a>

`@nestjs/authentication` không giới hạn tốc độ request. Đó là việc của `@nestjs/throttler`, một package riêng:

```bash
$ npm i --save @nestjs/throttler
```

Chỉ giới hạn theo địa chỉ IP là quá thô cho việc đăng nhập. Các khách hàng đằng sau cùng một địa chỉ mạng dùng chung nó, nên giới hạn không thể đủ thấp để ngăn một client đoán mật khẩu của một tài khoản. Hãy dùng hai [định nghĩa throttler](/security/rate-limiting#multiple-throttler-definitions); mỗi request được tính vào cả hai. `default` đếm theo địa chỉ IP, trên mọi route. `account` đếm theo email và địa chỉ IP, ở bất cứ đâu request body chỉ định một tài khoản:

```typescript
@@filename(src/auth/account-email)
/** The address the request body names, trimmed, lowercased and in Unicode NFC, or `''`. */
export function accountEmail(req: { body?: { email?: unknown } }): string {
  const email = req.body?.email;
  return typeof email === 'string' ? email.trim().normalize('NFC').toLowerCase() : '';
}
```

Đăng ký `ThrottlerModule` với cả hai định nghĩa, và `ThrottlerGuard` làm global guard:

```typescript
@@filename(src/app.module)
import { APP_GUARD, APP_PIPE } from '@nestjs/core';
import { ThrottlerGuard, ThrottlerModule, minutes, normalizeIp } from '@nestjs/throttler';
import { accountEmail } from './auth/account-email.js';
// ...

@Module({
  imports: [
    ThrottlerModule.forRoot([
      // Per IP address, on every route: 100 requests a minute.
      { name: 'default', ttl: minutes(1), limit: 100 },
      // Per email and IP address, wherever the request body names an account.
      {
        name: 'account',
        ttl: minutes(15),
        limit: 5,
        skipIf: (context) => !accountEmail(context.switchToHttp().getRequest()),
        getTracker: (req) => `${accountEmail(req)}|${normalizeIp(req.ip)}`,
      },
    ]),
    // ...
  ],
  providers: [
    { provide: APP_PIPE, useValue: new ValidationPipe({ whitelist: true }) },
    { provide: APP_GUARD, useClass: ThrottlerGuard },
  ],
})
export class AppModule {}
```

Guard chạy trước validation, nên `accountEmail()` kiểm tra `email` có phải là chuỗi hay không. `normalizeIp()` gom các địa chỉ IPv6 theo prefix `/64` của chúng, giống như tracker của chính throttler làm, nên một client không thể có bộ đếm mới cho mỗi địa chỉ trong subnet của nó.

Guard được đăng ký trong root module, nên nó chạy trước authentication guard. Global guard chạy theo thứ tự module, và root module đứng đầu. Điều đó có nghĩa là các bearer token đoán mò cũng bị tính vào giới hạn, thay vì chỉ bị từ chối với lỗi 401.

Cuối cùng, siết chặt giới hạn trên các route kiểm tra mật khẩu hoặc gửi email. Mỗi `@Throttle()` đếm theo route, và đặt cả hai giới hạn: theo địa chỉ IP, và theo tài khoản:

```typescript
@@filename(src/auth/auth.controller)
@Throttle({
  default: { limit: 30, ttl: minutes(15) },
  account: { limit: 5, ttl: minutes(15) },
})
@Post('sign-in')
// ...

@SkipThrottle({ account: true })
@Throttle({ default: { limit: 10, ttl: hours(1) } })
@Post('sign-up')
```

```typescript
@@filename(src/auth/tokens.controller)
@Throttle({
  default: { limit: 30, ttl: minutes(15) },
  account: { limit: 5, ttl: minutes(15) },
})
@Post()
```

```typescript
@@filename(src/auth/magic-link.controller)
@Throttle({
  default: { limit: 10, ttl: minutes(15) },
  account: { limit: 3, ttl: minutes(15) },
})
@Post()
```

```typescript
@@filename(src/auth/password-reset.controller)
import { accountEmail } from './account-email.js';
// ...

@Throttle({
  default: { limit: 10, ttl: minutes(15) },
  // Per address, from any IP address.
  account: { limit: 3, ttl: minutes(15), getTracker: accountEmail },
})
@Post('forgot')
```

`Throttle`, `SkipThrottle`, `minutes` và `hours` được import từ `@nestjs/throttler`. Giới hạn theo địa chỉ IP là chuyện cân nhắc, vì văn phòng và nhà mạng di động đặt nhiều khách hàng sau một địa chỉ. Giới hạn `account` áp dụng cho mọi route có `email` trong request body, ở mức 5 request mỗi 15 phút trừ khi route tự đặt giới hạn riêng; `@SkipThrottle({{ '{' }} account: true {{ '}' }})` loại một route ra.

- `forgot` đếm theo địa chỉ, bất kể địa chỉ IP, nên không ai có thể làm đầy hộp thư của khách hàng bằng link đặt lại mật khẩu, dù từ một hay nhiều địa chỉ IP. Ai đó dùng hết giới hạn này chỉ làm chậm request của chính khách hàng: các link họ gây ra đều được gửi tới khách hàng, và link nào cũng dùng được.
- Request xin magic link giữ email và địa chỉ IP đi cùng nhau. Một link chỉ dùng được trên trình duyệt đã xin nó, nên chỉ giới hạn theo địa chỉ sẽ cho phép bất kỳ ai dùng hết lượt link của khách hàng từ trình duyệt của chính họ, và ngăn khách hàng đăng nhập.
- Đăng ký mỗi lần dùng một địa chỉ mới, nên nó bỏ qua giới hạn `account` và để giới hạn theo địa chỉ IP làm việc. Nếu không, một khách hàng có mật khẩu không đạt quy tắc đăng ký vài lần sẽ bị từ chối.

Các mã xác thực hai lớp không cần throttle riêng: package khóa các mã của một tài khoản sau 5 lần sai, từ bất kỳ địa chỉ IP, route hay transport nào. `POST /auth/password/reset` cũng vậy: một token đoán mò chỉ tốn một lần tra cứu, và có tới 2^256 token.

> info **Gợi ý** Đằng sau một load balancer hoặc reverse proxy, mọi request dường như đều đến từ proxy. Hãy bật `trust proxy`, như mô tả trong phần [Proxy](/security/rate-limiting#proxies) của throttler, để tracker thấy được địa chỉ của client.
#### Giữ session và token trong database của bạn <a id="keep-sessions-and-tokens-in-your-database"></a>

Đến giờ, mọi thứ mà package lưu trữ đều nằm trong bộ nhớ: session, refresh token, authenticator và mã khôi phục, cùng các link và lần đăng nhập đang chờ. Chúng sẽ mất khi khởi động lại, và một instance thứ hai của API sẽ không thấy chúng. Package không tự nói chuyện với database của bạn. Nó mô tả những gì nó lưu trữ dưới dạng sáu interface, `SessionStore`, `RefreshTokenStore`, `MfaStore`, `MagicLinkStore`, `OidcStateStore` và `EmailTokenStore`, và ứng dụng của bạn implement chúng bằng cách truy cập database mà nó vốn đã có, rồi đăng ký bản implement đó.

Bước này trình bày bản implement đó hai lần, cho hai ORM mà các bài hướng dẫn trong loạt này dùng: lần đầu với Drizzle, là hướng chính của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối bước, cùng store đó cho ứng dụng dùng ORM là TypeORM. Hãy chọn một trong hai.

Store dùng PostgreSQL với Drizzle, qua [`@nestjs/drizzle`](/data/drizzle), bước này giả định ứng dụng của bạn đã có sẵn nó. `DrizzleModule` mở một pool `pg` từ URL của database và cung cấp database Drizzle, và nó đóng pool khi ứng dụng tắt, sau khi package đã hoàn tất công việc đang dở dang (ví dụ một link đặt lại mật khẩu đang được gửi đi). Thêm URL vào `.env`, và đăng ký module trong `AppModule`:

```bash
DATABASE_URL=postgres://localhost:5432/store
```

```typescript
@@filename(src/app.module)
import { DrizzleModule } from '@nestjs/drizzle';
import { drizzle } from 'drizzle-orm/node-postgres';
// ...
@Module({
  imports: [
    // The Drizzle database, on a pg pool the module closes when the application shuts down.
    DrizzleModule.forRootAsync({
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL! }),
    }),
    // ...
  ],
})
export class AppModule {}
```

Bắt đầu với các bảng. Chúng là các bảng Drizzle thông thường trong schema của ứng dụng, nằm cạnh các bảng của riêng bạn:

```typescript
@@filename(src/database/schema)
// The store's Drizzle tables. drizzle-kit generates the migrations from this file.
import { boolean, index, integer, jsonb, pgTable, primaryKey, text, timestamp } from 'drizzle-orm/pg-core';

const at = (name: string) => timestamp(name, { withTimezone: true, mode: 'date' });

// Authentication state: what DrizzleAuthenticationStore (src/auth) keeps for @nestjs/authentication.
// Tokens, links and sessions are stored by their SHA-256; TOTP secrets arrive encrypted.

export const sessions = pgTable(
  'sessions',
  {
    id: text('id').primaryKey(),
    userId: text('user_id').notNull(),
    createdAt: at('created_at').notNull(),
    expiresAt: at('expires_at').notNull(),
    lastActiveAt: at('last_active_at').notNull(),
    mfa: text('mfa', { enum: ['pending', 'verified'] }),
    metadata: jsonb('metadata').$type<Record<string, unknown>>(),
  },
  (table) => [
    index('sessions_user_id_idx').on(table.userId),
    index('sessions_expires_at_idx').on(table.expiresAt),
  ],
);

export const refreshTokens = pgTable(
  'refresh_tokens',
  {
    id: text('id').primaryKey(),
    familyId: text('family_id').notNull(),
    userId: text('user_id').notNull(),
    createdAt: at('created_at').notNull(),
    expiresAt: at('expires_at').notNull(),
    familyExpiresAt: at('family_expires_at').notNull(),
    usedAt: at('used_at'),
    // A family is revoked when any of its tokens is: that covers a successor saved after the revocation.
    revoked: boolean('revoked').notNull().default(false),
    claims: jsonb('claims').$type<Record<string, unknown>>(),
  },
  (table) => [
    index('refresh_tokens_family_id_idx').on(table.familyId),
    index('refresh_tokens_user_id_idx').on(table.userId),
    index('refresh_tokens_family_expires_at_idx').on(table.familyExpiresAt),
  ],
);

export const mfaAuthenticators = pgTable('mfa_authenticators', {
  userId: text('user_id').primaryKey(),
  secret: text('secret').notNull(),
  confirmed: boolean('confirmed').notNull(),
  pendingSecret: text('pending_secret'),
  lastUsedStep: integer('last_used_step'),
});

export const mfaRecoveryCodes = pgTable(
  'mfa_recovery_codes',
  {
    userId: text('user_id').notNull(),
    codeHash: text('code_hash').notNull(),
  },
  (table) => [primaryKey({ columns: [table.userId, table.codeHash] })],
);

export const mfaFailures = pgTable(
  'mfa_failures',
  {
    id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
    userId: text('user_id').notNull(),
    failedAt: at('failed_at').notNull(),
  },
  (table) => [
    index('mfa_failures_user_id_failed_at_idx').on(table.userId, table.failedAt),
    index('mfa_failures_failed_at_idx').on(table.failedAt),
  ],
);

export const magicLinks = pgTable(
  'magic_links',
  {
    id: text('id').primaryKey(),
    email: text('email').notNull(),
    createdAt: at('created_at').notNull(),
    expiresAt: at('expires_at').notNull(),
    redirectTo: text('redirect_to'),
  },
  (table) => [index('magic_links_expires_at_idx').on(table.expiresAt)],
);

export const oidcLogins = pgTable(
  'oidc_logins',
  {
    state: text('state').primaryKey(),
    provider: text('provider').notNull(),
    codeVerifier: text('code_verifier').notNull(),
    nonce: text('nonce'),
    redirectTo: text('redirect_to'),
    // Set for "connect your Google account" from a signed-in session.
    linkUserId: text('link_user_id'),
    linkSessionId: text('link_session_id'),
    createdAt: at('created_at').notNull(),
    expiresAt: at('expires_at').notNull(),
  },
  (table) => [index('oidc_logins_expires_at_idx').on(table.expiresAt)],
);

export const emailTokens = pgTable(
  'email_tokens',
  {
    id: text('id').primaryKey(),
    purpose: text('purpose', { enum: ['password-reset', 'email-verification'] }).notNull(),
    userId: text('user_id').notNull(),
    email: text('email').notNull(),
    fingerprint: text('fingerprint'),
    createdAt: at('created_at').notNull(),
    expiresAt: at('expires_at').notNull(),
  },
  (table) => [
    index('email_tokens_user_id_purpose_idx').on(table.userId, table.purpose),
    index('email_tokens_expires_at_idx').on(table.expiresAt),
  ],
);
```

- Session, token và link được lưu dưới dạng hash SHA-256 của các giá trị trong cookie và email, TOTP secret đến dưới dạng đã mã hóa bằng key của bạn (xem [xác thực hai lớp](/security/authentication#add-two-factor-authentication)), và mã khôi phục đến dưới dạng đã hash bằng scrypt. Không thứ gì trong các bảng này có thể bị dùng lại.
- `revoked` nằm trên từng refresh token thay vì trong một bảng family: một family được tính là đã thu hồi khi bất kỳ token nào của nó bị thu hồi. Điều này bao phủ cả trường hợp một token được lưu sau khi đã thu hồi, bởi một lần refresh bị thua trong cuộc đua.

Sinh migration từ schema, và áp dụng nó:

```bash
$ npx drizzle-kit generate --name=authentication
No config path provided, using default 'drizzle.config.ts'
Reading config file '/store/drizzle.config.ts'
8 tables
email_tokens 7 columns 2 indexes 0 fks
magic_links 5 columns 1 indexes 0 fks
mfa_authenticators 5 columns 0 indexes 0 fks
mfa_failures 3 columns 2 indexes 0 fks
mfa_recovery_codes 2 columns 0 indexes 0 fks
oidc_logins 9 columns 1 indexes 0 fks
refresh_tokens 9 columns 3 indexes 0 fks
sessions 7 columns 2 indexes 0 fks

[✓] Your SQL migration file ➜ drizzle/0000_authentication.sql 🚀
$ npx drizzle-kit migrate
No config path provided, using default 'drizzle.config.ts'
Reading config file '/store/drizzle.config.ts'
Using 'pg' driver for database querying
[✓] migrations applied successfully!
```

Giờ là store. Nó là một provider như mọi provider khác: nó inject database Drizzle, implement sáu interface bằng query builder của Drizzle, và tự đăng ký với `AuthenticationStorage` của package từ constructor của nó:

```typescript
@@filename(src/auth/drizzle-authentication.store)
import { Injectable } from '@nestjs/common';
import {
  AuthenticationStorage,
  type EmailTokenPurpose,
  type EmailTokenRecord,
  type EmailTokenStore,
  type MagicLinkRecord,
  type MagicLinkStore,
  type MfaStore,
  type OidcStateStore,
  type OidcTransaction,
  type RefreshTokenRecord,
  type RefreshTokenStore,
  type SessionRecord,
  type SessionStore,
  type TotpRecord,
} from '@nestjs/authentication';
import { InjectDrizzle } from '@nestjs/drizzle';
import { and, desc, eq, gt, isNull, lt, lte, or, sql } from 'drizzle-orm';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';
import {
  emailTokens,
  magicLinks,
  mfaAuthenticators,
  mfaFailures,
  mfaRecoveryCodes,
  oidcLogins,
  refreshTokens,
  sessions,
} from '../database/schema.js';

/**
 * Keeps sessions, refresh tokens, authenticators and pending links in
 * PostgreSQL, through Drizzle. Every method that decides whether something
 * works once is a single conditional statement, so the guarantees hold with
 * any number of API instances.
 */
@Injectable()
export class DrizzleAuthenticationStore
  implements SessionStore, RefreshTokenStore, MfaStore, MagicLinkStore, OidcStateStore, EmailTokenStore
{
  /** Pending links and logins kept per table: anyone can create them. */
  protected readonly maxPending: number = 100_000;

  constructor(
    @InjectDrizzle() private readonly db: NodePgDatabase,
    storage: AuthenticationStorage,
  ) {
    storage.registerSource({
      sessions: this,
      refreshTokens: this,
      mfa: this,
      magicLinks: this,
      oidcStates: this,
      emailTokens: this,
    });
  }

  // Sessions

  async getSession(id: string): Promise<SessionRecord | undefined> {
    const [row] = await this.db.select().from(sessions).where(eq(sessions.id, id));
    return row && withoutNulls(row);
  }

  async createSession(record: SessionRecord): Promise<void> {
    await this.db.insert(sessions).values(record);
    await this.db.delete(sessions).where(lte(sessions.expiresAt, record.createdAt));
  }

  async touchSession(id: string, lastActiveAt: Date): Promise<void> {
    // Conditional: a session deleted by a sign-out stays deleted.
    await this.db
      .update(sessions)
      .set({ lastActiveAt })
      .where(and(eq(sessions.id, id), lt(sessions.lastActiveAt, lastActiveAt)));
  }

  // Whether this call deleted it: of two rotations of a session, or a rotation and a sign-out, one wins.
  async deleteSession(id: string): Promise<boolean> {
    const deleted = await this.db.delete(sessions).where(eq(sessions.id, id)).returning({ id: sessions.id });
    return deleted.length > 0;
  }

  async listUserSessions(userId: string): Promise<SessionRecord[]> {
    const rows = await this.db.select().from(sessions).where(eq(sessions.userId, userId));
    return rows.map(withoutNulls);
  }

  async deleteUserSessions(userId: string): Promise<void> {
    await this.db.delete(sessions).where(eq(sessions.userId, userId));
  }

  // Refresh tokens

  async getRefreshToken(id: string): Promise<RefreshTokenRecord | undefined> {
    const [row] = await this.db.select().from(refreshTokens).where(eq(refreshTokens.id, id));
    if (!row) {
      return undefined;
    }
    const { revoked: _, ...token } = row;
    return withoutNulls(token);
  }

  async saveRefreshToken(record: RefreshTokenRecord): Promise<void> {
    await this.db.insert(refreshTokens).values(record);
    await this.db.delete(refreshTokens).where(lte(refreshTokens.familyExpiresAt, record.createdAt));
  }

  async markRefreshTokenUsed(id: string, at: Date): Promise<boolean> {
    // Conditional: of two refreshes with the same token, one updates the row.
    const updated = await this.db
      .update(refreshTokens)
      .set({ usedAt: at })
      .where(and(eq(refreshTokens.id, id), isNull(refreshTokens.usedAt)))
      .returning({ id: refreshTokens.id });
    return updated.length === 1;
  }

  async revokeRefreshTokenFamily(familyId: string): Promise<void> {
    await this.db.update(refreshTokens).set({ revoked: true }).where(eq(refreshTokens.familyId, familyId));
  }

  async isRefreshTokenFamilyRevoked(familyId: string): Promise<boolean> {
    const revoked = await this.db
      .select({ id: refreshTokens.id })
      .from(refreshTokens)
      .where(and(eq(refreshTokens.familyId, familyId), eq(refreshTokens.revoked, true)))
      .limit(1);
    return revoked.length > 0;
  }

  async revokeUserRefreshTokens(userId: string): Promise<void> {
    await this.db.update(refreshTokens).set({ revoked: true }).where(eq(refreshTokens.userId, userId));
  }

  // Authenticators, recovery codes and failed attempts

  async getTotp(userId: string): Promise<TotpRecord | undefined> {
    const [row] = await this.db.select().from(mfaAuthenticators).where(eq(mfaAuthenticators.userId, userId));
    if (!row) {
      return undefined;
    }
    const { userId: _, ...totp } = row;
    return withoutNulls(totp);
  }

  async saveTotp(userId: string, record: TotpRecord | null): Promise<void> {
    if (!record) {
      await this.db.delete(mfaAuthenticators).where(eq(mfaAuthenticators.userId, userId));
      return;
    }
    const values = { secret: record.secret, confirmed: record.confirmed, pendingSecret: record.pendingSecret ?? null };
    await this.db
      .insert(mfaAuthenticators)
      .values({ userId, ...values, lastUsedStep: record.lastUsedStep })
      .onConflictDoUpdate({
        target: mfaAuthenticators.userId,
        // Never lower the claimed step: the record may have been read before a claim.
        set: { ...values, lastUsedStep: sql`greatest(${mfaAuthenticators.lastUsedStep}, excluded.last_used_step)` },
      });
  }

  async claimTotpStep(userId: string, step: number): Promise<boolean> {
    // Conditional: a code's time step is accepted once.
    const claimed = await this.db
      .update(mfaAuthenticators)
      .set({ lastUsedStep: step })
      .where(
        and(
          eq(mfaAuthenticators.userId, userId),
          or(isNull(mfaAuthenticators.lastUsedStep), lt(mfaAuthenticators.lastUsedStep, step)),
        ),
      )
      .returning({ userId: mfaAuthenticators.userId });
    return claimed.length === 1;
  }

  async saveRecoveryCodes(userId: string, hashes: string[]): Promise<void> {
    await this.db.transaction(async (tx) => {
      await tx.delete(mfaRecoveryCodes).where(eq(mfaRecoveryCodes.userId, userId));
      if (hashes.length > 0) {
        await tx.insert(mfaRecoveryCodes).values([...new Set(hashes)].map((codeHash) => ({ userId, codeHash })));
      }
    });
  }

  async consumeRecoveryCode(userId: string, hash: string): Promise<boolean> {
    // Conditional: of two requests with the same code, one deletes the row.
    const consumed = await this.db
      .delete(mfaRecoveryCodes)
      .where(and(eq(mfaRecoveryCodes.userId, userId), eq(mfaRecoveryCodes.codeHash, hash)))
      .returning({ userId: mfaRecoveryCodes.userId });
    return consumed.length === 1;
  }

  countRecoveryCodes(userId: string): Promise<number> {
    return this.db.$count(mfaRecoveryCodes, eq(mfaRecoveryCodes.userId, userId));
  }

  async recordMfaFailure(userId: string, windowMs: number, now: number): Promise<number> {
    // Insert, then count, each committed on its own (no transaction): every attempt
    // counts itself and all those recorded before it.
    await this.db.insert(mfaFailures).values({ userId, failedAt: new Date(now) });
    const failures = await this.countMfaFailures(userId, windowMs, now);
    await this.db.delete(mfaFailures).where(lte(mfaFailures.failedAt, new Date(now - windowMs)));
    return failures;
  }

  countMfaFailures(userId: string, windowMs: number, now: number): Promise<number> {
    return this.db.$count(
      mfaFailures,
      and(eq(mfaFailures.userId, userId), gt(mfaFailures.failedAt, new Date(now - windowMs))),
    );
  }

  async clearMfaFailures(userId: string): Promise<void> {
    await this.db.delete(mfaFailures).where(eq(mfaFailures.userId, userId));
  }

  // Magic links

  async saveMagicLink(record: MagicLinkRecord): Promise<void> {
    await this.db.insert(magicLinks).values(record);
    await this.trim(magicLinks, record.createdAt);
  }

  async consumeMagicLink(id: string): Promise<MagicLinkRecord | undefined> {
    // DELETE … RETURNING: of two requests with the same link, one gets the row.
    const [row] = await this.db.delete(magicLinks).where(eq(magicLinks.id, id)).returning();
    return row && withoutNulls(row);
  }

  // Sign-ins with Google in progress

  async saveOidcState({ link, ...login }: OidcTransaction): Promise<void> {
    await this.db.insert(oidcLogins).values({ ...login, linkUserId: link?.userId, linkSessionId: link?.sessionId });
    await this.trim(oidcLogins, login.createdAt);
  }

  async consumeOidcState(state: string): Promise<OidcTransaction | undefined> {
    const [row] = await this.db.delete(oidcLogins).where(eq(oidcLogins.state, state)).returning();
    if (!row) {
      return undefined;
    }
    const { linkUserId, linkSessionId, ...login } = withoutNulls(row);
    return linkUserId && linkSessionId ? { ...login, link: { userId: linkUserId, sessionId: linkSessionId } } : login;
  }

  // Password reset and email verification links

  async saveEmailToken(record: EmailTokenRecord): Promise<void> {
    await this.db.insert(emailTokens).values(record);
    await this.trim(emailTokens, record.createdAt);
  }

  async consumeEmailToken(id: string, purpose: EmailTokenPurpose): Promise<EmailTokenRecord | undefined> {
    const [row] = await this.db
      .delete(emailTokens)
      .where(and(eq(emailTokens.id, id), eq(emailTokens.purpose, purpose)))
      .returning();
    return row && withoutNulls(row);
  }

  async deleteUserEmailTokens(userId: string, purpose: EmailTokenPurpose): Promise<void> {
    await this.db.delete(emailTokens).where(and(eq(emailTokens.userId, userId), eq(emailTokens.purpose, purpose)));
  }

  /** Deletes what expired, and past `maxPending`, what expires first. */
  private async trim(table: typeof magicLinks | typeof oidcLogins | typeof emailTokens, now: Date) {
    await this.db.delete(table).where(lte(table.expiresAt, now));
    const [cutoff] = await this.db
      .select({ expiresAt: table.expiresAt })
      .from(table)
      .orderBy(desc(table.expiresAt))
      .limit(1)
      .offset(this.maxPending);
    if (cutoff) {
      await this.db.delete(table).where(lte(table.expiresAt, cutoff.expiresAt));
    }
  }
}

/** A row without its NULL columns: the package's records leave optional fields out. */
type WithoutNulls<T> = { [K in keyof T as null extends T[K] ? never : K]: T[K] } & {
  [K in keyof T as null extends T[K] ? K : never]?: Exclude<T[K], null>;
};

function withoutNulls<T extends object>(row: T): WithoutNulls<T> {
  return Object.fromEntries(Object.entries(row).filter(([, value]) => value !== null)) as WithoutNulls<T>;
}
```

Thêm nó vào providers của `AuthModule`, giống như các credential provider và handler. Đăng ký trong constructor là đủ: Nest tạo provider lúc khởi động, trước request đầu tiên.

```typescript
@@filename(src/auth/auth.module)
import { DrizzleAuthenticationStore } from './drizzle-authentication.store.js';
// ...
providers: [
  // ...
  MagicLinkMailer,
  DrizzleAuthenticationStore,
],
```

Lúc khởi động, sau chuỗi provider và các handler, module log nơi mỗi loại state được lưu:

```bash
LOG [AuthenticationModule] AuthenticationRegistry: providers SessionAuth, JwtAuth; handlers EmailVerificationMailer (emailVerification), PasswordResetMailer (passwordReset), MagicLinkMailer (magicLink), AccountLinker (oidc)
LOG [AuthenticationModule] AuthenticationStorage: DrizzleAuthenticationStore
```

- **Một provider hay nhiều provider.** `registerSource()` nhận các interface theo tên, nên một class có thể implement cả sáu, như ở đây, hoặc nhiều class có thể chia nhau: một `RedisSessionStore` đăng ký `sessions`, còn class này đăng ký năm cái còn lại. Một store thứ hai cho cùng một tên sẽ lỗi lúc khởi động, kèm tên cả hai class.
- **Một số method phải là một câu lệnh duy nhất.** Bất cứ thứ gì quyết định một việc chỉ được xảy ra một lần đều là một câu lệnh có điều kiện duy nhất, không bao giờ là đọc rồi ghi. `touchSession()` chỉ cập nhật session còn tồn tại, nên một request chạy đua với việc đăng xuất không thể làm session sống lại. `deleteSession()` resolve ra việc nó có xóa dòng dữ liệu hay không, nên giữa hai lần xoay vòng của cùng một session, hoặc một lần xoay vòng và một lần đăng xuất, chỉ đúng một bên thắng. `markRefreshTokenUsed()`, `claimTotpStep()` và `consumeRecoveryCode()` đếm số dòng đã thay đổi, còn ba method `consume` là một câu `DELETE … RETURNING`. `saveTotp()` giữ time step lớn hơn bằng `greatest()`, nơi duy nhất store phải tự viết SQL. `recordMfaFailure()` insert trước rồi đếm sau, bên ngoài transaction, nên một loạt lần đoán song song không thể cùng thấy một con số thấp. Mỗi method của các interface store đều nêu quy tắc của nó, và cuộc đua mà nó ngăn chặn, trong doc comment.
- **Ghi nhận hoạt động là cố gắng hết sức (best-effort).** Nếu `touchSession()` thất bại (lock timeout, replica chỉ đọc), request và việc đăng xuất vẫn thành công. Session được giữ lại, `lastActiveAt` không thay đổi, và session sẽ chuyển sang trạng thái idle ở mốc hạn cũ trừ khi một request sau đó ghi nhận được hoạt động. Mỗi lần thất bại phát ra event `session-touch-failed`; log chỉ nhận một cảnh báo khi các lỗi bắt đầu, không có gì trong khi chúng tiếp diễn, và một dòng kèm số lần lỗi ở lần touch thành công tiếp theo.
- **Các bảng luôn có giới hạn.** Ai cũng có thể xin magic link hay link đặt lại mật khẩu, nên mỗi lần lưu sẽ xóa những gì đã hết hạn, và khi một bảng vượt quá 100.000 dòng đang chờ, xóa những gì hết hạn sớm nhất. Session và family refresh token đã hết hạn sẽ bị xóa khi có cái mới được ghi.
- **Đặt lại mật khẩu và xác minh email vẫn hoạt động y như cũ.** Link của chúng giờ là các dòng trong `email_tokens`, và các mailer của chúng vẫn gửi chúng qua `@nestjs/mail`.
- **Production từ chối dùng bộ nhớ.** Khi `NODE_ENV` đặt thành `production`, module sẽ không khởi động khi một store mà tính năng đã cấu hình cần dùng chưa được đăng ký, và nêu tên các interface cần implement. Mỗi tính năng chỉ cần các store mà nó dùng: `MfaStore` chỉ khi có `mfa`, và `RefreshTokenStore` chỉ khi có `accessToken` trong lúc refresh token được bật. [Hợp đồng của store](/security/authentication#the-store-contract) liệt kê chúng. Một store mà không tính năng đã cấu hình nào dùng sẽ lỗi ở lần đọc đầu tiên. `allowInMemoryStorage: true` trong tùy chọn module vẫn chạy trong bộ nhớ, nhưng khi đó mỗi lần khởi động lại hay deploy sẽ đăng xuất mọi người và quên các authenticator đã đăng ký, và các instance không chia sẻ gì với nhau.

Nếu người dùng của bạn nằm cùng database, `getSession()` có thể đọc người dùng của mỗi session trong cùng một query và truyền nó tiếp dưới dạng `extra`, thứ mà `validate()` của `SessionAuth` nhận được: một lần đọc mỗi request thay vì hai. Gán type cho nó bằng một key `sessionExtra` cạnh `user` (`users` và `toUser()` đại diện cho bảng của riêng bạn và hàm ánh xạ bỏ đi hash mật khẩu):

```typescript
@@filename(src/auth/auth-types)
import type { User } from '../users/user.js';

declare module '@nestjs/authentication' {
  interface AuthenticationTypes {
    user: User;
    sessionExtra: { user: User };
  }
}
```

```typescript
@@filename(src/auth/drizzle-authentication.store)
async getSession(id: string): Promise<SessionRecord | undefined> {
  // Joined fresh on every read. A session whose user is gone reads as unknown.
  const [row] = await this.db
    .select({ session: sessions, user: users })
    .from(sessions)
    .innerJoin(users, eq(users.id, sessions.userId))
    .where(eq(sessions.id, id));
  return row && { ...withoutNulls(row.session), extra: { user: toUser(row.user) } };
}
```

```typescript
@@filename(src/auth/session-auth.provider)
validate(session: SessionRecord) {
  return session.extra?.user ?? null;
}
```

`extra` không bao giờ được lưu: `createSession()` không bao giờ nhận nó, một lần xoay vòng bỏ nó đi, và `listUserSessions()` không nên đặt nó. Nó cũng không bị để lộ: `@CurrentSession()`, `request.session` và `AuthenticationContext.session` mang session mà không kèm nó, nên những gì handler cần phải nằm trong người dùng mà `validate()` trả về. Đừng copy người dùng vào dòng session thay vì join: bản sao sẽ bị cũ khi người dùng thay đổi.

Package cung cấp các quy tắc của nó dưới dạng test. `authenticationStoreContract()` từ `@nestjs/authentication/testing` trả về các test case chạy được với mọi test runner, và `concurrent: true` thêm các cuộc đua: refresh song song cùng một token, dùng song song cùng một mã hoặc link, một loạt mã sai, một lần đăng xuất chạy đua với một request, xóa song song cùng một session, và một lần xoay vòng chạy đua với một lần đăng xuất hoặc một lần xoay vòng khác. Hãy chạy chúng trên PGlite và, nơi các lời gọi thực sự chạy đua, trên PostgreSQL:

```typescript
@@filename(test/drizzle-authentication.store.e2e-spec)
import { fileURLToPath } from 'node:url';
import { PGlite } from '@electric-sql/pglite';
import { AuthenticationStorage } from '@nestjs/authentication';
import { authenticationStoreContract } from '@nestjs/authentication/testing';
import { sql } from 'drizzle-orm';
import { drizzle as nodePostgres, type NodePgDatabase } from 'drizzle-orm/node-postgres';
import { migrate as migrateNodePostgres } from 'drizzle-orm/node-postgres/migrator';
import { drizzle as pglite } from 'drizzle-orm/pglite';
import { migrate as migratePglite } from 'drizzle-orm/pglite/migrator';
import { Pool } from 'pg';
import { DrizzleAuthenticationStore } from '../src/auth/drizzle-authentication.store.js';
import { startPostgres } from './support/postgres.js';

type Database = NodePgDatabase;

const migrationsFolder = fileURLToPath(new URL('../drizzle', import.meta.url));

/** The store with a cap of 3 pending entries per table, so the suite can check it. */
class CappedStore extends DrizzleAuthenticationStore {
  protected override readonly maxPending = 3;
}

/** The store on empty tables, registered nowhere: the suite builds its own registry. */
async function emptyStore(db: Database) {
  await db.execute(
    sql`TRUNCATE sessions, refresh_tokens, mfa_authenticators, mfa_recovery_codes, mfa_failures, magic_links, oidc_logins, email_tokens`,
  );
  const store = new CappedStore(db, new AuthenticationStorage());
  return { sessions: store, refreshTokens: store, mfa: store, magicLinks: store, oidcStates: store, emailTokens: store };
}

describe('DrizzleAuthenticationStore on PGlite', () => {
  const client = new PGlite();
  const db = pglite({ client }) as unknown as Database;
  beforeAll(() => migratePglite(pglite({ client }), { migrationsFolder }));
  afterAll(() => client.close());

  for (const c of authenticationStoreContract(() => emptyStore(db), { concurrent: true, maxPending: 3 })) {
    it(c.name, c.run);
  }
});

// PostgreSQL on a pool of connections: the concurrency cases race for real.
const { postgres, reason } = await startPostgres();

describe.skipIf(!postgres)(`DrizzleAuthenticationStore on PostgreSQL${reason ? ` (skipped: ${reason})` : ''}`, () => {
  let pool: Pool;
  let db: Database;
  beforeAll(async () => {
    pool = new Pool({ connectionString: await postgres!.createDatabase('authentication_tutorial_store'), max: 10 });
    db = nodePostgres({ client: pool });
    await migrateNodePostgres(db, { migrationsFolder });
  });
  afterAll(async () => {
    await pool?.end();
    postgres!.stop();
  });

  for (const c of authenticationStoreContract(() => emptyStore(db), { concurrent: true, maxPending: 3 })) {
    it(c.name, c.run);
  }
});
```

`CappedStore` hạ mức trần số dòng đang chờ để `maxPending: 3` kiểm tra được nó. `startPostgres()` là một test helper tạo một database dùng một lần trên PostgreSQL server, hoặc bỏ qua các case PostgreSQL nếu không có server. Một store đọc một dòng rồi ghi ngược lại sẽ qua được các test khác nhưng thất bại ở những test này.

**Với TypeORM.** Cùng store đó cho một ứng dụng dùng ORM là TypeORM, trên cùng tám bảng. Drizzle vẫn là hướng chính của bài hướng dẫn: hãy dùng store này thay cho store ở trên, không phải dùng song song. Các bảng là entity, và mọi cột đều khai báo type của nó, để TypeORM CLI, vốn load chúng mà không có decorator metadata, thấy cùng một schema như ứng dụng:

```typescript
@@filename(src/typeorm/authentication.entities)
import type { EmailTokenPurpose, MfaState } from '@nestjs/authentication';
import { Column, Entity, Index, PrimaryColumn, PrimaryGeneratedColumn } from 'typeorm';

// The authentication tables, read and written by TypeOrmAuthenticationStore: the same
// tables as the Drizzle schema in src/database/schema.ts. Every column states its type, so
// the entities load the same with or without emitted decorator metadata (the TypeORM CLI
// runs them through tsx, which emits none). Tokens, links and sessions are stored by their
// SHA-256; TOTP secrets arrive encrypted.

/** What a `jsonb` column holds: a column typed `unknown` doesn't fit TypeORM's insert types. */
export type Json = object | string | number | boolean | null;

@Entity('sessions')
@Index('sessions_user_id_idx', ['userId'])
@Index('sessions_expires_at_idx', ['expiresAt'])
export class SessionEntity {
  @PrimaryColumn({ type: 'text' })
  id: string;

  @Column({ type: 'text', name: 'user_id' })
  userId: string;

  @Column({ type: 'timestamptz', name: 'created_at' })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'expires_at' })
  expiresAt: Date;

  @Column({ type: 'timestamptz', name: 'last_active_at' })
  lastActiveAt: Date;

  @Column({ type: 'text', nullable: true })
  mfa: MfaState | null;

  @Column({ type: 'jsonb', nullable: true })
  metadata: Record<string, Json> | null;
}

@Entity('refresh_tokens')
@Index('refresh_tokens_family_id_idx', ['familyId'])
@Index('refresh_tokens_user_id_idx', ['userId'])
@Index('refresh_tokens_family_expires_at_idx', ['familyExpiresAt'])
export class RefreshTokenEntity {
  @PrimaryColumn({ type: 'text' })
  id: string;

  @Column({ type: 'text', name: 'family_id' })
  familyId: string;

  @Column({ type: 'text', name: 'user_id' })
  userId: string;

  @Column({ type: 'timestamptz', name: 'created_at' })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'expires_at' })
  expiresAt: Date;

  @Column({ type: 'timestamptz', name: 'family_expires_at' })
  familyExpiresAt: Date;

  @Column({ type: 'timestamptz', name: 'used_at', nullable: true })
  usedAt: Date | null;

  // A family is revoked when any of its tokens is: that covers a successor saved after the revocation.
  @Column({ type: 'boolean', default: false })
  revoked: boolean;

  @Column({ type: 'jsonb', nullable: true })
  claims: Record<string, Json> | null;
}

@Entity('mfa_authenticators')
export class MfaAuthenticatorEntity {
  @PrimaryColumn({ type: 'text', name: 'user_id' })
  userId: string;

  @Column({ type: 'text' })
  secret: string;

  @Column({ type: 'boolean' })
  confirmed: boolean;

  @Column({ type: 'text', name: 'pending_secret', nullable: true })
  pendingSecret: string | null;

  @Column({ type: 'integer', name: 'last_used_step', nullable: true })
  lastUsedStep: number | null;
}

@Entity('mfa_recovery_codes')
export class MfaRecoveryCodeEntity {
  @PrimaryColumn({ type: 'text', name: 'user_id' })
  userId: string;

  @PrimaryColumn({ type: 'text', name: 'code_hash' })
  codeHash: string;
}

@Entity('mfa_failures')
@Index('mfa_failures_user_id_failed_at_idx', ['userId', 'failedAt'])
@Index('mfa_failures_failed_at_idx', ['failedAt'])
export class MfaFailureEntity {
  @PrimaryGeneratedColumn('identity', { type: 'integer', generatedIdentity: 'ALWAYS' })
  id: number;

  @Column({ type: 'text', name: 'user_id' })
  userId: string;

  @Column({ type: 'timestamptz', name: 'failed_at' })
  failedAt: Date;
}

@Entity('magic_links')
@Index('magic_links_expires_at_idx', ['expiresAt'])
export class MagicLinkEntity {
  @PrimaryColumn({ type: 'text' })
  id: string;

  @Column({ type: 'text' })
  email: string;

  @Column({ type: 'timestamptz', name: 'created_at' })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'expires_at' })
  expiresAt: Date;

  @Column({ type: 'text', name: 'redirect_to', nullable: true })
  redirectTo: string | null;
}

@Entity('oidc_logins')
@Index('oidc_logins_expires_at_idx', ['expiresAt'])
export class OidcLoginEntity {
  @PrimaryColumn({ type: 'text' })
  state: string;

  @Column({ type: 'text' })
  provider: string;

  @Column({ type: 'text', name: 'code_verifier' })
  codeVerifier: string;

  @Column({ type: 'text', nullable: true })
  nonce: string | null;

  @Column({ type: 'text', name: 'redirect_to', nullable: true })
  redirectTo: string | null;

  // Set for "connect your Google account" from a signed-in session.
  @Column({ type: 'text', name: 'link_user_id', nullable: true })
  linkUserId: string | null;

  @Column({ type: 'text', name: 'link_session_id', nullable: true })
  linkSessionId: string | null;

  @Column({ type: 'timestamptz', name: 'created_at' })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'expires_at' })
  expiresAt: Date;
}

@Entity('email_tokens')
@Index('email_tokens_user_id_purpose_idx', ['userId', 'purpose'])
@Index('email_tokens_expires_at_idx', ['expiresAt'])
export class EmailTokenEntity {
  @PrimaryColumn({ type: 'text' })
  id: string;

  @Column({ type: 'text' })
  purpose: EmailTokenPurpose;

  @Column({ type: 'text', name: 'user_id' })
  userId: string;

  @Column({ type: 'text' })
  email: string;

  @Column({ type: 'text', nullable: true })
  fingerprint: string | null;

  @Column({ type: 'timestamptz', name: 'created_at' })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'expires_at' })
  expiresAt: Date;
}
```

TypeORM CLI và `TypeOrmModule` dùng chung một bộ tùy chọn, trong một file data source:

```typescript
@@filename(src/typeorm/data-source)
import { DataSource, type DataSourceOptions } from 'typeorm';
import {
  EmailTokenEntity,
  MagicLinkEntity,
  MfaAuthenticatorEntity,
  MfaFailureEntity,
  MfaRecoveryCodeEntity,
  OidcLoginEntity,
  RefreshTokenEntity,
  SessionEntity,
} from './authentication.entities.js';
import { Authentication1790235914534 } from './migrations/1790235914534-Authentication.js';

/** What the application's TypeOrmModule and the TypeORM CLI share. */
export const dataSourceOptions = {
  type: 'postgres',
  url: process.env.DATABASE_URL,
  entities: [
    SessionEntity,
    RefreshTokenEntity,
    MfaAuthenticatorEntity,
    MfaRecoveryCodeEntity,
    MfaFailureEntity,
    MagicLinkEntity,
    OidcLoginEntity,
    EmailTokenEntity,
  ],
  migrations: [Authentication1790235914534],
} satisfies DataSourceOptions;

// The TypeORM CLI's data source: `migration:generate` compares the entities with this database.
export default new DataSource(dataSourceOptions);
```

Sinh migration từ các entity, trên một database đã áp dụng các migration trước đó, áp dụng nó, và kiểm tra entity và database có khớp nhau không. CLI cần một TypeScript loader cho file data source; ở đây dùng `tsx`:

```bash
$ npx tsx ./node_modules/typeorm/cli.js migration:generate src/typeorm/migrations/Authentication -d src/typeorm/data-source.ts --pretty
Migration /store/src/typeorm/migrations/1790235914534-Authentication.ts has been generated successfully.
$ npx tsx ./node_modules/typeorm/cli.js migration:run -d src/typeorm/data-source.ts
$ npx tsx ./node_modules/typeorm/cli.js migration:generate src/typeorm/migrations/Check -d src/typeorm/data-source.ts --check
No changes in database schema were found
```

Migration mà nó viết ra, `1790235914534-Authentication.ts`, gồm các câu lệnh `CREATE TABLE` và `CREATE INDEX` cho tám bảng ở trên, và `migrations` trong data source liệt kê nó. Giờ là store, theo cùng quy tắc như store Drizzle:

```typescript
@@filename(src/typeorm/typeorm-authentication.store)
import { Injectable } from '@nestjs/common';
import {
  AuthenticationStorage,
  type EmailTokenPurpose,
  type EmailTokenRecord,
  type EmailTokenStore,
  type MagicLinkRecord,
  type MagicLinkStore,
  type MfaStore,
  type OidcStateStore,
  type OidcTransaction,
  type RefreshTokenRecord,
  type RefreshTokenStore,
  type SessionRecord,
  type SessionStore,
  type TotpRecord,
} from '@nestjs/authentication';
import {
  DataSource,
  IsNull,
  LessThan,
  LessThanOrEqual,
  MoreThan,
  Or,
  type EntityTarget,
  type FindOptionsWhere,
  type ObjectLiteral,
} from 'typeorm';
import {
  EmailTokenEntity,
  MagicLinkEntity,
  MfaAuthenticatorEntity,
  MfaFailureEntity,
  MfaRecoveryCodeEntity,
  OidcLoginEntity,
  RefreshTokenEntity,
  SessionEntity,
  type Json,
} from './authentication.entities.js';

/**
 * Keeps sessions, refresh tokens, authenticators and pending links in
 * PostgreSQL, through TypeORM: the Drizzle store above, on the same
 * tables. Every method that decides whether something works once is a
 * single conditional statement, so the guarantees hold with any number of
 * API instances.
 */
@Injectable()
export class TypeOrmAuthenticationStore
  implements SessionStore, RefreshTokenStore, MfaStore, MagicLinkStore, OidcStateStore, EmailTokenStore
{
  /** Pending links and logins kept per table: anyone can create them. */
  protected readonly maxPending: number = 100_000;

  constructor(
    private readonly dataSource: DataSource,
    storage: AuthenticationStorage,
  ) {
    storage.registerSource({
      sessions: this,
      refreshTokens: this,
      mfa: this,
      magicLinks: this,
      oidcStates: this,
      emailTokens: this,
    });
  }

  private get manager() {
    return this.dataSource.manager;
  }

  // Sessions

  async getSession(id: string): Promise<SessionRecord | undefined> {
    const row = await this.manager.findOneBy(SessionEntity, { id });
    return row ? withoutNulls(row) : undefined;
  }

  async createSession(record: SessionRecord): Promise<void> {
    // JSON-safe: the package stores what `session.metadata` returned, as JSON.
    const metadata = (record.metadata ?? null) as Record<string, Json> | null;
    await this.manager.insert(SessionEntity, { ...record, mfa: record.mfa ?? null, metadata });
    await this.manager.delete(SessionEntity, { expiresAt: LessThanOrEqual(record.createdAt) });
  }

  async touchSession(id: string, lastActiveAt: Date): Promise<void> {
    // Conditional: a session deleted by a sign-out stays deleted.
    await this.manager.update(SessionEntity, { id, lastActiveAt: LessThan(lastActiveAt) }, { lastActiveAt });
  }

  // Whether this call deleted it: of two rotations of a session, or a rotation and a sign-out, one wins.
  async deleteSession(id: string): Promise<boolean> {
    const { affected } = await this.manager.delete(SessionEntity, { id });
    return (affected ?? 0) > 0;
  }

  async listUserSessions(userId: string): Promise<SessionRecord[]> {
    const rows = await this.manager.findBy(SessionEntity, { userId });
    return rows.map(withoutNulls);
  }

  async deleteUserSessions(userId: string): Promise<void> {
    await this.manager.delete(SessionEntity, { userId });
  }

  // Refresh tokens

  async getRefreshToken(id: string): Promise<RefreshTokenRecord | undefined> {
    const row = await this.manager.findOneBy(RefreshTokenEntity, { id });
    if (!row) {
      return undefined;
    }
    const { revoked: _, ...token } = row;
    return withoutNulls(token);
  }

  async saveRefreshToken(record: RefreshTokenRecord): Promise<void> {
    const claims = (record.claims ?? null) as Record<string, Json> | null;
    await this.manager.insert(RefreshTokenEntity, { ...record, usedAt: record.usedAt ?? null, claims });
    await this.manager.delete(RefreshTokenEntity, { familyExpiresAt: LessThanOrEqual(record.createdAt) });
  }

  async markRefreshTokenUsed(id: string, at: Date): Promise<boolean> {
    // Conditional: of two refreshes with the same token, one updates the row.
    const { affected } = await this.manager.update(RefreshTokenEntity, { id, usedAt: IsNull() }, { usedAt: at });
    return affected === 1;
  }

  async revokeRefreshTokenFamily(familyId: string): Promise<void> {
    await this.manager.update(RefreshTokenEntity, { familyId }, { revoked: true });
  }

  isRefreshTokenFamilyRevoked(familyId: string): Promise<boolean> {
    return this.manager.existsBy(RefreshTokenEntity, { familyId, revoked: true });
  }

  async revokeUserRefreshTokens(userId: string): Promise<void> {
    await this.manager.update(RefreshTokenEntity, { userId }, { revoked: true });
  }

  // Authenticators, recovery codes and failed attempts

  async getTotp(userId: string): Promise<TotpRecord | undefined> {
    const row = await this.manager.findOneBy(MfaAuthenticatorEntity, { userId });
    if (!row) {
      return undefined;
    }
    const { userId: _, ...totp } = row;
    return withoutNulls(totp);
  }

  async saveTotp(userId: string, record: TotpRecord | null): Promise<void> {
    if (!record) {
      await this.manager.delete(MfaAuthenticatorEntity, { userId });
      return;
    }
    // An upsert that never lowers the claimed step: the record may have been read before a
    // claim. GREATEST() over the conflicting row is beyond the upsert API, so this one is SQL.
    await this.manager.query(
      `INSERT INTO mfa_authenticators (user_id, secret, confirmed, pending_secret, last_used_step)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (user_id) DO UPDATE SET
         secret = EXCLUDED.secret,
         confirmed = EXCLUDED.confirmed,
         pending_secret = EXCLUDED.pending_secret,
         last_used_step = GREATEST(mfa_authenticators.last_used_step, EXCLUDED.last_used_step)`,
      [userId, record.secret, record.confirmed, record.pendingSecret ?? null, record.lastUsedStep ?? null],
    );
  }

  async claimTotpStep(userId: string, step: number): Promise<boolean> {
    // Conditional: a code's time step is accepted once.
    const { affected } = await this.manager.update(
      MfaAuthenticatorEntity,
      { userId, lastUsedStep: Or(IsNull(), LessThan(step)) },
      { lastUsedStep: step },
    );
    return affected === 1;
  }

  async saveRecoveryCodes(userId: string, hashes: string[]): Promise<void> {
    await this.dataSource.transaction(async (manager) => {
      await manager.delete(MfaRecoveryCodeEntity, { userId });
      if (hashes.length > 0) {
        await manager.insert(MfaRecoveryCodeEntity, [...new Set(hashes)].map((codeHash) => ({ userId, codeHash })));
      }
    });
  }

  async consumeRecoveryCode(userId: string, hash: string): Promise<boolean> {
    // Conditional: of two requests with the same code, one deletes the row.
    const { affected } = await this.manager.delete(MfaRecoveryCodeEntity, { userId, codeHash: hash });
    return affected === 1;
  }

  countRecoveryCodes(userId: string): Promise<number> {
    return this.manager.countBy(MfaRecoveryCodeEntity, { userId });
  }

  async recordMfaFailure(userId: string, windowMs: number, now: number): Promise<number> {
    // Insert, then count, each committed on its own (no transaction): every attempt
    // counts itself and all those recorded before it.
    await this.manager.insert(MfaFailureEntity, { userId, failedAt: new Date(now) });
    const failures = await this.countMfaFailures(userId, windowMs, now);
    await this.manager.delete(MfaFailureEntity, { failedAt: LessThanOrEqual(new Date(now - windowMs)) });
    return failures;
  }

  countMfaFailures(userId: string, windowMs: number, now: number): Promise<number> {
    return this.manager.countBy(MfaFailureEntity, { userId, failedAt: MoreThan(new Date(now - windowMs)) });
  }

  async clearMfaFailures(userId: string): Promise<void> {
    await this.manager.delete(MfaFailureEntity, { userId });
  }

  // Magic links

  async saveMagicLink(record: MagicLinkRecord): Promise<void> {
    await this.manager.insert(MagicLinkEntity, { ...record, redirectTo: record.redirectTo ?? null });
    await this.trim(MagicLinkEntity, record.createdAt);
  }

  async consumeMagicLink(id: string): Promise<MagicLinkRecord | undefined> {
    // DELETE … RETURNING: of two requests with the same link, one gets the row.
    const [row] = await this.deleteReturning(MagicLinkEntity, { id });
    return row && withoutNulls(row);
  }

  // Sign-ins with Google in progress

  async saveOidcState({ link, ...login }: OidcTransaction): Promise<void> {
    await this.manager.insert(OidcLoginEntity, {
      ...login,
      nonce: login.nonce ?? null,
      redirectTo: login.redirectTo ?? null,
      linkUserId: link?.userId ?? null,
      linkSessionId: link?.sessionId ?? null,
    });
    await this.trim(OidcLoginEntity, login.createdAt);
  }

  async consumeOidcState(state: string): Promise<OidcTransaction | undefined> {
    const [row] = await this.deleteReturning(OidcLoginEntity, { state });
    if (!row) {
      return undefined;
    }
    const { linkUserId, linkSessionId, ...login } = withoutNulls(row);
    return linkUserId && linkSessionId ? { ...login, link: { userId: linkUserId, sessionId: linkSessionId } } : login;
  }

  // Password reset and email verification links

  async saveEmailToken(record: EmailTokenRecord): Promise<void> {
    await this.manager.insert(EmailTokenEntity, { ...record, fingerprint: record.fingerprint ?? null });
    await this.trim(EmailTokenEntity, record.createdAt);
  }

  async consumeEmailToken(id: string, purpose: EmailTokenPurpose): Promise<EmailTokenRecord | undefined> {
    const [row] = await this.deleteReturning(EmailTokenEntity, { id, purpose });
    return row && withoutNulls(row);
  }

  async deleteUserEmailTokens(userId: string, purpose: EmailTokenPurpose): Promise<void> {
    await this.manager.delete(EmailTokenEntity, { userId, purpose });
  }

  /** `DELETE … RETURNING *`, as rows of the entity: the query builder returns raw column names. */
  private async deleteReturning<T extends ObjectLiteral>(entity: EntityTarget<T>, where: FindOptionsWhere<T>): Promise<T[]> {
    const { raw } = await this.manager.createQueryBuilder().delete().from(entity).where(where).returning('*').execute();
    const columns = this.dataSource.getMetadata(entity).columns;
    return (raw as Record<string, unknown>[]).map(
      (row) => Object.fromEntries(columns.map((column) => [column.propertyName, row[column.databaseName]])) as T,
    );
  }

  /** Deletes what expired, and past `maxPending`, what expires first. */
  private async trim<T extends { expiresAt: Date }>(entity: EntityTarget<T>, now: Date) {
    await this.manager.delete(entity, { expiresAt: LessThanOrEqual(now) } as FindOptionsWhere<T>);
    const [cutoff] = await this.manager.find(entity, {
      select: { expiresAt: true } as never,
      order: { expiresAt: 'DESC' } as never,
      skip: this.maxPending,
      take: 1,
    });
    if (cutoff) {
      await this.manager.delete(entity, { expiresAt: LessThanOrEqual(cutoff.expiresAt) } as FindOptionsWhere<T>);
    }
  }
}

/** A row without its NULL columns: the package's records leave optional fields out. */
type WithoutNulls<T> = { [K in keyof T as null extends T[K] ? never : K]: T[K] } & {
  [K in keyof T as null extends T[K] ? K : never]?: Exclude<T[K], null>;
};

function withoutNulls<T extends object>(row: T): WithoutNulls<T> {
  return Object.fromEntries(Object.entries(row).filter(([, value]) => value !== null)) as WithoutNulls<T>;
}
```

- **Update và delete có điều kiện** đặt điều kiện trong tiêu chí của `update()` và `delete()`, với `LessThan()`, `IsNull()` và `Or()`, và đọc `affected`. Đừng bao giờ dùng `save()`: nó sẽ ghi ngược lại một session mà một lần đăng xuất vừa xóa.
- **`saveTotp()`** giữ time step lớn hơn bằng `GREATEST()` trên dòng bị xung đột, điều mà API upsert không biểu diễn được, nên đây là câu lệnh duy nhất được viết bằng SQL, qua `manager.query()`.
- **Các method `consume`** là delete query builder với `returning('*')`. Nó trả về các dòng thô theo tên cột của database, nên `deleteReturning()` ánh xạ chúng ngược lại thành các thuộc tính entity thông qua entity metadata.
- **`recordMfaFailure()`** là hai câu lệnh trên `dataSource.manager`, mỗi câu được commit riêng, còn `saveRecoveryCodes()` là method duy nhất nằm trong `dataSource.transaction()`.
- **Dùng nó** thay cho store Drizzle: `TypeOrmModule.forRoot(dataSourceOptions)` trong `AppModule` thay cho `DrizzleModule`, và `TypeOrmAuthenticationStore` trong providers của `AuthModule` thay cho `DrizzleAuthenticationStore`. Nó inject `DataSource` mà `TypeOrmModule` cung cấp.

Bộ test hợp đồng chạy trên nó mà không cần sửa gì. TypeORM kết nối qua `pg`, nên bộ test cần một PostgreSQL server và sẽ bị bỏ qua nếu không có. Hai case bổ sung kiểm tra entity và migration có khớp nhau không (thứ mà `migration:generate --check` kiểm tra), và store có đăng ký cho cả sáu hợp đồng khi được cung cấp trong một module hay không:

```typescript
@@filename(test/typeorm-authentication.store.e2e-spec)
/**
 * TypeOrmAuthenticationStore against the package's contract suite
 * (`@nestjs/authentication/testing`), on PostgreSQL (the server in
 * SQL_TEST_PG_URL, else a throwaway local cluster; see test/support/postgres.ts),
 * with the migration the TypeORM CLI generated. A pool, so the concurrency
 * cases race for real. Skipped, with the reason, without a server.
 */
import { Logger } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { AuthenticationModule, AuthenticationStorage } from '@nestjs/authentication';
import { authenticationStoreContract } from '@nestjs/authentication/testing';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';
import { dataSourceOptions } from '../src/typeorm/data-source.js';
import { TypeOrmAuthenticationStore } from '../src/typeorm/typeorm-authentication.store.js';
import { startPostgres } from './support/postgres.js';

/** The store with a cap of 3 pending entries per table, so the suite can check it. */
class CappedStore extends TypeOrmAuthenticationStore {
  protected override readonly maxPending = 3;
}

const { postgres, reason } = await startPostgres();

describe.skipIf(!postgres)(`TypeOrmAuthenticationStore on PostgreSQL${reason ? ` (skipped: ${reason})` : ''}`, () => {
  let dataSource: DataSource;
  let url: string;

  beforeAll(async () => {
    url = await postgres!.createDatabase('authentication_tutorial_typeorm_store');
    dataSource = await new DataSource({ ...dataSourceOptions, url, poolSize: 10 }).initialize();
    await dataSource.runMigrations();
  });
  afterAll(async () => {
    await dataSource?.destroy();
    postgres!.stop();
  });

  /** The store on empty tables, registered nowhere: the suite builds its own registry. */
  async function emptyStore() {
    await dataSource.query(
      'TRUNCATE sessions, refresh_tokens, mfa_authenticators, mfa_recovery_codes, mfa_failures, magic_links, oidc_logins, email_tokens',
    );
    const store = new CappedStore(dataSource, new AuthenticationStorage());
    return { sessions: store, refreshTokens: store, mfa: store, magicLinks: store, oidcStates: store, emailTokens: store };
  }

  for (const c of authenticationStoreContract(emptyStore, { concurrent: true, maxPending: 3 })) {
    it(c.name, c.run);
  }

  it('has a migration that matches the entities (what `migration:generate --check` checks)', async () => {
    const { upQueries } = await dataSource.driver.createSchemaBuilder().log();
    expect(upQueries.map((query) => query.query)).toEqual([]);
  });

  it('registers itself for every contract when provided in a module', async () => {
    const log = vi.spyOn(Logger.prototype, 'log');
    const app = await Test.createTestingModule({
      imports: [TypeOrmModule.forRoot({ ...dataSourceOptions, url }), AuthenticationModule.forRoot()],
      providers: [TypeOrmAuthenticationStore],
    }).compile();
    await app.init();
    const storage = app.get(AuthenticationStorage);
    const store = app.get(TypeOrmAuthenticationStore);
    expect([storage.sessions, storage.refreshTokens, storage.mfa, storage.magicLinks, storage.oidcStates, storage.emailTokens]).toEqual(
      Array(6).fill(store),
    );
    expect(log).toHaveBeenCalledWith('AuthenticationStorage: TypeOrmAuthenticationStore');
    log.mockRestore();
    await app.close();
  });
});
```

> info **Gợi ý** Dùng Prisma? [Hợp đồng của store](/security/authentication#the-store-contract), nằm sau bài hướng dẫn, liệt kê những gì mỗi hợp đồng phải đảm bảo và cách Prisma biểu diễn các method nguyên tử. Hãy test store của bạn với cùng các case đó.

#### Cấp API key cho đối tác <a id="issue-api-keys-to-partners"></a>

Các trại cứu trợ mèo và cửa hàng thú cưng nhập hàng số lượng lớn từ hệ thống quản lý kho của họ, và một số khách hàng đặt hàng lại bằng script. Một script không thể điền vào form đăng nhập, và một refresh token thay đổi sau mỗi lần dùng không hợp với một job chạy hằng đêm. Thay vào đó, hãy cấp cho họ API key: các secret dài hạn mà khách hàng tạo trong web app và thu hồi khi không cần nữa. Script gửi key của nó dưới dạng bearer token, và hoạt động với tư cách khách hàng đã tạo ra nó.

Package kiểm tra các key, còn database của bạn lưu giữ chúng. Thêm một bảng vào schema:

```typescript
@@filename(src/database/schema)
// API keys (src/auth/api-key-auth.provider.ts): the SHA-256 of each key, never the key.
export const apiKeys = pgTable(
  'api_keys',
  {
    id: text('id').primaryKey(),
    userId: text('user_id').notNull(),
    hash: text('hash').notNull(),
    createdAt: at('created_at').notNull(),
    expiresAt: at('expires_at').notNull(),
  },
  (table) => [index('api_keys_user_id_idx').on(table.userId)],
);
```

Sinh migration cho nó, và áp dụng (output đã được rút gọn):

```bash
$ npx drizzle-kit generate --name=api_keys
...
9 tables
api_keys 5 columns 1 indexes 0 fks
...
[✓] Your SQL migration file ➜ drizzle/0001_api_keys.sql 🚀
$ npx drizzle-kit migrate
...
[✓] migrations applied successfully!
```

Credential provider thứ ba kế thừa `ApiKeyProvider`, và chỉ làm một việc: tìm key theo id của nó.

```typescript
@@filename(src/auth/api-key-auth.provider)
import { Injectable } from '@nestjs/common';
import { ApiKeyProvider, AuthenticationRegistry } from '@nestjs/authentication';
import { InjectDrizzle } from '@nestjs/drizzle';
import { eq } from 'drizzle-orm';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';
import { apiKeys } from '../database/schema.js';
import type { User } from '../users/user.js';
import { UsersRepository } from '../users/users.repository.js';

@Injectable()
export class ApiKeyAuth extends ApiKeyProvider<User> {
  constructor(
    @InjectDrizzle() private readonly db: NodePgDatabase,
    private readonly usersRepository: UsersRepository,
    registry: AuthenticationRegistry,
  ) {
    // Keys look like cat_<id>_<secret>. The prefix tells secret scanners what they found.
    super({ prefix: 'cat', realm: 'store' });
    // Third in the chain, after SessionAuth and JwtAuth.
    registry.registerProvider(this, { order: 2 });
  }

  // Called with the id part of a key; the provider then checks the hash and the expiry.
  // Returning null (no such key, or its owner was deleted) rejects the key.
  async findKey(id: string) {
    const [key] = await this.db.select().from(apiKeys).where(eq(apiKeys.id, id));
    const user = key && (await this.usersRepository.findById(key.userId));
    return user ? { hash: key.hash, user, expiresAt: key.expiresAt } : null;
  }
}
```

Một key có dạng `cat_<id>_<secret>`: prefix, một id công khai gồm 16 ký tự hex, và một secret gồm 256 bit ngẫu nhiên. `findKey()` tra cứu id, còn provider lo phần còn lại. Nó so sánh SHA-256 của toàn bộ key với `hash` đã lưu, trong thời gian không đổi và với cùng khối lượng công việc cho một id không tồn tại, và từ chối key kể từ thời điểm `expiresAt`. Một hàm hash chậm như scrypt của mật khẩu sẽ không thêm được gì ở đây, vì không ai đoán được 256 bit ngẫu nhiên, và nó sẽ làm chậm mọi request. Một key sai, đã hết hạn hoặc bị thu hồi sẽ nhận lỗi 401 với `error="invalid_token"`, giống như một access token không hợp lệ.

`JwtAuth` đọc cùng header `Authorization`. Một JWT luôn chứa hai dấu chấm còn một key thì không có dấu nào, nên `JwtAuth` để các key cho `ApiKeyAuth`, bất kể cái nào chạy trước. Một request không có thông tin xác thực vẫn chỉ nhận một challenge duy nhất, `Bearer realm="store"`, vì cả hai provider dùng chung realm.

Giờ là các endpoint tạo, liệt kê và thu hồi key:

```typescript
@@filename(src/auth/api-keys.controller)
import { Controller, Delete, Get, HttpCode, NotFoundException, Param, Post } from '@nestjs/common';
import { Authenticate, CurrentUser } from '@nestjs/authentication';
import { InjectDrizzle } from '@nestjs/drizzle';
import { and, eq } from 'drizzle-orm';
import type { NodePgDatabase } from 'drizzle-orm/node-postgres';
import { apiKeys } from '../database/schema.js';
import { ApiKeyAuth } from './api-key-auth.provider.js';
import { SessionAuth } from './session-auth.provider.js';

const ONE_YEAR = 365 * 24 * 60 * 60 * 1000;

// Managed from the web app, signed in with a session: a key can't create or revoke keys.
@Authenticate({ providers: [SessionAuth] })
@Controller('auth/api-keys')
export class ApiKeysController {
  constructor(
    @InjectDrizzle() private readonly db: NodePgDatabase,
    private readonly apiKeyAuth: ApiKeyAuth,
  ) {}

  // The only response that contains the key: the table keeps its hash.
  @Post()
  async create(@CurrentUser('id') userId: string) {
    const { key, id, hash } = this.apiKeyAuth.generate();
    const createdAt = new Date();
    const expiresAt = new Date(createdAt.getTime() + ONE_YEAR);
    await this.db.insert(apiKeys).values({ id, userId, hash, createdAt, expiresAt });
    return { id, key, createdAt, expiresAt };
  }

  @Get()
  list(@CurrentUser('id') userId: string) {
    return this.db
      .select({ id: apiKeys.id, createdAt: apiKeys.createdAt, expiresAt: apiKeys.expiresAt })
      .from(apiKeys)
      .where(eq(apiKeys.userId, userId));
  }

  // Revoked from the next request on. Another customer's key is a 404.
  @Delete(':id')
  @HttpCode(204)
  async revoke(@CurrentUser('id') userId: string, @Param('id') id: string) {
    const revoked = await this.db
      .delete(apiKeys)
      .where(and(eq(apiKeys.id, id), eq(apiKeys.userId, userId)))
      .returning();
    if (revoked.length === 0) {
      throw new NotFoundException();
    }
  }
}
```

- `generate()` trả về key, id và hash của nó. Bảng lưu id và hash, nên `create` là lần duy nhất ai đó nhìn thấy key. Một khách hàng làm mất key thì thu hồi nó và tạo key khác.
- Controller chỉ chấp nhận `SessionAuth`, nên key được quản lý từ web app. Dưới `providers`, thông tin xác thực của mọi provider khác đều được tính như không có: một key bị lộ không thể tạo thêm key, hay thu hồi key của chủ sở hữu nó.
- Key hết hạn sau một năm, để một key bị quên không dùng được mãi mãi. Xóa dòng dữ liệu của một key sẽ thu hồi nó kể từ request tiếp theo.

Đăng ký cả hai trong `AuthModule`:

```typescript
@@filename(src/auth/auth.module)
import { ApiKeyAuth } from './api-key-auth.provider.js';
import { ApiKeysController } from './api-keys.controller.js';
// ...
controllers: [
  // ...
  SessionsController,
  ApiKeysController,
],
providers: [
  // ...
  DrizzleAuthenticationStore,
  ApiKeyAuth,
],
```

Một key đăng nhập chủ sở hữu của nó trên mọi route không chỉ định provider, kể cả `POST /orders`. Nó không bao giờ được tính là yếu tố thứ hai: `PATCH /me/email` trả lời nó bằng `mfa_required`, giống như trả lời một session chưa qua bước nhập mã. Để giới hạn một route chỉ cho key, hoặc chặn key khỏi route đó, hãy liệt kê các provider mà route chấp nhận trong `@Authenticate()`. Trong một handler, `@CurrentSession()` chứa `keyId` của key, với `method` đặt là `api-key`, nên một audit log có thể cho biết key nào đã đặt một đơn hàng. Những key chỉ được đọc, hoặc chỉ được đặt hàng, là vấn đề phân quyền, và đó là việc của [`@nestjs/authorization`](/security/authorization).

**Với TypeORM.** Bảng là một entity, nằm cạnh các entity của store:

```typescript
@@filename(src/typeorm/api-key.entity)
import { Column, Entity, Index, PrimaryColumn } from 'typeorm';

// The api_keys table of src/database/schema.ts, for an application on TypeORM.
@Entity('api_keys')
@Index('api_keys_user_id_idx', ['userId'])
export class ApiKeyEntity {
  @PrimaryColumn({ type: 'text' })
  id: string;

  @Column({ type: 'text', name: 'user_id' })
  userId: string;

  @Column({ type: 'text' })
  hash: string;

  @Column({ type: 'timestamptz', name: 'created_at' })
  createdAt: Date;

  @Column({ type: 'timestamptz', name: 'expires_at' })
  expiresAt: Date;
}
```

Liệt kê nó trong `entities` của data source, và migration của nó, được sinh ra giống như các bảng của store, trong `migrations`. `findKey()` đọc dòng dữ liệu qua repository của entity, bằng `findOneBy()`, còn controller ghi nó bằng `insert()` và `delete()`.

#### Thử ngay <a id="try-it"></a>

Áp dụng các [migration](/security/authentication#keep-sessions-and-tokens-in-your-database), và khởi động ứng dụng với file `.env` từ các phần trước:

```bash
$ npm run start:dev -- --env-file .env
```

Trong một terminal khác, hãy đăng ký. Flag `-c` lưu session cookie vào một file, còn `-b` gửi nó kèm các request sau. `--json` (curl 7.82 trở lên) gửi một `POST` với body JSON. Header của response được rút gọn ở đây và bên dưới:

```bash
$ curl -i localhost:3000/auth/sign-up -c ada.txt --json '{"email":"ada@example.com","password":"correct horse battery"}'
HTTP/1.1 201 Created
Set-Cookie: __Host-sid=q0L7c...; Max-Age=1209600; Path=/; HttpOnly; Secure; SameSite=Lax
{"id":"7b5d3c2e-...","email":"ada@example.com","emailVerified":false,"roles":["customer"]}
```

Session và link xác minh đang chờ giờ là các dòng trong PostgreSQL. Id của session là hash SHA-256 của cookie, còn token của link hoàn toàn không được lưu:

```bash
$ psql "$DATABASE_URL" -c "SELECT user_id, mfa, metadata FROM sessions" -c "SELECT purpose, email FROM email_tokens"
               user_id                | mfa |          metadata
--------------------------------------+-----+-----------------------------
 7b5d3c2e-...                         |     | {"userAgent": "curl/8.7.1"}
(1 row)

      purpose       |      email
--------------------+-----------------
 email-verification | ada@example.com
(1 row)
```

Email xác minh xuất hiện trong log của ứng dụng (`LogMailTransport` in nội dung text của mỗi email):

```bash
LOG [LogMailTransport] "Confirm your email address" to ada@example.com
DEBUG [LogMailTransport] Confirm the email address of your store account:

Confirm my address (http://localhost:3000/verify-email?token=Vb3x...)

If you didn't create an account, ignore this email.
```

Cookie đăng nhập cho Ada, nhưng địa chỉ của cô ấy chưa được xác minh, nên cô ấy chưa đặt hàng được. Gửi token ngược lại giống như trang xác minh làm, và đơn hàng sẽ được chấp nhận. Không có cookie, API trả lời 401:

```bash
$ curl localhost:3000/me -b ada.txt
{"id":"7b5d3c2e-...","email":"ada@example.com","emailVerified":false,"roles":["customer"]}

$ curl localhost:3000/orders -b ada.txt --json '{"items":[{"productId":"salmon-kibble-2kg","quantity":1}]}'
{"message":"Email address not verified","error":"email_unverified","statusCode":403,"errorCode":"email_unverified"}

$ curl localhost:3000/auth/email/verify --json '{"token":"Vb3x..."}'
{"email":"ada@example.com","emailVerified":true}

$ curl localhost:3000/orders -b ada.txt --json '{"items":[{"productId":"salmon-kibble-2kg","quantity":1}]}'
{"id":"f3a1...","userId":"7b5d3c2e-...","items":[{"productId":"salmon-kibble-2kg","quantity":1}],"total":2499,"status":"pending"}

$ curl -i localhost:3000/orders
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="store"
{"message":"Unauthorized","statusCode":401,"errorCode":"missing_credentials"}
```

Đăng nhập với tư cách app mobile, và dùng access token. Các lệnh dưới đây dùng [jq](https://jqlang.org/) để lấy token ra:

```bash
$ TOKENS=$(curl -s localhost:3000/auth/token --json '{"email":"ada@example.com","password":"correct horse battery"}')
$ echo $TOKENS
{"accessToken":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","refreshToken":"Qm4x...","expiresIn":900}
$ ACCESS=$(echo $TOKENS | jq -r .accessToken) REFRESH=$(echo $TOKENS | jq -r .refreshToken)

$ curl localhost:3000/orders -H "Authorization: Bearer $ACCESS"
[{"id":"f3a1...","userId":"7b5d3c2e-...","items":[{"productId":"salmon-kibble-2kg","quantity":1}],"total":2499,"status":"pending"}]
```

Một refresh token chỉ dùng được một lần. Lần thử thứ hai với cùng token đó được xem là bị đánh cắp, và cả family bị thu hồi:

```bash
$ curl localhost:3000/auth/token/refresh --json "{\"refreshToken\":\"$REFRESH\"}"
{"accessToken":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","refreshToken":"n8Vb...","expiresIn":900}

$ curl localhost:3000/auth/token/refresh --json "{\"refreshToken\":\"$REFRESH\"}"
{"message":"Refresh token reused","error":"Unauthorized","statusCode":401}
```

Bật xác thực hai lớp. Thêm secret vào một app authenticator, và xác nhận bằng mã mà nó hiển thị. Mã chứng minh trình duyệt này có authenticator, nên session được xác minh kể từ đây, dưới một cookie mới (`-c` lưu nó lại):

```bash
$ curl -X POST localhost:3000/auth/mfa/enroll -b ada.txt
{"secret":"MZXW6YTBOI3DGNJS...","uri":"otpauth://totp/example.com:ada%40example.com?secret=MZXW6YTBOI3DGNJS...&issuer=example.com&algorithm=SHA1&digits=6&period=30"}

$ curl -i localhost:3000/auth/mfa/confirm -b ada.txt -c ada.txt --json '{"code":"492039"}'
HTTP/1.1 200 OK
Set-Cookie: __Host-sid=Kp4w...; Max-Age=1209571; Path=/; HttpOnly; Secure; SameSite=Lax
{"recoveryCodes":["7KQ2M-XR4PB","HT9WC-3MDNA","..."]}
```

> info **Gợi ý** Khi đã cài [oath-toolkit](https://www.nongnu.org/oath-toolkit/), `oathtool --totp -b` theo sau là secret sẽ in mã hiện tại ra terminal.

Đăng nhập lại. Session mới ở trạng thái pending cho đến khi qua được yếu tố thứ hai, và việc xác minh sẽ thay cookie:

```bash
$ curl localhost:3000/auth/sign-in -b ada.txt -c ada.txt --json '{"email":"ada@example.com","password":"correct horse battery"}'
{"mfaRequired":true}

$ curl localhost:3000/me -b ada.txt
{"message":"Second factor required","error":"mfa_required","statusCode":401,"errorCode":"mfa_required"}

$ curl localhost:3000/auth/mfa/verify -b ada.txt -c ada.txt --json '{"code":"815224"}'
{"mfa":"verified"}

$ curl -X PATCH localhost:3000/me/email -b ada.txt --json '{"email":"ada.lovelace@example.com"}'
{"id":"7b5d3c2e-...","email":"ada.lovelace@example.com","emailVerified":false,"roles":["customer"]}
```

Địa chỉ mới chưa được xác minh, và một email xác minh được gửi tới nó:

```bash
LOG [LogMailTransport] "Confirm your email address" to ada.lovelace@example.com
```

App mobile cũng bị yêu cầu nhập mã:

```bash
$ curl localhost:3000/auth/token --json '{"email":"ada.lovelace@example.com","password":"correct horse battery"}'
{"message":"Second factor required","error":"mfa_required","statusCode":401,"errorCode":"mfa_required"}
```

Bắt đầu một lần đăng nhập bằng Google. curl hiển thị redirect; mở cùng URL đó trên trình duyệt để hoàn tất, và bạn sẽ đến `/orders`, ở trạng thái đã đăng nhập:

```bash
$ curl -i 'localhost:3000/auth/oidc/google/login?redirectTo=/orders'
HTTP/1.1 302 Found
Set-Cookie: __Host-oidc_tx=Zq8...; Max-Age=600; Path=/; HttpOnly; Secure; SameSite=Lax
Location: https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=...&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Foidc%2Fgoogle%2Fcallback&scope=openid+email+profile&state=pW4c...&code_challenge=...&code_challenge_method=S256&nonce=...
```

Xin một magic link cho khách hàng mới tên Grace. Link chỉ dùng được trên trình duyệt đã xin nó, nên hãy giữ cookie mà response đặt. Email xuất hiện trong log của ứng dụng:

```bash
$ curl -i localhost:3000/auth/magic-link -c grace.txt --json '{"email":"grace@example.com"}'
HTTP/1.1 202 Accepted
Set-Cookie: __Host-magic_link_tx=Vn3p...; Max-Age=900; Path=/; HttpOnly; Secure; SameSite=Lax
```

```bash
LOG [LogMailTransport] "Your sign-in link" to grace@example.com
DEBUG [LogMailTransport] Sign in to the store (http://localhost:3000/sign-in/magic?token=Hq2x...)

The link works once, for 15 minutes. If you didn't ask for it, ignore this email.
```

Gửi token ngược lại giống như trang làm, kèm cookie đó. Grace nhận được một tài khoản, với địa chỉ đã xác minh, và một session:

```bash
$ curl localhost:3000/auth/magic-link/consume -b grace.txt -c grace.txt --json '{"token":"Hq2x..."}'
{"redirectTo":"/","mfaRequired":false}

$ curl localhost:3000/me -b grace.txt
{"id":"c41e9a07-...","email":"grace@example.com","emailVerified":true,"roles":["customer"]}
```

Grace điều hành một trại cứu trợ mèo, có hệ thống quản lý kho tự đặt mua cát vệ sinh. Hãy tạo một key cho nó từ session của cô ấy, và đặt hàng bằng key đó. Key không thể tạo key, và khi Grace thu hồi nó, nó ngừng hoạt động:

```bash
$ API_KEY=$(curl -s -X POST localhost:3000/auth/api-keys -b grace.txt)
$ echo $API_KEY
{"id":"d2cb7a64f3279c6b","key":"cat_d2cb7a64f3279c6b_QiBr...","createdAt":"2026-09-22T10:02:41.067Z","expiresAt":"2027-09-22T10:02:41.067Z"}
$ KEY=$(echo $API_KEY | jq -r .key) KEY_ID=$(echo $API_KEY | jq -r .id)

$ curl localhost:3000/orders -H "Authorization: Bearer $KEY" --json '{"items":[{"productId":"clumping-litter-10l","quantity":20}]}'
{"id":"db8a...","userId":"c41e9a07-...","items":[{"productId":"clumping-litter-10l","quantity":20}],"total":31980,"status":"pending"}

$ curl -X POST localhost:3000/auth/api-keys -H "Authorization: Bearer $KEY"
{"message":"Unauthorized","statusCode":401,"errorCode":"missing_credentials"}

$ curl -i -X DELETE localhost:3000/auth/api-keys/$KEY_ID -b grace.txt
HTTP/1.1 204 No Content

$ curl -i localhost:3000/orders -H "Authorization: Bearer $KEY"
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="store", error="invalid_token", error_description="invalid api key"
{"message":"invalid api key","error":"Unauthorized","statusCode":401}
```

Liệt kê các session của Ada, rồi đăng xuất cô ấy khỏi mọi nơi. Cookie cũ của cô ấy ngừng hoạt động:

```bash
$ curl localhost:3000/auth/sessions -b ada.txt
[{"id":"eT0r...","createdAt":"2026-09-22T10:02:11.042Z","lastActiveAt":"2026-09-22T10:03:30.518Z","userAgent":"curl/8.7.1","current":true}]

$ curl -i -X POST localhost:3000/auth/sign-out-everywhere -b ada.txt
HTTP/1.1 204 No Content
Set-Cookie: __Host-sid=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax

$ curl localhost:3000/me -b ada.txt
{"message":"Unauthorized","statusCode":401,"errorCode":"missing_credentials"}
```

Ada quên mật khẩu. Hãy xin link đặt lại mật khẩu cho địa chỉ của cô ấy, và cho một địa chỉ chưa ai đăng ký: cả hai đều nhận cùng response 202 rỗng, và chỉ Ada nhận được email:

```bash
$ curl -i localhost:3000/auth/password/forgot --json '{"email":"ada.lovelace@example.com"}'
HTTP/1.1 202 Accepted

$ curl -i localhost:3000/auth/password/forgot --json '{"email":"nobody@example.com"}'
HTTP/1.1 202 Accepted
```

```bash
LOG [LogMailTransport] "Reset your password" to ada.lovelace@example.com
DEBUG [LogMailTransport] Someone asked to reset the password of your store account.

Choose a new password (http://localhost:3000/reset-password?token=Rt7k...)

The link works once, for an hour. If it wasn't you, ignore this email: your password stays as it is.
```

Chọn mật khẩu mới bằng token, giống như trang đặt lại mật khẩu làm. Ada được đăng nhập lại, đang chờ yếu tố thứ hai (một session pending sống mười phút, `mfa.pendingTtl`, do đó có `Max-Age`), và mật khẩu cũ không còn dùng được nữa:

```bash
$ curl -i localhost:3000/auth/password/reset -c ada.txt --json '{"token":"Rt7k...","password":"a brand new passphrase"}'
HTTP/1.1 200 OK
Set-Cookie: __Host-sid=Yb2d...; Max-Age=600; Path=/; HttpOnly; Secure; SameSite=Lax
{"mfaRequired":true}

$ curl localhost:3000/auth/sign-in --json '{"email":"ada.lovelace@example.com","password":"correct horse battery"}'
{"message":"Invalid email or password","error":"Unauthorized","statusCode":401}
```

Cuối cùng, thử đoán mật khẩu của Grace. Lần thử thứ sáu trong vòng 15 phút bị từ chối trước khi mật khẩu được kiểm tra:

```bash
$ for i in 1 2 3 4 5 6; do curl -s -o /dev/null -w '%{http_code} ' localhost:3000/auth/sign-in --json '{"email":"grace@example.com","password":"password123"}'; done
401 401 401 401 401 429
```

#### GraphQL và WebSocket <a id="graphql-and-websockets"></a>

Global guard, `@Public()`, `@CurrentUser()` và `AuthenticationContext` cũng hoạt động trong GraphQL resolver và WebSocket gateway. Guard đọc cookie và header từ request mang chúng.

Trong GraphQL, đó là `req` trên GraphQL context, nên tùy chọn `context` phải là một hàm tạo context cho mỗi request. Một `context` cho dưới dạng object sẽ là một object duy nhất cho mọi request, và app sẽ lỗi lúc khởi động. Nest chỉ chạy global guard và interceptor trên root resolver: để guard cả field resolver, và cung cấp `AuthenticationContext` cho chúng, hãy thêm `fieldResolverEnhancers: ['guards', 'interceptors']`.

```typescript
@@filename(src/app.module)
GraphQLModule.forRoot<ApolloDriverConfig>({
  driver: ApolloDriver,
  autoSchemaFile: true,
  subscriptions: { 'graphql-ws': true },
  // Over graphql-ws there is no request per operation: the upgrade request stands in for it.
  context: ({ req, res, extra }) => ({ req: req ?? extra?.request, res }),
  fieldResolverEnhancers: ['guards', 'interceptors'],
}),
```

Qua `graphql-ws`, mọi operation trên một socket dùng chung upgrade request đó, và mỗi operation cần người dùng sẽ xác thực lại bằng cookie của nó, nên một lần đăng xuất khỏi mọi nơi sẽ chặn operation tiếp theo. `@CurrentUser()` cho mỗi operation người dùng riêng của nó, và `null` với operation `@Public()`. `req.user`, thứ mà module cũng đặt cho code đọc request, chứa người dùng của operation nào xác thực sau cùng: hãy đọc `@CurrentUser()` thay vào đó.

Nest không chạy guard nào trên `handleConnection()` của gateway, nên hãy xác thực handshake bằng `WsAuthenticator`:

```typescript
@@filename(src/orders/orders.gateway)
import type { IncomingMessage } from 'node:http';
import { WebSocketGateway, type OnGatewayConnection } from '@nestjs/websockets';
import { WsAuthenticator } from '@nestjs/authentication';
import type { WebSocket } from 'ws';

@WebSocketGateway()
export class OrdersGateway implements OnGatewayConnection {
  constructor(private readonly wsAuthenticator: WsAuthenticator) {}

  async handleConnection(client: WebSocket, request: IncomingMessage) {
    await this.wsAuthenticator.authenticateConnection(client, request);
  }
}
```

Nó đóng một kết nối không có ai đăng nhập, với mã 1008, hoặc `disconnect()` của socket.io; để giữ lại khách vãng lai, hãy truyền cho `authenticateConnection()` một tham số thứ ba có tùy chọn `required` là `false`. Với socket.io, nó đọc header của handshake, nên có thể bỏ tham số `request`. Một handshake từ trang của site khác là ẩn danh, giống như một [thao tác ghi cross-origin](/security/authentication#add-sign-up-and-sign-in). Sau đó guard xác thực lại mọi message, nên một session đã bị thu hồi sẽ ngừng hoạt động ngay giữa chừng kết nối. `@CurrentUser()` tính theo từng message, `null` với message `@Public()`. `client.user` chứa người dùng của message xác thực sau cùng, và bị xóa khi một message bị từ chối vì thông tin xác thực của nó.

[`@nestjs/authorization`](/security/authorization) kiểm tra `@Can()` với người dùng của từng message và từng operation, không phải của socket.

#### Test <a id="testing"></a>

End-to-end test khởi động `AppModule` thật, với ba thứ được thay đổi. Database là [PGlite](https://pglite.dev), PostgreSQL được biên dịch sang WebAssembly, với các migration thật của bạn được áp dụng, nên test không cần server. Mail được gửi tới một `InMemoryMailTransport`, transport này giữ mỗi email để bài test đọc. Và scrypt cố ý chậm, vài trăm mili giây và 128 MiB bộ nhớ cho mỗi lần hash ở mức chi phí mặc định, nên bài test ghi đè `PasswordHasher` bằng một bản rẻ hơn. Ứng dụng cũng đọc thiết lập lúc bootstrap, nên test cần các giá trị test cho chúng:

```typescript
@@filename(vitest.config.e2e)
export default defineConfig({
  // ...
  test: {
    // ...
    env: {
      APP_URL: 'http://localhost:3000',
      JWT_SECRET: 'test-only-jwt-secret-of-at-least-32-bytes',
      TOTP_ENCRYPTION_KEY: 'test-only-totp-key-of-at-least-32-chars',
      GOOGLE_CLIENT_ID: 'store.apps.googleusercontent.com',
      GOOGLE_CLIENT_SECRET: 'test-only-google-secret',
    },
  },
});
```

```typescript
@@filename(test/auth.e2e-spec)
import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { PGlite } from '@electric-sql/pglite';
import { PasswordHasher } from '@nestjs/authentication';
import { getDrizzleToken } from '@nestjs/drizzle';
import { InMemoryMailTransport, MailTransport } from '@nestjs/mail';
import { drizzle } from 'drizzle-orm/pglite';
import { migrate } from 'drizzle-orm/pglite/migrator';
import { fileURLToPath } from 'node:url';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';
import { VerifyEmailMail } from '../src/auth/email-verification.mailer.js';
import { PasswordResetMail } from '../src/auth/password-reset.mailer.js';

describe('Authentication (e2e)', () => {
  const pglite = new PGlite(); // PostgreSQL in-process: no server to start
  const mailbox = new InMemoryMailTransport();
  let app: INestApplication;
  const ada = { email: 'ada@example.com', password: 'correct horse battery' };

  beforeAll(async () => {
    const db = drizzle({ client: pglite });
    // The app's migrations, the authentication tables included.
    await migrate(db, { migrationsFolder: fileURLToPath(new URL('../drizzle', import.meta.url)) });
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(getDrizzleToken()) // the database DrizzleModule provides
      .useValue(db)
      .overrideProvider(MailTransport)
      .useValue(mailbox)
      .overrideProvider(PasswordHasher)
      .useValue(new PasswordHasher({ logN: 10 }))
      .compile();
    app = moduleRef.createNestApplication();
    await app.listen(0, '127.0.0.1');
  });

  afterAll(async () => {
    await app.close();
    await pglite.close();
  });

  it('signs up, verifies the address, then reads the profile with the session cookie', async () => {
    const res = await request(app.getHttpServer()).post('/auth/sign-up').send(ada).expect(201);
    const cookie = res.headers['set-cookie'][0].split(';')[0];

    const mail = mailbox.assertSent({ to: ada.email, mail: VerifyEmailMail });
    const token = mail.link('/verify-email').searchParams.get('token');
    await request(app.getHttpServer()).post('/auth/email/verify').send({ token }).expect(200);

    await request(app.getHttpServer())
      .get('/me')
      .set('Cookie', cookie)
      .expect(200, { id: res.body.id, email: ada.email, emailVerified: true, roles: ['customer'] });
  });

  it('issues bearer tokens to the mobile app', async () => {
    const res = await request(app.getHttpServer()).post('/auth/token').send(ada).expect(200);

    await request(app.getHttpServer())
      .get('/orders')
      .set('Authorization', `Bearer ${res.body.accessToken}`)
      .expect(200, []);
  });

  it('resets a forgotten password', async () => {
    await request(app.getHttpServer()).post('/auth/password/forgot').send({ email: ada.email }).expect(202);
    // The email goes out after the response, which doesn't wait for it.
    const mail = await vi.waitFor(() => mailbox.assertSent({ to: ada.email, mail: PasswordResetMail }));
    const token = mail.link('/reset-password').searchParams.get('token');

    await request(app.getHttpServer())
      .post('/auth/password/reset')
      .send({ token, password: 'a brand new passphrase' })
      .expect(200);
    await request(app.getHttpServer()).post('/auth/sign-in').send(ada).expect(401);
  });

  it('rejects anonymous requests and wrong passwords', async () => {
    await request(app.getHttpServer()).get('/orders').expect(401);
    await request(app.getHttpServer())
      .post('/auth/sign-in')
      .send({ ...ada, password: 'not the password' })
      .expect(401);
  });
});
```

- `mailbox.assertSent()` tìm email gần nhất gửi tới một địa chỉ, thuộc một mail class, còn `link()` trả về link đầu tiên trong đó có chứa path, dưới dạng `URL`. Đó là toàn bộ luồng cho link xác minh, đặt lại mật khẩu và magic link: gửi, tìm link, đi theo nó.
- Email đặt lại mật khẩu được gửi sau khi có response (xem [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords)), nên bài test chờ nó bằng `vi.waitFor()`. Các email khác được gửi trước khi route trả lời.
- `DrizzleAuthenticationStore` chạy trên PGlite giống như trên PostgreSQL. PGlite chỉ có một kết nối, nên hai request không bao giờ thực sự chạy đua ở đó; các [test hợp đồng](/security/authentication#keep-sessions-and-tokens-in-your-database) của store cũng chạy trên PostgreSQL, nơi chúng thực sự chạy đua.

Để đăng nhập một người dùng test mà không cần đi qua route đăng nhập, `SessionService.create()` trả về một session cookie, còn `TokenService.issue()` trả về một bearer token (cho người dùng không có authenticator). Để test code đọc `AuthenticationContext` mà không cần HTTP, hãy chạy nó với tư cách một người dùng: `run()` nhận một kết quả xác thực (người dùng, và tùy chọn là session) cùng một hàm để chạy.
#### Checklist cho production <a id="production-checklist"></a>

- **Đăng ký store cho mọi thứ mà module lưu giữ**, như trong phần [Giữ session và token trong database của bạn](/security/authentication#keep-sessions-and-tokens-in-your-database), và áp dụng các bảng của nó qua migration. Mọi instance của ứng dụng đều dùng chúng, nên một lần khởi động lại không đăng xuất ai cả. Module từ chối khởi động khi một store mà tính năng đã cấu hình cần dùng chưa được đăng ký, nhưng chỉ khi `NODE_ENV` là `production`: hãy đặt nó, nếu không một lần deploy quên đặt sẽ chạy trong bộ nhớ mà chỉ có một dòng log lúc khởi động báo điều đó. Hãy chạy các test hợp đồng của package với store của bạn, với `concurrent: true` trên PostgreSQL: chúng sẽ đánh trượt một store đọc rồi mới ghi ở chỗ cần một câu lệnh có điều kiện duy nhất.
- **Cấu hình cùng các tính năng trong mọi ứng dụng dùng chung database người dùng.** Mỗi ứng dụng tự quyết định dựa trên tùy chọn của nó xem một lần đăng nhập có hỏi yếu tố thứ hai không và việc đăng xuất khỏi mọi nơi có kết thúc refresh token không. Nếu bất kỳ ứng dụng nào đăng nhập người dùng cấu hình `mfa`, thì mọi ứng dụng đều phải cấu hình, nếu không một khách hàng đăng ký authenticator qua một ứng dụng có thể đăng nhập vào ứng dụng khác chỉ bằng mật khẩu. Tương tự, hãy cấu hình `accessToken`, với refresh token được bật, trong từng ứng dụng nếu việc đăng xuất khỏi mọi nơi hoặc đặt lại mật khẩu ở một ứng dụng cũng phải đăng xuất các token client của các ứng dụng khác.
- **Gửi email qua một provider thực thụ.** Hãy đặt `SMTP_URL`, hoặc truyền một transport khác. `LogMailTransport` ghi mọi link vào log, nơi bất kỳ ai đọc được log đều có thể đăng nhập với tư cách khách hàng.
- **Phục vụ ứng dụng qua HTTPS**, vì session cookie là `Secure`. Nếu web app chạy trên một origin khác với API, hãy liệt kê nó trong `session.trustedOrigins`, nếu không các lần đăng nhập và xin magic link của nó sẽ bị từ chối, còn các request `POST` và kết nối WebSocket của nó sẽ là ẩn danh. Đằng sau một proxy viết lại `Host`, hãy liệt kê cả origin công khai ở đó. Hãy giữ `cookie.secure` bật: một cookie `SameSite=None` không có nó sẽ lỗi lúc khởi động, vì trình duyệt sẽ bỏ qua nó.
- **Gọi `app.enableCsrfProtection()` trên Nest 12.1 trở lên**, với cùng `trustedOrigins`. Nó từ chối các thao tác ghi cross-origin tới mọi route, không chỉ những route dùng session cookie.
- **Giữ secret trong một secret manager**: JWT secret, các key mã hóa TOTP, Google client secret và thông tin đăng nhập SMTP. Xoay vòng các key TOTP như mô tả trong [Thêm xác thực hai lớp](/security/authentication#add-two-factor-authentication).
- **Xây dựng các trang xác minh và đặt lại mật khẩu để POST token**, và phục vụ chúng từ `APP_URL`. Các trình quét email đi theo link bằng request GET; một trang dùng token ngay khi load sẽ để chúng dùng hết token.
- **Giữ cho `forgot` không để lộ gì.** Hãy trả lời nó theo cùng một cách bất kể chuyện gì xảy ra, như [route `forgot`](/security/authentication#reset-forgotten-passwords) làm, và đừng `await` `request()`. Đăng ký vẫn trả lời 409 cho một địa chỉ đã có tài khoản; nếu điều đó quan trọng với bạn, hãy trả lời đăng ký theo cùng cách, và gửi email cho chủ sở hữu thay vào đó.
- **Đăng ký redirect URI của production** với Google, và đặt `APP_URL` thành origin công khai của ứng dụng.
- **Tính toán cấu hình server cho scrypt.** Mỗi lần hash ở mức chi phí mặc định tốn 128 MiB, trên threadpool của libuv (bốn thread trừ khi bạn đặt `UV_THREADPOOL_SIZE`). Các đợt đăng nhập dồn dập sẽ xếp hàng chờ nhau; throttler giới hạn chúng.
- **Dùng storage dùng chung cho throttler**, như Redis. Storage mặc định của nó đếm trong bộ nhớ của từng process, nên mỗi instance đếm riêng và một lần khởi động lại hay deploy sẽ reset bộ đếm. Bật `trust proxy` khi đứng sau proxy. Để chống đoán mật khẩu phân tán qua nhiều địa chỉ IP, hãy thêm một định nghĩa throttler thứ ba có tracker chỉ là email. Hãy đặt giới hạn cao hơn nhiều so với số lần khách hàng gõ nhầm trong một ngày, và bỏ qua nó trên các route khác ngoài đăng nhập và cấp token: bất kỳ ai biết địa chỉ cũng có thể dùng hết nó, và ngăn khách hàng đăng nhập bằng mật khẩu cho đến khi nó được reset.
- **Xoay vòng session khi quyền hạn thay đổi** bằng `SignInService.rotateSession()`. Sau khi đổi mật khẩu trong lúc đang đăng nhập, hoặc khi khách hàng bật hay tắt xác thực hai lớp, hãy kết thúc luôn các session và refresh token khác của họ: `SessionService.revokeAll()` với session hiện tại làm `except`, và `TokenService.revokeAll()`. Bất kỳ ai biết mật khẩu cũ có thể vẫn đang đăng nhập. Một lần [đặt lại mật khẩu](/security/authentication#reset-forgotten-passwords) làm việc này giúp bạn.
- **Xử lý API key như secret.** Bảng chỉ giữ hash của chúng, và một key chỉ được hiển thị một lần, khi được tạo: một database bị lộ không cho ai key nào, và một key bị mất sẽ bị thu hồi và thay thế, không bao giờ được hiển thị lại. Key hết hạn sau một năm, nên hãy nhắc chủ sở hữu tạo key kế tiếp khi key cũ vẫn còn dùng được. Thêm pattern `cat_` vào trình quét secret của bạn (GitHub secret scanning nhận pattern tùy chỉnh) để tìm các key bị commit lên repository, và thu hồi chúng. Request dùng key không phát ra event nào: hãy log `keyId` từ `@CurrentSession()` ở nơi bạn cần biết key nào đã làm gì. Một lần đặt lại mật khẩu hay đăng xuất khỏi mọi nơi không đụng tới key: hãy thu hồi chúng khi có các event đó nếu chúng cũng cần cắt luôn key.
- **Duy trì audit trail.** `AuthenticationEvents` công bố mọi lần đăng nhập và đăng xuất, thay đổi yếu tố thứ hai, refresh token bị dùng lại, đặt lại mật khẩu và xác minh email, trên stream `events$` của nó và trên `node:diagnostics_channel`. Hãy lưu chúng ở nơi team bảo mật của bạn tìm kiếm được. Đặt cảnh báo cho các event `mfa-failed` lặp lại với `locked: true` (ai đó có mật khẩu đang đoán mã), cho nhiều event `password-reset-requested` không có `userId` từ cùng một nguồn (ai đó đang dò tìm tài khoản), và cho các event `session-touch-failed`, vì chúng có nghĩa là session store đang từ chối ghi.
- **Import `AuthenticationModule` trước `AuthorizationModule`** nếu bạn thêm `@nestjs/authorization`. Global guard chạy theo thứ tự import, và phân quyền cần người dùng mà xác thực đặt vào. Thứ tự ngược lại sẽ lỗi lúc khởi động. `@nestjs/authorization` từ chối một handler không khai báo kiểm tra nào, và tính `@Public()` là một kiểm tra: một route công khai không cần `@Can.Anyone()`.

#### Hợp đồng của store <a id="the-store-contract"></a>

Bài hướng dẫn đã [viết authentication store bằng Drizzle](/security/authentication#keep-sessions-and-tokens-in-your-database). Phần này tóm tắt những gì sáu hợp đồng đòi hỏi ở mọi store, để viết store bằng một ORM khác. Mỗi method của các interface store đều nêu quy tắc của nó trong doc comment, cùng cuộc đua mà quy tắc đó ngăn chặn, và các test hợp đồng của package kiểm tra chúng.

**Đăng ký.** Một store là một singleton provider thông thường, tự đăng ký trong constructor bằng `registerSource()` trên `AuthenticationStorage` có thể inject, theo tên hợp đồng: `sessions`, `refreshTokens`, `mfa`, `magicLinks`, `oidcStates` và `emailTokens`. Tên method không bao giờ trùng nhau giữa các hợp đồng, nên một class có thể implement cả sáu, hoặc nhiều class có thể chia nhau. Registry kiểm tra cấu trúc của mỗi store ngay lập tức, từ chối store thứ hai cho cùng một tên trừ khi nó truyền `replace: true`, và khóa lại khi `AuthenticationModule` khởi tạo, log nơi mỗi loại state được lưu. Một hợp đồng không có store sẽ dùng mặc định trong bộ nhớ, thứ mất hết dữ liệu khi khởi động lại và không được chia sẻ giữa các instance.

**Bảo vệ trên production.** Với `NODE_ENV=production`, việc khởi động thất bại khi một hợp đồng mà tính năng đã cấu hình cần dùng không có store, kèm tên từng interface bị thiếu:

| Đã cấu hình | Hợp đồng |
| --- | --- |
| một `SessionCookieProvider` | `sessions` |
| `accessToken`, với refresh token được bật | `refreshTokens` |
| `accessToken`, với `refreshToken` đặt là `false` | không có |
| `mfa` | `mfa` |
| `magicLink` | `sessions`, `magicLinks` |
| `oidc` | `sessions`, `oidcStates` |
| `passwordReset` | `sessions`, `emailTokens` |
| `emailVerification` | `emailTokens` |

Xác thực hai lớp bị tắt nếu không có `mfa`: việc đăng nhập không đọc hợp đồng `mfa`. Refresh token chỉ tồn tại khi có `accessToken`, nên khi không có nó, hoặc khi `refreshToken` đặt là `false`, việc đăng xuất khỏi mọi nơi và đặt lại mật khẩu chỉ kết thúc session. Một hợp đồng mà không tính năng đã cấu hình nào dùng sẽ lỗi ở lần đọc đầu tiên thay vì chạy trong bộ nhớ. `allowInMemoryStorage: true` trong tùy chọn module vẫn chấp nhận các store trong bộ nhớ, nhưng khi đó mỗi lần khởi động lại hay deploy sẽ đăng xuất mọi người và quên các authenticator đã đăng ký, và các instance không chia sẻ gì với nhau.

**Các method phải nguyên tử.** Bất cứ thứ gì quyết định một việc chỉ được xảy ra một lần đều là một câu lệnh có điều kiện duy nhất, không bao giờ là đọc rồi ghi. Các method khác là các thao tác đọc, insert và delete thông thường. Không method nào nhận transaction của bạn: state xác thực được ghi riêng, không bao giờ là một phần của transaction nghiệp vụ.

| Hợp đồng | Method | Phải là | Vì sao |
| --- | --- | --- | --- |
| `SessionStore` | `touchSession()` | một câu `UPDATE` có điều kiện trên dòng đã tồn tại, chỉ đẩy `lastActiveAt` tới trước | một request ghi ngược session sau khi đã đăng xuất sẽ làm nó sống lại |
| `SessionStore` | `deleteSession()` | một câu `DELETE` resolve ra việc nó có xóa dòng hay không, dựa vào số dòng | giữa hai lần xoay vòng của cùng một session, hoặc một lần xoay vòng và một lần đăng xuất, chỉ một bên được thắng |
| `RefreshTokenStore` | `markRefreshTokenUsed()` | một câu `UPDATE ... WHERE used_at IS NULL`, đếm số dòng | kẻ trộm và chủ sở hữu refresh cùng lúc không được phép cùng thắng |
| `MfaStore` | `saveTotp()` | một câu upsert giữ `lastUsedStep` lớn hơn | lưu bản ghi không được mở lại một step vừa được dùng |
| `MfaStore` | `claimTotpStep()`, `consumeRecoveryCode()` | một câu `UPDATE` có điều kiện, một câu `DELETE`, đếm số dòng | một mã bị dùng lại phải thất bại |
| `MfaStore` | `recordMfaFailure()` | một câu insert, rồi một câu đếm, mỗi câu được commit riêng | một loạt lần đoán song song không được phép cùng thấy một con số thấp |
| `MfaStore` | `saveRecoveryCodes()` | một transaction: delete, rồi insert | bên đọc không bao giờ được thấy một nửa lô mã |
| `MagicLinkStore`, `OidcStateStore`, `EmailTokenStore` | `consumeMagicLink()`, `consumeOidcState()`, `consumeEmailToken()` | một câu `DELETE ... RETURNING` | một link không được phép đăng nhập hai trình duyệt, hay đặt hai mật khẩu |

Một family refresh token được tính là đã thu hồi khi bất kỳ token nào của nó bị thu hồi, nên một token kế tiếp được lưu sau khi thu hồi cũng bị thu hồi theo. Và các mục đang chờ (magic link, lần đăng nhập OIDC, email token) luôn có giới hạn: mỗi lần lưu sẽ xóa những gì đã hết hạn và, khi vượt quá mức trần, những gì hết hạn sớm nhất.

`touchSession()` là cố gắng hết sức: khi nó thất bại, request vẫn tiếp tục với session như đã đọc, và một event `session-touch-failed` báo cáo điều đó. `getSession()` có thể đặt `extra` thành những gì cùng query đã đọc kèm session, thường là người dùng của nó, để dùng cho `SessionCookieProvider.validate()`. `createSession()` không bao giờ nhận nó, và `listUserSessions()` không đặt nó.

**Với Prisma.** Bài hướng dẫn có store viết bằng Drizzle và bằng TypeORM, trên cùng các bảng. Một store Prisma tuân theo cùng các quy tắc:

- **Update và delete có điều kiện** (`touchSession()`, `deleteSession()`, `markRefreshTokenUsed()`, `claimTotpStep()`, `consumeRecoveryCode()`) là `updateMany()` hoặc `deleteMany()` với điều kiện trong `where`, và đọc `count` của chúng: `deleteSession()` resolve ra `count > 0`. Đừng bao giờ dùng `upsert()` cho `touchSession()`: nó có thể ghi ngược lại một session vừa bị xóa.
- **`saveTotp()`** cần `GREATEST(..., excluded.last_used_step)` trong câu upsert của nó. API upsert của Prisma không nhận biểu thức từ dòng bị xung đột, nên nó là SQL thô, với `$executeRaw`.
- **Các method `consume`** là `delete()` với mọi điều kiện trong `where` (id và, với `consumeEmailToken()`, cả mục đích), method này throw `P2025` khi không có gì khớp: hãy chuyển nó thành `undefined`.
- **`recordMfaFailure()`** là hai câu lệnh riêng biệt: một `create()`, rồi một `count()`. Không phải `prisma.$transaction([create, count])`, vì cách đó chạy cả hai trong một transaction chỉ commit sau khi đếm.
- **`saveRecoveryCodes()`** là method duy nhất cần transaction: `$transaction()`, dạng mảng của nó phù hợp ở đây.

**Test nó** bằng bộ test từ `@nestjs/authentication/testing`, như bài hướng dẫn làm. `authenticationStoreContract()` trả về các case cho mọi test runner, cho các hợp đồng mà factory của bạn trả về. `concurrent: true` thêm các cuộc đua: refresh song song cùng một token, dùng song song cùng một mã hoặc link, một loạt mã sai, một lần đăng xuất chạy đua với một request, xóa song song cùng một session, và một lần xoay vòng chạy đua với một lần đăng xuất hoặc một lần xoay vòng khác. Hãy chạy nó trên PostgreSQL với connection pool, nơi một store đọc rồi mới ghi sẽ thất bại. `maxPending` kiểm tra mức trần của các mục đang chờ, với một mức trần nhỏ được cấu hình cho bài test. Bộ test bỏ qua `extra` khi so sánh những gì `getSession()` trả về, nên một store có join người dùng vẫn qua được.
#### Tham khảo <a id="reference"></a>

##### Tùy chọn module <a id="module-options"></a>

`AuthenticationModule.forRoot()` nhận các tùy chọn này, và factory của `forRootAsync()` trả về chúng, ngoại trừ `isGlobal` và `globalGuard`, hai tùy chọn này vẫn nằm ở cấp cao nhất. Thời gian sống tính bằng mili giây, hoặc chuỗi như `'30s'`, `'15m'` và `'14d'`, tối đa 100 năm; giá trị dài hơn sẽ lỗi lúc khởi động. Mọi nhóm tùy chọn có liên quan tới đồng hồ đều nhận thêm `now`, một hàm trả về số mili giây epoch, dùng cho test.

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `isGlobal` | `true` | Đăng ký module ở cấp global. |
| `globalGuard` | `true` | Đăng ký `AuthenticationGuard` làm global guard. Với `false`, các route vẫn mở cho đến khi chúng dùng `@UseGuards(AuthenticationGuard)`. |
| `allowInMemoryStorage` | `false` | Khởi động với `NODE_ENV=production` khi một hợp đồng mà tính năng cần dùng chưa có store. Xem [Giữ session và token trong database của bạn](/security/authentication#keep-sessions-and-tokens-in-your-database). |
| `session.cookieName` | `__Host-sid` | Tên session cookie; là `sid` khi `cookie` không cho phép prefix `__Host-`. |
| `session.absoluteTtl` | `'7d'` | Thời gian sống tối đa của một session, bất kể nó hoạt động nhiều thế nào. |
| `session.idleTtl` | `'1d'` | Thời gian chờ khi không hoạt động, được gia hạn khi có hoạt động. `0` để tắt. |
| `session.touchInterval` | `'1m'` | Tần suất tối đa ghi hoạt động vào store. Phải ngắn hơn `idleTtl`, trừ khi nó là `0`: giá trị dài hơn sẽ lỗi lúc khởi động, vì người dùng đang hoạt động sẽ bị đăng xuất như thể không hoạt động. |
| `session.cookie` | `secure: true`, `sameSite: 'lax'`, `path: '/'` | Các thuộc tính cookie: `secure`, `sameSite`, `path`, `domain`. `HttpOnly` luôn được đặt. |
| `session.trustedOrigins` | không có | Các origin khác mà trang của chúng được phép dùng session cookie để ghi và đăng nhập. |
| `session.metadata` | không có | Một hàm nhận request đăng nhập, kết quả của nó được lưu cùng mỗi session mới. Xem [Cho khách hàng quản lý session](/security/authentication#let-customers-manage-their-sessions). |
| `password.logN` | `17` | Logarit cơ số 2 của chi phí scrypt N, một số nguyên từ 10 tới 22. `r` (mặc định `8`, tối đa 32), `p` (`1`, tối đa 16), `keyLength` (`32`) và `saltLength` (`16`, cả hai từ 16 tới 64) đặt các tham số còn lại. Một lần hash có thể tốn tối đa 1 GiB bộ nhớ (128·N·r byte) và gấp 16 lần khối lượng công việc mặc định (N·r·p), nên với `r` là 8, `logN` dừng ở 20. |
| `accessToken.key` | bắt buộc | Secret HS256 dài ít nhất 32 byte, hoặc một private key cho RS256, ES256 hay EdDSA, dưới dạng text PEM hoặc `KeyObject`. Một JWK hoặc key DER sẽ lỗi lúc khởi động: hãy import nó bằng `createPrivateKey()`. Xem [Cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app). |
| `accessToken.alg` | theo key | Thuật toán ký: HS256 với secret, thuật toán của chính key với private key. |
| `accessToken.issuer`, `audience` | không có | Các claim `iss` và `aud`, được ghi vào và kiểm tra trên mọi token. |
| `accessToken.ttl` | `'15m'` | Thời gian sống của access token. |
| `accessToken.kid`, `type` | không có, `JWT` | Các header `kid` và `typ`. |
| `refreshToken` | bật khi có `accessToken` | `false` chỉ cấp access token, không có refresh token và không cần `RefreshTokenStore`. Xem [Cấp token cho app mobile](/security/authentication#issue-tokens-to-the-mobile-app). |
| `refreshToken.ttl` | `'30d'` | Thời gian sống của một refresh token. |
| `refreshToken.absoluteTtl` | `'90d'` | Thời gian sống tối đa của một family refresh token, bất kể nó được xoay vòng bao nhiêu lần. |
| `mfa.encryption` | bắt buộc | `keys`, danh sách các key AES-256-GCM, mới nhất trước, cùng `migratePlaintext` (mặc định `false`); hoặc `false` để lưu secret dạng plaintext. Xem [Thêm xác thực hai lớp](/security/authentication#add-two-factor-authentication). |
| `mfa.issuer` | không có | Cái tên mà app authenticator hiển thị. |
| `mfa.window` | `1` | Số step 30 giây được chấp nhận ở mỗi phía của thời điểm hiện tại, một số nguyên từ 0 tới 10. |
| `mfa.maxAttempts` | `5` | Số mã sai được phép trong mỗi `lockoutWindow` trước khi mọi mã bị từ chối, một số nguyên ít nhất là 1. |
| `mfa.lockoutWindow` | `'15m'` | Khoảng thời gian dùng để đếm số mã sai. |
| `mfa.recoveryCodes` | `10` | Số mã khôi phục mỗi lô, một số nguyên ít nhất là 1. |
| `mfa.pendingTtl` | `'10m'` | Thời gian một session được phép chờ yếu tố thứ hai. |
| `emailVerification.url` | bắt buộc | Trang mà link xác minh mở ra. `ttl` mặc định là `'24h'`. Xem [Xác minh địa chỉ email](/security/authentication#verify-email-addresses). |
| `passwordReset.url` | bắt buộc | Trang mà link đặt lại mật khẩu mở ra. `ttl` mặc định là `'1h'`. Xem [Đặt lại mật khẩu đã quên](/security/authentication#reset-forgotten-passwords). |
| `magicLink.url` | bắt buộc | Trang mà magic link mở ra. `ttl` mặc định là `'15m'`. Xem [Thêm đăng nhập bằng magic link](/security/authentication#add-magic-link-sign-in). |
| `magicLink.bindToBrowser` | `true` | Chỉ chấp nhận link trên trình duyệt đã xin nó. |
| `magicLink.cookie` | `secure: true` | Các thuộc tính của cookie giao dịch `__Host-magic_link_tx`. |
| `oidc.callbackUrl` | bắt buộc | URL callback công khai, với `:provider` thay cho tên provider, hoặc một hàm nhận request và trả về URL đó. Xem [Thêm "Đăng nhập bằng Google"](/security/authentication#add-sign-in-with-google). |
| `oidc.providers` | bắt buộc | Cấu hình provider theo tên, như `google()`, `github()` và `microsoft()` (cái sau nhận thêm id `tenant` của directory), hoặc một hàm nhận tên và trả về cấu hình. Xem [Thêm "Đăng nhập bằng Google"](/security/authentication#add-sign-in-with-google). |
| `oidc.redirectAfterLogin` | `/` | Nơi đến khi lần đăng nhập không có `redirectTo`. |
| `oidc.transactionTtl` | `'10m'` | Thời gian tối đa một lần đăng nhập được phép kéo dài giữa redirect và callback. |
| `oidc.cookie` | `secure: true` | Các thuộc tính của cookie giao dịch `__Host-oidc_tx`. |
| `oidc.discoveryTtl`, `clockTolerance` | `'1h'`, `'30s'` | Thời gian một tài liệu discovery được tin cậy, và độ lệch cho phép với các claim thời gian của ID token. |

Các tính năng `emailVerification`, `passwordReset`, `magicLink` và `oidc` còn cần một handler cùng tên đã đăng ký; có cái này mà thiếu cái kia sẽ lỗi lúc khởi động. Một giá trị nằm ngoài các khoảng ở trên cũng vậy, kể cả `NaN` mà `Number()` tạo ra từ một biến môi trường chưa được đặt.

##### Tùy chọn route <a id="route-options"></a>

`@Authenticate()` nhận các tùy chọn này, trên class hoặc method:

| Tùy chọn | Mô tả |
| --- | --- |
| `optional` | Cho người gọi ẩn danh đi qua, với người dùng là `null`. Thông tin xác thực sai vẫn nhận lỗi 401. |
| `mfa` | Yêu cầu yếu tố thứ hai đã xác minh: một session đã xác minh, hoặc một JWT có `amr` chứa `mfa`, `otp` hoặc `hwk`. API key không bao giờ thỏa mãn được. Xem [Thêm xác thực hai lớp](/security/authentication#add-two-factor-authentication). |
| `verifiedEmail` | Yêu cầu địa chỉ email đã xác minh, nếu không trả lời 403 với `email_unverified`. Xem [Đọc người dùng hiện tại](/security/authentication#read-the-current-user). |
| `providers` | Chỉ những class provider này, hoặc class con của chúng, mới được xác thực route. |

##### API key <a id="api-keys"></a>

`ApiKeyProvider` nhận các tùy chọn này trong `super()`. Xem [Cấp API key cho đối tác](/security/authentication#issue-api-keys-to-partners).

| Tùy chọn | Mặc định | Mô tả |
| --- | --- | --- |
| `prefix` | bắt buộc | Phần mở đầu của mọi key, như trong `cat_<id>_<secret>`: từ 1 tới 16 chữ cái thường và chữ số, bắt đầu bằng một chữ cái. |
| `realm` | `api` | Realm trong challenge `WWW-Authenticate`. |

Class con của bạn implement `findKey(id)`, method này trả về `hash` đã lưu của key, `user` và `expiresAt` của nó, hoặc `null` với key không tồn tại, đã bị thu hồi, hoặc có chủ sở hữu không còn nữa. `generate()` trả về một key mới dưới dạng `key`, chỉ hiển thị một lần, cùng `id` và `hash` để lưu. Với một request dùng key, session là `keyId` và `expiresAt` của key, với `method` đặt là `api-key`.

##### Event <a id="events"></a>

`AuthenticationEvents` công bố mỗi event trên observable `events$` của nó, và trên diagnostics channel `nestjs:authentication:<type>`, như `nestjs:authentication:sign-in`.

| Loại | Payload | Khi nào |
| --- | --- | --- |
| `sign-in` | `userId`, `sessionId` hoặc `tokenFamilyId`, `method`, `mfa`, `metadata` | `SignInService.signIn()` hoặc `TokenService.issue()` đã đăng nhập một người dùng |
| `sign-out` | `userId`, `sessionId`, `tokenFamilyId` hoặc `everywhere` | Một session, một family refresh token, hoặc tất cả đã kết thúc |
| `mfa-verified` | `userId`, `method` (`totp` hoặc `recovery-code`) | Một mã đã được chấp nhận |
| `mfa-failed` | `userId`, `method`, `failures`, `locked` | Một mã bị từ chối, kể cả trong thời gian bị khóa |
| `mfa-enabled` | `userId`, `replaced` | Một authenticator đã được xác nhận |
| `mfa-disabled` | `userId` | Authenticator và mã khôi phục đã bị xóa |
| `recovery-codes-generated` | `userId`, `count` | Một lô mã khôi phục mới đã thay thế lô cũ |
| `refresh-token-reused` | `userId`, `tokenFamilyId` | Một refresh token đã dùng quay lại, và family của nó đã bị thu hồi |
| `password-reset-requested` | `email`, `userId` (không có với địa chỉ không tồn tại) | Ai đó đã xin link đặt lại mật khẩu |
| `password-reset` | `userId` | Một link đặt lại đã đặt mật khẩu mới |
| `email-verified` | `userId`, `email` | Một link xác minh đã được dùng |
| `magic-link-refused` | `reason` (`not-this-browser`, `unknown`, `expired` hoặc `refused`), `email` | Một magic link không đăng nhập được ai |
| `session-touch-failed` | `userId`, `sessionId`, `error` | `SessionStore.touchSession()` thất bại; request vẫn tiếp tục, và mốc hạn idle của session không thay đổi |

##### Lỗi <a id="errors"></a>

`AuthenticationError` là class cha của các lỗi trong package. Nó mang `status`, và tùy chọn `code`, `details` và `challenge` (header `WWW-Authenticate`). Khi được throw từ một handler hoặc bất cứ thứ gì handler gọi, nó trở thành HTTP exception của chính Nest, `UNAUTHENTICATED` của GraphQL, một `WsException` hoặc một `RpcException`. `code` của nó chính là `errorCode` của Nest. Qua HTTP và GraphQL, nó được đặt trên exception, nên một exception filter đọc được `exception.errorCode`, và Nest đưa nó vào body, hoặc vào `extensions.originalError` với GraphQL. Payload ws và rpc mang cùng key `errorCode`. Một lời từ chối có kèm message cũng gửi code dưới dạng `error`, như trước giờ vẫn vậy. `details`, một object thuần, được gửi nguyên vẹn dưới dạng `details`; không gì khác của lỗi (`cause`, stack) đến được client. Ví dụ, `new AuthenticationError('Too many attempts', options)` với `too_many_attempts` làm `code` và `retryAfter: 30` trong `details` sẽ trả lời:

```json
{"message":"Too many attempts","error":"too_many_attempts","statusCode":401,"errorCode":"too_many_attempts","details":{"retryAfter":30}}
```

| Lỗi | Status | `errorCode` | `error` | Khi nào |
| --- | --- | --- | --- | --- |
| `AuthenticationError` | 401 | `code` của nó, nếu có | `code` của nó; nếu không thì là `Unauthorized` khi có message, không có gì khi không có message | Thông tin xác thực sai, hoặc `requireUser()` khi không có người dùng (không message, không code) |
| `JwtError` | 401 | không có | `Unauthorized` | Một token sai định dạng, chữ ký không hợp lệ, đã hết hạn, hoặc thuộc issuer hay audience khác |
| `RefreshTokenError` | 401 | không có | `Unauthorized` | Một refresh token không hợp lệ, đã hết hạn hoặc bị dùng lại; `reason` cho biết trường hợp nào |
| `MagicLinkError` | 401 | `not_this_browser` | `not_this_browser` | Một magic link được mở trên trình duyệt khác với trình duyệt đã xin nó, hoặc sau khi trình duyệt đó đã xin thêm năm link mới hơn |
| `MfaAlreadyEnrolledError` | 409 | không có | `Conflict` | `enroll()` không có `replace: true` cho người dùng đã xác nhận authenticator |

Khi không provider nào nhận ra thông tin xác thực nào, guard trả lời 401 với `missing_credentials`, và không có `error`:

```json
{"message":"Unauthorized","statusCode":401,"errorCode":"missing_credentials"}
```

Điều đó bao gồm request không có thông tin xác thực, session cookie cũ hoặc không tồn tại (được tính như không có, để các route tùy chọn vẫn hoạt động), và thông tin xác thực mà `providers` của route không chấp nhận. Guard và `TokenService.issue()` cũng trả lời 401 với `mfa_required` khi còn thiếu yếu tố thứ hai, và 403 với `email_unverified` trên các route `verifiedEmail`, mỗi trường hợp đều dưới dạng cả `errorCode` lẫn `error`. Các route OIDC trả lời 400 với callback sai hoặc giả mạo, 401 khi câu trả lời của provider không qua được bước xác minh hoặc luồng link không có session đã đăng nhập, 403 khi resolver từ chối tài khoản hoặc luồng link được bắt đầu từ site khác, 404 với tên provider chưa được cấu hình, và 502 khi không liên lạc được với provider hoặc provider bị cấu hình sai, như một endpoint không phải https hay một bộ key không load được. `SignInService.signIn()` và `MagicLinkService.create()` trả lời 403 với request được gửi từ một origin khác.
