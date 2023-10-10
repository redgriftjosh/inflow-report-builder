import sys
import json
import requests
import common_functions
import reset_dataset_7_2
import pandas as pd

def check_datasets(report_id, report_json, dev):
    if "Air Compressor" in report_json["response"]:
        ac_ids = report_json["response"]["Air Compressor"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Found {len(ac_ids)} Air Compressor{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Air Compressors Found! You need at least one Air Compressor.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    if "Operation Period" in report_json["response"]:
        op_per_type = report_json["response"]["operating_period_type"]
        
        operating_period_ids = report_json["response"]["Operation Period"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Found {len(operating_period_ids)} Operating Period{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Operating Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()


    for ac in ac_ids:
        # Get the Air Compressor into a DataFrame
        ac_json = common_functions.get_req("Air-Compressor", ac, dev)
        if "AC-Data-Logger" in ac_json["response"]:
            ac_data_logger_id = ac_json["response"]["AC-Data-Logger"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing data loggers! Make sure each Air Compressor has a Properly Formatted CSV uploaded. Air Compressor ID: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        ac_data_logger_json = common_functions.get_req("AC-Data-Logger", ac_data_logger_id, dev)

        csv_url = ac_data_logger_json["response"]["CSV"]
        csv_url = f"https:{csv_url}"

        df = common_functions.csv_to_df(csv_url)

        # Trim & Exclude specified data
        if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
            df = common_functions.trim_df(report_json, df)

        if "exclusion" in report_json["response"]:
            df = common_functions.exclude_from_df(df, report_json, dev)
        
        # Create Kilowatts column
        volts = ac_json["response"]["volts"]
        pf50 = ac_json["response"]["pf if fifty"]
        pf = ac_json["response"]["pf"]
        amppf = ac_json["response"]["amps less pf"]
        bhp = ac_json["response"]["BHP"]
        
        df["Kilowatts"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf))
    
        # Create ACFM Column
        control = ac_json["response"]["Control Type"]
        cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        if control == "OLOL":
            threshold = ac_json["response"]["threshold-value"]
            df["ACFM"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_olol_acfm(amps, threshold, cfm))
        elif control == "VFD":
            slope, intercept = common_functions.calculate_slope_intercept(ac_json, cfm, volts, dev)
            df["ACFM"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_vfd_acfm(amps, slope, intercept))

        if op_per_type == "Daily":

            for operating_period_id in operating_period_ids:
                period_data = common_functions.daily_operating_period(df, operating_period_id, dev) # Filter dataframe to operating period

                dataset_7_2_calculations(period_data, operating_period_id, ac, cfm, dev)

        elif op_per_type == "Weekly":

            for operating_period_id in operating_period_ids:
                
                # get the average kw for this operating period
                period_data = common_functions.weekly_operating_period(df, operating_period_id, dev) # Filter dataframe to operating period

                dataset_7_2_calculations(period_data, operating_period_id, ac, cfm, dev)

def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    # local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    # data = json.loads(data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data.get('report-id')
    report_json = common_functions.get_req("Report", report_id, dev)
    common_functions.patch_req("Report", report_id, body={"loading": "Making sure your charts are set up to display all the data...", "is_loading_error": "no"}, dev=dev)
    reset_dataset_7_2.start(report_id, report_json, dev)
    get_average_kw(report_id, report_json, dev)

def dataset_7_2_calculations(idx, report_id, period_data, operating_period_id, ac, cfm, dev):
    operating_period_json = common_functions.get_req("Operation-Period", operating_period_id, dev)
    if "Name" in operating_period_json["response"]:    
        op_name =  operating_period_json["response"]["Name"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Populating {op_name}...", "is_loading_error": "no"}, dev=dev)
    
    # For entire Operating Period
    avg_kilowatts = period_data["Kilowatts"].mean() # get the average kw for this operating period

    acfm = period_data["ACFM"].mean() # get the average acfm for this operating period

    flow_percent = (acfm/cfm) * 100

    # For 15 min peaks
    peak_15_kw = period_data["Kilowatts"][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
    peak_15_acfm = period_data["ACFM"][::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
    peak_15_flow_percent = (peak_15_acfm/cfm) * 100

    # For 2 min peaks
    peak_2_kw = period_data["Kilowatts"][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
    peak_2_acfm = period_data["ACFM"][::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
    peak_2_flow_percent = (peak_2_acfm/cfm) * 100

    # ready for webhook
    body = {
        "kw": avg_kilowatts,
        "acfm": acfm,
        "flow-percent": flow_percent,
        "peak-15-kw": peak_15_kw,
        "peak-15-acfm": peak_15_acfm,
        "peak-15-flow-percent": peak_15_flow_percent,
        "peak-2-kw": peak_2_kw,
        "peak-2-acfm": peak_2_acfm,
        "peak-2-flow-percent": peak_2_flow_percent
        }

    # Send the patch to the dataset linked to the right air compressor 
    operating_period_json = common_functions.get_req("Operation-Period", operating_period_id, dev)
    dataset_ids = operating_period_json["response"]["dataset-7-2"]
    for dataset_id in dataset_ids:
        dataset_json = common_functions.get_req("dataset-7-2", dataset_id, dev)
        if dataset_json["response"]["air-compressor"] == ac:
            common_functions.patch_req("dataset-7-2", dataset_id, body, dev)

def get_average_kw(report_id, report_json, dev):
    if "Air Compressor" in report_json["response"] and report_json["response"]["Air Compressor"] != []:
        ac_ids = report_json["response"]["Air Compressor"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Found {len(ac_ids)} Air Compressor{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Air Compressors Found! You need at least one Air Compressor.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    if "Operation Period" in report_json["response"] and report_json["response"]["Operation Period"] != []:
        op_per_type = report_json["response"]["operating_period_type"]
        
        operating_period_ids = report_json["response"]["Operation Period"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Found {len(operating_period_ids)} Operating Period{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Operating Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    for idx, ac in enumerate(ac_ids):
        common_functions.patch_req("Report", report_id, body={"loading": f"Starting on Air Compressor {idx + 1}...", "is_loading_error": "no"}, dev=dev)
        
        
        # Get the Air Compressor into a DataFrame
        ac_json = common_functions.get_req("Air-Compressor", ac, dev)
        if "AC-Data-Logger" in ac_json["response"]:
            ac_data_logger_id = ac_json["response"]["AC-Data-Logger"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing data loggers! Make sure each Air Compressor has a Properly Formatted CSV uploaded. Air Compressor: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        ac_data_logger_json = common_functions.get_req("AC-Data-Logger", ac_data_logger_id, dev)
        
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor ID: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Reading CSV...", "is_loading_error": "no"}, dev=dev)
        csv_url = ac_data_logger_json["response"]["CSV"]
        csv_url = f"https:{csv_url}"

        df = common_functions.csv_to_df(csv_url)

        # Trim & Exclude specified data
        if "trim-start" in report_json["response"] and "trim-end" in report_json["response"]:
            df = common_functions.trim_df(report_json, df)
            common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Trimming CSV...", "is_loading_error": "no"}, dev=dev)

        if "exclusion" in report_json["response"]:
            df = common_functions.exclude_from_df(df, report_json, dev)
            common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Excluding from CSV...", "is_loading_error": "no"}, dev=dev)
        
        common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Kilowatts Column...", "is_loading_error": "no"}, dev=dev)
        # Create Kilowatts column
        
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
        
        
        df["Kilowatts"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf))

        common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: ACFM Column...", "is_loading_error": "no"}, dev=dev)
        # Create ACFM Column

        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Control Type! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "CFM" in ac_json["response"]:
            cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if control == "OLOL":
            if "threshold-value" in ac_json["response"]:
                threshold = ac_json["response"]["threshold-value"]
            else:
                common_functions.patch_req("Report", report_id, body={"loading": f"Missing Threshold Value! This is needed for ACFM calculations on OLOL control types. Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()
            df["ACFM"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_olol_acfm(amps, threshold, cfm))
        elif control == "VFD":
            slope, intercept = common_functions.calculate_slope_intercept(report_id, ac_json, cfm, volts, dev)
            df["ACFM"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_vfd_acfm(amps, slope, intercept))

        if op_per_type == "Daily":

            for operating_period_id in operating_period_ids:
                period_data = common_functions.daily_operating_period(df, operating_period_id, dev) # Filter dataframe to operating period

                dataset_7_2_calculations(idx, report_id, period_data, operating_period_id, ac, cfm, dev)

        elif op_per_type == "Weekly":

            for operating_period_id in operating_period_ids:
                
                # get the average kw for this operating period
                period_data = common_functions.weekly_operating_period(df, operating_period_id, dev) # Filter dataframe to operating period

                dataset_7_2_calculations(idx, report_id, period_data, operating_period_id, ac, cfm, dev)
    common_functions.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)
start()
    
    