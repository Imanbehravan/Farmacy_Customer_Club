from django.urls import path
from . import views

urlpatterns = [
    # User
    path('prescriptions/submit/', views.SubmitPrescriptionView.as_view(), name='submit_prescription'),
    path('prescriptions/', views.MyPrescriptionsView.as_view(), name='my_prescriptions'),

    # Admin Panel
    path('admin-panel/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-panel/prescriptions/', views.AdminPrescriptionsView.as_view(), name='admin_prescriptions'),
    path('admin-panel/prescriptions/<int:pk>/', views.AdminPrescriptionDetailView.as_view(), name='admin_prescription_detail'),
    path('admin-panel/prescriptions/<int:pk>/delete/', views.DeletePrescriptionView.as_view(), name='admin_prescription_delete'),
]