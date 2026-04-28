"""Convert simple XML to Python dicts."""
import xml.etree.ElementTree as ET


def element_to_dict(element):
    """Recursively convert an XML element to a Python dict.

    - Element with no children and no attributes: returns the text content.
    - Element with attributes or children: returns a dict.
    - Multiple children with the same tag: collected into a list.
    """
    children = list(element)
    if not children and not element.attrib:
        return element.text or ""

    result = {}

    if element.attrib:
        result.update({f"@{k}": v for k, v in element.attrib.items()})

    for child in children:
        key = child.tag
        if "}" in key:
            key = key.split("}", 1)[1]   # strip namespace
        value = element_to_dict(child)
        if key in result:
            existing = result[key]
            if not isinstance(existing, list):
                result[key] = [existing]
            result[key].append(value)
        else:
            result[key] = value

    if not children and element.text:
        result["#text"] = element.text

    return result


# Demo: parse an Atom feed entry
XML = """<entry xmlns="http://www.w3.org/2005/Atom">
  <title>First commit</title>
  <author><name>Linus Torvalds</name></author>
  <updated>2026-04-28T10:00:00Z</updated>
  <link href="https://github.com/torvalds/linux/commit/abc123" rel="alternate"/>
</entry>"""

import json

root = ET.fromstring(XML)
d = element_to_dict(root)
print(json.dumps(d, indent=2))
