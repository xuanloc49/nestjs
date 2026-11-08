#### Send it in the customer's language

The store sells in English and Polish. Customers choose a language when they sign up, and the `customers` table stores it in a `locale` column: `en` or `pl`. The mailer hands the locale of each send to the template engine, which picks the template for it.

Translate the template: add `order-confirmation.pl.html` next to the English one.

[[CODE:25]]

For the locale `pl`, `FileTemplateEngine` renders `order-confirmation.pl.html`, and for any other locale, or none, `order-confirmation.html`. A regional locale tries itself first, then its language: for `pt-BR`, the engine looks for `order-confirmation.pt-BR.html`, then `order-confirmation.pt.html`. Partials and the layout are looked up the same way, so the layout stays shared, and the Polish signature is a partial of its own:

[[CODE:26]]

A mail's copy is prose, so it's translated a file at a time: the translator sees the whole mail, and writes Polish sentences instead of filling in keys one by one. What the mail class computes still depends on the locale: the subject, the invoice's file name and the prices. They come from `@nestjs/i18n`, which the [internationalization chapter](/application/i18n) covers in depth. Add a catalog for the mail, one per language:

[[CODE:27]]

[[CODE:28]]

Register the catalogs' shape, so keys are checked at compile time, and register `I18nModule` next to `MailModule`:

[[CODE:29]]

[[CODE:30]]

Add the catalogs to the assets in `nest-cli.json` too (`i18n/**/*.json`), as the internationalization chapter shows.

The mail class is a provider, so it injects `I18nService` next to the invoice renderer. `render()` gets a second argument, the render context, whose `locale` is the one passed to `send()`, and the one the mailer hands to the template engine. Its `to` holds the parsed recipients, and is empty for a preview rendered without them:

[[CODE:31]]

The context doesn't change: the same values fill either template. `Key` is `keyof Translations['mail']['orderConfirmation']`, so a misspelled key is a compile error. Prices are formatted for the locale: `$25.98` in English, `25,98 USD` in Polish. The invoice's file name comes from the catalog: `invoice-1001.pdf` or `faktura-1001.pdf`.

> warning **Warning** Pass the locale explicitly. `I18nService` falls back to the current request's locale, and mail is often sent outside the recipient's request: from an outbox handler, as here, or from a request made by someone else, such as an admin. That request's locale is the wrong one.

The outbox handler passes the customer's locale when sending:

[[CODE:32]]

A Polish subject or recipient name can't go into a mail header as it is: headers are ASCII. The mailer encodes non-ASCII header text as RFC 2047 encoded-words, such as `=?UTF-8?Q?Twoje_zam=C3=B3wienie_=231001?=`, and the body as quoted-printable, so every server carries the message unchanged and mail clients show `Twoje zamówienie #1001`.

The preview takes the language from the query string, so both versions can be checked in a browser:

[[CODE:33]]

#### Use another template engine

`FileTemplateEngine` implements `MailTemplateEngine`, an abstract class with one method: `render()` takes the template's name, the context and the locale, and returns the HTML, or an object with `html` and `text`, or a promise of either. Extend it to render with Handlebars, EJS or anything else. An engine for Handlebars templates in `.hbs` files:

[[CODE:34]]

Pass it as `templates` in place of `FileTemplateEngine`: an instance, or the class, which Nest instantiates, so it can inject configuration or other providers. As with the transport, a class goes at the top level of `forRootAsync()`, next to `useFactory`, and the factory returns instances.

The mailer sends the HTML as the engine returns it, so escaping is the engine's job: Handlebars escapes double-braced values, as `FileTemplateEngine` does. `compat: true` makes names inside `#each` fall back to the outer context, so the templates of this tutorial render under Handlebars as they are. Handlebars doesn't know about the `partials/` folder and the layout: register the partials with `Handlebars.registerPartial()`, and render the layout around the mail yourself. For [MJML](https://mjml.io), convert the rendered MJML with `mjml2html()` before returning the HTML. Throw `MailTemplateError` for a template that is missing or broken: it's permanent, so the outbox dead-letters the mail instead of retrying it.

#### Write your own transport

For a provider the package doesn't ship a transport for, extend `MailTransport`. Its `send()` gets the finished message and resolves once the provider has accepted it. A transport for Mailgun, whose `messages.mime` endpoint takes the message as MIME, the way `SesTransport` sends it to SES:

[[CODE:35]]

Pass an instance as `transport`, as with the built-in transports. `send(message, options)` gets:

- **`message`.** A `MailMessage`, validated and frozen: `from`, `to`, `cc`, `bcc`, `replyTo`, `subject`, `html`, `text`, `attachments`, `headers` and `messageId`. `envelope` holds the SMTP envelope, with every recipient once, Bcc included, and `toMime()` returns the message as MIME, without the Bcc header. It's the same object on every attempt.
- **`signal`.** Aborts when the caller cancels the send, such as the outbox relay when a handler outlives its timeout. Stop the request, and reject with `signal.reason`; the mailer doesn't retry an abort.
- **`idempotencyKey`.** The caller's key, the same on every attempt and every redelivery. Send it to a provider that deduplicates requests, as `ResendTransport` does; the `Message-ID` is already derived from it.
- **`attempt`.** 1 for the first attempt, 2 for the first retry.

It resolves to `accepted`, the envelope recipients the provider took (all of them when left out), `providerMessageId` and `response`, which the mailer's `send()` resolves to in turn.

What it throws decides whether the mailer retries. Throw a `MailError` whose `permanent` says whether sending the same message again can succeed: `MailProviderError` for an HTTP API's refusal, which is permanent for a 4xx status other than 408, 409 and 429 unless you pass `permanent` yourself, `MailConnectionError` and `MailTimeoutError` for a failed or slow request. Any other error counts as transient, unless it has `permanent: true` or a 4xx `status`, so a network error from `fetch` is retried. An error with `retryAfterMs` makes the mailer wait at least that long before the next attempt, up to `maxDelay`.

A transport that holds connections or a client implements `close()`, which runs on application shutdown, after the sends in flight have finished.

#### Try it

Apply the migrations, which also add two customers and four products:

[[CODE:36]]

Start the application with the defaults: the file transport, and the relay running. Place an order for Ada:

[[CODE:37]]

The response comes back before any mail is sent. A moment later, the relay's handler renders the mail and the file transport writes it:

[[CODE:38]]

The file is the message exactly as SMTP would transmit it. Its headers and text part:

[[CODE:39]]

A few things to notice:

- The `Message-ID` is derived from the outbox message's id, not random. A redelivery would carry the same one.
- The text part was derived from the HTML, with the link written out.
- The body is quoted-printable, which keeps every line short enough for any mail server: the `=` at the end of the link's first line joins it with the next.

The HTML, the logo and the invoice follow:

[[CODE:40]]

Open the file in a mail client to see the rendered mail. To work on the template, open the preview in a browser instead. The response is the mail's HTML, the template in the layout, with the logo inlined as a `data:` URL (shortened here):

[[CODE:41]]

[[CODE:42]]

Next, order a product that doesn't exist:

[[CODE:43]]

The transaction rolls back, the `order.placed` message with it, and no mail is written.

Finally, see [the customer's language](/application/mail#send-it-in-the-customers-language) at work. Place an order for Zofia, who chose Polish at sign-up:

[[CODE:44]]

[[CODE:45]]

The body comes from `order-confirmation.pl.html`. The Polish subject and Zofia's name reach the file as encoded-words, and her invoice is `faktura-1002.pdf`:

[[CODE:46]]

#### Testing

Replace the transport with `InMemoryMailTransport`. It keeps every mail it receives, and has helpers that find one and read it:

[[CODE:47]]

- **Everything but the network is real.** The mail class renders its templates, with the catalogs and the invoice provider, the outbox and its inbox run, and the message is fully built, headers and attachments included. Only delivery is replaced.
- **The database is PostgreSQL, in-process.** PGlite (`@electric-sql/pglite`, a dev dependency) runs your real migrations, and the test overrides the database `DrizzleModule` registers (its token comes from `getDrizzleToken()`) with it, so the repositories and the outbox store use it. There's no server to start, and each test file gets a fresh database.
- **`assertSent()`** returns the most recent mail that matches, by recipient (`to` matches to, cc and bcc), `subject`, mail class or `template`, or a predicate. When nothing matches, it throws an error that lists what was sent. `assertNotSent()`, `filter()`, `find()` and `mails` cover the rest. The helpers throw plain errors, so they work with any test runner.
- **`link()`** returns the first link in the mail that contains a string or matches a regular expression, as a `URL`. For a password reset or a magic link, that is the whole test: send the mail, then call `mail.link('/reset-password').searchParams.get('token')` and follow the link. Entities are decoded, so the `&amp;` that escaping writes in a query string is `&` again.
- **`failNext()`** makes the next send throw, here a permanent SMTP error, to test the error path.
- **`raw`** is the message as MIME, and `mailer.render()` renders a mail class or a template on its own, for unit tests of a template.

#### Production checklist

- Configure SPF, DKIM and DMARC for the sending domain. HTTP providers sign with DKIM once the domain is verified with them; with SMTP, sign with the `dkim` option or at the relay.
- Keep STARTTLS required, and certificate verification on. For a relay with a private CA, pass `tls.ca` instead of turning verification off.
- Keep credentials in the environment or a secret store. Transports hold them in private fields, and error messages never contain them.
- Send transactional mail after commit, through the outbox, with `retry: false` in the handler and the outbox's retry policy sized to how long your provider can be down.
- Pass `idempotencyKey` for every mail sent from a handler that can run twice.
- Turn permanent mail errors into dead letters, and alert on `dead-lettered` outbox events. A refused address usually means a typo at sign-up, or a mailbox that no longer exists.
- Watch `MailEvents`, or the `nestjs:mail:sent` and `nestjs:mail:failed` diagnostics channels, for delivery failures and slow sends.
- Send through `SmtpTransport` or an HTTP provider's transport in production. `FileMailTransport` writes to the local disk, which a container loses when it restarts or is replaced, and `LogMailTransport` only logs: both are for development, and `InMemoryMailTransport` is for tests. The module warns at startup when one of them runs with `NODE_ENV=production`.
- Keep the outbox's messages in the application's database, through `PostgresOutboxStore` or another registered store, so a queued mail commits with its order and survives a restart. Without a store, the outbox refuses to start with `NODE_ENV=production`, and so does the store while its migrations aren't applied: apply them on deploy, as [the outbox tutorial](/reliability/outbox#keep-messages-in-your-database) shows.
- Ship the templates to `dist` with the CLI's assets, and keep the template cache on in production, which is the default: `cache: false` rereads the files for every mail.
- Don't register development-only routes, such as the preview, in production.
- Use `app.enableShutdownHooks()`, so a deploy waits for the mails in flight and closes SMTP connections.
