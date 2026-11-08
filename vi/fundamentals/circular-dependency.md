### Circular dependency

Circular dependency xảy ra khi hai class phụ thuộc lẫn nhau. Ví dụ, class A cần class B, và class B cũng cần class A. Trong Nest, circular dependency có thể xuất hiện giữa các module và giữa các provider.

Hãy tránh circular dependency khi có thể, nhưng không phải lúc nào cũng tránh được. Trong những trường hợp đó, Nest cho phép bạn giải quyết circular dependency giữa các provider theo hai cách: dùng **forward reference**, hoặc dùng class **ModuleRef** để lấy instance provider từ DI container. Chương này mô tả cả hai kỹ thuật, cũng như cách giải quyết circular dependency giữa các module.

> warning **Cảnh báo** Circular dependency cũng có thể phát sinh do dùng "barrel file" (các file `index.ts`) để gom import. Hãy tránh dùng barrel file cho các class module và provider. Đặc biệt, đừng dùng barrel file để import các file nằm cùng thư mục với barrel file, ví dụ `cats/cats.controller` không nên import `cats` để lấy file `cats/cats.service`. Để biết thêm chi tiết, xem [issue GitHub này về barrel file và circular dependency](https://github.com/nestjs/nest/issues/1181#issuecomment-430197191).

#### Forward reference

**Forward reference**, tạo bằng hàm tiện ích `forwardRef()`, cho phép Nest tham chiếu tới các class chưa được định nghĩa. Ví dụ, nếu `CatsService` và `CommonService` phụ thuộc lẫn nhau, cả hai phía của mối quan hệ có thể dùng `@Inject()` và tiện ích `forwardRef()` để giải quyết circular dependency. Nếu không, Nest sẽ không khởi tạo chúng, vì không phải mọi metadata cần thiết đều có sẵn. Đây là ví dụ:

```typescript
@@filename(cats.service)
@Injectable()
export class CatsService {
  constructor(
    @Inject(forwardRef(() => CommonService))
    private commonService: CommonService,
  ) {}
}
@@switch
@Injectable()
@Dependencies(forwardRef(() => CommonService))
export class CatsService {
  constructor(commonService) {
    this.commonService = commonService;
  }
}
```

> info **Gợi ý** Hàm `forwardRef()` được import từ package `@nestjs/common`.

Vậy là xong một phía của mối quan hệ. Giờ làm tương tự với `CommonService`:

```typescript
@@filename(common.service)
@Injectable()
export class CommonService {
  constructor(
    @Inject(forwardRef(() => CatsService))
    private catsService: CatsService,
  ) {}
}
@@switch
@Injectable()
@Dependencies(forwardRef(() => CatsService))
export class CommonService {
  constructor(catsService) {
    this.catsService = catsService;
  }
}
```

> warning **Cảnh báo** Thứ tự khởi tạo là không xác định. Hãy đảm bảo code của bạn không phụ thuộc vào việc constructor nào được gọi trước. Circular dependency phụ thuộc vào provider có `Scope.REQUEST` có thể dẫn tới dependency bị undefined. Xem [issue GitHub này về circular dependency với request scope](https://github.com/nestjs/nest/issues/5778) để biết thêm thông tin.

#### Dùng class ModuleRef thay thế <a id="moduleref-class-alternative"></a>

Một cách thay thế cho `forwardRef()` là refactor code và dùng class `ModuleRef` để lấy provider ở một phía của mối quan hệ (lẽ ra là) vòng tròn. Tìm hiểu thêm về class tiện ích `ModuleRef` trong chương [module reference](/fundamentals/module-ref).

#### Forward reference cho module <a id="module-forward-reference"></a>

Để giải quyết circular dependency giữa các module, dùng cùng hàm tiện ích `forwardRef()` ở cả hai phía của mối liên kết module. Ví dụ:

```typescript
@@filename(common.module)
@Module({
  imports: [forwardRef(() => CatsModule)],
})
export class CommonModule {}
```

Vậy là xong một phía của mối quan hệ. Giờ làm tương tự với `CatsModule`:

```typescript
@@filename(cats.module)
@Module({
  imports: [forwardRef(() => CommonModule)],
})
export class CatsModule {}
```
