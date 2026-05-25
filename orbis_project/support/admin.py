from django.contrib import admin, messages
from django import forms
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.html import format_html

from .models import Ticket, Service, Profile, TicketNote, ServicePurchase, HelpCenterQuery, InternalTicketNote, TicketComment, TicketReply

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
	list_display = ('id', 'title', 'created_by', 'assigned_to', 'service', 'priority', 'status', 'status_colored', 'created_at')
	list_display_links = ('id', 'title')
	list_editable = ('status', 'priority', 'assigned_to')
	list_filter = ('status', 'priority', 'service', 'created_at', 'assigned_to')
	search_fields = ('title', 'description', 'created_by__username')
	ordering = ('-created_at',)
	readonly_fields = ('created_at', 'closed_at')
	actions = ['mark_open', 'mark_in_progress', 'mark_resolved', 'mark_closed', 'assign_to_me']

	def status_colored(self, obj):
		colors = {
			'open': 'red',
			'in_progress': 'orange',
			'resolved': 'green',
			'closed': 'gray',
		}
		color = colors.get(obj.status, 'black')
		return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
	status_colored.short_description = 'Status'
	status_colored.admin_order_field = 'status'

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		if request.user.is_superuser:
			return qs
		return qs.filter(assigned_to=request.user) | qs.filter(created_by=request.user)

	def get_list_filter(self, request):
		list_filter = super().get_list_filter(request)
		if request.user.is_superuser:
			return list_filter + ('assigned_to',)
		return list_filter

	def save_model(self, request, obj, form, change):
		if not change:  # Creating new ticket
			obj.created_by = request.user
		if obj.status == 'closed' and not obj.closed_at:
			obj.closed_at = timezone.now()
		super().save_model(request, obj, form, change)

	# Method to display user's email
	def created_by_email(self, obj):
		return obj.created_by.email if obj.created_by.email else '-'
	created_by_email.short_description = 'User Email'

	def get_form(self, request, obj=None, **kwargs):
		"""Dynamically create form based on whether we're adding or editing."""
		form = super().get_form(request, obj, **kwargs)
		
		# Only add confirm_reopen for closed tickets being edited
		if obj and obj.status == 'closed':
			# Add the field to the existing form
			form.base_fields['confirm_reopen'] = forms.BooleanField(
				required=False, 
				label='Confirm reopen (allow changing from Closed)'
			)
		
		return form

	def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
		"""Customize the form for add vs change view."""
		return super().changeform_view(request, object_id, form_url, extra_context)

	# status badge is injected client-side via admin_custom.js to allow styling

	class Media:
		css = {
			'all': ('admin/admin_custom.css',)
		}

		js = ('admin/admin_custom.js',)

	# Bulk actions to change ticket status
	def mark_open(self, request, queryset):
		queryset.update(status='open')
		self.message_user(request, "Selected tickets marked as Open.")
	mark_open.short_description = "Mark selected tickets as OPEN"

	def mark_in_progress(self, request, queryset):
		queryset.update(status='in_progress')
		self.message_user(request, "Selected tickets marked as In Progress.")
	mark_in_progress.short_description = "Mark selected tickets as IN_PROGRESS"

	def mark_resolved(self, request, queryset):
		queryset.update(status='resolved')
		self.message_user(request, "Selected tickets marked as Resolved.")
	mark_resolved.short_description = "Mark selected tickets as RESOLVED"

	def mark_closed(self, request, queryset):
		for t in queryset:
			t.status = 'closed'
			t.closed_at = timezone.now()
			t.save()
		self.message_user(request, "Selected tickets marked as Closed.")
	mark_closed.short_description = "Mark selected tickets as CLOSED"

	def assign_to_me(self, request, queryset):
		for t in queryset:
			t.assigned_to = request.user
			t.save()
		self.message_user(request, "Selected tickets assigned to you.")
	assign_to_me.short_description = "Assign selected tickets to me"

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
	list_display = ('name', 'plan', 'price')
	search_fields = ('name', 'description')

@admin.register(TicketNote)
class TicketNoteAdmin(admin.ModelAdmin):
	list_display = ('id', 'ticket', 'created_by', 'author', 'is_admin_reply', 'created_at')
	list_filter = ('is_admin_reply', 'created_at')
	search_fields = ('body', 'created_by__username', 'author__username')


class TicketCommentInline(admin.TabularInline):
	model = TicketComment
	fields = ('author', 'comment', 'is_internal', 'created_at')
	readonly_fields = ('created_at',)
	extra = 0
	can_delete = True

class InternalTicketNoteInline(admin.TabularInline):
	model = InternalTicketNote
	fields = ('admin_user', 'note_text', 'created_at')
	readonly_fields = ('created_at',)
	extra = 1

# attach inline to TicketAdmin
TicketAdmin.inlines = (TicketCommentInline, InternalTicketNoteInline)

# register InternalTicketNote so it's manageable in admin separately if needed
admin.site.register(InternalTicketNote)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'email', 'phone', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')
    
    def email(self, obj):
        return obj.user.email if obj.user.email else '-'
    email.short_description = 'Email'


@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'sender', 'is_internal_note', 'created_at')
    list_filter = ('is_internal_note', 'created_at')
    search_fields = ('ticket__ticket_id', 'sender__username', 'message')

admin.site.register(ServicePurchase)
admin.site.register(HelpCenterQuery)
