### RabbitMQ

[RabbitMQ](https://www.rabbitmq.com/) là một message broker mã nguồn mở, gọn nhẹ, hỗ trợ nhiều giao thức messaging. Nó có thể được triển khai theo cấu hình phân tán và federated để đáp ứng các yêu cầu về quy mô lớn và tính sẵn sàng cao, và là một trong những message broker được triển khai rộng rãi nhất, được dùng bởi cả các startup nhỏ lẫn các doanh nghiệp lớn.

#### Cài đặt

Để bắt đầu xây dựng microservice dựa trên RabbitMQ, trước tiên hãy cài các package cần thiết:

[[CODE:1]]

#### Tổng quan

Để dùng transporter RabbitMQ, hãy truyền options object sau cho method `createMicroservice()`:

[[CODE:2]]

> info **Hint** Enum `Transport` được import từ package `@nestjs/microservices`.

#### Tùy chọn

Thuộc tính `options` phụ thuộc vào transporter được chọn. Transporter <strong>RabbitMQ</strong> cung cấp các thuộc tính sau.

<table>
  <tr>
    <td><code>urls</code></td>
    <td>Một mảng URL kết nối để thử theo thứ tự</td>
  </tr>
  <tr>
    <td><code>queue</code></td>
    <td>Tên queue mà server của bạn lắng nghe</td>
  </tr>
  <tr>
    <td><code>prefetchCount</code></td>
    <td>Đặt prefetch count cho channel</td>
  </tr>
  <tr>
    <td><code>isGlobalPrefetchCount</code></td>
    <td>Nếu là <code>true</code>, áp dụng prefetch count theo từng channel thay vì theo từng consumer</td>
  </tr>
  <tr>
    <td><code>noAck</code></td>
    <td>Nếu là <code>false</code>, bật chế độ acknowledgment thủ công. Mặc định là <code>true</code></td>
  </tr>
  <tr>
    <td><code>consumerTag</code></td>
    <td>Một tên mà server dùng để phân biệt các lần gửi message cho consumer; nó không được đang được dùng trên channel. Thường thì dễ hơn nếu bỏ qua nó, khi đó server tự tạo một tên ngẫu nhiên và cung cấp nó trong reply (xem <a href="https://amqp-node.github.io/amqplib/channel_api.html#channel_consume" rel="nofollow" target="_blank"><code>channel.consume()</code> trong tài liệu amqplib</a>)</td>
  </tr>
  <tr>
    <td><code>queueOptions</code></td>
    <td>Các tùy chọn bổ sung cho queue (xem <a href="https://amqp-node.github.io/amqplib/channel_api.html#channel_assertQueue" rel="nofollow" target="_blank"><code>channel.assertQueue()</code> trong tài liệu amqplib</a>)</td>
  </tr>
  <tr>
    <td><code>socketOptions</code></td>
    <td>Các tùy chọn bổ sung cho socket (xem <a href="https://amqp-node.github.io/amqplib/channel_api.html#connect" rel="nofollow" target="_blank"><code>connect()</code> trong tài liệu amqplib</a>)</td>
  </tr>
  <tr>
    <td><code>headers</code></td>
    <td>Các header được gửi kèm mọi message. Chỉ áp dụng cho cấu hình producer (client)</td>
  </tr>
  <tr>
    <td><code>replyQueue</code></td>
    <td>Reply queue cho producer. Mặc định là <code>amq.rabbitmq.reply-to</code></td>
  </tr>
  <tr>
    <td><code>persistent</code></td>
    <td>Nếu là giá trị truthy, message tồn tại qua các lần restart broker, với điều kiện chúng nằm trong một queue cũng tồn tại qua các lần restart</td>
  </tr>
  <tr>
    <td><code>noAssert</code></td>
    <td>Nếu là <code>true</code>, queue không được assert trước khi tiêu thụ. Mặc định là <code>false</code></td>
  </tr>
  <tr>
    <td><code>wildcards</code></td>
    <td>Chỉ đặt thành <code>true</code> nếu bạn muốn dùng topic exchange để định tuyến message tới các queue. Bật nó cho phép bạn dùng wildcard (<code>*</code>, <code>#</code>) trong message pattern và event pattern</td>
  </tr>
  <tr>
    <td><code>exchange</code></td>
    <td>Tên của exchange. Mặc định là tên queue khi <code>wildcards</code> được đặt thành <code>true</code></td>
  </tr>
  <tr>
    <td><code>exchangeType</code></td>
    <td>Loại exchange. Mặc định là <code>topic</code>. Nhận các loại AMQP tiêu chuẩn <code>direct</code>, <code>fanout</code>, <code>topic</code> và <code>headers</code>, hoặc tên của một loại exchange tùy chỉnh</td>
  </tr>
  <tr>
    <td><code>exchangeArguments</code></td>
    <td>Các argument bổ sung được truyền khi assert exchange</td>
  </tr>
  <tr>
    <td><code>routingKey</code></td>
    <td>Routing key bổ sung cho topic exchange</td>
  </tr>
  <tr>
    <td><code>maxConnectionAttempts</code></td>
    <td>Số lần thử kết nối tối đa. Chỉ áp dụng cho cấu hình consumer. Mặc định là <code>-1</code> (vô hạn)</td>
  </tr>
</table>

#### Client

Như với các transporter microservice khác, bạn có [nhiều lựa chọn](/microservices/basics#client-producer-class) để tạo một instance `ClientProxy` cho RabbitMQ.

Một cách để tạo instance là dùng `ClientsModule`. Import nó và gọi method `register()` của nó, truyền một options object có cùng các thuộc tính như ở trên cho method `createMicroservice()`, cộng thêm thuộc tính `name` dùng làm injection token. Đọc thêm về `ClientsModule` trong [trang tổng quan về microservice](/microservices/basics#client-producer-class).

[[CODE:3]]

Bạn cũng có thể tạo client bằng `ClientProxyFactory` hoặc `@Client()`, như mô tả trong [trang tổng quan về microservice](/microservices/basics#client-producer-class).

#### Context

Trong các tình huống phức tạp hơn, bạn có thể cần thêm thông tin về request đi vào. Khi dùng transporter RabbitMQ, bạn có thể truy cập object `RmqContext`.

[[CODE:4]]

> info **Hint** `@Payload()`, `@Ctx()` và `RmqContext` được import từ package `@nestjs/microservices`.

Để truy cập message RabbitMQ gốc (với `properties`, `fields` và `content` của nó), hãy dùng method `getMessage()` của object `RmqContext`:

[[CODE:5]]

Để lấy tham chiếu tới [channel](https://www.rabbitmq.com/channels.html) RabbitMQ, hãy dùng method `getChannelRef()` của object `RmqContext`:

[[CODE:6]]

#### Acknowledgement message

Để đảm bảo một message không bao giờ bị mất, RabbitMQ hỗ trợ [message acknowledgement](https://www.rabbitmq.com/confirms.html). Consumer gửi lại một acknowledgement để báo cho RabbitMQ rằng một message cụ thể đã được nhận và xử lý, và RabbitMQ có thể xóa nó. Nếu một consumer chết (channel của nó bị đóng, kết nối của nó bị đóng, hoặc kết nối TCP bị mất) mà không gửi ack, RabbitMQ cho rằng message chưa được xử lý xong và đưa nó trở lại hàng đợi.

Mặc định, transporter RabbitMQ không chờ acknowledgement (`noAck` là `true`). Để bật chế độ acknowledgment thủ công, hãy đặt thuộc tính `noAck` thành `false`:

[[CODE:7]]

Khi bật acknowledgement thủ công của consumer, bạn phải gửi một acknowledgement từ worker để báo rằng nó đã hoàn tất công việc:

[[CODE:8]]

#### Record builder

Để cấu hình các tùy chọn của message, hãy dùng class `RmqRecordBuilder` (nó cũng hoạt động cho các luồng event-based). Ví dụ, để đặt các thuộc tính `headers` và `priority`, hãy dùng method `setOptions()`:

[[CODE:9]]

> info **Hint** Class `RmqRecordBuilder` được export từ package `@nestjs/microservices`.

Bạn cũng có thể đọc các giá trị này ở phía server, bằng cách truy cập `RmqContext`:

[[CODE:10]]

Bắt đầu từ NestJS v12.1.3, một message handler cũng có thể trả về một record. Nest gửi dữ liệu của record làm reply và áp dụng các tùy chọn của record (ví dụ các thuộc tính `headers` và `priority`) cho message reply:

[[CODE:11]]

Reply luôn mang theo correlation id của request, để client có thể khớp nó với request.

#### Cập nhật trạng thái instance

Để nhận cập nhật real-time về kết nối và trạng thái của instance driver bên dưới, hãy subscribe stream `status`. Stream này cung cấp các cập nhật trạng thái riêng của driver được chọn. Với driver RMQ, stream `status` phát ra các event `connected`, `disconnected`, `blocked` và `unblocked`.

[[CODE:12]]

> info **Hint** Type `RmqStatus` được import từ package `@nestjs/microservices`.

Tương tự, bạn có thể subscribe stream `status` của server để nhận thông báo về trạng thái của server:

[[CODE:13]]

#### Lắng nghe các event của RabbitMQ

Trong một số trường hợp, bạn có thể muốn lắng nghe các event nội bộ do microservice phát ra. Ví dụ, bạn có thể lắng nghe event `error` để kích hoạt thêm các thao tác khi có lỗi xảy ra. Để làm vậy, hãy dùng method `on()`:

[[CODE:14]]

Tương tự, bạn có thể lắng nghe các event nội bộ của server:

[[CODE:15]]

> info **Hint** Type `RmqEvents` được import từ package `@nestjs/microservices`.

Bắt đầu từ NestJS v12.1.2, các listener được đăng ký bằng method `on()` của client vẫn được giữ cho tới khi bạn gọi `close()`, nên chúng cũng được gắn vào kết nối mới mà client tạo ở lời gọi `send()` hoặc `emit()` tiếp theo sau khi một lần thử kết nối thất bại. Các lần đăng ký không được khử trùng lặp, nên hãy đăng ký mỗi listener một lần thay vì đăng ký lại sau một lần thử thất bại.

#### Truy cập driver bên dưới

Với các use case nâng cao hơn, bạn có thể cần truy cập instance driver bên dưới, ví dụ để tự đóng kết nối hoặc dùng các method riêng của driver. Tuy nhiên, trong hầu hết các trường hợp, bạn **không cần** truy cập trực tiếp driver.

Để làm vậy, hãy dùng method `unwrap()`, method này trả về instance driver bên dưới. Dùng generic type parameter để chỉ định type của instance driver mà bạn mong đợi.

[[CODE:16]]

Tương tự, bạn có thể truy cập instance driver bên dưới của server:

[[CODE:17]]

#### Wildcard

RabbitMQ hỗ trợ dùng wildcard trong routing key để định tuyến message linh hoạt. Wildcard `#` khớp với không hoặc nhiều từ, còn wildcard `*` khớp với đúng một từ.

Ví dụ, routing key `cats.#` khớp với `cats`, `cats.meow` và `cats.meow.purr`. Routing key `cats.*` khớp với `cats.meow` nhưng không khớp với `cats.meow.purr`.

Để bật hỗ trợ wildcard trong microservice RabbitMQ của bạn, hãy đặt tùy chọn cấu hình `wildcards` thành `true` trong options object:

[[CODE:18]]

Với cấu hình này, bạn có thể dùng wildcard trong routing key khi subscribe event và message. Ví dụ, để lắng nghe các message có routing key `cats.#`:

[[CODE:19]]

Để gửi một message với một routing key cụ thể, hãy dùng method `send()` của instance `ClientProxy`:

[[CODE:20]]
