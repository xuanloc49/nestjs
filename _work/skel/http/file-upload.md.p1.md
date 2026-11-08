### File upload and streaming

This chapter covers files in both directions: receiving files that clients upload, and [streaming files](#streaming-files) back to clients.

To handle file uploads, Nest provides a built-in module based on the [multer](https://github.com/expressjs/multer) middleware package for Express. Multer handles data posted in the `multipart/form-data` format, which is primarily used to upload files with an HTTP `POST` request. The module is fully configurable, so you can adjust its behavior to your application's requirements.

> warning **Warning** Multer cannot process data that is not in the `multipart/form-data` format.

> info **Hint** If your application runs on the `FastifyAdapter`, the same interceptors are available from the `@nestjs/platform-fastify` package, backed by [@fastify/multipart](https://github.com/fastify/fastify-multipart) instead of Multer, and the decorators and pipes described in this chapter work unchanged. Only the import path changes - see the [Fastify](/http/file-upload#fastify) section below.

> info **Hint** If your application runs on the `NodeAdapter`, import the interceptors and `MulterModule` from `@nestjs/platform-node` instead of `@nestjs/platform-express`. They are the same Multer-based interceptors, so everything in this chapter applies unchanged.

For type safety, install the Multer type definitions:

[[CODE:1]]

With this package installed, you can use the `Express.Multer.File` type (import the `Express` namespace with `import {{ '{' }} Express {{ '}' }} from 'express'`).

#### Basic example

To upload a single file, bind the `FileInterceptor()` interceptor to the route handler and extract the file from the request with the `@UploadedFile()` decorator.

[[CODE:2]]

> info **Hint** The `FileInterceptor()` decorator is exported from the `@nestjs/platform-express` package. The `@UploadedFile()` decorator is exported from `@nestjs/common`.

The `FileInterceptor()` decorator takes two arguments:

- `fieldName`: the name of the HTML form field that holds the file
- `options`: an optional object of type `MulterOptions`. This is the same object the Multer constructor accepts (see the [Multer options](https://github.com/expressjs/multer#multeropts)).

> warning **Warning** `FileInterceptor()` may not be compatible with third party cloud providers like Google Firebase or others.

#### File validation

You will often want to validate incoming file metadata, such as the file size or MIME type. To do so, create a [pipe](/pipes) and bind it to the parameter decorated with `@UploadedFile()`. The following example implements a basic file size validation pipe:

[[CODE:3]]

Use it together with the `FileInterceptor` as follows:

[[CODE:4]]

For common cases, Nest provides a built-in pipe, `ParseFilePipe`, which also standardizes how new file validations are added:

[[CODE:5]]

`ParseFilePipe` requires an array of file validators to execute. The validator interface is described below. The pipe also accepts two **optional** options:

<table>
  <tr>
    <td><code>errorHttpStatusCode</code></td>
    <td>The HTTP status code to be thrown in case <b>any</b> validator fails. Default is <code>400</code> (BAD REQUEST)</td>
  </tr>
  <tr>
    <td><code>exceptionFactory</code></td>
    <td>A factory which receives the error message and returns an error.</td>
  </tr>
</table>

Validators used by this pipe are either built-in implementations or your own subclasses of the abstract `FileValidator` class:

[[CODE:6]]

> info **Hint** The `isValid()` method can be asynchronous. For type safety, type the `file` parameter as `Express.Multer.File` when you use Express (the default HTTP adapter).

A `FileValidator` receives the file object and validates it according to the options passed to its constructor. Nest provides two built-in implementations:

- `MaxFileSizeValidator` checks that the file's size is less than the provided value, in bytes.
- `FileTypeValidator` checks that the file's MIME type matches the given string or regular expression. By default, it determines the MIME type from the file content's [magic number](https://www.ibm.com/support/pages/what-magic-number).

The following snippet uses both validators with `ParseFilePipe`:

[[CODE:7]]

> info **Hint** If the list of validators grows long, define the array in a separate file and import it as a named constant, such as `fileValidators`.

Alternatively, compose the validators with the `ParseFilePipeBuilder` class. The builder instantiates each validator for you, so you pass only their options:

[[CODE:8]]

> info **Hint** A file is required by default. To make it optional, pass `fileIsRequired: false` in the options of the `build()` method (next to `errorHttpStatusCode`).

#### Array of files

To upload an array of files identified by a single field name, use the `FilesInterceptor()` decorator (note the plural **Files** in its name). It takes three arguments:

- `fieldName`: as described above
- `maxCount`: an optional maximum number of files to accept
- `options`: an optional `MulterOptions` object, as described above

When using `FilesInterceptor()`, extract files from the `request` with the `@UploadedFiles()` decorator.

[[CODE:9]]

> info **Hint** The `FilesInterceptor()` decorator is exported from the `@nestjs/platform-express` package. The `@UploadedFiles()` decorator is exported from `@nestjs/common`.

#### Validating an array of files

To validate an array of uploaded files, pass a pipe built with `ParseFilePipeBuilder` to the `@UploadedFiles()` decorator. The registered validators run against each file in the array.

[[CODE:10]]

#### Multiple files

To upload multiple files under different field names, use the `FileFieldsInterceptor()` decorator. It takes two arguments:

- `uploadedFields`: an array of objects, each with a required `name` property (the field name) and an optional `maxCount` property
- `options`: an optional `MulterOptions` object, as described above

When using `FileFieldsInterceptor()`, extract files from the `request` with the `@UploadedFiles()` decorator.

[[CODE:11]]

#### Any files

To accept files under any field names, use the `AnyFilesInterceptor()` decorator. It accepts an optional `options` object, as described above.

When using `AnyFilesInterceptor()`, extract files from the `request` with the `@UploadedFiles()` decorator.

[[CODE:12]]

#### No files

To accept `multipart/form-data` without allowing file uploads, use the `NoFilesInterceptor`. It sets the multipart fields as properties of the request body. A request that contains files is rejected with a `BadRequestException`.

[[CODE:13]]

#### Default options

You can pass Multer options to each file interceptor, as described above. To set default options instead, call the static `register()` method when you import the `MulterModule`. It accepts all [Multer options](https://github.com/expressjs/multer#multeropts).

[[CODE:14]]

> info **Hint** The `MulterModule` class is exported from the `@nestjs/platform-express` package.

Options passed to a file interceptor take precedence over these defaults. Starting with NestJS v12.0.4, the two `limits` objects are merged key by key, so a route that sets only `limits.fileSize` keeps a default such as `limits.files`. If one of them is a function, the interceptor's `limits` replaces the default one entirely.

#### Async configuration

To set `MulterModule` options asynchronously instead of statically, use the `registerAsync()` method. As with most dynamic modules, it supports several techniques for async configuration.

One technique is to use a factory function:

[[CODE:15]]

Like other [factory providers](/fundamentals/custom-providers#factory-providers-usefactory), the factory function can be `async` and can inject dependencies through `inject`.

[[CODE:16]]

Alternatively, you can configure the `MulterModule` using a class instead of a factory, as shown below:

[[CODE:17]]

The construction above instantiates `MulterConfigService` inside `MulterModule` and calls its `createMulterOptions()` method to obtain the options object. For this to work, `MulterConfigService` must implement the `MulterOptionsFactory` interface:

[[CODE:18]]

If you want to reuse an existing options provider instead of creating a private copy inside the `MulterModule`, use the `useExisting` syntax.

[[CODE:19]]

You can also pass `extraProviders` to the `registerAsync()` method. These providers are merged with the module's providers.

[[CODE:20]]

This is useful when the factory function or the class constructor needs additional dependencies.

#### Memory usage and storage

By default, Multer uses its in-memory storage engine (`memoryStorage()`): every uploaded file is read completely into memory and exposed as a `Buffer` on `file.buffer` before your route handler runs. This is convenient for small files (avatars or CSV imports), but each in-flight upload occupies as much memory as its size, so large files or many concurrent uploads can quickly exhaust the memory of your process.

> warning **Warning** Multer does not limit the size of uploaded files by default. When you keep files in memory, always set `limits.fileSize`.

##### File size limit

Use the `limits` option to reject files that are too large. When a limit is exceeded, Nest responds with a `413 File too large` error (for `fileSize`) or `400 Bad Request` (for other limits, such as `files`) and the route handler is not called.

[[CODE:21]]

> info **Hint** Unlike `MaxFileSizeValidator`, which runs after the whole file has been received, `limits.fileSize` makes Multer stop storing the file and reject the request as soon as the limit is reached, so oversized files never fully reach memory or disk. See the [Multer limits](https://github.com/expressjs/multer#limits) for the full list of options.

##### Field name limits

Field names such as `user[address][city]` or `tags[2]` build nested objects and arrays in the request body. Two limits bound them: `fieldNestingDepth`, the number of nesting levels (`a[b][c]` has 2), and `fieldArrayIndexLimit`, the highest array index (`tags[2]` uses index 2). A request that exceeds either one is rejected with a `400 Bad Request` response. Starting with NestJS v12.2, they default to 32 and 1000 respectively (Multer leaves them unlimited), so that a single request cannot build an arbitrarily deep body or a huge array. Set a limit to `Infinity` to lift it.

##### Disk storage

To keep memory usage constant regardless of file size, write uploads to disk with the `diskStorage()` engine. Multer then streams each file to disk as it arrives, and the file object exposes `destination`, `filename` and `path` instead of `buffer`.

[[CODE:22]]

> info **Hint** The `diskStorage()` and `memoryStorage()` functions are exported from the `multer` package. As a shorthand, pass `dest: './uploads'` to store files on disk under random names. If you pass a `destination` function instead of a string, you are responsible for creating the directory.

To apply the same storage and limits to every file interceptor in a module, set them as [default options](/http/file-upload#default-options) or with [async configuration](/http/file-upload#async-configuration).

Files stored on disk are not removed automatically once your route handler has run. Delete them (for example with `unlink()` from `fs/promises`) once you have processed them, including when processing fails. Starting with NestJS v12.2, if a pipe rejects the request (for example, because `ParseFilePipe` validation fails), the route handler does not run, and the stored files are removed once the error response has been sent.

##### Sending files to external storage

To store uploads in S3, Cloudflare R2 or another external store without buffering them in memory or writing a temporary file, use a storage engine that streams each file to its destination as it arrives. The [`@nestjs/storage`](/application/file-storage) package provides one, `uploadToDisk()`, which you pass as the `storage` option of `FileInterceptor()`. See [Upload product photos](/application/file-storage#upload-product-photos). Any other Multer [storage engine](https://github.com/expressjs/multer/blob/main/StorageEngine.md) works the same way.

> info **Hint** On the `FastifyAdapter`, you can also receive the file as a stream inside the route handler with `FileStreamInterceptor()`. See [Streaming uploads](/http/file-upload#streaming-uploads).
