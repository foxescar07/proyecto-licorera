from django import template

register = template.Library()

@register.filter(name='pesos')
def pesos(value):
    """
    Formatea un numero como pesos colombianos con puntos como
    separador de miles. Ej: 1234567 -> '1.234.567'
    """
    if value in (None, ''):
        return '0'
    try:
        valor = int(round(float(value)))
    except (TypeError, ValueError):
        return value

    return f"{valor:,}".replace(",", ".")