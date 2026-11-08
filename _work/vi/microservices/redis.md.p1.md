### Redis

Transporter [Redis](https://redis.io/) hiện thực mô hình messaging publish/subscribe và dùng tính năng [Pub/Sub](https://redis.io/topics/pubsub) của Redis. Các message được publish được phân loại theo channel, mà bên publish không biết subscriber nào (nếu có) sẽ nhận được chúng. Mỗi microservice có thể subscribe bao nhiêu channel tùy ý, và một message có thể được nhiều subscriber nhận. Các message trao đổi qua channel là **fire-and-forget**: nếu một message được publish mà không có subscriber nào quan tâm, message đó bị xóa và không thể khôi phục. Do đó, không có đảm bảo nào rằng một message hay event được ít nhất một service xử lý.

<figure><img class="illustrative-image" src="/assets/Redis_1.png" /></figure>

#### Cài đặt

Để bắt đầu xây dựng microservice dựa trên Redis, trước tiên hãy cài package cần thiết:

[[CODE:1]]

#### Tổng quan

Để dùng transporter Redis, hãy truyền options object sau cho method `createMicroservice()`:

[[CODE:2]]

> info **Hint** Enum `Transport` được import từ package `@nestjs/microservices`.

#### Tùy chọn

Thuộc tính `options` phụ thuộc vào transporter được chọn. Transporter <strong>Redis</strong> cung cấp các thuộc tính được mô tả bên dưới.

<table>
  <tr>
    <td><code>host</code></td>
    <td>Hostname của kết nối</td>
  </tr>
  <tr>
    <td><code>port</code></td>
    <td>Port của kết nối</td>
  </tr>
  <tr>
    <td><code>retryAttempts</code></td>
    <td>Số lần thử kết nối lại (mặc định: <code>0</code>, tức không thử lại)</td>
  </tr>
  <tr>
    <td><code>retryDelay</code></td>
    <td>Độ trễ giữa các lần thử kết nối lại (ms) (mặc định: <code>5000</code>)</td>
  </tr>
  <tr>
    <td><code>wildcards</code></td>
    <td>Bật wildcard subscription của Redis, chỉ thị transporter dùng <code>psubscribe</code>/<code>pmessage</code> bên dưới (mặc định: <code>false</code>)</td>
  </tr>
</table>

Transporter cũng hỗ trợ mọi thuộc tính của client chính thức [ioredis](https://redis.github.io/ioredis/index.html#RedisOptions).

#### Client

Như với các transporter microservice khác, bạn có <a href="/microservices/basics#client-producer-class">nhiều lựa chọn</a> để tạo một instance `ClientProxy` cho Redis.

Một cách để tạo instance là dùng `ClientsModule`. Import nó và dùng method `register()` của nó để truyền một options object có cùng các thuộc tính như ở trên cho method `createMicroservice()`, cộng thêm thuộc tính `name` dùng làm injection token. Đọc thêm về `ClientsModule` trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

[[CODE:3]]

Bạn cũng có thể tạo client bằng `ClientProxyFactory` hoặc decorator `@Client()`. Cả hai đều được mô tả trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

#### Context

Trong các tình huống phức tạp hơn, bạn có thể cần thêm thông tin về request đi vào. Với transporter Redis, bạn có thể truy cập object `RedisContext`.

[[CODE:4]]

> info **Hint** `@Payload()`, `@Ctx()` và `RedisContext` được import từ package `@nestjs/microservices`.

#### Wildcard

Để bật hỗ trợ wildcard, hãy đặt tùy chọn `wildcards` thành `true`. Điều này chỉ thị transporter dùng `psubscribe` và `pmessage` bên dưới.

[[CODE:5]]

Hãy truyền cả tùy chọn `wildcards` khi tạo một instance client.

Khi bật tùy chọn này, bạn có thể dùng wildcard trong message pattern và event pattern. Ví dụ, để subscribe mọi channel bắt đầu bằng `notifications.`, hãy dùng pattern sau:

[[CODE:6]]

#### Cập nhật trạng thái instance

Để nhận cập nhật real-time về kết nối và trạng thái của instance driver bên dưới, hãy subscribe stream `status`. Stream này cung cấp các cập nhật trạng thái riêng của driver được chọn. Với driver Redis, stream `status` phát ra các event `connected`, `disconnected` và `reconnecting`.

[[CODE:7]]

> info **Hint** Type `RedisStatus` được import từ package `@nestjs/microservices`.

Tương tự, bạn có thể subscribe stream `status` của server để nhận thông báo về trạng thái của server.

[[CODE:8]]

#### Lắng nghe các event của Redis

Trong một số trường hợp, bạn có thể muốn lắng nghe các event nội bộ do microservice phát ra. Ví dụ, bạn có thể lắng nghe event `error` để kích hoạt thêm các thao tác khi có lỗi xảy ra. Để làm vậy, hãy dùng method `on()`. Vì transporter Redis dùng hai kết nối (xem [truy cập driver bên dưới](#underlying-driver-access)), callback nhận kết nối đã phát ra event (`'pub'` hoặc `'sub'`) làm tham số đầu tiên:

[[CODE:9]]

Tương tự, bạn có thể lắng nghe các event nội bộ của server:

[[CODE:10]]

> info **Hint** Type `RedisEvents` được import từ package `@nestjs/microservices`.

Bắt đầu từ NestJS v12.1, các listener được đăng ký bằng method `on()` của client vẫn được giữ cho tới khi bạn gọi `close()`, nên chúng cũng được gắn vào các kết nối `pub` và `sub` mới mà client tạo ở lời gọi `send()` hoặc `emit()` tiếp theo sau khi kết nối đã kết thúc (khi mọi `retryAttempts` được cấu hình đã hết). Các lần đăng ký không được khử trùng lặp, nên hãy đăng ký mỗi listener một lần thay vì đăng ký lại từ callback của nó hoặc sau mỗi lần kết nối lại.

#### Truy cập driver bên dưới

Với các use case nâng cao hơn, bạn có thể cần truy cập instance driver bên dưới, ví dụ để tự đóng kết nối hoặc dùng các method riêng của driver. Tuy nhiên, trong hầu hết các trường hợp, bạn **không cần** truy cập trực tiếp driver.

Để làm vậy, hãy dùng method `unwrap()`, method này trả về instance driver bên dưới. Generic type parameter chỉ định type của instance driver mà bạn mong đợi.

[[CODE:11]]

Tương tự, bạn có thể truy cập instance driver bên dưới của server:

[[CODE:12]]

Khác với các transporter khác, transporter Redis trả về một tuple gồm hai instance `ioredis`: instance đầu tiên publish message, và instance thứ hai subscribe chúng.
