### Health check

Tích hợp Terminus cung cấp các health check **readiness/liveness**. Health check rất quan trọng trong các hệ thống backend phức tạp. Trong phát triển web, một health check thường là một địa chỉ riêng, ví dụ `https://my-website.com/health/readiness`.
Một service hoặc thành phần trong hạ tầng của bạn (ví dụ [Kubernetes](https://kubernetes.io/)) liên tục kiểm tra địa chỉ này. Tùy vào HTTP status code trả về từ một request `GET` tới địa chỉ này, service đó sẽ hành động khi nhận được một response "không khỏe" (unhealthy).
Vì định nghĩa "khỏe" hay "không khỏe" khác nhau tùy loại service bạn cung cấp, tích hợp **Terminus** cung cấp một tập các **health indicator**.

Ví dụ, nếu web server của bạn dùng MongoDB để lưu dữ liệu, thì việc MongoDB có còn đang chạy hay không là thông tin sống còn.
Trong trường hợp đó, bạn có thể dùng `MongooseHealthIndicator`. Khi đã được cấu hình (như mô tả bên dưới), địa chỉ health check của bạn sẽ trả về
một HTTP status code khỏe hoặc không khỏe, tùy vào việc MongoDB có đang chạy hay không.

#### Bắt đầu

Để bắt đầu với `@nestjs/terminus`, hãy cài dependency cần thiết:

[[CODE:1]]

#### Thiết lập một health check

Một health check là bản tổng hợp của các **health indicator**. Một health indicator kiểm tra xem một service đang ở trạng thái khỏe hay không khỏe. Một health check là tích cực nếu mọi health indicator được gán cho nó đều đang hoạt động. Vì nhiều ứng dụng cần các health indicator tương tự nhau, [`@nestjs/terminus`](https://github.com/nestjs/terminus) cung cấp sẵn một tập indicator:

- `HttpHealthIndicator`
- `TypeOrmHealthIndicator`
- `MongooseHealthIndicator`
- `SequelizeHealthIndicator`
- `MikroOrmHealthIndicator`
- `PrismaHealthIndicator`
- `MicroserviceHealthIndicator`
- `GRPCHealthIndicator`
- `MemoryHealthIndicator`
- `DiskHealthIndicator`

Để bắt đầu với health check đầu tiên, hãy tạo `HealthModule` và thêm `TerminusModule` vào mảng `imports` của nó.

> info **Hint** Để tạo module bằng [Nest CLI](/cli/overview), hãy chạy lệnh `$ nest g module health`.

[[CODE:2]]

Health check được thực thi bởi một [controller](/controllers), bạn có thể tạo nó bằng [Nest CLI](/cli/overview).

[[CODE:3]]

> info **Hint** Chúng tôi rất khuyên bạn bật shutdown hook trong ứng dụng. Khi được bật, tích hợp Terminus dùng lifecycle event này để báo trạng thái `'shutting_down'` và áp dụng [graceful shutdown timeout](#graceful-shutdown-timeout). Tìm hiểu thêm trong phần [shutdown ứng dụng](/fundamentals/lifecycle-events#application-shutdown).

#### HTTP health check

Khi đã cài `@nestjs/terminus`, import `TerminusModule` và tạo một controller mới, bạn đã sẵn sàng tạo một health check.

`HttpHealthIndicator` cần package `@nestjs/axios`, nên hãy đảm bảo nó đã được cài:

[[CODE:4]]

Giờ hãy thiết lập `HealthController`:

[[CODE:5]]

[[CODE:6]]

Health check giờ sẽ gửi một request `GET` tới địa chỉ `https://docs.nestjs.com`. Nếu
địa chỉ đó trả về một response khỏe, route tại `http://localhost:3000/health` sẽ trả về
object sau với status code `200`:

[[CODE:7]]

Package `@nestjs/terminus` export type của object response này dưới tên `HealthCheckResult`.

|           |                                                                                                                                                                                             |                                      |
|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| `status`  | Nếu có bất kỳ health indicator nào thất bại, status là `'error'`. Nếu không có indicator nào thất bại nhưng có ít nhất một indicator là `'degraded'`, status là `'degraded'`. Nếu ứng dụng Nest đang shutdown nhưng vẫn nhận HTTP request, status là `'shutting_down'`. | `'error' \| 'ok' \| 'degraded' \| 'shutting_down'` |
| `info`    | Object chứa thông tin về từng health indicator có status là `'up'` hoặc `'degraded'`, nói cách khác là "vẫn đang phục vụ".                                                                  | `object`                             |
| `error`   | Object chứa thông tin về từng health indicator có status là `'down'`, nói cách khác là "không khỏe".                                                                                         | `object`                             |
| `details` | Object chứa thông tin về mọi health indicator.                                                                                                                                              | `object`                             |

##### Kiểm tra HTTP response code cụ thể

Trong một số trường hợp, bạn có thể muốn kiểm tra theo tiêu chí cụ thể và validate response. Ví dụ, giả sử
`https://my-external-service.com` trả về response code `204`. Với `HttpHealthIndicator.responseCheck()`, bạn có thể
kiểm tra riêng response code đó và coi mọi code khác là không khỏe.

Trong ví dụ sau, mọi response code khác `204` đều là không khỏe. Tham số thứ ba là một hàm (đồng bộ hoặc bất đồng bộ)
trả về một boolean cho biết response được coi là khỏe (`true`) hay không khỏe (`false`).


[[CODE:8]]


#### TypeOrm health indicator

Terminus cho phép bạn thêm việc kiểm tra database vào health check. Trước khi dùng health indicator này, hãy đọc chương
[database](/data/typeorm) và đảm bảo kết nối database của ứng dụng đã được thiết lập.

> info **Hint** Bên dưới, `TypeOrmHealthIndicator` thực thi lệnh SQL `SELECT 1`, lệnh thường được dùng để kiểm tra database có còn sống không. Với database Oracle, nó dùng `SELECT 1 FROM DUAL`, và với SAP HANA là `SELECT now() FROM dummy`.

[[CODE:9]]

Nếu database của bạn kết nối được, một request `GET` tới `http://localhost:3000/health` sẽ trả về kết quả JSON sau:

[[CODE:10]]

Nếu ứng dụng của bạn dùng [nhiều database](/data/typeorm#multiple-databases), hãy inject từng
data source vào `HealthController`. Sau đó truyền tham chiếu data source cho `TypeOrmHealthIndicator` qua tùy chọn `connection`.

[[CODE:11]]


#### Disk health indicator

`DiskHealthIndicator` kiểm tra dung lượng lưu trữ đang được dùng. Để bắt đầu, hãy inject `DiskHealthIndicator`
vào `HealthController`. Ví dụ sau kiểm tra dung lượng lưu trữ được dùng bởi đường dẫn `/` (trên Windows, dùng `C:\\`).
Nếu hơn 50% tổng dung lượng lưu trữ đã được dùng, health check sẽ báo trạng thái không khỏe.

[[CODE:12]]

Method `DiskHealthIndicator.checkStorage()` cũng có thể kiểm tra theo một dung lượng cố định.
Ví dụ sau là không khỏe nếu dung lượng lưu trữ được dùng bởi đường dẫn `/` vượt quá 250GB.

[[CODE:13]]

#### Memory health indicator

Dùng `MemoryHealthIndicator` để đảm bảo process của bạn không vượt quá một giới hạn bộ nhớ nhất định.
Ví dụ sau kiểm tra heap của process.

> info **Hint** Heap là phần bộ nhớ chứa các vùng nhớ được cấp phát động. `checkHeap()` so sánh giá trị `heapUsed` do `process.memoryUsage()` báo cáo (bộ nhớ heap của V8 đang được dùng) với ngưỡng cho trước tính bằng byte.

[[CODE:14]]

Bạn cũng có thể kiểm tra RSS của process bằng `MemoryHealthIndicator.checkRSS()`. Ví dụ sau
trả về một response code không khỏe nếu process của bạn đã cấp phát hơn 150MB.

> info **Hint** RSS (Resident Set Size) cho biết lượng bộ nhớ được cấp phát cho process và đang nằm trong RAM.
> Nó không bao gồm bộ nhớ đã bị swap ra. Nó có bao gồm bộ nhớ từ các shared library, miễn là các page từ
> những library đó thực sự nằm trong bộ nhớ, cũng như toàn bộ bộ nhớ stack và heap.


[[CODE:15]]


#### Custom health indicator

Trong một số trường hợp, các health indicator có sẵn của `@nestjs/terminus` không đáp ứng hết mọi yêu cầu health check của bạn. Khi đó, bạn có thể tạo một custom health indicator.

Phần lớn health indicator theo cùng một pattern: chạy một thao tác, rồi đánh dấu indicator là `'up'` nếu nó thành công và `'down'` nếu nó thất bại. `HealthIndicatorService` hiện thực pattern này bằng `attempt()`. Để cho thấy cấu trúc của một indicator, chúng ta sẽ tạo một ví dụ `DogHealthIndicator`. Service này nên ở trạng thái `'up'` chừng nào một API chó bên ngoài còn trả lời trong vòng một giây.

[[CODE:16]]

`attempt()` nhận một hàm đồng bộ hoặc bất đồng bộ và đánh dấu indicator là `'up'` khi hàm resolve. Mọi dữ liệu mà hàm trả về sẽ được nối thêm vào kết quả. Nếu hàm throw, indicator được đánh dấu là `'down'` và error message được thêm vào kết quả. Trong cả hai trường hợp, thời gian hàm đã chạy được báo cáo dưới dạng `responseTime`. `withTimeout()` giới hạn lần thử trong số mili giây cho trước (xem [Timeout và caching](#timeouts-and-caching)).

Tiếp theo, đăng ký health indicator làm provider:

[[CODE:17]]

> info **Hint** Trong một ứng dụng thực tế, `DogHealthIndicator` nên được cung cấp trong một module riêng, ví dụ `DogModule`, rồi được `HealthModule` import.

Bước cuối cùng là thêm health indicator mới vào endpoint health check. Quay lại `HealthController` và thêm nó vào method `healthCheck()`:

[[CODE:18]]

Nếu API trả lời kịp thời, health check trả về kết quả sau:

[[CODE:19]]

> info **Hint** Terminus tự thực thi các attempt, nên bạn có thể truyền một attempt cho `health.check([...])` trực tiếp (`this.dogHealthIndicator.isHealthy('dog')`) hoặc bọc trong một hàm, như ví dụ ở trên.

##### Kiểm soát tường minh với up() và down()

Đôi khi "khỏe" có nghĩa là nhiều hơn "thao tác không throw". Để tự quyết định trạng thái, hãy trả về trực tiếp `up()` hoặc `down()` thay vì dùng `attempt()`. Giả sử giờ các chú chó được lưu ở local, và indicator chỉ khỏe nếu mọi `Dog` đều có type `'goodboy'`.

[[CODE:20]]

Cả `up()` và `down()` đều nhận một object chứa dữ liệu bổ sung, được nối thêm vào kết quả, hoặc một chuỗi, được thêm vào dưới dạng thuộc tính `message`.

##### Trạng thái degraded

Không phải vấn đề nào cũng đáng để đưa ứng dụng ra khỏi vòng phục vụ. Ví dụ, một cache không kết nối được sẽ làm ứng dụng chậm đi nhưng không làm nó hỏng. Với những trường hợp như vậy, một indicator có thể trả về `degraded()`. Một indicator degraded không làm health check thất bại: nó được liệt kê trong `info`, status tổng thể trở thành `'degraded'`, và HTTP status code vẫn là `200`. Các orchestrator tiếp tục điều phối lưu lượng tới, trong khi trạng thái vẫn hiển thị trên hệ thống giám sát.

[[CODE:21]]

[[CODE:22]]

Giống như `up()` và `down()`, `degraded()` nhận một object chứa dữ liệu bổ sung hoặc một chuỗi message. Ngay khi có bất kỳ indicator nào là `'down'`, status tổng thể là `'error'` bất kể các indicator degraded.

> warning **Warning** Một health indicator được xây bằng `up()`, `down()` và `degraded()` báo cáo trạng thái của nó bằng cách trả về một trong số đó. Một lỗi do indicator như vậy throw ra được coi là bug, không phải trạng thái không khỏe: nó hủy toàn bộ health check và dẫn tới response `500` thay vì `503`. Nếu indicator của bạn bọc một thao tác có thể throw, hãy dùng `attempt()`, hàm này chuyển một lỗi được throw thành trạng thái `'down'`.

#### Timeout và caching

Mọi check được xây bằng `attempt()` đều trả về một `HealthCheckAttempt`. Điều này bao gồm các custom indicator của bạn cũng như các indicator database, microservice và gRPC có sẵn. Trước khi attempt được thực thi, bạn có thể cấu hình nó bằng cách nối chuỗi `withTimeout()` và `cacheFor()`.

##### Timeout

`withTimeout()` giới hạn attempt trong số mili giây cho trước. Khi hết thời gian, indicator được đánh dấu là `'down'` và `AbortSignal` được truyền cho hàm của bạn sẽ bị abort. Hãy truyền `signal` đó cho thao tác bên dưới để nó cũng bị hủy theo, thay vì tiếp tục lơ lửng ở chế độ nền.

[[CODE:23]]

Nếu API chó từ custom indicator không trả lời trong vòng một giây, health check sẽ trả về kết quả sau:

[[CODE:24]]

> warning **Warning** Tùy chọn `timeout` của các indicator có sẵn (ví dụ `this.db.pingCheck('database', {{ '{' }} timeout: 1500 {{ '}' }})`) đã bị deprecated. Hãy nối chuỗi `.withTimeout()` trên attempt được trả về thay vào đó.

##### Caching

Các orchestrator thường poll health check vài giây một lần, và một số check quá tốn kém để chạy ở mọi request. `cacheFor()` cache kết quả của một attempt trong số mili giây cho trước. Trong khi vẫn còn một kết quả mới, hàm không được thực thi lại, và các health check đồng thời dùng chung một lần thực thi đang chạy. Cache được dùng chung giữa các request và được đánh key theo key của indicator.

[[CODE:25]]

Các kết quả lấy từ cache được đánh dấu bằng `cachedResponse: true`:

[[CODE:26]]

#### Logging

Mặc định, Terminus log một lỗi khi một health check thất bại. Khi có cấu hình graceful shutdown timeout, nó cũng log tiến trình shutdown. Method `TerminusModule.forRoot()` cho bạn kiểm soát nhiều hơn cách lỗi được log, và cho phép bạn tiếp quản toàn bộ việc log.

Phần này hướng dẫn bạn tạo một custom logger, `TerminusLogger`. Logger này kế thừa `ConsoleLogger` có sẵn,
nên bạn có thể chọn phần nào của logger cần override.

> info **Hint** Để tìm hiểu thêm về custom logger trong Nest, xem [inject một custom logger](/application/logger#injecting-a-custom-logger).


[[CODE:27]]

Khi đã tạo custom logger, hãy truyền nó cho `TerminusModule.forRoot()`:

[[CODE:28]]


Để tắt mọi message log từ Terminus, kể cả error message, hãy đặt tùy chọn `logger` thành `false`:

[[CODE:29]]



Bạn cũng có thể cấu hình cách các lỗi health check được hiển thị trong log.

| Kiểu log lỗi             | Mô tả                                                                                                                              | Ví dụ                                                                |
|:------------------|:-----------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------|
| `json`  (mặc định) | In bản tóm tắt kết quả health check dưới dạng một object JSON khi một check thất bại                                              | <figure><img src="/assets/Terminus_Error_Log_Json.png" /></figure>   |
| `pretty`          | In bản tóm tắt kết quả health check trong các ô được định dạng khi một check thất bại, làm nổi bật kết quả thành công và thất bại  | <figure><img src="/assets/Terminus_Error_Log_Pretty.png" /></figure> |

Để thay đổi kiểu log, hãy dùng tùy chọn cấu hình `errorLogStyle`:

[[CODE:30]]

#### Graceful shutdown timeout

Nếu ứng dụng của bạn cần trì hoãn việc shutdown, Terminus có thể xử lý giúp bạn bằng tùy chọn `gracefulShutdownTimeoutMs` (tính bằng mili giây, mặc định `0`).
Thiết lập này đặc biệt hữu ích với một orchestrator như Kubernetes.
Bằng cách đặt một độ trễ dài hơn một chút so với chu kỳ kiểm tra readiness, bạn có thể đạt được zero downtime khi tắt container: ngay khi nhận được tín hiệu kết thúc, health check báo `'shutting_down'` với status code `503`, nên orchestrator ngừng điều phối lưu lượng mới tới trong khi ứng dụng hoàn tất các request đang xử lý trong khoảng thời gian trì hoãn.

[[CODE:31]]

> warning **Warning** Độ trễ chỉ được áp dụng với `SIGTERM`, tín hiệu mà các orchestrator như Kubernetes gửi khi dừng một container. Các tín hiệu khác (ví dụ `SIGINT` từ `Ctrl+C`) vẫn chuyển health check sang `'shutting_down'` nhưng tắt ứng dụng ngay lập tức. Hãy đảm bảo [shutdown hook](/fundamentals/lifecycle-events#application-shutdown) đã được bật; nếu không, Terminus sẽ không bao giờ nhận được tín hiệu.

#### Thêm ví dụ

Có thêm các ví dụ chạy được trong [thư mục sample của Terminus](https://github.com/nestjs/terminus/tree/master/sample).
