### Caching

Caching là một **kỹ thuật** đơn giản mà hiệu quả để cải thiện hiệu năng của ứng dụng. Cache đóng vai trò một tầng lưu trữ tạm thời giúp truy cập nhanh những dữ liệu hay dùng, để bạn không phải lấy hoặc tính toán lại cùng một thông tin nhiều lần. Kết quả là thời gian phản hồi nhanh hơn và hiệu quả tổng thể tốt hơn.

#### Cài đặt

Để bắt đầu với caching trong Nest, hãy cài package `@nestjs/cache-manager` cùng với package `cache-manager`:

[[CODE:1]]

Mặc định, mọi thứ được lưu trong bộ nhớ. Vì bên dưới `cache-manager` dùng [Keyv](https://keyv.org/docs/), bạn có thể chuyển sang một giải pháp lưu trữ khác, như Redis, bằng cách cài package tương ứng. Xem phần [Dùng cache store khác](/data/caching#using-alternative-cache-stores) bên dưới.

#### Cache trong bộ nhớ

Để bật caching trong ứng dụng, hãy import `CacheModule` và cấu hình nó bằng method `register()`:

[[CODE:2]]

Thiết lập này khởi tạo caching trong bộ nhớ với các thiết lập mặc định, để bạn có thể bắt đầu cache dữ liệu ngay lập tức.

#### Tương tác với cache store

Để tương tác với instance cache manager, hãy inject nó vào class bằng token `CACHE_MANAGER`, như sau:

[[CODE:3]]

> info **Hint** Class `Cache` và token `CACHE_MANAGER` đều được import từ package `@nestjs/cache-manager`.

Dùng method `get()` của instance `Cache` (từ package `cache-manager`) để lấy các mục từ cache. Nếu mục không tồn tại trong cache, `get()` trả về `undefined` (`cache-manager` v6 thì trả về `null`). Hãy xem cả hai đều là cache miss khi chuyển đổi phiên bản.

[[CODE:4]]

Để thêm một mục vào cache, dùng method `set()`:

[[CODE:5]]

> warning **Note** Store trong bộ nhớ mặc định giữ tham chiếu tới giá trị thay vì một bản sao: `get()` trả về chính object đã được truyền vào `set()`, nên thay đổi object đó sau này cũng sẽ thay đổi mục trong cache. Hãy xem các giá trị trong cache là chỉ đọc, hoặc copy giá trị trước khi thay đổi. Các store Keyv trong phần [Dùng cache store khác](/data/caching#using-alternative-cache-stores) thì serialize giá trị thành JSON, nên instance của class sẽ trở lại dưới dạng object thuần và object `Date` sẽ trở lại dưới dạng chuỗi.

Bạn có thể chỉ định TTL (thời gian hết hạn tính bằng mili giây) cho một key cụ thể, như sau:

[[CODE:6]]

Ở đây, mục trong cache sẽ hết hạn sau một giây.

Để lưu một mục không bao giờ hết hạn, truyền TTL là `0`:

[[CODE:7]]

Để xóa một mục khỏi cache, dùng method `del()`:

[[CODE:8]]

Để xóa toàn bộ cache, dùng method `clear()`:

[[CODE:9]]

#### Tự động cache response

> warning **Warning** Trong ứng dụng [GraphQL](/graphql/quick-start), interceptor được thực thi riêng cho mỗi field resolver. Vì vậy, `CacheModule` (vốn dùng interceptor để cache response) không hoạt động đúng ở đó.

Để tự động cache response, hãy bind `CacheInterceptor` ở nơi bạn muốn cache dữ liệu:

[[CODE:10]]

> warning **Warning** Mặc định, chỉ các endpoint `GET` mới được cache (một `@CacheKey()` tường minh trên route handler sẽ bỏ qua bước kiểm tra này). Ngoài ra, các route HTTP inject response object gốc (`@Res()`) không thể dùng `CacheInterceptor`. Xem [map response](/interceptors#response-mapping) để biết thêm chi tiết.

Để giảm boilerplate, bạn có thể bind `CacheInterceptor` cho mọi endpoint ở cấp global:

[[CODE:11]]

#### Time-to-live (TTL)

Mặc định, `ttl` không được đặt, nên các mục trong cache không bao giờ hết hạn (giống như đặt nó thành `0`). Để chỉ định một [TTL](https://en.wikipedia.org/wiki/Time_to_live) tùy chỉnh, truyền tùy chọn `ttl` vào method `register()`:

[[CODE:12]]

#### Dùng module ở cấp global

Để dùng `CacheModule` trong các module khác, bạn cần import nó (như với mọi module Nest). Cách khác là khai báo nó là [global module](/modules#global-modules) bằng cách đặt thuộc tính `isGlobal` của options object thành `true`, như bên dưới. Khi đó, một khi `CacheModule` đã được load trong root module (ví dụ `AppModule`), bạn không cần import nó trong các module khác nữa.

[[CODE:13]]

#### Ghi đè cache global

Khi `CacheInterceptor` được bind ở cấp global, các mục cache được lưu dưới một key sinh tự động từ URL của request. Bạn có thể ghi đè một số thiết lập cache (`@CacheKey()` và `@CacheTTL()`) cho từng method để tùy biến chiến lược cache cho từng method của controller. Điều này đặc biệt có ý nghĩa khi dùng [các cache store khác nhau](/data/caching#using-alternative-cache-stores).

Bạn cũng có thể áp dụng decorator `@CacheTTL()` lên controller để đặt TTL cho mọi route của nó. Khi có cả thiết lập TTL ở cấp controller lẫn cấp method, thiết lập ở cấp method được ưu tiên.

[[CODE:14]]

> info **Hint** Các decorator `@CacheKey()` và `@CacheTTL()` được import từ package `@nestjs/cache-manager`.

Bạn có thể dùng decorator `@CacheKey()` có hoặc không có decorator `@CacheTTL()` đi kèm, và ngược lại, để chỉ ghi đè key hoặc chỉ ghi đè TTL. Các thiết lập không bị ghi đè bằng decorator sẽ dùng giá trị mặc định đăng ký với module (xem [Time-to-live (TTL)](/data/caching#time-to-live-ttl)).

#### WebSocket và Microservice

Bạn cũng có thể áp dụng `CacheInterceptor` cho WebSocket subscriber và microservice pattern (bất kể transport nào được dùng).

[[CODE:15]]

Trong các context này, decorator `@CacheKey()` là bắt buộc: nó chỉ định key dùng để lưu và lấy dữ liệu trong cache. Không có nó, response sẽ không được cache. Ngoài ra, hãy nhớ rằng bạn **không nên cache mọi thứ**. Đừng bao giờ cache những action thực hiện thao tác nghiệp vụ thay vì chỉ truy vấn dữ liệu.

Bạn cũng có thể chỉ định thời gian hết hạn cache (TTL) bằng decorator `@CacheTTL()`, decorator này ghi đè TTL mặc định:

[[CODE:16]]

> info **Hint** Trong ứng dụng HTTP, decorator `@CacheTTL()` hoạt động dù có hay không có decorator `@CacheKey()` đi kèm. Trong context WebSocket và microservice, nó không có tác dụng nếu thiếu `@CacheKey()`, vì không có key thì không có gì được cache.

#### Điều chỉnh cách theo dõi

Mặc định, Nest dùng URL của request (trong app HTTP) hoặc cache key đặt qua decorator `@CacheKey()` (trong app WebSocket và microservice) để gắn các bản ghi cache với endpoint của bạn. Đôi khi bạn có thể muốn theo dõi bản ghi dựa trên các yếu tố khác, ví dụ HTTP header (như `Authorization` để nhận diện đúng các endpoint `profile`).

Để làm vậy, hãy tạo một class con của `CacheInterceptor` và ghi đè method `trackBy()`:

[[CODE:17]]

#### Dùng cache store khác

Để chuyển sang một cache store khác, trước tiên hãy cài package tương ứng. Ví dụ, để dùng Redis, hãy cài package `@keyv/redis`. Ví dụ bên dưới cũng dùng store trong bộ nhớ từ package `cacheable`:

[[CODE:18]]

Khi đã có những thứ trên, bạn có thể đăng ký `CacheModule` với nhiều store, như bên dưới:

[[CODE:19]]

Ví dụ này đăng ký hai store: `CacheableMemory` và một Redis store. `CacheableMemory` là một store trong bộ nhớ tạo bằng storage adapter `KeyvCacheableMemory`, còn Redis store được tạo bằng helper `createKeyv()` từ `@keyv/redis`. Mảng `stores` chỉ định các store bạn muốn dùng. Store đầu tiên trong mảng là store mặc định, các store còn lại là store dự phòng.

> warning **Warning** Luôn gắn một listener `'error'` cho Redis store, như ở trên. Khi kết nối Redis bị ngắt, store phát ra event `'error'`, và Keyv sẽ throw nếu không có ai lắng nghe event đó, điều này có thể làm crash ứng dụng.

Xem [tài liệu Keyv](https://keyv.org/docs/) để biết thêm thông tin về các store có sẵn.

#### Cấu hình bất đồng bộ

Có thể bạn muốn truyền tùy chọn module theo kiểu bất đồng bộ thay vì tĩnh lúc compile. Khi đó, hãy dùng method `registerAsync()`, method này cung cấp vài cách để xử lý cấu hình bất đồng bộ.

Một cách là dùng hàm factory:

[[CODE:20]]

Factory hoạt động giống mọi factory module bất đồng bộ khác: nó có thể là `async` và có thể inject dependency qua `inject`.

[[CODE:21]]

Cách khác là dùng cú pháp `useClass`:

[[CODE:22]]

Cách khai báo này khởi tạo `CacheConfigService` bên trong `CacheModule` và dùng nó để lấy options object. `CacheConfigService` phải implement interface `CacheOptionsFactory` để cung cấp các tùy chọn cấu hình:

[[CODE:23]]

Để dùng một configuration provider đã có được import từ module khác, hãy dùng cú pháp `useExisting`:

[[CODE:24]]

Cách này hoạt động giống `useClass`, với một khác biệt quan trọng: `CacheModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã được tạo thay vì tự khởi tạo cái mới.

> info **Hint** `CacheModule#register`, `CacheModule#registerAsync` và `CacheOptionsFactory` nhận một generic (type argument) tùy chọn để thu hẹp các tùy chọn cấu hình riêng của store, giúp chúng type-safe.

Bạn cũng có thể truyền `extraProviders` vào method `registerAsync()`. Các provider này được merge với các provider của module:

[[CODE:25]]

Điều này hữu ích khi bạn muốn cung cấp thêm dependency cho hàm factory hoặc constructor của class.

#### Ví dụ

Một ví dụ chạy được có sẵn trong [sample cache](https://github.com/nestjs/nest/tree/master/sample/20-cache).
