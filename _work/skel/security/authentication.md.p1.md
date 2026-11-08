### Authentication

`@nestjs/authentication` signs users in and tells the rest of your application who they are. It registers a global guard, gives you decorators and an injectable context to read the current user, and ships the parts every sign-in flow needs: server-side sessions, password hashing, email verification and password reset links, TOTP two-factor authentication, magic links, OpenID Connect, access and refresh tokens, and API keys. All of them are built on Node.js built-ins, and they keep their state in your database through a store you write against documented interfaces, with the package's tests to check it. You write what only your application knows: how to load a user, which routes are public, and the endpoints of your sign-in flows.

In this tutorial, you'll add sign-in to the API of an online store for cat food and supplies. By the end, it will:

- Sign customers in with a password, with Google, or with a link sent by email, and keep the web app signed in with a session cookie.
- Confirm customers' email addresses, and let them reset a forgotten password.
- Give the mobile app short-lived bearer tokens and rotating refresh tokens.
- Offer two-factor authentication with an authenticator app, and require it to change an account's email address.
- Let customers see where they are signed in, and sign out everywhere.
- Limit how fast anyone can guess passwords.
- Keep its sessions, tokens and pending links in PostgreSQL, through Drizzle (or TypeORM).
- Let partners' systems and customers' scripts call the API with keys that customers create and revoke.

These are the endpoints you'll build, and the section that adds each one:

| Endpoint | Section |
| --- | --- |
| `POST /auth/sign-up`, `POST /auth/sign-in` | [Add sign-up and sign-in](/security/authentication#add-sign-up-and-sign-in) |
| `POST /auth/email/verify`, `POST /auth/email/verification` | [Verify email addresses](/security/authentication#verify-email-addresses) |
| `POST /auth/password/forgot`, `POST /auth/password/reset` | [Reset forgotten passwords](/security/authentication#reset-forgotten-passwords) |
| `GET /me`, `GET /orders`, `POST /orders` | [Read the current user](/security/authentication#read-the-current-user) |
| `POST /auth/token`, `POST /auth/token/refresh` | [Issue tokens to the mobile app](/security/authentication#issue-tokens-to-the-mobile-app) |
| `POST /auth/mfa/enroll`, `POST /auth/mfa/replace`, `POST /auth/mfa/confirm`, `POST /auth/mfa/verify`, `PATCH /me/email` | [Add two-factor authentication](/security/authentication#add-two-factor-authentication) |
| `GET /auth/oidc/google/login`, `GET /auth/oidc/google/callback` | [Add "Sign in with Google"](/security/authentication#add-sign-in-with-google) |
| `POST /auth/magic-link`, `POST /auth/magic-link/consume` | [Add magic-link sign-in](/security/authentication#add-magic-link-sign-in) |
| `GET /auth/sessions`, `DELETE /auth/sessions/:id`, `POST /auth/sign-out`, `POST /auth/sign-out-everywhere`, `POST /auth/token/revoke` | [Let customers manage their sessions](/security/authentication#let-customers-manage-their-sessions) |
| `POST /auth/api-keys`, `GET /auth/api-keys`, `DELETE /auth/api-keys/:id` | [Issue API keys to partners](/security/authentication#issue-api-keys-to-partners) |

#### Installation

Install the package:

[[CODE:1]]

Request bodies are validated with whatever your application already uses. Every DTO on this page comes twice, as a class with decorators and as a Zod schema, so pick the style you have and skip the other listing.

The tutorial keeps users in memory, behind a `UsersRepository` class. Replace its method bodies with Prisma, Drizzle, TypeORM, or whatever your application uses; the rest of the code only sees plain `User` objects. The authentication state (sessions, tokens, authenticators, pending links) moves to PostgreSQL in [Keep sessions and tokens in your database](/security/authentication#keep-sessions-and-tokens-in-your-database).

Starting with email verification, the application reads settings and secrets from environment variables. Keep them in a `.env` file during development, and start the application with it:

[[CODE:2]]

#### Register the authentication module

The package never reads your users table. It asks your code for a user by id, and your code decides what a user is. Here's the store's user. `emailVerified` records whether the customer proved they own the address; email verification sets it, and placing orders, Google sign-in and magic links depend on it:

[[CODE:3]]

The repository keeps password hashes to itself. Everything it returns is a `User` without one, so a user can be returned from a route or written to a log without leaking the hash:

[[CODE:4]]

[[CODE:5]]

Next comes a **credential provider**. A provider looks at an incoming request and returns the user the request proves, or `null` when the request carries no credentials it understands. `SessionCookieProvider` reads the session cookie, loads the session, and passes it to your `validate()` method, which loads the user:

[[CODE:6]]

Providers are ordinary `@Injectable()` classes, so they inject whatever they need, and they register themselves: the constructor hands `this` to `AuthenticationRegistry`, the package's list of providers, which the guard consults. The base class receives `SessionService` through property injection, which is why the constructor lists only `UsersRepository` and the registry. Because `validate()` runs on every authenticated request, a deleted user loses access right away, not when the session expires. When the users live in the same database as the sessions, the store can read the user in the same query and hand it to `validate()` as `session.extra`, so a request costs one read instead of two; [Keep sessions and tokens in your database](/security/authentication#keep-sessions-and-tokens-in-your-database) shows how.

Provide it in a module of your own. `AuthModule` will hold everything this tutorial adds under `src/auth`:

[[CODE:7]]

Now register `AuthenticationModule` in the root module, next to `AuthModule`:

[[CODE:8]]

`forRoot()` takes values only: lifetimes, secrets, client ids, the pages your emails link to. No class goes in the options. The credential providers, the handlers that later sections add and the [database store](/security/authentication#keep-sessions-and-tokens-in-your-database) are providers of your own modules, and each registers itself from its constructor, so it lives next to whatever it injects, and the module's options stay plain data. Lifetimes are milliseconds, or strings such as `'15m'` and `'14d'`, up to 100 years. `@nestjs/jwt` counts seconds instead, so a numeric lifetime under a minute logs a warning at startup: `3600` is 3.6 seconds here, not an hour.

At startup, once every provider's constructor has run, the registry locks and logs the chain it will try:

[[CODE:9]]

The module also registers a global guard. From now on, **every route requires a signed-in user** and answers `401 Unauthorized` to anyone else. If your application already has routes that must stay open, such as a health check or the product catalog, mark them with `@Public()`, which the next section introduces.

> info **Hint** Sessions are stored in memory until a provider registers a store, and with `NODE_ENV` set to `production` the module refuses to start that way. A [later section](/security/authentication#keep-sessions-and-tokens-in-your-database) moves them to your database.

#### Add sign-up and sign-in

Validate the request bodies first. Sign-up enforces a minimum password length; sign-in doesn't, so that a password set under an older rule still works:

[[CODE:10]]

The same rules as Zod schemas, whose inferred types replace the classes. Nest 12.1 validates any [Standard Schema](https://standardschema.dev/) object, from Zod, Valibot or ArkType, through `StandardSchemaValidationPipe`:

[[CODE:11]]

`PasswordHasher` hashes passwords with scrypt (`crypto.scrypt`, on the libuv threadpool, so it doesn't block the event loop), using OWASP's recommended parameters by default. A service wraps the two things the controller needs:

[[CODE:12]]

- `verify()` with no stored hash checks the password against a dummy hash. An unknown email and a wrong password take the same time and produce the same answer, so neither reveals which emails have accounts.
- Passwords are hashed with scrypt from `node:crypto`, at the parameters OWASP recommends (N=2^17, r=8, p=1: about 128 MiB of memory per hash), on the libuv thread pool. That's a memory-hard function, which bcrypt isn't, and it needs no native dependency. Every hash records the parameters it was made with (`$scrypt$ln=17,r=8,p=1$...`). When you raise the cost with the `password` option, `needsRehash()` tells you which stored hashes to upgrade, and the only moment you can do that is while the user signs in. Until then, `verify()` tops up the check of an older, cheaper hash to the work of the new parameters, so it still takes as long as an unknown email. Lowering the cost can't be hidden that way: a hash made with the costlier parameters takes longer to check until it's upgraded. The cost has a ceiling of 1 GiB of memory and 16 times the default work per hash, so with `r` at 8, `logN` stops at 20. Parameters beyond it fail at startup, and a stored hash made with them never verifies.
- `register()` leaves the address unverified. Typing an email into a sign-up form doesn't prove you own it.

The controller turns a verified password into a session:

[[CODE:13]]

`@Public()` on the class skips authentication for both routes. `SignInService.signIn()` is the one place where a first factor becomes a session: this step calls it after a password, and the Google and magic-link steps go through it too. It creates the session and sets the session cookie on the response itself, on Express and Fastify alike, so the controller needs neither `@Req()` nor `@Res()`:

- The cookie, `__Host-sid`, holds a random 256-bit token and is `HttpOnly`, `Secure` and `SameSite=Lax`. The `__Host-` prefix tells browsers to accept it only from this host, so a page on another subdomain can't plant a session cookie of its own. Only the token's SHA-256 hash is stored, so a leaked session store can't be replayed as cookies.
- It deletes the session this browser had before, which defends against session fixation.
- It refuses, with a 403, a sign-in posted from another website's page. Otherwise that page could sign the customer's browser in to an account of the attacker's choosing (login CSRF).
- `method` is recorded in the audit trail, which the section on [managing sessions](/security/authentication#let-customers-manage-their-sessions) mentions.
- `mfaRequired` stays `false` until you [add a second factor](/security/authentication#add-two-factor-authentication).

With the Zod schemas, the body parameters declare their schema instead of a class:

[[CODE:14]]

Register the controller in `AuthModule`:

[[CODE:15]]

> info **Hint** The DTOs are enforced only by a validation pipe: bind `ValidationPipe` globally, as an `APP_PIPE` provider of `AppModule` or with `useGlobalPipes()` in `main.ts`. With the Zod schemas, bind `StandardSchemaValidationPipe` the same way instead: an application uses one or the other. The [validation](/application/validation) page has the options of each.

> info **Hint** Chrome, Firefox and curl treat `http://localhost` as a secure origin and accept `Secure` and `__Host-` cookies from it, so you don't need HTTPS during development. On another host over plain HTTP, such as a LAN address, set `cookie.secure` to `false` in the `session` options there; the cookie is then named `sid`.

The session cookie is also protected against cross-site request forgery. Besides `SameSite=Lax`, the module ignores the cookie on `POST`, `PUT`, `PATCH` and `DELETE` requests, and on WebSocket handshakes, that come from another origin, judged by the `Sec-Fetch-Site`, `Origin` and `Host` headers, so those requests are anonymous. Clients that send neither `Sec-Fetch-Site` nor `Origin`, such as curl and your mobile app, are unaffected. If your web app runs on another origin than the API, list it in `session.trustedOrigins`.

On Nest 12.1 or later, also call `app.enableCsrfProtection()` in `main.ts`. It makes the same decision for every route, with a 403, including the public ones that have no session to protect yet. Pass it the same `trustedOrigins` as the `session` options.

#### Verify email addresses

Anyone can type any address into the sign-up form. Until the customer proves the address is theirs, by opening a link sent to it, the store treats it as unverified: it won't take orders whose receipts would go there, and it won't let a Google account or a magic link into that account, as later sections show. The package creates and checks the links. Your application sends them, with the mail library of your choice; the store uses `@nestjs/mail`:

[[CODE:16]]

From this step on, the application reads settings from environment variables. Add the application's public URL to `.env`. The links in the emails point to pages of the web app there:

[[CODE:17]]

> info **Hint** The tutorial reads `process.env` directly, to stay short. In an application, load the environment through [`@nestjs/config`](/application/configuration) with a validation schema, so a missing or malformed variable stops the application at startup rather than at the first request, and read the values from `ConfigService`.

Register `MailModule` in `AppModule`. Both modules now read environment variables, so `AuthenticationModule` switches to `forRootAsync()`: its factory runs at bootstrap, whereas the argument of `forRoot()` is evaluated when the file is imported, which was fine while every value was a literal. With `@nestjs/config`, add `inject: [ConfigService]` and read the values from the injected service instead. In development, `LogMailTransport` prints each email to the application's log, so you can follow the links; set `SMTP_URL` to send real email. `FileTemplateEngine` renders the bodies of the emails from HTML files in `src/mail/templates`, one per email:

[[CODE:18]]

The TypeScript compiler doesn't copy HTML files to `dist`: add the templates to the assets in `nest-cli.json`, as the [Mail](/application/mail#register-the-mail-module) tutorial shows; it covers the template syntax too.

The verification email is a template. The link goes between double braces, which escape it:

[[CODE:19]]

A mail class renders the email from the template, with the link as its context, and an `EmailVerificationHandler` connects the package to it: `send()` delivers a link, and `markVerified()` records a verified address in your users table. Like a credential provider, a handler registers itself, under the name of the feature it serves:

[[CODE:20]]

`markVerified()` marks only the address the link was sent to. If the customer has changed their address since, the link verifies nothing. The repository updates the row only while the address matches, which in SQL is one conditional update (`UPDATE users SET email_verified = true WHERE id = $1 AND email = $2`):

[[CODE:21]]

A feature has two halves: its handler, and its option. Provide the handler in `AuthModule`, and configure the page the links open. One half without the other fails at startup, with a message naming the missing one:

[[CODE:22]]

[[CODE:23]]

Send the link when a customer signs up:

[[CODE:24]]

Then add the endpoints. The link opens a page of the web app, which POSTs the token from its URL back to the API: email scanners and link previews follow links in emails with GET requests, and would use it up before the customer clicks.

[[CODE:25]]

- `EmailVerificationService.send()` stores the SHA-256 hash of a random 256-bit token, with the customer's id and the address, and passes the link to your handler. The token itself only exists in the email.
- A link works once, for 24 hours (`emailVerification.ttl`), and only for the address it was sent to. `verify()` returns `null` for an unknown, used or expired token, and for an address that has changed since, and the route answers 400.
- `resend` isn't `@Public()`: only a signed-in customer can ask for a new link, and only to their own address, so the route reveals nothing about other accounts.

Register the controller:

[[CODE:26]]

The package can also require a verified address on a route: `@Authenticate()` with `verifiedEmail: true` answers a signed-in customer whose address isn't verified with a 403. [Read the current user](/security/authentication#read-the-current-user) uses it for placing orders.

> info **Hint** `LogMailTransport` logs the text of each email at the `debug` level, links included, so never use it where logs are shipped. In production, set `SMTP_URL`, or pass another transport, such as `ResendTransport`. The [Mail](/application/mail) tutorial covers the options.

#### Reset forgotten passwords

A customer who forgot their password asks for a link, and chooses a new password on the page it opens. The email that sends the link is another template:

[[CODE:27]]

The package owns the tokens; a `PasswordResetHandler` finds accounts, sends the email, and stores the new password's hash:

[[CODE:28]]

`findUser()` returns the account's id, its stored address and its stored password hash, `null` for an account without a password. The link goes to that stored address, never to the one typed into the form: a lookup that ignores accents or dots, as MySQL's default collation does, would otherwise mail one customer's link to whoever typed a lookalike address. A link works only while the address and the hash are unchanged, so a password change, by any route, invalidates the links sent before it. Leaving the address or the hash out is an error, which the package logs instead of sending the link.

Enable password reset next to email verification, the handler in `AuthModule` and the page in the options:

[[CODE:29]]

[[CODE:30]]

One endpoint takes the address, the other the token and the new password, which follows the sign-up rules:

[[CODE:31]]

[[CODE:32]]

[[CODE:33]]

- `request()` returns before it looks the address up. Finding the account, storing the token and sending the email happen after the response, so a request for an address nobody registered gets the same 202, in the same time, as a customer's: the route can't tell anyone who has an account. That's why `forgot` doesn't `await` anything. A failure after the response, such as a mail server that is down, is logged.
- A link works once, for an hour (`passwordReset.ttl`), and only while the account still has the address and the password it had when the link was sent.
- `reset()` stores the new password's hash, invalidates the customer's other reset links, and ends every session of the account, and every refresh token once the application [issues them](/security/authentication#issue-tokens-to-the-mobile-app), so whoever knew the old password is signed out everywhere. [API keys](/security/authentication#issue-api-keys-to-partners) live in your own table and stay valid: to cut them off too, revoke them on the `password-reset` event. A password that `PasswordHasher` refuses, empty or over 4 KiB, gets `null` without spending the link, so the customer can try again. With `signIn: true`, it then signs the customer in on this browser through `SignInService`, so a customer with [two-factor authentication](/security/authentication#add-two-factor-authentication) still has to enter a code.
- The link proves the address too, so `reset()` marks it verified, through your `markVerified()`. That also rescues an account that someone else signed up for with the customer's address: the reset replaces the stranger's password and signs them out.

With the Zod schemas:

[[CODE:34]]

Register the controller:

[[CODE:35]]
