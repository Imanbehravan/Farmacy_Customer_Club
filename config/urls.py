from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import landing_view

urlpatterns = [
    # صفحه اصلی
    path('', landing_view, name='landing'),
    
    path('django-admin/', admin.site.urls),
    
    # همه اپ‌ها با path خالی (همونطور که قبلاً بودن)
    path('', include('apps.accounts.urls')),
    path('', include('apps.prescriptions.urls')),
    path('', include('apps.notifications.urls')),
    path('', include('apps.chat.urls')),
    path('', include('apps.blog.urls')),
    path('', include('apps.customer_club.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)