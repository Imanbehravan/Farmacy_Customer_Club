from django.urls import path
from . import views

app_name = 'customer_ranking'
urlpatterns = [
    path('', views.ranking_page, name='ranking'),
]