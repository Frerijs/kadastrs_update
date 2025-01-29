import requests

url = (
    "https://utility.arcgis.com/usrsvcs/servers/"
    "4923f6b355934843b33aa92718520f12/rest/services/Hosted/"
    "Kadastrs/FeatureServer/8/query?"
    "where=1%3D1&outFields=*&returnGeometry=true&f=json"
)
resp = requests.get(url)
print(resp.status_code)
print(resp.text)  # vai resp.json() ja parsējam
