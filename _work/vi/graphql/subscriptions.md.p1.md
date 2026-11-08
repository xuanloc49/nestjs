### Subscription

Ngoài việc lấy dữ liệu bằng query và thay đổi dữ liệu bằng mutation, đặc tả GraphQL còn hỗ trợ loại operation thứ ba, gọi là `subscription`. GraphQL subscription đẩy dữ liệu từ server tới những client chọn lắng nghe các message real-time. Giống như query, subscription chỉ định một tập field sẽ được gửi tới client. Tuy nhiên, thay vì trả về ngay một kết quả duy nhất, chúng mở một kênh, và server gửi kết quả tới client mỗi khi một event cụ thể xảy ra.

Một use case phổ biến của subscription là thông báo cho client về các event cụ thể, chẳng hạn khi một object mới được tạo hoặc các field được cập nhật (xem [Subscription](https://www.apollographql.com/docs/react/data/subscriptions) trong tài liệu Apollo).

#### Bật subscription với Apollo driver

Subscription được truyền qua WebSocket bởi package [graphql-ws](https://github.com/enisdenjo/graphql-ws). `@nestjs/graphql` đã phụ thuộc vào nó, nhưng hãy cài nó trong project của bạn nữa nếu bạn import trực tiếp từ nó (ví dụ type `Context` được dùng trong [Xác thực qua WebSocket](/graphql/subscriptions#authentication-over-websockets)):

[[CODE:1]]

Sau đó bật transport:

[[CODE:2]]

> warning **Warning** Hỗ trợ cho `subscriptions-transport-ws` đã bị **gỡ bỏ** trong `@nestjs/graphql` v14. Package này không còn là dependency, và key `'subscriptions-transport-ws'` không còn được chấp nhận trong options object `subscriptions`. Nếu bạn đang nâng cấp, hãy thay key đó bằng `'graphql-ws'` và cập nhật client sang giao thức mới hơn. Hai giao thức không tương thích với nhau ở tầng truyền tải, nên các client vẫn dùng `subscriptions-transport-ws` sẽ không kết nối được. Signature của callback `onConnect` cũng khác: với `graphql-ws`, nó nhận connection context, và các giá trị context bổ sung thuộc về field `extra` của nó (xem [Xác thực qua WebSocket](/graphql/subscriptions#authentication-over-websockets) bên dưới).

#### Code first

Để tạo một subscription theo cách tiếp cận code first, hãy dùng decorator `@Subscription()` (được export từ package `@nestjs/graphql`) và class `PubSub` từ package `graphql-subscriptions`, class này cung cấp một **API publish/subscribe** đơn giản.

Subscription handler sau **subscribe** một event bằng cách gọi `PubSub#asyncIterableIterator`. Method này nhận một tham số duy nhất, `triggerName`, tương ứng với tên topic của event.

[[CODE:3]]

> info **Hint** Mọi decorator đều được export từ package `@nestjs/graphql`, còn class `PubSub` được export từ package `graphql-subscriptions` (`npm i graphql-subscriptions`).

> warning **Note** `PubSub` là một class cung cấp API `publish` và `subscribe` đơn giản. Tìm hiểu thêm trong [hướng dẫn thiết lập graphql-subscriptions](https://www.apollographql.com/docs/graphql-subscriptions/setup.html). Tài liệu Apollo cảnh báo rằng [phần hiện thực mặc định](https://github.com/apollographql/graphql-subscriptions#getting-started-with-your-first-subscription) không phù hợp cho production. Các ứng dụng production nên dùng một phần hiện thực `PubSub` dựa trên một store bên ngoài (xem danh sách [các phần hiện thực PubSub](https://github.com/apollographql/graphql-subscriptions#pubsub-implementations)).

Nó sinh ra phần sau của GraphQL schema bằng SDL:

[[CODE:4]]

Theo định nghĩa, subscription trả về một object có một thuộc tính cấp cao nhất duy nhất với key là tên của subscription. Tên này hoặc được kế thừa từ tên của method subscription handler (tức `commentAdded` ở trên), hoặc được cung cấp tường minh qua tùy chọn `name` trong tham số thứ hai của decorator `@Subscription()`, như bên dưới.

[[CODE:5]]

Cấu trúc này tạo ra cùng SDL với đoạn code mẫu trước, nhưng tách tên method khỏi tên subscription.

#### Publish

Để publish event, hãy dùng method `PubSub#publish`. Nó thường được gọi bên trong một mutation để kích hoạt việc cập nhật phía client khi một phần của object graph thay đổi. Ví dụ:

[[CODE:6]]

Method `PubSub#publish` nhận một `triggerName` (một lần nữa, hãy coi nó là tên topic của event) làm tham số đầu tiên, và một event payload làm tham số thứ hai. Như đã nói, theo định nghĩa một subscription trả về một giá trị, và giá trị đó có một cấu trúc. Hãy xem lại SDL được sinh ra cho subscription `commentAdded`:

[[CODE:7]]

Điều này cho chúng ta biết subscription phải trả về một object có thuộc tính cấp cao nhất tên `commentAdded` với giá trị là một object `Comment`. Cấu trúc của event payload được phát ra bởi method `PubSub#publish` phải khớp với cấu trúc của giá trị mà subscription được kỳ vọng trả về. Trong ví dụ ở trên, câu lệnh `pubSub.publish('commentAdded', {{ '{' }} commentAdded: newComment {{ '}' }})` publish một event `commentAdded` với payload có cấu trúc phù hợp. Nếu cấu trúc không khớp, subscription sẽ thất bại khi event được resolve.

#### Lọc subscription

Để lọc bỏ các event cụ thể, hãy đặt thuộc tính `filter` thành một hàm lọc. Hàm này hoạt động giống callback được truyền cho method `filter()` của mảng. Nó nhận hai tham số: `payload`, chứa event payload (do bên publish event gửi), và `variables`, chứa mọi argument được truyền kèm request subscription. Nó trả về một boolean quyết định event có được publish tới các client đang lắng nghe hay không.

[[CODE:8]]

#### Biến đổi payload của subscription

Để biến đổi event payload được publish, hãy đặt thuộc tính `resolve` thành một hàm. Hàm này nhận event payload (do bên publish event gửi) và trả về giá trị phù hợp.

[[CODE:9]]

> warning **Note** Nếu bạn dùng tùy chọn `resolve`, hãy trả về payload đã được bóc ra (trong ví dụ của chúng ta, trả về trực tiếp object `newComment`, không phải object `{{ '{' }} commentAdded: newComment {{ '}' }}`).

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau.

[[CODE:10]]

Cấu trúc tương tự cũng dùng được với filter:

[[CODE:11]]

#### Schema first

Để tạo một subscription tương đương trong Nest, hãy dùng decorator `@Subscription()`.

[[CODE:12]]

Để lọc bỏ các event cụ thể dựa trên context và argument, hãy đặt thuộc tính `filter`.

[[CODE:13]]

Để biến đổi payload được publish, hãy dùng một hàm `resolve`.

[[CODE:14]]

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau:

[[CODE:15]]

Cấu trúc tương tự cũng dùng được với filter:

[[CODE:16]]

Bước cuối cùng là cập nhật file định nghĩa type.

[[CODE:17]]

Với điều này, chúng ta đã tạo một subscription duy nhất `commentAdded(title: String!): Comment`. Một [ví dụ schema first](https://github.com/nestjs/nest/blob/master/sample/12-graphql-schema-first) hoàn chỉnh có sẵn trong repository của NestJS.

#### PubSub

Các ví dụ ở trên khởi tạo một instance `PubSub` cục bộ. Cách được ưu tiên là định nghĩa `PubSub` làm một [provider](/fundamentals/custom-providers) và inject nó qua constructor (bằng decorator `@Inject()`), để cùng một instance được tái sử dụng trong toàn bộ ứng dụng. Ví dụ, định nghĩa một provider như sau, rồi inject `'PUB_SUB'` ở nơi cần.

[[CODE:18]]

#### Tùy chỉnh subscription server

Để tùy chỉnh subscription server (ví dụ để thay đổi path của nó, mặc định là path của GraphQL endpoint), hãy truyền một options object cho `graphql-ws` trong thuộc tính `subscriptions`:

[[CODE:19]]

Để tự cấu hình WebSocket server bên dưới (ví dụ để bật `perMessageDeflate`, giới hạn `maxPayload`, hoặc thêm bước kiểm tra `verifyClient`), hãy tạo một `WebSocketServer` của [`ws`](https://github.com/websockets/ws) và truyền nó làm `server`:

[[CODE:20]]

- Server phải được tạo với `noServer: true`: Nest điều hướng các HTTP upgrade request tới nó, và sẽ throw nếu không như vậy.
- Nếu server có `path`, nó được ưu tiên hơn `graphql-ws.path` và path của GraphQL endpoint.
- Server được giao cho `graphql-ws`, thư viện này thay thế tùy chọn `handleProtocols` của nó và, khi ứng dụng shutdown, đóng nó lại và gỡ bỏ mọi listener của nó.
- Hãy dùng một server riêng cho mỗi `GraphQLModule`; một instance không thể được dùng chung giữa các module.

> info **Hint** Chỉ phần hiện thực `ws` được hỗ trợ. Các adapter Fastify và uWebSockets của `graphql-ws` không thể cắm vào theo cách này.

#### Xác thực qua WebSocket

Để kiểm tra người dùng đã được xác thực hay chưa, hãy dùng callback function `onConnect`, thứ bạn có thể chỉ định trong các tùy chọn `subscriptions`.

Với `graphql-ws`, callback `onConnect` nhận connection context, bao gồm `connectionParams`.

[[CODE:21]]

#### Bật subscription với Mercurius driver

Để bật subscription, hãy đặt thuộc tính `subscription` thành `true`.

[[CODE:22]]

> info **Hint** Bạn cũng có thể truyền một options object để thiết lập một custom emitter, validate các kết nối đi vào, v.v. Xem tùy chọn `subscription` trong [tùy chọn plugin của Mercurius](https://github.com/mercurius-js/mercurius/blob/master/docs/api/options.md#plugin-options).

#### Code first

Để tạo một subscription theo cách tiếp cận code first, hãy dùng decorator `@Subscription()` (được export từ package `@nestjs/graphql`) và class `PubSub` từ package `mercurius`, class này cung cấp một **API publish/subscribe** đơn giản.

Subscription handler sau **subscribe** một event bằng cách gọi `PubSub#subscribe`. Method này nhận tên topic làm tham số.

[[CODE:23]]

> info **Hint** Mọi decorator dùng trong ví dụ ở trên đều được export từ package `@nestjs/graphql`, còn class `PubSub` được export từ package `mercurius`.

> warning **Note** `PubSub` là một class cung cấp API `publish` và `subscribe` đơn giản. Để đăng ký một class `PubSub` tùy chỉnh, xem [Subscriptions with custom PubSub](https://github.com/mercurius-js/mercurius/blob/master/docs/subscriptions.md#subscriptions-with-custom-pubsub) trong tài liệu Mercurius.

Nó sinh ra phần sau của GraphQL schema bằng SDL:

[[CODE:24]]

Theo định nghĩa, subscription trả về một object có một thuộc tính cấp cao nhất duy nhất với key là tên của subscription. Tên này hoặc được kế thừa từ tên của method subscription handler (tức `commentAdded` ở trên), hoặc được cung cấp tường minh qua tùy chọn `name` trong tham số thứ hai của decorator `@Subscription()`, như bên dưới.

[[CODE:25]]

Cấu trúc này tạo ra cùng SDL với đoạn code mẫu trước, nhưng tách tên method khỏi tên subscription.

#### Publish

Để publish event, hãy dùng method `PubSub#publish`. Nó thường được gọi bên trong một mutation để kích hoạt việc cập nhật phía client khi một phần của object graph thay đổi. Ví dụ:

[[CODE:26]]

Như đã nói, theo định nghĩa một subscription trả về một giá trị, và giá trị đó có một cấu trúc. Hãy xem lại SDL được sinh ra cho subscription `commentAdded`:

[[CODE:27]]

Điều này cho chúng ta biết subscription phải trả về một object có thuộc tính cấp cao nhất tên `commentAdded` với giá trị là một object `Comment`. Cấu trúc của event payload được phát ra bởi method `PubSub#publish` phải khớp với cấu trúc của giá trị mà subscription được kỳ vọng trả về. Trong ví dụ ở trên, câu lệnh `pubSub.publish({{ '{' }} topic: 'commentAdded', payload: {{ '{' }} commentAdded: newComment {{ '}' }} {{ '}' }})` publish một event `commentAdded` với payload có cấu trúc phù hợp. Nếu cấu trúc không khớp, subscription sẽ thất bại khi event được resolve.

#### Lọc subscription

Để lọc bỏ các event cụ thể, hãy đặt thuộc tính `filter` thành một hàm lọc. Hàm này hoạt động giống callback được truyền cho method `filter()` của mảng. Nó nhận hai tham số: `payload`, chứa event payload (do bên publish event gửi), và `variables`, chứa mọi argument được truyền kèm request subscription. Nó trả về một boolean quyết định event có được publish tới các client đang lắng nghe hay không.

[[CODE:28]]

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau.

[[CODE:29]]

#### Schema first

Để tạo một subscription tương đương trong Nest, hãy dùng decorator `@Subscription()`.

[[CODE:30]]

Để lọc bỏ các event cụ thể dựa trên context và argument, hãy đặt thuộc tính `filter`.

[[CODE:31]]

Để truy cập các provider được inject (ví dụ để validate dữ liệu với một service bên ngoài), hãy dùng cấu trúc sau:

[[CODE:32]]

Bước cuối cùng là cập nhật file định nghĩa type.

[[CODE:33]]

Với điều này, chúng ta đã tạo một subscription duy nhất `commentAdded(title: String!): Comment`.

#### PubSub

Các ví dụ ở trên dùng emitter `PubSub` mặc định ([mqemitter](https://github.com/mcollina/mqemitter)). Cho production, cách được ưu tiên là dùng `mqemitter-redis`. Ngoài ra, bạn có thể cung cấp một phần hiện thực `PubSub` tùy chỉnh (xem [Subscription](https://github.com/mercurius-js/mercurius/blob/master/docs/subscriptions.md) trong tài liệu Mercurius).

[[CODE:34]]

#### Xác thực qua WebSocket

Để kiểm tra người dùng đã được xác thực hay chưa, hãy dùng callback function `verifyClient`, thứ bạn có thể chỉ định trong các tùy chọn `subscription`.

Callback `verifyClient` nhận object `info` làm tham số đầu tiên, bạn có thể dùng nó để đọc các header của request.

[[CODE:35]]
