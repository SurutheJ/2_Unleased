"""
Tests for listing photo and video uploads (A9).

Run with:  python manage.py test listings.test_media
Files are written to a temporary MEDIA_ROOT that is deleted afterwards.
"""

import io
import os
import shutil
import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import UnleasedUser
from .models import Listing, ListingMedia
from .test_crud import form_data

TEMP_MEDIA = tempfile.mkdtemp(prefix='unleased-test-media-')


def photo(name='room.jpg', fmt='JPEG', size=(40, 30)):
    buffer = io.BytesIO()
    Image.new('RGB', size, (200, 120, 90)).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


def video(name='tour.mp4', body=b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 200):
    return SimpleUploadedFile(name, body, content_type='video/mp4')


@override_settings(MEDIA_ROOT=TEMP_MEDIA, LISTING_MAX_PHOTOS=3, LISTING_MAX_PHOTO_MB=1, LISTING_MAX_VIDEO_MB=1)
class ListingMediaTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.owner = UnleasedUser.objects.create_user(
            username='owner', password='Sublease#2026', email='owner@illinois.edu')
        cls.other = UnleasedUser.objects.create_user(
            username='other', password='Sublease#2026', email='other@illinois.edu')

    def setUp(self):
        self.client.force_login(self.owner)

    def create(self, **files):
        data = form_data()
        data.update(files)
        return self.client.post(reverse('listings:create'), data)

    def listing(self):
        return Listing.objects.get(lister=self.owner)

    # ---- uploading ----
    def test_create_with_photos_and_a_video(self):
        response = self.create(photos=[photo('a.jpg'), photo('b.png', 'PNG')], video=video())
        listing = self.listing()
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertEqual(len(listing.photos), 2)
        self.assertEqual(len(listing.videos), 1)
        for item in listing.media.all():
            self.assertTrue(os.path.exists(item.file.path))

    def test_create_without_media_still_works(self):
        self.create()
        self.assertEqual(self.listing().media.count(), 0)

    def test_cover_photo_shows_on_detail_page_and_browse_card(self):
        self.create(photos=[photo('cover.jpg')])
        cover_url = self.listing().cover_photo.file.url
        self.assertContains(self.client.get(self.listing().get_absolute_url()), cover_url)
        self.assertContains(self.client.get(reverse('listings:list')), cover_url)

    def test_video_is_shown_with_controls_on_detail_page(self):
        self.create(video=video())
        response = self.client.get(self.listing().get_absolute_url())
        self.assertContains(response, '<video src="' + self.listing().videos[0].file.url)

    # ---- guardrails ----
    def test_text_file_renamed_to_jpg_is_rejected(self):
        response = self.create(photos=[SimpleUploadedFile('fake.jpg', b'just some text', content_type='image/jpeg')])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'could not be read as an image')
        self.assertFalse(Listing.objects.filter(lister=self.owner).exists())

    def test_wrong_photo_extension_is_rejected(self):
        response = self.create(photos=[photo('room.gif')])
        self.assertContains(response, 'is not a JPG, PNG or WebP photo')

    def test_oversized_photo_is_rejected(self):
        big = SimpleUploadedFile('big.jpg', b'\xff\xd8' + b'0' * (1024 * 1024 + 10), content_type='image/jpeg')
        response = self.create(photos=[big])
        self.assertContains(response, 'is larger than 1 MB')

    def test_too_many_photos_is_rejected(self):
        response = self.create(photos=[photo(f'{i}.jpg') for i in range(4)])
        self.assertContains(response, 'at most 3 photos')

    def test_fake_video_is_rejected(self):
        response = self.create(video=SimpleUploadedFile('tour.mp4', b'not really a video at all', content_type='video/mp4'))
        self.assertContains(response, 'does not look like a real MP4/MOV video')

    def test_wrong_video_extension_is_rejected(self):
        response = self.create(video=video('tour.avi'))
        self.assertContains(response, 'is not an MP4 or MOV video')

    # ---- editing ----
    def test_edit_can_add_and_remove_media(self):
        self.create(photos=[photo('a.jpg'), photo('b.jpg')])
        listing = self.listing()
        first = listing.photos[0]
        first_path = first.file.path
        data = form_data(street_address=listing.street_address, unit_number=listing.unit_number)
        data.update({'remove_media': [first.pk], 'photos': [photo('c.jpg')], 'video': video()})
        response = self.client.post(reverse('listings:update', args=[listing.pk]), data)
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertEqual(len(listing.photos), 2)
        self.assertEqual(len(listing.videos), 1)
        self.assertFalse(ListingMedia.objects.filter(pk=first.pk).exists())
        self.assertFalse(os.path.exists(first_path))          # file removed from disk too

    def test_photo_limit_counts_existing_photos(self):
        self.create(photos=[photo('a.jpg'), photo('b.jpg'), photo('c.jpg')])
        listing = self.listing()
        data = form_data(street_address=listing.street_address, unit_number=listing.unit_number)
        data['photos'] = [photo('d.jpg')]
        response = self.client.post(reverse('listings:update', args=[listing.pk]), data)
        self.assertContains(response, 'at most 3 photos')

    def test_second_video_needs_the_first_removed(self):
        self.create(video=video())
        listing = self.listing()
        data = form_data(street_address=listing.street_address, unit_number=listing.unit_number)
        data['video'] = video('second.mp4')
        response = self.client.post(reverse('listings:update', args=[listing.pk]), data)
        self.assertContains(response, 'at most 1 video')

    def test_other_user_cannot_remove_media_from_their_own_form(self):
        self.create(photos=[photo('a.jpg')])
        mine = self.listing().photos[0]
        self.client.force_login(self.other)
        self.client.post(reverse('listings:create'), form_data(street_address='9 Other St', remove_media=[mine.pk]))
        self.assertTrue(ListingMedia.objects.filter(pk=mine.pk).exists())

    # ---- deleting ----
    def test_deleting_a_listing_deletes_its_files(self):
        self.create(photos=[photo('a.jpg')], video=video())
        listing = self.listing()
        paths = [item.file.path for item in listing.media.all()]
        self.client.post(reverse('listings:delete', args=[listing.pk]))
        self.assertEqual(ListingMedia.objects.count(), 0)
        for path in paths:
            self.assertFalse(os.path.exists(path))
