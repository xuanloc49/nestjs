### Lifecycle event

Một ứng dụng Nest, cũng như mọi thành phần trong ứng dụng, đều có một vòng đời do Nest quản lý. Nest cung cấp các **lifecycle hook** giúp bạn nắm được các sự kiện quan trọng trong vòng đời và hành động (chạy code đã đăng ký trên module, provider hoặc controller) khi chúng xảy ra.

#### Trình tự vòng đời <a id="lifecycle-sequence"></a>

Sơ đồ sau mô tả trình tự các sự kiện quan trọng trong vòng đời ứng dụng, từ lúc ứng dụng được bootstrap cho tới khi process Node.js thoát. Toàn bộ vòng đời chia thành ba giai đoạn: **khởi tạo**, **đang chạy** và **kết thúc**. Nắm được vòng đời này, bạn có thể lên kế hoạch khởi tạo module và service hợp lý, quản lý các kết nối đang mở, và tắt ứng dụng một cách êm ái (graceful shutdown) khi nhận được tín hiệu kết thúc.

<figure><img class="illustrative-image" src="/assets/lifecycle-events.png" /></figure>

#### Các lifecycle event <a id="lifecycle-events-1"></a>

Lifecycle event xảy ra trong quá trình bootstrap và tắt ứng dụng. Nest gọi các method lifecycle hook đã đăng ký trên module, provider và controller tại mỗi lifecycle event dưới đây (**shutdown hook** phải được bật trước, như mô tả trong [Tắt ứng dụng](/fundamentals/lifecycle-events#application-shutdown)). Như trong sơ đồ trên, Nest cũng gọi các method tương ứng bên dưới để bắt đầu và dừng lắng nghe kết nối.

Trong bảng sau, `onModuleInit()` và `onApplicationBootstrap()` chỉ được kích hoạt khi ứng dụng được khởi tạo: khi bạn gọi tường minh `app.init()` hoặc `app.listen()`, hoặc khi bạn tạo một ứng dụng standalone bằng `NestFactory.createApplicationContext()`, hàm này sẽ tự khởi tạo giúp bạn.

Các hook `onModuleDestroy()`, `beforeApplicationShutdown()` và `onApplicationShutdown()` chỉ được kích hoạt khi bạn gọi tường minh `app.close()`, hoặc khi process nhận được một tín hiệu hệ thống (như `SIGTERM`) và bạn đã gọi `enableShutdownHooks()` lúc bootstrap ứng dụng (xem [Tắt ứng dụng](/fundamentals/lifecycle-events#application-shutdown) bên dưới).

| Method lifecycle hook           | Lifecycle event kích hoạt việc gọi method hook                                                                                                                                                                |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `onModuleInit()`                | Được gọi khi các dependency của module chủ đã được resolve.                                                                                                                                                   |
| `onApplicationBootstrap()`      | Được gọi khi mọi module đã được khởi tạo, nhưng trước khi bắt đầu lắng nghe kết nối.                                                                                                                         |
| `onModuleDestroy()`\*           | Được gọi sau khi nhận được tín hiệu kết thúc (ví dụ `SIGTERM`).                                                                                                                                               |
| `beforeApplicationShutdown()`\* | Được gọi sau khi mọi handler `onModuleDestroy()` đã hoàn tất (Promise đã resolve hoặc reject);<br />khi hoàn tất (Promise đã resolve hoặc reject), mọi kết nối hiện có sẽ bị đóng (`app.close()` được gọi). |
| `onApplicationShutdown()`\*     | Được gọi sau khi các kết nối đóng lại, là bước cuối cùng của `app.close()`.                                                                                                                                   |

\* Với các event này, nếu bạn không gọi tường minh `app.close()`, bạn phải tự bật để chúng hoạt động với các tín hiệu hệ thống như `SIGTERM`. Xem [Tắt ứng dụng](/fundamentals/lifecycle-events#application-shutdown) bên dưới.

> warning **Cảnh báo** Các lifecycle hook liệt kê ở trên không được kích hoạt cho các class **request-scoped**. Class request-scoped không gắn với vòng đời ứng dụng, và thời gian tồn tại của chúng là không đoán trước được. Chúng được tạo riêng cho mỗi request và bị garbage collect sau khi response được gửi đi.

> info **Gợi ý** Nest gọi `onModuleInit()` và `onApplicationBootstrap()` theo từng module, sắp xếp theo khoảng cách của mỗi module tới root module trong import graph: các module được import sâu nhất (và các global module) chạy trước, root module chạy cuối cùng. Hook của mỗi module đều được await xong rồi Nest mới chuyển sang module tiếp theo. Các shutdown hook chạy theo thứ tự ngược lại.

#### Cách dùng <a id="usage"></a>

Mỗi lifecycle hook được đại diện bởi một interface. Về mặt kỹ thuật, interface là tùy chọn vì chúng không tồn tại sau khi compile TypeScript. Dù vậy, dùng chúng vẫn là thói quen tốt để tận dụng type chặt chẽ và hỗ trợ từ editor. Để đăng ký một lifecycle hook, hãy implement interface tương ứng. Ví dụ, để đăng ký một method được gọi trong lúc khởi tạo module trên một class cụ thể (ví dụ controller, provider hoặc module), hãy implement interface `OnModuleInit` bằng cách cung cấp method `onModuleInit()`:

```typescript
@@filename()
import { Injectable, OnModuleInit } from '@nestjs/common';

@Injectable()
export class UsersService implements OnModuleInit {
  onModuleInit() {
    console.log(`The module has been initialized.`);
  }
}
@@switch
import { Injectable } from '@nestjs/common';

@Injectable()
export class UsersService {
  onModuleInit() {
    console.log(`The module has been initialized.`);
  }
}
```

#### Khởi tạo bất đồng bộ <a id="asynchronous-initialization"></a>

Cả hai hook `OnModuleInit` và `OnApplicationBootstrap` đều cho phép bạn trì hoãn quá trình khởi tạo ứng dụng. Hãy trả về một `Promise`, hoặc đánh dấu method là `async` và `await` một thao tác bất đồng bộ hoàn tất trong thân method.

```typescript
@@filename()
async onModuleInit(): Promise<void> {
  await this.fetch();
}
@@switch
async onModuleInit() {
  await this.fetch();
}
```

#### Tắt ứng dụng <a id="application-shutdown"></a>

Các hook `onModuleDestroy()`, `beforeApplicationShutdown()` và `onApplicationShutdown()` được gọi trong giai đoạn kết thúc, khi có lời gọi tường minh `app.close()` hoặc, nếu bạn đã bật, khi nhận được tín hiệu hệ thống như `SIGTERM`. Tính năng này thường được dùng với [Kubernetes](https://kubernetes.io/) để quản lý vòng đời container, với dyno của [Heroku](https://www.heroku.com/), và với các dịch vụ tương tự.

Listener của shutdown hook tiêu tốn tài nguyên hệ thống, nên chúng bị tắt mặc định. Để dùng shutdown hook, bạn **phải bật listener** bằng cách gọi `enableShutdownHooks()`:

```typescript
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Starts listening for shutdown hooks
  app.enableShutdownHooks();

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

> warning **Cảnh báo** Do giới hạn vốn có của nền tảng, NestJS chỉ hỗ trợ hạn chế cho shutdown hook trên Windows. Bạn có thể kỳ vọng `SIGINT` hoạt động, cũng như `SIGBREAK` và ở một mức độ nào đó là `SIGHUP`. Tuy nhiên, `SIGTERM` không bao giờ hoạt động trên Windows, vì kill một process trong Task Manager là vô điều kiện (ứng dụng không có cách nào phát hiện hay ngăn chặn). Để tìm hiểu thêm về cách `SIGINT`, `SIGBREAK` và các tín hiệu khác được xử lý trên Windows, xem [tài liệu xử lý tín hiệu của libuv](https://docs.libuv.org/en/v1.x/signal.html) và tài liệu Node.js về [signal event](https://nodejs.org/api/process.html#process_signal_events).

> info **Gợi ý** `enableShutdownHooks()` tiêu tốn bộ nhớ vì phải khởi động listener. Khi bạn chạy nhiều app Nest trong một process Node.js (ví dụ khi chạy test song song), Node.js có thể cảnh báo có quá nhiều listener. Vì lý do này, shutdown hook không được bật mặc định. Hãy lưu ý điều này khi chạy nhiều instance trong một process Node.js.

Khi ứng dụng nhận được tín hiệu kết thúc, nó sẽ gọi các method `onModuleDestroy()`, `beforeApplicationShutdown()` và `onApplicationShutdown()` đã đăng ký, theo đúng thứ tự đó. `beforeApplicationShutdown()` và `onApplicationShutdown()` nhận tín hiệu tương ứng làm tham số đầu tiên (`onModuleDestroy()` không nhận tham số nào). Nếu một method đã đăng ký trả về promise, Nest sẽ không tiếp tục trình tự cho đến khi promise đó được resolve hoặc reject.

```typescript
@@filename()
@Injectable()
class UsersService implements OnApplicationShutdown {
  onApplicationShutdown(signal: string) {
    console.log(signal); // e.g., "SIGINT"
  }
}
@@switch
@Injectable()
class UsersService {
  onApplicationShutdown(signal) {
    console.log(signal); // e.g., "SIGINT"
  }
}
```

> info **Gợi ý** Gọi `app.close()` không kết thúc process Node.js. Nó chỉ chạy trình tự tắt ứng dụng (các hook `onModuleDestroy()`, `beforeApplicationShutdown()` và `onApplicationShutdown()`, cộng với việc đóng server bên dưới). Nếu còn interval đang chạy, các tác vụ nền chạy lâu, v.v., process sẽ không tự thoát.
