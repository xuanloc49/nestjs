### HTTPS

To create an application that uses the HTTPS protocol, set the `httpsOptions` property in the options object passed to the `NestFactory.create()` method:

[[CODE:1]]

If you use the `FastifyAdapter`, create the application as follows:

[[CODE:2]]

#### Multiple simultaneous servers

The following recipe shows how to create a Nest application that listens on multiple ports simultaneously (for example, on an HTTP port and an HTTPS port):

[[CODE:3]]

Because we created the servers ourselves with `http.createServer()` and `https.createServer()`, Nest doesn't close them when you call `app.close()` or when the process receives a termination signal. You need to close them yourself, for example with a provider that implements the `OnApplicationShutdown` hook:

[[CODE:4]]

> info **Hint** The `ExpressAdapter` is imported from the `@nestjs/platform-express` package. The `http` and `https` modules are built into Node.js.

> warning **Warning** This recipe does not work with [GraphQL subscriptions](/graphql/subscriptions).
