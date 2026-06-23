from django.urls import path
from . import views

# این خط رو حذف کن یا کامنت کن
# app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('verify/', views.VerifyOTPView.as_view(), name='verify_otp'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]