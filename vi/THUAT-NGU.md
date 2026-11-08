# Quy ước thuật ngữ

Bản dịch viết theo cách developer Việt nói chuyện với nhau hằng ngày. Từ nào cộng đồng vẫn dùng nguyên tiếng Anh thì giữ nguyên. Từ nào đã có cách dịch quen thuộc thì dịch. Mỗi khái niệm chỉ dùng một cách gọi trong toàn bộ tài liệu.

Những thứ luôn giữ nguyên: code, lệnh, tên API/class/method/decorator, tên package, đường dẫn, URL, tên biến môi trường, và mọi thứ nằm trong `inline code`.

## Giữ nguyên tiếng Anh

| Nhóm | Thuật ngữ |
| --- | --- |
| Building block của Nest | module, controller, provider, service, middleware, pipe, guard, interceptor, exception filter (gọi tắt: filter), decorator, gateway, resolver, adapter, transporter, strategy |
| Loại module | root module, feature module, shared module, global module, dynamic module |
| HTTP | request, response, route, route handler (gọi tắt: handler), endpoint, header, body, query string, query parameter, route parameter, status code, payload, cookie, session, middleware chain |
| DI | dependency injection (DI), inject, injection token, IoC container, singleton, scope, instance, dependency |
| Ngôn ngữ | class, method, constructor, interface, type, generic, enum, union, object, callback, Promise, Observable, stream, async/await, event loop, metadata, reflection |
| Lỗi | exception, throw, catch, stack trace |
| Vòng đời & chạy app | lifecycle hook, bootstrap, runtime, compile, transpile, build, deploy, production, development, hot reload |
| Công cụ & hệ sinh thái | framework, library, package, plugin, CLI, starter project, boilerplate, scaffold, monorepo, workspace |
| Dữ liệu | database, schema, migration, entity, repository, ORM, query, transaction, cache, queue, job, worker |
| Khác | event, listener, emit, subscribe, logger, log, token, JWT, hash, salt, test, unit test, e2e test, mock, stub, spy, coverage, validate / validation, serialize / serialization, implement, bind / binding, execution context, wildcard, prefix, payload |

## Dịch sang tiếng Việt

| Tiếng Anh | Tiếng Việt |
| --- | --- |
| application | ứng dụng |
| user | người dùng |
| feature | tính năng |
| configuration / config | cấu hình |
| environment variable | biến môi trường |
| directory / folder | thư mục |
| function | hàm |
| parameter / argument | tham số |
| property | thuộc tính |
| option | tùy chọn |
| value | giá trị |
| array | mảng |
| string | chuỗi |
| error | lỗi |
| default | mặc định |
| syntax | cú pháp |
| install / installation | cài đặt |
| register | đăng ký |
| lifecycle | vòng đời |
| request lifecycle | vòng đời request |
| architecture | kiến trúc |
| abstraction | lớp trừu tượng |
| third-party | bên thứ ba |
| built-in / out-of-the-box | có sẵn |
| performance | hiệu năng |
| security | bảo mật |
| authentication | xác thực |
| authorization | phân quyền |
| encryption | mã hóa |

## Nhãn ghi chú

| Bản gốc | Bản dịch |
| --- | --- |
| **Hint** | **Gợi ý** |
| **Warning** | **Cảnh báo** |
| **Note** | **Lưu ý** |
| **Notice** | **Chú ý** |

## Anchor của heading

Heading đã được dịch. Để mọi link kiểu `#alternatives` hay `/cli/usages#one-file-projects` vẫn dẫn đúng chỗ, mỗi heading có kèm một anchor mang slug tiếng Anh gốc, ví dụ:

```markdown
#### Cài đặt <a id="installation"></a>
```

Khi viết link tới một mục trong tài liệu, hãy dùng slug gốc tiếng Anh này.
