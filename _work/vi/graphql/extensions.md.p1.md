### Extension

> warning **Warning** Chương này chỉ áp dụng cho cách tiếp cận code first.

Extension là một **tính năng nâng cao, ở mức thấp** cho phép bạn định nghĩa dữ liệu tùy ý trong cấu hình type. Gắn custom metadata vào một số field cho phép bạn xây dựng các giải pháp tổng quát, tinh vi hơn. Ví dụ, với extension, bạn có thể định nghĩa các role cần có để truy cập những field cụ thể. Code của bạn có thể đọc các role này lúc runtime để xác định bên gọi có đủ quyền để lấy một field cụ thể hay không.

#### Thêm custom metadata

Để gắn custom metadata vào một field, hãy dùng decorator `@Extensions()` được export từ package `@nestjs/graphql`:

[[CODE:1]]

Trong ví dụ ở trên, chúng ta đã gán giá trị `Role.ADMIN` cho thuộc tính metadata `role`. `Role` là một enum TypeScript gom mọi role người dùng có trong hệ thống của chúng ta.

Ngoài field, bạn có thể dùng decorator `@Extensions()` ở cấp class và ở cấp method (ví dụ trên một query handler).

#### Dùng custom metadata

Logic dùng custom metadata có thể phức tạp tùy nhu cầu. Ví dụ, bạn có thể tạo một interceptor lưu hoặc log event cho mỗi lần gọi method, hoặc một [field middleware](/graphql/field-middleware) đối chiếu các role cần có để lấy một field với quyền của bên gọi (một hệ thống phân quyền ở cấp field).

Để minh họa, hãy định nghĩa một `checkRoleMiddleware` so sánh role của người dùng (ở đây được hardcode) với role cần có để truy cập field đích:

[[CODE:2]]

Khi đã có middleware này, hãy đăng ký nó cho field `password`:

[[CODE:3]]
