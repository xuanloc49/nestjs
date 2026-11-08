### Resolver

Resolver cung cấp chỉ dẫn để biến một operation [GraphQL](https://graphql.org/) (một query, mutation hoặc subscription) thành dữ liệu. Chúng trả về dữ liệu theo cấu trúc được chỉ định trong schema, hoặc đồng bộ hoặc dưới dạng một promise resolve ra kết quả có cấu trúc đó. Thông thường, bạn tự tạo một **resolver map** bằng tay. Ngược lại, package `@nestjs/graphql` tự động sinh resolver map từ metadata do các decorator mà bạn dùng để chú thích class cung cấp. Để minh họa cách tạo một GraphQL API với package này, chúng ta sẽ xây dựng một API đơn giản về tác giả.

#### Code first

Với cách tiếp cận code first, bạn không tự viết GraphQL schema bằng SDL. Thay vào đó, bạn dùng decorator của TypeScript để sinh SDL từ định nghĩa class TypeScript. Package `@nestjs/graphql` đọc metadata được định nghĩa qua các decorator và sinh schema cho bạn.

#### Object type

Phần lớn các định nghĩa trong một GraphQL schema là **object type**. Mỗi object type bạn định nghĩa nên đại diện cho một domain object mà client của ứng dụng có thể cần tương tác. Ví dụ, API mẫu của chúng ta cần lấy danh sách tác giả và bài viết của họ, nên chúng ta định nghĩa type `Author` và type `Post`.

Với cách tiếp cận schema first, bạn sẽ định nghĩa type `Author` bằng SDL như thế này:

[[CODE:1]]

Với cách tiếp cận code first, bạn định nghĩa schema bằng các class TypeScript và chú thích các field của chúng bằng decorator TypeScript. Phần tương đương với SDL ở trên theo cách tiếp cận code first là:

[[CODE:2]]

> info **Hint** Hệ thống metadata reflection của TypeScript có một số hạn chế. Chẳng hạn, nó không thể xác định một class gồm những thuộc tính nào, hay một thuộc tính là tùy chọn hay bắt buộc. Vì những hạn chế này, bạn phải dùng decorator `@Field()` trong các class định nghĩa schema để cung cấp metadata về GraphQL type và tính tùy chọn của từng field, hoặc dùng [CLI plugin](/graphql/cli-plugin) để sinh metadata này cho bạn.

Object type `Author`, giống như mọi class, được tạo thành từ một tập các field, mỗi field khai báo một type. Type của một field tương ứng với một [GraphQL type](https://graphql.org/learn/schema/), có thể là một object type khác hoặc một scalar type. Một GraphQL scalar type là một kiểu nguyên thủy (như `ID`, `String`, `Boolean` hay `Int`) resolve ra một giá trị duy nhất.

> info **Hint** Ngoài các scalar type có sẵn của GraphQL, bạn có thể định nghĩa [custom scalar type](/graphql/scalars).

Định nghĩa object type `Author` ở trên khiến Nest **sinh ra** SDL đã trình bày trước đó:

[[CODE:3]]

Decorator `@Field()` nhận một type function tùy chọn (ví dụ `type => Int`), và tùy chọn thêm một options object.

Type function là bắt buộc khi việc ánh xạ giữa hệ thống type của TypeScript và hệ thống type của GraphQL không rõ ràng. Cụ thể, nó **không** bắt buộc với type `string` và `boolean`, nhưng **là** bắt buộc với `number`, vốn có thể ánh xạ sang `Int` hoặc `Float` của GraphQL (không có type function, `number` mặc định ánh xạ sang `Float`). Type function trả về GraphQL type mong muốn, như trong các ví dụ xuyên suốt các chương này.

Options object có thể có bất kỳ cặp key/value nào sau đây:

- `nullable`: field có được phép null hay không (trong `@nestjs/graphql`, mỗi field mặc định là non-nullable); `boolean`
- `description`: mô tả của field; `string`
- `deprecationReason`: đánh dấu field là deprecated; `string`

Ví dụ:

[[CODE:4]]

> info **Hint** Bạn cũng có thể thêm mô tả cho, hoặc deprecate, toàn bộ object type: `@ObjectType({{ '{' }} description: 'Author model' {{ '}' }})`. Tương tự, nếu ứng dụng của bạn phục vụ [nhiều GraphQL endpoint](/graphql/quick-start#multiple-endpoints), bạn có thể giới hạn một type vào một module cụ thể: `@ObjectType({{ '{' }} registerIn: () => AuthorsModule {{ '}' }})`.

Khi field là một mảng, bạn phải chỉ ra kiểu mảng trong type function của decorator `@Field()`, như bên dưới:

[[CODE:5]]

> info **Hint** Ký hiệu ngoặc vuông của mảng (`[ ]`) cho biết độ sâu của mảng. Ví dụ, `[[Int]]` biểu diễn một ma trận số nguyên.

Để khai báo rằng các phần tử của mảng (không phải bản thân mảng) có thể null, hãy đặt thuộc tính `nullable` thành `'items'` như bên dưới:

[[CODE:6]]

> info **Hint** Nếu cả mảng lẫn các phần tử của nó đều có thể null, hãy đặt `nullable` thành `'itemsAndList'` thay vào đó.

Khi đã có object type `Author`, hãy định nghĩa object type `Post`.

[[CODE:7]]

Object type `Post` sinh ra phần sau của GraphQL schema bằng SDL:

[[CODE:8]]

#### Resolver theo code first

Tới đây, chúng ta đã định nghĩa các object (định nghĩa type) có thể tồn tại trong data graph, nhưng client vẫn chưa có cách nào tương tác với chúng. Để giải quyết điều đó, chúng ta cần một class resolver. Với cách tiếp cận code first, một class resolver vừa định nghĩa các resolver function **vừa** sinh ra **Query type**. Ví dụ bên dưới cho thấy cách làm:

[[CODE:9]]

> info **Hint** Mọi decorator (ví dụ `@Resolver`, `@ResolveField`, `@Args`, v.v.) đều được export từ package `@nestjs/graphql`.

Bạn có thể định nghĩa nhiều class resolver, và Nest sẽ kết hợp chúng lúc runtime. Xem phần [Module](/graphql/resolvers#module) bên dưới để biết thêm về cách tổ chức code.

> warning **Note** Logic bên trong các class `AuthorsService` và `PostsService` có thể đơn giản hoặc phức tạp tùy nhu cầu. Mục đích của ví dụ này là cho thấy cách dựng resolver và cách chúng tương tác với các provider khác.

`AuthorsResolver` ở trên định nghĩa một query resolver function và một field resolver function. Để tạo một resolver, hãy tạo một class có các resolver function làm method, và chú thích class bằng decorator `@Resolver()`.

Method `author()` là một query handler trả về object tác giả theo `id` được gửi trong request. Để đánh dấu một method là query handler, hãy dùng decorator `@Query()`.

Tham số truyền cho decorator `@Resolver()` là tùy chọn, nhưng nó trở nên quan trọng khi graph của bạn không còn đơn giản: nó cung cấp parent object được các field resolver function dùng khi chúng đi xuống một object graph.

Vì class này có một **field resolver** function (cho thuộc tính `posts` của object type `Author`), bạn **phải** truyền cho decorator `@Resolver()` một giá trị chỉ ra parent type (tức class `ObjectType` tương ứng) cho mọi field resolver được định nghĩa trong class. Một field resolver cần truy cập parent object (object mà field đang được resolve thuộc về). Ở đây, field resolver điền mảng `posts` của một tác giả bằng cách gọi một service với `id` của tác giả, đó là lý do parent object phải được xác định trong decorator `@Resolver()`. Sau đó parameter decorator `@Parent()` của method sẽ lấy ra tham chiếu tới parent object đó trong field resolver.

Bạn có thể định nghĩa nhiều resolver function `@Query()` (cả trong class này lẫn trong các class resolver khác). Chúng được gộp thành một định nghĩa **Query type** duy nhất trong SDL được sinh ra, cùng với các entry tương ứng trong resolver map. Điều này cho phép bạn định nghĩa query gần với model và service mà chúng dùng, và giữ chúng được tổ chức gọn gàng trong các module.

> info **Hint** Nest CLI cung cấp một generator (schematic) sinh **toàn bộ code boilerplate** cho bạn. Xem recipe [CRUD generator](/recipes/crud-generator) để biết chi tiết.

#### Tên của query type

Trong các ví dụ ở trên, decorator `@Query()` suy ra tên GraphQL query từ tên method. Ví dụ, xét cấu trúc sau từ ví dụ ở trên:

[[CODE:10]]

Nó sinh ra entry sau cho query author trong schema (query dùng cùng tên với method):

[[CODE:11]]

> info **Hint** Tìm hiểu thêm về [GraphQL query](https://graphql.org/learn/queries/).

Theo quy ước, các tên này được tách rời nhau. Ví dụ, bạn có thể đặt tên method query handler là `getAuthor()` nhưng vẫn đưa query ra dưới tên `author`. Điều tương tự áp dụng cho field resolver. Để làm vậy, hãy truyền tên ánh xạ làm tham số cho decorator `@Query()` và `@ResolveField()`, như bên dưới:

[[CODE:12]]

Method handler `getAuthor()` ở trên sinh ra phần sau của GraphQL schema bằng SDL:

[[CODE:13]]

#### Tùy chọn của decorator Query

Options object của decorator `@Query()` (nơi chúng ta truyền `{{ '{' }}name: 'author'{{ '}' }}` ở trên) nhận một số cặp key/value:

- `name`: tên của query; một `string`
- `description`: mô tả dùng để sinh tài liệu GraphQL schema (ví dụ trong GraphiQL); một `string`
- `deprecationReason`: đánh dấu query là deprecated trong metadata của schema (ví dụ hiển thị trong GraphiQL); một `string`
- `nullable`: query có thể trả về dữ liệu null hay không; `boolean`, `'items'` hoặc `'itemsAndList'` (xem ở trên để biết chi tiết về `'items'` và `'itemsAndList'`)

#### Tùy chọn của decorator Args

Dùng decorator `@Args()` để lấy argument từ một request để dùng trong method handler. Cách này hoạt động khá giống [việc lấy route parameter trong REST](/controllers#route-parameters).

Thông thường, decorator `@Args()` không cần options object. Ví dụ, nếu một identifier là chuỗi, cấu trúc sau là đủ: nó lấy field có tên tương ứng từ GraphQL request đi vào để dùng làm tham số của method.

[[CODE:14]]

Method `getAuthor()` dùng type `number`, điều này gây ra một vấn đề: type `number` của TypeScript không mang đủ thông tin về biểu diễn GraphQL mong muốn (ví dụ `Int` hay `Float`). Vì vậy bạn phải truyền tham chiếu type một cách **tường minh**, trong một options object được truyền làm tham số thứ hai cho decorator `@Args()`:

[[CODE:15]]

Options object nhận các cặp key/value tùy chọn sau:

- `type`: một hàm trả về GraphQL type
- `defaultValue`: một giá trị mặc định; `any`
- `description`: metadata mô tả; `string`
- `deprecationReason`: để deprecate một field và cung cấp metadata mô tả lý do; `string`
- `nullable`: field có được phép null hay không

Các method query handler có thể nhận nhiều argument. Ví dụ, để lấy một tác giả theo `firstName` và `lastName`, hãy gọi `@Args()` hai lần:

[[CODE:16]]

> info **Hint** Với một field nullable của GraphQL như `firstName`, bạn không cần thêm `null` hay `undefined` vào type TypeScript của field. Tuy nhiên hãy lưu ý rằng một field nullable sẽ để các giá trị này đi qua tới resolver của bạn, nên bạn cần phòng thủ trước chúng ở đó.

#### Class argument riêng

Với các lời gọi `@Args()` inline, code như ví dụ ở trên nhanh chóng trở nên cồng kềnh. Thay vào đó, bạn có thể tạo một class argument riêng `GetAuthorArgs` và truy cập nó trong method handler như sau:

[[CODE:17]]

Tạo class `GetAuthorArgs` bằng `@ArgsType()` như bên dưới:

[[CODE:18]]

> info **Hint** Một lần nữa, do những hạn chế của hệ thống metadata reflection của TypeScript, bạn phải dùng decorator `@Field()` để chỉ ra type và tính tùy chọn, hoặc dùng [CLI plugin](/graphql/cli-plugin). Như trước, bạn không cần thêm `null` hay `undefined` vào type của field nullable `firstName`, nhưng bạn cần phòng thủ trước các giá trị này trong resolver.

Nó sinh ra phần sau của GraphQL schema bằng SDL:

[[CODE:19]]

> info **Hint** Các class argument như `GetAuthorArgs` hoạt động rất tốt với `ValidationPipe` (xem [Validation](/application/validation)).

#### Kế thừa class

Bạn có thể dùng kế thừa class tiêu chuẩn của TypeScript để tạo các base class có thể mở rộng với các tính năng tiện ích chung (field và thuộc tính của field, validation, v.v.). Ví dụ, bạn có thể có một tập argument liên quan tới phân trang luôn bao gồm các field tiêu chuẩn `offset` và `limit`, cộng thêm các field index riêng theo từng type. Bạn có thể thiết lập một cây phân cấp class như bên dưới.

Base class `@ArgsType()`:

[[CODE:20]]

Subclass riêng theo type của base class `@ArgsType()`:

[[CODE:21]]

Cách tương tự có thể áp dụng cho các object `@ObjectType()`. Định nghĩa các thuộc tính chung trên base class:

[[CODE:22]]

Thêm các thuộc tính riêng theo type trên các subclass:

[[CODE:23]]

Bạn cũng có thể dùng kế thừa với resolver, và kết hợp nó với generic của TypeScript để giữ type safety. Ví dụ, để tạo một base class có một query `findAll` chung, hãy dùng cấu trúc như thế này:

[[CODE:24]]

Lưu ý những điểm sau:

- Cần có return type tường minh (`any` ở trên); nếu không, TypeScript sẽ phàn nàn về việc dùng một định nghĩa class private. Chúng tôi khuyên bạn định nghĩa một interface thay vì dùng `any`.
- `Type` được import từ package `@nestjs/common`.
- Thuộc tính `isAbstract: true` cho biết không nên sinh SDL (các câu lệnh Schema Definition Language) cho class này. Bạn cũng có thể đặt thuộc tính này trên các type khác để ngăn việc sinh SDL.

Đây là cách bạn có thể tạo một subclass cụ thể của `BaseResolver`:

[[CODE:25]]

Cấu trúc này sẽ sinh ra SDL sau:

[[CODE:26]]

#### Generic

Chúng ta đã thấy một cách dùng generic ở trên. Generic cho phép bạn xây các lớp trừu tượng có thể tái sử dụng. Ví dụ, đây là một cách hiện thực phân trang dựa trên cursor theo [hướng dẫn phân trang của GraphQL](https://graphql.org/learn/pagination/#pagination-and-edges):

[[CODE:27]]

Khi đã định nghĩa base class này, bạn có thể tạo các type chuyên biệt kế thừa hành vi của nó. Ví dụ:

[[CODE:28]]

#### Schema first

Như đã đề cập trong chương [Bắt đầu nhanh](/graphql/quick-start), với cách tiếp cận schema first, bạn bắt đầu bằng việc tự định nghĩa các type của schema bằng SDL (xem [ngôn ngữ type của GraphQL](https://graphql.org/learn/schema/#type-language)). Xét các định nghĩa type SDL sau.

> info **Hint** Để tiện theo dõi, chương này giữ toàn bộ SDL ở một chỗ (ví dụ một file `.graphql`, như bên dưới). Trong thực tế, bạn có thể muốn tổ chức theo module hơn. Ví dụ, bạn có thể tạo các file SDL riêng chứa định nghĩa type cho từng domain entity, và đặt chúng cùng các service, code resolver và class Nest module liên quan trong một thư mục riêng cho entity đó. Nest sẽ gộp mọi định nghĩa type riêng lẻ của schema lúc runtime.

[[CODE:29]]

#### Resolver theo schema first

Schema ở trên đưa ra một query duy nhất: `author(id: Int!): Author`.

> info **Hint** Tìm hiểu thêm về [GraphQL query](https://graphql.org/learn/queries/).

Giờ hãy tạo một class `AuthorsResolver` resolve các query về tác giả:

[[CODE:30]]

> info **Hint** Mọi decorator (ví dụ `@Resolver`, `@ResolveField`, `@Args`, v.v.) đều được export từ package `@nestjs/graphql`.

> warning **Note** Logic bên trong các class `AuthorsService` và `PostsService` có thể đơn giản hoặc phức tạp tùy nhu cầu. Mục đích của ví dụ này là cho thấy cách dựng resolver và cách chúng tương tác với các provider khác.

Decorator `@Resolver()` là bắt buộc. Nó nhận một tham số chuỗi tùy chọn là tên của một type. Tên này là bắt buộc bất cứ khi nào class có các decorator `@ResolveField()`, để cho Nest biết các method được gắn decorator liên kết với parent type nào (type `Author` trong ví dụ này). Ngoài ra, thay vì áp dụng `@Resolver()` cho class, bạn có thể áp dụng nó cho từng method:

[[CODE:31]]

Trong trường hợp này (`@Resolver()` ở cấp method), nếu một class có nhiều method `@ResolveField()`, bạn phải thêm `@Resolver()` cho từng method. Đây không được coi là best practice, vì nó tạo thêm chi phí.

> info **Hint** Bất kỳ tham số tên class nào được truyền cho `@Resolver()` đều **không** ảnh hưởng tới query (decorator `@Query()`) hay mutation (decorator `@Mutation()`).

> warning **Warning** Dùng decorator `@Resolver` ở cấp method không được hỗ trợ với cách tiếp cận **code first**.

Trong các ví dụ ở trên, decorator `@Query()` và `@ResolveField()` được liên kết với các field của GraphQL schema dựa trên tên method. Ví dụ, xét cấu trúc sau từ ví dụ ở trên:

[[CODE:32]]

Nó sinh ra entry sau cho query author trong schema (query dùng cùng tên với method):

[[CODE:33]]

Theo quy ước, các tên này được tách rời nhau, dùng những tên như `getAuthor()` hay `getPosts()` cho các method resolver. Để làm vậy, hãy truyền tên ánh xạ làm tham số cho decorator, như bên dưới:

[[CODE:34]]

> info **Hint** Nest CLI cung cấp một generator (schematic) sinh **toàn bộ code boilerplate** cho bạn. Xem recipe [CRUD generator](/recipes/crud-generator) để biết chi tiết.

#### Sinh type

Nếu bạn dùng cách tiếp cận schema first và đã bật việc sinh typing (với `outputAs: 'class'`, như trong chương [Bắt đầu nhanh](/graphql/quick-start)), việc chạy ứng dụng sẽ sinh ra file sau tại vị trí bạn đã chỉ định trong method `GraphQLModule.forRoot()`, ví dụ `src/graphql.ts`:

[[CODE:35]]

Sinh class (thay vì interface mặc định) cho phép bạn kết hợp các **decorator** validation khai báo với cách tiếp cận schema first (xem [Validation](/application/validation)). Ví dụ, bạn có thể thêm các decorator `class-validator` vào class `CreatePostInput` được sinh ra, như bên dưới, để bắt buộc độ dài chuỗi tối thiểu và tối đa cho field `title`:

[[CODE:36]]

> warning **Notice** Để bật validation tự động cho input (và parameter) của bạn, hãy dùng `ValidationPipe`. Tìm hiểu thêm trong các chương [Validation](/application/validation) và [Pipe](/pipes).

Tuy nhiên, các decorator được thêm trực tiếp vào file được sinh ra sẽ bị **ghi đè** mỗi khi file được sinh lại. Thay vào đó, hãy tạo một file riêng và kế thừa class được sinh ra.

[[CODE:37]]

#### Decorator cho argument của GraphQL

Bạn có thể truy cập các argument tiêu chuẩn của GraphQL resolver bằng các decorator riêng. Bảng bên dưới ánh xạ các decorator của Nest với các tham số Apollo thuần mà chúng đại diện.

<table>
  <tbody>
    <tr>
      <td><code>@Root()</code> và <code>@Parent()</code></td>
      <td><code>root</code>/<code>parent</code></td>
    </tr>
    <tr>
      <td><code>@Context(param?: string)</code></td>
      <td><code>context</code> / <code>context[param]</code></td>
    </tr>
    <tr>
      <td><code>@Info(param?: string)</code></td>
      <td><code>info</code> / <code>info[param]</code></td>
    </tr>
    <tr>
      <td><code>@Args(param?: string)</code></td>
      <td><code>args</code> / <code>args[param]</code></td>
    </tr>
  </tbody>
</table>

Các argument này có ý nghĩa như sau:

- `root`: một object chứa kết quả trả về từ resolver trên parent field, hoặc, với một field `Query` cấp cao nhất, là `rootValue` được truyền từ cấu hình server.
- `context`: một object được dùng chung bởi mọi resolver trong một query cụ thể; thường dùng để chứa trạng thái theo từng request.
- `info`: một object chứa thông tin về trạng thái thực thi của query.
- `args`: một object chứa các argument được truyền vào field trong query.

<app-banner-observe></app-banner-observe>

#### Module

Với các bước ở trên, chúng ta đã khai báo đầy đủ mọi thông tin mà `GraphQLModule` cần để sinh resolver map. `GraphQLModule` dùng reflection để đọc metadata được cung cấp qua các decorator, và tự động biến các class thành resolver map đúng.

Việc duy nhất còn lại bạn cần làm là **cung cấp** class resolver (`AuthorsResolver`), tức là liệt kê nó làm provider trong một module, và import module đó (`AuthorsModule`) ở đâu đó để Nest có thể dùng nó.

Ví dụ, bạn có thể làm việc này trong một `AuthorsModule`, module này cũng có thể cung cấp các service khác cần thiết trong ngữ cảnh này. Hãy đảm bảo import `AuthorsModule` ở đâu đó (ví dụ trong root module, hoặc trong một module khác được root module import).

[[CODE:38]]

> info **Hint** Tổ chức code theo **domain model** sẽ rất hữu ích (tương tự cách bạn tổ chức các entry point trong một REST API). Theo cách này, hãy giữ các model (class `ObjectType`), resolver và service cùng nhau trong một Nest module đại diện cho domain model đó, mỗi module một thư mục. Khi bạn làm vậy và dùng [Nest CLI](/cli/overview) để sinh từng thành phần, CLI sẽ nối các phần này lại với nhau cho bạn (đặt file vào đúng thư mục, thêm entry vào các mảng `providers` và `imports`, v.v.).
