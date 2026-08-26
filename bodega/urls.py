from django.urls import path
from . import views

app_name = 'bodega'

urlpatterns = [
    path('', views.bodega_home, name='bodega_home'),
    path('agenda/', views.agenda_list, name='agenda_list'),
    path('agenda/nueva/', views.agenda_create, name='agenda_create'),
    path('agenda/<int:codigo>/', views.agenda_detail, name='agenda_detail'),
    path('agenda/<int:codigo>/editar/', views.agenda_update, name='agenda_update'),
    path('agenda/<int:codigo>/completar/', views.agenda_completar, name='agenda_completar'),
    path('agenda/<int:codigo_agenda>/hallazgo/', views.hallazgo_create, name='hallazgo_create'),
    path('hallazgos/', views.hallazgo_list, name='hallazgo_list'),
]