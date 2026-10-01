from django.db import migrations


def set_audience(apps, schema_editor):
    Template = apps.get_model("checklists", "ChecklistTemplate")
    Template.objects.filter(name__icontains="Inventory").update(audience="INVENTORY_TEAM")
    Template.objects.filter(name__icontains="Cluster Manager").update(audience="CLUSTER_MANAGER")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("checklists", "0002_checklisttemplate_audience"),
    ]

    operations = [
        migrations.RunPython(set_audience, noop),
    ]
