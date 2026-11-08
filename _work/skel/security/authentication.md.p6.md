#### Reference

##### Module options

`AuthenticationModule.forRoot()` takes these options, and the `forRootAsync()` factory returns them, except `isGlobal` and `globalGuard`, which stay at the top level. Lifetimes are milliseconds, or strings such as `'30s'`, `'15m'` and `'14d'`, up to 100 years; a longer one fails at startup. Every group that has a clock also takes `now`, a function returning epoch milliseconds, for tests.

| Option | Default | Description |
| --- | --- | --- |
| `isGlobal` | `true` | Register the module globally. |
| `globalGuard` | `true` | Register `AuthenticationGuard` as a global guard. With `false`, routes stay open until they use `@UseGuards(AuthenticationGuard)`. |
| `allowInMemoryStorage` | `false` | Start with `NODE_ENV=production` while a contract a feature uses has no store. See [Keep sessions and tokens in your database](/security/authentication#keep-sessions-and-tokens-in-your-database). |
| `session.cookieName` | `__Host-sid` | The session cookie; `sid` when `cookie` rules out the `__Host-` prefix. |
| `session.absoluteTtl` | `'7d'` | A session's maximum lifetime, however active it is. |
| `session.idleTtl` | `'1d'` | Idle timeout, extended by activity. `0` turns it off. |
| `session.touchInterval` | `'1m'` | How often activity is written to the store at most. Shorter than `idleTtl`, unless that is `0`: a longer one fails at startup, since active users would be signed out as idle. |
| `session.cookie` | `secure: true`, `sameSite: 'lax'`, `path: '/'` | Cookie attributes: `secure`, `sameSite`, `path`, `domain`. `HttpOnly` is always set. |
| `session.trustedOrigins` | none | Other origins whose pages may use the session cookie for writes and sign in. |
| `session.metadata` | none | A function of the sign-in request whose result is stored with each new session. See [Let customers manage their sessions](/security/authentication#let-customers-manage-their-sessions). |
| `password.logN` | `17` | Base-2 logarithm of the scrypt cost N, an integer from 10 to 22. `r` (default `8`, up to 32), `p` (`1`, up to 16), `keyLength` (`32`) and `saltLength` (`16`, both from 16 to 64) set the other parameters. A hash may take at most 1 GiB of memory (128·N·r bytes) and 16 times the default work (N·r·p), so with `r` at 8, `logN` stops at 20. |
| `accessToken.key` | required | HS256 secret of at least 32 bytes, or a private key for RS256, ES256 or EdDSA, as PEM text or a `KeyObject`. A JWK or a DER key fails at startup: import it with `createPrivateKey()`. See [Issue tokens to the mobile app](/security/authentication#issue-tokens-to-the-mobile-app). |
| `accessToken.alg` | from the key | Signing algorithm: HS256 for a secret, the key's own for a private key. |
| `accessToken.issuer`, `audience` | none | The `iss` and `aud` claims, written into and checked on every token. |
| `accessToken.ttl` | `'15m'` | Access token lifetime. |
| `accessToken.kid`, `type` | none, `JWT` | The `kid` and `typ` headers. |
| `refreshToken` | on with `accessToken` | `false` issues access tokens alone, with no refresh tokens and no `RefreshTokenStore`. See [Issue tokens to the mobile app](/security/authentication#issue-tokens-to-the-mobile-app). |
| `refreshToken.ttl` | `'30d'` | Lifetime of one refresh token. |
| `refreshToken.absoluteTtl` | `'90d'` | Maximum lifetime of a refresh-token family, however often it rotates. |
| `mfa.encryption` | required | `keys`, a list of AES-256-GCM keys, newest first, plus `migratePlaintext` (default `false`); or `false` to store secrets in plaintext. See [Add two-factor authentication](/security/authentication#add-two-factor-authentication). |
| `mfa.issuer` | none | The name authenticator apps show. |
| `mfa.window` | `1` | Accepted 30-second steps on either side of now, an integer from 0 to 10. |
| `mfa.maxAttempts` | `5` | Failed codes allowed per `lockoutWindow` before every code is refused, an integer of at least 1. |
| `mfa.lockoutWindow` | `'15m'` | The window failed codes are counted in. |
| `mfa.recoveryCodes` | `10` | Recovery codes per batch, an integer of at least 1. |
| `mfa.pendingTtl` | `'10m'` | How long a session may wait for its second factor. |
| `emailVerification.url` | required | The page verification links open. `ttl` defaults to `'24h'`. See [Verify email addresses](/security/authentication#verify-email-addresses). |
| `passwordReset.url` | required | The page reset links open. `ttl` defaults to `'1h'`. See [Reset forgotten passwords](/security/authentication#reset-forgotten-passwords). |
| `magicLink.url` | required | The page magic links open. `ttl` defaults to `'15m'`. See [Add magic-link sign-in](/security/authentication#add-magic-link-sign-in). |
| `magicLink.bindToBrowser` | `true` | Accept a link only in the browser that requested it. |
| `magicLink.cookie` | `secure: true` | Attributes of the `__Host-magic_link_tx` transaction cookie. |
| `oidc.callbackUrl` | required | The public callback URL, with `:provider` in place of the provider's name, or a function of the request that returns it. See [Add "Sign in with Google"](/security/authentication#add-sign-in-with-google). |
| `oidc.providers` | required | Provider configurations by name, such as `google()`, `github()` and `microsoft()`, which also takes the directory's `tenant` id, or a function of the name that returns one. See [Add "Sign in with Google"](/security/authentication#add-sign-in-with-google). |
| `oidc.redirectAfterLogin` | `/` | Where to land when the login had no `redirectTo`. |
| `oidc.transactionTtl` | `'10m'` | How long a login may take between the redirect and the callback. |
| `oidc.cookie` | `secure: true` | Attributes of the `__Host-oidc_tx` transaction cookie. |
| `oidc.discoveryTtl`, `clockTolerance` | `'1h'`, `'30s'` | How long a discovery document is trusted, and the leeway for ID token time claims. |

The `emailVerification`, `passwordReset`, `magicLink` and `oidc` features also need a registered handler of the same name; one without the other fails at startup. So does a value outside the ranges above, including the `NaN` that `Number()` makes of an environment variable that isn't set.

##### Route options

`@Authenticate()` takes these options, on a class or a method:

| Option | Description |
| --- | --- |
| `optional` | Let anonymous callers through, with `null` as the user. Bad credentials still get a 401. |
| `mfa` | Require a verified second factor: a verified session, or a JWT whose `amr` contains `mfa`, `otp` or `hwk`. API keys never satisfy it. See [Add two-factor authentication](/security/authentication#add-two-factor-authentication). |
| `verifiedEmail` | Require a verified email address, or answer 403 with `email_unverified`. See [Read the current user](/security/authentication#read-the-current-user). |
| `providers` | Only these provider classes, or their subclasses, may authenticate the route. |

##### API keys

`ApiKeyProvider` takes these options in `super()`. See [Issue API keys to partners](/security/authentication#issue-api-keys-to-partners).

| Option | Default | Description |
| --- | --- | --- |
| `prefix` | required | Starts every key, as in `cat_<id>_<secret>`: 1 to 16 lowercase letters and digits, starting with a letter. |
| `realm` | `api` | The realm in the `WWW-Authenticate` challenge. |

Your subclass implements `findKey(id)`, which returns the key's stored `hash`, its `user` and its `expiresAt`, or `null` for a key that doesn't exist, was revoked, or whose owner is gone. `generate()` returns a new key as `key`, shown once, with the `id` and `hash` to store. For a request made with a key, the session is the key's `keyId` and `expiresAt`, with `method` set to `api-key`.

##### Events

`AuthenticationEvents` publishes each event on its `events$` observable, and on the `nestjs:authentication:<type>` diagnostics channel, such as `nestjs:authentication:sign-in`.

| Type | Payload | When |
| --- | --- | --- |
| `sign-in` | `userId`, `sessionId` or `tokenFamilyId`, `method`, `mfa`, `metadata` | `SignInService.signIn()` or `TokenService.issue()` signed a user in |
| `sign-out` | `userId`, `sessionId`, `tokenFamilyId` or `everywhere` | A session, a refresh-token family, or all of them ended |
| `mfa-verified` | `userId`, `method` (`totp` or `recovery-code`) | A code was accepted |
| `mfa-failed` | `userId`, `method`, `failures`, `locked` | A code was refused, including during a lockout |
| `mfa-enabled` | `userId`, `replaced` | An authenticator was confirmed |
| `mfa-disabled` | `userId` | The authenticator and recovery codes were removed |
| `recovery-codes-generated` | `userId`, `count` | A new batch of recovery codes replaced the old one |
| `refresh-token-reused` | `userId`, `tokenFamilyId` | A spent refresh token came back, and its family was revoked |
| `password-reset-requested` | `email`, `userId` (absent for an unknown address) | Someone asked for a reset link |
| `password-reset` | `userId` | A reset link set a new password |
| `email-verified` | `userId`, `email` | A verification link was used |
| `magic-link-refused` | `reason` (`not-this-browser`, `unknown`, `expired` or `refused`), `email` | A magic link signed nobody in |
| `session-touch-failed` | `userId`, `sessionId`, `error` | `SessionStore.touchSession()` failed; the request went on, and the session's idle deadline didn't move |

##### Errors

`AuthenticationError` is the base class of the package's errors. It carries `status`, and optionally `code`, `details` and `challenge` (the `WWW-Authenticate` header). Thrown from a handler or anything it calls, it becomes Nest's own HTTP exception, GraphQL `UNAUTHENTICATED`, a `WsException` or an `RpcException`. Its `code` is Nest's `errorCode`. Over HTTP and GraphQL it is set on the exception, so an exception filter reads `exception.errorCode`, and Nest puts it in the body, or in `extensions.originalError` for GraphQL. The ws and rpc payloads carry the same `errorCode` key. A refusal with a message also sends the code as `error`, as it always has. `details`, a plain object, is sent as `details`, as is; nothing else of the error (`cause`, the stack) reaches the client. For example, `new AuthenticationError('Too many attempts', options)` with `too_many_attempts` as the `code` and `retryAfter: 30` in `details` answers:

[[CODE:136]]

| Error | Status | `errorCode` | `error` | When |
| --- | --- | --- | --- | --- |
| `AuthenticationError` | 401 | its `code`, if any | its `code`; else `Unauthorized` with a message, none without | Bad credentials, or `requireUser()` without a user (no message, no code) |
| `JwtError` | 401 | none | `Unauthorized` | A token is malformed, badly signed, expired, or for another issuer or audience |
| `RefreshTokenError` | 401 | none | `Unauthorized` | A refresh token is invalid, expired or reused; `reason` says which |
| `MagicLinkError` | 401 | `not_this_browser` | `not_this_browser` | A magic link was opened in another browser than the one that requested it, or after that browser requested five newer ones |
| `MfaAlreadyEnrolledError` | 409 | none | `Conflict` | `enroll()` without `replace: true` for a user with a confirmed authenticator |

When no provider recognises any credentials, the guard answers 401 with `missing_credentials`, and no `error`:

[[CODE:137]]

That covers a request without credentials, a stale or unknown session cookie (which counts as none, so optional routes keep working), and credentials that a route's `providers` doesn't accept. The guard and `TokenService.issue()` also answer 401 with `mfa_required` while a second factor is missing, and 403 with `email_unverified` on `verifiedEmail` routes, each as both `errorCode` and `error`. The OIDC routes answer 400 for a bad or forged callback, 401 when the provider's answer fails verification or a link flow has no signed-in session, 403 when the resolver refuses the account or a link flow is started from another site, 404 for a provider name that isn't configured, and 502 when the provider can't be reached or is misconfigured, such as an endpoint that isn't https or a key set that can't be loaded. `SignInService.signIn()` and `MagicLinkService.create()` answer 403 to a request posted from another origin.
