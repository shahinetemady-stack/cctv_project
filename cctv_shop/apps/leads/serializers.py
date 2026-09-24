from rest_framework import serializers

from .models import Lead, LeadCampaign


class LeadSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "phone", "name", "city", "source", "source_display",
            "source_url", "source_title", "keyword", "category", "category_display",
            "status", "status_display", "notes",
            "sms_count", "last_sms_at", "created_at",
        ]


class LeadCampaignSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadCampaign
        fields = [
            "id", "name", "message",
            "filter_city", "filter_source", "filter_category", "filter_status", "filter_keyword",
            "status", "status_display", "total_targets", "sent_count", "failed_count",
            "started_at", "finished_at", "created_by_name", "created_at",
        ]

    def get_created_by_name(self, obj):
        u = getattr(obj, "created_by", None)
        return u.get_full_name() if u else ""
