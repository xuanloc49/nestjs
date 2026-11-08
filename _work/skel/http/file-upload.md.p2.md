#### Fastify

Starting with NestJS v12.1, applications running on the `FastifyAdapter` (see [Fastify adapter](/http/performance#fastify-adapter)) can handle file uploads with the same API, backed by the [@fastify/multipart](https://github.com/fastify/fastify-multipart) plugin instead of Multer. The interceptors described in this chapter take the same arguments and options, populate the request in the same way, and fail with the same error responses, while `@UploadedFile()`, `@UploadedFiles()`, `ParseFilePipe`, `ParseFilePipeBuilder` and the built-in file validators work unchanged.

First, install the plugin:

[[CODE:23]]

There is no need to register it: the `FastifyAdapter` registers the plugin automatically as soon as your application uses one of the upload interceptors (in applications that don't, it is not registered at all). If the package is not installed, the application fails to start with an error naming it.

Next, import the interceptors from `@nestjs/platform-fastify/multipart` instead of `@nestjs/platform-express`. The rest of the controller stays the same, except that files are typed as `UploadedMultipartFile`:

[[CODE:24]]

> info **Hint** Everything exported from `@nestjs/platform-fastify/multipart` is also re-exported from the `@nestjs/platform-fastify` package root. The interceptors only work with the `FastifyAdapter`: with the `ExpressAdapter`, the application fails to start, so keep importing them from `@nestjs/platform-express` there.

The table below maps the Express API to its Fastify counterpart:

| `@nestjs/platform-express`                                                                                            | `@nestjs/platform-fastify/multipart`                                                           |
| --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `FileInterceptor()`, `FilesInterceptor()`, `FileFieldsInterceptor()`, `AnyFilesInterceptor()`, `NoFilesInterceptor()` | Same names, arguments and options                                                              |
| `MulterOptions`                                                                                                       | `MultipartOptions`                                                                             |
| `MulterModule`, `MulterOptionsFactory`, `createMulterOptions()`                                                       | `MultipartModule`, `MultipartOptionsFactory`, `createMultipartOptions()`                       |
| `Express.Multer.File`                                                                                                 | `UploadedMultipartFile`                                                                        |
| `memoryStorage()` and `diskStorage()` from the `multer` package                                                       | `memoryStorage()` and `diskStorage()`                                                          |
| -                                                                                                                     | `FileStreamInterceptor()` (see [Streaming uploads](/http/file-upload#streaming-uploads)) |

The interceptor options are the ones Multer accepts: `dest`, `storage`, `limits` (an object, or a function that receives the request and returns one), `fileFilter`, `preservePath` and `defParamCharset`. Uploaded files are exposed as `req.file` or `req.files` and text fields as `req.body`, exactly as with Multer. `UploadedMultipartFile` has the same shape as `Express.Multer.File`, so you don't need the `@types/multer` package.

`MultipartModule` sets default options for the upload interceptors of the module that imports it, just like `MulterModule`. Its `registerAsync()` method accepts `useFactory` (with `imports` and `inject`), `useClass` and `useExisting`.

[[CODE:25]]

##### Storage

As with Multer, files are kept in memory (in `file.buffer`) unless you set the `dest` or `storage` option. `dest` writes each file to the given folder under a random name, and the `diskStorage()` function lets you choose the folder and the file name. Disk storage sets `destination`, `filename` and `path` on the file instead of `buffer`.

[[CODE:26]]

Storage engines follow Multer's storage engine contract (`_handleFile()` and `_removeFile()`), so Multer's own `multer.diskStorage()` and third-party Multer storage engines can be passed as `storage` unchanged.

##### Limits

`@fastify/multipart` applies stricter defaults than Multer. Unless configured otherwise, the maximum file size (`fileSize`) is the Fastify `bodyLimit` (1 MiB by default) and the maximum number of parts (`parts`) is 1000, whereas Multer limits neither. Larger files are rejected with a `413 File too large` response. You can raise these limits:

- for a single route, with the `limits` option of the interceptor
- for a module, with `MultipartModule.register()` or `registerAsync()`
- for the whole application, with the `multipart` option of the `FastifyAdapter`, which passes options to the plugin itself:

[[CODE:27]]

Limits set on a route are merged over the ones set with `MultipartModule` key by key, and both are merged over the application-wide ones. The only exception is `fieldNameSize`, which the interceptors don't read from the plugin options - set it on the route or with `MultipartModule`.

##### Plugin registration

The `multipart` option of the `FastifyAdapter` controls how the `@fastify/multipart` plugin is registered:

- not set (default): the adapter registers the plugin when an upload interceptor is used, unless it has been registered already
- an options object (`FastifyMultipartOptions`, e.g., `limits`): the adapter registers the plugin with these options when the application initializes
- `true`: same as above, with the plugin's default options
- `false`: the adapter never registers the plugin, for applications that register it themselves or parse multipart requests with another library (the upload interceptors still require `@fastify/multipart`, and the application fails to start if it is not registered)

Set the option to `true` (or pass an options object) when an upload interceptor is instantiated outside the dependency injection system, for example `new (FileInterceptor('file'))()` passed to `app.useGlobalInterceptors()`, as it doesn't trigger the automatic registration. The same applies when upload interceptors are only used in [lazy-loaded modules](/fundamentals/lazy-loading-modules) that are loaded after the application has started, since plugins can no longer be registered at that point.

If you prefer to register the plugin yourself, pass it to `app.register()`, either before or after `app.init()`. The adapter takes this registration over, so the plugin is registered only once, and your options take precedence over the ones passed through the `multipart` option:

[[CODE:28]]

> warning **Warning** Registering `@fastify/multipart` directly on the Fastify instance (`app.getHttpAdapter().getInstance().register(multipart)`), or passing a dynamic `import()` of it to `app.register()`, only works before `app.init()` (which `app.listen()` calls for you). After that, the adapter has already registered the plugin for your upload interceptors, and Fastify fails with an `FST_ERR_DEC_ALREADY_PRESENT` error. Use `app.register(multipart)` or the `multipart` option instead, or set the option to `false` to manage the plugin yourself.

##### Streaming uploads

The interceptors described so far store every file (in memory or on disk) before the route handler runs. To process a file as it arrives instead, for example to pipe a large upload to its final destination, use `FileStreamInterceptor()`, which is available on Fastify only. It takes the name of the field that holds the file and an optional options object (the same as for the other interceptors, except `dest` and `storage`), and hands the route handler a file with a `stream` property in place of `buffer`:

[[CODE:29]]

Since the file is never buffered, a few rules apply:

- Text fields must precede the file in the form. The ones sent before it are available in `req.body` (`@Body()`), while the parts that follow the file are not parsed.
- Only one file is accepted, in the given field. A file in any other field fails the request with a `400 Unexpected file field` response.
- The file size is not known up front, so `MaxFileSizeValidator` doesn't apply, and neither does the magic number check of `FileTypeValidator` (set its `skipMagicNumbersValidation` option to `true` to compare the client-provided mime type only). The `fileSize` limit is still enforced: once it is exceeded, the stream errors with a `PayloadTooLargeException`.
- Whatever the route handler leaves unread is discarded before the response is sent, so that the client can finish uploading. When the handler returns a `StreamableFile` (which may be the upload itself), the rest of the upload is discarded once the response has been sent instead. For this reason, a handler that responds with a `StreamableFile` of something other than the upload should read the upload first - otherwise, a client that is still uploading over a connection that is not kept alive may fail with an `EPIPE` or `ECONNRESET` error.

##### Differences from Multer

Besides the [default limits](/http/file-upload#limits), the Fastify interceptors differ from Multer in the following ways:

- A text field of exactly `fieldSize` bytes is accepted, while Multer rejects it.
- Field names that could pollute a prototype (`constructor`, or names with a `__proto__`, `constructor` or `prototype` segment, such as `user[constructor]`) fail the request with a `400 Invalid field name` response. Multer accepts them.
- Text fields sent with a `Content-Type: application/json` header arrive parsed, and invalid JSON fails the request with a `400` response (a `@fastify/multipart` feature). Malformed part header lines are ignored, whereas Multer fails the request with a `400` response.
- `fileFilter` functions and storage engines receive the Fastify request instead of the Express one.
- The `attachFieldsToBody` plugin option is not supported, as it consumes the request body before the interceptors run.
- Multer's `highWaterMark`, `fileHwm`, `defCharset` and `streamHandler` options are not supported by the interceptors.

#### Example

A working example of file uploads is available [here](https://github.com/nestjs/nest/tree/master/sample/29-file-upload).

#### Streaming files

To send a file from a route handler, you could pipe a stream into the response object:

[[CODE:30]]

With this approach, the handler takes over the response, so post-controller [interceptor](/interceptors) logic no longer runs. Instead, return a `StreamableFile` instance, and Nest pipes it into the response for you. For content that isn't a file, such as the tokens of an LLM, see [Streaming responses](/http/streaming-responses).

> info **Note** Streaming files applies to **HTTP applications**. The examples below do not apply to GraphQL or microservice applications.

##### Streamable file class

A `StreamableFile` holds the content to be sent. Its constructor accepts either a `Readable` stream or a `Uint8Array` (including a `Buffer`). The following example returns the `package.json` file instead of a JSON response. The same approach works for images, documents, and any other file type:

[[CODE:31]]

> info **Hint** The `StreamableFile` class is exported from the `@nestjs/common` package.

Neither the `ClassSerializerInterceptor` nor the `StandardSchemaSerializerInterceptor` [serializes](/application/serialization) `StreamableFile` responses.

##### Response headers

By default, the `Content-Type` response header is `application/octet-stream`. To change it, and to set the `Content-Disposition` and `Content-Length` headers, pass the `type`, `disposition`, and `length` options to the `StreamableFile` constructor:

[[CODE:32]]

When the content is a `Uint8Array`, `length` defaults to its size. For streams, set `length` yourself if you know the size in advance.

Headers with static values can also be set with the [`@Header()`](/controllers#response-headers) decorator:

[[CODE:33]]

To compute headers at runtime, inject the response object with `passthrough` enabled, so that Nest still sends the returned `StreamableFile`:

[[CODE:34]]

##### Stream errors

With the Express adapter, if the stream emits an error before any data has been sent, the client receives a `400 Bad Request` response, and the error is logged. Starting with NestJS v12.2, the response body no longer contains the error message, which may include the path of the file. If data has already been sent, the response is ended. To customize this behavior, pass a handler to the `setErrorHandler()` method:

[[CODE:35]]

The `setErrorLogger()` method replaces the function that logs errors: those the default error handler answers, and those the response stream emits while the file is being written to it.

> info **Note** The error handler and the error logger apply to the Express and Node adapters. With the Fastify adapter, a stream error is handled by the [exceptions layer](/exception-filters), so by default the client receives a `500 Internal Server Error` response.

##### Cross-platform support

Fastify can send streams without `stream.pipe(res)`, so with Fastify the `StreamableFile` class is not strictly required. However, Nest supports `StreamableFile` on both platforms, so code that returns it works unchanged if you switch between Express and Fastify.
