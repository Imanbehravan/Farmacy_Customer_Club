from django.contrib import admin
from .models import Purchase, Discount, GlobalDiscount, CampaignUsage


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_amount', 'discount_percentage', 'amount',
                    'is_cosmetic', 'discount_source', 'purchase_date')
    list_filter = ('is_cosmetic', 'discount_source', 'purchase_date')
    search_fields = ('user__phone_number', 'description')
    readonly_fields = ('purchase_date',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('user', 'percentage', 'discount_type', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used', 'discount_type')
    search_fields = ('user__phone_number',)
    readonly_fields = ('created_at',)


@admin.register(GlobalDiscount)
class GlobalDiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'percentage', 'category', 'is_active', 'created_at', 'expires_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(CampaignUsage)
class CampaignUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign', 'used_at')
    search_fields = ('user__phone_number', 'campaign__name')
    readonly_fields = ('used_at',)