### HTTP adapter

Đôi khi, bạn có thể cần truy cập HTTP server bên dưới, từ bên trong application context của Nest hoặc từ bên ngoài nó.

Mọi instance HTTP server hoặc library gốc (riêng của nền tảng) (ví dụ Express hay Fastify) đều được bọc trong một **adapter**. Adapter được đăng ký như một provider có sẵn ở phạm vi global, nên bạn có thể lấy nó từ application context hoặc inject nó vào các provider khác.

#### Cách làm bên ngoài application context <a id="outside-application-context-strategy"></a>

Để lấy tham chiếu tới `HttpAdapter` từ bên ngoài application context, hãy gọi method `getHttpAdapter()`:

```typescript
@@filename()
const app = await NestFactory.create(AppModule);
const httpAdapter = app.getHttpAdapter();
```

#### Dưới dạng injectable <a id="as-injectable"></a>

Để lấy tham chiếu tới `HttpAdapterHost` từ bên trong application context, hãy inject nó như mọi provider khác (ví dụ dùng constructor injection):

```typescript
@@filename()
export class CatsService {
  constructor(private adapterHost: HttpAdapterHost) {}
}
@@switch
@Dependencies(HttpAdapterHost)
export class CatsService {
  constructor(adapterHost) {
    this.adapterHost = adapterHost;
  }
}
```

> info **Gợi ý** `HttpAdapterHost` được import từ package `@nestjs/core`.

`HttpAdapterHost` **không phải** là một `HttpAdapter` thực sự. Để lấy instance `HttpAdapter` thực sự, hãy đọc thuộc tính `httpAdapter` của nó:

```typescript
const adapterHost = app.get(HttpAdapterHost);
const httpAdapter = adapterHost.httpAdapter;
```

`httpAdapter` là instance HTTP adapter bọc framework bên dưới. Nó là một instance của `ExpressAdapter`, `FastifyAdapter` hoặc `NodeAdapter` (tất cả đều kế thừa `AbstractHttpAdapter`).

Object adapter cung cấp một số method để tương tác với HTTP server. Để truy cập trực tiếp instance của library (ví dụ instance Express), hãy gọi method `getInstance()`:

```typescript
const instance = httpAdapter.getInstance();
```

#### Event lắng nghe <a id="listening-event"></a>

Để chạy code khi server bắt đầu lắng nghe các request đi vào, hãy subscribe stream `listen$`:

```typescript
this.httpAdapterHost.listen$.subscribe(() =>
  console.log('HTTP server is listening'),
);
```

`HttpAdapterHost` cũng cung cấp một thuộc tính boolean `listening` cho biết server hiện có đang lắng nghe hay không:

```typescript
if (this.httpAdapterHost.listening) {
  console.log('HTTP server is listening');
}
```
