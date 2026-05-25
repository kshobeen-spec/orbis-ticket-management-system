from rest_framework import serializers
from .models import Ticket, TicketComment, Profile, Service, Notification, ActivityLog

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'user', 'bio', 'profile_photo', 'phone', 'role', 'services']

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

class TicketCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'author', 'author_username', 'comment', 'is_internal', 'created_at']

class TicketSerializer(serializers.ModelSerializer):
    comments = TicketCommentSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    assigned_to_username = serializers.CharField(source='assigned_to.username', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    is_within_sla = serializers.ReadOnlyField()

    class Meta:
        model = Ticket
        fields = ['id', 'ticket_id', 'title', 'description', 'status', 'priority', 'service', 'service_name', 'created_by', 'created_by_username', 'assigned_to', 'assigned_to_username', 'attachment', 'created_at', 'updated_at', 'closed_at', 'comments', 'is_within_sla']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class ActivityLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    ticket_id = serializers.CharField(source='ticket.ticket_id', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'user_username', 'action', 'ticket', 'ticket_id', 'created_at']