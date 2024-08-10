import sys
import json
import common_functions
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from utilities import data_crunch_util, financial_util, compressor_util, requests_util, baseline_proposed_7_1_util


# Returns the id of the pressure sensor and the index of the pressure sensor
def get_pressure_sensor(report_id, dev):
    report_json = requests_util.get_req("Report", report_id, dev)
    pressure_sensors = report_json["response"]["pressure_sensor"]

    idx = 0
    for sensor in pressure_sensors:
        sensor_json = requests_util.get_req("pressure_sensor", sensor, dev)
        if sensor_json["response"]["header"] == True:
            return sensor_json["response"]["_id"], idx
        
        idx += 1
        
# Make sure we have everything we need before running
def check_dependencies(report_id, report_json, dev):
    requests_util.patch_req("Report", report_id, body={"loading": f"Checking Dependencies...", "is_loading_error": "no"}, dev=dev)

    # Checking if we have at least one operation period
    try:
        operation_period_ids = report_json["response"]["operation_period"]
    except:
        print(f"No Operating Periods found! You need at least on operation period...", file=sys.stderr)
        sys.exit(1)


    # Checking if we have the necessary data from section 3.2
    # try:
    #     peak_acfm_15 = report_json["response"]["15 Min Peak Flow"]
    #     # kw_max_avg_15 = report_json["response"]["kw_max_avg_15"] # Should only get for demand schedule not entire report
    # except:
    #     print(f"You'll need to run Section 3.2 before you run this one...", file=sys.stderr)
    #     sys.exit(1)
    


    # Checking if we have electrical utility providers entered
    try:
        electrical_provider = report_json["response"]["electrical_provider"]

        electrical_provider_json = requests_util.get_req("electrical_provider", electrical_provider, dev)
        on_peak_start = electrical_provider_json["response"]["on_peak_start"]
        off_peak_start = electrical_provider_json["response"]["off_peak_start"]

        electrical_provider_entrys = electrical_provider_json["response"]["electrical_provider_entry"]

    except:
        print(f"You'll need to run Section 3.2 before you run this one...", file=sys.stderr)
        sys.exit(1)
    
    baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = requests_util.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)

    demand_schedule_id = baseline_operation_7_1_json["response"]["demand_schedule_id"]

    # try:
    #     kw_max_avg_15 = df_calcs(report_id, report_json, demand_schedule_id, dev)
    # except:
    #     print(f"Something Went wrong getting 15 min kw for this operating period...", file=sys.stderr)
    #     sys.exit(1)
    # try:
    # except Exception as e:
    #     print(f"Please Select an Operation Period to define the Demand calculations...{e}", file=sys.stderr)
    #     sys.exit(1)

    
    return on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id
    

def create_first_baseline_operation_7_1(report_id, dev):
    response = requests_util.post_req("baseline_operation_7_1", body={"report": report_id}, dev=dev)
    baseline_operation_7_1 = response["id"]

    requests_util.patch_req("report", report_id, body={"baseline_operation_7_1": baseline_operation_7_1}, dev=dev)
    
    return baseline_operation_7_1

def reset_rows(report_id, report_json, dev):
    requests_util.patch_req("Report", report_id, body={"loading": f"Resetting Any Existing Data...", "is_loading_error": "no"}, dev=dev)

    try:
        baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]

    except:
        baseline_operation_7_1 = create_first_baseline_operation_7_1(report_id, dev)
    
    # Deleting any rows if they exist
    baseline_operation_7_1_json = requests_util.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)
    try:
        baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

        for row in baseline_operation_7_1_rows:
            requests_util.del_req("baseline_operation_7_1_row", row, dev)
    except:
        print(f"No Rows Found, I guess")

    requests_util.patch_req("Report", report_id, body={"loading": f"Getting started on the Calculations...", "is_loading_error": "no"}, dev=dev)

    return baseline_operation_7_1

def get_pressure_index(report_id, op_json, dev):
    _, i = get_pressure_sensor(report_id, dev)
    
    try:
        pressure = op_json["response"]["P2"][i]
        return pressure
    except:
        requests_util.patch_req("Report", report_id, body={"loading": "Cannot find the pressure in the Operating Period. Maybe Try running section 3.2?", "is_loading_error": "no"}, dev=dev)
        print(f"Found a Pressure Log but couldn't work with the name. Make sure it's formatted exactly like: P4", file=sys.stderr)
        sys.exit(1)

# def filter_df(df, report_json, op_id, dev):
#     op_per_type = report_json["response"]["operating_period_type"]

#     if op_per_type == "Daily":
        
#         return common_functions.daily_operating_period(df, op_id, dev) # Filter dataframe to operating period

#     elif op_per_type == "Weekly":

#         return common_functions.weekly_operating_period(df, op_id, dev) # Filter dataframe to operating period
        
#     elif op_per_type == "Experimental":

#         return common_functions.experimental_operating_period(df, op_id, dev) # Filter dataframe to operating period

def calculate_row(report_json, demand_schedule_id, op_id, op_json, baseline_operation_7_1, dev):

    # period_data = filter_df(df, report_json, op_id, dev)
    period_data = data_crunch_util.get_op_data_crunch(op_id, dev)
    
    report_id = report_json["response"]["_id"]

    # Average Calcs
    average_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
    average_kw_demand = period_data.filter(like='Kilowatts').sum(axis=1).mean()

    # Peak 15 min Calcs
    peak_15min_acfm = period_data.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
    kw_demand_15min = period_data.filter(like='Kilowatts').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
    print(f"kw_demand_15min: {kw_demand_15min}")

    try:
        hours_annual = op_json["response"]["Hours/yr"]
    except:
        print(f"Did you already run section 3.2? You need to if you haven't.", file=sys.stderr)
        sys.exit(1)


    pressure = get_pressure_index(report_id, op_json, dev)

    kwh_annual = average_kw_demand * hours_annual

    cost_to_operate = financial_util.get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id, op_id, dev)

    label = op_json["response"]["Name"]

    body = {
        "peak_15min_acfm": peak_15min_acfm,
        "average_acfm": average_acfm,
        "pressure": pressure,
        "hours_annual": hours_annual,
        "average_kw_demand": average_kw_demand,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate,
        "baseline_operation_7_1": baseline_operation_7_1,
        "label": label
    }

    if demand_schedule_id == op_id:
        body["kw_demand_15min"] = kw_demand_15min

    response = requests_util.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def get_ac_ids_for_dryer(report_json, connected_to, dev):
    ac_ids = report_json["response"]["air_compressor"]

    connected_to_list = connected_to.split(", ")

    connected_ac_ids = []

    idxs = []
    for idx, ac_id in enumerate(ac_ids):
        ac_json = requests_util.get_req("air_compressor", ac_id, dev)
        name = ac_json["response"]["Customer CA"]
        
        if name in connected_to_list:
            connected_ac_ids.append(ac_id)
            idxs.append(idx+1)
        
    
    return connected_ac_ids, idxs

def get_cfm_df(report_json, ac_ids, dev):
    report_id = report_json["response"]["_id"]
    cfms = []
    master_df = None
    for idx, ac in enumerate(ac_ids):
        ac_json = requests_util.get_req("air_compressor", ac, dev)
        ac_name = ac_json["response"]["Customer CA"]

        if "ac_data_logger" in ac_json["response"] and ac_json["response"]["ac_data_logger"] != []:
            ac_data_logger_id = ac_json["response"]["ac_data_logger"]
            ac_data_logger_json = requests_util.get_req("ac_data_logger", ac_data_logger_id, dev)
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        if "CSV" in ac_data_logger_json["response"]:
            csv_url = ac_data_logger_json["response"]["CSV"]
            csv_url = f"https:{csv_url}"
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        # patch_req("Report", report_id, body={"loading": f"{ac_name}: Reading CSV...", "is_loading_error": "no"}, dev=dev)
        df = common_functions.csv_to_df(csv_url)
        # response = requests.get(csv_url) # Step 2: Download the CSV file
        # response.raise_for_status() # Check that the request was successful
            
        # csv_data = StringIO(response.text) # Convert CSV into text of some sort
        # df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column
        # patch_req("Report", report_id, body={"loading": f"{ac_name}: Kilowatts{idx+1} Column...", "is_loading_error": "no"}, dev=dev)
        if "volts" in ac_json["response"]:
            volts = ac_json["response"]["volts"]
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing Volts! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "pf if fifty" in ac_json["response"]:
            pf50 = ac_json["response"]["pf if fifty"]
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing Power Factor When Less Than 50% Load! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "pf" in ac_json["response"]:
            pf = ac_json["response"]["pf"]
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing Power Factor! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "amps less pf" in ac_json["response"]:
            amppf = ac_json["response"]["amps less pf"]
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing Amps Less Than For Power Factor! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "BHP" in ac_json["response"]:
            bhp = ac_json["response"]["BHP"]
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing BHP! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        # patch_req("Report", report_id, body={"loading": f"{ac_name}: ACFM Column...", "is_loading_error": "no"}, dev=dev)
        # Create ACFM Column

        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            # patch_req("Report", report_id, body={"loading": f"Missing Control Type! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        cfm = compressor_util.get_cfm(control, ac_json, ac_name, dev)
        cfms.append(cfm)
        
        # if "CFM" in ac_json["response"]:
        #     cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        #     cfms.append(cfm)
        # elif control != "Fixed Speed - Variable Capacity":
        #     patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        #     sys.exit(1)
        # else:
        #     cfm = 1

        df = common_functions.calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id)

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
            # patch_req("Report", report_id, body={"loading": f"{ac_name}: Merging with other CSVs...", "is_loading_error": "no"}, dev=dev)
            print("Merged next Dataframe with master_df")
    
    # master_df_pressure = add_pressure_to_master_df(master_df, report_id, dev)

    if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
        # patch_req("Report", report_id, body={"loading": f"Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = common_functions.trim_df(report_json, master_df, dev)

    # my_dict["master_df"] = master_df
    # print("Added: master_df")

    if "exclusion" in report_json["response"]:
        # patch_req("Report", report_id, body={"loading": f"Removing Exclusiong from the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = common_functions.exclude_from_df(master_df, report_json, dev)

    return master_df
    
    master_df[f"Kilowatts"] = master_df.filter(like='ACFM').sum(axis=1).apply(lambda amps: calculate_dryer_kw_row(amps, volts, pf50, amppf, bhp, pf))

def calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm, dryer_json):
    try:
        multiplication_factor = dryer_json["response"]["multiplication_factor_cfm"]
    except:
        multiplication_factor = 1

    acfm = acfm * multiplication_factor

    x = [(capacity_scfm*0.1), capacity_scfm]
    y = [(full_load_kw*0.55), full_load_kw]

    slope, intercept = np.polyfit(x, y, 1)

    return slope * acfm + intercept

def get_cfm_loss_dpd(acfm, capacity_scfm, type):
    operational_factor = acfm / capacity_scfm

    if type == "Desiccant Dryer No Heat":
        cfm_loss = capacity_scfm * 0.18 * operational_factor
        return cfm_loss
    elif type == "Desiccant With Heat":
        cfm_loss = capacity_scfm * 0.08 * operational_factor
        return cfm_loss
    elif type == "Desiccant With Heat & Blower":
        cfm_loss = capacity_scfm * 0.03 * operational_factor
        return cfm_loss
    elif type == "Refrigerated":
        cfm_loss = 0
        return cfm_loss

def get_dryer_cfm_loss(capacity_scfm, type):
    
    if type == "Desiccant Dryer No Heat":
        cfm_loss = capacity_scfm * 0.18
        return cfm_loss
    elif type == "Desiccant With Heat":
        cfm_loss = capacity_scfm * 0.08
        return cfm_loss
    elif type == "Desiccant With Heat & Blower":
        cfm_loss = capacity_scfm * 0.03
        return cfm_loss
    elif type == "Refrigerated":
        cfm_loss = 0
        return cfm_loss

def calculate_dryer_row(report_json, baseline_operation_7_1, kw, kw_demand_15min, dev):
    
    average_kw_demand = kw

    total_hours = report_json["response"]["total_hours"]

    kwh_annual = average_kw_demand * total_hours

    cost_to_operate = financial_util.get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id="Dryers", op_id=None, dev=dev)

    label = "Dryers"

    body = {
        "average_kw_demand": average_kw_demand,
        "kw_demand_15min": kw_demand_15min,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate,
        "baseline_operation_7_1": baseline_operation_7_1,
        "label": label
    }

    response = requests_util.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def timed_kw_calc(dryer_json, full_load_kw):
    try:
        # e.g. 50
        load_factor = dryer_json["response"]["desiccant_load_factor_kw"]
    except:
        print(f"Missing Load Factor for Timed Dryer", file=sys.stderr)
        sys.exit(1)
    
    avg_kw = full_load_kw * (load_factor / 100)

    return avg_kw

def dpd_kw_calc(acfm, full_load_kw, capacity_scfm, dryer_json):
    try:
        multiplication_factor = dryer_json["response"]["multiplication_factor_cfm"]
    except:
        multiplication_factor = 1
        
    acfm = acfm * multiplication_factor

    try:
        # e.g. 50
        load_factor = dryer_json["response"]["desiccant_load_factor_kw"]
    except:
        print(f"Missing Load Factor for Dew Point Demand Dryer", file=sys.stderr)
        sys.exit(1)
    
    operational_factor = acfm / capacity_scfm

    avg_kw = full_load_kw * (load_factor / 100) * operational_factor

    return avg_kw

def calculate_dryer(report_json, baseline_operation_7_1, dev):
    try:
        dryer_ids = report_json["response"]["dryer"]
    except:
        print(f"No Dryers?", file=sys.stderr)
        sys.exit(1)

    kws = []
    demand_kws = []

    for dryer_id in dryer_ids:
        dryer_json = requests_util.get_req("dryer", dryer_id, dev)
        try:
            connected_to = dryer_json["response"]["connected_to"]
            full_load_kw = dryer_json["response"]["full_load_kw"]
            demand_kws.append(full_load_kw)
            capacity_scfm = dryer_json["response"]["capacity_scfm"]

            type = dryer_json["response"]["type_if_desiccant_dryer"]
            control = dryer_json["response"]["control"]
        except:
            print(f"Missing some dryer data make sure all the fields are filled out plz", file=sys.stderr)
            sys.exit(1)
        
        ac_ids, ac_idxs = get_ac_ids_for_dryer(report_json, connected_to, dev)

        report_id = report_json["response"]["_id"]

        # Get kW
        if control == "Cycling":
            # df = get_cfm_df(report_json, ac_ids, dev)
            df = data_crunch_util.get_report_data_crunch(report_id, "data_crunch_trim_exclu", dev)
            df = data_crunch_util.filter_df_to_ac_idx(df, ac_idxs)
            df[f"Kilowatts"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm, dryer_json))
            kw = df["Kilowatts"].mean()

        elif control == "Non-Cycling":
            kw = full_load_kw

        elif control == "Timed":
            kw = timed_kw_calc(dryer_json, full_load_kw)

        elif control == "Dew Point Demand":
            # df = get_cfm_df(report_json, ac_ids, dev)
            df = data_crunch_util.get_report_data_crunch(report_id, "data_crunch_trim_exclu", dev)
            df = data_crunch_util.filter_df_to_ac_idx(df, ac_idxs)
            df[f"Kilowatts"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: dpd_kw_calc(acfm, full_load_kw, capacity_scfm, dryer_json))
            kw = df["Kilowatts"].mean()

        kws.append(kw)
        
        # get cfm_loss
        if control == "Dew Point Demand":
            # df = get_cfm_df(report_json, ac_ids, dev)
            df = data_crunch_util.get_report_data_crunch(report_id, "data_crunch_trim_exclu", dev)
            df = data_crunch_util.filter_df_to_ac_idx(df, ac_idxs)
            df[f"CFM Loss"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: get_cfm_loss_dpd(acfm, capacity_scfm, type))
            cfm_loss = df["CFM Loss"].mean()
        else:
            cfm_loss = get_dryer_cfm_loss(capacity_scfm, type)
        
        requests_util.patch_req("dryer", dryer_id, body={"scfm_dryer_loss": cfm_loss}, dev=dev)

    total_kw = sum(kws)

    total_demand_kw = sum(demand_kws)

    row_id = calculate_dryer_row(report_json, baseline_operation_7_1, total_kw, total_demand_kw, dev)

    return row_id


def start_calculations(operation_period_ids, demand_schedule_id, report_json, baseline_operation_7_1, dev):

    # df = df_calcs(report_json, dev)

    row_ids = []

    for operation_period_id in operation_period_ids:
        op_json = requests_util.get_req("operation_period", operation_period_id, dev)
        
        row_id = calculate_row(report_json, demand_schedule_id, operation_period_id, op_json, baseline_operation_7_1, dev)
        row_ids.append(row_id)

    row_id = calculate_dryer(report_json, baseline_operation_7_1, dev)
    row_ids.append(row_id)

    patch_response = requests_util.patch_req("baseline_operation_7_1", baseline_operation_7_1, body={"baseline_operation_7_1_row": row_ids}, dev=dev)
    print(f"PATCH REQ RESPONSE: {patch_response}")


def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    # local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    # data = json.loads(data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data.get('report_id')
    report_json = requests_util.get_req("Report", report_id, dev)

    # Make sure we have everything we need before running
    on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id = check_dependencies(report_id, report_json, dev)

    # Delete any existing rows
    baseline_operation_7_1 = reset_rows(report_id, report_json, dev)

    # Run Calculations for each Operation Period
    baseline_proposed_7_1_util.start_calculations(operation_period_ids, demand_schedule_id, report_json, baseline_operation_7_1, dev)



start()


