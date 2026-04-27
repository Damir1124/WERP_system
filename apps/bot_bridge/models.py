# Модели для приложения bot_bridge (если понадобятся в будущем)
# Пока что приложение использует существующие модели из других apps

# Пример возможной будущей модели:
# class BotSession(models.Model):
#     tg_id = models.BigIntegerField(unique=True)
#     worker = models.ForeignKey('workers.Worker', on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     last_activity = models.DateTimeField(auto_now=True)