### Passport (xác thực)

[Passport](https://github.com/jaredhanson/passport) là library xác thực Node.js phổ biến nhất, được cộng đồng biết rõ và dùng trong nhiều ứng dụng production. Bạn có thể tích hợp nó với một ứng dụng **Nest** bằng module `@nestjs/passport`. Ở mức tổng quát, Passport thực hiện một chuỗi bước để:

- Xác thực một người dùng bằng cách kiểm tra "credential" của họ (như username/password, JSON Web Token ([JWT](https://jwt.io/)), hoặc identity token từ một Identity Provider)
- Quản lý trạng thái đã xác thực (bằng cách phát hành một token có thể mang đi, như JWT, hoặc tạo một [Express session](https://github.com/expressjs/session))
- Gắn thông tin về người dùng đã xác thực vào object `Request` để dùng tiếp trong các route handler

Passport có một hệ sinh thái [strategy](http://www.passportjs.org/) phong phú hiện thực nhiều cơ chế xác thực khác nhau. Dù đơn giản về khái niệm, tập strategy Passport để lựa chọn rất lớn và đa dạng. Passport trừu tượng hóa các bước đa dạng này thành một pattern chuẩn, và module `@nestjs/passport` bọc pattern này trong các cấu trúc quen thuộc của Nest.

Trong chương này, chúng ta sẽ hiện thực một giải pháp xác thực hoàn chỉnh từ đầu đến cuối cho một RESTful API server bằng các module này. Bạn có thể làm theo các bước trong chương này để xây dựng ví dụ hoàn chỉnh, và áp dụng cùng các khái niệm để hiện thực bất kỳ strategy Passport nào cũng như tùy chỉnh cơ chế xác thực của bạn.

#### Yêu cầu xác thực <a id="authentication-requirements"></a>

Với use case này, client bắt đầu bằng việc xác thực với username và password. Khi đã xác thực, server phát hành một JWT mà client có thể gửi dưới dạng [bearer token trong authorization header](https://tools.ietf.org/html/rfc6750) ở các request tiếp theo để chứng minh đã xác thực. Chúng ta cũng sẽ tạo một route được bảo vệ, chỉ truy cập được bởi các request có chứa JWT hợp lệ.

Chúng ta sẽ bắt đầu với yêu cầu đầu tiên: xác thực một người dùng. Sau đó chúng ta sẽ mở rộng nó bằng cách phát hành JWT. Cuối cùng, chúng ta sẽ tạo một route được bảo vệ kiểm tra JWT hợp lệ trên request.

Trước tiên, hãy cài các package cần thiết. Passport cung cấp một strategy tên [passport-local](https://github.com/jaredhanson/passport-local) hiện thực cơ chế xác thực username/password, phù hợp với phần này của use case.

```bash
$ npm install --save @nestjs/passport passport passport-local
$ npm install --save-dev @types/passport-local
```

> warning **Chú ý** Với **bất kỳ** strategy Passport nào bạn chọn, bạn luôn cần các package `@nestjs/passport` và `passport`. Bạn cũng cần package riêng của strategy (ví dụ `passport-jwt` hoặc `passport-local`) hiện thực strategy xác thực mà bạn đang xây dựng. Bạn cũng có thể cài các định nghĩa type cho strategy, như ở trên với `@types/passport-local`, để có type checking và hỗ trợ từ editor khi viết code TypeScript.

#### Hiện thực các strategy Passport <a id="implementing-passport-strategies"></a>

Giờ chúng ta đã sẵn sàng hiện thực tính năng xác thực. Chúng ta sẽ bắt đầu với tổng quan về quy trình dùng cho **mọi** strategy Passport. Sẽ hữu ích nếu coi bản thân Passport là một framework nhỏ. Nó trừu tượng hóa quy trình xác thực thành vài bước cơ bản mà bạn tùy chỉnh dựa trên strategy mình đang hiện thực. Nó giống một framework vì bạn cấu hình nó bằng cách cung cấp các tham số tùy chỉnh (dưới dạng JSON object thuần) và code tùy chỉnh dưới dạng các callback function, những thứ mà Passport gọi vào thời điểm thích hợp. Module `@nestjs/passport` bọc framework này trong một package theo phong cách Nest, để nó tích hợp tự nhiên vào một ứng dụng Nest. Chúng ta sẽ dùng `@nestjs/passport` bên dưới, nhưng trước tiên, hãy xem **Passport thuần** hoạt động thế nào.

Trong Passport thuần, bạn cấu hình một strategy bằng cách cung cấp hai thứ:

1. Một tập tùy chọn riêng của strategy đó. Ví dụ, trong một JWT strategy, bạn có thể cung cấp một secret để ký token.
2. Một "verify callback", là nơi bạn cho Passport biết cách tương tác với kho người dùng (nơi bạn quản lý tài khoản người dùng). Ở đây, bạn kiểm tra xem người dùng có tồn tại không (và/hoặc tạo người dùng mới), và credential của họ có hợp lệ không. Passport kỳ vọng callback này trả về một người dùng đầy đủ nếu việc validate thành công, hoặc `null` nếu thất bại (thất bại nghĩa là hoặc không tìm thấy người dùng, hoặc, với passport-local, mật khẩu không khớp).

Với `@nestjs/passport`, bạn cấu hình một strategy Passport bằng cách kế thừa class `PassportStrategy`. Bạn truyền các tùy chọn của strategy (mục 1 ở trên) bằng cách gọi `super()` trong constructor của subclass, tùy chọn kèm một options object. Bạn cung cấp verify callback (mục 2 ở trên) bằng cách hiện thực một method `validate()` trong subclass.

Chúng ta sẽ bắt đầu bằng việc sinh một `AuthModule` và trong đó, một `AuthService`:

```bash
$ nest g module auth
$ nest g service auth
```

`AuthService` sẽ dựa vào một `UsersService` đóng gói các thao tác về người dùng, nên hãy sinh module và service đó luôn:

```bash
$ nest g module users
$ nest g service users
```

Thay nội dung mặc định của các file được sinh ra này như bên dưới. Trong ứng dụng mẫu này, `UsersService` giữ một danh sách người dùng được hardcode trong bộ nhớ và cung cấp một method `findOne()` tra cứu người dùng theo username. Trong một ứng dụng thực tế, đây là nơi bạn xây dựng model người dùng và lớp lưu trữ bằng library bạn chọn (ví dụ TypeORM, Sequelize, Mongoose).

```typescript
@@filename(users/users.service)
import { Injectable } from '@nestjs/common';

// This should be a real class/interface representing a user entity
export type User = any;

@Injectable()
export class UsersService {
  private readonly users = [
    {
      userId: 1,
      username: 'john',
      password: 'changeme',
    },
    {
      userId: 2,
      username: 'maria',
      password: 'guess',
    },
  ];

  async findOne(username: string): Promise<User | undefined> {
    return this.users.find(user => user.username === username);
  }
}
@@switch
import { Injectable } from '@nestjs/common';

@Injectable()
export class UsersService {
  constructor() {
    this.users = [
      {
        userId: 1,
        username: 'john',
        password: 'changeme',
      },
      {
        userId: 2,
        username: 'maria',
        password: 'guess',
      },
    ];
  }

  async findOne(username) {
    return this.users.find(user => user.username === username);
  }
}
```

Trong `UsersModule`, thay đổi duy nhất cần làm là thêm `UsersService` vào mảng `exports` của decorator `@Module()`, để nó hiển thị bên ngoài module này (chúng ta sẽ dùng nó trong `AuthService` ngay sau đây).

```typescript
@@filename(users/users.module)
import { Module } from '@nestjs/common';
import { UsersService } from './users.service.js';

@Module({
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}
@@switch
import { Module } from '@nestjs/common';
import { UsersService } from './users.service.js';

@Module({
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}
```

`AuthService` của chúng ta lấy một người dùng và kiểm tra mật khẩu. Chúng ta tạo một method `validateUser()` cho mục đích này. Trong đoạn code bên dưới, chúng ta dùng cú pháp object rest để bỏ thuộc tính `password` khỏi object người dùng trước khi trả về nó. Local strategy của Passport sẽ gọi method `validateUser()` ngay sau đây.

```typescript
@@filename(auth/auth.service)
import { Injectable } from '@nestjs/common';
import { UsersService } from '../users/users.service.js';

@Injectable()
export class AuthService {
  constructor(private usersService: UsersService) {}

  async validateUser(username: string, pass: string): Promise<any> {
    const user = await this.usersService.findOne(username);
    if (user && user.password === pass) {
      const { password, ...result } = user;
      return result;
    }
    return null;
  }
}
@@switch
import { Injectable, Dependencies } from '@nestjs/common';
import { UsersService } from '../users/users.service.js';

@Injectable()
@Dependencies(UsersService)
export class AuthService {
  constructor(usersService) {
    this.usersService = usersService;
  }

  async validateUser(username, pass) {
    const user = await this.usersService.findOne(username);
    if (user && user.password === pass) {
      const { password, ...result } = user;
      return result;
    }
    return null;
  }
}
```

> warning **Cảnh báo** Trong một ứng dụng thực tế, không bao giờ lưu mật khẩu dưới dạng văn bản thuần. Thay vào đó, hãy dùng một library như [bcrypt](https://github.com/kelektiv/node.bcrypt.js#readme) với một thuật toán hash một chiều có salt. Với cách đó, bạn chỉ lưu các mật khẩu đã hash và so sánh hash đã lưu với phiên bản đã hash của mật khẩu **đi vào**, nên mật khẩu người dùng không bao giờ được lưu hay để lộ dưới dạng văn bản thuần. Để giữ ứng dụng mẫu đơn giản, chúng ta vi phạm quy tắc đó và dùng văn bản thuần. **Đừng làm điều này trong ứng dụng thật của bạn.**

Giờ hãy cập nhật `AuthModule` để import `UsersModule`.

```typescript
@@filename(auth/auth.module)
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { UsersModule } from '../users/users.module.js';

@Module({
  imports: [UsersModule],
  providers: [AuthService],
})
export class AuthModule {}
@@switch
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { UsersModule } from '../users/users.module.js';

@Module({
  imports: [UsersModule],
  providers: [AuthService],
})
export class AuthModule {}
```

#### Hiện thực Passport local <a id="implementing-passport-local"></a>

Giờ chúng ta có thể hiện thực **local authentication strategy** của Passport. Tạo một file tên `local.strategy.ts` trong thư mục `auth` và thêm đoạn code sau:

```typescript
@@filename(auth/local.strategy)
import { Strategy } from 'passport-local';
import { PassportStrategy } from '@nestjs/passport';
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { AuthService } from './auth.service.js';

@Injectable()
export class LocalStrategy extends PassportStrategy(Strategy) {
  constructor(private authService: AuthService) {
    super();
  }

  async validate(username: string, password: string): Promise<any> {
    const user = await this.authService.validateUser(username, password);
    if (!user) {
      throw new UnauthorizedException();
    }
    return user;
  }
}
@@switch
import { Strategy } from 'passport-local';
import { PassportStrategy } from '@nestjs/passport';
import { Injectable, UnauthorizedException, Dependencies } from '@nestjs/common';
import { AuthService } from './auth.service.js';

@Injectable()
@Dependencies(AuthService)
export class LocalStrategy extends PassportStrategy(Strategy) {
  constructor(authService) {
    super();
    this.authService = authService;
  }

  async validate(username, password) {
    const user = await this.authService.validateUser(username, password);
    if (!user) {
      throw new UnauthorizedException();
    }
    return user;
  }
}
```

Chúng ta đã làm theo công thức mô tả trước đó cho mọi strategy Passport. Cách chúng ta dùng passport-local không cần tùy chọn cấu hình nào, nên constructor gọi `super()` mà không có options object.

> info **Gợi ý** Bạn có thể truyền một options object trong lời gọi `super()` để tùy chỉnh hành vi của strategy Passport. Trong ví dụ này, strategy passport-local mặc định kỳ vọng các thuộc tính tên `username` và `password` trong body của request. Hãy truyền một options object để chỉ định tên thuộc tính khác, ví dụ: `super({{ '{' }} usernameField: 'email' {{ '}' }})`. Xem [tài liệu Passport](http://www.passportjs.org/docs/configure/) để biết thêm thông tin.

Chúng ta cũng đã hiện thực method `validate()`. Với mỗi strategy, Passport gọi verify function (được hiện thực bằng method `validate()` trong `@nestjs/passport`) với một tập tham số riêng của strategy. Với local strategy, Passport kỳ vọng một method `validate()` có signature sau: `validate(username: string, password: string): any`.

Phần lớn công việc validate được thực hiện trong `AuthService` (với sự trợ giúp của `UsersService`), nên method này ngắn gọn. Method `validate()` cho **mọi** strategy Passport đều theo một pattern tương tự, chỉ khác nhau ở cách biểu diễn credential. Nếu tìm thấy người dùng và credential hợp lệ, method trả về người dùng để Passport có thể hoàn tất các công việc của nó (ví dụ tạo thuộc tính `user` trên object `Request`), và pipeline xử lý request có thể tiếp tục. Nếu không, nó throw một exception và để [lớp xử lý exception](/exception-filters) xử lý.

Thông thường, khác biệt đáng kể duy nhất trong method `validate()` của mỗi strategy là **cách** bạn xác định một người dùng có tồn tại và hợp lệ hay không. Ví dụ, trong một JWT strategy, tùy yêu cầu, chúng ta có thể kiểm tra xem `userId` mang trong token đã decode có khớp với một bản ghi trong database người dùng không, hoặc có nằm trong danh sách token bị thu hồi không. Pattern kế thừa và hiện thực validate riêng cho từng strategy này nhất quán và có thể mở rộng.

Tiếp theo, cấu hình `AuthModule` để dùng các tính năng Passport mà chúng ta vừa định nghĩa. Cập nhật `auth.module.ts` thành như thế này:

```typescript
@@filename(auth/auth.module)
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { UsersModule } from '../users/users.module.js';
import { PassportModule } from '@nestjs/passport';
import { LocalStrategy } from './local.strategy.js';

@Module({
  imports: [UsersModule, PassportModule],
  providers: [AuthService, LocalStrategy],
})
export class AuthModule {}
@@switch
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { UsersModule } from '../users/users.module.js';
import { PassportModule } from '@nestjs/passport';
import { LocalStrategy } from './local.strategy.js';

@Module({
  imports: [UsersModule, PassportModule],
  providers: [AuthService, LocalStrategy],
})
export class AuthModule {}
```

#### Passport Guard có sẵn <a id="built-in-passport-guards"></a>

Chương [Guard](/guards) mô tả chức năng chính của guard: quyết định một request có được route handler xử lý hay không. Điều đó vẫn đúng, và chúng ta sẽ sớm dùng khả năng tiêu chuẩn đó. Tuy nhiên, module `@nestjs/passport` cũng đưa ra một điểm mới có thể gây bối rối lúc đầu, nên hãy bàn về nó ngay bây giờ. Từ góc nhìn xác thực, ứng dụng của bạn có thể ở một trong hai trạng thái:

1. người dùng/client **chưa** đăng nhập (chưa được xác thực)
2. người dùng/client **đã** đăng nhập (đã được xác thực)

Trong trường hợp đầu tiên (người dùng chưa đăng nhập), chúng ta cần thực hiện hai chức năng riêng biệt:

- Giới hạn các route mà một người dùng chưa xác thực có thể truy cập (tức là từ chối truy cập vào các route bị giới hạn). Chúng ta sẽ dùng guard theo vai trò quen thuộc của nó để xử lý chức năng này, bằng cách đặt một guard trên các route được bảo vệ. Guard này kiểm tra sự hiện diện của một JWT hợp lệ, nên chúng ta sẽ xây dựng nó sau, khi đã phát hành JWT.

- Khởi động chính **bước xác thực** khi một người dùng chưa xác thực cố gắng đăng nhập. Đây là bước chúng ta sẽ **phát hành** một JWT cho một người dùng hợp lệ. Client cần `POST` credential username/password để khởi động việc xác thực, nên chúng ta sẽ thiết lập một route `POST /auth/login` để xử lý việc đó. Câu hỏi còn lại là làm sao gọi strategy passport-local trong route đó.

Câu trả lời là một loại guard khác, hơi khác một chút. Module `@nestjs/passport` cung cấp một guard có sẵn gọi strategy Passport và khởi động các bước mô tả ở trên (lấy credential, chạy verify function, tạo thuộc tính `user`, v.v.).

Trường hợp thứ hai (người dùng đã đăng nhập) dựa vào loại guard tiêu chuẩn đã bàn ở trên để cho phép truy cập các route được bảo vệ.

<app-banner-courses-auth></app-banner-courses-auth>

#### Route đăng nhập <a id="login-route"></a>

Khi đã có strategy, giờ chúng ta có thể hiện thực một route `/auth/login` tối giản và áp dụng guard có sẵn để khởi động luồng passport-local.

Mở file `app.controller.ts` và thay nội dung của nó bằng đoạn sau:

```typescript
@@filename(app.controller)
import { Controller, Request, Post, UseGuards } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Controller()
export class AppController {
  @UseGuards(AuthGuard('local'))
  @Post('auth/login')
  async login(@Request() req: any) {
    return req.user;
  }
}
@@switch
import { Controller, Bind, Request, Post, UseGuards } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Controller()
export class AppController {
  @UseGuards(AuthGuard('local'))
  @Post('auth/login')
  @Bind(Request())
  async login(req) {
    return req.user;
  }
}
```

`AuthGuard('local')` tạo một guard gọi strategy Passport được đăng ký dưới tên `'local'`. Khi chúng ta kế thừa strategy passport-local, `@nestjs/passport` đã đăng ký `LocalStrategy` của chúng ta với Passport dưới tên mặc định đó, tên này đến từ package `passport-local`. Tên này cho guard biết strategy nào cần gọi khi ứng dụng có nhiều strategy Passport. Hiện chúng ta mới chỉ có một strategy, nhưng sẽ thêm strategy thứ hai ngay sau đây.

Để test route, hiện tại chúng ta sẽ cho `/auth/login` trả về người dùng. Điều này cũng minh họa một tính năng khác: guard lấy giá trị trả về từ method `validate()` và gán nó vào object `Request` dưới dạng `req.user`. Sau này, chúng ta sẽ thay nó bằng code tạo và trả về một JWT.

Vì đây là các API route, chúng ta sẽ test chúng bằng công cụ dòng lệnh phổ biến [cURL](https://curl.se/). Bạn có thể test với bất kỳ object `user` nào được hardcode trong `UsersService`.

```bash
$ # POST to /auth/login
$ curl -X POST http://localhost:3000/auth/login -d '{"username": "john", "password": "changeme"}' -H "Content-Type: application/json"
$ # result -> {"userId":1,"username":"john"}
```

Dù cách này hoạt động, việc truyền trực tiếp tên strategy cho `AuthGuard()` sẽ tạo ra các magic string trong codebase. Thay vào đó, chúng tôi khuyên bạn tạo class của riêng mình, như bên dưới:

```typescript
@@filename(auth/local-auth.guard)
import { Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class LocalAuthGuard extends AuthGuard('local') {}
```

Giờ hãy cập nhật route handler `/auth/login` để dùng `LocalAuthGuard` thay vào đó:

```typescript
@UseGuards(LocalAuthGuard)
@Post('auth/login')
async login(@Request() req: any) {
  return req.user;
}
```

#### Route đăng xuất <a id="logout-route"></a>

Để đăng xuất, bạn có thể tạo thêm một route gọi `req.logout()` để xóa session của người dùng. Cách này điển hình cho xác thực dựa trên session, nhưng không áp dụng cho JWT. Nó cần hỗ trợ session của Passport (`express-session` cùng với các middleware `passport.initialize()` và `passport.session()`), thứ mà recipe này không thiết lập. Từ Passport 0.6, `req.logout()` là bất đồng bộ và cần một callback, nên hãy bọc nó trong một promise:

```typescript
@UseGuards(LocalAuthGuard)
@Post('auth/logout')
async logout(@Request() req: any) {
  await new Promise<void>((resolve, reject) =>
    req.logout((err: any) => (err ? reject(err) : resolve())),
  );
}
```

#### Chức năng JWT <a id="jwt-functionality"></a>

Chúng ta đã sẵn sàng chuyển sang phần JWT của hệ thống xác thực. Hãy xem lại và tinh chỉnh các yêu cầu:

- Cho phép người dùng xác thực bằng username/password, trả về một JWT để dùng trong các lời gọi tiếp theo tới các endpoint API được bảo vệ. Chúng ta đã đi được một chặng dài để đáp ứng yêu cầu này. Để hoàn tất, chúng ta cần viết code phát hành JWT.
- Tạo các API route được bảo vệ dựa trên sự hiện diện của một JWT hợp lệ dưới dạng bearer token.

Cài thêm vài package để hỗ trợ các yêu cầu về JWT:

```bash
$ npm install --save @nestjs/jwt passport-jwt
$ npm install --save-dev @types/passport-jwt
```

Package [`@nestjs/jwt`](https://github.com/nestjs/jwt) là một package tiện ích giúp thao tác với JWT. Package `passport-jwt` là package Passport hiện thực JWT strategy, còn `@types/passport-jwt` cung cấp các định nghĩa type TypeScript cho nó.

Hãy xem kỹ hơn cách một request `POST /auth/login` được xử lý. Chúng ta đã gắn `LocalAuthGuard` cho route, guard này gọi strategy passport-local. Điều này có nghĩa là:

1. Route handler **chỉ được gọi nếu người dùng đã được validate**
2. Tham số `req` sẽ chứa một thuộc tính `user` (được Passport điền vào trong luồng xác thực passport-local)

Với điều này, giờ chúng ta có thể sinh một JWT thật và trả về nó từ route này. Để giữ các service được module hóa gọn gàng, chúng ta sẽ sinh JWT trong `AuthService`. Mở file `auth.service.ts` trong thư mục `auth`, inject `JwtService`, và thêm method `login()`, như bên dưới:

```typescript
@@filename(auth/auth.service)
import { Injectable } from '@nestjs/common';
import { UsersService } from '../users/users.service.js';
import { JwtService } from '@nestjs/jwt';

@Injectable()
export class AuthService {
  constructor(
    private usersService: UsersService,
    private jwtService: JwtService
  ) {}

  async validateUser(username: string, pass: string): Promise<any> {
    const user = await this.usersService.findOne(username);
    if (user && user.password === pass) {
      const { password, ...result } = user;
      return result;
    }
    return null;
  }

  async login(user: any) {
    const payload = { username: user.username, sub: user.userId };
    return {
      access_token: this.jwtService.sign(payload),
    };
  }
}

@@switch
import { Injectable, Dependencies } from '@nestjs/common';
import { UsersService } from '../users/users.service.js';
import { JwtService } from '@nestjs/jwt';

@Dependencies(UsersService, JwtService)
@Injectable()
export class AuthService {
  constructor(usersService, jwtService) {
    this.usersService = usersService;
    this.jwtService = jwtService;
  }

  async validateUser(username, pass) {
    const user = await this.usersService.findOne(username);
    if (user && user.password === pass) {
      const { password, ...result } = user;
      return result;
    }
    return null;
  }

  async login(user) {
    const payload = { username: user.username, sub: user.userId };
    return {
      access_token: this.jwtService.sign(payload),
    };
  }
}
```

`JwtService` từ `@nestjs/jwt` cung cấp một method `sign()` sinh JWT từ một tập con các thuộc tính của object `user`. Chúng ta trả về token dưới dạng một object đơn giản với một thuộc tính duy nhất `access_token`. Chúng ta dùng claim `sub` để chứa giá trị `userId`, để nhất quán với các chuẩn JWT.

Tiếp theo, cập nhật `AuthModule` để import các dependency mới và cấu hình `JwtModule`.

Trước tiên, tạo `constants.ts` trong thư mục `auth` và thêm đoạn code sau:

```typescript
@@filename(auth/constants)
export const jwtConstants = {
  secret: 'DO NOT USE THIS VALUE. INSTEAD, CREATE A COMPLEX SECRET AND KEEP IT SAFE OUTSIDE OF THE SOURCE CODE.',
};
@@switch
export const jwtConstants = {
  secret: 'DO NOT USE THIS VALUE. INSTEAD, CREATE A COMPLEX SECRET AND KEEP IT SAFE OUTSIDE OF THE SOURCE CODE.',
};
```

Chúng ta sẽ dùng nó để dùng chung key giữa bước ký và bước xác minh JWT.

> warning **Cảnh báo** **Đừng để lộ key này công khai**. Chúng tôi làm vậy ở đây để làm rõ code đang làm gì, nhưng trong một hệ thống production **bạn phải bảo vệ key này** bằng các biện pháp phù hợp, như một secrets vault, một biến môi trường, hoặc một configuration service.

Giờ hãy mở `auth.module.ts` trong thư mục `auth` và cập nhật nó thành như thế này:

```typescript
@@filename(auth/auth.module)
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { LocalStrategy } from './local.strategy.js';
import { UsersModule } from '../users/users.module.js';
import { PassportModule } from '@nestjs/passport';
import { JwtModule } from '@nestjs/jwt';
import { jwtConstants } from './constants.js';

@Module({
  imports: [
    UsersModule,
    PassportModule,
    JwtModule.register({
      secret: jwtConstants.secret,
      signOptions: { expiresIn: '60s' },
    }),
  ],
  providers: [AuthService, LocalStrategy],
  exports: [AuthService],
})
export class AuthModule {}
@@switch
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { LocalStrategy } from './local.strategy.js';
import { UsersModule } from '../users/users.module.js';
import { PassportModule } from '@nestjs/passport';
import { JwtModule } from '@nestjs/jwt';
import { jwtConstants } from './constants.js';

@Module({
  imports: [
    UsersModule,
    PassportModule,
    JwtModule.register({
      secret: jwtConstants.secret,
      signOptions: { expiresIn: '60s' },
    }),
  ],
  providers: [AuthService, LocalStrategy],
  exports: [AuthService],
})
export class AuthModule {}
```

Chúng ta cấu hình `JwtModule` bằng `register()`, truyền vào một configuration object. Xem [README của `@nestjs/jwt`](https://github.com/nestjs/jwt/blob/master/README.md) để biết thêm về `JwtModule` của Nest, và [tài liệu sử dụng `jsonwebtoken`](https://github.com/auth0/node-jsonwebtoken#usage) để biết chi tiết về các tùy chọn cấu hình có sẵn.

Giờ chúng ta có thể cập nhật route `/auth/login` để trả về một JWT.

```typescript
@@filename(app.controller)
import { Controller, Request, Post, UseGuards } from '@nestjs/common';
import { LocalAuthGuard } from './auth/local-auth.guard.js';
import { AuthService } from './auth/auth.service.js';

@Controller()
export class AppController {
  constructor(private authService: AuthService) {}

  @UseGuards(LocalAuthGuard)
  @Post('auth/login')
  async login(@Request() req: any) {
    return this.authService.login(req.user);
  }
}
@@switch
import { Controller, Dependencies, Bind, Request, Post, UseGuards } from '@nestjs/common';
import { LocalAuthGuard } from './auth/local-auth.guard.js';
import { AuthService } from './auth/auth.service.js';

@Dependencies(AuthService)
@Controller()
export class AppController {
  constructor(authService) {
    this.authService = authService;
  }

  @UseGuards(LocalAuthGuard)
  @Post('auth/login')
  @Bind(Request())
  async login(req) {
    return this.authService.login(req.user);
  }
}
```

Test lại các route bằng cURL. Bạn có thể dùng bất kỳ object `user` nào được hardcode trong `UsersService`.

```bash
$ # POST to /auth/login
$ curl -X POST http://localhost:3000/auth/login -d '{"username": "john", "password": "changeme"}' -H "Content-Type: application/json"
$ # result -> {"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
$ # Note: above JWT truncated
```

#### Hiện thực Passport JWT <a id="implementing-passport-jwt"></a>

Giờ chúng ta có thể giải quyết yêu cầu cuối cùng: bảo vệ các endpoint bằng cách yêu cầu một JWT hợp lệ trên request. Passport cũng giúp được ở đây, với strategy [passport-jwt](https://github.com/mikenicholson/passport-jwt) để bảo vệ các RESTful endpoint bằng JSON Web Token. Bắt đầu bằng việc tạo một file tên `jwt.strategy.ts` trong thư mục `auth` và thêm đoạn code sau:

```typescript
@@filename(auth/jwt.strategy)
import { ExtractJwt, Strategy } from 'passport-jwt';
import { PassportStrategy } from '@nestjs/passport';
import { Injectable } from '@nestjs/common';
import { jwtConstants } from './constants.js';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: jwtConstants.secret,
    });
  }

  async validate(payload: any) {
    return { userId: payload.sub, username: payload.username };
  }
}
@@switch
import { ExtractJwt, Strategy } from 'passport-jwt';
import { PassportStrategy } from '@nestjs/passport';
import { Injectable } from '@nestjs/common';
import { jwtConstants } from './constants.js';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: jwtConstants.secret,
    });
  }

  async validate(payload) {
    return { userId: payload.sub, username: payload.username };
  }
}
```

Với `JwtStrategy`, chúng ta đã làm theo cùng công thức mô tả trước đó cho mọi strategy Passport. Strategy này cần một số bước khởi tạo, nên chúng ta truyền một options object trong lời gọi `super()`. Xem [tùy chọn strategy của passport-jwt](https://github.com/mikenicholson/passport-jwt#configure-strategy) để biết danh sách đầy đủ. Trong trường hợp của chúng ta, các tùy chọn này là:

- `jwtFromRequest`: cung cấp cách lấy JWT ra từ `Request`. Chúng ta dùng cách tiêu chuẩn là cung cấp một bearer token trong header `Authorization` của các API request. Xem [lấy JWT từ request](https://github.com/mikenicholson/passport-jwt#extracting-the-jwt-from-the-request) để biết các lựa chọn khác.
- `ignoreExpiration`: để rõ ràng, chúng ta đặt giá trị mặc định `false`, giao trách nhiệm đảm bảo JWT chưa hết hạn cho module Passport. Nếu route của chúng ta nhận một JWT đã hết hạn, request bị từ chối với response `401 Unauthorized`.
- `secretOrKey`: chúng ta dùng lựa chọn tiện lợi là cung cấp một secret đối xứng để ký token. Các lựa chọn khác, như một public key mã hóa PEM, có thể phù hợp hơn cho ứng dụng production (xem [tùy chọn strategy của passport-jwt](https://github.com/mikenicholson/passport-jwt#configure-strategy) để biết thêm thông tin). Trong mọi trường hợp, như đã cảnh báo trước đó, **đừng để lộ secret này công khai**.

Method `validate()` đáng được bàn thêm một chút. Với JWT strategy, trước tiên Passport xác minh chữ ký của JWT và decode JSON. Sau đó nó gọi method `validate()` của chúng ta, truyền JSON đã decode làm tham số duy nhất. Dựa trên cách việc ký JWT hoạt động, **chúng ta được đảm bảo nhận được một token hợp lệ** mà chúng ta đã ký và phát hành trước đó cho một người dùng hợp lệ.

Do đó, callback `validate()` của chúng ta rất đơn giản: nó trả về một object chứa các thuộc tính `userId` và `username`. Hãy nhớ rằng giá trị trả về từ `validate()` trở thành thuộc tính `user` của object `Request`.

Bạn cũng có thể trả về một mảng, trong đó giá trị đầu tiên trở thành object `user` và giá trị thứ hai trở thành object `authInfo` (`req.authInfo`).

Cách này cũng chừa chỗ (có thể gọi là các 'hook') để chèn thêm logic nghiệp vụ khác vào quy trình. Ví dụ, chúng ta có thể tra cứu database trong method `validate()` để lấy thêm thông tin về người dùng, dẫn tới một object `user` phong phú hơn có sẵn trong `Request`. Đây cũng là nơi chúng ta có thể quyết định validate token thêm, như tra cứu `userId` trong danh sách token bị thu hồi, cho phép chúng ta thực hiện việc thu hồi token. Mô hình mà chúng ta hiện thực trong code mẫu ở đây là một mô hình "stateless JWT" nhanh, trong đó mỗi lời gọi API được phân quyền ngay lập tức dựa trên sự hiện diện của một JWT hợp lệ, và một chút thông tin về bên yêu cầu (`userId` và `username` của nó) có sẵn trong pipeline của Request.

Thêm `JwtStrategy` mới làm provider trong `AuthModule`:

```typescript
@@filename(auth/auth.module)
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { LocalStrategy } from './local.strategy.js';
import { JwtStrategy } from './jwt.strategy.js';
import { UsersModule } from '../users/users.module.js';
import { PassportModule } from '@nestjs/passport';
import { JwtModule } from '@nestjs/jwt';
import { jwtConstants } from './constants.js';

@Module({
  imports: [
    UsersModule,
    PassportModule,
    JwtModule.register({
      secret: jwtConstants.secret,
      signOptions: { expiresIn: '60s' },
    }),
  ],
  providers: [AuthService, LocalStrategy, JwtStrategy],
  exports: [AuthService],
})
export class AuthModule {}
@@switch
import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { LocalStrategy } from './local.strategy.js';
import { JwtStrategy } from './jwt.strategy.js';
import { UsersModule } from '../users/users.module.js';
import { PassportModule } from '@nestjs/passport';
import { JwtModule } from '@nestjs/jwt';
import { jwtConstants } from './constants.js';

@Module({
  imports: [
    UsersModule,
    PassportModule,
    JwtModule.register({
      secret: jwtConstants.secret,
      signOptions: { expiresIn: '60s' },
    }),
  ],
  providers: [AuthService, LocalStrategy, JwtStrategy],
  exports: [AuthService],
})
export class AuthModule {}
```

Bằng cách import cùng secret đã dùng khi ký JWT, chúng ta đảm bảo giai đoạn **xác minh** do Passport thực hiện và giai đoạn **ký** thực hiện trong `AuthService` dùng chung một secret.

Cuối cùng, chúng ta định nghĩa class `JwtAuthGuard` kế thừa `AuthGuard` có sẵn:

```typescript
@@filename(auth/jwt-auth.guard)
import { Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {}
```

#### Hiện thực route được bảo vệ và guard của JWT strategy <a id="implement-protected-route-and-jwt-strategy-guards"></a>

Giờ chúng ta có thể hiện thực route được bảo vệ và guard đi kèm của nó.

Mở file `app.controller.ts` và cập nhật nó như bên dưới:

```typescript
@@filename(app.controller)
import { Controller, Get, Request, Post, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from './auth/jwt-auth.guard.js';
import { LocalAuthGuard } from './auth/local-auth.guard.js';
import { AuthService } from './auth/auth.service.js';

@Controller()
export class AppController {
  constructor(private authService: AuthService) {}

  @UseGuards(LocalAuthGuard)
  @Post('auth/login')
  async login(@Request() req: any) {
    return this.authService.login(req.user);
  }

  @UseGuards(JwtAuthGuard)
  @Get('profile')
  getProfile(@Request() req: any) {
    return req.user;
  }
}
@@switch
import { Controller, Dependencies, Bind, Get, Request, Post, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from './auth/jwt-auth.guard.js';
import { LocalAuthGuard } from './auth/local-auth.guard.js';
import { AuthService } from './auth/auth.service.js';

@Dependencies(AuthService)
@Controller()
export class AppController {
  constructor(authService) {
    this.authService = authService;
  }

  @UseGuards(LocalAuthGuard)
  @Post('auth/login')
  @Bind(Request())
  async login(req) {
    return this.authService.login(req.user);
  }

  @UseGuards(JwtAuthGuard)
  @Get('profile')
  @Bind(Request())
  getProfile(req) {
    return req.user;
  }
}
```

Một lần nữa, chúng ta áp dụng một `AuthGuard`, lần này là guard gọi strategy được đăng ký dưới tên mặc định của passport-jwt, `jwt`. Khi route `GET /profile` được gọi, guard gọi strategy passport-jwt đã được cấu hình tùy chỉnh của chúng ta, validate JWT, và gán thuộc tính `user` vào object `Request`.

Đảm bảo ứng dụng đang chạy, và test các route bằng cURL.

```bash
$ # GET /profile
$ curl http://localhost:3000/profile
$ # result -> {"message":"Unauthorized","statusCode":401}

$ # POST /auth/login
$ curl -X POST http://localhost:3000/auth/login -d '{"username": "john", "password": "changeme"}' -H "Content-Type: application/json"
$ # result -> {"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2Vybm... }

$ # GET /profile using access_token returned from previous step as bearer code
$ curl http://localhost:3000/profile -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2Vybm..."
$ # result -> {"userId":1,"username":"john"}
```

Trong `AuthModule`, chúng ta đã cấu hình JWT hết hạn sau 60 giây. Con số này có lẽ quá ngắn cho một ứng dụng thực tế, và các chi tiết về hết hạn và làm mới token nằm ngoài phạm vi bài viết này. Chúng ta chọn nó để minh họa một đặc tính quan trọng của JWT và strategy passport-jwt: nếu bạn chờ 60 giây sau khi xác thực rồi mới gửi request `GET /profile`, bạn sẽ nhận response `401 Unauthorized`. Passport tự động kiểm tra thời gian hết hạn của JWT, nên ứng dụng của bạn không phải làm việc đó.

Đến đây là hoàn tất phần hiện thực xác thực bằng JWT. Các client JavaScript (như ứng dụng Angular, React hay Vue) và các client khác giờ có thể xác thực và giao tiếp an toàn với API server của chúng ta.

#### Mở rộng guard <a id="extending-guards"></a>

Trong hầu hết các trường hợp, dùng class `AuthGuard` được cung cấp sẵn là đủ. Tuy nhiên, bạn có thể muốn mở rộng việc xử lý lỗi mặc định hoặc logic xác thực. Để làm vậy, hãy kế thừa class có sẵn và override các method của nó trong một subclass.

```typescript
import {
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    // Add your custom authentication logic here
    // for example, call super.logIn(request) to establish a session.
    return super.canActivate(context);
  }

  handleRequest(err: any, user: any, info: any) {
    // You can throw an exception based on either "info" or "err" arguments
    if (err || !user) {
      throw err || new UnauthorizedException();
    }
    return user;
  }
}
```

Ngoài việc mở rộng xử lý lỗi và logic xác thực mặc định, bạn có thể cho việc xác thực đi qua một chuỗi strategy. Strategy đầu tiên thành công, redirect hoặc báo lỗi sẽ dừng chuỗi. Các lần xác thực thất bại lần lượt đi qua từng strategy, và việc xác thực chỉ thất bại nếu mọi strategy đều thất bại.

```typescript
export class JwtAuthGuard extends AuthGuard(['strategy_jwt_1', 'strategy_jwt_2', '...']) { ... }
```
#### Bật xác thực ở phạm vi global <a id="enable-authentication-globally"></a>

Nếu phần lớn endpoint của bạn nên được bảo vệ mặc định, bạn có thể đăng ký authentication guard làm một [global guard](/guards#binding-guards). Thay vì dùng decorator `@UseGuards()` trên từng controller, khi đó bạn đánh dấu các route cần công khai.

Trước tiên, đăng ký `JwtAuthGuard` làm global guard bằng cấu trúc sau (trong bất kỳ module nào):

```typescript
providers: [
  {
    provide: APP_GUARD,
    useClass: JwtAuthGuard,
  },
],
```

Khi đã có cấu hình này, Nest sẽ tự động gắn `JwtAuthGuard` vào mọi endpoint.

Tiếp theo, cung cấp một cơ chế để khai báo route là công khai. Để làm vậy, hãy tạo một custom decorator bằng decorator factory function `SetMetadata`.

```typescript
import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
```

File ở trên export hai hằng số: metadata key của chúng ta, tên `IS_PUBLIC_KEY`, và chính decorator mới, tên `Public` (bạn có thể đặt tên nó là `SkipAuth`, `AllowAnon`, hoặc bất cứ tên gì phù hợp với project).

Khi đã có custom decorator `@Public()`, bạn có thể dùng nó để gắn cho bất kỳ method nào, như sau:

```typescript
@Public()
@Get()
findAll() {
  return [];
}
```

Cuối cùng, `JwtAuthGuard` cần trả về `true` khi tìm thấy metadata `"isPublic"`. Để làm vậy, hãy dùng class `Reflector` (xem [kết hợp tất cả lại](/guards#putting-it-all-together) trong chương Guard).

```typescript
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  constructor(private reflector: Reflector) {
    super();
  }

  canActivate(context: ExecutionContext) {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) {
      return true;
    }
    return super.canActivate(context);
  }
}
```

#### Strategy request-scoped <a id="request-scoped-strategies"></a>

API của Passport dựa trên việc đăng ký strategy với instance global của library. Vì vậy, strategy không được thiết kế để có tùy chọn phụ thuộc request hay được khởi tạo động theo từng request (xem [injection scope](/fundamentals/injection-scopes) để tìm hiểu thêm về provider request-scoped). Nếu bạn cấu hình strategy là request-scoped, Nest sẽ không bao giờ khởi tạo nó, vì nó không gắn với route cụ thể nào, và không có cách nào xác định strategy "request-scoped" nào nên chạy cho một request cho trước.

Tuy nhiên, bạn có thể resolve động các provider request-scoped bên trong strategy. Để làm vậy, hãy dùng tính năng [module reference](/fundamentals/module-ref).

Trước tiên, mở file `local.strategy.ts` và inject `ModuleRef` theo cách thông thường:

```typescript
constructor(private moduleRef: ModuleRef) {
  super({
    passReqToCallback: true,
  });
}
```

> info **Gợi ý** Class `ModuleRef` được import từ package `@nestjs/core`.

Hãy đảm bảo đặt thuộc tính cấu hình `passReqToCallback` thành `true`, như ở trên.

Ở bước tiếp theo, instance request được dùng để lấy định danh context hiện tại, thay vì sinh một định danh mới (xem [lấy sub-tree hiện tại](/fundamentals/module-ref#getting-current-sub-tree) để tìm hiểu thêm về request context).

Giờ, bên trong method `validate()` của class `LocalStrategy`, hãy dùng method `getByRequest()` của class `ContextIdFactory` để tạo một context id dựa trên object request, và truyền nó cho lời gọi `resolve()`:

```typescript
async validate(
  request: Request,
  username: string,
  password: string,
) {
  const contextId = ContextIdFactory.getByRequest(request);
  // "AuthService" is a request-scoped provider
  const authService = await this.moduleRef.resolve(AuthService, contextId);
  ...
}
```

Trong ví dụ ở trên, method `resolve()` trả về một cách bất đồng bộ instance request-scoped của provider `AuthService` (giả sử `AuthService` được đánh dấu là provider request-scoped).

#### Tùy chỉnh Passport <a id="customize-passport"></a>

Để tùy chỉnh cách các guard gọi Passport, hãy truyền tùy chọn cho method `PassportModule.register()`. Ngoài `defaultStrategy` và `property`, hai tùy chọn mà `@nestjs/passport` tự dùng, các tùy chọn này được truyền cho lời gọi `authenticate()` của Passport, nên các tùy chọn có sẵn phụ thuộc vào strategy đang được hiện thực. Ví dụ:

```typescript
PassportModule.register({ session: true });
```

Bạn cũng có thể cấu hình một strategy bằng cách truyền một options object cho `super()` trong constructor của nó. Ví dụ, với local strategy:

```typescript
constructor(private authService: AuthService) {
  super({
    usernameField: 'email',
    passwordField: 'password',
  });
}
```

Xem [website Passport](http://www.passportjs.org/docs/oauth/) chính thức để biết các tên thuộc tính có sẵn.

#### Strategy có tên <a id="named-strategies"></a>

Khi hiện thực một strategy, bạn có thể đặt tên cho nó bằng cách truyền một tham số thứ hai cho hàm `PassportStrategy()`. Nếu không, mỗi strategy dùng tên mặc định của nó (ví dụ `'jwt'` cho JWT strategy):

```typescript
export class JwtStrategy extends PassportStrategy(Strategy, 'myjwt')
```

Sau đó bạn tham chiếu tới nó bằng một decorator như `@UseGuards(AuthGuard('myjwt'))`.

#### GraphQL

Để dùng một `AuthGuard` với [GraphQL](/graphql/quick-start), hãy kế thừa class `AuthGuard` có sẵn và override method `getRequest()`.

```typescript
@Injectable()
export class GqlAuthGuard extends AuthGuard('jwt') {
  getRequest(context: ExecutionContext) {
    const ctx = GqlExecutionContext.create(context);
    return ctx.getContext().req;
  }
}
```

Để lấy người dùng đang được xác thực trong GraphQL resolver, hãy định nghĩa một decorator `@CurrentUser()`:

```typescript
import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { GqlExecutionContext } from '@nestjs/graphql';

export const CurrentUser = createParamDecorator(
  (data: unknown, context: ExecutionContext) => {
    const ctx = GqlExecutionContext.create(context);
    return ctx.getContext().req.user;
  },
);
```

Để dùng decorator trong resolver, hãy đưa nó vào làm tham số của query hoặc mutation:

```typescript
@Query(() => User)
@UseGuards(GqlAuthGuard)
whoAmI(@CurrentUser() user: User) {
  return this.usersService.findById(user.id);
}
```

Với strategy passport-local, bạn cũng cần thêm các argument của GraphQL context vào body của request để Passport có thể truy cập chúng khi validate. Nếu không, bạn sẽ nhận lỗi `Unauthorized`.

```typescript
@Injectable()
export class GqlLocalAuthGuard extends AuthGuard('local') {
  getRequest(context: ExecutionContext) {
    const gqlExecutionContext = GqlExecutionContext.create(context);
    const gqlContext = gqlExecutionContext.getContext();
    const gqlArgs = gqlExecutionContext.getArgs();

    gqlContext.req.body = { ...gqlContext.req.body, ...gqlArgs };
    return gqlContext.req;
  }
}
```
