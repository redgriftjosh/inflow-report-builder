import base64
from datetime import datetime
import json
import sys
import urllib.parse
import pandas as pd
import requests
import common_functions
import plotly.graph_objects as go
import numpy as np
from utilities import compressor_util

def add_header_pressure_to_master_df(master_df, report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    master_df_pressure = None

    # low_pressures_15 = []

    if "pressure_sensor" in report_json["response"]:
        pressure_sensors = report_json["response"]["pressure_sensor"]
        for pressure_sensor in pressure_sensors:
            pressure_sensor_json = common_functions.get_req("pressure_sensor", pressure_sensor, dev)

            if pressure_sensor_json["response"]["header"]:
                pressure_csv = pressure_sensor_json["response"]["csv-psig"]
                pressure_csv = f"https:{pressure_csv}"

                df = common_functions.csv_to_df(pressure_csv)

                current_name_date = df.columns[1]
                current_name_num = df.columns[0]
                current_name_pressure = df.columns[2]
                df.rename(columns={current_name_date: f"Date{100}", current_name_num: f"Num{100}", current_name_pressure: f"Pressure{pressure_sensor}"}, inplace=True)

                if master_df_pressure is None:
                    master_df_pressure = pd.merge(master_df, df, left_on=f"Date1", right_on=f"Date{100}", how="outer")

                else:
                    master_df_pressure = pd.merge(master_df_pressure, df, left_on=f"Date1", right_on=f"Date{100}", how="outer")

        return master_df_pressure
    else:
        return master_df

def compile_df(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    if "air_compressor" in report_json["response"] and report_json["response"]["air_compressor"] != []:
        ac_ids = report_json["response"]["air_compressor"]
    else:
        common_functions.patch_req("Report", report_id, body={"loading": f"Unable to find any Air Compressors! You need at least one Air Compressor for this Chart.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    my_dict = {}

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
        
        cfm = compressor_util.get_cfm(control, ac_json, ac_name, dev)
        cfms.append(cfm)

        df = common_functions.calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id)
        
        current_name_date = df.columns[1]
        current_name_num = df.columns[0]
        current_name_amps = df.columns[2]
        df.rename(columns={current_name_date: f"Date{idx+1}", current_name_num: f"Num{idx+1}", current_name_amps: f"Amps{idx+1}"}, inplace=True)
        # df.to_csv(f"DataFrame index: {idx}.csv", index=False)

        # first_date = df.iloc[0, 1]

        if master_df is None:
            master_df = df
            print("added first DataFrame to master_df")
        else:
            master_df = pd.merge(master_df, df, left_on=f"Date{idx}", right_on=f"Date{idx+1}", how="outer")
            common_functions.patch_req("Report", report_id, body={"loading": f"{ac_name}: Merging with other CSVs...", "is_loading_error": "no"}, dev=dev)
            print("Merged next Dataframe with master_df")

    # master_df.to_csv(f"Master_df.csv", index=False)
    master_df = add_header_pressure_to_master_df(master_df, report_id, dev)

    master_df.to_csv("master_df.csv", index=False)
    if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
        common_functions.patch_req("Report", report_id, body={"loading": f"Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = common_functions.trim_df(report_json, master_df, dev)
        # master_df_pressure = trim_df(report_json, master_df, dev)

    print("Added: master_df")
    
    return master_df

def get_next_order(report_json, dev):
    if "appendix_graph" in report_json["response"]:
        appendix_graphs = report_json["response"]["appendix_graph"]
        next_order = len(appendix_graphs) + 1
    else:
        next_order = 1

    return next_order

def generate_graph(df, report_id, dev, kw_period, acfm_period, pressure_period, day_start, day_end, time_start, time_end, name):
    common_functions.patch_req("Report", report_id, body={"loading": f"Generating Graph: ACFM Monitoring Period...", "is_loading_error": "no"}, dev=dev)

    fig = go.Figure()
    tick_values = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500]

    if acfm_period == "2 minute":
        df['Average ACFM'] = df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)
    elif acfm_period == "15 minute":
        df['Average ACFM'] = df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
    elif acfm_period == "1 hour":
        df['Average ACFM'] = df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=300, min_periods=300).mean()[::-1].fillna(0)
    else:
        df['Average ACFM'] = df.filter(like='ACFM').sum(axis=1)

    if pressure_period == "2 minute":
        df['pressure_period'] = df.filter(like='Pressure').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)
    elif pressure_period == "15 minute":
        df['pressure_period'] = df.filter(like='Pressure').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
    elif pressure_period == "1 hour":
        df['pressure_period'] = df.filter(like='Pressure').sum(axis=1)[::-1].rolling(window=300, min_periods=300).mean()[::-1].fillna(0)
    else:
        df['pressure_period'] = df.filter(like='Pressure').sum(axis=1)
    
    colors = ['#c3ff00', '#88ff00', '#51ff00', '#09ff00', '#00ff51', '#00ffa6', '#00fffb']

    i = 1
    # Loop through each column in the DataFrame
    for col in df.columns:
        # Check if 'Kilowatts' is in the column name
        if 'Kilowatts' in col:
            if kw_period == "2 minute":
                df[f"kW{i}"] = df[col][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)
            elif kw_period == "15 minute":
                df[f"kW{i}"] = df[col][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
            elif kw_period == "1 hour":
                df[f"kW{i}"] = df[col][::-1].rolling(window=300, min_periods=300).mean()[::-1].fillna(0)
            else:
                df[f"kW{i}"] = df[col]
            
            # Main y-axis
            fig.add_trace(go.Scatter(
                x=np.array(df.iloc[:, 1]),
                y=df[f"kW{i}"],
                mode='markers',
                marker=dict(size=20, color=colors[i-1]),
                name=f"kW{i}",
                yaxis='y'  # Associate this trace with the secondary y-axis
            ))

            
            i += 1

    # Secondary y-axis
    fig.add_trace(go.Scatter(
        x=np.array(df.iloc[:, 1]),
        y=df['Average ACFM'],
        mode='markers',  # 'markers' means it's a scatterplot
        marker=dict(size=20, color='#0073ff'),
        name='ACFM',
        yaxis='y2'  # Associate this trace with the primary y-axis
    ))

    # Main y-axis
    fig.add_trace(go.Scatter(
        x=np.array(df.iloc[:, 1]),
        y=df['pressure_period'],
        mode='markers',
        marker=dict(size=20, color='#ff7700'),
        name='Header PSI',
        yaxis='y'  # Associate this trace with the secondary y-axis
    ))

    fig.update_layout(
    xaxis={
        'tickfont': {'size': 48},
        'gridcolor': 'lightgrey',
        'showgrid': True
    },
    yaxis={
        'title': {
            'text': f"PSI, kW",
            'font': {'size': 48}
        },
        'tickfont': {'size': 48},
        'gridcolor': 'lightgrey',
        'showgrid': True
    },
    # Correct the yaxis2 configuration to represent pressure data accurately
    yaxis2=dict(
        title="CFM",
        titlefont={'size': 48},
        tickfont={'size': 48},
        overlaying='y',
        side='right',  # This positions the yaxis2 on the right side
        gridcolor='lightgrey',
        showgrid=True,
        tickmode="sync"
    ),
    legend={'font': {'size': 48}},
    plot_bgcolor='white',
    paper_bgcolor='white'
)

    fig.write_image("temp_image.jpeg", width=3840, height=2160)

    filename = "temp_image.jpeg"
    with open(filename, "rb") as img_file:
        image_data = img_file.read()
    
    encoded_filename = urllib.parse.quote(filename)

    encoded_image_data = base64.b64encode(image_data).decode('utf-8')

    report_json = common_functions.get_req("Report", report_id, dev) # Get the Report Object

    order = get_next_order(report_json, dev)


    payload = {
        "graph_image": {
            "filename": encoded_filename,
            "private": False,
            "contents": encoded_image_data
        },
        "report": report_id,
        "order_sort": order,
        "acfm_period": acfm_period,
        "pressure_period": pressure_period,
        "kw_period": kw_period,
        "day_end": day_end,
        "day_start": day_start,
        "name": name,
        "time_end": time_end,
        "time_start": time_start
    }

    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/appendix_graph"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response)
    print(f"acfm_graph_3_min() {response.status_code, response.text}")

    response_data = response.json()

    # We need to do the following to add a new id to the list of ids in the report object.
    appendix_graph_id = response_data.get('id', None) # Get the id of the Graph we just created
    # print(f"appendix_graph_id: {appendix_graph_id}")
    try:
        existing_ids = report_json["response"]["appendix_graph"] # Extract teh  existing IDs from the report object
    except:
        existing_ids = []
    # print(f"existing_ids: {existing_ids}")

    all_ids = existing_ids + [appendix_graph_id]
    # print(F"all_ids: {all_ids}")

    common_functions.patch_req("report", report_id, body={"appendix_graph": all_ids}, dev=dev) # Update the report with the new id if the graph we just created
    common_functions.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)

def trim_df_to_selection(report_id, df, dev, day_start, day_end, time_start, time_end):
    report_json = common_functions.get_req("report", report_id, dev)

    report_id = report_json["response"]["_id"]

    start_date = datetime.strptime(day_start, "%b %d, %Y %I:%M %p")
    start_time = datetime.strptime(time_start, "%I:%M %p")
    start = start_date.replace(hour=start_time.hour, minute=start_time.minute)

    end_date = datetime.strptime(day_end, "%b %d, %Y %I:%M %p")
    end_time = datetime.strptime(time_end, "%I:%M %p")
    end = end_date.replace(hour=end_time.hour, minute=end_time.minute)

    df = df[(df.iloc[:, 1] >= start) & (df.iloc[:, 1] <= end)]

    return df
    # try:
    # except:
    #     common_functions.patch_req("Report", report_id, body={"loading": f"We're having some trouble with your date selection. Make sure the times are formatted exactly like '9:00 AM'.", "is_loading_error": "yes"}, dev=dev)
    #     sys.exit()

def start():
    data = json.loads(sys.argv[1])

    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data.get('report_id')
    day_start = data.get('day_start')
    day_end = data.get('day_end')
    time_start = data.get('time_start')
    time_end = data.get('time_end')
    kw_period = data.get('kw_period')
    acfm_period = data.get('acfm_period')
    pressure_period = data.get('pressure_period')
    name = data.get('name')

    # Testing the data
    print("** Appendix Graph Data **")
    print(f"report_id: {report_id}")
    print(f"dev: {dev}")
    print(f"day_start: {day_start}")
    print(f"day_end: {day_end}")
    print(f"time_start: {time_start}")
    print(f"time_end: {time_end}")
    print(f"kw_period: {kw_period}")
    print(f"acfm_period: {acfm_period}")
    print(f"pressure_period: {pressure_period}")

    print('compile_df')
    df = compile_df(report_id, dev)

    # This is different from common_functions.trim_df() because the user-inputted dates are formatted differently
    # when taking as a parameter instead of pulling from the database
    print('trim_df_to_selection')
    df = trim_df_to_selection(report_id, df, dev, day_start, day_end, time_start, time_end)

    # Just generat the graph josh. also you worked from like 1am to 3am on this. dont forget to log your hours
    print('generate_graph')
    generate_graph(df, report_id, dev, kw_period, acfm_period, pressure_period, day_start, day_end, time_start, time_end, name)





start()