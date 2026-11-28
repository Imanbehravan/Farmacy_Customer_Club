"""
آیکون‌های PWA را از روی  static/img/logo.png  می‌سازد.

بعد از جایگزین کردن لوگو، فقط این دستور را اجرا کنید:
    python manage.py make_pwa_icons
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageChops

MATCHA = (78, 112, 52)       # باید با --matcha-700 در main.css یکی باشد
WHITE = (255, 255, 255)


def fit(logo, size, padding):
    """لوگو را با حاشیه‌ی مشخص در مربع size×size وسط می‌گذارد."""
    inner = int(size * (1 - 2 * padding))
    img = logo.copy()
    img.thumbnail((inner, inner), Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return canvas


class Command(BaseCommand):
    help = 'ساخت آیکون‌های PWA، favicon و badge اعلان از static/img/logo.png'

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR) / 'static'
        src = base / 'img' / 'logo.png'
        if not src.exists():
            raise CommandError(f'فایل {src} پیدا نشد.')
        out = base / 'icons'
        out.mkdir(parents=True, exist_ok=True)
        logo = Image.open(src).convert('RGBA')

        # آیکون معمولی: پس‌زمینه‌ی سفید با گوشه‌های گرد
        for size in (192, 512):
            bg = Image.new('RGBA', (size, size), WHITE + (255,))
            bg.alpha_composite(fit(logo, size, 0.14))
            bg.save(out / f'icon-{size}.png')

        # Maskable: لوگو در ناحیه‌ی امن (۸۰٪ مرکز) روی زمینه‌ی ماچا
        mask = Image.new('RGBA', (512, 512), WHITE + (255,))
        mask.alpha_composite(fit(logo, 512, 0.22))
        mask.save(out / 'maskable-512.png')

        # iOS
        touch = Image.new('RGBA', (180, 180), WHITE + (255,))
        touch.alpha_composite(fit(logo, 180, 0.12))
        touch.convert('RGB').save(out / 'apple-touch-icon.png')

        # favicon
        fav = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        fav.alpha_composite(fit(logo, 64, 0.04))
        fav.save(out / 'favicon.png')

        # Badge اندروید: فقط سیلوئت سفید روی زمینه‌ی شفاف.
        # اگر لوگو پس‌زمینه‌ی تخت دارد (شفاف نیست)، اختلاف با رنگ گوشه‌ها شکل را می‌سازد.
        small = fit(logo, 96, 0.08)
        alpha = small.split()[3]
        opaque = [(n, c) for n, c in small.getcolors(maxcolors=96 * 96) if c[3] > 200]
        total = sum(n for n, _ in opaque)
        if total > 0.55 * 96 * 96 * 0.84 ** 2:       # بیشتر سطح لوگو رنگ تخت است (پس‌زمینه دارد)
            dominant = max(opaque)[1]
            bg = Image.new('RGB', small.size, dominant[:3])
            diff = ImageChops.difference(small.convert('RGB'), bg).convert('L')
            alpha = ImageChops.multiply(alpha, diff.point(lambda v: 255 if v > 40 else 0))
        badge = Image.new('RGBA', (96, 96), WHITE + (0,))
        badge.putalpha(alpha)
        badge.save(out / 'badge-96.png')

        self.stdout.write(self.style.SUCCESS(f'آیکون‌ها در {out} ساخته شد.'))
