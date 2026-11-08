### Mã hóa và hashing

**Mã hóa** (encryption) là quá trình encode thông tin. Quá trình này chuyển dạng biểu diễn gốc của thông tin, gọi là plaintext, sang một dạng khác gọi là ciphertext. Lý tưởng nhất là chỉ những bên được phép mới giải mã được ciphertext về lại plaintext và truy cập thông tin gốc. Bản thân mã hóa không ngăn được việc can thiệp, nhưng nó khiến kẻ muốn chặn bắt không đọc hiểu được nội dung. Mã hóa là một hàm hai chiều: thứ gì đã được mã hóa thì có thể giải mã bằng key phù hợp.

**Hashing** là quá trình chuyển một key đã cho thành một giá trị khác. Một hàm hash tạo ra giá trị mới theo một thuật toán toán học. Một khi giá trị đã được hash, lẽ ra không thể nào đi ngược từ output về input.

#### Mã hóa <a id="encryption"></a>

Node.js cung cấp sẵn [module crypto](https://nodejs.org/api/crypto.html) mà bạn có thể dùng để mã hóa và giải mã chuỗi, số, buffer, stream, v.v. Nest không cung cấp thêm package nào bọc ngoài module này, để tránh tạo ra những lớp trừu tượng không cần thiết.

Để làm ví dụ, hãy dùng thuật toán AES (Advanced Encryption Standard) `'aes-256-ctr'`, thuật toán này dùng chế độ mã hóa CTR.

```typescript
import { createCipheriv, randomBytes, scrypt } from 'node:crypto';
import { promisify } from 'node:util';

const iv = randomBytes(16);
const password = 'Password used to generate key';

// The key length is dependent on the algorithm.
// In this case for aes256, it is 32 bytes.
const key = (await promisify(scrypt)(password, 'salt', 32)) as Buffer;
const cipher = createCipheriv('aes-256-ctr', key, iv);

const textToEncrypt = 'Nest';
const encryptedText = Buffer.concat([
  cipher.update(textToEncrypt),
  cipher.final(),
]);
```

Để giải mã giá trị `encryptedText`:

```typescript
import { createDecipheriv } from 'node:crypto';

const decipher = createDecipheriv('aes-256-ctr', key, iv);
const decryptedText = Buffer.concat([
  decipher.update(encryptedText),
  decipher.final(),
]);
```

#### Hashing

Để hash mật khẩu, hãy dùng `PasswordHasher` từ [`@nestjs/authentication`](/security/authentication). Nó hash bằng scrypt từ `node:crypto`, với các tham số mà OWASP khuyến nghị (N=2^17, r=8, p=1: khoảng 128 MiB bộ nhớ cho mỗi lần hash), trên thread pool của libuv, nên không làm nghẽn event loop và không cần dependency native nào. scrypt là hàm memory-hard, khiến việc đoán mật khẩu trên GPU tốn kém hơn nhiều so với bcrypt.

Khi ứng dụng của bạn import `AuthenticationModule`, `PasswordHasher` là một provider, nên hãy inject nó ở nơi bạn lưu và kiểm tra mật khẩu:

```typescript
import { Injectable } from '@nestjs/common';
import { PasswordHasher } from '@nestjs/authentication';

@Injectable()
export class CredentialsService {
  constructor(private readonly passwordHasher: PasswordHasher) {}

  async hashPassword(password: string) {
    return this.passwordHasher.hash(password);
  }

  async checkPassword(password: string, storedHash: string | undefined) {
    return this.passwordHasher.verify(password, storedHash);
  }
}
```

- `hash()` trả về một chuỗi tự mô tả, như `$scrypt$ln=17,r=8,p=1$<salt>$<hash>`: các tham số và một salt ngẫu nhiên được lưu cùng hash, nên không cần giữ thêm gì khác.
- `verify()` so sánh trong thời gian không đổi. Hãy truyền `undefined` cho người dùng không tồn tại: nó sẽ kiểm tra một hash giả thay vào đó, để thời gian phản hồi không để lộ tài khoản nào tồn tại.
- Mật khẩu được chuẩn hóa Unicode (NFKC) trước khi hash, nên cùng một mật khẩu gõ trên các bàn phím khác nhau vẫn xác minh được.
- `hash()` từ chối mật khẩu rỗng và mật khẩu vượt quá 4 KiB bằng một `RangeError`, còn `verify()` trả lời `false` cho chúng mà không hash. Mọi quy tắc khác, như độ dài tối thiểu, là việc bạn phải tự kiểm tra trước.
- `needsRehash()` cho bạn biết một hash đã lưu được tạo với các tham số yếu hơn tham số hiện tại. Hãy kiểm tra nó sau một lần `verify()` thành công, và lưu hash mới trong lúc bạn còn có plaintext:

```typescript
if (this.passwordHasher.needsRehash(storedHash)) {
  await this.usersRepository.updatePasswordHash(user.id, await this.passwordHasher.hash(password));
}
```

Chi phí lấy từ tùy chọn `password` của module: đặt `logN` của nó thành 18 để tăng gấp đôi. Nó có mức trần là 1 GiB bộ nhớ và gấp 16 lần khối lượng công việc mặc định cho mỗi lần hash, nên với `r` mặc định là 8, `logN` dừng ở 20; các tham số vượt quá mức đó sẽ throw khi tạo hasher, và một hash đã lưu được tạo với chúng sẽ không bao giờ xác minh được. Bên ngoài module, hãy tự tạo một instance bằng `new PasswordHasher()`. Trong test, một instance rẻ hơn giúp test suite chạy nhanh, với `logN` đặt là 10.

> info **Gợi ý** Nếu bạn thích dùng argon2 hoặc bcrypt hơn, các package [argon2](https://www.npmjs.com/package/argon2) và [bcrypt](https://www.npmjs.com/package/bcrypt) dùng được ngay với Nest: hãy gọi các hàm `hash()` và `verify()` (argon2) hoặc `compare()` (bcrypt) của chúng từ provider của riêng bạn. Cả hai đều là native module, và bcrypt chỉ đọc 72 byte đầu tiên của mật khẩu.
