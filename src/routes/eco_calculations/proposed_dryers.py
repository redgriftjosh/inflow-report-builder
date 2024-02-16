import os
import sys
import json
import proposed_global
import pandas as pd
import numpy as np

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import common_functions

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

    try:
        scenario_id = data["scenario_id"]
    except:
        print(f"Can't find variable: scenario_id", file=sys.stderr)
        sys.exit(1)

    return dev, report_id, scenario_id

def create_new_scenario_difference(op_id, dev):
    response = common_functions.post_req("scenario_differences", body={"operation_period": op_id}, dev=dev)

    scenario_difference = response["id"]

    common_functions.patch_req("operation_period", op_id, body={"scenario_differences": scenario_difference}, dev=dev)

    return scenario_difference

def get_total_report_dryer_cfm(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    dryer_ids = report_json["response"]["dryer"]

    adjusted_cfms = []
    for dryer_id in dryer_ids:
        dryer_json = common_functions.get_req("dryer", dryer_id, dev)
        adjusted_cfm = dryer_json["response"]["scfm_dryer_loss"]

        adjusted_cfms.append(adjusted_cfm)

    total_report_dryer_cfm = sum(adjusted_cfms)

    return total_report_dryer_cfm

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

def calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm):
    x = [(capacity_scfm*0.1), capacity_scfm]
    y = [(full_load_kw*0.55), full_load_kw]

    slope, intercept = np.polyfit(x, y, 1)

    return slope * acfm + intercept

def get_total_proposed_dryer_kw(report_id, scenario_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    dryer_ids = scenario_proposed_json["response"]["dryer"]

    kws = []
    for dryer_id in dryer_ids:
        dryer_json = common_functions.get_req("dryer", dryer_id, dev)

        connected_to = dryer_json["response"]["connected_to"]
        full_load_kw = dryer_json["response"]["full_load_kw"]
        capacity_scfm = dryer_json["response"]["capacity_scfm"]

        type = dryer_json["response"]["type_if_desiccant_dryer"]
        control = dryer_json["response"]["control"]

        ac_ids = get_ac_ids_for_dryer(report_json, connected_to, dev)

        if control == "Cycling":
            df = get_cfm_df(report_json, ac_ids, dev)
            df[f"Kilowatts"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm))
            kw = df["Kilowatts"].mean()
        else:
            kw = full_load_kw
        kws.append(kw)
    
    total_kw = sum(kws)

    return total_kw

def get_total_proposed_dryer_cfm(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    dryer_ids = scenario_proposed_json["response"]["dryer"]

    adjusted_cfms = []
    for dryer_id in dryer_ids:
        dryer_json = common_functions.get_req("dryer", dryer_id, dev)

        capacity_scfm = dryer_json["response"]["capacity_scfm"]
        type = dryer_json["response"]["type_if_desiccant_dryer"]

        cfm_loss = get_dryer_cfm_loss(capacity_scfm, type)

        adjusted_cfms.append(cfm_loss)
    
    total_proposed_dryer_cfm = sum(adjusted_cfms)

    return total_proposed_dryer_cfm

def get_op_ids(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)

    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    operating_period_ids = scenario_proposed_json["response"]["operation_period"]

    return operating_period_ids

def get_total_report_dryer_kw(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    dryer_ids = report_json["response"]["dryer"]

    kws = []
    for dryer_id in dryer_ids:
        dryer_json = common_functions.get_req("dryer", dryer_id, dev)

        connected_to = dryer_json["response"]["connected_to"]
        full_load_kw = dryer_json["response"]["full_load_kw"]
        capacity_scfm = dryer_json["response"]["capacity_scfm"]

        type = dryer_json["response"]["type_if_desiccant_dryer"]
        control = dryer_json["response"]["control"]

        ac_ids = get_ac_ids_for_dryer(report_json, connected_to, dev)

        if control == "Cycling":
            df = get_cfm_df(report_json, ac_ids, dev)
            df[f"Kilowatts"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm))
            kw = df["Kilowatts"].mean()
        else:
            kw = full_load_kw
        print(f"report_dryer_kw: {kw}")
        kws.append(kw)
    
    total_kw = sum(kws)

    return total_kw

def start():
    dev, report_id, scenario_id = get_payload()
    
    total_proposed_dryer_cfm = get_total_proposed_dryer_cfm(scenario_id, dev)
    total_report_dryer_cfm = get_total_report_dryer_cfm(report_id, dev)

    total_dryer_cfm = total_proposed_dryer_cfm - total_report_dryer_cfm


    total_proposed_dryer_kw = get_total_proposed_dryer_kw(report_id, scenario_id, dev)
    print(f"total_proposed_dryer_kw: {total_proposed_dryer_kw}")

    total_report_dryer_kw = get_total_report_dryer_kw(report_id, dev)
    print(f"total_report_dryer_kw: {total_report_dryer_kw}")

    total_dryer_kw = total_proposed_dryer_kw - total_report_dryer_kw
    print(f"total_dryer_kw: {total_dryer_kw}")


    operating_period_ids = get_op_ids(scenario_id, dev)

    for operating_period_id in operating_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        try:
            scenario_differences = operating_period_json["response"]["scenario_differences"]
        except:
            scenario_differences = create_new_scenario_difference(operating_period_id, dev)

        common_functions.patch_req("scenario_differences", scenario_differences, body={"dryer_cfm_change": total_dryer_cfm, "dryer_kw_change": total_dryer_kw}, dev=dev)

        proposed_global.update_op_stats(operating_period_id, report_id, dev)


start()
