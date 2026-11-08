### Session

**HTTP session** lưu thông tin về người dùng qua nhiều request, điều này đặc biệt hữu ích cho các ứng dụng [MVC](/http/mvc).

#### Dùng với Express (mặc định) <a id="use-with-express-default"></a>

Đầu tiên, cài package [express-session](https://github.com/expressjs/session) (và các type của nó, với người dùng TypeScript):

```shell
$ npm i express-session
$ npm i -D @types/express-session
```

Sau khi cài xong, áp dụng middleware `express-session` làm global middleware (ví dụ trong file `main.ts`):

```typescript
import session from 'express-session';
// somewhere in your initialization file
app.use(
  session({
    secret: 'my-secret',
    resave: false,
    saveUninitialized: false,
  }),
);
```

> warning **Chú ý** Storage session phía server mặc định cố ý không được thiết kế cho môi trường production. Nó bị rò rỉ bộ nhớ trong hầu hết trường hợp, không mở rộng được quá một process, và chỉ dành cho debug và phát triển. Đọc thêm trong [repository express-session](https://github.com/expressjs/session).

`secret` được dùng để ký cookie session ID. Nó có thể là một chuỗi (một secret duy nhất) hoặc một mảng secret. Nếu bạn cung cấp một mảng, chỉ phần tử đầu tiên được dùng để ký cookie session ID, trong khi mọi phần tử đều được xét khi xác minh chữ ký trong request. Secret không nên dễ đoán; một chuỗi ký tự ngẫu nhiên là tốt nhất.

Bật tùy chọn `resave` sẽ buộc session được lưu lại vào session store, kể cả khi session không hề bị thay đổi trong request. Giá trị mặc định là `true`, nhưng việc dựa vào giá trị mặc định đã bị deprecate vì giá trị mặc định sẽ thay đổi trong tương lai.

Tương tự, bật tùy chọn `saveUninitialized` sẽ buộc một session "chưa khởi tạo" được lưu vào store. Một session là chưa khởi tạo khi nó mới được tạo nhưng chưa bị thay đổi. Chọn `false` hữu ích để implement session đăng nhập, giảm dung lượng lưu trữ trên server, hoặc tuân thủ các luật yêu cầu xin phép trước khi đặt cookie. Chọn `false` cũng giúp tránh race condition khi một client gửi nhiều request song song mà chưa có session (xem [tài liệu về `saveUninitialized`](https://github.com/expressjs/session#saveuninitialized)).

Middleware `session` nhận vài tùy chọn khác. Đọc thêm về chúng trong [tài liệu API của express-session](https://github.com/expressjs/session#options).

> info **Gợi ý** Tùy chọn `cookie.secure: true` được khuyên dùng. Tuy nhiên, nó yêu cầu website có HTTPS, vì secure cookie chỉ được gửi qua HTTPS. Nếu `secure` được đặt và bạn truy cập site qua HTTP, cookie sẽ không được đặt. Nếu server Node.js của bạn chạy đằng sau một proxy và bạn dùng `secure: true`, bạn cần đặt `"trust proxy"` trong Express.

Khi đã có những thứ trên, bạn có thể đặt và đọc giá trị session từ bên trong route handler, như sau:

```typescript
@Get()
findAll(@Req() request: Request) {
  request.session.visits = request.session.visits ? request.session.visits + 1 : 1;
}
```

> info **Gợi ý** Decorator `@Req()` được import từ package `@nestjs/common`, còn `Request` được import từ package `express`.

Cách khác là dùng decorator `@Session()` để lấy session object từ request, như sau:

```typescript
@Get()
findAll(@Session() session: Record<string, any>) {
  session.visits = session.visits ? session.visits + 1 : 1;
}
```

> info **Gợi ý** Decorator `@Session()` được import từ package `@nestjs/common`.

#### Dùng với Fastify <a id="use-with-fastify"></a>

Đầu tiên, cài package cần thiết:

```shell
$ npm i @fastify/secure-session
```

Sau khi cài xong, đăng ký plugin `@fastify/secure-session`:

```typescript
import secureSession from '@fastify/secure-session';

// somewhere in your initialization file
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter(),
);
await app.register(secureSession, {
  secret: 'averylogphrasebiggerthanthirtytwochars',
  salt: 'mq9hDxBVDbspDR6n',
});
```

> info **Gợi ý** Bạn cũng có thể [sinh trước một key](https://github.com/fastify/fastify-secure-session) hoặc dùng [xoay vòng key](https://github.com/fastify/fastify-secure-session#using-keys-with-key-rotation).

Đọc thêm về các tùy chọn có sẵn trong [repository @fastify/secure-session](https://github.com/fastify/fastify-secure-session).

Khi đã có những thứ trên, bạn có thể đặt và đọc giá trị session từ bên trong route handler, như sau:

```typescript
@Get()
findAll(@Req() request: FastifyRequest) {
  const visits = request.session.get('visits');
  request.session.set('visits', visits ? visits + 1 : 1);
}
```

Cách khác là dùng decorator `@Session()` để lấy session object từ request, như sau:

```typescript
@Get()
findAll(@Session() session: secureSession.Session) {
  const visits = session.get('visits');
  session.set('visits', visits ? visits + 1 : 1);
}
```

> info **Gợi ý** Decorator `@Session()` được import từ package `@nestjs/common`, còn `secureSession.Session` đến từ package `@fastify/secure-session` (câu import: `import * as secureSession from '@fastify/secure-session'`).
