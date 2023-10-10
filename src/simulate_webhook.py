import requests


url = "http://localhost:3000/reset-dataset-7-2"
data = {
    "report_id": "1234567890abcdefghijklmnopqrstuvwxyz",
    "dev": "yes"
}
response = requests.post(url, json=data)
print(response.text)