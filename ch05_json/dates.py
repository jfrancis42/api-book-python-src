import requests
from datetime import datetime, timezone

response = requests.get("https://api.github.com/users/torvalds")
response.raise_for_status()
user = response.json()

raw = user["created_at"]
print(type(raw))

# Python 3.10 compatible: replace Z with +00:00
dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
print(dt)
print(dt.tzinfo)

print(dt.strftime("%B %d, %Y"))

now = datetime.now(timezone.utc)
age = now - dt
print(f"Account is {age.days} days old.")
