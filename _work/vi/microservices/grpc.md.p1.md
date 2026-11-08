### gRPC

[gRPC](https://github.com/grpc/grpc-node) là một framework RPC hiện đại, mã nguồn mở, hiệu năng cao, có thể chạy trong mọi môi trường. Nó kết nối các service bên trong và xuyên qua các data center, với khả năng cắm thêm cho cân bằng tải, tracing, health check và xác thực.

Giống như nhiều hệ thống RPC khác, gRPC dựa trên việc định nghĩa một service dưới dạng các hàm (method) có thể được gọi từ xa. Với mỗi method, bạn định nghĩa tham số và return type. Service, tham số và return type được định nghĩa trong các file `.proto` bằng cơ chế <a href="https://protobuf.dev">protocol buffers</a> mã nguồn mở, không phụ thuộc ngôn ngữ của Google.

Với transporter gRPC, Nest dùng các file `.proto` để bind client và server một cách động, giúp việc hiện thực remote procedure call trở nên đơn giản và tự động serialize cũng như deserialize dữ liệu có cấu trúc.

#### Cài đặt

Để bắt đầu xây dựng microservice dựa trên gRPC, trước tiên hãy cài các package cần thiết:

[[CODE:1]]

#### Tổng quan

Như với các phần hiện thực lớp transport microservice khác của Nest, bạn chọn transporter gRPC bằng thuộc tính `transport` của options object được truyền cho method `createMicroservice()`. Trong ví dụ sau, chúng ta sẽ thiết lập một hero service. Thuộc tính `options` cung cấp metadata về service đó; các thuộc tính của nó được mô tả trong [Tùy chọn](/microservices/grpc#options) bên dưới.

[[CODE:2]]

> info **Hint** Hàm `join()` được import từ package `path`, còn enum `Transport` từ package `@nestjs/microservices`.

Trong file `nest-cli.json`, hãy thêm thuộc tính `assets` để phân phối các file không phải TypeScript, và `watchAssets` để theo dõi mọi asset không phải TypeScript. Trong trường hợp này, chúng ta muốn các file `.proto` được tự động copy vào thư mục `dist`.

[[CODE:3]]

#### Tùy chọn

Options object của transporter <strong>gRPC</strong> cung cấp các thuộc tính sau.

<table>
  <tr>
    <td><code>package</code></td>
    <td>Tên package Protobuf (khớp với thiết lập <code>package</code> trong file <code>.proto</code>). Cũng nhận một mảng tên package. Bắt buộc</td>
  </tr>
  <tr>
    <td><code>protoPath</code></td>
    <td>
      Đường dẫn tuyệt đối (hoặc tương đối so với thư mục làm việc hiện tại) tới file
      <code>.proto</code>, hoặc một mảng đường dẫn. Bắt buộc trừ khi bạn truyền một <code>packageDefinition</code> đã được load sẵn thay vào đó
    </td>
  </tr>
  <tr>
    <td><code>url</code></td>
    <td>URL kết nối. Một chuỗi có định dạng <code>ip address/dns name:port</code> (ví dụ <code>'0.0.0.0:50051'</code> cho một server Docker) xác định địa chỉ và port mà transporter thiết lập kết nối. Tùy chọn. Mặc định là <code>'localhost:5000'</code></td>
  </tr>
  <tr>
    <td><code>protoLoader</code></td>
    <td>Tên package NPM của tiện ích dùng để load các file <code>.proto</code>. Tùy chọn. Mặc định là <code>'@grpc/proto-loader'</code></td>
  </tr>
  <tr>
    <td><code>loader</code></td>
    <td>
      Các tùy chọn của <code>@grpc/proto-loader</code>, kiểm soát cách các file <code>.proto</code> được load. Tùy chọn. Xem
      <a
        href="https://github.com/grpc/grpc-node/blob/master/packages/proto-loader/README.md"
        rel="nofollow"
        target="_blank"
        >README của proto-loader</a
      > để biết chi tiết
    </td>
  </tr>
  <tr>
    <td><code>credentials</code></td>
    <td>
      Credential của server (channel credential khi được client dùng). Tùy chọn. Mặc định là credential không bảo mật. Xem <a
        href="https://grpc.io/grpc/node/grpc.ServerCredentials.html"
        rel="nofollow"
        target="_blank"
        >tài liệu tham khảo <code>ServerCredentials</code></a
      >
    </td>
  </tr>
</table>

#### Service gRPC mẫu

Hãy định nghĩa một service gRPC mẫu tên `HeroesService`. Trong object `options` ở trên, thuộc tính `protoPath` đặt đường dẫn tới file định nghĩa `hero.proto`. File `hero.proto` được cấu trúc bằng <a href="https://developers.google.com/protocol-buffers">protocol buffers</a>:

[[CODE:4]]

`HeroesService` cung cấp một method `FindOne()`. Method này nhận một input argument có type `HeroById` và trả về một message `Hero` (protocol buffers dùng các phần tử `message` để định nghĩa cả type tham số lẫn return type).

Tiếp theo, hãy hiện thực service. Để định nghĩa một handler đáp ứng định nghĩa này, hãy dùng decorator `@GrpcMethod()` trong một controller, như bên dưới. Decorator này cung cấp metadata cần thiết để khai báo một method là method của service gRPC.

> info **Hint** Decorator `@MessagePattern()` (xem [request-response](/microservices/basics#request-response)) được giới thiệu trong các chương microservice trước không được dùng với các microservice dựa trên gRPC. Decorator `@GrpcMethod()` thay thế vị trí của nó.

[[CODE:5]]

> info **Hint** Decorator `@GrpcMethod()` được import từ package `@nestjs/microservices`, còn `Metadata` và `ServerUnaryCall` được import từ package `@grpc/grpc-js`.

Decorator nhận hai tham số. Tham số đầu tiên là tên service (ví dụ `'HeroesService'`), tương ứng với định nghĩa service `HeroesService` trong `hero.proto`. Tham số thứ hai (chuỗi `'FindOne'`) tương ứng với method rpc `FindOne()` được định nghĩa bên trong `HeroesService` trong `hero.proto`.

Method handler `findOne()` nhận ba tham số: `data` được truyền từ bên gọi, `metadata` lưu metadata của gRPC request, và object `call`, object này cung cấp các thành phần như `sendMetadata()` để gửi metadata tới client.

Cả hai tham số của decorator `@GrpcMethod()` đều không bắt buộc. Nếu bạn bỏ tham số thứ hai (ví dụ `'FindOne'`), Nest liên kết handler với method rpc trong `.proto` có tên khớp với tên handler được viết hoa chữ cái đầu (ví dụ handler `findOne` được liên kết với định nghĩa rpc `FindOne`), như bên dưới.

[[CODE:6]]

Bạn cũng có thể bỏ tham số đầu tiên của `@GrpcMethod()`. Trong trường hợp này, Nest liên kết handler với định nghĩa service trong file `.proto` dựa trên tên của **class** nơi handler được định nghĩa. Ví dụ, trong đoạn code sau, class `HeroesService` liên kết các method handler của nó với định nghĩa service `HeroesService` trong `hero.proto` vì tên trùng khớp.

[[CODE:7]]

#### Client

Ứng dụng Nest có thể đóng vai trò gRPC client, tiêu thụ các service được định nghĩa trong file `.proto`. Bạn truy cập các service từ xa qua một object `ClientGrpc`, có thể lấy được theo nhiều cách.

Kỹ thuật được ưu tiên là import `ClientsModule`. Dùng method `register()` của nó để bind một package các service được định nghĩa trong một file `.proto` với một injection token, và cấu hình service. Thuộc tính `name` là injection token. Với các service gRPC, hãy dùng `transport: Transport.GRPC`. Thuộc tính `options` là một object có cùng các thuộc tính được mô tả trong [Tùy chọn](/microservices/grpc#options) ở trên.

[[CODE:8]]

> info **Hint** Method `register()` nhận một mảng object. Để đăng ký nhiều package, hãy cung cấp một danh sách object đăng ký cách nhau bởi dấu phẩy.

Khi đã đăng ký, hãy inject object `ClientGrpc` đã được cấu hình bằng `@Inject()`. Sau đó dùng method `getService()` của object `ClientGrpc` để lấy instance của service, như bên dưới.

[[CODE:9]]

> error **Warning** gRPC client không gửi các field có chứa dấu gạch dưới (`_`) trong tên trừ khi tùy chọn `keepCase` được đặt thành `true` trong cấu hình proto loader (`options.loader.keepCase` trong cấu hình transporter của microservice).

Điều này hơi khác so với kỹ thuật dùng cho các transporter microservice khác. Thay vì class `ClientProxy`, bạn dùng class `ClientGrpc`, class này cung cấp method `getService()`. Method generic `getService()` nhận tên service làm tham số và trả về instance của nó (nếu có).

Ngoài ra, bạn có thể dùng decorator `@Client()` để khởi tạo một object `ClientGrpc`, như sau:

[[CODE:10]]

Cuối cùng, với các tình huống phức tạp hơn, bạn có thể inject một client được cấu hình động bằng class `ClientProxyFactory`, như mô tả trong [phần client của trang tổng quan về microservice](/microservices/basics#client-producer-class).

Trong mỗi trường hợp, bạn sẽ có được một tham chiếu tới object proxy `HeroesService`, object này cung cấp cùng tập method được định nghĩa trong file `.proto`. Khi bạn gọi object proxy này (tức `heroesService`), gRPC serialize request, chuyển nó tới hệ thống từ xa, trả về một response, và deserialize response. Vì gRPC che chắn bạn khỏi những chi tiết giao tiếp mạng này, `heroesService` trông và hoạt động như một provider cục bộ.

Mọi method của service đều được viết theo **lower camel case**, theo quy ước tự nhiên của ngôn ngữ. Ví dụ, trong khi định nghĩa `HeroesService` trong file `.proto` chứa hàm `FindOne()`, instance `heroesService` cung cấp method `findOne()`.

[[CODE:11]]

Một handler cũng có thể trả về một `Observable`, khi đó các giá trị kết quả được phát ra cho tới khi stream hoàn tất.

[[CODE:12]]

Để gửi gRPC metadata kèm request, hãy truyền một tham số thứ hai, như sau:

[[CODE:13]]

> info **Hint** Class `Metadata` được import từ package `@grpc/grpc-js`.

Điều này yêu cầu cập nhật interface `HeroesService` đã định nghĩa trước đó để nhận tham số thứ hai.

#### Xử lý exception

Các gRPC handler có thể throw `RpcException`, nhưng một `RpcException` thuần không mang gRPC status code, nên client nhận `UNKNOWN` cho mọi lỗi. Bắt đầu từ NestJS v12, package `@nestjs/microservices` đi kèm các exception riêng cho gRPC và một `GrpcExceptionFilter` ánh xạ chúng sang các object lỗi gRPC đúng chuẩn.

Throw một trong các exception theo từng status từ handler của bạn:

[[CODE:14]]

Sau đó đăng ký filter để các exception đó được serialize thành lỗi gRPC:

[[CODE:15]]

Khi có filter, client nhận `ALREADY_EXISTS` thay vì `UNKNOWN`.

Bạn cũng có thể dùng `GrpcException` chung và truyền status một cách tường minh:

[[CODE:16]]

Các class exception theo từng status sau có sẵn. Mỗi class tương ứng với một thành phần của enum `GrpcStatus`:

<table>
  <tr>
    <td><code>GrpcCancelledException</code></td>
    <td><code>GrpcUnknownException</code></td>
    <td><code>GrpcInvalidArgumentException</code></td>
    <td><code>GrpcDeadlineExceededException</code></td>
  </tr>
  <tr>
    <td><code>GrpcNotFoundException</code></td>
    <td><code>GrpcAlreadyExistsException</code></td>
    <td><code>GrpcPermissionDeniedException</code></td>
    <td><code>GrpcResourceExhaustedException</code></td>
  </tr>
  <tr>
    <td><code>GrpcFailedPreconditionException</code></td>
    <td><code>GrpcAbortedException</code></td>
    <td><code>GrpcOutOfRangeException</code></td>
    <td><code>GrpcUnimplementedException</code></td>
  </tr>
  <tr>
    <td><code>GrpcInternalException</code></td>
    <td><code>GrpcUnavailableException</code></td>
    <td><code>GrpcDataLossException</code></td>
    <td><code>GrpcUnauthenticatedException</code></td>
  </tr>
</table>

> info **Hint** `GrpcExceptionFilter` cũng xử lý `RpcException`. Nếu object lỗi được truyền cho constructor của `RpcException` mang thuộc tính số `code` hoặc `status`, giá trị đó được dùng làm gRPC status; nếu không, lỗi được báo cáo là `UNKNOWN`. Mọi exception khác được báo cáo là `UNKNOWN` với một message chung chung.

#### Ví dụ

Một ví dụ chạy được có trong [sample gRPC](https://github.com/nestjs/nest/tree/master/sample/04-grpc) của repository NestJS.

#### gRPC Reflection

[Đặc tả gRPC Server Reflection](https://grpc.io/docs/guides/reflection/#overview) là một chuẩn cho phép gRPC client yêu cầu chi tiết về API mà server cung cấp, tương tự việc cung cấp một tài liệu OpenAPI cho một REST API. Điều này giúp làm việc với các công cụ debug như grpc-ui hay Postman dễ dàng hơn.

Để thêm hỗ trợ gRPC reflection cho server, trước tiên hãy cài package hiện thực:

[[CODE:17]]

Sau đó gắn nó vào gRPC server bằng hook `onLoadPackageDefinition` trong các tùy chọn gRPC server, như sau:

[[CODE:18]]

Giờ server của bạn đã trả lời các reflection request về chi tiết API.

#### gRPC Streaming

gRPC hỗ trợ các kết nối tồn tại lâu, theo quy ước được gọi là `streams`. Stream hữu ích cho các trường hợp như chat, theo dõi, hoặc truyền dữ liệu theo từng phần. Xem [hướng dẫn các khái niệm cốt lõi của gRPC](https://grpc.io/docs/guides/concepts/) để biết chi tiết.

Nest hỗ trợ gRPC stream handler theo hai cách:

- Handler dùng RxJS `Subject` + `Observable`: hữu ích để viết response trực tiếp bên trong một method của controller, hoặc để truyền chúng cho một consumer `Subject`/`Observable`
- Handler dùng call stream gRPC thuần: hữu ích để truyền lời gọi cho một executor xử lý phần còn lại của việc dispatch cho `Duplex` stream tiêu chuẩn của Node.js

<app-banner-enterprise></app-banner-enterprise>

#### Ví dụ streaming

Hãy định nghĩa một service gRPC mẫu mới tên `HelloService`. File `hello.proto` được cấu trúc bằng <a href="https://developers.google.com/protocol-buffers">protocol buffers</a>:

[[CODE:19]]

> info **Hint** `LotsOfGreetings` stream các request nhưng trả về một response duy nhất. Vì request của nó được stream, nó không thể được hiện thực bằng `@GrpcMethod()`; hãy dùng `@GrpcStreamMethod()` (giá trị cuối cùng mà `Observable` trả về phát ra sẽ được gửi làm response) hoặc `@GrpcStreamCall()` (phản hồi qua callback), cả hai đều được trình bày bên dưới.

Dựa trên file `.proto` này, hãy định nghĩa interface `HelloService`:

[[CODE:20]]

> info **Hint** Interface proto có thể được sinh tự động bởi package [ts-proto](https://github.com/stephenh/ts-proto). Xem [hướng dẫn NestJS của ts-proto](https://github.com/stephenh/ts-proto/blob/main/NESTJS.markdown) để tìm hiểu thêm.

#### Chiến lược Subject

Decorator `@GrpcStreamMethod()` cung cấp tham số của hàm dưới dạng một RxJS `Observable`, để handler có thể nhận và xử lý nhiều message.

[[CODE:21]]

> warning **Warning** Để hỗ trợ tương tác full-duplex với decorator `@GrpcStreamMethod()`, method của controller phải trả về một RxJS `Observable`.

> info **Hint** Class `Metadata` và interface `ServerDuplexStream` được import từ package `@grpc/grpc-js`.

Theo định nghĩa service trong file `.proto`, method `BidiHello` stream các request tới service. Để gửi nhiều message bất đồng bộ vào stream từ một client, hãy dùng một RxJS `ReplaySubject`.

[[CODE:22]]

Trong ví dụ ở trên, chúng ta đã ghi hai message vào stream (các lời gọi `next()`) và báo cho service rằng chúng ta đã gửi xong dữ liệu (lời gọi `complete()`).

#### Call stream handler

Khi response của method được định nghĩa là một `stream`, decorator `@GrpcStreamCall()` cung cấp tham số của hàm dưới dạng một `grpc.ServerDuplexStream`, hỗ trợ các method tiêu chuẩn như `.on('data', callback)`, `.write(message)` và `.end()`. Xem [tài liệu tham khảo API Node.js của gRPC](https://grpc.github.io/grpc/node/grpc-ClientDuplexStream.html) để biết danh sách đầy đủ các method.

Khi response của method không phải là một `stream`, decorator `@GrpcStreamCall()` cung cấp hai tham số của hàm: một `grpc.ServerReadableStream` (xem [tài liệu tham khảo `ServerReadableStream`](https://grpc.github.io/grpc/node/grpc-ServerReadableStream.html)) và một `callback`.

Hãy bắt đầu bằng việc hiện thực `BidiHello`, method hỗ trợ tương tác full-duplex.

[[CODE:23]]

> info **Hint** Decorator này không yêu cầu handler trả về gì cả. Bạn xử lý stream như với bất kỳ stream tiêu chuẩn nào khác.

Trong ví dụ ở trên, chúng ta đã dùng method `write()` để ghi các object vào response stream. Callback được truyền cho method `.on()` làm tham số thứ hai được gọi mỗi khi service nhận được một phần dữ liệu mới.

Tiếp theo, hãy hiện thực method `LotsOfGreetings`.

[[CODE:24]]

Ở đây, hàm `callback` gửi response khi `requestStream` đã được xử lý xong.

#### Health check

Khi bạn chạy một ứng dụng gRPC trong một orchestrator như Kubernetes, orchestrator cần biết ứng dụng có đang chạy và khỏe mạnh không. [Đặc tả gRPC Health Check](https://grpc.io/docs/guides/health-checking/) là một chuẩn cho phép gRPC server công bố tình trạng sức khỏe của nó để orchestrator có thể hành động phù hợp.

Để thêm hỗ trợ gRPC health check, trước tiên hãy cài package [grpc-health-check](https://github.com/grpc/grpc-node/tree/master/packages/grpc-health-check):

[[CODE:25]]

Sau đó gắn nó vào service gRPC bằng hook `onLoadPackageDefinition` trong các tùy chọn gRPC server, như sau. `protoPath` phải bao gồm cả file `.proto` của health check lẫn của hero.

[[CODE:26]]

> info **Hint** [gRPC health probe](https://github.com/grpc-ecosystem/grpc-health-probe) là một CLI để test gRPC health check trong môi trường container.

#### gRPC Metadata

Metadata là thông tin về một lời gọi RPC cụ thể dưới dạng một danh sách các cặp key-value, trong đó key là chuỗi và value thường là chuỗi nhưng cũng có thể là dữ liệu nhị phân. Bản thân gRPC không quan tâm tới nội dung metadata: nó cho phép client cung cấp thông tin liên quan tới lời gọi cho server, và ngược lại. Metadata có thể bao gồm token xác thực, định danh request và tag cho mục đích giám sát, và thông tin dữ liệu như số bản ghi trong một tập dữ liệu.

Để đọc metadata trong một handler `@GrpcMethod()`, hãy dùng tham số thứ hai (`metadata`), có type `Metadata` (được import từ package `@grpc/grpc-js`).

Để gửi metadata ngược lại từ handler, hãy dùng method `ServerUnaryCall#sendMetadata()` (trên tham số thứ ba của handler).

[[CODE:27]]

Tương tự, để đọc metadata trong các handler được chú thích bằng decorator `@GrpcStreamMethod()` (xem [Chiến lược Subject](/microservices/grpc#subject-strategy)), hãy dùng tham số thứ hai (`metadata`), có type `Metadata` (được import từ package `@grpc/grpc-js`).

Để gửi metadata ngược lại từ handler, hãy dùng method `ServerDuplexStream#sendMetadata()` (trên tham số thứ ba của handler).

Để đọc metadata từ bên trong [call stream handler](/microservices/grpc#call-stream-handler) (các handler được chú thích bằng decorator `@GrpcStreamCall()`), hãy lắng nghe event `metadata` trên tham chiếu `requestStream`, như sau:

[[CODE:28]]
