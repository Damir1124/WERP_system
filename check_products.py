import sys
sys.path.insert(0, '.')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')
import django
django.setup()
from apps.products.models import Product
print('Products:')
for p in Product.objects.all():
    print(f'{p.id} {p.name} {p.type_product} {p.price}')