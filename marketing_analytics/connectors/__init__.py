from marketing_analytics.connectors.registry import registry
from marketing_analytics.connectors.google_ads import GoogleAdsConnector
from marketing_analytics.connectors.meta_ads import MetaAdsConnector
from marketing_analytics.connectors.tiktok_ads import TikTokAdsConnector
from marketing_analytics.connectors.ga4 import GA4Connector

# Instantiate and register all modular platform connectors
registry.register_connector(GoogleAdsConnector())
registry.register_connector(MetaAdsConnector())
registry.register_connector(TikTokAdsConnector())
registry.register_connector(GA4Connector())

__all__ = ["registry"]
