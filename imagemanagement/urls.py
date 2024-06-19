from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path('start', views.start, name='start'),
    path('resultcheck', views.resultcheck, name='resultcheck'),
    path('mockwhms', views.mockwhms, name='mockwhms'),
]