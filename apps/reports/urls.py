from django.urls import path
from .excel_export import sales_report_excel

from . import views

app_name = "reports"

urlpatterns = [
    path("sales/", views.sales_report, name="sales_report"),
    path("sales/feed/", views.sales_feed, name="sales_feed"),
    path("sales/pdf/", views.sales_pdf, name="sales_pdf"),
    path('sales/excel/', sales_report_excel, name='sales_report_excel'),
]