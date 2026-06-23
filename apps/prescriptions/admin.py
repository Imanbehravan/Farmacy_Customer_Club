from django.contrib import admin
from .models import Prescription, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1
    fields = ('drug_name', 'quantity', 'dosage', 'is_available')


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'user', 'national_id', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tracking_code', 'national_id', 'user__phone_number')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    inlines = [PrescriptionItemInline]


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'drug_name', 'quantity', 'dosage', 'is_available')
    list_filter = ('is_available',)
    search_fields = ('drug_name', 'prescription__tracking_code')