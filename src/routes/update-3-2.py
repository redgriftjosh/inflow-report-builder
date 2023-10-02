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

data = json.loads(sys.argv[1])

# REPORT ID: 1696102514546x898860189615915000
report_id = data.get('report-id')

def get_req(type, id):
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/{type}/{id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf):
    return min(round(amps * volts * (pf50 if amps < amppf else pf) * sqrt(3) / 1000, 2), bhp * 0.746)

def calculate_olol_acfm(amps, thresholds, cfm):
    return 0 if amps < thresholds else cfm

def calculate_slope_intercept(ac_json, cfm, volts):
    rated_psig = ac_json["response"]["rated-psig"]
    setpoint_psig = ac_json["response"]["setpoint-psig"]
    correction_factor = 1 -((rated_psig - setpoint_psig) * 0.005)
    
    # Get arrays of the slope entries
    slope_entry_ids = ac_json["response"]["vfd-slope-entries"]
    power_input_kws = []
    capacity_acfms = []
    kw_to_amps = []
    corrected_amps = []
    corrected_acfms = []
    for idx, slope_entry_id in enumerate(slope_entry_ids):
        slope_json = get_req("vfd-slope-entries", slope_entry_id)
        
        power_input_kw = slope_json["response"]["power-input-kw"]
        power_input_kws.append(power_input_kw)

        capacity_acfm = slope_json["response"]["capacity-acfm"]
        capacity_acfms.append(capacity_acfm)
    
        kw_to_amp = (1000 * power_input_kw) / (sqrt(3) * 1 * volts)
        kw_to_amps.append(kw_to_amp)

        corrected_amp = kw_to_amp * correction_factor
        corrected_amps.append(corrected_amp)

        if idx == 0:
            corrected_acfm = cfm
        else:
            corrected_acfm = capacity_acfms[0] / cfm * capacity_acfm
        corrected_acfms.append(corrected_acfm)


    slope, intercept = np.polyfit(corrected_amps, corrected_acfms, 1)
    # print(f"Corrected Amps: {corrected_amps}")
    # print(f"Corracted ACFMs: {corrected_acfms}")
    # print(f"SLOPE: {slope}")
    # print(f"Intercept: {intercept}")

    return slope, intercept

def calculate_vfd_acfm(amps, slope, intercept):
    return amps * slope + intercept

def hours_between(start_time, end_time):
    today = datetime.today()
    start_datetime = datetime.combine(today, start_time)
    end_datetime = datetime.combine(today, end_time)

    if end_datetime <= start_datetime:
        end_datetime += timedelta(days=1)
    
    time_difference = end_datetime - start_datetime
    hours_difference = time_difference.total_seconds() / 3600 * 365

    return hours_difference

def update_operating_periods_in_bubble(operating_period_ids, avg_kilowatts, hours_between, avg_acfm, kpi):
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Operation-Period/{operating_period_ids}"
    body = {
        "kW": avg_kilowatts,
        "Hours/yr": hours_between,
        "ACFM Made": avg_acfm,
        "KPI": kpi
    }
    print(body)
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=body, headers=headers)
    print(response.text)

def compressor_capacity(report_id, cfms, max_flow_op, max_avg_15, max_avg_2):
    largest_cfm = max(cfms)
    supply_capacity = sum(cfms)
    redundancy = supply_capacity-max_flow_op-largest_cfm
    redundancy15 = supply_capacity-max_avg_15-largest_cfm
    redundancy2 = supply_capacity-max_avg_2-largest_cfm

    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Report/{report_id}"
    body = {
        "redundancy": redundancy,
        "redundancy-15": redundancy15,
        "redundancy-2": redundancy2,
        "supply-capacity": supply_capacity
    }
    print(body)
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=body, headers=headers)
    print(response.text)

def update_report_in_bubble(report_id, max_avg_15, max_avg_10, max_avg_5, max_avg_3, max_avg_2, low_avg_15, kw_max_avg_15, kpi_3_2):
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Report/{report_id}"
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
    print(body)
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=body, headers=headers)
    print(response.text)

def acfm_graph_3_min(master_df, report_id):
    master_df['3 Minute Average ACFMt'] = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=15, min_periods=15).mean()[::-1].fillna(0)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=master_df.iloc[:, 1],
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

    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Report/{report_id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=payload, headers=headers)
    print(response.text)

def update_pressure_in_bubble(period_id, avg_pressures):
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Operation-Period/{period_id}"
    body = {
        "P2": avg_pressures
    }
    print(body)
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=body, headers=headers)
    print(response.text)

def main(report_id):
    report_json = get_req("Report", report_id)
    ac_ids = report_json["response"]["Air Compressor"]

    # dataframes = []

    # first_dates = []

    master_df = None
    cfms = []
    for idx, ac in enumerate(ac_ids):
        ac_json = get_req("Air-Compressor", ac)
        ac_data_logger_id = ac_json["response"]["AC-Data-Logger"]

        ac_data_logger_json = get_req("AC-Data-Logger", ac_data_logger_id)

        csv_url = ac_data_logger_json["response"]["CSV"]
        csv_url = f"https:{csv_url}"

        response = requests.get(csv_url) # Step 2: Download the CSV file
        response.raise_for_status() # Check that the request was successful
            
        csv_data = StringIO(response.text) # Convert CSV into text of some sort
        df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
        

        volts = ac_json["response"]["volts"]
        pf50 = ac_json["response"]["pf if fifty"]
        pf = ac_json["response"]["pf"]
        amppf = ac_json["response"]["amps less pf"]
        bhp = ac_json["response"]["BHP"]
        
        df[f"Kilowatts{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf))

        control = ac_json["response"]["Control Type"]
        cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        cfms.append(cfm)

        if control == "OLOL":
            threshold = ac_json["response"]["threshold-value"]
            df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_olol_acfm(amps, threshold, cfm))
        elif control == "VFD":
            slope, intercept = calculate_slope_intercept(ac_json, cfm, volts)
            df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_vfd_acfm(amps, slope, intercept))
        
        current_name_date = df.columns[1]
        current_name_num = df.columns[0]
        current_name_amps = df.columns[2]
        df.rename(columns={current_name_date: f"Date{idx+1}", current_name_num: f"Num{idx+1}", current_name_amps: f"Amps{idx+1}"}, inplace=True)

        # first_date = df.iloc[0, 1]

        if master_df is None:
            master_df = df
            print("Master_DF is DF")
        else:
            master_df = pd.merge(master_df, df, left_on=f"Date{idx}", right_on=f"Date{idx+1}", how="outer")
            print("Merged master df with df")
    
    if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
        trim_start = datetime.strptime(report_json["response"]["trim-start"], '%b %d, %Y %I:%M %p')
        trim_end = datetime.strptime(report_json["response"]["trim-end"], '%b %d, %Y %I:%M %p')
        master_df = master_df[(master_df.iloc[:, 1] >= trim_start) & (master_df.iloc[:, 1] <= trim_end)]
        print("Trimmed up the")

    operating_period_ids = report_json["response"]["Operation Period"]
    start_times = []
    end_times = []
    operating_periods = []

    for operating_period_id in operating_period_ids:
        operating_period_json = get_req("Operation-Period", operating_period_id)
        start_time = datetime.strptime(operating_period_json["response"]["Start Time"], '%I:%M %p').time()
        start_times.append(start_time)

        end_time = datetime.strptime(operating_period_json["response"]["End Time"], '%I:%M %p').time()
        end_times.append(end_time)

        operating_period = operating_period_json["response"]["Name"]
        operating_periods.append(operating_period)


    avg_acfms = []
    for start_time, end_time, period_name, period_id in zip(start_times, end_times, operating_periods, operating_period_ids):
        if start_time < end_time:
            period_data = master_df[(master_df.iloc[:, 1].dt.time >= start_time) & (master_df.iloc[:, 1].dt.time < end_time)]
        else:  # Case for overnight period
            period_data = master_df[(master_df.iloc[:, 1].dt.time >= start_time) | (master_df.iloc[:, 1].dt.time < end_time)]

        avg_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
        avg_acfms.append(avg_acfm)
        avg_kilowatts = period_data.filter(like='Kilowatts').sum(axis=1).mean()
        kpi = avg_kilowatts/avg_acfm
        hours_diff = hours_between(start_time, end_time)
        update_operating_periods_in_bubble(period_id, avg_kilowatts, hours_diff, avg_acfm, kpi)
    max_flow_op = max(avg_acfms)

    # Get's peak 15, 10, 5, 3, and 2 min values just guessing on the 15 min low function because it seems like it will be 0 most of the time..

    # var name = the dataframe.get columns that include the name ACFM, add together on on axis for a "total" row then revers it's direction because the rolling function works from the bottom up, declare the window size, don't let it average less than the window size, flip back to normal direction fill all NaNs with 0's then get the max of the values.
    max_avg_15 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
    max_avg_10 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=50, min_periods=50).mean()[::-1].fillna(0).max()
    max_avg_5 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=25, min_periods=25).mean()[::-1].fillna(0).max()
    max_avg_3 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=15, min_periods=15).mean()[::-1].fillna(0).max()
    max_avg_2 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
    low_avg_15 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).min()

    compressor_capacity(report_id, cfms, max_flow_op, max_avg_15, max_avg_2)
    # master_df.to_csv('Master_df.csv', sep=',', header=True, encoding='utf-8', index=False)
    # print("Making master_df.csv...")

    kw_max_avg_15 = master_df.filter(like='Kilowatts').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()

    kpi_3_2 = kw_max_avg_15/max_avg_15

    update_report_in_bubble(report_id, max_avg_15, max_avg_10, max_avg_5, max_avg_3, max_avg_2, low_avg_15, kw_max_avg_15, kpi_3_2)

    acfm_graph_3_min(master_df, report_id)

    # Updating the Pressure sensor part of the chart
    if "pressure-sensor" in report_json["response"]:
        pressure_ids = report_json["response"]["pressure-sensor"]
        pressure_csvs = []
        for pressure_id in pressure_ids:
            pressure_json = get_req("pressure-sensor", pressure_id)
            if "csv-psig" in pressure_json["response"]:
                pressure_csv = pressure_json["response"]["csv-psig"]
                pressure_csv = f"https:{pressure_csv}"
                pressure_csvs.append(pressure_csv)
        
        for start_time, end_time, period_name, period_id in zip(start_times, end_times, operating_periods, operating_period_ids):
            avg_pressures = []

            for pressure_csv, pressure_id in zip(pressure_csvs, pressure_ids):
                response = requests.get(pressure_csv) # Step 2: Download the CSV file
                response.raise_for_status() # Check that the request was successful
                
                csv_data = StringIO(response.text) # Convert CSV into text of some sort
                
                df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
                
                if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
                    df = df[(df.iloc[:, 1] >= trim_start) & (df.iloc[:, 1] <= trim_end)] # trim the df to be all synced up with other pressure csvs
                
                if start_time < end_time:
                    period_data = df[(df.iloc[:, 1].dt.time >= start_time) & (df.iloc[:, 1].dt.time < end_time)]

                else:  # Case for overnight period
                    period_data = df[(df.iloc[:, 1].dt.time >= start_time) | (df.iloc[:, 1].dt.time < end_time)]

                avg_pressure = period_data.iloc[:, 2].mean()
                avg_pressures.append(avg_pressure)

            update_pressure_in_bubble(period_id, avg_pressures)



main(report_id)



