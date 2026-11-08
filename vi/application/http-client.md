### HTTP client

Hầu hết ứng dụng đều gọi tới các service khác qua HTTP. Package `@nestjs/http-client` cung cấp một client cho việc này, xây dựng trên API `fetch` có sẵn trong Node.js. Nó bổ sung những thứ mà `fetch` còn thiếu: base URL, header mặc định, JSON body, path parameter và query parameter, response có type, timeout, retry, interceptor và client có tên. Bạn cấu hình nó như một module Nest và inject nó giống như mọi provider khác.

Package này không có dependency nào ngoài `@nestjs/common` và `@nestjs/core`. Mọi method đều trả về Promise, nên bạn `await` các request và xử lý lỗi bằng `try`/`catch`. Nếu bạn thích Observable hơn, xem [Làm việc với RxJS](/application/http-client#working-with-rxjs).

> info **Gợi ý** Package này thay thế cho `HttpModule` dựa trên Axios từ `@nestjs/axios`, thứ mà chương này từng mô tả. `@nestjs/axios` vẫn có sẵn. Xem [Chuyển từ @nestjs/axios](/application/http-client#migrating-from-nestjsaxios) để chuyển đổi.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, hãy cài package:

```bash
$ npm i --save @nestjs/http-client
```

#### Bắt đầu <a id="getting-started"></a>

Import `HttpClientModule` vào module thực hiện request, và đăng ký một client bằng method `register()`:

```typescript
@@filename(cats.module)
import { Module } from '@nestjs/common';
import { HttpClientModule } from '@nestjs/http-client';
import { CatsService } from './cats.service.js';

@Module({
  imports: [
    HttpClientModule.register({
      baseUrl: 'https://api.example.com/v1',
      timeout: '5s',
    }),
  ],
  providers: [CatsService],
})
export class CatsModule {}
```

Sau đó inject class `HttpClient`:

```typescript
@@filename(cats.service)
import { Injectable } from '@nestjs/common';
import { HttpClient } from '@nestjs/http-client';
import type { Cat } from './interfaces/cat.interface.js';

@Injectable()
export class CatsService {
  constructor(private readonly http: HttpClient) {}

  async findAll(): Promise<Cat[]> {
    const { data } = await this.http.get<Cat[]>('/cats');
    return data;
  }
}
```

Request sẽ được gửi tới `https://api.example.com/v1/cats`. Một URL tương đối được nối vào `baseUrl` với đúng một dấu `/` ở giữa, nên prefix `/v1` được giữ lại (khác với `new URL('/cats', base)`, vốn sẽ bỏ mất nó). Một client không có `baseUrl` yêu cầu URL tuyệt đối.

Giống như các method `register()` khác, mỗi lần gọi sẽ tạo một client cho module import nó. Để một client inject được trong mọi module, đặt `isGlobal: true`.

#### Client có tên <a id="named-clients"></a>

Một ứng dụng thường giao tiếp với nhiều service upstream, mỗi service có base URL, thông tin xác thực và timeout riêng. Hãy đặt cho mỗi client một `name`:

```typescript
@@filename(repos.module)
@Module({
  imports: [
    HttpClientModule.register({
      name: 'github',
      baseUrl: 'https://api.github.com',
      headers: { accept: 'application/vnd.github+json' },
    }),
  ],
  providers: [ReposService],
})
export class ReposModule {}
```

và inject nó bằng decorator `@InjectHttpClient()`:

```typescript
@@filename(repos.service)
@Injectable()
export class ReposService {
  constructor(@InjectHttpClient('github') private readonly github: HttpClient) {}
}
```

Client đăng ký không có tên là client mặc định, được inject dưới dạng `HttpClient`. Hàm `getHttpClientToken(name)` trả về injection token của một client, hữu ích trong test và custom provider.

#### Giá trị mặc định cho toàn ứng dụng <a id="application-wide-defaults"></a>

Các thiết lập mà mọi client đều dùng chung, như header `user-agent`, timeout, chính sách retry, hay một interceptor để log, được đặt trong `HttpClientModule.forRoot()`. Hãy import nó một lần, trong root module. Nó luôn là global:

```typescript
@@filename(app.module)
@Module({
  imports: [
    HttpClientModule.forRoot({
      headers: { 'user-agent': 'cats-service/1.0' },
      timeout: '10s',
    }),
    CatsModule,
    ReposModule,
  ],
})
export class AppModule {}
```

`forRoot()` không tự đăng ký client nào, và không nhận `baseUrl`. Thiết lập riêng của mỗi client sẽ thắng giá trị mặc định, với ba ngoại lệ: header được merge (đặt một header thành `null` trong client để bỏ một header mặc định), thiết lập retry được merge theo từng trường, và các interceptor của `forRoot()` chạy trước các interceptor riêng của client.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Để tạo tùy chọn cho client từ các provider khác, như `ConfigService` trong chương [cấu hình](/application/configuration#getting-started), dùng `registerAsync()`:

```typescript
@@filename(repos.module)
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { HttpClientModule, type Duration } from '@nestjs/http-client';
import { ReposService } from './repos.service.js';

@Module({
  imports: [
    HttpClientModule.registerAsync({
      name: 'github',
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        baseUrl: config.getOrThrow<string>('GITHUB_API_URL'),
        headers: { authorization: `Bearer ${config.getOrThrow<string>('GITHUB_TOKEN')}` },
        timeout: config.get<Duration>('GITHUB_TIMEOUT', '5s'),
      }),
    }),
  ],
  providers: [ReposService],
})
export class ReposModule {}
```

Factory có thể là `async`. Nó trả về cùng các tùy chọn như `register()`, với type `HttpClientFactoryOptions`, ngoại trừ `name`, `isGlobal`, `imports` và các class interceptor: Nest cần những thứ đó để dựng module, trước khi factory chạy, nên chúng được đặt cạnh `useFactory`. Một factory trả về một trong những tùy chọn này sẽ làm ứng dụng dừng lại lúc khởi động.

Thay vì factory, bạn có thể truyền một class implement interface `HttpClientOptionsFactory`. Nest khởi tạo nó bên trong module của client và gọi method `createHttpClientOptions()` của nó:

```typescript
@@filename(github-client.config)
@Injectable()
export class GithubClientConfig implements HttpClientOptionsFactory {
  constructor(private readonly config: ConfigService) {}

  createHttpClientOptions(): HttpClientFactoryOptions {
    return { baseUrl: this.config.getOrThrow<string>('GITHUB_API_URL') };
  }
}
```

```typescript
HttpClientModule.registerAsync({
  name: 'github',
  imports: [ConfigModule],
  useClass: GithubClientConfig,
});
```

Để dùng lại một provider đã có thay vì tạo một bản sao riêng, truyền `useExisting: GithubClientConfig`, với module export nó nằm trong `imports`. `forRootAsync()` hoạt động theo cùng cách. Class `useClass` hoặc `useExisting` của nó implement `HttpClientModuleOptionsFactory`, với method `createHttpClientModuleOptions()`.

#### Gửi request <a id="making-requests"></a>

Client có một method cho mỗi HTTP verb: `get()`, `post()`, `put()`, `patch()`, `delete()`, `head()` và `options()`. Mỗi method nhận một URL và một options object tùy chọn, và resolve ra một `HttpResponse`. Method `request()` nhận verb qua tùy chọn `method`.

```typescript
@@filename(repos.service)
@Injectable()
export class ReposService {
  constructor(@InjectHttpClient('github') private readonly github: HttpClient) {}

  async findAll(org: string): Promise<Repo[]> {
    const { data } = await this.github.get<Repo[]>('/orgs/:org/repos', {
      params: { org },
      query: { type: 'public', sort: 'updated', topic: ['nest', 'typescript'] },
    });
    return data;
  }

  async createIssue(owner: string, repo: string, issue: CreateIssueDto): Promise<Issue> {
    const { data } = await this.github.post<Issue>('/repos/:owner/:repo/issues', {
      params: { owner, repo },
      json: issue,
    });
    return data;
  }
}
```

Các tùy chọn tương ứng với những gì một controller Nest đọc từ request:

- `params` điền vào các segment `:name` của path, có URI-encode. Một segment không có giá trị sẽ gây throw, kể cả khi bỏ qua `params`, và một key không khớp với segment nào, hoặc một giá trị có thể đẩy request sang endpoint khác (chuỗi rỗng, `.` hoặc `..`), cũng vậy.
- `query` là một object hoặc một instance `URLSearchParams`, được nối thêm vào query đã có sẵn trong URL. Mảng sẽ lặp lại key (`topic=nest&topic=typescript`), giá trị `Date` trở thành chuỗi ISO, còn giá trị `null` và `undefined` bị bỏ qua. Request đầu tiên ở trên được gửi tới `https://api.github.com/orgs/nestjs/repos?type=public&sort=updated&topic=nest&topic=typescript`.
- `json` được serialize bằng `JSON.stringify()`, và đặt header `content-type: application/json` trừ khi bạn đã đặt header này.
- `body` được truyền nguyên vẹn cho `fetch`: một chuỗi, `Buffer`, `FormData`, `URLSearchParams`, `Blob`, một web stream hoặc Node.js stream, hoặc một async iterable. Hãy truyền `json` hoặc `body`, không truyền cả hai. Một request `GET` hoặc `HEAD` có body sẽ throw trước khi gửi bất cứ thứ gì.
- `headers` được merge đè lên header của client. Giá trị `null` sẽ bỏ một header.
- `timeout`, `retry`, `signal`, `throwOnHttpError`, `redirect` và `dispatcher` ghi đè thiết lập của client cho một request, và được trình bày bên dưới.
- `context` là một object tự do mà các [interceptor](/application/http-client#interceptors) có thể đọc.

Type argument, như `Repo[]`, mô tả `data`. Không có gì kiểm tra nó lúc runtime, nên hãy validate response từ những API bạn không kiểm soát. Tùy chọn `responseType` điều khiển cách đọc body:

| `responseType` | `data` |
| --- | --- |
| `'auto'` (mặc định) | JSON đã parse khi `content-type` là JSON (bao gồm các type `+json`), ngược lại là chuỗi. `undefined` khi body rỗng, với response `204` và `205`, và với request `HEAD`. Response `304` mặc định sẽ throw, giống như mọi response không phải 2xx; với `throwOnHttpError: false`, `data` của nó là `undefined`. |
| `'json'` | JSON đã parse, bất kể content type là gì. |
| `'text'` | Một chuỗi. |
| `'arrayBuffer'` | Một `ArrayBuffer`. |
| `'stream'` | Một `Readable` của Node.js. Xem [Stream response](/application/http-client#streaming-responses). |
| `'response'` | `Response` của web, với body chưa được đọc. |

Type của `data` đi theo `responseType`, nên `responseType: 'text'` resolve ra `HttpResponse<string>`. Một response thành công có body không phải JSON hợp lệ, dù lẽ ra phải là JSON, sẽ reject với một `HttpParseError`. Object response có cấu trúc như sau:

```typescript
interface HttpResponse<T> {
  status: number;
  statusText: string;
  ok: boolean;
  headers: Headers; // a web Headers object: headers.get('etag')
  data: T;
  url: string; // the final URL, after redirects
  request: HttpRequest; // the request that was sent, after interceptors ran
}
```

#### Timeout và hủy request <a id="timeouts-and-cancellation"></a>

`fetch` không có timeout riêng, ngoài giới hạn 5 phút của undici, HTTP client bên trong Node.js. Hãy đặt `timeout` cho mỗi client, tính bằng mili giây hoặc dưới dạng chuỗi thời lượng như `'500ms'`, `'5s'` hay `'2m'`. Một giá trị không hợp lệ sẽ lỗi ngay lúc khởi động, với thông báo lỗi nêu tên tùy chọn. `0` nghĩa là không có timeout, đây là giá trị mặc định.

Timeout áp dụng cho **mỗi lần thử**, không phải cho toàn bộ lời gọi. Nó bao gồm các interceptor của lần thử và việc đọc body của response. Với `responseType: 'stream'` và `'response'`, timeout dừng lại ngay khi header đến, để một lượt tải dài không bị cắt ngang. Khi hết thời gian, lần thử sẽ thất bại với một `HttpTimeoutError`, và request được retry như sau mọi [lỗi tạm thời](/application/http-client#retries) khác.

Để hủy một request, truyền một `AbortSignal` vào tùy chọn `signal`. Nó được kết hợp với timeout. Một request bị hủy sẽ reject với `reason` của signal, giống như `fetch`, và không bao giờ được retry, kể cả khi nó đang chờ giữa hai lần thử.

Vì có retry, một lời gọi có thể kéo dài tới `attempts × timeout`, cộng thêm thời gian chờ giữa các lần thử. Để giới hạn toàn bộ lời gọi, hãy truyền một deadline làm signal:

```typescript
const { data } = await this.github.get<Repo>('/repos/:owner/:repo', {
  params: { owner, repo },
  signal: AbortSignal.timeout(10_000),
});
```

Deadline sẽ reject với một `DOMException` có tên `TimeoutError`, thứ mà `toHttpException()` map thành `504 Gateway Timeout`, giống như `HttpTimeoutError`. Để kết hợp nó với một signal khác, dùng `AbortSignal.any([signal, AbortSignal.timeout(10_000)])`.

#### Retry <a id="retries"></a>

Retry được **bật mặc định**. Không cần cấu hình gì, client sẽ thử tối đa 3 lần với `GET`, `HEAD`, `OPTIONS`, `PUT` và `DELETE`, các method mà HTTP định nghĩa là idempotent. Nó retry sau khi gặp:

- lỗi kết nối, như kết nối bị từ chối hoặc bị reset (kể cả khi bị reset trong lúc đọc body),
- timeout của từng lần thử,
- các response `408`, `429`, `500`, `502`, `503` và `504`.

Giữa các lần thử, client chờ theo exponential backoff với full jitter: một khoảng trễ ngẫu nhiên tối đa 200 ms sau lần thử đầu, tối đa 400 ms sau lần thứ hai, v.v., giới hạn ở 30 giây. Header `Retry-After` của response, tính bằng giây hoặc dưới dạng HTTP date, sẽ thay thế backoff. Khi nó yêu cầu chờ lâu hơn mức giới hạn, client sẽ không chờ gì cả, mà trả về (hoặc throw) ngay response `429` hoặc `503`. Một request có body là stream sẽ không bao giờ được retry, vì lần thử đầu tiên đã đọc hết nó.

Tùy chọn `retry` nhận số lần thử, `false` để chỉ thử một lần, hoặc một object:

```typescript
HttpClientModule.register({
  name: 'github',
  baseUrl: 'https://api.github.com',
  retry: {
    attempts: 4, // in total, including the first request
    backoff: { delay: '500ms', factor: 2, maxDelay: '5s', jitter: 'full' },
    retryIf: (error, attempt) => !(error instanceof HttpNetworkError),
    methods: ['GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE'],
    statusCodes: [408, 429, 500, 502, 503, 504],
  },
}),
```

Mọi trường bạn bỏ qua đều giữ giá trị mặc định. `backoff` cũng có thể là một hàm nhận số thứ tự của lần thử bị lỗi cùng lỗi của nó, và trả về một khoảng thời gian. `jitter` có thể là `'full'`, `'equal'` (ít nhất một nửa khoảng trễ tính được), hoặc `'none'`. `retryIf` chỉ được hỏi về những lỗi mà client vốn sẽ retry, nên nó có thể thu hẹp các giá trị mặc định chứ không mở rộng được; hãy dùng `methods` và `statusCodes` cho việc đó. Nó nhận `HttpResponseError` (kèm `body`), `HttpTimeoutError` hoặc `HttpNetworkError` của lần thử bị lỗi.

Thiết lập retry được xếp theo tầng: `forRoot()`, rồi client, rồi request. Mỗi tầng chỉ ghi đè những trường nó đặt, và một tầng sau có thể bật lại retry sau khi một tầng trước đã đặt `false`. Tuy nhiên, `methods` và `statusCodes` sẽ **thay thế** danh sách mặc định thay vì thêm vào.

`POST` và `PATCH` không được retry, vì lặp lại chúng có thể, chẳng hạn, trừ tiền khách hàng hai lần. Khi API upstream hỗ trợ idempotency key, hãy gửi kèm một key và bật retry cho riêng request đó:

```typescript
const { data } = await this.payments.post<Charge>('/charges', {
  json: charge,
  headers: { 'idempotency-key': `charge-${order.id}` },
  retry: { methods: ['POST'] },
});
```

Key xác định thao tác, nên mọi lần thử đều gửi cùng một key, và upstream trả về kết quả ban đầu thay vì tạo ra lần trừ tiền thứ hai. Đặt `methods: ['POST']` trên client thay vì làm vậy sẽ dừng luôn cả retry của `GET`, vì danh sách đó thay thế danh sách mặc định.

> warning **Cảnh báo** Retry nhân lên dọc theo chuỗi service. Nếu service A gọi B, B gọi C, và mỗi chặng thử 3 lần, một request lỗi tới C sẽ biến thành 9 lời gọi tới C, đến đúng lúc C đang chật vật. Chỉ retry ở một tầng, thường là service gọi tới dependency bên ngoài, và đặt `retry: false` cho các client gọi tới service của chính bạn.

#### Xử lý lỗi <a id="handling-errors"></a>

Một request sẽ reject với một trong các lỗi sau, tất cả đều kế thừa class `HttpClientError`:

| Lỗi | Khi nào | Các trường |
| --- | --- | --- |
| `HttpResponseError` | Upstream trả lời với status không phải 2xx. | `status`, `statusText`, `headers`, `body` (JSON đã parse, nếu không thì là text), `method`, `url` |
| `HttpTimeoutError` | Hết `timeout` ở lần thử cuối cùng. | `timeoutMs`, `method`, `url` |
| `HttpNetworkError` | Kết nối thất bại: DNS, kết nối bị từ chối hoặc reset, TLS, hoặc một redirect mà client từ chối (sang origin khác, hoặc với `redirect: 'error'`). | `cause` (ví dụ với `cause.code` là `ECONNREFUSED`), `method`, `url` |
| `HttpParseError` | Một response thành công không phải JSON hợp lệ, dù lẽ ra phải là JSON. | `status`, `statusText`, `headers`, `body` (text gốc), `method`, `url` |

Một request bị hủy sẽ reject với reason của signal, và lỗi do interceptor throw được truyền ra nguyên vẹn. Một request mà client từ chối gửi, như request có giá trị `params` không hợp lệ, sẽ reject với một `TypeError`. Để nhận response không phải 2xx dưới dạng giá trị, hãy đặt `throwOnHttpError: false` trên client hoặc trên một request, và tự kiểm tra `ok` hoặc `status`.

Nếu một trong các lỗi này thoát ra khỏi route handler, Nest sẽ trả về `500 Internal Server Error`. Tuy nhiên, với bên gọi API của bạn, một upstream bị lỗi thường là `502 Bad Gateway`, còn một upstream không trả lời kịp là `504 Gateway Timeout`. Hàm `toHttpException()` map các lỗi theo đúng cách đó:

| Lỗi | Trở thành |
| --- | --- |
| `HttpResponseError` | `502 Bad Gateway`, hoặc status và body của upstream khi status đó được liệt kê trong `forward` |
| `HttpTimeoutError`, hoặc `TimeoutError` của một deadline `AbortSignal.timeout()` | `504 Gateway Timeout` |
| `HttpNetworkError`, `HttpParseError` | `502 Bad Gateway` |
| Mọi thứ khác, kể cả một `HttpException` | Được trả về nguyên vẹn, để Nest xử lý như bình thường |

```typescript
@@filename(repos.service)
async findOne(owner: string, repo: string): Promise<Repo> {
  try {
    const { data } = await this.github.get<Repo>('/repos/:owner/:repo', {
      params: { owner, repo },
    });
    return data;
  } catch (error) {
    if (error instanceof HttpResponseError && error.status === 404) {
      throw new NotFoundException(`Repository ${owner}/${repo} not found`);
    }
    throw toHttpException(error);
  }
}
```

Mặc định, body của upstream không được chuyển cho bên gọi, vì nó có thể mô tả chi tiết nội bộ của upstream. Để chuyển tiếp một số status được chọn kèm body, như một `422` có body cho bên gọi biết cần sửa gì, hãy dùng `toHttpException(error, options)` với `forward` đặt thành `[422]`, hoặc `true` cho mọi status. Lỗi gốc được giữ lại làm `cause` của exception.

Exception filter có sẵn của Nest [không log](/exception-filters#exceptions-logging) `HttpException`, nên một lỗi `502` hay `504` sẽ không để lại dấu vết gì. Vì vậy `toHttpException()` log mọi lỗi mà nó chuyển thành `5xx`, với context `HttpClient`:

```text
ERROR [HttpClient] GET https://api.github.com/repos/nestjs/nest failed with 503 Service Unavailable; answering 502 Bad Gateway
```

Đặt tùy chọn `log` thành `false` khi có thứ khác, như exception filter của riêng bạn, đã log các lỗi upstream.

Thay vì map lỗi trong từng service, bạn có thể để chúng thoát khỏi handler nguyên vẹn và map chúng trong một [exception filter](/exception-filters#binding-filters). Cách này giữ cho nơi gọi không phải viết `try`/`catch`, và các interceptor ở vòng ngoài vẫn thấy được lỗi gốc:

```typescript
@@filename(http-client-error.filter)
import { ArgumentsHost, Catch } from '@nestjs/common';
import { BaseExceptionFilter } from '@nestjs/core';
import { HttpClientError, toHttpException } from '@nestjs/http-client';

@Catch(HttpClientError)
export class HttpClientErrorFilter extends BaseExceptionFilter {
  catch(error: HttpClientError, host: ArgumentsHost) {
    super.catch(toHttpException(error), host);
  }
}
```

Deadline `AbortSignal.timeout()` không phải là `HttpClientError`, nên hãy thêm `DOMException` vào `@Catch()` nếu bạn dùng deadline. `toHttpException()` trả về một `HttpException`, nên trong handler của microservice hoặc WebSocket, hãy tự chuyển lỗi thành `RpcException` hoặc `WsException`.

> info **Gợi ý** Thông báo và object lỗi sẽ xuất hiện trong log, nên client giữ bí mật không bị lộ trong đó. Thông báo không bao giờ chứa body của response, và URL trong đó được che các giá trị query, như `GET https://api.example.com/users?email=***`. Các trường `url`, `headers` và `body` là non-enumerable: code của bạn đọc được chúng, nhưng logger và `JSON.stringify()` sẽ bỏ qua.

#### Interceptor <a id="interceptors"></a>

Interceptor bọc mọi request mà client gửi đi. Nó nhận request và một hàm `next` để gửi request đó, rồi trả về `Response` của web nhận được. Dạng đơn giản nhất là một hàm:

```typescript
@@filename(api-key.interceptor)
import type { HttpClientInterceptorFn } from '@nestjs/http-client';

export function apiKeyInterceptor(apiKey: string): HttpClientInterceptorFn {
  return (request, next) => {
    request.headers.set('x-api-key', apiKey);
    return next(request);
  };
}
```

Object `HttpRequest` chứa `method`, `url` (một instance `URL`), `headers` (một instance `Headers`), `body`, `signal`, số thứ tự `attempt`, và `context` của request. Bạn có thể sửa trực tiếp trên nó, hoặc truyền một bản sao đã sửa vào `next()`. Interceptor thấy response **trước** khi kiểm tra status, nên response `4xx` hay `5xx` cũng đến được với chúng. Một interceptor phải trả về thứ mà `next()` resolve ra, hoặc một `Response` của riêng nó.

Khi một interceptor cần các provider khác, hãy viết nó dưới dạng class implement interface `HttpClientInterceptor`:

```typescript
@@filename(github-auth.interceptor)
import { Injectable } from '@nestjs/common';
import type { HttpClientInterceptor, HttpHandler, HttpRequest } from '@nestjs/http-client';
import { GithubTokenService } from './github-token.service.js';

@Injectable()
export class GithubAuthInterceptor implements HttpClientInterceptor {
  constructor(private readonly tokens: GithubTokenService) {}

  async intercept(request: HttpRequest, next: HttpHandler): Promise<Response> {
    request.headers.set('authorization', `Bearer ${await this.tokens.getToken()}`);
    return next(request);
  }
}
```

Truyền interceptor vào mảng `interceptors` của `register()` hoặc `forRoot()`, hoặc đặt cạnh `useFactory` trong các biến thể bất đồng bộ:

```typescript
@@filename(repos.module)
@Module({
  imports: [
    HttpClientModule.register({
      name: 'github',
      baseUrl: 'https://api.github.com',
      interceptors: [GithubAuthInterceptor],
    }),
  ],
  providers: [GithubTokenService, GithubAuthInterceptor, ReposService],
})
export class ReposModule {}
```

Nest resolve các class interceptor khi ứng dụng khởi tạo, nên một interceptor thậm chí có thể phụ thuộc vào một service inject chính client đó. Nếu class là một provider ở bất cứ đâu trong ứng dụng, như `GithubAuthInterceptor` ở trên, instance đó sẽ được dùng. Nếu không, Nest tạo nó bên trong module riêng của client, module này nhìn thấy các global provider và các module bạn truyền vào tùy chọn `imports` của `register()`. Một factory bất đồng bộ cũng có thể trả về interceptor trong tùy chọn của nó, nhưng chỉ là hàm và instance, như `apiKeyInterceptor(config.getOrThrow('API_KEY'))`.

Interceptor chạy theo thứ tự được liệt kê, cái đầu tiên ở ngoài cùng, và các interceptor của `forRoot()` chạy trước các interceptor riêng của client. Chúng chạy **một lần cho mỗi lần thử**, nên một lần retry sẽ lấy token mới, và `request.attempt` cho chúng biết đây là lần thử thứ mấy. Khi một lần thử thất bại, `next()` reject với một `HttpNetworkError` hoặc `HttpTimeoutError`, hoặc với abort reason. Điều này khiến interceptor là nơi tốt để log traffic tới upstream:

```typescript
@@filename(http-logging.interceptor)
import { Injectable, Logger } from '@nestjs/common';
import type { HttpClientInterceptor, HttpHandler, HttpRequest } from '@nestjs/http-client';

@Injectable()
export class HttpLoggingInterceptor implements HttpClientInterceptor {
  private readonly logger = new Logger('HttpClient');

  async intercept(request: HttpRequest, next: HttpHandler): Promise<Response> {
    const target = `${request.method} ${request.url.origin}${request.url.pathname}`;
    const start = performance.now();
    try {
      const response = await next(request);
      const ms = Math.round(performance.now() - start);
      this.logger.log(`${target} ${response.status} ${ms}ms (attempt ${request.attempt})`);
      return response;
    } catch (error) {
      this.logger.warn(`${target} failed: ${(error as Error).name} (attempt ${request.attempt})`);
      throw error;
    }
  }
}
```

Khi đăng ký bằng `HttpClientModule.forRoot()` và `interceptors: [HttpLoggingInterceptor]`, nó log request của mọi client. Nó log path mà không kèm query string, vì query string thường chứa dữ liệu cá nhân hoặc key.

> info **Gợi ý** Để tracing, bạn không cần interceptor. [NestJS Observe](/observability/distributed-tracing#http-to-http) ghi lại mọi lời gọi `fetch` đi ra dưới dạng span, và truyền trace id tới các service Nest khác.

#### Stream response <a id="streaming-responses"></a>

Để chuyển tiếp một response lớn mà không buffer nó trong bộ nhớ, đặt `responseType: 'stream'`. `data` sẽ là một `Readable` của Node.js, bạn có thể trả nó về từ route handler trong một [`StreamableFile`](/http/file-upload#streaming-files):

```typescript
@@filename(invoices.controller)
@Get(':id/pdf')
async download(@Param('id') id: string): Promise<StreamableFile> {
  const { data, headers } = await this.billing.get('/invoices/:id/pdf', {
    params: { id },
    responseType: 'stream',
  });
  return new StreamableFile(data, {
    type: headers.get('content-type') ?? 'application/pdf',
  });
}
```

Timeout dừng lại khi header đến, trong khi hủy `signal` vẫn dừng được việc tải. Một response không phải 2xx vẫn được đọc và throw dưới dạng `HttpResponseError`, như bình thường. Đừng chuyển header `content-length` của upstream thành tùy chọn `length`: `fetch` giải nén body gzip và brotli, nên stream có thể dài hơn những gì header ghi. Để lấy `ReadableStream` của web, dùng `responseType: 'response'` và đọc `data.body`.

#### Proxy, TLS và redirect <a id="proxies-tls-and-redirects"></a>

`fetch` của Node.js chạy trên undici, với dispatcher mặc định giữ một pool các kết nối keep-alive, nên trường hợp phổ biến không cần cấu hình gì. Để thay đổi kích thước pool, đi qua proxy, hoặc dùng thiết lập TLS tùy chỉnh (CA riêng, hoặc client certificate), hãy truyền một dispatcher của undici vào tùy chọn `dispatcher`:

```typescript
@@filename(partner.module)
import { readFileSync } from 'node:fs';
import { Agent } from 'undici';

@Module({
  imports: [
    HttpClientModule.register({
      name: 'partner',
      baseUrl: 'https://partner.example.com',
      dispatcher: new Agent({
        connections: 20,
        connect: {
          ca: readFileSync('certs/partner-ca.pem'),
          cert: readFileSync('certs/client.pem'),
          key: readFileSync('certs/client-key.pem'),
        },
      }),
    }),
  ],
})
export class PartnerModule {}
```

Với proxy, truyền `new ProxyAgent('http://proxy.internal:3128')`. Node.js không cung cấp các class này từ một module có sẵn, nên bạn phải tự cài package `undici` (`@nestjs/http-client` không phụ thuộc vào nó), tốt nhất là đúng major version mà bản Node.js của bạn đóng gói kèm. Một `http.Agent` của Node.js, thứ mà Axios nhận dưới dạng `httpsAgent`, không hoạt động với `fetch`, và sẽ không compile được. Để mọi client đi qua proxy lấy từ các biến môi trường `HTTP_PROXY`, `HTTPS_PROXY` và `NO_PROXY`, hãy khởi động Node.js với `--use-env-proxy` (hoặc đặt `NODE_USE_ENV_PROXY=1`) trên một bản có hỗ trợ.

Tùy chọn `redirect` điều khiển cách xử lý response `3xx`. Một client có `baseUrl` chỉ đi theo redirect trong cùng origin của nó, và báo lỗi `HttpNetworkError` với redirect sang host khác, vì header của nó mang thông tin xác thực của upstream đó (xem [Bảo mật](/application/http-client#security)). Một client không có `baseUrl` để `fetch` đi theo redirect tới bất cứ đâu, bỏ header `authorization` và `cookie` khi origin thay đổi, nhưng không bỏ các header khác.

Đặt `redirect` thành `'follow'` để đi theo redirect tới bất cứ đâu kể cả khi có `baseUrl`, cho một API cố ý redirect sang host khác; thành `'error'` để báo lỗi với mọi redirect; hoặc thành `'manual'` để nhận nguyên vẹn các response `3xx`. Một response `3xx` không phải là thành công, nên hãy kết hợp `'manual'` với `throwOnHttpError: false` để đọc header `location` của nó.

#### Bảo mật <a id="security"></a>

Client có cơ chế phòng tránh vài sai lầm phổ biến:

- **Một client có `baseUrl` chỉ gửi request tới origin của nó.** Một URL tuyệt đối cùng origin, như link phân trang, vẫn dùng được, nhưng URL trên host khác sẽ throw trước khi gửi bất cứ thứ gì. Redirect sang host khác cũng bị lỗi, trước khi request được lặp lại ở đó. Header và interceptor của client mang thông tin xác thực của upstream đó, và một URL lấy từ dữ liệu người dùng nhập vào hoặc từ response của upstream không được phép nhận chúng. Hãy dùng client không có `baseUrl` để gọi tới các host tùy ý, hoặc `redirect: 'follow'` cho một API cố ý redirect sang host khác.
- **Path parameter được encode.** Hãy đặt các giá trị của request vào `params` và `query` thay vì tự ghép path bằng string interpolation. Chúng được URI-encode, và một giá trị `params` như `..` sẽ throw thay vì đẩy request sang endpoint khác.
- **Thông tin xác thực trong URL bị từ chối.** Một `baseUrl` hoặc URL request như `https://user:pass@example.com` sẽ throw. Hãy gửi thông tin xác thực trong header `authorization`. Một giá trị header có ký tự xuống dòng sẽ throw, mà không trích giá trị đó trong thông báo lỗi.
- **Lỗi an toàn để log**, như mô tả trong [Xử lý lỗi](/application/http-client#handling-errors).

#### Test <a id="testing"></a>

Một `fetch` giả (stub) là cách dễ nhất để test code gọi tới API bên ngoài. Truyền nó vào `HttpClientModule.forRoot()`, và mọi client sẽ dùng nó, trong khi vẫn giữ base URL, header, chính sách retry và interceptor của mình. Stub chỉ cần trả về một `Response` chuẩn:

```typescript
@@filename(repos.service.spec)
import { Test } from '@nestjs/testing';
import { HttpClientModule } from '@nestjs/http-client';
import { vi } from 'vitest';
import { ReposModule } from './repos.module.js';
import { ReposService } from './repos.service.js';

describe('ReposService', () => {
  const fetch = vi.fn<typeof globalThis.fetch>();
  let repos: ReposService;

  beforeEach(async () => {
    fetch.mockReset();
    const moduleRef = await Test.createTestingModule({
      imports: [HttpClientModule.forRoot({ fetch }), ReposModule],
    }).compile();
    await moduleRef.init();
    repos = moduleRef.get(ReposService);
  });

  it('lists the public repositories of an organization', async () => {
    fetch.mockResolvedValueOnce(Response.json([{ name: 'nest' }]));

    await expect(repos.findAll('nestjs')).resolves.toEqual([{ name: 'nest' }]);
    const [url] = fetch.mock.calls[0];
    expect(String(url)).toBe(
      'https://api.github.com/orgs/nestjs/repos?type=public&sort=updated&topic=nest&topic=typescript',
    );
  });

  it('retries a 503', async () => {
    fetch
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(Response.json([]));

    await expect(repos.findAll('nestjs')).resolves.toEqual([]);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
```

Hãy cho mỗi lời gọi một `Response` riêng, như `mockResolvedValueOnce()` làm ở trên: body của response chỉ đọc được một lần, nên `mockResolvedValue()` sẽ đưa một response đã đọc rồi cho lần retry. Một client tự đặt tùy chọn `fetch` riêng sẽ giữ nguyên nó, vì thiết lập của client thắng giá trị mặc định của `forRoot()`. Một client không có tùy chọn này sẽ gọi `globalThis.fetch` ở mỗi request, nên `vi.stubGlobal('fetch', stub)` cũng dùng được.

Với e2e test cho một ứng dụng đã gọi `forRoot()`, hãy ghi đè tùy chọn của nó. Cách này thay thế mọi tùy chọn của `forRoot()`, ngoại trừ các interceptor truyền trực tiếp vào `forRoot()` hoặc đặt cạnh `useFactory`, những interceptor này vẫn tiếp tục chạy:

```typescript
const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
  .overrideProvider(HTTP_CLIENT_MODULE_OPTIONS)
  .useValue({ fetch })
  .compile();
```

Để hoàn toàn loại bỏ HTTP khỏi một bài test, hãy thay chính client bằng `overrideProvider(getHttpClientToken('github'))`. Bên ngoài Nest, ví dụ trong một script, hãy tạo client bằng `new HttpClient(options)`.
#### Làm việc với RxJS <a id="working-with-rxjs"></a>

Để kết hợp một request với các operator của RxJS, hãy bọc nó trong một Observable. `defer()` bắt đầu request khi Observable được subscribe, còn `from()` bắt đầu ngay lập tức:

```typescript
import { defer } from 'rxjs';

const cats$ = defer(() => this.http.get<Cat[]>('/cats'));
```

Cả hai đều không hủy request khi unsubscribe. Khi bạn cần điều đó, ví dụ với `switchMap()`, hãy nối việc unsubscribe với một `AbortController`:

```typescript
import { Observable } from 'rxjs';

function fromRequest<T>(send: (signal: AbortSignal) => Promise<T>): Observable<T> {
  return new Observable<T>((subscriber) => {
    const controller = new AbortController();
    send(controller.signal).then(
      (value) => {
        subscriber.next(value);
        subscriber.complete();
      },
      (error) => subscriber.error(error),
    );
    return () => controller.abort();
  });
}

const cats$ = fromRequest((signal) => this.http.get<Cat[]>('/cats', { signal }));
```

#### Chuyển từ `@nestjs/axios` <a id="migrating-from-nestjsaxios"></a>

Package `@nestjs/axios` vẫn có sẵn, và cả hai package có thể được cài song song trong lúc bạn chuyển đổi. Bảng sau ánh xạ các tính năng của nó sang `@nestjs/http-client`:

| `@nestjs/axios` | `@nestjs/http-client` |
| --- | --- |
| `HttpModule.register()` với `baseURL` | `HttpClientModule.register()` với `baseUrl` |
| `HttpModule.registerAsync()` | `HttpClientModule.registerAsync()`, nhận thêm cả `name` |
| `HttpModuleOptionsFactory` với `createHttpOptions()` | `HttpClientOptionsFactory` với `createHttpClientOptions()` |
| `extraProviders` trong `registerAsync()` | Một module export các provider, truyền vào `imports` |
| Mỗi module import có một `HttpService` | Client có tên, inject bằng `@InjectHttpClient(name)` |
| Các method của `HttpService`, trả về Observable | Các method của `HttpClient`, trả về Promise |
| `firstValueFrom(this.httpService.get(url))` | `await this.http.get(url)` |
| `post(url, data)` | `post(url, options)`, với dữ liệu nằm trong `json` (hoặc `body`) |
| `params` trong config của request | `query`. Mảng sẽ lặp lại key, trong khi Axios viết `key[]=`. Trong `@nestjs/http-client`, `params` điền vào các segment `:name` của path, và throw với key không khớp segment nào. |
| `response.headers['etag']` | `response.headers.get('etag')` |
| `AxiosError` với `error.response?.status` | `HttpResponseError` với `error.status` và `error.body` |
| `error.code === 'ECONNABORTED'` | `HttpTimeoutError` |
| `validateStatus: () => true` | `throwOnHttpError: false` |
| `axiosRef` (instance Axios) | Không có instance bên dưới. Hãy dùng tùy chọn của client, hoặc truyền một hàm tùy chỉnh làm `fetch`. |
| `axiosRef.interceptors.request.use()` và `response.use()` | `interceptors`, một hàm duy nhất cho cả request lẫn response |
| `httpsAgent` hoặc `proxy` | `dispatcher`, một `Agent` hoặc `ProxyAgent` của undici |
| `maxRedirects: 0` | `redirect: 'manual'` |
| Không có retry, trừ khi bạn thêm `axios-retry` | Retry bật mặc định cho các method idempotent. `retry: false` khôi phục hành vi của Axios. |
| `timeout` cho toàn bộ request | `timeout` cho mỗi lần thử, có thể viết dạng chuỗi như `'5s'` |
| `onUploadProgress`, `onDownloadProgress` | Không có tương đương. Hãy tự đếm byte của một stream. |
