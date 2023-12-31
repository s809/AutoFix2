# Generated by Django 4.2.5 on 2023-10-29 11:43

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_alter_servicehistory_repair_order_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата увольнения'),
        ),
        migrations.AlterField(
            model_name='repairorder',
            name='finishDate',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения'),
        ),
        migrations.AlterField(
            model_name='repairorder',
            name='startDate',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата записи'),
        ),
        migrations.AlterField(
            model_name='servicehistory',
            name='finishDate',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения'),
        ),
        migrations.AlterField(
            model_name='servicehistory',
            name='startDate',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата начала'),
        ),
    ]
