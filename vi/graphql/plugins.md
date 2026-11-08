### Plugin với Apollo

Plugin cho phép bạn mở rộng chức năng cốt lõi của Apollo Server bằng cách thực hiện các thao tác tùy chỉnh khi có những event nhất định. Các event này tương ứng với từng giai đoạn trong vòng đời của một GraphQL request, và với việc khởi động chính Apollo Server (xem [plugin](https://www.apollographql.com/docs/apollo-server/integrations/plugins/) trong tài liệu Apollo). Ví dụ, một plugin log cơ bản có thể log chuỗi GraphQL query của mỗi request gửi tới Apollo Server.

#### Custom plugin <a id="custom-plugins"></a>

Để tạo một plugin, hãy khai báo một class được chú thích bằng decorator `@Plugin()`, được export từ package `@nestjs/apollo`. Để có autocompletion tốt hơn, hãy implement thêm interface `ApolloServerPlugin` từ package `@apollo/server`.

```typescript
import { ApolloServerPlugin, GraphQLRequestListener } from '@apollo/server';
import { Plugin } from '@nestjs/apollo';

@Plugin()
export class LoggingPlugin implements ApolloServerPlugin {
  async requestDidStart(): Promise<GraphQLRequestListener<any>> {
    console.log('Request started');
    return {
      async willSendResponse() {
        console.log('Will send response');
      },
    };
  }
}
```

Khi đã có class này, hãy đăng ký `LoggingPlugin` làm provider:

```typescript
@Module({
  providers: [LoggingPlugin],
})
export class CommonModule {}
```

Nest tự động khởi tạo plugin và áp dụng nó cho Apollo Server.

#### Dùng plugin bên ngoài <a id="using-external-plugins"></a>

Apollo Server cung cấp sẵn một số plugin. Để dùng một plugin đã có, hãy import nó và thêm nó vào mảng `plugins`:

```typescript
import { ApolloServerPluginCacheControl } from '@apollo/server/plugin/cacheControl';

GraphQLModule.forRoot({
  // ...
  plugins: [ApolloServerPluginCacheControl({ defaultMaxAge: 5 })],
}),
```

> info **Gợi ý** Plugin `ApolloServerPluginCacheControl` được export từ entry point `@apollo/server/plugin/cacheControl` của package `@apollo/server`.

#### Plugin với Mercurius <a id="plugins-with-mercurius"></a>

Một số plugin Fastify dành riêng cho Mercurius phải được load sau plugin Mercurius trong cây plugin (xem [plugin](https://mercurius.dev/#/docs/plugins) trong tài liệu Mercurius).

> warning **Cảnh báo** [mercurius-upload](https://github.com/mercurius-js/mercurius-upload) là một ngoại lệ: hãy đăng ký nó trong file main.

Để làm việc này, `MercuriusDriver` cung cấp một tùy chọn cấu hình `plugins` không bắt buộc. Nó nhận một mảng object với hai thuộc tính: `plugin` và `options` của nó. Ví dụ, đăng ký [cache plugin](https://github.com/mercurius-js/cache) trông như thế này:

```typescript
GraphQLModule.forRoot({
  driver: MercuriusDriver,
  // ...
  plugins: [
    {
      plugin: cache,
      options: {
        ttl: 10,
        policy: {
          Query: {
            add: true
          }
        }
      },
    }
  ]
}),
```
