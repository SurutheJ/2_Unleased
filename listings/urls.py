from django.urls import path

from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.ListingListView.as_view(), name='list'),   # /listings/  main browse page
    path('manual/', views.listing_manual, name='manual'),
    path('render/', views.listing_render, name='render'),
    path('cbv-base/', views.ListingBaseView.as_view(), name='cbv_base'),
    path('cbv-generic/', views.ListingListView.as_view(), name='cbv_generic'),
    path('search/', views.listing_search, name='search'),      # GET search (public, shareable)
    path('my-inquiries/', views.InquiryLookupView.as_view(), name='inquiries'),  # POST search (private)
    path('<int:pk>/', views.ListingDetailView.as_view(), name='detail'),
]
