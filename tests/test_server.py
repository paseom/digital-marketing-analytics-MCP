import json
import pytest
from marketing_analytics.server import (
    fetch_campaigns,
    fetch_campaign_metrics,
    fetch_account_info,
    generate_report,
    get_account_config,
    get_api_schema,
    get_sample_reporting_data,
    summarize_campaign_performance,
    analyze_marketing_metrics,
    recommend_campaign_optimization
)
from marketing_analytics.models import Campaign, CampaignMetrics, AccountInfo, MarketingReport

def test_fetch_campaigns_tool():
    """Verify fetch_campaigns tool directly works as expected."""
    # Fetch all campaigns
    all_camps = fetch_campaigns()
    assert isinstance(all_camps, list)
    assert len(all_camps) > 0
    assert isinstance(all_camps[0], Campaign)

    # Fetch google campaigns
    google_camps = fetch_campaigns(platform="google_ads")
    assert all(c.platform == "google_ads" for c in google_camps)

    # Invalid platform
    with pytest.raises(ValueError):
        fetch_campaigns(platform="invalid_platform")

def test_fetch_campaign_metrics_tool():
    """Verify fetch_campaign_metrics tool works as expected."""
    metrics = fetch_campaign_metrics("utm-gads-search", "ga4")
    assert isinstance(metrics, CampaignMetrics)
    assert metrics.platform == "ga4"
    assert metrics.campaign_id == "utm-gads-search"
    assert metrics.impressions == 50000
    assert metrics.spend == 0.00
    assert metrics.ctr == 0.084

def test_fetch_account_info_tool():
    """Verify fetch_account_info tool works as expected."""
    info = fetch_account_info()
    assert isinstance(info, list)
    assert len(info) == 4
    assert isinstance(info[0], AccountInfo)

    meta_info = fetch_account_info(platform="meta_ads")
    assert len(meta_info) == 1
    assert meta_info[0].currency == "EUR"

def test_generate_report_tool():
    """Verify generate_report tool works as expected."""
    report = generate_report(platforms=["meta_ads", "tiktok_ads"])
    assert isinstance(report, MarketingReport)
    # Meta (2670) + TikTok (3360) = 6030
    assert report.total_spend == 6030.00

def test_config_resource():
    """Verify get_account_config resource returns valid JSON."""
    config_json = get_account_config()
    data = json.loads(config_json)
    assert "integrated_platforms" in data
    assert "accounts" in data
    assert data["mock_mode"] is True
    assert len(data["integrated_platforms"]) == 4

def test_schema_resource():
    """Verify get_api_schema resource returns correct schema JSON."""
    schema_json = get_api_schema(platform="tiktok_ads")
    data = json.loads(schema_json)
    assert data["platform"] == "tiktok_ads"
    assert "base_url" in data
    assert "endpoints" in data

    # Error payload for invalid platform
    error_json = get_api_schema(platform="invalid")
    err_data = json.loads(error_json)
    assert "error" in err_data

def test_sample_data_resource():
    """Verify get_sample_reporting_data resource returns valid sample data."""
    sample_json = get_sample_reporting_data(platform="google_ads")
    data = json.loads(sample_json)
    assert data["platform"] == "google_ads"
    assert "sample_response" in data

    error_json = get_sample_reporting_data(platform="invalid")
    err_data = json.loads(error_json)
    assert "error" in err_data

def test_summarize_campaign_performance_prompt():
    """Verify prompt formatting for summarize_campaign_performance."""
    prompt = summarize_campaign_performance(platform="meta_ads", campaign_name="Prospecting_Broad")
    assert "expert marketing analyst" in prompt
    assert "Prospecting_Broad" in prompt
    assert "meta_ads" in prompt

def test_analyze_marketing_metrics_prompt():
    """Verify prompt formatting for analyze_marketing_metrics."""
    metrics_str = '{"ctr": 0.05, "spend": 1000}'
    prompt = analyze_marketing_metrics(metrics_json=metrics_str)
    assert "Senior Growth Marketing Lead" in prompt
    assert metrics_str in prompt

def test_recommend_campaign_optimization_prompt():
    """Verify prompt formatting for recommend_campaign_optimization."""
    summary_text = "Campaign conversion is down but CTR is high."
    prompt = recommend_campaign_optimization(performance_summary=summary_text)
    assert "strategic, highly actionable campaign optimization recommendations" in prompt
    assert summary_text in prompt
