"""Demonstrate XML namespace handling with ElementTree."""
import xml.etree.ElementTree as ET

# A minimal SOAP-ish response with multiple namespaces
XML = """<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/"
              xmlns:data="urn:example:data">
  <env:Body>
    <data:GetWeatherResponse>
      <data:Temperature unit="F">72</data:Temperature>
      <data:City>Denver</data:City>
    </data:GetWeatherResponse>
  </env:Body>
</env:Envelope>
"""

NS = {
    "env": "http://schemas.xmlsoap.org/soap/envelope/",
    "data": "urn:example:data",
}

root = ET.fromstring(XML)

# Without namespace: fails silently (returns None)
body_wrong = root.find("Body")
print(f"Without NS: {body_wrong}")       # None

# With namespace dict: finds the element
body = root.find("env:Body", NS)
print(f"With NS: {body.tag}")            # {http://schemas.xmlsoap.org/soap/envelope/}Body

temp = body.find("data:GetWeatherResponse/data:Temperature", NS)
print(f"Temperature: {temp.text} {temp.get('unit')}")   # 72 F
city = body.find("data:GetWeatherResponse/data:City", NS)
print(f"City: {city.text}")   # Denver
