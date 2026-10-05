"""
accounts/urls.py
Маршруты подсистемы аутентификации.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',        views.login_view,        name='login'),
    path('logout/',       views.logout_view,        name='logout'),
    path('register/',     views.register_view,      name='register'),
    path('access-denied/', views.access_denied_view, name='access_denied'),
    path('profile/',      views.profile_view,       name='profile'),
]
