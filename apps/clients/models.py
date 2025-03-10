from django.db import models

class Client(models.Model):
    name = models.CharField(max_length=85, null=False, verbose_name="ФИО")
    phone = models.CharField(max_length=12, null=False, unique=True, verbose_name='Номер телефона')
    address = models.CharField(max_length=120, null=False, verbose_name='Адрес')
    balans = models.IntegerField(null=True, verbose_name='Предоплата')
    note = models.TextField(max_length=255, null=True, verbose_name="Примечание")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время регистрации')
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Время последнего редактирования")

    def __str__(self):
        return f'{self.name} + {self.phone}'