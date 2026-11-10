"""
Forms for creating and editing listings (A9: basic listing CRUD).

ListingForm is a ModelForm over the existing Listing model, limited to the
fields a lister actually fills in. Owner-only and system fields (lister,
verification, counters, AI metadata) are set by the views, never by the form.
"""

import os

from django import forms
from django.conf import settings

from .models import Listing, ListingMedia

PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov'}


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """A file field that accepts several files and returns a list."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if isinstance(data, (list, tuple)):
            return [super(MultipleFileField, self).clean(item, initial) for item in data if item]
        return [super().clean(data, initial)] if data else []


def _check_photo(upload):
    """Reject anything that is not a real JPG/PNG/WebP image under the size limit."""
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in PHOTO_EXTENSIONS:
        raise forms.ValidationError(f'"{upload.name}" is not a JPG, PNG or WebP photo.')
    if upload.size > settings.LISTING_MAX_PHOTO_MB * 1024 * 1024:
        raise forms.ValidationError(f'"{upload.name}" is larger than {settings.LISTING_MAX_PHOTO_MB} MB.')
    # Check the content, not just the name: a renamed text file must not pass.
    from PIL import Image
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image.verify()
        if image.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError(image.format)
    except Exception:
        raise forms.ValidationError(f'"{upload.name}" could not be read as an image.')
    finally:
        upload.seek(0)


def _check_video(upload):
    """Accept only MP4/MOV files under the size limit whose content looks like a video."""
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in VIDEO_EXTENSIONS:
        raise forms.ValidationError(f'"{upload.name}" is not an MP4 or MOV video.')
    if upload.size > settings.LISTING_MAX_VIDEO_MB * 1024 * 1024:
        raise forms.ValidationError(f'"{upload.name}" is larger than {settings.LISTING_MAX_VIDEO_MB} MB.')
    # MP4 and MOV files both start with a box whose type (bytes 4-8) is "ftyp".
    upload.seek(0)
    header = upload.read(12)
    upload.seek(0)
    if header[4:8] != b'ftyp':
        raise forms.ValidationError(f'"{upload.name}" does not look like a real MP4/MOV video.')


class ListingForm(forms.ModelForm):

    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'monthly_rent', 'utilities_included',
            'building_name', 'street_address', 'unit_number', 'city', 'state', 'zip_code',
            'bedrooms', 'bathrooms', 'is_private_bedroom', 'is_private_bathroom',
            'is_furnished', 'has_in_unit_laundry', 'has_parking', 'has_balcony',
            'pets_allowed', 'ac_included',
            'available_from', 'available_until', 'gender_preference', 'status',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'available_from': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'available_until': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
        labels = {
            'monthly_rent': 'Monthly rent ($)',
            'utilities_included': 'Utilities included',
            'is_private_bedroom': 'Private bedroom',
            'is_private_bathroom': 'Private bathroom',
            'is_furnished': 'Furnished',
            'has_in_unit_laundry': 'In-unit laundry',
            'has_parking': 'Parking',
            'has_balcony': 'Balcony',
            'pets_allowed': 'Pets allowed',
            'ac_included': 'A/C included',
            'zip_code': 'ZIP code',
        }

    photos = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'accept': '.jpg,.jpeg,.png,.webp'}),
        label='Add photos',
        help_text=f'Up to {settings.LISTING_MAX_PHOTOS} photos in total, JPG/PNG/WebP, '
                  f'{settings.LISTING_MAX_PHOTO_MB} MB each. The first photo is the cover image.',
    )
    video = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': '.mp4,.mov'}),
        label='Add a video',
        help_text=f'Up to {settings.LISTING_MAX_VIDEOS} short video, MP4/MOV, '
                  f'{settings.LISTING_MAX_VIDEO_MB} MB max (a quick room tour works well).',
    )
    remove_media = forms.ModelMultipleChoiceField(
        queryset=ListingMedia.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple, label='Remove',
    )

    def __init__(self, *args, lister=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['remove_media'].queryset = self.instance.media.all()
        else:
            del self.fields['remove_media']
        # The lister is not a form field (the view sets it), so Django's own
        # unique-constraint check skips the one constraint that involves it.
        # We keep the lister here and check that constraint ourselves in clean().
        self.lister = lister

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('available_from'), cleaned.get('available_until')
        if start and end and end <= start:
            self.add_error('available_until', 'The end date must be after the start date.')

        if self.lister is not None and start and cleaned.get('street_address'):
            duplicate = Listing.objects.filter(
                lister=self.lister,
                street_address=cleaned['street_address'],
                unit_number=cleaned.get('unit_number', ''),
                available_from=start,
            ).exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise forms.ValidationError(
                    'You already have a listing for this address, unit and start date.')

        self._clean_media(cleaned)
        return cleaned

    def _clean_media(self, cleaned):
        photos = cleaned.get('photos') or []
        video = cleaned.get('video')
        for upload in photos:
            try:
                _check_photo(upload)
            except forms.ValidationError as error:
                self.add_error('photos', error)
        if video:
            try:
                _check_video(video)
            except forms.ValidationError as error:
                self.add_error('video', error)

        # Count what the listing will have after this save: existing - removed + new.
        removing = set(cleaned.get('remove_media') or [])
        existing = list(self.instance.media.all()) if self.instance.pk else []
        kept_photos = sum(1 for m in existing if m.kind == 'photo' and m not in removing)
        kept_videos = sum(1 for m in existing if m.kind == 'video' and m not in removing)
        if kept_photos + len(photos) > settings.LISTING_MAX_PHOTOS:
            self.add_error('photos', f'A listing can have at most {settings.LISTING_MAX_PHOTOS} photos '
                                     f'(it would have {kept_photos + len(photos)}). Remove some first.')
        if video and kept_videos + 1 > settings.LISTING_MAX_VIDEOS:
            self.add_error('video', f'A listing can have at most {settings.LISTING_MAX_VIDEOS} video. '
                                    'Tick "Remove" on the current one to replace it.')

    def save_media(self, listing):
        """Delete the media the user ticked, then attach the new uploads.
        Called by the view after the listing itself is saved."""
        for item in self.cleaned_data.get('remove_media') or []:
            item.delete()   # also deletes the file (post_delete handler in models.py)
        for upload in self.cleaned_data.get('photos') or []:
            ListingMedia.objects.create(listing=listing, kind=ListingMedia.Kind.PHOTO, file=upload)
        if self.cleaned_data.get('video'):
            ListingMedia.objects.create(listing=listing, kind=ListingMedia.Kind.VIDEO,
                                        file=self.cleaned_data['video'])
