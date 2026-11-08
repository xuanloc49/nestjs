### Pipes

Pipe là một class được đánh dấu bằng decorator `@Injectable()` và implement interface `PipeTransform`.

<figure>
  <img class="illustrative-image" src="/assets/Pipe_1.png" />
</figure>

Pipe có hai công dụng điển hình:

- **transformation**: chuyển dữ liệu đầu vào sang dạng mong muốn (ví dụ từ chuỗi sang số nguyên)
- **validation**: kiểm tra dữ liệu đầu vào, nếu hợp lệ thì cho đi qua nguyên vẹn; nếu không thì throw exception

Trong cả hai trường hợp, pipe làm việc trên các tham số đang được xử lý bởi một <a href="controllers#route-parameters">route handler của controller</a>. Nest chèn pipe vào ngay trước khi method được gọi; pipe nhận các tham số dành cho method và xử lý chúng. Mọi thao tác transformation hay validation đều diễn ra lúc này, sau đó route handler mới được gọi với các tham số (có thể) đã được chuyển đổi.

Nest có sẵn một số pipe mà bạn dùng được ngay, và bạn cũng có thể tự viết pipe của riêng mình. Chương này giới thiệu các pipe có sẵn và cách bind chúng vào route handler. Sau đó, ta sẽ đi qua vài custom pipe để thấy cách xây dựng một pipe từ đầu.

> info **Hint** Pipe chạy bên trong vùng xử lý exception. Exception do pipe throw ra sẽ được lớp xử lý exception đảm nhận (global exception filter và mọi [exception filter](/exception-filters) được áp dụng cho context hiện tại). Khi pipe throw exception, route handler sẽ không được thực thi. Điều này khiến pipe trở thành nơi được khuyên dùng để validate dữ liệu đi vào ứng dụng từ các nguồn bên ngoài, ngay tại ranh giới của hệ thống.

#### Pipe có sẵn

Nest cung cấp sẵn các pipe sau, tất cả đều được export từ package `@nestjs/common`:

- `ValidationPipe`
- `StandardSchemaValidationPipe`
- `ParseIntPipe`
- `ParseFloatPipe`
- `ParseBoolPipe`
- `ParseArrayPipe`
- `ParseUUIDPipe`
- `ParseEnumPipe`
- `DefaultValuePipe`
- `ParseFilePipe`
- `ParseDatePipe`

Hãy bắt đầu với `ParseIntPipe`. Đây là ví dụ cho công dụng **transformation**: pipe đảm bảo tham số của route handler được chuyển thành số nguyên JavaScript, hoặc throw exception nếu chuyển đổi thất bại. Ở phần sau của chương, ta sẽ tự viết một bản implement đơn giản của `ParseIntPipe`. Các kỹ thuật dưới đây cũng áp dụng cho các pipe transformation có sẵn khác (`ParseBoolPipe`, `ParseFloatPipe`, `ParseEnumPipe`, `ParseArrayPipe`, `ParseDatePipe` và `ParseUUIDPipe`), mà chương này gọi chung là các pipe `Parse*`.

#### Bind pipe

Để dùng một pipe, bạn bind một instance của class pipe vào context phù hợp. Trong ví dụ `ParseIntPipe`, ta muốn gắn pipe với một method route handler cụ thể và đảm bảo nó chạy trước khi method được gọi. Cách khai báo sau làm được điều đó; ta gọi đây là bind pipe ở cấp tham số của method:

[[CODE:1]]

Cách này đảm bảo một trong hai kết quả: hoặc tham số mà `findOne()` nhận được là một số (đúng như `this.catsService.findOne()` mong đợi), hoặc một exception được throw trước khi route handler được gọi.

Ví dụ, giả sử route được gọi như sau:

[[CODE:2]]

Nest sẽ throw một exception, tạo ra response như sau:

[[CODE:3]]

Exception này ngăn phần thân của method `findOne()` thực thi.

Trong ví dụ trên, ta truyền vào một class (`ParseIntPipe`), không phải instance. Cách này để framework lo việc khởi tạo và bật được dependency injection. Giống như với guard và exception filter, bạn cũng có thể truyền một instance tạo tại chỗ, cách này hữu ích khi bạn muốn tùy chỉnh hành vi của pipe có sẵn bằng cách truyền tùy chọn:

[[CODE:4]]

Các pipe transformation khác (tất cả các pipe **Parse\***) được bind theo cùng cách. Chúng hoạt động với route parameter, query string parameter và các giá trị trong request body.

Ví dụ, với một query string parameter:

[[CODE:5]]

Ví dụ sau dùng `ParseUUIDPipe` để kiểm tra một tham số chuỗi có phải là UUID không:

[[CODE:6]]

> info **Hint** Mặc định, `ParseUUIDPipe` chấp nhận UUID ở mọi version (version 1 đến 8, Nil UUID và Max UUID). Để yêu cầu một version cụ thể, truyền tùy chọn `version` (`'1'`, `'2'`, `'3'`, `'4'`, `'5'`, `'6'`, `'7'` hoặc `'8'`). Kể từ NestJS v12.1.2, tùy chọn `version` cũng nhận các version này dưới dạng số (ví dụ `7`), và nhận `'all'` để chấp nhận mọi version, tương đương với việc bỏ trống `version`. Type `UUIDVersion` mô tả các giá trị này và được export từ `@nestjs/common`.

Bind pipe validation thì hơi khác một chút; ta sẽ nói đến ở phần sau của chương.

> info **Hint** Xem [Kỹ thuật validation](/application/validation) để có thêm nhiều ví dụ về pipe validation.

#### Custom pipe

Như đã nói, bạn có thể tự viết pipe của riêng mình. Dù Nest đã cung cấp sẵn `ParseIntPipe` và `ValidationPipe` rất mạnh, hãy cùng tự viết phiên bản đơn giản của từng cái từ đầu để thấy custom pipe được xây dựng như thế nào.

Ta bắt đầu với một `ValidationPipe` đơn giản. Ban đầu, nó nhận một giá trị đầu vào và trả về nguyên vẹn, hoạt động như một identity function.

[[CODE:7]]

> info **Hint** `PipeTransform<T, R>` là một interface generic mà mọi pipe đều phải implement. `T` là type của `value` đầu vào, còn `R` là type trả về của method `transform()`.

Mọi pipe đều phải implement method `transform()` để thỏa mãn hợp đồng của interface `PipeTransform`. Method này có hai tham số:

- `value`
- `metadata`

Tham số `value` là tham số của method đang được xử lý (trước khi route handler nhận nó), còn `metadata` là metadata của tham số đó. Object metadata có các thuộc tính sau:

[[CODE:8]]

Các thuộc tính này mô tả tham số đang được xử lý:

<table>
  <tr>
    <td>
      <code>type</code>
    </td>
    <td>Cho biết tham số là body
      (<code>@Body()</code>), query
      (<code>@Query()</code>), param
      (<code>@Param()</code>), hay một tham số tùy chỉnh (xem
      <a routerLink="/custom-decorators">custom decorator</a>).</td>
  </tr>
  <tr>
    <td>
      <code>metatype</code>
    </td>
    <td>
      Metatype của tham số, ví dụ
      <code>String</code>. Giá trị sẽ là
      <code>undefined</code> nếu bạn bỏ qua khai báo type trong signature của route handler hoặc dùng JavaScript thuần.
    </td>
  </tr>
  <tr>
    <td>
      <code>data</code>
    </td>
    <td>Chuỗi truyền vào decorator, ví dụ
      <code>@Body('string')</code>. Giá trị là
      <code>undefined</code> nếu bạn không truyền chuỗi nào vào decorator, như <code>@Body()</code>.</td>
  </tr>
  <tr>
    <td>
      <code>schema</code>
    </td>
    <td>
      Một schema tương thích Standard Schema được gắn qua tùy chọn của decorator tham số như <code>@Body({{ '{' }} schema {{ '}' }})</code> hoặc <code>@Param('id', {{ '{' }} schema {{ '}' }})</code>. Giá trị là <code>undefined</code> nếu không có schema nào được gắn.
    </td>
  </tr>
</table>

> warning **Warning** Interface TypeScript biến mất trong quá trình transpile. Nếu type của một tham số method được khai báo bằng interface thay vì class, giá trị `metatype` sẽ là `Object`.

> info **Hint** `StandardSchemaValidationPipe` có sẵn dùng trường `schema` để validate tham số với bất kỳ library nào tương thích Standard Schema. Tham số không có schema sẽ được cho đi qua nguyên vẹn.

#### Validation dựa trên schema

> info **Hint** Các phần sau tự xây dựng pipe validation từ đầu để cho thấy pipe hoạt động như thế nào. Để validation dựa trên schema trên production, hãy dùng `StandardSchemaValidationPipe` có sẵn. Pipe này chạy được với Zod, Valibot, ArkType và bất kỳ library nào tương thích [Standard Schema](https://standardschema.dev/), và đọc schema mà bạn gắn qua tùy chọn `schema` của các decorator tham số như `@Body()` và `@Param()`. Xem [Validation dựa trên schema](/application/validation#schema-based-validation) để biết chi tiết.

Hãy làm cho pipe validation hữu ích hơn. Xét method `create()` của `CatsController`: ta muốn đảm bảo object body của request POST là hợp lệ trước khi chạy method của service.

[[CODE:9]]

Tham số body `createCatDto` có type là `CreateCatDto`:

[[CODE:10]]

Mọi request tới method `create()` đều phải có body hợp lệ, nên ta cần validate ba member của object `createCatDto`. Ta có thể làm việc này ngay trong route handler, nhưng như vậy sẽ vi phạm **nguyên tắc đơn trách nhiệm** (single responsibility principle, SRP).

Một cách khác là tạo một **class validator** và giao việc cho nó. Nhược điểm là ta phải nhớ gọi validator ở đầu mỗi method.

Vậy còn middleware validation thì sao? Cách này có thể chạy, nhưng không thể tạo ra một **middleware generic** dùng được trong mọi context của ứng dụng. Middleware không biết gì về **execution context**, bao gồm handler sắp được gọi và các tham số của nó.

Pipe được thiết kế cho đúng trường hợp này, nên ta sẽ tiếp tục cải tiến pipe validation.

<app-banner-courses></app-banner-courses>

#### Validate object theo schema

Có vài cách để validate object một cách gọn gàng, theo tinh thần [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself). Một cách phổ biến là validation **dựa trên schema**, cách mà ta sẽ dùng ở đây.

Library [Zod](https://zod.dev/) cho phép bạn định nghĩa schema với API dễ đọc. Hãy xây dựng một pipe validation dùng schema của Zod.

Bắt đầu bằng việc cài package cần thiết:

[[CODE:11]]

Class dưới đây nhận một schema làm tham số constructor và gọi `schema.parse()`, method này validate tham số đầu vào theo schema đó.

Như đã nói ở trên, một **pipe validation** hoặc trả về giá trị, hoặc throw exception. Pipe này trả về giá trị đã được schema parse, hoặc throw `BadRequestException` nếu validation thất bại.

Phần tiếp theo sẽ chỉ cách cung cấp schema phù hợp cho từng route handler bằng decorator `@UsePipes()`. Nhờ đó pipe validation có thể tái sử dụng ở nhiều context, đúng như mục tiêu ban đầu.

[[CODE:12]]

#### Bind pipe validation

Ở trên, ta đã thấy cách bind các pipe transformation (như `ParseIntPipe` và các pipe `Parse*` khác). Bind pipe validation cũng đơn giản không kém.

Trong trường hợp này, ta muốn bind pipe ở cấp method. Để dùng `ZodValidationPipe` trong ví dụ, ta cần:

1. Tạo một instance của `ZodValidationPipe`
2. Truyền schema Zod tương ứng với context vào constructor của pipe
3. Bind pipe vào method

Đây là một schema Zod mẫu:

[[CODE:13]]

Bind pipe bằng decorator `@UsePipes()`:

[[CODE:14]]

> info **Hint** Decorator `@UsePipes()` được import từ package `@nestjs/common`.

Bạn cũng có thể bind `ZodValidationPipe` vào một tham số cụ thể, cùng với các pipe có sẵn. Ví dụ sau validate route parameter `id` bằng `ParseIntPipe` và request body bằng `ZodValidationPipe`:

[[CODE:15]]

> warning **Warning** Library `zod` yêu cầu bật tùy chọn compiler `strictNullChecks` trong file `tsconfig.json`.

#### Class validator

> warning **Warning** Các kỹ thuật trong phần này cần TypeScript và không dùng được nếu ứng dụng của bạn viết bằng JavaScript thuần.

Phần này trình bày một cách implement khác cho kỹ thuật validation của chúng ta.

Nest làm việc tốt với library [class-validator](https://github.com/typestack/class-validator), library này cung cấp validation dựa trên decorator. Validation dựa trên decorator kết hợp rất ăn ý với khả năng của **pipe** trong Nest, vì pipe có quyền truy cập `metatype` của tham số đang xử lý. Trước khi bắt đầu, hãy cài các package cần thiết:

[[CODE:16]]

Sau khi cài xong, thêm vài decorator vào class `CreateCatDto`. Điều này cho thấy một ưu điểm lớn của kỹ thuật này: class `CreateCatDto` vẫn là nguồn sự thật duy nhất cho object body của request POST, nên bạn không cần một class validation riêng.

[[CODE:17]]

> info **Hint** Đọc thêm về các decorator của class-validator trong [tài liệu class-validator](https://github.com/typestack/class-validator#usage).

Giờ ta có thể tạo một class `ValidationPipe` sử dụng các decorator này.

[[CODE:18]]

> info **Hint** Pipe này được cố ý viết ở mức cơ bản. Bạn không cần tự xây dựng một pipe validation generic: Nest cung cấp sẵn một `ValidationPipe` mạnh hơn, được mô tả ở cuối phần này.

> warning **Notice** Đoạn code trên dùng library [class-transformer](https://github.com/typestack/class-transformer), library này do cùng tác giả với library **class-validator** viết, nên hai library làm việc rất ăn ý với nhau.

Hãy cùng đi qua đoạn code này. Đầu tiên, method `transform()` được đánh dấu `async`. Điều này khả thi vì Nest hỗ trợ cả pipe đồng bộ lẫn **bất đồng bộ**. Ta cho method này là `async` vì một số validation của class-validator [có thể là bất đồng bộ](https://github.com/typestack/class-validator#custom-validation-classes) (chúng trả về promise).

Tiếp theo, ta dùng destructuring để lấy trường `metatype` từ object `ArgumentMetadata`. Đây là cách viết tắt cho việc nhận toàn bộ `ArgumentMetadata` rồi gán biến `metatype` trong một câu lệnh riêng.

Method helper `toValidate()` bỏ qua validation khi tham số đang xử lý là một type gốc của JavaScript. Type gốc không thể gắn decorator validation, nên không có lý do gì để validate chúng.

Tiếp theo, ta dùng hàm `plainToInstance()` của class-transformer để chuyển object tham số JavaScript thuần thành một object có type, để có thể áp dụng validation. Bước này là cần thiết vì body POST gửi đến, khi được deserialize từ network request, **không mang bất kỳ thông tin type nào** (đó là cách nền tảng bên dưới, như Express, hoạt động). Vì class-validator dựa vào các decorator validation đã định nghĩa trên DTO ở trên, ta chuyển body gửi đến thành một instance của class đã được decorate thay vì validate một object thuần.

Cuối cùng, vì đây là một **pipe validation**, nó hoặc trả về giá trị nguyên vẹn, hoặc throw exception.

Bước cuối cùng là bind `ValidationPipe`. Pipe có thể ở cấp tham số, cấp method, cấp controller hoặc cấp global. Ở trên, ta đã bind pipe validation dựa trên Zod ở cấp method bằng `@UsePipes()`. Trong ví dụ dưới đây, ta bind instance pipe vào decorator `@Body()` của route handler để pipe validate body của request POST.

[[CODE:19]]

Pipe cấp tham số hữu ích khi logic validation chỉ liên quan đến một tham số.

#### Pipe cấp global

Vì `ValidationPipe` được thiết kế generic nhất có thể, nó phát huy tác dụng tốt nhất khi là pipe **cấp global**, áp dụng cho mọi route handler trong toàn bộ ứng dụng.

[[CODE:20]]

> warning **Notice** Trong hybrid application, `useGlobalPipes()` mặc định không thiết lập pipe cho các microservice được kết nối (xem [Hybrid application](/faq/hybrid-application) để thay đổi hành vi này). Trong một ứng dụng microservice thông thường (không phải hybrid), `useGlobalPipes()` có mount pipe ở cấp global.

Global pipe đăng ký từ bên ngoài mọi module (bằng `useGlobalPipes()` như ví dụ trên) không thể inject dependency, vì việc bind diễn ra bên ngoài context của mọi module. Để giải quyết, bạn có thể đăng ký global pipe **trực tiếp từ bất kỳ module nào** bằng cách sau:

[[CODE:21]]

> info **Hint** Khi dùng cách này để thực hiện dependency injection cho pipe, pipe sẽ là global bất kể bạn đăng ký nó trong module nào. Hãy đăng ký nó trong module nơi pipe (`ValidationPipe` trong ví dụ trên) được định nghĩa. `useClass` không phải cách duy nhất để đăng ký custom provider; tìm hiểu thêm trong [Custom provider](/fundamentals/custom-providers).

#### ValidationPipe có sẵn

Bạn không cần tự xây dựng một pipe validation generic: Nest cung cấp sẵn `ValidationPipe`. `ValidationPipe` có sẵn có nhiều tùy chọn hơn bản mẫu xây dựng trong chương này, vốn được giữ ở mức cơ bản để minh họa cơ chế của một custom pipe. Với validation dựa trên schema, Nest cũng cung cấp sẵn `StandardSchemaValidationPipe`. Xem [Kỹ thuật validation](/application/validation) để biết đầy đủ chi tiết và nhiều ví dụ.

#### Công dụng transformation

Validation không phải công dụng duy nhất của custom pipe. Như đã nói ở đầu chương, pipe còn có thể **chuyển đổi** dữ liệu đầu vào sang định dạng mong muốn. Điều này khả thi vì giá trị trả về từ method `transform()` sẽ thay thế giá trị trước đó của tham số.

Khi nào thì việc này hữu ích? Đôi khi dữ liệu client gửi lên cần được thay đổi (ví dụ chuyển từ chuỗi sang số nguyên) trước khi route handler có thể xử lý. Một số trường bắt buộc cũng có thể bị thiếu, và bạn muốn áp dụng giá trị mặc định. **Pipe transformation** thực hiện những việc này bằng cách chèn một hàm xử lý vào giữa request của client và route handler.

Đây là một `ParseIntPipe` đơn giản, parse chuỗi thành số nguyên. (Như đã nói ở trên, Nest có sẵn một `ParseIntPipe` tinh vi hơn; đây chỉ là ví dụ đơn giản về một custom pipe transformation.)

[[CODE:22]]

Sau đó ta có thể bind pipe này vào tham số được chọn:

[[CODE:23]]

Một transformation hữu ích khác là tìm một entity **người dùng đã tồn tại** trong database dựa trên ID gửi kèm request:

[[CODE:24]]

Phần implement pipe này xin dành cho bạn đọc. Giống như mọi pipe transformation khác, nó nhận một giá trị đầu vào (một `id`) và trả về một giá trị đầu ra (một object `UserEntity`). Cách này giúp code của bạn mang tính khai báo hơn và [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself) hơn, bằng cách chuyển phần boilerplate ra khỏi route handler và đưa vào một pipe tái sử dụng được.

#### Cung cấp giá trị mặc định

Mặc định, các pipe `Parse*` yêu cầu giá trị của tham số phải được định nghĩa, và throw exception khi nhận được `null` hoặc `undefined` (trừ khi bạn đặt tùy chọn `optional` của chúng thành `true`). Để endpoint xử lý được các query string parameter bị thiếu, hãy cung cấp một giá trị mặc định được áp dụng trước khi các pipe `Parse*` xử lý. `DefaultValuePipe` phục vụ đúng mục đích này. Hãy khởi tạo một `DefaultValuePipe` trong decorator `@Query()`, đặt trước pipe `Parse*` tương ứng, như bên dưới:

[[CODE:25]]
