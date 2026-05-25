from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('help-center/', views.help_center, name='help_center'),
    path('help-center/submit/', views.submit_help_query_public, name='help_submit'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='profile_edit'),
    path('tickets/', views.tickets_list, name='tickets'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/export/', views.export_tickets_csv, name='export_tickets'),
    path('services/', views.services, name='services'),
    path('services/subscribe/<int:service_id>/', views.subscribe_service, name='service_subscribe'),
    path('services/unsubscribe/<int:service_id>/', views.unsubscribe_service, name='service_unsubscribe'),
    path('services/purchase/<int:service_id>/', views.purchase_service, name='service_purchase'),
    path('services/payment/<int:service_id>/', views.payment_confirmation, name='payment_confirm'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/assign/', views.assign_ticket, name='ticket_assign'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/tickets/<int:ticket_id>/', views.admin_ticket_detail, name='admin_ticket_detail'),
    
    # NEW: Engineer Resolution Workflow URLs
    path('engineer/tickets/<int:ticket_id>/', views.engineer_ticket_details, name='engineer_ticket_details'),
    path('engineer/dashboard/', views.engineer_dashboard_view, name='engineer_dashboard'),
    path('tickets/<int:ticket_id>/activity/', views.activity_timeline_view, name='activity_timeline'),
]
