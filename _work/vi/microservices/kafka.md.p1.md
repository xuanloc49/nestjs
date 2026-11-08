### Kafka

[Kafka](https://kafka.apache.org/) là một nền tảng streaming phân tán, mã nguồn mở, với ba khả năng chính:

- Publish và subscribe các stream record, tương tự một message queue hay hệ thống messaging doanh nghiệp.
- Lưu trữ các stream record một cách bền vững và chịu lỗi.
- Xử lý các stream record ngay khi chúng xảy ra.

Dự án Kafka hướng tới việc cung cấp một nền tảng thống nhất, throughput cao, độ trễ thấp để xử lý các luồng dữ liệu real-time. Nó tích hợp với Apache Storm và Spark để phân tích dữ liệu streaming real-time.

#### Cài đặt

Để bắt đầu xây dựng microservice dựa trên Kafka, trước tiên hãy cài package cần thiết:

[[CODE:1]]

#### Tổng quan

Như với các phần hiện thực lớp transport microservice khác của Nest, bạn chọn transporter Kafka bằng thuộc tính `transport` của options object được truyền cho method `createMicroservice()`, cùng một thuộc tính `options` tùy chọn, như bên dưới:

[[CODE:2]]

> info **Hint** Enum `Transport` được import từ package `@nestjs/microservices`.

#### Tùy chọn

Thuộc tính `options` phụ thuộc vào transporter được chọn. Transporter <strong>Kafka</strong> cung cấp các thuộc tính sau.

<table>
  <tr>
    <td><code>client</code></td>
    <td>Các tùy chọn cấu hình client (xem
      <a
        href="https://kafka.js.org/docs/configuration"
        rel="nofollow"
        target="_blank"
        >cấu hình client của KafkaJS</a
      >)</td>
  </tr>
  <tr>
    <td><code>consumer</code></td>
    <td>Các tùy chọn cấu hình consumer (xem
      <a
        href="https://kafka.js.org/docs/consuming#a-name-options-a-options"
        rel="nofollow"
        target="_blank"
        >tùy chọn consumer của KafkaJS</a
      >)</td>
  </tr>
  <tr>
    <td><code>run</code></td>
    <td>Các tùy chọn được truyền cho method <code>run()</code> của consumer (xem
      <a
        href="https://kafka.js.org/docs/consuming"
        rel="nofollow"
        target="_blank"
        >tiêu thụ message với KafkaJS</a
      >)</td>
  </tr>
  <tr>
    <td><code>subscribe</code></td>
    <td>Các tùy chọn được truyền cho method <code>subscribe()</code> của consumer, trừ <code>topics</code>, thứ mà Nest suy ra từ các pattern đã đăng ký (xem
      <a
        href="https://kafka.js.org/docs/consuming#frombeginning"
        rel="nofollow"
        target="_blank"
        >KafkaJS fromBeginning</a
      >)</td>
  </tr>
  <tr>
    <td><code>producer</code></td>
    <td>Các tùy chọn cấu hình producer (xem
      <a
        href="https://kafka.js.org/docs/producing#options"
        rel="nofollow"
        target="_blank"
        >tùy chọn producer của KafkaJS</a
      >)</td>
  </tr>
  <tr>
    <td><code>send</code></td>
    <td>Các tùy chọn được truyền cho method <code>send()</code> của producer, trừ <code>topic</code> và <code>messages</code> (xem
      <a
        href="https://kafka.js.org/docs/producing#options"
        rel="nofollow"
        target="_blank"
        >gửi message với KafkaJS</a
      >)</td>
  </tr>
  <tr>
    <td><code>parser</code></td>
    <td>Các tùy chọn của parser dùng để decode message đi vào: <code>keepBinary</code> truyền giá trị của message cho handler dưới dạng buffer thay vì decode chúng (<code>boolean</code>), và <code>maxMessageSize</code> là kích thước tính bằng byte, sau khi giải nén, mà một message vượt quá sẽ bị bỏ qua thay vì decode. Mặc định là <code>16777216</code> (16 MiB) (<code>number</code>)</td>
  </tr>
  <tr>
    <td><code>producerOnlyMode</code></td>
    <td>Chỉ dành cho client. Bỏ qua việc đăng ký consumer group để client chỉ đóng vai trò producer (<code>boolean</code>)</td>
  </tr>
  <tr>
    <td><code>postfixId</code></td>
    <td>Hậu tố được nối vào giá trị <code>clientId</code> và <code>groupId</code>. Mặc định là <code>'-server'</code> ở server và <code>'-client'</code> ở client (<code>string</code>)</td>
  </tr>
</table>

#### Client

Kafka hơi khác so với các transporter microservice khác: thay vì type `ClientProxy`, bạn dùng `ClientKafkaProxy`.

Như với các transporter microservice khác, bạn có [nhiều lựa chọn](/microservices/basics#client-producer-class) để tạo một instance `ClientKafkaProxy`.

Một lựa chọn là `ClientsModule`. Import nó và dùng method `register()` của nó để truyền một options object có cùng các thuộc tính như ở trên cho method `createMicroservice()`, cộng thêm thuộc tính `name` dùng làm injection token. Xem [phần client trong trang tổng quan về microservice](/microservices/basics#client-producer-class) để tìm hiểu thêm về `ClientsModule`.

[[CODE:3]]

Bạn cũng có thể tạo client bằng `ClientProxyFactory` hoặc decorator `@Client()`, cả hai đều được mô tả trong [trang tổng quan về microservice](/microservices/basics#client-producer-class).

Dùng decorator `@Client()` như sau:

[[CODE:4]]

#### Message pattern

Message pattern của microservice Kafka dùng hai topic cho kênh request và kênh reply. Method `ClientKafkaProxy.send()` gửi message kèm một [return address](https://www.enterpriseintegrationpatterns.com/patterns/messaging/ReturnAddress.html) bằng cách gắn một [correlation id](https://www.enterpriseintegrationpatterns.com/patterns/messaging/CorrelationIdentifier.html), reply topic và reply partition vào message request. Điều này yêu cầu instance `ClientKafkaProxy` phải subscribe reply topic và được gán ít nhất một partition trước khi gửi message.

Do đó, bạn cần ít nhất một partition của reply topic cho mỗi ứng dụng Nest đang chạy. Ví dụ, nếu bạn chạy 4 ứng dụng Nest nhưng reply topic chỉ có 3 partition, 1 trong các ứng dụng Nest sẽ thất bại khi nó cố gửi message.

Khi các instance `ClientKafkaProxy` mới khởi động, chúng tham gia consumer group và subscribe các topic tương ứng. Điều này kích hoạt một lần rebalance các partition của topic được gán cho các consumer trong group.

Thông thường, các partition của topic được gán bằng round-robin assigner, assigner này gán partition cho một tập consumer được sắp xếp theo tên consumer, những tên được đặt ngẫu nhiên khi ứng dụng khởi động. Tuy nhiên, khi một consumer mới tham gia consumer group, nó có thể nằm ở bất kỳ vị trí nào trong tập đó. Khi đó các consumer đã có từ trước nằm sau consumer mới có thể được gán các partition khác, và những consumer đó sẽ mất các message response của những request được gửi trước lần rebalance.

Để ngăn các consumer `ClientKafkaProxy` mất message response, Nest dùng một custom partition assigner có sẵn. Trong một lần rebalance, nó cho phép mỗi consumer đã có giữ nguyên reply partition đã được gán trước đó, và phân phối các partition còn lại cho các consumer khác.

#### Pattern dạng regular expression

KafkaJS hỗ trợ subscribe topic bằng regular expression. Bắt đầu từ NestJS v12, bạn có thể truyền trực tiếp một `RegExp` cho `@MessagePattern()` hoặc `@EventPattern()`. Nest giữ nguyên pattern, chuyển nó tới lời gọi `subscribe()` của KafkaJS, và fallback sang việc so khớp regular expression khi resolve handler cho một topic đi vào.

[[CODE:5]]

Điều này subscribe handler vào mọi topic khớp với biểu thức (`hero.kill.dragon`, `hero.rescue.villager`, v.v.) mà không cần đăng ký từng topic một cách tường minh. Dùng `context.getTopic()` để biết topic nào đã gửi message.

> info **Hint** Pattern dạng regular expression là khả năng riêng của Kafka; các transporter khác vẫn so khớp pattern theo giá trị chính xác. Nest reset `lastIndex` trước khi so khớp, nên các biểu thức global (`/g`) và sticky (`/y`) không gây ra việc so khớp trượt do giữ trạng thái.

#### Subscribe response của message

> warning **Note** Phần này chỉ liên quan nếu bạn dùng kiểu message [request-response](/microservices/basics#request-response) (decorator `@MessagePattern()` và method `ClientKafkaProxy.send()`). Việc subscribe response topic là không cần thiết với giao tiếp [event-based](/microservices/basics#event-based) (decorator `@EventPattern()` và method `ClientKafkaProxy.emit()`).

`ClientKafkaProxy` cung cấp method `subscribeToResponseOf()`, nhận tên topic của một request làm tham số và thêm tên reply topic được suy ra vào một tập các reply topic. Method này là bắt buộc khi hiện thực message pattern.

[[CODE:6]]

Nếu instance `ClientKafkaProxy` được tạo bất đồng bộ, hãy gọi method `subscribeToResponseOf()` trước khi gọi method `connect()`.

[[CODE:7]]

#### Message đi vào

Nest nhận các message Kafka đi vào dưới dạng object có các thuộc tính `key`, `value` và `headers` với giá trị có type `Buffer`. Nest parse các giá trị này bằng cách chuyển buffer thành chuỗi. Nếu một chuỗi "trông giống object" (tức là bắt đầu bằng dấu ngoặc nhọn hoặc ngoặc vuông), Nest cố parse nó thành JSON, trừ các header `kafka_correlationId`, `kafka_replyTopic` và `kafka_replyPartition` mà nó dùng để định tuyến reply, những header này luôn được giữ dưới dạng chuỗi. Sau đó `value` được truyền cho handler tương ứng.

Nest không decode một message lớn hơn 16 MiB sau khi giải nén, tính cả key, header và, trừ khi đặt `parser.keepBinary`, cả value của nó. Nó log và bỏ qua message đó, để offset của nó được commit, và một `ClientKafkaProxy` sẽ làm thất bại request mà reply như vậy trả lời. Để thay đổi giới hạn, hãy đặt tùy chọn `parser.maxMessageSize`.

#### Message đi ra

Nest serialize các message Kafka đi ra trước khi publish event hoặc gửi message. Việc serialize áp dụng cho các tham số được truyền cho method `emit()` và `send()` của `ClientKafkaProxy`, và cho các giá trị trả về từ một method `@MessagePattern()`. Nó "stringify" các giá trị không phải chuỗi hay buffer bằng `JSON.stringify()` hoặc method `toString()` của prototype.

[[CODE:8]]

> info **Hint** `@Payload()` được import từ package `@nestjs/microservices`.

Bạn cũng có thể gắn key cho message đi ra bằng cách truyền một object có các thuộc tính `key` và `value`. Việc gắn key cho message rất quan trọng để đáp ứng [yêu cầu co-partitioning](https://docs.confluent.io/current/ksql/docs/developer-guide/partition-data.html#co-partitioning-requirements).

[[CODE:9]]

Các message được truyền theo định dạng này cũng có thể chứa các header tùy chỉnh được đặt trong thuộc tính `headers`. Giá trị của header phải có type `string` hoặc `Buffer`, và một message có thể mang tối đa 10.000 header, một giá trị mảng được tính theo từng phần tử. Nest không gửi một message có nhiều hơn số đó: `emit()` và `send()` thất bại, và một reply của `@MessagePattern()` sẽ được log và bỏ đi.

[[CODE:10]]

#### Event-based

Dù cách request-response lý tưởng cho việc trao đổi message giữa các service, nó lại kém phù hợp khi kiểu message của bạn là event-based (kiểu lý tưởng cho Kafka), tức là khi bạn muốn publish event **mà không chờ response**. Trong trường hợp đó, bạn không muốn chịu chi phí duy trì hai topic mà request-response cần.

Xem [Tổng quan: Event-based](/microservices/basics#event-based) và [Tổng quan: Publish event](/microservices/basics#publishing-events) để tìm hiểu thêm.

#### Context

Trong các tình huống phức tạp hơn, bạn có thể cần thêm thông tin về request đi vào. Khi dùng transporter Kafka, bạn có thể truy cập object `KafkaContext`.

[[CODE:11]]

> info **Hint** `@Payload()`, `@Ctx()` và `KafkaContext` được import từ package `@nestjs/microservices`.

Để truy cập object `IncomingMessage` gốc của Kafka, hãy dùng method `getMessage()` của object `KafkaContext`, như sau:

[[CODE:12]]

Object `IncomingMessage` thỏa mãn interface sau:

[[CODE:13]]

Nếu handler của bạn mất nhiều thời gian để xử lý mỗi message, hãy cân nhắc dùng callback `heartbeat`. Để lấy hàm `heartbeat`, hãy dùng method `getHeartbeat()` của `KafkaContext`, như sau:

[[CODE:14]]

#### Quy ước đặt tên

Các thành phần microservice Kafka nối thêm một mô tả vai trò của chúng vào các tùy chọn `client.clientId` và `consumer.groupId` để tránh xung đột giữa thành phần client và server của microservice Nest. Mặc định, các thành phần `ClientKafkaProxy` nối thêm `-client` và các thành phần `ServerKafka` nối thêm `-server` vào cả hai tùy chọn. Các comment bên dưới cho thấy các giá trị được cung cấp được biến đổi thế nào.

[[CODE:15]]

Và với client:

[[CODE:16]]

> info **Hint** Để thay đổi hậu tố được nối thêm, hãy đặt tùy chọn `postfixId`. Để tùy chỉnh sâu hơn quy ước đặt tên client và consumer, hãy kế thừa các class `ClientKafka` và `ServerKafka` trong custom provider của riêng bạn và override constructor.

Vì message pattern của microservice Kafka dùng hai topic cho kênh request và kênh reply, reply pattern được suy ra từ topic của request. Mặc định, tên của reply topic là tên topic của request được nối thêm `.reply`.

[[CODE:17]]

> info **Hint** Để tùy chỉnh quy ước đặt tên reply topic, hãy kế thừa class `ClientKafka` trong custom provider của riêng bạn và override method `getResponsePatternName()`.

#### Exception có thể retry

Như với các transporter khác, các exception chưa được xử lý được tự động chuyển sang một định dạng "thân thiện với người dùng". Tuy nhiên, trong một số trường hợp đặc biệt, bạn có thể muốn bỏ qua cơ chế này và để driver `kafkajs` tiêu thụ exception thay vào đó. Throw một exception trong khi xử lý một message sẽ chỉ thị `kafkajs` **retry** nó (gửi lại nó), nghĩa là dù message (hoặc event) handler đã được kích hoạt, offset sẽ không được commit lên Kafka.

> warning **Warning** Với event handler (giao tiếp event-based), mặc định mọi exception chưa được xử lý đều được coi là **exception có thể retry**.

Với message handler, hãy dùng class riêng `KafkaRetriableException`, như sau:

[[CODE:18]]

> info **Hint** Class `KafkaRetriableException` được export từ package `@nestjs/microservices`.

> warning **Warning** Nest chỉ xử lý một message như một request khi nó mang các header `kafka_correlationId` và `kafka_replyTopic` mà `ClientKafkaProxy.send()` thêm vào. Mọi message khác, chẳng hạn một message được ghi bởi một producer không phải Nest, sẽ được xử lý như một event, kể cả khi nó tới một handler `@MessagePattern()`: các exception chưa được xử lý của nó có thể retry, và message tiếp theo của partition chỉ được xử lý khi stream mà handler trả về hoàn tất. Với các topic mà producer khác ghi vào, hãy đảm bảo message handler trả về stream có hoàn tất, và xử lý các message mà chúng không thể xử lý thay vì throw, trừ khi những message đó cần được gửi lại.

#### Xử lý exception tùy chỉnh

Ngoài các cơ chế xử lý lỗi mặc định, bạn có thể tạo một custom exception filter cho các event Kafka để quản lý logic retry. Ví dụ, filter bên dưới bỏ qua một event có vấn đề sau một số lần retry có thể cấu hình:

[[CODE:19]]

Filter này retry việc xử lý một event Kafka tối đa một số lần có thể cấu hình. Khi một exception xảy ra, nó publish lại message lên cùng topic với header `retry-count` được tăng lên, rồi commit offset hiện tại. Khi đạt số lần retry tối đa, nó gọi `skipHandler` tùy chỉnh (nếu được cung cấp) và commit offset, bỏ qua event có vấn đề. Điều này cho phép các event tiếp theo được xử lý mà không bị gián đoạn.

Bạn có thể đăng ký filter này ở phạm vi global hoặc ở cấp controller. Nó cần một instance Kafka producer:

[[CODE:20]]

[[CODE:21]]

Hãy đảm bảo cung cấp Kafka producer trong module của bạn:

[[CODE:22]]

#### Commit offset

Commit offset là việc thiết yếu khi làm việc với Kafka. Mặc định, message được commit tự động sau một khoảng thời gian nhất định (xem [tài liệu autocommit của KafkaJS](https://kafka.js.org/docs/consuming#autocommit)). `KafkaContext` cho bạn truy cập consumer đang hoạt động để tự commit offset. Consumer chính là consumer của KafkaJS và hoạt động giống [phần hiện thực gốc của KafkaJS](https://kafka.js.org/docs/consuming#manual-committing).

[[CODE:23]]

Để tắt auto-commit, hãy đặt `autoCommit: false` trong cấu hình `run`, như sau:

[[CODE:24]]

#### Cập nhật trạng thái instance

Để nhận cập nhật real-time về kết nối và trạng thái của instance driver bên dưới, hãy subscribe stream `status`. Stream này cung cấp các cập nhật trạng thái riêng của driver được chọn. Với driver Kafka, stream `status` phát ra các event `connected`, `disconnected`, `rebalancing`, `crashed` và `stopped`.

[[CODE:25]]

> info **Hint** Type `KafkaStatus` được import từ package `@nestjs/microservices`.

Tương tự, bạn có thể subscribe stream `status` của server để nhận thông báo về trạng thái của server:

[[CODE:26]]

#### Producer và consumer bên dưới

Với các use case nâng cao hơn, bạn có thể cần truy cập các instance producer và consumer bên dưới, ví dụ để tự đóng kết nối hoặc dùng các method riêng của driver. Tuy nhiên, trong hầu hết các trường hợp, bạn **không cần** truy cập trực tiếp driver.

Để làm vậy, hãy dùng các thuộc tính `producer` và `consumer` mà instance `ClientKafkaProxy` cung cấp.

[[CODE:27]]
