import sys
import json
import requests
from io import StringIO
import pandas as pd
from datetime import time, datetime, timedelta
from math import sqrt
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import base64
import urllib.parse

def get_req(type, id):
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/{type}/{id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def patch_req(type, id, body):
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/{type}/{id}"
    
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    try:
        response = requests.patch(url, json=body, headers=headers)
        print(f"patch_req() {response.status_code, response.text}")
    except requests.RequestException as e:
        print(e)

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

# gets start & end time for each day of the week returned in a dictionary.
def weekly_dictionary(operating_period_id):
    operating_period_json = get_req("Operation-Period", operating_period_id)

    days = ["sun", "mon", "tues", "wed", "thurs", "fri", "sat"] # for easily getting the data from bubble -- works with the naming convention
    large_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] # for 
    
    operating_period = {}

    for day, large_days in zip(days, large_days):
        start_key = f"{day}-start"
        end_key = f"{day}-end"
        
        start_time = datetime.strptime(operating_period_json["response"].get(start_key), '%I:%M %p').time() if operating_period_json["response"].get(start_key) else None
        end_time = datetime.strptime(operating_period_json["response"].get(end_key), '%I:%M %p').time() if operating_period_json["response"].get(end_key) else None

        operating_period[large_days] = {"start": start_time, "end": end_time}
    
    return operating_period

# return the number of hours within the operating periods per year.
# function is special for the daily operating periods.
def hours_between(operating_period_id):
    operating_period_json = get_req("Operation-Period", operating_period_id)
    start_time = datetime.strptime(operating_period_json["response"]["Start Time"], '%I:%M %p').time()
    end_time = datetime.strptime(operating_period_json["response"]["End Time"], '%I:%M %p').time()
    today = datetime.today()
    start_datetime = datetime.combine(today, start_time)
    end_datetime = datetime.combine(today, end_time)

    if end_datetime <= start_datetime:
        end_datetime += timedelta(days=1)
    
    time_difference = end_datetime - start_datetime
    hours_difference = time_difference.total_seconds() / 3600 * 365

    return hours_difference

# takes one operation period id and then returns a filtered dataFrame within the user-defined days & times
# to select a whole day, select 12am to 12am.
# to select a start time to the end of the day, select start time normally and 12am end time.
def weekly_operating_period(df, operating_period_id):
    operating_period = weekly_dictionary(operating_period_id) # gets start & end time for each day of the week and stores in a dictionary.

    filtered_dfs = []
    for day, times in operating_period.items():
        start_time = times['start']
        end_time = times['end']
        
        if start_time and end_time:  # Check if both start and end times are available
            if start_time < end_time:
                mask = (
                    (df.iloc[:, 1].dt.day_name() == day) &
                    (df.iloc[:, 1].dt.time >= start_time) &
                    (df.iloc[:, 1].dt.time < end_time)
                )
                filtered_dfs.append(df[mask])
            elif start_time == time(0, 0) and end_time == time(0, 0):
                mask = (
                    (df.iloc[:, 1].dt.day_name() == day)
                )
                filtered_dfs.append(df[mask])
            elif start_time > end_time and end_time == time(0, 0):
                mask = (
                    (df.iloc[:, 1].dt.day_name() == day) &
                    (df.iloc[:, 1].dt.time >= start_time)
                )
                filtered_dfs.append(df[mask])
                

    final_df = pd.concat(filtered_dfs)
    final_df = final_df.sort_values(by=df.columns[1]).reset_index(drop=True)

    return final_df

# takes a dataframe and an operating period ID and returns a filtered dataframe.
# Designed for daily operating period not weekly.
def daily_operating_period(df, operating_period_id):
    operating_period_json = get_req("Operation-Period", operating_period_id)
    start_time = datetime.strptime(operating_period_json["response"]["Start Time"], '%I:%M %p').time()
    end_time = datetime.strptime(operating_period_json["response"]["End Time"], '%I:%M %p').time()
    operating_period = operating_period_json["response"]["Name"]

    if start_time < end_time:
        period_data = df[(df.iloc[:, 1].dt.time >= start_time) & (df.iloc[:, 1].dt.time < end_time)]
    else:  # Case for overnight period
        period_data = df[(df.iloc[:, 1].dt.time >= start_time) | (df.iloc[:, 1].dt.time < end_time)]
    
    return period_data



# return the number of hours within the operating periods per year.
# function is special for the weekly operating periods.
def hours_between_weekly(operating_period_id):
    operating_period = weekly_dictionary(operating_period_id) # gets start & end time for each day of the week and stores in a dictionary.

    today = datetime.today()
    
    total_hours = []
    for day, times in operating_period.items():
        start_time = times['start']
        end_time = times['end']

        if start_time and end_time: # Check if both start and end times are available
            start_datetime = datetime.combine(today, start_time)
            end_datetime = datetime.combine(today, end_time)
            if start_time < end_time: # Check if start is before end time
                hours = end_datetime - start_datetime
                total_hours.append(hours)

            elif start_time == time(0, 0) and end_time == time(0, 0): # If start & end time are both midnight, add 24 hours
                hours = timedelta(days=1)
                total_hours.append(hours)
            
            elif start_time > end_time and end_time == time(0, 0): # If end time is midnight, add hours from start to end of day
                end_datetime += timedelta(days=1)
                hours = end_datetime - start_datetime
                total_hours.append(hours)
    
    # Sum the total seconds of all the timedeltas for the week
    total_seconds = sum(td.total_seconds() for td in total_hours)

    # Convert the total seconds to hours & multiply for whole year
    total_hours_year = total_seconds / 3600 * 52  # 3600 seconds in an hour, 52 weeks in a year

    return total_hours_year

# Returns an dictionary of pressure_id: csv_url designed for the pressure csvs in bubble
def get_pressure_csvs(pressure_ids):
    pressure_csvs = {}
    for pressure_id in pressure_ids:
        pressure_json = get_req("pressure-sensor", pressure_id)
        if "csv-psig" in pressure_json["response"]:
            pressure_csv = pressure_json["response"]["csv-psig"]
            pressure_csv = f"https:{pressure_csv}"
            pressure_csvs[pressure_id] = pressure_csv
    
    return pressure_csvs

# converts a csv url into a dataframe
def csv_to_df(pressure_csv):
    response = requests.get(pressure_csv) # Step 2: Download the CSV file
    response.raise_for_status() # Check that the request was successful
    
    csv_data = StringIO(response.text) # Convert CSV into text of some sort
    
    df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column

    return df

# trim the df to be all synced up with other pressure csvs
def trim_df(report_json, df):
    trim_start = datetime.strptime(report_json["response"]["trim-start"], '%b %d, %Y %I:%M %p')
    trim_end = datetime.strptime(report_json["response"]["trim-end"], '%b %d, %Y %I:%M %p')
    df = df[(df.iloc[:, 1] >= trim_start) & (df.iloc[:, 1] <= trim_end)]

    return df

# returns dictionary = {operating_period_id: {pressure_id: avg_pressure}, etc..}
# currently don't have a front end setup to be able to varify pressure_ids tho...
def get_avg_pressures(report_json):
    pressure_ids = report_json["response"]["pressure-sensor"]

    pressure_csvs = get_pressure_csvs(pressure_ids) # Returns an dictionary = {pressure_id: csv_url, etc..}

    operating_period_ids = report_json["response"]["Operation Period"] # array of operating_period_ids
    op_per_type = report_json["response"]["operating_period_type"] # can be "Daily" or "Weekly"

    op_per_avg_pressures = {} # will hold {operating_period_id: {pressure_id: avg_pressure}, etc..}
    if op_per_type == "Daily":

        for operating_period_id in operating_period_ids:

            avg_pressures = {}
            for id, pressure_csv in pressure_csvs.items():

                df = csv_to_df(pressure_csv) # convert csv_url to dataframe

                if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
                    df = trim_df(report_json, df) # trim the df to be all synced up with other pressure csvs

                df = daily_operating_period(df, operating_period_id) # filter df by operating period
                avg_pressure = df.iloc[:, 2].mean()
                avg_pressures[id] = avg_pressure

            op_per_avg_pressures[operating_period_id] = avg_pressures

    elif op_per_type == "Weekly":

        for operating_period_id in operating_period_ids:

            avg_pressures = {}
            for id, pressure_csv in pressure_csvs.items():

                df = csv_to_df(pressure_csv) # convert csv_url to dataframe

                if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
                    df = trim_df(report_json, df) # trim the df to be all synced up with other pressure csvs

                df = weekly_operating_period(df, operating_period_id) # filter df by operating period
                avg_pressure = df.iloc[:, 2].mean()
                avg_pressures[id] = avg_pressure

            op_per_avg_pressures[operating_period_id] = avg_pressures
    
    return op_per_avg_pressures

                    


            
    
    
    ###########################################################################################################################################################
    ###########################################################################################################################################################
    if "pressure-sensor" in report_json["response"]:
        pressure_ids = report_json["response"]["pressure-sensor"]
        pressure_csvs = []
        
        op_per_avg_pressures = []
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
            op_per_avg_pressures.append(avg_pressures)
        my_dict["op_per_avg_pressures"] = op_per_avg_pressures
        print("Added: op_per_avg_pressures")

        my_dict["pressure_ids"] = pressure_ids
        print("Added: pressure_ids")
            # update_pressure_in_bubble(period_id, avg_pressures)

def compile_master_df(report_id, return_option=None):
    report_json = get_req("Report", report_id)
    ac_ids = report_json["response"]["Air Compressor"]

    my_dict = {}

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
            print("added first DataFrame to master_df")
        else:
            master_df = pd.merge(master_df, df, left_on=f"Date{idx}", right_on=f"Date{idx+1}", how="outer")
            print("Merged next Dataframe with master_df")
    
    if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
        trim_start = datetime.strptime(report_json["response"]["trim-start"], '%b %d, %Y %I:%M %p')
        trim_end = datetime.strptime(report_json["response"]["trim-end"], '%b %d, %Y %I:%M %p')
        master_df = master_df[(master_df.iloc[:, 1] >= trim_start) & (master_df.iloc[:, 1] <= trim_end)]
        print("Trimmed up the")

    op_per_type = report_json["response"]["operating_period_type"]
    
    operating_period_ids = report_json["response"]["Operation Period"]

    if op_per_type == "Daily":
        
        avg_acfms = []
        op_per_avg_kws = []
        op_per_hours_betweens = []
        op_per_kpis = []

        for operating_period_id in operating_period_ids:
            period_data = daily_operating_period(master_df, operating_period_id)

            avg_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            avg_acfms.append(avg_acfm)

            avg_kilowatts = period_data.filter(like='Kilowatts').sum(axis=1).mean()
            op_per_avg_kws.append(avg_kilowatts)

            kpi = avg_kilowatts/avg_acfm
            op_per_kpis.append(kpi)

            hours_diff = hours_between(operating_period_id)
            op_per_hours_betweens.append(hours_diff)
    elif op_per_type == "Weekly":
        avg_acfms = []
        op_per_avg_kws = []
        op_per_hours_betweens = []
        op_per_kpis = []
        for operating_period_id in operating_period_ids:
            period_data = weekly_operating_period(master_df, operating_period_id) # see def for explanation

            avg_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            avg_acfms.append(avg_acfm)
            avg_kilowatts = period_data.filter(like='Kilowatts').sum(axis=1).mean()
            op_per_avg_kws.append(avg_kilowatts)
            kpi = avg_kilowatts/avg_acfm
            op_per_kpis.append(kpi)
            hours_diff = hours_between_weekly(operating_period_id)
            op_per_hours_betweens.append(hours_diff)
        

    my_dict["op_per_avg_kws"] = op_per_avg_kws
    print("Added: op_per_avg_kws")

    my_dict["op_per_avg_acfms"] = avg_acfms
    print("Added: op_per_avg_acfms")

    my_dict["operating_period_ids"] = operating_period_ids
    print("Added: operating_period_ids")

    my_dict["op_per_hours_betweens"] = op_per_hours_betweens
    print("Added: op_per_hours_betweens")

    my_dict["op_per_kpis"] = op_per_kpis
    print("Added: op_per_kpis")

    max_flow_op = max(avg_acfms)

    # Get's peak 15, 10, 5, 3, and 2 min values just guessing on the 15 min low function because it seems like it will be 0 most of the time..

    # var name = the dataframe.get columns that include the name ACFM, add together on on axis for a "total" row then revers it's direction because the rolling function works from the bottom up, declare the window size, don't let it average less than the window size, flip back to normal direction fill all NaNs with 0's then get the max of the values.
    max_avg_15 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
    max_avg_10 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=50, min_periods=50).mean()[::-1].fillna(0).max()
    max_avg_5 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=25, min_periods=25).mean()[::-1].fillna(0).max()
    max_avg_3 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=15, min_periods=15).mean()[::-1].fillna(0).max()
    max_avg_2 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
    low_avg_15 = master_df.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).min()

    # compressor_capacity(report_id, cfms, max_flow_op, max_avg_15, max_avg_2)

    my_dict["cfms"] = cfms
    print("Added: cfms")

    my_dict["max_flow_op"] = max_flow_op
    print("Added: max_flow_op")

    my_dict["max_avg_15"] = max_avg_15
    print("Added: max_avg_15")

    my_dict["max_avg_2"] = max_avg_2
    print("Added: max_avg_2")



    kw_max_avg_15 = master_df.filter(like='Kilowatts').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()

    kpi_3_2 = kw_max_avg_15/max_avg_15


    my_dict["max_avg_10"] = max_avg_10
    print("Added: max_avg_10")
    
    my_dict["max_avg_5"] = max_avg_5
    print("Added: max_avg_5")
    
    my_dict["max_avg_3"] = max_avg_3
    print("Added: max_avg_3")
    
    my_dict["low_avg_15"] = low_avg_15
    print("Added: low_avg_15")
    
    my_dict["kpi_3_2"] = kpi_3_2
    print("Added: kpi_3_2")
    
    my_dict["kw_max_avg_15"] = kw_max_avg_15
    print("Added: kw_max_avg_15")

    my_dict["master_df"] = master_df
    print("Added: master_df")


    return my_dict

def testing():
    report_json = get_req("Report", "1696116368926x296884495425208300")
    ac_ids = report_json["response"]["Air Compressor"]

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

        if master_df is None:
            master_df = df
            print("added first DataFrame to master_df")
        else:
            master_df = pd.merge(master_df, df, left_on=f"Date{idx}", right_on=f"Date{idx+1}", how="outer")
            print("Merged next Dataframe with master_df")


    weekly_operating_period(master_df, "1696357876378x758860842273341400")