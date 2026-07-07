from django.db import models

class Client(models.Model):
    name = models.CharField(max_length=85, null=False, verbose_name="ФИО")
    phone = models.CharField(max_length=13, null=False, unique=True, verbose_name='Номер телефона')
    address = models.CharField(max_length=120, null=False, verbose_name='Адрес')
    balans = models.IntegerField(null=True, blank=True, verbose_name='Предоплата')
    note = models.TextField(max_length=255, null=True, verbose_name="Примечание")
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Широта'
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Долгота'
    )
    tg_id = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        verbose_name='Telegram ID'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время регистрации')
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Время последнего редактирования")

    def __str__(self):
        return f'{self.name} + {self.phone}'