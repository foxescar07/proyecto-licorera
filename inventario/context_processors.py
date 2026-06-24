from django.db.models import Sum
from inventario.models import Lote
from productos.models import Producto, Categoria

def aside_stats(request):
    if not request.user.is_authenticated:
        return {}

    total_stock = Lote.objects.aggregate(total=Sum('stock_actual'))['total'] or 0
    total_cats  = Categoria.objects.count()

    productos_qs = Producto.objects.annotate(
        total_stock=Sum('presentaciones__lotes__stock_actual')
    )

    # Críticos: 5 unidades o menos
    criticos_qs = productos_qs.filter(
        total_stock__gt=0,
        total_stock__lte=5
    ).values('nombre', 'total_stock')

    # Bajos: entre 6 y 15 unidades
    bajos_qs = productos_qs.filter(
        total_stock__gt=5,
        total_stock__lte=15
    ).values('nombre', 'total_stock')

    total_alertas = criticos_qs.count() + bajos_qs.count()

    return {
        'sb_total_stock':    total_stock,
        'sb_stock_criticos': criticos_qs.count(),
        'sb_total_cats':     total_cats,
        # ↓ Nuevas variables para la campanita
        'notif_criticos':    list(criticos_qs),
        'notif_bajos':       list(bajos_qs),
        'notif_total':       total_alertas,
    }