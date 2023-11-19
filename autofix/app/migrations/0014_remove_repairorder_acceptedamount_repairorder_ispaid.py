# Generated by Django 4.2.5 on 2023-11-15 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0013_repairorder_acceptedamount'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='repairorder',
            name='acceptedAmount',
        ),
        migrations.AddField(
            model_name='repairorder',
            name='isPaid',
            field=models.BooleanField(default=False, verbose_name='Оплачено'),
        ),
    ]