### Dùng chung model

> warning **Warning** Chương này chỉ áp dụng cho cách tiếp cận code first.

Một trong những lợi thế lớn nhất khi dùng TypeScript cho backend của project là khả năng tái sử dụng cùng các model trong một ứng dụng frontend dựa trên TypeScript thông qua một package TypeScript dùng chung.

Tuy nhiên, các model được tạo theo cách tiếp cận code first được chú thích dày đặc bằng các decorator liên quan tới GraphQL. Những decorator đó không liên quan gì tới frontend và làm giảm hiệu năng của nó.

#### Dùng model shim

Để giải quyết vấn đề này, Nest cung cấp một "shim" thay thế các decorator gốc bằng code không làm gì cả. Package `@nestjs/graphql` cung cấp shim qua export condition `browser`, nên các bundler resolve condition đó cho bản build trình duyệt (ví dụ webpack với target `web`) sẽ tự động dùng nó.

Nếu bundler của bạn không resolve condition `browser`, hãy cấu hình một alias giữa package `@nestjs/graphql` và shim. Ví dụ, với webpack:

[[CODE:1]]

> info **Hint** Package [TypeORM](/data/typeorm) cung cấp một [model shim](https://github.com/typeorm/typeorm/blob/master/extra/typeorm-model-shim.js) tương tự.
