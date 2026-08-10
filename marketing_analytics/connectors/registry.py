from typing import Dict, List, Optional
from marketing_analytics.connectors.base import BaseMarketingConnector
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport, MarketingReport

class ConnectorRegistry:
    """Manages registered advertising platform connectors and coordinates multi-platform operations."""
    
    def __init__(self):
        self._connectors: Dict[str, BaseMarketingConnector] = {}

    def register_connector(self, connector: BaseMarketingConnector) -> None:
        """Register a platform connector."""
        name = connector.get_platform_name().lower()
        self._connectors[name] = connector

    def get_connector(self, platform: str) -> BaseMarketingConnector:
        """Retrieve a specific connector by platform name."""
        name = platform.lower()
        if name not in self._connectors:
            raise ValueError(f"Platform connector '{platform}' is not registered. Registered: {list(self._connectors.keys())}")
        return self._connectors[name]

    def get_all_connectors(self) -> List[BaseMarketingConnector]:
        """Get all registered platform connectors."""
        return list(self._connectors.values())

    def fetch_account_info(self, platform: Optional[str] = None) -> List[AccountInfo]:
        """Fetch account info across one or all registered platforms."""
        if platform:
            return [self.get_connector(platform).fetch_account_info()]
        return [c.fetch_account_info() for c in self.get_all_connectors()]

    def fetch_campaigns(self, platform: Optional[str] = None) -> List[Campaign]:
        """Fetch campaigns across one or all registered platforms."""
        if platform:
            return self.get_connector(platform).fetch_campaigns()
        
        all_campaigns = []
        for c in self.get_all_connectors():
            all_campaigns.extend(c.fetch_campaigns())
        return all_campaigns

    def fetch_campaign_metrics(self, campaign_id: str, platform: str) -> CampaignMetrics:
        """Fetch metrics for a campaign on a specific platform."""
        return self.get_connector(platform).fetch_metrics(campaign_id)
    
    def fetch_ad_groups(self, campaign_id: str, platform: str):
        """Fetch ad groups under a campaign on a specific platform."""
        return self.get_connector(platform).fetch_ad_groups(campaign_id)
 
    def fetch_ads(self, ad_group_id: str, platform: str):
        """Fetch ads under an ad group on a specific platform."""
        return self.get_connector(platform).fetch_ads(ad_group_id)
 
    def fetch_ad_group_metrics(self, ad_group_id: str, platform: str):
        """Fetch metrics for a specific ad group on a specific platform."""
        return self.get_connector(platform).fetch_ad_group_metrics(ad_group_id)
 
    def fetch_ad_metrics(self, ad_id: str, platform: str):
        """Fetch metrics for a specific ad on a specific platform."""
        return self.get_connector(platform).fetch_ad_metrics(ad_id)
    
    def fetch_asset_groups(self, campaign_id: str, platform: str):
        """Fetch asset groups under a campaign on a specific platform."""
        return self.get_connector(platform).fetch_asset_groups(campaign_id)
 
    def fetch_assets(self, asset_group_id: str, platform: str):
        """Fetch assets under an asset group on a specific platform."""
        return self.get_connector(platform).fetch_assets(asset_group_id)
 
    def fetch_asset_group_metrics(self, asset_group_id: str, platform: str):
        """Fetch metrics for a specific asset group on a specific platform."""
        return self.get_connector(platform).fetch_asset_group_metrics(asset_group_id)
    
    def fetch_keywords(self, ad_group_id: str, platform: str):
        """Fetch keywords under an ad group on a specific platform."""
        return self.get_connector(platform).fetch_keywords(ad_group_id)
 
    def fetch_keyword_metrics(self, keyword_id: str, platform: str):
        """Fetch metrics for a specific keyword on a specific platform."""
        return self.get_connector(platform).fetch_keyword_metrics(keyword_id)

    def generate_report(self, platforms: List[str], start_date: str, end_date: str) -> MarketingReport:
        """Generate an aggregated MarketingReport across selected platforms."""
        if not platforms:
            platforms = list(self._connectors.keys())

        platform_reports: Dict[str, PlatformReport] = {}
        total_impressions = 0
        total_clicks = 0
        total_spend = 0.0
        total_conversions = 0

        for p_name in platforms:
            connector = self.get_connector(p_name)
            p_report = connector.generate_report_data(start_date, end_date)
            platform_reports[p_name] = p_report
            
            total_impressions += p_report.impressions
            total_clicks += p_report.clicks
            total_spend += p_report.spend
            total_conversions += p_report.conversions

        # Calculated overall averages
        avg_ctr = (total_clicks / total_impressions) if total_impressions > 0 else 0.0
        avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0.0
        
        # Nominal conversion value computation (assume $100 per conversion for ROAS placeholder)
        estimated_revenue = total_conversions * 100.0
        avg_roas = (estimated_revenue / total_spend) if total_spend > 0 else 0.0

        return MarketingReport(
            start_date=start_date,
            end_date=end_date,
            platform_reports=platform_reports,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_spend=round(total_spend, 2),
            total_conversions=total_conversions,
            average_ctr=round(avg_ctr, 4),
            average_cpc=round(avg_cpc, 2),
            average_roas=round(avg_roas, 2)
        )

# Global singleton instance of registry for easier imports inside server
registry = ConnectorRegistry()
