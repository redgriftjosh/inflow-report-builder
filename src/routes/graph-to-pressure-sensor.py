import sys
import json
import requests
from io import StringIO
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import base64
import urllib.parse
import numpy as np

data = json.loads(sys.argv[1])

csv_psig = data.get('csv_psig')
pressure_id = data.get('pressure_id')
dev = data.get('dev')
if dev == 'yes':
    dev = '/version-test'
else:
    dev = ''

print(pressure_id)

response = requests.get(csv_psig)
response.raise_for_status()
csv_data = StringIO(response.text)
df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p')

df.info()

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=np.array(df.iloc[:, 1]),
    y=df.iloc[:, 2],
    mode='markers',  # 'markers' means it's a scatterplot
    marker=dict(size=5)
))

fig.update_layout(
    title="PSIG Over Time",
    xaxis_title="Timestamp",
    yaxis_title="psig",
)

fig.write_image("temp_image.jpeg", width=1920, height=540)

filename = "temp_image.jpeg"
with open(filename, "rb") as img_file:
    image_data = img_file.read()
    
encoded_filename = urllib.parse.quote(filename)

encoded_image_data = base64.b64encode(image_data).decode('utf-8')

html_string = pio.to_html(fig, full_html=False)

payload = {
    "pressure-image": {
        "filename": encoded_filename,
        "private": False,
        "contents": encoded_image_data
    },
    "pressure-html": html_string
}

url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/pressure_sensor/{pressure_id}"

headers = {
    "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
    "Content-Type": "application/json"
}
response = requests.patch(url, json=payload, headers=headers)
print(response.text)

html_string = pio.to_html(fig, full_html=False)

def update_pressure_graph_in_bubble(html_string, pressure_id):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/pressure_sensor/{pressure_id}"
    body = {
        "pressure-html": html_string
    }

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }

    response = requests.patch(url, json=body, headers=headers)
    print(response.text)

# update_pressure_graph_in_bubble(html_string, pressure_id)