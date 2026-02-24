from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0003_project_short_id_analysis_short_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysis",
            name="sequence_number",
            field=models.PositiveIntegerField(
                editable=False,
                verbose_name="sequence number",
            ),
        ),
    ]
