from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("sales/", views.sales_report, name="sales_report"),
    path("reports/sales/feed/", views.sales_feed, name="sales_feed"),
    path("reports/sales/pdf/", views.sales_pdf, name="sales_pdf"),
]