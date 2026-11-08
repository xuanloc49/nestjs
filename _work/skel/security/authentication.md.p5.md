#### Production checklist

- **Register a store for everything the module keeps**, as in [Keep sessions and tokens in your database](/security/authentication#keep-sessions-and-tokens-in-your-database), and apply its tables through your migrations. Every instance of the application uses them, so a restart signs nobody out. The module refuses to start while a store that a configured feature uses isn't registered, but only when `NODE_ENV` is `production`: set it, or a deployment that forgets it runs in memory with nothing but a startup log line to say so. Run the package's contract tests against your store with `concurrent: true` on PostgreSQL: they fail a store that reads and then writes where one conditional statement is needed.
- **Configure the same features in every application that shares the user database.** Each one decides from its own options whether a sign-in asks for a second factor and whether signing out everywhere ends refresh tokens. If any application that signs users in configures `mfa`, every one of them must, or a customer who enrolled through one signs in to another with a password alone. Likewise configure `accessToken`, with refresh tokens on, in each of them if a sign-out everywhere or a password reset in one should also sign out the token clients of the others.
- **Send email through a real provider.** Set `SMTP_URL`, or pass another transport. `LogMailTransport` writes every link to the log, where anyone who reads the logs could sign in as the customer.
- **Serve the application over HTTPS**, since the session cookie is `Secure`. If the web app runs on another origin than the API, list it in `session.trustedOrigins`, or its sign-ins and magic-link requests are refused, and its `POST` requests and WebSocket connections are anonymous. Behind a proxy that rewrites `Host`, list the public origin there too. Leave `cookie.secure` on: a `SameSite=None` cookie without it fails at startup, since browsers would drop it.
- **Call `app.enableCsrfProtection()` on Nest 12.1 or later**, with the same `trustedOrigins`. It refuses cross-origin writes to every route, not only those that use the session cookie.
- **Keep secrets in a secret manager**: the JWT secret, the TOTP encryption keys, the Google client secret and the SMTP credentials. Rotate the TOTP keys as described in [Add two-factor authentication](/security/authentication#add-two-factor-authentication).
- **Build the verification and reset pages to POST the token**, and serve them from `APP_URL`. Email scanners follow the links with GET requests; a page that used the token on load would let them spend it.
- **Keep `forgot` from revealing anything.** Answer it the same way whatever happens, as the [`forgot` route](/security/authentication#reset-forgotten-passwords) does, and don't `await` `request()`. Sign-up still answers 409 for an address that has an account; if that matters to you, answer sign-up the same way too, and email the owner instead.
- **Register the production redirect URI** with Google, and set `APP_URL` to the public origin of the application.
- **Size the servers for scrypt.** Each hash at the default cost takes 128 MiB, on the libuv threadpool (four threads unless you set `UV_THREADPOOL_SIZE`). Sign-in bursts queue behind each other; the throttler bounds them.
- **Use shared storage for the throttler**, such as Redis. Its default storage counts in each process's memory, so every instance counts on its own and a restart or deploy resets the counts. Enable `trust proxy` behind a proxy. For password guessing spread across many IP addresses, add a third throttler definition whose tracker is the email alone. Give it a limit well above what a customer mistypes in a day, and skip it on routes other than sign-in and token issuing: anyone who knows the address can use it up, and keep the customer from signing in with a password until it resets.
- **Rotate sessions on privilege changes** with `SignInService.rotateSession()`. After a password change made while signed in, or when a customer turns two-factor authentication on or off, also end their other sessions and refresh tokens: `SessionService.revokeAll()` with the current session as `except`, and `TokenService.revokeAll()`. Whoever knew the old password may still be signed in. A [password reset](/security/authentication#reset-forgotten-passwords) does this for you.
- **Handle API keys as secrets.** The table keeps only their hashes, and a key is shown once, when it's created: a leaked database gives nobody a key, and a lost key is revoked and replaced, never shown again. Keys expire after a year, so remind their owners to create the next one while the old one still works. Add the `cat_` pattern to your secret scanner (GitHub secret scanning takes custom patterns) to find keys committed to repositories, and revoke them. Requests made with a key emit no events: log the `keyId` from `@CurrentSession()` where you need to know which key did what. A password reset or a sign-out everywhere leaves keys alone: revoke them on those events if they should cut keys off too.
- **Keep an audit trail.** `AuthenticationEvents` publishes every sign-in and sign-out, second-factor change, reused refresh token, password reset and email verification, on its `events$` stream and on `node:diagnostics_channel`. Store them where your security team can search them. Alert on repeated `mfa-failed` events with `locked: true` (someone who has the password is guessing codes), and on many `password-reset-requested` events without a `userId` from one source (someone is probing for accounts), and on `session-touch-failed` events, which mean the session store is refusing writes.
- **Import `AuthenticationModule` before `AuthorizationModule`** if you add `@nestjs/authorization`. Global guards run in import order, and authorization needs the user that authentication sets. The other order fails at startup. `@nestjs/authorization` denies a handler that declares no check, and counts `@Public()` as one: a public route needs no `@Can.Anyone()`.

#### The store contract

The tutorial [wrote the authentication store with Drizzle](/security/authentication#keep-sessions-and-tokens-in-your-database). This section sums up what the six contracts ask of any store, for writing one with another ORM. Each method of the store interfaces gives its rule in its doc comment, with the race the rule prevents, and the package's contract tests check them.

**Registration.** A store is an ordinary singleton provider that registers itself in its constructor with `registerSource()` on the injectable `AuthenticationStorage`, by contract name: `sessions`, `refreshTokens`, `mfa`, `magicLinks`, `oidcStates` and `emailTokens`. Method names never repeat across the contracts, so one class can implement all six, or several classes can split them. The registry checks each store's shape at once, refuses a second store for a name unless it passes `replace: true`, and locks when `AuthenticationModule` initializes, logging where each kind of state lives. A contract with no store uses its in-memory default, which loses everything on restart and isn't shared between instances.

**Production guard.** With `NODE_ENV=production`, startup fails while a contract that a configured feature uses has no store, naming each missing interface:

| Configured | Contracts |
| --- | --- |
| a `SessionCookieProvider` | `sessions` |
| `accessToken`, with refresh tokens on | `refreshTokens` |
| `accessToken`, with `refreshToken` set to `false` | none |
| `mfa` | `mfa` |
| `magicLink` | `sessions`, `magicLinks` |
| `oidc` | `sessions`, `oidcStates` |
| `passwordReset` | `sessions`, `emailTokens` |
| `emailVerification` | `emailTokens` |

Two-factor authentication is off without `mfa`: sign-ins don't read the `mfa` contract. Refresh tokens exist only with `accessToken`, so without it, or with `refreshToken` set to `false`, signing out everywhere and resetting a password end sessions alone. A contract that none of your configured features uses fails at its first read instead of running in memory. `allowInMemoryStorage: true` in the module options accepts the in-memory stores anyway, but then every restart or deploy signs everyone out and forgets enrolled authenticators, and instances don't share any of it.

**The methods that must be atomic.** Whatever decides that something works only once is one conditional statement, never a read followed by a write. The other methods are plain reads, inserts and deletes. None takes your transaction: authentication state is written on its own, never as part of a business transaction.

| Contract | Method | Must be | Why |
| --- | --- | --- | --- |
| `SessionStore` | `touchSession()` | a conditional `UPDATE` of an existing row, moving `lastActiveAt` forward only | a request writing the session back after a sign-out would bring it back |
| `SessionStore` | `deleteSession()` | a `DELETE` that resolves whether it deleted the row, from its row count | of two rotations of one session, or a rotation and a sign-out, only one may win |
| `RefreshTokenStore` | `markRefreshTokenUsed()` | an `UPDATE ... WHERE used_at IS NULL`, counting rows | a thief and the owner refreshing at once must not both win |
| `MfaStore` | `saveTotp()` | an upsert that keeps the larger `lastUsedStep` | saving the record must not reopen a step just claimed |
| `MfaStore` | `claimTotpStep()`, `consumeRecoveryCode()` | a conditional `UPDATE`, a `DELETE`, counting rows | a replayed code must fail |
| `MfaStore` | `recordMfaFailure()` | an insert, then a count, each committed on its own | a burst of parallel guesses must not all see a low count |
| `MfaStore` | `saveRecoveryCodes()` | one transaction: delete, then insert | a reader must never see half a batch |
| `MagicLinkStore`, `OidcStateStore`, `EmailTokenStore` | `consumeMagicLink()`, `consumeOidcState()`, `consumeEmailToken()` | a `DELETE ... RETURNING` | one link must not sign in two browsers, or set two passwords |

A family of refresh tokens counts as revoked when any of its tokens is, so a successor saved after the revocation is revoked too. And the pending entries (magic links, OIDC logins, email tokens) stay bounded: each save deletes what has expired and, past a cap, what expires first.

`touchSession()` is best-effort: when it fails, the request goes on with the session as read, and a `session-touch-failed` event reports it. `getSession()` may set `extra` to what the same query read with the session, typically its user, for `SessionCookieProvider.validate()`. `createSession()` never receives it, and `listUserSessions()` doesn't set it.

**With Prisma.** The tutorial has the store with Drizzle and with TypeORM, on the same tables. A Prisma store follows the same rules:

- **Conditional updates and deletes** (`touchSession()`, `deleteSession()`, `markRefreshTokenUsed()`, `claimTotpStep()`, `consumeRecoveryCode()`) are `updateMany()` or `deleteMany()` with the condition in `where`, and their `count`: `deleteSession()` resolves `count > 0`. Never `upsert()` for `touchSession()`: it can write back a session that was just deleted.
- **`saveTotp()`** needs `GREATEST(..., excluded.last_used_step)` in its upsert. Prisma's upsert API doesn't take an expression from the conflicting row, so it is raw SQL, with `$executeRaw`.
- **The `consume` methods** are `delete()` with every condition in `where` (the id and, for `consumeEmailToken()`, the purpose), which throws `P2025` when nothing matched: turn that into `undefined`.
- **`recordMfaFailure()`** is two statements on their own: a `create()`, then a `count()`. Not `prisma.$transaction([create, count])`, which runs the two in one transaction that commits after the count.
- **`saveRecoveryCodes()`** is the one method that needs a transaction: `$transaction()`, whose array form fits here.

**Test it** with the suite from `@nestjs/authentication/testing`, as the tutorial does. `authenticationStoreContract()` returns cases for any test runner, for the contracts your factory returns. `concurrent: true` adds the races: parallel refreshes of one token, parallel uses of one code or link, bursts of failed codes, a sign-out racing a request, parallel deletes of one session, and a rotation racing a sign-out or another rotation. Run it against PostgreSQL with a connection pool, where a store that reads and then writes fails them. `maxPending` checks the cap on pending entries, with a small cap configured for the test. The suite ignores `extra` when it compares what `getSession()` returns, so a store that joins the user passes.
