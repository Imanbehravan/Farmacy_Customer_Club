import base64

from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid01


def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


class Command(BaseCommand):
    help = 'یک جفت کلید VAPID برای Web Push می‌سازد (مقادیر را در .env بگذارید).'

    def handle(self, *args, **options):
        vapid = Vapid01()
        vapid.generate_keys()
        public = vapid.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        private = vapid.private_key.private_numbers().private_value.to_bytes(32, 'big')
        self.stdout.write('\n# این دو خط را در فایل .env قرار دهید:')
        self.stdout.write(f'VAPID_PUBLIC_KEY={_b64(public)}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={_b64(private)}')
        self.stdout.write('\nهشدار: با عوض کردن کلیدها، اشتراک دستگاه‌های قبلی باطل می‌شود.\n')
