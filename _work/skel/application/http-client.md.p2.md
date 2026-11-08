#### Working with RxJS

To compose a request with RxJS operators, wrap it in an Observable. `defer()` starts the request when the Observable is subscribed to, while `from()` starts it immediately:

[[CODE:26]]

Neither one cancels the request on unsubscribe. When you need that, for example with `switchMap()`, connect unsubscription to an `AbortController`:

[[CODE:27]]

#### Migrating from `@nestjs/axios`

The `@nestjs/axios` package remains available, and both packages can be installed side by side while you migrate. The following table maps its features to `@nestjs/http-client`:

| `@nestjs/axios` | `@nestjs/http-client` |
| --- | --- |
| `HttpModule.register()` with `baseURL` | `HttpClientModule.register()` with `baseUrl` |
| `HttpModule.registerAsync()` | `HttpClientModule.registerAsync()`, which also takes a `name` |
| `HttpModuleOptionsFactory` with `createHttpOptions()` | `HttpClientOptionsFactory` with `createHttpClientOptions()` |
| `extraProviders` in `registerAsync()` | A module that exports the providers, passed in `imports` |
| One `HttpService` per importing module | Named clients, injected with `@InjectHttpClient(name)` |
| `HttpService` methods, which return Observables | `HttpClient` methods, which return Promises |
| `firstValueFrom(this.httpService.get(url))` | `await this.http.get(url)` |
| `post(url, data)` | `post(url, options)`, with the data in `json` (or `body`) |
| `params` in the request config | `query`. Arrays repeat the key, where Axios writes `key[]=`. In `@nestjs/http-client`, `params` fills `:name` path segments, and throws for a key that matches none. |
| `response.headers['etag']` | `response.headers.get('etag')` |
| `AxiosError` with `error.response?.status` | `HttpResponseError` with `error.status` and `error.body` |
| `error.code === 'ECONNABORTED'` | `HttpTimeoutError` |
| `validateStatus: () => true` | `throwOnHttpError: false` |
| `axiosRef` (the Axios instance) | No underlying instance. Use the client's options, or pass a custom function as `fetch`. |
| `axiosRef.interceptors.request.use()` and `response.use()` | `interceptors`, with one function for both the request and the response |
| `httpsAgent` or `proxy` | `dispatcher`, an undici `Agent` or `ProxyAgent` |
| `maxRedirects: 0` | `redirect: 'manual'` |
| No retries, unless you add `axios-retry` | Retries on by default for idempotent methods. `retry: false` restores the Axios behavior. |
| `timeout` for the whole request | `timeout` per attempt, also as a string such as `'5s'` |
| `onUploadProgress`, `onDownloadProgress` | No equivalent. Count the bytes of a stream instead. |
