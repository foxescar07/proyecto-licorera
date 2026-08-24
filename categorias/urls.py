from django.urls import path
from . import views

app_name = 'categorias'

urlpatterns = [
    path('', views.categorias_lista, name='lista'),
    path('crear/', views.categoria_crear, name='crear'),
    path('editar/<int:pk>/', views.categoria_editar, name='editar'),
    path('eliminar/<int:pk>/', views.categoria_eliminar, name='eliminar'),
]