from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.views import View
from django.views.generic import DetailView, ListView

from .models import Listing


# ---------------------------------------------------------------------------
# Function-based views
# ---------------------------------------------------------------------------

def listing_manual(request):
    """FBV 1: load the template by hand and wrap the result in HttpResponse."""
    template = loader.get_template('listings/listing_manual.html')
    context = {'count': Listing.objects.count()}
    return HttpResponse(template.render(context, request))


def listing_render(request):
    """FBV 2: query the model and use the render() shortcut."""
    listings = Listing.objects.select_related('lister')
    return render(request, 'listings/listing_render.html', {'listings': listings})


# ---------------------------------------------------------------------------
# Class-based views
# ---------------------------------------------------------------------------

class ListingBaseView(View):
    """CBV 1: plain View; query the model manually inside get()."""

    def get(self, request):
        listings = Listing.objects.filter(status=Listing.Status.AVAILABLE)
        return render(request, 'listings/listing_base.html', {'listings': listings})


class ListingListView(ListView):
    """CBV 2: generic ListView (default template: listings/listing_list.html)."""
    model = Listing
    context_object_name = 'listings'


class ListingDetailView(DetailView):
    """Generic DetailView (default template: listings/listing_detail.html)."""
    model = Listing
    context_object_name = 'listing'
