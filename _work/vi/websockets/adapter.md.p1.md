### Adapter

Module WebSocket không phụ thuộc nền tảng, nên bạn có thể dùng library của riêng mình (hoặc thậm chí một phần hiện thực gốc) bằng cách implement interface `WebSocketAdapter`. Interface này yêu cầu các method được mô tả trong bảng sau:

<table>
  <tr>
    <td><code>create</code></td>
    <td>Tạo một socket server instance dựa trên các tham số được truyền vào</td>
  </tr>
  <tr>
    <td><code>bindClientConnect</code></td>
    <td>Gắn event kết nối của client</td>
  </tr>
  <tr>
    <td><code>bindClientDisconnect</code></td>
    <td>Gắn event ngắt kết nối của client (tùy chọn)</td>
  </tr>
  <tr>
    <td><code>bindMessageHandlers</code></td>
    <td>Gắn message đi vào với message handler tương ứng</td>
  </tr>
  <tr>
    <td><code>close</code></td>
    <td>Kết thúc một server instance</td>
  </tr>
</table>

#### Mở rộng socket.io

Package [socket.io](https://github.com/socketio/socket.io) được bọc trong class `IoAdapter`. Bạn có thể kế thừa class này để tăng cường chức năng cơ bản của adapter. Ví dụ, giả sử ứng dụng của bạn phải broadcast event qua nhiều instance của web service đứng sau load balancer. Để hỗ trợ điều này, hãy kế thừa `IoAdapter` và override method duy nhất chịu trách nhiệm khởi tạo các socket.io server mới. Trước tiên, hãy cài các package cần thiết.

> warning **Warning** Để dùng socket.io với nhiều instance đứng sau load balancer, bạn phải hoặc tắt polling bằng cách đặt `transports: ['websocket']` trong cấu hình socket.io của client, hoặc bật định tuyến dựa trên cookie (sticky session) trong load balancer. Chỉ Redis thôi là chưa đủ. Xem [Enabling sticky session](https://socket.io/docs/v4/using-multiple-nodes/#enabling-sticky-session) trong tài liệu socket.io để biết thêm thông tin.

[[CODE:1]]

Khi đã cài các package, hãy tạo một class `RedisIoAdapter`.

[[CODE:2]]

Sau đó chuyển sang dùng Redis adapter vừa tạo.

[[CODE:3]]

#### Library ws

Một adapter khác có sẵn là `WsAdapter`, đóng vai trò proxy giữa framework và library [ws](https://github.com/websockets/ws) nhanh và đã được test kỹ lưỡng. Adapter này tương thích hoàn toàn với WebSocket gốc của trình duyệt và nhanh hơn package socket.io. Tuy nhiên, nó cung cấp sẵn ít tính năng hơn đáng kể, những tính năng mà nhiều ứng dụng cũng không cần tới.

> info **Hint** Library `ws` không hỗ trợ namespace (các kênh giao tiếp được `socket.io` phổ biến), và `WsAdapter` sẽ throw lỗi nếu bạn đặt tùy chọn `namespace`. Để mô phỏng tính năng này, hãy mount nhiều `ws` server trên các path khác nhau (ví dụ `@WebSocketGateway({{ '{' }} path: '/users' {{ '}' }})`).

Để dùng `ws`, trước tiên hãy cài package cần thiết:

[[CODE:4]]

Khi đã cài package, hãy đổi adapter:

[[CODE:5]]

> info **Hint** `WsAdapter` được import từ `@nestjs/platform-ws`.

`WsAdapter` xử lý message theo định dạng `{{ '{' }} event: string, data: any {{ '}' }}`. Để nhận và xử lý message theo định dạng khác, hãy cấu hình một message parser chuyển chúng sang định dạng này.

[[CODE:6]]

Ngoài ra, bạn có thể đặt message parser sau khi tạo adapter bằng method `setMessageParser()`.

#### Nâng cao (custom adapter)

Để minh họa, chúng ta sẽ tích hợp thủ công library [ws](https://github.com/websockets/ws). Như đã nói, đã có sẵn một adapter cho library này: class `WsAdapter` được cung cấp từ package `@nestjs/platform-ws`. Một phần hiện thực đơn giản hóa có thể trông như thế này:

[[CODE:7]]

> info **Hint** Để dùng library [ws](https://github.com/websockets/ws), hãy dùng `WsAdapter` có sẵn thay vì tự tạo adapter.

Sau đó thiết lập custom adapter bằng method `useWebSocketAdapter()`:

[[CODE:8]]

#### Ví dụ

Một ví dụ chạy được dùng `WsAdapter` có trong [sample 16-gateways-ws](https://github.com/nestjs/nest/tree/master/sample/16-gateways-ws).
