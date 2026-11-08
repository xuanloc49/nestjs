#### Add "Sign in with Google"

In the Google Cloud console, create an OAuth client ID of type **Web application**, and add this authorized redirect URI (and the production one, when you deploy):

[[CODE:62]]

Add the client's credentials to `.env`, next to `APP_URL`:

[[CODE:63]]

The first time someone signs in with Google, your application has to decide which local account that Google account belongs to. Store the link as a (provider, subject) pair, where the subject is Google's stable id for the account. Emails change; subjects don't. Add an identities table to the repository:

[[CODE:64]]

The package asks an `OidcAccountResolver` for that decision:

[[CODE:65]]

Linking by email needs both sides to have verified the address:

- **Google must have verified it** (`profile.emailVerified`). Otherwise, anyone could create a Google account with a customer's address and take over their account at the store. Returning `null` refuses the sign-in with a 403.
- **The store account must have verified it too** (`existing.emailVerified`). Otherwise, someone could sign up first with a customer's address and a password of their choosing, and keep access once the customer signs in with Google. This is called account pre-hijacking. An account created with a password is unverified until its owner opens the [verification link](/security/authentication#verify-email-addresses), or [resets the password](/security/authentication#reset-forgotten-passwords). Until then, it gets a 403 that asks the customer to sign in with their password and connect Google from their account.

Connecting Google to an account the customer is signed in to needs no email match at all. The package calls it a link flow: the web app's "Connect Google" button points to `GET /auth/oidc/google/login?link=true`. The package only starts it for a fully signed-in session, and not from another site's page, which gets a 403: a link attaches whatever Google account is signed in on this browser. On the callback it checks that the same session is still live, then calls `resolveUser()` with `linkTo`, the signed-in user. The resolver links the Google account to them, unless it already belongs to another customer. The session stays as it is, and the browser is redirected to `redirectTo`.

Enable OpenID Connect with the `google()` preset and the URL Google sends the browser back to. `:provider` stands for the provider's name, so one callback route serves every provider you add:

[[CODE:66]]

The routes are yours, so they sit with your other routes, under your prefixes, versions and throttling. `OidcService.start()` builds the redirect to Google and `finish()` handles the callback; a controller exposes the two:

[[CODE:67]]

- `GET /auth/oidc/google/login?redirectTo=/orders` redirects the browser to Google. The web app's "Sign in with Google" button is a plain link to it. `start()` uses the authorization code flow with PKCE, a `state` and a `nonce`. The login transaction is stored server-side under `state`, and the browser gets a secret whose SHA-256 hash is the `state`, in an `HttpOnly` cookie named `__Host-oidc_tx`, for 10 minutes.
- `GET /auth/oidc/google/callback` is where Google sends the browser back. `finish()` checks that the `state` in the query is the hash of the secret in the browser's cookie (so nobody can finish a login they didn't start in this browser, even with a callback URL read from a log or a browser's history), exchanges the code, verifies the ID token's signature against Google's published keys, and checks its issuer, audience, expiry and nonce. If Google can't be reached, or answers with an endpoint that isn't https, the answer is a 502, not a 401. It then calls `resolveUser()`, signs the user in through `SignInService` (so a customer with an authenticator gets a pending session), and returns the redirect to `redirectTo`, or to `/`. Only relative paths are accepted as `redirectTo`, so the login can't be turned into an open redirect.
- Both read the request and set their cookies through Nest's HTTP adapter, and return what `@Redirect()` expects, so the controller works on Express and Fastify alike, without `@Req()` or `@Res()`.

Register the controller and the resolver in `AuthModule`:

[[CODE:68]]

The `github()` preset works the same way. `microsoft()` also takes your directory's tenant id as its `tenant` option, next to `clientId` and `clientSecret`: a GUID from the Overview page of the Microsoft Entra admin center, such as `process.env.ENTRA_TENANT_ID`. A domain, or the multi-tenant `common`, `organizations` and `consumers`, fails at startup: for those, Microsoft publishes another issuer than the one asked for, and every sign-in would fail. Add them next to `google` in `providers`, and register the callback URL with each of them, with its name in place of `google`.

An application served under several domains, such as one domain per customer, can't name a single callback URL: a login started on one domain must come back to that domain. Pass a function of the request as `callbackUrl` instead. `start()` calls it on the login, and `finish()` calls it again on the callback, so it must return the same URL for both. Compare the host with your own list of domains rather than trusting the header, and register every URL it can return with each provider:

[[CODE:69]]

The function can also be `async`, to look the domains up in your database. Whatever it throws is the login's answer, like the 404 above for a domain the application doesn't serve, and a URL that isn't absolute fails the login with an error that names the function. The `__Host-oidc_tx` cookie belongs to the domain that set it, so a login finishes on the domain where it started. If the function ever returned another URL on the callback, the provider would refuse the code, and the callback would get a 401. Behind a proxy that rewrites the host, read the header it forwards instead, such as `X-Forwarded-Host`, and only from a proxy you trust.

Some applications only learn their providers at runtime. An application that sells to businesses may give each customer its own OIDC client, or let them bring their own identity provider, set up from an admin page and stored in your database. Pass a function of the provider's name as `providers` instead. `start()` calls it on the login, and `finish()` calls it again on the callback. Return the provider's configuration, or `undefined` for a name you don't serve, which gets a 404:

[[CODE:70]]

The configuration is looked up again on the callback rather than stored with the login, so a secret you rotate in your database is used from the next call on, by a login already under way too. Each configuration the function returns gets the checks the object form gets at startup: one without a `clientId`, or without a `clientSecret` unless its `tokenEndpointAuthMethod` is `'none'`, fails the login with an error that names the function. The function runs on every login and callback, so cache the lookup if it's slow. The package caches each provider's discovery document and keys by issuer, so customers who sign in through the same provider share them.

Identities are linked by (provider, subject), and the provider is the name, so each name must stand for one client of one provider. Put the customer in the name, like `acme` above, rather than using one name, such as `okta`, for every customer's provider: two customers' providers can give out the same subject. When customers bring their own identity provider, two more things change:

- **Their provider vouches for whatever address it likes.** It can mark any address as verified, including the address of another customer's user. The resolver above links accounts by verified email. With providers your customers control, link by email only to that customer's own accounts, or not at all.
- **The issuer is user input.** The package fetches the discovery document, the keys and the tokens from the URLs the configuration names, and nothing keeps those requests off your own network. Check an issuer a customer enters against the providers you support before you store it.

#### Add magic-link sign-in

A magic link signs a customer in from their inbox, without a password. The package creates and checks the links; delivering them is up to you, through a `MagicLinkHandler`. The store emails them like the verification links, with a template and a mail class of their own:

[[CODE:71]]

[[CODE:72]]

Enable magic links: the handler in `AuthModule`, and the URL the links point to in the options:

[[CODE:73]]

[[CODE:74]]

`MagicLinkService.create()` makes a random 256-bit token, valid for 15 minutes and usable once, and passes the link to your handler. It stores the SHA-256 hash of the token combined with a secret that only this browser's transaction cookie holds (see below), so a link read from a log, or forwarded, finds nothing, even with a forged cookie. With `bindToBrowser: false`, it stores the hash of the token alone. The token is added to the URL as a `token` query parameter, and your code never sees it otherwise.

Point the link at a page of your web app, not at the API. The page reads the token from its URL and POSTs it back. Email scanners and link previews follow links in emails with GET requests, and would use up the token before the customer clicks. The page must be on the same site as the API: requesting a link sets a cookie that the browser sends back with the token.

[[CODE:75]]

- The request route answers 202 whether or not the address has an account, and the account is only created once the link is used. A request posted from another site's page gets a 403, as a sign-in does: that page could otherwise set this browser's transaction cookie for a link to its author's address, then get the customer to open it (login CSRF).
- `consume()` burns the token, calls `resolveUser()`, and signs the user in through `SignInService`, which sets the cookie, so two-factor authentication still applies. `resolveUser()` returns the account with its stored `email`, and the link signs the account in only if that is the address the link was sent to, compared trimmed, lowercased and in Unicode NFC. A lookup that ignores accents or dots, as MySQL's default collation does, can't hand one mailbox another customer's account: `consume()` returns `null` instead.
- A link works only in the browser that asked for it. `create()` sets a transaction cookie, `__Host-magic_link_tx`, and `consume()` refuses the token without it, before looking anything up: it throws a `MagicLinkError`, and the module answers it with a 401 whose `error` is `not_this_browser` and whose message tells the customer to open the latest link in the browser they requested it from, or to request a new one here. Otherwise anyone could request a link for their own address and get a customer to open it, which would sign the customer's browser in to the attacker's account (login CSRF). The refused link stays valid in the browser that requested it, and the answer reveals nothing about the token, since a made-up one gets it too. The cookie keeps the last five links the browser requested, so a customer who clicks "Resend" and then opens the first email is still signed in; a link older than those five gets the same 401. So a customer who asks for a link on the laptop and opens the email on the phone is told to open it on the laptop, or to ask for a new link on the phone, which then works there; an application that would rather let the link itself work on the phone sets `bindToBrowser: false` in the `magicLink` options. Unknown, used and expired links, and addresses the handler refuses, get the controller's one generic answer: `consume()` returns `null` for all of them, and only the `magic-link-refused` event says which it was.
- Using the link proves the address, so accounts created by a link are verified. An account created with a password is different while its address is unverified: the link proves who owns the address now, not who chose the password, so the handler refuses it with a 403 rather than handing a pre-hijacked account to its owner. Once the owner has used the [verification link](/security/authentication#verify-email-addresses), or [reset the password](/security/authentication#reset-forgotten-passwords), magic links work for that account too.
- `redirectTo` survives the round trip only if it's a relative path, such as `/orders`.

With the Zod schema:

[[CODE:76]]

Register the controller:

[[CODE:77]]

#### Let customers manage their sessions

Sessions live on the server, so customers can see where they're signed in and end any of those sessions. To tell those sessions apart, record the browser each one belongs to. `session.metadata` runs whenever a customer signs in, with a password, with Google or with a magic link, and what it returns is stored with the new session:

[[CODE:78]]

Then list the sessions, and end them:

[[CODE:79]]

- Session ids are SHA-256 hashes of the cookie tokens. Showing them to their owner is safe, since a cookie can't be derived from one. `revoke()` takes the user as well as the id, and only ends a session that belongs to them, so an id from the URL can't end another customer's session.
- `sign-out` is `@Public()`, like `verify` in [two-factor authentication](/security/authentication#add-two-factor-authentication), so a customer who never finishes the second factor can still sign out. `signOut()` ends the session in this browser's cookie and clears the cookie. It returns `false` when there was no session, and the route answers 401: a bearer token here signs nothing out.
- `signOutEverywhere()` ends every session and, when the application issues them, every refresh token of the user, and clears this browser's cookie. Access tokens that were already issued stay valid until they expire, which is why they only last 15 minutes.

The mobile app signs out of one device by revoking its refresh token. Add a route to `TokensController`. `TokenService.revoke()` ends the token's family: the token, its predecessors and its successors:

[[CODE:80]]

Register the controller. This is the finished module, with every credential provider and handler of the tutorial:

[[CODE:81]]

Rotate the session whenever privileges change, for example after a password change or when a customer becomes staff: `SignInService.rotateSession()` gives this browser's session a new id, and sets the new cookie; `completeMfa()` already does this. It resolves `null`, and sets no cookie, when the browser has no session or lost it meanwhile: a sign-out everywhere, a password reset, or another request that rotated it first.

#### Rate-limit sign-in

`@nestjs/authentication` doesn't limit request rates. That's the job of `@nestjs/throttler`, a separate package:

[[CODE:82]]

A limit per IP address alone is too coarse for sign-in. Customers behind the same network address share it, so it can't be low enough to stop one client from guessing at one account. Use two [throttler definitions](/security/rate-limiting#multiple-throttler-definitions); each request counts against both. `default` counts per IP address, on every route. `account` counts per email and IP address, wherever the request body names an account:

[[CODE:83]]

Register `ThrottlerModule` with both definitions, and `ThrottlerGuard` as a global guard:

[[CODE:84]]

The guard runs before validation, so `accountEmail()` checks that `email` is a string. `normalizeIp()` groups IPv6 addresses by their `/64` prefix, as the throttler's own tracker does, so a client can't get a new counter for every address in its subnet.

The guard is registered in the root module, so it runs before the authentication guard. Global guards run in module order, and the root module comes first. That means guessed bearer tokens count against the limit too, rather than only being rejected with a 401.

Finally, tighten the limits on the routes that check a password or send an email. Each `@Throttle()` counts per route, and sets both limits: per IP address, and per account:

[[CODE:85]]

[[CODE:86]]

[[CODE:87]]

[[CODE:88]]

`Throttle`, `SkipThrottle`, `minutes` and `hours` are imported from `@nestjs/throttler`. The limits per IP address are a judgement call, since offices and mobile carriers put many customers behind one address. The `account` limit applies to every route whose request body has an `email`, at 5 requests per 15 minutes unless the route sets its own; `@SkipThrottle({{ '{' }} account: true {{ '}' }})` leaves a route out.

- `forgot` counts per address, whatever the IP address, so nobody can fill a customer's inbox with reset links, from one IP address or many. Someone who uses up that limit only delays the customer's own request: the links they caused went to the customer, and any of them works.
- The magic-link request keeps the email and IP address together. A link works only in the browser that asked for it, so a limit per address alone would let anyone use up a customer's links from their own browser, and keep the customer from signing in.
- Sign-up names a new address each time, so it skips the `account` limit and the limit per IP address does the work. Otherwise a customer whose password fails the sign-up rules a few times would be refused.

The two-factor codes don't need a throttle of their own: the package locks an account's codes after 5 failures, from any IP address, route or transport. Neither does `POST /auth/password/reset`: a guessed token costs one lookup, and there are 2^256 of them.

> info **Hint** Behind a load balancer or reverse proxy, every request seems to come from the proxy. Enable `trust proxy`, as described in the throttler's [Proxies](/security/rate-limiting#proxies) section, so the tracker sees client addresses.
