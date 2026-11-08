#### nest add

Imports a library that has been packaged as a **nest library**, running its install schematic.

[[CODE:8]]

##### Arguments

| Argument | Description                        |
| -------- | ---------------------------------- |
| `<name>` | The name of the library to import. |

##### Options

| Option                | Description                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `--dry-run`           | Report the changes that would be made, without changing the filesystem.<br/> Alias: `-d` |
| `--skip-install`      | Skip package installation.<br/> Alias: `-s`                                              |
| `--project [project]` | Project that the library should be added to.<br/> Alias: `-p`                            |

#### nest upgrade

Upgrades an existing project to the latest NestJS major version.

[[CODE:9]]

##### Description

Run from the root of a NestJS v11 project, `nest upgrade` updates your dependencies to v12 and applies the mechanical parts of the migration:

- Refuses to run on Node.js releases that lack `require(esm)` (anything older than v20.19, or v22.x older than v22.12)
- Bumps every recognized `@nestjs/*` package to its v12-compatible major (`@nestjs/graphql`, `@nestjs/apollo`, and `@nestjs/mercurius` go to v14), and reports any other `@nestjs/*` package it doesn't recognize so you can review it yourself
- Bumps TypeScript to v6 (required by the v12 CLI and schematics), and raises `engines.node` in `package.json` to `>=20.19.0` if it declares a lower floor
- Migrates `nest-cli.json` off the deprecated `webpack` / `webpackConfigPath` options and onto `--builder rspack`, updating matching `package.json` scripts
- Renames the GraphQL `playground` option to `graphiql`, switches subscriptions from `subscriptions-transport-ws` to `graphql-ws`, and swaps the packages accordingly
- Replaces the legacy `nats` package with `@nats-io/transport-node` / `@nats-io/nats-core` and rewrites `nats` imports
- Moves library-specific `@nestjs/config` settings under `validationOptions.libraryOptions` and bumps Joi to v18 (the first release implementing Standard Schema)
- Bumps Jest to v30 (and `@types/jest` / `ts-jest` to matching releases) where present, and warns that Jest can `require()` the ESM-only v12 packages only on Node.js v24.9+
- Optionally installs and wires up [`@nestjs/observe`](/observability/overview). It prompts, unless you pass `--observe` or `--no-observe`
- Checks `tsconfig.json` and `tsconfig.build.json` for settings that TypeScript 6 or the ESM-only packages no longer support, such as a legacy `moduleResolution` or a missing `rootDir`
- Scans your sources and prints notes about behavior that changed but can't be migrated automatically, such as lifecycle hook ordering, refined pipe signatures, and structured logging params

The command finishes by installing the updated dependencies (unless `--skip-install` is passed) and printing a report of everything it changed, warned about, and left for you.

> warning **Warning** `nest upgrade` only bumps the **local** `@nestjs/cli` dependency. Update a globally installed CLI yourself with `npm i -g @nestjs/cli@latest`, and do it **before** running the upgrade, because the command itself ships with the CLI.

> info **Hint** The command deliberately does not migrate your project to ESM, Vitest, or oxlint. Those are the defaults for newly generated v12 projects, but existing projects can adopt them on their own schedule. See the [migration guide](/migration-guide) for the full picture.

##### Options

| Option                          | Description                                                                                                       |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `--dry-run`                     | Report the changes that would be made, without changing the filesystem.<br/> Alias: `-d`                          |
| `--skip-install`                | Skip package installation.<br/> Alias: `-s`                                                                       |
| `--observe` / `--no-observe`    | Set up `@nestjs/observe`, or skip the setup, without being prompted. Omit both to be prompted in an interactive terminal (the prompt defaults to no). Without a terminal, Observe is not set up. |
| `--tag [tag]`                   | Use an npm dist-tag (e.g., `next`) instead of the default version ranges.<br/> Alias: `-t`                        |
| `--collection [collectionName]` | Schematics collection to use. Pass the package name of an installed npm package that contains the schematic.<br/> Alias: `-c` |

#### nest deploy

Deploys your application to the cloud, powered by [Mau](https://mau.nestjs.com/).

[[CODE:10]]

##### Description

`nest deploy` is a thin wrapper around the Mau CLI. It locates the Mau binary and forwards every argument you pass to `mau deploy`, so any option Mau supports works here unchanged.

If Mau is not installed in your project, the command offers to add `@nestjs/mau` as a dev dependency and then continues. In a non-interactive environment (e.g., CI), the command fails instead of prompting, so install Mau explicitly first:

[[CODE:11]]

Once Mau starts, it owns the terminal, so its output and prompts reach you directly. See the [Deployment chapter](/deployment#easy-deployment-with-mau) for what Mau does and how to configure it.

#### nest info

Displays information about installed Nest packages and other useful system information. For example:

[[CODE:12]]

[[CODE:13]]
