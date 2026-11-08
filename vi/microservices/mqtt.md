### MQTT

[MQTT](https://mqtt.org/) (Message Queuing Telemetry Transport) là một giao thức messaging mã nguồn mở, gọn nhẹ, được tối ưu cho độ trễ thấp. Nó cung cấp một cách có thể mở rộng và tiết kiệm chi phí để kết nối các thiết bị theo mô hình **publish/subscribe**. Một hệ thống giao tiếp xây trên MQTT gồm server publish, một broker, và một hoặc nhiều client. Giao thức được thiết kế cho các thiết bị hạn chế tài nguyên và cho các mạng băng thông thấp, độ trễ cao hoặc không ổn định.

#### Cài đặt <a id="installation"></a>

Để bắt đầu xây dựng microservice dựa trên MQTT, trước tiên hãy cài package cần thiết:

```bash
$ npm i --save mqtt
```

#### Tổng quan <a id="overview"></a>

Để dùng transporter MQTT, hãy truyền options object sau cho method `createMicroservice()`:

```typescript
@@filename(main)
const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
  transport: Transport.MQTT,
  options: {
    url: 'mqtt://localhost:1883',
  },
});
@@switch
const app = await NestFactory.createMicroservice(AppModule, {
  transport: Transport.MQTT,
  options: {
    url: 'mqtt://localhost:1883',
  },
});
```

> info **Gợi ý** Enum `Transport` được import từ package `@nestjs/microservices`.

#### Tùy chọn <a id="options"></a>

Object `options` phụ thuộc vào transporter được chọn. Transporter <strong>MQTT</strong> cung cấp các [tùy chọn client của MQTT.js](https://github.com/mqttjs/MQTT.js/#mqttclientstreambuilder-options), cũng như các thuộc tính `url`, `subscribeOptions` (xem [Quality of Service](#quality-of-service-qos)) và `userProperties` (xem [record builder](#record-builders)). Ở phía server, thuộc tính `maxConnectionAttempts` giới hạn số lần thử thiết lập kết nối ban đầu (mặc định: `-1`, tức không giới hạn). Giới hạn này không áp dụng cho các lần kết nối lại sau khi server đã kết nối.

#### Client

Như với các transporter microservice khác, bạn có <a href="/microservices/basics#client-producer-class">nhiều lựa chọn</a> để tạo một instance `ClientProxy` cho MQTT.

Một cách để tạo instance là dùng `ClientsModule`. Import nó và dùng method `register()` của nó để truyền một options object có cùng các thuộc tính như ở trên cho method `createMicroservice()`, cộng thêm thuộc tính `name` dùng làm injection token. Đọc thêm về `ClientsModule` trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

```typescript
@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'MATH_SERVICE',
        transport: Transport.MQTT,
        options: {
          url: 'mqtt://localhost:1883',
        }
      },
    ]),
  ]
  ...
})
```

Bạn cũng có thể tạo client bằng `ClientProxyFactory` hoặc decorator `@Client()`. Cả hai đều được mô tả trong <a href="/microservices/basics#client-producer-class">phần client của trang tổng quan</a>.

#### Context

Trong các tình huống phức tạp hơn, bạn có thể cần thêm thông tin về request đi vào. Với transporter MQTT, bạn có thể truy cập object `MqttContext`.

```typescript
@@filename()
@MessagePattern('notifications')
getNotifications(@Payload() data: number[], @Ctx() context: MqttContext) {
  console.log(`Topic: ${context.getTopic()}`);
}
@@switch
@Bind(Payload(), Ctx())
@MessagePattern('notifications')
getNotifications(data, context) {
  console.log(`Topic: ${context.getTopic()}`);
}
```

> info **Gợi ý** `@Payload()`, `@Ctx()` và `MqttContext` được import từ package `@nestjs/microservices`.

Để truy cập [packet](https://github.com/mqttjs/mqtt-packet) MQTT gốc, hãy dùng method `getPacket()` của object `MqttContext`:

```typescript
@@filename()
@MessagePattern('notifications')
getNotifications(@Payload() data: number[], @Ctx() context: MqttContext) {
  console.log(context.getPacket());
}
@@switch
@Bind(Payload(), Ctx())
@MessagePattern('notifications')
getNotifications(data, context) {
  console.log(context.getPacket());
}
```

#### Wildcard <a id="wildcards"></a>

Một subscription có thể nhắm tới một topic cụ thể, hoặc có thể chứa wildcard. Có hai wildcard: `+` khớp với một cấp topic, và `#` khớp với nhiều cấp topic.

```typescript
@@filename()
@MessagePattern('sensors/+/temperature/+')
getTemperature(@Ctx() context: MqttContext) {
  console.log(`Topic: ${context.getTopic()}`);
}
@@switch
@Bind(Ctx())
@MessagePattern('sensors/+/temperature/+')
getTemperature(context) {
  console.log(`Topic: ${context.getTopic()}`);
}
```

#### Quality of Service (QoS)

Mặc định, các subscription được tạo bằng decorator `@MessagePattern()` và `@EventPattern()` dùng QoS 0. Nếu bạn cần QoS cao hơn, hãy đặt nó ở phạm vi global bằng khối `subscribeOptions` khi thiết lập kết nối:

```typescript
@@filename(main)
const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
  transport: Transport.MQTT,
  options: {
    url: 'mqtt://localhost:1883',
    subscribeOptions: {
      qos: 2
    },
  },
});
@@switch
const app = await NestFactory.createMicroservice(AppModule, {
  transport: Transport.MQTT,
  options: {
    url: 'mqtt://localhost:1883',
    subscribeOptions: {
      qos: 2
    },
  },
});
```

#### QoS theo từng pattern <a id="per-pattern-qos"></a>

Bạn có thể ghi đè QoS của subscription cho từng pattern riêng bằng cách truyền thuộc tính `qos` trong object extras, tham số thứ hai của decorator `@MessagePattern()` hoặc `@EventPattern()`. Các pattern không có `qos` riêng sẽ dùng giá trị global `subscribeOptions.qos`.

```typescript
@@filename()
@EventPattern('critical-events', { qos: 2 })
handleCriticalEvent(@Payload() data: any) {
  // This subscription uses QoS 2
}

@EventPattern('metrics', { qos: 0 })
handleMetrics(@Payload() data: any) {
  // This subscription uses QoS 0
}
@@switch
@Bind(Payload())
@EventPattern('critical-events', { qos: 2 })
handleCriticalEvent(data) {
  // This subscription uses QoS 2
}

@Bind(Payload())
@EventPattern('metrics', { qos: 0 })
handleMetrics(data) {
  // This subscription uses QoS 0
}
```

#### Record builder <a id="record-builders"></a>

Để cấu hình các tùy chọn của message (điều chỉnh mức QoS, đặt cờ Retain hoặc DUP, hoặc thêm thuộc tính vào payload), hãy dùng class `MqttRecordBuilder`. Ví dụ, record sau đặt QoS thành `1` bằng method `setQoS()` và thêm một user property bằng method `setProperties()`:

```typescript
const userProperties = { 'x-version': '1.0.0' };
const record = new MqttRecordBuilder(':cat:')
  .setProperties({ userProperties })
  .setQoS(1)
  .build();
client.send('replace-emoji', record).subscribe(...);
```

> info **Gợi ý** Class `MqttRecordBuilder` được export từ package `@nestjs/microservices`.

Ở phía server, bạn có thể đọc các tùy chọn này qua `MqttContext`:

```typescript
@@filename()
@MessagePattern('replace-emoji')
replaceEmoji(@Payload() data: string, @Ctx() context: MqttContext): string {
  const { properties: { userProperties } } = context.getPacket();
  return userProperties['x-version'] === '1.0.0' ? '🐱' : '🐈';
}
@@switch
@Bind(Payload(), Ctx())
@MessagePattern('replace-emoji')
replaceEmoji(data, context) {
  const { properties: { userProperties } } = context.getPacket();
  return userProperties['x-version'] === '1.0.0' ? '🐱' : '🐈';
}
```

Để cấu hình user property cho mọi request do một client gửi đi, hãy truyền chúng làm tùy chọn cho `ClientProxyFactory`:

```typescript
import { Module } from '@nestjs/common';
import { ClientProxyFactory, Transport } from '@nestjs/microservices';

@Module({
  providers: [
    {
      provide: 'API_v1',
      useFactory: () =>
        ClientProxyFactory.create({
          transport: Transport.MQTT,
          options: {
            url: 'mqtt://localhost:1883',
            userProperties: { 'x-version': '1.0.0' },
          },
        }),
    },
  ],
})
export class ApiModule {}
```

Bắt đầu từ NestJS v12.1.3, một message handler cũng có thể trả về một record. Nest gửi dữ liệu của record làm reply và áp dụng các tùy chọn của record (ví dụ mức QoS và các property) cho message reply:

```typescript
@MessagePattern('replace-emoji')
replaceEmoji() {
  return new MqttRecordBuilder(':cat:')
    .setProperties({ userProperties: { 'x-version': '1.0.0' } })
    .setQoS(1)
    .build();
}
```

#### Cập nhật trạng thái instance <a id="instance-status-updates"></a>

Để nhận cập nhật real-time về kết nối và trạng thái của instance driver bên dưới, hãy subscribe stream `status`. Stream này cung cấp các cập nhật trạng thái riêng của driver được chọn. Với driver MQTT, stream `status` phát ra các event `connected`, `disconnected`, `reconnecting` và `closed`.

```typescript
this.client.status.subscribe((status: MqttStatus) => {
  console.log(status);
});
```

> info **Gợi ý** Type `MqttStatus` được import từ package `@nestjs/microservices`.

Tương tự, bạn có thể subscribe stream `status` của server để nhận thông báo về trạng thái của server.

```typescript
const server = app.connectMicroservice<MicroserviceOptions>(...);
server.status.subscribe((status: MqttStatus) => {
  console.log(status);
});
```

#### Lắng nghe các event của MQTT <a id="listening-to-mqtt-events"></a>

Trong một số trường hợp, bạn có thể muốn lắng nghe các event nội bộ do microservice phát ra. Ví dụ, bạn có thể lắng nghe event `error` để kích hoạt thêm các thao tác khi có lỗi xảy ra. Để làm vậy, hãy dùng method `on()`, như bên dưới:

```typescript
this.client.on('error', (err) => {
  console.error(err);
});
```

Tương tự, bạn có thể lắng nghe các event nội bộ của server:

```typescript
server.on<MqttEvents>('error', (err) => {
  console.error(err);
});
```

> info **Gợi ý** Type `MqttEvents` được import từ package `@nestjs/microservices`.

Bắt đầu từ NestJS v12.1.2, các listener được đăng ký bằng method `on()` của client vẫn được giữ cho tới khi bạn gọi `close()`, nên chúng cũng được gắn vào MQTT client mới được tạo ở lời gọi `send()` hoặc `emit()` tiếp theo sau khi client trước đã đóng mà không kết nối lại (ví dụ khi `reconnectPeriod` là `0`). Các lần đăng ký không được khử trùng lặp, nên hãy đăng ký mỗi listener một lần thay vì đăng ký lại từ callback của nó hoặc sau mỗi lần kết nối lại.

#### Truy cập driver bên dưới <a id="underlying-driver-access"></a>

Với các use case nâng cao hơn, bạn có thể cần truy cập instance driver bên dưới, ví dụ để tự đóng kết nối hoặc dùng các method riêng của driver. Tuy nhiên, trong hầu hết các trường hợp, bạn **không cần** truy cập trực tiếp driver.

Để làm vậy, hãy dùng method `unwrap()`, method này trả về instance driver bên dưới. Generic type parameter chỉ định type của instance driver mà bạn mong đợi.

```typescript
const mqttClient = this.client.unwrap<import('mqtt').MqttClient>();
```

Tương tự, bạn có thể truy cập instance driver bên dưới của server:

```typescript
const mqttClient = server.unwrap<import('mqtt').MqttClient>();
```
