# Generated by Django 4.2.5 on 2023-12-09 18:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0028_alter_servicehistory_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicehistory',
            name='repair_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='app.repairorder', verbose_name='Заявка на ремонт'),
        ),
        migrations.AlterField(
            model_name='warehouserestock',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='app.warehouseitem', verbose_name='Расходник'),
        ),
        migrations.AlterField(
            model_name='warehouseuse',
            name='repair_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='app.repairorder', verbose_name='Заявка на ремонт'),
        ),
    ]
