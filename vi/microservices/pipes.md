### Pipe

Pipe của microservice hoạt động giống như [pipe thông thường](/pipes). Khác biệt duy nhất là chúng nên throw `RpcException` thay vì `HttpException`. Trừ khi có một custom exception filter xử lý nó, một `HttpException` được throw trong lúc xử lý message sẽ tới client dưới dạng một message chung chung `Internal server error`.

> info **Gợi ý** Class `RpcException` được cung cấp từ package `@nestjs/microservices`.

#### Gắn pipe <a id="binding-pipes"></a>

Ví dụ sau dùng một pipe cấp method được khởi tạo thủ công. Tùy chọn `exceptionFactory` khiến `ValidationPipe` throw một `RpcException` thay vì `BadRequestException` mặc định của nó. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng pipe cấp controller (tức là đặt decorator `@UsePipes()` trước class controller).

```typescript
@@filename()
@UsePipes(new ValidationPipe({ exceptionFactory: (errors) => new RpcException(errors) }))
@MessagePattern({ cmd: 'sum' })
accumulate(data: number[]): number {
  return (data || []).reduce((a, b) => a + b);
}
@@switch
@UsePipes(new ValidationPipe({ exceptionFactory: (errors) => new RpcException(errors) }))
@MessagePattern({ cmd: 'sum' })
accumulate(data) {
  return (data || []).reduce((a, b) => a + b);
}
```

Decorator `@Payload()` cũng nhận tùy chọn `schema`, cho phép `StandardSchemaValidationPipe` (được export từ `@nestjs/common`) validate payload theo một [Standard Schema](/application/validation#schema-based-validation) (ví dụ một schema Zod). Hãy cấu hình tùy chọn `exceptionFactory` của nó theo cùng cách, để lỗi validation được throw dưới dạng `RpcException`:

```typescript
@@filename()
@UsePipes(new StandardSchemaValidationPipe({ exceptionFactory: (issues) => new RpcException(issues) }))
@MessagePattern({ cmd: 'sum' })
accumulate(@Payload({ schema: z.array(z.number()) }) data: number[]): number {
  return data.reduce((a, b) => a + b, 0);
}
@@switch
@UsePipes(new StandardSchemaValidationPipe({ exceptionFactory: (issues) => new RpcException(issues) }))
@Bind(Payload({ schema: z.array(z.number()) }))
@MessagePattern({ cmd: 'sum' })
accumulate(data) {
  return data.reduce((a, b) => a + b, 0);
}
```

> info **Gợi ý** Global pipe được đăng ký trên ứng dụng HTTP chính không áp dụng cho các microservice được kết nối vào một [ứng dụng hybrid](/faq/hybrid-application) trừ khi bạn đặt tùy chọn `inheritAppConfig`. Xem [dùng chung cấu hình](/faq/hybrid-application#sharing-configuration).
