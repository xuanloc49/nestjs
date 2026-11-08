### CRUD generator (chỉ TypeScript)

Trong suốt vòng đời của một project, việc xây dựng tính năng mới thường đồng nghĩa với việc thêm resource mới vào ứng dụng. Mỗi resource mới thường đòi hỏi cùng một tập thao tác lặp đi lặp lại.

#### Giới thiệu

Xét một tình huống thực tế trong đó bạn cần đưa ra các endpoint CRUD cho hai entity, **User** và **Product**. Theo best practice, bạn sẽ phải thực hiện vài thao tác cho mỗi entity:

- Sinh một module (`nest g mo`) để giữ code có tổ chức và thiết lập ranh giới rõ ràng (gom các thành phần liên quan)
- Sinh một controller (`nest g co`) để định nghĩa các route CRUD (hoặc query/mutation cho ứng dụng GraphQL)
- Sinh một service (`nest g s`) để hiện thực và cô lập logic nghiệp vụ
- Sinh một class/interface entity để biểu diễn cấu trúc dữ liệu của resource
- Sinh các Data Transfer Object (hoặc input cho ứng dụng GraphQL) để định nghĩa cách dữ liệu được gửi qua mạng

Để tăng tốc quá trình lặp đi lặp lại này, [Nest CLI](/cli/overview) cung cấp một generator (schematic) tự động sinh toàn bộ code boilerplate này.

> info **Note** Schematic hỗ trợ sinh controller **HTTP**, controller **Microservice**, resolver **GraphQL** (cả code first lẫn schema first), và Gateway **WebSocket**.

#### Sinh một resource mới

Để tạo một resource mới, hãy chạy lệnh sau ở thư mục gốc của project:

[[CODE:1]]

Lệnh `nest g resource` không chỉ sinh các building block của NestJS (các class module, service và controller), mà còn sinh một class entity, các class DTO, và các file test (`.spec`).

Đây là file controller được sinh ra (cho một REST API):

[[CODE:2]]

Lệnh này cũng tạo các placeholder cho mọi endpoint CRUD: route cho REST API, query và mutation cho GraphQL, và message handler cho cả microservice lẫn WebSocket gateway.

> info **Note** Các class service được sinh ra **không** gắn với bất kỳ **ORM (hay nguồn dữ liệu)** cụ thể nào, điều này giúp generator đủ tổng quát để đáp ứng nhu cầu của mọi project. Mặc định, mọi method đều chứa placeholder mà bạn có thể điền bằng các nguồn dữ liệu riêng của project.

Tương tự, để sinh resolver cho một ứng dụng GraphQL, hãy chọn `GraphQL (code first)` (hoặc `GraphQL (schema first)`) làm lớp transport.

Trong trường hợp này, Nest sinh một class resolver thay vì một controller REST API:

[[CODE:3]]

> info **Hint** Để bỏ qua việc sinh file test, hãy truyền cờ `--no-spec`, như sau: `nest g resource users --no-spec`.

Như bên dưới, lệnh này không chỉ tạo mọi mutation và query boilerplate, mà còn nối mọi thứ lại với nhau, dùng `UsersService`, entity `User` và các DTO.

[[CODE:4]]
