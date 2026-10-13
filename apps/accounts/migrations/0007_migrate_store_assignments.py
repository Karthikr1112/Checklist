from django.db import migrations


def forwards_func(apps, schema_editor):
    Store = apps.get_model('stores', 'Store')
    User = apps.get_model('accounts', 'User')

    for store in Store.objects.all():
        for attr in ('cluster_manager', 'store_manager', 'inventory_team', 'marketing_team'):
            user = getattr(store, attr, None)
            if user:
                user.assigned_stores.add(store)


def backwards_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_user_all_stores_access_user_assigned_stores'),
        ('stores', '0003_store_marketing_team'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
