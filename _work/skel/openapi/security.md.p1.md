### Security

To define which security mechanisms a specific operation uses, apply the `@ApiSecurity()` decorator:

[[CODE:1]]

Before you run your application, add the security definition to your base document using `DocumentBuilder`:

[[CODE:2]]

The most popular authentication techniques (e.g., `basic` and `bearer`) are built in, so you don't have to define their security mechanisms manually as shown above.

#### Basic authentication

To enable basic authentication, use `@ApiBasicAuth()`:

[[CODE:3]]

Before you run your application, add the security definition to your base document using `DocumentBuilder`:

[[CODE:4]]

#### Bearer authentication

To enable bearer authentication, use `@ApiBearerAuth()`:

[[CODE:5]]

Before you run your application, add the security definition to your base document using `DocumentBuilder`:

[[CODE:6]]

#### OAuth2 authentication

To enable OAuth2, use `@ApiOAuth2()`:

[[CODE:7]]

Before you run your application, add the security definition to your base document using `DocumentBuilder`:

[[CODE:8]]

#### Cookie authentication

To enable cookie authentication, use `@ApiCookieAuth()`:

[[CODE:9]]

Before you run your application, add the security definition to your base document using `DocumentBuilder`:

[[CODE:10]]
