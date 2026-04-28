import requests

response = requests.get("https://api.github.com/zen")

print("Status code:", response.status_code)
print("Content-Type:", response.headers["Content-Type"])
print("Body:", response.text)
