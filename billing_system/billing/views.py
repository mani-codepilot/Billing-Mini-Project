from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from .models import Product, Denomination, Invoice, InvoiceItem
from .serializers import ProductSerializer, DenominationSerializer, InvoiceSerializer
import threading

# Helpers

def quantize(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def compute_invoice_and_change(items_payload, paid_amount):
    """
    items_payload = [{"product_id":"P1","quantity":2}, ...]
    returned dict contains totals, list of item dicts, change and denominations chosen
    """
    total_without_tax = Decimal('0.00')
    total_tax = Decimal('0.00')
    item_rows = []

    # Build items, validate stock (raise ValueError on insufficient)
    for it in items_payload:
        pid = it.get('product_id')
        qty = int(it.get('quantity', 0))
        if qty <= 0:
            raise ValueError("Quantity must be >= 1")
        product = get_object_or_404(Product, product_id=pid)
        if product.stock < qty:
            raise ValueError(f"Insufficient stock for {product.product_id}")
        price = product.price
        tax_amt = quantize((price * qty * product.tax_pct) / Decimal('100'))
        subtotal = quantize(price * qty + tax_amt)
        item_rows.append({
            "product": product,
            "name": product.name,
            "price": quantize(price),
            "quantity": qty,
            "tax_amount": tax_amt,
            "subtotal": subtotal
        })
        total_without_tax += quantize(price * qty)
        total_tax += tax_amt

    total_amount = quantize(total_without_tax + total_tax)
    paid_amount = quantize(Decimal(paid_amount))
    change_amount = quantize(max(Decimal('0.00'), paid_amount - total_amount))

    # Compute denominations greedy, respecting availability
    denom_objs = list(Denomination.objects.order_by('-value'))
    remaining = change_amount
    chosen = {}
    for d in denom_objs:
        if remaining <= 0:
            chosen[str(d.value)] = 0
            continue
        val = quantize(d.value)
        # how many of this denom we can use
        can_use = int((remaining // val).to_integral_value())  # floor
        give = min(can_use, d.count_available)
        if give > 0:
            chosen[str(d.value)] = give
            remaining = quantize(remaining - (val * give))
        else:
            chosen[str(d.value)] = 0

    if remaining != Decimal('0.00'):
        # cannot give exact change with current denominations
        exact_change_possible = False
    else:
        exact_change_possible = True

    return {
        "items": item_rows,
        "total_without_tax": quantize(total_without_tax),
        "total_tax": quantize(total_tax),
        "total_amount": quantize(total_amount),
        "paid_amount": quantize(paid_amount),
        "change_amount": quantize(change_amount),
        "denominations_chosen": chosen,
        "exact_change_possible": exact_change_possible
    }

def persist_invoice_and_update_stock_and_denoms(customer_email, computed):
    inv = Invoice.objects.create(
        customer_email=customer_email,
        total_without_tax=computed['total_without_tax'],
        total_tax=computed['total_tax'],
        total_amount=computed['total_amount'],
        paid_amount=computed['paid_amount'],
        change_amount=computed['change_amount'],
        denominations_given=computed['denominations_chosen']
    )
    # items
    for it in computed['items']:
        InvoiceItem.objects.create(
            invoice=inv,
            product=it['product'],
            name=it['name'],
            price=it['price'],
            quantity=it['quantity'],
            tax_amount=it['tax_amount'],
            subtotal=it['subtotal']
        )
        # decrement product stock
        p = it['product']
        p.stock = max(0, p.stock - it['quantity'])
        p.save()

    # update denomination counts (subtract given counts)
    for val_str, count_given in computed['denominations_chosen'].items():
        if count_given and count_given > 0:
            denom = Denomination.objects.filter(value=Decimal(val_str)).first()
            if denom:
                denom.count_available = max(0, denom.count_available - count_given)
                denom.save()

    return inv

def send_invoice_email_async(invoice_id):
    # run in background thread
    def _send(invoice_id):
        inv = Invoice.objects.get(id=invoice_id)
        subject = f"Invoice #{inv.id}"
        body_lines = [
            f"Invoice #{inv.id}",
            f"Date: {inv.created_at}",
            f"Customer: {inv.customer_email}",
            f"Total: {inv.total_amount}",
            f"Paid: {inv.paid_amount}",
            f"Change: {inv.change_amount}",
            "",
            "Items:"
        ]
        for item in inv.items.all():
            body_lines.append(f"- {item.name} x{item.quantity} @ {item.price} => {item.subtotal}")
        body = "\n".join(body_lines)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [inv.customer_email], fail_silently=True)
    t = threading.Thread(target=_send, args=(invoice_id,))
    t.start()

# DRF viewsets (protected)

from rest_framework import permissions
class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "product_id"

class DenominationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Denomination.objects.all()
    serializer_class = DenominationSerializer

class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Invoice.objects.all().order_by('-created_at')
    serializer_class = InvoiceSerializer
    

# API endpoint to create invoice (authenticated)
from rest_framework.views import APIView

class CreateInvoiceAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        payload = request.data
        customer_email = payload.get('customer_email')
        items = payload.get('items', [])
        paid_amount = payload.get('paid_amount')
        if not customer_email or not items:
            return Response({"detail":"customer_email and items required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            computed = compute_invoice_and_change(items, paid_amount)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # persist
        invoice = persist_invoice_and_update_stock_and_denoms(customer_email, computed)
        # send email async
        send_invoice_email_async(invoice.id)
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Template views (simple)
@login_required
def billing_form(request):
    # billing form page
    return render(request, "billing/bill_form.html", {})

@login_required
def billing_detail(request, invoice_id):
    inv = Invoice.objects.get(id=invoice_id)
    return render(request, "billing/bill_detail.html", {"invoice": inv})

from django.db.models import Q

@login_required
def previous_purchases(request):
    email_query = request.GET.get("email")
    invoices = []
    selected_invoice = None

    if email_query:
        invoices = Invoice.objects.filter(customer_email__iexact=email_query).order_by("-created_at")
        inv_id = request.GET.get("invoice_id")
        if inv_id:
            selected_invoice = invoices.filter(id=inv_id).first()

    return render(request, "billing/previous_purchases.html", {
        "email_query": email_query,
        "invoices": invoices,
        "selected_invoice": selected_invoice
    })
