from django.db import models
from django.utils import timezone


class Client(models.Model):
    name = models.CharField(max_length=85, null=False, verbose_name="ФИО")
    phone = models.CharField(max_length=13, null=False, unique=True, verbose_name='Номер телефона')
    balans = models.IntegerField(null=True, blank=True, verbose_name='Предоплата')
    note = models.TextField(max_length=255, null=True, verbose_name="Примечание")
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Широта'
    )
    longitude = models.DecimalField(
        max_digits=10,
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

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        return f'{self.name} + {self.phone}'


class ClientAddress(models.Model):
    """
    Модель для хранения до 3-х адресов на одного клиента.
    При создании нового адреса, если их больше 3-х, самый старый удаляется.
    """
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='Клиент'
    )
    label = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='Метка (Дом, Офис, Работа)'
    )
    address_text = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name='Адрес'
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Широта'
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Долгота'
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последнее использование'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        ordering = ['-last_used_at', '-created_at']
        verbose_name = 'Адрес клиента'
        verbose_name_plural = 'Адреса клиентов'

    def __str__(self):
        if self.address_text:
            return f"{self.client.name}: {self.address_text[:50]}"
        elif self.latitude and self.longitude:
            return f"{self.client.name}: ({self.latitude}, {self.longitude})"
        return f"{self.client.name}: Адрес #{self.id}"