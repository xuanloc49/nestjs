### Ứng dụng standalone

Có nhiều cách để mount một ứng dụng Nest. Bạn có thể tạo một web app, một microservice, hoặc một **ứng dụng standalone** Nest thuần (không có network listener nào). Một ứng dụng standalone là một wrapper quanh **IoC container** của Nest, nơi chứa mọi class đã được khởi tạo. Thông qua object ứng dụng standalone, bạn có thể lấy tham chiếu tới bất kỳ instance nào đã tồn tại từ bất kỳ module nào được import. Điều này cho phép bạn tận dụng framework Nest ở bất cứ đâu, kể cả các **CRON** job dạng script. Bạn thậm chí có thể xây một **CLI** dựa trên nó.

#### Bắt đầu <a id="getting-started"></a>

Để tạo một ứng dụng standalone Nest, hãy dùng cấu trúc sau:

```typescript
@@filename()
async function bootstrap() {
  const app = await NestFactory.createApplicationContext(AppModule);
  // your application logic here ...
}
await bootstrap();
```

#### Lấy provider từ static module <a id="retrieving-providers-from-static-modules"></a>

Object ứng dụng standalone cho phép bạn lấy tham chiếu tới bất kỳ instance nào được đăng ký trong ứng dụng Nest. Giả sử một provider `TasksService` nằm trong một `TasksModule`, module này được `AppModule` import. Class này cung cấp một tập method mà bạn muốn gọi từ bên trong một CRON job.

```typescript
@@filename()
const tasksService = app.get(TasksService);
```

Để truy cập instance `TasksService`, hãy dùng method `get()`. Nó hoạt động như một **truy vấn** tìm một instance trong từng module đã đăng ký, và nhận token của bất kỳ provider nào. Để kiểm tra context một cách chặt chẽ, hãy truyền một options object có thuộc tính `strict: true`. Khi tùy chọn này có hiệu lực, bạn phải điều hướng tới một module cụ thể để lấy một instance từ context đã chọn đó.

```typescript
@@filename()
const tasksService = app.select(TasksModule).get(TasksService, { strict: true });
```

Bảng sau tóm tắt các method có sẵn để lấy tham chiếu instance từ object ứng dụng standalone.

<table>
  <tr>
    <td>
      <code>get()</code>
    </td>
    <td>
      Lấy một instance của controller hoặc provider (bao gồm guard, filter, v.v.) có trong application context.
    </td>
  </tr>
  <tr>
    <td>
      <code>select()</code>
    </td>
    <td>
      Điều hướng qua đồ thị module để lấy ra một instance cụ thể của module được chọn (dùng cùng với strict mode, như mô tả ở trên).
    </td>
  </tr>
</table>

> info **Gợi ý** Ở chế độ không strict, root module được chọn mặc định. Để chọn bất kỳ module nào khác, hãy tự điều hướng qua đồ thị module, từng bước một.

Một ứng dụng standalone không có network listener nào, nên các tính năng Nest gắn với việc xử lý request (ví dụ middleware, interceptor, pipe và guard) không có trong context này.

Ví dụ, kể cả khi bạn đăng ký một global interceptor trong ứng dụng rồi lấy một instance controller bằng method `app.get()`, interceptor sẽ không được thực thi khi bạn gọi các method của controller.

#### Lấy provider từ dynamic module <a id="retrieving-providers-from-dynamic-modules"></a>

Khi làm việc với [dynamic module](/fundamentals/dynamic-modules), hãy truyền cho `app.select()` chính object đại diện cho dynamic module đã được đăng ký trong ứng dụng. Ví dụ:

```typescript
@@filename()
export const dynamicConfigModule = ConfigModule.register({ folder: './config' });

@Module({
  imports: [dynamicConfigModule],
})
export class AppModule {}
```

Sau đó bạn có thể chọn module đó:

```typescript
@@filename()
const configService = app.select(dynamicConfigModule).get(ConfigService, { strict: true });
```

#### Giai đoạn kết thúc <a id="terminating-phase"></a>

Nếu bạn muốn process Node.js thoát sau khi script chạy xong (ví dụ với một script chạy CRON job), hãy gọi method `app.close()` ở cuối hàm `bootstrap()`:

```typescript
@@filename()
async function bootstrap() {
  const app = await NestFactory.createApplicationContext(AppModule);
  // application logic...
  await app.close();
}
await bootstrap();
```

Như mô tả trong chương [lifecycle event](/fundamentals/lifecycle-events), gọi `app.close()` sẽ kích hoạt các lifecycle hook của quá trình shutdown.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có trong [sample ứng dụng standalone](https://github.com/nestjs/nest/tree/master/sample/18-context) trên GitHub.
