from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("gold-prices", views.GoldPriceViewSet)
router.register("metals", views.MetalTypeViewSet)
router.register("customers", views.CustomerViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("stock/", views.StockAPIView.as_view(), name="api_stock"),
    path("price-calc/", views.PriceCalcAPIView.as_view(), name="api_price_calc"),
]
