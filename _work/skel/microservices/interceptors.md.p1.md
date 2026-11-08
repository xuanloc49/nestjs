### Interceptors

Microservice interceptors work the same way as [regular interceptors](/interceptors). The following example uses a manually instantiated method-scoped interceptor. As with HTTP-based applications, you can also use controller-scoped interceptors (i.e., prefix the controller class with a `@UseInterceptors()` decorator).

[[CODE:1]]

> info **Hint** Global interceptors registered on the main HTTP application don't apply to microservices connected to a [hybrid application](/faq/hybrid-application) unless you set the `inheritAppConfig` option. See [sharing configuration](/faq/hybrid-application#sharing-configuration).
