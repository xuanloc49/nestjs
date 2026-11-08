### MQTT

[MQTT](https://mqtt.org/) (Message Queuing Telemetry Transport) là một giao thức messaging mã nguồn mở, gọn nhẹ, được tối ưu cho độ trễ thấp. Nó cung cấp một cách có thể mở rộng và tiết kiệm chi phí để kết nối các thiết bị theo mô hình **publish/subscribe**. Một hệ thống giao tiếp xây trên MQTT gồm server publish, một broker, và một hoặc nhiều client. Giao thức được thiết kế cho các thiết bị hạn chế tài nguyên và cho các mạng băng thông thấp, độ trễ cao hoặc không ổn định.

#### Cài đặt

Để bắt đầu xây dựng microservice dựa trên MQTT, trước tiên hãy cài package cần thiết:

[[CODE:1]]

#### Tổng quan

Để dùng transporter MQTT, hãy truyền options object sau cho method `createMicroservice()`:

[[CODE:2]]

> info **Hint** Enum `Transport` được import từ package `@nestjs/microservices`.

#### Tùy chọn

Object `options` phụ thuộc vào transporter được chọn. Transporter <strong>MQTT</strong> cung cấp các [tùy chọn client của MQTT.js](https://github.com/mqttjs/MQTT.js/#mqttclientstreambuilder-options), cũng như các thuộc tính `url`, `subscribeOptions` (xem [Quality of Service](#quality-of-service-qos)) và `userProperties` (xem [record builder](#record-builders)). Ở phía server, thuộc tính `maxConnectionAttempts` giới hạn số lần thử thiết lập kết nối ban đầu (mặc định: `-1`, tức không giới hạn). Giới hạn này không áp dụng cho các lần kết nối lại sau khi server đã kết nối.

#### Client

Như với các transporter microservice khác, bạn có <a href="/microservices/basics#client-producer-class">nhiều lựa chọn</a> để tạo một instance `ClientProxy` cho MQTT.

Một cách để tạo instance là dùng `ClientsModule`. Import nó và dùng method `register()` của nó để truyền một options object có cùng các thuộc tính như ở trên cho method `createMicroservice()`, cộng thêm thuộc tính `name` dùng làm injection token. Đọc thêm về `ClientsModule` trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

[[CODE:3]]

Bạn cũng có thể tạo client bằng `ClientProxyFactory` hoặc decorator `@Client()`. Cả hai đều được mô tả trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

#### Context

Trong các tình huống phức tạp hơn, bạn có thể cần thêm thông tin về request đi vào. Với transporter MQTT, bạn có thể truy cập object `MqttContext`.

[[CODE:4]]

> info **Hint** `@Payload()`, `@Ctx()` và `MqttContext` được import từ package `@nestjs/microservices`.

Để truy cập [packet](https://github.com/mqttjs/mqtt-packet) MQTT gốc, hãy dùng method `getPacket()` của object `MqttContext`:

[[CODE:5]]

#### Wildcard

Một subscription có thể nhắm tới một topic cụ thể, hoặc có thể chứa wildcard. Có hai wildcard: `+` khớp với một cấp topic, và `#` khớp với nhiều cấp topic.

[[CODE:6]]

#### Quality of Service (QoS)

Mặc định, các subscription được tạo bằng decorator `@MessagePattern()` và `@EventPattern()` dùng QoS 0. Nếu bạn cần QoS cao hơn, hãy đặt nó ở phạm vi global bằng khối `subscribeOptions` khi thiết lập kết nối:

[[CODE:7]]

#### QoS theo từng pattern

Bạn có thể ghi đè QoS của subscription cho từng pattern riêng bằng cách truyền thuộc tính `qos` trong object extras, tham số thứ hai của decorator `@MessagePattern()` hoặc `@EventPattern()`. Các pattern không có `qos` riêng sẽ dùng giá trị global `subscribeOptions.qos`.

[[CODE:8]]

#### Record builder

Để cấu hình các tùy chọn của message (điều chỉnh mức QoS, đặt cờ Retain hoặc DUP, hoặc thêm thuộc tính vào payload), hãy dùng class `MqttRecordBuilder`. Ví dụ, record sau đặt QoS thành `1` bằng method `setQoS()` và thêm một user property bằng method `setProperties()`:

[[CODE:9]]

> info **Hint** Class `MqttRecordBuilder` được export từ package `@nestjs/microservices`.

Ở phía server, bạn có thể đọc các tùy chọn này qua `MqttContext`:

[[CODE:10]]

Để cấu hình user property cho mọi request do một client gửi đi, hãy truyền chúng làm tùy chọn cho `ClientProxyFactory`:

[[CODE:11]]

Bắt đầu từ NestJS v12.1.3, một message handler cũng có thể trả về một record. Nest gửi dữ liệu của record làm reply và áp dụng các tùy chọn của record (ví dụ mức QoS và các property) cho message reply:

[[CODE:12]]

#### Cập nhật trạng thái instance

Để nhận cập nhật real-time về kết nối và trạng thái của instance driver bên dưới, hãy subscribe stream `status`. Stream này cung cấp các cập nhật trạng thái riêng của driver được chọn. Với driver MQTT, stream `status` phát ra các event `connected`, `disconnected`, `reconnecting` và `closed`.

[[CODE:13]]

> info **Hint** Type `MqttStatus` được import từ package `@nestjs/microservices`.

Tương tự, bạn có thể subscribe stream `status` của server để nhận thông báo về trạng thái của server.

[[CODE:14]]

#### Lắng nghe các event của MQTT

Trong một số trường hợp, bạn có thể muốn lắng nghe các event nội bộ do microservice phát ra. Ví dụ, bạn có thể lắng nghe event `error` để kích hoạt thêm các thao tác khi có lỗi xảy ra. Để làm vậy, hãy dùng method `on()`, như bên dưới:

[[CODE:15]]

Tương tự, bạn có thể lắng nghe các event nội bộ của server:

[[CODE:16]]

> info **Hint** Type `MqttEvents` được import từ package `@nestjs/microservices`.

Bắt đầu từ NestJS v12.1.2, các listener được đăng ký bằng method `on()` của client vẫn được giữ cho tới khi bạn gọi `close()`, nên chúng cũng được gắn vào MQTT client mới được tạo ở lời gọi `send()` hoặc `emit()` tiếp theo sau khi client trước đã đóng mà không kết nối lại (ví dụ khi `reconnectPeriod` là `0`). Các lần đăng ký không được khử trùng lặp, nên hãy đăng ký mỗi listener một lần thay vì đăng ký lại từ callback của nó hoặc sau mỗi lần kết nối lại.

#### Truy cập driver bên dưới

Với các use case nâng cao hơn, bạn có thể cần truy cập instance driver bên dưới, ví dụ để tự đóng kết nối hoặc dùng các method riêng của driver. Tuy nhiên, trong hầu hết các trường hợp, bạn **không cần** truy cập trực tiếp driver.

Để làm vậy, hãy dùng method `unwrap()`, method này trả về instance driver bên dưới. Generic type parameter chỉ định type của instance driver mà bạn mong đợi.

[[CODE:17]]

Tương tự, bạn có thể truy cập instance driver bên dưới của server:

[[CODE:18]]
