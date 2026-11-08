### Security header

Security header, như những header mà [Helmet](https://github.com/helmetjs/helmet) đặt, báo cho trình duyệt bật các cơ chế bảo vệ chống lại những kiểu tấn công web phổ biến như cross-site scripting và clickjacking. Ví dụ như `Content-Security-Policy`, `Strict-Transport-Security` và `X-Frame-Options`.

Kể từ NestJS v12.1, Nest có thể đặt các header này giúp bạn bằng `app.useSecurityHeaders()`. Nó dùng cùng các giá trị mặc định như Helmet 8, hoạt động giống nhau trên Express và Fastify, và không cần cài thêm package nào.

#### Bắt đầu <a id="getting-started"></a>

Để bật các header, gọi method `useSecurityHeaders()` trên object ứng dụng Nest:

```typescript
// main.ts
const app = await NestFactory.create(AppModule);
app.useSecurityHeaders();
await app.listen(process.env.PORT ?? 3000);
```

Các header được đặt trên mọi response: response của route, response `404`, response lỗi, response bị [cơ chế bảo vệ CSRF](/security/csrf) từ chối, và các stream Server-Sent Events. Header `X-Powered-By` bị xóa. Các quy tắc sau được áp dụng:

- Gọi `useSecurityHeaders()` trước `app.init()` hoặc `app.listen()`. Gọi nó sau đó, hoặc gọi hai lần, sẽ throw lỗi.
- Các tùy chọn được validate ngay khi bạn gọi method, nên một cấu hình sai sẽ lỗi lúc khởi động (xem [Cấu hình header](/security/helmet#configuring-headers)).
- Các header được ghi bởi một middleware ở cấp framework (Express) hoặc hook `onRequest` (Fastify), được đăng ký tại thời điểm bạn gọi method. Middleware đăng ký bằng `app.use()` trước lời gọi đó sẽ chạy trước, và những response mà middleware đó tự gửi sẽ không mang các header này, nên hãy gọi `useSecurityHeaders()` ngay sau `NestFactory.create()`.
- `app.enableCsrfProtection()` dùng chung request hook. Bạn có thể gọi hai method theo bất kỳ thứ tự nào: các header luôn được ghi trước khi bước kiểm tra CSRF chạy.

#### Header mặc định <a id="default-headers"></a>

Không có tùy chọn, `useSecurityHeaders()` gửi các header sau, với cùng giá trị như Helmet 8:

| Header                              | Giá trị mặc định                                                | Tùy chọn                        |
| ----------------------------------- | --------------------------------------------------------------- | ------------------------------- |
| `Content-Security-Policy`           | Xem [Content Security Policy](/security/helmet#content-security-policy) | `contentSecurityPolicy`         |
| `Cross-Origin-Embedder-Policy`      | Không gửi                                                       | `crossOriginEmbedderPolicy`     |
| `Cross-Origin-Opener-Policy`        | `same-origin`                                                   | `crossOriginOpenerPolicy`       |
| `Cross-Origin-Resource-Policy`      | `same-origin`                                                   | `crossOriginResourcePolicy`     |
| `Origin-Agent-Cluster`              | `?1`                                                            | `originAgentCluster`            |
| `Referrer-Policy`                   | `no-referrer`                                                   | `referrerPolicy`                |
| `Strict-Transport-Security`         | `max-age=31536000; includeSubDomains`                           | `strictTransportSecurity`       |
| `X-Content-Type-Options`            | `nosniff`                                                       | `xContentTypeOptions`           |
| `X-DNS-Prefetch-Control`            | `off`                                                           | `xDnsPrefetchControl`           |
| `X-Download-Options`                | `noopen`                                                        | `xDownloadOptions`              |
| `X-Frame-Options`                   | `SAMEORIGIN`                                                    | `xFrameOptions`                 |
| `X-Permitted-Cross-Domain-Policies` | `none`                                                          | `xPermittedCrossDomainPolicies` |
| `X-XSS-Protection`                  | `0`                                                             | `xXssProtection`                |
| `X-Powered-By`                      | Bị xóa                                                          | `xPoweredBy`                    |

> info **Gợi ý** Trình duyệt bỏ qua `Strict-Transport-Security` qua HTTP thường, còn `X-XSS-Protection: 0` tắt bộ kiểm tra XSS của các trình duyệt cũ, vốn bản thân nó cũng là nguồn gây ra lỗ hổng.

#### Cấu hình header <a id="configuring-headers"></a>

Mỗi tùy chọn điều khiển một header. Truyền `false` để bỏ header đi, `true` để gửi giá trị mặc định của nó, hoặc một object để cấu hình nó:

```typescript
app.useSecurityHeaders({
  xFrameOptions: false,
  strictTransportSecurity: { maxAge: 63072000, preload: true },
  referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
});
```

Các tùy chọn nhận object có các thuộc tính sau:

| Tùy chọn                        | Thuộc tính                                                                                                                                            |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `contentSecurityPolicy`         | `directives`, `useDefaults` (mặc định `true`) và `reportOnly` (mặc định `false`). Xem [Content Security Policy](/security/helmet#content-security-policy). |
| `crossOriginEmbedderPolicy`     | `policy`: `'require-corp'` (gửi khi là `true`), `'credentialless'` hoặc `'unsafe-none'`.                                                              |
| `crossOriginOpenerPolicy`       | `policy`: `'same-origin'` (mặc định), `'same-origin-allow-popups'`, `'noopener-allow-popups'` hoặc `'unsafe-none'`.                                   |
| `crossOriginResourcePolicy`     | `policy`: `'same-origin'` (mặc định), `'same-site'` hoặc `'cross-origin'`.                                                                            |
| `referrerPolicy`                | `policy`: một referrer policy như `'strict-origin-when-cross-origin'` (mặc định `'no-referrer'`), hoặc một danh sách policy, mà trình duyệt đọc như một chuỗi dự phòng. |
| `strictTransportSecurity`       | `maxAge` tính bằng giây (mặc định `31536000`, tức 365 ngày), `includeSubDomains` (mặc định `true`) và `preload` (mặc định `false`).                    |
| `xDnsPrefetchControl`           | `allow` (mặc định `false`). `true` sẽ gửi `on`.                                                                                                       |
| `xFrameOptions`                 | `action`: `'sameorigin'` (mặc định) hoặc `'deny'`.                                                                                                    |
| `xPermittedCrossDomainPolicies` | `permittedPolicies`: `'none'` (mặc định), `'master-only'`, `'by-content-type'` hoặc `'all'`.                                                          |

Các tùy chọn còn lại, `originAgentCluster`, `xContentTypeOptions`, `xDownloadOptions`, `xPoweredBy` và `xXssProtection`, chỉ nhận giá trị boolean. Ví dụ, `xPoweredBy: false` giữ lại header `X-Powered-By`.

Tùy chọn không xác định, thuộc tính không xác định và giá trị không hợp lệ sẽ throw khi gọi `useSecurityHeaders()`. Các tên tùy chọn cũ của Helmet bị từ chối kèm gợi ý về tên hiện tại, ví dụ `Invalid security headers configuration: unknown option "hsts" (helmet's legacy name, use "strictTransportSecurity").`

Một route vẫn có thể ghi đè một header bằng decorator [`@Header()`](/controllers#response-headers), ví dụ để cho phép các site khác load một hình ảnh:

```typescript
@Get('avatars/:id')
@Header('Cross-Origin-Resource-Policy', 'cross-origin')
findAvatar(@Param('id') id: string) {}
```

> info **Gợi ý** Trên Fastify, `reply.header()` cũng ghi đè được một header, nhưng `reply.removeHeader()` không thể xóa một header do `useSecurityHeaders()` đặt.

#### Content Security Policy

`Content-Security-Policy` mặc định giống với của Helmet 8. Nó được gửi trên một dòng, không có dấu cách sau dấu chấm phẩy:

```text
default-src 'self';
base-uri 'self';
font-src 'self' https: data:;
form-action 'self';
frame-ancestors 'self';
img-src 'self' data:;
object-src 'none';
script-src 'self';
script-src-attr 'none';
style-src 'self' https: 'unsafe-inline';
upgrade-insecure-requests
```

Dùng thuộc tính `directives` để thay đổi nó:

```typescript
app.useSecurityHeaders({
  contentSecurityPolicy: {
    directives: {
      scriptSrc: ["'self'", 'https://cdn.example.com'],
      connectSrc: ["'self'", 'wss://realtime.example.com'],
      upgradeInsecureRequests: null,
    },
  },
});
```

Các directive hoạt động như sau:

- Tên được viết theo camelCase (`scriptSrc`) hoặc kebab-case (`'script-src'`).
- Một directive bạn đặt sẽ **thay thế** directive mặc định cùng tên, nên hãy thêm `'self'` khi bạn muốn giữ nó. Các directive khác được thêm vào policy.
- Một giá trị là một chuỗi hoặc một danh sách chuỗi. `true` hoặc danh sách rỗng sẽ gửi directive không có giá trị, còn `null` hoặc `false` sẽ xóa một directive, kể cả directive mặc định.
- Từ khóa, nonce và hash phải đặt trong dấu nháy đơn, như `"'self'"`. Một `self` không có dấu nháy sẽ bị từ chối, vì trình duyệt sẽ đọc nó như một host name.
- Giá trị chỉ được chứa ký tự ASCII in được, và không được chứa `;` hay `,`, nên một giá trị không thể thêm directive hay policy.

Để chỉ gửi các directive của riêng bạn, đặt `useDefaults` thành `false`. Khi đó policy cần một directive `defaultSrc`, trừ khi bạn đặt `defaultSrc: null` để cố ý bỏ nó đi.

Để thử một policy mà không làm hỏng các trang, đặt `reportOnly` thành `true`. Khi đó Nest gửi `Content-Security-Policy-Report-Only`, và trình duyệt báo cáo vi phạm thay vì chặn chúng. Thêm một directive `report-to` hoặc `report-uri` để nhận các báo cáo.

```typescript
app.useSecurityHeaders({
  contentSecurityPolicy: { reportOnly: true },
});
```

Để bỏ hoàn toàn header này, đặt `contentSecurityPolicy` thành `false`.

#### Swagger UI và các GraphQL IDE <a id="swagger-ui-and-graphql-ides"></a>

Policy áp dụng cho mọi response, kể cả các trang HTML của các công cụ API.

[Swagger UI](/openapi/introduction) do `@nestjs/swagger` phục vụ load script và stylesheet từ chính ứng dụng của bạn, nên nó chạy được với policy mặc định. Nếu bạn thêm script bằng tùy chọn `customJs`, hãy thêm host của chúng vào `scriptSrc`. Code inline từ tùy chọn `customJsStr` cần `'unsafe-inline'`. Directive mặc định `upgrade-insecure-requests` khiến trình duyệt load script và stylesheet qua HTTPS, nên nếu bạn phục vụ Swagger UI qua HTTP thường ngoài môi trường phát triển local, ví dụ trên một staging server truy cập bằng địa chỉ IP, chúng sẽ load thất bại. Hãy phục vụ Swagger UI qua HTTPS, hoặc xóa directive đó bằng `upgradeInsecureRequests: null`.

[GraphiQL](/graphql/quick-start#graphql-ide), do Apollo driver phục vụ, load React và GraphiQL từ `unpkg.com` và khởi động bằng một script inline. Mặc định, GraphiQL chỉ được bật khi `NODE_ENV` không phải `production`, nên chỉ nới lỏng policy ở đó:

```typescript
const isProduction = process.env.NODE_ENV === 'production';

app.useSecurityHeaders({
  contentSecurityPolicy: isProduction
    ? true
    : {
        directives: {
          scriptSrc: ["'self'", "'unsafe-inline'", 'https://unpkg.com'],
        },
      },
});
```

[Apollo Sandbox](/graphql/quick-start#apollo-sandbox), được bật bằng `ApolloServerPluginLandingPageLocalDefault()`, load script, hình ảnh và manifest của nó từ CDN của Apollo, và nhúng Sandbox trong một frame:

```typescript
app.useSecurityHeaders({
  contentSecurityPolicy: {
    directives: {
      scriptSrc: [
        "'self'",
        "'unsafe-inline'",
        'https://embeddable-sandbox.cdn.apollographql.com',
      ],
      imgSrc: [
        "'self'",
        'data:',
        'https://apollo-server-landing-page.cdn.apollographql.com',
      ],
      manifestSrc: [
        "'self'",
        'https://apollo-server-landing-page.cdn.apollographql.com',
      ],
      frameSrc: ["'self'", 'https://sandbox.embed.apollographql.com'],
    },
  },
});
```

> warning **Cảnh báo** `'unsafe-inline'` trong `script-src` từ bỏ phần lớn khả năng bảo vệ mà CSP mang lại chống lại cross-site scripting, cho mọi trang mà ứng dụng của bạn phục vụ. Hãy tránh dùng nó trên production.

#### Dùng trực tiếp Helmet <a id="using-helmet-directly"></a>

Các ứng dụng đang dùng Helmet có thể tiếp tục dùng nó. Vì tên tùy chọn của `useSecurityHeaders()` giống với của Helmet, một cấu hình Helmet thường chuyển sang được khi bạn đổi, với hai ngoại lệ:

- Giá trị của directive CSP phải là chuỗi, danh sách chuỗi, boolean hoặc `null`. Hàm, thứ mà Helmet chấp nhận để sinh nonce theo từng request, không được hỗ trợ.
- Các tên tùy chọn cũ của Helmet bị từ chối:

| Tên cũ của Helmet              | Tùy chọn                        |
| ------------------------------ | ------------------------------- |
| `dnsPrefetchControl`           | `xDnsPrefetchControl`           |
| `frameguard`                   | `xFrameOptions`                 |
| `hidePoweredBy`                | `xPoweredBy`                    |
| `hsts`                         | `strictTransportSecurity`       |
| `ieNoOpen`                     | `xDownloadOptions`              |
| `noSniff`                      | `xContentTypeOptions`           |
| `permittedCrossDomainPolicies` | `xPermittedCrossDomainPolicies` |
| `xssFilter`                    | `xXssProtection`                |

Để dùng chính Helmet, hãy cài package cho nền tảng của bạn và đăng ký nó trước các lời gọi `app.use()` khác hoặc các hàm thiết lập có thể gọi `app.use()`. Nền tảng bên dưới áp dụng middleware theo thứ tự đăng ký, nên Helmet đăng ký sau một route sẽ không áp dụng cho route đó. Các directive CSP ở trên cũng dùng được với tùy chọn `contentSecurityPolicy` của Helmet.

##### Express

```bash
$ npm i helmet
```

```typescript
// main.ts
import helmet from 'helmet';

app.use(helmet());
```

##### Fastify

Với `FastifyAdapter`, hãy dùng package [@fastify/helmet](https://github.com/fastify/fastify-helmet). Đây là một [Fastify plugin](https://fastify.dev/docs/latest/Reference/Plugins/), không phải middleware, nên hãy đăng ký nó bằng `app.register()`:

```bash
$ npm i @fastify/helmet
```

```typescript
// main.ts
import helmet from '@fastify/helmet';

await app.register(helmet);
```
