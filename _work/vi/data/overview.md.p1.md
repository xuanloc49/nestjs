### Tổng quan

Nest không phụ thuộc vào database cụ thể nào, nên bạn có thể tích hợp nó với bất kỳ database SQL hay NoSQL nào. Ở mức cơ bản nhất, kết nối Nest với một database nghĩa là load driver Node.js phù hợp cho database đó, giống như bạn làm với [Express](https://expressjs.com/en/guide/database-integration.html) hay Fastify, rồi cung cấp client cho phần còn lại của ứng dụng thông qua một [provider](/providers).

Hầu hết ứng dụng làm việc ở mức trừu tượng cao hơn, với một ORM hoặc query builder. Các chương trong mục này trình bày những tích hợp sau:

- **[TypeORM](/data/typeorm)** (`@nestjs/typeorm`): một ORM với entity dựa trên decorator và repository pattern. Nó hỗ trợ hầu hết database SQL, cũng như MongoDB.
- **[Drizzle](/data/drizzle)** (`@nestjs/drizzle`): một ORM nhẹ, ưu tiên TypeScript. Bạn khai báo bảng bằng các hàm thông thường và viết query bằng một query builder giống SQL, và Drizzle suy ra type của mọi kết quả từ schema.
- **[MongoDB](/data/mongodb)** (`@nestjs/mongoose`): schema và model của [Mongoose](https://mongoosejs.com/) cho MongoDB.
- **[Prisma](/data/prisma)**: một ORM sinh ra client type-safe từ một file schema. Nó không có package riêng cho Nest: bạn cung cấp client được sinh ra thông qua một provider.
- **[MikroORM](/data/mikroorm)** (`@mikro-orm/nestjs`, do team MikroORM duy trì): một ORM dựa trên các pattern Data Mapper, Unit of Work và Identity Map.
- **[Sequelize](/data/sequelize)** (`@nestjs/sequelize`): một ORM dựa trên promise cho database SQL. Với package `sequelize-typescript`, bạn khai báo model bằng decorator.

Team Nest duy trì các package `@nestjs/typeorm`, `@nestjs/drizzle`, `@nestjs/mongoose` và `@nestjs/sequelize`. Chúng bổ sung các tính năng đặc thù của Nest, như inject repository hoặc model, khả năng test, và cấu hình bất đồng bộ.

Bạn cũng có thể dùng trực tiếp bất kỳ library nào khác. Ví dụ, xem cách [xây dựng một module Nest cho Knex.js](https://dev.to/nestjs/build-a-nestjs-module-for-knex-js-or-other-resource-based-libraries-in-5-minutes-12an). Để cache kết quả query, xem [Caching](/data/caching).
