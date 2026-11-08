### Bảo mật

Để định nghĩa những cơ chế bảo mật mà một operation cụ thể dùng, hãy áp dụng decorator `@ApiSecurity()`:

```typescript
@ApiSecurity('basic')
@Controller('cats')
export class CatsController {}
```

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

```typescript
const options = new DocumentBuilder().addSecurity('basic', {
  type: 'http',
  scheme: 'basic',
});
```

Các kỹ thuật xác thực phổ biến nhất (ví dụ `basic` và `bearer`) đã có sẵn, nên bạn không phải tự định nghĩa cơ chế bảo mật của chúng như ở trên.

#### Basic authentication

Để bật basic authentication, hãy dùng `@ApiBasicAuth()`:

```typescript
@ApiBasicAuth()
@Controller('cats')
export class CatsController {}
```

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

```typescript
const options = new DocumentBuilder().addBasicAuth();
```

#### Bearer authentication

Để bật bearer authentication, hãy dùng `@ApiBearerAuth()`:

```typescript
@ApiBearerAuth()
@Controller('cats')
export class CatsController {}
```

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

```typescript
const options = new DocumentBuilder().addBearerAuth();
```

#### Xác thực OAuth2 <a id="oauth2-authentication"></a>

Để bật OAuth2, hãy dùng `@ApiOAuth2()`:

```typescript
@ApiOAuth2(['pets:write'])
@Controller('cats')
export class CatsController {}
```

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

```typescript
const options = new DocumentBuilder().addOAuth2();
```

#### Xác thực bằng cookie <a id="cookie-authentication"></a>

Để bật xác thực bằng cookie, hãy dùng `@ApiCookieAuth()`:

```typescript
@ApiCookieAuth()
@Controller('cats')
export class CatsController {}
```

Trước khi chạy ứng dụng, hãy thêm định nghĩa bảo mật vào tài liệu cơ sở bằng `DocumentBuilder`:

```typescript
const options = new DocumentBuilder().addCookieAuth('optional-session-id');
```
