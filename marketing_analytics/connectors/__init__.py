import json
import os

from marketing_analytics.connectors.registry import registry
from marketing_analytics.connectors.google_ads import GoogleAdsConnector
from marketing_analytics.connectors.meta_ads import MetaAdsConnector
from marketing_analytics.connectors.tiktok_ads import TikTokAdsConnector
from marketing_analytics.connectors.ga4 import GA4Connector

#Google Ads multiple accounts 
accounts_json = os.environ.get("GOOGLE_ADS_ACCOUNTS")
 
if accounts_json:
    accounts = json.loads(accounts_json)
    for label, customer_id in accounts.items():
        registry.register_connector(GoogleAdsConnector(customer_id=customer_id, account_label=label))
else:
    registry.register_connector(GoogleAdsConnector())

# Instantiate and register all modular platform connectors
registry.register_connector(MetaAdsConnector())
registry.register_connector(TikTokAdsConnector())
registry.register_connector(GA4Connector())

__all__ = ["registry"]
