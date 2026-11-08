### Mongo

Nest hỗ trợ hai cách để tích hợp với database [MongoDB](https://www.mongodb.com/). Bạn có thể dùng module [TypeORM](https://github.com/typeorm/typeorm) mô tả trong [chương TypeORM](/data/typeorm), vốn có connector cho MongoDB, hoặc dùng [Mongoose](https://mongoosejs.com), công cụ mô hình hóa object cho MongoDB phổ biến nhất. Chương này mô tả cách thứ hai, dùng package chuyên dụng `@nestjs/mongoose`.

Bắt đầu bằng việc cài các dependency cần thiết:

[[CODE:1]]

Sau khi cài xong, import `MongooseModule` vào root module `AppModule`:

[[CODE:2]]

Method `forRoot()` nhận cùng configuration object như `mongoose.connect()` của package Mongoose, như mô tả trong [hướng dẫn kết nối của Mongoose](https://mongoosejs.com/docs/connections.html).

#### Inject model

Với Mongoose, mọi thứ đều bắt nguồn từ một [Schema](https://mongoosejs.com/docs/guide.html). Mỗi schema ánh xạ tới một collection MongoDB và định nghĩa cấu trúc của các document trong collection đó. Schema được dùng để định nghĩa [Model](https://mongoosejs.com/docs/models.html). Model chịu trách nhiệm tạo và đọc document từ database MongoDB bên dưới.

Bạn có thể tạo schema bằng decorator của NestJS, hoặc tự tạo bằng chính Mongoose. Dùng decorator để tạo schema giúp giảm đáng kể boilerplate và cải thiện khả năng đọc code nói chung.

Hãy định nghĩa `CatSchema`:

[[CODE:3]]

> info **Hint** Bạn cũng có thể sinh ra một định nghĩa schema thô bằng class `DefinitionsFactory` (từ package `@nestjs/mongoose`). Cách này cho phép bạn tự sửa định nghĩa schema được sinh ra từ metadata đã cung cấp, hữu ích cho những trường hợp đặc biệt khó biểu diễn hết bằng decorator.

Decorator `@Schema()` đánh dấu một class là định nghĩa schema. Nó ánh xạ class `Cat` tới một collection MongoDB cùng tên, nhưng thêm chữ "s" ở cuối, nên tên collection cuối cùng là `cats`. Decorator này nhận một tham số tùy chọn duy nhất là một object tùy chọn schema. Hãy hình dung nó như object mà bạn thường truyền làm tham số thứ hai cho constructor của class `mongoose.Schema` (ví dụ `new mongoose.Schema(_, options)`). Để tìm hiểu thêm về các tùy chọn schema có sẵn, xem tài liệu [Mongoose schema options](https://mongoosejs.com/docs/guide.html#options).

Decorator `@Prop()` định nghĩa một thuộc tính trong document. Ví dụ, định nghĩa schema ở trên định nghĩa ba thuộc tính: `name`, `age` và `breed`. [Schema type](https://mongoosejs.com/docs/schematypes.html) của các thuộc tính này được tự động suy ra nhờ khả năng metadata (và reflection) của TypeScript. Tuy nhiên, trong những tình huống phức tạp hơn mà type không thể được suy ra ngầm (ví dụ mảng hoặc cấu trúc object lồng nhau), bạn phải chỉ định type một cách tường minh, như sau:

[[CODE:4]]

Ngoài ra, decorator `@Prop()` nhận một tham số options object (đọc thêm về [các tùy chọn schema type có sẵn](https://mongoosejs.com/docs/schematypes.html#schematype-options)). Với nó, bạn có thể chỉ định một thuộc tính là bắt buộc, đặt giá trị mặc định, hoặc đánh dấu nó là không thể thay đổi (immutable). Ví dụ:

[[CODE:5]]

Để chỉ định relation tới một model khác (để populate sau này), bạn cũng dùng decorator `@Prop()`. Ví dụ, nếu `Cat` có một `Owner` được lưu trong một collection khác tên là `owners`, thuộc tính cần có các tùy chọn `type` và `ref`:

[[CODE:6]]

Nếu có nhiều owner, cấu hình thuộc tính trông như sau:

[[CODE:7]]

Nếu bạn không định lúc nào cũng populate tham chiếu tới collection khác, hãy cân nhắc dùng `mongoose.Types.ObjectId` làm type:

[[CODE:8]]

Sau đó, khi cần populate có chọn lọc, hãy dùng một hàm repository chỉ định đúng type:

[[CODE:9]]

> info **Hint** Nếu không có document ngoại nào để populate, type có thể là `Owner | null`, tùy theo [cấu hình Mongoose](https://mongoosejs.com/docs/populate.html#doc-not-found) của bạn. Hoặc nó có thể throw lỗi, khi đó type là `Owner`.

Cuối cùng, bạn cũng có thể truyền một định nghĩa schema **thô** vào decorator. Điều này hữu ích khi, chẳng hạn, một thuộc tính biểu diễn một object lồng nhau không được định nghĩa dưới dạng class. Để làm vậy, dùng hàm `raw()` từ package `@nestjs/mongoose`, như sau:

[[CODE:10]]

Ngoài ra, nếu bạn thích **không dùng decorator**, bạn có thể tự định nghĩa schema. Ví dụ:

[[CODE:11]]

File `cat.schema` nằm trong thư mục `schemas` bên trong thư mục `cats`, nơi `CatsModule` cũng được định nghĩa. Dù bạn có thể đặt file schema ở bất cứ đâu, chúng tôi khuyên đặt chúng gần các object **domain** liên quan, trong thư mục module tương ứng.

Hãy xem `CatsModule`:

[[CODE:12]]

`MongooseModule` cung cấp method `forFeature()` để cấu hình module, bao gồm việc định nghĩa những model nào được đăng ký trong scope hiện tại. Để dùng các model ở một module khác, hãy thêm `MongooseModule` vào mảng `exports` của `CatsModule` và import `CatsModule` ở module đó.

Khi đã đăng ký schema, bạn có thể inject model `Cat` vào `CatsService` bằng decorator `@InjectModel()`:

[[CODE:13]]

#### Connection

Đôi khi, bạn có thể cần truy cập object [Mongoose Connection](https://mongoosejs.com/docs/api.html#Connection) gốc, ví dụ để gọi các API gốc trên nó. Inject Mongoose connection bằng decorator `@InjectConnection()` như sau:

[[CODE:14]]

#### Session

Để bắt đầu một session với Mongoose, hãy inject kết nối database bằng `@InjectConnection()` thay vì gọi trực tiếp `mongoose.startSession()`. Cách này tích hợp với hệ thống dependency injection của Nest và đảm bảo session được bắt đầu trên kết nối mà Nest quản lý.

Đây là ví dụ cách bắt đầu một session:

[[CODE:15]]

Trong ví dụ này, `@InjectConnection()` inject Mongoose connection vào service. Sau đó bạn có thể gọi `connection.startSession()` để bắt đầu một session mới và dùng nó để quản lý database transaction, đảm bảo các thao tác nguyên tử qua nhiều query. Sau khi bắt đầu transaction, hãy nhớ commit hoặc abort nó tùy theo logic của bạn, và kết thúc session khi xong.

#### Nhiều database

Một số project cần nhiều kết nối database, và module này cũng hỗ trợ điều đó. Để làm việc với nhiều kết nối, trước tiên hãy tạo các kết nối. Trong trường hợp này, việc đặt tên cho kết nối là **bắt buộc**.

[[CODE:16]]

> warning **Notice** Đừng tạo nhiều kết nối không có tên hoặc trùng tên, nếu không chúng sẽ ghi đè lẫn nhau.

Với cách thiết lập này, bạn phải cho method `MongooseModule.forFeature()` biết cần dùng kết nối nào:

[[CODE:17]]

Bạn cũng có thể inject object `Connection` của một kết nối cụ thể:

[[CODE:18]]

Để inject một `Connection` cụ thể vào một custom provider (ví dụ một factory provider), hãy dùng hàm `getConnectionToken()`, truyền tên của kết nối làm tham số:

[[CODE:19]]

Để inject một model từ một kết nối có tên, hãy truyền tên kết nối làm tham số thứ hai cho decorator `@InjectModel()`:

[[CODE:20]]

#### Hook (middleware)

Middleware (còn gọi là pre hook và post hook) là các hàm được trao quyền điều khiển trong quá trình thực thi các hàm bất đồng bộ. Middleware được chỉ định ở cấp schema và hữu ích để viết plugin (xem [tài liệu middleware của Mongoose](https://mongoosejs.com/docs/middleware.html)). Gọi `pre()` hoặc `post()` sau khi đã compile model sẽ không có tác dụng trong Mongoose. Để đăng ký hook **trước** khi đăng ký model, hãy dùng method `forFeatureAsync()` của `MongooseModule` cùng với một factory provider (tức là `useFactory`). Với kỹ thuật này, bạn có thể truy cập object schema, rồi dùng method `pre()` hoặc `post()` của nó để đăng ký hook trên schema đó. Ví dụ:

[[CODE:21]]

Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, hàm factory có thể là `async` và có thể inject dependency qua `inject`.

[[CODE:22]]

#### Plugin

Để đăng ký một [plugin](https://mongoosejs.com/docs/plugins.html) cho một schema cụ thể, dùng method `forFeatureAsync()`:

[[CODE:23]]

Để đăng ký một plugin cho mọi schema cùng lúc, hãy gọi method `.plugin()` của object `Connection`. Bạn phải truy cập connection trước khi model được tạo; để làm vậy, dùng tùy chọn `connectionFactory`:

[[CODE:24]]

#### Discriminator

[Discriminator](https://mongoosejs.com/docs/discriminators.html) là một cơ chế kế thừa schema. Chúng cho phép bạn có nhiều model với các schema chồng lấn nhau trên cùng một collection MongoDB bên dưới.

Giả sử bạn muốn theo dõi các loại event khác nhau trong một collection duy nhất. Mọi event đều có timestamp.

[[CODE:25]]

> info **Hint** Mongoose phân biệt các discriminator model qua "discriminator key", mặc định là `__t`. Mongoose thêm một path kiểu String tên là `__t` vào schema của bạn và dùng nó để theo dõi một document là instance của discriminator nào.
> Bạn cũng có thể dùng tùy chọn `discriminatorKey` để định nghĩa path dùng để phân biệt.

Các instance `SignUpEvent` và `ClickedLinkEvent` sẽ được lưu trong cùng collection với các event thông thường.

Giờ hãy định nghĩa class `ClickedLinkEvent`, như sau:

[[CODE:26]]

Và class `SignUpEvent`:

[[CODE:27]]

Khi đã có những thứ trên, hãy dùng tùy chọn `discriminators` để đăng ký discriminator cho một schema cụ thể. Nó hoạt động với cả `MongooseModule.forFeature()` lẫn `MongooseModule.forFeatureAsync()`:

[[CODE:28]]

#### Test

Khi unit test một ứng dụng, thông thường bạn muốn tránh mọi kết nối database, giúp các test suite dễ thiết lập và chạy nhanh hơn. Tuy nhiên, các class của bạn có thể phụ thuộc vào các model lấy từ instance kết nối. Để resolve các class này, hãy tạo các mock model.

Để việc này dễ hơn, package `@nestjs/mongoose` cung cấp hàm `getModelToken()` trả về một [injection token](/fundamentals/custom-providers#di-fundamentals) có sẵn dựa trên tên model. Với token này, bạn có thể cung cấp một bản implement mock bằng bất kỳ kỹ thuật [custom provider](/fundamentals/custom-providers) chuẩn nào, bao gồm `useClass`, `useValue` và `useFactory`. Ví dụ:

[[CODE:29]]

Trong ví dụ này, một `catModel` hard-code (một instance object) sẽ được cung cấp mỗi khi có nơi inject `Model<Cat>` bằng decorator `@InjectModel()`.

<app-banner-courses></app-banner-courses>

#### Cấu hình bất đồng bộ

Khi cần truyền tùy chọn module theo kiểu bất đồng bộ thay vì tĩnh, hãy dùng method `forRootAsync()`. Giống như hầu hết dynamic module, Nest cung cấp vài kỹ thuật cho cấu hình bất đồng bộ.

Một kỹ thuật là dùng hàm factory:

[[CODE:30]]

Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, hàm factory có thể là `async` và có thể inject dependency qua `inject`.

[[CODE:31]]

Cách khác là cấu hình `MongooseModule` bằng một class thay vì factory, như bên dưới:

[[CODE:32]]

Cách khai báo trên khởi tạo `MongooseConfigService` bên trong `MongooseModule`, dùng nó để tạo options object cần thiết. Trong ví dụ này, `MongooseConfigService` phải implement interface `MongooseOptionsFactory`, như bên dưới. `MongooseModule` gọi method `createMongooseOptions()` trên object đã khởi tạo của class được cung cấp.

[[CODE:33]]

Để dùng lại một options provider đã có thay vì tạo một bản sao riêng bên trong `MongooseModule`, hãy dùng cú pháp `useExisting`. Provider đó phải implement interface `MongooseOptionsFactory`:

[[CODE:34]]

#### Event của kết nối

Bạn có thể lắng nghe các [event kết nối](https://mongoosejs.com/docs/connections.html#connection-events) của Mongoose bằng tùy chọn cấu hình `onConnectionCreate`. Nest gọi hàm này với mỗi kết nối ngay khi kết nối được tạo, trước khi nó mở, nên bạn có thể đăng ký listener cho các event `connected`, `open`, `disconnected`, `reconnected` và `disconnecting`, như minh họa bên dưới:

[[CODE:35]]

Đoạn code này thiết lập kết nối tới một database MongoDB tại `mongodb://localhost/test`. Tùy chọn `onConnectionCreate` thiết lập các event listener để theo dõi trạng thái kết nối:

- `connected`: Được kích hoạt khi kết nối được thiết lập thành công.
- `open`: Kích hoạt khi kết nối đã mở hoàn toàn và sẵn sàng cho các thao tác.
- `disconnected`: Được gọi khi mất kết nối.
- `reconnected`: Được gọi khi kết nối được thiết lập lại sau khi bị ngắt.
- `disconnecting`: Xảy ra khi kết nối đang trong quá trình đóng.

Bạn cũng có thể dùng thuộc tính `onConnectionCreate` trong các cấu hình bất đồng bộ tạo bằng `MongooseModule.forRootAsync()`:

[[CODE:36]]

#### Subdocument

Để lồng subdocument bên trong một document cha, hãy định nghĩa các schema như sau:

[[CODE:37]]

Rồi tham chiếu tới subdocument trong schema cha:

[[CODE:38]]

Để chứa nhiều subdocument, hãy dùng một mảng subdocument. Nhớ ghi đè type của thuộc tính cho phù hợp:

[[CODE:39]]

#### Virtual

Trong Mongoose, một **virtual** là một thuộc tính tồn tại trên document nhưng không được lưu vào MongoDB. Thay vào đó, nó được tính động mỗi khi được truy cập. Virtual thường được dùng cho các giá trị dẫn xuất hoặc tính toán, như kết hợp các trường (ví dụ tạo thuộc tính `fullName` bằng cách nối `firstName` và `lastName`), hoặc để tạo các thuộc tính dựa trên dữ liệu đã có trong document.

[[CODE:40]]

> info **Hint** Decorator `@Virtual()` được import từ package `@nestjs/mongoose`.

Trong ví dụ này, virtual `fullName` được suy ra từ `firstName` và `lastName`. Dù nó hoạt động như một thuộc tính bình thường khi được truy cập, nó không bao giờ được lưu vào document MongoDB.

#### Ví dụ

Một ví dụ chạy được có sẵn trong [repository nestjs/nest](https://github.com/nestjs/nest/tree/master/sample/06-mongoose).
