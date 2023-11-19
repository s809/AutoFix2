# Generated by Django 4.2.5 on 2023-10-30 09:38

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0012_remove_repairorder_acceptedamount'),
    ]

    operations = [
        migrations.AddField(
            model_name='repairorder',
            name='acceptedAmount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Принятая сумма'),
        ),
    ]