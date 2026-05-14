from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0002_alter_deliveryjournal_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='trip',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='orders',
                to='logistics.couriertrip',
                verbose_name='Рейс',
            ),
        ),
    ]
