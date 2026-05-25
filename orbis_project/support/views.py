from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.utils.http import url_has_allowed_host_and_scheme
from datetime import timedelta
from django.utils import timezone
from collections import defaultdict
from django.db.models import Q
import json
from django.core.mail import EmailMessage
import csv
from django.http import HttpResponse, HttpResponseForbidden
import re

from .models import Ticket, Service, Profile, TicketNote, ServicePurchase, HelpCenterQuery, TicketComment, Notification, ActivityLog, TicketReply
from .models import InternalTicketNote
from .forms import TicketForm, HelpCenterQueryForm, TicketReplyForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Helper function to notify staff
def notify_staff(message, exclude_user=None):
    staff_users = User.objects.filter(Q(is_staff=True) | Q(profile__role='admin'))
    if exclude_user:
        staff_users = staff_users.exclude(id=exclude_user.id)
    for user in staff_users:
        Notification.objects.create(user=user, message=message)

# Phone regex pattern - matches various formats like: +1 555 555 5555, 555-555-5555, (555) 555-5555
PHONE_PATTERN = re.compile(r'^\+?1?\d{9,15}$|^\+?[\d\s\-()]{9,20}$')


def home(request):
    return render(request, "support/home.html")


def login_view(request):
    next_param = request.GET.get('next', '')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # respect `next` when present and safe
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard")
        messages.error(request, "Invalid credentials. Please try again.")
    return render(request, "support/login.html", {"next": next_param})


def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "support/signup.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, "support/signup.html")

        user = User.objects.create_user(username=username, password=password, email=email)
        login(request, user)
        return redirect("profile")

    return render(request, "support/signup.html")


@login_required
def profile(request):
    return render(request, "support/profile.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


class CustomPasswordResetView(PasswordResetView):
    template_name = 'support/password_reset.html'
    email_template_name = 'support/password_reset_email.html'
    success_url = '/password-reset/done/'

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'support/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'support/password_reset_confirm.html'
    success_url = '/password-reset/complete/'

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'support/password_reset_complete.html'


@login_required
def edit_profile(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        profile_photo = request.FILES.get("profile_photo")
        bio = request.POST.get("bio")
        phone = request.POST.get("phone")

        # Server-side phone validation
        if phone and phone.strip():
            phone = phone.strip()
            if not PHONE_PATTERN.match(phone):
                messages.error(request, "Invalid phone number format. Please use a valid format (e.g., +1 555 555 5555, 555-555-5555).")
                return render(request, "support/edit_profile.html", {"user": request.user})

        user = request.user
        if username:
            user.username = username
        if email:
            user.email = email
        if password:
            user.set_password(password)
        user.save()

        # Save profile details (ensure profile exists)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if profile_photo:
            profile.profile_photo = profile_photo
        if bio is not None:
            profile.bio = bio
        if phone is not None:
            profile.phone = phone.strip() if phone else ''
        profile.save()

        if password:
            update_session_auth_hash(request, user)

        messages.success(request, "Profile updated.")
        return redirect("profile")

    return render(request, "support/edit_profile.html", {"user": request.user})


@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('/admin/')

    # Timeframe filter
    timeframe = request.GET.get('timeframe', '30')
    try:
        days = int(timeframe)
    except (ValueError, TypeError):
        days = 30

    cutoff_date = timezone.now() - timedelta(days=days)

    # Determine user role and filter tickets accordingly
    try:
        user_role = request.user.profile.role
    except Exception:
        user_role = 'customer'

    print(f"DEBUG DASHBOARD: User {request.user.username}, is_staff: {request.user.is_staff}, role: {user_role}")

    user_tickets = list(Ticket.objects.filter(created_by=request.user, created_at__gte=cutoff_date).order_by('id'))
    for index, ticket in enumerate(user_tickets, start=1):
        ticket.user_ticket_number = index

    total_tickets = len(user_tickets)
    open_tickets = sum(1 for ticket in user_tickets if ticket.status == 'open')
    in_progress = sum(1 for ticket in user_tickets if ticket.status == 'in_progress')
    resolved = sum(1 for ticket in user_tickets if ticket.status == 'resolved')
    closed = sum(1 for ticket in user_tickets if ticket.status == 'closed')

    # Get purchased services
    purchased_services = ServicePurchase.objects.filter(user=request.user)
    cloud_storage_purchased = purchased_services.filter(service__name='Cloud Storage').exists()
    
    metrics = {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'in_progress': in_progress,
        'resolved': resolved,
        'closed': closed,
        'purchased_services': purchased_services.count(),
        'cloud_storage_status': 'Active' if cloud_storage_purchased else 'Not Purchased',
    }

    recent_tickets = sorted(user_tickets, key=lambda ticket: ticket.created_at, reverse=True)[:6]

    status_breakdown = {
        'Open': open_tickets,
        'In Progress': in_progress,
        'Resolved': resolved,
        'Closed': closed,
    }

    # Priority breakdown
    low = sum(1 for ticket in user_tickets if ticket.priority == 'low')
    medium = sum(1 for ticket in user_tickets if ticket.priority == 'medium')
    high = sum(1 for ticket in user_tickets if ticket.priority == 'high')
    priority_breakdown = {
        'Low': low,
        'Medium': medium,
        'High': high,
    }

    # Time-series: tickets created per day
    tickets_by_day = defaultdict(int)
    for ticket in user_tickets:
        day = ticket.created_at.date()
        tickets_by_day[day] += 1

    # Fill in missing days
    all_days = {}
    for i in range(days, -1, -1):
        day = (timezone.now() - timedelta(days=i)).date()
        all_days[str(day)] = tickets_by_day.get(day, 0)

    timeseries_data = json.dumps(all_days)

    return render(request, 'support/dashboard.html', {
        'metrics': metrics,
        'recent_tickets': recent_tickets,
        'status_breakdown': status_breakdown,
        'priority_breakdown': priority_breakdown,
        'timeframe': timeframe,
        'timeseries_data': timeseries_data,
        'purchased_services': purchased_services,
        'cloud_storage_purchased': cloud_storage_purchased,
    })


@login_required
def tickets_list(request):
    # If user is engineer or staff, show all tickets; otherwise only own tickets
    try:
        user_role = request.user.profile.role
    except Exception:
        user_role = 'customer'

    print(f"DEBUG: User {request.user.username}, is_staff: {request.user.is_staff}, role: {user_role}")

    if request.user.is_staff:
        qs = Ticket.objects.all().order_by('-created_at')
        print(f"DEBUG: Showing all tickets, count: {qs.count()}")
    elif user_role == 'engineer':
        qs = Ticket.objects.filter(Q(created_by=request.user) | Q(assigned_to=request.user)).order_by('-created_at')
        print(f"DEBUG: Showing assigned tickets, count: {qs.count()}")
    else:
        qs = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
        print(f"DEBUG: Showing own tickets, count: {qs.count()}")

    # Filters
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    q = request.GET.get('q')

    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(ticket_id__icontains=q) | Q(created_by__username__icontains=q))

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(qs, 10)
    try:
        tickets = paginator.page(page)
    except PageNotAnInteger:
        tickets = paginator.page(1)
    except EmptyPage:
        tickets = paginator.page(paginator.num_pages)

    context = {
        'tickets': tickets,
        'paginator': paginator,
        'status_choices': Ticket.STATUS_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'current_filters': {'status': status or '', 'priority': priority or '', 'q': q or ''}
    }
    return render(request, 'support/tickets.html', context)


@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created ticket {ticket.ticket_id}",
                ticket=ticket
            )
            notify_staff(f"New ticket {ticket.ticket_id} created by {request.user.username}: {ticket.title}")
            messages.success(request, 'Ticket created successfully.')
            return redirect('tickets')
    else:
        form = TicketForm()
    return render(request, 'support/create_ticket.html', {'form': form})


def services(request):
    # ensure demo services exist (idempotent)
    demo = [
        {
            'name': 'IT Support',
            'description': '24/7 IT support for your organization.',
            'plan': 'pro',
            'features': 'Email support,Phone support,On-site visits',
            'price': 49.99,
        },
        {
            'name': 'Customer Support Desk',
            'description': 'Full customer support desk solution.',
            'plan': 'enterprise',
            'features': 'Multichannel support,SLAs,Reporting',
            'price': 199.00,
        },
        {
            'name': 'Software Maintenance',
            'description': 'Ongoing maintenance for software products.',
            'plan': 'basic',
            'features': 'Bug fixes,Minor updates',
            'price': 19.99,
        },
        {
            'name': 'Website Management',
            'description': 'Professional website management and updates.',
            'plan': 'pro',
            'features': 'Content updates,Performance monitoring,SSL management',
            'price': 79.99,
        },
        {
            'name': 'Cloud & Hosting Support',
            'description': 'Expert support for cloud and hosting infrastructure.',
            'plan': 'enterprise',
            'features': 'Infrastructure monitoring,Auto-scaling setup,24/7 support',
            'price': 149.99,
        },
        {
            'name': 'Technical Consultation',
            'description': 'Expert technical advice and planning services.',
            'plan': 'pro',
            'features': 'Architecture review,Performance optimization,Security audit',
            'price': 99.99,
        },
        {
            'name': 'Cloud Storage',
            'description': 'Secure cloud storage with collaboration features.',
            'plan': 'enterprise',
            'features': '500GB storage,Version control,File sharing,Encryption',
            'price': 29.99,
        },
    ]
    for s in demo:
        Service.objects.get_or_create(name=s['name'], defaults=s)

    all_services = Service.objects.all()
    subscribed = []
    purchased = []
    
    if request.user.is_authenticated:
        # ensure profile exists (signals should handle this)
        try:
            subscribed = list(request.user.profile.services.all())
        except Profile.DoesNotExist:
            subscribed = []
        
        # Get purchased services
        purchased = list(ServicePurchase.objects.filter(user=request.user).values_list('service_id', flat=True))

    return render(request, 'support/services.html', {
        'services': all_services, 
        'subscribed': subscribed, 
        'purchased': purchased,
        'is_authenticated': request.user.is_authenticated,
    })


@login_required
def subscribe_service(request, service_id):
    if request.method == 'POST':
        service = Service.objects.filter(id=service_id).first()
        if not service:
            messages.error(request, 'Service not found.')
            return redirect('services')
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.services.add(service)
        messages.success(request, f'Subscribed to {service.name}.')
    return redirect('services')


@login_required
def unsubscribe_service(request, service_id):
    if request.method == 'POST':
        service = Service.objects.filter(id=service_id).first()
        if not service:
            messages.error(request, 'Service not found.')
            return redirect('services')
        try:
            profile = request.user.profile
            profile.services.remove(service)
            messages.success(request, f'Unsubscribed from {service.name}.')
        except Profile.DoesNotExist:
            pass
    return redirect('services')


@login_required
@login_required
def ticket_detail(request, ticket_id):
    ticket = Ticket.objects.filter(id=ticket_id).select_related('created_by', 'assigned_to').first()
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('tickets')

    try:
        user_role = request.user.profile.role
    except Exception:
        user_role = 'customer'

    can_manage = request.user.is_staff or user_role in ['support_engineer', 'admin']
    can_view = (
        request.user.is_staff
        or user_role == 'admin'
        or ticket.created_by == request.user
        or ticket.assigned_to == request.user
    )

    if not can_view:
        return HttpResponseForbidden('Forbidden')

    if request.method == 'POST':
        if 'message' in request.POST:
            form = TicketReplyForm(request.POST, request.FILES, show_internal_note=can_manage)
            if form.is_valid():
                reply = form.save(commit=False)
                reply.ticket = ticket
                reply.sender = request.user
                if not can_manage:
                    reply.is_internal_note = False
                reply.save()

                ticket.last_updated_by = request.user
                ticket.updated_at = timezone.now()
                ticket.save(update_fields=['last_updated_by', 'updated_at'])

                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Added {'internal ' if reply.is_internal_note else ''}reply to ticket {ticket.ticket_id}",
                    ticket=ticket,
                )

                if reply.is_internal_note:
                    staff_users = User.objects.filter(Q(is_staff=True) | Q(profile__role='admin')).exclude(id=request.user.id)
                    for staff_user in staff_users:
                        Notification.objects.create(
                            user=staff_user,
                            message=f"Internal note added to ticket {ticket.ticket_id}: {reply.message[:80]}"
                        )
                    messages.success(request, 'Internal note added.')
                else:
                    if request.user == ticket.created_by:
                        if ticket.assigned_to and ticket.assigned_to != request.user:
                            Notification.objects.create(
                                user=ticket.assigned_to,
                                message=f"Customer replied to ticket {ticket.ticket_id}: {reply.message[:80]}"
                            )
                        else:
                            notify_staff(f"Customer replied to ticket {ticket.ticket_id}: {reply.message[:80]}", exclude_user=request.user)
                    elif ticket.created_by != request.user:
                        Notification.objects.create(
                            user=ticket.created_by,
                            message=f"New reply added to ticket {ticket.ticket_id}: {reply.message[:80]}"
                        )
                    messages.success(request, 'Reply added successfully.')

                return redirect('ticket_detail', ticket_id=ticket.id)

            messages.error(request, 'Please add a message before sending your reply.')
            return redirect('ticket_detail', ticket_id=ticket.id)

        if 'submit_status' in request.POST and can_manage:
            new_status = request.POST.get('status')
            if new_status in dict(Ticket.STATUS_CHOICES):
                old_status = ticket.status
                ticket.status = new_status
                ticket.save()
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Changed status of ticket {ticket.ticket_id} from {old_status} to {new_status}",
                    ticket=ticket,
                )
                if ticket.created_by != request.user:
                    Notification.objects.create(
                        user=ticket.created_by,
                        message=f"Ticket {ticket.ticket_id} status changed to {ticket.get_status_display()}"
                    )
                if ticket.assigned_to and ticket.assigned_to != request.user:
                    Notification.objects.create(
                        user=ticket.assigned_to,
                        message=f"Ticket {ticket.ticket_id} status changed to {ticket.get_status_display()}"
                    )
                messages.success(request, 'Status updated.')
                return redirect('ticket_detail', ticket_id=ticket.id)

        if 'assign_to' in request.POST and can_manage:
            assign_to_id = request.POST.get('assign_to')
            if assign_to_id:
                try:
                    assign_to_user = User.objects.get(id=assign_to_id)
                    ticket.assigned_to = assign_to_user
                    ticket.save()
                    ActivityLog.objects.create(
                        user=request.user,
                        action=f"Assigned ticket {ticket.ticket_id} to {assign_to_user.username}",
                        ticket=ticket,
                    )
                    Notification.objects.create(
                        user=assign_to_user,
                        message=f"You have been assigned to ticket {ticket.ticket_id}: {ticket.title}"
                    )
                    messages.success(request, f'Assigned to {assign_to_user.username}.')
                except User.DoesNotExist:
                    messages.error(request, 'User not found.')
            else:
                ticket.assigned_to = None
                ticket.save()
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Unassigned ticket {ticket.ticket_id}",
                    ticket=ticket,
                )
                messages.success(request, 'Unassigned.')
            return redirect('ticket_detail', ticket_id=ticket.id)

    replies = ticket.replies.all() if can_manage else ticket.replies.filter(is_internal_note=False)
    engineers = User.objects.filter(Q(profile__role='support_engineer') | Q(profile__role='admin') | Q(is_staff=True)).distinct().order_by('username')
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'support/ticket_detail.html', {
        'ticket': ticket,
        'replies': replies,
        'engineers': engineers,
        'can_manage': can_manage,
        'reply_form': TicketReplyForm(show_internal_note=can_manage),
        'unread_notifications': unread_notifications,
    })


@login_required
def admin_dashboard(request):
    # only staff or support admins allowed
    try:
        role = request.user.profile.role
    except Exception:
        role = 'customer'

    from django.http import HttpResponseForbidden

    if not (request.user.is_staff or role == 'admin'):
        return HttpResponseForbidden('Forbidden')

    # filters
    status_filter = request.GET.get('status')
    service_filter = request.GET.get('service')
    assignee_filter = request.GET.get('assignee')

    qs = Ticket.objects.select_related('created_by', 'service', 'assigned_to').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if service_filter:
        try:
            sf = int(service_filter)
            qs = qs.filter(service_id=sf)
        except Exception:
            pass
    if assignee_filter:
        try:
            af = int(assignee_filter)
            qs = qs.filter(assigned_to_id=af)
        except Exception:
            pass

    total = Ticket.objects.count()
    open_count = Ticket.objects.filter(status='open').count()
    in_progress = Ticket.objects.filter(status='in_progress').count()
    closed = Ticket.objects.filter(status='closed').count()

    recent = qs[:10]

    # status breakdown for chart
    status_counts = {
        'Open': open_count,
        'In Progress': in_progress,
        'Closed': closed,
    }

    # per-engineer workload (assigned tickets)
    from django.db.models import Count
    engineers = User.objects.filter(profile__role='engineer') | User.objects.filter(is_staff=True)
    engineers = engineers.distinct()
    workload = engineers.annotate(assigned=Count('assigned_tickets')).order_by('-assigned')[:10]

    # services list for filter
    services = Service.objects.all()

    import json as _json

    return render(request, 'support/admin_dashboard.html', {
        'total': total,
        'open_count': open_count,
        'in_progress': in_progress,
        'closed': closed,
        'recent': recent,
        'status_counts_json': _json.dumps(status_counts),
        'workload': workload,
        'services': services,
        'engineers': engineers,
        'current_filters': {'status': status_filter or '', 'service': service_filter or '', 'assignee': assignee_filter or ''}
    })


@login_required
def admin_ticket_detail(request, ticket_id):
    try:
        role = request.user.profile.role
    except Exception:
        role = 'customer'

    from django.http import HttpResponseForbidden

    if not (request.user.is_staff or role == 'admin'):
        return HttpResponseForbidden('Forbidden')

    ticket = Ticket.objects.filter(id=ticket_id).select_related('created_by', 'service').first()
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('admin_dashboard')

    if request.method == 'POST':
        # change status (staff only)
        if 'status' in request.POST:
            if not request.user.is_staff:
                return HttpResponseForbidden('Forbidden')
            new_status = request.POST.get('status')
            if new_status in dict(Ticket.STATUS_CHOICES):
                ticket.status = new_status
                ticket.save()
                messages.success(request, 'Status updated.')
                return redirect('admin_ticket_detail', ticket_id=ticket.id)

        # add admin reply (visible to user)
        if 'reply' in request.POST:
            if not request.user.is_staff:
                return HttpResponseForbidden('Forbidden')
            body = request.POST.get('reply', '').strip()
            if body:
                TicketNote.objects.create(ticket=ticket, author=request.user, created_by=request.user, body=body, is_admin_reply=True)
                messages.success(request, 'Reply added to ticket.')
                return redirect('admin_ticket_detail', ticket_id=ticket.id)

        # add internal note (not visible to user)
        if 'internal_note' in request.POST:
            if not request.user.is_staff:
                return HttpResponseForbidden('Forbidden')
            body = request.POST.get('internal_note', '').strip()
            if body:
                InternalTicketNote.objects.create(ticket=ticket, admin_user=request.user, note_text=body)
                messages.success(request, 'Internal note added.')
                return redirect('admin_ticket_detail', ticket_id=ticket.id)

        # assign ticket to a user (admin can assign)
        if 'assign_to' in request.POST:
            if not request.user.is_staff:
                return HttpResponseForbidden('Forbidden')
            assignee_id = request.POST.get('assign_to')
            try:
                assignee_pk = int(assignee_id)
            except (ValueError, TypeError):
                assignee_pk = None
            assignee = User.objects.filter(id=assignee_pk).first() if assignee_pk else None
            if assignee:
                ticket.assigned_to = assignee
                ticket.save()
                messages.success(request, f'Assigned to {assignee.username}.')
            else:
                messages.error(request, 'Assignee not found.')
            return redirect('admin_ticket_detail', ticket_id=ticket.id)

    notes = ticket.notes.order_by('created_at')
    internal_notes = ticket.internal_notes.order_by('-created_at')

    # Provide list of support users for assignment dropdown
    users = User.objects.filter(is_staff=True) | User.objects.filter(profile__role='engineer')

    return render(request, 'support/admin_ticket_detail.html', {
        'ticket': ticket,
        'notes': notes,
        'internal_notes': internal_notes,
        'users': users,
    })


def send_assignment_email(ticket, assignee):
    """Send a placeholder email notification when a ticket is assigned."""
    try:
        subject = f"Ticket #{ticket.id} Assigned to You"
        body = f"""
Hello {assignee.username},

You have been assigned to the following ticket:

Ticket ID: #{ticket.id}
Title: {ticket.title}
Description: {ticket.description[:200]}...
Priority: {ticket.get_priority_display()}
Status: {ticket.get_status_display()}

Please log in to ORBiS to review and work on this ticket.

---
ORBiS Support System
        """
        # Placeholder: in production, configure EMAIL_BACKEND in settings.py
        # For now, this uses console EmailBackend which prints to stdout
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email='noreply@orbis.com',
            to=[assignee.email] if assignee.email else [],
        )
        email.send(fail_silently=True)
    except Exception as e:
        print(f"Error sending email: {e}")


@login_required
def assign_ticket(request, ticket_id):
    ticket = Ticket.objects.filter(id=ticket_id).select_related('created_by', 'assigned_to').first()
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('tickets')

    try:
        user_role = request.user.profile.role
    except Exception:
        user_role = 'customer'

    if not (request.user.is_staff or user_role == 'engineer'):
        messages.error(request, 'Permission denied.')
        return redirect('ticket_detail', ticket_id=ticket.id)

    if not (
        ticket.created_by == request.user
        or ticket.assigned_to == request.user
        or request.user.is_staff
    ):
        return HttpResponseForbidden('Forbidden')

    if request.method == 'POST':
        assignee_id = request.POST.get('assignee')
        if not assignee_id:
            messages.error(request, 'No assignee selected.')
        else:
            try:
                assignee_pk = int(assignee_id)
            except (ValueError, TypeError):
                assignee_pk = None

            assignee = User.objects.filter(id=assignee_pk).first() if assignee_pk else None
            if assignee:
                ticket.assigned_to = assignee
                ticket.save()
                # Send assignment email notification
                send_assignment_email(ticket, assignee)
                messages.success(request, f'Ticket assigned to {assignee.username}.')
            else:
                messages.error(request, 'Assignee not found.')

    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required
def export_tickets_csv(request):
    import csv
    from django.http import HttpResponse

    # Get tickets (same logic as tickets_list)
    try:
        user_role = request.user.profile.role
    except Exception:
        user_role = 'customer'

    print(f"DEBUG EXPORT: User {request.user.username}, is_staff: {request.user.is_staff}, role: {user_role}")

    if request.user.is_staff:
        qs = Ticket.objects.all().order_by('-created_at')
        print(f"DEBUG EXPORT: Showing all tickets, count: {qs.count()}")
    elif user_role == 'engineer':
        qs = Ticket.objects.filter(Q(created_by=request.user) | Q(assigned_to=request.user)).order_by('-created_at')
        print(f"DEBUG EXPORT: Showing assigned tickets, count: {qs.count()}")
    else:
        qs = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
        print(f"DEBUG EXPORT: Showing own tickets, count: {qs.count()}")

    # Apply same filters as tickets_list
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    q = request.GET.get('q')

    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(description__icontains=q)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Description', 'Status', 'Priority', 'Created By', 'Assigned To', 'Created At'])

    for ticket in qs:
        writer.writerow([
            ticket.id,
            ticket.title,
            ticket.description[:50] if ticket.description else '',
            ticket.get_status_display(),
            ticket.get_priority_display(),
            ticket.created_by.username,
            ticket.assigned_to.username if ticket.assigned_to else 'Unassigned',
            ticket.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


def about(request):
    return render(request, 'support/about.html')


def help_center(request):
    return render(request, 'support/help_center.html')


@login_required
def submit_help_query(request):
    if request.method == 'POST':
        form = HelpCenterQueryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! We have received your inquiry and will get back to you soon.')
            return redirect('help_center')
    else:
        form = HelpCenterQueryForm()
    return render(request, 'support/help_center.html', {'form': form})


def submit_help_query_public(request):
    if request.method == 'POST':
        form = HelpCenterQueryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! We have received your inquiry and will get back to you soon.')
            return redirect('help_center')
    else:
        form = HelpCenterQueryForm()
    return render(request, 'support/help_center.html', {'form': form})


@login_required
def purchase_service(request, service_id):
    if request.method == 'POST':
        service = Service.objects.filter(id=service_id).first()
        if not service:
            messages.error(request, 'Service not found.')
            return redirect('services')
        
        # Check if already purchased
        if ServicePurchase.objects.filter(user=request.user, service=service).exists():
            messages.info(request, f'You have already purchased {service.name}.')
            return redirect('services')
        
        # Create purchase record
        ServicePurchase.objects.create(user=request.user, service=service)
        messages.success(request, f'Successfully purchased {service.name}!')
        return redirect('services')
    
    service = Service.objects.filter(id=service_id).first()
    return render(request, 'support/payment.html', {'service': service})


@login_required
def payment_confirmation(request, service_id):
    service = Service.objects.filter(id=service_id).first()
    if not service:
        messages.error(request, 'Service not found.')
        return redirect('services')
    
    if request.method == 'POST':
        card_number = request.POST.get('card_number', '')
        expiry = request.POST.get('expiry', '')
        cvv = request.POST.get('cvv', '')
        
        # Dummy validation
        if not card_number or not expiry or not cvv:
            messages.error(request, 'All payment fields are required.')
            return render(request, 'support/payment.html', {'service': service})
        
        # Create purchase record (dummy payment success)
        purchase, created = ServicePurchase.objects.get_or_create(user=request.user, service=service)
        if created:
            messages.success(request, f'Payment successful! {service.name} has been added to your purchased services.')
        else:
            messages.info(request, f'You already own {service.name}.')
        
        return redirect('services')
    
    return render(request, 'support/payment.html', {'service': service})


# ============================================================================
# NEW: Engineer Resolution Workflow Views
# ============================================================================

@login_required
def engineer_ticket_details(request, ticket_id):
    """
    Comprehensive ticket detail page for engineers/admins with resolution management.
    
    Features:
    - Full ticket information display
    - Status update capability
    - Engineer notes (internal, not visible to customer)
    - Resolution summary (visible to customer)
    - Internal comment system
    - Activity timeline
    - Ticket assignment
    
    Access:
    - Only engineers/admins/staff can access
    - Or ticket creator can view
    """
    
    # Permission check
    try:
        user_role = request.user.profile.role
    except Profile.DoesNotExist:
        user_role = 'customer'
    
    ticket = Ticket.objects.select_related(
        'created_by', 'assigned_to', 'service', 'last_updated_by'
    ).prefetch_related(
        'comments', 'internal_notes', 'activity_logs'
    ).filter(id=ticket_id).first()
    
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('admin_dashboard' if request.user.is_staff else 'tickets')
    
    # Access control: allow creators, assigned engineers, staff, admins
    is_engineer_or_admin = request.user.is_staff or user_role in ['support_engineer', 'admin']
    is_ticket_creator = ticket.created_by == request.user
    is_assigned = ticket.assigned_to == request.user
    
    can_edit = is_engineer_or_admin
    can_view = is_engineer_or_admin or is_ticket_creator or is_assigned
    
    if not can_view:
        return HttpResponseForbidden('You do not have permission to view this ticket.')
    
    # Handle POST requests (form submissions)
    if request.method == 'POST' and can_edit:
        
        # Update resolution fields (engineer notes, resolution summary, status)
        if 'update_resolution' in request.POST:
            from .forms import EngineerResolutionForm
            form = EngineerResolutionForm(request.POST, instance=ticket)
            if form.is_valid():
                # Store the old status to check for status change
                old_status = Ticket.objects.get(pk=ticket.id).status
                
                # Save the ticket with updated fields
                ticket = form.save(commit=False)
                ticket.last_updated_by = request.user
                ticket.updated_at = timezone.now()
                
                # If status changed to 'resolved' or 'closed', set resolution_date
                if ticket.status in ['resolved', 'closed'] and not ticket.resolution_date:
                    ticket.resolution_date = timezone.now()
                
                ticket.save()
                
                # Log the activity
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Updated resolution for ticket {ticket.ticket_id}",
                    ticket=ticket
                )
                
                # Notify if status changed
                if old_status != ticket.status:
                    ActivityLog.objects.create(
                        user=request.user,
                        action=f"Changed ticket status from {old_status} to {ticket.status}",
                        ticket=ticket
                    )
                    # Create notification for customer
                    if ticket.created_by != request.user:
                        Notification.objects.create(
                            user=ticket.created_by,
                            message=f"Ticket {ticket.ticket_id} status changed to {ticket.get_status_display()}"
                        )
                
                messages.success(request, 'Ticket resolution updated successfully.')
                return redirect('engineer_ticket_details', ticket_id=ticket.id)
        
        # Add internal comment
        elif 'add_internal_comment' in request.POST:
            from .forms import InternalCommentForm
            form = InternalCommentForm(request.POST)
            if form.is_valid():
                internal_note = form.save(commit=False)
                internal_note.ticket = ticket
                internal_note.admin_user = request.user
                internal_note.save()
                
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Added internal comment to ticket {ticket.ticket_id}",
                    ticket=ticket
                )
                
                messages.success(request, 'Internal comment added successfully.')
                return redirect('engineer_ticket_details', ticket_id=ticket.id)
        
        # Assign ticket
        elif 'assign_ticket' in request.POST:
            from .forms import TicketAssignmentForm
            form = TicketAssignmentForm(request.POST, instance=ticket)
            if form.is_valid():
                old_assigned = ticket.assigned_to
                ticket = form.save(commit=False)
                ticket.last_updated_by = request.user
                ticket.save()
                
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Assigned ticket {ticket.ticket_id} to {ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'}",
                    ticket=ticket
                )
                
                # Notify the assigned engineer
                if ticket.assigned_to and ticket.assigned_to != request.user:
                    Notification.objects.create(
                        user=ticket.assigned_to,
                        message=f"You have been assigned to ticket {ticket.ticket_id}: {ticket.title}"
                    )
                
                messages.success(request, 'Ticket assignment updated.')
                return redirect('engineer_ticket_details', ticket_id=ticket.id)
    
    # Prepare forms for display
    from .forms import (
        EngineerResolutionForm, InternalCommentForm, 
        TicketAssignmentForm, TicketStatusForm
    )
    
    resolution_form = EngineerResolutionForm(instance=ticket) if can_edit else None
    internal_comment_form = InternalCommentForm() if can_edit else None
    assignment_form = TicketAssignmentForm(instance=ticket) if can_edit else None
    status_form = TicketStatusForm(instance=ticket) if can_edit else None
    
    # Get related data
    internal_notes = ticket.internal_notes.select_related('admin_user').order_by('-created_at')
    comments = ticket.comments.select_related('author').order_by('created_at')
    activity_logs = ActivityLog.objects.filter(ticket=ticket).select_related('user').order_by('-created_at')
    
    # Get customer info
    customer_profile = ticket.created_by.profile if hasattr(ticket.created_by, 'profile') else None
    
    # Calculate metrics
    time_elapsed = timezone.now() - ticket.created_at
    days_open = time_elapsed.days
    
    context = {
        'ticket': ticket,
        'can_edit': can_edit,
        'can_view': can_view,
        'is_engineer_or_admin': is_engineer_or_admin,
        'customer_profile': customer_profile,
        'internal_notes': internal_notes,
        'comments': comments,
        'activity_logs': activity_logs,
        'days_open': days_open,
        'resolution_form': resolution_form,
        'internal_comment_form': internal_comment_form,
        'assignment_form': assignment_form,
        'status_form': status_form,
        'status_choices': dict(Ticket.STATUS_CHOICES),
        'priority_classes': {
            'low': 'info',
            'medium': 'warning',
            'high': 'danger'
        }
    }
    
    return render(request, 'support/engineer_ticket_details.html', context)


@login_required
def engineer_dashboard_view(request):
    """
    Engineer-specific dashboard showing assigned tickets and resolution workload.
    """
    
    # Permission check
    try:
        user_role = request.user.profile.role
    except Profile.DoesNotExist:
        user_role = 'customer'
    
    is_engineer_or_admin = request.user.is_staff or user_role in ['support_engineer', 'admin']
    
    if not is_engineer_or_admin:
        return HttpResponseForbidden('Access denied. This dashboard is for engineers and admins only.')
    
    # Get assigned tickets
    assigned_tickets = Ticket.objects.filter(
        assigned_to=request.user
    ).select_related('created_by', 'service').order_by('-created_at')
    
    # Stats
    total_assigned = assigned_tickets.count()
    open_assigned = assigned_tickets.filter(status='open').count()
    in_progress = assigned_tickets.filter(status='in_progress').count()
    pending = assigned_tickets.filter(status='pending').count()
    resolved = assigned_tickets.filter(status='resolved').count()
    closed = assigned_tickets.filter(status='closed').count()
    
    # SLA status
    within_sla = sum(1 for t in assigned_tickets if t.is_within_sla)
    sla_at_risk = total_assigned - within_sla if total_assigned > 0 else 0
    
    # Recent activity
    recent_updates = ActivityLog.objects.filter(
        ticket__assigned_to=request.user
    ).select_related('ticket', 'user').order_by('-created_at')[:10]
    
    # Tickets needing attention (open or in_progress)
    urgent_tickets = assigned_tickets.filter(
        status__in=['open', 'in_progress'],
        priority='high'
    ).order_by('created_at')[:5]
    
    context = {
        'total_assigned': total_assigned,
        'open_assigned': open_assigned,
        'in_progress': in_progress,
        'pending': pending,
        'resolved': resolved,
        'closed': closed,
        'within_sla': within_sla,
        'sla_at_risk': sla_at_risk,
        'assigned_tickets': assigned_tickets[:15],
        'urgent_tickets': urgent_tickets,
        'recent_updates': recent_updates,
    }
    
    return render(request, 'support/engineer_dashboard.html', context)


@login_required  
def activity_timeline_view(request, ticket_id):
    """
    Display detailed activity timeline for a ticket.
    """
    
    try:
        user_role = request.user.profile.role
    except Profile.DoesNotExist:
        user_role = 'customer'
    
    ticket = Ticket.objects.filter(id=ticket_id).first()
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('tickets')
    
    # Permission check
    is_engineer_or_admin = request.user.is_staff or user_role in ['support_engineer', 'admin']
    is_ticket_creator = ticket.created_by == request.user
    is_assigned = ticket.assigned_to == request.user
    
    if not (is_engineer_or_admin or is_ticket_creator or is_assigned):
        return HttpResponseForbidden('You do not have permission to view this ticket.')
    
    # Get full activity timeline
    activity_logs = ActivityLog.objects.filter(
        ticket=ticket
    ).select_related('user').order_by('-created_at')
    
    context = {
        'ticket': ticket,
        'activity_logs': activity_logs,
    }
    
    return render(request, 'support/activity_timeline.html', context)

