import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workers', '0005_add_owner_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='worker',
            name='worker_type',
            field=models.CharField(choices=[('packer', 'Упаковщик'), ('courier', 'Курьер'), ('dispatcher', 'Диспетчер'), ('operator', 'Оператор'), ('owner', 'Владелец'), ('other', 'Прочие')], max_length=10, verbose_name='Тип сотрудника'),
        ),
    ]
