import sys
import json
import requests #to download csv from a link
from io import StringIO #We are using the StringIO class from the io module to read the CSV data from a string
import pandas as pd
import plotly.tools as tls
import plotly.offline as pyo
import plotly.graph_objects as go
import plotly.io as pio
import base64
import urllib.parse
import numpy as np

data = json.loads(sys.argv[1])
# data = {'file': 'https://b67746bf2162451d7611c5f5e3bde12a.cdn.bubble.io/f1696607311786x746368974526902900/%231.csv', 'logger-graph-id': '1696607318343x927521251863035900', 'dev': 'no'}
print(f"Incoming Webhook: {data}")
csv_url = data.get('file')
logger_graph_id = data.get('logger-graph-id')
dev = data.get('dev')
if dev == 'yes':
    dev = '/version-test'
else:
    dev = ''

response = requests.get(csv_url)
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
    title="Avg AC Current vs Timestamp",
    xaxis_title="Timestamp",
    yaxis_title="Avg AC Current (Amps)",
)

# fig.show()

# fig.write_html("scatterplot.html")

fig.write_image("temp_image.jpeg", width=1920, height=540)

filename = "temp_image.jpeg"
with open(filename, "rb") as img_file:
    image_data = img_file.read()
    
encoded_filename = urllib.parse.quote(filename)

encoded_image_data = base64.b64encode(image_data).decode('utf-8')

html_string = pio.to_html(fig, full_html=False)

payload = {
    "logger-image": {
        "filename": encoded_filename,
        "private": False,
        "contents": encoded_image_data
    },
    "logger-html": html_string
}

url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/logger-graph/{logger_graph_id}"

headers = {
    "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
    "Content-Type": "application/json"
}
response = requests.patch(url, json=payload, headers=headers)
print(response.text)
print(response.status_code)
