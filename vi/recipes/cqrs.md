### CQRS

Luồng của các ứng dụng [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) (Create, Read, Update và Delete) đơn giản có thể được mô tả như sau:

1. Lớp controller xử lý HTTP request và giao việc cho lớp service.
2. Lớp service là nơi chứa phần lớn logic nghiệp vụ.
3. Service dùng repository hoặc DAO để thay đổi và lưu trữ entity.
4. Entity đóng vai trò container chứa giá trị, với setter và getter.

Dù pattern này thường đủ dùng cho các ứng dụng nhỏ và vừa, nó có thể không phải là lựa chọn tốt nhất cho các ứng dụng lớn và phức tạp hơn. Trong những trường hợp như vậy, mô hình **CQRS** (Command and Query Responsibility Segregation) có thể phù hợp và dễ mở rộng hơn, tùy yêu cầu của ứng dụng. Lợi ích của mô hình này bao gồm:

- **Tách biệt mối quan tâm**. Thao tác đọc và ghi được xử lý bởi các model riêng biệt.
- **Khả năng mở rộng**. Thao tác đọc và ghi có thể được mở rộng độc lập.
- **Linh hoạt**. Đọc và ghi có thể dùng các kho dữ liệu khác nhau.
- **Hiệu năng**. Mỗi kho dữ liệu có thể được tối ưu cho khối lượng công việc của nó (đọc hoặc ghi).

Để hỗ trợ mô hình này, Nest cung cấp một [CQRS module](https://github.com/nestjs/cqrs) gọn nhẹ. Chương này mô tả cách dùng nó.

#### Cài đặt <a id="installation"></a>

Trước tiên, hãy cài package cần thiết:

```bash
$ npm install --save @nestjs/cqrs
```

Khi đã cài đặt xong, hãy mở root module của ứng dụng (thường là `AppModule`) và import `CqrsModule.forRoot()`:

```typescript
import { Module } from '@nestjs/common';
import { CqrsModule } from '@nestjs/cqrs';

@Module({
  imports: [CqrsModule.forRoot()],
})
export class AppModule {}
```

`forRoot()` nhận một configuration object tùy chọn. Để cung cấp các tùy chọn một cách bất đồng bộ (ví dụ từ một configuration service), hãy dùng `CqrsModule.forRootAsync()` thay vào đó. Các tùy chọn sau có sẵn:

| Thuộc tính                    | Mô tả                                                                                                                        | Mặc định                          |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| `commandPublisher`            | Publisher chịu trách nhiệm dispatch command vào hệ thống.                                                                    | `DefaultCommandPubSub`            |
| `eventPublisher`              | Publisher dùng để publish event, cho phép chúng được broadcast hoặc xử lý.                                                   | `DefaultPubSub`                   |
| `queryPublisher`              | Publisher dùng để publish query, thứ có thể kích hoạt các thao tác lấy dữ liệu.                                              | `DefaultQueryPubSub`              |
| `unhandledExceptionPublisher` | Publisher dùng để publish các exception chưa được xử lý tới `UnhandledExceptionBus`.                                         | `DefaultUnhandledExceptionPubSub` |
| `eventIdProvider`             | Service lấy event ID duy nhất từ các instance event.                                                                         | `DefaultEventIdProvider`          |
| `rethrowUnhandled`            | Các exception do event handler và saga throw có được throw lại thay vì được publish tới `UnhandledExceptionBus` hay không.    | `false`                           |

#### Command <a id="commands"></a>

Command thay đổi trạng thái của ứng dụng. Chúng nên hướng theo tác vụ thay vì hướng theo dữ liệu. Khi một command được dispatch, nó được xử lý bởi một **command handler** tương ứng, handler này chịu trách nhiệm cập nhật trạng thái ứng dụng.

```typescript
@@filename(heroes-game.service)
@Injectable()
export class HeroesGameService {
  constructor(private commandBus: CommandBus) {}

  async killDragon(heroId: string, killDragonDto: KillDragonDto) {
    return this.commandBus.execute(
      new KillDragonCommand(heroId, killDragonDto.dragonId)
    );
  }
}
@@switch
@Injectable()
@Dependencies(CommandBus)
export class HeroesGameService {
  constructor(commandBus) {
    this.commandBus = commandBus;
  }

  async killDragon(heroId, killDragonDto) {
    return this.commandBus.execute(
      new KillDragonCommand(heroId, killDragonDto.dragonId)
    );
  }
}
```

Đoạn code ở trên khởi tạo class `KillDragonCommand` và truyền nó cho method `execute()` của `CommandBus`. Đây là class command:

```typescript
@@filename(kill-dragon.command)
export class KillDragonCommand extends Command<{
  actionId: string // This type represents the command execution result
}> {
  constructor(
    public readonly heroId: string,
    public readonly dragonId: string,
  ) {
    super();
  }
}
@@switch
export class KillDragonCommand extends Command {
  constructor(heroId, dragonId) {
    super();
    this.heroId = heroId;
    this.dragonId = dragonId;
  }
}
```

Class `KillDragonCommand` kế thừa class `Command`, một class tiện ích được export từ package `@nestjs/cqrs` cho phép bạn định nghĩa return type của command. Trong trường hợp này, return type là một object có thuộc tính `actionId`. Mỗi khi command `KillDragonCommand` được dispatch, return type của method `CommandBus#execute()` được suy ra là `Promise<{{ '{' }} actionId: string {{ '}' }}>`. Điều này hữu ích khi command handler trả dữ liệu về cho bên gọi.

> info **Gợi ý** Việc kế thừa class `Command` là tùy chọn. Bạn chỉ cần nó để định nghĩa return type của command.

`CommandBus` đại diện cho một **stream** command. Nó dispatch command tới các handler phù hợp. Method `execute()` trả về một promise resolve ra giá trị mà handler trả về.

Hãy tạo một handler cho command `KillDragonCommand`.

```typescript
@@filename(kill-dragon.handler)
@CommandHandler(KillDragonCommand)
export class KillDragonHandler implements ICommandHandler<KillDragonCommand> {
  constructor(private repository: HeroesRepository) {}

  async execute(command: KillDragonCommand) {
    const { heroId, dragonId } = command;
    const hero = this.repository.findOneById(+heroId);

    hero.killEnemy(dragonId);
    await this.repository.persist(hero);

    // "ICommandHandler<KillDragonCommand>" forces you to return a value that matches the command's return type
    return {
      actionId: crypto.randomUUID(), // This value will be returned to the caller
    }
  }
}
@@switch
@CommandHandler(KillDragonCommand)
@Dependencies(HeroesRepository)
export class KillDragonHandler {
  constructor(repository) {
    this.repository = repository;
  }

  async execute(command) {
    const { heroId, dragonId } = command;
    const hero = this.repository.findOneById(+heroId);

    hero.killEnemy(dragonId);
    await this.repository.persist(hero);

    // "ICommandHandler<KillDragonCommand>" forces you to return a value that matches the command's return type
    return {
      actionId: crypto.randomUUID(), // This value will be returned to the caller
    }
  }
}
```

Handler này lấy entity `Hero` từ repository, gọi method `killEnemy()` của nó, rồi lưu các thay đổi. Class `KillDragonHandler` implement interface `ICommandHandler`, interface này yêu cầu một method `execute()`. Method `execute()` nhận object command làm tham số.

`ICommandHandler<KillDragonCommand>` yêu cầu `execute()` trả về một giá trị khớp với return type của command (ở đây là một object có thuộc tính `actionId`). Điều này chỉ áp dụng cho các command kế thừa class `Command`. Với các command khác, return type không bị ràng buộc.

Cuối cùng, đăng ký `KillDragonHandler` làm provider trong một module:

```typescript
providers: [KillDragonHandler];
```

#### Query <a id="queries"></a>

Query lấy dữ liệu từ trạng thái của ứng dụng. Chúng nên hướng theo dữ liệu thay vì hướng theo tác vụ. Khi một query được dispatch, nó được xử lý bởi một **query handler** tương ứng, handler này chịu trách nhiệm lấy dữ liệu.

`QueryBus` theo cùng pattern với `CommandBus`. Query handler implement interface `IQueryHandler` và được chú thích bằng decorator `@QueryHandler()`. Bắt đầu với class query:

```typescript
export class GetHeroQuery extends Query<Hero> {
  constructor(public readonly heroId: string) {
    super();
  }
}
```

Giống như class `Command`, class `Query` là một class tiện ích được export từ package `@nestjs/cqrs` cho phép bạn định nghĩa return type của query. Trong trường hợp này, return type là một object `Hero`. Mỗi khi query `GetHeroQuery` được dispatch, return type của method `QueryBus#execute()` được suy ra là `Promise<Hero>`.

Để lấy hero, hãy tạo một query handler:

```typescript
@@filename(get-hero.handler)
@QueryHandler(GetHeroQuery)
export class GetHeroHandler implements IQueryHandler<GetHeroQuery> {
  constructor(private repository: HeroesRepository) {}

  async execute(query: GetHeroQuery) {
    return this.repository.findOneById(query.heroId);
  }
}
@@switch
@QueryHandler(GetHeroQuery)
@Dependencies(HeroesRepository)
export class GetHeroHandler {
  constructor(repository) {
    this.repository = repository;
  }

  async execute(query) {
    return this.repository.findOneById(query.heroId);
  }
}
```

Class `GetHeroHandler` implement interface `IQueryHandler`, interface này yêu cầu một method `execute()`. Method `execute()` nhận object query làm tham số và phải trả về dữ liệu khớp với return type của query (trong trường hợp này là một object `Hero`).

Cuối cùng, đăng ký `GetHeroHandler` làm provider trong một module:

```typescript
providers: [GetHeroHandler];
```

Để dispatch query, hãy dùng `QueryBus`:

```typescript
const hero = await this.queryBus.execute(new GetHeroQuery(heroId)); // "hero" will be auto-inferred as "Hero" type
```

#### Event <a id="events"></a>

Event thông báo cho các phần khác của ứng dụng về những thay đổi trong trạng thái ứng dụng. Chúng được dispatch bởi các **model** hoặc trực tiếp qua `EventBus`. Khi một event được dispatch, nó được xử lý bởi các **event handler** tương ứng, chẳng hạn để cập nhật read model.

Để minh họa, hãy tạo một class event:

```typescript
@@filename(hero-killed-dragon.event)
export class HeroKilledDragonEvent {
  constructor(
    public readonly heroId: string,
    public readonly dragonId: string,
  ) {}
}
@@switch
export class HeroKilledDragonEvent {
  constructor(heroId, dragonId) {
    this.heroId = heroId;
    this.dragonId = dragonId;
  }
}
```

Dù bạn có thể dispatch event trực tiếp bằng method `EventBus.publish()`, bạn cũng có thể dispatch chúng từ model. Hãy cập nhật model `Hero` để dispatch event `HeroKilledDragonEvent` khi method `killEnemy()` được gọi.

```typescript
@@filename(hero.model)
export class Hero extends AggregateRoot {
  constructor(private id: string) {
    super();
  }

  killEnemy(enemyId: string) {
    // Business logic
    this.apply(new HeroKilledDragonEvent(this.id, enemyId));
  }
}
@@switch
export class Hero extends AggregateRoot {
  constructor(id) {
    super();
    this.id = id;
  }

  killEnemy(enemyId) {
    // Business logic
    this.apply(new HeroKilledDragonEvent(this.id, enemyId));
  }
}
```

Method `apply()` dispatch event. Nó nhận một object event làm tham số. Tuy nhiên, model không biết gì về `EventBus`, nên bạn cần kết nối hai thứ này. Class `EventPublisher` làm việc đó:

```typescript
@@filename(kill-dragon.handler)
@CommandHandler(KillDragonCommand)
export class KillDragonHandler implements ICommandHandler<KillDragonCommand> {
  constructor(
    private repository: HeroesRepository,
    private publisher: EventPublisher,
  ) {}

  async execute(command: KillDragonCommand) {
    const { heroId, dragonId } = command;
    const hero = this.publisher.mergeObjectContext(
      await this.repository.findOneById(+heroId),
    );
    hero.killEnemy(dragonId);
    hero.commit();

    return {
      actionId: crypto.randomUUID(),
    };
  }
}
@@switch
@CommandHandler(KillDragonCommand)
@Dependencies(HeroesRepository, EventPublisher)
export class KillDragonHandler {
  constructor(repository, publisher) {
    this.repository = repository;
    this.publisher = publisher;
  }

  async execute(command) {
    const { heroId, dragonId } = command;
    const hero = this.publisher.mergeObjectContext(
      await this.repository.findOneById(+heroId),
    );
    hero.killEnemy(dragonId);
    hero.commit();

    return {
      actionId: crypto.randomUUID(),
    };
  }
}
```

Method `EventPublisher#mergeObjectContext` merge event publisher vào object được cung cấp. Object này phải implement interface `IAggregateRoot` (hoặc kế thừa class `AggregateRoot`). Khi đã merge, object có thể publish event vào event stream.

Các event được áp dụng bằng `apply()` được xếp hàng cho tới khi bạn gọi method `commit()` của model, method này dispatch mọi event còn tồn đọng. Để dispatch event ngay khi chúng được áp dụng, hãy đặt thuộc tính `autoCommit` thành `true`:

```typescript
export class Hero extends AggregateRoot {
  constructor(private id: string) {
    super();
    this.autoCommit = true;
  }
}
```

Để merge event publisher vào một class thay vì vào một object đã có, hãy dùng method `EventPublisher#mergeClassContext`:

```typescript
const HeroModel = this.publisher.mergeClassContext(Hero);
const hero = new HeroModel('id'); // <-- HeroModel is a class
```

Giờ mọi instance của class `HeroModel` đều có thể publish event mà không cần gọi method `mergeObjectContext()`.

Từ `@nestjs/cqrs` 12.1, `commit()`, `publish()` và `publishAll()` của một model trả về những gì event bus trả về, tức là bất cứ thứ gì event publisher trả về. Publisher trong bộ nhớ mặc định không trả về gì, vì nó không chờ các event handler. Với một publisher bất đồng bộ, chẳng hạn một publisher ghi vào message broker, `await hero.commit()` sẽ chờ nó và throw khi nó thất bại.

Cả ba cũng nhận một dispatcher context, thứ mà event publisher nhận thay cho model. Một command handler có thể truyền transaction của nó theo cách này, cho một publisher ghi qua transaction đó:

```typescript
await hero.commit({ transaction: tx });
```

`commit()` xóa các event của model ngay khi nó giao chúng cho event bus, mà không chờ publisher, nên gọi lại nó không bao giờ publish cùng các event hai lần. Nếu một `commit()` được await thất bại, hãy rollback và chạy lại command với một model vừa được load lại.

#### Aggregate Root linh hoạt <a id="flexible-aggregate-roots"></a>

Class `AggregateRoot` là một base class mà bạn có thể kế thừa để thêm khả năng hướng event cho domain model. Tuy nhiên, cách này yêu cầu các domain entity kế thừa trực tiếp `AggregateRoot`, điều có thể là một hạn chế nếu ứng dụng của bạn đã có một cây kế thừa entity sẵn (ví dụ một base class `Entity` hoặc các base class riêng của domain như `Monster` hay `Vehicle`).

Để linh hoạt hơn, package `@nestjs/cqrs` hỗ trợ ba cách hiện thực aggregate root:

**Cách 1: Truyền thống (Kế thừa class)**

Đây là cách tiêu chuẩn được trình bày trong các ví dụ trước. Nó hoạt động tốt cho các tình huống đơn giản và các project mới.

```typescript
export class Hero extends AggregateRoot {
  constructor(private id: string) {
    super();
  }

  killEnemy(enemyId: string) {
    this.apply(new HeroKilledDragonEvent(this.id, enemyId));
  }
}
```

**Cách 2: Mixin (Cho cây kế thừa đã có)**

Nếu bạn đã có một base class và không thể kế thừa trực tiếp `AggregateRoot`, hãy dùng hàm mixin `WithAggregateRoot<EventBase, TBase>()`. Nó áp dụng hành vi aggregate root cho bất kỳ base class nào đã có.

```typescript
@@filename(dragon.model)
abstract class Monster {
  constructor(protected readonly id: string) {}
  abstract roar(): void;
}

export class Dragon extends WithAggregateRoot(Monster) {
  roar(): void {
    console.log('Roarrrr!');
  }

  die(): void {
    this.roar();
    this.apply(new DragonDiedEvent(this.id)); // Provided by the mixin
  }
}
@@switch
class Monster {
  constructor(id) {
    this.id = id;
  }
}

export class Dragon extends WithAggregateRoot(Monster) {
  roar() {
    console.log('Roarrrr!');
  }

  die() {
    this.roar();
    this.apply(new DragonDiedEvent(this.id));
  }
}
```

**Cách 3: Tự hiện thực**

Để kiểm soát tối đa, hoặc để giữ lớp domain hoàn toàn không phụ thuộc framework, hãy implement trực tiếp interface `IAggregateRoot`:

```typescript
export class CustomEntity implements IAggregateRoot {
  autoCommit = false;
  private events: IEvent[] = [];

  getUncommittedEvents() {
    return this.events;
  }

  publish(event: IEvent, dispatcherContext?: unknown) {
    // custom logic
  }

  publishAll(events: IEvent[], dispatcherContext?: unknown) {
    // custom logic
  }

  commit(dispatcherContext?: unknown) {
    // custom logic, such as:
    // return this.publishAll(this.events.splice(0), dispatcherContext);
  }

  uncommit() {
    // custom logic
  }

  apply(event: IEvent) {
    this.events.push(event);
  }

  loadFromHistory(history: IEvent[]) {
    // custom logic
  }
}
```

Cả ba cách đều hoạt động với `EventPublisher`, thứ nhận bất kỳ object nào implement interface `IAggregateRoot`. Từ `@nestjs/cqrs` 12.1, `mergeObjectContext()` và `mergeClassContext()` cho model các method `publish()` và `publishAll()` truyền dispatcher context tiếp cho event bus và trả về kết quả của nó. Một `commit()` tùy chỉnh hỗ trợ dispatcher context bằng cách truyền nó tiếp cho `publishAll()`. Các tham số là tùy chọn: một phần hiện thực không có chúng, với các method không trả về gì, vẫn thỏa mãn interface.

#### Publish event thủ công <a id="manual-event-publishing"></a>

Để publish một event mà không đi qua model, hãy gọi trực tiếp method `EventBus#publish()`:

```typescript
this.eventBus.publish(new HeroKilledDragonEvent(heroId, dragonId));
```

> info **Gợi ý** `EventBus` là một class có thể inject.

Mỗi event có thể có nhiều **event handler**.

```typescript
@@filename(hero-killed-dragon.handler)
@EventsHandler(HeroKilledDragonEvent)
export class HeroKilledDragonHandler implements IEventHandler<HeroKilledDragonEvent> {
  constructor(private repository: HeroesRepository) {}

  handle(event: HeroKilledDragonEvent) {
    // Business logic
  }
}
```

> info **Gợi ý** Event handler chạy bên ngoài context HTTP request truyền thống:
>
> - Lỗi được throw trong command handler vẫn có thể được bắt bởi các [exception filter](/exception-filters) có sẵn.
> - Lỗi được throw trong event handler không thể được bắt bởi exception filter, nên bạn phải tự xử lý chúng: bằng một khối `try/catch`, bằng một [saga](/recipes/cqrs#sagas) kích hoạt một event bù trừ, hoặc bằng một cách khác tùy bạn chọn.
> - Giá trị mà một command handler trả về vẫn có thể được gửi lại cho client trong HTTP response.
> - Event handler không thể gửi HTTP response. Để gửi thông tin tới client, hãy dùng [WebSocket](/websockets/gateways), [server-sent event](/http/server-sent-events), hoặc một cơ chế khác.

Như với command và query, hãy đăng ký `HeroKilledDragonHandler` làm provider trong một module:

```typescript
providers: [HeroKilledDragonHandler];
```

#### Saga <a id="sagas"></a>

Một saga là một tiến trình kéo dài lắng nghe event và có thể kích hoạt command mới. Saga thường được dùng để quản lý các luồng công việc phức tạp. Ví dụ, khi một người dùng đăng ký, một saga có thể lắng nghe `UserRegisteredEvent` và gửi cho người dùng một email chào mừng.

Một saga có thể lắng nghe 1..\* event. Với library [RxJS](https://github.com/ReactiveX/rxjs), bạn có thể lọc, map, tách và gộp các event stream để xây dựng các luồng công việc tinh vi. Mỗi saga trả về một `Observable` phát ra các instance command. Mỗi command được phát ra sau đó được `CommandBus` dispatch một cách **bất đồng bộ**.

> info **Gợi ý** Saga chạy trong bộ nhớ. Với các tiến trình phải tồn tại qua các lần restart, xem [Durable saga](/recipes/cqrs#durable-sagas).

Hãy tạo một saga lắng nghe `HeroKilledDragonEvent` và dispatch command `DropAncientItemCommand`.

```typescript
@@filename(heroes-game.saga)
@Injectable()
export class HeroesGameSagas {
  @Saga()
  dragonKilled = (events$: Observable<any>): Observable<ICommand> => {
    return events$.pipe(
      ofType(HeroKilledDragonEvent),
      map((event) => new DropAncientItemCommand(event.heroId, fakeItemID)),
    );
  }
}
@@switch
@Injectable()
export class HeroesGameSagas {
  @Saga()
  dragonKilled = (events$) => {
    return events$.pipe(
      ofType(HeroKilledDragonEvent),
      map((event) => new DropAncientItemCommand(event.heroId, fakeItemID)),
    );
  }
}
```

> info **Gợi ý** Operator `ofType` và decorator `@Saga()` được export từ package `@nestjs/cqrs`.

Decorator `@Saga()` đánh dấu thuộc tính là một saga. Tham số `events$` là một stream `Observable` chứa mọi event. Operator `ofType` lọc stream theo loại event được chỉ định, và operator `map` ánh xạ mỗi event thành một instance command mới.

Trong ví dụ này, mỗi `HeroKilledDragonEvent` được ánh xạ thành một command `DropAncientItemCommand`, command này sau đó được `CommandBus` dispatch tự động.

Như với query, command và event handler, hãy đăng ký `HeroesGameSagas` làm provider trong một module:

```typescript
providers: [HeroesGameSagas];
```

#### Durable saga <a id="durable-sagas"></a>

Saga và event handler chạy trong bộ nhớ. Nếu process dừng giữa một event và command mà saga dispatch, command đó sẽ không bao giờ được dispatch. Một saga kết hợp nhiều event, chẳng hạn một saga chờ thanh toán sau khi đặt hàng và bỏ cuộc sau một giờ, sẽ mất các event mà nó đã thấy khi restart. Một event được publish ngay trước khi transaction đằng sau nó rollback vẫn tới được chúng.

Khi một tiến trình phải tồn tại qua các lần restart và deploy, hãy để các event khởi động và gửi signal cho một [durable workflow](/reliability/workflows) thay vào đó. Entry point `@nestjs/workflows/cqrs` ánh xạ event sang workflow, nên code của bạn vẫn tiếp tục thực thi command và publish event:

```bash
$ npm i --save @nestjs/workflows
```

```typescript
@@filename(app.module)
import { CqrsModule } from '@nestjs/cqrs';
import { WorkflowsModule } from '@nestjs/workflows';
import { WorkflowsCqrsModule } from '@nestjs/workflows/cqrs';

@Module({
  imports: [CqrsModule.forRoot(), WorkflowsModule.forRoot(), WorkflowsCqrsModule],
  providers: [PlaceOrderHandler, OrderFulfilmentWorkflow],
})
export class AppModule {}
```

Cho tới khi bạn đăng ký một store, `WorkflowsModule` giữ các workflow trong bộ nhớ. Trên PostgreSQL hoặc MySQL, hãy đăng ký `PostgresWorkflowStore` hoặc `MySqlWorkflowStore` của package làm provider, trên database client mà bạn đang dùng, như [Giữ workflow trong database của bạn](/reliability/workflows#keep-workflows-in-your-database) trình bày: khi đó các workflow nằm trong database của bạn, và việc khởi động cũng như gửi signal cho chúng có thể tham gia vào transaction của bạn.

`@StartOn()` khởi động workflow khi một event được publish, và `@SignalOn()` đánh thức instance đang chờ một event khác:

```typescript
@@filename(order-fulfilment.workflow)
@Workflow('order-fulfilment')
@StartOn(OrderPlacedEvent, {
  id: (event) => `order-${event.order.id}`,
  input: (event) => event.order,
})
@SignalOn(OrderDeliveredEvent, {
  signal: shipmentDelivered,
  key: (event) => event.delivery.reference,
})
export class OrderFulfilmentWorkflow implements WorkflowRunner<Order, FulfilmentResult> {
  constructor(private readonly commandBus: CommandBus) {}

  async run(ctx: WorkflowContext, order: Order): Promise<FulfilmentResult> {
    const charge = await ctx.step('charge-payment', ({ idempotencyKey }) =>
      this.commandBus.execute(new ChargePaymentCommand(order, idempotencyKey)),
    );

    const delivery = await ctx.waitForSignal('await-delivery', shipmentDelivered, {
      key: order.id,
      timeout: '3d',
    });
    // ...
  }
}
```

Command handler truyền transaction của nó làm tham số thứ hai của `publish()`, tức dispatcher context của CQRS. Khi đó workflow được tạo trong transaction đó, nên nó tồn tại khi và chỉ khi đơn hàng đã được lưu:

```typescript
@@filename(place-order.handler)
return this.db.transaction(async (tx) => {
  await tx.insert(orders).values(order);
  await this.eventBus.publish(new OrderPlacedEvent(order), { transaction: tx });
  return order;
});
```

Các event của một aggregate cũng đi theo cách tương tự. Từ `@nestjs/cqrs` 12.1, hãy truyền transaction cho `commit()` của aggregate trong cùng callback, và await nó: nó resolve khi các workflow đã được khởi động và gửi signal.

```typescript
await order.commit({ transaction: tx });
```

Trạng thái của workflow nằm trong database của bạn, nên nó tồn tại qua các lần restart và deploy. Một step đã hoàn tất không bao giờ chạy lại, và một step mà process chết giữa chừng sẽ chạy lại với cùng idempotency key, thứ mà command giao cho payment provider. Một event lặp lại sẽ tìm thấy instance mà event đầu tiên đã khởi động. Các event handler và saga của bạn vẫn nhận mọi event, sau các workflow. Xem [Durable workflow với CQRS](/reliability/workflows#with-cqrs) để biết đảm bảo của từng cách publish, và aggregate.

#### Exception chưa được xử lý <a id="unhandled-exceptions"></a>

Event handler được thực thi bất đồng bộ, nên chúng phải luôn xử lý exception đúng cách để ngăn ứng dụng rơi vào trạng thái không nhất quán. Nếu một exception không được xử lý, `EventBus` sẽ log nó, tạo một object `UnhandledExceptionInfo`, và đẩy nó vào stream `UnhandledExceptionBus`. Điều tương tự áp dụng cho các exception do saga throw và do các command handler đang thực thi command mà saga dispatch throw. `UnhandledExceptionBus` là một `Observable` mà bạn có thể subscribe để xử lý các exception chưa được xử lý. Nếu tùy chọn `rethrowUnhandled` được đặt thành `true`, các exception này được throw lại thay vì được publish tới `UnhandledExceptionBus`.

```typescript
private destroy$ = new Subject<void>();

constructor(private unhandledExceptionsBus: UnhandledExceptionBus) {
  this.unhandledExceptionsBus
    .pipe(takeUntil(this.destroy$))
    .subscribe((exceptionInfo) => {
      // Handle exception here
      // e.g. send it to external service, terminate process, or publish a new event
    });
}

onModuleDestroy() {
  this.destroy$.next();
  this.destroy$.complete();
}
```

Để chỉ xử lý các loại exception cụ thể, hãy dùng operator `UnhandledExceptionBus.ofType()`, operator này lọc exception bằng `instanceof`:

```typescript
this.unhandledExceptionsBus
  .pipe(
    takeUntil(this.destroy$),
    UnhandledExceptionBus.ofType(TransactionNotAllowedException),
  )
  .subscribe((exceptionInfo) => {
    // Handle exception here
  });
```

Ở đây, chỉ những exception là instance của `TransactionNotAllowedException` mới tới được subscriber.

Object `UnhandledExceptionInfo` chứa các thuộc tính sau:

```typescript
export interface UnhandledExceptionInfo<
  Cause = IEvent | ICommand,
  Exception = any,
> {
  /**
   * The exception that was thrown.
   */
  exception: Exception;
  /**
   * The cause of the exception (event or command reference).
   */
  cause: Cause;
}
```

#### Subscribe mọi event <a id="subscribing-to-all-events"></a>

`CommandBus`, `QueryBus` và `EventBus` đều là **Observable**. Điều này có nghĩa là bạn có thể subscribe toàn bộ stream và, chẳng hạn, xử lý mọi event: log chúng ra console hoặc lưu chúng vào một event store.

```typescript
private destroy$ = new Subject<void>();

constructor(private eventBus: EventBus) {
  this.eventBus
    .pipe(takeUntil(this.destroy$))
    .subscribe((event) => {
      // Save events to database
    });
}

onModuleDestroy() {
  this.destroy$.next();
  this.destroy$.complete();
}
```

#### Request-scoping

Nếu bạn đến từ các ngôn ngữ lập trình khác, có thể bạn sẽ ngạc nhiên rằng trong Nest, phần lớn mọi thứ được dùng chung giữa các request đi vào: một connection pool tới database, các singleton service có trạng thái global, và nhiều thứ khác. Node.js không theo mô hình stateless đa luồng request/response, trong đó mỗi request được xử lý bởi một thread riêng. Vì vậy, việc dùng singleton instance là **an toàn** cho ứng dụng của bạn.

Tuy nhiên, có những trường hợp đặc biệt mà vòng đời theo request cho một handler là điều mong muốn, như cache theo từng request trong ứng dụng GraphQL, theo dõi request, hoặc multi-tenancy. Xem chương [injection scope](/fundamentals/injection-scopes) để tìm hiểu cách kiểm soát scope.

Dùng các provider request-scoped cùng với CQRS có thể phức tạp vì `CommandBus`, `QueryBus` và `EventBus` là singleton. Package `@nestjs/cqrs` xử lý điều này bằng cách tự động tạo một instance mới của handler request-scoped cho mỗi command, query hoặc event được xử lý.

Để một handler trở thành request-scoped, hãy:

1. Phụ thuộc vào một provider request-scoped.
2. Hoặc đặt tường minh scope của nó thành `REQUEST` trong decorator `@CommandHandler()`, `@QueryHandler()` hoặc `@EventsHandler()`, như sau:

```typescript
@CommandHandler(KillDragonCommand, {
  scope: Scope.REQUEST,
})
export class KillDragonHandler {
  // Implementation here
}
```

Để inject request payload vào một provider request-scoped, hãy dùng decorator `@Inject(REQUEST)` (`REQUEST` được export từ `@nestjs/core`). Tuy nhiên trong CQRS, request payload phụ thuộc vào ngữ cảnh: nó có thể là một HTTP request, một scheduled job, hoặc bất kỳ thao tác nào khác kích hoạt một command.

Payload phải là một instance của `AsyncContext` (được export từ `@nestjs/cqrs`) hoặc của một class kế thừa nó. Nó đóng vai trò request context và chứa dữ liệu có thể truy cập trong suốt vòng đời của request.

```typescript
import { AsyncContext } from '@nestjs/cqrs';

export class MyRequest extends AsyncContext {
  constructor(public readonly user: User) {
    super();
  }
}
```

Khi thực thi một command, hãy truyền request context tùy chỉnh làm tham số thứ hai cho method `CommandBus#execute()`:

```typescript
const myRequest = new MyRequest(user);
await this.commandBus.execute(
  new KillDragonCommand(heroId, killDragonDto.dragonId),
  myRequest,
);
```

Điều này giúp instance `MyRequest` có sẵn dưới dạng provider `REQUEST` cho handler tương ứng:

```typescript
@CommandHandler(KillDragonCommand, {
  scope: Scope.REQUEST,
})
export class KillDragonHandler {
  constructor(
    @Inject(REQUEST) private request: MyRequest, // Inject the request context
  ) {}

  // Handler implementation here
}
```

Query hoạt động theo cùng cách:

```typescript
const myRequest = new MyRequest(user);
const hero = await this.queryBus.execute(new GetHeroQuery(heroId), myRequest);
```

Và trong query handler:

```typescript
@QueryHandler(GetHeroQuery, {
  scope: Scope.REQUEST,
})
export class GetHeroHandler {
  constructor(
    @Inject(REQUEST) private request: MyRequest, // Inject the request context
  ) {}

  // Handler implementation here
}
```

Với event, bạn có thể truyền request context cho `EventBus#publish()`, nhưng cách này ít phổ biến hơn. Thay vào đó, hãy dùng `EventPublisher` để merge request context vào một model:

```typescript
const hero = this.publisher.mergeObjectContext(
  await this.repository.findOneById(+heroId),
  this.request, // Inject the request context here
);
```

Các event handler request-scoped xử lý những event này sẽ truy cập được request context.

Saga luôn là singleton vì chúng quản lý các tiến trình kéo dài (đăng ký một saga trong một provider không phải singleton sẽ throw một exception). Tuy nhiên, bạn có thể lấy request context từ các object event:

```typescript
@Saga()
dragonKilled = (events$: Observable<any>): Observable<ICommand> => {
  return events$.pipe(
    ofType(HeroKilledDragonEvent),
    map((event) => {
      const request = AsyncContext.of(event); // Retrieve the request context
      const command = new DropAncientItemCommand(event.heroId, fakeItemID);

      AsyncContext.merge(request, command); // Merge the request context into the command
      return command;
    }),
  );
}
```

Ngoài ra, hãy gọi method `request.attachTo(command)` để gắn request context vào command.

#### Ví dụ <a id="example"></a>

Một ví dụ chạy được có trong [repository nest-cqrs-example](https://github.com/kamilmysliwiec/nest-cqrs-example).
