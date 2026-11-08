### CI/CD integration

> info **Hint** This chapter covers the Nest Devtools integration with the Nest framework. If you are looking for the Devtools application, visit the [Devtools](https://devtools.nestjs.com) website. CI/CD integration is available on the **[Enterprise](https://devtools.nestjs.com/settings)** plan.

Local usage is great for exploring your application as you build it, but the real payoff comes when Devtools becomes part of your delivery pipeline. CI/CD integration publishes a snapshot of your application's graph on every build. You get a running history of how your architecture evolves and, more importantly, an automatic report on every pull request that shows exactly what changed structurally. It's the difference between hoping a refactor didn't break anything and knowing it didn't.

See why teams rely on CI/CD integration to catch architectural drift before it ships:

<figure>
  <iframe
    width="1000"
    height="565"
    src="https://www.youtube.com/embed/r5RXcBrnEQ8"
    title="YouTube video player"
    frameBorder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowFullScreen
  ></iframe>
</figure>

#### Publishing graphs

First, wire up the application bootstrap file (`main.ts`) to use the `GraphPublisher` class, exported from `@nestjs/devtools-integration` (see the [Devtools overview](/devtools/overview) if you haven't installed it yet):

[[CODE:1]]

Here, `GraphPublisher` pushes your serialized graph to the centralized registry. `PUBLISH_GRAPH` is a custom environment variable that distinguishes a CI/CD publish run from a regular application bootstrap. Setting `preview` to `true` bootstraps the application in preview mode, which means the constructors and lifecycle hooks of your controllers, enhancers, and providers don't execute. This isn't **required**, but it keeps CI runs fast and simple (no database connection needed, for example).

The shape of `publishOptions` depends on your CI/CD provider. The sections below cover the most popular ones. If your provider isn't listed, the underlying fields are the same everywhere, so you can adapt the configuration in minutes.

Once your graph publishes successfully, you'll see output like this in your workflow logs:

<figure><img src="/assets/devtools/graph-published-terminal.png" /></figure>

Every published graph shows up as a new entry on the project's page:

<figure><img src="/assets/devtools/project.png" /></figure>

#### Reports

Devtools generates a report for every build, **as long as** a matching snapshot already exists in the registry. If you open a pull request against `master` and a graph for `master` was already published, Devtools detects the differences and builds a report automatically. Otherwise, there's nothing to compare against yet.

Find your reports on the project's page (see [organizations](https://devtools.nestjs.com/organizations)).

<figure><img src="/assets/devtools/report.png" /></figure>

This is where Devtools really earns its keep: catching changes that slip past code review. Say someone quietly changes the scope of a **deeply nested provider**. That's easy to miss in a diff, and impossible to miss in a report. Remove a guard from an endpoint, and it shows up as an affected change immediately. If integration or e2e tests didn't cover that route, you might not have noticed until it was too late. Devtools catches it at review time instead.

The same goes for **large codebases**: make a module global, and you immediately see how many new edges landed on the graph, usually a strong signal that something needs a second look.

Reports are also a great artifact to link in your pull request description. Instead of asking a reviewer to trust that "this only touches the billing module," you can point them at the exact set of nodes and edges that changed, turning an architectural claim into something they can verify in seconds.

#### Build preview

You can replay every published graph: click **Preview** to see exactly how it looked at that point in time. When a report is available, differences are highlighted directly on the graph:

- green nodes represent added elements
- light white nodes represent updated elements
- red nodes represent deleted elements

Here's what that looks like:

<figure><img src="/assets/devtools/nodes-selection.png" /></figure>

Being able to rewind and compare graphs makes troubleshooting straightforward, with no more guessing what changed and when. Set things up so that every pull request (or even every commit) gets its own snapshot in the registry, and you'll always have a clear trail to follow. Think of Devtools as version control that understands how Nest assembles your application, and can **show you** the difference instead of just describing it.

#### Integrations: GitHub Actions

Create a new workflow file in `.github/workflows` (for example, `publish-graph.yml`) with the following content:

[[CODE:2]]

> info **Hint** For better security, store `DEVTOOLS_API_KEY` as a GitHub secret instead of hardcoding it. See [Creating secrets for a repository](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository).

This workflow runs on every pull request and on direct pushes to `master`. Adapt it to your project's needs; the one requirement is to provide the environment variables that `GraphPublisher` relies on.

Before the workflow can run, fill in the one remaining variable: `DEVTOOLS_API_KEY`. Generate a dedicated API key for your project on the **[API keys page](https://devtools.nestjs.com/settings/manage-api-keys)**.

Finally, go back to `main.ts` and fill in the `publishOptions` object we left empty earlier:

[[CODE:3]]

For the smoothest experience, we also recommend installing the **GitHub application** for your project by clicking "Integrate GitHub app" (see below). It's optional, but well worth it.

<figure><img src="/assets/devtools/integrate-github-app.png" /></figure>

With the app installed, you see the status of your preview and report generation right inside the pull request:

<figure><img src="/assets/devtools/actions-preview.png" /></figure>

#### Integrations: Gitlab Pipelines

Create a `.gitlab-ci.yml` file in your project root with the following definition:

[[CODE:4]]

> info **Hint** As with GitHub, we recommend storing `DEVTOOLS_API_KEY` as a CI/CD secret instead of committing it.

This pipeline runs on every merge request and on direct pushes to `master`. Adjust it to fit your project, but make sure the environment variables that `GraphPublisher` needs are always present.

One variable in this definition still needs a real value: `DEVTOOLS_API_KEY`. Generate a dedicated API key for your project on the **[API keys page](https://devtools.nestjs.com/settings/manage-api-keys)**.

Finally, go back to `main.ts` and fill in the `publishOptions` object we left empty earlier:

[[CODE:5]]

#### Other CI/CD tools

The integration doesn't depend on GitHub or GitLab. All `GraphPublisher` needs is a handful of values that describe the current build (what triggered it, which commit, which branch), so it works with any provider, including [Bitbucket Pipelines](https://bitbucket.org/product/features/pipelines), [CircleCI](https://circleci.com/), and more.

Here's the full `publishOptions` shape and what each field represents, so you can wire up any pipeline:

[[CODE:6]]

Most of these values are available in your CI/CD provider's built-in environment variables. See the [CircleCI built-in environment variables](https://circleci.com/docs/variables/#built-in-environment-variables) and [Bitbucket variables and secrets](https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/) references as a starting point.

For your pipeline triggers, we recommend the following setup:

- `push`: only for branches that represent a deployment environment, e.g., `master`, `main`, `staging`, or `production`.
- `pull request`: always, or at least when the **target branch** is a deployment environment (see above).

This combination keeps your registry populated with a snapshot of every deployable state of `master`, while still generating a report on every pull request that targets it. That pairing is what makes reports useful in the first place.
