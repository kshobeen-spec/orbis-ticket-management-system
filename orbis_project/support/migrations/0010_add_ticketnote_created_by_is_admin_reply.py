from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('support', '0009_alter_helpcenterquery_id_alter_profile_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='ticketnote',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ticket_notes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ticketnote',
            name='is_admin_reply',
            field=models.BooleanField(default=False),
        ),
    ]
