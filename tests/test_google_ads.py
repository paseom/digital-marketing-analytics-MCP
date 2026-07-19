from google.ads.googleads.client import GoogleAdsClient
from mcp import os

client = GoogleAdsClient.load_from_storage("google-ads.yaml")

service = client.get_service("GoogleAdsService")

query = """
SELECT
    customer.id,
    customer.descriptive_name
FROM customer
LIMIT 1
"""

response = service.search_stream(
    customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID"),
    query=query,
)

for batch in response:
    for row in batch.results:
        print(row.customer.id)
        print(row.customer.descriptive_name)