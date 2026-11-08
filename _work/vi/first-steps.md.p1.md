### Những bước đầu tiên

Loạt bài này trình bày **những kiến thức nền tảng cốt lõi** của Nest. Để giới thiệu các building block thiết yếu của một ứng dụng Nest, chúng ta sẽ xây dựng một ứng dụng CRUD cơ bản, với các tính năng bao quát khá nhiều nội dung ở mức nhập môn.

#### Ngôn ngữ

Nest được viết bằng [TypeScript](https://www.typescriptlang.org/), chạy trên [Node.js](https://nodejs.org/en/), và hỗ trợ cả TypeScript lẫn JavaScript thuần. Vì Nest dùng các tính năng mới nhất của ngôn ngữ, muốn dùng Nest với JavaScript thuần thì bạn cần đến [Babel](https://babeljs.io/).

Phần lớn ví dụ trong tài liệu này dùng TypeScript, nhưng bạn có thể **chuyển bất kỳ đoạn code nào** sang cú pháp JavaScript thuần bằng nút chuyển ngôn ngữ ở góc trên bên phải của đoạn code.

#### Yêu cầu

Hãy chắc chắn rằng [Node.js](https://nodejs.org) đã được cài trên hệ điều hành của bạn. Để chạy một ứng dụng Nest, bạn cần **v20.19 trở lên** (hoặc **v22.12+** nếu dùng dòng 22.x). Các generator của Nest CLI (như `nest new` và `nest generate`) yêu cầu **v22.22.3+, v24.15+ hoặc v26+**. Chúng tôi khuyên dùng bản active LTS mới nhất, vì nó đáp ứng cả hai yêu cầu trên.

#### Thiết lập

Cách nhanh nhất để thiết lập một project mới là dùng [Nest CLI](/cli/overview). Khi đã cài [npm](https://www.npmjs.com/), chạy các lệnh sau trong terminal:

[[CODE:1]]

CLI sẽ hỏi bạn muốn dùng module system nào: ESM (mặc định), dùng Vitest làm test runner, hay CommonJS, dùng Jest.

CLI cũng hỏi bạn có muốn thiết lập [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') không, đây là nền tảng observability chính thức của Nest. Nếu bạn đồng ý, project được tạo ra sẽ có sẵn SDK `@nestjs/observe`, đã được nối sẵn vào `AppModule` và `NestFactory.create()`. Trong terminal tương tác, câu trả lời mặc định là yes; trong môi trường không tương tác, như CI, câu hỏi này bị bỏ qua và Observe không được thêm vào. Truyền `--observe` hoặc `--no-observe` để bỏ qua câu hỏi và chọn luôn đáp án. Xem chương [Observability](/observability/overview) để biết Observe bao gồm những gì.

Nếu bạn thiết lập Observe, sau khi cài xong dependency, CLI sẽ đề nghị liên kết project mới với Observe. Nếu đồng ý, CLI in ra một mã để bạn xác nhận tại [observe.nestjs.com/link](https://www.observe.nestjs.com/link 'Liên kết project với NestJS Observe') (đăng ký trước nếu bạn chưa có tài khoản; gói miễn phí không cần thông tin thanh toán), sau đó CLI ghi app key và secret vào `.env` và cho mọi script `nest start` (`start`, `start:dev` và `start:debug`) load file này. Request, background job, lỗi và distributed trace sẽ bắt đầu được gửi lên từ lần khởi động ứng dụng tiếp theo. Để liên kết sau, hoặc khi CLI không đề nghị (không có terminal, hoặc dùng `--skip-install`), chạy `npx @nestjs/observe link` trong thư mục project - xem [Liên kết từ terminal](/observability/sdk#linking-from-the-terminal).

> info **Gợi ý** Project mới được tạo với chế độ [strict](https://www.typescriptlang.org/tsconfig#strict) của TypeScript đã bật. Để tắt, đặt `"strict": false` trong file `tsconfig.json` được tạo ra.

CLI tạo thư mục `project-name`, cài dependency, sinh vài file boilerplate và tạo thư mục `src/` chứa một số file core.

<div class="file-tree">
  <div class="item">src</div>
  <div class="children">
    <div class="item">app.controller.spec.ts</div>
    <div class="item">app.controller.ts</div>
    <div class="item">app.module.ts</div>
    <div class="item">app.service.ts</div>
    <div class="item">main.ts</div>
  </div>
</div>

Bảng sau mô tả các file core này:

|                          |                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------- |
| `app.controller.ts`      | Một controller cơ bản với một route duy nhất.                                         |
| `app.controller.spec.ts` | Unit test cho controller.                                                             |
| `app.module.ts`          | Root module của ứng dụng.                                                             |
| `app.service.ts`         | Một service cơ bản với một method duy nhất.                                           |
| `main.ts`                | File entry của ứng dụng. File này dùng `NestFactory` để tạo instance ứng dụng Nest.   |

File `main.ts` chứa một hàm async làm nhiệm vụ **bootstrap** ứng dụng:

[[CODE:2]]

Để tạo instance ứng dụng Nest, ta dùng `NestFactory` từ `@nestjs/core`, class này cung cấp vài method cho việc đó. Method `create()` trả về một application object implement interface `INestApplication`. Các method của object này sẽ được mô tả trong các chương sau. Trong ví dụ `main.ts` ở trên, ứng dụng khởi động một HTTP listener và chờ các HTTP request gửi đến.

Cấu trúc project do Nest CLI tạo ra khuyến khích quy ước đặt mỗi module trong một thư mục riêng.

> info **Gợi ý** Mặc định, nếu có lỗi xảy ra trong lúc tạo ứng dụng, process sẽ thoát với code `1`. Nếu muốn lỗi được throw ra thay vì thoát, hãy tắt tùy chọn `abortOnError` (ví dụ: `NestFactory.create(AppModule, {{ '{' }} abortOnError: false {{ '}' }})`).

<app-banner-courses></app-banner-courses>

#### Nền tảng

Nest được thiết kế để không phụ thuộc vào nền tảng (platform-agnostic). Nhờ độc lập với nền tảng, bạn có thể tạo ra những phần logic tái sử dụng được trong nhiều loại ứng dụng khác nhau. Nest làm việc được với bất kỳ HTTP framework Node.js nào, miễn là có adapter cho framework đó. Có ba nền tảng HTTP được hỗ trợ sẵn: [Express](https://expressjs.com/), [Fastify](https://www.fastify.io) và module [`node:http`](https://nodejs.org/api/http.html) có sẵn trong Node.js. Hãy chọn cái phù hợp nhất với nhu cầu của bạn (xem [HTTP adapter](/http/performance)).

|                    |                                                                                                                                                                                                                                                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `platform-express` | [Express](https://expressjs.com/) là một web framework tối giản, rất nổi tiếng cho Node.js. Đây là library đã được kiểm chứng qua thực chiến, sẵn sàng cho production và có cộng đồng lớn với nhiều tài nguyên. Mặc định Nest dùng package `@nestjs/platform-express`, nên bạn không cần thiết lập gì thêm.                               |
| `platform-fastify` | [Fastify](https://www.fastify.io/) là một framework hiệu năng cao, overhead thấp, tập trung vào hiệu quả và tốc độ. Để tìm hiểu cách dùng, xem [Fastify adapter](/http/performance#fastify-adapter).                                                                                                                                  |
| `platform-node`    | `NodeAdapter` chạy Nest trực tiếp trên module `node:http` của Node.js, và là adapter nhanh nhất trong ba cái. Request và response object của nó có sẵn các helper kiểu Express, nên phần lớn middleware Express đều chạy được. Chúng tôi khuyên dùng adapter này kể từ v12.3, và nó sẽ trở thành mặc định ở v13. Để tìm hiểu cách dùng, xem [Node adapter](/http/performance#node-adapter). |

Mỗi nền tảng có interface ứng dụng riêng, lần lượt là `NestExpressApplication`, `NestFastifyApplication` và `NestNodeApplication`.

Khi bạn truyền một type vào method `NestFactory.create()` như ví dụ bên dưới, object `app` sẽ có thêm các method chỉ nền tảng đó mới có. Bạn **không cần** chỉ định type, **trừ khi** muốn truy cập API của nền tảng bên dưới.

[[CODE:3]]

##### Dùng Node adapter

Kể từ v12.3, chúng tôi khuyên chạy các ứng dụng mới trên Node adapter. Adapter này chưa phải mặc định, nên bạn cần cài package:

[[CODE:4]]

Sau đó truyền một instance `NodeAdapter` vào `NestFactory.create()` trong file `main.ts`:

[[CODE:5]]

Mọi thứ khác trong ứng dụng giữ nguyên: controller, provider và phần lớn middleware Express vẫn chạy như cũ. Xem [Node adapter](/http/performance#node-adapter) để biết vài chỗ nó khác với Express.

Bài test end-to-end mà CLI sinh ra (`test/app.e2e-spec.ts`) tự tạo ứng dụng riêng, và ứng dụng này chạy trên Express trừ khi bạn truyền vào một adapter. Hãy truyền thêm `new NodeAdapter()` vào lời gọi `createNestApplication()` trong đó, để bài test chạy trên cùng adapter với ứng dụng.

#### Chạy ứng dụng

Sau khi cài đặt xong, chạy lệnh sau để khởi động ứng dụng và lắng nghe các HTTP request gửi đến:

[[CODE:6]]

> info **Gợi ý** Để build nhanh hơn trong lúc phát triển, dùng [SWC builder](/recipes/swc) bằng cách truyền flag `-b swc` vào script `start`: `npm run start -- -b swc`.

Lệnh này khởi động HTTP server trên port được định nghĩa trong file `src/main.ts` (`3000`, trừ khi có đặt biến môi trường `PORT`). Khi ứng dụng đã chạy, mở trình duyệt và truy cập `http://localhost:3000/`. Bạn sẽ thấy dòng chữ `Hello World!`.

Để theo dõi thay đổi trên các file, hãy khởi động ứng dụng bằng lệnh sau:

[[CODE:7]]

Lệnh này theo dõi các file của bạn, và mỗi khi có thay đổi, nó sẽ compile lại rồi khởi động lại server.

#### Lint và format code

[Nest CLI](/cli/overview) hướng tới việc scaffold sẵn một quy trình phát triển ổn định và mở rộng tốt. Để có sẵn một quy trình mặc định nhanh gọn, các project TypeScript được tạo ra đã cài sẵn một **linter** và một **formatter**, lần lượt là [oxlint](https://oxc.rs/docs/guide/usage/linter.html) và [Prettier](https://prettier.io/).

> info **Gợi ý** Chưa rõ formatter và linter khác nhau thế nào? Xem [bài so sánh](https://prettier.io/docs/en/comparison.html) của Prettier.

Với các môi trường headless không dùng IDE (continuous integration, Git hook, v.v.), project có sẵn các script `npm` để chạy [`oxlint`](https://www.npmjs.com/package/oxlint) và [`prettier`](https://www.npmjs.com/package/prettier):

[[CODE:8]]
