from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import Notification

from . import push


@receiver(post_save, sender=Notification)
def push_on_new_notification(sender, instance, created, raw=False, **kwargs):
    """هر اعلان تازه (در همه‌ی بخش‌های سایت) خودکار به گوشی/سیستم کاربر هم پوش می‌شود."""
    if created and not raw:
        push.push_after_commit([instance])
