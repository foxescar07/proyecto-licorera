from django.urls import path  # type: ignore
from . import views

app_name = 'presentaciones'

urlpatterns = [
    path('<int:pk>/guardar/', views.guardar,     name='guardar'),
    path('<int:pk>/json/',    views.listar_json, name='json'),
]