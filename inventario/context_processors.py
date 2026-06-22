from django.db.models import Sum
from inventario.models import Lote
from productos.models import Producto, Categoria

def aside_stats(request):
    if not request.user.is_authenticated:
        return {}

    total_stock = Lote.objects.aggregate(total=Sum('stock_actual'))['total'] or 0
    
    # Productos con stock total <= 5
    criticos = Producto.objects.annotate(
        total_stock=Sum('presentaciones__lotes__stock_actual')
    ).filter(total_stock__lte=5).count()
    
    total_cats = Categoria.objects.count()

    return {
        'sb_total_stock': total_stock,
        'sb_stock_criticos': criticos,
        'sb_total_cats': total_cats
    }
