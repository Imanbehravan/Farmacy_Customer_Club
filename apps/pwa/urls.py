from django.urls import path
from . import views

urlpatterns = [
    path('manifest.webmanifest', views.manifest, name='pwa_manifest'),
    path('sw.js', views.service_worker, name='pwa_sw'),
    path('offline/', views.offline, name='pwa_offline'),
    path('pwa/push/subscribe/', views.push_subscribe, name='push_subscribe'),
    path('pwa/push/unsubscribe/', views.push_unsubscribe, name='push_unsubscribe'),
    path('pwa/push/test/', views.push_test, name='push_test'),
]
