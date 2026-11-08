### Migrate từ Fastify

Một ứng dụng Fastify có thể chuyển sang Nest mà vẫn chạy trên Fastify: các plugin của bạn vẫn hoạt động, và các route được chuyển từng cái một hoặc tất cả cùng lúc.

Nest chạy trên Fastify qua `FastifyAdapter`, nên đây không phải là đổi server. Router, các plugin, JSON schema và việc serialize vẫn giữ nguyên, kể cả cách path được so khớp, cách query string được parse và kích thước tối đa của body. Những gì bạn thêm vào là cấu trúc xung quanh chúng: module, dependency injection, và guard cùng pipe thay cho các hook được đăng ký theo từng route.

#### Chọn cách tiếp cận

| Câu hỏi | Từng route một | Tất cả cùng lúc |
| --- | --- | --- |
| Nó hoạt động thế nào? | Nest chạy trên instance Fastify của bạn, và các route được chuyển sang nó từng cái một | Một ứng dụng Nest mới thay thế ứng dụng Fastify trong một lần release |
| Cái gì được deploy? | Mỗi route được chuyển, một cách độc lập | Mọi thứ, một lần |
| Việc phát triển tính năng thì sao? | Vẫn tiếp tục, và các endpoint mới được viết trong Nest | Phải chờ, hoặc viết hai lần, cho tới khi chuyển đổi |
| Quay lui thế nào? | Khôi phục một route | Deploy bản release Fastify cuối cùng |
| Phiên bản Fastify nào? | Fastify 5, nên hãy nâng cấp trước | Bất kỳ, vì ứng dụng Fastify không bị động tới |
| Các plugin hiện có thì sao? | Chúng vẫn chạy, cả cho route của Nest | Bạn đăng ký lại chúng trên ứng dụng Nest |
| Có hai phong cách trong code bao lâu? | Cho tới khi route cuối cùng được chuyển | Không bao giờ |

Hãy chuyển từng route một khi ứng dụng lớn, khi có nhiều người cùng làm, hoặc khi nó không thể chờ. Hãy chuyển tất cả cùng lúc khi nó đủ nhỏ để review như một thay đổi duy nhất và bạn có thể cố định những gì nó làm bằng test. Cách đó cũng phù hợp với một [coding agent](/recipes/fastify-migration#give-it-to-a-coding-agent).

#### Từng route một

Ứng dụng Fastify giữ các route, plugin và error handler của nó, các endpoint mới được viết trong Nest, và các endpoint hiện có được chuyển sang khi bạn sửa chúng lần tới. Cả hai trả lời trên cùng một port, nên client không nhận ra, và mỗi bước đều có thể được deploy độc lập.

##### Yêu cầu

- **Fastify 5.** `FastifyAdapter` của Nest đăng ký các plugin yêu cầu phiên bản này, nên một instance Fastify 4 sẽ thất bại ngay khi Nest khởi động. Hãy nâng cấp ứng dụng trước.
- **TypeScript.** Code Nest trên trang này là TypeScript. Nếu ứng dụng Fastify được viết bằng JavaScript, các file của nó có thể giữ nguyên: tùy chọn `allowJs` của TypeScript biên dịch chúng cùng phần còn lại.

Cài Nest cạnh Fastify:

[[CODE:1]]

##### Chạy Nest trên ứng dụng Fastify

Nest thường tự tạo instance Fastify của riêng nó. Hãy đưa cho nó instance của bạn thay vào đó. Dừng việc ứng dụng tự lắng nghe, và để một hàm trả về nó. Nest đặt error handler và not-found handler riêng của instance, nên có hai điều phải thay đổi:

- Chuyển `setErrorHandler()` vào một plugin chứa các route của bạn. Nó vẫn tiếp tục xử lý lỗi của chúng, và Fastify sẽ không cảnh báo về việc nó bị ghi đè.
- Gỡ bỏ `setNotFoundHandler()`. Nest từ chối khởi động với `Not found handler already set`, và nó tự trả lời các route không tồn tại.

[[CODE:2]]

Sau đó truyền nó cho `FastifyAdapter`, và để Nest lắng nghe:

[[CODE:3]]

Giờ cả hai cùng phục vụ request từ một instance Fastify:

- Các route Fastify trả lời như trước đây, và lỗi của chúng tới error handler riêng của chúng.
- Các plugin và hook được đăng ký trên root instance cũng áp dụng cho route của Nest, nên `helmet` và hook `onRequest` ở trên chạy cho chúng, và `request.jwtVerify()` hoạt động bên trong một guard của Nest.
- Các hook được đăng ký bên trong một plugin được đóng gói vẫn ở trong đó, như mọi khi, nên chúng không chạy cho route của Nest.
- Lỗi trong route của Nest đi qua các [exception filter](/exception-filters) của nó, và một request tới route mà cả hai đều không có sẽ nhận response `404` của Nest.

##### Chuyển một route

Viết route trong Nest, và xóa nó khỏi Fastify trong cùng thay đổi. Router của Fastify từ chối trùng lặp, nên khi cả hai cùng có trong code, ứng dụng sẽ dừng lúc khởi động với `Method 'GET' already declared for route`. Một plugin bạn đang dùng có thể làm nền cho một [guard](/guards), và `@RouteSchema()` nhận JSON schema mà route đã có:

[[CODE:4]]

[[CODE:5]]

Hãy đọc [Giữ những gì sẽ thay đổi mà không báo lỗi](/recipes/fastify-migration#keep-what-would-change-without-an-error) trong lúc làm. Nó áp dụng cho mọi route được chuyển, và response schema ở trên có mặt chính là vì nó.

##### Hoàn tất migration

Khi các route Fastify đã hết, hãy đăng ký các plugin trên ứng dụng Nest bằng `app.register()`, biến error handler thành một [exception filter](/exception-filters), xóa thư mục `legacy`, và tạo ứng dụng bằng `new FastifyAdapter()`.

#### Tất cả cùng lúc

Một ứng dụng Nest mới thay thế ứng dụng Fastify trong một lần release. Cho tới lúc đó ứng dụng Fastify giữ nguyên, và nó là tham chiếu cho những gì ứng dụng mới phải làm. Hãy giữ `FastifyAdapter` trong suốt quá trình migration, kể cả khi bạn định đổi adapter sau này: điều đó giữ nguyên router, việc parse query, giới hạn body và cú pháp path, nên ít thứ có thể thay đổi cùng lúc hơn.

##### Cố định API bằng test

Viết các test chỉ biết URL, để cùng các test chạy được trên cả hai ứng dụng. Duyệt qua mọi plugin và route, và bao phủ status code, body và các header quan trọng của mỗi route, cho cả trường hợp thất bại lẫn thành công. Kiểm tra rằng các field mà một response schema loại bỏ vẫn bị loại bỏ:

[[CODE:6]]

Chạy chúng trên ứng dụng Fastify cho tới khi tất cả đều pass, trước khi viết bất kỳ dòng code Nest nào:

[[CODE:7]]

##### Chuyển đổi ứng dụng

Tạo ứng dụng Nest bằng `nest new` cạnh ứng dụng Fastify, [chuyển nó sang `FastifyAdapter`](/http/performance#fastify-adapter), và chuyển mỗi plugin chứa route thành một controller:

| Fastify | Nest |
| --- | --- |
| `app.register(routes, {{ '{' }} prefix {{ '}' }})` | Một [controller](/controllers), `@Controller('api/orders')`, trong một [module](/modules) |
| `app.get('/:id', handler)` | `@Get(':id')` trên một method |
| `request.params`, `request.query`, `request.body` | `@Param()`, `@Query()`, `@Body()` |
| `schema: {{ '{' }} querystring, body, response {{ '}' }}` | `@RouteSchema()` từ `@nestjs/platform-fastify`, với cùng các JSON schema |
| `onRequest: app.authenticate` | Một [guard](/guards) |
| `preHandler: app.requireRole('admin')` | Metadata trên route, được một guard đọc |
| Một decorator như `request.jwtVerify()` | Cùng lời gọi đó trên `@Req()`, với plugin đã được đăng ký |
| `reply.code(201).send(x)` | `return x`, kèm `@HttpCode()` khi status không phải mặc định |
| `reply.code(204).send()` | `@HttpCode(204)`, và không trả về gì |
| `reply.redirect(url, 301)` | `@Redirect(url, 301)` |
| `reply.setCookie()` | `@Res({{ '{' }} passthrough: true {{ '}' }}) reply`, sau đó `reply.setCookie()` và `return` như thường lệ |
| `reply.type('application/json')` | `@Header('content-type', 'application/json')` |
| `reply.send(stream)` | `new StreamableFile(stream, {{ '{' }} type {{ '}' }})` |
| `await request.file()` | Cùng lời gọi đó trên `@Req()`, với `@fastify/multipart` đã được đăng ký |
| `app.register(plugin, options)` | `app.register(plugin, options)` |
| `app.addHook('onRequest', fn)` | `app.getHttpAdapter().getInstance().addHook('onRequest', fn)` |
| `setErrorHandler()` và `setNotFoundHandler()` | Một [exception filter](/exception-filters) global |
| Một plugin decorate instance bằng một database pool | Một [provider](/fundamentals/custom-providers#value-providers-usevalue) |

Đường dẫn route giữ nguyên, vì cùng một router đọc chúng: `search/:term?`, `items/:id(^\\d+$)`, và `assets/*`, với `@Param('*')`.

##### Giữ những gì sẽ thay đổi mà không báo lỗi

Hai điểm trong số này làm lộ dữ liệu mà không có lỗi nào cả, nên hãy kiểm tra chúng trước:

| Trong Fastify | Trong một ứng dụng Nest | Để giữ hành vi cũ |
| --- | --- | --- |
| Một response schema loại bỏ mọi field mà nó không liệt kê, nên handler có thể trả về toàn bộ bản ghi | Không có schema, mọi field đều được gửi đi, kể cả `passwordHash` | `@RouteSchema({{ '{' }} response {{ '}' }})` trên mỗi route từng có schema |
| Một `POST` trả lời `200`, và `response: {{ '{' }} 200: schema {{ '}' }}` được áp dụng | Một `POST` trả lời `201`, nên một schema đánh key theo `200` không còn được áp dụng, và các field cũng được trả về | `@HttpCode(200)`, hoặc đánh key schema theo `201` |
| Việc xác thực trong `onRequest` chạy trước validation, nên một request không hợp lệ và không có token sẽ nhận `401` | `@RouteSchema({{ '{' }} body {{ '}' }})` validate trước mọi guard, nên request đó nhận lỗi validation | Validate bằng một [pipe](/application/validation#schema-based-validation), `@Body({{ '{' }} schema {{ '}' }})`, pipe này chạy sau guard, trên những route mà điều này quan trọng |
| Lỗi có cấu trúc mà handler của bạn đặt cho chúng | `{{ '{' }} statusCode, message, error {{ '}' }}` | Một exception filter global |
| Một lỗi validation tới handler của bạn với `err.validation` | Nó tới filter theo cùng cách, với `exception.validation` | Cùng filter đó |
| Một route không tồn tại nhận not-found handler của bạn | `NotFoundException`, với body của Nest | Cùng filter đó |

Filter phải giữ cấu trúc lỗi của bạn cho mọi lỗi, kể cả những lỗi mà Nest và Fastify tự phát sinh. Các lỗi về body như JSON sai định dạng hay body vượt giới hạn tới dưới dạng một `HttpException`:

[[CODE:8]]

[[CODE:9]]

##### Chuyển đổi

Chạy cùng các test trên ứng dụng Nest, và sửa ứng dụng chứ không sửa test:

[[CODE:10]]

Khi chúng pass, hãy deploy nó thay cho ứng dụng Fastify, và giữ bản release Fastify cuối cùng ở trạng thái có thể deploy cho tới khi bản mới đã phục vụ lưu lượng thật.

#### Giao cho một coding agent

Cách tiếp cận nào cũng làm được với một coding agent, và tất cả cùng lúc là lựa chọn phù hợp hơn khi ứng dụng đủ nhỏ để review trong một thay đổi. Hãy chỉ cho agent trang này và buộc nó tuân theo các test, để nó không thể tuyên bố thành công với code chỉ đơn thuần biên dịch được:

[[CODE:11]]
