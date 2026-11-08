### File storage

`@nestjs/storage` keeps files on named disks (a local folder, S3 or an S3-compatible store such as R2) behind one API, with public and signed URLs.

An online store for cat food and supplies keeps three kinds of files. Product photos are uploaded by staff and shown to everyone. Invoices are PDF files that only the customer who paid should be able to download. And the warehouse team photographs products with the store's mobile app, which uploads large photos that shouldn't have to pass through the order API.

In development, all of this should work from a folder on the laptop. In production, the files go to S3 or Cloudflare R2, because the API runs on several instances and none of them has a disk that lasts. The code that stores and serves files should be the same in both.

`@nestjs/storage` gives each place files live a name, a **disk**, and one API for all of them: `put()`, `get()`, `list()`, `delete()`, public URLs and signed URLs. It ships a local disk, an S3 disk that works with AWS S3 and S3-compatible stores (Cloudflare R2, MinIO, Backblaze B2), and an in-memory disk for tests. It talks to S3 over `fetch`, with no AWS SDK, and depends only on `@nestjs/common` and `@nestjs/core`.

It doesn't parse uploads. multer on Express and `@nestjs/platform-fastify/multipart` on Fastify keep doing that, with `FileInterceptor()` as usual. This package is where the files end up: it provides a storage engine that streams each upload straight onto a disk.

In this tutorial, you'll:

- configure a public disk for photos and a private disk for everything else,
- stream photo uploads onto the photos disk, with the type and size checked before anything is written,
- store invoices privately and hand out download links that expire after five minutes,
- let the mobile app upload photos directly to storage, with a signed upload URL,
- switch from local disks to S3 or R2 with configuration alone,
- test all of it against in-memory disks.

#### Installation

To get started, install the required dependencies:

[[CODE:1]]

#### Configure the disks

The app needs two disks. `photos` holds product photos, which anyone may see, so it has a public URL. `private` holds invoices and uploads that haven't been checked yet, and is only reachable through signed URLs. Keeping public and private files on separate disks (separate buckets, in production) means a file never becomes public by accident.

Start with the configuration, a [custom configuration file](/application/configuration#custom-configuration-files) for `@nestjs/config`. `STORAGE_DRIVER` will pick local disks or S3 [in production](/application/file-storage#use-s3-or-r2-in-production); until then, everything is local:

[[CODE:2]]

The disks are built from that configuration by a factory function:

[[CODE:3]]

A `LocalDisk` keeps files in a directory, which it creates at startup. `publicUrl` is where the files can be fetched publicly: the photos disk's `url(key)` returns URLs under it. In development, the app itself will serve that path (see [Upload product photos](/application/file-storage#upload-product-photos)); in production, a CDN will.

A local directory can't produce signed URLs the way S3 does, so the private disk signs its own: with `signedUrls`, its `signedUrl()` returns URLs under `baseUrl`, signed with HMAC-SHA256, which the app verifies and serves (see [Serve signed URLs in development](/application/file-storage#serve-signed-urls-in-development)). `keys` takes one or more keys. The first signs, and all of them verify, so you can rotate a key by putting the new one first and removing the old one once the links it signed have expired. A key must have at least 32 characters.

Register the module with `forRootAsync()`, so the factory can read `ConfigService`:

[[CODE:4]]

`StorageModule` is global. Services inject a disk in one of three ways:

| Injection | Gives you |
| --- | --- |
| `private readonly files: StorageDisk` | The default disk, here `private` |
| `@InjectDisk('photos') private readonly photos: StorageDisk` | The disk called `photos` |
| `private readonly storage: Storage` | Every disk: `storage.disk('photos')`, for code that picks a disk at runtime |

Configuration mistakes stop the application at startup. Without `STORAGE_SIGNING_KEY`, `getOrThrow()` reports the missing key; with a short one, the error says the signing key must have at least 32 characters. The same goes for a `default` that names no disk, and for a class that injects a disk name no configuration provides:

[[CODE:5]]

#### Upload product photos

Photos may be JPEG, PNG or WebP images of up to 5 MiB. The rules are shared by the upload endpoint below and the [mobile uploads](/application/file-storage#upload-straight-to-storage-from-the-mobile-app) further down:

[[CODE:6]]

The upload endpoint uses `FileInterceptor()` from `@nestjs/platform-express`, as any upload does. The difference is the `storage` option: `uploadToDisk()` is a multer storage engine that streams the file onto a disk instead of into memory or a temp folder:

[[CODE:7]]

By the time the handler runs, the photo is stored. `uploadToDisk()` has done three things on the way:

- **It checked what the file is, not what the client says it is.** A browser sends the type it guesses from the file name, and a script can send anything, so a file declared `image/png` may well be an HTML page or an SVG with a script in it. The engine reads the first bytes of the stream, detects the type from their signature (JPEG, PNG, GIF, WebP, AVIF, HEIC and PDF are built in; [other formats](/application/file-storage#accept-csv-and-other-text-formats) take a detector of your own), and refuses anything not in `contentTypes` with a `415` before a byte is written. The stored content type is the detected one, never the client's.
- **It enforced the size limit without leaving a partial file.** multer stops reading at `limits.fileSize`. The engine then refuses to commit what it received: the request fails with `413 File too large`, nothing is stored, and no file is replaced.
- **It picked the key.** By default, a random UUID and the extension of the detected type, such as `2f1c0d6e-….png`. Unique keys matter: an upload never overwrites another, and a cached photo never goes stale.

`@UploadedFile()` returns a `StoredUpload`: multer's usual fields (`fieldname`, `originalname`, `mimetype`, `size`) plus `key`, `disk`, `contentType` and `etag`. `mimetype` is still the client's claim; use `contentType`.

> info **Hint** `ParseFilePipe` and its validators run after the interceptor, when a streamed file is already stored, and `FileTypeValidator` needs the file in memory to check its bytes. With `uploadToDisk()`, check type and size in the engine, as above. On Fastify, import `FileInterceptor` from `@nestjs/platform-fastify/multipart` and register `@fastify/multipart`; `uploadToDisk()` works the same with both.

Products have this shape, and the application's `ProductsService` has `findOne(id)`, which throws `NotFoundException` for an unknown id, and `setPhoto(id, key)`:

[[CODE:8]]

The service records the new photo, and deletes the previous one:

[[CODE:9]]

The interceptor runs before the handler, so the file is stored even when the product turns out not to exist. The service deletes it in that case, which keeps a mistyped id from leaving orphans behind. `url(key)` builds the public URL from the disk's `publicUrl`.

The `GET photos/:file` route serves photos in development. `serveFile()` streams a file from a disk as the response, with `Content-Type`, `Content-Length`, `ETag`, `Last-Modified`, the `Cache-Control` stored with the file (`private` when none is, so a shared cache never keeps a file that may be one user's), and `X-Content-Type-Options: nosniff`, so the browser never second-guesses the type. `disposition: 'inline'` lets the browser show the image; for types that could run script in your origin, such as HTML or SVG, `serveFile()` sends `Content-Disposition: attachment` regardless. It answers `Range` requests with `206`, `If-None-Match` with `304`, and a missing file with `404`.

Register the feature module, and import `ProductsModule` in `AppModule`:

[[CODE:10]]

##### Accept CSV and other text formats

Built-in detection recognizes formats by the fixed bytes they start with. A CSV file has no such signature, so `contentTypes: ['text/csv']` on its own refuses every CSV with a `415`. For a format like that, pass `detectContentType`: a function that receives the start of the file and returns its type, or `undefined` when it doesn't recognize it.

Staff update prices by uploading a spreadsheet export. The app recognizes one by its header row:

[[CODE:11]]

The upload endpoint allows `text/csv` and passes the function to `uploadToDisk()`. Price lists go to the private disk, because nobody has checked their rows yet:

[[CODE:12]]

- **Built-in detection comes first.** The function only runs when the file isn't one of the built-in formats. A PNG renamed to `prices.csv` is still detected as a PNG, and refused. Passing the exported `detectContentType()` helper as the option does nothing, because that's the check that already ran.
- **It sees the start of the file.** `bytes` holds the first 4 KiB, or the whole file when it's smaller. To change that, set `contentTypeSampleBytes` to a whole number from 1 byte to 64 KiB (it requires `detectContentType`). The second argument has `originalname` and `mimetype`, but they're the client's claims, so decide from the bytes.
- **What it returns is checked against `contentTypes`.** Types are compared without their parameters: `text/csv` in the list allows `text/csv; charset=utf-8`. When the function returns `undefined`, or a type that isn't in the list, the upload is refused with a `415` before a byte is written. Without `contentTypes`, any returned type is accepted, and an unrecognized file is stored as `application/octet-stream`.
- **The returned type is the one the file is stored and served with.** Include the charset for text formats. It also sets the extension: `file.extension` is `.csv` in `key()` above, and the default key ends with it too.
- **It may be async.** The engine waits for the promise while it holds the request, so it must settle quickly. Return `undefined` for a file you don't recognize rather than throwing: an error fails the upload as it would anywhere else in the request, so anything but an `HttpException` becomes a `500` instead of a `415`. So does returning anything but a string or `undefined`.

> warning **Warning** The function classifies the start of the file. It doesn't validate the file: a price list with the right header can hold anything after it. `PriceListsService.import()` must read the whole file, check every row, and delete `file.key` when it rejects the list, as with any check that runs after the interceptor.

#### Keep invoices private

An invoice is generated the first time a customer asks for it and stored on the private disk. A real app renders the PDF with a library or a rendering service; this stand-in is enough to follow the flow:

[[CODE:13]]

The service reads the order with the application's `OrdersService`, in which order `ord_1000` has been paid and `ord_1001` hasn't, stores the invoice once, and returns a signed link to it:

[[CODE:14]]

`put()` takes a `Buffer`, a string, a `Uint8Array`, a Node stream, a web `ReadableStream`, or any async iterable of bytes. On every disk, a write is atomic: a reader sees the old file or the new one, never half of one, and a write that fails leaves nothing behind. `metadata` stores your own string values with the file; `stat()` and `get()` return them.

For `LocalDisk`, a failed filesystem write removes the temporary file and preserves any existing file. If writing makes no progress, or the persisted size differs from the bytes written, `put()` rejects with `StorageError`.

`signedUrl()` returns a link that works without any other credentials until it expires. `expiresIn` is a duration: `'5m'`, `'1h'`, or milliseconds, 15 minutes by default and at most 7 days, S3's limit. `filename` sets the name the browser saves the file under.

The endpoint returns the link rather than the file, which lets a web page or the mobile app open it directly:

[[CODE:15]]

Register `OrdersController`, `OrdersService` and `InvoicesService` in an `OrdersModule`. In a real app, the endpoint also checks that the invoice belongs to the signed-in customer, for instance with a policy from the [authorization](/security/authorization) tutorial. The link itself needs no check: whoever holds it may download that one file until it expires.

#### Serve signed URLs in development

With a local disk, the signed link points at the app itself, `http://localhost:3000/files?key=…&expires=…&signature=…`, so the app needs a route that verifies and serves it:

[[CODE:16]]

`serveSignedUrl()` checks the signature, the expiry and the method, then answers like `serveFile()`, with the file name the link was signed with. The signature covers the route (`baseUrl`), the key, the expiry and the file name, so changing any of them is a `403 Invalid signed URL`, a link past its expiry is a `403 The signed URL has expired`, and a link issued for one disk's route is refused by another's, even when both use the same signing key. Download managers can resume a large file with `Range` requests.

Register the controller in a `FilesModule`, and import it in `AppModule` along with the other features:

[[CODE:17]]

The route stays in the app in production. There, the private disk is an S3 disk whose signed URLs point at the bucket, so `serveSignedUrl()` has nothing to serve and answers `404`.

#### Upload straight to storage from the mobile app

The warehouse team photographs products with the mobile app. Photos are large, and phones are often on slow connections, so an upload through the API would hold a connection and a request for as long as it takes. Instead, the app asks the API for an upload URL, sends the photo straight to storage, and then tells the API it is done:

1. `POST /products/:id/photo/uploads` with the photo's type and size returns a signed upload URL.
2. The app sends the photo to that URL with `PUT`.
3. `PUT /products/:id/photo` with the upload's key makes it the product's photo.

The upload goes to the private disk, under `incoming/`, because the API hasn't looked at it yet. Only after checking it does the API copy it to the photos disk:

[[CODE:18]]

`signedUpload()` returns the URL, the method (`PUT`), the headers the client must send, and when the URL expires. The URL is signed for exactly the declared content type and size: a different `Content-Type`, or a body of another length, is refused by the storage (`403`), so the app can't send a 2 GB video where it announced a 2 MB photo.

The declared type is still the client's claim. `completeUpload()` therefore treats the upload as untrusted:

- **The key must be one it handed out for this product.** Without that check, a client could submit `invoices/ord_1000.pdf` and have the API copy someone's invoice to the public photos disk.
- **The size is checked again** with `stat()`, which returns the file's metadata without its body.
- **The bytes are checked** by reading only the first 16, with a ranged `get()`, and passing them to `detectContentType()`, which recognizes JPEG, PNG, GIF, WebP, AVIF, HEIC and PDF.

Only then is the photo streamed from one disk to the other: `get()` returns the body as a Node stream, and `put()` accepts it, so the file never sits in memory whole. On S3, that is a download and an upload through the API instance, which is fine for photos; for very large files, you would process them where they are, for instance with a job.

The two routes in the controller pass the request on:

[[CODE:19]]

With a local disk, the upload URL points at the app again, so `FilesController` receives the `PUT` too. `receiveSignedUpload()` does what S3 does with a presigned URL: it checks the signature, the expiry, the content type and the length, and streams the body onto the disk:

[[CODE:20]]

> info **Hint** On Fastify, the upload's body must reach the handler unread. Fastify only parses JSON and plain text by default and answers other content types with `415`, so register a catch-all parser that leaves the body alone: `app.getHttpAdapter().getInstance().addContentTypeParser('*', (req, payload, done) => done(null))`.

Uploads that are never completed stay under `incoming/`. On S3, a lifecycle rule deletes them after a day (see the production checklist).

#### Use S3 or R2 in production

In production, both disks become S3 disks. A local disk can't serve there: a container's file system is discarded when the task is replaced (a deploy, a scale-in, a failed node), taking the files with it, and other instances can't read them. Only the factory changes; every service, controller and signed URL keeps working:

[[CODE:21]]

`S3Disk` reads credentials from the standard `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` variables, unless you pass `credentials`, either an object or a function that returns them (called before every request, for credentials that rotate). Without credentials, the app doesn't start. The same class covers several services:

| Service | Settings |
| --- | --- |
| AWS S3 | `region`, such as `eu-central-1`. No `endpoint` |
| Cloudflare R2 | `endpoint: 'https://<account id>.r2.cloudflarestorage.com'`, `region: 'auto'` |
| MinIO | `endpoint: 'http://minio:9000'`, `forcePathStyle: true` |
| Backblaze B2 | `endpoint: 'https://s3.<region>.backblazeb2.com'`, `region` |
| Google Cloud Storage | `endpoint: 'https://storage.googleapis.com'`, HMAC keys as credentials, `batchDelete: false` |

With S3, `signedUrl()` and `signedUpload()` return presigned URLs, signed with the credentials, which the bucket verifies itself: the app's `/files` route isn't involved. `url()` returns URLs under `publicUrl`, typically a CDN or R2's public bucket domain in front of the photos bucket.

Uploads stream to S3 too. A file up to 8 MiB goes up in one request; a longer one, or a stream whose length isn't known, goes up as a multipart upload, four 8 MiB parts at a time, and is aborted if anything fails, so a failed upload never becomes a file. Requests that fail with a network error, a timeout, throttling (`429`, `SlowDown`) or a `5xx` are retried with backoff, up to 3 attempts in all. `multipart`, `retry` and `timeout` tune this per disk.

> info **Hint** Every S3 request is signed with Signature Version 4, implemented on `node:crypto`. It is checked against the AWS Signature Version 4 test suite and the examples in the Amazon S3 API reference, so there is no AWS SDK to install.

#### Try it

Start the app with a signing key, in a directory with a `kibble.png`, a `scratching-post.jpg` and a `notes.txt`:

[[CODE:22]]

Upload a photo. Then try a text file declared as an image, which the app refuses without storing it:

[[CODE:23]]

Fetch a photo's headers:

[[CODE:24]]

Get a signed link to an invoice, download it, and try the same link for another order:

[[CODE:25]]

Finally, upload a photo the way the mobile app does. Ask for an upload URL, send the file there, and submit its key:

[[CODE:26]]

The files are in `storage/photos` and `storage/private`, as plain files: `storage/private/invoices/ord_1000.pdf` is the invoice. The `.nest-storage` folder in each holds temporary files during writes, and the metadata that a file name can't carry.

#### Testing

`InMemoryDisk` keeps files in memory and behaves like the other disks: the same key rules, ranges, listings, metadata and signed URLs. Like S3, it can hold both `a` and `a/b`, which a local disk refuses with `StorageKeyConflictError`. In an end-to-end test, replace the disks by overriding `STORAGE_MODULE_OPTIONS`, the options the factory would have returned:

[[CODE:27]]

The overridden options replace the factory's result, so the test needs no signing key and touches no file system. `keys()` lists what a disk holds and `clear()` empties it. The upload goes through multer and `uploadToDisk()` as in production; only the place the bytes land differs.

To test what reaches a real file system, use a `LocalDisk` on a temporary directory instead. For S3-specific behavior, such as presigned URLs or multipart uploads, point an `S3Disk` at MinIO or another S3-compatible server running locally.
