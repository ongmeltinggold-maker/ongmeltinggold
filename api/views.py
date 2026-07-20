from decimal import Decimal, InvalidOperation
from rest_framework import viewsets, mixins
from rest_framework.views import APIView
from rest_framework.response import Response

from catalog.models import GoldPrice, MetalType
from customers.models import Customer
from inventory.models import StockMovement
from sales import services
from .serializers import GoldPriceSerializer, CustomerSerializer, MetalTypeSerializer


class GoldPriceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GoldPrice.objects.all()
    serializer_class = GoldPriceSerializer


class MetalTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MetalType.objects.all()
    serializer_class = MetalTypeSerializer


class CustomerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(name_th__icontains=q) | Q(national_id__icontains=q) | Q(tel__icontains=q))
        return qs


class StockAPIView(APIView):
    """สต็อกคงเหลือแยกวัสดุ (กรัม)"""
    def get(self, request):
        data = [{"metal": m.name_th, "code": m.code,
                 "balance_gram": str(StockMovement.balance_for(m))}
                for m in MetalType.objects.all()]
        return Response(data)


class PriceCalcAPIView(APIView):
    """คำนวณราคาซื้อตามสูตร (POST: metal_code, purity, weight, is_vip, base_price?, fee_percent?)"""
    def post(self, request):
        d = request.data
        try:
            metal = MetalType.objects.get(code=d.get("metal_code"))
        except MetalType.DoesNotExist:
            return Response({"error": "ไม่พบประเภทโลหะ"}, status=400)
        try:
            r, base, fee = services.compute_buy(
                metal, d.get("purity"), d.get("weight"),
                is_vip=bool(d.get("is_vip")), base_price=d.get("base_price"),
                fee_percent=d.get("fee_percent"))
        except (InvalidOperation, TypeError, ValueError) as e:
            return Response({"error": str(e)}, status=400)
        return Response({"metal": metal.code, "base_price": str(base), "fee_percent": str(fee),
                         **r.as_dict()})
