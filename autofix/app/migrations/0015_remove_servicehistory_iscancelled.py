# Generated by Django 4.2.5 on 2023-11-19 08:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0014_remove_repairorder_acceptedamount_repairorder_ispaid'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='servicehistory',
            name='isCancelled',
        ),
    ]
