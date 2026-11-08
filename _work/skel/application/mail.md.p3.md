#### Reference

##### Module options

`MailModule.forRoot()` takes these options, and a `forRootAsync()` factory returns them. With `useClass` or `useExisting` in place of `useFactory`, the class implements `MailOptionsFactory`, whose `createMailOptions()` returns them. `transport`, `templates`, `imports` and `isGlobal` also sit next to `useFactory`, `useClass` or `useExisting` in `forRootAsync()`. The resolved options are provided under the `MAIL_MODULE_OPTIONS` token.

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `transport` | `MailTransport` instance or class | none (required) | How mail leaves the application. A class is instantiated by Nest, so it can inject configuration. See [Send in production](/application/mail#send-in-production). |
| `templates` | `MailTemplateEngine` instance or class | none | Renders mail that names a `template`: `FileTemplateEngine`, or [your own](/application/mail#use-another-template-engine). A class is instantiated by Nest. Without one, a mail with a template fails with `MailTemplateError`. |
| `from` | address | none | The default sender. A message without a sender fails with `MailMessageError`. |
| `replyTo` | address or array | none | The default Reply-To. |
| `headers` | `Record<string, string>` | none | Added to every message. A message's own headers win. |
| `retry` | number, `false` or retry options | 3 attempts | Attempts per send, with backoff from `1s` doubling to `30s`, full jitter. `false` makes one attempt. See [Send after the order commits](/application/mail#send-after-the-order-commits). |
| `imports` | modules | none | Modules whose exports a transport or template engine class injects. |
| `isGlobal` | `boolean` | `true` | Registers `Mailer`, `MailEvents`, `MailTransport` and `MailTemplateEngine` globally. |

The retry options are `attempts` (total, including the first), `backoff` (an object with `delay`, `factor`, `maxDelay` and `jitter`, or a function of the attempt) and `retryIf` (can only narrow which transient errors are retried). When an HTTP provider answers with a `Retry-After` header, typically with a 429 or a 503, the error keeps it as `retryAfterMs`, and the mailer waits at least that long before the next attempt, up to `maxDelay` (`30s` with a backoff function). The `signal` still ends the wait. SMTP replies have no `Retry-After`, and an outbox handler with `retry: false` leaves the wait to the outbox's backoff.

##### Template engine

`FileTemplateEngine` takes:

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `dir` | `string` | none (required) | The directory of the templates, with partials in its `partials/` folder. A relative path is resolved against the working directory. |
| `layout` | `string` | none | A template that wraps every mail's HTML, placing it with triple braces around `body`. A `.txt` version, if there is one, wraps the text. |
| `cache` | `boolean` | `true` | Keeps compiled templates, and which files exist, in memory. `false` reads the files for every mail, to see edits in development. |

`template: 'order-confirmation'` with the locale `pt-BR` renders the first file that exists of `order-confirmation.pt-BR.html`, `order-confirmation.pt.html` and `order-confirmation.html`, and the first of the same names with `.txt` as the text part, if any. Template names are letters, digits, `-` and `_`, in folders separated by `/`. Other names, and locales that aren't language tags, fail with `MailTemplateError`, so neither can reach a file outside `dir`.

##### Template syntax

The syntax is a subset of Handlebars:

<table>
  <tr>
    <th>Syntax</th>
    <th>Renders</th>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }} customer.name {{ '}' }}{{ '}' }}</code></td>
    <td>The value, HTML-escaped. Paths use dots, and <code>items.0</code> is an array's first item. A missing value renders as nothing. In a <code>.txt</code> template, the value as it is.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}{{ '{' }} body {{ '}' }}{{ '}' }}{{ '}' }}</code></td>
    <td>The value as it is, for HTML you produced yourself. HTML built with the <code>html</code> tag is inserted as it is between double braces too.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#if paid{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}else{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/if{{ '}' }}{{ '}' }}</code></td>
    <td>The first part when the value is truthy, else the <code>else</code> part, which is optional. <code>false</code>, <code>0</code>, an empty string, an empty list and a missing value are falsy. <code>{{ '{' }}{{ '{' }}else if pending{{ '}' }}{{ '}' }}</code> chains another condition.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#unless paid{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/unless{{ '}' }}{{ '}' }}</code></td>
    <td>The opposite of <code>#if</code>, with an optional <code>else</code> part.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#each items{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}else{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/each{{ '}' }}{{ '}' }}</code></td>
    <td>The first part once for every item of a list, or every value of an object; the <code>else</code> part for an empty or missing list.</td>
  </tr>
  <tr>
    <td><code>this, &#64;index, &#64;first, &#64;last, &#64;key</code></td>
    <td>Inside <code>#each</code>: the item, its position from 0, whether it's the first or the last, and an object's key. A name the item doesn't have is looked up in the outer contexts.</td>
  </tr>
  <tr>
    <td><code>../number, &#64;root.shop</code></td>
    <td>The context outside the current <code>#each</code>, and the template's context.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}> signature{{ '}' }}{{ '}' }}</code></td>
    <td>The partial <code>partials/signature.html</code> (<code>.txt</code> in a text template), in the mail's locale, with the context where it's included.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}! note {{ '}' }}{{ '}' }}, {{ '{' }}{{ '{' }}!-- note --{{ '}' }}{{ '}' }}</code></td>
    <td>Comments, left out of the output. The second form may contain double braces.</td>
  </tr>
  <tr>
    <td><code>\{{ '{' }}{{ '{' }}</code></td>
    <td>Literal double braces.</td>
  </tr>
</table>

There are no helpers and no expressions. Values are read from the context's own properties, never from a prototype, and functions aren't called. Anything else between double braces, a block that is never closed, and a double-braced value inside a tag but outside a quoted attribute value fail with `MailTemplateError`, which has the `file`, the `line` and the `column`.

##### Send options

`mailer.send(MailClass, options)` and `mailer.send(message)` take:

| Option | Description |
| --- | --- |
| `to`, `cc`, `bcc` | One address or an array. An address is a string holding exactly one address, or an object with `name` and `address`. `bcc` goes only into the SMTP envelope. |
| `data` | The mail class's data, typed from its `render()`. |
| `locale` | Passed to `render()` in the render context, and to the template engine, which picks the template for it. See [Send it in the customer's language](/application/mail#send-it-in-the-customers-language). |
| `from`, `replyTo` | Override the module's defaults. |
| `subject`, `html`, `text` | The content, for a message written inline. `text` is derived from `html` when omitted. |
| `template`, `context` | The template the body is rendered from, and the values it reads, in place of `html` and `text`. A mail class's `render()` returns them the same way. |
| `attachments` | Each has `filename`, `content` (a `Buffer`, string or stream) or a local `path`, and optionally `contentType` and `cid`. See [Attach the invoice and preview the mail](/application/mail#attach-the-invoice-and-preview-the-mail). |
| `headers` | Custom headers, such as `List-Unsubscribe`. |
| `retry` | Overrides the module's `retry` for this send. |
| `signal` | An `AbortSignal` that stops the send and any wait between attempts. |
| `idempotencyKey` | Identifies the mail across redeliveries. The `Message-ID` is derived from it. |

`mailer.render(MailClass, options)` and `mailer.render(message)` take the same without the delivery options, and resolve to the `MailMessage`, which records its `template` and `locale`. `send()` resolves to `messageId`, `providerMessageId` (when the provider has one), `accepted` (the accepted envelope recipients), `response` (the final SMTP reply) and `attempts`.

##### Transports

| Transport | Options | Idempotency key |
| --- | --- | --- |
| `SmtpTransport` | `url` or `host`, `port`, `secure`, `startTls` (`required`, `opportunistic` or `never`; `required` by default, `opportunistic` for localhost), `auth` (`user` with `pass` or `accessToken`), `authMethod` (`PLAIN`, `LOGIN` or `XOAUTH2`), `name`, `tls`, `pool`, `timeouts`, `dkim` (`domainName`, `keySelector`, `privateKey`, `headers`) | derived `Message-ID` only |
| `ResendTransport` | `apiKey`, `baseUrl`, `timeout`, `fetch` | `Idempotency-Key`, 24 hours |
| `PostmarkTransport` | `serverToken`, `messageStream` (default `outbound`), `baseUrl`, `timeout`, `fetch` | none |
| `SendGridTransport` | `apiKey`, `baseUrl`, `timeout`, `fetch` | none |
| `SesTransport` | `region`, `credentials`, `configurationSetName`, `endpoint`, `timeout`, `fetch` | none |
| `FileMailTransport` | `directory`, `log` | development only |
| `LogMailTransport` | `body`, `logger` | development only |
| `InMemoryMailTransport` | none | tests only, see [Testing](/application/mail#testing) |

`InMemoryMailTransport.mails` lists every mail received, oldest first, as a `SentMail`, which `filter()`, `find()` and `assertSent()` return too. A `SentMail` has the message's `messageId`, `from`, `to`, `cc`, `bcc`, `subject`, `html`, `text`, `attachments`, `headers`, `mail` (the mail class), `template` and `locale`, plus `sentAt` (when the transport received it), `raw` (the MIME source), `links` (every link, from the HTML, then the ones only the text part has), `link()`, `attachment()` and `message`, the `MailMessage` itself. `clear()` forgets them all.

With `pool: true`, `SmtpTransport` keeps up to 5 connections, sends up to 100 messages per connection, and closes a connection after 30 seconds idle; an object with `maxConnections`, `maxMessages` and `idleTimeout` as `pool` changes those limits. Its default timeouts are `30s` to connect, `30s` for the greeting, `1m` per command and `5m` for the data. HTTP providers time out after `30s` per request.

##### Events

`MailEvents.events$` emits one event per send, after its retries. Each event is also published on a `node:diagnostics_channel` channel.

| Event type | Channel | When | Payload |
| --- | --- | --- | --- |
| `sent` | `nestjs:mail:sent` | The transport accepted the message. | `messageId`, `mail`, `recipients`, `subject`, `transport`, `attempts`, `durationMs`, `providerMessageId` |
| `failed` | `nestjs:mail:failed` | The send failed after its retries, or its `signal` aborted before the first attempt (`attempts` is 0). | The same fields without `providerMessageId`, plus `error` and `permanent` |

A message that fails validation throws before any event.

##### Errors

Every error extends `MailError`, which has `permanent` (whether sending the same message again can't succeed) and `code` (the SMTP reply code or the provider's HTTP status). The mailer retries only errors that aren't permanent. See [Send after the order commits](/application/mail#send-after-the-order-commits).

| Error | When | Permanent |
| --- | --- | --- |
| `MailMessageError` | The message is invalid, before anything is sent. `field` names the field, `status` is 400. | Yes |
| `MailConnectionError` | DNS, a refused or reset connection, TLS or a certificate. `cause` holds the socket error. | No, except configuration problems such as a server without STARTTLS when it's required |
| `MailTimeoutError` | A phase outlived its timeout. Has `phase` and `timeoutMs`. | No |
| `MailSmtpError` | An SMTP error reply. Has `code`, `enhancedCode`, `command` and `response`. | For 5xx replies |
| `MailRecipientsRejectedError` | The server refused one or more recipients, and nothing was sent. `rejected` lists them. Extends `MailSmtpError`. | When any refusal is 5xx |
| `MailTemplateError` | A template is missing or doesn't compile, or a mail names a template without a template engine. Has `template`, and `file`, `line` and `column` for a problem in a file. | Yes |
| `MailProviderError` | An HTTP provider refused the request. Has `code` (the HTTP status), `provider`, `providerCode`, and `retryAfterMs` when the response had a valid `Retry-After`. | For 4xx except 408, 409 and 429 |
