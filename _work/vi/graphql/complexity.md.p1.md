### Độ phức tạp

> warning **Warning** Chương này chỉ áp dụng cho cách tiếp cận code first.

Query complexity cho phép bạn định nghĩa mức độ phức tạp của các field nhất định, và giới hạn query bằng một **độ phức tạp tối đa**. Ý tưởng là biểu diễn độ phức tạp của mỗi field bằng một con số. Một mặc định phổ biến là cho mỗi field độ phức tạp `1`. Bạn cũng có thể tùy chỉnh cách tính độ phức tạp của một GraphQL query bằng các complexity estimator. Một complexity estimator là một hàm tính độ phức tạp của một field. Bạn có thể thêm bao nhiêu estimator tùy thích vào rule, và chúng chạy lần lượt. Estimator đầu tiên trả về một giá trị số sẽ quyết định độ phức tạp của field đó.

Package `@nestjs/graphql` tích hợp với các công cụ như [graphql-query-complexity](https://github.com/slicknode/graphql-query-complexity), công cụ cung cấp giải pháp dựa trên phân tích chi phí. Với library này, bạn có thể từ chối các query quá tốn kém để thực thi.

#### Cài đặt

Để bắt đầu, hãy cài dependency cần thiết:

[[CODE:1]]

#### Bắt đầu

Khi đã cài đặt xong, hãy định nghĩa class `ComplexityPlugin`:

[[CODE:2]]

Để minh họa, độ phức tạp tối đa cho phép được đặt là `20`. Ví dụ ở trên dùng hai estimator, `fieldExtensionsEstimator` và `simpleEstimator`:

- `fieldExtensionsEstimator`: lấy giá trị độ phức tạp được định nghĩa cho mỗi field trong schema của bạn (qua `extensions` của field)
- `simpleEstimator`: trả về một độ phức tạp cố định cho mỗi field (dùng làm fallback cho các field không có độ phức tạp được định nghĩa)

> info **Hint** Nhớ thêm class này vào mảng `providers` của một module.

#### Độ phức tạp ở cấp field

Khi đã có plugin này, bạn có thể định nghĩa độ phức tạp của bất kỳ field nào bằng cách chỉ định thuộc tính `complexity` trong options object được truyền cho decorator `@Field()`:

[[CODE:3]]

Ngoài ra, bạn có thể định nghĩa một hàm estimator:

[[CODE:4]]

#### Độ phức tạp ở cấp Query/Mutation

Decorator `@Query()` và `@Mutation()` cũng nhận thuộc tính `complexity` trong options object của chúng:

[[CODE:5]]
