from rest_framework import serializers
from catalog.models import GoldPrice, MetalType
from customers.models import Customer


class GoldPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoldPrice
        fields = ["id", "date", "bar_sell", "bar_buy", "jewelry_buy"]


class MetalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetalType
        fields = ["id", "code", "name_th", "formula", "vat_exempt"]


class CustomerSerializer(serializers.ModelSerializer):
    vip = serializers.BooleanField(read_only=True)
    masked_national_id = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "national_id", "masked_national_id", "name_th", "name_en",
                  "tel", "address", "is_vip", "vip", "member_rank"]
