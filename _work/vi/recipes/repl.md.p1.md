### Read-Eval-Print-Loop (REPL)

REPL là một môi trường tương tác nhận từng input của người dùng, thực thi chúng, và trả kết quả về cho người dùng. Tính năng REPL cho phép bạn xem đồ thị dependency và gọi method trên các provider (và controller) trực tiếp từ terminal.

#### Cách dùng

Để chạy ứng dụng NestJS ở chế độ REPL, hãy tạo một file mới `repl.ts` (cạnh file `main.ts` hiện có) và thêm đoạn code sau:

[[CODE:1]]

Sau đó khởi động REPL từ terminal bằng lệnh sau:

[[CODE:2]]

> info **Hint** Hàm `repl()` trả về một promise resolve ra một object [Node.js REPL server](https://nodejs.org/api/repl.html). Bạn có thể truyền [các tùy chọn REPL của Node.js](https://nodejs.org/api/repl.html#replstartoptions) làm tham số thứ hai của nó.

Khi nó đang chạy, bạn sẽ thấy các message sau trong console:

[[CODE:3]]

Giờ bạn có thể tương tác với đồ thị dependency. Chẳng hạn, bạn có thể lấy instance `AppService` (ví dụ này dùng project starter) và gọi method `getHello()` của nó:

[[CODE:4]]

Bạn có thể thực thi bất kỳ đoạn code JavaScript nào từ terminal. Ví dụ, bạn có thể gán instance `AppController` cho một biến cục bộ và dùng `await` để gọi một method bất đồng bộ:

[[CODE:5]]

Để hiển thị mọi method public có trên một provider hoặc controller cho trước, hãy dùng hàm `methods()`, như sau:

[[CODE:6]]

Để in mọi module đã đăng ký dưới dạng danh sách, cùng với controller và provider của chúng, hãy dùng `debug()`:

[[CODE:7]]

Đây là một demo nhanh:

<figure><img src="/assets/repl.gif" alt="Ví dụ REPL" /></figure>

Phần tiếp theo mô tả chi tiết hơn các hàm native có sẵn.

#### Hàm native

REPL có sẵn của NestJS đi kèm một vài hàm native có sẵn ở phạm vi global khi bạn khởi động REPL. Gọi `help()` để liệt kê chúng.

Nếu bạn không nhớ signature (tức các tham số mong đợi và return type) của một hàm, hãy dùng `<function_name>.help`. Chẳng hạn:

[[CODE:8]]

> info **Hint** Các interface hàm này được viết theo [cú pháp function type expression của TypeScript](https://www.typescriptlang.org/docs/handbook/2/functions.html#function-type-expressions).

| Hàm          | Mô tả                                                                                                              | Signature                                                             |
| ------------ | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| `debug`      | In mọi module đã đăng ký dưới dạng danh sách, cùng với controller và provider của chúng. Truyền một module (ví dụ `debug(MyModule)`) để chỉ in các thành phần của module đó. | `debug(moduleCls?: ClassRef \| string) => void`                       |
| `get` hoặc `$` | Lấy một instance của provider hoặc controller; throw một exception nếu không tìm thấy.                           | `get(token: InjectionToken) => any`                                   |
| `help`       | Hiển thị mọi hàm native có sẵn của REPL.                                                                           | `help() => void`                                                      |
| `methods`    | Hiển thị mọi method public có trên một provider hoặc controller cho trước.                                         | `methods(token: ClassRef \| string) => void`                          |
| `resolve`    | Resolve một instance transient hoặc request-scoped của provider hoặc controller; throw một exception nếu không tìm thấy. | `resolve(token: InjectionToken, contextId: any) => Promise<any>`  |
| `select`     | Điều hướng qua cây module, ví dụ để lấy ra một instance cụ thể từ module được chọn.                               | `select(token: DynamicModule \| ClassRef) => INestApplicationContext` |

#### Watch mode

Trong lúc phát triển, chạy REPL ở watch mode sẽ hữu ích để các thay đổi code được phản ánh tự động:

[[CODE:9]]

Nhược điểm là lịch sử lệnh của REPL bị bỏ đi sau mỗi lần reload. Để giữ lại nó, hãy sửa hàm `bootstrap()` như sau:

[[CODE:10]]

Giờ lịch sử được giữ lại giữa các lần chạy và reload.
