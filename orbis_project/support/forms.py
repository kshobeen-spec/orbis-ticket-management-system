import re
from django import forms
from django.core.validators import RegexValidator
from .models import Ticket, HelpCenterQuery, Profile, TicketComment, InternalTicketNote, TicketReply

# Phone regex validator - accepts various formats like:
# +1 555 555 5555, +1-555-555-5555, 555-555-5555, (555) 555-5555, 5555555555
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$|^\+?[\d\s\-()]{9,20}$',
    message="Phone number must be entered in a valid format (e.g., +1 555 555 5555, 555-555-5555, (555) 555-5555)."
)


class ProfileForm(forms.ModelForm):
    phone = forms.CharField(
        validators=[phone_regex],
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+1 555 555 5555',
            'pattern': r'^\+?1?\d{9,15}$|^\+?[\d\s\-()]{9,20}$',
            'title': 'Enter a valid phone number (e.g., +1 555 555 5555)'
        })
    )

    class Meta:
        model = Profile
        fields = ['bio', 'profile_photo', 'phone']


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'service', 'priority', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Brief title of the issue'}),
            'description': forms.Textarea(attrs={'rows':6, 'placeholder':'Describe the issue in detail...'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class TicketReplyForm(forms.ModelForm):
    def __init__(self, *args, show_internal_note=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not show_internal_note:
            self.fields.pop('is_internal_note', None)

    class Meta:
        model = TicketReply
        fields = ['message', 'attachment', 'is_internal_note']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Reply to the customer or add an update...',
                'class': 'form-control conversation-textarea'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control conversation-file-input'
            }),
            'is_internal_note': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'message': 'Message',
            'attachment': 'Attachment (optional)',
            'is_internal_note': 'Mark as internal note',
        }


class HelpCenterQueryForm(forms.ModelForm):
    class Meta:
        model = HelpCenterQuery
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your Name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your Email', 'class': 'form-control'}),
            'message': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Your Question or Message', 'class': 'form-control'}),
        }


# ============================================================================
# NEW: Engineer Resolution Workflow Forms
# ============================================================================

class TicketStatusForm(forms.ModelForm):
    """
    Form for engineers/admins to update ticket status.
    Provides dropdown with available statuses.
    """
    class Meta:
        model = Ticket
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control form-select',
                'id': 'ticket-status-select'
            }),
        }
        labels = {
            'status': 'Ticket Status',
        }


class EngineerNotesForm(forms.ModelForm):
    """
    Form for engineers to add internal troubleshooting notes.
    These notes are NOT visible to customers.
    """
    class Meta:
        model = Ticket
        fields = ['engineer_notes']
        widgets = {
            'engineer_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Add internal troubleshooting notes, diagnostic steps, and technical details here. These are not visible to customers.',
                'id': 'engineer-notes-textarea'
            }),
        }
        labels = {
            'engineer_notes': 'Internal Engineer Notes',
        }


class ResolutionSummaryForm(forms.ModelForm):
    """
    Form for engineers to add the resolution summary.
    This is visible to customers once ticket is resolved/closed.
    """
    class Meta:
        model = Ticket
        fields = ['resolution_summary']
        widgets = {
            'resolution_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Provide a clear, customer-friendly summary of how the issue was resolved. This will be visible to the customer.',
                'id': 'resolution-summary-textarea'
            }),
        }
        labels = {
            'resolution_summary': 'Resolution Summary (Visible to Customer)',
        }


class EngineerResolutionForm(forms.ModelForm):
    """
    Comprehensive form combining status update, engineer notes, and resolution summary.
    Used in the main ticket resolution workflow.
    """
    class Meta:
        model = Ticket
        fields = ['status', 'engineer_notes', 'resolution_summary']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control form-select',
            }),
            'engineer_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Internal troubleshooting steps and technical notes...',
            }),
            'resolution_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Customer-facing resolution summary...',
            }),
        }
        labels = {
            'status': 'Update Status',
            'engineer_notes': 'Internal Engineer Notes',
            'resolution_summary': 'Resolution Summary (Customer Visible)',
        }


class InternalCommentForm(forms.ModelForm):
    """
    Form for adding internal-only comments to a ticket.
    Comments are never visible to customers.
    """
    class Meta:
        model = InternalTicketNote
        fields = ['note_text']
        widgets = {
            'note_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Add an internal comment. This is not visible to the customer.',
                'id': 'internal-comment-textarea'
            }),
        }
        labels = {
            'note_text': 'Internal Comment (Staff Only)',
        }


class TicketAssignmentForm(forms.ModelForm):
    """
    Form for admins to assign/reassign a ticket to an engineer.
    Only shows users with engineer or admin roles.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show engineers and admins in the assignment dropdown
        from django.contrib.auth.models import User
        engineer_profiles = Profile.objects.filter(
            role__in=['support_engineer', 'admin']
        ).values_list('user_id', flat=True)
        self.fields['assigned_to'].queryset = User.objects.filter(
            id__in=engineer_profiles
        ).order_by('first_name', 'last_name')
    
    class Meta:
        model = Ticket
        fields = ['assigned_to']
        widgets = {
            'assigned_to': forms.Select(attrs={
                'class': 'form-control form-select',
            }),
        }
        labels = {
            'assigned_to': 'Assign to Engineer',
        }
