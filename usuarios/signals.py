from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import RegistroActividad


def _obtener_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@receiver(user_logged_in)
def registrar_ingreso(sender, request, user, **kwargs):
    RegistroActividad.objects.create(
        usuario=user,
        ip_address=_obtener_ip(request)
    )