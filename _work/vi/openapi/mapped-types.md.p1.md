### Mapped type

Khi xây dựng các tính năng như **CRUD** (Create/Read/Update/Delete), việc dựng các biến thể của một base entity type thường rất hữu ích. Nest cung cấp một số hàm tiện ích thực hiện việc biến đổi type để giúp công việc này thuận tiện hơn.

#### Partial

Khi xây dựng các type dùng để validate input (còn gọi là DTO), việc dựng các biến thể **create** và **update** trên cùng một type thường rất hữu ích. Ví dụ, biến thể **create** có thể yêu cầu mọi field, trong khi biến thể **update** có thể cho mọi field là tùy chọn.

Nest cung cấp hàm tiện ích `PartialType()` để làm việc này dễ hơn và giảm thiểu boilerplate.

Hàm `PartialType()` trả về một type (class) với mọi thuộc tính của type đầu vào được đặt thành tùy chọn. Ví dụ, giả sử bạn có một type **create** như sau:

[[CODE:1]]

Mặc định, mọi field này đều là bắt buộc. Để tạo một type có cùng các field, nhưng mỗi field đều là tùy chọn, hãy dùng `PartialType()` và truyền tham chiếu class (`CreateCatDto`) làm tham số:

[[CODE:2]]

> info **Hint** Hàm `PartialType()` được import từ package `@nestjs/swagger`.

#### Pick

Hàm `PickType()` dựng một type (class) mới bằng cách chọn một tập thuộc tính từ một type đầu vào. Ví dụ, giả sử bạn bắt đầu với một type như:

[[CODE:3]]

Bạn có thể chọn một tập thuộc tính từ class này bằng hàm tiện ích `PickType()`:

[[CODE:4]]

> info **Hint** Hàm `PickType()` được import từ package `@nestjs/swagger`.

#### Omit

Hàm `OmitType()` dựng một type bằng cách chọn mọi thuộc tính từ một type đầu vào rồi loại bỏ một tập key cụ thể. Ví dụ, giả sử bạn bắt đầu với một type như:

[[CODE:5]]

Bạn có thể sinh ra một type dẫn xuất có mọi thuộc tính **trừ** `name`, như bên dưới. Trong cấu trúc này, tham số thứ hai của `OmitType()` là một mảng tên thuộc tính.

[[CODE:6]]

> info **Hint** Hàm `OmitType()` được import từ package `@nestjs/swagger`.

#### Intersection

Hàm `IntersectionType()` kết hợp hai hoặc nhiều type thành một type (class) mới. Ví dụ, giả sử bạn bắt đầu với hai type như:

[[CODE:7]]

Bạn có thể sinh ra một type mới kết hợp mọi thuộc tính của cả hai type:

[[CODE:8]]

> info **Hint** Hàm `IntersectionType()` được import từ package `@nestjs/swagger`.

#### Kết hợp

Các hàm tiện ích ánh xạ type có thể kết hợp với nhau. Ví dụ, đoạn sau tạo ra một type (class) có mọi thuộc tính của type `CreateCatDto` trừ `name`, với các thuộc tính đó được đặt thành tùy chọn:

[[CODE:9]]
