### Custom provider

Các chương trước đã đề cập tới nhiều khía cạnh của **dependency injection (DI)** và cách Nest sử dụng nó. Một ví dụ là dependency injection [qua constructor](/providers#dependency-injection), dùng để inject các instance (thường là service provider) vào class. Dependency injection được tích hợp sẵn vào lõi của Nest ở mức nền tảng. Đến giờ, ta mới chỉ tìm hiểu một pattern chính. Khi ứng dụng ngày càng phức tạp, có thể bạn sẽ cần đến toàn bộ tính năng của hệ thống DI, nên chương này sẽ đi sâu hơn vào nó.

#### Nền tảng DI

Dependency injection là một kỹ thuật [inversion of control (IoC)](https://en.wikipedia.org/wiki/Inversion_of_control), trong đó bạn giao việc khởi tạo dependency cho IoC container (ở đây là hệ thống runtime của NestJS) thay vì tự khởi tạo chúng một cách tường minh trong code. Hãy xem điều gì xảy ra trong ví dụ sau từ chương [Providers](/providers).

Đầu tiên, ta định nghĩa một provider. Decorator `@Injectable()` đánh dấu class `CatsService` là một provider.

[[CODE:1]]

Sau đó ta yêu cầu Nest inject provider vào class controller:

[[CODE:2]]

Cuối cùng, ta đăng ký provider với IoC container của Nest:

[[CODE:3]]

Có ba bước then chốt giúp việc này hoạt động:

1. Trong `cats.service.ts`, decorator `@Injectable()` khai báo `CatsService` là một class mà IoC container của Nest có thể quản lý.
2. Trong `cats.controller.ts`, `CatsController` khai báo một dependency vào token `CatsService` thông qua injection qua constructor:

[[CODE:4]]

3. Trong `app.module.ts`, ta gắn token `CatsService` với class `CatsService` từ file `cats.service.ts`. Phần <a href="/fundamentals/custom-providers#standard-providers">Provider chuẩn</a> bên dưới sẽ chỉ rõ việc gắn kết này (còn gọi là _đăng ký_) diễn ra như thế nào.

Khi IoC container của Nest khởi tạo một `CatsController`, trước tiên nó tìm mọi dependency\*. Khi tìm thấy dependency `CatsService`, nó tra token `CatsService`, token này trả về class `CatsService` theo bước đăng ký (bước 3 ở trên). Giả sử scope là `SINGLETON` (mặc định), Nest sẽ hoặc tạo một instance của `CatsService`, cache lại rồi trả về, hoặc nếu đã có instance trong cache thì trả về instance đó.

\*Phần giải thích này đã được đơn giản hóa để minh họa ý chính. Trong thực tế, việc phân tích code để tìm dependency là một quá trình phức tạp diễn ra trong lúc bootstrap ứng dụng. Một đặc điểm quan trọng là việc phân tích dependency (hay "tạo dependency graph") có tính **bắc cầu**: trong ví dụ trên, nếu bản thân `CatsService` cũng có dependency, chúng cũng sẽ được resolve. Dependency graph đảm bảo các dependency được resolve đúng thứ tự, về cơ bản là "từ dưới lên". Cơ chế này giúp bạn không phải tự quản lý những dependency graph phức tạp.

<app-banner-courses></app-banner-courses>

#### Provider chuẩn

Hãy xem kỹ hơn decorator `@Module()`. Trong `app.module`, ta khai báo:

[[CODE:5]]

Thuộc tính `providers` nhận một mảng provider. Đến giờ, ta đã cung cấp các provider dưới dạng danh sách tên class. Thực ra, cú pháp `providers: [CatsService]` là cách viết tắt của cú pháp đầy đủ hơn:

[[CODE:6]]

Cách khai báo tường minh này cho thấy rõ quá trình đăng ký: nó gắn token `CatsService` với class `CatsService`. Cách viết tắt chỉ là cho tiện trong trường hợp phổ biến nhất, khi token được dùng để yêu cầu một instance của class cùng tên.

#### Custom provider

Đôi khi yêu cầu của bạn vượt quá những gì _provider chuẩn_ cung cấp. Ví dụ:

- Bạn muốn tự tạo một instance thay vì để Nest khởi tạo (hoặc trả về instance đã cache của) một class.
- Bạn muốn dùng lại một class đã có cho một dependency thứ hai.
- Bạn muốn thay một class bằng phiên bản mock để test.

Nest cho phép bạn định nghĩa custom provider để xử lý những trường hợp này, và cung cấp vài cách để định nghĩa chúng. Các phần sau sẽ đi qua từng cách.

> info **Hint** Nếu gặp vấn đề khi resolve dependency, hãy đặt biến môi trường `NEST_DEBUG` để có thêm log về quá trình resolve dependency trong lúc khởi động.

#### Value provider: `useValue`

Cú pháp `useValue` hữu ích để inject một giá trị hằng, đưa một library bên ngoài vào container của Nest, hoặc thay bản implement thật bằng một mock object. Ví dụ, giả sử bạn muốn Nest dùng một `CatsService` mock cho mục đích test:

[[CODE:7]]

Trong ví dụ này, token `CatsService` được resolve thành mock object `mockCatsService`. `useValue` yêu cầu một giá trị, ở đây là một object literal có cùng interface với class `CatsService` mà nó thay thế. Nhờ [structural typing](https://www.typescriptlang.org/docs/handbook/type-compatibility.html) của TypeScript, bạn có thể dùng bất kỳ object nào có interface tương thích, kể cả object literal hay instance class tạo bằng `new`.

#### Token provider không dựa trên class

Đến giờ, ta đã dùng tên class làm token cho provider (giá trị của thuộc tính `provide` trong một provider liệt kê ở mảng `providers`). Điều này khớp với pattern chuẩn dùng trong [injection qua constructor](/providers#dependency-injection), nơi token cũng là tên class. (Xem lại <a href="/fundamentals/custom-providers#di-fundamentals">Nền tảng DI</a> để ôn lại về token.) Đôi khi bạn cần sự linh hoạt để dùng chuỗi hoặc symbol làm DI token. Ví dụ:

[[CODE:8]]

Trong ví dụ này, ta gắn một token dạng chuỗi (`'CONNECTION'`) với một object `connection` đã có sẵn, import từ một file bên ngoài.

> warning **Notice** Ngoài chuỗi, bạn cũng có thể dùng [symbol](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Symbol) của JavaScript hoặc [enum](https://www.typescriptlang.org/docs/handbook/enums.html) của TypeScript làm giá trị token.

Pattern [injection qua constructor](/providers#dependency-injection) chuẩn **yêu cầu** dependency phải được khai báo bằng tên class. Tuy nhiên, custom provider `'CONNECTION'` lại dùng token dạng chuỗi. Để inject provider như vậy, hãy dùng decorator `@Inject()`, decorator này nhận một tham số duy nhất là token.

[[CODE:9]]

> info **Hint** Decorator `@Inject()` được import từ package `@nestjs/common`.

Các ví dụ trên dùng trực tiếp chuỗi `'CONNECTION'` để minh họa. Để tổ chức code gọn gàng, hãy định nghĩa token trong một file riêng, như `constants.ts`, rồi import ở những nơi cần, giống như cách bạn làm với symbol hoặc enum.

#### Interface và abstract class

Type và interface của TypeScript bị xóa trong quá trình compile, nên Nest không thể tham chiếu tới chúng lúc runtime. Một interface có thể mô tả hình dạng của dependency, nhưng tự nó không thể đóng vai trò DI token.

Vì Nest resolve provider dựa trên token tồn tại lúc runtime, hãy dùng token dạng chuỗi hoặc `Symbol` khi đăng ký provider cho một interface:

[[CODE:10]]

Để inject provider này, truyền token đó vào decorator `@Inject()`:

[[CODE:11]]

Khác với interface, abstract class tồn tại lúc runtime. Bạn có thể dùng abstract class vừa làm hợp đồng TypeScript vừa làm DI token:

[[CODE:12]]

Với token là abstract class, injection qua constructor dùng trực tiếp type abstract class và không cần `@Inject()`:

[[CODE:13]]

Hãy dùng token dạng chuỗi hoặc `Symbol` khi DI token lúc runtime cần tách rời khỏi class. Token `Symbol` đặc biệt hữu ích cho library và các ứng dụng lớn: mỗi symbol có một định danh duy nhất lúc runtime, giúp tránh việc vô tình trùng nhau khi các provider không liên quan dùng cùng một token chuỗi. Khi dùng token symbol, hãy export nó từ một file dùng chung và dùng lại đúng instance symbol đó ở mọi nơi provider được đăng ký và inject. Hãy dùng abstract class khi bạn muốn một thứ duy nhất vừa là hợp đồng vừa là token lúc runtime, và bạn thích injection qua constructor đơn giản hơn. Interface thuần vẫn là lựa chọn tốt khi type chỉ dùng để kiểm tra lúc compile và không cần DI token.

#### Class provider: `useClass`

Cú pháp `useClass` cho phép bạn xác định động class mà một token sẽ được resolve thành. Ví dụ, giả sử ta có một class `ConfigService` trừu tượng (hoặc mặc định), và ta muốn Nest cung cấp một bản implement khác của configuration service tùy theo môi trường hiện tại. Đoạn code sau implement chiến lược này:

[[CODE:14]]

Có hai chi tiết đáng chú ý trong ví dụ này. Thứ nhất, ta định nghĩa `configServiceProvider` dưới dạng object literal, rồi truyền nó vào thuộc tính `providers` của decorator module. Đây chỉ là cách tổ chức code; về mặt chức năng, nó tương đương với các ví dụ đã dùng từ đầu chương.

Thứ hai, ta dùng tên class `ConfigService` làm token. Với bất kỳ class nào phụ thuộc vào `ConfigService`, Nest sẽ inject một instance của class được cung cấp (`DevelopmentConfigService` hoặc `ProductionConfigService`), ghi đè lên mọi bản implement mặc định có thể đã được khai báo ở nơi khác (ví dụ một `ConfigService` khai báo với decorator `@Injectable()`).

#### Factory provider: `useFactory`

Cú pháp `useFactory` cho phép bạn tạo provider một cách **động**. Giá trị của provider chính là thứ mà hàm factory trả về. Hàm factory có thể đơn giản hoặc phức tạp tùy nhu cầu. Một factory đơn giản có thể không phụ thuộc vào provider nào khác. Một factory phức tạp hơn có thể inject các provider nó cần để tính toán kết quả. Với trường hợp sau, cú pháp factory provider có một cặp cơ chế liên quan:

1. Hàm factory có thể nhận các tham số (tùy chọn).
2. Thuộc tính `inject` (tùy chọn) nhận một mảng provider mà Nest sẽ resolve và truyền làm tham số cho hàm factory trong lúc khởi tạo. Các provider này cũng có thể được đánh dấu là tùy chọn. Hai danh sách này tương ứng với nhau: Nest truyền các instance từ danh sách `inject` vào hàm factory làm tham số, theo đúng thứ tự. Ví dụ dưới đây minh họa điều này.

[[CODE:15]]

#### Alias provider: `useExisting`

Cú pháp `useExisting` cho phép bạn tạo alias cho provider đã có, giúp bạn có hai cách để truy cập cùng một provider. Trong ví dụ dưới đây, token (dạng chuỗi) `'AliasedLoggerService'` là alias của token (dạng class) `LoggerService`. Giả sử ta có hai dependency khác nhau, một vào `'AliasedLoggerService'` và một vào `LoggerService`. Nếu cả hai dependency đều có scope `SINGLETON`, chúng sẽ cùng được resolve thành một instance.

[[CODE:16]]

#### Provider không phải service

Provider thường cung cấp service, nhưng không chỉ giới hạn ở đó. Một provider có thể cung cấp **bất kỳ** giá trị nào. Ví dụ, một provider có thể cung cấp một configuration object tùy theo môi trường hiện tại:

[[CODE:17]]

#### Export custom provider

Giống như mọi provider khác, custom provider có phạm vi giới hạn trong module khai báo nó. Để module khác thấy được nó, bạn phải export nó, bằng token hoặc bằng toàn bộ object provider.

Ví dụ sau export provider bằng token của nó:

[[CODE:18]]

Cách khác là export toàn bộ object provider:

[[CODE:19]]
