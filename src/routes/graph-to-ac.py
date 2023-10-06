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

# data = json.loads(sys.argv[1])
data = {'file': 'https://b67746bf2162451d7611c5f5e3bde12a.cdn.bubble.io/f1696602450548x620097974325447200/%231.csv', 'logger-graph-id': '1696602904810x250681693894869000', 'dev': 'no'}
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
    x=df.iloc[:, 1],
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


# def update_graph_in_bubble(html_string, compressor_id):
#     url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Air-Compressor/{compressor_id}"
#     body = {
#         "logger-html": html_string
#     }

#     headers = {
#         "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
#         "Content-Type": "application/json"
#     }

#     response = requests.patch(url, json=body, headers=headers)
#     print(response.text)


# update_graph_in_bubble(html_string, compressor_id)
# This was using mtplotlib and converting to plotly html object to send interactive figures through the post request. The conversion from matplotlib to plotly didn't work.
# plt.scatter(df.iloc[:, 1], df.iloc[:, 2])
# plt.xlabel('Timestamp')
# plt.ylabel('Amps')
# plt.title('Amps Over Time')
# plt.xticks(rotation=45)
# mpl_fig = plt.gcf()
# plotly_fig = tls.mpl_to_plotly(mpl_fig)
# pyo.plot(plotly_fig, filename="scatterplot.html")
