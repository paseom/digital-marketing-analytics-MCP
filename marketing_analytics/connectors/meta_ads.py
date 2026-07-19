from typing import List, Dict, Any
from marketing_analytics.connectors.base import BaseMarketingConnector
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport

class MetaAdsConnector(BaseMarketingConnector):
    """Placeholder Connector for Meta Ads (Facebook Ads)."""

    def get_platform_name(self) -> str:
        return "meta_ads"

    def fetch_account_info(self) -> AccountInfo:
        return AccountInfo(
            account_id="act_987654321",
            account_name="Meta Ads Client Workspace",
            platform=self.get_platform_name(),
            currency="EUR",
            timezone="Europe/Paris",
            status="ACTIVE"
        )

    def fetch_campaigns(self) -> List[Campaign]:
        return [
            Campaign(
                campaign_id="m-camp-101",
                campaign_name="Prospecting_Broad_Interest_EU",
                platform=self.get_platform_name(),
                status="ENABLED",
                budget=200.00,
                start_date="2026-02-01"
            ),
            Campaign(
                campaign_id="m-camp-102",
                campaign_name="Retargeting_Catalog_Sales",
                platform=self.get_platform_name(),
                status="ENABLED",
                budget=100.00,
                start_date="2026-02-15"
            ),
            Campaign(
                campaign_id="m-camp-103",
                campaign_name="Lead_Generation_Lookalike_FR",
                platform=self.get_platform_name(),
                status="PAUSED",
                budget=120.00,
                start_date="2026-04-01",
                end_date="2026-06-30"
            )
        ]

    def fetch_metrics(self, campaign_id: str) -> CampaignMetrics:
        if campaign_id == "m-camp-101":
            impressions = 80000
            clicks = 1600
            spend = 1500.00
            conversions = 35
        elif campaign_id == "m-camp-102":
            impressions = 45000
            clicks = 1125
            spend = 850.00
            conversions = 40
        elif campaign_id == "m-camp-103":
            impressions = 12000
            clicks = 240
            spend = 320.00
            conversions = 15
        else:
            impressions = 10000
            clicks = 200
            spend = 150.00
            conversions = 4

        ctr = (clicks / impressions) if impressions > 0 else 0.0
        cpc = (spend / clicks) if clicks > 0 else 0.0
        roas = ((conversions * 100.0) / spend) if spend > 0 else 0.0

        return CampaignMetrics(
            campaign_id=campaign_id,
            platform=self.get_platform_name(),
            impressions=impressions,
            clicks=clicks,
            spend=round(spend, 2),
            conversions=conversions,
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=round(roas, 2)
        )

    def generate_report_data(self, start_date: str, end_date: str) -> PlatformReport:
        impressions = 137000
        clicks = 2965
        spend = 2670.00
        conversions = 90

        ctr = clicks / impressions
        cpc = spend / clicks
        roas = (conversions * 100.0) / spend

        return PlatformReport(
            platform=self.get_platform_name(),
            impressions=impressions,
            clicks=clicks,
            spend=round(spend, 2),
            conversions=conversions,
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=round(roas, 2)
        )

    def get_api_schema(self) -> Dict[str, Any]:
        return {
            "platform": self.get_platform_name(),
            "api_version": "v19.0",
            "base_url": "https://graph.facebook.com",
            "authentication": {
                "type": "OAuth2 / Bearer Token",
                "required_fields": ["access_token"]
            },
            "endpoints": [
                {
                    "path": "/v19.0/{act_account_id}/campaigns",
                    "method": "GET",
                    "description": "Fetch list of campaigns in the ad account.",
                    "query_params": ["fields", "limit"]
                },
                {
                    "path": "/v19.0/{campaign_id}/insights",
                    "method": "GET",
                    "description": "Get conversion, spend and performance data for a campaign.",
                    "query_params": ["fields", "date_preset", "time_range"]
                }
            ]
        }

    def get_sample_data(self) -> Dict[str, Any]:
        return {
            "platform": self.get_platform_name(),
            "sample_response": {
                "data": [
                    {
                        "campaign_id": "120205555444333222",
                        "campaign_name": "Prospecting_Broad_Interest_EU",
                        "impressions": "80000",
                        "clicks": "1600",
                        "spend": "1500.00",
                        "conversions": [
                            {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "35"}
                        ]
                    }
                ],
                "paging": {
                    "cursors": {
                        "before": "MAZDZD",
                        "after": "MTZDZD"
                    }
                }
            }
        }
