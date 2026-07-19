import pytest
from marketing_analytics.connectors import registry
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, PlatformReport, MarketingReport

def test_registry_has_all_connectors():
    """Verify that all platform connectors are successfully registered."""
    connectors = registry.get_all_connectors()
    assert len(connectors) == 4
    
    platform_names = {c.get_platform_name() for c in connectors}
    expected_platforms = {"google_ads", "meta_ads", "tiktok_ads", "ga4"}
    assert platform_names == expected_platforms

def test_fetch_account_info():
    """Verify retrieving account info for a platform and all platforms."""
    # Test specific platform
    google_info = registry.fetch_account_info("google_ads")
    assert len(google_info) == 1
    assert isinstance(google_info[0], AccountInfo)
    assert google_info[0].platform == "google_ads"
    assert google_info[0].status == "ACTIVE"

    # Test all platforms
    all_info = registry.fetch_account_info()
    assert len(all_info) == 4
    platforms = {info.platform for info in all_info}
    assert "ga4" in platforms

def test_fetch_campaigns():
    """Verify retrieving campaigns."""
    # Specific platform
    meta_camps = registry.fetch_campaigns("meta_ads")
    assert len(meta_camps) > 0
    assert all(isinstance(c, Campaign) for c in meta_camps)
    assert all(c.platform == "meta_ads" for c in meta_camps)

    # All platforms
    all_camps = registry.fetch_campaigns()
    assert len(all_camps) > 0
    platforms = {c.platform for c in all_camps}
    assert {"google_ads", "meta_ads", "tiktok_ads", "ga4"}.issubset(platforms)

def test_fetch_campaign_metrics():
    """Verify campaign metrics fetching and calculated fields."""
    metrics = registry.fetch_campaign_metrics("g-camp-001", "google_ads")
    assert isinstance(metrics, CampaignMetrics)
    assert metrics.platform == "google_ads"
    assert metrics.campaign_id == "g-camp-001"
    assert metrics.impressions == 25000
    assert metrics.clicks == 1250
    assert metrics.spend == 1200.50
    assert metrics.conversions == 45
    # Math checks
    assert metrics.ctr == 0.05
    assert metrics.cpc == 0.96
    # (45 conversions * $100) / $1200.50 = 3.748 -> rounded to 3.75
    assert metrics.roas == 3.75

def test_generate_report():
    """Verify the multi-platform aggregated report generation and average calculations."""
    platforms = ["google_ads", "meta_ads", "tiktok_ads"]
    report = registry.generate_report(platforms=platforms, start_date="2026-07-01", end_date="2026-07-10")
    
    assert isinstance(report, MarketingReport)
    assert report.start_date == "2026-07-01"
    assert report.end_date == "2026-07-10"
    
    # Combined checks
    # Google Spend (3645.5) + Meta Spend (2670) + TikTok Spend (3360) = 9675.50
    assert report.total_spend == 9675.50
    # Google Conversions (136) + Meta (90) + TikTok (78) = 304
    assert report.total_conversions == 304
    # Google Clicks (4330) + Meta (2965) + TikTok (16000) = 23295
    assert report.total_clicks == 23295
    # Google Impressions (183000) + Meta (137000) + TikTok (800000) = 1120000
    assert report.total_impressions == 1120000

    # Average checks
    # CTR = 23295 / 1120000 = 0.020799 -> rounded to 0.0208
    assert report.average_ctr == 0.0208
    # CPC = 9675.50 / 23295 = 0.41534 -> rounded to 0.42
    assert report.average_cpc == 0.42
    # ROAS = (304 * 100) / 9675.50 = 3.1419 -> rounded to 3.14
    assert report.average_roas == 3.14

def test_invalid_platform_throws_error():
    """Verify that an invalid platform name raises a ValueError."""
    with pytest.raises(ValueError, match="Platform connector 'invalid_platform' is not registered"):
        registry.get_connector("invalid_platform")
