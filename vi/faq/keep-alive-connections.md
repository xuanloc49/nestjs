### Kết nối keep-alive

Mặc định, các HTTP adapter của NestJS chờ tới khi các response đã hoàn tất rồi mới đóng ứng dụng. Đôi khi hành vi này không mong muốn hoặc gây bất ngờ: một số request dùng header `Connection: Keep-Alive` và giữ kết nối mở trong thời gian dài.

Nếu bạn muốn ứng dụng luôn thoát mà không chờ các kết nối này kết thúc, hãy bật tùy chọn `forceCloseConnections` khi tạo ứng dụng NestJS.

> info **Gợi ý** Phần lớn người dùng không cần tùy chọn này. Dấu hiệu điển hình cho thấy bạn cần nó là một ứng dụng không thoát khi bạn kỳ vọng, thường là khi có bật `app.enableShutdownHooks()`, và hay gặp nhất trong lúc phát triển khi chạy với `--watch`.

#### Cách dùng <a id="usage"></a>

Trong file `main.ts`, hãy bật tùy chọn này khi tạo ứng dụng NestJS:

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    forceCloseConnections: true,
  });
  await app.listen(process.env.PORT ?? 3000);
}

await bootstrap();
```

> info **Lưu ý** Các adapter Express, Fastify và Node đều hiện thực tùy chọn ứng dụng `forceCloseConnections`. Với Fastify, việc này cần NestJS v12.1 trở lên. Ở các phiên bản cũ hơn, hãy truyền tùy chọn server `forceCloseConnections` riêng của Fastify cho constructor của `FastifyAdapter` thay vào đó.
