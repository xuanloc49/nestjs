# Translation workflow notes (internal)

Workflow: `python -I _tools/nt.py skel <rel>` -> translate `_work/skel/<rel>.pN.md` into `_work/vi/<rel>.pN.md` -> `python -I _tools/nt.py build <rel>` -> `vi/<rel>`. `status` shows progress. Glossary: `vi/THUAT-NGU.md`.

Style decisions already applied (keep consistent):
- Admonition labels: leave `**Hint**`/`**Warning**`/`**Notice**`/`**Note**` in English in the skeleton; build auto-converts to Gợi ý/Cảnh báo/Chú ý/Lưu ý.
- Headings: Nest building blocks stay English (Controllers, Providers, Modules, Middleware, Exception filters, Pipes, Guards, Interceptors, Custom provider, Dynamic module, Injection scope, Execution context, Lifecycle event, Module reference, Discovery service, Testing). Descriptive headings translated ("#### Bind guard", "#### Cài đặt", "#### Cách dùng", "#### Bắt đầu").
- Page titles used in link text: "Những bước đầu tiên" (/first-steps), "Provider bất đồng bộ", "Không phụ thuộc nền tảng", "Custom route decorator", "Ứng dụng standalone" (/standalone-applications), "Kỹ thuật validation" (/application/validation), "HTTP adapter" (/http/performance), "Nest so với Fastify, Express và Hono".
- "exceptions layer" -> "lớp xử lý exception"; method-scoped/controller-scoped/global-scoped -> "cấp method / cấp controller / cấp global"; parameter-scoped -> "cấp tham số".
- "we recommend" -> "chúng tôi khuyên"; "you" -> "bạn"; tutorial "we/let's" -> "ta"/"hãy".
- "resolve" stays (resolve dependency/promise). "register" -> "đăng ký". "bind" stays. "instantiate" -> "khởi tạo".
- request-scoped / singleton / transient / durable stay English.
- "built-in X" -> "X có sẵn". "out of the box" -> "có sẵn"/"mặc định".
- Keep external article titles in English.
- Link tooltips ('title') may be translated.
