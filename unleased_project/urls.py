"""
URL configuration for unleased_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from listings.views import home, vega_chart_png, vega_chart_spec

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('listings/', include('listings.urls')),
    # A4 Part 1: dedicated chart endpoints, e.g. /vega-lite/chart1.png and /vega-lite/chart1.json
    path('vega-lite/<slug:chart>.png', vega_chart_png, name='vega_chart_png'),
    path('vega-lite/<slug:chart>.json', vega_chart_spec, name='vega_chart_spec'),
]
