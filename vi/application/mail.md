### Mail

`@nestjs/mail` gửi email từ một ứng dụng Nest: các mail class được render từ template HTML có escape, gửi qua SMTP hoặc một email API, và đọc lại được trong test.

Khi một khách hàng đặt hàng ở cửa hàng online bán thức ăn và đồ dùng cho mèo, họ mong nhận được email xác nhận trong vòng một phút: danh sách sản phẩm, tổng tiền, link tới đơn hàng, và hóa đơn dạng PDF. Gửi email đó cho tử tế cần nhiều hơn một lời gọi tới library SMTP:

- **HTML phải an toàn.** Tên sản phẩm hay tên khách hàng sẽ nằm trong markup. Nếu không escape, một cái tên như `<script>` hay một dấu `&` lạc chỗ sẽ làm vỡ layout, hoặc tệ hơn.
- **Mail phải sống sót qua sự cố.** Mail server có thể greylist, giới hạn tốc độ và sập. Một lần gửi thất bại ngay trong request hoặc sẽ làm thất bại một đơn hàng đã commit, hoặc làm mất email.
- **Test phải thấy được những gì đã gửi.** Một bài test cho "khách hàng nhận được xác nhận kèm link tới đơn hàng" cần mail đã render và các link trong đó, chứ không phải một lời gọi method bị mock.

`@nestjs/mail` đáp ứng những yêu cầu này. Mail class là các provider có thể inject, render subject và body từ dữ liệu có type, nên chúng có thể inject các provider khác của bạn, như repository hay bộ render PDF. Body lấy từ một file template HTML, được render bởi một engine nhỏ có sẵn (escape mọi giá trị nó chèn vào), hoặc bởi Handlebars hay bất kỳ engine nào bạn cắm vào. Transport lo việc gửi kết quả đi: SMTP, viết trên `node:net` và `node:tls`, và Resend, Postmark, SendGrid, Amazon SES qua HTTP API của chúng. Trong test, transport được thay bằng một transport trong bộ nhớ và đọc lại các mail mà nó nhận được. Package không có dependency nào ngoài chính Nest.

Trong bài hướng dẫn này, bạn sẽ thêm email xác nhận đơn hàng vào API đơn hàng của cửa hàng:

- Ở môi trường development, mọi mail được ghi ra file `.eml` thay vì gửi đi.
- Xác nhận đơn hàng là một mail class render một template HTML, nằm trong một layout mà mọi mail dùng chung, đính kèm hóa đơn và logo dạng inline.
- Một route preview hiển thị mail trên trình duyệt mà không gửi đi.
- Mail được gửi sau khi đơn hàng commit, qua outbox, có retry và dead letter.
- Production gửi qua SMTP hoặc Resend, chọn bằng một biến môi trường.

#### Cài đặt <a id="installation"></a>

Để bắt đầu, cài dependency cần thiết:

```bash
$ npm i --save @nestjs/mail
```

#### Đăng ký mail module <a id="register-the-mail-module"></a>

Đăng ký `MailModule` trong root module, cạnh `DrizzleModule`. Bài hướng dẫn mail cần database cho khách hàng và đơn hàng của họ, cũng như cho các bảng của outbox, nơi mail được [gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits). Ở môi trường development, `FileMailTransport` ghi mỗi mail ra một file trong `var/mail` thay vì gửi đi, còn `FileTemplateEngine` render body của mail từ các file HTML trong `mail/templates`. Các feature module mà nó import được xây dựng trong các phần tiếp theo:

```typescript
@@filename(app.module)
import { Module } from '@nestjs/common';
import { DrizzleModule } from '@nestjs/drizzle';
import { FileMailTransport, FileTemplateEngine, MailModule } from '@nestjs/mail';
import { drizzle } from 'drizzle-orm/node-postgres';
import { join } from 'node:path';
import * as schema from './database/schema.js';
import { NotificationsModule } from './notifications/notifications.module.js';
import { OrdersModule } from './orders/orders.module.js';

@Module({
  imports: [
    DrizzleModule.forRootAsync({
      // A pg pool on DATABASE_URL: the customers and orders, and the outbox's tables
      useFactory: () => ({ drizzle, connection: process.env.DATABASE_URL!, schema }),
    }),
    MailModule.forRoot({
      // Development: every mail becomes an .eml file in var/mail instead of leaving the machine
      transport: new FileMailTransport({ directory: 'var/mail' }),
      // Mail bodies are HTML files in mail/templates, wrapped in mail/templates/layout.html
      templates: new FileTemplateEngine({
        dir: join(import.meta.dirname, 'mail/templates'),
        layout: 'layout',
        // Development reads the files for every mail, so edits show up without a restart
        cache: process.env.NODE_ENV === 'production',
      }),
      from: 'Orders <orders@example.com>',
    }),
    OrdersModule,
    NotificationsModule,
  ],
})
export class AppModule {}
```

- `transport`: cách mail rời khỏi ứng dụng. Mọi transport đều kế thừa abstract class `MailTransport`, class này cũng chính là injection token của nó, nên trong test bạn thay nó bằng `overrideProvider(MailTransport)`. `FileMailTransport` dành cho development: mở các file `.eml` trong bất kỳ mail client nào để thấy chính xác những gì sẽ được gửi. Nó ghi ra ổ đĩa local và không gửi tới ai cả, nên [trên production](/application/mail#send-in-production) ứng dụng chuyển sang SMTP hoặc Resend.
- `templates`: render các mail có chỉ định template. `FileTemplateEngine` đọc các file `.html` từ `dir`, và bọc mọi mail trong template `layout`, tức `mail/templates/layout.html`. Một `dir` tương đối được resolve theo thư mục làm việc; nếu tạo từ `import.meta.dirname`, nó trỏ tới chỗ cạnh file `app.module.js` đã compile, bất kể ứng dụng được khởi động từ đâu. Template đã compile được cache lại. Khi tắt `cache`, như ở đây với môi trường không phải production, mỗi mail sẽ đọc lại file, nên template vừa sửa sẽ xuất hiện ngay ở mail tiếp theo mà không cần khởi động lại.
- `from`: người gửi mặc định. Mỗi message có thể ghi đè nó.

Trình biên dịch TypeScript không copy file HTML sang `dist`. Hãy thêm các template vào [asset](/cli/monorepo#assets) trong `nest-cli.json`, để chúng nằm ở `dist/mail/templates`, cạnh file `app.module.js` đã compile:

```json
{
  "compilerOptions": {
    "assets": ["mail/templates/**/*"],
    "watchAssets": true
  }
}
```

Với `watchAssets`, `nest start --watch` sẽ copy template sang `dist` mỗi khi bạn lưu nó.

> info **Gợi ý** Bài hướng dẫn đọc trực tiếp `process.env` cho ngắn gọn. Trong một ứng dụng thực tế, hãy load môi trường qua [`@nestjs/config`](/application/configuration) với một validation schema, để việc thiếu `DATABASE_URL` hay `SMTP_URL` làm ứng dụng dừng ngay lúc khởi động, và đọc giá trị từ `ConfigService` trong các factory.

`MailModule` là global và cung cấp `Mailer` để gửi mail, cùng `MailEvents` để báo cáo những gì đã gửi và những gì thất bại. Thiếu `transport` hoặc `from` không hợp lệ sẽ làm ứng dụng dừng lúc khởi động, kèm thông báo nêu tên tùy chọn.

#### Viết mail xác nhận đơn hàng <a id="write-the-order-confirmation-mail"></a>

Body của mail là một template HTML. Giá trị được đặt giữa cặp ngoặc nhọn đôi, và một block như `#each` lặp lại phần template của nó cho mỗi phần tử trong danh sách:

```html
@@filename(mail/templates/order-confirmation.html)
<p>Hi {{ '{' }}{{ '{' }} customer.name {{ '}' }}{{ '}' }},</p>
<p>thank you for your order! We are packing it now.</p>
<table>
  <tr><th>Product</th><th>Qty</th><th>Price</th></tr>
  {{ '{' }}{{ '{' }}#each items{{ '}' }}{{ '}' }}
  <tr>
    <td>{{ '{' }}{{ '{' }} name {{ '}' }}{{ '}' }}</td>
    <td>{{ '{' }}{{ '{' }} quantity {{ '}' }}{{ '}' }}</td>
    <td>{{ '{' }}{{ '{' }} price {{ '}' }}{{ '}' }}</td>
  </tr>
  {{ '{' }}{{ '{' }}/each{{ '}' }}{{ '}' }}
</table>
<p><strong>Total: {{ '{' }}{{ '{' }} total {{ '}' }}{{ '}' }}</strong></p>
<p><a href="{{ '{' }}{{ '{' }} orderUrl {{ '}' }}{{ '}' }}">View your order</a></p>
```

Mọi mail đều được bọc trong layout. Layout đặt mail đã render vào bằng ngoặc nhọn ba quanh `body`, và chèn chữ ký, một partial nằm trong `mail/templates/partials/signature.html`:

```html
@@filename(mail/templates/layout.html)
<!DOCTYPE html>
<html>
<body>
{{ '{' }}{{ '{' }}{{ '{' }} body {{ '}' }}{{ '}' }}{{ '}' }}
{{ '{' }}{{ '{' }}> signature{{ '}' }}{{ '}' }}
</body>
</html>
```

```html
@@filename(mail/templates/partials/signature.html)
<p>The customer care team</p>
```

Một mail class implement `Mailable<TData>`. Method `render()` của nó nhận dữ liệu và trả về subject, tên template và context của template, tức các giá trị mà template đọc:

```typescript
@@filename(notifications/order-confirmation.mail)
import { Injectable } from '@nestjs/common';
import type { Mailable } from '@nestjs/mail';
import type { Customer } from '../customers/customers.repository.js';
import type { Order } from '../orders/order.js';

export interface OrderConfirmation {
  order: Order;
  customer: Customer;
}

const SHOP_URL = process.env.SHOP_URL ?? 'https://shop.example.com';

@Injectable()
export class OrderConfirmationMail implements Mailable<OrderConfirmation> {
  render({ order, customer }: OrderConfirmation) {
    const price = (cents: number) => `$${(cents / 100).toFixed(2)}`;
    return {
      subject: `Your order #${order.number}`,
      // mail/templates/order-confirmation.html, wrapped in the layout
      template: 'order-confirmation',
      // The values the template shows, ready to insert: prices formatted, the link built
      context: {
        customer,
        items: order.items.map((item) => ({
          name: item.name,
          quantity: item.quantity,
          price: price(item.price * item.quantity),
        })),
        total: price(order.total),
        orderUrl: `${SHOP_URL}/orders/${order.id}`,
      },
    };
  }
}
```

Template không chứa logic. Nó có giá trị, các block `#if`, `#unless` và `#each`, partial và comment, nhưng không có helper hay biểu thức: những gì cần code, như định dạng giá hay tạo link, được làm trong mail class, bằng TypeScript, nơi chúng có type và được test. Cú pháp là một tập con của Handlebars (xem [Cú pháp template](/application/mail#template-syntax)), nên các template chuyển được sang [engine khác](/application/mail#use-another-template-engine) mà không cần sửa.

Ngoặc nhọn đôi sẽ escape giá trị. Một sản phẩm tên `Feather wand toy <limited edition>` sẽ trở thành `Feather wand toy &lt;limited edition&gt;`, và tên khách hàng không thể chèn markup vào. Hai quy tắc khiến việc này khó mà làm sai:

- Escape bảo vệ được nội dung phần tử và giá trị thuộc tính có dấu nháy, nên đó là những chỗ duy nhất mà giá trị trong ngoặc nhọn đôi được phép đặt. Một giá trị nằm bên trong thẻ ở bất kỳ chỗ nào khác là lỗi compile: `href=` theo sau trực tiếp là giá trị, hoặc một giá trị đứng giữa các thuộc tính. Escape không bảo vệ được cả hai chỗ đó (nếu không có dấu nháy, một dấu cách trong giá trị sẽ mở ra một thuộc tính mới). Hãy đặt giá trị thuộc tính trong dấu nháy, như link ở trên.
- Ngoặc nhọn ba chèn giá trị nguyên vẹn, dành cho HTML do chính bạn tạo ra. Trong bài hướng dẫn này, chỉ `body` của layout cần đến nó.

Một giá trị bị thiếu sẽ render ra rỗng, giống như Handlebars. Bên trong `#each`, `this` là phần tử hiện tại, `@index`, `@first` và `@last` mô tả vị trí của nó, và một tên mà phần tử không có sẽ được tra trong context của template, nên một dòng có thể hiển thị giá trị từ bên ngoài danh sách. Một template không compile được sẽ làm mail thất bại với một `MailTemplateError` vĩnh viễn, lỗi này nêu tên file và vị trí:

```text
order-confirmation.html:5:3: {{ '{' }}{{ '{' }}#each items{{ '}' }}{{ '}' }} is never closed (expected {{ '{' }}{{ '{' }}/each{{ '}' }}{{ '}' }})
```

Không có template dạng text. Mailer tự suy ra phần plain text từ HTML: các đoạn văn, các dòng của bảng, và link dưới dạng `View your order (https://shop.example.com/orders/…)`. Các mail client không hiển thị HTML, và bộ lọc spam, sẽ đọc phần này. Để tự viết nó, hãy thêm `order-confirmation.txt` cạnh file HTML: engine sẽ render nó làm phần text, với cùng cú pháp, không escape.

Đăng ký class làm provider, giống như mọi injectable khác:

```typescript
@@filename(notifications/notifications.module)
import { Module } from '@nestjs/common';
import { OrderConfirmationMail } from './order-confirmation.mail.js';

@Module({
  providers: [OrderConfirmationMail],
})
export class NotificationsModule {}
```

Sau đó gửi nó khi có đơn hàng được đặt. `mailer.send()` nhận mail class và người nhận, còn type của `data` lấy từ `render()` của class:

```typescript
@@filename(orders/orders.service)
async placeOrder({ customerId, items }: PlaceOrderDto): Promise<Order> {
  const customer = await this.customersRepository.findById(customerId);
  if (!customer) {
    throw new BadRequestException(`Unknown customer "${customerId}"`);
  }
  if (!items?.length) {
    throw new BadRequestException('An order needs at least one item');
  }

  const order = await this.db.transaction((tx) => this.insertOrder(tx, customerId, items));

  // After the commit: never inside the transaction, which would stay open, holding its
  // connection and locks, for as long as the mail server takes to answer
  await this.mailer.send(OrderConfirmationMail, {
    to: { name: customer.name, address: customer.email },
    data: { order, customer },
  });
  return order;
}
```

Người nhận là một object có `name` và `address`, nên một cái tên có dấu phẩy hoặc dấu nháy vẫn là một display name duy nhất. Một chuỗi cũng dùng được, như `'Ada Lovelace <ada@example.com>'`, nhưng chuỗi phải chứa đúng một địa chỉ: một danh sách phân cách bằng dấu phẩy sẽ gây throw, nên một cái tên do người dùng gõ vào không bao giờ thêm được người nhận. Danh sách người nhận là mảng.

Đặt một đơn hàng và một file sẽ xuất hiện trong `var/mail`. Cách này chạy được, nhưng nó gửi mail từ request, sau khi commit. Phần [Gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits) giải thích vì sao như vậy là chưa đủ, và sửa lại.

**Mail viết inline.** Một mail đủ nhỏ để viết bằng TypeScript thì không cần file template. `render()` trả về `html` thay cho `template` và `context`, tạo bằng tagged template `html`:

```typescript
@@filename(notifications/order-confirmation.mail)
return {
  subject: `Your order #${order.number}`,
  html: html`
    <p>Hi ${customer.name},</p>
    <p>thank you for your order! We are packing it now.</p>
    <table>
      ${order.items.map(
        (item) => html`
          <tr>
            <td>${item.name}</td>
            <td>${item.quantity}</td>
            <td>${price(item.price * item.quantity)}</td>
          </tr>`,
      )}
    </table>
    // ...
};
```

`html` escape mọi giá trị bạn chèn vào, theo cùng quy tắc như template: một giá trị bên trong thẻ phải nằm trong giá trị thuộc tính có dấu nháy, nếu không sẽ throw. Các template `html` lồng nhau và mảng của chúng, như các dòng của bảng, được chèn nguyên vẹn, còn `unsafeHtml()` chèn HTML do chính bạn tạo ra; cái tên đã là lời cảnh báo. `mailer.send()` cũng nhận `html`, cho message gửi không cần mail class.

#### Đính kèm hóa đơn và preview mail <a id="attach-the-invoice-and-preview-the-mail"></a>

Hóa đơn là một file PDF, được render bởi một provider nhỏ. Nó tự viết PDF bằng tay với một font có sẵn, để ví dụ không cần dependency. Một ứng dụng thực tế sẽ dùng library PDF hoặc một dịch vụ render ở đây. Mail chỉ cần các byte:

```typescript
@@filename(notifications/invoice-pdf)
@Injectable()
export class InvoicePdf {
  render(order: Order, customer: Customer): Buffer {
    const money = (cents: number) => `$${(cents / 100).toFixed(2)}`;
    const lines = [
      `Invoice ${order.number}`,
      `Date: ${order.placedAt.slice(0, 10)}`,
      `Bill to: ${customer.name}`,
      '',
      ...order.items.map((item) => `${item.quantity} x ${item.name}  ${money(item.price * item.quantity)}`),
      '',
      `Total: ${money(order.total)}`,
    ];
    // ...
  }
}
```

`render()` trả về file đính kèm cùng với template. Hóa đơn là một file đính kèm thông thường. Logo là một hình ảnh inline: `cid` của nó biến nó thành một phần của HTML, HTML tham chiếu tới nó bằng `cid:logo@example.com`. Logo nằm ở đầu mọi mail, nên tham chiếu được đặt trong layout:

```html
@@filename(mail/templates/layout.html)
<!DOCTYPE html>
<html>
<body>
<p><img src="cid:logo@example.com" alt="Logo" width="120" height="32"></p>
{{ '{' }}{{ '{' }}{{ '{' }} body {{ '}' }}{{ '}' }}{{ '}' }}
{{ '{' }}{{ '{' }}> signature{{ '}' }}{{ '}' }}
</body>
</html>
```

Mail class đính kèm logo và hóa đơn:

```typescript
@@filename(notifications/order-confirmation.mail)
const LOGO = join(import.meta.dirname, 'assets/logo.png');

@Injectable()
export class OrderConfirmationMail implements Mailable<OrderConfirmation> {
  constructor(private readonly invoicePdf: InvoicePdf) {}

  render({ order, customer }: OrderConfirmation) {
    // ...
    return {
      subject: `Your order #${order.number}`,
      // mail/templates/order-confirmation.html, wrapped in the layout
      template: 'order-confirmation',
      // ...
      attachments: [
        // Inline: the layout's <img> references it by its cid
        { cid: 'logo@example.com', path: LOGO },
        { filename: `invoice-${order.number}.pdf`, content: this.invoicePdf.render(order, customer) },
      ],
    };
  }
}
```

Mọi mail render trong layout này đều phải đính kèm logo theo cùng cách, nếu không phần header sẽ hiện hình ảnh bị hỏng. Template có thêm một dòng sau link, `<p>Your invoice is attached.</p>`.

Nội dung của file đính kèm là `Buffer`, chuỗi hoặc stream, hoặc được đọc từ một `path` local khi mail được gửi. Content type lấy theo tên file, và tên file không phải ASCII sẽ được encode để mọi mail client đều hiển thị được. Mailer sắp xếp các phần theo cách mà mail client mong đợi: logo nằm cạnh HTML, nên một client hiển thị bản text sẽ không liệt kê nó như một file đính kèm.

> warning **Cảnh báo** Đừng bao giờ tạo `path` của file đính kèm từ dữ liệu người dùng nhập vào. File ở đường dẫn đó sẽ được đính kèm, bất kể nó là gì. URL bị từ chối chứ không được tải về.

Trong lúc làm template, bạn không muốn phải đặt một đơn hàng cho mỗi thay đổi. `mailer.render()` render một mail class mà không gửi đi. Một route chỉ dành cho development hiển thị kết quả trên trình duyệt. Khi tắt cache template, nó hiển thị template vừa sửa ngay ở lần refresh tiếp theo:

```typescript
@@filename(notifications/mail-preview.controller)
import { Controller, Get, Header } from '@nestjs/common';
import { Mailer } from '@nestjs/mail';
import { OrderConfirmationMail, type OrderConfirmation } from './order-confirmation.mail.js';

const SAMPLE: OrderConfirmation = {
  customer: {
    id: 'sample',
    name: 'Ada Lovelace',
    email: 'ada@example.com',
    // ...
  },
  order: {
    id: '00000000-0000-4000-8000-000000000000',
    number: 1001,
    customerId: 'sample',
    items: [
      { productId: 'salmon-kibble-2kg', name: 'Salmon kibble, 2 kg', quantity: 2, price: 2499 },
      { productId: 'feather-wand', name: 'Feather wand toy', quantity: 1, price: 799 },
    ],
    total: 5797,
    placedAt: '2026-09-22T10:00:00.000Z',
  },
};

@Controller('dev/mail')
export class MailPreviewController {
  constructor(private readonly mailer: Mailer) {}

  /** Renders the mail with sample data, without sending it: GET /dev/mail/order-confirmation */
  @Get('order-confirmation')
  @Header('content-type', 'text/html; charset=utf-8')
  async orderConfirmation() {
    const message = await this.mailer.render(OrderConfirmationMail, { data: SAMPLE });

    // Browsers don't resolve cid: references; inline the images as data: URLs instead
    let body = message.html ?? '';
    for (const { cid, contentType, content } of message.attachments) {
      if (cid) {
        body = body.replaceAll(`cid:${cid}`, `data:${contentType};base64,${content.toString('base64')}`);
      }
    }
    return body;
  }
}
```

`render()` trả về `MailMessage` hoàn chỉnh: subject, HTML và phần text suy ra, các file đính kèm, và `toMime()` để lấy message thô. Ở đây người nhận là tùy chọn. `render()` cũng nhận một message viết inline, như một subject, một `template` và `context` của nó, để preview template mà không cần mail class. Chỉ đăng ký controller ở môi trường không phải production:

```typescript
@@filename(notifications/notifications.module)
@Module({
  // The preview route renders mail with sample data; production doesn't need it
  controllers: process.env.NODE_ENV === 'production' ? [] : [MailPreviewController],
  providers: [OrderConfirmationMail, InvoicePdf],
})
export class NotificationsModule {}
```

#### Gửi sau khi đơn hàng commit <a id="send-after-the-order-commits"></a>

Phần [Viết mail xác nhận đơn hàng](/application/mail#write-the-order-confirmation-mail) gửi mail từ request, sau khi đơn hàng commit. Có ba thứ có thể hỏng ở đó:

- **Một lần crash giữa lúc commit và lúc gửi sẽ làm mất mail.** Một đợt deploy khởi động lại process đúng lúc đó sẽ để lại một đơn hàng đã thanh toán mà không có xác nhận.
- **Mail server gặp sự cố sẽ làm thất bại một request vốn đã thành công.** Đơn hàng đã được lưu, nhưng khách hàng thấy lỗi 500 và có thể đặt hàng lại.
- **Khách hàng phải chờ mail server.** Một phiên trao đổi SMTP mất hàng trăm mili giây, và một server chậm sẽ kéo theo thời gian của request.

Đây là bài toán dual-write trong [bài hướng dẫn outbox](/reliability/outbox), và outbox (`@nestjs/outbox`, được cài và thiết lập trong bài hướng dẫn đó) giải quyết nó. Đơn hàng và một message `order.placed` được commit trong cùng một transaction, và một relay chuyển message cho một handler để gửi mail. Nếu gửi thất bại, relay sẽ retry có backoff, và chuyển những message không bao giờ thành công vào bảng dead-letter. Outbox giữ message của nó trong database PostgreSQL của ứng dụng, cạnh các đơn hàng, thông qua store của nó, `PostgresOutboxStore` từ `@nestjs/outbox/postgres`, trên database mà [`@nestjs/drizzle`](/data/drizzle) đăng ký. Store tự tạo các bảng của nó, trong một schema riêng, khi ứng dụng khởi động; phần [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database) trong bài hướng dẫn outbox trình bày về chúng, và cách áp dụng migration của chúng trên production.

Phần này trình bày transaction đơn hàng hai lần: lần đầu với Drizzle, là hướng chính của bài hướng dẫn, và sau đó, trong mục "Với TypeORM" ở cuối phần, cùng transaction đó cho ứng dụng dùng ORM là TypeORM. Hãy chọn một trong hai.

Đăng ký `OutboxModule`, và store làm provider của root module: một factory inject database Drizzle và registry `OutboxStorage`, nơi store tự đăng ký. Không có nó, outbox sẽ giữ message trong bộ nhớ, và làm mất chúng khi khởi động lại:

```typescript
@@filename(app.module)
@Module({
  imports: [
    // ...
    OutboxModule.forRootAsync({
      useFactory: () => ({
        relay: { enabled: process.env.OUTBOX_RELAY !== 'off' },
        // A mail server that is down for a while doesn't lose the confirmation
        retry: { attempts: 10, backoff: { delay: '10s', maxDelay: '10m' } },
      }),
    }),
    // ...
  ],
  providers: [
    {
      // Messages and inbox records in your database, in a schema of their own (nest_outbox)
      provide: PostgresOutboxStore,
      inject: [getDrizzleToken(), OutboxStorage],
      useFactory: (db: Database, outboxStorage: OutboxStorage) =>
        new PostgresOutboxStore({ executor: fromDrizzle(db) }, outboxStorage),
    },
  ],
})
export class AppModule {}
```

`OrdersService` thêm message thay vì gửi mail, với `tx` của Drizzle, để message được commit hoặc rollback cùng với đơn hàng:

```typescript
@@filename(orders/orders.service)
async placeOrder({ customerId, items }: PlaceOrderDto): Promise<Order> {
  if (!(await this.customersRepository.findById(customerId))) {
    throw new BadRequestException(`Unknown customer "${customerId}"`);
  }
  if (!items?.length) {
    throw new BadRequestException('An order needs at least one item');
  }

  const order = await this.db.transaction(async (tx) => {
    const order = await this.insertOrder(tx, customerId, items);
    // Same transaction: the confirmation mail is queued only if the order commits
    await this.outbox.add(tx, { topic: 'order.placed', payload: order });
    return order;
  });

  this.outbox.notify(); // send now instead of at the next poll
  return order;
}
```

Handler gửi mail:

```typescript
@@filename(notifications/order-mails.handler)
import { Injectable } from '@nestjs/common';
import { MailError, Mailer } from '@nestjs/mail';
import { NonRetryableMessageError, OnOutboxMessage, type OutboxHandlerContext } from '@nestjs/outbox';
import { CustomersRepository } from '../customers/customers.repository.js';
import type { Order } from '../orders/order.js';
import { OrderConfirmationMail } from './order-confirmation.mail.js';

@Injectable()
export class OrderMailsHandler {
  constructor(
    private readonly mailer: Mailer,
    private readonly customersRepository: CustomersRepository,
  ) {}

  // Runs after the order committed. The inbox skips messages this consumer already handled.
  @OnOutboxMessage('order.placed', { consumer: 'order-confirmation-mail' })
  async sendConfirmation(order: Order, { message, signal }: OutboxHandlerContext) {
    const customer = await this.customersRepository.findById(order.customerId);
    if (!customer) {
      throw new NonRetryableMessageError(`Customer ${order.customerId} not found`);
    }

    try {
      await this.mailer.send(OrderConfirmationMail, {
        to: { name: customer.name, address: customer.email },
        data: { order, customer },
        // Over SMTP, a redelivery of this message keeps its Message-ID; Resend gets the
        // key as its Idempotency-Key and refuses the duplicate
        idempotencyKey: message.id,
        signal,
        // The outbox retries with its own backoff, and dead-letters what never succeeds
        retry: false,
      });
    } catch (error) {
      // A refused address or sender won't be accepted later: dead-letter it now
      if (error instanceof MailError && error.permanent) {
        throw new NonRetryableMessageError(error.message, { cause: error });
      }
      throw error;
    }
  }
}
```

Đăng ký handler trong `NotificationsModule`, module này import `CustomersModule` để lấy repository:

```typescript
@@filename(notifications/notifications.module)
@Module({
  imports: [CustomersModule],
  // The preview route renders mail with sample data; production doesn't need it
  controllers: process.env.NODE_ENV === 'production' ? [] : [MailPreviewController],
  providers: [OrderConfirmationMail, InvoicePdf, OrderMailsHandler],
})
export class NotificationsModule {}
```

Mỗi tùy chọn của lời gọi `send()` có một nhiệm vụ riêng:

- **`idempotencyKey`.** Outbox gửi ít nhất một lần: một relay crash sau khi gửi, trước khi kịp ghi lại, sẽ gửi lại. Key xác định mail xuyên suốt các lần gửi đó. Header `Message-ID` được suy ra từ nó, nên qua SMTP, một bản trùng sẽ mang cùng id, và Gmail cùng các bên nhận khác dùng id đó để loại bỏ bản trùng. `ResendTransport` gửi key dưới dạng `Idempotency-Key` của Resend, và Resend từ chối bản trùng trong vòng 24 giờ. Postmark, SendGrid và SES tự gán `Message-ID` của chúng và không có idempotency key, nên với các dịch vụ này, một lần gửi lại có thể đến tay khách hàng hai lần.
- **`signal`.** Relay sẽ abort nó khi handler chạy lâu hơn `publishTimeout`. Mailer sẽ dừng phiên trao đổi SMTP hoặc HTTP request.
- **`retry: false`.** Mặc định mailer retry các lỗi tạm thời ba lần, có backoff. Ở đây outbox đã retry rồi, trong khoảng thời gian tính bằng phút thay vì giây, nên mailer chỉ thử một lần cho mỗi lần gửi. Retry ở cả hai tầng sẽ nhân số lần lên.

Mọi lỗi mà package throw ra đều kế thừa `MailError`, và flag `permanent` của nó cho biết gửi lại cùng message có thể thành công hay không. Một reply SMTP 4xx (greylisting, hộp thư đầy), một lỗi 429 từ HTTP provider, một timeout hay một kết nối bị ngắt đều là lỗi tạm thời: handler throw lại nó, và outbox sẽ retry. Một reply 5xx, như `550 5.1.1 User unknown`, là lỗi vĩnh viễn: handler throw `NonRetryableMessageError`, và outbox chuyển message vào dead-letter ngay lập tức thay vì thử thêm mười lần nữa.

Khi SMTP từ chối một trong nhiều người nhận, transaction được reset trước khi message được gửi, nên một lỗi luôn có nghĩa là không ai nhận được nó, và việc retry của outbox không thể gửi trùng. Ngoại lệ duy nhất: kết nối bị ngắt sau khi message đã được truyền đi, trước khi server trả lời. Mailer không thể biết server đã giữ lại message hay chưa, nên báo một lỗi tạm thời, và lần retry sẽ gửi lại nó, với cùng `Message-ID`.

**Với TypeORM.** Cùng transaction đơn hàng đó cho một ứng dụng dùng ORM là TypeORM. Drizzle vẫn là hướng chính của bài hướng dẫn: hãy dùng code này thay cho code Drizzle ở trên, không phải dùng song song. Outbox giữ message thông qua cùng store đó, trên data source của TypeORM, như phần [Giữ message trong database của bạn](/reliability/outbox#keep-messages-in-your-database) trong bài hướng dẫn outbox trình bày. Ứng dụng ví dụ giữ phiên bản này trong `src/typeorm`, cạnh code Drizzle của bài hướng dẫn, với khách hàng, sản phẩm và đơn hàng là các entity.

`TypeOrmModule` thay chỗ cho `DrizzleModule` trong root module, với các tùy chọn mà TypeORM CLI dùng chung, và factory của store inject `DataSource` của nó, thông qua `fromTypeOrm()`:

```typescript
@@filename(typeorm/app.module)
@Module({
  imports: [
    TypeOrmModule.forRootAsync({
      // The entities and migrations the CLI uses; migrations run on deploy (`migration:run`)
      useFactory: () => ({ ...dataSourceOptions, url: process.env.DATABASE_URL }),
    }),
    // ...
    OutboxModule.forRootAsync({
      useFactory: () => ({
        relay: { enabled: process.env.OUTBOX_RELAY !== 'off' },
        // A mail server that is down for a while doesn't lose the confirmation
        retry: { attempts: 10, backoff: { delay: '10s', maxDelay: '10m' } },
      }),
    }),
    // ...
  ],
  providers: [
    {
      // Messages and inbox records in your database, in a schema of their own (nest_outbox)
      provide: PostgresOutboxStore,
      inject: [DataSource, OutboxStorage],
      useFactory: (dataSource: DataSource, outboxStorage: OutboxStorage) =>
        new PostgresOutboxStore({ executor: fromTypeOrm(dataSource) }, outboxStorage),
    },
  ],
})
export class AppModule {}
```

`OrdersService` mở transaction bằng data source, và truyền entity manager của transaction vào `outbox.add()`, cạnh các thao tác ghi của chính nó. Type parameter của outbox là `EntityManager` của TypeORM:

```typescript
@@filename(typeorm/orders.service)
@Injectable()
export class OrdersService {
  constructor(
    private readonly dataSource: DataSource,
    private readonly customersRepository: CustomersRepository,
    private readonly outbox: Outbox<EntityManager>,
  ) {}

  async placeOrder({ customerId, items }: PlaceOrderDto): Promise<Order> {
    // ... check the customer and the items, as in the Drizzle version

    const order = await this.dataSource.transaction(async (manager) => {
      const order = await this.insertOrder(manager, customerId, items);
      // The transaction's EntityManager: the confirmation mail is queued only if the order commits
      await this.outbox.add(manager, { topic: 'order.placed', payload: order });
      return order;
    });

    this.outbox.notify(); // send now instead of at the next poll
    return order;
  }

  private async insertOrder(manager: EntityManager, customerId: string, items: PlaceOrderDto['items']): Promise<Order> {
    const found = await manager.findBy(ProductEntity, { id: In(items.map((item) => item.productId)) });
    // ... price the lines and total them, as in the Drizzle version
    // The database numbers the order from its sequence: 1001, 1002, ...
    const { generatedMaps } = await manager.insert(OrderEntity, { id, customerId, items: lines, total, placedAt });
    const { number } = generatedMaps[0] as Pick<OrderEntity, 'number'>;
    return { id, number, customerId, items: lines, total, placedAt: placedAt.toISOString() };
  }
}
```

`OrderEntity` khai báo `number` là một identity column (`generated: 'identity'`), nên `manager.insert()` trả về con số mà database đã gán trong `generatedMaps`. Một entity không thể chỉ định sequence bắt đầu từ đâu, nên migration seed của ví dụ khởi động lại nó từ 1001, cạnh các khách hàng và sản phẩm mà nó insert. Handler và `NotificationsModule` giữ nguyên; `CustomersRepository` đọc khách hàng bằng TypeORM, giống như phần còn lại của ứng dụng.

#### Gửi trên production <a id="send-in-production"></a>

Development ghi file ra ổ đĩa local, thứ mà một container sẽ mất khi bị thay thế; production cần một transport thực thụ. Hãy chọn nó theo môi trường, để cùng một bản build chạy được ở mọi nơi:

```typescript
@@filename(mail-transport)
import { FileMailTransport, ResendTransport, SmtpTransport, type MailTransport } from '@nestjs/mail';
import { readFileSync } from 'node:fs';

/**
 * The transport for this environment: `file` in development (the default), `smtp` or
 * `resend` in production. Missing settings fail at startup, naming the variable.
 */
export function mailTransport(env: NodeJS.ProcessEnv = process.env): MailTransport {
  switch (env.MAIL_TRANSPORT ?? 'file') {
    case 'file':
      return new FileMailTransport({ directory: env.MAIL_DIRECTORY ?? 'var/mail' });
    case 'smtp':
      return new SmtpTransport({
        url: required(env, 'SMTP_URL'), // smtp://user:password@smtp.example.com:587
        pool: true,
        // A private CA, e.g. for a relay inside the company network
        ...(env.SMTP_CA_FILE && { tls: { ca: readFileSync(env.SMTP_CA_FILE) } }),
      });
    case 'resend':
      return new ResendTransport({ apiKey: required(env, 'RESEND_API_KEY') });
    default:
      throw new Error(`MAIL_TRANSPORT must be "file", "smtp" or "resend" (got "${env.MAIL_TRANSPORT}")`);
  }
}

function required(env: NodeJS.ProcessEnv, name: string): string {
  const value = env[name];
  if (!value) {
    throw new Error(`${name} is required when MAIL_TRANSPORT is "${env.MAIL_TRANSPORT}"`);
  }
  return value;
}
```

Tạo transport trong `forRootAsync()`. Factory chạy lúc khởi động, nên một lỗi gõ trong `MAIL_TRANSPORT` hay việc thiếu `SMTP_URL` sẽ làm ứng dụng dừng ngay tại đó thay vì làm hỏng mail đầu tiên:

```typescript
@@filename(app.module)
MailModule.forRootAsync({
  // Runs at startup: a bad MAIL_TRANSPORT or a missing SMTP_URL stops the app there
  useFactory: () => ({
    transport: mailTransport(),
    templates: new FileTemplateEngine({
      dir: join(import.meta.dirname, 'mail/templates'),
      layout: 'layout',
      cache: process.env.NODE_ENV === 'production',
    }),
    from: process.env.MAIL_FROM ?? 'Orders <orders@example.com>',
  }),
}),
```

**SMTP.** `SmtpTransport` tự nói chuyện bằng SMTP, trên `node:net` và `node:tls`:

- **Mã hóa.** Trên port 587, nó nâng cấp kết nối bằng STARTTLS, và một server không hỗ trợ STARTTLS sẽ bị từ chối thay vì gửi dạng plaintext. `startTls: 'opportunistic'`, mặc định cho localhost, chỉ nâng cấp khi server hỗ trợ, còn `'never'` giữ plaintext, dành cho relay trên mạng tin cậy. Trên port 465 (`smtps://`), nó dùng TLS ngay từ byte đầu tiên. Chứng chỉ được xác minh theo host name; `tls.ca` thêm một CA riêng. Thông tin đăng nhập không bao giờ được gửi qua kết nối không mã hóa, trừ khi gửi tới localhost.
- **Xác thực.** Nó dùng AUTH PLAIN hoặc LOGIN, tùy server hỗ trợ cái nào, và `authMethod` ép dùng một cái cụ thể. Với Gmail và Microsoft 365, hãy truyền OAuth access token làm `accessToken` trong `auth` để dùng XOAUTH2. OAuth access token sẽ hết hạn, thường là sau một giờ, nên `accessToken` cũng có thể là một hàm trả về token, hoặc một promise của token: nó được gọi cho mỗi kết nối mới, và có thể lấy token mới. `name` đặt tên mà transport dùng để giới thiệu bản thân trong `EHLO`; mặc định là host name của máy nếu đó là tên đầy đủ (fully qualified), nếu không thì là địa chỉ IP.
- **Pooling.** `pool: true` giữ tối đa năm kết nối mở và dùng lại chúng, thay vì một lần bắt tay TCP và TLS cho mỗi mail. Một object sẽ đặt các giới hạn: `maxConnections` (mặc định 5; các lần gửi tiếp theo phải chờ có kết nối rảnh), `maxMessages` (mặc định 100, sau đó kết nối sẽ được thay mới) và `idleTimeout` (mặc định `'30s'`, sau đó kết nối rảnh sẽ bị đóng). Mọi kết nối đều gửi `QUIT` khi ứng dụng tắt.
- **Reply.** Một reply 4xx là `MailSmtpError` tạm thời, reply 5xx là vĩnh viễn. Cả hai đều mang `code` của reply, mã mở rộng (như `5.1.1`) và text của server.

Để ký mail bằng DKIM khi SMTP server của bạn không làm việc đó, hãy thêm `dkim` với domain (`domainName`), selector (`keySelector`) và private key (`privateKey`, dạng PEM hoặc `KeyObject`). Key RSA ký bằng `rsa-sha256`, key Ed25519 ký bằng `ed25519-sha256` (RFC 8463); không phải bên nhận nào cũng đã xác minh được chữ ký Ed25519, và transport chỉ ký bằng một key, nên RSA là lựa chọn an toàn trừ khi bạn biết chắc server của người nhận hỗ trợ. Chữ ký bao gồm From, Reply-To, To, Cc, Subject, Date, Message-ID và các header MIME, cộng thêm các header tùy chỉnh của message; `dkim.headers` thay thế danh sách đó. From luôn được ký, và được liệt kê nhiều hơn số lần nó xuất hiện trong message một lần, nên một From thứ hai được thêm vào phía dưới chữ ký sẽ làm hỏng chữ ký. Các HTTP provider tự ký bằng domain đã xác minh của bạn.

**HTTP provider.** `ResendTransport`, `PostmarkTransport`, `SendGridTransport` và `SesTransport` gọi API của các provider bằng `fetch`, và không cần SDK nào. Tùy chọn `fetch` thay thế hàm toàn cục, để đi qua proxy hoặc để stub API trong test. `SesTransport` ký request bằng AWS Signature Version 4, và nhận các credential provider của AWS SDK, như instance role, làm `credentials`. Trong bốn cái, chỉ Resend hỗ trợ idempotency key. Resend và SendGrid cần ít nhất một người nhận `to`: một mail chỉ có `cc` hoặc `bcc` sẽ thất bại với `MailMessageError` trước khi gửi request.

**Địa chỉ quốc tế hóa.** Một domain có ký tự không phải ASCII (`zoë@kočka.example`) được chuyển sang dạng ASCII (IDNA, `xn--...`) với mọi transport, để không server nào phải hỗ trợ nó. Phần local không phải ASCII, đứng trước `@`, thì không chuyển được: qua SMTP, nó cần extension SMTPUTF8 của server. `SmtpTransport` dùng SMTPUTF8 khi server hỗ trợ, nếu không sẽ thất bại với một `MailConnectionError` vĩnh viễn trước khi gửi bất cứ thứ gì: `The SMTP server ... doesn't support SMTPUTF8, which an address with non-ASCII characters needs`. Các HTTP provider nhận địa chỉ nguyên vẹn, và việc chấp nhận hay không là do provider quyết định.

Hãy dùng `app.enableShutdownHooks()` trong `main.ts`, để một đợt deploy cho relay hoàn tất những mail đang gửi, rồi mới đóng SMTP pool.
#### Gửi bằng ngôn ngữ của khách hàng <a id="send-it-in-the-customers-language"></a>

Cửa hàng bán hàng bằng tiếng Anh và tiếng Ba Lan. Khách hàng chọn ngôn ngữ khi đăng ký, và bảng `customers` lưu nó trong cột `locale`: `en` hoặc `pl`. Mailer chuyển locale của mỗi lần gửi cho template engine, engine sẽ chọn template tương ứng.

Hãy dịch template: thêm `order-confirmation.pl.html` cạnh template tiếng Anh.

```html
@@filename(mail/templates/order-confirmation.pl.html)
<p>Cześć {{ '{' }}{{ '{' }} customer.name {{ '}' }}{{ '}' }},</p>
<p>dziękujemy za zamówienie! Właśnie je pakujemy.</p>
<table>
  <tr><th>Produkt</th><th>Ilość</th><th>Cena</th></tr>
  {{ '{' }}{{ '{' }}#each items{{ '}' }}{{ '}' }}
  <tr>
    <td>{{ '{' }}{{ '{' }} name {{ '}' }}{{ '}' }}</td>
    <td>{{ '{' }}{{ '{' }} quantity {{ '}' }}{{ '}' }}</td>
    <td>{{ '{' }}{{ '{' }} price {{ '}' }}{{ '}' }}</td>
  </tr>
  {{ '{' }}{{ '{' }}/each{{ '}' }}{{ '}' }}
</table>
<p><strong>Razem: {{ '{' }}{{ '{' }} total {{ '}' }}{{ '}' }}</strong></p>
<p><a href="{{ '{' }}{{ '{' }} orderUrl {{ '}' }}{{ '}' }}">Zobacz zamówienie</a></p>
<p>Fakturę znajdziesz w załączniku.</p>
```

Với locale `pl`, `FileTemplateEngine` render `order-confirmation.pl.html`, còn với mọi locale khác, hoặc không có locale, nó render `order-confirmation.html`. Một locale có vùng sẽ thử chính nó trước, rồi đến ngôn ngữ của nó: với `pt-BR`, engine tìm `order-confirmation.pt-BR.html`, rồi `order-confirmation.pt.html`. Partial và layout cũng được tìm theo cùng cách, nên layout vẫn dùng chung, còn chữ ký tiếng Ba Lan là một partial riêng:

```html
@@filename(mail/templates/partials/signature.pl.html)
<p>Zespół obsługi klienta</p>
```

Nội dung của một mail là văn xuôi, nên nó được dịch theo từng file: người dịch thấy toàn bộ mail, và viết câu tiếng Ba Lan thay vì điền từng key một. Những gì mail class tính toán vẫn phụ thuộc vào locale: subject, tên file hóa đơn và giá tiền. Chúng lấy từ `@nestjs/i18n`, được trình bày chi tiết trong [chương đa ngôn ngữ](/application/i18n). Hãy thêm một catalog cho mail, mỗi ngôn ngữ một catalog:

```json
@@filename(i18n/en/mail.json)
{
  "orderConfirmation": {
    "subject": "Your order #{number}",
    "invoiceFile": "invoice-{number}.pdf"
  }
}
```

```json
@@filename(i18n/pl/mail.json)
{
  "orderConfirmation": {
    "subject": "Twoje zamówienie #{number}",
    "invoiceFile": "faktura-{number}.pdf"
  }
}
```

Đăng ký cấu trúc của các catalog, để key được kiểm tra lúc compile, và đăng ký `I18nModule` cạnh `MailModule`:

```typescript
@@filename(i18n/translations)
import type mail from './en/mail.json';

export interface Translations {
  mail: typeof mail;
}

declare module '@nestjs/i18n' {
  interface I18nTypes {
    translations: Translations;
  }
}
```

```typescript
@@filename(app.module)
@Module({
  imports: [
    // ...
    I18nModule.forRoot({
      defaultLocale: 'en',
      supportedLocales: ['en', 'pl'],
      loader: new JsonI18nLoader({ path: join(import.meta.dirname, 'i18n') }),
    }),
    MailModule.forRootAsync({
      // ...
    }),
    // ...
  ],
})
export class AppModule {}
```

Hãy thêm cả các catalog vào asset trong `nest-cli.json` (`i18n/**/*.json`), như chương đa ngôn ngữ đã hướng dẫn.

Mail class là một provider, nên nó inject `I18nService` cạnh bộ render hóa đơn. `render()` nhận thêm tham số thứ hai, render context, trong đó `locale` là locale truyền vào `send()`, cũng là locale mà mailer chuyển cho template engine. `to` của nó chứa danh sách người nhận đã parse, và rỗng khi preview được render mà không có người nhận:

```typescript
@@filename(notifications/order-confirmation.mail)
type Key = keyof Translations['mail']['orderConfirmation'];

const SHOP_URL = process.env.SHOP_URL ?? 'https://shop.example.com';
const LOGO = join(import.meta.dirname, 'assets/logo.png');

@Injectable()
export class OrderConfirmationMail implements Mailable<OrderConfirmation> {
  constructor(
    private readonly i18nService: I18nService,
    private readonly invoicePdf: InvoicePdf,
  ) {}

  render({ order, customer }: OrderConfirmation, { locale }: MailRenderContext) {
    // Mail is sent outside the customer's request, so the locale is always passed explicitly
    const t = (key: Key, args?: Record<string, unknown>) =>
      this.i18nService.t(`mail.orderConfirmation.${key}`, { locale, args });
    const price = (cents: number) =>
      this.i18nService.formatNumber(cents / 100, { locale, style: 'currency', currency: 'USD' });
    return {
      subject: t('subject', { number: order.number }),
      // order-confirmation.pl.html for Polish, else order-confirmation.html
      template: 'order-confirmation',
      // ...
      attachments: [
        // Inline: the layout's <img> references it by its cid
        { cid: 'logo@example.com', path: LOGO },
        { filename: t('invoiceFile', { number: order.number }), content: this.invoicePdf.render(order, customer) },
      ],
    };
  }
}
```

Context không thay đổi: cùng các giá trị đó điền vào template nào cũng được. `Key` là `keyof Translations['mail']['orderConfirmation']`, nên một key viết sai là lỗi compile. Giá tiền được định dạng theo locale: `$25.98` trong tiếng Anh, `25,98 USD` trong tiếng Ba Lan. Tên file hóa đơn lấy từ catalog: `invoice-1001.pdf` hoặc `faktura-1001.pdf`.

> warning **Cảnh báo** Hãy truyền locale một cách tường minh. `I18nService` quay về locale của request hiện tại, mà mail thường được gửi bên ngoài request của người nhận: từ một outbox handler, như ở đây, hoặc từ request của người khác, như một admin. Locale của request đó là locale sai.

Outbox handler truyền locale của khách hàng khi gửi:

```typescript
@@filename(notifications/order-mails.handler)
await this.mailer.send(OrderConfirmationMail, {
  to: { name: customer.name, address: customer.email },
  data: { order, customer },
  locale: customer.locale,
  // ...
});
```

Một subject hay tên người nhận tiếng Ba Lan không thể đưa nguyên vẹn vào header của mail: header chỉ dùng ASCII. Mailer encode text không phải ASCII trong header thành encoded-word theo RFC 2047, như `=?UTF-8?Q?Twoje_zam=C3=B3wienie_=231001?=`, và body theo quoted-printable, để mọi server đều chuyển message nguyên vẹn và mail client hiển thị `Twoje zamówienie #1001`.

Preview lấy ngôn ngữ từ query string, nên có thể kiểm tra cả hai phiên bản trên trình duyệt:

```typescript
@@filename(notifications/mail-preview.controller)
/** Renders the mail with sample data, without sending it: GET /dev/mail/order-confirmation?locale=pl */
@Get('order-confirmation')
@Header('content-type', 'text/html; charset=utf-8')
async orderConfirmation(@Query('locale') locale = 'en') {
  const message = await this.mailer.render(OrderConfirmationMail, { data: SAMPLE, locale });
  // ...
}
```

#### Dùng template engine khác <a id="use-another-template-engine"></a>

`FileTemplateEngine` implement `MailTemplateEngine`, một abstract class chỉ có một method: `render()` nhận tên template, context và locale, rồi trả về HTML, hoặc một object có `html` và `text`, hoặc một promise của một trong hai. Hãy kế thừa nó để render bằng Handlebars, EJS hay bất cứ thứ gì khác. Một engine cho template Handlebars trong các file `.hbs`:

```typescript
@@filename(mail/handlebars-template.engine)
import { MailTemplateEngine, MailTemplateError, type MailTemplateRenderOptions } from '@nestjs/mail';
import Handlebars from 'handlebars';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const TEMPLATES = join(import.meta.dirname, 'templates');

/** Renders order-confirmation.pl.hbs, else order-confirmation.hbs, with Handlebars. */
export class HandlebarsTemplateEngine extends MailTemplateEngine {
  private readonly templates = new Map<string, ReturnType<typeof Handlebars.compile> | undefined>();

  async render(name: string, context: object, { locale }: MailTemplateRenderOptions) {
    // Only a language code goes into a file name, never whatever the locale holds
    const localized = locale && /^[a-z]{2}$/.test(locale) ? [`${name}.${locale}.hbs`] : [];
    for (const file of [...localized, `${name}.hbs`]) {
      const template = await this.load(file);
      if (template) {
        return template(context);
      }
    }
    throw new MailTemplateError(`No template "${name}" in ${TEMPLATES}`, { template: name });
  }

  private async load(file: string) {
    if (!this.templates.has(file)) {
      const source = await readFile(join(TEMPLATES, file), 'utf8').catch(() => undefined);
      // compat: plain paths fall back to outer contexts, as in FileTemplateEngine
      this.templates.set(file, source === undefined ? undefined : Handlebars.compile(source, { compat: true }));
    }
    return this.templates.get(file);
  }
}
```

Truyền nó làm `templates` thay cho `FileTemplateEngine`: một instance, hoặc chính class, để Nest khởi tạo, nhờ đó nó có thể inject cấu hình hoặc các provider khác. Giống như với transport, class được đặt ở cấp cao nhất của `forRootAsync()`, cạnh `useFactory`, còn factory trả về instance.

Mailer gửi HTML đúng như engine trả về, nên escape là việc của engine: Handlebars escape các giá trị trong ngoặc nhọn đôi, giống như `FileTemplateEngine`. `compat: true` cho các tên bên trong `#each` quay về tra trong context bên ngoài, nên các template trong bài hướng dẫn này render được bằng Handlebars mà không cần sửa. Handlebars không biết gì về thư mục `partials/` và layout: hãy đăng ký partial bằng `Handlebars.registerPartial()`, và tự render layout bao quanh mail. Với [MJML](https://mjml.io), hãy chuyển MJML đã render bằng `mjml2html()` trước khi trả về HTML. Hãy throw `MailTemplateError` cho template bị thiếu hoặc bị hỏng: đây là lỗi vĩnh viễn, nên outbox sẽ chuyển mail vào dead-letter thay vì retry.

#### Tự viết transport <a id="write-your-own-transport"></a>

Với một provider mà package không có sẵn transport, hãy kế thừa `MailTransport`. Method `send()` của nó nhận message hoàn chỉnh và resolve khi provider đã chấp nhận message. Một transport cho Mailgun, với endpoint `messages.mime` nhận message dạng MIME, giống cách `SesTransport` gửi tới SES:

```typescript
@@filename(mail/mailgun.transport)
import {
  MailProviderError,
  MailTransport,
  type MailMessage,
  type MailTransportResult,
  type MailTransportSendOptions,
} from '@nestjs/mail';

export interface MailgunTransportOptions {
  domain: string;
  apiKey: string;
  /** `https://api.eu.mailgun.net` for a domain in the EU region. */
  baseUrl?: string;
}

/** Sends the finished MIME message through Mailgun's `messages.mime` endpoint. */
export class MailgunTransport extends MailTransport {
  readonly #apiKey: string;
  private readonly url: string;

  constructor({ domain, apiKey, baseUrl = 'https://api.mailgun.net' }: MailgunTransportOptions) {
    super();
    this.#apiKey = apiKey;
    this.url = `${baseUrl}/v3/${encodeURIComponent(domain)}/messages.mime`;
  }

  async send(message: MailMessage, { signal }: MailTransportSendOptions): Promise<MailTransportResult> {
    const form = new FormData();
    // The envelope names every recipient; the MIME message leaves Bcc out
    form.append('to', message.envelope.to.join(','));
    form.append('message', new Blob([new Uint8Array(message.toMime())]), 'message.eml');

    // An abort rejects with signal.reason; a network error is transient, so the mailer retries it
    const response = await fetch(this.url, {
      method: 'POST',
      headers: { authorization: `Basic ${Buffer.from(`api:${this.#apiKey}`).toString('base64')}` },
      body: form,
      signal: AbortSignal.any([signal, AbortSignal.timeout(30_000)]),
    });

    if (!response.ok) {
      const retryAfter = Number(response.headers.get('retry-after'));
      // Permanent for 4xx except 408, 409 and 429: those and 5xx are retried
      throw new MailProviderError({
        provider: 'mailgun',
        status: response.status,
        detail: await response.text(),
        ...(retryAfter > 0 && { retryAfterMs: retryAfter * 1_000 }),
      });
    }

    const { id } = (await response.json()) as { id?: string };
    return { accepted: message.envelope.to, providerMessageId: id };
  }
}
```

Truyền một instance làm `transport`, giống như với các transport có sẵn. `send(message, options)` nhận:

- **`message`.** Một `MailMessage` đã được validate và đóng băng (frozen): `from`, `to`, `cc`, `bcc`, `replyTo`, `subject`, `html`, `text`, `attachments`, `headers` và `messageId`. `envelope` chứa SMTP envelope, với mỗi người nhận xuất hiện một lần, kể cả Bcc, còn `toMime()` trả về message dạng MIME, không kèm header Bcc. Đây là cùng một object ở mọi lần thử.
- **`signal`.** Abort khi bên gọi hủy việc gửi, như outbox relay khi một handler chạy quá timeout. Hãy dừng request, và reject với `signal.reason`; mailer không retry một lần abort.
- **`idempotencyKey`.** Key của bên gọi, giống nhau ở mọi lần thử và mọi lần gửi lại. Hãy gửi nó tới provider có khả năng loại bỏ request trùng, như `ResendTransport` làm; `Message-ID` vốn đã được suy ra từ nó.
- **`attempt`.** 1 cho lần thử đầu tiên, 2 cho lần retry đầu tiên.

Nó resolve ra `accepted`, các người nhận trong envelope mà provider đã nhận (tất cả nếu bỏ trống), `providerMessageId` và `response`, đây cũng là thứ mà `send()` của mailer resolve ra.

Những gì nó throw sẽ quyết định mailer có retry hay không. Hãy throw một `MailError` có `permanent` cho biết gửi lại cùng message có thể thành công hay không: `MailProviderError` cho lời từ chối của HTTP API, là lỗi vĩnh viễn với status 4xx ngoại trừ 408, 409 và 429 (trừ khi bạn tự truyền `permanent`), `MailConnectionError` và `MailTimeoutError` cho request thất bại hoặc chậm. Mọi lỗi khác đều được tính là tạm thời, trừ khi nó có `permanent: true` hoặc `status` 4xx, nên một lỗi mạng từ `fetch` sẽ được retry. Một lỗi có `retryAfterMs` sẽ khiến mailer chờ ít nhất khoảng đó trước lần thử tiếp theo, tối đa là `maxDelay`.

Một transport giữ kết nối hoặc client thì implement `close()`, method này chạy khi ứng dụng tắt, sau khi các lần gửi đang diễn ra đã xong.

#### Thử ngay <a id="try-it"></a>

Áp dụng các migration, chúng cũng thêm hai khách hàng và bốn sản phẩm:

```bash
$ export DATABASE_URL=postgres://localhost:5432/store
$ npx drizzle-kit migrate
```

Khởi động ứng dụng với các giá trị mặc định: file transport, và relay đang chạy. Đặt một đơn hàng cho Ada:

```bash
$ curl -X POST localhost:3000/orders \
    -H 'Content-Type: application/json' \
    -d '{"customerId":"ada","items":[{"productId":"salmon-kibble-2kg","quantity":2},{"productId":"feather-wand","quantity":1}]}'
{"id":"fd2bfc1c-db5c-455c-8876-bf7331a1029c","number":1001,"customerId":"ada","items":[{"productId":"salmon-kibble-2kg","name":"Salmon kibble, 2 kg","quantity":2,"price":2499},{"productId":"feather-wand","name":"Feather wand toy","quantity":1,"price":799}],"total":5797,"placedAt":"2026-09-25T10:59:00.173Z"}
```

Response trả về trước khi có mail nào được gửi. Một lát sau, handler của relay render mail và file transport ghi nó ra:

```bash
[Nest] 37252  - 09/25/2026, 12:59:00 PM     LOG [FileMailTransport] "Your order #1001" to ada@example.com written to var/mail/2026-09-25T10-59-00-199Z--LtIZd5B_AiZek3-x8nOt88YfUYjgkZi-42ff80.eml
```

File này chính là message đúng như SMTP sẽ truyền đi. Phần header và phần text của nó:

```bash
$ head -33 var/mail/*.eml
From: Orders <orders@example.com>
To: Ada Lovelace <ada@example.com>
Subject: Your order #1001
Date: Fri, 25 Sep 2026 10:59:00 +0000
Message-ID: <-LtIZd5B_AiZek3-x8nOt88YfUYjgkZi@example.com>
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="=_bTCd1MQ5LoxTNFNN0nLRwu8d"

--=_bTCd1MQ5LoxTNFNN0nLRwu8d
Content-Type: multipart/alternative; boundary="=_9HVDyVBGuLsAaijTpu4Y2_XU"

--=_9HVDyVBGuLsAaijTpu4Y2_XU
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: quoted-printable

Hi Ada Lovelace,

thank you for your order! We are packing it now.

Product Qty Price
Salmon kibble, 2 kg 2 $49.98
Feather wand toy 1 $7.99

Total: $57.97

View your order (https://shop.example.com/orders/fd2bfc1c-db5c-455c-8876-bf=
7331a1029c)

Your invoice is attached.

The customer care team
--=_9HVDyVBGuLsAaijTpu4Y2_XU
Content-Type: multipart/related; boundary="=_u7PgKDXrb-x3mIz35ZArIBAa"
```

Vài điều đáng chú ý:

- `Message-ID` được suy ra từ id của outbox message, không phải ngẫu nhiên. Một lần gửi lại sẽ mang cùng id.
- Phần text được suy ra từ HTML, với link được viết ra đầy đủ.
- Body ở dạng quoted-printable, giúp mọi dòng đủ ngắn cho bất kỳ mail server nào: dấu `=` ở cuối dòng đầu tiên của link nối nó với dòng tiếp theo.

Tiếp theo là HTML, logo và hóa đơn:

```bash
$ grep -E '^Content-(Type|Disposition|ID):' var/mail/*.eml | tail -5
Content-Type: image/png; name="logo.png"
Content-Disposition: inline; filename="logo.png"
Content-ID: <logo@example.com>
Content-Type: application/pdf; name="invoice-1001.pdf"
Content-Disposition: attachment; filename="invoice-1001.pdf"
```

Mở file trong một mail client để xem mail đã render. Để làm việc với template, hãy mở preview trên trình duyệt thay vào đó. Response là HTML của mail, template nằm trong layout, với logo được chèn inline dưới dạng URL `data:` (đã rút gọn ở đây):

```bash
$ curl localhost:3000/dev/mail/order-confirmation
```

```html
<!DOCTYPE html>
<html>
<body>
<p><img src="data:image/png;base64,…" alt="Logo" width="120" height="32"></p>
<p>Hi Ada Lovelace,</p>
<p>thank you for your order! We are packing it now.</p>
<table>
  <tr><th>Product</th><th>Qty</th><th>Price</th></tr>
  <tr>
    <td>Salmon kibble, 2 kg</td>
    <td>2</td>
    <td>$49.98</td>
  </tr>
  <tr>
    <td>Feather wand toy</td>
    <td>1</td>
    <td>$7.99</td>
  </tr>
</table>
<p><strong>Total: $57.97</strong></p>
<p><a href="https://shop.example.com/orders/00000000-0000-4000-8000-000000000000">View your order</a></p>
<p>Your invoice is attached.</p>

<p>The customer care team</p>
</body>
</html>
```

Tiếp theo, đặt mua một sản phẩm không tồn tại:

```bash
$ curl -X POST localhost:3000/orders \
    -H 'Content-Type: application/json' \
    -d '{"customerId":"ada","items":[{"productId":"salmon-kibble-2kg","quantity":1},{"productId":"catnip-mouse","quantity":1}]}'
{"message":"Unknown product \"catnip-mouse\"","error":"Bad Request","statusCode":400}
```

Transaction bị rollback, kéo theo message `order.placed`, và không có mail nào được ghi.

Cuối cùng, hãy xem [ngôn ngữ của khách hàng](/application/mail#send-it-in-the-customers-language) hoạt động. Đặt một đơn hàng cho Zofia, người đã chọn tiếng Ba Lan khi đăng ký:

```bash
$ curl -X POST localhost:3000/orders \
    -H 'Content-Type: application/json' \
    -d '{"customerId":"zofia","items":[{"productId":"feather-wand","quantity":1}]}'
{"id":"7fa5ce1f-9ef3-49b0-8de9-a2d98056c299","number":1002,"customerId":"zofia","items":[{"productId":"feather-wand","name":"Feather wand toy","quantity":1,"price":799}],"total":799,"placedAt":"2026-09-25T10:59:00.424Z"}
```

```bash
[Nest] 37252  - 09/25/2026, 12:59:00 PM     LOG [FileMailTransport] "Twoje zamówienie #1002" to zofia@example.com written to var/mail/2026-09-25T10-59-00-453Z-GnMdyKUxVa0FRBJ6wZ2k5snIWsdQmwC2-697a51.eml
```

Body lấy từ `order-confirmation.pl.html`. Subject tiếng Ba Lan và tên của Zofia được ghi vào file dưới dạng encoded-word, và hóa đơn của cô ấy là `faktura-1002.pdf`:

```bash
$ head -3 var/mail/2026-09-25T10-59-00-453Z-GnMdyKUxVa0FRBJ6wZ2k5snIWsdQmwC2-697a51.eml
From: Orders <orders@example.com>
To: =?UTF-8?Q?Zofia_W=C3=B3jcik?= <zofia@example.com>
Subject: =?UTF-8?Q?Twoje_zam=C3=B3wienie_=231002?=
```

#### Test <a id="testing"></a>

Thay transport bằng `InMemoryMailTransport`. Nó giữ lại mọi mail nhận được, và có các helper để tìm và đọc mail:

```typescript
@@filename(test/order-confirmation.e2e-spec)
import { PGlite } from '@electric-sql/pglite';
import { getDrizzleToken } from '@nestjs/drizzle';
import { InMemoryMailTransport, MailSmtpError, MailTransport } from '@nestjs/mail';
import { OutboxDeadLetters, OutboxRelay } from '@nestjs/outbox';
import { Test, type TestingModule } from '@nestjs/testing';
import { drizzle } from 'drizzle-orm/pglite';
import { migrate } from 'drizzle-orm/pglite/migrator';
import { fileURLToPath } from 'node:url';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { AppModule } from '../src/app.module.js';
import { OrderConfirmationMail } from '../src/notifications/order-confirmation.mail.js';
import { OrdersService } from '../src/orders/orders.service.js';

describe('Order confirmation mail', () => {
  const client = new PGlite(); // PostgreSQL in-process
  const mailbox = new InMemoryMailTransport();
  let moduleRef: TestingModule;
  let orders: OrdersService;
  let relay: OutboxRelay;

  beforeAll(async () => {
    const db = drizzle({ client });
    // Your migrations: the tables, and the seeded customers and products. The outbox's store
    // creates its own schema in init().
    await migrate(db, { migrationsFolder: fileURLToPath(new URL('../drizzle', import.meta.url)) });
    process.env.OUTBOX_RELAY = 'off'; // no poll loop: the test drives the relay
    moduleRef = await Test.createTestingModule({ imports: [AppModule] })
      .overrideProvider(getDrizzleToken())
      .useValue(db) // the outbox's store runs on it too
      .overrideProvider(MailTransport)
      .useValue(mailbox)
      .compile();
    await moduleRef.init();
    orders = moduleRef.get(OrdersService);
    relay = moduleRef.get(OutboxRelay);
  });

  afterAll(async () => {
    await moduleRef.close();
    await client.close();
  });

  beforeEach(() => mailbox.clear());

  it('confirms the order with the invoice and a link to it', async () => {
    const order = await orders.placeOrder({ customerId: 'ada', items: [{ productId: 'salmon-kibble-2kg', quantity: 1 }] });
    mailbox.assertNotSent(); // nothing until the relay publishes the committed order

    await relay.runOnce();

    const mail = mailbox.assertSent({ to: 'ada@example.com', mail: OrderConfirmationMail });
    expect(mail.subject).toBe(`Your order #${order.number}`);
    expect(mail.attachment(`invoice-${order.number}.pdf`).contentType).toBe('application/pdf');
    expect(mail.link('/orders/').pathname).toBe(`/orders/${order.id}`);
  });

  it('dead-letters a confirmation the mail server refuses', async () => {
    mailbox.failNext(new MailSmtpError('RCPT TO', { code: 550, text: 'User unknown' }));
    await orders.placeOrder({ customerId: 'ada', items: [{ productId: 'salmon-kibble-2kg', quantity: 1 }] });

    await relay.runOnce();

    mailbox.assertNotSent();
    const [deadLetter] = await moduleRef.get(OutboxDeadLetters).list();
    expect(deadLetter).toMatchObject({ topic: 'order.placed', reason: 'rejected' });
  });
});
```

- **Mọi thứ đều thật, trừ mạng.** Mail class render template của nó, với catalog và provider hóa đơn, outbox và inbox của nó đều chạy, và message được dựng hoàn chỉnh, kể cả header và file đính kèm. Chỉ có việc gửi đi là bị thay thế.
- **Database là PostgreSQL, chạy ngay trong process.** PGlite (`@electric-sql/pglite`, một dev dependency) chạy các migration thật của bạn, và bài test ghi đè database mà `DrizzleModule` đăng ký (token của nó lấy từ `getDrizzleToken()`) bằng PGlite, nên các repository và outbox store đều dùng nó. Không cần khởi động server nào, và mỗi file test có một database mới.
- **`assertSent()`** trả về mail gần nhất khớp điều kiện, theo người nhận (`to` khớp với to, cc và bcc), `subject`, mail class hoặc `template`, hoặc một predicate. Khi không có gì khớp, nó throw một lỗi liệt kê những gì đã được gửi. `assertNotSent()`, `filter()`, `find()` và `mails` lo phần còn lại. Các helper throw lỗi thông thường, nên chúng chạy được với mọi test runner.
- **`link()`** trả về link đầu tiên trong mail có chứa một chuỗi hoặc khớp một biểu thức chính quy, dưới dạng `URL`. Với tính năng reset mật khẩu hay magic link, đó là toàn bộ bài test: gửi mail, rồi gọi `mail.link('/reset-password').searchParams.get('token')` và đi theo link. Các entity được decode, nên `&amp;` mà việc escape ghi vào query string sẽ trở lại thành `&`.
- **`failNext()`** khiến lần gửi tiếp theo throw, ở đây là một lỗi SMTP vĩnh viễn, để test nhánh xử lý lỗi.
- **`raw`** là message dạng MIME, còn `mailer.render()` render riêng một mail class hoặc một template, dùng cho unit test của template.

#### Checklist cho production <a id="production-checklist"></a>

- Cấu hình SPF, DKIM và DMARC cho domain gửi mail. Các HTTP provider ký bằng DKIM khi domain đã được xác minh với họ; với SMTP, hãy ký bằng tùy chọn `dkim` hoặc ký ở relay.
- Giữ STARTTLS là bắt buộc, và bật xác minh chứng chỉ. Với relay dùng CA riêng, hãy truyền `tls.ca` thay vì tắt xác minh.
- Giữ thông tin đăng nhập trong biến môi trường hoặc kho secret. Transport giữ chúng trong các trường private, và thông báo lỗi không bao giờ chứa chúng.
- Gửi mail giao dịch sau khi commit, qua outbox, với `retry: false` trong handler và chính sách retry của outbox được điều chỉnh theo khoảng thời gian provider của bạn có thể bị sập.
- Truyền `idempotencyKey` cho mọi mail gửi từ một handler có thể chạy hai lần.
- Biến các lỗi mail vĩnh viễn thành dead letter, và đặt cảnh báo cho các outbox event `dead-lettered`. Một địa chỉ bị từ chối thường là do gõ sai lúc đăng ký, hoặc hộp thư không còn tồn tại.
- Theo dõi `MailEvents`, hoặc các diagnostics channel `nestjs:mail:sent` và `nestjs:mail:failed`, để phát hiện gửi thất bại và gửi chậm.
- Trên production, hãy gửi qua `SmtpTransport` hoặc transport của một HTTP provider. `FileMailTransport` ghi ra ổ đĩa local, thứ mà container sẽ mất khi khởi động lại hoặc bị thay thế, còn `LogMailTransport` chỉ ghi log: cả hai dành cho development, và `InMemoryMailTransport` dành cho test. Module sẽ cảnh báo lúc khởi động nếu một trong số chúng chạy với `NODE_ENV=production`.
- Giữ message của outbox trong database của ứng dụng, qua `PostgresOutboxStore` hoặc một store đã đăng ký khác, để mail trong hàng đợi được commit cùng đơn hàng và sống sót qua việc khởi động lại. Không có store, outbox sẽ từ chối khởi động với `NODE_ENV=production`, và store cũng vậy khi các migration của nó chưa được áp dụng: hãy áp dụng chúng khi deploy, như [bài hướng dẫn outbox](/reliability/outbox#keep-messages-in-your-database) chỉ dẫn.
- Ship các template sang `dist` bằng asset của CLI, và giữ cache template bật trên production, đây là giá trị mặc định: `cache: false` sẽ đọc lại file cho mỗi mail.
- Đừng đăng ký các route chỉ dành cho development, như preview, trên production.
- Dùng `app.enableShutdownHooks()`, để một đợt deploy chờ các mail đang gửi xong và đóng các kết nối SMTP.
#### Tham khảo <a id="reference"></a>

##### Tùy chọn module <a id="module-options"></a>

`MailModule.forRoot()` nhận các tùy chọn này, và factory của `forRootAsync()` trả về chúng. Khi dùng `useClass` hoặc `useExisting` thay cho `useFactory`, class đó implement `MailOptionsFactory`, với `createMailOptions()` trả về các tùy chọn. `transport`, `templates`, `imports` và `isGlobal` cũng đặt cạnh `useFactory`, `useClass` hoặc `useExisting` trong `forRootAsync()`. Các tùy chọn đã resolve được cung cấp dưới token `MAIL_MODULE_OPTIONS`.

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `transport` | instance hoặc class `MailTransport` | không có (bắt buộc) | Cách mail rời khỏi ứng dụng. Class sẽ được Nest khởi tạo, nên nó có thể inject cấu hình. Xem [Gửi trên production](/application/mail#send-in-production). |
| `templates` | instance hoặc class `MailTemplateEngine` | không có | Render các mail có chỉ định `template`: `FileTemplateEngine`, hoặc [engine của riêng bạn](/application/mail#use-another-template-engine). Class sẽ được Nest khởi tạo. Không có tùy chọn này, một mail có template sẽ thất bại với `MailTemplateError`. |
| `from` | địa chỉ | không có | Người gửi mặc định. Một message không có người gửi sẽ thất bại với `MailMessageError`. |
| `replyTo` | địa chỉ hoặc mảng | không có | Reply-To mặc định. |
| `headers` | `Record<string, string>` | không có | Được thêm vào mọi message. Header riêng của message sẽ được ưu tiên. |
| `retry` | số, `false` hoặc tùy chọn retry | 3 lần thử | Số lần thử cho mỗi lần gửi, với backoff bắt đầu từ `1s` và nhân đôi tới `30s`, full jitter. `false` chỉ thử một lần. Xem [Gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits). |
| `imports` | module | không có | Các module có export mà class transport hoặc template engine inject. |
| `isGlobal` | `boolean` | `true` | Đăng ký `Mailer`, `MailEvents`, `MailTransport` và `MailTemplateEngine` ở cấp global. |

Các tùy chọn retry gồm `attempts` (tổng số lần, tính cả lần đầu), `backoff` (một object có `delay`, `factor`, `maxDelay` và `jitter`, hoặc một hàm theo số lần thử) và `retryIf` (chỉ có thể thu hẹp những lỗi tạm thời nào được retry). Khi một HTTP provider trả lời kèm header `Retry-After`, thường là với lỗi 429 hoặc 503, lỗi sẽ giữ nó trong `retryAfterMs`, và mailer chờ ít nhất khoảng đó trước lần thử tiếp theo, tối đa là `maxDelay` (`30s` khi dùng hàm backoff). `signal` vẫn kết thúc được việc chờ. Reply của SMTP không có `Retry-After`, và một outbox handler với `retry: false` sẽ để việc chờ cho backoff của outbox.

##### Template engine

`FileTemplateEngine` nhận:

| Tùy chọn | Type | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `dir` | `string` | không có (bắt buộc) | Thư mục chứa template, với partial nằm trong thư mục con `partials/`. Đường dẫn tương đối được resolve theo thư mục làm việc. |
| `layout` | `string` | không có | Một template bọc HTML của mọi mail, đặt nó vào bằng ngoặc nhọn ba quanh `body`. Phiên bản `.txt`, nếu có, sẽ bọc phần text. |
| `cache` | `boolean` | `true` | Giữ các template đã compile, và danh sách file nào tồn tại, trong bộ nhớ. `false` sẽ đọc file cho mỗi mail, để thấy được thay đổi khi đang phát triển. |

`template: 'order-confirmation'` với locale `pt-BR` sẽ render file đầu tiên tồn tại trong số `order-confirmation.pt-BR.html`, `order-confirmation.pt.html` và `order-confirmation.html`, và file đầu tiên cùng tên với đuôi `.txt` làm phần text, nếu có. Tên template gồm chữ cái, chữ số, `-` và `_`, nằm trong các thư mục phân cách bằng `/`. Các tên khác, và các locale không phải language tag, sẽ thất bại với `MailTemplateError`, nên không cái nào có thể trỏ tới file nằm ngoài `dir`.

##### Cú pháp template <a id="template-syntax"></a>

Cú pháp là một tập con của Handlebars:

<table>
  <tr>
    <th>Cú pháp</th>
    <th>Render ra</th>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }} customer.name {{ '}' }}{{ '}' }}</code></td>
    <td>Giá trị, đã escape HTML. Đường dẫn dùng dấu chấm, và <code>items.0</code> là phần tử đầu tiên của mảng. Giá trị bị thiếu sẽ render ra rỗng. Trong template <code>.txt</code>, giá trị được giữ nguyên.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}{{ '{' }} body {{ '}' }}{{ '}' }}{{ '}' }}</code></td>
    <td>Giá trị nguyên vẹn, dành cho HTML do chính bạn tạo ra. HTML tạo bằng tag <code>html</code> cũng được chèn nguyên vẹn khi nằm giữa ngoặc nhọn đôi.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#if paid{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}else{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/if{{ '}' }}{{ '}' }}</code></td>
    <td>Phần đầu tiên khi giá trị là truthy, ngược lại là phần <code>else</code> (tùy chọn). <code>false</code>, <code>0</code>, chuỗi rỗng, danh sách rỗng và giá trị bị thiếu đều là falsy. <code>{{ '{' }}{{ '{' }}else if pending{{ '}' }}{{ '}' }}</code> nối thêm một điều kiện khác.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#unless paid{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/unless{{ '}' }}{{ '}' }}</code></td>
    <td>Ngược lại với <code>#if</code>, với phần <code>else</code> tùy chọn.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}#each items{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}else{{ '}' }}{{ '}' }} … {{ '{' }}{{ '{' }}/each{{ '}' }}{{ '}' }}</code></td>
    <td>Phần đầu tiên lặp lại một lần cho mỗi phần tử của danh sách, hoặc mỗi giá trị của object; phần <code>else</code> dành cho danh sách rỗng hoặc bị thiếu.</td>
  </tr>
  <tr>
    <td><code>this, &#64;index, &#64;first, &#64;last, &#64;key</code></td>
    <td>Bên trong <code>#each</code>: phần tử hiện tại, vị trí của nó tính từ 0, nó có phải phần tử đầu tiên hay cuối cùng không, và key của object. Một tên mà phần tử không có sẽ được tra trong các context bên ngoài.</td>
  </tr>
  <tr>
    <td><code>../number, &#64;root.shop</code></td>
    <td>Context bên ngoài <code>#each</code> hiện tại, và context của template.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}> signature{{ '}' }}{{ '}' }}</code></td>
    <td>Partial <code>partials/signature.html</code> (<code>.txt</code> trong template text), theo locale của mail, với context tại chỗ nó được chèn.</td>
  </tr>
  <tr>
    <td><code>{{ '{' }}{{ '{' }}! note {{ '}' }}{{ '}' }}, {{ '{' }}{{ '{' }}!-- note --{{ '}' }}{{ '}' }}</code></td>
    <td>Comment, bị loại khỏi output. Dạng thứ hai có thể chứa ngoặc nhọn đôi.</td>
  </tr>
  <tr>
    <td><code>\{{ '{' }}{{ '{' }}</code></td>
    <td>Ngoặc nhọn đôi theo nghĩa đen.</td>
  </tr>
</table>

Không có helper và không có biểu thức. Giá trị được đọc từ các thuộc tính riêng của context, không bao giờ từ prototype, và hàm không được gọi. Bất cứ thứ gì khác nằm giữa ngoặc nhọn đôi, một block không bao giờ được đóng, và một giá trị trong ngoặc nhọn đôi nằm bên trong thẻ nhưng ngoài giá trị thuộc tính có dấu nháy, đều thất bại với `MailTemplateError`, lỗi này có `file`, `line` và `column`.

##### Tùy chọn gửi <a id="send-options"></a>

`mailer.send(MailClass, options)` và `mailer.send(message)` nhận:

| Tùy chọn | Mô tả |
| --- | --- |
| `to`, `cc`, `bcc` | Một địa chỉ hoặc một mảng. Một địa chỉ là chuỗi chứa đúng một địa chỉ, hoặc một object có `name` và `address`. `bcc` chỉ đi vào SMTP envelope. |
| `data` | Dữ liệu của mail class, có type lấy từ `render()` của nó. |
| `locale` | Được truyền vào `render()` trong render context, và vào template engine, engine sẽ chọn template theo nó. Xem [Gửi bằng ngôn ngữ của khách hàng](/application/mail#send-it-in-the-customers-language). |
| `from`, `replyTo` | Ghi đè giá trị mặc định của module. |
| `subject`, `html`, `text` | Nội dung, dành cho message viết inline. `text` được suy ra từ `html` khi bỏ trống. |
| `template`, `context` | Template dùng để render body, và các giá trị nó đọc, thay cho `html` và `text`. `render()` của mail class trả về chúng theo cùng cách. |
| `attachments` | Mỗi file có `filename`, `content` (một `Buffer`, chuỗi hoặc stream) hoặc một `path` local, cùng `contentType` và `cid` tùy chọn. Xem [Đính kèm hóa đơn và preview mail](/application/mail#attach-the-invoice-and-preview-the-mail). |
| `headers` | Các header tùy chỉnh, như `List-Unsubscribe`. |
| `retry` | Ghi đè `retry` của module cho lần gửi này. |
| `signal` | Một `AbortSignal` dừng việc gửi và mọi khoảng chờ giữa các lần thử. |
| `idempotencyKey` | Xác định mail xuyên suốt các lần gửi lại. `Message-ID` được suy ra từ nó. |

`mailer.render(MailClass, options)` và `mailer.render(message)` nhận các tùy chọn tương tự nhưng không có các tùy chọn gửi, và resolve ra `MailMessage`, object này ghi lại `template` và `locale` của nó. `send()` resolve ra `messageId`, `providerMessageId` (khi provider có), `accepted` (các người nhận trong envelope đã được chấp nhận), `response` (reply SMTP cuối cùng) và `attempts`.

##### Transport <a id="transports"></a>

| Transport | Tùy chọn | Idempotency key |
| --- | --- | --- |
| `SmtpTransport` | `url` hoặc `host`, `port`, `secure`, `startTls` (`required`, `opportunistic` hoặc `never`; mặc định `required`, `opportunistic` với localhost), `auth` (`user` kèm `pass` hoặc `accessToken`), `authMethod` (`PLAIN`, `LOGIN` hoặc `XOAUTH2`), `name`, `tls`, `pool`, `timeouts`, `dkim` (`domainName`, `keySelector`, `privateKey`, `headers`) | chỉ có `Message-ID` được suy ra |
| `ResendTransport` | `apiKey`, `baseUrl`, `timeout`, `fetch` | `Idempotency-Key`, 24 giờ |
| `PostmarkTransport` | `serverToken`, `messageStream` (mặc định `outbound`), `baseUrl`, `timeout`, `fetch` | không có |
| `SendGridTransport` | `apiKey`, `baseUrl`, `timeout`, `fetch` | không có |
| `SesTransport` | `region`, `credentials`, `configurationSetName`, `endpoint`, `timeout`, `fetch` | không có |
| `FileMailTransport` | `directory`, `log` | chỉ dành cho development |
| `LogMailTransport` | `body`, `logger` | chỉ dành cho development |
| `InMemoryMailTransport` | không có | chỉ dành cho test, xem [Test](/application/mail#testing) |

`InMemoryMailTransport.mails` liệt kê mọi mail đã nhận, cũ nhất trước, dưới dạng `SentMail`, cũng là thứ mà `filter()`, `find()` và `assertSent()` trả về. Một `SentMail` có `messageId`, `from`, `to`, `cc`, `bcc`, `subject`, `html`, `text`, `attachments`, `headers`, `mail` (mail class), `template` và `locale` của message, cộng thêm `sentAt` (thời điểm transport nhận được), `raw` (mã nguồn MIME), `links` (mọi link, từ HTML, rồi đến các link chỉ có trong phần text), `link()`, `attachment()` và `message`, chính là `MailMessage`. `clear()` xóa sạch tất cả.

Với `pool: true`, `SmtpTransport` giữ tối đa 5 kết nối, gửi tối đa 100 message trên mỗi kết nối, và đóng một kết nối sau 30 giây không hoạt động; truyền một object có `maxConnections`, `maxMessages` và `idleTimeout` làm `pool` sẽ thay đổi các giới hạn đó. Timeout mặc định của nó là `30s` để kết nối, `30s` cho lời chào, `1m` cho mỗi lệnh và `5m` cho phần dữ liệu. HTTP provider timeout sau `30s` cho mỗi request.

##### Event <a id="events"></a>

`MailEvents.events$` phát ra một event cho mỗi lần gửi, sau các lần retry của nó. Mỗi event cũng được publish trên một channel `node:diagnostics_channel`.

| Loại event | Channel | Khi nào | Payload |
| --- | --- | --- | --- |
| `sent` | `nestjs:mail:sent` | Transport đã chấp nhận message. | `messageId`, `mail`, `recipients`, `subject`, `transport`, `attempts`, `durationMs`, `providerMessageId` |
| `failed` | `nestjs:mail:failed` | Việc gửi thất bại sau các lần retry, hoặc `signal` của nó abort trước lần thử đầu tiên (`attempts` là 0). | Các trường tương tự nhưng không có `providerMessageId`, cộng thêm `error` và `permanent` |

Một message không qua được validation sẽ throw trước khi có event nào.

##### Lỗi <a id="errors"></a>

Mọi lỗi đều kế thừa `MailError`, class này có `permanent` (gửi lại cùng message có chắc chắn không thành công hay không) và `code` (mã reply SMTP hoặc HTTP status của provider). Mailer chỉ retry những lỗi không phải vĩnh viễn. Xem [Gửi sau khi đơn hàng commit](/application/mail#send-after-the-order-commits).

| Lỗi | Khi nào | Vĩnh viễn |
| --- | --- | --- |
| `MailMessageError` | Message không hợp lệ, trước khi gửi bất cứ thứ gì. `field` nêu tên trường, `status` là 400. | Có |
| `MailConnectionError` | DNS, kết nối bị từ chối hoặc reset, TLS hoặc chứng chỉ. `cause` chứa lỗi socket. | Không, trừ các vấn đề cấu hình như server không hỗ trợ STARTTLS khi nó là bắt buộc |
| `MailTimeoutError` | Một giai đoạn chạy quá timeout của nó. Có `phase` và `timeoutMs`. | Không |
| `MailSmtpError` | Một reply lỗi của SMTP. Có `code`, `enhancedCode`, `command` và `response`. | Với reply 5xx |
| `MailRecipientsRejectedError` | Server từ chối một hoặc nhiều người nhận, và không có gì được gửi. `rejected` liệt kê họ. Kế thừa `MailSmtpError`. | Khi có bất kỳ lời từ chối nào là 5xx |
| `MailTemplateError` | Một template bị thiếu hoặc không compile được, hoặc một mail chỉ định template mà không có template engine. Có `template`, và `file`, `line`, `column` khi lỗi nằm trong một file. | Có |
| `MailProviderError` | Một HTTP provider từ chối request. Có `code` (HTTP status), `provider`, `providerCode`, và `retryAfterMs` khi response có `Retry-After` hợp lệ. | Với 4xx ngoại trừ 408, 409 và 429 |
