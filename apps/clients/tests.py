from django.test import TestCase
from .models import Client
from faker import Faker

fake = Faker()

class ClientTestSave(TestCase):
    def setUp(self):
        '''Создание клиента перед каждым тестом'''
        self.client_instance = Client.objects.create(
            name=fake.name()[:85],
            phone=fake.phone_number()[:12],
            address=fake.address()[:120],
            balans=fake.random_int(min=-100, max=100),
            note=fake.text()[:255],
            created_at=fake.date()
        )

    def test_client_creation(self):
        """Проверка сейва клиента"""
        self.assertTrue(Client.objects.filter(address=self.client_instance.address).exists())

    def test_client_unique_phone(self):
        """Проверка уникальности номера телефона"""
        with self.assertRaises(Exception):
            Client.objects.create(
                name=fake.name(),
                phone=self.client_instance.phone,
                address=fake.address(),
                balans=fake.random_int(min=-100, max=100),
                note=fake.text(max_nb_chars=255),
                date_created=fake.date()
            )
