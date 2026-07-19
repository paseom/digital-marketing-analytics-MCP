# Marketing Analytics MCP Server

A modular, reusable **Model Context Protocol (MCP)** server built in Python using FastMCP. 

The server provides a unified, clean interface to interact with major advertising and analytics platforms:
- **Google Ads**
- **Meta Ads (Facebook)**
- **TikTok Ads**
- **Google Analytics 4 (GA4)**

It uses a decoupled **Connector Architecture** with a centralized **Registry**, allowing you to implement platform-specific APIs and authentication profiles later under dedicated modules without modifying the core server logic.

---

## Architecture Overview

```
D:\My Folder\Magang\I-dac\MCP (Python)\
├── marketing_analytics/
│   ├── __init__.py
│   ├── server.py             # Entrypoint and FastMCP server registration
│   ├── models.py             # Pydantic schema models for strict type safety
│   ├── connectors/
│   │   ├── __init__.py       # Auto-registers active platform connectors
│   │   ├── base.py           # Abstract BaseMarketingConnector interface
│   │   ├── registry.py       # Central orchestrator for multi-platform actions
│   │   ├── google_ads.py     # Google Ads API Connector
│   │   ├── meta_ads.py       # Meta Ads API Connector
│   │   ├── tiktok_ads.py     # TikTok Ads API Connector
│   │   └── ga4.py            # Google Analytics 4 API Connector
│   └── data/                 # Platform configuration & metadata schemas
├── tests/
│   ├── test_server.py        # Unit tests for tools, resources, and prompts
│   └── test_connectors.py    # Unit tests for connector/registry logic
├── pyproject.toml            # Package definition and dependencies
└── README.md                 # This documentation
```

### Connector Interface (`base.py`)
Every platform connector inherits from `BaseMarketingConnector` and implements the following methods:
*   `fetch_account_info() -> AccountInfo`
*   `fetch_campaigns() -> List[Campaign]`
*   `fetch_metrics(campaign_id: str) -> CampaignMetrics`
*   `generate_report_data(start_date: str, end_date: str) -> PlatformReport`
*   `get_api_schema() -> Dict[str, Any]`
*   `get_sample_data() -> Dict[str, Any]`

---

## Exposed MCP Primitives

### 🛠️ Tools
*   `fetch_account_info(platform: Optional[str])`: Returns advertiser account details (account ID, name, currency, status, etc.).
*   `fetch_campaigns(platform: Optional[str])`: Retrieves campaigns (names, budgets, statuses, dates) across one or all platforms.
*   `fetch_campaign_metrics(campaign_id: str, platform: str)`: Fetches performance metrics (impressions, clicks, spend, conversions, CPC, CTR, ROAS) for a specific campaign.
*   `generate_report(platforms: Optional[List[str]], start_date: str, end_date: str)`: Generates an aggregated marketing dashboard across platforms.

### 📄 Resources
*   `marketing://config`: Reads overall integrated accounts configuration and platform connection status.
*   `marketing://schemas/{platform}`: Reads the formal API endpoint, schema definition, and authentication requirements for a specific platform.
*   `marketing://sample-data/{platform}`: Reads mock raw payload responses from direct platform APIs for debugging and LLM context.

### 💬 Prompts
*   `summarize_campaign_performance(platform, campaign_name)`: AI prompt template tailored for summarizing campaign performance.
*   `analyze_marketing_metrics(metrics_json)`: AI prompt template for in-depth CPC, CTR, and ROAS analysis.
*   `recommend_campaign_optimization(performance_summary)`: AI prompt template for PPC strategic recommendations (bidding, creatives, targeting).

---

## Installation & Setup

### Prerequisites
*   Python 3.11+
*   Node.js (for testing via the MCP Inspector)

### 1. Initialize Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install package in development mode along with development dependencies
pip install -e ".[dev]"
```

### 2. Running Unit Tests
Validate that everything compiles and calculations match expectations:
```bash
python -m pytest
```

---

## Running and Debugging

### Using MCP Inspector
You can inspect the registered tools, resources, and prompts using the official Model Context Protocol Inspector:

```bash
npx @modelcontextprotocol/inspector .venv/Scripts/python marketing_analytics/server.py
```

### Configuring Claude Desktop
To add this server to your Claude Desktop application, open your Claude config file:
*   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
*   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following configuration (replace the directory with your actual folder path):

```json
{
  "mcpServers": {
    "marketing-analytics": {
      "command": "D:\\My Folder\\Magang\\I-dac\\MCP (Python)\\.venv\\Scripts\\python.exe",
      "args": [
        "D:\\My Folder\\Magang\\I-dac\\MCP (Python)\\marketing_analytics\\server.py"
      ]
    }
  }
}
```

Restart Claude Desktop, and you will see the new tools, resources, and prompts available!
"# MCP" 
"# digital-marketing-analytics-MCP" 
