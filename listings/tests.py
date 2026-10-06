"""
Route smoke tests: every page and API in the app should load without errors.

Run with:  python manage.py test listings
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import UnleasedUser
from .models import Listing


class RouteSmokeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        lister = UnleasedUser.objects.create_user(
            username='lister', password='test1234', edu_email='lister@illinois.edu',
        )
        cls.listing = Listing.objects.create(
            lister=lister, title='Test room', description='A test listing.',
            monthly_rent=600, street_address='1 Test St', bedrooms=1, bathrooms=1,
            available_from=date(2026, 1, 1), available_until=date(2026, 6, 1),
        )

    def test_pages_and_apis_return_200(self):
        names = [
            'home', 'listings:list', 'listings:manual', 'listings:render',
            'listings:cbv_base', 'listings:cbv_generic', 'listings:search',
            'listings:inquiries', 'listings:insights', 'listings:insights_chart',
            'listings:api', 'listings:api_text', 'listings:api_by_status',
            'listings:vega_charts', 'listings:proximity', 'listings:reports',
            'listings:export_csv', 'listings:export_json',
        ]
        for name in names:
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_detail_page_uses_get_absolute_url(self):
        response = self.client.get(self.listing.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_missing_listing_is_404(self):
        response = self.client.get(reverse('listings:detail', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)

    def test_exports_are_downloads(self):
        csv_response = self.client.get(reverse('listings:export_csv'))
        json_response = self.client.get(reverse('listings:export_json'))
        self.assertIn('attachment', csv_response['Content-Disposition'])
        self.assertIn('attachment', json_response['Content-Disposition'])

    def test_vega_chart_endpoints(self):
        for chart in ['chart1', 'chart2']:
            with self.subTest(chart=chart):
                png = self.client.get(reverse('vega_chart_png', args=[chart]))
                self.assertEqual(png.status_code, 200)
                self.assertEqual(png['Content-Type'], 'image/png')
                spec = self.client.get(reverse('vega_chart_spec', args=[chart])).json()
                self.assertTrue(spec['data']['url'].startswith('http'))
        self.assertEqual(self.client.get('/vega-lite/chart9.png').status_code, 404)

    def test_proximity_api_rejects_missing_listing_id(self):
        response = self.client.get(reverse('listings:api_proximity'))
        self.assertEqual(response.status_code, 400)
