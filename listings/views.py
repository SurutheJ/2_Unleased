from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.views import View
from django.views.generic import DetailView, ListView

from .models import Listing

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
