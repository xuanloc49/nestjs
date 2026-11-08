### Global prefix

Để đặt một prefix cho **mọi route** được đăng ký trong một ứng dụng HTTP, hãy gọi method `setGlobalPrefix()` trên instance `INestApplication`.

```typescript
const app = await NestFactory.create(AppModule);
app.setGlobalPrefix('v1');
```

Để loại trừ các route khỏi global prefix, hãy dùng tùy chọn `exclude`:

```typescript
app.setGlobalPrefix('v1', {
  exclude: [{ path: 'health', method: RequestMethod.GET }],
});
```

Ngoài ra, bạn có thể chỉ định một route dưới dạng chuỗi, điều này loại trừ nó với mọi request method:

```typescript
app.setGlobalPrefix('v1', { exclude: ['cats'] });
```

> info **Gợi ý** Thuộc tính `path` hỗ trợ wildcard parameter thông qua package [path-to-regexp](https://github.com/pillarjs/path-to-regexp#parameters). Dấu sao wildcard trần (`*`) đã bị deprecated; hãy dùng parameter (`:param`) hoặc wildcard có tên (`*splat`) thay vào đó. Một wildcard có tên yêu cầu ít nhất một segment bổ sung, nên `health/*splat` loại trừ `/health/status` nhưng không loại trừ chính `/health`. Để loại trừ cả hai, hãy bọc wildcard trong dấu ngoặc nhọn: `health/{{ '{' }}*splat&#125;`.

#### Route bị loại trừ và request không khớp <a id="excluded-routes-and-unmatched-requests"></a>

Các route bị loại trừ được đăng ký bên ngoài prefix, nhưng Nest vẫn xử lý những request tới chúng mà không khớp với handler nào. Ví dụ, với `exclude: ['health']` và chỉ có một handler `GET /health`, một request `POST /health` sẽ đi qua các exception filter của bạn và nhận response `404` tiêu chuẩn của Nest.

Với Express adapter, một request tới một path không nằm dưới prefix cũng không bị loại trừ sẽ không bao giờ tới được Nest: Express trả lời nó bằng trang `404` mặc định của mình. Fastify adapter chuyển mọi request không khớp cho Nest.

> info **Gợi ý** Khi bật [URI versioning](/http/versioning), việc loại trừ được so khớp mà không tính segment phiên bản, và một route bị loại trừ vẫn giữ segment đó. Ví dụ, `exclude: ['health']` với `defaultVersion: '1'` phục vụ route tại `/v1/health`.
