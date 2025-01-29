import requests

headers = {
    "User-Agent": "MyStreamlitApp/1.0 (myemail@domain.com)"
}
params = {
    "format": "json",
    "limit": 5,
    "q": "Talsi"
}
r = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers)
print("Status code:", r.status_code)
print("Response:", r.text)
