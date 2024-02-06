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

    section_5_1 = section_5_json["response"]["section_5_1"]
    section_5_1_json = common_functions.get_req("section_5_1", section_5_1, dev)

    end_time = section_5_1_json["response"]["end_time"]
    end_date = section_5_1_json["response"]["end_date"]
    start_time = section_5_1_json["response"]["start_time"]
    start_date = section_5_1_json["response"]["start_date"]
    period = section_5_1_json["response"]["period"]

    return start_date, start_time, end_date, end_time, period, report_json, section_5_1

def get_df(dev, report_id):
    report_json = common_functions.get_req("report", report_id, dev)
    if "air_compressor" in report_json["response"] and report_json["response"]["air_compressor"] != []:
        ac_ids = report_json["response"]["air_compressor"]
    else:
        common_functions.patch_req("Report", report_id, body={"loading": f"Unable to find any Air Compressors! You need at least one Air Compressor for this Chart.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    master_df = None
    cfms = []
    for idx, ac in enumerate(ac_ids):
        ac_json = common_functions.get_req("air_compressor", ac, dev)
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor ID: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        common_functions.patch_req("Report", report_id, body={"loading": f"Getting started on {ac_name}...", "is_loading_error": "no"}, dev=dev)

        if "ac_data_logger" in ac_json["response"] and ac_json["response"]["ac_data_logger"] != []:
            ac_data_logger_id = ac_json["response"]["ac_data_logger"]
            ac_data_logger_json = common_functions.get_req("ac_data_logger", ac_data_logger_id, dev)
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        if "CSV" in ac_data_logger_json["response"]:
            csv_url = ac_data_logger_json["response"]["CSV"]
            csv_url = f"https:{csv_url}"
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        common_functions.patch_req("Report", report_id, body={"loading": f"{ac_name}: Reading CSV...", "is_loading_error": "no"}, dev=dev)
        df = common_functions.csv_to_df(csv_url)
        # response = requests.get(csv_url) # Step 2: Download the CSV file
        # response.raise_for_status() # Check that the request was successful
            
        # csv_data = StringIO(response.text) # Convert CSV into text of some sort
        # df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
        common_functions.patch_req("Report", report_id, body={"loading": f"{ac_name}: Kilowatts{idx+1} Column...", "is_loading_error": "no"}, dev=dev)
        if "volts" in ac_json["response"]:
            volts = ac_json["response"]["volts"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Volts! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "pf if fifty" in ac_json["response"]:
            pf50 = ac_json["response"]["pf if fifty"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Power Factor When Less Than 50% Load! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "pf" in ac_json["response"]:
            pf = ac_json["response"]["pf"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Power Factor! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "amps less pf" in ac_json["response"]:
            amppf = ac_json["response"]["amps less pf"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Amps Less Than For Power Factor! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "BHP" in ac_json["response"]:
            bhp = ac_json["response"]["BHP"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing BHP! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        df[f"Kilowatts{idx+1}"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf))

        common_functions.patch_req("Report", report_id, body={"loading": f"{ac_name}: ACFM Column...", "is_loading_error": "no"}, dev=dev)
        # Create ACFM Column

        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Control Type! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if control == "Fixed Speed - Variable Capacity":
            cfm = 1
        else:
            if "CFM" in ac_json["response"]:
                cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
                cfms.append(cfm)
            else:
                common_functions.patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()
        df = common_functions.calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id)
        
        current_name_date = df.columns[1]
        current_name_num = df.columns[0]
        current_name_amps = df.columns[2]
        df.rename(columns={current_name_date: f"Date{idx+1}", current_name_num: f"Num{idx+1}", current_name_amps: f"Amps{idx+1}"}, inplace=True)

        # first_date = df.iloc[0, 1]

        if master_df is None:
            master_df = df
            print("added first DataFrame to master_df")
        else:
            master_df = pd.merge(master_df, df, left_on=f"Date{idx}", right_on=f"Date{idx+1}", how="outer")
            common_functions.patch_req("Report", report_id, body={"loading": f"{ac_name}: Merging with other CSVs...", "is_loading_error": "no"}, dev=dev)
            print("Merged next Dataframe with master_df")
    
    return master_df

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

def create_graph(df, period, report_id, section_5_1, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Generating Graph...", "is_loading_error": "no"}, dev=dev)

    if period == "2 minute":
        df["avg_acfm"] = df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)
        peak_acfm = df["avg_acfm"][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
    elif period == "15 minute":
        df["avg_acfm"] = df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
        peak_acfm = df["avg_acfm"][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
    elif period == "1 hour":
        df["avg_acfm"] = df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=300, min_periods=300).mean()[::-1].fillna(0)
        peak_acfm = df["avg_acfm"][::-1].rolling(window=300, min_periods=300).mean()[::-1].fillna(0).max()
        peak_acfm = df["avg_acfm"].fillna(0).max()
    else:
        common_functions.patch_req("Report", report_id, body={"loading": f"No Period Selected", "is_loading_error": "yes"}, dev=dev)
        sys.exit(1)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=np.array(df.iloc[:, 1]),
        y=df["avg_acfm"],
        mode='markers',  # 'markers' means it's a scatterplot
        marker=dict(size=20)
    ))

    fig.update_layout(
    title={
        'text': f"{period} Average ACFM",
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
        'showgrid': True
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

    peak_acfm_floor = (peak_acfm // 10) * 10

    payload = {
        "graph_img": {
            "filename": encoded_filename,
            "private": False,
            "contents": encoded_image_data
        },
        "peak_acfm": peak_acfm,
        "peak_acfm_floor": peak_acfm_floor
    }

    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/section_5_1/{section_5_1}"

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
    start_date, start_time, end_date, end_time, period, report_json, section_5_1 = get_dependencies(report_id, dev)

    df = get_df(dev, report_id)

    if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
        common_functions.patch_req("Report", report_id, body={"loading": f"Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        df = common_functions.trim_df(report_json, df, dev)
    
    df = filter_selection(df, start_date, start_time, end_date, end_time, report_id, dev)

    create_graph(df, period, report_id, section_5_1, dev)




start()