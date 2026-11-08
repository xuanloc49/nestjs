### Không phụ thuộc nền tảng

Nest là một framework không phụ thuộc nền tảng (platform-agnostic). Bạn có thể phát triển những **phần logic tái sử dụng được** và dùng chúng trong nhiều loại ứng dụng khác nhau. Ví dụ, hầu hết các thành phần có thể được dùng lại nguyên vẹn trên các HTTP server framework khác nhau bên dưới (ví dụ Express và Fastify), và thậm chí trên các _loại_ ứng dụng khác nhau (ví dụ HTTP server, microservice với các transport layer khác nhau, và WebSocket).

#### Viết một lần, dùng mọi nơi <a id="build-once-use-everywhere"></a>

Phần **Overview** của tài liệu chủ yếu trình bày các kỹ thuật code dùng HTTP server framework (ví dụ app cung cấp REST API hoặc app render phía server theo kiểu MVC). Tuy nhiên, tất cả các building block đó đều dùng được trên các transport layer khác ([microservice](/microservices/basics) hoặc [WebSocket](/websockets/gateways)).

Nest cũng có sẵn một module [GraphQL](/graphql/quick-start) chuyên dụng. Bạn có thể dùng GraphQL làm API layer thay thế qua lại với REST API.

Ngoài ra, tính năng [application context](/standalone-applications) cho phép bạn xây dựng bất kỳ loại ứng dụng Node.js nào trên nền Nest, kể cả cron job và app CLI.

Nest hướng tới việc trở thành một nền tảng hoàn chỉnh cho các app Node.js, mang lại mức độ mô-đun hóa và khả năng tái sử dụng cao hơn cho ứng dụng của bạn. Viết một lần, dùng mọi nơi.
