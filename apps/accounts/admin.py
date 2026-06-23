from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'first_name', 'last_name', 'national_id', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('phone_number', 'first_name', 'last_name', 'national_id')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'national_id')}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('تاریخ‌ها', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2'),
        }),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'code', 'created_at', 'is_used')
    list_filter = ('is_used',)
    search_fields = ('phone_number',)
    readonly_fields = ('created_at',)
