### Nest Commander

Mở rộng từ chương [ứng dụng standalone](/standalone-applications), package [nest-commander](https://nest-commander.jaymcdoniel.dev) cho phép bạn viết các ứng dụng dòng lệnh với cấu trúc tương tự một ứng dụng Nest thông thường.

> info **Lưu ý** `nest-commander` là một package bên thứ ba và không do team lõi NestJS quản lý. Hãy báo cáo mọi vấn đề với library trong [repository nest-commander](https://github.com/jmcdo29/nest-commander/issues/new/choose).

#### Cài đặt <a id="installation"></a>

Trước tiên, hãy cài package:

```bash
$ npm i nest-commander
```

#### Một file Command <a id="a-command-file"></a>

`nest-commander` cho phép bạn viết ứng dụng dòng lệnh bằng [decorator](https://www.typescriptlang.org/docs/handbook/decorators.html): decorator `@Command()` cho class và decorator `@Option()` cho các method của những class đó. Mỗi class command nên kế thừa abstract class `CommandRunner` và được gắn decorator `@Command()`.

Nest coi mọi command là một `@Injectable()`, nên dependency injection hoạt động như thường lệ. Abstract class `CommandRunner` đảm bảo mọi command đều có một method `run()` trả về `Promise<void>` và nhận các tham số `string[], Record<string, any>`. Method `run()` là nơi logic của command bắt đầu. Tham số đầu tiên của nó là một mảng mọi tham số không khớp với cờ tùy chọn nào, phòng khi bạn cần làm việc với nhiều tham số. Ở tham số thứ hai, options object, tên thuộc tính khớp với thuộc tính `name` được truyền cho các decorator `@Option()`, và giá trị của chúng là giá trị trả về của các option handler tương ứng. Để có type safety tốt hơn, bạn cũng có thể tạo một interface cho các tùy chọn.

#### Chạy Command <a id="running-the-command"></a>

Trong một ứng dụng NestJS, bạn dùng `NestFactory` để tạo server và chạy nó bằng `listen()`. Tương tự, package `nest-commander` cung cấp một API để chạy ứng dụng dòng lệnh: import `CommandFactory`, gọi static method `run()` của nó, và truyền vào root module của ứng dụng:

```ts
import { CommandFactory } from 'nest-commander';
import { AppModule } from './app.module.js';

async function bootstrap() {
  await CommandFactory.run(AppModule);
}

await bootstrap();
```

Mặc định, logger của Nest bị tắt khi dùng `CommandFactory`. Để bật nó, hãy truyền một logger làm tham số thứ hai cho method `run()`. Bạn có thể cung cấp một logger NestJS tùy chỉnh hoặc một mảng các log level mà bạn muốn giữ. Ví dụ, truyền `['error']` để chỉ in log lỗi của Nest.

```ts
import { CommandFactory } from 'nest-commander';
import { AppModule } from './app.module.js';
import { LogService } from './log.service.js';

async function bootstrap() {
  await CommandFactory.run(AppModule, new LogService());

  // or, if you only want to print Nest's warnings and errors
  await CommandFactory.run(AppModule, ['warn', 'error']);
}

await bootstrap();
```

Bên dưới, `CommandFactory` gọi `NestFactory` giúp bạn và gọi `app.close()` khi command kết thúc, nên bạn không phải lo về rò rỉ bộ nhớ. Để thêm xử lý lỗi, hãy bọc lời gọi `run()` trong một khối `try/catch`, hoặc nối một lời gọi `.catch()` vào lời gọi `bootstrap()`.

#### Testing

`nest-commander` cung cấp các tiện ích testing hòa hợp với phần còn lại của hệ sinh thái NestJS. Thay vì dùng `CommandFactory` để dựng command ở chế độ test, hãy dùng `CommandTestFactory` từ package `nest-commander-testing` và truyền vào metadata của module, tương tự cách `Test.createTestingModule()` từ `@nestjs/testing` hoạt động. Thực tế, nó dùng `@nestjs/testing` bên dưới. Bạn vẫn có thể nối các lời gọi `overrideProvider()` trước khi gọi `compile()` để thay các provider trong test.

#### Kết hợp tất cả lại <a id="putting-it-all-together"></a>

Class sau định nghĩa một CLI command có thể nhận subcommand `basic` hoặc được gọi trực tiếp. Nó hỗ trợ các cờ `-n`, `-s` và `-b` (cùng các dạng đầy đủ của chúng), với một parser tùy chỉnh cho mỗi tùy chọn. Cờ `--help` cũng được hỗ trợ, như thông lệ với commander.

```ts
import { Command, CommandRunner, Option } from 'nest-commander';
import { LogService } from './log.service.js';

interface BasicCommandOptions {
  string?: string;
  boolean?: boolean;
  number?: number;
}

@Command({ name: 'basic', description: 'A parameter parse' })
export class BasicCommand extends CommandRunner {
  constructor(private readonly logService: LogService) {
    super();
  }

  async run(
    passedParam: string[],
    options?: BasicCommandOptions,
  ): Promise<void> {
    if (options?.boolean !== undefined && options?.boolean !== null) {
      this.runWithBoolean(passedParam, options.boolean);
    } else if (options?.number) {
      this.runWithNumber(passedParam, options.number);
    } else if (options?.string) {
      this.runWithString(passedParam, options.string);
    } else {
      this.runWithNone(passedParam);
    }
  }

  @Option({
    flags: '-n, --number [number]',
    description: 'A basic number parser',
  })
  parseNumber(val: string): number {
    return Number(val);
  }

  @Option({
    flags: '-s, --string [string]',
    description: 'A string return',
  })
  parseString(val: string): string {
    return val;
  }

  @Option({
    flags: '-b, --boolean [boolean]',
    description: 'A boolean parser',
  })
  parseBoolean(val: string): boolean {
    return JSON.parse(val);
  }

  runWithString(param: string[], option: string): void {
    this.logService.log({ param, string: option });
  }

  runWithNumber(param: string[], option: number): void {
    this.logService.log({ param, number: option });
  }

  runWithBoolean(param: string[], option: boolean): void {
    this.logService.log({ param, boolean: option });
  }

  runWithNone(param: string[]): void {
    this.logService.log({ param });
  }
}
```

Hãy đảm bảo class command được thêm vào một module:

```ts
@Module({
  providers: [LogService, BasicCommand],
})
export class AppModule {}
```

Sau đó, để chạy CLI, hãy thêm đoạn sau vào file `main.ts`:

```ts
async function bootstrap() {
  await CommandFactory.run(AppModule);
}

await bootstrap();
```

Giờ bạn đã có một ứng dụng dòng lệnh.

#### Thông tin thêm <a id="more-information"></a>

Hãy truy cập [trang tài liệu nest-commander](https://nest-commander.jaymcdoniel.dev) để có thêm thông tin, ví dụ và tài liệu API.
