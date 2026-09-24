from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.views import View
from django.views.generic import DetailView, ListView

from .models import Inquiry, Listing

# All four list views share ONE template. The views differ in how they fetch
# and pass the data; the page itself looks the same. `view_label` is only a
# small tag shown on the page so you can tell which view produced it.
LIST_TEMPLATE = 'listings/listing_list.html'


# ---------------------------------------------------------------------------
# Function-based views
# ---------------------------------------------------------------------------

def home(request):
    """
    Home page (/): a welcome header, the total number of listings,
    and the three newest listings that are still available.
    """
    context = {
        'featured': Listing.objects.filter(status=Listing.Status.AVAILABLE)[:3],
        'total_listings': Listing.objects.count(),
    }
    return render(request, 'listings/home.html', context)


def listing_manual(request):
    """FBV 1: load the template by hand and wrap the result in HttpResponse."""
    template = loader.get_template(LIST_TEMPLATE)
    context = {
        'listings': Listing.objects.select_related('lister'),
        'view_label': 'HttpResponse + loader.get_template()',
    }
    return HttpResponse(template.render(context, request))


def listing_render(request):
    """FBV 2: query the model and use the render() shortcut."""
    context = {
        'listings': Listing.objects.select_related('lister'),
        'view_label': 'render() shortcut',
    }
    return render(request, LIST_TEMPLATE, context)


# ---------------------------------------------------------------------------
# Class-based views
# ---------------------------------------------------------------------------

class ListingBaseView(View):
    """CBV 1: plain View; query the model manually inside get()."""

    def get(self, request):
        context = {
            'listings': Listing.objects.filter(status=Listing.Status.AVAILABLE),
            'view_label': 'Base CBV (View), available listings only',
        }
        return render(request, LIST_TEMPLATE, context)


class ListingListView(ListView):
    """CBV 2: generic ListView (its default template is listings/listing_list.html)."""
    model = Listing
    template_name = LIST_TEMPLATE
    context_object_name = 'listings'
    extra_context = {'view_label': 'Generic ListView'}


class ListingDetailView(DetailView):
    """Generic DetailView (default template: listings/listing_detail.html)."""
    model = Listing
    context_object_name = 'listing'


# ---------------------------------------------------------------------------
# A3 Section 2: search and ORM queries
# ---------------------------------------------------------------------------

def listing_search(request):
    """
    PUBLIC search, submitted with GET.

    The filters live in the URL (e.g. /listings/search/?q=furnished&max_rent=800),
    so the same link always loads the same results. A student can bookmark it
    or paste it in a group chat and their roommate sees the exact same list.
    Nothing here is private, so there is no reason to hide it in a POST body.
    """
    q = request.GET.get('q', '').strip()
    max_rent = request.GET.get('max_rent', '').strip()
    min_bedrooms = request.GET.get('min_bedrooms', '').strip()
    lister_name = request.GET.get('lister', '').strip()
    status = request.GET.get('status', '').strip()

    results = Listing.objects.select_related('lister')

    if q:
        # Keyword search across several text fields (OR, using Q objects).
        results = results.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(building_name__icontains=q)
        )
    if max_rent.isdigit():
        results = results.filter(monthly_rent__lte=max_rent)
    if min_bedrooms.isdigit():
        results = results.filter(bedrooms__gte=min_bedrooms)
    if lister_name:
        # Relationship-spanning lookup: Listing -> lister (UnleasedUser).
        # The double underscore follows the ForeignKey into the user table.
        results = results.filter(
            Q(lister__first_name__icontains=lister_name)
            | Q(lister__last_name__icontains=lister_name)
            | Q(lister__username__icontains=lister_name)
        )
    if status in Listing.Status.values:
        results = results.filter(status=status)

    searched = any([q, max_rent, min_bedrooms, lister_name, status])

    context = {
        'results': results,
        'searched': searched,
        'total_listings': Listing.objects.count(),
        'status_choices': Listing.Status.choices,
        # Echo the inputs back so the form keeps what the user typed.
        'form_values': {
            'q': q,
            'max_rent': max_rent,
            'min_bedrooms': min_bedrooms,
            'lister': lister_name,
            'status': status,
        },
    }
    return render(request, 'listings/listing_search.html', context)


class InquiryLookupView(View):
    """
    PRIVATE search, submitted with POST: "Track my inquiries".

    A seeker types their .edu email to see the inquiries they have sent and
    whether each one was accepted. This is personal data (an email address,
    and for accepted inquiries the listing's private street address), so it
    should NOT end up in the URL, browser history, bookmarks or server logs.
    POST sends the email in the request body instead, and {% csrf_token %}
    protects the form. Refreshing or sharing the page does not replay it.
    """
    template_name = 'listings/inquiry_lookup.html'

    def get(self, request):
        # First visit: just show the empty form.
        return render(request, self.template_name, {'submitted': False})

    def post(self, request):
        email = request.POST.get('edu_email', '').strip().lower()
        error = ''
        inquiries = Inquiry.objects.none()

        if not email.endswith('.edu'):
            error = 'Please enter the .edu email you used on Unleased.'
        else:
            # Relationship-spanning lookup: Inquiry -> seeker (UnleasedUser).
            # We never show the email back in a URL; it only lives in this request.
            inquiries = (
                Inquiry.objects
                .filter(seeker__edu_email__iexact=email)
                .select_related('listing')
            )

        context = {
            'submitted': True,
            'email': email,
            'error': error,
            'inquiries': inquiries,
        }
        return render(request, self.template_name, context)
