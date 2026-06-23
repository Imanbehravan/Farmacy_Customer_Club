import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        # Determine room
        if self.user.is_staff:
            # Admin connecting to a specific user's room
            self.room_user_id = self.scope['url_route']['kwargs'].get('user_id')
            self.room_group_name = f'chat_{self.room_user_id}'
        else:
            # Regular user connecting to their own room
            self.room_group_name = f'chat_{self.user.id}'
            self.room_user_id = self.user.id

        # Ensure room exists
        await self.get_or_create_room()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Send chat history
        history = await self.get_history()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': history
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data.get('message', '').strip()
        if not message_text:
            return

        is_admin = self.user.is_staff
        msg = await self.save_message(message_text, is_admin)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender': 'داروساز' if is_admin else self.user.phone_number,
                'is_from_admin': is_admin,
                'time': msg['time'],
                'id': msg['id'],
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'is_from_admin': event['is_from_admin'],
            'time': event['time'],
            'id': event['id'],
        }))

    @database_sync_to_async
    def get_or_create_room(self):
        from .models import ChatRoom
        from apps.accounts.models import User
        try:
            user = User.objects.get(id=self.room_user_id)
            room, _ = ChatRoom.objects.get_or_create(user=user)
            return room
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, message_text, is_admin):
        from .models import ChatRoom, ChatMessage
        from apps.accounts.models import User
        user = User.objects.get(id=self.room_user_id)
        room = ChatRoom.objects.get(user=user)
        msg = ChatMessage.objects.create(
            room=room,
            sender=self.user,
            message=message_text,
            is_from_admin=is_admin
        )
        return {'id': msg.id, 'time': msg.created_at.strftime('%H:%M')}

    @database_sync_to_async
    def get_history(self):
        from .models import ChatRoom, ChatMessage
        from apps.accounts.models import User
        try:
            user = User.objects.get(id=self.room_user_id)
            room = ChatRoom.objects.get(user=user)
            messages = ChatMessage.objects.filter(room=room).order_by('created_at')[:50]
            return [{
                'id': m.id,
                'message': m.message,
                'sender': 'داروساز' if m.is_from_admin else m.sender.phone_number,
                'is_from_admin': m.is_from_admin,
                'time': m.created_at.strftime('%H:%M'),
            } for m in messages]
        except Exception:
            return []
