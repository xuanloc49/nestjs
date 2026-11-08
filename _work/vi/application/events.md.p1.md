### Event

Package [Event Emitter](https://www.npmjs.com/package/@nestjs/event-emitter) (`@nestjs/event-emitter`) cung cấp một bản implement observer, cho phép bạn subscribe và lắng nghe các event xảy ra trong ứng dụng. Event là cách tốt để tách rời các phần khác nhau của ứng dụng, vì một event có thể có nhiều listener không phụ thuộc lẫn nhau.

Bên trong, `EventEmitterModule` dùng package [eventemitter2](https://github.com/EventEmitter2/EventEmitter2).

#### Bắt đầu

Đầu tiên, cài package cần thiết:

[[CODE:1]]

Sau khi cài xong, import `EventEmitterModule` vào root module `AppModule` và gọi method static `forRoot()` của nó, như bên dưới:

[[CODE:2]]

Lời gọi `.forRoot()` khởi tạo event emitter và đăng ký mọi event listener khai báo trong app của bạn. Việc đăng ký diễn ra trong lifecycle hook `onApplicationBootstrap`, đảm bảo mọi module đều đã load và khai báo xong event listener của chúng. Mặc định module được đăng ký là [global module](/modules#global-modules), nên bạn có thể inject event emitter ở bất cứ đâu mà không cần import lại `EventEmitterModule`. Để thay đổi điều này, đặt tùy chọn `global` thành `false`.

Để cấu hình instance `EventEmitter2` bên dưới, truyền một configuration object vào method `.forRoot()`, như sau:

[[CODE:3]]

#### Dispatch event

Để dispatch (tức là phát) một event, trước tiên hãy inject `EventEmitter2` qua constructor:

[[CODE:4]]

> info **Hint** Import `EventEmitter2` từ package `@nestjs/event-emitter`.

Sau đó dùng nó trong class như sau:

[[CODE:5]]

#### Lắng nghe event

Để khai báo một event listener, hãy decorate method xử lý event bằng decorator `@OnEvent()`, như sau:

[[CODE:6]]

> info **Hint** Nếu một event listener thuộc về một provider [request-scoped](/fundamentals/injection-scopes), Nest sẽ tạo một instance mới của provider đó cho mỗi event mà nó xử lý. Payload của event sẽ thay thế cho request object, nên inject `REQUEST` trong provider đó sẽ cho bạn payload. Nếu payload bạn emit chính là request object gửi đến (hoặc mang context ID của nó), hãy đặt tùy chọn `inheritRequestContextId` của `forRoot()` thành `true` để listener dùng lại DI sub-tree của request đó thay vì tạo cái mới.

Tham số đầu tiên có thể là `string` hoặc `symbol` với event emitter đơn giản, và `string | symbol | Array<string | symbol>` với wildcard emitter.

Tham số thứ hai (tùy chọn) là một object tùy chọn cho listener:

[[CODE:7]]

> info **Hint** Để tìm hiểu thêm về object `OnOptions`, xem [tài liệu `eventemitter2`](https://github.com/EventEmitter2/EventEmitter2#emitteronevent-listener-options-objectboolean).

Ví dụ, listener sau chạy bất đồng bộ:

[[CODE:8]]

Để dùng namespace và wildcard, truyền tùy chọn `wildcard` vào method `EventEmitterModule#forRoot()`. Khi bật namespace và wildcard, event có thể là chuỗi phân cách bằng dấu phân cách (`foo.bar`) hoặc mảng (`['foo', 'bar']`). Bạn có thể cấu hình dấu phân cách bằng tùy chọn `delimiter`. Khi bật namespace, bạn có thể subscribe event bằng wildcard:

[[CODE:9]]

Một wildcard đơn khớp với đúng một segment. Ví dụ, `order.*` khớp với các event `order.created` và `order.shipped`, nhưng không khớp với `order.delayed.out_of_stock`. Để lắng nghe những event như vậy, dùng pattern wildcard nhiều cấp (tức là `**`), mô tả trong [tài liệu EventEmitter2 về wildcard nhiều cấp](https://github.com/EventEmitter2/EventEmitter2#multi-level-wildcards).

Với pattern này, bạn có thể, chẳng hạn, tạo một event listener bắt mọi event:

[[CODE:10]]

> info **Hint** Class `EventEmitter2` cung cấp vài method hữu ích để tương tác với event, như `waitFor()` và `onAny()`. Xem [tài liệu EventEmitter2](https://github.com/EventEmitter2/EventEmitter2) để biết chi tiết.

#### Độ ưu tiên của listener

Truyền `priority` trong tùy chọn của `@OnEvent()` để chọn thứ tự gọi các listener của cùng một event. Nest thu thập mọi listener `@OnEvent`, sắp xếp chúng theo độ ưu tiên (cao nhất trước), rồi mới đăng ký. Listener không có `priority` sẽ dùng `0`: độ ưu tiên dương chạy trước chúng, độ ưu tiên âm chạy sau. `Infinity` và `-Infinity` đều được chấp nhận, còn `NaN` sẽ quay về `0`.

[[CODE:11]]

Listener có `prependListener: true` vẫn đứng trước các listener `@OnEvent` khác, giống như khi không có độ ưu tiên. Nest sắp xếp riêng từng nhóm trong hai nhóm này theo độ ưu tiên, nên một listener prepend vẫn chạy trước một listener append có độ ưu tiên cao hơn. Các listener có cùng độ ưu tiên giữ nguyên thứ tự như khi không có độ ưu tiên: thứ tự được phát hiện với listener append, và thứ tự ngược lại với listener prepend.

Độ ưu tiên chỉ sắp xếp các listener `@OnEvent` có cùng tên event với nhau. Nó giữ nguyên vị trí của các listener được thêm trực tiếp vào `EventEmitter2`. Nó cũng giữ nguyên thứ tự mà [EventEmitter2](https://github.com/EventEmitter2/EventEmitter2) gọi giữa một listener wildcard (`order.*`) và một listener khớp chính xác (`order.created`).

Độ ưu tiên chỉ có hiệu lực với các listener bắt đầu công việc một cách đồng bộ khi event được emit:

- Listener đăng ký với `async: true`, `nextTick: true` hoặc `promisify: true` bị trì hoãn, nên chúng chạy sau mọi listener đồng bộ, bất kể độ ưu tiên. Ví dụ, `@OnEvent('order.created', {{ '{' }} priority: 10, async: true {{ '}' }})` vẫn chạy sau `notifyWarehouse()` ở trên.
- Listener trên provider [request-scoped](/fundamentals/injection-scopes) hoặc durable phải resolve instance trước khi phần thân của chúng chạy, nên phần thân có thể bắt đầu sau các listener có độ ưu tiên thấp hơn. Độ ưu tiên không có hiệu lực với chúng.

Độ ưu tiên quyết định thứ tự gọi listener, chứ không quyết định listener tiếp theo có chạy hay không. Ở mọi chế độ, kể cả `emit()` thông thường, một listener có độ ưu tiên cao hơn mà throw hoặc reject thì các listener sau nó vẫn chạy. Một bước kiểm tra bảo mật ở độ ưu tiên cao hơn không thể dựa vào việc throw lỗi để bỏ qua một listener phía sau, như `notifyWarehouse()` ở trên.

#### Tránh mất event

Các event được emit trước hoặc trong lúc lifecycle hook `onApplicationBootstrap` chạy (ví dụ từ constructor hoặc method `onModuleInit()`) có thể bị bỏ lỡ, vì listener có thể chưa được đăng ký.

Để tránh điều này, hãy dùng method `waitUntilReady()` của `EventEmitterReadinessWatcher` (export từ `@nestjs/event-emitter`). Nó trả về một promise resolve khi mọi listener đã được đăng ký. Hãy gọi nó trong lifecycle hook `onApplicationBootstrap` của provider trước khi emit event:

[[CODE:12]]

> info **Note** Việc này chỉ cần thiết với các event được emit trước khi lifecycle hook `onApplicationBootstrap` hoàn tất.

#### Ví dụ

Một ví dụ chạy được có sẵn trong [sample event emitter](https://github.com/nestjs/nest/tree/master/sample/30-event-emitter).
