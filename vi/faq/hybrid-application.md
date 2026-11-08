### Ứng dụng hybrid

Một ứng dụng hybrid lắng nghe request từ hai hoặc nhiều nguồn khác nhau. Nó có thể kết hợp một HTTP server với một microservice listener, hoặc kết hợp nhiều microservice listener khác nhau. Method `createMicroservice()` không hỗ trợ nhiều server, nên trong trường hợp này bạn tự tạo và khởi động từng microservice. Để làm vậy, hãy kết nối các instance `INestMicroservice` vào instance `INestApplication` bằng method `connectMicroservice()`.

```typescript
const app = await NestFactory.create(AppModule);
const microservice = app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.TCP,
});

await app.startAllMicroservices();
await app.listen(3001);
```

> info **Gợi ý** Method `app.listen(port)` khởi động một HTTP server trên port được chỉ định. Nếu ứng dụng của bạn không xử lý HTTP request, hãy dùng method `app.init()` thay vào đó.

> warning **Chú ý** Thứ tự của các lời gọi này là quan trọng. Với `await app.startAllMicroservices()` đứng trước (như ở trên), các microservice bắt đầu tiêu thụ message **trước khi** các lifecycle hook của ứng dụng (như `onModuleInit` và `onApplicationBootstrap`) hoàn tất. Hãy gọi `app.listen()` (hoặc `app.init()`) trước `startAllMicroservices()` nếu các handler của bạn không được nhận message cho tới khi mọi module đã khởi tạo xong hoàn toàn.

Để kết nối nhiều instance microservice, hãy gọi `connectMicroservice()` một lần cho mỗi microservice:

```typescript
const app = await NestFactory.create(AppModule);
// microservice #1
const microserviceTcp = app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.TCP,
  options: {
    port: 3002,
  },
});
// microservice #2
const microserviceRedis = app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.REDIS,
  options: {
    host: 'localhost',
    port: 6379,
  },
});

await app.startAllMicroservices();
await app.listen(3001);
```

Trong một ứng dụng hybrid có nhiều microservice, bạn có thể gắn `@MessagePattern()` với một transport strategy duy nhất (ví dụ NATS) bằng cách truyền một tham số thứ hai xác định transport. Với các strategy có sẵn, đây là một giá trị của enum `Transport`; với một [custom transporter](/microservices/custom-transport), đó là symbol `transportId` của class server của nó.

```typescript
@@filename()
@MessagePattern('time.us.*', Transport.NATS)
getDate(@Payload() data: number[], @Ctx() context: NatsContext) {
  console.log(`Subject: ${context.getSubject()}`); // e.g. "time.us.east"
  return new Date().toLocaleTimeString(...);
}
@MessagePattern({ cmd: 'time.us' }, Transport.TCP)
getTCPDate(@Payload() data: number[]) {
  return new Date().toLocaleTimeString(...);
}
@MessagePattern('topic.time.us', XYZServer.Transport) // XYZServer is a custom transporter
getXYZDate(@Payload() data: number[]) {
  return new Date().toLocaleTimeString(...);
}
@@switch
@Bind(Payload(), Ctx())
@MessagePattern('time.us.*', Transport.NATS)
getDate(data, context) {
  console.log(`Subject: ${context.getSubject()}`); // e.g. "time.us.east"
  return new Date().toLocaleTimeString(...);
}
@Bind(Payload(), Ctx())
@MessagePattern({ cmd: 'time.us' }, Transport.TCP)
getTCPDate(data, context) {
  return new Date().toLocaleTimeString(...);
}

@Bind(Payload())
@MessagePattern('topic.time.us', XYZServer.Transport)
getXYZDate(data) {
  return new Date().toLocaleTimeString(...);
}
```

> info **Gợi ý** `@Payload()`, `@Ctx()`, `Transport` và `NatsContext` được import từ `@nestjs/microservices`. `XYZServer.Transport` ở đây đại diện cho symbol `transportId` mà custom transporter cung cấp.

#### Dùng chung cấu hình <a id="sharing-configuration"></a>

Mặc định, các microservice được kết nối không kế thừa các pipe, interceptor, guard và filter global được cấu hình cho ứng dụng chính (dựa trên HTTP). Điều này áp dụng cho cả các enhancer được đăng ký bằng các method `useGlobal*()` lẫn những enhancer được đăng ký làm provider với các token `APP_PIPE`, `APP_INTERCEPTOR`, `APP_GUARD` và `APP_FILTER`.
Để kế thừa cấu hình này, hãy đặt thuộc tính `inheritAppConfig` trong options object được truyền làm tham số thứ hai của `connectMicroservice()`:

```typescript
const microservice = app.connectMicroservice<MicroserviceOptions>(
  {
    transport: Transport.TCP,
  },
  { inheritAppConfig: true },
);
```

> info **Gợi ý** Một microservice được kết nối đăng ký các message handler của nó ngay khi `connectMicroservice()` được gọi. Khi bạn dùng `inheritAppConfig`, hãy gọi `app.useGlobalPipes()`, `app.useGlobalGuards()` và các method `useGlobal*()` khác **trước** `connectMicroservice()`, nếu không các enhancer mà chúng đăng ký sẽ không áp dụng cho các handler của microservice.
