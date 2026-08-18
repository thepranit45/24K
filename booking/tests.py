from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Barber


class BarberDashboardAccessTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username='shop-manager',
            password='test-password',
            is_staff=True,
        )
        self.customer_user = get_user_model().objects.create_user(
            username='customer',
            password='test-password',
        )

    def test_dashboard_redirects_signed_out_visitors_to_login(self):
        response = self.client.get(reverse('barber_dashboard'))

        self.assertRedirects(
            response,
            '/auth/login/?next=/barber/dashboard/',
            fetch_redirect_response=False,
        )

    def test_dashboard_is_available_to_staff(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('barber_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_dashboard.html')
        self.assertContains(response, 'Barber Dashboard')

    def test_dashboard_blocks_non_staff_users(self):
        self.client.force_login(self.customer_user)

        response = self.client.get(reverse('barber_dashboard'))

        self.assertEqual(response.status_code, 403)

    def test_any_available_slots_close_when_prashant_is_off_duty(self):
        Barber.objects.filter(name='Prashant Borhade').update(is_active=False)

        response = self.client.get(reverse('get_time_slots'), {
            'date': timezone.localdate().isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['slots'], [])
