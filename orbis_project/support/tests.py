from django.test import TestCase, Client
from django.contrib.auth.models import User
from support.models import Profile, Ticket, Service, TicketNote, TicketReply
from django.urls import reverse


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_profile_created_on_user_creation(self):
        """Test that a Profile is auto-created when a User is created."""
        profile = Profile.objects.get(user=self.user)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.role, 'customer')

    def test_profile_role_choices(self):
        """Test that profile role defaults to customer."""
        profile = self.user.profile
        self.assertIn(profile.role, ['customer', 'engineer', 'admin'])


class TicketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            status='open',
            priority='high',
            created_by=self.user
        )

    def test_ticket_creation(self):
        """Test that a Ticket can be created."""
        self.assertEqual(self.ticket.title, 'Test Ticket')
        self.assertEqual(self.ticket.status, 'open')
        self.assertEqual(self.ticket.priority, 'high')

    def test_ticket_str(self):
        """Test Ticket string representation."""
        self.assertEqual(str(self.ticket), f'#{self.ticket.id} Test Ticket')

    def test_ticket_assignment(self):
        """Test assigning a ticket to a user."""
        engineer = User.objects.create_user(username='engineer', password='pass123')
        engineer.profile.role = 'engineer'
        engineer.profile.save()
        
        self.ticket.assigned_to = engineer
        self.ticket.save()
        
        self.assertEqual(self.ticket.assigned_to, engineer)


class TicketNoteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            status='open',
            priority='medium',
            created_by=self.user
        )
        self.note = TicketNote.objects.create(
            ticket=self.ticket,
            author=self.user,
            body='Test note body'
        )

    def test_ticket_note_creation(self):
        """Test that a TicketNote can be created."""
        self.assertEqual(self.note.body, 'Test note body')
        self.assertEqual(self.note.ticket, self.ticket)
        self.assertEqual(self.note.author, self.user)


class ServiceModelTest(TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            name='IT Support',
            description='24/7 IT support',
            plan='pro',
            features='Email support,Phone support',
            price=49.99
        )

    def test_service_creation(self):
        """Test that a Service can be created."""
        self.assertEqual(self.service.name, 'IT Support')
        self.assertEqual(self.service.plan, 'pro')

    def test_service_feature_list(self):
        """Test that feature_list parses features correctly."""
        features = self.service.feature_list()
        self.assertEqual(len(features), 2)
        self.assertIn('Email support', features)


class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'testuser'
        self.password = 'testpass123'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_login_view_get(self):
        """Test login page loads."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/login.html')

    def test_login_view_post_success(self):
        """Test successful login."""
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, 302)  # Redirect to profile

    def test_login_view_post_fail(self):
        """Test failed login."""
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stay on login page

    def test_signup_view_get(self):
        """Test signup page loads."""
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/signup.html')

    def test_signup_view_post_success(self):
        """Test successful signup."""
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'confirm_password': 'newpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to profile
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_signup_password_mismatch(self):
        """Test signup with mismatched passwords."""
        response = self.client.post(reverse('signup'), {
            'username': 'newuser2',
            'email': 'newuser2@example.com',
            'password': 'pass123',
            'confirm_password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser2').exists())


class TicketViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        self.ticket = Ticket.objects.create(
            title='Test Ticket',
            description='Test Description',
            created_by=self.user
        )

    def test_tickets_list_view(self):
        """Test tickets list view loads."""
        response = self.client.get(reverse('tickets'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/tickets.html')

    def test_ticket_create_view_get(self):
        """Test create ticket page loads."""
        response = self.client.get(reverse('ticket_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/create_ticket.html')

    def test_ticket_create_view_post(self):
        """Test creating a ticket."""
        response = self.client.post(reverse('ticket_create'), {
            'title': 'New Ticket',
            'description': 'New ticket description',
            'priority': 'high'
        })
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(Ticket.objects.filter(title='New Ticket').exists())

    def test_ticket_detail_view(self):
        """Test ticket detail page loads."""
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/ticket_detail.html')

    def test_ticket_export_csv(self):
        """Test CSV export."""
        response = self.client.get(reverse('export_tickets'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        # Create sample tickets
        for i in range(5):
            Ticket.objects.create(
                title=f'Ticket {i}',
                status='open' if i % 2 == 0 else 'resolved',
                priority='high' if i % 3 == 0 else 'medium',
                created_by=self.user
            )

    def test_dashboard_view(self):
        """Test dashboard view loads."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/dashboard.html')

    def test_dashboard_timeframe_filter(self):
        """Test dashboard with timeframe parameter."""
        response = self.client.get(reverse('dashboard') + '?timeframe=7')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['timeframe'], '7')


class TicketSaveAndAdminActionsTest(TestCase):
    def setUp(self):
        from django.test import RequestFactory
        from django.contrib import admin
        from django.contrib.messages.storage.fallback import FallbackStorage
        from support.admin import TicketAdmin

        self.factory = RequestFactory()
        self.staff = User.objects.create_user(username='staff', password='staffpass')
        self.staff.is_staff = True
        self.staff.save()
        self.user = User.objects.create_user(username='user1', password='pass')
        self.ticket1 = Ticket.objects.create(title='T1', description='d', created_by=self.user)
        self.ticket2 = Ticket.objects.create(title='T2', description='d2', created_by=self.user)
        # instantiate admin
        self.admin_instance = TicketAdmin(Ticket, admin.site)

        def build_request():
            request = self.factory.get('/')
            request.session = {}
            request._messages = FallbackStorage(request)
            return request

        self.build_request = build_request

    def test_closed_sets_closed_at_on_save(self):
        t = Ticket.objects.create(title='CloseMe', created_by=self.user)
        self.assertIsNone(t.closed_at)
        t.status = 'closed'
        t.save()
        t.refresh_from_db()
        self.assertIsNotNone(t.closed_at)

    def test_mark_closed_action_sets_closed_at(self):
        # simulate request with staff user
        request = self.build_request()
        request.user = self.staff
        qs = Ticket.objects.filter(id__in=[self.ticket1.id, self.ticket2.id])
        # call admin action
        self.admin_instance.mark_closed(request, qs)
        for t in qs:
            t.refresh_from_db()
            self.assertEqual(t.status, 'closed')
            self.assertIsNotNone(t.closed_at)

    def test_assign_to_me_action_assigns(self):
        request = self.build_request()
        request.user = self.staff
        qs = Ticket.objects.filter(id=self.ticket1.id)
        self.admin_instance.assign_to_me(request, qs)
        self.ticket1.refresh_from_db()
        self.assertEqual(self.ticket1.assigned_to, self.staff)


class TicketReplyConversationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = User.objects.create_user(username='customer', password='pass123')
        self.engineer = User.objects.create_user(username='engineer', password='pass123')
        self.engineer.profile.role = 'support_engineer'
        self.engineer.profile.save()
        self.ticket = Ticket.objects.create(
            title='Conversation Ticket',
            description='Need help with login.',
            created_by=self.customer,
            assigned_to=self.engineer,
        )

    def test_ticket_reply_model_creation(self):
        reply = TicketReply.objects.create(
            ticket=self.ticket,
            sender=self.customer,
            message='I am still seeing the login error.'
        )

        self.assertEqual(reply.ticket, self.ticket)
        self.assertEqual(reply.sender, self.customer)
        self.assertFalse(reply.is_internal_note)

    def test_customer_can_add_public_reply_and_internal_notes_are_hidden(self):
        self.client.login(username='customer', password='pass123')

        response = self.client.post(reverse('ticket_detail', args=[self.ticket.id]), {
            'message': 'Customer update message.',
            'attachment': '',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TicketReply.objects.filter(ticket=self.ticket, sender=self.customer, message='Customer update message.').exists())

        staff_login = self.client.login(username='engineer', password='pass123')
        self.assertTrue(staff_login)

        response = self.client.post(reverse('ticket_detail', args=[self.ticket.id]), {
            'message': 'Internal troubleshooting note.',
            'is_internal_note': 'on',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TicketReply.objects.filter(ticket=self.ticket, sender=self.engineer, message='Internal troubleshooting note.', is_internal_note=True).exists())

        self.client.logout()
        self.client.login(username='customer', password='pass123')
        detail_response = self.client.get(reverse('ticket_detail', args=[self.ticket.id]))

        self.assertContains(detail_response, 'Customer update message.')
        self.assertNotContains(detail_response, 'Internal troubleshooting note.')
