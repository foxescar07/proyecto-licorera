from django.urls import path
from . import views

app_name = 'ayuda'

urlpatterns = [
    path('', views.index_ayuda, name='index'),
]