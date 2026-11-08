### Socket activation

Với socket activation, service manager mở socket lắng nghe cho ứng dụng của bạn. [systemd](https://systemd.io/) lắng nghe trên port, khởi động ứng dụng khi kết nối đầu tiên tới, và giao socket cho nó. Các kết nối tới trong lúc ứng dụng khởi động hoặc restart sẽ chờ trong hàng đợi của kernel thay vì bị từ chối.

Điều này hữu ích cho các service hiếm khi được gọi, như công cụ nội bộ, trang admin, hoặc rất nhiều service trên một máy development hay staging. Nếu ứng dụng cũng tự thoát sau một khoảng thời gian không có request, một service như vậy sẽ không chiếm bộ nhớ khi không ai dùng. Cái giá là cold start: request đầu tiên sau một khoảng nghỉ phải chờ tới khi Node.js load ứng dụng và Nest bootstrap nó.

> info **Gợi ý** Lắng nghe trên một socket do service manager truyền vào là một tính năng của [`server.listen()`](https://nodejs.org/api/net.html#serverlistenhandle-backlog-callback) trong Node.js. Nó không được hỗ trợ trên Windows.

#### Unit của systemd <a id="systemd-units"></a>

Tạo một socket unit, ví dụ `/etc/systemd/system/my-app.socket`:

```bash
[Socket]
ListenStream=3000

[Install]
WantedBy=sockets.target
```

Cạnh nó, tạo một service unit cùng tên, `/etc/systemd/system/my-app.service`:

```bash
[Service]
WorkingDirectory=/srv/my-app
ExecStart=/usr/bin/node dist/main.js
Restart=on-failure
```

Sau đó chỉ bật socket. systemd sẽ khởi động `my-app.service` ở kết nối đầu tiên:

```bash
$ sudo systemctl daemon-reload
$ sudo systemctl enable --now my-app.socket
```

> warning **Cảnh báo** Hãy khởi động trực tiếp `node` trong `ExecStart`. systemd truyền socket dưới dạng file descriptor `3` và đặt các biến môi trường `LISTEN_FDS` và `LISTEN_PID`, trong đó `LISTEN_PID` là ID của process mà nó đã khởi động. Nếu có `npm start`, `nest start` hoặc một shell script ở giữa, `LISTEN_PID` sẽ không khớp với process của ứng dụng. Khi đó phần bootstrap bên dưới sẽ fallback sang lắng nghe trên port, việc này thất bại với `EADDRINUSE` vì systemd đã giữ port đó.

> info **Gợi ý** Để thử mà không cần file unit, hãy chạy `systemd-socket-activate --listen=3000 node dist/main.js`. Nó truyền socket theo cùng cách, nhưng chỉ khởi động ứng dụng một lần. Nó cũng không chuyển tiếp các biến như `NODE_ENV` trừ khi bạn chỉ định chúng bằng `--setenv=NODE_ENV`.

#### Bootstrap

Trong file `main.ts`, hãy lắng nghe trên socket được truyền vào khi ứng dụng được khởi động theo cách này, và trên một port trong trường hợp ngược lại:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();

  // Set by systemd when it passes the listening socket to this process
  const activated =
    process.env.LISTEN_FDS === '1' &&
    process.env.LISTEN_PID === String(process.pid);

  if (activated) {
    await app.listen({ fd: 3 } as any);
  } else {
    await app.listen(process.env.PORT ?? 3000);
  }
}

await bootstrap();
```

Các adapter Express và Node truyền nguyên options object cho `server.listen()` của Node.js, nhưng typing của `listen()` của chúng chỉ nhận một port, nên cần ép kiểu. Adapter Fastify nhận `fd` trong các tùy chọn listen có type của nó:

```typescript
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter(),
);
// ...
await app.listen({ fd: 3 });
```

#### Thoát khi rảnh <a id="exiting-when-idle"></a>

systemd không tự dừng ứng dụng. Để giải phóng bộ nhớ của nó, hãy cho ứng dụng tự thoát sau một khoảng thời gian không có request, và systemd sẽ khởi động lại nó ở kết nối tiếp theo. Helper sau đếm các request đang xử lý trên HTTP server bên dưới, nên nó hoạt động với mọi adapter và cũng thấy được các request không bao giờ tới được route handler:

```typescript
@@filename(exit-when-idle)
import type { INestApplication } from '@nestjs/common';
import type { Server } from 'node:http';

export function exitWhenIdle(app: INestApplication, idleMs: number) {
  const server: Server = app.getHttpServer();
  let inFlight = 0;
  let timer: NodeJS.Timeout | undefined;

  const scheduleExit = () => {
    timer = setTimeout(async () => {
      await app.close();
      process.exit(0);
    }, idleMs);
  };

  server.on('request', (req, res) => {
    inFlight++;
    clearTimeout(timer);
    res.once('close', () => {
      if (--inFlight === 0) {
        scheduleExit();
      }
    });
  });
  scheduleExit();
}
```

Gọi nó một lần khi ứng dụng đã lắng nghe trên socket được truyền vào:

```typescript
if (activated) {
  await app.listen({ fd: 3 } as any);
  exitWhenIdle(app, 5 * 60_000); // Exit after 5 minutes without requests
}
```

`app.close()` chạy cùng các [shutdown hook](/fundamentals/lifecycle-events#application-shutdown) như `enableShutdownHooks()` làm khi systemd dừng service bằng `SIGTERM`. Mã thoát `0` báo cho systemd rằng service đã dừng một cách sạch sẽ, nên `Restart=on-failure` sẽ không khởi động lại nó. systemd giữ bản sao socket riêng của nó luôn mở, nên một kết nối tới trong lúc ứng dụng thoát sẽ chờ lần khởi động tiếp theo.

Helper chỉ đếm HTTP request. Một stream server-sent event được đếm cho tới khi client ngắt kết nối, nhưng một kết nối WebSocket đang mở thì không. Nếu ứng dụng của bạn dùng WebSocket, hãy đếm thêm các socket của event `upgrade` của server cho tới khi chúng đóng.

#### Những điều cần lưu ý <a id="things-to-keep-in-mind"></a>

- Dùng `Restart=on-failure`, không phải `Restart=always`. Với `always`, systemd sẽ khởi động lại ứng dụng ngay sau khi nó thoát vì rảnh.
- Các health check và uptime monitor gửi request tới ứng dụng sẽ khởi động nó và giữ nó chạy.
- Các scheduled job (xem [Task scheduling](/application/task-scheduling)) và queue consumer không chạy khi ứng dụng đã dừng. Hãy chạy chúng trong một process luôn hoạt động.
- Request đầu tiên sau một khoảng nghỉ phải chờ toàn bộ quá trình bootstrap, kể cả các kết nối database được mở bởi [async provider](/fundamentals/async-providers). Chương [Serverless](/faq/serverless) cho thấy các cách để rút ngắn nó. Node.js cũng có thể tái sử dụng [compile cache](https://nodejs.org/api/module.html#module-compile-cache) giữa các lần khởi động: hãy thêm `Environment=NODE_COMPILE_CACHE=/var/cache/my-app` và `CacheDirectory=my-app` vào service unit. Node.js ghi cache khi process thoát, và một process bị kill bằng `SIGTERM` mà không có `enableShutdownHooks()` sẽ không ghi nó.
