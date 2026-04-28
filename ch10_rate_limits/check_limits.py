import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

response = requests.get(
    "https://api.github.com/rate_limit",
    headers={
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
    },
)
response.raise_for_status()

limits = response.json()["resources"]
for resource, data in limits.items():
    reset = datetime.fromtimestamp(data["reset"]).strftime("%H:%M:%S")
    print(f"{resource:12} {data['remaining']:>5}/{data['limit']} (resets {reset})")
