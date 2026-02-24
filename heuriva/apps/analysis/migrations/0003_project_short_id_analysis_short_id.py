import secrets

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="short_id",
            field=models.CharField(
                default=None,
                editable=False,
                max_length=12,
                unique=True,
                verbose_name="short ID",
            ),
        ),
        migrations.AlterField(
            model_name="analysis",
            name="short_id",
            field=models.CharField(
                default=None,
                editable=False,
                max_length=12,
                unique=True,
                verbose_name="short ID",
            ),
        ),
    ]
