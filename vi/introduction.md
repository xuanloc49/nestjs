### Giới thiệu

Nest (NestJS) là một framework để xây dựng các ứng dụng server-side [Node.js](https://nodejs.org/) hiệu quả và dễ mở rộng, từ một API nhỏ nằm gọn trong một file cho đến các hệ thống cấp doanh nghiệp với nhiều team cùng làm. Nest dùng progressive JavaScript, được viết bằng và hỗ trợ đầy đủ [TypeScript](https://www.typescriptlang.org/) (nhưng vẫn cho phép bạn viết JavaScript thuần), đồng thời kết hợp các yếu tố của OOP (lập trình hướng đối tượng), FP (lập trình hàm) và FRP (functional reactive programming).

Bên dưới, Nest dùng các HTTP server framework mạnh mẽ như [Express](https://expressjs.com/) (mặc định), và có thể cấu hình để dùng [Fastify](https://github.com/fastify/fastify) hoặc chính module `node:http` của Node (xem [HTTP adapter](/http/performance)). Để so sánh Nest với các framework này và với Hono, xem [Nest so với Fastify, Express và Hono](/faq/nest-vs-fastify-express-hono).

Nest cung cấp một lớp trừu tượng nằm trên các framework Node.js phổ biến này (Express và Fastify), nhưng vẫn cho developer truy cập trực tiếp API của chúng. Nhờ vậy, bạn được tự do dùng vô số module bên thứ ba sẵn có cho nền tảng bên dưới.

#### Triết lý <a id="philosophy"></a>

Những năm gần đây, nhờ có Node.js, JavaScript đã trở thành "ngôn ngữ chung" của web cho cả frontend lẫn backend. Điều này dẫn đến sự ra đời của các project như [Angular](https://angular.dev/), [React](https://github.com/facebook/react) và [Vue](https://github.com/vuejs/core), giúp developer làm việc năng suất hơn và tạo ra được các ứng dụng frontend nhanh, dễ test, dễ mở rộng. Tuy nhiên, dù Node.js (và JavaScript phía server) có rất nhiều library, helper và tool xuất sắc, chưa cái nào thực sự giải quyết được vấn đề chính: **kiến trúc**.

Nest cung cấp sẵn một kiến trúc ứng dụng giúp developer và các team tạo ra những ứng dụng dễ test, dễ mở rộng, loosely coupled và dễ bảo trì. Kiến trúc này lấy cảm hứng rất nhiều từ Angular.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, bạn có thể scaffold project bằng [Nest CLI](/cli/overview) hoặc [clone một starter project](#alternatives). Cả hai cách đều cho ra cùng một kết quả.

Để scaffold project bằng Nest CLI, chạy các lệnh dưới đây. Chúng sẽ tạo một thư mục project mới, sinh sẵn các file core ban đầu của Nest cùng các module hỗ trợ, cho project một cấu trúc nền theo quy ước. Chúng tôi khuyên người mới dùng **Nest CLI**, và chương [Những bước đầu tiên](/first-steps) cũng đi tiếp theo hướng này.

```bash
$ npm i -g @nestjs/cli
$ nest new project-name
```

Với project nhỏ hoặc phiên bản đầu tiên, `nest new project-name --minimal` sẽ tạo một ứng dụng có toàn bộ code nằm trong [một file](/cli/usages#one-file-projects).

Nest cũng có các package chính chủ cho những thứ mà hầu hết backend đều cần, như [xác thực](/security/authentication), [mail](/application/mail), [lưu trữ file](/application/file-storage), [webhook](/http/webhooks), [queue](/application/queues), [AI](/ai/overview) và [MCP](/mcp/overview), nên hãy xem qua chúng trước khi thêm một library khác.

#### Cách khác <a id="alternatives"></a>

Ngoài ra, bạn có thể cài TypeScript starter project bằng **Git**:

```bash
$ git clone https://github.com/nestjs/typescript-starter.git project
$ cd project
$ npm install
$ npm run start
```

> info **Gợi ý** Để clone repository mà không kèm lịch sử Git, dùng [degit](https://github.com/Rich-Harris/degit).

Mở trình duyệt và truy cập [`http://localhost:3000/`](http://localhost:3000/).

Để cài bản JavaScript của starter project, dùng `javascript-starter.git` trong chuỗi lệnh ở trên.

Bạn cũng có thể bắt đầu một project mới từ con số không bằng cách tự cài các package core và package hỗ trợ. Khi đó, bạn phải tự thiết lập các file boilerplate của project. Tối thiểu, bạn cần các dependency sau: `@nestjs/core`, `@nestjs/common`, `rxjs` và `reflect-metadata`. Để xem hướng dẫn từng bước tạo một project hoàn chỉnh theo cách này, xem bài [5 steps to create a bare minimum NestJS app from scratch](https://dev.to/micalevisk/5-steps-to-create-a-bare-minimum-nestjs-app-from-scratch-5c3b).
