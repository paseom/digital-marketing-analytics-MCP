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
