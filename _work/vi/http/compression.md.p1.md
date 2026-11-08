### Nén response

Nén response có thể giảm đáng kể kích thước body của response, giúp web app load nhanh hơn.

Với các website **traffic cao** trên production, chúng tôi rất khuyên bạn chuyển việc nén ra khỏi application server, thường là sang một reverse proxy (ví dụ Nginx). Trong trường hợp đó, đừng dùng compression middleware.

#### Dùng với Express (mặc định)

Dùng package middleware [compression](https://github.com/expressjs/compression) để bật nén response. Nó hỗ trợ các kiểu encoding gzip, deflate và Brotli, và chọn một kiểu dựa trên header `Accept-Encoding` của request.

Đầu tiên, cài các package cần thiết:

[[CODE:1]]

Sau khi cài xong, áp dụng compression middleware ở cấp global:

[[CODE:2]]

#### Dùng với Fastify

Nếu bạn dùng `FastifyAdapter`, hãy dùng plugin [@fastify/compress](https://github.com/fastify/fastify-compress) thay vào đó:

[[CODE:3]]

Sau khi cài xong, đăng ký plugin `@fastify/compress`. Mặc định nó nén mọi response đủ điều kiện.

> warning **Warning** Hãy chắc chắn rằng bạn truyền type `NestFastifyApplication` khi tạo ứng dụng. Nếu không, method `register()` sẽ không có sẵn để áp dụng plugin.

[[CODE:4]]

Mặc định, `@fastify/compress` dùng encoding đầu tiên mà client chấp nhận, theo thứ tự ưu tiên sau: `zstd` (trên các phiên bản Node.js có hỗ trợ), `br` (Brotli), `gzip` và `deflate`. Brotli đạt tỉ lệ nén cao, nhưng các mức chất lượng cao thì chậm. Plugin mặc định đặt chất lượng Brotli (`BROTLI_PARAM_QUALITY`) là 4 thay vì mặc định 11 của zlib. Bạn có thể đặt nó trong khoảng từ 0 (nhanh nhất) tới 11 (output nhỏ nhất), đánh đổi giữa thời gian nén và kích thước response. Hãy tinh chỉnh giá trị này theo khối lượng công việc của bạn. Ví dụ sau đặt chất lượng một cách tường minh:

[[CODE:5]]

Cách khác là giới hạn `@fastify/compress` chỉ dùng gzip và deflate. Response có thể lớn hơn, nhưng được nén nhanh hơn.

Để chỉ định các encoding, hãy truyền tùy chọn `encodings` trong tham số thứ hai của `app.register()`:

[[CODE:6]]

Cấu hình này bảo `@fastify/compress` chỉ dùng các encoding gzip và deflate, ưu tiên gzip khi client hỗ trợ cả hai.
