### Supabase

Supabase gives an application a Postgres database, sign-in, file storage and an API that the browser can call directly, which covers a lot without a backend. What it leaves out is the work that needs a secret, a retry or a clock: Stripe webhooks, scheduled jobs, queues, an admin API. Nest takes on that work next to Supabase, on the same database and for the same users.

| Stays in Supabase | Goes in Nest |
| --- | --- |
| Sign-up, sign-in and password resets | Checking who is calling, and what they may do |
| Postgres, its migrations and row level security | Business rules, and queries that span many tables |
| Browser reads and writes that row level security covers | Anything that needs a secret: payments, email, other APIs |
| Storage and Realtime | Stripe webhooks, scheduled jobs, queues and an admin API |

The browser keeps calling Supabase directly for what row level security covers, and calls Nest with the same access token for the rest.

If a short function or two is all you need, [Edge Functions](https://supabase.com/docs/guides/functions) may be enough, with no server to run. They have [limits on CPU time and duration](https://supabase.com/docs/guides/functions/limits) and nowhere to run a queue's worker, so Nest fits better once you have jobs, queues or many routes that share code.

This recipe builds such an application on the local Supabase stack, so that you can run each step as you read. [The finished module](/recipes/supabase#the-finished-module) shows how the pieces are wired together.

#### Create the projects

The local stack needs Docker.

[[CODE:1]]

`npx supabase status -o env` prints the stack's URLs and keys. Put `API_URL`, `PUBLISHABLE_KEY`, `SECRET_KEY` and `DB_URL` in `.env`, under the names this recipe reads:

[[CODE:2]]

> warning **Warning** The secret key bypasses row level security. It belongs on the server only, and never in anything you ship to a browser or a mobile app.

> info **Hint** A hosted project has the same keys in its dashboard. Supabase is [deprecating](https://supabase.com/docs/guides/api/api-keys) the older `anon` and `service_role` keys by the end of 2026, so use these two.

Load `.env` with [`@nestjs/config`](/application/configuration):

[[CODE:3]]

[[CODE:4]]

Keep it first in `imports`, as the modules you'll add after it read `process.env` as they're declared. A module declared in another file reads it earlier, when the file is imported, so use `forRootAsync()` for what you register there.

#### Define a table

The schema stays in Supabase's migrations:

[[CODE:5]]

Write the table in the file this creates under `supabase/migrations`, with a policy that lets users reach only their own rows. `auth.uid()` is the user the request's access token belongs to:

[[CODE:6]]

Apply it to the local database:

[[CODE:7]]

> warning **Warning** Supabase's API serves the tables in the `public` schema to anyone with the publishable key, and that key is in your browser code. Enable row level security on every table you create there, including those only Nest uses. With it enabled and no policy, the key reads nothing.

#### Verify Supabase tokens

Supabase Auth signs an access token for each signed-in user, and publishes the public keys that verify it. [`@nestjs/authentication`](/security/authentication) can verify tokens from another issuer, so Nest needs no secret from Supabase to know who is calling:

[[CODE:8]]

[[CODE:9]]

The role comes from `app_metadata`, which only your server can change. A signed-in user can change their own `user_metadata` with `supabase.auth.updateUser()`, so never base a decision on it.

Register the module and the provider:

[[CODE:10]]

The module registers a global guard, so every route now answers `401 Unauthorized` without a valid token, including one with a bad signature, another issuer or audience, or an expired one. Mark a route that stays open with `@Public()`, and read the user with `@CurrentUser()`:

[[CODE:11]]

> info **Hint** A project still on the legacy JWT secret signs tokens with it and publishes no keys. Pass `key: process.env.SUPABASE_JWT_SECRET` instead of `jwks`, until you [migrate to signing keys](https://supabase.com/docs/guides/auth/signing-keys).

#### Call Nest from the browser

The browser sends the access token that Supabase gave it. `getSession()` refreshes the token when it has expired:

[[CODE:12]]

If the browser calls Nest on another origin, [allow that origin](/security/cors) when the application starts:

[[CODE:13]]

#### Query as the user, or as the server

`@supabase/supabase-js` is a client for your database's REST API. Generate types from your schema, so that a query on a table or a column that doesn't exist fails to compile, and run this again after each migration:

[[CODE:14]]

Create one client for the server, and one per request for the user. A client holds no database connection, so that's cheap:

[[CODE:15]]

A small decorator reads the token that the guard has already verified:

[[CODE:16]]

Prefer `forUser()` in a route that acts for a user. Your policies keep applying, so a query that forgets a filter still returns only that user's rows, and an insert for someone else is refused:

[[CODE:17]]

Use `admin` for what the server does on its own behalf, where no user is involved, as in a job or a webhook.

#### Query Postgres directly

For transactions and for queries that the REST API can't express, connect to the database with [`@nestjs/drizzle`](/data/drizzle) or another [database integration](/data/overview). The webhooks and jobs below use this connection too:

[[CODE:18]]

[[CODE:19]]

Locally, `DATABASE_URL` is the stack's `DB_URL`. On a hosted project, Nest is a persistent backend, so use the [direct connection string](https://supabase.com/docs/guides/database/connecting-to-postgres), or the shared pooler in session mode if your host only has IPv4. The pooler's transaction mode doesn't support prepared statements, nor the `LISTEN` that BullMQ's PostgreSQL backend uses.

Supabase's migrations stay the source of truth, so the Drizzle schema only describes the tables to query:

[[CODE:20]]

> warning **Warning** Row level security doesn't protect these queries. The `postgres` role bypasses it, so a query with no filter returns every user's rows, and each query has to check the owner itself.

To keep your policies on a direct query instead, run it in a transaction as the `authenticated` role, with the claims that `auth.uid()` reads:

[[CODE:21]]

Both settings end with the transaction, so they never reach the next query on that connection. Here's each way side by side, with `@CurrentSession()` giving a route the verified claims:

[[CODE:22]]

#### Protect an admin API

An admin API is what the browser can't do itself, as it needs the secret key. Keep a user's role in `app_metadata`, which `SupabaseAuth` already reads, and set it from the server:

[[CODE:23]]

The role is in the user's next token, so someone already signed in gets it when their token refreshes, within an hour by default.

Check it with [`@nestjs/authorization`](/security/authorization):

[[CODE:24]]

[[CODE:25]]

[[CODE:26]]

Register the module with `AuthorizationModule.forRoot({{ '{' }} globalGuard: false {{ '}' }})`, and `AdminPolicy` in `providers`. Its global guard is on by default and denies every route that has no `@Can()`, which would also close the routes above. A guest gets `401`, a user without the role `403`.

#### Receive Stripe webhooks

[`@nestjs/webhooks`](/http/webhooks) verifies a webhook's signature and remembers which events it has processed. It keeps its state in your database, through `@nestjs/outbox`, in schemas of their own. Supabase's API doesn't serve those schemas, so they stay private:

[[CODE:27]]

The signature covers the exact bytes that Stripe sent, so create the application with `rawBody`:

[[CODE:28]]

Name the sender in the module's `receivers`, with the signing secret from the Stripe dashboard or from `stripe listen`. This application only receives webhooks, so it needs neither of the background workers:

[[CODE:29]]

Register the two stores in `providers`. `migrate: true` creates their schemas at startup, which suits development (see [Deployment](/recipes/supabase#deployment) for production):

[[CODE:30]]

Add a table for what the webhook changes. Only Nest reads it, and the policy-less row level security keeps it from the browser. Add it to a new migration:

[[CODE:31]]

[[CODE:32]]

The route is `@Public()`, as the signature is what authenticates it, and an invalid one gets `401`. `processInTransaction()` records the event's id in the same transaction as your change, so a redelivery changes nothing:

[[CODE:33]]

To try it, forward events to your application with the [Stripe CLI](https://docs.stripe.com/stripe-cli), which prints the signing secret to put in `STRIPE_WEBHOOK_SECRET`:

[[CODE:34]]

#### Run scheduled jobs

There are two ways to run a job in Nest. Both work on any number of instances, and each run happens on one of them:

|  | `@nestjs/schedule` with `@nestjs/locks` | BullMQ |
| --- | --- | --- |
| **Where it runs** | In the instance that holds the lease | In a worker that picks it up |
| **If a run fails** | It waits for the next tick | It retries, with a backoff |
| **If every instance is down** | The tick is missed | The job waits in the queue |
| **What it adds to Postgres** | One table | A schema of its own |
| **What else it does** | Nothing else | Jobs enqueued from your code, priorities and flows |
| **Choose it for** | A job that's safe to skip, as the next tick catches up | A job that mustn't be lost, or runs for long |

Both can call the same code:

[[CODE:35]]

> info **Hint** [Supabase Cron](https://supabase.com/docs/guides/cron) schedules SQL inside Postgres, with no application involved. It's a good fit for a job that's only SQL, such as deleting old rows.

##### With `@nestjs/schedule` and `@nestjs/locks`

[`@nestjs/schedule`](/application/task-scheduling) runs a job inside the application, next to the code it calls. On its own, it runs the job on every instance. [`@nestjs/locks`](/reliability/locks) adds `@OnOneInstance()`: the first instance to fire takes a lease and runs every tick while it's up, and the others skip them. When it stops, another takes over, about a second after a clean shutdown and within 30 seconds after a crash:

[[CODE:36]]

[[CODE:37]]

[[CODE:38]]

The lease has to live somewhere that all instances share, and in production the application refuses to start with only the default in-memory store. Keep it in your database, with a table in a new migration:

[[CODE:39]]

Then copy the Drizzle table and `DrizzleLockStore` from [Keep locks in your database](/reliability/locks#keep-locks-in-your-database), and add the store to `providers`.

##### With BullMQ

[BullMQ](/application/queues) keeps jobs in a queue, with retries and a backoff. It usually runs on Redis, and it also has a PostgreSQL backend, so on Supabase it can use the database you already have:

[[CODE:40]]

[[CODE:41]]

`migrate: true` creates the `bullmq` schema at startup, which Supabase's API doesn't serve. The migration takes an advisory lock, so several instances starting together apply it once.

> info **Hint** To use Redis, install `ioredis` and replace those options with `connection: {{ '{' }} host, port {{ '}' }}`. Nothing else changes.

A job scheduler creates the job on each tick. The id makes it one schedule, however many instances declare it:

[[CODE:42]]

The processor runs it, on whichever instance is free:

[[CODE:43]]

The same queue takes jobs from your own code, such as a route that shouldn't wait for an email. Inject it with `@InjectQueue('billing')`, and add a case for the job to the processor:

[[CODE:44]]

#### Hand out file uploads

A browser can upload to Supabase Storage directly, under policies on the `storage.objects` table. When the decision belongs on the server, such as a quota or a paid plan, keep the bucket private and let Nest sign each upload. Create the bucket in a migration:

[[CODE:45]]

[[CODE:46]]

The browser then uploads straight to Supabase, so the file never passes through your application:

[[CODE:47]]

To hand a file back, `createSignedUrl(path, 60)` on the admin client makes a link that works for 60 seconds.

#### Test against the local stack

An end-to-end test can use real tokens and your real policies, as the stack gives you both. Put it in `test/`, and run `npx supabase start` and `npx supabase db reset` before it:

[[CODE:48]]

#### Move an Edge Function to Nest

Most of a function has a direct counterpart, and you can move them one at a time, as both use the same tokens and database:

| In an Edge Function | In Nest |
| --- | --- |
| Reading the `Authorization` header and calling `supabase.auth.getUser()` | `SupabaseAuth` and `@CurrentUser()` |
| A client created with the caller's header | `SupabaseService.forUser()` |
| A client created with the secret key | `SupabaseService.admin` |
| Verifying Stripe's signature by hand | `@VerifyWebhook('stripe')` |
| `pg_cron` calling the function over HTTP | `@Cron()`, or a BullMQ job scheduler |
| `supabase secrets set` | Your host's environment variables |
| `supabase.functions.invoke('name')` in the browser | `fetch()` with the access token |

#### The finished module

Here's everything above wired together, with both ways of running a job, of which you'll keep one:

[[CODE:49]]

[[CODE:50]]

`enableShutdownHooks()` lets a running job finish and passes its lease on when a deploy stops an instance.

#### Deployment

Nest deploys separately from Supabase, on anything that runs Node.js (see [Deployment](/deployment)). Host it close to your database's region, as every query crosses that distance.

Apply your migrations to the hosted project:

[[CODE:51]]

Set the same environment variables on your host, with the hosted project's values and the connection string from [Query Postgres directly](/recipes/supabase#query-postgres-directly). Each instance opens its own connections, for Drizzle and for BullMQ, so count them against your project's [connection limit](https://supabase.com/docs/guides/database/connection-management).

The webhook stores shouldn't change a schema while a new version boots, in the middle of a rolling deploy. Remove `migrate: true` from those two, and apply their migrations as a step before the new version starts, with `DATABASE_URL` set. BullMQ's can stay, as it runs in one transaction under an advisory lock:

[[CODE:52]]
