"""
Forms for creating and editing listings (A9: basic listing CRUD).

ListingForm is a ModelForm over the existing Listing model, limited to the
fields a lister actually fills in. Owner-only and system fields (lister,
verification, counters, AI metadata) are set by the views, never by the form.
"""

from django import forms

from .models import Listing


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

    def __init__(self, *args, lister=None, **kwargs):
        super().__init__(*args, **kwargs)
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
        return cleaned
