#### Giới hạn, child và công việc theo batch

##### Giới hạn số lượng chạy cùng lúc

Một worker chạy mọi instance tới hạn mà nó còn chỗ. Có ba tùy chọn quyết định cái gì được chạy, và theo thứ tự nào, trên mọi worker: một giới hạn concurrency, một rate limit và một độ ưu tiên. Quy trình giao hàng đặt hai tùy chọn đầu trong `@Workflow()`:

[[CODE:30]]

**Concurrency.** `concurrency` giới hạn số instance chạy cùng lúc: một `limit` cho cả workflow, hoặc một `limit` theo từng key với một hàm `key`, ở đây là id khách hàng. Một mảng nhận mỗi loại một cái. Một instance chỉ giữ slot trong khi một lần thực thi đang chạy nó, kể cả compensation, chứ không giữ khi nó đang sleep hay wait: một giới hạn bảo vệ những gì các step gọi tới, và một đơn hàng đỗ lại nhiều ngày không cản trở ai cả. Một process bị crash sẽ giải phóng slot của nó khi lease hết hạn. Các instance vượt quá giới hạn vẫn ở trạng thái tới hạn và chờ slot, instance quá hạn lâu nhất được ưu tiên, và một key đã đầy sẽ bị bỏ qua, nên một khách hàng bận rộn không bao giờ cản trở đơn hàng của khách hàng khác. Key được tính từ input khi instance khởi động, và tùy chọn `concurrencyKey` của `start()` cho phép đặt key khác, với workflow có giới hạn theo key.

**Rate limit.** `rateLimit` giới hạn số lần thực thi bắt đầu trong mỗi cửa sổ: `max` mỗi `duration` cho cả workflow, hoặc theo từng key với một hàm `key`, có thể ghi đè bằng tùy chọn `rateLimitKey` của `start()`. Mọi lần thực thi đều được tính, lần đầu tiên và mỗi lần tiếp tục sau một sleep, một signal, backoff của một lần retry hay một lần cancel, vì mỗi lần đều có thể gọi tới thứ mà giới hạn bảo vệ. Quy trình giao hàng gửi tối đa một request tới payment provider mỗi lần thực thi, nên điều này giới hạn số request của nó, và cả những lần thực thi không gửi request nào. Một cửa sổ mở ra với lần thực thi đầu tiên sau khi cửa sổ trước kết thúc, và cho phép `max` lần thực thi cho tới khi nó đóng lại, nên hai cửa sổ liền kề có thể cho phép gấp đôi `max` trong một `duration`. Chẳng hạn payment provider cho phép 20 request mỗi giây: hãy cho phép 10.

**Độ ưu tiên.** Tùy chọn `priority` của `start()` quyết định cái gì được claim trước: độ ưu tiên thấp nhất, rồi đến instance quá hạn lâu nhất. Đó là một số nguyên từ 1 tới 2.097.151, và các instance khởi động không có độ ưu tiên sẽ đi trước mọi instance có độ ưu tiên. Đơn hàng hỏa tốc đi trước:

[[CODE:31]]

Vì các instance không có độ ưu tiên đi trước, nên khi đơn hàng đã có độ ưu tiên, các công việc khác cần có độ ưu tiên để đi sau chúng: lịch chạy của batch hóa đơn cho nó giá trị 10, trong [Chạy workflow theo lịch](/reliability/workflows#run-workflows-on-a-schedule). Một instance giữ độ ưu tiên của nó cho mọi lần thực thi, và các child kế thừa độ ưu tiên của cha. Độ ưu tiên là tuyệt đối: một dòng đơn hàng hỏa tốc liên tục sẽ giữ chân các đơn tiêu chuẩn. `@StartOn()` nhận cùng tùy chọn này, như [Với CQRS](/reliability/workflows#with-cqrs) trình bày.

Các giới hạn lấy từ phiên bản cao nhất được đăng ký của workflow và áp dụng cho mọi phiên bản của nó, và mỗi process áp dụng các giới hạn của code mà nó chạy, nên hãy deploy thay đổi về giới hạn ở mọi nơi. Các lần claim không bao giờ cho phép nhiều hơn mức giới hạn cho phép, nhưng có thể cho phép ít hơn trong chốc lát: các worker poll cùng lúc có thể mất vài lần poll để lấp đầy một cửa sổ ngắn, và khi có cả concurrency key lẫn rate-limit key, một ứng viên bị một loại key bỏ qua sẽ chờ lần claim tiếp theo. Các lần claim cũng sắp xếp các instance tới hạn theo độ ưu tiên, điều mà index trên `wake_at` không làm được: rẻ khi có ít instance tới hạn, nhưng đáng kể khi tồn đọng nhiều. `drain()` dừng lại khi không còn gì có thể bắt đầu.

##### Khởi động child workflow

Việc vận chuyển phát triển thêm: đặt lịch lấy hàng với đơn vị vận chuyển, hủy nó nếu đơn hàng bị hoàn tác, rồi chờ việc giao hàng hoặc trả hàng. Đó là một quy trình riêng, có step, retry và trạng thái riêng, nên hãy cho nó một workflow riêng, và chạy nó như một **child** của quy trình giao hàng:

[[CODE:32]]

`CarrierClient` là bản thay thế cho API đặt lịch của đơn vị vận chuyển, giống như payment provider, nó trả lời một idempotency key lặp lại bằng lần đặt lịch đầu tiên. Trong quy trình giao hàng, child thay thế cho lần chờ:

[[CODE:33]]

Đăng ký `ShipmentWorkflow` và `CarrierClient` làm provider, cạnh quy trình giao hàng. Webhook của đơn vị vận chuyển không thay đổi: nó gửi signal với id đơn hàng, và giờ shipment là instance đang chờ nó.

- **`ctx.executeChild()`** khởi động child và chờ nó kết thúc. Cả hai đều được ghi journal, dưới dạng `$child:<id>` và `$result:<id>`, nên một lần replay nhận lại cùng child thay vì khởi động một child khác, và quy trình giao hàng đỗ lại trong lúc đó. `ctx.startChild()` chỉ khởi động nó, và trả về một handle: `result()` của handle chờ child, và handle là một điều kiện của `waitForAny()`, để cho child chạy đua với một timer hoặc một signal.
- **Id.** Id của một child mặc định gồm id của cha, tên workflow và số thứ tự child của workflow đó trong lần chạy này, chẳng hạn `order-71e1973d/shipment#1`. Hãy cho các child được khởi động từ các nhánh song song một tùy chọn `id` suy ra từ dữ liệu của bạn, để một lần replay, vốn có thể chạm tới chúng theo thứ tự khác, tìm thấy đúng từng child.
- **Thất bại.** Nếu child thất bại, bị hủy hoặc bị terminate, `executeChild()` throw một `ChildWorkflowFailedError`, với `status` của nó và lỗi của nó làm `cause`. Nếu không bắt, nó làm quy trình giao hàng thất bại như mọi lỗi khác: một kiện hàng bị trả về làm shipment thất bại, compensation của shipment hủy lịch lấy hàng, rồi đến quy trình giao hàng, với các compensation hoàn tiền và giải phóng hàng trong kho. Hãy bắt nó để thử cách khác, chẳng hạn một đơn vị vận chuyển khác.
- **`parentClose`** quyết định điều gì xảy ra với một child vẫn đang chạy khi cha của nó kết thúc hoặc bắt đầu bù trừ: `'cancel'`, mặc định, sẽ hủy nó, và các compensation của nó chạy; `'terminate'` dừng nó mà không chạy compensation; `'abandon'` để nó tiếp tục chạy. Khi bộ phận hỗ trợ hủy đơn hàng, shipment bị hủy cùng nó, và lịch lấy hàng bị hủy cùng shipment.
- Một child kế thừa độ ưu tiên của cha, trừ khi `startChild()` nhận một độ ưu tiên riêng, và nhận các tùy chọn `concurrencyKey` và `rateLimitKey` như `start()`. `getStatus()` với tùy chọn `children` liệt kê các child của một instance, mỗi child kèm `parentId`, và `list()` phân trang chúng theo `parentId`.

##### Step chạy lâu

Một step có thể chạy hàng giờ. Trong khi nó chạy, worker liên tục gia hạn lease ở chế độ nền. Với công việc batch dài, hãy lưu checkpoint tiến độ để một lần crash không khởi động lại công việc từ đầu. Ở đây, một batch hàng tháng render hóa đơn từng trang một:

[[CODE:34]]

- `heartbeat(progress)` ghi checkpoint vào journal. Nếu lần thử chết, lần tiếp theo nhận nó dưới dạng `progress`. Khai báo type của tham số là `WorkflowStepContext<Checkpoint>` sẽ gán type cho cả hai. Trang đang được xử lý dở sẽ được render lại, nên `renderPage()` phải ghi đè thay vì nối thêm.
- `heartbeatTimeout` làm thất bại một lần thử ngừng gọi `heartbeat()`, chẳng hạn một lần thử bị kẹt ở một socket treo, trong khi process vẫn còn sống. Tùy chọn `timeout` giới hạn tổng thời lượng của lần thử.
- `signal` bị abort khi shutdown, khi mất lease và khi gặp các timeout đó. Hãy truyền nó cho các thao tác I/O của bạn.

Một lịch chạy, bên dưới, khởi động batch mỗi tháng. Khi công việc nên chạy trên các process riêng, chẳng hạn một nhóm renderer PDF, hãy giao nó cho một queue [BullMQ](/application/queues) từ một step, và chờ job báo lại bằng một signal. Job id là `idempotencyKey` của step, nên một step được retry sẽ không đưa job vào hàng đợi hai lần:

[[CODE:35]]

Processor của queue báo lại khi job đã xong:

[[CODE:36]]

`id` giúp signal chỉ được lưu một lần khi BullMQ chạy lại job, và một job xong trước khi workflow chạm tới lần chờ vẫn được tính, vì signal là bền vững.

##### Chạy workflow theo lịch

Hóa đơn đến hạn vào ngày 1 hàng tháng. Thay vì một cron job khởi động batch, hãy khai báo một lịch chạy trên workflow:

[[CODE:37]]

Mọi worker có code khai báo lịch chạy này đều khởi động các lần chạy của nó, và mỗi lần chạy khởi động đúng một instance, bất kể có bao nhiêu worker: id của nó là id của lịch chạy và thời điểm của lần chạy, chẳng hạn `monthly-invoices@2026-10-01T06:00:00.000Z`. Hàm `input` nhận lần chạy, gồm `id` của lịch chạy và thời điểm `at` của nó, và instance cũng nhận điều này, dưới dạng `ctx.schedule`, giá trị này là `null` với một instance được khởi động theo cách khác.

- **Khi nào.** `cron` nhận 5 trường, hoặc 6 trường với giây đứng đầu, `every` là một khoảng cố định, và `rrule` là một recurrence rule theo RFC 5545. Thời điểm là giờ đồng hồ trong `tz`, mặc định là UTC, nên batch bắt đầu lúc 02:00 ở New York cả trước lẫn sau khi đổi giờ. Khi lùi giờ, một giờ địa phương xuất hiện hai lần chỉ chạy một lần, ở lần đầu tiên, nên một lịch chạy hàng giờ sẽ bỏ qua lượt thứ hai của giờ bị lặp. Khi tiến giờ, một thời điểm không tồn tại vẫn chạy, muộn đúng bằng khoảng giờ bị nhảy: 02:30 chạy lúc 03:30. `every` không nhận `tz`: nó lặp lại một khoảng cố định bất kể múi giờ. `startAt`, `endAt` và `limit` giới hạn một lịch chạy.
- **`missed`** cho biết điều gì xảy ra với các lần chạy mà không worker nào hoạt động để khởi động, trong lúc deploy hoặc gặp sự cố. `'skip'`, mặc định, chỉ khởi động một lần chạy nếu có worker tìm thấy nó trong vòng một phút kể từ thời điểm của nó; `'once'` khởi động lần gần nhất trong số đó; `'all'` khởi động từng lần, tối đa 100 lần gần nhất, và cần `overlap: 'allow'`. Các lần chạy mà nó bỏ qua được báo cáo trong một event `schedule-skipped`.
- **`overlap`** cho biết một lần chạy làm gì khi một instance mà lịch chạy đã khởi động vẫn chưa kết thúc: `'skip'`, mặc định, bỏ qua nó, kèm một event `schedule-skipped`; `'allow'` vẫn khởi động nó; `'cancel-previous'` hủy instance đang chạy; `'buffer-one'` khởi động nó khi instance đang chạy kết thúc.

Một lịch chạy được khai báo thuộc về code, kể cả trong khi một lần rolling deploy chạy song song code cũ và code mới. Mỗi process lưu các lịch chạy mà workflow của nó khai báo khi nó khởi động, và xác nhận chúng mỗi phút trong khi worker của nó chạy. Một process để nguyên một lịch chạy trong khi một process khác xác nhận nó, nếu code của chính nó không khai báo lịch đó hoặc một phiên bản mới hơn của workflow khai báo nó khác đi. Khi không có process nào xác nhận lịch chạy trong năm phút, một process sẽ xóa lịch chạy mà code của nó không khai báo, dù nó có chạy workflow của lịch đó hay không, và thay một khai báo khác bằng khai báo của chính nó. Vì vậy một pod cũ restart giữa lúc rollout sẽ không động tới các lịch chạy mà code mới thêm vào hoặc một phiên bản mới thay đổi, một lịch chạy bị một lần deploy loại bỏ sẽ biến mất khoảng năm phút sau khi process cuối cùng của code cũ dừng, kể cả khi lần deploy xóa workflow của nó, và một lần rollback sẽ mang khai báo cũ trở lại.

Các process của code khác trên cùng database, chẳng hạn worker của các workflow khác, cũng xóa một lịch chạy khi không có worker nào có code khai báo nó chạy trong năm phút, chẳng hạn khi các worker đó bị scale về không. Process tiếp theo có code khai báo nó sẽ lưu lại nó khi khởi động, và lịch chạy bắt đầu lại: từ lần chạy tiếp theo, không bị tạm dừng, với số lần chạy được đếm lại từ không.

`WorkflowClient.schedules`, cũng có thể inject dưới tên `WorkflowSchedules`, xử lý lịch chạy lúc runtime. `trigger('monthly-invoices')` khởi động một lần chạy ngay bây giờ, bất kể `overlap` nói gì và kể cả khi lịch chạy đang tạm dừng, với thời điểm hiện tại làm `at`. `pause()` dừng các lần chạy cho tới `resume()`, lệnh này bắt đầu lại từ lần chạy đầu tiên sau thời điểm hiện tại. `preview()` trả về các lần chạy tiếp theo, tính bằng epoch mili giây, còn `get()` và `list()` đọc các lịch chạy. Một lịch chạy không có trong code, chẳng hạn mỗi khách hàng một lịch, được lưu bằng `upsert()`, và `remove()` xóa nó, để các instance mà nó đã khởi động tiếp tục chạy:

[[CODE:38]]

`upsert()` và `remove()` từ chối một lịch chạy đã khai báo, vốn được thay đổi trong code.

##### Chờ kết quả

Phần lớn bên gọi khởi động một workflow rồi đi tiếp. Một số cần kết quả của nó: một kế toán viên muốn hóa đơn của một tháng ngay bây giờ, trước khi lịch chạy render chúng, gọi một route render chúng và trả lời bằng số lượng. `startAndWait()` khởi động instance và chờ nó kết thúc:

[[CODE:39]]

- `startAndWait()` là `start()`, rồi `result()`, lệnh này chờ một instance kết thúc và resolve với output của nó. Với một id đã có instance, nó chờ instance đó, nên kế toán viên gọi lại route, trong khi batch đang chạy hoặc sau khi nó đã kết thúc, sẽ nhận cùng batch. Các tùy chọn của lần chờ là tham số thứ tư: `timeout` của tham số thứ ba vẫn là run timeout của instance.
- Quá `timeout` của lần chờ, tính theo giờ thực chứ không theo đồng hồ của module, nó reject với `WorkflowResultTimeoutError`, và instance vẫn tiếp tục chạy: route trả lời `202`. Tùy chọn `signal` dừng lần chờ khi nó bị abort, chẳng hạn khi bên gọi bỏ đi.
- Khi shutdown, một lần chờ kéo dài trong khi worker hoàn tất các step đang chạy, tối đa `shutdownTimeout`, nên một instance kết thúc trong lúc đó vẫn trả về kết quả của nó. Sau đó lần chờ reject với một `Error`, trước khi Nest đóng HTTP server, và route trả lời ngay lập tức, ở đây là với `500`, thay vì giữ chân quá trình shutdown cho tới `timeout` của lần chờ.
- Một instance đã thất bại, bị hủy hoặc bị terminate sẽ reject với một `WorkflowFailedError`, có `status` cho biết nó kết thúc thế nào và `cause` là lỗi của nó. Ở đây, đó là `500`.
- `result()` chờ một instance theo id của nó, chẳng hạn instance mà `trigger()` đã khởi động, bất kể process nào chạy nó. `startAndWait()` từ chối tùy chọn `transaction`, vì instance chỉ tồn tại khi transaction của bạn commit: hãy gọi `start()` trong transaction, và `result()` sau khi commit.

#### Deploy thay đổi một cách an toàn

Journal được đánh key theo tên, nên tên của step, sleep và wait là một hợp đồng với mọi instance vẫn đang chạy. Tên cũng là một phần của idempotency key.

Giả sử bạn đổi tên `charge-payment` thành `charge-card` và deploy. Một đơn hàng đang chờ đơn vị vận chuyển sẽ tiếp tục, không tìm thấy entry `charge-card` nào trong journal, và sẽ trừ tiền thẻ lần nữa, với một key mà payment provider chưa từng thấy. Trước khi step mới đầu tiên của một lần thực thi chạy, engine kiểm tra rằng code đã chạm tới mọi step trong journal. Ở đây thì không, nên instance thất bại mà không trừ tiền:

[[CODE:40]]

Các compensation của nó cũng không chạy, vì chúng được định nghĩa bởi code không còn khớp nữa. Instance được để lại cho một người xử lý. Bước kiểm tra này không thấy được một step giữ nguyên tên nhưng phần thân giờ làm điều gì đó khác.

Một số thay đổi không cần phiên bản mới:

- thay đổi phần thân của một step mà không thay đổi ý nghĩa của nó,
- thêm step sau step, sleep hoặc wait cuối cùng mà bất kỳ instance đang chạy nào đã chạm tới,
- thay đổi tùy chọn retry và timeout.

Mọi thay đổi khác phải được ship dưới dạng một phiên bản mới. Chẳng hạn bộ phận marketing muốn một email xác nhận đơn hàng ngay sau khi thanh toán. Chèn một step trước `reserve-stock` sẽ thay đổi những gì một lần replay thấy, nên hãy copy class và tăng phiên bản của nó:

[[CODE:41]]

Đăng ký cả hai class. Một instance giữ phiên bản mà nó đã bắt đầu, và một worker chỉ claim các phiên bản mà nó đã đăng ký, nên pod cũ và mới có thể chạy song song trong một lần rolling deploy. Các instance mới bắt đầu trên phiên bản cao nhất được đăng ký, kể cả khi controller vẫn truyền `OrderFulfilmentWorkflow`, vì class chỉ dùng để xác định tên workflow. Để cố định một phiên bản, hãy thêm `version: 1` vào các tùy chọn của `start()`. Gỡ phiên bản 1 khi `list()` với tên workflow, `version: 1` và các trạng thái chưa kết thúc (`pending`, `running`, `suspended` và `compensating`) trả về rỗng.

##### Quy tắc cho code workflow

`run()` thực thi lại từ đầu mỗi khi một instance tiếp tục. Code nằm giữa các step chạy ở mọi lần thực thi, nên nó phải đưa ra cùng các quyết định mỗi lần:

- Đặt mọi thứ chạm tới hoặc đọc từ thế giới bên ngoài vào một step: lời gọi HTTP, đọc và ghi database, feature flag.
- Bên ngoài step, hãy dùng `ctx.now()`, `ctx.random()` và `ctx.uuid()` thay cho `Date.now()`, `Math.random()` và `randomUUID()`. Chúng được ghi journal.
- Trong `run()`, chỉ `await` các thao tác của `ctx` và các phép tính thuần. Không bao giờ chờ một timer thật.
- Tên step, sleep và wait phải là duy nhất trong một lần chạy. Trong một vòng lặp, hãy thêm index vào tên, chẳng hạn `remind-1` và `remind-2`. Hãy cho các child được khởi động từ các nhánh song song một `id` riêng.
- Đừng gọi các method của `ctx` bên trong hàm của một step. Hàm đó chạy một lần và các lần replay chỉ thấy kết quả của nó, nên engine sẽ làm instance thất bại khi một step gọi `ctx`. Hãy throw một `NonRetryableStepError` từ step thay vì gọi `ctx.fail()` ở đó.
- Nếu bạn bắt lỗi trong `run()`, hãy throw lại những gì bạn không xử lý. `isWorkflowInterrupt()` nhận diện luồng điều khiển của engine. Engine không phụ thuộc vào nó: sau một interrupt bị nuốt mất thì không step nào chạy, `commit()` throw lại, và một lần cancel vẫn hủy. Nhưng các khối `finally` chạy ở mỗi lần tạm dừng, nên hãy giữ side effect ngoài chúng.
- `Promise.all()` trên các step thì ổn, và một step trong cùng `Promise.all()` với một sleep hoặc wait sẽ bắt đầu sau nó. `Promise.race()` và `Promise.any()` không an toàn khi replay.
- Input, kết quả step và payload của signal phải serialize được sang JSON. Một `Date` trả về dưới dạng chuỗi, ở lần chạy đầu tiên và ở mọi lần replay, và các type `Journaled` của kết quả và payload nói rõ điều đó.
- Không giữ trạng thái theo từng lần chạy trên `this`: một instance của class phục vụ mọi đơn hàng.

#### Chạy thử và test

##### Chạy thử

Tạo database, áp dụng migration của bạn, và khởi động ứng dụng với `DATABASE_URL` trỏ tới database:

[[CODE:42]]

Log nêu tên store đang dùng, không phải store trong bộ nhớ mặc định, và cho biết store đã tạo schema của nó: migration của bạn đã tạo `orders`, còn store tạo các bảng riêng của nó. Đặt một đơn hàng, rồi hỏi xem nó đang ở đâu:

[[CODE:43]]

Đơn hàng và quy trình giao hàng của nó đã được commit cùng nhau, worker đã nhận instance, thẻ đã bị trừ tiền, hạt cho mèo đã được giữ chỗ, và instance đang đỗ cho tới khi đơn vị vận chuyển báo việc giao hàng hoặc trả hàng, hoặc hạn chót 3 ngày trong `wakeAt` trôi qua.

Giờ hãy đóng vai đơn vị vận chuyển và báo việc giao hàng:

[[CODE:44]]

Instance đã vượt qua điểm không thể quay lại và đang ngủ cho tới khi việc nhờ đánh giá tới hạn sau 7 ngày. Bộ phận hỗ trợ không còn có thể hủy đơn hàng, và một lần giao hàng cho đơn hàng mà store không biết sẽ bị từ chối:

[[CODE:45]]

Đặt một đơn hàng thứ hai (ở đây nó có id `58b424f5`) và hủy nó trong khi nó đang chờ đơn vị vận chuyển:

[[CODE:46]]

Journal hiển thị cả hai compensation: hàng trong kho được giải phóng trước, rồi tiền được hoàn lại. Lần chờ chưa bao giờ hoàn tất, nên nó được đánh dấu `cancelled`, và stage vẫn ở chỗ workflow đặt lần cuối.

Các instance là các dòng trong database của bạn, trong schema của store, cạnh các đơn hàng:

[[CODE:47]]

Cuối cùng, restart ứng dụng và hỏi lại đơn hàng đầu tiên. Trạng thái của nó không thay đổi, và store không tìm thấy gì để migrate. Khởi động một process thứ hai trên một port khác với cùng database, và hai process sẽ chia sẻ công việc: mỗi instance chạy trên một trong hai tại một thời điểm. Để thấy timeout 3 ngày mà không phải chờ 3 ngày, hãy dùng một test clock, như các test bên dưới làm.

##### Test với đồng hồ thủ công

Có hai thứ giúp test workflow nhanh và tất định:

- Mọi timestamp mà engine dùng (hạn chót, thời điểm retry, thời hạn lease và `ctx.now()`) đều đến từ `clock` của module. Một `ManualWorkflowClock` chỉ dịch chuyển khi bạn gọi `advance()`.
- Khi worker bị tắt, không có gì chạy ở chế độ nền. `WorkflowWorker.drain()` chạy mọi instance tới hạn cho tới khi không còn instance nào có thể bắt đầu, và khởi động các lần chạy của những lịch chạy mà đồng hồ đã vượt qua. Đồng hồ bắt đầu vào ngày 1 tháng 1 năm 2026 lúc 00:00 UTC, nên một test dịch nó đi nhiều ngày cũng sẽ khởi động lần chạy đầu tiên của batch hóa đơn, lúc 07:00 UTC.

Chạy các test trên PGlite, với các migration thật của bạn. Override database mà `DrizzleModule` đăng ký (`getDrizzleToken()` trả về token của nó) bằng một database trên PGlite: workflow store sẽ theo đó, vì factory của nó inject database này, và tạo schema của nó ở đó khi ứng dụng khởi động. Override `WORKFLOWS_MODULE_OPTIONS` với một `ManualWorkflowClock` và một worker bị tắt. Dùng chung database và các bản thay thế cho API bên ngoài giữa các ứng dụng, vì chúng tồn tại lâu hơn một process:

[[CODE:48]]

Với đồng hồ thủ công, timeout 3 ngày chỉ là một lời gọi `advance()`:

[[CODE:49]]

##### Test khả năng phục hồi sau crash

`createWorld()` tạo một database mới cho mỗi test. An toàn khi crash cần hai ứng dụng trên cùng database. Đóng một ứng dụng trong khi một step đang treo sẽ mô phỏng một lần crash: shutdown timeout hết hạn, và lease của process đã chết vẫn ở trong database cho tới khi hết hạn. Ứng dụng thứ hai tiếp quản sau đó:

[[CODE:50]]

Cùng cách thiết lập này bao phủ một lần crash giữa chừng các compensation: process tiếp theo replay journal để dựng lại danh sách compensation, bỏ qua những cái đã làm, và tiếp tục với phần còn lại. PGlite chỉ có một kết nối, nên nó không thể cho thấy hai worker chạy đua giành cùng một instance; các test store của bài hướng dẫn chạy các tình huống race của hợp đồng trên một PostgreSQL server, cùng với ba ứng dụng chia nhau 30 đơn hàng.

Để cho một test store riêng mà không cần override provider, hãy gọi `registerSource()` trên `moduleRef.get(WorkflowStorage)` trước `init()`, với `replace: true`: không có nó, lần đăng ký thứ hai sẽ throw. Tùy chọn `clock` nhận bất kỳ `WorkflowClock` nào, một object có `now()` trả về epoch mili giây, nên một test có thể điều khiển engine bằng một đồng hồ mà nó đã có sẵn.
