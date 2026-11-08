### Exception filters

Nest có sẵn một **lớp xử lý exception** (exceptions layer) đảm nhận mọi exception chưa được xử lý trong toàn ứng dụng. Khi code của bạn không xử lý một exception nào đó, lớp này sẽ bắt nó và tự động gửi về một response phù hợp, thân thiện với người dùng.

<figure>
  <img class="illustrative-image" src="/assets/Filter_1.png" />
</figure>

Mặc định, việc này do một **global exception filter** có sẵn đảm nhận, filter này xử lý các exception thuộc type `HttpException` (và các class con của nó). Khi một exception **không được nhận diện** (không phải `HttpException` cũng không phải class kế thừa từ `HttpException`), exception filter có sẵn sẽ tạo ra JSON response mặc định như sau:

```json
{
  "statusCode": 500,
  "message": "Internal server error"
}
```

> info **Gợi ý** Global exception filter hỗ trợ một phần library `http-errors`. Một error được throw ra nếu mang các thuộc tính `statusCode` và `message` theo đúng dạng mà library đó tạo ra sẽ được gửi về với chính các giá trị này, thay vì response `InternalServerErrorException` mặc định dành cho exception không được nhận diện. Kể từ NestJS v12.2, nếu thuộc tính `expose` của error là `false`, response sẽ mang reason phrase chuẩn của status code đó (ví dụ `Bad Gateway`) thay vì message của error. `http-errors` đặt `expose` thành `false` với các status code từ 500 trở lên, nên hãy truyền `expose: true` vào `createError()` khi message của lỗi 5xx là để cho client đọc.

#### Throw exception chuẩn <a id="throwing-standard-exceptions"></a>

Nest cung cấp sẵn class `HttpException`, export từ package `@nestjs/common`. Với các API REST và GraphQL dựa trên HTTP thông thường, cách làm tốt nhất là gửi về các HTTP response object chuẩn khi xảy ra những điều kiện lỗi nhất định.

Ví dụ, `CatsController` có method `findAll()` (một route handler `GET`). Giả sử route handler này throw một exception. Để minh họa, ta sẽ hard-code như sau:

```typescript
@@filename(cats.controller)
@Get()
async findAll() {
  throw new HttpException('Forbidden', HttpStatus.FORBIDDEN);
}
```

> info **Gợi ý** `HttpStatus` là một enum helper import từ package `@nestjs/common`.

Khi client gọi endpoint này, response trông như sau:

```json
{
  "statusCode": 403,
  "message": "Forbidden"
}
```

Constructor của `HttpException` nhận hai tham số bắt buộc quyết định response:

- Tham số `response` định nghĩa body của JSON response. Nó có thể là một `string` hoặc một `object`, như mô tả bên dưới.
- Tham số `status` định nghĩa [HTTP status code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status).

Mặc định, body của JSON response có hai thuộc tính:

- `statusCode`: mặc định là HTTP status code truyền vào tham số `status`
- `message`: mô tả ngắn về lỗi HTTP dựa trên `status`

Để chỉ ghi đè phần message trong body của JSON response, hãy truyền một chuỗi vào tham số `response`. Để ghi đè toàn bộ body của JSON response, truyền một object vào tham số `response`. Nest sẽ serialize object đó và trả về làm body của JSON response.

> info **Gợi ý** Một instance `Error` truyền vào tham số `response` sẽ không được serialize vào body của response. Thay vào đó, Nest gửi body mặc định `{{ '{' }} statusCode, message {{ '}' }}` ứng với status, để các thuộc tính của error không bị lộ ra cho client. Để giữ lại error gốc phục vụ việc log, hãy truyền nó vào `cause`.

Tham số thứ hai của constructor, `status`, phải là một HTTP status code hợp lệ. Cách làm tốt nhất là dùng enum `HttpStatus` import từ `@nestjs/common`.

Tham số **thứ ba** (tùy chọn) của constructor, `options`, có thể dùng để cung cấp [cause](https://nodejs.org/en/blog/release/v16.9.0/#error-cause) của lỗi. Object `cause` không được serialize vào response object, nhưng nó hữu ích cho việc log, vì nó cung cấp thông tin về lỗi bên trong đã khiến `HttpException` bị throw.

Đây là ví dụ ghi đè toàn bộ body của response và cung cấp cause của lỗi:

```typescript
@@filename(cats.controller)
@Get()
async findAll() {
  try {
    await this.service.findAll();
  } catch (error) {
    throw new HttpException({
      status: HttpStatus.FORBIDDEN,
      error: 'This is a custom message',
    }, HttpStatus.FORBIDDEN, {
      cause: error
    });
  }
}
```

Khi đó response trông như sau:

```json
{
  "status": 403,
  "error": "This is a custom message"
}
```

#### Log exception <a id="exceptions-logging"></a>

Mặc định, exception filter không log các exception có sẵn như `HttpException` (và mọi exception kế thừa từ nó). Các exception này được xem là một phần của luồng hoạt động bình thường của ứng dụng, nên chúng không xuất hiện trên console. Điều tương tự áp dụng cho `WsException` và `RpcException` trong context tương ứng của chúng.

`HttpException` kế thừa từ class `IntrinsicException`, được export từ package `@nestjs/common`. Các exception filter có sẵn không bao giờ log các instance của `IntrinsicException`, đây là cách chúng phân biệt exception thuộc về hoạt động bình thường với exception không phải.

Để log các exception này, hãy tạo một custom exception filter, như mô tả trong phần [Exception filter](#exception-filters) bên dưới.

#### Theo dõi lỗi trên production <a id="tracking-errors-in-production"></a>

Exception filter quyết định *client* sẽ thấy gì. Tự nó không cho bạn biết rằng một `TypeError` bắt đầu xuất hiện trong `OrdersService` từ mười hai phút trước, ở 4% lượt checkout, và chỉ với những khách hàng có sản phẩm giảm giá trong giỏ. Nó cũng không cho bạn biết dòng code nào đã throw.

Cách làm thường thấy là log stack trace rồi tìm lại sau, nhưng cách này chưa đủ: stack trace trong file log trỏ tới code đã compile (`/var/app/current/dist/orders/orders.service.js:35`), không kèm ngữ cảnh mã nguồn, và không cho biết đây là lần xuất hiện đầu tiên hay lần thứ mười nghìn.

[NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') xem một lỗi chưa được xử lý là một đối tượng quan trọng thực thụ, chứ không phải một dòng log. Mọi lỗi đi tới lớp xử lý exception đều được ghi lại cùng với request đã gây ra nó, và:

- **Stack trace đi kèm mã nguồn.** Frame được map ngược qua source map về `src/orders/orders.service.ts:35`, và các dòng xung quanh được hiển thị ngay tại chỗ, nên bạn đọc được đoạn code lỗi ngay trong thẻ lỗi mà không cần clone gì cả.
- **Các lần xuất hiện được gom thành defect.** Những lỗi cùng class và cùng hình dạng stack được gộp lại thành một nhóm có fingerprint, kèm số lần xảy ra, thời điểm thấy lần đầu và lần cuối, cùng bản release đã gây ra nó. "Mới xuất hiện từ v2.4.1" là thông tin bạn đọc thẳng trên trang chứ không phải tự suy luận.
- **Lỗi giữ nguyên ngữ cảnh của nó.** Trace chứa lỗi, người dùng gặp lỗi, các log được ghi trong request đó, và các span đã chạy trước khi throw đều được đính kèm, nên bạn thấy được request đang làm gì khi nó lỗi.

<figure><img src="https://www.observe.nestjs.com/docs/telemetry/error-with-source.webp" alt="Thẻ lỗi kèm ngữ cảnh mã nguồn" /></figure>

Vì lỗi đã mang sẵn code của chính nó, bạn có thể giao nó cho một coding agent chỉ với một cú click: **Copy agent prompt** đóng gói lỗi, stack trace đã rút gọn kèm các dòng mã nguồn, các span chậm và các log xung quanh thành một prompt hoàn chỉnh cho Claude Code, Cursor hoặc bất kỳ tool nào đang mở repository của bạn.

Phần này bổ sung chứ không thay thế cho các filter được mô tả trong chương này: filter định hình response, còn instrumentation ghi lại những gì đã xảy ra trên đường đi. Xem [Theo dõi lỗi](/observability/error-monitoring) để biết mọi thứ SDK ghi lại về một lỗi, chương [Observability](/observability/overview) để thiết lập, và [Dashboard](/observability/dashboard#issues) để biến một lỗi lặp lại thành một issue được theo dõi và tự xác minh bản fix.

#### Custom exception <a id="custom-exceptions"></a>

Trong hầu hết trường hợp, bạn không cần viết custom exception mà có thể dùng các HTTP exception có sẵn của Nest được mô tả ở phần tiếp theo. Nếu thực sự cần custom exception, bạn nên tạo **cây phân cấp exception** của riêng mình, trong đó các custom exception kế thừa từ class gốc `HttpException`. Khi đó Nest sẽ nhận diện được exception của bạn và tự động lo phần response lỗi. Hãy implement một custom exception như vậy:

```typescript
@@filename(forbidden.exception)
export class ForbiddenException extends HttpException {
  constructor() {
    super('Forbidden', HttpStatus.FORBIDDEN);
  }
}
```

Vì `ForbiddenException` kế thừa từ `HttpException` gốc, nó hoạt động được với exception handler có sẵn, nên ta có thể dùng nó trong method `findAll()`.

```typescript
@@filename(cats.controller)
@Get()
async findAll() {
  throw new ForbiddenException();
}
```

#### HTTP exception có sẵn <a id="built-in-http-exceptions"></a>

Nest cung cấp một bộ exception chuẩn kế thừa từ `HttpException` gốc. Chúng được export từ package `@nestjs/common` và đại diện cho nhiều HTTP exception phổ biến nhất:

- `BadRequestException`
- `UnauthorizedException`
- `NotFoundException`
- `ForbiddenException`
- `NotAcceptableException`
- `RequestTimeoutException`
- `ConflictException`
- `GoneException`
- `HttpVersionNotSupportedException`
- `PayloadTooLargeException`
- `UnsupportedMediaTypeException`
- `UnprocessableEntityException`
- `InternalServerErrorException`
- `NotImplementedException`
- `ImATeapotException`
- `MethodNotAllowedException`
- `MisdirectedException`
- `BadGatewayException`
- `ServiceUnavailableException`
- `GatewayTimeoutException`
- `PreconditionFailedException`

Mọi exception có sẵn cũng có thể cung cấp `cause` và phần mô tả lỗi thông qua tham số `options`:

```typescript
throw new BadRequestException('Something bad happened', {
  cause: new Error(),
  description: 'Some error description',
});
```

Khi đó response trông như sau:

```json
{
  "message": "Something bad happened",
  "error": "Some error description",
  "statusCode": 400
}
```

#### Mã lỗi cho máy đọc <a id="machine-readable-error-codes"></a>

`status` và `message` của một exception mô tả lỗi đủ rõ cho con người, nhưng lại không tiện để client rẽ nhánh xử lý. Nhiều lỗi khác nhau, như email không hợp lệ và mật khẩu yếu, đều có thể trả về `400 Bad Request`, buộc client phải parse chuỗi message dành cho người đọc để phân biệt chúng.

Để tránh điều đó, hãy truyền `errorCode` qua tham số `options`. Đây là một định danh ổn định, cho máy đọc, và được serialize vào body của response:

```typescript
throw new BadRequestException('Password is too weak', {
  errorCode: 'WEAK_PASSWORD',
});
```

Khi đó response mang thêm mã lỗi bên cạnh các trường thông thường:

```json
{
  "message": "Password is too weak",
  "error": "Bad Request",
  "statusCode": 400,
  "errorCode": "WEAK_PASSWORD"
}
```

`errorCode` là tùy chọn và có thể kết hợp với `cause` và `description`. Nó cũng có trên chính `HttpException`, nên custom exception cũng có thể đặt nó:

```typescript
throw new HttpException(
  'Forbidden',
  HttpStatus.FORBIDDEN,
  { errorCode: 'ACCOUNT_SUSPENDED' },
);
```

> info **Gợi ý** Khác với `cause`, vốn dành cho việc log và không bao giờ được serialize, `errorCode` là một phần của body response và được thiết kế để client sử dụng.

#### Exception filter <a id="exception-filters-1"></a>

Exception filter có sẵn tự động xử lý được nhiều trường hợp, nhưng có thể bạn muốn **toàn quyền kiểm soát** lớp xử lý exception, ví dụ để thêm log hoặc dùng một JSON schema khác tùy theo các yếu tố động. **Exception filter** được thiết kế cho đúng mục đích này. Nó cho phép bạn kiểm soát chính xác luồng thực thi và nội dung response gửi về client.

Hãy tạo một exception filter bắt các exception là instance của class `HttpException` và implement logic response tùy chỉnh cho chúng. Để làm vậy, ta cần truy cập các object `Request` và `Response` của nền tảng bên dưới. Ta sẽ dùng object `Request` để lấy `url` gốc và đưa vào response, và dùng object `Response` để trực tiếp kiểm soát response được gửi đi, bằng method `response.json()`.

```typescript
@@filename(http-exception.filter)
import { ExceptionFilter, Catch, ArgumentsHost, HttpException } from '@nestjs/common';
import type { Request, Response } from 'express';

@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();
    const status = exception.getStatus();

    response
      .status(status)
      .json({
        statusCode: status,
        timestamp: new Date().toISOString(),
        path: request.url,
      });
  }
}
@@switch
import { Catch, HttpException } from '@nestjs/common';

@Catch(HttpException)
export class HttpExceptionFilter {
  catch(exception, host) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse();
    const request = ctx.getRequest();
    const status = exception.getStatus();

    response
      .status(status)
      .json({
        statusCode: status,
        timestamp: new Date().toISOString(),
        path: request.url,
      });
  }
}
```

> info **Gợi ý** Mọi exception filter nên implement interface generic `ExceptionFilter<T>`. Interface này yêu cầu bạn cung cấp method `catch(exception: T, host: ArgumentsHost)` với signature như trên. `T` là type của exception.

> warning **Cảnh báo** Nếu bạn dùng `@nestjs/platform-fastify`, hãy dùng `response.send()` thay vì `response.json()`, và import các type tương ứng từ `fastify`.

Decorator `@Catch(HttpException)` gắn metadata cần thiết vào exception filter, báo cho Nest biết filter này chỉ tìm các exception thuộc type `HttpException` và không gì khác. Decorator `@Catch()` nhận một tham số hoặc một danh sách phân cách bằng dấu phẩy, cho phép bạn thiết lập filter cho nhiều loại exception cùng lúc.

#### Arguments host

Hãy xem các tham số của method `catch()`. Tham số `exception` là exception object đang được xử lý. Tham số `host` là một object `ArgumentsHost`, một tiện ích cho phép bạn truy cập các tham số truyền vào handler gốc, bất kể handler đó được gọi trong context nào. Trong đoạn code mẫu ở trên, ta dùng các method helper của nó để lấy các object `Request` và `Response` của request nơi exception phát sinh. `ArgumentsHost` được trình bày đầy đủ trong [chương execution context](/fundamentals/execution-context).

Lý do cần mức trừu tượng này là vì `ArgumentsHost` hoạt động được trong mọi context: context HTTP server dùng ở đây, nhưng còn cả microservice và WebSocket. Chương execution context sẽ chỉ cách lấy các <a href="/fundamentals/execution-context#host-handler-arguments">tham số bên dưới</a> cho **bất kỳ** context nào thông qua cùng một object này, giúp bạn viết một exception filter duy nhất hoạt động được trên tất cả các context.

<app-banner-courses></app-banner-courses>

#### Bind filter <a id="binding-filters"></a>

Hãy bind `HttpExceptionFilter` mới tạo vào method `create()` của `CatsController`.

```typescript
@@filename(cats.controller)
@Post()
@UseFilters(new HttpExceptionFilter())
async create(@Body() createCatDto: CreateCatDto) {
  throw new ForbiddenException();
}
@@switch
@Post()
@UseFilters(new HttpExceptionFilter())
@Bind(Body())
async create(createCatDto) {
  throw new ForbiddenException();
}
```

> info **Gợi ý** Decorator `@UseFilters()` được import từ package `@nestjs/common`.

Giống như decorator `@Catch()`, `@UseFilters()` nhận một instance filter hoặc một danh sách instance filter phân cách bằng dấu phẩy. Ở đây, ta tạo instance `HttpExceptionFilter` ngay tại chỗ. Cách khác là truyền vào class (thay vì instance), để framework lo việc khởi tạo và bật được **dependency injection**.

```typescript
@@filename(cats.controller)
@Post()
@UseFilters(HttpExceptionFilter)
async create(@Body() createCatDto: CreateCatDto) {
  throw new ForbiddenException();
}
@@switch
@Post()
@UseFilters(HttpExceptionFilter)
@Bind(Body())
async create(createCatDto) {
  throw new ForbiddenException();
}
```

> info **Gợi ý** Khi có thể, hãy ưu tiên bind filter bằng class thay vì bằng instance. Cách này giảm **lượng bộ nhớ sử dụng**, vì Nest có thể dùng lại instance của cùng một class trong toàn bộ module.

Trong ví dụ trên, `HttpExceptionFilter` chỉ được áp dụng cho route handler `create()`, tức là filter ở cấp method. Exception filter có thể được đặt ở nhiều cấp độ: cấp method (một method của controller, resolver hoặc gateway), cấp controller, hoặc cấp global. Ví dụ, để thiết lập filter ở cấp controller, làm như sau:

```typescript
@@filename(cats.controller)
@Controller()
@UseFilters(new HttpExceptionFilter())
export class CatsController {}
```

Cách này thiết lập `HttpExceptionFilter` cho mọi route handler định nghĩa trong `CatsController`.

Để tạo filter ở cấp global, làm như sau:

```typescript
@@filename(main)
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalFilters(new HttpExceptionFilter());
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

> warning **Cảnh báo** Method `useGlobalFilters()` không thiết lập filter cho gateway hay hybrid application.

Filter cấp global được dùng trên toàn ứng dụng, cho mọi controller và mọi route handler. Về mặt dependency injection, global filter đăng ký từ bên ngoài mọi module (bằng `useGlobalFilters()` như ví dụ trên) không thể inject dependency, vì việc đăng ký diễn ra bên ngoài context của mọi module. Để giải quyết, bạn có thể đăng ký filter cấp global **trực tiếp từ bất kỳ module nào** bằng cách sau:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { APP_FILTER } from '@nestjs/core';

@Module({
  providers: [
    {
      provide: APP_FILTER,
      useClass: HttpExceptionFilter,
    },
  ],
})
export class AppModule {}
```

> info **Gợi ý** Khi dùng cách này để thực hiện dependency injection cho filter, filter sẽ là global bất kể module nào dùng cách khai báo này. Hãy đăng ký nó trong module nơi filter (`HttpExceptionFilter` trong ví dụ trên) được định nghĩa. Ngoài ra, `useClass` không phải cách duy nhất để đăng ký custom provider. Tìm hiểu thêm về [custom provider](/fundamentals/custom-providers).

> info **Gợi ý** Exception throw từ [middleware](/middleware#error-handling) cũng được lớp xử lý exception xử lý. Vì middleware chạy trước khi route handler được chọn, chỉ các exception filter **global** mới được áp dụng (`app.useGlobalFilters()` hoặc `APP_FILTER`). Các binding `@UseFilters()` ở cấp method và cấp controller sẽ không được gọi.

Bạn có thể đăng ký bao nhiêu filter tùy ý bằng kỹ thuật này, chỉ cần thêm từng filter vào mảng `providers`.

#### Bắt mọi exception <a id="catch-everything"></a>

Để bắt **mọi** exception chưa được xử lý, bất kể type của nó, hãy để trống danh sách tham số của decorator `@Catch()`, tức là `@Catch()`.

Ví dụ dưới đây không phụ thuộc nền tảng: nó gửi response thông qua [HTTP adapter](./faq/http-adapter) thay vì dùng trực tiếp các object `Request` và `Response` riêng của nền tảng, nên cùng một filter chạy được với cả Express và Fastify.

```typescript
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { HttpAdapterHost } from '@nestjs/core';

@Catch()
export class CatchEverythingFilter implements ExceptionFilter {
  constructor(private readonly httpAdapterHost: HttpAdapterHost) {}

  catch(exception: unknown, host: ArgumentsHost): void {
    // In certain situations `httpAdapter` might not be available in the
    // constructor, so resolve it here.
    const { httpAdapter } = this.httpAdapterHost;

    const ctx = host.switchToHttp();

    const httpStatus =
      exception instanceof HttpException
        ? exception.getStatus()
        : HttpStatus.INTERNAL_SERVER_ERROR;

    const responseBody = {
      statusCode: httpStatus,
      timestamp: new Date().toISOString(),
      path: httpAdapter.getRequestUrl(ctx.getRequest()),
    };

    httpAdapter.reply(ctx.getResponse(), responseBody, httpStatus);
  }
}
```

> warning **Cảnh báo** Khi kết hợp một filter bắt mọi exception với một filter bind vào một type exception cụ thể, hãy khai báo filter bắt mọi exception **trước**, để filter cụ thể hơn vẫn xử lý được type mà nó được bind.

#### Kế thừa <a id="inheritance"></a>

Thông thường, bạn sẽ tạo các exception filter tùy biến hoàn toàn theo yêu cầu của ứng dụng. Tuy nhiên, trong một số trường hợp, có thể bạn chỉ muốn mở rộng **global exception filter** có sẵn và ghi đè hành vi của nó trong một số điều kiện nhất định.

Để giao việc xử lý exception cho filter gốc, hãy kế thừa `BaseExceptionFilter` và gọi method `catch()` được kế thừa.

```typescript
@@filename(all-exceptions.filter)
import { Catch, ArgumentsHost } from '@nestjs/common';
import { BaseExceptionFilter } from '@nestjs/core';

@Catch()
export class AllExceptionsFilter extends BaseExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    super.catch(exception, host);
  }
}
@@switch
import { Catch } from '@nestjs/common';
import { BaseExceptionFilter } from '@nestjs/core';

@Catch()
export class AllExceptionsFilter extends BaseExceptionFilter {
  catch(exception, host) {
    super.catch(exception, host);
  }
}
```

> warning **Cảnh báo** Các filter cấp method và cấp controller kế thừa `BaseExceptionFilter` không nên được khởi tạo bằng `new`. Thay vào đó, hãy để framework tự khởi tạo chúng.

Global filter **có thể** kế thừa filter gốc, theo một trong hai cách.

Cách thứ nhất là truyền tham chiếu `HttpAdapter` vào constructor khi khởi tạo custom global filter:

```typescript
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  const { httpAdapter } = app.get(HttpAdapterHost);
  app.useGlobalFilters(new AllExceptionsFilter(httpAdapter));

  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

Cách thứ hai là đăng ký filter bằng token `APP_FILTER`, <a href="exception-filters#binding-filters">như đã trình bày ở trên</a>.
