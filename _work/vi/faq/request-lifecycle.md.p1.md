### Vòng đời request

Ứng dụng Nest xử lý request và tạo response theo một trình tự gọi là **vòng đời request**. Với middleware, pipe, guard và interceptor cùng tham gia, việc lần ra một đoạn code cụ thể chạy ở đâu trong vòng đời request có thể khá khó, đặc biệt khi các thành phần cấp global, cấp controller và cấp route được kết hợp với nhau. Nhìn chung, một request đi qua middleware, rồi guard, rồi interceptor, rồi pipe, và cuối cùng quay lại qua interceptor trên đường trả về (khi response được tạo ra).

#### Middleware

Middleware chạy theo một trình tự cụ thể. Trước tiên, Nest chạy các middleware được gắn global (như middleware được gắn bằng `app.use()`), rồi chạy [middleware gắn với module](/middleware), loại được so khớp theo path. Middleware chạy tuần tự theo thứ tự chúng được gắn, giống như middleware trong Express. Với middleware được gắn ở các module khác nhau, middleware từ các global module (được gắn `@Global()`) chạy trước, sau đó là middleware gắn trong root module, tiếp theo là middleware từ các module khác, sắp xếp theo khoảng cách của chúng tới root module trong đồ thị import.

#### Guard

Việc thực thi guard bắt đầu với global guard, tiếp tục với controller guard, và kết thúc với route guard. Như với middleware, guard chạy theo thứ tự chúng được gắn. Ví dụ:

[[CODE:1]]

`Guard1` sẽ thực thi trước `Guard2` và cả hai sẽ thực thi trước `Guard3`.

> info **Hint** "Global", "controller" và "route" chỉ nơi mà guard (hoặc thành phần khác) được gắn. Một thành phần được đăng ký bằng `app.useGlobalGuards()` (hoặc method tương tự), hoặc được cung cấp qua một module với token `APP_GUARD` (hoặc token tương tự), là được gắn global. Nếu không, nó được gắn với một controller nếu decorator đứng trước một class controller, hoặc với một route nếu decorator đứng trước một route handler.

#### Interceptor

Interceptor phần lớn theo cùng pattern như guard, với một khác biệt: vì interceptor trả về [RxJS Observable](https://github.com/ReactiveX/rxjs), các observable được resolve theo kiểu vào trước ra sau. Request đi vào đi theo thứ tự tiêu chuẩn global, controller, route, nhưng phía response (tức là sau khi route handler trả về) được resolve từ route tới controller tới global. Ngoài ra, mọi lỗi do pipe, controller hay service throw đều có thể được đọc trong operator `catchError` của interceptor.

#### Pipe

Pipe theo trình tự tiêu chuẩn global, controller, route, và các pipe được truyền cho `@UsePipes()` chạy theo kiểu vào trước ra trước. Tuy nhiên, ở cấp route parameter, khi nhiều parameter có pipe, các pipe xử lý parameter cuối cùng trước và parameter đầu tiên sau cùng. Điều này cũng áp dụng cho pipe cấp route và cấp controller. Ví dụ, xét controller sau:

[[CODE:2]]

Ở đây, `GeneralValidationPipe` chạy cho object `query`, rồi `params`, rồi `body` trước khi chuyển sang `RouteSpecificPipe`, pipe này cũng theo cùng thứ tự. Mọi pipe riêng cho parameter sẽ chạy (một lần nữa, từ parameter cuối tới parameter đầu) sau các pipe cấp controller và cấp route.

#### Filter

Filter là thành phần duy nhất không resolve global trước. Thay vào đó, filter resolve từ cấp thấp nhất có thể: Nest kiểm tra filter gắn với route trước, rồi filter cấp controller, và cuối cùng là filter global. Exception không thể được chuyển từ filter này sang filter khác; nếu một filter cấp route bắt exception, một filter cấp controller hay global không thể bắt cùng exception đó. Để đạt hiệu quả tương tự, hãy dùng kế thừa giữa các filter.

> info **Hint** Filter chỉ chạy khi một exception chưa được bắt xảy ra trong quá trình xử lý request. Các exception mà bạn tự bắt (ví dụ bằng `try/catch`) không kích hoạt exception filter. Ngay khi gặp một exception chưa được bắt, phần còn lại của vòng đời bị bỏ qua và request đi thẳng tới filter. Các exception được throw từ [middleware](/middleware#error-handling) cũng được lớp xử lý exception xử lý, nhưng chỉ các exception filter **global** mới áp dụng, vì middleware chạy trước khi một route handler được chọn.

#### Tóm tắt

Nhìn chung, vòng đời request trông như sau:

1. Request đi vào
2. Middleware
   - 2.1. Middleware gắn global
   - 2.2. Middleware gắn với module
3. Guard
   - 3.1 Global guard
   - 3.2 Controller guard
   - 3.3 Route guard
4. Interceptor (trước controller)
   - 4.1 Global interceptor
   - 4.2 Controller interceptor
   - 4.3 Route interceptor
5. Pipe
   - 5.1 Global pipe
   - 5.2 Controller pipe
   - 5.3 Route pipe
   - 5.4 Route parameter pipe
6. Controller (method handler)
7. Service (nếu có)
8. Interceptor (sau request)
   - 8.1 Route interceptor
   - 8.2 Controller interceptor
   - 8.3 Global interceptor
9. Exception filter
   - 9.1 Route filter
   - 9.2 Controller filter
   - 9.3 Global filter
10. Response của server
