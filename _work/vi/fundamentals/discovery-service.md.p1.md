### Discovery service

`DiscoveryService`, do package `@nestjs/core` cung cấp, cho phép bạn kiểm tra và lấy ra động các provider, controller và metadata của chúng trong một ứng dụng NestJS. Tính năng này đặc biệt hữu ích khi xây dựng plugin, decorator, hoặc các tính năng nâng cao dựa vào introspection lúc runtime, giúp bạn xây dựng các kiến trúc linh hoạt, mô-đun hơn với hành vi tự động và động.

#### Bắt đầu

Trước khi dùng `DiscoveryService`, hãy import `DiscoveryModule` vào module nơi bạn định dùng nó. Việc này giúp service có sẵn để dependency injection:

[[CODE:1]]

Khi đã thiết lập module, bạn có thể inject `DiscoveryService` vào bất kỳ provider nào cần khả năng khám phá động:

[[CODE:2]]

#### Khám phá provider và controller

Một khả năng quan trọng của `DiscoveryService` là lấy ra mọi provider đã đăng ký trong ứng dụng, hữu ích để xử lý động các provider dựa trên những điều kiện cụ thể. Đoạn code sau lấy ra mọi provider:

[[CODE:3]]

Mỗi object trả về là một `InstanceWrapper`, chứa các thông tin như instance, token và class (`metatype`) của provider. Tương tự, để lấy mọi controller đã đăng ký trong ứng dụng, dùng:

[[CODE:4]]

Điều này hữu ích khi cần xử lý động các controller, ví dụ để theo dõi analytics hoặc cho các cơ chế đăng ký tự động.

Cả hai method đều nhận một options object tùy chọn. Truyền vào một mảng `include` chứa các class module để giới hạn việc khám phá trong những module đó:

[[CODE:5]]

#### Lấy metadata

Ngoài việc khám phá provider và controller, `DiscoveryService` còn lấy được metadata gắn trên các thành phần này. Điều này đặc biệt có giá trị khi làm việc với custom decorator lưu metadata lúc runtime.

Ví dụ, xét một custom decorator dùng để gắn tag metadata cụ thể cho provider:

[[CODE:6]]

Áp dụng decorator này lên một service sẽ lưu metadata để truy vấn sau:

[[CODE:7]]

Khi metadata đã được gắn vào provider theo cách này, bạn có thể dùng `DiscoveryService` để lọc provider dựa trên metadata đã gán. Đoạn code sau lấy ra một provider được gắn tag với một giá trị metadata cụ thể:

[[CODE:8]]

Decorator tạo bằng `DiscoveryService.createDecorator()` cũng đăng ký luôn các class mà nó decorate, nên bạn có thể chỉ lấy ra những class đó bằng cách truyền `KEY` của decorator vào tùy chọn `metadataKey`, thay vì tự lọc toàn bộ provider:

[[CODE:9]]

Cùng một decorator cũng có thể áp dụng lên method. Để đọc metadata ở cấp method, truyền tên method làm tham số thứ ba cho `getMetadataByDecorator()`.

#### Tổng kết

`DiscoveryService` mở ra khả năng introspection lúc runtime trong ứng dụng NestJS. Bằng cách khám phá động các provider, controller và metadata của chúng, nó đóng vai trò viên gạch nền cho các framework mở rộng được, plugin và các tính năng dựa trên tự động hóa, dù bạn cần quét và xử lý provider, lấy metadata để xử lý tiếp, hay xây dựng kiến trúc mô-đun.
