"""Profile pages (A9, based on the P1-A1 Profile wireframe).

/profile/            your own profile: preferences, activity, your listings
/profile/edit/       edit your name, bio, preferences and lifestyle
/users/<username>/   anyone's public profile: verification, bio, lifestyle,
                     reviews and available listings (no email, budget or dates)
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render

from listings.models import Inquiry, Listing
from .forms import ProfileForm
from .models import UnleasedUser


def _term(day):
    """'Fall 2026' style label for the month someone joined."""
    season = 'Spring' if day.month <= 5 else 'Summer' if day.month <= 7 else 'Fall'
    return f'{season} {day.year}'


def _profile_context(person, viewer):
    received = Inquiry.objects.filter(listing__lister=person)
    total = received.count()
    answered = received.exclude(status=Inquiry.Status.PENDING).count()
    reviews = person.reviews_received.select_related('reviewer')
    is_own = viewer.is_authenticated and viewer.pk == person.pk
    listings = person.listings.prefetch_related('media')
    if not is_own:
        listings = listings.filter(status=Listing.Status.AVAILABLE)
    return {
        'person': person,
        'is_own': is_own,
        'display_name': person.get_full_name() or person.username,
        'initial': (person.first_name or person.username)[:1].upper(),
        'joined': _term(person.date_joined),
        'lifestyle': [
            ('Sleep schedule', person.get_sleep_schedule_display()),
            ('Cleanliness', person.get_cleanliness_display()),
            ('Noise level', person.get_noise_level_display()),
            ('Guests', person.get_guests_policy_display()),
            ('Pets', 'OK with pets' if person.pets_ok else 'Prefers no pets'),
        ],
        'activity': {
            'listings': person.listings.count(),
            'saved': person.saved_listings.count(),
            'visits': person.booked_visits.count(),
            'inquiries': person.inquiries_sent.count(),
            # Share of inquiries on this person's listings that got an answer.
            'response_rate': round(100 * answered / total) if total else None,
            'inquiries_received': total,
        },
        'reviews': reviews[:5],
        'review_count': reviews.count(),
        'avg_rating': reviews.aggregate(avg=Avg('rating'))['avg'],
        'listings': listings,
    }


@login_required
def my_profile(request):
    return render(request, 'accounts/profile.html', _profile_context(request.user, request.user))


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile was updated.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile_edit.html', {'form': form})


def public_profile(request, username):
    person = get_object_or_404(UnleasedUser, username=username, is_active=True)
    if request.user.is_authenticated and request.user.pk == person.pk:
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', _profile_context(person, request.user))
