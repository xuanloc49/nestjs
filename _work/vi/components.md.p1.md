### Providers

Provider là một khái niệm cốt lõi trong Nest. Nhiều class cơ bản trong Nest, như service, repository, factory và helper, đều có thể được xem là provider. Ý tưởng chính của provider là nó có thể được **inject** vào như một dependency, nhờ đó các object có thể liên kết với nhau. Nest runtime sẽ lo việc "nối dây" giữa các object này.

<figure><img class="illustrative-image" src="/assets/Components_1.png" /></figure>

Ở chương trước, ta đã xây dựng một `CatsController` cơ bản. Controller nên tập trung xử lý HTTP request và giao các tác vụ phức tạp hơn cho **provider**. Ở dạng đơn giản nhất, provider là các class JavaScript thông thường được liệt kê trong mảng `providers` của một module. Để biết thêm chi tiết, xem chương [Modules](/modules).

> info **Hint** Nest cho phép bạn thiết kế và tổ chức dependency theo hướng đối tượng, nên việc tuân theo [nguyên tắc SOLID](https://en.wikipedia.org/wiki/SOLID) là một thói quen tốt.

#### Service

Hãy bắt đầu bằng việc tạo `CatsService`. Service này lo việc lưu trữ và truy xuất dữ liệu cho `CatsController`. Vì nó đóng gói logic của ứng dụng, nó là ứng viên tự nhiên để làm provider.

[[CODE:1]]

> info **Hint** Để tạo service bằng CLI, chạy `$ nest g service cats`.

`CatsService` là một class cơ bản với một thuộc tính và hai method. Điểm mấu chốt là decorator `@Injectable()`. Decorator này gắn metadata vào class, khai báo rằng `CatsService` có thể được quản lý bởi [IoC](https://en.wikipedia.org/wiki/Inversion_of_control) container của Nest.

Ví dụ này cũng dùng interface `Cat`:

[[CODE:2]]

Giờ đã có service để lưu và lấy dữ liệu cat, hãy dùng nó trong `CatsController`:

[[CODE:3]]

`CatsService` được **inject** qua constructor của class. Phần tiếp theo sẽ giải thích cách Nest resolve nó.

#### Dependency injection

Nest được xây dựng quanh design pattern **dependency injection**. Để làm quen với khái niệm này, xem [tài liệu Angular](https://angular.dev/guide/di).

Nest resolve dependency dựa theo type. Trong ví dụ dưới đây, Nest resolve `catsService` bằng cách cung cấp một instance của `CatsService`. Với scope mặc định (singleton), Nest chỉ tạo instance một lần và chia sẻ nó cho mọi class phụ thuộc vào nó. Sau đó Nest truyền instance này vào constructor của controller:

[[CODE:4]]

Chỉ một dòng này làm hai việc:

- Từ khóa `private` biến `catsService` thành một **parameter property** của TypeScript: nó khai báo member `catsService` trên class và gán tham số constructor cho member đó, nên bạn không phải tự viết `this.catsService = catsService`.
- Type annotation `CatsService` chính là thứ Nest dùng để resolve. Lúc compile, TypeScript emit type của các tham số constructor dưới dạng metadata, và container đọc metadata đó để xác định cần cung cấp provider nào.

> warning **Warning** Vì việc resolve dựa trên type được emit ra, annotation phải trỏ tới thứ gì đó tồn tại lúc runtime, tức là một **class**. Interface và type alias bị xóa trong quá trình compile. Nếu `AppConfig` là interface, `constructor(private config: AppConfig)` sẽ khiến Nest không có token nào để tìm, và ứng dụng sẽ lỗi ngay lúc khởi động với thông báo "Nest can't resolve dependencies". Điều tương tự xảy ra khi bạn import một class bằng `import type`, vì câu import đó cũng bị xóa. Để inject thứ không phải class, hãy đăng ký nó dưới một token và inject tường minh bằng `@Inject()`, như mô tả trong [Custom provider](/fundamentals/custom-providers#interfaces-and-abstract-classes).

#### Scope

Mặc định, vòng đời ("scope") của provider trùng với vòng đời của ứng dụng. Khi ứng dụng bootstrap, Nest resolve mọi dependency, nghĩa là mọi provider đều được khởi tạo. Tương tự, khi ứng dụng tắt, mọi provider đều bị hủy. Bạn cũng có thể gán cho provider một scope khác, ví dụ cho nó là **request-scoped** để vòng đời của nó gắn với từng request riêng lẻ. Xem chương [Injection scope](/fundamentals/injection-scopes) để biết chi tiết.

<app-banner-courses></app-banner-courses>

#### Custom provider

Nest có sẵn một IoC (inversion of control) container quản lý mối quan hệ giữa các provider. Container này là nền tảng của dependency injection và hỗ trợ nhiều hơn các provider dạng class mà ta đã thấy: bạn còn có thể định nghĩa provider bằng giá trị thuần, class, và factory đồng bộ hoặc bất đồng bộ. Để xem ví dụ, xem chương [Custom provider](/fundamentals/custom-providers).

#### Optional provider

Có những dependency không phải lúc nào cũng bắt buộc. Ví dụ, một class có thể phụ thuộc vào một **configuration object** nhưng sẽ dùng giá trị mặc định nếu không có object nào được cung cấp. Dependency như vậy là tùy chọn, và việc nó vắng mặt không nên gây ra lỗi.

Để đánh dấu một dependency là tùy chọn, áp dụng decorator `@Optional()` lên tham số constructor:

[[CODE:5]]

Ví dụ này inject một custom provider, nên nó truyền custom **token** `HTTP_OPTIONS` vào `@Inject()`. Các ví dụ trước dùng injection qua constructor, trong đó mỗi dependency được xác định bằng class của nó trong signature của constructor. Để tìm hiểu thêm về custom provider và token của chúng, xem chương [Custom provider](/fundamentals/custom-providers).

`@Optional()` chỉ ảnh hưởng đến trường hợp provider bị _thiếu_: nếu không có gì được đăng ký dưới `HTTP_OPTIONS`, Nest sẽ inject `undefined` thay vì báo lỗi lúc khởi động. Do đó, class phải tự lo phần giá trị dự phòng, thường là bằng cách merge giá trị được inject (nếu có) đè lên một bộ giá trị mặc định.

#### Injection qua property

Các ví dụ từ đầu đến giờ đều dùng injection qua constructor, tức là provider được inject thông qua constructor. Trong một số trường hợp, **injection qua property** tiện hơn. Ví dụ, nếu một class cha phụ thuộc vào một hoặc nhiều provider, việc mọi class con phải truyền chúng lên qua `super()` sẽ rất rườm rà. Thay vào đó, bạn có thể áp dụng decorator `@Inject()` trực tiếp lên property:

[[CODE:6]]

> warning **Warning** Nếu class của bạn không kế thừa class nào khác, hãy ưu tiên injection qua **constructor**. Constructor thể hiện rõ ràng class cần những dependency nào, giúp code dễ theo dõi hơn so với các property được đánh dấu `@Inject()`.

#### Đăng ký provider

Khi đã có provider (`CatsService`) và nơi dùng nó (`CatsController`), bạn cần đăng ký service với Nest để Nest có thể thực hiện việc inject. Để làm vậy, thêm service vào mảng `providers` của decorator `@Module()` trong file module (`app.module.ts`):

[[CODE:7]]

Giờ Nest đã có thể resolve các dependency của class `CatsController`.

Cấu trúc thư mục lúc này trông như sau:

<div class="file-tree">
<div class="item">src</div>
<div class="children">
<div class="item">cats</div>
<div class="children">
<div class="item">dto</div>
<div class="children">
<div class="item">create-cat.dto.ts</div>
</div>
<div class="item">interfaces</div>
<div class="children">
<div class="item">cat.interface.ts</div>
</div>
<div class="item">cats.controller.ts</div>
<div class="item">cats.service.ts</div>
</div>
<div class="item">app.module.ts</div>
<div class="item">main.ts</div>
</div>
</div>

#### Khởi tạo thủ công

Đến giờ, Nest vẫn tự động resolve dependency. Trong một số trường hợp, bạn có thể cần bước ra ngoài hệ thống dependency injection để lấy hoặc khởi tạo provider một cách thủ công. Có hai kỹ thuật cho những trường hợp này:

- Để lấy instance đã có hoặc khởi tạo provider một cách động, dùng `ModuleRef`, được mô tả trong chương [Module reference](/fundamentals/module-ref).
- Để lấy provider bên trong hàm `bootstrap()` (ví dụ cho ứng dụng standalone, hoặc để dùng một configuration service trong lúc bootstrap), xem [Ứng dụng standalone](/standalone-applications).
