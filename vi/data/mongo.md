### Mongo

Nest hỗ trợ hai cách để tích hợp với database [MongoDB](https://www.mongodb.com/). Bạn có thể dùng module [TypeORM](https://github.com/typeorm/typeorm) mô tả trong [chương TypeORM](/data/typeorm), vốn có connector cho MongoDB, hoặc dùng [Mongoose](https://mongoosejs.com), công cụ mô hình hóa object cho MongoDB phổ biến nhất. Chương này mô tả cách thứ hai, dùng package chuyên dụng `@nestjs/mongoose`.

Bắt đầu bằng việc cài các dependency cần thiết:

```bash
$ npm i @nestjs/mongoose mongoose
```

Sau khi cài xong, import `MongooseModule` vào root module `AppModule`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';

@Module({
  imports: [MongooseModule.forRoot('mongodb://localhost/nest')],
})
export class AppModule {}
```

Method `forRoot()` nhận cùng configuration object như `mongoose.connect()` của package Mongoose, như mô tả trong [hướng dẫn kết nối của Mongoose](https://mongoosejs.com/docs/connections.html).

#### Inject model <a id="model-injection"></a>

Với Mongoose, mọi thứ đều bắt nguồn từ một [Schema](https://mongoosejs.com/docs/guide.html). Mỗi schema ánh xạ tới một collection MongoDB và định nghĩa cấu trúc của các document trong collection đó. Schema được dùng để định nghĩa [Model](https://mongoosejs.com/docs/models.html). Model chịu trách nhiệm tạo và đọc document từ database MongoDB bên dưới.

Bạn có thể tạo schema bằng decorator của NestJS, hoặc tự tạo bằng chính Mongoose. Dùng decorator để tạo schema giúp giảm đáng kể boilerplate và cải thiện khả năng đọc code nói chung.

Hãy định nghĩa `CatSchema`:

```typescript
@@filename(schemas/cat.schema)
import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type CatDocument = HydratedDocument<Cat>;

@Schema()
export class Cat {
  @Prop()
  name: string;

  @Prop()
  age: number;

  @Prop()
  breed: string;
}

export const CatSchema = SchemaFactory.createForClass(Cat);
```

> info **Gợi ý** Bạn cũng có thể sinh ra một định nghĩa schema thô bằng class `DefinitionsFactory` (từ package `@nestjs/mongoose`). Cách này cho phép bạn tự sửa định nghĩa schema được sinh ra từ metadata đã cung cấp, hữu ích cho những trường hợp đặc biệt khó biểu diễn hết bằng decorator.

Decorator `@Schema()` đánh dấu một class là định nghĩa schema. Nó ánh xạ class `Cat` tới một collection MongoDB cùng tên, nhưng thêm chữ "s" ở cuối, nên tên collection cuối cùng là `cats`. Decorator này nhận một tham số tùy chọn duy nhất là một object tùy chọn schema. Hãy hình dung nó như object mà bạn thường truyền làm tham số thứ hai cho constructor của class `mongoose.Schema` (ví dụ `new mongoose.Schema(_, options)`). Để tìm hiểu thêm về các tùy chọn schema có sẵn, xem tài liệu [Mongoose schema options](https://mongoosejs.com/docs/guide.html#options).

Decorator `@Prop()` định nghĩa một thuộc tính trong document. Ví dụ, định nghĩa schema ở trên định nghĩa ba thuộc tính: `name`, `age` và `breed`. [Schema type](https://mongoosejs.com/docs/schematypes.html) của các thuộc tính này được tự động suy ra nhờ khả năng metadata (và reflection) của TypeScript. Tuy nhiên, trong những tình huống phức tạp hơn mà type không thể được suy ra ngầm (ví dụ mảng hoặc cấu trúc object lồng nhau), bạn phải chỉ định type một cách tường minh, như sau:

```typescript
@Prop([String])
tags: string[];
```

Ngoài ra, decorator `@Prop()` nhận một tham số options object (đọc thêm về [các tùy chọn schema type có sẵn](https://mongoosejs.com/docs/schematypes.html#schematype-options)). Với nó, bạn có thể chỉ định một thuộc tính là bắt buộc, đặt giá trị mặc định, hoặc đánh dấu nó là không thể thay đổi (immutable). Ví dụ:

```typescript
@Prop({ required: true })
name: string;
```

Để chỉ định relation tới một model khác (để populate sau này), bạn cũng dùng decorator `@Prop()`. Ví dụ, nếu `Cat` có một `Owner` được lưu trong một collection khác tên là `owners`, thuộc tính cần có các tùy chọn `type` và `ref`:

```typescript
import mongoose from 'mongoose';
import { Owner } from '../owners/schemas/owner.schema.js';

// inside the class definition
@Prop({ type: mongoose.Schema.Types.ObjectId, ref: 'Owner' })
owner: Owner;
```

Nếu có nhiều owner, cấu hình thuộc tính trông như sau:

```typescript
@Prop({ type: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Owner' }] })
owners: Owner[];
```

Nếu bạn không định lúc nào cũng populate tham chiếu tới collection khác, hãy cân nhắc dùng `mongoose.Types.ObjectId` làm type:

```typescript
@Prop({ type: mongoose.Schema.Types.ObjectId, ref: 'Owner' })
// This ensures the field is not confused with a populated reference
owner: mongoose.Types.ObjectId;
```

Sau đó, khi cần populate có chọn lọc, hãy dùng một hàm repository chỉ định đúng type:

```typescript
import { Owner } from './schemas/owner.schema.js';

// e.g. inside a service or repository
async findAllPopulated() {
  return this.catModel.find().populate<{ owner: Owner }>("owner");
}
```

> info **Gợi ý** Nếu không có document ngoại nào để populate, type có thể là `Owner | null`, tùy theo [cấu hình Mongoose](https://mongoosejs.com/docs/populate.html#doc-not-found) của bạn. Hoặc nó có thể throw lỗi, khi đó type là `Owner`.

Cuối cùng, bạn cũng có thể truyền một định nghĩa schema **thô** vào decorator. Điều này hữu ích khi, chẳng hạn, một thuộc tính biểu diễn một object lồng nhau không được định nghĩa dưới dạng class. Để làm vậy, dùng hàm `raw()` từ package `@nestjs/mongoose`, như sau:

```typescript
@Prop(raw({
  firstName: { type: String },
  lastName: { type: String }
}))
details: Record<string, any>;
```

Ngoài ra, nếu bạn thích **không dùng decorator**, bạn có thể tự định nghĩa schema. Ví dụ:

```typescript
export const CatSchema = new mongoose.Schema({
  name: String,
  age: Number,
  breed: String,
});
```

File `cat.schema` nằm trong thư mục `schemas` bên trong thư mục `cats`, nơi `CatsModule` cũng được định nghĩa. Dù bạn có thể đặt file schema ở bất cứ đâu, chúng tôi khuyên đặt chúng gần các object **domain** liên quan, trong thư mục module tương ứng.

Hãy xem `CatsModule`:

```typescript
@@filename(cats.module)
import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { CatsController } from './cats.controller.js';
import { CatsService } from './cats.service.js';
import { Cat, CatSchema } from './schemas/cat.schema.js';

@Module({
  imports: [MongooseModule.forFeature([{ name: Cat.name, schema: CatSchema }])],
  controllers: [CatsController],
  providers: [CatsService],
})
export class CatsModule {}
```

`MongooseModule` cung cấp method `forFeature()` để cấu hình module, bao gồm việc định nghĩa những model nào được đăng ký trong scope hiện tại. Để dùng các model ở một module khác, hãy thêm `MongooseModule` vào mảng `exports` của `CatsModule` và import `CatsModule` ở module đó.

Khi đã đăng ký schema, bạn có thể inject model `Cat` vào `CatsService` bằng decorator `@InjectModel()`:

```typescript
@@filename(cats.service)
import { Model } from 'mongoose';
import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Cat } from './schemas/cat.schema.js';
import { CreateCatDto } from './dto/create-cat.dto.js';

@Injectable()
export class CatsService {
  constructor(@InjectModel(Cat.name) private catModel: Model<Cat>) {}

  async create(createCatDto: CreateCatDto): Promise<Cat> {
    const createdCat = new this.catModel(createCatDto);
    return createdCat.save();
  }

  async findAll(): Promise<Cat[]> {
    return this.catModel.find().exec();
  }
}
@@switch
import { Model } from 'mongoose';
import { Injectable, Dependencies } from '@nestjs/common';
import { getModelToken } from '@nestjs/mongoose';
import { Cat } from './schemas/cat.schema.js';

@Injectable()
@Dependencies(getModelToken(Cat.name))
export class CatsService {
  constructor(catModel) {
    this.catModel = catModel;
  }

  async create(createCatDto) {
    const createdCat = new this.catModel(createCatDto);
    return createdCat.save();
  }

  async findAll() {
    return this.catModel.find().exec();
  }
}
```

#### Connection

Đôi khi, bạn có thể cần truy cập object [Mongoose Connection](https://mongoosejs.com/docs/api.html#Connection) gốc, ví dụ để gọi các API gốc trên nó. Inject Mongoose connection bằng decorator `@InjectConnection()` như sau:

```typescript
import { Injectable } from '@nestjs/common';
import { InjectConnection } from '@nestjs/mongoose';
import { Connection } from 'mongoose';

@Injectable()
export class CatsService {
  constructor(@InjectConnection() private connection: Connection) {}
}
```

#### Session <a id="sessions"></a>

Để bắt đầu một session với Mongoose, hãy inject kết nối database bằng `@InjectConnection()` thay vì gọi trực tiếp `mongoose.startSession()`. Cách này tích hợp với hệ thống dependency injection của Nest và đảm bảo session được bắt đầu trên kết nối mà Nest quản lý.

Đây là ví dụ cách bắt đầu một session:

```typescript
import { Injectable } from '@nestjs/common';
import { InjectConnection } from '@nestjs/mongoose';
import { Connection } from 'mongoose';

@Injectable()
export class CatsService {
  constructor(@InjectConnection() private readonly connection: Connection) {}

  async startTransaction() {
    const session = await this.connection.startSession();
    session.startTransaction();
    // Your transaction logic here
  }
}
```

Trong ví dụ này, `@InjectConnection()` inject Mongoose connection vào service. Sau đó bạn có thể gọi `connection.startSession()` để bắt đầu một session mới và dùng nó để quản lý database transaction, đảm bảo các thao tác nguyên tử qua nhiều query. Sau khi bắt đầu transaction, hãy nhớ commit hoặc abort nó tùy theo logic của bạn, và kết thúc session khi xong.

#### Nhiều database <a id="multiple-databases"></a>

Một số project cần nhiều kết nối database, và module này cũng hỗ trợ điều đó. Để làm việc với nhiều kết nối, trước tiên hãy tạo các kết nối. Trong trường hợp này, việc đặt tên cho kết nối là **bắt buộc**.

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';

@Module({
  imports: [
    MongooseModule.forRoot('mongodb://localhost/test', {
      connectionName: 'cats',
    }),
    MongooseModule.forRoot('mongodb://localhost/users', {
      connectionName: 'users',
    }),
  ],
})
export class AppModule {}
```

> warning **Chú ý** Đừng tạo nhiều kết nối không có tên hoặc trùng tên, nếu không chúng sẽ ghi đè lẫn nhau.

Với cách thiết lập này, bạn phải cho method `MongooseModule.forFeature()` biết cần dùng kết nối nào:

```typescript
@Module({
  imports: [
    MongooseModule.forFeature([{ name: Cat.name, schema: CatSchema }], 'cats'),
  ],
})
export class CatsModule {}
```

Bạn cũng có thể inject object `Connection` của một kết nối cụ thể:

```typescript
import { Injectable } from '@nestjs/common';
import { InjectConnection } from '@nestjs/mongoose';
import { Connection } from 'mongoose';

@Injectable()
export class CatsService {
  constructor(@InjectConnection('cats') private connection: Connection) {}
}
```

Để inject một `Connection` cụ thể vào một custom provider (ví dụ một factory provider), hãy dùng hàm `getConnectionToken()`, truyền tên của kết nối làm tham số:

```typescript
{
  provide: CatsService,
  useFactory: (catsConnection: Connection) => {
    return new CatsService(catsConnection);
  },
  inject: [getConnectionToken('cats')],
}
```

Để inject một model từ một kết nối có tên, hãy truyền tên kết nối làm tham số thứ hai cho decorator `@InjectModel()`:

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(@InjectModel(Cat.name, 'cats') private catModel: Model<Cat>) {}
}
@@switch
@Injectable()
@Dependencies(getModelToken(Cat.name, 'cats'))
export class CatsService {
  constructor(catModel) {
    this.catModel = catModel;
  }
}
```

#### Hook (middleware) <a id="hooks-middleware"></a>

Middleware (còn gọi là pre hook và post hook) là các hàm được trao quyền điều khiển trong quá trình thực thi các hàm bất đồng bộ. Middleware được chỉ định ở cấp schema và hữu ích để viết plugin (xem [tài liệu middleware của Mongoose](https://mongoosejs.com/docs/middleware.html)). Gọi `pre()` hoặc `post()` sau khi đã compile model sẽ không có tác dụng trong Mongoose. Để đăng ký hook **trước** khi đăng ký model, hãy dùng method `forFeatureAsync()` của `MongooseModule` cùng với một factory provider (tức là `useFactory`). Với kỹ thuật này, bạn có thể truy cập object schema, rồi dùng method `pre()` hoặc `post()` của nó để đăng ký hook trên schema đó. Ví dụ:

```typescript
@Module({
  imports: [
    MongooseModule.forFeatureAsync([
      {
        name: Cat.name,
        useFactory: () => {
          const schema = CatSchema;
          schema.pre('save', function () {
            console.log('Hello from pre save');
          });
          return schema;
        },
      },
    ]),
  ],
})
export class AppModule {}
```

Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, hàm factory có thể là `async` và có thể inject dependency qua `inject`.

```typescript
@Module({
  imports: [
    MongooseModule.forFeatureAsync([
      {
        name: Cat.name,
        imports: [ConfigModule],
        useFactory: (configService: ConfigService) => {
          const schema = CatSchema;
          schema.pre('save', function() {
            console.log(
              `${configService.get('APP_NAME')}: Hello from pre save`,
            );
          });
          return schema;
        },
        inject: [ConfigService],
      },
    ]),
  ],
})
export class AppModule {}
```

#### Plugin <a id="plugins"></a>

Để đăng ký một [plugin](https://mongoosejs.com/docs/plugins.html) cho một schema cụ thể, dùng method `forFeatureAsync()`:

```typescript
import autopopulate from 'mongoose-autopopulate';

@Module({
  imports: [
    MongooseModule.forFeatureAsync([
      {
        name: Cat.name,
        useFactory: () => {
          const schema = CatSchema;
          schema.plugin(autopopulate);
          return schema;
        },
      },
    ]),
  ],
})
export class AppModule {}
```

Để đăng ký một plugin cho mọi schema cùng lúc, hãy gọi method `.plugin()` của object `Connection`. Bạn phải truy cập connection trước khi model được tạo; để làm vậy, dùng tùy chọn `connectionFactory`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import autopopulate from 'mongoose-autopopulate';

@Module({
  imports: [
    MongooseModule.forRoot('mongodb://localhost/test', {
      connectionFactory: (connection) => {
        connection.plugin(autopopulate);
        return connection;
      }
    }),
  ],
})
export class AppModule {}
```

#### Discriminator <a id="discriminators"></a>

[Discriminator](https://mongoosejs.com/docs/discriminators.html) là một cơ chế kế thừa schema. Chúng cho phép bạn có nhiều model với các schema chồng lấn nhau trên cùng một collection MongoDB bên dưới.

Giả sử bạn muốn theo dõi các loại event khác nhau trong một collection duy nhất. Mọi event đều có timestamp.

```typescript
@@filename(event.schema)
@Schema({ discriminatorKey: 'kind' })
export class Event {
  @Prop({
    type: String,
    required: true,
    enum: [ClickedLinkEvent.name, SignUpEvent.name],
  })
  kind: string;

  @Prop({ type: Date, required: true })
  time: Date;
}

export const EventSchema = SchemaFactory.createForClass(Event);
```

> info **Gợi ý** Mongoose phân biệt các discriminator model qua "discriminator key", mặc định là `__t`. Mongoose thêm một path kiểu String tên là `__t` vào schema của bạn và dùng nó để theo dõi một document là instance của discriminator nào.
> Bạn cũng có thể dùng tùy chọn `discriminatorKey` để định nghĩa path dùng để phân biệt.

Các instance `SignUpEvent` và `ClickedLinkEvent` sẽ được lưu trong cùng collection với các event thông thường.

Giờ hãy định nghĩa class `ClickedLinkEvent`, như sau:

```typescript
@@filename(click-link-event.schema)
@Schema()
export class ClickedLinkEvent {
  kind: string;
  time: Date;

  @Prop({ type: String, required: true })
  url: string;
}

export const ClickedLinkEventSchema = SchemaFactory.createForClass(ClickedLinkEvent);
```

Và class `SignUpEvent`:

```typescript
@@filename(sign-up-event.schema)
@Schema()
export class SignUpEvent {
  kind: string;
  time: Date;

  @Prop({ type: String, required: true })
  user: string;
}

export const SignUpEventSchema = SchemaFactory.createForClass(SignUpEvent);
```

Khi đã có những thứ trên, hãy dùng tùy chọn `discriminators` để đăng ký discriminator cho một schema cụ thể. Nó hoạt động với cả `MongooseModule.forFeature()` lẫn `MongooseModule.forFeatureAsync()`:

```typescript
@@filename(event.module)
import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';

@Module({
  imports: [
    MongooseModule.forFeature([
      {
        name: Event.name,
        schema: EventSchema,
        discriminators: [
          { name: ClickedLinkEvent.name, schema: ClickedLinkEventSchema },
          { name: SignUpEvent.name, schema: SignUpEventSchema },
        ],
      },
    ]),
  ]
})
export class EventsModule {}
```

#### Test <a id="testing"></a>

Khi unit test một ứng dụng, thông thường bạn muốn tránh mọi kết nối database, giúp các test suite dễ thiết lập và chạy nhanh hơn. Tuy nhiên, các class của bạn có thể phụ thuộc vào các model lấy từ instance kết nối. Để resolve các class này, hãy tạo các mock model.

Để việc này dễ hơn, package `@nestjs/mongoose` cung cấp hàm `getModelToken()` trả về một [injection token](/fundamentals/custom-providers#di-fundamentals) có sẵn dựa trên tên model. Với token này, bạn có thể cung cấp một bản implement mock bằng bất kỳ kỹ thuật [custom provider](/fundamentals/custom-providers) chuẩn nào, bao gồm `useClass`, `useValue` và `useFactory`. Ví dụ:

```typescript
@Module({
  providers: [
    CatsService,
    {
      provide: getModelToken(Cat.name),
      useValue: catModel,
    },
  ],
})
export class CatsModule {}
```

Trong ví dụ này, một `catModel` hard-code (một instance object) sẽ được cung cấp mỗi khi có nơi inject `Model<Cat>` bằng decorator `@InjectModel()`.

<app-banner-courses></app-banner-courses>

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Khi cần truyền tùy chọn module theo kiểu bất đồng bộ thay vì tĩnh, hãy dùng method `forRootAsync()`. Giống như hầu hết dynamic module, Nest cung cấp vài kỹ thuật cho cấu hình bất đồng bộ.

Một kỹ thuật là dùng hàm factory:

```typescript
MongooseModule.forRootAsync({
  useFactory: () => ({
    uri: 'mongodb://localhost/nest',
  }),
});
```

Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, hàm factory có thể là `async` và có thể inject dependency qua `inject`.

```typescript
MongooseModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: async (configService: ConfigService) => ({
    uri: configService.get<string>('MONGODB_URI'),
  }),
  inject: [ConfigService],
});
```

Cách khác là cấu hình `MongooseModule` bằng một class thay vì factory, như bên dưới:

```typescript
MongooseModule.forRootAsync({
  useClass: MongooseConfigService,
});
```

Cách khai báo trên khởi tạo `MongooseConfigService` bên trong `MongooseModule`, dùng nó để tạo options object cần thiết. Trong ví dụ này, `MongooseConfigService` phải implement interface `MongooseOptionsFactory`, như bên dưới. `MongooseModule` gọi method `createMongooseOptions()` trên object đã khởi tạo của class được cung cấp.

```typescript
@Injectable()
export class MongooseConfigService implements MongooseOptionsFactory {
  createMongooseOptions(): MongooseModuleOptions {
    return {
      uri: 'mongodb://localhost/nest',
    };
  }
}
```

Để dùng lại một options provider đã có thay vì tạo một bản sao riêng bên trong `MongooseModule`, hãy dùng cú pháp `useExisting`. Provider đó phải implement interface `MongooseOptionsFactory`:

```typescript
MongooseModule.forRootAsync({
  imports: [ConfigModule],
  useExisting: ConfigService,
});
```

#### Event của kết nối <a id="connection-events"></a>

Bạn có thể lắng nghe các [event kết nối](https://mongoosejs.com/docs/connections.html#connection-events) của Mongoose bằng tùy chọn cấu hình `onConnectionCreate`. Nest gọi hàm này với mỗi kết nối ngay khi kết nối được tạo, trước khi nó mở, nên bạn có thể đăng ký listener cho các event `connected`, `open`, `disconnected`, `reconnected` và `disconnecting`, như minh họa bên dưới:

```typescript
MongooseModule.forRoot('mongodb://localhost/test', {
  onConnectionCreate: (connection: Connection) => {
    connection.on('connected', () => console.log('connected'));
    connection.on('open', () => console.log('open'));
    connection.on('disconnected', () => console.log('disconnected'));
    connection.on('reconnected', () => console.log('reconnected'));
    connection.on('disconnecting', () => console.log('disconnecting'));

    return connection;
  },
}),
```

Đoạn code này thiết lập kết nối tới một database MongoDB tại `mongodb://localhost/test`. Tùy chọn `onConnectionCreate` thiết lập các event listener để theo dõi trạng thái kết nối:

- `connected`: Được kích hoạt khi kết nối được thiết lập thành công.
- `open`: Kích hoạt khi kết nối đã mở hoàn toàn và sẵn sàng cho các thao tác.
- `disconnected`: Được gọi khi mất kết nối.
- `reconnected`: Được gọi khi kết nối được thiết lập lại sau khi bị ngắt.
- `disconnecting`: Xảy ra khi kết nối đang trong quá trình đóng.

Bạn cũng có thể dùng thuộc tính `onConnectionCreate` trong các cấu hình bất đồng bộ tạo bằng `MongooseModule.forRootAsync()`:

```typescript
MongooseModule.forRootAsync({
  useFactory: () => ({
    uri: 'mongodb://localhost/test',
    onConnectionCreate: (connection: Connection) => {
      // Register event listeners here
      return connection;
    },
  }),
}),
```

#### Subdocument <a id="subdocuments"></a>

Để lồng subdocument bên trong một document cha, hãy định nghĩa các schema như sau:

```typescript
@@filename(name.schema)
@Schema()
export class Name {
  @Prop()
  firstName: string;

  @Prop()
  lastName: string;
}

export const NameSchema = SchemaFactory.createForClass(Name);
```

Rồi tham chiếu tới subdocument trong schema cha:

```typescript
@@filename(person.schema)
@Schema()
export class Person {
  @Prop(NameSchema)
  name: Name;
}

export const PersonSchema = SchemaFactory.createForClass(Person);

export type PersonDocumentOverride = {
  name: Types.Subdocument<Types.ObjectId> & Name;
};

export type PersonDocument = HydratedDocument<Person, PersonDocumentOverride>;
```

Để chứa nhiều subdocument, hãy dùng một mảng subdocument. Nhớ ghi đè type của thuộc tính cho phù hợp:

```typescript
@@filename(person.schema)
@Schema()
export class Person {
  @Prop([NameSchema])
  name: Name[];
}

export const PersonSchema = SchemaFactory.createForClass(Person);

export type PersonDocumentOverride = {
  name: Types.DocumentArray<Name>;
};

export type PersonDocument = HydratedDocument<Person, PersonDocumentOverride>;
```

#### Virtual <a id="virtuals"></a>

Trong Mongoose, một **virtual** là một thuộc tính tồn tại trên document nhưng không được lưu vào MongoDB. Thay vào đó, nó được tính động mỗi khi được truy cập. Virtual thường được dùng cho các giá trị dẫn xuất hoặc tính toán, như kết hợp các trường (ví dụ tạo thuộc tính `fullName` bằng cách nối `firstName` và `lastName`), hoặc để tạo các thuộc tính dựa trên dữ liệu đã có trong document.

```ts
class Person {
  @Prop()
  firstName: string;

  @Prop()
  lastName: string;

  @Virtual({
    get: function (this: Person) {
      return `${this.firstName} ${this.lastName}`;
    },
  })
  fullName: string;
}
```

> info **Gợi ý** Decorator `@Virtual()` được import từ package `@nestjs/mongoose`.

Trong ví dụ này, virtual `fullName` được suy ra từ `firstName` và `lastName`. Dù nó hoạt động như một thuộc tính bình thường khi được truy cập, nó không bao giờ được lưu vào document MongoDB.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn trong [repository nestjs/nest](https://github.com/nestjs/nest/tree/master/sample/06-mongoose).
