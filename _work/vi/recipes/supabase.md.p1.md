### Supabase

Supabase cho một ứng dụng một database Postgres, chức năng đăng nhập, lưu trữ file và một API mà trình duyệt có thể gọi trực tiếp, bao phủ được rất nhiều thứ mà không cần backend. Những gì nó bỏ ngỏ là các công việc cần một secret, một lần retry hay một đồng hồ: Stripe webhook, scheduled job, queue, một admin API. Nest đảm nhận phần việc đó bên cạnh Supabase, trên cùng database và cho cùng người dùng.

| Ở lại Supabase | Đặt trong Nest |
| --- | --- |
| Đăng ký, đăng nhập và đặt lại mật khẩu | Kiểm tra ai đang gọi, và họ được làm gì |
| Postgres, migration của nó và row level security | Quy tắc nghiệp vụ, và các query trải qua nhiều bảng |
| Đọc và ghi từ trình duyệt mà row level security bao phủ | Mọi thứ cần secret: thanh toán, email, API khác |
| Storage và Realtime | Stripe webhook, scheduled job, queue và một admin API |

Trình duyệt tiếp tục gọi trực tiếp Supabase cho những gì row level security bao phủ, và gọi Nest bằng cùng access token cho phần còn lại.

Nếu tất cả những gì bạn cần là một hai hàm ngắn, [Edge Function](https://supabase.com/docs/guides/functions) có thể là đủ, không cần server nào phải vận hành. Chúng có [giới hạn về thời gian CPU và thời lượng](https://supabase.com/docs/guides/functions/limits) và không có chỗ để chạy worker của một queue, nên Nest phù hợp hơn khi bạn đã có job, queue hoặc nhiều route dùng chung code.

Recipe này xây dựng một ứng dụng như vậy trên Supabase stack chạy local, để bạn có thể chạy từng bước trong lúc đọc. [Module hoàn chỉnh](/recipes/supabase#the-finished-module) cho thấy các phần được nối với nhau thế nào.

#### Tạo các project

Stack local cần Docker.

[[CODE:1]]

`npx supabase status -o env` in ra các URL và key của stack. Hãy đặt `API_URL`, `PUBLISHABLE_KEY`, `SECRET_KEY` và `DB_URL` vào `.env`, dưới những tên mà recipe này đọc:

[[CODE:2]]

> warning **Warning** Secret key bỏ qua row level security. Nó chỉ thuộc về server, và không bao giờ được đưa vào bất cứ thứ gì bạn ship cho trình duyệt hay ứng dụng di động.

> info **Hint** Một project được host có cùng các key trong dashboard của nó. Supabase đang [deprecate](https://supabase.com/docs/guides/api/api-keys) các key cũ `anon` và `service_role` trước cuối năm 2026, nên hãy dùng hai key này.

Load `.env` bằng [`@nestjs/config`](/application/configuration):

[[CODE:3]]

[[CODE:4]]

Giữ nó đứng đầu trong `imports`, vì các module bạn sẽ thêm sau nó đọc `process.env` ngay khi được khai báo. Một module được khai báo trong file khác đọc nó sớm hơn, khi file được import, nên hãy dùng `forRootAsync()` cho những gì bạn đăng ký ở đó.

#### Định nghĩa một bảng

Schema vẫn nằm trong các migration của Supabase:

[[CODE:5]]

Viết bảng vào file mà lệnh này tạo trong `supabase/migrations`, với một policy chỉ cho phép người dùng truy cập các dòng của chính họ. `auth.uid()` là người dùng sở hữu access token của request:

[[CODE:6]]

Áp dụng nó vào database local:

[[CODE:7]]

> warning **Warning** API của Supabase phục vụ các bảng trong schema `public` cho bất kỳ ai có publishable key, và key đó nằm trong code trình duyệt của bạn. Hãy bật row level security trên mọi bảng bạn tạo ở đó, kể cả những bảng chỉ Nest dùng. Khi đã bật mà không có policy nào, key đó không đọc được gì.

#### Xác minh token của Supabase

Supabase Auth ký một access token cho mỗi người dùng đã đăng nhập, và công bố các public key dùng để xác minh nó. [`@nestjs/authentication`](/security/authentication) có thể xác minh token từ một issuer khác, nên Nest không cần secret nào từ Supabase để biết ai đang gọi:

[[CODE:8]]

[[CODE:9]]

Role lấy từ `app_metadata`, thứ mà chỉ server của bạn mới thay đổi được. Một người dùng đã đăng nhập có thể tự thay đổi `user_metadata` của mình bằng `supabase.auth.updateUser()`, nên đừng bao giờ dựa vào nó để đưa ra quyết định.

Đăng ký module và provider:

[[CODE:10]]

Module đăng ký một global guard, nên giờ mọi route đều trả lời `401 Unauthorized` khi không có token hợp lệ, kể cả token có chữ ký sai, issuer hoặc audience khác, hoặc đã hết hạn. Đánh dấu một route vẫn mở bằng `@Public()`, và đọc người dùng bằng `@CurrentUser()`:

[[CODE:11]]

> info **Hint** Một project vẫn dùng JWT secret cũ sẽ ký token bằng nó và không công bố key nào. Hãy truyền `key: process.env.SUPABASE_JWT_SECRET` thay cho `jwks`, cho tới khi bạn [chuyển sang signing key](https://supabase.com/docs/guides/auth/signing-keys).

#### Gọi Nest từ trình duyệt

Trình duyệt gửi access token mà Supabase đã cấp cho nó. `getSession()` làm mới token khi nó đã hết hạn:

[[CODE:12]]

Nếu trình duyệt gọi Nest trên một origin khác, hãy [cho phép origin đó](/security/cors) khi ứng dụng khởi động:

[[CODE:13]]

#### Query với tư cách người dùng, hoặc với tư cách server

`@supabase/supabase-js` là một client cho REST API của database. Hãy sinh type từ schema của bạn, để một query trên một bảng hoặc cột không tồn tại sẽ không biên dịch được, và chạy lại lệnh này sau mỗi migration:

[[CODE:14]]

Tạo một client cho server, và mỗi request một client cho người dùng. Một client không giữ kết nối database nào, nên việc này rẻ:

[[CODE:15]]

Một decorator nhỏ đọc token mà guard đã xác minh:

[[CODE:16]]

Hãy ưu tiên `forUser()` trong một route hành động thay cho một người dùng. Các policy của bạn vẫn tiếp tục được áp dụng, nên một query quên bộ lọc vẫn chỉ trả về các dòng của người dùng đó, và một câu insert cho người khác sẽ bị từ chối:

[[CODE:17]]

Dùng `admin` cho những gì server tự làm, nơi không có người dùng nào liên quan, như trong một job hoặc một webhook.

#### Query trực tiếp Postgres

Với transaction và các query mà REST API không diễn đạt được, hãy kết nối tới database bằng [`@nestjs/drizzle`](/data/drizzle) hoặc một [tích hợp database](/data/overview) khác. Các webhook và job bên dưới cũng dùng kết nối này:

[[CODE:18]]

[[CODE:19]]

Ở local, `DATABASE_URL` là `DB_URL` của stack. Trên một project được host, Nest là một backend chạy liên tục, nên hãy dùng [connection string trực tiếp](https://supabase.com/docs/guides/database/connecting-to-postgres), hoặc shared pooler ở session mode nếu host của bạn chỉ có IPv4. Transaction mode của pooler không hỗ trợ prepared statement, cũng không hỗ trợ `LISTEN` mà backend PostgreSQL của BullMQ dùng.

Các migration của Supabase vẫn là nguồn sự thật, nên Drizzle schema chỉ mô tả các bảng cần query:

[[CODE:20]]

> warning **Warning** Row level security không bảo vệ các query này. Role `postgres` bỏ qua nó, nên một query không có bộ lọc sẽ trả về các dòng của mọi người dùng, và mỗi query phải tự kiểm tra chủ sở hữu.

Để giữ các policy của bạn trên một query trực tiếp, hãy chạy nó trong một transaction với role `authenticated`, kèm các claim mà `auth.uid()` đọc:

[[CODE:21]]

Cả hai thiết lập đều kết thúc cùng transaction, nên chúng không bao giờ ảnh hưởng tới query tiếp theo trên kết nối đó. Đây là từng cách đặt cạnh nhau, với `@CurrentSession()` cung cấp cho route các claim đã được xác minh:

[[CODE:22]]

#### Bảo vệ một admin API

Một admin API là thứ mà trình duyệt không tự làm được, vì nó cần secret key. Hãy giữ role của người dùng trong `app_metadata`, thứ mà `SupabaseAuth` đã đọc, và đặt nó từ server:

[[CODE:23]]

Role nằm trong token tiếp theo của người dùng, nên một người đã đăng nhập sẽ có nó khi token của họ được làm mới, mặc định trong vòng một giờ.

Kiểm tra nó bằng [`@nestjs/authorization`](/security/authorization):

[[CODE:24]]

[[CODE:25]]

[[CODE:26]]

Đăng ký module bằng `AuthorizationModule.forRoot({{ '{' }} globalGuard: false {{ '}' }})`, và `AdminPolicy` trong `providers`. Global guard của nó được bật mặc định và từ chối mọi route không có `@Can()`, điều này cũng sẽ đóng các route ở trên. Một khách nhận `401`, một người dùng không có role nhận `403`.

#### Nhận Stripe webhook

[`@nestjs/webhooks`](/http/webhooks) xác minh chữ ký của một webhook và ghi nhớ những event nào nó đã xử lý. Nó giữ trạng thái trong database của bạn, qua `@nestjs/outbox`, trong các schema riêng. API của Supabase không phục vụ các schema đó, nên chúng vẫn là riêng tư:

[[CODE:27]]

Chữ ký bao phủ chính xác các byte mà Stripe đã gửi, nên hãy tạo ứng dụng với `rawBody`:

[[CODE:28]]

Khai báo bên gửi trong `receivers` của module, với signing secret lấy từ dashboard Stripe hoặc từ `stripe listen`. Ứng dụng này chỉ nhận webhook, nên nó không cần background worker nào:

[[CODE:29]]

Đăng ký hai store trong `providers`. `migrate: true` tạo các schema của chúng lúc khởi động, phù hợp cho development (xem [Deployment](/recipes/supabase#deployment) cho production):

[[CODE:30]]

Thêm một bảng cho những gì webhook thay đổi. Chỉ Nest đọc nó, và row level security không có policy giữ nó khỏi trình duyệt. Thêm nó vào một migration mới:

[[CODE:31]]

[[CODE:32]]

Route là `@Public()`, vì chữ ký là thứ xác thực nó, và một chữ ký không hợp lệ sẽ nhận `401`. `processInTransaction()` ghi lại id của event trong cùng transaction với thay đổi của bạn, nên một lần gửi lại không thay đổi gì:

[[CODE:33]]

Để chạy thử, hãy chuyển tiếp event tới ứng dụng bằng [Stripe CLI](https://docs.stripe.com/stripe-cli), công cụ này in ra signing secret để đặt vào `STRIPE_WEBHOOK_SECRET`:

[[CODE:34]]

#### Chạy scheduled job

Có hai cách để chạy một job trong Nest. Cả hai đều hoạt động trên bất kỳ số instance nào, và mỗi lần chạy diễn ra trên một instance:

|  | `@nestjs/schedule` với `@nestjs/locks` | BullMQ |
| --- | --- | --- |
| **Chạy ở đâu** | Trong instance đang giữ lease | Trong một worker nhận job |
| **Nếu một lần chạy thất bại** | Nó chờ tick tiếp theo | Nó retry, kèm backoff |
| **Nếu mọi instance đều down** | Tick bị lỡ | Job chờ trong queue |
| **Thêm gì vào Postgres** | Một bảng | Một schema riêng |
| **Nó làm thêm gì** | Không gì khác | Job được đưa vào queue từ code của bạn, độ ưu tiên và flow |
| **Chọn nó cho** | Một job an toàn khi bỏ qua, vì tick tiếp theo sẽ bù lại | Một job không được mất, hoặc chạy lâu |

Cả hai đều có thể gọi cùng một đoạn code:

[[CODE:35]]

> info **Hint** [Supabase Cron](https://supabase.com/docs/guides/cron) lên lịch SQL bên trong Postgres, không có ứng dụng nào tham gia. Nó rất hợp với một job chỉ toàn SQL, như xóa các dòng cũ.

##### Với `@nestjs/schedule` và `@nestjs/locks`

[`@nestjs/schedule`](/application/task-scheduling) chạy một job bên trong ứng dụng, cạnh đoạn code mà nó gọi. Đứng riêng, nó chạy job trên mọi instance. [`@nestjs/locks`](/reliability/locks) thêm `@OnOneInstance()`: instance đầu tiên kích hoạt sẽ lấy một lease và chạy mọi tick chừng nào nó còn sống, còn các instance khác bỏ qua chúng. Khi nó dừng, một instance khác tiếp quản, khoảng một giây sau một lần shutdown bình thường và trong vòng 30 giây sau một lần crash:

[[CODE:36]]

[[CODE:37]]

[[CODE:38]]

Lease phải nằm ở nơi mà mọi instance dùng chung, và trong production ứng dụng từ chối khởi động nếu chỉ có store trong bộ nhớ mặc định. Hãy giữ nó trong database của bạn, với một bảng trong một migration mới:

[[CODE:39]]

Sau đó copy bảng Drizzle và `DrizzleLockStore` từ [Giữ lock trong database của bạn](/reliability/locks#keep-locks-in-your-database), và thêm store vào `providers`.

##### Với BullMQ

[BullMQ](/application/queues) giữ job trong một queue, kèm retry và backoff. Nó thường chạy trên Redis, và cũng có một backend PostgreSQL, nên trên Supabase nó có thể dùng database bạn đã có:

[[CODE:40]]

[[CODE:41]]

`migrate: true` tạo schema `bullmq` lúc khởi động, schema mà API của Supabase không phục vụ. Migration lấy một advisory lock, nên nhiều instance khởi động cùng lúc chỉ áp dụng nó một lần.

> info **Hint** Để dùng Redis, hãy cài `ioredis` và thay các tùy chọn đó bằng `connection: {{ '{' }} host, port {{ '}' }}`. Không có gì khác thay đổi.

Một job scheduler tạo job ở mỗi tick. Id giúp nó là một lịch chạy duy nhất, bất kể có bao nhiêu instance khai báo nó:

[[CODE:42]]

Processor chạy nó, trên bất kỳ instance nào đang rảnh:

[[CODE:43]]

Cùng queue đó nhận job từ code của bạn, chẳng hạn một route không nên chờ việc gửi email. Inject nó bằng `@InjectQueue('billing')`, và thêm một case cho job vào processor:

[[CODE:44]]

#### Cấp quyền upload file

Một trình duyệt có thể upload trực tiếp lên Supabase Storage, dưới các policy trên bảng `storage.objects`. Khi quyết định thuộc về server, như một hạn mức hoặc một gói trả phí, hãy giữ bucket ở chế độ riêng tư và để Nest ký cho từng lần upload. Tạo bucket trong một migration:

[[CODE:45]]

[[CODE:46]]

Sau đó trình duyệt upload thẳng lên Supabase, nên file không bao giờ đi qua ứng dụng của bạn:

[[CODE:47]]

Để trả một file về, `createSignedUrl(path, 60)` trên admin client tạo một link hoạt động trong 60 giây.

#### Test với stack local

Một end-to-end test có thể dùng token thật và các policy thật của bạn, vì stack cung cấp cả hai. Hãy đặt nó trong `test/`, và chạy `npx supabase start` cùng `npx supabase db reset` trước khi chạy test:

[[CODE:48]]

#### Chuyển một Edge Function sang Nest

Phần lớn một function đều có thành phần tương ứng trực tiếp, và bạn có thể chuyển chúng từng cái một, vì cả hai dùng cùng token và database:

| Trong một Edge Function | Trong Nest |
| --- | --- |
| Đọc header `Authorization` và gọi `supabase.auth.getUser()` | `SupabaseAuth` và `@CurrentUser()` |
| Một client được tạo với header của bên gọi | `SupabaseService.forUser()` |
| Một client được tạo với secret key | `SupabaseService.admin` |
| Tự xác minh chữ ký của Stripe bằng tay | `@VerifyWebhook('stripe')` |
| `pg_cron` gọi function qua HTTP | `@Cron()`, hoặc một job scheduler của BullMQ |
| `supabase secrets set` | Biến môi trường của host |
| `supabase.functions.invoke('name')` trên trình duyệt | `fetch()` kèm access token |

#### Module hoàn chỉnh

Đây là mọi thứ ở trên được nối lại với nhau, với cả hai cách chạy job, bạn sẽ giữ một trong hai:

[[CODE:49]]

[[CODE:50]]

`enableShutdownHooks()` cho phép một job đang chạy hoàn tất và chuyển lease của nó đi khi một lần deploy dừng một instance.

#### Deployment

Nest được deploy riêng với Supabase, trên bất cứ thứ gì chạy được Node.js (xem [Deployment](/deployment)). Hãy host nó gần region của database, vì mọi query đều phải đi qua khoảng cách đó.

Áp dụng các migration lên project được host:

[[CODE:51]]

Đặt cùng các biến môi trường trên host của bạn, với giá trị của project được host và connection string từ [Query trực tiếp Postgres](/recipes/supabase#query-postgres-directly). Mỗi instance mở các kết nối riêng, cho Drizzle và cho BullMQ, nên hãy tính chúng vào [giới hạn kết nối](https://supabase.com/docs/guides/database/connection-management) của project.

Các webhook store không nên thay đổi schema trong lúc một phiên bản mới đang boot, giữa một lần rolling deploy. Hãy bỏ `migrate: true` khỏi hai store đó, và áp dụng migration của chúng như một bước trước khi phiên bản mới khởi động, với `DATABASE_URL` được đặt. Migration của BullMQ có thể giữ nguyên, vì nó chạy trong một transaction dưới một advisory lock:

[[CODE:52]]
