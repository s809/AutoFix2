# Generated by Django 4.2.5 on 2023-12-04 10:45

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0024_repairorder_vehicle_license_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='repairorder',
            name='vehicle_license_number',
            field=models.CharField(max_length=15, verbose_name='Гос. номер автомобиля'),
        ),
        migrations.AlterField(
            model_name='repairorder',
            name='vehicle_mileage',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(0)], verbose_name='Пробег автомобиля'),
        ),
        migrations.AlterField(
            model_name='repairorder',
            name='vehicle_vin',
            field=models.CharField(max_length=17, validators=[django.core.validators.MinLengthValidator(17)], verbose_name='VIN автомобиля'),
        ),
        *[migrations.RunSQL(
            f"""
            DROP TABLE IF EXISTS app_{model_name}_search;
            CREATE VIRTUAL TABLE app_{model_name}_search USING FTS5({fields});
            INSERT INTO app_{model_name}_search
                SELECT {fields}
                FROM app_{model_name}
                {" WHERE deleted_at IS NULL" if has_deleted_at else ""};
            """,
            f"""
            DROP TABLE IF EXISTS app_{model_name}_search;
            CREATE VIRTUAL TABLE app_{model_name}_search USING FTS5({prev_fields});
            INSERT INTO app_{model_name}_search
                SELECT {prev_fields}
                FROM app_{model_name}
                {" WHERE deleted_at IS NULL" if has_deleted_at else ""};
            """
        ) for [model_name, has_deleted_at, prev_fields, fields] in [
            ["repairorder", True,
             "client_name,vehicle_manufacturer,vehicle_model,complaints,diagnostic_results,comments,id,vehicle_license_number,vehicle_mileage,vehicle_vin",
             "client_name,vehicle_manufacturer,vehicle_model,complaints,diagnostic_results,comments,id,vehicle_license_number,vehicle_vin"],
        ]]
    ]