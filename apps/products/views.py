from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Product


class ProductListView(APIView):
    """Список товаров"""
    def get(self, request):
        products = Product.objects.all()[:10]
        data = [{"id": p.id, "name": p.name, "type_product": p.type_product,
                 "price": p.price, "track_inventory": p.track_inventory} for p in products]
        return Response(data)


class ProductDetailView(APIView):
    """Детали товара"""
    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            data = {
                "id": product.id,
                "name": product.name,
                "type_product": product.type_product,
                "price": product.price,
                "track_inventory": product.track_inventory,
                "description": product.description,
            }
            return Response(data)
        except Product.DoesNotExist:
            return Response({"error": "Товар не найден"}, status=status.HTTP_404_NOT_FOUND)
