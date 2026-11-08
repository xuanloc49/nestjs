### Migrate từ Express

Một ứng dụng Express có thể chuyển sang Nest từng route một, với cả hai cùng phục vụ request, hoặc tất cả cùng lúc, trong một lần release. Trang này nói về cả hai cách.

#### Chọn cách tiếp cận

| Câu hỏi | Từng route một | Tất cả cùng lúc |
| --- | --- | --- |
| Nó hoạt động thế nào? | Nest chạy trên ứng dụng Express của bạn, và các route được chuyển sang nó từng cái một | Một ứng dụng Nest mới thay thế ứng dụng Express trong một lần release |
| Cái gì được deploy? | Mỗi route được chuyển, một cách độc lập | Mọi thứ, một lần |
| Việc phát triển tính năng thì sao? | Vẫn tiếp tục, và các endpoint mới được viết trong Nest | Phải chờ, hoặc viết hai lần, cho tới khi chuyển đổi |
| Quay lui thế nào? | Khôi phục một route | Deploy bản release Express cuối cùng |
| Phiên bản Express nào? | Express 5, nên hãy nâng cấp trước | Bất kỳ, vì ứng dụng Express không bị động tới |
| Các middleware hiện có thì sao? | Chúng vẫn chạy, cả cho route của Nest | Chúng được chuyển sang Nest cùng mọi thứ khác |
| Có hai phong cách trong code bao lâu? | Cho tới khi route cuối cùng được chuyển | Không bao giờ |

Hãy chuyển từng route một khi ứng dụng lớn, khi có nhiều người cùng làm, hoặc khi nó không thể chờ. Hãy chuyển tất cả cùng lúc khi nó đủ nhỏ để review như một thay đổi duy nhất và bạn có thể cố định những gì nó làm bằng test. Cách đó cũng phù hợp với một [coding agent](/recipes/express-migration#give-it-to-a-coding-agent), thứ có thể chuyển đổi cả một ứng dụng trong một lần, nhưng không tự biết được những gì phải giữ nguyên.

#### Từng route một

Ứng dụng Express giữ các route, middleware và error handler của nó, các endpoint mới được viết trong Nest, và các endpoint hiện có được chuyển sang khi bạn sửa chúng lần tới. Cả hai trả lời trên cùng một port, phía sau cùng các middleware, nên client, session và phần xác thực không nhận ra, và mỗi bước đều có thể được deploy độc lập.

##### Yêu cầu

- **Express 5.** Adapter Express của Nest điều khiển một ứng dụng Express 5, và một ứng dụng Express 4 sẽ thất bại ngay khi Nest khởi động. Hãy nâng cấp ứng dụng trước, với [hướng dẫn migration](https://expressjs.com/en/guide/migrating-5.html) của Express và codemod của nó, `npx @expressjs/codemod upgrade`.
- **TypeScript.** Code Nest trên trang này là TypeScript. Nếu ứng dụng Express được viết bằng JavaScript, các file của nó có thể giữ nguyên: tùy chọn `allowJs` của TypeScript biên dịch chúng cùng phần còn lại.

Một ứng dụng CommonJS có thể giữ nguyên CommonJS. Các package của Nest là ESM, thứ mà một ứng dụng CommonJS load được trên các phiên bản Node.js được liệt kê trong [hướng dẫn migration](/migration-guide#esm-packages).

Cài Nest cạnh Express:

[[CODE:1]]

##### Chạy Nest trên ứng dụng Express

Nest thường tự tạo ứng dụng Express của riêng nó. Hãy đưa cho nó ứng dụng của bạn thay vào đó. Dừng việc ứng dụng Express tự lắng nghe, và export một hàm dựng nó, để các test có thể tự dựng ứng dụng của chúng:

[[CODE:2]]

Sau đó truyền nó cho `ExpressAdapter`, và để Nest lắng nghe:

[[CODE:3]]

Express chạy middleware và route theo thứ tự chúng được thêm vào. Mọi thứ mà ứng dụng Express thêm vào đều đứng trước. Nest thêm các route của nó khi ứng dụng khởi động, trong `listen()` hoặc `init()`, và sau đó là một handler trả lời `404` cho các request không khớp route nào. Vì vậy:

- Các route Express trả lời như trước đây.
- Các route của Nest trả lời những request mà route Express không trả lời.
- Các route của Nest thấy những gì middleware Express đặt lên request, như `req.user`, và body mà các parser của nó đã đọc.
- Một request tới route mà cả hai đều không có sẽ nhận response `404` của Nest.

> warning **Warning** Hãy gỡ bỏ một handler `404` bắt tất cả, như `app.use((req, res) => res.status(404).send())`, khỏi ứng dụng Express. Nó đứng trước các route của Nest, nên nó cũng trả lời request của chúng, và handler của Nest sẽ trả lời các route không tồn tại thay cho nó. Hãy giữ error handler: một error handler của Express chỉ nhận lỗi của các middleware và route được thêm vào trước nó, nên nó vẫn tiếp tục xử lý lỗi của các route Express, trong khi các [exception filter](/exception-filters) của Nest xử lý lỗi của các route Nest.

Phần nào của ứng dụng chạy cho route nào:

| Phần | Route Express | Route Nest |
| --- | --- | --- |
| Middleware được thêm vào ứng dụng Express (body parser, session, xác thực) | Có | Có |
| Error handler của ứng dụng Express | Có | Không |
| Middleware được thêm qua Nest: [`MiddlewareConsumer`](/middleware), `app.use()`, `app.enableCors()` | Không | Có |
| [Guard](/guards), [interceptor](/interceptors), [pipe](/pipes) và [exception filter](/exception-filters) | Không | Có |

Các middleware mà ứng dụng Express đang chạy cũng đứng trước các route của Nest, nên một [guard](/guards) có thể kiểm tra user mà middleware xác thực hiện có đã đặt lên request:

[[CODE:4]]

> info **Hint** Với một [global prefix](/faq/global-prefix), handler `404` của Nest chỉ trả lời các path nằm dưới prefix. Một path nằm ngoài nó mà không route Express nào khớp sẽ nhận trang `404` mặc định của Express.

##### Chuyển một route

Viết các endpoint mới trong Nest. Để chuyển một endpoint hiện có, hãy viết nó thành một route Nest và xóa nó khỏi router Express. Vì các route Express đứng trước, một route Nest có cùng method và path sẽ không trả lời cho tới khi route Express biến mất, nên cả hai có thể cùng có trong code cho tới khi bạn sẵn sàng chuyển:

[[CODE:5]]

[[CODE:6]]

`GET /orders` vẫn do Express trả lời, còn `GET /orders/:id` đi qua router Express và tới Nest.

[End-to-end test](/fundamentals/testing#end-to-end-testing) bao phủ cả hai loại route khi ứng dụng test cũng được dựng trên ứng dụng Express. Hãy truyền adapter cho `createNestApplication()`, và cùng một test sẽ kiểm tra một route trước và sau khi nó được chuyển:

[[CODE:7]]

##### Dùng chung code giữa hai bên

Ứng dụng Express đã có những object mà code Nest cần, như một database pool, các repository, hoặc một mailer. Hãy đăng ký chúng làm [value provider](/fundamentals/custom-providers#value-providers-usevalue), để Nest inject cùng các instance mà code Express dùng:

[[CODE:8]]

Import `LegacyModule` một lần trong `AppModule`, và bất kỳ provider nào cũng có thể inject `OrdersRepository` theo class của nó.

Chiều ngược lại cũng được. Khi `NestFactory.create()` trả về, `app.get()` trả về bất kỳ provider nào, nên một route vẫn ở lại trong Express có thể gọi logic đã được chuyển vào một service của Nest. Hãy thêm route trước `listen()`, và nó sẽ đứng trước các route của Nest như phần còn lại của ứng dụng Express:

[[CODE:9]]

##### Hoàn tất migration

Khi các router Express đã trống, hãy chuyển phần còn lại của ứng dụng Express vào Nest: middleware vào [middleware của Nest](/middleware) hoặc `app.use()`, và error handler vào một [exception filter](/exception-filters). Sau đó xóa thư mục `legacy`, và tạo ứng dụng mà không có tham số adapter:

[[CODE:10]]

#### Tất cả cùng lúc

Một ứng dụng Nest mới thay thế ứng dụng Express trong một lần release. Cho tới lúc đó ứng dụng Express giữ nguyên, trên phiên bản Express mà nó đang chạy, và nó là tham chiếu cho những gì ứng dụng mới phải làm.

Phần lớn rủi ro không nằm ở việc chuyển đổi, vì một bản chuyển đổi sai thường thất bại rõ ràng. Nó nằm ở những gì thay đổi mà không báo lỗi: một status code, cấu trúc của một error response, cách một query string được parse. Vì vậy migration bắt đầu bằng những test nhận ra được các thay đổi đó.

##### Cố định API bằng test

Viết các test chỉ biết URL, để cùng các test chạy được trên cả hai ứng dụng. Duyệt qua mọi router và lời gọi `app.use()`, và bao phủ status code, body và các header quan trọng của mỗi route, cho cả trường hợp thất bại lẫn thành công:

[[CODE:11]]

Chạy chúng trên ứng dụng Express cho tới khi tất cả đều pass, trước khi viết bất kỳ dòng code Nest nào:

[[CODE:12]]

##### Chuyển đổi ứng dụng

Tạo ứng dụng Nest bằng `nest new` cạnh ứng dụng Express, và chuyển mỗi router thành một controller:

| Express | Nest |
| --- | --- |
| `express.Router()` cho một resource | Một [controller](/controllers) trong một [module](/modules) (`nest generate resource`) |
| `router.get('/:id', handler)` | `@Get(':id')` trên một method |
| `req.params`, `req.query`, `req.body` | `@Param()`, `@Query()`, `@Body()` |
| Tự validate `req.body` bằng tay | Một [schema hoặc một DTO](/application/validation), hoặc giữ nguyên bước kiểm tra nếu test cố định status và message của nó |
| Middleware xác thực đặt `req.user` | Một [guard](/guards) đặt nó, và một [custom decorator](/custom-decorators) đọc nó |
| `requireRole('admin')` | Metadata trên route, được một guard đọc |
| `router.param('id', load)` | Một [pipe](/pipes): `@Param('id', OrderByIdPipe)`. Guard chạy trước pipe, nên việc xác thực vẫn đi trước |
| `res.json(x)` | `return x`, kèm `@HttpCode()` khi status không phải mặc định |
| `res.status(204).end()` | `@HttpCode(204)`, và không trả về gì |
| `res.redirect(301, url)` | `@Redirect(url, 301)` |
| `res.cookie()` | `@Res({{ '{' }} passthrough: true {{ '}' }}) res`, sau đó `res.cookie()` và `return` như thường lệ |
| `res.type()`, `res.attachment()` | `@Header()` |
| `res.write()` | `@Res() res`, sau đó ghi vào nó như trong Express |
| `next(err)` | `throw err`, được một [exception filter](/exception-filters) xử lý |
| Error handler và `404` bắt tất cả | Một exception filter global |
| `app.use(helmet())` | `app.use(helmet())` |
| `app.use(cors(options))` | `app.enableCors(options)` |
| `express.static(dir)` | `app.useStaticAssets(dir, {{ '{' }} prefix {{ '}' }})` |
| `multer(options).single('file')` | `@UseInterceptors(FileInterceptor('file', options))` và `@UploadedFile()` |
| Các module giữ một database pool hoặc một mailer | Ban đầu là [value provider](/fundamentals/custom-providers#value-providers-usevalue), sau đó là service |

Một router có xác thực, kiểm tra role và một parameter handler trở thành:

[[CODE:13]]

##### Giữ những gì sẽ thay đổi mà không báo lỗi

Đây là những khác biệt vẫn biên dịch được, khởi động được và trông có vẻ đúng, những thứ mà test của bạn phải bắt được:

| Trong Express | Trong một ứng dụng Nest | Để giữ hành vi cũ |
| --- | --- | --- |
| `res.json()` trả lời `200`, kể cả trên một `POST` | Một handler `POST` trả lời `201` | `@HttpCode(200)` |
| Lỗi có cấu trúc mà handler của bạn đặt cho chúng | `{{ '{' }} statusCode, message, error {{ '}' }}` | Một exception filter global |
| Một route không tồn tại nhận `404` của bạn | `NotFoundException`, với body của Nest | Cùng filter đó |
| JSON sai định dạng tới handler của bạn dưới dạng `entity.parse.failed` | `BadRequestException`, lỗi mà một URL sai định dạng như `/orders/%FF` cũng gây ra | Cùng filter đó |
| Một JSON body lớn hơn 100 kB tới handler của bạn dưới dạng `entity.too.large` | Một `HttpException` với status `413` | Cùng filter đó |
| Một lỗi multer tới handler của bạn dưới dạng `MulterError` | `FileInterceptor` gây ra `PayloadTooLargeException` cho lỗi kích thước, và `400` cho hầu hết các lỗi khác | Cùng filter đó, hoặc tự chạy multer |
| Chỉ các định dạng body mà bạn đã thêm parser mới được đọc | Cả body JSON lẫn URL-encoded đều được đọc | `bodyParser: false` trong `NestFactory.create()`, rồi `app.use(express.json())` |
| `router.use(authenticate)` cũng trả lời cho các path không có route nào bên dưới nó | Một guard chỉ chạy trên các route tồn tại, nên các path đó nhận `404` | Giữ nó dưới dạng middleware, với `consumer.apply(authenticate).forRoutes('api/orders/{{ '{' }}*path{{ '}' }}')`, nếu client có thể nhận ra khác biệt |
| `router.param()` chạy trước middleware riêng của route, nên một bản ghi không tồn tại là `404` với bất kỳ ai | Mọi guard chạy trước mọi pipe, nên `requireRole` trả lời trước, với `403` | Kiểm tra role trong handler, sau pipe, nếu client có thể nhận ra khác biệt |
| Trên Express 4, `?min[total]=10` là `{{ '{' }} min: {{ '{' }} total: '10' {{ '}' }} {{ '}' }}` | Parser của Express 5 cho ra `{{ '{' }} 'min[total]': '10' {{ '}' }}` | `app.set('query parser', 'extended')` |
| Trên Express 4, một request không có body có `req.body` là `{{ '{' }}{{ '}' }}` | `@Body()` là `undefined`, nên destructure nó sẽ throw | `body ?? {{ '{' }}{{ '}' }}` |
| `res.json('1.2.3')` gửi một chuỗi JSON | Trả về một chuỗi sẽ gửi `text/html` | `@Res() res`, rồi `res.json('1.2.3')` |

Đường dẫn route cũng phải thay đổi, nhưng những thay đổi đó thất bại rõ ràng: `/search/:term?` dừng ứng dụng lúc khởi động, và cần đổi thành `search{{ '{' }}/:term{{ '}' }}`. Một wildcard cần có tên, `assets/*path`, và `@Param('path')` trả về các đoạn của nó dưới dạng một mảng. `assets/*path` không khớp với `/assets/` khi không có gì phía sau, nên hãy dùng `assets/{{ '{' }}*path{{ '}' }}` nếu Express 4 đã trả lời path đó.

Đi từ Express 4 lên cũng mang theo những thay đổi nhỏ riêng của Express 5, mà các test so sánh chính xác từng byte sẽ phát hiện: `charset=utf-8` ở chỗ file tĩnh từng ghi `UTF-8`, và một body khác trên các redirect. Không client nào nên phụ thuộc vào những thứ đó, nên hãy chấp nhận chúng thay vì cố định các phiên bản cũ của library Express để tái tạo chúng.

Filter và `main.ts` giữ phần lớn những điều này. Chúng phải giữ cấu trúc lỗi của bạn cho mọi lỗi, kể cả những lỗi mà Nest tự phát sinh, nên hãy kiểm tra xem test của bạn kỳ vọng những lỗi nào. Ví dụ, filter này báo cáo mọi `BadRequestException` là JSON sai định dạng:

[[CODE:14]]

[[CODE:15]]

##### Chuyển đổi

Chạy cùng các test trên ứng dụng Nest, và sửa ứng dụng chứ không sửa test:

[[CODE:16]]

Khi chúng pass, hãy deploy nó thay cho ứng dụng Express, và giữ bản release Express cuối cùng ở trạng thái có thể deploy cho tới khi bản mới đã phục vụ lưu lượng thật.

#### Giao cho một coding agent

Cách tiếp cận nào cũng làm được với một coding agent, và tất cả cùng lúc là lựa chọn phù hợp hơn khi ứng dụng đủ nhỏ để review trong một thay đổi. Hãy chỉ cho agent trang này và buộc nó tuân theo các test, để nó không thể tuyên bố thành công với code chỉ đơn thuần biên dịch được:

[[CODE:17]]
