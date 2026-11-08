### SDK

The `@nestjs/observe` SDK is what gets your application's requests, jobs, errors, logs, and traces into your [NestJS Observe](https://www.observe.nestjs.com/ 'NestJS Observe') dashboard. It hooks into Nest's own request lifecycle - controllers, interceptors, resolvers, queue consumers - rather than bolting a generic Node.js agent onto the process, so most of what shows up in the dashboard needs no manual span wiring.

> info **Hint** Not sure it is worth the setup yet? The [live demo](https://www.observe-demo.nestjs.com/dashboard 'NestJS Observe live demo') shows what this instrumentation produces - traces, waterfalls, errors and jobs from a busy service - without installing anything.

#### Installation

There are two ways to set up the SDK: one command that does it for you, or the same steps by hand.

**With one command.** Run the following in your project's directory:

[[CODE:1]]

The command prints an eight-letter code. Type it at [observe.nestjs.com/link](https://www.observe.nestjs.com/link 'Link a project to NestJS Observe'), signing up first if you don't have an account, and approve. The command then writes the project's key pair into `.env` as `OBSERVE_APP_KEY` and `OBSERVE_APP_SECRET`, git-ignores `.env`, and adds `--env-file .env` to every script that runs `nest start` (`start`, `start:dev`, and `start:debug` in a `nest new` project).

If the application doesn't use the SDK yet, the command also installs `@nestjs/observe` with your package manager and makes the three edits from the [Quick start](#quick-start) below for you. It tells you so before you approve. See [Linking from the terminal](#linking-from-the-terminal) for exactly what it changes.

> warning **Warning** The SDK requires `@nestjs/core` v11.1.4 or later (it relies on the `instrument` application option introduced in that release), and `@nestjs/graphql` v13.4.4 or later if your application uses GraphQL. Earlier versions lack the hooks the SDK needs.

**By hand.** Install the SDK:

[[CODE:2]]

Then make the three edits from the [Quick start](#quick-start) below, generate an API key on your project's **API Keys** page (see [First project](/observability/overview#first-project)), and set the key pair as `OBSERVE_APP_KEY` and `OBSERVE_APP_SECRET`. This is also the way to go wherever the command leaves the wiring to you.

#### Quick start

The integration takes three steps. First, call `createObserveModule()` once, typically in `app.module.ts` or another root-level file. It returns a matched pair - a Nest module and an `instrument` hook - bound to the same configuration:

[[CODE:3]]

Second, import `ObserveModule.forRoot()` into your root module with at least a `serviceId` (shown above). Third, pass `ObserveInstrument` to `NestFactory.create()` so the SDK attaches to the application before it starts handling traffic:

[[CODE:4]]

> warning **Fastify** With `FastifyAdapter` (or any explicit adapter), the adapter takes the second argument, so the application options - and therefore `instrument` - move to the **third**:
>
> [[CODE:5]]
>
> Passing the options object as the second argument alongside an adapter silently drops them, and the SDK never attaches.

That completes the integration. Once the application receives traffic, requests, errors, and traces appear in your project's dashboard within moments, with no exporter to configure and no schema to design. The same `instrument` option is accepted by `NestFactory.createMicroservice()` and `NestFactory.createApplicationContext()`, so workers and standalone applications are instrumented the same way.

> info **Hint** `createObserveModule()` itself takes an options object that controls how trace ids are generated, how error source context is captured, and which providers are instrumented - see [Trace correlation](#trace-correlation) and [Error source context](#error-source-context) below. Everything else is configured through `ObserveModule.forRoot()`.

#### Configuring the module

Beyond the credentials in the quick start, these options decide how the SDK identifies your application, where it sends what it records, and how much it tells you about itself.

##### Authenticating and identifying the application

[[CODE:6]]

| Option           | Type     | Default  | Description                                                                                                                                                                                                |
| ---------------- | -------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `appKey`         | `string` | required | Written into `.env` as `OBSERVE_APP_KEY` by `npx @nestjs/observe link`, or generated from your project's **API Keys** page - see [First project](/observability/overview#first-project). Keep it out of source control. |
| `appSecret`      | `string` | required | Issued alongside `appKey`, the same way, and written as `OBSERVE_APP_SECRET`. Keep it out of source control.                                                                                               |
| `serviceId`      | `string` | required | Identifies this application in your dashboard. If you run multiple instances of the same service, use a value unique per instance (hostname, container id) to tell them apart in the Profiler. |
| `serviceVersion` | `string \| false` | inferred | Identifies the deployment - a semantic version, a commit hash, or any other identifier, at most 50 characters. When it isn't set, the SDK infers it at startup (see below); `false` reports none. |

Every request and job records the release that served it, which is what powers the **Releases** view: each version compared against the one before it, and a [verdict](/observability/dashboard#releases-and-their-verdicts) on what it changed. You usually don't need to set `serviceVersion`. When it isn't set, the SDK infers the release when the application starts, from the first of these that has one:

1. **`OBSERVE_SERVICE_VERSION`** in the environment, for a deploy that wants to be explicit without touching code.
2. **The commit your platform or CI exposes at runtime**: Vercel, Render, Railway, Heroku (with dyno metadata), Coolify, and Dokku, or GitHub Actions, GitLab CI, Bitbucket Pipelines, CircleCI, Buildkite, Azure Pipelines, and AWS CodeBuild for an application a CI job boots. `GIT_COMMIT_SHA`, `GIT_COMMIT`, `GIT_SHA`, `COMMIT_SHA`, and `SOURCE_VERSION` are read too.
3. **The commit checked out where the process runs**, read from the repository's `.git`.
4. **The revision a container platform names each deploy by**: Cloud Run's `K_REVISION`, Azure Container Apps' `CONTAINER_APP_REVISION`.

A container image built by your own pipeline usually carries none of these, since the build excludes `.git` and CI variables don't survive into the image. Hand it the commit at build time:

[[CODE:7]]

with `ARG GIT_SHA` and `ENV OBSERVE_SERVICE_VERSION=$GIT_SHA` in the Dockerfile. A `serviceVersion` you pass yourself wins over all of the above. An inferred commit is reported in full, as `git rev-parse HEAD` prints it, and the dashboard shortens it for display; that full form is also what to pass as `fixedInVersion` when resolving an issue.

<figure><img src="https://www.observe.nestjs.com/docs/sdk/deployments.webp" alt="Releases" /></figure>

##### Linking from the terminal

`npx @nestjs/observe link` puts a key pair on a developer's machine without copying a secret out of the browser, and sets the SDK up in an application that doesn't use it yet. Run it in the project's directory (the one with `package.json`), or point it there with `--cwd <dir>`:

1. It prints an eight-letter code, such as `BCDF-GHJK`, and opens [observe.nestjs.com/link](https://www.observe.nestjs.com/link 'Link a project to NestJS Observe') in your browser. With `--no-browser`, in CI, or without a terminal, it only prints the address. The code expires after 15 minutes. If the application doesn't use the SDK yet, the command also says, below the code, that it will install and wire it once you approve.
2. Type the code on that page. If you don't have an account yet, you sign up first; if you're signed out, you sign in. Either way, you come back to the code afterwards.
3. Check the request: the page shows the hostname of the machine and the package name the command sent. Then choose where the key goes. The page proposes your newest project, and in it the application named after your package, or a new application if there isn't one yet. You can change both, including to a new project.
4. Approve. The dashboard issues a new API key for that application, and the command writes it into the project.

In every project, the command changes up to three files:

- **`.env`** receives `OBSERVE_APP_KEY` and `OBSERVE_APP_SECRET`, single-quoted, replacing an earlier pair and leaving every other line as it was. A new `.env` is created readable only by you. The quotes are deliberate: a key or secret can contain `$` and `&`, which `dotenv-expand` (or `ConfigModule` with `expandVariables`) would rewrite, and at which a shell sourcing the file would stop.
- **`.gitignore`** gets a `.env` entry, unless the file is already ignored (as it is in a project generated by `nest new`).
- **`package.json`**: every script whose command begins with `nest start` gets `--env-file .env`: `start`, `start:dev`, and `start:debug` in a project generated by `nest new`, and a monorepo's per-application scripts as well. Scripts that already pass an env file are left alone, and so is `start:prod` (`node dist/main`). A `start` or `start:dev` script that starts the application some other way is left alone too, but the command names it, so you can load `.env` there yourself (for example, with `node --env-file=.env`).

In an application that doesn't use the SDK yet (no source file imports `@nestjs/observe`), the command also sets the SDK up, the way `nest new` does:

- **The SDK** is installed at the command's own version (`@nestjs/observe@^0.3.16` from 0.3.16). The command uses the package manager that the project's lockfile belongs to (pnpm, Yarn, Bun, or npm), looking up to the repository's root, so that a package in a workspace finds the root's lockfile. Without a lockfile, it uses the one named by the `packageManager` field in `package.json`, and npm otherwise. An `@nestjs/observe` that is already installed but older than the command is upgraded the same way. In that case, run `npx @nestjs/observe@latest link`, because plain `npx` runs the version installed in the project.
- **The root module**, the one `main.ts` passes to `NestFactory.create()` (found by following its import), gets the `createObserveModule()` call, and `ObserveModule.forRoot()` as the first entry of its `imports`. The options read the key pair from `OBSERVE_APP_KEY` and `OBSERVE_APP_SECRET`, and set `serviceId` to the name of the application you approved, lower-cased, with spaces turned into dashes and any other punctuation dropped (`Cats API` becomes `cats-api`).
- **`main.ts`** passes `instrument: ObserveInstrument` to `NestFactory.create()`, inside its options object, or as a new options argument if there is none.

The edits follow each file's quotes, semicolons, and indentation, and either both files change or neither does. The command lists them, so you can review them with `git diff`.

In some projects, the command leaves the wiring to you and prints why; the [Quick start](#quick-start) shows the edits to make. It does so in a workspace with several applications (the key belongs to one of them), in a JavaScript project, and wherever it can't edit the code safely, for example when `main.ts` imports the root module through a path alias rather than a relative path, when `imports` isn't a plain array, or when an `instrument` option is already passed. If the installation fails, the command prints the install command for you to run yourself, and leaves the wiring to you as well.

Before it asks for a code, the command turns away a project that it would have to install the SDK in but that has no `@nestjs/core`, or runs a NestJS version older than 11.

Nothing is written until the key arrives, so a denied, expired, or interrupted link leaves the project unchanged.

> warning **Warning** Approve only a code you started yourself, and only when it matches your terminal. The code is typed rather than carried in a URL so that nobody can send you a link that approves a key for them.

The key appears on the project's **API Keys** page like any other, named `CLI` followed by the time it was issued, and expires after a year; run the command again for a new one. `.env` stays on the machine that ran the command, so each teammate (or each additional machine) runs `npx @nestjs/observe link` as well and gets a key of its own for the same application.

##### Reading the key pair from the environment

When `appKey` or `appSecret` is unset or empty, or still holds the placeholder that `nest new` generates (`'YOUR_APP_KEY'` and `'YOUR_APP_SECRET'`), `ObserveModule` reads `OBSERVE_APP_KEY` or `OBSERVE_APP_SECRET` from the environment instead. This is what lets a project generated with Observe report once it's linked, without any change to `AppModule`. A value you pass yourself always wins, and the same fallback applies to the options that `forRootAsync()` resolves.

The variables are read when the options are resolved (for `forRoot()`, when the `AppModule` file is imported), so they must already be in `process.env` at that point. The `--env-file` flag loads them before any module runs.

In production, set `OBSERVE_APP_KEY` and `OBSERVE_APP_SECRET` in the environment (your platform's secrets or environment settings) rather than shipping `.env`. A project generated by `nest new` runs `node dist/main` for `start:prod`, which doesn't load `.env` anyway, and `nest start` skips an `--env-file` that doesn't exist, so a fresh clone or a CI run without `.env` still starts. Give production a key of its own from the project's **API Keys** page, so revoking a development key never stops it from reporting.

> info **Hint** The `link` command and the environment fallback require `@nestjs/observe` 0.3.15 or later. Installing and wiring the SDK into an application that doesn't use it yet requires 0.3.16 or later.

##### Turning the SDK off outside production

To keep an environment from reporting - local development, a CI run - keep `ObserveModule` imported and switch it off with `enabled`, rather than passing fake credentials, which are sent and refused:

[[CODE:8]]

`enabled: false` records and sends nothing - no traces, runtime metrics, or logs, and no request to any collector - and needs no credentials. The module stays in place, so `TracerService` can still be injected and calling it is harmless. Leaving the credentials unset also sends nothing, but logs a warning at every start, since in production that usually means the environment variables never reached the process. `enabled` requires `@nestjs/observe` 0.3.13 or later.

##### Asynchronous configuration

When the credentials come from a configuration provider rather than directly from `process.env`, use `forRootAsync()`. It accepts the same `useFactory`/`inject`, `useClass`, and `useExisting` shapes as every other Nest dynamic module (a class implements `ObserveOptionsFactory` with a `createObserveOptions()` method), plus `extraProviders` and `global`:

[[CODE:9]]

##### Collector endpoint

[[CODE:10]]

`endpoint` (default `'https://observe-api.nestjs.com'`) is the base URL of the collector. Telemetry and profiles share it, so the two can never point at different places. To override it without touching the config, set the `OBSERVE_ENDPOINT` environment variable. NestJS Observe is a hosted service and `observe-api.nestjs.com` is the only collector it runs; change the endpoint when your traffic has to leave through a forwarding proxy, or to point a test environment at a stub that accepts the batches.

##### Debugging the SDK itself

[[CODE:11]]

`debug` (default `false`) logs additional diagnostic information from the SDK to the console. Use it while getting instrumentation working, and turn it off in production.

##### Shutdown

When the application closes - `app.close()`, or a `SIGTERM` once `app.enableShutdownHooks()` has been called - the SDK sends what it still holds before it stops: the requests and jobs that finished since the last batch, their errors, the log lines buffered before shutdown began, and a last runtime sample. It waits at most `shutdownFlushTimeout` (default `2000` ms) for the collector, then lets the application exit; `0` skips the final send.

Two things decide what makes it in:

- **Signals.** Nest runs shutdown hooks on `SIGTERM` only if the application called `app.enableShutdownHooks()` at bootstrap. Without it, a deploy or a scale-in ends the process at once, and the last few seconds of telemetry are lost.
- **Module order.** Global modules shut down in reverse order of import. A job still running at shutdown is reported only if `ObserveModule` comes before `BullModule`, and before any module that registers a queue, in your root module's `imports`.

In test suites that boot the application with real credentials, set `shutdownFlushTimeout: 0`, so every `app.close()` doesn't send that test's requests to your project or wait on a collector the test environment can't reach. The final send requires `@nestjs/observe` 0.3.10 or later.
