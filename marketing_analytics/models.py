from pydantic import BaseModel, Field
from typing import Optional, List, Dict

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
    campaign_type: str = Field(..., description="Advertising channel type (SEARCH, PERFORMANCE_MAX, DEMAND_GEN, SMART, dst)")

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

class AdGroup(BaseModel):
    """Ad group / ad set — level di antara Campaign dan Ad individual."""
    ad_group_id: str = Field(..., description="Unique identifier for the ad group")
    ad_group_name: str = Field(..., description="Name of the ad group")
    campaign_id: str = Field(..., description="ID of the parent campaign")
    platform: str = Field(..., description="The platform this ad group belongs to")
    status: str = Field(..., description="Ad group status (e.g., ENABLED, PAUSED, REMOVED)")
 
class Ad(BaseModel):
    """Individual ad creative."""
    ad_id: str = Field(..., description="Unique identifier for the ad")
    ad_name: Optional[str] = Field(None, description="Ad name/label if available (some ad types like RSA don't have a single name)")
    ad_group_id: str = Field(..., description="ID of the parent ad group")
    platform: str = Field(..., description="The platform this ad belongs to")
    status: str = Field(..., description="Ad status (e.g., ENABLED, PAUSED, REMOVED)")
    ad_type: str = Field(..., description="Ad format/type (e.g., RESPONSIVE_SEARCH_AD)")
 
class AdGroupMetrics(BaseModel):
    """Performance metrics for a specific ad group."""
    ad_group_id: str = Field(..., description="Ad group identifier")
    platform: str = Field(..., description="The platform")
    impressions: int
    clicks: int
    spend: float
    conversions: int
    ctr: float
    cpc: float
    roas: float
 
class AdMetrics(BaseModel):
    """Performance metrics for a specific ad."""
    ad_id: str = Field(..., description="Ad identifier")
    platform: str = Field(..., description="The platform")
    impressions: int
    clicks: int
    spend: float
    conversions: int
    ctr: float
    cpc: float
    roas: float

class AssetGroup(BaseModel):
    """Asset Group — pengganti Ad Group untuk campaign tipe Performance Max & Demand Gen."""
    asset_group_id: str = Field(..., description="Unique identifier for the asset group")
    asset_group_name: str = Field(..., description="Name of the asset group")
    campaign_id: str = Field(..., description="ID of the parent campaign")
    platform: str = Field(..., description="The platform")
    status: str = Field(..., description="Asset group status")
 
class Asset(BaseModel):
    """Individual asset (gambar/teks/video) di dalam Asset Group.
    CATATAN: Google Ads TIDAK menyediakan angka impression per-asset individual,
    cuma performance_label (LOW/GOOD/BEST). Angka metrics beneran ada di level
    AssetGroup, bukan di sini."""
    asset_id: str = Field(..., description="Unique identifier for the asset")
    asset_type: str = Field(..., description="TEXT, IMAGE, VIDEO, dll")
    content_summary: str = Field(..., description="Isi teks asset, atau placeholder [image]/[video] kalau bukan teks")
    asset_group_id: str = Field(..., description="ID of the parent asset group")
    platform: str = Field(..., description="The platform")
    performance_label: str = Field(..., description="LOW, GOOD, BEST, atau UNKNOWN — bukan angka, ini kategori dari Google")
 
class AssetGroupMetrics(BaseModel):
    """Performance metrics untuk satu Asset Group — INI yang punya angka impression asli."""
    asset_group_id: str = Field(..., description="Asset group identifier")
    platform: str = Field(..., description="The platform")
    impressions: int
    clicks: int
    spend: float
    conversions: int
    ctr: float
    cpc: float
    roas: float
class Keyword(BaseModel):
    """Search keyword — nempel di level Ad Group, nentuin kapan ad ditampilkan."""
    keyword_id: str = Field(..., description="Unique identifier for the keyword criterion")
    keyword_text: str = Field(..., description="The actual keyword text")
    match_type: str = Field(..., description="Match type (EXACT, PHRASE, BROAD)")
    ad_group_id: str = Field(..., description="ID of the parent ad group")
    platform: str = Field(..., description="The platform")
    status: str = Field(..., description="Keyword status (ENABLED, PAUSED, REMOVED)")
 
 
class KeywordMetrics(BaseModel):
    """Performance metrics for a specific keyword."""
    keyword_id: str = Field(..., description="Keyword identifier")
    platform: str = Field(..., description="The platform")
    impressions: int
    clicks: int
    spend: float
    conversions: int
    ctr: float
    cpc: float
    roas: float
    
class DailyTrend(BaseModel):
    """Satu titik data harian — dipakai untuk trend chart."""
    platform: str = Field(..., description="The platform")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    spend: float = Field(..., description="Spend for this day in account currency")
    impressions: int = Field(..., description="Impressions for this day")
    clicks: int = Field(..., description="Clicks for this day")
    ctr: float = Field(..., description="Click-Through Rate for this day")
    cpc: float = Field(..., description="Cost Per Click for this day")

class DemographicRow(BaseModel):
    """Satu baris breakdown demografi — untuk satu dimensi (age ATAU gender, tidak disilangkan)."""
    segment: str = Field(..., description="The demographic segment label, e.g. '25-34' or 'FEMALE'")
    spend: float
    impressions: int
    clicks: int
    ctr: float
    cpc: float

class AudienceDemographics(BaseModel):
    """Audience breakdown by age, gender, and (Google Ads Display only) income range."""
    platform: str = Field(..., description="The platform")
    by_age: List[DemographicRow] = Field(default_factory=list)
    by_gender: List[DemographicRow] = Field(default_factory=list)
    by_income: List[DemographicRow] = Field(
        default_factory=list,
        description="Household income bracket breakdown. Only populated for Google Ads Display Network campaigns — always empty for Search campaigns and for Meta Ads (not supported by that platform)."
    )

class TargetedInterest(BaseModel):
    """A single targeted interest/category on an ad group or ad set."""
    platform: str = Field(..., description="The platform")
    criterion_id: Optional[str] = Field(None, description="ID of the targeting criterion, if available")
    name: Optional[str] = Field(None, description="Human-readable interest name/category, if resolved")
    raw: Optional[str] = Field(None, description="Raw identifier/category string as returned by the platform API, for cases where a human-readable name isn't resolved")
    
class ForecastPoint(BaseModel):
    """Satu titik hasil proyeksi untuk tanggal tertentu di masa depan."""
    date: str = Field(..., description="Predicted date (YYYY-MM-DD)")
    spend: float = Field(..., description="Predicted spend")
    impressions: int = Field(..., description="Predicted impressions")
    clicks: int = Field(..., description="Predicted clicks")

class ForecastResult(BaseModel):
    """Hasil forecast berbasis trend historis (regresi linear sederhana)."""
    platform: str = Field(..., description="The platform")
    campaign_id: Optional[str] = Field(None, description="Campaign ID if scoped to one campaign")
    method: str = Field("linear_regression", description="Forecasting method used")
    historical_days_used: int = Field(..., description="Number of historical daily data points used to build the forecast")
    forecast: List[ForecastPoint] = Field(..., description="Predicted daily values for the requested future period")
    disclaimer: str = Field(
        "Ini proyeksi statistik dari trend historis (regresi linear), bukan forecast resmi dari platform. "
        "Akurasi terbatas untuk campaign dengan pola musiman, promo, atau perubahan budget mendadak.",
        description="Caveat to show alongside forecast results"
    )