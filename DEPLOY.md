# راهنمای CI/CD و پیامک کد تایید

## ۱) پیامک کد تایید با کاوه‌نگار

کد از **سرویس Verify Lookup** کاوه‌نگار ارسال می‌شود (مخصوص کد تایید و سریع‌تر/مطمئن‌تر از ارسال ساده).

### کارهایی که در پنل کاوه‌نگار باید انجام بدهید
1. وارد [panel.kavenegar.com](https://panel.kavenegar.com) شوید و حساب را **شارژ** کنید.
2. **کلید API** را از بخش تنظیمات/حساب کاربری بردارید (`API Key`).
   - اگر محدودیت IP برای کلید فعال است، IP سرور (`193.138.77.13`) را اضافه کنید.
3. یک **قالب تایید (Verify Template)** بسازید:
   - نام قالب: `verify` (اگر نام دیگری گذاشتید باید در `.env` هم بگذارید)
   - متن قالب (حتما شامل `%token`):
     ```
     باشگاه مشتریان داروخانه
     کد تایید شما: %token
     ```
   - لینک در متن نگذارید. قالب باید **تایید شود** (معمولا از چند دقیقه تا چند ساعت).
4. بعد از تایید قالب، این دو خط را در فایل `.env` **روی سرور** (`/opt/pharmacy/.env`) بگذارید:
   ```
   KAVENEGAR_API_KEY=کلید-شما
   KAVENEGAR_TEMPLATE=verify
   ```
5. اعمال تنظیمات:
   ```bash
   cd /opt/pharmacy && WEB_TAG=$(cat .current_tag) docker compose up -d --force-recreate web && docker compose restart nginx
   ```

به‌محض ثبت `KAVENEGAR_API_KEY`، نمایش کد روی صفحه **خودکار خاموش** می‌شود و فقط پیامک ارسال می‌شود.
تا وقتی کلید ثبت نشده، رفتار قبلی (نمایش کد روی صفحه) برقرار است تا ورود کاربران قطع نشود.

### تست سریع کلید و قالب از روی سرور
```bash
curl -s "https://api.kavenegar.com/v1/<API_KEY>/verify/lookup.json" \
  --data-urlencode "receptor=09xxxxxxxxx" --data-urlencode "token=123456" --data-urlencode "template=verify"
```
در پاسخ باید `"status":200` ببینید. خطاهای رایج: `401` کلید نامعتبر/IP مجاز نیست، `424` قالب پیدا نشد یا هنوز تایید نشده، `418` اعتبار کافی نیست.

### محافظت‌های اضافه‌شده
- کد ۶ رقمی با `secrets` (امن) ساخته می‌شود؛ اعتبار ۵ دقیقه
- فاصله‌ی ۲ دقیقه بین دو درخواست برای یک شماره، حداکثر ۵ پیامک در ساعت برای هر شماره، ۳۰ درخواست در ساعت برای هر IP
- بعد از ۵ بار کد اشتباه، کد باطل می‌شود (جلوگیری از حدس زدن)
- اگر ارسال پیامک شکست بخورد، خطا لاگ می‌شود و به کاربر پیام مناسب نشان داده می‌شود
- همه‌ی سقف‌ها از `.env` قابل تغییرند: `OTP_COOLDOWN_SECONDS`, `OTP_MAX_PER_HOUR`, `OTP_MAX_PER_IP_HOUR`, `OTP_MAX_ATTEMPTS`

---

## ۲) CI/CD (GitHub Actions)

با هر `push` به `main`:
1. **Test**: `check`، بررسی commit بودن مایگریشن‌ها، تست‌ها (با Postgres و Redis واقعی)
2. **Build**: ساخت ایمیج Docker در GitHub (روی سرور چیزی build نمی‌شود، پس به PyPI/Docker Hub از داخل ایران وابسته نیست)
3. **Deploy**: ایمیج با SSH به سرور فرستاده می‌شود، `migrate` و `collectstatic` اجرا می‌شود، سلامت‌سنجی انجام می‌شود؛ اگر ناموفق بود **خودکار به نسخه‌ی قبلی برمی‌گردد**

روی Pull Request فقط مرحله‌ی Test اجرا می‌شود.

### راه‌اندازی (یک‌بار)

**الف) روی کامپیوتر خودتان یک کلید SSH مخصوص دیپلوی بسازید**
```bash
ssh-keygen -t ed25519 -f gh_deploy -N "" -C "github-actions"
```
دو فایل `gh_deploy` (خصوصی) و `gh_deploy.pub` (عمومی) ساخته می‌شود.

**ب) سرور را آماده کنید** (فایل `deploy/setup-server.sh` را به سرور بفرستید و اجرا کنید)
```bash
scp deploy/setup-server.sh root@193.138.77.13:/root/
ssh root@193.138.77.13
# روی سرور:
# قبل از هر کاری از دیتابیس فعلی بکاپ بگیرید:
docker exec pharmacy_db pg_dump -U pharmacy_user pharmacy_club > /root/backup-$(date +%F).sql
# اگر پروژه‌ی فعلی در مسیری مثل /root/Farmacy_Customer_Club است، OLD_PROJECT_DIR را بدهید تا .env فعلی کپی شود:
OLD_PROJECT_DIR=/root/Farmacy_Customer_Club bash /root/setup-server.sh "$(cat کلید-عمومی-gh_deploy.pub)"
```
اسکریپت Docker را (در صورت نبود) نصب می‌کند، کاربر `deploy` می‌سازد، کلید عمومی را به آن می‌دهد و `/opt/pharmacy/.env` را آماده می‌کند.
سپس `/opt/pharmacy/.env` را باز کنید و مطمئن شوید: `DEBUG=False`، `SECRET_KEY` قوی، `ALLOWED_HOSTS` شامل IP/دامنه‌ی سایت، و رمز دیتابیس همان رمز فعلی است.

**ج) در GitHub: Settings → Secrets and variables → Actions → New repository secret**

| Secret | مقدار |
|---|---|
| `SSH_HOST` | `193.138.77.13` |
| `SSH_USER` | `deploy` |
| `SSH_PRIVATE_KEY` | کل محتوای فایل `gh_deploy` (خصوصی) |
| `SSH_KNOWN_HOSTS` | (اختیاری ولی بهتر) خروجی `ssh-keyscan -t ed25519 193.138.77.13` |
| `SSH_PORT` | (اختیاری) پیش‌فرض 22 |

اختیاری: در تب **Variables** مقدار `DEPLOY_PATH` (پیش‌فرض `/opt/pharmacy`).
همچنین یک Environment به نام `production` بسازید (Settings → Environments)؛ اگر خواستید می‌توانید برای آن تایید دستی (Required reviewers) بگذارید.

**د) اولین دیپلوی**: تغییرات را commit و روی `main` push کنید (یا از تب Actions گزینه‌ی *Run workflow*).

### نکات مهم
- **نام پروژه‌ی compose و دیتابیس**: `deploy.sh` volume دیتابیس فعلی (`*_postgres_data`) را پیدا می‌کند و از همان نام پروژه استفاده می‌کند تا دیتا و مدیا گم نشوند. اگر چند volume پیدا شد، نام را دستی در `/opt/pharmacy/.compose_project` بنویسید.
- **برگشت به نسخه‌ی قدیمی**: در تب Actions یک run قدیمی موفق را *Re-run* کنید.
- **لاگ‌ها**: `cd /opt/pharmacy && docker compose logs -f web`
- **HTTPS/دامنه**: اگر سایت با دامنه و HTTPS سرو می‌شود، در `.env` این‌ها را اضافه کنید: `CSRF_TRUSTED_ORIGINS=https://دامنه` و `USE_X_FORWARDED_PROTO=True` (و گواهی را در nginx/پروکسی جلویی تنظیم کنید).
- هر دیپلوی ایمیج (~صدها مگابایت فشرده) را به سرور می‌فرستد؛ بسته به سرعت اینترنت سرور ممکن است چند دقیقه طول بکشد.
- تست‌ها فعلا فقط برای اپ `accounts` است؛ با نوشتن تست برای اپ‌های دیگر و افزودن label به مرحله‌ی Tests در `ci-cd.yml` پوشش بیشتر می‌شود.
