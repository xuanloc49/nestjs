### Scalar

Một GraphQL object type có tên và các field, nhưng tới một lúc nào đó các field đó phải resolve ra dữ liệu cụ thể. Scalar type cung cấp dữ liệu đó: chúng biểu diễn các lá của query (xem [scalar type](https://graphql.org/learn/schema/#scalar-types) trong tài liệu GraphQL). GraphQL có các scalar type có sẵn sau: `Int`, `Float`, `String`, `Boolean` và `ID`. Ngoài những type này, bạn có thể cần hỗ trợ các kiểu dữ liệu nguyên tử tùy chỉnh (ví dụ `Date`).

#### Code first

Cách tiếp cận code first đi kèm năm scalar, ba trong số đó là alias cho các GraphQL type đã có:

- `ID` (alias cho `GraphQLID`): một định danh duy nhất, thường dùng để lấy lại một object hoặc làm key cho cache
- `Int` (alias cho `GraphQLInt`): một số nguyên có dấu 32-bit
- `Float` (alias cho `GraphQLFloat`): một giá trị số thực dấu phẩy động có dấu, độ chính xác kép
- `GraphQLISODateTime`: một chuỗi ngày giờ theo UTC (được dùng mặc định để biểu diễn type `Date`)
- `GraphQLTimestamp`: một số nguyên có dấu biểu diễn ngày giờ dưới dạng số mili giây kể từ khi bắt đầu Unix epoch

Mặc định, `GraphQLISODateTime` (ví dụ `2019-12-03T09:54:33Z`) biểu diễn type `Date`. Để dùng `GraphQLTimestamp` thay vào đó, hãy đặt thuộc tính `dateScalarMode` của object `buildSchemaOptions` thành `'timestamp'`:

[[CODE:1]]

Tương tự, `GraphQLFloat` mặc định biểu diễn type `number`. Để dùng `GraphQLInt` thay vào đó, hãy đặt thuộc tính `numberScalarMode` của object `buildSchemaOptions` thành `'integer'`:

[[CODE:2]]

Bạn cũng có thể tạo các custom scalar.

#### Ghi đè một scalar mặc định

Để tạo một phần hiện thực tùy chỉnh cho scalar `Date`, hãy tạo một class mới:

[[CODE:3]]

Khi đã có class này, hãy đăng ký `DateScalar` làm provider:

[[CODE:4]]

Giờ bạn có thể dùng type `Date` trong các class của mình:

[[CODE:5]]

#### Import một custom scalar

Để dùng một custom scalar, hãy import nó và đăng ký nó làm resolver. Để minh họa, chúng ta sẽ dùng package `graphql-type-json`, package này định nghĩa một GraphQL scalar type `JSON`.

Bắt đầu bằng việc cài package:

[[CODE:6]]

Khi đã cài package, hãy truyền một custom resolver cho method `forRoot()`:

[[CODE:7]]

Giờ bạn có thể dùng type `JSON` trong các class của mình:

[[CODE:8]]

Để có một bộ scalar làm sẵn, hãy xem package [graphql-scalars](https://www.npmjs.com/package/graphql-scalars).

#### Tạo một custom scalar

Để định nghĩa một custom scalar, hãy tạo một instance `GraphQLScalarType` mới. Ví dụ sau tạo một custom scalar `UUID`:

[[CODE:9]]

Sau đó truyền một custom resolver cho method `forRoot()`:

[[CODE:10]]

Giờ bạn có thể dùng type `UUID` trong các class của mình:

[[CODE:11]]

#### Schema first

Để định nghĩa một custom scalar (xem [custom scalar](https://www.apollographql.com/docs/graphql-tools/scalars.html) trong tài liệu GraphQL Tools), hãy tạo một định nghĩa type và một resolver riêng. Như trong tài liệu chính thức, chúng ta sẽ dùng package `graphql-type-json`, package này định nghĩa một GraphQL scalar type `JSON`.

Bắt đầu bằng việc cài package:

[[CODE:12]]

Khi đã cài package, hãy truyền một custom resolver cho method `forRoot()`:

[[CODE:13]]

Giờ chúng ta có thể dùng scalar `JSON` trong các định nghĩa type:

[[CODE:14]]

Một cách khác để định nghĩa một scalar type là tạo một class. Giả sử bạn muốn thêm một type `Date` vào schema:

[[CODE:15]]

Khi đã có class này, hãy đăng ký `DateScalar` làm provider:

[[CODE:16]]

Giờ bạn có thể dùng scalar `Date` trong các định nghĩa type:

[[CODE:17]]

Mặc định, định nghĩa TypeScript được sinh ra cho mọi custom scalar là `any`, vốn không type-safe. Bạn có thể cấu hình cách Nest sinh typing cho các custom scalar khi chỉ định cách sinh type:

[[CODE:18]]

> info **Hint** Ngoài ra, bạn có thể dùng một tham chiếu type, ví dụ `DateTime: Date`. Trong trường hợp này, `GraphQLDefinitionsFactory` dùng thuộc tính `name` của type được chỉ định (`Date.name`) để sinh các định nghĩa TypeScript. Với các type tùy chỉnh (không có sẵn), bạn cũng phải thêm một câu lệnh import.

Giờ, với các GraphQL custom scalar type sau:

[[CODE:19]]

Nest sinh ra các định nghĩa TypeScript sau trong `src/graphql.ts`:

[[CODE:20]]

Ở đây, thuộc tính `customScalarTypeMapping` ánh xạ mỗi custom scalar sang type TypeScript cần khai báo cho nó. Thuộc tính `additionalHeader` thêm các import mà những định nghĩa type này cần. Cuối cùng, đặt `defaultScalarType` thành `'unknown'` sẽ alias mọi custom scalar không được liệt kê trong `customScalarTypeMapping` thành `unknown` thay vì `any`, điều mà [TypeScript khuyến nghị](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-0.html#new-unknown-top-type) từ phiên bản 3.0 để tăng type safety.

> info **Hint** Ví dụ import `_BigNumber` từ `bignumber.js` dưới một alias để tránh [tham chiếu type vòng tròn](https://github.com/Microsoft/TypeScript/issues/12525#issuecomment-263166239).
