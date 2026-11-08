#### Làm việc với RxJS

Để kết hợp một request với các operator của RxJS, hãy bọc nó trong một Observable. `defer()` bắt đầu request khi Observable được subscribe, còn `from()` bắt đầu ngay lập tức:

[[CODE:26]]

Cả hai đều không hủy request khi unsubscribe. Khi bạn cần điều đó, ví dụ với `switchMap()`, hãy nối việc unsubscribe với một `AbortController`:

[[CODE:27]]

#### Chuyển từ `@nestjs/axios`

Package `@nestjs/axios` vẫn có sẵn, và cả hai package có thể được cài song song trong lúc bạn chuyển đổi. Bảng sau ánh xạ các tính năng của nó sang `@nestjs/http-client`:

| `@nestjs/axios` | `@nestjs/http-client` |
| --- | --- |
| `HttpModule.register()` với `baseURL` | `HttpClientModule.register()` với `baseUrl` |
| `HttpModule.registerAsync()` | `HttpClientModule.registerAsync()`, nhận thêm cả `name` |
| `HttpModuleOptionsFactory` với `createHttpOptions()` | `HttpClientOptionsFactory` với `createHttpClientOptions()` |
| `extraProviders` trong `registerAsync()` | Một module export các provider, truyền vào `imports` |
| Mỗi module import có một `HttpService` | Client có tên, inject bằng `@InjectHttpClient(name)` |
| Các method của `HttpService`, trả về Observable | Các method của `HttpClient`, trả về Promise |
| `firstValueFrom(this.httpService.get(url))` | `await this.http.get(url)` |
| `post(url, data)` | `post(url, options)`, với dữ liệu nằm trong `json` (hoặc `body`) |
| `params` trong config của request | `query`. Mảng sẽ lặp lại key, trong khi Axios viết `key[]=`. Trong `@nestjs/http-client`, `params` điền vào các segment `:name` của path, và throw với key không khớp segment nào. |
| `response.headers['etag']` | `response.headers.get('etag')` |
| `AxiosError` với `error.response?.status` | `HttpResponseError` với `error.status` và `error.body` |
| `error.code === 'ECONNABORTED'` | `HttpTimeoutError` |
| `validateStatus: () => true` | `throwOnHttpError: false` |
| `axiosRef` (instance Axios) | Không có instance bên dưới. Hãy dùng tùy chọn của client, hoặc truyền một hàm tùy chỉnh làm `fetch`. |
| `axiosRef.interceptors.request.use()` và `response.use()` | `interceptors`, một hàm duy nhất cho cả request lẫn response |
| `httpsAgent` hoặc `proxy` | `dispatcher`, một `Agent` hoặc `ProxyAgent` của undici |
| `maxRedirects: 0` | `redirect: 'manual'` |
| Không có retry, trừ khi bạn thêm `axios-retry` | Retry bật mặc định cho các method idempotent. `retry: false` khôi phục hành vi của Axios. |
| `timeout` cho toàn bộ request | `timeout` cho mỗi lần thử, có thể viết dạng chuỗi như `'5s'` |
| `onUploadProgress`, `onDownloadProgress` | Không có tương đương. Hãy tự đếm byte của một stream. |
