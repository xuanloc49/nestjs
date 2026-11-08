### Raw body

One of the most common reasons to access the raw request body is webhook signature verification. Verifying a webhook signature usually requires the unparsed request body to calculate an HMAC hash.

> warning **Warning** This feature works only if the built-in global body parser middleware is enabled, i.e., you must not pass `bodyParser: false` when creating the application.

#### Use with Express

First, enable the option when creating your Nest Express application:

[[CODE:1]]

To access the raw request body in a controller, type the request with the `RawBodyRequest` convenience interface, which exposes a `rawBody` field:

[[CODE:2]]

#### Registering a different parser

By default, only the `json` and `urlencoded` parsers are registered. To use a different parser, register it explicitly.

For example, to register a `text` parser:

[[CODE:3]]

> warning **Warning** Make sure you pass the correct application type to the `NestFactory.create()` call. For Express applications, the correct type is `NestExpressApplication`; otherwise, the `useBodyParser()` method won't be found.

#### Body parser size limit

If your application needs to parse bodies larger than the Express default of `100kb`, raise the limit:

[[CODE:4]]

The `useBodyParser()` method respects the `rawBody` option passed in the application options.

#### Use with Fastify

First, enable the option when creating your Nest Fastify application:

[[CODE:5]]

To access the raw request body in a controller, type the request with the `RawBodyRequest` convenience interface, which exposes a `rawBody` field:

[[CODE:6]]

#### Registering a different parser

By default, only the `application/json` and `application/x-www-form-urlencoded` parsers are registered. To use a different parser, register it explicitly.

For example, to register a `text/plain` parser:

[[CODE:7]]

> warning **Warning** Make sure you pass the correct application type to the `NestFactory.create()` call. For Fastify applications, the correct type is `NestFastifyApplication`; otherwise, the `useBodyParser()` method won't be found.

#### Body parser size limit

If your application needs to parse bodies larger than the Fastify default of 1 MiB, raise the limit:

[[CODE:8]]

The `useBodyParser()` method respects the `rawBody` option passed in the application options.
