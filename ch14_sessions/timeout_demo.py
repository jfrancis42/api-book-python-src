"""Demonstrate timeout behavior with requests."""
import requests

# Without timeout -- hangs indefinitely if server is slow
# response = requests.get("https://httpbin.org/delay/10")  # don't do this

# With connect + read timeout
try:
    # (connect_timeout_seconds, read_timeout_seconds)
    response = requests.get(
        "https://httpbin.org/delay/2",
        timeout=(5, 1),   # connect: 5s, read: 1s -- will timeout reading
    )
except requests.Timeout:
    print("Timed out waiting for response (expected)")

# With a single timeout value -- applies to each phase independently
try:
    response = requests.get("https://api.github.com/zen", timeout=10)
    print(f"GitHub zen: {response.text!r}")
except requests.Timeout:
    print("Timed out")
