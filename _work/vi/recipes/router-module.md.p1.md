### Router module

> info **Hint** Chương này chỉ liên quan tới các ứng dụng dựa trên HTTP.

Trong một ứng dụng HTTP (ví dụ một REST API), đường dẫn route của một handler được xác định bằng cách nối prefix (tùy chọn) được khai báo cho controller (bên trong decorator `@Controller()`) và bất kỳ đường dẫn nào được chỉ định trong decorator của method (ví dụ `@Get('users')`). Bạn có thể tìm hiểu thêm về điều này trong phần [routing](/controllers#routing) của chương controller. Ngoài ra, bạn có thể định nghĩa một [global prefix](/faq/global-prefix) cho mọi route được đăng ký trong ứng dụng, hoặc bật [versioning](/http/versioning).

Trong một số trường hợp, việc định nghĩa một prefix ở cấp module sẽ hữu ích, prefix này sau đó áp dụng cho mọi controller được đăng ký bên trong module đó. Ví dụ, hãy tưởng tượng một ứng dụng REST đưa ra vài endpoint được dùng bởi một phần cụ thể của ứng dụng gọi là "Dashboard". Thay vì lặp lại prefix `/dashboard` trong mỗi controller, bạn có thể dùng `RouterModule`, như sau:

[[CODE:1]]

> info **Hint** Class `RouterModule` được export từ package `@nestjs/core`.

Bạn cũng có thể định nghĩa các cấu trúc phân cấp, trong đó mỗi module có các module `children`. Các module con kế thừa prefix của module cha. Trong ví dụ sau, `AdminModule` được đăng ký làm module cha của `DashboardModule` và `MetricsModule`:

[[CODE:2]]

> info **Hint** Hãy dùng tính năng này một cách cẩn thận, vì lạm dụng nó có thể khiến code khó bảo trì theo thời gian.

Trong ví dụ ở trên, mọi controller được đăng ký bên trong `DashboardModule` đều có thêm prefix `/admin/dashboard`, vì module nối các đường dẫn một cách đệ quy từ trên xuống dưới, từ cha tới con. Tương tự, mọi controller được định nghĩa bên trong `MetricsModule` đều có thêm prefix cấp module `/admin/metrics`.
