#### Với CQRS

Nếu ứng dụng của bạn theo [recipe CQRS](/recipes/cqrs), command handler sẽ publish event, còn event handler và saga phản ứng với chúng. Chúng phản ứng trong bộ nhớ: một event được publish ngay trước khi process dừng sẽ không bao giờ tới được chúng, và một saga đang chờ event thứ hai sẽ quên event đầu tiên khi restart. Entry point `@nestjs/workflows/cqrs` cho phép chính các event khởi động và gửi signal cho workflow, một cách bền vững, trong khi code của bạn vẫn tiếp tục thực thi command và publish event. Nó hoạt động với `@nestjs/cqrs` 11 trở lên, được đăng ký bằng `CqrsModule.forRoot()` như trong recipe.

##### Map event sang workflow

Ở đây quy trình giao hàng bắt đầu khi đơn hàng được đặt và thức dậy khi đơn vị vận chuyển báo việc giao hàng, như trước, nhưng các lời gọi workflow client đã biến mất khỏi code ứng dụng. Import `WorkflowsCqrsModule` cạnh `CqrsModule` và `WorkflowsModule`:

[[CODE:51]]

Sau đó map các event trên class workflow. `@StartOn()` khởi động workflow khi một event được publish, và `@SignalOn()` gửi một trong các signal của nó:

[[CODE:52]]

`id` của `@StartOn()` là bắt buộc. Nó suy ra instance id từ business key, như `start()` làm, nên một event được publish hai lần sẽ tìm thấy instance mà lần đầu đã khởi động. Nó cũng nhận `priority`, `concurrencyKey` và `rateLimitKey` của `start()`, mỗi cái dưới dạng một giá trị hoặc một hàm nhận event: ở đây, đơn hàng hỏa tốc đi trước, như trước. `id` của `@SignalOn()` không bắt buộc, và trở thành `id` của signal: một event giao hàng được publish lại, chẳng hạn do webhook của đơn vị vận chuyển được retry, sẽ không lưu signal thứ hai. `input` mặc định là chính event, và `payload` của signal cũng vậy. TypeScript kiểm tra input so với `run()` và payload so với type của signal. Các event là những class thuần, như `OrderPlacedEvent` với tham số constructor `readonly order: Order`.

Command handler lưu đơn hàng và publish event trong một transaction:

[[CODE:53]]

Tham số thứ hai của `publish()` và `publishAll()` là dispatcher context của CQRS. `WorkflowsCqrsModule` đọc thuộc tính `transaction` của nó và truyền cho `start()` và `signal()`, nên instance được tạo qua transaction của bạn, y như với tùy chọn `transaction`. Với TypeORM, dispatcher context mang `EntityManager` mà `dataSource.transaction()` đưa cho callback của nó, dưới cùng thuộc tính `transaction`. `publish()` resolve khi các workflow đã được khởi động và gửi signal, và chỉ khi đó event mới tới được event handler và saga của bạn. Các event không được workflow nào map sẽ đi thẳng qua, không thay đổi. Các controller thực thi command: `POST /orders` thực thi `PlaceOrderCommand`, và webhook của đơn vị vận chuyển thực thi `MarkDeliveredCommand`, có `MarkDeliveredHandler` làm điều tương tự cho việc giao hàng: nó cập nhật trạng thái đơn hàng và publish `OrderDeliveredEvent` trong một transaction, nên trạng thái và signal cùng commit.

Module bọc bất kỳ publisher nào mà event bus đang có, nên một publisher bạn đặt bằng tùy chọn `eventPublisher` của `CqrsModule.forRoot()` (chẳng hạn một message broker) vẫn nhận mọi event, sau các workflow. Thay thế `EventBus.publisher` sau khi khởi động sẽ bỏ qua các workflow, nên việc khởi động sẽ thất bại nếu có gì đó làm vậy. Nó cũng thất bại khi một workflow map event nhưng `WorkflowsCqrsModule` không được import, khi một class map cùng một event hai lần, hoặc khi `@StartOn()` đưa key cho một workflow không có giới hạn theo key. Khi hai phiên bản của một workflow được đăng ký, `@StartOn()` của phiên bản cao nhất quyết định cái gì được khởi động, và một signal tới được các instance đang chờ của mọi phiên bản, được gửi một lần, nên các khai báo `@SignalOn()` của chúng phải thống nhất về payload và `id`: `publish()` sẽ reject khi chúng không thống nhất.

Các mapping nằm trên class workflow, nên mọi process publish các event đã được map đều đăng ký chúng, kể cả một process không chạy workflow nào, chẳng hạn một API chỉ đặt đơn hàng. Hãy đăng ký các class và store ở đó như thường lệ, và truyền `worker: false` cho `WorkflowsModule.forRoot()`: process này khởi động và gửi signal cho workflow, còn các process worker thực thi chúng. Một process import `WorkflowsCqrsModule` nhưng không đăng ký workflow nào map event sẽ không khởi động và không gửi signal gì cả, và log một cảnh báo lúc khởi động nói rõ điều đó.

##### Thực thi command từ step

Một step có thể thực thi command. Hãy truyền idempotency key của step kèm theo command, và để handler chuyển nó cho hệ thống mà nó gọi:

[[CODE:54]]

`ChargePaymentHandler` gọi `PaymentsService.charge()` với key, nên một step được retry không bao giờ trừ tiền hai lần, và kết quả của command được ghi journal như kết quả của mọi step. Một step cũng có thể publish event và gửi signal. Nó chạy ít nhất một lần, nên một event được publish từ một step có thể được publish lại. Một lần khởi động đã được map sẽ tìm thấy instance của nó, và một `start()` không có `id` trong một step cũng vậy: nó nhận một id suy ra từ `idempotencyKey` của step, tên workflow và vị trí của nó trong số các lần khởi động workflow đó của step, và một lần lặp lại sẽ trả về instance như lúc được khởi động lần đầu, kể cả input. Một signal được gửi từ bên trong một step, trực tiếp hoặc qua một event đã được map, chỉ được lưu một lần: không có `id` riêng, nó nhận một id suy ra từ `idempotencyKey` của step và vị trí của nó trong số các signal cùng tên và key của step. Hãy gửi chúng theo một thứ tự cố định. Một step gửi đồng thời nhiều signal cùng tên và key nên cho mỗi signal một `id` riêng.

##### Mỗi cách publish đảm bảo điều gì

Mức đảm bảo phụ thuộc vào cách, và thời điểm, event được publish:

| Event được publish thế nào | Việc khởi động hoặc gửi signal cho workflow | Nếu process chết hoặc một thao tác ghi thất bại |
| --- | --- | --- |
| Trong transaction của bạn, với transaction trong dispatcher context | Commit cùng các thao tác ghi của bạn, hoặc không commit gì cả | Không có gì bị làm dở dang. Một lần khởi động hoặc gửi signal thất bại sẽ reject `publish()`, và transaction của bạn rollback |
| Các event của một aggregate, từ `commit()` với transaction trong dispatcher context (`@nestjs/cqrs` 12.1 trở lên), hoặc với `publishAll()` trong transaction của bạn, như bên dưới | Commit cùng các thao tác ghi của bạn, hoặc không commit gì cả | Như trên: một lần khởi động hoặc gửi signal thất bại sẽ reject `commit()` hoặc `publishAll()`, và transaction của bạn rollback |
| Sau khi transaction của bạn commit | Được ghi trước khi `publish()` resolve | Một lần crash giữa lúc commit và lúc publish sẽ làm mất nó. Hãy publish lại từ một job đối soát: `id` của lần khởi động giúp việc đó an toàn, và id của signal cũng vậy, nếu `@SignalOn()` có đặt |
| Từ `commit()` không có transaction, của một aggregate được merge với `EventPublisher` | Được ghi bên ngoài transaction của bạn, ở chế độ nền trừ khi bạn await `commit()` (12.1 trở lên) | Mất khi crash nếu không có gì chờ nó, và bị bỏ lại khi transaction của bạn rollback. Các lỗi được đưa tới `UnhandledExceptionBus` và log, và module log một cảnh báo mỗi event class một lần |
| Từ `commit()` không có transaction, của một aggregate `@Publishable()` | Được ghi bên ngoài transaction của bạn, ở chế độ nền trừ khi bạn await `commit()` (12.1 trở lên) | Mất khi crash nếu không có gì chờ nó, và bị bỏ lại khi transaction của bạn rollback. Nếu không await, một lỗi là một unhandled promise rejection, mặc định sẽ làm dừng Node.js. Không có gì phân biệt nó với một `publish()` thông thường, nên không có cảnh báo |
| Từ một step của workflow | Một lần, bất kể step chạy bao nhiêu lần | Một step được retry không khởi động gì mới, và không lưu signal thứ hai |

Một aggregate được merge bằng `EventPublisher.mergeObjectContext()` hoặc `mergeClassContext()`, hoặc được gắn `@Publishable()`, publish các event của nó từ `commit()`. Với `@nestjs/cqrs` 12.1 trở lên, `commit()` nhận một dispatcher context, giống như `publish()`, và trả về những gì event bus trả về. Hãy truyền cho nó transaction của bạn và await nó trong transaction của command handler: khi đó các event của aggregate sẽ khởi động và gửi signal cho workflow trong transaction đó, và `commit()` reject khi một lần khởi động hoặc gửi signal thất bại, làm transaction rollback:

[[CODE:55]]

`commit()` xóa các event của aggregate khi nó giao chúng đi, trước khi các workflow được ghi, nên sau một lần thất bại, hãy chạy lại command với một aggregate vừa được load lại.

Không có dispatcher context, `commit()` publish bên ngoài transaction của bạn: các workflow vẫn khởi động, nhưng một lần rollback sẽ bỏ lại chúng, và một lần crash trước khi chúng được ghi sẽ làm mất chúng. Đừng để nó publish các event khởi động hoặc gửi signal cho workflow. Với `@nestjs/cqrs` 12.0 trở về trước, `commit()` không nhận context và không trả về gì để chờ, nên hãy tự publish các event của aggregate, trong transaction của command handler, rồi xóa chúng:

[[CODE:56]]

Module sẽ báo cho bạn khi một event đã được map tới từ `commit()` của một aggregate đã merge mà không có transaction: ở lần đầu tiên, nó log một cảnh báo nêu tên event class. Các event của một aggregate `@Publishable()` tới mà không có dispatcher context nào, giống như một lời gọi `publish()` thông thường, nên chúng không nhận cảnh báo.

Event handler và saga của bạn vẫn nhận mọi event, trong bộ nhớ, sau các workflow. Bên trong một transaction, chúng chạy trước khi transaction commit, như chúng vẫn luôn làm, nên chúng có thể phản ứng với một event mà sau đó transaction của nó lại rollback. Một saga biến một event thành một command có thể giữ nguyên là saga. Một saga ghi nhớ event, chẳng hạn một saga chờ thanh toán sau khi đặt đơn và bỏ cuộc sau một giờ, thực chất là một workflow trá hình: hãy khởi động workflow từ event đầu tiên, map các event còn lại sang signal, và để `waitForSignal()` với một `timeout` lo việc chờ đợi, một cách bền vững.

#### Chuẩn bị cho production

##### Giữ journal ngắn gọn

Mỗi lần thực thi đều load toàn bộ journal của instance và replay `run()` từ đầu. Một quy trình có số step cố định sẽ giữ journal nhỏ, nhưng một vòng lặp có một step hoặc một sleep mỗi vòng sẽ thêm entry chừng nào nó còn chạy, và mỗi lần thực thi lại chậm hơn. Module cảnh báo khi một journal đạt 1.000 entry hoặc 1 MB: mỗi instance một lần, khi nó vượt ngưỡng, trong log và dưới dạng event `journal-large`. Khi nó chứa 10.000 entry hoặc 10 MB, instance thất bại trước khi ghi thêm entry nào: các compensation của nó chạy, chúng vẫn có thể ghi entry của mình, và nó kết thúc ở trạng thái `failed` với một `WorkflowJournalLimitError`. Tùy chọn `journal` của module thay đổi cả hai ngưỡng. Hãy định cỡ chúng theo workflow thông thường dài nhất của bạn với dư địa thoải mái, và đặt một giới hạn thành `Infinity` để tắt nó:

[[CODE:57]]

Một quy trình kéo dài mãi mãi, chẳng hạn một gói đăng ký cát vệ sinh hàng tháng, sẽ tiếp tục trong một instance mới thay vào đó. Sau một năm giao hàng, step cuối cùng của nó khởi động instance cho năm tiếp theo, và instance hiện tại hoàn tất:

[[CODE:58]]

Step khởi động instance tiếp theo một lần: một step được retry sẽ tìm thấy instance mà nó đã khởi động. Instance mới có journal mới và id riêng, nên năm đã kết thúc vẫn đọc được cho tới khi chính sách lưu trữ dọn dẹp nó. Tiếp tục dưới cùng id sẽ đòi hỏi mọi store phải thay thế journal tại chỗ, dưới lease của worker; một id mới không đòi hỏi gì mới từ store. Khi mỗi vòng độc lập với nhau, một lịch chạy còn đơn giản hơn: nó khởi động mỗi lần chạy một instance, mỗi instance có journal riêng, như [Chạy workflow theo lịch](/reliability/workflows#run-workflows-on-a-schedule) trình bày.

##### Mã hóa những gì workflow lưu trữ

Store giữ những gì workflow của bạn xử lý: đơn hàng, các lần trừ tiền, việc giao hàng. Để những thứ đó không đọc được với bất kỳ ai đọc database hoặc các bản backup của nó, hãy cho module một **payload codec**. `AesGcmPayloadCodec` mã hóa bằng AES-256-GCM, với các khóa từ secret manager của bạn. Tạo nó trong factory của module, factory này chạy lúc khởi động:

[[CODE:59]]

Một khóa là 32 byte ngẫu nhiên ở dạng base64 (`openssl rand -base64 32`), dưới một id do bạn chọn. Một khóa bị thiếu (một biến môi trường chưa đặt), không phải base64 hoặc không đủ 32 byte sẽ làm việc khởi động thất bại, kèm một lỗi nêu tên nó.

- **Những gì nó mã hóa**: mọi thứ chứa dữ liệu của bạn. Input và output, kết quả step và checkpoint, payload của signal, custom status, lý do hủy, input của lịch chạy, và message cùng stack của lỗi. Mỗi payload được mã hóa dưới một khóa được suy ra riêng cho nó, với vị trí lưu trữ của nó làm dữ liệu xác thực, nên một payload bị thay đổi, hoặc bị chuyển sang instance hay field khác, sẽ không giải mã được thay vì bị đọc. Các payload từ 1 KiB trở lên được nén trước. Nếu payload trộn lẫn secret với dữ liệu do kẻ tấn công chọn, và kẻ tấn công có thể thấy kích thước được lưu, hãy tắt việc nén bằng `compress: false`.
- **Những gì vẫn đọc được**, vì store cần so khớp, lọc, sắp xếp hoặc đếm dựa trên chúng: id, tên và phiên bản workflow, trạng thái, tên và key của signal, key concurrency và rate-limit, độ ưu tiên, liên kết tới cha và lịch chạy, tên entry của journal, và mọi thời điểm. Lỗi giữ nguyên tên của chúng, chẳng hạn `StepFailedError`. Vì vậy hãy chọn id và key không nói lên điều gì nhạy cảm: `order-71e1973d`, chứ không phải một địa chỉ email. Ở đây concurrency key là id khách hàng, đọc được trong `concurrency_key`.
- **Dạng lưu trữ**: `$wf1:aes-256-gcm:2026-09.` theo sau là ciphertext, một chuỗi trong cùng các cột JSON, nên store không cần thay đổi gì.

**Xoay vòng khóa.** Thêm một khóa, và đặt nó làm `current`. Một payload được giải mã bằng khóa đã mã hóa nó, và mọi thứ được ghi từ đó trở đi dùng khóa hiện tại. Không có gì được mã hóa lại hàng loạt: payload được ghi lại khi các instance tiến triển, và payload cũ biến mất theo các lần dọn dẹp. Vì vậy hãy giữ một khóa trong danh sách chừng nào mọi thứ nó đã mã hóa vẫn có thể được đọc: các instance chưa kết thúc, các signal chưa bị dọn dẹp, và các lịch chạy được lưu dưới khóa đó. Input của một lịch chạy được khai báo sẽ được lưu lại dưới khóa hiện tại lúc khởi động và mỗi phút, nhưng input của một lịch chạy được upsert thì chỉ được lưu lại ở lần `upsert()` tiếp theo: `pause()` và `resume()` giữ nguyên nó như đã lưu.

[[CODE:60]]

Một instance có payload cần một khóa không có trong danh sách sẽ không đọc được: `getStatus()` throw một lỗi nêu tên khóa, `list()` hiển thị instance mà không có payload, và các worker để yên nó cho tới khi khóa quay lại, rồi mới chạy nó.

Thêm một codec không làm hỏng instance nào đang chạy: các payload được lưu trước đó được đọc nguyên trạng, và các thao tác ghi mới được mã hóa. Đó cũng là giới hạn của việc bảo vệ. Ai đó có quyền ghi vào database có thể thay một payload đã mã hóa bằng một payload thuần, và khiến nó được đọc: codec bảo vệ những gì nó đã mã hóa khỏi việc bị đọc và bị sửa, chứ không bảo vệ database khỏi những người có quyền ghi vào nó.

Một codec của riêng bạn implement `WorkflowPayloadCodec`: một `id`, được lưu cùng mỗi payload, và `encode()` cùng `decode()`, nhận giá trị và vị trí lưu trữ của nó. Truyền class của nó cho `codec` để Nest tạo nó, với các dependency từ các global module, chẳng hạn một KMS client. Để thay một codec, hãy liệt kê codec mới trước và codec cũ sau nó: codec đầu tiên mã hóa, và mỗi payload được giải mã bằng codec có id mà nó mang.

##### Checklist cho production

- Truyền `idempotencyKey` cho mọi side effect, kể cả compensation. Step chạy ít nhất một lần.
- Cho signal một `id` khi bên gửi của nó có thể chạy hai lần, chẳng hạn một webhook được bên gửi retry hoặc một message consumer. Signal được gửi từ một step tự động có id.
- Gọi `enableShutdownHooks()`, và giữ `shutdownTimeout` dưới grace period của platform (mặc định 30 giây trên Kubernetes).
- Chọn `leaseDuration` một cách có cân nhắc. Đó là khoảng thời gian các instance của một process bị crash phải chờ trước khi process khác tiếp quản, và một process có event loop bị treo lâu hơn mức đó sẽ mất các instance của nó. Việc hết hạn lease so sánh các timestamp do các host khác nhau ghi, nên hãy giữ đồng hồ của chúng được đồng bộ (NTP) và `leaseDuration` lớn hơn hẳn mọi độ lệch giữa chúng.
- Đăng ký một store trên database của bạn: `PostgresWorkflowStore`, `MySqlWorkflowStore`, hoặc một store của riêng bạn. Trong bộ nhớ, hoặc trong một file trên ổ đĩa của container, trạng thái chết theo instance: store trong bộ nhớ mặc định mất mọi đơn hàng đang chạy khi restart, và việc khởi động sẽ từ chối nó trong production. Chạy contract suite trên store của riêng bạn trong CI, trên database của nó, với `concurrent: true`.
- Áp dụng migration của store trước khi một phiên bản mới khởi động, bằng `npx @nestjs/workflows migrate` hoặc công cụ migration của bạn, và kiểm tra chúng trong CI bằng `npx @nestjs/workflows status`. Với `NODE_ENV=production`, store không migrate lúc khởi động: một schema chậm phiên bản sẽ làm việc khởi động thất bại.
- Chạy bao nhiêu worker tùy thích, trên bao nhiêu host tùy thích. Định cỡ connection pool cho chúng: mỗi instance đang chạy gia hạn lease và ghi journal qua pool, và mỗi lần poll giữ một kết nối cho lần claim của nó.
- Khởi động workflow trong transaction ghi các dòng nghiệp vụ của chúng (`transaction: tx`, hoặc `EntityManager` với TypeORM), để một lần crash giữa hai bước không thể để lại một đơn hàng không có gì xử lý. Hãy truyền transaction, không bao giờ truyền root database. Với CQRS, hãy publish các event bên trong transaction đó, với transaction trong dispatcher context.
- Giữ các transaction gửi signal ngắn gọn: signal và các lần tạm dừng đăng ký wait xếp hàng phía sau chúng. Trên PostgreSQL, giữ chúng ở READ COMMITTED, và isolation mặc định của database cũng vậy: store từ chối một level chặt hơn. Trên MySQL, giữ chúng ở REPEATABLE READ hoặc READ COMMITTED, và chạy lại một transaction khi nó thất bại do deadlock (lỗi 1213).
- Xác minh chữ ký của webhook, và chỉ trả về `2xx` sau khi transaction chứa signal đã commit.
- Cảnh báo khi có instance cần người xử lý. `compensation_failed` nghĩa là một lần hoàn tác đã bỏ cuộc giữa chừng, và một instance `failed` với `WorkflowNonDeterminismError` nghĩa là một lần deploy đã làm hỏng replay. `WorkflowClient.list()` tìm ra chúng, và [Ý nghĩa của từng trạng thái](/reliability/workflows#what-each-status-means) cho biết cần làm gì với từng cái: `retry()` khi đã sửa nguyên nhân, hoặc `delete()`. Cho log và metric, hãy subscribe `WorkflowEvents.events$`, hoặc các diagnostics channel `nestjs:workflows:*` mà các công cụ tracing đọc được mà không cần Nest; [Event](/reliability/workflows#events) map chúng lên một trace.
- Đánh dấu điểm không thể quay lại bằng `ctx.commit()`. Trước nó, mọi lần thất bại và hủy đều hoàn tác các step đã hoàn tất.
- Dọn dẹp các instance đã kết thúc mỗi đêm bằng `purge()`, trên một instance của ứng dụng, như [Dọn dẹp các instance đã kết thúc](/reliability/workflows#purge-finished-instances) trình bày. Giữ `olderThan` của nó dài hơn khoảng thời gian gửi lại của mọi bên gửi: `id` của một signal chỉ khử trùng lặp chừng nào signal còn được lưu.
- Giữ journal ngắn gọn: giới hạn các vòng lặp, và tiếp tục một vòng lặp không bao giờ kết thúc trong một instance mới ([Giữ journal ngắn gọn](/reliability/workflows#keep-journals-short)). Cho một quy trình phải bỏ cuộc ở một thời điểm nào đó một run timeout ([Timeout cho toàn bộ workflow](/reliability/workflows#time-out-the-whole-workflow)).
- Định cỡ giới hạn concurrency và rate theo những gì các step gọi tới, và deploy thay đổi về chúng tới mọi process: mỗi process áp dụng các giới hạn của code mà nó chạy. Khi một số instance đã có độ ưu tiên, hãy cho các instance còn lại độ ưu tiên nữa, vì các instance không có độ ưu tiên sẽ đi trước.
- Deploy một lịch chạy được khai báo tới mọi process đăng ký workflow của nó: chỉ các worker có code khai báo nó mới khởi động các lần chạy của nó. Một lịch chạy bị một lần deploy loại bỏ, hoặc bị xóa workflow, vẫn tiếp tục khởi động trên các process của code cũ, và biến mất khoảng năm phút sau khi process cuối cùng trong số đó dừng. Đặt `missed` cho những công việc không được bỏ qua khi không có worker nào hoạt động vào thời điểm của nó. Nếu các process của code khác dùng chung database, đừng để một lịch chạy không có worker nào có code khai báo nó trong năm phút: chúng sẽ xóa nó, và nó bắt đầu lại khi có một worker như vậy khởi động.
- Mã hóa những gì store lưu giữ bằng một codec, với các khóa từ secret manager của bạn ([Mã hóa những gì workflow lưu trữ](/reliability/workflows#encrypt-what-workflows-store)). Giữ một khóa cũ trong danh sách chừng nào mọi thứ nó đã mã hóa còn có thể được đọc, và chọn id và key không nói lên điều gì nhạy cảm: chúng vẫn đọc được.
