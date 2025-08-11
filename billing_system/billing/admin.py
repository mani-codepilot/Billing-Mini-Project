from django.contrib import admin
from .models import Product, Denomination, Invoice, InvoiceItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id','name','price','stock')

@admin.register(Denomination)
class DenominationAdmin(admin.ModelAdmin):
    list_display = ('value','count_available')

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    readonly_fields = ['name','price','tax_amount','quantity','subtotal']
    can_delete = False
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id','customer_email','created_at','total_amount')
    inlines = [InvoiceItemInline]
    readonly_fields = ['denominations_given']
