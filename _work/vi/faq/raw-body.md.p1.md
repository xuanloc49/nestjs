### Raw body

Một trong những lý do phổ biến nhất để truy cập raw body của request là xác minh chữ ký webhook. Việc xác minh chữ ký webhook thường cần request body chưa được parse để tính một HMAC hash.

> warning **Warning** Tính năng này chỉ hoạt động nếu middleware body parser global có sẵn được bật, tức là bạn không được truyền `bodyParser: false` khi tạo ứng dụng.

#### Dùng với Express

Trước tiên, hãy bật tùy chọn khi tạo ứng dụng Nest Express:

[[CODE:1]]

Để truy cập raw body của request trong một controller, hãy gán type cho request bằng interface tiện ích `RawBodyRequest`, interface này cung cấp field `rawBody`:

[[CODE:2]]

#### Đăng ký một parser khác

Mặc định, chỉ các parser `json` và `urlencoded` được đăng ký. Để dùng một parser khác, hãy đăng ký nó một cách tường minh.

Ví dụ, để đăng ký một parser `text`:

[[CODE:3]]

> warning **Warning** Hãy đảm bảo bạn truyền đúng type ứng dụng cho lời gọi `NestFactory.create()`. Với ứng dụng Express, type đúng là `NestExpressApplication`; nếu không, method `useBodyParser()` sẽ không được tìm thấy.

#### Giới hạn kích thước của body parser

Nếu ứng dụng của bạn cần parse các body lớn hơn mặc định `100kb` của Express, hãy tăng giới hạn:

[[CODE:4]]

Method `useBodyParser()` tôn trọng tùy chọn `rawBody` được truyền trong các tùy chọn của ứng dụng.

#### Dùng với Fastify

Trước tiên, hãy bật tùy chọn khi tạo ứng dụng Nest Fastify:

[[CODE:5]]

Để truy cập raw body của request trong một controller, hãy gán type cho request bằng interface tiện ích `RawBodyRequest`, interface này cung cấp field `rawBody`:

[[CODE:6]]

#### Đăng ký một parser khác

Mặc định, chỉ các parser `application/json` và `application/x-www-form-urlencoded` được đăng ký. Để dùng một parser khác, hãy đăng ký nó một cách tường minh.

Ví dụ, để đăng ký một parser `text/plain`:

[[CODE:7]]

> warning **Warning** Hãy đảm bảo bạn truyền đúng type ứng dụng cho lời gọi `NestFactory.create()`. Với ứng dụng Fastify, type đúng là `NestFastifyApplication`; nếu không, method `useBodyParser()` sẽ không được tìm thấy.

#### Giới hạn kích thước của body parser

Nếu ứng dụng của bạn cần parse các body lớn hơn mặc định 1 MiB của Fastify, hãy tăng giới hạn:

[[CODE:8]]

Method `useBodyParser()` tôn trọng tùy chọn `rawBody` được truyền trong các tùy chọn của ứng dụng.
