import sys
import json
import requests
import common_functions
import pandas as pd
import base64

def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    # data = json.loads(local_data)
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
    if "air_compressor" in report_json["response"] and report_json["response"]["air_compressor"] != []:
        ac_ids = report_json["response"]["air_compressor"]
    else:
        common_functions.patch_req("Report", report_id, body={"loading": f"Unable to find any Air Compressors! You need at least one Air Compressor for this Chart.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    master_df = None
    cfms = []
    for idx, ac in enumerate(ac_ids):
        ac_json = common_functions.get_req("air_compressor", ac, dev)
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor ID: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Reading {ac_name}.csv...", "is_loading_error": "no"}, dev=dev)

        if "ac_data_logger" in ac_json["response"] and ac_json["response"]["ac_data_logger"] != []:
            ac_data_logger_id = ac_json["response"]["ac_data_logger"]
            ac_data_logger_json = common_functions.get_req("ac_data_logger", ac_data_logger_id, dev)
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
        
        df = common_functions.calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id)

        # if control == "OLOL":
        #     if "threshold-value" in ac_json["response"]:
        #         threshold = ac_json["response"]["threshold-value"]
        #     else:
        #         common_functions.patch_req("Report", report_id, body={"loading": f"Missing Threshold Value! This is needed for ACFM calculations on OLOL control types. Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        #         sys.exit()
        #     df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_olol_acfm(amps, threshold, cfm))
        # elif control == "VFD":
        #     slope, intercept = common_functions.calculate_slope_intercept(report_id, ac_json, cfm, volts, dev)
        #     df[f"ACFM{idx+1}"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_vfd_acfm(amps, slope, intercept))
        
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
    
    if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Trimming the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = common_functions.trim_df(report_json, master_df, dev)

    if "exclusion" in report_json["response"]:
        common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Removing Exclusions from the dataset...", "is_loading_error": "no"}, dev=dev)
        master_df = common_functions.exclude_from_df(master_df, report_json, dev)

    if "operation_period" in report_json["response"] and report_json["response"]["operation_period"] != []:
        op_per_type = report_json["response"]["operating_period_type"]
        
        operating_period_ids = report_json["response"]["operation_period"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Found {len(operating_period_ids)} Operating Period{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Operating Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    

    if op_per_type == "Daily":

        for operating_period_id in operating_period_ids:
            operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
            try:
                operating_period_name = operating_period_json["response"]["Name"]
            except:
                operating_period_name = ''
                
            common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Data_Crunch_{operating_period_name}.csv...", "is_loading_error": "no"}, dev=dev)
            period_data = common_functions.daily_operating_period(master_df, operating_period_id, dev)

            file_name = f"Data_Crunch_{common_functions.sanitize_filename(f'{operating_period_name}_{operating_period_id}')}.csv"

            csv_data = period_data.to_csv(index=False)
            base64_encoded_data = base64.b64encode(csv_data.encode()).decode()

            body = {
                "file": {
                    "filename": file_name,
                    "contents": base64_encoded_data,
                    "private": False
                    }
                }

            url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/operation_period/{operating_period_id}"

            headers = {
                "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1"
            }

            try:
                response = requests.patch(url, json=body, headers=headers)
                print(f"patched: {file_name}, {response.status_code}")
                print(response.text)
            except requests.RequestException as e:
                print(e)

            # common_functions.patch_req("operation_period", operating_period_id, body={"data-crunch": f"https://www.pythonanywhere.com/user/jredgrift/files/home/jredgrift/inflow-report-builder/src/Data_Crunch_{common_functions.sanitize_filename(f'{operating_period_name}_{operating_period_id}')}.csv"}, dev=dev)
    elif op_per_type == "Weekly":

        for operating_period_id in operating_period_ids:
            operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
            try:
                operating_period_name = operating_period_json["response"]["Name"]
            except:
                operating_period_name = ''
            
            common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Data_Crunch_{operating_period_name}.csv...", "is_loading_error": "no"}, dev=dev)
            file_name = f"Data_Crunch_{common_functions.sanitize_filename(f'{operating_period_name}_{operating_period_id}')}.csv"
                
            period_data = common_functions.weekly_operating_period(master_df, operating_period_id, dev) # see def for explanation
            

            csv_data = period_data.to_csv(index=False)
            base64_encoded_data = base64.b64encode(csv_data.encode()).decode()

            body = {
                "file": {
                    "filename": file_name,
                    "contents": base64_encoded_data,
                    "private": False
                    }
                }

            url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/operation_period/{operating_period_id}"

            headers = {
                "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1"
            }

            try:
                response = requests.patch(url, json=body, headers=headers)
                print(f"patched: {file_name}, {response.status_code}")
                print(response.text)
            except requests.RequestException as e:
                print(e)
    elif op_per_type == "Experimental":
        for operating_period_id in operating_period_ids:
            operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)

            mins = common_functions.minutes_between_experimental(operating_period_id, dev)

            try:
                operating_period_name = operating_period_json["response"]["Name"]
            except:
                operating_period_name = ''
            
            common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Data_Crunch_{operating_period_name}.csv...", "is_loading_error": "no"}, dev=dev)
            file_name = f"Data_Crunch_{common_functions.sanitize_filename(f'{operating_period_name}_{operating_period_id}')}.csv"
                
            period_data = common_functions.experimental_operating_period(master_df, operating_period_id, dev)
            

            csv_data = period_data.to_csv(index=False)
            base64_encoded_data = base64.b64encode(csv_data.encode()).decode()

            body = {
                "file": {
                    "filename": file_name,
                    "contents": base64_encoded_data,
                    "private": False
                    },
                "Hours/yr": mins
                }

            url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/operation_period/{operating_period_id}"

            headers = {
                "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1"
            }

            try:
                response = requests.patch(url, json=body, headers=headers)
                print(f"patched: {file_name}, {response.status_code}")
                print(response.text)
            except requests.RequestException as e:
                print(e)
    
    common_functions.patch_req("Report", report_id, body={"loading": f"Building Data Crunch: Success!", "is_loading_error": "no"}, dev=dev)
            


start()