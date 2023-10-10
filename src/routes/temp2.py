import requests

url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Exclusion/1696724921631x612981081364234200"

headers = {
    "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
    "Content-Type": "application/json"
}
response = requests.get(url, headers=headers)
response.raise_for_status()
print(response.json())