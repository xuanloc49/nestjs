### SDK

SDK `@nestjs/observe` là thứ đưa request, job, lỗi, log và trace của ứng dụng lên dashboard [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') của bạn. Nó hook vào chính vòng đời request của Nest - controller, interceptor, resolver, queue consumer - thay vì gắn một agent Node.js chung chung vào process, nên hầu hết những gì hiện lên trên dashboard đều không cần tự nối span bằng tay.

> info **Gợi ý** Chưa chắc có đáng công thiết lập không? [Bản demo trực tiếp](https://www.observe-demo.nestjs.com/dashboard 'Bản demo trực tiếp của NestJS Observe') cho thấy những gì instrumentation này tạo ra - trace, waterfall, lỗi và job từ một service bận rộn - mà không cần cài gì cả.

#### Cài đặt <a id="installation"></a>

Có hai cách để thiết lập SDK: một lệnh làm hết giúp bạn, hoặc tự làm các bước đó bằng tay.

**Bằng một lệnh.** Chạy lệnh sau trong thư mục project:

```bash
$ npx @nestjs/observe link
```

Lệnh in ra một mã gồm tám chữ cái. Hãy gõ nó tại [observe.nestjs.com/link](https://www.observe.nestjs.com/link 'Liên kết project với NestJS Observe'), đăng ký trước nếu bạn chưa có tài khoản, và xác nhận. Sau đó lệnh ghi cặp key của project vào `.env` dưới dạng `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET`, thêm `.env` vào git-ignore, và thêm `--env-file .env` vào mọi script chạy `nest start` (`start`, `start:dev` và `start:debug` trong một project tạo bằng `nest new`).

Nếu ứng dụng chưa dùng SDK, lệnh còn cài `@nestjs/observe` bằng package manager của bạn và thực hiện giúp bạn ba chỗ sửa trong phần [Bắt đầu nhanh](#quick-start) bên dưới. Nó báo cho bạn biết điều đó trước khi bạn xác nhận. Xem [Liên kết từ terminal](#linking-from-the-terminal) để biết chính xác nó thay đổi những gì.

> warning **Cảnh báo** SDK yêu cầu `@nestjs/core` v11.1.4 trở lên (nó dựa vào tùy chọn ứng dụng `instrument` được giới thiệu trong bản phát hành đó), và `@nestjs/graphql` v13.4.4 trở lên nếu ứng dụng của bạn dùng GraphQL. Các phiên bản cũ hơn thiếu các hook mà SDK cần.

**Bằng tay.** Cài SDK:

```bash
$ npm i @nestjs/observe
```

Sau đó thực hiện ba chỗ sửa trong phần [Bắt đầu nhanh](#quick-start) bên dưới, tạo một API key trên trang **API Keys** của project (xem [Project đầu tiên](/observability/overview#first-project)), và đặt cặp key dưới dạng `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET`. Đây cũng là cách cần làm ở bất cứ đâu mà lệnh để phần nối dây cho bạn tự làm.

#### Bắt đầu nhanh <a id="quick-start"></a>

Việc tích hợp gồm ba bước. Đầu tiên, gọi `createObserveModule()` một lần, thường trong `app.module.ts` hoặc một file khác ở cấp gốc. Nó trả về một cặp khớp nhau - một module Nest và một hook `instrument` - gắn với cùng một cấu hình:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { createObserveModule } from '@nestjs/observe';
import { AppController } from './app.controller.js';
import { AppService } from './app.service.js';

export const { ObserveModule, ObserveInstrument } = createObserveModule();

@Module({
  imports: [
    ObserveModule.forRoot({
      appKey: process.env.OBSERVE_APP_KEY!,
      appSecret: process.env.OBSERVE_APP_SECRET!,
      serviceId: 'cats-app',
    }),
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
```

Thứ hai, import `ObserveModule.forRoot()` vào root module với ít nhất một `serviceId` (như ở trên). Thứ ba, truyền `ObserveInstrument` vào `NestFactory.create()` để SDK gắn vào ứng dụng trước khi nó bắt đầu xử lý traffic:

```typescript
@@filename(main)
import { NestFactory } from '@nestjs/core';
import { AppModule, ObserveInstrument } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    instrument: ObserveInstrument,
  });
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

> warning **Fastify** Với `FastifyAdapter` (hoặc bất kỳ adapter tường minh nào), adapter chiếm tham số thứ hai, nên tùy chọn ứng dụng - và do đó cả `instrument` - chuyển sang tham số **thứ ba**:
>
> ```typescript
> const app = await NestFactory.create<NestFastifyApplication>(
>   AppModule,
>   new FastifyAdapter(),
>   { instrument: ObserveInstrument },
> );
> ```
>
> Truyền options object làm tham số thứ hai cùng với một adapter sẽ âm thầm làm mất chúng, và SDK không bao giờ gắn vào được.

Vậy là xong phần tích hợp. Khi ứng dụng nhận traffic, request, lỗi và trace xuất hiện trên dashboard của project chỉ trong chốc lát, không cần cấu hình exporter và không cần thiết kế schema. Tùy chọn `instrument` đó cũng được `NestFactory.createMicroservice()` và `NestFactory.createApplicationContext()` chấp nhận, nên worker và ứng dụng standalone được instrument theo cùng cách.

> info **Gợi ý** Bản thân `createObserveModule()` nhận một options object điều khiển cách sinh trace id, cách ghi lại ngữ cảnh mã nguồn của lỗi, và những provider nào được instrument - xem [Liên kết trace](#trace-correlation) và [Ngữ cảnh mã nguồn của lỗi](#error-source-context) bên dưới. Mọi thứ khác được cấu hình qua `ObserveModule.forRoot()`.

#### Cấu hình module <a id="configuring-the-module"></a>

Ngoài thông tin xác thực trong phần bắt đầu nhanh, các tùy chọn này quyết định cách SDK định danh ứng dụng của bạn, nơi nó gửi những gì nó ghi lại, và nó cho bạn biết bao nhiêu về chính nó.

##### Xác thực và định danh ứng dụng <a id="authenticating-and-identifying-the-application"></a>

```typescript
ObserveModule.forRoot({
  appKey: process.env.OBSERVE_APP_KEY!,
  appSecret: process.env.OBSERVE_APP_SECRET!,
  serviceId: 'cats-app',
});
```

| Tùy chọn         | Type     | Mặc định | Mô tả                                                                                                                                                                                                      |
| ---------------- | -------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `appKey`         | `string` | bắt buộc | Được `npx @nestjs/observe link` ghi vào `.env` dưới dạng `OBSERVE_APP_KEY`, hoặc được tạo từ trang **API Keys** của project - xem [Project đầu tiên](/observability/overview#first-project). Đừng để nó trong source control. |
| `appSecret`      | `string` | bắt buộc | Được cấp kèm `appKey`, theo cùng cách, và được ghi dưới dạng `OBSERVE_APP_SECRET`. Đừng để nó trong source control.                                                                                        |
| `serviceId`      | `string` | bắt buộc | Định danh ứng dụng này trên dashboard. Nếu bạn chạy nhiều instance của cùng một service, hãy dùng giá trị duy nhất cho mỗi instance (hostname, container id) để phân biệt chúng trong Profiler. |
| `serviceVersion` | `string \| false` | được suy ra | Định danh lần deploy - một semantic version, một commit hash, hoặc bất kỳ định danh nào khác, tối đa 50 ký tự. Khi không được đặt, SDK tự suy ra lúc khởi động (xem bên dưới); `false` thì không báo cáo gì. |

Mọi request và job đều ghi lại release đã phục vụ nó, đó là thứ đứng sau view **Releases**: mỗi phiên bản được so sánh với phiên bản trước đó, kèm một [kết luận](/observability/dashboard#releases-and-their-verdicts) về những gì nó đã thay đổi. Thường thì bạn không cần đặt `serviceVersion`. Khi nó không được đặt, SDK suy ra release lúc ứng dụng khởi động, từ nguồn đầu tiên có giá trị trong số sau:

1. **`OBSERVE_SERVICE_VERSION`** trong môi trường, cho một lần deploy muốn chỉ định tường minh mà không động vào code.
2. **Commit mà nền tảng hoặc CI của bạn cung cấp lúc runtime**: Vercel, Render, Railway, Heroku (với dyno metadata), Coolify và Dokku, hoặc GitHub Actions, GitLab CI, Bitbucket Pipelines, CircleCI, Buildkite, Azure Pipelines và AWS CodeBuild với một ứng dụng do CI job khởi động. `GIT_COMMIT_SHA`, `GIT_COMMIT`, `GIT_SHA`, `COMMIT_SHA` và `SOURCE_VERSION` cũng được đọc.
3. **Commit đang được checkout tại nơi process chạy**, đọc từ thư mục `.git` của repository.
4. **Revision mà một nền tảng container dùng để đặt tên cho mỗi lần deploy**: `K_REVISION` của Cloud Run, `CONTAINER_APP_REVISION` của Azure Container Apps.

Một container image do pipeline của riêng bạn build thường không mang cái nào trong số này, vì quá trình build loại bỏ `.git` và biến của CI không còn tồn tại trong image. Hãy truyền commit cho nó lúc build:

```bash
$ docker build --build-arg GIT_SHA=$(git rev-parse HEAD) .
```

với `ARG GIT_SHA` và `ENV OBSERVE_SERVICE_VERSION=$GIT_SHA` trong Dockerfile. Một `serviceVersion` bạn tự truyền vào sẽ thắng mọi nguồn ở trên. Một commit được suy ra sẽ được báo cáo đầy đủ, như `git rev-parse HEAD` in ra, và dashboard rút gọn nó khi hiển thị; dạng đầy đủ đó cũng là thứ cần truyền làm `fixedInVersion` khi đóng một issue.

<figure><img src="https://www.observe.nestjs.com/docs/sdk/deployments.webp" alt="Release" /></figure>

##### Liên kết từ terminal <a id="linking-from-the-terminal"></a>

`npx @nestjs/observe link` đặt một cặp key lên máy của developer mà không cần copy secret ra khỏi trình duyệt, và thiết lập SDK trong một ứng dụng chưa dùng nó. Hãy chạy nó trong thư mục project (thư mục có `package.json`), hoặc trỏ nó tới đó bằng `--cwd <dir>`:

1. Nó in ra một mã gồm tám chữ cái, như `BCDF-GHJK`, và mở [observe.nestjs.com/link](https://www.observe.nestjs.com/link 'Liên kết project với NestJS Observe') trên trình duyệt. Với `--no-browser`, trong CI, hoặc khi không có terminal, nó chỉ in ra địa chỉ. Mã hết hạn sau 15 phút. Nếu ứng dụng chưa dùng SDK, lệnh còn ghi, bên dưới mã, rằng nó sẽ cài và nối SDK khi bạn xác nhận.
2. Gõ mã trên trang đó. Nếu bạn chưa có tài khoản, bạn đăng ký trước; nếu bạn chưa đăng nhập, bạn đăng nhập. Dù thế nào, bạn cũng quay lại với mã sau đó.
3. Kiểm tra yêu cầu: trang hiển thị hostname của máy và tên package mà lệnh đã gửi. Sau đó chọn nơi đặt key. Trang đề xuất project mới nhất của bạn, và trong đó là ứng dụng mang tên package của bạn, hoặc một ứng dụng mới nếu chưa có. Bạn có thể đổi cả hai, kể cả sang một project mới.
4. Xác nhận. Dashboard cấp một API key mới cho ứng dụng đó, và lệnh ghi nó vào project.

Ở mọi project, lệnh thay đổi tối đa ba file:

- **`.env`** nhận `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET`, đặt trong dấu nháy đơn, thay thế cặp trước đó và giữ nguyên mọi dòng khác. Một `.env` mới được tạo với quyền chỉ bạn đọc được. Dấu nháy là có chủ ý: key hoặc secret có thể chứa `$` và `&`, những ký tự mà `dotenv-expand` (hoặc `ConfigModule` với `expandVariables`) sẽ viết lại, và tại đó một shell source file này sẽ dừng lại.
- **`.gitignore`** có thêm mục `.env`, trừ khi file đó vốn đã bị ignore (như trong một project tạo bằng `nest new`).
- **`package.json`**: mọi script có lệnh bắt đầu bằng `nest start` đều được thêm `--env-file .env`: `start`, `start:dev` và `start:debug` trong một project tạo bằng `nest new`, và cả các script theo từng ứng dụng của một monorepo. Các script đã truyền một env file được giữ nguyên, và `start:prod` (`node dist/main`) cũng vậy. Một script `start` hoặc `start:dev` khởi động ứng dụng theo cách khác cũng được giữ nguyên, nhưng lệnh sẽ nêu tên nó, để bạn tự load `.env` ở đó (ví dụ bằng `node --env-file=.env`).

Trong một ứng dụng chưa dùng SDK (không file mã nguồn nào import `@nestjs/observe`), lệnh còn thiết lập SDK, giống như `nest new` làm:

- **SDK** được cài ở chính phiên bản của lệnh (`@nestjs/observe@^0.3.16` từ 0.3.16). Lệnh dùng package manager mà lockfile của project thuộc về (pnpm, Yarn, Bun hoặc npm), tìm ngược lên tới thư mục gốc của repository, để một package trong workspace tìm được lockfile ở gốc. Không có lockfile, nó dùng package manager được nêu trong trường `packageManager` của `package.json`, nếu không thì dùng npm. Một `@nestjs/observe` đã được cài nhưng cũ hơn lệnh sẽ được nâng cấp theo cùng cách. Trong trường hợp đó, hãy chạy `npx @nestjs/observe@latest link`, vì `npx` thông thường chạy phiên bản đã cài trong project.
- **Root module**, module mà `main.ts` truyền vào `NestFactory.create()` (được tìm bằng cách đi theo câu import của nó), có thêm lời gọi `createObserveModule()`, và `ObserveModule.forRoot()` ở mục đầu tiên trong `imports`. Các tùy chọn đọc cặp key từ `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET`, và đặt `serviceId` thành tên của ứng dụng mà bạn đã xác nhận, chuyển sang chữ thường, dấu cách thành dấu gạch ngang và bỏ các dấu câu khác (`Cats API` trở thành `cats-api`).
- **`main.ts`** truyền `instrument: ObserveInstrument` vào `NestFactory.create()`, bên trong options object của nó, hoặc dưới dạng một tham số options mới nếu chưa có.

Các chỗ sửa tuân theo dấu nháy, dấu chấm phẩy và cách thụt lề của mỗi file, và hoặc cả hai file cùng thay đổi, hoặc không file nào thay đổi. Lệnh liệt kê chúng ra, để bạn có thể rà soát bằng `git diff`.

Ở một số project, lệnh để phần nối dây cho bạn tự làm và in ra lý do; phần [Bắt đầu nhanh](#quick-start) chỉ ra những chỗ cần sửa. Nó làm vậy trong một workspace có nhiều ứng dụng (key thuộc về một trong số chúng), trong một project JavaScript, và ở bất cứ đâu nó không thể sửa code một cách an toàn, ví dụ khi `main.ts` import root module qua một path alias thay vì đường dẫn tương đối, khi `imports` không phải một mảng thông thường, hoặc khi đã có tùy chọn `instrument` được truyền. Nếu việc cài đặt thất bại, lệnh in ra lệnh cài để bạn tự chạy, và cũng để phần nối dây cho bạn tự làm.

Trước khi xin mã, lệnh từ chối một project mà nó phải cài SDK vào nhưng không có `@nestjs/core`, hoặc đang chạy phiên bản NestJS cũ hơn 11.

Không có gì được ghi cho đến khi key đến, nên một lần liên kết bị từ chối, hết hạn hoặc bị gián đoạn sẽ để project nguyên vẹn.

> warning **Cảnh báo** Chỉ xác nhận mã mà chính bạn đã khởi tạo, và chỉ khi nó khớp với terminal của bạn. Mã được gõ vào thay vì nằm trong một URL, để không ai có thể gửi cho bạn một link xác nhận key cho họ.

Key xuất hiện trên trang **API Keys** của project như mọi key khác, được đặt tên là `CLI` kèm thời điểm cấp, và hết hạn sau một năm; hãy chạy lại lệnh để có key mới. `.env` ở lại trên máy đã chạy lệnh, nên mỗi đồng đội (hoặc mỗi máy bổ sung) cũng chạy `npx @nestjs/observe link` và nhận một key riêng cho cùng ứng dụng đó.

##### Đọc cặp key từ biến môi trường <a id="reading-the-key-pair-from-the-environment"></a>

Khi `appKey` hoặc `appSecret` chưa được đặt hoặc rỗng, hoặc vẫn giữ placeholder mà `nest new` sinh ra (`'YOUR_APP_KEY'` và `'YOUR_APP_SECRET'`), `ObserveModule` sẽ đọc `OBSERVE_APP_KEY` hoặc `OBSERVE_APP_SECRET` từ môi trường thay vào đó. Đây là điều cho phép một project được tạo kèm Observe bắt đầu báo cáo ngay khi được liên kết, mà không cần thay đổi gì trong `AppModule`. Một giá trị bạn tự truyền vào luôn thắng, và cơ chế dự phòng tương tự áp dụng cho các tùy chọn mà `forRootAsync()` resolve.

Các biến được đọc khi tùy chọn được resolve (với `forRoot()`, là khi file `AppModule` được import), nên chúng phải có sẵn trong `process.env` tại thời điểm đó. Flag `--env-file` load chúng trước khi bất kỳ module nào chạy.

Trên production, hãy đặt `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET` trong môi trường (thiết lập secret hoặc biến môi trường của nền tảng) thay vì ship kèm `.env`. Một project tạo bằng `nest new` chạy `node dist/main` cho `start:prod`, lệnh này vốn không load `.env`, và `nest start` bỏ qua một `--env-file` không tồn tại, nên một bản clone mới hoặc một lần chạy CI không có `.env` vẫn khởi động được. Hãy cấp cho production một key riêng từ trang **API Keys** của project, để việc thu hồi một key development không bao giờ làm production ngừng báo cáo.

> info **Gợi ý** Lệnh `link` và cơ chế dự phòng từ biến môi trường yêu cầu `@nestjs/observe` 0.3.15 trở lên. Việc cài và nối SDK vào một ứng dụng chưa dùng nó yêu cầu 0.3.16 trở lên.

##### Tắt SDK ngoài production <a id="turning-the-sdk-off-outside-production"></a>

Để một môi trường không báo cáo - phát triển local, một lần chạy CI - hãy giữ `ObserveModule` được import và tắt nó bằng `enabled`, thay vì truyền thông tin xác thực giả, vì chúng vẫn được gửi đi và bị từ chối:

```typescript
ObserveModule.forRoot({
  enabled: process.env.NODE_ENV === 'production',
  appKey: process.env.OBSERVE_APP_KEY ?? '',
  appSecret: process.env.OBSERVE_APP_SECRET ?? '',
  serviceId: 'cats-app',
});
```

`enabled: false` không ghi lại và không gửi gì cả - không trace, metric runtime hay log, và không có request nào tới collector - và không cần thông tin xác thực. Module vẫn ở đó, nên `TracerService` vẫn có thể được inject và gọi nó cũng không gây hại gì. Để trống thông tin xác thực cũng không gửi gì, nhưng log một cảnh báo ở mỗi lần khởi động, vì trên production điều đó thường có nghĩa là biến môi trường không bao giờ đến được process. `enabled` yêu cầu `@nestjs/observe` 0.3.13 trở lên.

##### Cấu hình bất đồng bộ <a id="asynchronous-configuration"></a>

Khi thông tin xác thực đến từ một configuration provider thay vì trực tiếp từ `process.env`, hãy dùng `forRootAsync()`. Nó nhận cùng các dạng `useFactory`/`inject`, `useClass` và `useExisting` như mọi dynamic module khác của Nest (một class implement `ObserveOptionsFactory` với method `createObserveOptions()`), cộng thêm `extraProviders` và `global`:

```typescript
@@filename(app.module)
ObserveModule.forRootAsync({
  imports: [ConfigModule],
  inject: [ConfigService],
  useFactory: (config: ConfigService) => ({
    appKey: config.getOrThrow('OBSERVE_APP_KEY'),
    appSecret: config.getOrThrow('OBSERVE_APP_SECRET'),
    serviceId: config.get('SERVICE_ID', 'cats-app'),
    serviceVersion: config.get('GIT_SHA'),
  }),
});
```

##### Endpoint của collector <a id="collector-endpoint"></a>

```typescript
ObserveModule.forRoot({
  // ...
  endpoint: 'https://observe-api.nestjs.com',
});
```

`endpoint` (mặc định `'https://observe-api.nestjs.com'`) là URL gốc của collector. Telemetry và profile dùng chung nó, nên hai thứ không bao giờ trỏ tới hai nơi khác nhau. Để ghi đè nó mà không động vào cấu hình, hãy đặt biến môi trường `OBSERVE_ENDPOINT`. NestJS Observe là một dịch vụ được host sẵn và `observe-api.nestjs.com` là collector duy nhất nó chạy; hãy đổi endpoint khi traffic của bạn phải đi ra ngoài qua một forwarding proxy, hoặc để trỏ một môi trường test tới một stub chấp nhận các lô dữ liệu.

##### Debug chính SDK <a id="debugging-the-sdk-itself"></a>

```typescript
ObserveModule.forRoot({
  // ...
  debug: true,
});
```

`debug` (mặc định `false`) log thêm thông tin chẩn đoán từ SDK ra console. Hãy dùng nó trong lúc làm cho instrumentation hoạt động, và tắt nó trên production.

##### Tắt ứng dụng <a id="shutdown"></a>

Khi ứng dụng đóng lại - `app.close()`, hoặc một `SIGTERM` khi đã gọi `app.enableShutdownHooks()` - SDK gửi những gì nó vẫn còn giữ trước khi dừng: các request và job đã xong kể từ lô trước, lỗi của chúng, các dòng log đã được buffer trước khi bắt đầu tắt, và một mẫu runtime cuối cùng. Nó chờ collector tối đa `shutdownFlushTimeout` (mặc định `2000` ms), rồi để ứng dụng thoát; `0` thì bỏ qua lần gửi cuối cùng.

Có hai thứ quyết định những gì được gửi đi:

- **Tín hiệu.** Nest chỉ chạy shutdown hook khi nhận `SIGTERM` nếu ứng dụng đã gọi `app.enableShutdownHooks()` lúc bootstrap. Không có nó, một lần deploy hay scale-in sẽ kết thúc process ngay lập tức, và vài giây telemetry cuối cùng bị mất.
- **Thứ tự module.** Các global module tắt theo thứ tự ngược với thứ tự import. Một job vẫn đang chạy lúc tắt chỉ được báo cáo nếu `ObserveModule` đứng trước `BullModule`, và trước mọi module đăng ký queue, trong `imports` của root module.

Trong các test suite khởi động ứng dụng với thông tin xác thực thật, hãy đặt `shutdownFlushTimeout: 0`, để mỗi lần `app.close()` không gửi request của bài test đó lên project của bạn hay chờ một collector mà môi trường test không với tới được. Lần gửi cuối cùng yêu cầu `@nestjs/observe` 0.3.10 trở lên.
#### Instrument tự động <a id="automatic-instrumentation"></a>

Mọi thứ trong phần này đều được ghi lại mà không cần dòng code nào của bạn; chỉ cần cài SDK là đủ. Các tùy chọn chỉ để thu hẹp hoặc tắt nó đi.

##### Query database và HTTP gửi ra ngoài <a id="database-queries-and-outbound-http"></a>

Kể từ `@nestjs/observe` 0.3.0, các query database và request gửi ra ngoài xuất hiện dưới dạng span mà không cần cấu hình gì, lồng bên dưới method đã thực hiện chúng. Một lời gọi repository chậm sẽ cho thấy nó đang chờ _câu lệnh nào_.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/sql.webp" alt="Một query được mở trong waterfall" /></figure>

Database được instrument ở tầng driver thay vì ORM: `pg`, `mysql2`, `mssql` và `mongodb` được phát hiện nếu ứng dụng của bạn đã phụ thuộc vào chúng, điều này bao phủ TypeORM, MikroORM, Drizzle, Mongoose, Knex, Sequelize và các driver adapter của Prisma mà không cần nêu tên cái nào. SQL Server là ngoại lệ: `mssql` là thứ mà TypeORM và SQL Server adapter của Prisma chạy trên đó, nhưng Knex, Sequelize và MikroORM nói chuyện với SQL Server trực tiếp qua `tedious`, thứ chưa được hỗ trợ (cũng như `mssql/msnodesqlv8`). Các ORM đi kèm bản sao driver lồng bên trong riêng (MikroORM và Mongoose làm vậy mỗi khi phiên bản không khớp) cũng được xử lý. Các công việc nội bộ của driver (bắt tay kết nối, xác thực, ping) không được ghi lại. Một span query được gắn nhãn bằng động từ và bảng của nó (`SELECT users`) và mang câu lệnh với **mọi literal bị loại bỏ** - chuỗi, số, danh sách `IN (...)` và comment đều được thay thế trước khi span rời khỏi process, còn các tham số bind thì hoàn toàn không bao giờ được đọc. Các query lặp lại dưới cùng một cha được gộp thành một node duy nhất kèm số lần, nên một lỗi N+1 hiện ra là `SELECT order_items ×47` thay vì 47 dòng.

Các client khác, trong đó có Redis và Kafka, không được instrument ở tầng library. Tuy nhiên, một ứng dụng Nest gần như luôn đăng ký chúng dưới dạng provider - một client `ioredis` từ một factory, một `ClientKafka` từ `ClientsModule` - và SDK ghi lại các lời gọi method của mọi provider: mỗi lời gọi trên client là một span dưới method đã thực hiện nó, và một lời gọi trả về promise, như các lệnh của `ioredis`, được tính giờ cho đến khi promise settle. Một client được tạo và gọi bên ngoài dependency injection sẽ không được ghi lại.

HTTP gửi ra ngoài được đọc từ chính diagnostics channel của Node, nên `fetch`, `undici` và mọi thứ xây dựng trên `node:http` (axios, got, hầu hết các SDK) đều được bao phủ mà không cần patch gì. Span được gắn nhãn `GET api.example.com` và mang URL với các query parameter nhạy cảm được che đi. SDK cũng gửi trace id hiện tại dưới dạng `x-request-id`, giúp [tracing HTTP-to-HTTP](/observability/distributed-tracing#http-to-http) trở nên tự động. Khi bật tùy chọn [`openTelemetry`](/observability/opentelemetry#running-beside-opentelemetry), nó gửi thêm một `traceparent` theo chuẩn W3C: `http.traceContext: false` sẽ không gửi header đó, còn `propagateTraceId` quyết định cả hai header được gửi tới đâu.

```typescript
ObserveModule.forRoot({
  // ...
  outgoing: {
    database: true,
    http: {
      ignore: (url) => url.startsWith('https://internal-metrics.'),
      // Only forward the trace id to your own services
      propagateTraceId: (url) => url.includes('.svc.cluster.local'),
    },
  },
});
```

Đặt `outgoing: false` để tắt hết, hoặc `database: false` / `http: false` để tắt riêng từng phần.

> info **Gợi ý** Các span này **không bị tính phí**. Chúng là chi tiết của một span method mà bạn đã gửi, nên chúng không được tính vào Observability Event hay giới hạn tốc độ của bạn. Một request chạy mười query tốn chi phí như trước.

##### Lời gọi model <a id="model-calls"></a>

Kể từ `@nestjs/observe` 0.3.20, một lời gọi `fetch` tới một model provider còn ghi lại trên span gửi ra ngoài những gì lời gọi đã dùng: model, số token đầu vào, đầu ra và đầu vào được cache mà response của provider ghi, và, với stream, thời gian tới event đầu tiên. OpenAI, Azure OpenAI, Anthropic, Google Gemini và Vertex AI, Amazon Bedrock, Mistral, Groq, OpenRouter, Together AI, DeepSeek, xAI, Cohere và Perplexity được nhận diện theo host, nên các SDK chính thức, Vercel AI SDK và LangChain đều được bao phủ mà không cần nêu tên.

- **Được đọc khi response đi qua.** SDK đọc response theo tốc độ mà code của bạn đọc, kể cả stream, và chuyển nó đi nguyên vẹn. Một stream mà code của bạn hủy cũng bị hủy ở phía provider.
- **Prompt và completion không bao giờ được gửi đi.** Chỉ có model và số token rời khỏi process.
- **Chỉ với `fetch`.** Một lời gọi thực hiện qua `node:http` - axios, hoặc client mặc định của AWS SDK cho Bedrock - vẫn giữ span gửi ra ngoài thông thường của nó mà không có model hay token.

Một gateway đứng trước các provider (LiteLLM, Portkey, proxy của riêng bạn) hoặc một model tự host có API tương thích OpenAI được thêm vào theo host, và các lời gọi của nó được gắn tag provider `custom`. `outgoing: {{ '{' }} llm: false {{ '}' }}` ngừng đọc các lời gọi model trong khi vẫn giữ span thông thường của chúng:

```typescript
ObserveModule.forRoot({
  // ...
  outgoing: {
    llm: { hosts: ['llm-gateway.internal:4000'] },
  },
});
```

Một [quy tắc production](/observability/production-rules) có thể giới hạn số lời gọi model mà một request được thực hiện.

##### WebSocket gateway <a id="websocket-gateways"></a>

Các message được xử lý bởi `@SubscribeMessage()` được báo cáo dưới dạng request với protocol `ws` và operation id là `GatewayClass:pattern`, trên mọi platform adapter. Khối tùy chọn `ws` nhận cùng các hook `ignore`, `tags`, `setAttributes` và `getUserId` như các transport khác; mỗi hook nhận `{{ '{' }} gateway, pattern, client, data {{ '}' }}`. Việc kết nối và ngắt kết nối không phải là operation và không được báo cáo.

##### Queue <a id="queues"></a>

Cả `@nestjs/bullmq` lẫn `@nestjs/bull` bản gốc đều được instrument: mỗi lần chạy processor được báo cáo dưới dạng một job, kèm thời gian chờ trong queue, số thứ tự lần thử và kết quả. Một job được thêm từ bên trong một operation đang được trace sẽ thừa hưởng trace id của operation đó - xem [Distributed tracing](/observability/distributed-tracing#queue-jobs-bullmq-and-bull).

##### Metric runtime và profiling <a id="runtime-metrics-and-profiling"></a>

```typescript
ObserveModule.forRoot({
  // ...
  runtimeMetrics: true,
  runtimeMetricsInterval: 60000,
});
```

`runtimeMetrics` (mặc định `true`) lấy mẫu bộ nhớ, CPU, garbage collection và độ trễ event loop theo chu kỳ (`runtimeMetricsInterval`, mặc định `60000` ms) và cung cấp dữ liệu cho **Profiler**. Chính các mẫu đó còn đóng vai trò heartbeat của ứng dụng: một cảnh báo **Telemetry silence** sẽ kích hoạt khi chúng ngừng đến, cho bạn một cơ chế giám sát uptime nhẹ nhàng mà không cần probe bên ngoài.

#### Lỗi và request thất bại <a id="errors-and-failed-requests"></a>

Một lỗi thoát ra khỏi controller, resolver hoặc job được tự động ghi lại. Các tùy chọn này quyết định những gì đi kèm với nó: mã nguồn quanh frame lỗi, và header cùng body của request đã thất bại.

##### Ngữ cảnh mã nguồn của lỗi <a id="error-source-context"></a>

Các lỗi lan ra khỏi controller, resolver, job hoặc span được tự động ghi lại. Khi bật `sourceContext` (mặc định), SDK còn đọc các dòng mã nguồn quanh mỗi stack frame thuộc ứng dụng của một lỗi đã ghi lại và đính kèm chúng. Điều này cho phép dashboard hiển thị đoạn code lỗi cạnh stack trace, kể cả với một lỗi production trên một bản build mà bạn không checkout.

```typescript
@@filename(app.module)
export const { ObserveModule, ObserveInstrument } = createObserveModule({
  sourceContext: {
    linesOfContext: 5,
    maxFrames: 5,
    sourceMaps: false,
  },
});
```

Đây là tùy chọn của `createObserveModule()`, không phải `forRoot()`. Đặt `sourceContext: false` để tắt, hoặc truyền một object để tinh chỉnh các giá trị mặc định:

| Tùy chọn         | Type      | Mặc định | Mô tả                                                                                                                                                                                                                                                                                                                                                                          |
| ---------------- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `linesOfContext` | `number`  | `5`      | Số dòng được đọc ở mỗi phía của dòng thuộc frame.                                                                                                                                                                                                                                                                                                                              |
| `maxFrames`      | `number`  | `5`      | Số frame thuộc ứng dụng, tính từ đỉnh stack, được đính kèm mã nguồn. Giới hạn kích thước payload với các stack sâu.                                                                                                                                                                                                                                                            |
| `sourceMaps`     | `boolean` | `false`  | Map các frame đã compile ngược lại qua source map trước khi đọc mã nguồn. Chỉ cần thiết nếu process chạy code đã compile _mà không có_ hỗ trợ source map của chính Node (`--enable-source-maps` hoặc `process.setSourceMapsEnabled(true)`); khi đã bật hỗ trợ đó, các frame vốn đã mang vị trí gốc và tùy chọn này là thừa. Tốn một lần parse map cho mỗi file đã compile ở lần chạm đầu tiên, rồi được cache lại. |

> warning **Cảnh báo** Bật tùy chọn này sẽ gửi các đoạn mã nguồn của ứng dụng (thường là vài dòng quanh lỗi) lên dashboard, nơi chúng được lưu cùng lỗi. Các frame bên trong `node_modules` và phần nội bộ của Node không bao giờ được đọc, chỉ có mã nguồn của ứng dụng. Hãy tắt nó nếu việc gửi đi bất kỳ đoạn mã nguồn nào là không chấp nhận được với codebase của bạn.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/error-with-source.webp" alt="Thẻ lỗi kèm ngữ cảnh mã nguồn" /></figure>

##### Ghi lại request thất bại và chậm <a id="capturing-failed-and-slow-requests"></a>

Khi một HTTP request **thất bại**, SDK ghi lại kèm theo một danh sách nhỏ, cố định các header được phép - `user-agent`, `content-type`, `content-length`, `accept`, `host`, `origin` và `referer`. Không header nào trong số này dùng để xác thực hay định danh người gọi. Nếu bạn đặt `slowerThanMs`, các request chạy ít nhất bằng khoảng đó cũng được ghi lại theo cùng cách, dù có thất bại hay không. Một request bình thường không ghi lại gì. Request body mặc định **tắt**; hãy bật tường minh nếu bạn muốn:

```typescript
ObserveModule.forRoot({
  // ...
  http: {
    capture: {
      headers: ['user-agent', 'x-tenant-id'],
      body: { maxBytes: 4096 }, // default 2048, at most 16384
      slowerThanMs: 2000,
    },
  },
});
```

Mọi thứ được ghi lại đều đi qua [`redaction`](/observability/sdk#logs) trước khi rời khỏi process: các key nhạy cảm (`password`, `token`, `authorization`, ...) được che theo tên bên trong body, và việc chỉ định một header nhạy cảm sẽ ghi lại `[REDACTED]` thay vì giá trị của nó. `capture: false` không ghi lại gì cả. Dữ liệu ghi lại được hiển thị trên trang chi tiết của request dưới dạng thẻ **Request**.

#### Log và liên kết trace <a id="logs-and-trace-correlation"></a>

Mỗi lần thực thi đều có một trace id. Các tùy chọn này quyết định các dòng log của bạn liên quan tới nó như thế nào: được chuyển tiếp lên dashboard, hoặc chỉ được gắn id để hệ thống log của riêng bạn có thể link tới trace.

##### Log <a id="logs"></a>

```typescript
ObserveModule.forRoot({
  // ...
  forwardLogs: true,
  redaction: {
    enabled: true,
    keys: ['internalToken'],
    patterns: [/acct_[a-z0-9]{16}/gi],
  },
});
```

`forwardLogs` (mặc định `false`) gửi các dòng log của ứng dụng (bất cứ thứ gì được ghi qua `Logger` của Nest) lên dashboard, liên kết với trace đang hoạt động khi mỗi dòng được ghi. Trên trang execution, mỗi dòng được đặt lên dòng thời gian của trace, cạnh span đang chạy khi nó được ghi. Việc chuyển tiếp log có sẵn từ gói Pro trở lên.

Chuyển tiếp log đưa chúng lên hạ tầng mà bạn không kiểm soát, nên che giấu dữ liệu được bật mặc định. Cơ chế che giấu đó cũng làm sạch message và stack của mọi lỗi đã ghi lại cùng mọi dữ liệu request đã ghi lại, bất kể `forwardLogs` có bật hay không:

| Trường của `redaction` | Type       | Mặc định       | Mô tả                                                                                                                                                                                                                                                                    |
| ---------------------- | ---------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `enabled`              | `boolean`  | `true`         | Có làm sạch gì hay không.                                                                                                                                                                                                                                                |
| `useDefaultPatterns`   | `boolean`  | `true`         | Áp dụng các pattern có sẵn: bearer token, JWT, AWS key id, PEM private key, secret dạng `key=value`, và số thẻ hợp lệ theo thuật toán Luhn. Chỉ tắt nếu bạn thay thế hoàn toàn chúng bằng `patterns` của riêng mình; không có trường hợp hợp lệ nào cho việc chuyển tiếp log mà không che giấu. |
| `patterns`             | `RegExp[]` | -              | Các pattern bổ sung cần che, cho những secret có dạng mà chỉ codebase của bạn biết (prefix token nội bộ, định danh khách hàng). Luôn được áp dụng như thể là global, nên một lần khớp không bao giờ chỉ giới hạn ở lần xuất hiện đầu tiên trong một dòng.                |
| `keys`                 | `string[]` | -              | Các key bổ sung có giá trị bị che hoàn toàn (trong thuộc tính log, header và body đã ghi lại, và query string của URL), ngoài danh sách có sẵn. So sánh không phân biệt hoa thường và bỏ qua `-`/`_`, nên `apiKey`, `api_key` và `API-KEY` là cùng một mục.             |
| `replacement`          | `string`   | `'[REDACTED]'` | Text thay thế cho mọi thứ khớp.                                                                                                                                                                                                                                          |

> info **Gợi ý** Kể cả khi tắt `forwardLogs`, SDK vẫn bổ sung cho `ConsoleLogger` để mọi dòng được ghi bên trong một lần thực thi đang được trace đều mang trace id của nó (`attachTraceIdToLogs`, xem [Liên kết trace](#trace-correlation)). Điều đó cho phép bạn liên kết hệ thống tổng hợp log của riêng mình với trace trên dashboard mà không cần gửi nội dung log đi đâu cả.

##### Liên kết trace <a id="trace-correlation"></a>

Đây cũng là các tùy chọn của `createObserveModule()`. Chúng quyết định cách request nhận được trace id và cách id đó xuất hiện trong log của riêng bạn:

```typescript
@@filename(app.module)
import { randomUUID } from 'node:crypto';

export const { ObserveModule, ObserveInstrument } = createObserveModule({
  traceIdKey: 'traceId',
  traceIdGenerator: (req: any) => req.headers['x-request-id'] ?? randomUUID(),
  attachTraceIdToLogs: true,
});
```

| Tùy chọn              | Type                       | Mặc định                                                      | Mô tả                                                                                                                               |
| --------------------- | -------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `traceIdKey`          | `string`                   | `'traceId'`                                                   | Key dùng để lưu trace id trong request context, để lấy ra sau này thông qua `TracerService`.                                        |
| `traceIdGenerator`    | `(req: unknown) => string` | Dùng lại một `x-request-id` đúng định dạng (header HTTP, hoặc metadata của packet microservice) nếu có, nếu không thì một UUID v7 | Sinh trace id cho mỗi request. Được gọi với request object với HTTP; với các protocol khác, nó nhận transport context. |
| `attachTraceIdToLogs` | `boolean`                  | `true`                                                        | Bổ sung cho `ConsoleLogger` để đưa trace id vào log message, để log có thể được liên kết với trace kể cả khi không có `forwardLogs`. Ở định dạng text mặc định, id nằm ở cuối dòng, sau message (`   Trace ID: <id>`); với [log JSON](/application/logger#json-logging), nó là trường `traceId`. Các dòng được ghi bên ngoài một lần thực thi đang được trace giữ nguyên. |

Vì generator mặc định dùng lại `x-request-id` gửi đến, một chuỗi các HTTP service vốn đã dùng chung một trace mà không cần cấu hình thêm. Các service được instrument bằng OpenTelemetry truyền trace tiếp qua `traceparent` thay vào đó, header mà tùy chọn `openTelemetry` của `forRoot()` đọc và gửi - xem [Chạy cạnh OpenTelemetry](/observability/opentelemetry#running-beside-opentelemetry). Điều tương tự áp dụng cho các transport microservice: TCP và Redis trên `@nestjs/microservices` 12.0.4 trở lên, và NATS, Kafka, RabbitMQ, MQTT 5 và gRPC trên 12.3.3 trở lên. Truyền trace qua các phiên bản cũ hơn và qua GraphQL cần thêm vài dòng code - xem [Distributed tracing](/observability/distributed-tracing).
#### Định hình những gì được ghi lại <a id="shaping-what-is-recorded"></a>

Các tùy chọn này làm phong phú những gì SDK ghi lại (request dành cho ai, liên quan tới cái gì) và loại bỏ những gì bạn không cần.

##### Gắn người dùng với dữ liệu telemetry <a id="associating-users-with-telemetry"></a>

`getUserId` đọc request gửi đến và trả về bất kỳ định danh nào mà hệ thống của bạn dùng cho một người: user id, account id, hoặc một id theo phạm vi tenant. Đặt nó một lần và view **Users** sẽ tự động có dữ liệu:

```typescript
ObserveModule.forRoot({
  // ...
  http: {
    getUserId: (req) => req.user?.id ?? 'anonymous',
  },
});
```

Cùng tùy chọn đó có trên `rpc` (nhận transport id và `BaseRpcContext`), `grpc` (nhận call object), `graphql` (nhận GraphQL context, cho các operation không nằm trong HTTP request nào), và `ws` (nhận message của gateway), mỗi cái đọc context riêng của transport thay vì một HTTP request. Việc báo cáo định danh người dùng là tùy chọn: traffic không có định danh vẫn hiện ở mọi nơi ngoại trừ các view theo người dùng. Dashboard xem định danh như một chuỗi opaque và không bao giờ cố resolve nó thành tên hay email, nên hãy ưu tiên dùng một id nội bộ opaque thay vì bất cứ thứ gì định danh cá nhân.

##### Tag và thuộc tính tùy chỉnh <a id="tags-and-custom-attributes"></a>

`http`, `rpc`, `grpc`, `graphql` và `jobs` đều nhận cùng hai tùy chọn để gắn dữ liệu của riêng bạn vào mọi request mà chúng bao phủ:

| Tùy chọn        | Áp dụng                                                       | Mô tả                                                                                                    |
| --------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `tags`          | Cùng một `Record<string, string>` tĩnh cho mọi request        | Được gửi lên Observe. Dành cho các hằng số không thay đổi theo lời gọi, ví dụ `project`, `env`, `region`. |
| `setAttributes` | Một hàm nhận request/call/job, trả về các cặp key-value       | Giữ lại trong ứng dụng của bạn. Dành cho ngữ cảnh theo lời gọi mà code của bạn đọc sau đó, ví dụ tenant id, feature flag. |

```typescript
ObserveModule.forRoot({
  // ...
  http: {
    tags: { project: 'cats-app', env: process.env.NODE_ENV ?? 'development' },
    setAttributes: (req) => ({ tenantId: req.headers['x-tenant-id'] }),
  },
  jobs: {
    setAttributes: (job) => ({ queueName: job.queueName, jobName: job.name }),
  },
});
```

`tags` xuất hiện dưới dạng tag trên request hoặc job tương ứng, có thể tìm kiếm và hiển thị trên trang chi tiết của nó.

Các giá trị của `setAttributes` **không được gửi lên Observe** và không xuất hiện trên dashboard. Khi mỗi lời gọi bắt đầu, chúng được ghi vào [thuộc tính theo request](/observability/manual-instrumentation#request-scoped-attributes) của lời gọi đó, giống như tự gọi `setAttribute()` cho từng key, nên bất kỳ code nào xử lý lời gọi đó đều có thể đọc chúng bằng `getAttribute()`. Hàm nhận bất cứ thứ gì transport có: request với `http`, transport id và `BaseRpcContext` với `rpc`, call object với `grpc`, resolve info và GraphQL context với `graphql`, và `{{ '{' }} queueName, name, id {{ '}' }}` với `jobs`.

Để thấy một giá trị theo lời gọi trên dashboard, hãy thêm nó làm tag trên một span bằng `TracerService` (xem [Instrumentation thủ công](/observability/manual-instrumentation)):

```typescript
const span = await this.tracerService.activeSpan();
span.addTags({ tenantId: String(this.tracerService.getAttribute('tenantId')) });
```

> info **Gợi ý** Một GraphQL server thường là một HTTP endpoint, nên request của nó vốn đã chịu tác động của tùy chọn `http`: `http.ignore` bỏ một request trước khi tầng GraphQL thấy nó, còn `http.getUserId` cung cấp người dùng cho các query qua HTTP. Khối `graphql` tinh chỉnh những gì xảy ra _bên trong_ một request đã được cho qua, theo từng operation chứ không phải theo từng resolver, và `graphql.getUserId` chỉ được hỏi đến với những operation chưa nằm trong một HTTP trace, như subscription qua WebSocket.

##### Bỏ qua các operation ồn ào <a id="ignoring-noisy-operations"></a>

Mỗi khối transport đầu vào (`http`, `rpc`, `grpc`, `graphql` và `ws`) có một tùy chọn `ignore` bỏ hoàn toàn việc instrument cho những lời gọi khớp điều kiện, như một health check endpoint, một probe nội bộ, hay bất cứ thứ gì không đáng để trace:

```typescript
ObserveModule.forRoot({
  // ...
  http: {
    ignore: ['/health', { method: 'GET', path: /^\/internal\// }],
  },
  rpc: {
    ignore: (transportId, ctx) =>
      ctx instanceof TcpContext && ctx.getPattern() === 'ping',
  },
  grpc: {
    ignore: (call) => call.path.endsWith('/Health/Check'),
  },
  graphql: {
    ignore: (info) => info.fieldName === 'healthcheck',
  },
});
```

`http.ignore` nhận một mảng path, các cặp `{{ '{' }} method, path {{ '}' }}` (`path` có thể là chuỗi hoặc `RegExp`), và các `RegExp` thông thường, hoặc một predicate duy nhất trên request. `rpc.ignore`, `grpc.ignore` và `graphql.ignore` là các predicate trên context riêng của transport (lần lượt là transport id và `BaseRpcContext` của `@nestjs/microservices`, call object của gRPC, và resolve info của GraphQL). Khớp tên một trường GraphQL sẽ bỏ qua toàn bộ operation mà trường đó dẫn đầu, không chỉ riêng trường đó: một operation được đo từ đầu đến cuối, nên hoặc nó được trace, hoặc không.

`ignore` ngăn dữ liệu telemetry được tạo ra ngay từ đầu. Bộ lọc loại bỏ trong phần kiểm soát chi tiêu của dashboard là một công cụ khác: chúng loại bỏ các event đã được tạo ra ngay lúc tiếp nhận để giảm khối lượng tính phí. Hãy dùng `ignore` khi bạn không muốn một trace tồn tại, và dùng bộ lọc loại bỏ khi bạn muốn tinh chỉnh chi phí trên dữ liệu mà SDK đã đang tạo ra.

`http` còn nhận `queryParamsObfuscateRegex`, một `RegExp` che các giá trị query string nhạy cảm trước khi chúng được gửi đi. Nó được áp dụng thêm bên trên cơ chế che giấu có sẵn, cơ chế này luôn che các tham số nhạy cảm phổ biến (`token`, `password`, `code`, `signature`, v.v.).

##### Lấy mẫu trace và gom lô <a id="trace-sampling-and-batching"></a>

```typescript
ObserveModule.forRoot({
  // ...
  tracesSampleRate: 0.25,
  maxTracesPerBatch: 1000,
  flushInterval: 5000,
});
```

| Tùy chọn            | Type                                                                       | Mặc định | Mô tả                                                                                                     |
| ------------------- | -------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------- |
| `tracesSampleRate`  | `number \| ((protocol: 'http' \| 'rpc' \| 'grpc' \| 'graphql' \| 'ws', attributes) => boolean)` | `1.0`    | Tỉ lệ trace được gửi đi, hoặc một predicate để quyết định theo từng trace. `0` được tính như chưa đặt và sẽ gửi tất cả; truyền `() => false` để không gửi gì. `1.0` gửi tất cả; `0.1` gửi 10%. |
| `maxTracesPerBatch` | `number`                                                                   | `1000`   | Giới hạn số trace gửi đi mỗi lô, để kiểm soát khối lượng với các ứng dụng traffic cao.                    |
| `flushInterval`     | `number` (ms)                                                              | `5000`   | Tần suất SDK gom lô và gửi các trace đã thu thập.                                                         |

Dữ liệu telemetry được buffer trong process và được gửi đi theo chu kỳ flush thay vì gửi ngay cùng mỗi request. Việc lấy mẫu ở đây quyết định những gì SDK _tạo ra_. Phần kiểm soát chi tiêu theo project của dashboard (lấy mẫu span, giới hạn tốc độ, bộ lọc loại bỏ) tác động lên những gì nó đã gửi, và bạn có thể thay đổi chúng mà không cần deploy lại.

#### Khai báo mục tiêu trong code <a id="declaring-objectives-in-code"></a>

`@Objective()` nêu ra những gì một route cam kết, ngay cạnh handler phải giữ cam kết đó, và Observe biến mỗi cam kết thành một [SLO](/observability/dashboard#slos). Mục tiêu được viết, review và đánh version cùng với route mà nó bao phủ, trong cùng một lần thay đổi:

```typescript
import { Objective } from '@nestjs/observe';

@Controller('orders')
export class OrdersController {
  @Post()
  @Objective({ availability: 99.9, latency: { underMs: 300, target: 99 } })
  create(@Body() dto: CreateOrderDto) {
    return this.ordersService.create(dto);
  }
}
```

| Tùy chọn       | Nó cam kết điều gì                                                                       |
| -------------- | ---------------------------------------------------------------------------------------- |
| `availability` | Tỉ lệ phần trăm request không thất bại vì lỗi chưa được xử lý - `99.9` cho ba số chín.   |
| `latency`      | `{{ '{' }} underMs, target {{ '}' }}`: `target` phần trăm request hoàn tất trong dưới `underMs` mili giây. |
| `windowDays`   | Khoảng thời gian trượt dùng để đánh giá: 7, 14, 28 (mặc định), hoặc 30 ngày.             |
| `name`         | Tên mà dashboard dùng để gọi nó, thay cho route và cam kết.                              |

Mục tiêu nằm trong khoảng từ 90 tới 99.999, và một handler có thể mang tối đa mười `@Objective()`; bất cứ thứ gì nằm ngoài các giới hạn đó sẽ được log và bị bỏ qua khi ứng dụng khởi động. Mỗi cam kết trở thành một SLO riêng, có phạm vi theo ứng dụng và route mà handler phục vụ, và xuất hiện khi route đã có traffic. Từ đó trở đi, code là chủ của nó: đổi một mục tiêu, một khoảng thời gian hay một cái tên rồi deploy, và cùng SLO đó sẽ thay đổi theo. Dashboard đánh dấu một SLO được khai báo là **in code** và không chỉnh sửa nó, và việc xóa nó ở đó sẽ không có tác dụng lâu dài khi decorator vẫn còn, vì SDK khai báo lại các mục tiêu của mỗi route mỗi giờ. Để bỏ một SLO, hãy xóa decorator, rồi xóa SLO. SLO cần một gói có hỗ trợ (Scale hoặc Enterprise); trên các gói khác, các khai báo được gửi đi nhưng bị bỏ qua.

#### Tham khảo cấu hình đầy đủ <a id="full-configuration-reference"></a>

Toàn bộ tùy chọn trong một bảng. Các tùy chọn liệt kê dưới `createObserveModule()` phải được đặt ở đó; mọi thứ khác đặt trong `forRoot()`/`forRootAsync()`.

| Vị trí                  | Tùy chọn                              | Mục đích                                                                  |
| ----------------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `createObserveModule()` | `sourceContext`                       | Đính kèm các dòng mã nguồn vào stack frame của lỗi                        |
| `createObserveModule()` | `traceIdKey`                          | Key trong context dùng để lưu trace id                                    |
| `createObserveModule()` | `traceIdGenerator`                    | Cách mỗi request nhận được trace id                                       |
| `createObserveModule()` | `attachTraceIdToLogs`                 | Thêm trace id vào output của `ConsoleLogger`                              |
| `createObserveModule()` | `skipInstrumentation`                 | Predicate loại các instance provider khỏi việc instrument                 |
| `forRoot()`             | `appKey`, `appSecret`                 | Cặp API key của project (hoặc `OBSERVE_APP_KEY`, `OBSERVE_APP_SECRET`)    |
| `forRoot()`             | `endpoint`                            | URL gốc của collector (hoặc `OBSERVE_ENDPOINT`)                           |
| `forRoot()`             | `enabled`                             | `false` không ghi lại và không gửi gì, dành cho development và CI         |
| `forRoot()`             | `serviceId`, `serviceVersion`         | Định danh ứng dụng và release (release được suy ra khi chưa đặt)          |
| `forRoot()`             | `http`, `rpc`, `grpc`, `graphql`      | `tags`, `setAttributes`, `getUserId`, `ignore` theo từng transport        |
| `forRoot()`             | `jobs`                                | `tags` và `setAttributes` cho queue job và job theo lịch                  |
| `forRoot()`             | `http.queryParamsObfuscateRegex`      | Che các giá trị query string nhạy cảm                                     |
| `forRoot()`             | `http.capture`                        | Header (và tùy chọn là body) được ghi lại với request thất bại và chậm    |
| `forRoot()`             | `outgoing`                            | Span cho query database và HTTP gửi ra ngoài; `outgoing.llm` cho lời gọi model |
| `forRoot()`             | `openTelemetry`                       | `traceparent` W3C vào và ra, cạnh một SDK OpenTelemetry                   |
| `forRoot()`             | `otlp`                                | Export span qua OTLP tới backend OpenTelemetry của bạn                    |
| `forRoot()`             | `ws`                                  | `tags`, `setAttributes`, `getUserId`, `ignore` cho WebSocket gateway      |
| `forRoot()`             | `runtimeMetrics`, `runtimeMetricsInterval` | Mẫu của Profiler và heartbeat                                        |
| `forRoot()`             | `forwardLogs`, `redaction`            | Stream log và làm sạch dữ liệu                                            |
| `forRoot()`             | `tracesSampleRate`                    | Tỉ lệ (hoặc predicate) trace được gửi đi                                  |
| `forRoot()`             | `maxTracesPerBatch`, `flushInterval`  | Gom lô                                                                    |
| `forRoot()`             | `spanCollapse`                        | Gộp các span anh em lặp lại (ngưỡng mặc định `20`, giữ lại `3` cái chậm nhất) |
| `forRoot()`             | `shutdownFlushTimeout`                | Thời gian việc đóng ứng dụng chờ lần gửi cuối cùng (mặc định `2000` ms)   |
| `forRoot()`             | `debug`                               | Chẩn đoán SDK                                                             |

#### Đọc tiếp <a id="where-to-go-next"></a>

- [Instrumentation thủ công](/observability/manual-instrumentation) - thêm span của riêng bạn, ghi lại các lỗi đã xử lý, gắn thuộc tính theo request, và báo cáo custom metric.
- [Distributed tracing](/observability/distributed-tracing) - giữ một trace duy nhất xuyên qua HTTP, gRPC, các transport microservice và GraphQL.
- [Dashboard](/observability/dashboard) - những gì hiện lên khi SDK đã chạy, và các view liên quan tới nhau như thế nào.
