import sys
import json
import requests
import common_functions
import pandas as pd

def start():
    # data = json.loads(sys.argv[1]) # Proper Code. Keep this
    local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    data = json.loads(local_data)
    print(data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''
    report_id = data.get('report-id')
    compile_master_df(report_id, dev)
    

def compile_master_df(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    if "Air Compressor" in report_json["response"] and report_json["response"]["Air Compressor"] != []:
        ac_ids = report_json["response"]["Air Compressor"]
    else:
        common_functions.patch_req("Report", report_id, body={"loading": f"Unable to find any Air Compressors! You need at least one Air Compressor for this Chart.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    master_df = None
    cfms = []
    for idx, ac in enumerate(ac_ids):
        ac_json = common_functions.get_req("Air-Compressor", ac, dev)
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor ID: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Reading {ac_name}.csv...", "is_loading_error": "no"}, dev=dev)

        if "AC-Data-Logger" in ac_json["response"] and ac_json["response"]["AC-Data-Logger"] != []:
            ac_data_logger_id = ac_json["response"]["AC-Data-Logger"]
            ac_data_logger_json = common_functions.get_req("AC-Data-Logger", ac_data_logger_id, dev)
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        if "CSV" in ac_data_logger_json["response"]:
            csv_url = ac_data_logger_json["response"]["CSV"]
            csv_url = f"https:{csv_url}"
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Data Logger! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        df = common_functions.csv_to_df(csv_url)

        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: {ac_name}: Kilowatts{idx+1} Column...", "is_loading_error": "no"}, dev=dev)
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

        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: {ac_name}: ACFM{idx+1} Column...", "is_loading_error": "no"}, dev=dev)
        # Create ACFM Column

        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Control Type! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "CFM" in ac_json["response"]:
            cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
            cfms.append(cfm)
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        if control == "OLOL":
            if "threshold-value" in ac_json["response"]:
                threshold = ac_json["response"]["threshold-value"]
            else:
                common_functions.patch_req("Report", report_id, body={"loading": f"Missing Threshold Value! This is needed for ACFM calculations on OLOL control types. Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()
            df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_olol_acfm(amps, threshold, cfm))
        elif control == "VFD":
            slope, intercept = common_functions.calculate_slope_intercept(report_id, ac_json, cfm, volts, dev)
            df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_vfd_acfm(amps, slope, intercept))
        
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
            common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Merging with other CSVs...", "is_loading_error": "no"}, dev=dev)
            print("Merged next Dataframe with master_df")
    
    if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = common_functions.trim_df(report_json, master_df)

    if "exclusion" in report_json["response"]:
        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Removing Exclusiong from the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = common_functions.exclude_from_df(master_df, report_json, dev)

    if "Operation Period" in report_json["response"] and report_json["response"]["Operation Period"] != []:
        op_per_type = report_json["response"]["operating_period_type"]
        
        operating_period_ids = report_json["response"]["Operation Period"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Found {len(operating_period_ids)} Operating Period{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Operating Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    

    if op_per_type == "Daily":

        for operating_period_id in operating_period_ids:
            operating_period_json = common_functions.get_req("Operation-Period", operating_period_id, dev)
            operating_period_name = operating_period_json["response"]["Name"]
            common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Data_Crunch_{operating_period_name}.csv...", "is_loading_error": "no"}, dev=dev)
            period_data = common_functions.daily_operating_period(master_df, operating_period_id, dev)

            period_data.to_csv(f"Data_Crunch_{operating_period_name}_{operating_period_id}.csv")

            common_functions.patch_req("Operation-Period", operating_period_id, body={"data-crunch": f"https://www.pythonanywhere.com/user/jredgrift/files/home/jredgrift/inflow-report-builder/src/routes/Data_Crunch_{operating_period_name}_{operating_period_id}.csv"}, dev=dev)
    elif op_per_type == "Weekly":

        for operating_period_id in operating_period_ids:
            operating_period_json = common_functions.get_req("Operation Period", operating_period_id, dev)
            operating_period_name = operating_period_json["response"]["Name"]
            common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Data_Crunch_{operating_period_name}.csv...", "is_loading_error": "no"}, dev=dev)
            period_data = common_functions.weekly_operating_period(master_df, operating_period_id, dev) # see def for explanation

            period_data.to_csv(f"Data_Crunch{operating_period_name}_{operating_period_id}.csv")

            common_functions.patch_req("Operation-Period", operating_period_id, body={"data-crunch": f"https://www.pythonanywhere.com/user/jredgrift/files/home/jredgrift/inflow-report-builder/src/routes/Data_Crunch_{operating_period_name}_{operating_period_id}.csv"}, dev=dev)
    
    common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Success!", "is_loading_error": "no"}, dev=dev)
            


start()