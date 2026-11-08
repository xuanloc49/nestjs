#### Read the current user

`@CurrentUser()` injects the user that `validate()` loaded:

[[CODE:36]]

`@CurrentUser('id')` injects a single property. `@CurrentSession()` injects what the provider considers the session: here, the stored session record.

> info **Hint** Optional: tell the package your user type once, and its types follow. Augment the `AuthenticationTypes` interface of `@nestjs/authentication` in a `declare module` block, with `user: User` (the tutorial keeps it in `src/auth/auth-types.ts`). From then on `@CurrentUser('key')` accepts only keys of `User` and is typed to return that property, and `AuthenticationContext.user` and `.session` are typed too. A `sessionExtra` key types `SessionRecord.extra`, what a session store reads along with each session (exported as `SessionExtra`, `unknown` without the key). It doesn't type the parameter itself: a parameter decorator has no say over the annotation, so `user: User` stays on the parameter. And it is one user type for the whole application, so an application with two kinds of principal keeps the annotations instead. The same interface takes `refreshTokens: false` for an application that [turns refresh tokens off](/security/authentication#issue-tokens-to-the-mobile-app).

[[CODE:37]]

Controllers aren't the only code that needs the user. Orders belong to the customer who placed them, and `OrdersService` reads that customer from `AuthenticationContext`, so the controller doesn't pass the user down:

[[CODE:38]]

[[CODE:39]]

[[CODE:40]]

`@Authenticate()` with `verifiedEmail: true` lets only customers with a verified address place orders. Anyone else signed in gets a 403 whose `error` is `email_unverified`, which tells the web app to ask the customer to open the [verification link](/security/authentication#verify-email-addresses), or to send it again. It's a 403 rather than a 401: signing in again wouldn't help. `GET /orders` has no such requirement. By default the guard reads `emailVerified` from the user that `validate()` loaded; your `EmailVerificationHandler` can override `isVerified(user)` if your user type stores it differently.

[[CODE:41]]

Add `OrdersModule` to the `imports` of `AppModule`:

[[CODE:42]]

`AuthenticationContext` is a singleton. It reads the current request's user from an `AsyncLocalStorage` that the module opens around each handler, so it's correct in anything the handler calls or awaits, however many requests run at the same time. `requireUser()` returns the user, or throws an `AuthenticationError`, which the module answers with a 401 on any transport. Outside a request, in a queue consumer or a cron job, `AuthenticationContext` is empty, and its `run()` method runs a function as a given user. It's also empty in middleware, guards and exception filters, which run outside the handler.

#### Issue tokens to the mobile app

The store's mobile app authenticates with bearer tokens rather than cookies. It sends a short-lived JWT access token in the `Authorization` header, and renews it with a long-lived refresh token.

Add a signing secret to `.env`. It must be at least 32 bytes. Without it, the application refuses to start, naming the option: `accessToken.key` is required.

[[CODE:43]]

The application both issues and verifies the access tokens, so describe them once, with the `accessToken` options. The key signs them, and the issuer, audience and lifetime go into every token and are checked on every request:

[[CODE:44]]

With a secret as the key, tokens are signed with HS256. The second credential provider verifies them. `JwtBearerProvider` reads the `Authorization` header, checks the signature against the `accessToken` key, and `exp`, `iss` and `aud`, and passes the verified claims to your `validate()`:

[[CODE:45]]

> info **Hint** HS256 with a shared secret suits an API that both issues and verifies its tokens. If other services verify them too, make the `accessToken` key an ES256 private key: `JwtAuth` then verifies with its public half, and so can they. To accept tokens from another issuer instead, pass `super()` its `jwks` URL, which must be https (plain http only on localhost), or its public `key`, with `issuer` and `audience`: both are required, because an identity provider signs every client's tokens with the same keys. For tokens without an audience, pass `audience: false` and check the claim that names your client in `validate()`. Add `clockTolerance: '30s'` for another issuer's clock. Keys are PEM text or a `KeyObject`; import a JWK with `createPublicKey()` from `node:crypto`, passing the JWK as `key` and `'jwk'` as `format`. An empty `key` or `jwks`, such as an unset environment variable, fails at startup instead of falling back to the `accessToken` options. A service that only verifies tokens can leave `accessToken` out entirely and give `super()` what it verifies with: the shared `key`, or the `jwks` with `issuer` and `audience`.

Provide it in `AuthModule`:

[[CODE:46]]

For each request, the guard asks the providers in ascending `order`, and the first one that returns a user wins. `SessionAuth` registered with the default order, `0`, and `JwtAuth` asked for `1`, so a request with a session cookie is signed in by `SessionAuth`, and a request with a bearer token, which has no cookie, gets `null` from `SessionAuth` and is handled by `JwtAuth`. The order is given at registration rather than left to the order in which Nest constructs the providers: that one follows the module graph, and changes when a provider moves to another module or an import is added. Two providers asking for the same order fail at startup, naming both. A request with neither gets a 401 with `missing_credentials` as its `errorCode`; its `WWW-Authenticate` header lists what the providers accept: `Bearer realm="store"`. A token that fails verification gets a 401 that says why, as RFC 6750 describes, for example `error="invalid_token", error_description="token expired"`. That tells the mobile app to refresh.

Now the endpoints that issue tokens:

[[CODE:47]]

`TokenService.issue()` signs an access token with the `accessToken` options, starts a refresh token, and returns both, with `expiresIn`, the access token's lifetime in seconds. Refresh tokens are opaque, and stored as hashes. Each one works once: `refresh()` spends it and returns its successor, with a new access token. The successors of one sign-in form a family. If a spent token comes back, two parties hold it, a thief and the app, so the service revokes the whole family and both have to sign in again. A refresh token that is unknown, expired or reused throws `RefreshTokenError`, an `AuthenticationError`, which the module answers with a 401, so `refresh` needs no error handling of its own.

The `amr` claim records how the user signed in, and [two-factor authentication](/security/authentication#add-two-factor-authentication) relies on it. `issue()` stores the `claims` with the refresh-token family, and `refresh()` puts them into every access token it mints, so refreshed tokens describe the same sign-in. Keep facts that can change, such as roles, out of `claims`: they would stay in the tokens for as long as the family lives. `validate()` loads the current user on every request instead.

A service that signs short-lived access tokens and has its clients sign in again can turn refresh tokens off. With `refreshToken` set to `false`, `issue()` returns `accessToken` and `expiresIn` alone, and stores nothing, so the application needs no `RefreshTokenStore`. The token endpoint's response has no refresh token: clients sign in again when the access token expires. `refresh()` and `revoke()` throw, saying refresh tokens are disabled, and `revokeAll()` does nothing. The second factor and the `amr` claim work as before. Declare `refreshTokens: false` on `AuthenticationTypes` too, so `issue()` is typed to return an `AccessTokenResult` rather than a `TokenPair`:

[[CODE:48]]

[[CODE:49]]

The option is what runs; the declaration only tells the compiler. An application that sets the option without the declaration gets no refresh token at run time, typed as a string, and `refresh()` throws on it. `refreshToken` set to `false` without `accessToken` changes nothing, and logs a warning at startup.

Register the controller:

[[CODE:50]]

#### Add two-factor authentication

Customers can protect their accounts with an authenticator app (time-based one-time passwords, or TOTP). Configure `mfa` in `AppModule`:

[[CODE:51]]

The server has to read a TOTP secret back to check codes, so, unlike a password, it can't be hashed. `MfaService` encrypts each secret with AES-256-GCM before it reaches storage, bound to its user, and decrypts it only to verify a code. Anyone holding a copy of your database, but not the key, can't generate codes. The key is required: configuring `mfa` without `encryption` throws at startup. (`encryption: false` stores plaintext on purpose, for tests.) A secret shorter than 128 bits never verifies: `enroll()` makes 160, but secrets imported from another system may be shorter, and their users enroll again.

Add the key to `.env`. A string key must be at least 32 characters of random data:

[[CODE:52]]

> info **Hint** To rotate the key, put a new one first in `keys` and keep the old one after it. The first key encrypts, every listed key decrypts, and secrets are re-encrypted with the new key as they're used. Remove the old key once nothing uses it. Keys need no names: each encrypted secret records an id derived from its key.

Two-factor authentication is off unless `mfa` is configured. Without it, `MfaService.isEnrolled()` answers `false` without reading the store, so sign-ins never ask for a code, and every other `MfaService` method throws `MFA is not configured` before touching storage. Removing `mfa` from the options turns two-factor authentication off for every customer, including those who already enrolled an authenticator.

The MFA endpoints enroll an authenticator, confirm it, and complete a sign-in:

[[CODE:53]]

- `enroll()` stores a new, unconfirmed secret, and returns it with an `otpauth://` URI that the web app shows as a QR code. Once an authenticator is confirmed, `enroll()` refuses to overwrite it and throws `MfaAlreadyEnrolledError`, which the module answers with a 409, `Authenticator already enrolled`. Overwriting it would switch two-factor authentication off until the new one was confirmed.
- `replace` handles a new phone. `enroll()` with `replace: true` stages a second secret, and the current authenticator keeps working until `confirm()` receives a code from the new one. `@Authenticate()` with `mfa: true` makes the route require a verified second factor, so a stolen password alone can't swap in someone else's authenticator.
- `SignInService.confirmMfa()` activates the authenticator once it produces a valid code, so a mistyped secret can't lock anyone out. That code also proves this browser has the authenticator, so the session becomes verified, under a new cookie: the customer can use the routes that require a second factor right away, without signing in again. A confirmation sent with a bearer token, which has no session, only activates the authenticator. The ten recovery codes the route returns are shown only this once, and stored under a slow hash salted with the customer's id, so a copy of the database doesn't reveal them.
- Once an authenticator is confirmed, `SignInService.signIn()` creates **pending** sessions for that user. A pending session isn't signed in anywhere: routes that need a user answer with a 401 and `"errorCode": "mfa_required"`, which tells the web app to ask for a code. That's why `verify` is `@Public()`. `completeMfa()` reads the session from this browser's cookie, checks a code or a recovery code, and rotates the session to a new id with `mfa: 'verified'`, setting the new cookie. A pending session expires after 10 minutes (`mfa.pendingTtl`), not after the 14 days of `session.absoluteTtl`: a pending cookie is half a credential. Verifying the code gives the session its full lifetime.
- `completeMfa()` only acts on the session cookie. A request with a bearer token and no cookie gets a 401.
- Codes are accepted 30 seconds either side of now, and each code works once. After 5 wrong codes in 15 minutes, the account refuses every code, right ones included, until the window passes. Each attempt is counted before it's checked, so sending guesses in parallel doesn't get around the limit.

A verified second factor can also be required for individual routes, which is called step-up authentication. The store requires it to change the email address, since that's how an account is recovered. The new address arrives in the `EmailDto` of [Reset forgotten passwords](/security/authentication#reset-forgotten-passwords). Add the route, with `@Authenticate()`:

[[CODE:54]]

With the Zod schema:

[[CODE:55]]

Every route already requires a signed-in user; `@Authenticate()` adjusts how. With `mfa: true`, a cookie session passes once it's verified. A customer who hasn't enrolled an authenticator can't pass it, so the web app asks them to enroll first.

The new address is unverified, so the route sends a verification link to it, and the customer can't place orders until they use it. The links sent to the old address stop working: they verify only the address they were sent to.

The mobile app must not become a way around the second factor, and it can't be: like `signIn()`, `TokenService.issue()` gives a customer with a confirmed authenticator no tokens without a code. It answers 401 with `"errorCode": "mfa_required"`, which tells the app to ask for one. The app then sends the password again, with the code. Add the code to the body:

[[CODE:56]]

[[CODE:57]]

And pass it on as the `secondFactor`:

[[CODE:58]]

[[CODE:59]]

A request without a code isn't counted as a failed attempt, so the app can find out whether it needs one. A verified code adds `mfa` to the `amr` claim. `JwtBearerProvider` treats a token whose `amr` contains `mfa`, `otp` or `hwk` as verified, so it passes `mfa: true` routes. Refreshed tokens carry the same `amr` as the sign-in that started their family, so a mobile app that signed in with a code stays verified until its refresh tokens expire or are revoked. `issue()` never takes those three values from your own `claims`: it drops them, with a warning in the log, and adds `mfa` only once it has verified a code, so an application can't mint a verified token by accident.

Register the controller:

[[CODE:60]]

##### Turn off two-factor authentication

`MfaService.disable()` removes the customer's authenticator and their recovery codes, and emits `mfa-disabled`. Add a route to `MfaController`, with `SessionService` and `TokenService` injected into its constructor:

[[CODE:61]]

- `@Authenticate()` with `mfa: true` is the minimum: without it, a stolen password alone could turn the second factor off. An API key never passes it. It doesn't prove the customer is at the keyboard now, though: a session stays verified for its whole lifetime. So the route asks for a code as well. `verifyTotp()` resolves `false` for a wrong code, counts toward the same lockout as signing in, and each code works once.
- `disable()` deletes every recovery code along with the authenticator, and drops a replacement staged by `replace` that was never confirmed. Enrolling again starts from scratch, with a new batch of recovery codes.
- `disable()` leaves sessions and tokens alone. The customer's other verified sessions would keep passing `mfa: true` routes, and so would their refresh-token families, whose `amr` keeps `mfa` on every refresh. The route ends them, keeping this browser's session. Access tokens already issued stay valid until they expire. Sent with a bearer token, the request has no session id to keep: every session ends, and `TokenService.revokeAll()` signs that client out too.
- A session still waiting for its second factor can't complete it, since there's no authenticator left to check a code against. `revokeAll()` ends it with the others.
- A customer whose enrollment was never confirmed has no verified session, so this route refuses them. To cancel such an enrollment, call `disable()` from a route without it while `isEnrolled()` is `false`, or call `enroll()` again.
