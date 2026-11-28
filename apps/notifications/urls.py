from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.NotificationsPageView.as_view(), name='notifications_page'),
    path('api/notifications/', views.NotificationsAPIView.as_view(), name='notifications_api'),
    path('api/notifications/<int:pk>/read/', views.MarkReadView.as_view(), name='mark_read'),
    path('admin-panel/broadcast/', views.AdminBroadcastView.as_view(), name='admin_broadcast'),
]
