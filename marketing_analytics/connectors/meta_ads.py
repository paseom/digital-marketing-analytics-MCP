import os
import logging
from datetime import date, timedelta
from typing import List, Dict, Any

import requests

from marketing_analytics.connectors.base import BaseMarketingConnector
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("marketing_analytics_mcp.meta_ads")

GRAPH_API_VERSION = "v21.0"  # cek versi terbaru di developers.facebook.com/docs/graph-api/changelog kalau ada error deprecated
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaAdsConnector(BaseMarketingConnector):
    """Real connector for Meta Ads (Facebook/Instagram) using the Graph Marketing API directly."""

    def __init__(self, ad_account_id: str = None, access_token: str = None, account_label: str = None):
        self.ad_account_id = (ad_account_id or "").strip()
        self.access_token = access_token or os.environ.get("META_ACCESS_TOKEN")

        if not self.ad_account_id:
            raise ValueError("META_AD_ACCOUNT_ID is not set")

        # Meta Ads API menggunakan prefix "act_" pada Ad Account ID
        if not self.ad_account_id.startswith("act_"):
            self.ad_account_id = f"act_{self.ad_account_id}"

        if not self.access_token:
            raise ValueError("META_ACCESS_TOKEN is not set")

        self._platform_name = f"meta_ads_{account_label}" if account_label else "meta_ads"

    def get_platform_name(self) -> str:
        return self._platform_name

    # ---------------------------------------------------------------
    # Internal helper
    # ---------------------------------------------------------------

    def _get(self, path: str, params: dict) -> dict:
        params = {**params, "access_token": self.access_token}
        resp = requests.get(f"{GRAPH_API_BASE}/{path}", params=params, timeout=30)
        data = resp.json()
        if "error" in data:
            logger.error(f"Meta Graph API error: {data['error']}")
            raise ValueError(f"Meta Ads API error: {data['error'].get('message', data['error'])}")
        return data

    # ---------------------------------------------------------------
    # Account info
    # ---------------------------------------------------------------

    def fetch_account_info(self) -> AccountInfo:
        data = self._get(
            self.ad_account_id,
            {"fields": "name,currency,timezone_name,account_status"},
        )
        # account_status: 1 = ACTIVE, 2 = DISABLED, 3 = UNSETTLED, dst — mapping sederhana
        status_map = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW", 9: "IN_GRACE_PERIOD"}
        return AccountInfo(
            account_id=self.ad_account_id,
            account_name=data.get("name", ""),
            platform=self.get_platform_name(),
            currency=data.get("currency", ""),
            timezone=data.get("timezone_name", ""),
            status=status_map.get(data.get("account_status"), "UNKNOWN"),
        )

    # ---------------------------------------------------------------
    # Campaigns
    # ---------------------------------------------------------------

    def fetch_campaigns(self) -> List[Campaign]:
        data = self._get(
            f"{self.ad_account_id}/campaigns",
            {
                "fields": "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time",
                "limit": 100,
            },
        )
        campaigns = []
        for item in data.get("data", []):
            # Meta budget dalam sen/cent (bukan micros kayak Google Ads) — bagi 100
            budget_raw = item.get("daily_budget") or item.get("lifetime_budget") or "0"
            campaigns.append(
                Campaign(
                    campaign_id=item["id"],
                    campaign_name=item["name"],
                    platform=self.get_platform_name(),
                    status=item.get("status", "UNKNOWN"),
                    budget=round(int(budget_raw) / 100, 2),
                    start_date=item.get("start_time", "")[:10] if item.get("start_time") else "",
                    end_date=item.get("stop_time", "")[:10] if item.get("stop_time") else None,
                    campaign_type=item.get("objective", "UNKNOWN"),  # Meta gak punya "channel type" kayak Google, dipetakan ke objective
                )
            )
        return campaigns

    # ---------------------------------------------------------------
    # Metrics for one campaign
    # ---------------------------------------------------------------

    def fetch_metrics(self, campaign_id: str, start_date: str = None, end_date: str = None) -> CampaignMetrics:
        if not end_date:
            end_date = (date.today() - timedelta(days=1)).isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()

        data = self._get(
            f"{campaign_id}/insights",
            {
                "fields": "impressions,clicks,spend,actions",
                "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
            },
        )
        rows = data.get("data", [])
        if not rows:
            impressions, clicks, spend, conversions = 0, 0, 0.0, 0
        else:
            row = rows[0]  # insights tanpa breakdown balikin 1 baris agregat
            impressions = int(row.get("impressions", 0))
            clicks = int(row.get("clicks", 0))
            spend = float(row.get("spend", 0))
            # "conversions" di Meta itu custom per advertiser (lewat Pixel/custom event),
            # bukan 1 metric tunggal kayak Google Ads. Ini sum SEMUA action type
            # sebagai pendekatan awal — SESUAIKAN action_type spesifik (misal
            # "purchase", "lead") sesuai conversion event yang dipake i-DAC.
            conversions = sum(int(a.get("value", 0)) for a in row.get("actions", []))

        ctr = (clicks / impressions) if impressions else 0.0
        cpc = (spend / clicks) if clicks else 0.0
        roas = 0.0  # butuh action_values buat hitung revenue, ditambahin nanti kalau perlu

        return CampaignMetrics(
            campaign_id=campaign_id,
            platform=self.get_platform_name(),
            impressions=impressions,
            clicks=clicks,
            spend=round(spend, 2),
            conversions=conversions,
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=roas,
        )

    # ---------------------------------------------------------------
    # Aggregated report across a date range
    # ---------------------------------------------------------------

    def generate_report_data(self, start_date: str, end_date: str) -> PlatformReport:
        data = self._get(
            f"{self.ad_account_id}/insights",
            {
                "fields": "impressions,clicks,spend,actions",
                "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
                "level": "account",
            },
        )
        rows = data.get("data", [])
        if not rows:
            impressions, clicks, spend, conversions = 0, 0, 0.0, 0
        else:
            row = rows[0]
            impressions = int(row.get("impressions", 0))
            clicks = int(row.get("clicks", 0))
            spend = float(row.get("spend", 0))
            conversions = sum(int(a.get("value", 0)) for a in row.get("actions", []))

        ctr = (clicks / impressions) if impressions else 0.0
        cpc = (spend / clicks) if clicks else 0.0

        return PlatformReport(
            platform=self.get_platform_name(),
            impressions=impressions,
            clicks=clicks,
            spend=round(spend, 2),
            conversions=conversions,
            ctr=round(ctr, 4),
            cpc=round(cpc, 2),
            roas=0.0,
        )

    # ---------------------------------------------------------------
    # Static metadata
    # ---------------------------------------------------------------

    def get_api_schema(self) -> Dict[str, Any]:
        return {
            "platform": self.get_platform_name(),
            "api_version": GRAPH_API_VERSION,
            "base_url": GRAPH_API_BASE,
            "authentication": {
                "type": "OAuth2 (System User Access Token recommended)",
                "required_fields": ["access_token", "ad_account_id"],
            },
            "endpoints": [
                {
                    "path": "/{ad_account_id}/campaigns",
                    "method": "GET",
                    "description": "List campaigns for the ad account.",
                },
                {
                    "path": "/{campaign_id}/insights",
                    "method": "GET",
                    "description": "Performance metrics for a campaign within a date range.",
                },
            ],
        }

    def get_sample_data(self) -> Dict[str, Any]:
        return {
            "platform": self.get_platform_name(),
            "sample_response": {
                "data": [
                    {
                        "id": "120210000000000",
                        "name": "Sample Campaign",
                        "status": "ACTIVE",
                        "objective": "OUTCOME_TRAFFIC",
                        "daily_budget": "50000",
                    }
                ]
            },
        }