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
import re


def clean_json(my_json, processed_ids=None, additional_keys=None):
    
    try:
        my_json = my_json['response']
    except:
        print("Could not remove: my_json['response']")
    
    keys_to_remove = ["_id", "Modified Date", "Created Date", "Created By", "created_by_user_id"]

    if additional_keys is not None:
        keys_to_remove.extend(additional_keys)

    for key in keys_to_remove:
        print(f"Removed: {key}")
        my_json.pop(key, None)
    

    if processed_ids:
        new_json = {}

        for key, value in my_json.items():
            if value not in processed_ids:
                new_json[key] = value
            else:
                print(f"Removed: {key}: {value}")
                
        print('')
        return new_json
    else:
        return my_json


def find_ids(my_json):
    object_id_pattern = re.compile(r'^\d+x\d+$') # pattern states any number of numbers separated by an x e.g.(1x1) or (12423x0934)
    id_dict = {}
    for key, value in my_json.items(): # For each item in the clean json (should be clean)
        if isinstance(value, list): # if the value of this item is an array (LiSt)
            for id in value: # for each id in the list
                if object_id_pattern.match(str(id)) and len(str(id)) == 32: # if it matches pattern and is 32 characters add to dict
                    id_dict[key] = value
                break
        else:
            if object_id_pattern.match(str(value)) and len(str(value)) == 32: # if it's not a list then just check if the value matches and add to dictionary
                id_dict[key] = value

    
    return id_dict

def get_req(type, id, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}/{id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_list_req(type, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def del_req(type, id, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}/{id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.status_code

def post_req(type, body, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()

def patch_req(type, id, body, dev):
    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/{type}/{id}"
    
    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }
    try:
        response = requests.patch(url, json=body, headers=headers)
        # print(f"patched: {body}, {response.status_code}")
    except requests.RequestException as e:
        print(e)

def calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf):
    return min(round(amps * volts * (pf50 if amps < amppf else pf) * sqrt(3) / 1000, 2), bhp * 0.746)

def calculate_olol_acfm(amps, thresholds, cfm):
    return 0 if amps < thresholds else cfm

def get_polynomial_vars_vriable_capacity(report_id, ac_json, volts, dev):
    if "Customer CA" in ac_json["response"]:
        ac_name = ac_json["response"]["Customer CA"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    if "rated-psig" in ac_json["response"]:
        rated_psig = ac_json["response"]["rated-psig"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing value: 'Rated PSIG'! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    
    if "setpoint-psig" in ac_json["response"]:
        setpoint_psig = ac_json["response"]["setpoint-psig"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing Value: 'Setpoint PSIG'! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    correction_factor = 1 -((rated_psig - setpoint_psig) * 0.005)

    if "pf" in ac_json["response"]:
        pf = ac_json["response"]["pf"]
    else:
        pf = 0.97
    

    if "vfd_slope_entries" in ac_json["response"] and ac_json["response"]["vfd_slope_entries"] != []:
        slope_entry_ids = ac_json["response"]["vfd_slope_entries"]
        if len(slope_entry_ids) < 3:
            patch_req("Report", report_id, body={"loading": f"We need at least three Power / Capacity Entries in VFD compressors! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
    else:
        patch_req("Report", report_id, body={"loading": f"We need at least two Power / Capacity Entries in VFD compressors! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    power_input_kws = []
    capacity_acfms = []
    kw_to_amps = []
    corrected_amps = []
    for idx, slope_entry_id in enumerate(slope_entry_ids):
        slope_json = get_req("vfd_slope_entries", slope_entry_id, dev)
        
        if "power-input-kw" in slope_json["response"] and "capacity-acfm" in slope_json["response"]:
            power_input_kw = slope_json["response"]["power-input-kw"]
            power_input_kws.append(power_input_kw)

            capacity_acfm = slope_json["response"]["capacity-acfm"]
            capacity_acfms.append(capacity_acfm)
        else:
            patch_req("Report", report_id, body={"loading": f"Incomplete Power / Capacity Entry! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
    
        kw_to_amp = (1000 * power_input_kw) / (sqrt(3) * pf * volts)
        kw_to_amps.append(kw_to_amp)

        corrected_amp = kw_to_amp * correction_factor
        corrected_amps.append(corrected_amp)

    
    min_amps = min(corrected_amps)
    max_flow = max(capacity_acfms)

    coefficients = np.polyfit(corrected_amps, capacity_acfms, 2)
    a, b, c = coefficients

    return a, b, c, min_amps, max_flow

def get_polynomial_vars(report_id, ac_json, cfm, volts, dev):
    if "Customer CA" in ac_json["response"]:
        ac_name = ac_json["response"]["Customer CA"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    if "rated-psig" in ac_json["response"]:
        rated_psig = ac_json["response"]["rated-psig"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing value: 'Rated PSIG'! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    
    if "setpoint-psig" in ac_json["response"]:
        setpoint_psig = ac_json["response"]["setpoint-psig"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing Value: 'Setpoint PSIG'! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    correction_factor = 1 -((rated_psig - setpoint_psig) * 0.005)

    if "pf" in ac_json["response"]:
        pf = ac_json["response"]["pf"]
    else:
        pf = 0.97
    

    if "vfd_slope_entries" in ac_json["response"] and ac_json["response"]["vfd_slope_entries"] != []:
        slope_entry_ids = ac_json["response"]["vfd_slope_entries"]
        if len(slope_entry_ids) < 3:
            patch_req("Report", report_id, body={"loading": f"We need at least three Power / Capacity Entries in VFD compressors! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
    else:
        patch_req("Report", report_id, body={"loading": f"We need at least two Power / Capacity Entries in VFD compressors! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    power_input_kws = []
    capacity_acfms = []
    kw_to_amps = []
    corrected_amps = []
    corrected_acfms = []
    for idx, slope_entry_id in enumerate(slope_entry_ids):
        slope_json = get_req("vfd_slope_entries", slope_entry_id, dev)
        
        if "power-input-kw" in slope_json["response"] and "capacity-acfm" in slope_json["response"]:
            power_input_kw = slope_json["response"]["power-input-kw"]
            power_input_kws.append(power_input_kw)

            capacity_acfm = slope_json["response"]["capacity-acfm"]
            capacity_acfms.append(capacity_acfm)
        else:
            patch_req("Report", report_id, body={"loading": f"Incomplete Power / Capacity Entry! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
    
        kw_to_amp = (1000 * power_input_kw) / (sqrt(3) * pf * volts)
        kw_to_amps.append(kw_to_amp)

        corrected_amp = kw_to_amp * correction_factor
        corrected_amps.append(corrected_amp)

        if idx == 0:
            corrected_acfm = cfm
        else:
            corrected_acfm = cfm / capacity_acfms[0] * capacity_acfm
        print(f"Corrected ACFM: {corrected_acfm}")
        corrected_acfms.append(corrected_acfm)
    
    min_amps = min(corrected_amps)
    max_flow = max(corrected_acfms)

    coefficients = np.polyfit(corrected_amps, corrected_acfms, 2)
    a, b, c = coefficients

    return a, b, c, min_amps, max_flow

def calculate_slope_intercept(report_id, ac_json, cfm, volts, dev):
    if "Customer CA" in ac_json["response"]:
        ac_name = ac_json["response"]["Customer CA"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    
    if "rated-psig" in ac_json["response"]:
        rated_psig = ac_json["response"]["rated-psig"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing value: 'Rated PSIG'! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    
    if "setpoint-psig" in ac_json["response"]:
        setpoint_psig = ac_json["response"]["setpoint-psig"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing Value: 'Setpoint PSIG'! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    correction_factor = 1 -((rated_psig - setpoint_psig) * 0.005)
    
    if "kw_at_full_load" in ac_json["response"]:
        kw_at_full_load = ac_json["response"]["kw_at_full_load"]
    else:
        patch_req("Report", report_id, body={"loading": f"Missing Value: 'kw_at_full_load'! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    
    if "pf" in ac_json["response"]:
        pf = ac_json["response"]["pf"]
    else:
        pf = 0.97

    kw_to_amp = (1000 * kw_at_full_load) / (sqrt(3) * pf * volts)

    corrected_amp = kw_to_amp * correction_factor

    corrected_amps = [corrected_amp, (corrected_amp * 0.7)]
    corrected_acfms = [cfm, 0]

    min_amps = min(corrected_amps)


    slope, intercept = np.polyfit(corrected_amps, corrected_acfms, 1)

    return slope, intercept, min_amps

def calculate_vfd_acfm(amps, a, b, c, min_amps, max_flow):

    init_flow = a * amps**2 + b * amps + c

    if amps < min_amps:
        return 0
    elif init_flow > max_flow:
        return max_flow
    else:
        return init_flow

def calculate_inlet_mod_acfm(amps, slope, intercept, min_amps, max_flow):
    
    init_flow = amps * slope + intercept

    if amps < min_amps:
        return 0
    elif init_flow > max_flow:
        return max_flow
    else:
        return init_flow

def calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id):
    print(f"control: {control}")
    if control == "Fixed Speed - OLOL":
        if "threshold-value" in ac_json["response"]:
            threshold = ac_json["response"]["threshold-value"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Threshold Value! This is needed for ACFM calculations on OLOL control types. Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_olol_acfm(amps, threshold, cfm))
        return df
    elif control == "Variable Speed - VFD":
        print(f"Control Type: {control}")
        a, b, c, min_amps, max_flow  = get_polynomial_vars(report_id, ac_json, cfm, volts, dev)
        print(a, b, c, min_amps, max_flow)
        df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_vfd_acfm(amps, a, b, c, min_amps, max_flow))
        return df
    elif control == "Fixed Speed - Inlet Modulation":
        slope, intercept, min_amps = calculate_slope_intercept(report_id, ac_json, cfm, volts, dev)
        df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_inlet_mod_acfm(amps, slope, intercept, min_amps, cfm))
        return df
    elif control == "Fixed Speed - Variable Capacity":
        a, b, c, min_amps, max_flow = get_polynomial_vars_vriable_capacity(report_id, ac_json, volts, dev)
        print(a, b, c, min_amps, max_flow)
        df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_vfd_acfm(amps, a, b, c, min_amps, max_flow))
        return df
    else:
        patch_req("Report", report_id, body={"loading": f"Cannot calculate Flow! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        sys.exit()


# gets start & end time for each day of the week returned in a dictionary.
def weekly_dictionary(operating_period_id, dev):
    operating_period_json = get_req("operation_period", operating_period_id, dev)

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
def hours_between(operating_period_id, dev):
    operating_period_json = get_req("operation_period", operating_period_id, dev)
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
def weekly_operating_period(df, operating_period_id, dev):
    operating_period = weekly_dictionary(operating_period_id, dev) # gets start & end time for each day of the week and stores in a dictionary.

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
def daily_operating_period(df, operating_period_id, dev):
    operating_period_json = get_req("operation_period", operating_period_id, dev)
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
def hours_between_weekly(operating_period_id, dev):
    operating_period = weekly_dictionary(operating_period_id, dev) # gets start & end time for each day of the week and stores in a dictionary.

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

# Get's the total number of minutes selected per week without duplicates for overlapping time ranges.
# Can return just the total minutes or the weekly_schedule if you're comparing operating periods
def minutes_between_experimental(op_id, dev):
    op_json = get_req("operation_period", op_id, dev) # Get's a json object of all the time_range IDs
    time_ranges = op_json["response"]["time_range"] # List if time_range IDs

    # List of 10080 False values e.g. = [False, False, False, False, False, False...]
    # Each index represents a minute in the week. e.g. index 120 would be equal to Monday at 2:00 AM. 121 = Monday at 2:01 AM etc.
    # The plan is to mark each minute as true based on the user-entered times. This way if we have any overlap the minute will only ever be marked as True so we can't have more than 10080 minutes in a week.
    weekly_schedule = [False] * 10080

    # For each time range in this operation period
    for time_range in time_ranges:
        time_json = get_req("time_range", time_range, dev) # Get the json for each range
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] # Will be used to carry over to the next day by adding 1 to the index
        days = time_json["response"]["repeat_on_weekly"] # Get's the list of days selected by the user.

        if time_json["response"]["all_day"] == True: # If "All Day" is checked
            for day in days: # Loop through each day selected by the user
                day_idx = days_of_week.index(day) # Get the index for the day selected by the user from the initialized "days_of_week" list. "Monday" would = 0
                for minute in range(1440): # Loop through an arbitrary for loop 1440 times

                    # Get the day_idx (Monday = 0) * 1440 mins per day 0 = monday at 12am 1440 = tuesday at 12am
                    weekly_schedule[day_idx * 1440 + minute] = True # Mark each minute in this entire day as True
        
        else: # If "All Day" is NOT checked

            #Get convert start and end times to time objects - Must be formatted like "9:45 PM"
            start_time = datetime.strptime(time_json["response"]["start_time"], '%I:%M %p').time()
            end_time = datetime.strptime(time_json["response"]["end_time"], '%I:%M %p').time()


            for day in days: # Loop through each day selected by the user
                day_idx = days_of_week.index(day) # Get the index for the day selected by the user from the initialized "days_of_week" list. "Sunday" would = 6
                
                # Total number of minutes from the 12:00 AM for this day
                start_minute = start_time.hour * 60 + start_time.minute
                end_minute = end_time.hour * 60 + end_time.minute

                if start_time > end_time: # Over night case (If the start time is earlier than the end time carry over night)
                    for minute in range(int(start_minute), 1440):
                        weekly_schedule[day_idx * 1440 + minute] = True
                    end_day_idx = day_idx + 1 if day_idx < 6 else 0

                    for minute in range(int(end_minute)):
                        weekly_schedule[end_day_idx * 1440 + minute] = True

                else:
                    for minute in range(int(start_minute), int(end_minute)):
                        weekly_schedule[day_idx * 1440 + minute] = True
    
    weekly_minutes = sum(weekly_schedule) # Adds together only true values in list -- e.g. sum([False, True, False, True]) = 2

    total_minutes = weekly_minutes * 52

    return total_minutes, weekly_schedule
                

def experimental_operating_period(df, op_id, dev):
    op_json = get_req("operation_period", op_id, dev) # Get's a json object of all the time_range IDs
    time_ranges = op_json["response"]["time_range"] # List if time_range IDs

    filtered_dfs = []
    
    for time_range in time_ranges:
        time_json = get_req("time_range", time_range, dev) # For each time range get the json for each range
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

    return final_df

# Returns an dictionary of pressure_id: csv_url designed for the pressure csvs in bubble
def get_pressure_csvs(report_id, pressure_ids, dev):
    pressure_csvs = {}
    for pressure_id in pressure_ids:
        pressure_json = get_req("pressure_sensor", pressure_id, dev)
        if "csv-psig" in pressure_json["response"]:
            pressure_csv = pressure_json["response"]["csv-psig"]
            pressure_csv = f"https:{pressure_csv}"
            pressure_csvs[pressure_id] = pressure_csv
        else:
            patch_req("Report", report_id, body={"loading": f"Unable to find Pressure CSV! Make sure all pressure sensors added have a CSV Uploaded", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
    return pressure_csvs

# converts a csv url into a dataframe
def csv_to_df(csv_url):
    response = requests.get(csv_url) # Step 2: Download the CSV file
    response.raise_for_status() # Check that the request was successful
    
    csv_data = StringIO(response.text) # Convert CSV into text of some sort
    
    df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column

    return df

# trim the df to be all synced up with other pressure csvs
def trim_df(report_json, df, dev):
    try:
        trim_id = report_json["response"]["trim"]
        report_id = report_json["response"]["_id"]
        trim_json = get_req("trim", trim_id, dev)

        start_date = datetime.strptime(trim_json["response"]["start_date"], "%Y-%m-%dT%H:%M:%S.%fZ")
        start_time = datetime.strptime(trim_json["response"]["start_time"], "%I:%M %p")
        start = start_date.replace(hour=start_time.hour, minute=start_time.minute)

        end_date = datetime.strptime(trim_json["response"]["end_date"], "%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = datetime.strptime(trim_json["response"]["end_time"], "%I:%M %p")
        end = end_date.replace(hour=end_time.hour, minute=end_time.minute)

        df = df[(df.iloc[:, 1] >= start) & (df.iloc[:, 1] <= end)]

        return df
    except:
        patch_req("Report", report_id, body={"loading": f"We're having some trouble Trimming your dataset. Make sure the times are formatted exactly like '9:00 AM'.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

# Takes in a DataFrame and ouputs a dataframe with excluded time ranges from user input
def exclude_from_df(df, report_json, dev):
    try:
        exclusion_ids = report_json["response"]["exclusion"]
        report_id = report_json["response"]["_id"]

        # Initialize a mask with all False (i.e., don't exclude any row initially)
        exclusion_mask = pd.Series([False] * len(df), index=df.index)

        # Add each exclusion to the mask
        for exclusion_id in exclusion_ids:
            exclusion_json = get_req("exclusion", exclusion_id, dev)
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
        patch_req("Report", report_id, body={"loading": f"We're having some trouble removing Exclusions from your dataset. Make sure the times are formatted exactly like '9:00 AM'.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

def sanitize_filename(filename):
    # Define the allowed characters
    allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    # Replace characters that are not in the allowed set with "_"
    sanitized = ''.join(char if char in allowed_chars else '_' for char in filename)
    
    return sanitized

# Returns a Dictionary = {"pressure_id": {"15-min-peak": 123, "10-min-peak": 321, etc..}, etc..}
def get_pressure_peaks(report_id, report_json, dev):
    pressure_ids = report_json["response"]["pressure_sensor"]

    pressure_peaks = {}
    for id in pressure_ids:
        pressure_json = get_req("pressure_sensor", id, dev)
        if "csv-psig" in pressure_json["response"]:
            pressure_csv = pressure_json["response"]["csv-psig"]
            pressure_csv = f"https:{pressure_csv}"
        else:
            patch_req("Report", report_id, body={"loading": f"Unable to find Pressure CSV! Make sure all pressure sensors added have a CSV Uploaded", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        df = csv_to_df(pressure_csv) # convert csv_url to dataframe

        if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
            df = trim_df(report_json, df, dev) # trim the df to be all synced up with other pressure csvs

        if "exclusion" in report_json["response"]:
            df = exclude_from_df(df, report_json, dev)

        pressure_peak_15 = df.iloc[:, 2][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
        pressure_peak_10 = df.iloc[:, 2][::-1].rolling(window=50, min_periods=50).mean()[::-1].fillna(0).max()
        pressure_peak_5 = df.iloc[:, 2][::-1].rolling(window=25, min_periods=25).mean()[::-1].fillna(0).max()
        pressure_peak_3 = df.iloc[:, 2][::-1].rolling(window=15, min_periods=15).mean()[::-1].fillna(0).max()
        pressure_peak_2 = df.iloc[:, 2][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
        pressure_low_15 = df.iloc[:, 2][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).min()

        pressure_peaks[id] = {
            "15-min-peak": pressure_peak_15,
            "10-min-peak": pressure_peak_10,
            "5-min-peak": pressure_peak_5,
            "3-min-peak": pressure_peak_3,
            "2-min-peak": pressure_peak_2,
            "15-min-low": pressure_low_15
            }
    
    return pressure_peaks

# returns dictionary = {operating_period_id: {pressure_id: avg_pressure}, etc..}
# currently don't have a front end setup to be able to varify pressure_ids for operating periods...
def get_avg_pressures(report_id, report_json, dev):
    pressure_ids = report_json["response"]["pressure_sensor"]

    patch_req("Report", report_id, body={"loading": f"Reading Pressure CSVs...", "is_loading_error": "no"}, dev=dev)
    pressure_csvs = get_pressure_csvs(report_id, pressure_ids, dev) # Returns an dictionary = {pressure_id: csv_url, etc..}

    operating_period_ids = report_json["response"]["operation_period"] # array of operating_period_ids
    op_per_type = report_json["response"]["operating_period_type"] # can be "Daily" or "Weekly"

    patch_req("Report", report_id, body={"loading": f"Calculating Average Pressure for each Pressure Log in each Operating Period...", "is_loading_error": "no"}, dev=dev)
    op_per_avg_pressures = {} # will hold {operating_period_id: {pressure_id: avg_pressure}, etc..}
    if op_per_type == "Daily":

        for operating_period_id in operating_period_ids:

            avg_pressures = {}
            for id, pressure_csv in pressure_csvs.items():

                df = csv_to_df(pressure_csv) # convert csv_url to dataframe

                if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
                    df = trim_df(report_json, df, dev) # trim the df to be all synced up with other pressure csvs

                if "exclusion" in report_json["response"]:
                    df = exclude_from_df(df, report_json, dev)

                df = daily_operating_period(df, operating_period_id, dev) # filter df by operating period
                avg_pressure = df.iloc[:, 2].mean()
                avg_pressures[id] = avg_pressure

            op_per_avg_pressures[operating_period_id] = avg_pressures

    elif op_per_type == "Weekly":

        for operating_period_id in operating_period_ids:

            avg_pressures = {}
            for id, pressure_csv in pressure_csvs.items():

                df = csv_to_df(pressure_csv) # convert csv_url to dataframe

                if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
                    df = trim_df(report_json, df, dev) # trim the df to be all synced up with other pressure csvs
                
                if "exclusion" in report_json["response"]:
                    df = exclude_from_df(df, report_json, dev)

                df = weekly_operating_period(df, operating_period_id, dev) # filter df by operating period
                avg_pressure = df.iloc[:, 2].mean()
                avg_pressures[id] = avg_pressure

            op_per_avg_pressures[operating_period_id] = avg_pressures
    
    return op_per_avg_pressures




def compile_master_df(report_id, dev):
    report_json = get_req("report", report_id, dev)
    if "air_compressor" in report_json["response"] and report_json["response"]["air_compressor"] != []:
        ac_ids = report_json["response"]["air_compressor"]
    else:
        patch_req("Report", report_id, body={"loading": f"Unable to find any Air Compressors! You need at least one Air Compressor for this Chart.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    my_dict = {}

    master_df = None
    cfms = []
    for idx, ac in enumerate(ac_ids):
        ac_json = get_req("air_compressor", ac, dev)
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor ID: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        patch_req("Report", report_id, body={"loading": f"Getting started on {ac_name}...", "is_loading_error": "no"}, dev=dev)

        if "ac_data_logger" in ac_json["response"] and ac_json["response"]["ac_data_logger"] != []:
            ac_data_logger_id = ac_json["response"]["ac_data_logger"]
            ac_data_logger_json = get_req("ac_data_logger", ac_data_logger_id, dev)
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        if "CSV" in ac_data_logger_json["response"]:
            csv_url = ac_data_logger_json["response"]["CSV"]
            csv_url = f"https:{csv_url}"
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        patch_req("Report", report_id, body={"loading": f"{ac_name}: Reading CSV...", "is_loading_error": "no"}, dev=dev)
        df = csv_to_df(csv_url)
        # response = requests.get(csv_url) # Step 2: Download the CSV file
        # response.raise_for_status() # Check that the request was successful
            
        # csv_data = StringIO(response.text) # Convert CSV into text of some sort
        # df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
        patch_req("Report", report_id, body={"loading": f"{ac_name}: Kilowatts{idx+1} Column...", "is_loading_error": "no"}, dev=dev)
        if "volts" in ac_json["response"]:
            volts = ac_json["response"]["volts"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Volts! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "pf if fifty" in ac_json["response"]:
            pf50 = ac_json["response"]["pf if fifty"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Power Factor When Less Than 50% Load! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "pf" in ac_json["response"]:
            pf = ac_json["response"]["pf"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Power Factor! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "amps less pf" in ac_json["response"]:
            amppf = ac_json["response"]["amps less pf"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Amps Less Than For Power Factor! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "BHP" in ac_json["response"]:
            bhp = ac_json["response"]["BHP"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing BHP! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        df[f"Kilowatts{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf))

        patch_req("Report", report_id, body={"loading": f"{ac_name}: ACFM Column...", "is_loading_error": "no"}, dev=dev)
        # Create ACFM Column

        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            patch_req("Report", report_id, body={"loading": f"Missing Control Type! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if control == "Fixed Speed - Variable Capacity":
            cfm = 1
        else:
            if "CFM" in ac_json["response"]:
                cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
                cfms.append(cfm)
            else:
                patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()
        
        # if "CFM" in ac_json["response"]:
        #     cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        #     cfms.append(cfm)
        # elif control != "Fixed Speed - Variable Capacity":
        #     patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        #     sys.exit(1)
        # else:
        #     cfm = 1

        df = calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id)

        # if control == "OLOL":
        #     if "threshold-value" in ac_json["response"]:
        #         threshold = ac_json["response"]["threshold-value"]
        #     else:
        #         patch_req("Report", report_id, body={"loading": f"Missing Threshold Value! This is needed for ACFM calculations on OLOL control types. Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        #         sys.exit()
        #     df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_olol_acfm(amps, threshold, cfm))
        # elif control == "VFD":
        #     slope, intercept = calculate_slope_intercept(report_id, ac_json, cfm, volts, dev)
        #     df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: calculate_vfd_acfm(amps, slope, intercept))
        
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
            patch_req("Report", report_id, body={"loading": f"{ac_name}: Merging with other CSVs...", "is_loading_error": "no"}, dev=dev)
            print("Merged next Dataframe with master_df")
    
    if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
        patch_req("Report", report_id, body={"loading": f"Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = trim_df(report_json, master_df, dev)

    my_dict["master_df"] = master_df
    print("Added: master_df")

    if "exclusion" in report_json["response"]:
        patch_req("Report", report_id, body={"loading": f"Removing Exclusiong from the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = exclude_from_df(master_df, report_json, dev)

    if "operation_period" in report_json["response"] and report_json["response"]["operation_period"] != []:
        op_per_type = report_json["response"]["operating_period_type"]
        
        operating_period_ids = report_json["response"]["operation_period"]
        patch_req("Report", report_id, body={"loading": f"Found {len(operating_period_ids)} Operating Period{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        patch_req("Report", report_id, body={"loading": "No Operating Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    

    if op_per_type == "Daily":
        
        avg_acfms = []
        op_per_avg_kws = []
        op_per_hours_betweens = []
        op_per_kpis = []

        for operating_period_id in operating_period_ids:
            period_data = daily_operating_period(master_df, operating_period_id, dev)

            avg_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            avg_acfms.append(avg_acfm)

            avg_kilowatts = period_data.filter(like='Kilowatts').sum(axis=1).mean()
            op_per_avg_kws.append(avg_kilowatts)

            kpi = avg_kilowatts/avg_acfm
            op_per_kpis.append(kpi)

            hours_diff = hours_between(operating_period_id, dev)
            op_per_hours_betweens.append(hours_diff)
    elif op_per_type == "Weekly":
        avg_acfms = []
        op_per_avg_kws = []
        op_per_hours_betweens = []
        op_per_kpis = []
        for operating_period_id in operating_period_ids:
            period_data = weekly_operating_period(master_df, operating_period_id, dev) # see def for explanation

            avg_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            avg_acfms.append(avg_acfm)
            avg_kilowatts = period_data.filter(like='Kilowatts').sum(axis=1).mean()
            op_per_avg_kws.append(avg_kilowatts)
            kpi = avg_kilowatts/avg_acfm
            op_per_kpis.append(kpi)
            hours_diff = hours_between_weekly(operating_period_id, dev)
            op_per_hours_betweens.append(hours_diff)
    elif op_per_type == "Experimental":
        avg_acfms = []
        op_per_avg_kws = []
        op_per_hours_betweens = []
        op_per_kpis = []
        for operating_period_id in operating_period_ids:
            period_data = experimental_operating_period(master_df, operating_period_id, dev)

            avg_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            avg_acfms.append(avg_acfm)

            avg_kilowatts = period_data.filter(like='Kilowatts').sum(axis=1).mean()
            op_per_avg_kws.append(avg_kilowatts)

            kpi = avg_kilowatts/avg_acfm
            op_per_kpis.append(kpi)

            mins_diff, _ = minutes_between_experimental(operating_period_id, dev)
            hours_diff = mins_diff / 60
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

    my_dict["master_df_excluded"] = master_df
    print("Added: master_df")


    return my_dict
