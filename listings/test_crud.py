"""
Tests for A9's basic listing CRUD and the "Create listing from this" link
from the AI assistant.

Run with:  python manage.py test listings.test_crud
"""

from datetime import date, timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from accounts.models import UnleasedUser
from .forms import ListingForm
from .models import Listing

START = date.today() + timedelta(days=30)
END = START + timedelta(days=90)


def form_data(**overrides):
    data = {
        'title': 'Room near Green St', 'description': 'Bright room, close to campus.',
        'monthly_rent': '650', 'street_address': '505 E Green St', 'unit_number': '4B',
        'city': 'Champaign', 'state': 'IL', 'zip_code': '61820',
        'bedrooms': '3', 'bathrooms': '1.5', 'is_private_bedroom': 'on', 'is_furnished': 'on',
        'available_from': START.isoformat(), 'available_until': END.isoformat(),
        'gender_preference': 'any', 'status': 'available',
    }
    data.update(overrides)
    return data


class ListingCrudTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = UnleasedUser.objects.create_user(
            username='owner', password='Sublease#2026', email='owner@illinois.edu')
        cls.other = UnleasedUser.objects.create_user(
            username='other', password='Sublease#2026', email='other@illinois.edu')
        cls.listing = Listing.objects.create(
            lister=cls.owner, title='Owner room', description='Existing listing.',
            monthly_rent=700, street_address='1 Test St', bedrooms=1, bathrooms=1,
            available_from=START, available_until=END,
        )

    # ---- access ----
    def test_all_crud_pages_require_login(self):
        login = reverse('account_login')
        urls = [reverse('listings:create'), reverse('listings:mine'),
                reverse('listings:update', args=[self.listing.pk]),
                reverse('listings:delete', args=[self.listing.pk])]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(login))

    # ---- create ----
    def test_create_sets_the_logged_in_user_as_lister(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('listings:create'), form_data())
        listing = Listing.objects.get(title='Room near Green St')
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertEqual(listing.lister, self.other)
        self.assertFalse(listing.ai_parsed)

    def test_lister_cannot_be_chosen_through_the_form(self):
        self.client.force_login(self.other)
        self.client.post(reverse('listings:create'), form_data(lister=self.owner.pk))
        self.assertEqual(Listing.objects.get(title='Room near Green St').lister, self.other)

    def test_end_date_must_be_after_start_date(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('listings:create'),
                                    form_data(available_until=START.isoformat()))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The end date must be after the start date.')
        self.assertFalse(Listing.objects.filter(title='Room near Green St').exists())

    def test_missing_required_fields_show_errors_not_a_crash(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('listings:create'), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')

    def test_duplicate_listing_gives_a_form_error_not_a_500(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('listings:create'), form_data(
            street_address='1 Test St', unit_number='', available_from=START.isoformat()))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You already have a listing for this address')

    def test_form_without_a_lister_still_validates_dates(self):
        form = ListingForm(data=form_data(available_until=START.isoformat()))
        self.assertFalse(form.is_valid())
        self.assertIn('available_until', form.errors)

    # ---- edit ----
    def test_owner_can_edit(self):
        self.client.force_login(self.owner)
        url = reverse('listings:update', args=[self.listing.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, form_data(title='Updated title', street_address='1 Test St', unit_number=''))
        self.assertRedirects(response, self.listing.get_absolute_url())
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, 'Updated title')

    def test_other_user_cannot_edit(self):
        self.client.force_login(self.other)
        url = reverse('listings:update', args=[self.listing.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, form_data(title='Hacked')).status_code, 404)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, 'Owner room')

    # ---- delete ----
    def test_owner_can_delete_after_confirming(self):
        self.client.force_login(self.owner)
        url = reverse('listings:delete', args=[self.listing.pk])
        self.assertContains(self.client.get(url), 'Delete this listing?')
        self.assertRedirects(self.client.post(url), reverse('listings:mine'))
        self.assertFalse(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.other)
        url = reverse('listings:delete', args=[self.listing.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    # ---- my listings ----
    def test_my_listings_shows_only_own_listings(self):
        Listing.objects.create(
            lister=self.other, title='Other room', description='x', monthly_rent=500,
            street_address='2 Test St', bedrooms=1, bathrooms=1, available_from=START, available_until=END)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('listings:mine'))
        self.assertContains(response, 'Owner room')
        self.assertNotContains(response, 'Other room')

    def test_detail_page_shows_edit_link_only_to_owner(self):
        edit_url = reverse('listings:update', args=[self.listing.pk])
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.listing.get_absolute_url()), edit_url)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(self.listing.get_absolute_url()), edit_url)


GOOD_REPLY = ('{"title": "Room near Green St", "monthly_rent": 650, "bedrooms": 3, "is_furnished": true, '
              '"has_in_unit_laundry": true, "pets_allowed": false, "has_parking": null, "has_balcony": null, '
              '"utilities_included": null, "available_from": null, "available_until": null}')
MESSAGE = ('subletting my room, 3bd apt near green st, $650/mo, furnished, in unit laundry, '
           'no pets, text 217-555-0199')


class CreateFromAiTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UnleasedUser.objects.create_user(
            username='tester', password='Sublease#2026', email='tester@illinois.edu')

    def setUp(self):
        self.client.force_login(self.user)

    @mock.patch('listings.ai_local.run_local_model', return_value=GOOD_REPLY)
    def run_assistant(self, run):
        return self.client.post(reverse('listings:ai_assistant'), {'message': MESSAGE})

    def test_assistant_shows_the_create_button_and_saves_nothing(self):
        response = self.run_assistant()
        self.assertContains(response, reverse('listings:create') + '?from_ai=1')
        self.assertEqual(Listing.objects.count(), 0)

    def test_form_is_prefilled_from_the_ai_result(self):
        self.run_assistant()
        response = self.client.get(reverse('listings:create') + '?from_ai=1')
        form = response.context['form']
        self.assertEqual(form.initial['title'], 'Room near Green St')
        self.assertEqual(form.initial['monthly_rent'], '650')
        self.assertEqual(form.initial['bedrooms'], 3)
        self.assertTrue(form.initial['is_furnished'])
        self.assertFalse(form.initial['pets_allowed'])
        self.assertContains(response, 'Pre-filled from the AI assistant')

    def test_plain_create_page_is_not_prefilled(self):
        self.run_assistant()
        response = self.client.get(reverse('listings:create'))
        self.assertNotIn('title', response.context['form'].initial)
        self.assertNotContains(response, 'Pre-filled from the AI assistant')

    def test_saving_marks_the_listing_ai_parsed_and_keeps_the_masked_message(self):
        self.run_assistant()
        response = self.client.post(reverse('listings:create'), form_data(from_ai='1'))
        listing = Listing.objects.get(lister=self.user)
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertTrue(listing.ai_parsed)
        self.assertIn('3bd apt near green st', listing.raw_whatsapp_text)
        self.assertNotIn('217-555-0199', listing.raw_whatsapp_text)   # phone was masked by clean_message
        self.assertNotIn('ai_draft', self.client.session)              # the draft is used once

    def test_from_ai_without_a_draft_falls_back_to_a_normal_form(self):
        response = self.client.get(reverse('listings:create') + '?from_ai=1')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pre-filled from the AI assistant')
