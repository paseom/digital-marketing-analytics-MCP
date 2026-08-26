from marketing_analytics.connectors.google_ads import GoogleAdsConnector

connector = GoogleAdsConnector(customer_id="8339902360")
result = connector.get_audience_demographics(
    specific_date=None,
    all_time=False,
    campaign_id="23385247852"
)
print(result.by_age)
