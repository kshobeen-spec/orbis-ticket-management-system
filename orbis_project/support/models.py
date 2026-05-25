from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    ROLE_CHOICES = [
        ('user', 'User'),
        ('support_engineer', 'Support Engineer'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    services = models.ManyToManyField('Service', blank=True, related_name='subscribers')

    def __str__(self):
        return self.user.username


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),  # New: Waiting for customer/external info
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    # Core fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    service = models.ForeignKey('Service', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    ticket_id = models.CharField(max_length=12, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to='ticket_attachments/', null=True, blank=True)
    
    # NEW: Engineer resolution workflow fields
    engineer_notes = models.TextField(
        blank=True,
        help_text='Internal engineering notes and troubleshooting steps. Not visible to customers.'
    )
    resolution_summary = models.TextField(
        blank=True,
        help_text='Summary of the resolution provided to the customer. Visible after ticket closure.'
    )
    resolution_date = models.DateTimeField(null=True, blank=True, help_text='When the ticket was resolved')
    last_updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tickets_updated'
    )

    def __str__(self):
        return f"#{self.id} {self.title}"

    @property
    def ticket_code(self):
        if not self.id:
            return "ORB-0000"
        return f"ORB-{self.id:04d}"

    @property
    def sla_deadline(self):
        sla_hours = {'low': 168, 'medium': 72, 'high': 24}[self.priority]  # hours
        return self.created_at + timedelta(hours=sla_hours)

    @property
    def is_within_sla(self):
        if self.status == 'closed':
            return self.closed_at <= self.sla_deadline
        return timezone.now() <= self.sla_deadline

    def save(self, *args, **kwargs):
        # Auto-generate a unique global ticket identifier if missing
        if not self.ticket_id:
            if self.pk:
                next_number = self.pk
            else:
                last_ticket = Ticket.objects.order_by('-id').first()
                next_number = last_ticket.id + 1 if last_ticket else 1
            self.ticket_id = f"ORB-{next_number:04d}"

        # automatically set closed_at when ticket is closed
        from django.utils import timezone
        try:
            old = Ticket.objects.get(pk=self.pk)
        except Ticket.DoesNotExist:
            old = None

        # If status has moved to closed and we don't already have closed_at, set it
        if self.status == 'closed' and not self.closed_at:
            self.closed_at = timezone.now()

        # keep closed_at if already set and ticket reopened (do not auto-clear)
        super().save(*args, **kwargs)


class Service(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic')
    features = models.TextField(blank=True, help_text='Comma-separated feature list')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def feature_list(self):
        if not self.features:
            return []
        return [f.strip() for f in self.features.split(',')]

    def __str__(self):
        return f"{self.name} ({self.get_plan_display()})"


class TicketNote(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    # New field: created_by (preferred canonical name) kept nullable for compatibility
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_notes')
    # Message body (kept as `body` for backwards compatibility with existing templates)
    body = models.TextField()
    # Flag indicating this note is a reply intended to be visible to the ticket owner
    is_admin_reply = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note #{self.id} on Ticket #{self.ticket.id}"


class InternalTicketNote(models.Model):
    """Admin/internal-only note attached to a Ticket. Not exposed to end users."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='internal_notes')
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='internal_ticket_notes')
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Internal Ticket Note'
        verbose_name_plural = 'Internal Ticket Notes'

    def __str__(self):
        return f"Internal Note #{self.id} on Ticket #{self.ticket.id}"


class ServicePurchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchased_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='purchases')
    purchased_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'service')

    def __str__(self):
        return f"{self.user.username} - {self.service.name}"


class HelpCenterQuery(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Query from {self.name} ({self.email})"


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal comments for staff only
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.ticket.ticket_id}"


class TicketReply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='replies')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ticket_replies')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='ticket_replies/', blank=True, null=True)
    is_internal_note = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Ticket Reply'
        verbose_name_plural = 'Ticket Replies'

    def __str__(self):
        return f"Reply #{self.id} on {self.ticket.ticket_id} by {self.sender.username}"

    @property
    def sender_role(self):
        if self.sender.is_staff:
            return 'Admin'
        try:
            role = self.sender.profile.role
        except Exception:
            role = 'customer'

        if role == 'support_engineer':
            return 'Engineer'
        if role == 'admin':
            return 'Admin'
        return 'Customer'


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=255)
    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action}"
