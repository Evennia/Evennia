# Generated by Django 2.1.8 on 2019-04-14 23:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0003_host'),
        ('accounts', '0009_auto_20190403_0745'),
    ]

    operations = [
        migrations.CreateModel(
            name='Login',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='LoginSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='login_records', to=settings.AUTH_USER_MODEL)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='account_logins', to='server.Host')),
            ],
        ),
        migrations.AddField(
            model_name='login',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logins', to='accounts.LoginSource'),
        ),
        migrations.AlterUniqueTogether(
            name='loginsource',
            unique_together={('account', 'host')},
        ),
    ]
