from datetime import date, timedelta
import os
import logging
from typing import List, Dict, Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from marketing_analytics.connectors.base import BaseMarketingConnector
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport, DailyTrend, DemographicRow, AudienceDemographics, TargetedInterest

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
            campaign.advertising_channel_type,
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
                    campaign_type=row.campaign.advertising_channel_type.name,
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
 
    def fetch_ad_group_metrics(self, ad_group_id: str, start_date: str = None, end_date: str = None):
        if not end_date:
            end_date = (date.today() - timedelta(days=1)).isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
            
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM ad_group
            WHERE ad_group.id = {int(ad_group_id)}
                AND segments.date BETWEEN '{start_date}' AND '{end_date}'
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
 
    def fetch_ad_metrics(self, ad_id: str, start_date: str = None, end_date: str = None):
        if not end_date:
            end_date = (date.today() - timedelta(days=1)).isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
            
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM ad_group_ad
            WHERE ad_group_ad.ad.id = {int(ad_id)}
                AND segments.date BETWEEN '{start_date}' AND '{end_date}'
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
    # Keywords
    # ---------------------------------------------------------------
 
    def fetch_keywords(self, ad_group_id: str) -> list:
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.ad_group
            FROM keyword_view
            WHERE ad_group.id = {int(ad_group_id)}
            ORDER BY ad_group_criterion.criterion_id
        """
        rows = self._execute_query(query)
 
        from marketing_analytics.models import Keyword
        keywords = []
        for row in rows:
            keywords.append(
                Keyword(
                    keyword_id=str(row.ad_group_criterion.criterion_id),
                    keyword_text=row.ad_group_criterion.keyword.text,
                    match_type=row.ad_group_criterion.keyword.match_type.name,
                    ad_group_id=ad_group_id,
                    platform=self.get_platform_name(),
                    status=row.ad_group_criterion.status.name,
                )
            )
        return keywords
 
    # ---------------------------------------------------------------
    # Keyword metrics
    # ---------------------------------------------------------------
 
    def fetch_keyword_metrics(self, keyword_id: str, ad_group_id: str, start_date: str = None, end_date: str = None):
        if not end_date:
            end_date = (date.today() - timedelta(days=1)).isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat() 
 
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM keyword_view
            WHERE ad_group_criterion.criterion_id = {int(keyword_id)}
                AND ad_group.id = {int(ad_group_id)}
                AND segments.date BETWEEN '{start_date}' AND '{end_date}'
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
 
        from marketing_analytics.models import KeywordMetrics
        return KeywordMetrics(
            keyword_id=keyword_id,
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
    # Asset Groups (Performance Max & Demand Gen)
    # ---------------------------------------------------------------
 
    def fetch_asset_groups(self, campaign_id: str) -> list:
        query = f"""
            SELECT
                asset_group.id,
                asset_group.name,
                asset_group.status,
                asset_group.campaign
            FROM asset_group
            WHERE campaign.id = {int(campaign_id)}
            ORDER BY asset_group.id
        """
        rows = self._execute_query(query)
 
        from marketing_analytics.models import AssetGroup
        asset_groups = []
        for row in rows:
            asset_groups.append(
                AssetGroup(
                    asset_group_id=str(row.asset_group.id),
                    asset_group_name=row.asset_group.name,
                    campaign_id=campaign_id,
                    platform=self.get_platform_name(),
                    status=row.asset_group.status.name,
                )
            )
        return asset_groups
 
    # ---------------------------------------------------------------
    # Assets (individual creative pieces di dalam asset group)
    # ---------------------------------------------------------------
 
    def fetch_assets(self, asset_group_id: str) -> list:
        query = f"""
            SELECT
                asset_group_asset.asset,
                asset_group_asset.field_type,
                asset_group_asset.performance_label,
                asset_group_asset.status,
                asset.id,
                asset.type,
                asset.text_asset.text
            FROM asset_group_asset
            WHERE asset_group.id = {int(asset_group_id)}
            ORDER BY asset.id
        """
        rows = self._execute_query(query)
 
        from marketing_analytics.models import Asset
        assets = []
        for row in rows:
            # Text asset punya isi teksnya langsung; tipe lain (IMAGE/VIDEO) gak
            # punya representasi teks, kita kasih placeholder yang jelas.
            asset_type_name = row.asset.type_.name if hasattr(row.asset, "type_") else row.asset.type.name
            if asset_type_name == "TEXT" and row.asset.text_asset.text:
                content_summary = row.asset.text_asset.text
            else:
                content_summary = f"[{asset_type_name.lower()}]"
 
            assets.append(
                Asset(
                    asset_id=str(row.asset.id),
                    asset_type=asset_type_name,
                    content_summary=content_summary,
                    asset_group_id=asset_group_id,
                    platform=self.get_platform_name(),
                    performance_label=row.asset_group_asset.performance_label.name,
                )
            )
        return assets
 
    # ---------------------------------------------------------------
    # Asset Group metrics (angka beneran, level Asset individual TIDAK punya ini)
    # ---------------------------------------------------------------
 
    def fetch_asset_group_metrics(self, asset_group_id: str):
        query = f"""
            SELECT
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM asset_group
            WHERE asset_group.id = {int(asset_group_id)}
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
 
        from marketing_analytics.models import AssetGroupMetrics
        return AssetGroupMetrics(
            asset_group_id=asset_group_id,
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
    # Date range helper — konsisten dengan MetaAdsConnector
    # ---------------------------------------------------------------
    def _resolve_date_range(self, specific_date: str = None, all_time: bool = False):
        if specific_date:
            return specific_date, specific_date
        if all_time:
            return "2000-01-01", (date.today() - timedelta(days=1)).isoformat()
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=29)
        return start.isoformat(), end.isoformat()
    
        # ---------------------------------------------------------------
    # Daily Trends
    # ---------------------------------------------------------------
    def get_daily_trends(self, specific_date: str = None, all_time: bool = False, campaign_id: str = None) -> List[DailyTrend]:
        date_start, date_end = self._resolve_date_range(specific_date, all_time)
        campaign_filter = f"AND campaign.id = {int(campaign_id)}" if campaign_id else ""

        query = f"""
            SELECT
                segments.date,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'
                AND campaign.status != 'REMOVED'
                {campaign_filter}
            ORDER BY segments.date
        """
        rows = self._execute_query(query)
        return [
            DailyTrend(
                platform=self.get_platform_name(),
                date=str(row.segments.date),
                spend=round(row.metrics.cost_micros / 1_000_000, 2),
                impressions=row.metrics.impressions,
                clicks=row.metrics.clicks,
                ctr=round(row.metrics.ctr, 4),
                cpc=round(row.metrics.average_cpc / 1_000_000, 2),
            )
            for row in rows
        ]

    # ---------------------------------------------------------------
    # Audience — Demografi (age & gender, dari 2 resource terpisah)
    # ---------------------------------------------------------------
    def get_audience_demographics(self, specific_date: str = None, all_time: bool = False, campaign_id: str = None) -> AudienceDemographics:
        date_start, date_end = self._resolve_date_range(specific_date, all_time)
        campaign_filter = f"AND campaign.id = {int(campaign_id)}" if campaign_id else ""

        age_query = f"""
            SELECT ad_group_criterion.age_range.type,
                metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.ctr, metrics.average_cpc
            FROM age_range_view
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}' {campaign_filter}
        """
        gender_query = f"""
            SELECT ad_group_criterion.gender.type,
                metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.ctr, metrics.average_cpc
            FROM gender_view
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}' {campaign_filter}
        """
        income_query = f"""
            SELECT ad_group_criterion.income_range.type,
                metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.ctr, metrics.average_cpc
            FROM income_range_view
            WHERE segments.date BETWEEN '{date_start}' AND '{date_end}' {campaign_filter}
        """

        age_rows = self._execute_query(age_query)
        gender_rows = self._execute_query(gender_query)
        income_rows = self._execute_query(income_query)

        def _aggregate_by_segment(rows, get_segment):
            """Gabungkan baris-baris dengan segment sama (misal beberapa ad group
            yang sama-sama punya baris 'AGE_RANGE_25_34') jadi satu total per segment."""
            agg: Dict[str, Dict[str, float]] = {}
            for row in rows:
                seg = get_segment(row)
                bucket = agg.setdefault(seg, {"cost_micros": 0, "impressions": 0, "clicks": 0})
                bucket["cost_micros"] += row.metrics.cost_micros
                bucket["impressions"] += row.metrics.impressions
                bucket["clicks"] += row.metrics.clicks

            result = []
            for seg, vals in agg.items():
                impressions = vals["impressions"]
                clicks = vals["clicks"]
                spend = vals["cost_micros"] / 1_000_000
                ctr = (clicks / impressions) if impressions else 0.0
                cpc = (spend / clicks) if clicks else 0.0
                result.append(DemographicRow(
                    segment=seg,
                    spend=round(spend, 2),
                    impressions=impressions,
                    clicks=clicks,
                    ctr=round(ctr, 4),
                    cpc=round(cpc, 2),
                ))
            return result

        by_age = _aggregate_by_segment(age_rows, lambda r: r.ad_group_criterion.age_range.type_.name)
        by_gender = _aggregate_by_segment(gender_rows, lambda r: r.ad_group_criterion.gender.type_.name)
        by_income = _aggregate_by_segment(income_rows, lambda r: r.ad_group_criterion.income_range.type_.name)

        return AudienceDemographics(
            platform=self.get_platform_name(),
            by_age=by_age,
            by_gender=by_gender,
            by_income=by_income,
        )

    # ---------------------------------------------------------------
    # Audience — Interests
    # ---------------------------------------------------------------
    def get_targeted_interests(self, ad_group_id: str) -> List[TargetedInterest]:
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.user_interest.user_interest_category,
                ad_group_criterion.status
            FROM ad_group_criterion
            WHERE ad_group.id = {int(ad_group_id)}
                AND ad_group_criterion.type = 'USER_INTEREST'
        """
        rows = self._execute_query(query)
        return [
            TargetedInterest(
                platform=self.get_platform_name(),
                criterion_id=str(row.ad_group_criterion.criterion_id),
                name=None,  # butuh query tambahan ke resource user_interest buat resolve nama aslinya
                raw=row.ad_group_criterion.user_interest.user_interest_category,
            )
            for row in rows
        ]
        
    # ---------------------------------------------------------------
    # Keyword Volume
    # ---------------------------------------------------------------
    def get_keyword_volume(self, seed_keywords: List[str], language_id: str = "1000", location_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        language_id default 1000 = English. Untuk Bahasa Indonesia, cek constant
        yang sesuai (biasanya 1017 untuk Indonesian, TAPI harus dikonfirmasi lewat
        GoogleAdsService languageConstants sebelum dipakai production).
        location_ids default None -> Indonesia (geoTargetConstant 2360), sesuaikan
        kalau target market beda.
        """
        if location_ids is None:
            location_ids = ["2360"]  # Indonesia

        keyword_plan_idea_service = self.client.get_service("KeywordPlanIdeaService")
        keyword_competition_level_enum = self.client.enums.KeywordPlanCompetitionLevelEnum

        request = self.client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = self.customer_id
        request.language = f"languageConstants/{language_id}"
        request.geo_target_constants = [f"geoTargetConstants/{loc}" for loc in location_ids]
        request.keyword_plan_network = self.client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        request.keyword_seed.keywords.extend(seed_keywords)

        response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

        results = []
        for idea in response:
            metrics = idea.keyword_idea_metrics
            results.append({
                "keyword_text": idea.text,
                "avg_monthly_searches": metrics.avg_monthly_searches if metrics.avg_monthly_searches else None,
                "competition": metrics.competition.name if metrics.competition else "UNKNOWN",
                "competition_index": metrics.competition_index if metrics.competition_index else None,
                "low_top_of_page_bid": round(metrics.low_top_of_page_bid_micros / 1_000_000, 2) if metrics.low_top_of_page_bid_micros else None,
                "high_top_of_page_bid": round(metrics.high_top_of_page_bid_micros / 1_000_000, 2) if metrics.high_top_of_page_bid_micros else None,
            })
        return results    
    
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