import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class LogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'logs_group'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'ping')
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def log_message(self, event):
        log = event['log']
        await self.send(text_data=json.dumps({
            'type': 'log',
            'log': log
        }))
