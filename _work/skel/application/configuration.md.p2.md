#### Expandable variables

The `@nestjs/config` package supports environment variable expansion. With this technique, you can create nested environment variables, where one variable is referenced within the definition of another. For example:

[[CODE:45]]

With this construction, the variable `SUPPORT_EMAIL` resolves to `'support@mywebsite.com'`. The `${{ '{' }}...{{ '}' }}` syntax triggers resolving the value of the variable `APP_URL` inside the definition of `SUPPORT_EMAIL`.

> info **Hint** For this feature, the `@nestjs/config` package internally uses [dotenv-expand](https://github.com/motdotla/dotenv-expand).

Enable environment variable expansion with the `expandVariables` property of the options object passed to `ConfigModule.forRoot()`, as shown below. Instead of `true`, you can also pass an object with options for `dotenv-expand`.

[[CODE:46]]

#### Using in the `main.ts`

Although the configuration is stored in a service, you can still use it in the `main.ts` file, for example, to read variables such as the application port or the CORS host.

To access it, use the `app.get()` method with the service class:

[[CODE:47]]

You can then use it as usual, by calling the `get()` method with the configuration key:

[[CODE:48]]
