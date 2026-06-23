from django.contrib import admin
from .models import Notification, BroadcastMessage


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__phone_number', 'title')
    readonly_fields = ('created_at',)


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'discount_percentage', 'recipient_count', 'sent_by', 'sent_at')
    readonly_fields = ('sent_at', 'recipient_count', 'sent_by')