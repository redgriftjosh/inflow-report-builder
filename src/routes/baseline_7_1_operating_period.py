# print("I ran")
import sys
import json
import common_functions
from datetime import datetime, timedelta

# print("All Good")
# sys.exit()

# Get's the operating period ID so you can pull data you need from it.
def get_op_id(report_id, operating_period_name, dev):
    report_json = common_functions.get_req("Report", report_id, dev)

    if "operation_period" in report_json["response"]:
        operating_period_ids = report_json["response"]["operation_period"]
        
        for operating_period_id in operating_period_ids:
            operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
            operating_period_name_temp = operating_period_json["response"]["Name"]
            
            if operating_period_name_temp == operating_period_name:
                focus_op_id = operating_period_id
                return focus_op_id
            
        common_functions.patch_req("Report", report_id, body={"loading": "I can't find that operating period for some reason...", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
                
    else:
        print(f"Error: No Operating Periods Found! You need at least one Operating Period.", file=sys.stderr)
        sys.exit(1)
        common_functions.patch_req("Report", report_id, body={"loading": "No Operating Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

def get_pressure_index(report_id, op_json, dev):
    report_json = common_functions.get_req("Report", report_id, dev)
    baseline_operation_7_1_id = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1_id, dev)

    try:
        p_what = baseline_operation_7_1_json["response"]["p_what"]
    except:
        common_functions.patch_req("Report", report_id, body={"loading": "No Pressure Selected gonna skip this part...", "is_loading_error": "no"}, dev=dev)
        return None
    
    try:
        i = int(p_what.replace("P", ""))-1
        pressure = op_json["response"]["P2"][i]
        return pressure
    except:
        common_functions.patch_req("Report", report_id, body={"loading": "Found a Pressure Log but couldn't work with the name. Make sure it's formatted exactly like P4", "is_loading_error": "no"}, dev=dev)
        return None

def calculate_cost_to_operate(report_json, kw_demand_15min, kwh_annual, dev):
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

    cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))

    return cost_to_operate


def get_body(op_id, report_id, dev):
    op_json = common_functions.get_req("operation_period", op_id, dev)

    report_json = common_functions.get_req("Report", report_id, dev)
    peak_15min_acfm = report_json["response"]["15 Min Peak Flow"]

    try:
        average_acfm = op_json["response"]["ACFM Made"]
    except:
        print(f"I'm looking for Averaeg ACFM Made from section 3.2 but can't seem to find it... Did you already run section 3.2? You need to if you haven't.", file=sys.stderr)
        sys.exit(1)

    pressure = get_pressure_index(report_id, op_json, dev)

    hours_annual = op_json["response"]["Hours/yr"]

    average_kw_demand = op_json["response"]["kW"]

    kw_demand_15min = report_json["response"]["kw_max_avg_15"]

    kwh_annual = average_kw_demand * hours_annual
    
    common_functions.patch_req("Report", report_id, body={"loading": f"Calculating Cost To Operate...", "is_loading_error": "no"}, dev=dev)
    cost_to_operate = calculate_cost_to_operate(report_json, kw_demand_15min, kwh_annual, dev)

    body = {
        "peak_15min_acfm": peak_15min_acfm,
        "average_acfm": average_acfm,
        "pressure": pressure,
        "hours_annual": hours_annual,
        "average_kw_demand": average_kw_demand,
        "kw_demand_15min": kw_demand_15min,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate
    }
    return body


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

    operating_period_name = data.get('operating_period_name')
    if operating_period_name == "":
        print(f"Please Enter an Operating Period.", file=sys.stderr)
        sys.exit(1)

    baseline_operation_7_1_row_id = data.get('baseline_operation_7_1_row_id')

    common_functions.patch_req("Report", report_id, body={"loading": f"Getting Data From {operating_period_name}...", "is_loading_error": "no"}, dev=dev)
    op_id = get_op_id(report_id, operating_period_name, dev)

    body = get_body(op_id, report_id, dev)
    body["label"] = operating_period_name

    common_functions.patch_req("baseline_operation_7_1_row", baseline_operation_7_1_row_id, body, dev)
    common_functions.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)



start()


