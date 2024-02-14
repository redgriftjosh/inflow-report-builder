import sys
import json
import common_functions
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Make sure we have everything we need before running
def check_dependencies(report_id, report_json, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Checking Dependencies...", "is_loading_error": "no"}, dev=dev)

    # Checking if we have at least one operation period
    try:
        operation_period_ids = report_json["response"]["operation_period"]
    except:
        print(f"No Operating Periods found! You need at least on operation period...", file=sys.stderr)
        sys.exit(1)

    # Checking if we have the necessary data from section 3.2
    try:
        peak_acfm_15 = report_json["response"]["15 Min Peak Flow"]
        kw_max_avg_15 = report_json["response"]["kw_max_avg_15"]
    except:
        print(f"You'll need to run Section 3.2 before you run this one...", file=sys.stderr)
        sys.exit(1)
    
    # Checking if we have electrical utility providers entered
    try:
        electrical_provider = report_json["response"]["electrical_provider"]

        electrical_provider_json = common_functions.get_req("electrical_provider", electrical_provider, dev)
        on_peak_start = electrical_provider_json["response"]["on_peak_start"]
        off_peak_start = electrical_provider_json["response"]["off_peak_start"]

        electrical_provider_entrys = electrical_provider_json["response"]["electrical_provider_entry"]

    except:
        print(f"You'll need to run Section 3.2 before you run this one...", file=sys.stderr)
        sys.exit(1)
    
    baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)

    demand_schedule_id = baseline_operation_7_1_json["response"]["demand_schedule_id"]
    # try:
    # except Exception as e:
    #     print(f"Please Select an Operation Period to define the Demand calculations...{e}", file=sys.stderr)
    #     sys.exit(1)

    
    return on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id, kw_max_avg_15
    

def create_first_baseline_operation_7_1(report_id, dev):
    response = common_functions.post_req("baseline_operation_7_1", body={"report": report_id}, dev=dev)
    baseline_operation_7_1 = response["id"]

    common_functions.patch_req("report", report_id, body={"baseline_operation_7_1": baseline_operation_7_1}, dev=dev)
    
    return baseline_operation_7_1

def reset_rows(report_id, report_json, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Resetting Any Existing Data...", "is_loading_error": "no"}, dev=dev)

    try:
        baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]

    except:
        baseline_operation_7_1 = create_first_baseline_operation_7_1(report_id, dev)
    
    # Deleting any rows if they exist
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)
    try:
        baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

        for row in baseline_operation_7_1_rows:
            common_functions.del_req("baseline_operation_7_1_row", row, dev)
    except:
        print(f"No Rows Found, I guess")

    common_functions.patch_req("Report", report_id, body={"loading": f"Getting started on the Calculations...", "is_loading_error": "no"}, dev=dev)

    return baseline_operation_7_1

def get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id, op_id, dev):
    try:
        elec_provider_id = report_json["response"]["electrical_provider"]
    except:
        print(f"Can't find any Electrical Utility info!", file=sys.stderr)
        sys.exit(1)
    elec_provider_json = common_functions.get_req("electrical_provider", elec_provider_id, dev)
    elec_entry_ids = elec_provider_json["response"]["electrical_provider_entry"]

    on_peak_list = []

    kwh_on_peak_list = []
    kwh_off_peak_list = []

    for elec_entry_id in elec_entry_ids:
        elec_entry_json = common_functions.get_req("electrical_provider_entry", elec_entry_id, dev)
        month_start = datetime.strptime(elec_entry_json["response"]["month_start"], "%B").month
        month_end = datetime.strptime(elec_entry_json["response"]["month_end"], "%B").month
        kw_on_peak = elec_entry_json["response"]["kw_on_peak"]

        if month_start <= month_end:
            num_months = month_end - month_start + 1
        else:
            # If the start month is after the end month, it implies the end month is in the next year
            num_months = (12 - month_start) + month_end + 1
        
        on_peak = kw_demand_15min * kw_on_peak * num_months
            
        on_peak_list.append(on_peak)

        kwh_on_peak = elec_entry_json["response"]["kwh_on_peak"] * (num_months / 12)
        kwh_on_peak_list.append(kwh_on_peak)

        kwh_off_peak = elec_entry_json["response"]["kwh_off_peak"] * (num_months / 12)
        kwh_off_peak_list.append(kwh_off_peak)

    blended_on_peak = sum(kwh_on_peak_list)
    blended_off_peak = sum(kwh_off_peak_list)

    on_peak_start = datetime.strptime(elec_provider_json["response"]["on_peak_start"], '%I:%M %p').time()
    off_peak_start = datetime.strptime(elec_provider_json["response"]["off_peak_start"], '%I:%M %p').time()

    # Create datetime objects by combining the time with today's date
    today = datetime.today().date()
    on_peak_start_dt = datetime.combine(today, on_peak_start)
    off_peak_start_dt = datetime.combine(today, off_peak_start)

    # If off_peak_start is the next day
    if off_peak_start < on_peak_start:
        off_peak_start_dt += timedelta(days=1)

    # Calculate the difference between the two datetime objects
    on_peak_seconds = (off_peak_start_dt - on_peak_start_dt).total_seconds()

    on_peak_days = on_peak_seconds / (24 * 60 * 60)

    if op_id == demand_schedule_id or demand_schedule_id == "Dryers":
        cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
    else:
        cost_to_operate = (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))

    return cost_to_operate

def get_pressure_index(report_id, op_json, dev):
    report_json = common_functions.get_req("Report", report_id, dev)
    baseline_operation_7_1_id = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1_id, dev)

    try:
        p_what = baseline_operation_7_1_json["response"]["p_what"]
    except:
        print(f"No Pressure Selected...", file=sys.stderr)
        sys.exit(1)
    
    try:
        i = int(p_what.replace("P", ""))-1
        pressure = op_json["response"]["P2"][i]
        return pressure
    except:
        common_functions.patch_req("Report", report_id, body={"loading": "Found a Pressure Log but couldn't work with the name. Make sure it's formatted exactly like P4", "is_loading_error": "no"}, dev=dev)
        print(f"Found a Pressure Log but couldn't work with the name. Make sure it's formatted exactly like: P4", file=sys.stderr)
        sys.exit(1)
    
def calculate_row(report_json, kw_demand_15min, demand_schedule_id, op_id, op_json, baseline_operation_7_1, dev):
    
    print(f"REPORT JSON: {report_json}")
    report_id = report_json["response"]["_id"]

    try:
        average_acfm = op_json["response"]["ACFM Made"]
        peak_15min_acfm = op_json["response"]["peak_15min_acfm"]
        average_kw_demand = op_json["response"]["kW"]
        hours_annual = op_json["response"]["Hours/yr"]
        kw_demand_15min = report_json["response"]["kw_max_avg_15"]

    except:
        print(f"Did you already run section 3.2? You need to if you haven't.", file=sys.stderr)
        sys.exit(1)


    pressure = get_pressure_index(report_id, op_json, dev)

    kwh_annual = average_kw_demand * hours_annual

    cost_to_operate = get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id, op_id, dev)

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

    response = common_functions.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def get_ac_ids_for_dryer(report_json, connected_to, dev):
    ac_ids = report_json["response"]["air_compressor"]

    connected_to_list = connected_to.split(", ")

    connected_ac_ids = []

    for ac_id in ac_ids:
        ac_json = common_functions.get_req("air_compressor", ac_id, dev)
        name = ac_json["response"]["Customer CA"]
        
        if name in connected_to_list:
            connected_ac_ids.append(ac_id)
    
    return connected_ac_ids

def get_cfm_df(report_json, ac_ids, dev):
    report_id = report_json["response"]["_id"]
    cfms = []
    master_df = None
    for idx, ac in enumerate(ac_ids):
        ac_json = common_functions.get_req("air_compressor", ac, dev)
        ac_name = ac_json["response"]["Customer CA"]

        if "ac_data_logger" in ac_json["response"] and ac_json["response"]["ac_data_logger"] != []:
            ac_data_logger_id = ac_json["response"]["ac_data_logger"]
            ac_data_logger_json = common_functions.get_req("ac_data_logger", ac_data_logger_id, dev)
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
        
        if control == "Fixed Speed - Variable Capacity":
            cfm = 1
        else:
            if "CFM" in ac_json["response"]:
                cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
                cfms.append(cfm)
            else:
                # patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()
        
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

def calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm):
    x = [(capacity_scfm*0.1), capacity_scfm]
    y = [(full_load_kw*0.55), full_load_kw]

    slope, intercept = np.polyfit(x, y, 1)

    return slope * acfm + intercept

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

def calculate_dryer_row(report_json, baseline_operation_7_1, kw, dev):
    
    kw_demand_15min = kw
    average_kw_demand = kw

    total_hours = report_json["response"]["total_hours"]

    kwh_annual = average_kw_demand * total_hours

    cost_to_operate = get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id="Dryers", op_id=None, dev=dev)

    label = "Dryers"

    body = {
        "average_kw_demand": average_kw_demand,
        "kw_demand_15min": kw_demand_15min,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate,
        "baseline_operation_7_1": baseline_operation_7_1,
        "label": label
    }

    response = common_functions.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def calculate_dryer(report_json, baseline_operation_7_1, dev):
    try:
        dryer_ids = report_json["response"]["dryer"]
    except:
        print(f"No Dryers?", file=sys.stderr)
        sys.exit(1)

    kws = []

    for dryer_id in dryer_ids:
        dryer_json = common_functions.get_req("dryer", dryer_id, dev)
        try:
            connected_to = dryer_json["response"]["connected_to"]
            full_load_kw = dryer_json["response"]["full_load_kw"]
            capacity_scfm = dryer_json["response"]["capacity_scfm"]

            type = dryer_json["response"]["type_if_desiccant_dryer"]
            control = dryer_json["response"]["control"]
        except:
            print(f"Missing some dryer data make sure all the fields are filled out plz", file=sys.stderr)
            sys.exit(1)

        ac_ids = get_ac_ids_for_dryer(report_json, connected_to, dev)

        if control == "Cycling":
            df = get_cfm_df(report_json, ac_ids, dev)
            df[f"Kilowatts"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm))
            kw = df["Kilowatts"].mean()
        else:
            kw = full_load_kw
        kws.append(kw)


        cfm_loss = get_dryer_cfm_loss(capacity_scfm, type)
        
        common_functions.patch_req("dryer", dryer_id, body={"scfm_dryer_loss": cfm_loss}, dev=dev)

    total_kw = sum(kws)

    row_id = calculate_dryer_row(report_json, baseline_operation_7_1, total_kw, dev)

    return row_id


def start_calculations(operation_period_ids, demand_schedule_id, report_json, kw_demand_15min, baseline_operation_7_1, dev):

    row_ids = []

    for operation_period_id in operation_period_ids:
        op_json = common_functions.get_req("operation_period", operation_period_id, dev)
        
        row_id = calculate_row(report_json, kw_demand_15min, demand_schedule_id, operation_period_id, op_json, baseline_operation_7_1, dev)
        row_ids.append(row_id)

    row_id = calculate_dryer(report_json, baseline_operation_7_1, dev)
    row_ids.append(row_id)

    patch_response = common_functions.patch_req("baseline_operation_7_1", baseline_operation_7_1, body={"baseline_operation_7_1_row": row_ids}, dev=dev)
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
    report_json = common_functions.get_req("Report", report_id, dev)

    # Make sure we have everything we need before running
    on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id, kw_demand_15min = check_dependencies(report_id, report_json, dev)

    # Delete any existing rows
    baseline_operation_7_1 = reset_rows(report_id, report_json, dev)

    # Run Calculations for each Operation Period
    start_calculations(operation_period_ids, demand_schedule_id, report_json, kw_demand_15min, baseline_operation_7_1, dev)



start()


