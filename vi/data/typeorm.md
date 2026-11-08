### TypeORM

Package `@nestjs/typeorm` tích hợp [TypeORM](https://github.com/typeorm/typeorm) với Nest. TypeORM là một trong những Object Relational Mapper (ORM) trưởng thành nhất cho TypeScript. Vì được viết bằng TypeScript, nó tích hợp rất tốt với Nest.

Để bắt đầu, hãy cài các dependency cần thiết. Chương này dùng [MySQL](https://www.mysql.com/), nhưng TypeORM hỗ trợ nhiều database quan hệ khác, như PostgreSQL, Oracle, Microsoft SQL Server và SQLite, cũng như các database NoSQL như MongoDB. Các bước trong chương này giống nhau cho mọi database mà TypeORM hỗ trợ; bạn chỉ cần cài client library cho database của mình.

```bash
$ npm install --save @nestjs/typeorm typeorm mysql2
```

Sau khi cài xong, import `TypeOrmModule` vào root module `AppModule`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'mysql',
      host: 'localhost',
      port: 3306,
      username: 'root',
      password: 'root',
      database: 'test',
      entities: [],
      synchronize: true,
    }),
  ],
})
export class AppModule {}
```

> warning **Cảnh báo** Đừng dùng `synchronize: true` trên production; nếu không, bạn có thể mất dữ liệu production.

Method `forRoot()` nhận mọi thuộc tính cấu hình mà [constructor `DataSource`](https://typeorm.io/docs/data-source/data-source-options#common-data-source-options) của TypeORM hỗ trợ. Nó cũng nhận thêm các thuộc tính sau:

<table>
  <tr>
    <td><code>retryAttempts</code></td>
    <td>Số lần thử kết nối tới database (mặc định: <code>10</code>)</td>
  </tr>
  <tr>
    <td><code>retryDelay</code></td>
    <td>Khoảng trễ giữa các lần thử kết nối lại, tính bằng mili giây (mặc định: <code>3000</code>)</td>
  </tr>
  <tr>
    <td><code>toRetry</code></td>
    <td>Hàm nhận lỗi kết nối và trả về việc có retry hay không. Mặc định, mọi lỗi đều được retry</td>
  </tr>
  <tr>
    <td><code>verboseRetryLog</code></td>
    <td>Nếu là <code>true</code>, thông báo lỗi sẽ được đưa vào dòng log của mỗi lần thử kết nối lại (mặc định: <code>false</code>)</td>
  </tr>
  <tr>
    <td><code>autoLoadEntities</code></td>
    <td>Nếu là <code>true</code>, entity sẽ được tự động load (mặc định: <code>false</code>). Xem <a href="/data/typeorm#auto-load-entities">Tự động load entity</a></td>
  </tr>
  <tr>
    <td><code>manualInitialization</code></td>
    <td>Nếu là <code>true</code>, data source không được khởi tạo trong lúc khởi tạo module, nên không có kết nối nào được thiết lập và không migration nào chạy. Bạn phải tự gọi <code>DataSource.initialize()</code> và tự xử lý retry nếu cần (mặc định: <code>false</code>)</td>
  </tr>
</table>

> info **Gợi ý** Tìm hiểu thêm về các tùy chọn có sẵn trong tài liệu [TypeORM data source options](https://typeorm.io/docs/data-source/data-source-options).

Khi đã xong, bạn có thể inject các object `DataSource` và `EntityManager` của TypeORM ở bất cứ đâu trong project, mà không cần import module nào. Ví dụ:

```typescript
@@filename(app.module)
import { DataSource } from 'typeorm';

@Module({
  imports: [TypeOrmModule.forRoot(), UsersModule],
})
export class AppModule {
  constructor(private dataSource: DataSource) {}
}
@@switch
import { DataSource } from 'typeorm';

@Dependencies(DataSource)
@Module({
  imports: [TypeOrmModule.forRoot(), UsersModule],
})
export class AppModule {
  constructor(dataSource) {
    this.dataSource = dataSource;
  }
}
```

#### Repository pattern

[TypeORM](https://github.com/typeorm/typeorm) hỗ trợ **repository design pattern**, nên mỗi entity có repository riêng. Bạn lấy các repository này từ data source.

Để tiếp tục ví dụ, ta cần ít nhất một entity. Hãy định nghĩa entity `User`.

```typescript
@@filename(user.entity)
import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  firstName: string;

  @Column()
  lastName: string;

  @Column({ default: true })
  isActive: boolean;
}
```

> info **Gợi ý** Tìm hiểu thêm về entity trong [tài liệu TypeORM](https://typeorm.io/docs/entity/entities/).

File entity `User` nằm trong thư mục `users`, thư mục này chứa mọi file liên quan tới `UsersModule`. Bạn có thể đặt các file model ở bất cứ đâu, nhưng chúng tôi khuyên đặt chúng gần **domain** của chúng, trong thư mục module tương ứng.

Để bắt đầu dùng entity `User`, hãy cho TypeORM biết về nó bằng cách thêm nó vào mảng `entities` trong tùy chọn của `forRoot()` (trừ khi bạn dùng đường dẫn glob tĩnh):

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { User } from './users/user.entity.js';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'mysql',
      host: 'localhost',
      port: 3306,
      username: 'root',
      password: 'root',
      database: 'test',
      entities: [User],
      synchronize: true,
    }),
  ],
})
export class AppModule {}
```

Tiếp theo, hãy xem `UsersModule`:

```typescript
@@filename(users.module)
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { UsersService } from './users.service.js';
import { UsersController } from './users.controller.js';
import { User } from './user.entity.js';

@Module({
  imports: [TypeOrmModule.forFeature([User])],
  providers: [UsersService],
  controllers: [UsersController],
})
export class UsersModule {}
```

Module này dùng method `forFeature()` để định nghĩa những repository nào được đăng ký trong scope hiện tại. Khi đã có nó, bạn có thể inject repository `User` vào `UsersService` bằng decorator `@InjectRepository()`:

```typescript
@@filename(users.service)
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity.js';

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private usersRepository: Repository<User>,
  ) {}

  findAll(): Promise<User[]> {
    return this.usersRepository.find();
  }

  findOne(id: number): Promise<User | null> {
    return this.usersRepository.findOneBy({ id });
  }

  async remove(id: number): Promise<void> {
    await this.usersRepository.delete(id);
  }
}
@@switch
import { Injectable, Dependencies } from '@nestjs/common';
import { getRepositoryToken } from '@nestjs/typeorm';
import { User } from './user.entity.js';

@Injectable()
@Dependencies(getRepositoryToken(User))
export class UsersService {
  constructor(usersRepository) {
    this.usersRepository = usersRepository;
  }

  findAll() {
    return this.usersRepository.find();
  }

  findOne(id) {
    return this.usersRepository.findOneBy({ id });
  }

  async remove(id) {
    await this.usersRepository.delete(id);
  }
}
```

> warning **Chú ý** Đừng quên import `UsersModule` vào root module `AppModule`.

Để dùng repository bên ngoài module import `TypeOrmModule.forFeature()`, hãy re-export các provider mà nó sinh ra. Bạn có thể làm việc này bằng cách export toàn bộ module:

```typescript
@@filename(users.module)
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { User } from './user.entity.js';

@Module({
  imports: [TypeOrmModule.forFeature([User])],
  exports: [TypeOrmModule]
})
export class UsersModule {}
```

Giờ thì nếu bạn import `UsersModule` vào `UserHttpModule`, bạn có thể dùng `@InjectRepository(User)` trong các provider của module sau:

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

Relation là liên kết giữa hai hoặc nhiều bảng, dựa trên các trường chung của mỗi bảng, thường liên quan tới khóa chính và khóa ngoại.

Có ba loại relation:

<table>
  <tr>
    <td><code>One-to-one</code></td>
    <td>Mỗi dòng trong bảng chính có một và chỉ một dòng liên kết trong bảng ngoại. Dùng decorator <code>@OneToOne()</code> để định nghĩa loại relation này.</td>
  </tr>
  <tr>
    <td><code>One-to-many / Many-to-one</code></td>
    <td>Mỗi dòng trong bảng chính có một hoặc nhiều dòng liên quan trong bảng ngoại. Dùng các decorator <code>@OneToMany()</code> và <code>@ManyToOne()</code> để định nghĩa loại relation này.</td>
  </tr>
  <tr>
    <td><code>Many-to-many</code></td>
    <td>Mỗi dòng trong bảng chính có nhiều dòng liên quan trong bảng ngoại, và mỗi dòng trong bảng ngoại có nhiều dòng liên quan trong bảng chính. Dùng decorator <code>@ManyToMany()</code> để định nghĩa loại relation này.</td>
  </tr>
</table>

Để định nghĩa relation trong entity, hãy dùng các **decorator** tương ứng. Ví dụ, để định nghĩa mỗi `User` có thể có nhiều ảnh, dùng decorator `@OneToMany()`.

```typescript
@@filename(user.entity)
import { Entity, Column, PrimaryGeneratedColumn, OneToMany } from 'typeorm';
import { Photo } from '../photos/photo.entity.js';

@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  firstName: string;

  @Column()
  lastName: string;

  @Column({ default: true })
  isActive: boolean;

  @OneToMany(type => Photo, photo => photo.user)
  photos: Photo[];
}
```

> info **Gợi ý** Để tìm hiểu thêm về relation trong TypeORM, xem [tài liệu TypeORM](https://typeorm.io/docs/relations/relations).

#### Tự động load entity <a id="auto-load-entities"></a>

Thêm entity thủ công vào mảng `entities` trong tùy chọn data source có thể khá nhàm chán. Ngoài ra, tham chiếu entity từ root module sẽ phá vỡ ranh giới domain của ứng dụng và để lộ chi tiết implementation ra các phần khác. Để tránh điều này, hãy đặt thuộc tính `autoLoadEntities` của options object truyền vào `forRoot()` thành `true`:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      ...
      autoLoadEntities: true,
    }),
  ],
})
export class AppModule {}
```

Khi bật tùy chọn này, mọi entity đăng ký qua method `forFeature()` sẽ tự động được thêm vào mảng `entities` trong tùy chọn data source.

> warning **Cảnh báo** Những entity không được đăng ký qua `forFeature()`, mà chỉ được tham chiếu từ entity khác (qua relation), sẽ không được thiết lập `autoLoadEntities` đưa vào.

#### Tách định nghĩa entity <a id="separating-entity-definition"></a>

Bạn có thể định nghĩa entity và các cột của nó ngay trong class model, bằng decorator. Cách khác là định nghĩa entity và các cột trong các file riêng bằng [entity schema](https://typeorm.io/docs/entity/separating-entity-definition).

```typescript
import { EntitySchema } from 'typeorm';
import { User } from './user.entity.js';

export const UserSchema = new EntitySchema<User>({
  name: 'User',
  target: User,
  columns: {
    id: {
      type: Number,
      primary: true,
      generated: true,
    },
    firstName: {
      type: String,
    },
    lastName: {
      type: String,
    },
    isActive: {
      type: Boolean,
      default: true,
    },
  },
  relations: {
    photos: {
      type: 'one-to-many',
      target: 'Photo', // the name of the PhotoSchema
    },
  },
});
```

> warning **Cảnh báo** Nếu bạn cung cấp tùy chọn `target`, tùy chọn `name` phải trùng với tên của class target. Nếu không cung cấp `target`, bạn có thể dùng tên bất kỳ.

Nest cho phép bạn dùng một instance `EntitySchema` ở bất cứ đâu cần một class entity. Ví dụ:

```typescript
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { UserSchema } from './user.schema.js';
import { UsersController } from './users.controller.js';
import { UsersService } from './users.service.js';

@Module({
  imports: [TypeOrmModule.forFeature([UserSchema])],
  providers: [UsersService],
  controllers: [UsersController],
})
export class UsersModule {}
```

#### Transaction trong TypeORM <a id="typeorm-transactions"></a>

Một [database transaction](https://en.wikipedia.org/wiki/Database_transaction) là một đơn vị công việc thực hiện trên database và được xử lý một cách nhất quán, tin cậy, độc lập với các transaction khác. Nhìn chung, một transaction đại diện cho mọi thay đổi trong database.

Có vài chiến lược để xử lý [transaction trong TypeORM](https://typeorm.io/docs/advanced-topics/transactions/). Chúng tôi khuyên dùng class `QueryRunner`, vì nó cho bạn toàn quyền kiểm soát transaction.

Đầu tiên, inject object `DataSource` vào class như bình thường:

```typescript
@Injectable()
export class UsersService {
  constructor(private dataSource: DataSource) {}
}
```

> info **Gợi ý** Class `DataSource` được import từ package `typeorm`.

Sau đó dùng nó để tạo transaction:

```typescript
async createMany(users: User[]) {
  const queryRunner = this.dataSource.createQueryRunner();

  await queryRunner.connect();
  await queryRunner.startTransaction();
  try {
    await queryRunner.manager.save(users[0]);
    await queryRunner.manager.save(users[1]);

    await queryRunner.commitTransaction();
  } catch (err) {
    // since we have errors, roll back the changes we made
    await queryRunner.rollbackTransaction();
  } finally {
    // you need to release a manually instantiated query runner
    await queryRunner.release();
  }
}
```

> info **Gợi ý** `dataSource` chỉ được dùng để tạo `QueryRunner`. Tuy nhiên, test class này sẽ đòi hỏi mock toàn bộ object `DataSource`, vốn có rất nhiều method. Thay vào đó, chúng tôi khuyên dùng một class factory helper (ví dụ `QueryRunnerFactory`) implement một interface chỉ có những method cần thiết để quản lý transaction. Cách này giúp các method đó dễ mock.

<app-banner-observe></app-banner-observe>

Cách khác là dùng method `transaction()` kiểu callback của object `DataSource` (xem [Creating and using transactions](https://typeorm.io/docs/advanced-topics/transactions/#creating-and-using-transactions) trong tài liệu TypeORM):

```typescript
async createMany(users: User[]) {
  await this.dataSource.transaction(async manager => {
    await manager.save(users[0]);
    await manager.save(users[1]);
  });
}
```

#### Subscriber <a id="subscribers"></a>

Với [subscriber](https://typeorm.io/docs/advanced-topics/listeners-and-subscribers#what-is-a-subscriber) của TypeORM, bạn có thể lắng nghe các event cụ thể của entity.

```typescript
import {
  DataSource,
  EntitySubscriberInterface,
  EventSubscriber,
  InsertEvent,
} from 'typeorm';
import { User } from './user.entity.js';

@EventSubscriber()
export class UserSubscriber implements EntitySubscriberInterface<User> {
  constructor(dataSource: DataSource) {
    dataSource.subscribers.push(this);
  }

  listenTo() {
    return User;
  }

  beforeInsert(event: InsertEvent<User>) {
    console.log(`BEFORE USER INSERTED: `, event.entity);
  }
}
```

> error **Cảnh báo** Event subscriber không thể là [request-scoped](/fundamentals/injection-scopes).

Giờ hãy thêm class `UserSubscriber` vào mảng `providers`:

```typescript
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { User } from './user.entity.js';
import { UsersController } from './users.controller.js';
import { UsersService } from './users.service.js';
import { UserSubscriber } from './user.subscriber.js';

@Module({
  imports: [TypeOrmModule.forFeature([User])],
  providers: [UsersService, UserSubscriber],
  controllers: [UsersController],
})
export class UsersModule {}
```

#### Migration <a id="migrations"></a>

[Migration](https://typeorm.io/docs/advanced-topics/migrations/) cung cấp cách cập nhật dần schema database để giữ nó đồng bộ với data model của ứng dụng, trong khi vẫn giữ nguyên dữ liệu hiện có trong database. Để sinh, chạy và revert migration, TypeORM cung cấp một [CLI](https://typeorm.io/docs/advanced-topics/migrations/#creating-a-new-migration) chuyên dụng.

Các class migration tách biệt khỏi mã nguồn ứng dụng Nest, và TypeORM quản lý vòng đời của chúng. Vì vậy, bạn không thể dùng dependency injection hay các tính năng đặc thù khác của Nest trong migration. Để tìm hiểu thêm, xem [hướng dẫn migration](https://typeorm.io/docs/advanced-topics/migrations/) trong tài liệu TypeORM.

#### Nhiều database <a id="multiple-databases"></a>

Một số project cần nhiều kết nối database, và module này cũng hỗ trợ điều đó. Để làm việc với nhiều kết nối, trước tiên hãy tạo chúng. Trong trường hợp này, mọi data source ngoài data source mặc định đều phải có một **name** duy nhất.

Giả sử bạn có một entity `Album` được lưu trong database riêng của nó.

```typescript
const defaultOptions = {
  type: 'postgres' as const,
  port: 5432,
  username: 'user',
  password: 'password',
  database: 'db',
  synchronize: true,
};

@Module({
  imports: [
    TypeOrmModule.forRoot({
      ...defaultOptions,
      host: 'user_db_host',
      entities: [User],
    }),
    TypeOrmModule.forRoot({
      ...defaultOptions,
      name: 'albumsConnection',
      host: 'album_db_host',
      entities: [Album],
    }),
  ],
})
export class AppModule {}
```

> warning **Chú ý** Nếu bạn không đặt `name` cho một data source, tên của nó sẽ là `default`. Đừng đăng ký nhiều data source không có tên, hoặc trùng tên; nếu không, chúng sẽ ghi đè lẫn nhau.

> warning **Chú ý** Nếu bạn dùng `TypeOrmModule.forRootAsync()`, bạn **cũng** phải đặt tên data source bên ngoài `useFactory`. Ví dụ:
>
> ```typescript
> TypeOrmModule.forRootAsync({
>   name: 'albumsConnection',
>   useFactory: ...,
>   inject: ...,
> }),
> ```
>
> Để biết thêm chi tiết, xem [issue #86 của nestjs/typeorm](https://github.com/nestjs/typeorm/issues/86).

Lúc này, mỗi entity `User` và `Album` được đăng ký với data source riêng của nó. Với cách thiết lập này, bạn phải cho method `TypeOrmModule.forFeature()` và decorator `@InjectRepository()` biết cần dùng data source nào. Nếu bạn không truyền tên data source, data source `default` sẽ được dùng.

```typescript
@Module({
  imports: [
    TypeOrmModule.forFeature([User]),
    TypeOrmModule.forFeature([Album], 'albumsConnection'),
  ],
})
export class AppModule {}
```

Bạn cũng có thể inject `DataSource` hoặc `EntityManager` của một data source cụ thể:

```typescript
@Injectable()
export class AlbumsService {
  constructor(
    @InjectDataSource('albumsConnection')
    private dataSource: DataSource,
    @InjectEntityManager('albumsConnection')
    private entityManager: EntityManager,
  ) {}
}
```

Bạn cũng có thể inject bất kỳ `DataSource` nào vào một factory provider bằng hàm `getDataSourceToken()`:

```typescript
@Module({
  providers: [
    {
      provide: AlbumsService,
      useFactory: (albumsConnection: DataSource) => {
        return new AlbumsService(albumsConnection);
      },
      inject: [getDataSourceToken('albumsConnection')],
    },
  ],
})
export class AlbumsModule {}
```

#### Test <a id="testing"></a>

Khi unit test một ứng dụng, thông thường bạn muốn tránh kết nối tới database, để các test suite độc lập và chạy nhanh nhất có thể. Tuy nhiên, các class của bạn có thể phụ thuộc vào repository lấy từ instance data source. Giải pháp là tạo các mock repository bằng [custom provider](/fundamentals/custom-providers). Mỗi repository đã đăng ký được tự động đại diện bởi một token `<EntityName>Repository`, trong đó `EntityName` là tên class entity của bạn.

Package `@nestjs/typeorm` export hàm `getRepositoryToken()`, hàm này trả về token đó cho một entity cụ thể. Với data source có tên, hãy truyền tên data source làm tham số thứ hai.

```typescript
@Module({
  providers: [
    UsersService,
    {
      provide: getRepositoryToken(User),
      useValue: mockRepository,
    },
  ],
})
export class UsersModule {}
```

Giờ thì `mockRepository` được dùng làm repository `User`. Mỗi khi một class inject nó bằng `@InjectRepository(User)`, Nest sẽ cung cấp object `mockRepository` đã đăng ký.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Có thể bạn muốn truyền tùy chọn module theo kiểu bất đồng bộ thay vì tĩnh. Khi đó, hãy dùng method `forRootAsync()`, method này hỗ trợ vài cách để cung cấp cấu hình bất đồng bộ.

Một cách là dùng hàm factory:

```typescript
TypeOrmModule.forRootAsync({
  useFactory: () => ({
    type: 'mysql',
    host: 'localhost',
    port: 3306,
    username: 'root',
    password: 'root',
    database: 'test',
    entities: [],
    synchronize: true,
  }),
});
```

Factory này hoạt động như mọi [provider bất đồng bộ](/fundamentals/async-providers) khác (ví dụ nó có thể là `async`, và có thể inject dependency qua `inject`).

```typescript
TypeOrmModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: (configService: ConfigService) => ({
    type: 'mysql',
    host: configService.get('HOST'),
    port: +configService.get('PORT'),
    username: configService.get('USERNAME'),
    password: configService.get('PASSWORD'),
    database: configService.get('DATABASE'),
    entities: [],
    synchronize: true,
  }),
  inject: [ConfigService],
});
```

Cách khác là dùng cú pháp `useClass`:

```typescript
TypeOrmModule.forRootAsync({
  useClass: TypeOrmConfigService,
});
```

Cách khai báo trên khởi tạo `TypeOrmConfigService` bên trong `TypeOrmModule` và dùng nó để tạo options object bằng cách gọi `createTypeOrmOptions()`. Điều này có nghĩa là `TypeOrmConfigService` phải implement interface `TypeOrmOptionsFactory`:

```typescript
@Injectable()
export class TypeOrmConfigService implements TypeOrmOptionsFactory {
  createTypeOrmOptions(): TypeOrmModuleOptions {
    return {
      type: 'mysql',
      host: 'localhost',
      port: 3306,
      username: 'root',
      password: 'root',
      database: 'test',
      entities: [],
      synchronize: true,
    };
  }
}
```

Để dùng lại một provider được import từ module khác thay vì tạo `TypeOrmConfigService` bên trong `TypeOrmModule`, hãy dùng cú pháp `useExisting`:

```typescript
TypeOrmModule.forRootAsync({
  imports: [ConfigModule],
  useExisting: ConfigService,
});
```

Cách này hoạt động giống `useClass`, với một khác biệt quan trọng: `TypeOrmModule` sẽ tìm trong các module đã import để dùng lại một `ConfigService` đã có thay vì khởi tạo cái mới.

> info **Gợi ý** Hãy định nghĩa thuộc tính `name` ở cùng cấp với thuộc tính `useFactory`, `useClass` hoặc `useExisting`. Điều này cho phép Nest đăng ký data source dưới đúng injection token.

#### DataSource factory tùy chỉnh <a id="custom-datasource-factory"></a>

Cùng với cấu hình bất đồng bộ (`useFactory`, `useClass` hoặc `useExisting`), bạn có thể chỉ định thêm hàm `dataSourceFactory` để tự cung cấp data source TypeORM thay vì để `TypeOrmModule` tạo nó.

`dataSourceFactory` nhận `DataSourceOptions` của TypeORM đã được resolve bởi cấu hình bất đồng bộ và trả về một `Promise` resolve ra một `DataSource` của TypeORM. Nếu data source trả về chưa được khởi tạo, `TypeOrmModule` sẽ khởi tạo nó (trừ khi có đặt `manualInitialization`).

```typescript
TypeOrmModule.forRootAsync({
  imports: [ConfigModule],
  inject: [ConfigService],
  // Use useFactory, useClass, or useExisting
  // to configure the DataSourceOptions.
  useFactory: (configService: ConfigService) => ({
    type: 'mysql',
    host: configService.get('HOST'),
    port: +configService.get('PORT'),
    username: configService.get('USERNAME'),
    password: configService.get('PASSWORD'),
    database: configService.get('DATABASE'),
    entities: [],
    synchronize: true,
  }),
  // dataSourceFactory receives the configured DataSourceOptions
  // and returns a Promise<DataSource>.
  dataSourceFactory: async (options) => {
    const dataSource = await new DataSource(options!).initialize();
    return dataSource;
  },
});
```

> info **Gợi ý** Class `DataSource` được import từ package `typeorm`.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có sẵn trong [ứng dụng mẫu TypeORM](https://github.com/nestjs/nest/tree/master/sample/05-sql-typeorm) trong repository NestJS.

<app-banner-enterprise></app-banner-enterprise>
