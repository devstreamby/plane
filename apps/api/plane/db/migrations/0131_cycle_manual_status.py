from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0130_backfill_project_issue_type_levels")]

    operations = [
        migrations.AddField(
            model_name="cycle",
            name="manual_status",
            field=models.CharField(
                max_length=20,
                choices=[("DRAFT", "Draft"), ("CURRENT", "Current"), ("COMPLETED", "Completed")],
                default="DRAFT",
            ),
        ),
    ]
