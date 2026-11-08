### Guard

Không có khác biệt căn bản nào giữa guard của WebSocket và [guard của ứng dụng HTTP thông thường](/guards). Khác biệt duy nhất là thay vì throw `HttpException`, bạn nên throw `WsException`. Nếu một guard trả về `false`, Nest throw một `WsException` với message `'Forbidden resource'`.

> info **Gợi ý** Class `WsException` được cung cấp từ package `@nestjs/websockets`.

#### Gắn guard <a id="binding-guards"></a>

Ví dụ sau dùng một guard cấp method. Như với các ứng dụng dựa trên HTTP, bạn cũng có thể dùng guard cấp gateway (tức là gắn `@UseGuards()` cho class gateway). Global guard được đăng ký bằng `app.useGlobalGuards()` hoặc token `APP_GUARD` cũng áp dụng cho gateway.

```typescript
@@filename()
@UseGuards(AuthGuard)
@SubscribeMessage('events')
handleEvent(client: Client, data: unknown): WsResponse<unknown> {
  const event = 'events';
  return { event, data };
}
@@switch
@UseGuards(AuthGuard)
@SubscribeMessage('events')
handleEvent(client, data) {
  const event = 'events';
  return { event, data };
}
```
