### Versioning

> info **Hint** This chapter applies only to HTTP-based applications.

Versioning lets you run **different versions** of your controllers or individual routes within the same application. Applications change frequently, and you often need to introduce breaking changes while still supporting the previous version of the application.

Nest supports four types of versioning:

<table>
  <tr>
    <td><a href='http/versioning#uri-versioning-type'><code>URI Versioning</code></a></td>
    <td>The version is passed within the URI of the request (default)</td>
  </tr>
  <tr>
    <td><a href='http/versioning#header-versioning-type'><code>Header Versioning</code></a></td>
    <td>A custom request header specifies the version</td>
  </tr>
  <tr>
    <td><a href='http/versioning#media-type-versioning-type'><code>Media Type Versioning</code></a></td>
    <td>The <code>Accept</code> header of the request specifies the version</td>
  </tr>
  <tr>
    <td><a href='http/versioning#custom-versioning-type'><code>Custom Versioning</code></a></td>
    <td>Any aspect of the request may specify the version(s). You provide a custom function that extracts the version(s).</td>
  </tr>
</table>

#### URI Versioning Type

URI Versioning uses the version passed within the URI of the request, such as `https://example.com/v1/route` and `https://example.com/v2/route`.

> warning **Notice** With URI Versioning, the version is automatically added to the URI after the <a href="faq/global-prefix">global path prefix</a> (if one exists) and before any controller or route paths.

To enable URI Versioning for your application, do the following:

[[CODE:1]]

> warning **Notice** By default, the version in the URI is automatically prefixed with `v`. To change the prefix, set the `prefix` key to your desired value, or set it to `false` to disable it.

> info **Hint** The `VersioningType` enum is available to use for the `type` property and is imported from the `@nestjs/common` package.

#### Header Versioning Type

Header Versioning uses a custom, user-specified request header whose value specifies the version to use for the request.

To enable **Header Versioning** for your application, do the following:

[[CODE:2]]

The `header` property is the name of the header that contains the version of the request.

> info **Hint** The `VersioningType` enum is available to use for the `type` property and is imported from the `@nestjs/common` package.

#### Media Type Versioning Type

Media Type Versioning uses the `Accept` header of the request to specify the version.

Within the `Accept` header, the version is separated from the media type with a semicolon (`;`), followed by a key-value pair that represents the version to use for the request, such as `Accept: application/json;v=2`. The key is treated as a prefix for the version, so the `key` property must include both the key and the separator.

To enable **Media Type Versioning** for your application, do the following:

[[CODE:3]]

The `key` property is the key and separator of the key-value pair that contains the version. For `Accept: application/json;v=2`, set the `key` property to `v=`.

> info **Hint** The `VersioningType` enum is available to use for the `type` property and is imported from the `@nestjs/common` package.

#### Custom Versioning Type

Custom Versioning uses any aspect of the request to specify the version (or versions). Nest analyzes the incoming request with an `extractor` function that returns a string or an array of strings.

If the requester provides multiple versions, the extractor function can return an array of strings sorted from the highest version to the lowest. Versions are matched to routes in order from highest to lowest.

If the `extractor` returns an empty string or array, no versioned route is matched, so a request to one receives a `404` response status. [`VERSION_NEUTRAL`](/http/versioning#version-neutral) routes still match, as do routes that do not specify a version when no [global default version](/http/versioning#global-default-version) is set.

For example, if an incoming request specifies that it supports versions `1`, `2`, and `3`, the `extractor` **must** return `['3', '2', '1']`. This ensures that the highest possible route version is selected first.

If versions `['3', '2', '1']` are extracted, but routes exist only for versions `2` and `1`, the route that matches version `2` is selected (version `3` is ignored).

> warning **Notice** With the Express adapter, make your `extractor` return a single version (a string, or an array with one element). Selecting the highest matching version from a multi-element array **does not reliably work** in Express due to design limitations of the adapter. If you need that behavior, use the Fastify adapter, which supports both single-version and highest-matching-version selection.

To enable **Custom Versioning** for your application, create an `extractor` function and pass it to `enableVersioning()`:

[[CODE:4]]

#### Usage

Versioning lets you version controllers and individual routes, and also lets certain resources opt out of versioning. Usage is the same regardless of the versioning type your application uses.

> warning **Notice** If versioning is enabled for the application but a controller or route does not specify a version (and no [global default version](/http/versioning#global-default-version) is set), that controller or route behaves like a [`VERSION_NEUTRAL`](/http/versioning#version-neutral) one. With URI Versioning, it is served only at its path without a version (`/cats`, while `/v1/cats` receives a `404` response status). With the other versioning types, it is served whatever version the request contains, or none. A request containing a version that has no corresponding controller or route receives a `404` response status, as does a request without a version when only versioned controllers or routes match its path.

#### Controller versions

A version can be applied to a controller, setting the version for all routes within that controller.

To add a version to a controller, do the following:

[[CODE:5]]

#### Route versions

A version can be applied to an individual route. This version overrides any other version that would affect the route, such as the controller version.

To add a version to an individual route, do the following:

[[CODE:6]]

#### Multiple versions

Multiple versions can be applied to a controller or route. To use multiple versions, set the version to an array:

[[CODE:7]]

#### Version "Neutral"

Some controllers or routes behave the same regardless of the version. To accommodate this, set the version to the `VERSION_NEUTRAL` symbol.

An incoming request is mapped to a `VERSION_NEUTRAL` controller or route regardless of the version specified, including when the request contains no version at all.

> warning **Notice** With URI Versioning, a `VERSION_NEUTRAL` resource does not have the version in its URI.

To add a version-neutral controller or route, do the following:

[[CODE:8]]

> warning **Notice** Register a version-neutral controller or route, or one that does not specify a version when no [global default version](/http/versioning#global-default-version) is set, after any versioned controllers or routes that share its path: list it later in the module's `controllers` array, declare it below them in the same controller, or put it in a module registered after theirs. A module's own controllers are registered before those of the modules it imports, and imported modules in the order of the `imports` array. With the Express adapter and any versioning type other than URI Versioning, routes that share a path are tried in registration order, so a version-neutral route registered first also receives the requests meant for the versioned ones.

#### Global default version

If you don't want to provide a version for each controller or individual route, or you want a specific version to act as the default for every controller or route that doesn't specify one, set the `defaultVersion` as follows:

[[CODE:9]]

#### Middleware versioning

[Middleware](/middleware) can also use versioning metadata to target a specific route version. To do so, set the `version` property in the route object passed to the `MiddlewareConsumer.forRoutes()` method:

[[CODE:10]]

With URI Versioning, the code above applies the `LoggerMiddleware` only to version `'2'` of the `/cats` endpoint, since each version is served at its own path.

> warning **Notice** With Header, Media Type or Custom Versioning, all versions of an endpoint share one path, so the middleware runs for the requests to every version of `/cats`. To run code for a single version with these versioning types, use a guard or an interceptor on that version's controller or route handler instead.
