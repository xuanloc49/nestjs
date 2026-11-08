# Tài liệu NestJS (bản dịch tiếng Việt)

Đây là bản dịch tiếng Việt của tài liệu chính thức NestJS tại <https://docs.nestjs.com/>.

- Nguồn: repository [nestjs/docs.nestjs.com](https://github.com/nestjs/docs.nestjs.com), thư mục `content/`, commit `85edfd9d690c227f3b253391ab4f807e5d700052` (2026-11-06).
- Bản quyền nội dung gốc: Copyright (c) 2017-present Kamil Myśliwiec, phát hành theo MIT License. Toàn văn license nằm trong file [LICENSE](LICENSE) đi kèm.
- Bản dịch giữ nguyên cấu trúc thư mục và tên file của `content/`, nên có thể thay thế trực tiếp vào repository gốc để build.

## Nguyên tắc dịch

- Code, lệnh, tên API, đường dẫn, URL và cú pháp markdown/HTML được giữ nguyên tuyệt đối. Các code block được ráp lại từ bản gốc bằng script, không qua tay người dịch.
- Thuật ngữ theo cách developer Việt dùng hằng ngày. Xem [THUAT-NGU.md](THUAT-NGU.md).
- Heading đã dịch luôn kèm anchor mang slug tiếng Anh gốc, nên mọi link dạng `#installation` hay `/cli/usages#one-file-projects` vẫn dẫn đúng chỗ.

## Mục lục

Thứ tự theo menu của docs.nestjs.com.

### [Giới thiệu](introduction.md)

### Tổng quan

- [Những bước đầu tiên](first-steps.md)
- [Controllers](controllers.md)
- [Providers](components.md)
- [Modules](modules.md)
- [Middleware](middlewares.md)
- [Exception filters](exception-filters.md)
- [Pipes](pipes.md)
- [Guards](guards.md)
- [Interceptors](interceptors.md)
- [Custom route decorator](custom-decorators.md)

### Kiến thức nền tảng

- [Custom provider](fundamentals/dependency-injection.md)
- [Provider bất đồng bộ](fundamentals/async-components.md)
- [Dynamic module](fundamentals/dynamic-modules.md)
- [Injection scope](fundamentals/provider-scopes.md)
- [Circular dependency](fundamentals/circular-dependency.md)
- [Module reference](fundamentals/module-reference.md)
- [Lazy loading module](fundamentals/lazy-loading-modules.md)
- [Execution context](fundamentals/execution-context.md)
- [Lifecycle event](fundamentals/lifecycle-events.md)
- [Discovery service](fundamentals/discovery-service.md)
- [Không phụ thuộc nền tảng](fundamentals/platform-agnosticism.md)
- [Testing](fundamentals/unit-testing.md)

### Ứng dụng

- [Cấu hình](application/configuration.md)
- [Validation](application/validation.md)
- [Serialization](application/serialization.md)
- [Logger](application/logger.md)
- [Event](application/events.md)
- [Task scheduling](application/task-scheduling.md)
- [Queue](application/queues.md)
- [HTTP client](application/http-client.md)
- [Đa ngôn ngữ](application/i18n.md)
- [Mail](application/mail.md)
- [Lưu trữ file](application/file-storage.md)

### Dữ liệu

- [Tổng quan](data/overview.md)
- [TypeORM](data/typeorm.md)
- [Drizzle](data/drizzle.md)
- [Mongo](data/mongo.md)
- [Prisma](data/prisma.md)
- [MikroORM](data/mikroorm.md)
- [Sequelize](data/sequelize.md)
- [Caching](data/caching.md)

### Bảo mật

- [Xác thực](security/authentication.md)
- [Phân quyền](security/authorization.md)
- [Mã hóa và hashing](security/encryption-hashing.md)
- [Security header](security/helmet.md)
- [CORS](security/cors.md)
- [Bảo vệ CSRF](security/csrf.md)
- [Giới hạn tốc độ](security/rate-limiting.md)

### HTTP

- [Versioning](http/versioning.md)
- [Cookie](http/cookies.md)
- [Session](http/sessions.md)
- [Upload và stream file](http/file-upload.md)
- [Nén response](http/compression.md)
- [Stream response](http/streaming-responses.md)
- [Server-Sent Events](http/server-sent-events.md)
- [Model-View-Controller](http/mvc.md)
- [HTTP adapter](http/performance.md)
- [Webhook](http/webhooks.md)

### Observability

- [Tổng quan](observability/overview.md)
- [SDK](observability/sdk.md)
- [Instrumentation thủ công](observability/manual-instrumentation.md)
- [Distributed tracing](observability/distributed-tracing.md)
- [Error monitoring](observability/error-monitoring.md)
- [Dashboard](observability/dashboard.md)
- [Production rules](observability/production-rules.md)
- [MCP server](observability/mcp-server.md)
- [OpenTelemetry](observability/opentelemetry.md)
- [Chọn một APM](observability/choosing-an-apm.md)

### Độ tin cậy

- [Resilience](reliability/resilience.md)
- [Idempotency key](reliability/idempotency.md)
- [Outbox](reliability/outbox.md)
- [Durable workflow](reliability/workflows.md)
- [Distributed lock](reliability/locks.md)
- [Health check](reliability/terminus.md)

### GraphQL

- [Quick start](graphql/quick-start.md)
- [Resolver](graphql/resolvers-map.md)
- [Mutation](graphql/mutations.md)
- [Subscription](graphql/subscriptions.md)
- [Scalar](graphql/scalars.md)
- [Directive](graphql/directives.md)
- [Interface](graphql/interfaces.md)
- [Union và Enum](graphql/unions-and-enums.md)
- [Field middleware](graphql/field-middleware.md)
- [Mapped type](graphql/mapped-types.md)
- [Plugin với Apollo](graphql/plugins.md)
- [Độ phức tạp](graphql/complexity.md)
- [Extension](graphql/extensions.md)
- [CLI Plugin](graphql/cli-plugin.md)
- [Sinh SDL](graphql/schema-generator.md)
- [Dùng chung model](graphql/sharing-models.md)
- [Các tính năng khác](graphql/guards-interceptors.md)
- [Federation](graphql/federation.md)

### WebSockets

- [Gateway](websockets/gateways.md)
- [Exception filter](websockets/exception-filters.md)
- [Pipe](websockets/pipes.md)
- [Guard](websockets/guards.md)
- [Interceptor](websockets/interceptors.md)
- [Adapter](websockets/adapter.md)

### MCP

- [Model Context Protocol (MCP)](mcp/overview.md)
- [Primitive](mcp/primitives.md)
- [Transport](mcp/transports.md)
- [Testing](mcp/testing.md)
- [Migration](mcp/migration.md)

### AI

- [AI](ai/overview.md)
- [Model](ai/models.md)
- [Tool](ai/tools.md)
- [Agent](ai/agents.md)
- [Embedding](ai/embeddings.md)
- [Testing](ai/testing.md)

### Microservices

- [Tổng quan](microservices/basics.md)
- [Redis](microservices/redis.md)
- [MQTT](microservices/mqtt.md)
- [NATS](microservices/nats.md)
- [RabbitMQ](microservices/rabbitmq.md)
- [Kafka](microservices/kafka.md)
- [gRPC](microservices/grpc.md)
- [Custom transporter](microservices/custom-transport.md)
- [Exception filter](microservices/exception-filters.md)
- [Pipe](microservices/pipes.md)
- [Pre-request hook](microservices/pre-request-hooks.md)
- [Guard](microservices/guards.md)
- [Interceptor](microservices/interceptors.md)

### [Deployment](deployment.md)

### [Ứng dụng standalone](application-context.md)

### CLI

- [Tổng quan](cli/overview.md)
- [Workspace](cli/workspaces.md)
- [Library](cli/libraries.md)
- [Tham khảo lệnh CLI](cli/usages.md)
- [Nest CLI và script](cli/scripts.md)

### OpenAPI

- [Giới thiệu](openapi/introduction.md)
- [Type và parameter](openapi/types-and-parameters.md)
- [Operation](openapi/operations.md)
- [Bảo mật](openapi/security.md)
- [Mapped type](openapi/mapped-types.md)
- [Decorator](openapi/decorators.md)
- [CLI Plugin](openapi/cli-plugin.md)
- [Các tính năng khác](openapi/other-features.md)

### Recipes

- [Read-Eval-Print-Loop (REPL)](recipes/repl.md)
- [CRUD generator (chỉ TypeScript)](recipes/crud-generator.md)
- [SWC](recipes/swc.md)
- [Passport (xác thực)](recipes/passport.md)
- [Hot Reload](recipes/hot-reload.md)
- [Router module](recipes/router-module.md)
- [Migrate từ Fastify](recipes/fastify-migration.md)
- [CQRS](recipes/cqrs.md)
- [Serve Static](recipes/serve-static.md)
- [Next.js](recipes/nextjs.md)
- [Supabase](recipes/supabase.md)
- [Nest Commander](recipes/nest-commander.md)
- [Async Local Storage](recipes/async-local-storage.md)
- [Socket activation](recipes/socket-activation.md)
- [Migrate từ Express](recipes/express-migration.md)

### FAQ

- [Nest so với Fastify, Express và Hono](faq/nest-vs-fastify-express-hono.md)
- [Serverless](faq/serverless.md)
- [Cloudflare Workers](faq/cloudflare-workers.md)
- [HTTP adapter](faq/http-adapter.md)
- [Kết nối keep-alive](faq/keep-alive-connections.md)
- [Global prefix](faq/global-prefix.md)
- [Raw body](faq/raw-body.md)
- [Ứng dụng hybrid](faq/hybrid-application.md)
- [HTTPS và nhiều server](faq/multiple-servers.md)
- [Vòng đời request](faq/request-lifecycle.md)
- [Các lỗi thường gặp](faq/errors.md)

### Devtools

- [Tổng quan](devtools/overview.md)
- [Tích hợp CI/CD](devtools/ci-cd.md)

### [Hướng dẫn migration](migration.md)

### Khám phá

- [Ai đang dùng Nest?](discover/who-uses.md)

### [Ủng hộ](support.md)

### Trang khác

- [Tư vấn NestJS chính thức](enterprise.md)
