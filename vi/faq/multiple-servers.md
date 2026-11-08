### HTTPS

Để tạo một ứng dụng dùng giao thức HTTPS, hãy đặt thuộc tính `httpsOptions` trong options object được truyền cho method `NestFactory.create()`:

```typescript
const httpsOptions = {
  key: fs.readFileSync('./secrets/private-key.pem'),
  cert: fs.readFileSync('./secrets/public-certificate.pem'),
};
const app = await NestFactory.create(AppModule, {
  httpsOptions,
});
await app.listen(process.env.PORT ?? 3000);
```

Nếu bạn dùng `FastifyAdapter`, hãy tạo ứng dụng như sau:

```typescript
const app = await NestFactory.create<NestFastifyApplication>(
  AppModule,
  new FastifyAdapter({ https: httpsOptions }),
);
```

#### Nhiều server chạy đồng thời <a id="multiple-simultaneous-servers"></a>

Recipe sau cho thấy cách tạo một ứng dụng Nest lắng nghe đồng thời trên nhiều port (ví dụ trên một port HTTP và một port HTTPS):

```typescript
const httpsOptions = {
  key: fs.readFileSync('./secrets/private-key.pem'),
  cert: fs.readFileSync('./secrets/public-certificate.pem'),
};

const server = express();
const app = await NestFactory.create(AppModule, new ExpressAdapter(server));
await app.init();

const httpServer = http.createServer(server).listen(3000);
const httpsServer = https.createServer(httpsOptions, server).listen(443);
```

Vì chúng ta tự tạo các server bằng `http.createServer()` và `https.createServer()`, Nest không đóng chúng khi bạn gọi `app.close()` hoặc khi process nhận tín hiệu kết thúc. Bạn cần tự đóng chúng, ví dụ bằng một provider implement hook `OnApplicationShutdown`:

```typescript
@Injectable()
export class ShutdownObserver implements OnApplicationShutdown {
  private httpServers: http.Server[] = [];

  public addHttpServer(server: http.Server): void {
    this.httpServers.push(server);
  }

  public async onApplicationShutdown(): Promise<void> {
    await Promise.all(
      this.httpServers.map(
        (server) =>
          new Promise((resolve, reject) => {
            server.close((error) => {
              if (error) {
                reject(error);
              } else {
                resolve(null);
              }
            });
          }),
      ),
    );
  }
}

const shutdownObserver = app.get(ShutdownObserver);
shutdownObserver.addHttpServer(httpServer);
shutdownObserver.addHttpServer(httpsServer);
```

> info **Gợi ý** `ExpressAdapter` được import từ package `@nestjs/platform-express`. Các module `http` và `https` có sẵn trong Node.js.

> warning **Cảnh báo** Recipe này không hoạt động với [GraphQL subscription](/graphql/subscriptions).
