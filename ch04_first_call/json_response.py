import requests

response = requests.get("https://api.github.com/users/torvalds")
response.raise_for_status()

user = response.json()
print("Login:       ", user["login"])
print("Name:        ", user["name"])
print("Public repos:", user["public_repos"])
print("Followers:   ", user["followers"])
