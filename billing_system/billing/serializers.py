from rest_framework import serializers
from .models import Product, Denomination, Invoice, InvoiceItem

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id','name','product_id','stock','price','tax_pct']

class DenominationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Denomination
        fields = ['id','value','count_available']

class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['product','name','price','tax_amount','quantity','subtotal']

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    class Meta:
        model = Invoice
        fields = ['id','customer_email','created_at','total_without_tax','total_tax','total_amount','paid_amount','change_amount','denominations_given','items']
