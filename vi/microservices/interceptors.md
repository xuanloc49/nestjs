### Interceptor

Interceptor của microservice hoạt động giống như [interceptor thông thường](/interceptors). Ví dụ sau dùng một interceptor cấp method được khởi tạo thủ công. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng interceptor cấp controller (tức là đặt decorator `@UseInterceptors()` trước class controller).

```typescript
@@filename()
@UseInterceptors(new TransformInterceptor())
@MessagePattern({ cmd: 'sum' })
accumulate(data: number[]): number {
  return (data || []).reduce((a, b) => a + b);
}
@@switch
@UseInterceptors(new TransformInterceptor())
@MessagePattern({ cmd: 'sum' })
accumulate(data) {
  return (data || []).reduce((a, b) => a + b);
}
```

> info **Gợi ý** Global interceptor được đăng ký trên ứng dụng HTTP chính không áp dụng cho các microservice được kết nối vào một [ứng dụng hybrid](/faq/hybrid-application) trừ khi bạn đặt tùy chọn `inheritAppConfig`. Xem [dùng chung cấu hình](/faq/hybrid-application#sharing-configuration).
