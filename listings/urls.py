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
    path('insights/', views.listing_insights, name='insights'),  # aggregations
    path('insights/chart.png', views.listing_status_chart, name='insights_chart'),  # matplotlib PNG
    path('api/', views.listing_api, name='api'),                  # JSON API (JsonResponse)
    path('api.txt', views.listing_api_text, name='api_text'),     # same data, HttpResponse/text
    path('api/by-status/', views.listing_api_by_status, name='api_by_status'),  # chart-ready JSON (bar chart)
    path('api/proximity/', views.listing_proximity, name='api_proximity'),      # external geocoding API (keyless)
    path('charts/', views.vega_charts, name='vega_charts'),        # two embedded Vega-Lite charts
    path('proximity/', views.listing_proximity_page, name='proximity'),  # HTML page calling api_proximity via fetch()
    path('<int:pk>/', views.ListingDetailView.as_view(), name='detail'),  # GET show + POST inquire
]
