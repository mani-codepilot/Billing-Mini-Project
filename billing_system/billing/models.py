from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone

class Product(models.Model):
    name = models.CharField(max_length=200)
    product_id = models.CharField(max_length=50, unique=True)
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.product_id} - {self.name}"

class Denomination(models.Model):
    # store denomination value (like 2000, 500, 100, 50, 20, 10, 5, 2, 1, 0.5)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    count_available = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-value']

    def __str__(self):
        return f"{self.value} x {self.count_available}"

class Invoice(models.Model):
    customer_email = models.EmailField()
    created_at = models.DateTimeField(default=timezone.now)
    total_without_tax = models.DecimalField(max_digits=12, decimal_places=2)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # denominations_given: {"2000.00": 1, "500.00": 0, ...}
    denominations_given = models.JSONField(default=dict)

    def __str__(self):
        return f"Invoice #{self.id} to {self.customer_email} @ {self.created_at}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.name} (Invoice {self.invoice_id})"
