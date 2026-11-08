### Bảo mật

Để định nghĩa những cơ chế bảo mật mà một operation cụ thể dùng, hãy áp dụng decorator `@ApiSecurity()`:

[[CODE:1]]

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

[[CODE:2]]

Các kỹ thuật xác thực phổ biến nhất (ví dụ `basic` và `bearer`) đã có sẵn, nên bạn không phải tự định nghĩa cơ chế bảo mật của chúng như ở trên.

#### Basic authentication

Để bật basic authentication, hãy dùng `@ApiBasicAuth()`:

[[CODE:3]]

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

[[CODE:4]]

#### Bearer authentication

Để bật bearer authentication, hãy dùng `@ApiBearerAuth()`:

[[CODE:5]]

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

[[CODE:6]]

#### Xác thực OAuth2

Để bật OAuth2, hãy dùng `@ApiOAuth2()`:

[[CODE:7]]

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

[[CODE:8]]

#### Xác thực bằng cookie

Để bật xác thực bằng cookie, hãy dùng `@ApiCookieAuth()`:

[[CODE:9]]

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

[[CODE:10]]
