### Nest Commander

Expanding on the [standalone applications](/standalone-applications) chapter, the [nest-commander](https://nest-commander.jaymcdoniel.dev) package lets you write command-line applications with a structure similar to a typical Nest application.

> info **Note** `nest-commander` is a third-party package and is not managed by the NestJS core team. Please report any issues with the library in the [nest-commander repository](https://github.com/jmcdo29/nest-commander/issues/new/choose).

#### Installation

First, install the package:

[[CODE:1]]

#### A Command file

`nest-commander` lets you write command-line applications with [decorators](https://www.typescriptlang.org/docs/handbook/decorators.html): the `@Command()` decorator for classes and the `@Option()` decorator for methods of those classes. Every command class should extend the `CommandRunner` abstract class and be decorated with the `@Command()` decorator.

Nest treats every command as an `@Injectable()`, so dependency injection works as usual. The `CommandRunner` abstract class ensures that every command has a `run()` method that returns a `Promise<void>` and takes the parameters `string[], Record<string, any>`. The `run()` method is where your command's logic starts. Its first argument is an array of all parameters that didn't match an option flag, in case you need to work with multiple parameters. In the second argument, the options object, the property names match the `name` property given to the `@Option()` decorators, and their values are the return values of the corresponding option handlers. For better type safety, you can also create an interface for your options.

#### Running the Command

In a NestJS application, you use the `NestFactory` to create a server and run it with `listen()`. Similarly, the `nest-commander` package exposes an API to run your command-line application: import the `CommandFactory`, call its static `run()` method, and pass in the root module of your application:

[[CODE:2]]

By default, Nest's logger is disabled when using the `CommandFactory`. To enable it, pass a logger as the second argument to the `run()` method. You can provide either a custom NestJS logger or an array of the log levels you want to keep. For example, pass `['error']` to print only Nest's error logs.

[[CODE:3]]

Under the hood, `CommandFactory` calls `NestFactory` for you and calls `app.close()` when the command finishes, so you don't need to worry about memory leaks. To add error handling, wrap the `run()` call in a `try/catch` block, or chain a `.catch()` call to the `bootstrap()` call.

#### Testing

`nest-commander` provides testing utilities that fit in with the rest of the NestJS ecosystem. Instead of using the `CommandFactory` to build the command in test mode, use the `CommandTestFactory` from the `nest-commander-testing` package and pass in your module metadata, similarly to how `Test.createTestingModule()` from `@nestjs/testing` works. In fact, it uses `@nestjs/testing` under the hood. You can still chain `overrideProvider()` calls before calling `compile()` to swap out providers in the test.

#### Putting it all together

The following class defines a CLI command that can take the subcommand `basic` or be called directly. It supports the `-n`, `-s`, and `-b` flags (along with their long forms), with a custom parser for each option. The `--help` flag is also supported, as is customary with commander.

[[CODE:4]]

Make sure the command class is added to a module:

[[CODE:5]]

Then, to run the CLI, add the following to your `main.ts` file:

[[CODE:6]]

You now have a command-line application.

#### More Information

Visit the [nest-commander docs site](https://nest-commander.jaymcdoniel.dev) for more information, examples, and API documentation.
