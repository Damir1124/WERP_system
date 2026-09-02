"""
Тесты для IdentifyView и permissions на основе worker_type.

Обязательные сценарии (раздел 15 ТЗ):
1. Worker с ролью COURIER возвращает target_app = courier
2. Worker с ролью OPERATOR возвращает target_app = admin
3. Worker с ролью OWNER возвращает target_app = admin
4. Client без Worker возвращает target_app = client
5. Неизвестный Telegram ID возвращает target_app = registration
6. Если одинаковый tg_id есть в Worker и Client, выбирается Worker
7. Невалидный Telegram initData не даёт доступ
8. Клиент не получает доступ к курьерскому API
9. Клиент не получает доступ к Admin API
10. Курьер не получает доступ к Admin API
11. OPERATOR и OWNER получают доступ к API мини-статистики
12. Пользователь не может назначить себе COURIER, OPERATOR или OWNER через API
13. Регистрация нового клиента привязывает tg_id к Client
14. Launcher корректно обрабатывает ошибку backend и не открывает чужой интерфейс
"""
import json
import hmac
import hashlib
from unittest.mock import patch
from urllib.parse import urlencode

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.workers.models import Worker
from apps.clients.models import Client


def _make_fake_init_data(tg_id: int, bot_token: str = "test_token") -> str:
    """
    Создаёт подписанный initData для тестов.
    """
    user_data = json.dumps({"id": tg_id, "first_name": "Test", "last_name": "User"})
    params = {
        "query_id": "test_query_id",
        "user": user_data,
        "auth_date": "1700000000",
        "hash": "test_hash",
    }
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_params)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_value
    return urlencode(params)


class IdentifyViewTests(TestCase):
    """Тесты для IdentifyView (/api/bot/identify/)"""

    def setUp(self):
        self.client = APIClient()
        self.identify_url = reverse('bot_bridge:identify')

        self.worker_courier = Worker.objects.create(
            full_name="Курьер Тест",
            phone="+998901234567",
            worker_type=Worker.WorkerType.COURIER,
            tg_id=1001,
        )
        self.worker_operator = Worker.objects.create(
            full_name="Оператор Тест",
            phone="+998901234568",
            worker_type=Worker.WorkerType.OPERATOR,
            tg_id=1002,
        )
        self.worker_owner = Worker.objects.create(
            full_name="Владелец Тест",
            phone="+998901234569",
            worker_type=Worker.WorkerType.OWNER,
            tg_id=1003,
        )
        self.client_user = Client.objects.create(
            name="Клиент Тест",
            phone="+998901234570",
            tg_id=2001,
        )

    def _call_identify(self, tg_id=None, init_data=None):
        headers = {}
        params = {}
        if init_data:
            headers['HTTP_X_TELEGRAM_INIT_DATA'] = init_data
        if tg_id is not None:
            params['tg_id'] = tg_id
        return self.client.get(self.identify_url, params, **headers)

    # ─── Сценарий 1: COURIER → target_app = courier ─────────────────────────
    def test_courier_returns_courier_app(self):
        """Worker с ролью COURIER возвращает target_app = courier"""
        response = self._call_identify(tg_id=1001)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'COURIER')
        self.assertEqual(data['target_app'], 'courier')
        self.assertEqual(data['bot_role'], 'courier')
        self.assertEqual(data['worker_id'], self.worker_courier.id)
        self.assertTrue(data['authenticated'])

    # ─── Сценарий 2: DISPATCHER → target_app = admin ────────────────────────
    def test_operator_returns_operator_app(self):
        """Worker с ролью OPERATOR возвращает target_app = operator"""
        response = self._call_identify(tg_id=1002)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'OPERATOR')
        self.assertEqual(data['target_app'], 'operator')
        self.assertEqual(data['bot_role'], 'operator')
        self.assertEqual(data['worker_id'], self.worker_operator.id)

    # ─── Сценарий 3: OWNER → target_app = admin ─────────────────────────────
    def test_owner_returns_admin_app(self):
        """Worker с ролью OWNER возвращает target_app = admin"""
        response = self._call_identify(tg_id=1003)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'OWNER')
        self.assertEqual(data['target_app'], 'admin')
        self.assertEqual(data['bot_role'], 'owner')
        self.assertEqual(data['worker_id'], self.worker_owner.id)

    # ─── Сценарий 4: Client без Worker → target_app = client ────────────────
    def test_client_returns_client_app(self):
        """Client без Worker возвращает target_app = client"""
        response = self._call_identify(tg_id=2001)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'CLIENT')
        self.assertEqual(data['target_app'], 'client')
        self.assertEqual(data['bot_role'], 'client')
        self.assertEqual(data['client_id'], self.client_user.id)
        self.assertIsNone(data['worker_id'])

    # ─── Сценарий 5: Неизвестный → target_app = client (бесшовный вход) ─────
    def test_unknown_returns_client_app(self):
        """Неизвестный Telegram ID идёт в клиентский Mini App (бесшовный вход по tg_id)"""
        response = self._call_identify(tg_id=99999)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'UNKNOWN')
        self.assertEqual(data['target_app'], 'client')
        self.assertEqual(data['bot_role'], 'client')
        self.assertFalse(data['authenticated'])

    # ─── Сценарий 6: Приоритет Worker над Client ────────────────────────────
    def test_worker_priority_over_client(self):
        """Если одинаковый tg_id есть в Worker и Client, выбирается Worker"""
        Client.objects.create(
            name="Клиент-дублёр",
            phone="+998901234571",
            tg_id=1001,
        )
        response = self._call_identify(tg_id=1001)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'COURIER')
        self.assertEqual(data['target_app'], 'courier')
        self.assertEqual(data['worker_id'], self.worker_courier.id)
        self.assertIsNone(data['client_id'])

    # ─── Сценарий 7: Невалидный initData ────────────────────────────────────
    @override_settings(BOT_TOKEN="test_token", BOT_BRIDGE_VERIFY_INIT_DATA=True)
    def test_invalid_init_data_returns_401(self):
        """Невалидный Telegram initData не даёт доступ (при включённой проверке)"""
        response = self._call_identify(init_data="invalid_data")
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)

    # ─── Сценарий 7b: Валидный initData работает ────────────────────────────
    @patch('apps.bot_bridge.views.verify_telegram_init_data', return_value=True)
    @patch('apps.bot_bridge.views.extract_user_id_from_init_data', return_value=1001)
    def test_valid_init_data_works(self, mock_extract, mock_verify):
        """Валидный initData работает"""
        init_data = _make_fake_init_data(tg_id=1001)
        response = self._call_identify(init_data=init_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'COURIER')

    # ─── Сценарий 8: Клиент не получает доступ к курьерскому API ────────────
    def test_client_cannot_access_courier_api(self):
        """Клиент не получает доступ к курьерскому API (403)"""
        response = self.client.get(
            reverse('bot_bridge:courier_profile'),
            **{'HTTP_X_TELEGRAM_ID': '2001'}
        )
        self.assertEqual(response.status_code, 403)

    # ─── Сценарий 9: Клиент не получает доступ к Admin API ──────────────────
    def test_client_cannot_access_admin_api(self):
        """Клиент не получает доступ к Admin API (403)"""
        response = self.client.get(
            reverse('bot_bridge:admin_stats_today'),
            **{'HTTP_X_TELEGRAM_ID': '2001'}
        )
        self.assertEqual(response.status_code, 403)

    # ─── Сценарий 10: Курьер не получает доступ к Admin API ─────────────────
    def test_courier_cannot_access_admin_api(self):
        """Курьер не получает доступ к Admin API (403)"""
        response = self.client.get(
            reverse('bot_bridge:admin_stats_today'),
            **{'HTTP_X_TELEGRAM_ID': '1001'}
        )
        self.assertEqual(response.status_code, 403)

    # ─── Сценарий 11: DISPATCHER и OWNER получают доступ к Admin API ────────
    def test_operator_can_access_admin_api(self):
        """OPERATOR получает доступ к Admin API"""
        response = self.client.get(
            reverse('bot_bridge:admin_stats_today'),
            **{'HTTP_X_TELEGRAM_ID': '1002'}
        )
        self.assertEqual(response.status_code, 200)

    def test_owner_can_access_admin_api(self):
        """OWNER получает доступ к Admin API"""
        response = self.client.get(
            reverse('bot_bridge:admin_stats_today'),
            **{'HTTP_X_TELEGRAM_ID': '1003'}
        )
        self.assertEqual(response.status_code, 200)

    # ─── Сценарий 12: Нельзя назначить себе роль через API ──────────────────
    def test_cannot_self_assign_role_via_api(self):
        """Пользователь не может назначить себе COURIER, DISPATCHER или OWNER через API"""
        response = self.client.post(
            '/api/bot/identify/',
            {'tg_id': 1001, 'worker_type': 'owner'},
            **{'HTTP_X_TELEGRAM_ID': '1001'}
        )
        self.assertEqual(response.status_code, 405)

    # ─── Сценарий 13: Регистрация клиента привязывает tg_id ─────────────────
    def test_client_registration_binds_tg_id(self):
        """Регистрация нового клиента привязывает tg_id к Client"""
        tg_id = 9999
        response = self.client.post(
            reverse('bot_bridge:client_register'),
            {
                'name': 'Новый Клиент',
                'tg_id': tg_id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'created')

        client = Client.objects.filter(tg_id=tg_id).first()
        self.assertIsNotNone(client)
        self.assertEqual(client.name, 'Новый Клиент')

    # ─── Сценарий 13b: Приоритет Worker при регистрации клиента ─────────────
    def test_client_register_worker_priority(self):
        """Регистрация клиента не создаёт дубль для работника (приоритет Worker)"""
        response = self.client.post(
            reverse('bot_bridge:client_register'),
            {
                'name': 'Дубль',
                'tg_id': 1001,  # tg_id курьера из setUp
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'worker')
        self.assertEqual(data['worker_id'], self.worker_courier.id)
        self.assertFalse(data['registered'])
        # Дубль Client не создан
        self.assertFalse(Client.objects.filter(tg_id=1001).exists())

    # ─── Сценарий 14: Launcher обрабатывает ошибку backend ──────────────────
    def test_launcher_error_handling(self):
        """Launcher корректно обрабатывает ошибку backend (400)"""
        response = self.client.get(self.identify_url)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)


class IdentifyViewInitDataTests(TestCase):
    """Тесты для IdentifyView с initData"""

    def setUp(self):
        self.client = APIClient()
        self.identify_url = reverse('bot_bridge:identify')

        self.worker = Worker.objects.create(
            full_name="Тестовый Курьер",
            phone="+998901234560",
            worker_type=Worker.WorkerType.COURIER,
            tg_id=5001,
        )

    @patch('apps.bot_bridge.views.verify_telegram_init_data', return_value=True)
    @patch('apps.bot_bridge.views.extract_user_id_from_init_data', return_value=5001)
    def test_identify_with_init_data_header(self, mock_extract, mock_verify):
        """IdentifyView работает с initData в заголовке"""
        init_data = _make_fake_init_data(tg_id=5001)
        response = self.client.get(
            self.identify_url,
            **{'HTTP_X_TELEGRAM_INIT_DATA': init_data}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'COURIER')
        self.assertEqual(data['worker_id'], self.worker.id)

    def test_identify_without_tg_id_and_init_data(self):
        """IdentifyView без tg_id и initData возвращает 400"""
        response = self.client.get(self.identify_url)
        self.assertEqual(response.status_code, 400)


class WorkerTypeTests(TestCase):
    """Тесты для worker_type"""

    def setUp(self):
        self.worker = Worker.objects.create(
            full_name="Тест",
            phone="+998901234561",
            worker_type=Worker.WorkerType.COURIER,
            tg_id=6001,
        )

    def test_worker_type_choices(self):
        """worker_type принимает COURIER, OWNER, OPERATOR"""
        self.assertEqual(self.worker.worker_type, Worker.WorkerType.COURIER)
        self.worker.worker_type = Worker.WorkerType.OPERATOR
        self.worker.save()
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.worker_type, Worker.WorkerType.OPERATOR)

    def test_packer_worker_returns_worker_role(self):
        """Worker с типом PACKER возвращает role=WORKER, target_app=None"""
        w = Worker.objects.create(
            full_name="Упаковщик",
            phone="+998901234563",
            worker_type=Worker.WorkerType.PACKER,
            tg_id=7001,
        )
        client = APIClient()
        response = client.get(
            reverse('bot_bridge:identify'),
            {'tg_id': 7001},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['role'], 'WORKER')
        self.assertIsNone(data['target_app'])