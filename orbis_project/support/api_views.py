from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Ticket, TicketComment, Profile, Service, Notification, ActivityLog
from .serializers import TicketSerializer, TicketCommentSerializer, ProfileSerializer, ServiceSerializer, NotificationSerializer, ActivityLogSerializer

class IsOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.created_by == request.user

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]
    queryset = Ticket.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        ActivityLog.objects.create(
            user=self.request.user,
            action=f"Created ticket {serializer.instance.ticket_id}",
            ticket=serializer.instance
        )

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketCommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(ticket=ticket, author=request.user)
            ActivityLog.objects.create(
                user=request.user,
                action=f"Added comment to ticket {ticket.ticket_id}",
                ticket=ticket
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        if not request.user.is_staff:
            return Response({'error': 'Only staff can assign tickets'}, status=status.HTTP_403_FORBIDDEN)
        assigned_to_id = request.data.get('assigned_to')
        if assigned_to_id:
            ticket.assigned_to_id = assigned_to_id
            ticket.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f"Assigned ticket {ticket.ticket_id} to user {ticket.assigned_to.username}",
                ticket=ticket
            )
        return Response({'status': 'assigned'})

class TicketCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TicketCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = TicketComment.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return TicketComment.objects.all()
        return TicketComment.objects.filter(Q(ticket__created_by=user) & Q(is_internal=False))

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Notification.objects.all()

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ActivityLog.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ActivityLog.objects.all()
        return ActivityLog.objects.filter(user=user)