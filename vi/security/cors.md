### CORS

Cross-origin resource sharing (CORS) là một cơ chế cho phép request resource từ một domain khác. Bên dưới, Nest dùng package [cors](https://github.com/expressjs/cors) của Express hoặc package [@fastify/cors](https://github.com/fastify/fastify-cors) của Fastify, tùy theo nền tảng bên dưới. Các package này cung cấp nhiều tùy chọn mà bạn có thể tùy chỉnh theo yêu cầu.

#### Bắt đầu <a id="getting-started"></a>

Để bật CORS, gọi method `enableCors()` trên object ứng dụng Nest.

```typescript
const app = await NestFactory.create(AppModule);
app.enableCors();
await app.listen(process.env.PORT ?? 3000);
```

Method `enableCors()` nhận một configuration object tùy chọn. Các thuộc tính có sẵn của nó được mô tả trong tài liệu chính thức [CORS configuration options](https://github.com/expressjs/cors#configuration-options). Cách khác là truyền một [hàm callback](https://github.com/expressjs/cors#customizing-cors-settings-dynamically-per-request) tính toán configuration object cho mỗi request.

Bạn cũng có thể bật CORS thông qua options object của method `create()`. Đặt thuộc tính `cors` thành `true` để bật CORS với thiết lập mặc định, hoặc truyền một [CORS configuration object](https://github.com/expressjs/cors#configuration-options) hay [hàm callback](https://github.com/expressjs/cors#customizing-cors-settings-dynamically-per-request) làm giá trị của thuộc tính `cors` để tùy chỉnh hành vi.

```typescript
const app = await NestFactory.create(AppModule, { cors: true });
await app.listen(process.env.PORT ?? 3000);
```

#### Các method được cho phép mặc định <a id="default-allowed-methods"></a>

Hai package không có cùng giá trị mặc định, nên `enableCors()` không kèm tùy chọn sẽ không trả về cùng `Access-Control-Allow-Methods` trên cả hai nền tảng. Package [cors](https://github.com/expressjs/cors) của Express trả lời `GET,HEAD,PUT,PATCH,POST,DELETE`, trong khi [@fastify/cors](https://github.com/fastify/fastify-cors) chỉ trả lời các [method nằm trong safelist của CORS](https://fetch.spec.whatwg.org/#methods): `GET,HEAD,POST`.

> warning **Cảnh báo** Trên Fastify, một request `PUT`, `PATCH` hoặc `DELETE` cross-origin sẽ bị từ chối ngay ở bước preflight trừ khi bạn tự liệt kê method đó. Cùng code ứng dụng đó vẫn chạy được trên Express.

Cả hai package đều đọc cùng tùy chọn `methods`, nên hãy định nghĩa nó một cách tường minh mỗi khi API của bạn được gọi từ origin khác với method nằm ngoài safelist. Tùy chọn này được chấp nhận bởi cả `enableCors()` lẫn thuộc tính `cors` trong options object của `create()`.

```typescript
app.enableCors({
  methods: ['GET', 'HEAD', 'PUT', 'PATCH', 'POST', 'DELETE'],
});
```
