# Generated manually — add CourierShift expenses (ShiftExpense).
# Corresponds to apps/logistics/models.py :: ShiftExpense

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0011_delete_deliveryjournal_alter_couriershift_courier'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShiftExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(max_length=255, verbose_name='Причина расхода')),
                ('amount', models.IntegerField(verbose_name='Стоимость')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('shift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to='logistics.couriershift', verbose_name='Смена')),
            ],
            options={
                'verbose_name': 'Расход смены',
                'verbose_name_plural': 'Расходы смен',
                'ordering': ['created_at'],
            },
        ),
    ]