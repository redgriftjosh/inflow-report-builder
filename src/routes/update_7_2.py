import sys
import json
import common_functions
import reset_dataset_7_2
from utilities import data_crunch_util, compressor_util, requests_util
# import common_functions 


def calculate_values(df, operating_period_id, report_json, dev):
    ac_ids = report_json["response"]["air_compressor"]
    for idx, ac in enumerate(ac_ids):
        ac_json = requests_util.get_req("air_compressor", ac, dev)

        # Get the Name
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            print(f"Missing Name! Air Compressor ID: {ac}", file=sys.stderr)
            sys.exit(1)

        # Get the Control Type
        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            print(f"Missing Control Type! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)

        # Get the CFM
        cfm = compressor_util.get_cfm(control, ac_json, ac_name, dev)

        avg_kilowatts = df[f"Kilowatts{idx+1}"].mean()
        acfm = df[f"ACFM{idx+1}"].mean()
        flow_percent = (acfm/cfm) * 100

        peak_15_acfm_index = df['15_Min_Avg_Flow'].idxmax() # Get the index of the max TOTAL peak 15 minute average flow
        peak_15_acfm = df.at[peak_15_acfm_index, f"15_Min_Avg_Flow_AC{idx+1}"]
        peak_15_kw_index = df['15_Min_Avg_kW'].idxmax() # Get the index of the max TOTAL peak 15 minute average kW
        peak_15_kw = df.at[peak_15_acfm_index, f"15_Min_Avg_kW_AC{idx+1}"]
        peak_15_flow_percent = (peak_15_acfm/cfm) * 100

        peak_2_acfm_index = df['2_Min_Avg_Flow'].idxmax() # Get the index of the max TOTAL peak 15 minute average flow
        peak_2_acfm = df.at[peak_2_acfm_index, f"2_Min_Avg_Flow_AC{idx+1}"]
        peak_2_kw_index = df['2_Min_Avg_kW'].idxmax() # Get the index of the max TOTAL peak 15 minute average kW
        peak_2_kw = df.at[peak_2_kw_index, f"2_Min_Avg_kW_AC{idx+1}"]
        peak_2_flow_percent = (peak_2_acfm/cfm) * 100
        print("")
        print(f"peak_15_acfm: {peak_15_acfm}")
        print(f"cfm: {cfm}")
        print(f"peak_15_flow_percent: {peak_15_flow_percent}")
        print("")
        print(f"AC{idx+1}")
        print(f"peak_15_acfm_index: {peak_15_acfm_index}")
        print(f"peak_15_kw_index: {peak_15_kw_index}")

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
        
        # print(f"body: {body}")
        # Send the patch to the dataset linked to the right air compressor 
        operating_period_json = requests_util.get_req("operation_period", operating_period_id, dev)
        dataset_ids = operating_period_json["response"]["dataset_7_2"]
        for dataset_id in dataset_ids:
            dataset_json = requests_util.get_req("dataset_7_2", dataset_id, dev)
            if dataset_json["response"]["air_compressor"] == ac:
                requests_util.patch_req("dataset_7_2", dataset_id, body, dev)


def loop_through_operating_periods(report_id, report_json, dev):
    if "operation_period" in report_json["response"] and report_json["response"]["operation_period"] != []:
        operating_period_ids = report_json["response"]["operation_period"]
        requests_util.patch_req("Report", report_id, body={"loading": f"Found {len(operating_period_ids)} Operating Period{'s' if len(operating_period_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        print("No Operating Periods Found! You need at least one Operating Period.", file=sys.stderr)
        sys.exit(1)
    

    for operating_period_id in operating_period_ids:
        print(f"operating_period_id: {operating_period_id}")
        df = data_crunch_util.get_op_data_crunch(operating_period_id, dev)
        print("It's a miracle!")
        
        calculate_values(df, operating_period_id, report_json, dev)

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
    report_json = requests_util.get_req("Report", report_id, dev)
    requests_util.patch_req("Report", report_id, body={"loading": "Making sure your charts are set up to display all the data...", "is_loading_error": "no"}, dev=dev)
    reset_dataset_7_2.start(report_id, report_json, dev)
    loop_through_operating_periods(report_id, report_json, dev)
    requests_util.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)

if __name__ == "__main__":
    start()
