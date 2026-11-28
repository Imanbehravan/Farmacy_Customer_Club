from django.contrib import admin
from .models import PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_agent', 'failure_count', 'created_at', 'last_success_at')
    search_fields = ('user__phone_number', 'user_agent')
    readonly_fields = ('endpoint', 'p256dh', 'auth', 'created_at', 'last_success_at')

    @admin.display(description='دستگاه')
    def short_agent(self, obj):
        return (obj.user_agent or '—')[:60]
