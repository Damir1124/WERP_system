from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from .models import Order, OrderItem
from apps.clients.models import Client, ClientAddress
from apps.products.models import Product


class OrderForm(forms.ModelForm):
    """Кастомная форма для создания заказа с удобным интерфейсом"""
    
    # Поля для быстрого создания клиента (если его нет в БД)
    client_phone = forms.CharField(
        max_length=13,
        required=True,
        label='Номер телефона',
        widget=forms.TextInput(attrs={
            'class': 'vTextField',
            'placeholder': '+998901234567',
            'style': 'width: 300px;'
        }),
        help_text='Введите номер телефона клиента (например, +998901234567)'
    )
    
    client_address = forms.CharField(
        max_length=120,
        required=True,
        label='Адрес доставки',
        widget=forms.TextInput(attrs={
            'class': 'vTextField',
            'placeholder': 'Улица, дом, квартира',
            'style': 'width: 500px;'
        }),
        help_text='Адрес доставки заказа'
    )
    
    class Meta:
        model = Order
        fields = ['payment_type', 'assigned_courier', 'note']
        widgets = {
            'payment_type': forms.Select(attrs={
                'class': 'vTextField',
                'style': 'width: 200px;'
            }),
            'assigned_courier': forms.Select(attrs={
                'class': 'vTextField',
                'style': 'width: 300px;'
            }),
            'note': forms.Textarea(attrs={
                'class': 'vLargeTextField',
                'rows': 3,
                'placeholder': 'Дополнительная информация о заказе',
                'style': 'width: 500px;'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Если редактируем существующий заказ
        if self.instance.pk and self.instance.client:
            if 'client_phone' in self.fields:
                self.fields['client_phone'].initial = self.instance.client.phone
            if 'client_address' in self.fields:
                self.fields['client_address'].initial = (
                    self.instance.delivery_address.address_text
                    if self.instance.delivery_address else ''
                )
        
        # Настройка лейблов и порядка полей.
        # Для DELIVERED/CANCELLED заказов часть полей readonly и отсутствует в self.fields.
        if 'payment_type' in self.fields:
            self.fields['payment_type'].label = 'Способ оплаты'
        if 'assigned_courier' in self.fields:
            self.fields['assigned_courier'].label = 'Назначить курьера (опционально)'
            self.fields['assigned_courier'].required = False
        if 'note' in self.fields:
            self.fields['note'].label = 'Примечание к заказу'
            self.fields['note'].required = False
    
    def clean_client_phone(self):
        """Валидация номера телефона"""
        phone = self.cleaned_data.get('client_phone')
        if phone:
            # Убираем все лишнее
            phone = phone.replace(' ', '').replace('-', '').replace('+', '')
            
            # Приводим к формату 998XXXXXXXXX (12 символов)
            if len(phone) == 9:
                phone = '998' + phone
            elif phone.startswith('8') and len(phone) == 10:
                phone = '998' + phone[1:]
            elif not phone.startswith('998'):
                raise forms.ValidationError('Номер должен начинаться с 998 или быть в формате 901234567')
            
            # Проверяем длину
            if len(phone) != 12:
                raise forms.ValidationError('Неверный формат номера. Ожидается: 998901234567 (12 цифр)')
        
        return phone
    
    def save(self, commit=True):
        """Сохранение заказа с автоматическим созданием/поиском клиента"""
        order = super().save(commit=False)

        # Если это новый заказ — присваиваем декоративный номер
        if not order.pk and order.display_number is None:
            from apps.logistics.services import get_next_display_number
            order.display_number = get_next_display_number()
        
        # Получаем данные клиента из формы
        phone = self.cleaned_data.get('client_phone')
        address = self.cleaned_data.get('client_address')
        
        # Ищем существующего клиента по телефону
        client, created = Client.objects.get_or_create(
            phone=phone,
            defaults={
                'name': f'Клиент {phone}',
            }
        )

        # Адрес доставки сохраняем в ClientAddress и привязываем к заказу
        if address:
            delivery_address, _ = ClientAddress.objects.get_or_create(
                client=client,
                address_text=address,
                defaults={'last_used_at': timezone.now()},
            )
            delivery_address.last_used_at = timezone.now()
            delivery_address.save()
            order.delivery_address = delivery_address
            # Снимок адреса прямо в заказ (история доставки не зависит от ClientAddress)
            order.delivery_address_text = delivery_address.address_text
            order.delivery_latitude = delivery_address.latitude
            order.delivery_longitude = delivery_address.longitude

        order.client = client
        
        if commit:
            order.save()
            self.save_m2m()
        
        return order


class OrderItemForm(forms.ModelForm):
    """Форма для позиции заказа"""
    
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'vTextField product-select',
                'style': 'width: 300px;'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'vIntegerField',
                'min': 1,
                'value': 1,
                'style': 'width: 80px;'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].label = 'Продукт'
        self.fields['quantity'].label = 'Количество'
        
        # Показываем только активные продукты с ценой
        self.fields['product'].queryset = Product.objects.all().order_by('type_product', 'name')


# Formset для управления несколькими позициями заказа
OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=3,  # Показываем 3 пустые формы для добавления продуктов
    can_delete=True,
    min_num=1,  # Минимум 1 продукт в заказе
    validate_min=True,
)
