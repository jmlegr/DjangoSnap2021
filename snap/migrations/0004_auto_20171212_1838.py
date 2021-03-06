# Generated by Django 2.0 on 2017-12-12 18:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('snap', '0003_auto_20171211_2240'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActionProgrammation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.IntegerField()),
                ('action', models.CharField(blank=True, max_length=30, null=True)),
                ('situation', models.CharField(blank=True, max_length=30, null=True)),
                ('typeMorph', models.CharField(blank=True, max_length=30, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Bounds',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='DroppedBlock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('block_id', models.IntegerField()),
                ('blockSpec', models.CharField(blank=True, max_length=100, null=True)),
                ('category', models.CharField(blank=True, max_length=30, null=True)),
                ('bounds', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='snap.Bounds')),
            ],
        ),
        migrations.CreateModel(
            name='Inputs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valeur', models.CharField(blank=True, max_length=30)),
                ('type', models.CharField(blank=True, max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Point',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('x', models.IntegerField()),
                ('y', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='droppedblock',
            name='inputs',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='snap.Inputs'),
        ),
        migrations.AddField(
            model_name='bounds',
            name='corner',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='corner', to='snap.Point'),
        ),
        migrations.AddField(
            model_name='bounds',
            name='origin',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='origin', to='snap.Point'),
        ),
        migrations.AddField(
            model_name='actionprogrammation',
            name='lastDroppedBlock',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='snap.DroppedBlock'),
        ),
        migrations.AddField(
            model_name='actionprogrammation',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
