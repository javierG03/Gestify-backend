from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("usuarios", "0006_documenttype_alter_customuser_city_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE usuarios_documenttype RENAME TO users_document_type;",
            reverse_sql="ALTER TABLE users_document_type RENAME TO usuarios_documenttype;",
        ),
    ]
