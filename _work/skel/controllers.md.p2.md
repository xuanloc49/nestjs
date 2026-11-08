#### Getting up and running

Even with `CatsController` fully defined, Nest doesn't know about it yet and won't create an instance of the class.

Controllers must always belong to a module, which is why we include the `controllers` array in the `@Module()` decorator. Since we haven't defined any modules other than the root `AppModule`, we'll use it to register `CatsController`:

[[CODE:29]]

With this metadata attached to the module class through the `@Module()` decorator, Nest can determine which controllers to mount.

#### Library-specific approach

So far, we've covered the standard Nest way of manipulating responses. The alternative is to use a library-specific [response object](https://expressjs.com/en/api.html#res), injected with the `@Res()` decorator. To highlight the differences, let's rewrite `CatsController` as follows:

[[CODE:30]]

This approach offers more flexibility by giving full control over the response object (e.g., header manipulation and access to library-specific features), but it should be used with caution. It is generally less clear and has some downsides. The main disadvantage is that your code becomes platform-dependent, since different underlying libraries may expose different APIs on the response object. It also makes testing harder, as you need to mock the response object, among other things.

In addition, this approach loses compatibility with Nest features that rely on standard response handling, such as interceptors and the `@HttpCode()` / `@Header()` decorators. To address this, enable the `passthrough` option:

[[CODE:31]]

This way, you can interact with the native response object (for example, to set cookies or headers based on specific conditions) while leaving the rest to the framework.
