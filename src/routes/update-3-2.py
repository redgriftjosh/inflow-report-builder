import sys
import json
import requests
from io import StringIO
import pandas as pd
from datetime import datetime, timedelta
from math import sqrt
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import base64
import urllib.parse
import common_functions


data = json.loads(sys.argv[1]) # Proper Code. Keep this
dev = data.get('dev')
if dev == 'yes':
    dev = '/version-test'
else:
    dev = ''
# next 2 lines are for running the code without the webhook. REPORT ID: 1696116368926x296884495425208300
# local_data = '{"report-id": "1696116368926x296884495425208300"}'

report_id = data.get('report-id')

print("Getting all data from common_functions.py")
my_dict_compile_master = common_functions.compile_master_df(report_id, dev)

operating_period_ids = my_dict_compile_master["operating_period_ids"]

master_df = my_dict_compile_master["master_df"]

def update_op_periods(my_dict_compile_master, operating_period_ids):
    op_per_avg_kws = my_dict_compile_master["op_per_avg_kws"]
    op_per_avg_acfms = my_dict_compile_master["op_per_avg_acfms"]
    op_per_hours_betweens = my_dict_compile_master["op_per_hours_betweens"]
    op_per_kpis = my_dict_compile_master["op_per_kpis"]

    for operating_period_id, op_per_avg_kw, op_per_avg_acfm, op_per_hours_between, op_per_kpi in zip(operating_period_ids, op_per_avg_kws, op_per_avg_acfms, op_per_hours_betweens, op_per_kpis):
        body = {
            "kW": op_per_avg_kw,
            "ACFM Made": op_per_avg_acfm,
            "Hours/yr": op_per_hours_between,
            "KPI": op_per_kpi
        }
        common_functions.patch_req("Operation-Period", operating_period_id, body, dev)

def update_peak_demends(my_dict_compile_master):
    kpi_3_2 = my_dict_compile_master["kpi_3_2"]
    max_avg_15 = my_dict_compile_master["max_avg_15"]
    max_avg_10 = my_dict_compile_master["max_avg_10"]
    max_avg_5 = my_dict_compile_master["max_avg_5"]
    max_avg_3 = my_dict_compile_master["max_avg_3"]
    max_avg_2 = my_dict_compile_master["max_avg_2"]
    low_avg_15 = my_dict_compile_master["low_avg_15"]
    kw_max_avg_15 = my_dict_compile_master["kw_max_avg_15"]

    body = {
        "15 Min Peak Flow": max_avg_15,
        "10 Min Peak Flow": max_avg_10,
        "5 Min Peak Flow": max_avg_5,
        "3 Min Peak Flow": max_avg_3,
        "2 Min Peak Flow": max_avg_2,
        "15 Min Low Flow": low_avg_15,
        "kw_max_avg_15": kw_max_avg_15,
        "kpi-3-2": kpi_3_2
    }

    common_functions.patch_req("Report", report_id, body, dev)

def update_pressures(report_id):
    print("Updating Average Pressure per Operating Period")
    report_json = common_functions.get_req("Report", report_id), dev
    if "pressure-sensor" in report_json["response"]:
        op_per_avg_pressures = common_functions.get_avg_pressures(report_json)

        print(f"Full Dictionary: {op_per_avg_pressures}")
        
        for operating_period_id, pressure in op_per_avg_pressures.items():
            print(f"For Operating Period ID: {operating_period_id} Average Pressures: {pressure}")
            p2 = list(pressure.values())
            body = {
            "P2": p2
            }
            common_functions.patch_req("Operation-Period", operating_period_id, body, dev)
    else:
        print("Nevermind, there are no pressure sensors to calculate")

def acfm_graph_3_min(master_df, report_id):
    master_df['3 Minute Average ACFMt'] = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=15, min_periods=15).mean()[::-1].fillna(0)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=np.array(master_df.iloc[:, 1]),
        y=master_df['3 Minute Average ACFMt'],
        mode='markers',  # 'markers' means it's a scatterplot
        marker=dict(size=10)
    ))

    fig.update_layout(
    title={
        'text': "ACFM Monitoring Period",
        'font': {'size': 36}  # Adjust title font size
    },
    xaxis_title="Timestamp",
    xaxis={
        'title': {
            'text': "Timestamp",
            'font': {'size': 24}  # Adjust x-axis title font size
        },
        'tickfont': {'size': 24},  # Adjust x-axis tick labels font size
        'gridcolor': 'lightgrey',
        'showgrid': True
    },
    yaxis_title="Full Monitoring - ACFM (3 min avg.)",
    yaxis={
        'title': {
            'text': "Full Monitoring - ACFM (3 min avg.)",
            'font': {'size': 24}  # Adjust y-axis title font size
        },
        'tickfont': {'size': 24},  # Adjust y-axis tick labels font size
        'gridcolor': 'lightgrey',
        'showgrid': True
    },
    legend={'font': {'size': 24}},  # Adjust legend font size
    plot_bgcolor='white',
    paper_bgcolor='white'
    )

    fig.write_image("temp_image.jpeg", width=1920, height=1080)

    filename = "temp_image.jpeg"
    with open(filename, "rb") as img_file:
        image_data = img_file.read()
    
    encoded_filename = urllib.parse.quote(filename)

    encoded_image_data = base64.b64encode(image_data).decode('utf-8')


    payload = {
        "acfm-graph-3-min": {
            "filename": encoded_filename,
            "private": False,
            "contents": encoded_image_data
        }
    }

    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/Report/{report_id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=payload, headers=headers)
    # print(response.text)
    print(f"acfm_graph_3_min() {response.status_code, response.text}")

update_op_periods(my_dict_compile_master, operating_period_ids)

update_peak_demends(my_dict_compile_master)

update_pressures(report_id)

acfm_graph_3_min(master_df, report_id)