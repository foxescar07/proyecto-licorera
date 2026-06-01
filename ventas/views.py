from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.db import transaction
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from io import BytesIO
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER
from .models import Devolucion, DetalleDevolucion, Venta, DetalleVenta


# ════════════════════════════════════════
# DEVOLUCIONES
# ════════════════════════════════════════

@login_required
def lista_devoluciones(request):
    devoluciones = Devolucion.objects.select_related(
        'venta'
    ).prefetch_related(
        'detalles__detalle_venta__presentacion__producto'
    ).order_by('-fecha')

    return render(
        request,
        'devoluciones.html',
        {
            'devoluciones': devoluciones
        }
    )


@login_required
def buscar_venta_devolucion(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'ventas': []})

    ventas = Venta.objects.filter(
        cliente__icontains=q
    ).order_by('-fecha')[:10]

    if q.isdigit():
        ventas = (
            Venta.objects.filter(pk=int(q)) | ventas
        ).distinct()

    return JsonResponse({'ventas': [
        {
            'id':      v.pk,
            'cliente': v.cliente,
            'fecha':   v.fecha.strftime('%d/%m/%Y %H:%M'),
            'total':   float(v.total_venta),
        }
        for v in ventas
    ]})


@login_required
def detalle_venta_devolucion(request, venta_id):
    venta = get_object_or_404(
        Venta,
        pk=venta_id,
    )

    return JsonResponse({
        'venta_id': venta.pk,

        'cliente': venta.cliente,

        'fecha': venta.fecha.strftime(
            '%d/%m/%Y %H:%M'
        ),

        'total': float(
            venta.total_venta
        ),

        'detalles': [
            {
                'detalle_id': d.pk,

                'producto': (
                    d.presentacion.producto.nombre
                    if d.presentacion else ''
                ),

                'presentacion': (
                    d.presentacion.nombre
                    if d.presentacion else ''
                ),

                'cantidad': d.cantidad,

                'precio': float(
                    d.precio_unitario
                ),

                'subtotal': float(
                    d.subtotal()
                ),
            }
            for d in venta.detalles.select_related(
                'presentacion__producto'
            ).all()
        ],
    })


@login_required
@transaction.atomic
def registrar_devolucion(request):
    if request.method != 'POST':
        return redirect('devoluciones:lista_devoluciones')

    venta_id = request.POST.get('venta_id')

    motivo = request.POST.get(
        'motivo',
        ''
    )

    tipo_reembolso = request.POST.get(
        'tipo_reembolso',
        'efectivo'
    )

    detalle_ids = request.POST.getlist(
        'detalle_id[]'
    )

    cantidades = request.POST.getlist(
        'cantidad[]'
    )

    estados = request.POST.getlist(
        'estado_producto[]'
    )

    observaciones = request.POST.getlist(
        'observacion[]'
    )

    venta = get_object_or_404(Venta, pk=venta_id)

    if not detalle_ids:
        messages.error(
            request,
            'Debes seleccionar al menos un producto para devolver.'
        )
        return redirect('devoluciones:lista_devoluciones')

    total_devuelto   = Decimal('0')
    detalles_a_crear = []

    for i in range(len(detalle_ids)):
        detalle = get_object_or_404(
            DetalleVenta,
            pk=detalle_ids[i],
        )

        cantidad    = int(cantidades[i])
        estado      = estados[i]
        observacion = observaciones[i]

        total_devuelto += detalle.precio_unitario * cantidad
        detalles_a_crear.append({
            'detalle':     detalle,
            'cantidad':    cantidad,
            'estado':      estado,
            'observacion': observacion,
        })

    devolucion = Devolucion.objects.create(
        venta=venta,
        motivo=motivo,
        tipo_reembolso=tipo_reembolso,
        total_devuelto=total_devuelto,
    )

    for item in detalles_a_crear:
        detalle     = item['detalle']
        cantidad    = item['cantidad']
        estado      = item['estado']
        observacion = item['observacion']

        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            detalle_venta=detalle,
            cantidad=cantidad,
            estado_producto=estado,
            observacion=observacion,
        )

        if detalle.presentacion:
            detalle.presentacion.cantidad += cantidad
            detalle.presentacion.save()

    messages.success(
        request,
        f'Devolución {devolucion.numero} registrada correctamente.'
    )

    return redirect('devoluciones:lista_devoluciones')


@login_required
def comprobante_devolucion(request, pk):
    devolucion = get_object_or_404(
        Devolucion.objects.select_related(
            'venta'
        ).prefetch_related(
            'detalles__detalle_venta__presentacion__producto'
        ),
        pk=pk,
    )

    messages.success(
        request,
        f'Devolución {devolucion.numero} registrada correctamente.'
    )

    return redirect('devoluciones:lista_devoluciones')


# ════════════════════════════════════════
# DESCARGA PDF DE DEVOLUCIÓN
# ════════════════════════════════════════

@login_required
def descargar_comprobante_pdf(request, pk):
    """Genera un PDF del comprobante de devolución."""
    devolucion = get_object_or_404(
        Devolucion.objects.select_related('venta').prefetch_related(
            'detalles__detalle_venta__presentacion__producto'
        ),
        pk=pk,
    )

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.5*inch, leftMargin=0.5*inch,
        topMargin=0.5*inch,   bottomMargin=0.5*inch,
    )

    elements = []
    styles   = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2e7de9'),
        spaceAfter=6,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#0d1b2e'),
        spaceAfter=4,
        spaceBefore=4,
    )

    elements.append(Paragraph("COMPROBANTE DE DEVOLUCIÓN", title_style))
    elements.append(Spacer(1, 0.15*inch))

    # ── Información general ──────────────────────────────────────
    info_data = [
        ['Número:',   devolucion.numero,
         'Fecha:',    devolucion.fecha.strftime('%d/%m/%Y %H:%M')],
        ['Cliente:',  devolucion.venta.cliente,
         'Venta:',    f'VTA-{devolucion.venta.pk:04d}'],
        ['Motivo:',   devolucion.get_motivo_display(),
         'Reembolso:', devolucion.get_tipo_reembolso_display()],
    ]

    info_table = Table(info_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('FONT',         (0, 0), (-1, -1), 'Helvetica', 9),
        ('TEXTCOLOR',    (0, 0), (-1, -1), colors.HexColor('#333333')),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND',   (0, 0), (0, -1),  colors.HexColor('#f0f0f0')),
        ('BACKGROUND',   (2, 0), (2, -1),  colors.HexColor('#f0f0f0')),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.2*inch))

    # ── Tabla de productos ───────────────────────────────────────
    elements.append(Paragraph("Productos Devueltos", heading_style))

    productos_data = [['Producto', 'Presentación', 'Cantidad', 'P. Unitario', 'Subtotal']]
    for det in devolucion.detalles.all():
        d                = det.detalle_venta
        producto_nombre  = d.presentacion.producto.nombre if d.presentacion else '—'
        presentacion_str = d.presentacion.nombre          if d.presentacion else 'Unidad'
        productos_data.append([
            producto_nombre[:30],
            presentacion_str[:20],
            str(det.cantidad),
            f"${d.precio_unitario:,.0f}".replace(',', '.'),
            f"${d.precio_unitario * det.cantidad:,.0f}".replace(',', '.'),
        ])

    productos_table = Table(
        productos_data,
        colWidths=[2.5*inch, 1.5*inch, 0.7*inch, 1*inch, 1*inch],
    )
    productos_table.setStyle(TableStyle([
        ('FONT',           (0, 0), (-1, -1), 'Helvetica', 8),
        ('FONTNAME',       (0, 0), (-1,  0), 'Helvetica-Bold'),
        ('TEXTCOLOR',      (0, 0), (-1,  0), colors.whitesmoke),
        ('BACKGROUND',     (0, 0), (-1,  0), colors.HexColor('#2e7de9')),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',          (2, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING',    (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('GRID',           (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
    ]))
    elements.append(productos_table)
    elements.append(Spacer(1, 0.2*inch))

    # ── Total ────────────────────────────────────────────────────
    total_data = [[
        '', '', '',
        'Total Devuelto:',
        f"${devolucion.total_devuelto:,.0f}".replace(',', '.'),
    ]]
    total_table = Table(
        total_data,
        colWidths=[2.5*inch, 1.5*inch, 0.7*inch, 1.3*inch, 1*inch],
    )
    total_table.setStyle(TableStyle([
        ('FONT',         (0, 0), (-1, -1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR',    (0, 0), (-1, -1), colors.HexColor('#00e5a0')),
        ('ALIGN',        (3, 0), (-1,  0), 'RIGHT'),
        ('BACKGROUND',   (3, 0), (-1,  0), colors.HexColor('#f0f0f0')),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 0.3*inch))

    # ── Pie de página ────────────────────────────────────────────
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}"
        "<br/>CYS Ltda. — Gestión de Devoluciones",
        footer_style,
    ))

    doc.build(elements)
    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'Comprobante_Devolucion_{devolucion.numero}.pdf',
        content_type='application/pdf',
    )


# ════════════════════════════════════════
# HISTORIAL DE DEVOLUCIONES CON BÚSQUEDA
# ════════════════════════════════════════

@login_required
def historial_devoluciones(request):
    devoluciones = Devolucion.objects.select_related('venta').prefetch_related(
        'detalles__detalle_venta__presentacion__producto'
    ).order_by('-fecha')

    query = request.GET.get('q', '').strip()
    if query:
        devoluciones = (
            devoluciones.filter(venta__cliente__icontains=query)
            | devoluciones.filter(pk__icontains=query)
            | devoluciones.filter(venta__pk__icontains=query)
        )

    total_devoluciones = devoluciones.count()
    total_devuelto     = sum(d.total_devuelto for d in devoluciones)

    return render(request, 'devoluciones/historial.html', {
        'devoluciones':       devoluciones[:50],
        'query':              query,
        'total_devoluciones': total_devoluciones,
        'total_devuelto':     total_devuelto,
    })


@login_required
def detalle_devolucion(request, pk):
    devolucion = get_object_or_404(
        Devolucion.objects.select_related('venta').prefetch_related(
            'detalles__detalle_venta__presentacion__producto'
        ),
        pk=pk,
    )

    return render(request, 'ventas/devoluciones.html', {
        'devolucion': devolucion,
    })