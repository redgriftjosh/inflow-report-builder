import json
import sys
import common_functions
import pandas as pd
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import base64
import urllib.parse
import requests

def get_payload():
    data = json.loads(sys.argv[1])

    try:
        dev = data["dev"]
        if dev == 'yes':
            dev = '/version-test'
        else:
            dev = ''
    except:
        print(f"Can't find variable: dev", file=sys.stderr)
        sys.exit(1)
    
    try:
        report_id = data["report_id"]
    except:
        print(f"Can't find variable: report_id", file=sys.stderr)
        sys.exit(1)

    return dev, report_id

def get_dependencies(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    section_5 = report_json["response"]["section_5"]
    section_5_json = common_functions.get_req("section_5", section_5, dev)

    section_5_2 = section_5_json["response"]["section_5_2"]

    threshold_psi = report_json["response"]["low_15_min_acfm_threshold"]

    return threshold_psi, section_5_2

def get_df(dev, report_id):
    report_json = common_functions.get_req("report", report_id, dev)
    header_id = common_functions.get_header_id(report_json, dev)

    pressure_json = common_functions.get_req("pressure_sensor", header_id, dev)
    if "csv-psig" in pressure_json["response"]:
        pressure_csv = pressure_json["response"]["csv-psig"]
        pressure_csv = f"https:{pressure_csv}"
    else:
        common_functions.patch_req("Report", report_id, body={"loading": f"Unable to find Pressure CSV! Make sure all pressure sensors added have a CSV Uploaded", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    common_functions.patch_req("Report", report_id, body={"loading": f"Reading CSV...", "is_loading_error": "no"}, dev=dev)
    df = common_functions.csv_to_df(pressure_csv)

    if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
        common_functions.patch_req("Report", report_id, body={"loading": f"Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        df = common_functions.trim_df(report_json, df, dev)

    return df

def filter_selection(df, start_date, start_time, end_date, end_time, report_id, dev):
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        start_time = datetime.strptime(start_time, "%I:%M %p")
        start = start_date.replace(hour=start_time.hour, minute=start_time.minute)

        end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = datetime.strptime(end_time, "%I:%M %p")
        end = end_date.replace(hour=end_time.hour, minute=end_time.minute)

        df = df[(df.iloc[:, 1] >= start) & (df.iloc[:, 1] <= end)]

        return df
    except:
        common_functions.patch_req("Report", report_id, body={"loading": f"We're having some trouble Selecting the timerange you specified. Make sure the times are formatted exactly like '9:00 AM'.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

def create_graph(df, report_id, threshold_psi, section_5_2, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Generating Graph...", "is_loading_error": "no"}, dev=dev)

    avg_pressure = df.iloc[:, 2][df.iloc[:, 2] >= 80].mean()


    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=np.array(df.iloc[:, 1]),
        y=df.iloc[:, 2],
        mode='markers',  # 'markers' means it's a scatterplot
        marker=dict(size=20)
    ))

    fig.add_shape(
    type="line",
    x0=df.iloc[:, 1].min(),  # Start of the line (minimum x-value of your data for full width)
    y0=avg_pressure,  # The y-value where the line should be drawn
    x1=df.iloc[:, 1].max(),  # End of the line (maximum x-value of your data for full width)
    y1=avg_pressure,  # The y-value where the line should be drawn (same as y0 for a horizontal line)
    line=dict(
        color="Black",  # Line color
        width=8  # Line width
        ),
    )

    fig.add_annotation(
    text=f"Header - {round(avg_pressure, 1)} psig avg.",  # Text to display
    xref="paper", yref="paper",  # Use 'paper' reference for relative positioning
    x=0.5, y=0.15,  # Center of the graph (0.5, 0.5) in relative coordinates
    showarrow=False,  # Do not show an arrow pointing to the text
    font=dict(
        size=72  # Font size of the text
        )
    )

    fig.update_layout(
    title={
        'text': f" Average Pressure",
        'font': {'size': 72},  # Adjust title font size
        'y': 0.99
    },
    xaxis={
        'tickfont': {'size': 48},  # Adjust x-axis tick labels font size
        'gridcolor': 'lightgrey',
        'showgrid': True
    },
    yaxis={
        'tickfont': {'size': 48},  # Adjust y-axis tick labels font size
        'gridcolor': 'lightgrey',
        'showgrid': True,
        'range': [threshold_psi, df.iloc[:, 2].max()]
    },
    legend={'font': {'size': 48}},  # Adjust legend font size
    plot_bgcolor='white',
    paper_bgcolor='white'
    )

    fig.write_image("temp_image.jpeg", width=3840, height=2160)

    filename = "temp_image.jpeg"
    with open(filename, "rb") as img_file:
        image_data = img_file.read()
    
    encoded_filename = urllib.parse.quote(filename)

    encoded_image_data = base64.b64encode(image_data).decode('utf-8')

    payload = {
        "graph_img": {
            "filename": encoded_filename,
            "private": False,
            "contents": encoded_image_data
        }
    }

    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/section_5_2/{section_5_2}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=payload, headers=headers)
    # print(response.text)
    print(f"acfm_graph_3_min() {response.status_code, response.text}")
    common_functions.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)

def start():
    dev, report_id = get_payload()
    threshold_psi, section_5_2 = get_dependencies(report_id, dev)

    df = get_df(dev, report_id)
    
    # df = filter_selection(df, start_date, start_time, end_date, end_time, report_id, dev)

    create_graph(df, report_id, threshold_psi, section_5_2, dev)




start()