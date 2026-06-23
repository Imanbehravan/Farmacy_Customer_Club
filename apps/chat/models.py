from django.db import models
from django.conf import settings


class ChatRoom(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_room',
        verbose_name='کاربر'
    )
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    last_message_at = models.DateTimeField(auto_now=True, verbose_name='آخرین پیام')

    class Meta:
        verbose_name = 'اتاق چت'
        verbose_name_plural = 'اتاق‌های چت'
        ordering = ['-last_message_at']

    def __str__(self):
        return f"چت {self.user.phone_number}"

    def unread_by_admin(self):
        return self.messages.filter(is_from_admin=False, is_read=False).count()


class ChatMessage(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='اتاق'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='فرستنده'
    )
    message = models.TextField(verbose_name='پیام')
    is_from_admin = models.BooleanField(default=False, verbose_name='از طرف ادمین')
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ارسال')

    class Meta:
        verbose_name = 'پیام'
        verbose_name_plural = 'پیام‌ها'
        ordering = ['created_at']

    def __str__(self):
        sender_label = 'ادمین' if self.is_from_admin else self.sender.phone_number
        return f"{sender_label}: {self.message[:40]}"
