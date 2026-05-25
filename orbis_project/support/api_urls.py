from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import TicketViewSet, TicketCommentViewSet, ProfileViewSet, ServiceViewSet, NotificationViewSet, ActivityLogViewSet

router = DefaultRouter()
router.register(r'tickets', TicketViewSet)
router.register(r'comments', TicketCommentViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'activity-logs', ActivityLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]