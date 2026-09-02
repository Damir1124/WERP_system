from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.utils import timezone
from .models import Client, ClientAddress
from .serializers import ClientAddressSerializer


class ClientListView(APIView):
    """Список клиентов"""
    def get(self, request):
        clients = Client.objects.all()[:10]
        data = [{"id": c.id, "name": c.name, "phone": c.phone,
                 "balans": c.balans} for c in clients]
        return Response(data)


class ClientDetailView(APIView):
    """Детали клиента"""
    def get(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)
            data = {
                "id": client.id,
                "name": client.name,
                "phone": client.phone,
                "balans": client.balans,
                "latitude": client.latitude,
                "longitude": client.longitude,
                "tg_id": client.tg_id,
            }
            return Response(data)
        except Client.DoesNotExist:
            return Response({"error": "Клиент не найден"}, status=status.HTTP_404_NOT_FOUND)


class ClientOrderHistoryView(APIView):
    """История заказов клиента"""
    def get(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)
            # Используем связанные заказы через ForeignKey
            orders = client.order_set.all()[:10]
            data = [{"id": o.id, "status": o.status, "payment_type": o.payment_type,
                     "created_at": o.created_at} for o in orders]
            return Response({"client": client.name, "orders": data})
        except Client.DoesNotExist:
            return Response({"error": "Клиент не найден"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_client_addresses(request, phone):
    """
    Получить до 3-х адресов клиента по номеру телефона.
    Адреса отсортированы по last_used_at (последний использованный первым).
    
    GET /api/clients/addresses/<phone>/
    
    Response:
    {
        "addresses": [
            {
                "id": 1,
                "address_text": "ул. Навои, 15",
                "latitude": 41.311151,
                "longitude": 69.279737,
                "last_used_at": "2026-07-11T10:30:00Z",
                "created_at": "2026-07-01T08:00:00Z"
            },
            ...
        ]
    }
    """
    # Нормализуем телефон (убираем +, пробелы, дефисы) — как в ClientSearchView
    normalized_phone = phone.replace('+', '').replace(' ', '').replace('-', '')

    client = (
        Client.objects.filter(phone=phone).first()
        or Client.objects.filter(phone=normalized_phone).first()
    )
    if not client:
        return Response({'addresses': []})

    # Получаем до 3-х адресов, отсортированных по last_used_at
    addresses = client.addresses.all()[:3]
    serializer = ClientAddressSerializer(addresses, many=True)
    return Response({'addresses': serializer.data})


@api_view(['POST'])
def save_client_address(request):
    """
    Сохранить или обновить адрес клиента.
    
    Логика:
    1. Если адрес с таким текстом уже существует — обновляем координаты и last_used_at
    2. Если адрес новый — создаём новую запись
    3. Если адресов больше 3-х — удаляем самый старый
    
    POST /api/clients/addresses/save/
    
    Body:
    {
        "client_id": 1,
        "address_text": "ул. Навои, 15",
        "latitude": 41.311151,
        "longitude": 69.279737
    }
    
    Response:
    {
        "status": "ok",
        "address_id": 1,
        "action": "created" | "updated"
    }
    """
    client_id = request.data.get('client_id')
    address_text = request.data.get('address_text', '').strip()
    label = request.data.get('label', '').strip()
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not client_id:
        return Response(
            {'error': 'client_id обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return Response(
            {'error': 'Клиент не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Проверяем, существует ли уже такой адрес (по тексту)
    if address_text:
        existing = client.addresses.filter(address_text=address_text).first()
    else:
        # Если текста нет, ищем по координатам
        existing = None
        if latitude and longitude:
            existing = client.addresses.filter(
                latitude=latitude,
                longitude=longitude
            ).first()
    
    if existing:
        # Обновляем существующий адрес
        existing.address_text = address_text
        existing.label = label
        existing.latitude = latitude
        existing.longitude = longitude
        existing.last_used_at = timezone.now()
        existing.save()
        
        return Response({
            'status': 'ok',
            'address_id': existing.id,
            'action': 'updated'
        })
    else:
        # Создаём новый адрес
        new_address = ClientAddress.objects.create(
            client=client,
            label=label,
            address_text=address_text,
            latitude=latitude,
            longitude=longitude,
            last_used_at=timezone.now()
        )
        
        # Если адресов больше 3, удаляем самый старый БЕЗ заказов
        addresses = client.addresses.all()
        if addresses.count() > 3:
            # Не трогаем адреса, на которые висят заказы (orders__isnull=True)
            oldest_unused = (
                client.addresses
                .filter(orders__isnull=True)
                .order_by('last_used_at', 'created_at')
                .first()
            )
            if oldest_unused:
                oldest_unused.delete()
            # иначе все адреса заняты заказами — оставляем 4-й, не удаляем привязанные
        
        return Response({
            'status': 'ok',
            'address_id': new_address.id,
            'action': 'created'
        })


@api_view(['POST'])
def delete_client_address(request):
    """
    Удалить адрес клиента.
    
    POST /api/clients/addresses/delete/
    
    Body:
    {
        "address_id": 1
    }
    
    Response:
    {
        "status": "ok",
        "deleted": true
    }
    """
    address_id = request.data.get('address_id')
    if not address_id:
        return Response(
            {'error': 'address_id обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        address = ClientAddress.objects.get(id=address_id)
    except ClientAddress.DoesNotExist:
        return Response(
            {'error': 'Адрес не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    address.delete()
    return Response({
        'status': 'ok',
        'deleted': True
    })


@api_view(['POST'])
def update_client_profile(request):
    """
    Обновить профиль клиента (имя, телефон, адрес).
    
    POST /api/clients/profile/update/
    
    Body:
    {
        "client_id": 1,
        "name": "Иван",
        "phone": "+998901234567"
    }
    
    Response:
    {
        "status": "ok",
        "client_id": 1
    }
    """
    client_id = request.data.get('client_id')
    if not client_id:
        return Response(
            {'error': 'client_id обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return Response(
            {'error': 'Клиент не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    name = request.data.get('name')
    phone = request.data.get('phone')
    
    if name is not None:
        client.name = name.strip()
    if phone is not None:
        client.phone = phone.strip()
    
    client.save()
    return Response({
        'status': 'ok',
        'client_id': client.id,
        'name': client.name,
        'phone': client.phone,
    })
