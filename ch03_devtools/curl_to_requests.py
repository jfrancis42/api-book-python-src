"""
Demonstrates the manual translation of a cURL command to Python requests.

Given this cURL command from DevTools:

    curl 'https://api.github.com/repos/torvalds/linux/issues' \
      -X POST \
      -H 'Accept: application/vnd.github+json' \
      -H 'Authorization: Bearer YOUR_TOKEN' \
      -H 'Content-Type: application/json' \
      -d '{"title": "Test issue", "body": "Created from curl translation example"}'

The equivalent requests code is below.
"""

import requests

# cURL -H flags become the headers dict.
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": "Bearer YOUR_TOKEN",   # replace with your token
    "Content-Type": "application/json",
}

# cURL -d with JSON becomes the json= parameter (requests sets Content-Type automatically).
# Note: when using json=, omit "Content-Type" from headers -- requests adds it.
body = {
    "title": "Test issue",
    "body": "Created from curl translation example",
}

# cURL -X POST with a URL becomes requests.post().
response = requests.post(
    "https://api.github.com/repos/torvalds/linux/issues",
    headers=headers,
    json=body,
)

print(f"Status: {response.status_code}")

if response.status_code == 201:
    issue = response.json()
    print(f"Created issue #{issue['number']}: {issue['title']}")
    print(f"URL: {issue['html_url']}")
else:
    print(f"Error: {response.text}")
