# Generated by Django 4.2.7 on 2023-11-04 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('newsbaitapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiment',
            name='randomization_seed',
            field=models.IntegerField(default=None),
        ),
    ]
