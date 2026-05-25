# Manual migration to add phone field to Profile
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('support', '0011_internalnote_and_closedat'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='phone',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
