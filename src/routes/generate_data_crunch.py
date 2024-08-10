import base64
import gzip
import json
import sys
import pandas as pd
import urllib.parse
import requests
import common_functions
from utilities import requests_util, data_crunch_util

def upload_op_data_crunch(master_df, report_id, op_id, dev):
    print(f"upload_op_data_crunch")
    print(master_df.head())
    # Convert the DataFrame to a CSV file

    op_json = requests_util.get_req("operation_period", op_id, dev)
    try:
        op_name = op_json["response"]["Name"]
    except:
        print(f"Looking for an Operation Periods name... Did you name all your Operation Periods?", file=sys.stderr)
        sys.exit(1)
    
    requests_util.patch_req("Report", report_id, body={"loading": f"Converting and uploading {op_name}_data_crunch.csv", "is_loading_error": "no"}, dev=dev)
    csv_data = master_df.to_csv(index=False)
    num_characters = len(csv_data)

    # Print the number of characters
    print(f"Number of characters in upload_op_data_crunch: {num_characters}")

    compressed_csv_data = gzip.compress(csv_data.encode())
    encoded_csv_data = base64.b64encode(compressed_csv_data).decode('utf-8')

    # Encode the CSV data
    # encoded_csv_data = base64.b64encode(csv_data.encode()).decode('utf-8')

    # Send to bubble
    requests_util.patch_file_req("data_crunch", encoded_csv_data, f"{op_name}_data_crunch.csv", "operation_period", op_id, dev)

    requests_util.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)

def upload_raw_data_crunch(master_df, report_id, dev):
    # Fill NaN values with a default value (e.g., 0)
    # master_df = master_df.fillna(0)

    # master_df = master_df.head(90000)
    
    print(f"upload_raw_data_crunch")
    print(master_df.head())

    # Convert the DataFrame to a CSV file
    requests_util.patch_req("Report", report_id, body={"loading": f"Converting and Uploading raw_data_crunch.csv...", "is_loading_error": "no"}, dev=dev)
    csv_data = master_df.to_csv(index=False)
    num_characters = len(csv_data)
    # Compress the CSV data
    compressed_csv_data = gzip.compress(csv_data.encode())
    encoded_csv_data = base64.b64encode(compressed_csv_data).decode('utf-8')

    # Print the number of characters
    print(f"Number of characters in upload_raw_data_crunch: {num_characters}")
    print(f"Compressed data size: {len(compressed_csv_data)}")

    # Encode the CSV data
    # encoded_csv_data = base64.b64encode(csv_data.encode()).decode('utf-8')
    print(f"upload_raw_data_crunch1")
    # Send to bubble
    requests_util.patch_file_req("data_crunch_raw", encoded_csv_data, f"raw_data_crunch.csv", "Report", report_id, dev)
    # sys.exit(0)

def upload_trimmed_data_crunch(master_df, report_id, dev):
    print(f"upload_trimmed_data_crunch")
    print(master_df.head())
    # Convert the DataFrame to a CSV file
    requests_util.patch_req("Report", report_id, body={"loading": f"Converting and Uploading trimmed_data_crunch.csv...", "is_loading_error": "no"}, dev=dev)
    csv_data = master_df.to_csv(index=False)

    compressed_csv_data = gzip.compress(csv_data.encode())
    encoded_csv_data = base64.b64encode(compressed_csv_data).decode('utf-8')


    # Encode the CSV data
    # encoded_csv_data = base64.b64encode(csv_data.encode()).decode('utf-8')

    # Send to bubble
    requests_util.patch_file_req("data_crunch_trimmed", encoded_csv_data, f"trimmed_data_crunch.csv", "report", report_id, dev)

def upload_exluded_data_crunch(master_df, report_id, dev):
    print(f"upload_exluded_data_crunch")
    print(master_df.head())
    # Convert the DataFrame to a CSV file
    requests_util.patch_req("Report", report_id, body={"loading": f"Converting and Uploading trimmed_excluded_data_crunch.csv...", "is_loading_error": "no"}, dev=dev)
    csv_data = master_df.to_csv(index=False)

    compressed_csv_data = gzip.compress(csv_data.encode())
    encoded_csv_data = base64.b64encode(compressed_csv_data).decode('utf-8')


    # Encode the CSV data
    # encoded_csv_data = base64.b64encode(csv_data.encode()).decode('utf-8')

    # Send to bubble
    requests_util.patch_file_req("data_crunch_trim_exclu", encoded_csv_data, f"trimmed_excluded_data_crunch.csv", "report", report_id, dev)

def add_pressure_to_master_df(master_df, report_id, dev):
    report_json = requests_util.get_req("report", report_id, dev)

    master_df_pressure = None

    low_pressures_15 = []

    if "pressure_sensor" in report_json["response"]:
        pressure_sensors = report_json["response"]["pressure_sensor"]
        pressure_csvs = common_functions.get_pressure_csvs(report_id, pressure_sensors, dev)

        for idx, (id, pressure_csv) in enumerate(pressure_csvs.items()):
            df = common_functions.csv_to_df(pressure_csv)

            current_name_date = df.columns[1]
            current_name_num = df.columns[0]
            current_name_pressure = df.columns[2]
            df.rename(columns={current_name_date: f"Date{idx+100}", current_name_num: f"Num{idx+100}", current_name_pressure: f"Pressure{id}"}, inplace=True)
            
            if master_df_pressure is None:
                master_df_pressure = pd.merge(master_df, df, left_on=f"Date1", right_on=f"Date{idx+100}", how="outer")

            else:
                master_df_pressure = pd.merge(master_df_pressure, df, left_on=f"Date1", right_on=f"Date{idx+100}", how="outer")

        return master_df_pressure
    else:
        return None

def generate_data_crunch(dev, report_id):
    df = data_crunch_util.generate_raw_data_crunch(dev, report_id)
    df.to_csv("raw_data_crunch.csv")
    upload_raw_data_crunch(df, report_id, dev)

    df = data_crunch_util.trim_df(report_id, df, dev)
    df.to_csv("trim_df.csv")
    upload_trimmed_data_crunch(df, report_id, dev)

    df = data_crunch_util.exclude_from_df(report_id, df, dev)
    df.to_csv("trim_df.csv")
    upload_exluded_data_crunch(df, report_id, dev)

    report_json = requests_util.get_req("report", report_id, dev)

    if "operation_period" in report_json["response"] and report_json["response"]["operation_period"] != []:
        op_per_type = report_json["response"]["operating_period_type"]
        
        operating_period_ids = report_json["response"]["operation_period"]
        requests_util.patch_req("Report", report_id, body={"loading": f"Found {len(operating_period_ids)} Operating Period{'s' if len(operating_period_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        print(f"No Operating Periods found! You need at least on operation period...", file=sys.stderr)
        sys.exit(1)
    

    if op_per_type == "Experimental":
        for operating_period_id in operating_period_ids:
            op_json = requests_util.get_req("operation_period", operating_period_id, dev)
            op_name = op_json["response"]["Name"]

            period_data = data_crunch_util.filter_df_to_each_operating_period(df, operating_period_id, dev)
            period_data.to_csv(f"{op_name}_data_crunch.csv")

            upload_op_data_crunch(period_data, report_id, operating_period_id, dev)
            
    else:
        print(f"You're using an outdated operating period type. Please convert to the latest operation period type", file=sys.stderr)
        sys.exit(1)

def get_payload():
    data = json.loads(sys.argv[1])
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''
    report_id = data.get('report-id')

    return dev, report_id

def start():
    dev, report_id = get_payload()
    generate_data_crunch(dev, report_id)

start()