"""
Tests for the profile pages (A9).

Run with:  python manage.py test accounts
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from listings.models import Inquiry, Listing
from .models import UnleasedUser, UserReview


class ProfileTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.parul = UnleasedUser.objects.create_user(
            username='parul', password='Sublease#2026', email='parul@illinois.edu',
            first_name='Parul', budget_min=600, budget_max=800, preferred_area='Near the Quad',
            sleep_schedule='night')
        cls.seeker = UnleasedUser.objects.create_user(
            username='seeker', password='Sublease#2026', email='seeker@gmail.com')
        cls.listing = Listing.objects.create(
            lister=cls.parul, title='Room near Green St', description='x', monthly_rent=650,
            street_address='1 Test St', bedrooms=1, bathrooms=1,
            available_from=date(2027, 1, 1), available_until=date(2027, 5, 1))
        Inquiry.objects.create(listing=cls.listing, seeker=cls.seeker, message='Hi', status='accepted')
        UserReview.objects.create(reviewer=cls.seeker, reviewee=cls.parul, rating=4, comment='Quick replies')

    # ---- own profile ----
    def test_profile_needs_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('account_login')))

    def test_own_profile_shows_private_preferences_and_activity(self):
        self.client.force_login(self.parul)
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, 'Parul')
        self.assertContains(response, '.edu verified')
        self.assertContains(response, '$600 to $800/mo')
        self.assertContains(response, 'Near the Quad')
        self.assertContains(response, 'parul@illinois.edu')
        self.assertContains(response, '100%')                     # 1 of 1 inquiries answered
        self.assertContains(response, 'Quick replies')
        self.assertContains(response, 'Edit profile')

    def test_navbar_links_to_profile(self):
        self.client.force_login(self.parul)
        self.assertContains(self.client.get(reverse('home')), reverse('accounts:profile'))

    # ---- public profile ----
    def test_public_profile_hides_private_details(self):
        response = self.client.get(reverse('accounts:public_profile', args=['parul']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Room near Green St')
        self.assertContains(response, 'Night owl')
        self.assertNotContains(response, 'parul@illinois.edu')
        self.assertNotContains(response, '$600 to $800')
        self.assertNotContains(response, 'Edit profile')

    def test_public_profile_of_yourself_redirects_to_your_profile(self):
        self.client.force_login(self.parul)
        self.assertRedirects(self.client.get(reverse('accounts:public_profile', args=['parul'])),
                             reverse('accounts:profile'))

    def test_unknown_user_is_404(self):
        self.assertEqual(self.client.get(reverse('accounts:public_profile', args=['nobody'])).status_code, 404)

    def test_listing_page_links_to_the_lister_profile(self):
        response = self.client.get(self.listing.get_absolute_url())
        self.assertContains(response, reverse('accounts:public_profile', args=['parul']))

    # ---- editing ----
    def test_edit_saves_changes(self):
        self.client.force_login(self.seeker)
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Sam', 'last_name': '', 'bio': 'Grad student',
            'budget_min': '500', 'budget_max': '700', 'move_in_from': '2027-01-01',
            'move_in_until': '2027-02-01', 'preferred_area': 'Green St',
            'sleep_schedule': 'early', 'cleanliness': '', 'noise_level': '', 'guests_policy': '',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.seeker.refresh_from_db()
        self.assertEqual(self.seeker.first_name, 'Sam')
        self.assertEqual(self.seeker.budget_max, 700)
        self.assertFalse(self.seeker.pets_ok)

    def test_edit_rejects_inverted_budget_and_dates(self):
        self.client.force_login(self.seeker)
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': '', 'last_name': '', 'bio': '', 'budget_min': '900', 'budget_max': '500',
            'move_in_from': '2027-03-01', 'move_in_until': '2027-01-01', 'preferred_area': '',
            'sleep_schedule': '', 'cleanliness': '', 'noise_level': '', 'guests_policy': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'must be at least the bottom')
        self.assertContains(response, 'must be after the start')

    def test_edit_cannot_change_protected_fields(self):
        self.client.force_login(self.seeker)
        self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Sam', 'last_name': '', 'bio': '', 'preferred_area': '',
            'sleep_schedule': '', 'cleanliness': '', 'noise_level': '', 'guests_policy': '',
            'is_edu_verified': 'on', 'response_rate': '100', 'username': 'hacker', 'email': 'x@illinois.edu',
        })
        self.seeker.refresh_from_db()
        self.assertFalse(self.seeker.is_edu_verified)
        self.assertEqual(self.seeker.username, 'seeker')
        self.assertEqual(self.seeker.email, 'seeker@gmail.com')
