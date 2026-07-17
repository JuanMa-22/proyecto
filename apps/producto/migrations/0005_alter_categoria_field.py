from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('producto', '0004_rename_categoria_id_producto_categoria_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='producto',
            name='categoria',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, to='categoria.categoria', db_column='categoria_id')
        ),
    ]
