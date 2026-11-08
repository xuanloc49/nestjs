### Mail

`@nestjs/mail` sends email from a Nest application: mail classes rendered from escaped HTML templates, sent over SMTP or an email API, and read back in tests.

When a customer places an order at an online store for cat food and supplies, they expect a confirmation email within a minute: the items, the total, a link to the order, and the invoice as a PDF. Sending that email well takes more than a call to an SMTP library:

- **The HTML must be safe.** A product name or a customer name ends up in the markup. Unescaped, a name like `<script>` or a stray `&` breaks the layout, or worse.
- **The mail must survive failures.** Mail servers greylist, rate-limit and go down. A send that fails inside the request either fails an order that already committed, or loses the email.
- **Tests must see what was sent.** A test for "the customer gets a confirmation with a link to the order" needs the rendered mail and its links, not a mocked method call.

`@nestjs/mail` covers these. Mail classes are injectable providers that render a subject and a body from typed data, so they can inject your other providers, such as a repository or a PDF renderer. The body comes from an HTML template file, rendered by a small built-in engine that escapes every value it inserts, or by Handlebars or any other engine you plug in. Transports deliver the result: SMTP, written on `node:net` and `node:tls`, and Resend, Postmark, SendGrid and Amazon SES over their HTTP APIs. Tests swap the transport for an in-memory one and read the mails it received. The package has no dependencies beyond Nest itself.

In this tutorial, you'll add order confirmation emails to the store's order API:

- Development writes every mail to an `.eml` file instead of sending it.
- The confirmation is a mail class that renders an HTML template, in a layout that every mail shares, with the invoice attached and the logo inline.
- A preview route shows the mail in a browser without sending it.
- Mail goes out after the order commits, through the outbox, with retries and dead letters.
- Production sends through SMTP or Resend, picked by an environment variable.

#### Installation

To get started, install the required dependency:

[[CODE:1]]

#### Register the mail module

Register `MailModule` in the root module, next to `DrizzleModule`. The mail tutorial needs the database for the customers and their orders, and for the outbox's tables, through which the mail is [sent after the order commits](/application/mail#send-after-the-order-commits). In development, `FileMailTransport` writes each mail to a file in `var/mail` instead of sending it, and `FileTemplateEngine` renders the mail bodies from HTML files in `mail/templates`. The feature modules it imports are built in the following sections:

[[CODE:2]]

- `transport`: how mail leaves the application. Every transport extends the abstract `MailTransport` class, which is also its injection token, so tests replace it with `overrideProvider(MailTransport)`. `FileMailTransport` is for development: open the `.eml` files in any mail client to see exactly what would be sent. It writes to the local disk and reaches nobody, so [in production](/application/mail#send-in-production) the application switches to SMTP or Resend.
- `templates`: renders the mails that name a template. `FileTemplateEngine` reads `.html` files from `dir`, and wraps every mail in the `layout` template, `mail/templates/layout.html`. A relative `dir` is resolved against the working directory; built from `import.meta.dirname`, it points next to the compiled `app.module.js`, wherever the application is started. Compiled templates are cached. With `cache` off, as here outside production, every mail reads the files again, so an edited template shows up in the next mail without a restart.
- `from`: the default sender. A message can override it.

The TypeScript compiler doesn't copy HTML files to `dist`. Add the templates to the [assets](/cli/monorepo#assets) in `nest-cli.json`, so they land in `dist/mail/templates`, next to the compiled `app.module.js`:

[[CODE:3]]

With `watchAssets`, `nest start --watch` copies a template to `dist` whenever you save it.

> info **Hint** The tutorial reads `process.env` directly, to stay short. In an application, load the environment through [`@nestjs/config`](/application/configuration) with a validation schema, so a missing `DATABASE_URL` or `SMTP_URL` stops the application at startup, and read the values from `ConfigService` in the factories.

`MailModule` is global and provides `Mailer`, which sends mail, and `MailEvents`, which reports what was sent and what failed. A missing `transport` or an invalid `from` stops the application at startup, with a message that names the option.

#### Write the order confirmation mail

The mail's body is an HTML template. Values go between double braces, and a block such as `#each` repeats its part of the template for every item of a list:

[[CODE:4]]

Every mail is wrapped in the layout. It places the rendered mail with triple braces around `body`, and includes the signature, a partial that lives in `mail/templates/partials/signature.html`:

[[CODE:5]]

[[CODE:6]]

A mail class implements `Mailable<TData>`. Its `render()` method gets the data and returns the subject, the template's name and its context, the values the template reads:

[[CODE:7]]

The template is logic-less. It has values, `#if`, `#unless` and `#each` blocks, partials and comments, but no helpers and no expressions: what needs code, such as formatting a price or building a link, happens in the mail class, in TypeScript, where it's typed and tested. The syntax is a subset of Handlebars (see [Template syntax](/application/mail#template-syntax)), so the templates move to [another engine](/application/mail#use-another-template-engine) as they are.

Double braces escape the value. A product named `Feather wand toy <limited edition>` becomes `Feather wand toy &lt;limited edition&gt;`, and the customer's name can't inject markup. Two rules make it hard to get wrong:

- Escaping protects element content and quoted attribute values, so those are the only places a double-braced value may go. A value inside a tag anywhere else is a compile error: `href=` followed directly by the value, or a value standing between attributes. Escaping can't protect either place (unquoted, a space in the value would start a new attribute). Quote attribute values, as the link above does.
- Triple braces insert a value as it is, for HTML you produced yourself. In this tutorial, only the layout's `body` needs them.

A missing value renders as nothing, as in Handlebars. Inside `#each`, `this` is the item, `@index`, `@first` and `@last` describe its position, and a name the item doesn't have is looked up in the template's context, so a row can show a value from outside the list. A template that doesn't compile fails the mail with a permanent `MailTemplateError`, which names the file and the position:

[[CODE:8]]

There is no text template. The mailer derives the plain-text part from the HTML: paragraphs, table rows, and links as `View your order (https://shop.example.com/orders/…)`. Mail clients that don't show HTML, and spam filters, read that part. To write it yourself, add `order-confirmation.txt` next to the HTML: the engine renders it as the text part, with the same syntax, without escaping.

Register the class as a provider, like any other injectable:

[[CODE:9]]

Then send it when an order is placed. `mailer.send()` takes the mail class and the recipient, and the type of `data` comes from the class's `render()`:

[[CODE:10]]

The recipient is an object with a `name` and an `address`, so a name with a comma or quotes stays one display name. A string works too, as in `'Ada Lovelace <ada@example.com>'`, but a string must hold exactly one address: a comma-separated list throws, so a name typed by a user can never add a recipient. Lists of recipients are arrays.

Place an order and a file appears in `var/mail`. This works, but it sends the mail from the request, after the commit. [Send after the order commits](/application/mail#send-after-the-order-commits) explains why that isn't good enough, and fixes it.

**Mails written inline.** A mail small enough to write in TypeScript doesn't need a template file. `render()` returns `html` in place of `template` and `context`, built with the `html` tagged template:

[[CODE:11]]

`html` escapes every value you interpolate, by the same rules as a template: a value inside a tag must be in a quoted attribute value, or it throws. Nested `html` templates and arrays of them, like the table rows, are inserted as they are, and `unsafeHtml()` inserts HTML you produced yourself; the name is the warning. `mailer.send()` takes `html` too, for a message sent without a mail class.

#### Attach the invoice and preview the mail

The invoice is a PDF, rendered by a small provider. It writes the PDF by hand with a built-in font, to keep the example free of dependencies. A real application uses a PDF library or a rendering service here. The mail only needs the bytes:

[[CODE:12]]

`render()` returns attachments along with the template. The invoice is a regular attachment. The logo is an inline image: its `cid` makes it part of the HTML, which references it as `cid:logo@example.com`. The logo heads every mail, so the reference goes in the layout:

[[CODE:13]]

The mail class attaches the logo and the invoice:

[[CODE:14]]

Every mail rendered in this layout attaches the logo the same way, or its header shows a broken image. The template gets one more line after the link, `<p>Your invoice is attached.</p>`.

An attachment's content is a `Buffer`, a string, or a stream, or it's read from a local `path` when the mail is sent. The content type comes from the file name, and a non-ASCII file name is encoded so that every mail client shows it. The mailer arranges the parts the way mail clients expect: the logo sits next to the HTML, so a client that shows the text version doesn't list it as an attachment.

> warning **Warning** Never build an attachment `path` from user input. The file at that path is attached, whatever it is. URLs are refused, not fetched.

While you work on the template, you don't want to place an order for every change. `mailer.render()` renders a mail class without sending it. A development-only route shows the result in the browser. With the template cache off, it shows an edited template on the next refresh:

[[CODE:15]]

`render()` returns the finished `MailMessage`: the subject, the HTML and the derived text, the attachments, and `toMime()` for the raw message. Recipients are optional here. `render()` also takes a message written inline, such as a subject, a `template` and its `context`, to preview a template without a mail class. Register the controller only outside production:

[[CODE:16]]

#### Send after the order commits

[Write the order confirmation mail](/application/mail#write-the-order-confirmation-mail) sends the mail from the request, after the order commits. Three things go wrong there:

- **A crash between the commit and the send loses the mail.** A deploy that restarts the process at the wrong moment leaves a paid order without a confirmation.
- **A mail server outage fails a request that already succeeded.** The order is saved, but the customer sees a 500 and may order again.
- **The customer waits for the mail server.** An SMTP exchange takes hundreds of milliseconds, and a slow server takes the request's time with it.

This is the dual-write problem from the [outbox tutorial](/reliability/outbox), and the outbox (`@nestjs/outbox`, installed and set up in that tutorial) fixes it. The order and an `order.placed` message commit in one transaction, and a relay hands the message to a handler that sends the mail. If the send fails, the relay retries it with backoff, and it moves messages that never succeed to the dead-letter table. The outbox keeps its messages in the application's PostgreSQL database, next to the orders, through its store, `PostgresOutboxStore` from `@nestjs/outbox/postgres`, on the database that [`@nestjs/drizzle`](/data/drizzle) registers. The store creates its tables, in a schema of their own, when the application starts; [Keep messages in your database](/reliability/outbox#keep-messages-in-your-database) in the outbox tutorial covers them, and how to apply their migrations in production.

This section shows the order transaction twice: first with Drizzle, which is the tutorial's path, and then, under "With TypeORM" at the end of the section, the same transaction for an application whose ORM is TypeORM. Take one of the two.

Register `OutboxModule`, and the store as a provider of the root module: a factory that injects the Drizzle database and the `OutboxStorage` registry, which the store registers itself with. Without it, the outbox would keep its messages in memory, and lose them on restart:

[[CODE:17]]

`OrdersService` adds the message instead of sending the mail, with Drizzle's `tx`, so the message commits or rolls back with the order:

[[CODE:18]]

The handler sends the mail:

[[CODE:19]]

Register the handler in `NotificationsModule`, which imports `CustomersModule` for the repository:

[[CODE:20]]

Each option of the `send()` call has a job:

- **`idempotencyKey`.** The outbox delivers at least once: a relay that crashes after sending, before recording it, sends again. The key identifies the mail across those deliveries. The `Message-ID` header is derived from it, so over SMTP a duplicate carries the same id, which Gmail and other receivers use to drop it. `ResendTransport` sends the key as Resend's `Idempotency-Key`, and Resend refuses the duplicate for 24 hours. Postmark, SendGrid and SES assign their own `Message-ID` and have no idempotency keys, so with them a redelivery can reach the customer twice.
- **`signal`.** The relay aborts it when the handler outlives `publishTimeout`. The mailer stops the SMTP exchange or the HTTP request.
- **`retry: false`.** The mailer retries transient failures three times by default, with backoff. Here the outbox already retries, over minutes instead of seconds, so the mailer makes one attempt per delivery. Retries at both layers would multiply.

Every error the package throws extends `MailError`, and its `permanent` flag says whether sending the same message again can succeed. A 4xx SMTP reply (greylisting, a full mailbox), a 429 from an HTTP provider, a timeout or a dropped connection is transient: the handler rethrows it, and the outbox retries. A 5xx reply, such as `550 5.1.1 User unknown`, is permanent: the handler throws `NonRetryableMessageError`, and the outbox dead-letters the message at once instead of trying ten more times.

When SMTP refuses one of several recipients, the transaction is reset before the message is sent, so an error always means nobody received it, and the outbox's retry can't deliver twice. The one exception: the connection drops after the message was transmitted, before the server answers. The mailer can't know whether the server kept it, reports a transient error, and the retry sends it again, with the same `Message-ID`.

**With TypeORM.** The same order transaction for an application whose ORM is TypeORM. Drizzle stays the tutorial's path: take this code instead of the Drizzle code above, not next to it. The outbox keeps its messages through the same store, on TypeORM's data source, as the outbox tutorial's [Keep messages in your database](/reliability/outbox#keep-messages-in-your-database) shows. The example application keeps this version in `src/typeorm`, next to the tutorial's Drizzle code, with the customers, products and orders as entities.

`TypeOrmModule` takes the place of `DrizzleModule` in the root module, with the options the TypeORM CLI shares, and the store's factory injects its `DataSource`, through `fromTypeOrm()`:

[[CODE:21]]

`OrdersService` opens its transaction with the data source, and passes the transaction's entity manager to `outbox.add()`, next to its own writes. The outbox's type parameter is TypeORM's `EntityManager`:

[[CODE:22]]

`OrderEntity` declares `number` as an identity column (`generated: 'identity'`), so `manager.insert()` returns the number the database assigned in `generatedMaps`. An entity can't state where the sequence starts, so the example's seed migration restarts it at 1001, next to the customers and products it inserts. The handler and `NotificationsModule` stay as they are; `CustomersRepository` reads the customer with TypeORM, like the rest of the application.

#### Send in production

Development writes files, to a local disk that a container loses when it's replaced; production needs a real transport. Pick it from the environment, so the same build runs everywhere:

[[CODE:23]]

Build the transport in `forRootAsync()`. The factory runs at startup, so a typo in `MAIL_TRANSPORT` or a missing `SMTP_URL` stops the application there instead of failing the first mail:

[[CODE:24]]

**SMTP.** `SmtpTransport` speaks SMTP itself, on `node:net` and `node:tls`:

- **Encryption.** On port 587 it upgrades with STARTTLS, and a server that doesn't offer STARTTLS is refused rather than sent to in plaintext. `startTls: 'opportunistic'`, the default for localhost, upgrades only when the server offers it, and `'never'` stays in plaintext, for a relay on a trusted network. On port 465 (`smtps://`) it uses TLS from the first byte. Certificates are verified against the host name; `tls.ca` adds a private CA. Credentials are never sent over an unencrypted connection, except to localhost.
- **Authentication.** It uses AUTH PLAIN or LOGIN, whichever the server offers, and `authMethod` forces one. For Gmail and Microsoft 365, pass an OAuth access token as `accessToken` in `auth` for XOAUTH2. OAuth access tokens expire, typically after an hour, so `accessToken` can also be a function that returns one, or a promise of one: it's called for every new connection, and can fetch a fresh token. `name` sets the name the transport introduces itself with in `EHLO`; the default is the machine's host name when it's fully qualified, else its IP address.
- **Pooling.** `pool: true` keeps up to five connections open and reuses them, instead of a TCP and TLS handshake per mail. An object sets the limits: `maxConnections` (default 5; further sends wait for a free connection), `maxMessages` (default 100, after which a connection is replaced) and `idleTimeout` (default `'30s'`, after which an idle connection is closed). Every connection says `QUIT` when the application shuts down.
- **Replies.** A 4xx reply is a transient `MailSmtpError`, a 5xx reply a permanent one. Both carry the reply `code`, the enhanced code (such as `5.1.1`) and the server's text.

To sign mail with DKIM when your SMTP server doesn't, add `dkim` with the domain (`domainName`), the selector (`keySelector`) and the private key (`privateKey`, PEM or a `KeyObject`). An RSA key signs with `rsa-sha256`, an Ed25519 key with `ed25519-sha256` (RFC 8463); not every receiver verifies Ed25519 signatures yet, and the transport signs with one key, so RSA is the safe choice unless you know your recipients' servers do. The signature covers From, Reply-To, To, Cc, Subject, Date, Message-ID and the MIME headers, plus the message's custom headers; `dkim.headers` replaces that list. From is always signed, and listed once more than it occurs in the message, so a second From added below the signature breaks it. HTTP providers sign with your verified domain themselves.

**HTTP providers.** `ResendTransport`, `PostmarkTransport`, `SendGridTransport` and `SesTransport` call the providers' APIs with `fetch`, and need no SDK. The `fetch` option replaces the global one, to go through a proxy or to stub the API in a test. `SesTransport` signs its requests with AWS Signature Version 4, and accepts the AWS SDK's credential providers, such as instance roles, as `credentials`. Of the four, only Resend supports idempotency keys. Resend and SendGrid need at least one `to` recipient: a mail with only `cc` or `bcc` fails with `MailMessageError` before the request.

**Internationalized addresses.** A domain with non-ASCII characters (`zoë@kočka.example`) is converted to its ASCII form (IDNA, `xn--...`) for every transport, so no server has to support it. A non-ASCII local part, before the `@`, can't be converted: over SMTP it needs the server's SMTPUTF8 extension. `SmtpTransport` uses SMTPUTF8 when the server offers it, and otherwise fails with a permanent `MailConnectionError` before sending anything: `The SMTP server ... doesn't support SMTPUTF8, which an address with non-ASCII characters needs`. The HTTP providers get the address as it is, and whether they accept it is up to the provider.

Use `app.enableShutdownHooks()` in `main.ts`, so a deploy lets the relay finish the mails it is sending, and closes the SMTP pool afterwards.
