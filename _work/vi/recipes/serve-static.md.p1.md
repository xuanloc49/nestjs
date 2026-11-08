### Serve Static

Để phục vụ nội dung tĩnh, như một ứng dụng single-page (SPA), hãy dùng `ServeStaticModule` từ package [`@nestjs/serve-static`](https://www.npmjs.com/package/@nestjs/serve-static).

#### Cài đặt

Trước tiên, hãy cài package cần thiết:

[[CODE:1]]

#### Bootstrap

Khi đã cài đặt xong, hãy import `ServeStaticModule` vào root `AppModule` và cấu hình nó bằng cách truyền một configuration object cho method `forRoot()`:

[[CODE:2]]

Khi đã có cấu hình này, hãy build website tĩnh và đặt nội dung của nó vào vị trí được chỉ định bởi thuộc tính `rootPath`.

#### Cấu hình

[`ServeStaticModule`](https://github.com/nestjs/serve-static) nhận nhiều tùy chọn để tùy chỉnh hành vi của nó. Ví dụ, bạn có thể đặt đường dẫn nơi ứng dụng tĩnh được render, loại trừ các đường dẫn cụ thể, hoặc bật hay tắt response header `Cache-Control`. Xem [interface `ServeStaticModuleOptions`](https://github.com/nestjs/serve-static/blob/master/lib/interfaces/serve-static-options.interface.ts) để biết danh sách đầy đủ các tùy chọn.

> warning **Notice** Mặc định, `renderPath` khớp với mọi đường dẫn, và module trả về file `index.html`. Điều này cho phép client-side routing cho SPA của bạn, trong khi các route được khai báo trong controller vẫn được server xử lý. Bạn có thể thay đổi hành vi này bằng cách kết hợp các tùy chọn `serveRoot` và `renderPath` với các tùy chọn khác. Với Fastify adapter, hãy đặt `serveStaticOptions.fallthrough` thành `true` để mô phỏng hành vi fallthrough của Express, tức là gửi `index.html` thay vì lỗi 404 cho các route không tồn tại.

#### Ví dụ

Một ví dụ chạy được có trong [sample serve-static](https://github.com/nestjs/nest/tree/master/sample/24-serve-static) trên GitHub.
