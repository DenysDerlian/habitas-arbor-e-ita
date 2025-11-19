# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_add_ecosystem_services'),
    ]

    operations = [
        migrations.AddField(
            model_name='tree',
            name='origem',
            field=models.CharField(
                choices=[('nativa', 'Nativa'), ('exotica', 'Exótica'), ('desconhecida', 'Desconhecida')],
                default='desconhecida',
                max_length=20,
                verbose_name='Origem'
            ),
        ),
    ]

