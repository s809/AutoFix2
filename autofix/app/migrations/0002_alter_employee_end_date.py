# Generated by Django 4.2.5 on 2023-10-17 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='end_date',
            field=models.DateField(blank=True, verbose_name='Дата увольнения'),
        ),
    ]
