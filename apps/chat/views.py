from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from .models import ChatRoom, ChatMessage


def is_admin(user):
    return user.is_authenticated and user.is_staff


class UserChatView(View):
    @method_decorator(login_required)
    def get(self, request):
        room, _ = ChatRoom.objects.get_or_create(user=request.user)
        messages = ChatMessage.objects.filter(room=room).order_by('created_at')
        # Mark admin messages as read
        ChatMessage.objects.filter(room=room, is_from_admin=True, is_read=False).update(is_read=True)
        return render(request, 'chat/room.html', {
            'room': room,
            'chat_messages': messages,
            'ws_url': f'/ws/chat/',
        })


class AdminChatListView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request):
        rooms = ChatRoom.objects.select_related('user').order_by('-last_message_at')
        rooms_data = []
        for room in rooms:
            last_msg = room.messages.order_by('-created_at').first()
            unread = room.messages.filter(is_from_admin=False, is_read=False).count()
            rooms_data.append({
                'room': room,
                'last_message': last_msg,
                'unread': unread,
            })
        return render(request, 'admin_panel/chat_list.html', {'rooms_data': rooms_data})


class AdminChatRoomView(View):
    @method_decorator(login_required)
    @method_decorator(user_passes_test(is_admin, login_url='/login/'))
    def get(self, request, user_id):
        from apps.accounts.models import User
        chat_user = get_object_or_404(User, id=user_id)
        room, _ = ChatRoom.objects.get_or_create(user=chat_user)
        messages = ChatMessage.objects.filter(room=room).order_by('created_at')
        # Mark user messages as read
        ChatMessage.objects.filter(room=room, is_from_admin=False, is_read=False).update(is_read=True)
        return render(request, 'admin_panel/chat_room.html', {
            'room': room,
            'chat_user': chat_user,
            'chat_messages': messages,
            'ws_url': f'/ws/chat/{user_id}/',
        })
