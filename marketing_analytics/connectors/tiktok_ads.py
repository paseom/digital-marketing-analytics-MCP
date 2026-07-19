from typing import List, Dict, Any
from marketing_analytics.connectors.base import BaseMarketingConnector
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport

class TikTokAdsConnector(BaseMarketingConnector):
    """Placeholder Connector for TikTok Ads."""

    def get_platform_name(self) -> str:
        return "tiktok_ads"

    def fetch_account_info(self) -> AccountInfo:
        return AccountInfo(
            account_id="7123456789012345678",
            account_name="TikTok Global Campaign Store",
            platform=self.get_platform_name(),
            currency="USD",
            timezone="Asia/Singapore",
            status="ACTIVE"
        )

    def fetch_campaigns(self) -> List[Campaign]:
        return [
            Campaign(
                campaign_id="t-camp-201",
                campaign_name="SparkAds_Influencer_CoLab",
                platform=self.get_platform_name(),
                status="ENABLED",
                budget=300.00,
                start_date="2026-03-01"
            ),
            Campaign(
                campaign_id="t-camp-202",
                campaign_name="VideoView_Trends_GenZ",
                platform=self.get_platform_name(),
                status="ENABLED",
                budget=150.00,
                start_date="2026-04-10"
            )
        ]

    def fetch_metrics(self, campaign_id: str) -> CampaignMetrics:
        if campaign_id == "t-camp-201":
            impressions = 320000
            clicks = 6400
            spend = 1920.00
            conversions = 48
        elif campaign_id == "t-camp-202":
            impressions = 480000
            clicks = 9600
            spend = 1440.00
            conversions = 30
        else:
            impressions = 50000
            clicks = 1000
            spend = 300.00
            conversions = 5

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
        impressions = 800000
        clicks = 16000
        spend = 3360.00
        conversions = 78

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
            "api_version": "v1.3",
            "base_url": "https://business-api.tiktok.com/open_api",
            "authentication": {
                "type": "Access Token",
                "required_fields": ["secret", "app_id", "access_token"]
            },
            "endpoints": [
                {
                    "path": "/v1.3/campaign/get/",
                    "method": "GET",
                    "description": "Fetch campaigns filtering by advertiser_id.",
                    "query_params": ["advertiser_id", "page", "page_size"]
                },
                {
                    "path": "/v1.3/report/integrated/get/",
                    "method": "GET",
                    "description": "Get advertiser reporting aggregated reports.",
                    "query_params": ["advertiser_id", "report_type", "data_level", "dimensions", "metrics", "start_date", "end_date"]
                }
            ]
        }

    def get_sample_data(self) -> Dict[str, Any]:
        return {
            "platform": self.get_platform_name(),
            "sample_response": {
                "code": 0,
                "message": "OK",
                "request_id": "202607101234567890abcdef",
                "data": {
                    "list": [
                        {
                            "campaign_id": "1753298572935293",
                            "campaign_name": "SparkAds_Influencer_CoLab",
                            "budget": 300.0,
                            "budget_mode": "BUDGET_MODE_DAY",
                            "status": "CAMPAIGN_STATUS_ENABLE",
                            "opt_status": "CONTROL_STATUS_ENABLE"
                        }
                    ]
                }
            }
        }
