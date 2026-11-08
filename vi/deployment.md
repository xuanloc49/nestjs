### Deployment

Khi bạn đã sẵn sàng deploy ứng dụng NestJS lên production, có một số bước quan trọng bạn có thể làm để đảm bảo nó chạy hiệu quả nhất có thể. Hướng dẫn này bao gồm các mẹo thiết yếu và best practice để deploy ứng dụng NestJS thành công.

Nếu bạn không muốn tự quản lý hạ tầng, [Mau](https://mau.nestjs.com/ 'Deploy Nest'), nền tảng deploy chính thức của chúng tôi, đưa bạn lên production trên AWS chỉ với một lệnh. Hãy chuyển thẳng tới [Deploy dễ dàng với Mau](/deployment#easy-deployment-with-mau), hoặc đọc tiếp để nắm các khái niệm nền tảng áp dụng cho mọi lựa chọn hosting.

#### Yêu cầu trước <a id="prerequisites"></a>

Trước khi deploy ứng dụng NestJS, hãy đảm bảo bạn có:

- Một ứng dụng NestJS chạy được và sẵn sàng để deploy.
- Quyền truy cập vào một nền tảng deploy hoặc server nơi bạn có thể host ứng dụng.
- Mọi biến môi trường cần thiết cho ứng dụng đã được thiết lập.
- Mọi service cần thiết, như database, đã được thiết lập và sẵn sàng.
- Node.js 20.19 trở lên (22.12 trở lên với dòng 22.x) được cài trên nền tảng deploy, như mô tả trong [Yêu cầu trước](/first-steps#prerequisites). Hãy ưu tiên một phiên bản Node.js vẫn còn trong giai đoạn active LTS.

> info **Gợi ý** Với [Mau](https://mau.nestjs.com/ 'Deploy Nest'), phần lớn danh sách ở trên được lo giúp bạn: nó cấp phát server, các database và broker mà ứng dụng cần, cùng các biến môi trường, nên yêu cầu duy nhất còn lại là bản thân ứng dụng.

#### Build ứng dụng <a id="building-your-application"></a>

Để build ứng dụng NestJS, hãy biên dịch code TypeScript thành JavaScript. Quá trình này tạo ra một thư mục `dist` chứa các file đã biên dịch. Build ứng dụng bằng cách chạy lệnh sau:

```bash
$ npm run build
```

Lệnh này thường chạy `nest build` bên dưới, một wrapper quanh trình biên dịch TypeScript với một số tính năng bổ sung (như copy asset). Nếu bạn có một build script tùy chỉnh, bạn có thể chạy trực tiếp nó. Với monorepo của Nest CLI, hãy truyền tên project cần build làm tham số (`npm run build my-app`).

Sau khi biên dịch thành công, bạn sẽ thấy một thư mục `dist` ở thư mục gốc của project chứa các file đã biên dịch, với `main.js` là entry point. Nếu bạn có file `.ts` nào ở thư mục gốc của project (và `tsconfig.json` được cấu hình để biên dịch chúng), chúng cũng được biên dịch vào thư mục `dist`, điều này làm thay đổi cấu trúc thư mục: thay vì `dist/main.js`, bạn sẽ có `dist/src/main.js`. Hãy lưu ý điều đó khi cấu hình server.

#### Môi trường production <a id="production-environment"></a>

Môi trường production là nơi người dùng bên ngoài truy cập được ứng dụng của bạn. Đó có thể là một nền tảng cloud như [AWS](https://aws.amazon.com/) (với EC2, ECS, v.v.), [Azure](https://azure.microsoft.com/) hay [Google Cloud](https://cloud.google.com/), hoặc một server riêng do bạn quản lý, như [Hetzner](https://www.hetzner.com/).

Để đơn giản hóa quá trình deploy và tránh phải thiết lập thủ công, bạn có thể dùng [Mau](https://mau.nestjs.com/ 'Deploy Nest'), nền tảng chính thức của chúng tôi để deploy ứng dụng NestJS trên AWS. Nó cho bạn những lợi ích của AWS liệt kê bên dưới mà không cần bạn tự cấu hình gì cả. Xem [Deploy dễ dàng với Mau](/deployment#easy-deployment-with-mau) để biết chi tiết.

Một số ưu điểm của việc dùng một **nền tảng cloud** hoặc dịch vụ như [Mau](https://mau.nestjs.com/ 'Deploy Nest') bao gồm:

- Khả năng mở rộng: Mở rộng ứng dụng khi lượng người dùng tăng lên.
- Bảo mật: Hưởng lợi từ các tính năng bảo mật có sẵn và các chứng nhận tuân thủ.
- Giám sát: Theo dõi hiệu năng và tình trạng của ứng dụng theo thời gian thực.
- Độ tin cậy: Đảm bảo ứng dụng luôn sẵn sàng với cam kết uptime cao.

Mặt khác, các nền tảng cloud thường đắt hơn việc tự host, và bạn có thể ít quyền kiểm soát hạ tầng bên dưới hơn. Một VPS đơn giản có thể là lựa chọn tốt nếu bạn tìm một giải pháp tiết kiệm hơn và có chuyên môn kỹ thuật để tự quản lý server. Hãy nhớ rằng bạn sẽ phải tự lo các việc như bảo trì server, bảo mật và backup.

#### NODE_ENV=production

Dù về mặt kỹ thuật không có khác biệt nào giữa development và production trong Node.js và NestJS, việc đặt biến môi trường `NODE_ENV` thành `production` khi chạy ứng dụng trong môi trường production là một thói quen tốt, vì một số library trong hệ sinh thái hoạt động khác đi dựa trên biến này (ví dụ bật hoặc tắt output debug).

Bạn có thể đặt biến môi trường `NODE_ENV` khi khởi động ứng dụng:

```bash
$ NODE_ENV=production node dist/main.js
```

Ngoài ra, hãy đặt nó trong dashboard của nhà cung cấp cloud hoặc của Mau.

#### Chạy ứng dụng <a id="running-your-application"></a>

Để chạy ứng dụng NestJS trong production, hãy dùng lệnh sau:

```bash
$ node dist/main.js # Adjust this based on your entry point location
```

Lệnh này khởi động ứng dụng, lắng nghe trên port được truyền cho `app.listen()` (`3000` trong các project mới được tạo, trừ khi biến môi trường `PORT` được đặt). Hãy đảm bảo nền tảng deploy định tuyến lưu lượng tới port đó.

Ngoài ra, bạn có thể dùng lệnh `nest start`. Nó là một wrapper quanh `node dist/main.js`, với một khác biệt quan trọng: nó chạy `nest build` trước khi khởi động ứng dụng, nên bạn không cần tự chạy `npm run build`.

#### Health check <a id="health-checks"></a>

Health check là thiết yếu để theo dõi tình trạng và trạng thái của ứng dụng NestJS trong production. Với một endpoint health check, bạn có thể thường xuyên xác minh ứng dụng đang chạy như mong đợi và phản ứng với các vấn đề trước khi chúng trở nên nghiêm trọng.

Trong NestJS, bạn có thể hiện thực health check bằng package **@nestjs/terminus**, package này hỗ trợ kiểm tra kết nối database, service bên ngoài và các indicator tùy chỉnh.

Xem chương [health check (Terminus)](/reliability/terminus) để tìm hiểu cách hiện thực health check trong ứng dụng NestJS.

#### Logging

Logging là thiết yếu với mọi ứng dụng sẵn sàng cho production. Nó giúp bạn theo dõi lỗi, giám sát hành vi và xử lý sự cố. Trong NestJS, bạn có thể quản lý logging bằng [logger có sẵn](/application/logger), hoặc chọn các library bên ngoài nếu bạn cần các tính năng nâng cao hơn.

Các best practice cho logging:

- Log lỗi, không phải exception: Tập trung vào việc log các error message chi tiết để tăng tốc debug và xử lý sự cố.
- Tránh dữ liệu nhạy cảm: Không bao giờ log thông tin nhạy cảm như mật khẩu hay token.
- Dùng correlation ID: Trong các hệ thống phân tán, hãy đưa các định danh duy nhất (như correlation ID) vào log để trace request xuyên qua các service.
- Dùng log level: Phân loại log theo mức độ nghiêm trọng (ví dụ `info`, `warn`, `error`), và tắt log debug hoặc verbose trong production để giảm nhiễu.

> info **Gợi ý** Nếu bạn dùng [AWS](https://aws.amazon.com/) (qua [Mau](https://mau.nestjs.com/ 'Deploy Nest') hoặc trực tiếp), hãy cân nhắc log dạng JSON để dễ parse và phân tích log hơn.

Với các ứng dụng phân tán, một dịch vụ logging tập trung như Elasticsearch, Loggly hay Datadog rất hữu ích. Những công cụ này cung cấp khả năng tổng hợp, tìm kiếm và trực quan hóa log, giúp việc giám sát và phân tích hiệu năng cũng như hành vi của ứng dụng dễ dàng hơn.

#### Observability

Health check và log cho bạn biết ứng dụng có đang chạy hay không; chúng không cho bạn biết route nào chậm đi sau lần deploy vừa rồi, class nào đang ngốn thời gian, hay dòng nào đã throw. Để biết những điều đó, hãy instrument ứng dụng bằng [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe'), nền tảng observability chính thức của chúng tôi: cài SDK `@nestjs/observe`, truyền một API key, và request, job, lỗi, log cùng trace sẽ bắt đầu được gửi tới một dashboard mà không cần tự nối span hay vận hành collector nào.

```typescript
const app = await NestFactory.create(AppModule, {
  instrument: ObserveInstrument,
});
```

Xem chương [Observability](/observability/overview) để biết toàn bộ cách thiết lập, bao gồm việc đánh phiên bản các lần deploy bằng `serviceVersion` để mỗi bản release được so sánh với bản trước nó.

#### Scale up hay scale out <a id="scaling-up-or-out"></a>

Mở rộng ứng dụng NestJS một cách hiệu quả là điều cốt yếu để xử lý lưu lượng tăng lên và đảm bảo hiệu năng tối ưu. Có hai chiến lược chính để mở rộng: **mở rộng theo chiều dọc** và **mở rộng theo chiều ngang**. Hiểu cả hai giúp bạn thiết kế ứng dụng để xử lý tải hiệu quả.

**Mở rộng theo chiều dọc**, thường gọi là "scale up", là tăng tài nguyên của một server duy nhất để cải thiện hiệu năng của nó. Điều này có thể là thêm CPU, RAM hoặc dung lượng lưu trữ cho máy hiện có. Những điểm chính cần cân nhắc:

- Đơn giản: Mở rộng theo chiều dọc thường đơn giản hơn để thực hiện vì bạn chỉ cần nâng cấp server hiện có thay vì quản lý nhiều instance.
- Giới hạn: Có những giới hạn vật lý về việc bạn có thể mở rộng một máy tới mức nào. Khi chạm công suất tối đa, bạn có thể cần cân nhắc các lựa chọn khác.
- Tiết kiệm chi phí: Với các ứng dụng có lưu lượng vừa phải, mở rộng theo chiều dọc có thể tiết kiệm chi phí, vì nó giảm nhu cầu hạ tầng bổ sung.

Ví dụ: Nếu ứng dụng NestJS của bạn được host trên một máy ảo và bạn nhận thấy nó chạy chậm vào giờ cao điểm, bạn có thể nâng cấp VM lên một instance lớn hơn với nhiều tài nguyên hơn, thường bằng cách chọn một loại instance lớn hơn trong dashboard của nhà cung cấp.

**Mở rộng theo chiều ngang**, hay "scale out", là thêm nhiều server hoặc instance hơn để phân phối tải. Chiến lược này được dùng rộng rãi trong các môi trường cloud và là thiết yếu với các ứng dụng dự kiến có lưu lượng cao. Lợi ích và những điều cần cân nhắc:

- Tăng công suất: Bằng cách thêm nhiều instance của ứng dụng, bạn có thể xử lý số lượng người dùng đồng thời lớn hơn mà không làm giảm hiệu năng.
- Dự phòng: Một server hỏng không làm sập toàn bộ ứng dụng, vì lưu lượng có thể được phân phối lại cho các server còn lại.
- Cân bằng tải: Để quản lý nhiều instance hiệu quả, hãy dùng load balancer (như Nginx hoặc AWS Elastic Load Balancing) để phân phối đều lưu lượng đi vào trên các server.

Ví dụ: Với một ứng dụng NestJS có lưu lượng cao, bạn có thể deploy nhiều instance của ứng dụng trong một môi trường cloud và dùng một load balancer để định tuyến request, đảm bảo không instance nào trở thành nút cổ chai.

Các công nghệ container hóa như [Docker](https://www.docker.com/) và các nền tảng điều phối container như [Kubernetes](https://kubernetes.io/) giúp quá trình này trở nên đơn giản. Bạn cũng có thể dùng các load balancer riêng của cloud như [AWS Elastic Load Balancing](https://aws.amazon.com/elasticloadbalancing/) hay [Azure Load Balancer](https://azure.microsoft.com/en-us/services/load-balancer/) để phân phối lưu lượng giữa các instance của ứng dụng.

> info **Gợi ý** [Mau](https://mau.nestjs.com/ 'Deploy Nest') hỗ trợ sẵn mở rộng theo chiều ngang trên AWS, nên bạn có thể deploy nhiều instance của ứng dụng NestJS và quản lý chúng chỉ với vài cú click.

#### Một số mẹo khác <a id="some-other-tips"></a>

Hãy ghi nhớ những mẹo bổ sung này khi deploy ứng dụng NestJS:

- **Bảo mật**: Bảo vệ ứng dụng khỏi các mối đe dọa phổ biến như SQL injection và XSS. Xem các chương trong mục "Security", như [Helmet](/security/helmet) và [CORS](/security/cors), để biết chi tiết.
- **Giám sát**: Dùng các công cụ giám sát như [Prometheus](https://prometheus.io/) hay [New Relic](https://newrelic.com/) để theo dõi hiệu năng và tình trạng của ứng dụng. Các nhà cung cấp cloud và Mau có thể cung cấp sẵn các dịch vụ giám sát (như [AWS CloudWatch](https://aws.amazon.com/cloudwatch/)).
- **Không hardcode biến môi trường**: Tránh hardcode thông tin nhạy cảm như API key, mật khẩu hay token trong code. Hãy dùng biến môi trường hoặc một secret manager để lưu và truy cập các giá trị này một cách an toàn.
- **Backup**: Thường xuyên backup dữ liệu để tránh mất dữ liệu khi có sự cố.
- **Tự động hóa deploy**: Dùng các pipeline CI/CD để tự động hóa quá trình deploy và đảm bảo tính nhất quán giữa các môi trường.
- **Rate limiting**: Hiện thực rate limiting để ngăn lạm dụng và bảo vệ ứng dụng khỏi các cuộc tấn công DDoS. Xem chương [rate limiting](/security/rate-limiting) để biết chi tiết, hoặc dùng một dịch vụ như [AWS WAF](https://aws.amazon.com/waf/) để được bảo vệ nâng cao.

#### Docker hóa ứng dụng <a id="dockerizing-your-application"></a>

[Docker](https://www.docker.com/) là một nền tảng dùng container hóa để cho phép developer đóng gói ứng dụng cùng các dependency của nó thành một đơn vị chuẩn hóa gọi là container. Container gọn nhẹ, dễ di chuyển và cô lập, khiến chúng lý tưởng để deploy ứng dụng trong nhiều môi trường khác nhau, từ phát triển ở local tới production.

Lợi ích của việc Docker hóa ứng dụng NestJS:

- Nhất quán: Docker đảm bảo ứng dụng chạy giống nhau trên mọi máy, loại bỏ vấn đề "trên máy tôi chạy được mà".
- Cô lập: Mỗi container chạy trong môi trường cô lập riêng, tránh xung đột giữa các dependency.
- Khả năng mở rộng: Bạn có thể mở rộng ứng dụng bằng cách chạy nhiều container trên các máy hoặc cloud instance khác nhau.
- Tính di động: Container di chuyển giữa các môi trường mà không cần thay đổi, nên bạn có thể deploy ứng dụng trên các nền tảng khác nhau.

Để cài Docker, hãy làm theo hướng dẫn trên [website Docker](https://www.docker.com/get-started). Khi đã cài Docker, hãy tạo một `Dockerfile` trong project NestJS. Đó là một file text chứa các chỉ dẫn mà Docker dùng để build container image.

Đây là một `Dockerfile` mẫu cho một ứng dụng NestJS:

```bash
# Use the official Node.js image as the base image
FROM node:24

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install the application dependencies
RUN npm install

# Copy the rest of the application files
COPY . .

# Build the NestJS application
RUN npm run build

# Expose the application port
EXPOSE 3000

# Command to run the application
CMD ["node", "dist/main"]
```

> info **Gợi ý** Hãy thay `node:24` bằng phiên bản Node.js mà project của bạn dùng (NestJS v12 cần Node.js 20.19 trở lên, hoặc 22.12 trở lên với dòng 22.x). Bạn có thể tìm các Docker image Node.js có sẵn trong [repository chính thức trên Docker Hub](https://hub.docker.com/_/node).

`Dockerfile` cơ bản này thiết lập môi trường Node.js, cài các dependency của ứng dụng, build ứng dụng NestJS và chạy nó. Bạn có thể tùy chỉnh nó theo yêu cầu của project (ví dụ dùng một base image khác, tối ưu quá trình build, hoặc chỉ cài các dependency cho production).

Tiếp theo, tạo một file `.dockerignore` ở thư mục gốc của project để chỉ định các file và thư mục mà Docker nên bỏ qua khi build image:

```bash
node_modules
dist
*.log
*.md
.git
```

File này giữ các file không cần thiết ngoài container image, giúp image gọn nhẹ. Khi đã có `Dockerfile`, bạn có thể build Docker image. Mở terminal, chuyển tới thư mục project, và chạy lệnh sau:

```bash
docker build -t my-nestjs-app .
```

Trong lệnh này:

- `-t my-nestjs-app`: Gắn tag cho image với tên `my-nestjs-app`.
- `.`: Chỉ định thư mục hiện tại làm build context.

Sau khi build image, hãy chạy nó dưới dạng container:

```bash
docker run -p 3000:3000 my-nestjs-app
```

Trong lệnh này:

- `-p 3000:3000`: Ánh xạ port 3000 trên máy host tới port 3000 trong container.
- `my-nestjs-app`: Chỉ định image cần chạy.

Giờ ứng dụng NestJS của bạn sẽ chạy bên trong một Docker container.

Để deploy Docker image lên một nhà cung cấp cloud hoặc chia sẻ nó với người khác, hãy push nó lên một container registry (như [Docker Hub](https://hub.docker.com/), [Amazon ECR](https://aws.amazon.com/ecr/) hay [Google Artifact Registry](https://cloud.google.com/artifact-registry)).

Khi đã chọn registry, hãy push image:

```bash
docker login # Log in to your Docker registry
docker tag my-nestjs-app your-dockerhub-username/my-nestjs-app # Tag your image
docker push your-dockerhub-username/my-nestjs-app # Push your image
```

Thay `your-dockerhub-username` bằng username Docker Hub của bạn hoặc URL registry phù hợp. Sau khi push image, bạn có thể pull nó về bất kỳ máy nào và chạy nó dưới dạng container.

Các nhà cung cấp cloud như AWS, Azure và Google Cloud cung cấp các dịch vụ container được quản lý giúp đơn giản hóa việc deploy và quản lý container ở quy mô lớn. Các dịch vụ này cung cấp những tính năng như auto-scaling, cân bằng tải và giám sát cho ứng dụng NestJS trong production.

#### Deploy dễ dàng với Mau <a id="easy-deployment-with-mau"></a>

[Mau](https://mau.nestjs.com/ 'Deploy Nest') là nền tảng chính thức của chúng tôi để deploy ứng dụng NestJS trên [AWS](https://aws.amazon.com/). Nó lo mọi thứ mà các phần trước mô tả (cấp phát server, nối database và broker, quản lý biến môi trường, mở rộng, giám sát và CI/CD), nên bạn không phải tự lắp ráp chúng.

##### Deploy <a id="deploying"></a>

Từ NestJS v12, Nest CLI đi kèm lệnh `deploy`. Chạy nó từ thư mục gốc của project:

```bash
$ nest deploy
```

Nếu Mau chưa được cài, lệnh sẽ đề nghị thêm `@nestjs/mau` làm dev dependency rồi tiếp tục. Mọi tùy chọn bạn truyền vào đều được chuyển tiếp cho `mau deploy`. Xem [nest deploy](/cli/usages#nest-deploy) để biết chi tiết.

Bạn cũng có thể cài Mau CLI ở phạm vi global và gọi trực tiếp nó. Đây là lựa chọn đúng cho môi trường CI, nơi không có prompt tương tác:

```bash
$ npm install -g @nestjs/mau
$ mau deploy
```

Khi deploy hoàn tất, ứng dụng của bạn đã chạy trên AWS, thường chỉ trong vài phút kể từ lần chạy đầu tiên.

##### Tại sao dùng Mau <a id="why-mau"></a>

Với Mau, việc cấp phát và bảo trì hạ tầng chỉ cần vài cú click. Bên dưới, Mau dùng **Amazon Web Services** để cho bạn một nền tảng mạnh mẽ và đáng tin cậy, đồng thời che đi sự phức tạp của AWS. Bạn nhận được những lợi thế của AWS mà không cần học và quản lý các chi tiết của nó, điều khiến Mau phù hợp với các startup, doanh nghiệp vừa và nhỏ, doanh nghiệp lớn, và bất kỳ developer nào muốn ship sản phẩm hơn là cấu hình hạ tầng.

<figure><img src="https://www.mau.nestjs.com/docs/applications/dashboard.png" /></figure>

Với [Mau](https://mau.nestjs.com/ 'Deploy Nest'), bạn có thể:

- Deploy ứng dụng NestJS chỉ với vài cú click (API, microservice, v.v.).
- Cấp phát **database** như:
  - PostgreSQL
  - MySQL
  - MongoDB (DocumentDB)
  - Redis
  - và nhiều loại khác
- Thiết lập các dịch vụ broker như:
  - RabbitMQ
  - Kafka
  - NATS
- Deploy các tác vụ theo lịch (**CRON job**) và background worker.
- Deploy lambda function và ứng dụng serverless.
- Thiết lập **pipeline CI/CD** cho việc deploy tự động.
- Và nhiều hơn nữa.

##### Mau tương ứng với hướng dẫn này thế nào <a id="how-mau-maps-to-this-guide"></a>

Mỗi chủ đề được trình bày trước đó trong chương này đều có một phiên bản được quản lý tương đương trong Mau:

<table>
  <tr>
    <td><a href="/deployment#node_envproduction">Biến môi trường</a></td>
    <td>Đặt <code>NODE_ENV</code> và các secret trong dashboard của Mau thay vì quản lý chúng trên server.</td>
  </tr>
  <tr>
    <td><a href="/deployment#logging">Logging</a></td>
    <td>Log được thu thập và xem được trong dashboard. Log dạng JSON đặc biệt hữu ích ở đây; xem <a href="/application/logger">chương Logger</a>.</td>
  </tr>
  <tr>
    <td><a href="/deployment#scaling-up-or-out">Mở rộng</a></td>
    <td>Hỗ trợ sẵn mở rộng theo chiều ngang: chạy nhiều instance của ứng dụng và quản lý chúng từ dashboard.</td>
  </tr>
  <tr>
    <td><a href="/deployment#health-checks">Health check</a></td>
    <td>Trỏ Mau tới endpoint mà bạn đưa ra bằng <a href="/reliability/terminus">Terminus</a> và các instance không khỏe sẽ được xử lý giúp bạn.</td>
  </tr>
  <tr>
    <td><a href="/deployment#some-other-tips">Giám sát và backup</a></td>
    <td>Metric đến từ AWS CloudWatch, và các database được quản lý được backup tự động.</td>
  </tr>
</table>

Hãy đăng ký ngay hôm nay và [deploy với Mau](https://mau.nestjs.com/ 'Deploy Nest') để đưa ứng dụng NestJS của bạn lên AWS chỉ trong vài phút.
