from django.contrib import admin
from .models import DeliveryReport


@admin.register(DeliveryReport)
class DeliveryReportAdmin(admin.ModelAdmin):
    list_display = ("id", "summary", "payment", "cooler", "accessory", "bottle", "water", "note")
    list_filter = ("payment",)
    search_fields = ("id", "note")

    readonly_fields = ("summary",)

    autocomplete_fields = ("cooler", "accessory", "bottle", "water")

    fieldsets = (
        ("Основная информация", {
            "fields": ("note", "payment", "summary")
        }),
        ("Продукты", {
            "fields": ("cooler", "accessory", "bottle", "water")
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.summary = obj.calculate_summary()  # Пересчитываем сумму перед сохранением
        super().save_model(request, obj, form, change)


from django.contrib import admin
from .models import DeliveryLog


@admin.register(DeliveryLog)
class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ("courier_name", "action", "quantity", "date")
    list_filter = ("action", "date")
    search_fields = ("courier_name__full_name",)  # Поиск по имени курьера

    autocomplete_fields = ("courier_name",)

    fieldsets = (
        ("Основная информация", {
            "fields": ("courier_name", "action", "quantity", "date")
        }),
    )
