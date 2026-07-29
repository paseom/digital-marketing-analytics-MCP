# Marketing Analytics MCP Server

A **Model Context Protocol (MCP)** server built in Python using FastMCP, connecting AI agents to real advertising platform data — currently live with **Google Ads**, with a modular connector architecture ready for Meta Ads, TikTok Ads, and GA4.

**🔗 Live chat interface:** [digital-marketing-mcp.streamlit.app](https://digital-marketing-mcp.streamlit.app) (login required, restricted to internal email domain)
**🔗 MCP server endpoint:** `https://digital-marketing-analytics-mcp.vercel.app/`

📘 **Untuk arsitektur lengkap, deployment guide, dan troubleshooting, lihat [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md).**

---

## Status Connector

| Platform | Status |
|---|---|
| Google Ads | ✅ Real |
| Meta Ads | ⚠️ Placeholder (dummy) |
| TikTok Ads | ⚠️ Placeholder (dummy) |
| GA4 | ⚠️ Placeholder (dummy) |

---

## Arsitektur

```
Streamlit Chat (frontend)  ──▶  MCP Server (Vercel, FastMCP)  ──▶  Google Ads API
        │
        ▼
   Gemini API (tool-calling)
```

- **MCP server** (`marketing_analytics/`) di-deploy ke **Vercel** sebagai Streamable HTTP endpoint (serverless)
- **Chat frontend** (`Frontend/`) di-deploy ke **Streamlit Community Cloud**, connect ke MCP server + Gemini API
- Dua komponen ini independen, hosting terpisah, connect lewat URL publik

Detail penuh (kenapa pilihan arsitektur ini, gotcha teknis pas deploy, dll) ada di [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md).

### Connector Interface (`base.py`)

Setiap connector platform wajib implementasi:

- `fetch_account_info() -> AccountInfo`
- `fetch_campaigns() -> List[Campaign]`
- `fetch_metrics(campaign_id: str) -> CampaignMetrics`
- `generate_report_data(start_date: str, end_date: str) -> PlatformReport`
- `get_api_schema() -> Dict[str, Any]`
- `get_sample_data() -> Dict[str, Any]`

---

## Struktur Repo

```
├── marketing_analytics/
│   ├── server.py             
│   ├── models.py            
│   └── connectors/
│       ├── __init__.py         
│       ├── base.py               
│       ├── registry.py           
│       ├── google_ads.py          
│       ├── meta_ads.py              # ⚠️ Dummy
│       ├── tiktok_ads.py             # ⚠️ Dummy
│       └── ga4.py                     # ⚠️ Dummy
├── api/
│   └── index.py             
├── Frontend/
│   └── app.py                
├── tests/
├── vercel.json
└── pyproject.toml               
```

---

## Exposed MCP Primitives

### 🛠️ Tools

- `fetch_account_info(platform: Optional[str])` — detail akun iklan (nama, currency, status), semua akun kalau `platform` tidak diisi
- `fetch_campaigns(platform: Optional[str])` — daftar campaign (nama, budget, status, tanggal)
- `fetch_campaign_metrics(campaign_id: str, platform: str)` — metrics performa (impressions, clicks, spend, conversions, CPC, CTR, ROAS)
- `generate_report(platforms: Optional[List[str]], start_date: str, end_date: str)` — laporan agregat lintas platform/akun

### 📄 Resources

- `marketing://config` — status koneksi & daftar akun terintegrasi
- `marketing://schemas/{platform}` — skema API & auth requirement per platform
- `marketing://sample-data/{platform}` — contoh raw payload buat debugging

### 💬 Prompts

- `summarize_campaign_performance(platform, campaign_name)`
- `analyze_marketing_metrics(metrics_json)`
- `recommend_campaign_optimization(performance_summary)`

---

## Setup Lokal

### Prasyarat

- Python 3.11+
- Node.js (buat MCP Inspector)

### 1. Install dependency

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux

pip install -e ".[dev]"
```

### 2. Isi credential

Copy `google-ads.yaml.example` → `google-ads.yaml`, isi credential Google Ads asli. **Jangan commit file ini** (sudah di-`.gitignore`).

### 3. Jalankan test

```bash
python -m pytest
```

### 4. Debug pakai MCP Inspector

```bash
npx @modelcontextprotocol/inspector .venv/Scripts/python marketing_analytics/server.py
```

Untuk test versi yang sudah di-deploy (Vercel), pakai transport **Streamable HTTP** di Inspector, URL: `https://digital-marketing-analytics-mcp.vercel.app/`.

### 5. Jalankan chat frontend lokal

```bash
cd Frontend
pip install -r requirements.txt
streamlit run app.py
```

Butuh `Frontend/.streamlit/secrets.toml` terisi (lihat [DEVELOPER_GUIDE.md §3](./DEVELOPER_GUIDE.md#3-environment-variables--referensi-lengkap)).

---

## Deployment

Panduan lengkap + daftar error yang pernah kejadian dan cara benerinnya ada di **[DEVELOPER_GUIDE.md §8](./DEVELOPER_GUIDE.md#8-deploy--panduan--gotcha-yang-pernah-kejadian)**.

Ringkas:
- **Backend** → Vercel, Streamable HTTP transport, env var di dashboard Vercel
- **Frontend** → Streamlit Community Cloud, secrets di dashboard Streamlit, auth via Google OAuth (domain-restricted)