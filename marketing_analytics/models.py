from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class AccountInfo(BaseModel):
    """Metadata about a marketing/advertiser account."""
    account_id: str = Field(..., description="Unique identifier for the account")
    account_name: str = Field(..., description="Name of the advertiser account")
    platform: str = Field(..., description="The ad platform (e.g., google_ads, meta_ads, tiktok_ads, ga4)")
    currency: str = Field(..., description="Currency code used in the account (e.g., USD, EUR, IDR)")
    timezone: str = Field(..., description="Timezone of the account (e.g., UTC, America/New_York, Asia/Jakarta)")
    status: str = Field(..., description="Status of the account (e.g., ACTIVE, SUSPENDED, PENDING)")

class Campaign(BaseModel):
    """Metadata about an ad campaign."""
    campaign_id: str = Field(..., description="Unique identifier for the campaign")
    campaign_name: str = Field(..., description="Name of the campaign")
    platform: str = Field(..., description="The platform this campaign belongs to")
    status: str = Field(..., description="Campaign delivery status (e.g., ENABLED, PAUSED, REMOVED)")
    budget: float = Field(..., description="Daily or lifetime budget of the campaign")
    start_date: str = Field(..., description="Start date of the campaign in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date of the campaign in YYYY-MM-DD format (optional)")

class CampaignMetrics(BaseModel):
    """Performance metrics for a specific campaign or aggregated platform."""
    campaign_id: Optional[str] = Field(None, description="Campaign identifier (optional if aggregated)")
    platform: str = Field(..., description="The platform (e.g., google_ads, meta_ads, tiktok_ads, ga4)")
    impressions: int = Field(..., description="Number of times ads were displayed")
    clicks: int = Field(..., description="Number of times ads were clicked")
    spend: float = Field(..., description="Total cost of delivery in account currency")
    conversions: int = Field(..., description="Number of desired conversions achieved")
    ctr: float = Field(..., description="Click-Through Rate (clicks / impressions) as a fraction/percentage")
    cpc: float = Field(..., description="Cost Per Click (spend / clicks)")
    roas: float = Field(..., description="Return on Ad Spend (revenue generated / spend). Assume nominal conversion value for placeholders.")

class PlatformReport(BaseModel):
    """Aggregated report for a single platform."""
    platform: str = Field(..., description="The platform name")
    impressions: int = Field(..., description="Total impressions")
    clicks: int = Field(..., description="Total clicks")
    spend: float = Field(..., description="Total spend")
    conversions: int = Field(..., description="Total conversions")
    ctr: float = Field(..., description="Overall Click-Through Rate")
    cpc: float = Field(..., description="Overall Cost Per Click")
    roas: float = Field(..., description="Overall Return on Ad Spend")

class MarketingReport(BaseModel):
    """An aggregated marketing report across multiple platforms."""
    start_date: str = Field(..., description="Start date of the report range (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date of the report range (YYYY-MM-DD)")
    platform_reports: Dict[str, PlatformReport] = Field(..., description="Dictionary mapping platform names to platform aggregated reports")
    total_impressions: int = Field(..., description="Combined impressions across all included platforms")
    total_clicks: int = Field(..., description="Combined clicks across all included platforms")
    total_spend: float = Field(..., description="Combined spend across all included platforms")
    total_conversions: int = Field(..., description="Combined conversions across all included platforms")
    average_ctr: float = Field(..., description="Combined Click-Through Rate")
    average_cpc: float = Field(..., description="Combined Cost Per Click")
    average_roas: float = Field(..., description="Combined Return on Ad Spend")
