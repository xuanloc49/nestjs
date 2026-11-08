#### Keep sessions and tokens in your database

Everything the package stores has lived in memory so far: sessions, refresh tokens, authenticators and recovery codes, and pending links and logins. It's lost on restart, and a second instance of the API wouldn't see it. The package doesn't talk to your database itself. It describes what it stores as six interfaces, `SessionStore`, `RefreshTokenStore`, `MfaStore`, `MagicLinkStore`, `OidcStateStore` and `EmailTokenStore`, and your application implements them with the database access it already has, then registers the implementation.

This step shows that implementation twice, for the two ORMs the family's tutorials use: first with Drizzle, which is the tutorial's path, and then, under "With TypeORM" at the end of the step, the same store for an application whose ORM is TypeORM. Take one of the two.

The store uses PostgreSQL with Drizzle, through [`@nestjs/drizzle`](/data/drizzle), which this step assumes your application already has. `DrizzleModule` opens a `pg` pool from the database's URL and provides the Drizzle database, and it closes the pool when the application shuts down, after the package has finished the work it still had in flight (a reset link on its way out, for instance). Add the URL to `.env`, and register the module in `AppModule`:

[[CODE:89]]

[[CODE:90]]

Start with the tables. They're ordinary Drizzle tables in the application's schema, next to your own:

[[CODE:91]]

- Sessions, tokens and links are stored as SHA-256 hashes of the values in the cookies and emails, TOTP secrets arrive encrypted with your key (see [two-factor authentication](/security/authentication#add-two-factor-authentication)), and recovery codes arrive hashed with scrypt. Nothing in these tables can be replayed.
- `revoked` is on each refresh token rather than in a table of families: a family counts as revoked when any of its tokens is. That covers a token saved after the revocation, by a refresh that lost a race.

Generate the migration from the schema, and apply it:

[[CODE:92]]

Now the store. It's a provider like any other: it injects the Drizzle database, implements the six interfaces with Drizzle's query builder, and registers itself with the package's `AuthenticationStorage` from its constructor:

[[CODE:93]]

Add it to the providers of `AuthModule`, like the credential providers and the handlers. Registering in the constructor is all it takes: Nest creates the provider at startup, before the first request.

[[CODE:94]]

At startup, after the chain of providers and the handlers, the module logs where each kind of state lives:

[[CODE:95]]

- **One provider or several.** `registerSource()` takes the interfaces by name, so one class can implement all six, as here, or several classes can split them: a `RedisSessionStore` that registers `sessions`, and this class registering the other five. A second store for the same name fails at startup, naming both classes.
- **Some methods must be one statement.** Whatever decides that something works only once is a single conditional statement, never a read followed by a write. `touchSession()` updates only a session that still exists, so a request racing a sign-out can't bring the session back. `deleteSession()` resolves whether it deleted the row, so of two rotations of one session, or a rotation and a sign-out, exactly one wins. `markRefreshTokenUsed()`, `claimTotpStep()` and `consumeRecoveryCode()` count the rows they changed, and the three `consume` methods are a `DELETE … RETURNING`. `saveTotp()` keeps the larger time step with `greatest()`, the one place the store writes SQL by hand. `recordMfaFailure()` inserts first and counts second, outside a transaction, so a burst of parallel guesses can't all see a low count. Each method of the store interfaces gives its rule, and the race it prevents, in its doc comment.
- **Recording activity is best-effort.** If `touchSession()` fails (a lock timeout, a read-only replica), the request and sign-outs still succeed. The session is kept, `lastActiveAt` doesn't move, and the session goes idle at its previous deadline unless a later request records activity. Every failure emits a `session-touch-failed` event; the log gets one warning when failures start, nothing while they continue, and one line with their count on the next successful touch.
- **The tables stay bounded.** Anyone can ask for a magic link or a reset link, so each save deletes what has expired and, past 100,000 pending rows in a table, what expires first. Expired sessions and refresh-token families go as new ones are written.
- **Password reset and email verification keep working unchanged.** Their links are rows in `email_tokens` now, and their mailers still send them through `@nestjs/mail`.
- **Production refuses memory.** With `NODE_ENV` set to `production`, the module won't start while a store that a configured feature uses isn't registered, and names the interfaces to implement. Each feature needs only the stores it uses: `MfaStore` only with `mfa`, and `RefreshTokenStore` only with `accessToken` while refresh tokens are on. [The store contract](/security/authentication#the-store-contract) lists them. A store that none of your configured features uses fails at its first read instead. `allowInMemoryStorage: true` in the module options runs in memory anyway, but then every restart or deploy signs everyone out and forgets enrolled authenticators, and instances don't share any of it.

If your users live in the same database, `getSession()` can read each session's user in the same query and pass it on as `extra`, which `SessionAuth`'s `validate()` receives: one read per request instead of two. Type it with a `sessionExtra` key next to `user` (`users` and `toUser()` stand for your own table and the mapping that leaves out the password hash):

[[CODE:96]]

[[CODE:97]]

[[CODE:98]]

`extra` is never stored: `createSession()` never receives it, a rotation leaves it out, and `listUserSessions()` shouldn't set it. Nor is it exposed: `@CurrentSession()`, `request.session` and `AuthenticationContext.session` carry the session without it, so whatever the handlers need goes in the user `validate()` returns. Don't copy the user onto the session row instead of joining it: the copy goes stale when the user changes.

The package ships its rules as tests. `authenticationStoreContract()` from `@nestjs/authentication/testing` returns test cases that work with any test runner, and `concurrent: true` adds the races: parallel refreshes of one token, parallel uses of one code or link, bursts of failed codes, a sign-out racing a request, parallel deletes of one session, and a rotation racing a sign-out or another rotation. Run them on PGlite and, where the calls really race, on PostgreSQL:

[[CODE:99]]

`CappedStore` lowers the cap on pending rows so that `maxPending: 3` can check it. `startPostgres()` is a test helper that creates a throwaway database on a PostgreSQL server, or skips the PostgreSQL cases without one. A store that reads a row and then writes it back passes the other tests and fails these.

**With TypeORM.** The same store for an application whose ORM is TypeORM, on the same eight tables. Drizzle stays the tutorial's path: take this store instead of the one above, not next to it. The tables are entities, and every column states its type, so that the TypeORM CLI, which loads them without decorator metadata, sees the same schema as the application:

[[CODE:100]]

The TypeORM CLI and `TypeOrmModule` share one set of options, in a data source file:

[[CODE:101]]

Generate the migration from the entities, against a database with your previous migrations applied, apply it, and check that the entities and the database agree. The CLI needs a TypeScript loader for the data source file; this uses `tsx`:

[[CODE:102]]

The migration it wrote, `1790235914534-Authentication.ts`, is the `CREATE TABLE` and `CREATE INDEX` statements of the eight tables above, and `migrations` in the data source lists it. Now the store, under the same rules as the Drizzle one:

[[CODE:103]]

- **Conditional updates and deletes** put the condition in the criteria of `update()` and `delete()`, with `LessThan()`, `IsNull()` and `Or()`, and read `affected`. Never `save()`: it would write back a session that a sign-out just deleted.
- **`saveTotp()`** keeps the larger time step with `GREATEST()` over the conflicting row, which the upsert API can't express, so it is the one statement written as SQL, through `manager.query()`.
- **The `consume` methods** are the delete query builder with `returning('*')`. It returns raw rows under the database's column names, so `deleteReturning()` maps them back to entity properties through the entity metadata.
- **`recordMfaFailure()`** is two statements on `dataSource.manager`, each committed on its own, and `saveRecoveryCodes()` is the one method inside `dataSource.transaction()`.
- **Use it** in place of the Drizzle store: `TypeOrmModule.forRoot(dataSourceOptions)` in `AppModule` instead of `DrizzleModule`, and `TypeOrmAuthenticationStore` in the providers of `AuthModule` instead of `DrizzleAuthenticationStore`. It injects the `DataSource` that `TypeOrmModule` provides.

The contract suite runs on it unchanged. TypeORM connects through `pg`, so the suite needs a PostgreSQL server and is skipped without one. Two more cases check that the entities and the migration agree (what `migration:generate --check` checks), and that the store registers for all six contracts when provided in a module:

[[CODE:104]]

> info **Hint** Using Prisma? [The store contract](/security/authentication#the-store-contract), after the tutorial, lists what each contract must guarantee and how Prisma expresses the atomic methods. Test your store against the same cases.

#### Issue API keys to partners

Cat shelters and pet shops restock in bulk from their own inventory systems, and some customers reorder with a script. A script can't fill in a sign-in form, and a refresh token that changes with every use is a poor fit for a nightly job. Give them API keys instead: long-lived secrets that a customer creates in the web app and revokes when they're no longer needed. The script sends its key as a bearer token, and acts as the customer who created it.

The package checks the keys, and your database keeps them. Add a table to the schema:

[[CODE:105]]

Generate its migration, and apply it (the output is trimmed):

[[CODE:106]]

The third credential provider extends `ApiKeyProvider`, and does one thing: it finds a key by its id.

[[CODE:107]]

A key reads `cat_<id>_<secret>`: the prefix, a public id of 16 hex characters, and a secret of 256 random bits. `findKey()` looks up the id, and the provider does the rest. It compares the SHA-256 of the whole key with the stored `hash`, in constant time and with the same work for an id that doesn't exist, and refuses the key from `expiresAt` on. A slow hash such as the passwords' scrypt would add nothing here, since nobody guesses 256 random bits, and it would slow down every request. A wrong, expired or revoked key gets a 401 with `error="invalid_token"`, like a bad access token.

`JwtAuth` reads the same `Authorization` header. A JWT always contains two dots and a key contains none, so `JwtAuth` leaves keys to `ApiKeyAuth`, whichever of the two runs first. A request without credentials still gets a single challenge, `Bearer realm="store"`, since both providers use the same realm.

Now the endpoints that create, list and revoke keys:

[[CODE:108]]

- `generate()` returns the key, its id and its hash. The table stores the id and the hash, so `create` is the only time anyone sees the key. A customer who loses a key revokes it and creates another.
- The controller accepts `SessionAuth` alone, so keys are managed from the web app. Under `providers`, the credentials of any other provider count as none: a leaked key can't create more keys, or revoke its owner's.
- Keys expire after a year, so a forgotten key doesn't work forever. Deleting a key's row revokes it from the next request on.

Register both in `AuthModule`:

[[CODE:109]]

A key signs its owner in on every route that doesn't name its providers, `POST /orders` included. It never counts as a second factor: `PATCH /me/email` answers it with `mfa_required`, as it answers a session that hasn't passed the code. To keep a route to keys, or away from them, list the providers the route accepts in `@Authenticate()`. In a handler, `@CurrentSession()` holds the key's `keyId`, with `method` set to `api-key`, so an audit log can say which key placed an order. Keys that may only read, or only order, are a question of permissions, which is what [`@nestjs/authorization`](/security/authorization) is for.

**With TypeORM.** The table is an entity, next to the store's entities:

[[CODE:110]]

List it in the data source's `entities`, and its migration, generated as for the store's tables, in `migrations`. `findKey()` reads the row through the entity's repository, with `findOneBy()`, and the controller writes it with `insert()` and `delete()`.

#### Try it

Apply the [migrations](/security/authentication#keep-sessions-and-tokens-in-your-database), and start the application with the `.env` file from the previous sections:

[[CODE:111]]

In another terminal, sign up. The `-c` flag saves the session cookie to a file, and `-b` sends it with later requests. `--json` (curl 7.82 or later) sends a `POST` with a JSON body. Response headers are trimmed here and below:

[[CODE:112]]

The session and the pending verification link are rows in PostgreSQL now. The session's id is the SHA-256 hash of the cookie, and the link's token isn't stored at all:

[[CODE:113]]

The verification email appears in the application's log (`LogMailTransport` prints the text of each email):

[[CODE:114]]

The cookie signs Ada in, but her address isn't verified, so she can't place an order yet. Send the token back as the verification page would, and the order goes through. Without the cookie, the API answers 401:

[[CODE:115]]

Sign in as the mobile app, and use the access token. The commands below use [jq](https://jqlang.org/) to extract the tokens:

[[CODE:116]]

A refresh token works once. The second attempt with the same token is treated as theft, and revokes the whole family:

[[CODE:117]]

Turn on two-factor authentication. Add the secret to an authenticator app, and confirm with the code it shows. The code proves this browser has the authenticator, so the session is verified from here on, under a new cookie (`-c` saves it):

[[CODE:118]]

> info **Hint** With [oath-toolkit](https://www.nongnu.org/oath-toolkit/) installed, `oathtool --totp -b` followed by the secret prints the current code in the terminal.

Sign in again. The new session is pending until it passes the second factor, and verifying replaces the cookie:

[[CODE:119]]

The new address is unverified, and a verification email goes to it:

[[CODE:120]]

The mobile app is asked for a code too:

[[CODE:121]]

Start a Google sign-in. curl shows the redirect; open the same URL in a browser to complete it, and you land on `/orders`, signed in:

[[CODE:122]]

Ask for a magic link for a new customer, Grace. The link works only in the browser that asked for it, so keep the cookie the response sets. The email appears in the application's log:

[[CODE:123]]

[[CODE:124]]

Send the token back as the page would, with that cookie. Grace gets an account, with a verified address, and a session:

[[CODE:125]]

Grace runs a cat shelter, whose inventory system reorders litter. Create a key for it from her session, and place an order with the key. The key can't create keys, and once Grace revokes it, it stops working:

[[CODE:126]]

List Ada's sessions, then sign her out everywhere. Her old cookie stops working:

[[CODE:127]]

Ada forgot her password. Ask for a reset link for her address, and for an address nobody registered: both get the same empty 202, and only Ada gets an email:

[[CODE:128]]

[[CODE:129]]

Choose a new password with the token, as the reset page would. Ada is signed in again, pending her second factor (a pending session lives ten minutes, `mfa.pendingTtl`, hence the `Max-Age`), and the old password no longer works:

[[CODE:130]]

Finally, guess Grace's password. The sixth attempt within 15 minutes is refused before the password is checked:

[[CODE:131]]

#### GraphQL and WebSockets

The global guard, `@Public()`, `@CurrentUser()` and `AuthenticationContext` work in GraphQL resolvers and WebSocket gateways too. The guard reads the cookie and the headers from the request that carries them.

In GraphQL, that's the `req` on the GraphQL context, so the `context` option must be a function that builds a context for each request. A `context` given as an object would be one object for every request, and the app fails at startup. Nest runs global guards and interceptors on root resolvers only: to guard field resolvers too, and to give them `AuthenticationContext`, add `fieldResolverEnhancers: ['guards', 'interceptors']`.

[[CODE:132]]

Over `graphql-ws`, every operation on a socket shares that upgrade request, and each operation that needs a user authenticates again with its cookie, so a sign-out everywhere stops the next one. `@CurrentUser()` gives each operation its own user, and `null` to a `@Public()` one. `req.user`, which the module also sets for code that reads the request, holds whichever operation authenticated last: read `@CurrentUser()` instead.

Nest runs no guards on a gateway's `handleConnection()`, so authenticate the handshake with `WsAuthenticator`:

[[CODE:133]]

It closes a connection that nobody signed in on, with code 1008, or socket.io's `disconnect()`; to keep guests, pass `authenticateConnection()` a third argument whose `required` option is `false`. With socket.io, it reads the handshake's headers, so the `request` argument can go. A handshake from another site's page is anonymous, as a [cross-origin write](/security/authentication#add-sign-up-and-sign-in) is. The guard then authenticates every message again, so a revoked session stops working mid-connection. `@CurrentUser()` is per message, `null` on a `@Public()` one. `client.user` holds the user of the last message that authenticated, and is cleared once a message is refused for its credentials.

[`@nestjs/authorization`](/security/authorization) checks `@Can()` against the user of each message and each operation, not the socket's.

#### Testing

End-to-end tests boot the real `AppModule`, with three things changed. The database is [PGlite](https://pglite.dev), PostgreSQL compiled to WebAssembly, with your real migrations applied, so the tests need no server. Mail goes to an `InMemoryMailTransport`, which keeps each email for the test to read. And scrypt is slow on purpose, a few hundred milliseconds and 128 MiB of memory per hash at the default cost, so the test overrides `PasswordHasher` with a cheaper one. The application also reads its settings at bootstrap, so the tests need test values for them:

[[CODE:134]]

[[CODE:135]]

- `mailbox.assertSent()` finds the latest email to an address, of a mail class, and `link()` returns its first link containing the path, as a `URL`. That's the whole flow for verification, reset and magic links: send, find the link, follow it.
- The reset email is sent after the response (see [Reset forgotten passwords](/security/authentication#reset-forgotten-passwords)), so the test waits for it with `vi.waitFor()`. The other emails are sent before the route answers.
- `DrizzleAuthenticationStore` runs on PGlite as it does on PostgreSQL. PGlite has a single connection, so two requests never truly race there; the store's [contract tests](/security/authentication#keep-sessions-and-tokens-in-your-database) run on PostgreSQL too, where they do.

To sign a test user in without going through a sign-in route, `SessionService.create()` returns a session cookie, and `TokenService.issue()` a bearer token (for a user without an authenticator). To test code that reads `AuthenticationContext` without HTTP, run it as a user: `run()` takes an authentication result (the user, and optionally the session) and a function to run.
