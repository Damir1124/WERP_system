import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FinancialTransactions, Finance
from .utils import update_finance_record


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для живого мониторинга финансового дашборда"""
    
    async def connect(self):
        """Подключение клиента к группе 'dashboard'"""
        self.group_name = 'dashboard'
        
        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем текущее состояние финансов при подключении
        await self.send_current_finance()

    async def disconnect(self, close_code):
        """Отключение клиента от группы"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_current_finance(self):
        """Отправка текущих финансовых данных клиенту"""
        finance_data = await self.get_latest_finance()
        await self.send(text_data=json.dumps({
            'type': 'finance_update',
            'data': finance_data
        }))

    @database_sync_to_async
    def get_latest_finance(self):
        """Получение последней финансовой сводки из базы данных"""
        try:
            finance = Finance.objects.latest('date')
            return {
                'income': finance.income,
                'consumption': finance.consumption,
                'profit': finance.profit,
                'card_profit': finance.card_profit,
                'date': finance.date.isoformat()
            }
        except Finance.DoesNotExist:
            return {
                'income': 0,
                'consumption': 0,
                'profit': 0,
                'card_profit': 0,
                'date': None
            }

    async def finance_update(self, event):
        """Обработка события обновления финансовых данных"""
        # Отправляем обновленные данные клиенту
        await self.send(text_data=json.dumps(event))


# Сигнал для отправки обновлений при сохранении FinancialTransactions
@receiver(post_save, sender=FinancialTransactions)
def send_finance_update_on_transaction(sender, instance, **kwargs):
    """
    Сигнал, который отправляет обновление в WebSocket группу
    при каждом сохранении FinancialTransactions
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    # Обновляем финансовую запись для даты транзакции
    update_finance_record(instance.date)
    
    # Получаем последние данные Finance
    try:
        finance = Finance.objects.filter(date=instance.date).first()
        if not finance:
            finance = Finance.objects.latest('date')
    except Finance.DoesNotExist:
        finance = None
    
    if finance:
        # Подготавливаем данные для отправки
        finance_data = {
            'income': finance.income,
            'consumption': finance.consumption,
            'profit': finance.profit,
            'card_profit': finance.card_profit,
            'date': finance.date.isoformat()
        }
        
        # Отправляем обновление в группу WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'dashboard',
            {
                'type': 'finance_update',
                'data': finance_data
            }
        )