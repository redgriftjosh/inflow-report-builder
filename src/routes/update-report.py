import sys
import json
import requests #to download csv from a link
from io import StringIO #We are using the StringIO class from the io module to read the CSV data from a string
import pandas as pd #For calcuations on dataframes.
from math import sqrt
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.io as pio
import base64
import urllib.parse

data = json.loads(sys.argv[1])

print(data)

# Required Values
csv_urls = data.get('amps_csvs') # Step 1: Get the CSV file URLs from the POST request data
start_times = [datetime.strptime(time, '%I:%M %p').time() for time in data['start_times']]
end_times = [datetime.strptime(time, '%I:%M %p').time() for time in data['end_times']]
operating_periods = data['operating_period_names']
operating_period_ids = data['operating_period_ids']
thresholds = data['thresholds']
volts = data['volts']
amppfs = data['amppfs']
pf50s = data['pf50s']
pfs = data['pfs']
bhps = data['bhps']
cfms = data['cfms']
trim_start = datetime.strptime(data.get('trim_start'), '%b %d, %Y %I:%M %p')
trim_end = datetime.strptime(data.get('trim_end'), '%b %d, %Y %I:%M %p')
report_id = data.get('report-id')


print(f"trim_start: {trim_start} and trim_end: {trim_end}")


dataframes = []

def calculate_kilowatts(amps, idx):
    return min(round(amps * volts[idx] * (pf50s[idx] if amps < amppfs[idx] else pfs[idx]) * sqrt(3) / 1000, 2), bhps[idx] * 0.746)

def calculate_acfm(amps, thresholds, idx):
    return 0 if amps < thresholds[idx] else cfms[idx]

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

def update_updating(report_id):
    
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Report/{report_id}"
    body = {
        "updating": False
    }
    print(body)
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.patch(url, json=body, headers=headers)
    print(response.text)

for idx, csv_url in enumerate(csv_urls):
    response = requests.get(csv_url) # Step 2: Download the CSV file
    response.raise_for_status() # Check that the request was successful
        
    csv_data = StringIO(response.text) # Convert CSV into text of some sort
    df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
    df = df[(df.iloc[:, 1] >= trim_start) & (df.iloc[:, 1] <= trim_end)]
    
    df[f"Kilowatts{idx}"] = df.iloc[:, 2].apply(lambda amps: calculate_kilowatts(amps, idx))

    df[f"ACFM{idx}"] = df.iloc[:, 2].apply(lambda amps: calculate_acfm(amps, thresholds, idx))

    # TESTING PURPOSES
    # df.to_csv(f"kW-and-acfm-AC{idx+1}.csv", sep=',', header=True, encoding='utf-8', index=False)

    dataframes.append(df)

master_df = pd.concat(dataframes, axis=1) # smoosh the dfs together axis=1 means side by side (adding columns) not stacked which is default or axis=0


# TESTING PURPOSES
# master_df.to_csv('Master_df.csv', sep=',', header=True, encoding='utf-8', index=False)

print('master_df.info')
master_df.info()

print('print(master_df.head(10))')
print(master_df.head(10))
avg_acfms = []
for start_time, end_time, period_name, period_id in zip(start_times, end_times, operating_periods, operating_period_ids):
    if start_time < end_time:
        period_data = master_df[(master_df.iloc[:, 1].dt.time >= start_time) & (master_df.iloc[:, 1].dt.time < end_time)]
    else:  # Case for overnight period
        period_data = master_df[(master_df.iloc[:, 1].dt.time >= start_time) | (master_df.iloc[:, 1].dt.time < end_time)]
    
    # print(f"Info on: {period_name}")
    # period_data.info()

    # TESTING PURPOSES
    # period_data.to_csv(f"master_df for {period_name}.csv", sep=',', header=True, encoding='utf-8', index=False)

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

kw_max_avg_15 = master_df.filter(like='Kilowatts').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()

kpi_3_2 = kw_max_avg_15/max_avg_15

update_report_in_bubble(report_id, max_avg_15, max_avg_10, max_avg_5, max_avg_3, max_avg_2, low_avg_15, kw_max_avg_15, kpi_3_2)

acfm_graph_3_min(master_df, report_id)


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

#If there's at least one pressure log
if (data['pressure_csvs'][0] != 'https:' and data['pressure_ids'][0] != ''):
    pressure_csvs = data['pressure_csvs']
    pressure_ids = data['pressure_ids']

    for start_time, end_time, period_name, period_id in zip(start_times, end_times, operating_periods, operating_period_ids):
        

        avg_pressures = []

        for pressure_csv, pressure_id in zip(pressure_csvs, pressure_ids):
            response = requests.get(pressure_csv) # Step 2: Download the CSV file
            response.raise_for_status() # Check that the request was successful
            csv_data = StringIO(response.text) # Convert CSV into text of some sort
            df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
            df = df[(df.iloc[:, 1] >= trim_start) & (df.iloc[:, 1] <= trim_end)] # trim the df to be all synced up with other pressure csvs

            if start_time < end_time:
                period_data = df[(df.iloc[:, 1].dt.time >= start_time) & (df.iloc[:, 1].dt.time < end_time)]

            else:  # Case for overnight period
                period_data = df[(df.iloc[:, 1].dt.time >= start_time) | (df.iloc[:, 1].dt.time < end_time)]

            avg_pressure = period_data.iloc[:, 2].mean()
            avg_pressures.append(avg_pressure)

        update_pressure_in_bubble(period_id, avg_pressures)


else:
    print('pressure_csvs and pressure_ids are not both populated I guess..')


update_updating(report_id)
