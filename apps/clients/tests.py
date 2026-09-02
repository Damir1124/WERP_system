from django.test import TestCase
from django.utils import timezone
from .models import Client


class ClientTestSave(TestCase):
    def setUp(self):
        """Создание клиента перед каждым тестом."""
        self.client_instance = Client.objects.create(
            name='Тестовый Клиент',
            phone='+998901111111',
            balans=100,
            note='Тестовая заметка',
            created_at=timezone.now(),
        )

    def test_client_creation(self):
        """Проверка сейва клиента"""
        self.assertTrue(Client.objects.filter(phone=self.client_instance.phone).exists())

    def test_client_unique_phone(self):
        """Проверка уникальности номера телефона"""
        with self.assertRaises(Exception):
            Client.objects.create(
                name='Другой Клиент',
                phone=self.client_instance.phone,
                balans=50,
                note='',
            )
