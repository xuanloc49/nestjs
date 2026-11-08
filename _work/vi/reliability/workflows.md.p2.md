#### Khởi động workflow

##### Khởi động nó cùng đơn hàng

Một đơn hàng và việc xử lý giao hàng của nó đi liền với nhau: một đơn hàng không có gì xử lý cũng tệ như một quy trình giao hàng trừ tiền cho một đơn hàng chưa bao giờ được lưu. Vì vậy `OrdersService` lưu đơn hàng và khởi động workflow trong một Drizzle transaction. `WorkflowClient` khởi động các instance; hãy truyền cho nó `tx` của transaction:

[[CODE:15]]

Với `transaction`, store tạo instance qua transaction mà ORM của bạn đã đưa cho callback, nên nó commit cùng đơn hàng, hoặc rollback cùng đơn hàng nếu có gì đó phía sau trong callback thất bại. Worker chỉ thấy các instance đã commit: nó nhận instance này ở lần poll tiếp theo sau khi commit. Hãy truyền transaction, không phải database, thứ mà store sẽ từ chối: `start()` không có tùy chọn này sẽ ghi một cách độc lập, chính là việc dual write mà tùy chọn này loại bỏ. Với TypeORM, hãy truyền `EntityManager` của transaction, và với Prisma, là transaction client, như [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database) trình bày.

Instance id lấy từ id đơn hàng, điều này khiến `start()` trở nên idempotent. Khởi động cùng id với cùng input sẽ trả về instance đã có với `created: false`, còn một input khác sẽ throw `WorkflowIdConflictError`. Một job đối soát có thể gọi lại nó cho một đơn hàng mà không trừ tiền hai lần.

##### Báo cáo trạng thái

Controller đặt đơn hàng và báo cáo việc xử lý giao hàng đang ở đâu:

[[CODE:16]]

`getStatus()` trả về instance: `status`, `wakeAt`, các signal mà nó `waits`, `error` hoặc `output` của nó, và, với tùy chọn `journal`, mọi step. Các trạng thái là `pending`, `running`, `suspended`, `compensating`, `completed`, `failed`, `cancelled` và `compensation_failed`; [Ý nghĩa của từng trạng thái](/reliability/workflows#what-each-status-means) cho biết mỗi trạng thái nghĩa là gì và cần làm gì với nó. Endpoint map instance sang một view nhỏ. Đừng trả instance thô cho khách hàng, vì nó chứa input và chi tiết lease.

`stage` đến từ workflow. `ctx.setStatus()` đặt **custom status** của instance, một giá trị JSON tối đa 16 KiB mà `getStatus()` và `list()` trả về dưới tên `customStatus`: ở đây, là một từ mô tả đơn hàng đang ở đâu. Hãy đặt nó trong `run()` khi đơn hàng tiến triển, và đặt thành `delivered` khi đơn vị vận chuyển đã giao hàng (trong [Ngủ một tuần, rồi nhờ đánh giá](/reliability/workflows#sleep-for-a-week-then-ask-for-a-review)):

[[CODE:17]]

Status không được ghi journal. Mỗi lần thực thi đều replay `run()`, và cùng với nó là các lời gọi `setStatus()`, nên mỗi lần thực thi lại đặt status trên đường nó đi qua, và một status được đặt trong vòng lặp không làm journal phình ra. Workflow không bao giờ đọc lại nó, nên không có quyết định nào của workflow phụ thuộc vào nó. Nó được ghi cùng lần ghi tiếp theo của instance: khi step tiếp theo bắt đầu, khi instance đỗ lại, hoặc khi nó kết thúc. Vì vậy endpoint hiển thị `paid` trong khi `reserve-stock` chờ retry, và `awaiting-delivery` khi instance đỗ lại chờ đơn vị vận chuyển. Một status mà workflow không còn thay đổi sẽ được giữ nguyên, chẳng hạn `awaiting-delivery` trên một đơn hàng đã bị hủy: `status` cho biết điều gì đã xảy ra. Một giá trị không phải JSON, hoặc chiếm hơn 16 KiB dưới dạng JSON, sẽ làm instance thất bại với một `TypeError`, còn `undefined` sẽ xóa status. Mỗi thay đổi được ghi sẽ được phát ra dưới dạng event `custom-status`.

#### Chờ signal và timer

##### Chờ webhook giao hàng

Tiếp theo, workflow chờ đơn vị vận chuyển. Webhook và workflow dùng chung một signal: một tên và type của payload, định nghĩa một lần, để không bên nào gõ sai tên hay gửi sai cấu trúc:

[[CODE:18]]

Thêm đoạn này vào `run()`, sau `reserve-stock`:

[[CODE:19]]

`waitForSignal()` ghi lại lần chờ và đỗ instance lại: trạng thái của nó chuyển thành `suspended` và `wakeAt` là hạn chót. Không có bộ nhớ, timer hay worker nào bị giữ trong 3 ngày đó. Nó resolve với payload của signal, có type `CarrierEvent`, hoặc với `null` khi hết thời gian timeout. Khi đó `ctx.fail()` làm instance thất bại, và các compensation chạy theo thứ tự ngược: hàng trong kho được giải phóng, rồi tiền được hoàn lại. Tùy chọn `match` lọc thêm các signal theo payload, chẳng hạn `match: (event) => event.trackingNumber !== ''`; nó chạy lại ở mỗi lần replay, nên phải là một pure function của payload.

Webhook đánh dấu đơn hàng đã được giao và gửi signal. Cả hai diễn ra trong một method mới `OrdersService.markDelivered()`, trong một transaction, nên trạng thái đơn hàng và signal cùng commit. Hãy thêm nó, cùng với import của signal:

[[CODE:20]]

Controller xác minh callback và chuyển nó đi:

[[CODE:21]]

`signal()` lưu signal với một `key` dùng để liên kết và đánh thức các instance đang chờ signal và key đó. Key được so khớp chính xác, nên id đơn hàng giúp việc giao hàng của đơn này không đánh thức đơn khác, và một lần chờ không có key chỉ nhận các signal được gửi không kèm key. Signal là bền vững. Một webhook tới trước khi workflow chạm tới lần chờ vẫn được tính, và mỗi signal được tiêu thụ tối đa một lần cho mỗi instance, nên các lần retry của đơn vị vận chuyển là vô hại. Tuy vậy mỗi lần retry vẫn lưu một signal, trừ khi bạn truyền một `id`, chẳng hạn mã vận đơn: một signal có cùng tên và `id` chỉ được lưu một lần, và một lần lặp lại sẽ trả về `signalId` của signal đầu tiên với `created: false`. Một lần giao hàng được ghi nhận sau hạn chót sẽ thua timeout, kể cả khi không có worker nào đang chạy lúc hạn chót trôi qua.

Controller chỉ trả lời `200` sau khi transaction đã commit. Một lần giao hàng cho đơn hàng mà store không biết sẽ rollback với `404`, không để lại signal nào, và nếu database lỗi, đơn vị vận chuyển nhận một lỗi và gửi lại webhook. Các signal được gửi trong một transaction xếp hàng chờ nhau cho tới khi transaction kết thúc, nên hãy giữ các transaction như vậy ngắn gọn. Trên PostgreSQL, transaction phải dùng isolation mặc định READ COMMITTED; store từ chối một level chặt hơn, vì nó có thể bỏ lỡ một lần chờ được đăng ký trong lúc transaction chạy. Trên MySQL, REPEATABLE READ mặc định cũng dùng được.

##### Chờ thứ nào tới trước

Đơn vị vận chuyển không phải lúc nào cũng giao được hàng. Khi không giao được, họ mang kiện hàng về kho và báo `shipment.returned`. Khai báo signal thứ hai, cạnh signal đầu tiên:

[[CODE:22]]

Webhook gửi nó giống như gửi việc giao hàng. Một method mới `OrdersService.markReturned()` đặt trạng thái đơn hàng thành `returned` và gửi signal, trong một transaction, giống `markDelivered()`:

[[CODE:23]]

Giờ workflow chờ việc giao hàng, việc trả hàng hoặc 3 ngày, thứ nào tới trước. Thay lời gọi `waitForSignal()` bằng `ctx.waitForAny()`:

[[CODE:24]]

`ctx.signalWait()` và `ctx.timer()` chỉ mô tả một điều kiện, và `waitForAny()` chờ chúng cùng nhau. Nó đỗ instance lại một lần, với mọi signal mà nó chờ và hạn chót sớm nhất, và resolve với `key` của điều kiện xảy ra trước cùng `value` của nó: payload của một signal, hoặc `null` cho một timer. Kiểm tra `key` sẽ thu hẹp type của `value`, nên sau hai lần kiểm tra `delivery` là một `CarrierEvent`. Một kiện hàng bị trả về làm instance thất bại, và các compensation giải phóng hàng trong kho, vốn đã quay về kho, và hoàn tiền. `waitingFor` của endpoint trạng thái liệt kê cả hai signal trong khi instance chờ.

Kết quả được ghi journal thành một entry dưới tên của lần chờ, nên mọi lần thực thi sau đều nhận cùng bên thắng. Khi nhiều điều kiện cùng sẵn sàng một lúc, signal được ghi nhận trước sẽ thắng, bất kể nó khớp với điều kiện nào. Một signal được gửi sau hạn chót của một timer không được tính, giống như `timeout` của `waitForSignal()`, và timer được tính từ lúc lần chờ được chạm tới lần đầu. Chỉ signal thắng mới được lấy: một lần trả hàng được báo sau việc giao hàng sẽ ở lại cho một lần chờ sau của cùng instance. Để chờ tất cả trong nhiều signal, hãy await nhiều lời gọi `waitForSignal()` với `Promise.all()`: mỗi lời gọi được ghi journal riêng, và instance đỗ lại một lần cho tất cả. Một child workflow cũng có thể là một điều kiện, như [Khởi động child workflow](/reliability/workflows#start-child-workflows) trình bày.

##### Ngủ một tuần, rồi nhờ đánh giá

Kết thúc `run()` bằng điểm không thể quay lại, một timer bền vững và step cuối cùng:

[[CODE:25]]

`ctx.sleep()` lưu một thời điểm đánh thức và đỗ instance lại, giống như lần chờ. Sau 7 ngày, bất kỳ worker nào cũng sẽ tiếp tục nó: không bao giờ sớm hơn, và thường trong vòng một khoảng poll tính từ hạn chót. Khi tiếp tục, `run()` replay từ đầu: `charge-payment` và `await-delivery` trả về các giá trị đã ghi journal, nên `charge` và `delivery` vẫn nằm trong phạm vi một tuần sau đó. Một delayed job không thể cho bạn sự tiếp nối này. Để ngủ tới một thời điểm cụ thể, hãy truyền một object có `until`, là một `Date` hoặc epoch tính bằng mili giây, được tính từ các giá trị đã ghi journal như `ctx.now()`.

`ctx.commit()` đánh dấu điểm không thể quay lại. Khi kiện hàng đã được giao, hoàn tiền sẽ là sai, bất kể điều gì xảy ra tiếp theo. `commit()` loại bỏ các compensation đã đăng ký cho tới thời điểm đó. Nếu sau đó email đánh giá thất bại vĩnh viễn, instance kết thúc ở trạng thái `failed` với lỗi của step, và không có gì được hoàn tiền hay giải phóng. Một lần hủy sau điểm này cũng không hoàn tác gì cả. Chỉ các step sau `commit()` mới đăng ký các compensation còn có thể chạy. Điểm commit được ghi journal dưới tên của nó, nên nó replay như một step, và endpoint trạng thái liệt kê nó là `delivered`.

##### Timeout cho toàn bộ workflow

`timeout` của một lần chờ giới hạn một lần chờ, và `timeout` của một step giới hạn một lần thử. Để giới hạn toàn bộ một instance, hãy cho workflow một run timeout:

[[CODE:26]]

Hạn chót là thời điểm instance bắt đầu cộng với timeout, được lưu cùng instance dưới dạng `deadline` của nó, nên nó giữ nguyên qua các lần restart và deploy, và một instance đang đỗ sẽ thức dậy vì nó kể cả khi lần sleep hoặc wait của nó sẽ kết thúc muộn hơn. Khi hạn chót trôi qua, instance dừng ở lời gọi `ctx` tiếp theo (một step đang chạy sẽ hoàn tất trước), các compensation của nó chạy, và nó kết thúc ở trạng thái `failed` với một `WorkflowTimeoutError`. Compensation không bị giới hạn bởi hạn chót. Ở đây lần chờ bỏ cuộc sau 3 ngày và lần sleep mất 7 ngày, nên 30 ngày là một tấm lưới an toàn. `start()` cũng nhận tùy chọn `timeout`, ghi đè giá trị của decorator cho instance đó.

#### Hủy và vận hành workflow

##### Cho bộ phận chăm sóc khách hàng hủy đơn

Thêm một route `cancel()` vào `OrdersController`, và thêm `ConflictException` cùng `HttpCode` vào import từ `@nestjs/common`. `OrdersService.markCancelled()` đặt trạng thái của đơn hàng:

[[CODE:27]]

`cancel()` đặt một cờ. Một instance đang đỗ sẽ thức dậy ngay lập tức. Một instance đang chạy sẽ để step hiện tại hoàn tất và dừng ở lời gọi `ctx` tiếp theo. (Một instance đang chạy ở process khác sẽ nhận ra cờ này ở lần gia hạn lease tiếp theo, trong vòng một phần ba `leaseDuration`.) Dù theo cách nào, các compensation của các step đã hoàn tất cũng chạy theo thứ tự ngược, và instance kết thúc ở trạng thái `cancelled` với lý do làm error message. `cancel()` trả về instance kèm cờ `accepted`. Cờ này là `false` khi instance đã hoàn tất hoặc thất bại, khi nó đang bù trừ cho một lần thất bại, hoặc khi đã có yêu cầu cancel hoặc terminate trước đó. Lần cancel thứ hai không thay đổi gì, và lý do đầu tiên được giữ lại.

Khi đơn vị vận chuyển đã báo việc giao hàng, route trả lời `409`, vì bộ phận hỗ trợ nên khởi tạo một lần trả hàng thay vào đó. Workflow không dựa vào bước kiểm tra đó. Một lần hủy tới nó sau `ctx.commit('delivered')` sẽ dừng việc nhờ đánh giá và không hoàn tiền gì cả. Một lần hủy mà nó thấy trước khi đã tiêu thụ event giao hàng vẫn hoàn tiền, vì nó chưa chạm tới điểm không thể quay lại.

##### Ý nghĩa của từng trạng thái

`status` của một instance cho biết nó đang làm gì, và liệu nó có cần bạn can thiệp không:

| Trạng thái | Ý nghĩa | Cần làm gì |
| --- | --- | --- |
| `pending` | Đã khởi động, và chưa được worker nào claim. Một instance cứ ở `pending` là đang chờ một slot concurrency hoặc chỗ trống trong một cửa sổ rate-limit, hoặc thuộc một phiên bản mà không worker nào đang chạy đăng ký | Không cần gì khi một giới hạn đang giữ nó. Nếu không, hãy deploy một worker với phiên bản đó, hoặc xóa instance |
| `running` | Một worker đang giữ lease và thực thi nó | Không cần gì. `cancel()` dừng nó ở lời gọi `ctx` tiếp theo, và `terminate()` thì dừng mà không bù trừ |
| `suspended` | Đang đỗ ở một lần sleep, wait hoặc backoff của retry, cho tới `wakeAt` hoặc một signal | Không cần gì. Một signal hoặc `cancel()` sẽ đánh thức nó |
| `compensating` | Đang hoàn tác các step đã hoàn tất sau một lần thất bại hoặc hủy | Không cần gì: nó sẽ kết thúc ở `failed`, `cancelled` hoặc `compensation_failed`. `terminate()` dừng việc hoàn tác |
| `completed` | Đã xong, với kết quả của `run()` làm `output` | Không cần gì, cho tới khi chính sách lưu trữ dọn dẹp nó |
| `cancelled` | Đã bị hủy, sau khi các compensation chạy, hoặc bị terminate mà không chạy chúng (`error.name` là `WorkflowTerminatedError`). `error.message` là lý do | Không cần gì, cho tới khi chính sách lưu trữ dọn dẹp nó |
| `failed` | Một step đã bỏ cuộc, `ctx.fail()` được gọi, run timeout đã trôi qua hoặc journal chạm giới hạn, và sau đó các compensation đã chạy. Hoặc một lỗi định nghĩa, chẳng hạn một lần deploy làm hỏng replay, đã làm nó thất bại mà không bù trừ | Nếu không có compensation nào chạy, hãy sửa nguyên nhân và retry nó. Nếu không thì nó đã xong: các step đã hoàn tất của nó đã được hoàn tác |
| `compensation_failed` | Một lần hoàn tác đã bỏ cuộc giữa chừng. `error` là lỗi gốc, với lỗi riêng của compensation nằm ở `error.compensation` | Sửa nguyên nhân, chẳng hạn một API kho bị down, và retry nó. Hoặc tự hoàn tất việc hoàn tác bằng tay và xóa instance |

##### Retry, xóa hoặc terminate

`WorkflowClient` có các hành động cho cột cuối cùng của bảng. Hãy gọi chúng từ một route chỉ dành cho nhân viên hoặc một script:

[[CODE:28]]

- **`retry()`** chạy lại một instance `failed` từ journal của nó: các step đã hoàn tất trả về kết quả của chúng, step đã bỏ cuộc được trả lại số lần thử, và các lần sleep và wait mà instance bỏ dở sẽ bắt đầu lại. Một lần deploy làm hỏng replay sẽ được retry khi code đã sửa chạy. Nó từ chối một instance mà các compensation đã chạy, vì tiếp tục sẽ xây dựng trên công việc đã bị hoàn tác: hãy khởi động một instance mới thay vào đó. Một instance đã quá run timeout cần một timeout mới, qua tùy chọn `timeout` (tính từ bây giờ), hoặc `false` để không có timeout. Một instance `compensation_failed` sẽ chạy lại các compensation chưa hoàn tất, mỗi cái được trả lại số lần thử, và kết thúc như lẽ ra nó đã kết thúc: `failed` hoặc `cancelled`.
- **`delete()`** xóa một instance đã kết thúc cùng journal của nó. Một instance chưa kết thúc cần tùy chọn `force`, và bị xóa mà không chạy các compensation của nó: hãy dùng nó cho một instance mà không worker nào còn chạy được nữa, chẳng hạn một instance thuộc phiên bản bạn không còn deploy.
- **`cancel()`**, như ở trên, dừng một instance vẫn đang chạy, và chạy các compensation của nó.
- **`terminate()`** dừng một instance mà không chạy các compensation của nó, cho một instance mà việc hoàn tác không được phép hoặc không thể chạy, chẳng hạn một đơn hàng mà bộ phận hỗ trợ đã hoàn tiền bằng tay. Một instance đang đỗ dừng ngay lập tức, một instance đang chạy dừng ở lời gọi `ctx` tiếp theo, và một instance đang bù trừ dừng sau compensation mà nó đang chạy. Nó kết thúc ở trạng thái `cancelled`, với một `WorkflowTerminatedError` có message là lý do (`Terminated.` nếu không có lý do). Nó cũng được chấp nhận sau một lần `cancel()`, và thay thế lần cancel đó, còn một lần `cancel()` sau nó sẽ bị từ chối. Các child của nó nhận `parentClose` của chúng, như với mọi lần kết thúc khác.

`retry()` và `delete()` throw một `WorkflowStateError`, có `status` là `409`, với một trạng thái mà chúng không có ý nghĩa, và khi một thay đổi khác trên instance chạy đua với chúng. Một lần retry được ghi journal thành `$retry:1`, `$retry:2` và cứ thế, kèm trạng thái và lỗi mà nó đã retry, và cả hai hành động đều được phát ra, dưới dạng `workflow-retried` và `workflow-deleted`.

##### Dọn dẹp các instance đã kết thúc

Các instance đã kết thúc vẫn ở lại, cùng journal của chúng, cho tới khi bạn dọn dẹp chúng. `purge()` xóa những instance đã kết thúc lâu hơn tùy chọn `olderThan` của nó, từng batch một, cùng các signal không còn instance nào nhận được. Một instance chỉ nhận các signal được gửi sau khi nó bắt đầu, nên khi mọi instance chưa kết thúc đều bắt đầu sau một signal, và signal đó cũ hơn `olderThan`, nó sẽ bị xóa; signal mới nhất luôn được giữ lại. Các instance `compensation_failed` chờ một người xử lý, nên chúng chỉ bị dọn dẹp khi bạn liệt kê chúng trong tùy chọn `status`. Hãy chạy nó mỗi đêm, trên một instance của ứng dụng, với `@Cron()` từ `@nestjs/schedule` và `@OnOneInstance()` từ [`@nestjs/locks`](/reliability/locks):

[[CODE:29]]

`purge()` resolve với số `instances` và `signals` mà nó đã xóa, và số cửa sổ rate-limit đã kết thúc (`rateLimits`). `id` của một signal giúp khử trùng lặp chừng nào signal còn được lưu, nên hãy giữ `olderThan` dài hơn khoảng thời gian gửi lại của mọi bên gửi, chẳng hạn các lần retry webhook của đơn vị vận chuyển.
