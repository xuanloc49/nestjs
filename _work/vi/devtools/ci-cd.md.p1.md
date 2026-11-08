### Tích hợp CI/CD

> info **Hint** Chương này nói về việc tích hợp Nest Devtools với framework Nest. Nếu bạn đang tìm ứng dụng Devtools, hãy truy cập website [Devtools](https://devtools.nestjs.com). Tích hợp CI/CD có trong gói **[Enterprise](https://devtools.nestjs.com/settings)**.

Dùng ở local rất tốt để khám phá ứng dụng trong lúc xây dựng nó, nhưng lợi ích thực sự đến khi Devtools trở thành một phần của pipeline delivery. Tích hợp CI/CD publish một snapshot đồ thị ứng dụng của bạn ở mỗi lần build. Bạn có một lịch sử liên tục về cách kiến trúc thay đổi theo thời gian và, quan trọng hơn, một report tự động trên mỗi pull request cho thấy chính xác những gì đã thay đổi về mặt cấu trúc. Đó là khác biệt giữa việc hy vọng một lần refactor không làm hỏng gì và việc biết chắc nó không làm hỏng gì.

Xem lý do các team dựa vào tích hợp CI/CD để bắt sự lệch kiến trúc trước khi nó được ship:

<figure>
  <iframe
    width="1000"
    height="565"
    src="https://www.youtube.com/embed/r5RXcBrnEQ8"
    title="YouTube video player"
    frameBorder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowFullScreen
  ></iframe>
</figure>

#### Publish đồ thị

Trước tiên, cấu hình file bootstrap của ứng dụng (`main.ts`) để dùng class `GraphPublisher`, được export từ `@nestjs/devtools-integration` (xem [tổng quan Devtools](/devtools/overview) nếu bạn chưa cài nó):

[[CODE:1]]

Ở đây, `GraphPublisher` đẩy đồ thị đã serialize của bạn lên registry tập trung. `PUBLISH_GRAPH` là một biến môi trường tự định nghĩa, dùng để phân biệt một lần chạy publish trên CI/CD với một lần bootstrap ứng dụng thông thường. Đặt `preview` thành `true` sẽ bootstrap ứng dụng ở preview mode, nghĩa là constructor và lifecycle hook của các controller, enhancer và provider sẽ không được thực thi. Điều này không **bắt buộc**, nhưng nó giúp các lần chạy CI nhanh và đơn giản (ví dụ không cần kết nối database).

Cấu trúc của `publishOptions` phụ thuộc vào nhà cung cấp CI/CD của bạn. Các phần bên dưới đề cập tới những nhà cung cấp phổ biến nhất. Nếu nhà cung cấp của bạn không có trong danh sách, các field bên dưới đều giống nhau ở mọi nơi, nên bạn có thể điều chỉnh cấu hình trong vài phút.

Khi đồ thị được publish thành công, bạn sẽ thấy output như thế này trong log của workflow:

<figure><img src="/assets/devtools/graph-published-terminal.png" /></figure>

Mỗi đồ thị được publish hiện lên như một mục mới trên trang của project:

<figure><img src="/assets/devtools/project.png" /></figure>

#### Report

Devtools sinh một report cho mỗi lần build, **miễn là** đã có một snapshot tương ứng trong registry. Nếu bạn mở một pull request nhắm tới `master` và một đồ thị cho `master` đã được publish trước đó, Devtools phát hiện các khác biệt và tự động tạo report. Nếu không, sẽ chưa có gì để so sánh.

Bạn tìm report ở trang của project (xem [organizations](https://devtools.nestjs.com/organizations)).

<figure><img src="/assets/devtools/report.png" /></figure>

Đây là chỗ Devtools thực sự đáng đồng tiền: bắt được những thay đổi lọt qua code review. Giả sử ai đó lặng lẽ đổi scope của một **provider lồng sâu**. Điều đó dễ bị bỏ sót trong một diff, nhưng không thể bỏ sót trong report. Gỡ một guard khỏi một endpoint, và nó hiện ra ngay dưới dạng một thay đổi bị ảnh hưởng. Nếu integration test hay e2e test không bao phủ route đó, có thể bạn sẽ không nhận ra cho tới khi đã quá muộn. Devtools bắt được nó ngay lúc review.

Điều tương tự áp dụng cho **codebase lớn**: chuyển một module thành global, và bạn thấy ngay có bao nhiêu cạnh mới xuất hiện trên đồ thị, thường là một tín hiệu rõ ràng rằng có gì đó cần xem lại.

Report cũng là thứ rất nên đính link trong mô tả pull request. Thay vì bảo reviewer tin rằng "thay đổi này chỉ đụng tới billing module", bạn có thể chỉ cho họ chính xác tập node và cạnh đã thay đổi, biến một khẳng định về kiến trúc thành thứ họ có thể kiểm chứng trong vài giây.

#### Xem trước bản build

Bạn có thể xem lại mọi đồ thị đã publish: click **Preview** để thấy chính xác nó trông thế nào ở thời điểm đó. Khi có report, các khác biệt được highlight trực tiếp trên đồ thị:

- node màu xanh lá là các phần tử được thêm
- node màu trắng nhạt là các phần tử được cập nhật
- node màu đỏ là các phần tử bị xóa

Nó trông như thế này:

<figure><img src="/assets/devtools/nodes-selection.png" /></figure>

Khả năng tua lại và so sánh đồ thị khiến việc xử lý sự cố trở nên đơn giản, không còn phải đoán cái gì đã thay đổi và khi nào. Hãy thiết lập sao cho mỗi pull request (hoặc thậm chí mỗi commit) đều có snapshot riêng trong registry, và bạn sẽ luôn có một dấu vết rõ ràng để lần theo. Hãy coi Devtools như một hệ thống version control hiểu cách Nest lắp ráp ứng dụng của bạn, và có thể **cho bạn thấy** khác biệt thay vì chỉ mô tả nó.

#### Tích hợp: GitHub Actions

Tạo một file workflow mới trong `.github/workflows` (ví dụ `publish-graph.yml`) với nội dung sau:

[[CODE:2]]

> info **Hint** Để bảo mật tốt hơn, hãy lưu `DEVTOOLS_API_KEY` dưới dạng GitHub secret thay vì hardcode nó. Xem [Creating secrets for a repository](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository).

Workflow này chạy trên mỗi pull request và trên các lần push trực tiếp lên `master`. Hãy điều chỉnh nó theo nhu cầu của project; yêu cầu duy nhất là phải cung cấp các biến môi trường mà `GraphPublisher` dựa vào.

Trước khi workflow có thể chạy, hãy điền biến còn lại: `DEVTOOLS_API_KEY`. Tạo một API key riêng cho project của bạn ở **[trang API keys](https://devtools.nestjs.com/settings/manage-api-keys)**.

Cuối cùng, quay lại `main.ts` và điền object `publishOptions` mà chúng ta đã để trống trước đó:

[[CODE:3]]

Để có trải nghiệm mượt mà nhất, chúng tôi cũng khuyên cài **GitHub application** cho project bằng cách click "Integrate GitHub app" (xem bên dưới). Việc này không bắt buộc, nhưng rất đáng làm.

<figure><img src="/assets/devtools/integrate-github-app.png" /></figure>

Khi đã cài app, bạn thấy trạng thái tạo preview và report ngay bên trong pull request:

<figure><img src="/assets/devtools/actions-preview.png" /></figure>

#### Tích hợp: Gitlab Pipelines

Tạo một file `.gitlab-ci.yml` ở thư mục gốc của project với định nghĩa sau:

[[CODE:4]]

> info **Hint** Giống như với GitHub, chúng tôi khuyên lưu `DEVTOOLS_API_KEY` dưới dạng CI/CD secret thay vì commit nó.

Pipeline này chạy trên mỗi merge request và trên các lần push trực tiếp lên `master`. Hãy điều chỉnh nó cho phù hợp với project, nhưng đảm bảo các biến môi trường mà `GraphPublisher` cần luôn có mặt.

Một biến trong định nghĩa này vẫn cần giá trị thật: `DEVTOOLS_API_KEY`. Tạo một API key riêng cho project của bạn ở **[trang API keys](https://devtools.nestjs.com/settings/manage-api-keys)**.

Cuối cùng, quay lại `main.ts` và điền object `publishOptions` mà chúng ta đã để trống trước đó:

[[CODE:5]]

#### Các công cụ CI/CD khác

Việc tích hợp không phụ thuộc vào GitHub hay GitLab. Tất cả những gì `GraphPublisher` cần là vài giá trị mô tả lần build hiện tại (cái gì kích hoạt nó, commit nào, branch nào), nên nó hoạt động với mọi nhà cung cấp, bao gồm [Bitbucket Pipelines](https://bitbucket.org/product/features/pipelines), [CircleCI](https://circleci.com/), và nhiều nhà cung cấp khác.

Đây là cấu trúc đầy đủ của `publishOptions` và ý nghĩa của từng field, để bạn có thể kết nối với bất kỳ pipeline nào:

[[CODE:6]]

Hầu hết các giá trị này có sẵn trong các biến môi trường có sẵn của nhà cung cấp CI/CD. Hãy xem tài liệu [CircleCI built-in environment variables](https://circleci.com/docs/variables/#built-in-environment-variables) và [Bitbucket variables and secrets](https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/) làm điểm khởi đầu.

Với các trigger của pipeline, chúng tôi khuyên thiết lập như sau:

- `push`: chỉ với các branch đại diện cho một môi trường deploy, ví dụ `master`, `main`, `staging`, hoặc `production`.
- `pull request`: luôn luôn, hoặc ít nhất khi **branch đích** là một môi trường deploy (xem ở trên).

Sự kết hợp này giúp registry luôn có snapshot của mọi trạng thái có thể deploy của `master`, trong khi vẫn sinh report cho mỗi pull request nhắm tới nó. Chính sự kết hợp đó là thứ khiến report trở nên hữu ích ngay từ đầu.
