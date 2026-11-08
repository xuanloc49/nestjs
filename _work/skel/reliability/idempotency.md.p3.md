#### Reference

##### Module options

`IdempotencyModule.forRoot()` takes these options. `forRootAsync()` takes `isGlobal` and `imports` at the top level, next to `useFactory`, `useClass` or `useExisting`, and the factory returns the rest. Every option except `header`, `replayHeaders`, `encryption`, `allowInMemoryStorage` and `isGlobal` can also be set per class or handler in `@Idempotent()`, where it is merged field by field over the module's.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `required` | `boolean` | `false` | Rejects calls without a key with `IDEMPOTENCY_KEY_REQUIRED`. See [Make the payment endpoint idempotent](/reliability/idempotency#make-the-payment-endpoint-idempotent). |
| `scope` | function, object or `false` | none | The key namespace, such as the user id. An object has one function per context, under `http`, `graphql` and `rpc`. `false` shares one namespace on purpose. |
| `ttl` | `Duration` | `'24h'` | How long a completed result is replayed. See [Tune TTLs and failure handling](/reliability/idempotency#tune-ttls-and-failure-handling). |
| `lockTtl` | `Duration` | `'60s'` | How long an in-flight lock survives after renewals stop. The lock is renewed every `lockTtl / 3`. |
| `retryAfter` | `Duration` | `'1s'` | The wait sent with `IDEMPOTENCY_KEY_IN_USE`, in whole seconds, rounded up. |
| `keyFrom` | source, or one source per context | see below | Where the key comes from: `header`, `arg` (GraphQL), `payload` (microservices) or a function of the `ExecutionContext`. |
| `fingerprint` | `(payload, context) => unknown` | the whole payload | What a retry must repeat. The method and URL, GraphQL field or message pattern, and the scope always count. |
| `storeIf` | `(status, error) => boolean` | `status < 500` | Which outcomes are stored and replayed. Others release the key. |
| `header` | `string` | `'Idempotency-Key'` | The HTTP header, also read by GraphQL, and the transport header name for microservices. |
| `replayHeaders` | `string[]` | none | Response headers replayed in addition to `Location`, `Content-Type`, `Content-Language`, `Content-Location`, `ETag` and `Last-Modified`. `Set-Cookie` and headers the platform writes for every response are refused at startup. |
| `encryption` | an object with `keys` | off | AES-256-GCM encryption of stored records. `keys` lists 32-byte `Buffer`s or strings of at least 32 characters, newest first. See [Encrypt stored receipts](/reliability/idempotency#encrypt-stored-receipts). |
| `allowInMemoryStorage` | `boolean` | `false` | Lets a production app start without a registered store. |
| `isGlobal` | `boolean` | `true` | Registers the module globally. |

Every duration takes milliseconds or a string such as `'45s'`, `'48h'` or `'7d'`.

The key comes from these sources by default:

| Context | Default source |
| --- | --- |
| HTTP | The `Idempotency-Key` header (the `header` option) |
| GraphQL | The mutation's `idempotencyKey` argument, then the header |
| Microservices | The payload's `idempotencyKey` property, then the transport header named by `header` |

A key is 1 to 255 printable ASCII characters. A number in a payload counts as its digits.

##### Events

`IdempotencyEvents.events$` emits every event, and each is also published on a diagnostics channel. Every payload has `type`, `context` (`'http'`, `'graphql'` or `'rpc'`), `handler` (such as `OrdersController.pay`), `key` and, when there is one, `scope`.

| Type | Channel | Payload type | Other fields | When |
| --- | --- | --- | --- | --- |
| `replayed` | `nestjs:idempotency:replayed` | `IdempotencyReplayedEvent` | `status` | A retry got the stored result, or a duplicate event was skipped |
| `rejected` | `nestjs:idempotency:rejected` | `IdempotencyRejectedEvent` | `code`, `status` | A call was refused before its handler ran. There is no `key` for `IDEMPOTENCY_KEY_REQUIRED` and `IDEMPOTENCY_KEY_INVALID`. |
| `lock-lost` | `nestjs:idempotency:lock-lost` | `IdempotencyLockLostEvent` | `phase` (`'extend'`, `'complete'` or `'release'`) | The attempt's outcome isn't in the store, so a retry may run the handler again |

`IdempotencyEvent` is the union of the three payload types.

##### Errors

Rejections carry one of these codes, typed as `IdempotencyErrorCode`. Over HTTP, the code is in the response body. In GraphQL, it's in the field error's `extensions`, with `httpStatus` and, for a 409, `retryAfter`. On microservices, the `RpcException` payload has `status`, `code`, `statusCode`, `message` and, for a 409, `retryAfter`.

| Code | Status | Message | Cause |
| --- | --- | --- | --- |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | An idempotency key is required for this operation. | No key, with `required: true` |
| `IDEMPOTENCY_KEY_INVALID` | 400 | The idempotency key must be 1 to 255 printable ASCII characters. | A key that is too long, has other characters, or isn't a string or number |
| `IDEMPOTENCY_KEY_IN_USE` | 409, with `Retry-After` | A request with this idempotency key is still being processed. | The first call with the key is still running |
| `IDEMPOTENCY_KEY_REUSED` | 422 | This idempotency key was already used for a different request. | The same key with a different fingerprint |
| `IDEMPOTENCY_RECORD_UNREADABLE` | 500 | The stored result for this idempotency key could not be read. | The stored record fails to decrypt, for example because its key was removed |
