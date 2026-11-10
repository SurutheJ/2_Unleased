from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.my_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='profile_edit'),
    path('users/<str:username>/', views.public_profile, name='public_profile'),
]
