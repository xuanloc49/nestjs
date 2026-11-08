### Sequelize

Package `@nestjs/sequelize` tích hợp ORM [Sequelize](https://sequelize.org/) với Nest. Nó cũng dùng package [sequelize-typescript](https://github.com/RobinBuschmann/sequelize-typescript), package này cung cấp decorator để định nghĩa model theo kiểu khai báo.

Để bắt đầu, trước tiên ta cài các dependency cần thiết. Trong chương này, ta sẽ minh họa với hệ quản trị database quan hệ [MySQL](https://www.mysql.com/) phổ biến, nhưng Sequelize hỗ trợ nhiều database quan hệ khác, như PostgreSQL, MySQL, Microsoft SQL Server, SQLite và MariaDB. Quy trình ta đi qua trong chương này giống nhau cho mọi database mà Sequelize hỗ trợ. Bạn chỉ cần cài client API library tương ứng cho database đã chọn.

```bash
$ npm install --save @nestjs/sequelize sequelize sequelize-typescript mysql2
$ npm install --save-dev @types/sequelize
```

Sau khi cài xong, ta có thể import `SequelizeModule` vào root module `AppModule`.

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { SequelizeModule } from '@nestjs/sequelize';

@Module({
  imports: [
    SequelizeModule.forRoot({
      dialect: 'mysql',
      host: 'localhost',
      port: 3306,
      username: 'root',
      password: 'root',
      database: 'test',
      models: [],
    }),
  ],
})
export class AppModule {}
```

Method `forRoot()` hỗ trợ mọi thuộc tính cấu hình mà constructor của Sequelize cung cấp ([đọc thêm](https://sequelize.org/docs/v6/getting-started/#connecting-to-a-database)). Ngoài ra, còn có vài thuộc tính cấu hình bổ sung được mô tả bên dưới.

<table>
  <tr>
    <td><code>retryAttempts</code></td>
    <td>Số lần thử kết nối tới database (mặc định: <code>10</code>)</td>
  </tr>
  <tr>
    <td><code>retryDelay</code></td>
    <td>Khoảng trễ giữa các lần thử kết nối lại (ms) (mặc định: <code>3000</code>)</td>
  </tr>
  <tr>
    <td><code>autoLoadModels</code></td>
    <td>Nếu là <code>true</code>, model sẽ được tự động load (mặc định: <code>false</code>)</td>
  </tr>
  <tr>
    <td><code>autoCloseConnection</code></td>
    <td>Nếu là <code>true</code>, kết nối sẽ được đóng khi ứng dụng tắt (mặc định: <code>true</code>)</td>
  </tr>
  <tr>
    <td><code>synchronize</code></td>
    <td>Nếu là <code>true</code>, các model được tự động load sẽ được đồng bộ (mặc định: <code>true</code>)</td>
  </tr>
</table>

Khi đã xong, object `Sequelize` sẽ có thể inject được trong toàn bộ project (không cần import module nào), ví dụ:

```typescript
@@filename(app.service)
import { Injectable } from '@nestjs/common';
import { Sequelize } from 'sequelize-typescript';

@Injectable()
export class AppService {
  constructor(private sequelize: Sequelize) {}
}
@@switch
import { Injectable } from '@nestjs/common';
import { Sequelize } from 'sequelize-typescript';

@Dependencies(Sequelize)
@Injectable()
export class AppService {
  constructor(sequelize) {
    this.sequelize = sequelize;
  }
}
```

#### Model <a id="models"></a>

Sequelize implement pattern Active Record. Với pattern này, bạn dùng trực tiếp các class model để tương tác với database. Để tiếp tục ví dụ, ta cần ít nhất một model. Hãy định nghĩa model `User`.

```typescript
@@filename(user.model)
import { Column, Model, Table } from 'sequelize-typescript';

@Table
export class User extends Model {
  @Column
  firstName: string;

  @Column
  lastName: string;

  @Column({ defaultValue: true })
  isActive: boolean;
}
```

> info **Gợi ý** Tìm hiểu thêm về các decorator có sẵn [tại đây](https://github.com/RobinBuschmann/sequelize-typescript#column).

File model `User` nằm trong thư mục `users`. Thư mục này chứa mọi file liên quan tới `UsersModule`. Bạn có thể tùy ý quyết định nơi đặt các file model, tuy nhiên chúng tôi khuyên tạo chúng gần **domain** của chúng, trong thư mục module tương ứng.

Để bắt đầu dùng model `User`, ta cần cho Sequelize biết về nó bằng cách thêm nó vào mảng `models` trong tùy chọn của method `forRoot()` của module:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { SequelizeModule } from '@nestjs/sequelize';
import { User } from './users/user.model.js';

@Module({
  imports: [
    SequelizeModule.forRoot({
      dialect: 'mysql',
      host: 'localhost',
      port: 3306,
      username: 'root',
      password: 'root',
      database: 'test',
      models: [User],
    }),
  ],
})
export class AppModule {}
```

Tiếp theo, hãy xem `UsersModule`:

```typescript
@@filename(users.module)
import { Module } from '@nestjs/common';
import { SequelizeModule } from '@nestjs/sequelize';
import { User } from './user.model.js';
import { UsersController } from './users.controller.js';
import { UsersService } from './users.service.js';

@Module({
  imports: [SequelizeModule.forFeature([User])],
  providers: [UsersService],
  controllers: [UsersController],
})
export class UsersModule {}
```

Module này dùng method `forFeature()` để định nghĩa những model nào được đăng ký trong scope hiện tại. Khi đã có nó, ta có thể inject `UserModel` vào `UsersService` bằng decorator `@InjectModel()`:

```typescript
@@filename(users.service)
import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/sequelize';
import { User } from './user.model.js';

@Injectable()
export class UsersService {
  constructor(
    @InjectModel(User)
    private userModel: typeof User,
  ) {}

  async findAll(): Promise<User[]> {
    return this.userModel.findAll();
  }

  findOne(id: string): Promise<User> {
    return this.userModel.findOne({
      where: {
        id,
      },
    });
  }

  async remove(id: string): Promise<void> {
    const user = await this.findOne(id);
    await user.destroy();
  }
}
@@switch
import { Injectable, Dependencies } from '@nestjs/common';
import { getModelToken } from '@nestjs/sequelize';
import { User } from './user.model.js';

@Injectable()
@Dependencies(getModelToken(User))
export class UsersService {
  constructor(usersRepository) {
    this.usersRepository = usersRepository;
  }

  async findAll() {
    return this.userModel.findAll();
  }

  findOne(id) {
    return this.userModel.findOne({
      where: {
        id,
      },
    });
  }

  async remove(id) {
    const user = await this.findOne(id);
    await user.destroy();
  }
}
```

> warning **Chú ý** Đừng quên import `UsersModule` vào root module `AppModule`.

Nếu muốn dùng model bên ngoài module import `SequelizeModule.forFeature`, bạn cần re-export các provider mà nó sinh ra.
Bạn có thể làm việc này bằng cách export toàn bộ module, như sau:

```typescript
@@filename(users.module)
import { Module } from '@nestjs/common';
import { SequelizeModule } from '@nestjs/sequelize';
import { User } from './user.entity.js';

@Module({
  imports: [SequelizeModule.forFeature([User])],
  exports: [SequelizeModule]
})
export class UsersModule {}
```

Giờ nếu ta import `UsersModule` vào `UserHttpModule`, ta có thể dùng `@InjectModel(User)` trong các provider của module sau.

```typescript
@@filename(users-http.module)
import { Module } from '@nestjs/common';
import { UsersModule } from './users.module.js';
import { UsersService } from './users.service.js';
import { UsersController } from './users.controller.js';

@Module({
  imports: [UsersModule],
  providers: [UsersService],
  controllers: [UsersController]
})
export class UserHttpModule {}
```

#### Relation <a id="relations"></a>

Relation là liên kết được thiết lập giữa hai hoặc nhiều bảng. Relation dựa trên các trường chung của mỗi bảng, thường liên quan tới khóa chính và khóa ngoại.

Có ba loại relation:

<table>
  <tr>
    <td><code>One-to-one</code></td>
    <td>Mỗi dòng trong bảng chính có một và chỉ một dòng liên kết trong bảng ngoại</td>
  </tr>
  <tr>
    <td><code>One-to-many / Many-to-one</code></td>
    <td>Mỗi dòng trong bảng chính có một hoặc nhiều dòng liên quan trong bảng ngoại</td>
  </tr>
  <tr>
    <td><code>Many-to-many</code></td>
    <td>Mỗi dòng trong bảng chính có nhiều dòng liên quan trong bảng ngoại, và mỗi bản ghi trong bảng ngoại có nhiều dòng liên quan trong bảng chính</td>
  </tr>
</table>

Để định nghĩa relation trong model, hãy dùng các **decorator** tương ứng. Ví dụ, để định nghĩa mỗi `User` có thể có nhiều ảnh, dùng decorator `@HasMany()`.

```typescript
@@filename(user.model)
import { Column, Model, Table, HasMany } from 'sequelize-typescript';
import { Photo } from '../photos/photo.model.js';

@Table
export class User extends Model {
  @Column
  firstName: string;

  @Column
  lastName: string;

  @Column({ defaultValue: true })
  isActive: boolean;

  @HasMany(() => Photo)
  photos: Photo[];
}
```

> info **Gợi ý** Để tìm hiểu thêm về association trong Sequelize, hãy đọc chương [này](https://github.com/RobinBuschmann/sequelize-typescript#model-association).

#### Tự động load model <a id="auto-load-models"></a>

Thêm model thủ công vào mảng `models` trong tùy chọn kết nối có thể khá nhàm chán. Ngoài ra, tham chiếu model từ root module sẽ phá vỡ ranh giới domain của ứng dụng và khiến chi tiết implementation bị lộ ra các phần khác. Để giải quyết vấn đề này, hãy tự động load model bằng cách đặt cả hai thuộc tính `autoLoadModels` và `synchronize` của configuration object (truyền vào method `forRoot()`) thành `true`, như bên dưới:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { SequelizeModule } from '@nestjs/sequelize';

@Module({
  imports: [
    SequelizeModule.forRoot({
      ...
      autoLoadModels: true,
      synchronize: true,
    }),
  ],
})
export class AppModule {}
```

Khi chỉ định tùy chọn đó, mọi model đăng ký qua method `forFeature()` sẽ tự động được thêm vào mảng `models` của configuration object.

> warning **Cảnh báo** Lưu ý rằng những model không được đăng ký qua method `forFeature()`, mà chỉ được tham chiếu từ model khác (qua association), sẽ không được đưa vào.

#### Transaction trong Sequelize <a id="sequelize-transactions"></a>

Một database transaction tượng trưng cho một đơn vị công việc được thực hiện trong hệ quản trị database trên một database, và được xử lý một cách nhất quán, tin cậy, độc lập với các transaction khác. Nhìn chung, một transaction đại diện cho mọi thay đổi trong database ([tìm hiểu thêm](https://en.wikipedia.org/wiki/Database_transaction)).

Có nhiều chiến lược khác nhau để xử lý [transaction trong Sequelize](https://sequelize.org/docs/v6/other-topics/transactions/). Dưới đây là một bản implement mẫu cho managed transaction (auto-callback).

Đầu tiên, ta cần inject object `Sequelize` vào class theo cách thông thường:

```typescript
@Injectable()
export class UsersService {
  constructor(private sequelize: Sequelize) {}
}
```

> info **Gợi ý** Class `Sequelize` được import từ package `sequelize-typescript`.

Giờ ta có thể dùng object này để tạo transaction.

```typescript
async createMany() {
  try {
    await this.sequelize.transaction(async t => {
      const transactionHost = { transaction: t };

      await this.userModel.create(
          { firstName: 'Abraham', lastName: 'Lincoln' },
          transactionHost,
      );
      await this.userModel.create(
          { firstName: 'John', lastName: 'Boothe' },
          transactionHost,
      );
    });
  } catch (err) {
    // Transaction has been rolled back
    // err is whatever rejected the promise chain returned to the transaction callback
  }
}
```

> info **Gợi ý** Lưu ý rằng instance `Sequelize` chỉ được dùng để bắt đầu transaction. Tuy nhiên, test class này sẽ đòi hỏi mock toàn bộ object `Sequelize` (vốn có khá nhiều method). Vì vậy, chúng tôi khuyên dùng một class factory helper (ví dụ `TransactionRunner`) và định nghĩa một interface với một tập method giới hạn cần thiết để duy trì transaction. Kỹ thuật này giúp việc mock các method đó khá đơn giản.

#### Migration <a id="migrations"></a>

[Migration](https://sequelize.org/docs/v6/other-topics/migrations/) cung cấp cách cập nhật dần schema database để giữ nó đồng bộ với data model của ứng dụng, trong khi vẫn giữ nguyên dữ liệu hiện có trong database. Để sinh, chạy và revert migration, Sequelize cung cấp một [CLI](https://sequelize.org/docs/v6/other-topics/migrations/#installing-the-cli) chuyên dụng.

Các class migration tách biệt khỏi mã nguồn ứng dụng Nest. Vòng đời của chúng do Sequelize CLI quản lý. Vì vậy, bạn không thể tận dụng dependency injection và các tính năng đặc thù khác của Nest với migration. Để tìm hiểu thêm về migration, hãy làm theo hướng dẫn trong [tài liệu Sequelize](https://sequelize.org/docs/v6/other-topics/migrations/#installing-the-cli).

<app-banner-courses></app-banner-courses>

#### Nhiều database <a id="multiple-databases"></a>

Một số project cần nhiều kết nối database. Module này cũng làm được điều đó. Để làm việc với nhiều kết nối, trước tiên hãy tạo các kết nối. Trong trường hợp này, việc đặt tên cho kết nối trở nên **bắt buộc**.

Giả sử bạn có một entity `Album` được lưu trong database riêng của nó.

```typescript
const defaultOptions = {
  dialect: 'postgres',
  port: 5432,
  username: 'user',
  password: 'password',
  database: 'db',
  synchronize: true,
};

@Module({
  imports: [
    SequelizeModule.forRoot({
      ...defaultOptions,
      host: 'user_db_host',
      models: [User],
    }),
    SequelizeModule.forRoot({
      ...defaultOptions,
      name: 'albumsConnection',
      host: 'album_db_host',
      models: [Album],
    }),
  ],
})
export class AppModule {}
```

> warning **Chú ý** Nếu bạn không đặt `name` cho một kết nối, tên của nó sẽ là `default`. Lưu ý rằng bạn không nên có nhiều kết nối không có tên, hoặc trùng tên, nếu không chúng sẽ bị ghi đè.

Lúc này, bạn đã có các model `User` và `Album` được đăng ký với kết nối riêng của chúng. Với cách thiết lập này, bạn phải cho method `SequelizeModule.forFeature()` và decorator `@InjectModel()` biết cần dùng kết nối nào. Nếu bạn không truyền tên kết nối nào, kết nối `default` sẽ được dùng.

```typescript
@Module({
  imports: [
    SequelizeModule.forFeature([User]),
    SequelizeModule.forFeature([Album], 'albumsConnection'),
  ],
})
export class AppModule {}
```

Bạn cũng có thể inject instance `Sequelize` của một kết nối cụ thể:

```typescript
@Injectable()
export class AlbumsService {
  constructor(
    @InjectConnection('albumsConnection')
    private sequelize: Sequelize,
  ) {}
}
```

Bạn cũng có thể inject bất kỳ instance `Sequelize` nào vào các provider:

```typescript
@Module({
  providers: [
    {
      provide: AlbumsService,
      useFactory: (albumsSequelize: Sequelize) => {
        return new AlbumsService(albumsSequelize);
      },
      inject: [getConnectionToken('albumsConnection')],
    },
  ],
})
export class AlbumsModule {}
```

#### Test <a id="testing"></a>

Khi unit test một ứng dụng, thông thường ta muốn tránh kết nối database, giữ cho các test suite độc lập và quá trình chạy nhanh nhất có thể. Nhưng các class của ta có thể phụ thuộc vào các model lấy từ instance kết nối. Xử lý thế nào? Giải pháp là tạo các mock model. Để làm vậy, ta thiết lập [custom provider](/fundamentals/custom-providers). Mỗi model đã đăng ký được tự động đại diện bởi một token `<ModelName>Model`, trong đó `ModelName` là tên class model của bạn.

Package `@nestjs/sequelize` cung cấp hàm `getModelToken()`, hàm này trả về một token có sẵn dựa trên model đã cho.

```typescript
@Module({
  providers: [
    UsersService,
    {
      provide: getModelToken(User),
      useValue: mockModel,
    },
  ],
})
export class UsersModule {}
```

Giờ thì `mockModel` thay thế sẽ được dùng làm `UserModel`. Mỗi khi có class yêu cầu `UserModel` bằng decorator `@InjectModel()`, Nest sẽ dùng object `mockModel` đã đăng ký.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Có thể bạn muốn truyền tùy chọn cho `SequelizeModule` theo kiểu bất đồng bộ thay vì tĩnh. Khi đó, hãy dùng method `forRootAsync()`, method này cung cấp vài cách để xử lý cấu hình bất đồng bộ.

Một cách là dùng hàm factory:

```typescript
SequelizeModule.forRootAsync({
  useFactory: () => ({
    dialect: 'mysql',
    host: 'localhost',
    port: 3306,
    username: 'root',
    password: 'root',
    database: 'test',
    models: [],
  }),
});
```

Factory của ta hoạt động như mọi [provider bất đồng bộ](https://docs.nestjs.com/fundamentals/async-providers) khác (ví dụ nó có thể là `async` và có thể inject dependency qua `inject`).

```typescript
SequelizeModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: (configService: ConfigService) => ({
    dialect: 'mysql',
    host: configService.get('HOST'),
    port: +configService.get('PORT'),
    username: configService.get('USERNAME'),
    password: configService.get('PASSWORD'),
    database: configService.get('DATABASE'),
    models: [],
  }),
  inject: [ConfigService],
});
```

Cách khác là dùng cú pháp `useClass`:

```typescript
SequelizeModule.forRootAsync({
  useClass: SequelizeConfigService,
});
```

Cách khai báo trên sẽ khởi tạo `SequelizeConfigService` bên trong `SequelizeModule` và dùng nó để cung cấp options object bằng cách gọi `createSequelizeOptions()`. Lưu ý rằng điều này có nghĩa là `SequelizeConfigService` phải implement interface `SequelizeOptionsFactory`, như bên dưới:

```typescript
@Injectable()
class SequelizeConfigService implements SequelizeOptionsFactory {
  createSequelizeOptions(): SequelizeModuleOptions {
    return {
      dialect: 'mysql',
      host: 'localhost',
      port: 3306,
      username: 'root',
      password: 'root',
      database: 'test',
      models: [],
    };
  }
}
```

Để tránh việc tạo `SequelizeConfigService` bên trong `SequelizeModule` và dùng một provider được import từ module khác, bạn có thể dùng cú pháp `useExisting`.

```typescript
SequelizeModule.forRootAsync({
  imports: [ConfigModule],
  useExisting: ConfigService,
});
```

Cách khai báo này hoạt động giống `useClass`, với một khác biệt quan trọng - `SequelizeModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã có thay vì khởi tạo cái mới.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn [tại đây](https://github.com/nestjs/nest/tree/master/sample/07-sequelize).
