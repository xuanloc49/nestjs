### Read-Eval-Print-Loop (REPL)

A REPL is an interactive environment that takes single user inputs, executes them, and returns the result to the user. The REPL feature lets you inspect your dependency graph and call methods on your providers (and controllers) directly from your terminal.

#### Usage

To run your NestJS application in REPL mode, create a new `repl.ts` file (alongside the existing `main.ts` file) and add the following code:

[[CODE:1]]

Then start the REPL from your terminal with the following command:

[[CODE:2]]

> info **Hint** The `repl()` function returns a promise that resolves to a [Node.js REPL server](https://nodejs.org/api/repl.html) object. You can pass [Node.js REPL options](https://nodejs.org/api/repl.html#replstartoptions) as its second argument.

Once it's running, you should see the following messages in your console:

[[CODE:3]]

You can now interact with your dependency graph. For instance, you can retrieve the `AppService` instance (this example uses the starter project) and call its `getHello()` method:

[[CODE:4]]

You can execute any JavaScript code from your terminal. For example, you can assign the `AppController` instance to a local variable and use `await` to call an asynchronous method:

[[CODE:5]]

To display all public methods available on a given provider or controller, use the `methods()` function, as follows:

[[CODE:6]]

To print all registered modules as a list, together with their controllers and providers, use `debug()`:

[[CODE:7]]

Here's a quick demo:

<figure><img src="/assets/repl.gif" alt="REPL example" /></figure>

The following section describes the built-in native functions in more detail.

#### Native functions

The built-in NestJS REPL comes with a few native functions that are globally available when you start the REPL. Call `help()` to list them.

If you don't remember the signature (i.e., the expected parameters and return type) of a function, use `<function_name>.help`. For instance:

[[CODE:8]]

> info **Hint** These function interfaces are written in [TypeScript function type expression syntax](https://www.typescriptlang.org/docs/handbook/2/functions.html#function-type-expressions).

| Function     | Description                                                                                                        | Signature                                                             |
| ------------ | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| `debug`      | Prints all registered modules as a list, together with their controllers and providers. Pass a module (e.g., `debug(MyModule)`) to print only that module's components. | `debug(moduleCls?: ClassRef \| string) => void`                       |
| `get` or `$` | Retrieves an instance of a provider or controller; throws an exception if it can't be found.                       | `get(token: InjectionToken) => any`                                   |
| `help`       | Displays all available REPL native functions.                                                                      | `help() => void`                                                      |
| `methods`    | Displays all public methods available on a given provider or controller.                                           | `methods(token: ClassRef \| string) => void`                          |
| `resolve`    | Resolves a transient or request-scoped instance of a provider or controller; throws an exception if it can't be found. | `resolve(token: InjectionToken, contextId: any) => Promise<any>`      |
| `select`     | Navigates through the modules tree, for example, to pull out a specific instance from the selected module.        | `select(token: DynamicModule \| ClassRef) => INestApplicationContext` |

#### Watch mode

During development, it's useful to run the REPL in watch mode so that code changes are reflected automatically:

[[CODE:9]]

The downside is that the REPL's command history is discarded after each reload. To preserve it, modify your `bootstrap()` function as follows:

[[CODE:10]]

The history is now preserved between runs and reloads.
