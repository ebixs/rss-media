# rss-media — خط ساخت تصویر اینستاگرام رامان سلامت سهیل

این مخزن فقط عکس‌های پست‌های اینستاگرام را می‌سازد و نگه می‌دارد. عمومی است چون اینستاگرام (از طریق Metricool) عکس را از نشانی `raw.githubusercontent.com` می‌خواند.

- `posts/<تاریخ>-<نام>/post.md` متن و پرامپت تصویر هر پست؛ `final.jpg` عکس نهایی؛ `metricool.json` نتیجهٔ زمان‌بندی و انتشار.
- `scripts/generate.py` ساخت پس‌زمینه با Cloudflare Workers AI (رایگان)؛ `scripts/compose.py` قالب برند فارسی.
- `.github/workflows/images.yml` با هر push پستی تازه، دو گزینهٔ عکس می‌سازد.

**قواعد محتوا، اسکیل‌های اینستاگرام، موتور یادگیری، سئو و داشبورد** در مخزن خصوصی بازاریابی هستند: `ebixs/rss-marketing` (نام قبلی `rss-social`).
