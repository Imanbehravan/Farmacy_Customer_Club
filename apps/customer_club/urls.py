from django.urls import path
from . import views

urlpatterns = [
    path('admin-panel/purchases/', views.AdminPurchasesView.as_view(), name='admin_purchases'),
    path('admin-panel/purchases/user-info/', views.UserDiscountInfoView.as_view(), name='user_discount_info'),
    path('admin-panel/campaigns/', views.AdminCampaignsView.as_view(), name='admin_campaigns'),
    path('admin-panel/campaigns/<int:pk>/toggle/', views.ToggleCampaignView.as_view(), name='toggle_campaign'),
]
