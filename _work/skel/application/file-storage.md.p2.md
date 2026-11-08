#### Production checklist

- **Keep public and private files in separate buckets.** Give the photos bucket public read access, or put a CDN in front of it and point `publicUrl` at the CDN. Keep the private bucket fully private: invoices and uploads are only reachable through signed URLs. There is no per-file public flag, because new S3 buckets have object ACLs disabled, and a flag on one file is easy to get wrong.
- **Expire abandoned uploads.** Add a lifecycle rule to the private bucket that deletes objects under `incoming/` after a day, and one that aborts incomplete multipart uploads after a day.
- **Allow direct uploads from browsers with CORS.** The mobile app doesn't need it, but a web page that sends a `PUT` to a presigned URL does: allow `PUT` from your site's origin, with the `Content-Type` header.
- **Grant the app only what it uses.** An IAM policy with `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` and `s3:ListBucket` on the two buckets is enough. Keep `s3:ListBucket`: without it, S3 answers a request for a missing file with `403` instead of `404`, and `exists()` fails instead of returning `false`. For short-lived credentials, pass a `credentials` function that returns them.
- **Encrypt at rest.** S3 encrypts new objects by default; for a KMS key of your own, set `serverSideEncryption: 'aws:kms'` and `kmsKeyId` on the disk. R2 always encrypts.
- **Keep links short-lived.** Five minutes is plenty for a link a user clicks right away. A signed URL can't be revoked: it stays valid until it expires (or, on S3, until the credentials that signed it expire or lose access), so whoever it leaks to can use it until then.
- **Set a signing key per environment** for local disks (development and CI), from a secret, with at least 32 characters, and rotate it by putting the new key first in `keys`.
- **Don't use a local disk in production.** Files written to a container's disk vanish when the task is replaced, and other instances can't read them. Use S3, R2 or another object store (see [Use S3 or R2 in production](/application/file-storage#use-s3-or-r2-in-production)); local disks are for development and tests, and the module logs a warning at startup when it finds one with `NODE_ENV=production`.
- **Treat every key built from user input with care.** Keys are validated on every disk (no `..`, no absolute paths, no control characters), so user input can't escape a disk, but it can still name any file on it. Build keys from ids you control, as the upload endpoints above do.

#### Reference

##### Module options

`StorageModule.forRoot()` takes these options, and a `forRootAsync()` factory returns `default` and disk instances. Disk classes, `imports` and `isGlobal` sit next to `useFactory`, `useClass` or `useExisting`. The options are provided as `STORAGE_MODULE_OPTIONS`.

| Option | Default | Description |
| --- | --- | --- |
| `disks` | none (required) | Disks by name: instances, or `StorageDisk` classes that Nest instantiates, which can inject. See [Configure the disks](/application/file-storage#configure-the-disks). |
| `default` | the only disk | The disk that `StorageDisk` and `storage.disk()` resolve to. Required with more than one disk. |
| `imports` | none | Modules whose exports the disk classes inject. |
| `isGlobal` | `true` | Registers `Storage`, `StorageDisk` and the named disks globally. |

##### Disk methods

Every disk has the same methods, key rules and errors. A key is a relative, `/`-separated path of at most 1024 UTF-8 bytes, without empty, `.` or `..` segments, backslashes or control characters.

| Method | Description |
| --- | --- |
| `put(key, body, options)` | Writes a file atomically. Options: `contentType` (inferred from the extension by default), `cacheControl`, `contentDisposition`, `metadata` (string values, 2 KB in total), `contentLength`, `signal`. Resolves to `key`, `size`, `contentType` and `etag`. |
| `get(key, options)` | The file's metadata and its `body` as a Node stream. `range` takes `start` and an inclusive `end`, or `suffix`. |
| `getBuffer(key)`, `getText(key)` | The whole file. |
| `stat(key)`, `exists(key)` | The metadata without the body, or whether the file exists. |
| `delete(keys)` | One key or an array. Missing keys are ignored. |
| `list(options)`, `listAll(options)` | A page of `key`, `size`, `lastModified` and `etag` in UTF-8 byte order, with a `cursor`. Options: `prefix`, `cursor`, `limit` (up to 1000, the default). `listAll()` iterates every page. |
| `copy(from, to)`, `move(from, to)` | Within the disk, metadata included. |
| `url(key)` | The public URL under `publicUrl`. Throws without one. |
| `signedUrl(key, options)` | A download link. Options: `expiresIn` (default 15 minutes, at most 7 days), `filename`, `disposition`. See [Keep invoices private](/application/file-storage#keep-invoices-private). |
| `signedUpload(key, options)` | `url`, `method` (`PUT`), `headers` and `expiresAt` for a direct upload. Options: `contentType` (required), `contentLength`, `expiresIn`. See [Upload straight to storage from the mobile app](/application/file-storage#upload-straight-to-storage-from-the-mobile-app). |

##### Disks

| Disk | Options |
| --- | --- |
| `LocalDisk` | `root` (required, created at startup), `publicUrl`, `signedUrls`. For development and tests. `path(key)` returns a file's absolute path. |
| `S3Disk` | `bucket` (required), `region`, `endpoint`, `forcePathStyle`, `credentials`, `prefix`, `serverSideEncryption`, `kmsKeyId`, `multipart`, `retry`, `timeout`, `batchDelete`, `fetch`, `publicUrl`. See [Use S3 or R2 in production](/application/file-storage#use-s3-or-r2-in-production). |
| `InMemoryDisk` | `publicUrl`, `signedUrls`. For tests, with `keys()` and `clear()`. See [Testing](/application/file-storage#testing). |

`signedUrls` takes `baseUrl`, the route that serves the URLs, and `keys`, signing keys of at least 32 characters. The first key signs, and all of them verify. `S3Disk` defaults: `region` from `AWS_REGION`, then `AWS_DEFAULT_REGION`, then `us-east-1`; credentials from `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN`; `multipart` with a `partSize` of 8 MiB and a `concurrency` of 4; `retry: 3`, with backoff from 100 ms doubling to 20 seconds; no `timeout`; `batchDelete: true`.

##### HTTP helpers

| Helper | Options | Description |
| --- | --- | --- |
| `uploadToDisk(options)` | `disk` (a name or an instance, default the default disk), `contentTypes`, `detectContentType`, `contentTypeSampleBytes` (default 4 KiB, from 1 byte to 64 KiB, requires `detectContentType`), `cacheControl`, `key`, `metadata` | A storage engine for `FileInterceptor()`. `key` and `metadata` are functions of the file and the request. `detectContentType(bytes, file)` returns the type of a file the built-in detection doesn't recognize, or `undefined`, and may return a promise. See [Upload product photos](/application/file-storage#upload-product-photos) and [Accept CSV and other text formats](/application/file-storage#accept-csv-and-other-text-formats). |
| `serveFile(disk, key, options)` | `res` (required), `req`, `disposition` (default `attachment`), `filename`, `cacheControl` | Streams a file as the response, with `Range` and `If-None-Match` support when given `req`. |
| `serveSignedUrl(disk, options)` | `req`, `res`, `cacheControl` | Verifies and serves an app-served signed download URL. See [Serve signed URLs in development](/application/file-storage#serve-signed-urls-in-development). |
| `receiveSignedUpload(disk, options)` | `req`, `res`, `maxSize` | Verifies an app-served signed upload URL and streams the `PUT` body onto the disk. `maxSize` limits uploads signed without a `contentLength`. |
| `detectContentType(bytes)` | none | The type of a file from its first 16 bytes: JPEG, PNG, GIF, WebP, AVIF, HEIC or PDF, else `undefined`. It's the built-in detection `uploadToDisk()` runs, and knows nothing of the `detectContentType` option. |

##### Errors

Every error extends `StorageError`. Outside the HTTP helpers, they aren't `HttpException`s, so map them in your own code where they mean something to your API.

| Error | `status` | When |
| --- | --- | --- |
| `StorageFileNotFoundError` | 404 | `get()`, `stat()`, `copy()` or `move()` of a missing key. Has `key`. |
| `StorageInvalidKeyError` | 400 | A key that breaks the key rules. Has `reason`. |
| `StorageBodyLengthError` | 400 | The body didn't match `contentLength`. Has `expected` and `received`. |
| `StorageRangeNotSatisfiableError` | 416 | A range that starts past the end of the file. Has `size`. |
| `StorageKeyConflictError` | 409 | A local disk can't hold both `a` and `a/b`. |
| `StorageSignedUrlError` | 403 | A signed URL failed verification. `reason` is `missing`, `invalid`, `expired` or `method`. |
| `StorageServiceError` | none | The object store refused or failed. Has `code` (such as `AccessDenied` or `SlowDown`), `upstreamStatus`, `requestId` and `operation`. |
