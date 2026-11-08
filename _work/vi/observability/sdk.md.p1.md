### SDK

SDK `@nestjs/observe` là thứ đưa request, job, lỗi, log và trace của ứng dụng lên dashboard [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') của bạn. Nó hook vào chính vòng đời request của Nest - controller, interceptor, resolver, queue consumer - thay vì gắn một agent Node.js chung chung vào process, nên hầu hết những gì hiện lên trên dashboard đều không cần tự nối span bằng tay.

> info **Hint** Chưa chắc có đáng công thiết lập không? [Bản demo trực tiếp](https://www.observe-demo.nestjs.com/dashboard 'Bản demo trực tiếp của NestJS Observe') cho thấy những gì instrumentation này tạo ra - trace, waterfall, lỗi và job từ một service bận rộn - mà không cần cài gì cả.

#### Cài đặt

Có hai cách để thiết lập SDK: một lệnh làm hết giúp bạn, hoặc tự làm các bước đó bằng tay.

**Bằng một lệnh.** Chạy lệnh sau trong thư mục project:

[[CODE:1]]

Lệnh in ra một mã gồm tám chữ cái. Hãy gõ nó tại [observe.nestjs.com/link](https://www.observe.nestjs.com/link 'Liên kết project với NestJS Observe'), đăng ký trước nếu bạn chưa có tài khoản, và xác nhận. Sau đó lệnh ghi cặp key của project vào `.env` dưới dạng `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET`, thêm `.env` vào git-ignore, và thêm `--env-file .env` vào mọi script chạy `nest start` (`start`, `start:dev` và `start:debug` trong một project tạo bằng `nest new`).

Nếu ứng dụng chưa dùng SDK, lệnh còn cài `@nestjs/observe` bằng package manager của bạn và thực hiện giúp bạn ba chỗ sửa trong phần [Bắt đầu nhanh](#quick-start) bên dưới. Nó báo cho bạn biết điều đó trước khi bạn xác nhận. Xem [Liên kết từ terminal](#linking-from-the-terminal) để biết chính xác nó thay đổi những gì.

> warning **Warning** SDK yêu cầu `@nestjs/core` v11.1.4 trở lên (nó dựa vào tùy chọn ứng dụng `instrument` được giới thiệu trong bản phát hành đó), và `@nestjs/graphql` v13.4.4 trở lên nếu ứng dụng của bạn dùng GraphQL. Các phiên bản cũ hơn thiếu các hook mà SDK cần.

**Bằng tay.** Cài SDK:

[[CODE:2]]

Sau đó thực hiện ba chỗ sửa trong phần [Bắt đầu nhanh](#quick-start) bên dưới, tạo một API key trên trang **API Keys** của project (xem [Project đầu tiên](/observability/overview#first-project)), và đặt cặp key dưới dạng `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET`. Đây cũng là cách cần làm ở bất cứ đâu mà lệnh để phần nối dây cho bạn tự làm.

#### Bắt đầu nhanh

Việc tích hợp gồm ba bước. Đầu tiên, gọi `createObserveModule()` một lần, thường trong `app.module.ts` hoặc một file khác ở cấp gốc. Nó trả về một cặp khớp nhau - một module Nest và một hook `instrument` - gắn với cùng một cấu hình:

[[CODE:3]]

Thứ hai, import `ObserveModule.forRoot()` vào root module với ít nhất một `serviceId` (như ở trên). Thứ ba, truyền `ObserveInstrument` vào `NestFactory.create()` để SDK gắn vào ứng dụng trước khi nó bắt đầu xử lý traffic:

[[CODE:4]]

> warning **Fastify** Với `FastifyAdapter` (hoặc bất kỳ adapter tường minh nào), adapter chiếm tham số thứ hai, nên tùy chọn ứng dụng - và do đó cả `instrument` - chuyển sang tham số **thứ ba**:
>
> [[CODE:5]]
>
> Truyền options object làm tham số thứ hai cùng với một adapter sẽ âm thầm làm mất chúng, và SDK không bao giờ gắn vào được.

Vậy là xong phần tích hợp. Khi ứng dụng nhận traffic, request, lỗi và trace xuất hiện trên dashboard của project chỉ trong chốc lát, không cần cấu hình exporter và không cần thiết kế schema. Tùy chọn `instrument` đó cũng được `NestFactory.createMicroservice()` và `NestFactory.createApplicationContext()` chấp nhận, nên worker và ứng dụng standalone được instrument theo cùng cách.

> info **Hint** Bản thân `createObserveModule()` nhận một options object điều khiển cách sinh trace id, cách ghi lại ngữ cảnh mã nguồn của lỗi, và những provider nào được instrument - xem [Liên kết trace](#trace-correlation) và [Ngữ cảnh mã nguồn của lỗi](#error-source-context) bên dưới. Mọi thứ khác được cấu hình qua `ObserveModule.forRoot()`.

#### Cấu hình module

Ngoài thông tin xác thực trong phần bắt đầu nhanh, các tùy chọn này quyết định cách SDK định danh ứng dụng của bạn, nơi nó gửi những gì nó ghi lại, và nó cho bạn biết bao nhiêu về chính nó.

##### Xác thực và định danh ứng dụng

[[CODE:6]]

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

[[CODE:7]]

với `ARG GIT_SHA` và `ENV OBSERVE_SERVICE_VERSION=$GIT_SHA` trong Dockerfile. Một `serviceVersion` bạn tự truyền vào sẽ thắng mọi nguồn ở trên. Một commit được suy ra sẽ được báo cáo đầy đủ, như `git rev-parse HEAD` in ra, và dashboard rút gọn nó khi hiển thị; dạng đầy đủ đó cũng là thứ cần truyền làm `fixedInVersion` khi đóng một issue.

<figure><img src="https://www.observe.nestjs.com/docs/sdk/deployments.webp" alt="Release" /></figure>

##### Liên kết từ terminal

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

> warning **Warning** Chỉ xác nhận mã mà chính bạn đã khởi tạo, và chỉ khi nó khớp với terminal của bạn. Mã được gõ vào thay vì nằm trong một URL, để không ai có thể gửi cho bạn một link xác nhận key cho họ.

Key xuất hiện trên trang **API Keys** của project như mọi key khác, được đặt tên là `CLI` kèm thời điểm cấp, và hết hạn sau một năm; hãy chạy lại lệnh để có key mới. `.env` ở lại trên máy đã chạy lệnh, nên mỗi đồng đội (hoặc mỗi máy bổ sung) cũng chạy `npx @nestjs/observe link` và nhận một key riêng cho cùng ứng dụng đó.

##### Đọc cặp key từ biến môi trường

Khi `appKey` hoặc `appSecret` chưa được đặt hoặc rỗng, hoặc vẫn giữ placeholder mà `nest new` sinh ra (`'YOUR_APP_KEY'` và `'YOUR_APP_SECRET'`), `ObserveModule` sẽ đọc `OBSERVE_APP_KEY` hoặc `OBSERVE_APP_SECRET` từ môi trường thay vào đó. Đây là điều cho phép một project được tạo kèm Observe bắt đầu báo cáo ngay khi được liên kết, mà không cần thay đổi gì trong `AppModule`. Một giá trị bạn tự truyền vào luôn thắng, và cơ chế dự phòng tương tự áp dụng cho các tùy chọn mà `forRootAsync()` resolve.

Các biến được đọc khi tùy chọn được resolve (với `forRoot()`, là khi file `AppModule` được import), nên chúng phải có sẵn trong `process.env` tại thời điểm đó. Flag `--env-file` load chúng trước khi bất kỳ module nào chạy.

Trên production, hãy đặt `OBSERVE_APP_KEY` và `OBSERVE_APP_SECRET` trong môi trường (thiết lập secret hoặc biến môi trường của nền tảng) thay vì ship kèm `.env`. Một project tạo bằng `nest new` chạy `node dist/main` cho `start:prod`, lệnh này vốn không load `.env`, và `nest start` bỏ qua một `--env-file` không tồn tại, nên một bản clone mới hoặc một lần chạy CI không có `.env` vẫn khởi động được. Hãy cấp cho production một key riêng từ trang **API Keys** của project, để việc thu hồi một key development không bao giờ làm production ngừng báo cáo.

> info **Hint** Lệnh `link` và cơ chế dự phòng từ biến môi trường yêu cầu `@nestjs/observe` 0.3.15 trở lên. Việc cài và nối SDK vào một ứng dụng chưa dùng nó yêu cầu 0.3.16 trở lên.

##### Tắt SDK ngoài production

Để một môi trường không báo cáo - phát triển local, một lần chạy CI - hãy giữ `ObserveModule` được import và tắt nó bằng `enabled`, thay vì truyền thông tin xác thực giả, vì chúng vẫn được gửi đi và bị từ chối:

[[CODE:8]]

`enabled: false` không ghi lại và không gửi gì cả - không trace, metric runtime hay log, và không có request nào tới collector - và không cần thông tin xác thực. Module vẫn ở đó, nên `TracerService` vẫn có thể được inject và gọi nó cũng không gây hại gì. Để trống thông tin xác thực cũng không gửi gì, nhưng log một cảnh báo ở mỗi lần khởi động, vì trên production điều đó thường có nghĩa là biến môi trường không bao giờ đến được process. `enabled` yêu cầu `@nestjs/observe` 0.3.13 trở lên.

##### Cấu hình bất đồng bộ

Khi thông tin xác thực đến từ một configuration provider thay vì trực tiếp từ `process.env`, hãy dùng `forRootAsync()`. Nó nhận cùng các dạng `useFactory`/`inject`, `useClass` và `useExisting` như mọi dynamic module khác của Nest (một class implement `ObserveOptionsFactory` với method `createObserveOptions()`), cộng thêm `extraProviders` và `global`:

[[CODE:9]]

##### Endpoint của collector

[[CODE:10]]

`endpoint` (mặc định `'https://observe-api.nestjs.com'`) là URL gốc của collector. Telemetry và profile dùng chung nó, nên hai thứ không bao giờ trỏ tới hai nơi khác nhau. Để ghi đè nó mà không động vào cấu hình, hãy đặt biến môi trường `OBSERVE_ENDPOINT`. NestJS Observe là một dịch vụ được host sẵn và `observe-api.nestjs.com` là collector duy nhất nó chạy; hãy đổi endpoint khi traffic của bạn phải đi ra ngoài qua một forwarding proxy, hoặc để trỏ một môi trường test tới một stub chấp nhận các lô dữ liệu.

##### Debug chính SDK

[[CODE:11]]

`debug` (mặc định `false`) log thêm thông tin chẩn đoán từ SDK ra console. Hãy dùng nó trong lúc làm cho instrumentation hoạt động, và tắt nó trên production.

##### Tắt ứng dụng

Khi ứng dụng đóng lại - `app.close()`, hoặc một `SIGTERM` khi đã gọi `app.enableShutdownHooks()` - SDK gửi những gì nó vẫn còn giữ trước khi dừng: các request và job đã xong kể từ lô trước, lỗi của chúng, các dòng log đã được buffer trước khi bắt đầu tắt, và một mẫu runtime cuối cùng. Nó chờ collector tối đa `shutdownFlushTimeout` (mặc định `2000` ms), rồi để ứng dụng thoát; `0` thì bỏ qua lần gửi cuối cùng.

Có hai thứ quyết định những gì được gửi đi:

- **Tín hiệu.** Nest chỉ chạy shutdown hook khi nhận `SIGTERM` nếu ứng dụng đã gọi `app.enableShutdownHooks()` lúc bootstrap. Không có nó, một lần deploy hay scale-in sẽ kết thúc process ngay lập tức, và vài giây telemetry cuối cùng bị mất.
- **Thứ tự module.** Các global module tắt theo thứ tự ngược với thứ tự import. Một job vẫn đang chạy lúc tắt chỉ được báo cáo nếu `ObserveModule` đứng trước `BullModule`, và trước mọi module đăng ký queue, trong `imports` của root module.

Trong các test suite khởi động ứng dụng với thông tin xác thực thật, hãy đặt `shutdownFlushTimeout: 0`, để mỗi lần `app.close()` không gửi request của bài test đó lên project của bạn hay chờ một collector mà môi trường test không với tới được. Lần gửi cuối cùng yêu cầu `@nestjs/observe` 0.3.10 trở lên.
