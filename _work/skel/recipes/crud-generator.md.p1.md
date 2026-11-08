### CRUD generator (TypeScript only)

Over the lifespan of a project, building new features often means adding new resources to the application. Each new resource typically requires the same set of repetitive operations.

#### Introduction

Consider a real-world scenario in which you need to expose CRUD endpoints for two entities, **User** and **Product**. Following best practices, you would have to perform several operations for each entity:

- Generate a module (`nest g mo`) to keep code organized and establish clear boundaries (grouping related components)
- Generate a controller (`nest g co`) to define CRUD routes (or queries/mutations for GraphQL applications)
- Generate a service (`nest g s`) to implement and isolate business logic
- Generate an entity class/interface to represent the resource data shape
- Generate Data Transfer Objects (or inputs for GraphQL applications) to define how the data will be sent over the network

To speed up this repetitive process, the [Nest CLI](/cli/overview) provides a generator (schematic) that generates all of this boilerplate code automatically.

> info **Note** The schematic supports generating **HTTP** controllers, **Microservice** controllers, **GraphQL** resolvers (both code first and schema first), and **WebSocket** Gateways.

#### Generating a new resource

To create a new resource, run the following command in the root directory of your project:

[[CODE:1]]

The `nest g resource` command generates not only the NestJS building blocks (module, service, and controller classes), but also an entity class, DTO classes, and the test (`.spec`) files.

Here's the generated controller file (for a REST API):

[[CODE:2]]

The command also creates placeholders for all the CRUD endpoints: routes for REST APIs, queries and mutations for GraphQL, and message handlers for both microservices and WebSocket gateways.

> info **Note** Generated service classes are **not** tied to any specific **ORM (or data source)**, which makes the generator generic enough to meet the needs of any project. By default, all methods contain placeholders that you can populate with the data sources specific to your project.

Likewise, to generate resolvers for a GraphQL application, select `GraphQL (code first)` (or `GraphQL (schema first)`) as your transport layer.

In this case, Nest generates a resolver class instead of a REST API controller:

[[CODE:3]]

> info **Hint** To skip generating test files, pass the `--no-spec` flag, as follows: `nest g resource users --no-spec`.

As shown below, the command not only creates all the boilerplate mutations and queries, but also wires everything together, using the `UsersService`, the `User` entity, and the DTOs.

[[CODE:4]]
