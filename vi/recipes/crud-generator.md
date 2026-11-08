### CRUD generator (chỉ TypeScript)

Trong suốt vòng đời của một project, việc xây dựng tính năng mới thường đồng nghĩa với việc thêm resource mới vào ứng dụng. Mỗi resource mới thường đòi hỏi cùng một tập thao tác lặp đi lặp lại.

#### Giới thiệu <a id="introduction"></a>

Xét một tình huống thực tế trong đó bạn cần đưa ra các endpoint CRUD cho hai entity, **User** và **Product**. Theo best practice, bạn sẽ phải thực hiện vài thao tác cho mỗi entity:

- Sinh một module (`nest g mo`) để giữ code có tổ chức và thiết lập ranh giới rõ ràng (gom các thành phần liên quan)
- Sinh một controller (`nest g co`) để định nghĩa các route CRUD (hoặc query/mutation cho ứng dụng GraphQL)
- Sinh một service (`nest g s`) để hiện thực và cô lập logic nghiệp vụ
- Sinh một class/interface entity để biểu diễn cấu trúc dữ liệu của resource
- Sinh các Data Transfer Object (hoặc input cho ứng dụng GraphQL) để định nghĩa cách dữ liệu được gửi qua mạng

Để tăng tốc quá trình lặp đi lặp lại này, [Nest CLI](/cli/overview) cung cấp một generator (schematic) tự động sinh toàn bộ code boilerplate này.

> info **Lưu ý** Schematic hỗ trợ sinh controller **HTTP**, controller **Microservice**, resolver **GraphQL** (cả code first lẫn schema first), và Gateway **WebSocket**.

#### Sinh một resource mới <a id="generating-a-new-resource"></a>

Để tạo một resource mới, hãy chạy lệnh sau ở thư mục gốc của project:

```shell
$ nest g resource
```

Lệnh `nest g resource` không chỉ sinh các building block của NestJS (các class module, service và controller), mà còn sinh một class entity, các class DTO, và các file test (`.spec`).

Đây là file controller được sinh ra (cho một REST API):

```typescript
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Post()
  create(@Body() createUserDto: CreateUserDto) {
    return this.usersService.create(createUserDto);
  }

  @Get()
  findAll() {
    return this.usersService.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.usersService.findOne(+id);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() updateUserDto: UpdateUserDto) {
    return this.usersService.update(+id, updateUserDto);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return this.usersService.remove(+id);
  }
}
```

Lệnh này cũng tạo các placeholder cho mọi endpoint CRUD: route cho REST API, query và mutation cho GraphQL, và message handler cho cả microservice lẫn WebSocket gateway.

> info **Lưu ý** Các class service được sinh ra **không** gắn với bất kỳ **ORM (hay nguồn dữ liệu)** cụ thể nào, điều này giúp generator đủ tổng quát để đáp ứng nhu cầu của mọi project. Mặc định, mọi method đều chứa placeholder mà bạn có thể điền bằng các nguồn dữ liệu riêng của project.

Tương tự, để sinh resolver cho một ứng dụng GraphQL, hãy chọn `GraphQL (code first)` (hoặc `GraphQL (schema first)`) làm lớp transport.

Trong trường hợp này, Nest sinh một class resolver thay vì một controller REST API:

```shell
$ nest g resource users

> ? What transport layer do you use? GraphQL (code first)
> ? Would you like to generate CRUD entry points? Yes
> CREATE src/users/users.module.ts (224 bytes)
> CREATE src/users/users.resolver.spec.ts (525 bytes)
> CREATE src/users/users.resolver.ts (1109 bytes)
> CREATE src/users/users.service.spec.ts (453 bytes)
> CREATE src/users/users.service.ts (625 bytes)
> CREATE src/users/dto/create-user.input.ts (195 bytes)
> CREATE src/users/dto/update-user.input.ts (281 bytes)
> CREATE src/users/entities/user.entity.ts (187 bytes)
> UPDATE src/app.module.ts (312 bytes)
```

> info **Gợi ý** Để bỏ qua việc sinh file test, hãy truyền cờ `--no-spec`, như sau: `nest g resource users --no-spec`.

Như bên dưới, lệnh này không chỉ tạo mọi mutation và query boilerplate, mà còn nối mọi thứ lại với nhau, dùng `UsersService`, entity `User` và các DTO.

```typescript
import { Resolver, Query, Mutation, Args, Int } from '@nestjs/graphql';
import { UsersService } from './users.service.js';
import { User } from './entities/user.entity.js';
import { CreateUserInput } from './dto/create-user.input.js';
import { UpdateUserInput } from './dto/update-user.input.js';

@Resolver(() => User)
export class UsersResolver {
  constructor(private readonly usersService: UsersService) {}

  @Mutation(() => User)
  createUser(@Args('createUserInput') createUserInput: CreateUserInput) {
    return this.usersService.create(createUserInput);
  }

  @Query(() => [User], { name: 'users' })
  findAll() {
    return this.usersService.findAll();
  }

  @Query(() => User, { name: 'user' })
  findOne(@Args('id', { type: () => Int }) id: number) {
    return this.usersService.findOne(id);
  }

  @Mutation(() => User)
  updateUser(@Args('updateUserInput') updateUserInput: UpdateUserInput) {
    return this.usersService.update(updateUserInput.id, updateUserInput);
  }

  @Mutation(() => User)
  removeUser(@Args('id', { type: () => Int }) id: number) {
    return this.usersService.remove(id);
  }
}
```
