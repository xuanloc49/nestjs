### NATS

[NATS](https://nats.io) là một hệ thống messaging mã nguồn mở đơn giản, bảo mật và hiệu năng cao dành cho các ứng dụng cloud native, messaging IoT và kiến trúc microservice. NATS server được viết bằng Go, và có client library cho hàng chục ngôn ngữ lập trình phổ biến. NATS hỗ trợ cả hai kiểu gửi **At Most Once** và **At Least Once**. Nó chạy ở mọi nơi, từ các server lớn và cloud instance tới các edge gateway và thiết bị Internet of Things.

#### Cài đặt

Để bắt đầu xây dựng microservice dựa trên NATS, trước tiên hãy cài package cần thiết:

[[CODE:1]]

> warning **Warning** Từ NestJS v12, transporter NATS nhắm tới **NATS v3** và dùng driver `@nats-io/transport-node`. Nếu bạn đang nâng cấp từ phiên bản cũ hơn, hãy gỡ package `nats` cũ (`npm uninstall nats`) và cài `@nats-io/transport-node` thay vào đó. Xem [hướng dẫn migration](/migration-guide#nats-v3) để biết chi tiết.

#### Tổng quan

Để dùng transporter NATS, hãy truyền options object sau cho method `createMicroservice()`:

[[CODE:2]]

> info **Hint** Enum `Transport` được import từ package `@nestjs/microservices`.

#### Tùy chọn

Object `options` phụ thuộc vào transporter được chọn. Transporter <strong>NATS</strong> cung cấp các [tùy chọn kết nối của NATS](https://github.com/nats-io/nats.js/blob/main/core/README.md#connecting-to-a-nats-server), cùng các thuộc tính sau:

<table>
  <tr>
    <td><code>queue</code></td>
    <td>Queue group mà server của bạn subscribe cùng (để <code>undefined</code> để bỏ qua thiết lập này). Đọc thêm về queue group của NATS <a href="/microservices/nats#queue-groups">bên dưới</a>.</td>
  </tr>
  <tr>
    <td><code>gracefulShutdown</code></td>
    <td>Bật graceful shutdown. Khi bật, trước tiên server unsubscribe khỏi mọi subject, rồi chờ <code>gracePeriod</code> trước khi đóng kết nối. Mặc định là <code>false</code>.</td>
  </tr>
  <tr>
    <td><code>gracePeriod</code></td>
    <td>Thời gian tính bằng mili giây cần chờ sau khi unsubscribe khỏi mọi subject khi <code>gracefulShutdown</code> được bật. Mặc định là <code>10000</code> ms.</td>
  </tr>
  <tr>
    <td><code>headers</code></td>
    <td>Các header được thêm vào mọi message mà một client gửi đi (xem <a href="/microservices/nats#record-builders">record builder</a>).</td>
  </tr>
</table>

#### Client

Như với các transporter microservice khác, bạn có <a href="/microservices/basics#client-producer-class">nhiều lựa chọn</a> để tạo một instance `ClientProxy` cho NATS.

Một cách để tạo instance là dùng `ClientsModule`. Import nó và dùng method `register()` của nó để truyền một options object có cùng các thuộc tính như ở trên cho method `createMicroservice()`, cộng thêm thuộc tính `name` dùng làm injection token. Đọc thêm về `ClientsModule` trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

[[CODE:3]]

Bạn cũng có thể tạo client bằng `ClientProxyFactory` hoặc decorator `@Client()`. Cả hai đều được mô tả trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

#### Request-response

Với kiểu message [request-response](/microservices/basics#request-response), transporter NATS không dùng API [Request-Reply](https://docs.nats.io/nats-concepts/reqreply) có sẵn của NATS. Thay vào đó, client publish một "request" trên một subject cho trước bằng method `publish()` kèm một tên reply subject duy nhất. Bên phản hồi lắng nghe trên subject đó và gửi response tới reply subject. Các reply subject được định tuyến ngược về bên yêu cầu một cách động, bất kể vị trí của mỗi bên.

#### Event-based

Với kiểu message [event-based](/microservices/basics#event-based), transporter NATS dùng cơ chế [Publish-Subscribe](https://docs.nats.io/nats-concepts/pubsub) có sẵn của NATS. Một publisher gửi một message trên một subject, và mọi subscriber đang hoạt động lắng nghe trên subject đó đều nhận được message. Subscriber cũng có thể đăng ký quan tâm tới các subject có [wildcard](#wildcards). Pattern một-nhiều này đôi khi được gọi là fan-out.

#### Queue group

NATS cung cấp một tính năng cân bằng tải có sẵn gọi là [distributed queue](https://docs.nats.io/nats-concepts/queue). Để tạo một queue subscription, hãy dùng thuộc tính `queue` như sau:

[[CODE:4]]

#### Context

Trong các tình huống phức tạp hơn, bạn có thể cần thêm thông tin về request đi vào. Với transporter NATS, bạn có thể truy cập object `NatsContext`.

[[CODE:5]]

> info **Hint** `@Payload()`, `@Ctx()` và `NatsContext` được import từ package `@nestjs/microservices`.

#### Wildcard

Một subscription có thể nhắm tới một subject cụ thể, hoặc có thể chứa wildcard.

[[CODE:6]]

#### Record builder

Để cấu hình các tùy chọn của message, hãy dùng class `NatsRecordBuilder`. Nó hoạt động cho cả luồng request-response lẫn event-based. Ví dụ, để thêm header `x-version`, hãy dùng method `setHeaders()`:

[[CODE:7]]

> info **Hint** Class `NatsRecordBuilder` được export từ package `@nestjs/microservices`.

Ở phía server, bạn có thể đọc các header này qua `NatsContext`:

[[CODE:8]]

Để cấu hình header cho mọi request do một client gửi đi, hãy truyền chúng làm tùy chọn cho `ClientProxyFactory`:

[[CODE:9]]

Header được đặt trên một record được ưu tiên hơn tùy chọn `headers` ở cấp client.

Bắt đầu từ NestJS v12.1.3, một message handler cũng có thể trả về một record. Nest gửi dữ liệu của record làm reply và các header của record làm header của message reply:

[[CODE:10]]

#### Custom serializer và deserializer

Bắt đầu từ NestJS v12, Nest serialize các packet NATS thành chuỗi JSON, và các custom deserializer cho NATS nhận toàn bộ object message của NATS thay vì một `Uint8Array` thô. Nếu bạn đã viết một custom deserializer, hãy đọc payload qua `msg.json()` thay vì tự decode các byte:

[[CODE:11]]

#### Cập nhật trạng thái instance

Để nhận cập nhật real-time về kết nối và trạng thái của instance driver bên dưới, hãy subscribe stream `status`. Stream này cung cấp các cập nhật trạng thái riêng của driver được chọn. Với driver NATS, stream `status` phát ra các event `connected`, `disconnected` và `reconnecting`.

[[CODE:12]]

> info **Hint** Type `NatsStatus` được import từ package `@nestjs/microservices`.

Tương tự, bạn có thể subscribe stream `status` của server để nhận thông báo về trạng thái của server.

[[CODE:13]]

#### Lắng nghe các event của NATS

Trong một số trường hợp, bạn có thể muốn lắng nghe các event nội bộ do microservice phát ra. Transporter NATS phát ra các event `disconnect`, `reconnect` và `update` (server trong cluster được thêm hoặc gỡ bỏ). Ví dụ, bạn có thể lắng nghe event `disconnect` để kích hoạt thêm các thao tác khi mất kết nối. Để làm vậy, hãy dùng method `on()`, như bên dưới:

[[CODE:14]]

Tương tự, bạn có thể lắng nghe các event nội bộ của server:

[[CODE:15]]

> info **Hint** Type `NatsEvents` được import từ package `@nestjs/microservices`.

#### Truy cập driver bên dưới

Với các use case nâng cao hơn, bạn có thể cần truy cập instance driver bên dưới, ví dụ để tự đóng kết nối hoặc dùng các method riêng của driver. Tuy nhiên, trong hầu hết các trường hợp, bạn **không cần** truy cập trực tiếp driver.

Để làm vậy, hãy dùng method `unwrap()`, method này trả về instance driver bên dưới. Generic type parameter chỉ định type của instance driver mà bạn mong đợi.

[[CODE:16]]

Tương tự, bạn có thể truy cập instance driver bên dưới của server:

[[CODE:17]]
