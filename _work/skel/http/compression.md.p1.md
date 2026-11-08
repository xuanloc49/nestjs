### Compression

Compression can significantly reduce the size of the response body, which makes a web app faster to load.

For **high-traffic** websites in production, we strongly recommend offloading compression from the application server, typically to a reverse proxy (e.g., Nginx). In that case, don't use compression middleware.

#### Use with Express (default)

Use the [compression](https://github.com/expressjs/compression) middleware package to enable response compression. It supports the gzip, deflate, and Brotli encodings, and picks one based on the request's `Accept-Encoding` header.

First, install the required packages:

[[CODE:1]]

Once the installation is complete, apply the compression middleware globally:

[[CODE:2]]

#### Use with Fastify

If you use the `FastifyAdapter`, use the [@fastify/compress](https://github.com/fastify/fastify-compress) plugin instead:

[[CODE:3]]

Once the installation is complete, register the `@fastify/compress` plugin. It compresses all eligible responses by default.

> warning **Warning** Make sure you pass the `NestFastifyApplication` type when creating the application. Otherwise, the `register()` method isn't available to apply the plugin.

[[CODE:4]]

By default, `@fastify/compress` uses the first encoding the client accepts, in this order of preference: `zstd` (on Node.js versions that support it), `br` (Brotli), `gzip`, and `deflate`. Brotli achieves a high compression ratio, but higher quality levels are slow. The plugin sets the Brotli quality (`BROTLI_PARAM_QUALITY`) to 4 by default instead of zlib's default of 11. You can set it anywhere from 0 (fastest) to 11 (smallest output), trading compression time against response size. Tune this value for your workload. The following example sets the quality explicitly:

[[CODE:5]]

Alternatively, you can restrict `@fastify/compress` to gzip and deflate. Responses may be larger, but they are compressed faster.

To specify the encodings, pass the `encodings` option in the second argument to `app.register()`:

[[CODE:6]]

This configuration tells `@fastify/compress` to use only the gzip and deflate encodings, preferring gzip when the client supports both.
