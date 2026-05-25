# Generated manual migration for adding InternalTicketNote and closed_at
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('support', '0010_add_ticketnote_created_by_is_admin_reply'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='InternalTicketNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note_text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='internal_notes', to='support.ticket')),
                ('admin_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='internal_ticket_notes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Internal Ticket Note',
                'verbose_name_plural': 'Internal Ticket Notes',
            },
        ),
    ]
