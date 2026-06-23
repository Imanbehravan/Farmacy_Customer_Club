from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.UserChatView.as_view(), name='user_chat'),
    path('admin-panel/chat/', views.AdminChatListView.as_view(), name='admin_chat_list'),
    path('admin-panel/chat/<int:user_id>/', views.AdminChatRoomView.as_view(), name='admin_chat_room'),
]
