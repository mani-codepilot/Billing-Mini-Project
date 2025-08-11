from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, DenominationViewSet, InvoiceViewSet, CreateInvoiceAPI, billing_form, billing_detail, previous_purchases

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'denominations', DenominationViewSet, basename='denomination')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/create-invoice/', CreateInvoiceAPI.as_view(), name='api-create-invoice'),
    path('', billing_form, name='billing-form'),
    path('invoice/<int:invoice_id>/', billing_detail, name='billing-detail'),
    path('previous-purchases/', previous_purchases, name='previous-purchases'),
]
