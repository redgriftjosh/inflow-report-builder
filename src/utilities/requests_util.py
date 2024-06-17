import requests
import urllib.parse


def get_req(type, id, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}/{id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_list_req(type, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def del_req(type, id, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}/{id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.status_code

def post_req(type, body, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()

def patch_req(type, id, body, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}/{id}"
    
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    try:
        response = requests.patch(url, json=body, headers=headers)
        response.raise_for_status()
        print(f"patched: {response.text}, {response.status_code}")
    except requests.RequestException as e:
        print(e)

def payload_file(field, encoded_data, filename):
    encoded_filename = urllib.parse.quote(filename)

    payload = {
        field: {
            "filename": encoded_filename,
            "private": False,
            "contents": encoded_data
        }
    }

    return payload

def patch_file_req(field, encoded_data, filename, type, id, dev):
    print(f"patch_file_req {filename}")
    payload = payload_file(field, encoded_data, filename)
    # print(f"payload {payload}")

    patch_req(type, id, payload, dev)