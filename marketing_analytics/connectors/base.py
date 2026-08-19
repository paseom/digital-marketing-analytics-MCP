from abc import ABC, abstractmethod
from typing import List, Dict, Any
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport

class BaseMarketingConnector(ABC):
    """Abstract Base Class representing a Marketing Platform API Connector."""

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the unique lowercase name of the platform (e.g. 'google_ads')."""
        pass

    @abstractmethod
    def fetch_account_info(self) -> AccountInfo:
        """Fetch metadata for the configured advertiser account on this platform."""
        pass

    @abstractmethod
    def fetch_campaigns(self) -> List[Campaign]:
        """Fetch all active and paused campaigns from this platform."""
        pass

    @abstractmethod
    def fetch_metrics(self, campaign_id: str) -> CampaignMetrics:
        """Fetch performance metrics for a specific campaign on this platform."""
        pass

    @abstractmethod
    def generate_report_data(self, start_date: str, end_date: str) -> PlatformReport:
        """Fetch aggregated performance statistics for the platform within a date range."""
        pass

    @abstractmethod
    def get_api_schema(self) -> Dict[str, Any]:
        """Return the API request/response schema metadata for this platform."""
        pass

    @abstractmethod
    def get_sample_data(self) -> Dict[str, Any]:
        """Return a sample raw response payload from this platform for testing and debugging."""
        pass
    
    def fetch_ad_groups(self, campaign_id: str):
        """Fetch ad groups under a specific campaign. Optional — override if platform supports it."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung data level ad group.")
 
    def fetch_ads(self, ad_group_id: str):
        """Fetch ads under a specific ad group. Optional — override if platform supports it."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung data level ad.")
 
    def fetch_ad_group_metrics(self, ad_group_id: str):
        """Fetch performance metrics for a specific ad group. Optional."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung metrics level ad group.")
 
    def fetch_ad_metrics(self, ad_id: str):
        """Fetch performance metrics for a specific ad. Optional."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung metrics level ad.")
    
    def fetch_asset_groups(self, campaign_id: str):
        """Fetch asset groups (PMax/Demand Gen). Optional — override if platform supports it."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung data level asset group.")
 
    def fetch_assets(self, asset_group_id: str):
        """Fetch assets under a specific asset group. Optional."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung data level asset.")
 
    def fetch_asset_group_metrics(self, asset_group_id: str):
        """Fetch performance metrics for a specific asset group. Optional."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung metrics level asset group.")
    
    def fetch_keyword_metrics(self, keyword_id: str, ad_group_id: str, start_date: str = None, end_date: str = None):
        """Fetch performance metrics for a specific keyword. Optional."""
        raise NotImplementedError(f"{self.get_platform_name()} belum mendukung metrics level keyword.")