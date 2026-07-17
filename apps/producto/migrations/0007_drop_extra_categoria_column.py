from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('producto', '0006_alter_producto_categoria'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""ALTER TABLE producto DROP COLUMN IF EXISTS categoria_id_id;""",
            reverse_sql="""-- No reverse operation (cannot restore dropped column)""",
        ),
    ]
