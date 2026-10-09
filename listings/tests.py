"""
Route and access tests: every page and API loads, public pages and the one
public API work without logging in, and everything private requires login.

Run with:  python manage.py test listings
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import UnleasedUser
from .models import Inquiry, Listing

PUBLIC_PAGES = [
    'home', 'listings:list', 'listings:manual', 'listings:render',
    'listings:cbv_base', 'listings:cbv_generic', 'listings:search',
]
PROTECTED_PAGES = [
    'listings:inquiries', 'listings:insights', 'listings:insights_chart',
    'listings:vega_charts', 'listings:proximity', 'listings:reports',
    'listings:export_csv', 'listings:export_json',
]
PROTECTED_APIS = ['listings:api', 'listings:api_text', 'listings:api_proximity']
PUBLIC_API = 'listings:api_by_status'


class AccessTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.lister = UnleasedUser.objects.create_user(
            username='lister', password='Sublease#2026', email='lister@illinois.edu',
        )
        cls.seeker = UnleasedUser.objects.create_user(
            username='seeker', password='Sublease#2026', email='seeker@gmail.com',
        )
        cls.listing = Listing.objects.create(
            lister=cls.lister, title='Test room', description='A test listing.',
            monthly_rent=600, street_address='1 Test St', bedrooms=1, bathrooms=1,
            available_from=date(2026, 1, 1), available_until=date(2026, 6, 1),
        )

    # ---- logged out ----
    def test_public_pages_work_logged_out(self):
        for name in PUBLIC_PAGES:
            with self.subTest(route=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.get(self.listing.get_absolute_url()).status_code, 200)

    def test_protected_pages_redirect_to_login(self):
        login_url = reverse('account_login')
        for name in PROTECTED_PAGES:
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(login_url))

    def test_protected_apis_return_401_json(self):
        for name in PROTECTED_APIS:
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response['Content-Type'], 'application/json')
                self.assertIn('error', response.json())

    def test_public_api_open_to_everyone(self):
        response = self.client.get(reverse(PUBLIC_API))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        self.assertIsInstance(response.json(), list)

    def test_vega_chart1_public_chart2_protected(self):
        self.assertEqual(self.client.get(reverse('vega_chart_png', args=['chart1'])).status_code, 200)
        self.assertEqual(self.client.get(reverse('vega_chart_spec', args=['chart1'])).status_code, 200)
        self.assertEqual(self.client.get(reverse('vega_chart_png', args=['chart2'])).status_code, 401)
        self.assertEqual(self.client.get(reverse('vega_chart_spec', args=['chart2'])).status_code, 401)
        self.assertEqual(self.client.get('/vega-lite/chart9.png').status_code, 404)

    def test_navbar_hides_protected_tabs_logged_out(self):
        html = self.client.get(reverse('home')).content.decode()
        self.assertNotIn(reverse('listings:reports'), html)
        self.assertNotIn(reverse('listings:inquiries'), html)
        self.assertIn(reverse('account_login'), html)

    def test_sending_inquiry_requires_login(self):
        response = self.client.post(self.listing.get_absolute_url(), {'message': 'Hi'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Inquiry.objects.exists())

    # ---- logged in ----
    def test_everything_works_logged_in(self):
        self.client.login(username='seeker', password='Sublease#2026')
        for name in PUBLIC_PAGES + PROTECTED_PAGES + PROTECTED_APIS + [PUBLIC_API]:
            if name == 'listings:api_proximity':
                continue  # needs ?listing_id= and an external call; checked below
            with self.subTest(route=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        for chart in ['chart1', 'chart2']:
            with self.subTest(chart=chart):
                png = self.client.get(reverse('vega_chart_png', args=[chart]))
                self.assertEqual(png['Content-Type'], 'image/png')
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn(reverse('listings:reports'), html)

    def test_proximity_api_rejects_missing_listing_id(self):
        self.client.login(username='seeker', password='Sublease#2026')
        self.assertEqual(self.client.get(reverse('listings:api_proximity')).status_code, 400)

    def test_inquiry_uses_logged_in_user_and_my_inquiries_shows_only_mine(self):
        self.client.login(username='seeker', password='Sublease#2026')
        self.client.post(self.listing.get_absolute_url(), {'message': 'Is it available?'})
        inquiry = Inquiry.objects.get()
        self.assertEqual(inquiry.seeker, self.seeker)
        self.assertIn('Test room', self.client.get(reverse('listings:inquiries')).content.decode())
        self.client.logout()
        self.client.login(username='lister', password='Sublease#2026')
        self.assertNotIn('Test room', self.client.get(reverse('listings:inquiries')).content.decode())

    def test_exports_are_downloads(self):
        self.client.login(username='seeker', password='Sublease#2026')
        self.assertIn('attachment', self.client.get(reverse('listings:export_csv'))['Content-Disposition'])
        self.assertIn('attachment', self.client.get(reverse('listings:export_json'))['Content-Disposition'])
