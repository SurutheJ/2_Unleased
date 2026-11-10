"""Profile edit form (A9). Account fields that need checks of their own
(username, email, .edu verification, response rate) are not editable here."""

from django import forms

from .models import UnleasedUser


class ProfileForm(forms.ModelForm):

    class Meta:
        model = UnleasedUser
        fields = [
            'first_name', 'last_name', 'bio',
            'budget_min', 'budget_max', 'move_in_from', 'move_in_until', 'preferred_area',
            'sleep_schedule', 'cleanliness', 'noise_level', 'guests_policy', 'pets_ok',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'maxlength': 500}),
            'move_in_from': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'move_in_until': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'preferred_area': forms.TextInput(attrs={'placeholder': 'e.g. Near the Quad, Green St'}),
        }
        labels = {
            'bio': 'Bio',
            'budget_min': 'Budget from ($/mo)',
            'budget_max': 'Budget to ($/mo)',
            'move_in_from': 'Move-in from',
            'move_in_until': 'Move-in until',
            'preferred_area': 'Preferred area',
            'guests_policy': 'Guests',
            'pets_ok': 'OK living with pets',
        }

    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '')
        if len(bio) > 500:
            raise forms.ValidationError('Keep the bio under 500 characters.')
        return bio

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get('budget_min'), cleaned.get('budget_max')
        if low is not None and high is not None and low > high:
            self.add_error('budget_max', 'The top of your budget must be at least the bottom.')
        start, end = cleaned.get('move_in_from'), cleaned.get('move_in_until')
        if start and end and end < start:
            self.add_error('move_in_until', 'The end of the move-in window must be after the start.')
        return cleaned
