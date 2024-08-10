from datetime import datetime
import gzip
from io import StringIO
import io
import sys
import pandas as pd
import requests
from routes import common_functions
from utilities import requests_util, compressor_util

# Fetches the CSV data from the given URL and returns a pandas DataFrame
def data_crunch_csv_to_df(csv_url):
    response = requests.get(csv_url) # Step 2: Download the CSV file
    response.raise_for_status() # Check that the request was successful
    
    compressed_data = io.BytesIO(response.content)
    with gzip.open(compressed_data, 'rt') as f:
        csv_data = f.read()
    
    # print(f"csv_data[:1000]: {csv_data[:1000]}")
    # csv_data = StringIO(response.text) # Convert CSV into text of some sort

    # Use io.StringIO to convert the CSV string into a file-like object
    csv_data = StringIO(csv_data)
    
    df = pd.read_csv(csv_data, parse_dates=[1], date_format='%Y-%m-%d %H:%M:%S') # Step 3: Read the CSV data into a pandas DataFrame and format the date column

    return df

# Fetches the CSV from the given Operation Period and returns a pandas DataFrame
def get_op_data_crunch(op_id, dev):

    op_json = requests_util.get_req("operation_period", op_id, dev)
    try:
        op_name = op_json["response"]["Name"]
    except:
        print(f"Looking for an Operation Periods name... Did you name all your Operation Periods?", file=sys.stderr)
        sys.exit(1)
    
    try:
        csv_url = op_json["response"]["data_crunch"]
        csv_url = f"https:{csv_url}"
    except:
        print(f"Missing data cruncher! Make sure each Operating Period has a Properly Formatted CSV uploaded. Operating Period: {op_name}", file=sys.stderr)
        sys.exit(1)

    try:
        return data_crunch_csv_to_df(csv_url)
    except:
        print(f"Unable to read DataCrunch CSV. Operating Period: {op_name}", file=sys.stderr)
        sys.exit(1)

# Fetches the CSV from the given Report and returns a pandas DataFrame
def get_report_data_crunch(report_id, field, dev):

    report_json = requests_util.get_req("report", report_id, dev)
    
    try:
        csv_url = report_json["response"][field]
        csv_url = f"https:{csv_url}"
    except:
        print(f"Missing data cruncher! Make sure your Report has trimmed_excluded_data_crunch.csv", file=sys.stderr)
        sys.exit(1)

    try:
        return data_crunch_csv_to_df(csv_url)
    except:
        print(f"Unable to read trimmed_excluded_data_crunch.csv", file=sys.stderr)
        sys.exit(1)

# Adds the Pressure CSVs to the Master Data Crunch DataFrame
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

# Fetching the Datalogger CSVs and returns an unfiltered DataFrame
def generate_raw_data_crunch(dev, report_id):
    report_json = requests_util.get_req("report", report_id, dev)
    if "air_compressor" in report_json["response"] and report_json["response"]["air_compressor"] != []:
        ac_ids = report_json["response"]["air_compressor"]
    else:
        print(f"Unable to find any Air Compressors! You need at least one Air Compressor to generate Data Crunch.", file=sys.stderr)
        sys.exit(1)
    my_dict = {}

    master_df = None
    cfms = []
    for idx, ac in enumerate(ac_ids):
        ac_json = requests_util.get_req("air_compressor", ac, dev)
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            print(f"Missing Name! Air Compressor ID: {ac}", file=sys.stderr)
            sys.exit(1)
        
        requests_util.patch_req("Report", report_id, body={"loading": f"Getting started on {ac_name}...", "is_loading_error": "no"}, dev=dev)

        if "ac_data_logger" in ac_json["response"] and ac_json["response"]["ac_data_logger"] != []:
            ac_data_logger_id = ac_json["response"]["ac_data_logger"]
            ac_data_logger_json = requests_util.get_req("ac_data_logger", ac_data_logger_id, dev)
        else:
            print(f"Missing Data Logger! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)

        if "CSV" in ac_data_logger_json["response"]:
            csv_url = ac_data_logger_json["response"]["CSV"]
            csv_url = f"https:{csv_url}"
        else:
            print(f"Missing Data Logger! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)

        requests_util.patch_req("Report", report_id, body={"loading": f"{ac_name}: Reading CSV...", "is_loading_error": "no"}, dev=dev)
        df = common_functions.csv_to_df(csv_url)
        # response = requests.get(csv_url) # Step 2: Download the CSV file
        # response.raise_for_status() # Check that the request was successful
            
        # csv_data = StringIO(response.text) # Convert CSV into text of some sort
        # df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
        requests_util.patch_req("Report", report_id, body={"loading": f"{ac_name}: Kilowatts{idx+1} Column...", "is_loading_error": "no"}, dev=dev)
        if "volts" in ac_json["response"]:
            volts = ac_json["response"]["volts"]
        else:
            print(f"Missing Volts! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)
        
        if "pf if fifty" in ac_json["response"]:
            pf50 = ac_json["response"]["pf if fifty"]
        else:
            print(f"Missing Power Factor When Less Than 50% Load! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)
        
        if "pf" in ac_json["response"]:
            pf = ac_json["response"]["pf"]
        else:
            print(f"Missing Power Factor! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)
        
        if "amps less pf" in ac_json["response"]:
            amppf = ac_json["response"]["amps less pf"]
        else:
            print(f"Missing Amps Less Than For Power Factor! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)
        
        if "BHP" in ac_json["response"]:
            bhp = ac_json["response"]["BHP"]
        else:
            print(f"Missing BHP! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)
        
        df[f"Kilowatts{idx+1}"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf))
        df[f'15_Min_Avg_kW_AC{idx+1}'] = df[f'Kilowatts{idx+1}'][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
        df[f'2_Min_Avg_kW_AC{idx+1}'] = df[f'Kilowatts{idx+1}'][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)

        requests_util.patch_req("Report", report_id, body={"loading": f"{ac_name}: ACFM Column...", "is_loading_error": "no"}, dev=dev)
        # Create ACFM Column

        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            print(f"Missing Control Type! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)
        cfm = compressor_util.get_cfm(control, ac_json, ac_name, dev)
        cfms.append(cfm)

        df = common_functions.calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id)
        df[f'15_Min_Avg_Flow_AC{idx+1}'] = df[f'ACFM{idx+1}'][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
        df[f'2_Min_Avg_Flow_AC{idx+1}'] = df[f'ACFM{idx+1}'][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)
        
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
            requests_util.patch_req("Report", report_id, body={"loading": f"{ac_name}: Merging with other CSVs...", "is_loading_error": "no"}, dev=dev)
            print("Merged next Dataframe with master_df")
    
    master_df.info()

    # Get the total number of rows
    total_rows = master_df.shape[0]
    # print("Total number of rows:", total_rows)

    master_df['Total_Flow'] = master_df.filter(like='ACFM').sum(axis=1) # Not using ACFM because I'm scared some other script will use filter(like='ACFM') on this df again and get the wrong data

    master_df['15_Min_Avg_Flow'] = master_df['Total_Flow'][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
    master_df['10_Min_Avg_Flow'] = master_df['Total_Flow'][::-1].rolling(window=50, min_periods=50).mean()[::-1].fillna(0)
    master_df['5_Min_Avg_Flow'] = master_df['Total_Flow'][::-1].rolling(window=25, min_periods=25).mean()[::-1].fillna(0)
    master_df['3_Min_Avg_Flow'] = master_df['Total_Flow'][::-1].rolling(window=15, min_periods=15).mean()[::-1].fillna(0)
    master_df['2_Min_Avg_Flow'] = master_df['Total_Flow'][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)

    master_df['Total_kW'] = master_df.filter(like='Kilowatts').sum(axis=1)

    master_df['15_Min_Avg_kW'] = master_df['Total_kW'][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0)
    master_df['10_Min_Avg_kW'] = master_df['Total_kW'][::-1].rolling(window=50, min_periods=50).mean()[::-1].fillna(0)
    master_df['5_Min_Avg_kW'] = master_df['Total_kW'][::-1].rolling(window=25, min_periods=25).mean()[::-1].fillna(0)
    master_df['3_Min_Avg_kW'] = master_df['Total_kW'][::-1].rolling(window=15, min_periods=15).mean()[::-1].fillna(0)
    master_df['2_Min_Avg_kW'] = master_df['Total_kW'][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0)

    master_df = add_pressure_to_master_df(master_df, report_id, dev)

    return master_df

def trim_df(report_id, df, dev):
    report_json = requests_util.get_req("report", report_id, dev)
    if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
        requests_util.patch_req("Report", report_id, body={"loading": f"Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        try:
            trim_id = report_json["response"]["trim"]
            report_id = report_json["response"]["_id"]
            trim_json = requests_util.get_req("trim", trim_id, dev)

            start_date = datetime.strptime(trim_json["response"]["start_date"], "%Y-%m-%dT%H:%M:%S.%fZ")
            start_time = datetime.strptime(trim_json["response"]["start_time"], "%I:%M %p")
            start = start_date.replace(hour=start_time.hour, minute=start_time.minute)

            end_date = datetime.strptime(trim_json["response"]["end_date"], "%Y-%m-%dT%H:%M:%S.%fZ")
            end_time = datetime.strptime(trim_json["response"]["end_time"], "%I:%M %p")
            end = end_date.replace(hour=end_time.hour, minute=end_time.minute)

            df = df[(df.iloc[:, 1] >= start) & (df.iloc[:, 1] <= end)]

            return df
        except:
            print(f"We're having some trouble Trimming your dataset. Make sure the times are formatted exactly like '9:00 AM'.", file=sys.stderr)
            sys.exit(1)
    else:
        return df

def exclude_from_df(report_id, df, dev):
    report_json = requests_util.get_req("report", report_id, dev)
    if "exclusion" in report_json["response"]:
        requests_util.patch_req("Report", report_id, body={"loading": f"Removing Exclusions from the dataset...", "is_loading_error": "no"}, dev=dev)
        try:
            exclusion_ids = report_json["response"]["exclusion"]
            report_id = report_json["response"]["_id"]

            # Initialize a mask with all False (i.e., don't exclude any row initially)
            exclusion_mask = pd.Series([False] * len(df), index=df.index)

            # Add each exclusion to the mask
            for exclusion_id in exclusion_ids:
                exclusion_json = requests_util.get_req("exclusion", exclusion_id, dev)
                start_date = datetime.strptime(exclusion_json["response"]["start_date"], "%Y-%m-%dT%H:%M:%S.%fZ")
                start_time = datetime.strptime(exclusion_json["response"]["start_time"], "%I:%M %p")
                start = start_date.replace(hour=start_time.hour, minute=start_time.minute)

                end_date = datetime.strptime(exclusion_json["response"]["end_date"], "%Y-%m-%dT%H:%M:%S.%fZ")
                end_time = datetime.strptime(exclusion_json["response"]["end_time"], "%I:%M %p")
                end = end_date.replace(hour=end_time.hour, minute=end_time.minute)

                exclusion_mask |= (df.iloc[:, 1] >= start) & (df.iloc[:, 1] <= end)
            
            # Use the inverse of the mask to filter the dataframe
            return df[~exclusion_mask]
        except:
            print(f"We're having some trouble removing Exclusions from your dataset. Make sure the times are formatted exactly like '9:00 AM'.", file=sys.stderr)
            sys.exit(1)
    else:
        return df

def filter_df_to_each_operating_period(df, op_id, dev):
    op_json = requests_util.get_req("operation_period", op_id, dev) # Get's a json object of all the time_range IDs
    time_ranges = op_json["response"]["time_range"] # List if time_range IDs

    filtered_dfs = []
    
    for time_range in time_ranges:
        time_json = requests_util.get_req("time_range", time_range, dev) # For each time range get the json for each range
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days = time_json["response"]["repeat_on_weekly"]


        if time_json["response"]["all_day"] == True:
            for day in days:
                mask = (df.iloc[:, 1].dt.day_name() == day)
                filtered_dfs.append(df[mask])
        else:

            start_time = datetime.strptime(time_json["response"]["start_time"], '%I:%M %p').time()
            end_time = datetime.strptime(time_json["response"]["end_time"], '%I:%M %p').time()

            if start_time > end_time:
                for day in days:
                    day_idx = days_of_week.index(day)
                    end_day = days_of_week[day_idx+1] if day_idx < 6 else days_of_week[0]
                    mask = (((df.iloc[:, 1].dt.day_name() == day) & (df.iloc[:, 1].dt.time >= start_time)) | ((df.iloc[:, 1].dt.time < end_time) & (df.iloc[:, 1].dt.day_name() == end_day)))
                    filtered_dfs.append(df[mask])
            else:
                # Normal range within the same day
                for day in days:
                    mask = ((df.iloc[:, 1].dt.day_name() == day) & (df.iloc[:, 1].dt.time >= start_time) & (df.iloc[:, 1].dt.time < end_time))
                    filtered_dfs.append(df[mask])

    final_df = pd.concat(filtered_dfs)
    final_df = final_df.sort_values(by=df.columns[1]).reset_index(drop=True)

    final_df.to_csv('Experimental Operating Period Filter.csv', index=False)

    return final_df

# Takes the Index of the Air Compressors and returns a DataFrame with only those columns
def filter_df_to_ac_idx(df, ac_idxs):

    # Construct the column names
    col_names = [f"ACFM{i}" for i in ac_idxs]

    col_names += [col for col in df.columns if col.startswith('Date')]
    filtered_df = df[col_names]
    filtered_df.info()
    # print(f"filter_df_to_ac_idx: {filtered_df.head(10)}")
    return df[col_names]


def csv_to_df(csv_data, report_id, dev):
    try:
        df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p')
    except Exception as e:
        print(f"Cannot read CSV. Please follow the formatting Guide.", file=sys.stderr)
        sys.exit(1)
    requests_util.patch_req("Report", report_id, body={"loading": f"CSV Readable ✅", "is_loading_error": "no"}, dev=dev)
    df.info()

    print(df.head(20))
    try:
        pd.to_datetime(df.iloc[:, 1], format='%m/%d/%y %I:%M:%S %p')
        requests_util.patch_req("Report", report_id, body={"loading": f"CSV Readable ✅, Date Format ✅, Checking for Consistend Dates...", "is_loading_error": "no"}, dev=dev)
    except ValueError:
        print("Column 'B' is not properly formatted as a date.", file=sys.stderr)
        sys.exit(1)

    # Calculate the time difference between each date
    df['Time_Difference'] = df.iloc[:, 1].diff()

    df.info()

    print(df.head(20))

    # Loop through the DataFrame to find discrepancies
    for i in range(1, len(df)):  # Start from 1 because the first row's diff is NaT
        if df.iloc[i]['Time_Difference'] != pd.Timedelta(seconds=12):
            if i == 1:
                print(f"It looks like the date column is not seeing the seconds. Double check the date format matches 'mm/dd/yy hh:mm:ss AM/PM': {i}", file=sys.stderr)
            print(f"It looks like not all dates are 12 seconds apart! I found this at row {i}", file=sys.stderr)
            sys.exit(1)
    requests_util.patch_req("Report", report_id, body={"loading": f"CSV Readable ✅, Date Format ✅, Consistend Dates ✅", "is_loading_error": "no"}, dev=dev)

    return df

def download_csv(csv_url):
    try:
        return requests.get(f"https:{csv_url}")
    except:
        print(f"No File Uploaded", file=sys.stderr)
        sys.exit(1)
    