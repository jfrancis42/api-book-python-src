"""Parse an RSS 2.0 feed using the stdlib xml module.

Uses the Python Package Index (PyPI) "new packages" feed as a real-world example.
"""
import xml.etree.ElementTree as ET
import urllib.request

RSS_URL = "https://pypi.org/rss/packages.xml"

with urllib.request.urlopen(RSS_URL) as response:
    xml_bytes = response.read()

root = ET.fromstring(xml_bytes)

# RSS 2.0 has no namespace on its core elements
channel = root.find("channel")
print(f"Feed: {channel.findtext('title')}")
print(f"Description: {channel.findtext('description')}\n")

items = channel.findall("item")
for item in items[:5]:
    title = item.findtext("title", "")
    link = item.findtext("link", "")
    pub_date = item.findtext("pubDate", "")
    print(f"  {pub_date[:16]}  {title}")
