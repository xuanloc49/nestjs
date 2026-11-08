### MikroORM

[MikroORM](https://mikro-orm.io) là một ORM TypeScript cho Node.js dựa trên các pattern Data Mapper, Unit of Work và Identity Map. Nó hỗ trợ MongoDB, MySQL, MariaDB, PostgreSQL, SQLite, Microsoft SQL Server và Oracle. Package `@mikro-orm/nestjs` tích hợp nó với Nest: nó đăng ký ORM và `EntityManager` của ORM làm provider, hỗ trợ inject repository, tạo một request context cho mỗi HTTP request, và đóng kết nối database khi ứng dụng tắt.

Chương này trình bày các phần đặc thù của Nest trong việc tích hợp. Xem [tài liệu MikroORM](https://mikro-orm.io/docs) để có thông tin đầy đủ về bản thân ORM.

> info **Lưu ý** `@mikro-orm/nestjs` là package của bên thứ ba và không do core team NestJS quản lý. Hãy báo lỗi liên quan tới library này tại [repository mikro-orm/nestjs](https://github.com/mikro-orm/nestjs).

> info **Gợi ý** Chương này dành cho MikroORM v7 và `@mikro-orm/nestjs` v7. Nếu bạn đang nâng cấp từ MikroORM v6, xem [hướng dẫn nâng cấp MikroORM từ v6 lên v7](https://mikro-orm.io/docs/upgrading-v6-to-v7).

#### Cài đặt <a id="installation"></a>

Cài module Nest cùng với MikroORM, package decorator của nó, và driver cho database của bạn. Chương này dùng SQLite:

```bash
$ npm i @mikro-orm/nestjs @mikro-orm/core @mikro-orm/decorators @mikro-orm/sqlite
```

MikroORM cung cấp một package driver cho mỗi database được hỗ trợ, như `@mikro-orm/postgresql`, `@mikro-orm/mysql` và `@mikro-orm/mongodb`. Xem [hướng dẫn quick start của MikroORM](https://mikro-orm.io/docs/quick-start#installation) để có danh sách đầy đủ.

> info **Gợi ý** Kể từ MikroORM v7, decorator không còn được export từ `@mikro-orm/core`. Các project Nest dùng legacy decorator (experimental), nên hãy import các decorator như `@Entity()` và `@Property()` từ `@mikro-orm/decorators/legacy`. Import `EntityManager`, `EntityRepository` và `MikroORM` từ package driver của bạn (ví dụ `@mikro-orm/sqlite`), còn các type khác (ví dụ symbol `EntityRepositoryType`) từ `@mikro-orm/core`. Các đoạn code trong chương này đều kèm câu import tương ứng.

Sau khi cài xong, import `MikroOrmModule` vào root module `AppModule`:

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { ReflectMetadataProvider } from '@mikro-orm/decorators/legacy';
import { SqliteDriver } from '@mikro-orm/sqlite';

@Module({
  imports: [
    MikroOrmModule.forRoot({
      driver: SqliteDriver,
      dbName: 'my-db-name.sqlite3',
      entities: ['./dist/**/*.entity.js'],
      entitiesTs: ['./src/**/*.entity.ts'],
      metadataProvider: ReflectMetadataProvider,
    }),
  ],
})
export class AppModule {}
```

Method `forRoot()` nhận cùng configuration object như `MikroORM.init()`. Xem [tài liệu cấu hình MikroORM](https://mikro-orm.io/docs/configuration) để có danh sách tùy chọn đầy đủ. Các glob pattern `entities` và `entitiesTs` cho MikroORM biết nơi tìm các file entity: nó dùng `entitiesTs` khi chạy từ mã nguồn TypeScript và `entities` khi chạy từ JavaScript đã compile (xem [folder-based discovery](https://mikro-orm.io/docs/folder-based-discovery)).

> info **Gợi ý** Kể từ MikroORM v7, `ReflectMetadataProvider` không còn là metadata provider mặc định. Hãy đặt nó tường minh như ở trên, để MikroORM suy ra type của thuộc tính từ metadata mà TypeScript emit cho legacy decorator.

Ngoài ra, `forRoot()` hỗ trợ các tùy chọn đặc thù của Nest sau, tất cả đều được mô tả ở phần sau của chương:

<table>
  <tr>
    <td><code>autoLoadEntities</code></td>
    <td>Nếu là <code>true</code>, các entity đăng ký qua <code>forFeature()</code> sẽ được tự động thêm vào cấu hình (mặc định: <code>false</code>)</td>
  </tr>
  <tr>
    <td><code>registerRequestContext</code></td>
    <td>Nếu là <code>true</code>, đăng ký một middleware tạo request context cho mỗi HTTP request (mặc định: <code>true</code>)</td>
  </tr>
  <tr>
    <td><code>forRoutesPath</code></td>
    <td>Route path mà middleware request context áp dụng (mặc định: mọi route)</td>
  </tr>
  <tr>
    <td><code>scope</code></td>
    <td><a href="/fundamentals/injection-scopes">Injection scope</a> của provider <code>EntityManager</code> (mặc định: <code>Scope.DEFAULT</code>)</td>
  </tr>
  <tr>
    <td><code>contextName</code></td>
    <td>Tên của kết nối, bắt buộc khi bạn kết nối tới <a href="/data/mikroorm#multiple-databases">nhiều database</a></td>
  </tr>
</table>

Cách khác là giữ cấu hình trong một file `mikro-orm.config.ts` riêng, file mà [MikroORM CLI](https://mikro-orm.io/docs/quick-start#setting-up-the-commandline-tool) cũng dùng. Helper `defineConfig()` do package driver export sẽ tự đặt tùy chọn `driver` giúp bạn:

```typescript
// mikro-orm.config.ts
import { ReflectMetadataProvider } from '@mikro-orm/decorators/legacy';
import { defineConfig } from '@mikro-orm/sqlite';

export default defineConfig({
  dbName: 'my-db-name.sqlite3',
  entities: ['./dist/**/*.entity.js'],
  entitiesTs: ['./src/**/*.entity.ts'],
  metadataProvider: ReflectMetadataProvider,
});
```

Sau đó truyền cấu hình vào `forRoot()`. Kể từ MikroORM v7, `forRoot()` không còn nhận danh sách tham số rỗng, nên bạn phải truyền cấu hình một cách tường minh:

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import config from './mikro-orm.config.js';

@Module({
  imports: [MikroOrmModule.forRoot(config)],
})
export class AppModule {}
```

Sau đó, các object `MikroORM` và `EntityManager` có thể inject được trong toàn bộ project, mà không cần import module nào ở nơi khác:

```typescript
import { Injectable } from '@nestjs/common';
import { EntityManager, MikroORM } from '@mikro-orm/sqlite';

@Injectable()
export class AppService {
  constructor(
    private readonly orm: MikroORM,
    private readonly em: EntityManager,
  ) {}
}
```

> info **Lưu ý** Import `EntityManager` và `MikroORM` từ package `@mikro-orm/<driver>`, trong đó `<driver>` là `sqlite`, `postgresql`, `mysql`, hoặc driver nào bạn dùng, để có API đặc thù của driver. Nếu bạn có cài `@mikro-orm/sql` làm dependency, bạn cũng có thể import `EntityManager` từ đó. Các class generic do `@mikro-orm/core` export cũng được đăng ký làm injection token.

#### Repository <a id="repositories"></a>

MikroORM hỗ trợ repository design pattern, nên mỗi entity có repository riêng. Xem [tài liệu repository của MikroORM](https://mikro-orm.io/docs/repositories) để biết chi tiết. Để tiếp tục ví dụ, hãy định nghĩa một entity `Photo`:

```typescript
// photo/photo.entity.ts
import { Entity, PrimaryKey, Property } from '@mikro-orm/decorators/legacy';

@Entity()
export class Photo {
  @PrimaryKey()
  id: number;

  @Property()
  name: string;
}
```

> info **Gợi ý** Ngoài decorator, MikroORM có thể định nghĩa entity bằng helper `defineEntity()` hoặc class `EntitySchema`. Tìm hiểu thêm trong [hướng dẫn định nghĩa entity của MikroORM](https://mikro-orm.io/docs/defining-entities).

Để định nghĩa những repository nào được đăng ký trong scope hiện tại, dùng method `forFeature()`:

```typescript
// photo/photo.module.ts
import { Module } from '@nestjs/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { Photo } from './photo.entity.js';
import { PhotoService } from './photo.service.js';
import { PhotoController } from './photo.controller.js';

@Module({
  imports: [MikroOrmModule.forFeature([Photo])],
  providers: [PhotoService],
  controllers: [PhotoController],
})
export class PhotoModule {}
```

> info **Lưu ý** Đừng đăng ký các base entity qua `forFeature()`, vì không có repository nào cho chúng. Tuy nhiên, base entity vẫn cần là một phần của cấu hình ORM (ví dụ tùy chọn `entities` của `forRoot()`).

Sau đó import `PhotoModule` vào root module `AppModule`:

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import config from './mikro-orm.config.js';
import { PhotoModule } from './photo/photo.module.js';

@Module({
  imports: [MikroOrmModule.forRoot(config), PhotoModule],
})
export class AppModule {}
```

Giờ bạn có thể inject repository `Photo` vào `PhotoService` bằng decorator `@InjectRepository()`:

```typescript
// photo/photo.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityManager, EntityRepository } from '@mikro-orm/sqlite';
import { Photo } from './photo.entity.js';

@Injectable()
export class PhotoService {
  constructor(
    @InjectRepository(Photo)
    private readonly photoRepository: EntityRepository<Photo>,
    private readonly em: EntityManager,
  ) {}

  findAll(): Promise<Photo[]> {
    return this.photoRepository.findAll();
  }

  findOne(id: number): Promise<Photo | null> {
    return this.photoRepository.findOne({ id });
  }

  async create(name: string): Promise<Photo> {
    const photo = this.photoRepository.create({ name });
    await this.em.flush();
    return photo;
  }

  async remove(id: number): Promise<void> {
    const photo = await this.photoRepository.findOneOrFail({ id });
    await this.em.remove(photo).flush();
  }
}
```

Repository không có method `persist()` hay `flush()`, nên các thao tác ghi phải đi qua `EntityManager`, thứ implement pattern [Unit of Work](https://mikro-orm.io/docs/unit-of-work). Method `create()` của repository đánh dấu entity mới cần được lưu, còn `em.flush()` ghi mọi thay đổi đang chờ xuống database trong một transaction duy nhất.

#### Dùng repository tùy chỉnh <a id="using-custom-repositories"></a>

Để thêm các method query của riêng bạn, hãy kế thừa `EntityRepository` và trỏ entity tới class của bạn qua tùy chọn `repository`:

```typescript
// author/author.entity.ts
import { EntityRepositoryType } from '@mikro-orm/core';
import { Entity, PrimaryKey, Property } from '@mikro-orm/decorators/legacy';
import { AuthorRepository } from './author.repository.js';

@Entity({ repository: () => AuthorRepository })
export class Author {
  // enables type inference in `em.getRepository()`
  [EntityRepositoryType]?: AuthorRepository;

  @PrimaryKey()
  id: number;

  @Property()
  name: string;
}
```

```typescript
// author/author.repository.ts
import { EntityRepository } from '@mikro-orm/sqlite';
import { Author } from './author.entity.js';

export class AuthorRepository extends EntityRepository<Author> {
  findByName(name: string): Promise<Author | null> {
    return this.findOne({ name });
  }
}
```

Khi bạn truyền entity `Author` vào `forFeature()`, module cũng đăng ký chính class repository tùy chỉnh làm provider. Vì vậy bạn có thể inject nó bằng class của nó, mà không cần decorator `@InjectRepository()`:

```typescript
@Injectable()
export class AuthorService {
  constructor(private readonly authorRepository: AuthorRepository) {}
}
```

#### Tự động load entity <a id="load-entities-automatically"></a>

Thêm entity thủ công vào mảng `entities` của cấu hình có thể khá nhàm chán. Ngoài ra, tham chiếu entity từ root module sẽ phá vỡ ranh giới domain của ứng dụng và để lộ chi tiết implementation ra các phần khác. Đường dẫn glob giải quyết được vấn đề này, nhưng chúng không hoạt động khi bạn bundle ứng dụng (ví dụ trong một [monorepo](/cli/monorepo)): MikroORM tìm các file khớp lúc runtime, mà một bundle không chứa chúng dưới dạng các file riêng.

Một cách khác là tự động load entity bằng cách đặt thuộc tính `autoLoadEntities` của configuration object (truyền vào method `forRoot()`) thành `true`, như bên dưới:

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { ReflectMetadataProvider } from '@mikro-orm/decorators/legacy';
import { SqliteDriver } from '@mikro-orm/sqlite';

@Module({
  imports: [
    MikroOrmModule.forRoot({
      driver: SqliteDriver,
      dbName: 'my-db-name.sqlite3',
      metadataProvider: ReflectMetadataProvider,
      autoLoadEntities: true,
    }),
  ],
})
export class AppModule {}
```

Khi bật tùy chọn này, mọi entity đăng ký qua method `forFeature()` sẽ tự động được thêm vào mảng `entities` của configuration object.

> info **Lưu ý** Những entity không được đăng ký qua method `forFeature()`, mà chỉ được tham chiếu từ một entity khác (qua relationship), sẽ không được thiết lập `autoLoadEntities` đưa vào.

> info **Lưu ý** `autoLoadEntities` không có tác dụng với MikroORM CLI, CLI vẫn cần một cấu hình CLI với danh sách entity đầy đủ. Tuy nhiên, bạn có thể dùng glob ở đó, vì CLI không chạy bundle của bạn.

#### Request context

MikroORM giữ các entity đã load trong một [identity map](https://mikro-orm.io/docs/identity-map), thứ không được phép chia sẻ giữa các request đồng thời. Mỗi request cần một bản fork riêng của `EntityManager`, với một identity map sạch. `MikroOrmModule` lo việc này giúp bạn: nó đăng ký một middleware cho mọi route, chạy mỗi HTTP request bên trong một `RequestContext`. Bên trong context đó, `EntityManager` global mà bạn inject (và mọi repository phụ thuộc vào nó) sẽ âm thầm chuyển việc cho bản fork của request.

Bên ngoài request context, MikroORM từ chối dùng `EntityManager` global cho các thao tác phụ thuộc vào identity map, như `find()` hay `flush()`, và throw một `ValidationError`. [Phần tiếp theo](/data/mikroorm#request-scoped-handlers-in-queues) chỉ cách tạo context cho code không chạy như một phần của HTTP request.

Để chỉ áp dụng middleware cho một tập con route, hãy đặt tùy chọn `forRoutesPath`. Để tắt nó, đặt `registerRequestContext` thành `false`. Ví dụ, thay vì dùng middleware, bạn có thể để Nest tạo một bản fork `EntityManager` cho mỗi request bằng cách cho provider `EntityManager` là [request-scoped](/fundamentals/injection-scopes):

```typescript
// app.module.ts
import { Module, Scope } from '@nestjs/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import config from './mikro-orm.config.js';

@Module({
  imports: [
    MikroOrmModule.forRoot({
      ...config,
      registerRequestContext: false,
      scope: Scope.REQUEST,
    }),
  ],
})
export class AppModule {}
```

> warning **Cảnh báo** Với `scope: Scope.REQUEST`, mọi provider phụ thuộc vào `EntityManager` (kể cả repository) cũng trở thành request-scoped. Điều này ảnh hưởng tới hiệu năng, như mô tả trong [chương injection scope](/fundamentals/injection-scopes#performance).

#### Handler có request context trong queue <a id="request-scoped-handlers-in-queues"></a>

Middleware chỉ chạy cho HTTP request. Code nằm ngoài luồng đó, như consumer của [queue](/application/queues) và [tác vụ theo lịch](/application/task-scheduling), không có request context, nên bạn phải tự tạo.

Với các method này, hãy dùng decorator `@CreateRequestContext()`. Nó fork `EntityManager` và chạy method `async` được decorate bên trong một context mới. Decorator tìm `EntityManager` thông qua thuộc tính `orm` (một instance `MikroORM`) hoặc thuộc tính `em` (một `EntityManager`) của class, nên hãy inject một trong hai dưới đúng tên đó:

```typescript
import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { CreateRequestContext } from '@mikro-orm/decorators/legacy';
import { MikroORM } from '@mikro-orm/sqlite';
import { Photo } from './photo.entity.js';

@Injectable()
export class PhotoStatsService {
  private readonly logger = new Logger(PhotoStatsService.name);

  constructor(private readonly orm: MikroORM) {}

  @Cron(CronExpression.EVERY_HOUR)
  @CreateRequestContext()
  async logPhotoCount() {
    // runs in a separate context, with its own identity map
    const count = await this.orm.em.count(Photo);
    this.logger.log(`Found ${count} photos`);
  }
}
```

> warning **Cảnh báo** Hãy đặt `@CreateRequestContext()` ngay trên method, bên dưới các method decorator khác như `@Cron()`. Decorator này thay method bằng một wrapper. Các decorator liệt kê phía trên nó sẽ gắn metadata vào wrapper đó, còn các decorator liệt kê phía dưới sẽ gắn metadata vào method gốc, thứ mà Nest không bao giờ nhìn thấy (trong ví dụ này, cron job sẽ không được đăng ký).

> info **Lưu ý** Đúng như tên gọi, decorator này luôn tạo một context mới, khác với phương án thay thế `@EnsureRequestContext()`, decorator chỉ tạo context nếu method chưa chạy bên trong một context khác. Trước MikroORM v6, `@CreateRequestContext()` có tên là `@UseRequestContext()`, và trước v7, nó được export từ `@mikro-orm/core`.

#### Transaction <a id="transactions"></a>

MikroORM xếp hàng mọi thao tác ghi cho đến khi bạn gọi `em.flush()`, lúc đó nó bọc chúng trong một transaction duy nhất. Để tự kiểm soát ranh giới transaction, ví dụ để flush nhiều lần hoặc kết hợp các thay đổi với query khác, hãy dùng method `em.transactional()`:

```typescript
import { Injectable } from '@nestjs/common';
import { EntityManager } from '@mikro-orm/sqlite';
import { Photo } from './photo.entity.js';

@Injectable()
export class PhotoService {
  constructor(private readonly em: EntityManager) {}

  async createMany(names: string[]): Promise<void> {
    await this.em.transactional(async (em) => {
      for (const name of names) {
        em.create(Photo, { name });
      }
    });
  }
}
```

Callback nhận một `EntityManager` đã fork, chạy bên trong transaction. Khi callback hoàn tất, MikroORM flush bản fork và commit transaction. Nếu callback throw, MikroORM rollback transaction và throw lại lỗi.

Cách khác là dùng decorator `@Transactional()`, decorator này bọc method `async` được decorate trong `em.transactional()`:

```typescript
import { Injectable } from '@nestjs/common';
import { Transactional } from '@mikro-orm/decorators/legacy';
import { EntityManager } from '@mikro-orm/sqlite';
import { Photo } from './photo.entity.js';

@Injectable()
export class PhotoService {
  constructor(private readonly em: EntityManager) {}

  @Transactional()
  async createMany(names: string[]): Promise<void> {
    for (const name of names) {
      this.em.create(Photo, { name });
    }
  }
}
```

Giống như `@CreateRequestContext()`, decorator tìm `EntityManager` qua thuộc tính `em` hoặc `orm` của class, và quay về context hiện tại nếu class không có cả hai. Khi được gọi bên trong một transaction khác, `em.transactional()` bắt đầu một nested transaction (savepoint), còn `@Transactional()` mặc định tham gia vào transaction hiện có. Xem [tài liệu transaction của MikroORM](https://mikro-orm.io/docs/transactions) để biết về các tùy chọn propagation, isolation level và locking.

#### Serialization

Entity của MikroORM có method `toJSON()` áp dụng các [quy tắc serialization](https://mikro-orm.io/docs/serializing) của MikroORM: nó bỏ qua các thuộc tính ẩn, áp dụng serializer tùy chỉnh cho thuộc tính, và serialize các relation đã populate thành object lồng nhau, còn các relation chưa populate thành khóa chính của chúng. Khi một route handler trả về entity, Nest chuyển nó thành JSON, nên các quy tắc này được áp dụng tự động.

> warning **Cảnh báo** Đừng dùng [serializer có sẵn của Nest](/application/serialization) (`ClassSerializerInterceptor`) với entity của MikroORM. Nó dựa vào `class-transformer`, thứ không hiểu các wrapper mà MikroORM dùng cho relation: nó serialize cấu trúc nội bộ của một `Reference`, và việc duyệt qua một `Collection` dẫn tới đệ quy vô hạn (lỗi "Maximum call stack size exceeded").

Thay vào đó, hãy cấu hình serialization trên entity bằng các tùy chọn của MikroORM:

```typescript
// book/book.entity.ts
import { type Rel } from '@mikro-orm/core';
import { Entity, ManyToOne, PrimaryKey, Property } from '@mikro-orm/decorators/legacy';
import { Author } from '../author/author.entity.js';

@Entity()
export class Book {
  @PrimaryKey()
  id: number;

  @Property()
  title: string;

  @Property({ hidden: true }) // Equivalent of class-transformer's `@Exclude()`
  hiddenField: number = Date.now();

  @Property({ persist: false }) // Similar to class-transformer's `@Expose()`. Only exists in memory, but is serialized.
  count?: number;

  @ManyToOne(() => Author, {
    serializer: (author: Author) => author.name,
    serializedName: 'authorName',
  }) // Equivalent of class-transformer's `@Transform()`
  author: Rel<Author>;
}
```

> info **Gợi ý** Khi các entity tham chiếu lẫn nhau, hãy bọc type của relation trong `Rel<T>` (hoặc dùng `Ref<T>`) từ `@mikro-orm/core`, và truyền entity đích vào decorator relation, như ở trên. Nếu không, TypeScript sẽ emit decorator metadata tham chiếu trực tiếp tới class liên quan. Trong project ESM, các câu import vòng tròn giữa các file entity khi đó sẽ lỗi lúc khởi động với một `ReferenceError` (ví dụ "Cannot access 'Author' before initialization").

Để kiểm soát serialization cho riêng một route handler, hãy chuyển entity một cách tường minh bằng hàm `serialize()`, hàm này được export bởi package driver và bởi `@mikro-orm/core`. Nó nhận các tùy chọn như `populate`, `exclude`, `fields` và `groups`:

```typescript
@Get(':id')
async findOne(@Param('id', ParseIntPipe) id: number) {
  const book = await this.em.findOneOrFail(Book, { id }, { populate: ['author'] });
  return serialize(book, { fields: ['title', 'author'] }); // { title: '...', authorName: '...' }
}
```

Để có một object thuần với các quy tắc mặc định được áp dụng, gọi `wrap(entity).toObject()`.

#### Nhiều database <a id="multiple-databases"></a>

Để kết nối tới nhiều database, hãy gọi `MikroOrmModule.forRoot()` một lần cho mỗi database, và đặt cho mỗi kết nối một `contextName` duy nhất. Với cách thiết lập này, hãy đặt `registerRequestContext` thành `false` trên mọi kết nối, vì middleware mặc định chỉ hoạt động với một kết nối duy nhất, không có tên. Thay vào đó, import `MikroOrmModule.forMiddleware()` một lần. Middleware của nó tạo một request context bao phủ mọi kết nối:

```typescript
// app.module.ts
import { Module } from '@nestjs/common';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { ReflectMetadataProvider } from '@mikro-orm/decorators/legacy';
import { SqliteDriver } from '@mikro-orm/sqlite';
import { Album } from './album/album.entity.js';
import { Photo } from './photo/photo.entity.js';

@Module({
  imports: [
    MikroOrmModule.forRoot({
      contextName: 'photos',
      registerRequestContext: false,
      driver: SqliteDriver,
      dbName: 'photos.sqlite3',
      entities: [Photo],
      metadataProvider: ReflectMetadataProvider,
    }),
    MikroOrmModule.forRoot({
      contextName: 'albums',
      registerRequestContext: false,
      driver: SqliteDriver,
      dbName: 'albums.sqlite3',
      entities: [Album],
      metadataProvider: ReflectMetadataProvider,
    }),
    MikroOrmModule.forMiddleware(),
  ],
})
export class AppModule {}
```

> warning **Chú ý** Nếu bạn dùng `MikroOrmModule.forRootAsync()`, hãy đặt `contextName` cạnh `useFactory`, không phải bên trong options object mà factory trả về.

Với cách thiết lập này, hãy truyền tên context vào method `forFeature()` và decorator `@InjectRepository()`:

```typescript
// album/album.module.ts
@Module({
  imports: [MikroOrmModule.forFeature([Album], 'albums')],
  providers: [AlbumService],
})
export class AlbumModule {}
```

Để inject `MikroORM` hoặc `EntityManager` của một kết nối cụ thể, dùng các decorator `@InjectMikroORM()` và `@InjectEntityManager()`:

```typescript
// album/album.service.ts
import { Injectable } from '@nestjs/common';
import { InjectEntityManager, InjectMikroORM, InjectRepository } from '@mikro-orm/nestjs';
import { EntityManager, EntityRepository, MikroORM } from '@mikro-orm/sqlite';
import { Album } from './album.entity.js';

@Injectable()
export class AlbumService {
  constructor(
    @InjectRepository(Album, 'albums')
    private readonly albumRepository: EntityRepository<Album>,
    @InjectEntityManager('albums')
    private readonly em: EntityManager,
    @InjectMikroORM('albums')
    private readonly orm: MikroORM,
  ) {}
}
```

Để inject mọi instance `MikroORM` đã đăng ký dưới dạng mảng, dùng decorator `@InjectMikroORMs()`.

#### Test <a id="testing"></a>

Khi unit test một ứng dụng, thông thường bạn muốn tránh kết nối database, giúp các test suite độc lập và chạy nhanh. Tuy nhiên, các class của bạn có thể phụ thuộc vào repository và `EntityManager`. Để resolve các class này, hãy cung cấp các bản implement mock bằng [custom provider](/fundamentals/custom-providers).

Package `@mikro-orm/nestjs` cung cấp hàm `getRepositoryToken()` trả về một injection token có sẵn dựa trên entity đã cho (ví dụ `'PhotoRepository'` cho entity `Photo`), cho phép bạn mock repository. Với repository tùy chỉnh, hãy dùng chính class của nó làm token:

```typescript
import { Module } from '@nestjs/common';
import { getRepositoryToken } from '@mikro-orm/nestjs';
import { EntityManager } from '@mikro-orm/sqlite';
import { Photo } from './photo.entity.js';
import { PhotoService } from './photo.service.js';

@Module({
  providers: [
    PhotoService,
    {
      // or, for a custom repository: `provide: PhotoRepository`
      provide: getRepositoryToken(Photo),
      useValue: mockedRepository,
    },
    {
      provide: EntityManager,
      useValue: mockedEntityManager,
    },
  ],
})
export class PhotoModule {}
```

Giờ thì object `mockedRepository` được inject ở bất cứ đâu một class trong module này yêu cầu repository `Photo` bằng decorator `@InjectRepository(Photo)`. Với [nhiều database](/data/mikroorm#multiple-databases), hãy truyền tên context làm tham số thứ hai, ví dụ `getRepositoryToken(Album, 'albums')`.

#### Cấu hình bất đồng bộ <a id="async-configuration"></a>

Khi cần truyền tùy chọn module theo kiểu bất đồng bộ thay vì tĩnh, hãy dùng method `forRootAsync()`. Giống như hầu hết dynamic module, Nest cung cấp vài kỹ thuật cho cấu hình bất đồng bộ.

Một kỹ thuật là dùng hàm factory. Giống như các [factory provider](/fundamentals/custom-providers#factory-providers-usefactory) khác, hàm factory có thể là `async` và có thể inject dependency qua `inject`:

```typescript
MikroOrmModule.forRootAsync({
  imports: [ConfigModule],
  useFactory: (configService: ConfigService) => ({
    dbName: configService.getOrThrow<string>('DB_NAME'),
    autoLoadEntities: true,
    metadataProvider: ReflectMetadataProvider,
  }),
  inject: [ConfigService],
  driver: SqliteDriver,
});
```

> warning **Cảnh báo** Hãy đặt tùy chọn `driver` cạnh `useFactory`, như ở trên. Module cần biết driver trước khi gọi factory, để đăng ký các class `EntityManager` và `MikroORM` đặc thù của driver làm injection token. Không có nó, việc inject `EntityManager` từ package driver sẽ lỗi khi resolve dependency.

Cách khác là cấu hình `MikroOrmModule` bằng một class thay vì factory, như bên dưới:

```typescript
MikroOrmModule.forRootAsync({
  useClass: MikroOrmConfigService,
  driver: SqliteDriver,
});
```

Cách khai báo trên khởi tạo `MikroOrmConfigService` bên trong `MikroOrmModule`, dùng nó để tạo options object cần thiết. Trong ví dụ này, `MikroOrmConfigService` phải implement interface `MikroOrmOptionsFactory`, như bên dưới. `MikroOrmModule` gọi method `createMikroOrmOptions()` trên object đã khởi tạo của class được cung cấp.

```typescript
import { Injectable } from '@nestjs/common';
import { MikroOrmModuleOptions, MikroOrmOptionsFactory } from '@mikro-orm/nestjs';
import { ReflectMetadataProvider } from '@mikro-orm/decorators/legacy';

@Injectable()
export class MikroOrmConfigService implements MikroOrmOptionsFactory {
  createMikroOrmOptions(): MikroOrmModuleOptions {
    return {
      dbName: 'my-db-name.sqlite3',
      autoLoadEntities: true,
      metadataProvider: ReflectMetadataProvider,
    };
  }
}
```

Để dùng lại một options provider đã có thay vì tạo một bản sao riêng bên trong `MikroOrmModule`, hãy dùng cú pháp `useExisting`. Provider đó phải implement interface `MikroOrmOptionsFactory`, và một module liệt kê trong `imports` phải export nó:

```typescript
MikroOrmModule.forRootAsync({
  imports: [DatabaseConfigModule],
  useExisting: MikroOrmConfigService,
  driver: SqliteDriver,
});
```

#### Tắt ứng dụng <a id="application-shutdown"></a>

`MikroOrmModule` đóng ORM và kết nối database của nó trong lifecycle hook `onApplicationShutdown()`, hook mà Nest gọi khi bạn gọi `app.close()`. Tuy nhiên, mặc định Nest không lắng nghe các tín hiệu kết thúc process như `SIGTERM`, nên kết nối sẽ không được đóng khi process bị kết thúc. Để đóng nó cả trong trường hợp đó, hãy bật [shutdown hook](/fundamentals/lifecycle-events#application-shutdown):

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

#### Ví dụ <a id="example"></a>

Để xem các ứng dụng hoàn chỉnh dùng NestJS với MikroORM, xem các repository [nestjs-realworld-example-app](https://github.com/mikro-orm/nestjs-realworld-example-app) và [nestjs-example-app](https://github.com/mikro-orm/nestjs-example-app).
