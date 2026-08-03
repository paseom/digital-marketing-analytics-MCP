import os
import logging
from typing import List, Dict, Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from marketing_analytics.connectors.base import BaseMarketingConnector
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("marketing_analytics_mcp.google_ads")

class GoogleAdsConnector(BaseMarketingConnector):
    """Real connector for Google Ads using the official Google Ads Python SDK."""

    def __init__(self, customer_id: str = None, account_label: str = None):
        self.client = self._build_client()
        self.service = self.client.get_service("GoogleAdsService")
        customer_id = customer_id or os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
        if not customer_id:
            raise ValueError(
                "No customer_id provided and GOOGLE_ADS_CUSTOMER_ID is not set."
                "e.g. export GOOGLE_ADS_CUSTOMER_ID=1234567890"
            )
        self.customer_id = customer_id.strip().replace("-", "")
        self._platform_name = f"google_ads_{account_label}" if account_label else "google_ads"

        # Reported in get_api_schema(); override if it doesn't match your installed SDK version.
        self.api_version = os.environ.get("GOOGLE_ADS_API_VERSION", "v24")
        
    @staticmethod
    def _build_client() -> GoogleAdsClient:
        """
        Local dev: reads google-ads.yaml from disk (via load_from_storage).
        Cloud Run / production: google-ads.yaml is gitignored and won't exist in the
        container, so credentials are read from env vars instead (via load_from_dict).
        Switches automatically based on whether GOOGLE_ADS_DEVELOPER_TOKEN is set.
        """
        if os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"):
            config = {
                "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
                "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
                "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
                "use_proto_plus": True,
            }
            login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
            if login_customer_id:
                config["login_customer_id"] = login_customer_id.replace("-", "")
            return GoogleAdsClient.load_from_dict(config)
 
        return GoogleAdsClient.load_from_storage("google-ads.yaml")
    
    # ---------------------------------------------------------------
    # Internal helper
    # ---------------------------------------------------------------

    def _execute_query(self, query: str, customer_id: str = None) -> list:
        cid = customer_id or self.customer_id
        try:
            stream = self.service.search_stream(customer_id=cid, query=query)
            rows = []
            for batch in stream:
                rows.extend(batch.results)
            return rows
        except GoogleAdsException as ex:
            logger.error(
                f"GoogleAdsException: request_id={ex.request_id}, "
                f"failure={ex.failure}"
            )
            raise

    def get_platform_name(self) -> str:
        return self._platform_name
    
    # ---------------------------------------------------------------
    # Account info
    # ---------------------------------------------------------------

    def fetch_account_info(self) -> AccountInfo:
        query = """
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone,
                customer.status
            FROM customer
            LIMIT 1
        """
        rows = self._execute_query(query)
        if not rows:
            raise ValueError(f"No customer found for customer_id={self.customer_id}")

        row = rows[0]
        return AccountInfo(
            account_id=str(row.customer.id),
            account_name=row.customer.descriptive_name,
            platform=self.get_platform_name(),
            currency=row.customer.currency_code,
            timezone=row.customer.time_zone,
            status=row.customer.status.name,
        )

    # ---------------------------------------------------------------
    # Campaigns
    # ---------------------------------------------------------------
    
    def fetch_campaigns(self) -> List[Campaign]:
        query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.start_date_time,
            campaign.end_date_time,
            campaign_budget.amount_micros
        FROM campaign
        ORDER BY campaign.id
        """
        rows = self._execute_query(query)
        
        campaigns = []
        for row in rows:
            campaigns.append(
                Campaign(
                    campaign_id=str(row.campaign.id),
                    campaign_name=row.campaign.name,
                    platform=self.get_platform_name(),
                    status=row.campaign.status.name,
                    budget=round(row.campaign_budget.amount_micros / 1_000_000, 2),
                    start_date=str(row.campaign.start_date_time) if row.campaign.start_date_time else "",
                    end_date=str(row.campaign.end_date_time) if row.campaign.end_date_time else None,
                )
            )
        return campaigns

    # ---------------------------------------------------------------
    # Metrics for one campaign
    # ---------------------------------------------------------------
    
    def fetch_metrics(self, campaign_id: str) -> CampaignMetrics:
        query = f"""
            SELECT
                campaign.id,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE campaign.id = {int(campaign_id)}
                AND segments.date DURING LAST_30_DAYS
        """
        rows = self._execute_query(query)

        impressions = 0
        clicks = 0
        cost_micros = 0
        conversions = 0.0
        conversions_value = 0.0

        for row in rows:
            impressions += row.metrics.impressions
            clicks += row.metrics.clicks
            cost_micros += row.metrics.cost_micros
            conversions += row.metrics.conversions
            conversions_value += row.metrics.conversions_value

        spend = cost_micros / 1_000_000
        ctr = (clicks / impressions) if impressions else 0.0
        cpc = (spend / clicks) if clicks else 0.0
        roas = (conversions_value / spend) if spend else 0.0

        return CampaignMetrics(
            campaign_id=campaign_id,
            platform=self.get_platform_name(),
            impressions=impressions,
            clicks=clicks,
            spend=round(spend, 2),
            conversions=int(conversions),
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=round(roas, 2),
        )
        
    # ---------------------------------------------------------------
    # Ad Groups
    # ---------------------------------------------------------------
 
    def fetch_ad_groups(self, campaign_id: str) -> list:
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.campaign
            FROM ad_group
            WHERE campaign.id = {int(campaign_id)}
            ORDER BY ad_group.id
        """
        rows = self._execute_query(query)
 
        from marketing_analytics.models import AdGroup
        ad_groups = []
        for row in rows:
            ad_groups.append(
                AdGroup(
                    ad_group_id=str(row.ad_group.id),
                    ad_group_name=row.ad_group.name,
                    campaign_id=campaign_id,
                    platform=self.get_platform_name(),
                    status=row.ad_group.status.name,
                )
            )
        return ad_groups
 
    # ---------------------------------------------------------------
    # Ads
    # ---------------------------------------------------------------
 
    def fetch_ads(self, ad_group_id: str) -> list:
        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.name,
                ad_group_ad.ad.type,
                ad_group_ad.status,
                ad_group_ad.ad_group
            FROM ad_group_ad
            WHERE ad_group.id = {int(ad_group_id)}
            ORDER BY ad_group_ad.ad.id
        """
        rows = self._execute_query(query)
 
        from marketing_analytics.models import Ad
        ads = []
        for row in rows:
            # Beberapa tipe ad (misal Responsive Search Ad) gak punya field "name"
            # tunggal — ad.name bisa kosong, fallback ke label generik.
            ad_name = row.ad_group_ad.ad.name or f"Ad {row.ad_group_ad.ad.id} ({row.ad_group_ad.ad.type.name})"
            ads.append(
                Ad(
                    ad_id=str(row.ad_group_ad.ad.id),
                    ad_name=ad_name,
                    ad_group_id=ad_group_id,
                    platform=self.get_platform_name(),
                    status=row.ad_group_ad.status.name,
                    ad_type=row.ad_group_ad.ad.type.name,
                )
            )
        return ads
 
    # ---------------------------------------------------------------
    # Ad Group metrics
    # ---------------------------------------------------------------
 
    def fetch_ad_group_metrics(self, ad_group_id: str):
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM ad_group
            WHERE ad_group.id = {int(ad_group_id)}
                AND segments.date DURING LAST_30_DAYS
        """
        rows = self._execute_query(query)
 
        impressions = sum(r.metrics.impressions for r in rows)
        clicks = sum(r.metrics.clicks for r in rows)
        cost_micros = sum(r.metrics.cost_micros for r in rows)
        conversions = sum(r.metrics.conversions for r in rows)
        conversions_value = sum(r.metrics.conversions_value for r in rows)
 
        spend = cost_micros / 1_000_000
        ctr = (clicks / impressions) if impressions else 0.0
        cpc = (spend / clicks) if clicks else 0.0
        roas = (conversions_value / spend) if spend else 0.0
 
        from marketing_analytics.models import AdGroupMetrics
        return AdGroupMetrics(
            ad_group_id=ad_group_id,
            platform=self.get_platform_name(),
            impressions=impressions,
            clicks=clicks,
            spend=round(spend, 2),
            conversions=int(conversions),
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=round(roas, 2),
        )
 
    # ---------------------------------------------------------------
    # Ad metrics
    # ---------------------------------------------------------------
 
    def fetch_ad_metrics(self, ad_id: str):
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM ad_group_ad
            WHERE ad_group_ad.ad.id = {int(ad_id)}
                AND segments.date DURING LAST_30_DAYS
        """
        rows = self._execute_query(query)
 
        impressions = sum(r.metrics.impressions for r in rows)
        clicks = sum(r.metrics.clicks for r in rows)
        cost_micros = sum(r.metrics.cost_micros for r in rows)
        conversions = sum(r.metrics.conversions for r in rows)
        conversions_value = sum(r.metrics.conversions_value for r in rows)
 
        spend = cost_micros / 1_000_000
        ctr = (clicks / impressions) if impressions else 0.0
        cpc = (spend / clicks) if clicks else 0.0
        roas = (conversions_value / spend) if spend else 0.0
 
        from marketing_analytics.models import AdMetrics
        return AdMetrics(
            ad_id=ad_id,
            platform=self.get_platform_name(),
            impressions=impressions,
            clicks=clicks,
            spend=round(spend, 2),
            conversions=int(conversions),
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=round(roas, 2),
        )

    # ---------------------------------------------------------------
    # Aggregated report across a date range
    # ---------------------------------------------------------------
    
    def generate_report_data(self, start_date: str, end_date: str) -> PlatformReport:
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                AND campaign.status != 'REMOVED'
        """
        rows = self._execute_query(query)

        total_impressions = 0
        total_clicks = 0
        total_cost_micros = 0
        total_conversions = 0.0
        total_conversions_value = 0.0

        for row in rows:
            total_impressions += row.metrics.impressions
            total_clicks += row.metrics.clicks
            total_cost_micros += row.metrics.cost_micros
            total_conversions += row.metrics.conversions
            total_conversions_value += row.metrics.conversions_value

        total_spend = total_cost_micros / 1_000_000
        ctr = (total_clicks / total_impressions) if total_impressions else 0.0
        cpc = (total_spend / total_clicks) if total_clicks else 0.0
        roas = (total_conversions_value / total_spend) if total_spend else 0.0

        return PlatformReport(
            platform=self.get_platform_name(),
            impressions=total_impressions,
            clicks=total_clicks,
            spend=round(total_spend, 2),
            conversions=int(total_conversions),
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=round(roas, 2),
        )
    
    # ---------------------------------------------------------------
    # Static metadata (unchanged, not a live API call)
    # ---------------------------------------------------------------

    def get_api_schema(self) -> Dict[str, Any]:
        return {
            "platform": self.get_platform_name(),
            "api_version": self.api_version,
            "base_url": "https://googleads.googleapis.com",
            "authentication": {
                "type": "OAuth2",
                "required_fields": ["developer_token", "client_id", "client_secret", "refresh_token", "customer_id"],
            },
            "endpoints": [
                {
                    "path": f"/{self.api_version}/customers/{{customer_id}}/googleAds:searchStream",
                    "method": "POST",
                    "description": "Run search query to retrieve campaigns, metrics, and account structure.",
                    "sample_query": "SELECT campaign.id, campaign.name, metrics.impressions, metrics.clicks FROM campaign",
                }
            ],
        }

    def get_sample_data(self) -> Dict[str, Any]:
        return {
            "platform": self.get_platform_name(),
            "sample_response": {
                "results": [
                    {
                        "campaign": {
                            "resourceName": "customers/1234567890/campaigns/111222333",
                            "id": "111222333",
                            "name": "Search_Brand_US",
                            "status": "ENABLED",
                            "advertisingChannelType": "SEARCH",
                        },
                        "metrics": {
                            "impressions": "25000",
                            "clicks": "1250",
                            "costMicros": "1200500000",
                            "conversions": "45.0",
                        },
                    }
                ],
                "fieldMask": "campaign.id,campaign.name,metrics.impressions,metrics.clicks,metrics.costMicros",
            },
        }