# Generated by Django 4.2.5 on 2023-12-12 17:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0029_alter_servicehistory_repair_order_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='repairorder',
            name='finish_until',
            field=models.DateField(blank=True, null=True, verbose_name='Завершить до'),
        ),
    ]
