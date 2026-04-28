import requests

response = requests.get("https://api.github.com/zen")
print(response.text)
