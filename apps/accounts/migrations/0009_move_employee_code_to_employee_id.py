"""Older StyleHR logins stored the employee code (e.g. RR-10317) in full_name and the
numeric StyleHR id in employee_id. Move the code into employee_id; full_name is then
replaced with the real name on the user's next StyleHR login."""
import re

from django.db import migrations

EMPLOYEE_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,6}-\d+$")


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(source="STYLEHR"):
        name = (user.full_name or "").strip()
        if EMPLOYEE_CODE_RE.match(name) and user.employee_id != name:
            user.employee_id = name
            user.save(update_fields=["employee_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_user_vm_role_alter_user_role"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
