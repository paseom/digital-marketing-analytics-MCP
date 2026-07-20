import os
import json
import logging
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from marketing_analytics.connectors import registry
from marketing_analytics.models import AccountInfo, Campaign, CampaignMetrics, MarketingReport

# Configure simple logging to stderr (stdio transport safe)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marketing_analytics_mcp")

# Initialize FastMCP Server
_allowed_hosts = ["localhost:*", "127.0.0.1:*", "digital-marketing-analytics-mcp.vercel.app"]
_allowed_origins = ["http://localhost:*", "http://127.0.0.1:*", "https://digital-marketing-analytics-mcp.vercel.app"]
_vercel_url = os.environ.get("VERCEL_URL")
if _vercel_url:
    _allowed_hosts.append(_vercel_url)
    _allowed_origins.append(f"https://{_vercel_url}")
 
mcp = FastMCP(
    "Marketing Analytics Server",
    instructions="Unified API connector and reporting server for major Ad/Analytics platforms (Google Ads, Meta Ads, TikTok Ads, GA4).",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_allowed_hosts,
        allowed_origins=_allowed_origins,
    ),
)

# ==========================================
#                  TOOLS
# ==========================================

@mcp.tool()
def fetch_campaigns(platform: Optional[str] = None) -> List[Campaign]:
    """
    Fetch marketing campaigns from active platforms.
    
    Args:
        platform: Optional platform name (google_ads, meta_ads, tiktok_ads, ga4). If omitted, campaigns from all platforms are fetched.
    """
    try:
        logger.info(f"Fetching campaigns (platform={platform})")
        return registry.fetch_campaigns(platform=platform)
    except ValueError as e:
        logger.error(f"Error fetching campaigns: {e}")
        raise

@mcp.tool()
def fetch_campaign_metrics(campaign_id: str, platform: str) -> CampaignMetrics:
    """
    Fetch performance metrics for a specific campaign on a given platform.
    
    Args:
        campaign_id: Unique identifier of the campaign.
        platform: Platform name (google_ads, meta_ads, tiktok_ads, ga4).
    """
    try:
        logger.info(f"Fetching metrics for campaign '{campaign_id}' on platform '{platform}'")
        return registry.fetch_campaign_metrics(campaign_id=campaign_id, platform=platform)
    except Exception as e:
        logger.error(f"Error fetching campaign metrics: {e}")
        raise

@mcp.tool()
def fetch_account_info(platform: Optional[str] = None) -> List[AccountInfo]:
    """
    Fetch advertiser/property account metadata.
    
    Args:
        platform: Optional platform name (google_ads, meta_ads, tiktok_ads, ga4). If omitted, retrieves all configured accounts.
    """
    try:
        logger.info(f"Fetching account info (platform={platform})")
        return registry.fetch_account_info(platform=platform)
    except Exception as e:
        logger.error(f"Error fetching account info: {e}")
        raise

@mcp.tool()
def generate_report(platforms: Optional[List[str]] = None, start_date: str = "2026-07-01", end_date: str = "2026-07-10") -> MarketingReport:
    """
    Generate an aggregated performance report across multiple marketing platforms.
    
    Args:
        platforms: List of platform names to include (google_ads, meta_ads, tiktok_ads, ga4). Defaults to all platforms if empty or None.
        start_date: Report start date (YYYY-MM-DD).
        end_date: Report end date (YYYY-MM-DD).
    """
    try:
        platforms_list = platforms or []
        logger.info(f"Generating marketing report for platforms={platforms_list}, from {start_date} to {end_date}")
        return registry.generate_report(platforms=platforms_list, start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise


# ==========================================
#                RESOURCES
# ==========================================

@mcp.resource("marketing://config")
def get_account_config() -> str:
    """Get integrated marketing platform account configuration and current connection statuses."""
    try:
        accounts = registry.fetch_account_info()
        config_data = {
            "integrated_platforms": [acc.platform for acc in accounts],
            "accounts": [acc.model_dump() for acc in accounts],
            "version": "1.0.0",
            "mock_mode": True
        }
        return json.dumps(config_data, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve configuration: {str(e)}"}, indent=2)

@mcp.resource("marketing://schemas/{platform}")
def get_api_schema(platform: str) -> str:
    """
    Get the API schema and configuration template for a specific platform.
    
    Args:
        platform: The platform name (google_ads, meta_ads, tiktok_ads, ga4).
    """
    try:
        conn = registry.get_connector(platform)
        return json.dumps(conn.get_api_schema(), indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve schema for platform '{platform}': {str(e)}"}, indent=2)

@mcp.resource("marketing://sample-data/{platform}")
def get_sample_reporting_data(platform: str) -> str:
    """
    Get sample raw response data payload for testing or debugging a platform.
    
    Args:
        platform: The platform name (google_ads, meta_ads, tiktok_ads, ga4).
    """
    try:
        conn = registry.get_connector(platform)
        return json.dumps(conn.get_sample_data(), indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve sample data for platform '{platform}': {str(e)}"}, indent=2)


# ==========================================
#                PROMPTS
# ==========================================

@mcp.prompt()
def summarize_campaign_performance(platform: str, campaign_name: str) -> str:
    """
    Create a prompt template for summarizing campaign performance.
    
    Args:
        platform: Ad platform name (e.g. google_ads, meta_ads).
        campaign_name: Name of the campaign.
    """
    return (
        f"You are an expert marketing analyst. Please provide a concise, high-level summary of the performance of the campaign "
        f"'{campaign_name}' on the '{platform}' platform.\n\n"
        f"In your summary, please highlight:\n"
        f"1. Overall delivery and status.\n"
        f"2. Key performance indicators (KPIs) like clicks, impressions, CTR, CPC, and ROAS (if applicable).\n"
        f"3. Any notable performance trends or potential issues you suggest looking into.\n"
        f"4. A single sentence recommendation on whether to scale, maintain, or pause this campaign.\n\n"
        f"Keep the summary professional, action-oriented, and structured with clear bullet points."
    )

@mcp.prompt()
def analyze_marketing_metrics(metrics_json: str) -> str:
    """
    Create a prompt template for in-depth marketing metrics analysis.
    
    Args:
        metrics_json: JSON string of campaign performance metrics.
    """
    return (
        f"You are a Senior Growth Marketing Lead. Analyze the following campaign performance metrics (provided in JSON format) "
        f"for efficiency, trends, and anomalies:\n\n"
        f"{metrics_json}\n\n"
        f"Please perform the following analysis:\n"
        f"- **Cost-Efficiency**: Assess the CPC (Cost Per Click) and CPC-to-Conversion efficiency. Are we overpaying on certain targets?\n"
        f"- **Conversion Health**: Evaluate the ROAS (Return on Ad Spend) or Cost per Conversion. Is this campaign profitable?\n"
        f"- **Funnel Attrition**: Look at the CTR (Click-Through Rate). Is our ad creative compelling enough relative to the impression volume?\n"
        f"- **Actionable Recommendations**: Give 2-3 specific optimization tactics (e.g., bid strategy adjustments, creative changes, budget reallocations)."
    )

@mcp.prompt()
def recommend_campaign_optimization(performance_summary: str) -> str:
    """
    Create a prompt template for campaign optimization recommendations based on a performance summary.
    
    Args:
        performance_summary: Text summary of campaign performance.
    """
    return (
        f"You are an expert PPC/Media Buying consultant. Based on the performance summary below, "
        f"please provide strategic, highly actionable campaign optimization recommendations:\n\n"
        f"--- PERFORMANCE SUMMARY ---\n"
        f"{performance_summary}\n"
        f"---------------------------\n\n"
        f"Structure your recommendations into three specific categories:\n"
        f"1. **Budget & Bid Management** (e.g., scaling budgets, capping bids, or shifting budget to top performers)\n"
        f"2. **Audience & Targeting Tweaks** (e.g., negative keywords, exclusions, or expanding broad search/lookalikes)\n"
        f"3. **Ad Creative & Landing Page Iteration** (e.g., hook variations, call-to-actions, or layout test suggestions)\n\n"
        f"Ensure each recommendation is concrete, explaining both *what* to do and *why* it will help based on the data."
    )


def main():
    """Run the server."""
    logger.info("Starting Marketing Analytics MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()
