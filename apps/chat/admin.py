from django.contrib import admin
from .models import ChatRoom, ChatMessage


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'created_at', 'last_message_at')
    list_filter = ('is_active',)
    search_fields = ('user__phone_number',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender', 'is_from_admin', 'is_read', 'created_at')
    list_filter = ('is_from_admin', 'is_read')
    search_fields = ('room__user__phone_number', 'message')
    readonly_fields = ('created_at',)
