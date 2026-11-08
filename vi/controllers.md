### Controllers

Controller chịu trách nhiệm xử lý các **request** gửi đến và trả **response** về cho client.

<figure><img class="illustrative-image" src="/assets/Controllers_1.png" /></figure>

Mục đích của một controller là xử lý những request cụ thể của ứng dụng. Cơ chế **routing** quyết định controller nào sẽ xử lý request nào. Một controller thường có nhiều route, và mỗi route có thể thực hiện một hành động khác nhau.

Để tạo một controller cơ bản, ta dùng class và **decorator**. Decorator gắn metadata cần thiết vào class, và Nest dựa vào metadata đó để xây dựng routing map, nối mỗi request tới controller tương ứng.

> info **Gợi ý** Để tạo một CRUD controller có sẵn [validation](https://docs.nestjs.com/application/validation), dùng [CRUD generator](https://docs.nestjs.com/recipes/crud-generator#crud-generator) của CLI: `nest g resource [name]`.

#### Routing

Ví dụ sau dùng decorator `@Controller()`, decorator **bắt buộc** để định nghĩa một controller cơ bản, với prefix route path tùy chọn là `cats`. Đặt prefix trong decorator `@Controller()` giúp gom các route liên quan lại với nhau và bớt code lặp. Ví dụ, để gom các route quản lý entity cat vào path `/cats`, ta khai báo prefix `cats` trong decorator `@Controller()`. Khi đó bạn không cần lặp lại phần path này cho từng route trong file.

```typescript
@@filename(cats.controller)
import { Controller, Get } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Get()
  findAll(): string {
    return 'This action returns all cats';
  }
}
@@switch
import { Controller, Get } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Get()
  findAll() {
    return 'This action returns all cats';
  }
}
```

> info **Gợi ý** Để tạo controller bằng CLI, chạy lệnh `$ nest g controller [name]`.

Decorator HTTP request method `@Get()` đặt trước method `findAll()` báo cho Nest tạo một handler cho một endpoint cụ thể. Một endpoint được xác định bởi HTTP request method (ở đây là GET) và route path. Route path của một handler là sự kết hợp giữa prefix (tùy chọn) khai báo cho controller **và** path chỉ định trong decorator của method. Vì ví dụ trên có đặt prefix (`cats`) nhưng không có path trong decorator của method, Nest sẽ map các request `GET /cats` tới handler này.

Nếu decorator của method cũng chỉ định path, chẳng hạn `@Get('breed')`, route cuối cùng sẽ là `GET /cats/breed`.

Khi có request `GET /cats` đến, Nest điều hướng nó tới method `findAll()` do bạn định nghĩa. Tên method đặt tùy ý: bạn phải khai báo một method để bind route vào, nhưng Nest không quan tâm tên của nó là gì.

Method này trả về status code 200 cùng với response tương ứng, trong trường hợp này là một chuỗi. Để giải thích vì sao, ta cần giới thiệu hai cách **khác nhau** mà Nest cung cấp để thao tác với response:

<table>
  <tr>
    <td>Chuẩn (khuyên dùng)</td>
    <td>
      Với cách có sẵn này, khi route handler trả về một object hoặc mảng JavaScript, nó sẽ được <strong>tự động</strong>
      serialize thành JSON. Khi handler trả về một kiểu primitive của JavaScript (ví dụ: <code>string</code>, <code>number</code>, <code>boolean</code>), Nest gửi giá trị đó đi mà không cố serialize. Nhờ vậy, việc xử lý response rất đơn giản: chỉ cần trả về giá trị, Nest lo phần còn lại.
      <br />
      <br /> <strong>Status code</strong> của response mặc định là 200, trừ request POST
      dùng 201. Bạn có thể thay đổi hành vi này bằng cách thêm decorator <code>@HttpCode(...)</code>
      ở cấp handler (xem <a href='controllers#status-code'>Status code</a>).
    </td>
  </tr>
  <tr>
    <td>Riêng của library</td>
    <td>
      Bạn có thể dùng <a href="https://expressjs.com/en/api.html#res" rel="nofollow" target="_blank">response object</a> riêng của library (ví dụ Express), được inject bằng decorator <code>@Res()</code> trong signature của route handler (ví dụ: <code>findAll(@Res() response)</code>). Cách này cho phép bạn dùng các method xử lý response gốc mà object đó cung cấp. Ví dụ, với Express, bạn có thể tạo response bằng code như <code>response.status(200).send()</code>.
    </td>
  </tr>
</table>

> warning **Cảnh báo** Nest phát hiện khi một handler dùng `@Res()` hoặc `@Next()`, tức là bạn đã chọn cách riêng của library. Nếu dùng cả hai cách cùng lúc, cách chuẩn sẽ bị **tự động vô hiệu hóa** cho route đó và không còn hoạt động như mong đợi. Để kết hợp cả hai (ví dụ, inject response object chỉ để set cookie hoặc header, còn lại để framework lo), hãy đặt tùy chọn `passthrough` thành `true` trong decorator `@Res({{ '{' }} passthrough: true {{ '}' }})`.

<app-banner-observe></app-banner-observe>

#### Request object

Handler thường cần truy cập thông tin **request** của client. Nest cho phép truy cập [request object](https://expressjs.com/en/api.html#req) của nền tảng bên dưới (mặc định là Express). Để lấy nó, thêm decorator `@Req()` vào signature của handler, decorator này yêu cầu Nest inject request object vào.

```typescript
@@filename(cats.controller)
import { Controller, Get, Req } from '@nestjs/common';
import type { Request } from 'express';

@Controller('cats')
export class CatsController {
  @Get()
  findAll(@Req() request: Request): string {
    return 'This action returns all cats';
  }
}
@@switch
import { Controller, Bind, Get, Req } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Get()
  @Bind(Req())
  findAll(request) {
    return 'This action returns all cats';
  }
}
```

> info **Gợi ý** Để tận dụng typing của `express` (như tham số `request: Request` ở trên), hãy cài package `@types/express`.

Request object đại diện cho HTTP request và có các thuộc tính cho query string, route parameter, HTTP header và body (xem [tài liệu Express](https://expressjs.com/en/api.html#req)). Trong hầu hết trường hợp, bạn không cần truy cập thủ công các thuộc tính này. Thay vào đó, hãy dùng các decorator chuyên dụng có sẵn như `@Body()` hoặc `@Query()`. Bảng sau liệt kê các decorator được cung cấp và object tương ứng của nền tảng mà chúng đại diện.

<table>
  <tbody>
    <tr>
      <td><code>@Request(), @Req()</code></td>
      <td><code>req</code></td></tr>
    <tr>
      <td><code>@Response(), @Res()</code><span class="table-code-asterisk">*</span></td>
      <td><code>res</code></td>
    </tr>
    <tr>
      <td><code>@Next()</code></td>
      <td><code>next</code></td>
    </tr>
    <tr>
      <td><code>@Session()</code></td>
      <td><code>req.session</code></td>
    </tr>
    <tr>
      <td><code>@Param(key?: string)</code></td>
      <td><code>req.params</code> / <code>req.params[key]</code></td>
    </tr>
    <tr>
      <td><code>@Body(key?: string)</code></td>
      <td><code>req.body</code> / <code>req.body[key]</code></td>
    </tr>
    <tr>
      <td><code>@Query(key?: string)</code></td>
      <td><code>req.query</code> / <code>req.query[key]</code></td>
    </tr>
    <tr>
      <td><code>@Headers(name?: string)</code></td>
      <td><code>req.headers</code> / <code>req.headers[name]</code></td>
    </tr>
    <tr>
      <td><code>@Cookies(name?: string)</code></td>
      <td>các cookie của request / cookie có tên <code>name</code> (xem <a routerLink="/techniques/cookies">Cookies</a>)</td>
    </tr>
    <tr>
      <td><code>@SignedCookies(name?: string)</code></td>
      <td>các signed cookie đã được xác minh / signed cookie có tên <code>name</code></td>
    </tr>
    <tr>
      <td><code>@Ip()</code></td>
      <td><code>req.ip</code></td>
    </tr>
    <tr>
      <td><code>@HostParam()</code></td>
      <td><code>req.hosts</code></td>
    </tr>
  </tbody>
</table>

<sup>\* </sup>Để tương thích với typing của các nền tảng HTTP bên dưới (ví dụ Express và Fastify), Nest cung cấp decorator `@Res()` và `@Response()`. `@Res()` là alias của `@Response()`. Cả hai đều trả về trực tiếp `response` object gốc của nền tảng bên dưới. Khi dùng chúng, hãy cài thêm typing cho library bên dưới (ví dụ `@types/express`) để tận dụng tối đa. Khi bạn inject `@Res()` hoặc `@Response()` vào một route handler, bạn đã chuyển Nest sang **chế độ riêng của library** cho handler đó, và bạn phải tự quản lý response. Khi đó bạn bắt buộc phải gửi response bằng cách gọi một method trên `response` object (ví dụ `res.json(...)` hoặc `res.send(...)`); nếu không, request sẽ bị treo.

`@Body()`, `@Query()`, `@Param()` và `@RawBody()` cũng nhận một options object với các thuộc tính `schema` và `pipes`. Nhờ đó bạn có thể gắn trực tiếp các schema tương thích [Standard Schema](https://standardschema.dev/), như schema tạo bằng Zod, Valibot hoặc ArkType, vào route parameter.

```typescript
@Post()
create(@Body({ schema: createCatSchema }) createCatDto: CreateCatDto) {
  return this.catsService.create(createCatDto);
}

@Get(':id')
findOne(@Param('id', { schema: z.coerce.number().int().positive() }) id: number) {
  return this.catsService.findOne(id);
}
```

Bản thân các decorator này chỉ gắn schema vào dưới dạng metadata. Để validate theo schema, hãy đăng ký `StandardSchemaValidationPipe` có sẵn hoặc một custom pipe đọc `metadata.schema`.

> info **Gợi ý** Để biết cách tạo decorator của riêng bạn, xem chương [Custom route decorator](/custom-decorators).

#### Resource <a id="resources"></a>

Ở trên, ta đã định nghĩa một endpoint để lấy resource cats (route **GET**). Thông thường, ta cũng cần một endpoint để tạo bản ghi mới. Hãy thêm một handler **POST**:

```typescript
@@filename(cats.controller)
import { Controller, Get, Post } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Post()
  create(): string {
    return 'This action adds a new cat';
  }

  @Get()
  findAll(): string {
    return 'This action returns all cats';
  }
}
@@switch
import { Controller, Get, Post } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Post()
  create() {
    return 'This action adds a new cat';
  }

  @Get()
  findAll() {
    return 'This action returns all cats';
  }
}
```

Nest cung cấp decorator cho mọi HTTP method chuẩn: `@Get()`, `@Post()`, `@Put()`, `@Delete()`, `@Patch()`, `@Options()`, `@Head()` và `@QueryMethod()`. Decorator cuối map tới method `QUERY`; nó được đặt tên là `QueryMethod` để tránh trùng với decorator tham số `@Query()`. Ngoài ra, `@All()` định nghĩa một endpoint xử lý tất cả các method này.

#### Route wildcard <a id="route-wildcards"></a>

Nest cũng hỗ trợ route theo pattern. Ví dụ, dấu sao (`*`) ở cuối path đóng vai trò wildcard, khớp với mọi tổ hợp ký tự. Trong ví dụ sau, method `findAll()` sẽ được thực thi cho mọi route bắt đầu bằng `abcd/`, bất kể phía sau có bao nhiêu ký tự.

```typescript
@Get('abcd/*')
findAll() {
  return 'This route uses a wildcard';
}
```

Route path `'abcd/*'` khớp với `abcd/`, `abcd/123`, `abcd/abc`, v.v. Trong path dạng chuỗi, dấu gạch ngang (`-`) và dấu chấm (`.`) được hiểu theo nghĩa đen.

Cách này chạy được với cả Express và Fastify. Tuy nhiên, Express v5 đã làm routing chặt chẽ hơn: trong Express thuần, wildcard phải được đặt tên thì route mới hoạt động (ví dụ `abcd/{{ '{' }}*splat&#125;`, trong đó `splat` là tên tùy ý cho tham số wildcard, không có ý nghĩa đặc biệt gì). Vì Nest có một lớp tương thích cho Express, bạn vẫn có thể dùng dấu sao không đặt tên (`*`) làm wildcard.

Với dấu sao nằm ở **giữa route**, Express yêu cầu wildcard có tên (ví dụ `ab{{ '{' }}*splat&#125;cd`), còn Fastify thì hoàn toàn không hỗ trợ.

#### Xung đột route và thứ tự phân giải <a id="route-conflicts-and-resolution-order"></a>

Nest đăng ký route theo thứ tự khai báo. Trên các adapter phụ thuộc thứ tự, như Express adapter mặc định, một route có tham số có thể âm thầm che mất một route cụ thể hơn:

```typescript
@Controller('users')
export class UsersController {
  @Get(':id')
  findOne() {}

  @Get('me') // never reached: `:id` matches "me" first
  findMe() {}
}
```

Lỗi này rất dễ bị bỏ sót: ứng dụng khởi động mà không có cảnh báo nào, và vấn đề chỉ lộ ra lúc runtime, khi một request bị đưa tới nhầm handler. Các pipe như `ParseIntPipe` không giúp được gì ở đây, vì routing chọn handler *trước* khi bất kỳ pipe nào chạy.

NestJS v12 bổ sung hai thuộc tính `NestApplicationOptions` (phải tự bật) để phòng tránh chuyện này. Cả hai đều mặc định giữ hành vi cũ, nên các ứng dụng hiện có không bị ảnh hưởng trừ khi bạn đặt chúng.

**`routeConflictPolicy`** bật chẩn đoán ngay lúc bootstrap. Với mỗi loại xung đột, nó nhận một mức độ nghiêm trọng là `'off'` (mặc định), `'warn'` hoặc `'error'`:

```typescript
const app = await NestFactory.create(AppModule, {
  routeConflictPolicy: { duplicate: 'error', shadow: 'warn' },
});
```

<table>
  <tr>
    <td><code>duplicate</code></td>
    <td>Hai route có cùng method, path, host và version.</td>
  </tr>
  <tr>
    <td><code>shadow</code></td>
    <td>Hai route pattern có thể cùng khớp một request (ví dụ <code>/users/me</code> và <code>/users/:id</code>).</td>
  </tr>
</table>

Với `'error'`, tất cả các cặp vi phạm được gom vào một `RouteConflictException` duy nhất, throw ra khi ứng dụng khởi tạo (trong `app.init()`, hoặc trong `app.listen()` nếu bạn không gọi `init()` tường minh). Nhờ vậy, bạn thấy mọi xung đột cùng lúc thay vì mỗi lần restart chỉ thấy một.

**`routeResolutionStrategy`** điều khiển thứ tự đăng ký. Đặt nó thành `'specificity'` sẽ đăng ký các route cụ thể nhất trước (segment cố định được ưu tiên hơn segment có tham số, segment có tham số được ưu tiên hơn wildcard), nên ví dụ ở trên sẽ chạy đúng bất kể thứ tự khai báo:

```typescript
const app = await NestFactory.create(AppModule, {
  routeResolutionStrategy: 'specificity',
});
```

Mặc định là `'declaration'`, giữ nguyên hành vi cũ.

> info **Gợi ý** Ngoài policy `duplicate`, các tùy chọn này chỉ có tác dụng trên những adapter mà thứ tự đăng ký ảnh hưởng tới việc khớp route. `ExpressAdapter` phụ thuộc thứ tự; `FastifyAdapter` thì không, vì router của nó (`find-my-way`) vốn đã xếp hạng route theo độ cụ thể. Trên Fastify, policy `shadow` không làm gì cả và việc sắp xếp `'specificity'` không có tác dụng, còn policy `duplicate` thì được áp dụng trên cả hai adapter. Các type `RouteConflictPolicy`, `RouteConflictPolicyLevel` và `RouteResolutionStrategy` được export từ `@nestjs/common`.

#### Status code

Như đã nói, **status code** mặc định của response là **200**, trừ request POST mặc định là **201**. Bạn có thể thay đổi hành vi này bằng decorator `@HttpCode(...)` ở cấp handler.

```typescript
@Post()
@HttpCode(204)
create() {
  return 'This action adds a new cat';
}
```

> info **Gợi ý** Import `HttpCode` từ package `@nestjs/common`.

Thường thì status code không cố định mà phụ thuộc vào nhiều yếu tố. Khi đó, hãy dùng **response** object riêng của library (inject bằng `@Res()`), hoặc nếu có lỗi thì throw một exception.

#### Response header <a id="response-headers"></a>

Để set một response header tùy chỉnh, dùng decorator `@Header()` hoặc response object riêng của library (và gọi trực tiếp `res.header()`).

```typescript
@Post()
@Header('Cache-Control', 'no-store')
create() {
  return 'This action adds a new cat';
}
```

> info **Gợi ý** Import `Header` từ package `@nestjs/common`.

#### Redirect <a id="redirection"></a>

Để redirect response tới một URL cụ thể, dùng decorator `@Redirect()` hoặc response object riêng của library (và gọi trực tiếp `res.redirect()`).

`@Redirect()` nhận hai tham số tùy chọn là `url` và `statusCode`. Nếu bỏ qua, `statusCode` mặc định là `302` (`Found`).

```typescript
@Get()
@Redirect('https://nestjs.com', 301)
```

> info **Gợi ý** Để xác định HTTP status code hoặc URL redirect một cách động, hãy trả về một object theo interface `HttpRedirectResponse` (export từ `@nestjs/common`).

Giá trị trả về sẽ ghi đè mọi tham số truyền vào decorator `@Redirect()`. Ví dụ:

```typescript
@@filename()
@Get('docs')
@Redirect('https://docs.nestjs.com', 302)
getDocs(@Query('version') version) {
  if (version && version === '5') {
    return { url: 'https://docs.nestjs.com/v5/' };
  }
}
@@switch
@Get('docs')
@Redirect('https://docs.nestjs.com', 302)
@Bind(Query('version'))
getDocs(version) {
  if (version && version === '5') {
    return { url: 'https://docs.nestjs.com/v5/' };
  }
}
```

#### Route parameter <a id="route-parameters"></a>

Route với path cố định sẽ không dùng được khi bạn cần nhận **dữ liệu động** trong request (ví dụ `GET /cats/1` để lấy cat có id `1`). Để định nghĩa route có tham số, hãy thêm các **token** route parameter vào route path để bắt giá trị động từ URL, như decorator `@Get()` trong ví dụ bên dưới. Sau đó bạn có thể truy cập các route parameter này bằng decorator `@Param()`, thêm vào signature của method.

> info **Gợi ý** Hãy khai báo các route có tham số sau các path cố định, để path có tham số không chặn mất traffic dành cho path cố định. Xem [Xung đột route và thứ tự phân giải](/controllers#route-conflicts-and-resolution-order) để biết các tùy chọn giúp phát hiện vấn đề này lúc bootstrap hoặc tự xử lý giúp bạn.

```typescript
@@filename()
@Get(':id')
findOne(@Param() params: any): string {
  console.log(params.id);
  return `This action returns a #${params.id} cat`;
}
@@switch
@Get(':id')
@Bind(Param())
findOne(params) {
  console.log(params.id);
  return `This action returns a #${params.id} cat`;
}
```

Decorator `@Param()` dùng để decorate một tham số của method (`params` trong ví dụ trên), giúp các **route** parameter trở thành thuộc tính của tham số đó bên trong method. Như trong code, bạn truy cập tham số `id` qua `params.id`. Cách khác là truyền một token tham số cụ thể vào decorator, rồi dùng thẳng route parameter theo tên trong thân method.

> info **Gợi ý** Import `Param` từ package `@nestjs/common`.

```typescript
@@filename()
@Get(':id')
findOne(@Param('id') id: string): string {
  return `This action returns a #${id} cat`;
}
@@switch
@Get(':id')
@Bind(Param('id'))
findOne(id) {
  return `This action returns a #${id} cat`;
}
```

#### Routing theo sub-domain <a id="sub-domain-routing"></a>

Decorator `@Controller()` có thể nhận tùy chọn `host` để yêu cầu HTTP host của request gửi đến phải khớp với một giá trị cụ thể.

```typescript
@@filename(admin.controller)
@Controller({ host: 'admin.example.com' })
export class AdminController {
  @Get()
  index(): string {
    return 'Admin page';
  }
}
@@switch
@Controller({ host: 'admin.example.com' })
export class AdminController {
  @Get()
  index() {
    return 'Admin page';
  }
}
```

> warning **Cảnh báo** Vì **Fastify** không hỗ trợ nested router, hãy dùng Express adapter mặc định hoặc Node adapter nếu bạn cần routing theo sub-domain.

Giống như `path` của route, tùy chọn `host` có thể dùng token để bắt giá trị động ở vị trí đó trong host name, như token host parameter trong decorator `@Controller()` bên dưới. Bạn có thể truy cập các host parameter khai báo theo cách này bằng decorator `@HostParam()`, thêm vào signature của method.

```typescript
@@filename(account.controller)
@Controller({ host: ':account.example.com' })
export class AccountController {
  @Get()
  getInfo(@HostParam('account') account: string) {
    return account;
  }
}
@@switch
@Controller({ host: ':account.example.com' })
export class AccountController {
  @Get()
  @Bind(HostParam('account'))
  getInfo(account) {
    return account;
  }
}
```

#### Chia sẻ state <a id="state-sharing"></a>

Developer đến từ các ngôn ngữ lập trình khác có thể bất ngờ khi biết rằng trong Nest, gần như mọi thứ đều được chia sẻ giữa các request. Điều này bao gồm những resource như connection pool của database, các singleton service có state toàn cục, v.v. Node.js không theo mô hình request/response đa luồng stateless, trong đó mỗi request được xử lý bởi một thread riêng. Vì vậy, dùng singleton instance trong Nest là hoàn toàn **an toàn**.

Dù vậy, một số trường hợp đặc biệt có thể cần controller có vòng đời theo request, chẳng hạn cache theo từng request trong ứng dụng GraphQL, theo dõi request, hay multi-tenancy. Để biết cách điều khiển việc này, xem [Injection scope](/fundamentals/injection-scopes).

#### Bất đồng bộ <a id="asynchronicity"></a>

JavaScript hiện đại dựa rất nhiều vào xử lý dữ liệu **bất đồng bộ**, và Nest hỗ trợ đầy đủ hàm `async`. Một hàm `async` luôn trả về `Promise`, nên route handler có thể trả về một giá trị trì hoãn và Nest sẽ tự động resolve nó:

```typescript
@@filename(cats.controller)
@Get()
async findAll(): Promise<any[]> {
  return [];
}
@@switch
@Get()
async findAll() {
  return [];
}
```

Route handler cũng có thể trả về [observable stream](https://rxjs.dev/guide/observable) của RxJS. Nest sẽ tự subscribe stream bên trong và resolve giá trị được emit cuối cùng khi stream hoàn tất.

```typescript
@@filename(cats.controller)
@Get()
findAll(): Observable<any[]> {
  return of([]);
}
@@switch
@Get()
findAll() {
  return of([]);
}
```

Cả hai cách đều hợp lệ; hãy chọn cách phù hợp nhất với nhu cầu của bạn.

#### Request payload <a id="request-payloads"></a>

Route handler POST trong ví dụ trước chưa nhận tham số nào từ client. Hãy sửa lại bằng cách thêm decorator `@Body()`.

Trước khi tiếp tục (nếu bạn dùng TypeScript), ta cần định nghĩa schema **DTO** (Data Transfer Object). DTO là một object định nghĩa cấu trúc dữ liệu được gửi qua mạng. Bạn có thể định nghĩa schema DTO bằng interface **TypeScript** hoặc class thông thường, nhưng **class** là lựa chọn được khuyên dùng. Class là một phần của chuẩn JavaScript ES6, nên chúng vẫn tồn tại như các thực thể thật trong code JavaScript sau khi compile. Ngược lại, interface TypeScript bị xóa trong quá trình transpile, nên Nest không thể tham chiếu tới chúng lúc runtime. Điều này quan trọng vì các tính năng như **pipe** cần truy cập metatype của biến lúc runtime, và chỉ class mới làm được điều đó.

Tạo class `CreateCatDto`:

```typescript
@@filename(create-cat.dto)
export class CreateCatDto {
  name: string;
  age: number;
  breed: string;
}
```

Class này có ba thuộc tính cơ bản. Giờ ta có thể dùng DTO mới trong `CatsController`:

```typescript
@@filename(cats.controller)
@Post()
async create(@Body() createCatDto: CreateCatDto) {
  return 'This action adds a new cat';
}
@@switch
@Post()
@Bind(Body())
async create(createCatDto) {
  return 'This action adds a new cat';
}
```

> info **Gợi ý** `ValidationPipe` có thể lọc bỏ những thuộc tính mà route handler không nên nhận. Bạn khai báo whitelist các thuộc tính được chấp nhận, và mọi thuộc tính không nằm trong whitelist sẽ tự động bị loại khỏi object kết quả. Trong ví dụ `CreateCatDto`, whitelist gồm các thuộc tính `name`, `age` và `breed`. Tìm hiểu thêm tại [Loại bỏ thuộc tính](https://docs.nestjs.com/application/validation#stripping-properties).

#### Query parameter <a id="query-parameters"></a>

Để lấy query parameter từ request gửi đến, dùng decorator `@Query()`.

Giả sử có một route lọc danh sách cat theo các query parameter như `age` và `breed`. Đầu tiên, khai báo các query parameter trong `CatsController`:

```typescript
@@filename(cats.controller)
@Get()
async findAll(@Query('age') age: number, @Query('breed') breed: string) {
  return `This action returns all cats filtered by age: ${age} and breed: ${breed}`;
}
@@switch
@Get()
@Bind(Query('age'), Query('breed'))
async findAll(age, breed) {
  return `This action returns all cats filtered by age: ${age} and breed: ${breed}`;
}
```

Trong ví dụ này, decorator `@Query()` lấy giá trị của `age` và `breed` từ query string. Ví dụ, một request tới:

```plaintext
GET /cats?age=2&breed=Persian
```

sẽ cho `age` là `'2'` và `breed` là `'Persian'`. Giá trị query parameter luôn đến dưới dạng chuỗi, và chỉ khai báo type `number` không tự chuyển đổi được. Để nhận về số, hãy áp dụng một pipe như `ParseIntPipe` (xem [Pipes](/pipes)).

Nếu ứng dụng cần xử lý query parameter phức tạp hơn, như object lồng nhau hoặc mảng:

```plaintext
?filter[where][name]=John&filter[where][age]=30
?item[]=1&item[]=2
```

hãy cấu hình HTTP adapter (Express, Fastify hoặc Node) để dùng query parser phù hợp. Với Express, dùng parser `extended`, parser này hỗ trợ query object phức tạp:

```typescript
@@filename(main)
const app = await NestFactory.create<NestExpressApplication>(AppModule);
app.set('query parser', 'extended');
@@switch
const app = await NestFactory.create(AppModule);
app.set('query parser', 'extended');
```

Với Fastify, dùng tùy chọn router `querystringParser`:

```typescript
@@filename(main)
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter({
    routerOptions: {
      querystringParser: (str) => qs.parse(str),
    },
  }),
);
@@switch
const app = await NestFactory.create(
  AppModule,
  new FastifyAdapter({
    routerOptions: {
      querystringParser: (str) => qs.parse(str),
    },
  }),
);
```

Node adapter nhận trực tiếp tùy chọn `querystringParser`:

```typescript
@@filename(main)
const app = await NestFactory.create<NestNodeApplication>(
  AppModule,
  new NodeAdapter({
    querystringParser: (str) => qs.parse(str),
  }),
);
@@switch
const app = await NestFactory.create(
  AppModule,
  new NodeAdapter({
    querystringParser: (str) => qs.parse(str),
  }),
);
```

> info **Gợi ý** `qs` là một query string parser hỗ trợ lồng nhau và mảng. Cài bằng `npm install qs`.

#### Xử lý lỗi <a id="handling-errors"></a>

Việc xử lý lỗi (tức là làm việc với exception) được trình bày trong chương [Exception filters](/exception-filters).

#### Theo dõi route trên production <a id="observing-routes-in-production"></a>

Một controller chạy hoàn hảo trên máy bạn có thể hoạt động rất khác khi gặp traffic thật. Trên production, câu hỏi không bao giờ là "route này có chạy không?" mà là "tại sao `GET /cats/:id` tăng từ 40 ms lên 900 ms sau đợt deploy hôm thứ Ba, và bị với mọi request hay chỉ một tenant xui xẻo?"

Route handler là đơn vị tự nhiên để trả lời câu hỏi đó, và [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') báo cáo đúng theo đơn vị này. Vì SDK `@nestjs/observe` hook vào chính vòng đời request của Nest thay vì bọc HTTP server, mọi số đo đều được gắn nhãn theo route pattern bạn đã khai báo (`GET /cats/:id`, chứ không phải 10.000 URL khác nhau). Nhờ đó, mỗi route là một dòng duy nhất mà bạn có thể sắp xếp, vẽ biểu đồ và đặt cảnh báo:

```typescript
const app = await NestFactory.create(AppModule, {
  instrument: ObserveInstrument,
});
```

Cộng thêm việc import `ObserveModule.forRoot()` vào root module, thế là xong toàn bộ phần tích hợp. Từ đó, tìm ra một route chậm chỉ mất ba cú click: sắp xếp danh sách route theo p95; mở operation để xem độ chậm là ổn định hay lúc có lúc không, và có bắt đầu từ một bản release nào không; rồi mở một lần thực thi chậm và đọc waterfall của nó để xem controller, method của service hay query nào đã chiếm thời gian. Thời gian được tính theo từng **class và method**, đã trừ đi thời gian chờ await, nên `CatsService.findOne()` tốn 800 ms trong chính code của nó sẽ được phân biệt ngay với `CatsService.findOne()` chờ database 800 ms.

Xem chương [Observability](/observability/overview) để bắt đầu thiết lập, và [Dashboard](/observability/dashboard) để xem toàn bộ quy trình từ một cảnh báo đi xuống tới một request cụ thể.

#### Ví dụ resource đầy đủ <a id="full-resource-sample"></a>

Ví dụ sau dùng một số decorator có sẵn để tạo một controller cơ bản. Controller này cung cấp vài method để truy cập và thao tác với dữ liệu nội bộ.

```typescript
@@filename(cats.controller)
import { Controller, Get, Query, Post, Body, Put, Param, Delete } from '@nestjs/common';
import { CreateCatDto, UpdateCatDto, ListAllEntities } from './dto.js';

@Controller('cats')
export class CatsController {
  @Post()
  create(@Body() createCatDto: CreateCatDto) {
    return 'This action adds a new cat';
  }

  @Get()
  findAll(@Query() query: ListAllEntities) {
    return `This action returns all cats (limit: ${query.limit} items)`;
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return `This action returns a #${id} cat`;
  }

  @Put(':id')
  update(@Param('id') id: string, @Body() updateCatDto: UpdateCatDto) {
    return `This action updates a #${id} cat`;
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return `This action removes a #${id} cat`;
  }
}
@@switch
import { Controller, Get, Query, Post, Body, Put, Param, Delete, Bind } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Post()
  @Bind(Body())
  create(createCatDto) {
    return 'This action adds a new cat';
  }

  @Get()
  @Bind(Query())
  findAll(query) {
    return `This action returns all cats (limit: ${query.limit} items)`;
  }

  @Get(':id')
  @Bind(Param('id'))
  findOne(id) {
    return `This action returns a #${id} cat`;
  }

  @Put(':id')
  @Bind(Param('id'), Body())
  update(id, updateCatDto) {
    return `This action updates a #${id} cat`;
  }

  @Delete(':id')
  @Bind(Param('id'))
  remove(id) {
    return `This action removes a #${id} cat`;
  }
}
```

> info **Gợi ý** Nest CLI có một generator (schematic) tự động tạo ra **toàn bộ code boilerplate**, để bạn không phải viết tay. Tìm hiểu thêm trong recipe [CRUD generator](/recipes/crud-generator).
#### Cho controller chạy <a id="getting-up-and-running"></a>

Dù `CatsController` đã được định nghĩa đầy đủ, Nest vẫn chưa biết đến nó và sẽ không tạo instance của class này.

Controller luôn phải thuộc về một module, vì vậy ta khai báo mảng `controllers` trong decorator `@Module()`. Vì hiện chưa định nghĩa module nào khác ngoài root module `AppModule`, ta sẽ dùng nó để đăng ký `CatsController`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { CatsController } from './cats/cats.controller.js';

@Module({
  controllers: [CatsController],
})
export class AppModule {}
```

Khi metadata này đã được gắn vào class module thông qua decorator `@Module()`, Nest sẽ biết cần mount những controller nào.

#### Cách dùng riêng của library <a id="library-specific-approach"></a>

Đến giờ, ta đã tìm hiểu cách chuẩn của Nest để thao tác với response. Cách còn lại là dùng [response object](https://expressjs.com/en/api.html#res) riêng của library, được inject bằng decorator `@Res()`. Để thấy rõ sự khác biệt, hãy viết lại `CatsController` như sau:

```typescript
@@filename()
import { Controller, Get, Post, Res, HttpStatus } from '@nestjs/common';
import type { Response } from 'express';

@Controller('cats')
export class CatsController {
  @Post()
  create(@Res() res: Response) {
    res.status(HttpStatus.CREATED).send();
  }

  @Get()
  findAll(@Res() res: Response) {
    res.status(HttpStatus.OK).json([]);
  }
}
@@switch
import { Controller, Get, Post, Bind, Res, HttpStatus } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Post()
  @Bind(Res())
  create(res) {
    res.status(HttpStatus.CREATED).send();
  }

  @Get()
  @Bind(Res())
  findAll(res) {
    res.status(HttpStatus.OK).json([]);
  }
}
```

Cách này linh hoạt hơn vì cho bạn toàn quyền điều khiển response object (ví dụ: thao tác header và dùng các tính năng riêng của library), nhưng nên dùng một cách thận trọng. Nhìn chung, code sẽ kém rõ ràng hơn và có một số nhược điểm. Nhược điểm chính là code của bạn bị phụ thuộc vào nền tảng, vì mỗi library bên dưới có thể cung cấp API khác nhau trên response object. Nó cũng khiến việc test khó hơn, chẳng hạn bạn phải mock response object.

Ngoài ra, cách này làm mất tương thích với các tính năng của Nest dựa trên cơ chế xử lý response chuẩn, như interceptor và các decorator `@HttpCode()` / `@Header()`. Để khắc phục, hãy bật tùy chọn `passthrough`:

```typescript
@@filename()
@Get()
findAll(@Res({ passthrough: true }) res: Response) {
  res.status(HttpStatus.OK);
  return [];
}
@@switch
@Get()
@Bind(Res({ passthrough: true }))
findAll(res) {
  res.status(HttpStatus.OK);
  return [];
}
```

Bằng cách này, bạn vẫn tương tác được với response object gốc (ví dụ, set cookie hoặc header theo điều kiện cụ thể) trong khi để framework lo phần còn lại.
