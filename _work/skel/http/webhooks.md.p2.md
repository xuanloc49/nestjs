#### Let partners subscribe

Shelters and resellers call the partner API with an API key: the example's two partners, Northside Pet Supplies (a reseller) and Riverside Cat Shelter, have the sample keys in [Installation](/http/webhooks#installation). `PartnerGuard` looks the key's hash up and sets the partner on the request, and `@CurrentPartner()` reads it:

[[CODE:13]]

A subscription is a URL, the event types to receive, and a description; an update sends only what changes. The DTOs check the shape, and leave the URL and the types to the package, which knows what it accepts. Request bodies are validated with whatever the application already uses: every DTO on this page comes twice, as a class with `class-validator` decorators and as a Zod schema, so pick the style you have and skip the other listing:

[[CODE:14]]

The same rules as Zod schemas, whose inferred types replace the classes. Nest 12.1 validates any [Standard Schema](https://standardschema.dev/) object, from Zod, Valibot or ArkType, through `StandardSchemaValidationPipe`:

[[CODE:15]]

The subscription API is a controller over `WebhookEndpoints`. Every call passes the partner's id as the **tenant**: an endpoint is created for that tenant, listed for that tenant, and another partner's endpoint id behaves as if it didn't exist:

[[CODE:16]]

With the Zod schemas, the body parameters declare their schema instead of a class:

[[CODE:17]]

> info **Hint** The DTOs are enforced only by a validation pipe: bind `ValidationPipe` globally, with `useGlobalPipes()` in `main.ts` as [Register the modules](/http/webhooks#register-the-modules) does (`whitelist` drops properties without a decorator), or as an `APP_PIPE` provider. With the Zod schemas, bind `StandardSchemaValidationPipe` the same way instead: an application uses one or the other. The [validation](/application/validation) page has the options of each.

`create()` returns the endpoint with its `secret`, a Standard Webhooks `whsec_…` of 32 random bytes, generated here. This API shows it this once: `list()` and `get()` never include it, and a partner that lost it rotates. The package keeps the secret, sealed when `encryption` is set, because it signs with it, and `getSecret()` reads the current one back, for a "reveal" button behind a fresh sign-in if your API offers one. Endpoints moved from Svix or another Standard Webhooks sender keep their secrets: a migration script passes the partner's existing `whsec_…` as the `secret` of `create()`, so the partner's verifier keeps working, and `rotateSecret()` takes a given `secret` the same way. The package checks what the partner submits and throws an `InvalidWebhookEndpointError` with a 400 status: a URL that isn't `https://` (or `http://` with `allowHttp`), that carries credentials, or whose host is a blocked address, such as `https://169.254.169.254/latest/meta-data/` or `https://localhost/`; an event type that isn't in `eventTypes`. A partner's mistakes come back as 400s, and another partner's ids as 404s, through one filter:

[[CODE:18]]

[[CODE:19]]

The delivery log's controller, added to this module [later](/http/webhooks#retries-the-delivery-log-and-replay), gives the partner the other half: what was sent to their endpoints.

#### Send order.shipped and order.cancelled after the commit

`Webhooks.dispatch()` takes your transaction handle first, like `Outbox.add()`: with Drizzle, the `tx` that `db.transaction()` passes its callback, whose type the service gives `Webhooks<Transaction>`. Cancelling an order updates it and dispatches `order.cancelled` on the same `tx`; shipping it (which the carrier triggers, in [Receive the carrier's Stripe-like webhooks](/http/webhooks#receive-the-carriers-stripe-like-webhooks)) updates it and dispatches `order.shipped`. `tenant` is the partner that placed the order, so only that partner's endpoints receive it:

[[CODE:20]]

Nothing leaves the process inside the transaction. If it rolls back, the message never existed. If it commits, the outbox relay picks the message up (`notify()` asks it to do so now instead of at its next poll) and hands it to the package's fan-out, which creates one delivery per enabled endpoint of the tenant that subscribed to the type. The worker then signs and sends each. This is what Northside's server receives, on every attempt of the delivery, with the same `webhook-id` and the exact body that was serialized at `dispatch()`:

[[CODE:21]]

The signature is keyed with the endpoint's secret, so the partner can verify it with any Standard Webhooks library. Or with this package: Northside's receiver is a Nest application of its own, with its own root module, that only receives, with `outgoing: false`, and `@VerifyWebhook('store')` on its route. `STORE_WEBHOOK_SECRET` takes a comma-separated list, because the store's [rotation](/http/webhooks#rotate-secrets) signs with two secrets for a day:

[[CODE:22]]

[[CODE:23]]

[[CODE:24]]

The partner's `OutboxModule` provides the inbox that `@VerifyWebhook()` deduplicates with. It runs in memory here; a real partner registers the outbox's store on its own database, `PostgresOutboxStore` on PostgreSQL, as the analytics service does in [the outbox tutorial](/reliability/outbox#publish-to-the-analytics-microservice).

#### Retries, the delivery log and replay

A 2xx from the partner is a success. Anything else is a failed attempt: a 5xx, a 4xx, a 3xx (redirects are never followed), a timeout, a refused connection. The worker retries after the backoff, honors a `Retry-After` header in seconds or as an HTTP date (up to the backoff's cap, a day; any other value is ignored), and on a 429, 502, 503 or 504 pauses that endpoint until then, five seconds without a header: its other deliveries wait without an attempt, so a partner asking for a breather gets one probe, not one per batch, while the other partners' deliveries go on. Three answers end a delivery early: a 410 Gone, which also disables the endpoint (`gone`); a destination the transport refuses (the subscription checks, run again at every send, because DNS changes); and `retry.retryIf` saying no. After the last attempt, the delivery is `failed` with the reason `exhausted`.

An endpoint that fails every attempt for `disableEndpointAfter` is disabled with the reason `failing`, and `WebhooksEvents` emits `endpoint-disabled`: tell the partner. A success at any point resets the clock. A disabled endpoint, whether by the worker or by the partner (`enabled: false` in the subscription `update()`), gets no delivery for anything dispatched while it stays disabled: the fan-out skips it, and nothing creates those deliveries later. A replay doesn't either, because it re-sends deliveries that exist. What does exist are the deliveries that were pending when the endpoint was disabled: they fail with the reason `endpoint-disabled` when their turn comes, and after re-enabling, the partner can ask for those again, as the failed deliveries they are. Re-enabling forgets the failures, and the endpoint receives what is dispatched from then on.

Every attempt is logged: the status code, the duration, the first 4 KB of the response body, the error. The partner reads its own log, and asks for a delivery to be sent again, one or every failed one since an outage began. The bulk retry takes an endpoint and the start of the outage, both optional:

[[CODE:25]]

[[CODE:26]]

[[CODE:27]]

With the Zod schema:

[[CODE:28]]

A retry starts a new round: `attempts` back to 0, sent now, with the same `webhook-id` and the same body. The log of the earlier rounds stays. Because the id is the same, a partner whose inbox kept it answers 2xx without running its handler, so a replay is safe for a delivered webhook too: Northside can ask for the last hour again after losing its own database, and get only what it hasn't processed.

Operators get the same through `WebhookDeliveries` without a tenant: `stats()` (pending, due, leased and failed counts, and `lagMs`, how long the most overdue delivery has waited, the number to alert on), `retry()` across tenants, and `prune('30d')`, which nothing calls for you. `WebhooksEvents.events$` emits `delivered`, `retry-scheduled`, `delivery-failed`, `endpoint-disabled` and `destination-blocked`, each also on a `node:diagnostics_channel` channel named `nestjs:webhooks:<event>`.

#### Receive the payment provider's webhooks

The payment provider tells the store that a payment went through with a Standard Webhooks request. Verifying it needs the body exactly as the provider signed it, so the application is created with `rawBody: true`. That works on Express and on Fastify:

[[CODE:29]]

The sender goes into the module's `receivers`, by the name the route will use. The payment provider's secret is the one it shows in its dashboard:

[[CODE:30]]

`@VerifyWebhook('payments')` on the route verifies the request before the handler runs, and `@IncomingWebhook()` gives what was verified: the sender's `id` for the webhook, the signed `timestamp`, the `payload` parsed from the signed bytes, and `processInTransaction()`:

[[CODE:31]]

[[CODE:32]]

[[CODE:33]]

What the decorator checks, in order: the three `webhook-` headers are present and well formed, with a `webhook-id` of at most 255 characters, counted in code points; one `v1,` signature in `webhook-signature` matches the HMAC of `id.timestamp.body` with one of the configured secrets (compared in constant time; several secrets can be listed while the payment provider rotates); the signed timestamp is within 5 minutes of now, in either direction; the body is JSON. A request that fails gets a 401 with a generic message. The reason never goes to the sender; it goes to the `verification-failed` event, with the receiver's name. A signed body that isn't JSON gets a 400 from the framework's body parser before the decorator sees it, so no event is emitted for it. The same holds for a body over the body parser's size limit (100 kB on Express and 1 MiB on Fastify by default): it gets a 413 before the decorator runs, and no event is emitted. If the payment provider sends larger bodies, raise the limit with `useBodyParser()`, as described in [Raw body](/faq/raw-body#body-parser-size-limit).

Then comes deduplication. The payment provider retries until it gets a 2xx, so a timeout after the handler succeeded makes it send the same `webhook-id` again. The receiver keeps an inbox of the ids it processed (the outbox's inbox, consumer `webhooks:payments`): a known id is answered with an empty 200 without running the handler, and an id is recorded only after the handler succeeded, so a handler that threw is run again on the payment provider's retry. Two copies arriving together at one instance run the handler once; two instances receiving them at the same moment could both run it, which is what the next paragraph is for.

`markPaid()` moves money-related state, so the controller goes one step further with `processInTransaction()`: the webhook's id is recorded *through the order's transaction*, and `markPaid()` runs only if it is new. The record and the new status commit together. A redelivery after a crash between the handler and the inbox write, or one racing this request on another instance, finds the id and changes nothing; it resolves with `duplicate` set, which the controller uses to log only once. And when `markPaid()` throws, a payment for the wrong amount, say, the transaction rolls back, the record with it, the sender gets the 409, and its retry gets another chance once the order is fixed.

For development, a small script signs a request the way the payment provider (and, in the next section, the carrier) would, with `signWebhook()` from `@nestjs/webhooks/testing`:

[[CODE:34]]

#### Receive the carrier's Stripe-like webhooks

The carrier copied Stripe's scheme: a `Carrier-Signature: t=…,v1=…` header, the hex HMAC-SHA256 of `t.body` keyed with the secret's text, and the event's id inside the payload. The receiver in the [`receivers` option](/http/webhooks#receive-the-payment-providers-webhooks) says so: `scheme: 'stripe'` with the `header` name. Stripe's own webhooks are the same receiver without `header`. GitHub's, and senders with a scheme of their own, are in [Other senders](/http/webhooks#other-senders).

The handler is the interesting part. Marking the order shipped and telling the partner happen in one transaction: the order's new status, the partner's `order.shipped` message (through the outbox) and this webhook's inbox record commit together, or none of them does:

[[CODE:35]]

`markShipped()` is the method from [Send order.shipped and order.cancelled after the commit](/http/webhooks#send-ordershipped-and-ordercancelled-after-the-commit). The deduplication id is the event's `id` from the signed payload, not a header, because that is what Stripe's scheme signs. A `shipment.shipped` event for an order that isn't paid yet is refused with a 409, and nothing is recorded: when the carrier retries it after the payment arrived, the same event id is processed.

#### Other senders

GitHub's webhooks take `scheme: 'github'`: `X-Hub-Signature-256`, the hex HMAC-SHA256 of the body keyed with the secret's text.

> warning **Warning** GitHub signs neither a timestamp nor an id. A captured request verifies forever, and deduplication keys by default on the `X-GitHub-Delivery` header, which isn't signed: the same request replayed with a new value in that header runs the handler again.

Key the deduplication on the signed body instead, with the receiver's `id` option. The payload is parsed from the bytes that were signed, so a replay has the same id as the original, and the inbox skips it:

[[CODE:36]]

The inbox remembers an id until `OutboxInbox.prune()` removes it, so for GitHub its window is also how long a replay is caught: keep it long. Replayed after that, a request verifies and runs; accepting GitHub's webhooks only from the addresses it publishes (`hooks` in `https://api.github.com/meta`) narrows who can send one.

A sender with a scheme of its own is a class extending `WebhookSignatureScheme`. Say the store also sells through a marketplace, which signs the URL it posts to followed by the body, and puts the event's id in the body:

[[CODE:37]]

- `verify(request, keys)` gets the request's `headers` (lower-case names) and its `rawBody`, as received, and one key per configured secret. It returns `valid: true`, with the sender's `id` when a header carries one and the signed `timestamp` in epoch seconds when the scheme signs one (the receiver's `tolerance` then applies), or `valid: false` with a `reason` for the `verification-failed` event and a `detail`. It runs synchronously, before the body is parsed as JSON.
- `WebhookSignatureScheme.matches(expected, candidates)` compares in constant time. Never compare signatures with `===`.
- `idFromPayload(payload, headers)` gives the deduplication id when no header carries one, from the parsed body, as the built-in Stripe scheme does with the event's `id`. An id longer than 255 characters, from either, is refused with `malformed-header`.
- `key(secret)` turns each configured secret into the key `verify()` receives, once, at startup, where a malformed secret stops the application. The default takes the secret's text and refuses an empty one or one with surrounding whitespace. Override it for an encoded secret, as the `standard` scheme does for `whsec_…`.

The receiver takes an instance:

[[CODE:38]]

#### Rotate secrets

A secret leaks, or a partner's policy says a year is enough. `POST /partner/webhook-endpoints/:id/rotate-secret` (see [Let partners subscribe](/http/webhooks#let-partners-subscribe)) returns a new secret, and the old one keeps signing next to it for `secretRotationOverlap`, 24 hours: every delivery carries two `v1,` signatures, and a Standard Webhooks verifier accepts any one that matches. The partner adds the new secret to its list, deploys, removes the old one, on its own schedule. After the overlap, only the new secret signs. `rotateSecret()` with `overlap: 0` retires the old one at once, for a leaked secret.

Set `WEBHOOKS_ENCRYPTION_KEYS` to seal the secrets at rest, `openssl rand -base64 32` for each key, newest first. Endpoints created before are still read (their secrets are plaintext) and sealed at their next rotation.

#### Try it

Create the database, and apply your migrations to it, which create the order API's tables and rows from [Installation](/http/webhooks#installation):

[[CODE:39]]

Export the secrets the payment provider and the carrier share with the store (invented here), allow deliveries to this machine, and start the API on port 3000:

[[CODE:40]]

[[CODE:41]]

Your migrations created the order API's tables, and the stores their schemas, next to them. Northside subscribes, with its API key, to both events at a receiver it will run on port 4100. The response carries the secret, this once:

[[CODE:42]]

> info **Hint** `--json` needs curl 7.82 or later.

The URL of a cloud metadata service is refused before anything is stored, and so is an event type the API doesn't send. Riverside Cat Shelter, the other partner, gets a 404 for Northside's endpoint:

[[CODE:43]]

Start Northside's receiver, `partner-service/main.ts`, on port 4100, with the secret it was given in its environment:

[[CODE:44]]

Now place an order, and let the payment provider pay for it and the carrier ship it. The script signs the requests they would send, with the secrets exported above:

[[CODE:45]]

The API's log shows both webhooks processed, and Northside's log shows `order.shipped` arriving right after the carrier's, with its `webhook-id`:

[[CODE:46]]

[[CODE:47]]

Northside's delivery log has the delivery, and its details have the message and the one attempt, with the partner's status code and how long it took:

[[CODE:48]]

[[CODE:49]]

Stop Northside's receiver with `Ctrl+C`, then place an order and cancel it. The delivery fails to connect, the API logs the wait before the next attempt, and the partner's log shows the delivery pending with its error:

[[CODE:50]]

[[CODE:51]]

Start the receiver again. The retry goes through, and the log keeps both attempts:

[[CODE:52]]

[[CODE:53]]

[[CODE:54]]

Northside asks for that delivery again. It is sent with the same `webhook-id`, the receiver's inbox recognizes it and answers 204 without running the handler (nothing new in its log), and the delivery log shows a new round:

[[CODE:55]]

[[CODE:56]]

Now the payment provider's side. A redelivery with the same `webhook-id` (a lost 200, so the provider retried) is answered but not processed again: the API logs one payment. A tampered body and a wrong secret are refused, without a reason:

[[CODE:57]]

[[CODE:58]]

Finally, rotate the endpoint's secret. The receiver still runs with the old one, and the next delivery verifies anyway: it carries both signatures. Then restart the receiver with the new secret listed first and the old one behind it, as a partner would deploy it, and place and cancel another order: that delivery verifies too:

[[CODE:59]]

[[CODE:60]]

[[CODE:61]]

[[CODE:62]]

[[CODE:63]]

The deliveries are rows in your database, in the store's schema:

[[CODE:64]]

#### Testing

In an e2e test, run PostgreSQL in-process with [PGlite](https://pglite.dev) and your real migrations, turn the relay and the worker off, replace the transport with the one that records requests, and sign the providers' requests with `signWebhook()`. Override the database `DrizzleModule` registers (`getDrizzleToken()` returns its token) with one on PGlite: the stores follow, because their factories inject it, and create their schemas there when the application starts:

[[CODE:65]]

- The outbox, both stores, the migrations, the fan-out, the signing and the verification are real. Only the network is replaced: `InMemoryWebhookTransport` answers 200 and keeps every request, and `respondWith(503)` or a function simulates a partner that is down, slow or picky.
- `deliver()` is the whole pipeline after the commit: `relay.runOnce()` publishes the committed messages (the fan-out creates the deliveries), `worker.runOnce()` claims one batch and sends it.
- `SentWebhook.isSignedWith(secret)` verifies the `v1` signature with an endpoint's secret, and `data` is the body's `data`, so a test asserts on what the partner would have verified and read.
- `signWebhook()` produces the body and headers the payment provider, Stripe or GitHub would send. Reuse its `id` for a redelivery, move `timestamp` to test the tolerance, change a byte of the body for a tampered request.
- For behavior that depends on time, such as backoff, leases and the rotation overlap, move `Date.now()` forward with `vi.spyOn(Date, 'now')`. The worker and the stores take the time from it, and real timers keep running for sockets.
- The example's `tutorial.e2e-spec.ts` runs every section of this page over real HTTP, on PGlite and on a PostgreSQL server: the API delivers to the partner's receiver through the default transport, with the outage, the replay, the redeliveries and the rotation. Its `zod.e2e-spec.ts` boots the same app with the Zod variants of the DTOs and `StandardSchemaValidationPipe`. Its store tests run the stores through Drizzle on PGlite, PostgreSQL and MySQL, and through TypeORM on PostgreSQL: the contract suites, a dispatch that commits and rolls back with the order, and the schemas in production.

See [End-to-end testing](/fundamentals/testing#end-to-end-testing) for more about the testing setup.
