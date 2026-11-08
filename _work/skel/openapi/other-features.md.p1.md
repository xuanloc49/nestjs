### Other features

This page covers other features of the Swagger module that you may find useful.

#### Global prefix

To ignore the global prefix set through `setGlobalPrefix()`, use the `ignoreGlobalPrefix` option:

[[CODE:1]]

#### Global parameters

To define parameters for all routes, use `DocumentBuilder`:

[[CODE:2]]

#### Global responses

To define global responses for all routes, use `DocumentBuilder`. This is useful for setting up consistent responses across all endpoints in your application, such as error codes like `401 Unauthorized` or `500 Internal Server Error`.

[[CODE:3]]

#### Multiple specifications

The `SwaggerModule` supports multiple specifications. In other words, you can serve different documentation, with different UIs, on different endpoints.

To support multiple specifications, your application must be written with a modular approach. The `createDocument()` method takes a third argument, `extraOptions`, which is an object with an `include` property. The `include` property takes an array of modules.

Set up support for multiple specifications as shown below:

[[CODE:4]]

Now start your server with the following command:

[[CODE:5]]

Navigate to `http://localhost:3000/api/cats` to see the Swagger UI for cats:

<figure><img src="/assets/swagger-cats.png" /></figure>

In turn, `http://localhost:3000/api/dogs` will expose the Swagger UI for dogs:

<figure><img src="/assets/swagger-dogs.png" /></figure>

#### Dropdown in the explorer bar

To list multiple specifications in the dropdown menu of the explorer bar, set `explorer: true` and configure `swaggerOptions.urls` in your `SwaggerCustomOptions`.

> info **Hint** Make sure that `swaggerOptions.urls` points to the JSON format of your Swagger documents. To specify the JSON document's path, use the `jsonDocumentUrl` option of `SwaggerCustomOptions`. For more options, see [setup options](/openapi/introduction#setup-options).

Here's how to select multiple specifications from a dropdown in the explorer bar:

[[CODE:6]]

This example sets up a main API along with separate specifications for cats and dogs, each accessible from the dropdown in the explorer bar.
