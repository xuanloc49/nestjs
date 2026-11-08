### Next.js

Một ứng dụng Next.js có thể dùng Nest làm backend: một repository, một origin cho trình duyệt, và các request schema được dùng chung bởi cả hai ứng dụng.

Route handler và Server Action là đủ cho một backend nhỏ. Khi nó lớn lên, với background job, webhook, một API công khai, một client di động hoặc một team riêng, nó cần cấu trúc mà Nest mang lại: module, dependency injection, guard, và validation trên mọi route. Next.js tiếp tục lo việc render, còn Nest đảm nhận mọi thứ phía sau:

| Next.js | Nest |
| --- | --- |
| Page, layout và Server Component | API, và các quy tắc nghiệp vụ đằng sau nó |
| Form, và trạng thái của trình duyệt | Validate những gì form gửi lên |
| Lấy dữ liệu để render | Database, và mọi nguồn dữ liệu khác |
| | Đăng nhập, phân quyền, webhook, queue, scheduled job |
| | Các client khác, như một ứng dụng di động |

Trang này thiết lập một ứng dụng Nest cạnh một ứng dụng Next.js, rồi chuyển một backend từ bên này sang bên kia:

- Cả hai nằm trong một repository, dưới dạng npm workspace.
- Trình duyệt gọi `/api` trên origin của Next.js, và Next.js chuyển request tiếp cho Nest, nên cookie hoạt động mà không cần CORS.
- Các Zod schema trong một package dùng chung validate một form trên trình duyệt và cùng request đó trong Nest.
- Các route handler bạn đang có vẫn tiếp tục trả lời, và được [chuyển sang Nest](/recipes/nextjs#migrate-a-nextjs-backend-to-nest) từng cái một.

#### Bố cục project

[[CODE:1]]

`package.json` ở thư mục gốc khai báo các workspace:

[[CODE:2]]

Tạo cả hai ứng dụng mà không cài package của chúng, rồi cài mọi thứ một lần, từ thư mục gốc:

[[CODE:3]]

`--skip-git` cũng khiến ứng dụng Nest không có `.gitignore`, nên hãy thêm một file ở thư mục gốc của repository:

[[CODE:4]]

Development server của Next.js chiếm port `3000`, nên hãy cho Nest một port khác trong `apps/api/src/main.ts`, và đặt các route của nó dưới `/api`, path mà trình duyệt sẽ gọi:

[[CODE:5]]

#### Chuyển `/api` tới Nest

[Rewrite](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites) của Next.js chuyển một request tiếp tới một server khác và trả về response của nó, mà trình duyệt không thấy redirect nào. Trong `apps/web/next.config.ts`, hãy gửi mọi request `/api` mà ứng dụng Next.js không tự trả lời tới Nest:

[[CODE:6]]

Trình duyệt giao tiếp với một origin, origin của Next.js. Một cookie mà Nest đặt, như một session, được lưu cho origin đó và được gửi lại kèm mọi request tới nó, nên nó tới được cả Nest lẫn Next.js, và Nest không cần cấu hình [CORS](/security/cors) nào.

Các rewrite `fallback` chạy sau khi Next.js đã kiểm tra mọi page và route handler của nó, kể cả các route động. Vì vậy một route handler đã có, như `src/app/api/orders/[id]/route.ts`, vẫn tiếp tục trả lời request của nó, và chỉ phần còn lại mới tới Nest. Một path `/api` mà cả hai ứng dụng đều không có sẽ nhận response `404` của Nest. Một rewrite `afterFiles` sẽ chạy trước các route động, và chuyển các request của route handler đó cho Nest.

Đặt `API_URL` cho môi trường development trong `apps/web/.env.development`:

[[CODE:7]]

> warning **Warning** Next.js đọc `rewrites()` khi nó build ứng dụng, nên `API_URL` cũng phải được đặt cho `next build`: một giá trị khác khi ứng dụng khởi động sẽ không thay đổi nơi các rewrite của nó trỏ tới.

Mọi thứ mà một API làm đều đi qua rewrite mà không bị thay đổi: cookie, raw request body cho chữ ký [webhook](/http/webhooks), [server-sent event](/http/server-sent-events) ngay khi được ghi, và [WebSocket](/websockets/gateways) với adapter `ws`. Có hai giới hạn thất bại rất tệ, với lỗi `500` và không có thông báo lỗi hữu ích nào: một request body lớn hơn 10 MB, và một response mất hơn 30 giây mới bắt đầu, chẳng hạn một lời gọi tới language model. Hãy tăng chúng bằng hai tùy chọn thử nghiệm của Next.js:

[[CODE:8]]

Nest cũng thấy server Next.js là client, nên `req.ip` là địa chỉ của nó, và mọi thứ giới hạn request theo địa chỉ IP, như [`@nestjs/throttler`](/security/rate-limiting), sẽ coi mọi khách truy cập của bạn là một. Next.js không tự thêm `X-Forwarded-For`, nhưng nó chuyển tiếp header do một load balancer đứng trước nó đặt. Nếu bạn có load balancer, hãy gọi `app.set('trust proxy', 1)` trên `NestExpressApplication`. Nếu không có, hãy để tắt, nếu không một khách truy cập có thể tự khai bất kỳ địa chỉ nào.

#### Dùng chung schema giữa các ứng dụng

Nest validate một request body theo bất kỳ schema [Standard Schema](https://standardschema.dev/) nào, như một schema Zod (xem [Validation dựa trên schema](/application/validation#schema-based-validation)). Hãy đặt các schema trong một package riêng, `packages/contracts`, và ứng dụng Next.js validate form của nó bằng chính schema mà Nest dùng để kiểm tra request, và cả hai đều dùng các type được suy ra từ nó.

[[CODE:9]]

[[CODE:10]]

[[CODE:11]]

Package được biên dịch, để cả hai ứng dụng import JavaScript thuần cùng các khai báo type của nó. Hãy thêm nó vào cả hai ứng dụng, và build nó (`npm run dev -w @acme/contracts` build lại nó ở mỗi thay đổi):

[[CODE:12]]

Trong Nest, hãy gắn `StandardSchemaValidationPipe` và truyền schema cho `@Body()`:

[[CODE:13]]

[[CODE:14]]

Trong Next.js, một form kiểm tra input của nó bằng cùng schema đó trước khi gửi bất cứ thứ gì:

[[CODE:15]]

Một request không đến từ form của bạn, từ một script hoặc một phiên bản cũ hơn của ứng dụng, vẫn được Nest kiểm tra:

[[CODE:16]]

Để chạy mọi thứ bằng một lệnh, hãy thêm `concurrently` vào thư mục gốc, và hai script vào `package.json` của nó. Package dùng chung phải được build trước các ứng dụng import nó:

[[CODE:17]]

[[CODE:18]]

#### Đăng nhập người dùng

Việc đăng nhập thuộc về Nest, vì API là thứ mà nó bảo vệ. [`@nestjs/authentication`](/security/authentication) giữ session trong một cookie `HttpOnly`, và một form đăng nhập bằng cách post tới `/api/auth/sign-in` qua rewrite, như mọi request khác từ trình duyệt. Chương đó xây dựng nó, và có một thiết lập riêng khi chạy phía sau Next.js.

Module bỏ qua session cookie trên một `POST` từ origin khác, và từ chối các lần đăng nhập từ origin khác, để ngăn cross-site request forgery. Phía sau một rewrite, host riêng của Nest là `localhost:3001` trong khi `Origin` của trình duyệt là `http://localhost:3000`. Các trình duyệt gửi `Sec-Fetch-Site` vẫn đi qua được, nhưng một client chỉ gửi `Origin` sẽ nhận `403`. Vì vậy hãy khai báo origin của Next.js là đáng tin:

[[CODE:19]]

Các request từ mọi origin khác vẫn bị từ chối.

#### Gọi Nest từ server Next.js

Server Component và Server Action chạy trên server Next.js, nên chúng gọi trực tiếp Nest, không qua rewrite. Cookie của trình duyệt không đi kèm những request đó trừ khi bạn chuyển tiếp chúng, nên hãy đặt việc đó vào một helper:

[[CODE:20]]

[[CODE:21]]

> warning **Warning** Một page lấy dữ liệu mà không đọc cookie có thể được render trong lúc `next build`, nên Nest phải truy cập được từ quá trình build, nếu không nó sẽ thất bại với `fetch failed`.

#### Migrate một backend Next.js sang Nest

Chính [hướng dẫn backend](https://nextjs.org/docs/app/guides/backend-for-frontend) của Next.js nói rằng các khả năng backend của nó "are not a full backend replacement" (không thay thế được một backend đầy đủ). Một backend Next.js chạy tốt cho tới khi nó phải là một backend thực sự, và vượt qua điểm đó thì một backend riêng có thể là lựa chọn đơn giản hơn.

##### Tại sao nó có thể đơn giản hơn

Không phải vì ít code hơn. Cùng bốn endpoint (liệt kê, tạo, đọc và hủy một đơn hàng, cho một người dùng đã đăng nhập) có số dòng gần như nhau ở route handler và ở một controller cùng service của Nest. Điều thay đổi là những gì bạn phải nhớ:

| | Route handler | Nest |
| --- | --- | --- |
| Kiểm tra session | Trong mọi handler, ở đây là bốn lần. Một handler quên kiểm tra sẽ thành công khai | Một lần, trong một [global guard](/security/authentication). Một route mới trả lời `401` cho tới khi bạn đánh dấu nó `@Public()` |
| Validate một body | Mỗi handler tự parse nó và tự dựng `400` riêng | `@Body({{ '{' }} schema {{ '}' }})`, và handler chỉ chạy với input hợp lệ |
| Một bản ghi không tồn tại | Mỗi handler tự dựng `404` riêng, và một helper không thể kết thúc request thay cho nó | `throw new NotFoundException()` từ bất cứ đâu, như một service |
| Test logic | Handler đọc `cookies()`, hàm này throw `was called outside a request scope`, nên một test phải mock `next/headers` | Một service là một class: `new OrdersService()`, không có HTTP và không phải mock framework |
| Tìm một endpoint | Mỗi path một file, với path nằm trong tên thư mục | Mỗi resource một controller |
| Scheduled job | Không có gì có sẵn, nên một nền tảng phải gọi một URL | `@Cron()`, trong cùng process với phần còn lại của ứng dụng |
| WebSocket | Không hoạt động ở nơi handler được deploy dưới dạng lambda function, theo chính hướng dẫn đó | [Gateway](/websockets/gateways) |

Đây là một trong bốn endpoint đó ở cả hai phía. Dưới dạng route handler:

[[CODE:22]]

Các handler khác lặp lại những dòng đầu tiên của nó. Trong Nest, guard đã kiểm tra session, và service chứa quy tắc, nơi các method khác có thể tái sử dụng nó và một test có thể tiếp cận nó:

[[CODE:23]]

[[CODE:24]]

[[CODE:25]]

Bạn có thể đi được một phần đường bằng các helper: một wrapper `withSession()`, rồi một cái cho validation, rồi một cái biến lỗi thành response. Đó là một bước hợp lý, và cũng chính là tự viết guard, pipe và exception filter của riêng bạn.

Nó cũng có cái giá. Có thêm một ứng dụng thứ hai cần deploy, một rewrite cần cấu hình, và một bước nhảy mạng giữa một Server Component và dữ liệu của nó. Nếu backend của bạn chỉ là vài handler với một client và không có công việc nền, hãy giữ route handler.

##### Cái gì đi đâu

Hãy viết các endpoint mới trong Nest, và chuyển các endpoint hiện có khi bạn sửa chúng lần tới. Mỗi phần của một backend Next.js đều có nơi để chuyển tới:

| Trong Next.js | Trong Nest |
| --- | --- |
| Một route handler | Một method của [controller](/controllers) |
| Một database query trong Server Component hoặc Server Action | Một [service](/providers) phía sau một endpoint, được gọi qua `api()` |
| `getSession()` ở đầu mọi handler | Global guard của [`@nestjs/authentication`](/security/authentication), và `@CurrentUser()` |
| Tự kiểm tra `request.json()` bằng tay | `@Body({{ '{' }} schema {{ '}' }})` |
| Kiểm tra role bên trong handler | [`@nestjs/authorization`](/security/authorization) |
| Một route handler webhook đọc `request.text()` | `@VerifyWebhook()` từ [`@nestjs/webhooks`](/http/webhooks) |
| Một route cron được nền tảng gọi | `@Cron()` từ [`@nestjs/schedule`](/application/task-scheduling) |
| Công việc được khởi động bằng `after()`, như gửi email | Một [queue](/application/queues), và [`@nestjs/mail`](/application/mail) |

##### Chuyển một route

Viết endpoint trong Nest dưới cùng path, và xóa route handler. URL không thay đổi, nên client cũng không phải thay đổi. Vì route handler đứng trước rewrite, cả hai có thể cùng có trong code cho tới khi bạn xóa route handler.

Sau đó hãy kiểm tra những gì client có thể nhận ra:

- **Status code.** `NextResponse.json()` trả lời `200` trên một `POST`, còn một `POST` của Nest trả lời `201` trừ khi bạn thêm `@HttpCode(200)`.
- **Cấu trúc của lỗi**, giờ là `{{ '{' }} statusCode, message, error {{ '}' }}`. Một [global exception filter](/recipes/express-migration#keep-what-would-change-without-an-error) giữ cấu trúc cũ nếu client phụ thuộc vào nó.
- **Các segment động.** `[id]` trở thành `:id`, và một catch-all `[...path]` trở thành `*path`, với `@Param('path')` là một mảng các segment.

##### Chuyển query ra khỏi page

Một Server Component hoặc Server Action truy vấn trực tiếp database sẽ chuyển sang gửi request thay vào đó, và query được chuyển vào một service của Nest:

[[CODE:26]]

Khi không còn gì trong `apps/web` import database client nữa, hãy gỡ nó khỏi ứng dụng Next.js, để một page không thể đi vòng qua API.

#### Deployment

Hai ứng dụng được deploy riêng. Bất kể nền tảng nào, thứ tự đều giống nhau: build `@acme/contracts`, rồi đến các ứng dụng, với `API_URL` được đặt cho `next build`.

Nest chạy ở bất cứ đâu Node.js chạy được (xem [Deployment](/deployment)). Nếu bạn deploy ứng dụng Next.js trên Vercel, hãy đặt `API_URL` trong môi trường của nó thành địa chỉ của Nest. Vercel cũng có thể [deploy Nest](https://vercel.com/docs/frameworks/backend/nestjs), như một project riêng. Các client khác, như một ứng dụng di động, gọi trực tiếp địa chỉ của Nest, và chỉ cần cấu hình [CORS](/security/cors) nếu chúng chạy trên trình duyệt ở một origin khác.
