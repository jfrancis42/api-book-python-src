"""Parse an Atom feed (GitHub's commit feed) using the stdlib xml module."""
import xml.etree.ElementTree as ET
import urllib.request
import os
from dotenv import load_dotenv

load_dotenv()

# GitHub exposes Atom feeds for repository commits (no auth required for public repos)
FEED_URL = "https://github.com/torvalds/linux/commits/master.atom"

with urllib.request.urlopen(FEED_URL) as response:
    xml_bytes = response.read()

root = ET.fromstring(xml_bytes)

# The Atom namespace must be included in tag lookups
NS = {"atom": "http://www.w3.org/2005/Atom"}

title = root.find("atom:title", NS).text
print(f"Feed: {title}\n")

entries = root.findall("atom:entry", NS)
for entry in entries[:5]:
    entry_title = (entry.find("atom:title", NS).text or "").strip()
    updated = (entry.find("atom:updated", NS).text or "").strip()
    author = (entry.find("atom:author/atom:name", NS).text or "").strip()
    print(f"  {updated[:10]}  {author:20s}  {entry_title[:60]}")
