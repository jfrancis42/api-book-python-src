import requests

response = requests.get("https://api.github.com/users/torvalds")
response.raise_for_status()

user = response.json()

print(type(user))
print(user["login"])
print(user.get("company", "N/A"))
print(user["public_repos"] + 1)
